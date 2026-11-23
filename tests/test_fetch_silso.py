"""ADR-007 WP-75 pattern: the SILSO sunspot fetch stores bytes unchanged, offline."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

from vedic_astrology_core.datasets import snapshots as snap

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_silso", REPO / "scripts" / "fetch" / "silso_sunspots.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BODY = (
    b"1749;01;1749.042;  96.7; -1.0;   -1;1\r\n"
    b"1749;02;1749.123; 104.3; -1.0;   -1;1\r\n"
    b"2026;10;2026.790;  45.7; 10.2; 1126;0\r\n"
)
LICENCES = (
    "sources:\n  silso_sunspots:\n    licence: test\n    terms_url: https://www.sidc.be/SILSO/legal\n"
    "    decision: hash_only\n"
)


@pytest.fixture()
def env(tmp_path):
    lic = tmp_path / "lic.yaml"
    lic.write_text(LICENCES)
    return {
        "snapshot_root": tmp_path / "snapshots",
        "index_path": tmp_path / "idx.json",
        "licences_path": lic,
        "repo_root": tmp_path,
    }


def test_bytes_are_stored_unchanged_and_indexed(env):
    seen = []
    path = mod.run(opener=lambda url: seen.append(url) or BODY, **env)
    assert path.read_bytes() == BODY
    entry = snap.load_index(env["index_path"])["snapshots"][0]
    assert entry["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert (entry["rows"], entry["date_min"], entry["date_max"]) == (3, "1749-01", "2026-10")
    assert entry["committable"] is False
    assert seen == [mod.URL]


def test_generic_client_name_only():
    assert mod.USER_AGENT == "astro-research-fetch/1.0"
    src = (REPO / "scripts" / "fetch" / "silso_sunspots.py").read_text()
    assert "@" not in src.split('"""')[2]


def test_series_must_start_in_1749(env):
    with pytest.raises(SystemExit):
        mod.run(opener=lambda url: b"2000;01;2000.042; 10.0; 1.0; 5;1\n", **env)


def test_unknown_licence_stops_without_writing(env):
    env["licences_path"].write_text("sources: {}\n")
    with pytest.raises(snap.SnapshotError):
        mod.run(opener=lambda url: BODY, **env)
    assert not env["snapshot_root"].exists() or not list(env["snapshot_root"].iterdir())
