"""WP-67: adapter protocol and dataset grades."""

from datetime import date

import pytest

from vedic_astrology_core.domains.base import (
    DatasetGradeError,
    DatasetSpec,
    DomainAdapter,
    GateHashError,
    GateRecord,
    Periods,
    compute_grade,
    verdicts_allowed,
    write_gate,
)
from vedic_astrology_core.domains.base import (
    deposit_problems,
    festival_spotcheck_problems,
    load_grade_register,
)
from vedic_astrology_core.domains.simulated import (
    SimulatedDomain,
    simulated_grades,
    simulated_registers,
)



def test_protocol_methods_exist_and_abstract():
    with pytest.raises(TypeError):
        DomainAdapter({}, {})
    for name in ("dataset", "grid", "calendar_context", "outcomes", "controls", "periods"):
        assert callable(getattr(SimulatedDomain(), name))


@pytest.fixture
def GATE(tmp_path):
    return write_gate(tmp_path / "gate.json", {"principles": ["x"], "passed": True})


def test_outcomes_need_gate_hash(GATE):
    d = SimulatedDomain()
    for bad in (None, "", "abc", "Z" * 64):
        with pytest.raises(GateHashError):
            d.outcomes(bad)
        with pytest.raises(GateHashError):
            d.controls(bad)
    assert d.outcome_reads == 0
    assert len(d.outcomes(GATE)["value"]) == d.n_years
    assert d.outcome_reads == 1


def test_gate_hash_alone_or_forged_is_refused(tmp_path, GATE):
    """m9: the hash is checked against the written gate file, not its format."""
    d = SimulatedDomain()
    with pytest.raises(GateHashError, match="alone"):
        d.outcomes("0" * 64)
    with pytest.raises(GateHashError, match="alone"):
        d.outcomes(GATE.sha256)  # right hash, but no file named
    with pytest.raises(GateHashError, match="does not match"):
        d.outcomes("0" * 64, gate_path=GATE.path)
    with pytest.raises(GateHashError, match="cannot be read"):
        d.outcomes(GateRecord(tmp_path / "missing.json", GATE.sha256))
    assert d.outcome_reads == 0
    assert d.outcomes(GATE.sha256, gate_path=GATE.path) is not None
    GATE.path.write_text('{"passed": false}\n')  # gate edited after the hash was taken
    with pytest.raises(GateHashError, match="does not match"):
        d.outcomes(GATE)
    arr = tmp_path / "list.json"
    import hashlib

    arr.write_text("[1]")
    with pytest.raises(GateHashError, match="JSON object"):
        d.controls(hashlib.sha256(b"[1]").hexdigest(), gate_path=arr)


def test_outcome_free_entry_points_do_not_read_outcomes():
    d = SimulatedDomain()
    d.grid(), d.calendar_context(), d.periods(), d.dataset()
    assert d.outcome_reads == 0


def test_grade_a_and_record():
    ds = SimulatedDomain().dataset()
    assert ds.grade == "A" and ds.limitations == ()
    rec = ds.as_record()
    assert rec["grade"] == "A" and rec["sha256"] == ds.sha256
    assert verdicts_allowed("A")


def test_grade_b_cases():
    sha = SimulatedDomain().sha256
    d = SimulatedDomain(grades=simulated_grades(sha, open_items=["unit conversion open"]))
    assert d.dataset().grade == "B"
    assert d.dataset().limitations == ("unit conversion open",)
    assert SimulatedDomain(grades=simulated_grades(sha, reproduced=False)).dataset().grade == "B"
    base = SimulatedDomain()
    idx, lic = simulated_registers(base.sha256, verified=False, date_read=None)
    unread = SimulatedDomain(index=idx, licences=lic)
    assert unread.dataset().grade == "B"
    assert "licence not yet read" in unread.dataset().limitations
    assert verdicts_allowed("B")


def test_grade_c_cases_block_verdicts():
    flawed = SimulatedDomain(
        grades=simulated_grades(SimulatedDomain().sha256, quality_flaws=["median volume 53 contracts"])
    )
    assert flawed.dataset().grade == "C"
    with pytest.raises(DatasetGradeError):
        flawed.require_verdict_grade()
    assert not verdicts_allowed("C")
    base = SimulatedDomain()
    spec = base.dataset_spec()
    assert compute_grade(spec, {"snapshots": []}, {})[0] == "C"
    idx, _ = simulated_registers(base.sha256)
    assert compute_grade(spec, idx, {})[0] == "C"
    assert compute_grade(DatasetSpec("x", "nothex", "simulated", ("a", "b"), 1), idx, {})[0] == "C"
    other = DatasetSpec("x", base.sha256, "other", ("a", "b"), 1)
    assert compute_grade(other, idx, {"other": {}})[0] == "C"
    assert base.require_verdict_grade().grade == "A"


def test_grade_cannot_be_set_by_hand():
    assert "grade" not in DatasetSpec.__dataclass_fields__
    with pytest.raises(TypeError):
        DatasetSpec("x", "y", "z", ("a", "b"), 1, grade="A")


def test_unknown_grade_rejected():
    with pytest.raises(ValueError):
        verdicts_allowed("D")


def test_periods_validation():
    p = SimulatedDomain().periods()
    assert p.explore[1] < p.confirm[0]
    with pytest.raises(ValueError):
        Periods((date(2000, 1, 1), date(2010, 1, 1)), (date(2010, 1, 1), date(2020, 1, 1)))
    with pytest.raises(ValueError):
        Periods((date(2010, 1, 1), date(2000, 1, 1)), (date(2011, 1, 1), date(2020, 1, 1)))


def test_simulated_is_deterministic():
    a, b = SimulatedDomain(seed=3), SimulatedDomain(seed=3)
    assert a.sha256 == b.sha256
    assert a.sha256 != SimulatedDomain(seed=4).sha256


def test_old_grade_arguments_raise_type_error():
    """D-05: reproduced, open_items and quality_flaws are not constructor arguments."""
    for kw in ({"reproduced": True}, {"open_items": ["x"]}, {"quality_flaws": ["y"]}):
        with pytest.raises(TypeError):
            SimulatedDomain(**kw)
    with pytest.raises(TypeError):
        DatasetSpec("x", "y", "z", ("a", "b"), 1, reproduced=True)


def test_register_row_without_checker_or_date_is_grade_c():
    sha = SimulatedDomain().sha256
    for kw in ({"checked_by": None}, {"checked_by": "  "}, {"date": None}):
        d = SimulatedDomain(grades=simulated_grades(sha, **kw))
        assert d.dataset().grade == "C"
        assert "no named checker or date" in d.dataset().limitations[0]


def test_no_register_row_is_at_best_grade_b():
    d = SimulatedDomain(grades=[])
    assert d.dataset().grade == "B"
    assert "not yet reproduced independently" in d.dataset().limitations


def test_source_row_adds_open_items_but_cannot_set_reproduced():
    base = SimulatedDomain()
    rows = [{"source_id": "simulated", "reproduced": True, "open_items": ["source-wide gap"],
             "checked_by": "t", "date": "2026-11-22"}]
    lim = SimulatedDomain(grades=rows).dataset().limitations
    assert "source-wide gap" in lim and "not yet reproduced independently" in lim
    assert base.dataset().grade == "A"


def test_committed_register_rows_are_complete():
    rows = load_grade_register()
    assert rows
    for r in rows:
        assert r["checked_by"] and r["date"]


def test_register_row_needs_exactly_one_key(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("rows:\n  - reproduced: true\n")
    with pytest.raises(ValueError):
        load_grade_register(p)


def test_deposit_problems():
    idx = {"snapshots": [
        {"file": "a", "sha256": "a" * 64, "deposit_doi": "10.5281/zenodo.1"},
        {"file": "b", "sha256": "b" * 64, "owner_archive": True, "owner_archive_reason": "licence forbids"},
        {"file": "c", "sha256": "c" * 64, "owner_archive": True},
        {"file": "d", "sha256": "d" * 64, "deposit_doi": None, "owner_archive": None},
    ]}
    assert deposit_problems(idx, ["a" * 64, "b" * 64]) == []
    probs = deposit_problems(idx, ["c" * 64, "d" * 64, "e" * 64])
    assert len(probs) == 3 and "not in the snapshot index" in probs[2]


def test_committed_index_has_deposit_fields():
    import json
    from pathlib import Path

    idx = json.loads((Path(__file__).resolve().parents[1] / "data" / "snapshot_index.json").read_text())
    assert all("deposit_doi" in e and "owner_archive" in e for e in idx["snapshots"])


def test_festival_spotcheck(tmp_path):
    assert any("owner task" in p for p in festival_spotcheck_problems())  # committed table is empty
    p = tmp_path / "f.yaml"
    p.write_text("rows:\n  - {festival: Diwali, year: 2012, date: '2012-11-13', reference: Almanac X p1}\n"
                 "  - {festival: Holi, year: 2013}\n")
    probs = festival_spotcheck_problems(p, leap_years=[2012, 2015])
    assert any("rows[1]: missing" in x for x in probs)
    assert any("2015" in x for x in probs) and not any("2012 has" in x for x in probs)
    assert festival_spotcheck_problems(tmp_path / "none.yaml")
