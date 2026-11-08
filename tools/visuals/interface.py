"""Module docstring."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DiagramRequest:
    """Docstring."""

    context: str
    intent: str
    output_filename: str
    caption: str = ""


class DiagramGenerator(ABC):
    """Abstract base class for diagram generators."""

    @abstractmethod
    async def generate(self, request: DiagramRequest) -> str:
        """
        Generate a diagram based on the request.

        Args:
            request (DiagramRequest): The details of the diagram to generate.

        Returns:
            str: The path to the generated file.
        """
        pass
