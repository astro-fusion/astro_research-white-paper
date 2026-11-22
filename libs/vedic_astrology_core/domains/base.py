"""Domain adapter protocol and dataset grades (ADR-007 section 4, WP-67).

An adapter gives the pipeline: the dataset with its hash and grade, the time
grid, the calendar context, the outcomes, the controls and the explore and
confirm periods. Two entry points are kept apart on purpose:

- :meth:`DomainAdapter.calendar_context` and :meth:`DomainAdapter.grid` read
  no outcome. The gate step may call only these.
- :meth:`DomainAdapter.outcomes` raises unless it is given a written gate
  record: the pipeline writes `gate.json` first (:func:`write_gate`) and
  passes the returned :class:`GateRecord` (or the hash and `gate_path`).
  The file must exist, be a JSON object, and its SHA-256 must equal the
  hash, so a made-up 64-hex string no longer opens the outcomes (code audit
  m9, strategy audit S-05 d).

Grades (ADR-007 4.1) are computed from the snapshot index, the licence
register and the dataset grade register (`data/registry/dataset_grades.yaml`,
ADR-008 D-05). `reproduced`, `open_items` and `quality_flaws` come only from
that register; each row names a checker and a date, or it grades C. They are
never written by hand: :class:`DatasetSpec` has no grade field and the
adapters take no such arguments.

- A: in the index, hash matches, licence read (`verified` and `date_read`),
  reproduced independently, no open item.
- B: in the index with a known licence, but a licence is unread or an open
  item remains. Verdicts allowed; the open items print as limitations.
- C: not in the index, unknown source, hash mismatch, or a known quality flaw.
  No verdict (Untestable: data quality).
"""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import yaml

GRADES = ("A", "B", "C")
REPO = Path(__file__).resolve().parents[3]
GRADES_PATH = REPO / "data" / "registry" / "dataset_grades.yaml"
FESTIVAL_SPOTCHECK_PATH = REPO / "data" / "registry" / "festival_spotcheck.yaml"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class DatasetGradeError(RuntimeError):
    """A verdict was requested on a grade C dataset."""


class GateHashError(RuntimeError):
    """`outcomes()` was called without a valid, written gate record."""


@dataclass(frozen=True)
class GateRecord:
    """A gate file on disk and the SHA-256 of its bytes."""

    path: Path
    sha256: str


def write_gate(path: Union[str, Path], record: Mapping[str, Any]) -> GateRecord:
    """Write `gate.json` (sorted keys) and return its record. Outcome-free."""
    if not isinstance(record, Mapping):
        raise TypeError("a gate record is a mapping")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(dict(record), indent=2, sort_keys=True, default=str) + "\n").encode()
    p.write_bytes(data)
    return GateRecord(p, hashlib.sha256(data).hexdigest())


def verify_gate(gate: Any, gate_path: Optional[Union[str, Path]] = None) -> GateRecord:
    """Check a gate against the written file; return the verified record.

    `gate` is a :class:`GateRecord`, or a SHA-256 hex string with
    `gate_path`. Raises :class:`GateHashError` when the hash is malformed,
    the file is missing or not a JSON object, or its bytes hash differently.
    """
    if isinstance(gate, GateRecord):
        if gate_path is not None and Path(gate_path) != gate.path:
            raise GateHashError("gate_path differs from the gate record's path")
        sha, path = gate.sha256, gate.path
    else:
        sha, path = gate, gate_path
    if not isinstance(sha, str) or not _HEX64.match(sha):
        raise GateHashError(
            "outcomes and controls need the SHA-256 of gate.json; "
            "the gate must be written before outcomes are read"
        )
    if path is None:
        raise GateHashError(
            "a gate hash alone cannot be verified; pass the GateRecord from "
            "write_gate() or the gate_path of the written gate.json"
        )
    p = Path(path)
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise GateHashError(f"gate file {p} cannot be read: {exc}") from exc
    if hashlib.sha256(data).hexdigest() != sha:
        raise GateHashError(f"gate hash does not match the bytes of {p}")
    try:
        parsed = json.loads(data)
    except ValueError as exc:
        raise GateHashError(f"gate file {p} is not JSON") from exc
    if not isinstance(parsed, dict):
        raise GateHashError(f"gate file {p} is not a JSON object")
    return GateRecord(p, sha)


@dataclass(frozen=True)
class DatasetSpec:
    """What a plan says about a dataset. Carries no grade."""

    id: str
    sha256: str
    source_id: str
    span: Tuple[str, str]
    n_units: int
    n_events: Optional[int] = None


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


def load_grade_register(path: Union[str, Path] = GRADES_PATH) -> List[dict]:
    """Rows of the dataset grade register (ADR-008 D-05).

    Each row has `sha256` (one snapshot) or `source_id` (every snapshot of
    that source), the inputs `reproduced`, `open_items`, `quality_flaws`, and
    `checked_by` and `date`. A missing file is an empty register.
    """
    p = Path(path)
    if not p.is_file():
        return []
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    rows = doc.get("rows", []) if isinstance(doc, Mapping) else doc
    if not isinstance(rows, list):
        raise ValueError(f"{p}: 'rows' must be a list")
    out = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping) or not (("sha256" in row) ^ ("source_id" in row)):
            raise ValueError(f"{p}: rows[{i}] needs exactly one of 'sha256' or 'source_id'")
        out.append(dict(row))
    return out


def _row_problem(row: Mapping[str, Any]) -> Optional[str]:
    who, when = row.get("checked_by"), row.get("date")
    if not (isinstance(who, str) and who.strip()) or not when or not str(when).strip():
        key = row.get("sha256") or row.get("source_id")
        return f"grade register row for {str(key)[:12]} has no named checker or date"
    return None


def compute_grade(
    spec: DatasetSpec,
    index: Mapping[str, Any],
    licences: Mapping[str, Mapping[str, Any]],
    register: Optional[Iterable[Mapping[str, Any]]] = None,
) -> Tuple[str, Tuple[str, ...]]:
    """Grade and limitation list from the index, licence and grade registers.

    `index` is the parsed `data/snapshot_index.json`; `licences` is the
    `source_id -> record` mapping of `data/registry/licences.yaml`; `register`
    is the rows of `data/registry/dataset_grades.yaml` (default: that file).
    """
    rows = list(load_grade_register() if register is None else register)
    mine = [r for r in rows if r.get("sha256") == spec.sha256 or
            (r.get("source_id") == spec.source_id and "sha256" not in r)]
    flaws: List[str] = []
    items: List[str] = []
    reproduced = False
    for r in mine:
        bad = _row_problem(r)
        if bad:
            return "C", (bad,)
        flaws += [str(x) for x in r.get("quality_flaws") or ()]
        items += [str(x) for x in r.get("open_items") or ()]
        if r.get("sha256") == spec.sha256 and r.get("reproduced"):
            reproduced = True
    if flaws:
        return "C", tuple(flaws)
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
    if not reproduced:
        limits.append("not yet reproduced independently")
    limits.extend(items)
    return ("B" if limits else "A"), tuple(limits)


def deposit_problems(
    index: Mapping[str, Any], sha256s: Iterable[str]
) -> List[str]:
    """ADR-008 D-04: every snapshot a sealed plan uses is deposited or archived.

    A snapshot passes with `deposit_doi` (a DOI string) or with
    `owner_archive: true` and a non-empty `owner_archive_reason`. Unknown
    hashes fail. The build calls this with the hashes of each sealed plan.
    """
    out = []
    for sha in sha256s:
        e = _snapshot_entry(sha, index)
        if e is None:
            out.append(f"{sha[:12]}: not in the snapshot index")
        elif e.get("deposit_doi"):
            continue
        elif e.get("owner_archive") is True and str(e.get("owner_archive_reason") or "").strip():
            continue
        else:
            out.append(
                f"{e.get('file', sha[:12])}: no deposit_doi, and no owner_archive with a reason"
            )
    return out


def festival_spotcheck_problems(
    path: Union[str, Path] = FESTIVAL_SPOTCHECK_PATH,
    leap_years: Iterable[int] = (),
) -> List[str]:
    """ADR-008 D-09: the festival baseline needs an external spot-check table.

    The table (`data/registry/festival_spotcheck.yaml`) lists almanac dates
    supplied by the owner. Each row needs `festival`, `year`, `date` (the
    almanac's) and `reference`. Every year in `leap_years` (years with an
    adhika month) needs at least one row. Empty list means the baseline may be used.
    """
    p = Path(path)
    if not p.is_file():
        return [f"{p.name}: spot-check table not found"]
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    rows = doc.get("rows") or []
    problems: List[str] = []
    years = set()
    for i, r in enumerate(rows):
        if not isinstance(r, Mapping):
            problems.append(f"rows[{i}]: not a mapping")
            continue
        miss = [k for k in ("festival", "year", "date", "reference") if not r.get(k)]
        if miss:
            problems.append(f"rows[{i}]: missing {miss}")
        else:
            years.add(int(r["year"]))
    if not rows:
        problems.append("no almanac dates supplied yet (owner task)")
    for y in sorted(set(int(v) for v in leap_years) - years):
        problems.append(f"leap-month year {y} has no spot-check row")
    return problems


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
        grades: Optional[Iterable[Mapping[str, Any]]] = None,
    ) -> None:
        self._index = index
        self._licences = licences
        self._grades = None if grades is None else list(grades)

    # -- outcome-free entry points -------------------------------------
    @abstractmethod
    def dataset_spec(self) -> DatasetSpec:
        """The dataset the plan names (no grade)."""

    def dataset(self) -> DomainDataset:
        """Dataset with its hash and a grade computed from the registers."""
        spec = self.dataset_spec()
        grade, limits = compute_grade(spec, self._index, self._licences, self._grades)
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

    def outcomes(self, gate: Any = None, *, gate_path: Optional[Union[str, Path]] = None
                 ) -> Mapping[str, Any]:
        """Outcomes; raises unless a written gate record verifies (:func:`verify_gate`)."""
        self._require_gate_hash(gate, gate_path)
        return self._outcomes()

    def controls(self, gate: Any = None, *, gate_path: Optional[Union[str, Path]] = None
                 ) -> Mapping[str, Any]:
        """Controls may include outcome-derived series, so they are gated too."""
        self._require_gate_hash(gate, gate_path)
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
    def _require_gate_hash(gate: Any, gate_path: Optional[Union[str, Path]] = None) -> GateRecord:
        return verify_gate(gate, gate_path)
