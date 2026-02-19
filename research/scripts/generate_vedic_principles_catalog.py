#!/usr/bin/env python3
"""Generate shared Vedic principles catalog for all reports."""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "src" / "vedic_astrology_core" / "principles" / "catalog.py"

spec = importlib.util.spec_from_file_location("vedic_principles_catalog", CATALOG_PATH)
module = importlib.util.module_from_spec(spec)
if spec and spec.loader:
    spec.loader.exec_module(module)
else:
    raise SystemExit(f"Unable to import catalog module from {CATALOG_PATH}")

OUT_PATH = ROOT / "data" / "vedic_principles_catalog.csv"

path = module.write_vedic_principles_catalog(OUT_PATH)
print(f"Wrote {path}")
