"""Tests for the run seal (ADR-004 WP-03): clean tree, provisional, confirm ledger."""

import json
import subprocess
from datetime import datetime, timezone

import pytest

from vedic_astrology_core.stats import seal
from vedic_astrology_core.stats.manifest import build_manifest
from vedic_astrology_core.stats.seal import (
    ConfirmAlreadyRunError,
    DirtyTreeError,
    LedgerTamperedError,
    SealError,
    begin_confirm,
    confirm_window,
    require_clean_tree,
    stamp_results,
)

PLAN = """study: demo
data:
  end: "2026-10-30"
periods:
  explore_end: "2015-12-31"
  confirm_start: "2016-01-01"
"""

DATA_SHA = "a" * 64


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A temporary git repository with a committed study plan."""
    r = tmp_path / "repo"
    (r / "studies" / "demo").mkdir(parents=True)
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@example.invalid")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".gitignore").write_text("ignored/\n")
    (r / "studies" / "demo" / "hypothesis.yaml").write_text(PLAN)
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "plan")
    return r


def _commit_all(repo, msg="c"):
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)


def _confirm(repo, **kw):
    study = repo / "studies" / "demo"
    return begin_confirm(study, study / "hypothesis.yaml", DATA_SHA, repo_root=repo, **kw)


# ------------------------------------------------------------- clean tree


def test_clean_tree_passes(repo):
    s = require_clean_tree(repo)
    assert s["provisional"] is False and s["dirty"] is False
    assert s["commit"] == _git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize("kind", ["modified", "staged", "untracked"])
def test_dirty_tree_raises(repo, kind):
    plan = repo / "studies" / "demo" / "hypothesis.yaml"
    if kind == "modified":
        plan.write_text(PLAN + "# edit\n")
    elif kind == "staged":
        plan.write_text(PLAN + "# edit\n")
        _git(repo, "add", "-A")
    else:
        (repo / "new_module.py").write_text("x = 1\n")
    with pytest.raises(DirtyTreeError):
        require_clean_tree(repo)


def test_ignored_files_do_not_dirty(repo):
    (repo / "ignored").mkdir()
    (repo / "ignored" / "snap.csv").write_text("1\n")
    assert require_clean_tree(repo)["provisional"] is False


def test_provisional_run_passes_dirty_and_is_stamped(repo):
    (repo / "x.txt").write_text("x")
    s = require_clean_tree(repo, provisional=True)
    assert s["provisional"] is True and s["dirty"] is True
    res = stamp_results({"tests": []}, s)
    assert res["provisional"] is True and res["git"]["dirty"] is True


def test_outside_git_raises_unless_provisional(tmp_path):
    with pytest.raises(DirtyTreeError):
        require_clean_tree(tmp_path)
    assert require_clean_tree(tmp_path, provisional=True)["provisional"] is True


def test_provisional_must_be_bool(repo):
    with pytest.raises(TypeError):
        require_clean_tree(repo, provisional="false")


def test_no_environment_bypass(repo, monkeypatch):
    """No environment variable turns the check off."""
    (repo / "x.txt").write_text("x")
    for name in ("ASTRO_ALLOW_DIRTY", "ALLOW_DIRTY", "PROVISIONAL", "SEAL_DISABLE", "CI"):
        monkeypatch.setenv(name, "1")
    with pytest.raises(DirtyTreeError):
        require_clean_tree(repo)


def test_stamp_never_downgrades_provisional(repo):
    s = require_clean_tree(repo)
    assert stamp_results({"provisional": True}, s)["provisional"] is True
    assert stamp_results({}, s)["provisional"] is False


def test_manifest_provisional_field(repo):
    assert build_manifest(repo_root=repo)["provisional"] is False
    assert build_manifest(repo_root=repo, provisional=True)["provisional"] is True
    assert build_manifest(repo_root=repo, extra={"provisional": True})["provisional"] is True
    (repo / "x.txt").write_text("x")
    # A dirty tree never yields provisional False, even if extra says so.
    m = build_manifest(repo_root=repo, extra={"provisional": False})
    assert m["provisional"] is True
    with pytest.raises(DirtyTreeError):
        build_manifest(repo_root=repo, require_clean=True)
    m = build_manifest(repo_root=repo, require_clean=True, provisional=True)
    assert m["provisional"] is True


# ---------------------------------------------------------- confirm window


def test_confirm_window_from_plan_not_clock():
    assert confirm_window({"periods": {"confirm_start": "2016-01-01"},
                           "data": {"end": "2026-10-30"}}) == ("2016-01-01", "2026-10-30")
    assert confirm_window({"periods": {"confirm_start": "2016-01-01",
                                       "confirm_end": "2020-12-31"},
                           "data": {"end": "2026-10-30"}})[1] == "2020-12-31"


@pytest.mark.parametrize(
    "plan",
    [
        {"periods": {"confirm_start": "2016-01-01"}},  # no end: never "now"
        {"periods": {}, "data": {"end": "2026-10-30"}},
        {"periods": {"confirm_start": "2016-01-01", "confirm_end": "2015-01-01"}},
        {"periods": {"confirm_start": "2016-01-01", "confirm_end": "soon"}},
    ],
)
def test_confirm_window_rejects_bad_plans(plan):
    with pytest.raises(SealError):
        confirm_window(plan)


# ------------------------------------------------------------------ ledger


def test_first_confirm_is_logged(repo):
    when = datetime(2027, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    e = _confirm(repo, now=when)
    lines = (repo / "studies" / "demo" / "confirm_ledger.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0]) == e
    assert e["plan_sha256"] == seal.plan_sha256(repo / "studies" / "demo" / "hypothesis.yaml")
    assert e["data_sha256"] == DATA_SHA
    assert e["commit"] == _git(repo, "rev-parse", "HEAD")
    assert e["utc"] == "2027-01-02T03:04:05+00:00"
    assert e["period"] == {"start": "2016-01-01", "end": "2026-10-30"}
    assert e["plan_path"] == "studies/demo/hypothesis.yaml"


def test_second_confirm_raises(repo):
    _confirm(repo)
    _commit_all(repo, "ledger")
    with pytest.raises(ConfirmAlreadyRunError):
        _confirm(repo)


def test_uncommitted_ledger_blocks_second_confirm(repo):
    """Before the ledger is committed the tree is dirty, so nothing runs."""
    _confirm(repo)
    with pytest.raises(DirtyTreeError):
        _confirm(repo)


def test_version_bump_does_not_open_new_confirm(repo):
    _confirm(repo)
    _commit_all(repo, "ledger")
    plan = repo / "studies" / "demo" / "hypothesis.yaml"
    plan.write_text(PLAN.replace("study: demo", "study: demo_v2\nversion: 2")
                    .replace("2026-10-30", "2027-10-30"))
    _commit_all(repo, "plan v2")
    with pytest.raises(ConfirmAlreadyRunError):
        _confirm(repo)


def test_deleted_ledger_is_detected(repo):
    _confirm(repo)
    _commit_all(repo, "ledger")
    (repo / "studies" / "demo" / "confirm_ledger.jsonl").unlink()
    with pytest.raises(DirtyTreeError):  # uncommitted deletion
        _confirm(repo)
    _commit_all(repo, "delete ledger")
    with pytest.raises(LedgerTamperedError):  # committed deletion
        _confirm(repo)


def test_truncated_or_rewritten_ledger_is_detected(repo):
    _confirm(repo)
    _commit_all(repo, "ledger")
    (repo / "studies" / "demo" / "confirm_ledger.jsonl").write_text("")
    _commit_all(repo, "empty ledger")
    with pytest.raises(LedgerTamperedError):
        _confirm(repo)


def test_ledger_deleted_on_other_branch_still_counts(repo):
    """History on any ref counts: a fresh branch cannot hide the old confirm."""
    _confirm(repo)
    _commit_all(repo, "ledger")
    base = _git(repo, "rev-parse", "HEAD~1")
    _git(repo, "checkout", "-q", "-b", "fresh", base)
    with pytest.raises(LedgerTamperedError):
        _confirm(repo)


def test_confirm_requires_clean_tree_and_committed_plan(repo):
    (repo / "x.txt").write_text("x")
    with pytest.raises(DirtyTreeError):
        _confirm(repo)
    assert not (repo / "studies" / "demo" / "confirm_ledger.jsonl").exists()


def test_confirm_requires_data_hash(repo):
    study = repo / "studies" / "demo"
    with pytest.raises(SealError):
        begin_confirm(study, study / "hypothesis.yaml", "", repo_root=repo)


def test_confirm_with_no_window_end_raises_and_logs_nothing(repo):
    plan = repo / "studies" / "demo" / "hypothesis.yaml"
    plan.write_text("study: demo\nperiods:\n  confirm_start: '2016-01-01'\n")
    _commit_all(repo, "plan without end")
    with pytest.raises(SealError):
        _confirm(repo)
    assert not (repo / "studies" / "demo" / "confirm_ledger.jsonl").exists()
