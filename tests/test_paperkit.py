"""Tests for the paper kit accessor (ADR-004 WP-16)."""

import json
import math

import pytest

from vedic_astrology_core.paperkit import (
    MissingKeyError,
    NullValueError,
    Results,
    format_number,
    format_p,
)

DATA = {
    "headline": {"n": 42, "spa_p": 0.5257, "tiny_p": 0.00004, "frac": 0.125, "verdict": "null"},
    "tests": [{"p": 0.01}, {"p": 0.2}],
    "missing_value": None,
    "nan_value": float("nan"),
    "flag": True,
}


@pytest.fixture
def res():
    return Results(DATA, "mem")


def test_get_nested_and_list(res):
    assert res.get("headline.n") == 42
    assert res.get("tests.1.p") == 0.2


@pytest.mark.parametrize("key", ["headline.nope", "nope", "tests.5.p", "tests.x", "headline.n.deeper", ""])
def test_missing_key_raises(res, key):
    with pytest.raises(MissingKeyError):
        res.get(key)


def test_missing_key_is_keyerror_with_readable_message(res):
    with pytest.raises(KeyError) as exc:
        res.get("headline.nope")
    assert "headline.nope" in str(exc.value)
    assert not str(exc.value).startswith("'")


@pytest.mark.parametrize("key", ["missing_value", "nan_value"])
def test_null_and_nan_raise(res, key):
    assert res.has(key) or key == "nan_value"
    with pytest.raises(NullValueError):
        res.get(key)


def test_has(res):
    assert res.has("headline.n")
    assert not res.has("headline.zzz")


def test_formatting(res):
    assert res.num("headline.spa_p", 3) == "0.526"
    assert res.num("headline.n") == "42"
    assert res.count("headline.n") == "42"
    assert res.pct("headline.frac") == "12.5%"
    assert res.p("headline.spa_p") == "p = 0.526"
    assert res.p("headline.tiny_p") == "p < 0.001"
    assert res.text("headline.verdict") == "null"


def test_type_errors(res):
    with pytest.raises(TypeError):
        res.num("flag")
    with pytest.raises(TypeError):
        res.text("headline.n")
    with pytest.raises(ValueError):
        res.count("headline.spa_p")


def test_format_helpers():
    assert format_number(3.14159, 2) == "3.14"
    assert format_number(7) == "7"
    with pytest.raises(NullValueError):
        format_number(math.inf)
    with pytest.raises(ValueError):
        format_p(1.5)


def test_load_roundtrip(tmp_path):
    p = tmp_path / "results.json"
    p.write_text(json.dumps({"a": {"b": 1.5}}))
    assert Results.load(p).num("a.b", 1) == "1.5"
    p.write_text("[1, 2]")
    with pytest.raises(ValueError):
        Results.load(p)
