#!/usr/bin/env python3
"""Compute personal numerology metrics from birth data (optional)."""
from pathlib import Path
import pandas as pd
from datetime import datetime

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "births.csv"
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "personal_numerology_metrics.csv"

if not DATA_PATH.exists():
    print(f"Birth dataset not found at {DATA_PATH}. Skipping personal metrics.")
    raise SystemExit(0)

births = pd.read_csv(DATA_PATH)
if "birth_date" not in births.columns:
    raise SystemExit("births.csv must contain 'birth_date' column (YYYY-MM-DD)")

MASTER = {11, 22, 33}

def digital_root(n: int, preserve_master: bool = True) -> int:
    if preserve_master and n in MASTER:
        return n
    return (n - 1) % 9 + 1 if n > 0 else 0

rows = []
for _, row in births.iterrows():
    b = str(row["birth_date"])[:10]
    dt = datetime.strptime(b, "%Y-%m-%d")
    digits = [int(c) for c in dt.strftime("%Y%m%d")]
    life_path = digital_root(sum(digits))

    # Pinnacles (classic method)
    month = digital_root(dt.month)
    day = digital_root(dt.day)
    year = digital_root(dt.year)
    pin1 = digital_root(month + day)
    pin2 = digital_root(day + year)
    pin3 = digital_root(pin1 + pin2)
    pin4 = digital_root(month + year)

    # Challenges
    ch1 = abs(month - day)
    ch2 = abs(day - year)
    ch3 = abs(ch1 - ch2)
    ch4 = abs(month - year)

    rows.append({
        "birth_date": b,
        "life_path": life_path,
        "pinnacle_1": pin1,
        "pinnacle_2": pin2,
        "pinnacle_3": pin3,
        "pinnacle_4": pin4,
        "challenge_1": ch1,
        "challenge_2": ch2,
        "challenge_3": ch3,
        "challenge_4": ch4,
    })

pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
print(f"Wrote {OUT_PATH} with {len(rows)} rows")
