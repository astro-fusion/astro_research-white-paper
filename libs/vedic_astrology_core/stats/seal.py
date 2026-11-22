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
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import yaml

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


def stamp_results(results: Dict[str, Any], seal: Mapping[str, Any]) -> Dict[str, Any]:
    """Write the seal into a results dict (in place) and return it.

    ``provisional`` is never downgraded: a result already marked provisional
    (for example, fixture data) stays provisional.
    """
    results["provisional"] = bool(results.get("provisional", False) or seal["provisional"])
    git = dict(results.get("git") or {})
    git.update({"commit": seal.get("commit"), "dirty": seal.get("dirty")})
    results["git"] = git
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
