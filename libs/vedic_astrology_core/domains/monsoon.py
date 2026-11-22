"""Monsoon adapter (ADR-007 section 4.2, WP-79).

The unit of evidence is the **season**: one all-India (or regional) June to
September rainfall value per year. Everything here keeps to that unit:

- `grid()` is one step per year (from the plan, not from the data).
- `calendar(principle)` gives one yes/no per year, evaluated at the instant
  or window the principle's source names: the weekday lord at the Sun's entry
  into Ardra (Meghesha), the weekday lord of Chaitra Shukla Pratipada
  (Varsheshvara), or a sky condition on any day of a season window (Mars in
  Rohini). It reads no outcome.
- An *episode* is a run of consecutive active seasons. The effect, its
  interval and its p-value are computed over episodes (`season_test`): each
  episode is compared with the inactive seasons near it (a local baseline,
  ADR-007 5.2), so slow rainfall epochs do not pass as an effect, and
  consecutive active seasons that share a baseline count once.

The plan values (years, explore/confirm split, LPA base, SESOI, budget, local
baseline, reference place, firewall paths) are read from a plan file. D9 has
not been written; `studies/monsoon/plan.yaml` is a DRAFT with the ADR-007
section 4.2 proposals (owner decision H16, default adopted).

Firewall (ADR-007 4.3, amending ADR-004 D-8): real IITM rainfall, and every
control derived from it, is refused until (a) the plan has
`status: registered` and its SHA-256 matches the hash the caller registered,
(b) the WP-70 calibration record on simulated rainfall says it passed for
that plan hash, and (c) the family lock exists. Simulated rainfall
(`simulate_rainfall`) is always allowed.

Principles live in `rules/monsoon/`. Until WP-65 adds `monsoon` to the
rule schema's `domain` enum the files carry a leading `_` (the catalogue
loader skips them) and `load_principles` validates them with the domain
mapped to `mundane`.
"""

from __future__ import annotations

import json
import re
import typing
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import yaml

from .base import DatasetSpec, DomainAdapter, Periods

REPO = Path(__file__).resolve().parents[3]
PLAN_PATH = REPO / "studies" / "monsoon" / "plan.yaml"
RULES_DIR = REPO / "rules" / "monsoon"

PLAN_KEYS = {
    "domain", "status", "plan_version", "design_task", "decisions",
    "unit_of_evidence", "years", "periods", "dataset", "lpa", "outcomes", "sesoi",
    "budget_m", "test", "reference_place", "controls", "principles",
    "untestable_now", "firewall",
}
PLAN_REQUIRED = {
    "domain", "status", "unit_of_evidence", "years", "periods", "dataset", "lpa",
    "outcomes", "sesoi", "budget_m", "test", "reference_place", "controls",
    "principles", "firewall",
}
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
SEASON_MONTHS = ("JUN", "JUL", "AUG", "SEP")
IITM_COLUMNS = MONTHS + ("JF", "MAM", "JJAS", "OND", "ANN")
# date.weekday(): Monday is 0.
WEEKDAY_LORDS = ("Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun")
NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
    "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
)
NAKSHATRA_SPAN = 360.0 / 27.0
CALENDAR_KINDS = ("weekday_lord_at_instant", "condition_in_season_window")
INSTANTS = ("sun_nakshatra_ingress", "chaitra_shukla_pratipada")
VARA_CONVENTIONS = ("sunrise", "udaya", "civil")
DIRECTIONS = ("increase", "decrease", "either")


class FirewallError(RuntimeError):
    """Real rainfall was requested before the ADR-007 4.3 conditions hold."""


class PlanError(ValueError):
    """The monsoon plan or a monsoon rule file is malformed."""


class VariantError(ValueError):
    """A variant that the principle does not declare was requested."""


# ---------------------------------------------------------------- the plan
def load_plan(path: Path = PLAN_PATH) -> Dict[str, Any]:
    """Read the plan strictly: an unknown or missing top-level key fails."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PlanError(f"{path}: a plan is one mapping")
    unknown = sorted(set(data) - PLAN_KEYS)
    if unknown:
        raise PlanError(f"{path}: unknown key(s) {unknown}")
    missing = sorted(PLAN_REQUIRED - set(data))
    if missing:
        raise PlanError(f"{path}: missing key(s) {missing}")
    if data["domain"] != "monsoon":
        raise PlanError(f"{path}: domain must be 'monsoon'")
    if data["status"] not in ("draft", "registered"):
        raise PlanError(f"{path}: status must be 'draft' or 'registered'")
    if data["unit_of_evidence"] != "season":
        raise PlanError(f"{path}: the unit of evidence must be 'season'")
    y0, y1 = (int(v) for v in data["years"])
    ex, cf = data["periods"]["explore"], data["periods"]["confirm"]
    if not (y0 <= int(ex[0]) <= int(ex[1]) < int(cf[0]) <= int(cf[1]) <= y1):
        raise PlanError(f"{path}: periods must be ordered inside the plan's years")
    return data


def _sha256(path: Path) -> str:
    from vedic_astrology_core.stats.manifest import file_sha256

    return file_sha256(path)


# ---------------------------------------------------------------- parsers
def region_key(name: str) -> str:
    """'ALL-INDIA' -> 'all_india'; 'WEST CENTRAL INDIA' -> 'west_central_india'."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


_BLOCK = re.compile(r"^\s*\d+\s+(.+?)\s+RAINFALL\b")


def parse_iitm_regions(text: str) -> Dict[str, pd.DataFrame]:
    """Parse an IITM regional rainfall file into one frame per region.

    Values in the file are tenths of a millimetre; the frames are in mm,
    indexed by year, with the twelve months and JF, MAM, JJAS, OND, ANN.
    """
    out: Dict[str, Dict[int, List[float]]] = {}
    region: Optional[str] = None
    for line in text.splitlines():
        m = _BLOCK.match(line)
        if m:
            region = region_key(m.group(1))
            out.setdefault(region, {})
            continue
        parts = line.split()
        if region and len(parts) == 1 + len(IITM_COLUMNS) and re.fullmatch(r"\d{4}", parts[0]):
            out[region][int(parts[0])] = [float(v) / 10.0 for v in parts[1:]]
    frames = {}
    for key, rows in out.items():
        df = pd.DataFrame.from_dict(rows, orient="index", columns=list(IITM_COLUMNS))
        df.index.name = "year"
        frames[key] = df.sort_index()
    return frames


def parse_psl_monthly(text: str) -> pd.DataFrame:
    """Parse a NOAA PSL monthly table (first line 'start end'; rows 'year v1..v12').

    Missing values (-99.99, -9999 and similar) become NaN.
    """
    lines = text.splitlines()
    first = lines[0].split()
    y0, y1 = int(first[0]), int(first[1])
    rows = {}
    for line in lines[1:]:
        parts = line.split()
        if len(parts) == 13 and re.fullmatch(r"\d{4}", parts[0]) and y0 <= int(parts[0]) <= y1:
            vals = [float(v) for v in parts[1:]]
            rows[int(parts[0])] = [np.nan if v <= -99.0 else v for v in vals]
    df = pd.DataFrame.from_dict(rows, orient="index", columns=list(MONTHS))
    df.index.name = "year"
    return df.sort_index()


# ---------------------------------------------------------- sky instants
_ENGINES: Dict[str, Any] = {}


def _engine(ayanamsa: str):
    from vedic_astrology_core.astrology.ephemeris import EphemerisEngine

    key = str(ayanamsa).lower()
    if key not in _ENGINES:
        _ENGINES[key] = EphemerisEngine(ayanamsa_system=key)
    return _ENGINES[key]


def _sun_lon(jd: float, ayanamsa: str) -> float:
    return float(_engine(ayanamsa).get_planet_position(jd, "SUN")["longitude"]) % 360.0


_J2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


def _jd(dt: datetime) -> float:
    return (dt - _J2000).total_seconds() / 86400.0 + 2451545.0


def jd_to_datetime(jd: float) -> datetime:
    """UTC datetime of a Julian day (UT)."""
    return _J2000 + timedelta(days=jd - 2451545.0)


def sun_nakshatra_ingress(year: int, nakshatra: str, ayanamsa: str = "lahiri") -> float:
    """JD (UT) of the Sun's entry into a sidereal nakshatra in that year."""
    if nakshatra not in NAKSHATRAS:
        raise ValueError(f"unknown nakshatra {nakshatra!r}")
    target = NAKSHATRAS.index(nakshatra) * NAKSHATRA_SPAN
    start = _jd(datetime(int(year), 1, 1, tzinfo=timezone.utc))
    delta = (target - _sun_lon(start, ayanamsa)) % 360.0
    guess = start + delta / 0.9856

    def ahead(jd: float) -> bool:  # Sun at or past the target (within half a circle)
        return ((_sun_lon(jd, ayanamsa) - target + 180.0) % 360.0 - 180.0) >= 0.0

    lo, hi = guess - 4.0, guess + 4.0
    if ahead(lo) or not ahead(hi):
        raise RuntimeError(f"could not bracket the Sun's ingress into {nakshatra} in {year}")
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if ahead(mid):
            hi = mid
        else:
            lo = mid
    return hi


def chaitra_shukla_pratipada(year: int) -> float:
    """JD (UT) of the new Moon that starts Chaitra (the luni-solar new year)."""
    from vedic_astrology_core.astrology.mundane import year_start

    return float(year_start(int(year)))


def _sunrise_after(jd: float, place: Mapping[str, Any]) -> float:
    import swisseph as swe

    res, tret = swe.rise_trans(
        jd, swe.SUN, swe.CALC_RISE, (float(place["lon"]), float(place["lat"]), 0.0)
    )
    if res != 0:
        raise RuntimeError("no sunrise found at the reference place")
    return float(tret[0])


def _sunrise_at_or_before(jd: float, place: Mapping[str, Any]) -> float:
    t = _sunrise_after(jd - 1.5, place)
    last = None
    while t <= jd:
        last = t
        t = _sunrise_after(t + 0.01, place)
    if last is None:
        raise RuntimeError("no sunrise found before the instant")
    return last


def _local_date(jd: float, place: Mapping[str, Any]) -> date:
    return (jd_to_datetime(jd) + timedelta(hours=float(place["tz_offset_hours"]))).date()


def vara_lord(jd: float, convention: str, place: Mapping[str, Any]) -> Tuple[str, date]:
    """Lord of the weekday (vara) for an instant, and the local date naming it.

    - `sunrise`: the vara that contains the instant (sunrise to sunrise).
    - `udaya`: the vara of the first sunrise after the instant.
    - `civil`: the local civil date (midnight to midnight).
    """
    if convention == "sunrise":
        day = _local_date(_sunrise_at_or_before(jd, place), place)
    elif convention == "udaya":
        day = _local_date(_sunrise_after(jd, place), place)
    elif convention == "civil":
        day = _local_date(jd, place)
    else:
        raise ValueError(f"vara convention must be one of {VARA_CONVENTIONS}")
    return WEEKDAY_LORDS[day.weekday()], day


# ------------------------------------------------- leave-year-out baselines
def leave_year_out_anomaly_pct(
    values: Sequence[float], years: Sequence[int], base_years: Tuple[int, int]
) -> np.ndarray:
    """Percent anomaly of each year against the base-period mean WITHOUT that year (D-06).

    For a year outside the base period this equals the usual anomaly; for a
    year inside it the year is dropped from its own mean, so a spike cannot
    pull its own baseline toward itself.
    """
    v = np.asarray(values, dtype=float)
    y = np.asarray(years, dtype=int)
    inb = (y >= int(base_years[0])) & (y <= int(base_years[1])) & np.isfinite(v)
    n, tot = int(inb.sum()), float(v[inb].sum())
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if not np.isfinite(v[i]):
            continue
        if inb[i]:
            if n < 2:
                continue
            base = (tot - v[i]) / (n - 1)
        else:
            if n < 1:
                continue
            base = tot / n
        out[i] = 100.0 * (v[i] - base) / base
    return out


def leave_year_out_running_mean(values: Sequence[float], half_window: int) -> np.ndarray:
    """Mean of the `half_window` years either side, leaving the year itself out (D-06)."""
    a = np.asarray(values, dtype=float)
    k = int(half_window)
    out = np.full(len(a), np.nan)
    for i in range(len(a)):
        w = np.r_[a[max(0, i - k):i], a[i + 1:i + 1 + k]]
        w = w[np.isfinite(w)]
        if w.size:
            out[i] = w.mean()
    return out


# ------------------------------------------------------------- principles
@dataclass(frozen=True)
class MonsoonPrinciple:
    """A rule file of rules/monsoon with its yearly evaluation spec."""

    rule: Any  # vedic_astrology_core.rules.schema.Rule
    spec: Mapping[str, Any]
    path: Path
    domain: str = "monsoon"

    @property
    def id(self) -> str:
        return self.rule.id

    def outcomes(self) -> Dict[str, str]:
        """Outcome series -> claimed direction."""
        return dict(self.spec.get("outcomes") or {})

    def variants(self) -> List[Dict[str, str]]:
        """Declared sensitivity cells, one dict per cell."""
        return [{k: v} for k, vals in (self.spec.get("variants") or {}).items() for v in vals]


def _domain_enum() -> Tuple[str, ...]:
    from vedic_astrology_core.rules.schema import Rule

    return tuple(typing.get_args(Rule.model_fields["domain"].annotation))


def load_principles(rules_dir: Path = RULES_DIR) -> Dict[str, MonsoonPrinciple]:
    """Load every rule file in `rules_dir` (a leading `_` included)."""
    from vedic_astrology_core.rules.schema import Rule

    allowed = _domain_enum()
    out: Dict[str, MonsoonPrinciple] = {}
    for path in sorted(Path(rules_dir).glob("*.y*ml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("domain") != "monsoon":
            raise PlanError(f"{path}: a monsoon rule needs domain: monsoon")
        if "monsoon" not in allowed:  # until WP-65 extends the enum
            data = dict(data, domain="mundane")
        rule = Rule.model_validate(data)
        spec = (rule.notes or {}).get("season_calendar")
        if not isinstance(spec, dict) or spec.get("kind") not in CALENDAR_KINDS:
            raise PlanError(f"{path}: notes.season_calendar.kind must be one of {CALENDAR_KINDS}")
        if not spec.get("outcomes"):
            raise PlanError(f"{path}: notes.season_calendar.outcomes is empty")
        for series, direction in spec["outcomes"].items():
            if direction not in DIRECTIONS:
                raise PlanError(f"{path}: outcome {series} has direction {direction!r}")
        if rule.id in out:
            raise PlanError(f"{path}: duplicate id {rule.id}")
        out[rule.id] = MonsoonPrinciple(rule, spec, path)
    return out


# --------------------------------------------------------------- calendars
def _period_mask(years: np.ndarray, period: Optional[Tuple[int, int]]) -> np.ndarray:
    years = np.asarray(years)
    if period is None:
        return np.ones(len(years), dtype=bool)
    return (years >= int(period[0])) & (years <= int(period[1]))


def _runs(active: np.ndarray) -> List[Tuple[int, int]]:
    """Index runs (first, last) of consecutive True values."""
    a = np.asarray(active, dtype=bool)
    runs, start = [], None
    for i, v in enumerate(a):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(a) - 1))
    return runs


@dataclass
class YearCalendar:
    """One yes/no per season. Reads no outcome."""

    principle_id: str
    years: np.ndarray
    active: np.ndarray
    detail: List[Dict[str, Any]] = field(default_factory=list)
    variant: Dict[str, str] = field(default_factory=dict)

    @property
    def duty_cycle(self) -> float:
        return float(np.mean(self.active)) if len(self.active) else 0.0

    def episodes(self, period: Optional[Tuple[int, int]] = None) -> List[Tuple[int, int]]:
        """Runs of consecutive active seasons, as (first year, last year)."""
        mask = _period_mask(self.years, period)
        return [(int(self.years[a]), int(self.years[b])) for a, b in _runs(self.active & mask)]

    def as_series(self) -> pd.Series:
        return pd.Series(self.active, index=pd.Index(self.years, name="year"), name=self.principle_id)

    def shifted(self, k: int) -> "YearCalendar":
        """The calendar rotated by `k` seasons (a shifted-sky negative control)."""
        return YearCalendar(
            f"{self.principle_id}@shift{int(k)}y", self.years.copy(), np.roll(self.active, int(k)),
            [], dict(self.variant, shift_years=str(int(k))),
        )


# ------------------------------------------------------ season statistics
@dataclass
class SeasonDifferences:
    """Per-episode differences against the local baseline."""

    differences: np.ndarray
    episodes: List[Tuple[int, int]]
    n_active_seasons: int
    n_dropped: int
    dropped: List[Tuple[int, int]]


def season_differences(
    years: Sequence[int],
    active: Sequence[bool],
    values: Sequence[float],
    *,
    half_window: int = 15,
    min_inactive: int = 5,
    period: Optional[Tuple[int, int]] = None,
) -> SeasonDifferences:
    """Each episode's mean minus the mean of inactive seasons near it.

    An episode is a run of consecutive active seasons inside `period`. Its
    baseline is every inactive season with a value, inside `period`, within
    `half_window` years of the episode. An episode with fewer than
    `min_inactive` such seasons, or with no value of its own, is dropped and
    counted. The result has one difference per episode: the unit of evidence.
    """
    years = np.asarray(years, dtype=int)
    act = np.asarray(active, dtype=bool)
    vals = np.asarray(values, dtype=float)
    if not (len(years) == len(act) == len(vals)):
        raise ValueError("years, active and values must have the same length")
    if np.any(np.diff(years) != 1):
        raise ValueError("years must be consecutive (one season per year)")
    inside = _period_mask(years, period)
    ok = np.isfinite(vals)
    diffs, kept, dropped = [], [], []
    n_active = int(np.sum(act & inside & ok))
    for a, b in _runs(act & inside):
        y0, y1 = years[a], years[b]
        own = vals[a : b + 1][ok[a : b + 1]]
        near = (~act) & inside & ok & (years >= y0 - half_window) & (years <= y1 + half_window)
        if own.size == 0 or int(near.sum()) < min_inactive:
            dropped.append((int(y0), int(y1)))
            continue
        diffs.append(float(own.mean() - vals[near].mean()))
        kept.append((int(y0), int(y1)))
    return SeasonDifferences(np.asarray(diffs, dtype=float), kept, n_active, len(dropped), dropped)


def season_test(
    years: Sequence[int],
    active: Sequence[bool],
    values: Sequence[float],
    *,
    direction: str,
    half_window: int = 15,
    min_inactive: int = 5,
    period: Optional[Tuple[int, int]] = None,
    n_draws: int = 99999,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, Any]:
    """Effect, 95 % interval, X95 and p over episodes.

    The effect is signed so that positive is the claimed direction
    (`direction: either` is tested two-sided, unsigned). The p-value is the
    episode-level sign-flip test (exact up to 20 episodes); the interval is
    the wild cluster interval over episodes (`stats/episodes.py`). Neither
    ever treats a month or a day as a unit.
    """
    from vedic_astrology_core.stats.episodes import sign_flip_test, wild_cluster_interval

    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    sd = season_differences(years, active, values, half_window=half_window,
                            min_inactive=min_inactive, period=period)
    sign = -1.0 if direction == "decrease" else 1.0
    d = sign * sd.differences
    rng = rng if rng is not None else np.random.default_rng(0)
    out: Dict[str, Any] = {
        "unit": "season",
        "n_episodes": int(len(d)),
        "n_active_seasons": sd.n_active_seasons,
        "n_dropped_episodes": sd.n_dropped,
        "episodes": sd.episodes,
        "direction": direction,
    }
    if len(d) == 0:
        out.update(effect=float("nan"), effect_sd=float("nan"), ci95=(float("nan"), float("nan")),
                   x95=float("inf"), p=1.0, p_min=1.0, exact=True)
        return out
    alternative = "two-sided" if direction == "either" else "greater"
    test = sign_flip_test(d, alternative=alternative, rng=rng, n_draws=n_draws)
    ci = wild_cluster_interval(d, level=0.95, rng=rng, n_draws=n_draws)
    upper = wild_cluster_interval(d, level=0.90, rng=rng, n_draws=n_draws).ci_high
    vals = np.asarray(values, dtype=float)[_period_mask(np.asarray(years), period)]
    scale = float(np.nanstd(vals, ddof=1)) if np.sum(np.isfinite(vals)) > 1 else float("nan")
    out.update(
        effect=float(d.mean()),
        effect_sd=float(d.mean() / scale) if np.isfinite(scale) and scale > 0 else float("nan"),
        ci95=(float(ci.ci_low), float(ci.ci_high)),
        x95=float(upper),  # one-sided 95 % upper limit in the claimed direction
        p=float(test.p_value),
        p_min=float(test.p_min),
        exact=bool(test.exact_enumeration),
    )
    return out


def risk_ratio(active: Sequence[bool], flags: Sequence[float],
               period_mask: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Rate of a yes/no season outcome in active against inactive seasons."""
    a = np.asarray(active, dtype=bool)
    f = np.asarray(flags, dtype=float)
    m = np.isfinite(f) if period_mask is None else (np.isfinite(f) & period_mask)
    r1 = float(f[a & m].mean()) if np.any(a & m) else float("nan")
    r0 = float(f[~a & m].mean()) if np.any(~a & m) else float("nan")
    rr = r1 / r0 if np.isfinite(r0) and r0 > 0 else float("nan")
    return {"rate_active": r1, "rate_inactive": r0, "risk_difference": r1 - r0, "risk_ratio": rr}


# --------------------------------------------------------- simulated rain
SEASON_SHARES = {"JUN": 0.19, "JUL": 0.32, "AUG": 0.29, "SEP": 0.20}


def simulate_rainfall(
    years: Sequence[int],
    *,
    seed: int = 0,
    regions: Sequence[str] = ("all_india",),
    lpa_mm: float = 850.0,
    sd_pct: float = 10.0,
    phi: float = 0.3,
    epoch_amplitude_pct: float = 4.0,
    epoch_period_years: float = 60.0,
    effect_pct: float = 0.0,
    active: Optional[Sequence[bool]] = None,
) -> Dict[str, pd.DataFrame]:
    """Simulated seasonal rainfall in the IITM frame layout (mm).

    Anomaly (percent of `lpa_mm`) = slow epoch (a sinusoid of random phase)
    + AR(1) noise + `effect_pct` in `active` seasons. With `effect_pct = 0`
    the rainfall is independent of every calendar: the calibration null.
    """
    years = np.asarray(years, dtype=int)
    rng = np.random.default_rng(seed)
    act = np.zeros(len(years), bool) if active is None else np.asarray(active, bool)
    out = {}
    for r in regions:
        e = rng.normal(0.0, sd_pct * np.sqrt(1 - phi**2), len(years))
        noise = np.empty(len(years))
        noise[0] = rng.normal(0.0, sd_pct)
        for t in range(1, len(years)):
            noise[t] = phi * noise[t - 1] + e[t]
        phase = rng.uniform(0, 2 * np.pi)
        epoch = epoch_amplitude_pct * np.sin(2 * np.pi * years / epoch_period_years + phase)
        jjas = lpa_mm * (1.0 + (epoch + noise + effect_pct * act) / 100.0)
        df = pd.DataFrame({m: jjas * s for m, s in SEASON_SHARES.items()},
                          index=pd.Index(years, name="year"))
        df["JJAS"] = jjas
        out[r] = df
    return out


# ------------------------------------------------------------------ adapter
class MonsoonDomain(DomainAdapter):
    """Indian summer monsoon, one season per year (IITM 1871-2016)."""

    domain = "monsoon"

    def __init__(
        self,
        index: Mapping[str, Any],
        licences: Mapping[str, Mapping[str, Any]],
        *,
        plan_path: Path = PLAN_PATH,
        rules_dir: Path = RULES_DIR,
        registered_plan_sha256: Optional[str] = None,
        simulated: Optional[Mapping[str, pd.DataFrame]] = None,
        repo: Path = REPO,
        grades: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> None:
        super().__init__(index, licences, grades)
        self.plan_path = Path(plan_path)
        self.rules_dir = Path(rules_dir)
        self.repo = Path(repo)
        self.plan = load_plan(self.plan_path)
        self._registered_sha = registered_plan_sha256
        self._simulated = dict(simulated) if simulated is not None else None
        self._principles: Optional[Dict[str, MonsoonPrinciple]] = None
        self._cal_cache: Dict[Tuple, YearCalendar] = {}
        self._outcome_cache: Optional[Dict[str, Any]] = None
        self.outcome_reads = 0

    # -- plan, dataset, grid -------------------------------------------
    def _path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.repo / p

    def dataset_spec(self) -> DatasetSpec:
        prim = self.plan["dataset"]["primary"]
        return DatasetSpec(
            id=f"{prim['id']}_{prim['sha256'][:12]}",
            sha256=prim["sha256"],
            source_id=prim["source_id"],
            span=tuple(str(s) for s in prim["span"]),
            n_units=len(self.grid()),
            n_events=None,
        )

    def grid(self) -> pd.Index:
        """One step per season, from the plan's years (no data read)."""
        y0, y1 = (int(v) for v in self.plan["years"])
        return pd.Index(np.arange(y0, y1 + 1), name="year")

    def periods(self) -> Periods:
        p = self.plan["periods"]
        return Periods(
            explore=(date(int(p["explore"][0]), 1, 1), date(int(p["explore"][1]), 12, 31)),
            confirm=(date(int(p["confirm"][0]), 1, 1), date(int(p["confirm"][1]), 12, 31)),
            pseudo_out_of_sample=bool(p.get("pseudo_out_of_sample", True)),
        )

    def period_years(self, which: str) -> Tuple[int, int]:
        """'explore', 'confirm' or 'whole' as (first year, last year)."""
        if which == "whole":
            y0, y1 = self.plan["years"]
            return int(y0), int(y1)
        a, b = self.plan["periods"][which]
        return int(a), int(b)

    def calendar_context(self) -> Mapping[str, Any]:
        years = np.asarray(self.grid())
        return {
            "unit": "season",
            "years": years,
            "season_months": list(SEASON_MONTHS),
            "reference_place": dict(self.plan["reference_place"]),
            "explore": _period_mask(years, self.period_years("explore")),
            "confirm": _period_mask(years, self.period_years("confirm")),
        }

    def declared_cells(self, principle_id: str) -> List[Dict[str, str]]:
        """Sensitivity cells the principle declares (primary excluded)."""
        return self.principles()[principle_id].variants()

    # -- principles and calendars (outcome-free) ------------------------
    def principles(self) -> Dict[str, MonsoonPrinciple]:
        if self._principles is None:
            loaded = load_principles(self.rules_dir)
            listed = list(self.plan["principles"])
            missing = [p for p in listed if p not in loaded]
            if missing:
                raise PlanError(f"plan names principle(s) with no rule file: {missing}")
            self._principles = {k: loaded[k] for k in listed}
        return self._principles

    def calendar(
        self,
        principle_id: str,
        variant: Optional[Mapping[str, str]] = None,
        years: Optional[Sequence[int]] = None,
    ) -> YearCalendar:
        """The yearly calendar of a principle (primary, or one declared cell)."""
        pr = self.principles()[principle_id]
        variant = dict(variant or {})
        declared = pr.spec.get("variants") or {}
        for k, v in variant.items():
            if v not in (declared.get(k) or []):
                raise VariantError(f"{principle_id} does not declare the cell {k}={v!r}")
        yrs = np.asarray(self.grid() if years is None else years, dtype=int)
        key = (principle_id, tuple(sorted(variant.items())), tuple(int(y) for y in yrs))
        if key not in self._cal_cache:
            if pr.spec["kind"] == "weekday_lord_at_instant":
                cal = self._weekday_calendar(pr, variant, yrs)
            else:
                cal = self._window_calendar(pr, variant, yrs)
            self._cal_cache[key] = cal
        return self._cal_cache[key]

    def _weekday_calendar(self, pr: MonsoonPrinciple, variant: Dict[str, str],
                          years: np.ndarray) -> YearCalendar:
        spec = pr.spec
        ayanamsa = variant.get("ayanamsa", pr.rule.ayanamsa or "lahiri")
        vara = variant.get("vara", spec.get("vara", "sunrise"))
        place = self.plan["reference_place"]
        lords = set(spec["active_lords"])
        instant = spec.get("instant")
        if instant not in INSTANTS:
            raise PlanError(f"{pr.id}: unknown instant {instant!r}")
        if instant == "chaitra_shukla_pratipada" and ayanamsa != "lahiri":
            raise VariantError("the lunar new year is computed with Lahiri only")
        active, detail = [], []
        for y in years:
            if instant == "sun_nakshatra_ingress":
                jd = sun_nakshatra_ingress(int(y), spec["nakshatra"], ayanamsa)
            else:
                jd = chaitra_shukla_pratipada(int(y))
            lord, day = vara_lord(jd, vara, place)
            active.append(lord in lords)
            detail.append({
                "year": int(y),
                "instant_utc": jd_to_datetime(jd).isoformat(timespec="minutes"),
                "vara_date": day.isoformat(),
                "lord": lord,
            })
        return YearCalendar(pr.id, years, np.asarray(active, bool), detail, variant)

    def _window_calendar(self, pr: MonsoonPrinciple, variant: Dict[str, str],
                         years: np.ndarray) -> YearCalendar:
        from vedic_astrology_core.rules.grid import GridEvaluator

        spec = pr.spec
        if "ayanamsa" in variant:
            raise VariantError("condition calendars run on the rule engine's Lahiri sky only")
        m0, m1 = (int(v) for v in spec.get("season", [6, 9]))
        after: Any = pd.Timedelta(0)
        before: Any = pd.Timedelta(0)
        w = pr.rule.window
        if variant.get("window") != "season_only" and w is not None:
            def off(n):
                n = float(n or 0)
                if w.unit == "months":
                    return pd.DateOffset(months=int(round(n)))
                per = {"hours": 1 / 24, "days": 1.0, "weeks": 7.0, "years": 365.25}[w.unit]
                return pd.Timedelta(days=n * per)
            after, before = off(w.after), off(w.before)
        step = int(spec.get("step_days", 1))
        spans, moments = [], []
        for y in years:
            start = pd.Timestamp(int(y), m0, 1, tz="UTC") - after
            end = pd.Timestamp(int(y), m1, 1, tz="UTC") + pd.offsets.MonthEnd(0) + before
            days = pd.date_range(start, end, freq=f"{step}D")
            spans.append((len(moments), len(moments) + len(days), start, end))
            moments.extend(days)
        ev = GridEvaluator(pd.DatetimeIndex(moments), node_model=pr.rule.node_model)
        fired = ev.fired(pr.rule)
        active, detail = [], []
        for (a, b, start, end), y in zip(spans, years):
            hit = fired[a:b]
            active.append(bool(hit.any()))
            first = moments[a + int(np.argmax(hit))].date().isoformat() if hit.any() else None
            detail.append({
                "year": int(y),
                "window": [start.date().isoformat(), end.date().isoformat()],
                "days_active": int(hit.sum()),
                "first_day": first,
            })
        return YearCalendar(pr.id, years, np.asarray(active, bool), detail, variant)

    def attainable_p(self, cal: YearCalendar, which: str = "confirm",
                     alternative: str = "greater", n_draws: int = 99999) -> float:
        """Smallest sign-flip p the calendar allows in a period (gate G5 input)."""
        from vedic_astrology_core.stats.episodes import sign_flip_p_min

        k = len(cal.episodes(self.period_years(which)))
        return sign_flip_p_min(k, alternative, n_draws)

    # -- the firewall ------------------------------------------------------
    def firewall_status(self) -> Dict[str, Any]:
        """Which of the three ADR-007 4.3 conditions hold, with reasons."""
        reasons: List[str] = []
        sha = _sha256(self.plan_path)
        if self.plan["status"] != "registered":
            reasons.append(f"(a) plan status is {self.plan['status']!r}, not 'registered'")
        if not self._registered_sha:
            reasons.append("(a) no registered plan hash was given")
        elif self._registered_sha != sha:
            reasons.append("(a) plan file differs from the registered hash")
        fw = self.plan["firewall"]
        cal_path = self._path(fw["calibration_record"])
        if not cal_path.is_file():
            reasons.append(f"(b) no calibration record at {fw['calibration_record']}")
        else:
            rec = json.loads(cal_path.read_text(encoding="utf-8"))
            if not (rec.get("passed") is True and rec.get("domain") == "monsoon"
                    and rec.get("rainfall") == "simulated" and rec.get("plan_sha256") == sha):
                reasons.append("(b) the calibration record does not show a pass on "
                               "simulated rainfall for this plan")
        lock = self._path(fw["family_lock"])
        if not (lock.is_file() and lock.stat().st_size > 0):
            reasons.append(f"(c) no family lock at {fw['family_lock']}")
        return {"open": not reasons, "reasons": reasons, "plan_sha256": sha}

    def _rainfall(self) -> Tuple[Dict[str, pd.DataFrame], str]:
        if self._simulated is not None:
            return self._simulated, "simulated"
        status = self.firewall_status()
        if not status["open"]:
            raise FirewallError(
                "real rainfall is refused until ADR-007 4.3 holds: " + "; ".join(status["reasons"])
            )
        prim = self.plan["dataset"]["primary"]
        path = self._path(prim["file"])
        if _sha256(path) != prim["sha256"]:
            raise FirewallError(f"{prim['file']} does not match the plan's SHA-256")
        return parse_iitm_regions(path.read_text(encoding="latin-1")), "iitm"

    # -- gated -------------------------------------------------------------
    def _season_outcomes(self) -> Dict[str, Any]:
        if self._outcome_cache is not None:
            return self._outcome_cache
        frames, source = self._rainfall()
        years = np.asarray(self.grid())
        b0, b1 = (int(v) for v in self.plan["lpa"]["base_years"])
        lo = float(self.plan["outcomes"]["drought_below_pct"])
        hi = float(self.plan["outcomes"]["excess_above_pct"])
        series: Dict[str, np.ndarray] = {}
        lpa: Dict[str, float] = {}
        for region, df in frames.items():
            df = df.reindex(years)
            base = df.loc[b0:b1, "JJAS"]
            if base.isna().any() or len(base) != b1 - b0 + 1:
                raise ValueError(f"{region}: the LPA base years {b0}-{b1} are not all present")
            lpa[region] = float(base.mean())
            jjas = df["JJAS"].to_numpy(float)
            anom = 100.0 * (jjas - lpa[region]) / lpa[region]
            fin = np.isfinite(anom)
            series[f"{region}_jjas_mm"] = jjas
            series[f"{region}_jjas_anomaly_pct"] = anom
            series[f"{region}_jjas_loo_anomaly_pct"] = leave_year_out_anomaly_pct(
                jjas, years, (b0, b1)
            )
            series[f"{region}_drought"] = np.where(fin, (anom < lo).astype(float), np.nan)
            series[f"{region}_excess"] = np.where(fin, (anom > hi).astype(float), np.nan)
            for m in SEASON_MONTHS:
                series[f"{region}_{m.lower()}_mm"] = df[m].to_numpy(float)
        self._outcome_cache = {
            "unit": "season",
            "source": source,
            "years": years,
            "series": series,
            "lpa_mm": lpa,
            "lpa_base_years": [b0, b1],
            "primary": self.plan["outcomes"]["primary"],
        }
        return self._outcome_cache

    def _outcomes(self) -> Mapping[str, Any]:
        out = self._season_outcomes()
        self.outcome_reads += 1
        return out

    def _controls(self) -> Mapping[str, Any]:
        """ENSO (the positive control), IOD, rainfall epochs and persistence.

        The rainfall-derived terms pass the same firewall as the outcomes.
        """
        years = np.asarray(self.grid())
        cfg = self.plan["controls"]
        out: Dict[str, Any] = {"years": years, "missing": {}}
        for name, (grp, key), cols in (
            ("oni_jas", ("enso", "oni"), ("JUL", "AUG", "SEP")),
            ("nino34_jjas", ("enso", "nino34"), SEASON_MONTHS),
            ("dmi_jjas", ("iod", "dmi"), SEASON_MONTHS),
        ):
            ent = cfg[grp][key]
            path = self._path(ent["file"])
            if not path.is_file():
                out["missing"][name] = f"snapshot {ent['file']} not present"
                continue
            if _sha256(path) != ent["sha256"]:
                out["missing"][name] = f"snapshot {ent['file']} does not match the plan's SHA-256"
                continue
            df = parse_psl_monthly(path.read_text(encoding="latin-1")).reindex(years)
            out[name] = df[list(cols)].mean(axis=1, skipna=False).to_numpy(float)
        long_cfg = (cfg.get("enso") or {}).get("nino34_long")
        if long_cfg:  # one series for explore and confirm years (ADR-008 6.1 item 7)
            path = self._path(long_cfg["file"])
            if not path.is_file():
                out["missing"]["nino34_long"] = f"snapshot {long_cfg['file']} not present"
            elif _sha256(path) != long_cfg["sha256"]:
                out["missing"]["nino34_long"] = (
                    f"snapshot {long_cfg['file']} does not match the plan's SHA-256"
                )
            else:
                df = parse_psl_monthly(path.read_text(encoding="latin-1")).reindex(years)
                out["nino34_long"] = df[list(SEASON_MONTHS)].mean(axis=1, skipna=False).to_numpy(float)
                out["nino34_long_covers"] = (int(df.dropna(how="all").index.min()),
                                              int(df.dropna(how="all").index.max()))
        if "oni_jas" in out:
            # PSL lists ONI by centre month: JUL, AUG, SEP are JJA, JAS, ASO.
            oni = out["oni_jas"]
            avail = np.isfinite(oni)
            thr = float(cfg["enso"]["el_nino_threshold"])
            out["el_nino"] = YearCalendar("control.el_nino", years, avail & (oni >= thr))
            out["el_nino_available"] = avail
        out["positive"] = [{
            "id": "control.el_nino", "kind": "positive", "direction": "decrease",
            "outcome": self.plan["outcomes"]["primary"],
            "note": "El Nino seasons (mean ONI over JJA, JAS, ASO at or above the threshold), 1950 on",
        }]
        out["negative"] = [{
            "id": "control.shifted_sky", "kind": "negative",
            "note": "each calendar rotated by k seasons (YearCalendar.shifted)",
        }]
        out["pending"] = {
            "sunspot": "SILSO has no fetch script or snapshot yet",
        }
        if "nino34_long" not in out:
            out["pending"]["nino34_long"] = "no pinned long Nino 3.4 snapshot in the plan (scripts/fetch/nino34_long.py)"
        anom = self._season_outcomes()["series"][self.plan["outcomes"]["primary"]]
        k = int(cfg["epoch"]["running_mean_years"]) // 2
        out["epoch_31y"] = leave_year_out_running_mean(anom, k)
        lag = int(cfg["persistence"]["lag_years"])
        out["last_year_anomaly"] = np.r_[np.full(lag, np.nan), anom[:-lag]]
        return out

    # -- one test on one calendar and one outcome -------------------------
    def season_effect(
        self,
        cal: YearCalendar,
        outcome: str,
        gate_hash: Optional[str],
        *,
        which: str = "whole",
        direction: Optional[str] = None,
        n_draws: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> Dict[str, Any]:
        """Season-level effect of a calendar on one outcome series."""
        oc = self.outcomes(gate_hash)
        if direction is None:
            pr = self.principles().get(cal.principle_id)
            if pr is None or outcome not in pr.outcomes():
                raise ValueError(f"{cal.principle_id} declares no direction for {outcome}")
            direction = pr.outcomes()[outcome]
        values = pd.Series(oc["series"][outcome], index=oc["years"]).reindex(cal.years).to_numpy()
        t = self.plan["test"]
        lb = t["local_baseline"]
        period = self.period_years(which)
        res = season_test(
            cal.years, cal.active, values, direction=direction,
            half_window=int(lb["half_window_years"]), min_inactive=int(lb["min_inactive"]),
            period=period, n_draws=int(n_draws or t["n_draws"]), rng=rng,
        )
        res.update(outcome=outcome, period=list(period), source=oc["source"])
        if outcome.endswith(("_drought", "_excess")):
            res["risk"] = risk_ratio(cal.active, values, _period_mask(cal.years, period))
        return res


__all__ = [
    "FirewallError",
    "MonsoonDomain",
    "MonsoonPrinciple",
    "PlanError",
    "SeasonDifferences",
    "VariantError",
    "YearCalendar",
    "chaitra_shukla_pratipada",
    "leave_year_out_anomaly_pct",
    "leave_year_out_running_mean",
    "load_plan",
    "load_principles",
    "parse_iitm_regions",
    "parse_psl_monthly",
    "risk_ratio",
    "season_differences",
    "season_test",
    "simulate_rainfall",
    "sun_nakshatra_ingress",
    "vara_lord",
]
