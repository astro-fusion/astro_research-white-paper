"""The ``use`` leaf: a combination points at an existing principle (schema v3).

A rule may name another rule instead of copying its conditions::

    conditions:
      all:
        - use: seismic.mangal_ketu_primary           # or {id: ..., version: 3}
        - moon_mandala: {mandalas: [agni]}

The leaf stands for the referenced rule's primary conditions, with that
rule's parameters bound to their current values. Its variants are not
included, and its parameters cannot be tuned through the child.
:class:`~vedic_astrology_core.rules.schema.UseOf` expands the leaf while the
child is validated, so the engine and the grid evaluator see an ordinary
condition tree and need no change.

Guards (ADR-007 WP-65):

- a missing id, a parent without conditions and a reference cycle are
  validation errors;
- an optional ``version`` pin refuses a parent at another version;
- every expanded leaf keeps a fingerprint (parent id, version, SHA-256 of the
  bound conditions, and the same for each ancestor), so a parent changed
  without a version bump is visible to the family lock (WP-66) through
  :func:`fingerprint`.

Where parents are looked up: the sources given to :func:`use_rules` (rule
directories, files or ``{id: raw mapping}``), innermost first, then the
default rules directory (``$ASTRO_RULES_DIR`` or the repository's
``rules/``). Files are parsed, not validated, when indexed; a parent is
validated when it is used.

This module registers no predicate; it is imported by the module discovery of
:mod:`.` like any other module in the folder and does nothing at import.
"""

import contextlib
import contextvars
import copy
import difflib
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

import yaml

__all__ = [
    "ResolvedUse",
    "UseError",
    "clear_cache",
    "entering",
    "find_cycles",
    "fingerprint",
    "parents",
    "raw_rules",
    "resolve",
    "rule_stack",
    "use_rules",
    "use_targets",
]

Source = Union[str, Path, Mapping[str, Mapping[str, Any]]]


class UseError(ValueError):
    """A ``use`` leaf that cannot be resolved (missing, cycle, version, ...)."""


@dataclass(frozen=True)
class ResolvedUse:
    """One resolved ``use`` leaf.

    Attributes:
        id: the parent rule id.
        version: the parent's version at resolution.
        conditions: the parent's conditions with its parameters bound (raw).
        sha256: SHA-256 of ``conditions`` in canonical JSON.
        lineage: ``(id, version, sha256)`` of the parent and every ancestor
            reached through further ``use`` leaves, parent first.
        raw_hashes: ``(id, sha256 of the raw file data)`` for the same rules,
            used to invalidate the cache.
    """

    id: str
    version: int
    conditions: Any
    sha256: str
    lineage: Tuple[Tuple[str, int, str], ...]
    raw_hashes: Tuple[Tuple[str, str], ...]


_STACK: contextvars.ContextVar = contextvars.ContextVar("use_stack", default=())
_SOURCES: contextvars.ContextVar = contextvars.ContextVar("use_sources", default=())
_INDEX: Dict[str, Tuple[Tuple, Dict[str, Dict[str, Any]]]] = {}
_CACHE: Dict[Tuple[str, Optional[int]], ResolvedUse] = {}


def canonical_sha(value: Any) -> str:
    """SHA-256 of ``value`` as sorted, compact JSON."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clear_cache() -> None:
    """Forget every indexed directory and resolved parent."""
    _INDEX.clear()
    _CACHE.clear()


# ------------------------------------------------------------------ stack
def rule_stack() -> Tuple[str, ...]:
    """Ids of the rules being validated, outermost first."""
    return _STACK.get()


@contextlib.contextmanager
def entering(rule_id: Optional[str]) -> Iterator[None]:
    """Mark ``rule_id`` as being validated (for cycle detection)."""
    if not isinstance(rule_id, str):
        yield
        return
    token = _STACK.set(_STACK.get() + (rule_id,))
    try:
        yield
    finally:
        _STACK.reset(token)


# ---------------------------------------------------------------- sources
@contextlib.contextmanager
def use_rules(*sources: Source) -> Iterator[None]:
    """Look up ``use`` parents in ``sources`` first, inside this block.

    A source is a rules directory, a rule file, or a mapping from id to the
    raw rule data. Inner blocks are searched before outer ones.
    """
    token = _SOURCES.set(tuple(sources) + _SOURCES.get())
    try:
        yield
    finally:
        _SOURCES.reset(token)


def _files(target: Path) -> List[Path]:
    if target.is_dir():
        return [
            p
            for p in sorted(target.rglob("*.y*ml"))
            if not p.name.startswith("_") and p.suffix in (".yaml", ".yml")
        ]
    return [target] if target.exists() else []


def _index(target: Path) -> Dict[str, Dict[str, Any]]:
    """``{id: raw data}`` of every parseable rule file under ``target``."""
    files = _files(target)
    signature = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        signature.append((str(path), stat.st_mtime_ns, stat.st_size))
    key = str(target.resolve())
    cached = _INDEX.get(key)
    if cached is not None and cached[0] == tuple(signature):
        return cached[1]
    found: Dict[str, Dict[str, Any]] = {}
    for path in files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue  # the loader reports it for that file
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            found.setdefault(data["id"], data)  # first wins, as in the loader
    _INDEX[key] = (tuple(signature), found)
    return found


def _default_dir() -> Path:
    from ..loader import default_rules_dir  # lazy: the loader imports us

    return default_rules_dir()


def _lookup(rule_id: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Raw data of ``rule_id`` (or None) and every id that was searched."""
    seen: List[str] = []
    for source in tuple(_SOURCES.get()) + (_default_dir(),):
        table = source if isinstance(source, Mapping) else _index(Path(source))
        if rule_id in table:
            return dict(table[rule_id]), seen
        seen.extend(table)
    return None, seen


# -------------------------------------------------------------- resolving
def _parse_target(value: Any) -> Tuple[str, Optional[int]]:
    if isinstance(value, str):
        return value, None
    if isinstance(value, Mapping) and isinstance(value.get("id"), str):
        return value["id"], value.get("version")
    if hasattr(value, "id"):
        return value.id, getattr(value, "version", None)
    raise UseError("use takes a rule id, or {id: <rule id>, version: <n>}")


def _cache_valid(hit: ResolvedUse) -> bool:
    stack = set(_STACK.get())
    for rule_id, raw_sha in hit.raw_hashes:
        if rule_id in stack:
            return False  # re-resolve so that the cycle is reported
        raw, _ = _lookup(rule_id)
        if raw is None or canonical_sha(raw) != raw_sha:
            return False
    return True


def resolve(target: Any, version: Optional[int] = None) -> ResolvedUse:
    """Resolve one ``use`` target to its parent's bound primary conditions.

    Args:
        target: a rule id, or ``{id, version}``.
        version: pin; overrides a version given in ``target``.

    Raises:
        UseError: missing id, cycle, version mismatch, parent invalid or
            without conditions.
    """
    rule_id, pinned = _parse_target(target)
    if version is not None:
        pinned = version
    stack = _STACK.get()
    if rule_id in stack:
        chain = list(stack[stack.index(rule_id) :]) + [rule_id]
        raise UseError("use cycle: " + " -> ".join(chain))
    key = (rule_id, pinned)
    hit = _CACHE.get(key)
    if hit is not None and _cache_valid(hit):
        return hit

    raw, known = _lookup(rule_id)
    if raw is None:
        guess = difflib.get_close_matches(rule_id, known, n=1, cutoff=0.5)
        hint = f" Did you mean '{guess[0]}'?" if guess else ""
        raise UseError(f"use: no rule '{rule_id}'.{hint}")

    from pydantic import ValidationError

    from ..schema import Rule, UseOf  # lazy: schema imports the predicates
    from ..tuning import bind_template

    try:
        parent = Rule.model_validate(copy.deepcopy(raw))
    except ValidationError as exc:
        cycle = [e for e in exc.errors() if "use cycle" in str(e.get("msg", ""))]
        if cycle:
            msg = cycle[0]["msg"]
            raise UseError(msg.split("Value error, ", 1)[-1]) from None
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise UseError(
            f"use: rule '{rule_id}' is not valid ({where}: {first['msg']})"
        ) from None
    if parent.conditions is None:
        raise UseError(
            f"use: rule '{rule_id}' has no conditions (status: {parent.status})"
        )
    if pinned is not None and parent.version != pinned:
        raise UseError(
            f"use: '{rule_id}' is pinned to version {pinned} but the rule is at "
            f"version {parent.version}; review the change and update the pin"
        )
    bound, _ = bind_template(copy.deepcopy(raw))
    conditions = bound["conditions"]
    sha = canonical_sha(conditions)
    lineage: List[Tuple[str, int, str]] = [(rule_id, parent.version, sha)]
    raw_hashes: List[Tuple[str, str]] = [(rule_id, canonical_sha(raw))]
    for node in _use_nodes(parent.conditions, UseOf):
        res = node.resolved
        if res is None:
            continue
        for item in res.lineage:
            if item not in lineage:
                lineage.append(item)
        for item in res.raw_hashes:
            if item not in raw_hashes:
                raw_hashes.append(item)
    out = ResolvedUse(
        rule_id, parent.version, conditions, sha, tuple(lineage), tuple(raw_hashes)
    )
    _CACHE[key] = out
    return out


# ---------------------------------------------------------------- reading
def _use_nodes(cond: Any, use_type: type) -> Iterator[Any]:
    """Every expanded ``use`` node in a validated condition tree (top level)."""
    if cond is None:
        return
    if isinstance(cond, use_type):
        yield cond
        return  # its ancestors are in its own lineage
    for name in ("all", "any", "not_", "at_least"):
        child = getattr(cond, name, None)
        if child is None:
            continue
        if name == "at_least":
            child = child.of
        for item in child if isinstance(child, list) else [child]:
            yield from _use_nodes(item, use_type)


def parents(rule: Any) -> List[ResolvedUse]:
    """The resolved ``use`` leaves of a validated rule, in tree order."""
    from ..schema import UseOf

    return [n.resolved for n in _use_nodes(rule.conditions, UseOf) if n.resolved]


def fingerprint(rule: Any) -> Dict[str, Any]:
    """What a calendar of ``rule`` depends on through ``use``.

    ``{"uses": [{id, version, sha256}, ...], "sha256": ...}`` with every
    ancestor once, in first-seen order. Equal fingerprints mean the expanded
    parent conditions are identical; a parent edited without a version bump
    changes the hash.
    """
    seen: List[Tuple[str, int, str]] = []
    for res in parents(rule):
        for item in res.lineage:
            if item not in seen:
                seen.append(item)
    uses = [{"id": i, "version": v, "sha256": s} for i, v, s in seen]
    return {"uses": uses, "sha256": canonical_sha(uses)}


def use_targets(raw_conditions: Any) -> List[str]:
    """Every rule id named by a ``use`` leaf in raw (unvalidated) conditions."""
    found: List[str] = []
    if isinstance(raw_conditions, dict):
        for key, value in raw_conditions.items():
            if key == "use":
                try:
                    found.append(_parse_target(value)[0])
                except UseError:
                    pass
            else:
                found.extend(use_targets(value))
    elif isinstance(raw_conditions, list):
        for item in raw_conditions:
            found.extend(use_targets(item))
    return found


def find_cycles(raw_rules: Mapping[str, Mapping[str, Any]]) -> List[List[str]]:
    """Every ``use`` cycle among raw rules ``{id: data}`` (each once)."""
    graph = {
        rid: use_targets((data or {}).get("conditions"))
        for rid, data in raw_rules.items()
    }
    cycles: List[List[str]] = []
    seen_keys = set()
    state: Dict[str, int] = {}
    path: List[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        path.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                cyc = path[path.index(nxt) :] + [nxt]
                key = frozenset(cyc)
                if key not in seen_keys:
                    seen_keys.add(key)
                    cycles.append(cyc)
            elif state.get(nxt) is None and nxt in graph:
                visit(nxt)
        path.pop()
        state[node] = 2

    for rid in graph:
        if state.get(rid) is None:
            visit(rid)
    return cycles


def raw_rules(sources: Sequence[Source]) -> Dict[str, Dict[str, Any]]:
    """``{id: raw data}`` from rule directories, files or mappings."""
    out: Dict[str, Dict[str, Any]] = {}
    for source in sources:
        table = source if isinstance(source, Mapping) else _index(Path(source))
        for rid, data in table.items():
            out.setdefault(rid, dict(data))
    return out
