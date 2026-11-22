"""Closed registration batches, fixed thresholds, eligibility and random streams.

ADR-008 section 3 (H-3, H-4), work package WP-88. Re-specifies ADR-007 WP-66:
the budget M, the slots and Benjamini-Yekutieli are withdrawn. Closes S-03,
S-04, S-09 (supportability table), S-10 (stated per domain), G-04 (``use:``
parents pinned by hash), G-06 (random streams) and G-12 (no budget to run
out of).

The family lock of a domain is one append-only, hash-chained JSON-lines file.
Each line holds the SHA-256 of the line before it. Entry kinds:

``register``
    One test: (rule id, version, candidate variant, outcome) with its calendar
    hash, lineage id, pinned ``use:`` parents and the open batch it joined.
    Controls are registered outside every batch (rule 9).
``batch_close``
    Test ids, n_b, alpha_b, ``a_test = alpha_b / n_b``, the vintage the batch
    is confirmed on and the seal bundle hash. Written before any confirm
    outcome of that vintage is read. ``a_test`` is stored and never
    recomputed (rule 4).
``batch_results``
    SHA-256 of the results file of a closed batch. A later run re-verifies
    those bytes; it recomputes nothing (section 3.4).

Rules implemented here (ADR-008 3.2): 1 vintages, 2 batches, 3 alpha spending
``alpha_b = 0.04 x 0.2^(b-1)``, 4 fixed Bonferroni threshold per batch, 5 fresh
data for batch 2 onward, 6 registered after unblinding is descriptive, 7 seen
confirm periods, 8 at most 3 candidate variants per lineage per batch,
9 controls outside every batch, 10 replication as a new test in a later batch.
Section 3.5: ``seed = first 8 bytes of SHA-256(plan seed | test id | purpose)``.

The guarantee is per domain and per verdict type, family-wise: the chance of
at least one false Supported in a domain, over all batches for ever, is at most
sum(alpha_b) = 0.05 under any dependence (Bonferroni inside a batch, alpha
spent across batches, fresh data for every later batch).

Pure Python plus numpy; no outcome access, no network, no thread.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any, Collection, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

__all__ = [
    "ALPHA_FIRST",
    "ALPHA_RATIO",
    "MAX_VARIANTS",
    "PRIMARY",
    "SEED_PURPOSES",
    "FAMILY_WISE_STATEMENT",
    "FamilyError",
    "FamilyLockError",
    "DuplicateTestError",
    "DuplicateCalendarError",
    "TooManyVariantsError",
    "UnpinnedUseError",
    "StaleVintageError",
    "ClosedBatchChangedError",
    "LockMismatchError",
    "Eligibility",
    "FamilyLock",
    "alpha_for_batch",
    "alpha_table",
    "a_test_for",
    "passes",
    "stream_seed",
    "stream_rng",
    "calendar_hash",
    "lineage_id",
    "make_test_id",
    "canonical_bytes",
    "limit_verdict",
    "min_blocks_for_support",
    "min_informative_for_limit",
    "supportability_table",
    "clone_attack_case",
]

#: Alpha of batch 1 and the ratio between consecutive batches (rule 3).
ALPHA_FIRST = "0.04"
ALPHA_RATIO = "0.2"
#: Ceiling on the sum of alpha_b over all batches of a domain.
ALPHA_TOTAL = Fraction(1, 20)
#: Candidate variants per lineage per batch (rule 8).
MAX_VARIANTS = 3
#: Variant name of the primary specification.
PRIMARY = "primary"
#: Purposes of a random stream (section 3.5).
SEED_PURPOSES: Tuple[str, ...] = ("signflip", "thinning", "placebo", "bootstrap")
#: Minimum K_eff of gate G4 (section 1.1 item 9).
K_EFF_MIN = 8

#: First paragraph of the summary (S-10); the number of domains comes from the run set.
FAMILY_WISE_STATEMENT = (
    "Chance of at least one false Supported in a domain: at most 5% over all time. "
    "Across {d} domains and three verdict types: at most {d} x 3 x 5% in total; "
    "expected number of false verdicts at most that."
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
VERDICTS = ("S", "C", "E", "N", "U")


# ----------------------------------------------------------------- errors
class FamilyError(ValueError):
    """A registration, close or check that the family rules refuse."""


class FamilyLockError(FamilyError):
    """The lock file is not a valid hash chain, or belongs to another domain."""


class DuplicateTestError(FamilyError):
    """The test id (rule, version, variant, outcome) is already registered."""


class DuplicateCalendarError(FamilyError):
    """Another test of the domain has the same calendar for the same outcome."""


class TooManyVariantsError(FamilyError):
    """More than MAX_VARIANTS candidate variants of one lineage in one batch."""


class UnpinnedUseError(FamilyError):
    """A use: parent without version or hash (G-04)."""


class StaleVintageError(FamilyError):
    """A batch would close on a vintage whose confirm outcomes were already open."""


class ClosedBatchChangedError(FamilyError):
    """The results of a closed batch differ from the bytes recorded for it."""


class LockMismatchError(FamilyError):
    """The rule files and the lock disagree (calendar or parent changed)."""


# ----------------------------------------------------------------- alpha
def _fraction(x: Any) -> Fraction:
    if isinstance(x, bool) or x is None:
        raise FamilyError("alpha parameters must be numbers")
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        return Fraction(repr(x))
    try:
        return Fraction(x)
    except (TypeError, ValueError) as exc:
        raise FamilyError(f"alpha parameter {x!r} is not a number") from exc


def _schedule(first: Any = ALPHA_FIRST, ratio: Any = ALPHA_RATIO) -> Tuple[Fraction, Fraction]:
    f, r = _fraction(first), _fraction(ratio)
    if f <= 0 or not (0 < r < 1):
        raise FamilyError("alpha spending needs first > 0 and 0 < ratio < 1")
    if f / (1 - r) > ALPHA_TOTAL:
        raise FamilyError("alpha spending: first / (1 - ratio) must be at most 0.05")
    return f, r


def alpha_for_batch(b: int, first: Any = ALPHA_FIRST, ratio: Any = ALPHA_RATIO) -> float:
    """~~alpha_b = first x ratio^(b-1)~~ as the nearest double (0.04, 0.008, 0.0016, ...)."""
    if isinstance(b, bool) or not isinstance(b, int) or b < 1:
        raise FamilyError("batch numbers start at 1")
    f, r = _schedule(first, ratio)
    return float(f * r ** (b - 1))


def alpha_table(n_batches: int, first: Any = ALPHA_FIRST, ratio: Any = ALPHA_RATIO) -> List[float]:
    """alpha_b for batches 1 to n_batches."""
    return [alpha_for_batch(b, first, ratio) for b in range(1, n_batches + 1)]


def a_test_for(alpha_b: float, n_b: int) -> float:
    """The fixed per-test threshold ~~alpha_b / n_b~~ (Bonferroni, rule 4)."""
    if isinstance(n_b, bool) or not isinstance(n_b, int) or n_b < 1:
        raise FamilyError("a batch has at least one test")
    return float(alpha_b) / n_b


def passes(p: float, a_test: float) -> bool:
    """A p-value passes its fixed threshold when ~~p <= a_test~~ (the boundary passes)."""
    p = float(p)
    if not (0.0 <= p <= 1.0):
        raise FamilyError(f"p-value {p!r} outside [0, 1]")
    return p <= float(a_test)


# --------------------------------------------------------------- streams
def stream_seed(plan_seed: Union[int, str], test_id: str, purpose: str) -> int:
    """First 8 bytes (big-endian) of SHA-256("plan seed|test id|purpose").

    Every random draw of a test comes from its own stream, so adding, removing
    or reordering other tests changes none of its numbers (G-06, F6).
    """
    if purpose not in SEED_PURPOSES:
        raise FamilyError(f"purpose must be one of {SEED_PURPOSES}, got {purpose!r}")
    if isinstance(plan_seed, bool) or not isinstance(plan_seed, (int, str)) or plan_seed == "":
        raise FamilyError("plan seed must be an integer or a non-empty string")
    if not isinstance(test_id, str) or not test_id:
        raise FamilyError("test id must be a non-empty string")
    digest = hashlib.sha256(f"{plan_seed}|{test_id}|{purpose}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def stream_rng(plan_seed: Union[int, str], test_id: str, purpose: str) -> np.random.Generator:
    """A fresh generator on the test's own stream; never shared between tests."""
    return np.random.default_rng(stream_seed(plan_seed, test_id, purpose))


# ------------------------------------------------------------ identities
def calendar_hash(active: Any) -> str:
    """SHA-256 of the active-bar vector on a vintage's grid (one byte per bar, 0 or 1)."""
    a = np.asarray(active)
    if a.ndim != 1 or a.size == 0:
        raise FamilyError("a calendar is a non-empty one-dimensional vector of bars")
    if a.dtype != bool:
        if not np.all(np.isin(a, (0, 1))):
            raise FamilyError("calendar bars must be 0/1 or boolean")
        a = a.astype(bool)
    return hashlib.sha256(a.astype(np.uint8).tobytes()).hexdigest()


def lineage_id(root_rule_id: str, cal_hash: str) -> str:
    """SHA-256 of "root rule id|calendar hash" (ADR-008 4.1)."""
    _check_hex(cal_hash, "calendar hash")
    return hashlib.sha256(f"{root_rule_id}|{cal_hash}".encode("utf-8")).hexdigest()


def make_test_id(rule_id: str, version: int, variant: str, outcome: str) -> str:
    """~~rule@version/variant/outcome~~; a new version is a new test."""
    return f"{rule_id}@{version}/{variant}/{outcome}"


def canonical_bytes(obj: Any) -> bytes:
    """Sorted-key compact JSON as UTF-8 (the bytes a results file is hashed by)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def _sha(data: Union[str, bytes]) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _check_hex(value: Any, what: str) -> str:
    if not isinstance(value, str) or not _HEX64.match(value):
        raise FamilyError(f"{what} must be 64 lower-case hex characters")
    return value


def _iso(value: Any, end: bool) -> Optional[str]:
    """ISO date of a year, year-month, ISO string or date; month/year ends when end=True."""
    import datetime as _dt

    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, int) and not isinstance(value, bool):
        value = f"{value:04d}"
    if not isinstance(value, str):
        return None
    s = value.strip()
    try:
        if re.fullmatch(r"\d{4}", s):
            return f"{s}-12-31" if end else f"{s}-01-01"
        if re.fullmatch(r"\d{4}-\d{2}", s):
            y, m = int(s[:4]), int(s[5:])
            if not end:
                return _dt.date(y, m, 1).isoformat()
            nxt = _dt.date(y + (m == 12), m % 12 + 1, 1)
            return (nxt - _dt.timedelta(days=1)).isoformat()
        return _dt.date.fromisoformat(s[:10]).isoformat()
    except ValueError:
        return None


def _vintage(v: Any) -> Dict[str, Any]:
    """Normalise a plan vintage: id, confirm_period {start, end}, seen, never_opened."""
    if not isinstance(v, Mapping):
        raise FamilyError("a vintage is a mapping with id, confirm_period and seen")
    vid = v.get("id")
    if not isinstance(vid, str) or not vid:
        raise FamilyError("a vintage needs an id")
    seen = v.get("seen")
    if not isinstance(seen, bool):
        raise FamilyError(f"vintage {vid}: 'seen' must be true or false (rule 7)")
    per = v.get("confirm_period")
    if not isinstance(per, Mapping):
        raise FamilyError(f"vintage {vid}: confirm_period needs start and end")
    a, b = _iso(per.get("start"), False), _iso(per.get("end"), True)
    if a is None or b is None or a > b:
        raise FamilyError(f"vintage {vid}: confirm_period needs readable start <= end")
    never = v.get("never_opened", False)
    if not isinstance(never, bool):
        raise FamilyError(f"vintage {vid}: never_opened must be true or false")
    out = {"id": vid, "confirm_period": {"start": a, "end": b}, "seen": seen, "never_opened": never}
    if v.get("snapshot") is not None:
        out["snapshot"] = str(v["snapshot"])
    return out


# ------------------------------------------------------------ eligibility
@dataclass(frozen=True)
class Eligibility:
    """What a test may say on one vintage (ADR-008 3.2 eligibility table).

    ~~numbers~~ is confirmatory, confirmatory_e_only, descriptive or control.
    ~~flags~~ always go on the card; ~~blocked~~ maps S, C and E to the flag
    added when that candidate verdict is lowered to N.
    """

    test_id: str
    vintage_id: str
    row: str
    allow_s: bool
    allow_c: bool
    allow_e: bool
    numbers: str
    flags: Tuple[str, ...] = ()
    blocked: Tuple[Tuple[str, str], ...] = ()
    a_test: Optional[float] = None
    batch: Optional[int] = None

    def allows(self, verdict: str) -> bool:
        return {"S": self.allow_s, "C": self.allow_c, "E": self.allow_e}.get(verdict, True)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "vintage_id": self.vintage_id,
            "row": self.row,
            "allow": {"S": self.allow_s, "C": self.allow_c, "E": self.allow_e},
            "numbers": self.numbers,
            "flags": list(self.flags),
            "a_test": self.a_test,
            "batch": self.batch,
        }


def limit_verdict(candidate: str, elig: Eligibility) -> Tuple[str, Tuple[str, ...]]:
    """Apply eligibility to a candidate verdict: (final verdict, flags).

    S, C or E that the row forbids become N with the row's blocking flag.
    N and U pass through. Eligibility never raises a verdict.
    """
    if candidate not in VERDICTS:
        raise FamilyError(f"verdict must be one of {VERDICTS}, got {candidate!r}")
    flags = list(elig.flags)
    if candidate in ("S", "C", "E") and not elig.allows(candidate):
        extra = dict(elig.blocked).get(candidate)
        if extra and extra not in flags:
            flags.append(extra)
        return "N", tuple(flags)
    return candidate, tuple(flags)


# ------------------------------------------------------------ the lock
@dataclass
class _Test:
    entry: Dict[str, Any]
    seq: int


@dataclass
class _Batch:
    number: int
    tests: List[str] = field(default_factory=list)
    close: Optional[Dict[str, Any]] = None
    results_sha256: Optional[str] = None


class FamilyLock:
    """The append-only, hash-chained family lock of one domain.

    path=None keeps the lock in memory (simulations). Otherwise every entry
    is appended to the file as one canonical JSON line, and opening the lock
    re-reads and re-checks every line (chain, sequence, domain, rules).
    """

    def __init__(self, path: Optional[Union[str, Path]], domain: str,
                 *, max_variants: int = MAX_VARIANTS):
        if not isinstance(domain, str) or not domain:
            raise FamilyError("a family lock belongs to one named domain")
        if isinstance(max_variants, bool) or not isinstance(max_variants, int) \
                or not 0 <= max_variants <= MAX_VARIANTS:
            raise FamilyError(f"max_variants must be an integer from 0 to {MAX_VARIANTS} (rule 8)")
        self.path = Path(path) if path is not None else None
        self.domain = domain
        self.max_variants = max_variants
        self._lines: List[str] = []
        self._entries: List[Dict[str, Any]] = []
        self._tests: Dict[str, _Test] = {}
        self._by_calendar: Dict[Tuple[str, str], List[str]] = {}
        self._batches: Dict[int, _Batch] = {1: _Batch(1)}
        self._schedule: Optional[Tuple[str, str]] = None
        if self.path is not None and self.path.exists():
            for line in self._file_lines():
                self._ingest(line)

    # -------------------------------------------------------- chain
    def _file_lines(self) -> List[str]:
        if self.path is None or not self.path.exists():
            return []
        return [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def _ingest(self, line: str) -> Dict[str, Any]:
        n = len(self._lines) + 1
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FamilyLockError(f"lock line {n} is not JSON") from exc
        if not isinstance(entry, dict):
            raise FamilyLockError(f"lock line {n} is not an object")
        prev = _sha(self._lines[-1]) if self._lines else None
        if entry.get("prev_sha256") != prev:
            raise FamilyLockError(f"lock line {n}: hash chain broken")
        if entry.get("seq") != n:
            raise FamilyLockError(f"lock line {n}: sequence number {entry.get('seq')!r}")
        if entry.get("domain") != self.domain:
            raise FamilyLockError(f"lock line {n}: domain {entry.get('domain')!r}, expected {self.domain!r}")
        if line != canonical_bytes(entry).decode("utf-8"):
            raise FamilyLockError(f"lock line {n}: not in canonical form (edited by hand?)")
        kind = entry.get("kind")
        if kind == "register":
            self._apply_register(entry, n)
        elif kind == "batch_close":
            self._apply_close(entry, n)
        elif kind == "batch_results":
            b = self._batches.get(entry.get("batch"))
            if b is None or b.close is None or b.results_sha256 is not None:
                raise FamilyLockError(f"lock line {n}: results for a batch that is not closed or already has them")
            b.results_sha256 = _check_hex(entry.get("results_sha256"), "results hash")
        else:
            raise FamilyLockError(f"lock line {n}: unknown kind {kind!r}")
        self._lines.append(line)
        self._entries.append(entry)
        return entry

    def _append(self, body: Dict[str, Any]) -> Dict[str, Any]:
        entry = dict(body)
        entry["domain"] = self.domain
        entry["seq"] = len(self._lines) + 1
        entry["prev_sha256"] = _sha(self._lines[-1]) if self._lines else None
        line = canonical_bytes(entry).decode("utf-8")
        if self.path is not None and self._file_lines() != self._lines:
            raise FamilyLockError(f"{self.path} changed since it was opened; reopen the lock")
        self._ingest(line)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        return dict(entry)

    def verify(self) -> Optional[str]:
        """Re-read the file (if any), check the whole chain and return the head hash."""
        if self.path is not None:
            FamilyLock(self.path, self.domain, max_variants=self.max_variants)
            if self._file_lines() != self._lines:
                raise FamilyLockError(f"{self.path} differs from the lock as opened")
        return self.head()

    def head(self) -> Optional[str]:
        """SHA-256 of the last line (what the seal bundle records); None when empty."""
        return _sha(self._lines[-1]) if self._lines else None

    @property
    def entries(self) -> List[Dict[str, Any]]:
        return [dict(e) for e in self._entries]

    # --------------------------------------------------- batches
    def closed_batches(self) -> List[int]:
        return sorted(n for n, b in self._batches.items() if b.close is not None)

    def open_batch(self) -> int:
        """Number of the batch new tests join: one after the last closed batch."""
        closed = self.closed_batches()
        return (closed[-1] + 1) if closed else 1

    def batch_tests(self, b: int) -> List[str]:
        batch = self._batches.get(b)
        return list(batch.tests) if batch else []

    def batch_close_entry(self, b: int) -> Optional[Dict[str, Any]]:
        batch = self._batches.get(b)
        return dict(batch.close) if batch and batch.close else None

    def _closing_on(self, vintage_id: str) -> Optional[Dict[str, Any]]:
        for n in self.closed_batches():
            c = self._batches[n].close
            if c["vintage"]["id"] == vintage_id:
                return c
        return None

    # --------------------------------------------------- register
    def register(
        self,
        *,
        rule_id: str,
        version: int,
        outcome: str,
        calendar_hash: str,
        variant: str = PRIMARY,
        use_parents: Sequence[Any] = (),
        replication_of: Optional[str] = None,
        control: bool = False,
        test_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register one test into the open batch and return its lock entry.

        Refuses a duplicate test id, a calendar already registered for the
        same outcome (a renamed copy, P6), a fourth candidate variant of one
        lineage in one batch (rule 8) and an unpinned use: parent (G-04).
        replication_of re-registers an old principle in a later batch
        (rule 10); the old record does not change. control=True keeps the
        test outside every batch (rule 9).
        """
        if not isinstance(rule_id, str) or not rule_id:
            raise FamilyError("rule_id must be a non-empty string")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise FamilyError("version must be a whole number >= 1")
        if not isinstance(outcome, str) or not outcome:
            raise FamilyError("outcome must be a non-empty string")
        if not isinstance(variant, str) or not variant:
            raise FamilyError("variant must be a non-empty string")
        if not isinstance(control, bool):
            raise FamilyError("control must be a bool")
        _check_hex(calendar_hash, "calendar hash")
        parents = _pin_parents(use_parents)
        tid = test_id or make_test_id(rule_id, version, variant, outcome)
        body: Dict[str, Any] = {
            "kind": "register",
            "test_id": tid,
            "rule_id": rule_id,
            "version": version,
            "variant": variant,
            "outcome": outcome,
            "calendar_hash": calendar_hash,
            "lineage_id": lineage_id(rule_id, calendar_hash),
            "use_parents": parents,
            "replication_of": replication_of,
            "control": control,
            "batch": None if control else self.open_batch(),
            "after_close_of": self.closed_batches(),
        }
        self._check_register(body)
        return self._append(body)

    def _check_register(self, e: Mapping[str, Any]) -> None:
        tid = e["test_id"]
        if tid in self._tests:
            raise DuplicateTestError(f"test {tid} is already registered")
        if e.get("control"):
            if e.get("replication_of") is not None or e.get("batch") is not None:
                raise FamilyError("a control is outside every batch and is not a replication")
            return
        b = e["batch"]
        if b != self.open_batch():
            raise FamilyLockError(f"test {tid}: batch {b} is not the open batch {self.open_batch()}")
        key = (e["calendar_hash"], e["outcome"])
        same = [t for t in self._by_calendar.get(key, []) if not self._tests[t].entry["control"]]
        rep = e.get("replication_of")
        if rep is not None:
            orig = self._tests.get(rep)
            if orig is None or orig.entry["control"]:
                raise FamilyError(f"replication_of {rep!r} is not a registered test")
            ob = orig.entry["batch"]
            if self._batches[ob].close is None or ob >= b:
                raise FamilyError(
                    f"replication_of {rep!r}: the original's batch must be closed and earlier (rule 10)"
                )
            others = [t for t in same if self._tests[t].entry["batch"] == b]
            if others:
                raise DuplicateCalendarError(f"test {tid}: calendar already registered in this batch as {others[0]}")
        elif same:
            raise DuplicateCalendarError(
                f"test {tid}: same calendar and outcome as {same[0]} (a renamed copy is refused; "
                "to replicate on fresh data, register with replication_of in a later batch)"
            )
        if e["variant"] != PRIMARY:
            names = {
                self._tests[t].entry["variant"]
                for t in self._batches[b].tests
                if self._tests[t].entry["rule_id"] == e["rule_id"] and self._tests[t].entry["variant"] != PRIMARY
            }
            names.add(e["variant"])
            if len(names) > self.max_variants:
                raise TooManyVariantsError(
                    f"{e['rule_id']}: at most {self.max_variants} candidate variants per lineage per batch; "
                    "move the rest to the sensitivity grid"
                )

    def _apply_register(self, e: Dict[str, Any], seq: int) -> None:
        for k in ("test_id", "rule_id", "version", "variant", "outcome", "calendar_hash",
                  "lineage_id", "use_parents", "replication_of", "control", "batch", "after_close_of"):
            if k not in e:
                raise FamilyLockError(f"lock line {seq}: register entry lacks {k!r}")
        _check_hex(e["calendar_hash"], "calendar hash")
        if e["lineage_id"] != lineage_id(e["rule_id"], e["calendar_hash"]):
            raise FamilyLockError(f"lock line {seq}: lineage id does not match rule and calendar")
        if e["after_close_of"] != self.closed_batches():
            raise FamilyLockError(f"lock line {seq}: after_close_of does not match the closed batches")
        if _pin_parents(e["use_parents"]) != e["use_parents"]:
            raise FamilyLockError(f"lock line {seq}: use parents not in normal form")
        self._check_register(e)
        self._tests[e["test_id"]] = _Test(e, seq)
        self._by_calendar.setdefault((e["calendar_hash"], e["outcome"]), []).append(e["test_id"])
        if not e["control"]:
            self._batches.setdefault(e["batch"], _Batch(e["batch"])).tests.append(e["test_id"])

    # --------------------------------------------------- close
    def close_batch(
        self,
        *,
        vintage: Mapping[str, Any],
        seal_bundle_sha256: str,
        alpha_first: Any = ALPHA_FIRST,
        alpha_ratio: Any = ALPHA_RATIO,
        plan_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Close the open batch: fix n_b, alpha_b and a_test for its tests.

        Must happen before any confirm outcome of the vintage is read (the
        seal bundle and its outside timestamp, WP-89, prove the order).
        Batch 1 may close on any vintage of the plan. A later batch needs a
        fresh vintage (rule 5): not used by an earlier close, and either
        listed never_opened or with a confirm period that starts after every
        earlier vintage's confirm period ends. The alpha schedule is fixed by
        the first close; a later close with another schedule is refused.
        """
        b = self.open_batch()
        if not self._batches.get(b) or not self._batches[b].tests:
            raise FamilyError(f"batch {b} has no tests to close")
        v = _vintage(vintage)
        _check_hex(seal_bundle_sha256, "seal bundle hash")
        if plan_sha256 is not None:
            _check_hex(plan_sha256, "plan hash")
        f, r = _schedule(alpha_first, alpha_ratio)
        n_b = len(self._batches[b].tests)
        alpha_b = float(f * r ** (b - 1))
        body = {
            "kind": "batch_close",
            "batch": b,
            "vintage": v,
            "test_ids": list(self._batches[b].tests),
            "n_b": n_b,
            "alpha_first": str(f),
            "alpha_ratio": str(r),
            "alpha_b": alpha_b,
            "a_test": a_test_for(alpha_b, n_b),
            "seal_bundle_sha256": seal_bundle_sha256,
            "plan_sha256": plan_sha256,
        }
        return self._append(body)

    def _apply_close(self, e: Dict[str, Any], seq: int) -> None:
        b = e.get("batch")
        if b != self.open_batch():
            raise FamilyLockError(f"lock line {seq}: batch_close for batch {b!r}, open batch is {self.open_batch()}")
        batch = self._batches.get(b)
        if batch is None or not batch.tests or e.get("test_ids") != batch.tests:
            raise FamilyLockError(f"lock line {seq}: batch_close {b} test ids differ from the registered tests")
        v = _vintage(e.get("vintage"))
        if v != e["vintage"]:
            raise FamilyLockError(f"lock line {seq}: vintage not in normal form")
        f, r = _schedule(e.get("alpha_first"), e.get("alpha_ratio"))
        sched = (str(f), str(r))
        if self._schedule is not None and sched != self._schedule:
            raise FamilyError(
                f"batch {b}: alpha schedule {sched} differs from {self._schedule} fixed at the first close"
            )
        if e.get("n_b") != len(batch.tests):
            raise FamilyLockError(f"lock line {seq}: n_b is not the number of tests")
        alpha_b = float(f * r ** (b - 1))
        if e.get("alpha_b") != alpha_b or e.get("a_test") != a_test_for(alpha_b, len(batch.tests)):
            raise FamilyLockError(f"lock line {seq}: alpha_b or a_test is not the schedule's value")
        _check_hex(e.get("seal_bundle_sha256"), "seal bundle hash")
        prior = [self._batches[n].close["vintage"] for n in self.closed_batches()]
        if any(p["id"] == v["id"] for p in prior):
            raise StaleVintageError(
                f"batch {b}: vintage {v['id']} was unblinded by an earlier batch; a later batch needs unseen data"
            )
        if prior and not v["never_opened"]:
            last_end = max(p["confirm_period"]["end"] for p in prior)
            if v["confirm_period"]["start"] <= last_end:
                raise StaleVintageError(
                    f"batch {b}: vintage {v['id']} starts {v['confirm_period']['start']}, not after the "
                    f"previous confirm data end {last_end}; it is not fresh (rule 5)"
                )
        self._schedule = sched
        batch.close = dict(e)
        self._batches.setdefault(b + 1, _Batch(b + 1))

    # --------------------------------------------------- records
    def test(self, test_id: str) -> Dict[str, Any]:
        t = self._tests.get(test_id)
        if t is None:
            raise FamilyError(f"test {test_id!r} is not registered")
        return dict(t.entry)

    def test_ids(self) -> List[str]:
        return list(self._tests)

    def test_record(self, test_id: str) -> Dict[str, Any]:
        """The stored threshold record of a test (section 3.4); None fields while its batch is open."""
        t = self._tests.get(test_id)
        if t is None:
            raise FamilyError(f"test {test_id!r} is not registered")
        e = t.entry
        close = self._batches[e["batch"]].close if not e["control"] else None
        return {
            "test_id": e["test_id"],
            "rule_id": e["rule_id"],
            "version": e["version"],
            "variant": e["variant"],
            "outcome": e["outcome"],
            "calendar_hash": e["calendar_hash"],
            "lineage_id": e["lineage_id"],
            "use_parents": e["use_parents"],
            "control": e["control"],
            "batch": e["batch"],
            "vintage_id": close["vintage"]["id"] if close else None,
            "n_b": close["n_b"] if close else None,
            "alpha_b": close["alpha_b"] if close else None,
            "a_test": close["a_test"] if close else None,
            "seal_bundle_sha256": close["seal_bundle_sha256"] if close else None,
            "lock_position": {"register": t.seq, "batch_close": close["seq"] if close else None},
        }

    def eligibility(
        self,
        test_id: str,
        vintage: Mapping[str, Any],
        *,
        first_look_calendars: Collection[str] = (),
    ) -> Eligibility:
        """Which verdicts a test may reach on a vintage (ADR-008 3.2 table).

        first_look_calendars holds the calendar hashes committed before the
        project's first look at a seen vintage (rule 7); only those tests may
        give E there, with flag seen_data.
        """
        t = self._tests.get(test_id)
        if t is None:
            raise FamilyError(f"test {test_id!r} is not registered")
        e = t.entry
        v = _vintage(vintage)
        vid = v["id"]
        none = dict(allow_s=False, allow_c=False, allow_e=False)
        if e["control"]:
            return Eligibility(test_id, vid, "control", numbers="control", flags=("control",), **none)
        closing = self._closing_on(vid)
        if closing is not None and closing["vintage"] != v:
            raise FamilyError(f"vintage {vid} differs from the one recorded when batch {closing['batch']} closed")

        def blocked(flag: str) -> Tuple[Tuple[str, str], ...]:
            return (("S", flag), ("C", flag), ("E", flag))

        if closing is None:
            flag = "batch_open" if self._batches[e["batch"]].close is None else "not_batch_vintage"
            return Eligibility(test_id, vid, flag, numbers="descriptive", flags=(flag,),
                               blocked=blocked(flag), batch=e["batch"], **none)
        if closing["batch"] != e["batch"]:
            if closing["batch"] in e["after_close_of"]:
                flag, row = "registered_after_unblinding", "after_close_same_vintage"
            else:
                flag, row = "not_batch_vintage", "not_batch_vintage"
            return Eligibility(test_id, vid, row, numbers="descriptive", flags=(flag,),
                               blocked=blocked(flag), batch=e["batch"], **none)
        a = closing["a_test"]
        if v["seen"]:
            e_ok = e["calendar_hash"] in set(first_look_calendars)
            return Eligibility(
                test_id, vid, "before_close_seen",
                allow_s=False, allow_c=False, allow_e=e_ok,
                numbers="confirmatory_e_only" if e_ok else "descriptive",
                flags=("seen_data",) if e_ok else (),
                blocked=(("S", "signal_on_seen_data"), ("C", "signal_on_seen_data"), ("E", "seen_data")),
                a_test=a, batch=e["batch"],
            )
        row = "before_close_unseen" if e["batch"] == 1 else "later_batch_fresh"
        return Eligibility(test_id, vid, row, allow_s=True, allow_c=True, allow_e=True,
                           numbers="confirmatory", a_test=a, batch=e["batch"])

    # ---------------------------------------------- closed results
    def record_batch_results(self, batch: int, results: bytes) -> Dict[str, Any]:
        """Hash the results file of a closed batch into the chain (once).

        Calling again with the same bytes returns the stored hash; other bytes
        raise ClosedBatchChangedError (a closed batch is never recomputed).
        """
        b = self._batches.get(batch)
        if b is None or b.close is None:
            raise FamilyError(f"batch {batch} is not closed")
        digest = _sha(bytes(results))
        if b.results_sha256 is not None:
            if b.results_sha256 != digest:
                raise ClosedBatchChangedError(
                    f"batch {batch}: results differ from those recorded ({b.results_sha256[:12]})"
                )
            return {"batch": batch, "results_sha256": digest}
        return self._append({"kind": "batch_results", "batch": batch, "results_sha256": digest})

    def verify_batch_results(self, batch: int, results: bytes) -> None:
        """Raise unless the bytes are exactly the recorded results of the batch."""
        b = self._batches.get(batch)
        if b is None or b.results_sha256 is None:
            raise FamilyError(f"batch {batch} has no recorded results")
        if _sha(bytes(results)) != b.results_sha256:
            raise ClosedBatchChangedError(f"batch {batch}: results file changed after it was recorded")

    # ---------------------------------------------- rules vs lock
    def check_against_rules(self, current: Iterable[Mapping[str, Any]]) -> None:
        """Raise LockMismatchError if the rule files and the lock disagree.

        current lists the tests built from the rule files now: test_id,
        calendar_hash and use_parents (id, version, sha256). A test not in the
        lock, a changed calendar, or a use: parent whose version or hash
        changed while the child keeps its version all fail: a parent edit
        needs a new child version (G-04). Tests in the lock but no longer in
        the files keep their place in their batch.
        """
        problems = []
        for c in current:
            tid = c.get("test_id")
            t = self._tests.get(tid)
            if t is None:
                problems.append(f"{tid}: not registered in the family lock")
                continue
            if c.get("calendar_hash") != t.entry["calendar_hash"]:
                problems.append(f"{tid}: calendar changed since registration; register a new version")
            try:
                now = _pin_parents(c.get("use_parents") or ())
            except UnpinnedUseError as exc:
                problems.append(f"{tid}: {exc}")
                continue
            was = {p["id"]: p for p in t.entry["use_parents"]}
            for p in now:
                old = was.get(p["id"])
                if old is None:
                    problems.append(f"{tid}: use parent {p['id']} not in the lock; re-version the child")
                elif (old["version"], old["sha256"]) != (p["version"], p["sha256"]):
                    problems.append(
                        f"{tid}: use parent {p['id']} changed ({old['version']}/{old['sha256'][:12]} -> "
                        f"{p['version']}/{p['sha256'][:12]}); re-version the child"
                    )
            for m in sorted(set(was) - {p["id"] for p in now}):
                problems.append(f"{tid}: use parent {m} removed; re-version the child")
        if problems:
            raise LockMismatchError("rule files and family lock disagree:\n  - " + "\n  - ".join(problems))


def _pin_parents(use_parents: Any) -> List[Dict[str, Any]]:
    """Normalise use: parents to {id, version, sha256} sorted by id; refuse unpinned ones.

    Accepts mappings or (id, version, sha256) tuples, such as the lineage of
    rules.predicates.compose.ResolvedUse.
    """
    out = []
    for p in use_parents or ():
        if isinstance(p, Mapping):
            pid, ver, sha = p.get("id"), p.get("version"), p.get("sha256")
        elif isinstance(p, (list, tuple)) and len(p) == 3:
            pid, ver, sha = p
        else:
            raise UnpinnedUseError(f"use parent {p!r}: give (id, version, sha256)")
        if not isinstance(pid, str) or not pid:
            raise UnpinnedUseError("use parent without id")
        if isinstance(ver, bool) or not isinstance(ver, int) or ver < 1:
            raise UnpinnedUseError(f"use parent {pid}: write use: {pid}@<version> (pinned)")
        if not isinstance(sha, str) or not _HEX64.match(sha):
            raise UnpinnedUseError(f"use parent {pid}: the parent's hash must be recorded in the lock")
        out.append({"id": pid, "version": ver, "sha256": sha})
    ids = [p["id"] for p in out]
    if len(ids) != len(set(ids)):
        raise UnpinnedUseError("a use parent is listed twice")
    return sorted(out, key=lambda p: p["id"])


# --------------------------------------------------- supportability (S-09)
def min_blocks_for_support(a_test: float, side: str) -> int:
    """Fewest used blocks whose exact sign-flip p can reach a_test.

    The smallest one-sided p of the exact sign-flip on k blocks is 2^-k; a
    two-sided test doubles it. So 9, 10 and 11 blocks at 2.0e-3, 1.0e-3 and
    6.7e-4 (ADR-008 3.3). There is no default side.
    """
    if side not in ("greater", "less", "two_sided"):
        raise FamilyError("side must be greater, less or two_sided (there is no default side)")
    a = float(a_test)
    if not 0 < a < 1:
        raise FamilyError("a_test must lie in (0, 1)")
    mult = 2.0 if side == "two_sided" else 1.0
    k = 0
    while mult * 2.0 ** (-k) > a:
        k += 1
    return k


def min_informative_for_limit(a: float) -> int:
    """ceil(log2(1/a)) informative blocks needed to print a limit at level a (2.2)."""
    a = float(a)
    if not 0 < a < 1:
        raise FamilyError("level must lie in (0, 1)")
    k = 0
    while 2.0 ** (-k) > a:
        k += 1
    return k


def supportability_table(tests: Iterable[Mapping[str, Any]], a_test: float) -> Dict[str, Any]:
    """Counts of tests that can support, can only limit, or are untestable at a_test.

    Each test gives test_id, side, k_eff, blocks_used (predicted blocks with a
    non-zero difference) and informative_at_sesoi (predicted I at r = SESOI;
    None when the outcome has no SESOI). The gate (WP-94) prints this before
    a batch closes, with a_test for the current n_b. Below K_eff 8 a test is
    untestable; a test that can support is not counted again as limit-only.
    """
    rows = []
    counts = {"support": 0, "limit_only": 0, "untestable": 0}
    need_limit = min_informative_for_limit(a_test)
    for t in tests:
        need_s = min_blocks_for_support(a_test, t["side"])
        i_sesoi = t.get("informative_at_sesoi")
        if float(t["k_eff"]) < K_EFF_MIN:
            cat = "untestable"
        elif int(t["blocks_used"]) >= need_s:
            cat = "support"
        elif i_sesoi is not None and int(i_sesoi) >= need_limit:
            cat = "limit_only"
        else:
            cat = "untestable"
        counts[cat] += 1
        rows.append({"test_id": t["test_id"], "category": cat, "blocks_needed_support": need_s,
                     "informative_needed_limit": need_limit})
    return {"a_test": float(a_test), "counts": counts, "rows": rows}


# --------------------------------------------------- clone attack (F3, F4)
def clone_attack_case(
    n_families: int = 2000,
    *,
    n_tests: int = 43,
    n_renamed: int = 5,
    n_variants: int = 6,
    n_use_children: int = 6,
    fresh: bool = False,
    seed: int = 0,
) -> Dict[str, int]:
    """Simulate the S-04 clone attack on null families (cases F3 and F4).

    Each family registers n_tests null tests, closes batch 1 on an unseen
    vintage and reads uniform p-values. The adversary then registers 17
    copies of the test with the smallest p: renamed files (same calendar),
    candidate variants of the same rule and use: children. On the old vintage
    each accepted copy reports that smallest p. With fresh=True an
    independent fresh vintage follows and batch 2 is confirmed on it, the
    copies perfectly correlated there (Bonferroni holds under any dependence).

    Returns counts: families, families with any false S, false S among the
    copies on the old vintage, copies accepted and refused. This exercises
    the registration and eligibility rules of this module; WP-98 repeats the
    case with real calendars through the whole pipeline.
    """
    rng = np.random.default_rng(seed)
    v1 = {"id": "v1", "confirm_period": {"start": "2000-01-01", "end": "2010-12-31"}, "seen": False}
    v2 = {"id": "v2", "confirm_period": {"start": "2011-01-01", "end": "2020-12-31"}, "seen": False}
    bundle = "0" * 64

    def new_cal() -> str:
        return hashlib.sha256(rng.bytes(16)).hexdigest()

    def final(test_id: str, vintage: Mapping[str, Any], p: float) -> str:
        el = lock.eligibility(test_id, vintage)
        cand = "S" if el.a_test is not None and passes(p, el.a_test) else "N"
        return limit_verdict(cand, el)[0]

    any_false = copies_s = accepted = refused = 0
    for _ in range(n_families):
        lock = FamilyLock(None, "sim")
        ids = [lock.register(rule_id=f"sim.r{i}", version=1, outcome="y", calendar_hash=new_cal())["test_id"]
               for i in range(n_tests)]
        lock.close_batch(vintage=v1, seal_bundle_sha256=bundle)
        p1 = rng.random(n_tests)
        false_s = any(final(t, v1, p) == "S" for t, p in zip(ids, p1))
        winner = lock.test(ids[int(np.argmin(p1))])
        p_win = float(p1.min())
        attempts = (
            [dict(rule_id=f"sim.renamed{k}", version=1, outcome="y", calendar_hash=winner["calendar_hash"])
             for k in range(n_renamed)]
            + [dict(rule_id=winner["rule_id"], version=1, outcome="y", variant=f"orb{k}",
                    calendar_hash=new_cal()) for k in range(n_variants)]
            + [dict(rule_id=f"sim.child{k}", version=1, outcome="y", calendar_hash=new_cal(),
                    use_parents=[(winner["rule_id"], 1, winner["calendar_hash"])]) for k in range(n_use_children)]
        )
        clones = []
        for kw in attempts:
            try:
                clones.append(lock.register(**kw)["test_id"])
                accepted += 1
            except FamilyError:
                refused += 1
        for c in clones:
            if final(c, v1, p_win) == "S":
                copies_s += 1
                false_s = True
        if fresh and clones:
            lock.close_batch(vintage=v2, seal_bundle_sha256=bundle)
            u = float(rng.random())
            if any(final(c, v2, u) == "S" for c in clones):
                false_s = True
        any_false += bool(false_s)
    return {"families": n_families, "families_any_false_s": any_false, "copies_false_s_old_vintage": copies_s,
            "copies_accepted": accepted, "copies_refused": refused}
