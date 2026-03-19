r"""src/celestial/ephemeris_engine.py.

Swiss Ephemeris Wrapper — Celestial Position Computation
=========================================================
Provides high-precision geocentric ecliptic and equatorial coordinates
for all major planetary bodies using pyswisseph (Lahiri ayanamsa).

Mathematical model: papers/astrology/01_celestial_mechanics_and_ephemeris.md
Symbol reference:   SYMBOLOGY.md §II.A–II.B
Data output:        data/ephemeris/

Usage
-----
    python src/celestial/ephemeris_engine.py \
        --body_list Sun Moon Mars Mercury Jupiter Venus Saturn \
        --start_jd 2451545.0 \
        --end_jd 2488069.5 \
        --step_days 1 \
        --output data/ephemeris/planets_2000_2100.parquet
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Ayanamsa Mapping (Swiss Ephemeris constants) ──────────────────────────────
AYANAMSA_MODES: dict[str, int] = {
    "Lahiri": 0,  # swe.SIDM_LAHIRI
    "Raman": 3,  # swe.SIDM_RAMAN
    "KP": 5,  # swe.SIDM_KRISHNAMURTI
    "Fagan-Bradley": 1,  # swe.SIDM_FAGAN_BRADLEY
}

# ── Body ID mapping (Swiss Ephemeris constants) ─────────────────────────────
BODY_IDS: dict[str, int] = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9,
    "Rahu": 10,  # Mean ascending node (Ketu = Rahu + 180°)
    "Ketu": 11,  # Mean descending node
}

# J2000.0 epoch
J2000: float = 2451545.0


@dataclass
class CelestialPosition:
    """Geocentric position of a celestial body.

    All angles in degrees; distance in AU; JD in Terrestrial Time.
    Symbol mapping: SYMBOLOGY.md §II.A
    """

    body_name: str
    jd_tt: float  # Julian Day (TT)
    lambda_ecl: float  # Tropical ecliptic longitude λ_ecl [°]
    beta: float  # Celestial latitude β [°]
    r_au: float  # Geocentric distance [AU]
    lambda_sid: float  # Sidereal (Lahiri) longitude [°]
    delta_decl: float  # Declination δ_decl [°]
    alpha_ra: float  # Right ascension α [°]
    velocity: float  # Longitudinal velocity dλ_ecl/dt [°/day]
    is_retrograde: bool  # True if dλ_ecl/dt < 0
    is_oob: bool  # Out-of-Bounds: |δ_decl| > obliquity


def _ecliptic_to_equatorial(
    lambda_ecl_deg: float,
    beta_deg: float,
    epsilon_deg: float = 23.4393,
) -> tuple[float, float]:
    """
    Transform ecliptic (λ_ecl, β) to equatorial (α, δ_decl).

    Equations (SYMBOLOGY.md §II.A):
        sin(δ) = sin(β)cos(ε) + cos(β)sin(ε)sin(λ)
        cos(α)cos(δ) = cos(β)cos(λ)
        sin(α)cos(δ) = −sin(β)sin(ε) + cos(β)cos(ε)sin(λ)
    """
    lam = math.radians(lambda_ecl_deg)
    bet = math.radians(beta_deg)
    eps = math.radians(epsilon_deg)

    sin_delta = math.sin(bet) * math.cos(eps) + math.cos(bet) * math.sin(
        eps
    ) * math.sin(lam)
    delta_rad = math.asin(sin_delta)

    sin_alpha_cos_delta = -math.sin(bet) * math.sin(eps) + math.cos(bet) * math.cos(
        eps
    ) * math.sin(lam)
    cos_alpha_cos_delta = math.cos(bet) * math.cos(lam)

    alpha_rad = math.atan2(sin_alpha_cos_delta, cos_alpha_cos_delta)
    if alpha_rad < 0:
        alpha_rad += 2 * math.pi

    return math.degrees(alpha_rad), math.degrees(delta_rad)


def compute_position(
    body_name: str, jd_tt: float, ayanamsa_name: str = "Lahiri"
) -> CelestialPosition:
    """
    Compute the geocentric ecliptic and equatorial position of a body.

    Requires pyswisseph. Falls back gracefully if not installed.
    """
    try:
        import swisseph as swe
    except ImportError as exc:
        raise ImportError(
            "pyswisseph is required. Install with: pip install pyswisseph"
        ) from exc

    body_id = BODY_IDS[body_name]
    mode = AYANAMSA_MODES.get(ayanamsa_name, swe.SIDM_LAHIRI)
    swe.set_sid_mode(mode)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    # Tropical position
    trop_result, _ = swe.calc_ut(jd_tt, body_id, flags)
    lambda_ecl, beta, r_au, velocity = (
        trop_result[0],
        trop_result[1],
        trop_result[2],
        trop_result[3],
    )

    # Sidereal position (Lahiri)
    sid_result, _ = swe.calc_ut(jd_tt, body_id, flags | swe.FLG_SIDEREAL)
    lambda_sid = sid_result[0]

    # Compute obliquity at epoch
    epsilon = swe.calc_ut(jd_tt, swe.ECL_NUT, 0)[0][0]  # returns obliquity in index 0

    # Equatorial coordinates
    alpha_ra, delta_decl = _ecliptic_to_equatorial(lambda_ecl, beta, epsilon)

    is_oob = abs(delta_decl) > epsilon

    return CelestialPosition(
        body_name=body_name,
        jd_tt=jd_tt,
        lambda_ecl=lambda_ecl,
        beta=beta,
        r_au=r_au,
        lambda_sid=lambda_sid,
        delta_decl=delta_decl,
        alpha_ra=alpha_ra,
        velocity=velocity,
        is_retrograde=velocity < 0,
        is_oob=is_oob,
    )


def generate_ephemeris(
    body_names: list[str],
    jd_start: float,
    jd_end: float,
    step_days: float = 1.0,
    ayanamsa_name: str = "Lahiri",
) -> pd.DataFrame:
    """
    Compute positions for multiple bodies over a time range.

    Returns a long-format DataFrame suitable for Parquet export.
    Columns: jd_tt, body_name, lambda_ecl, beta, r_au, lambda_sid,
             delta_decl, alpha_ra, velocity, is_retrograde, is_oob.
    """
    jd_range = np.arange(jd_start, jd_end, step_days)
    records: list[dict] = []

    for jd in jd_range:
        for name in body_names:
            try:
                pos = compute_position(name, float(jd), ayanamsa_name)
                records.append(
                    {
                        "jd_tt": pos.jd_tt,
                        "body_name": pos.body_name,
                        "lambda_ecl": pos.lambda_ecl,
                        "beta": pos.beta,
                        "r_au": pos.r_au,
                        "lambda_sid": pos.lambda_sid,
                        "delta_decl": pos.delta_decl,
                        "alpha_ra": pos.alpha_ra,
                        "velocity": pos.velocity,
                        "is_retrograde": pos.is_retrograde,
                        "is_oob": pos.is_oob,
                    }
                )
            except Exception:
                logger.exception("Error computing %s at JD=%.2f", name, jd)

    df = pd.DataFrame(records)
    logger.info(
        "Generated %d ephemeris records for %d bodies, %.0f time-steps.",
        len(df),
        len(body_names),
        len(jd_range),
    )
    return df


def main() -> None:
    """Run ephemeris generator CLI."""
    parser = argparse.ArgumentParser(description="Swiss Ephemeris position generator")
    parser.add_argument("--body_list", nargs="+", default=list(BODY_IDS.keys()))
    parser.add_argument("--start_jd", type=float, default=J2000)
    parser.add_argument("--end_jd", type=float, default=J2000 + 36524.25)  # 100 years
    parser.add_argument("--step_days", type=float, default=1.0)
    parser.add_argument(
        "--ayanamsa",
        choices=list(AYANAMSA_MODES.keys()),
        default="Lahiri",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/ephemeris/planets_j2000_j2100.parquet"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    df = generate_ephemeris(
        body_names=args.body_list,
        jd_start=args.start_jd,
        jd_end=args.end_jd,
        step_days=args.step_days,
        ayanamsa_name=args.ayanamsa,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    logger.info("Ephemeris saved → %s", args.output)


if __name__ == "__main__":
    main()
