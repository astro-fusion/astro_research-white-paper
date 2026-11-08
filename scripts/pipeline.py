#!/usr/bin/env python3
"""
AstroFusion Research Automation Pipeline.

=======================================
This script automates the end-to-end research flow:
1. Data Ingestion/Generation
2. Feature Engineering
3. Statistical Analysis & Metrics Computation
4. Artifact Generation for Thesis
"""

import logging
import subprocess  # nosec B404
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TRACKS = {
    "track_2_earthquake": {
        "dir": REPO_ROOT / "research/use_cases/earthquake",
        "scripts": [
            "generate_daily_astro_features.py",
            "generate_combination_catalog.py",
            "compute_combination_metrics.py",
        ],
    },
    "track_3_gold": {
        "dir": REPO_ROOT / "research/use_cases/gold_market",
        "scripts": [
            "fetch_gold_data.py",
            "generate_gold_astro_features.py",
            "generate_gold_astro_catalog.py",
            "compute_gold_astro_metrics.py",
        ],
    },
}


def run_script(script_path: Path):
    """Docstring."""
    logger.info(f"Running: {script_path.name}")
    try:
        subprocess.check_call([sys.executable, str(script_path)])  # nosec B603
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {script_path}: {e}")
        sys.exit(1)


def main():
    """Docstring."""
    logger.info("Starting AstroFusion Research Pipeline...")

    # 1. Run Global Artifact Generator
    run_script(REPO_ROOT / "src/generate_artifacts.py")

    # 2. Run Track-specific scripts
    for track_name, track_info in TRACKS.items():
        logger.info(f"=== Processing {track_name} ===")
        script_dir = track_info["dir"] / "scripts"
        for script_name in track_info["scripts"]:
            run_script(script_dir / script_name)

    # 3. Final Step: Reminder for Quarto
    logger.info("=== Pipeline Complete ===")
    logger.info("You can now render the final report using:")
    logger.info("quarto render docs/research/COMPREHENSIVE_RESEARCH_THESIS.qmd")


if __name__ == "__main__":
    main()
