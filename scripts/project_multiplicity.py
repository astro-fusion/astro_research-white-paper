#!/usr/bin/env python3
"""Count every hypothesis the project has tested (ADR-004 WP-08, review item 8).

Reads every ``studies/*/artifacts/results.json`` and writes
``studies/project_multiplicity.json``: per study and for the whole project,
the number of hypotheses tested, how many were nominally significant, how
many survived their study's own correction, and how many false discoveries
chance alone would give if no tested principle had any effect. ADR-007
section 3 prints this project-wide count on the cross-domain summary.

What counts as one hypothesis
-----------------------------
Every JSON object (anywhere in a results file) that carries a p-value key
from :data:`P_KEYS` is one test, counted once even if it reports several
p-values for the same hypothesis (``p_value`` and ``p_poisson``). An
object whose p keys are all null is a declared test that was not computed
(untestable, below an event floor) and is counted separately. A
confirmation re-test, a raw-catalogue variant or a sensitivity table counts
as its own test: the count is deliberately an upper bound. Equivalence tests
(``p_tost``) count as tests but are tallied apart (``n_equivalence_tests``,
``n_equivalence_shown``), because their small p-values are not discoveries.

Objects under :data:`EXCLUDED_SECTIONS` (stationarity diagnostics, positive
and negative method controls) test the method, not a principle, and are
reported but not counted. A study that tested more hypotheses than it
stores p-values for (the combination atlas keeps only its best candidate)
declares the totals under ``counts``; :data:`DECLARED_COUNTS` reads them and
the larger of declared and found is used.

Chance expectations (all at the plan's alpha, default 0.05)
-----------------------------------------------------------
* ``expected_nominal_false_positives_if_all_null``: ``alpha * N``. Each test
  is nominally significant with probability at most alpha when its
  principle has no effect.
* ``expected_families_with_a_false_discovery_if_all_null``: at most
  ``alpha * F`` for F corrected families; under the global null FDR control
  is family-wise control.
* ``project_by``: one Benjamini-Yekutieli correction over every stored
  effect-test p-value with the family size set to the whole project count N
  (equivalence tests and tests without a stored p-value count toward N and
  are treated as p = 1).

The output contains no timestamp, only the SHA-256 of each input, so it
changes only when a results file changes.

Usage::

    python scripts/project_multiplicity.py [--root DIR] [--out FILE] [--alpha 0.05]
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

P_KEYS = ("p_value", "p_shift", "p_matched", "p_family", "p_consistent")
"""Keys of an effect test (H0: no effect); the first finite one is its p."""

EQUIVALENCE_P_KEYS = ("p_tost", "p_equivalence")
"""Keys of an equivalence test (H0: an effect at least the margin). Such a
test counts as a hypothesis tested, but a small p shows absence of a
meaningful effect, not a discovery, so it is kept out of the nominal count
and out of the project-wide correction."""

ALL_P_KEYS = P_KEYS + EQUIVALENCE_P_KEYS

EXCLUDED_SECTIONS = ("stationarity", "controls")
"""Top-level sections that test the method, not a principle."""

DECLARED_COUNTS = {
    "n_tested": ("counts", "testable"),
    "n_nominal_significant": ("counts", "explore_nominal_p_lt_alpha"),
    "n_examined": ("counts", "candidates"),
}
"""Totals a study declares when it does not store every p-value."""

SCHEMA = "project-multiplicity/1"


def _finite_p(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        return None
    return float(value)


def _section_path(path: Tuple[str, ...]) -> str:
    return ".".join(path) if path else "(root)"


def _walk(node: Any, path: Tuple[str, ...], out: List[Tuple[Tuple[str, ...], dict]]):
    if isinstance(node, dict):
        if any(k in node for k in ALL_P_KEYS):
            out.append((path, node))
        for key, value in node.items():
            _walk(value, path + (str(key),), out)
    elif isinstance(node, list):
        for item in node:
            _walk(item, path + ("[]",), out)


def _first_p(record: dict, keys: Tuple[str, ...]) -> Optional[float]:
    for key in keys:
        p = _finite_p(record.get(key))
        if p is not None:
            return p
    return None


def _corrected_significant(record: dict, alpha: float) -> bool:
    if record.get("significant") is True or record.get("confirmed") is True:
        return True
    q = _finite_p(record.get("q_value"))
    return q is not None and q < alpha


def _declared(data: dict) -> Dict[str, int]:
    found = {}
    for name, (section, key) in DECLARED_COUNTS.items():
        block = data.get(section)
        if isinstance(block, dict):
            value = block.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                found[name] = value
    return found


def study_summary(path: Path, alpha: float = 0.05) -> Dict[str, Any]:
    """Return the hypothesis count of one results file and its stored p-values."""
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: results.json must be a JSON object")
    records: List[Tuple[Tuple[str, ...], dict]] = []
    _walk(data, (), records)

    sections: Dict[str, int] = {}
    excluded: Dict[str, int] = {}
    corrected_sections = set()
    p_values: List[float] = []
    n_not_computed = 0
    n_equivalence = 0
    n_equivalence_shown = 0
    n_nominal = 0
    n_corrected = 0
    for rec_path, record in records:
        name = _section_path(rec_path)
        if rec_path and rec_path[0] in EXCLUDED_SECTIONS:
            excluded[name] = excluded.get(name, 0) + 1
            continue
        p = _first_p(record, P_KEYS)
        if p is None:
            p_eq = _first_p(record, EQUIVALENCE_P_KEYS)
            if p_eq is None:
                n_not_computed += 1
            else:
                sections[name] = sections.get(name, 0) + 1
                n_equivalence += 1
                n_equivalence_shown += p_eq < alpha
            continue
        sections[name] = sections.get(name, 0) + 1
        p_values.append(p)
        n_nominal += p < alpha
        if "q_value" in record or "significant" in record:
            corrected_sections.add(name)
        n_corrected += _corrected_significant(record, alpha)

    declared = _declared(data)
    n_found = len(p_values) + n_equivalence
    n_tested = max(n_found, declared.get("n_tested", 0))
    n_nominal_used = max(n_nominal, declared.get("n_nominal_significant", 0))
    git = data.get("git") if isinstance(data.get("git"), dict) else {}
    return {
        "results": path.as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "study": path.parent.parent.name,
        "study_label": data.get("study"),
        "provisional": bool(data.get("provisional", False)),
        "git_dirty": git.get("dirty"),
        "n_tested": int(n_tested),
        "n_with_stored_p": int(n_found),
        "n_equivalence_tests": int(n_equivalence),
        "n_equivalence_shown": int(n_equivalence_shown),
        "n_declared_not_computed": int(n_not_computed),
        "n_examined": int(max(n_tested, declared.get("n_examined", 0))),
        "n_nominal_significant": int(n_nominal_used),
        "n_corrected_significant": int(n_corrected),
        "n_corrected_families": len(corrected_sections),
        "expected_nominal_false_positives_if_all_null": alpha * n_tested,
        "declared_counts": declared,
        "sections": dict(sorted(sections.items())),
        "excluded_method_checks": dict(sorted(excluded.items())),
        "_p_values": p_values,
    }


def _by_count(p_values: List[float], m: int, alpha: float) -> Tuple[int, float]:
    """Benjamini-Yekutieli rejections among ``p_values`` with family size m."""
    if m < 1:
        return 0, float("nan")
    h_m = sum(1.0 / i for i in range(1, m + 1))
    ranked = sorted(p_values)
    k = 0
    for i, p in enumerate(ranked, start=1):
        if p <= i * alpha / (m * h_m):
            k = i
    return k, alpha / (m * h_m)


def project_summary(root: Path, alpha: float = 0.05) -> Dict[str, Any]:
    """Return the project-wide summary over every study results file."""
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    files = sorted((root / "studies").glob("*/artifacts/results.json"))
    studies = []
    all_p: List[float] = []
    for f in files:
        s = study_summary(f, alpha)
        s["results"] = f.relative_to(root).as_posix()
        all_p.extend(s.pop("_p_values"))
        studies.append(s)
    n_total = sum(s["n_tested"] for s in studies)
    n_families = sum(s["n_corrected_families"] for s in studies)
    n_by, threshold = _by_count(all_p, n_total, alpha)
    return {
        "schema": SCHEMA,
        "alpha": alpha,
        "n_studies": len(studies),
        "n_hypotheses_tested": int(n_total),
        "n_hypotheses_examined": int(sum(s["n_examined"] for s in studies)),
        "n_with_stored_p": int(sum(s["n_with_stored_p"] for s in studies)),
        "n_equivalence_tests": int(sum(s["n_equivalence_tests"] for s in studies)),
        "n_equivalence_shown": int(sum(s["n_equivalence_shown"] for s in studies)),
        "n_declared_not_computed": int(
            sum(s["n_declared_not_computed"] for s in studies)
        ),
        "n_nominal_significant": int(sum(s["n_nominal_significant"] for s in studies)),
        "n_corrected_significant": int(
            sum(s["n_corrected_significant"] for s in studies)
        ),
        "n_corrected_families": int(n_families),
        "expected_nominal_false_positives_if_all_null": alpha * n_total,
        "expected_families_with_a_false_discovery_if_all_null": alpha * n_families,
        "project_by": {
            "family_size": int(n_total),
            "rank1_threshold": threshold,
            "n_significant": int(n_by),
            "n_effect_p_values": len(all_p),
            "missing_p_treated_as": 1.0,
        },
        "any_provisional": any(s["provisional"] for s in studies),
        "any_dirty": any(s["git_dirty"] is True for s in studies),
        "excluded_sections": list(EXCLUDED_SECTIONS),
        "studies": studies,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """Write the project-wide multiplicity summary."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    out = args.out or root / "studies" / "project_multiplicity.json"
    summary = project_summary(root, args.alpha)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        f"{summary['n_hypotheses_tested']} hypotheses in {summary['n_studies']} "
        f"studies; {summary['n_nominal_significant']} nominal, "
        f"{summary['expected_nominal_false_positives_if_all_null']:.1f} expected by "
        f"chance; {summary['project_by']['n_significant']} survive project-wide BY "
        f"-> {out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
