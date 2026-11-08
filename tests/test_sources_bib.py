"""papers/sources.bib parses, and every practitioner rule cites an entry in it."""

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).parent.parent
BIB = REPO / "papers" / "sources.bib"
RULE_FILES = sorted(REPO.glob("rules/*/practitioner/*.yaml"))


def _entries():
    """Map bib key to its fields, with pybtex when installed, else a strict regex."""
    text = BIB.read_text()
    try:
        from pybtex.database import parse_string
    except ImportError:  # pragma: no cover - pybtex is a research extra
        parse_string = None
    if parse_string is not None:
        data = parse_string(text, "bibtex")
        return {
            key: {k.lower(): str(v) for k, v in e.fields.items()}
            for key, e in data.entries.items()
        }
    assert text.count("{") == text.count("}"), "unbalanced braces"
    out = {}
    for m in re.finditer(r"@(\w+)\{([^,\s]+),(.*?)\n\}", text, re.S):
        fields = dict(re.findall(r"(\w+)\s*=\s*\{(.*?)\},?\n", m.group(3) + "\n"))
        out[m.group(2)] = {k.lower(): v for k, v in fields.items()}
    return out


ENTRIES = _entries()
URLS = {e.get("url") for e in ENTRIES.values() if e.get("url")}


def test_bib_parses_with_unique_keys():
    """Every entry parses; keys are unique (pybtex raises on duplicates)."""
    keys = re.findall(r"^@\w+\{([^,]+),", BIB.read_text(), re.M)
    assert len(keys) == len(set(keys)) == len(ENTRIES)
    assert len(ENTRIES) >= 50


def test_no_commissioned_survey_is_cited():
    """The AI-generated surveys led to sources; they are never cited as one."""
    text = BIB.read_text().lower()
    for word in ("gemini", "grok", "deep research", "commissioned survey"):
        assert word not in re.sub(r"^%.*$", "", text, flags=re.M), word


def test_there_are_practitioner_rules():
    """The practitioner folders are populated."""
    assert len(RULE_FILES) >= 30


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda p: p.stem)
def test_practitioner_rule_sources_resolve(path):
    """source.url is in the bib (or inline), and every cited key exists."""
    rule = yaml.safe_load(path.read_text())
    assert rule["tier"] == "experimental"
    url = rule["source"].get("url")
    assert url and url.startswith(("http://", "https://")), "source.url must be a URL"
    assert url in URLS, f"{url} has no entry in papers/sources.bib"
    notes = rule["notes"]
    for key in notes["bib"]:
        assert key in ENTRIES, key
    root = notes["root_source"]
    assert root.get("bibkey") is None or root["bibkey"] in ENTRIES
    assert root.get("citation")
    prac = notes["practitioner"]
    assert prac["url"] == url and prac["name"] and prac["title"] and prac["date"]
    if rule["status"] == "needs_predicates":
        assert notes["missing_predicates"] and rule["conditions"] is None
    else:
        assert rule.get("reference_cases"), "an active rule needs a reference case"
