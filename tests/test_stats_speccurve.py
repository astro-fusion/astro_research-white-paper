"""Tests for the specification curve with a joint circular-shift p-value."""

import numpy as np
import pytest

from vedic_astrology_core.stats.speccurve import specification_curve


def _make(n, effect, rng):
    """Build the make fixture."""
    window = np.zeros(n, dtype=bool)
    for start in range(0, n, 200):
        window[start : start + 20] = True
    base = 0.01
    rate = np.where(window, base * effect, base)
    events = np.flatnonzero(rng.random(n) < rate)
    return window, events


def _estimator(window, events, n):
    """Build the estimator fixture."""

    def est(spec, shift):
        w = np.roll(window, spec["lag"])
        if spec["widen"]:
            w = w | np.roll(w, 5)
        ev = (events + shift) % n
        n_in = w[ev].sum()
        t_in = w.sum()
        rr = (n_in / t_in) / ((len(ev) - n_in) / (n - t_in))
        se = np.sqrt(1 / max(n_in, 1) + 1 / max(len(ev) - n_in, 1))
        return {
            "estimate": rr,
            "ci_low": rr * np.exp(-1.96 * se),
            "ci_high": rr * np.exp(1.96 * se),
        }

    return est


def test_curve_shape_and_sorting():
    """Check curve shape and sorting."""
    rng = np.random.default_rng(0)
    n = 20000
    w, ev = _make(n, 4.0, rng)
    res = specification_curve(
        _estimator(w, ev, n),
        {"lag": [0, 1, 2], "widen": [False, True]},
        np.random.default_rng(1),
        n=n,
        min_shift=500,
        n_draws=99,
    )
    f = res.frame
    assert len(f) == 6
    assert list(f.columns[:2]) == ["lag", "widen"]
    assert (np.diff(f["estimate"].to_numpy()) >= 0).all()
    assert f["rank"].tolist() == list(range(1, 7))
    assert res.share_excluding_null == pytest.approx(1.0)
    assert res.p_median == pytest.approx(1 / 100)


def test_null_effect_is_not_significant():
    """Check null effect is not significant."""
    rng = np.random.default_rng(2)
    n = 20000
    w, ev = _make(n, 1.0, rng)
    res = specification_curve(
        _estimator(w, ev, n),
        {"lag": [0, 3], "widen": [False, True]},
        np.random.default_rng(3),
        n=n,
        min_shift=500,
        n_draws=99,
    )
    assert res.p_median > 0.05
    assert 0.0 <= res.share_excluding_null <= 1.0
    assert len(res.null_medians) == 99


def test_rejects_empty_grid():
    """Check rejects empty grid."""
    with pytest.raises(ValueError):
        specification_curve(lambda s, k: {}, {}, np.random.default_rng(0), n=10)


def test_plot_helper_draws_both_panels(tmp_path):
    """Check plot helper draws both panels."""
    import matplotlib

    matplotlib.use("Agg")
    from vedic_astrology_core.stats.plots import save_figure, specification_curve_figure

    rng = np.random.default_rng(4)
    n = 5000
    w, ev = _make(n, 2.0, rng)
    res = specification_curve(
        _estimator(w, ev, n),
        {"lag": [0, 1], "widen": [False, True]},
        np.random.default_rng(5),
        n=n,
        min_shift=200,
        n_draws=9,
    )
    fig = specification_curve_figure(res, ["lag", "widen"])
    assert len(fig.axes) == 2
    out = save_figure(
        fig, tmp_path / "sc.png", {"data_sha256": "x", "commit": "y", "seed": 5}
    )
    assert out.exists()
