"""Fetch event catalogues into hashed snapshots under ``data/snapshots/``.

Snapshots are gitignored. Each one gets a ``<name>.manifest.json`` with the
source URL, query, fetch time, byte size, SHA-256 and row count, so a published
result can name the exact bytes it used.

Sources
-------
usgs   USGS FDSN event service, CSV, global M>=6, 1900-2026. Public domain.
dfo    Dartmouth Flood Observatory global archive. The public file URL changes
       between releases; pass ``--url`` or ``--local <path>`` (see TODO).
emdat  Stub. EM-DAT needs registration and its licence forbids redistribution,
       so it is fetch-on-demand only and never committed.

``--offline`` skips the network and snapshots the tracked ``events.jsonl``.

Usage::

    python studies/mundane/scripts/fetch_catalogues.py usgs
    python studies/mundane/scripts/fetch_catalogues.py dfo --local archive.xlsx
    python studies/mundane/scripts/fetch_catalogues.py all --offline
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root
from studies.mundane.scripts.paths import EVENTS_FILE, SNAPSHOT_DIR  # noqa: E402

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_PARAMS = {
    "format": "csv",
    "starttime": "1900-01-01",
    "endtime": "2026-12-31",
    "minmagnitude": "6",
    "orderby": "time-asc",
}
# TODO: the DFO archive file URL could not be resolved on 2026-11-08
# (https://floodobservatory.colorado.edu/Archives/index.html returned 404 and
# no archive links were found on the site root). Find the current "Global
# Active Archive" Excel/CSV link on https://floodobservatory.colorado.edu and
# pass it as --url, or download it and pass --local <path>. Once confirmed,
# set DFO_URL below.
DFO_URL: Optional[str] = None

EMDAT_NOTICE = (
    "EM-DAT (CRED, UCLouvain) requires a free registration and its terms "
    "forbid redistribution. This repository never stores it. Register at "
    "https://public.emdat.be, download the export yourself, then run "
    "'fetch_catalogues.py emdat --local <file>' to hash it into "
    "data/snapshots/ (gitignored) so results can cite its SHA-256."
)


def sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int:
    """Rows in a text snapshot (lines minus the CSV header); 0 for binaries."""
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return 0
    with path.open("rb") as fh:
        lines = sum(1 for _ in fh)
    return lines if path.suffix.lower() == ".jsonl" else max(lines - 1, 0)


def write_manifest(path: Path, source: str, extra: Dict[str, Any]) -> Path:
    """Write ``<snapshot>.manifest.json`` next to the snapshot and return it."""
    manifest = {
        "source": source,
        "file": path.name,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path),
        "rows": count_rows(path),
    }
    manifest.update(extra)
    out = path.with_name(path.name + ".manifest.json")
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return out


def fetch_usgs(out_dir: Path = SNAPSHOT_DIR) -> Path:
    """Download the USGS global M>=6 catalogue as CSV."""
    import requests  # local import: offline use needs no network stack

    out_dir.mkdir(parents=True, exist_ok=True)
    resp = requests.get(USGS_URL, params=USGS_PARAMS, timeout=300)
    resp.raise_for_status()
    dest = out_dir / "usgs_m6_1900_2026.csv"
    dest.write_bytes(resp.content)
    write_manifest(dest, "USGS FDSN event service", {
        "url": resp.url, "query": USGS_PARAMS, "licence": "public domain"})
    return dest


def fetch_dfo(out_dir: Path = SNAPSHOT_DIR, url: Optional[str] = None,
              local: Optional[Path] = None) -> Path:
    """Snapshot the Dartmouth Flood Observatory archive from a URL or a file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if local is not None:
        dest = out_dir / f"dfo_{Path(local).name}"
        shutil.copyfile(local, dest)
        source_url = f"local:{Path(local).name}"
    else:
        url = url or DFO_URL
        if not url:
            raise SystemExit(
                "DFO archive URL not set (see the TODO in fetch_catalogues.py). "
                "Pass --url <link> or --local <downloaded file>.")
        import requests

        resp = requests.get(url, timeout=300)
        resp.raise_for_status()
        dest = out_dir / ("dfo_" + url.rsplit("/", 1)[-1].split("?")[0])
        dest.write_bytes(resp.content)
        source_url = url
    write_manifest(dest, "Dartmouth Flood Observatory", {
        "url": source_url, "licence": "see the DFO site; cite the archive"})
    return dest


def fetch_emdat(out_dir: Path = SNAPSHOT_DIR, local: Optional[Path] = None
                ) -> Optional[Path]:
    """EM-DAT stub: explain the licence, or hash a file the user downloaded."""
    if local is None:
        print(EMDAT_NOTICE)
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"emdat_{Path(local).name}"
    shutil.copyfile(local, dest)
    write_manifest(dest, "EM-DAT (CRED, UCLouvain)", {
        "licence": "registration required; not redistributable"})
    return dest


def snapshot_offline(out_dir: Path = SNAPSHOT_DIR) -> Path:
    """Offline fallback: hash a copy of the tracked ``events.jsonl``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "events_tracked.jsonl"
    shutil.copyfile(EVENTS_FILE, dest)
    write_manifest(dest, "tracked studies/mundane/data/events.jsonl", {
        "licence": "CC BY 4.0 (AstroFusion mundane dataset)"})
    return dest


def main(argv: Optional[list] = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", choices=["usgs", "dfo", "emdat", "all"])
    ap.add_argument("--offline", action="store_true",
                    help="no network: snapshot the tracked events.jsonl")
    ap.add_argument("--local", type=Path, help="use a file you downloaded")
    ap.add_argument("--url", help="DFO archive URL")
    ap.add_argument("--out-dir", type=Path, default=SNAPSHOT_DIR)
    args = ap.parse_args(argv)

    if args.offline:
        print(snapshot_offline(args.out_dir))
        return 0
    done = []
    if args.source in ("usgs", "all"):
        done.append(fetch_usgs(args.out_dir))
    if args.source in ("dfo", "all"):
        if args.source == "all" and not (args.url or args.local or DFO_URL):
            print("dfo: skipped (no URL; pass --url or --local)")
        else:
            done.append(fetch_dfo(args.out_dir, args.url, args.local))
    if args.source in ("emdat", "all"):
        local = args.local if args.source == "emdat" else None
        fetched = fetch_emdat(args.out_dir, local)
        if fetched:
            done.append(fetched)
    for path in done:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
