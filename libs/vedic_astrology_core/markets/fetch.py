"""Market price adapters returning one tidy frame shape, plus hashed snapshots.

Every adapter returns a DataFrame with the columns of :data:`TIDY_COLUMNS`:

- ``date``: the market's local trading date (tz-naive ``datetime64``, midnight)
- ``close``: the closing (or fixing) price, strictly positive
- ``source``: where it came from, e.g. ``"fred"`` or ``"yahoo"``
- ``series_id``: the source's identifier, e.g. ``"GOLDPMGBD228NLBM"``
- ``is_futures``: True for futures contracts, which are never described as spot

``volume`` is kept when the source provides it. ``df.attrs["source_url"]`` and
``df.attrs["description"]`` carry provenance into :func:`snapshot`.

Network access is injectable (``opener``/``downloader``) so the tests run
offline on the fixtures in ``tests/fixtures/markets/``.
"""

import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional, Union

import pandas as pd

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
YAHOO_URL = "https://finance.yahoo.com/quote/{ticker}"

TIDY_COLUMNS = ["date", "close", "source", "series_id", "is_futures"]

KNOWN_SERIES: Dict[str, str] = {
    "GOLDPMGBD228NLBM": "LBMA gold price, PM fixing, USD per troy ounce (FRED)",
    "GOLDAMGBD228NLBM": "LBMA gold price, AM fixing, USD per troy ounce (FRED)",
    "SLVPRUSD": "LBMA silver price, USD per troy ounce (FRED)",
    "GC=F": "COMEX gold front-month continuous futures (Yahoo); not spot",
    "SI=F": "COMEX silver front-month continuous futures (Yahoo); not spot",
}


class FetchError(RuntimeError):
    """A source could not be reached or returned something other than data."""


def _default_opener(url: str) -> str:
    import requests

    try:
        response = requests.get(url, timeout=60)
    except requests.RequestException as exc:  # pragma: no cover - network
        raise FetchError(f"{url}: {exc}") from exc
    if response.status_code != 200:
        raise FetchError(f"{url}: HTTP {response.status_code}")
    return response.text


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise a tidy price frame (sorted, unique, positive)."""
    missing = [c for c in TIDY_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"price frame lacks columns {missing}")
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None).dt.normalize()
    out["close"] = pd.to_numeric(out["close"], errors="raise").astype(float)
    out["is_futures"] = out["is_futures"].astype(bool)
    out = out.dropna(subset=["close"]).sort_values("date")
    if out["date"].duplicated().any():
        raise ValueError("price frame has duplicate dates")
    if (out["close"] <= 0).any():
        raise ValueError("price frame has non-positive closes")
    cols = TIDY_COLUMNS + [c for c in out.columns if c not in TIDY_COLUMNS]
    out = out[cols].reset_index(drop=True)
    out.attrs = dict(df.attrs)
    return out


def parse_fred_csv(text: str, series_id: str) -> pd.DataFrame:
    """Parse FRED's ``fredgraph.csv`` (blank or ``.`` marks a missing day)."""
    if text.lstrip().startswith("<"):
        raise FetchError(f"FRED returned HTML, not CSV, for {series_id}")
    raw = pd.read_csv(io.StringIO(text), na_values=["."], keep_default_na=True)
    if series_id not in raw.columns or len(raw.columns) != 2:
        raise FetchError(f"FRED CSV for {series_id} has columns {list(raw.columns)}")
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(raw.iloc[:, 0]),
            "close": pd.to_numeric(raw[series_id], errors="coerce"),
        }
    ).dropna(subset=["close"])
    df["source"] = "fred"
    df["series_id"] = series_id
    df["is_futures"] = False
    df.attrs["source_url"] = FRED_URL.format(series_id=series_id)
    df.attrs["description"] = KNOWN_SERIES.get(series_id, series_id)
    return tidy(df)


def fred(
    series_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    opener: Optional[Callable[[str], str]] = None,
) -> pd.DataFrame:
    """Download a FRED series without an API key.

    Note: FRED withdrew the LBMA gold and silver series in 2022 (licensing);
    those ids now return HTTP 404 and raise :class:`FetchError`.
    """
    url = FRED_URL.format(series_id=series_id)
    df = parse_fred_csv((opener or _default_opener)(url), series_id)
    return clip(df, start, end)


def clip(df: pd.DataFrame, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
    """Keep rows with ``start <= date <= end`` (either bound optional)."""
    attrs = dict(df.attrs)
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end)]
    df = df.reset_index(drop=True)
    df.attrs = attrs
    return df


def _yfinance_download(ticker: str, start: str, end: Optional[str]) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - optional extra
        raise FetchError("yfinance missing: pip install -e '.[fetch]'") from exc
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if data is None or data.empty:
        raise FetchError(f"Yahoo returned no rows for {ticker}")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data


def yahoo(
    ticker: str,
    start: str = "1990-01-01",
    end: Optional[str] = None,
    is_futures: Optional[bool] = None,
    downloader: Optional[Callable[[str, str, Optional[str]], pd.DataFrame]] = None,
    drop_zero_volume: bool = True,
) -> pd.DataFrame:
    """Download daily closes from Yahoo Finance via yfinance (``fetch`` extra).

    Tickers ending in ``=F`` are futures; passing ``is_futures=False`` for one
    raises, so a futures series can never be labelled spot. Rows with zero
    volume are stale quotes and are dropped by default.
    """
    looks_futures = ticker.upper().endswith("=F")
    if is_futures is None:
        is_futures = looks_futures
    if looks_futures and not is_futures:
        raise ValueError(f"{ticker} is a futures contract; it cannot be spot")
    data = (downloader or _yfinance_download)(ticker, start, end)
    data = data.reset_index()
    date_col = "Date" if "Date" in data.columns else data.columns[0]
    df = pd.DataFrame(
        {"date": pd.to_datetime(data[date_col]), "close": data["Close"].astype(float)}
    )
    if "Volume" in data.columns:
        df["volume"] = data["Volume"].astype(float)
        if drop_zero_volume:
            df = df[df["volume"] > 0]
    df = df.dropna(subset=["close"])
    df["source"] = "yahoo"
    df["series_id"] = ticker
    df["is_futures"] = bool(is_futures)
    df.attrs["source_url"] = YAHOO_URL.format(ticker=ticker)
    df.attrs["description"] = KNOWN_SERIES.get(ticker, ticker)
    df.attrs["dropped_zero_volume"] = int(len(data) - len(df))
    return tidy(df)


def read_tidy_csv(path: Union[str, Path]) -> pd.DataFrame:
    """Read a tidy CSV (fixture or snapshot) written by :func:`snapshot`."""
    df = pd.read_csv(path)
    return tidy(df)


def csv_bytes(df: pd.DataFrame) -> bytes:
    """Canonical CSV encoding used for hashing (ISO dates, full precision)."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out.to_csv(index=False, float_format="%.6f", lineterminator="\n").encode()


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def default_snapshot_root() -> Path:
    """``$ASTRO_DATA_ROOT/snapshots``, else ``<repo>/data/snapshots``."""
    repo = Path(__file__).resolve().parents[3]
    return Path(os.environ.get("ASTRO_DATA_ROOT", repo / "data")) / "snapshots"


def snapshot(
    df: pd.DataFrame,
    name: str,
    root: Optional[Union[str, Path]] = None,
    source_url: Optional[str] = None,
    fetched_at: Optional[str] = None,
) -> Path:
    """Write ``<root>/<name>_<sha256[:12]>.csv`` plus a manifest; return the path.

    ``root`` defaults to ``data/snapshots`` (gitignored); the manifest
    (``.manifest.json`` next to the CSV) records hash, rows, date range,
    fetched_at and source URL, and study manifests copy the hash.
    """
    root = Path(root) if root is not None else default_snapshot_root()
    root.mkdir(parents=True, exist_ok=True)
    data = csv_bytes(tidy(df))
    digest = sha256_bytes(data)
    path = root / f"{name}_{digest[:12]}.csv"
    path.write_bytes(data)
    manifest = snapshot_manifest(df, digest, source_url, fetched_at)
    manifest["file"] = path.name
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return path


def snapshot_manifest(
    df: pd.DataFrame,
    digest: str,
    source_url: Optional[str] = None,
    fetched_at: Optional[str] = None,
) -> Dict:
    """Provenance record for a price frame."""
    dates = pd.to_datetime(df["date"])
    return {
        "sha256": digest,
        "rows": int(len(df)),
        "date_min": dates.min().strftime("%Y-%m-%d"),
        "date_max": dates.max().strftime("%Y-%m-%d"),
        "fetched_at": fetched_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": source_url or df.attrs.get("source_url"),
        "description": df.attrs.get("description"),
        "series_id": str(df["series_id"].iloc[0]) if len(df) else None,
        "is_futures": bool(df["is_futures"].iloc[0]) if len(df) else None,
    }


def load_snapshot(path: Union[str, Path], expected_sha256: Optional[str] = None):
    """Read a snapshot and verify its hash (from the name or ``expected``)."""
    path = Path(path)
    digest = sha256_bytes(path.read_bytes())
    stem_hash = path.stem.rsplit("_", 1)[-1]
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(f"{path.name}: sha256 {digest} != {expected_sha256}")
    if expected_sha256 is None and not digest.startswith(stem_hash):
        raise ValueError(f"{path.name}: content hash {digest[:12]} != name")
    return read_tidy_csv(path), digest
