# 🌐 Source Code (Logic Layer)

The `src/` directory contains the core computational engines and logic for the research platform.

## Key Components

### 🪐 **Core Vedic Astrology Engine**

- **Swiss Ephemeris Backend**: Astronomical precision with 0.1 arcsecond accuracy.
- **Lahiri Ayanamsa**: Traditional Chitra Paksha ayanamsa system.
- **Complete Birth Charts**: Support for all planets, lunar nodes, and houses.

### 📊 **Dignity & Strength Analysis**

- **Classical Dignity Scoring**: Moolatrikona, own sign, and exaltation analysis.
- **Quantitative Strength Metrics**: 0-100 planetary power calculations.
- **Aspect Analysis**: Planetary relationships and influence patterns.

### 📈 **Temporal Dynamics**

- **Transit Analysis**: Current planetary influences on natal positions.
- **Dasha Period Calculations**: Major and sub-period influence mapping.
- **Time Series Analysis**: Engines for computing how planetary strengths evolve over time.

## Workflow

1. **Data Ingestion**: Fetching raw data from `data/`.
2. **Alignment**: Mapping timestamps to high-precision astrological coordinates.
3. **Statistical Engine**: Running Granger Causality and Monte Carlo permutations.
4. **Orchestration**: `generate_artifacts.py` triggers the full pipeline.
