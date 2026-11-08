"""Graded rule strength in [0, 1], from the rule's ``strength`` block.

A rule without ``strength`` is binary: 1 while it fires, 0 otherwise. With
``strength`` the value while it fires is the ``combine`` (product, min or
mean) of its terms, each in [0, 1]:

* ``orb_closeness``: ``1 - separation / orb`` (1 at exact conjunction).
* ``aspect_closeness``: ``1 - |separation - angle| / orb``.
* ``dignity_weight``: uccha bala / 60 (BPHS Ch. 27): the arc from the
  planet's deep-debilitation point over 180 degrees, 1 at the paramoccha.
* ``dasha_weight``: 1 when ``lord`` runs the mahadasha, 1/2 the antardasha,
  1/4 the pratyantardasha (the first listed level that matches), else 0.
* ``eclipse_magnitude``: the largest magnitude at greatest eclipse among
  the eclipses in the window, clipped to [0, 1] (Swiss Ephemeris
  ``sol_eclipse_how`` / ``lun_eclipse_how``; 0 for a penumbral-only one).
"""

from typing import List, Tuple

import numpy as np

from ..astrology.combustion import angular_separation
from ..dignity.exaltation_matrix import uccha_bala
from .context import EvalContext
from .tuning import Strength
from .vocabulary import to_planet_enum

LEVEL_WEIGHT = {1: 1.0, 2: 0.5, 3: 0.25}


def _clip(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def term_value(term, ctx: EvalContext) -> Tuple[float, str]:
    """Return (value in [0, 1], plain-words evidence) of one strength term."""
    name = next(iter(type(term).model_fields))
    body = getattr(term, name)
    sky = ctx.sky
    if name == "orb_closeness":
        a, b = body.planets
        sep = angular_separation(sky.lon(a), sky.lon(b))
        v = _clip(1.0 - sep / body.orb)
        return v, f"{a}-{b} {sep:.1f} deg apart, orb {body.orb:g}: {v:.2f}"
    if name == "aspect_closeness":
        a, b = body.planets
        sep = angular_separation(sky.lon(a), sky.lon(b))
        v = _clip(1.0 - abs(sep - body.angle) / body.orb)
        return v, f"{a}-{b} {sep:.1f} deg, {body.angle:g} +/- {body.orb:g}: {v:.2f}"
    if name == "dignity_weight":
        bala = uccha_bala(to_planet_enum(body.planet), sky.lon(body.planet))
        v = _clip(bala / 60.0)
        return v, f"{body.planet} uccha bala {bala:.1f} of 60: {v:.2f}"
    if name == "dasha_weight":
        chain = ctx.dasha_chain(max(body.levels))
        for level in sorted(body.levels):
            if chain[level - 1] == body.lord:
                v = LEVEL_WEIGHT[level]
                return v, f"{body.lord} runs dasha level {level}: {v:.2f}"
        return 0.0, f"{body.lord} runs none of levels {body.levels}: 0.00"
    if name == "eclipse_magnitude":
        from ..astrology.mundane import eclipse_magnitude, magnitude_strength
        from .eclipses import eclipses_between

        found = eclipses_between(
            sky.jd - body.days_before, sky.jd + body.days_after, body.kind
        )
        if not found:
            return 0.0, "no eclipse in the window: 0.00"
        mags = [eclipse_magnitude(e.kind, e.jd) for e in found]
        v = magnitude_strength(max(mags))
        return v, f"largest eclipse magnitude {max(mags):.2f}: {v:.2f}"
    raise ValueError(f"unknown strength term {name}")  # pragma: no cover


def combine(values: List[float], how: str) -> float:
    """Combine term values with product, min or mean."""
    if not values:
        return 1.0
    if how == "product":
        return float(np.prod(values))
    if how == "min":
        return float(min(values))
    return float(np.mean(values))


def strength_value(strength: Strength, ctx: EvalContext) -> Tuple[float, List[str]]:
    """Return the combined strength and the evidence of each term."""
    parts = [term_value(t, ctx) for t in strength.terms]
    return combine([v for v, _ in parts], strength.combine), [w for _, w in parts]


__all__ = ["LEVEL_WEIGHT", "combine", "strength_value", "term_value"]
