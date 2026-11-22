"""Run seal: results from a clean tree, and one confirm per plan lineage.

ADR-004 D-2 (review flaw C2). Two guards:

* :func:`require_clean_tree` refuses a non-provisional run unless the
  working tree is a git checkout with no modified, staged or untracked
  (non-ignored) files. A run that is explicitly flagged provisional is let
  through and is stamped ``provisional: true``. There is deliberately no
  environment variable or other side door: provisional is an argument.
* :func:`begin_confirm` appends one entry to the append-only ledger
  ``<study_dir>/confirm_ledger.jsonl`` (ADR-007: ``studies/validity/``) with
  plan hash, data hash, commit, UTC time, period, lineage, principle id, the
  hash of the previous line (hash chain) and an ``external_timestamp``
  placeholder. It raises if a confirm of the same key is recorded in ANY
  ledger of the repository, in the working tree or in git history on any
  ref (code audit M4, strategy audit S-05).

Confirm key: (principle id, plan lineage). Principle id None is a confirm of
the whole plan and collides with every principle of the lineage. The lineage
is matched by identity tokens, any one of which collides: the plan's
``lineage`` field (declare it: it moves with a copied study), its ``study``
and ``id`` fields, its repository path and the SHA-256 of its bytes. So
editing the plan or bumping its version (same path), renaming the study
(same path or same lineage) or copying the folder (same bytes, same study,
same lineage) does not open a second confirm. Deleting or truncating a ledger
that was ever committed is detected from git history.

Confirm ledgers are not run inputs: :func:`tree_state` ignores an added or
modified ``confirm_ledger.jsonl`` (not a deleted one), so writing the entry
does not make the confirm run itself provisional (code audit M1).

External timestamp: the entry carries ``external_timestamp: null``. The
owner can stamp the entry outside the repository (OpenTimestamps, Zenodo,
OSF) and record the receipt with :func:`record_external_timestamp`, which
appends a separate line (ledger lines are never edited).

The confirm window comes from the plan (``periods.confirm_start`` /
``periods.confirm_end``, ``periods.confirm: {start, end}`` or
``split.confirm: [start, end]``; end else ``data.end``), never from the clock.
The entry is written before the confirm computes anything, so a confirm that
crashes still counts as spent.

Seal stamp (ADR-008 9.2): :class:`SealedRun` adds the interpreter, the hash
of ``ops/requirements.lock.txt`` (refusing installed versions that differ),
the ephemeris model with the hash of every ephemeris file, and the path and
hash of every file the run opened (an audit hook on ``open``). A sealed run
fails if it read a file git does not track, other than snapshots listed in
``data/snapshot_index.json``, or if it started a thread (G-13).
:func:`load_study_modules` imports study scripts by file path under unique
module names (G-03).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import re
import site
import subprocess
import sys
import types
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import yaml

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata  # type: ignore

PathLike = Union[str, Path]

LEDGER_NAME = "confirm_ledger.jsonl"


class SealError(RuntimeError):
    """A run would break the seal (dirty tree, second confirm, tampering)."""


class DirtyTreeError(SealError):
    """Non-provisional run from a tree that is not a clean git checkout."""


class ConfirmAlreadyRunError(SealError):
    """The plan lineage already has a confirm in its ledger."""


class LedgerTamperedError(SealError):
    """The ledger lost entries that git history shows it once had."""


# --------------------------------------------------------------------- git


def _git(args: Sequence[str], cwd: PathLike) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=False
    )


def _repo_toplevel(repo_root: Optional[PathLike]) -> Optional[Path]:
    cwd = Path(repo_root) if repo_root is not None else Path.cwd()
    try:
        out = _git(["rev-parse", "--show-toplevel"], cwd)
    except OSError:
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return Path(out.stdout.strip())


def _porcelain_path(line: str) -> str:
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip().strip('"')


def _is_ledger_append(line: str) -> bool:
    """An added or modified confirm ledger; a deletion still counts as dirty."""
    return Path(_porcelain_path(line)).name == LEDGER_NAME and "D" not in line[:2]


def tree_state(repo_root: Optional[PathLike] = None) -> Dict[str, Any]:
    """Return ``{"commit", "dirty", "changes"}`` counting untracked files.

    Outside git (or with no commit yet) ``commit`` and ``dirty`` are None.
    ``changes`` lists the porcelain lines that make the tree dirty. An added
    or modified ``confirm_ledger.jsonl`` is not a change: the ledger is a log
    of runs, never an input of one (a deleted ledger still counts).
    This is the one definition of dirty (manifest, seal, mundane writer).
    """
    top = _repo_toplevel(repo_root)
    if top is None:
        return {"commit": None, "dirty": None, "changes": []}
    head = _git(["rev-parse", "--verify", "HEAD"], top)
    if head.returncode != 0:
        return {"commit": None, "dirty": None, "changes": []}
    status = _git(["status", "--porcelain", "--untracked-files=all"], top)
    if status.returncode != 0:
        return {"commit": head.stdout.strip(), "dirty": None, "changes": []}
    changes = [ln for ln in status.stdout.splitlines()
               if ln.strip() and not _is_ledger_append(ln)]
    return {"commit": head.stdout.strip(), "dirty": bool(changes), "changes": changes}


def require_clean_tree(
    repo_root: Optional[PathLike] = None, *, provisional: bool = False
) -> Dict[str, Any]:
    """Raise unless the tree is clean or the run is flagged provisional.

    Returns the seal stamp ``{"commit", "dirty", "provisional"}`` to be
    written into results and manifests. A provisional run always gets
    ``provisional: True``; a non-provisional run gets it False only from a
    clean git checkout. Untracked files that git does not ignore count as
    dirty (they can change what the run imports or reads).
    """
    if not isinstance(provisional, bool):
        raise TypeError("provisional must be a bool")
    state = tree_state(repo_root)
    stamp = {"commit": state["commit"], "dirty": state["dirty"], "provisional": True}
    if provisional:
        return stamp
    if state["commit"] is None or state["dirty"] is None:
        raise DirtyTreeError(
            "not a git checkout with a commit; only a provisional run may write results"
        )
    if state["dirty"]:
        shown = "; ".join(state["changes"][:10])
        more = "" if len(state["changes"]) <= 10 else f" (+{len(state['changes']) - 10} more)"
        raise DirtyTreeError(
            f"working tree is dirty ({shown}{more}); commit first or flag the run provisional"
        )
    stamp["provisional"] = False
    return stamp


SEAL_STAMP_KEYS = (
    "environment", "ephemeris", "files_read", "files_written", "reads_summary",
    "threads_started", "problems",
)


def stamp_results(results: Dict[str, Any], seal: Mapping[str, Any]) -> Dict[str, Any]:
    """Write the seal into a results dict (in place) and return it.

    ``provisional`` is never downgraded: a result already marked provisional
    (for example, fixture data) stays provisional.
    """
    results["provisional"] = bool(results.get("provisional", False) or seal["provisional"])
    git = dict(results.get("git") or {})
    git.update({"commit": seal.get("commit"), "dirty": seal.get("dirty")})
    results["git"] = git
    extra = {k: seal[k] for k in SEAL_STAMP_KEYS if k in seal}
    if extra:  # a SealedRun stamp (ADR-008 9.2): environment, ephemeris, files read
        results["seal"] = extra
    return results


# -------------------------------------------------------------------- plan


def plan_sha256(plan_path: PathLike) -> str:
    """SHA-256 of the plan file's bytes."""
    return hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()


def _as_date(value: Any, what: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            pass
    raise SealError(f"plan field {what} is not an ISO date: {value!r}")


def _window_fields(plan: Mapping[str, Any]) -> Tuple[Any, str, Any, str]:
    """(start, its name, end or None, its name) from any accepted plan schema."""
    periods = plan.get("periods") or {}
    split = plan.get("split") or {}
    if "confirm_start" in periods:
        return (periods["confirm_start"], "periods.confirm_start",
                periods.get("confirm_end"), "periods.confirm_end")
    block = periods.get("confirm")
    if isinstance(block, Mapping) and "start" in block:
        return block["start"], "periods.confirm.start", block.get("end"), "periods.confirm.end"
    block = split.get("confirm") if isinstance(split, Mapping) else None
    if isinstance(block, Mapping) and "start" in block:
        return block["start"], "split.confirm.start", block.get("end"), "split.confirm.end"
    if isinstance(block, (list, tuple)) and len(block) in (1, 2):
        end = block[1] if len(block) == 2 else None
        return block[0], "split.confirm[0]", end, "split.confirm[1]"
    raise SealError(
        "plan has no confirm start (periods.confirm_start, periods.confirm.start "
        "or split.confirm)"
    )


def confirm_window(plan: Mapping[str, Any]) -> Tuple[str, str]:
    """Return the plan's confirm window as ISO dates ``(start, end)``.

    Accepted schemas (code audit M3): ``periods.confirm_start`` /
    ``periods.confirm_end`` (gold, silver), ``periods.confirm: {start, end}``
    (mundane) and ``split.confirm: [start, end]`` (earthquake). A missing end
    falls back to ``data.end``. Neither is ever taken from the current date;
    a plan with no end raises.
    """
    raw_start, start_name, raw_end, end_name = _window_fields(plan)
    start = _as_date(raw_start, start_name)
    if raw_end is not None:
        end = _as_date(raw_end, end_name)
    elif (plan.get("data") or {}).get("end") is not None:
        end = _as_date(plan["data"]["end"], "data.end")
    else:
        raise SealError("plan states no confirm end (periods.confirm_end or data.end)")
    if end < start:
        raise SealError(f"confirm window ends ({end}) before it starts ({start})")
    return start.isoformat(), end.isoformat()


# ------------------------------------------------------------------ ledger


def confirm_ledger_path(study_dir: PathLike) -> Path:
    """``<study_dir>/confirm_ledger.jsonl``."""
    return Path(study_dir) / LEDGER_NAME


def read_ledger(path: PathLike) -> List[Dict[str, Any]]:
    """Parse a ledger; a missing file is an empty ledger. Bad lines raise."""
    p = Path(path)
    if not p.exists():
        return []
    entries = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerTamperedError(f"{p}:{n} is not valid JSON") from exc
    return entries


def _historical_lines(path: Path, top: Path) -> List[str]:
    """Every non-empty ledger line in any committed version, on any ref."""
    rel = path.resolve().relative_to(top.resolve()).as_posix()
    log = _git(["log", "--all", "--format=%H", "--", rel], top)
    if log.returncode != 0:
        return []
    lines: List[str] = []
    seen = set()
    for sha in log.stdout.split():
        show = _git(["show", f"{sha}:{rel}"], top)
        if show.returncode != 0:  # the commit that deleted it
            continue
        for ln in show.stdout.splitlines():
            if ln.strip() and ln not in seen:
                seen.add(ln)
                lines.append(ln)
    return lines


def verify_ledger(path: PathLike, repo_root: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    """Return the ledger entries; raise if git history shows lost entries."""
    p = Path(path)
    top = _repo_toplevel(repo_root if repo_root is not None else p.parent)
    current = []
    if p.exists():
        current = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if top is not None:
        try:
            past = _historical_lines(p, top)
        except ValueError:  # ledger outside the repository
            past = []
        have = set(current)
        missing = [ln for ln in past if ln not in have]
        if missing:
            raise LedgerTamperedError(
                f"{p} has lost {len(missing)} entr{'y' if len(missing) == 1 else 'ies'} "
                "that git history records; the confirm for this lineage is spent"
            )
    return read_ledger(p)


def entry_sha256(entry: Mapping[str, Any]) -> str:
    """SHA-256 of a ledger entry as it is written (one JSON line, sorted keys)."""
    return hashlib.sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()


def _line_sha256(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def plan_identity(plan: Mapping[str, Any], plan_rel: str, plan_hash: str) -> List[str]:
    """Identity tokens of a plan lineage; any shared token is the same lineage."""
    tokens = []
    for key in ("lineage", "study", "id"):
        value = plan.get(key)
        if value not in (None, ""):
            tokens.append(f"{key}:{value}")
    tokens += [f"path:{plan_rel}", f"sha256:{plan_hash}"]
    return tokens


def _entry_identity(entry: Mapping[str, Any]) -> set:
    if isinstance(entry.get("identity"), list):
        return set(entry["identity"])
    tokens = set()  # entries written before the identity field existed
    if entry.get("study"):
        tokens.add(f"study:{entry['study']}")
    if entry.get("plan_path"):
        tokens.add(f"path:{entry['plan_path']}")
    if entry.get("plan_sha256"):
        tokens.add(f"sha256:{entry['plan_sha256']}")
    return tokens


def _is_confirm(entry: Any) -> bool:
    return isinstance(entry, dict) and entry.get("kind", "confirm") == "confirm"


def _same_key(entry: Mapping[str, Any], principle_id: Optional[str], identity: set) -> bool:
    other = entry.get("principle_id")
    if principle_id is not None and other is not None and other != principle_id:
        return False
    return bool(_entry_identity(entry) & identity)


def _repo_ledger_entries(top: Path) -> List[Tuple[str, Dict[str, Any]]]:
    """Every confirm entry of every ledger: working tree and git history, any ref."""
    found: List[Tuple[str, Dict[str, Any]]] = []
    seen = set()

    def add(where: str, text: str) -> None:
        for ln in text.splitlines():
            if not ln.strip() or ln in seen:
                continue
            seen.add(ln)
            try:
                entry = json.loads(ln)
            except json.JSONDecodeError:
                continue  # verify_ledger reports bad lines of the target ledger
            if _is_confirm(entry):
                found.append((where, entry))

    listed = _git(["ls-files", "-co", "--exclude-standard", "-z"], top)
    for rel in listed.stdout.split("\0") if listed.returncode == 0 else []:
        if rel and Path(rel).name == LEDGER_NAME and (top / rel).exists():
            add(rel, (top / rel).read_text(encoding="utf-8"))
    log = _git(["log", "--all", "--format=commit %H", "--name-only", "--", f"*{LEDGER_NAME}"], top)
    sha = None
    for ln in log.stdout.splitlines() if log.returncode == 0 else []:
        if ln.startswith("commit "):
            sha = ln.split()[1]
        elif ln.strip() and sha and Path(ln.strip()).name == LEDGER_NAME:
            show = _git(["show", f"{sha}:{ln.strip()}"], top)
            if show.returncode == 0:
                add(f"{ln.strip()}@{sha[:12]}", show.stdout)
    return found


def record_external_timestamp(
    ledger_path: PathLike,
    entry_hash: str,
    service: str,
    receipt: str,
    *,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Append the receipt of an external timestamp of one confirm entry.

    The owner stamps ``entry_sha256(entry)`` outside the repository
    (OpenTimestamps, Zenodo, OSF) and records the receipt here. Ledger lines
    are never edited, so the stamp is a line of its own that names the entry.
    """
    p = Path(ledger_path)
    entries = read_ledger(p)
    if not any(_is_confirm(e) and entry_sha256(e) == entry_hash for e in entries):
        raise SealError(f"{p} has no confirm entry with hash {entry_hash}")
    if not service or not receipt:
        raise SealError("an external timestamp needs a service and a receipt")
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamp = {
        "kind": "external_timestamp",
        "entry_sha256": entry_hash,
        "service": service,
        "receipt": receipt,
        "utc": when.isoformat(timespec="seconds"),
        "prev_sha256": _line_sha256(lines[-1]) if lines else None,
    }
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(stamp, sort_keys=True) + "\n")
    return stamp


def begin_confirm(
    study_dir: PathLike,
    plan_path: PathLike,
    data_sha256: str,
    *,
    principle_id: Optional[str] = None,
    repo_root: Optional[PathLike] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Log the single confirm of (principle, plan lineage) and return its entry.

    Requires a clean tree (a confirm is never provisional), a plan file that
    git tracks, a data hash and a confirm window from the plan. Raises
    :class:`ConfirmAlreadyRunError` if any ledger of the repository (working
    tree or history) records a confirm of the same key, whatever plan hash
    or period it was for; see the module docstring for the key. ``now`` only
    sets the logged time; it does not affect the window.
    """
    if not isinstance(data_sha256, str) or not data_sha256.strip():
        raise SealError("a confirm needs the SHA-256 of its data")
    root = repo_root if repo_root is not None else study_dir
    stamp = require_clean_tree(root, provisional=False)
    top = _repo_toplevel(root)
    plan_p = Path(plan_path)
    tracked = _git(["ls-files", "--error-unmatch", "--", str(plan_p.resolve())], top)
    if tracked.returncode != 0:
        raise SealError(f"plan {plan_p} is not committed")
    plan = yaml.safe_load(plan_p.read_text(encoding="utf-8")) or {}
    start, end = confirm_window(plan)

    if principle_id is not None and (not isinstance(principle_id, str) or not principle_id.strip()):
        raise SealError("principle_id must be a non-empty string or None (whole plan)")
    plan_rel = plan_p.resolve().relative_to(top.resolve()).as_posix()
    p_hash = plan_sha256(plan_p)
    identity = plan_identity(plan, plan_rel, p_hash)

    ledger = confirm_ledger_path(study_dir)
    entries = verify_ledger(ledger, top)
    local = [("" + str(ledger), e) for e in entries if _is_confirm(e)]
    for where, prior in local + _repo_ledger_entries(top):
        if _same_key(prior, principle_id, set(identity)):
            raise ConfirmAlreadyRunError(
                f"{where} already records a confirm of this lineage "
                f"(principle {prior.get('principle_id')!r}, commit {prior.get('commit')}, "
                f"{prior.get('utc')}); one confirm per principle and plan lineage"
            )
    lines = []
    if ledger.exists():
        lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
    when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    entry = {
        "kind": "confirm",
        "study": plan.get("study"),
        "lineage": plan.get("lineage") or plan.get("study") or plan.get("id") or plan_rel,
        "principle_id": principle_id,
        "identity": identity,
        "plan_path": plan_rel,
        "plan_sha256": p_hash,
        "data_sha256": data_sha256.strip(),
        "commit": stamp["commit"],
        "utc": when.isoformat(timespec="seconds"),
        "period": {"start": start, "end": end},
        "prev_sha256": _line_sha256(lines[-1]) if lines else None,
        # Placeholder: filled by an external stamp (record_external_timestamp).
        "external_timestamp": None,
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


# ============================================================ seal stamp
# ADR-008 section 9.2 (strategy audit G-02, G-03, G-13). The stamp adds the
# interpreter, the hash of the dependency lock (and a refusal when installed
# versions differ from it), the ephemeris model and the hash of every
# ephemeris file, and the path and hash of every file the run opened, which an
# audit hook on ``open`` records. A sealed run fails if it read a file git
# does not track, other than snapshots listed in data/snapshot_index.json.
# Nothing here starts a thread: the hook records into plain lists and every
# check runs after recording has stopped (processes, no threads; G-13).

CODE_REPO = Path(__file__).resolve().parents[3]
LOCK_REL = "ops/requirements.lock.txt"
SNAPSHOT_INDEX_REL = "data/snapshot_index.json"
THREAD_EVENTS = ("_thread.start_new_thread", "_thread.start_joinable_thread")


class EnvironmentMismatchError(SealError):
    """Installed package versions differ from the lock (or there is no lock)."""


class UntrackedReadError(SealError):
    """A sealed run read a file that git does not track."""


class ThreadStartedError(SealError):
    """A sealed run started a thread (the ayanamsa mode is process-global)."""


def _file_sha256(path: PathLike, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _norm_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# ------------------------------------------------------------ environment


def read_lock(path: PathLike) -> Dict[str, str]:
    """``{normalised name: version}`` from a pip/uv lock (``name==version`` lines)."""
    pins: Dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9_.\-]*)(?:\[[^\]]*\])?==([^\s;\\]+)", line)
        if m:
            pins[_norm_dist(m.group(1))] = m.group(2)
    return pins


def installed_versions() -> Dict[str, str]:
    """``{normalised name: version}`` of every distribution this interpreter sees."""
    found: Dict[str, str] = {}
    for dist in importlib_metadata.distributions():
        name = dist.metadata["Name"] if dist.metadata else None
        if name:
            found.setdefault(_norm_dist(name), dist.version)
    return found


def default_lock_path(repo_root: Optional[PathLike] = None) -> Path:
    """The lock of ``repo_root``'s checkout, else the lock of the code's own repository."""
    top = _repo_toplevel(repo_root)
    if top is not None and (top / LOCK_REL).is_file():
        return top / LOCK_REL
    return CODE_REPO / LOCK_REL


def environment_stamp(
    lock_path: Optional[PathLike] = None, repo_root: Optional[PathLike] = None
) -> Dict[str, Any]:
    """Interpreter, lock hash and every difference between the lock and this environment.

    ``lock_mismatches`` lists packages whose installed version differs from
    the lock (these refuse a sealed run). ``lock_missing`` (locked, not
    installed: an extra such as docs) and ``unlocked`` (installed, not in the
    lock: the project itself, type stubs) are recorded only; a missing
    package cannot feed a run, it fails the import.
    """
    lock = Path(lock_path) if lock_path is not None else default_lock_path(repo_root)
    stamp: Dict[str, Any] = {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "lock_path": None,
        "lock_sha256": None,
        "matches_lock": False,
        "lock_mismatches": [],
        "lock_missing": [],
        "unlocked": [],
    }
    if not lock.is_file():
        return stamp
    top = _repo_toplevel(lock.parent)
    try:
        stamp["lock_path"] = lock.resolve().relative_to(top.resolve()).as_posix() if top else str(lock)
    except ValueError:
        stamp["lock_path"] = str(lock)
    stamp["lock_sha256"] = _file_sha256(lock)
    pins = read_lock(lock)
    have = installed_versions()
    stamp["lock_mismatches"] = [
        {"name": n, "locked": v, "installed": have[n]}
        for n, v in sorted(pins.items())
        if n in have and have[n] != v
    ]
    stamp["lock_missing"] = sorted(n for n in pins if n not in have)
    stamp["unlocked"] = sorted(f"{n}=={v}" for n, v in have.items() if n not in pins)
    stamp["matches_lock"] = not stamp["lock_mismatches"]
    return stamp


def require_locked_environment(
    lock_path: Optional[PathLike] = None,
    repo_root: Optional[PathLike] = None,
    *,
    provisional: bool = False,
) -> Dict[str, Any]:
    """Return :func:`environment_stamp`; raise for a non-provisional run that differs from the lock."""
    stamp = environment_stamp(lock_path, repo_root)
    if provisional:
        return stamp
    if stamp["lock_sha256"] is None:
        raise EnvironmentMismatchError(f"no dependency lock ({LOCK_REL}); a sealed run needs one")
    if stamp["lock_mismatches"]:
        shown = ", ".join(
            f"{m['name']} {m['installed']} (lock {m['locked']})" for m in stamp["lock_mismatches"][:8]
        )
        more = len(stamp["lock_mismatches"]) - 8
        raise EnvironmentMismatchError(
            f"installed versions differ from {stamp['lock_path']}: {shown}"
            + (f" (+{more} more)" if more > 0 else "")
            + "; sync the environment to the lock or flag the run provisional"
        )
    return stamp


# -------------------------------------------------------------- ephemeris


def _engine_field(engine: Any, *names: str) -> Any:
    for name in names:
        if isinstance(engine, Mapping) and engine.get(name) is not None:
            return engine[name]
        if not isinstance(engine, Mapping) and getattr(engine, name, None) is not None:
            return getattr(engine, name)
    return None


def ephemeris_stamp(engine: Any = None, ephe_path: Optional[PathLike] = None) -> Dict[str, Any]:
    """Ephemeris model and the SHA-256 of every ephemeris file the engine can read.

    The model comes from the engine (``EphemerisEngine`` or its info dict);
    without one, Swiss Ephemeris is probed once with a tropical Sun (this
    neither sets nor reads the global ayanamsa mode). Files are every regular
    file in the ephemeris path (``ephe_path``, the engine's, else
    ``SE_EPHE_PATH``). Swiss Ephemeris reads them with C ``fopen``, which
    the open audit hook cannot see, so they are hashed here instead.
    ``problems`` is non-empty when "swieph" is in use and no file is hashed.
    """
    import swisseph as swe  # noqa: PLC0415

    info = engine.get_ephemeris_info() if hasattr(engine, "get_ephemeris_info") else engine
    model = _engine_field(info, "ephemeris_model") if info is not None else None
    source = "engine"
    if model is None:
        from ..astrology.ephemeris import ephemeris_model_from_retflag  # noqa: PLC0415

        _, retflag = swe.calc_ut(2451545.0, swe.SUN, swe.FLG_SWIEPH)
        model = ephemeris_model_from_retflag(retflag)
        source = "probe"
    path = ephe_path
    if path is None and engine is not None:
        path = _engine_field(engine, "ephe_path")
    if path is None:
        path = os.environ.get("SE_EPHE_PATH") or None
    files: List[Dict[str, Any]] = []
    for part in (str(path).split(os.pathsep) if path else []):
        d = Path(part)
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                files.append({"path": str(f), "sha256": _file_sha256(f)})
    problems = []
    if model == "swieph" and not files:
        problems.append("Swiss Ephemeris files are in use but none was found to hash")
    return {
        "model": model,
        "model_source": source,
        "ayanamsa": _engine_field(info, "ayanamsa_system", "ayanamsa") if info is not None else None,
        "node_model": _engine_field(info, "node_model") if info is not None else None,
        "swisseph_version": getattr(swe, "version", None),
        "ephe_path": str(path) if path else None,
        "files": files,
        "problems": problems,
    }


# ------------------------------------------------------------- files read

_HOOK_INSTALLED = False
_ACTIVE: List["ReadLog"] = []


def _audit_hook(event: str, args: Tuple[Any, ...]) -> None:
    """Process-wide audit hook; records only while a :class:`ReadLog` is active."""
    if not _ACTIVE:
        return
    try:
        if event == "open":
            raw = args[0]
            if raw is None or isinstance(raw, int):
                return
            path = os.path.abspath(os.fsdecode(os.fspath(raw)))
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else None
            for log in _ACTIVE:
                log.events.append((path, mode, flags))
        elif event in THREAD_EVENTS:
            for log in _ACTIVE:
                log.threads.append(event)
    except Exception:  # noqa: BLE001 - an audit hook must never break the open it watches
        return


def _install_hook() -> None:
    global _HOOK_INSTALLED
    if not _HOOK_INSTALLED:
        sys.addaudithook(_audit_hook)  # permanent by design; inert when no log is active
        _HOOK_INSTALLED = True


def _is_write(mode: Any, flags: Any) -> bool:
    if isinstance(flags, int) and flags >= 0:
        acc = flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)
        return acc in (os.O_WRONLY, os.O_RDWR) or bool(flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    return isinstance(mode, str) and any(c in mode for c in "wax+")


def _is_read(mode: Any, flags: Any) -> bool:
    if isinstance(flags, int) and flags >= 0:
        return flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR) in (os.O_RDONLY, os.O_RDWR)
    return not isinstance(mode, str) or "r" in mode or "+" in mode


class ReadLog:
    """Paths opened (with mode and flags) and threads started while active."""

    def __init__(self) -> None:
        self.events: List[Tuple[str, Any, Any]] = []
        self.threads: List[str] = []

    def start(self) -> "ReadLog":
        _install_hook()
        if self not in _ACTIVE:
            _ACTIVE.append(self)
        return self

    def stop(self) -> "ReadLog":
        while self in _ACTIVE:
            _ACTIVE.remove(self)
        return self

    def __enter__(self) -> "ReadLog":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()


def _under(path: Path, roots: Sequence[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _environment_roots() -> List[Path]:
    roots = {sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix}
    try:
        roots.update(site.getsitepackages())
        roots.add(site.getusersitepackages())
    except Exception:  # noqa: BLE001 - site may be stubbed (virtualenv, embedded)
        pass
    return [Path(r).resolve() for r in roots if r]


def _system_roots() -> List[Path]:
    roots = ["/dev", "/proc", "/sys", "/etc", "/private/etc", "/private/var/db/timezone", "/usr/share", "/usr/lib",
             "/System", "/Library"]
    try:
        import zoneinfo  # noqa: PLC0415

        roots += list(zoneinfo.TZPATH)
    except Exception:  # noqa: BLE001
        pass
    return [Path(r).resolve() for r in roots if Path(r).exists()]


def _cache_roots() -> List[Path]:
    home = Path.home()
    roots = [home / ".matplotlib", home / ".cache", home / ".config", home / "Library" / "Caches"]
    for var in ("MPLCONFIGDIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME"):
        if os.environ.get(var):
            roots.append(Path(os.environ[var]))
    return [r.resolve() for r in roots]


def _snapshot_hashes(top: Optional[Path], snapshot_index: Optional[PathLike]) -> Dict[str, str]:
    """``{sha256: file name}`` of every snapshot listed in the index."""
    path = Path(snapshot_index) if snapshot_index is not None else (
        top / SNAPSHOT_INDEX_REL if top is not None else None)
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = data.get("snapshots", []) if isinstance(data, Mapping) else data
    return {
        str(e["sha256"]): Path(str(e.get("file", ""))).name
        for e in entries
        if isinstance(e, Mapping) and e.get("sha256")
    }


def files_read_stamp(
    log: ReadLog,
    repo_root: Optional[PathLike] = None,
    *,
    snapshot_index: Optional[PathLike] = None,
) -> Dict[str, Any]:
    """Classify, hash and check what a :class:`ReadLog` saw (call after it stopped).

    Every file read inside the repository, or outside it but not part of
    the interpreter, the operating system or a tool cache, is listed with its
    path, SHA-256 and status: ``tracked``, ``snapshot`` (hash listed in the
    snapshot index), ``run_output`` (written earlier by this run),
    ``untracked``, ``ignored``, ``outside_repo`` or ``gone`` (inside the repository,
    no longer there). The last four are ``problems``. An open of a path outside
    the repository that does not exist is a probe that read nothing (counted
    as ``absent``). Python bytecode, interpreter and system files are counted
    in ``summary``; the environment is pinned by the lock hash instead.
    """
    top = _repo_toplevel(repo_root)
    topr = top.resolve() if top is not None else None
    tracked: set = set()
    if top is not None:
        listed = _git(["ls-files", "-z"], top)
        if listed.returncode == 0:
            tracked = {p for p in listed.stdout.split("\0") if p}
    snapshots = _snapshot_hashes(top, snapshot_index)
    env_roots, sys_roots, cache_roots = _environment_roots(), _system_roots(), _cache_roots()
    summary = {"environment": 0, "bytecode": 0, "system": 0, "cache": 0, "absent": 0}
    written: Dict[str, None] = {}
    reads: Dict[str, Dict[str, Any]] = {}
    for raw, mode, flags in log.events:
        p = Path(raw)
        try:
            p = p.resolve()
        except OSError:
            pass
        key = str(p)
        if _is_write(mode, flags):
            written.setdefault(key, None)
        if not _is_read(mode, flags) or key in reads:
            continue
        if p.is_dir():
            continue
        if topr is not None and _under(p, [topr]) and not _under(p, env_roots):
            rel = p.relative_to(topr).as_posix()
            if p.suffix == ".pyc" or "__pycache__" in p.parts:
                summary["bytecode"] += 1
                continue
            rec: Dict[str, Any] = {"path": rel}
        elif _under(p, env_roots):
            summary["bytecode" if p.suffix == ".pyc" else "environment"] += 1
            continue
        elif _under(p, sys_roots):
            summary["system"] += 1
            continue
        elif _under(p, cache_roots):
            summary["cache"] += 1
            continue
        else:
            rel = None
            rec = {"path": key}
        if not p.is_file() and rel is None and key not in written:
            summary["absent"] += 1  # a probe that found nothing outside the repo read nothing
            continue
        if not p.is_file():
            rec.update(sha256=None, status="run_output" if key in written else "gone")
            reads[key] = rec
            continue
        sha = _file_sha256(p)
        rec["sha256"] = sha
        if key in written:
            status = "run_output"
        elif rel is not None and rel in tracked:
            status = "tracked"
        elif snapshots.get(sha) == p.name:
            status = "snapshot"
        elif rel is None:
            status = "outside_repo"
        else:
            ign = _git(["check-ignore", "-q", "--", rel], top)
            status = "ignored" if ign.returncode == 0 else "untracked"
        rec["status"] = status
        reads[key] = rec
    files = sorted(reads.values(), key=lambda r: r["path"])
    problems = [
        f"{r['path']} ({r['status']})" for r in files
        if r["status"] in ("untracked", "ignored", "outside_repo", "gone")
    ]
    out_written = []
    for key in written:
        p = Path(key)
        if topr is not None and _under(p, [topr]):
            out_written.append(p.relative_to(topr).as_posix())
        elif not _under(p, env_roots + sys_roots + cache_roots):
            out_written.append(key)
    return {
        "files_read": files,
        "files_written": sorted(set(out_written)),
        "reads_summary": summary,
        "threads_started": len(log.threads),
        "problems": problems,
    }


# -------------------------------------------------------------- sealed run


class SealedRun:
    """A run whose stamp names everything that produced its numbers.

    Usage::

        with SealedRun(repo_root, provisional=False) as run:
            numbers = compute()
            stamp = run.finish(engine=engine)   # before writing results
        stamp_results(results, stamp)

    On entry: :func:`require_clean_tree` and :func:`require_locked_environment`
    (both refuse a non-provisional run), then the open audit hook records.
    :meth:`finish` stops recording and adds the environment, ephemeris and
    files-read stamp. A non-provisional run raises :class:`UntrackedReadError`
    if it read a file git does not track (snapshots listed in the index
    excepted), :class:`ThreadStartedError` if it started a thread, and
    :class:`EnvironmentMismatchError` if the ephemeris files cannot be hashed.
    A provisional run records the same problems in the stamp and is not
    refused. Leaving the block without :meth:`finish` calls it.
    """

    def __init__(
        self,
        repo_root: Optional[PathLike] = None,
        *,
        provisional: bool = False,
        lock_path: Optional[PathLike] = None,
        snapshot_index: Optional[PathLike] = None,
        ephe_path: Optional[PathLike] = None,
    ) -> None:
        if not isinstance(provisional, bool):
            raise TypeError("provisional must be a bool")
        self.repo_root = repo_root
        self.provisional = provisional
        self.lock_path = lock_path
        self.snapshot_index = snapshot_index
        self.ephe_path = ephe_path
        self.log = ReadLog()
        self.stamp: Optional[Dict[str, Any]] = None
        self._tree: Optional[Dict[str, Any]] = None
        self._env: Optional[Dict[str, Any]] = None

    def __enter__(self) -> "SealedRun":
        self._tree = require_clean_tree(self.repo_root, provisional=self.provisional)
        self._env = require_locked_environment(
            self.lock_path, self.repo_root, provisional=self.provisional
        )
        self.log.start()
        return self

    def finish(self, engine: Any = None) -> Dict[str, Any]:
        """Stop recording, check and return the full stamp (idempotent)."""
        if self.stamp is not None:
            return self.stamp
        self.log.stop()
        if self._tree is None:
            raise SealError("SealedRun.finish() called outside its with-block")
        reads = files_read_stamp(self.log, self.repo_root, snapshot_index=self.snapshot_index)
        eph = ephemeris_stamp(engine, self.ephe_path)
        stamp = dict(self._tree)
        stamp.update(
            environment=self._env,
            ephemeris=eph,
            files_read=reads["files_read"],
            files_written=reads["files_written"],
            reads_summary=reads["reads_summary"],
            threads_started=reads["threads_started"],
            problems=reads["problems"] + eph["problems"],
        )
        self.stamp = stamp
        if not self.provisional:
            if reads["problems"]:
                shown = "; ".join(reads["problems"][:10])
                raise UntrackedReadError(
                    f"the run read files git does not track: {shown}; commit them, list the "
                    "snapshot in the index or flag the run provisional"
                )
            if reads["threads_started"]:
                raise ThreadStartedError(
                    f"the run started {reads['threads_started']} thread(s); the ayanamsa "
                    "mode is process-global, so sealed runs use processes, not threads (G-13)"
                )
            if eph["problems"]:
                raise EnvironmentMismatchError("; ".join(eph["problems"]))
        return stamp

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is not None:
            self.log.stop()
            return False
        self.finish()
        return False


# ---------------------------------------------------- study script imports


def load_study_modules(
    scripts_dir: PathLike, names: Sequence[str], *, namespace: str
) -> Dict[str, types.ModuleType]:
    """Import study scripts by file path under unique module names (G-03).

    Each ``<scripts_dir>/<name>.py`` becomes ``_study_<namespace>__<name>`` in
    ``sys.modules``. Six study folders have a ``pipeline.py``; importing them by
    bare name through ``sys.path`` lets the first import win. ``names`` are
    loaded in order (dependencies first); while they load, each bare name is
    aliased to its unique module so the scripts' own sibling imports
    (``import decluster``) resolve to this folder. Afterwards the bare names
    in ``sys.modules`` are put back as they were, and the script folder is
    taken off ``sys.path`` if a script put it there.
    """
    folder = Path(scripts_dir).resolve()
    safe_ns = re.sub(r"\W", "_", namespace)
    saved = {n: sys.modules.get(n) for n in names}
    saved_path = list(sys.path)
    loaded: Dict[str, types.ModuleType] = {}
    try:
        for name in names:
            src = folder / f"{name}.py"
            unique = f"_study_{safe_ns}__{name}"
            mod = sys.modules.get(unique)
            if mod is None or Path(getattr(mod, "__file__", "") or "").resolve() != src:
                spec = importlib.util.spec_from_file_location(unique, src)
                if spec is None or spec.loader is None:
                    raise ImportError(f"cannot load study script {src}")
                mod = importlib.util.module_from_spec(spec)
                sys.modules[unique] = mod
                sys.modules[name] = mod
                try:
                    spec.loader.exec_module(mod)
                except BaseException:
                    sys.modules.pop(unique, None)
                    raise
            sys.modules[name] = mod
            loaded[name] = mod
    finally:
        for name, old in saved.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        added = [p for p in sys.path if p not in saved_path]
        for p in added:
            try:
                same = Path(p).resolve() == folder
            except OSError:
                same = False
            if same:
                while p in sys.path:
                    sys.path.remove(p)
    return loaded
