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
L4     faithful: a review by a second git identity, committed before the
       batch close, or carrying an outside reference (ADR-008 G-09, A-10)
L5     explored: a logged fit
L6     confirmed or refuted: a confirm stamp for the current version
=====  ==================================================================

"Validated principle" means L4 and faithful encoding only. A rule may enter a
confirmatory family at L2 or above (:data:`FAMILY_MIN_LEVEL`, owner decision
"L2"); words below L4 say "encoding" (ADR-008 7.1).

Cross-check fixtures (ADR-004 WP-21) are JSON files carrying ``rule_id``,
``source`` (``jhora_manual`` counts; ``pyjhora`` does not), a non-empty
``reader``, the two numbers ``computed_deg`` and ``reference_deg``, and
``agrees: true``. The code checks the numbers against the tolerance
(:data:`JHORA_TOL_ARCMIN`, :data:`HORIZONS_TOL_ARCSEC`); a file may state a
tighter ``tolerance_arcmin`` or ``tolerance_arcsec`` but never a looser one.
A file without ``agrees: true``, without numbers, or out of tolerance is not
counted; an out-of-tolerance or non-agreeing Horizons file fails the check.

L4 is a :class:`ReviewProof`, not a typed flag. The reviewer's git identity
must differ from the author's, and the review commit must predate the batch
close, or the review must carry an outside reference. A later review is shown
with its date and does not give L4 (A-10).
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
FAMILY_MIN_LEVEL = 2
MIN_JHORA_CASES = 3
JHORA_TOL_ARCMIN = 1.0
HORIZONS_TOL_ARCSEC = 5.0


@dataclass(frozen=True)
class ReviewProof:
    """Git-derived proof of one review (G-09, A-10).

    ``reviewer_identity`` and ``author_identity`` are git identities (e-mail).
    ``committed_at`` is the review commit's date (timezone-aware).
    ``outside_reference`` is a citation of a reviewer outside the project.
    ``by`` is the review entry's handle, used to match it to the rule.
    """

    by: str
    reviewer_identity: str
    author_identity: str
    committed_at: Optional[datetime] = None
    outside_reference: str = ""


@dataclass(frozen=True)
class Evidence:
    """Evidence that cannot be read from the rule file alone (L3).

    ``None`` means "not checked", which does not satisfy the level.
    """

    cases_pass: Optional[bool] = None
    n_cases: int = 0
    jhora_cases: int = 0
    horizons_ok: Optional[bool] = None
    review_proofs: Tuple[ReviewProof, ...] = ()
    batch_close: Optional[datetime] = None


@dataclass
class LevelReport:
    """The computed level and what each level still lacks."""

    rule_id: str
    level: int
    missing: Dict[int, List[str]] = field(default_factory=dict)
    attestation: Optional[str] = None

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
        if self.attestation:
            lines.append(self.attestation)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-friendly form."""
        return {
            "rule": self.rule_id,
            "level": self.level,
            "name": self.name,
            "missing": {f"L{k}": v for k, v in sorted(self.missing.items())},
            "attestation": self.attestation,
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


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _l4_review(rule: Rule, ev: Evidence) -> Tuple[List[str], Optional[str]]:
    """Missing items for L4 and the attestation line (A-10)."""
    need = [
        "a review with verdict faithful for this version, by a named reviewer on a "
        "second git identity whose commit predates the batch close, or that carries "
        "an outside reference"
    ]
    late: List[str] = []
    for entry in rule.review:
        if entry.verdict != "faithful":
            continue
        if entry.version not in (None, rule.version):
            continue
        if _norm(entry.by) == _norm(rule.author):
            continue
        for proof in ev.review_proofs:
            if _norm(proof.by) != _norm(entry.by):
                continue
            if _norm(proof.reviewer_identity) == _norm(proof.author_identity):
                continue
            if proof.outside_reference.strip():
                return [], f"attested faithful by {entry.by} with an outside reference"
            if proof.committed_at is None:
                continue
            when = _aware(proof.committed_at)
            if ev.batch_close is not None and when < _aware(ev.batch_close):
                return [], f"attested before the result: {entry.by}, {when.date()}"
            late.append(f"{entry.by}, {when.date()}")
    if late:
        return need, "reviewed after the batch close (not attested before the result): " + "; ".join(late)
    return need, None


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
    l4, attestation = _l4_review(rule, evidence or Evidence())
    checks = {
        1: _l1(rule),
        2: _l2(rule),
        3: _l3(rule, evidence),
        4: l4,
        5: _l5(rule),
        6: _l6(rule),
    }
    reached = 0
    for n in range(1, 7):
        if checks[n]:
            break
        reached = n
    missing = {n: m for n, m in checks.items() if m}
    return LevelReport(rule.id, reached, missing, attestation if reached >= 4 or 4 in missing else None)


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
        and _fixture_agrees(d, JHORA_TOL_ARCMIN * 60.0, "tolerance_arcmin", 60.0)
    ]
    hz = [d for d in _fixture_files(root / "horizons") if mine(d)]
    return Evidence(
        cases_pass=cases_pass,
        n_cases=len(rule.reference_cases),
        jhora_cases=len(jhora),
        horizons_ok=bool(hz)
        and all(_fixture_agrees(d, HORIZONS_TOL_ARCSEC, "tolerance_arcsec", 1.0) for d in hz),
    )


def _fixture_agrees(doc: dict, limit_arcsec: float, tol_key: str, unit: float) -> bool:
    """True when ``agrees`` is true and the stated numbers are within tolerance."""
    if doc.get("agrees") is not True:
        return False
    try:
        computed = float(doc["computed_deg"])
        reference = float(doc["reference_deg"])
    except (KeyError, TypeError, ValueError):
        return False
    if computed != computed or reference != reference:
        return False
    limit = limit_arcsec
    if doc.get(tol_key) is not None:
        try:
            stated = float(doc[tol_key]) * unit
        except (TypeError, ValueError):
            return False
        if stated > limit:
            return False
        limit = stated
    diff = abs((computed - reference + 180.0) % 360.0 - 180.0) * 3600.0
    return diff <= limit


def review_proof_from_commit(
    sha: str,
    by: str,
    author_identity: str,
    repo: Optional[Path] = None,
    outside_reference: str = "",
) -> ReviewProof:
    """Read a review commit's author e-mail and committer date from git."""
    out = subprocess.run(
        ["git", "show", "-s", "--format=%ae%n%cI", sha],
        cwd=str(repo or default_fixture_dir().parent.parent),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return ReviewProof(
        by=by,
        reviewer_identity=out[0],
        author_identity=author_identity,
        committed_at=datetime.fromisoformat(out[1]),
        outside_reference=outside_reference,
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
    "HORIZONS_TOL_ARCSEC",
    "JHORA_TOL_ARCMIN",
    "LevelReport",
    "ReviewProof",
    "evidence_for",
    "fixture_evidence",
    "level",
    "review_proof_from_commit",
]
