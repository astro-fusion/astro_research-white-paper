"""Changelog of the validity record (ADR-007 section 9, WP-74). Synthetic records only."""

from __future__ import annotations

import json

import pytest

from vedic_astrology_core.validity import changelog as C


def rec(tid, code="N", effect=0.1, x95=1.0, domain="d", rule="r.a", version=1, n_b=2, a_test=0.01, slot=1):
    return {
        "test_id": tid, "domain": domain, "principle": {"id": rule, "version": version},
        "verdict": {"code": code}, "effect": {"full": {"estimate": effect}}, "bound": {"x95": {"value": x95}},
        "threshold": {"n_b": n_b, "alpha_b": 0.05, "lock_position": {"register": slot}},
        "a_test_used": a_test, "input_sha256": "ab" * 32,
    }


def state(version=1, orient=15, data="d1", plan="p1", engine="e1", budget=None):
    return C.input_state(
        rules={"r.a": C.rule_state(version, {"id": "r.a", "params": {"orb": {"value": orient}}})},
        datasets={"d": data}, plans={"d": plan}, engine=engine, budget=budget or {"d": {"1": {"n_b": 2}}})


def entry(old, new, so, sn, **kw):
    return C.build_entry("2026-12-03-aaaaaaaaaaaa", "2026-11-29-bbbbbbbbbbbb", old, new, so, sn, **kw)


def lines(e):
    return {(t["test_id"], t["change"]): t for t in e["tests"]}


def test_new_principle():
    e = entry([], [rec("r.a@v1/primary/o", slot=3)], None, state())
    t = e["tests"][0]
    assert (t["change"], t["cause"], t["slot"]) == ("added", "new_principle", 3)
    assert t["verdict"] == {"from": None, "to": "N"}
    assert e["summary"]["slots_used"] == {"d": [3]} and e["summary"]["verdict_changes"] == 0


def test_changed_parameter_supersedes_old_version_and_lists_the_field():
    old = [rec("r.a@v1/primary/o", "N")]
    new = [rec("r.a@v2/primary/o", "N", version=2, slot=4)]
    e = entry(old, new, state(1, 15), state(2, 8))
    r = e["inputs_changed"]["rules"][0]
    assert (r["id"], r["from_version"], r["to_version"]) == ("r.a", 1, 2)
    assert r["fields"] == [{"path": "params.orb.value", "from": 15, "to": 8}]
    ls = lines(e)
    assert ls[("r.a@v2/primary/o", "added")]["cause"] == "rule_changed"
    assert ls[("r.a@v1/primary/o", "superseded")]["cause"] == "rule_changed"
    assert ls[("r.a@v1/primary/o", "superseded")]["verdict"] == {"from": "N", "to": "N"}


def test_new_data_snapshot_recomputes_with_data_cause():
    old = [rec("t", "N", effect=0.1)]
    new = [rec("t", "S", effect=0.9)]
    e = entry(old, new, state(data="d1"), state(data="d2"))
    t = e["tests"][0]
    assert (t["change"], t["cause"]) == ("recomputed", "data_changed")
    assert t["verdict"] == {"from": "N", "to": "S"} and e["summary"]["verdict_changes"] == 1
    assert e["inputs_changed"]["datasets"] == [{"domain": "d", "from": "d1", "to": "d2"}]


def test_raised_budget_recomputes_with_budget_cause():
    old = [rec("t", "S", a_test=0.01, n_b=2)]
    new = [rec("t", "N", a_test=0.004, n_b=5)]
    e = entry(old, new, state(budget={"d": {"1": {"n_b": 2}}}), state(budget={"d": {"1": {"n_b": 5}}}))
    t = e["tests"][0]
    assert t["cause"] == "budget_changed" and t["verdict"] == {"from": "S", "to": "N"}
    assert e["inputs_changed"]["budget"][0]["domain"] == "d"


def test_unchanged_tests_are_only_counted():
    r = rec("t")
    e = entry([r], [dict(r)], state(), state(data="d2"))
    assert e["tests"] == [] and e["summary"]["unchanged"] == 1


def test_verdict_change_with_no_input_change_fails():
    with pytest.raises(C.ChangelogError, match="verdict changed"):
        entry([rec("t", "N")], [rec("t", "S")], state(), state())


def test_numbers_change_with_no_input_change_fails():
    with pytest.raises(C.ChangelogError, match="numbers changed"):
        entry([rec("t", effect=0.1)], [rec("t", effect=0.2)], state(), state())


def test_non_strict_returns_the_unexplained_change_for_diff():
    e = entry([rec("t", "N")], [rec("t", "S")], state(), state(), strict=False)
    assert len(e["unexplained"]) == 1


def test_engine_change_is_named():
    e = entry([rec("t", effect=0.1)], [rec("t", effect=0.2)], state(engine="e1"), state(engine="e2"))
    assert e["tests"][0]["cause"] == "engine_changed" and e["inputs_changed"]["engine"] == {"from": "e1", "to": "e2"}


def test_run_id_is_date_plus_input_hash():
    a, b = C.run_id_for("2026-12-03", state()), C.run_id_for("2026-12-03", state(data="d2"))
    assert a.startswith("2026-12-03-") and len(a) == len("2026-12-03-") + 12 and a != b
    assert a == C.run_id_for("2026-12-03", state())


def test_chain_append_and_tamper(tmp_path):
    p = tmp_path / "changelog.jsonl"
    e1 = C.build_entry("r1", None, [], [rec("t")], None, state())
    C.append_entry(p, e1)
    e2 = C.build_entry("r2", "r1", [rec("t")], [rec("t")], state(), state(data="d2"))
    row = C.append_entry(p, e2)
    assert row["seq"] == 2 and len(C.read_entries(p)) == 2
    with pytest.raises(C.ChangelogError):
        C.append_entry(p, C.build_entry("r3", "r1", [], [], None, state()))  # wrong predecessor
    with pytest.raises(C.ChangelogError):
        C.append_entry(p, e2)  # already recorded
    lines_ = p.read_text().splitlines()
    first = json.loads(lines_[0])
    first["run_id"] = "edited"
    p.write_text(json.dumps(first) + "\n" + lines_[1] + "\n")
    with pytest.raises(Exception, match="chain"):
        C.read_entries(p)


def test_render_and_card_history():
    e = entry([], [rec("r.a@v1/primary/o")], None, state())
    page = C.render_qmd([e])
    assert "r.a@v1/primary/o" in page and "added" in page and page.startswith("---")
    assert C.card_history([e], "r.a")[0].startswith("2026-12-03-aaaaaaaaaaaa: added (new_principle)")
    assert C.card_history([e], "other") == []
