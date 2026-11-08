"""Convert the 67 AstroFusion mundane draft rules into rules/mundane/experimental/."""

import glob
import os
from datetime import datetime, timedelta, timezone

import yaml

from common import REPO, daily, make_cases, moments, write_rule
from vedic_astrology_core.rules.predicates import PREDICATES

# Draft YAML files from the AstroFusion open export (not in this repository).
DRAFTS = os.environ.get("MUNDANE_DRAFTS", "mundane-open-export/rules_draft")
AUTHOR = "AstroFusion mundane rule registry (open export 2026-11-08)"
DELHI = {"lat": 28.6139, "lon": 77.209, "tz": "Asia/Kolkata"}
INDIA_1947 = {
    "moment": "1947-08-15T00:00:00+05:30",
    "place": DELHI,
    "label": "India independence chart (Delhi, 00:00 IST), as used by B.V. Raman",
}
NAKS = ["Revati", "Ashwini", "Bharani", "Ardra", "Punarvasu", "Pushya", "Ashlesha"]
DUAL = ["Gemini", "Virgo", "Sagittarius", "Pisces"]


def axis(a, b):
    """Return a condition: Jupiter and Saturn both on the a-b axis."""
    return {
        "all": [
            {"in_sign": {"planet": "Jupiter", "signs": [a, b]}},
            {"in_sign": {"planet": "Saturn", "signs": [a, b]}},
        ]
    }


def hard_pair(a, b, orb=6):
    """Return a condition: a hard aspect between two planets."""
    return {
        "any": [
            {"conjunct_within": {"planets": [a, b], "orb": orb}},
            {"separation_within": {"planets": [a, b], "angle": 90, "orb": orb}},
            {"separation_within": {"planets": [a, b], "angle": 180, "orb": orb}},
        ]
    }


SAME_SIGN = (
    "The draft gives no orb, so the conjunction is read as the same sign (whole-sign"
    " yuti)."
)

# id -> (conditions, kind of search, conversion note)
CONVERTED = {
    "mundane.ch10.northern_border_sensitivity_tripod": (
        {
            "all": [
                {
                    "any": [
                        {"in_nakshatra": {"planet": p, "nakshatras": NAKS}}
                        for p in ("Saturn", "Rahu", "Ketu")
                    ]
                },
                {
                    "in_sign": {
                        "planet": "Mars",
                        "signs": ["Aries", "Leo", "Virgo", "Sagittarius", "Pisces"],
                    }
                },
            ]
        },
        "daily",
        "Sign numbers 1, 5, 6, 9, 12 are Aries, Leo, Virgo, Sagittarius, Pisces.",
    ),
    "mundane.ch10.ketu_ninth_legal_commercial_friction": (
        {
            "transit_in_house_from_natal": {
                "planet": "Ketu",
                "from": "Lagna",
                "houses": [9],
            }
        },
        "natal",
        "The national chart is supplied at evaluation time (natal).",
    ),
    "mundane.ch6.jupiter_saturn_opposition_axis": (
        {
            "all": [
                {
                    "separation_within": {
                        "planets": ["Jupiter", "Saturn"],
                        "angle": 180,
                        "orb": 12,
                    }
                },
                {
                    "any": [
                        axis("Gemini", "Sagittarius"),
                        axis("Aries", "Libra"),
                        axis("Cancer", "Capricorn"),
                    ]
                },
            ]
        },
        "daily",
        (
            "Axis sign pairs [3, 9], [1, 7], [4, 10] are Gemini-Sagittarius,"
            " Aries-Libra, Cancer-Capricorn; both planets must be on the axis."
        ),
    ),
    "mundane.ch6.classical_parasara_trigger": (
        {
            "all": [
                {"in_nakshatra": {"planet": "Saturn", "nakshatras": ["Krittika"]}},
                {"in_nakshatra": {"planet": "Jupiter", "nakshatras": ["Vishakha"]}},
            ]
        },
        "daily",
        "",
    ),
    "mundane.ch6.classical_devala_dual_signs": (
        {
            "all": [
                {"in_sign": {"planet": "Jupiter", "signs": DUAL}},
                {"in_sign": {"planet": "Saturn", "signs": DUAL}},
            ]
        },
        "daily",
        "Sign numbers 3, 6, 9, 12 are the dual signs.",
    ),
    "mundane.ch6.classical_varahamihira_venus_jupiter": (
        {
            "separation_within": {
                "planets": ["Venus", "Jupiter"],
                "angle": 180,
                "orb": 10,
            }
        },
        "daily",
        "",
    ),
    "mundane.ch6.coalition_viability_index": (
        {
            "any": [
                {"in_sign": {"planet": "Saturn", "signs": ["Cancer"]}},
                {"in_sign": {"planet": "Jupiter", "signs": ["Sagittarius"]}},
                {"in_sign": {"planet": "Saturn", "signs": ["Sagittarius"]}},
            ]
        },
        "daily",
        "Evaluate at the moment of government formation.",
    ),
    "mundane.ch7.himalaya_jupiter_ketu_cancer_sensitivity": (
        {
            "all": [
                {"in_sign": {"planet": "Jupiter", "signs": ["Cancer"]}},
                {"in_sign": {"planet": "Ketu", "signs": ["Cancer"]}},
                {"conjunct_within": {"planets": ["Jupiter", "Ketu"], "orb": 10}},
            ]
        },
        "daily",
        "",
    ),
    "mundane.ch7.oath_aquarius_baseline_penalty": (
        {"in_sign": {"planet": "Lagna", "signs": ["Aquarius"]}},
        "lagna",
        "Evaluate at the oath moment and place.",
    ),
    "mundane.ch4.sun_lagna_moon_rahu_third_house": (
        {
            "all": [
                {"in_house_from": {"planet": "Moon", "from": "Sun", "houses": [3]}},
                {"in_house_from": {"planet": "Rahu", "from": "Sun", "houses": [3]}},
                {"conjunct_within": {"planets": ["Moon", "Rahu"], "orb": 8}},
            ]
        },
        "hourly",
        "Sun-Lagna: houses counted from the Sun's sign.",
    ),
    "mundane.core.r026_3rd_house_travel_illusion_affliction": (
        {
            "all": [
                {"in_house_from": {"planet": "Moon", "from": "Rahu", "houses": [1]}},
                {"in_house_from": {"planet": "Moon", "from": "Sun", "houses": [3]}},
            ]
        },
        "hourly",
        SAME_SIGN + " Sun-Lagna: houses counted from the Sun's sign.",
    ),
    "mundane.core.r005_geo_magnetic_astrological_stability_index": (
        {
            "at_least": {
                "n": 2,
                "of": [
                    hard_pair("Saturn", "Jupiter"),
                    hard_pair("Jupiter", "Mars"),
                    hard_pair("Saturn", "Mars"),
                ],
            }
        },
        "daily",
        "Hard aspects 0, 90, 180 deg within 6 deg; at least two of the three pairs.",
    ),
    "mundane.core.r008_mundane_house_domain_mapping": (
        {
            "any": [
                {
                    "transit_in_house_from_natal": {
                        "planet": p,
                        "from": "Lagna",
                        "houses": [6, 8, 10, 12],
                    }
                }
                for p in ("Sun", "Mars", "Saturn", "Rahu", "Ketu")
            ]
        },
        "natal",
        "'Malefic' is read as the natural malefics Sun, Mars, Saturn, Rahu and Ketu.",
    ),
    "mundane.ch9.capital_saturn_transit_clock": (
        {
            "transit_in_house_from_natal": {
                "planet": "Saturn",
                "from": "Lagna",
                "houses": [1, 4, 6, 7, 8, 10],
            }
        },
        "natal",
        "The capital's chart is supplied at evaluation time (natal).",
    ),
    "mundane.core.r011_agastya_solar_ingress_atmospheric_optics": (
        {
            "longitude_between": {
                "planet": "Sun",
                "start": 141.5,
                "end": 144.5,
                "note": "sidereal 143 +/- 1.5 deg",
            }
        },
        "daily",
        "Sun at sidereal 143 deg within 1.5 deg.",
    ),
    "mundane.ch5.eclipse_lunar_baseline_window": (
        {"eclipse_in_sign": {"kind": "lunar", "days_before": 30, "days_after": 30}},
        "daily",
        "Any lunar eclipse within 30 days either side.",
    ),
    "mundane.ch5.eclipse_territorial_mapping": (
        {
            "any": [
                {
                    "eclipse_in_sign": {
                        "kind": "any",
                        "signs": ["Leo", "Aquarius", "Cancer"],
                        "days_before": 1,
                        "days_after": 1,
                    }
                },
                {
                    "eclipse_in_sign": {
                        "kind": "any",
                        "nakshatras": ["Shravana"],
                        "days_before": 1,
                        "days_after": 1,
                    }
                },
            ]
        },
        "eclipse",
        (
            "The territorial flags are annotations, kept in notes.flags; the condition"
            " is the eclipse placement within a day of the moment."
        ),
    ),
    "mundane.ch8.center_state_friction_index": (
        {
            "all": [
                {"in_house_from": {"planet": "Mars", "from": "Mercury", "houses": [1]}},
                {"in_house": {"planet": "Mars", "houses": [7]}},
            ]
        },
        "lagna",
        SAME_SIGN + " Evaluate at the capital's inauguration moment and place.",
    ),
}

# Draft predicate names that the vocabulary already covers under another name.
EQUIVALENT = {
    "planet_in_sign": "in_sign",
    "planet_in_sign_in": "in_sign",
    "rising_sign_is": "in_sign (planet: Lagna)",
    "planet_in_nakshatra": "in_nakshatra",
    "planet_in_nakshatra_in": "in_nakshatra",
    "planet_in_house_from": "in_house_from",
    "conjunction_within_orb": "conjunct_within",
    "aspect_within_orb": "separation_within",
    "transit_planet_in_house_from_natal": "transit_in_house_from_natal",
    "opposition_axis_signs": "in_sign on both planets",
    "dasha_lord_is": "dasha_lord_is",
}
OUTER = {"Uranus", "Neptune", "Pluto"}

SPECIAL_REASON = {
    "mundane.core.r009_varsheshvara_annual_cabinet_portfolios": (
        "The rule reads the weekday lord at each solar ingress to assign an annual"
        " 'cabinet' (a lookup table), not a condition that holds at a moment."
    ),
    "mundane.ch8.decadal_mahadasa_era_mapping": (
        "The draft condition (the dasha lord is any of the nine) is always true; the"
        " rule maps eras to dasha lords rather than testing a moment."
    ),
    "mundane.ch10.dvi_dvadasha_axis_detection": (
        "Compares two charts' ascendants (2/12 relation between charts); needs a"
        " two-chart predicate."
    ),
}


def walk_names(node, out):
    """Collect predicate names used anywhere in a condition tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("all", "any", "not"):
                walk_names(v, out)
            else:
                out.append(k)
    elif isinstance(node, list):
        for x in node:
            walk_names(x, out)


def candidates(kind):
    """Return candidate moments for reference cases of a rule kind."""
    if kind in ("daily", "natal"):
        return daily("1950-01-01", "2040-12-31")
    if kind == "hourly":
        s = datetime(2000, 1, 1, tzinfo=timezone.utc)
        return moments(s, s + timedelta(days=3650), timedelta(hours=3))
    if kind == "lagna":
        s = datetime(2000, 1, 1, tzinfo=timezone.utc)
        return moments(s, s + timedelta(days=800), timedelta(minutes=20))
    if kind == "eclipse":
        s = datetime(2017, 8, 15, tzinfo=timezone.utc)
        return moments(s, s + timedelta(days=4000), timedelta(hours=6))
    raise ValueError(kind)


def convert(draft):
    """Convert one AstroFusion draft rule to the rules/ schema."""
    rid = draft["id"]
    cond = draft["conditions"]
    machine = {
        k: v
        for k, v in cond.items()
        if k not in ("original", "original_thresholds", "original_full")
    }
    src = {k: v for k, v in draft["source"].items() if v is not None}
    src["note"] = (
        "Chapter refers to the mundane text synthesis behind the AstroFusion registry "
        "(attributed to B.V. Raman and M.C. Jain plus classical authors); the book "
        "edition is not identified, see the export PROVENANCE."
    )
    rule = {
        "id": rid,
        "name": draft["name"],
        "domain": "mundane",
        "claim": " ".join(str(draft["claim"]).split()),
        "source": src,
        "author": AUTHOR,
        "tier": "experimental",
    }
    notes = {
        "original_condition": cond.get("original"),
        "original_thresholds": cond.get("original_thresholds"),
        "mapping_status": draft["mapping_status"],
        "draft_conditions": machine,
        "event_types": draft.get("event_types"),
        "confidence_in_app": draft.get("confidence_in_app"),
        "severity_in_app": draft.get("severity_in_app"),
        "validation": draft.get("validation"),
    }
    if rid == "mundane.ch5.eclipse_territorial_mapping":
        notes["flags"] = cond.get("original")
    window = draft.get("window")
    if window:
        rule["window"] = {k: v for k, v in window.items() if v is not None}
    if rid in CONVERTED:
        conditions, kind, conv = CONVERTED[rid]
        rule["status"] = "active"
        rule["conditions"] = conditions
        place = DELHI if kind == "lagna" else None
        natal = INDIA_1947 if kind == "natal" else None
        cases = make_cases(rule, candidates(kind), place=place, natal=natal)
        if not cases:
            raise SystemExit(f"no reference case found for {rid}")
        rule["reference_cases"] = cases
        notes["conversion"] = (
            conv + " " if conv else ""
        ) + "Converted by hand from draft_conditions to the astro-rules vocabulary."
        if kind == "natal":
            notes["natal_chart"] = (
                "Reference cases use the India 1947 chart; any national chart can be"
                " given with --natal-moment/--natal-lat/--natal-lon."
            )
    else:
        names = []
        walk_names(machine, names)
        missing = sorted(
            {n for n in names if n not in PREDICATES and n not in EQUIVALENT}
        )
        outer = sorted(
            OUTER
            & set(yaml.safe_dump(machine).replace(":", " ").replace(",", " ").split())
        )
        rule["status"] = "needs_predicates"
        rule["conditions"] = None
        if rid in SPECIAL_REASON:
            reason = SPECIAL_REASON[rid]
        elif draft["mapping_status"] == "descriptive" and not missing:
            reason = (
                "Descriptive in the source registry: it states an interpretation or a"
                " data layer, not a condition on the sky."
            )
        else:
            parts = []
            if missing:
                parts.append(
                    "the vocabulary has no predicate for " + ", ".join(missing)
                )
            if outer:
                parts.append(
                    "it uses "
                    + ", ".join(outer)
                    + (", which is" if len(outer) == 1 else ", which are")
                    + " outside the nine grahas"
                )
            if not parts:
                parts.append(
                    "its parameters refer to charts or quantities the engine does not"
                    " model (see draft_conditions)"
                )
            reason = "Not expressible yet: " + "; ".join(parts) + "."
        notes["needs_predicates"] = reason
        notes["missing_predicates"] = missing
    rule["notes"] = {k: v for k, v in notes.items() if v not in (None, [], {})}
    return rule


def main():
    """Convert every draft and write rules/mundane/experimental/."""
    out = REPO / "rules" / "mundane" / "experimental"
    total = 0
    for f in sorted(glob.glob(DRAFTS + "/*.yaml")):
        for draft in yaml.safe_load(open(f)):
            rule = convert(draft)
            name = rule["id"].removeprefix("mundane.") + ".yaml"
            write_rule(out / name, rule, "../../schema.json")
            total += 1
            print(
                rule["status"],
                rule["id"],
                [c["expect"] for c in rule.get("reference_cases", [])],
            )
    print(total)


if __name__ == "__main__":
    main()
