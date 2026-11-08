"""Every rule predicate on at least two golden charts.

Charts come from ``tests/fixtures/golden_charts.json`` (pyswisseph / PyJHora
oracle). The expected booleans were worked out by hand from the fixture's
sidereal positions, quoted in each comment (mean nodes, whole-sign houses):

ktm_1990 (Kathmandu 1990-05-15 04:45 UT): Lagna Cancer 13.3; Sun Taurus 0.4;
  Moon Sagittarius 29.7 (Uttara Ashadha); Mars Aquarius 24.4; Mercury Aries
  14.3 R; Jupiter Gemini 15.8; Venus Pisces 18.7; Saturn Capricorn 1.5 R;
  Rahu Capricorn 17.6; Ketu Cancer 17.6.
del_1947 (Delhi 1947-08-14 18:30 UT): Lagna Taurus 7.7; Sun Cancer 28.0;
  Moon Cancer 4.0; Mars Gemini 7.5; Mercury Cancer 13.7; Jupiter Libra 25.9
  (Vishakha); Venus Cancer 22.6; Saturn Cancer 20.5; Rahu Taurus 5.1.
grw_j2000 (Greenwich 2000-01-01 12:00 UT): Lagna Aries 0.4; Sun Sagittarius
  16.5; Moon Libra 19.5 (Swati); Mars Aquarius 4.1; Mercury Sagittarius 8.0;
  Jupiter Aries 1.4; Venus Scorpio 7.7; Saturn Aries 16.5 R; Rahu Cancer 11.2;
  Ketu Capricorn 11.2.
nyc_2001 (New York 2001-09-11 12:46 UT): Lagna Virgo 20.5; Sun Leo 25.0;
  Moon Gemini 4.2 (Mrigashira); Mars Sagittarius 7.6; Mercury Virgo 20.4;
  Jupiter Gemini 17.7; Venus Cancer 24.5; Saturn Taurus 20.9.
syd_2024 (Sydney 2024-02-28 19:00 UT): Lagna Aquarius 5.9; Sun Aquarius 15.5;
  Moon Libra 1.7; Mercury Aquarius 15.9; Jupiter Aries 16.9; Saturn Aquarius
  15.6.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from vedic_astrology_core.rules import PREDICATES, EvalContext, Location, check

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)
CHARTS = {c["id"]: c for c in FIXTURE["charts"]}


def chart_place(cid):
    """Location of a fixture chart."""
    c = CHARTS[cid]
    return Location(c["latitude"], c["longitude"], c["timezone"])


def chart_moment(cid):
    """UTC instant of a fixture chart."""
    return datetime.fromisoformat(CHARTS[cid]["utc"])


def ctx(cid, natal=None, moment=None):
    """Context at a golden chart, optionally with another chart as natal."""
    natal_pair = None
    if natal is not None:
        natal_pair = (chart_moment(natal), chart_place(natal))
    return EvalContext.at(moment or chart_moment(cid), chart_place(cid), natal_pair)


CASES = [
    # in_sign
    ("ktm_1990", "in_sign", {"planet": "Jupiter", "signs": ["Gemini"]}, True),
    ("ktm_1990", "in_sign", {"planet": "Jupiter", "signs": "Cancer"}, False),
    ("del_1947", "in_sign", {"planet": "Saturn", "signs": ["Cancer"]}, True),
    ("del_1947", "in_sign", {"planet": "Lagna", "signs": ["Vrishabha"]}, True),
    ("nyc_2001", "in_sign", {"planet": "Ascendant", "signs": ["Leo"]}, False),
    # in_house: whole sign from the Lagna
    ("ktm_1990", "in_house", {"planet": "Jupiter", "houses": [12]}, True),
    ("ktm_1990", "in_house", {"planet": "Jupiter", "houses": [1]}, False),
    ("del_1947", "in_house", {"planet": "Sun", "houses": 3}, True),
    ("grw_j2000", "in_house", {"planet": "Saturn", "houses": [1]}, True),
    # in_house_from
    (
        "ktm_1990",
        "in_house_from",
        {"planet": "Jupiter", "from": "Moon", "houses": [7]},
        True,
    ),
    (
        "del_1947",
        "in_house_from",
        {"planet": "Mars", "from": "Sun", "houses": [12]},
        True,
    ),
    (
        "del_1947",
        "in_house_from",
        {"planet": "Mars", "from": "Sun", "houses": [2]},
        False,
    ),
    (
        "nyc_2001",
        "in_house_from",
        {"planet": "Moon", "from": "Lagna", "houses": [10]},
        True,
    ),
    # in_kendra_from
    ("ktm_1990", "in_kendra_from", {"planet": "Jupiter", "from": "Moon"}, True),
    ("ktm_1990", "in_kendra_from", {"planet": "Mars", "from": "Moon"}, False),
    ("grw_j2000", "in_kendra_from", {"planet": "Jupiter", "from": "Moon"}, True),
    ("nyc_2001", "in_kendra_from", {"planet": "Jupiter", "from": "Moon"}, True),
    ("del_1947", "in_kendra_from", {"planet": "Jupiter", "from": "Lagna"}, False),
    # in_trikona_from
    ("grw_j2000", "in_trikona_from", {"planet": "Sun", "from": "Lagna"}, True),
    ("nyc_2001", "in_trikona_from", {"planet": "Mars", "from": "Lagna"}, False),
    ("ktm_1990", "in_trikona_from", {"planet": "Mars", "from": "Jupiter"}, True),
    # in_nakshatra
    (
        "ktm_1990",
        "in_nakshatra",
        {"planet": "Moon", "nakshatras": ["Uttara Ashadha"]},
        True,
    ),
    ("grw_j2000", "in_nakshatra", {"planet": "Moon", "nakshatras": ["Svati"]}, True),
    ("grw_j2000", "in_nakshatra", {"planet": "Moon", "nakshatras": ["Chitra"]}, False),
    (
        "del_1947",
        "in_nakshatra",
        {"planet": "Jupiter", "nakshatras": ["Visakha"]},
        True,
    ),
    # nakshatra_lord_is
    ("ktm_1990", "nakshatra_lord_is", {"planet": "Moon", "lords": ["Sun"]}, True),
    ("grw_j2000", "nakshatra_lord_is", {"planet": "Moon", "lords": ["Rahu"]}, True),
    ("grw_j2000", "nakshatra_lord_is", {"planet": "Moon", "lords": ["Ketu"]}, False),
    # dignity_in
    ("grw_j2000", "dignity_in", {"planet": "Jupiter", "dignities": ["friend"]}, True),
    (
        "grw_j2000",
        "dignity_in",
        {"planet": "Saturn", "dignities": ["debilitation"]},
        True,
    ),
    ("del_1947", "dignity_in", {"planet": "Moon", "dignities": ["own"]}, True),
    ("del_1947", "dignity_in", {"planet": "Mars", "dignities": ["enemy"]}, True),
    ("ktm_1990", "dignity_in", {"planet": "Venus", "dignities": ["exaltation"]}, True),
    ("ktm_1990", "dignity_in", {"planet": "Saturn", "dignities": ["own"]}, True),
    (
        "nyc_2001",
        "dignity_in",
        {"planet": "Mercury", "dignities": ["exaltation"]},
        True,
    ),
    (
        "nyc_2001",
        "dignity_in",
        {"planet": "Mercury", "dignities": ["moolatrikona"]},
        False,
    ),
    ("nyc_2001", "dignity_in", {"planet": "Sun", "dignities": ["moolatrikona"]}, False),
    (
        "syd_2024",
        "dignity_in",
        {"planet": "Saturn", "dignities": ["moolatrikona"]},
        True,
    ),
    # combust: Surya Siddhanta orbs
    ("syd_2024", "combust", {"planet": "Mercury"}, True),  # 0.4 deg from Sun
    ("syd_2024", "combust", {"planet": "Saturn"}, True),  # 0.1 deg
    ("syd_2024", "combust", {"planet": "Jupiter"}, False),
    ("grw_j2000", "combust", {"planet": "Mercury"}, True),  # 8.5 deg < 14
    ("grw_j2000", "combust", {"planet": "Venus"}, False),
    ("ktm_1990", "combust", {"planet": "Mercury"}, False),  # 16.1 > 12 (retro)
    # retrograde
    ("ktm_1990", "retrograde", {"planet": "Mercury"}, True),
    ("ktm_1990", "retrograde", {"planet": "Saturn"}, True),
    ("grw_j2000", "retrograde", {"planet": "Saturn"}, True),
    ("grw_j2000", "retrograde", {"planet": "Jupiter"}, False),
    ("nyc_2001", "retrograde", {"planet": "Saturn"}, False),
    ("nyc_2001", "retrograde", {"planet": "Rahu"}, True),
    # conjunct_within: degree orb, may cross a sign boundary
    ("syd_2024", "conjunct_within", {"planets": ["Sun", "Saturn"], "orb": 1}, True),
    ("syd_2024", "conjunct_within", {"planets": ["Sun", "Jupiter"], "orb": 1}, False),
    ("del_1947", "conjunct_within", {"planets": ["Venus", "Saturn"], "orb": 2}, False),
    ("del_1947", "conjunct_within", {"planets": ["Venus", "Saturn"], "orb": 3}, True),
    ("ktm_1990", "conjunct_within", {"planets": ["Moon", "Saturn"], "orb": 2}, True),
    # separation_within: Moon-Jupiter 161.9 deg at J2000; Jupiter-Mars 169.9
    (
        "grw_j2000",
        "separation_within",
        {"planets": ["Moon", "Jupiter"], "angle": 180, "orb": 20},
        True,
    ),
    (
        "grw_j2000",
        "separation_within",
        {"planets": ["Moon", "Jupiter"], "angle": 180, "orb": 15},
        False,
    ),
    (
        "nyc_2001",
        "separation_within",
        {"planets": ["Jupiter", "Mars"], "angle": 180, "orb": 12},
        True,
    ),
    # graha_drishti: whole-sign, special aspects of Mars, Jupiter, Saturn
    ("grw_j2000", "graha_drishti", {"planet": "Saturn", "target": "Moon"}, True),
    (
        "grw_j2000",
        "graha_drishti",
        {"planet": "Saturn", "target": "Ketu", "aspects": [10]},
        True,
    ),
    (
        "grw_j2000",
        "graha_drishti",
        {"planet": "Saturn", "target": "Ketu", "aspects": [3]},
        False,
    ),
    ("grw_j2000", "graha_drishti", {"planet": "Jupiter", "target": "Sun"}, True),
    ("grw_j2000", "graha_drishti", {"planet": "Mars", "target": "Venus"}, False),
    ("grw_j2000", "graha_drishti", {"planet": "Jupiter", "target": "Saturn"}, False),
    (
        "ktm_1990",
        "graha_drishti",
        {"planet": "Mars", "target": "Sun", "aspects": [4]},
        True,
    ),
    ("ktm_1990", "graha_drishti", {"planet": "Saturn", "target": "Venus"}, True),
    ("ktm_1990", "graha_drishti", {"planet": "Saturn", "target": "Lagna"}, True),
    ("ktm_1990", "graha_drishti", {"planet": "Jupiter", "target": "Mars"}, True),
    # varga_sign (D9/D10 from the fixture's PyJHora vargas)
    (
        "ktm_1990",
        "varga_sign",
        {"planet": "Moon", "varga": 9, "signs": ["Sagittarius"]},
        True,
    ),
    (
        "ktm_1990",
        "varga_sign",
        {"planet": "Jupiter", "varga": "D9", "signs": ["Aquarius"]},
        True,
    ),
    (
        "ktm_1990",
        "varga_sign",
        {"planet": "Venus", "varga": 10, "signs": ["Taurus"]},
        True,
    ),
    (
        "grw_j2000",
        "varga_sign",
        {"planet": "Lagna", "varga": 9, "signs": ["Aries"]},
        True,
    ),
    ("nyc_2001", "varga_sign", {"planet": "Sun", "varga": 9, "signs": ["Leo"]}, False),
    # planet_speed_below
    ("grw_j2000", "planet_speed_below", {"planet": "Saturn", "speed": 0.05}, True),
    ("grw_j2000", "planet_speed_below", {"planet": "Jupiter", "speed": 0.05}, True),
    ("ktm_1990", "planet_speed_below", {"planet": "Jupiter", "speed": 0.05}, False),
    (
        "ktm_1990",
        "planet_speed_below",
        {"planet": "Mercury", "speed": 0.01, "absolute": False},
        True,
    ),
    # longitude_between (wraps through 0 Aries)
    (
        "grw_j2000",
        "longitude_between",
        {"planet": "Jupiter", "start": 350, "end": 10},
        True,
    ),
    (
        "grw_j2000",
        "longitude_between",
        {"planet": "Sun", "start": 250, "end": 260},
        True,
    ),
    (
        "grw_j2000",
        "longitude_between",
        {"planet": "Sun", "start": 0, "end": 250},
        False,
    ),
    (
        "nyc_2001",
        "longitude_between",
        {"planet": "Sun", "start": 141.5, "end": 144.5},
        False,
    ),
    # moon_phase: elongation 239.3 (tithi 20) ktm; 303.0 (26) j2000; 5.7 (1) del_1984
    ("ktm_1990", "moon_phase", {"phase": "waning"}, True),
    ("ktm_1990", "moon_phase", {"tithis": [20]}, True),
    ("grw_j2000", "moon_phase", {"phase": "waxing"}, False),
    ("del_1984", "moon_phase", {"phase": "waxing", "tithis": [1, 2]}, True),
    ("lon_1900", "moon_phase", {"phase": "new"}, True),
    ("nyc_2044", "moon_phase", {"phase": "full"}, False),
    # weekday_lord_is: the vara runs sunrise to sunrise
    ("ktm_1990", "weekday_lord_is", {"lords": ["Mars"]}, True),  # Tuesday 10:30
    ("grw_j2000", "weekday_lord_is", {"lords": ["Saturn"]}, True),  # Saturday
    # 00:00 IST on Friday 15 Aug 1947 is still Thursday until sunrise.
    ("del_1947", "weekday_lord_is", {"lords": ["Jupiter"]}, True),
    ("del_1947", "weekday_lord_is", {"lords": ["Venus"]}, False),
]


@pytest.mark.parametrize("cid,name,params,expected", CASES)
def test_predicate_on_golden_chart(cid, name, params, expected):
    """The predicate's verdict matches the hand-derived value."""
    outcome = check(ctx(cid), name, **params)
    assert outcome.held is expected, outcome.evidence
    assert outcome.evidence


def test_kendra_is_counted_by_sign_not_degree():
    """Moon Aries 29 deg and Jupiter Cancer 28 deg are 4th by sign (S3-3).

    The old src detector used the 89-degree difference and missed this.
    """
    from vedic_astrology_core.rules.context import Sky

    positions = {
        "Moon": {"longitude": 29.0, "longitude_speed": 13.0},
        "Jupiter": {"longitude": 118.0, "longitude_speed": 0.1},
    }
    context = EvalContext(Sky.from_positions(positions))
    outcome = check(context, "in_kendra_from", planet="Jupiter", **{"from": "Moon"})
    assert outcome.held is True
    assert "4th from Moon in Aries" in outcome.evidence


def test_in_kendra_from_evidence_reads_as_plain_words():
    """Evidence names the signs and the house count."""
    outcome = check(
        ctx("ktm_1990"), "in_kendra_from", planet="Jupiter", **{"from": "Moon"}
    )
    assert outcome.evidence.startswith("Jupiter is in Gemini 15.8 deg, 7th from Moon")
    assert "which is a kendra" in outcome.evidence


@pytest.mark.parametrize(
    "cid,level,lords,expected",
    [
        # fixture dasha: ktm_1990 born in Sun-Rahu-Jupiter
        ("ktm_1990", 1, ["Sun"], True),
        ("ktm_1990", 2, ["Rahu"], True),
        ("ktm_1990", 3, ["Jupiter"], True),
        ("ktm_1990", 1, ["Moon"], False),
        # del_1947 born in Saturn-Saturn-Ketu
        ("del_1947", 1, ["Saturn"], True),
        ("del_1947", 3, ["Ketu"], True),
        ("del_1947", 2, ["Mercury"], False),
    ],
)
def test_dasha_lord_is_at_birth(cid, level, lords, expected):
    """Running Vimshottari lords at birth agree with the PyJHora fixture."""
    outcome = check(ctx(cid, natal=cid), "dasha_lord_is", level=level, lords=lords)
    assert outcome.held is expected, outcome.evidence


def test_antardasha_lord_is():
    """Antardasha at birth: ktm_1990 Rahu, del_1947 Saturn."""
    assert check(
        ctx("ktm_1990", natal="ktm_1990"), "antardasha_lord_is", lords="Rahu"
    ).held
    assert not check(
        ctx("ktm_1990", natal="ktm_1990"), "antardasha_lord_is", lords="Moon"
    ).held
    assert check(
        ctx("del_1947", natal="del_1947"), "antardasha_lord_is", lords=["Saturn"]
    ).held


def test_dasha_later_in_life():
    """ktm_1990 is in the Moon mahadasha from JD 2449717.26 (Dec 1994)."""
    later = datetime.fromisoformat("1996-01-01T00:00:00+00:00")
    context = ctx("ktm_1990", natal="ktm_1990", moment=later)
    assert check(context, "dasha_lord_is", lords=["Moon"]).held


def test_transit_in_house_from_natal():
    """1990 transits over the 1947 India chart (Lagna Taurus, Moon Cancer).

    Transit Saturn (Capricorn) is 9th from Taurus and 7th from Cancer; transit
    Ketu (Cancer) is 3rd from the Lagna.
    """
    context = ctx("ktm_1990", natal="del_1947")
    t = "transit_in_house_from_natal"
    assert check(context, t, planet="Saturn", houses=[9]).held
    assert check(context, t, planet="Saturn", houses=[7], **{"from": "Moon"}).held
    assert check(context, t, planet="Ketu", houses=[3]).held
    assert not check(context, t, planet="Ketu", houses=[9]).held


def test_transit_conjunct_natal():
    """2001 Venus (Cancer 24.5) is 3.5 deg from the 1947 Sun (Cancer 28.0).

    1990 Sun (Taurus 0.4) is 7.4 deg from the 1947 Lagna (Taurus 7.7).
    """
    t = "transit_conjunct_natal"
    c2001 = ctx("nyc_2001", natal="del_1947")
    assert check(c2001, t, planet="Venus", natal_point="Sun", orb=5).held
    assert not check(c2001, t, planet="Venus", natal_point="Sun", orb=3).held
    c1990 = ctx("ktm_1990", natal="del_1947")
    assert check(c1990, t, planet="Sun", natal_point="Lagna", orb=8).held
    assert not check(c1990, t, planet="Sun", natal_point="Lagna", orb=7).held


def test_eclipse_in_sign_near_golden_charts():
    """Eclipses around two golden charts (dates from the NASA catalogue).

    nyc_2001: total solar eclipse 2001-06-21 (82 days before; sidereal Sun in
    Gemini) and partial lunar eclipse 2001-07-05 (68 days before; Moon in
    Sagittarius). grw_j2000: total lunar eclipse 2000-01-21 (20 days after;
    Moon in Cancer).
    """
    nyc = ctx("nyc_2001")
    e = "eclipse_in_sign"
    assert check(
        nyc, e, kind="solar", signs=["Gemini"], days_before=90, days_after=0
    ).held
    assert check(
        nyc, e, kind="lunar", signs=["Sagittarius"], days_before=90, days_after=0
    ).held
    assert not check(nyc, e, kind="any", days_before=60, days_after=0).held
    assert not check(
        nyc, e, kind="solar", signs=["Leo"], days_before=90, days_after=0
    ).held
    j2000 = ctx("grw_j2000")
    assert check(
        j2000, e, kind="lunar", signs=["Cancer"], days_before=0, days_after=21
    ).held
    assert not check(j2000, e, kind="lunar", days_before=0, days_after=19).held


def test_eclipse_search_finds_known_eclipses():
    """2017-08-21 total solar (Sun in sidereal Leo) and 2018-07-27 total lunar."""
    from vedic_astrology_core.rules.eclipses import eclipses_between
    from vedic_astrology_core.utils.datetime_utils import julian_day

    start = julian_day(datetime.fromisoformat("2017-08-01T00:00:00+00:00"))
    end = julian_day(datetime.fromisoformat("2018-08-01T00:00:00+00:00"))
    found = eclipses_between(start, end, "any")
    solar = [e for e in found if e.kind == "solar"]
    lunar = [e for e in found if e.kind == "lunar"]
    aug = solar[0]
    assert aug.moment.strftime("%Y-%m-%d %H") == "2017-08-21 18"
    assert aug.subtype == "total"
    assert int(aug.longitude // 30) == 4  # Leo
    july = lunar[-1]
    assert july.moment.strftime("%Y-%m-%d %H") == "2018-07-27 20"
    assert july.subtype == "total"
    assert int(july.longitude // 30) == 9  # Capricorn


def test_ingress():
    """J2000: Moon (Libra 19.5, 12 deg/day) enters Scorpio about 0.88 day later.

    ktm_1990: the Sun (Taurus 0.4, 0.96 deg/day) entered Taurus 0.39 day before.
    """
    j2000 = ctx("grw_j2000")
    assert check(
        j2000, "ingress", planet="Moon", signs=["Scorpio"], days_before=0, days_after=1
    ).held
    assert not check(
        j2000, "ingress", planet="Moon", days_before=0, days_after=0.5
    ).held
    assert not check(j2000, "ingress", planet="Sun", days_before=1, days_after=1).held
    ktm = ctx("ktm_1990")
    assert check(
        ktm, "ingress", planet="Sun", signs="Taurus", days_before=1, days_after=0
    ).held
    assert not check(ktm, "ingress", planet="Sun", days_before=0.3, days_after=0).held


def test_every_predicate_is_covered_here():
    """Each registered predicate appears in a test in this file."""
    text = Path(__file__).read_text()
    missing = [name for name in PREDICATES if f'"{name}"' not in text]
    assert not missing


def test_every_predicate_has_a_docstring_and_example():
    """The vocabulary is documented for astrologers."""
    for name, spec in PREDICATES.items():
        assert len(spec.doc) > 40, name
        assert spec.example and name in spec.example, name
        spec.params.model_validate(spec.example[name])
