# 🧪 tests/ — Test Suite

This directory contains the complete test suite for the Vedic Astrology Research Platform.

---

## 📁 Test Files

| File                                   | Type        | Coverage Area                                            |
| -------------------------------------- | ----------- | -------------------------------------------------------- |
| `test_astrology.py`                    | Unit        | Core astrological calculations (charts, houses, planets) |
| `test_dignity.py`                      | Unit        | Planetary dignity scoring rules                          |
| `test_numerology.py`                   | Unit        | Numerology calculators (mulanka, bhagyanka, Lo Shu)      |
| `test_integration.py`                  | Integration | Full pipeline: data → analysis → output                  |
| `test_research_pipeline_phase1/2/3.py` | Pipeline    | Research pipeline phase validation                       |
| `test_vimshottari_dasha.py`            | Unit        | Dasha period calculations                                |
| `test_reference_charts.py`             | Reference   | Known-good chart validation against classical references |
| `test_golden_*.py`                     | Golden      | Positions, houses, vargas, dasha, combustion vs PyJHora  |
| `test_horizons_crosscheck.py`          | Astronomy   | Apparent longitudes vs JPL Horizons (DE441), offline     |
| `test_aspects.py`                      | Unit        | Geometric aspect matrix, out-of-bounds, parallels        |

---

## 🚀 Running Tests

### Quick (Unit Tests Only)

```bash
pytest tests/ -m "not slow and not integration" -v
```

### Full Suite

```bash
pytest tests/ -v
```

### With Coverage Report

```bash
pytest tests/ --cov=libs --cov-report=html --cov-report=term-missing
open htmlcov/index.html  # View coverage in browser
```

### Specific Test File

```bash
pytest tests/test_dignity.py -v
```

### Filter by Keyword

```bash
pytest -k "mars or retrograde" -v
```

### Slow / Integration Tests

```bash
pytest tests/ -m "slow" -v          # Slow tests only
pytest tests/ -m "integration" -v   # Integration tests only
```

### Ephemeris cross-check against JPL Horizons

```bash
pytest tests/test_horizons_crosscheck.py -v -s       # offline, stored fixtures
HORIZONS_LIVE=1 pytest tests/test_horizons_crosscheck.py -s   # fetch fresh values
python -m tests.horizons                              # rewrite the fixtures
```

No `PYTHONPATH` is needed: install the package (`pip install -e ".[dev]"`);
`tests/conftest.py` adds the repository root for `studies`, `scripts`,
`application` and `tools`.

---

## 🏷️ Test Markers

| Marker        | Description                                   | Usage                      |
| ------------- | --------------------------------------------- | -------------------------- |
| `slow`        | Tests that take >5 seconds                    | `@pytest.mark.slow`        |
| `integration` | Tests that run the full pipeline              | `@pytest.mark.integration` |
| `reference`   | Tests validating against known classical data | `@pytest.mark.reference`   |

---

## ✍️ Writing New Tests

Follow the patterns in `test_dignity.py` as a template:

```python
import pytest
from vedic_astrology_core.dignity import calculate_planetary_dignity

class TestPlanetaryDignity:
    """Unit tests for planetary dignity calculations."""

    def test_sun_in_aries_is_exalted(self):
        """Sun should be exalted in Aries (classical rule)."""
        result = calculate_planetary_dignity("Sun", "Aries", 10.0)
        assert result["dignity"] == "exaltation"

    @pytest.mark.parametrize("planet,sign,expected", [
        ("Moon", "Taurus", "exaltation"),
        ("Mars", "Capricorn", "exaltation"),
        ("Mercury", "Virgo", "exaltation"),
    ])
    def test_classical_exaltations(self, planet, sign, expected):
        result = calculate_planetary_dignity(planet, sign, 10.0)
        assert result["dignity"] == expected

    def test_invalid_planet_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_planetary_dignity("InvalidPlanet", "Aries", 10.0)
```

**Minimum requirements for a new function:**

- Happy path test
- At least 2 edge case / boundary tests
- At least 1 invalid input test

---

## 📊 Coverage Targets

| Module                       | Target Coverage |
| ---------------------------- | --------------- |
| `libs/vedic_astrology_core/` | > 85%           |
| `libs/vedic_numerology/`     | > 85%           |
| `tools/visuals/`             | > 70%           |
| `application/`               | > 70%           |

---

## 📖 Full Testing Guide

See [`TESTING_GUIDE.md`](TESTING_GUIDE.md) for in-depth documentation including:

- Mocking strategies for Swiss Ephemeris
- Parameterized test patterns
- Playwright setup for E2E tests
- CI test execution details
