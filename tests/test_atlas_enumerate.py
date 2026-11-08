"""Tests for the combination-atlas grammar expansion."""

import importlib.util

import pytest

from studies._paths import STUDIES_ROOT

SCRIPTS = STUDIES_ROOT / "combinations" / "scripts"


def _load(name, file):
    """Build the load fixture."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


enum = _load("atlas_enumerate", "enumerate.py")


@pytest.fixture(scope="module")
def cands():
    """Return the expanded candidates."""
    return enum.expand()


def test_expansion_is_deterministic(cands):
    """Check expansion is deterministic."""
    again = enum.expand()
    assert [c["key"] for c in cands] == [c["key"] for c in again]
    ids = [f"atl-{i:05d}" for i in range(1, len(cands) + 1)]
    assert [c["id"] for c in cands] == ids


def test_counts_per_template(cands):
    """Check counts per template."""
    counts = {}
    for c in cands:
        counts[c["template"]] = counts.get(c["template"], 0) + 1
    # 9 planets: sign 108 + lagna 108 + Moon-houses 96 + nakshatra groups 81.
    assert counts["T1"] == 393
    assert counts["T2"] == 72 + 36
    assert counts["T3"] == 18
    assert counts["T4"] == 108 * 16
    assert counts["T5"] == 393 * 2
    assert counts["T6"] == 108 * 2
    assert counts["T7"] == 108 * 16
    assert len(cands) == 4977


def test_keys_unique_and_depth_bounded(cands):
    """Check keys unique and depth bounded."""
    keys = [c["key"] for c in cands]
    assert len(set(keys)) == len(keys)
    assert max(c["depth"] for c in cands) <= 3
    assert all(c["depth"] == len(c["clauses"]) for c in cands)


def test_plain_words(cands):
    """Check plain words."""
    by_key = {c["key"]: c for c in cands}
    assert by_key["MARS@sign=0"]["definition"] == "Mars in Aries"
    assert by_key["MARS>aspect>SATURN"]["definition"] == (
        "Mars casts a Parashari aspect on Saturn")
    assert by_key["MARS~conj~SATURN"]["definition"] == "Mars within 8 deg of Saturn"
    assert "Ketu-ruled nakshatra (Ashvini, Magha, Mula)" in by_key[
        "SUN@nakshatra_group=0"]["definition"]
    assert "mahadasha" in by_key["dasha1=SATURN"]["definition"]
    assert "from the moment's lagna at Kathmandu" in by_key[
        "SATURN@house_from_lagna=7"]["definition"]
    assert "MOON@house_from_moon=0" not in by_key
