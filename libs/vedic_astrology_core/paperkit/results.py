"""One accessor for the numbers in a paper (ADR-004 D-7).

``Results.get("headline.n_significant_explore")`` walks dotted keys through
nested dicts and lists (a list index is an integer segment, for example
``tests.0.p``). A missing key raises :class:`MissingKeyError`; a key whose
value is null or NaN raises :class:`NullValueError`. Nothing prints a blank
or a default, so a stale or misspelt key stops the build.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Union

PathLike = Union[str, Path]


class MissingKeyError(KeyError):
    """The dotted key is not present in the results file."""

    def __str__(self) -> str:  # KeyError would repr() the message
        return str(self.args[0]) if self.args else ""


class NullValueError(ValueError):
    """The key exists but holds null or NaN, which a paper must not print."""


def format_number(value: Any, digits: int = 2) -> str:
    """Format a number consistently: integers plain, floats to ``digits`` places.

    Booleans and non-numbers are rejected so a flag is never printed as 1.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"not a number: {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise NullValueError(f"non-finite number: {value!r}")
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def format_p(value: Any, digits: int = 3) -> str:
    """Format a p-value: ``p < 0.001`` below the floor, else ``p = 0.xxx``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"not a number: {value!r}")
    if not math.isfinite(value) or value < 0 or value > 1:
        raise ValueError(f"not a probability: {value!r}")
    floor = 10 ** -digits
    if value < floor:
        return f"p < {floor:.{digits}f}"
    return f"p = {value:.{digits}f}"


class Results:
    """A loaded ``results.json`` with strict dotted-key access."""

    def __init__(self, data: Dict[str, Any], path: PathLike = "<memory>"):
        self.data = data
        self.path = str(path)

    @classmethod
    def load(cls, path: PathLike) -> "Results":
        p = Path(path)
        with p.open() as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"{p}: top level must be an object")
        return cls(data, p)

    def has(self, key: str) -> bool:
        """True if the key exists (a null value still counts as present)."""
        try:
            self._walk(key)
        except MissingKeyError:
            return False
        return True

    def _walk(self, key: str) -> Any:
        if not isinstance(key, str) or not key:
            raise MissingKeyError(f"empty key in {self.path}")
        node: Any = self.data
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            elif isinstance(node, list) and part.lstrip("-").isdigit():
                try:
                    node = node[int(part)]
                except IndexError:
                    raise MissingKeyError(
                        f"key {key!r}: index {part} out of range in {self.path}"
                    ) from None
            else:
                raise MissingKeyError(f"key {key!r}: no {part!r} in {self.path}")
        return node

    def get(self, key: str) -> Any:
        """Return the value at ``key``; raise if missing, null or NaN."""
        value = self._walk(key)
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raise NullValueError(f"key {key!r} is null in {self.path}")
        return value

    def num(self, key: str, digits: int = 2) -> str:
        """The number at ``key`` as text with ``digits`` decimals."""
        return format_number(self.get(key), digits)

    def count(self, key: str) -> str:
        """The whole number at ``key`` as text."""
        value = self.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"key {key!r} is not a number: {value!r}")
        if float(value) != int(value):
            raise ValueError(f"key {key!r} is not whole: {value!r}")
        return str(int(value))

    def pct(self, key: str, digits: int = 1) -> str:
        """A fraction at ``key`` shown as a percentage, for example ``12.5%``."""
        value = self.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"key {key!r} is not a number: {value!r}")
        return f"{value * 100:.{digits}f}%"

    def p(self, key: str, digits: int = 3) -> str:
        """The p-value at ``key`` as ``p = 0.012`` or ``p < 0.001``."""
        return format_p(self.get(key), digits)

    def text(self, key: str) -> str:
        """The string at ``key``."""
        value = self.get(key)
        if not isinstance(value, str):
            raise TypeError(f"key {key!r} is not text: {value!r}")
        return value
