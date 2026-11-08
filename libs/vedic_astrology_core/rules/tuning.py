"""Schema v2 blocks: tunable ``params``, graded ``strength``, and the record.

A rule declares its tunable knobs once, with a range::

    params:
      orb: {value: 8, min: 2, max: 12, step: 1, unit: deg}

and refers to them anywhere in ``conditions``, ``window`` or ``strength`` as
``$orb``. Nothing else is tunable. ``astro-rules fit`` writes the
append-only ``tuning_log``; ``astro-rules confirm`` writes ``validation``
once per rule version; ``astro-rules review`` appends to ``review``.
"""

import copy
import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .predicates import PlanetName

PARAM_NAME = r"^[a-z][a-z0-9_]*$"
PARAM_REF = re.compile(r"^\$([a-z][a-z0-9_]*)$")
UNITS = ("deg", "days", "hours", "weeks", "months", "years", "count", "au", "ratio")


class Strict(BaseModel):
    """Base model: unknown keys are errors."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ------------------------------------------------------------------ params
class Param(Strict):
    """One tunable parameter: its current value and the range ``fit`` may try."""

    value: float
    min: float
    max: float
    step: float = Field(gt=0)
    unit: Literal[UNITS]  # type: ignore[valid-type]
    note: Optional[str] = None

    @model_validator(mode="after")
    def _range(self):
        if self.min > self.max:
            raise ValueError(f"min {self.min:g} is above max {self.max:g}")
        if not self.min <= self.value <= self.max:
            raise ValueError(
                f"value {self.value:g} lies outside its range "
                f"[{self.min:g}, {self.max:g}]"
            )
        return self

    def grid(self) -> List[float]:
        """Every value from ``min`` to ``max`` in steps of ``step``."""
        n = int(round((self.max - self.min) / self.step))
        values = [round(self.min + i * self.step, 10) for i in range(n + 1)]
        return [v for v in values if v <= self.max + 1e-9]


def find_refs(value: Any) -> Set[str]:
    """Every ``$name`` referenced anywhere inside ``value``."""
    found: Set[str] = set()
    if isinstance(value, str):
        match = PARAM_REF.match(value)
        if match:
            found.add(match.group(1))
    elif isinstance(value, dict):
        for item in value.values():
            found |= find_refs(item)
    elif isinstance(value, list):
        for item in value:
            found |= find_refs(item)
    return found


def substitute(value: Any, values: Dict[str, float]) -> Any:
    """Return a copy of ``value`` with each ``$name`` replaced by its value."""
    if isinstance(value, str):
        match = PARAM_REF.match(value)
        if match:
            name = match.group(1)
            if name not in values:
                raise ValueError(
                    f"unknown parameter '${name}': declare it under params "
                    f"(declared: {', '.join(sorted(values)) or 'none'})"
                )
            number = values[name]
            return int(number) if float(number).is_integer() else number
        return value
    if isinstance(value, dict):
        return {k: substitute(v, values) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, values) for v in value]
    return value


def param_values(raw_params: Any) -> Dict[str, float]:
    """``{name: value}`` from a raw ``params`` mapping (unvalidated input)."""
    if not isinstance(raw_params, dict):
        return {}
    out = {}
    for name, spec in raw_params.items():
        if isinstance(spec, dict) and isinstance(spec.get("value"), (int, float)):
            out[str(name)] = float(spec["value"])
    return out


BOUND_FIELDS = ("conditions", "window", "strength")


def bind_template(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Set[str]]:
    """Substitute every ``$param`` in a raw rule; return (data, names used)."""
    values = param_values(data.get("params"))
    used: Set[str] = set()
    out = dict(data)
    for key in BOUND_FIELDS:
        if key in out and out[key] is not None:
            used |= find_refs(out[key])
            out[key] = substitute(copy.deepcopy(out[key]), values)
    return out, used


# ---------------------------------------------------------------- strength
class OrbClosenessBody(Strict):
    """1 at exact conjunction, falling linearly to 0 at ``orb`` degrees."""

    planets: List[PlanetName] = Field(min_length=2, max_length=2)
    orb: float = Field(gt=0, le=30)


class AspectClosenessBody(Strict):
    """1 at the exact ``angle``, falling linearly to 0 at ``orb`` from it."""

    planets: List[PlanetName] = Field(min_length=2, max_length=2)
    angle: float = Field(ge=0, le=180)
    orb: float = Field(gt=0, le=30)


class DignityWeightBody(Strict):
    """Uccha bala / 60 (BPHS Ch. 27): 1 at deep exaltation, 0 at deep fall."""

    planet: PlanetName

    @field_validator("planet")
    @classmethod
    def _visible(cls, value):
        if value in ("Rahu", "Ketu"):
            raise ValueError("uccha bala is defined for the Sun to Saturn only")
        return value


class DashaWeightBody(Strict):
    """1 if ``lord`` runs the mahadasha, 1/2 the antardasha, 1/4 the third level."""

    lord: PlanetName
    levels: List[int] = Field(default_factory=lambda: [1, 2], min_length=1)

    @field_validator("levels")
    @classmethod
    def _levels(cls, value):
        if any(level not in (1, 2, 3) for level in value):
            raise ValueError("dasha levels are 1, 2 or 3")
        return value


class OrbCloseness(Strict):
    """Strength term ``orb_closeness``."""

    orb_closeness: OrbClosenessBody


class AspectCloseness(Strict):
    """Strength term ``aspect_closeness``."""

    aspect_closeness: AspectClosenessBody


class DignityWeight(Strict):
    """Strength term ``dignity_weight``."""

    dignity_weight: DignityWeightBody


class DashaWeight(Strict):
    """Strength term ``dasha_weight``."""

    dasha_weight: DashaWeightBody


StrengthTerm = Union[OrbCloseness, AspectCloseness, DignityWeight, DashaWeight]
TERM_NAMES = ("orb_closeness", "aspect_closeness", "dignity_weight", "dasha_weight")


class Strength(Strict):
    """Graded output in [0, 1] while the rule fires; absent means binary."""

    combine: Literal["product", "min", "mean"] = "product"
    terms: List[StrengthTerm] = Field(min_length=1)  # type: ignore[valid-type]

    @field_validator("terms", mode="before")
    @classmethod
    def _known(cls, value):
        for term in value if isinstance(value, list) else []:
            if not (isinstance(term, dict) and len(term) == 1):
                raise ValueError(
                    "each strength term has one key: " + ", ".join(TERM_NAMES)
                )
            key = next(iter(term))
            if key not in TERM_NAMES:
                raise ValueError(
                    f"unknown strength term '{key}'; use one of "
                    + ", ".join(TERM_NAMES)
                )
        return value


# ------------------------------------------------------------------ record
class GridRange(Strict):
    """The range one parameter was swept over."""

    min: float
    max: float
    step: float


class ExploreResult(Strict):
    """The chosen cell's explore-period numbers."""

    rate_ratio: Optional[float] = None
    ci: List[Optional[float]] = Field(default_factory=list)
    p: Optional[float] = None
    q_within_grid: Optional[float] = None
    n_cells: int = Field(ge=1)
    n_events: Optional[int] = None
    period: List[str] = Field(default_factory=list)


class TuningEntry(Strict):
    """One ``astro-rules fit`` run (append-only)."""

    at: AwareDatetime
    by: str = Field(min_length=1)
    study: str
    version: int = Field(ge=1)
    grid: Dict[str, GridRange] = Field(default_factory=dict)
    chosen: Dict[str, float] = Field(default_factory=dict)
    explore: ExploreResult
    spec_curve_artifact: Optional[str] = None
    note: Optional[str] = None


class ConfirmResult(Strict):
    """The single confirm-period run."""

    rate_ratio: Optional[float] = None
    ci: List[Optional[float]] = Field(default_factory=list)
    p: Optional[float] = None
    q_family: Optional[float] = None
    family: Optional[str] = None
    family_size: Optional[int] = None
    n_events: Optional[int] = None
    period: List[str] = Field(default_factory=list)
    direction: Optional[str] = None


class Validation(Strict):
    """Written once per rule version by ``astro-rules confirm``."""

    status: Literal["unvalidated", "confirmed", "not_confirmed"] = "unvalidated"
    version: Optional[int] = None
    study: Optional[str] = None
    confirm: Optional[ConfirmResult] = None
    at: Optional[AwareDatetime] = None
    commit: Optional[str] = None

    @model_validator(mode="after")
    def _stamped(self):
        if self.status != "unvalidated":
            missing = [
                k for k in ("version", "study", "confirm", "at") if not getattr(self, k)
            ]
            if missing:
                raise ValueError(
                    f"validation status {self.status} needs {', '.join(missing)}"
                )
        return self


class ReviewEntry(Strict):
    """An astrologer's sign-off that the encoding is faithful to the source."""

    by: str = Field(min_length=1)
    at: AwareDatetime
    verdict: Literal["faithful", "not_faithful"]
    note: str = Field(min_length=1)
    version: Optional[int] = None


def allow_param_refs(schema: Any, skip: Tuple[str, ...] = ("Param",)) -> Any:
    """Let every number in a JSON Schema also be a ``$param`` reference string."""
    ref = {"type": "string", "pattern": PARAM_REF.pattern}

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if node.get("type") in ("number", "integer"):
                inner = {k: v for k, v in node.items() if k not in ("title",)}
                out = {"anyOf": [inner, ref]}
                if "title" in node:
                    out["title"] = node["title"]
                return out
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    out = dict(schema)
    defs = out.get("$defs", {})
    out = {k: walk(v) if k != "$defs" else v for k, v in out.items()}
    out["$defs"] = {
        name: (body if name in skip else walk(body)) for name, body in defs.items()
    }
    return out


__all__ = [
    "BOUND_FIELDS",
    "ConfirmResult",
    "ExploreResult",
    "GridRange",
    "PARAM_NAME",
    "PARAM_REF",
    "Param",
    "ReviewEntry",
    "Strength",
    "StrengthTerm",
    "TERM_NAMES",
    "TuningEntry",
    "Validation",
    "allow_param_refs",
    "bind_template",
    "find_refs",
    "param_values",
    "substitute",
]
