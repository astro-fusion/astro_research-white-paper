"""A toy domain for tests (ADR-007 WP-67). Yearly grid, seeded outcomes.

It builds its own in-memory snapshot index and licence register from the
generated data, so the grade goes through the same `compute_grade` as a real
adapter.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from .base import DatasetSpec, DomainAdapter, Periods

SOURCE_ID = "simulated"


def simulated_registers(
    sha256: str, *, verified: bool = True, date_read: Optional[str] = "2026-11-22"
) -> Tuple[dict, dict]:
    """In-memory (index, licences) holding one simulated snapshot."""
    index = {
        "schema": 1,
        "snapshots": [{"file": "sim.csv", "sha256": sha256, "source_id": SOURCE_ID}],
    }
    licences = {SOURCE_ID: {"verified": verified, "date_read": date_read}}
    return index, licences


def simulated_grades(
    sha256: str,
    *,
    reproduced: bool = True,
    open_items: Sequence[str] = (),
    quality_flaws: Sequence[str] = (),
    checked_by: Optional[str] = "simulated test checker",
    date: Optional[str] = "2026-11-22",
) -> list:
    """In-memory grade register rows for one simulated snapshot."""
    return [{
        "sha256": sha256, "reproduced": reproduced, "open_items": list(open_items),
        "quality_flaws": list(quality_flaws), "checked_by": checked_by, "date": date,
    }]


class SimulatedDomain(DomainAdapter):
    """Yearly toy series: Gaussian outcome, optional planted effect."""

    domain = "simulated"

    def __init__(
        self,
        *,
        seed: int = 0,
        n_years: int = 100,
        start_year: int = 1900,
        effect: float = 0.0,
        grades: Optional[Sequence[Mapping[str, Any]]] = None,
        index: Optional[Mapping[str, Any]] = None,
        licences: Optional[Mapping[str, Mapping[str, Any]]] = None,
    ) -> None:
        self.seed, self.n_years, self.start_year = seed, n_years, start_year
        self.effect = effect
        self.outcome_reads = 0
        rng = np.random.default_rng(seed)
        self._active = (np.arange(n_years) % 4 == 0).astype(float)
        self._values = rng.normal(size=n_years) + effect * self._active
        self.sha256 = hashlib.sha256(self._values.tobytes()).hexdigest()
        if index is None or licences is None:
            index, licences = simulated_registers(self.sha256)
        if grades is None:
            grades = simulated_grades(self.sha256)
        super().__init__(index, licences, grades)

    def dataset_spec(self) -> DatasetSpec:
        return DatasetSpec(
            id=f"simulated_{self.seed}",
            sha256=self.sha256,
            source_id=SOURCE_ID,
            span=(str(self.start_year), str(self.start_year + self.n_years - 1)),
            n_units=self.n_years,
        )

    def grid(self) -> Sequence[date]:
        return [date(self.start_year + i, 1, 1) for i in range(self.n_years)]

    def calendar_context(self) -> Mapping[str, Any]:
        years = np.arange(self.start_year, self.start_year + self.n_years)
        return {"year": years, "decade": years // 10 * 10}

    def periods(self) -> Periods:
        cut = self.start_year + int(self.n_years * 0.6)
        return Periods(
            explore=(date(self.start_year, 1, 1), date(cut - 1, 12, 31)),
            confirm=(date(cut, 1, 1), date(self.start_year + self.n_years - 1, 12, 31)),
        )

    def _outcomes(self) -> Dict[str, np.ndarray]:
        self.outcome_reads += 1
        return {"value": self._values.copy()}

    def _controls(self) -> Dict[str, np.ndarray]:
        rng = np.random.default_rng(self.seed + 1)
        return {"shifted": np.roll(self._active, int(rng.integers(1, self.n_years)))}
