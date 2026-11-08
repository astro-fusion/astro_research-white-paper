"""Mundane pipeline: validate -> features -> table -> summary -> stats stub.

Usage::

    python studies/mundane/scripts/pipeline.py --seed 42 --limit 50

Each event is paired with the country named by its ``country_iso`` when that
country is in ``countries.yaml``; the others are counted as skipped. Event
times are not recorded, so features are computed at local noon of the event
date. Every row carries the ``time_known`` flag of the country's natal chart.
"""

import argparse
import json
import logging
import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root
from studies.mundane.scripts import features, validate_data  # noqa: E402
from studies._paths import REPO_ROOT, artifacts_dir  # noqa: E402
from studies.mundane.scripts.validate_data import (  # noqa: E402
    COUNTRIES_FILE, EVENTS_FILE,
)

log = logging.getLogger("mundane.pipeline")


def load_countries(path: Path = COUNTRIES_FILE) -> Dict[str, Dict[str, Any]]:
    """Return countries keyed by ISO code."""
    rows = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["countries"]
    return {c["iso"]: c for c in rows}


def load_events(path: Path = EVENTS_FILE) -> List[Dict[str, Any]]:
    """Return the events from a JSONL file."""
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def select_events(events: List[Dict[str, Any]], limit: Optional[int], seed: int
                  ) -> List[Dict[str, Any]]:
    """Seeded random subset (by position) when ``limit`` is set."""
    if limit is None or limit >= len(events):
        return events
    idx = sorted(random.Random(seed).sample(range(len(events)), limit))
    return [events[i] for i in idx]


def build_feature_table(events: List[Dict[str, Any]],
                        countries: Dict[str, Dict[str, Any]],
                        window_days: int) -> tuple:
    """Return ``(rows, skipped)`` feature rows and the skipped-event count."""
    engine = features.get_engine()
    natal_cache: Dict[str, Dict[str, Any]] = {}
    rows: List[Dict[str, Any]] = []
    skipped = Counter()
    for ev in events:
        country = countries.get(ev.get("country_iso"))
        if country is None:
            skipped["no_country_in_countries_yaml"] += 1
            continue
        iso = country["iso"]
        if iso not in natal_cache:
            natal_cache[iso] = features.natal_chart(country, engine)
        try:
            day = date.fromisoformat(ev["date"])
            when = features.local_datetime(day, country["timezone"])
        except (ValueError, OverflowError):
            skipped["bad_date"] += 1
            continue
        for row in features.moment_features(
            country, when, window_days=window_days, natal=natal_cache[iso],
            engine=engine,
        ):
            row.update(event_id=ev["id"], event_title=ev["title"],
                       event_date=ev["date"], event_type=ev["event_type"])
            rows.append(row)
    return rows, skipped


def write_table(df: pd.DataFrame, out_dir: Path) -> str:
    """Write Parquet if pyarrow is installed, otherwise CSV; return the format."""
    try:
        import pyarrow  # noqa: F401
        df.to_parquet(out_dir / "features.parquet", index=False)
        return "parquet"
    except ImportError:
        df.to_csv(out_dir / "features.csv", index=False)
        return "csv"


def run_stats_stub() -> str:
    """Statistical step placeholder: the stats module is written elsewhere."""
    try:
        import vedic_astrology_core.stats  # noqa: F401
    except ImportError:
        log.info("stats module pending")
        return "pending"
    log.info("stats module found; testing is not wired until hypothesis.yaml "
             "is final and has sourced founding times")
    return "available_not_wired"


def run(seed: int = 42, limit: Optional[int] = None, window_days: int = 30,
        out_dir: Optional[Path] = None, events_path: Path = EVENTS_FILE,
        countries_path: Path = COUNTRIES_FILE) -> Dict[str, Any]:
    """Run the pipeline and return the summary dictionary."""
    libs = str(REPO_ROOT / "libs")
    if libs not in sys.path:
        sys.path.insert(0, libs)
    random.seed(seed)
    np.random.seed(seed)
    out_dir = Path(out_dir or artifacts_dir("mundane"))
    out_dir.mkdir(parents=True, exist_ok=True)

    problems = (validate_data.validate_countries(countries_path)
                + validate_data.validate_events(events_path, countries_path))
    if problems:
        raise SystemExit("validation failed:\n" + "\n".join(problems[:20]))

    countries = load_countries(countries_path)
    events = select_events(load_events(events_path), limit, seed)
    rows, skipped = build_feature_table(events, countries, window_days)
    df = pd.DataFrame(rows)
    fmt = write_table(df, out_dir)
    summary = {
        "seed": seed, "limit": limit, "window_days": window_days,
        "countries": len(countries), "events_selected": len(events),
        "events_featured": int(df["event_id"].nunique()) if len(df) else 0,
        "events_skipped": dict(skipped), "feature_rows": len(df),
        "rows_by_family": dict(Counter(df["family"])) if len(df) else {},
        "events_by_type": dict(Counter(e["event_type"] for e in events)),
        "rows_time_known_false": int((~df["time_known"]).sum()) if len(df) else 0,
        "table_format": fmt, "stats": run_stats_stub(),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limit", type=int, default=None, help="seeded event subset")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    summary = run(args.seed, args.limit, args.window_days, args.out_dir)
    log.info(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
