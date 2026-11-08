"""Published explorer data under site/data/: derived, small, and traceable.

The market files must never carry a price or a return (Yahoo terms of use);
every file carries a ``_meta`` block whose ``data_sha256`` matches its rows.
"""

import hashlib
import json
import sys
from datetime import timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "site" / "data"
sys.path.insert(0, str(REPO / "scripts"))

import export_site_data as esd  # noqa: E402

FILES = sorted(DATA.glob("*.json"))
FORBIDDEN = ("close", "return", "price", "log_ret", "fwd_")


def load(name):
    """Return one published JSON file."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_every_expected_file_is_published():
    """Every expected file is published."""
    names = {p.name for p in FILES}
    assert {
        "results.json",
        "market_gold.json",
        "market_silver.json",
        "pinksheet_monthly.json",
        "earthquake.json",
        "ephemeris_monthly.json",
        "mundane_countries.json",
        "mundane_dasha.json",
        "rules.json",
        "numerology_daily.json",
        "workbench_earthquake.json",
        "workbench_gold.json",
        "workbench_silver.json",
        "atlas.json",
    } <= names


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_meta_is_present_and_hash_matches(path):
    """Meta is present and hash matches."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    meta = doc.pop("_meta")
    for key in (
        "data_sha256",
        "commit",
        "seed",
        "generated_at",
        "source",
        "licence",
        "inputs",
    ):
        assert key in meta, f"{path.name}: _meta lacks {key}"
    body = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(body.encode()).hexdigest() == meta["data_sha256"]
    assert meta["file"] == path.name


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_files_stay_small(path):
    """Files stay small (workbench daily arrays: 3 MB, see the cut test)."""
    limit = 3_000_000 if path.name.startswith("workbench_") else 1_000_000
    assert path.stat().st_size < limit


@pytest.mark.parametrize("metal", ["gold", "silver"])
def test_market_files_have_no_price_or_return_columns(metal):
    """Market files have no price or return columns."""
    doc = load(f"market_{metal}.json")
    cols = doc["columns"]
    for name in cols:
        assert not any(bad in name.lower() for bad in FORBIDDEN), name
    for name, values in cols.items():
        if name == "date":
            continue
        # Flags, signs and quintile classes only: small integers, no floats.
        seen = {v for v in values if v is not None}
        assert all(isinstance(v, int) for v in seen), name
        assert seen <= {-1, 0, 1, 2, 3, 4, 5}, name
    assert set(doc["columns"]["fwd21_q"]) - {None} == {1, 2, 3, 4, 5}


def test_no_file_in_site_data_has_a_price_or_return_column_from_yahoo():
    """No file in site data has a price or return column from yahoo."""
    for path in FILES:
        if path.name == "pinksheet_monthly.json":
            continue  # World Bank, CC BY 4.0: published on purpose
        doc = json.loads(path.read_text(encoding="utf-8"))
        cols = doc.get("columns", {})
        for name in cols:
            assert "close" not in name.lower() and "return" not in name.lower()


def test_pink_sheet_is_world_bank_with_licence_and_hash():
    """Pink sheet is world bank with licence and hash."""
    doc = load("pinksheet_monthly.json")
    assert "CC BY 4.0" in doc["_meta"]["licence"]
    assert len(doc["_meta"]["inputs"]["pink_sheet"]["sha256"]) == 64
    assert doc["columns"]["month"][0] == "1960-01"
    assert len(doc["columns"]["gold"]) == len(doc["columns"]["month"])


def test_rules_export_covers_every_rule_file():
    """Rules export covers every rule file."""
    doc = load("rules.json")
    files = list((REPO / "rules").rglob("*.yaml"))
    assert len(doc["rules"]) == len(files)
    assert not doc["problems"]
    for rule in doc["rules"]:
        assert (REPO / rule["path"]).exists()
        if rule["status"] != "needs_predicates":
            assert rule["conditions"]["text"]


def test_earthquake_export_matches_the_study_counts():
    """Earthquake export matches the study counts."""
    doc = load("earthquake.json")
    res = json.loads((REPO / "studies/earthquake/artifacts/results.json").read_text())
    counts = {r["catalogue"]: r["n_events"] for r in res["declustering"]["summary"]}
    ev = doc["events"]
    assert len(ev["time"]) == counts["raw"]
    assert sum(ev["gk"]) == counts["gk"]
    assert sum(ev["nn"]) == counts["nn"]


def test_dasha_only_for_charts_with_a_time():
    """Dasha only for charts with a time."""
    countries = load("mundane_countries.json")["countries"]
    charts = load("mundane_dasha.json")["charts"]
    for c in countries:
        for k in c["candidates"]:
            assert k["has_dasha"] == bool(k["time"])
            assert (k["key"] in charts) == bool(k["time"])


# ------------------------------------------------------- helper functions
def test_intervals_turns_a_mask_into_runs():
    """Intervals turns a mask into runs."""
    import numpy as np
    import pandas as pd

    grid = pd.date_range("2020-01-01", periods=6, freq="1h", tz="UTC")
    runs = esd.intervals(np.array([0, 1, 1, 0, 1, 1]), grid)
    assert runs == [
        ["2020-01-01T01:00", "2020-01-01T03:00"],
        ["2020-01-01T04:00", "2020-01-01T06:00"],
    ]


def test_chart_moment_reads_local_mean_time_from_longitude():
    """Chart moment reads local mean time from longitude."""
    moment = esd.chart_moment(
        {"date": "1776-07-04", "time": "12:00:00", "time_zone": "LMT", "lon": -75.0}
    )
    assert moment.tzinfo == timezone.utc
    assert moment.isoformat() == "1776-07-04T17:00:00+00:00"
    assert esd.chart_moment({"date": "1947-08-15", "time": None}) is None


def test_chart_moment_reads_an_iana_zone():
    """Chart moment reads an iana zone."""
    moment = esd.chart_moment(
        {
            "date": "1947-08-15",
            "time": "00:00:00",
            "time_zone": "Asia/Kolkata",
            "lon": 77.2,
        }
    )
    assert moment.isoformat() == "1947-08-14T18:30:00+00:00"


def test_plain_words_renders_without_evaluating():
    """Plain words renders without evaluating."""
    from vedic_astrology_core.rules.loader import load_rules

    loaded, _ = load_rules([REPO / "rules/seismic/mangal_ketu_primary.yaml"])
    tree = esd.plain_words(loaded[0].rule.conditions)
    assert tree["text"].startswith("Conjunct within")
    assert "Mars" in tree["text"] and "13" in tree["text"]
    assert tree["gloss"].startswith("Two planets")


def test_market_definitions_cover_every_registered_indicator():
    """Market definitions cover every registered indicator."""
    for study in ("gold_market", "silver_market"):
        defs = esd.market_definitions(study)
        ids = [s["id"] for s in esd.hypothesis(study)["indicators"]]
        assert [d["id"] for d in defs] == ids
        assert all(d["definition"] for d in defs)


def test_rules_export_schema_v2_fields_and_client_flag():
    """Every rule carries version, validation state and an evaluable flag."""
    doc = load("rules.json")
    states = {"confirmed", "not_confirmed", "tuned", "unvalidated"}
    for rule in doc["rules"]:
        assert rule["version"] >= 1
        assert rule["validation_state"] in states
        assert isinstance(rule["tuning_log"], list)
        if rule["client_evaluable"]:
            assert rule["machine"] is not None
    counts = doc["validation_counts"]
    assert set(counts) == states and sum(counts.values()) == len(doc["rules"])
    ids = {r["id"] for r in doc["rules"] if r["client_evaluable"]}
    assert "seismic.mangal_shani_malefic" in ids
    assert "general.gaja_kesari.classical" not in ids  # needs the Lagna


def test_atlas_export_marks_its_source():
    """The atlas says whether it is the real atlas or the fixture."""
    doc = load("atlas.json")
    cols = doc["columns"]
    n = doc["n"]
    assert all(len(v) == n for v in cols.values())
    real = (REPO / "studies/combinations/artifacts/atlas.csv").exists()
    assert doc["fixture"] is (not real)
    if doc["fixture"]:
        assert "FIXTURE" in doc["_meta"]["source"]
    assert 0 <= doc["threshold"] <= doc["alpha"]


def test_by_threshold_is_the_largest_passing_p():
    """BY threshold is the largest p under the step-up line."""
    import numpy as np

    p = np.array([0.0001, 0.0004, 0.2, 0.9])
    c = 1 + 1 / 2 + 1 / 3 + 1 / 4
    assert esd.by_threshold(p) == 0.0004
    assert 0.0004 <= 2 * 0.05 / (4 * c)
    assert esd.by_threshold(np.array([0.5, 0.9])) == 0.0
