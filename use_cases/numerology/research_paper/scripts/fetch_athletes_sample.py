#!/usr/bin/env python3
"""Fetch athlete dataset and create sampled names/births files."""
from pathlib import Path
import pandas as pd

URL = "https://raw.githubusercontent.com/stat408/Data/main/athletes%20new.csv"
SAMPLE_N = 500
SEED = 42

out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)

# Load data
athletes = pd.read_csv(URL)

# Normalize column names
athletes.columns = [c.strip().lower() for c in athletes.columns]

# Guess key columns
name_col = None
for cand in ["name", "athlete", "athlete_name", "full_name"]:
    if cand in athletes.columns:
        name_col = cand
        break

birth_col = None
for cand in ["birth_date", "birthdate", "dob", "date_of_birth"]:
    if cand in athletes.columns:
        birth_col = cand
        break

if name_col is None or birth_col is None:
    raise SystemExit(f"Missing name/birth columns. Columns: {athletes.columns}")

# Keep required columns
keep_cols = [name_col, birth_col]
for extra in ["sport", "country", "country_code", "country_full"]:
    if extra in athletes.columns:
        keep_cols.append(extra)

athletes = athletes[keep_cols].dropna(subset=[name_col, birth_col])

# Sample
athletes_sample = athletes.sample(n=min(SAMPLE_N, len(athletes)), random_state=SEED)

# Write files
athletes_sample.rename(columns={name_col: "name", birth_col: "birth_date"}).to_csv(out_dir / "athletes_sample.csv", index=False)

athletes_sample[[name_col]].rename(columns={name_col: "name"}).to_csv(out_dir / "names.csv", index=False)
athletes_sample[[birth_col]].rename(columns={birth_col: "birth_date"}).to_csv(out_dir / "births.csv", index=False)

print(f"Wrote athletes_sample.csv, names.csv, births.csv in {out_dir}")
