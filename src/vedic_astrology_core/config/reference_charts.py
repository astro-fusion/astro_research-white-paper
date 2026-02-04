"""Shared reference charts for mundane and global analyses."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ReferenceChart:
    key: str
    name: str
    datetime: datetime
    latitude: float
    longitude: float
    timezone: str
    description: str


def get_reference_charts() -> dict:
    """Return the default reference charts catalog."""
    india_tz = ZoneInfo("Asia/Kolkata")
    utc = timezone.utc

    charts = {
        "india_independence": ReferenceChart(
            key="india_independence",
            name="India Independence Chart",
            datetime=datetime(1947, 8, 15, 0, 0, 0, tzinfo=india_tz),
            latitude=28.6139,
            longitude=77.1025,
            timezone="Asia/Kolkata",
            description="Mundane reference chart for India (Independence).",
        ),
        "nepal_constitution_2015": ReferenceChart(
            key="nepal_constitution_2015",
            name="Nepal Constitution Chart (2015)",
            datetime=datetime(2015, 9, 20, 0, 0, 0, tzinfo=ZoneInfo("Asia/Kathmandu")),
            latitude=27.7172,
            longitude=85.3240,
            timezone="Asia/Kathmandu",
            description="Mundane reference chart for Nepal (2015 Constitution).",
        ),
        "global_baseline_2000": ReferenceChart(
            key="global_baseline_2000",
            name="Global Baseline 2000-01-01",
            datetime=datetime(2000, 1, 1, 0, 0, 0, tzinfo=utc),
            latitude=0.0,
            longitude=0.0,
            timezone="UTC",
            description="Global baseline chart aligned to dataset start.",
        ),
    }
    return charts


def get_reference_chart(key: str) -> ReferenceChart:
    charts = get_reference_charts()
    if key not in charts:
        raise KeyError(f"Unknown reference chart key: {key}")
    return charts[key]
