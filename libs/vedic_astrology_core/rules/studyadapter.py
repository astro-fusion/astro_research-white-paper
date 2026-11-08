"""Connect a rule to a pre-registered study: periods, events, grid, indicator.

Each study's ``hypothesis.yaml`` splits its time axis once into an EXPLORE
and a CONFIRM period (ADR-003). This adapter reads that split and gives the
rule workbench:

* the explore and confirm periods,
* a daily grid (earthquakes) or the trading-bar grid (markets) for each,
* the event series on that grid: the Gardner-Knopoff declustered
  catalogue for the earthquake study, the extreme-move bars (absolute
  return above the past-only rolling quantile) for a market study,
* an evaluator from a rule with bound params to its indicator on the grid.

The holdout rule is structural: only a function whose name contains
``confirm`` returns confirm-period data. ``fit`` and ``dose`` use the
``explore_*`` functions; only ``confirm`` calls the ``confirm_*`` ones.
"""

import json
import sys
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

from .context import Location
from .grid import GridEvaluator
from .schema import Rule

REPO = Path(__file__).resolve().parents[3]
STUDIES = {
    "earthquake": "earthquake",
    "gold_market": "gold_market",
    "gold": "gold_market",
    "silver_market": "silver_market",
    "silver": "silver_market",
}
EVENT_CACHE = "events_declustered_gk.csv"
EARTHQUAKE_PLACE = Location(28.0, 85.0, "UTC")  # the registered Himalayan arc
DEFAULT_SEED = 42


def studies_root() -> Path:
    """``studies/`` of this repository."""
    return REPO / "studies"


def resolve_study(name: str) -> str:
    """Return the study directory name for ``name`` (aliases: gold, silver)."""
    if name not in STUDIES:
        raise KeyError(
            f"unknown study '{name}'; the workbench knows "
            + ", ".join(sorted(set(STUDIES.values())))
        )
    return STUDIES[name]


def load_hypothesis(study: str) -> Dict:
    """Read ``studies/<study>/hypothesis.yaml``."""
    path = studies_root() / resolve_study(study) / "hypothesis.yaml"
    return yaml.safe_load(path.read_text())


@dataclass(frozen=True)
class Period:
    """A half-open UTC interval ``[start, end)`` of a study's time axis."""

    name: str
    start: pd.Timestamp
    end: pd.Timestamp

    def label(self) -> List[str]:
        """``[first day, last day]`` as ISO dates."""
        last = self.end - pd.Timedelta(days=1)
        return [self.start.date().isoformat(), last.date().isoformat()]


def _ts(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")


def split_periods(hyp: Dict) -> Tuple[Period, Period]:
    """Return (explore, confirm) from a hypothesis file.

    Two layouts are registered: ``split: {explore: [a, b], confirm: [c, d]}``
    (earthquake) and ``periods: {explore_end, confirm_start}`` with
    ``data: {start, end}`` (markets). End dates are inclusive in the files.
    """
    one = pd.Timedelta(days=1)
    if "split" in hyp:
        split = hyp["split"]
        e0, e1 = split["explore"]
        c0, c1 = split["confirm"]
        purge = pd.Timedelta(days=int(split.get("purge_days", 0)))
        explore = Period("explore", _ts(e0), _ts(e1) + one - purge)
        confirm = Period("confirm", _ts(c0), _ts(c1) + one)
    elif "periods" in hyp:
        data = hyp.get("data", {})
        explore = Period(
            "explore",
            _ts(data.get("start", "1900-01-01")),
            _ts(hyp["periods"]["explore_end"]) + one,
        )
        confirm = Period(
            "confirm",
            _ts(hyp["periods"]["confirm_start"]),
            _ts(data.get("end", pd.Timestamp.now("UTC").date())) + one,
        )
    else:
        raise ValueError("hypothesis.yaml has neither 'split' nor 'periods'")
    if confirm.start < explore.end:
        raise ValueError("the confirm period overlaps the explore period")
    return explore, confirm


def direction_of(rule: Rule) -> str:
    """Return the registered alternative from ``expected_effect.direction``."""
    effect = rule.expected_effect
    direction = effect.direction if effect else None
    return {"increase": "greater", "decrease": "less"}.get(direction, "two-sided")


# ------------------------------------------------------------------ events
def _earthquake_events(study_dir: Path) -> Tuple[pd.Series, str]:
    """Declustered (Gardner-Knopoff) event times, all periods, and their hash.

    Read from ``studies/earthquake/artifacts/events_declustered_gk.csv``;
    built once from the catalogue snapshot with the study's own pipeline
    functions when absent.
    """
    from ..stats.manifest import file_sha256

    cache = study_dir / "artifacts" / EVENT_CACHE
    if not cache.exists():
        scripts = str(study_dir / "scripts")
        for p in (scripts, str(REPO), str(REPO / "libs")):
            if p not in sys.path:
                sys.path.insert(0, p)
        import decluster  # type: ignore[import-not-found]
        import pipeline  # type: ignore[import-not-found]

        cat, info = pipeline.load_catalogue()
        keep = decluster.gardner_knopoff(cat).to_numpy()
        out = cat.loc[keep, ["time", "latitude", "longitude", "depth", "mw", "id"]]
        cache.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(cache, index=False)
        cache.with_suffix(".json").write_text(
            json.dumps({"snapshot": info["snapshot"], "sha256": info["sha256"]})
        )
    times = pd.to_datetime(pd.read_csv(cache)["time"], utc=True, format="ISO8601")
    return times.sort_values().reset_index(drop=True), file_sha256(cache)


def _market_bars(study: str, hyp: Dict) -> Tuple[pd.DataFrame, str]:
    """Trading bars with UTC sample instants and the extreme-move flag."""
    from ..markets import fetch
    from ..markets.study import targets
    from ..stats.manifest import file_sha256

    snaps = sorted((REPO / "data" / "snapshots").glob(f"{study}_*.csv"))
    if snaps:
        path = snaps[-1]
        manifest = path.with_name(path.stem + ".manifest.json")
        series = (
            json.loads(manifest.read_text()).get("series_id")
            if manifest.exists()
            else None
        )
        src = next(
            (s for s in hyp["data"]["sources"] if s["series_id"] == series),
            hyp["data"]["sources"][0],
        )
    else:
        path = REPO / hyp["data"]["fixture"]["path"]
        src = hyp["data"]["fixture"]
    prices = fetch.read_tidy_csv(path)
    raw_dates = prices["date"] if "date" in prices else prices.index
    dates = pd.DatetimeIndex(pd.to_datetime(raw_dates))
    close = prices["close"].to_numpy(dtype=float)
    tests = hyp["tests"]
    flag = targets(
        close, int(tests["extreme_window_bars"]), float(tests["extreme_quantile"])
    )["extreme"].to_numpy()
    local = pd.DatetimeIndex(
        [pd.Timestamp(f"{d.date()} {src.get('sample_time', '12:00')}") for d in dates]
    ).tz_localize(src.get("tz", "UTC"))
    bars = pd.DataFrame(
        {"date": dates.normalize(), "instant": local.tz_convert("UTC"), "extreme": flag}
    )
    return bars, file_sha256(path)


# ----------------------------------------------------------------- adapter
class StudyAdapter:
    """One study as the rule workbench sees it."""

    def __init__(self, study: str, place: Optional[Location] = None):
        """Read the study's hypothesis; data load lazily."""
        self.study = resolve_study(study)
        self.dir = studies_root() / self.study
        self.hypothesis = load_hypothesis(self.study)
        self._explore, self._confirm = split_periods(self.hypothesis)
        self.kind = "events" if self.study == "earthquake" else "market"
        self.place = place or (EARTHQUAKE_PLACE if self.kind == "events" else None)
        self._evaluators: Dict[Tuple[str, str], GridEvaluator] = {}

    # ---- registration
    @property
    def seed(self) -> int:
        """The registered seed."""
        test = self.hypothesis.get("test") or self.hypothesis.get("tests") or {}
        return int(test.get("seed", DEFAULT_SEED))

    @property
    def min_shift(self) -> int:
        """Minimum circular shift in grid steps (days or bars)."""
        test = self.hypothesis.get("test") or self.hypothesis.get("tests") or {}
        if "min_shift_days" in test:
            return int(test["min_shift_days"])
        return int(test.get("min_shift_bars", 400))

    @property
    def n_draws(self) -> int:
        """Registered number of null draws."""
        test = self.hypothesis.get("test") or self.hypothesis.get("tests") or {}
        return int(test.get("n_draws", test.get("n_perm", 10000)))

    @property
    def alpha(self) -> float:
        """Registered significance level."""
        test = self.hypothesis.get("test") or self.hypothesis.get("tests") or {}
        return float(test.get("alpha", 0.05))

    @property
    def correction(self) -> str:
        """Return the registered multiplicity method: bh, by or bonferroni."""
        test = self.hypothesis.get("test") or self.hypothesis.get("tests") or {}
        method = str(test.get("correction", "by")).lower()
        return {"benjamini_yekutieli": "by", "benjamini_hochberg": "bh"}.get(
            method, method
        )

    @property
    def event_label(self) -> str:
        """What an event is in this study."""
        if self.kind == "events":
            return "declustered (Gardner-Knopoff) earthquakes per day"
        return "extreme-move bars (|return| above the past-only rolling quantile)"

    # ---- data, all periods (private: callers use explore_* or confirm_*)
    @cached_property
    def _data(self) -> Tuple[pd.DataFrame, str]:
        """Return (frame with 'moment' and 'event' per step, data sha256)."""
        if self.kind == "events":
            times, sha = _earthquake_events(self.dir)
            start = min(self._explore.start, times.min().normalize())
            days = pd.date_range(start, self._confirm.end, freq="D", inclusive="left")
            counts = np.zeros(len(days), dtype=np.int64)
            idx = ((times - days[0]) // pd.Timedelta(days=1)).to_numpy(dtype=np.int64)
            idx = idx[(idx >= 0) & (idx < len(days))]
            np.add.at(counts, idx, 1)
            frame = pd.DataFrame(
                {"moment": days + pd.Timedelta(hours=12), "event": counts},
                index=days,
            )
            return frame, sha
        bars, sha = _market_bars(self.study, self.hypothesis)
        # The indicator on bar t-1 is tested against the outcome on bar t.
        frame = pd.DataFrame(
            {
                "moment": bars["instant"].shift(1).to_numpy(),
                "event": bars["extreme"].to_numpy(),
            },
            index=pd.DatetimeIndex(bars["date"]).tz_localize("UTC"),
        ).iloc[1:]
        frame = frame[np.isfinite(frame["event"].to_numpy(dtype=float))]
        frame["event"] = frame["event"].astype(np.int64)
        return frame, sha

    def _cut(self, period: Period) -> pd.DataFrame:
        frame = self._data[0]
        return frame[(frame.index >= period.start) & (frame.index < period.end)]

    def _evaluator(self, period: Period, rule: Rule) -> GridEvaluator:
        natal = None
        if rule.natal is not None:
            from .engine import to_location

            natal = (rule.natal.moment, to_location(rule.natal.place))
        natal_key = rule.natal.model_dump_json() if rule.natal else ""
        key = (period.name, rule.node_model + natal_key)
        if key not in self._evaluators:
            moments = pd.DatetimeIndex(self._cut(period)["moment"])
            self._evaluators[key] = GridEvaluator(
                moments, self.place, natal, rule.node_model
            )
        return self._evaluators[key]

    @staticmethod
    def _bins(frame: pd.DataFrame) -> np.ndarray:
        counts = frame["event"].to_numpy(dtype=np.int64)
        return np.repeat(np.arange(len(counts)), counts)

    @property
    def data_sha256(self) -> str:
        """SHA-256 of the event data file."""
        return self._data[1]

    # ---- explore
    def explore_period(self) -> Period:
        """Return the EXPLORE period."""
        return self._explore

    def explore_grid(self) -> pd.DatetimeIndex:
        """Grid steps (UTC days or bars) of the explore period."""
        return pd.DatetimeIndex(self._cut(self._explore).index)

    def explore_events(self) -> np.ndarray:
        """Event grid indices in the explore period (repeated per event)."""
        return self._bins(self._cut(self._explore))

    def explore_indicator(self, rule: Rule) -> np.ndarray:
        """Return the rule's indicator (conditions + window) on the explore grid."""
        return self._evaluator(self._explore, rule).indicator(rule)

    def explore_strength(self, rule: Rule) -> np.ndarray:
        """Return the rule's graded strength on the explore grid."""
        return self._evaluator(self._explore, rule).strength(rule)

    def explore_evaluator(self) -> Callable[[Rule], np.ndarray]:
        """Return ``rule -> indicator`` on the explore grid (for a sweep)."""
        return self.explore_indicator

    # ---- confirm (only `astro-rules confirm` calls these)
    def confirm_period(self) -> Period:
        """Return the CONFIRM period (the holdout)."""
        return self._confirm

    def confirm_grid(self) -> pd.DatetimeIndex:
        """Grid steps of the confirm period."""
        return pd.DatetimeIndex(self._cut(self._confirm).index)

    def confirm_events(self) -> np.ndarray:
        """Event grid indices in the confirm period."""
        return self._bins(self._cut(self._confirm))

    def confirm_indicator(self, rule: Rule) -> np.ndarray:
        """Return the rule's indicator on the confirm grid."""
        return self._evaluator(self._confirm, rule).indicator(rule)

    # ---- registered family
    def family_member(self, rule: Rule) -> Optional[str]:
        """Return the registered indicator id of this rule, if it is in the family.

        A hypothesis indicator names its rule with ``rule:`` (an id, or the
        name of a migrated catalogue rule).
        """
        names = {rule.id, rule.name}
        migrated = (rule.notes or {}).get("migrated_from", "")
        if "(" in str(migrated):
            names.add(str(migrated).rsplit("(", 1)[1].rstrip(") "))
        for spec in self.hypothesis.get("indicators", []):
            if spec.get("rule") in names:
                return spec["id"]
        return None

    def confirm_family_p_values(self, member: str) -> Optional[pd.DataFrame]:
        """Confirm-period p-values of the registered family, from the artifacts.

        Returns a frame with ``indicator`` and ``p_value`` (one row per test)
        or None when the study has not been run.
        """
        art = self.dir / "artifacts"
        if self.kind == "events":
            path = art / "confirmation.csv"
            if not path.exists():
                return None
            df = pd.read_csv(path)
            df = df[df["period"] == "confirm"]
            df = df[df["catalogue"].isin(["gk", "nn"])]
            df = df.assign(own=(df["indicator"] == member) & (df["catalogue"] == "gk"))
            return df[["indicator", "p_value", "own"]].dropna(subset=["p_value"])
        path = art / "tbl_confirmation.csv"
        if not path.exists():
            return None
        df = pd.read_csv(path)
        df = df.assign(own=(df["indicator"] == member) & (df["target"] == "extreme"))
        return df[["indicator", "p_value", "own"]].dropna(subset=["p_value"])


__all__ = [
    "Period",
    "StudyAdapter",
    "direction_of",
    "load_hypothesis",
    "resolve_study",
    "split_periods",
]
