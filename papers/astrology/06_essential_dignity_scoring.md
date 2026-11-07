# ⚖️ White Paper 06: Essential Dignity Scoring Arrays

## Quantised Qualitative Astrological Weights as O(1) Hash Maps

> **Symbol reference**: [SYMBOLOGY.md §II.F](../../SYMBOLOGY.md)
> **Code**: [`src/celestial/dignity_scoring.py`](../../src/celestial/dignity_scoring.py)

---

## Abstract

Essential dignity in classical and Vedic astrology assigns a qualitative status to each planet based on its ecliptic longitude — a positional relationship between the planet and the sign (or exact degree) it inhabits. Converting these qualitative judgments into quantised integer weights creates machine-operable data structures suitable for statistical analysis, ML feature engineering, and multi-chart comparative studies. This white paper documents the complete dignity taxonomy, the hash-map scoring lookup architecture achieving O(1) retrieval, and the normalisation schema for numerical integration with astrophysical datasets.

---

## 1. Essential Dignity Taxonomy

### 1.1 Sign-Based Dignities

| Dignity              | Condition                                         | Weight $w$ | Description                |
| -------------------- | ------------------------------------------------- | ---------- | -------------------------- |
| Domicile (Rulership) | Planet in its own sign                            | +5         | Strongest native placement |
| Exaltation           | Planet in exaltation sign                         | +4         | Highly favoured placement  |
| Triplicity           | Planet rules the triplicity of the sign           | +3         | Moderate strength          |
| Term (Bound)         | Planet rules the term of the current degree       | +2         | Weak specific strength     |
| Face (Decan)         | Planet rules the face/decan of the current degree | +1         | Weakest dignity            |
| Peregrine            | No dignity applies                                | 0          | Neutral; wandering         |
| Detriment            | Opposite sign from domicile                       | −4         | Hostile placement          |
| Fall                 | Opposite sign from exaltation                     | −3         | Debilitated placement      |

### 1.2 Exact-Degree Exaltation Points

The maximum dignity score (+10) is awarded only at the **specific degree** of exaltation:

| Planet    | Exaltation Degree | Exaltation Sign | Full Precision      |
| --------- | ----------------- | --------------- | ------------------- |
| Sun ☉     | 10°               | Aries ♈        | 10°00' Aries        |
| Moon ☽    | 3°                | Taurus ♉       | 3°00' Taurus        |
| Mercury ☿ | 15°               | Virgo ♍        | 15°00' Virgo        |
| Venus ♀   | 27°               | Pisces ♓       | 27°00' Pisces       |
| Mars ♂    | 28°               | Capricorn ♑    | 28°00' Capricorn    |
| Jupiter ♃ | 5°                | Cancer ♋       | 5°00' Cancer        |
| Saturn ♄  | 20°               | Libra ♎        | 20°00' Libra        |
| Rahu ☊    | 20°               | Gemini ♊       | (traditional Vedic) |
| Ketu ☋    | 20°               | Sagittarius ♐  | (traditional Vedic) |

---

## 2. Planetary Rulership Table

### 2.1 Western Traditional (7 Planets)

| Planet  | Domicile 1  | Domicile 2 | Detriment 1 | Detriment 2 |
| ------- | ----------- | ---------- | ----------- | ----------- |
| Sun     | Leo         | —          | Aquarius    | —           |
| Moon    | Cancer      | —          | Capricorn   | —           |
| Mercury | Gemini      | Virgo      | Sagittarius | Pisces      |
| Venus   | Taurus      | Libra      | Scorpio     | Aries       |
| Mars    | Aries       | Scorpio    | Libra       | Taurus      |
| Jupiter | Sagittarius | Pisces     | Gemini      | Virgo       |
| Saturn  | Capricorn   | Aquarius   | Cancer      | Leo         |

### 2.2 Vedic (Jyotish) — Inclusding Rahu/Ketu

| Planet  | Moolatrikona Sign | Moolatrikona Degrees | Own Sign(s)           |
| ------- | ----------------- | -------------------- | --------------------- |
| Sun     | Leo               | 0°–20°               | Leo                   |
| Moon    | Taurus            | 4°–30°               | Cancer                |
| Mars    | Aries             | 0°–12°               | Aries, Scorpio        |
| Mercury | Virgo             | 16°–20°              | Gemini, Virgo         |
| Jupiter | Sagittarius       | 0°–10°               | Sagittarius, Pisces   |
| Venus   | Libra             | 0°–15°               | Taurus, Libra         |
| Saturn  | Aquarius          | 0°–20°               | Capricorn, Aquarius   |
| Rahu    | —                 | —                    | Virgo (some schools)  |
| Ketu    | —                 | —                    | Pisces (some schools) |

---

## 3. Hash-Map Implementation Architecture

### 3.1 Data Structure

The dignity scorer uses a nested `dict` (Python) for O(1) lookup, keyed on `(planet, sign)` pairs:

```python
# src/celestial/dignity_scoring.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

# Dignity score weights (see Paper §1.1)
W_DOMICILE    =  5
W_EXALTATION  =  4
W_EXALT_EXACT = 10
W_TRIPLICITY  =  3
W_TERM        =  2
W_FACE        =  1
W_PEREGRINE   =  0
W_DETRIMENT   = -4
W_FALL        = -3

@dataclass(frozen=True)
class DignityResult:
    planet:        str
    sign:          str
    degree:        float
    dignity_name:  str
    score:         int
    is_exact_exaltation: bool

def score_dignity(
    planet: str,
    lambda_ecl_deg: float,   # Sidereal or tropical, per system configuration
    system: Literal["western", "vedic"] = "vedic",
) -> DignityResult:
    """
    Look up the essential dignity score for `planet` at `lambda_ecl_deg`.
    Achieves O(1) average time via dict lookup.

    Parameters
    ----------
    planet : str
        Planet name, e.g. "Sun", "Moon", "Mars".
    lambda_ecl_deg : float
        Ecliptic longitude in degrees [0, 360).
    system : "western" or "vedic"
        Which rulership table to use.

    Returns
    -------
    DignityResult with score in range [-4, +10].
    """
    sign_index = int(lambda_ecl_deg // 30) % 12
    sign = SIGNS[sign_index]
    degree_in_sign = lambda_ecl_deg % 30.0

    # Load appropriate lookup tables (imported from ops/config/)
    rulership_table = _load_rulership_table(system)
    exaltation_table = _load_exaltation_table()
    fall_table = _load_fall_table()

    # O(1) lookup
    if (planet, sign) in rulership_table.get("domicile", {}):
        return DignityResult(planet, sign, degree_in_sign, "domicile", W_DOMICILE, False)

    if planet in exaltation_table:
        ex_sign, ex_degree = exaltation_table[planet]
        if sign == ex_sign:
            is_exact = abs(degree_in_sign - ex_degree) < 1.0
            score = W_EXALT_EXACT if is_exact else W_EXALTATION
            name = "exact_exaltation" if is_exact else "exaltation"
            return DignityResult(planet, sign, degree_in_sign, name, score, is_exact)

    if (planet, sign) in fall_table:
        return DignityResult(planet, sign, degree_in_sign, "fall", W_FALL, False)

    if (planet, sign) in rulership_table.get("detriment", {}):
        return DignityResult(planet, sign, degree_in_sign, "detriment", W_DETRIMENT, False)

    return DignityResult(planet, sign, degree_in_sign, "peregrine", W_PEREGRINE, False)


def _load_rulership_table(system: str) -> dict:
    """Load from ops/config/dignity_rules.yml — cached at module import."""
    ...  # Implementation reads YAML once and caches as module-level dict

def _load_exaltation_table() -> dict[str, tuple[str, float]]:
    """Returns {planet: (exaltation_sign, exact_degree)}."""
    return {
        "Sun":     ("Aries",       10.0),
        "Moon":    ("Taurus",       3.0),
        "Mercury": ("Virgo",       15.0),
        "Venus":   ("Pisces",      27.0),
        "Mars":    ("Capricorn",   28.0),
        "Jupiter": ("Cancer",       5.0),
        "Saturn":  ("Libra",       20.0),
        "Rahu":    ("Gemini",      20.0),
        "Ketu":    ("Sagittarius", 20.0),
    }

def _load_fall_table() -> set[tuple[str, str]]:
    """Fall = opposite sign from exaltation."""
    OPPOSITE = {
        "Aries": "Libra", "Libra": "Aries",
        "Taurus": "Scorpio", "Scorpio": "Taurus",
        "Gemini": "Sagittarius", "Sagittarius": "Gemini",
        "Cancer": "Capricorn", "Capricorn": "Cancer",
        "Leo": "Aquarius", "Aquarius": "Leo",
        "Virgo": "Pisces", "Pisces": "Virgo",
    }
    exaltation = _load_exaltation_table()
    return {(planet, OPPOSITE[ex_sign]) for planet, (ex_sign, _) in exaltation.items()}
```

---

## 4. Normalised Dignity Score for Statistical Analysis

For integration with ML pipelines (Phase IV), scores are normalised to $[0, 1]$:

$$D_{\rm norm}(p, \lambda_{\rm ecl}) = \frac{D(p, \lambda_{\rm ecl}) - D_{\rm min}}{D_{\rm max} - D_{\rm min}} = \frac{D(p, \lambda_{\rm ecl}) + 4}{14}$$

where $D_{\rm min} = -4$ (detriment) and $D_{\rm max} = +10$ (exact exaltation).

---

_Symbol cross-reference: [SYMBOLOGY.md §II.F](../../SYMBOLOGY.md). Dignity rules are YAML-configurable at `ops/config/dignity_rules.yml` and `ops/config/dignity_rules_vedic.yml`._
