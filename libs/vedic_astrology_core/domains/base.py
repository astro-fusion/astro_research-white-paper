"""Domain adapter protocol and dataset grades (ADR-007 section 4, WP-67).

An adapter gives the pipeline: the dataset with its hash and grade, the time
grid, the calendar context, the outcomes, the controls and the explore and
confirm periods. Two entry points are kept apart on purpose:

- :meth:`DomainAdapter.calendar_context` and :meth:`DomainAdapter.grid` read
  no outcome. The gate step may call only these.
- :meth:`DomainAdapter.outcomes` raises unless a gate hash is passed. The
  pipeline writes `gate.json` and its hash first, then passes the hash here.

Grades (ADR-007 4.1) are computed from the snapshot index and the licence
register plus the open items a plan declares. They are never written by hand:
:class:`DatasetSpec` has no grade field.

- A: in the index, hash matches, licence read (`verified` and `date_read`),
  reproduced independently, no open item.
- B: in the index with a known licence, but a licence is unread or an open
  item remains. Verdicts allowed; the open items print as limitations.
- C: not in the index, unknown source, hash mismatch, or a known quality flaw.
  No verdict (Untestable: data quality).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

GRADES = ("A", "B", "C")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class DatasetGradeError(RuntimeError):
    """A verdict was requested on a grade C dataset."""


class GateHashError(RuntimeError):
    """`outcomes()` was called without a valid gate hash."""


@dataclass(frozen=True)
class DatasetSpec:
    """What a plan says about a dataset. Carries no grade."""

    id: str
    sha256: str
    source_id: str
    span: Tuple[str, str]
    n_units: int
    n_events: Optional[int] = None
    reproduced: bool = False
    open_items: Tuple[str, ...] = ()
    quality_flaws: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DomainDataset:
    """A dataset entry with its computed grade and limitations."""

    spec: DatasetSpec
    grade: str
    limitations: Tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def sha256(self) -> str:
        return self.spec.sha256

    def as_record(self) -> Dict[str, Any]:
        """The `dataset` entry of the result record (ADR-007 section 7)."""
        return {
            "id": self.spec.id,
            "grade": self.grade,
            "sha256": self.spec.sha256,
            "span": list(self.spec.span),
            "n_units": self.spec.n_units,
            "n_events": self.spec.n_events,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class Periods:
    """Explore and confirm periods, inclusive date bounds, explore first."""

    explore: Tuple[date, date]
    confirm: Tuple[date, date]
    pseudo_out_of_sample: bool = False

    def __post_init__(self) -> None:
        for name, (a, b) in (("explore", self.explore), ("confirm", self.confirm)):
            if a > b:
                raise ValueError(f"{name} period starts after it ends")
        if self.explore[1] >= self.confirm[0]:
            raise ValueError("explore period must end before the confirm period starts")


def _snapshot_entry(sha256: str, index: Mapping[str, Any]) -> Optional[dict]:
    for entry in index.get("snapshots", []):
        if entry.get("sha256") == sha256:
            return entry
    return None


def compute_grade(
    spec: DatasetSpec,
    index: Mapping[str, Any],
    licences: Mapping[str, Mapping[str, Any]],
) -> Tuple[str, Tuple[str, ...]]:
    """Grade and limitation list from the index and licence register.

    `index` is the parsed `data/snapshot_index.json`; `licences` is the
    `source_id -> record` mapping of `data/registry/licences.yaml`.
    """
    if spec.quality_flaws:
        return "C", tuple(spec.quality_flaws)
    if not _HEX64.match(spec.sha256 or ""):
        return "C", ("dataset hash is not a SHA-256",)
    entry = _snapshot_entry(spec.sha256, index)
    if entry is None:
        return "C", ("dataset hash is not in the snapshot index",)
    if entry.get("source_id") != spec.source_id:
        return "C", ("snapshot source differs from the plan's source",)
    record = licences.get(spec.source_id)
    if record is None:
        return "C", (f"source {spec.source_id!r} is not in the licence register",)
    limits = []
    if not (record.get("verified") and record.get("date_read")):
        limits.append("licence not yet read")
    if not spec.reproduced:
        limits.append("not yet reproduced independently")
    limits.extend(spec.open_items)
    return ("B" if limits else "A"), tuple(limits)


def verdicts_allowed(grade: str) -> bool:
    """Grade C blocks every verdict; A and B allow all."""
    if grade not in GRADES:
        raise ValueError(f"unknown grade {grade!r}")
    return grade != "C"


class DomainAdapter(ABC):
    """Protocol every domain adapter implements."""

    domain: str = ""

    def __init__(
        self,
        index: Mapping[str, Any],
        licences: Mapping[str, Mapping[str, Any]],
    ) -> None:
        self._index = index
        self._licences = licences

    # -- outcome-free entry points -------------------------------------
    @abstractmethod
    def dataset_spec(self) -> DatasetSpec:
        """The dataset the plan names (no grade)."""

    def dataset(self) -> DomainDataset:
        """Dataset with its hash and a grade computed from the registers."""
        spec = self.dataset_spec()
        grade, limits = compute_grade(spec, self._index, self._licences)
        return DomainDataset(spec, grade, limits)

    @abstractmethod
    def grid(self) -> Sequence[Any]:
        """The time grid. Reads no outcome."""

    @abstractmethod
    def calendar_context(self) -> Mapping[str, Any]:
        """Non-outcome context for calendars (season flags, weekday...)."""

    @abstractmethod
    def periods(self) -> Periods:
        """Explore and confirm periods."""

    # -- outcome entry points ------------------------------------------
    @abstractmethod
    def _outcomes(self) -> Mapping[str, Any]:
        """Return outcomes. Called only through :meth:`outcomes`."""

    @abstractmethod
    def _controls(self) -> Mapping[str, Any]:
        """Return controls. Called only through :meth:`controls`."""

    def outcomes(self, gate_hash: Optional[str] = None) -> Mapping[str, Any]:
        """Outcomes; raises unless a gate hash (SHA-256 hex) is passed."""
        self._require_gate_hash(gate_hash)
        return self._outcomes()

    def controls(self, gate_hash: Optional[str] = None) -> Mapping[str, Any]:
        """Controls may include outcome-derived series, so they are gated too."""
        self._require_gate_hash(gate_hash)
        return self._controls()

    def require_verdict_grade(self) -> DomainDataset:
        """Return the dataset, or raise when grade C blocks verdicts."""
        ds = self.dataset()
        if not verdicts_allowed(ds.grade):
            raise DatasetGradeError(
                f"{self.domain or 'domain'}: dataset {ds.id} is grade C "
                f"({'; '.join(ds.limitations)}); Untestable: data quality"
            )
        return ds

    @staticmethod
    def _require_gate_hash(gate_hash: Optional[str]) -> None:
        if not isinstance(gate_hash, str) or not _HEX64.match(gate_hash):
            raise GateHashError(
                "outcomes and controls need the SHA-256 of gate.json; "
                "the gate must be written before outcomes are read"
            )
