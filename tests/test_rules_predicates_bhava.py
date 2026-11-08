"""House lords, malefics, elements, the lunar calendar and cycles.

Natal checks use India's independence chart (15 August 1947, 00:00 IST,
New Delhi): Taurus Lagna with the Sun, Moon, Mercury, Venus and Saturn in
Cancer (the 3rd), Rahu in the 1st and Ketu in the 7th.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from vedic_astrology_core.rules import EvalContext, Location, check
from vedic_astrology_core.rules.engine import rule_inputs
from vedic_astrology_core.rules.schema import Rule

DELHI = Location(28.61, 77.21, "Asia/Kolkata")
INDIA = (datetime(1947, 8, 14, 18, 30, tzinfo=timezone.utc), DELHI)


def at(y, mo, d, h=0, place=None, natal=None):
    """Return a context at a UTC instant."""
    return EvalContext.at(datetime(y, mo, d, h, tzinfo=timezone.utc), place, natal)


def test_month_paksha_and_the_2023_adhika():
    """Adhika Shravana 2023 (18 July - 16 August); Ashadha shukla 10 July 2024."""
    assert check(at(2023, 8, 1), "month_paksha", months=["Shravana"]).held
    assert check(at(2023, 8, 1), "month_paksha", months=["Shravana"], adhika=True).held
    assert not check(
        at(2023, 8, 1), "month_paksha", months=["Shravana"], adhika=False
    ).held
    out = check(at(2024, 7, 10), "month_paksha", months=["Ashadha"], paksha="shukla")
    assert out.held and "tithi 4" in out.evidence
    assert not check(
        at(2024, 7, 10), "month_paksha", months=["Ashadha"], paksha="krishna"
    ).held
    with pytest.raises(ValidationError, match="unknown lunar month"):
        check(at(2024, 7, 10), "month_paksha", months=["Ashad"])


def test_nakshatra_on_tithi():
    """10 July 2024: the Moon in Magha on Ashadha shukla 4."""
    ok = check(
        at(2024, 7, 10),
        "nakshatra_on_tithi",
        nakshatras=["Magha"],
        tithis=[4],
        months=["Ashadha"],
    )
    assert ok.held and "Magha on tithi 4 of Ashadha" in ok.evidence
    assert not check(
        at(2024, 7, 10), "nakshatra_on_tithi", nakshatras=["Magha"], tithis=[5]
    ).held
    assert not check(
        at(2024, 7, 10),
        "nakshatra_on_tithi",
        nakshatras=["Magha"],
        tithis=[4],
        months=["Shravana"],
    ).held


def test_lord_of_house_in_on_the_india_chart():
    """Taurus Lagna: the 4th lord (Sun) and the 1st lord (Venus) are in the 3rd."""
    ctx = at(2024, 1, 1, natal=INDIA)
    out = check(ctx, "lord_of_house_in", house=4, houses=[3], chart="natal")
    assert out.held and "4th lord from the natal Lagna is Sun" in out.evidence
    assert check(ctx, "lord_of_house_in", house=1, houses=[3], chart="natal").held
    assert not check(ctx, "lord_of_house_in", house=4, houses=[12], chart="natal").held
    # counted from the natal Moon (Cancer): the 4th lord is Venus, in the 1st
    assert check(
        ctx, "lord_of_house_in", house=4, houses=[1], chart="natal", **{"from": "Moon"}
    ).held


def test_malefic_in_house_on_the_india_chart():
    """Sun and Saturn in the 3rd; Rahu in the 1st; Ketu in the 7th."""
    ctx = at(2024, 1, 1, natal=INDIA)
    out = check(ctx, "malefic_in_house", houses=[3], count_gte=2, chart="natal")
    assert out.held and "Sun, Saturn" in out.evidence
    assert check(
        ctx, "malefic_in_house", houses=[1, 7], count_gte=2, chart="natal"
    ).held
    assert not check(ctx, "malefic_in_house", houses=[6], chart="natal").held


def test_lords_conjoined_on_the_india_chart():
    """Lords of the 1st (Venus) and 4th (Sun) share Cancer, the 3rd."""
    ctx = at(2024, 1, 1, natal=INDIA)
    out = check(ctx, "lords_conjoined", houses=[1, 4], chart="natal")
    assert out.held and "together in the 3rd" in out.evidence
    assert check(
        ctx, "lords_conjoined", houses=[1, 4], in_houses=[3], chart="natal"
    ).held
    assert not check(
        ctx, "lords_conjoined", houses=[1, 4], in_houses=[4], chart="natal"
    ).held
    # 7th lord Mars (Gemini) is not with the 1st lord
    assert not check(ctx, "lords_conjoined", houses=[1, 7], chart="natal").held


def test_lagna_based_predicates_declare_their_inputs():
    """chart: now needs a place; chart: natal needs a natal with a place."""
    rule = Rule.model_validate(
        {
            "id": "t.lords",
            "name": "n",
            "domain": "mundane",
            "claim": "c",
            "source": {"text": "BPHS"},
            "author": "a",
            "tier": "experimental",
            "conditions": {
                "all": [
                    {"lords_conjoined": {"houses": [1, 6]}},
                    {"malefic_in_house": {"houses": [6], "chart": "natal"}},
                ]
            },
            "reference_cases": [
                {"moment": "2000-01-01T00:00:00Z", "expect": "fires", "note": "n"}
            ],
        }
    )
    assert rule_inputs(rule) == {"place", "natal", "natal_place"}


def test_afflicted_element_on_the_1962_cluster():
    """5 February 1962: Sun, Mars and Saturn (with Ketu) in earthy Capricorn."""
    out = check(at(1962, 2, 5), "afflicted_element", element="earth", count_gte=3)
    assert out.held and "Mars in Capricorn" in out.evidence
    assert not check(at(1962, 2, 5), "afflicted_element", element="fire").held


def test_cycle_resonance():
    """Sixty years after the 1961 Jupiter-Saturn conjunction, within 1 year."""
    ref = "1961-02-18T00:00:00Z"
    out = check(
        at(2021, 3, 1),
        "cycle_resonance",
        reference=ref,
        period_years=60,
        tolerance_years=1,
    )
    assert out.held and "60.0 years" in out.evidence
    assert not check(
        at(1991, 3, 1),
        "cycle_resonance",
        reference=ref,
        period_years=60,
        tolerance_years=3,
    ).held
    # before the reference counts too
    assert check(
        at(1901, 3, 1),
        "cycle_resonance",
        reference=ref,
        period_years=60,
        tolerance_years=1,
    ).held
    with pytest.raises(ValidationError, match="less than half"):
        check(
            at(2021, 3, 1),
            "cycle_resonance",
            reference=ref,
            period_years=10,
            tolerance_years=5,
        )


def test_conjunction_or_mutual_aspect():
    """Same sign (1962), mutual 7th (Sept 2010), one-way 3rd (July 2000)."""
    assert check(
        at(1962, 2, 5),
        "conjunction_or_mutual_aspect",
        planet="Mars",
        others=["Saturn"],
    ).held
    out = check(
        at(2010, 9, 15),
        "conjunction_or_mutual_aspect",
        planet="Jupiter",
        others=["Saturn"],
    )
    assert out.held and "aspect each other" in out.evidence
    # Mars in the 3rd from Saturn: Saturn aspects Mars, Mars does not return it
    assert not check(
        at(2000, 7, 29),
        "conjunction_or_mutual_aspect",
        planet="Mars",
        others=["Saturn"],
    ).held
    # with an orb the conjunction is by degree, not by sign
    assert not check(
        at(1962, 2, 5),
        "conjunction_or_mutual_aspect",
        planet="Mars",
        others=["Saturn"],
        orb=0.5,
    ).held
