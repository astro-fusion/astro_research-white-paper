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
