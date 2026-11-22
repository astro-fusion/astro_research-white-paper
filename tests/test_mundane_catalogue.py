"""Method catalogue (ADR-006 WP-48): schema, loader, seed entries."""

import shutil
from pathlib import Path

import pytest
import yaml

from vedic_astrology_core.mundane.catalogue import (
    CatalogueError,
    MethodNotCited,
    default_methods_dir,
    load_catalogue,
    load_method_file,
)

SEED = default_methods_dir()


@pytest.fixture(scope="module")
def cat():
    return load_catalogue()


def _entry(**over):
    base = yaml.safe_load((SEED / "_varga.d9.yaml").read_text())
    base.update(over)
    return base


def _write(tmp_path, data, name=None):
    path = tmp_path / (name or f"_{data['id']}.yaml")
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


def test_seed_catalogue_loads_with_all_section_4_3_ids(cat):
    expected = {
        "varga.d1", "varga.d2", "varga.d3", "varga.d4", "varga.d7", "varga.d9",
        "varga.d5", "varga.d6", "varga.d8", "dasha.vimshottari", "dasha.lord_state",
        "transit.gochara_moon", "transit.from_lagna", "transit.conjunct_natal",
        "transit.aspects_natal",
        "transit.over_varga", "transit.in_varga", "sky.bs32_mandala", "sky.kurma",
        "sky.eclipse", "sky.samvatsara", "sky.graha_yuddha", "annual.mesha_sankranti",
        "annual.chaitra_pratipada", "house.mundane_meaning", "cycle.jupiter_saturn",
        "transit.ashtakavarga",
    }
    assert set(cat.methods) == expected


def test_every_implementation_imports(cat):
    for m in cat:
        if m.implementation:
            assert callable(m.resolve()), m.id


def test_all_seed_entries_are_unverified_today(cat):
    for m in cat:
        assert m.citation_status() == "unverified", m.id
        assert m.level() == 0


def test_extended_varga_not_cited(cat):
    for mid in ("varga.d5", "varga.d6", "varga.d8"):
        m = cat.get(mid)
        assert m.tier == "extended" and m.implementation is None
        with pytest.raises(MethodNotCited, match="not cited"):
            cat.compute(mid, 10.0)


def test_compute_runs_seed_method(cat):
    assert cat.compute("varga.d9", 0.0) == 0
    assert cat.compute("varga.d1", 45.0) == 1


def test_unknown_method_refused(cat):
    with pytest.raises(CatalogueError, match="no catalogue entry"):
        cat.compute("varga.d99", 1.0)


def test_use_gates(cat):
    assert cat.require("varga.d9", "case_file")
    with pytest.raises(CatalogueError):
        cat.require("varga.d9", "explore")
    with pytest.raises(CatalogueError):
        cat.require("varga.d9", "confirmatory")


def test_hash_is_stable_and_changes_with_content(tmp_path):
    assert load_catalogue().hash() == load_catalogue().hash()
    copy = tmp_path / "m"
    shutil.copytree(SEED, copy)
    assert load_catalogue(copy).hash() == load_catalogue().hash()
    p = copy / "_varga.d9.yaml"
    p.write_text(p.read_text().replace("sidereal_longitude", "other", 1))
    assert load_catalogue(copy).hash() != load_catalogue().hash()


@pytest.mark.parametrize("key", ["citation_status", "level"])
def test_computed_keys_may_not_be_written(tmp_path, key):
    path = _write(tmp_path, _entry(**{key: "verified"}))
    with pytest.raises(CatalogueError, match="computed"):
        load_method_file(path)


def test_unknown_key_rejected(tmp_path):
    path = _write(tmp_path, _entry(colour="red"))
    with pytest.raises(CatalogueError, match="unknown field"):
        load_method_file(path)


def test_core_without_formula_fails(tmp_path):
    data = _entry()
    data["definition"]["formula"] = None
    with pytest.raises(CatalogueError, match="formula"):
        load_method_file(_write(tmp_path, data))


def test_bad_implementation_path_fails(tmp_path):
    data = _entry(implementation={"module": "vedic_astrology_core.astrology.divisional", "function": "nope"})
    with pytest.raises(CatalogueError, match="does not exist"):
        load_method_file(_write(tmp_path, data))
    data = _entry(implementation={"module": "vedic_astrology_core.no_such", "function": "f"})
    with pytest.raises(CatalogueError, match="does not import"):
        load_method_file(_write(tmp_path, data))


def test_unknown_predicate_fails(tmp_path):
    with pytest.raises(CatalogueError, match="not registered"):
        load_method_file(_write(tmp_path, _entry(predicates=["no_such_predicate"])))


def test_filename_and_family_must_match_id(tmp_path):
    with pytest.raises(CatalogueError, match="file name"):
        load_method_file(_write(tmp_path, _entry(), name="_varga.d1.yaml"))
    with pytest.raises(CatalogueError, match="family"):
        load_method_file(_write(tmp_path, _entry(family="dasha")))


def test_extended_cannot_enter_aggregate(tmp_path):
    with pytest.raises(CatalogueError, match="aggregate"):
        load_method_file(_write(tmp_path, _entry(tier="extended")))


def test_status_rises_with_evidence(tmp_path):
    data = _entry()
    data["source"].update(
        quote="q", verse="1", checked_by="maintainer", checked_at="2026-11-22"
    )
    m, _ = load_method_file(_write(tmp_path, data))
    assert m.citation_status() == "page_cited"
    assert m.level() == 1
    assert m.allowed_in("explore") and not m.allowed_in("confirmatory")
    # three existing reference cases make it verified
    root = tmp_path
    fx = []
    for i in range(3):
        (root / f"c{i}.json").write_text("{}")
        fx.append(f"c{i}.json")
    data["reference_cases"] = fx
    m, _ = load_method_file(_write(tmp_path, data))
    assert m.citation_status(root) == "verified"
    assert m.level(root) == 3
    assert m.allowed_in("confirmatory", root)
    # missing fixtures do not count
    data["reference_cases"] = ["missing1.json", "missing2.json", "missing3.json"]
    m, _ = load_method_file(_write(tmp_path, data))
    assert m.citation_status(root) == "page_cited"


def test_duplicate_ids_fail(tmp_path):
    _write(tmp_path, _entry())
    _write(tmp_path, _entry(), name="_varga.d9b.yaml")
    with pytest.raises(CatalogueError):
        load_catalogue(tmp_path)


def test_method_files_are_invisible_to_rule_loader():
    from vedic_astrology_core.rules.loader import discover

    assert not [p for p in discover() if "methods" in p.parts]
