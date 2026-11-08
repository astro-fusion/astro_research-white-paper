"""The workbench export holds the EXPLORE period only (ADR-003).

Confirm-period rows must never reach ``site/data/``: the site is where
astrologers tune, and the holdout decides only because it is not there.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "site" / "data"
sys.path.insert(0, str(REPO / "scripts"))

import export_site_data as esd  # noqa: E402

STUDIES = sorted(esd.WORKBENCH_STUDIES.items())


def load(key):
    """Return one published workbench file."""
    return json.loads((DATA / f"workbench_{key}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("key,study", STUDIES)
def test_no_row_is_on_or_after_the_confirm_start(key, study):
    """No row is on or after the confirm start read from hypothesis.yaml."""
    cut = esd.split_of(esd.hypothesis(study))["confirm_start"]
    doc = load(key)
    dates = [r[0] for r in doc["rows"]]
    assert dates, key
    assert max(dates) < cut.strftime("%Y-%m-%d")
    assert doc["explore"]["confirm_start"] == cut.strftime("%Y-%m-%d")
    assert dates == sorted(dates) and len(set(dates)) == len(dates)


@pytest.mark.parametrize("key,study", STUDIES)
def test_no_confirm_date_appears_anywhere_in_the_file(key, study):
    """No ISO date on or after the confirm start appears anywhere in the text."""
    import re

    cut = esd.split_of(esd.hypothesis(study))["confirm_start"].strftime("%Y-%m-%d")
    doc = load(key)
    doc.pop("_meta")  # generation time, not data
    doc["explore"].pop("confirm_start")  # the declared cut itself
    body = json.dumps(doc)
    late = [d for d in re.findall(r"\d{4}-\d{2}-\d{2}", body) if d >= cut]
    assert late == []


@pytest.mark.parametrize("key,study", STUDIES)
def test_rows_are_arrays_with_the_declared_fields(key, study):
    """Rows are arrays of arrays matching ``fields``; no price or return."""
    doc = load(key)
    assert all(len(r) == len(doc["fields"]) for r in doc["rows"])
    for name in doc["fields"]:
        assert not any(bad in name.lower() for bad in ("close", "return", "price"))
    row = doc["rows"][len(doc["rows"]) // 2]
    f = {k: i for i, k in enumerate(doc["fields"])}
    assert all(0 <= row[f[p]] < 360 for p in doc["planets"])
    assert 1 <= row[f["tithi"]] <= 30 and 0 <= row[f["nakshatra"]] <= 26
    assert doc["min_shift"] > 0


@pytest.mark.parametrize("key,study", STUDIES)
def test_file_stays_under_three_megabytes(key, study):
    """File stays under 3 MB."""
    assert (DATA / f"workbench_{key}.json").stat().st_size < 3_000_000


def test_split_reads_both_registered_forms():
    """Split reads the earthquake form, the market form and the ADR-003 form."""
    eq = esd.split_of(
        {
            "split": {
                "explore": ["1976-01-01", "2010-12-31"],
                "confirm": ["2011-01-01", "2026-10-31"],
            }
        }
    )
    assert eq["confirm_start"] == pd.Timestamp("2011-01-01")
    mk = esd.split_of(
        {"periods": {"explore_end": "2015-12-31", "confirm_start": "2016-01-01"}}
    )
    assert mk["confirm_start"] == pd.Timestamp("2016-01-01")
    adr = esd.split_of({"confirm": {"start": "2020-01-01"}})
    assert adr["confirm_start"] == pd.Timestamp("2020-01-01")
    with pytest.raises(SystemExit):
        esd.split_of({"periods": {}})


def test_the_guard_refuses_a_confirm_date():
    """The guard hard-fails on a confirm-period date and passes the day before."""
    cut = pd.Timestamp("2011-01-01")
    esd.assert_explore_only(["2010-12-31"], cut)
    with pytest.raises(SystemExit, match="confirm-period"):
        esd.assert_explore_only(["2010-12-31", "2011-01-01"], cut)


def test_dasha_runs_change_only_on_a_new_period():
    """Dasha runs are [row, lord1, lord2] and adjacent runs differ."""
    doc = load("earthquake")
    for chart in doc["dasha"].values():
        runs = chart["runs"]
        assert runs[0][0] == 0
        for a, b in zip(runs, runs[1:]):
            assert b[0] > a[0] and a[1:] != b[1:]
