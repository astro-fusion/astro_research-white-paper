"""The closed predicate vocabulary of the rule engine.

A predicate is a small pure function ``(context, params) -> Outcome`` that
says whether one astrological fact holds at a moment, and why, in plain
words. Each predicate declares a Pydantic parameter model with
``extra="forbid"``, so a typo such as ``orb_degs`` is an error rather than a
silent default. Rule authors only ever name predicates; developers add new
ones here, with a docstring giving the classical definition and tests.
"""

from dataclasses import dataclass, field
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
)

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    WithJsonSchema,
)

from ..context import EvalContext
from ..vocabulary import (
    LAGNA,
    all_aliases,
    nakshatra_name,
    planet_name,
    point_name,
    sign_name,
)


class Outcome(NamedTuple):
    """Result of one predicate: whether it held and the evidence in words."""

    held: bool
    evidence: str


def _as_list(value: Any) -> Any:
    return value if isinstance(value, list) else [value]


def _names(kind: str) -> Dict[str, Any]:
    return {"type": "string", "enum": all_aliases(kind)}


PlanetName = Annotated[
    str, AfterValidator(planet_name), WithJsonSchema(_names("planet"))
]
PointName = Annotated[str, AfterValidator(point_name), WithJsonSchema(_names("point"))]
SignName = Annotated[str, AfterValidator(sign_name), WithJsonSchema(_names("sign"))]
NakshatraName = Annotated[
    str, AfterValidator(nakshatra_name), WithJsonSchema(_names("nakshatra"))
]
House = Annotated[int, Field(ge=1, le=12)]

PlanetList = Annotated[List[PlanetName], BeforeValidator(_as_list), Field(min_length=1)]
SignList = Annotated[List[SignName], BeforeValidator(_as_list), Field(min_length=1)]
NakshatraList = Annotated[
    List[NakshatraName], BeforeValidator(_as_list), Field(min_length=1)
]
HouseList = Annotated[List[House], BeforeValidator(_as_list), Field(min_length=1)]


class Params(BaseModel):
    """Base for predicate parameters: unknown keys are errors."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, frozen=True)

    #: Fields whose point is read from the natal chart, not the sky now.
    natal_fields: ClassVar[Tuple[str, ...]] = ()

    def inputs(self) -> Set[str]:
        """Return inputs beyond the moment: "place", "natal", "natal_place"."""
        needed: Set[str] = set()
        for name in type(self).model_fields:
            if getattr(self, name) == LAGNA:
                needed.add("natal_place" if name in self.natal_fields else "place")
        return needed

    def label(self) -> str:
        """Short "key=value" rendering of the parameters the author wrote."""
        parts = []
        for name, info in type(self).model_fields.items():
            value = getattr(self, name)
            if value is None or name not in self.model_fields_set:
                continue
            key = info.alias or name
            if isinstance(value, list):
                value = "[" + ", ".join(str(v) for v in value) + "]"
            parts.append(f"{key}={value}")
        return ", ".join(parts)


@dataclass(frozen=True)
class PredicateSpec:
    """A registered predicate."""

    name: str
    params: Type[Params]
    func: Callable[[EvalContext, Any], Outcome]
    needs: frozenset = field(default_factory=frozenset)
    shorthand: Optional[str] = None
    category: str = ""
    example: Optional[Dict[str, Any]] = None

    @property
    def doc(self) -> str:
        """The predicate's docstring (its classical definition)."""
        return (self.func.__doc__ or "").strip()

    def inputs(self, params: Params) -> Set[str]:
        """All inputs this predicate needs for these parameters."""
        return set(self.needs) | params.inputs()


PREDICATES: Dict[str, PredicateSpec] = {}


def predicate(
    name: str,
    params: Type[Params],
    needs: Tuple[str, ...] = (),
    shorthand: Optional[str] = None,
    category: str = "",
    example: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Register ``func`` as predicate ``name`` with its parameter model."""

    def register(func: Callable) -> Callable:
        if name in PREDICATES:
            raise ValueError(f"predicate {name!r} registered twice")
        PREDICATES[name] = PredicateSpec(
            name, params, func, frozenset(needs), shorthand, category, example
        )
        return func

    return register


def check(ctx: EvalContext, name: str, **params: Any) -> Outcome:
    """Validate ``params`` and evaluate predicate ``name`` (handy in tests)."""
    spec = PREDICATES[name]
    return spec.func(ctx, spec.params.model_validate(params))


def house_from(from_sign: int, to_sign: int) -> int:
    """Whole-sign house (1-12) of ``to_sign`` counted from ``from_sign``."""
    return (to_sign - from_sign) % 12 + 1


def point_label(point: str) -> str:
    """Return "the Lagna" for the ascendant, else the planet's name."""
    return "the Lagna" if point == LAGNA else point


# Register the vocabulary (imports are for their side effect).
from . import placement, relations, timing, mundane  # noqa: E402,F401

__all__ = [
    "PREDICATES",
    "Outcome",
    "Params",
    "PredicateSpec",
    "check",
    "house_from",
    "predicate",
]
