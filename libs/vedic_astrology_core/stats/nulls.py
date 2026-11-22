"""Null surrogates that keep the autocorrelation of the series they resample.

Never shuffle days i.i.d.: astrological states come in long runs and event
series cluster, so an i.i.d. shuffle makes p-values far too small.

* :func:`circular_shift_null` rotates an indicator by a random offset of at
  least ``min_shift`` steps. The indicator's run structure and the outcome's
  clustering are both kept; only their alignment is broken.
  :func:`circular_shift_offsets` gives the offsets for a whole test: every
  admissible offset when there are no more than the draws asked for (exact),
  otherwise distinct offsets drawn without replacement.
* :func:`stationary_block_bootstrap` resamples a series in blocks of
  geometric length (Politis and Romano 1994).
* :func:`phase_randomization` keeps the power spectrum of a continuous
  series and randomises its Fourier phases (Theiler et al. 1992).

All take ``rng=np.random.default_rng(seed)``.
"""

import numpy as np


def make_rng(seed: int) -> np.random.Generator:
    """Return ``np.random.default_rng(seed)``, the one way studies seed nulls."""
    return np.random.default_rng(int(seed))


def _check_rng(rng) -> np.random.Generator:
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy Generator: np.random.default_rng(seed)")
    return rng


def n_admissible_shifts(n: int, min_shift: int) -> int:
    """Return the number of distinct offsets in ``[min_shift, n - min_shift]``.

    Raises:
        ValueError: If the series is too short for the minimum shift.
    """
    n, min_shift = int(n), int(min_shift)
    if min_shift < 1:
        raise ValueError("min_shift must be at least 1")
    if n - min_shift < min_shift:
        raise ValueError(f"series of length {n} is too short for min_shift {min_shift}")
    return n - 2 * min_shift + 1


def circular_shift_offsets(
    n: int, min_shift: int, n_draws: int, rng: np.random.Generator
) -> np.ndarray:
    """Return distinct offsets from ``[min_shift, n - min_shift]``.

    When that admissible set holds at most ``n_draws`` offsets, every one is
    returned once in increasing order (an exact test; ``rng`` is not used).
    Otherwise ``n_draws`` offsets are drawn uniformly without replacement.
    Either way no offset repeats, so a p-value of
    ``(n_extreme + 1) / (len(offsets) + 1)`` can reach the floor that
    :func:`shift_null_info` reports.

    Raises:
        ValueError: If the series is too short for the minimum shift.
    """
    _check_rng(rng)
    m = n_admissible_shifts(n, min_shift)
    min_shift, n_draws = int(min_shift), int(n_draws)
    if n_draws <= 0:
        return np.empty(0, dtype=np.int64)
    if m <= n_draws:
        return np.arange(min_shift, min_shift + m, dtype=np.int64)
    return min_shift + rng.choice(m, size=n_draws, replace=False).astype(np.int64)


def shift_null_info(n: int, min_shift: int, n_draws: int) -> dict:
    """Describe the null that :func:`circular_shift_offsets` builds.

    Returns:
        ``n_admissible`` (distinct offsets in ``[min_shift, n - min_shift]``),
        ``n_shifts`` (offsets actually used), ``exact_enumeration`` (every
        admissible offset used) and ``p_min``, the smallest attainable
        ``(n_extreme + 1) / (n_shifts + 1)``, that is ``1 / (n_shifts + 1)``.
    """
    m = n_admissible_shifts(n, min_shift)
    used = min(m, max(int(n_draws), 0))
    return {
        "n_admissible": int(m),
        "n_shifts": int(used),
        "exact_enumeration": bool(used == m),
        "p_min": 1.0 / (used + 1),
    }


def circular_shift_null(
    indicator, min_shift: int, rng: np.random.Generator
) -> np.ndarray:
    """Return the indicator rotated by one random offset >= ``min_shift``.

    Args:
        indicator: 1-D array (binary or continuous) on a regular time grid.
        min_shift: Smallest offset in grid steps; use at least the longest
            period of the indicator so shifted copies are not re-aligned.
        rng: ``np.random.default_rng(seed)``.
    """
    x = np.asarray(indicator)
    offset = circular_shift_offsets(len(x), min_shift, 1, rng)[0]
    return np.roll(x, int(offset))


def stationary_bootstrap_indices(
    n: int, mean_block: float, rng: np.random.Generator
) -> np.ndarray:
    """Return resampling indices of the Politis-Romano stationary bootstrap.

    Blocks start at uniform positions, have geometric lengths with mean
    ``mean_block`` and wrap around the end of the series.
    """
    _check_rng(rng)
    if mean_block < 1:
        raise ValueError("mean_block must be at least 1")
    p = 1.0 / float(mean_block)
    new_block = rng.random(n) < p
    new_block[0] = True
    block_first = np.flatnonzero(new_block)
    block_start = rng.integers(0, n, size=len(block_first))
    block_id = np.cumsum(new_block) - 1
    offset = np.arange(n) - block_first[block_id]
    return (block_start[block_id] + offset) % n


def stationary_block_bootstrap(
    series, mean_block: float, rng: np.random.Generator
) -> np.ndarray:
    """Return one stationary-bootstrap resample of ``series`` (same length)."""
    x = np.asarray(series)
    return x[stationary_bootstrap_indices(len(x), mean_block, rng)]


def phase_randomization(series, rng: np.random.Generator) -> np.ndarray:
    """Return a surrogate with the same amplitude spectrum and random phases.

    The mean (zero frequency) and, for even lengths, the Nyquist term are
    kept, so the surrogate is real with the same mean and variance.
    """
    _check_rng(rng)
    x = np.asarray(series, dtype=float)
    n = len(x)
    spectrum = np.fft.rfft(x)
    phases = rng.uniform(0.0, 2.0 * np.pi, size=len(spectrum))
    phases[0] = 0.0
    if n % 2 == 0:
        phases[-1] = 0.0
    surrogate = np.abs(spectrum) * np.exp(1j * (np.angle(spectrum) + phases))
    surrogate[0] = spectrum[0]
    if n % 2 == 0:
        surrogate[-1] = spectrum[-1]
    return np.fft.irfft(surrogate, n=n)
