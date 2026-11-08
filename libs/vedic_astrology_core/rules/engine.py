"""Evaluate a rule at a moment and explain, in plain words, why it fired."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Set, Union

from .context import EvalContext, Location
from .predicates import PREDICATES
from .schema import AllOf, AnyOf, AtLeast, ChartSpec, Leaf, NotOf, Place, Rule

PlaceLike = Union[Place, Location, Dict[str, Any], None]


class RuleNotEvaluable(ValueError):
    """The rule has no machine conditions yet (status: needs_predicates)."""


@dataclass
class ExplainNode:
    """One condition, whether it held, and the evidence."""

    condition: str
    held: bool
    evidence: str = ""
    children: List["ExplainNode"] = field(default_factory=list)

    def render(self, indent: int = 0) -> str:
        """Indented plain-text tree, one condition per line."""
        mark = "HOLDS" if self.held else "FAILS"
        line = "  " * indent + f"[{mark}] {self.condition}"
        if self.evidence:
            line += f": {self.evidence}"
        return "\n".join([line] + [c.render(indent + 1) for c in self.children])

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly form."""
        return {
            "condition": self.condition,
            "held": self.held,
            "evidence": self.evidence,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class Evaluation:
    """Result of evaluating a rule at one moment."""

    rule_id: str
    fired: bool
    tree: ExplainNode

    def render(self) -> str:
        """Plain-text explanation."""
        verdict = "FIRES" if self.fired else "is SILENT"
        return f"{self.rule_id} {verdict}\n{self.tree.render(1)}"


def to_location(place: PlaceLike) -> Optional[Location]:
    """Accept a :class:`Place`, :class:`Location`, dict or None."""
    if place is None or isinstance(place, Location):
        return place
    if isinstance(place, Place):
        return Location(place.lat, place.lon, place.tz)
    return to_location(Place.model_validate(place))


def explain_condition(cond: Any, ctx: EvalContext) -> ExplainNode:
    """Evaluate one condition tree node, keeping the evidence."""
    if isinstance(cond, AllOf):
        kids = [explain_condition(c, ctx) for c in cond.all]
        n = sum(k.held for k in kids)
        return ExplainNode("all of", n == len(kids), f"{n} of {len(kids)} held", kids)
    if isinstance(cond, AnyOf):
        kids = [explain_condition(c, ctx) for c in cond.any]
        n = sum(k.held for k in kids)
        return ExplainNode("any of", n > 0, f"{n} of {len(kids)} held", kids)
    if isinstance(cond, NotOf):
        kid = explain_condition(cond.not_, ctx)
        return ExplainNode("not", not kid.held, "", [kid])
    if isinstance(cond, AtLeast):
        body = cond.at_least
        kids = [explain_condition(c, ctx) for c in body.of]
        n = sum(k.held for k in kids)
        return ExplainNode(
            f"at least {body.n} of",
            n >= body.n,
            f"{n} of {len(kids)} held, {body.n} needed",
            kids,
        )
    if isinstance(cond, Leaf):
        spec = PREDICATES[cond.predicate]
        outcome = spec.func(ctx, cond.params)
        return ExplainNode(
            f"{cond.predicate}({cond.params.label()})", outcome.held, outcome.evidence
        )
    raise TypeError(f"not a condition: {cond!r}")


def iter_leaves(cond: Any) -> Iterator[Leaf]:
    """Every predicate leaf in a condition tree."""
    if cond is None:
        return
    if isinstance(cond, Leaf):
        yield cond
    elif isinstance(cond, AllOf):
        for c in cond.all:
            yield from iter_leaves(c)
    elif isinstance(cond, AnyOf):
        for c in cond.any:
            yield from iter_leaves(c)
    elif isinstance(cond, NotOf):
        yield from iter_leaves(cond.not_)
    elif isinstance(cond, AtLeast):
        for c in cond.at_least.of:
            yield from iter_leaves(c)


def rule_inputs(rule: Rule) -> Set[str]:
    """Return the inputs beyond a moment the rule needs (place, natal, ...)."""
    needed: Set[str] = set()
    for leaf in iter_leaves(rule.conditions):
        needed |= PREDICATES[leaf.predicate].inputs(leaf.params)
    return needed


def build_context(
    rule: Rule,
    moment: datetime,
    place: PlaceLike = None,
    natal: Optional[ChartSpec] = None,
) -> EvalContext:
    """Context for ``rule`` at ``moment``; the rule's own natal is the default."""
    natal = natal or rule.natal
    natal_pair = None
    if natal is not None:
        natal_pair = (natal.moment, to_location(natal.place))
    return EvalContext.at(moment, to_location(place), natal_pair, rule.node_model)


def evaluate_context(rule: Rule, ctx: EvalContext) -> Evaluation:
    """Evaluate ``rule`` in a prepared context."""
    if rule.conditions is None:
        raise RuleNotEvaluable(
            f"{rule.id} has no machine conditions yet (status: {rule.status})"
        )
    tree = explain_condition(rule.conditions, ctx)
    return Evaluation(rule.id, tree.held, tree)


def evaluate(
    rule: Rule,
    moment: datetime,
    place: PlaceLike = None,
    natal: Optional[ChartSpec] = None,
) -> Evaluation:
    """Return whether ``rule`` fires at ``moment``, with the explain tree."""
    return evaluate_context(rule, build_context(rule, moment, place, natal))


def explain(
    rule: Rule,
    moment: datetime,
    place: PlaceLike = None,
    natal: Optional[ChartSpec] = None,
) -> ExplainNode:
    """Return the explain tree of ``rule`` at ``moment`` (see :func:`evaluate`)."""
    return evaluate(rule, moment, place, natal).tree


@dataclass
class CaseResult:
    """Outcome of one reference case."""

    rule_id: str
    index: int
    expected: str
    fired: Optional[bool]
    tree: Optional[ExplainNode] = None
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        """True when the rule did what the case expects."""
        return self.error is None and self.fired == (self.expected == "fires")


def run_reference_cases(rule: Rule) -> List[CaseResult]:
    """Evaluate every reference case of ``rule``."""
    results = []
    for i, case in enumerate(rule.reference_cases):
        try:
            result = evaluate(rule, case.moment, case.place, case.natal)
        except (ValueError, KeyError) as exc:
            results.append(CaseResult(rule.id, i, case.expect, None, error=str(exc)))
            continue
        results.append(CaseResult(rule.id, i, case.expect, result.fired, result.tree))
    return results


__all__ = [
    "CaseResult",
    "Evaluation",
    "ExplainNode",
    "RuleNotEvaluable",
    "build_context",
    "evaluate",
    "evaluate_context",
    "explain",
    "explain_condition",
    "iter_leaves",
    "rule_inputs",
    "run_reference_cases",
    "to_location",
]
