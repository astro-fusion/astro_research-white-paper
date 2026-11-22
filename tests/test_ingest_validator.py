"""Tests for tools/ingest (ADR-004 WP-10). No network: openers and runners are injected."""

import json
import shutil
import urllib.error
from datetime import date
from pathlib import Path

import pytest

from tools.ingest import contracts, urlcheck, validate

FIX = Path(__file__).parent / "fixtures" / "ingest"
TODAY = date(2026, 11, 22)


class Resp:
    def __init__(self, status=200, body=b""):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def close(self):
        pass


def opener_ok(req, timeout):
    return Resp(200)


def make_opener(dead=(), archive=None, seen=None):
    def opener(req, timeout):
        if seen is not None:
            seen.append((req.full_url, dict(req.header_items())))
        if "archive.org/wait" in req.full_url:
            if archive:
                return Resp(200, json.dumps({"archived_snapshots": {"closest": {
                    "available": True, "url": archive}}}).encode())
            return Resp(200, b"{}")
        if any(d in req.full_url for d in dead):
            raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)
        return Resp(200)
    return opener


def runner_ok(path):
    return 0, "1 rules valid"


def runner_fail(path):
    return 1, "schema problem"


def stage(tmp_path, *names):
    d = tmp_path / "incoming" / "topic"
    d.mkdir(parents=True)
    for n in names:
        dest = d / Path(n).name
        shutil.copy(FIX / n, dest)
    return d


def run(d, opener=opener_ok, runner=runner_ok, urls=True):
    return validate.validate_dir(d, check_urls=urls, opener=opener, rules_runner=runner,
                                 known_ids=set(), today=TODAY)


def test_contract_lookup_and_mapping():
    assert contracts.contract_for("literature_gold.csv").name == "literature"
    assert contracts.contract_for("drivers.csv").name == "sources"
    assert contracts.contract_for("mystery.csv") is None
    m = contracts.suggest_mapping(["dataset", "frequency"], ["dataset", "freq"])
    assert m == {"freq": "frequency"}


def test_column_mismatch_is_reported_never_guessed(tmp_path):
    d = stage(tmp_path, "cols/sources_gold.csv")
    rep = run(d, urls=False)
    f = rep["files"]["sources_gold.csv"]
    assert f["status"] == "needs_mapping" and f["rows"] == []
    assert f["issues"][0]["suggested_mapping"]["freq"] == "frequency"
    assert "frequency" in (d / "sources_gold.csv").read_text()  # file untouched
    assert (d / "VERIFICATION.json").exists()


def test_value_dump_rejected(tmp_path):
    d = stage(tmp_path, "dump/prices.csv")
    f = run(d, urls=False)["files"]["prices.csv"]
    assert f["status"] == "rejected" and f["issues"][0]["code"] == "value_dump"


def test_row_rejections(tmp_path):
    d = stage(tmp_path, "bad/gold_forecasts_exante.csv")
    rows = run(d, urls=False)["files"]["gold_forecasts_exante.csv"]["rows"]
    reasons = [" ".join(r["reasons"]) for r in rows]
    assert "on or after the target window" in reasons[0]
    assert "no URL, DOI" in reasons[1]
    assert "unparsable date" in reasons[2]
    assert "is before target_start" in reasons[3]


def test_duplicate_ids(tmp_path):
    d = stage(tmp_path, "episodes/gold_episodes.csv")
    rows = run(d, urls=False)["files"]["gold_episodes.csv"]["rows"]
    assert not rows[0]["reasons"]
    assert any("duplicate episode_id" in r for r in rows[1]["reasons"])


def test_url_checks_use_generic_client_and_archive(tmp_path):
    seen = []
    d = stage(tmp_path, "good/gold_forecasts_exante.csv")
    op = make_opener(dead=("example.org/b",), archive="https://web.archive.org/web/2012/x", seen=seen)
    rows = run(d, op)["files"]["gold_forecasts_exante.csv"]["rows"]
    assert rows[0]["url_status"] == "ok" and rows[1]["url_status"] == "http_404"
    assert rows[1]["archive_url"].startswith("https://web.archive.org")
    assert seen and all(h["User-agent"] == urlcheck.USER_AGENT for _, h in seen)
    assert not any("astro" in u.lower() or "bishal" in str(h).lower() for u, h in seen)


def test_dead_link_without_archive_rejected(tmp_path):
    d = stage(tmp_path, "good/gold_forecasts_exante.csv")
    rows = run(d, make_opener(dead=("example.org/b",)))["files"]["gold_forecasts_exante.csv"]["rows"]
    assert any("dead link" in r for r in rows[1]["reasons"])
    # live link but no archive capture: ex-ante date unproven
    assert any("archive capture" in r for r in rows[0]["reasons"])


def test_rule_yaml_checks(tmp_path):
    d = stage(tmp_path, "rules/good_rule.yaml", "rules/prose_rule.yaml")
    rules = run(d, runner=runner_ok, urls=False)["rules"]
    assert rules["good_rule.yaml"]["status"] == "ok"
    prose = rules["prose_rule.yaml"]
    assert prose["status"] == "fixable"
    msgs = " ".join(i["message"] for i in prose["issues"])
    assert "tier" in msgs and "ex_ante" in msgs and "prose" in msgs
    failing = run(d, runner=runner_fail, urls=False)["rules"]
    assert failing["good_rule.yaml"]["status"] == "fail"
    assert failing["prose_rule.yaml"]["status"] == "fixable"  # marked needs_predicates


def test_rule_duplicate_id(tmp_path):
    d = stage(tmp_path, "rules/good_rule.yaml")
    r = validate.check_rule_file(d / "good_rule.yaml", runner_ok, {"flood.test.good"})
    assert r["status"] == "fail"


def test_promote_requires_accepted_and_checked_by(tmp_path):
    d = stage(tmp_path, "good/gold_forecasts_exante.csv")
    op = make_opener(archive="https://web.archive.org/web/2010/x")
    run(d, op)
    vp = d / "VERIFICATION.json"
    rep = json.loads(vp.read_text())
    rows = rep["files"]["gold_forecasts_exante.csv"]["rows"]
    rows[0].update(verdict="accepted", checked_by="Reviewer", checked_on="2026-11-22")
    rows[1].update(verdict="accepted")  # no checked_by
    vp.write_text(json.dumps(rep))
    repo = tmp_path / "repo"
    out = validate.promote(d, repo)
    assert out["promoted"] == {"gold_forecasts_exante.csv": 1}
    promoted = (repo / "data" / "registry" / "topic" / "gold_forecasts_exante.csv").read_text()
    assert "Reviewer" in promoted and "B Two" not in promoted
    for col in contracts.PROMOTED_COLUMNS:
        assert col in promoted.splitlines()[0]
    # verdicts survive a re-validation
    again = run(d, op)["files"]["gold_forecasts_exante.csv"]["rows"]
    assert again[0]["checked_by"] == "Reviewer"


def test_promote_skips_machine_rejected_and_changed_files(tmp_path):
    d = stage(tmp_path, "bad/gold_forecasts_exante.csv")
    run(d, urls=False)
    vp = d / "VERIFICATION.json"
    rep = json.loads(vp.read_text())
    for r in rep["files"]["gold_forecasts_exante.csv"]["rows"]:
        r.update(verdict="accepted", checked_by="X")
    vp.write_text(json.dumps(rep))
    assert validate.promote(d, tmp_path / "repo")["promoted"] == {}
    (d / "gold_forecasts_exante.csv").write_text("changed")
    assert "changed since validation" in validate.promote(d, tmp_path / "repo")["skipped_files"][
        "gold_forecasts_exante.csv"]


def test_misplaced_and_relocate(tmp_path):
    repo = tmp_path
    (repo / "flood_data.csv").write_text("a,b\n1,2\n")
    (repo / "studies" / "monsoon" / "rules").mkdir(parents=True)
    (repo / "studies" / "monsoon" / "rules" / "r.yaml").write_text("id: x\n")
    found = validate.find_misplaced(repo, tracked=lambda r, p: False)
    assert {f["path"] for f in found} == {"flood_data.csv", "studies/monsoon/rules/r.yaml"}
    assert found[0]["suggested_topic"] in ("flood", None)
    dest = validate.relocate(repo / "flood_data.csv", "flood", repo)
    assert dest == repo / "research" / "incoming" / "flood" / "flood_data.csv" and dest.exists()
    assert not (repo / "flood_data.csv").exists()
    dest2 = validate.relocate(repo / "studies/monsoon/rules/r.yaml", "flood", repo)
    assert dest2.parent.name == "rules"
    (repo / "flood_data.csv").write_text("again")
    with pytest.raises(FileExistsError):
        validate.relocate(repo / "flood_data.csv", "flood", repo)
