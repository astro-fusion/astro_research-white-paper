"""
AI Visuals Generator
====================

This script uses the PaperBanana library to generate academic-quality diagrams
and figures for the research report.

It requires the GOOGLE_API_KEY environment variable to be set.
"""

import asyncio
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for API Key
if not os.environ.get("GOOGLE_API_KEY"):
    logger.warning("GOOGLE_API_KEY not found. Skipping AI diagram generation.")
    sys.exit(0)

try:
    from paperbanana import DiagramType, GenerationInput, PaperBananaPipeline
    from paperbanana.core.config import Settings
except ImportError:
    logger.error("PaperBanana library not found. Please install it via pip.")
    sys.exit(1)

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "research", "reports", "artifacts")

# Ensure artifacts directory exists
os.makedirs(ARTIFACTS_DIR, exist_ok=True)


async def generate_methodology_diagram():
    """Generates a methodology diagram using PaperBanana."""
    logger.info("Generating AI Methodology Diagram...")

    settings = Settings(
        vlm_provider="gemini",
        image_provider="google_imagen",
        refinement_iterations=3,
        output_dir=ARTIFACTS_DIR,
    )

    pipeline = PaperBananaPipeline(settings=settings)

    # Context for the diagram
    # Ideally, this would be read from a file or the paper content itself.
    context = """
    Our research pipeline consists of three main stages:
    1. Data Ingestion: Fetching market data (Gold XAUUSD) and astronomical ephemerides.
    2. Data Alignment: Merging time-series data and calculating planetary positions.
    3. Statistical Analysis: Running Granger Causality, Lomb-Scargle Periodograms, and Molchan trajectories to test correlations between planetary movements and gold price volatility.
    The final output is a rendered Quarto research report.
    """

    input_data = GenerationInput(
        source_context=context,
        communicative_intent="A flow diagram showing the data processing pipeline from raw data to final analysis.",
        diagram_type=DiagramType.METHODOLOGY,
        caption="Automated Research Pipeline Flow",
    )

    try:
        result = await pipeline.generate(input_data)

        # Rename/Move the output to a standard name if needed,
        # but PaperBanana returns the path.
        # We might want to symlink or copy it to a fixed name for Quarto.
        final_path = os.path.join(ARTIFACTS_DIR, "fig_methodology_ai.png")

        # Check if result.image_path exists and move it
        if result.image_path and os.path.exists(result.image_path):
            # basic file move/rename logic
            os.rename(result.image_path, final_path)
            logger.info(f"Saved diagram to {final_path}")
        else:
            logger.warning(f"PaperBanana finished but image path is unclear: {result}")

    except Exception as e:
        logger.error(f"Failed to generate diagram: {e}")
        # specific error handling if needed


def main():
    asyncio.run(generate_methodology_diagram())


if __name__ == "__main__":
    main()
