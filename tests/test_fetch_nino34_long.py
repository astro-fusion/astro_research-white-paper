"""WP-95: the long Nino 3.4 fetch stores bytes unchanged, offline."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

from vedic_astrology_core.datasets import snapshots as snap

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_nino34_long", REPO / "scripts" / "fetch" / "nino34_long.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Deliberately odd bytes: CRLF, trailing spaces, a non-UTF-8 byte.
BODY = (
    b"          1870        1872\r\n"
    + b" 1870    25.58   25.57   26.43   26.96   26.59   26.61   26.19   25.99   26.22   25.82   25.86   25.79  \r\n"
    + b" 1871    26.33   26.18   26.83   27.27   27.16   27.16   26.62   26.54   26.5    26.1    25.9    25.8\r\n"
    + b" 1872   -99.99  -99.99  -99.99  -99.99  -99.99  -99.99  -99.99  -99.99  -99.99  -99.99  -99.99  -99.99\r\n"
    + b"\xb0 footer\r\n"
)
LICENCES = (
    "sources:\n  noaa_nino34_long:\n    licence: test\n    terms_url: https://psl.noaa.gov/\n"
    "    decision: commit\n"
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
    assert (entry["rows"], entry["date_min"], entry["date_max"]) == (24, "1870-01", "1871-12")
    assert seen == [mod.URL]


def test_generic_client_name_only():
    assert mod.USER_AGENT == "astro-research-fetch/1.0"
    src = (REPO / "scripts" / "fetch" / "nino34_long.py").read_text()
    assert "@" not in src.split('"""')[2]  # no contact details in code


def test_series_must_start_by_1871(env):
    late = b"          1948        1950\n 1948 " + b" 26.0" * 12 + b"\n"
    with pytest.raises(SystemExit):
        mod.run(opener=lambda url: late, **env)


def test_unknown_licence_stops_without_writing(env, tmp_path):
    env["licences_path"].write_text("sources: {}\n")
    with pytest.raises(snap.SnapshotError):
        mod.run(opener=lambda url: BODY, **env)
    assert not env["snapshot_root"].exists() or not list(env["snapshot_root"].iterdir())
