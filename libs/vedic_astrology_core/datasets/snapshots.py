"""Snapshot index and licence register (ADR-004 WP-11).

``data/snapshot_index.json`` is the committed list of every frozen input:
file, SHA-256, rows, date range, source URL, licence and whether the bytes are
committed to git. ``data/registry/licences.yaml`` records, per source, the terms
URL, the date a person read them and the decision (commit the file, or publish
the hash plus the fetch script only). The rule when unsure: hash plus fetch
script, no file.

Nothing here touches the network. Fetch scripts under ``scripts/fetch/`` call
:func:`write_snapshot`.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

REPO_ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = REPO_ROOT / "data" / "snapshot_index.json"
LICENCES_PATH = REPO_ROOT / "data" / "registry" / "licences.yaml"
SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"
SCHEMA_VERSION = 1

ENTRY_FIELDS = (
    "file",
    "sha256",
    "rows",
    "date_min",
    "date_max",
    "source_id",
    "source_url",
    "licence",
    "committable",
    "committed",
    "fetched_at",
)

PathLike = Union[str, Path]


class SnapshotError(RuntimeError):
    """A snapshot, the index or the licence register is inconsistent."""


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: PathLike) -> str:
    """Hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------- licences
def load_licences(path: PathLike = LICENCES_PATH) -> Dict[str, dict]:
    """Return ``{source_id: record}`` from the licence register."""
    import yaml

    data = yaml.safe_load(Path(path).read_text()) or {}
    sources = data.get("sources")
    if not isinstance(sources, dict):
        raise SnapshotError(f"{path}: no 'sources' mapping")
    for source_id, record in sources.items():
        for key in ("licence", "terms_url", "decision"):
            if key not in record:
                raise SnapshotError(f"{path}: source {source_id!r} lacks {key!r}")
        if record["decision"] not in ("commit", "hash_only"):
            raise SnapshotError(
                f"{path}: source {source_id!r} decision must be commit or hash_only"
            )
    return sources


def licence_for(source_id: str, path: PathLike = LICENCES_PATH) -> dict:
    """Record for ``source_id``; an unknown source raises (never guessed)."""
    sources = load_licences(path)
    if source_id not in sources:
        raise SnapshotError(f"source {source_id!r} is not in the licence register")
    return sources[source_id]


# ------------------------------------------------------------------- index
def load_index(path: PathLike = INDEX_PATH) -> dict:
    """Read the index, or return an empty one when the file does not exist."""
    path = Path(path)
    if not path.is_file():
        return {"schema": SCHEMA_VERSION, "snapshots": []}
    data = json.loads(path.read_text())
    if data.get("schema") != SCHEMA_VERSION or "snapshots" not in data:
        raise SnapshotError(f"{path}: unsupported snapshot index")
    return data


def save_index(index: dict, path: PathLike = INDEX_PATH) -> None:
    """Write the index sorted by file name, with a trailing newline."""
    index = dict(index)
    index["snapshots"] = sorted(index["snapshots"], key=lambda e: e["file"])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(index, indent=2) + "\n")


def add_entry(entry: dict, index_path: PathLike = INDEX_PATH) -> dict:
    """Add or replace the entry for ``entry['file']``; return it."""
    missing = [k for k in ENTRY_FIELDS if k not in entry]
    if missing:
        raise SnapshotError(f"index entry lacks {missing}")
    index = load_index(index_path)
    index["snapshots"] = [e for e in index["snapshots"] if e["file"] != entry["file"]]
    index["snapshots"].append({k: entry[k] for k in ENTRY_FIELDS})
    save_index(index, index_path)
    return entry


def write_snapshot(
    content: bytes,
    name: str,
    ext: str,
    source_id: str,
    source_url: str,
    rows: Optional[int] = None,
    date_min: Optional[str] = None,
    date_max: Optional[str] = None,
    snapshot_root: PathLike = SNAPSHOT_ROOT,
    index_path: PathLike = INDEX_PATH,
    licences_path: PathLike = LICENCES_PATH,
    fetched_at: Optional[str] = None,
    extra: Optional[dict] = None,
    repo_root: PathLike = REPO_ROOT,
) -> Path:
    """Write ``<name>_<sha12>.<ext>`` plus manifest and add the index entry.

    The licence comes from the register (an unknown ``source_id`` raises).
    ``committed`` is recorded as False: whether the bytes enter git is a
    separate, deliberate step, allowed only when ``committable`` is true.
    """
    licence = licence_for(source_id, licences_path)
    digest = sha256_bytes(content)
    root = Path(snapshot_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}_{digest[:12]}.{ext.lstrip('.')}"
    path.write_bytes(content)
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        rel = path.resolve().relative_to(Path(repo_root).resolve()).as_posix()
    except ValueError:
        rel = path.as_posix()
    entry = {
        "file": rel,
        "sha256": digest,
        "rows": rows,
        "date_min": date_min,
        "date_max": date_max,
        "source_id": source_id,
        "source_url": source_url,
        "licence": licence["licence"],
        "committable": licence["decision"] == "commit",
        "committed": False,
        "fetched_at": fetched_at,
    }
    manifest = dict(entry, bytes=len(content))
    manifest.update(extra or {})
    Path(str(path) + ".manifest.json").write_text(json.dumps(manifest, indent=2))
    add_entry(entry, index_path)
    return path


def _is_tracked(rel: str, repo_root: Path) -> Optional[bool]:
    """True/False when git knows; None when this is not a git checkout."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=repo_root,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.returncode == 0


def verify_index(
    index_path: PathLike = INDEX_PATH,
    snapshot_root: PathLike = SNAPSHOT_ROOT,
    repo_root: PathLike = REPO_ROOT,
) -> List[str]:
    """Return a list of problems (empty when the index and files agree).

    - a listed file that exists must match its SHA-256;
    - a listed file that is absent is fine only when ``committed`` is false
      (hash-only snapshot; a reader checks their own copy against the hash);
    - a file in the snapshot folder that the index does not list is an error;
    - an entry that claims ``committed`` while ``committable`` is false is an error.
    """
    repo_root = Path(repo_root)
    snapshot_root = Path(snapshot_root)
    index = load_index(index_path)
    problems: List[str] = []
    listed = set()
    for entry in index["snapshots"]:
        rel = entry["file"]
        listed.add((repo_root / rel).resolve())
        path = repo_root / rel
        if entry.get("committed") and not entry.get("committable"):
            problems.append(f"{rel}: committed but its licence does not allow it")
        if not path.is_file():
            if entry.get("committed"):
                problems.append(f"{rel}: listed as committed but the file is missing")
            continue
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            problems.append(f"{rel}: sha256 {actual[:12]} != index {entry['sha256'][:12]}")
    if snapshot_root.is_dir():
        for path in sorted(snapshot_root.iterdir()):
            if not path.is_file() or path.name.endswith(".manifest.json"):
                continue
            if path.name.startswith(".") or path.name == "README.md":
                continue
            if path.resolve() not in listed:
                problems.append(f"{path.name}: snapshot is not listed in the index")
    return problems
