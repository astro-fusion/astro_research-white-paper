"""Shared helpers for writing migrated rule files with computed reference cases."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "libs"))

from vedic_astrology_core.rules.engine import evaluate  # noqa: E402
from vedic_astrology_core.rules.schema import Rule  # noqa: E402

ENGINE_NOTE = (
    "astro-research engine 2026-11-08 (Lahiri, mean node); not yet checked in JHora"
)


class Dumper(yaml.SafeDumper):
    """Indent lists under their key; never emit anchors."""

    def ignore_aliases(self, data):
        """Never emit YAML anchors."""
        return True

    def increase_indent(self, flow=False, indentless=False):
        """Indent block sequences under their key."""
        return super().increase_indent(flow, False)


def _str(dumper, data):
    if "\n" in data or len(data) > 80:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


Dumper.add_representer(str, _str)


def iso(dt):
    """Return ``dt`` as a UTC ISO-8601 string with a Z suffix."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def moments(start, end, step):
    """Yield datetimes from ``start`` to ``end`` every ``step``."""
    t = start
    while t <= end:
        yield t
        t += step


def find_cases(
    rule_dict,
    candidates,
    place=None,
    natal=None,
    want=("fires", "silent"),
    run=3,
    cap=4000,
):
    """Middle moment of the first run of each wanted outcome.

    A run is a stretch of consecutive candidate moments with the same
    outcome; its middle is far from the boundaries, so the case does not
    flip with a small change in ephemeris or ayanamsa.
    """
    rule = _scratch(rule_dict)
    natal_spec = None
    if natal is not None:
        from vedic_astrology_core.rules.schema import ChartSpec

        natal_spec = ChartSpec.model_validate(natal)
    found = {}
    current, stretch = None, []

    def close():
        if current in want and current not in found and len(stretch) >= run:
            found[current] = stretch[len(stretch) // 2]

    for t in candidates:
        key = "fires" if evaluate(rule, t, place, natal_spec).fired else "silent"
        if key != current or len(stretch) >= cap:
            close()
            current, stretch = key, []
        stretch.append(t)
        if all(w in found for w in want):
            break
    close()
    return found


def _scratch(rule_dict):
    d = dict(rule_dict)
    d["tier"] = "experimental"
    d["status"] = "active"
    d["reference_cases"] = [
        {"moment": "2000-01-01T00:00:00Z", "expect": "fires", "note": "x"}
    ]
    return Rule.model_validate(d)


def explain_words(rule_dict, t, place=None, natal=None):
    """Return the plain-word explanation of a rule at moment ``t``."""
    from vedic_astrology_core.rules.schema import ChartSpec

    rule = _scratch(rule_dict)
    natal_spec = ChartSpec.model_validate(natal) if natal else None
    res = evaluate(rule, t, place, natal_spec)
    leaves = []

    def walk(node):
        if not node.children:
            leaves.append(node.evidence)
        for c in node.children:
            walk(c)

    walk(res.tree)
    return res.fired, "; ".join(leaves)


def make_cases(
    rule_dict,
    candidates,
    place=None,
    natal=None,
    want=("fires", "silent"),
    run=3,
    extra_note="",
):
    """Pick computed true and false reference cases for a rule."""
    found = find_cases(rule_dict, candidates, place, natal, want, run)
    cases = []
    for expect in want:
        if expect not in found:
            continue
        t = found[expect]
        fired, words = explain_words(rule_dict, t, place, natal)
        assert fired == (expect == "fires")
        case = {"moment": iso(t)}
        if place is not None:
            case["place"] = dict(place)
        if natal is not None:
            case["natal"] = natal
        case["expect"] = expect
        case["note"] = (extra_note + " " if extra_note else "") + words
        case["verified_with"] = ENGINE_NOTE
        cases.append(case)
    return cases


def write_rule(path, rule_dict, schema_rel):
    """Validate a rule and write it as YAML with a schema header."""
    Rule.model_validate(rule_dict)  # fail fast
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.dump(
        rule_dict, Dumper=Dumper, sort_keys=False, width=88, allow_unicode=True
    )
    path.write_text(f"# yaml-language-server: $schema={schema_rel}\n" + text)


def daily(start="1990-01-01", end="2035-12-31", hour=6):
    """Return a daily UTC moment generator over a date range."""
    s = datetime.fromisoformat(start).replace(hour=hour, tzinfo=timezone.utc)
    e = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    return moments(s, e, timedelta(days=1))
