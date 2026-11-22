"""ADR-007 WP-75: round-4 fetch scripts (offline, injected opener)."""

import importlib.util
from pathlib import Path

import pytest

from vedic_astrology_core.datasets import snapshots as snap

REPO = Path(__file__).resolve().parents[1]

# SHA-256 prefixes from the incoming audit of 2026-11-22.
AUDITED = {
    "bundesbank_gold_dem": ("87c15f38332d9916", 7622),
    "iitm_all_india_macro": ("76380a8e9ee3b635", None),
    "iitm_subdivisions": ("b8781f2be3a5f824", None),
    "iitm_longest_instrumental": ("633a217e7f49b70e", None),
    "noaa_oni": ("27af499bc406f8e5", None),
    "noaa_nino34": ("8ba6cd0536adffc9", None),
    "noaa_dmi_hadley": ("e243536c69444c7", None),
    "dfo_global_flood_records": ("9ebcb24b96e06f82", None),
    "usgs_comcat_himalaya_m55": ("a7192c45a45b1ba6", 182),
    "isc_bulletin_himalaya_m55": ("81b7fd2693dca0a5", 210),
}


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


def _entries(env):
    return snap.load_index(env["index_path"])["snapshots"]


def test_bundesbank_counts_values_not_empty_days(env):
    text = (
        '\N{ZERO WIDTH NO-BREAK SPACE}"";BBEX3.D.XAU.DEM.EA.AC.C01;FLAGS\n"";Goldpreis;\n'
        "1968-06-21;5292;\n1968-06-22;.;Kein Wert vorhanden\n"
        "1968-06-24;5293;\n1998-12-31;.;Kein Wert vorhanden\n"
    )
    mod = _script("bundesbank_gold")
    assert "BBEX3/D.XAU.DEM" in mod.URL and "BBEX3.D" not in mod.URL.split("data/")[1]
    mod.run(opener=lambda u: text.encode("utf-8"), **env)
    (entry,) = _entries(env)
    assert (entry["rows"], entry["date_min"], entry["date_max"]) == (2, "1968-06-21", "1968-06-24")
    assert entry["source_id"] == "bundesbank_gold" and entry["committable"] is True


def test_bundesbank_rejects_empty(env):
    with pytest.raises(SystemExit):
        _script("bundesbank_gold").run(opener=lambda u: b"<html></html>", **env)


def test_iitm_three_files_hash_only(env):
    text = (
        "146  ALL-INDIA  RAINFALL    (1871-2016)\n"
        " 1871 " + " ".join(["10.5"] * 17) + "\n"
        " 1872 " + " ".join(["11"] * 17) + "\n"
        "SD 141 125\n"
    )
    paths = _script("iitm_rainfall").run(opener=lambda u: text.encode(), **env)
    assert len(paths) == 3
    entries = _entries(env)
    assert {e["rows"] for e in entries} == {2}
    assert {(e["date_min"], e["date_max"]) for e in entries} == {("1871", "1872")}
    assert all(e["committable"] is False for e in entries)


def test_noaa_enso_skips_sentinels_and_footer(env):
    table = (
        " 1950 2026\n"
        "1950 -1.0 -1.1 -1.2 -1.3 -1.4 -1.5 -1.6 -1.7 -1.8 -1.9 -2.0 -2.1\n"
        "2026 0.1 0.2 -99.9 -99.9 -99.9 -99.9 -99.9 -99.9 -99.9 -99.9 -99.9 -99.9\n"
        "-99.90\nnote text\n"
    )
    _script("noaa_enso").run(opener=lambda u: table.encode(), **env)
    entries = {Path(e["file"]).name.split("_")[1]: e for e in _entries(env)}
    assert set(entries) == {"oni", "nino34", "dmi"}
    oni = entries["oni"]
    assert (oni["rows"], oni["date_min"], oni["date_max"]) == (14, "1950-01", "2026-02")
    assert oni["committable"] is True and entries["dmi"]["committable"] is False


def test_dfo_dates_and_rows(env):
    csv_text = (
        "\N{ZERO WIDTH NO-BREAK SPACE}#,Glide #,Start Date,End Date,Country\n"
        "5506,,1/6/24,1/9/24,Australia\n"
        "12,,1/1/85,1/5/85,Peru\n"
    )
    _script("dfo_floods").run(opener=lambda u: csv_text.encode("utf-8"), **env)
    (entry,) = _entries(env)
    assert (entry["rows"], entry["date_min"], entry["date_max"]) == (2, "1985-01-01", "2024-01-06")
    assert entry["licence"] == "CC0 1.0"
    with pytest.raises(SystemExit):
        _script("dfo_floods").run(opener=lambda u: b"a,b\n1,2\n", **env)


def test_usgs_rows_and_range(env):
    text = (
        "time,latitude,longitude,depth,mag\n"
        "2025-10-17T12:15:03.739Z,36.7,72.8,8,5.5\n"
        "1976-08-12T23:26:46.200Z,26.6,97.0,27,6.4\n"
    )
    mod = _script("usgs_catalogue")
    assert "minmagnitude=5.5" in mod.URL and "endtime=2026-01-01" in mod.URL
    mod.run(opener=lambda u: text.encode(), **env)
    (entry,) = _entries(env)
    assert (entry["rows"], entry["date_min"], entry["date_max"]) == (2, "1976-08-12", "2025-10-17")
    assert entry["source_id"] == "usgs_comcat"
    with pytest.raises(SystemExit):
        mod.run(opener=lambda u: b"<html>", **env)


def test_isc_ignores_agency_footer(env):
    text = (
        "#EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|Contributor|"
        "ContributorID|MagType|Magnitude|MagAuthor|EventLocationName|EventType\n"
        "709746|1976-08-12T23:26:48.188|26.6|97.1|26.6|ISC|ISC|ISC|1|MW|5.87|GCMT|Myanmar|earthquake\n"
        "1|2025-10-17T01:00:00.000|36.7|72.8|8|ISC|ISC|ISC|2|MW|5.5|GCMT|X|earthquake\n"
        "\n# Agencies whose data contributed\n# STR  EOST   France\n"
    )
    _script("isc_catalogue").run(opener=lambda u: text.encode(), **env)
    (entry,) = _entries(env)
    assert (entry["rows"], entry["date_min"], entry["date_max"]) == (2, "1976-08-12", "2025-10-17")
    assert entry["committable"] is False


def test_new_sources_in_licence_register_and_urls_https():
    sources = snap.load_licences()
    for key in ("bundesbank_gold", "iitm_rainfall", "noaa_enso", "noaa_dmi", "dfo_floods", "isc_bulletin"):
        assert key in sources
    for name in ("bundesbank_gold", "dfo_floods", "usgs_catalogue", "isc_catalogue"):
        assert _script(name).URL.startswith("https://")


def test_committed_index_has_audited_hashes():
    index = {Path(e["file"]).name: e for e in snap.load_index()["snapshots"]}
    for stem, (prefix, rows) in AUDITED.items():
        match = [e for name, e in index.items() if name.startswith(stem + "_")]
        assert match, f"{stem} is not in data/snapshot_index.json"
        assert match[0]["sha256"].startswith(prefix)
        if rows is not None:
            assert match[0]["rows"] == rows
    assert snap.verify_index() == []
