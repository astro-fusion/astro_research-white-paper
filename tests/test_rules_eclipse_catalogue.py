"""Eclipse catalogue and ingress shortcut: faster, and equal to the direct computation.

Strategy audit 2 diagnosis (DIAG, item 3): ``eclipse_window`` and ``sun_ingress``
took hours on the hourly earthquake grid because every grid step ran its own
Swiss Ephemeris eclipse search (about 7 ms a step) or a half-day ingress scan.
rules/eclipses.py now reads a catalogue and the ingress predicate skips the
scan when no crossing is possible. Both must give exactly what the direct
computation gives: same eclipses (same floats), same held flag, same text.
"""

from __future__ import annotations

import random
import time
from datetime import timezone

import pytest

from vedic_astrology_core.rules import eclipses as E
from vedic_astrology_core.rules.context import EvalContext, Sky
from vedic_astrology_core.rules.predicates import Outcome
from vedic_astrology_core.rules.predicates import mundane as M
from vedic_astrology_core.rules.predicates import samhita as S
from vedic_astrology_core.rules.vocabulary import SIGN_NAMES
from vedic_astrology_core.utils.datetime_utils import julian_day_to_datetime

J1976, J2011 = 2442778.5, 2455562.5  # the earthquake grid's span


# ------------------------------------------------------------- references
def old_eclipses_between(jd_start, jd_end, kind="any"):
    """The function as it was: one direct chained search per window."""
    kinds = ("solar", "lunar") if kind == "any" else (kind,)
    out = []
    for k in kinds:
        out.extend(E._search.__wrapped__(round(jd_start, 6), round(jd_end, 6), k))
    return sorted(out, key=lambda e: e.jd)


def old_ingress(ctx, p):
    """The ingress predicate as it was (always the half-day scan)."""
    engine = ctx.sky.engine
    jd0 = ctx.sky.jd - p.days_before
    jd1 = ctx.sky.jd + p.days_after
    body = p.planet.upper()

    def sign_at(jd):
        return int(engine.get_planet_position(jd, body)["longitude"] // 30)

    step = M._step_days(p.planet)
    crossings = []
    t, s = jd0, sign_at(jd0)
    while t < jd1:
        t2 = min(t + step, jd1)
        s2 = sign_at(t2)
        if s2 != s:
            lo, hi = t, t2
            for _ in range(20):
                mid = (lo + hi) / 2
                if sign_at(mid) == s:
                    lo = mid
                else:
                    hi = mid
            crossings.append((hi, s2))
        t, s = t2, s2
    window = M._window(p.days_before, p.days_after)
    if not crossings:
        return Outcome(False, f"{p.planet} stays in {SIGN_NAMES[s]} {window} the moment (no ingress)")
    words = []
    held = False
    for jd, sign in crossings:
        name = SIGN_NAMES[sign]
        when = julian_day_to_datetime(jd)
        words.append(f"{p.planet} enters {name} at {when:%Y-%m-%d %H:%M} UT")
        held = held or p.signs is None or name in p.signs
    wanted = f"; wanted {', '.join(p.signs)}" if p.signs else ""
    return Outcome(held, f"{'; '.join(words)} ({window}){wanted}")


def _ctx(jd: float) -> EvalContext:
    return EvalContext(Sky(julian_day_to_datetime(jd).replace(tzinfo=timezone.utc)))


# ------------------------------------------------------------- eclipses
def _windows(n: int, seed: int):
    rng = random.Random(seed)
    for _ in range(n):
        s = rng.uniform(J1976 - 36525.0, J2011 + 36525.0)  # placebo shifts reach a century
        yield s, s + rng.choice([0.5, 2.0, 14.0, 60.0, 400.0, 900.0])


@pytest.mark.parametrize("kind", ["solar", "lunar", "any"])
def test_catalogue_equals_direct_search_on_random_windows(kind):
    for s, e in _windows(150, seed={"solar": 1, "lunar": 2, "any": 3}[kind]):
        assert E.eclipses_between(s, e, kind) == old_eclipses_between(s, e, kind), (s, e, kind)


def test_catalogue_equals_direct_search_at_block_edges_and_peaks():
    peaks = [ecl.jd for ecl in old_eclipses_between(J1976, J1976 + 1.5 * 365.25, "any")]
    anchors = [E._BLOCK_EPOCH + i * E._BLOCK_DAYS for i in range(-6, 2)]
    starts = []
    for x in peaks + anchors + [a + 1.0 for a in anchors]:
        starts += [x + d for d in (-1.0, -0.02, -0.011, -0.0101, -1e-3, -1e-4, -1e-5, 0.0,
                                   1e-5, 1e-4, 1e-3, 0.0101, 0.011, 0.02, 1.0)]
    for s in starts:
        for span in (0.0, 1.0, 30.0):
            for kind in ("solar", "lunar", "any"):
                assert E.eclipses_between(s, s + span, kind) == old_eclipses_between(s, s + span, kind), \
                    (s, span, kind)


def test_catalogue_window_ends_are_inclusive_like_the_search():
    ecl = old_eclipses_between(J1976, J1976 + 400.0, "solar")[0]
    assert E.eclipses_between(ecl.jd - 3.0, ecl.jd, "solar") == [ecl]
    assert E.eclipses_between(ecl.jd - 3.0, ecl.jd - 1e-5, "solar") == []  # windows are rounded to 1e-6 day
    for e in (ecl.jd, ecl.jd - 1e-6, ecl.jd - 1e-5, ecl.jd + 1e-6):
        assert E.eclipses_between(ecl.jd - 3.0, e, "solar") == old_eclipses_between(ecl.jd - 3.0, e, "solar")


@pytest.mark.parametrize("params", [
    {"kind": "any", "days_before": 7, "days_after": 7, "penumbral": False},
    {"kind": "any", "days_before": 30, "days_after": 30, "pair_within_days": 16},
    {"kind": "solar", "days_before": 15, "days_after": 0, "min_magnitude": 0.5},
])
def test_eclipse_within_days_outcome_unchanged(params, monkeypatch):
    p = S.EclipseWithin(**params)
    rng = random.Random(7)
    jds = [rng.uniform(J1976, J2011) for _ in range(150)]
    new = [S.eclipse_within_days(_ctx(jd), p) for jd in jds]
    monkeypatch.setattr(S, "eclipses_between", old_eclipses_between)
    old = [S.eclipse_within_days(_ctx(jd), p) for jd in jds]
    assert [(o.held, o.evidence) for o in new] == [(o.held, o.evidence) for o in old]
    assert any(o.held for o in new) and not all(o.held for o in new)


def test_eclipse_in_sign_outcome_unchanged(monkeypatch):
    p = M.EclipseInSign(kind="any", signs=["Leo", "Aquarius"], days_before=15, days_after=15)
    jds = [J1976 + 3.7 * i for i in range(300)]
    new = [M.eclipse_in_sign(_ctx(jd), p) for jd in jds]
    monkeypatch.setattr(M, "eclipses_between", old_eclipses_between)
    old = [M.eclipse_in_sign(_ctx(jd), p) for jd in jds]
    assert [(o.held, o.evidence) for o in new] == [(o.held, o.evidence) for o in old]


def test_hourly_eclipse_window_is_fast():
    """Before: about 7 ms per hourly step; the 1976-2010 grid (445,608 steps) took about 50 minutes."""
    p = S.EclipseWithin(kind="any", days_before=7, days_after=7, penumbral=False)
    E.eclipses_between(J1976 + 400.0, J1976 + 420.0)  # build the blocks once
    ctxs = [_ctx(J1976 + 400.0 + h / 24.0) for h in range(2000)]
    t = time.perf_counter()
    for c in ctxs:
        S.eclipse_within_days(c, p)
    per_step = (time.perf_counter() - t) / len(ctxs)
    assert per_step < 1e-3, f"{per_step * 1e3:.2f} ms per hourly step"


# ------------------------------------------------------------- ingress
@pytest.mark.parametrize("planet,days", [("Sun", 2.0), ("Sun", 0.0), ("Sun", 14.0), ("Moon", 0.5),
                                         ("Moon", 0.9), ("Mars", 2.0), ("Mercury", 3.0)])
def test_ingress_outcome_unchanged(planet, days):
    rng = random.Random(hash((planet, days)) & 0xFFFF)
    p = M.Ingress(planet=planet, days_before=days, days_after=days)
    q = M.Ingress(planet=planet, signs=["Aries", "Libra"], days_before=days, days_after=days / 2)
    jds = [rng.uniform(J1976, J2011) for _ in range(250)]
    # and steps right around a crossing, where the shortcut must not decide
    jds += [J1976 + 30.0 + h / 24.0 for h in range(0, 24 * 40, 7)]
    for jd in jds:
        c = _ctx(jd)
        for par in (p, q):
            a, b = M.ingress(c, par), old_ingress(c, par)
            assert (a.held, a.evidence) == (b.held, b.evidence), (planet, days, jd)


def test_ingress_shortcut_skips_the_scan(monkeypatch):
    calls = []
    c = _ctx(J1976 + 10.0)
    eng = c.sky.engine
    orig = eng.get_planet_position

    def spy(jd, body, *a, **k):
        calls.append(jd)
        return orig(jd, body, *a, **k)

    monkeypatch.setattr(eng, "get_planet_position", spy)
    p = M.Ingress(planet="Sun", days_before=2, days_after=2)
    out = M.ingress(c, p)
    assert not out.held and "stays in" in out.evidence
    assert len(calls) == 2  # was 9 (the start and eight half-day steps)
