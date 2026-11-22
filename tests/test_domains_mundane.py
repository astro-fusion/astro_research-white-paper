"""ADR-008 WP-97 (G-07): national charts return U, one vocabulary, no mapping."""

import inspect

from vedic_astrology_core.domains import mundane as M
from vedic_astrology_core.mundane import aggregate as agg
from vedic_astrology_core.validity import sentences as S


def test_every_test_is_u_too_few_events():
    recs = M.national_chart_records(["t1", "t2", "t3"])
    assert [r["code"] for r in recs] == ["U"] * 3
    reason = S.UNTESTABLE_REASONS["too_few_events"]
    for r in recs:
        assert r["reason"] == "too_few_events"
        assert any(reason in line for line in r["lines"])
        assert all(S.is_allowed(line) for line in r["lines"])


def test_no_mapping_function_exists():
    names = [n for n, _ in inspect.getmembers(M, inspect.isroutine)]
    assert not [n for n in names if "map" in n.lower()]
    src = inspect.getsource(M)
    for word in agg.VERDICTS:
        assert f'"{word}"' not in src


def test_report_ids_checked_but_not_read():
    rep = {"main": {"tests": [{"test_id": "a", "verdict": "effect found"}]}}
    assert M.national_chart_records(["a"], report=rep)[0]["code"] == "U"
    try:
        M.national_chart_records(["b"], report=rep)
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched ids accepted")


def test_aggregate_headline_labelled_descriptive():
    assert agg.DESCRIPTIVE_LABEL.startswith("descriptive")
    rep = {"plan_id": "p", "period": "explore", "label": None, "n_events_total": 3,
           "descriptive_only": True, "main": {"families": []}}
    assert agg.DESCRIPTIVE_LABEL in agg.summary_lines(rep)
