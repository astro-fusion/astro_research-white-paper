"""Same-family count models: NB2 baseline versus NB2 with astro covariates.

Replaces the withdrawn ``train_models.py`` / ``validate_results.py``, which
compared a Poisson baseline with a negative binomial (alpha fixed at 1) by
AIC, so the family switch alone produced the difference. Here both models
are NB2 with alpha estimated, compared by

* a likelihood-ratio test (df = number of astro covariates), and
* leave-one-year-out cross-validated predictive log-likelihood.

Nothing is written to the current directory; the pipeline stores results.
"""

from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats as sps


def monthly_design(
    event_times, indicators: pd.DataFrame, columns: List[str]
) -> pd.DataFrame:
    """Return monthly counts, a centred time trend and indicator fractions."""
    idx = indicators.index
    month = idx.tz_convert("UTC").tz_localize(None).to_period("M")
    frac = indicators[columns].astype(float).groupby(month).mean()
    t = pd.to_datetime(pd.Series(event_times), utc=True, format="ISO8601")
    counts = t.dt.tz_localize(None).dt.to_period("M").value_counts()
    frame = frac.copy()
    frame.insert(0, "count", counts.reindex(frac.index).fillna(0).astype(int))
    years = np.asarray([p.year + (p.month - 0.5) / 12 for p in frac.index])
    frame.insert(1, "trend", (years - years.mean()) / 10.0)
    frame["year"] = [p.year for p in frac.index]
    return frame


def _fit_nb2(y, x):
    import statsmodels.api as sm

    model = sm.NegativeBinomial(y, sm.add_constant(x, has_constant="add"),
                                loglike_method="nb2")
    return model.fit(disp=0, maxiter=500, method="bfgs")


def _nb2_logpmf(y, mu, alpha) -> np.ndarray:
    size = 1.0 / alpha
    return sps.nbinom.logpmf(y, size, size / (size + mu))


def _predict(fit, x) -> np.ndarray:
    import statsmodels.api as sm

    exog = sm.add_constant(x, has_constant="add")
    beta = np.asarray(fit.params)[:-1]
    return np.exp(np.asarray(exog, dtype=float) @ beta)


def compare_nb_models(frame: pd.DataFrame, astro_cols: List[str]) -> Dict:
    """Fit both NB2 models, run the LR test and leave-one-year-out CV."""
    y = frame["count"].to_numpy()
    base_x = frame[["trend"]]
    full_x = frame[["trend"] + list(astro_cols)]
    base = _fit_nb2(y, base_x)
    full = _fit_nb2(y, full_x)
    lr = max(0.0, 2.0 * (full.llf - base.llf))
    df = len(astro_cols)
    cv_base, cv_full = 0.0, 0.0
    for year in sorted(frame["year"].unique()):
        test = frame["year"] == year
        train = ~test
        fb = _fit_nb2(y[train], base_x[train])
        ff = _fit_nb2(y[train], full_x[train])
        cv_base += _nb2_logpmf(y[test], _predict(fb, base_x[test]),
                               float(fb.params.iloc[-1])).sum()
        cv_full += _nb2_logpmf(y[test], _predict(ff, full_x[test]),
                               float(ff.params.iloc[-1])).sum()
    names = list(full.params.index)
    return {
        "n_months": int(len(frame)),
        "n_events": int(y.sum()),
        "baseline": {"llf": float(base.llf), "alpha": float(base.params.iloc[-1]),
                     "aic": float(base.aic)},
        "research": {"llf": float(full.llf), "alpha": float(full.params.iloc[-1]),
                     "aic": float(full.aic),
                     "coefficients": {k: float(full.params[k]) for k in names},
                     "std_errors": {k: float(full.bse[k]) for k in names}},
        "lr_stat": float(lr),
        "lr_df": int(df),
        "lr_p_value": float(sps.chi2.sf(lr, df)),
        "loyo_cv_loglik_baseline": float(cv_base),
        "loyo_cv_loglik_research": float(cv_full),
        "loyo_cv_gain": float(cv_full - cv_base),
    }
