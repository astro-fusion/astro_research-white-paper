"""Tests for manifests, the plotting footer and pre-specified spectra."""

import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from vedic_astrology_core.stats.manifest import (  # noqa: E402
    file_sha256,
    git_commit,
    manifest_path,
    write_manifest,
)
from vedic_astrology_core.stats.plots import save_figure  # noqa: E402
from vedic_astrology_core.stats.spectral import (  # noqa: E402
    lomb_scargle_at_periods,
)

ABC_SHA = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_known_answer(tmp_path):
    """SHA-256 of b'abc'."""
    f = tmp_path / "a.txt"
    f.write_bytes(b"abc")
    assert file_sha256(f) == ABC_SHA


def test_manifest_written_next_to_artifact(tmp_path):
    """A file artifact gets <name>.manifest.json with every required field."""
    data = tmp_path / "data.csv"
    data.write_bytes(b"abc")
    art = tmp_path / "table.csv"
    art.write_text("x\n")
    engine = {
        "ephemeris_model": "moshier",
        "ayanamsa_system": "lahiri",
        "node_model": "mean",
        "version": "2.10",
    }
    path = write_manifest(
        art,
        inputs=[{"path": data, "row_count": 1, "date_range": ["2000", "2001"]}],
        seed=42,
        engine=engine,
        repo_root=tmp_path,
    )
    assert path == tmp_path / "table.csv.manifest.json"
    m = json.loads(path.read_text())
    assert m["inputs"][0]["sha256"] == ABC_SHA
    assert m["inputs"][0]["path"] == "data.csv"
    assert (m["seed"], m["ephemeris_model"], m["ayanamsa"], m["node_model"]) == (
        42,
        "moshier",
        "lahiri",
        "mean",
    )
    assert manifest_path(tmp_path) == tmp_path / "manifest.json"


def test_git_commit_outside_repo(tmp_path):
    """Outside a repository the commit is None, not an error."""
    assert git_commit(tmp_path)["commit"] is None


def test_save_figure_adds_footer(tmp_path):
    """The footer carries hash, commit and seed; missing keys raise."""
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    out = save_figure(
        fig,
        tmp_path / "f.png",
        {"data_sha256": "abcdef0123456789", "commit": "1234567890ab", "seed": 7},
    )
    assert out.exists() and out.stat().st_size > 0
    texts = [t.get_text() for t in fig.texts]
    assert any("abcdef012345" in t and "seed 7" in t for t in texts)
    with pytest.raises(KeyError):
        save_figure(fig, tmp_path / "g.png", {"seed": 1})
    plt.close(fig)


def test_lomb_scargle_finds_prespecified_period():
    """A 29.5-day sinusoid has a tiny FAP at 29.5 days and not at 365."""
    rng = np.random.default_rng(0)
    idx = pd.date_range("2000-01-01", periods=2000, freq="D")
    y = np.sin(2 * np.pi * np.arange(2000) / 29.5) + rng.normal(size=2000)
    res = lomb_scargle_at_periods(pd.Series(y, idx), [29.5, 365.25])
    assert res.loc[0, "fap_bonferroni"] < 1e-10
    assert res.loc[1, "fap_bonferroni"] > 0.01
