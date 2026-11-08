"""The rule file format (Pydantic v2), exported as ``rules/schema.json``.

A rule is one YAML document::

    id: general.gaja_kesari.moon_kendra
    name: Gaja Kesari Yoga (Moon kendra form)
    domain: general
    claim: Jupiter in a kendra from the Moon gives fame and lasting wealth.
    source: {text: Brihat Parashara Hora Shastra, chapter: "36", verse: "3-4"}
    author: "@handle"
    tier: classical
    conditions:
      in_kendra_from: {planet: Jupiter, from: Moon}
    reference_cases:
      - {moment: "2000-01-01T12:00:00Z", expect: fires, note: "..."}

``conditions`` is a boolean tree: ``all``, ``any``, ``not`` and
``at_least`` nest freely; every leaf names one predicate from the closed
vocabulary in :mod:`.predicates`. Unknown keys anywhere are errors.
"""

import copy
import difflib
import json
from pathlib import Path
from typing import Annotated, Any, ClassVar, Dict, List, Literal, Optional, Union

import pytz
from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    PrivateAttr,
    Tag,
    create_model,
    field_validator,
    model_validator,
)

from .predicates import PREDICATES, Params
from .tuning import (
    PARAM_NAME,
    Param,
    ReviewEntry,
    Strength,
    TuningEntry,
    Validation,
    allow_param_refs,
    bind_template,
)

CONNECTIVES = ("all", "any", "not", "at_least")
ID_PATTERN = r"^[a-z0-9_]+(\.[a-z0-9_]+)+$"


class Strict(BaseModel):
    """Base model: unknown keys are errors."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --------------------------------------------------------------- conditions
def suggest(word: str, choices: List[str]) -> str:
    """Return " Did you mean 'x'?" for the closest choice, or ""."""
    guess = difflib.get_close_matches(str(word), choices, n=1, cutoff=0.5)
    return f" Did you mean '{guess[0]}'?" if guess else ""


def normalize_condition(value: Any) -> Any:
    """Expand the shorthand forms and reject unknown predicates early.

    Accepted shorthand (the ADR-001 style)::

        {planet: Jupiter, in_kendra_from: Moon}  -> in_kendra_from: {planet, from}
        {planet: Jupiter, not: combust}          -> not: {combust: {planet}}
        {planet: Venus, retrograde: true}        -> retrograde: {planet}
    """
    if not isinstance(value, dict):
        raise ValueError(
            "a condition must be a mapping such as "
            "'in_sign: {planet: Sun, signs: [Leo]}' or 'all: [...]', "
            f"got {value!r}"
        )
    if "planet" in value and len(value) == 2:
        key = next(k for k in value if k != "planet")
        arg = value[key]
        if key == "not" and isinstance(arg, str):
            return {"not": normalize_condition({"planet": value["planet"], arg: True})}
        if key in PREDICATES:
            spec = PREDICATES[key]
            if arg is True or arg is None:
                params = {"planet": value["planet"]}
            elif isinstance(arg, dict):
                params = {"planet": value["planet"], **arg}
            elif spec.shorthand:
                params = {"planet": value["planet"], spec.shorthand: arg}
            else:
                raise ValueError(
                    f"'{key}' needs its parameters as a mapping, e.g. "
                    f"{json.dumps(spec.example)}"
                )
            return {key: params}
    if len(value) != 1:
        raise ValueError(
            "a condition has exactly one key (a predicate, or all / any / not / "
            f"at_least); got {', '.join(map(str, value))}"
        )
    key = next(iter(value))
    if key not in CONNECTIVES and key not in PREDICATES:
        raise ValueError(
            f"unknown predicate '{key}'."
            + suggest(key, list(PREDICATES) + list(CONNECTIVES))
            + " Run 'astro-rules list --predicates' for the vocabulary."
        )
    return value


def _tag(value: Any) -> Optional[str]:
    if isinstance(value, dict) and len(value) == 1:
        return next(iter(value))
    if isinstance(value, BaseModel):
        return getattr(type(value), "tag", None)
    return None


class Leaf(Strict):
    """A condition that names one predicate."""

    tag: ClassVar[str] = ""

    @property
    def predicate(self) -> str:
        """The predicate name."""
        return self.tag

    @property
    def params(self) -> Params:
        """The validated predicate parameters."""
        return getattr(self, self.tag)


class AllOf(Strict):
    """Every child condition holds."""

    tag: ClassVar[str] = "all"
    all: List["Condition"] = Field(min_length=1)


class AnyOf(Strict):
    """At least one child condition holds."""

    tag: ClassVar[str] = "any"
    any: List["Condition"] = Field(min_length=1)


class NotOf(Strict):
    """The child condition does not hold."""

    tag: ClassVar[str] = "not"
    not_: "Condition" = Field(alias="not")


class AtLeastBody(Strict):
    """``n`` of the listed conditions must hold."""

    n: int = Field(ge=1)
    of: List["Condition"] = Field(min_length=1)

    @model_validator(mode="after")
    def _n_fits(self):
        if self.n > len(self.of):
            raise ValueError(f"n={self.n} but only {len(self.of)} conditions listed")
        return self


class AtLeast(Strict):
    """At least ``n`` of the listed conditions hold."""

    tag: ClassVar[str] = "at_least"
    at_least: AtLeastBody


def _leaf_model(name: str, params: type) -> type:
    model = create_model(  # type: ignore[call-overload]
        f"Leaf_{name}",
        __base__=Leaf,
        **{name: (params, Field(description=PREDICATES[name].doc.split("\n")[0]))},
    )
    model.tag = name
    return model


LEAF_MODELS = {
    name: _leaf_model(name, spec.params) for name, spec in PREDICATES.items()
}

_MEMBERS = [
    Annotated[AllOf, Tag("all")],
    Annotated[AnyOf, Tag("any")],
    Annotated[NotOf, Tag("not")],
    Annotated[AtLeast, Tag("at_least")],
] + [Annotated[model, Tag(name)] for name, model in LEAF_MODELS.items()]

_TaggedUnion = Annotated[  # type: ignore[valid-type]
    Union[tuple(_MEMBERS)],  # type: ignore[valid-type]
    Discriminator(_tag),
]
Condition = Annotated[
    _TaggedUnion, BeforeValidator(normalize_condition)  # type: ignore[valid-type]
]

for _model in (AllOf, AnyOf, NotOf, AtLeastBody, AtLeast):
    _model.model_rebuild()


# ---------------------------------------------------------- rule metadata
class Place(Strict):
    """Where a chart is cast: latitude, longitude (east +), IANA time zone."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    tz: str = "UTC"

    @field_validator("tz")
    @classmethod
    def _known_tz(cls, value: str) -> str:
        try:
            pytz.timezone(value)
        except pytz.UnknownTimeZoneError:
            raise ValueError(
                f"unknown time zone '{value}' (use an IANA name such as "
                "'Asia/Kathmandu' or 'UTC')"
            ) from None
        return value


class ChartSpec(Strict):
    """A natal chart: a person's birth or a nation's founding moment."""

    moment: AwareDatetime
    place: Optional[Place] = None
    label: Optional[str] = None


class Source(Strict):
    """Where the rule comes from.

    One of: a text with chapter (and verse), an application registry entry
    (``app_registry`` + ``id``), or a ``url``. A rule is ``classical`` only
    when it has both ``text`` and ``chapter``.
    """

    text: Optional[str] = None
    chapter: Optional[str] = None
    verse: Optional[str] = None
    edition: Optional[str] = None
    app_registry: Optional[str] = None
    id: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None

    @field_validator("chapter", "verse", "id", mode="before")
    @classmethod
    def _stringify(cls, value):
        return value if value is None else str(value)

    @model_validator(mode="after")
    def _one_kind(self):
        if not (self.text or (self.app_registry and self.id) or self.url):
            raise ValueError(
                "source needs {text, chapter, verse}, {app_registry, id} or {url}"
            )
        return self

    @property
    def cited(self) -> bool:
        """True when the source names a text and a chapter."""
        return bool(self.text and self.chapter)

    def short(self) -> str:
        """One-line citation."""
        if self.text:
            parts = [self.text]
            if self.chapter:
                parts.append(f"ch. {self.chapter}")
            if self.verse:
                parts.append(f"v. {self.verse}")
            return ", ".join(parts)
        if self.app_registry:
            return f"{self.app_registry} #{self.id}"
        return str(self.url)


class Window(Strict):
    """The time window in which the claimed effect is expected."""

    unit: Literal["hours", "days", "weeks", "months", "years"]
    before: Optional[float] = Field(default=None, ge=0)
    after: Optional[float] = Field(default=None, ge=0)
    note: Optional[str] = None


class ExpectedEffect(Strict):
    """What the rule predicts, for the statistics layer."""

    series: Optional[str] = None
    direction: Optional[Literal["up", "down", "increase", "decrease", "either"]] = None
    event: Optional[str] = None
    description: Optional[str] = None


class ReferenceCase(Strict):
    """A moment at which the rule is known to fire or stay silent."""

    moment: AwareDatetime
    place: Optional[Place] = None
    natal: Optional[ChartSpec] = None
    expect: Literal["fires", "silent"]
    note: str = Field(min_length=1)
    verified_with: Optional[str] = None


class Rule(Strict):
    """One astrological rule.

    Schema v2 adds ``params`` (tunable knobs with ranges, referenced as
    ``$name`` in ``conditions``, ``window`` and ``strength``), ``strength``
    (graded output), the append-only ``tuning_log``, the write-once
    ``validation`` stamp and the ``review`` sign-offs.
    """

    id: str = Field(pattern=ID_PATTERN, description="unique, lowercase, dotted")
    version: int = Field(
        default=1,
        ge=1,
        description="bump on any change to conditions, params or strength",
    )
    name: str = Field(min_length=1)
    domain: Literal["financial", "seismic", "mundane", "natal", "general"]
    claim: str = Field(min_length=1)
    source: Source
    author: str = Field(min_length=1)
    tier: Literal["classical", "experimental"]
    status: Literal["active", "needs_predicates", "needs_verification"] = "active"
    node_model: Literal["mean", "true"] = "mean"
    natal: Optional[ChartSpec] = None
    conditions: Optional[Condition]  # type: ignore[valid-type]
    window: Optional[Window] = None
    expected_effect: Optional[ExpectedEffect] = None
    reference_cases: List[ReferenceCase] = Field(default_factory=list)
    params: Dict[Annotated[str, Field(pattern=PARAM_NAME)], Param] = Field(
        default_factory=dict
    )
    strength: Optional[Strength] = None
    tuning_log: List[TuningEntry] = Field(default_factory=list)
    validation: Validation = Field(default_factory=Validation)
    validation_history: List[Validation] = Field(
        default_factory=list,
        description="stamps of earlier versions, moved here when a new version starts",
    )
    review: List[ReviewEntry] = Field(default_factory=list)
    notes: Optional[Dict[str, Any]] = None

    _template: Dict[str, Any] = PrivateAttr(default_factory=dict)

    @model_validator(mode="wrap")
    @classmethod
    def _bind_params(cls, data, handler):
        """Replace each ``$param`` with its value; keep the raw template."""
        if not isinstance(data, dict):
            return handler(data)
        bound, used = bind_template(data)
        declared = set(
            (data.get("params") or {}) if isinstance(data.get("params"), dict) else {}
        )
        unused = sorted(declared - used)
        if unused:
            raise ValueError(
                "parameter(s) declared but never referenced as $name: "
                + ", ".join(unused)
            )
        rule = handler(bound)
        rule._template = copy.deepcopy(data)
        return rule

    def bind(self, values: Dict[str, float]) -> "Rule":
        """Return this rule with ``params`` set to ``values`` (others unchanged).

        Raises:
            ValueError: unknown parameter name, or a value outside its range.
        """
        data = (
            copy.deepcopy(self._template)
            if self._template
            else (self.model_dump(by_alias=True, exclude_none=True))
        )
        params = data.get("params") or {}
        for name, value in values.items():
            if name not in params:
                raise ValueError(f"{self.id} has no parameter '{name}'")
            params[name]["value"] = value
        return Rule.model_validate(data)

    @property
    def param_values(self) -> Dict[str, float]:
        """``{name: current value}``."""
        return {name: p.value for name, p in self.params.items()}

    @model_validator(mode="after")
    def _consistent(self):
        if self.tier == "classical" and not self.source.cited:
            raise ValueError(
                "tier 'classical' needs a source with text and chapter; "
                "without them use tier: experimental"
            )
        if self.conditions is None and self.status != "needs_predicates":
            raise ValueError(
                "conditions: null is allowed only with status: needs_predicates"
            )
        if self.status == "needs_predicates":
            if self.tier != "experimental":
                raise ValueError("status needs_predicates requires tier experimental")
            return self
        expects = {case.expect for case in self.reference_cases}
        if self.tier == "classical" and expects != {"fires", "silent"}:
            raise ValueError(
                "a classical rule needs reference_cases with at least one "
                "'expect: fires' and one 'expect: silent'"
            )
        if not self.reference_cases:
            raise ValueError("a rule needs at least one reference case")
        return self


def json_schema() -> Dict[str, Any]:
    """Return the JSON Schema of a rule file."""
    schema = allow_param_refs(Rule.model_json_schema(by_alias=True))
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Astrological rule"
    return schema


def write_json_schema(path: Path) -> None:
    """Write the JSON Schema to ``path`` (``rules/schema.json``)."""
    path.write_text(json.dumps(json_schema(), indent=2, sort_keys=True) + "\n")


__all__ = [
    "AllOf",
    "AnyOf",
    "AtLeast",
    "ChartSpec",
    "Condition",
    "ExpectedEffect",
    "Leaf",
    "NotOf",
    "Place",
    "ReferenceCase",
    "Rule",
    "Source",
    "Window",
    "json_schema",
    "write_json_schema",
]
