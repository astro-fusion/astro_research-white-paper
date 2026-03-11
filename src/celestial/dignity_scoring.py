"""src/celestial/dignity_scoring.py.

Essential Dignity O(1) Hash-Map Scoring Engine
===============================================
See: papers/astrology/06_essential_dignity_scoring.md
     SYMBOLOGY.md §II.F
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SIGNS: list[str] = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

OPPOSITE_SIGN: dict[str, str] = {
    "Aries": "Libra",
    "Libra": "Aries",
    "Taurus": "Scorpio",
    "Scorpio": "Taurus",
    "Gemini": "Sagittarius",
    "Sagittarius": "Gemini",
    "Cancer": "Capricorn",
    "Capricorn": "Cancer",
    "Leo": "Aquarius",
    "Aquarius": "Leo",
    "Virgo": "Pisces",
    "Pisces": "Virgo",
}

W_EXACT_EXALTATION: int = 10
W_DOMICILE: int = 5
W_EXALTATION: int = 4
W_TRIPLICITY: int = 3
W_TERM: int = 2
W_FACE: int = 1
W_PEREGRINE: int = 0
W_DETRIMENT: int = -4
W_FALL: int = -3
D_MIN: int = W_DETRIMENT  # = −4
D_MAX: int = W_EXACT_EXALTATION  # = +10


@dataclass(frozen=True)
class DignityResult:
    """Result of a dignity score calculation."""

    planet: str
    sign: str
    degree_in_sign: float
    dignity_name: str
    score: int
    is_exact_exaltation: bool

    @property
    def normalized_score(self) -> float:
        """Normalised score in [0, 1] for ML feature use."""
        return (self.score - D_MIN) / (D_MAX - D_MIN)


# ── Lookup tables ────────────────────────────────────────────────────────────

_EXALTATION_TABLE: dict[str, tuple[str, float]] = {
    "Sun": ("Aries", 10.0),
    "Moon": ("Taurus", 3.0),
    "Mercury": ("Virgo", 15.0),
    "Venus": ("Pisces", 27.0),
    "Mars": ("Capricorn", 28.0),
    "Jupiter": ("Cancer", 5.0),
    "Saturn": ("Libra", 20.0),
    "Rahu": ("Gemini", 20.0),
    "Ketu": ("Sagittarius", 20.0),
}

_FALL_TABLE: set[tuple[str, str]] = {
    (planet, OPPOSITE_SIGN[ex_sign])
    for planet, (ex_sign, _) in _EXALTATION_TABLE.items()
}

# Western domicile rulership (traditional 7-planet system)
_DOMICILE_WESTERN: dict[str, list[str]] = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mercury": ["Gemini", "Virgo"],
    "Venus": ["Taurus", "Libra"],
    "Mars": ["Aries", "Scorpio"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Saturn": ["Capricorn", "Aquarius"],
}

# Vedic domicile (own signs — Swa kshetra)
_DOMICILE_VEDIC: dict[str, list[str]] = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mercury": ["Gemini", "Virgo"],
    "Venus": ["Taurus", "Libra"],
    "Mars": ["Aries", "Scorpio"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Saturn": ["Capricorn", "Aquarius"],
    "Rahu": ["Virgo"],
    "Ketu": ["Pisces"],
}


# Detriment = opposite of domicile sign(s)
def _build_detriment_table(domicile: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        planet: [OPPOSITE_SIGN[s] for s in signs if s in OPPOSITE_SIGN]
        for planet, signs in domicile.items()
    }


_DETRIMENT_WESTERN = _build_detriment_table(_DOMICILE_WESTERN)
_DETRIMENT_VEDIC = _build_detriment_table(_DOMICILE_VEDIC)


def score_dignity(
    planet: str,
    lambda_ecl_deg: float,
    system: Literal["western", "vedic"] = "vedic",
    exact_exalt_orb: float = 1.0,
) -> DignityResult:
    """
    Score the essential dignity of `planet` at `lambda_ecl_deg`.

    Achieves O(1) average lookup time via dict/set membership tests.

    Parameters
    ----------
    planet : str
        e.g. "Sun", "Moon", "Mars".
    lambda_ecl_deg : float
        Ecliptic longitude λ_ecl [0, 360).
    system : "western" | "vedic"
    exact_exalt_orb : float
        Degrees within which the exact exaltation point earns +10.

    Returns
    -------
    DignityResult with score in [−4, +10].
    """
    sign_index = int(lambda_ecl_deg // 30) % 12
    sign = SIGNS[sign_index]
    deg_in_sign = lambda_ecl_deg % 30.0

    domicile_table = _DOMICILE_VEDIC if system == "vedic" else _DOMICILE_WESTERN
    detriment_table = _DETRIMENT_VEDIC if system == "vedic" else _DETRIMENT_WESTERN

    # 1. Domicile
    if planet in domicile_table and sign in domicile_table[planet]:
        return DignityResult(planet, sign, deg_in_sign, "domicile", W_DOMICILE, False)

    # 2. Exaltation (exact or sign-wide)
    if planet in _EXALTATION_TABLE:
        ex_sign, ex_degree = _EXALTATION_TABLE[planet]
        if sign == ex_sign:
            is_exact = abs(deg_in_sign - ex_degree) <= exact_exalt_orb
            score = W_EXACT_EXALTATION if is_exact else W_EXALTATION
            name = "exact_exaltation" if is_exact else "exaltation"
            return DignityResult(planet, sign, deg_in_sign, name, score, is_exact)

    # 3. Fall
    if (planet, sign) in _FALL_TABLE:
        return DignityResult(planet, sign, deg_in_sign, "fall", W_FALL, False)

    # 4. Detriment
    if planet in detriment_table and sign in detriment_table[planet]:
        return DignityResult(planet, sign, deg_in_sign, "detriment", W_DETRIMENT, False)

    # 5. Peregrine (no dignity)
    return DignityResult(planet, sign, deg_in_sign, "peregrine", W_PEREGRINE, False)
