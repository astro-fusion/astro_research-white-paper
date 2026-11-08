#!/usr/bin/env python3
"""Decluster an earthquake catalogue two ways and report the counts.

* :func:`gardner_knopoff` is the window method of Gardner and Knopoff (1974)
  with the van Stiphout et al. (2012) functional form of the windows.
* :func:`nearest_neighbour` is the Zaliapin and Ben-Zion (2013)
  nearest-neighbour method with a threshold from a two-component Gaussian
  mixture on ``log10(eta)``.

Both take a DataFrame with ``time`` (UTC), ``latitude``, ``longitude`` and
``mw`` and return a boolean Series, True for events kept as mainshocks
(background). Usage on the latest snapshot::

    python studies/earthquake/scripts/decluster.py [--snapshot PATH]
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

EARTH_RADIUS_KM = 6371.0
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def days_since_epoch(times) -> np.ndarray:
    """Return float days since 1970-01-01 UTC (independent of datetime unit)."""
    t = pd.to_datetime(pd.Series(times), utc=True, format="ISO8601")
    return ((t - EPOCH) / pd.Timedelta(days=1)).to_numpy(dtype=float)


def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Return great-circle distances in km (broadcasts)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def gk_windows(m) -> Tuple[np.ndarray, np.ndarray]:
    """Return Gardner-Knopoff ``(distance_km, time_days)`` windows."""
    m = np.asarray(m, dtype=float)
    dist = 10 ** (0.1238 * m + 0.983)
    days = np.where(m >= 6.5, 10 ** (0.032 * m + 2.7389), 10 ** (0.5409 * m - 0.547))
    return dist, days


def gardner_knopoff(df: pd.DataFrame) -> pd.Series:
    """Return True for mainshocks under the Gardner-Knopoff window method.

    Events are processed largest first. Every not-yet-removed event that is
    no larger, within the distance window and within the time window
    (before or after) of a kept event is removed.
    """
    t = days_since_epoch(df["time"])
    lat = df["latitude"].to_numpy(float)
    lon = df["longitude"].to_numpy(float)
    m = df["mw"].to_numpy(float)
    dist_w, time_w = gk_windows(m)
    removed = np.zeros(len(df), dtype=bool)
    for i in np.lexsort((t, -m)):
        if removed[i]:
            continue
        near = np.abs(t - t[i]) <= time_w[i]
        near &= m <= m[i]
        near[i] = False
        cand = np.flatnonzero(near & ~removed)
        if len(cand):
            d = haversine_km(lat[i], lon[i], lat[cand], lon[cand])
            removed[cand[d <= dist_w[i]]] = True
    return pd.Series(~removed, index=df.index, name="mainshock_gk")


def nearest_neighbour_eta(
    df: pd.DataFrame, b: float = 1.0, df_frac: float = 1.6, r_min_km: float = 1.0
) -> np.ndarray:
    """Return ``log10`` of each event's nearest-neighbour proximity.

    ``eta_ij = t_ij * r_ij**df * 10**(-b m_i)`` over earlier events ``i``;
    time in years, epicentral distance in km (floored at ``r_min_km``).
    The first event has no parent and gets ``+inf``.
    """
    t = days_since_epoch(df["time"]) / 365.25
    order = np.argsort(t, kind="stable")
    lat = df["latitude"].to_numpy(float)[order]
    lon = df["longitude"].to_numpy(float)[order]
    m = df["mw"].to_numpy(float)[order]
    ts = t[order]
    log_eta = np.full(len(df), np.inf)
    for j in range(1, len(df)):
        dt = ts[j] - ts[:j]
        ok = dt > 0
        if not ok.any():
            continue
        r = np.maximum(haversine_km(lat[j], lon[j], lat[:j][ok], lon[:j][ok]), r_min_km)
        val = np.log10(dt[ok]) + df_frac * np.log10(r) - b * m[:j][ok]
        log_eta[j] = val.min()
    out = np.empty(len(df))
    out[order] = log_eta
    return out


def gmm_threshold(x, fallback: float = -5.0, n_iter: int = 300) -> Dict:
    """Fit a two-component Gaussian mixture and return the density minimum.

    Returns a dict with ``threshold``, the component means, sds, weights
    and ``separated`` (False when the fallback was used).
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    mu = np.percentile(x, [25, 75]).astype(float)
    sd = np.array([x.std(), x.std()]) / 2 + 1e-6
    w = np.array([0.5, 0.5])
    for _ in range(n_iter):
        dens = (
            w * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        )
        resp = dens / np.maximum(dens.sum(axis=1, keepdims=True), 1e-300)
        nk = resp.sum(axis=0)
        w = nk / len(x)
        mu = (resp * x[:, None]).sum(axis=0) / nk
        sd = np.sqrt((resp * (x[:, None] - mu) ** 2).sum(axis=0) / nk) + 1e-6
    lo, hi = np.argsort(mu)
    grid = np.linspace(mu[lo], mu[hi], 2001)
    mix = sum(
        w[k] * np.exp(-0.5 * ((grid - mu[k]) / sd[k]) ** 2) / sd[k] for k in (lo, hi)
    )
    interior = mix[1:-1]
    separated = bool(
        len(interior)
        and (mu[hi] - mu[lo]) > max(sd)
        and (interior.min() < min(mix[0], mix[-1]))
    )
    threshold = float(grid[1:-1][np.argmin(interior)]) if separated else fallback
    return {
        "threshold": threshold,
        "means": [float(mu[lo]), float(mu[hi])],
        "sds": [float(sd[lo]), float(sd[hi])],
        "weights": [float(w[lo]), float(w[hi])],
        "separated": separated,
    }


def nearest_neighbour(
    df: pd.DataFrame, b: float = 1.0, df_frac: float = 1.6
) -> Tuple[pd.Series, Dict]:
    """Return mainshock flags and the fitted threshold for the NN method."""
    log_eta = nearest_neighbour_eta(df, b=b, df_frac=df_frac)
    fit = gmm_threshold(log_eta)
    keep = ~(log_eta < fit["threshold"])
    fit["log10_eta"] = log_eta
    return pd.Series(keep, index=df.index, name="mainshock_nn"), fit


def main(argv=None) -> int:
    """Print event counts before and after each declustering method."""
    from pipeline import load_catalogue

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)
    cat, info = load_catalogue(args.snapshot, offline=args.offline)
    gk = gardner_knopoff(cat)
    nn, fit = nearest_neighbour(cat)
    print(f"source {info['source']}; Mw >= {info['completeness']['threshold']}")
    print(f"raw events:               {len(cat)}")
    print(f"Gardner-Knopoff mainshocks: {int(gk.sum())}")
    print(
        f"nearest-neighbour mainshocks: {int(nn.sum())} "
        f"(log10 eta0 = {fit['threshold']:.2f})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
