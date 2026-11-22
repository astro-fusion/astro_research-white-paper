"""Run seal: results from a clean tree, and one confirm per plan lineage.

ADR-004 D-2 (review flaw C2). Two guards:

* :func:`require_clean_tree` refuses a non-provisional run unless the
  working tree is a git checkout with no modified, staged or untracked
  (non-ignored) files. A run that is explicitly flagged provisional is let
  through and is stamped ``provisional: true``. There is deliberately no
  environment variable or other side door: provisional is an argument.
* :func:`begin_confirm` appends one entry to the append-only ledger
  ``studies/<study>/confirm_ledger.jsonl`` (plan hash, data hash, commit,
  UTC time, period) and raises if the ledger already holds a confirm. The
  ledger file is the plan lineage: editing the plan, bumping its version or
  renaming the study does not open a second confirm. Deleting or truncating
  a ledger that was ever committed is detected from git history.

The confirm window comes from the plan (``periods.confirm_start`` to
``periods.confirm_end``, else ``data.end``), never from the clock. The
entry is written before the confirm computes anything, so a confirm that
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


def tree_state(repo_root: Optional[PathLike] = None) -> Dict[str, Any]:
    """Return ``{"commit", "dirty", "changes"}`` counting untracked files.

    Outside git (or with no commit yet) ``commit`` and ``dirty`` are None.
    ``changes`` lists the porcelain lines that make the tree dirty.
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
    changes = [ln for ln in status.stdout.splitlines() if ln.strip()]
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


def confirm_window(plan: Mapping[str, Any]) -> Tuple[str, str]:
    """Return the plan's confirm window as ISO dates ``(start, end)``.

    Start is ``periods.confirm_start``. End is ``periods.confirm_end``, or
    else ``data.end``. Neither is ever taken from the current date; a plan
    with no end raises.
    """
    periods = plan.get("periods") or {}
    if "confirm_start" not in periods:
        raise SealError("plan has no periods.confirm_start")
    start = _as_date(periods["confirm_start"], "periods.confirm_start")
    if periods.get("confirm_end") is not None:
        end = _as_date(periods["confirm_end"], "periods.confirm_end")
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


def begin_confirm(
    study_dir: PathLike,
    plan_path: PathLike,
    data_sha256: str,
    *,
    repo_root: Optional[PathLike] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Log the single confirm of a plan lineage and return its entry.

    Requires a clean tree (a confirm is never provisional), a plan file that
    git tracks, a data hash and a confirm window from the plan. Raises
    :class:`ConfirmAlreadyRunError` if the lineage's ledger holds any entry,
    whatever plan hash or period it was for. ``now`` only sets the logged
    time; it does not affect the window.
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

    ledger = confirm_ledger_path(study_dir)
    entries = verify_ledger(ledger, top)
    if entries:
        first = entries[0]
        raise ConfirmAlreadyRunError(
            f"{ledger} already records a confirm (commit {first.get('commit')}, "
            f"{first.get('utc')}); one confirm per plan lineage"
        )
    when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    entry = {
        "study": plan.get("study"),
        "plan_path": plan_p.resolve().relative_to(top.resolve()).as_posix(),
        "plan_sha256": plan_sha256(plan_p),
        "data_sha256": data_sha256.strip(),
        "commit": stamp["commit"],
        "utc": when.isoformat(timespec="seconds"),
        "period": {"start": start, "end": end},
    }
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry
