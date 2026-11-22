"""Tests for scripts/project_multiplicity.py (ADR-004 WP-08)."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "project_multiplicity", ROOT / "scripts" / "project_multiplicity.py"
)
pm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pm)


def _write(root: Path, study: str, data: dict) -> None:
    """Write one fake study results file under root."""
    path = root / "studies" / study / "artifacts" / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.fixture()
def tree(tmp_path):
    """Three fake studies covering effect, declared and equivalence records."""
    _write(
        tmp_path,
        "alpha",
        {
            "study": "alpha",
            "provisional": False,
            "git": {"commit": "x", "dirty": True},
            "tests": [
                {"id": 1, "p_value": 0.01, "q_value": 0.03, "significant": True},
                {"id": 2, "p_value": 0.20, "p_poisson": 0.001, "q_value": 0.4},
                {"id": 3, "p_value": 0.9, "q_value": 0.9},
            ],
            "stationarity": [{"adf_p": 0.5, "p_value": 0.001}],
            "controls": {"positive": {"best": {"p_value": 0.0001}}},
            "spa": {"p_consistent": 0.5, "p_lower": 0.4, "p_upper": 0.6},
        },
    )
    _write(
        tmp_path,
        "beta",
        {
            "study": "not-beta",
            "provisional": True,
            "counts": {
                "candidates": 500,
                "testable": 100,
                "explore_nominal_p_lt_alpha": 7,
            },
            "best": {"p_value": 0.004, "q_value": 1.0},
        },
    )
    _write(
        tmp_path,
        "gamma",
        {
            "H1": {"p_tost": 1e-6, "equivalent": True},
            "H2": [{"p_tost": 0.3}],
            "factors": [{"p_shift": None, "p_matched": None, "testable": False}],
        },
    )
    return tmp_path


def test_counts_each_test_once_and_skips_method_checks(tree):
    """A record with two p keys is one test; diagnostics and controls are not."""
    s = pm.study_summary(tree / "studies/alpha/artifacts/results.json")
    assert s["n_tested"] == 4  # three tests + SPA
    assert s["n_nominal_significant"] == 1  # p_value, not p_poisson, is the p
    assert s["n_corrected_significant"] == 1
    assert s["n_corrected_families"] == 1
    assert s["excluded_method_checks"] == {
        "controls.positive.best": 1,
        "stationarity.[]": 1,
    }
    assert s["sections"] == {"spa": 1, "tests.[]": 3}
    assert s["git_dirty"] is True
    assert s["expected_nominal_false_positives_if_all_null"] == pytest.approx(0.2)


def test_declared_counts_win_when_larger(tree):
    """A study that stores only its best candidate declares its totals."""
    s = pm.study_summary(tree / "studies/beta/artifacts/results.json")
    assert s["study"] == "beta" and s["study_label"] == "not-beta"
    assert s["n_with_stored_p"] == 1
    assert s["n_tested"] == 100
    assert s["n_examined"] == 500
    assert s["n_nominal_significant"] == 7
    assert s["provisional"] is True


def test_equivalence_tests_count_but_are_not_discoveries(tree):
    """p_tost records are tests; a small TOST p is not a nominal discovery."""
    s = pm.study_summary(tree / "studies/gamma/artifacts/results.json")
    assert s["n_tested"] == 2
    assert s["n_equivalence_tests"] == 2
    assert s["n_equivalence_shown"] == 1
    assert s["n_nominal_significant"] == 0
    assert s["n_declared_not_computed"] == 1


def test_project_summary_totals_and_by(tree):
    """Project totals add up; the project BY uses family size N."""
    out = pm.project_summary(tree)
    assert out["n_studies"] == 3
    assert out["n_hypotheses_tested"] == 4 + 100 + 2
    assert out["n_hypotheses_examined"] == 4 + 500 + 2
    assert out["n_nominal_significant"] == 1 + 7
    assert out["expected_nominal_false_positives_if_all_null"] == pytest.approx(
        0.05 * 106
    )
    assert out["expected_families_with_a_false_discovery_if_all_null"] == pytest.approx(
        0.05 * 2
    )
    h = sum(1 / i for i in range(1, 107))
    assert out["project_by"]["rank1_threshold"] == pytest.approx(0.05 / (106 * h))
    assert out["project_by"]["n_significant"] == 0
    assert out["project_by"]["n_effect_p_values"] == 5
    assert out["any_provisional"] and out["any_dirty"]
    assert [s["study"] for s in out["studies"]] == ["alpha", "beta", "gamma"]
    assert out["studies"][0]["results"] == "studies/alpha/artifacts/results.json"


def test_by_count_matches_step_up():
    """The BY count is the largest rank whose p is under its step-up line."""
    k, thr = pm._by_count([1e-6, 1e-5, 0.5], 3, 0.05)
    h = 1 + 1 / 2 + 1 / 3
    assert thr == pytest.approx(0.05 / (3 * h))
    assert k == 2


def test_main_writes_deterministic_json(tree, capsys):
    """The CLI writes studies/project_multiplicity.json, byte-identical on rerun."""
    assert pm.main(["--root", str(tree)]) == 0
    out = tree / "studies" / "project_multiplicity.json"
    first = out.read_bytes()
    assert pm.main(["--root", str(tree)]) == 0
    assert out.read_bytes() == first
    data = json.loads(first)
    assert data["schema"] == pm.SCHEMA
    assert "generated" not in json.dumps(data)
    assert "106 hypotheses" in capsys.readouterr().out


def test_bad_alpha_raises(tree):
    """Alpha outside (0, 1) is refused."""
    with pytest.raises(ValueError):
        pm.project_summary(tree, alpha=1.5)


def test_runs_on_the_committed_results():
    """Every committed study results file is read without error."""
    files = sorted((ROOT / "studies").glob("*/artifacts/results.json"))
    if not files:
        pytest.skip("no committed results")
    out = pm.project_summary(ROOT)
    assert out["n_studies"] == len(files)
    assert out["n_hypotheses_tested"] >= sum(
        1 for s in out["studies"] if s["n_tested"] > 0
    )
