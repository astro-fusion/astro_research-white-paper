"""
Global Shadbala Scorer.

Calculates a 'Global Planetary Power' index for research purposes.
Unlike full Shadbala which requires a specific location (Ascendant/Dig Bala),
this scorer focuses on components that are consistent globally or geocentrically:
1. Chesta Bala (Motion Strength): Retrograde/Slow = Strong.
2. Sthana Bala (Position Strength): Exaltation/Own Sign.
3. Yuddha Bala (Planetary War): Proximity < 1 degree.
"""

import math
from typing import Dict, List, Optional

from ..astrology.ephemeris import EphemerisEngine
from ..config.constants import Planet
from .scorer import DignityScorer


class GlobalShadbalaScorer:
    """
    Calculates global planetary strength (0-100) for research matrix.
    """

    def __init__(self, ephemeris: Optional[EphemerisEngine] = None):
        self.ephemeris = ephemeris or EphemerisEngine()
        self.dignity_scorer = DignityScorer()

    def calculate_global_power(self, julian_day: float) -> Dict[str, float]:
        """
        Calculate daily power score (0-100) for all planets.

        Args:
            julian_day: The time point to score.

        Returns:
            Dict mapping planet name to global score.
        """
        positions = self.ephemeris.get_all_planet_positions(julian_day)
        scores = {}

        # 1. Base Scores (Sthana Bala - Positional)
        # We reuse the existing DignityScorer for Exaltation/Own Sign logic.
        for pname, pdata in positions.items():
            if pname in ["Rahu", "Ketu"]:
                # Nodes use simpler logic for now (just sign position)
                scores[pname] = 50.0
                continue

            planet_const = getattr(Planet, pname.upper(), None)
            if not planet_const:
                continue

            # DignityScorer needs sign index and longitude
            base = self.dignity_scorer.calculate_base_score(
                planet=planet_const,
                sign_index=pdata["sign"],
                longitude=pdata["longitude"],
            )
            scores[pname] = base

        # 2. Chesta Bala (Motion Strength)
        # Ancient logic: Retrograde (Vakra) is very strong.
        # Fast direct (Sighra) is weak.
        # We add a bonus/penalty to the base score.
        for pname, pdata in positions.items():
            if pname in ["Sun", "Moon", "Rahu", "Ketu"]:
                continue

            speed = pdata.get("longitude_speed", 0)
            is_retro = pdata.get("retrograde", False)

            if is_retro:
                # Significant boost for retrograde
                scores[pname] = min(100.0, scores[pname] * 1.3)
            elif abs(speed) < 0.1:
                # Stationary/Very slow
                scores[pname] = min(100.0, scores[pname] * 1.1)

        # 3. Yuddha Bala (Planetary War)
        # If two planets are within 1 degree, they are at war.
        # In research, we penalize BOTH for stress/volatility, or check declination for winner.
        # Simplified for Global Index: Penalize both slightly to represent "Conflict".
        keys = list(scores.keys())
        for i in range(len(keys)):
            p1 = keys[i]
            if p1 not in positions:
                continue

            for j in range(i + 1, len(keys)):
                p2 = keys[j]
                if p2 not in positions:
                    continue

                # Check longitude diff
                l1 = positions[p1]["longitude"]
                l2 = positions[p2]["longitude"]

                diff = abs(l1 - l2)
                if diff > 180:
                    diff = 360 - diff

                if diff < 1.0:
                    # War!
                    # Penalize score
                    scores[p1] *= 0.8
                    scores[p2] *= 0.8

        return scores
