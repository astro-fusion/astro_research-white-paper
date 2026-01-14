"""
Dignity Modifiers

Implements modifiers that adjust planetary dignity scores based on:
- Retrograde motion (Neecha Bhanga - cancellation of debilitation)
- Combustion (close proximity to Sun)
- Other positional modifiers
"""

from typing import Any, Dict, Optional

from ..config.constants import Planet

# Modifier constants
RETROGRADE_BONUS_DEBILITATED = 50  # Points added for retrograde debilitated planet
RETROGRADE_BONUS_NORMAL = 15  # Points added for retrograde non-debilitated planet

COMBUST_PENALTY_MAJOR = 40  # Points subtracted for close combustion
COMBUST_PENALTY_MINOR = 20  # Points subtracted for moderate combustion

# Combustion orbs (degrees from Sun)
COMBUST_ORB_MAJOR = 3.0  # Within 3° of Sun (major combustion)
COMBUST_ORB_MINOR = 8.0  # Within 8° of Sun (minor combustion)

# Other modifiers
EXACT_EXALTATION_BONUS = 5  # Bonus for exact exaltation degree
EXACT_DEBILITATION_PENALTY = 10  # Additional penalty for exact debilitation


def apply_retrograde_bonus(
    base_score: float, is_retrograde: bool, is_debilitated: bool
) -> float:
    """
    Apply retrograde bonus to dignity score.

    In Vedic astrology, retrograde planets are considered stronger, especially
    when debilitated (Neecha Bhanga - cancellation of debilitation).

    Args:
        base_score: Base dignity score (0-100)
        is_retrograde: Whether planet is retrograde
        is_debilitated: Whether planet is debilitated

    Returns:
        Modified score with retrograde bonus applied
    """
    if not is_retrograde:
        return base_score

    if is_debilitated:
        # Neecha Bhanga: Retrograde debilitated planet gets significant bonus
        modified_score = base_score + RETROGRADE_BONUS_DEBILITATED
    else:
        # Normal retrograde bonus
        modified_score = base_score + RETROGRADE_BONUS_NORMAL

    # Cap at 100
    return min(modified_score, 100.0)


def apply_combust_penalty(
    base_score: float, is_combust: bool, combust_degree: Optional[float] = None
) -> float:
    """
    Apply combustion penalty to dignity score.

    Planets too close to the Sun lose their ability to express their qualities.

    Args:
        base_score: Base dignity score (0-100)
        is_combust: Whether planet is combust
        combust_degree: Degrees of separation from Sun (optional, for graduated penalty)

    Returns:
        Modified score with combustion penalty applied
    """
    if not is_combust:
        return base_score

    if combust_degree is not None and combust_degree <= COMBUST_ORB_MAJOR:
        # Major combustion (very close to Sun)
        penalty = COMBUST_PENALTY_MAJOR
    else:
        # Minor combustion
        penalty = COMBUST_PENALTY_MINOR

    modified_score = base_score - penalty

    # Floor at 0
    return max(modified_score, 0.0)


def apply_exact_degree_modifiers(
    base_score: float, planet_longitude: float, planet: Planet
) -> float:
    """
    Apply modifiers for planets at exact exaltation or debilitation degrees.

    Args:
        base_score: Base dignity score
        planet_longitude: Planet's longitude in degrees
        planet: Planet enum

    Returns:
        Modified score with exact degree bonuses/penalties
    """
    from .exaltation_matrix import DEBILITATION_TABLE, EXALTATION_TABLE

    modified_score = base_score

    # Check for exact exaltation
    if planet in EXALTATION_TABLE:
        exalt_sign, exalt_deg = EXALTATION_TABLE[planet]
        exalt_longitude = exalt_sign * 30 + exalt_deg

        if abs(planet_longitude - exalt_longitude) <= 0.5:  # Within 0.5°
            modified_score += EXACT_EXALTATION_BONUS

    # Check for exact debilitation
    if planet in DEBILITATION_TABLE:
        debilitation_sign, debilitation_deg = DEBILITATION_TABLE[planet]
        debilitation_longitude = debilitation_sign * 30 + debilitation_deg

        if abs(planet_longitude - debilitation_longitude) <= 0.5:  # Within 0.5°
            modified_score -= EXACT_DEBILITATION_PENALTY

    return max(0.0, min(modified_score, 100.0))


def apply_shadbala_modifiers(
    base_score: float, chart_data: Dict[str, Any], planet: Planet
) -> float:
    """
    Apply Shad Bala (six-fold strength) modifiers.

    This is a simplified implementation of the Shad Bala system.
    Full implementation would require complex calculations.

    Args:
        base_score: Base dignity score
        chart_data: Chart data dictionary
        planet: Planet enum

    Returns:
        Modified score with Shad Bala adjustments
    """
    # This is a placeholder for Shad Bala implementation
    # Full Shad Bala includes:
    # 1. Sthana Bala (Positional strength) - already handled in base_score
    # 2. Dig Bala (Directional strength)
    # 3. Kala Bala (Temporal strength)
    # 4. Chesta Bala (Motional strength) - partially handled by retrograde
    # 5. Naisargika Bala (Natural strength)
    # 6. Drig Bala (Aspect strength)

    # For now, return base score unchanged
    # TODO: Implement full Shad Bala system
    return base_score


def apply_all_modifiers(
    base_score: float,
    planet_data: Dict[str, Any],
    planet: Planet,
    chart_data: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Apply all available modifiers to a dignity score.

    Args:
        base_score: Base dignity score (0-100)
        planet_data: Planet position data from ephemeris
        planet: Planet enum
        chart_data: Full chart data (optional)

    Returns:
        Final modified dignity score (0-100)
    """
    modified_score = base_score

    # Retrograde modifier
    is_retrograde = planet_data.get("retrograde", False)
    is_debilitated = base_score <= 5  # Very low score indicates debilitation

    modified_score = apply_retrograde_bonus(
        modified_score, is_retrograde, is_debilitated
    )

    # Combustion modifier
    is_combust = planet_data.get("combust", False)
    # Calculate angular separation from Sun for graduated penalty
    combust_degree = None
    if "sun_longitude" in planet_data:
        sun_long = planet_data["sun_longitude"]
        planet_long = planet_data["longitude"]
        combust_degree = abs(planet_long - sun_long)
        combust_degree = min(combust_degree, 360 - combust_degree)  # Handle wraparound

    modified_score = apply_combust_penalty(modified_score, is_combust, combust_degree)

    # Exact degree modifiers
    planet_longitude = planet_data.get("longitude", 0)
    modified_score = apply_exact_degree_modifiers(
        modified_score, planet_longitude, planet
    )

    # Shad Bala modifiers (if chart data available)
    if chart_data is not None:
        modified_score = apply_shadbala_modifiers(modified_score, chart_data, planet)

    # Ensure score stays within bounds
    return max(0.0, min(modified_score, 100.0))


def get_modifier_explanation(
    base_score: float, final_score: float, planet_data: Dict[str, Any], planet: Planet
) -> str:
    """
    Generate explanation of how modifiers affected the dignity score.

    Args:
        base_score: Original dignity score
        final_score: Final modified score
        planet_data: Planet position data
        planet: Planet enum

    Returns:
        String explanation of modifiers applied
    """
    explanations = []
    score_change = final_score - base_score

    if abs(score_change) < 0.1:
        return "No significant modifiers applied."

    # Check retrograde
    if planet_data.get("retrograde", False):
        is_debilitated = base_score <= 5
        if is_debilitated:
            explanations.append(
                "Neecha Bhanga: Retrograde debilitated planet gains strength"
            )
        else:
            explanations.append(
                "Retrograde bonus: Planet gains strength in retrograde motion"
            )

    # Check combustion
    if planet_data.get("combust", False):
        explanations.append(
            "Combustion penalty: Planet loses strength due to proximity to Sun"
        )

    # Check exact degrees
    planet_longitude = planet_data.get("longitude", 0)
    from .exaltation_matrix import DEBILITATION_TABLE, EXALTATION_TABLE

    if planet in EXALTATION_TABLE:
        exalt_sign, exalt_deg = EXALTATION_TABLE[planet]
        exalt_longitude = exalt_sign * 30 + exalt_deg
        if abs(planet_longitude - exalt_longitude) <= 0.5:
            explanations.append(
                "Exact exaltation: Additional strength from precise placement"
            )

    if planet in DEBILITATION_TABLE:
        debilitation_sign, debilitation_deg = DEBILITATION_TABLE[planet]
        debilitation_longitude = debilitation_sign * 30 + debilitation_deg
        if abs(planet_longitude - debilitation_longitude) <= 0.5:
            explanations.append(
                "Exact debilitation: Additional weakness from precise placement"
            )

    if explanations:
        return " | ".join(explanations)
    else:
        return f"Score modified by {score_change:+.1f} points (unspecified modifiers)"
