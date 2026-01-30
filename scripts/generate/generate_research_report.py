"""
Research Report CLI Wrapper
===========================

This script has been refactored to serve as the entry point for the new
Scientific Reporting Pipeline. It replaces the old monolithic ReportLab generator.

New Pipeline Workflow:
1. Data Ingestion: src/data/fetch_market_data.py
2. Astro Alignment: src/data/align_astro_data.py
3. Artifact Generation: src/generate_artifacts.py
4. Manuscript Rendering: Quarto

Usage:
    python scripts/generate/generate_research_report.py
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def run_step(script_path: str, description: str):
    """Runs a Python script as a subprocess."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    
    full_path = os.path.join(PROJECT_ROOT, script_path)
    try:
        subprocess.run([sys.executable, full_path], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run {description}")
        sys.exit(1)

def main():
    print("🚀 Starting Scientific Research Report Pipeline...\n")
    
    # Step 1: Fetch Data
    # run_step("src/data/fetch_market_data.py", "Fetching Market Data (Gold XAUUSD)")
    # Note: Skipping fetch step by default to avoid hammering Yahoo API. 
    # Use explicit call if needed.
    
    # Step 2: Align Data
    # run_step("src/data/align_astro_data.py", "Aligning Astronomical Ephemerides")
    
    # Step 3: Analyze & Generate Artifacts
    run_step("src/generate_artifacts.py", "Running Statistical Analysis & Generating Artifacts")
    
    print(f"\n{'='*60}")
    print("✅ PIPELINE COMPLETE")
    print(f"{'='*60}")
    print("\nNext Steps:")
    print("1. Review artifacts in: reports/artifacts/")
    print("2. Render the final manuscript PDF using Quarto:")
    print("   $ quarto render reports/manuscript.qmd --to pdf -o manuscript_nature.pdf  # Default Nature")
    print("   $ quarto render reports/manuscript.qmd --to pdf -M csl=styles/ieee.csl -o manuscript_ieee.pdf # IEEE Override")
    print("\nThe generated PDF will contain the rigorous scientific analysis required.")

if __name__ == "__main__":
    main()
