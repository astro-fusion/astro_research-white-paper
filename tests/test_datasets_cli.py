"""Tests for scripts/generate_planetary_dataset.py."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT = SCRIPT / "generate_planetary_dataset.py"


def _load():
    spec = importlib.util.spec_from_file_location("gen_planetary_cli", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_generate_then_check(tmp_path, capsys):
    """Generate two years, then --check passes; tampering fails it."""
    cli = _load()
    out = str(tmp_path / "out")
    assert cli.main(["--years", "2000-2001", "--out", out, "--fmt", "csv"]) == 0
    assert cli.main(["--check", "--out", out]) == 0
    (Path(out) / "2001.csv").write_text("tampered")
    assert cli.main(["--check", "--out", out]) == 1
    assert "2001.csv" in capsys.readouterr().out


def test_parse_years():
    """'1600-2100' and '2000' parse."""
    cli = _load()
    assert cli.parse_years("1600-2100") == (1600, 2100)
    assert cli.parse_years("2000") == (2000, 2000)
