"""Tests for shared Vedic principles catalog."""

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "src" / "vedic_astrology_core" / "principles" / "catalog.py"

spec = importlib.util.spec_from_file_location("vedic_principles_catalog", CATALOG_PATH)
module = importlib.util.module_from_spec(spec)
if spec and spec.loader:
    spec.loader.exec_module(module)
else:
    raise RuntimeError(f"Unable to import catalog module from {CATALOG_PATH}")


def test_catalog_schema_and_uniqueness():
    df = module.build_vedic_principles_catalog()
    expected_cols = {
        "principle_id",
        "family",
        "item_type",
        "name",
        "description",
        "scope",
        "computable",
        "sources",
    }
    assert expected_cols.issubset(df.columns)
    assert df["principle_id"].is_unique
    assert len(df) > 100


def test_catalog_core_counts():
    df = module.build_vedic_principles_catalog()
    graha_members = df[(df["family"] == "graha") & (df["item_type"] == "member")]
    nak_members = df[(df["family"] == "nakshatra") & (df["item_type"] == "member")]
    rashi_members = df[(df["family"] == "rashi") & (df["item_type"] == "member")]

    assert len(graha_members) == 9
    assert len(nak_members) == 27
    assert len(rashi_members) == 12
