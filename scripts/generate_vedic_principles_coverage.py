#!/usr/bin/env python3
"""Generate cross-report coverage matrix for Vedic principles."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "vedic_principles_catalog.csv"
OUT_PATH = ROOT / "data" / "vedic_principles_coverage.csv"

REPORT_KEYS = ["numerology", "earthquake", "gold"]

REPORT_COMPUTED_FAMILIES = {
    "numerology": {
        "graha",
        "nakshatra",
        "rashi",
        "dignity",
    },
    "earthquake": {
        "drishti",
        "graha_yuddha",
        "combustion",
        "retrograde",
        "shadbala",
        "dasha",
        "bhava",
        "rashi",
        "nakshatra",
        "tithi",
        "karana",
        "yoga",
        "syzygy",
        "eclipse",
        "graha",
    },
    "gold": {
        "drishti",
        "combustion",
        "retrograde",
        "dasha",
        "rashi",
        "nakshatra",
        "syzygy",
        "eclipse",
        "graha",
    },
}

REPORT_DOCUMENTED_FAMILIES = {
    "numerology": {"tithi", "karana", "yoga", "bhava", "gocara", "shadbala"},
    "earthquake": {"gocara", "varga", "ashtakavarga", "arudha", "avastha", "muhurta", "upagraha", "kala", "yoga_classical"},
    "gold": {"gocara", "varga", "ashtakavarga", "arudha", "avastha", "muhurta", "upagraha", "kala", "yoga_classical"},
}

if not MASTER_PATH.exists():
    raise SystemExit(f"Missing master catalog: {MASTER_PATH}. Run generate_vedic_principles_catalog.py")

master = pd.read_csv(MASTER_PATH)
rows = []

for report in REPORT_KEYS:
    computed = REPORT_COMPUTED_FAMILIES.get(report, set())
    documented = REPORT_DOCUMENTED_FAMILIES.get(report, set())

    for _, row in master.iterrows():
        family = row["family"]
        if family in computed:
            status = "computed"
        elif family in documented:
            status = "documented"
        else:
            status = "not_included"

        rows.append({
            "report": report,
            "principle_id": row["principle_id"],
            "family": row["family"],
            "item_type": row["item_type"],
            "name": row["name"],
            "scope": row["scope"],
            "computable": bool(row["computable"]),
            "coverage_status": status,
        })

coverage = pd.DataFrame(rows)
coverage.to_csv(OUT_PATH, index=False)
print(f"Wrote {OUT_PATH} with {len(coverage)} rows")
