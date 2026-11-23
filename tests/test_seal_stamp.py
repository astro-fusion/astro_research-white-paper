"""ADR-008 WP-90: seal stamp (environment, ephemeris, files read) and study imports.

Strategy audit G-02 (seal does not cover environment or ignored inputs), G-03
(module-name collision between study scripts) and G-13 (no threads).
Each read path the audit hook must see has its own test: builtin open,
pathlib, pandas, yaml, numpy; Swiss Ephemeris reads its files in C, so the
ephemeris files are hashed from the ephemeris path instead.
"""

import json
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from vedic_astrology_core.stats import seal
from vedic_astrology_core.stats.manifest import build_manifest
from vedic_astrology_core.stats.seal import (
    EnvironmentMismatchError,
    SealedRun,
    ThreadStartedError,
    UntrackedReadError,
    environment_stamp,
    ephemeris_stamp,
    installed_versions,
    load_study_modules,
    read_lock,
    require_locked_environment,
    stamp_results,
)

REPO = Path(__file__).resolve().parents[1]
RULE = "kind: rule\nid: demo.tracked\n"


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_lock(path: Path, override=None) -> Path:
    pins = dict(installed_versions())
    pins.update(override or {})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{n}=={v}\n    # via test\n" for n, v in sorted(pins.items())))
    return path


@pytest.fixture
def repo(tmp_path):
    """A clean git repo: a tracked rule and csv, an ignored rule (the G-02 case), a lock."""
    r = tmp_path / "repo"
    (r / "rules" / "experimental").mkdir(parents=True)
    (r / "data").mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@example.invalid")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".gitignore").write_text("rules/experimental/ignored.yaml\ndata/snap_*.csv\nout/\n")
    (r / "rules" / "tracked.yaml").write_text(RULE)
    (r / "rules" / "experimental" / "ignored.yaml").write_text("kind: rule\nid: demo.ignored\n")
    (r / "data" / "tracked.csv").write_text("a,b\n1,2\n")
    (r / "data" / "snap_x.csv").write_text("a,b\n3,4\n")
    _write_lock(r / "ops" / "requirements.lock.txt")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "init")
    return r


def _run(repo, **kw):
    return SealedRun(repo, **kw)


# ------------------------------------------------------------- files read


def test_tracked_reads_pass_and_are_hashed(repo):
    with _run(repo) as run:
        yaml.safe_load((repo / "rules" / "tracked.yaml").read_text())
        pd.read_csv(repo / "data" / "tracked.csv")
        stamp = run.finish()
    paths = {r["path"]: r for r in stamp["files_read"]}
    assert paths["rules/tracked.yaml"]["status"] == "tracked"
    assert paths["data/tracked.csv"]["status"] == "tracked"
    assert len(paths["data/tracked.csv"]["sha256"]) == 64
    assert stamp["problems"] == [] and stamp["provisional"] is False
    assert stamp["threads_started"] == 0


def test_untracked_rule_file_read_fails_the_run(repo):
    """G-02: an ignored rule file read from a clean tree fails the sealed run (yaml path)."""
    with pytest.raises(UntrackedReadError, match="ignored.yaml"):
        with _run(repo):
            with open(repo / "rules" / "experimental" / "ignored.yaml") as fh:
                yaml.safe_load(fh)


def test_untracked_file_made_during_run_fails(repo):
    """A file created outside the run (untracked) and read through pathlib fails."""
    run = _run(repo).__enter__()
    other = repo / "rules" / "late.yaml"
    # Written before the run's log saw it? No: the log sees the write, so it is
    # run output. Write it with recording paused to model another process.
    run.log.stop()
    other.write_text(RULE)
    run.log.start()
    other.read_text()
    with pytest.raises(UntrackedReadError, match="late.yaml .untracked."):
        run.finish()


def test_pandas_read_of_ignored_csv_fails(repo):
    with pytest.raises(UntrackedReadError, match="snap_x.csv"):
        with _run(repo):
            pd.read_csv(repo / "data" / "snap_x.csv")


def test_numpy_read_of_ignored_file_fails(repo):
    path = repo / "out" / "arr.npy"
    path.parent.mkdir()
    np.save(path, np.arange(3))
    with pytest.raises(UntrackedReadError, match="arr.npy"):
        with _run(repo):
            np.load(path)


def test_indexed_snapshot_is_allowed(repo, tmp_path):
    """Snapshots listed in the index (by hash and name) may be read though ignored."""
    snap = repo / "data" / "snap_x.csv"
    index = tmp_path / "snapshot_index.json"
    index.write_text(json.dumps({"snapshots": [
        {"file": "data/snap_x.csv", "sha256": seal._file_sha256(snap)}]}))
    with _run(repo, snapshot_index=index) as run:
        pd.read_csv(snap)
        stamp = run.finish()
    assert {r["path"]: r["status"] for r in stamp["files_read"]}["data/snap_x.csv"] == "snapshot"
    # Same name, different bytes: not the indexed snapshot.
    index.write_text(json.dumps({"snapshots": [{"file": "data/snap_x.csv", "sha256": "0" * 64}]}))
    with pytest.raises(UntrackedReadError):
        with _run(repo, snapshot_index=index):
            pd.read_csv(snap)


def test_run_output_read_back_is_allowed(repo):
    with _run(repo) as run:
        out = repo / "out" / "res.json"
        out.parent.mkdir()
        out.write_text("{}")
        json.loads(out.read_text())
        stamp = run.finish()
    assert stamp["files_written"] == ["out/res.json"]
    assert {r["path"]: r["status"] for r in stamp["files_read"]}["out/res.json"] == "run_output"


def test_outside_repo_read_fails(repo, tmp_path):
    outside = tmp_path / "elsewhere.csv"
    outside.write_text("a\n1\n")
    with pytest.raises(UntrackedReadError, match="outside_repo"):
        with _run(repo):
            pd.read_csv(outside)


def test_provisional_records_but_does_not_refuse(repo):
    with _run(repo, provisional=True) as run:
        (repo / "rules" / "experimental" / "ignored.yaml").read_text()
        stamp = run.finish()
    assert stamp["provisional"] is True
    assert any("ignored.yaml (ignored)" in p for p in stamp["problems"])
    res = stamp_results({}, stamp)
    assert res["provisional"] is True
    assert res["seal"]["problems"] == stamp["problems"]
    assert res["seal"]["environment"]["lock_sha256"]


def test_hook_is_inert_outside_a_run(repo):
    run = _run(repo).__enter__()
    run.finish()
    n = len(run.log.events)
    (repo / "rules" / "tracked.yaml").read_text()
    assert len(run.log.events) == n


# ------------------------------------------------------------ environment


def test_lock_matches_installed(repo):
    stamp = require_locked_environment(repo / "ops" / "requirements.lock.txt")
    assert stamp["matches_lock"] is True and stamp["lock_mismatches"] == []
    assert stamp["python"].count(".") == 2 and len(stamp["lock_sha256"]) == 64


def test_changed_numpy_version_fails(repo):
    """G-02: a numpy version that differs from the lock refuses the sealed run."""
    lock = _write_lock(repo / "ops" / "requirements.lock.txt", {"numpy": "0.0.1"})
    _git(repo, "commit", "-qam", "lock with another numpy")
    with pytest.raises(EnvironmentMismatchError, match="numpy"):
        require_locked_environment(lock)
    with pytest.raises(EnvironmentMismatchError, match="numpy"):
        _run(repo).__enter__()
    with pytest.raises(EnvironmentMismatchError):
        build_manifest(repo_root=repo, require_clean=True, lock_path=lock)
    with _run(repo, provisional=True) as run:
        stamp = run.finish()
    mm = stamp["environment"]["lock_mismatches"]
    assert {"name": "numpy", "locked": "0.0.1", "installed": np.__version__} in mm
    assert stamp["environment"]["matches_lock"] is False


def test_missing_lock_refuses(tmp_path):
    with pytest.raises(EnvironmentMismatchError, match="no dependency lock"):
        require_locked_environment(tmp_path / "none.txt")


def test_read_lock_parses_uv_format(tmp_path):
    lock = tmp_path / "l.txt"
    lock.write_text("# header\nNumPy==2.0.0\n    # via x\nappnope==0.1 ; sys_platform == 'darwin'\n"
                    "ruamel.yaml==0.18 \\\n    --hash=sha256:abc\n")
    assert read_lock(lock) == {"numpy": "2.0.0", "appnope": "0.1", "ruamel-yaml": "0.18"}


def test_project_lock_is_stamped():
    stamp = environment_stamp()
    assert stamp["lock_path"] == "ops/requirements.lock.txt"
    assert len(stamp["lock_sha256"]) == 64


# -------------------------------------------------------------- ephemeris


def test_ephemeris_files_hashed(tmp_path):
    ephe = tmp_path / "ephe"
    ephe.mkdir()
    (ephe / "sepl_18.se1").write_bytes(b"planets")
    (ephe / "semo_18.se1").write_bytes(b"moon")
    st = ephemeris_stamp({"ephemeris_model": "swieph", "ayanamsa_system": "LAHIRI"}, ephe)
    assert [Path(f["path"]).name for f in st["files"]] == ["semo_18.se1", "sepl_18.se1"]
    assert all(len(f["sha256"]) == 64 for f in st["files"])
    assert st["model"] == "swieph" and st["problems"] == []


def test_ephemeris_swieph_without_files_is_a_problem(tmp_path, monkeypatch, repo):
    monkeypatch.delenv("SE_EPHE_PATH", raising=False)
    st = ephemeris_stamp({"ephemeris_model": "swieph"}, None)
    assert st["problems"]
    with pytest.raises(EnvironmentMismatchError, match="Swiss Ephemeris"):
        with _run(repo) as run:
            run.finish(engine={"ephemeris_model": "swieph"})


def test_ephemeris_engine_and_probe():
    from vedic_astrology_core.astrology.ephemeris import EphemerisEngine

    eng = EphemerisEngine()
    st = ephemeris_stamp(eng)
    assert st["model"] == eng.ephemeris_model and st["model_source"] == "engine"
    assert st["ayanamsa"] and st["swisseph_version"]
    probe = ephemeris_stamp()
    assert probe["model"] in ("swieph", "moshier", "jpl") and probe["model_source"] == "probe"


def test_manifest_carries_environment_and_ephemeris(repo):
    with _run(repo) as run:
        (repo / "rules" / "tracked.yaml").read_text()
        stamp = run.finish()
    m = build_manifest(repo_root=repo, run_stamp=stamp)
    assert m["environment"]["lock_sha256"] == stamp["environment"]["lock_sha256"]
    assert m["ephemeris"]["model"]
    assert [r["path"] for r in m["files_read"]] == ["rules/tracked.yaml"]
    assert m["threads_started"] == 0
    plain = build_manifest(repo_root=repo)
    assert "environment" in plain and "ephemeris" in plain


# ---------------------------------------------------------------- threads


def test_thread_in_sealed_run_fails(repo):
    """G-13: a sealed run that starts a thread is refused."""
    with pytest.raises(ThreadStartedError):
        with _run(repo):
            t = threading.Thread(target=lambda: None)
            t.start()
            t.join()
    with _run(repo, provisional=True) as run:
        t = threading.Thread(target=lambda: None)
        t.start()
        t.join()
        assert run.finish()["threads_started"] == 1


def test_stamp_and_study_imports_start_no_thread(repo):
    """G-13: recording, stamping and loading study scripts start no thread."""
    for name in list(sys.modules):
        if name.startswith("_study_earthquake__"):
            del sys.modules[name]
    from vedic_astrology_core.domains import earthquake

    before = threading.active_count()
    with _run(repo, provisional=True) as run:
        earthquake._study_modules()
        stamp = run.finish()
    assert stamp["threads_started"] == 0
    assert threading.active_count() == before


# -------------------------------------------------------- study imports G-03


def test_gold_and_earthquake_pipelines_resolve_to_their_own_file(monkeypatch):
    """G-03: with gold's pipeline imported first by bare name, earthquake still gets its own."""
    from vedic_astrology_core.domains import earthquake

    gold_dir = REPO / "studies" / "gold_market" / "scripts"
    eq_dir = REPO / "studies" / "earthquake" / "scripts"
    monkeypatch.setattr(sys, "path", [str(gold_dir)] + list(sys.path))
    for name in ("pipeline", "decluster", "indicators", "robustness", "fetch_catalogue",
                 "count_models"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    import pipeline as first  # noqa: PLC0415 - the old first-import-wins path

    assert Path(first.__file__).resolve() == gold_dir / "pipeline.py"
    for name in [n for n in sys.modules if n.startswith("_study_earthquake__")]:
        monkeypatch.delitem(sys.modules, name)  # force a fresh load in this test
    path_before = list(sys.path)
    decluster, fc, ind, eq_pipeline, rb = earthquake._study_modules()
    assert Path(eq_pipeline.__file__).resolve() == eq_dir / "pipeline.py"
    for mod, name in ((decluster, "decluster"), (fc, "fetch_catalogue"), (ind, "indicators"),
                      (rb, "robustness")):
        assert Path(mod.__file__).resolve() == eq_dir / f"{name}.py"
    # The earthquake pipeline's own sibling imports point at its folder.
    assert eq_pipeline.decluster is decluster and eq_pipeline.ind is ind
    assert eq_pipeline.__name__ == "_study_earthquake__pipeline"
    # The bare name is left as it was, and no script folder stays on sys.path.
    assert sys.modules["pipeline"] is first
    assert [p for p in sys.path if p not in path_before and Path(p).resolve() == eq_dir] == []

    gold = load_study_modules(gold_dir, ["pipeline"], namespace="gold_market")["pipeline"]
    assert Path(gold.__file__).resolve() == gold_dir / "pipeline.py"
    assert gold is not eq_pipeline and gold.__name__ == "_study_gold_market__pipeline"
    assert sys.modules["pipeline"] is first


def test_study_modules_are_loaded_once():
    from vedic_astrology_core.domains import earthquake

    a = earthquake._study_modules()
    b = earthquake._study_modules()
    assert all(x is y for x, y in zip(a, b))


# ------------------------------------------------ strategy audit 2 N-12: Python version


def test_n12_python_version_in_the_lock_header_is_enforced(repo):
    """Before: the Python version was recorded and never compared with the lock."""
    lock = repo / "ops" / "requirements.lock.txt"
    body = lock.read_text()
    lock.write_text("#    uv pip compile pyproject.toml --python-version 2.7 -o ops/requirements.lock.txt\n" + body)
    stamp = environment_stamp(lock)
    assert stamp["lock_python"] == "2.7" and stamp["python_matches_lock"] is False
    assert stamp["matches_lock"] is False
    with pytest.raises(EnvironmentMismatchError, match="Python"):
        require_locked_environment(lock)
    assert require_locked_environment(lock, provisional=True)["python_matches_lock"] is False
    here = ".".join(sys.version.split()[0].split(".")[:2])
    lock.write_text(f"#    uv pip compile --python-version {here} -o x\n" + body)
    ok = require_locked_environment(lock)
    assert ok["lock_python"] == here and ok["matches_lock"] is True


def test_n12_project_lock_names_its_python():
    assert seal.lock_python(REPO / "ops" / "requirements.lock.txt") == "3.12"
