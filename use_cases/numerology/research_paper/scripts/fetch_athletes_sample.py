#!/usr/bin/env python3
"""Fetch athlete dataset and create sampled names/births files."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

URL = "https://raw.githubusercontent.com/stat408/Data/main/athletes%20new.csv"
SAMPLE_N = 500
SEED = 42

out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)

athletes_path = out_dir / "athletes_sample.csv"
names_path = out_dir / "names.csv"
births_path = out_dir / "births.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch athlete dataset sample.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-download and resample even if cached files exist.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not attempt network access; require cached files.",
    )
    return parser.parse_args()


def cached_files_exist() -> bool:
    return athletes_path.exists() and names_path.exists() and births_path.exists()


def ensure_cached_or_exit(offline: bool) -> None:
    if cached_files_exist():
        print(f"Using cached athletes data in {out_dir}")
        raise SystemExit(0)
    if offline:
        raise SystemExit("Offline mode enabled but no cached athlete files found.")


def main() -> None:
    args = parse_args()
    if not args.refresh:
        ensure_cached_or_exit(args.offline)

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
    athletes_sample.rename(columns={name_col: "name", birth_col: "birth_date"}).to_csv(
        athletes_path, index=False
    )

    athletes_sample[[name_col]].rename(columns={name_col: "name"}).to_csv(
        names_path, index=False
    )
    athletes_sample[[birth_col]].rename(columns={birth_col: "birth_date"}).to_csv(
        births_path, index=False
    )

    print(f"Wrote athletes_sample.csv, names.csv, births.csv in {out_dir}")


if __name__ == "__main__":
    main()
