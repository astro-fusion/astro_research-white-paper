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
from .predicates import compose
from .tuning import (
    PARAM_NAME,
    Param as _BaseParam,
    ReviewEntry as _BaseReviewEntry,
    Strength,
    TuningEntry,
    Validation,
    allow_param_refs,
    bind_template,
    out_of_range,
)

CONNECTIVES = ("all", "any", "not", "at_least")
#: Leaves that name another rule instead of a predicate (schema v3).
REFERENCES = ("use",)
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
    if key not in CONNECTIVES and key not in REFERENCES and key not in PREDICATES:
        raise ValueError(
            f"unknown predicate '{key}'."
            + suggest(key, list(PREDICATES) + list(CONNECTIVES) + list(REFERENCES))
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


class UseTarget(Strict):
    """The rule a ``use`` leaf points at, optionally pinned to a version."""

    id: str = Field(pattern=ID_PATTERN)
    version: Optional[int] = Field(
        default=None,
        ge=1,
        description="refuse the parent at any other version",
    )


def _hide_expansion(schema: Dict[str, Any]) -> None:
    """The expanded parent conditions are not written by authors."""
    props = schema.get("properties", {})
    props.pop("all", None)
    if "use" in props:
        props["use"] = {
            "anyOf": [{"type": "string", "pattern": ID_PATTERN}, props["use"]],
            "description": "a rule id, or {id, version} to pin the version",
        }
    if "all" in schema.get("required", []):
        schema["required"] = [k for k in schema["required"] if k != "all"]


class _Expanded(dict):
    """Marks the data of a ``use`` leaf after its parent was expanded."""


class UseOf(AllOf):
    """The frozen primary conditions of another rule (schema v3).

    Written ``use: <rule id>`` or ``use: {id: <rule id>, version: <n>}``.
    On validation the parent's conditions, with its parameters bound, are
    expanded into ``all`` (one child), so the engine evaluates the leaf as
    an ordinary "all of" node. A missing id, a parent without conditions, a
    version that differs from the pin and a reference cycle are errors.
    """

    model_config = ConfigDict(json_schema_extra=_hide_expansion)

    tag: ClassVar[str] = "use"
    use: UseTarget
    all: List["Condition"] = Field(  # type: ignore[assignment]
        min_length=1, max_length=1, exclude=True
    )

    _resolved: Optional[compose.ResolvedUse] = PrivateAttr(default=None)

    @field_validator("use", mode="before")
    @classmethod
    def _shorthand(cls, value):
        return {"id": value} if isinstance(value, str) else value

    @model_validator(mode="wrap")
    @classmethod
    def _expand(cls, data, handler):
        if isinstance(data, (BaseModel, _Expanded)) or not isinstance(data, dict):
            return handler(data)  # pydantic may re-enter with the expansion
        if "all" in data:
            raise ValueError("'use' takes no other keys; write it as its own leaf")
        if "use" not in data:
            return handler(data)
        target = UseTarget.model_validate(cls._shorthand(data["use"]))
        resolved = compose.resolve(target.id, target.version)
        with compose.entering(target.id):
            node = handler(
                _Expanded(use=data["use"], all=[copy.deepcopy(resolved.conditions)])
            )
        node._resolved = resolved
        return node

    @property
    def resolved(self) -> Optional[compose.ResolvedUse]:
        """The parent as resolved: id, version, bound conditions and hashes."""
        return self._resolved


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
    Annotated[UseOf, Tag("use")],
] + [Annotated[model, Tag(name)] for name, model in LEAF_MODELS.items()]

_TaggedUnion = Annotated[  # type: ignore[valid-type]
    Union[tuple(_MEMBERS)],  # type: ignore[valid-type]
    Discriminator(_tag),
]
Condition = Annotated[
    _TaggedUnion, BeforeValidator(normalize_condition)  # type: ignore[valid-type]
]

for _model in (AllOf, AnyOf, NotOf, AtLeastBody, AtLeast, UseOf):
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


class Param(_BaseParam):
    """A tunable parameter plus the citation for its range (schema v2.1).

    ``range_source`` names where the range comes from: a verse, a named
    commentary, or "author's choice" stated as such. Optional so that older
    files load; level L2 requires it.
    """

    range_source: Optional[str] = Field(default=None, min_length=1)


class ReviewEntry(_BaseReviewEntry):
    """A review sign-off, plus the reviewer's blindness attestation (v2.1).

    ``blind_attestation`` is true when the reviewer states that they saw no
    test result for the rule. Level L4 requires it.
    """

    blind_attestation: Optional[bool] = None


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
    translator: Optional[str] = None
    page: Optional[str] = None
    quote: Optional[str] = Field(default=None, min_length=1)
    archive_url: Optional[str] = None
    published: Optional[str] = None
    checked_by: Optional[str] = None
    checked_on: Optional[str] = None
    app_registry: Optional[str] = None
    id: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None

    @field_validator(
        "chapter", "verse", "id", "page", "published", "checked_on", mode="before"
    )
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


# ------------------------------------------------------- schema v3 blocks
READING_KINDS = ("forward_trigger", "concurrent", "post_event_classification")
SLUG = r"^[a-z][a-z0-9_]*$"


class Reading(Strict):
    """Which reading of the source is tested (ADR-007 section 3.2).

    ``kind`` is how the project tests it; ``text_says`` is how the source
    uses it, when that differs or is known. The limitations section of the
    report is built from both.
    """

    kind: Literal[READING_KINDS]  # type: ignore[valid-type]
    text_says: Optional[Literal[READING_KINDS]] = None  # type: ignore[valid-type]
    note: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _explain_gap(self):
        if self.text_says and self.text_says != self.kind and not self.note:
            raise ValueError(
                f"the source reads it as {self.text_says} but it is tested as "
                f"{self.kind}; say why in note"
            )
        return self


class OperationalChoice(Strict):
    """One choice the source does not fix, and who fixed it."""

    choice: str = Field(min_length=1)
    value: Union[bool, int, float, str, List[Union[bool, int, float, str]]]
    fixed_by: Literal["text", "practitioner", "project"]
    note: Optional[str] = Field(default=None, min_length=1)


class TestSpec(Strict):
    """Where the principle is tested: one domain outcome, one slot."""

    __test__: ClassVar[bool] = False  # not a pytest class

    domain: str = Field(pattern=SLUG, description="validity domain, e.g. gold")
    outcome: str = Field(pattern=SLUG, description="outcome id in the domain plan")
    direction: Literal["increase", "decrease", "either"]
    note: Optional[str] = Field(default=None, min_length=1)


class Conventions(Strict):
    """Calculation conventions a variant may change (no condition changes)."""

    node_model: Optional[Literal["mean", "true"]] = None
    zodiac: Optional[Literal["sidereal", "tropical"]] = None
    ayanamsa: Optional[str] = Field(default=None, min_length=1)


class Variant(Strict):
    """A declared permutation of the principle; never searched.

    ``candidate``: one slot per outcome and its own verdict; needs a
    ``reason``. ``sensitivity``: no slot and no verdict; shown on the
    curve. A variant changes declared ``params`` (within their ranges)
    and/or ``conventions``, nothing else.
    """

    id: str = Field(pattern=SLUG)
    role: Literal["candidate", "sensitivity"]
    params: Dict[Annotated[str, Field(pattern=PARAM_NAME)], float] = Field(
        default_factory=dict
    )
    conventions: Optional[Conventions] = None
    reason: Optional[str] = Field(default=None, min_length=1)
    source: Optional[Source] = None

    @model_validator(mode="after")
    def _changes_something(self):
        if self.id == "primary":
            raise ValueError("variant id 'primary' is reserved for the rule itself")
        conv = self.conventions.model_dump(exclude_none=True) if self.conventions else {}
        if not self.params and not conv:
            raise ValueError(
                f"variant '{self.id}' changes nothing; give params or conventions"
            )
        if self.role == "candidate" and not self.reason:
            raise ValueError(f"candidate variant '{self.id}' needs a reason")
        return self


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
    zodiac: Optional[Literal["sidereal", "tropical"]] = None
    ayanamsa: Optional[str] = Field(default=None, min_length=1)
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
    reading: Optional[Reading] = None
    operationalisation: List[OperationalChoice] = Field(default_factory=list)
    tests: List[TestSpec] = Field(
        default_factory=list,
        description="where this principle is tested; one slot each (ADR-007)",
    )
    variants: List[Variant] = Field(default_factory=list)
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
        with compose.entering(data.get("id")):
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

    @property
    def uses(self) -> List[compose.ResolvedUse]:
        """The rules this rule's conditions point at with ``use``."""
        return compose.parents(self)

    def use_fingerprint(self) -> Dict[str, Any]:
        """Ids, versions and condition hashes of every ``use`` ancestor."""
        return compose.fingerprint(self)

    def variant(self, variant_id: str) -> Variant:
        """Return the declared variant ``variant_id``; KeyError otherwise."""
        for item in self.variants:
            if item.id == variant_id:
                return item
        raise KeyError(
            f"{self.id} has no variant '{variant_id}'."
            + suggest(variant_id, [v.id for v in self.variants])
        )

    @model_validator(mode="after")
    def _v3_blocks(self):
        if self.tests and (self.reading is None or not self.operationalisation):
            raise ValueError(
                "a rule with tests needs reading and operationalisation "
                "(ADR-007 F-9): say which reading is tested and every choice "
                "the source does not fix"
            )
        seen_tests = set()
        for test in self.tests:
            key = (test.domain, test.outcome)
            if key in seen_tests:
                raise ValueError(f"test {test.domain}.{test.outcome} is listed twice")
            seen_tests.add(key)
        choices = [c.choice for c in self.operationalisation]
        dup = sorted({c for c in choices if choices.count(c) > 1})
        if dup:
            raise ValueError(f"operationalisation lists {', '.join(dup)} twice")
        ids = [v.id for v in self.variants]
        dup = sorted({v for v in ids if ids.count(v) > 1})
        if dup:
            raise ValueError(f"variant id(s) used twice: {', '.join(dup)}")
        for item in self.variants:
            problems = out_of_range(self.params, item.params)
            if problems:
                raise ValueError(f"variant '{item.id}': " + "; ".join(problems))
        return self

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
    "Conventions",
    "ExpectedEffect",
    "Leaf",
    "NotOf",
    "OperationalChoice",
    "Param",
    "Place",
    "Reading",
    "ReferenceCase",
    "ReviewEntry",
    "Rule",
    "Source",
    "TestSpec",
    "UseOf",
    "UseTarget",
    "Variant",
    "Window",
    "json_schema",
    "write_json_schema",
]
