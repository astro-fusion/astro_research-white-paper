"""Names an astrologer may write in a rule file.

Planets, the Lagna, signs and nakshatras are resolved here, with the usual
Sanskrit and spelling variants accepted as aliases ("Guru" is Jupiter,
"Mesha" is Aries, "Aswini" is Ashwini). Unknown names raise
:class:`VocabularyError` with a "did you mean" suggestion.
"""

import difflib
from typing import Dict, List, Union

from ..config.constants import NAKSHATRAS, Planet

LAGNA = "Lagna"

PLANET_NAMES: List[str] = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
]

SIGN_NAMES: List[str] = [
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

NAKSHATRA_NAMES: List[str] = [NAKSHATRAS[i]["name"] for i in range(27)]

_PLANET_ALIASES = {
    "surya": "Sun",
    "ravi": "Sun",
    "chandra": "Moon",
    "soma": "Moon",
    "mangal": "Mars",
    "mangala": "Mars",
    "kuja": "Mars",
    "budha": "Mercury",
    "guru": "Jupiter",
    "brihaspati": "Jupiter",
    "shukra": "Venus",
    "sukra": "Venus",
    "shani": "Saturn",
    "sani": "Saturn",
    "northnode": "Rahu",
    "southnode": "Ketu",
}

_LAGNA_ALIASES = {"lagna", "ascendant", "asc", "rising"}

_SIGN_ALIASES = {
    "mesha": "Aries",
    "vrishabha": "Taurus",
    "vrishabham": "Taurus",
    "mithuna": "Gemini",
    "karka": "Cancer",
    "karkata": "Cancer",
    "kataka": "Cancer",
    "simha": "Leo",
    "kanya": "Virgo",
    "tula": "Libra",
    "vrischika": "Scorpio",
    "vrishchika": "Scorpio",
    "dhanu": "Sagittarius",
    "dhanus": "Sagittarius",
    "makara": "Capricorn",
    "kumbha": "Aquarius",
    "meena": "Pisces",
    "mina": "Pisces",
}

_NAKSHATRA_ALIASES = {
    "aswini": "Ashwini",
    "asvini": "Ashwini",
    "kritika": "Krittika",
    "karthika": "Krittika",
    "mrigasira": "Mrigashira",
    "mrigashirsha": "Mrigashira",
    "mrigasirsha": "Mrigashira",
    "arudra": "Ardra",
    "aridra": "Ardra",
    "pushyami": "Pushya",
    "pusya": "Pushya",
    "aslesha": "Ashlesha",
    "ashlesa": "Ashlesha",
    "makha": "Magha",
    "purvaphalguni": "Purva Phalguni",
    "pubba": "Purva Phalguni",
    "uttaraphalguni": "Uttara Phalguni",
    "uttara": "Uttara Phalguni",
    "chitta": "Chitra",
    "svati": "Swati",
    "visakha": "Vishakha",
    "visaka": "Vishakha",
    "anuradha": "Anuradha",
    "jyeshta": "Jyeshtha",
    "jyestha": "Jyeshtha",
    "moola": "Mula",
    "purvashadha": "Purva Ashadha",
    "poorvashadha": "Purva Ashadha",
    "uttarashadha": "Uttara Ashadha",
    "sravana": "Shravana",
    "shravan": "Shravana",
    "dhanishtha": "Dhanishta",
    "dhanista": "Dhanishta",
    "satabhisha": "Shatabhisha",
    "shatabhishak": "Shatabhisha",
    "satabhishak": "Shatabhisha",
    "purvabhadrapada": "Purva Bhadrapada",
    "purvabhadra": "Purva Bhadrapada",
    "uttarabhadrapada": "Uttara Bhadrapada",
    "uttarabhadra": "Uttara Bhadrapada",
}


class VocabularyError(ValueError):
    """An unknown planet, sign or nakshatra name in a rule."""


def _key(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _resolve(kind: str, name: object, canonical: List[str], aliases: Dict) -> str:
    if not isinstance(name, str):
        raise VocabularyError(f"{kind} must be a name, got {name!r}")
    key = _key(name)
    table = {_key(c): c for c in canonical}
    table.update(aliases)
    if key in table:
        return table[key]
    guess = difflib.get_close_matches(key, list(table), n=1, cutoff=0.6)
    hint = f" Did you mean '{table[guess[0]]}'?" if guess else ""
    raise VocabularyError(
        f"unknown {kind} '{name}'.{hint} Known: {', '.join(canonical)}"
    )


def planet_name(name: object) -> str:
    """Return the canonical planet name ("Guru" -> "Jupiter")."""
    return _resolve("planet", name, PLANET_NAMES, _PLANET_ALIASES)


def point_name(name: object) -> str:
    """Return a canonical planet name or "Lagna" (the ascendant)."""
    if isinstance(name, str) and _key(name) in _LAGNA_ALIASES:
        return LAGNA
    try:
        return planet_name(name)
    except VocabularyError as exc:
        raise VocabularyError(str(exc).replace("planet", "planet or Lagna", 1))


def sign_name(name: object) -> str:
    """Return the canonical sign name ("Mesha" -> "Aries")."""
    return _resolve("sign", name, SIGN_NAMES, _SIGN_ALIASES)


def nakshatra_name(name: object) -> str:
    """Return the canonical nakshatra name ("Aswini" -> "Ashwini")."""
    return _resolve("nakshatra", name, NAKSHATRA_NAMES, _NAKSHATRA_ALIASES)


def to_planet_enum(name: str) -> Planet:
    """Return the :class:`Planet` for a canonical planet name."""
    return Planet[planet_name(name).upper()]


def sign_index(name: Union[str, int]) -> int:
    """Return the 0-based sign index (Aries = 0) of a sign name."""
    return SIGN_NAMES.index(sign_name(name))


def nakshatra_index(name: str) -> int:
    """Return the 0-based nakshatra index (Ashwini = 0)."""
    return NAKSHATRA_NAMES.index(nakshatra_name(name))


def ordinal(n: int) -> str:
    """Return 1st, 2nd, 3rd, 4th ... for a house number."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def all_aliases(kind: str) -> List[str]:
    """Every accepted spelling for ``kind`` (planet, point, sign, nakshatra)."""
    if kind == "planet":
        return PLANET_NAMES + sorted(a.title() for a in _PLANET_ALIASES)
    if kind == "point":
        return all_aliases("planet") + [LAGNA, "Ascendant"]
    if kind == "sign":
        return SIGN_NAMES + sorted(a.title() for a in _SIGN_ALIASES)
    if kind == "nakshatra":
        return NAKSHATRA_NAMES + sorted(a.title() for a in _NAKSHATRA_ALIASES)
    raise ValueError(kind)
