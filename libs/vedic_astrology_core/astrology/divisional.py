"""
Divisional charts (vargas) after Brihat Parashara Hora Shastra.

All sixteen Shodasavargas are defined in BPHS Ch. 6 ("Shodasha Varga
Adhyaya", R. Santhanam translation, Ranjan Publications 1984). Every equal
varga divides a sign into ``n`` parts and maps part ``k`` (0-based) to
``start_sign + step * k``, where the start sign depends on the rashi; that
rule is written as one table row per varga below. The trimsamsa (D30) uses
the unequal five-part division of BPHS Ch. 6 and is handled separately.

Sign indices: 0 = Aries ... 11 = Pisces. "Odd" signs are Aries, Gemini, ...
(index 0, 2, ...). Movable (chara) = index % 3 == 0, fixed (sthira) = 1,
dual (dvisvabhava) = 2. Element order = fire, earth, air, water (index % 4).

The golden tests check every part of every sign against PyJHora's
"traditional Parashara" method for each varga.
"""

from typing import Callable, Dict, List, Tuple

from ..config.constants import SIGN_NAMES, ZodiacSign

ARIES, TAURUS, GEMINI, CANCER, LEO, VIRGO = 0, 1, 2, 3, 4, 5
LIBRA, SCORPIO, SAGITTARIUS, CAPRICORN, AQUARIUS, PISCES = 6, 7, 8, 9, 10, 11

VARGA_FACTORS: List[int] = [1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60]


def _is_odd(sign: int) -> bool:
    return sign % 2 == 0


def _by_modality(movable: int, fixed: int, dual: int) -> Callable[[int], int]:
    return lambda sign: (movable, fixed, dual)[sign % 3]


def _by_element(fire: int, earth: int, air: int, water: int) -> Callable[[int], int]:
    return lambda sign: (fire, earth, air, water)[sign % 4]


# factor -> (start sign as a function of the rashi, step between parts)
EQUAL_VARGA_TABLE: Dict[int, Tuple[Callable[[int], int], int]] = {
    # D1 Rashi.
    1: (lambda s: s, 1),
    # D3 Drekkana: 1st, 5th and 9th from the sign.
    3: (lambda s: s, 4),
    # D4 Chaturthamsa: 1st, 4th, 7th and 10th from the sign.
    4: (lambda s: s, 3),
    # D7 Saptamsa: odd signs from the sign, even signs from the 7th.
    7: (lambda s: s if _is_odd(s) else s + 6, 1),
    # D9 Navamsa: fire from Aries, earth from Capricorn, air from Libra,
    # water from Cancer (movable from itself, fixed from 9th, dual from 5th).
    9: (_by_element(ARIES, CAPRICORN, LIBRA, CANCER), 1),
    # D10 Dasamsa: odd signs from the sign, even signs from the 9th.
    10: (lambda s: s if _is_odd(s) else s + 8, 1),
    # D12 Dwadasamsa: from the sign itself.
    12: (lambda s: s, 1),
    # D16 Shodasamsa: movable from Aries, fixed from Leo, dual from Sagittarius.
    16: (_by_modality(ARIES, LEO, SAGITTARIUS), 1),
    # D20 Vimsamsa: movable from Aries, fixed from Sagittarius, dual from Leo.
    20: (_by_modality(ARIES, SAGITTARIUS, LEO), 1),
    # D24 Chaturvimsamsa (Siddhamsa): odd signs from Leo, even from Cancer.
    24: (lambda s: LEO if _is_odd(s) else CANCER, 1),
    # D27 Bhamsa (Nakshatramsa): fire from Aries, earth from Cancer, air from
    # Libra, water from Capricorn.
    27: (_by_element(ARIES, CANCER, LIBRA, CAPRICORN), 1),
    # D40 Khavedamsa: odd signs from Aries, even signs from Libra.
    40: (lambda s: ARIES if _is_odd(s) else LIBRA, 1),
    # D45 Akshavedamsa: movable from Aries, fixed from Leo, dual from Sagittarius.
    45: (_by_modality(ARIES, LEO, SAGITTARIUS), 1),
    # D60 Shashtyamsa: counted from the sign itself.
    60: (lambda s: s, 1),
}

# D30 Trimsamsa, BPHS Ch. 6: (upper bound in degrees, sign) per segment.
# Odd signs: Mars 5, Saturn 5, Jupiter 8, Mercury 7, Venus 5 degrees.
TRIMSAMSA_ODD: List[Tuple[float, int]] = [
    (5.0, ARIES),
    (10.0, AQUARIUS),
    (18.0, SAGITTARIUS),
    (25.0, GEMINI),
    (30.0, LIBRA),
]
# Even signs: Venus 5, Mercury 7, Jupiter 8, Saturn 5, Mars 5 degrees.
TRIMSAMSA_EVEN: List[Tuple[float, int]] = [
    (5.0, TAURUS),
    (12.0, VIRGO),
    (20.0, PISCES),
    (25.0, CAPRICORN),
    (30.0, SCORPIO),
]


def _split(longitude: float) -> Tuple[int, float]:
    lon = longitude % 360.0
    sign = int(lon // 30) % 12
    return sign, lon - sign * 30.0


def _part(degrees_in_sign: float, factor: int) -> int:
    return min(int(degrees_in_sign // (30.0 / factor)), factor - 1)


def equal_varga_sign(longitude: float, factor: int) -> int:
    """Varga sign for an equal division, using :data:`EQUAL_VARGA_TABLE`."""
    start, step = EQUAL_VARGA_TABLE[factor]
    sign, deg = _split(longitude)
    return (start(sign) + step * _part(deg, factor)) % 12


def d1_rashi(longitude: float) -> int:
    """D1 Rashi chart sign (BPHS Ch. 6)."""
    return _split(longitude)[0]


def d2_hora(longitude: float) -> int:
    """D2 Hora, Parashara method (BPHS Ch. 6).

    Odd signs: first 15 deg is the Sun's hora (Leo), second 15 deg the Moon's
    (Cancer). Even signs: first half Moon (Cancer), second half Sun (Leo).
    """
    sign, deg = _split(longitude)
    first_half = deg < 15.0
    sun_hora = first_half if _is_odd(sign) else not first_half
    return LEO if sun_hora else CANCER


def d3_drekkana(longitude: float) -> int:
    """D3 Drekkana (BPHS Ch. 6): 1st, 5th, 9th sign from the rashi."""
    return equal_varga_sign(longitude, 3)


def d4_chaturthamsa(longitude: float) -> int:
    """D4 Chaturthamsa (BPHS Ch. 6): 1st, 4th, 7th, 10th sign from the rashi."""
    return equal_varga_sign(longitude, 4)


def d7_saptamsa(longitude: float) -> int:
    """D7 Saptamsa (BPHS Ch. 6): odd signs from the sign, even from the 7th."""
    return equal_varga_sign(longitude, 7)


def d9_navamsa(longitude: float) -> int:
    """D9 Navamsa (BPHS Ch. 6): fire Aries, earth Capricorn, air Libra, water Cancer."""
    return equal_varga_sign(longitude, 9)


def d10_dasamsa(longitude: float) -> int:
    """D10 Dasamsa (BPHS Ch. 6): odd signs from the sign, even from the 9th."""
    return equal_varga_sign(longitude, 10)


def d12_dwadasamsa(longitude: float) -> int:
    """D12 Dwadasamsa (BPHS Ch. 6): counted from the sign itself."""
    return equal_varga_sign(longitude, 12)


def d16_shodasamsa(longitude: float) -> int:
    """D16 Shodasamsa (BPHS Ch. 6): movable Aries, fixed Leo, dual Sagittarius."""
    return equal_varga_sign(longitude, 16)


def d20_vimsamsa(longitude: float) -> int:
    """D20 Vimsamsa (BPHS Ch. 6): movable Aries, fixed Sagittarius, dual Leo."""
    return equal_varga_sign(longitude, 20)


def d24_chaturvimsamsa(longitude: float) -> int:
    """D24 Chaturvimsamsa (BPHS Ch. 6): odd signs from Leo, even from Cancer."""
    return equal_varga_sign(longitude, 24)


def d27_bhamsa(longitude: float) -> int:
    """D27 Bhamsa (BPHS Ch. 6): fire Aries, earth Cancer, air Libra, water Capricorn."""
    return equal_varga_sign(longitude, 27)


def d30_trimsamsa(longitude: float) -> int:
    """D30 Trimsamsa (BPHS Ch. 6), unequal parts.

    Odd signs: 0-5 Aries (Mars), 5-10 Aquarius (Saturn), 10-18 Sagittarius
    (Jupiter), 18-25 Gemini (Mercury), 25-30 Libra (Venus). Even signs:
    0-5 Taurus (Venus), 5-12 Virgo (Mercury), 12-20 Pisces (Jupiter),
    20-25 Capricorn (Saturn), 25-30 Scorpio (Mars).
    """
    sign, deg = _split(longitude)
    table = TRIMSAMSA_ODD if _is_odd(sign) else TRIMSAMSA_EVEN
    for upper, varga in table:
        if deg < upper:
            return varga
    return table[-1][1]


def d40_khavedamsa(longitude: float) -> int:
    """D40 Khavedamsa (BPHS Ch. 6): odd signs from Aries, even from Libra."""
    return equal_varga_sign(longitude, 40)


def d45_akshavedamsa(longitude: float) -> int:
    """D45 Akshavedamsa (BPHS Ch. 6): movable Aries, fixed Leo, dual Sagittarius."""
    return equal_varga_sign(longitude, 45)


def d60_shashtyamsa(longitude: float) -> int:
    """D60 Shashtyamsa (BPHS Ch. 6): counted from the sign itself."""
    return equal_varga_sign(longitude, 60)


VARGA_FUNCTIONS: Dict[int, Callable[[float], int]] = {
    1: d1_rashi,
    2: d2_hora,
    3: d3_drekkana,
    4: d4_chaturthamsa,
    7: d7_saptamsa,
    9: d9_navamsa,
    10: d10_dasamsa,
    12: d12_dwadasamsa,
    16: d16_shodasamsa,
    20: d20_vimsamsa,
    24: d24_chaturvimsamsa,
    27: d27_bhamsa,
    30: d30_trimsamsa,
    40: d40_khavedamsa,
    45: d45_akshavedamsa,
    60: d60_shashtyamsa,
}


def varga_sign(longitude: float, factor: int) -> int:
    """Return the sign index (0-11) of ``longitude`` in the D-``factor`` chart.

    Raises:
        ValueError: If ``factor`` is not one of :data:`VARGA_FACTORS`.
    """
    if factor not in VARGA_FUNCTIONS:
        raise ValueError(f"Unsupported varga D{factor}; supported: {VARGA_FACTORS}")
    return VARGA_FUNCTIONS[factor](longitude)


def calculate_vargas(longitude: float) -> Dict[int, int]:
    """Return {factor: sign index} for all sixteen Shodasavargas."""
    return {factor: varga_sign(longitude, factor) for factor in VARGA_FACTORS}


def get_navamsa_sign(longitude: float) -> Tuple[int, str]:
    """Return (sign_index, sign_name) of the Navamsa (D9) position."""
    d9 = d9_navamsa(longitude)
    return d9, SIGN_NAMES[list(ZodiacSign)[d9]]


def calculate_d9(longitude: float) -> Dict:
    """Return D9 index, sign name and the vargottama flag."""
    d9_index, d9_name = get_navamsa_sign(longitude)
    return {
        "index": d9_index,
        "sign_name": d9_name,
        "is_vargottama": d9_index == d1_rashi(longitude),
    }
