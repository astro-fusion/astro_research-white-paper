"""Festival days computed in-house (ADR-004 WP-06); the Gemini file is rejected."""

import csv
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from vedic_astrology_core.markets import festivals as f

FIXTURE = Path(__file__).parent / "fixtures" / "markets" / "festival_dates.csv"
ROWS = list(csv.DictReader(FIXTURE.open()))


def _iso(s):
    return date.fromisoformat(s)


# Spec cases (adhika-masa years 2020 and 2023 are where the Gemini file failed).
DIWALI = {2019: "2019-10-27", 2020: "2020-11-14", 2021: "2021-11-04",
          2022: "2022-10-24", 2023: "2023-11-12", 2024: "2024-10-31"}  # fmt: skip
AKSHAYA = {2019: "2019-05-07", 2020: "2020-04-26", 2021: "2021-05-14",
           2022: "2022-05-03", 2023: "2023-04-22", 2024: "2024-05-10"}  # fmt: skip


@pytest.mark.parametrize("year,expected", sorted(DIWALI.items()))
def test_diwali_2019_2024(year, expected):
    # 2024: amavasya covers sunset on 31 Oct and 1 Nov; 31 Oct is the convention.
    assert f.festival_dates(year, "diwali") == [_iso(expected)]


@pytest.mark.parametrize("year,expected", sorted(AKSHAYA.items()))
def test_akshaya_tritiya_2019_2024(year, expected):
    assert f.festival_dates(year, "akshaya_tritiya") == [_iso(expected)]


def test_rejected_gemini_dates_are_not_reproduced():
    assert _iso("2020-10-16") not in f.festival_dates(2020, "diwali")
    assert _iso("2021-04-15") not in f.festival_dates(2021, "akshaya_tritiya")


@pytest.mark.parametrize("name", sorted(f.FESTIVALS))
def test_fixture_has_at_least_ten_published_dates(name):
    assert sum(r["festival"] == name for r in ROWS) >= 10


@pytest.mark.parametrize("row", [r for r in ROWS if r["festival"] in f.FESTIVALS],
                         ids=lambda r: f"{r['festival']}-{r['year']}")
def test_festival_matches_published_date(row):
    assert f.festival_dates(int(row["year"]), row["festival"]) == [_iso(row["date"])]


def test_fixture_cites_a_source_in_every_row():
    assert all(r["source"].strip() for r in ROWS)


def test_adhik_maas_spans_match_published():
    starts = {int(r["year"]): _iso(r["date"]) for r in ROWS if r["festival"] == "adhik_maas_start"}
    ends = {int(r["year"]): _iso(r["date"]) for r in ROWS if r["festival"] == "adhik_maas_end"}
    assert len(starts) >= 10
    for y in starts:
        spans = f.adhik_maas(y)
        assert [(s["start"], s["end"]) for s in spans] == [(starts[y], ends[y])]


def test_no_adhik_maas_in_a_non_leap_year_and_festival_exists_once():
    assert f.adhik_maas(2022) == [] and f.adhik_maas(2024) == []
    for y in (2022, 2024):
        for name in f.FESTIVALS:
            assert len(f.festival_dates(y, name)) == 1


def test_adhika_month_flagged_and_nija_month_named_alike():
    months = [m for m in f.lunar_months(2020) if m["number"] == 7]
    assert [m["adhika"] for m in months] == [True, False]


def test_pitru_paksha_ends_on_mahalaya_and_lasts_about_15_days():
    for y in (2021, 2022, 2023):
        first, last = f.pitru_paksha(y)
        assert last == f.festival_dates(y, "mahalaya_amavasya")[0]
        assert 14 <= (last - first).days + 1 <= 16


def test_pushya_days_recur_about_every_27_days():
    days = f.pushya_dates(date(2023, 1, 1), date(2023, 12, 31))
    assert 12 <= len(days) <= 20
    firsts = [d for i, d in enumerate(days) if i == 0 or (d - days[i - 1]).days > 1]
    gaps = [(b - a).days for a, b in zip(firsts, firsts[1:])]
    assert all(26 <= g <= 28 for g in gaps)


def test_festival_flags_columns_and_dates():
    idx = pd.date_range("2020-10-01", "2020-11-30", freq="D")
    flags = f.festival_flags(idx)
    assert flags.index.equals(idx)
    assert flags.loc["2020-11-14", "diwali"] and flags["diwali"].sum() == 1
    assert flags.loc["2020-11-13", "dhanteras"]
    assert flags.loc["2020-10-01", "adhik_maas"] and not flags.loc["2020-10-17", "adhik_maas"]
    assert flags.loc["2020-10-01", "pitru_paksha"] is not None
    assert flags["guru_pushya"].sum() <= flags["pushya"].sum()


def test_unknown_festival_raises():
    with pytest.raises(ValueError):
        f.festival_dates(2020, "holi")
