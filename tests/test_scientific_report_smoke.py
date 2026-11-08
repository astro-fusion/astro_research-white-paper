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


def test_artifact_generation(tmp_path):
    """Verify that the script runs and produces all required files.

    Output goes to a temporary directory so tracked artifacts stay untouched.
    """
    env = dict(os.environ, ASTRO_ARTIFACTS_DIR=str(tmp_path))
    result = subprocess.run(
        [sys.executable, GENERATE_ARTIFACTS_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
    )
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


def test_dynamic_stats_integrity():
    """Verify that the committed JSON stats contain the expected keys and types."""
    json_path = os.path.join(ARTIFACTS_DIR, "stats_granger.json")
    with open(json_path, "r") as f:
        data = json.load(f)

    for planet in ["Mars", "Saturn", "Jupiter"]:
        assert planet in data, f"Planet {planet} missing from granger stats"
        stats = data[planet]
        assert "F-Statistic" in stats
        assert "p-value" in stats
        assert "Significant" in stats


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
