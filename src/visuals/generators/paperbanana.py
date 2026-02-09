import logging
import os

from ..interface import DiagramGenerator, DiagramRequest

try:
    from paperbanana import DiagramType, GenerationInput, PaperBananaPipeline
    from paperbanana.core.config import Settings

    PAPERBANANA_AVAILABLE = True
except ImportError:
    PAPERBANANA_AVAILABLE = False


logger = logging.getLogger(__name__)


class PaperBananaGenerator(DiagramGenerator):
    """Generates diagrams using PaperBanana."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    async def generate(self, request: DiagramRequest) -> str:
        logger.info(f"Generating PaperBanana diagram: {request.output_filename}")

        if not PAPERBANANA_AVAILABLE:
            logger.error("PaperBanana library not found. Please install it via pip.")
            return ""

        settings = Settings(
            vlm_provider="gemini",
            image_provider="google_imagen",
            refinement_iterations=3,
            output_dir=self.output_dir,
        )

        pipeline = PaperBananaPipeline(settings=settings)

        input_data = GenerationInput(
            source_context=request.context,
            communicative_intent=request.intent,
            diagram_type=DiagramType.METHODOLOGY,
            caption=request.caption,
        )

        try:
            result = await pipeline.generate(input_data)

            # PaperBanana generates a filename based on timestamp/id.
            # We rename it to the requested filename for consistency.
            final_path = os.path.join(self.output_dir, request.output_filename)

            if result.image_path and os.path.exists(result.image_path):
                # If target exists, remove it first to avoid errors on some systems
                if os.path.exists(final_path):
                    os.remove(final_path)

                os.rename(result.image_path, final_path)
                logger.info(f"Saved PaperBanana diagram to {final_path}")
                return final_path
            else:
                logger.warning(
                    f"PaperBanana finished but image path is unclear: {result}"
                )
                return ""

        except Exception as e:
            logger.error(f"Failed to generate PaperBanana diagram: {e}")
            raise e
