"""Lomb-Scargle periodogram at pre-specified periods only.

Testing the whole frequency grid and picking the peak is a search; this
module evaluates the standard-normalised power only at periods fixed in the
hypothesis file (synodic or sidereal periods) and gives the single-frequency
false-alarm probability ``(1 - P)^((N - 3) / 2)`` (Scargle 1982, Gaussian
white noise), Bonferroni-adjusted over the number of periods. Use a
circular-shift or AR(1) surrogate null from :mod:`.nulls` when the residuals
are red.
"""

from typing import Dict, Sequence

import numpy as np
import pandas as pd


def lomb_scargle_at_periods(
    series: pd.Series, periods_days: Sequence[float]
) -> pd.DataFrame:
    """Return power and false-alarm probabilities at the given periods.

    Args:
        series: Values with a ``DatetimeIndex`` (unevenly spaced is fine).
        periods_days: Periods fixed a priori, in days.

    Returns:
        DataFrame with ``period_days``, ``power``, ``fap_single`` and
        ``fap_bonferroni``.
    """
    from astropy.timeseries import LombScargle

    s = pd.Series(series).dropna()
    t = (s.index - s.index[0]).total_seconds().to_numpy() / 86400.0
    y = s.to_numpy(dtype=float)
    periods = np.asarray(periods_days, dtype=float)
    if np.any(periods <= 0):
        raise ValueError("periods must be positive")
    power = LombScargle(t, y, normalization="standard").power(1.0 / periods)
    n = len(y)
    fap = np.clip((1.0 - power) ** ((n - 3) / 2.0), 0.0, 1.0)
    return pd.DataFrame({
        "period_days": periods,
        "power": power,
        "fap_single": fap,
        "fap_bonferroni": np.minimum(1.0, fap * len(periods)),
    })


def lomb_scargle_grid(
    series: pd.Series, min_period: float = 2.0, max_period: float = 3000.0
) -> Dict[str, np.ndarray]:
    """Return the full periodogram for display (not for testing).

    The ``fap_level_01`` entry is astropy's 1 % false-alarm level for the
    whole grid (Baluev 2008).
    """
    from astropy.timeseries import LombScargle

    s = pd.Series(series).dropna()
    t = (s.index - s.index[0]).total_seconds().to_numpy() / 86400.0
    ls = LombScargle(t, s.to_numpy(dtype=float))
    freq, power = ls.autopower(
        minimum_frequency=1.0 / max_period, maximum_frequency=1.0 / min_period
    )
    return {
        "period_days": 1.0 / freq,
        "power": power,
        "fap_level_01": float(ls.false_alarm_level(0.01)),
    }
