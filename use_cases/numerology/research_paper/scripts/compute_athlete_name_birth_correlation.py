#!/usr/bin/env python3
"""Compute correlation between name-based numerology and birth numerology for athletes."""
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
athletes = pd.read_csv(DATA_DIR / "athletes_sample.csv")

# Normalize columns
athletes.columns = [c.strip().lower() for c in athletes.columns]
if "name" not in athletes.columns or "birth_date" not in athletes.columns:
    raise SystemExit("athletes_sample.csv must include name and birth_date")

# Mapping tables
PYTH_MAP = {
    **{c: 1 for c in "AJS"}, **{c: 2 for c in "BKT"}, **{c: 3 for c in "CLU"},
    **{c: 4 for c in "DMV"}, **{c: 5 for c in "ENW"}, **{c: 6 for c in "FOX"},
    **{c: 7 for c in "GPY"}, **{c: 8 for c in "HQZ"}, **{c: 9 for c in "IR"},
}
CHAL_MAP = {
    **{c: 1 for c in "AIJQY"}, **{c: 2 for c in "BKR"}, **{c: 3 for c in "CGLS"},
    **{c: 4 for c in "DMT"}, **{c: 5 for c in "EHNX"}, **{c: 6 for c in "UVW"},
    **{c: 7 for c in "OZ"}, **{c: 8 for c in "FP"},
}
MASTER = {11,22,33}
VOWELS = set("AEIOUY")
VEDIC_PLANETS = {1:"Sun",2:"Moon",3:"Jupiter",4:"Rahu",5:"Mercury",6:"Venus",7:"Ketu",8:"Saturn",9:"Mars"}


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

rows = []
for _, row in athletes.iterrows():
    name = str(row["name"])
    b = str(row["birth_date"])[:10]

    # Life Path
    digits = [int(c) for c in b.replace("-", "") if c.isdigit()]
    life_path = digital_root(sum(digits)) if digits else None

    # Name Expression
    pyth_expr = digital_root(name_value(name, PYTH_MAP))
    chald_expr = digital_root(name_value(name, CHAL_MAP))

    rows.append({
        "name": name,
        "birth_date": b,
        "life_path": life_path,
        "pyth_expression": pyth_expr,
        "chald_expression": chald_expr,
        "life_path_planet": VEDIC_PLANETS.get(life_path),
        "pyth_planet": VEDIC_PLANETS.get(pyth_expr if pyth_expr <= 9 else None),
        "chald_planet": VEDIC_PLANETS.get(chald_expr if chald_expr <= 9 else None),
    })

out = pd.DataFrame(rows)
out.to_csv(DATA_DIR / "athlete_name_birth_metrics.csv", index=False)

# Contingency tables
ct_pyth = pd.crosstab(out["life_path"], out["pyth_expression"])
ct_chald = pd.crosstab(out["life_path"], out["chald_expression"])

# Cramer's V

def cramers_v(ct):
    n = ct.values.sum()
    if n == 0:
        return 0
    row_sums = ct.sum(axis=1).values.reshape(-1,1)
    col_sums = ct.sum(axis=0).values.reshape(1,-1)
    expected = row_sums @ col_sums / n
    chi2 = ((ct.values - expected) ** 2 / expected).sum()
    k = min(ct.shape) - 1
    return np.sqrt(chi2 / (n * k)) if k > 0 else 0

summary = pd.DataFrame([
    {"metric":"cramers_v_pyth", "value": cramers_v(ct_pyth)},
    {"metric":"cramers_v_chald", "value": cramers_v(ct_chald)},
])
summary.to_csv(DATA_DIR / "athlete_name_birth_correlation.csv", index=False)

print("Wrote athlete_name_birth_metrics.csv and athlete_name_birth_correlation.csv")
