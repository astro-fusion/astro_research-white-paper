"""
Compatibility constants for `vedic_numerology`.

The canonical Planet enum and PLANET_NAMES live in `vedic_astrology_core.config`.
This module re-exports them so existing docs/tests that reference
`vedic_numerology.config.constants` continue to work.
"""

from vedic_astrology_core.config.constants import PLANET_NAMES, Planet

__all__ = ["Planet", "PLANET_NAMES"]
