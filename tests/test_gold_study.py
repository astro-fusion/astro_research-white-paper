"""The gold-market study: pre-registration and committed results agree."""

import json
from pathlib import Path

import pytest

from vedic_astrology_core.markets import study

STUDY = Path(__file__).resolve().parent.parent / "studies" / "gold_market"
RESULTS = STUDY / "artifacts" / "results.json"


def test_hypothesis_is_complete():
    """Check the pre-registration states every fixed choice."""
    cfg = study.load_hypothesis(STUDY / "hypothesis.yaml")
    assert cfg["study"] == "gold_market"
    assert cfg["tests"]["correction"] == "by" and cfg["tests"]["alpha"] == 0.05
    assert cfg["tests"]["n_perm"] >= 10000 and cfg["tests"]["min_shift_bars"] >= 400
    assert cfg["periods"]["confirm_start"] == "2016-01-01"
    assert len(cfg["indicators"]) == 14
    assert all(s["kind"] in ("retrograde", "combust", "in_sign", "tithi", "rule")
               for s in cfg["indicators"])
    assert cfg["data"]["sources"][0]["adapter"] == "fred"


def test_pipeline_script_is_configuration_only():
    """Check the study script holds no study-specific logic."""
    text = (STUDY / "scripts" / "pipeline.py").read_text()
    assert len(text.splitlines()) <= 30
    assert "markets.study import main" in text and "def " not in text


@pytest.mark.skipif(not RESULTS.exists(), reason="pipeline not run")
def test_committed_results_match_the_preregistration():
    """Check results.json was produced from this hypothesis file."""
    res = json.loads(RESULTS.read_text())
    cfg = study.load_hypothesis(STUDY / "hypothesis.yaml")
    assert res["seed"] == 42
    ids = [s["id"] for s in cfg["indicators"]]
    assert res["family"]["indicators"] + res["family"]["indicators_not_evaluated"] \
        == ids
    assert res["family"]["size_explore"] == 3 * len(res["family"]["indicators"])
    assert res["data"]["is_futures"] is (res["data"]["adapter"] != "fred")
    if res["data"]["is_futures"]:
        assert "not spot" in res["data"]["label"]
    explore = [t for t in res["tests"] if t["period"] == "explore" and t["testable"]]
    assert sum(t["significant"] for t in explore) \
        == res["headline"]["n_significant_explore"]
