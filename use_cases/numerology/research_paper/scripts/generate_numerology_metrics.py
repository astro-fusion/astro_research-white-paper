#!/usr/bin/env python3
"""Generate daily numerology metrics and pattern frequencies for a date range."""
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

START = date(2024, 1, 1)
END = date(2024, 12, 31)

# Numerology helpers

def digital_root(n: int) -> int:
    return (n - 1) % 9 + 1 if n > 0 else 0

rows = []
cur = START
while cur <= END:
    day = cur.day
    month = cur.month
    year = cur.year
    udn = digital_root(day + month + sum(int(c) for c in str(year)))
    umn = digital_root(month + sum(int(c) for c in str(year)))
    uyn = digital_root(sum(int(c) for c in str(year)))

    # Count digits in YYYYMMDD for Lo Shu / missing number analysis
    datestr = cur.strftime('%Y%m%d')
    counts = {str(i): datestr.count(str(i)) for i in range(1, 10)}

    row = {
        'date': cur.isoformat(),
        'udn': udn,
        'umn': umn,
        'uyn': uyn,
    }
    for i in range(1, 10):
        row[f'count_{i}'] = counts[str(i)]
        row[f'missing_{i}'] = 1 if counts[str(i)] == 0 else 0
    rows.append(row)
    cur += timedelta(days=1)

out_dir = Path(__file__).resolve().parents[1] / 'data'
out_dir.mkdir(parents=True, exist_ok=True)
metric_path = out_dir / 'numerology_daily_metrics.csv'

pd.DataFrame(rows).to_csv(metric_path, index=False)
print(f"Wrote {metric_path} with {len(rows)} rows")
