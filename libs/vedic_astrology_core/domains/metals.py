"""Metals adapter: gold and silver (ADR-007 section 4.2, WP-76; ADR-008 D-01, D-02, A-05, A-06).

One interface over three kinds of price series. Each series is named by metal,
currency and market, and every outcome id carries all three (ADR-008 A-06):

========================  ======  ==========================================  =====
series id                 freq    source (snapshot)                           grade
========================  ======  ==========================================  =====
gold_dem_frankfurt        daily   Bundesbank BBEX3 D.XAU.DEM.EA.AC.C01        A/B
gold_usd_pinksheet        month   World Bank Pink Sheet, Gold column          A/B
silver_usd_pinksheet      month   World Bank Pink Sheet, Silver column        A/B
gold_usd_comex            daily   Yahoo GC=F front-month futures              C
silver_usd_comex          daily   Yahoo SI=F front-month futures              C
========================  ======  ==========================================  =====

Grades A/B are computed by :func:`.base.compute_grade` from the snapshot index,
the licence register and `data/registry/dataset_grades.yaml`; nothing here
can raise a grade. The Yahoo series are forced to grade C (descriptive only,
no verdict) whatever the registers say.

Currency. The only verified daily series is the Frankfurt fixing in DEM per kg,
1968-06-18 to 1998-12-30. No verified DEM/USD series exists in the repository,
so it is **not** converted: the outcome stays in DEM and its id says so
(`gold_dem_frankfurt`). A `gold_usd` daily outcome is declared Untestable
until a verified FX series and its gap rule (ADR-008 D-02) are in the plan.

Sampling instant (the WP-76 risk). The sky is sampled at the series' own
fixing time in the fixing's own time zone, with daylight saving taken from the
IANA database (Germany had no summer time 1950 to 1979, then CEST from 1980):

* Frankfurt: 13:00 Europe/Berlin, Frankfurt am Main (project setting; the plan
  confirms it under ADR-008 D-07).
* Pink Sheet gold: the London afternoon fixing, 15:00 Europe/London, on every
  civil day of the month (the price is a monthly average of daily fixings).
* Pink Sheet silver: 12:00 Europe/London (the London silver fixing was a
  midday fix; before July 1976 the Pink Sheet used Handy and Harman, New York).
* Yahoo COMEX: 13:30 America/New_York (settlement).

A-05: the fixing instant is the market's convention, not the panchanga's.
:meth:`MetalsDomain.convention_disagreement` reports the share of grid days on
which a calendar sampled at local sunrise at the source's place differs from the
same calendar sampled at the fixing instant; for Moon rules it is large.

Gaps. Bundesbank rows with "." carry no fixing (weekends, holidays) and are
not grid days. A return is taken from the previous fixing day; a return over
more than four calendar days is flagged (`long_gap`), never silently merged.

Outcomes are past-only: the standardised absolute return uses
:func:`..stats.volatility.past_only_volatility` (fitted on bars before t), and
the extreme-move flag compares |r_t| with the 95th percentile of |r| over
bars before t. Baselines come from :mod:`..markets.baselines` (calendar terms
with the series' own holidays) and :mod:`..markets.festivals` (only after the
D-09 spot-check passes). Lunar-phase terms are not used as baselines: they are
astrological calendars themselves. GARCH-X is not run here; where a plan uses
it, it is secondary (ADR-008 S-16).

Monthly data (D-01): the unit is the month; a month is active when the daily
calendar is active on at least half of its days (:func:`month_active`);
`guard_bars` is 1. A monthly result is never a cross-check of a daily one.

Past data only. Nothing here forecasts.
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ..markets import align as _align
from ..stats.manifest import file_sha256
from .base import (
    DatasetSpec,
    DomainAdapter,
    DomainDataset,
    Periods,
    festival_spotcheck_problems,
)

REPO = Path(__file__).resolve().parents[3]

#: A return over more than this many calendar days is flagged (WP-76).
LONG_GAP_DAYS = 4
#: Two-tier gold market (official 35 USD price beside the free market), from the
#: London closure of March 1968 to the end of dollar convertibility, 15 Aug 1971.
TWO_TIER = (date(1968, 3, 17), date(1971, 8, 15))
#: The Pink Sheet gold price was officially fixed before April 1968 (ADR-007 4.2).
MONTHLY_FIRST_PRICE = "1968-04"
EXTREME_QUANTILE = 0.95
MIN_TRAIN = 500


class PinError(RuntimeError):
    """The plan pins no snapshot hash, the pin is unknown, or the bytes differ."""


@dataclass(frozen=True)
class Place:
    """A fixing or source place: latitude, longitude (east positive), IANA zone."""

    name: str
    lat: float
    lon: float
    tz: str


FRANKFURT = Place("Frankfurt am Main", 50.1109, 8.6821, "Europe/Berlin")
LONDON = Place("London", 51.5074, -0.1278, "Europe/London")
NEW_YORK = Place("New York", 40.7128, -74.0060, "America/New_York")
DELHI = Place("New Delhi", 28.6139, 77.2090, "Asia/Kolkata")


@dataclass(frozen=True)
class SeriesSpec:
    """One price series: what it is, where and when it is fixed."""

    id: str
    metal: str
    currency: str
    market: str
    freq: str  # "daily" | "monthly"
    source_id: str
    unit: str
    fixing_time: str  # local HH:MM in place.tz
    place: Place
    fixing_fixed_by: str
    reader: str  # "bundesbank" | "pinksheet" | "yahoo"
    column: Optional[str] = None
    explore_end: date = date(1986, 12, 31)
    confirm_start: date = date(1987, 1, 1)
    pseudo_out_of_sample: bool = False
    force_grade_c: Optional[str] = None
    market_sentence: str = ""
    notes: Tuple[str, ...] = ()


SERIES: Dict[str, SeriesSpec] = {
    "gold_dem_frankfurt": SeriesSpec(
        id="gold_dem_frankfurt", metal="gold", currency="dem", market="frankfurt",
        freq="daily", source_id="bundesbank_gold", unit="DEM per kg",
        fixing_time="13:00", place=FRANKFURT,
        fixing_fixed_by="project (to be confirmed in the domain plan, ADR-008 D-07)",
        reader="bundesbank",
        explore_end=date(1986, 12, 31), confirm_start=date(1987, 1, 1),
        market_sentence="tested on the Frankfurt fixing in DEM",
        notes=(
            "Frankfurt gold fixing in DEM per kg, 1968-06-18 to 1998-12-30 only; "
            "modern daily gold is not tested.",
            "Prices in German marks: daily changes mix gold with the DEM exchange rate "
            "(1969 revaluation, 1971 float). No verified DEM/USD series exists, so no USD outcome.",
            "Sky sampled at 13:00 Frankfurt local time (CET/CEST); the fixing time is a "
            "project setting until the plan confirms it (D-07).",
            "Two-tier gold market until 1971-08-15 (flag two_tier).",
        ),
    ),
    "gold_usd_pinksheet": SeriesSpec(
        id="gold_usd_pinksheet", metal="gold", currency="usd", market="pinksheet",
        freq="monthly", source_id="worldbank_pinksheet",
        unit="USD per troy ounce, monthly average",
        fixing_time="15:00", place=LONDON,
        fixing_fixed_by="source (London afternoon fixing, average of daily rates)",
        reader="pinksheet", column="Gold",
        explore_end=date(1999, 12, 31), confirm_start=date(2000, 1, 1),
        pseudo_out_of_sample=True,
        market_sentence="tested on the World Bank monthly average of the London gold fixing in USD",
        notes=(
            "Monthly averages of daily London afternoon fixings: the unit is the month, "
            "neighbouring returns are correlated, guard_bars 1.",
            "Used from 1968-04; the price was officially fixed before.",
            "From June 2025 the Pink Sheet gold price is a spot average, not the London fixing.",
            "Monthly gold and silver from 2000 were looked at in an earlier study.",
        ),
    ),
    "silver_usd_pinksheet": SeriesSpec(
        id="silver_usd_pinksheet", metal="silver", currency="usd", market="pinksheet",
        freq="monthly", source_id="worldbank_pinksheet",
        unit="USD per troy ounce, monthly average",
        fixing_time="12:00", place=LONDON,
        fixing_fixed_by="project (London silver fixing was a midday fix)",
        reader="pinksheet", column="Silver",
        explore_end=date(1999, 12, 31), confirm_start=date(2000, 1, 1),
        pseudo_out_of_sample=True,
        market_sentence="tested on the World Bank monthly average of silver prices in USD",
        notes=(
            "Monthly averages: the unit is the month, guard_bars 1.",
            "Before July 1976 the Pink Sheet silver price is Handy and Harman (New York), "
            "then the London fixing: a series splice.",
            "Used from 1968-04, the same start as monthly gold.",
            "Monthly gold and silver from 2000 were looked at in an earlier study.",
        ),
    ),
    "gold_usd_comex": SeriesSpec(
        id="gold_usd_comex", metal="gold", currency="usd", market="comex",
        freq="daily", source_id="yahoo_finance",
        unit="USD per troy ounce (front-month futures)",
        fixing_time="13:30", place=NEW_YORK, fixing_fixed_by="project (COMEX settlement)",
        reader="yahoo", explore_end=date(2012, 12, 31), confirm_start=date(2013, 1, 1),
        pseudo_out_of_sample=True,
        force_grade_c="Yahoo GC=F: continuous front-month futures, not spot; unverified source (review C4)",
        market_sentence="described on COMEX gold futures in USD (descriptive only)",
    ),
    "silver_usd_comex": SeriesSpec(
        id="silver_usd_comex", metal="silver", currency="usd", market="comex",
        freq="daily", source_id="yahoo_finance",
        unit="USD per troy ounce (front-month futures)",
        fixing_time="13:30", place=NEW_YORK, fixing_fixed_by="project (COMEX settlement)",
        reader="yahoo", explore_end=date(2012, 12, 31), confirm_start=date(2013, 1, 1),
        pseudo_out_of_sample=True,
        force_grade_c="Yahoo SI=F: continuous front-month futures, median volume 53 contracts (review C4)",
        market_sentence="described on COMEX silver futures in USD (descriptive only)",
    ),
}

#: Outcomes declared but not testable on the committed data.
UNTESTABLE = {
    "gold_usd_frankfurt.log_return": "no verified DEM/USD series in the repository (ADR-008 D-02)",
    "silver_usd_daily": "no verified daily silver series (Yahoo SI=F is grade C)",
}


# ------------------------------------------------------------------ readers
_ROW = re.compile(r"^(\d{4}-\d{2}-\d{2});([^;]*);")


def parse_bundesbank(text: str) -> pd.Series:
    """Fixings of a Bundesbank BBEX3 CSV: Series of floats on fixing dates.

    Rows with "." (no fixing) are left out; any other non-number raises.
    """
    dates, values = [], []
    for line in text.lstrip("﻿").splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        v = m.group(2).strip()
        if not v or v == ".":
            continue
        try:
            values.append(float(v))
        except ValueError:
            raise ValueError(f"unexpected Bundesbank value: {line[:60]!r}") from None
        dates.append(m.group(1))
    if not dates:
        raise ValueError("Bundesbank file has no fixing")
    idx = pd.DatetimeIndex(pd.to_datetime(dates), name="date")
    if not idx.is_monotonic_increasing or idx.has_duplicates:
        raise ValueError("Bundesbank dates are not strictly increasing")
    return pd.Series(values, index=idx, name="price")


_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _xlsx_rows(content: bytes, sheet_name: str) -> List[Dict[str, str]]:
    """Rows of one sheet as {column letter: text}; stdlib only (no openpyxl)."""
    z = zipfile.ZipFile(io.BytesIO(content))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    target = None
    for s in wb.find(f"{_NS}sheets"):
        if s.get("name") == sheet_name:
            target = rels[s.get(_RID)]
    if target is None:
        raise ValueError(f"sheet {sheet_name!r} not in the workbook")
    shared: List[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        shared = ["".join(t.text or "" for t in si.iter(f"{_NS}t"))
                  for si in ET.fromstring(z.read("xl/sharedStrings.xml"))]
    sheet = ET.fromstring(z.read("xl/" + target.lstrip("/").replace("xl/", "", 1)))
    rows = []
    for row in sheet.find(f"{_NS}sheetData"):
        cells = {}
        for c in row:
            v = c.find(f"{_NS}v")
            if v is None:
                continue
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            cells[col] = shared[int(v.text)] if c.get("t") == "s" else (v.text or "")
        rows.append(cells)
    return rows


def parse_pinksheet(content: bytes, column: str) -> pd.Series:
    """Monthly prices of one Pink Sheet column, indexed by month start."""
    rows = _xlsx_rows(content, "Monthly Prices")
    header = next((r for r in rows if column in (str(v).strip() for v in r.values())), None)
    if header is None:
        raise ValueError(f"Pink Sheet has no {column!r} column")
    col = next(k for k, v in header.items() if str(v).strip() == column)
    idx, vals = [], []
    for r in rows:
        m = re.fullmatch(r"(\d{4})M(\d{2})", str(r.get("A", "")).strip())
        if not m:
            continue
        try:
            v = float(r.get(col, ""))
        except ValueError:
            v = np.nan
        idx.append(pd.Timestamp(int(m.group(1)), int(m.group(2)), 1))
        vals.append(v)
    return pd.Series(vals, index=pd.DatetimeIndex(idx, name="month"), name="price")


def parse_yahoo(text: str) -> pd.Series:
    """Closes of a tidy Yahoo CSV (date, close, ...)."""
    df = pd.read_csv(io.StringIO(text))
    s = pd.Series(df["close"].astype(float).to_numpy(),
                  index=pd.DatetimeIndex(pd.to_datetime(df["date"]), name="date"), name="price")
    return s.dropna().sort_index()


# ------------------------------------------------------------- calendars
def fixing_instants(dates: Sequence, spec: SeriesSpec) -> pd.DatetimeIndex:
    """UTC instants of the series' fixing time, local wall clock, on each date."""
    return _align.sample_instants(dates, spec.fixing_time, spec.place.tz)


def sunrise_instants(dates: Sequence, place: Place) -> pd.DatetimeIndex:
    """UTC instants of local sunrise at `place` on each civil date."""
    from ..rules.context import Location, sunrise_before

    loc = Location(place.lat, place.lon, place.tz)
    zone = ZoneInfo(place.tz)
    out = []
    for d in pd.DatetimeIndex(pd.to_datetime(list(dates))):
        noon = datetime.combine(d.date(), time(12, 0), tzinfo=zone)
        rise = sunrise_before(noon, loc)
        if rise is None:
            raise ValueError(f"no sunrise at {place.name} on {d.date()}")
        out.append(pd.Timestamp(rise).tz_convert("UTC"))
    return pd.DatetimeIndex(out)


def month_active(daily_active: pd.Series, months: Sequence, min_share: float = 0.5) -> pd.Series:
    """ADR-008 D-01: a month is active when active on at least half its days.

    `daily_active` is a boolean series on civil days (every day of each
    month); `months` are the month starts of the monthly grid.
    """
    s = pd.Series(daily_active).astype(float)
    s.index = pd.DatetimeIndex(s.index).normalize()
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    share = s.groupby(s.index.to_period("M")).mean()
    per = pd.DatetimeIndex(months).to_period("M")
    missing = [str(p) for p in per if p not in share.index]
    if missing:
        raise ValueError(f"daily calendar does not cover month(s) {missing[:3]}")
    return pd.Series(share.reindex(per).to_numpy() >= min_share,
                     index=pd.DatetimeIndex(months), name="active")


def _resolve(index: Mapping[str, Any], sha: str) -> Optional[dict]:
    for e in index.get("snapshots", []):
        if e.get("sha256") == sha:
            return e
    return None


# ------------------------------------------------------------- adapter
class MetalsDomain(DomainAdapter):
    """Gold or silver prices behind one adapter; one instance per series."""

    def __init__(
        self,
        index: Mapping[str, Any],
        licences: Mapping[str, Mapping[str, Any]],
        *,
        series: str,
        pinned_sha256: Optional[str] = None,
        grades: Optional[Sequence[Mapping[str, Any]]] = None,
        periods: Optional[Periods] = None,
        vol_method: str = "garch",
        min_train: int = MIN_TRAIN,
        refit_every: int = 21,
        long_gap_days: int = LONG_GAP_DAYS,
        gold_pinned_sha256: Optional[str] = None,
    ) -> None:
        super().__init__(index, licences, grades)
        if series not in SERIES:
            raise ValueError(f"unknown metals series {series!r}; one of {sorted(SERIES)}")
        self.spec = SERIES[series]
        self.domain = self.spec.metal
        self._pinned = pinned_sha256
        self._periods = periods
        self.vol_method = vol_method
        self.min_train = int(min_train)
        self.refit_every = int(refit_every)
        self.long_gap_days = int(long_gap_days)
        self._gold_pin = gold_pinned_sha256
        self._prices: Optional[pd.Series] = None
        self._grid: Optional[pd.DatetimeIndex] = None

    # -- snapshot ------------------------------------------------------
    def snapshot_path(self) -> Path:
        """The snapshot the plan pins; no "newest snapshot" fallback (ADR-008)."""
        if not self._pinned:
            raise PinError(f"{self.spec.id}: the plan must pin the snapshot's SHA-256")
        e = _resolve(self._index, self._pinned)
        if e is None:
            raise PinError(f"pinned snapshot {self._pinned[:12]} is not in the snapshot index")
        if e.get("source_id") != self.spec.source_id:
            raise PinError(
                f"pinned snapshot {self._pinned[:12]} is from {e.get('source_id')!r}; "
                f"series {self.spec.id} needs {self.spec.source_id!r}"
            )
        path = REPO / e["file"]
        if not path.is_file():
            raise PinError(f"pinned snapshot file {e['file']} is not on disk")
        if file_sha256(path) != self._pinned:
            raise PinError(f"bytes of {e['file']} do not hash to the pinned SHA-256")
        return path

    def _raw_prices(self) -> pd.Series:
        """All prices of the pinned snapshot on their own dates."""
        if self._prices is None:
            path = self.snapshot_path()
            if self.spec.reader == "bundesbank":
                s = parse_bundesbank(path.read_text(encoding="utf-8-sig"))
            elif self.spec.reader == "pinksheet":
                s = parse_pinksheet(path.read_bytes(), self.spec.column or "")
                s = s[s.index >= pd.Timestamp(MONTHLY_FIRST_PRICE + "-01")].dropna()
                if len(s) and len(pd.date_range(s.index[0], s.index[-1], freq="MS")) != len(s):
                    raise ValueError(f"{self.spec.id}: a month inside the span has no price")
            else:
                s = parse_yahoo(path.read_text(encoding="utf-8"))
            if (s <= 0).any():
                raise ValueError(f"{self.spec.id}: non-positive price")
            self._prices = s
        return self._prices

    # -- dataset and grade ---------------------------------------------
    def dataset_spec(self) -> DatasetSpec:
        path = self.snapshot_path()
        g = self.grid()
        fmt = "%Y-%m" if self.spec.freq == "monthly" else "%Y-%m-%d"
        return DatasetSpec(
            id=f"{self.spec.id}_{self._pinned[:12]}",
            sha256=file_sha256(path),
            source_id=self.spec.source_id,
            span=(g[0].strftime(fmt), g[-1].strftime(fmt)),
            n_units=int(len(g)),
            n_events=None,
        )

    def dataset(self) -> DomainDataset:
        """Grade from the registers; a Yahoo series is always grade C."""
        ds = super().dataset()
        if self.spec.force_grade_c:
            return DomainDataset(ds.spec, "C", (self.spec.force_grade_c,) + tuple(ds.limitations))
        return ds

    def limitations(self) -> List[str]:
        """Series-level lines for the card's "Limits of this test" box."""
        return list(self.spec.notes)

    # -- outcome-free --------------------------------------------------
    def grid(self) -> pd.DatetimeIndex:
        """Return dates: fixing days (daily) or month starts (monthly).

        Built from which dates carry a price; no price value is used. The
        first price date opens the series and is not a return date.
        """
        if self._grid is None:
            self._grid = pd.DatetimeIndex(self._raw_prices().index[1:], name="date")
        return self._grid

    def gap_days(self) -> np.ndarray:
        """Calendar days spanned by each return."""
        d = self._raw_prices().index
        return (d[1:] - d[:-1]).days.to_numpy()

    def sample_instants(self) -> pd.DatetimeIndex:
        """UTC sampling instant of each daily grid date (fixing time, local zone)."""
        if self.spec.freq != "daily":
            raise ValueError("monthly series: use daily_instants() and month_active()")
        return fixing_instants(self.grid(), self.spec)

    def daily_instants(self) -> pd.DatetimeIndex:
        """Fixing instants on every civil day of every grid month (monthly series)."""
        g = self.grid()
        days = pd.date_range(g[0], g[-1] + pd.offsets.MonthEnd(0), freq="D")
        return fixing_instants(days, self.spec)

    def calendar_context(self) -> Mapping[str, Any]:
        g = self.grid()
        dates = np.asarray(g.date)
        ctx: Dict[str, Any] = {
            "series": self.spec.id,
            "metal": self.spec.metal,
            "currency": self.spec.currency,
            "market": self.spec.market,
            "market_sentence": self.spec.market_sentence,
            "freq": self.spec.freq,
            "fixing_time": self.spec.fixing_time,
            "timezone": self.spec.place.tz,
            "place": {"name": self.spec.place.name, "lat": self.spec.place.lat,
                      "lon": self.spec.place.lon},
            "fixing_fixed_by": self.spec.fixing_fixed_by,
            "month": g.month.to_numpy(),
            "two_tier": (dates >= TWO_TIER[0]) & (dates <= TWO_TIER[1]),
        }
        if self.spec.freq == "daily":
            gaps = self.gap_days()
            ctx.update({
                "sample_instants": self.sample_instants(),
                "weekday": g.day_of_week.to_numpy(),
                "gap_days": gaps,
                "long_gap": gaps > self.long_gap_days,
                "guard_bars": 0,
            })
        else:
            ctx.update({"daily_instants": self.daily_instants(), "guard_bars": 1,
                        "month_rule": "active when active on at least half its days (D-01)"})
        return ctx

    def periods(self) -> Periods:
        if self._periods is not None:
            return self._periods
        g = self.grid()
        last = (g[-1] + pd.offsets.MonthEnd(0)) if self.spec.freq == "monthly" else g[-1]
        return Periods(
            explore=(g[0].date(), self.spec.explore_end),
            confirm=(self.spec.confirm_start, last.date()),
            pseudo_out_of_sample=self.spec.pseudo_out_of_sample,
        )

    def outcome_ids(self) -> Dict[str, str]:
        """Outcome id -> plan outcome type. Every id names metal, currency, market."""
        s = self.spec.id
        if self.spec.freq == "daily":
            return {f"{s}.log_return": "continuous", f"{s}.abs_return_std": "absolute_return",
                    f"{s}.extreme_move": "binary"}
        return {f"{s}.log_return": "continuous", f"{s}.abs_return": "absolute_return"}

    def declared_cells(self) -> Dict[str, Any]:
        """Sensitivity cells and secondary analyses this adapter declares."""
        cells: Dict[str, Any] = {
            "volatility_method": {
                "primary": self.vol_method,
                "sensitivity": [m for m in ("garch", "ewma") if m != self.vol_method],
            },
            "day_convention": {"primary": "fixing_instant",
                               "sensitivity": ["sunrise at the source's place (A-05)"]},
            "garch_x": {"role": "secondary"},
            "untestable": dict(UNTESTABLE),
        }
        if self.spec.id == "gold_dem_frankfurt":
            cells["second_dataset"] = {"id": "gold_usd_pinksheet", "role": "sensitivity"}
        return cells

    def convention_disagreement(
        self,
        evaluate: Callable[[pd.DatetimeIndex], Sequence[Any]],
        place: Place = DELHI,
        dates: Optional[Sequence] = None,
    ) -> Dict[str, Any]:
        """A-05: share of days on which sunrise and fixing-instant readings differ.

        `evaluate` maps UTC instants to calendar values (a nakshatra, a tithi,
        a yes/no). It is called at the fixing instant of each day and at local
        sunrise at `place` on the same civil date. Outcome-free.
        """
        days = pd.DatetimeIndex(self.grid() if dates is None else pd.to_datetime(list(dates)))
        a = np.asarray(evaluate(fixing_instants(days, self.spec)))
        b = np.asarray(evaluate(sunrise_instants(days, place)))
        if a.shape != b.shape or len(a) != len(days):
            raise ValueError("evaluate must return one value per instant")
        return {"share": float((a != b).mean()) if len(days) else float("nan"),
                "n_days": int(len(days)), "place": place.name,
                "fixing": f"{self.spec.fixing_time} {self.spec.place.tz}"}

    def holidays(self) -> pd.DatetimeIndex:
        """Weekdays inside the span with no price (the series' own holidays)."""
        d = self._raw_prices().index
        return pd.bdate_range(d[0], d[-1]).difference(d)

    # -- gated ---------------------------------------------------------
    def _returns(self) -> pd.Series:
        p = self._raw_prices().to_numpy()
        return pd.Series(np.log(p[1:] / p[:-1]), index=self.grid(), name="log_return")

    def _outcomes(self) -> Mapping[str, Any]:
        s = self.spec.id
        r = self._returns()
        out: Dict[str, Any] = {
            "series": s,
            "unit": self.spec.unit,
            "price": self._raw_prices().copy(),
            f"{s}.log_return": r,
        }
        gaps = self.gap_days()
        out["gap_days"] = pd.Series(gaps, index=r.index, name="gap_days")
        if self.spec.freq == "monthly":
            out[f"{s}.abs_return"] = r.abs().rename("abs_return")
            out["guard_bars"] = 1
            return out
        from ..stats.volatility import past_only_volatility

        vol = past_only_volatility(r, method=self.vol_method, min_train=self.min_train,
                                   refit_every=self.refit_every)
        out[f"{s}.abs_return_std"] = vol["z"].abs().rename("abs_return_std")
        out["volatility"] = vol
        absr = r.abs()
        thr = absr.expanding(min_periods=self.min_train).quantile(EXTREME_QUANTILE).shift(1)
        out[f"{s}.extreme_move"] = (absr > thr).astype(float).where(thr.notna()).rename("extreme_move")
        out["extreme_threshold"] = thr.rename("threshold")
        out["long_gap"] = pd.Series(gaps > self.long_gap_days, index=r.index, name="long_gap")
        out["guard_bars"] = 0
        return out

    def _controls(self) -> Mapping[str, Any]:
        from ..markets import baselines as bl

        g = self.grid()
        out: Dict[str, Any] = {}
        if self.spec.freq == "daily":
            cal = bl.calendar_terms(g, holidays=self.holidays())
        else:
            cal = pd.DataFrame(index=g)
            for m in range(2, 13):
                cal[f"month_{m:02d}"] = (g.month == m).astype(int)
        out["calendar_terms"] = cal
        problems = self._festival_problems()
        out["festival_check"] = problems
        if problems:  # D-09: no festival baseline until the spot-check passes
            out["festival_terms"] = None
            out["baselines"] = cal
            out["baselines_complete"] = False
        else:
            ff = self._festival_terms()
            out["festival_terms"] = ff
            out["baselines"] = pd.concat([cal, ff], axis=1)
            out["baselines_complete"] = True
        out["macro_terms"] = None
        out["macro_note"] = "no macro series with a verified fetch for this span"
        if self.spec.metal == "silver" and self.spec.freq == "monthly":
            gold = MetalsDomain(self._index, self._licences, series="gold_usd_pinksheet",
                                pinned_sha256=self._gold_pin or self._pinned, grades=self._grades)
            out["gold_co_movement"] = (
                gold._returns().reindex(g).rename("gold_usd_pinksheet.log_return")
            )
        return out

    def _festival_terms(self) -> pd.DataFrame:
        from ..markets import festivals as fest

        g = self.grid()
        if self.spec.freq == "daily":
            ff = fest.festival_flags(g).astype(int)
        else:
            days = pd.date_range(g[0], g[-1] + pd.offsets.MonthEnd(0), freq="D")
            ff = fest.festival_flags(days).astype(float)
            ff = ff.groupby(days.to_period("M")).mean().set_axis(g)
        return ff.loc[:, ff.sum() > 0]

    def _festival_problems(self) -> List[str]:
        from ..markets import festivals as fest

        g = self.grid()
        leap = [y for y in range(g[0].year, g[-1].year + 1) if fest.adhik_maas(y)]
        return festival_spotcheck_problems(leap_years=leap)
