"""
Vedic Numerology + Astrology integration layer.

This package provides a thin integration between:
- `vedic_astrology_core` (astrological calculations, dignity scoring, ephemeris)
- Vedic numerology (Mulanka/Bhagyanka + planetary mapping)

It exists because the repository and docs/tests reference `vedic_numerology`,
while the core library lives in `vedic_astrology_core`.
"""

from .analysis import VedicNumerologyAstrology, analyze_birth_chart

__all__ = ["VedicNumerologyAstrology", "analyze_birth_chart"]
