"""
Global planetary strength index (research heuristic).

This is NOT Shadbala. Shadbala (BPHS Ch. 27) is the sum of six strengths
(sthana, dig, kala, chesta, naisargika and drik bala) in virupas, several of
which need the ascendant, the birth place and the time of day. The index here
is an ad-hoc 0-100 score for location-independent time series:

1. Base: the dignity score of :class:`DignityScorer` (sign-based).
2. Motion: x1.3 when retrograde, x1.1 when nearly stationary (Mars to
   Saturn only; the Sun, Moon and nodes have no chesta in this sense).
3. Graha yuddha (planetary war): x0.8 for both planets when two of Mars,
   Mercury, Jupiter, Venus and Saturn are within 1 degree. Classically war
   applies only to these five; the Sun, Moon and nodes never fight.
4. Rahu and Ketu get a fixed 50.

Do not call this index "Shadbala" in papers.
"""

from typing import Dict, Optional

from ..astrology.ephemeris import EphemerisEngine
from ..config.constants import Planet, PlanetDict
from .scorer import DignityScorer

NODES = (Planet.RAHU, Planet.KETU)
NO_CHESTA = (Planet.SUN, Planet.MOON, Planet.RAHU, Planet.KETU)
WAR_PLANETS = (Planet.MARS, Planet.MERCURY, Planet.JUPITER, Planet.VENUS, Planet.SATURN)
NODE_SCORE = 50.0
RETROGRADE_FACTOR = 1.3
STATIONARY_FACTOR = 1.1
STATIONARY_SPEED = 0.1  # degrees/day
WAR_ORB = 1.0  # degrees
WAR_FACTOR = 0.8


class GlobalStrengthScorer:
    """Location-independent planetary strength index (0-100); not Shadbala."""

    def __init__(
        self,
        ephemeris: Optional[EphemerisEngine] = None,
        rahu_exalted_in: str = "taurus",
    ):
        """Create the scorer with an ephemeris engine and node tradition."""
        self.ephemeris = ephemeris or EphemerisEngine()
        self.dignity_scorer = DignityScorer(rahu_exalted_in=rahu_exalted_in)

    def calculate_global_power(self, julian_day: float) -> PlanetDict:
        """
        Calculate the strength index (0-100) of every planet.

        Args:
            julian_day: Julian day (UT) to score.

        Returns:
            :class:`PlanetDict` mapping Planet to score.
        """
        positions = PlanetDict(self.ephemeris.get_all_planet_positions(julian_day))
        scores: Dict[Planet, float] = PlanetDict()

        for planet, pdata in positions.items():
            if planet in NODES:
                scores[planet] = NODE_SCORE
                continue
            scores[planet] = self.dignity_scorer.calculate_base_score(
                planet=planet,
                sign_index=pdata["sign"],
                longitude=pdata["longitude"],
            )

        for planet, pdata in positions.items():
            if planet in NO_CHESTA:
                continue
            speed = pdata.get("longitude_speed", 0.0)
            if pdata.get("retrograde", speed < 0):
                scores[planet] = min(100.0, scores[planet] * RETROGRADE_FACTOR)
            elif abs(speed) < STATIONARY_SPEED:
                scores[planet] = min(100.0, scores[planet] * STATIONARY_FACTOR)

        fighters = [p for p in WAR_PLANETS if p in positions]
        for i, p1 in enumerate(fighters):
            for p2 in fighters[i + 1 :]:
                diff = abs(positions[p1]["longitude"] - positions[p2]["longitude"])
                diff = min(diff % 360.0, 360.0 - diff % 360.0)
                if diff < WAR_ORB:
                    scores[p1] *= WAR_FACTOR
                    scores[p2] *= WAR_FACTOR

        return scores  # type: ignore[return-value]
