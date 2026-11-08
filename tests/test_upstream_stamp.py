"""The upstream stamp must match the committed bundle files."""

import hashlib
from pathlib import Path

import pytest
import yaml

DATA = Path(__file__).resolve().parent.parent / "studies" / "mundane" / "data"
STAMP = yaml.safe_load((DATA / "UPSTREAM.yaml").read_text())
HINT = (
    "re-stamp studies/mundane/data/UPSTREAM.yaml "
    "(shasum -a 256 <file>; see docs/UPSTREAM_CONTRACT.md)"
)


def _rows(name):
    text = (DATA / name).read_text()
    if name.endswith(".yaml"):
        return len(yaml.safe_load(text)["countries"])
    return sum(1 for line in text.splitlines() if line.strip())


def test_stamp_has_contract_keys():
    """Stamp carries every key the contract lists."""
    for key in ("bundle_version", "exported_at", "row_counts", "sha256",
                "exporter_commit", "licence", "attribution"):
        assert key in STAMP, f"UPSTREAM.yaml missing {key}"
    assert STAMP["licence"] == "CC-BY-4.0"


@pytest.mark.parametrize("name", sorted(STAMP["sha256"]))
def test_hash_matches(name):
    """Each committed bundle file hashes to the stamped value."""
    actual = hashlib.sha256((DATA / name).read_bytes()).hexdigest()
    assert actual == STAMP["sha256"][name], (
        f"{name} is stale: hash differs from UPSTREAM.yaml; {HINT}"
    )


@pytest.mark.parametrize("key,name", [("countries", "countries.yaml"),
                                      ("events", "events.jsonl")])
def test_row_count_matches(key, name):
    """Stamped row counts match the files."""
    assert _rows(name) == STAMP["row_counts"][key], (
        f"{name} is stale: row count differs from UPSTREAM.yaml; {HINT}"
    )
