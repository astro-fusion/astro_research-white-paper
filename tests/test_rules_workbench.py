"""astro-rules fit, confirm, dose and review (ADR-003), on shortened periods."""

import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

from vedic_astrology_core.rules import default_rules_dir, load_rules
from vedic_astrology_core.rules import studyadapter as sa
from vedic_astrology_core.rules.cli import main
from vedic_astrology_core.rules.yamlio import edit_rule_file

RULE = "seismic.mangal_ketu_primary"
EXPLORE = sa.Period(
    "explore",
    pd.Timestamp("2000-01-01", tz="UTC"),
    pd.Timestamp("2006-01-01", tz="UTC"),
)
CONFIRM = sa.Period(
    "confirm",
    pd.Timestamp("2011-01-01", tz="UTC"),
    pd.Timestamp("2017-01-01", tz="UTC"),
)


@pytest.fixture
def short_periods(monkeypatch):
    """Six-year explore and confirm periods keep the tests quick."""
    monkeypatch.setattr(sa, "split_periods", lambda hyp: (EXPLORE, CONFIRM))


@pytest.fixture
def rules_dir(tmp_path):
    """Return a writable copy of the seismic rules."""
    target = tmp_path / "seismic"
    shutil.copytree(default_rules_dir() / "seismic", target)

    def fresh(doc):
        """Return the rule to an untuned, unvalidated v2."""
        doc["version"] = 2
        doc["params"]["orb"]["value"] = 13
        doc["validation"] = {"status": "unvalidated"}
        for key in ("tuning_log", "validation_history", "review"):
            if key in doc:
                del doc[key]

    edit_rule_file(target / "mangal_ketu_primary.yaml", fresh)
    return target


@pytest.fixture
def figures(tmp_path, monkeypatch):
    """Send specification curves to a temporary directory."""
    from vedic_astrology_core.rules import workbench

    real = workbench.fit

    def fit(*args, **kwargs):
        kwargs.setdefault("figure_dir", tmp_path / "fig")
        return real(*args, **kwargs)

    monkeypatch.setattr(workbench, "fit", fit)
    return tmp_path / "fig"


def run(capsys, *argv):
    """Run the CLI; return (exit code, stdout, stderr)."""
    code = main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


def read(path: Path):
    """Return the parsed YAML of a rule file."""
    return yaml.safe_load(path.read_text())


def test_fit_tunes_on_explore_and_logs(capsys, short_periods, rules_dir, figures):
    """Fit prints the top cells, writes the curve, updates params, appends a log."""
    path = rules_dir / "mangal_ketu_primary.yaml"
    before = path.read_text()
    code, out, err = run(
        capsys,
        "fit",
        RULE,
        "--study",
        "earthquake",
        "--by",
        "@t",
        "--draws",
        "99",
        "--rules-dir",
        str(rules_dir),
    )
    assert code == 0, err
    assert "EXPLORE 2000-01-01 to 2005-12-31 only" in out
    assert "top 5 cells" in out and "orb=" in out
    data = read(path)
    entry = data["tuning_log"][0]
    assert entry["by"] == "@t" and entry["study"] == "earthquake"
    assert entry["version"] == 2 and entry["explore"]["n_cells"] == 18
    assert entry["explore"]["period"] == ["2000-01-01", "2005-12-31"]
    assert data["params"]["orb"]["value"] == entry["chosen"]["orb"]
    assert (figures / f"speccurve_{RULE}_v2.png").exists()
    assert path.read_text().startswith(before.splitlines()[0])  # comment kept
    loaded, problems = load_rules([rules_dir])
    assert not problems, problems


def test_fit_never_reads_the_confirm_period(
    capsys, short_periods, rules_dir, figures, monkeypatch
):
    """Fit and dose run with every confirm accessor booby-trapped."""

    def trap(*_a, **_k):
        raise AssertionError("confirm data touched")

    for name in ("confirm_grid", "confirm_events", "confirm_indicator"):
        monkeypatch.setattr(sa.StudyAdapter, name, trap)
    code, _, err = run(
        capsys,
        "fit",
        RULE,
        "--study",
        "earthquake",
        "--by",
        "@t",
        "--draws",
        "49",
        "--dry-run",
        "--rules-dir",
        str(rules_dir),
    )
    assert code == 0, err


def test_confirm_runs_once_per_version(capsys, short_periods, rules_dir, figures):
    """Confirm stamps validation; a second confirm on the version is refused."""
    path = rules_dir / "mangal_ketu_primary.yaml"
    code, out, err = run(
        capsys, "confirm", RULE, "--study", "earthquake", "--rules-dir", str(rules_dir)
    )
    assert code == 0, err
    assert "one frozen run on CONFIRM 2011-01-01 to 2016-12-31" in out
    stamp = read(path)["validation"]
    assert stamp["status"] in ("confirmed", "not_confirmed")
    assert stamp["version"] == 2 and stamp["study"] == "earthquake"
    assert stamp["confirm"]["period"] == ["2011-01-01", "2016-12-31"]
    assert stamp["confirm"]["family_size"] == 1
    assert stamp["commit"]
    text = path.read_text()
    code, _, err = run(
        capsys, "confirm", RULE, "--study", "earthquake", "--rules-dir", str(rules_dir)
    )
    assert code == 2
    assert "already confirmed" in err and "new version" in err
    assert path.read_text() == text

    code, _, err = run(
        capsys,
        "fit",
        RULE,
        "--study",
        "earthquake",
        "--by",
        "@t",
        "--draws",
        "49",
        "--rules-dir",
        str(rules_dir),
    )
    assert code == 2 and "--new-version" in err
    code, out, err = run(
        capsys,
        "fit",
        RULE,
        "--study",
        "earthquake",
        "--by",
        "@t",
        "--draws",
        "49",
        "--new-version",
        "--rules-dir",
        str(rules_dir),
    )
    assert code == 0, err
    data = read(path)
    assert data["version"] == 3
    assert data["validation"] == {"status": "unvalidated"}
    assert data["validation_history"][0]["version"] == 2
    assert data["tuning_log"][-1]["version"] == 3
    loaded, problems = load_rules([rules_dir])
    assert not problems, problems


def test_review_appends(capsys, rules_dir):
    """Review adds an entry with the version and keeps earlier ones."""
    path = rules_dir / "mangal_ketu_primary.yaml"
    for verdict in ("faithful", "not_faithful"):
        code, out, err = run(
            capsys,
            "review",
            RULE,
            "--by",
            "@a",
            "--verdict",
            verdict,
            "--note",
            "checked the orb",
            "--rules-dir",
            str(rules_dir),
        )
        assert code == 0, err
    reviews = read(path)["review"]
    assert [r["verdict"] for r in reviews] == ["faithful", "not_faithful"]
    assert reviews[0]["version"] == 2
    assert not load_rules([rules_dir])[1]


def test_dose_needs_a_strength_block(capsys, short_periods, rules_dir):
    """A binary rule has no dose."""
    code, _, err = run(
        capsys, "dose", RULE, "--study", "earthquake", "--rules-dir", str(rules_dir)
    )
    assert code == 2 and "no strength block" in err


def test_dose_reports_quintiles_and_trend(capsys, short_periods, rules_dir):
    """A graded rule: five quintiles, rate ratios, and three trend p-values."""
    path = rules_dir / "mangal_ketu_primary.yaml"
    text = path.read_text().replace(
        "validation:",
        "strength:\n  combine: product\n  terms:\n"
        "  - orb_closeness: {planets: [Mars, Ketu], orb: $orb}\nvalidation:",
        1,
    )
    path.write_text(text)
    code, out, err = run(
        capsys,
        "dose",
        RULE,
        "--study",
        "earthquake",
        "--draws",
        "49",
        "--rules-dir",
        str(rules_dir),
    )
    assert code == 0, err
    assert "quintile" in out and "RR vs silent" in out
    assert "cochran_armitage" in out and "Kendall tau-b" in out
    assert "circular-shift p" in out
    assert sum(1 for line in out.splitlines() if line.strip()[:1].isdigit()) == 5


def test_unknown_rule_and_study(capsys, rules_dir):
    """Usage errors exit 2 with a suggestion."""
    code, _, err = run(
        capsys,
        "fit",
        "seismic.mangal_ketu_primry",
        "--study",
        "earthquake",
        "--by",
        "@t",
        "--rules-dir",
        str(rules_dir),
    )
    assert code == 2 and "Did you mean" in err
    code, _, err = run(
        capsys, "confirm", RULE, "--study", "tsunami", "--rules-dir", str(rules_dir)
    )
    assert code == 2 and "earthquake" in err
