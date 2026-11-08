"""The website's structure: navigation, explorers, components, theme."""

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
EXPLORERS = {
    "explore/sky-events.qmd": "sky-events-chart",
    "explore/effects.qmd": "effects-chart",
    "explore/markets.qmd": "markets-dist",
    "explore/atlas.qmd": "atlas-map",
    "principles.qmd": "principles-chart",
    "explore/numerology.qmd": "numerology-chart",
    "explore/workbench.qmd": "wb-overlay",
    "explore/atlas-combinations.qmd": "atlas-volcano",
}
BANNER = (
    "You are tuning on the exploration period only; confirmation runs once, "
    "by a maintainer, on data this page does not contain."
)


def quarto():
    """Return the parsed _quarto.yml."""
    return yaml.safe_load((REPO / "_quarto.yml").read_text(encoding="utf-8"))


def test_navbar_order_and_menus():
    """Navbar order and menus."""
    left = quarto()["website"]["navbar"]["left"]
    assert [i["text"] for i in left] == [
        "Home",
        "Methods",
        "Principles",
        "Data",
        "Studies",
        "Explore",
        "Contribute",
        "Corrections",
    ]
    studies = {i["text"] for i in left[4]["menu"]}
    assert "Mundane atlas" in studies
    explore = [i["href"] for i in left[5]["menu"]]
    for page in EXPLORERS:
        assert f"site/{page}" in explore
    right = quarto()["website"]["navbar"]["right"]
    assert right[0]["icon"] == "github"


def test_project_settings():
    """Project settings."""
    cfg = quarto()
    assert "site/data/**" in cfg["project"]["resources"]
    assert "site/explore/*.qmd" in cfg["project"]["render"]
    assert cfg["crossref"]["title-delim"] == ":"
    theme = cfg["format"]["html"]["theme"]
    assert list(theme) == ["dark", "light"]  # dark first: the default
    for variant in theme.values():
        for f in variant[1:]:
            assert (REPO / f).exists()


@pytest.mark.parametrize("page,chart_id", EXPLORERS.items())
def test_explorer_page_contract(page, chart_id):
    """Explorer page contract."""
    text = (SITE / page).read_text(encoding="utf-8")
    assert "**How to read this.**" in text
    assert "provenance(" in text
    assert f'id="{chart_id}"' in text
    assert "```{python" not in text  # no engine needed at render
    assert re.search(
        r"Inputs\.radio\(\[[^\]]*\]|Inputs\.radio\(new Map", text
    )  # a toggle
    for name in re.findall(r'FileAttachment\("([^"]+)"\)', text):
        assert (SITE / page).parent.joinpath(name).resolve().exists(), name
    for inc in re.findall(r"\{\{< include ([^ ]+) >\}\}", text):
        assert (SITE / page).parent.joinpath(inc).resolve().exists(), inc


@pytest.mark.parametrize("page", [p for p in EXPLORERS if p != "principles.qmd"])
def test_static_twin_is_named_or_its_absence_stated(page):
    """Static twin is named or its absence stated."""
    text = (SITE / page).read_text(encoding="utf-8")
    twins = re.findall(r'"(studies/[^"]+\.png)"', text)
    twins += re.findall(r"`(studies/\$\{metal\}_market/artifacts/[^`]+\.png)`", text)
    if twins:
        for t in twins:
            for metal in ("gold", "silver"):
                assert (REPO / t.replace("${metal}", metal)).exists(), t
    else:
        assert "twin: []" in text and "note:" in text


@pytest.mark.parametrize(
    "path", sorted((SITE / "components").glob("*.ojs")), ids=lambda p: p.name
)
def test_components_stay_under_300_lines(path):
    """Components stay under 300 lines."""
    assert len(path.read_text(encoding="utf-8").splitlines()) < 300


def scss_list(text, name):
    """Return the hex values of an SCSS list variable."""
    m = re.search(rf"\${name}: \(([^)]*)\)", text)
    return [h.strip() for h in m.group(1).split(",")]


def test_palette_in_components_matches_the_theme():
    """Palette in components matches the theme."""
    ojs = (SITE / "components" / "theme.ojs").read_text(encoding="utf-8")
    for mode in ("light", "dark"):
        scss = (SITE / "theme" / f"astrofusion-{mode}.scss").read_text(encoding="utf-8")
        block = re.search(rf"{mode}: \{{(.*?)\n  \}}", ojs, re.S).group(1)
        series = re.search(r"series: \[([^\]]*)\]", block).group(1)
        assert [s.strip().strip('"') for s in series.split(",")] == scss_list(
            scss, "af-series"
        )
        seq = re.search(r"seq: \[([^\]]*)\]", block).group(1)
        assert [s.strip().strip('"') for s in seq.split(",")] == scss_list(
            scss, "af-seq"
        )


def test_theme_credits_the_token_source():
    """Theme credits the token source."""
    for mode in ("light", "dark"):
        scss = (SITE / "theme" / f"astrofusion-{mode}.scss").read_text(encoding="utf-8")
        assert "af-design/styles/tokens.css" in scss
        assert "fonts.googleapis.com" in scss
        assert "#0f0c29" in scss  # cosmic-900 token


def test_home_keeps_vision_first_and_has_the_status_strip():
    """Home keeps vision first and has the status strip."""
    text = (SITE / "index.qmd").read_text(encoding="utf-8")
    order = [
        "## What this project is",
        "## How to read a comparison here",
        "## The principles in use",
        "## Studies and their status",
    ]
    positions = [text.index(h) for h in order]
    assert positions == sorted(positions)
    assert 'id="study-status"' in text
    assert "| Study | What it compares | Status |" not in text
    for word in ("Null:", "disproved", "debunked", "proves"):
        assert word not in text


def test_methods_keeps_working_expectations():
    """Methods keeps working expectations."""
    text = (SITE / "methods.qmd").read_text(encoding="utf-8")
    assert "## Working expectations" in text
    assert "The project owner's current expectation, recorded as a hypothesis" in text


def test_status_strip_has_no_verdict_language():
    """Status strip has no verdict language."""
    import json

    doc = json.loads((SITE / "data" / "results.json").read_text(encoding="utf-8"))
    for s in doc["status"]:
        assert s["link"]
        for word in ("null", "disproved", "debunked", "works", "fails"):
            assert word not in s["headline"].lower()


def test_workbench_states_the_explore_only_rule_and_reads_no_confirm_data():
    """Workbench states the explore-only rule and reads no confirm data."""
    text = (SITE / "explore" / "workbench.qmd").read_text(encoding="utf-8")
    assert BANNER in " ".join(text.split())
    assert "workbench-core.mjs" in text
    assert (SITE / "components" / "workbench-core.mjs").exists()
    for name in re.findall(r'FileAttachment\("([^"]+)"\)', text):
        assert name.endswith(("rules.json",)) or "workbench_" in name, name
    assert "propose-rule.yml" in text and 'id="wb-submit"' in text
    assert (REPO / ".github" / "ISSUE_TEMPLATE" / "propose-rule.yml").exists()


def test_workbench_issue_fields_exist_in_the_template():
    """Every field the workbench prefills is an id in the issue template."""
    form = yaml.safe_load(
        (REPO / ".github" / "ISSUE_TEMPLATE" / "propose-rule.yml").read_text()
    )
    ids = {b.get("id") for b in form["body"]}
    text = (SITE / "explore" / "workbench.qmd").read_text(encoding="utf-8")
    block = text.split("const q = {", 1)[1].split("};", 1)[0]
    keys = set(re.findall(r"^\s*(\w+):", block, re.M)) - {"template", "title"}
    assert keys and keys <= ids, keys - ids


def test_home_has_the_rule_validation_strip():
    """Home has the confirmed / tuned / unvalidated strip."""
    text = (SITE / "index.qmd").read_text(encoding="utf-8")
    assert 'id="rule-status"' in text
    for word in ("confirmed", "tuned", "unvalidated"):
        assert f'["{word}"' in text


def test_principles_shows_version_validation_tuning_and_reviews():
    """Principles shows version, validation stamp, tuning log and reviews."""
    text = (SITE / "principles.qmd").read_text(encoding="utf-8")
    for needle in ("version", "stamp(", "Tuning log", "Reviews", "viewof validations"):
        assert needle in text, needle


def test_atlas_page_marks_a_fixture():
    """The atlas page flags fixture data in a banner."""
    text = (SITE / "explore" / "atlas-combinations.qmd").read_text(encoding="utf-8")
    assert "atlas.fixture" in text and "Illustrative fixture, not results" in text
