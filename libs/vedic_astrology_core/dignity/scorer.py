"""
Dignity Scorer.

Main engine for calculating planetary dignity scores (0-100) based on:
- Essential dignity (exaltation, debilitation, moolatrikona, own signs)
- Friendship relationships
- Positional modifiers (retrograde, combust)
"""

from typing import Any, Dict, Optional

from ..config.constants import Planet
from .exaltation_matrix import (
    DEFAULT_RAHU_EXALTED_IN,
    _validate_tradition,
    get_dignity_type,
    is_in_debilitation,
    is_in_exaltation,
    is_in_moolatrikona,
    is_in_own_sign,
    uccha_bala,
)
from .friendship_matrix import (
    FriendshipType,
    calculate_tatkalika_maitri,
    get_combined_friendship,
    get_natural_friendship,
)
from .modifiers import apply_all_modifiers, get_modifier_explanation


class DignityScorer:
    """
    Main class for calculating planetary dignity scores.

    Provides methods to score planets based on their positions in a birth chart,
    incorporating all aspects of Vedic dignity calculation.
    """

    # Dignity score mapping (0-100 scale)
    DIGNITY_SCORES = {
        "exaltation": 100,
        "moolatrikona": 90,
        "own_sign": 75,
        "great_friend": 65,  # Adhi Mitra
        "friend": 50,  # Mitra
        "neutral": 40,  # Sama
        "enemy": 25,  # Shatru
        "great_enemy": 10,  # Adhi Shatru
        "debilitation": 5,
    }

    def __init__(self, rahu_exalted_in: str = DEFAULT_RAHU_EXALTED_IN) -> None:
        """Initialize the dignity scorer.

        Args:
            rahu_exalted_in: Node-exaltation tradition, "taurus" (default;
                Ketu in Scorpio) or "gemini" (Ketu in Sagittarius).
        """
        self.rahu_exalted_in = _validate_tradition(rahu_exalted_in)

    def calculate_base_score(
        self,
        planet: Planet,
        sign_index: int,
        longitude: float,
        chart: Optional[Any] = None,
    ) -> float:
        """
        Calculate base dignity score without modifiers.

        Args:
            planet: Planet to score
            sign_index: Zodiac sign index (0-11)
            longitude: Planet's longitude in degrees
            chart: BirthChart object (optional, for friendship calculations)

        Returns:
            Base dignity score (0-100)
        """
        # Essential dignity hierarchy. Exaltation/debilitation are whole-sign;
        # a moolatrikona range inside the exaltation sign (Moon in Taurus,
        # Mercury in Virgo) counts as moolatrikona, as in get_dignity_type.
        tradition = self.rahu_exalted_in
        if is_in_moolatrikona(longitude, planet):
            return self.DIGNITY_SCORES["moolatrikona"]
        elif is_in_exaltation(longitude, planet, tradition):
            return self.DIGNITY_SCORES["exaltation"]
        elif is_in_debilitation(longitude, planet, tradition):
            return self.DIGNITY_SCORES["debilitation"]
        elif is_in_own_sign(longitude, planet):
            return self.DIGNITY_SCORES["own_sign"]
        else:
            # Neutral sign, check friendship with sign lord
            return self._calculate_friendship_score(planet, sign_index, chart)

    def calculate_full_score(
        self,
        planet: Planet,
        sign_index: int,
        longitude: float,
        chart: Optional[Any] = None,
        planet_data: Optional[Dict] = None,
    ) -> float:
        """
        Calculate complete dignity score with all modifiers.

        Args:
            planet: Planet to score
            sign_index: Zodiac sign index (0-11)
            longitude: Planet's longitude in degrees
            chart: BirthChart object (optional)
            planet_data: Planet position data dictionary (optional, for modifiers)

        Returns:
            Full dignity score (0-100)
        """
        # Calculate base score
        base_score = self.calculate_base_score(planet, sign_index, longitude, chart)

        # Apply modifiers if planet data available
        if planet_data is not None:
            final_score = apply_all_modifiers(base_score, planet_data, planet, chart)
        else:
            final_score = base_score

        return final_score

    @staticmethod
    def friendship_with_sign_lord(
        planet: Planet, sign_lord: Planet, chart: Optional[Any] = None
    ) -> FriendshipType:
        """Return the friendship of ``planet`` with ``sign_lord``.

        The single rule used for both the score and its description:
        Panchadha (five-fold) Maitri when the chart has planet positions,
        otherwise Naisargika (natural) friendship only.
        """
        natural = get_natural_friendship(planet, sign_lord)
        chart_planets = getattr(chart, "planets", None)
        if chart is not None and isinstance(chart_planets, dict) and chart_planets:
            temporary = calculate_tatkalika_maitri(chart, planet, sign_lord)
            return get_combined_friendship(natural, temporary)
        return natural

    _FRIENDSHIP_SCORE_KEYS = {
        FriendshipType.ADHI_MITRA: "great_friend",
        FriendshipType.MITRA: "friend",
        FriendshipType.NATURAL_FRIEND: "friend",
        FriendshipType.SHATRU: "enemy",
        FriendshipType.NATURAL_ENEMY: "enemy",
        FriendshipType.ADHI_SHATRU: "great_enemy",
    }

    def _calculate_friendship_score(
        self, planet: Planet, sign_index: int, chart: Optional[Any] = None
    ) -> float:
        """
        Calculate dignity score based on friendship with sign lord.

        Returns:
            Dignity score based on friendship (10-65)
        """
        sign_lord = self._get_sign_lord(sign_index)
        if sign_lord is None:
            return self.DIGNITY_SCORES["neutral"]
        friendship = self.friendship_with_sign_lord(planet, sign_lord, chart)
        key = self._FRIENDSHIP_SCORE_KEYS.get(friendship, "neutral")
        return self.DIGNITY_SCORES[key]

    def _get_sign_lord(self, sign_index: int) -> Optional[Planet]:
        """
        Get the lord (ruling planet) of a zodiac sign.

        Args:
            sign_index: Zodiac sign index (0-11)

        Returns:
            Ruling planet, or None if no traditional ruler
        """
        # Traditional Vedic sign lords
        sign_lords = {
            0: Planet.MARS,  # Aries - Mars
            1: Planet.VENUS,  # Taurus - Venus
            2: Planet.MERCURY,  # Gemini - Mercury
            3: Planet.MOON,  # Cancer - Moon
            4: Planet.SUN,  # Leo - Sun
            5: Planet.MERCURY,  # Virgo - Mercury
            6: Planet.VENUS,  # Libra - Venus
            7: Planet.MARS,  # Scorpio - Mars
            8: Planet.JUPITER,  # Sagittarius - Jupiter
            9: Planet.SATURN,  # Capricorn - Saturn
            10: Planet.SATURN,  # Aquarius - Saturn
            11: Planet.JUPITER,  # Pisces - Jupiter
        }

        return sign_lords.get(sign_index)

    def score_planet_in_chart(self, planet: Planet, chart: Any) -> Dict[str, Any]:
        """
        Score a planet's dignity in a complete birth chart.

        Args:
            planet: Planet to score
            chart: BirthChart object

        Returns:
            Dictionary with scoring details:
            - 'score': Final dignity score (0-100)
            - 'base_score': Score before modifiers
            - 'dignity_type': Type of dignity (exaltation, etc.)
            - 'sign_lord': Ruling planet of sign
            - 'friendship': Friendship with sign lord
            - 'modifiers': Explanation of applied modifiers
        """
        if planet not in chart.planets:
            return {
                "score": 0.0,
                "base_score": 0.0,
                "dignity_type": "Not found",
                "sign_lord": None,
                "friendship": None,
                "modifiers": "Planet position not available",
            }

        planet_data = chart.planets[planet]
        longitude = planet_data["longitude"]
        sign_index = planet_data["sign"]

        # Calculate scores
        base_score = self.calculate_base_score(planet, sign_index, longitude, chart)
        final_score = self.calculate_full_score(
            planet, sign_index, longitude, chart, planet_data
        )

        # Get dignity type
        dignity_type = get_dignity_type(longitude, planet, self.rahu_exalted_in)

        # Get sign lord and friendship (same rule as the score)
        sign_lord = self._get_sign_lord(sign_index)
        friendship_desc = "Neutral"
        if sign_lord is not None:
            friendship_desc = self.friendship_with_sign_lord(
                planet, sign_lord, chart
            ).value

        # Get modifier explanation
        modifiers = get_modifier_explanation(
            base_score, final_score, planet_data, planet
        )

        return {
            "score": final_score,
            "base_score": base_score,
            "dignity_type": dignity_type,
            "sign_lord": sign_lord.name if sign_lord else None,
            "friendship": friendship_desc,
            "uccha_bala": (
                None
                if planet in (Planet.RAHU, Planet.KETU)
                else uccha_bala(planet, longitude)
            ),
            "modifiers": modifiers,
        }

    def get_dignity_status(self, score: float) -> str:
        """
        Convert dignity score to descriptive status.

        Args:
            score: Dignity score (0-100)

        Returns:
            Descriptive status string
        """
        if score >= 90:
            return "Exalted/Excellent"
        elif score >= 75:
            return "Very Strong"
        elif score >= 60:
            return "Strong"
        elif score >= 45:
            return "Moderate"
        elif score >= 25:
            return "Weak"
        elif score >= 10:
            return "Very Weak"
        else:
            return "Debilitated/Critical"

    def compare_planet_scores(
        self, planet_scores: Dict[Planet, float]
    ) -> Dict[str, Any]:
        """
        Compare dignity scores of multiple planets.

        Args:
            planet_scores: Dictionary mapping planets to their scores

        Returns:
            Analysis dictionary with comparisons and insights
        """
        if not planet_scores:
            return {"error": "No planet scores provided"}

        scores_list = list(planet_scores.values())
        # Find highest and lowest
        max_score = max(scores_list)
        min_score = min(scores_list)
        avg_score = sum(scores_list) / len(scores_list)

        max_planets = [p.name for p, s in planet_scores.items() if s == max_score]
        min_planets = [p.name for p, s in planet_scores.items() if s == min_score]

        # Calculate distribution
        excellent = sum(1 for s in scores_list if s >= 90)
        strong = sum(1 for s in scores_list if 75 <= s < 90)
        moderate = sum(1 for s in scores_list if 45 <= s < 75)
        weak = sum(1 for s in scores_list if 25 <= s < 45)
        poor = sum(1 for s in scores_list if s < 25)

        return {
            "strongest_planets": max_planets,
            "weakest_planets": min_planets,
            "highest_score": max_score,
            "lowest_score": min_score,
            "average_score": avg_score,
            "distribution": {
                "excellent": excellent,
                "strong": strong,
                "moderate": moderate,
                "weak": weak,
                "poor": poor,
            },
        }


# Convenience functions for external use
def calculate_base_score(
    planet: Planet, sign_index: int, longitude: float, chart: Optional[Any] = None
) -> float:
    """
    Calculate base dignity score.

    Args:
        planet: Planet to score
        sign_index: Zodiac sign index (0-11)
        longitude: Planet's longitude in degrees
        chart: BirthChart object (optional)

    Returns:
        Base dignity score (0-100)
    """
    scorer = DignityScorer()
    return scorer.calculate_base_score(planet, sign_index, longitude, chart)


def calculate_full_score(
    planet: Planet,
    sign_index: int,
    longitude: float,
    chart: Optional[Any] = None,
    planet_data: Optional[Dict] = None,
) -> float:
    """
    Calculate full dignity score.

    Args:
        planet: Planet to score
        sign_index: Zodiac sign index (0-11)
        longitude: Planet's longitude in degrees
        chart: BirthChart object (optional)
        planet_data: Planet position data (optional)

    Returns:
        Full dignity score (0-100)
    """
    scorer = DignityScorer()
    return scorer.calculate_full_score(
        planet, sign_index, longitude, chart, planet_data
    )
