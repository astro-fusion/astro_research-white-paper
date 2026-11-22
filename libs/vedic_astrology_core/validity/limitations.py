"""The limitations builder (ADR-007 section 6, WP-72; wording per ADR-008 7.1).

Every principle card carries a "Limits of this test" box. Nobody writes it by
hand: :func:`build_limitations` builds it from the rule file, the domain plan,
the dataset entry, the calendar and the gate record. One row per line of
ADR-007 section 6, always in the same order:

1. citation level            6. data span and quality
2. tradition                 7. evidence amount
3. reading tested            8. what was not tested
4. choices the text leaves   9. separability
5. conventions              10. seen before
                            11. disputes

A rule with no ``reading`` or no ``operationalisation`` cannot get a box and
raises :class:`LimitationError` (ADR-007 F-9). A row whose input is missing is
still printed, as "not recorded", so that an absent input never flatters a rule.
Rows that need a trigger (separability, seen before, disputes) appear only when
it holds.

Wording: below L4 the first line says the words about this principle are about
the project's encoding (ADR-008 7.1). No row says "validated", "proven" or
anything about astrology as a whole. Pure Python; no outcome is read and no
network is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from pydantic import BaseModel

from ..rules import levels as _levels
from ..rules.schema import Leaf, Rule
from .sentences import ENCODING_LEVEL, UNTESTABLE_REASONS

__all__ = [
    "KINDS",
    "Limitation",
    "LimitationError",
    "build_limitations",
    "require_registrable",
    "separable_from_calendar",
]

#: Row kinds in card order.
KINDS = (
    "citation_level",
    "tradition",
    "reading_tested",
    "choices",
    "conventions",
    "data",
    "evidence_amount",
    "not_tested",
    "separability",
    "seen_before",
    "disputes",
)

#: Predicates that read a stretch of the zodiac; with the Sun they track the calendar year.
_SKY_PREDICATES = ("in_sign", "longitude_between", "in_nakshatra", "varga_sign")
#: R4 fails at or above this baseline R^2 (ADR-007 6.1 item 5).
R4_MAX_BASELINE_R2 = 0.5

_READING_WORDS = {
    "forward_trigger": "a trigger that comes before the event",
    "concurrent": "something present at the same time as the event",
    "post_event_classification": "a classification made after the event",
}


class LimitationError(ValueError):
    """The rule cannot get a limits box; ``problems`` lists what is missing."""

    def __init__(self, rule_id: str, problems: Iterable[str]):
        self.rule_id = rule_id
        self.problems = list(problems)
        super().__init__(f"{rule_id}: no limits box can be built: " + "; ".join(self.problems))


@dataclass(frozen=True)
class Limitation:
    """One line of the limits box: its row ``kind`` and its ``text``."""

    kind: str
    text: str

    def to_dict(self) -> Dict[str, str]:
        return {"kind": self.kind, "text": self.text}


# ------------------------------------------------------------------ helpers
def require_registrable(rule: Rule) -> None:
    """Raise :class:`LimitationError` when reading or operationalisation is missing."""
    problems: List[str] = []
    if rule.reading is None:
        problems.append("reading: not stated")
    if not rule.operationalisation:
        problems.append("operationalisation: no choice is recorded")
    if problems:
        raise LimitationError(rule.id, problems)


def _sentence(text: str) -> str:
    text = " ".join(str(text).split())
    return text if text.endswith((".", "!", "?")) else text + "."


def _fmt(x: Any) -> str:
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.3g}"
    if isinstance(x, (list, tuple)):
        return ", ".join(_fmt(v) for v in x)
    return str(x)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _walk_leaves(node: Any) -> Iterable[Leaf]:
    if isinstance(node, Leaf):
        yield node
    if isinstance(node, BaseModel):
        for name in type(node).model_fields:
            yield from _walk_leaves(getattr(node, name))
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_leaves(item)


def separable_from_calendar(rule: Rule) -> Optional[str]:
    """Name the Sun predicate that makes the rule a calendar variable, or None.

    A condition that places the Sun in a sign, nakshatra or longitude band is
    the same variable as a stretch of the calendar year.
    """
    for leaf in _walk_leaves(rule.conditions):
        if leaf.predicate in _SKY_PREDICATES and getattr(leaf.params, "planet", None) == "Sun":
            return leaf.predicate
    return None


# --------------------------------------------------------------------- rows
def _citation(rule: Rule, report: Any) -> str:
    n = report.level
    parts = [f"Level L{n} ({report.name})."]
    parts.append(f"Source: {rule.source.short()}.")
    if n < ENCODING_LEVEL:
        parts.append(
            "No independent astrologer has attested the encoding, so every verdict is "
            "about the project's encoding of the rule."
        )
    nxt = report.next_missing if n < 6 else []
    if nxt:
        shown = "; ".join(nxt[:4]) + (" and more" if len(nxt) > 4 else "")
        parts.append(f"Missing for L{n + 1}: {shown}.")
    return " ".join(_sentence(p) for p in parts)


def _tradition(rule: Rule) -> str:
    src = rule.source
    if rule.tier == "classical" and src.cited:
        return f"Classical source: {src.short()}."
    if src.text and src.chapter:
        return (
            f"Modern practice. The rule is attributed to {src.short()} through a "
            "practitioner, not read from the classical text."
        )
    return (
        "Modern practice. No classical chapter is cited for it"
        + (f" ({src.short()})." if src.short() else ".")
    )


def _reading(rule: Rule) -> str:
    r = rule.reading
    kind = _READING_WORDS[r.kind]
    if r.text_says is None:
        text = (
            f"Tested as {kind}. The project does not record how the source reads it, "
            "so a null here may not test the source's own claim."
        )
    elif r.text_says == r.kind:
        text = f"The source reads it as {kind}, and it was tested the same way."
    else:
        text = (
            f"The text reads it as {_READING_WORDS[r.text_says]}. We tested it as {kind}. "
            "A null here does not test the text's own claim."
        )
        if r.note:
            text += " " + r.note
    return _sentence(text)


def _choices(rule: Rule) -> str:
    lines: List[str] = []
    for c in rule.operationalisation:
        if c.fixed_by == "text":
            continue
        who = "chosen by the project" if c.fixed_by == "project" else "taken from a practitioner"
        line = f"{c.choice}: {_fmt(c.value)}, {who}"
        if c.alternatives:
            line += f". Other values: {_fmt(c.alternatives)}"
        elif c.fixed_by == "project":
            line += ". No alternatives are recorded"
        lines.append(_sentence(line))
    for name, param in rule.params.items():
        if not getattr(param, "range_source", None):
            lines.append(_sentence(f"{name} = {_fmt(param.value)}: no source is cited for its range"))
    if not lines:
        return "Every choice is fixed by the text; none is left to the project."
    return " ".join(lines)


def _conventions(rule: Rule) -> str:
    zodiac = rule.zodiac or "not stated"
    ayanamsa = rule.ayanamsa or "not stated"
    parts = [f"Zodiac {zodiac}, ayanamsa {ayanamsa}, {rule.node_model} node"]
    if "node_model" not in rule.model_fields_set:
        parts[0] += " (default, not stated in the file)"
    by_name = {c.choice: c for c in rule.operationalisation}
    for name, label in (("place", "place"), ("day_convention", "day convention"), ("horizon", "horizon")):
        c = by_name.get(name)
        parts.append(f"{label} {_fmt(c.value)}" if c is not None else f"{label} not recorded")
    return _sentence(", ".join(parts))


def _data(dataset: Optional[Mapping]) -> str:
    if not dataset:
        return "Data span and quality: not recorded."
    parts: List[str] = []
    span = _get(dataset, "span")
    if span:
        if isinstance(span, (list, tuple)) and len(span) == 2:
            parts.append(f"{span[0]} to {span[1]} only")
        else:
            parts.append(f"{_fmt(span)} only")
    else:
        parts.append("Span not recorded")
    grade = _get(dataset, "grade")
    parts.append(f"data grade {grade}" if grade else "grade not recorded")
    unit = _get(dataset, "unit") or _get(dataset, "currency")
    if unit:
        parts.append(f"values in {unit}")
    licence = _get(dataset, "licence")
    if licence in (None, "", "unread", "unknown"):
        parts.append("licence not yet read")
    elif licence not in ("ok", "cleared", "read"):
        parts.append(f"licence: {_fmt(licence)}")
    for item in _get(dataset, "open_items") or ():
        parts.append(f"open item: {_fmt(item)}")
    return _sentence(". ".join(p[0].upper() + p[1:] for p in parts))


def _evidence(calendar: Optional[Mapping], gate: Any) -> str:
    if not calendar:
        return "Evidence amount: not recorded."
    duty = _get(calendar, "duty_cycle")
    n_conf = _get(calendar, "episodes_confirm")
    mde = _get(calendar, "mde_confirm", _get(gate, "mde_confirm") if gate is not None else None)
    parts = []
    parts.append(f"Active {duty * 100:.0f}% of the time" if duty is not None else "Active share not recorded")
    parts.append(
        f"{n_conf} episode{'s' if n_conf != 1 else ''} in the confirm period"
        if n_conf is not None
        else "confirm-period episodes not recorded"
    )
    text = _sentence(", ".join(parts))
    text += (
        f" Smallest detectable effect: {_fmt(mde)}."
        if mde is not None
        else " Smallest detectable effect: not recorded."
    )
    return text


def _reason_words(codes: Iterable[str]) -> List[str]:
    return [UNTESTABLE_REASONS.get(c, str(c).replace("_", " ")) for c in codes]


def _not_tested(rule: Rule, plan: Optional[Mapping], gate: Any) -> str:
    lines: List[str] = []
    if plan:
        domain = plan.get("domain")
        planned = [o.get("id") for o in plan.get("outcomes") or [] if isinstance(o, Mapping)]
        tested = {t.outcome for t in rule.tests if t.domain == domain}
        missing = [o for o in planned if o and o not in tested]
        if missing:
            lines.append(f"Not tested on {_fmt(missing)}: the rule file names no test for {'it' if len(missing) == 1 else 'them'}.")
        extra = sorted(tested - set(planned))
        if extra:
            lines.append(f"Named in the rule but absent from the {domain} plan: {_fmt(extra)}.")
    else:
        lines.append("Outcomes of the domain: plan not recorded.")
    if gate is not None:
        sup = _reason_words(_get(gate, "support_failed", ()) or ())
        lim = _reason_words(_get(gate, "limit_failed", ()) or ())
        if sup:
            lines.append(f"Support was not reachable: {_fmt(sup)}.")
        if lim:
            lines.append(f"No effect could be excluded: {_fmt(lim)}.")
    return " ".join(lines) if lines else "Every outcome of the domain plan has a test, and the gate raised no failure."


def _separability(rule: Rule, r4: Any) -> Optional[str]:
    pred = separable_from_calendar(rule)
    r2 = None
    if r4 is not None:
        if isinstance(r4, (int, float)) and not isinstance(r4, bool):
            r2 = float(r4)
        else:
            detail = _get(r4, "detail") or r4
            r2 = _get(detail, "baseline_r2")
            r2 = None if r2 is None else float(r2)
    fails = r2 is not None and r2 >= R4_MAX_BASELINE_R2
    if pred is None and not fails:
        return None
    if pred is not None:
        text = (
            "The Sun's position here is almost the same variable as a stretch of the calendar year. "
            "A calendar effect cannot be told apart."
        )
    else:
        text = "The calendar is almost the same variable as the calendar year. A calendar effect cannot be told apart."
    if r2 is not None:
        text += f" The baselines alone explain {r2 * 100:.0f}% of its variation."
    return text


def _seen_before(plan: Optional[Mapping]) -> Optional[str]:
    if not plan:
        return None
    seen = [v.get("id") for v in plan.get("vintages") or [] if isinstance(v, Mapping) and v.get("seen") is True]
    if plan.get("pseudo_out_of_sample") is True and not seen:
        seen = ["the plan"]
    if not seen:
        return None
    return "The confirm years were looked at in an earlier study (" + _fmt(seen) + ")."


def _disputes(rule: Rule, disputes: Iterable[str]) -> Optional[str]:
    if rule.id not in set(disputes):
        return None
    return "Schools disagree on the sign of this effect; the test is two-sided."


# ----------------------------------------------------------------- the box
def build_limitations(
    rule: Rule,
    *,
    plan: Optional[Mapping] = None,
    dataset: Optional[Mapping] = None,
    calendar: Optional[Mapping] = None,
    gate: Any = None,
    r4: Any = None,
    disputes: Iterable[str] = (),
    level_report: Optional[_levels.LevelReport] = None,
    evidence: Optional[_levels.Evidence] = None,
) -> List[Limitation]:
    """Build the limits box of one test, in the order of ADR-007 section 6.

    Args:
        rule: The registered rule (needs ``reading`` and ``operationalisation``).
        plan: The domain plan mapping (outcomes, vintages).
        dataset: The dataset entry: span, grade, unit or currency, licence,
            open_items.
        calendar: duty_cycle, episodes_confirm and optionally mde_confirm.
        gate: A GateResult or its dict (support_failed, limit_failed).
        r4: The R4 baseline R^2 (float), a CheckResult or its dict.
        disputes: Rule ids named in the DISPUTES.md files.
        level_report: A computed level; default is levels.level(rule, evidence).

    Raises:
        LimitationError: reading or operationalisation is missing.
    """
    require_registrable(rule)
    report = level_report or _levels.level(rule, evidence)
    rows = [
        ("citation_level", _citation(rule, report)),
        ("tradition", _tradition(rule)),
        ("reading_tested", _reading(rule)),
        ("choices", _choices(rule)),
        ("conventions", _conventions(rule)),
        ("data", _data(dataset)),
        ("evidence_amount", _evidence(calendar, gate)),
        ("not_tested", _not_tested(rule, plan, gate)),
        ("separability", _separability(rule, r4)),
        ("seen_before", _seen_before(plan)),
        ("disputes", _disputes(rule, disputes)),
    ]
    return [Limitation(k, t) for k, t in rows if t]
