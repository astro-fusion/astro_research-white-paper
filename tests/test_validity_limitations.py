"""ADR-007 WP-72: the limitations builder (section 6)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vedic_astrology_core.rules.schema import Rule
from vedic_astrology_core.validity import limitations as lim
from vedic_astrology_core.validity.limitations import KINDS, LimitationError, build_limitations

ROOT = Path(__file__).resolve().parents[1]
MANDALA = ROOT / "rules/mundane/practitioner/bs32_agni_mandala_earthquake.yaml"

CHOICES = [
    {"choice": "day_convention", "value": "utc_day", "fixed_by": "project", "alternatives": ["local_day"]},
    {"choice": "place", "value": "London", "fixed_by": "project", "alternatives": ["Delhi"]},
    {"choice": "horizon", "value": 0, "fixed_by": "text"},
]
TESTS = [{"domain": "earthquake", "outcome": "mainshock_rate", "direction": "either", "project_extension": True}]
PLAN = {
    "domain": "earthquake",
    "outcomes": [{"id": "mainshock_rate"}, {"id": "m7_rate"}],
    "vintages": [{"id": "eq_v1", "seen": True}],
}


def rule_from(path: Path, **extra) -> Rule:
    doc = yaml.safe_load(path.read_text())
    doc.update(extra)
    return Rule.model_validate(doc)


def mandala(**extra) -> Rule:
    reading = {"kind": "forward_trigger", "text_says": "post_event_classification",
               "note": "the chapter classifies a shock after it happened"}
    return rule_from(MANDALA, reading=reading, operationalisation=CHOICES, tests=TESTS, **extra)


def sun_rule() -> Rule:
    doc = yaml.safe_load(MANDALA.read_text())
    doc["conditions"] = {"in_sign": {"planet": "Sun", "signs": ["Leo"]}}
    doc["reading"] = {"kind": "concurrent"}
    doc["operationalisation"] = CHOICES
    doc["tests"] = TESTS
    return Rule.model_validate(doc)


def by_kind(rows):
    return {r.kind: r.text for r in rows}


def test_mandala_yields_reading_line():
    rows = by_kind(build_limitations(mandala()))
    text = rows["reading_tested"]
    assert "post-event" not in text
    assert "The text reads it as a classification made after the event." in text
    assert "We tested it as a trigger that comes before the event." in text
    assert "A null here does not test the text's own claim." in text


def test_all_rows_in_order_with_full_inputs():
    rows = build_limitations(
        sun_rule(),
        plan={**PLAN, "domain": "earthquake"},
        dataset={"span": ["1968", "1998"], "grade": "B", "unit": "German marks", "licence": "unread"},
        calendar={"duty_cycle": 0.04, "episodes_confirm": 9, "mde_confirm": 3.1},
        gate={"support_failed": ["too_few_episodes"], "limit_failed": []},
        r4=0.8,
        disputes=[sun_rule().id],
    )
    assert [r.kind for r in rows] == list(KINDS)
    t = by_kind(rows)
    assert "Active 4% of the time, 9 episodes in the confirm period." in t["evidence_amount"]
    assert "3.1" in t["evidence_amount"]
    assert "1968 to 1998 only" in t["data"] and "German marks" in t["data"] and "Licence not yet read" in t["data"]
    assert "m7_rate" in t["not_tested"] and "fewer than 8" in t["not_tested"]
    assert "Schools disagree" in t["disputes"]
    assert "eq_v1" in t["seen_before"]


def test_sun_in_sign_yields_separability_line():
    t = by_kind(build_limitations(sun_rule()))
    assert "separability" in t
    assert "A calendar effect cannot be told apart." in t["separability"]
    assert lim.separable_from_calendar(sun_rule()) == "in_sign"


def test_moon_rule_has_no_separability_unless_r4_fails():
    assert "separability" not in by_kind(build_limitations(mandala()))
    assert "separability" not in by_kind(build_limitations(mandala(), r4=0.2))
    assert "separability" in by_kind(build_limitations(mandala(), r4={"detail": {"baseline_r2": 0.7}}))


def test_missing_reading_or_operationalisation_raises():
    with pytest.raises(LimitationError) as e:
        build_limitations(rule_from(MANDALA, operationalisation=CHOICES))
    assert "reading" in str(e.value)
    with pytest.raises(LimitationError) as e:
        build_limitations(rule_from(MANDALA, reading={"kind": "concurrent"}))
    assert "operationalisation" in str(e.value)
    with pytest.raises(LimitationError):
        lim.require_registrable(rule_from(MANDALA))


def test_choices_and_conventions():
    t = by_kind(build_limitations(mandala()))
    assert "place: London, chosen by the project. Other values: Delhi." in t["choices"]
    assert "horizon" not in t["choices"]  # fixed by the text
    assert "window_before = 0" in t["choices"]  # param with no range_source
    assert "Zodiac not stated" in t["conventions"] and "mean node" in t["conventions"]
    assert "place London" in t["conventions"]


def test_below_l4_citation_line_says_encoding():
    t = by_kind(build_limitations(mandala()))
    assert t["citation_level"].startswith("Level L")
    assert "encoding" in t["citation_level"]
    assert "validated" not in " ".join(t.values()).lower()


def test_tradition_experimental_and_classical():
    t = by_kind(build_limitations(mandala()))
    assert t["tradition"].startswith("Modern practice.")
    r = mandala()
    classical = r.model_copy(update={"tier": "classical", "source": r.source.model_copy(update={"chapter": "32"})})
    assert by_kind(build_limitations(classical))["tradition"].startswith("Classical source:")


def test_missing_inputs_print_not_recorded():
    t = by_kind(build_limitations(mandala()))
    assert "not recorded" in t["data"]
    assert "not recorded" in t["evidence_amount"]
    assert "plan not recorded" in t["not_tested"]
    assert "seen_before" not in t and "disputes" not in t


def test_reading_same_and_unrecorded():
    r = mandala()
    same = r.model_copy(update={"reading": r.reading.model_copy(update={"text_says": "forward_trigger"})})
    assert "tested the same way" in by_kind(build_limitations(same))["reading_tested"]
    none = r.model_copy(update={"reading": r.reading.model_copy(update={"text_says": None})})
    assert "does not record how the source reads it" in by_kind(build_limitations(none))["reading_tested"]
