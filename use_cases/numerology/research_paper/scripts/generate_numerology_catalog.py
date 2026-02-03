#!/usr/bin/env python3
"""Generate exhaustive numerology principles catalog."""
from pathlib import Path
import pandas as pd

# Core principle sets
NUMBERS = list(range(1, 10))
MASTER = [11, 22, 33]
KARMIC_DEBT = [13, 14, 16, 19]
COMPOUND = list(range(1, 100))

# Lo Shu grid positions (traditional)
LOSHU_POS = {
    1: (3,1), 2: (1,3), 3: (2,3),
    4: (1,2), 5: (2,2), 6: (3,2),
    7: (1,1), 8: (2,1), 9: (3,3)
}

# Vedic number-planet mapping (Mulanka / Bhagyanka)
VEDIC_PLANETS = {
    1: 'Sun', 2: 'Moon', 3: 'Jupiter', 4: 'Rahu', 5: 'Mercury',
    6: 'Venus', 7: 'Ketu', 8: 'Saturn', 9: 'Mars'
}

PYTH_LETTERS = {
    1: "AJS", 2: "BKT", 3: "CLU", 4: "DMV", 5: "ENW",
    6: "FOX", 7: "GPY", 8: "HQZ", 9: "IR"
}

CHAL_LETTERS = {
    1: "AIJQY", 2: "BKR", 3: "CGLS", 4: "DMT", 5: "EHNX",
    6: "UVW", 7: "OZ", 8: "FP"
}

rows = []

def add(category, rule, parameters=None, **fields):
    combo_id = f"{category}:{len(rows)+1:06d}"
    row = {
        "combo_id": combo_id,
        "category": category,
        "rule": rule,
        "parameters": parameters or "",
    }
    row.update(fields)
    rows.append(row)

# Lo Shu grid principles
for n, pos in LOSHU_POS.items():
    add("lo_shu", f"Lo Shu position for {n}", f"pos={pos}", number=n)

# Missing number analysis (1-9)
for n in NUMBERS:
    add("missing_number", f"Missing number {n}", "count=0", number=n)

# Repeated number (1-9)
for n in NUMBERS:
    for count in [2,3,4,5]:
        add("repetition", f"Number {n} repeated {count} times", f"count={count}", number=n, count=count)

# Master numbers
for n in MASTER:
    add("master_number", f"Master number {n}", "preserve_master=true", number=n)

# Karmic debt
for n in KARMIC_DEBT:
    add("karmic_debt", f"Karmic debt {n}", "special_reduction=true", number=n)

# Compound numbers (1-99)
for n in COMPOUND:
    add("compound_number", f"Compound number {n}", "compound_meaning", number=n)

# Life path / destiny / expression / soul urge / personality / maturity / balance
add("personal_number", "Life Path", "birth date reduction")
add("personal_number", "Destiny / Expression", "full name reduction")
add("personal_number", "Soul Urge", "vowels only")
add("personal_number", "Personality", "consonants only")
add("personal_number", "Maturity", "life path + destiny")
add("personal_number", "Balance", "initials reduction")

# Pinnacles and Challenges
for i in range(1, 5):
    add("pinnacle", f"Pinnacle {i}", "derived from birth month/day/year")
    add("challenge", f"Challenge {i}", "derived from birth month/day/year")

# Karmic lessons / hidden passion (missing or dominant numbers)
for n in NUMBERS:
    add("karmic_lesson", f"Karmic lesson {n}", "missing from name")
    add("hidden_passion", f"Hidden passion {n}", "dominant in name")

# Vedic numerology mapping
for n, p in VEDIC_PLANETS.items():
    add("vedic_mapping", f"Vedic number {n} maps to {p}", "mulanka/bhagyanka", number=n, planet=p)

# Pythagorean name numerology mapping
for n, letters in PYTH_LETTERS.items():
    add("pythagorean_mapping", f"Pythagorean letters for {n}", f"letters={letters}", number=n)

# Chaldean name numerology mapping
for n, letters in CHAL_LETTERS.items():
    add("chaldean_mapping", f"Chaldean letters for {n}", f"letters={letters}", number=n)

# Date-based transits (day number, month number, year number)
for n in NUMBERS:
    add("transit_day", f"Universal Day Number = {n}", "date reduction", number=n)
    add("transit_month", f"Universal Month Number = {n}", "month reduction", number=n)
    add("transit_year", f"Universal Year Number = {n}", "year reduction", number=n)

out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)
cat_path = out_dir / "numerology_catalog.csv"
pd.DataFrame(rows).to_csv(cat_path, index=False)
print(f"Wrote {cat_path} with {len(rows)} rows")
