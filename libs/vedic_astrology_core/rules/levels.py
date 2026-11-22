"""Validation levels L0 to L6, computed from the evidence (ADR-004 D-4, WP-20).

A level is never typed into a rule file. :func:`level` reads the rule and an
optional :class:`Evidence` (reference-case results and cross-check fixtures)
and returns a :class:`LevelReport`: the highest level whose conditions, and
those of every level below it, are met, plus what is missing for the next one.

=====  ==================================================================
L0     loads against the schema
L1     sourced: text, edition, translator, chapter, verse or page, quote
       (or url, published date, archive link) and a maintainer check
L2     operationalised: conditions, every param with a range_source,
       expected_effect.direction, zodiac, ayanamsa and node model stated
L3     computationally verified: reference cases pass, >= 3 agree with a
       manual Jagannatha Hora reading, Horizons instants agree
L4     faithful: a review by a named non-author who attests to blindness
L5     explored: a logged fit
L6     confirmed or refuted: a confirm stamp for the current version
=====  ==================================================================

"Validated principle" means L4 and faithful encoding only. A rule may enter a
confirmatory family at L3 or above (:data:`FAMILY_MIN_LEVEL`).

Cross-check fixtures (ADR-004 WP-21) are JSON files carrying ``rule_id``,
``source`` (``jhora_manual`` counts; ``pyjhora`` does not), a non-empty
``reader`` and ``agrees`` (false disqualifies the file). Each JHora file is
one agreeing reference case; each Horizons file with the rule's id and
``agrees: true`` counts toward the Horizons check.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .schema import Rule

LEVEL_NAMES = {
    0: "Recorded",
    1: "Sourced",
    2: "Operationalised",
    3: "Computationally verified",
    4: "Faithful",
    5: "Explored",
    6: "Confirmed or refuted",
}
FAMILY_MIN_LEVEL = 3
MIN_JHORA_CASES = 3


@dataclass(frozen=True)
class Evidence:
    """Evidence that cannot be read from the rule file alone (L3).

    ``None`` means "not checked", which does not satisfy the level.
    """

    cases_pass: Optional[bool] = None
    n_cases: int = 0
    jhora_cases: int = 0
    horizons_ok: Optional[bool] = None


@dataclass
class LevelReport:
    """The computed level and what each level still lacks."""

    rule_id: str
    level: int
    missing: Dict[int, List[str]] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Name of the reached level."""
        return LEVEL_NAMES[self.level]

    @property
    def label(self) -> str:
        """An L2-style label."""
        return f"L{self.level}"

    @property
    def next_missing(self) -> List[str]:
        """What is missing for the next level (empty at L6)."""
        return self.missing.get(self.level + 1, [])

    def render(self) -> str:
        """Human-readable report."""
        lines = [f"{self.rule_id}: {self.label} {self.name}"]
        if self.level < 6:
            lines.append(f"missing for L{self.level + 1} {LEVEL_NAMES[self.level + 1]}:")
            lines += [f"  - {m}" for m in self.next_missing]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-friendly form."""
        return {
            "rule": self.rule_id,
            "level": self.level,
            "name": self.name,
            "missing": {f"L{k}": v for k, v in sorted(self.missing.items())},
        }


def _norm(handle: str) -> str:
    return handle.strip().lstrip("@").casefold()


def _l1(rule: Rule) -> List[str]:
    s = rule.source
    out: List[str] = []
    if s.text:
        for name in ("edition", "translator", "chapter", "quote"):
            if not getattr(s, name):
                out.append(f"source.{name}")
        if not (s.verse or s.page):
            out.append("source.verse or source.page")
    elif s.url:
        for name in ("published", "archive_url", "quote"):
            if not getattr(s, name):
                out.append(f"source.{name}")
    else:
        out.append(
            "a citable source: text (with edition, translator, chapter, verse "
            "or page, quote) or url (with published, archive_url, quote)"
        )
    if not (s.checked_by and s.checked_on):
        out.append("a maintainer check: source.checked_by and source.checked_on")
    return out


def _l2(rule: Rule) -> List[str]:
    out: List[str] = []
    if rule.conditions is None:
        out.append("structured conditions (conditions is null)")
    for name, param in rule.params.items():
        if not getattr(param, "range_source", None):
            out.append(f"params.{name}.range_source")
    if not (rule.expected_effect and rule.expected_effect.direction):
        out.append("expected_effect.direction")
    if rule.zodiac is None:
        out.append("zodiac (sidereal or tropical)")
    if rule.ayanamsa is None:
        out.append("ayanamsa")
    if "node_model" not in rule.model_fields_set:
        out.append("node_model stated explicitly")
    return out


def _l3(rule: Rule, ev: Optional[Evidence]) -> List[str]:
    ev = ev or Evidence()
    out: List[str] = []
    if rule.status != "active":
        out.append(f"status active (it is {rule.status})")
    if ev.cases_pass is None:
        out.append("reference cases not run (pass Evidence or use the CLI)")
    elif not ev.cases_pass:
        out.append("every reference case must pass")
    if ev.jhora_cases < MIN_JHORA_CASES:
        out.append(
            f"{MIN_JHORA_CASES - ev.jhora_cases} more reference case(s) agreeing with "
            f"a manual Jagannatha Hora reading to 1 arcminute (have {ev.jhora_cases})"
        )
    if not ev.horizons_ok:
        out.append("Horizons agreement to 5 arcseconds for the instants involved")
    return out


def _l4(rule: Rule) -> List[str]:
    for entry in rule.review:
        if entry.verdict != "faithful":
            continue
        if entry.version not in (None, rule.version):
            continue
        if _norm(entry.by) == _norm(rule.author):
            continue
        if entry.blind_attestation is True:
            return []
    return [
        "a review with verdict faithful for this version, by a named reviewer who "
        "is not the rule's author and attests blind_attestation: true"
    ]


def _l5(rule: Rule) -> List[str]:
    return [] if rule.tuning_log else ["a logged fit (tuning_log entry)"]


def _l6(rule: Rule) -> List[str]:
    v = rule.validation
    if v.status != "unvalidated" and v.version == rule.version:
        return []
    return [f"a confirm stamp for version {rule.version} (astro-rules confirm)"]


def level(rule: Rule, evidence: Optional[Evidence] = None) -> LevelReport:
    """Compute the validation level of the rule.

    The level is the highest N such that levels 1..N are all met. The report's
    missing mapping holds, for every unmet level, what that level lacks.
    """
    checks = {
        1: _l1(rule),
        2: _l2(rule),
        3: _l3(rule, evidence),
        4: _l4(rule),
        5: _l5(rule),
        6: _l6(rule),
    }
    reached = 0
    for n in range(1, 7):
        if checks[n]:
            break
        reached = n
    missing = {n: m for n, m in checks.items() if m}
    return LevelReport(rule.id, reached, missing)


def _fixture_files(directory: Path) -> List[dict]:
    docs = []
    if directory.is_dir():
        for path in sorted(directory.rglob("*.json")):
            try:
                doc = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if isinstance(doc, dict):
                docs.append(doc)
    return docs


def default_fixture_dir() -> Path:
    """The tests/fixtures directory of the repository checkout."""
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def fixture_evidence(
    rule: Rule,
    cases_pass: Optional[bool],
    fixtures: Optional[Path] = None,
) -> Evidence:
    """Build Evidence from the cross-check fixtures that name this rule."""
    root = fixtures or default_fixture_dir()

    def mine(doc: dict) -> bool:
        return doc.get("rule_id") == rule.id

    jhora = [
        d
        for d in _fixture_files(root / "jhora")
        if mine(d)
        and d.get("source") == "jhora_manual"
        and str(d.get("reader") or "").strip()
        and d.get("agrees") is not False
    ]
    hz = [d for d in _fixture_files(root / "horizons") if mine(d)]
    return Evidence(
        cases_pass=cases_pass,
        n_cases=len(rule.reference_cases),
        jhora_cases=len(jhora),
        horizons_ok=bool(hz) and all(d.get("agrees") is True for d in hz),
    )


def evidence_for(rule: Rule, fixtures: Optional[Path] = None) -> Evidence:
    """Run the reference cases and read the fixtures (heavy: uses the engine)."""
    from .engine import run_reference_cases

    ok = rule.status == "active" and all(r.passed for r in run_reference_cases(rule))
    return fixture_evidence(rule, ok, fixtures)


__all__ = [
    "Evidence",
    "FAMILY_MIN_LEVEL",
    "LEVEL_NAMES",
    "LevelReport",
    "evidence_for",
    "fixture_evidence",
    "level",
]
