"""Build a shared Vedic astrology principles catalog for cross-report coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd

GRAHAS = [
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

RASHIS = [
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

NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashirsha",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

TITHIS = [
    "Pratipada",
    "Dvitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dvadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima",
    "Pratipada (Krishna)",
    "Dvitiya (Krishna)",
    "Tritiya (Krishna)",
    "Chaturthi (Krishna)",
    "Panchami (Krishna)",
    "Shashthi (Krishna)",
    "Saptami (Krishna)",
    "Ashtami (Krishna)",
    "Navami (Krishna)",
    "Dashami (Krishna)",
    "Ekadashi (Krishna)",
    "Dvadashi (Krishna)",
    "Trayodashi (Krishna)",
    "Chaturdashi (Krishna)",
    "Amavasya",
]

KARANAS = [
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Garaja",
    "Vanija",
    "Vishti",
    "Shakuni",
    "Chatushpada",
    "Naga",
    "Kimstughna",
]

YOGAS = [
    "Vishkumbha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shula",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]

VARGAS = [
    "D1 (Rasi)",
    "D2 (Hora)",
    "D3 (Drekkana)",
    "D4 (Chaturthamsha)",
    "D7 (Saptamsha)",
    "D9 (Navamsha)",
    "D10 (Dashamsha)",
    "D12 (Dwadashamsha)",
    "D16 (Shodashamsha)",
    "D20 (Vimshamsha)",
    "D24 (Chaturvimshamsha)",
    "D27 (Saptavimshamsha)",
    "D30 (Trimshamsha)",
    "D40 (Khavedamsha)",
    "D45 (Akshavedamsha)",
    "D60 (Shashtiamsha)",
]

DASHAS = [
    "Vimshottari",
    "Yogini",
    "Ashtottari",
    "Kalachakra",
    "Chara",
]

AVASTHAS = [
    "Bala",
    "Kumara",
    "Yuva",
    "Vriddha",
    "Mrityu",
    "Nidrashayana",
]

ASHTAKAVARGA = [
    "Bhinnashtakavarga",
    "Sarvashtakavarga",
]

ARUDHA = [
    "Arudha Lagna",
    "Bhava Arudha",
]

UPAGRAHAS = [
    "Gulika",
    "Mandi",
    "Yamaghantaka",
    "Ardhaprahara",
    "Kala",
]

SOURCES_CORE = (
    "bphs; varahamihira_brihat_samhita; surya_siddhanta; saravali; jataka_parijata"
)


def _add(
    rows: List[dict],
    principle_id: str,
    family: str,
    item_type: str,
    name: str,
    description: str,
    scope: str,
    computable: bool,
    sources: str = SOURCES_CORE,
) -> None:
    rows.append(
        {
            "principle_id": principle_id,
            "family": family,
            "item_type": item_type,
            "name": name,
            "description": description,
            "scope": scope,
            "computable": bool(computable),
            "sources": sources,
        }
    )


def _add_many(
    rows: List[dict],
    prefix: str,
    family: str,
    names: Iterable[str],
    description_template: str,
    scope: str,
    computable: bool,
    sources: str = SOURCES_CORE,
) -> None:
    for name in names:
        pid = f"{prefix}_{name.lower().replace(' ', '_').replace('(', '').replace(')', '')}"
        desc = description_template.format(name=name)
        _add(rows, pid, family, "member", name, desc, scope, computable, sources)


def build_vedic_principles_catalog() -> pd.DataFrame:
    """Return a DataFrame describing the shared Vedic principles taxonomy."""
    rows: List[dict] = []

    _add(
        rows,
        "graha",
        "graha",
        "family",
        "Graha (Planets)",
        "Nine planetary agents (Grahas) form the primary causal factors in Jyotish.",
        "core",
        True,
    )
    _add(
        rows,
        "rashi",
        "rashi",
        "family",
        "Rashi (Zodiac Signs)",
        "Twelve zodiac signs provide the spatial framework for planetary placement.",
        "core",
        True,
    )
    _add(
        rows,
        "bhava",
        "bhava",
        "family",
        "Bhava (Houses)",
        "Twelve houses encode experiential domains and areas of life.",
        "core",
        True,
    )
    _add(
        rows,
        "drishti",
        "drishti",
        "family",
        "Drishti (Aspects)",
        "Planetary aspects indicate interaction and influence between Grahas.",
        "core",
        True,
    )
    _add(
        rows,
        "nakshatra",
        "nakshatra",
        "family",
        "Nakshatra (Lunar Mansions)",
        "27 lunar mansions describe fine-grained lunar influence and timing.",
        "core",
        True,
    )
    _add(
        rows,
        "tithi",
        "tithi",
        "family",
        "Tithi (Lunar Day)",
        "30 lunar days drive timing and qualitative day classification.",
        "core",
        True,
    )
    _add(
        rows,
        "karana",
        "karana",
        "family",
        "Karana (Half-Tithi)",
        "11 karanas are half-tithi segments used for event suitability.",
        "core",
        True,
    )
    _add(
        rows,
        "yoga",
        "yoga",
        "family",
        "Yoga (Lunar-Solar Sum)",
        "27 yogas express combined Sun-Moon angular effects.",
        "core",
        True,
    )
    _add(
        rows,
        "combustion",
        "combustion",
        "family",
        "Combustion",
        "Planetary weakness when too close to the Sun.",
        "core",
        True,
    )
    _add(
        rows,
        "retrograde",
        "retrograde",
        "family",
        "Retrograde",
        "Apparent backward motion influencing results.",
        "core",
        True,
    )
    _add(
        rows,
        "graha_yuddha",
        "graha_yuddha",
        "family",
        "Graha Yuddha",
        "Planetary war when Grahas conjoin closely.",
        "core",
        True,
    )
    _add(
        rows,
        "shadbala",
        "shadbala",
        "family",
        "Shadbala",
        "Six-fold planetary strength system.",
        "core",
        True,
    )
    _add(
        rows,
        "dignity",
        "dignity",
        "family",
        "Dignity (Uccha/Neecha)",
        "Exaltation/debilitation sign-based strengths.",
        "core",
        True,
    )
    _add(
        rows,
        "syzygy",
        "syzygy",
        "family",
        "Syzygy (New/Full Moon)",
        "Sun-Moon alignment and opposition phases.",
        "core",
        True,
    )
    _add(
        rows,
        "eclipse",
        "eclipse",
        "family",
        "Eclipse",
        "Sun or Moon near nodal axis during syzygy.",
        "core",
        True,
    )

    _add(
        rows,
        "gocara",
        "gocara",
        "family",
        "Gocara (Transits)",
        "Planetary transits over natal or mundane reference points.",
        "extended",
        True,
    )
    _add(
        rows,
        "dasha",
        "dasha",
        "family",
        "Dasha Systems",
        "Major/minor period systems governing timing (e.g., Vimshottari).",
        "extended",
        True,
    )
    _add(
        rows,
        "varga",
        "varga",
        "family",
        "Varga Charts",
        "Divisional charts used to refine planetary strength and focus.",
        "extended",
        False,
    )
    _add(
        rows,
        "ashtakavarga",
        "ashtakavarga",
        "family",
        "Ashtakavarga",
        "Point-based evaluation of planetary contributions per sign.",
        "extended",
        False,
    )
    _add(
        rows,
        "arudha",
        "arudha",
        "family",
        "Arudha (Pada)",
        "Reflection-based indicators of manifestation and perception.",
        "extended",
        False,
    )
    _add(
        rows,
        "yoga_classical",
        "yoga_classical",
        "family",
        "Classical Yogas",
        "Combinational yogas such as Raja, Dhana, and Arishta yogas.",
        "extended",
        False,
    )
    _add(
        rows,
        "avastha",
        "avastha",
        "family",
        "Avastha (Planetary States)",
        "Planetary condition states across age/strength stages.",
        "extended",
        False,
    )
    _add(
        rows,
        "muhurta",
        "muhurta",
        "family",
        "Muhurta (Electional)",
        "Timing selection principles for auspicious actions.",
        "extended",
        False,
    )
    _add(
        rows,
        "upagraha",
        "upagraha",
        "family",
        "Upagraha",
        "Sub-planetary points used for timing and health indicators.",
        "extended",
        False,
    )
    _add(
        rows,
        "kala",
        "kala",
        "family",
        "Kala (Time Lords)",
        "Hora and kala divisions governing time quality.",
        "extended",
        False,
    )

    _add_many(rows, "graha", "graha", GRAHAS, "Graha: {name}.", "core", True)
    _add_many(rows, "rashi", "rashi", RASHIS, "Rashi: {name}.", "core", True)
    _add_many(
        rows,
        "bhava",
        "bhava",
        [str(i) for i in range(1, 13)],
        "Bhava: House {name}.",
        "core",
        True,
    )
    _add_many(
        rows, "nakshatra", "nakshatra", NAKSHATRAS, "Nakshatra: {name}.", "core", True
    )
    _add_many(rows, "tithi", "tithi", TITHIS, "Tithi: {name}.", "core", True)
    _add_many(rows, "karana", "karana", KARANAS, "Karana: {name}.", "core", True)
    _add_many(rows, "yoga", "yoga", YOGAS, "Yoga: {name}.", "core", True)

    _add_many(rows, "varga", "varga", VARGAS, "Varga chart: {name}.", "extended", False)
    for name in DASHAS:
        computable = name == "Vimshottari"
        _add(
            rows,
            f"dasha_{name.lower()}",
            "dasha",
            "member",
            name,
            f"Dasha system: {name}.",
            "extended",
            computable,
        )
    _add_many(
        rows, "avastha", "avastha", AVASTHAS, "Avastha: {name}.", "extended", False
    )
    _add_many(
        rows,
        "ashtakavarga",
        "ashtakavarga",
        ASHTAKAVARGA,
        "Ashtakavarga method: {name}.",
        "extended",
        False,
    )
    _add_many(
        rows, "arudha", "arudha", ARUDHA, "Arudha concept: {name}.", "extended", False
    )
    _add_many(
        rows, "upagraha", "upagraha", UPAGRAHAS, "Upagraha: {name}.", "extended", False
    )

    df = pd.DataFrame(rows)
    df = df.sort_values(["family", "item_type", "scope", "principle_id"]).reset_index(
        drop=True
    )
    return df


def write_vedic_principles_catalog(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = build_vedic_principles_catalog()
    df.to_csv(path, index=False)
    return path
