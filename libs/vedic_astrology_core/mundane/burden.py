"""Search burden, plan checks and the minimal detectable effect (ADR-006 WP-55).

Three jobs, none of which reads an outcome:

* :func:`load_plan` reads ``studies/mundane/hypothesis.yaml`` (schema
  ``mundane-plan/1``) strictly: an unknown or missing top-level key fails.
* :func:`plan_tests` flattens the declared families into one
  :class:`TestSpec` per omnibus test (one partition = one test, section
  5.3.3). A test whose predicate reads only the natal chart is refused: the
  founding chart never changes, so such a factor is true at every event and
  every control date (section 5.1, "purely natal factors").
* :func:`burden_report` reproduces the counts of section 5.1 for the full D1
  to D9 setting, recomputes the plan's declared counts (and fails on any
  difference), checks the budgets of section 5.3.5 (and fails a plan over
  budget) and rebuilds the minimal-detectable-effect table of section 5.4.

The MDE here is the exact calculation the table was built with: a one-sided
exact binomial test on the count of events with the factor active, the event
count fixed and events independent. It is deterministic.
``core/stats/power.py: minimum_detectable_rate_ratio`` answers a related
question by simulation (Poisson event total, conditional test) and gives the
same figures only to within simulation noise, so it is not used for the table.
"""

from __future__ import annotations

import json
from functools import lru_cache
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import yaml
from scipy import stats as sps
from scipy.optimize import brentq

from vedic_astrology_core.stats.manifest import file_sha256

REPO_ROOT = Path(__file__).resolve().parents[3]
PLAN_FILE = REPO_ROOT / "studies" / "mundane" / "hypothesis.yaml"
PLAN_SCHEMA = "mundane-plan/1"

#: Top-level keys of a mundane-plan/1 file. All are required.
PLAN_KEYS = (
    "schema", "id", "version", "lineage", "status", "registered_on",
    "registered_commit", "scope", "question", "inputs", "settings", "charts",
    "events", "periods", "windows", "stability", "testability", "method_gate",
    "families", "declared_counts", "shown_not_tested", "excluded", "controls",
    "statistics", "budgets", "mde", "calibration", "outputs", "reporting",
    "amendments",
)
_TEST_KEYS = ("id", "predicate", "params", "cell_param", "cells", "needs_stable", "methods")
_FAMILY_KEYS = ("id", "label", "tests")
_FAMILY_OPTIONAL = ("partition_cells", "collapse")

#: Predicates whose value moves with the moment: the running dasha lord or a
#: transiting graha, read against the natal frame. Any other predicate that
#: needs the natal chart reads only the natal chart and is purely natal.
MOVING_PREDICATES = frozenset({
    "dasha_lord_is",
    "antardasha_lord_is",
    "dasha_lord_in_house",
    "dasha_lord_rules_house",
    "dasha_lord_dignity",
    "transit_in_house_from_natal",
    "transit_conjunct_natal",
    "transit_aspects_natal",
})

#: The mean five-state dignity partition of the plan (family F3).
DIGNITY_STATES = 5
#: Block J of section 5.1 (event-sky factors) is a catalogue count, "about 470".
EVENT_SKY_FACTORS = 470
#: Mean count of houses a dasha lord rules: Sun and Moon one, five grahas two,
#: the nodes none (Parashari sign lords): 12 / 9.
MEAN_HOUSES_RULED = 12.0 / 9.0
#: Graha drishti (special aspects) per graha, as in rules/predicates/relations.py.
DRISHTI_COUNT = {"Sun": 1, "Moon": 1, "Mercury": 1, "Venus": 1, "Mars": 3,
                 "Jupiter": 3, "Saturn": 3, "Rahu": 1, "Ketu": 1}


class PlanError(ValueError):
    """The plan breaks its schema or a rule of section 5.3."""


class BudgetExceeded(PlanError):
    """The plan declares more omnibus tests than a budget allows."""


class NatalFactorError(PlanError):
    """A purely natal factor was put into a tested family."""


# ------------------------------------------------------------------- plan
@dataclass(frozen=True)
class Plan:
    """A loaded plan and the SHA-256 of its file."""

    data: Dict[str, Any]
    sha256: str
    path: Optional[Path] = None

    @property
    def sha12(self) -> str:
        return self.sha256[:12]

    def __getitem__(self, key: str) -> Any:
        return self.data[key]


def load_plan(path: Union[str, Path] = PLAN_FILE) -> Plan:
    """Load and check a mundane-plan/1 file (unknown or missing keys fail)."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    check_plan_keys(data)
    plan = Plan(data=data, sha256=file_sha256(path), path=path)
    plan_tests(plan)  # validates every family and test
    return plan


def plan_from_dict(data: Dict[str, Any], sha256: str = "0" * 64) -> Plan:
    """A plan built in memory (tests, simulations). Same checks as :func:`load_plan`."""
    check_plan_keys(data)
    plan = Plan(data=data, sha256=sha256)
    plan_tests(plan)
    return plan


def check_plan_keys(data: Any) -> None:
    if not isinstance(data, dict):
        raise PlanError("plan: top level must be a mapping")
    if data.get("schema") != PLAN_SCHEMA:
        raise PlanError(f"plan: schema must be {PLAN_SCHEMA!r}, got {data.get('schema')!r}")
    unknown = sorted(set(data) - set(PLAN_KEYS))
    if unknown:
        raise PlanError(f"plan: unknown key(s) {unknown}")
    missing = [k for k in PLAN_KEYS if k not in data]
    if missing:
        raise PlanError(f"plan: missing key(s) {missing}")


@dataclass(frozen=True)
class TestSpec:
    """One declared omnibus test: a partition of mutually exclusive cells."""

    id: str
    family: str
    predicate: str
    params: Dict[str, Any]
    cell_param: str
    cells: Tuple[Any, ...]
    needs_stable: Tuple[str, ...]
    methods: Tuple[str, ...]
    #: Dignity partitions: collapsed cell -> raw dignities, and the raw priority.
    collapse: Optional[Dict[str, Tuple[str, ...]]] = None
    priority: Optional[Tuple[str, ...]] = None
    #: The predicate's parameter that receives a cell (e.g. "lords" for cell_param "lord").
    param_name: str = field(default="")

    __test__ = False  # not a pytest class

    def factor_id(self, cell: Any) -> str:
        """Factor id of one cell: ``<test_id>:<cell>``."""
        return f"{self.id}:{cell}"

    def cell_params(self, cell: Any) -> Dict[str, Any]:
        """Predicate parameters that make the predicate true exactly on ``cell``."""
        p = dict(self.params)
        if self.collapse is not None:
            p[self.param_name] = list(self.collapse[cell])
        else:
            p[self.param_name] = [cell]
        return p


def _resolve_param(predicate: str, cell_param: str, where: str) -> str:
    from vedic_astrology_core.rules.predicates import PREDICATES

    spec = PREDICATES[predicate]
    names = set()
    for name, info in spec.params.model_fields.items():
        names.add(name)
        if info.alias:
            names.add(info.alias)
    plural = cell_param[:-1] + "ies" if cell_param.endswith("y") else cell_param + "s"
    for cand in (cell_param, plural):
        if cand in names:
            return cand
    raise PlanError(f"{where}: predicate {predicate!r} has no parameter {cell_param!r}")


def check_moving(predicate: str, where: str = "test") -> None:
    """Refuse a predicate that reads only the natal chart (section 5.1)."""
    from vedic_astrology_core.rules.predicates import PREDICATES

    if predicate not in PREDICATES:
        raise PlanError(f"{where}: predicate {predicate!r} is not registered")
    if "natal" in PREDICATES[predicate].needs and predicate not in MOVING_PREDICATES:
        raise NatalFactorError(
            f"{where}: {predicate!r} is a purely natal factor; it is constant per "
            "chart and cannot separate events from control dates (case file only)"
        )


def plan_tests(plan: Union[Plan, Mapping[str, Any]]) -> List[TestSpec]:
    """Every declared omnibus test, in plan order. Validates the families."""
    from vedic_astrology_core.rules.predicates import PREDICATES

    data = plan.data if isinstance(plan, Plan) else plan
    families = data.get("families")
    if not isinstance(families, list) or not families:
        raise PlanError("plan: families must be a non-empty list")
    out: List[TestSpec] = []
    seen_tests, seen_fam = set(), set()
    for fam in families:
        fid = fam.get("id") if isinstance(fam, dict) else None
        where = f"family {fid}"
        if not isinstance(fam, dict):
            raise PlanError("plan: each family must be a mapping")
        unknown = sorted(set(fam) - set(_FAMILY_KEYS) - set(_FAMILY_OPTIONAL))
        if unknown:
            raise PlanError(f"{where}: unknown key(s) {unknown}")
        missing = [k for k in _FAMILY_KEYS if k not in fam]
        if missing:
            raise PlanError(f"{where}: missing key(s) {missing}")
        if fid in seen_fam:
            raise PlanError(f"{where}: duplicate family id")
        seen_fam.add(fid)
        if not isinstance(fam["tests"], list) or not fam["tests"]:
            raise PlanError(f"{where}: tests must be a non-empty list")
        collapse = priority = None
        if "collapse" in fam:
            c = dict(fam["collapse"])
            priority = tuple(c.pop("priority", ()) or ())
            collapse = {k: tuple(v) for k, v in c.items()}
            raw = [d for v in collapse.values() for d in v]
            if len(raw) != len(set(raw)):
                raise PlanError(f"{where}: a raw state is collapsed into two cells")
            if set(priority) != set(raw):
                raise PlanError(f"{where}: collapse.priority must list every raw state once")
        for t in fam["tests"]:
            tid = t.get("id") if isinstance(t, dict) else None
            tw = f"test {tid}"
            if not isinstance(t, dict):
                raise PlanError(f"{where}: each test must be a mapping")
            unknown = sorted(set(t) - set(_TEST_KEYS))
            if unknown:
                raise PlanError(f"{tw}: unknown key(s) {unknown}")
            missing = [k for k in _TEST_KEYS if k not in t]
            if missing:
                raise PlanError(f"{tw}: missing key(s) {missing}")
            if tid in seen_tests:
                raise PlanError(f"{tw}: duplicate test id")
            seen_tests.add(tid)
            check_moving(t["predicate"], tw)
            cells = tuple(t["cells"])
            if len(cells) < 2 or len(set(cells)) != len(cells):
                raise PlanError(f"{tw}: a partition needs two or more distinct cells")
            if collapse is not None and set(cells) != set(collapse):
                raise PlanError(f"{tw}: cells must equal the family's collapsed states")
            pname = _resolve_param(t["predicate"], t["cell_param"], tw)
            spec = TestSpec(
                id=str(tid), family=str(fid), predicate=t["predicate"],
                params=dict(t["params"] or {}), cell_param=t["cell_param"], cells=cells,
                needs_stable=tuple(t["needs_stable"] or ()), methods=tuple(t["methods"]),
                collapse=collapse, priority=priority, param_name=pname,
            )
            pred = PREDICATES[spec.predicate]
            if collapse is not None:
                # A raw state the predicate refuses for these parameters (moolatrikona
                # outside D1) cannot occur there; it is dropped from its cell.
                valid = {}
                for cell in cells:
                    keep = []
                    for raw_state in collapse[cell]:
                        try:
                            pred.params.model_validate({**spec.params, pname: [raw_state]})
                            keep.append(raw_state)
                        except Exception:
                            continue
                    if not keep:
                        raise PlanError(f"{tw}: cell {cell!r} has no valid raw state")
                    valid[cell] = tuple(keep)
                spec = replace(spec, collapse=valid,
                               priority=tuple(r for r in priority if any(r in v for v in valid.values())))
            for cell in cells:  # every cell must be a valid parameter set
                try:
                    pred.params.model_validate(spec.cell_params(cell))
                except Exception as exc:  # pydantic ValidationError and friends
                    raise PlanError(f"{tw}: cell {cell!r} is not a valid parameter: {exc}")
            out.append(spec)
    return out


def family_ids(plan: Union[Plan, Mapping[str, Any]]) -> List[str]:
    data = plan.data if isinstance(plan, Plan) else plan
    return [f["id"] for f in data["families"]]


def count_plan(plan: Union[Plan, Mapping[str, Any]]) -> Dict[str, Any]:
    """Families, omnibus tests (one per partition) and cells, as declared in the families."""
    tests = plan_tests(plan)
    by_family: Dict[str, int] = {}
    for fid in family_ids(plan):
        by_family[fid] = sum(1 for t in tests if t.family == fid)
    return {
        "families": len(by_family),
        "omnibus_tests": len(tests),
        "by_family": by_family,
        "cells_total": sum(len(t.cells) for t in tests),
    }


def check_declared(plan: Union[Plan, Mapping[str, Any]]) -> Dict[str, Any]:
    """Recompute the counts and fail on any difference from ``declared_counts``."""
    data = plan.data if isinstance(plan, Plan) else plan
    counts = count_plan(plan)
    declared = data["declared_counts"]
    diffs = []
    for key in ("families", "omnibus_tests", "cells_total"):
        if int(declared.get(key, -1)) != counts[key]:
            diffs.append(f"{key}: declared {declared.get(key)}, found {counts[key]}")
    if dict(declared.get("by_family") or {}) != counts["by_family"]:
        diffs.append(f"by_family: declared {declared.get('by_family')}, found {counts['by_family']}")
    if diffs:
        raise PlanError("declared counts differ from the families: " + "; ".join(diffs))
    return counts


def check_budget(plan: Union[Plan, Mapping[str, Any]], counts: Optional[Dict[str, Any]] = None,
                 *, programme_used: int = 0) -> Dict[str, Any]:
    """Section 5.3.5. Raises :class:`BudgetExceeded` when a cap is passed.

    ``programme_used`` is the number of omnibus tests other plans of the same
    data vintage have already used.
    """
    data = plan.data if isinstance(plan, Plan) else plan
    counts = counts or count_plan(plan)
    b = data["budgets"]
    n = counts["omnibus_tests"]
    caps = []
    if data["scope"].get("slice") == "first":
        caps.append(("max_omnibus_tests_first_slice", int(b["max_omnibus_tests_first_slice"]), n))
    caps.append(("max_omnibus_tests_per_country_event_type",
                 int(b["max_omnibus_tests_per_country_event_type"]), n))
    caps.append(("max_omnibus_tests_programme_per_data_vintage",
                 int(b["max_omnibus_tests_programme_per_data_vintage"]), n + int(programme_used)))
    over = [f"{name}: {used} > {cap}" for name, cap, used in caps if used > cap]
    if b.get("used_by_this_plan") is not None and int(b["used_by_this_plan"]) != n:
        raise PlanError(f"budgets.used_by_this_plan is {b['used_by_this_plan']}, plan has {n}")
    if over:
        raise BudgetExceeded("plan over budget: " + "; ".join(over))
    return {"omnibus_tests": n, "caps": {name: cap for name, cap, _ in caps}, "within_budget": True}


# ----------------------------------------------------------- search space
def search_space(vargas: int = 9, grahas: int = 9, houses: int = 12, levels: int = 3,
                 dignity_states: int = DIGNITY_STATES, event_sky: int = EVENT_SKY_FACTORS,
                 charts: int = 7, windows: int = 3, ayanamsas: int = 2,
                 node_models: int = 2) -> Dict[str, Any]:
    """The counts of section 5.1 (blocks A to J) for the given setting.

    ``true_at_any_moment`` is the expected number of statements true at one
    instant, block by block (block J excluded: it depends on the sky).
    """
    blocks = {
        "A_dasha_lord_identity": grahas * levels,
        "B_dasha_lord_house_from_lagna": levels * vargas * houses,
        "C_dasha_lord_house_from_moon": levels * vargas * houses,
        "D_dasha_lord_rules_house": levels * vargas * houses,
        "E_dasha_lord_dignity": levels * vargas * dignity_states,
        "F_transit_house_from_lagna": grahas * houses * vargas,
        "G_transit_house_from_moon": grahas * houses * vargas,
        "H_transit_conjunct_or_aspect_natal": grahas * grahas * 2 * vargas,
    }
    fgh = (blocks["F_transit_house_from_lagna"] + blocks["G_transit_house_from_moon"]
           + blocks["H_transit_conjunct_or_aspect_natal"])
    blocks["I_transit_read_in_own_varga"] = fgh * (vargas - 1)
    blocks["J_event_sky"] = event_sky
    single = sum(blocks.values())
    dasha = sum(v for k, v in blocks.items() if k[0] in "ABCDE")
    transit = sum(v for k, v in blocks.items() if k[0] in "FGHI")

    drishti_mean = sum(DRISHTI_COUNT.values()) / len(DRISHTI_COUNT)
    true_h = vargas * grahas * grahas * (1.0 + drishti_mean) / houses
    true = {
        "A": float(levels),
        "B": float(levels * vargas),
        "C": float(levels * vargas),
        "D": levels * vargas * MEAN_HOUSES_RULED,
        "E": float(levels * vargas),
        "F": float(grahas * vargas),
        "G": float(grahas * vargas),
        "H": true_h,
    }
    true["I"] = (true["F"] + true["G"] + true["H"]) * (vargas - 1)
    return {
        "setting": {"vargas": vargas, "grahas": grahas, "houses": houses, "levels": levels,
                    "dignity_states": dignity_states},
        "blocks": blocks,
        "single_factors": single,
        "dasha_factors": dasha,
        "transit_factors": transit,
        "pairs_dasha_by_transit": dasha * transit,
        "multiplier": charts * windows * ayanamsas * node_models,
        "always_true_BCFG": int(true["B"] + true["C"] + true["F"] + true["G"]),
        "true_at_any_moment": {"by_block": true, "total_excluding_J": round(sum(true.values()), 1)},
        "chance_significant_at_0_05": round(0.05 * single),
    }


# --------------------------------------------------------------------- MDE
def by_rank1_alpha(m: int, alpha: float = 0.05) -> float:
    """Benjamini-Yekutieli threshold for the smallest p of ``m`` tests."""
    harmonic = sum(1.0 / i for i in range(1, int(m) + 1))
    return alpha / (int(m) * harmonic)


def mde_exact(n_events: int, duty: float, alpha: float, power: float = 0.80) -> float:
    return _mde_exact(int(n_events), round(float(duty), 12), float(alpha), float(power))


@lru_cache(maxsize=65536)
def _mde_exact(n_events: int, duty: float, alpha: float, power: float) -> float:
    """Smallest rate ratio detected with ``power`` (section 5.4).

    One-sided exact binomial on the count of active events out of
    ``n_events``; under the null each event is active with probability
    ``duty``; under rate ratio RR with ``RR d / (RR d + 1 - d)``.
    Returns ``inf`` when no count can reach ``alpha``.
    """
    n = int(n_events)
    d = float(duty)
    if n <= 0 or not 0 < d < 1:
        raise ValueError("need n_events > 0 and 0 < duty < 1")
    k = int(sps.binom.isf(alpha, n, d)) + 1
    while k > 1 and sps.binom.sf(k - 2, n, d) <= alpha:
        k -= 1
    while k <= n and sps.binom.sf(k - 1, n, d) > alpha:
        k += 1
    if k > n:
        return float("inf")
    if sps.binom.sf(k - 1, n, d) >= power:
        return 1.0
    p1 = brentq(lambda p: sps.binom.sf(k - 1, n, p) - power, d, 1 - 1e-12, xtol=1e-12)
    return p1 * (1 - d) / (d * (1 - p1))


def mde_table(plan: Union[Plan, Mapping[str, Any], None] = None) -> Dict[str, Any]:
    """Rebuild the table of section 5.4 and compare it with the plan's copy."""
    data = (plan.data if isinstance(plan, Plan) else plan) if plan is not None else None
    if data is not None:
        spec = data["mde"]
        thresholds = dict(spec["thresholds"])
        power = float(spec["power"])
        columns = list(spec["columns"])
        duties = sorted(float(k.split("_", 1)[1]) for k in spec if k.startswith("duty_"))
    else:
        spec = None
        thresholds = {"one_test": 0.05, "family_24": 5.5e-4, "family_60": 1.8e-4,
                      "all_32000": 1.6e-6}
        power = 0.80
        columns = ["events", "one_test", "family_24", "family_60", "all_32000"]
        duties = [0.10, 0.25]
    rows_out: Dict[str, List[List[float]]] = {}
    max_diff = 0.0
    for d in duties:
        key = f"duty_{d:.2f}"
        events = [10, 20, 30, 50, 100, 200, 500, 1000]
        if spec is not None and key in spec:
            events = [int(r[0]) for r in spec[key]]
        rows = []
        for i, n in enumerate(events):
            row = [n] + [round(mde_exact(n, d, float(thresholds[c]), power), 2) for c in columns[1:]]
            rows.append(row)
            if spec is not None and key in spec:
                for got, want in zip(row[1:], spec[key][i][1:]):
                    max_diff = max(max_diff, abs(got - float(want)) / float(want))
        rows_out[key] = rows
    out: Dict[str, Any] = {"power": power, "thresholds": thresholds, "columns": columns,
                           "test": "one_sided_exact_binomial", "rows": rows_out}
    if spec is not None:
        out["max_relative_difference_from_plan"] = round(max_diff, 4)
        chk = spec.get("check")
        if chk:
            out["check"] = {**chk, "computed": round(mde_exact(int(chk["events"]),
                                                               float(chk["duty"]), 0.05, power), 2)}
    return out


def mde_alpha(plan: Union[Plan, Mapping[str, Any]]) -> float:
    """Level used for per-test MDE: BY rank 1 for the plan's ``family_size_used``."""
    data = plan.data if isinstance(plan, Plan) else plan
    m = int(data["mde"]["this_plan"]["family_size_used"])
    return by_rank1_alpha(m, float(data["statistics"]["hierarchy"]["level_1"]["alpha"]))


# ------------------------------------------------------------------ report
def burden_report(plan: Plan, *, programme_used: int = 0) -> Dict[str, Any]:
    """Everything the ``burden`` command prints. Raises on a count mismatch or over budget."""
    counts = check_declared(plan)
    budget = check_budget(plan, counts, programme_used=programme_used)
    tests = plan_tests(plan)
    return {
        "schema": "mundane-burden/1",
        "plan_id": plan["id"],
        "plan_sha256": plan.sha256,
        "search_space_full_d1_d9": search_space(),
        "plan_counts": counts,
        "budget": budget,
        "tests": [{"id": t.id, "family": t.family, "predicate": t.predicate,
                   "cells": len(t.cells), "methods": list(t.methods)} for t in tests],
        "mde": mde_table(plan),
        "mde_alpha_per_test": mde_alpha(plan),
        "event_floor": int(plan["budgets"]["min_events_for_test"]),
    }


def write_burden(report: Dict[str, Any], path: Union[str, Path]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


__all__ = [
    "BudgetExceeded", "MOVING_PREDICATES", "NatalFactorError", "PLAN_FILE", "Plan",
    "PlanError", "TestSpec", "burden_report", "by_rank1_alpha", "check_budget",
    "check_declared", "check_moving", "count_plan", "load_plan", "mde_alpha", "mde_exact",
    "mde_table", "plan_from_dict", "plan_tests", "search_space", "write_burden",
]
