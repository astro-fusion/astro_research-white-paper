"""Validation levels L0 to L6 are computed from evidence (ADR-004 D-4, WP-20)."""

import copy
import json
from datetime import datetime, timezone

import pytest

from vedic_astrology_core.rules import default_rules_dir, load_rules
from vedic_astrology_core.rules.levels import (
    FAMILY_MIN_LEVEL,
    Evidence,
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


GOOD = Evidence(cases_pass=True, n_cases=2, jhora_cases=3, horizons_ok=True)
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
    assert level(rule, GOOD).level == 3
    assert level(rule, Evidence(True, 2, 2, True)).level == 2
    assert level(rule, Evidence(True, 2, 3, False)).level == 2
    assert level(rule, Evidence(False, 2, 3, True)).level == 2
    assert FAMILY_MIN_LEVEL == 3


def test_l3_refuses_rules_that_wait():
    """A needs_verification rule cannot be L3."""
    rule = base(status="needs_verification", tier="experimental")
    assert level(rule, GOOD).level == 2


def test_l4_needs_a_blind_reviewer_who_is_not_the_author():
    """Author reviews and unblind reviews do not count."""
    own = base(review=[{**REVIEW, "by": "@Author"}])
    assert level(own, GOOD).level == 3
    unblind = base(review=[{**REVIEW, "blind_attestation": None}])
    assert level(unblind, GOOD).level == 3
    bad = base(review=[{**REVIEW, "verdict": "not_faithful"}])
    assert level(bad, GOOD).level == 3
    ok = base(review=[REVIEW])
    assert level(ok, GOOD).level == 4


def test_l5_and_l6_are_cumulative():
    """Fit and confirm count only on top of the lower levels."""
    explored = base(review=[REVIEW], tuning_log=[TUNING])
    assert level(explored, GOOD).level == 5
    confirmed = base(review=[REVIEW], tuning_log=[TUNING], validation=STAMP)
    report = level(confirmed, GOOD)
    assert report.level == 6 and report.next_missing == []
    assert report.name == "Confirmed or refuted"
    assert report.render().splitlines()[0].endswith("L6 Confirmed or refuted")
    # a confirm without review stays at L3 (the report still lists L4 as missing)
    skipped = base(tuning_log=[TUNING], validation=STAMP)
    got = level(skipped, GOOD)
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


def test_fixture_evidence_counts_only_manual_agreeing_readings(tmp_path):
    """pyjhora and disagreeing files do not count toward L3."""
    rule = base()
    (tmp_path / "jhora").mkdir()
    (tmp_path / "horizons").mkdir()
    docs = [
        {"rule_id": rule.id, "source": "jhora_manual", "reader": "A", "agrees": True},
        {"rule_id": rule.id, "source": "jhora_manual", "reader": "B"},
        {"rule_id": rule.id, "source": "pyjhora", "reader": "C"},
        {"rule_id": rule.id, "source": "jhora_manual", "reader": "", "agrees": True},
        {"rule_id": rule.id, "source": "jhora_manual", "reader": "D", "agrees": False},
        {"rule_id": "other.rule", "source": "jhora_manual", "reader": "E"},
    ]
    for i, doc in enumerate(docs):
        (tmp_path / "jhora" / f"{i}.json").write_text(json.dumps(doc))
    (tmp_path / "horizons" / "a.json").write_text(
        json.dumps({"rule_id": rule.id, "agrees": True})
    )
    ev = fixture_evidence(rule, True, tmp_path)
    assert ev.jhora_cases == 2 and ev.horizons_ok is True
    empty = fixture_evidence(rule, True, tmp_path / "none")
    assert empty.jhora_cases == 0 and empty.horizons_ok is False


def test_every_committed_rule_has_a_level():
    """The catalogue computes; nothing is above L2 without evidence."""
    loaded, problems = load_rules([default_rules_dir()])
    assert not problems
    for item in loaded:
        assert level(item.rule).level <= 2, item.rule.id
