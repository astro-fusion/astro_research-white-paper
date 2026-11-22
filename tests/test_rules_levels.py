"""Validation levels L0 to L6 are computed from evidence (ADR-004 D-4, WP-20)."""

import copy
import json
from datetime import datetime, timezone

import pytest

from vedic_astrology_core.rules import default_rules_dir, load_rules
from vedic_astrology_core.rules.levels import (
    FAMILY_MIN_LEVEL,
    Evidence,
    ReviewProof,
    fixture_evidence,
    level,
)
from vedic_astrology_core.rules.schema import Rule

FULL_SOURCE = {
    "text": "Brihat Samhita",
    "edition": "Bhat 1981",
    "translator": "M. R. Bhat",
    "chapter": "17",
    "verse": "1-3",
    "quote": "When Mars and Ketu meet ...",
    "checked_by": "@maintainer",
    "checked_on": "2026-11-22",
}


def raw(**over):
    """Raw data of a rule that is exactly L2 (sourced and operationalised)."""
    data = {
        "id": "test.levels",
        "name": "L",
        "domain": "seismic",
        "claim": "c",
        "source": dict(FULL_SOURCE),
        "author": "@author",
        "tier": "classical",
        "node_model": "mean",
        "zodiac": "sidereal",
        "ayanamsa": "lahiri",
        "params": {
            "orb": {
                "value": 8,
                "min": 2,
                "max": 12,
                "step": 1,
                "unit": "deg",
                "range_source": "author's choice",
            }
        },
        "conditions": {"conjunct_within": {"planets": ["Mars", "Saturn"], "orb": "$orb"}},
        "expected_effect": {"direction": "up"},
        "reference_cases": [
            {"moment": "2000-01-01T12:00:00Z", "expect": "fires", "note": "a"},
            {"moment": "2001-01-01T12:00:00Z", "expect": "silent", "note": "b"},
        ],
    }
    data.update(over)
    return data


def base(**over):
    """A rule that is exactly L2."""
    return Rule.model_validate(raw(**over))


CLOSE = datetime(2026, 12, 1, tzinfo=timezone.utc)
PROOF = ReviewProof(
    by="@reviewer",
    reviewer_identity="rev@example.org",
    author_identity="auth@example.org",
    committed_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
)
GOOD3 = Evidence(cases_pass=True, n_cases=2, jhora_cases=3, horizons_ok=True)
GOOD = Evidence(
    cases_pass=True,
    n_cases=2,
    jhora_cases=3,
    horizons_ok=True,
    review_proofs=(PROOF,),
    batch_close=CLOSE,
)
REVIEW = {
    "by": "@reviewer",
    "at": datetime(2026, 11, 22, tzinfo=timezone.utc),
    "verdict": "faithful",
    "note": "ok",
    "version": 1,
    "blind_attestation": True,
}
TUNING = {
    "at": datetime(2026, 11, 22, tzinfo=timezone.utc),
    "by": "@me",
    "study": "earthquake",
    "version": 1,
    "explore": {"n_cells": 3},
}
STAMP = {
    "status": "not_confirmed",
    "version": 1,
    "study": "earthquake",
    "confirm": {"p": 0.5},
    "at": datetime(2026, 11, 23, tzinfo=timezone.utc),
}


def test_l0_when_source_is_thin():
    """A bare source only records the rule."""
    rule = base(source={"text": "Folk", "chapter": "1"})
    report = level(rule)
    assert report.level == 0
    assert "source.edition" in report.next_missing
    assert "a maintainer check" in " ".join(report.next_missing)


def test_l1_to_l2_progress_and_what_is_missing():
    """Complete source gives L1; L2 needs range_source, direction, zodiac, ayanamsa."""
    data = raw()
    data["params"]["orb"].pop("range_source")
    data.pop("zodiac")
    data.pop("ayanamsa")
    data["expected_effect"] = {"description": "x"}
    data.pop("node_model")
    rule = Rule.model_validate(data)
    report = level(rule)
    assert report.level == 1
    assert set(report.next_missing) == {
        "params.orb.range_source",
        "expected_effect.direction",
        "zodiac (sidereal or tropical)",
        "ayanamsa",
        "node_model stated explicitly",
    }


def test_l2_without_evidence_stops_there():
    """Cases not run: L3 is unmet and says so."""
    report = level(base())
    assert report.level == 2
    assert any("reference cases not run" in m for m in report.next_missing)


def test_l3_needs_cases_jhora_and_horizons():
    """Each piece of L3 evidence is required."""
    rule = base()
    assert level(rule, GOOD3).level == 3
    assert level(rule, Evidence(True, 2, 2, True)).level == 2
    assert level(rule, Evidence(True, 2, 3, False)).level == 2
    assert level(rule, Evidence(False, 2, 3, True)).level == 2
    assert FAMILY_MIN_LEVEL == 2


def test_l3_refuses_rules_that_wait():
    """A needs_verification rule cannot be L3."""
    rule = base(status="needs_verification", tier="experimental")
    assert level(rule, GOOD).level == 2


def test_l4_needs_a_second_identity_before_the_batch_close():
    """A typed blind flag is not enough; the proof is checked (G-09, A-10)."""
    ok = base(review=[REVIEW])
    report = level(ok, GOOD)
    assert report.level == 4
    assert "attested before the result" in report.attestation
    # the typed flag alone, with no proof, does not give L4
    assert level(ok, GOOD3).level == 3
    own = base(review=[{**REVIEW, "by": "@Author"}])
    assert level(own, GOOD).level == 3
    bad = base(review=[{**REVIEW, "verdict": "not_faithful"}])
    assert level(bad, GOOD).level == 3
    # same git identity as the author is rejected
    same = Evidence(
        True, 2, 3, True,
        review_proofs=(ReviewProof("@reviewer", "AUTH@example.org", "auth@example.org", PROOF.committed_at),),
        batch_close=CLOSE,
    )
    assert level(ok, same).level == 3


def test_late_review_is_shown_with_its_date_and_is_not_l4():
    """A review after the batch close is not attested before the result."""
    late = ReviewProof("@reviewer", "rev@example.org", "auth@example.org",
                       datetime(2026, 12, 5, tzinfo=timezone.utc))
    ev = Evidence(True, 2, 3, True, review_proofs=(late,), batch_close=CLOSE)
    report = level(base(review=[REVIEW]), ev)
    assert report.level == 3
    assert "2026-12-05" in report.attestation
    assert "not attested before the result" in report.attestation
    # no batch close known: cannot show the review predates anything
    ev2 = Evidence(True, 2, 3, True, review_proofs=(PROOF,), batch_close=None)
    assert level(base(review=[REVIEW]), ev2).level == 3


def test_outside_reference_gives_l4_without_a_date():
    """A review with an outside reference counts even after the close."""
    ref = ReviewProof("@reviewer", "rev@example.org", "auth@example.org",
                      datetime(2026, 12, 5, tzinfo=timezone.utc), "J. Doe, letter 2026-12-05")
    ev = Evidence(True, 2, 3, True, review_proofs=(ref,), batch_close=CLOSE)
    report = level(base(review=[REVIEW]), ev)
    assert report.level == 4 and "outside reference" in report.attestation


def test_l5_and_l6_are_cumulative():
    """Fit and confirm count only on top of the lower levels."""
    explored = base(review=[REVIEW], tuning_log=[TUNING])
    assert level(explored, GOOD).level == 5
    confirmed = base(review=[REVIEW], tuning_log=[TUNING], validation=STAMP)
    report = level(confirmed, GOOD)
    assert report.level == 6 and report.next_missing == []
    assert report.name == "Confirmed or refuted"
    assert report.render().splitlines()[0].endswith("L6 Confirmed or refuted")
    assert "Confirmed or refuted" in report.render().splitlines()[0]
    # a confirm without review stays at L3 (the report still lists L4 as missing)
    skipped = base(tuning_log=[TUNING], validation=STAMP)
    got = level(skipped, GOOD3)
    assert got.level == 3 and 4 in got.missing


def test_stale_confirm_stamp_does_not_count():
    """A stamp from another version is not L6."""
    stale = base(
        version=2,
        review=[{**REVIEW, "version": 2}],
        tuning_log=[{**TUNING, "version": 2}],
        validation=STAMP,
    )
    assert level(stale, GOOD).level == 5


def test_url_source_levels():
    """Practitioner sources need url, published, archive_url and quote."""
    src = {
        "url": "https://example.org/a",
        "published": "2019-05-01",
        "archive_url": "https://web.archive.org/web/2019/https://example.org/a",
        "quote": "q",
        "checked_by": "@m",
        "checked_on": "2026-11-22",
    }
    rule = base(source=src, tier="experimental")
    assert level(rule).level == 2
    assert level(base(source={"url": "https://example.org/a"}, tier="experimental")).level == 0


def _jh(rule_id, **over):
    doc = {"rule_id": rule_id, "source": "jhora_manual", "reader": "A", "agrees": True,
           "computed_deg": 10.0, "reference_deg": 10.0 + 0.5 / 60}
    doc.update(over)
    return doc


def test_fixture_evidence_checks_numbers_and_tolerances(tmp_path):
    """agrees must be true and the numbers must be inside the tolerance."""
    rule = base()
    (tmp_path / "jhora").mkdir()
    (tmp_path / "horizons").mkdir()
    docs = [
        _jh(rule.id),
        _jh(rule.id, reader="B", computed_deg=359.99, reference_deg=0.0 + 0.0001),  # wraps
        _jh(rule.id, reader="B2", agrees=None),
        {k: v for k, v in _jh(rule.id, reader="B3").items() if k != "agrees"},
        _jh(rule.id, source="pyjhora", reader="C"),
        _jh(rule.id, reader=""),
        _jh(rule.id, reader="D", agrees=False),
        _jh(rule.id, reader="F", reference_deg=10.1),  # 6 arcmin out
        _jh(rule.id, reader="G", tolerance_arcmin=5, reference_deg=10.05),  # loosened
        {k: v for k, v in _jh(rule.id, reader="H").items() if k != "computed_deg"},
        _jh("other.rule", reader="E"),
    ]
    for i, doc in enumerate(docs):
        (tmp_path / "jhora" / f"{i}.json").write_text(json.dumps(doc))
    hz = {"rule_id": rule.id, "agrees": True, "computed_deg": 100.0, "reference_deg": 100.0 + 3 / 3600}
    (tmp_path / "horizons" / "a.json").write_text(json.dumps(hz))
    ev = fixture_evidence(rule, True, tmp_path)
    assert ev.jhora_cases == 2 and ev.horizons_ok is True
    # an out-of-tolerance Horizons file fails the check
    (tmp_path / "horizons" / "b.json").write_text(json.dumps({**hz, "reference_deg": 100.01}))
    assert fixture_evidence(rule, True, tmp_path).horizons_ok is False
    (tmp_path / "horizons" / "b.json").unlink()
    # a Horizons fixture without agrees is not counted as agreement
    (tmp_path / "horizons" / "a.json").write_text(
        json.dumps({k: v for k, v in hz.items() if k != "agrees"})
    )
    assert fixture_evidence(rule, True, tmp_path).horizons_ok is False
    empty = fixture_evidence(rule, True, tmp_path / "none")
    assert empty.jhora_cases == 0 and empty.horizons_ok is False


def test_every_committed_rule_has_a_level():
    """The catalogue computes; nothing is above L2 without evidence."""
    loaded, problems = load_rules([default_rules_dir()])
    assert not problems
    for item in loaded:
        assert level(item.rule).level <= 2, item.rule.id
