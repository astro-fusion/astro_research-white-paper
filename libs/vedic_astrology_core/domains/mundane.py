"""National-chart adapter under the one scheme (ADR-008 G-07, WP-97; replaces ADR-007 WP-80).

There is one multiplicity scheme and one verdict vocabulary: the flat family
and the verdict function of ADR-008. The ADR-006 omnibus and hierarchical
output (core/mundane/aggregate.py) stays as a page labelled "descriptive".
Until the national-chart domain passes the gate of ADR-008 5.1 (Indian
mainshocks are about 5 expected events against a confirm floor of 30), every
test returns U with the reason "too few events". No function here maps the
ADR-006 verdict words to verdict codes: none exists, so the two
vocabularies cannot disagree.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..validity import verdict as _v
from ..validity.family import Eligibility

__all__ = ["REASON", "RECORD_SCHEMA", "untestable_record", "national_chart_records"]

RECORD_SCHEMA = "national-chart-result/1"
REASON = "too_few_events"


def untestable_record(test_id: str, level: int = 1, *, vintage_id: str = "national") -> Dict[str, Any]:
    """One test as U with the reason "too few events"; no p-value, no estimate."""
    el = Eligibility(test_id=test_id, vintage_id=vintage_id, row="descriptive",
                     allow_s=False, allow_c=False, allow_e=False, numbers="descriptive")
    v = _v.verdict(_v.VerdictInput(level=level, eligibility=el, side="two-sided",
                                   can_support=False, can_limit=False,
                                   untestable_reason=REASON))
    rec = v.to_dict()
    rec.update({"schema": RECORD_SCHEMA, "test_id": test_id, "reason": REASON})
    return rec


def national_chart_records(test_ids: Sequence[str], level: int = 1,
                           report: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """Records for the declared tests, from the ids alone.

    report (an ADR-006 aggregate report) is accepted only to check that its
    test ids are the declared ones; none of its numbers or words is read.
    """
    ids = list(test_ids)
    if report is not None:
        got = [t.get("test_id") for t in report["main"]["tests"]]
        if sorted(got) != sorted(ids):
            raise ValueError(f"report tests {sorted(got)} differ from declared {sorted(ids)}")
    return [untestable_record(t, level) for t in ids]
