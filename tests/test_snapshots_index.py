"""Snapshot index, licence register and open-data fetch scripts (offline)."""

import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest

from vedic_astrology_core.datasets import snapshots as snap

REPO = Path(__file__).resolve().parents[1]
FRED_CSV = (
    REPO / "tests" / "fixtures" / "markets" / "fred_DEXUSUK_2019-12-20_2020-01-10.csv"
).read_text()


def _script(name):
    spec = importlib.util.spec_from_file_location(
        f"fetch_{name}", REPO / "scripts" / "fetch" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def env(tmp_path):
    return {
        "snapshot_root": tmp_path / "snapshots",
        "index_path": tmp_path / "idx.json",
        "repo_root": tmp_path,
    }


def test_licence_register_loads_and_unknown_raises():
    sources = snap.load_licences()
    assert sources["yahoo_finance"]["decision"] == "hash_only"
    assert sources["worldbank_pinksheet"]["decision"] == "commit"
    with pytest.raises(snap.SnapshotError):
        snap.licence_for("no_such_source")


def test_write_snapshot_adds_entry_and_verifies(env):
    path = snap.write_snapshot(
        b"a,b\n1,2\n", "demo", "csv", "gfz_kp", "http://x", rows=1, **env
    )
    assert path.name == f"demo_{snap.sha256_file(path)[:12]}.csv"
    entry = snap.load_index(env["index_path"])["snapshots"][0]
    assert entry["sha256"] == snap.sha256_file(path)
    assert entry["licence"] == "CC BY 4.0" and entry["committable"] is True
    assert entry["committed"] is False
    assert json.loads(Path(str(path) + ".manifest.json").read_text())["bytes"] == 8
    assert snap.verify_index(env["index_path"], env["snapshot_root"], env["repo_root"]) == []


def test_verify_fails_on_hash_mismatch(env):
    path = snap.write_snapshot(b"one", "demo", "txt", "gfz_kp", "u", **env)
    path.write_bytes(b"tampered")
    problems = snap.verify_index(env["index_path"], env["snapshot_root"], env["repo_root"])
    assert any("sha256" in p for p in problems)


def test_verify_fails_on_unlisted_snapshot(env):
    snap.write_snapshot(b"one", "demo", "txt", "gfz_kp", "u", **env)
    (env["snapshot_root"] / "stray_123.csv").write_text("x")
    problems = snap.verify_index(env["index_path"], env["snapshot_root"], env["repo_root"])
    assert problems == ["stray_123.csv: snapshot is not listed in the index"]


def test_hash_only_entry_may_be_absent_but_committed_may_not(env):
    path = snap.write_snapshot(b"one", "demo", "txt", "yahoo_finance", "u", **env)
    path.unlink()
    args = (env["index_path"], env["snapshot_root"], env["repo_root"])
    assert snap.verify_index(*args) == []
    index = snap.load_index(env["index_path"])
    index["snapshots"][0]["committed"] = True
    snap.save_index(index, env["index_path"])
    problems = snap.verify_index(*args)
    assert any("does not allow" in p for p in problems)
    assert any("missing" in p for p in problems)


def test_committed_repo_index_is_consistent():
    index = snap.load_index()
    assert index["snapshots"], "data/snapshot_index.json is empty"
    assert snap.verify_index() == []
    for entry in index["snapshots"]:
        assert entry["source_id"] in snap.load_licences()


def test_fred_script(env):
    path = _script("fred").run("DEXUSUK", "fred_us_gov", opener=lambda u: FRED_CSV, **env)
    entry = snap.load_index(env["index_path"])["snapshots"][0]
    assert entry["rows"] == 14 and entry["date_min"] == "2019-12-20"
    assert path.exists()
    with pytest.raises(SystemExit):
        _script("fred").run("GOLDPMGBD228NLBM", **env)
    with pytest.raises(SystemExit):
        _script("fred").run("DEXUSUK", **env)  # licence unknown: never guessed


def test_gfz_kp_script(env):
    text = "# header\n1932 01 01 1 1 0 0 3 3 3\n1932 01 02 2 2 0 0 3 3 3\n"
    _script("gfz_kp").run(opener=lambda u: text.encode(), **env)
    entry = snap.load_index(env["index_path"])["snapshots"][0]
    assert (entry["rows"], entry["date_min"], entry["date_max"]) == (2, "1932-01-01", "1932-01-02")


def test_cftc_script_filters_markets(env):
    csv = (
        "Market_and_Exchange_Names,Report_Date_as_YYYY-MM-DD,Open_Interest_All\n"
        '"GOLD - COMMODITY EXCHANGE INC.",2020-01-07,100\n'
        '"CORN - CHICAGO BOARD OF TRADE",2020-01-07,5\n'
        '"GOLD - COMMODITY EXCHANGE INC.",2020-01-14,110\n'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("annual.txt", csv)
    _script("cftc_cot").run([2020], opener=lambda u: buf.getvalue(), **env)
    entry = snap.load_index(env["index_path"])["snapshots"][0]
    assert entry["rows"] == 2 and entry["date_max"] == "2020-01-14"
    assert entry["source_id"] == "cftc_cot"


def test_pinksheet_script_rejects_non_xlsx_and_indexes(env):
    mod = _script("worldbank_pinksheet")
    with pytest.raises(SystemExit):
        mod.run(opener=lambda u: b"<html>", **env)
    mod.run(opener=lambda u: b"PK\x03\x04not-really-a-workbook", **env)
    entry = snap.load_index(env["index_path"])["snapshots"][0]
    assert entry["source_id"] == "worldbank_pinksheet" and entry["rows"] is None


def test_check_data_snapshots_only_passes_on_repo():
    mod = _script_at(REPO / "scripts" / "check_data.py")
    assert mod.main(["--snapshots-only"]) == 0


def _script_at(path):
    spec = importlib.util.spec_from_file_location("check_data_mod", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
