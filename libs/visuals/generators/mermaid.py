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


class MermaidGenerator(DiagramGenerator):
    """Generates Mermaid diagrams using Gemini."""

    def __init__(self, output_dir: str):
        """Docstring."""
        self.output_dir = output_dir
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if self.api_key and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)

    async def generate(self, request: DiagramRequest) -> str:
        """Docstring."""
        logger.info(f"Generating Mermaid diagram: {request.output_filename}")

        if not GENAI_AVAILABLE:
            logger.error(
                "google-generativeai library not found. Please install it via pip."
            )
            return ""

        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not found. Skipping Mermaid generation.")
            return ""

        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"""
        You are an expert in creating Mermaid.js diagrams.

        Context:
        {request.context}

        Goal:
        Create a Mermaid diagram that represents: {request.intent}

        Requirements:
        - Use standard Mermaid syntax (graph TD, sequenceDiagram, etc.).
        - Return ONLY the mermaid code block, e.g.:
        ```mermaid
        graph TD
          A --> B
        ```
        - Do not include any other markdown or text.
        """

        try:
            response = model.generate_content(prompt)
            content = response.text

            # Clean up response to get just the code
            mermaid_code = content.strip()
            if mermaid_code.startswith("```mermaid"):
                mermaid_code = mermaid_code[10:]
            if mermaid_code.startswith("```"):
                mermaid_code = mermaid_code[3:]
            if mermaid_code.endswith("```"):
                mermaid_code = mermaid_code[:-3]

            mermaid_code = mermaid_code.strip()

            output_path = os.path.join(self.output_dir, request.output_filename)

            with open(output_path, "w") as f:
                f.write(mermaid_code)

            logger.info(f"Saved Mermaid diagram to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate Mermaid diagram: {e}")
            raise e
