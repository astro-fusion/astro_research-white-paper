"""Expand a rule file into the tests a domain plan registers (ADR-007 section 3.3 C, ADR-008 3.2 rule 8).

One rule gives, for every ``tests`` entry that names the domain:

* the **primary** test (variant id ``primary``);
* one test per declared **candidate** variant (its own slot and verdict), at
  most ``max_candidates`` per lineage (ADR-008 3.2 rule 8: "More go to the
  sensitivity grid"); the extra candidates, in file order, are demoted to
  sensitivity cells and listed in ``demoted``;
* the declared **sensitivity** variants as cells of the primary test (no
  slot, no verdict; robustness R3 only).

A variant changes declared ``params`` (within their ranges) and/or
``conventions``; nothing else exists, nothing is searched. A convention the
evaluator cannot compute (a tropical zodiac, which robustness refuses as a
rival system, or an ayanamsa other than the engine's) is never dropped in
silence: it is listed in ``not_computable`` and the caller refuses the test
(a declared cell that vanished would let R3 pass with less evidence).

Project-fixed operationalisation choices list their ``alternatives`` as
free text (schema 3.1, F-04). They are carried in ``declared_alternatives``
for the card; a free-text alternative is not a calendar, so it is not a cell.

Pure: reads no file and no outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..rules.schema import Rule, TestSpec, Variant
from .family import MAX_VARIANTS, PRIMARY

__all__ = [
    "VariantError",
    "Expansion",
    "ENGINE_AYANAMSA",
    "bound_rule",
    "convention_problems",
    "expand",
]

#: The ayanamsa the rule engine's grid evaluator computes (core/rules/context.py).
ENGINE_AYANAMSA = "lahiri"


class VariantError(ValueError):
    """A variant cannot be built (unknown id, a value out of range)."""


@dataclass(frozen=True)
class Expansion:
    """One registrable test of a rule: (rule version, variant, domain outcome).

    ``rule`` is the rule with the variant's params and conventions applied;
    ``sensitivity`` maps each sensitivity cell id to its bound rule (only on
    the primary test); ``demoted`` lists candidate ids moved to the
    sensitivity grid by rule 8; ``not_computable`` lists why a variant or
    cell cannot be evaluated.
    """

    rule_id: str
    version: int
    variant: str
    role: str  # "primary" | "candidate"
    test: TestSpec
    rule: Rule
    sensitivity: Mapping[str, Rule] = field(default_factory=dict)
    demoted: Tuple[str, ...] = ()
    not_computable: Tuple[str, ...] = ()
    declared_alternatives: Mapping[str, Tuple[Any, ...]] = field(default_factory=dict)

    @property
    def side(self) -> str:
        """The pipeline side of the test's claimed direction (no default)."""
        return {"increase": "greater", "decrease": "less", "either": "two-sided"}[self.test.direction]


def convention_problems(rule: Rule, variant: Optional[Variant] = None) -> List[str]:
    """Why the grid evaluator cannot compute this rule (or this variant of it)."""
    out: List[str] = []
    zodiac = rule.zodiac
    ayan = rule.ayanamsa
    if variant is not None and variant.conventions is not None:
        zodiac = variant.conventions.zodiac or zodiac
        ayan = variant.conventions.ayanamsa or ayan
    where = f"variant {variant.id}" if variant is not None else "rule"
    if zodiac == "tropical":
        out.append(f"{where}: a tropical zodiac is a rival system, not a cell (robustness.RIVAL_SYSTEMS)")
    if ayan is not None and str(ayan).strip().lower() != ENGINE_AYANAMSA:
        out.append(f"{where}: ayanamsa {ayan!r} is not computed by the grid evaluator ({ENGINE_AYANAMSA} only)")
    return out


def bound_rule(rule: Rule, variant: Optional[Variant]) -> Rule:
    """The rule with a variant's params and conventions applied (primary: unchanged)."""
    if variant is None:
        return rule
    try:
        out = rule.bind(dict(variant.params)) if variant.params else rule
    except ValueError as exc:
        raise VariantError(f"{rule.id} variant {variant.id}: {exc}") from exc
    conv = variant.conventions.model_dump(exclude_none=True) if variant.conventions else {}
    if conv:
        out = out.model_copy(update={k: v for k, v in conv.items() if k in ("node_model", "zodiac", "ayanamsa")})
    return out


def _alternatives(rule: Rule) -> Dict[str, Tuple[Any, ...]]:
    return {c.choice: tuple(c.alternatives) for c in rule.operationalisation
            if c.fixed_by == "project" and c.alternatives}


def expand(rule: Rule, domain: str, *, max_candidates: int = MAX_VARIANTS,
           outcomes: Optional[Sequence[str]] = None) -> List[Expansion]:
    """Every test of ``rule`` in ``domain`` (optionally only the named rule outcomes).

    Raises VariantError when a variant cannot be bound (a value out of range).
    """
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or max_candidates < 0:
        raise VariantError("max_candidates must be a non-negative integer")
    specs = [t for t in rule.tests if t.domain == domain and (outcomes is None or t.outcome in outcomes)]
    if not specs:
        return []
    candidates = [v for v in rule.variants if v.role == "candidate"]
    kept, demoted = candidates[:max_candidates], candidates[max_candidates:]
    cells: Dict[str, Rule] = {}
    problems: List[str] = list(convention_problems(rule))
    for v in [v for v in rule.variants if v.role == "sensitivity"] + demoted:
        problems += convention_problems(rule, v)
        cells[v.id] = bound_rule(rule, v)
    alts = _alternatives(rule)
    out: List[Expansion] = []
    for spec in specs:
        out.append(Expansion(rule.id, int(rule.version), PRIMARY, "primary", spec, rule,
                             dict(cells), tuple(v.id for v in demoted), tuple(problems), alts))
        for v in kept:
            vp = tuple(convention_problems(rule, v))
            out.append(Expansion(rule.id, int(rule.version), v.id, "candidate", spec, bound_rule(rule, v),
                                 {}, (), vp, alts))
    return out
