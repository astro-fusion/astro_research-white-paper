"""Provenance manifest written next to every artifact.

``manifest.json`` records what is needed to reproduce a number: SHA-256,
row count and date range of every input, the git commit (and whether the
working tree was dirty), the seed, and the ephemeris configuration
(``ephemeris_model`` "swieph" or "moshier", ayanamsa, node model).
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

PathLike = Union[str, Path]


def file_sha256(path: PathLike, chunk: int = 1 << 20) -> str:
    """Return the hex SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def git_commit(repo_root: Optional[PathLike] = None) -> Dict[str, Any]:
    """Return ``{"commit": sha, "dirty": bool}`` or ``commit=None`` outside git."""
    cwd = str(repo_root) if repo_root else None
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": sha, "dirty": bool(status)}


def engine_info(engine: Any) -> Dict[str, Any]:
    """Return ephemeris model, ayanamsa and node model from an engine or dict."""
    if engine is None:
        return {"ephemeris_model": None, "ayanamsa": None, "node_model": None}
    info = engine if isinstance(engine, dict) else engine.get_ephemeris_info()
    return {
        "ephemeris_model": info.get("ephemeris_model"),
        "ayanamsa": info.get("ayanamsa_system", info.get("ayanamsa")),
        "node_model": info.get("node_model"),
        "swisseph_version": info.get("version"),
    }


def build_manifest(
    *,
    inputs: Iterable[Dict[str, Any]] = (),
    seed: Optional[int] = None,
    engine: Any = None,
    repo_root: Optional[PathLike] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble a manifest dictionary.

    Args:
        inputs: One dict per input with ``path`` and optionally
            ``row_count`` and ``date_range`` (``[first, last]``); the
            SHA-256 is computed here.
        seed: The seed passed to ``np.random.default_rng``.
        engine: An ``EphemerisEngine`` or its ``get_ephemeris_info()`` dict.
        repo_root: Repository for the git commit (default: current dir).
        extra: Any further study-specific fields.
    """
    records = []
    for item in inputs:
        rec = dict(item)
        rec["path"] = str(rec["path"])
        rec["sha256"] = file_sha256(rec["path"])
        if repo_root is not None:
            try:
                rec["path"] = str(
                    Path(rec["path"]).resolve().relative_to(Path(repo_root).resolve())
                )
            except ValueError:
                pass
        records.append(rec)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_commit(repo_root),
        "seed": seed,
        "inputs": records,
        "python": platform.python_version(),
    }
    manifest.update(engine_info(engine))
    if extra:
        manifest.update(extra)
    return manifest


def manifest_path(artifact: PathLike) -> Path:
    """Return where the manifest of ``artifact`` lives.

    A directory gets ``<dir>/manifest.json``; a file ``x.csv`` gets
    ``x.csv.manifest.json`` beside it.
    """
    p = Path(artifact)
    if p.is_dir():
        return p / "manifest.json"
    return p.with_name(p.name + ".manifest.json")


def write_manifest(artifact: PathLike, **kwargs: Any) -> Path:
    """Build a manifest (see :func:`build_manifest`) and write it next to it."""
    path = manifest_path(artifact)
    manifest = build_manifest(**kwargs)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    return path
