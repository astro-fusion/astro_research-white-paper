"""Tests for the mundane CLI (ADR-006 WP-56). Fast: no daily grid, no full report."""

import json

import pytest

from vedic_astrology_core.mundane import cli
from vedic_astrology_core.mundane import registry as reg


def run(capsys, *argv):
    rc = cli.main(list(argv))
    cap = capsys.readouterr()
    return rc, cap.out, cap.err


def test_validate_ok(capsys):
    rc, out, err = run(capsys, "validate")
    assert rc == 0, err
    assert "primary chart: in-1947-midnight (grade C)" in out
    assert "18 omnibus tests" in out
    assert "explore-period events in the counts: 3" in out


def test_catalogue_list_and_show(capsys):
    rc, out, _ = run(capsys, "catalogue", "list")
    assert rc == 0 and "dasha.vimshottari" in out
    rc, out, _ = run(capsys, "catalogue", "show", "dasha.vimshottari")
    assert rc == 0 and "missing for the next level" in out and "status unverified" in out
    rc, _, err = run(capsys, "catalogue", "show", "nope.nothing")
    assert rc == 2 and "no catalogue entry" in err


def test_chart_table_marks_unstable(capsys):
    rc, out, _ = run(capsys, "chart", "in-1947-midnight")
    assert rc == 0 and "Lagna" in out and "unstable" in out
    rc, _, err = run(capsys, "chart", "zz-none")
    assert rc == 2 and "unknown chart" in err


def test_burden_counts_and_over_budget(capsys, tmp_path):
    rc, out, _ = run(capsys, "burden", "--out", str(tmp_path / "burden.json"))
    assert rc == 0 and "18 omnibus tests" in out
    assert json.loads((tmp_path / "burden.json").read_text())["plan_counts"]["omnibus_tests"] == 18
    import yaml
    data = yaml.safe_load(cli.bur.PLAN_FILE.read_text())
    data["budgets"]["max_omnibus_tests_first_slice"] = 10
    bad = tmp_path / "plan.yaml"
    bad.write_text(yaml.safe_dump(data))
    rc, _, err = run(capsys, "--plan", str(bad), "burden")
    assert rc == 1 and "over budget" in err


def test_confirm_report_refused(capsys):
    rc, _, err = run(capsys, "report", "--period", "confirm")
    assert rc == 2 and "not available until WP-63" in err
    rc, _, err = run(capsys, "controls", "--period", "confirm")
    assert rc == 2 and "not available until WP-63" in err


def test_controls_written_and_reproducible(capsys, tmp_path):
    rc, out, _ = run(capsys, "controls", "--out", str(tmp_path / "a"))
    assert rc == 0 and "3 events" in out
    rc, _, _ = run(capsys, "controls", "--out", str(tmp_path / "b"))
    a = sorted((tmp_path / "a").glob("controls_*.csv"))[0]
    b = sorted((tmp_path / "b").glob("controls_*.csv"))[0]
    assert a.read_bytes() == b.read_bytes()
    assert a.with_suffix(".manifest.json").exists()


def test_casefile_writes_json_and_html(capsys, tmp_path):
    rc, out, err = run(capsys, "casefile", "usgs:usp0004y1r", "--format", "json,html", "--out", str(tmp_path))
    assert rc == 0, err
    js = list(tmp_path.glob("*.json"))
    assert len(js) == 1 and list(tmp_path.glob("*.html"))
    assert json.loads(js[0].read_text())["schema"] == "casefile/1"
    rc, _, err = run(capsys, "casefile", "usgs:nope")
    assert rc == 2 and "unknown event" in err


def test_event_selection():
    plan = cli.bur.load_plan()
    events, charts = reg.load_events(), reg.load_charts()
    assert len(cli.slice_events(plan, events)) == 3
    ids = [e.event_id for e in cli.casefile_events(plan, events)]
    assert len(ids) == 5 and all(i.startswith("usgs:") for i in ids)
    (ev, ch), = cli.case_file_only_pairs(plan, events, charts)
    assert ev.event_id == "usgs:us20002926" and ch.chart_id == "np-2008-republic"


def test_primary_mismatch_fails():
    plan = cli.bur.load_plan()
    charts = [c for c in reg.load_charts() if c.chart_id != "in-1947-midnight"]
    with pytest.raises(cli.CliError):
        cli.primary_for(plan, charts)
