"""Domain plan schema and validator (ADR-008 WP-93; closes S-12, S-13, S-16, D-01,
D-02, D-07, F-02, F-05, A-06 and the plan half of S-08).

A domain plan is a mapping (normally the YAML file
studies/validity/domains/<domain>.yaml). It is hashed and sealed before any
outcome is read, so nothing a result could bend may be left open. The validator
refuses a plan, with one message per problem, when

* any required key is missing (one test per key);
* any text value contains "proposal", "proposed", "default adopted" or "tbd";
* any key is a routing key (the calendar-class routing table is deleted) or
  names a primary p-method other than the block sign-flip;
* a SESOI has no source: a quoted source with page, or a checked yardstick in
  studies/validity/sesoi_sources.yaml that is not a file of this repository;
* an outcome id does not carry its market and currency (market domains);
* a vintage lacks "seen", or is not marked seen where the project already
  published numbers (earthquake 2011 onward; monthly gold and silver 2000 on);
* a snapshot hash is not pinned (64 hex characters, no "latest");
* a GARCH-X block is not secondary, or carries a_test or a verdict;
* a monsoon plan's ENSO series does not cover every explore and confirm period;
* a monsoon, flood or earthquake plan lacks the nodal and solar-cycle baselines;
* (ADR-008 A3) a plan with a yearly vintage lacks `enso.phase_base_period`; a
  SESOI's grid_x lacks the SESOI or a value on each side of it; a yes/no outcome
  with a SESOI has no named source for its base rate; a SESOI is set per test;
  a category boundary is used without the source naming the class; a yardstick's
  kind does not fit the outcome type; or a yardstick is only a candidate.

SESOI candidates (studies/validity/sesoi_sources.yaml, key "candidates") carry
the status "proposed, awaiting H18". They are listed and reported by
sesoi_report() but never usable: a plan that points at one is refused, so
verdict E stays impossible until the owner has read the number at the page and
moved the entry to "entries".

Pure Python, no outcome access, no network.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

__all__ = [
    "PlanError",
    "REQUIRED_KEYS",
    "OUTCOME_KEYS",
    "REQUIRED_SIGNOFFS",
    "SEEN_THROUGH",
    "validate_plan",
    "load_plan",
    "plan_hash",
    "can_return_e",
    "validate_sesoi_sources",
    "load_sesoi_sources",
    "sesoi_report",
    "CANDIDATE_STATUS",
]

#: Day the project's published numbers reach (ADR-008 3.2 rule 7, F-05).
SEEN_THROUGH = _dt.date(2026, 11, 22)

#: Top-level keys, all required (S-12 row of ADR-008 section 10.2).
REQUIRED_KEYS: Tuple[str, ...] = (
    "domain",
    "status",
    "seed",
    "split",
    "vintages",
    "snapshots",
    "outcomes",
    "windows",
    "merge_gap",
    "guard_bars",
    "day_convention",
    "r_measures",
    "placebo_sets",
    "baselines",
    "alpha_spending",
)

#: Keys every outcome carries.
OUTCOME_KEYS: Tuple[str, ...] = (
    "id",
    "type",
    "estimand",
    "effect_model",
    "side",
    "sesoi",
    "guard_bars",
    "grid_x",
)

REQUIRED_SIGNOFFS: Tuple[str, ...] = ("H16", "H19", "H20", "L2", "Support")

STATUSES = ("draft", "registered")
OUTCOME_TYPES = {
    "continuous": "pooled_difference",
    "absolute_return": "pooled_log_ratio",
    "event": "pooled_rate_ratio",
    "binary": "pooled_risk_ratio",
}
SIDES = ("greater", "less", "two_sided")
R_KEYS = ("R1", "R2", "R3", "R4")
MARKET_DOMAINS = {"gold", "silver"}
SLOW_CYCLE_DOMAINS = {"monsoon", "flood", "earthquake"}
SLOW_CYCLE_BASELINES = {"nodal_18_6y": "18.6-year nodal term", "solar_cycle": "solar-cycle term"}
SESOI_KINDS = (
    "daily_returns",
    "monthly_returns",
    "earthquake_rate",
    "monsoon_rainfall",
    "flood_rate",
    "daily_volatility",
    "extreme_move_risk",
    "monsoon_drought_risk",
)

#: Which yardstick kinds fit which outcome type (A3.4 item 5).
_KINDS_FOR_TYPE = {
    "continuous": ("daily_returns", "monthly_returns", "monsoon_rainfall"),
    "absolute_return": ("daily_volatility",),
    "event": ("earthquake_rate", "flood_rate"),
    "binary": ("extreme_move_risk", "monsoon_drought_risk"),
}

#: Status every unchecked candidate carries; such a candidate is never usable.
CANDIDATE_STATUS = "proposed, awaiting H18"
_CANDIDATE_FIELDS = ("id", "kind", "outcomes", "status", "citation")
_PER_TEST_KEYS = ("tests", "per_test", "per_rule", "rules", "overrides", "by_test", "by_rule")

# seen rules: (domain, grain, first seen date). A vintage whose period overlaps
# [since, SEEN_THROUGH] must carry seen: true.
_SEEN_RULES = (
    ("earthquake", None, _dt.date(2011, 1, 1)),
    ("gold", "monthly", _dt.date(2000, 1, 1)),
    ("silver", "monthly", _dt.date(2000, 1, 1)),
)

_FORBIDDEN_TEXT = re.compile(r"\b(proposals?|proposed|default[\s_-]+adopted|tbd)\b", re.I)
_ROUTING_KEY = re.compile(r"rout(e|es|ing)|calendar[_-]?class", re.I)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_PLACEHOLDER = re.compile(r"^(latest|newest|current|auto|none|tbd|)$", re.I)
_REPO_PATH = re.compile(
    r"^(\.{0,2}/|docs/|studies/|data/|libs/|site/|tests/|tools/|scripts/)"
    r"|FINDINGS_LEDGER|OWNER_DECISIONS|results\.json|ADR-\d+",
    re.I,
)


class PlanError(ValueError):
    """A plan failed validation; the errors attribute lists every problem."""

    def __init__(self, errors: Iterable[str]):
        self.errors = list(errors)
        super().__init__("invalid domain plan:\n  - " + "\n  - ".join(self.errors))


# --------------------------------------------------------------------------- helpers


def _date(value: Any, end: bool = False) -> Optional[_dt.date]:
    """Year (int), ISO date or month string, or date object, as a date; None if unreadable."""
    if isinstance(value, bool):
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, int):
        try:
            return _dt.date(value, 12, 31) if end else _dt.date(value, 1, 1)
        except ValueError:
            return None
    if isinstance(value, str):
        s = value.strip()
        try:
            if re.fullmatch(r"\d{4}", s):
                return _date(int(s), end)
            if re.fullmatch(r"\d{4}-\d{2}", s):
                y, m = int(s[:4]), int(s[5:])
                if end:
                    nxt = _dt.date(y + (m == 12), m % 12 + 1, 1)
                    return nxt - _dt.timedelta(days=1)
                return _dt.date(y, m, 1)
            return _dt.date.fromisoformat(s)
        except ValueError:
            return None
    return None


def _period(value: Any) -> Optional[Tuple[_dt.date, _dt.date]]:
    if not isinstance(value, Mapping):
        return None
    a, b = _date(value.get("start")), _date(value.get("end"), end=True)
    if a is None or b is None or a > b:
        return None
    return a, b


def _walk(obj: Any, path: str = "") -> Iterable[Tuple[str, Any, Any]]:
    """Yield (path, key, value) for every mapping entry and (path, None, str) for list strings."""
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            yield p, k, v
            yield from _walk(v, p)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            p = f"{path}[{i}]"
            if isinstance(v, str):
                yield p, None, v
            yield from _walk(v, p)


def _ids(items: Any) -> List[str]:
    out = []
    for it in items or []:
        if isinstance(it, str):
            out.append(it)
        elif isinstance(it, Mapping) and isinstance(it.get("id"), str):
            out.append(it["id"])
    return out


# --------------------------------------------------------------------------- sesoi sources

_SOURCE_FIELDS = (
    "id",
    "kind",
    "citation",
    "page",
    "number_as_printed",
    "conversion",
    "converted_value",
    "checker",
    "date",
)


def _check_citation(citation: Any) -> bool:
    return isinstance(citation, str) and bool(citation.strip()) and not _REPO_PATH.search(citation.strip())


def validate_sesoi_sources(doc: Any) -> List[str]:
    """Errors for the yardstick table (studies/validity/sesoi_sources.yaml)."""
    errs: List[str] = []
    if not isinstance(doc, Mapping):
        return ["sesoi_sources: not a mapping"]
    if doc.get("schema_version") != 1:
        errs.append("sesoi_sources: schema_version must be 1")
    entries = doc.get("entries")
    if not isinstance(entries, list):
        return errs + ["sesoi_sources: 'entries' must be a list (empty is allowed)"]
    seen_ids = set()
    for i, e in enumerate(entries):
        where = f"sesoi_sources.entries[{i}]"
        if not isinstance(e, Mapping):
            errs.append(f"{where}: not a mapping")
            continue
        for f in _SOURCE_FIELDS:
            if e.get(f) in (None, "", []):
                errs.append(f"{where}: missing '{f}'")
        if e.get("id") in seen_ids:
            errs.append(f"{where}: duplicate id '{e.get('id')}'")
        seen_ids.add(e.get("id"))
        if e.get("kind") not in SESOI_KINDS and e.get("kind") not in (None, ""):
            errs.append(f"{where}: kind '{e.get('kind')}' not in {list(SESOI_KINDS)}")
        if e.get("citation") not in (None, "") and not _check_citation(e.get("citation")):
            errs.append(f"{where}: citation must be an external publication, not a file of this repository")
        if e.get("date") not in (None, "") and _date(e.get("date")) is None:
            errs.append(f"{where}: date must be ISO")
        cv = e.get("converted_value")
        if cv is not None and (isinstance(cv, bool) or not isinstance(cv, (int, float))):
            errs.append(f"{where}: converted_value must be a number")
    cands = doc.get("candidates", [])
    if not isinstance(cands, list):
        return errs + ["sesoi_sources: 'candidates' must be a list"]
    for i, c in enumerate(cands):
        where = f"sesoi_sources.candidates[{i}]"
        if not isinstance(c, Mapping):
            errs.append(f"{where}: not a mapping")
            continue
        for f in _CANDIDATE_FIELDS:
            if c.get(f) in (None, "", []):
                errs.append(f"{where}: missing '{f}'")
        if c.get("id") in seen_ids:
            errs.append(f"{where}: duplicate id '{c.get('id')}'")
        seen_ids.add(c.get("id"))
        if c.get("status") not in (None, "") and c.get("status") != CANDIDATE_STATUS:
            errs.append(f"{where}: status must be '{CANDIDATE_STATUS}' (a checked entry belongs in 'entries')")
        if c.get("kind") not in SESOI_KINDS and c.get("kind") not in (None, ""):
            errs.append(f"{where}: kind '{c.get('kind')}' not in {list(SESOI_KINDS)}")
        if c.get("outcomes") not in (None, "") and not (
            isinstance(c["outcomes"], list) and all(isinstance(x, str) and x for x in c["outcomes"])
        ):
            errs.append(f"{where}: outcomes must be a list of outcome ids")
        if c.get("citation") not in (None, "") and not _check_citation(c.get("citation")):
            errs.append(f"{where}: citation must be an external publication, not a file of this repository")
        for f in ("converted_value", "checker", "number_as_printed"):
            if c.get(f) not in (None, ""):
                errs.append(f"{where}: '{f}' is filled; once the owner has read the page, move it to 'entries'")
    return errs


def load_sesoi_sources(path: Any) -> Dict[str, Any]:
    """Load and validate the yardstick table; raise PlanError on any problem."""
    import yaml

    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    errs = validate_sesoi_sources(doc)
    if errs:
        raise PlanError(errs)
    return doc


def _candidate_table(sesoi_sources: Any) -> Dict[str, Mapping]:
    if not isinstance(sesoi_sources, Mapping):
        return {}
    return {
        c["id"]: c for c in sesoi_sources.get("candidates") or [] if isinstance(c, Mapping) and "id" in c
    }


def sesoi_report(plan: Any, sesoi_sources: Any = None) -> List[Dict[str, Any]]:
    """Per outcome: is a SESOI in force, can E be returned, and which candidates wait for H18.

    A candidate is always reported as not usable for E (status "proposed,
    awaiting H18"); only a validated plan SESOI backed by a checked entry or a
    quoted source counts. Pure reporting; it changes nothing.
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(plan, Mapping):
        return out
    table = _sesoi_table(sesoi_sources)
    cands = _candidate_table(sesoi_sources)
    for i, o in enumerate(plan.get("outcomes") or []):
        if not isinstance(o, Mapping):
            continue
        errs: List[str] = []
        _check_sesoi(o, f"outcomes[{i}]", table, errs, cands)
        usable = can_return_e(o) and not errs
        waiting = [
            {"id": c["id"], "status": c.get("status"), "usable_for_e": False,
             "recommended": bool(c.get("recommended"))}
            for c in cands.values()
            if o.get("id") in (c.get("outcomes") or [])
        ]
        if usable:
            note = "SESOI in force"
        elif waiting:
            note = "no SESOI in force; candidates await the owner (H18): E not usable, X95 and X-strict only"
        else:
            note = "no SESOI and no candidate: E impossible, X95 and X-strict only"
        out.append({"outcome": o.get("id"), "usable_for_e": usable, "candidates": waiting,
                    "problems": errs, "note": note})
    return out


def _sesoi_table(sesoi_sources: Any) -> Dict[str, Mapping]:
    if not sesoi_sources:
        return {}
    entries = sesoi_sources.get("entries", []) if isinstance(sesoi_sources, Mapping) else sesoi_sources
    return {e["id"]: e for e in entries if isinstance(e, Mapping) and "id" in e}


# --------------------------------------------------------------------------- validation


def _check_sesoi(
    o: Mapping,
    where: str,
    table: Dict[str, Mapping],
    errs: List[str],
    cands: Optional[Dict[str, Mapping]] = None,
) -> None:
    if "sesoi" not in o:
        return  # reported as missing key
    s = o["sesoi"]
    if s is None:
        return  # explicit "no SESOI": E impossible (7.2 rule 3)
    if not isinstance(s, Mapping):
        errs.append(f"{where}.sesoi: must be null (no SESOI) or a mapping")
        return
    v = s.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
        errs.append(f"{where}.sesoi.value: must be a positive number")
    for k in _PER_TEST_KEYS:
        if k in s:
            errs.append(f"{where}.sesoi.{k}: one SESOI per (domain, outcome); no per-test values (A3.4 item 1)")
    # A3.2 item 7: grid_x holds the SESOI and a value on each side
    grid = o.get("grid_x")
    if (
        isinstance(grid, list)
        and grid
        and all(isinstance(g, (int, float)) and not isinstance(g, bool) for g in grid)
        and isinstance(v, (int, float))
        and not isinstance(v, bool)
        and v > 0
    ):
        if not any(math.isclose(g, v, rel_tol=1e-9, abs_tol=1e-12) for g in grid):
            errs.append(f"{where}.grid_x: must contain the SESOI {v} (A3.2 item 7)")
        if not any(g < v and not math.isclose(g, v, rel_tol=1e-9) for g in grid) or not any(
            g > v and not math.isclose(g, v, rel_tol=1e-9) for g in grid
        ):
            errs.append(f"{where}.grid_x: needs at least one value on each side of the SESOI (A3.2 item 7)")
    # a yes/no outcome with a SESOI needs a base rate from a named publication
    if o.get("type") == "binary":
        br = o.get("base_rate")
        if isinstance(br, bool) or not isinstance(br, (int, float)) or not 0 < br < 1:
            errs.append(f"{where}.base_rate: a binary outcome with a SESOI needs a base rate in (0, 1)")
        if not (isinstance(o.get("base_rate_source"), str) and o["base_rate_source"].strip()):
            errs.append(f"{where}.base_rate_source: the base rate must come from a named publication (A3.2 item 7)")
    kind = s.get("kind")
    if kind == "source":
        for f in ("rule_id", "page", "quotation"):
            if not s.get(f):
                errs.append(f"{where}.sesoi: kind 'source' needs '{f}'")
        if s.get("category_boundary"):  # A3.4 item 4
            word = str(s.get("class_word") or "").strip().lower()
            if not word or word not in str(s.get("quotation") or "").lower():
                errs.append(
                    f"{where}.sesoi: a category boundary is not an effect size; the quotation must contain "
                    "the class word (class_word) the source itself uses (A3.4 item 4)"
                )
            if not s.get("band_citation"):
                errs.append(f"{where}.sesoi: a category boundary needs 'band_citation' for the number")
    elif kind == "yardstick":
        yid = s.get("yardstick_id")
        entry = table.get(yid)
        if entry is None and cands and yid in cands:
            errs.append(
                f"{where}.sesoi: yardstick_id '{yid}' is a candidate ('{cands[yid].get('status')}'); "
                "not usable for E until the owner has checked it at the page (H18)"
            )
        elif entry is None:
            errs.append(f"{where}.sesoi: yardstick_id '{yid}' has no entry in sesoi_sources")
        else:
            allowed = _KINDS_FOR_TYPE.get(o.get("type"))
            if allowed and entry.get("kind") not in allowed:
                errs.append(
                    f"{where}.sesoi: yardstick kind '{entry.get('kind')}' does not fit outcome type "
                    f"'{o.get('type')}' (allowed: {list(allowed)})"
                )
            missing = [f for f in _SOURCE_FIELDS if entry.get(f) in (None, "", [])]
            if missing:
                errs.append(f"{where}.sesoi: sesoi_sources entry '{yid}' lacks {missing}")
            if not entry.get("page") or not entry.get("checker"):
                errs.append(f"{where}.sesoi: sesoi_sources entry '{yid}' needs page and checker")
            if not _check_citation(entry.get("citation")):
                errs.append(f"{where}.sesoi: sesoi_sources entry '{yid}' cites a file of this repository")
            if entry.get("converted_value") != v:
                errs.append(f"{where}.sesoi.value must equal sesoi_sources '{yid}' converted_value")
    else:
        errs.append(
            f"{where}.sesoi.kind: must be 'source' or 'yardstick' (no value is chosen by the project), got {kind!r}"
        )


def _check_outcomes(
    plan: Mapping, table: Dict[str, Mapping], errs: List[str], cands: Optional[Dict[str, Mapping]] = None
) -> None:
    outcomes = plan.get("outcomes")
    if not isinstance(outcomes, list) or not outcomes:
        if "outcomes" in plan:
            errs.append("outcomes: must be a non-empty list")
        return
    domain = plan.get("domain")
    seen_ids = set()
    for i, o in enumerate(outcomes):
        where = f"outcomes[{i}]"
        if not isinstance(o, Mapping):
            errs.append(f"{where}: not a mapping")
            continue
        for k in OUTCOME_KEYS:
            if k not in o or (k != "sesoi" and o[k] in (None, "", [])):
                errs.append(f"{where}: missing key '{k}'")
        oid = o.get("id")
        if isinstance(oid, str):
            if oid in seen_ids:
                errs.append(f"{where}: duplicate outcome id '{oid}'")
            seen_ids.add(oid)
        typ, est = o.get("type"), o.get("estimand")
        if typ is not None and typ not in OUTCOME_TYPES:
            errs.append(f"{where}.type: '{typ}' not in {sorted(OUTCOME_TYPES)}")
        elif typ is not None and est is not None and est != OUTCOME_TYPES[typ]:
            errs.append(f"{where}.estimand: type '{typ}' is tested with '{OUTCOME_TYPES[typ]}', got '{est}'")
        if o.get("side") is not None and o["side"] not in SIDES:
            errs.append(f"{where}.side: must be one of {list(SIDES)} (there is no default side)")
        gb = o.get("guard_bars")
        if gb is not None and (isinstance(gb, bool) or not isinstance(gb, int) or gb < 0):
            errs.append(f"{where}.guard_bars: must be an integer >= 0")
        grid = o.get("grid_x")
        if grid is not None:
            ok = (
                isinstance(grid, list)
                and len(grid) >= 2
                and all(isinstance(g, (int, float)) and not isinstance(g, bool) for g in grid)
                and all(a < b for a, b in zip(grid, grid[1:]))
            )
            if not ok:
                errs.append(f"{where}.grid_x: must be a strictly increasing list of at least 2 numbers")
        if typ == "event" and not o.get("counting_unit"):
            errs.append(f"{where}: event outcomes need 'counting_unit'")
        if typ == "absolute_return" and not o.get("floor"):
            errs.append(f"{where}: absolute_return outcomes need the log-scale 'floor'")
        # outcome ids carry market and currency (A-06, D-02)
        if domain in MARKET_DOMAINS or o.get("market") or o.get("currency"):
            for f in ("market", "currency"):
                if not o.get(f):
                    errs.append(f"{where}: missing key '{f}' (outcome ids name market and currency)")
            if isinstance(oid, str):
                tokens = set(re.split(r"[_:\-.\s]+", oid.lower()))
                for f in ("market", "currency"):
                    val = o.get(f)
                    if isinstance(val, str) and val.strip() and val.lower() not in tokens:
                        errs.append(f"{where}.id '{oid}' must contain the {f} '{val}'")
        _check_sesoi(o, where, table, errs, cands)


def _check_vintages(plan: Mapping, errs: List[str]) -> List[Tuple[_dt.date, _dt.date]]:
    spans: List[Tuple[_dt.date, _dt.date]] = []
    vs = plan.get("vintages")
    if not isinstance(vs, list) or not vs:
        if "vintages" in plan:
            errs.append("vintages: must be a non-empty list")
        return spans
    domain = plan.get("domain")
    for i, v in enumerate(vs):
        where = f"vintages[{i}]"
        if not isinstance(v, Mapping):
            errs.append(f"{where}: not a mapping")
            continue
        for k in ("id", "snapshot", "grain", "confirm_period", "seen"):
            if k not in v or v[k] in (None, "", {}):
                errs.append(f"{where}: missing key '{k}'" + (" (every vintage states seen)" if k == "seen" else ""))
        if "seen" in v and v["seen"] is not None and not isinstance(v["seen"], bool):
            errs.append(f"{where}.seen: must be true or false")
        per = _period(v.get("confirm_period"))
        if v.get("confirm_period") not in (None, "", {}) and per is None:
            errs.append(f"{where}.confirm_period: needs readable start and end, start <= end")
        if per:
            spans.append(per)
            for rule_domain, grain, since in _SEEN_RULES:
                if domain != rule_domain or (grain and v.get("grain") != grain):
                    continue
                if per[1] >= since and per[0] <= SEEN_THROUGH and v.get("seen") is not True:
                    errs.append(
                        f"{where}: confirm period overlaps published numbers (from {since}); seen must be true"
                    )
    return spans


def _check_split(plan: Mapping, errs: List[str]) -> List[Tuple[_dt.date, _dt.date]]:
    spans: List[Tuple[_dt.date, _dt.date]] = []
    sp = plan.get("split")
    if sp is None:
        return spans
    if not isinstance(sp, Mapping):
        errs.append("split: must be a mapping with explore (and confirm)")
        return spans
    exp = _period(sp.get("explore"))
    if exp is None:
        errs.append("split.explore: needs readable start and end")
    else:
        spans.append(exp)
    if sp.get("confirm") is not None:
        c = _period(sp["confirm"])
        if c is None:
            errs.append("split.confirm: needs readable start and end")
        else:
            spans.append(c)
            if exp and c[0] <= exp[1]:
                errs.append("split: confirm must start after explore ends")
    return spans


def _check_snapshots(plan: Mapping, snapshot_index: Any, errs: List[str]) -> None:
    snaps = plan.get("snapshots")
    if not isinstance(snaps, list) or not snaps:
        if "snapshots" in plan:
            errs.append("snapshots: must be a non-empty list of pinned snapshots")
        return
    known = None
    if snapshot_index is not None:
        items = snapshot_index.get("snapshots", []) if isinstance(snapshot_index, Mapping) else snapshot_index
        known = {s.get("sha256") for s in items if isinstance(s, Mapping)}
    ids = set()
    for i, s in enumerate(snaps):
        where = f"snapshots[{i}]"
        if not isinstance(s, Mapping):
            errs.append(f"{where}: not a mapping")
            continue
        for k in ("id", "file", "sha256"):
            if not s.get(k):
                errs.append(f"{where}: missing key '{k}'")
        ids.add(s.get("id"))
        h = s.get("sha256")
        if h and (not isinstance(h, str) or _PLACEHOLDER.match(h) or not _HEX64.match(h)):
            errs.append(f"{where}.sha256: must be a pinned 64-hex hash (no 'latest' or 'newest' fallback)")
        elif h and known is not None and h not in known:
            errs.append(f"{where}.sha256: not in the snapshot index")
    for i, v in enumerate(plan.get("vintages") or []):
        if isinstance(v, Mapping) and v.get("snapshot") and v["snapshot"] not in ids:
            errs.append(f"vintages[{i}].snapshot '{v['snapshot']}' is not a pinned snapshot id")


def _check_monsoon(plan: Mapping, spans: List[Tuple[_dt.date, _dt.date]], errs: List[str]) -> None:
    yearly = any(isinstance(v, Mapping) and v.get("grain") == "yearly" for v in plan.get("vintages") or [])
    if plan.get("domain") != "monsoon" and not yearly:
        return
    enso = plan.get("enso")
    if not isinstance(enso, Mapping):
        errs.append("enso: a monsoon or yearly plan needs one ENSO series ('enso' mapping with series_id, sha256, covers)")
        return
    for k in ("series_id", "sha256", "covers"):
        if not enso.get(k):
            errs.append(f"enso: missing key '{k}'")
    h = enso.get("sha256")
    if h and (not isinstance(h, str) or not _HEX64.match(h)):
        errs.append("enso.sha256: must be a pinned 64-hex hash")
    cov = _period(enso.get("covers"))
    if enso.get("covers") and cov is None:
        errs.append("enso.covers: needs readable start and end")
    if yearly:  # A3.1 item 2: the anomaly base period of the phase threshold
        base = _period(enso.get("phase_base_period"))
        if base is None:
            errs.append("enso.phase_base_period: a yearly plan needs the anomaly base period (start and end)")
        elif cov and (base[0] < cov[0] or base[1] > cov[1]):
            errs.append("enso.phase_base_period: must lie inside the ENSO series' covers")
    if cov:
        for a, b in spans:
            if a < cov[0] or b > cov[1]:
                errs.append(
                    f"enso: series covers {cov[0]}..{cov[1]} but the plan uses {a}..{b}; one ENSO series must "
                    "cover explore and confirm periods"
                )


def _check_misc(plan: Mapping, errs: List[str]) -> None:
    for k in ("merge_gap", "guard_bars"):
        v = plan.get(k)
        if k in plan and (isinstance(v, bool) or not isinstance(v, int) or v < 0):
            errs.append(f"{k}: must be an integer >= 0")
    if plan.get("status") is not None and plan["status"] not in STATUSES:
        errs.append(f"status: must be one of {list(STATUSES)}")
    if "seed" in plan and (isinstance(plan["seed"], bool) or not isinstance(plan["seed"], (int, str)) or plan["seed"] == ""):
        errs.append("seed: must be an integer or a non-empty string")
    for k in ("windows", "placebo_sets", "baselines"):
        if k in plan and not isinstance(plan[k], (list, dict)):
            errs.append(f"{k}: must be a list or a mapping")
    rm = plan.get("r_measures")
    if isinstance(rm, Mapping):
        for r in R_KEYS:
            e = rm.get(r)
            if not isinstance(e, Mapping) or not e.get("measure") or e.get("threshold") is None:
                errs.append(f"r_measures.{r}: needs 'measure' and 'threshold'")
    elif "r_measures" in plan:
        errs.append("r_measures: must be a mapping with R1 to R4")
    a = plan.get("alpha_spending")
    if isinstance(a, Mapping):
        first, ratio, mv = a.get("first"), a.get("ratio"), a.get("max_variants")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (first, ratio, mv)):
            errs.append("alpha_spending: needs numeric 'first', 'ratio' and 'max_variants'")
        else:
            if not (0 < ratio < 1) or first <= 0 or first / (1 - ratio) > 0.05 + 1e-12:
                errs.append("alpha_spending: first / (1 - ratio) must be at most 0.05")
            if mv > 3:
                errs.append("alpha_spending.max_variants: at most 3 (ADR-008 3.2 rule 8)")
    elif "alpha_spending" in plan:
        errs.append("alpha_spending: must be a mapping")
    # baselines for slow physical cycles (F-02)
    if plan.get("domain") in SLOW_CYCLE_DOMAINS and isinstance(plan.get("baselines"), (list, dict)):
        have = set(_ids(plan["baselines"])) if isinstance(plan["baselines"], list) else set(plan["baselines"])
        for b, label in SLOW_CYCLE_BASELINES.items():
            if b not in have:
                errs.append(f"baselines: a {plan['domain']} plan needs the '{b}' baseline ({label})")
    # GARCH-X is secondary, with no a_test and no verdict (S-16)
    for path, key, val in _walk(plan):
        if key and re.fullmatch(r"garch[_-]?x", str(key), re.I):
            if not isinstance(val, Mapping) or val.get("role") != "secondary":
                errs.append(f"{path}: GARCH-X must be labelled role: secondary")
            elif "a_test" in val or "verdict" in val:
                errs.append(f"{path}: GARCH-X has no a_test and no verdict")
    # sign-offs (no batch closes under an unsigned owner decision)
    if plan.get("status") == "registered":
        so = plan.get("owner_signoffs")
        need = list(REQUIRED_SIGNOFFS)
        if any(isinstance(o, Mapping) and o.get("sesoi") for o in plan.get("outcomes") or []):
            need.append("H18")
        for dec in need:
            if not isinstance(so, Mapping) or _date(so.get(dec)) is None:
                errs.append(f"owner_signoffs.{dec}: a registered plan needs the owner's sign-off date")


def validate_plan(
    plan: Any,
    *,
    sesoi_sources: Any = None,
    snapshot_index: Any = None,
) -> List[str]:
    """Return every problem found (empty list: the plan is complete).

    sesoi_sources is the loaded yardstick table (or its entry list);
    snapshot_index the loaded data/snapshot_index.json (optional cross-check).
    """
    if not isinstance(plan, Mapping):
        return ["plan: not a mapping"]
    errs: List[str] = []
    for k in REQUIRED_KEYS:
        v = plan.get(k)
        zero_ok = k in ("merge_gap", "guard_bars", "seed") and isinstance(v, int) and not isinstance(v, bool)
        if not zero_ok and (v is None or v == "" or v == [] or v == {}):
            errs.append(f"missing required key '{k}'")
    # forbidden words and routing keys, anywhere
    for path, key, val in _walk(plan):
        if key is not None and _ROUTING_KEY.search(str(key)):
            errs.append(f"{path}: routing keys are not allowed (one primary method for every outcome)")
        if key is not None and str(key) in ("p_method", "primary_test", "primary_method"):
            if val != "block_signflip":
                errs.append(f"{path}: the primary test is 'block_signflip' for every outcome")
        if isinstance(val, str):
            m = _FORBIDDEN_TEXT.search(val)
            if m:
                errs.append(f"{path}: the word '{m.group(0)}' is refused; nothing in a plan may be open")
    table = _sesoi_table(sesoi_sources)
    _check_outcomes(plan, table, errs, _candidate_table(sesoi_sources))
    for k in plan:
        if re.fullmatch(r"sesoi[_-]?(by|per|override).*", str(k), re.I):
            errs.append(f"{k}: one SESOI per (domain, outcome), set inside the outcome (A3.4 item 1)")
    spans = _check_split(plan, errs) + _check_vintages(plan, errs)
    _check_snapshots(plan, snapshot_index, errs)
    _check_monsoon(plan, spans, errs)
    _check_misc(plan, errs)
    return errs


def load_plan(path: Any, *, sesoi_sources_path: Any = None, snapshot_index_path: Any = None) -> Dict[str, Any]:
    """Load and validate a YAML plan; raise PlanError with every problem."""
    import yaml

    plan = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sesoi = load_sesoi_sources(sesoi_sources_path) if sesoi_sources_path else None
    index = json.loads(Path(snapshot_index_path).read_text(encoding="utf-8")) if snapshot_index_path else None
    errs = validate_plan(plan, sesoi_sources=sesoi, snapshot_index=index)
    if errs:
        raise PlanError(errs)
    return plan


def plan_hash(plan: Mapping) -> str:
    """SHA-256 of the canonical JSON form of a plan (what the seal records)."""
    blob = json.dumps(plan, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def can_return_e(outcome: Mapping) -> bool:
    """Verdict E needs a SESOI; no SESOI (explicit null) means E is impossible (7.2 rule 3)."""
    return isinstance(outcome, Mapping) and isinstance(outcome.get("sesoi"), Mapping) and bool(outcome["sesoi"])
