"""ADR-008 WP-96: report gate and summary (section 9.3; rows S-10, A-06, F-06, O-01, O-02)."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

from vedic_astrology_core.paperkit import Results
from vedic_astrology_core.stats.exclusion import LimitRecord
from vedic_astrology_core.validity import report as RP
from vedic_astrology_core.validity import sentences as S
from vedic_astrology_core.validity import verdict as V
from vedic_astrology_core.validity.family import Eligibility

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_paper_keys", ROOT / "tools" / "check_paper_keys.py")
cpk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpk)

ELIG = Eligibility(test_id="t", vintage_id="v1", row="before_close_unseen", allow_s=True, allow_c=True,
                   allow_e=True, numbers="confirmatory", a_test=0.002, batch=1)
GOOD_ROB = {"R1": True, "R2": True, "R3": True, "R4": True}


def lim(v):
    return LimitRecord(alpha=0.05, value=v, unbounded=v is None, reason=None if v else "too_few_informative_blocks",
                       scale="difference", informative=12, required_informative=5, k_eff=12.0)


def make_verdict(level=2, code="S", **over):
    kw = dict(level=level, eligibility=ELIG, side="greater", can_support=True, can_limit=True,
              p_sup=0.0001 if code == "S" else 0.5, p_opp=0.0001 if code == "C" else 0.5,
              p_ex=0.0001 if code == "E" else 0.5, explore_same_sign=True, robustness=GOOD_ROB,
              source_published="1900", confirm_start="1999-01-01", sesoi=0.1, informative_at_sesoi=12,
              k_eff=12.0, estimate_magnitude=0.3, x95=lim(0.05), x_strict=lim(0.08), n_blocks=12,
              support_underpowered=False, attested_after=None)
    if code == "U":
        kw.update(can_support=False, can_limit=False, untestable_reason="too_few_episodes")
    kw.update(over)
    return V.verdict(V.VerdictInput(**kw)).to_dict()


def rec(i, level=2, code="S", entry="text", name=None, market="Frankfurt fixing", currency="DEM", **over):
    return {
        "id": f"p_{i:03d}", "name": name or f"Moon in house {i}", "domain": "gold", "level": level,
        "entry": entry, "outcome": {"market": market, "currency": currency}, "justified": True,
        "verdict": make_verdict(level, code, **over),
        "estimate": {"with_baselines": 0.31, "without_baselines": 0.12},
    }


def results_dict(records, domains=6, certificate=None):
    d = {
        "schema": RP.REPORT_SCHEMA, "provisional": False, "git": {"commit": "c0ffee", "dirty": False},
        "plan": {"sha256": "aa" * 32}, "data": {"sha256": "bb" * 32},
        "records": copy.deepcopy(records), "family": {"domains": domains},
        "sampling_frame": {"not_encodable": 4, "not_sourced": 2, "untestable": 3},
    }
    if certificate is not None:
        d["certificate"] = certificate
    return d


CERT = {"cases": [{"case_id": "X9", "cell": "x2_K12", "rate": 0.37}, {"case_id": "X1", "cell": "a", "rate": 0.01}]}
MIXED = [rec(1, 2, "S"), rec(2, 4, "S"), rec(3, 2, "N"), rec(4, 5, "E"), rec(5, 3, "U"), rec(6, 4, "C")]


@pytest.fixture
def built(tmp_path):
    rp = tmp_path / "results.json"
    rp.write_text(json.dumps(results_dict(MIXED, certificate=CERT)))
    out = tmp_path / "pages"
    manifest = RP.write_report(rp, out)
    return rp, out, manifest


def res_of(records, **kw):
    return Results(results_dict(records, **kw))


# ---------------------------------------------------------------- gate
def test_clean_build_passes_the_gate(built):
    rp, out, manifest = built
    assert RP.check_report(rp, out) == []
    assert (out / "summary.md").exists() and (out / "methods.md").exists()
    assert set(manifest["pages"]) == {f"card/p_00{i}.md" for i in range(1, 7)} | {"summary.md", "methods.md"}


def test_edited_results_file_fails(built):
    rp, out, _ = built
    d = json.loads(rp.read_text())
    d["records"][0]["verdict"]["code"] = "N"
    rp.write_text(json.dumps(d))
    problems = RP.check_report(rp, out)
    assert any(p.startswith("HASH results file") for p in problems)


def test_edited_results_with_new_manifest_still_fails_render(built):
    rp, out, manifest = built
    d = json.loads(rp.read_text())
    d["records"][0]["name"] = "Moon in house 99"
    rp.write_text(json.dumps(d))
    manifest["results"]["sha256"] = hashlib.sha256(rp.read_bytes()).hexdigest()
    problems = RP.check_report(rp, out, manifest=manifest)
    assert any(p.startswith("RENDER page card/p_001.md differs") for p in problems)


def test_page_with_one_extra_word_fails(built):
    rp, out, _ = built
    page = out / "card" / "p_001.md"
    page.write_text(page.read_text().replace("Contradicted", "Contradicted").replace(
        "Not supported", "Not supported really"))
    page = out / "summary.md"
    page.write_text(page.read_text() + "\nAstrology is debunked.\n")
    problems = RP.check_report(rp, out)
    assert any(p.startswith("RENDER page summary.md differs") for p in problems)
    assert any("SENTENCE summary.md" in p and "debunked" in p for p in problems)


def test_extra_word_in_a_card_fails(built):
    rp, out, _ = built
    page = out / "card" / "p_003.md"
    page.write_text(page.read_text().replace("No effect was shown.", "No effect was clearly shown."))
    problems = RP.check_report(rp, out)
    assert any("RENDER page card/p_003.md differs" in p for p in problems)
    assert any("SENTENCE card/p_003.md" in p for p in problems)


def test_extra_and_missing_pages_fail(built):
    rp, out, _ = built
    (out / "card" / "p_002.md").unlink()
    (out / "card" / "stray.md").write_text("Astrology fails.\n")
    problems = RP.check_report(rp, out)
    assert any("p_002.md is missing" in p for p in problems)
    assert any("stray.md is not produced" in p for p in problems)
    assert any("SENTENCE card/stray.md" in p for p in problems)


@pytest.mark.parametrize("phrase", ["debunked", "astrology fails", "proven", "confirmed", "no evidence for astrology"])
def test_paraphrases_fail_the_allow_list(phrase):
    assert not RP.allowed_line(f"The principle is {phrase}.")
    assert not RP.allowed_line(phrase.capitalize())


def test_provisional_or_dirty_results_stop_the_build(tmp_path):
    for over in ({"provisional": True}, {"git": {"commit": "c0ffee", "dirty": True}}, {"git": {"dirty": False}}):
        d = results_dict(MIXED)
        d.update(over)
        rp = tmp_path / "r.json"
        rp.write_text(json.dumps(d))
        with pytest.raises(RP.ReportError):
            RP.write_report(rp, tmp_path / "o")


def test_missing_key_stops_the_build():
    d = results_dict(MIXED)
    del d["family"]
    with pytest.raises(Exception):
        RP.render_summary(Results(d))
    d = results_dict(MIXED)
    d["records"][0]["estimate"]["with_baselines"] = None
    with pytest.raises(ValueError):
        RP.render_card(Results(d), 0)


def test_unsafe_page_id_refused():
    r = rec(1)
    r["id"] = "../evil"
    with pytest.raises(RP.ReportError):
        RP.render_pages(res_of([r]))


def test_verdict_line_outside_allow_list_refused():
    r = rec(1)
    r["verdict"]["lines"][3] = "Astrology is proven."
    with pytest.raises(RP.ReportError):
        RP.render_card(res_of([r]), 0)


def test_words_must_match_code_and_level():
    r = rec(1, level=2, code="S")
    r["verdict"]["lines"][0] = S.verdict_words("S", 4)  # L4 words on an L2 card
    with pytest.raises(RP.ReportError):
        RP.render_card(res_of([r]), 0)


def test_changelog_chain_and_manifest(tmp_path):
    rp = tmp_path / "results.json"
    rp.write_text(json.dumps(results_dict(MIXED)))
    log = tmp_path / "changelog.jsonl"
    l1 = json.dumps({"prev_sha256": None, "entry": "a"}, sort_keys=True)
    l2 = json.dumps({"prev_sha256": hashlib.sha256(l1.encode()).hexdigest(), "entry": "b"}, sort_keys=True)
    log.write_text(l1 + "\n" + l2 + "\n")
    out = tmp_path / "pages"
    manifest = RP.write_report(rp, out, changelog=log)
    assert RP.check_report(rp, out, changelog=log) == []
    log.write_text(l1.replace('"a"', '"x"') + "\n" + l2 + "\n")
    assert any("changelog chain broken" in p for p in RP.check_report(rp, out, changelog=log))
    assert manifest["changelog_head_sha256"] == hashlib.sha256(l2.encode()).hexdigest()


# ---------------------------------------------------------------- S-10
def test_union_bound_sentence_and_number_from_run_set():
    for d in (1, 6, 7):
        text = RP.render_summary(res_of(MIXED, domains=d))
        assert f"Across {d} domains and three verdict types: at most {d * 3 * 0.05:.2f} in total" in text
        assert "Chance of at least one false Supported in a domain: at most 5% over all time." in text
    # It is the first paragraph after the title.
    paras = text.split("\n\n")
    assert paras[1].startswith("Chance of at least one false Supported")


# ---------------------------------------------------------------- A-06
def test_card_names_market_and_currency_and_verdict_lines_have_no_market_word():
    r = rec(1, name="Moon in house 1")
    card = RP.render_card(res_of([r]), 0)
    assert "Tested on the Frankfurt fixing in DEM." in card
    for ln in r["verdict"]["lines"]:
        assert not re.search(r"\bgold\b", ln, re.I)
        assert "Frankfurt" not in ln and "DEM" not in ln
    for code in "SCENU":
        for lv in (2, 4):
            for ln in make_verdict(lv, code)["lines"]:
                assert not re.search(r"\bgold\b|\bsilver\b", ln, re.I)
    assert not RP.allowed_line("A null on gold.")
    assert not RP.allowed_line("Tested on gold.")
    assert not RP.allowed_line("Tested on the gold market.")


def test_card_without_currency_is_refused():
    r = rec(1, currency="")
    with pytest.raises(Exception):
        RP.render_card(res_of([r]), 0)


# ---------------------------------------------------------------- F-06
def test_project_extension_only_in_its_own_table():
    recs = [rec(1, 2, "N"), rec(2, 2, "N", project_extension=True, name="Mars in house 2")]
    text = RP.render_summary(res_of(recs))
    head, ext = text.split("## Project extensions")
    assert "Mars in house 2" in ext
    assert "| Encoding not supported, not excluded | 1 |" in head  # the extension is not counted there
    assert RP.render_card(res_of(recs), 1).count("The outcome or direction is a project extension") == 1


# ---------------------------------------------------------------- O-01, 7.1
def test_two_columns_on_card_and_summary():
    card = RP.render_card(res_of([rec(1, 2, "S", known_channel="festival buying")]), 0)
    assert "| Calendar is associated with the outcome | Beyond known physical and social channels |" in card
    assert "| yes | no |" in card
    summary = RP.render_summary(res_of([rec(1, 2, "S", known_channel="festival buying"), rec(2, 2, "S")]))
    assert "| Encoding supported on this dataset | 2 | 2 | 1 |" in summary


def test_no_verdict_sentence_without_encoding_below_l4_over_random_records():
    rnd = random.Random(8)
    recs = []
    for i in range(200):
        lv, code = rnd.choice([1, 2, 3, 4, 5, 6]), rnd.choice("SCENU")
        recs.append(rec(i, lv, code, entry=rnd.choice(RP.ENTRIES)))
    res = res_of(recs)
    for i, r in enumerate(recs):
        card = RP.render_card(res, i)
        assert RP.disallowed_lines(card) == []
        if r["level"] < 4:
            first = [ln for ln in card.splitlines() if S.match(ln) and S.match(ln).startswith("verdict.")]
            assert len(first) == 1 and "ncoding" in first[0]
            assert "It is not a result about the source text or about astrology." in card
        else:
            assert "ncoding" not in card.split("## Verdict")[1].split("\n")[2]
    assert RP.disallowed_lines(RP.render_summary(res)) == []


def test_reading_differs_title_and_no_source_in_verdict_line():
    r = rec(1, 2, "N", reading_differs=True, source_name="Brihat Samhita")
    card = RP.render_card(res_of([r]), 0)
    assert card.startswith("# Project hypothesis derived from Brihat Samhita")
    assert "Brihat" not in card.split("## Verdict")[1]


# ---------------------------------------------------------------- O-02
def test_summary_opens_with_sampling_frame_and_has_no_percentage_cell_or_total():
    text = RP.render_summary(res_of(MIXED + [rec(7, 2, "N", reading_differs=True, source_name="Surya Siddhanta")]))
    assert text.index("## Sampling frame") < text.index("## Evidence level 4")
    assert text.index("## Sampling frame") < text.index("## Evidence level below 4")
    frame = text.split("## Sampling frame")[1].split("## Evidence level 4")[0]
    assert "| text | 6 |" in frame and "| project | 1 |" in frame  # a differing reading counts as project
    assert "| Not encodable | 4 |" in frame
    for ln in text.splitlines():
        if ln.startswith("|"):
            assert "%" not in ln
    assert "total" not in text.lower().replace("in total; expected", "")
    assert not re.search(r"\bastrology\b", text, re.I)
    # L2 and L4 counts sit in separate tables.
    l4 = text.split("## Evidence level 4 and above")[1].split("## Evidence level below 4")[0]
    enc = text.split("## Evidence level below 4")[1].split("## Project extensions")[0]
    assert "Encoding" not in l4 and "| Supported on this dataset | 1 |" in l4
    assert "| Encoding supported on this dataset | 1 |" in enc


# ---------------------------------------------------------------- methods
def test_methods_page_shows_x9_and_not_addressed_rule():
    text = RP.render_methods(res_of(MIXED, certificate=CERT))
    assert "| x2_K12 | 37.0% |" in text
    assert "X1" not in text
    assert "| 8 | 31% |" in text and "| 12 | 22% |" in text and "| 20 | 14% |" in text
    assert "Not addressed: an effect that appears in fewer than 31% of the episodes." in text
    no_cert = RP.render_methods(res_of(MIXED))
    assert "not recorded" in no_cert


def test_pages_are_deterministic_and_sorted():
    a = RP.render_pages(res_of(list(reversed(MIXED))))
    b = RP.render_pages(res_of(MIXED))
    assert a == b
    assert list(a)[:-2] == sorted(list(a)[:-2]) and list(a)[-2:] == ["summary.md", "methods.md"]


# ---------------------------------------------------------------- tools/check_paper_keys.py
def test_check_paper_keys_report_gate(built, tmp_path):
    rp, out, _ = built
    ok = cpk.main(["--pages", str(out), "--results", str(rp)])
    assert ok == 0
    page = out / "summary.md"
    page.write_text(page.read_text() + "\nOne more sentence.\n")
    assert cpk.main(["--pages", str(out), "--results", str(rp)]) == 1


def test_check_paper_keys_results_hash(built, tmp_path):
    rp, out, manifest = built
    assert cpk.check_results_hash("x", rp, manifest) == []
    bad = dict(manifest, results={"sha256": "0" * 64})
    assert cpk.check_results_hash("x", rp, bad)


def test_no_provenance_refused_with_report_gate(built):
    rp, out, _ = built
    assert cpk.main(["--pages", str(out), "--results", str(rp), "--no-provenance"]) == 2
