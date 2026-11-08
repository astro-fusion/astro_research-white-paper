"""markets.features: engine-derived indicators, enum labels, loud failures."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.config.constants import Planet
from vedic_astrology_core.markets import features

ENGINE = EphemerisEngine()
J2000 = pd.DatetimeIndex([pd.Timestamp("2000-01-01 12:00", tz="UTC")])


def test_unknown_body_raises():
    """S1-12: Uranus is not dropped silently."""
    with pytest.raises(ValueError, match="Unknown body 'Uranus'"):
        features.resolve_bodies(["Sun", "Uranus"])
    assert features.resolve_bodies(["sun", Planet.KETU]) == [Planet.SUN, Planet.KETU]


def test_naive_instants_raise():
    """Check naive instants raise."""
    with pytest.raises(ValueError):
        features.indicator_frame(pd.DatetimeIndex(["2000-01-01"]), ["Sun"], ENGINE)


def test_frame_matches_engine_and_uses_enum_values():
    """Check frame matches engine and uses enum values."""
    frame = features.indicator_frame(
        J2000, ["Sun", "Moon", "Jupiter"], ENGINE, lagna_sign=0
    )
    jd = ENGINE.datetime_to_julian_day(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
    pos = ENGINE.get_all_planet_positions(jd)
    row = frame.iloc[0]
    assert row["SUN_lon"] == pytest.approx(pos[Planet.SUN]["longitude"])
    assert row["SUN_sign"] == "Sagittarius"  # sidereal Sun at J2000 ~256.5 deg
    assert row["SUN_house"] == 9  # whole-sign from an Aries lagna
    assert row["SUN_nakshatra"] == "Purva Ashadha"
    assert row["SUN_nak_lord"] == "VENUS"
    assert all("Planet." not in str(v) for v in row.values)
    assert row["JUPITER_retro"] == pos[Planet.JUPITER]["retrograde"]
    assert 1 <= row["tithi"] <= 30


def test_dasha_lord_from_natal_chart():
    """Check dasha lord from natal chart."""
    natal = {"birth": datetime(1990, 1, 1, tzinfo=timezone.utc), "moon_longitude": 0.5}
    # Moon in Ashwini (Ketu) at 0.5 deg: Ketu mahadasha runs about 6.6 more years.
    idx = pd.DatetimeIndex(
        [pd.Timestamp("1991-01-01", tz="UTC"), pd.Timestamp("2000-01-01", tz="UTC")]
    )
    frame = features.indicator_frame(idx, ["Moon"], ENGINE, natal=natal)
    assert frame["dasha_lord"].tolist() == ["KETU", "VENUS"]


def test_rule_firings_from_registry_agree_with_engine():
    """Check rule firings from registry agree with engine."""
    idx = pd.date_range("2020-01-01", periods=60, freq="7D", tz="UTC")
    frame = features.indicator_frame(
        idx, ["Venus", "Jupiter"], ENGINE, rules_use_case="financial"
    )
    if frame.attrs.get("rules_skipped"):
        pytest.skip(f"registry unavailable: {frame.attrs['rules_skipped']}")
    assert "rule:Venus-Retrograde-Reversal" in frame.columns
    assert (frame["rule:Venus-Retrograde-Reversal"] == frame["VENUS_retro"]).all()
    jup = frame["rule:Jupiter-Retrograde-Contraction"]
    assert (jup == frame["JUPITER_retro"]).all()


def test_rule_firings_skip_with_warning_when_registry_breaks(monkeypatch, caplog):
    """Check rule firings skip with warning when registry breaks."""
    import vedic_astrology_core.combinations as comb

    def boom():
        raise RuntimeError("registry mid-change")

    monkeypatch.setattr(comb, "get_registry", boom)
    out = features.rule_firings(J2000, "financial", ENGINE)
    assert out.empty and "registry mid-change" in out.attrs["rules_skipped"]
    assert "rule firings skipped" in caplog.text


def test_build_indicators_specs_and_failures():
    """Check build indicators specs and failures."""
    idx = pd.date_range("2020-01-01", periods=400, freq="D", tz="UTC")
    frame = features.indicator_frame(idx, ["Sun", "Moon", "Mercury"], ENGINE)
    specs = [
        {"id": "mercury_retro", "kind": "retrograde", "body": "Mercury"},
        {"id": "sun_aries", "kind": "in_sign", "body": "Sun", "signs": ["Aries"]},
        {"id": "purnima", "kind": "tithi", "tithis": [15]},
    ]
    ind = features.build_indicators(frame, specs)
    assert ind["mercury_retro"].tolist() == frame["MERCURY_retro"].tolist()
    assert 28 <= ind["sun_aries"].sum() <= 32
    assert 12 <= ind["purnima"].sum() <= 16
    with pytest.raises(ValueError, match="never active"):
        features.build_indicators(
            frame, [{"id": "x", "kind": "in_sign", "body": "Sun", "signs": ["Nowhere"]}]
        )
    with pytest.raises(ValueError, match="unknown indicator kind"):
        features.build_indicators(frame, [{"id": "x", "kind": "vibes"}])
