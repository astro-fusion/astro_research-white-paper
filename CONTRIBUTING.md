# 🤝 Contributing to the Vedic Astrology Research Platform

First off — **thank you** for taking the time to contribute! This is an open science project and every contribution matters, whether it's a typo fix, a new test case, a better formula, or an entirely new research track.

---

## 📋 Table of Contents

1. [Code of Conduct](#-code-of-conduct)
2. [Ways to Contribute](#-ways-to-contribute)
3. [Finding What to Work On](#-finding-what-to-work-on)
4. [Development Setup](#-development-setup)
5. [Workflow: Fork → Branch → PR](#-workflow-fork--branch--pr)
6. [Coding Standards](#-coding-standards)
7. [Testing Requirements](#-testing-requirements)
8. [Adding a Research Use Case](#-adding-a-research-use-case)
9. [Adding Edge Cases](#-adding-edge-cases)
10. [Documentation Standards](#-documentation-standards)
11. [Commit Message Format](#-commit-message-format)
12. [Pull Request Checklist](#-pull-request-checklist)
13. [Getting Help](#-getting-help)

---

## 🌍 Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before getting started.

---

## 🌟 Ways to Contribute

### 🐛 Bug Reports

Found a calculation that looks wrong? A broken script? [Open a Bug Report →](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=bug_report.yml)

### ✨ Feature Requests

Have an idea for a new feature or improvement? [Open a Feature Request →](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=feature_request.yml)

### 🔬 New Research Tracks

Want to propose a new empirical research question? [Open a Research Request →](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=research_request.yml)

### 🧪 Tests & Edge Cases

Adding test coverage is always valuable — especially planetary edge cases (retrograde stations, combust planets, ayanamsa boundary crossings). See [docs/EDGE_CASES.md](docs/EDGE_CASES.md).

### 📖 Documentation

Improve READMEs, add tutorials, fix broken links, add language translations.

### 🔧 Code Quality

Refactoring, type hints, performance improvements, CI/CD improvements.

---

## 🔍 Finding What to Work On

| Label                                                                                                                    | Description                                |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| [`good-first-issue`](https://github.com/astro-fusion/astro_research-white-paper/issues?q=label%3A%22good+first+issue%22) | Great starting points for new contributors |
| [`help-wanted`](https://github.com/astro-fusion/astro_research-white-paper/issues?q=label%3A%22help+wanted%22)           | Issues actively needing attention          |
| [`research`](https://github.com/astro-fusion/astro_research-white-paper/issues?q=label%3Aresearch)                       | Research methodology discussions           |
| [`edge-case`](https://github.com/astro-fusion/astro_research-white-paper/issues?q=label%3A%22edge-case%22)               | Known or discovered edge cases             |
| [`documentation`](https://github.com/astro-fusion/astro_research-white-paper/issues?q=label%3Adocumentation)             | Documentation improvements                 |

**Tip**: Comment on an issue before starting work to avoid duplication. Say "I'd like to work on this" and a maintainer will assign it to you.

---

## 💻 Development Setup

> For a full guide see [docs/DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md).

```bash
# 1. Fork the repo on GitHub (click "Fork" button)

# 2. Clone YOUR fork
git clone https://github.com/YOUR_USERNAME/astro_research-white-paper.git
cd astro_research-white-paper

# 3. Add upstream remote (to keep your fork in sync)
git remote add upstream https://github.com/astro-fusion/astro_research-white-paper.git

# 4. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 5. Install dependencies
pip install -r ops/requirements.txt
pip install -e ".[dev]"

# 6. Install pre-commit hooks (runs linters automatically on commit)
pip install pre-commit
pre-commit install

# 7. Verify everything works
pytest tests/ -v
make quality-gate
```

### Keeping Your Fork Up to Date

```bash
git fetch upstream
git checkout main
git rebase upstream/main
git push origin main
```

---

## 🔄 Workflow: Fork → Branch → PR

```bash
# 1. Sync your fork with upstream main
git fetch upstream && git rebase upstream/main

# 2. Create a descriptively named branch
git checkout -b feat/add-mars-retrograde-edge-case
# OR
git checkout -b fix/dasha-calculation-off-by-one
# OR
git checkout -b docs/improve-libs-readme

# 3. Make your changes
# ... edit files ...

# 4. Run quality checks before committing
make quality-gate  # lint + type-check + tests

# 5. Stage and commit (see commit format below)
git add .
git commit -m "feat(libs): add Mars retrograde boundary detection"

# 6. Push your branch
git push origin feat/add-mars-retrograde-edge-case

# 7. Open a Pull Request on GitHub
# → Use the PR template provided
# → Reference any related issues (e.g., "Closes #42")
```

---

## 📏 Coding Standards

### Python Style

We follow **PEP 8** enforced by **Black** and **isort**.

```bash
# Auto-format your code before committing
black libs/ tests/ research/scripts/ application/
isort libs/ tests/ research/scripts/ application/

# Check (without modifying)
black --check --diff libs/ tests/
```

### Type Hints (Required)

All public functions **must** have type hints:

```python
# ✅ Good
from typing import Optional

def calculate_dasha_period(
    birth_date: str,
    planet: str,
    duration_years: float
) -> dict[str, float]:
    """..."""

# ❌ Bad — missing type hints
def calculate_dasha_period(birth_date, planet, duration_years):
    pass
```

### Docstrings (Google Style)

All public functions, classes, and modules must have docstrings:

```python
def calculate_planetary_dignity(planet: str, sign: str, degree: float) -> dict:
    """Calculate the classical Vedic dignity score for a planet in a sign.

    Scores are based on traditional Jyotish rules: exaltation, own sign,
    Moolatrikona, friendly sign, neutral, enemy sign, and debilitation.

    Args:
        planet: Planet name (e.g., "Mars", "Jupiter"). Case-insensitive.
        sign: Vedic zodiac sign name (e.g., "Aries", "Taurus").
        degree: Degree within the sign (0.0 – 30.0).

    Returns:
        A dict with keys:
            - ``dignity`` (str): Dignity category ("exaltation", "own", etc.)
            - ``score`` (float): Numerical score from 0.0 to 100.0
            - ``planet`` (str): Normalized planet name

    Raises:
        ValueError: If planet or sign is not recognized.

    Example:
        >>> result = calculate_planetary_dignity("Mars", "Capricorn", 28.0)
        >>> result["dignity"]
        'exaltation'
        >>> result["score"]
        100.0
    """
```

### Naming Conventions

| Item            | Convention                   | Example                                         |
| --------------- | ---------------------------- | ----------------------------------------------- |
| Functions       | `snake_case`, verb-first     | `calculate_mulanka()`, `fetch_ephemeris_data()` |
| Classes         | `PascalCase`                 | `VedicChart`, `NumerologyCalculator`            |
| Boolean vars    | `is_`, `has_`, `can_` prefix | `is_retrograde`, `has_dignity`                  |
| Constants       | `UPPER_SNAKE_CASE`           | `LAHIRI_AYANAMSA_OFFSET`                        |
| Private methods | `_leading_underscore`        | `_normalize_degree()`                           |

---

## 🧪 Testing Requirements

All new code **must** be accompanied by tests:

```bash
# Run the full test suite
pytest tests/ -v

# Run with coverage report (aim for >85% on new code)
pytest tests/ --cov=libs --cov-report=html --cov-report=term-missing

# Run only fast tests (skip slow integration tests)
pytest tests/ -m "not slow" -v

# Run a specific test file
pytest tests/test_dignity.py -v

# Run tests matching a keyword
pytest -k "retrograde" -v
```

### Test Structure

```python
import pytest
from libs.vedic_astrology_core.dignity import calculate_planetary_dignity

class TestPlanetaryDignity:
    """Test suite for planetary dignity calculations."""

    def test_mars_in_exaltation(self):
        """Mars should be exalted in Capricorn near 28 degrees."""
        result = calculate_planetary_dignity("Mars", "Capricorn", 28.0)
        assert result["dignity"] == "exaltation"
        assert result["score"] == pytest.approx(100.0, abs=1.0)

    def test_mars_in_debilitation(self):
        """Mars should be debilitated in Cancer."""
        result = calculate_planetary_dignity("Mars", "Cancer", 28.0)
        assert result["dignity"] == "debilitation"

    @pytest.mark.parametrize("planet,sign,expected_dignity", [
        ("Sun", "Aries", "exaltation"),
        ("Moon", "Taurus", "exaltation"),
        ("Saturn", "Aries", "debilitation"),
    ])
    def test_classical_exaltations(self, planet, sign, expected_dignity):
        """Verify classical Vedic exaltation positions."""
        result = calculate_planetary_dignity(planet, sign, 10.0)
        assert result["dignity"] == expected_dignity

    def test_invalid_planet_raises(self):
        """An unrecognized planet name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown planet"):
            calculate_planetary_dignity("Pluto", "Aries", 10.0)
```

---

## 🔬 Adding a Research Use Case

Research use cases live in `research/use_cases/`. To add a new track:

1. **Discuss first** — Open a [Research Request issue](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=research_request.yml) to get feedback before investing time.

2. **Create the structure**:

   ```
   research/use_cases/your_topic/
   ├── README.md          ← Hypothesis, methodology, data sources
   ├── data/              ← Raw dataset (or instructions to download)
   ├── analysis.qmd       ← Quarto notebook with reproducible analysis
   ├── tests/             ← Validation tests for your analysis
   └── reports/           ← Generated report outputs
   ```

3. **Follow the methodology template** in [docs/RESEARCH_METHODOLOGY.md](docs/RESEARCH_METHODOLOGY.md).

4. **State your falsifiable hypothesis** clearly in `README.md`. We welcome research that disproves as much as research that proves.

---

## ⚠️ Adding Edge Cases

Found a calculation that breaks at a boundary condition? Please contribute it!

See [docs/EDGE_CASES.md](docs/EDGE_CASES.md) for the catalog of known edge cases.

To add a new one:

1. Add an entry to `docs/EDGE_CASES.md` describing the condition and expected behavior.
2. Add a failing (or newly passing) test in the appropriate test file.
3. Fix the code if you can; otherwise, open the PR with just the test — even a failing test is valuable!

---

## 📖 Documentation Standards

- Use **Markdown** for all documentation.
- Every directory that contains significant code should have a `README.md`.
- Keep READMEs **scannable**: use tables, code blocks, and headers liberally.
- Cross-link between documents generously.
- Keep instructions **copy-pasteable** — every code block should actually work.

---

## 💬 Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer: "Closes #123"]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `research`

**Examples**:

```
feat(libs): add Vimshottari Dasha sub-period calculations
fix(tests): correct expected value for Saturn exaltation test
docs(research): add earthquake use case README
test(dignity): add edge case for combust planet near exaltation degree
research(numerology): add Lo Shu grid analysis for 1990-2000 athletes
chore(ci): update Python version matrix to include 3.12
```

---

## ✅ Pull Request Checklist

Before opening your PR, confirm:

- [ ] Code follows the style guidelines (`make quality-gate` passes)
- [ ] New functions have type hints and docstrings
- [ ] Tests are added for new functionality (happy path + 2 edge cases minimum)
- [ ] All existing tests still pass (`pytest tests/ -v`)
- [ ] Documentation is updated if behavior changed
- [ ] Commit messages follow the conventional commit format
- [ ] The PR description references the related issue (`Closes #<number>`)

---

## ❓ Getting Help

| Channel                                                                                      | Use Case                                  |
| -------------------------------------------------------------------------------------------- | ----------------------------------------- |
| [GitHub Issues](https://github.com/astro-fusion/astro_research-white-paper/issues)           | Bug reports, feature requests             |
| [GitHub Discussions](https://github.com/astro-fusion/astro_research-white-paper/discussions) | Questions, ideas, methodology discussions |
| [Wiki](https://github.com/astro-fusion/astro_research-white-paper/wiki)                      | In-depth guides and reference material    |

Don't be shy — open an issue or discussion even if you're unsure. We'd rather you ask than get stuck!

---

🌟 **Thank you for contributing to open science!**
