"""The rule workbench: tune on EXPLORE, decide once on CONFIRM (ADR-003).

* :func:`fit` sweeps a rule's declared ``params`` over the explore period,
  tests every cell with the circular-shift rate-ratio test, adjusts the
  p-values within the grid (Benjamini-Hochberg), draws the specification
  curve and returns a ``tuning_log`` entry.
* :func:`confirm` runs the frozen rule once on the confirm period and
  returns the ``validation`` stamp. It refuses a version already stamped.
* :func:`dose` reports the event rate across strength quintiles and the
  trend across them.

No statistics are written here: rates, nulls, multiplicity, dose-response
and the specification curve come from :mod:`vedic_astrology_core.stats`.
"""

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..stats.dose import dose_response
from ..stats.manifest import git_commit
from ..stats.multiplicity import adjust
from ..stats.permutation import permutation_test
from ..stats.plots import HOUSE_STYLE, PALETTE, save_figure
from ..stats.rates import indicator_rate_ratio, rate_ratio, rate_ratio_shift_test
from ..stats.speccurve import specification_curve
from .schema import Rule
from .studyadapter import REPO, StudyAdapter, direction_of

MAX_CELLS = 600
FIT_DRAWS = 2000
CURVE_DRAWS = 200


class WorkbenchError(ValueError):
    """A workbench command cannot run on this rule or study."""


def now_utc() -> datetime:
    """Return the current UTC time, to the second."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def in_direction(rr: float, alternative: str) -> bool:
    """Return True when the rate ratio lies in the registered direction."""
    if not np.isfinite(rr):
        return False
    if alternative == "greater":
        return rr > 1
    if alternative == "less":
        return rr < 1
    return True


def grid_cells(rule: Rule) -> List[Dict[str, float]]:
    """Every combination of the rule's parameter grids (one empty cell if none)."""
    names = list(rule.params)
    grids = [rule.params[n].grid() for n in names]
    return [dict(zip(names, combo)) for combo in itertools.product(*grids)]


def _closeness(cell: Dict[str, float], rule: Rule) -> float:
    return sum(
        abs(v - rule.params[k].value) / (rule.params[k].step or 1)
        for k, v in cell.items()
    )


def _cell_label(cell: Dict[str, float]) -> str:
    if not cell:
        return "(no params)"
    return ", ".join(f"{k}={v:g}" for k, v in cell.items())


# --------------------------------------------------------------------- fit
@dataclass
class FitResult:
    """Outcome of :func:`fit`."""

    rule_id: str
    version: int
    study: str
    cells: pd.DataFrame
    chosen: Dict[str, float]
    chosen_row: Dict[str, Any]
    curve: Any
    figure: Optional[Path]
    entry: Dict[str, Any]
    n_events: int
    n_steps: int
    alternative: str
    notes: List[str] = field(default_factory=list)

    def top(self, k: int = 5) -> pd.DataFrame:
        """Return the ``k`` best cells by p-value."""
        ok = self.cells[self.cells["p"].notna()]
        return ok.sort_values(["p", "closeness"]).head(k)


def fit(
    rule: Rule,
    adapter: StudyAdapter,
    by: str,
    n_draws: int = FIT_DRAWS,
    curve_draws: int = CURVE_DRAWS,
    max_cells: int = MAX_CELLS,
    figure_dir: Optional[Path] = None,
) -> FitResult:
    """Sweep the rule's params on the explore period and choose a cell.

    The chosen cell has the smallest circular-shift p-value among cells
    whose rate ratio lies in the registered direction (ties go to the cell
    nearest the current values). Raises :class:`WorkbenchError` when the
    grid is too large or the rule cannot be evaluated.
    """
    cells = grid_cells(rule)
    if len(cells) > max_cells:
        raise WorkbenchError(
            f"{len(cells)} cells exceed the limit of {max_cells}; narrow the "
            "parameter ranges or raise the step"
        )
    alternative = direction_of(rule)
    events = adapter.explore_events()
    n_steps = len(adapter.explore_grid())
    seed = adapter.seed
    indicators: List[np.ndarray] = []
    rows = []
    for i, cell in enumerate(cells):
        bound = rule.bind(cell) if cell else rule
        ind = adapter.explore_indicator(bound)
        indicators.append(ind)
        row: Dict[str, Any] = dict(cell)
        row.update(
            cell=_cell_label(cell),
            closeness=_closeness(cell, rule),
            time_fraction=float(ind.mean()),
        )
        if len(events) == 0 or ind.all() or not ind.any():
            row.update(rate_ratio=np.nan, ci_low=np.nan, ci_high=np.nan, p=np.nan)
            row["skipped"] = "indicator always or never on"
        else:
            rng = np.random.default_rng([seed, i])
            res = rate_ratio_shift_test(
                events, ind, adapter.min_shift, n_draws, rng, alternative=alternative
            )
            row.update(
                n_in=res.exact.n_in,
                rate_ratio=res.exact.rate_ratio,
                ci_low=res.exact.ci_low,
                ci_high=res.exact.ci_high,
                p=res.p_value,
                skipped="",
            )
        rows.append(row)
    frame = pd.DataFrame(rows)
    valid = frame["p"].notna().to_numpy()
    frame["q_within_grid"] = np.nan
    if valid.any():
        frame.loc[valid, "q_within_grid"] = adjust(frame.loc[valid, "p"], "bh")
    notes = []
    candidates = frame[
        valid & np.array([in_direction(r, alternative) for r in frame["rate_ratio"]])
    ]
    if len(candidates):
        best = candidates.sort_values(["p", "closeness"], kind="mergesort").index[0]
    else:
        best = frame.sort_values("closeness", kind="mergesort").index[0]
        notes.append(
            "no cell has its rate ratio in the registered direction; the current "
            "values are kept"
        )
    chosen = dict(cells[int(best)])
    chosen_row = frame.loc[best].to_dict()

    curve = None
    if valid.sum() >= 1:
        grid = {"cell": [i for i in range(len(cells)) if valid[i]]}

        def estimator(spec, shift):
            ind = indicators[spec["cell"]]
            rr = indicator_rate_ratio((events + shift) % n_steps, ind)
            return {
                "estimate": rr.rate_ratio,
                "ci_low": rr.ci_low,
                "ci_high": rr.ci_high,
            }

        curve = specification_curve(
            estimator,
            grid,
            np.random.default_rng([seed, 10_000]),
            n_steps,
            min_shift=adapter.min_shift,
            n_draws=curve_draws,
            alternative=alternative,
        )

    out_dir = figure_dir or (adapter.dir / "artifacts")
    figure = _plot_curve(
        rule,
        adapter,
        frame,
        best,
        out_dir / f"speccurve_{rule.id}_v{rule.version}.png",
        alternative,
    )
    period = adapter.explore_period().label()
    entry = {
        "at": now_utc(),
        "by": by,
        "study": adapter.study,
        "version": rule.version,
        "grid": {
            name: {"min": p.min, "max": p.max, "step": p.step}
            for name, p in rule.params.items()
        },
        "chosen": chosen,
        "explore": {
            "rate_ratio": _num(chosen_row.get("rate_ratio")),
            "ci": [_num(chosen_row.get("ci_low")), _num(chosen_row.get("ci_high"))],
            "p": _num(chosen_row.get("p")),
            "q_within_grid": _num(chosen_row.get("q_within_grid")),
            "n_cells": len(cells),
            "n_events": int(len(events)),
            "period": period,
        },
        "spec_curve_artifact": _relative(figure),
    }
    if curve is not None:
        entry["note"] = (
            f"specification curve: median RR {curve.median_estimate:.3g}, joint "
            f"circular-shift p {curve.p_median:.3g} ({curve.n_draws} draws); "
            f"{curve.share_excluding_null:.0%} of cells exclude RR = 1"
        )
    return FitResult(
        rule.id,
        rule.version,
        adapter.study,
        frame,
        chosen,
        chosen_row,
        curve,
        figure,
        entry,
        int(len(events)),
        n_steps,
        alternative,
        notes,
    )


def _num(value) -> Optional[float]:
    if value is None:
        return None
    value = float(value)
    return None if not np.isfinite(value) else float(f"{value:.6g}")


def _relative(path: Optional[Path]) -> Optional[str]:
    if path is None:
        return None
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _plot_curve(rule, adapter, frame, best, path, alternative) -> Optional[Path]:
    """Specification curve: every cell's rate ratio with its 95% CI, sorted."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ok = frame[frame["p"].notna()].sort_values("rate_ratio", kind="mergesort")
    names = list(rule.params)
    with matplotlib.rc_context(HOUSE_STYLE):
        rows = 1 + len(names)
        fig, axes = plt.subplots(
            rows,
            1,
            figsize=(7.0, 3.0 + 0.8 * len(names)),
            sharex=True,
            gridspec_kw={"height_ratios": [3] + [1] * len(names)},
            squeeze=False,
        )
        ax = axes[0][0]
        x = np.arange(len(ok))
        colours = [PALETTE[1] if i == best else PALETTE[0] for i in ok.index]
        ax.vlines(x, ok["ci_low"], ok["ci_high"], colors="0.7", lw=1)
        ax.scatter(x, ok["rate_ratio"], c=colours, s=14, zorder=3)
        ax.axhline(1.0, color="0.3", lw=0.8, ls="--")
        if len(ok) and (ok["ci_low"] > 0).all():
            ax.set_yscale("log")
        ax.set_ylabel("Rate ratio (95% CI)")
        ax.set_title(
            f"{rule.id} v{rule.version}: {len(frame)} cells on {adapter.study} "
            f"explore {adapter.explore_period().label()[0][:4]}-"
            f"{adapter.explore_period().label()[1][:4]} ({alternative}); "
            "red = chosen",
            fontsize=8,
        )
        for k, name in enumerate(names, start=1):
            axp = axes[k][0]
            axp.scatter(x, ok[name], s=6, c="0.25")
            axp.set_ylabel(f"{name}\n({rule.params[name].unit})", fontsize=7)
        axes[-1][0].set_xlabel("Cells sorted by rate ratio")
        commit = git_commit(REPO).get("commit")
        out = save_figure(
            fig,
            path,
            {
                "data_sha256": adapter.data_sha256,
                "commit": commit,
                "seed": adapter.seed,
            },
            note="explore period only",
        )
        plt.close(fig)
    return out


# ----------------------------------------------------------------- confirm
def stamped(rule: Rule) -> bool:
    """Return True when this rule version already has a confirm stamp."""
    v = rule.validation
    return v.status != "unvalidated" and (v.version in (None, rule.version))


def confirm(rule: Rule, adapter: Optional[StudyAdapter]) -> Dict[str, Any]:
    """Run the frozen rule once on the confirm period; return the stamp.

    Raises:
        WorkbenchError: The version is already stamped.
    """
    if stamped(rule):
        raise WorkbenchError(
            f"{rule.id} v{rule.version} was already confirmed on "
            f"{rule.validation.study} at {rule.validation.at} "
            f"({rule.validation.status}); a new attempt needs a new version: "
            "run astro-rules fit --new-version (or change the rule and bump "
            "'version'), then confirm the new version"
        )
    if adapter is None:
        raise WorkbenchError("confirm needs a study")
    alternative = direction_of(rule)
    events = adapter.confirm_events()
    ind = adapter.confirm_indicator(rule)
    period = adapter.confirm_period().label()
    result: Dict[str, Any] = {
        "period": period,
        "n_events": int(len(events)),
        "direction": alternative,
    }
    if len(events) == 0 or ind.all() or not ind.any():
        result.update(rate_ratio=None, ci=[None, None], p=None)
        status = "not_confirmed"
        result.update(family="none (indicator degenerate on confirm)")
    else:
        rng = np.random.default_rng([adapter.seed, 20_000])
        res = rate_ratio_shift_test(
            events, ind, adapter.min_shift, adapter.n_draws, rng, alternative
        )
        p = float(res.p_value)
        q, family, size = _family_q(rule, adapter, p)
        result.update(
            rate_ratio=_num(res.exact.rate_ratio),
            ci=[_num(res.exact.ci_low), _num(res.exact.ci_high)],
            p=_num(p),
            q_family=_num(q),
            family=family,
            family_size=size,
        )
        ok = q < adapter.alpha and in_direction(res.exact.rate_ratio, alternative)
        status = "confirmed" if ok else "not_confirmed"
    return {
        "status": status,
        "version": rule.version,
        "study": adapter.study,
        "confirm": result,
        "at": now_utc(),
        "commit": git_commit(REPO).get("commit"),
    }


def _family_q(rule: Rule, adapter: StudyAdapter, p: float):
    member = adapter.family_member(rule)
    fam = adapter.confirm_family_p_values(member) if member else None
    if member and fam is not None and fam["own"].any():
        ps = fam["p_value"].to_numpy(dtype=float).copy()
        own = np.flatnonzero(fam["own"].to_numpy())
        ps[own] = p
        q = float(adjust(ps, adapter.correction)[own[0]])
        label = (
            f"registered family of {adapter.study} as '{member}' "
            f"({adapter.correction.upper()}, {len(ps)} tests)"
        )
        return q, label, int(len(ps))
    return p, "this rule alone (not in the study's registered family)", 1


# -------------------------------------------------------------------- dose
@dataclass
class DoseReport:
    """Event rate across strength quintiles while the rule fires."""

    table: pd.DataFrame
    baseline: Dict[str, float]
    method: str
    statistic: float
    p_value: float
    kendall_tau: float
    kendall_p: float
    shift_p: float
    n_fired: int
    n_perm: int


def dose(rule: Rule, adapter: StudyAdapter, n_perm: int = 999) -> DoseReport:
    """Dose-response on the explore period.

    Steps where the rule fires are cut into strength quintiles. Per quintile
    the event rate and its rate ratio against the steps where the rule is
    silent (exact Poisson CI, :func:`stats.rates.rate_ratio`). The trend is
    the Cochran-Armitage test on event days (:mod:`stats.dose`) and
    Kendall's tau-b between strength and the event count
    (``scipy.stats.kendalltau``); because days are autocorrelated, tau is
    also tested against circular shifts of the strength series
    (:func:`stats.permutation.permutation_test`).
    """
    from scipy.stats import kendalltau

    if rule.strength is None:
        raise WorkbenchError(
            f"{rule.id} has no strength block; dose needs a graded rule "
            "(add strength: {combine, terms})"
        )
    strength = adapter.explore_strength(rule)
    counts = np.bincount(adapter.explore_events(), minlength=len(strength))
    fired = strength > 0
    if fired.sum() < 10:
        raise WorkbenchError(f"{rule.id} fires on only {int(fired.sum())} steps")
    res = dose_response(strength[fired], (counts[fired] > 0).astype(float), 5)
    score = res.table["bin"].to_numpy()
    codes = pd.qcut(
        pd.Series(strength[fired]).rank(method="average"),
        5,
        labels=False,
        duplicates="drop",
    )
    bins = pd.factorize(codes, sort=True)[0]
    silent_n = float((~fired).sum())
    silent_ev = int(counts[~fired].sum())
    rows = []
    for b in score:
        mask = bins == b
        n_ev = int(counts[fired][mask].sum())
        t = float(mask.sum())
        rr = rate_ratio(n_ev, t, silent_ev, silent_n) if silent_n > 0 else None
        rows.append(
            {
                "quintile": int(b) + 1,
                "strength": f"{strength[fired][mask].min():.2f}-"
                f"{strength[fired][mask].max():.2f}",
                "steps": int(t),
                "events": n_ev,
                "rate_per_1000": 1000.0 * n_ev / t,
                "rr_vs_silent": rr.rate_ratio if rr else np.nan,
                "ci_low": rr.ci_low if rr else np.nan,
                "ci_high": rr.ci_high if rr else np.nan,
            }
        )
    tau = kendalltau(strength[fired], counts[fired])

    def stat(x, y):
        on = x > 0
        if on.sum() < 3:
            return 0.0
        value = kendalltau(x[on], y[on]).statistic
        return 0.0 if not np.isfinite(value) else float(value)

    perm = permutation_test(
        stat,
        strength,
        counts,
        rng=np.random.default_rng([adapter.seed, 30_000]),
        null="circular_shift",
        n_perm=n_perm,
        alternative="greater",
        min_shift=adapter.min_shift,
        n_boot=0,
    )
    return DoseReport(
        pd.DataFrame(rows),
        {
            "steps": silent_n,
            "events": silent_ev,
            "rate_per_1000": 1000.0 * silent_ev / silent_n if silent_n else np.nan,
        },
        res.method,
        res.statistic,
        res.p_value,
        float(tau.statistic),
        float(tau.pvalue),
        perm.p_value,
        int(fired.sum()),
        n_perm,
    )


# ------------------------------------------------------------------ review
def review_entry(rule: Rule, by: str, verdict: str, note: str) -> Dict[str, Any]:
    """Return a ``review`` entry for this rule version."""
    if verdict not in ("faithful", "not_faithful"):
        raise WorkbenchError("verdict is faithful or not_faithful")
    if not note.strip():
        raise WorkbenchError("a review needs a note saying what was checked")
    return {
        "by": by,
        "at": now_utc(),
        "verdict": verdict,
        "note": note.strip(),
        "version": rule.version,
    }


__all__ = [
    "DoseReport",
    "FitResult",
    "WorkbenchError",
    "confirm",
    "dose",
    "fit",
    "grid_cells",
    "in_direction",
    "review_entry",
    "stamped",
]
