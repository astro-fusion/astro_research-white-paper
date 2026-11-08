"""Migrate combinations/catalog/*.yaml and src detect_yogas into rules/."""

from datetime import datetime, timedelta, timezone

from common import REPO, daily, make_cases, moments, write_rule

AUTHOR_CATALOG = "astro-research combinations catalog (migrated 2026-11-08)"
FIRE = ["Aries", "Leo", "Sagittarius"]

CATALOG = [
    # (domain, slug, old name, claim, source, conditions, notes)
    (
        "financial",
        "venus_retrograde_reversal",
        "Venus-Retrograde-Reversal",
        "Venus retrograde signals a reversal in value expectations (gold).",
        {
            "text": "Financial Astrology Tradition",
            "note": "No classical text or chapter; carried over from the old catalog.",
        },
        {"retrograde": {"planet": "Venus"}},
        {},
    ),
    (
        "financial",
        "jupiter_retrograde_contraction",
        "Jupiter-Retrograde-Contraction",
        "Jupiter retrograde signals contraction or a pause in market expansion.",
        {
            "text": "Financial Astrology Tradition",
            "note": "No classical text or chapter; carried over from the old catalog.",
        },
        {"retrograde": {"planet": "Jupiter"}},
        {},
    ),
    (
        "financial",
        "shukra_guru_wealth",
        "Shukra-Guru-Wealth",
        "A Venus-Jupiter conjunction within 8 degrees favours wealth (gold up).",
        {
            "text": "Classical Wealth Yoga",
            "note": (
                "Named only generically in the old catalog; no text, chapter or verse."
            ),
        },
        {"conjunct_within": {"planets": ["Venus", "Jupiter"], "orb": 8}},
        {},
    ),
    (
        "financial",
        "venus_own_sign",
        "Venus-Own-Sign",
        "Venus in its own signs (Taurus, Libra) supports value and luxury assets.",
        {
            "text": "Brihat Parashara Hora Shastra",
            "note": (
                "The old catalog cites BPHS without a chapter; BPHS gives the sign"
                " rulerships, not the market claim."
            ),
        },
        {"dignity_in": {"planet": "Venus", "dignities": ["own"]}},
        {
            "conversion": (
                "INSIGN Venus [Taurus, Libra] became dignity_in own (same signs)."
            )
        },
    ),
    (
        "seismic",
        "mangal_ketu_primary",
        "Mangal-Ketu-Primary",
        (
            "A Mars-Ketu conjunction within 13 degrees releases sudden martial energy"
            " (earthquakes)."
        ),
        {
            "text": "Brihat Samhita",
            "chapter": "17",
            "note": (
                "Carried over from the old catalog. Brihat Samhita Ch. 17 is on"
                " planetary war (graha yuddha); earthquakes are Ch. 32. The citation"
                " does not support the claim, so the rule stays experimental."
            ),
        },
        {"conjunct_within": {"planets": ["Mars", "Ketu"], "orb": 13}},
        {},
    ),
    (
        "seismic",
        "mangal_ketu_fire_sign",
        "Mangal-Ketu-Fire-Sign",
        "A Mars-Ketu conjunction is amplified when Mars is in a fire sign.",
        {
            "text": "Brihat Samhita",
            "chapter": "17",
            "note": (
                "Old catalog: 'Brihat Samhita + Elemental Amplification'. Not verified"
                " against the text; see mangal_ketu_primary."
            ),
        },
        {
            "all": [
                {"conjunct_within": {"planets": ["Mars", "Ketu"], "orb": 13}},
                {"in_sign": {"planet": "Mars", "signs": FIRE}},
            ]
        },
        {},
    ),
    (
        "seismic",
        "mangal_shani_malefic",
        "Mangal-Shani-Malefic",
        "A Mars-Saturn conjunction within 15 degrees is associated with earthquakes.",
        {
            "text": "Phaladeepika",
            "chapter": "3",
            "note": "Carried over from the old catalog; not verified against the text.",
        },
        {"conjunct_within": {"planets": ["Mars", "Saturn"], "orb": 15}},
        {},
    ),
    (
        "seismic",
        "mangal_8th_aspect_ketu",
        "Mangal-8th-Aspect-Ketu",
        "Mars casting its special 8th aspect on Ketu triggers seismic stress.",
        {
            "text": "Brihat Parashara Hora Shastra",
            "note": (
                "BPHS gives Mars's 8th aspect, not the seismic claim; no chapter in the"
                " old catalog."
            ),
        },
        {"graha_drishti": {"planet": "Mars", "target": "Ketu", "aspects": [8]}},
        {
            "conversion": (
                "Was degree-based (Mars + 210 deg within 15 deg of Ketu). Now"
                " whole-sign graha drishti: Ketu in the 8th sign from Mars."
            )
        },
    ),
    (
        "seismic",
        "shani_10th_aspect_mars",
        "Shani-10th-Aspect-Mars",
        "Saturn casting its special 10th aspect on Mars triggers seismic stress.",
        {
            "text": "Brihat Parashara Hora Shastra",
            "note": (
                "BPHS gives Saturn's 10th aspect, not the seismic claim; no chapter in"
                " the old catalog."
            ),
        },
        {"graha_drishti": {"planet": "Saturn", "target": "Mars", "aspects": [10]}},
        {
            "conversion": (
                "Was degree-based (Saturn + 270 deg within 15 deg of Mars). Now"
                " whole-sign graha drishti: Mars in the 10th sign from Saturn."
            )
        },
    ),
    (
        "seismic",
        "shrapit_yoga",
        "Shrapit-Yoga",
        (
            "A Saturn-Rahu conjunction (Shrapit yoga) within 12 degrees is associated"
            " with earthquakes."
        ),
        {
            "text": "Classical Tradition",
            "note": "Shrapit yoga is a modern name; no classical chapter.",
        },
        {"conjunct_within": {"planets": ["Saturn", "Rahu"], "orb": 12}},
        {},
    ),
    (
        "seismic",
        "mars_retrograde_tension",
        "Mars-Retrograde-Tension",
        "Mars retrograde builds internal crustal tension.",
        {
            "text": "Modern Mundane Astrology",
            "note": "Modern claim; no classical chapter.",
        },
        {"retrograde": {"planet": "Mars"}},
        {},
    ),
    (
        "seismic",
        "saturn_stationary",
        "Saturn-Stationary",
        (
            "Saturn near its station (moving under 0.05 deg/day) is associated with"
            " earthquakes."
        ),
        {
            "text": "Modern Mundane Astrology",
            "note": "Modern claim; no classical chapter.",
        },
        {"planet_speed_below": {"planet": "Saturn", "speed": 0.05}},
        {
            "conversion": (
                "STATIONARY (|speed| <= 0.05) became planet_speed_below (|speed| <"
                " 0.05)."
            )
        },
    ),
]


def catalog():
    """Write the migrated combinations catalog rules."""
    for domain, slug, name, claim, source, cond, notes in CATALOG:
        rule = {
            "id": f"{domain}.{slug}",
            "name": name,
            "domain": domain,
            "claim": claim,
            "source": source,
            "author": AUTHOR_CATALOG,
            "tier": "experimental",
            "conditions": cond,
        }
        if domain == "financial":
            rule["expected_effect"] = {"series": "gold_usd", "description": claim}
        else:
            rule["expected_effect"] = {"event": "earthquake", "direction": "increase"}
        rule["reference_cases"] = make_cases(rule, daily("2000-01-01", "2040-12-31"))
        stem = domain if domain == "financial" else "seismic"
        n = {
            "migrated_from": (
                f"libs/vedic_astrology_core/combinations/catalog/{stem}_yogas.yaml"
                f" ({name})"
            )
        }
        n.update(notes)
        rule["notes"] = n
        write_rule(REPO / "rules" / domain / f"{slug}.yaml", rule, "../schema.json")
        print("wrote", rule["id"], [c["expect"] for c in rule["reference_cases"]])


BPHS_GK = {
    "text": "Brihat Parashara Hora Shastra",
    "chapter": "36",
    "verse": "3-4",
    "edition": "R. Santhanam tr., Ranjan Publications",
    "note": (
        "Gaja Kesari is the first yoga of the chapter on various yogas (Nana Yoga)."
        " Chapter and verse numbering differ between editions; check against yours."
    ),
}
KTM = {"lat": 27.7172, "lon": 85.324, "tz": "Asia/Kathmandu"}


def general():
    """Write the general yogas migrated from the src detector."""
    # 1. The src detector's definition, corrected to count by sign.
    rule = {
        "id": "general.gaja_kesari.moon_kendra",
        "name": "Gaja Kesari Yoga (Moon kendra form)",
        "domain": "general",
        "claim": (
            "Jupiter in a kendra (1, 4, 7, 10) counted by sign from the Moon gives"
            " fame, wealth and lasting reputation."
        ),
        "source": BPHS_GK,
        "author": "astro-research (from the retired engine's detect_yogas)",
        "tier": "classical",
        "conditions": {"in_kendra_from": {"planet": "Jupiter", "from": "Moon"}},
    }
    cases = make_cases(rule, daily("2000-01-01", "2030-12-31"))
    # Regression for review S3-3: a kendra by sign that the degree test missed.
    from vedic_astrology_core.rules.context import EvalContext
    from vedic_astrology_core.rules.predicates import check

    for t in moments(
        datetime(2014, 1, 1, tzinfo=timezone.utc),
        datetime(2030, 1, 1, tzinfo=timezone.utc),
        timedelta(hours=6),
    ):
        c = EvalContext.at(t)
        m, j = c.sky.lon("Moon"), c.sky.lon("Jupiter")
        diff = (j - m) % 360.0
        by_sign = (int(j // 30) - int(m // 30)) % 12
        if by_sign in (3, 9) and int(diff // 30) not in (0, 3, 6, 9):
            out = check(c, "in_kendra_from", planet="Jupiter", **{"from": "Moon"})
            assert out.held
            cases.append(
                {
                    "moment": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "expect": "fires",
                    "note": (
                        f"Review S3-3 regression: {out.evidence}. The degree difference"
                        f" is {diff:.1f}, which the old src detector (diff // 30) did"
                        " not count as a kendra."
                    ),
                    "verified_with": (
                        "astro-research engine 2026-11-08 (Lahiri, mean node); not yet"
                        " checked in JHora"
                    ),
                }
            )
            break
    rule["reference_cases"] = cases
    rule["notes"] = {
        "simplified": (
            "This is the common short form. BPHS also requires a benefic to join or"
            " aspect Jupiter and Jupiter to be free of debilitation, combustion and an"
            " enemy's sign; see general.gaja_kesari.classical."
        ),
        "fixes": (
            "the retired engine's detect_yogas counted int((Jupiter - Moon)"
            " // 30), a degree difference, so Moon Aries 29 with Jupiter Cancer 28 (89"
            " deg) was missed (review S3-3). Counting is by sign here."
        ),
    }
    write_rule(
        REPO / "rules" / "general" / "gaja_kesari.moon_kendra.yaml",
        rule,
        "../schema.json",
    )
    print("wrote", rule["id"], [c["expect"] for c in rule["reference_cases"]])

    # 2. The full BPHS definition.
    benefic_touch = {
        "any": [
            {"graha_drishti": {"planet": "Mercury", "target": "Jupiter"}},
            {"graha_drishti": {"planet": "Venus", "target": "Jupiter"}},
            {"in_house_from": {"planet": "Mercury", "from": "Jupiter", "houses": [1]}},
            {"in_house_from": {"planet": "Venus", "from": "Jupiter", "houses": [1]}},
        ]
    }
    rule = {
        "id": "general.gaja_kesari.classical",
        "name": "Gaja Kesari Yoga (BPHS definition)",
        "domain": "general",
        "claim": (
            "Jupiter in a kendra from the Lagna or the Moon, joined or aspected by a"
            " benefic, and not debilitated, combust or in an enemy's sign, gives a"
            " splendid, wealthy and lasting reputation."
        ),
        "source": BPHS_GK,
        "author": "astro-research",
        "tier": "classical",
        "conditions": {
            "all": [
                {
                    "any": [
                        {"in_kendra_from": {"planet": "Jupiter", "from": "Moon"}},
                        {"in_kendra_from": {"planet": "Jupiter", "from": "Lagna"}},
                    ]
                },
                benefic_touch,
                {
                    "not": {
                        "dignity_in": {
                            "planet": "Jupiter",
                            "dignities": ["debilitation", "enemy"],
                        }
                    }
                },
                {"not": {"combust": {"planet": "Jupiter"}}},
            ]
        },
    }
    cands = moments(
        datetime(2000, 1, 1, tzinfo=timezone.utc),
        datetime(2030, 1, 1, tzinfo=timezone.utc),
        timedelta(hours=7),
    )
    rule["reference_cases"] = make_cases(rule, cands, place=KTM)
    rule["notes"] = {
        "benefics": (
            "Mercury and Venus are taken as the benefics. The Moon (a benefic when"
            " waxing) is not included yet; a waxing-Moon condition can be added with"
            " moon_phase."
        ),
        "enemy": (
            "'Enemy sign' uses natural friendship (naisargika maitri) to the sign lord:"
            " Jupiter's enemies are Mercury and Venus, so Gemini, Virgo, Taurus and"
            " Libra."
        ),
    }
    write_rule(
        REPO / "rules" / "general" / "gaja_kesari.classical.yaml",
        rule,
        "../schema.json",
    )
    print("wrote", rule["id"], [c["expect"] for c in rule["reference_cases"]])

    # 3. Budha-Aditya.
    rule = {
        "id": "general.budha_aditya",
        "name": "Budha-Aditya Yoga",
        "domain": "general",
        "claim": "The Sun and Mercury in the same sign give intelligence and skill.",
        "source": {
            "text": "Modern Jyotish usage",
            "note": (
                "The name is common in modern practice; no BPHS chapter defines it as a"
                " yoga, so the rule is experimental."
            ),
        },
        "author": "astro-research (from the retired engine's detect_yogas)",
        "tier": "experimental",
        "conditions": {
            "in_house_from": {"planet": "Mercury", "from": "Sun", "houses": [1]}
        },
    }
    rule["reference_cases"] = make_cases(rule, daily("2000-01-01", "2030-12-31"))
    rule["notes"] = {
        "definition": (
            "Same sign, as in detect_yogas; no orb and no combustion test (Mercury is"
            " often combust when it forms this yoga)."
        )
    }
    write_rule(REPO / "rules" / "general" / "budha_aditya.yaml", rule, "../schema.json")
    print("wrote", rule["id"], [c["expect"] for c in rule["reference_cases"]])


if __name__ == "__main__":
    catalog()
    general()
