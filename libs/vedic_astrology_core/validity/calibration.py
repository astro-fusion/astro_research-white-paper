"""Calibration case registry, Clopper-Pearson bound and the calibration certificate.

ADR-008 section 4.4 (H-6, closes G-01), work package WP-84.

The whole-pipeline calibration (WP-98) runs every case of ADR-008 sections
1.3, 2.4, 3.6, 4.4, 5, 6.3, 7.3 and 8 and writes
``studies/validity/calibration/certificate.json``. ``begin_confirm`` calls
:func:`check_certificate` before it issues a confirm handle. The check
refuses when the certificate is missing, when a case required for the test's
outcome type failed or ran with too few replications, or when any certified
file (``core/stats``, ``core/validity``, ``core/domains``,
``tests/simulators.py``) or the environment lock changed since the
certificate was written. So changing the statistics after calibrating means
calibrating again.

This module holds the case **specifications** (id, replications, pass mark,
outcome types). The code that runs a case lives with the method it certifies
(WP-85 onwards) and in the WP-98 suite; it hands back counts, and
:func:`evaluate` turns counts into a pass or a fail with the same bound for
every case.

Pass mark used throughout: the upper one-sided 95% Clopper-Pearson bound on
the rate, also for the fast subset (REVIEW_1 fix 2: a fast cell passes only
when its bound, not its observed rate, is at or below the fast mark; a cell
that misses it is inconclusive and must be run at full size).

Provenance (audit 2 N-01, N-12, N-23). Every chunk of a calibration run
carries :func:`provenance` (digests of the certified code, of the harness
file :data:`HARNESS_PATH`, of the environment lock and of the installed
packages). The harness refuses to add up chunks whose provenance differs from
the code on disk, and the certificate stores the commit, the harness hash and
the installed versions. :func:`check_certificate` refuses a certificate
without them, or whose harness or installed packages differ now. A case with
any cell below its full replications is not passed in ``case_passed``.
No thread is started here (G-13).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scipy.stats import beta as _beta

SCHEMA_VERSION = 1

#: Outcome types of ADR-008 section 2.2. A certificate is checked per type.
OUTCOME_TYPES: Tuple[str, ...] = ("continuous", "log_ratio", "events", "flags")
ALL = OUTCOME_TYPES

#: Paths (relative to the repository root) whose git blob hashes the
#: certificate pins. Directories are walked recursively.
CERTIFIED_PATHS: Tuple[str, ...] = (
    "libs/vedic_astrology_core/stats",
    "libs/vedic_astrology_core/validity",
    "libs/vedic_astrology_core/domains",
    "tests/simulators.py",
)
ENV_LOCK_PATH = "ops/requirements.lock.txt"
#: The whole-pipeline harness that holds the scenarios (audit 2 N-23): its
#: hash is stored in the certificate and checked like the certified code.
HARNESS_PATH = "tests/test_validity_calibration.py"
#: Fast-subset mark (ADR-008 1.3) when a case names none. Judged on the upper
#: Clopper-Pearson bound (REVIEW_1 fix 2), never on the observed rate.
FAST_THRESHOLD = 0.085
DEFAULT_CERTIFICATE_PATH = "studies/validity/calibration/certificate.json"

_SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
_SKIP_SUFFIXES = (".pyc", ".pyo")
_SKIP_NAMES = {".DS_Store"}

#: Pass-rule kinds.
UPPER_BOUND_AT_MOST = "upper_bound_at_most"  # CP upper bound <= threshold
RATE_ABOVE = "rate_above"  # observed rate > threshold (documents an old loophole)
RATE_AT_LEAST = "rate_at_least"  # observed rate >= threshold (power)
ZERO = "zero"  # no event in any replication
PROPERTY = "property"  # a deterministic check; the runner says pass or fail
RECORD = "record"  # stored and shown, no pass mark (X9)
RULE_KINDS = (UPPER_BOUND_AT_MOST, RATE_ABOVE, RATE_AT_LEAST, ZERO, PROPERTY, RECORD)


class CertificateError(RuntimeError):
    """The calibration certificate is missing, failed, stale or tampered with."""


# ---------------------------------------------------------------- bounds
def clopper_pearson_upper(k: int, n: int, confidence: float = 0.95) -> float:
    """Upper one-sided Clopper-Pearson bound on a binomial rate.

    ``k`` events in ``n`` trials; the bound is the ``confidence`` quantile of
    Beta(k + 1, n - k), and 1 when ``k == n``.
    """
    k, n = int(k), int(n)
    if n <= 0 or k < 0 or k > n:
        raise ValueError(f"need 0 <= k <= n and n > 0, got k={k}, n={n}")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0, 1)")
    if k == n:
        return 1.0
    return float(_beta.ppf(confidence, k + 1, n - k))


def max_passing_count(n: int, threshold: float = 0.06, confidence: float = 0.95) -> int:
    """Largest count k whose upper Clopper-Pearson bound is at or below ``threshold``.

    Returns -1 when even k = 0 fails (too few replications for the mark).
    """
    lo, hi = -1, int(n)
    while lo < hi:  # the bound increases with k
        mid = (lo + hi + 1) // 2
        if clopper_pearson_upper(mid, n, confidence) <= threshold:
            lo = mid
        else:
            hi = mid - 1
    return lo


# ----------------------------------------------------------------- seeds
def derive_seed(*parts: object) -> int:
    """Seed from the first 8 bytes of SHA-256 over ``"|".join(parts)`` (ADR-008 3.5)."""
    text = "|".join(str(p) for p in parts)
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def case_seed(base_seed: int, case_id: str, cell: str = "", purpose: str = "calibration") -> int:
    """Seed of one case cell: no generator is shared between cases or cells."""
    return derive_seed(base_seed, case_id, cell, purpose)


# --------------------------------------------------------------- registry
@dataclass(frozen=True)
class CaseSpec:
    """One calibration case as written in ADR-008."""

    case_id: str
    section: str
    title: str
    rule: str
    threshold: Optional[float] = None
    replications: Optional[int] = None
    outcome_types: Tuple[str, ...] = ALL
    fast_replications: Optional[int] = None
    fast_threshold: Optional[float] = None

    def __post_init__(self):
        if self.rule not in RULE_KINDS:
            raise ValueError(f"{self.case_id}: unknown rule {self.rule!r}")
        if self.rule in (UPPER_BOUND_AT_MOST, RATE_ABOVE, RATE_AT_LEAST):
            if self.threshold is None or self.replications is None:
                raise ValueError(f"{self.case_id}: rule {self.rule} needs threshold and replications")
        if self.rule == ZERO and self.replications is None:
            raise ValueError(f"{self.case_id}: rule zero needs replications")
        bad = set(self.outcome_types) - set(OUTCOME_TYPES)
        if bad or not self.outcome_types:
            raise ValueError(f"{self.case_id}: unknown outcome types {sorted(bad)}")


CASES: Dict[str, CaseSpec] = {}


def register(spec: CaseSpec) -> CaseSpec:
    """Add a case; an id can be registered once only."""
    if spec.case_id in CASES:
        raise ValueError(f"case {spec.case_id} is already registered")
    CASES[spec.case_id] = spec
    return spec


def get_case(case_id: str) -> CaseSpec:
    try:
        return CASES[case_id]
    except KeyError:
        raise KeyError(f"unknown calibration case {case_id!r}") from None


def required_cases(outcome_type: str) -> List[CaseSpec]:
    """Cases a confirm of this outcome type needs passed (RECORD cases excluded)."""
    if outcome_type not in OUTCOME_TYPES:
        raise ValueError(f"unknown outcome type {outcome_type!r}")
    return [
        c for c in CASES.values() if outcome_type in c.outcome_types and c.rule != RECORD
    ]


_C, _L, _E, _F = "continuous", "log_ratio", "events", "flags"
_N = 10_000  # per-test rates
_FAM = 2_000  # family rates
_POW = 1_000  # power

for _spec in (
    # Section 1.3: balanced blocks and the primary test (no effect planted).
    CaseSpec("B1", "1.3", "Periodic calendars, i.i.d. Normal", UPPER_BOUND_AT_MOST, 0.06, _N, ALL, 400, 0.085),
    CaseSpec("B2", "1.3", "Skewed bars: lognormal, exponential, 98% zeros", UPPER_BOUND_AT_MOST, 0.06, _N, ALL, 400, 0.085),
    CaseSpec("B3", "1.3", "Dependence: GARCH, regimes, AR(1); real calendars 1968-1998", UPPER_BOUND_AT_MOST, 0.06, _N, ALL, 400, 0.085),
    CaseSpec("B4", "1.3", "No bar in two blocks; control bars never exceed inactive bars", PROPERTY),
    CaseSpec("B5", "1.3", "Old episode_differences exceeds size on 5/5 and 20/5", RATE_ABOVE, 0.07, _N, (_C,)),
    CaseSpec("B6", "1.3", "Test and gate report the same side and used blocks", PROPERTY),
    # Section 2.4: exclusion by effect removal (effect planted in bars).
    CaseSpec("X1", "2.4", "False exclusion at SESOI: Normal, Student-t(3)", UPPER_BOUND_AT_MOST, 0.06, _N, (_C, _L)),
    CaseSpec("X2", "2.4", "False exclusion at SESOI: lognormal, exponential", UPPER_BOUND_AT_MOST, 0.06, _N, (_C, _L)),
    CaseSpec("X3", "2.4", "False exclusion at SESOI: rare Poisson events", UPPER_BOUND_AT_MOST, 0.06, _N, (_E,)),
    CaseSpec("X4", "2.4", "False exclusion at SESOI: Neyman-Scott clustered events, doubling background", UPPER_BOUND_AT_MOST, 0.06, _N, (_E,)),
    CaseSpec("X5", "2.4", "False exclusion at SESOI: clustered GARCH flags, drought years", UPPER_BOUND_AT_MOST, 0.06, _N, (_F,)),
    CaseSpec("X6", "2.4", "X95 coverage at 0, SESOI/2, SESOI, 2 SESOI", UPPER_BOUND_AT_MOST, 0.06, _N, ALL),
    CaseSpec("X7", "2.4", "Balance edge 0.5, 0.75, 1.0", UPPER_BOUND_AT_MOST, 0.06, _N, (_C, _L, _E)),
    CaseSpec("X8", "2.4", "Old episode_equivalence falsely excludes on skewed rows", RATE_ABOVE, 0.10, _N, (_C,)),
    CaseSpec("X9", "2.4", "Uneven effect in 20% of episodes (recorded, no pass mark)", RECORD, None, _N, ALL),
    CaseSpec("X10", "2.4", "Exclusion p never increases as r grows", PROPERTY),
    # Section 3.6: families.
    CaseSpec("F1", "3.6", "Fixed threshold: other p-values do not move a verdict", PROPERTY),
    CaseSpec("F2", "3.6", "Adding tests leaves batch 1 byte-identical", PROPERTY),
    CaseSpec("F3", "3.6", "Clone attack on the same vintage", UPPER_BOUND_AT_MOST, 0.06, _FAM),
    CaseSpec("F4", "3.6", "Clone attack with a fresh vintage", UPPER_BOUND_AT_MOST, 0.06, _FAM),
    CaseSpec("F5", "3.6", "Alpha table sums to at most 0.05", PROPERTY),
    CaseSpec("F6", "3.6", "Seeds: adding a test leaves other numbers identical", PROPERTY),
    CaseSpec("F7", "3.6", "Eligibility table", PROPERTY),
    CaseSpec("F8S", "3.6", "Null families through the pipeline: any false S", UPPER_BOUND_AT_MOST, 0.06, _FAM),
    CaseSpec("F8C", "3.6", "Null families through the pipeline: any false C", UPPER_BOUND_AT_MOST, 0.06, _FAM),
    # Section 4.4: power (W3 runs inside each sealed run, not in the certificate).
    CaseSpec("W1", "4.4", "Power at twice the minimal detectable effect", RATE_AT_LEAST, 0.80, _POW),
    CaseSpec("W2", "4.4", "Limit-only tests never support", ZERO, None, _POW),
    CaseSpec("W4", "4.4", "support_underpowered flag present when P(S | SESOI) < 0.8", PROPERTY),
    # Section 5: placebo skies.
    CaseSpec("R2N", "5", "R2 pass rate under no effect", UPPER_BOUND_AT_MOST, 0.06, _N),
    CaseSpec("R2P", "5", "Nakshatra, tithi and orb calendars with a strong effect pass R2; R2 per test", PROPERTY),
    # Section 6.3: season.
    CaseSpec("Z1", "6.3", "Seasonal mean, no calendar effect", UPPER_BOUND_AT_MOST, 0.06, _N),
    CaseSpec("Z2", "6.3", "Seasonal clustered events", UPPER_BOUND_AT_MOST, 0.06, _N, (_E,)),
    CaseSpec("Z3", "6.3", "Yearly rainfall with ENSO driver and epoch wave", UPPER_BOUND_AT_MOST, 0.06, _N, (_C, _F)),
    CaseSpec("Z4", "6.3", "Old neighbour design passes a Sun-linked calendar", RATE_ABOVE, 0.20, _N, (_C,)),
    CaseSpec("Z5", "6.3", "Sun in sign is Untestable without reading the outcome", PROPERTY),
    CaseSpec("Z6", "6.3", "Nodal proxy: S at most 5% with the nodal baseline", UPPER_BOUND_AT_MOST, 0.06, _N, (_C, _F)),
    # Section 7.3: known channels.
    CaseSpec("K1", "7.3", "Festival-only effect: S with baselines", UPPER_BOUND_AT_MOST, 0.06, _N, (_C,)),
    CaseSpec("K2", "7.3", "Festival-only effect: S without baselines", RATE_ABOVE, 0.50, _N, (_C,)),
    # Section 8: data rules.
    CaseSpec("D1", "8", "Monthly averages with one guard month", UPPER_BOUND_AT_MOST, 0.06, _N, (_C, _L)),
):
    register(_spec)


# ---------------------------------------------------------------- results
@dataclass(frozen=True)
class CaseResult:
    """The outcome of one cell of one case (a cell is one generator x K x ...)."""

    case_id: str
    cell: str
    replications: Optional[int]
    count: Optional[int]
    rate: Optional[float]
    upper_bound: Optional[float]
    passed: bool
    rule: str
    threshold: Optional[float]
    note: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


def evaluate(case_id: str, cell: str, count: int, replications: int, fast: bool = False) -> CaseResult:
    """Turn a count of rejections (or of successes for power) into a result.

    ``fast`` uses the case's fast subset mark (ADR-008 1.3: 400 replications,
    mark 0.085). REVIEW_1 fix 2: a fast cell passes only when its upper
    Clopper-Pearson bound is at or below the mark (at 400 replications: 24
    rejections or fewer), not its observed rate; a fast cell that misses the
    mark is inconclusive and must be run at full size. A fast result never
    satisfies :func:`check_certificate` because its replications are below
    the case's.
    """
    spec = get_case(case_id)
    if spec.rule == PROPERTY:
        raise ValueError(f"{case_id} is a property case; use property_result")
    k, n = int(count), int(replications)
    rate = k / n if n else float("nan")
    ub = clopper_pearson_upper(k, n)
    threshold = spec.threshold
    if fast:
        if spec.fast_threshold is None:
            raise ValueError(f"{case_id} has no fast subset")
        threshold = spec.fast_threshold
    if fast:
        passed = fast_passes(spec, k, n)
    elif spec.rule == UPPER_BOUND_AT_MOST:
        passed = ub <= threshold
    elif spec.rule == RATE_ABOVE:
        passed = rate > threshold
    elif spec.rule == RATE_AT_LEAST:
        passed = rate >= threshold
    elif spec.rule == ZERO:
        passed = k == 0
    else:  # RECORD
        passed = True
    return CaseResult(case_id, str(cell), n, k, rate, ub, bool(passed), spec.rule, threshold)


def fast_threshold(spec: CaseSpec) -> float:
    """The fast-subset mark of a case (its own, else :data:`FAST_THRESHOLD`)."""
    return float(spec.fast_threshold if spec.fast_threshold is not None else FAST_THRESHOLD)


def fast_passes(spec: CaseSpec, count: int, replications: int) -> bool:
    """Fast-subset judgement of a size case (REVIEW_1 fix 2).

    The upper one-sided 95% Clopper-Pearson bound on the rejection rate must
    be at or below the fast mark. The observed rate is never the rule. Only
    for :data:`UPPER_BOUND_AT_MOST` cases; other rules have no fast mark.
    """
    if spec.rule != UPPER_BOUND_AT_MOST:
        raise ValueError(f"{spec.case_id}: only upper-bound cases have a fast mark")
    return clopper_pearson_upper(int(count), int(replications)) <= fast_threshold(spec)


def property_result(case_id: str, cell: str, passed: bool, note: str = "") -> CaseResult:
    """Result of a property case (no replications, a plain pass or fail)."""
    spec = get_case(case_id)
    if spec.rule != PROPERTY:
        raise ValueError(f"{case_id} is not a property case")
    return CaseResult(case_id, str(cell), None, None, None, None, bool(passed), PROPERTY, None, note)


# ------------------------------------------------------------- code hashes
def git_blob_sha1(data: bytes) -> str:
    """The id ``git hash-object`` gives these bytes (no filters applied)."""
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def _walk(root: Path, rel: str) -> Iterable[Path]:
    p = root / rel
    if p.is_file():
        yield p
        return
    if not p.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(p):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for name in sorted(filenames):
            if name in _SKIP_NAMES or name.endswith(_SKIP_SUFFIXES):
                continue
            yield Path(dirpath) / name


def code_hashes(repo_root, paths: Sequence[str] = CERTIFIED_PATHS) -> Dict[str, str]:
    """Git blob hash of every file under ``paths``, keyed by POSIX path from the root.

    Files on disk are hashed, tracked or not, so an untracked helper that
    changes a result also invalidates the certificate.
    """
    root = Path(repo_root)
    out: Dict[str, str] = {}
    for rel in paths:
        for f in _walk(root, rel):
            out[f.relative_to(root).as_posix()] = git_blob_sha1(f.read_bytes())
    return dict(sorted(out.items()))


def env_lock_hash(repo_root, lock_path: str = ENV_LOCK_PATH) -> Optional[str]:
    """SHA-256 of the environment lock file, or None when there is none."""
    p = Path(repo_root) / lock_path
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(obj) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def harness_hash(repo_root, harness_path: str = HARNESS_PATH) -> Optional[str]:
    """Git blob hash of the calibration harness, or None when there is none (N-23)."""
    p = Path(repo_root) / harness_path
    return git_blob_sha1(p.read_bytes()) if p.is_file() else None


def installed_versions() -> Dict[str, str]:
    """Installed distributions of this interpreter, name (lower case) to version (N-12)."""
    from importlib import metadata

    out: Dict[str, str] = {}
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip().lower()
        if name:
            out[name] = str(dist.version)
    return dict(sorted(out.items()))


def git_commit(repo_root) -> Optional[str]:
    """HEAD commit of the repository, or None outside git (recorded, never checked)."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root), capture_output=True,
                             text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and len(sha) == 40 else None


def provenance(
    repo_root,
    paths: Sequence[str] = CERTIFIED_PATHS,
    lock_path: str = ENV_LOCK_PATH,
    harness_path: str = HARNESS_PATH,
) -> Dict[str, Optional[str]]:
    """What produced a calibration count (audit 2 N-01).

    Digests of the certified code (every blob hash under `paths`), of the
    harness file, of the environment lock and of the installed packages.
    Every chunk of a run carries it; chunks with different provenance are
    never added up, and the certificate stores the one its counts came from.
    """
    return {
        "code_sha256": _digest(code_hashes(repo_root, paths)),
        "harness_sha256": harness_hash(repo_root, harness_path),
        "env_lock_sha256": env_lock_hash(repo_root, lock_path),
        "installed_sha256": _digest(installed_versions()),
    }


def check_provenance(chunks: Iterable[Optional[Mapping]], current: Mapping) -> int:
    """Refuse (raise :class:`CertificateError`) unless every chunk was made by `current`.

    `chunks` holds one provenance per finished chunk (None when a chunk
    has none, as chunks written before N-01 do). Returns the number checked.
    A mix of code versions, or chunks from code other than the code on disk,
    can never be summed into one certificate (N-01).
    """
    want = dict(current)
    n = 0
    stale = 0
    missing = 0
    for p in chunks:
        n += 1
        if p is None:
            missing += 1
        elif dict(p) != want:
            stale += 1
    if missing or stale:
        raise CertificateError(
            f"{stale + missing} of {n} calibration chunks were not produced by the code on disk "
            f"({missing} carry no provenance, {stale} another code, harness, lock or environment); "
            "start from an empty work directory"
        )
    return n


# ------------------------------------------------------------ certificate

def _clean_rate(v):
    return None if (isinstance(v, float) and math.isnan(v)) else v


def build_certificate(
    results: Sequence[CaseResult],
    repo_root,
    seed: int,
    created_utc: Optional[str] = None,
    paths: Sequence[str] = CERTIFIED_PATHS,
    lock_path: str = ENV_LOCK_PATH,
    run_provenance: Optional[Mapping] = None,
    harness_path: str = HARNESS_PATH,
) -> Dict:
    """Certificate body plus its own SHA-256 (``body_sha256``).

    ``run_provenance``: the provenance every chunk of the run carried (the
    harness has checked they agree); it must equal :func:`provenance` of
    the files on disk now, or the certificate is refused here (N-01).
    ``case_passed`` is False for a case with any cell below the case's full
    replications (a fast cell can never make a case pass).
    """
    now = provenance(repo_root, paths, lock_path, harness_path)
    if run_provenance is not None and dict(run_provenance) != now:
        raise CertificateError("the run's provenance differs from the code on disk; recalibrate")
    rows = []
    for r in results:
        get_case(r.case_id)  # unknown ids are refused
        d = r.to_dict()
        d["rate"] = _clean_rate(d["rate"])
        rows.append(d)
    rows.sort(key=lambda d: (d["case_id"], d["cell"]))
    summary = {}
    for cid in sorted({d["case_id"] for d in rows}):
        need = get_case(cid).replications
        summary[cid] = all(
            d["passed"] and (need is None or d["replications"] is None or int(d["replications"]) >= int(need))
            for d in rows if d["case_id"] == cid
        )
    body = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": created_utc,
        "seed": int(seed),
        "certified_paths": list(paths),
        "code_hashes": code_hashes(repo_root, paths),
        "env_lock_path": lock_path,
        "env_lock_sha256": env_lock_hash(repo_root, lock_path),
        "commit": git_commit(repo_root),
        "harness_path": harness_path,
        "harness_sha256": now["harness_sha256"],
        "installed": installed_versions(),
        "provenance": now,
        "cases": rows,
        "case_passed": summary,
    }
    body["body_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def write_certificate(path, results: Sequence[CaseResult], repo_root, seed: int, **kw) -> Dict:
    """Build the certificate and write it as sorted, indented JSON."""
    cert = build_certificate(results, repo_root, seed, **kw)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cert, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return cert


def load_certificate(path) -> Dict:
    """Read a certificate and verify its own body hash."""
    p = Path(path)
    if not p.is_file():
        raise CertificateError(f"no calibration certificate at {p}")
    try:
        cert = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CertificateError(f"certificate is not valid JSON: {exc}") from None
    if not isinstance(cert, dict) or "body_sha256" not in cert:
        raise CertificateError("certificate has no body_sha256")
    body = {k: v for k, v in cert.items() if k != "body_sha256"}
    if hashlib.sha256(_canonical(body)).hexdigest() != cert["body_sha256"]:
        raise CertificateError("certificate body does not match its body_sha256 (edited by hand?)")
    if cert.get("schema_version") != SCHEMA_VERSION:
        raise CertificateError(f"certificate schema {cert.get('schema_version')!r} is not {SCHEMA_VERSION}")
    return cert


def check_certificate(
    path,
    repo_root,
    outcome_type: Optional[str] = None,
) -> Dict:
    """Refuse (raise :class:`CertificateError`) unless the certificate still holds.

    Checks, in order: the file exists and its body hash is intact; the
    certified files and the environment lock hash equal those on disk now
    (any changed, added or removed file fails); and, when ``outcome_type``
    is given, every case required for it has at least one result, every
    cell passed and ran with at least the case's replications.
    Returns the certificate.
    """
    cert = load_certificate(path)
    paths = tuple(cert.get("certified_paths") or CERTIFIED_PATHS)
    if tuple(paths) != tuple(CERTIFIED_PATHS):
        raise CertificateError("certificate covers other paths than the code requires")
    now = code_hashes(repo_root, paths)
    then = cert.get("code_hashes", {})
    if now != then:
        changed = sorted(k for k in set(now) | set(then) if now.get(k) != then.get(k))
        raise CertificateError(
            "certified code changed since calibration: " + ", ".join(changed[:10])
            + (" ..." if len(changed) > 10 else "")
        )
    lock = cert.get("env_lock_path", ENV_LOCK_PATH)
    if env_lock_hash(repo_root, lock) != cert.get("env_lock_sha256"):
        raise CertificateError("environment lock changed since calibration")
    prov = cert.get("provenance")
    if not isinstance(prov, dict) or "harness_sha256" not in cert:
        raise CertificateError("certificate has no run provenance (commit, harness, installed packages; "
                               "audit 2 N-01); recalibrate from an empty work directory")
    if harness_hash(repo_root, cert.get("harness_path", HARNESS_PATH)) != cert.get("harness_sha256"):
        raise CertificateError("calibration harness changed since calibration (N-23)")
    if _digest(installed_versions()) != prov.get("installed_sha256"):
        raise CertificateError("installed packages differ from those the calibration ran on (N-12)")
    if outcome_type is not None:
        rows = cert.get("cases", [])
        for spec in required_cases(outcome_type):
            mine = [r for r in rows if r.get("case_id") == spec.case_id]
            if not mine:
                raise CertificateError(f"case {spec.case_id} missing from the certificate")
            for r in mine:
                if not r.get("passed"):
                    raise CertificateError(f"case {spec.case_id} cell {r.get('cell')!r} failed")
                if spec.replications is not None and (r.get("replications") or 0) < spec.replications:
                    raise CertificateError(
                        f"case {spec.case_id} cell {r.get('cell')!r} ran {r.get('replications')} "
                        f"replications, needs {spec.replications}"
                    )
    return cert


__all__ = [
    "ALL",
    "CASES",
    "CERTIFIED_PATHS",
    "CaseResult",
    "CaseSpec",
    "CertificateError",
    "DEFAULT_CERTIFICATE_PATH",
    "ENV_LOCK_PATH",
    "OUTCOME_TYPES",
    "build_certificate",
    "case_seed",
    "check_certificate",
    "clopper_pearson_upper",
    "code_hashes",
    "derive_seed",
    "env_lock_hash",
    "evaluate",
    "FAST_THRESHOLD",
    "HARNESS_PATH",
    "check_provenance",
    "fast_passes",
    "fast_threshold",
    "get_case",
    "git_commit",
    "harness_hash",
    "installed_versions",
    "provenance",
    "git_blob_sha1",
    "load_certificate",
    "max_passing_count",
    "property_result",
    "register",
    "required_cases",
    "write_certificate",
]
