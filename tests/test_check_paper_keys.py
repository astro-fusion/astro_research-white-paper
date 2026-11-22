"""Tests for the results-key gate (ADR-004 WP-16)."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_paper_keys", ROOT / "tools" / "check_paper_keys.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

DATA_SHA = "ab" * 32
PLAN = ("study: demo\nversion: 2\nsnapshots:\n  - id: main\n    file: x.csv\n    sha256: %s\n" % DATA_SHA).encode()


def make_results(**over):
    d = {
        "provisional": False,
        "git": {"commit": "c0ffee", "dirty": False},
        "plan": {"sha256": hashlib.sha256(PLAN).hexdigest()},
        "data": {"sha256": DATA_SHA},
        "headline": {"n": 42, "verdict": "null"},
    }
    d.update(over)
    return d


@pytest.fixture
def paper_dir(tmp_path):
    (tmp_path / "paper").mkdir()
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "hypothesis.yaml").write_bytes(PLAN)
    (tmp_path / "index.json").write_text(json.dumps({"snapshots": [{"sha256": DATA_SHA}]}))
    return tmp_path


def run(paper_dir, body, results=None, extra=()):
    (paper_dir / "artifacts" / "results.json").write_text(json.dumps(results or make_results()))
    paper = paper_dir / "paper" / "p.qmd"
    paper.write_text(body)
    return gate.main(
        [str(paper), "--snapshot-index", str(paper_dir / "index.json"), *extra]
    )


GOOD = (
    "---\ntitle: T 2026\n---\n\n# Results\n\n"
    "We ran " + "`{python} R.count('headline.n')`" + " tests (see [@smith2020]).\n"
)


def test_good_paper_passes(paper_dir, capsys):
    assert run(paper_dir, GOOD) == 0


def test_missing_key_fails(paper_dir, capsys):
    body = GOOD + "\nAlso " + "`{python} R.num('headline.absent')`" + ".\n"
    assert run(paper_dir, body) == 1
    assert "KEY" in capsys.readouterr().err


def test_bare_number_fails_and_allowlist_passes(paper_dir, capsys):
    body = GOOD + "\nThe effect was 3.7 percent in 2019.\n"
    assert run(paper_dir, body) == 1
    err = capsys.readouterr().err
    assert "'3.7'" in err and "'2019'" in err
    (paper_dir / "paper" / "numbers_allowlist.txt").write_text("# years\n2019\n3.7\n")
    assert run(paper_dir, body) == 0


def test_numbers_in_code_urls_and_ids_ignored(paper_dir):
    body = GOOD + (
        "\n" + "```" + "{python}\nx = 12345\n" + "```" + "\n"
        "See https://example.org/a/99 and WP-16, D1, L3 and [link 55](http://x.y/77).\n"
    )
    assert run(paper_dir, body) == 0


def test_provisional_fails(paper_dir, capsys):
    assert run(paper_dir, GOOD, make_results(provisional=True)) == 1
    assert "DIRTY" in capsys.readouterr().err


def test_dirty_tree_fails(paper_dir, capsys):
    assert run(paper_dir, GOOD, make_results(git={"commit": "c0ffee", "dirty": True})) == 1
    assert "DIRTY" in capsys.readouterr().err


def test_plan_hash_mismatch_fails(paper_dir, capsys):
    assert run(paper_dir, GOOD, make_results(plan={"sha256": "00"})) == 1
    assert "STALE" in capsys.readouterr().err


def test_missing_plan_hash_fails(paper_dir, capsys):
    r = make_results()
    del r["plan"]
    assert run(paper_dir, GOOD, r) == 1
    assert "no plan hash" in capsys.readouterr().err


def test_data_hash_not_in_index_fails(paper_dir, capsys):
    assert run(paper_dir, GOOD, make_results(data={"sha256": "ff" * 32})) == 1
    assert "STALE" in capsys.readouterr().err


def test_no_provenance_skips_checks_three_and_four(paper_dir):
    assert run(paper_dir, GOOD, make_results(provisional=True), extra=["--no-provenance"]) == 0


def test_labelled_results(paper_dir, capsys):
    other = paper_dir / "other.json"
    other.write_text(json.dumps(make_results(headline={"n": 7})))
    (paper_dir / "artifacts" / "results.json").write_text(json.dumps(make_results()))
    paper = paper_dir / "paper" / "p.qmd"
    paper.write_text("`{python} R.get('a:headline.n')`" + " and " + "`{python} R.get('b:headline.n')`" + "\n")
    args = [str(paper), "--results", f"a={paper_dir / 'artifacts' / 'results.json'}",
            "--results", f"b={other}", "--snapshot-index", str(paper_dir / "index.json"),
            "--plan", str(paper_dir / "hypothesis.yaml")]
    assert gate.main(args) == 0
    paper.write_text("`{python} R.get('headline.n')`" + "\n")
    assert gate.main(args) == 1
    assert "label" in capsys.readouterr().err


def test_template_passes_key_syntax():
    """The shipped template parses, uses the kit and has the IMRaD headings."""
    text = (ROOT / "templates" / "imrad_paper.qmd").read_text()
    for h in ("# Abstract", "# Introduction", "# Methods", "# Results", "# Discussion", "# Conclusion"):
        assert h in text
    assert "paperkit" in text
    assert gate.check_numbers(text, set()) == []


def test_fixture_paper_missing_key_exits_nonzero_via_cli(paper_dir):
    import subprocess, sys

    (paper_dir / "artifacts" / "results.json").write_text(json.dumps(make_results()))
    paper = paper_dir / "paper" / "p.qmd"
    paper.write_text("`{python} R.get('nope.key')`" + "\n")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_paper_keys.py"), str(paper), "--no-provenance"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1 and "KEY" in proc.stderr


@pytest.mark.parametrize("text, token", [
    ("The effect was -0.42 in the sample.", "-0.42"),
    ("It was significant at p = .03 only.", ".03"),
    ("Gold cost $5 more.", "$5"),
    ("A price of $1,850 was reached.", "$1,850"),
    ("A drop of −1.5 percent.", "−1.5"),
])
def test_signed_dot_and_currency_numbers_are_bare(text, token):
    """M5: negative, leading-dot and currency numbers are caught."""
    fails = gate.check_numbers(text, set())
    assert any(repr(token) in f for f in fails), fails
    assert gate.check_numbers(text, {token}) == []


def test_hyphen_and_dot_glued_to_words_are_not_signs():
    text = "See ADR-004, WP-16, S-05, v1.2 and the 2020-05-01 snapshot."
    assert [f.split("'")[1] for f in gate.check_numbers(text, set())] == ["2020"]


def test_dataset_sha256_is_accepted(paper_dir):
    """The ADR-007 domain record spells the data hash dataset.sha256."""
    r = make_results()
    del r["data"]
    r["dataset"] = {"id": "x", "grade": "A", "sha256": DATA_SHA}
    assert run(paper_dir, GOOD, r) == 0


def test_two_spellings_must_agree(paper_dir, capsys):
    r = make_results(dataset={"sha256": "ff" * 32})
    assert run(paper_dir, GOOD, r) == 1
    assert "disagree" in capsys.readouterr().err
    r = make_results(plan_sha256="00" * 32)
    assert run(paper_dir, GOOD, r) == 1


def test_commit_only_inside_another_block_is_not_provenance(paper_dir, capsys):
    """The gate reads the top-level git block only (one contract)."""
    r = make_results()
    del r["git"]
    r["slice"] = {"commit": "c0ffee", "tree_dirty": False}
    assert run(paper_dir, GOOD, r) == 1
    assert "DIRTY" in capsys.readouterr().err


def test_indexed_but_unpinned_data_hash_fails(paper_dir, capsys):
    """D-08: a hash that is in the index but not pinned by the plan is stale."""
    other = "cd" * 32
    (paper_dir / "index.json").write_text(
        json.dumps({"snapshots": [{"sha256": DATA_SHA}, {"sha256": other}]})
    )
    assert run(paper_dir, GOOD, make_results(data={"sha256": other})) == 1
    assert "not one" in capsys.readouterr().err


def test_plan_without_pins_fails(paper_dir, capsys):
    bare = b"study: demo\nversion: 2\n"
    (paper_dir / "hypothesis.yaml").write_bytes(bare)
    res = make_results(plan={"sha256": hashlib.sha256(bare).hexdigest()})
    assert run(paper_dir, GOOD, res) == 1
    assert "pins no snapshot hash" in capsys.readouterr().err
