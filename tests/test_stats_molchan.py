"""Tests for Molchan diagrams, binomial bounds and the area skill score."""

import numpy as np
import pytest

from vedic_astrology_core.stats.molchan import (
    area_skill_score,
    binomial_bound,
    molchan_p_value,
    molchan_point,
    molchan_trajectory,
    time_random_reference,
)


def test_point_uses_time_axis():
    """Tau is the fraction of grid steps under alarm; nu the miss fraction."""
    alarm = np.zeros(1000, dtype=int)
    alarm[:100] = 1
    tau, nu = molchan_point(alarm, [5, 50, 500, 900])
    assert tau == pytest.approx(0.1)
    assert nu == pytest.approx(0.5)


def test_trajectory_sorted_ascending_with_end_points():
    """The curve runs from (0, 1) to (1, 0) with tau non-decreasing."""
    score = np.random.default_rng(0).normal(size=500)
    traj = molchan_trajectory(score, [1, 2, 3, 4, 5])
    assert (np.diff(traj["tau"]) >= 0).all()
    assert traj.iloc[0][["tau", "nu"]].tolist() == [0.0, 1.0]
    assert traj.iloc[-1][["tau", "nu"]].tolist() == [1.0, 0.0]


def test_area_skill_score_known_answers_and_order_invariance():
    """Diagonal gives 0.5, perfect gives 1; reversed input gives the same."""
    t = np.linspace(0, 1, 11)
    assert area_skill_score(t, 1 - t) == pytest.approx(0.5)
    assert area_skill_score([0.0, 0.0, 1.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)
    tau = np.array([0.0, 0.2, 0.5, 1.0])
    nu = np.array([1.0, 0.4, 0.2, 0.0])
    assert area_skill_score(tau[::-1], nu[::-1]) == pytest.approx(
        area_skill_score(tau, nu)
    )
    # Bug class: np.interp on a decreasing xp returned garbage.
    assert area_skill_score(tau, nu) == pytest.approx(
        1 - (0.2 * 0.7 + 0.3 * 0.3 + 0.5 * 0.1)
    )


def test_perfect_score_has_high_skill():
    """A score that peaks at every event has ASS near 1."""
    score = np.zeros(1000)
    events = np.arange(0, 1000, 100)
    score[events] = 1.0
    traj = molchan_trajectory(score, events)
    assert area_skill_score(traj["tau"], traj["nu"]) > 0.98


def test_binomial_bound_known_answer():
    """N=10, tau=0.5: P(H>=9)=11/1024 <= 0.05 < P(H>=8), so bound 0.1."""
    assert binomial_bound(10, 0.5)[0] == pytest.approx(0.1)
    bounds = binomial_bound(30, np.linspace(0.01, 0.99, 50))
    assert (np.diff(bounds) <= 1e-12).all()
    assert molchan_p_value(10, 0.5, 0.1) == pytest.approx(11 / 1024)


def test_time_random_reference_centres_on_half():
    """Uniform random events have expected ASS 0.5."""
    score = np.random.default_rng(1).normal(size=2000)
    ref = time_random_reference(
        score, 50, np.random.default_rng(2), n_sims=400, observed_ass=0.9
    )
    assert ref["mean"] == pytest.approx(0.5, abs=0.02)
    assert ref["q025"] < 0.5 < ref["q975"]
    assert ref["p_value"] == pytest.approx(1 / 401)
