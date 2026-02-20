"""Atomic Astrological Conditions.

This module defines the foundational building blocks for astrological rules.
Every condition evaluates a specific planetary state (e.g., Conjunction, Aspect,
Sign Placement) and returns a binary activation state along with an optional
continuous strength score (0.0 to 1.0).
"""

from typing import Dict, List, Any, Union


class AstroCondition:
    """Base class for all astrological conditions."""

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Evaluate the condition against a set of planetary positions.

        Args:
            positions: Dictionary of planetary position data from EphemerisEngine.

        Returns:
            Dict containing:
                - is_active: bool
                - score: float (0.0 to 1.0, representing strength/closeness)
                - details: str (human readable explanation)
        """
        raise NotImplementedError("Subclasses must implement evaluate()")

    def _angular_separation(self, lon1: float, lon2: float) -> float:
        """Calculate the shortest angular distance between two longitudes."""
        diff = abs(lon1 - lon2)
        return min(diff, 360.0 - diff)

    def get_planet_data(self, positions: Dict[str, Dict], planet: str) -> Dict:
        """Extract planet data, raising a clear error if missing."""
        planet = planet.capitalize()
        # Handle nodes gracefully since they might be keyed as 'True Node'/'Rahu' etc.
        if planet not in positions:
            if planet == "Rahu" and "True Node" in positions:
                return positions["True Node"]
            elif planet == "Ketu" and "South Node" in positions:
                return positions["South Node"]
            else:
                raise KeyError(f"Planet '{planet}' not found in position data.")
        return positions[planet]


class ConjunctionCondition(AstroCondition):
    """Checks if two planets are within a specified angular orb."""

    def __init__(self, planet1: str, planet2: str, orb_deg: float):
        """Initialize with two planets and an angular orb."""
        self.planet1 = planet1
        self.planet2 = planet2
        self.orb_deg = orb_deg

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """Evaluate conjunction between two planets."""
        p1_data = self.get_planet_data(positions, self.planet1)
        p2_data = self.get_planet_data(positions, self.planet2)

        sep = self._angular_separation(p1_data["longitude"], p2_data["longitude"])
        is_active = sep <= self.orb_deg

        # Linear falloff score: 1.0 at 0 deg, 0.0 at orb_deg
        score = max(0.0, 1.0 - (sep / self.orb_deg)) if is_active else 0.0

        return {
            "is_active": is_active,
            "score": score,
            "details": (
                f"{self.planet1}-{self.planet2} separation: "
                f"{sep:.2f}° (orb: {self.orb_deg}°)"
            ),
        }


class ZodiacSignCondition(AstroCondition):
    """Checks if a planet is in a specific set of zodiac signs."""

    def __init__(self, planet: str, allowed_signs: List[Union[str, int]]):
        """Initialize with a planet and a list of allowed zodiac signs."""
        self.planet = planet

        # Standardize signs to integer indices (0=Aries, 11=Pisces)
        self.allowed_sign_indices = []
        sign_map = {
            "aries": 0,
            "taurus": 1,
            "gemini": 2,
            "cancer": 3,
            "leo": 4,
            "virgo": 5,
            "libra": 6,
            "scorpio": 7,
            "sagittarius": 8,
            "capricorn": 9,
            "aquarius": 10,
            "pisces": 11,
        }

        for s in allowed_signs:
            if isinstance(s, int):
                self.allowed_sign_indices.append(s)
            elif isinstance(s, str) and s.lower() in sign_map:
                self.allowed_sign_indices.append(sign_map[s.lower()])
            else:
                raise ValueError(f"Unknown sign: {s}")

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """Evaluate if the planet is in one of the allowed signs."""
        p_data = self.get_planet_data(positions, self.planet)
        current_sign = p_data.get("sign")

        # Fallback if the ephemeris dictionary uses different key shapes
        if current_sign is None:
            current_sign = int(p_data["longitude"] / 30) % 12

        is_active = current_sign in self.allowed_sign_indices
        score = 1.0 if is_active else 0.0

        return {
            "is_active": is_active,
            "score": score,
            "details": f"{self.planet} in sign {current_sign}",
        }


class SignElementCondition(AstroCondition):
    """
    Checks if a planet is in a sign of a specific element.

    Supported elements: FIRE, EARTH, AIR, WATER.
    """

    ELEMENT_MAP = {
        "FIRE": [0, 4, 8],  # Aries, Leo, Sagittarius
        "EARTH": [1, 5, 9],  # Taurus, Virgo, Capricorn
        "AIR": [2, 6, 10],  # Gemini, Libra, Aquarius
        "WATER": [3, 7, 11],  # Cancer, Scorpio, Pisces
    }

    def __init__(self, planet: str, element: str):
        """Initialize with a planet and a specific element (FIRE, WATER, etc.)."""
        self.planet = planet
        self.element = element.upper()
        if self.element not in self.ELEMENT_MAP:
            raise ValueError(
                f"Invalid element '{element}'. "
                f"Must be one of {list(self.ELEMENT_MAP.keys())}"
            )

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """Evaluate if the planet is in a sign of the given element."""
        p_data = self.get_planet_data(positions, self.planet)
        current_sign = p_data.get("sign")
        if current_sign is None:
            current_sign = int(p_data["longitude"] / 30) % 12

        is_active = current_sign in self.ELEMENT_MAP[self.element]

        return {
            "is_active": is_active,
            "score": 1.0 if is_active else 0.0,
            "details": f"{self.planet} in element {self.element} (sign {current_sign})",
        }


class AspectCondition(AstroCondition):
    """
    Evaluate Vedic aspects from one planet to another involving house counts.

    Vedic tracking considers sign-to-sign aspects, but this implements degrees.
    """

    def __init__(
        self,
        aspecting_planet: str,
        target_planet: str,
        house_aspect: int,
        orb_deg: float = 15.0,
    ):
        """Initialize with aspecting/target planets and house distance."""
        self.aspecting_planet = aspecting_planet
        self.target_planet = target_planet
        self.house_aspect = house_aspect
        self.orb_deg = orb_deg

        # Target angle is (house - 1) * 30 degrees ahead
        self.target_angle = (house_aspect - 1) * 30.0

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """Evaluate specific house aspect from one planet to another."""
        p1_data = self.get_planet_data(positions, self.aspecting_planet)
        p2_data = self.get_planet_data(positions, self.target_planet)

        # Calculate aspect point
        aspect_point = (p1_data["longitude"] + self.target_angle) % 360.0

        sep = self._angular_separation(aspect_point, p2_data["longitude"])
        is_active = sep <= self.orb_deg

        score = max(0.0, 1.0 - (sep / self.orb_deg)) if is_active else 0.0

        return {
            "is_active": is_active,
            "score": score,
            "details": (
                f"{self.aspecting_planet} {self.house_aspect}th aspect on "
                f"{self.target_planet}. Separation: {sep:.2f}° (orb: {self.orb_deg}°)"
            ),
        }


class RetrogradeCondition(AstroCondition):
    """Checks if a planet is in retrograde motion."""

    def __init__(self, planet: str):
        """Initialize with a planet to track."""
        self.planet = planet

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """Evaluate if the planet is in retrograde motion."""
        p_data = self.get_planet_data(positions, self.planet)

        # Most celestial bodies have a 'retrograde' boolean, or negative longitude_speed
        is_retro = p_data.get("retrograde", False)
        if "longitude_speed" in p_data and not is_retro:
            is_retro = p_data["longitude_speed"] < 0

        return {
            "is_active": is_retro,
            "score": 1.0 if is_retro else 0.0,
            "details": f"{self.planet} retrograde: {is_retro}",
        }


class StationaryCondition(AstroCondition):
    """Checks if a planet is near stationary (speed very close to 0)."""

    def __init__(self, planet: str, speed_threshold: float = 0.05):
        """Initialize with planet and speed threshold."""
        self.planet = planet
        self.speed_threshold = speed_threshold

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """Evaluate if the planet is near-stationary."""
        p_data = self.get_planet_data(positions, self.planet)
        speed = p_data.get("longitude_speed", 999.0)

        is_active = abs(speed) <= self.speed_threshold
        # Score increases as speed approaches 0
        score = (
            max(0.0, 1.0 - (abs(speed) / self.speed_threshold)) if is_active else 0.0
        )

        return {
            "is_active": is_active,
            "score": score,
            "details": (
                f"{self.planet} speed: {speed:.4f}°/day "
                f"(thresh: {self.speed_threshold})"
            ),
        }


# Factory for creating conditions from dictionary configs (YAML loaded)
def create_condition(config: Dict[str, Any]) -> AstroCondition:
    """Instantiate rule conditions from their config dict."""
    cond_type = config.get("type", "").upper()

    if cond_type == "CONJUNCTION":
        return ConjunctionCondition(
            config["planet1"], config["planet2"], float(config.get("orb_deg", 10.0))
        )
    elif cond_type == "ASPECT":
        return AspectCondition(
            config["aspect_planet"],
            config["target_planet"],
            int(config["house_aspect"]),
            float(config.get("orb_deg", 15.0)),
        )
    elif cond_type == "SIGNELEMENT":
        return SignElementCondition(config["planet"], config["element"])
    elif cond_type == "INSIGN":
        return ZodiacSignCondition(config["planet"], config["signs"])
    elif cond_type == "RETROGRADE":
        return RetrogradeCondition(config["planet"])
    elif cond_type == "STATIONARY":
        return StationaryCondition(
            config["planet"], float(config.get("speed_threshold", 0.05))
        )
    else:
        raise ValueError(f"Unknown condition type: {cond_type}")
