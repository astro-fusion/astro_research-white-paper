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
from vedic_astrology_core.domains.simulated import SimulatedDomain, simulated_registers



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
    d = SimulatedDomain(open_items=["unit conversion open"])
    assert d.dataset().grade == "B"
    assert d.dataset().limitations == ("unit conversion open",)
    assert SimulatedDomain(reproduced=False).dataset().grade == "B"
    base = SimulatedDomain()
    idx, lic = simulated_registers(base.sha256, verified=False, date_read=None)
    unread = SimulatedDomain(index=idx, licences=lic)
    assert unread.dataset().grade == "B"
    assert "licence not yet read" in unread.dataset().limitations
    assert verdicts_allowed("B")


def test_grade_c_cases_block_verdicts():
    flawed = SimulatedDomain(quality_flaws=["median volume 53 contracts"])
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
