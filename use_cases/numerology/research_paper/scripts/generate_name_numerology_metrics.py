#!/usr/bin/env python3
"""Compute name-based numerology metrics (Pythagorean + Chaldean)."""
from pathlib import Path
import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "names.csv"
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "name_numerology_metrics.csv"

if not DATA_PATH.exists():
    print(f"Name dataset not found at {DATA_PATH}. Skipping name-based metrics.")
    raise SystemExit(0)

names_df = pd.read_csv(DATA_PATH)
if "name" not in names_df.columns:
    raise SystemExit("names.csv must contain a 'name' column")

# Mapping tables
PYTH_MAP = {
    **{c: 1 for c in "AJS"},
    **{c: 2 for c in "BKT"},
    **{c: 3 for c in "CLU"},
    **{c: 4 for c in "DMV"},
    **{c: 5 for c in "ENW"},
    **{c: 6 for c in "FOX"},
    **{c: 7 for c in "GPY"},
    **{c: 8 for c in "HQZ"},
    **{c: 9 for c in "IR"},
}

CHAL_MAP = {
    **{c: 1 for c in "AIJQY"},
    **{c: 2 for c in "BKR"},
    **{c: 3 for c in "CGLS"},
    **{c: 4 for c in "DMT"},
    **{c: 5 for c in "EHNX"},
    **{c: 6 for c in "UVW"},
    **{c: 7 for c in "OZ"},
    **{c: 8 for c in "FP"},
}

VOWELS = set("AEIOUY")

MASTER = {11,22,33}


def digital_root(n: int, preserve_master: bool = True) -> int:
    if preserve_master and n in MASTER:
        return n
    return (n - 1) % 9 + 1 if n > 0 else 0


def name_value(name: str, mapping: dict) -> int:
    total = 0
    for ch in name.upper():
        if ch.isalpha():
            total += mapping.get(ch, 0)
    return total


def soul_urge(name: str, mapping: dict) -> int:
    total = 0
    for ch in name.upper():
        if ch.isalpha() and ch in VOWELS:
            total += mapping.get(ch, 0)
    return total


def personality(name: str, mapping: dict) -> int:
    total = 0
    for ch in name.upper():
        if ch.isalpha() and ch not in VOWELS:
            total += mapping.get(ch, 0)
    return total

rows = []
for name in names_df["name"].astype(str):
    py_val = name_value(name, PYTH_MAP)
    ch_val = name_value(name, CHAL_MAP)

    row = {
        "name": name,
        "pyth_expression": digital_root(py_val),
        "chald_expression": digital_root(ch_val),
        "pyth_soul_urge": digital_root(soul_urge(name, PYTH_MAP)),
        "chald_soul_urge": digital_root(soul_urge(name, CHAL_MAP)),
        "pyth_personality": digital_root(personality(name, PYTH_MAP)),
        "chald_personality": digital_root(personality(name, CHAL_MAP)),
    }
    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(OUT_PATH, index=False)
print(f"Wrote {OUT_PATH} with {len(out)} rows")
