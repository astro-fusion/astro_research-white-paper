"""Placebo skies and ayanamsa sensitivity for indicator tests (ADR-004 WP-07).

A real-sky statistic means little until it is ranked against skies that carry
no astrology but share the same indicator machinery. Three placebo kinds:

* ``shift`` -- the sky of another date: the indicator at instant ``t`` is
  computed at ``t + offset`` (at least 400 days, either direction), so run
  structure and slow cycles are kept and only the alignment with the outcome
  is broken. Note that a shift that is close to a planet's period (for
  example about 29.5 years for Saturn) re-creates part of the real sky; the
  400 day floor is the ADR minimum, not a guarantee against that.
* ``tropical`` -- the same planets read in the tropical zodiac (sign and
  nakshatra recomputed from longitude plus the true Lahiri ayanamsa; houses
  only when the lagna's longitude is given, see :func:`rezodiac`).
  Retrograde, combustion and tithi do not depend on the zodiac and are
  unchanged. The tropical zodiac is a rival system, so this one deterministic
  draw is better read as a sensitivity variant than as a placebo.
* ``scramble`` -- sign (and whole-sign house) labels permuted at random, one
  permutation per placebo; nakshatra columns are left alone.

:func:`placebo_skies` returns, per kind, the rank of the real sky's largest
statistic among the placebos, and per indicator the rank of that
indicator's own statistic (strategy audit A-01: R2 is per test). The
p-value is ``rank / (n + 1)``, so it can never be zero. Ties are mid-ranked
(a placebo equal to the real sky counts one half), and a placebo that leaves
an indicator unchanged is dropped for that indicator: a placebo kind that
changes nothing is "not applicable", never "failed". So nakshatra, tithi,
retrograde and combustion indicators, which scrambling sign labels or the
tropical zodiac do not touch, are judged by the placebos that do move them.
The statistic is supplied by the caller (a function from the boolean
indicator frame to ``{indicator_id: non-negative statistic}``), so the whole
selection step is repeated on every placebo as ADR-005 requires.

:func:`ayanamsa_sensitivity` rebuilds indicators under other ayanamsas and
counts the bars that change. Positions are shifted by the difference of the
mean ayanamsas, so only one ephemeris pass is needed. Exception:
``true_chitrapaksha`` (``SIDM_TRUE_CITRA``) is a true ayanamsa and already
contains nutation, so its delta against the mean base carries up to about
17 arcseconds of nutation (code audit m7). That is far below a sign or
nakshatra boundary width and changes at most a bar that sits within 17
arcseconds of a boundary. ``rule:`` columns come from the combination
registry and are not rebuilt; this is reported.
"""

from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd
import swisseph as swe

from ..astrology.ayanamsa import (
    SIGN_NAMES_LIST,
    AyanamsaSystem,
    ayanamsa_mean,
    ayanamsa_true,
    resolve_ayanamsa_system,
)
from ..astrology.chart import get_nakshatra
from ..astrology.ephemeris import EphemerisEngine
from ..config.constants import to_planet
from . import features

MIN_OFFSET_DAYS = 400
PLACEBO_KINDS = ("shift", "tropical", "scramble")
AYANAMSA_VARIANTS = ("lahiri", "raman", "krishnamurti", "true_chitrapaksha")

Statistic = Callable[[pd.DataFrame], Mapping[str, float]]


def _mean_ayanamsa(jd: float, system: str) -> float:
    """Mean ayanamsa in degrees; ``true_chitrapaksha`` is SIDM_TRUE_CITRA.

    SIDM_TRUE_CITRA is a true ayanamsa: it includes nutation (up to about 17
    arcseconds), unlike the other three. See the module docstring.
    """
    if system == "true_chitrapaksha":
        swe.set_sid_mode(swe.SIDM_TRUE_CITRA, 0.0, 0.0)
        return float(swe.get_ayanamsa_ut(jd))
    return ayanamsa_mean(jd, resolve_ayanamsa_system(system))


def _bodies_in(frame: pd.DataFrame) -> List[str]:
    return [c[: -len("_lon")] for c in frame.columns if c.endswith("_lon")]


def rezodiac(
    frame: pd.DataFrame,
    delta_deg,
    lagna_sign: Optional[int] = None,
    lagna_lon: Optional[float] = None,
) -> pd.DataFrame:
    """Return a copy of ``frame`` with longitudes moved by ``delta_deg``.

    ``delta_deg`` is a scalar or one value per row (new = old + delta, mod
    360). ``_lon``, ``_sign``, ``_nakshatra`` and ``_nak_lord`` are recomputed.

    Houses (code audit m6): the lagna moves with the same delta. With
    ``lagna_lon`` (the lagna's longitude in the frame's zodiac) ``_house`` is
    recomputed from the moved lagna. With only ``lagna_sign`` the lagna's
    degree is unknown, so its new sign is unknown too; ``_house`` is then
    kept, because planets and lagna rotate together and whole-sign houses
    do not change except near a boundary. Never are planets of one zodiac
    counted from the lagna of another. Everything else is kept.
    """
    out = frame.copy()
    delta = np.broadcast_to(np.asarray(delta_deg, dtype=float), (len(frame),))
    new_lagna = None
    if lagna_lon is not None:
        new_lagna = (((float(lagna_lon) + delta) % 360.0) // 30.0).astype(int)
    for key in _bodies_in(frame):
        lon = (frame[f"{key}_lon"].to_numpy(dtype=float) + delta) % 360.0
        signs = (lon // 30.0).astype(int)
        naks = [get_nakshatra(float(x)) for x in lon]
        out[f"{key}_lon"] = lon
        out[f"{key}_sign"] = [SIGN_NAMES_LIST[s] for s in signs]
        out[f"{key}_nakshatra"] = [n["name"] for n in naks]
        out[f"{key}_nak_lord"] = [to_planet(n["lord"]).name for n in naks]
        if new_lagna is not None and f"{key}_house" in frame.columns:
            out[f"{key}_house"] = (signs - new_lagna) % 12 + 1
    return out


def scramble_signs(
    frame: pd.DataFrame, rng: np.random.Generator, lagna_sign: Optional[int] = None
) -> pd.DataFrame:
    """Return a copy with sign labels permuted by one random permutation.

    The same permutation is used for every body. Whole-sign houses are
    recomputed from the permuted sign when ``lagna_sign`` is given.
    """
    perm = rng.permutation(12)
    index_of = {name: i for i, name in enumerate(SIGN_NAMES_LIST)}
    out = frame.copy()
    for key in _bodies_in(frame):
        new = np.array([perm[index_of[s]] for s in frame[f"{key}_sign"]])
        out[f"{key}_sign"] = [SIGN_NAMES_LIST[i] for i in new]
        if lagna_sign is not None and f"{key}_house" in frame.columns:
            out[f"{key}_house"] = (new - int(lagna_sign)) % 12 + 1
    return out


def shift_offsets(
    n: int,
    rng: np.random.Generator,
    min_days: int = MIN_OFFSET_DAYS,
    max_days: int = 3650,
) -> np.ndarray:
    """Return ``n`` distinct day offsets with ``min_days <= |offset| <= max_days``.

    Both signs are admissible. Raises if fewer than ``n`` distinct offsets exist
    or ``min_days`` is below the ADR minimum of 400.
    """
    if min_days < MIN_OFFSET_DAYS:
        raise ValueError(f"placebo offsets must be at least {MIN_OFFSET_DAYS} days")
    pool = np.concatenate(
        [np.arange(min_days, max_days + 1), -np.arange(min_days, max_days + 1)]
    )
    if n > len(pool):
        raise ValueError(f"only {len(pool)} distinct offsets exist, {n} requested")
    return rng.choice(pool, size=n, replace=False)


def shifted_sky_frame(
    instants: pd.DatetimeIndex,
    offset_days: int,
    frame_builder: Callable[[pd.DatetimeIndex], pd.DataFrame],
) -> pd.DataFrame:
    """Build the frame of the sky ``offset_days`` away, indexed by ``instants``."""
    if abs(int(offset_days)) < MIN_OFFSET_DAYS:
        raise ValueError(f"placebo offsets must be at least {MIN_OFFSET_DAYS} days")
    other = pd.DatetimeIndex(instants) + pd.Timedelta(days=int(offset_days))
    frame = frame_builder(other)
    frame.index = pd.DatetimeIndex(instants)
    return frame


def rank_of_real(
    real_max: float,
    placebo_max: Sequence[float],
    ties: str = "mid",
    rng: Optional[np.random.Generator] = None,
    tol: float = 1e-12,
) -> Dict[str, float]:
    """Rank of the real statistic among placebo statistics (1 = larger than all).

    ``rank = 1 + #(placebo > real) + tie share``; ``p = rank / (n + 1)``.
    Ties (within ``tol``, relative) do not all count against the real sky
    (strategy audit A-01): ``ties="mid"`` counts each tie one half (mid-rank),
    ``ties="random"`` breaks them at random with ``rng``, ``ties="against"``
    is the old rule (every tie counts against the real sky).
    """
    arr = np.asarray(list(placebo_max), dtype=float)
    if arr.size == 0:
        raise ValueError("no placebo statistics")
    real = float(real_max)
    eps = tol * max(1.0, abs(real))
    n_greater = int((arr > real + eps).sum())
    n_tied = int((np.abs(arr - real) <= eps).sum())
    if ties == "mid":
        rank = 1 + n_greater + n_tied / 2.0
    elif ties == "random":
        if rng is None:
            raise ValueError("ties='random' needs an rng")
        rank = 1 + n_greater + int(rng.integers(0, n_tied + 1))
    elif ties == "against":
        rank = 1 + n_greater + n_tied
    else:
        raise ValueError(f"unknown ties rule {ties!r}")
    return {
        "real_max": real,
        "n_placebo": int(arr.size),
        "n_greater": n_greater,
        "n_tied": n_tied,
        "ties": ties,
        "rank": rank,
        "p_value": rank / (arr.size + 1),
    }


def _not_applicable(n_drawn: int, why: str) -> Dict:
    return {"applicable": False, "rank": None, "p_value": None, "n_placebo": n_drawn,
            "n_used": 0, "reason": why}


def _max_stat(statistic: Statistic, indicators: pd.DataFrame) -> float:
    stats = statistic(indicators)
    if not stats:
        raise ValueError("statistic returned no values")
    return float(max(stats.values()))


def placebo_skies(
    instants: pd.DatetimeIndex,
    bodies: Iterable,
    specs: Sequence[Dict],
    statistic: Statistic,
    n_placebo: int = 200,
    kinds: Sequence[str] = PLACEBO_KINDS,
    seed: int = 0,
    engine: Optional[EphemerisEngine] = None,
    lagna_sign: Optional[int] = None,
    min_offset_days: int = MIN_OFFSET_DAYS,
    max_offset_days: int = 3650,
    frame_builder: Optional[Callable[[pd.DatetimeIndex], pd.DataFrame]] = None,
    base_frame: Optional[pd.DataFrame] = None,
    ties: str = "mid",
    lagna_lon: Optional[float] = None,
) -> Dict:
    """Rank the real sky's largest statistic among placebo skies.

    Args:
        instants: timezone-aware instants of the study bars.
        bodies: bodies for the frame.
        specs: indicator specs (``features.build_indicators``).
        statistic: indicator frame -> ``{id: statistic}``, larger = more
            extreme (use absolute values). The maximum over indicators is
            compared; an indicator that is never active in a placebo sky
            counts as zero.
        n_placebo: placebos per kind.
        kinds: any of ``shift``, ``tropical``, ``scramble``.
        seed: seeds offsets and permutations.
        frame_builder / base_frame: injection points (tests, caching); by
            default the engine builds frames with ``features.indicator_frame``.
        ties: tie rule of :func:`rank_of_real` (default mid-rank).
        lagna_lon: the lagna's longitude, so the tropical placebo can move
            the lagna too; without it house columns are kept (see
            :func:`rezodiac`).

    Returns:
        ``{"real": {id: stat}, "real_max": float, "kinds": {kind: {...rank,
        p_value, applicable, n_used, placebo_max, per_indicator: {id:
        {rank, p_value, applicable, ...}}}}}``; shift also lists
        ``offsets_days``. A placebo identical to the real sky for an
        indicator is dropped for it; with none left the entry is
        ``applicable: False`` with rank and p None.
    """
    bad = [k for k in kinds if k not in PLACEBO_KINDS]
    if bad:
        raise ValueError(f"unknown placebo kinds {bad}; expected {PLACEBO_KINDS}")
    index = pd.DatetimeIndex(instants)
    bodies = list(bodies)
    engine = engine or EphemerisEngine()
    rng = np.random.default_rng(int(seed))
    if frame_builder is None:

        def frame_builder(inst):
            return features.indicator_frame(
                inst, bodies, engine, lagna_sign=lagna_sign
            )

    real_frame = base_frame if base_frame is not None else frame_builder(index)
    real_ind = features.build_indicators(real_frame, specs)
    real = dict(statistic(real_ind))
    real_max = float(max(real.values()))
    ids = [spec["id"] for spec in specs]

    def lenient(frame: pd.DataFrame) -> pd.DataFrame:
        cols = {}
        for spec in specs:
            try:
                cols[spec["id"]] = features.build_indicators(frame, [spec])[spec["id"]]
            except ValueError as exc:
                if "never active" not in str(exc):
                    raise
                cols[spec["id"]] = pd.Series(False, index=frame.index)
        return pd.DataFrame(cols, index=frame.index)

    def one(frame: pd.DataFrame):
        ind = lenient(frame)
        stats = statistic(ind)
        if not stats:
            raise ValueError("statistic returned no values")
        changed = {
            i: not np.array_equal(ind[i].to_numpy(bool), real_ind[i].to_numpy(bool))
            for i in ids
        }
        return dict(stats), changed

    result: Dict = {"real": real, "real_max": real_max, "kinds": {},
                    "ties": ties, "houses": "recomputed" if lagna_lon is not None else "kept"}
    for kind in kinds:
        extra: Dict = {}
        if kind == "shift":
            offsets = shift_offsets(n_placebo, rng, min_offset_days, max_offset_days)
            draws = [one(shifted_sky_frame(index, int(o), frame_builder)) for o in offsets]
            extra["offsets_days"] = [int(o) for o in offsets]
        elif kind == "tropical":
            jds = [engine.datetime_to_julian_day(t.to_pydatetime()) for t in index]
            delta = [ayanamsa_true(jd, AyanamsaSystem.LAHIRI) for jd in jds]
            # One deterministic draw: a rival zodiac, reported as a variant.
            draws = [one(rezodiac(real_frame, delta, lagna_sign, lagna_lon))]
            extra["deterministic"] = True
            extra["role"] = "variant"
        else:
            draws = [one(scramble_signs(real_frame, rng, lagna_sign)) for _ in range(n_placebo)]
        # Max over indicators, among the placebos that change at least one.
        moved = [s for s, ch in draws if any(ch.values())]
        if moved:
            entry = rank_of_real(real_max, [max(s.values()) for s in moved], ties, rng)
            entry["applicable"] = True
            entry["n_used"] = len(moved)
        else:
            entry = _not_applicable(len(draws), "no placebo of this kind changes any indicator")
        entry["n_placebo"] = len(draws)
        entry["n_identical_dropped"] = len(draws) - len(moved)
        entry["placebo_max"] = [float(max(s.values())) for s, _ in draws]
        # Per indicator: that indicator's statistic, placebos that move it.
        per: Dict[str, Dict] = {}
        for i in ids:
            vals = [float(s.get(i, 0.0)) for s, ch in draws if ch[i]]
            if not vals:
                per[i] = _not_applicable(len(draws), f"{kind} does not change this indicator")
                continue
            r = rank_of_real(float(real.get(i, 0.0)), vals, ties, rng)
            r.update(applicable=True, n_used=len(vals), n_placebo=len(draws))
            per[i] = r
        entry["per_indicator"] = per
        entry.update(extra)
        result["kinds"][kind] = entry
    return result


def ayanamsa_sensitivity(
    frame: pd.DataFrame,
    specs: Sequence[Dict],
    variants: Sequence[str] = AYANAMSA_VARIANTS,
    base: str = "lahiri",
    instants: Optional[pd.DatetimeIndex] = None,
    engine: Optional[EphemerisEngine] = None,
    lagna_sign: Optional[int] = None,
    lagna_lon: Optional[float] = None,
) -> Dict:
    """Count the bars whose indicators change under other ayanamsas.

    ``frame`` must come from an engine using the ``base`` ayanamsa. Returns
    ``{"n_bars", "base", "rules_not_rebuilt", "variants": {name: {"bars_changed":
    {id: n}, "any_changed": n, "active_base": {id: n}, "active_variant":
    {id: n}}}}``. An indicator that is never active under a variant counts as
    all-false rather than raising.
    """
    index = pd.DatetimeIndex(instants if instants is not None else frame.index)
    engine = engine or EphemerisEngine(base)
    jds = [engine.datetime_to_julian_day(t.to_pydatetime()) for t in index]

    def build(fr: pd.DataFrame) -> pd.DataFrame:
        cols = {}
        for spec in specs:
            try:
                cols[spec["id"]] = features.build_indicators(fr, [spec])[spec["id"]]
            except ValueError as exc:
                if "never active" not in str(exc):
                    raise
                cols[spec["id"]] = np.zeros(len(fr), dtype=bool)
        return pd.DataFrame(cols, index=fr.index)

    base_ind = build(frame)
    out: Dict = {
        "n_bars": int(len(index)),
        "base": base,
        "rules_not_rebuilt": [s["id"] for s in specs if s.get("kind") == "rule"],
        "variants": {},
    }
    for name in variants:
        delta = [_mean_ayanamsa(jd, base) - _mean_ayanamsa(jd, name) for jd in jds]
        ind = build(rezodiac(frame, delta, lagna_sign, lagna_lon))
        changed = base_ind.to_numpy() != ind.to_numpy()
        out["variants"][name] = {
            "bars_changed": {
                c: int(changed[:, i].sum()) for i, c in enumerate(base_ind.columns)
            },
            "any_changed": int(changed.any(axis=1).sum()),
            "active_base": {c: int(base_ind[c].sum()) for c in base_ind.columns},
            "active_variant": {c: int(ind[c].sum()) for c in ind.columns},
        }
    return out
