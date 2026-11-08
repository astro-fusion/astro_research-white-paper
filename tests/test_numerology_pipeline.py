"""The numerology study samples aware datetimes and writes results.json."""

import importlib.util
import json
import sys
from datetime import date

import pandas as pd
import pytest

from studies._paths import study_dir

SCRIPTS = study_dir("numerology_vs_astrology") / "scripts"


def _load(name):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator_module():
    """Import generate_temporal_analysis from the study's scripts."""
    return _load("generate_temporal_analysis")


def test_every_day_is_generated(generator_module):
    """No day is skipped (naive datetimes used to fail every day)."""
    gen = generator_module.TemporalDataGenerator(date(2024, 1, 1), date(2024, 2, 1))
    rows = gen.generate_data()
    assert len(rows) == 31
    assert {"astrology_moon_nakshatra_lord", "numerology_active_planet"} <= set(
        rows[0])


def test_zone_changes_the_sampled_moment(generator_module):
    """Noon in Kathmandu is 06:15 UTC, so some days get another nakshatra."""
    span = (date(2024, 1, 1), date(2024, 2, 1))
    utc = generator_module.TemporalDataGenerator(*span, tz="UTC").generate_data()
    ktm = generator_module.TemporalDataGenerator(
        *span, tz="Asia/Kathmandu").generate_data()
    a = [r["astrology_moon_nakshatra"] for r in utc]
    b = [r["astrology_moon_nakshatra"] for r in ktm]
    assert a != b
    assert [r["numerology_active_planet"] for r in utc] == [
        r["numerology_active_planet"] for r in ktm]


def test_pipeline_writes_results(generator_module, tmp_path):
    """A short run writes results.json with both registered hypotheses."""
    pipeline = _load("pipeline")
    gen = generator_module.TemporalDataGenerator(date(2024, 1, 1), date(2024, 4, 1))
    frame = pd.DataFrame(gen.generate_data())
    res = pipeline.run(42, out_dir=tmp_path, frame=frame, data_dir=tmp_path)
    saved = json.loads((tmp_path / "results.json").read_text())
    assert saved["hypothesis_id"] == res["hypothesis_id"]
    assert saved["sampling"]["tz"] == "UTC"
    assert -1 <= saved["H1_kappa"]["kappa"] <= 1
    assert saved["H1_kappa"]["se_used"] >= saved["H1_kappa"]["se_analytic"]
    assert len(saved["H2_planets"]) == 9
    assert (tmp_path / "manifest.json").exists()
    d = saved["description"]
    assert d["n_days"] == 91
    assert d["nakshatra_lord_changes_per_year"] > 300
