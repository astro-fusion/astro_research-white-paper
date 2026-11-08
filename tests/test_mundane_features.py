"""Tests for sign-level transit-to-natal features (two countries, two events)."""

from datetime import date, datetime

import pytest
import yaml

from studies.mundane.scripts import features as F
from studies.mundane.scripts.validate_data import COUNTRIES_FILE
from vedic_astrology_core.config.constants import Planet


@pytest.fixture(scope="module")
def countries():
    """Countries."""
    rows = yaml.safe_load(COUNTRIES_FILE.read_text())["countries"]
    return {c["iso"]: c for c in rows}


def test_naive_datetime_raises(countries):
    """Naive datetime raises."""
    with pytest.raises(ValueError):
        F.moment_features(countries["US"], datetime(2001, 9, 11, 12, 0))


def test_natal_is_noon_without_houses(countries):
    """Natal is noon without houses."""
    natal = F.natal_chart(countries["US"])
    assert natal["time_known"] is False
    assert natal["houses"] is None
    assert natal["datetime"].hour == 12 and natal["datetime"].tzinfo is not None
    # 1776-07-04 noon: sidereal Sun in Gemini (index 2), Lahiri
    assert natal["signs"][Planet.SUN] == 2
    assert set(natal["signs"]) == set(F.NATAL_PLANETS)


def test_india_natal_sun_is_cancer(countries):
    """India natal sun is cancer."""
    natal = F.natal_chart(countries["IN"])
    assert natal["signs"]["SUN"] == 3  # 1947-08-15: sidereal Cancer


def test_sign_relation_arithmetic():
    """Sign relation arithmetic."""
    same = F.sign_relation(4, 4, Planet.SUN)
    assert same["conjunct_sign"] and not same["opposition_sign"]
    opp = F.sign_relation(0, 6, Planet.SUN)
    assert opp["opposition_sign"] and opp["aspect_whole_sign"]
    assert opp["signs_between"] == 6
    # Saturn aspects 3rd and 10th from itself; Sun does not
    assert F.sign_relation(0, 2, Planet.SATURN)["aspect_whole_sign"]
    assert not F.sign_relation(0, 2, Planet.SUN)["aspect_whole_sign"]
    # wrap-around: transit Pisces (11) to natal Aries (0) is one sign ahead
    assert F.sign_relation(11, 0, Planet.MARS)["signs_between"] == 1


def test_event_9_11_united_states(countries):
    """Event 9 11 united states."""
    us = countries["US"]
    when = F.local_datetime(date(2001, 9, 11), us["timezone"])
    rows = F.moment_features(us, when, window_days=30)
    assert all(r["time_known"] is False and r["iso"] == "US" for r in rows)
    pairs = [r for r in rows if r["family"] == "transit_natal"]
    assert len(pairs) == 81
    ingress = [r for r in rows if r["family"] == "ingress"]
    # Sun entered sidereal Virgo about 5 days later and Leo about 26 days earlier
    assert sorted(r["to_sign"] for r in ingress) == [4, 5]
    assert any(abs(r["days_offset"] - 5.0) < 0.2 for r in ingress)
    stations = {r["planet"]: r for r in rows if r["family"] == "station"}
    assert stations["SATURN"]["kind"] == "retrograde"
    assert abs(stations["SATURN"]["days_offset"] - 15.3) < 0.5
    assert not [r for r in rows if r["family"] == "eclipse"]


def test_event_gujarat_earthquake_india(countries):
    """Event gujarat earthquake india."""
    india = countries["IN"]
    when = F.local_datetime(date(2001, 1, 26), india["timezone"])
    rows = F.moment_features(india, when, window_days=30)
    ecl = [r for r in rows if r["family"] == "eclipse"]
    # total lunar eclipse of 2001-01-09, 17 days before
    assert len(ecl) == 1
    assert ecl[0]["kind"] == "lunar" and abs(ecl[0]["days_offset"] + 16.9) < 1.0
    assert all(r["time_known"] is False for r in rows)


def test_known_time_unlocks_flag_but_not_houses(countries):
    """Known time unlocks flag but not houses."""
    c = dict(countries["IN"])
    c["founding"] = dict(c["founding"], time="00:00:00", time_known=True)
    natal = F.natal_chart(c)
    assert natal["time_known"] is True and natal["datetime"].hour == 0
    assert natal["houses"] is None  # lagna is not computed by this module
