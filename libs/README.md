# 🔧 libs/ — Core Computation Library

The `libs/` directory contains all the **importable Python library code** that powers the research platform. It is designed to be pip-installable as a standalone package.

---

## 📦 Package Structure

```
libs/
├── vedic_astrology_core/    ← Core astrological engine (Swiss Ephemeris integration)
├── vedic_numerology/        ← Numerology calculators (Lo Shu, Chaldean, Vedic)
├── visuals/                 ← Chart and visualization generators
├── models/                  ← Shared data models and type definitions
└── __init__.py              ← Package init, version info
```

---

## 🪐 `vedic_astrology_core/` — Core Engine

The heart of the platform. Wraps the **Swiss Ephemeris** (`pyswisseph`) for astronomical precision.

| Submodule        | Purpose                                                 |
| ---------------- | ------------------------------------------------------- |
| `astrology/`     | Birth chart generation, house calculations              |
| `dignity/`       | Classical Vedic planetary dignity scoring (0–100 scale) |
| `dasha/`         | Vimshottari Dasha & sub-period calculations             |
| `combinations/`  | Yoga and planetary combination detection                |
| `principles/`    | Rules catalog from classical Jyotish texts              |
| `utils/`         | Date/time conversion, ayanamsa, coordinate transforms   |
| `visualization/` | Chart plotting utilities                                |
| `time_series.py` | Planetary strength time series computation              |
| `cli.py`         | Command-line interface entry point                      |

### Key Concepts

- **Ayanamsa**: Uses **Lahiri (Chitra Paksha)** — the official ayanamsa of the Government of India
- **Precision**: Swiss Ephemeris provides sub-arcsecond accuracy for dates from 2000 BCE to 3000 CE
- **Coordinate system**: All positions in sidereal (not tropical) longitude

### Quick Usage

```python
from libs.vedic_astrology_core import VedicChart
from libs.vedic_astrology_core.dignity import calculate_planetary_dignity

# Generate a birth chart
chart = VedicChart(
    birth_date="1984-08-27",
    birth_time="10:30",
    latitude=28.6139,
    longitude=77.1025,
    timezone="Asia/Kolkata"
)

# Get planetary position
mars_pos = chart.get_planet_position("Mars")
print(f"Mars: {mars_pos['sign']} at {mars_pos['degree']:.2f}°")

# Calculate dignity score
dignity = calculate_planetary_dignity("Mars", mars_pos["sign"], mars_pos["degree"])
print(f"Dignity: {dignity['dignity']} (score: {dignity['score']})")
```

---

## 🔢 `vedic_numerology/` — Numerology Engine

Implements multiple numerology traditions with a unified interface.

| Module         | System        | Description                                |
| -------------- | ------------- | ------------------------------------------ |
| `mulanka.py`   | Vedic         | Birth number (psychic number) calculation  |
| `bhagyanka.py` | Vedic         | Destiny number calculation                 |
| `lo_shu.py`    | Chinese/Vedic | Lo Shu grid analysis                       |
| `chaldean.py`  | Chaldean      | Letter-to-number mapping and name analysis |
| `compound.py`  | General       | Compound number reduction                  |

### Quick Usage

```python
from libs.vedic_numerology import NumerologyCalculator

calc = NumerologyCalculator()
result = calc.calculate_full_profile("1984-08-27")
print(f"Mulanka (Birth Number): {result['mulanka']}")
print(f"Bhagyanka (Destiny): {result['bhagyanka']}")
```

---

## 📊 `visuals/` — Visualization Engine

Generates charts and plots for research reports.

| Module               | Output                                   |
| -------------------- | ---------------------------------------- |
| `birth_chart.py`     | North/South Indian chart diagrams        |
| `timeline_plot.py`   | Planetary strength over time line charts |
| `dignity_heatmap.py` | Dignity score heatmaps across datasets   |
| `lo_shu_grid.py`     | Lo Shu grid visualizations               |

---

## 🧪 Testing the Library

```bash
# All library unit tests
pytest tests/test_astrology.py tests/test_dignity.py tests/test_numerology.py -v

# With coverage
pytest tests/ --cov=libs --cov-report=html

# Run only fast unit tests (skip slow integration tests)
pytest tests/ -m "not slow" -v
```

---

## 🔌 Installing as a Package

```bash
# Install in editable mode (for development)
pip install -e ".[dev]"

# Install only runtime dependencies
pip install -e .

# Install with Swiss Ephemeris support
pip install -e ".[ephemeris]"
```

---

## 🤝 Contributing to the Library

When adding a new calculation:

1. Add the function to the appropriate submodule
2. Write a Google-style docstring with an `Example:` section
3. Add full type hints on all parameters and return values
4. Write tests covering: happy path, boundary values, and invalid inputs
5. Add an entry to the relevant `README.md` table

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full details.
