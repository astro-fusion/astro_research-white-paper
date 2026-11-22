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

PLAN = b"study: demo\nversion: 2\n"
DATA_SHA = "ab" * 32


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
