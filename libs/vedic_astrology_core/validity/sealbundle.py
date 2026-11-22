"""Seal bundle, outside timestamp and the confirm handle (ADR-008 4.2, WP-89).

Closes the remaining parts of strategy-audit finding S-05. The order the
code enforces is::

    seal_domain()                       issue_confirm_handle()
    1 clean tree, no legacy reader      1 not provisional, clean tree
    2 build the seal bundle             2 bundle bytes canonical, recomputed
    3 batch_close in the family lock      now equals the stamped one
      carries the bundle's SHA-256      3 family lock closes the batch with
    4 commit bundle + lock, push          this bundle hash
    5 stamp the HASH (only the hash)    4 calibration certificate still holds
      with OpenTimestamps; commit and   5 the .ots proof verifies: completed
      push the .ots proof                 Bitcoin attestation for this hash
                                        6 the commit that holds batch_close
                                          is an ancestor of the remote head
                                        7 confirm ledger chain and history
                                          intact; no entry with the same key
                                        8 one keyed entry per test appended
                                          AND committed; only then a handle

A completed attestation takes hours, so sealing and confirming are never the
same sitting (intended).

**OpenTimestamps is called through one function**, :func:`ots_client`. It is
not wired to the real client: owner decision H19 is pending, so the default
raises :class:`OtsNotConfiguredError` and nothing leaves the machine. Tests
replace it (``monkeypatch.setattr(sealbundle, "ots_client", fake)``). The
function receives only the 64-hex bundle hash (and, to verify, the proof
bytes it returned); no file, path or content of the repository.

**Confirm-period rows.** :func:`guarded` wraps a domain adapter. Without a
valid :class:`ConfirmHandle` for its domain, ``outcomes()``, ``catalogue()``
and ``mainshock_flags()`` return rows up to the explore end only; asking for
a later date raises :class:`ConfirmAccessError`; values that cannot be cut by
date (counts, totals, a ``confirm`` key) are withheld. A handle is a Python
object registered in this module when :func:`issue_confirm_handle` succeeds;
a handle built by hand is not registered and opens nothing. A provisional run
never gets a handle. The adapters' own methods are not changed here: a caller
that bypasses :func:`guarded` still reaches every row (open item for the
adapter files, ADR-008 4.1).

Old study pipelines that read confirm-period rows directly are listed in
:data:`LEGACY_CONFIRM_READERS`; :func:`seal_domain` refuses to close a batch
while a listed file for the domain still exists without the adapter-only
marker (ADR-008 4.1: moved behind the adapters or deleted before the first
batch close).

Keyed confirm ledger (ADR-008 4.1): one file,
``studies/validity/confirm_ledger.jsonl``, hash-chained (each line holds the
SHA-256 of the line before it). Key of a confirm entry: ``(domain,
dataset_sha256, period, lineage_id, version, variant, outcome)``; one entry
per key, for ever, searched in every ledger of the working tree and of git
history on any ref. ``dataset_sha256`` is recomputed from the snapshot files.

No thread is started here (G-13). Network is touched only by ``git push`` and
``git fetch`` against the named remote, and by :func:`ots_client` once wired.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from ..domains.base import GateHashError, verify_gate
from ..stats.seal import (
    ConfirmAlreadyRunError,
    DirtyTreeError,
    LedgerTamperedError,
    SealError,
    _git,
    _repo_ledger_entries,
    _repo_toplevel,
    require_clean_tree,
    verify_ledger,
)
from . import calibration
from .family import FamilyLock, canonical_bytes

__all__ = [
    "ADAPTER_ONLY_MARKER",
    "BUNDLE_SCHEMA",
    "DEFAULT_BUNDLE_DIR",
    "DEFAULT_LEDGER",
    "LEGACY_CONFIRM_READERS",
    "BundleMismatchError",
    "ConfirmAccessError",
    "ConfirmAlreadyRunError",
    "ConfirmHandle",
    "DirtyTreeError",
    "GateHashError",
    "GuardedAdapter",
    "LedgerTamperedError",
    "LegacyReaderError",
    "NotPublishedError",
    "OtsNotConfiguredError",
    "OtsProofError",
    "OtsResult",
    "ProvisionalRunError",
    "SealBundleError",
    "SealSources",
    "build_bundle",
    "bundle_problems",
    "bundle_sha256",
    "confirm_key",
    "guarded",
    "handle_is_valid",
    "issue_confirm_handle",
    "legacy_reader_problems",
    "ots_client",
    "seal_domain",
    "verify_chain",
]

BUNDLE_SCHEMA = 1
DEFAULT_LEDGER = "studies/validity/confirm_ledger.jsonl"
DEFAULT_BUNDLE_DIR = "studies/validity/seals"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
PathLike = Union[str, Path]

#: Text a legacy study file carries once it reads confirm rows only through
#: the adapters (or the file is deleted).
ADAPTER_ONLY_MARKER = "confirm-access: adapter-only (ADR-008 4.1)"

#: Old pipelines that read confirm-period rows of a domain's snapshots
#: directly (found by reading the code on 2026-11-22). Each must be moved
#: behind the adapters (and carry ADAPTER_ONLY_MARKER) or be deleted before
#: the domain's first batch close.
LEGACY_CONFIRM_READERS: Dict[str, Tuple[str, ...]] = {
    "earthquake": (
        "studies/earthquake/scripts/pipeline.py",  # period slices, confirmation table
        "studies/earthquake/scripts/robustness.py",  # holdout AUC on the confirm slice
        "studies/combinations/scripts/pipeline.py",  # earthquake catalogue, confirm slice
    ),
    "gold": (
        "libs/vedic_astrology_core/markets/study.py",  # confirm(), SPA in the confirm period
        "studies/gold_market/scripts/pipeline.py",
    ),
    "silver": (
        "libs/vedic_astrology_core/markets/study.py",
        "studies/silver_market/scripts/pipeline.py",
    ),
    "monsoon": (),
}


# ------------------------------------------------------------------ errors
class SealBundleError(SealError):
    """The seal bundle cannot be built or read."""


class BundleMismatchError(SealBundleError):
    """The bundle recomputed now differs from the stamped one (P7)."""


class OtsProofError(SealBundleError):
    """The .ots proof is missing, pending, for another hash or invalid (P8)."""


class OtsNotConfiguredError(OtsProofError):
    """The OpenTimestamps client is not wired (owner decision H19 pending)."""


class NotPublishedError(SealBundleError):
    """The commit holding batch_close is not on the public remote branch."""


class ProvisionalRunError(SealBundleError):
    """A provisional run asked for a confirm handle (P5)."""


class LegacyReaderError(SealBundleError):
    """An old pipeline still reads confirm rows outside the adapters."""


class ConfirmAccessError(SealBundleError):
    """A confirm-period row was asked for without a valid handle (P4)."""


# ----------------------------------------------------- OpenTimestamps seam
@dataclass(frozen=True)
class OtsResult:
    """What a verifier reports for one proof."""

    status: str  # "complete", "pending" or "invalid"
    digest: str
    block_height: Optional[int] = None
    attested_utc: Optional[str] = None


def ots_client(action: str, digest: str, proof: Optional[bytes] = None) -> Any:
    """The one call to OpenTimestamps; tests replace this function.

    ``action="stamp"``: submit ``digest`` (64-hex SHA-256 of the bundle) and
    return the proof bytes. ``action="verify"``: check ``proof`` for
    ``digest`` and return an :class:`OtsResult` (or a mapping with its
    fields). Only the hash is ever passed.

    Not wired: owner decision H19 (OpenTimestamps as the outside timestamp)
    is pending, so this raises and nothing is sent.
    """
    raise OtsNotConfiguredError(
        "the OpenTimestamps client is not wired (owner decision H19 pending); "
        "no outside timestamp can be made or verified, so no confirm handle is issued"
    )


def _ots(action: str, digest: str, proof: Optional[bytes] = None) -> Any:
    if not isinstance(digest, str) or not _HEX64.match(digest):
        raise SealBundleError("only a 64-hex SHA-256 is ever sent to the timestamp service")
    return globals()["ots_client"](action, digest, proof)


def _as_ots_result(value: Any) -> OtsResult:
    if isinstance(value, OtsResult):
        return value
    if isinstance(value, Mapping):
        return OtsResult(
            status=str(value.get("status")),
            digest=str(value.get("digest")),
            block_height=value.get("block_height"),
            attested_utc=value.get("attested_utc"),
        )
    raise OtsProofError(f"the timestamp verifier returned {type(value).__name__}, not a result")


# ------------------------------------------------------------------ helpers
def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line_sha(line: str) -> str:
    return _sha_bytes(line.encode("utf-8"))


def _top(repo_root: PathLike) -> Path:
    top = _repo_toplevel(repo_root)
    if top is None:
        raise SealBundleError(f"{repo_root} is not a git checkout")
    return top.resolve()


def _rel(top: Path, path: PathLike) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = top / p
    try:
        return p.resolve().relative_to(top).as_posix()
    except ValueError as exc:
        raise SealBundleError(f"{path} is outside the repository") from exc


def _hash_file(top: Path, rel: str) -> str:
    p = top / rel
    if not p.is_file():
        raise SealBundleError(f"{rel} does not exist")
    return _sha_bytes(p.read_bytes())


def _hash_or_none(top: Path, rel: str) -> Optional[str]:
    p = top / rel
    return _sha_bytes(p.read_bytes()) if p.is_file() else None


def _git_ok(args: Sequence[str], top: Path, what: str) -> str:
    out = _git(args, top)
    if out.returncode != 0:
        raise SealBundleError(f"{what} failed: {(out.stderr or out.stdout).strip()}")
    return out.stdout.strip()


def _commit_paths(top: Path, rels: Sequence[str], message: str) -> str:
    """Commit only these paths (other sessions may edit the same checkout)."""
    _git_ok(["add", "--", *rels], top, "git add")
    _git_ok(["commit", "-q", "-m", message, "--", *rels], top, "git commit")
    return _git_ok(["rev-parse", "HEAD"], top, "git rev-parse")


def _push(top: Path, remote: str, branch: str) -> None:
    _git_ok(["push", "-q", remote, f"HEAD:refs/heads/{branch}"], top, f"git push {remote} {branch}")


def _is_ancestor(top: Path, commit: str, ref: str) -> bool:
    return _git(["merge-base", "--is-ancestor", commit, ref], top).returncode == 0


# ------------------------------------------------------------ ledger chain
def verify_chain(path: PathLike) -> List[Dict[str, Any]]:
    """Parse a hash-chained ledger; raise :class:`LedgerTamperedError` on a broken link (P9).

    Each line's ``prev_sha256`` must be the SHA-256 of the line before it
    (None on the first line). A missing file is an empty ledger.
    """
    p = Path(path)
    if not p.exists():
        return []
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out: List[Dict[str, Any]] = []
    prev: Optional[str] = None
    for n, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LedgerTamperedError(f"{p}:{n} is not valid JSON") from exc
        if not isinstance(entry, dict) or entry.get("prev_sha256") != prev:
            raise LedgerTamperedError(f"{p}:{n}: hash chain broken (prev_sha256 does not match line {n - 1})")
        out.append(entry)
        prev = _line_sha(line)
    return out


def _ledger_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def confirm_key(
    domain: str, dataset_sha256: str, period: Mapping[str, str], test: Mapping[str, Any]
) -> Dict[str, Any]:
    """The ledger key of one confirm (ADR-008 4.1)."""
    return {
        "domain": domain,
        "dataset_sha256": dataset_sha256,
        "period": {"start": period["start"], "end": period["end"]},
        "lineage_id": test["lineage_id"],
        "version": test["version"],
        "variant": test["variant"],
        "outcome": test["outcome"],
    }


# ---------------------------------------------------------- legacy readers
def legacy_reader_problems(repo_root: PathLike, domain: str) -> List[str]:
    """Listed old pipelines of the domain that still exist without the adapter-only marker."""
    top = Path(repo_root)
    problems = []
    for rel in LEGACY_CONFIRM_READERS.get(domain, ()):
        p = top / rel
        if p.is_file() and ADAPTER_ONLY_MARKER not in p.read_text(encoding="utf-8", errors="replace"):
            problems.append(rel)
    return problems


# ------------------------------------------------------------------ bundle
@dataclass(frozen=True)
class SealSources:
    """Every input the seal bundle hashes. Paths are inside the repository.

    ``gates`` maps each test id of the open batch to its written
    ``gate.json``. ``outcome_types`` are the calibration outcome types the
    batch's tests use; the certificate is checked for each at confirm.
    """

    domain: str
    plan: PathLike
    family_lock: PathLike
    gates: Mapping[str, PathLike]
    rule_files: Sequence[PathLike]
    datasets: Sequence[PathLike]
    environment_lock: PathLike
    ephemeris_files: Sequence[PathLike]
    certificate: PathLike
    vintage: Mapping[str, Any]
    outcome_types: Sequence[str] = ()
    ledger: PathLike = DEFAULT_LEDGER


def _hashed(top: Path, paths: Sequence[PathLike], what: str) -> List[Dict[str, str]]:
    rels = sorted({_rel(top, p) for p in paths})
    if not rels:
        raise SealBundleError(f"the seal bundle needs at least one {what}")
    return [{"path": r, "sha256": _hash_file(top, r)} for r in rels]


def build_bundle(repo_root: PathLike, src: SealSources) -> Dict[str, Any]:
    """The seal bundle of the domain's open batch (ADR-008 4.2 step 1). Reads no outcome.

    Commit id, plan hash, family lock head, confirm ledger head, the batch's
    test ids with calendar hashes and gate.json hashes, rule-file hashes,
    dataset hashes, environment lock hash, ephemeris file hashes and the
    calibration certificate hash. Every hash is computed here from the files;
    no caller-supplied hash is accepted.
    """
    top = _top(repo_root)
    if not isinstance(src.domain, str) or not src.domain:
        raise SealBundleError("a seal bundle belongs to one named domain")
    for ot in src.outcome_types:
        if ot not in calibration.OUTCOME_TYPES:
            raise SealBundleError(f"unknown outcome type {ot!r}")
    lock_rel = _rel(top, src.family_lock)
    if not (top / lock_rel).is_file():
        raise SealBundleError(f"family lock {lock_rel} does not exist")
    lock = FamilyLock(top / lock_rel, src.domain)
    lock.verify()
    batch = lock.open_batch()
    test_ids = lock.batch_tests(batch)
    if not test_ids:
        raise SealBundleError(f"batch {batch} of {src.domain} has no tests")
    gates = {str(k): _rel(top, v) for k, v in src.gates.items()}
    if sorted(gates) != sorted(test_ids):
        raise SealBundleError(
            f"gate files must cover exactly the batch's tests: missing "
            f"{sorted(set(test_ids) - set(gates))}, extra {sorted(set(gates) - set(test_ids))}"
        )
    tests = []
    for tid in test_ids:
        e = lock.test(tid)
        rec = verify_gate(_hash_file(top, gates[tid]), top / gates[tid])
        tests.append({
            "test_id": tid,
            "rule_id": e["rule_id"],
            "version": e["version"],
            "variant": e["variant"],
            "outcome": e["outcome"],
            "calendar_hash": e["calendar_hash"],
            "lineage_id": e["lineage_id"],
            "gate": {"path": gates[tid], "sha256": rec.sha256},
        })
    ledger_rel = _rel(top, src.ledger)
    lines = _ledger_lines(top / ledger_rel)
    verify_chain(top / ledger_rel)
    plan_rel = _rel(top, src.plan)
    env_rel = _rel(top, src.environment_lock)
    cert_rel = _rel(top, src.certificate)
    eph = sorted({_rel(top, p) for p in src.ephemeris_files})
    return {
        "kind": "seal_bundle",
        "schema": BUNDLE_SCHEMA,
        "domain": src.domain,
        "commit": _git_ok(["rev-parse", "HEAD"], top, "git rev-parse"),
        "batch": batch,
        "vintage": dict(src.vintage),
        "plan": {"path": plan_rel, "sha256": _hash_file(top, plan_rel)},
        "family_lock": {"path": lock_rel, "head": lock.head()},
        "confirm_ledger": {"path": ledger_rel, "head": _line_sha(lines[-1]) if lines else None},
        "tests": tests,
        "rule_files": _hashed(top, src.rule_files, "rule file"),
        "datasets": _hashed(top, src.datasets, "dataset"),
        "environment_lock": {"path": env_rel, "sha256": _hash_file(top, env_rel)},
        "ephemeris": [{"path": r, "sha256": _hash_file(top, r)} for r in eph],
        "certificate": {"path": cert_rel, "sha256": _hash_file(top, cert_rel)},
        "outcome_types": sorted(set(src.outcome_types)),
    }


def _bundle_bytes(bundle: Mapping[str, Any]) -> bytes:
    return canonical_bytes(dict(bundle)) + b"\n"


def bundle_sha256(bundle: Mapping[str, Any]) -> str:
    """SHA-256 of the bundle file's bytes (canonical JSON plus a newline)."""
    return _sha_bytes(_bundle_bytes(bundle))


def _read_bundle(path: Path) -> Tuple[Dict[str, Any], str]:
    if not path.is_file():
        raise SealBundleError(f"no seal bundle at {path}")
    data = path.read_bytes()
    try:
        bundle = json.loads(data)
    except ValueError as exc:
        raise BundleMismatchError(f"{path} is not JSON") from exc
    if not isinstance(bundle, dict) or bundle.get("kind") != "seal_bundle":
        raise BundleMismatchError(f"{path} is not a seal bundle")
    if _bundle_bytes(bundle) != data:
        raise BundleMismatchError(f"{path} is not in canonical form (edited after sealing?)")
    return bundle, _sha_bytes(data)


def _dataset_key_hash(datasets: Sequence[Mapping[str, str]]) -> str:
    hashes = sorted(d["sha256"] for d in datasets)
    return hashes[0] if len(hashes) == 1 else _sha_bytes("|".join(hashes).encode("utf-8"))


def _close_entry(lock: FamilyLock, sha: str) -> Optional[Dict[str, Any]]:
    for b in lock.closed_batches():
        close = lock.batch_close_entry(b)
        if close and close.get("seal_bundle_sha256") == sha:
            return close
    return None


def bundle_problems(repo_root: PathLike, bundle: Mapping[str, Any], sha: str) -> List[str]:
    """Every difference between the stamped bundle and the repository now (empty: equal).

    Content hashes are recomputed from the files the bundle names. The family
    lock must hold the batch_close carrying ``sha``, written directly after
    the recorded lock head, for exactly the recorded tests and calendars. The
    recorded commit must be an ancestor of HEAD; the recorded confirm-ledger
    head must still be a line of the ledger.
    """
    top = _top(repo_root)
    out: List[str] = []

    def same(rel: str, want: Optional[str], what: str) -> None:
        now = _hash_or_none(top, rel)
        if now != want:
            out.append(f"{what} {rel}: {'missing' if now is None else 'changed'}")

    if bundle.get("schema") != BUNDLE_SCHEMA:
        return [f"bundle schema {bundle.get('schema')!r} is not {BUNDLE_SCHEMA}"]
    same(bundle["plan"]["path"], bundle["plan"]["sha256"], "plan")
    for kind, what in (("rule_files", "rule file"), ("datasets", "dataset"), ("ephemeris", "ephemeris file")):
        for item in bundle.get(kind, []):
            same(item["path"], item["sha256"], what)
    same(bundle["environment_lock"]["path"], bundle["environment_lock"]["sha256"], "environment lock")
    same(bundle["certificate"]["path"], bundle["certificate"]["sha256"], "calibration certificate")
    for t in bundle.get("tests", []):
        same(t["gate"]["path"], t["gate"]["sha256"], f"gate of {t['test_id']}")
    commit = bundle.get("commit")
    if not isinstance(commit, str) or not _is_ancestor(top, commit, "HEAD"):
        out.append(f"bundle commit {commit} is not an ancestor of HEAD")
    head = bundle["confirm_ledger"]["head"]
    led_lines = _ledger_lines(top / bundle["confirm_ledger"]["path"])
    if head is not None and head not in {_line_sha(ln) for ln in led_lines}:
        out.append("confirm ledger no longer holds the line the bundle recorded as its head")
    try:
        lock = FamilyLock(top / bundle["family_lock"]["path"], bundle["domain"])
        lock.verify()
    except Exception as exc:  # noqa: BLE001 - any lock failure is a mismatch
        out.append(f"family lock {bundle['family_lock']['path']}: {exc}")
        return out
    close = _close_entry(lock, sha)
    if close is None:
        out.append("no batch_close in the family lock carries this bundle hash")
        return out
    if close["batch"] != bundle["batch"]:
        out.append(f"batch_close is for batch {close['batch']}, bundle for {bundle['batch']}")
    if close["prev_sha256"] != bundle["family_lock"]["head"]:
        out.append("batch_close does not follow the lock head recorded in the bundle")
    if close["test_ids"] != [t["test_id"] for t in bundle["tests"]]:
        out.append("batch_close test ids differ from the bundle's")
    if close.get("plan_sha256") not in (None, bundle["plan"]["sha256"]):
        out.append("batch_close plan hash differs from the bundle's")
    for t in bundle["tests"]:
        try:
            e = lock.test(t["test_id"])
        except Exception:  # noqa: BLE001
            out.append(f"{t['test_id']} is not registered in the lock")
            continue
        for k in ("calendar_hash", "lineage_id", "version", "variant", "outcome", "rule_id"):
            if e[k] != t[k]:
                out.append(f"{t['test_id']}: {k} differs from the lock")
    return out


# -------------------------------------------------------------------- seal
def seal_domain(
    repo_root: PathLike,
    src: SealSources,
    *,
    remote: str = "origin",
    branch: str = "main",
    bundle_dir: PathLike = DEFAULT_BUNDLE_DIR,
) -> Dict[str, Any]:
    """``astro-validity seal <domain>``: bundle, batch_close, commit, push, stamp (4.2 steps 1-2).

    Refuses a dirty tree and a domain whose legacy confirm readers remain.
    Commits only the bundle, the family lock and the proof file.
    Returns the bundle path, its hash, the closing commit and the proof path.
    """
    top = _top(repo_root)
    require_clean_tree(top, provisional=False)
    legacy = legacy_reader_problems(top, src.domain)
    if legacy:
        raise LegacyReaderError(
            f"{src.domain}: old pipelines still read confirm rows outside the adapters: "
            + ", ".join(legacy) + "; move them behind the adapters or delete them first"
        )
    bundle = build_bundle(top, src)
    rel_dir = _rel(top, bundle_dir)
    bundle_rel = f"{rel_dir}/{src.domain}/batch-{bundle['batch']}.json"
    bpath = top / bundle_rel
    if bpath.exists():
        raise SealBundleError(f"{bundle_rel} already exists; a batch is sealed once")
    data = _bundle_bytes(bundle)
    sha = _sha_bytes(data)
    bpath.parent.mkdir(parents=True, exist_ok=True)
    bpath.write_bytes(data)
    lock = FamilyLock(top / bundle["family_lock"]["path"], src.domain)
    lock.close_batch(vintage=src.vintage, seal_bundle_sha256=sha, plan_sha256=bundle["plan"]["sha256"])
    commit = _commit_paths(
        top, [bundle_rel, bundle["family_lock"]["path"]],
        f"seal({src.domain}): close batch {bundle['batch']}, bundle {sha[:12]}",
    )
    _push(top, remote, branch)
    proof = _ots("stamp", sha)
    if not isinstance(proof, (bytes, bytearray)) or not proof:
        raise OtsProofError("the timestamp client returned no proof bytes")
    ots_rel = bundle_rel + ".ots"
    (top / ots_rel).write_bytes(bytes(proof))
    _commit_paths(top, [ots_rel], f"seal({src.domain}): OpenTimestamps proof for {sha[:12]}")
    _push(top, remote, branch)
    return {"bundle": bundle_rel, "bundle_sha256": sha, "commit": commit, "ots": ots_rel,
            "batch": bundle["batch"]}


# ------------------------------------------------------------------ handle
_ISSUED: Dict[str, "ConfirmHandle"] = {}


@dataclass(frozen=True)
class ConfirmHandle:
    """Proof that the confirm gate passed; the only key to confirm-period rows."""

    domain: str
    batch: int
    bundle_sha256: str
    bundle_path: str
    ots_path: str
    block_height: int
    vintage_id: str
    period: Tuple[str, str]
    test_ids: Tuple[str, ...]
    ledger_commit: str
    token: str = field(repr=False, compare=False)

    def footer(self) -> Dict[str, Any]:
        """Record for the run manifest and every card footer (4.2 step 4)."""
        return {
            "seal_bundle": self.bundle_path,
            "seal_bundle_sha256": self.bundle_sha256,
            "ots_proof": self.ots_path,
            "bitcoin_block_height": self.block_height,
            "confirm_ledger_commit": self.ledger_commit,
        }


def handle_is_valid(handle: Any, domain: Optional[str] = None) -> bool:
    """True for a handle this module issued (for ``domain``, when given)."""
    if not isinstance(handle, ConfirmHandle):
        return False
    if _ISSUED.get(handle.token) is not handle:
        return False
    return domain is None or handle.domain == domain


def issue_confirm_handle(
    repo_root: PathLike,
    bundle_path: PathLike,
    *,
    remote: str = "origin",
    branch: str = "main",
    provisional: bool = False,
    now: Optional[datetime] = None,
) -> ConfirmHandle:
    """``astro-validity confirm <domain>``: every check of 4.2 step 3, the keyed ledger, then a handle."""
    if not isinstance(provisional, bool):
        raise TypeError("provisional must be a bool")
    if provisional:
        raise ProvisionalRunError("a provisional run never gets a confirm handle")
    top = _top(repo_root)
    require_clean_tree(top, provisional=False)
    brel = _rel(top, bundle_path)
    bundle, sha = _read_bundle(top / brel)
    problems = bundle_problems(top, bundle, sha)
    if problems:
        raise BundleMismatchError("seal bundle differs from the repository: " + "; ".join(problems))
    for ot in bundle.get("outcome_types") or [None]:
        try:
            calibration.check_certificate(top / bundle["certificate"]["path"], top, ot)
        except calibration.CertificateError as exc:
            raise SealBundleError(f"calibration certificate refuses the confirm: {exc}") from exc
    ots_rel = brel + ".ots"
    if not (top / ots_rel).is_file():
        raise OtsProofError(f"no OpenTimestamps proof at {ots_rel}")
    res = _as_ots_result(_ots("verify", sha, (top / ots_rel).read_bytes()))
    if res.digest != sha:
        raise OtsProofError("the proof attests another hash than this bundle's")
    if res.status != "complete":
        raise OtsProofError(f"the proof is {res.status!r}, not a completed Bitcoin attestation")
    if isinstance(res.block_height, bool) or not isinstance(res.block_height, int) or res.block_height <= 0:
        raise OtsProofError("the proof names no Bitcoin block height")
    lock_rel = bundle["family_lock"]["path"]
    added = _git(["log", "--format=%H", "-S", sha, "--", lock_rel], top)
    commits = added.stdout.split() if added.returncode == 0 else []
    if not commits:
        raise NotPublishedError("no commit holds the batch_close of this bundle")
    close_commit = commits[-1]  # the oldest commit whose diff added the hash
    _git_ok(["fetch", "-q", remote, branch], top, f"git fetch {remote} {branch}")
    remote_head = _git_ok(["rev-parse", "FETCH_HEAD"], top, "git rev-parse FETCH_HEAD")
    if not _is_ancestor(top, close_commit, remote_head):
        raise NotPublishedError(
            f"the batch_close commit {close_commit[:12]} is not on {remote}/{branch}; push it first"
        )

    lock = FamilyLock(top / lock_rel, bundle["domain"])
    close = _close_entry(lock, sha)
    period = dict(close["vintage"]["confirm_period"])
    ledger_rel = bundle["confirm_ledger"]["path"]
    ledger = top / ledger_rel
    local = verify_chain(ledger)  # P9
    verify_ledger(ledger, top)  # P2: committed lines removed
    dataset = _dataset_key_hash(bundle["datasets"])
    keys = [(t, confirm_key(bundle["domain"], dataset, period, t)) for t in bundle["tests"]]
    prior = [(str(ledger_rel), e) for e in local] + _repo_ledger_entries(top)
    for t, key in keys:
        for where, e in prior:
            if isinstance(e, dict) and e.get("kind", "confirm") == "confirm" and e.get("key") == key:
                raise ConfirmAlreadyRunError(
                    f"{where} already records a confirm of {key['domain']} lineage "
                    f"{key['lineage_id'][:12]} ({key['outcome']}, {key['variant']}, v{key['version']}) "
                    f"on this dataset and period (as {e.get('test_id')!r}); one confirm per key"
                )
    when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds")
    head_commit = _git_ok(["rev-parse", "HEAD"], top, "git rev-parse")
    lines = _ledger_lines(ledger)
    new = []
    for t, key in keys:
        entry = {
            "kind": "confirm",
            "key": key,
            "test_id": t["test_id"],
            "principle_id": t["test_id"],
            "identity": [f"lineage_id:{key['lineage_id']}"],
            "batch": bundle["batch"],
            "bundle_sha256": sha,
            "bitcoin_block_height": res.block_height,
            "commit": head_commit,
            "utc": when,
            "prev_sha256": _line_sha(lines[-1]) if lines else None,
        }
        line = json.dumps(entry, sort_keys=True)
        lines.append(line)
        new.append(line)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as fh:
        for line in new:
            fh.write(line + "\n")
    # No handle before the entries are committed (P2): a failure here leaves no handle.
    ledger_commit = _commit_paths(
        top, [ledger_rel], f"confirm({bundle['domain']}): batch {bundle['batch']}, bundle {sha[:12]}"
    )
    handle = ConfirmHandle(
        domain=bundle["domain"],
        batch=int(bundle["batch"]),
        bundle_sha256=sha,
        bundle_path=brel,
        ots_path=ots_rel,
        block_height=int(res.block_height),
        vintage_id=str(close["vintage"]["id"]),
        period=(period["start"], period["end"]),
        test_ids=tuple(t["test_id"] for t in bundle["tests"]),
        ledger_commit=ledger_commit,
        token=secrets.token_hex(16),
    )
    _ISSUED[handle.token] = handle
    return handle


# ------------------------------------------------------------------- guard
def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return date(int(value), 12, 31)
    return pd.Timestamp(value).date()


def _dates(values: Any) -> np.ndarray:
    """Calendar dates of a time column, a date index or a yearly grid."""
    if isinstance(values, pd.Index) and not isinstance(values, pd.DatetimeIndex) \
            and pd.api.types.is_integer_dtype(values):  # a yearly grid (monsoon)
        return np.array([date(int(y), 1, 1) for y in values], dtype=object)
    ts = pd.to_datetime(pd.Series(list(values)), utc=True)
    return np.array([t.date() for t in ts], dtype=object)


_WITHHELD = object()


class GuardedAdapter:
    """A domain adapter seen through the confirm gate (ADR-008 4.1, P4).

    Without a handle valid for the adapter's domain every returned row ends
    at the explore end: frames with a ``time`` column or a date index are
    filtered, arrays on the grid are cut to the explore bars, values that
    cannot be cut by date (counts, totals, any ``confirm`` key) are withheld
    and listed in :attr:`withheld`. Asking for a date after the explore end
    raises :class:`ConfirmAccessError`.
    """

    def __init__(self, adapter: Any, handle: Optional[ConfirmHandle] = None) -> None:
        self._adapter = adapter
        domain = getattr(adapter, "domain", "") or ""
        if handle is not None and not handle_is_valid(handle, domain):
            raise ConfirmAccessError(f"the handle is not a confirm handle issued for {domain!r}")
        self.handle = handle
        self.withheld: List[str] = []

    @property
    def domain(self) -> str:
        return getattr(self._adapter, "domain", "")

    @property
    def confirm_open(self) -> bool:
        return self.handle is not None and handle_is_valid(self.handle, self.domain)

    def explore_end(self) -> date:
        return self._adapter.periods().explore[1]

    # -- outcome-free entry points pass through --------------------------
    def grid(self) -> Any:
        return self._adapter.grid()

    def calendar_context(self) -> Any:
        return self._adapter.calendar_context()

    def periods(self) -> Any:
        return self._adapter.periods()

    def dataset(self) -> Any:
        return self._adapter.dataset()

    # -- gated entry points ----------------------------------------------
    def _check_until(self, until: Any) -> None:
        if until is not None and not self.confirm_open and _to_date(until) > self.explore_end():
            raise ConfirmAccessError(
                f"{self.domain}: rows after the explore end {self.explore_end()} need a confirm handle"
            )

    def _n_explore_bars(self) -> int:
        return int((_dates(self._adapter.grid()) <= self.explore_end()).sum())

    def _cut(self, value: Any, path: str) -> Any:
        end = self.explore_end()
        if isinstance(value, pd.DataFrame):
            if "time" in value.columns:
                return value.loc[_dates(value["time"]) <= end]
            if isinstance(value.index, pd.DatetimeIndex):
                return value.loc[_dates(value.index) <= end]
        if isinstance(value, pd.Series) and isinstance(value.index, pd.DatetimeIndex):
            return value.loc[_dates(value.index) <= end]
        if isinstance(value, np.ndarray) and value.ndim >= 1 and value.shape[0] == len(self._adapter.grid()):
            return value[: self._n_explore_bars()]
        if isinstance(value, Mapping):
            out = {}
            for k, v in value.items():
                sub = f"{path}.{k}" if path else str(k)
                if str(k).lower() in ("confirm", "full", "all"):
                    self.withheld.append(sub)
                    continue
                cut = self._cut(v, sub)
                if cut is not _WITHHELD:
                    out[k] = cut
            return out
        if isinstance(value, (list, tuple)):
            items = [self._cut(v, f"{path}[{i}]") for i, v in enumerate(value)]
            items = [v for v in items if v is not _WITHHELD]
            return tuple(items) if isinstance(value, tuple) else items
        if isinstance(value, str) or value is None or callable(value):
            return value
        self.withheld.append(path or "<value>")
        return _WITHHELD

    def _guard(self, value: Any, path: str) -> Any:
        if self.confirm_open:
            return value
        out = self._cut(value, path)
        return None if out is _WITHHELD else out

    def outcomes(self, gate: Any = None, *, gate_path: Optional[PathLike] = None, until: Any = None) -> Any:
        verify_gate(gate, gate_path)  # P3 before anything is read
        self._check_until(until)
        return self._guard(self._adapter.outcomes(gate, gate_path=gate_path), "outcomes")

    def controls(self, gate: Any = None, *, gate_path: Optional[PathLike] = None) -> Any:
        verify_gate(gate, gate_path)
        return self._guard(self._adapter.controls(gate, gate_path=gate_path), "controls")

    def catalogue(self, until: Any = None) -> Any:
        self._check_until(until)
        return self._guard(self._adapter.catalogue(), "catalogue")

    def mainshock_flags(self, cat: Optional[pd.DataFrame] = None, until: Any = None) -> Any:
        self._check_until(until)
        if not self.confirm_open:
            if cat is not None and "time" in cat.columns and (_dates(cat["time"]) > self.explore_end()).any():
                raise ConfirmAccessError(f"{self.domain}: catalogue rows after the explore end need a handle")
            if cat is None:
                full = self._adapter.catalogue()
                frame = full[0] if isinstance(full, tuple) else full
                cat = self._cut(frame, "catalogue")
        return self._guard(self._adapter.mainshock_flags(cat), "mainshock_flags")


def guarded(adapter: Any, handle: Optional[ConfirmHandle] = None) -> GuardedAdapter:
    """The adapter seen through the confirm gate; explore rows only without a valid handle."""
    return GuardedAdapter(adapter, handle)
