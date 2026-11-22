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
    """An uncommitted entry already spends the confirm."""
    _confirm(repo)
    with pytest.raises(ConfirmAlreadyRunError):
        _confirm(repo)


def test_ledger_write_leaves_the_confirm_run_clean(repo):
    """M1: the confirm's own ledger entry does not make its run provisional."""
    _confirm(repo)
    state = seal.tree_state(repo)
    assert state["dirty"] is False and state["changes"] == []
    assert require_clean_tree(repo)["provisional"] is False
    assert build_manifest(repo_root=repo)["provisional"] is False
    stamp = stamp_results({}, require_clean_tree(repo))
    assert stamp["provisional"] is False and stamp["git"]["dirty"] is False


def test_ledger_ignore_is_narrow(repo):
    """Only an added or modified ledger is ignored; other files still dirty."""
    (repo / "studies" / "demo" / "confirm_ledger.jsonl.bak").write_text("x")
    assert seal.tree_state(repo)["dirty"] is True


def test_copied_study_folder_cannot_confirm_again(repo):
    """M4: a copy of the study without its ledger is the same lineage."""
    _confirm(repo)
    _commit_all(repo, "ledger")
    src = repo / "studies" / "demo"
    dst = repo / "studies" / "demo2"
    dst.mkdir()
    (dst / "hypothesis.yaml").write_text((src / "hypothesis.yaml").read_text())
    _commit_all(repo, "copy")
    with pytest.raises(ConfirmAlreadyRunError):
        begin_confirm(dst, dst / "hypothesis.yaml", DATA_SHA, repo_root=repo)


def test_lineage_declared_in_plan_blocks_renamed_copy(repo):
    """A renamed copy with new bytes is still blocked by its lineage field."""
    study = repo / "studies" / "demo"
    (study / "hypothesis.yaml").write_text("lineage: demo-line\n" + PLAN)
    _commit_all(repo, "lineage")
    _confirm(repo)
    _commit_all(repo, "ledger")
    copy = repo / "studies" / "renamed"
    copy.mkdir()
    (copy / "hypothesis.yaml").write_text(
        "lineage: demo-line\n" + PLAN.replace("study: demo", "study: renamed") + "# x\n")
    _commit_all(repo, "renamed copy")
    with pytest.raises(ConfirmAlreadyRunError):
        begin_confirm(copy, copy / "hypothesis.yaml", DATA_SHA, repo_root=repo)


def test_confirm_found_in_history_of_another_ledger(repo):
    """A ledger deleted with its folder still blocks the lineage via history."""
    _confirm(repo)
    _commit_all(repo, "ledger")
    old = repo / "studies" / "demo"
    new = repo / "studies" / "moved"
    _git(repo, "mv", str(old), str(new))
    (new / "confirm_ledger.jsonl").unlink()
    _commit_all(repo, "move without ledger")
    with pytest.raises(ConfirmAlreadyRunError):
        begin_confirm(new, new / "hypothesis.yaml", DATA_SHA, repo_root=repo)


def test_ledger_is_keyed_per_principle_and_lineage(repo):
    """S-05: one ledger holds many principles; each confirms once."""
    a = _confirm(repo, principle_id="rule.a")
    b = _confirm(repo, principle_id="rule.b")
    assert a["principle_id"] == "rule.a" and b["principle_id"] == "rule.b"
    with pytest.raises(ConfirmAlreadyRunError):
        _confirm(repo, principle_id="rule.a")
    with pytest.raises(ConfirmAlreadyRunError):  # a whole-plan confirm collides with all
        _confirm(repo)
    lines = (repo / "studies" / "demo" / "confirm_ledger.jsonl").read_text().splitlines()
    assert a["prev_sha256"] is None
    assert b["prev_sha256"] == seal._line_sha256(lines[0])  # hash chain
    assert a["external_timestamp"] is None and a["lineage"] == "demo"


def test_external_timestamp_is_appended_not_edited(repo):
    e = _confirm(repo, principle_id="rule.a")
    ledger = repo / "studies" / "demo" / "confirm_ledger.jsonl"
    before = ledger.read_text()
    h = seal.entry_sha256(e)
    st = seal.record_external_timestamp(ledger, h, "opentimestamps", "receipt-base64")
    after = ledger.read_text()
    assert after.startswith(before) and st["entry_sha256"] == h
    assert st["prev_sha256"] == seal._line_sha256(before.splitlines()[-1])
    with pytest.raises(SealError):
        seal.record_external_timestamp(ledger, "0" * 64, "ots", "r")
    # the stamp line is not a confirm: another principle may still confirm
    _confirm(repo, principle_id="rule.b")


def test_confirm_window_reads_every_committed_plan():
    """M3: gold, silver (periods.confirm_start), mundane (periods.confirm) and
    earthquake (split.confirm) plans all give a window."""
    import yaml
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    want = {
        "gold_market": ("2016-01-01", None),
        "silver_market": ("2016-01-01", None),
        "mundane": ("2011-01-01", "2026-10-31"),
        "earthquake": ("2011-01-01", "2026-10-31"),
    }
    for study, (start, end) in want.items():
        plan = yaml.safe_load((root / "studies" / study / "hypothesis.yaml").read_text())
        got = confirm_window(plan)
        assert got[0] == start, study
        if end is not None:
            assert got[1] == end, study


def test_confirm_window_split_and_nested_schemas():
    assert confirm_window({"split": {"confirm": ["2011-01-01", "2026-10-31"]}}) == (
        "2011-01-01", "2026-10-31")
    assert confirm_window({"periods": {"confirm": {"start": "2011-01-01", "end": "2020-01-01"}}}) == (
        "2011-01-01", "2020-01-01")
    assert confirm_window({"periods": {"confirm": {"start": "2011-01-01"}},
                           "data": {"end": "2012-01-01"}})[1] == "2012-01-01"
    with pytest.raises(SealError):
        confirm_window({"split": {"confirm": ["2011-01-01"]}})


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


def test_git_commit_counts_untracked_files(repo):
    """m5: one definition of dirty; an untracked module dirties the stamp."""
    from vedic_astrology_core.stats.manifest import git_commit

    assert git_commit(repo)["dirty"] is False
    (repo / "helper.py").write_text("x = 1\n")
    assert git_commit(repo)["dirty"] is True


def test_manifest_hashes_untracked_and_ignored_inputs(repo):
    """S-05: inputs outside version control are pinned by hash and marked."""
    import hashlib

    (repo / "ignored").mkdir()
    snap = repo / "ignored" / "snap.csv"
    snap.write_text("a,b\n1,2\n")
    loose = repo / "loose.py"
    loose.write_text("y = 2\n")
    plan = repo / "studies" / "demo" / "hypothesis.yaml"
    m = build_manifest(repo_root=repo, inputs=[{"path": snap}, {"path": loose}, {"path": plan}])
    by = {r["path"]: r for r in m["inputs"]}
    assert by["ignored/snap.csv"]["git_status"] == "ignored"
    assert by["ignored/snap.csv"]["sha256"] == hashlib.sha256(snap.read_bytes()).hexdigest()
    assert by["loose.py"]["git_status"] == "untracked"
    assert by["studies/demo/hypothesis.yaml"]["git_status"] == "tracked"
    assert {"path": "loose.py", "sha256": hashlib.sha256(loose.read_bytes()).hexdigest()} in m["untracked_files"]
    assert m["provisional"] is True
