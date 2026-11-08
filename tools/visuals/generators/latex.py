"""Module docstring."""
import logging
import os

try:
    import google.generativeai as genai

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
from ..interface import DiagramGenerator, DiagramRequest

logger = logging.getLogger(__name__)


class LatexGenerator(DiagramGenerator):
    """Generates LaTeX/TikZ diagrams using Gemini."""

    def __init__(self, output_dir: str):
        """Docstring."""
        self.output_dir = output_dir
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if self.api_key and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)

    async def generate(self, request: DiagramRequest) -> str:
        """Docstring."""
        logger.info(f"Generating LaTeX diagram: {request.output_filename}")

        if not GENAI_AVAILABLE:
            logger.error(
                "google-generativeai library not found. Please install it via pip."
            )
            return ""

        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found. Skipping LaTeX generation.")
            return ""

        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = r"""
        You are an expert in creating LaTeX TikZ diagrams.

        Context:
        {request.context}

        Goal:
        Create a TikZ diagram that represents: {request.intent}

        Requirements:
        - Return ONLY the LaTeX code.
        - The code should be a standalone `\documentclass{standalone}` if
          possible, or just the `tikzpicture` environment.
        - Let's prefer standalone for easier verification.
        - Return ONLY the code block.
        """

        try:
            response = model.generate_content(prompt)
            content = response.text

            # Clean up response
            latex_code = content.strip()
            if latex_code.startswith("```latex"):
                latex_code = latex_code[8:]
            elif latex_code.startswith("```tex"):
                latex_code = latex_code[6:]
            elif latex_code.startswith("```"):
                latex_code = latex_code[3:]

            if latex_code.endswith("```"):
                latex_code = latex_code[:-3]

            latex_code = latex_code.strip()

            output_path = os.path.join(self.output_dir, request.output_filename)

            with open(output_path, "w") as f:
                f.write(latex_code)

            logger.info(f"Saved LaTeX diagram to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate LaTeX diagram: {e}")
            raise e
