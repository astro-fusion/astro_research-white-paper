"""Pytest setup shared by every test.

The engine is an installed package: ``pip install -e ".[dev]"`` exposes
``vedic_astrology_core`` and ``vedic_numerology`` (sources under ``libs/``),
so no ``PYTHONPATH`` is needed. The repository root is put on ``sys.path``
here so tests can also import the trees that are not packaged: ``studies``,
``scripts``, ``application`` and ``tools``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
