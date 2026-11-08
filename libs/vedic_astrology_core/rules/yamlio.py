"""Write a rule file back without losing its comments, key order or layout.

``astro-rules fit``, ``confirm`` and ``review`` change a few keys of a rule
file. They go through :func:`edit_rule_file`, which round-trips the file
with ruamel.yaml (comments and key order survive), keeps the file's own
sequence indentation and line width, and strips the trailing spaces
ruamel leaves after folded plain scalars.
"""

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Union

PathLike = Union[str, Path]


def _yaml(text: str):
    try:
        from ruamel.yaml import YAML
    except ImportError as exc:  # pragma: no cover - dev extra
        raise RuntimeError(
            "writing rule files needs ruamel.yaml: pip install -e '.[dev]'"
        ) from exc
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.representer.add_representer(
        type(None),
        lambda rep, _value: rep.represent_scalar("tag:yaml.org,2002:null", "null"),
    )
    longest = max((len(line) for line in text.splitlines()), default=80)
    yaml.width = max(88, min(longest - 4, 116))
    # "key:\n  - item" (offset 2) or "key:\n- item" (offset 0), as the file has it.
    indented = re.search(r"^[a-z_]+:\n  - ", text, re.M) is not None
    if indented:
        yaml.indent(mapping=2, sequence=4, offset=2)
    else:
        yaml.indent(mapping=2, sequence=2, offset=0)
    return yaml


def plain(value: Any) -> Any:
    """Convert numpy scalars, tuples and datetimes into YAML-friendly values."""
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        return value.item()
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        if value.is_integer() and abs(value) < 1e15:
            return int(value)
        return float(f"{value:.6g}")
    return value


def flow(value: Any):
    """Return a mapping or list that ruamel writes in flow style, ``{a: 1}``."""
    from ruamel.yaml.comments import CommentedMap, CommentedSeq

    out = CommentedSeq(value) if isinstance(value, list) else CommentedMap(value)
    out.fa.set_flow_style()
    return out


def edit_rule_file(path: PathLike, mutate: Callable[[Any], None]) -> str:
    """Load ``path``, let ``mutate`` change the mapping in place, write it back.

    Returns the new text. The leading ``# yaml-language-server`` comment and
    every other comment are kept.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    yaml = _yaml(text)
    data = yaml.load(text)
    mutate(data)
    buf = io.StringIO()
    yaml.dump(data, buf)
    out = "\n".join(line.rstrip() for line in buf.getvalue().splitlines()) + "\n"
    path.write_text(out, encoding="utf-8")
    return out


def insert_key(data: Any, key: str, value: Any, before: tuple = ("notes",)) -> None:
    """Set ``data[key]``; a new key goes before the first of ``before`` present."""
    if key in data:
        data[key] = value
        return
    keys = list(data.keys())
    for anchor in before:
        if anchor in keys:
            data.insert(keys.index(anchor), key, value)
            return
    data[key] = value


__all__ = ["edit_rule_file", "flow", "insert_key", "plain"]
