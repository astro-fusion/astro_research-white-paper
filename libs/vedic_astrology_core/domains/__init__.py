"""Domain adapters for the validity pipeline (ADR-007 section 4)."""

from .base import (
    DatasetGradeError,
    DatasetSpec,
    DomainAdapter,
    DomainDataset,
    GateHashError,
    Periods,
    compute_grade,
    verdicts_allowed,
)

__all__ = [
    "DatasetGradeError",
    "DatasetSpec",
    "DomainAdapter",
    "DomainDataset",
    "GateHashError",
    "Periods",
    "compute_grade",
    "verdicts_allowed",
]
