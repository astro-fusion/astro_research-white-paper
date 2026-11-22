"""WP-76: metals adapter (gold and silver), ADR-007 4.2 with ADR-008 D-01, D-02, A-05, A-06."""

import hashlib
import json
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from vedic_astrology_core.domains.base import (
    DatasetGradeError,
    GateHashError,
    write_gate,
)
from vedic_astrology_core.domains import metals
from vedic_astrology_core.domains.metals import (
    MetalsDomain,
    PinError,
    SERIES,
    fixing_instants,
    month_active,
    parse_bundesbank,
)

REPO = Path(__file__).resolve().parents[1]
BB = "87c15f38332d991634191215733b37a120bb5f800b7b5bb17118884c69784474"
PK = "3c8d9d8dbb48342fdbf24777c39a8ce8964cc2fd0958f72f6779e6e4ad99cde2"
YG = "3085b0d501ecd3f123b6ca48ef4b13705e2d22d1a9465a0e9f463aa81032365a"
GATE = write_gate(Path(tempfile.mkdtemp()) / "gate.json", {"test": "metals"})


def _registers():
    index = json.loads((REPO / "data" / "snapshot_index.json").read_text())
    lic = yaml.safe_load((REPO / "data" / "registry" / "licences.yaml").read_text())
    return index, lic.get("sources", lic)


def _need(sha):
    index, _ = _registers()
    e = next((e for e in index["snapshots"] if e["sha256"] == sha), None)
    if e is None or not (REPO / e["file"]).is_file():
        pytest.skip(f"snapshot {sha[:12]} not on disk")


def _bundesbank_text(prices):
    """A Bundesbank-style CSV: a row for every calendar day, "." on days without a fixing."""
    lines = ['﻿"";BBEX3.D.XAU.DEM.EA.AC.C01;BBEX3.D.XAU.DEM.EA.AC.C01_FLAGS',
             "Einheit;DEM;"]
    days = pd.date_range(min(prices), max(prices), freq="D")
    for d in days:
        v = prices.get(d)
        lines.append(f"{d.date()};{v:.0f};" if v is not None else f"{d.date()};.;Kein Wert vorhanden")
    return "\n".join(lines) + "\n"


def _synthetic(tmp_path, prices, *, series="gold_dem_frankfurt", source="bundesbank_gold",
               text=None, verified=True):
    body = (text if text is not None else _bundesbank_text(prices)).encode()
    path = tmp_path / "snap.csv"
    path.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    index = {"schema": 1, "snapshots": [{"file": str(path), "sha256": sha, "source_id": source}]}
    lic = {source: {"verified": verified, "date_read": "2026-11-22" if verified else None}}
    grades = [{"sha256": sha, "reproduced": True, "open_items": [], "quality_flaws": [],
               "checked_by": "test", "date": "2026-11-22"}]
    return MetalsDomain(index, lic, series=series, pinned_sha256=sha, grades=grades,
                        vol_method="ewma", min_train=50, refit_every=5), path


def _walk(n=160, start="1985-01-02", seed=1):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, periods=n)
    p = 30000 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    return dict(zip(days, p))


# ------------------------------------------------------------------ real data
@pytest.fixture(scope="module")
def frankfurt():
    _need(BB)
    index, lic = _registers()
    return MetalsDomain(index, lic, series="gold_dem_frankfurt", pinned_sha256=BB,
                        vol_method="ewma")


def test_bundesbank_pinned_snapshot_has_7622_fixings(frankfurt):
    assert len(frankfurt._raw_prices()) == 7622
    g = frankfurt.grid()
    assert len(g) == 7621  # the first fixing opens the series
    assert str(g[0].date()) == "1968-06-19" and str(g[-1].date()) == "1998-12-30"
    ds = frankfurt.dataset()
    assert ds.grade == "B" and "licence not yet read" in ds.limitations
    assert ds.id.startswith("gold_dem_frankfurt_87c15f38332d")


def test_frankfurt_outcomes_stay_in_dem_and_name_market(frankfurt):
    ids = frankfurt.outcome_ids()
    for oid in ids:
        tokens = set(oid.replace(".", "_").split("_"))
        assert {"gold", "dem", "frankfurt"} <= tokens
    assert "usd" not in " ".join(ids)
    assert frankfurt.calendar_context()["market_sentence"] == "tested on the Frankfurt fixing in DEM"
    assert "gold_usd_frankfurt.log_return" in frankfurt.declared_cells()["untestable"]
    assert frankfurt.declared_cells()["garch_x"] == {"role": "secondary"}
    assert any("German marks" in x for x in frankfurt.limitations())


def test_frankfurt_sampling_instant_follows_cet_and_cest(frankfurt):
    """The WP-76 risk: 13:00 Frankfurt is 12:00 UTC in winter and before 1980, 11:00 UTC in summer from 1980."""
    spec = SERIES["gold_dem_frankfurt"]
    inst = fixing_instants(["1979-07-16", "1980-07-15", "1985-01-15", "1985-07-15"], spec)
    assert [t.hour for t in inst] == [12, 11, 12, 11]
    assert str(inst.tz) == "UTC"
    ctx = frankfurt.calendar_context()
    assert ctx["sample_instants"][0] == pd.Timestamp("1968-06-19 12:00", tz="UTC")
    assert len(ctx["sample_instants"]) == len(frankfurt.grid())
    assert ctx["timezone"] == "Europe/Berlin" and ctx["fixing_time"] == "13:00"


def test_frankfurt_gaps_and_two_tier_are_outcome_free_context(frankfurt):
    ctx = frankfurt.calendar_context()
    gaps, flag = ctx["gap_days"], ctx["long_gap"]
    assert len(gaps) == len(frankfurt.grid())
    assert (flag == (gaps > 4)).all() and flag.sum() > 0
    tt = ctx["two_tier"]
    g = frankfurt.grid()
    assert tt[0] and not tt[g > pd.Timestamp("1971-08-15")].any()


def test_frankfurt_periods_follow_adr_split(frankfurt):
    p = frankfurt.periods()
    assert p.explore[1] == date(1986, 12, 31) and p.confirm[0] == date(1987, 1, 1)
    assert not p.pseudo_out_of_sample


def test_outcomes_and_controls_need_gate(frankfurt):
    with pytest.raises(GateHashError):
        frankfurt.outcomes()
    with pytest.raises(GateHashError):
        frankfurt.controls("0" * 64)


def test_frankfurt_outcomes_flag_long_gaps(frankfurt):
    o = frankfurt.outcomes(GATE)
    r = o["gold_dem_frankfurt.log_return"]
    assert len(r) == 7621 and o["guard_bars"] == 0
    assert (o["long_gap"] == (o["gap_days"] > 4)).all()
    em = o["gold_dem_frankfurt.extreme_move"].dropna()
    assert 0.02 < em.mean() < 0.12  # a past-only 95th percentile flags about 5%


# ------------------------------------------------------------------ Pink Sheet
@pytest.fixture(scope="module")
def pink_gold():
    _need(PK)
    index, lic = _registers()
    return MetalsDomain(index, lic, series="gold_usd_pinksheet", pinned_sha256=PK)


def test_pinksheet_monthly_starts_after_official_price(pink_gold):
    g = pink_gold.grid()
    assert str(g[0].date()) == "1968-05-01"  # price used from 1968-04, first return 1968-05
    assert (g.day == 1).all()
    assert pink_gold.dataset().grade == "B"
    ctx = pink_gold.calendar_context()
    assert ctx["guard_bars"] == 1 and ctx["timezone"] == "Europe/London"
    di = ctx["daily_instants"]
    assert di[0] == pd.Timestamp("1968-05-01 14:00", tz="UTC")  # 15:00 London summer time (UTC+1)
    p = pink_gold.periods()
    assert p.confirm[0] == date(2000, 1, 1) and p.pseudo_out_of_sample
    o = pink_gold.outcomes(GATE)
    assert set(pink_gold.outcome_ids()) <= set(o)
    assert o["guard_bars"] == 1


def test_silver_monthly_has_gold_co_movement_and_blocks_unchecked_festivals():
    _need(PK)
    index, lic = _registers()
    a = MetalsDomain(index, lic, series="silver_usd_pinksheet", pinned_sha256=PK)
    assert all("silver" in k and "usd" in k and "pinksheet" in k for k in a.outcome_ids())
    c = a.controls(GATE)
    co = c["gold_co_movement"]
    assert len(co) == len(a.grid()) and co.notna().all()
    if c["festival_check"]:  # D-09 spot-check not yet supplied: no festival baseline
        assert c["festival_terms"] is None and c["baselines_complete"] is False
    assert list(c["calendar_terms"].columns)[0] == "month_02"


def test_month_active_needs_half_the_days():
    days = pd.date_range("2001-01-01", "2001-02-28", freq="D")
    active = pd.Series(False, index=days)
    active.iloc[:16] = True  # 16 of 31 January days
    active.iloc[31:31 + 13] = True  # 13 of 28 February days
    out = month_active(active, ["2001-01-01", "2001-02-01"])
    assert out.tolist() == [True, False]
    with pytest.raises(ValueError, match="cover"):
        month_active(active, ["2001-03-01"])


# ------------------------------------------------------------------ Yahoo is grade C
def test_yahoo_series_is_grade_c_even_with_a_clean_register(tmp_path):
    text = "date,close,source,series_id,is_futures,volume\n" + "\n".join(
        f"{d.date()},{1000 + i},yahoo,GC=F,True,10" for i, d in enumerate(pd.bdate_range("2001-01-02", periods=30))
    )
    a, _ = _synthetic(tmp_path, None, series="gold_usd_comex", source="yahoo_finance", text=text)
    ds = a.dataset()
    assert ds.grade == "C" and "GC=F" in ds.limitations[0]
    with pytest.raises(DatasetGradeError):
        a.require_verdict_grade()


def test_real_yahoo_snapshot_is_grade_c():
    _need(YG)
    index, lic = _registers()
    a = MetalsDomain(index, lic, series="gold_usd_comex", pinned_sha256=YG)
    assert a.dataset().grade == "C"


# ------------------------------------------------------------------ pins
def test_pin_is_required_and_checked(tmp_path):
    a, path = _synthetic(tmp_path, _walk(20))
    index, lic = a._index, a._licences
    with pytest.raises(PinError, match="pin"):
        MetalsDomain(index, lic, series="gold_dem_frankfurt").grid()
    with pytest.raises(PinError, match="not in the snapshot index"):
        MetalsDomain(index, lic, series="gold_dem_frankfurt", pinned_sha256="a" * 64).grid()
    with pytest.raises(PinError, match="needs 'worldbank_pinksheet'"):
        MetalsDomain(index, lic, series="gold_usd_pinksheet",
                     pinned_sha256=index["snapshots"][0]["sha256"]).grid()
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(PinError, match="do not hash"):
        MetalsDomain(index, lic, series="gold_dem_frankfurt",
                     pinned_sha256=index["snapshots"][0]["sha256"]).grid()
    with pytest.raises(ValueError, match="unknown metals series"):
        MetalsDomain(index, lic, series="gold")


def test_clean_register_gives_grade_a(tmp_path):
    a, _ = _synthetic(tmp_path, _walk(20))
    assert a.dataset().grade == "A"


# ------------------------------------------------------------------ parsing and gaps
def test_parse_bundesbank_skips_dot_days_and_refuses_junk():
    s = parse_bundesbank("x;y;\n1970-01-02;1000;\n1970-01-03;.;Kein Wert\n1970-01-05;1010;\n")
    assert list(s.index.strftime("%Y-%m-%d")) == ["1970-01-02", "1970-01-05"]
    with pytest.raises(ValueError, match="unexpected"):
        parse_bundesbank("1970-01-02;abc;\n")


def test_returns_over_more_than_four_days_are_flagged(tmp_path):
    days = ["1985-03-01", "1985-03-04", "1985-03-08", "1985-03-13", "1985-03-14"]
    prices = {pd.Timestamp(d): 30000.0 + 10 * i for i, d in enumerate(days)}
    a, _ = _synthetic(tmp_path, prices)
    ctx = a.calendar_context()
    assert ctx["gap_days"].tolist() == [3, 4, 5, 1]
    assert ctx["long_gap"].tolist() == [False, False, True, False]
    # weekdays without a fixing are the series' own holidays (not US holidays)
    hol = a.holidays()
    assert pd.Timestamp("1985-03-05") in hol and pd.Timestamp("1985-03-04") not in hol


def test_outcomes_are_past_only(tmp_path):
    prices = _walk(160)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a, _ = _synthetic(tmp_path / "a", prices)
    later = dict(prices)
    k = sorted(later)[120]
    later[k] = later[k] * 1.3  # a shock at price date 120; nothing before it may change
    b, _ = _synthetic(tmp_path / "b", later)
    oa, ob = a.outcomes(GATE), b.outcomes(GATE)
    cut = pd.Timestamp(k)
    for key in ("gold_dem_frankfurt.abs_return_std", "gold_dem_frankfurt.extreme_move",
                "extreme_threshold"):
        xa, xb = oa[key][oa[key].index < cut], ob[key][ob[key].index < cut]
        pd.testing.assert_series_equal(xa, xb)
    assert not oa["gold_dem_frankfurt.abs_return_std"].equals(ob["gold_dem_frankfurt.abs_return_std"])
    thr = oa["extreme_threshold"]
    assert thr.iloc[:50].isna().all() and thr.iloc[51:].notna().all()


def test_daily_controls_use_series_holidays_and_no_lunar_terms(tmp_path):
    a, _ = _synthetic(tmp_path, _walk(60))
    c = a.controls(GATE)
    cols = set(c["calendar_terms"].columns)
    assert {"turn_of_month", "holiday_eve", "wd_1"} <= cols
    assert not any(col.startswith("moon_") for col in c["baselines"].columns)
    assert c["macro_terms"] is None


# ------------------------------------------------------------------ A-05
def test_sunrise_and_fixing_conventions_disagree_for_the_moon(tmp_path):
    from vedic_astrology_core.rules.context import get_engine
    from vedic_astrology_core.config.constants import Planet

    eng = get_engine()

    def nakshatra(instants):
        out = []
        for t in instants:
            jd = eng.datetime_to_julian_day(t.to_pydatetime())
            out.append(int(eng.get_planet_position(jd, Planet.MOON)["longitude"] // (360 / 27)))
        return out

    a, _ = _synthetic(tmp_path, _walk(60, start="1975-01-02"))
    res = a.convention_disagreement(nakshatra)
    assert res["n_days"] == 59 and res["place"] == "New Delhi"
    assert 0.2 < res["share"] < 0.8  # about 11 hours apart: the Moon moves about 6 degrees
    same = a.convention_disagreement(lambda inst: [0] * len(inst))
    assert same["share"] == 0.0
