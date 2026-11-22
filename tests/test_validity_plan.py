"""Tests for the domain plan schema and validator (ADR-008 WP-93)."""

import copy
import datetime as dt

import pytest

from vedic_astrology_core.validity import plan as P

H = "a" * 64
H2 = "b" * 64

YARDSTICK = {
    "id": "ys1",
    "kind": "daily_returns",
    "citation": "Doe J (2001) Turn of the month. J Fin 5:1-20. doi:10.0/x",
    "page": "p. 7, table 2",
    "number_as_printed": "0.11% per day",
    "conversion": "log points",
    "converted_value": 11.0,
    "checker": "A. Checker",
    "date": "2026-11-01",
}
TABLE = {"schema_version": 1, "entries": [YARDSTICK]}


def _outcome(**kw):
    o = {
        "id": "gold_dem_frankfurt",
        "market": "frankfurt",
        "currency": "DEM",
        "type": "continuous",
        "estimand": "pooled_difference",
        "effect_model": "constant_shift",
        "side": "two_sided",
        "sesoi": None,
        "guard_bars": 0,
        "grid_x": [0.5, 1.0, 2.0],
    }
    o.update(kw)
    return o


def _base(domain="gold"):
    return {
        "domain": domain,
        "status": "draft",
        "seed": 7,
        "split": {"explore": {"start": "1968-06-18", "end": "1986-12-31"},
                  "confirm": {"start": "1987-01-01", "end": "1998-12-30"}},
        "vintages": [{"id": "v1", "snapshot": "s1", "grain": "daily",
                      "confirm_period": {"start": "1987-01-01", "end": "1998-12-30"}, "seen": False}],
        "snapshots": [{"id": "s1", "file": "data/snapshots/x.csv", "sha256": H}],
        "outcomes": [_outcome()],
        "windows": {"episode": "calendar"},
        "merge_gap": 0,
        "guard_bars": 0,
        "day_convention": "frankfurt_fixing_local_date",
        "r_measures": {r: {"measure": "m_" + r, "threshold": 0.5} for r in P.R_KEYS},
        "placebo_sets": [{"id": "shifted_sky"}],
        "baselines": ["month", "weekday"],
        "alpha_spending": {"first": 0.04, "ratio": 0.2, "max_variants": 3},
    }


def _monsoon():
    p = _base("monsoon")
    p["split"] = {"explore": {"start": 1871, "end": 1960}, "confirm": {"start": 1961, "end": 2016}}
    p["vintages"] = [{"id": "v1", "snapshot": "s1", "grain": "yearly",
                      "confirm_period": {"start": 1961, "end": 2016}, "seen": False}]
    p["outcomes"] = [_outcome(id="jjas_rainfall_pct", market=None, currency=None)]
    del p["outcomes"][0]["market"], p["outcomes"][0]["currency"]
    p["baselines"] = ["enso", "nodal_18_6y", "solar_cycle"]
    p["enso"] = {"series_id": "nino34_long", "sha256": H2, "covers": {"start": 1870, "end": 2016}}
    return p


def _errs(p, **kw):
    return P.validate_plan(p, **kw)


def test_good_plans_pass():
    assert _errs(_base()) == []
    assert _errs(_monsoon()) == []


@pytest.mark.parametrize("key", P.REQUIRED_KEYS)
def test_each_required_key_is_required(key):
    p = _base()
    del p[key]
    errs = _errs(p)
    assert any(f"'{key}'" in e for e in errs), errs
    p = _base()
    p[key] = None
    assert any(f"'{key}'" in e for e in _errs(p))


@pytest.mark.parametrize("key", P.OUTCOME_KEYS)
def test_each_outcome_key_is_required(key):
    p = _base()
    del p["outcomes"][0][key]
    assert any(f"'{key}'" in e for e in _errs(p))


def test_zero_is_a_value_for_merge_gap_guard_and_seed():
    p = _base()
    p["merge_gap"] = 0
    p["guard_bars"] = 0
    p["seed"] = 0
    assert _errs(p) == []


@pytest.mark.parametrize("word", ["proposal", "Proposed", "default adopted", "Default_Adopted", "TBD"])
def test_forbidden_words_refused(word):
    p = _base()
    p["day_convention"] = f"x ({word})"
    assert any("refused" in e for e in _errs(p))
    p = _base()
    p["baselines"] = ["month", f"note: {word}"]
    assert any("refused" in e for e in _errs(p))


def test_routing_keys_and_methods_refused():
    p = _base()
    p["routing"] = {"periodic": "shift"}
    assert any("routing" in e for e in _errs(p))
    p = _base()
    p["outcomes"][0]["calendar_class"] = "x"
    assert any("routing" in e for e in _errs(p))
    p = _base()
    p["p_method"] = "shift"
    assert any("block_signflip" in e for e in _errs(p))
    p["p_method"] = "block_signflip"
    assert _errs(p) == []


def test_estimand_must_match_type_and_side_has_no_default():
    p = _base()
    p["outcomes"][0]["estimand"] = "pooled_rate_ratio"
    assert any("estimand" in e for e in _errs(p))
    p = _base()
    p["outcomes"][0]["side"] = "up"
    assert any("side" in e for e in _errs(p))


def test_grid_x_must_increase():
    for bad in ([2.0, 1.0], [1.0], "x", [1, "a"]):
        p = _base()
        p["outcomes"][0]["grid_x"] = bad
        assert any("grid_x" in e for e in _errs(p)), bad


def test_event_and_absolute_return_extra_keys():
    p = _base("earthquake")
    p["outcomes"] = [_outcome(id="mainshock_rate", type="event", estimand="pooled_rate_ratio")]
    del p["outcomes"][0]["market"], p["outcomes"][0]["currency"]
    p["baselines"] += ["nodal_18_6y", "solar_cycle"]
    p["vintages"][0]["seen"] = True
    assert any("counting_unit" in e for e in _errs(p))
    p["outcomes"][0]["counting_unit"] = "declustered_mainshock"
    assert _errs(p) == []
    p = _base()
    p["outcomes"][0].update(type="absolute_return", estimand="pooled_log_ratio")
    assert any("floor" in e for e in _errs(p))


# ---- SESOI (7.2)


def _with_sesoi(s):
    p = _base()
    p["outcomes"][0]["sesoi"] = s
    return p


def test_no_sesoi_is_allowed_but_never_returns_e():
    p = _base()
    assert _errs(p) == []
    assert P.can_return_e(p["outcomes"][0]) is False
    assert P.can_return_e({"sesoi": {}}) is False
    assert P.can_return_e({}) is False


def test_sesoi_from_yardstick_passes_and_can_return_e():
    s = {"value": 11.0, "kind": "yardstick", "yardstick_id": "ys1"}
    p = _with_sesoi(s)
    assert _errs(p, sesoi_sources=TABLE) == []
    assert P.can_return_e(p["outcomes"][0]) is True


def test_sesoi_without_table_entry_refused():
    s = {"value": 11.0, "kind": "yardstick", "yardstick_id": "ys1"}
    assert any("no entry" in e for e in _errs(_with_sesoi(s)))
    assert any("no entry" in e for e in _errs(_with_sesoi(s), sesoi_sources={"entries": []}))


@pytest.mark.parametrize("field", ["page", "checker", "citation", "converted_value"])
def test_sesoi_entry_without_field_refused(field):
    t = copy.deepcopy(TABLE)
    del t["entries"][0][field]
    s = {"value": 11.0, "kind": "yardstick", "yardstick_id": "ys1"}
    assert _errs(_with_sesoi(s), sesoi_sources=t)
    assert P.validate_sesoi_sources(t)


@pytest.mark.parametrize("cite", ["docs/research/FINDINGS_LEDGER.md", "site/data/results.json",
                                  "docs/adr/ADR-007-principle-validity-reports.md", "./x.md"])
def test_sesoi_citing_repo_file_refused(cite):
    t = copy.deepcopy(TABLE)
    t["entries"][0]["citation"] = cite
    s = {"value": 11.0, "kind": "yardstick", "yardstick_id": "ys1"}
    assert any("repository" in e for e in _errs(_with_sesoi(s), sesoi_sources=t))
    assert any("repository" in e for e in P.validate_sesoi_sources(t))


def test_sesoi_value_must_match_entry():
    s = {"value": 25.0, "kind": "yardstick", "yardstick_id": "ys1"}
    assert any("converted_value" in e for e in _errs(_with_sesoi(s), sesoi_sources=TABLE))


def test_sesoi_chosen_by_project_refused():
    assert any("sesoi.kind" in e for e in _errs(_with_sesoi({"value": 25})))
    assert any("sesoi.kind" in e for e in _errs(_with_sesoi({"value": 25, "kind": "project"})))
    assert any("positive" in e for e in _errs(_with_sesoi({"value": 0, "kind": "source"})))


def test_sesoi_from_source_needs_page_and_quotation():
    s = {"value": 2.0, "kind": "source", "rule_id": "r1"}
    errs = _errs(_with_sesoi(s))
    assert any("'page'" in e for e in errs) and any("'quotation'" in e for e in errs)
    s.update(page="p. 3", quotation="twice as often")
    assert _errs(_with_sesoi(s)) == []


def test_empty_sesoi_table_validates():
    assert P.validate_sesoi_sources({"schema_version": 1, "entries": []}) == []
    assert P.validate_sesoi_sources({"entries": []})  # schema_version missing


def test_committed_sesoi_table_loads_and_is_empty():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "studies" / "validity" / "sesoi_sources.yaml"
    assert P.load_sesoi_sources(path)["entries"] == []


# ---- market and currency (A-06)


def test_outcome_id_carries_market_and_currency():
    p = _base()
    p["outcomes"][0]["id"] = "gold_return"
    errs = _errs(p)
    assert any("market" in e for e in errs) and any("currency" in e for e in errs)
    p = _base()
    del p["outcomes"][0]["currency"]
    assert any("'currency'" in e for e in _errs(p))
    p = _base()
    del p["outcomes"][0]["market"]
    assert any("'market'" in e for e in _errs(p))


# ---- vintages, seen (F-05)


def test_vintage_needs_seen():
    p = _base()
    del p["vintages"][0]["seen"]
    assert any("seen" in e for e in _errs(p))
    p["vintages"][0]["seen"] = "no"
    assert any("true or false" in e for e in _errs(p))


def test_earthquake_2011_onward_must_be_seen():
    p = _base("earthquake")
    p["outcomes"] = [_outcome(id="mainshock_rate", type="event", estimand="pooled_rate_ratio",
                              counting_unit="declustered_mainshock")]
    del p["outcomes"][0]["market"], p["outcomes"][0]["currency"]
    p["baselines"] += ["nodal_18_6y", "solar_cycle"]
    p["vintages"][0]["confirm_period"] = {"start": 2011, "end": 2024}
    assert any("seen must be true" in e for e in _errs(p))
    p["vintages"][0]["seen"] = True
    assert _errs(p) == []
    # a vintage of data nobody has yet is not forced to be seen
    p["vintages"][0].update(seen=False, confirm_period={"start": "2027-01-01", "end": "2030-12-31"})
    assert _errs(p) == []


def test_monthly_gold_and_silver_from_2000_must_be_seen():
    for dom in ("gold", "silver"):
        p = _base(dom)
        p["outcomes"][0]["id"] = f"{dom}_dem_frankfurt"
        p["vintages"][0].update(grain="monthly", confirm_period={"start": "2000-01", "end": "2026-10"})
        assert any("seen must be true" in e for e in _errs(p)), dom
        p["vintages"][0]["seen"] = True
        assert _errs(p) == [], dom
    # daily gold confirm 1987-1998 is not in the rule
    assert _errs(_base()) == []


def test_vintage_snapshot_must_be_pinned_id():
    p = _base()
    p["vintages"][0]["snapshot"] = "nope"
    assert any("not a pinned snapshot" in e for e in _errs(p))


def test_split_confirm_after_explore():
    p = _base()
    p["split"]["confirm"]["start"] = "1980-01-01"
    assert any("after explore" in e for e in _errs(p))


# ---- pinned snapshots (D-03)


@pytest.mark.parametrize("h", ["latest", "newest", "abc", "A" * 64, "g" * 64])
def test_snapshot_hash_must_be_pinned(h):
    p = _base()
    p["snapshots"][0]["sha256"] = h
    assert any("sha256" in e for e in _errs(p))


def test_snapshot_index_cross_check():
    idx = {"snapshots": [{"sha256": H}]}
    assert _errs(_base(), snapshot_index=idx) == []
    idx = {"snapshots": [{"sha256": H2}]}
    assert any("snapshot index" in e for e in _errs(_base(), snapshot_index=idx))


# ---- monsoon ENSO coverage (F-02)


def test_monsoon_requires_enso_covering_both_periods():
    p = _monsoon()
    p["enso"]["covers"] = {"start": 1950, "end": 2016}  # explore 1871-1960 uncovered
    assert any("cover explore and confirm" in e for e in _errs(p))
    p = _monsoon()
    p["enso"]["covers"] = {"start": 1870, "end": 2010}  # confirm to 2016 uncovered
    assert any("cover explore and confirm" in e for e in _errs(p))
    p = _monsoon()
    del p["enso"]
    assert any("enso" in e for e in _errs(p))
    p = _monsoon()
    p["enso"]["sha256"] = "latest"
    assert any("enso.sha256" in e for e in _errs(p))


def test_slow_cycle_baselines_required():
    for dom_fix in (_monsoon,):
        for b in ("nodal_18_6y", "solar_cycle"):
            p = dom_fix()
            p["baselines"].remove(b)
            assert any(b in e for e in _errs(p))
    p = _monsoon()
    p["baselines"] = [{"id": "nodal_18_6y"}, {"id": "solar_cycle"}]
    assert _errs(p) == []


# ---- GARCH-X secondary (S-16)


def test_garch_x_must_be_secondary_without_a_test_or_verdict():
    p = _base()
    p["sensitivity"] = {"garch_x": {"shifts": 199}}
    assert any("secondary" in e for e in _errs(p))
    p["sensitivity"]["garch_x"] = {"role": "secondary", "a_test": 0.001}
    assert any("a_test" in e for e in _errs(p))
    p["sensitivity"]["garch_x"] = {"role": "secondary", "verdict": "S"}
    assert any("verdict" in e for e in _errs(p))
    p["sensitivity"]["garch_x"] = {"role": "secondary", "shifts": 199}
    assert _errs(p) == []


# ---- alpha spending, R measures, sign-offs


def test_alpha_spending_rules():
    p = _base()
    p["alpha_spending"]["first"] = 0.05
    assert any("0.05" in e for e in _errs(p))
    p = _base()
    p["alpha_spending"]["max_variants"] = 4
    assert any("max_variants" in e for e in _errs(p))


@pytest.mark.parametrize("r", P.R_KEYS)
def test_each_r_measure_needed(r):
    p = _base()
    del p["r_measures"][r]
    assert any(f"r_measures.{r}" in e for e in _errs(p))


def test_registered_plan_needs_signoffs():
    p = _base()
    p["status"] = "registered"
    errs = _errs(p)
    for d in P.REQUIRED_SIGNOFFS:
        assert any(f"owner_signoffs.{d}" in e for e in errs)
    assert not any("H18" in e for e in errs)  # no SESOI, no H18
    p["owner_signoffs"] = {d: "2026-12-01" for d in P.REQUIRED_SIGNOFFS}
    assert _errs(p) == []
    p["outcomes"][0]["sesoi"] = {"value": 11.0, "kind": "yardstick", "yardstick_id": "ys1"}
    assert any("H18" in e for e in _errs(p, sesoi_sources=TABLE))
    p["owner_signoffs"]["H18"] = dt.date(2026, 12, 2)
    assert _errs(p, sesoi_sources=TABLE) == []


# ---- loading and hashing


def test_load_plan_roundtrip_and_hash(tmp_path):
    import yaml

    p = _base()
    f = tmp_path / "gold.yaml"
    f.write_text(yaml.safe_dump(p))
    loaded = P.load_plan(f)
    assert P.plan_hash(loaded) == P.plan_hash(p)
    q = copy.deepcopy(p)
    q["seed"] = 8
    assert P.plan_hash(q) != P.plan_hash(p)
    p["day_convention"] = "default adopted"
    f.write_text(yaml.safe_dump(p))
    with pytest.raises(P.PlanError) as ei:
        P.load_plan(f)
    assert any("refused" in e for e in ei.value.errors)


def test_non_mapping_plan():
    assert _errs([1]) == ["plan: not a mapping"]
