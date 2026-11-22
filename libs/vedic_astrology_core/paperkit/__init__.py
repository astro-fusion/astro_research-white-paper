"""Paper kit: every number in a paper is read from ``results.json`` by key.

See ADR-004 D-7 and ``tools/check_paper_keys.py`` (the results-key gate).
"""

from .results import (
    PROVENANCE_KEYS,
    MissingKeyError,
    NullValueError,
    Results,
    format_number,
    format_p,
    provenance,
)

__all__ = [
    "PROVENANCE_KEYS",
    "MissingKeyError",
    "NullValueError",
    "Results",
    "format_number",
    "format_p",
    "provenance",
]
