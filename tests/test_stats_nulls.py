"""Tests for the autocorrelation-preserving null surrogates."""

import numpy as np
import pytest

from vedic_astrology_core.stats.nulls import (
    circular_shift_null,
    circular_shift_offsets,
    make_rng,
    phase_randomization,
    stationary_block_bootstrap,
    stationary_bootstrap_indices,
)


def test_circular_shift_is_a_rotation_with_offset_in_range():
    """The surrogate equals np.roll of the input by an offset >= min_shift."""
    x = np.repeat([0, 1, 0, 1, 1, 0], [50, 10, 70, 5, 20, 45])
    rng = np.random.default_rng(7)
    y = circular_shift_null(x, 30, rng)
    offsets = [k for k in range(len(x)) if np.array_equal(np.roll(x, k), y)]
    assert any(30 <= k <= len(x) - 30 for k in offsets)
    assert y.sum() == x.sum()


def test_offsets_are_bounded_and_seeded():
    """Offsets lie in [min_shift, n - min_shift] and repeat with the seed."""
    a = circular_shift_offsets(1000, 200, 5000, np.random.default_rng(1))
    b = circular_shift_offsets(1000, 200, 5000, np.random.default_rng(1))
    assert a.min() >= 200 and a.max() <= 800
    np.testing.assert_array_equal(a, b)


def test_shift_rejects_short_series_and_legacy_rng():
    """Too-short series and np.random module state are refused."""
    with pytest.raises(ValueError):
        circular_shift_null(np.zeros(10), 6, np.random.default_rng(0))
    with pytest.raises(TypeError):
        circular_shift_null(np.zeros(10), 2, np.random)


def test_bootstrap_block_lengths_have_requested_mean():
    """Mean run of consecutive indices is close to mean_block."""
    idx = stationary_bootstrap_indices(200_000, 20.0, np.random.default_rng(3))
    breaks = np.flatnonzero(np.diff(idx) != 1)
    mean_run = len(idx) / (len(breaks) + 1)
    assert 18.0 < mean_run < 22.0
    assert idx.min() >= 0 and idx.max() < 200_000


def test_bootstrap_with_unit_blocks_resamples_iid_values():
    """mean_block=1 starts a new block at every step; values come from x."""
    x = np.arange(100.0)
    y = stationary_block_bootstrap(x, 1.0, np.random.default_rng(5))
    assert len(y) == 100
    assert set(y) <= set(x)


def test_phase_randomisation_keeps_spectrum_and_mean():
    """Amplitude spectrum and mean are kept; the series itself changes."""
    rng = np.random.default_rng(11)
    for n in (512, 513):
        x = np.cumsum(rng.normal(size=n))
        s = phase_randomization(x, np.random.default_rng(2))
        np.testing.assert_allclose(np.abs(np.fft.rfft(s)), np.abs(np.fft.rfft(x)),
                                   rtol=1e-8, atol=1e-8)
        assert s.mean() == pytest.approx(x.mean())
        assert not np.allclose(s, x)


def test_make_rng_is_seeded_generator():
    """make_rng(seed) equals np.random.default_rng(seed)."""
    a = make_rng(5).integers(0, 1000, 10)
    b = np.random.default_rng(5).integers(0, 1000, 10)
    np.testing.assert_array_equal(a, b)
