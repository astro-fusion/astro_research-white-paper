"""Daily astrological indicator frames computed by the engine.

Everything here comes from :class:`EphemerisEngine` (sidereal Lahiri, mean
node by default) and the combination registry; no plotting or study code
computes positions itself.

Labels are enum *values* such as ``"MOON"`` or ``"Aries"``, never
``str(enum)`` (``"Planet.MOON"``), which once made every nakshatra-lord test
in the gold study all-zero (review item S1-12). Unknown bodies raise.
"""

import logging
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

from ..astrology.ayanamsa import SIGN_NAMES_LIST
from ..astrology.chart import get_nakshatra
from ..astrology.ephemeris import EphemerisEngine
from ..config.constants import Planet, to_planet
from ..dasha.vimshottari import compute_vimshottari_periods

logger = logging.getLogger(__name__)

INDICATOR_KINDS = ("retrograde", "combust", "in_sign", "tithi", "rule", "house")


def resolve_bodies(bodies: Iterable) -> List[Planet]:
    """Resolve body names to :class:`Planet`; any unknown body raises.

    Uranus, Neptune and Pluto are not grahas and are rejected rather than
    silently dropped.
    """
    out = []
    for body in bodies:
        try:
            out.append(to_planet(body))
        except KeyError:
            raise ValueError(
                f"Unknown body {body!r}; expected one of " f"{[p.name for p in Planet]}"
            ) from None
    if not out:
        raise ValueError("no bodies requested")
    return out


def _tithi(sun_lon: float, moon_lon: float) -> int:
    """Tithi 1-30 from the Moon-Sun elongation (12 degrees each)."""
    return int(((moon_lon - sun_lon) % 360.0) // 12.0) + 1


def indicator_frame(
    instants: Sequence[datetime],
    bodies: Iterable,
    engine: Optional[EphemerisEngine] = None,
    lagna_sign: Optional[int] = None,
    natal: Optional[Dict] = None,
    rules_use_case: Optional[str] = None,
) -> pd.DataFrame:
    """Per-instant planetary state for ``bodies``.

    Args:
        instants: timezone-aware instants (naive datetimes raise in the
            engine), usually from :func:`.align.sample_instants`.
        bodies: planet names or :class:`Planet` members.
        engine: ephemeris engine (default: Lahiri, mean node).
        lagna_sign: 0-11 sign of a reference ascendant; adds whole-sign
            ``<BODY>_house`` columns (1-12).
        natal: ``{"birth": aware datetime, "moon_longitude": float}`` adds
            ``dasha_lord`` (Vimshottari mahadasha lord, enum name).
        rules_use_case: if given, adds ``rule:<name>`` columns from the
            combination registry (see :func:`rule_firings`).

    Returns:
        DataFrame indexed by the instants with, per body ``B``:
        ``B_lon``, ``B_sign``, ``B_nakshatra``, ``B_nak_lord``, ``B_retro``,
        ``B_combust`` (and ``B_house``); plus ``tithi`` when Sun and Moon
        are both requested.
    """
    planets = resolve_bodies(bodies)
    engine = engine or EphemerisEngine()
    index = pd.DatetimeIndex(instants)
    if index.tz is None:
        raise ValueError("instants must be timezone-aware")
    rows = []
    for ts in index:
        positions = engine.get_all_planet_positions(
            engine.datetime_to_julian_day(ts.to_pydatetime())
        )
        row = {}
        for p in planets:
            pos = positions[p]
            nak = get_nakshatra(pos["longitude"])
            key = p.name
            row[f"{key}_lon"] = pos["longitude"]
            row[f"{key}_sign"] = SIGN_NAMES_LIST[pos["sign"]]
            row[f"{key}_nakshatra"] = nak["name"]
            row[f"{key}_nak_lord"] = to_planet(nak["lord"]).name
            row[f"{key}_retro"] = bool(pos["retrograde"])
            row[f"{key}_combust"] = bool(pos["combust"])
            if lagna_sign is not None:
                row[f"{key}_house"] = (pos["sign"] - int(lagna_sign)) % 12 + 1
        if Planet.SUN in planets and Planet.MOON in planets:
            row["tithi"] = _tithi(
                positions[Planet.SUN]["longitude"], positions[Planet.MOON]["longitude"]
            )
        rows.append(row)
    frame = pd.DataFrame(rows, index=index)
    if natal is not None:
        frame["dasha_lord"] = dasha_lords(index, natal)
    if rules_use_case is not None:
        firings = rule_firings(index, rules_use_case, engine)
        frame = frame.join(firings)
        frame.attrs.update(firings.attrs)
    return frame


def dasha_lords(index: pd.DatetimeIndex, natal: Dict) -> List[str]:
    """Vimshottari mahadasha lord (enum name) at each instant."""
    periods = compute_vimshottari_periods(
        natal["birth"], natal["moon_longitude"], total_years=240
    )
    out = []
    for ts in index:
        t = ts.to_pydatetime()
        lord = next((p.lord for p in periods if p.start <= t < p.end), None)
        if lord is None:
            raise ValueError(f"{t} lies outside the computed dasha span")
        out.append(to_planet(lord).name)
    return out


def rule_firings(
    index: pd.DatetimeIndex,
    use_case: str = "financial",
    engine: Optional[EphemerisEngine] = None,
) -> pd.DataFrame:
    """``rule:<name>`` boolean columns from the combination registry.

    The registry is mid-migration to ``rules/**.yaml``; the import is isolated
    here, and if it fails the frame is empty with ``attrs["rules_skipped"]``
    set and a logged warning, so callers can report what was not evaluated.
    """
    try:
        from ..combinations import CombinationEvaluator, get_registry

        rules = get_registry().get_rules_by_usecase(use_case)
        evaluator = CombinationEvaluator(engine or EphemerisEngine(), rules)
        rows = []
        for ts in index:
            res = evaluator.evaluate_date(ts.to_pydatetime())
            rows.append({f"rule:{k}": bool(v["is_active"]) for k, v in res.items()})
    except Exception as exc:  # registry API mid-change: skip, never guess
        reason = f"{type(exc).__name__}: {exc}"
        logger.warning("rule firings skipped (%s)", reason)
        empty = pd.DataFrame(index=index)
        empty.attrs["rules_skipped"] = reason
        return empty
    frame = pd.DataFrame(rows, index=index)
    frame.attrs["rules_evaluated"] = sorted(frame.columns)
    return frame


def build_indicators(frame: pd.DataFrame, specs: Sequence[Dict]) -> pd.DataFrame:
    """Boolean indicator columns from declarative specs (hypothesis.yaml).

    Spec kinds: ``retrograde``/``combust`` (``body``), ``in_sign`` (``body``,
    ``signs``), ``house`` (``body``, ``houses``), ``tithi`` (``tithis``) and
    ``rule`` (``rule``: registry rule name). An unknown kind, a missing
    column or an indicator that is never active raises.
    """
    out = pd.DataFrame(index=frame.index)
    for spec in specs:
        kind, ident = spec.get("kind"), spec["id"]
        if kind not in INDICATOR_KINDS:
            raise ValueError(f"{ident}: unknown indicator kind {kind!r}")
        body = to_planet(spec["body"]).name if "body" in spec else None
        if kind == "retrograde":
            values = frame[f"{body}_retro"]
        elif kind == "combust":
            values = frame[f"{body}_combust"]
        elif kind == "in_sign":
            values = frame[f"{body}_sign"].isin(spec["signs"])
        elif kind == "house":
            values = frame[f"{body}_house"].isin(spec["houses"])
        elif kind == "tithi":
            values = frame["tithi"].isin(spec["tithis"])
        else:
            column = f"rule:{spec['rule']}"
            if column not in frame.columns:
                raise KeyError(f"{ident}: registry rule {spec['rule']!r} not evaluated")
            values = frame[column]
        values = np.asarray(values, dtype=bool)
        if not values.any():
            raise ValueError(f"{ident}: indicator is never active in the sample")
        out[ident] = values
    return out
