"""Mundane predicates and tables, checked on known dates.

Each expected value below is a published fact (an eclipse date, a cluster,
a perihelic opposition, a calendar date) or a table from the cited verse.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from vedic_astrology_core.astrology import mundane as m
from vedic_astrology_core.rules import EvalContext, check
from vedic_astrology_core.rules.schema import Rule
from vedic_astrology_core.rules.strength import strength_value


def at(y, mo, d, h=0, mi=0):
    """Return a context at a UTC instant."""
    return EvalContext.at(datetime(y, mo, d, h, mi, tzinfo=timezone.utc))


# ------------------------------------------------------------------ tables
def test_kurma_table_follows_brihat_samhita_14():
    """BS 14.1-31: three asterisms per division from Krittika in the centre."""
    table = m.kurma_table("krittika")
    assert table["centre"] == ["Krittika", "Rohini", "Mrigashira"]
    assert table["east"] == ["Ardra", "Punarvasu", "Pushya"]
    assert table["south_east"] == ["Ashlesha", "Magha", "Purva Phalguni"]
    assert table["south"] == ["Uttara Phalguni", "Hasta", "Chitra"]
    assert table["south_west"] == ["Swati", "Vishakha", "Anuradha"]
    assert table["west"] == ["Jyeshtha", "Mula", "Purva Ashadha"]
    assert table["north_west"] == ["Uttara Ashadha", "Shravana", "Dhanishta"]
    assert table["north"] == ["Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada"]
    assert sorted(table["north_east"]) == ["Ashwini", "Bharani", "Revati"]


def test_kurma_practitioner_convention_starts_in_the_north():
    """The AstroRidhis table: Ashwini, Bharani, Krittika north; then north-east."""
    table = m.kurma_table("ashwini")
    assert table["north"] == ["Ashwini", "Bharani", "Krittika"]
    assert table["north_east"] == ["Rohini", "Mrigashira", "Ardra"]


def test_mandalas_partition_the_27_nakshatras():
    """BS 32: four circles, each asterism in exactly one (Abhijit dropped)."""
    names = [n for group in m.MANDALAS.values() for n in group]
    assert len(names) == 27 and len(set(names)) == 27
    assert m.mandala_of("Uttara Bhadrapada") == "varuna"
    assert m.mandala_of("Uttara Ashadha") == "indra"
    assert m.mandala_of("Krittika") == "agni"
    assert m.mandala_of("Ashwini") == "vayu"


@pytest.mark.parametrize(
    "year, start, name",
    [
        (1987, "1987-03-29", "Prabhava"),
        (2023, "2023-03-21", "Shobhakrit"),
        (2024, "2024-04-08", "Krodhi"),
        (2025, "2025-03-29", "Vishvavasu"),
    ],
)
def test_samvatsara_and_year_start(year, start, name):
    """Ugadi (Chaitra Shukla Pratipada) begins at the preceding new Moon (UT)."""
    jd = m.year_start(year)
    got = m.samvatsara(jd + 1.0)
    assert got[0] == name
    assert got[2].date().isoformat() == start


def test_lunar_month_with_an_adhika():
    """2023 had an adhika Shravana (18 July - 16 August)."""
    import swisseph as swe

    name, adhika, _ = m.lunar_month(swe.julday(2023, 8, 1, 0.0))
    assert (name, adhika) == ("Shravana", True)
    name, adhika, _ = m.lunar_month(swe.julday(2023, 8, 25, 0.0))
    assert (name, adhika) == ("Shravana", False)


def test_eclipse_magnitudes():
    """1 August 2008 total solar (1.039 max); 16 August 2008 partial lunar 0.81."""
    import swisseph as swe

    assert m.eclipse_magnitude("solar", swe.julday(2008, 8, 1, 10.35)) > 1.0
    lunar = swe.lun_eclipse_when(swe.julday(2008, 8, 10), swe.FLG_SWIEPH, 0)[1][0]
    assert m.eclipse_magnitude("lunar", lunar) == pytest.approx(0.81, abs=0.01)


# ------------------------------------------------------------- predicates
def test_planets_in_one_sign_gte_on_the_1962_cluster():
    """4-5 February 1962: all seven visible grahas in sidereal Capricorn."""
    out = check(at(1962, 2, 5), "planets_in_one_sign_gte", count=7)
    assert out.held and "7 in Capricorn" in out.evidence
    assert not check(
        at(1962, 2, 5), "planets_in_one_sign_gte", count=7, signs=["Aquarius"]
    ).held
    assert not check(at(2020, 1, 1), "planets_in_one_sign_gte", count=5).held


def test_eclipse_within_days_with_pair_and_magnitude():
    """1 August 2008 total solar eclipse, paired with the 16 August lunar."""
    out = check(
        at(2008, 8, 7),
        "eclipse_within_days",
        kind="solar",
        days_before=10,
        pair_within_days=16,
        min_magnitude=0.9,
    )
    assert out.held and "paired with the lunar of 2008-08-16" in out.evidence
    assert not check(
        at(2008, 8, 7), "eclipse_within_days", kind="solar", days_before=3
    ).held
    # 2008-02-07 annular solar and 2008-02-21 total lunar: also a pair
    assert check(
        at(2008, 2, 10),
        "eclipse_within_days",
        kind="lunar",
        days_after=15,
        pair_within_days=16,
    ).held
    # magnitude threshold above the 1 August eclipse fails
    assert not check(
        at(2008, 8, 7),
        "eclipse_within_days",
        kind="solar",
        days_before=10,
        min_magnitude=1.2,
    ).held


def test_eclipse_within_days_can_drop_penumbral():
    """9 February 2009 was a penumbral-only lunar eclipse."""
    assert check(
        at(2009, 2, 9), "eclipse_within_days", kind="lunar", days_before=1, days_after=1
    ).held
    assert not check(
        at(2009, 2, 9),
        "eclipse_within_days",
        kind="lunar",
        days_before=1,
        days_after=1,
        penumbral=False,
    ).held


def test_eclipse_degree_transited_by():
    """The 26 December 2019 solar eclipse fell at sidereal Sagittarius 10.

    On 1 June 2020 Saturn was 27 deg past it. At greatest eclipse the Sun
    stands on the eclipse degree by definition, and the node opposite the
    eclipse (Rahu, with the eclipse near Ketu) opposes it.
    """
    assert not check(
        at(2020, 6, 1),
        "eclipse_degree_transited_by",
        planets=["Saturn"],
        orb=5,
        kind="solar",
    ).held
    out = check(
        at(2019, 12, 26, 5, 18),
        "eclipse_degree_transited_by",
        planets=["Sun"],
        orb=0.5,
        kind="solar",
        lookback_days=1,
    )
    assert out.held and "Sagittarius 10.0" in out.evidence
    opp = check(
        at(2019, 12, 26, 5, 18),
        "eclipse_degree_transited_by",
        planets=["Rahu"],
        orb=10,
        angles=[180],
        kind="solar",
        lookback_days=1,
    )
    assert opp.held  # Rahu opposes the Sun-Moon at a solar eclipse near Ketu


def test_kurma_direction_conventions_disagree_on_krittika():
    """Rahu in Krittika (1 June 2022): centre by BS 14, north by the practitioner."""
    assert check(
        at(2022, 6, 1), "kurma_direction", planet="Rahu", directions=["centre"]
    ).held
    assert check(
        at(2022, 6, 1),
        "kurma_direction",
        planet="Rahu",
        directions=["north"],
        start="ashwini",
    ).held
    with pytest.raises(ValidationError):
        check(at(2022, 6, 1), "kurma_direction", planet="Rahu", directions=["up"])


def test_moon_mandala_on_tohoku_and_gorkha():
    """Tohoku (Moon in Krittika: Agni); Gorkha (Moon in Punarvasu: Vayu)."""
    assert check(at(2011, 3, 11, 5, 46), "moon_mandala", mandalas=["agni"]).held
    out = check(at(2015, 4, 25, 6, 11), "moon_mandala", mandalas=["agni"])
    assert not out.held and "Vayu" in out.evidence


def test_planet_distance_at_the_2003_perihelic_opposition():
    """Mars came to 0.3727 au on 27 August 2003, the closest in 60,000 years."""
    out = check(at(2003, 8, 27, 10), "planet_distance_au_lte", planet="Mars", au=0.38)
    assert out.held and "0.373 au" in out.evidence
    assert not check(
        at(2005, 1, 1), "planet_distance_au_lte", planet="Mars", au=0.5
    ).held
    with pytest.raises(ValidationError, match="nodes have no distance"):
        check(at(2005, 1, 1), "planet_distance_au_lte", planet="Rahu", au=1)


def test_samvatsara_is():
    """2024-25 is Krodhi; the day before Ugadi 2024 was still Shobhakrit."""
    assert check(at(2024, 6, 1), "samvatsara_is", names=["Krodhi"]).held
    assert check(at(2024, 4, 8), "samvatsara_is", names=["Shobhakrit"]).held
    with pytest.raises(ValidationError, match="unknown samvatsara"):
        check(at(2024, 6, 1), "samvatsara_is", names=["Krodha"])


def test_eclipse_magnitude_strength_term():
    """The strength term reads the largest magnitude in the window."""
    rule = Rule.model_validate(
        {
            "id": "t.ecl",
            "name": "n",
            "domain": "mundane",
            "claim": "c",
            "source": {"text": "BS"},
            "author": "a",
            "tier": "experimental",
            "conditions": {"eclipse_within_days": {"days_before": 10}},
            "strength": {
                "combine": "product",
                "terms": [{"eclipse_magnitude": {"kind": "any", "days_before": 10}}],
            },
            "reference_cases": [
                {"moment": "2008-08-07T00:00:00Z", "expect": "fires", "note": "n"}
            ],
        }
    )
    value, words = strength_value(rule.strength, at(2008, 8, 7))
    assert value == 1.0 and "1.02" in words[0]
    value, _ = strength_value(rule.strength, at(2008, 8, 20))
    assert value == pytest.approx(0.81, abs=0.01)


# ------------------------------------- dasha lords and transits over vargas
# Natal: the 1947 India chart of the golden fixture (del_1947: Lagna Taurus,
# Moon Cancer, Venus Cancer, Saturn Cancer, Jupiter Libra, Ketu Scorpio).
# Fixture D9 (PyJHora): Lagna Pisces, Moon Leo, Venus Capricorn, Jupiter
# Taurus, Saturn Capricorn. At nyc_2001 the running period is Venus-Jupiter-
# Sun; at del_1947 itself it is Saturn-Saturn-Ketu (fixture dasha).
import json as _json  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

from vedic_astrology_core.rules import PREDICATES, Location  # noqa: E402
from vedic_astrology_core.rules.context import (  # noqa: E402
    VargaNotComputable,
    check_varga,
)

_GOLDEN = {
    c["id"]: c
    for c in _json.loads(
        (_Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
    )["charts"]
}


def _golden(cid):
    c = _GOLDEN[cid]
    return (
        datetime.fromisoformat(c["utc"]),
        Location(c["latitude"], c["longitude"], c["timezone"]),
    )


def over_india(cid):
    """Context at golden chart ``cid`` with the 1947 India chart as natal."""
    moment, place = _golden(cid)
    return EvalContext.at(moment, place, _golden("del_1947"))


NEW = (
    "dasha_lord_in_house",
    "dasha_lord_rules_house",
    "dasha_lord_dignity",
    "transit_aspects_natal",
)


def test_natal_varga_helpers_match_the_fixture():
    """D9 signs of the natal points agree with the PyJHora vargas."""
    ctx = over_india("nyc_2001")
    d9 = _GOLDEN["del_1947"]["vargas"]["D9"]
    for point, key in [("Lagna", "ASC"), ("Moon", "MOON"), ("Venus", "VENUS"),
                       ("Jupiter", "JUPITER"), ("Saturn", "SATURN")]:
        assert ctx.natal_varga_sign(point, 9) == d9[key], point
    assert ctx.natal_varga_sign("Venus", 1) == ctx.natal.sign("Venus")
    assert ctx.natal_house_of("Venus", "Lagna", 9) == 11  # Capricorn from Pisces


def test_check_varga_accepts_d_names_and_refuses_the_rest():
    """D9, "9" and 9 are one varga; D5, D6, D8 are not computable; D2 has no houses."""
    assert check_varga("D9") == check_varga("9") == check_varga(9) == 9
    for bad in (5, 6, 8, "D13", "navamsa"):
        with pytest.raises(VargaNotComputable):
            check_varga(bad)
    assert check_varga(2) == 2
    with pytest.raises(VargaNotComputable, match="two signs only"):
        check_varga(2, houses=True)
    with pytest.raises(VargaNotComputable):
        over_india("nyc_2001").natal_varga_sign("Moon", 5)


def test_dasha_lord_in_house():
    """Venus mahadasha: D1 Cancer (3rd from Taurus, 1st from the Moon); D9
    Capricorn, 11th from the D9 Lagna Pisces. Jupiter antardasha: D9 Taurus,
    10th from the D9 Moon in Leo."""
    ctx = over_india("nyc_2001")
    t = "dasha_lord_in_house"
    assert check(ctx, t, level=1, houses=[3]).held
    assert not check(ctx, t, level=1, houses=[1]).held
    assert check(ctx, t, level=1, houses=[1], **{"from": "Moon"}).held
    out = check(ctx, t, level=1, varga=9, houses=[11])
    assert out.held
    assert "Capricorn in the natal D9, the 11th from the Lagna in Pisces" in out.evidence
    assert check(ctx, t, level=2, varga="D9", houses=[10], **{"from": "Moon"}).held
    assert not check(ctx, t, level=2, varga=9, houses=[1]).held


def test_dasha_lord_rules_house():
    """Venus rules Taurus and Libra: the 1st and 6th from a Taurus Lagna.
    In D9 (Lagna Pisces) Jupiter rules the 1st and 10th. A Ketu period
    (pratyantardasha at the 1947 moment) rules no house."""
    ctx = over_india("nyc_2001")
    t = "dasha_lord_rules_house"
    out = check(ctx, t, level=1, houses=[6])
    assert out.held and "rules the 1st and 6th" in out.evidence
    assert not check(ctx, t, level=1, houses=[2]).held
    assert check(ctx, t, level=2, varga=9, houses=[10]).held
    assert not check(ctx, t, level=2, varga=9, houses=[9]).held
    # Sun pratyantardasha rules Leo, the 2nd from the Cancer Moon.
    assert check(ctx, t, level=3, houses=[2], **{"from": "Moon"}).held
    moment, place = _golden("del_1947")
    birth = EvalContext.at(moment, place, (moment, place))
    out = check(birth, t, level=3, houses=list(range(1, 13)))
    assert not out.held and "rules no house" in out.evidence


def test_dasha_lord_dignity():
    """Venus in Cancer is in an enemy's sign (D1); Venus in Capricorn (D9) a
    friend's. At 1947 Saturn (mahadasha) is in Cancer in D1 but in its own
    Capricorn in D9."""
    ctx = over_india("nyc_2001")
    t = "dasha_lord_dignity"
    assert check(ctx, t, level=1, dignities=["enemy"]).held
    assert check(ctx, t, level=1, varga=9, dignities=["friend"]).held
    assert check(ctx, t, level=2, varga=9, dignities="enemy").held  # Jupiter Taurus
    moment, place = _golden("del_1947")
    birth = EvalContext.at(moment, place, (moment, place))
    assert not check(birth, t, level=1, dignities=["own"]).held
    assert check(birth, t, level=1, varga=9, dignities=["own"]).held
    with pytest.raises(ValidationError, match="moolatrikona"):
        check(ctx, t, varga=9, dignities=["moolatrikona"])


@pytest.mark.parametrize("name", ["dasha_lord_in_house", "dasha_lord_rules_house",
                                  "dasha_lord_dignity"])
@pytest.mark.parametrize("varga", [2, 5, 6, 8, "D5"])
def test_dasha_predicates_refuse_vargas_they_cannot_compute(name, varga):
    """D5, D6, D8 are not computable; D2 has no houses or dignities."""
    params = {"varga": varga}
    params.update({"dignities": ["own"]} if name == "dasha_lord_dignity" else
                  {"houses": [1]})
    with pytest.raises(ValidationError):
        check(over_india("nyc_2001"), name, **params)


def test_dasha_lord_counting_origin_is_lagna_or_moon():
    """from: Sun is refused; the Lagna needs a natal place, the Moon does not."""
    with pytest.raises(ValidationError, match="Lagna or the Moon"):
        check(over_india("nyc_2001"), "dasha_lord_in_house", houses=[1],
              **{"from": "Sun"})
    spec = PREDICATES["dasha_lord_in_house"]
    lagna = spec.params.model_validate({"houses": [1]})
    moon = spec.params.model_validate({"houses": [1], "from": "Moon"})
    assert spec.inputs(lagna) == {"natal", "natal_place"}
    assert spec.inputs(moon) == {"natal"}


def test_transit_aspects_natal():
    """2001 Saturn in Taurus casts its 3rd aspect on the natal Moon (Cancer);
    2001 Jupiter in Gemini its 5th on natal Jupiter (Libra). 2001 Venus in
    Cancer shares the natal Sun's sign: a conjunction, not an aspect."""
    ctx = over_india("nyc_2001")
    t = "transit_aspects_natal"
    out = check(ctx, t, planet="Saturn", natal_point="Moon")
    assert out.held and "the 3rd sign from it" in out.evidence
    assert not check(ctx, t, planet="Saturn", natal_point="Moon", aspects=[10]).held
    assert check(ctx, t, planet="Jupiter", natal_point="Jupiter", aspects=5).held
    assert not check(ctx, t, planet="Venus", natal_point="Sun").held
    with pytest.raises(ValidationError, match="Mars casts only"):
        check(ctx, t, planet="Mars", natal_point="Moon", aspects=[5])


def test_transit_in_house_from_natal_over_vargas():
    """2001 Saturn: Taurus in D1, Cancer in D9. Natal D9 Lagna Pisces, so the
    D1 transit is 3rd over the D9 Lagna and the D9 transit is 5th."""
    ctx = over_india("nyc_2001")
    t = "transit_in_house_from_natal"
    assert check(ctx, t, planet="Saturn", houses=[3], varga=9).held
    out = check(ctx, t, planet="Saturn", houses=[5], varga=9, transit_varga=9)
    assert out.held and "Cancer in D9" in out.evidence
    assert not check(ctx, t, planet="Saturn", houses=[3], varga=9, transit_varga=9).held
    with pytest.raises(ValidationError, match="transit_varga"):
        check(ctx, t, planet="Saturn", houses=[3], transit_varga=9)
    for bad in (2, 5, 6, 8):
        with pytest.raises(ValidationError):
            check(ctx, t, planet="Saturn", houses=[3], varga=bad)


def test_transit_in_house_defaults_are_unchanged():
    """varga and transit_varga default to 1: same result, words and label."""
    ctx = over_india("ktm_1990")
    t = "transit_in_house_from_natal"
    for kw in ({"from": "Lagna"}, {"from": "Moon"}):
        plain = check(ctx, t, planet="Saturn", houses=[9], **kw)
        explicit = check(ctx, t, planet="Saturn", houses=[9], varga=1,
                         transit_varga=1, **kw)
        assert plain == explicit
    assert check(ctx, t, planet="Saturn", houses=[9]).evidence == (
        "transiting Saturn is in Capricorn 1.5 deg, the 9th from the natal "
        "Lagna in Taurus"
    )
    params = PREDICATES[t].params.model_validate({"planet": "Saturn", "houses": [9]})
    assert params.label() == "planet=Saturn, houses=[9]"


def test_new_predicates_name_a_catalogue_id():
    """Each new or widened predicate's docstring names a catalogued method."""
    import re

    from vedic_astrology_core.mundane.catalogue import load_catalogue

    ids = set(load_catalogue().methods)
    for name in NEW + ("transit_in_house_from_natal",):
        named = set(re.findall(r"``([a-z]+\.[a-z0-9_]+)``", PREDICATES[name].doc))
        assert named and named <= ids, (name, named - ids)


def test_rule_with_new_predicates_validates_and_fires():
    """A rule using the new predicates validates and its reference case fires."""
    rule = Rule.model_validate(
        {
            "id": "test.wp52",
            "name": "WP-52 smoke",
            "domain": "mundane",
            "tier": "experimental",
            "claim": "c",
            "author": "a",
            "source": {"text": "test"},
            "conditions": {
                "all": [
                    {"dasha_lord_in_house": {"varga": 9, "houses": [11]}},
                    {"transit_aspects_natal": {"planet": "Saturn",
                                               "natal_point": "Moon"}},
                ]
            },
            "reference_cases": [
                {
                    "moment": "2001-09-11T12:46:00Z",
                    "natal": {
                        "moment": "1947-08-14T18:30:00Z",
                        "place": {"lat": 28.6139, "lon": 77.209,
                                  "tz": "Asia/Kolkata"},
                    },
                    "expect": "fires",
                    "note": "Venus D9 11th; Saturn 3rd aspect on the Moon",
                }
            ],
        }
    )
    from vedic_astrology_core.rules import run_reference_cases

    (result,) = run_reference_cases(rule)
    assert result.passed, result.error
