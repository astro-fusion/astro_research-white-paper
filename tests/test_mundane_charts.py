"""Founding chart table (ADR-006 WP-50)."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from tests.golden import CHARTS, point
from vedic_astrology_core.astrology.divisional import varga_sign
from vedic_astrology_core.mundane import charts as charts_mod
from vedic_astrology_core.mundane.catalogue import CatalogueError, MethodNotCited
from vedic_astrology_core.mundane.charts import GRAHAS, founding_table
from vedic_astrology_core.mundane.registry import RegistryError, load_charts

GOLD = {c["id"]: c for c in CHARTS}["del_1947"]
KEYS = {"Sun": "SUN", "Moon": "MOON", "Mars": "MARS", "Mercury": "MERCURY",
        "Jupiter": "JUPITER", "Venus": "VENUS", "Saturn": "SATURN",
        "Rahu": "RAHU", "Ketu": "KETU", "Lagna": "ASC"}


@pytest.fixture(scope="module")
def india():
    return {c.chart_id: c for c in load_charts()}["in-1947-midnight"]


@pytest.fixture(scope="module")
def table(india):
    return founding_table(india, ["D1", "D9"])


def test_india_matches_pyjhora_golden(table):
    assert table.has_lagna and table.moment_utc.isoformat() == GOLD["utc"]
    for varga in ("D1", "D9"):
        for row in table.points:
            assert row.vargas[varga].sign == GOLD["vargas"][varga][KEYS[row.point]], (varga, row.point)


def test_lagna_and_nine_grahas(table):
    assert [r.point for r in table.points] == ["Lagna", *GRAHAS]
    assert abs(table.row("Lagna").longitude - GOLD["ascendant"]) < 1 / 60


def test_houses_from_varga_lagna(table):
    for varga in ("D1", "D9"):
        lagna = table.row("Lagna").vargas[varga]
        assert lagna.house == 1
        for row in table.points:
            p = row.vargas[varga]
            assert p.house == (p.sign - lagna.sign) % 12 + 1
    assert table.row("Lagna").vargas["D1"].sign_name == "Taurus"


def test_dignity(table):
    moon = table.row("Moon").vargas["D1"]
    assert moon.sign_name == "Cancer" and moon.dignity == ["own"]
    assert table.row("Lagna").vargas["D1"].dignity is None
    for row in table.points[1:]:
        assert row.vargas["D9"].dignity and "moolatrikona" not in row.vargas["D9"].dignity


def test_uses_varga_sign_only(table):
    for row in table.points:
        assert row.vargas["D9"].sign == varga_sign(row.longitude, 9)


@pytest.mark.parametrize("varga", ["D5", "D6", "D8"])
def test_uncited_varga_raises(india, varga):
    with pytest.raises(MethodNotCited, match="not cited"):
        founding_table(india, ["D1", varga])


def test_unknown_varga_raises(india):
    with pytest.raises(CatalogueError):
        founding_table(india, ["D99"])
    with pytest.raises(CatalogueError):
        founding_table(india, ["nine"])


def test_date_only_chart_has_no_lagna_or_houses(india):
    dated = replace(
        india, time=None,
        time_evidence={**india.time_evidence, "kind": "none", "stated_precision_minutes": None},
    )
    t = founding_table(dated, ["D1", "D9"])
    assert not t.has_lagna and not t.time_known and t.grade == "D"
    assert [r.point for r in t.points] == list(GRAHAS)
    for row in t.points:
        for p in row.vargas.values():
            assert p.house is None
            assert p.sign is not None


def test_d2_hora_lord_no_houses(table, india):
    t = founding_table(india, ["D1", "D2"])
    for row in t.points:
        p = row.vargas["D2"]
        assert p.house is None and p.dignity is None
        assert p.hora_lord in ("Sun", "Moon")
        assert p.hora_lord == ("Sun" if p.sign == 4 else "Moon")


def test_moment_override_must_be_aware(india):
    with pytest.raises(ValueError):
        founding_table(india, ["D1"], moment=datetime(1947, 8, 15, 0, 0))
    shifted = founding_table(india, ["D1"], moment=datetime(1947, 8, 14, 18, 31, tzinfo=timezone.utc))
    assert shifted.moment_utc.minute == 31


def test_grade_x_refused(india):
    with pytest.raises(RegistryError):
        founding_table(replace(india, date_disputed=True))


def test_provenance_and_dict(table):
    d = table.to_dict()
    assert len(d["catalogue_sha256"]) == 64
    assert d["settings"]["houses"] == "whole_sign"
    assert d["grade"] == "C"
    assert charts_mod.SETTINGS["ayanamsa"] == "lahiri"
