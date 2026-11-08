"""A rule-free test of whether any function of the sky predicts event days.

Instead of naming a configuration, fit a regularised (L2) logistic model from
sky features (sin and cos of every longitude, speeds, tithi and nakshatra
one-hot) to a 0/1 event-day series and score it out of sample with
time-ordered (forward-chaining) cross-validation: fold ``k`` trains on every
block before it and tests on the next. The same model is refitted on the sky
circularly shifted against the events (:func:`shifted_sky_auc_test`); the
shifted fits keep every periodicity and autocorrelation of the sky and of the
events and break only their alignment, so their AUCs are the null.

The model is scikit-learn's ``LogisticRegression`` when it is installed and
otherwise the same L2-penalised likelihood minimised with L-BFGS
(:func:`fit_ridge_logistic`); features are standardised on the training
block only. The penalty is fixed in advance, never tuned on the test blocks.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy import optimize
from scipy.special import expit
from scipy.stats import rankdata

from .nulls import _check_rng, circular_shift_offsets


def auc(y_true, score) -> float:
    """Return the ROC AUC (Mann-Whitney, ties count one half)."""
    y = np.asarray(y_true).astype(bool)
    s = np.asarray(score, dtype=float)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(s)
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


@dataclass
class RidgeLogistic:
    """Fitted L2 logistic model on standardised features."""

    coef: np.ndarray
    intercept: float
    mean: np.ndarray
    scale: np.ndarray

    def decision(self, x) -> np.ndarray:
        """Return the linear predictor (log-odds) for rows of ``x``."""
        z = (np.asarray(x, dtype=float) - self.mean) / self.scale
        return z @ self.coef + self.intercept


def fit_ridge_logistic(x, y, l2: float = 1.0) -> RidgeLogistic:
    """Fit ``min -loglik + l2/2 ||w||^2`` (intercept unpenalised)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale = np.where(scale > 0, scale, 1.0)
    z = (x - mean) / scale
    try:  # pragma: no cover - depends on the environment
        from sklearn.linear_model import LogisticRegression

        m = LogisticRegression(C=1.0 / l2, max_iter=1000).fit(z, y)
        return RidgeLogistic(m.coef_[0], float(m.intercept_[0]), mean, scale)
    except ImportError:
        pass
    p = z.shape[1]

    def f(w):
        eta = z @ w[:p] + w[p]
        loss = np.sum(np.logaddexp(0.0, eta) - y * eta) + 0.5 * l2 * w[:p] @ w[:p]
        r = expit(eta) - y
        grad = np.concatenate([z.T @ r + l2 * w[:p], [r.sum()]])
        return loss, grad

    w0 = np.zeros(p + 1)
    base = np.clip(y.mean(), 1e-6, 1 - 1e-6)
    w0[p] = np.log(base / (1 - base))
    res = optimize.minimize(f, w0, jac=True, method="L-BFGS-B")
    return RidgeLogistic(res.x[:p], float(res.x[p]), mean, scale)


def forward_chaining_auc(
    x,
    y,
    n_folds: int = 5,
    l2: float = 1.0,
    on_split: Optional[Callable] = None,
) -> float:
    """Mean test-block AUC over ``n_folds`` forward-chaining splits.

    The series is cut into ``n_folds + 1`` contiguous blocks; fold ``k``
    trains on blocks ``0..k`` and tests on block ``k + 1``. Folds whose test
    block has no event (or only events) are skipped.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y).astype(int)
    edges = np.linspace(0, len(y), n_folds + 2).astype(int)
    scores = []
    for k in range(n_folds):
        tr = np.arange(0, edges[k + 1])
        te = np.arange(edges[k + 1], edges[k + 2])
        if on_split is not None:
            on_split(tr, te)
        if y[tr].min() == y[tr].max() or y[te].min() == y[te].max():
            continue
        model = fit_ridge_logistic(x[tr], y[tr], l2)
        scores.append(auc(y[te], model.decision(x[te])))
    return float(np.mean(scores)) if scores else float("nan")


def holdout_auc(x_train, y_train, x_test, y_test, l2: float = 1.0) -> float:
    """Train once, score once: AUC on a frozen test period."""
    model = fit_ridge_logistic(x_train, y_train, l2)
    return auc(y_test, model.decision(x_test))


@dataclass
class ClassifierTest:
    """Observed out-of-sample AUC against shifted-sky AUCs."""

    auc: float
    null_aucs: np.ndarray
    null_q05: float
    null_q50: float
    null_q95: float
    p_value: float
    n_draws: int
    n_folds: int
    l2: float


def shifted_sky_auc_test(
    x,
    y,
    min_shift: int,
    n_draws: int,
    rng: np.random.Generator,
    n_folds: int = 5,
    l2: float = 1.0,
) -> ClassifierTest:
    """Forward-chaining AUC of the real sky versus circularly shifted skies.

    p = (1 + #{null AUC >= observed}) / (n_draws + 1).
    """
    _check_rng(rng)
    x = np.asarray(x, dtype=float)
    obs = forward_chaining_auc(x, y, n_folds, l2)
    offsets = circular_shift_offsets(len(x), min_shift, n_draws, rng)
    null = np.array(
        [
            forward_chaining_auc(np.roll(x, int(k), axis=0), y, n_folds, l2)
            for k in offsets
        ]
    )
    ok = null[np.isfinite(null)]
    q = np.quantile(ok, [0.05, 0.5, 0.95]) if len(ok) else [np.nan] * 3
    p = float((1 + np.sum(ok >= obs)) / (len(ok) + 1))
    return ClassifierTest(
        float(obs),
        null,
        float(q[0]),
        float(q[1]),
        float(q[2]),
        p,
        int(n_draws),
        int(n_folds),
        float(l2),
    )
