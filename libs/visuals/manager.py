"""Module docstring."""
import asyncio
import logging
from typing import Dict, List

from .generators import LatexGenerator, MermaidGenerator, PaperBananaGenerator
from .interface import DiagramGenerator, DiagramRequest

logger = logging.getLogger(__name__)


class VisualsManager:
    """Orchestrates diagram generation using available generators."""

    def __init__(self, output_dir: str):
        """Docstring."""
        self.output_dir = output_dir
        self.generators: Dict[str, DiagramGenerator] = {
            "paperbanana": PaperBananaGenerator(output_dir),
            "mermaid": MermaidGenerator(output_dir),
            "latex": LatexGenerator(output_dir),
        }

    async def generate_diagrams(self, requests: List[DiagramRequest]):
        """Generate multiple diagrams in parallel."""
        tasks = []
        for req in requests:
            # Determine generator based on output filename extension or explicit type
            # For now, let's infer from extension or default to paperbanana
            generator_key = "paperbanana"

            if req.output_filename.endswith(".mmd"):
                generator_key = "mermaid"
            elif req.output_filename.endswith(".tex"):
                generator_key = "latex"
            elif req.output_filename.endswith(".png"):
                generator_key = "paperbanana"

            generator = self.generators.get(generator_key)
            if generator:
                tasks.append(generator.generate(req))
            else:
                logger.warning(f"No generator found for {req.output_filename}")

        await asyncio.gather(*tasks)


async def run_visuals_generation(output_dir: str):
    """Entry point for the pipeline."""
    manager = VisualsManager(output_dir)

    # Define the diagrams we want to generate
    # This could be externalized to a config file later
    requests = [
        # 1. Methodology Flow (PaperBanana - High Level Visual)
        DiagramRequest(
            context="""
            Our research pipeline consists of three main stages:
            1. Data Ingestion: Fetching market data (Gold XAUUSD) and
               astronomical ephemerides.
            2. Data Alignment: Merging time-series data and calculating
               planetary positions.
            3. Statistical Analysis: Running Granger Causality, Lomb-Scargle
               Periodograms, and Molchan trajectories.
            The final output is a rendered Quarto research report.
            """,
            intent="A flow diagram showing the data processing pipeline from raw data to final analysis.",  # noqa: E501
            output_filename="fig_methodology_ai.png",
            caption="Automated Research Pipeline Flow",
        ),
        # 2. System Architecture (Mermaid - Technical)
        DiagramRequest(
            context="""
            The system is built using Python.
            Modules:
            - src.data: Handlers for Yahoo Finance and Swiss Ephemeris.
            - src.models: Statistical tests (stationarity, causality).
            - libs.visuals: Diagram generation system with plugins for
              PaperBanana, Mermaid, LaTeX.
            - research/scripts: CLI entry points.
            Data flows from libs.models -> libs.visuals -> research/reports/.
            """,
            intent="A class diagram or component diagram showing the module dependencies.",  # noqa: E501
            output_filename="fig_architecture.mmd",
            caption="System Architecture",
        ),
        # 3. Mathematical Model (LaTeX - Exact Formula)
        DiagramRequest(
            context="""
            We model the relationship between Gold Volatility (sigma_t)
            and Planetary Speed (v_t) using a linear regression with
            seasonal components.
            Formula: sigma_t = alpha + beta * v_t + gamma * sin(2*pi*t/P) + epsilon_t
            """,
            intent=(
                "A visual representation of the regression model equation "
                "or a conceptual plot of a sine wave fitted to data points."
            ),
            output_filename="fig_math_model.tex",
            caption="Mathematical Model",
        ),
    ]

    await manager.generate_diagrams(requests)


if __name__ == "__main__":
    import os

    # Default path for testing
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "reports", "artifacts")
    asyncio.run(run_visuals_generation(ARTIFACTS_DIR))
