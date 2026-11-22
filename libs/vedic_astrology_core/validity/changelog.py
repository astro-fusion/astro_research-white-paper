"""Hash-chained changelog of the validity record (ADR-007 section 9, WP-74).

One entry per `astro-validity all` that changed anything. Every line of
`studies/validity/changelog.jsonl` carries `prev_sha256`, the SHA-256 of the
line before it, so the same chain check as the other ledgers applies
(sealbundle.verify_chain).

An entry says which inputs changed (rules, datasets, plans, engine), and for
every test what that did: added, superseded or recomputed (a test whose
numbers did not move is only counted). Each changed test names its cause.

Two hard rules (ADR-007 section 9, ADR-008 section 9):

* a test whose inputs did not change must reproduce its stored numbers
  exactly; and
* a verdict that changes with no rule, data, plan, budget or engine change is
  a bug. Both raise :class:`ChangelogError` and nothing is appended.

Pure functions over results mappings; no outcome is read and nothing is
computed here. Past data only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .family import canonical_bytes
from .sealbundle import verify_chain

__all__ = [
    "CHANGELOG_SCHEMA",
    "CAUSES",
    "ChangelogError",
    "flatten_params",
    "rule_state",
    "input_state",
    "run_id_for",
    "diff_inputs",
    "compare",
    "build_entry",
    "read_entries",
    "append_entry",
    "head_sha256",
    "render_qmd",
    "card_history",
]

CHANGELOG_SCHEMA = "validity-changelog/1"
PathLike = Union[str, Path]
#: Cause order: the first that applies is named on the test line.
CAUSES: Tuple[str, ...] = (
    "rule_changed", "new_principle", "data_changed", "plan_changed", "budget_changed", "engine_changed")


class ChangelogError(ValueError):
    """An unexplained change, or a broken append: the run stops and nothing is recorded."""


def _sha(data: Union[str, bytes]) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


# ------------------------------------------------------------------ state
def flatten_params(obj: Any, prefix: str = "") -> Dict[str, Any]:
    """Nested mappings to {dotted path: leaf}; lists are leaves."""
    out: Dict[str, Any] = {}
    if isinstance(obj, Mapping):
        for k in sorted(obj, key=str):
            out.update(flatten_params(obj[k], f"{prefix}.{k}" if prefix else str(k)))
    else:
        out[prefix] = obj
    return out


def rule_state(version: int, doc: Mapping[str, Any]) -> Dict[str, Any]:
    """One rule file as the changelog sees it: version, content hash, flat params."""
    return {
        "version": int(version),
        "sha256": _sha(canonical_bytes(doc)),
        "params": flatten_params(doc.get("params") or {}, "params"),
    }


def input_state(
    *,
    rules: Mapping[str, Mapping[str, Any]],
    datasets: Mapping[str, str],
    plans: Mapping[str, str],
    engine: Optional[str],
    budget: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Every input the record depends on, normalised (and JSON-safe)."""
    return json.loads(canonical_bytes({
        "rules": {k: dict(v) for k, v in rules.items()},
        "datasets": dict(datasets),
        "plans": dict(plans),
        "engine": engine,
        "budget": dict(budget or {}),
    }).decode("utf-8"))


def run_id_for(date: str, state: Mapping[str, Any]) -> str:
    """Date plus the first 12 hex characters of the hash over all inputs (ADR-007 7.2)."""
    return f"{date}-{_sha(canonical_bytes(state))[:12]}"


def diff_inputs(old: Optional[Mapping[str, Any]], new: Mapping[str, Any]) -> Dict[str, Any]:
    """The `inputs_changed` block of an entry."""
    old = old or {}
    o_rules, n_rules = old.get("rules") or {}, new.get("rules") or {}
    rules = []
    for rid in sorted(set(o_rules) | set(n_rules)):
        a, b = o_rules.get(rid), n_rules.get(rid)
        if a == b:
            continue
        fields = []
        pa = (a or {}).get("params") or {}
        pb = (b or {}).get("params") or {}
        for path in sorted(set(pa) | set(pb)):
            if pa.get(path) != pb.get(path):
                fields.append({"path": path, "from": pa.get(path), "to": pb.get(path)})
        rules.append({
            "id": rid,
            "from_version": None if a is None else a["version"],
            "to_version": None if b is None else b["version"],
            "fields": fields,
        })
    def keyed(name: str) -> List[Dict[str, Any]]:
        a, b = old.get(name) or {}, new.get(name) or {}
        return [{"domain": d, "from": a.get(d), "to": b.get(d)}
                for d in sorted(set(a) | set(b)) if a.get(d) != b.get(d)]
    e_old, e_new = old.get("engine"), new.get("engine")
    return {
        "rules": rules,
        "datasets": keyed("datasets"),
        "plans": keyed("plans"),
        "budget": keyed("budget"),
        "engine": None if e_old == e_new else {"from": e_old, "to": e_new},
    }


# ---------------------------------------------------------------- compare
def _key(rec: Mapping[str, Any]) -> Tuple[str, str]:
    return str(rec.get("domain", "")), str(rec["test_id"])


def _code(rec: Optional[Mapping[str, Any]]) -> Optional[str]:
    return None if rec is None else (rec.get("verdict") or {}).get("code")


def _effect(rec: Optional[Mapping[str, Any]]) -> Optional[float]:
    if rec is None:
        return None
    e = (rec.get("effect") or {}).get("full") or {}
    return e.get("estimate")


def _x95(rec: Optional[Mapping[str, Any]]) -> Optional[float]:
    if rec is None:
        return None
    x = (rec.get("bound") or {}).get("x95")
    return x.get("value") if isinstance(x, Mapping) else None


def _budget(rec: Mapping[str, Any]) -> Tuple[Any, Any, Any]:
    th = rec.get("threshold") or {}
    return th.get("n_b"), th.get("alpha_b"), rec.get("a_test_used")


def _numbers(rec: Mapping[str, Any]) -> bytes:
    """What must reproduce exactly: everything but the stamp and the input hash."""
    drop = {"input_sha256", "provenance", "stamp", "seal"}
    return canonical_bytes({k: v for k, v in rec.items() if k not in drop})


def compare(
    old_results: Optional[Iterable[Mapping[str, Any]]],
    new_results: Iterable[Mapping[str, Any]],
    old_state: Optional[Mapping[str, Any]],
    new_state: Mapping[str, Any],
    *,
    strict: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str]]:
    """Compare two sets of result records (all domains) under two input states.

    Returns (test lines, summary, unexplained). With strict=True an
    unexplained change raises ChangelogError instead of being returned.
    """
    olds = {_key(r): r for r in (old_results or [])}
    news = {_key(r): r for r in new_results}
    changed = diff_inputs(old_state, new_state)
    o_rules = (old_state or {}).get("rules") or {}
    n_rules = new_state.get("rules") or {}
    rules_changed = {r["id"] for r in changed["rules"]}
    data_dom = {d["domain"] for d in changed["datasets"]}
    plan_dom = {d["domain"] for d in changed["plans"]}
    engine_changed = changed["engine"] is not None
    lines: List[Dict[str, Any]] = []
    unexplained: List[str] = []
    unchanged = 0
    verdict_changes = 0
    for k in sorted(news):
        dom, tid = k
        new = news[k]
        old = olds.get(k)
        rid = (new.get("principle") or {}).get("id")
        if old is None:
            seen_rule = rid in o_rules or any((o.get("principle") or {}).get("id") == rid for o in olds.values())
            cause = "rule_changed" if seen_rule else "new_principle"
            lines.append({
                "test_id": tid, "domain": dom, "change": "added", "cause": cause,
                "slot": ((new.get("threshold") or {}).get("lock_position") or {}).get("register"),
                "verdict": {"from": None, "to": _code(new)},
                "effect": {"from": None, "to": _effect(new)},
                "x95": {"from": None, "to": _x95(new)},
            })
            continue
        if _numbers(old) == _numbers(new):
            unchanged += 1
            continue
        causes = []
        if rid in rules_changed or (new.get("principle") or {}).get("version") != (old.get("principle") or {}).get("version"):
            causes.append("rule_changed")
        if dom in data_dom:
            causes.append("data_changed")
        if dom in plan_dom:
            causes.append("plan_changed")
        if _budget(old) != _budget(new):
            causes.append("budget_changed")
        if engine_changed:
            causes.append("engine_changed")
        if not causes:
            what = "verdict" if _code(old) != _code(new) else "numbers"
            unexplained.append(f"{tid}: {what} changed ({_code(old)} to {_code(new)}) with no rule, data, plan, budget or engine change")
            continue
        if _code(old) != _code(new):
            verdict_changes += 1
        lines.append({
            "test_id": tid, "domain": dom, "change": "recomputed", "cause": causes[0], "causes": causes,
            "slot": ((new.get("threshold") or {}).get("lock_position") or {}).get("register"),
            "verdict": {"from": _code(old), "to": _code(new)},
            "effect": {"from": _effect(old), "to": _effect(new)},
            "x95": {"from": _x95(old), "to": _x95(new)},
        })
    for k in sorted(set(olds) - set(news)):
        dom, tid = k
        old = olds[k]
        rid = (old.get("principle") or {}).get("id")
        newer = rid in n_rules and n_rules[rid]["version"] != (o_rules.get(rid) or {}).get("version")
        lines.append({
            "test_id": tid, "domain": dom, "change": "superseded",
            "cause": "rule_changed" if newer else "plan_changed",
            "verdict": {"from": _code(old), "to": _code(old)},
        })
    if unexplained and strict:
        raise ChangelogError("; ".join(unexplained))
    slots: Dict[str, List[int]] = {}
    for ln in lines:
        if ln["change"] == "added" and ln.get("slot") is not None:
            slots.setdefault(ln["domain"], []).append(ln["slot"])
    summary = {
        "slots_used": {d: sorted(v) for d, v in sorted(slots.items())},
        "verdict_changes": verdict_changes,
        "unchanged": unchanged,
    }
    return lines, summary, unexplained


def build_entry(
    run_id: str,
    previous_run_id: Optional[str],
    old_results: Optional[Iterable[Mapping[str, Any]]],
    new_results: Iterable[Mapping[str, Any]],
    old_state: Optional[Mapping[str, Any]],
    new_state: Mapping[str, Any],
    *,
    strict: bool = True,
) -> Dict[str, Any]:
    """One changelog entry (without the chain fields). Raises on an unexplained change."""
    lines, summary, unexplained = compare(old_results, new_results, old_state, new_state, strict=strict)
    entry = {
        "schema": CHANGELOG_SCHEMA,
        "run_id": run_id,
        "previous_run_id": previous_run_id,
        "inputs_changed": diff_inputs(old_state, new_state),
        "tests": lines,
        "summary": summary,
        "state": dict(new_state),
    }
    if unexplained:
        entry["unexplained"] = unexplained
    return entry


# ------------------------------------------------------------------ chain
def read_entries(path: PathLike) -> List[Dict[str, Any]]:
    """All entries; raises LedgerTamperedError on a broken chain. A missing file is empty."""
    return verify_chain(path)


def head_sha256(path: PathLike) -> Optional[str]:
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()] \
        if Path(path).exists() else []
    return _sha(lines[-1]) if lines else None


def append_entry(path: PathLike, entry: Mapping[str, Any]) -> Dict[str, Any]:
    """Append an entry, chained to the line before. Refuses a broken chain or a wrong predecessor."""
    p = Path(path)
    existing = read_entries(p)
    last = existing[-1] if existing else None
    if entry.get("previous_run_id") != (last["run_id"] if last else None):
        raise ChangelogError(
            f"previous_run_id {entry.get('previous_run_id')!r} is not the last entry's run id "
            f"{(last or {}).get('run_id')!r}")
    if last and entry.get("run_id") == last["run_id"]:
        raise ChangelogError(f"run {entry.get('run_id')} is already in the changelog")
    body = dict(entry)
    body["seq"] = len(existing) + 1
    body["prev_sha256"] = head_sha256(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(canonical_bytes(body).decode("utf-8") + "\n")
    return body


# -------------------------------------------------------------- rendering
def _fmt(x: Any) -> str:
    return "none" if x is None else str(x)


def card_history(entries: Sequence[Mapping[str, Any]], rule_id: str) -> List[str]:
    """The lines of a principle's card under "Version history" (from the changelog)."""
    out: List[str] = []
    for e in entries:
        for t in e.get("tests", []):
            if t["test_id"].split("@", 1)[0] == rule_id:
                v = t.get("verdict") or {}
                out.append(f"{e['run_id']}: {t['change']} ({t['cause']}), verdict {_fmt(v.get('from'))} to {_fmt(v.get('to'))}")
    return out


def render_qmd(entries: Sequence[Mapping[str, Any]]) -> str:
    """The changelog page, newest first. Text only; generated, never edited by hand."""
    out = ["---", "title: Changelog", "---", "",
           "Generated from `studies/validity/changelog.jsonl`. Do not edit.", ""]
    if not entries:
        out.append("No entries yet.")
    for e in reversed(list(entries)):
        out += [f"## {e['run_id']}", "", f"Previous run: {_fmt(e.get('previous_run_id'))}", ""]
        ic = e.get("inputs_changed") or {}
        for r in ic.get("rules", []):
            out.append(f"- rule {r['id']}: version {_fmt(r['from_version'])} to {_fmt(r['to_version'])}")
            for f in r.get("fields", []):
                out.append(f"    - {f['path']}: {_fmt(f['from'])} to {_fmt(f['to'])}")
        for name in ("datasets", "plans", "budget"):
            for d in ic.get(name, []):
                out.append(f"- {name[:-1] if name != 'budget' else name} {d['domain']}: changed")
        if ic.get("engine"):
            out.append(f"- engine: {_fmt(ic['engine']['from'])} to {_fmt(ic['engine']['to'])}")
        out.append("")
        out += ["| Test | Change | Cause | Verdict |", "|---|---|---|---|"]
        for t in e.get("tests", []):
            v = t.get("verdict") or {}
            out.append(f"| {t['test_id']} | {t['change']} | {t['cause']} | {_fmt(v.get('from'))} to {_fmt(v.get('to'))} |")
        out.append("")
    return "\n".join(out) + "\n"
