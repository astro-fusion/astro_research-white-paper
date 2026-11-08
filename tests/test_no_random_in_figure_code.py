"""Guard: figure-producing research code must not draw random numbers.

Figures in the papers were once drawn from ``np.random`` and presented as
results (see CORRECTIONS.md, 2026-11-08). This test walks every Python file
under ``scripts/`` and ``studies/`` whose name marks it as figure
code and fails if it calls
``np.random.*``, ``numpy.random.*``, ``random.*`` or ``rng.*`` outside a
function whose name contains ``simulat``. Simulated illustrations must live in
such a function, run only behind an explicit ``--simulation`` flag, and carry a
``SIMULATED_`` filename prefix and watermark: a file that draws random
numbers inside a ``*simulat*`` function must also define a ``--simulation``
flag and use the ``SIMULATED_`` prefix.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = (REPO_ROOT / "scripts", REPO_ROOT / "studies")
FIGURE_NAME_MARKERS = ("figure", "asset", "graph", "plot", "artifact")
RANDOM_ROOTS = (("np", "random"), ("numpy", "random"), ("random",), ("rng",))
EXCLUDED_DIRS = {"_freeze", "_site", "__pycache__", ".ipynb_checkpoints"}


def _figure_files():
    files = []
    for path in sorted(p for d in SCAN_DIRS for p in d.rglob("*.py")):
        if EXCLUDED_DIRS.intersection(path.parts):
            continue
        name = path.stem.lower()
        if any(marker in name for marker in FIGURE_NAME_MARKERS):
            files.append(path)
    return files


def _attribute_chain(node):
    """Return ('np', 'random', 'normal') for ``np.random.normal``."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return tuple(reversed(parts))
    return ()


def _is_random_call(call):
    chain = _attribute_chain(call.func)
    if len(chain) < 2:
        return False
    return any(chain[: len(root)] == root for root in RANDOM_ROOTS)


class _RandomCallFinder(ast.NodeVisitor):
    def __init__(self):
        self.function_stack = []
        self.violations = []
        self.simulated_calls = 0

    def _visit_function(self, node):
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Call(self, node):
        if _is_random_call(node):
            in_simulation = any("simulat" in f.lower() for f in self.function_stack)
            if in_simulation:
                self.simulated_calls += 1
            else:
                self.violations.append(
                    (node.lineno, ".".join(_attribute_chain(node.func)))
                )
        self.generic_visit(node)


def _scan(path):
    source = path.read_text(encoding="utf-8")
    finder = _RandomCallFinder()
    finder.visit(ast.parse(source, filename=str(path)))
    return source, finder


def _violations(path):
    return _scan(path)[1].violations


def test_figure_files_are_found():
    """The walk must cover the known figure generators."""
    names = {p.name for p in _figure_files()}
    assert "generate_artifacts.py" in names
    assert "generate_paper_figures.py" in names


@pytest.mark.parametrize(
    "path", _figure_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_random_outside_simulation_functions(path):
    """No random draws in figure code outside a ``*simulat*`` function."""
    violations = _violations(path)
    assert not violations, (
        f"{path.relative_to(REPO_ROOT)} draws random numbers outside a "
        f"function named '*simulat*': {violations}"
    )


@pytest.mark.parametrize(
    "path", _figure_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_simulation_is_opt_in_and_labelled(path):
    """Simulated draws need a --simulation flag and SIMULATED_ outputs."""
    source, finder = _scan(path)
    if finder.simulated_calls == 0:
        return
    assert (
        '"--simulation"' in source
    ), f"{path.relative_to(REPO_ROOT)} simulates data but has no --simulation flag"
    assert "SIMULATED_" in source, (
        f"{path.relative_to(REPO_ROOT)} simulates data but its outputs are not "
        "named SIMULATED_*"
    )


def test_detector_flags_random_and_allows_simulation(tmp_path):
    """Self-check of the AST rule on a small sample."""
    sample = tmp_path / "plot_sample.py"
    sample.write_text(
        "import numpy as np\n"
        "import random\n"
        "def plot_results():\n"
        "    return np.random.normal(0, 1, 5), random.uniform(0, 1)\n"
        "def simulate_noise(rng):\n"
        "    return np.random.normal(0, 1, 5), rng.normal()\n"
    )
    assert [chain for _, chain in _violations(sample)] == [
        "np.random.normal",
        "random.uniform",
    ]
