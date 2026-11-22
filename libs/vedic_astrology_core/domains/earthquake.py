"""Earthquake adapter (ADR-007 section 4, WP-77).

Same polygon, completeness rule, Mw homogenisation and hourly UTC grid as the
registered plan `studies/earthquake/hypothesis.yaml`. The study scripts
(`fetch_catalogue.py`, `decluster.py`, `pipeline.py`, `robustness.py`) are
imported unchanged.

- `grid()`, `calendar_context()` and `periods()` read no catalogue row: the
  grid bounds come from the plan, not from the data.
- `outcomes(gate_hash)` loads the catalogue, declusters it and returns event
  grid bins per declustering method. The method is a declared cell:
  Gardner-Knopoff is primary; nearest-neighbour and the raw catalogue are
  sensitivity cells (ETAS is added when WP-26 lands).
- `controls(gate_hash)` declares the positive control (tidal phase) and the
  negative control (shifted sky) as control "principles".

Open item: the ISC Bulletin cross-check catalogue is not yet a committed
snapshot; the dataset is graded B and says so.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from ..stats.seal import load_study_modules
from .base import DatasetSpec, DomainAdapter, Periods

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "studies" / "earthquake" / "scripts"
SOURCE_ID = "usgs_comcat"
METHODS = ("gk", "nn", "raw")
PRIMARY_METHOD = "gk"
ISC_OPEN_ITEM = (
    "ISC Bulletin cross-check catalogue not yet a committed snapshot (second-dataset cell open)"
)
MB_OPEN_ITEM = "magnitudes are mostly converted from mb (review M7)"


class PinError(RuntimeError):
    """The plan pins no snapshot hash, or the pinned one is unknown."""


def _study_modules():
    """Import the unchanged study scripts by file path under unique names (G-03).

    Six study folders have a `pipeline.py`; a bare `import pipeline` through
    `sys.path` lets whichever folder came first win in one process. The
    scripts are loaded as `_study_earthquake__<name>`, dependencies first, so
    their own sibling imports resolve to this folder.
    """
    mods = load_study_modules(
        SCRIPTS,
        ("count_models", "indicators", "robustness", "fetch_catalogue", "decluster", "pipeline"),
        namespace="earthquake",
    )
    return (
        mods["decluster"], mods["fetch_catalogue"], mods["indicators"], mods["pipeline"],
        mods["robustness"],
    )


def _d(s: str) -> date:
    return date.fromisoformat(str(s)[:10])


class EarthquakeDomain(DomainAdapter):
    """Himalayan-arc mainshock rate on an hourly grid."""

    domain = "earthquake"

    def __init__(
        self,
        index: Mapping[str, Any],
        licences: Mapping[str, Mapping[str, Any]],
        *,
        snapshot: Optional[Path] = None,
        declustering: str = PRIMARY_METHOD,
        pinned_sha256: Optional[str] = None,
        grades: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> None:
        super().__init__(index, licences, grades)
        if declustering not in METHODS:
            raise ValueError(f"unknown declustering method {declustering!r}")
        self.declustering = declustering
        self._pinned = pinned_sha256
        self._snapshot = Path(snapshot) if snapshot else None
        self._hyp_cache: Optional[Dict] = None
        self._grid: Optional[pd.DatetimeIndex] = None

    # -- plan and snapshot ---------------------------------------------
    @property
    def hyp(self) -> Dict:
        if self._hyp_cache is None:
            _, fc, *_ = _study_modules()
            self._hyp_cache = fc.load_hypothesis()
        return self._hyp_cache

    def snapshot_path(self) -> Path:
        """The snapshot whose SHA-256 the plan pins (ADR-008 D-03).

        There is no "newest snapshot" fallback: without `pinned_sha256` (or an
        explicit `snapshot` file) this raises :class:`PinError`.
        """
        if self._snapshot is not None:
            return self._snapshot
        if not self._pinned:
            raise PinError("earthquake adapter needs the plan's pinned snapshot hash (D-03)")
        for e in self._index.get("snapshots", []):
            if e.get("sha256") == self._pinned:
                return REPO / e["file"]
        raise PinError(f"pinned snapshot {self._pinned[:12]} is not in the snapshot index")

    def dataset_spec(self) -> DatasetSpec:
        from vedic_astrology_core.stats.manifest import file_sha256

        path = self.snapshot_path()
        sha = file_sha256(path)
        grid = self.grid()
        return DatasetSpec(
            id=f"usgs_comcat_himalaya_{sha[:12]}",
            sha256=sha,
            source_id=SOURCE_ID,
            span=(str(grid[0].date()), str(grid[-1].date())),
            n_units=int(len(grid)),
            n_events=None,
        )

    # -- outcome-free ---------------------------------------------------
    def grid(self) -> pd.DatetimeIndex:
        """Hourly UTC grid over the plan's catalogue window (left edges)."""
        if self._grid is None:
            _, _, ind, *_ = _study_modules()
            cat = self.hyp["catalogue"]
            step = int(self.hyp["time_grid"]["step_hours"])
            self._grid = ind.time_grid(cat["start"], cat["end"], step)
        return self._grid

    def calendar_context(self) -> Mapping[str, Any]:
        from vedic_astrology_core.stats import controls

        g = self.grid()
        return {
            "step_hours": int(self.hyp["time_grid"]["step_hours"]),
            "timezone": "UTC",
            "monsoon_season": controls.monsoon_flag(g),
            "region": self.hyp["region"]["name"],
        }

    def periods(self) -> Periods:
        sp = self.hyp["split"]
        return Periods(
            explore=(_d(sp["explore"][0]), _d(sp["explore"][1])),
            confirm=(_d(sp["confirm"][0]), _d(sp["confirm"][1])),
            pseudo_out_of_sample=True,  # confirm years 2011 to 2026 were seen (ADR-004 D-2)
        )

    def declared_cells(self) -> Dict[str, Any]:
        """Sensitivity cells this adapter declares for the earthquake domain."""
        return {
            "declustering": {
                "primary": PRIMARY_METHOD,
                "sensitivity": [m for m in METHODS if m != PRIMARY_METHOD],
                "pending": ["etas (WP-26)"],
            },
            "second_dataset": {"id": "isc_bulletin", "status": "open"},
        }

    # -- gated ----------------------------------------------------------
    def catalogue(self) -> Tuple[pd.DataFrame, Dict]:
        """Analysed catalogue (Mw at or above the completeness threshold)."""
        *_, pipeline, _ = _study_modules()
        return pipeline.load_catalogue(self.snapshot_path())

    def mainshock_flags(self, cat: Optional[pd.DataFrame] = None) -> Dict[str, pd.Series]:
        """Boolean mainshock flags per declustering method.

        The nearest-neighbour threshold is fitted on explore-period events
        only and then applied to both periods (code audit m8): confirm-period
        events must not decide which explore events are mainshocks. Each
        event's proximity uses earlier events only, so it is past-only.
        """
        decluster, *_ = _study_modules()
        if cat is None:
            cat, _ = self.catalogue()
        log_eta = decluster.nearest_neighbour_eta(cat)
        per = self.periods()
        d = cat["time"].dt.tz_convert("UTC").dt.date
        explore = ((d >= per.explore[0]) & (d <= per.explore[1])).to_numpy()
        fit = decluster.gmm_threshold(log_eta[explore])
        fit["fitted_on"] = "explore"
        self.nn_fit = {k: v for k, v in fit.items() if k != "log10_eta"}
        nn = pd.Series(~(log_eta < fit["threshold"]), index=cat.index, name="mainshock_nn")
        return {
            "gk": decluster.gardner_knopoff(cat),
            "nn": nn,
            "raw": pd.Series(True, index=cat.index, name="raw"),
        }

    def _outcomes(self) -> Mapping[str, Any]:
        _, _, ind, *_ = _study_modules()
        cat, info = self.catalogue()
        flags = self.mainshock_flags(cat)
        grid = self.grid()
        per = self.periods()
        bins_by_method: Dict[str, np.ndarray] = {}
        counts: Dict[str, Dict[str, int]] = {}
        for name, keep in flags.items():
            ev = cat[keep.to_numpy()]
            bins_by_method[name] = ind.event_bins(ev["time"], grid)
            d = ev["time"].dt.tz_convert("UTC").dt.date
            counts[name] = {
                "all": int(len(ev)),
                "explore": int(((d >= per.explore[0]) & (d <= per.explore[1])).sum()),
                "confirm": int(((d >= per.confirm[0]) & (d <= per.confirm[1])).sum()),
            }
        return {
            "declustering": self.declustering,
            "event_bins": bins_by_method[self.declustering],
            "event_bins_by_method": bins_by_method,
            "mainshock_counts": counts,
            "n_analysed": int(len(cat)),
            "completeness": info["completeness"],
            "catalogue_info": {k: v for k, v in info.items() if k != "all_mw"},
        }

    def _controls(self) -> Mapping[str, Any]:
        """Control principles: the tidal positive control and shifted-sky negatives."""
        cfg = self.hyp["controls"]
        pos = cfg["positive"]
        per_day = int(round(24 / int(self.hyp["time_grid"]["step_hours"])))
        n = len(self.grid())
        min_shift = int(self.hyp["test"]["min_shift_days"])
        base = int(cfg["negative"]["offset_days"])
        # A distribution of shifts: the registered offset plus evenly spaced ones.
        span = n // per_day - 2 * min_shift
        offsets = sorted({base, *(int(min_shift + span * k / 9) for k in range(10))})
        return {
            "positive": [
                {"id": f"control.{s['id']}", "kind": "positive", "label": s["label"],
                 "direction": s["direction"]}
                for s in pos["indicators"]
            ],
            "negative": [
                {"id": f"control.shifted_sky@{o}d", "kind": "negative", "offset_days": o,
                 "offset_steps": o * per_day}
                for o in offsets
            ],
            "tidal_frame": self.tidal_frame,
            "shifted_sky": self.shifted_sky,
            "decision": {"period": pos["decision_period"], "catalogues": pos["decision_catalogues"]},
        }

    def tidal_frame(self, eph: pd.DataFrame) -> pd.DataFrame:
        """Tidal-phase indicator columns on an ephemeris frame of the grid."""
        *_, rb = _study_modules()
        return rb.tidal_frame(eph, self.hyp["controls"])

    @staticmethod
    def shifted_sky(frame: pd.DataFrame, offset_steps: int) -> pd.DataFrame:
        """The calendar rotated by a fixed offset against the fixed event series."""
        from vedic_astrology_core.stats import controls

        return controls.shifted_sky(frame, offset_steps)
