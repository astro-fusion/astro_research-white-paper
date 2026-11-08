"""The astro-rules command line: validate, test, explain, list, schema."""

import json
from pathlib import Path

import pytest

from vedic_astrology_core.rules.cli import main

FIXTURES = Path(__file__).parent / "fixtures" / "rules"
VALID = str(FIXTURES / "valid")


def run(capsys, *argv):
    """Run the CLI; return (exit code, stdout, stderr)."""
    code = main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_validate_ok(capsys):
    """Valid rules: exit 0 and a count."""
    code, out, _ = run(capsys, "validate", VALID)
    assert code == 0
    assert "3 rules valid" in out


def test_validate_reports_each_problem(capsys):
    """Invalid files: exit 1, one line per problem with file and line."""
    code, out, _ = run(capsys, "validate", str(FIXTURES / "invalid"))
    assert code == 1
    assert "typos.yaml:10: conditions.all[0].conjunct_within.orb_degs" in out
    assert "unknown predicate 'house_frm'" in out
    assert "tier 'classical' needs a source with text and chapter" in out
    assert "missing_place.yaml" in out and "add a place" in out
    assert "problems in" in out


def test_validate_rejects_duplicate_ids(capsys):
    """Duplicate ids across files fail validation."""
    code, out, _ = run(capsys, "validate", str(FIXTURES / "duplicate"))
    assert code == 1
    assert "duplicate id 'test.saturn_tenth'" in out


def test_test_command_passes_valid_rules(capsys):
    """Reference cases of the valid fixtures all pass; needs_predicates skipped."""
    code, out, _ = run(capsys, "test", VALID)
    assert code == 0, out
    assert "PASS test.gaja_kesari (6 cases)" in out
    assert "SKIP test.waiting (needs_predicates)" in out
    assert "7 passed, 0 failed" in out


def test_test_command_prints_explain_tree_on_mismatch(capsys):
    """A mismatch fails, prints the tree; needs_verification is only listed."""
    code, out, _ = run(capsys, "test", str(FIXTURES / "failing"))
    assert code == 1
    assert "FAIL test.wrong_expectation case 0" in out
    assert "expected fires, got silent" in out
    assert "[FAILS] retrograde(planet=Jupiter): Jupiter moves +0.041" in out
    assert "KNOWN test.known_issue case 0 (needs_verification)" in out
    assert "1 failed, 1 known" in out


def test_test_command_known_issues_alone_exit_zero(capsys):
    """needs_verification mismatches do not fail the run."""
    code, out, _ = run(capsys, "test", str(FIXTURES / "failing" / "known_issue.yaml"))
    assert code == 0
    assert "needs_verification rules: test.known_issue" in out


def test_explain_command(capsys):
    """Explain prints the verdict and the tree."""
    code, out, _ = run(
        capsys,
        "explain",
        "test.gaja_kesari",
        "1990-05-15T10:30:00+05:45",
        "--rules-dir",
        VALID,
    )
    assert code == 0
    assert out.startswith("test.gaja_kesari FIRES")
    assert "7th from Moon in Sagittarius, which is a kendra" in out


def test_explain_with_place_and_local_time(capsys):
    """A naive moment is read in --tz; the place feeds the Lagna."""
    code, out, _ = run(
        capsys,
        "explain",
        "test.saturn_tenth",
        "2000-01-01T12:00:00",
        "--lat",
        "51.4769",
        "--lon",
        "0",
        "--tz",
        "Europe/London",
        "--rules-dir",
        VALID,
    )
    assert code == 0, out
    assert "FIRES" in out and "1st house from the Lagna in Aries" in out


def test_explain_errors_are_friendly(capsys):
    """Unknown ids, missing places and naive moments exit 2 with a hint."""
    code, _, err = run(
        capsys, "explain", "test.gaja_kesri", "2000-01-01T00:00Z", "--rules-dir", VALID
    )
    assert code == 2 and "Did you mean 'test.gaja_kesari'" in err
    code, _, err = run(
        capsys,
        "explain",
        "test.saturn_tenth",
        "2000-01-01T00:00Z",
        "--rules-dir",
        VALID,
    )
    assert code == 2 and "needs a place" in err
    code, _, err = run(
        capsys, "explain", "test.gaja_kesari", "2000-01-01T00:00", "--rules-dir", VALID
    )
    assert code == 2 and "time zone" in err


def test_list_filters(capsys):
    """List shows rules, filtered by domain and tier."""
    code, out, _ = run(capsys, "list", "--rules-dir", VALID)
    assert code == 0
    assert "test.gaja_kesari" in out and "test.waiting" in out
    code, out, _ = run(capsys, "list", "--rules-dir", VALID, "--tier", "classical")
    assert "test.gaja_kesari" in out and "test.waiting" not in out
    code, out, _ = run(capsys, "list", "--rules-dir", VALID, "--domain", "mundane")
    assert "test.waiting" in out and "test.gaja_kesari" not in out


def test_list_predicates(capsys):
    """The vocabulary with one example each."""
    code, out, _ = run(capsys, "list", "--predicates")
    assert code == 0
    assert "in_kendra_from" in out and "graha_drishti" in out
    assert '{"in_kendra_from": {"planet": "Jupiter", "from": "Moon"}}' in out


def test_schema_command_prints_json(capsys):
    """Schema prints the JSON Schema."""
    code, out, _ = run(capsys, "schema")
    assert code == 0
    assert json.loads(out)["title"] == "Astrological rule"


def test_no_command_shows_help(capsys):
    """Without a command the usage is printed and the exit code is 2."""
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
