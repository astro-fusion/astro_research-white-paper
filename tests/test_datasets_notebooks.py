"""The ported dataset notebooks execute end to end on a two-year range."""

import os
from pathlib import Path

import pytest

papermill = pytest.importorskip("papermill")
pytest.importorskip("pyarrow")
pytest.importorskip("ipykernel")

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = [
    "03_planet_combinations.ipynb",
    "04_date_planet_conjunctions.ipynb",
]


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_notebook_executes(name, tmp_path, monkeypatch):
    """Run with papermill on 2000-2001; the notebook regenerates its data."""
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join(
            [str(ROOT / "libs"), str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]
        ),
    )
    out = tmp_path / name
    papermill.execute_notebook(
        str(ROOT / "notebooks" / name),
        str(out),
        parameters={
            "START_YEAR": 2000,
            "END_YEAR": 2001,
            "DATA_DIR": str(tmp_path / "planetary"),
        },
        kernel_name="python3",
        cwd=str(ROOT / "notebooks"),
        progress_bar=False,
    )
    assert out.exists()
    assert (tmp_path / "planetary" / "2001.parquet").exists()


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_notebooks_are_committed_without_outputs(name):
    """Committed notebooks carry no outputs or execution counts."""
    import json

    cells = json.loads((ROOT / "notebooks" / name).read_text())["cells"]
    for cell in cells:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None
