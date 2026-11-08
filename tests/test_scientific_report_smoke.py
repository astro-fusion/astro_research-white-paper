"""Smoke tests for scientific report build."""

import json
import os
import subprocess
import sys

import pytest

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "research", "reports", "artifacts")
MANUSCRIPT_QMD = os.path.join(BASE_DIR, "research", "reports", "manuscript.qmd")
GENERATE_ARTIFACTS_SCRIPT = os.path.join(
    BASE_DIR, "research", "scripts", "generate_artifacts.py"
)


# 50 trading days of real COMEX gold closes (Yahoo Finance GC=F, from
# 2000-08-30) with planetary columns from the engine as it stood before the
# 2026-11-08 corrections (tropical longitudes). A pipeline smoke fixture only;
# not an input for any reported result.
FIXTURE_CSV = os.path.join(
    BASE_DIR, "tests", "fixtures", "gold_comex_tropical_planets_2000-08-30_50rows.csv"
)


def _run_generate_artifacts(tmp_path, data_path):
    env = dict(
        os.environ,
        ASTRO_ARTIFACTS_DIR=str(tmp_path),
        ASTRO_PROCESSED_DATA_PATH=str(data_path),
        MPLBACKEND="Agg",
    )
    return subprocess.run(
        [sys.executable, GENERATE_ARTIFACTS_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
    )


def test_artifact_generation(tmp_path):
    """Verify that the script runs on a real fixture and writes all artifacts.

    Output goes to a temporary directory so the repository stays untouched.
    """
    result = _run_generate_artifacts(tmp_path, FIXTURE_CSV)
    assert result.returncode == 0, f"Artifact generation failed: {result.stderr}"

    expected_files = [
        "tbl_stationarity.csv",
        "fig_periodogram.pdf",
        "stats_granger.json",
        "fig_molchan.pdf",
        "fig_permutation_dist.pdf",
    ]
    for filename in expected_files:
        path = tmp_path / filename
        assert path.exists(), f"Missing expected artifact: {filename}"

    with open(tmp_path / "stats_granger.json", "r") as f:
        data = json.load(f)
    for planet in ["Mars", "Saturn", "Jupiter"]:
        assert planet in data, f"Planet {planet} missing from granger stats"
        stats = data[planet]
        assert "F-Statistic" in stats
        assert "p-value" in stats
        assert "Significant" in stats


def test_artifact_generation_fails_without_data(tmp_path):
    """Missing input must fail loudly and never write placeholder data."""
    missing = tmp_path / "data" / "aligned_planetary_data.csv"
    result = _run_generate_artifacts(tmp_path / "out", missing)
    assert result.returncode != 0
    assert "not found" in result.stderr
    assert not missing.exists()
    assert not (tmp_path / "out" / "stats_granger.json").exists()


@pytest.mark.skipif(
    subprocess.run(["quarto", "--version"], capture_output=True).returncode != 0,
    reason="Quarto not installed",
)
def test_quarto_render_smoke():
    """Attempt a dry-run or partial render of the manuscript."""
    output_pdf = os.path.join(BASE_DIR, "reports", "smoke_test_render.pdf")

    # We use --to pdf and a specific output filename
    # We also use --execute to ensure the python blocks run
    result = subprocess.run(
        [
            "quarto",
            "render",
            MANUSCRIPT_QMD,
            "--to",
            "pdf",
            "-o",
            "smoke_test_render.pdf",
            "--execute",
        ],
        capture_output=True,
        text=True,
    )

    try:
        assert result.returncode == 0, f"Quarto render failed: {result.stderr}"
    finally:
        # Cleanup
        if os.path.exists(output_pdf):
            os.remove(output_pdf)
