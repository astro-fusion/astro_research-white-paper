"""
Dignity Module

Handles planetary dignity calculations including:
- Exaltation/debilitation matrices
- Friendship matrices (Naisargika/Tatkalika Maitri)
- Dignity scoring (0-100 scale)
- Modifiers for retrograde (Neecha Bhanga) and combust
"""

from .exaltation_matrix import DEBILITATION_TABLE, EXALTATION_TABLE, get_exaltation_sign
from .friendship_matrix import NAISARGIKA_MAITRI, calculate_tatkalika_maitri
from .modifiers import apply_combust_penalty, apply_retrograde_bonus
from .scorer import DignityScorer, calculate_base_score, calculate_full_score

__all__ = [
    "DignityScorer",
    "calculate_base_score",
    "calculate_full_score",
    "EXALTATION_TABLE",
    "DEBILITATION_TABLE",
    "get_exaltation_sign",
    "NAISARGIKA_MAITRI",
    "calculate_tatkalika_maitri",
    "apply_retrograde_bonus",
    "apply_combust_penalty",
]
