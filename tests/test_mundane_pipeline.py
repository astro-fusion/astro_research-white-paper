"""Tests for the mundane pipeline and catalogue fetcher helpers."""

import json

from studies.mundane.scripts import fetch_catalogues as fc
from studies.mundane.scripts import pipeline


def test_pipeline_is_seeded_and_complete(tmp_path):
    """Pipeline is seeded and complete."""
    a = pipeline.run(seed=7, limit=12, out_dir=tmp_path / "a")
    b = pipeline.run(seed=7, limit=12, out_dir=tmp_path / "b")
    assert a == b
    assert a["events_selected"] == 12 and a["countries"] == 113
    assert a["feature_rows"] > 0
    assert a["rows_time_known_false"] == a["feature_rows"]
    assert a["stats"] in {"pending", "available_not_wired"}
    on_disk = json.loads((tmp_path / "a" / "summary.json").read_text())
    assert on_disk == a
    table = "features." + ("parquet" if a["table_format"] == "parquet" else "csv")
    assert (tmp_path / "a" / table).exists()
    first = (tmp_path / "a" / table).read_bytes()
    assert first == (tmp_path / "b" / table).read_bytes()


def test_select_events_seed_changes_subset():
    """Select events seed changes subset."""
    events = [{"id": i} for i in range(100)]
    pick = pipeline.select_events
    assert pick(events, 10, 1) == pick(events, 10, 1)
    assert pick(events, 10, 1) != pick(events, 10, 2)
    assert pipeline.select_events(events, None, 1) is events


def test_offline_snapshot_writes_manifest(tmp_path):
    """Offline snapshot writes manifest."""
    dest = fc.snapshot_offline(tmp_path)
    manifest = json.loads((tmp_path / "events_tracked.jsonl.manifest.json").read_text())
    assert manifest["sha256"] == fc.sha256_of(dest)
    assert manifest["rows"] == 825


def test_emdat_stub_explains_licence(capsys, tmp_path):
    """Emdat stub explains licence."""
    assert fc.fetch_emdat(tmp_path) is None
    assert "registration" in capsys.readouterr().out


def test_dfo_without_url_exits_with_hint(tmp_path):
    """Dfo without url exits with hint."""
    import pytest
    with pytest.raises(SystemExit) as exc:
        fc.fetch_dfo(tmp_path)
    assert "--local" in str(exc.value)


def test_dfo_local_file_is_hashed(tmp_path):
    """Dfo local file is hashed."""
    src = tmp_path / "FloodArchive.csv"
    src.write_text("a,b\n1,2\n3,4\n")
    dest = fc.fetch_dfo(tmp_path / "snap", local=src)
    manifest = json.loads(
        (tmp_path / "snap" / (dest.name + ".manifest.json")).read_text())
    assert manifest["rows"] == 2 and manifest["sha256"] == fc.sha256_of(dest)
