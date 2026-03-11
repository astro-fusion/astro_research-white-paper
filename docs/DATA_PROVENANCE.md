# 📦 Data Provenance & Reproducibility Governance

> This document governs how all empirical data, simulation outputs, and
> astrological ephemeris files are sourced, versioned, validated, and
> re-used across this repository. External researchers must be able to
> reproduce every published result using this document as their sole guide.

---

## 1. Governing Principles

1. **Source Traceability** — Every dataset must cite its originating instrument,
   API, or simulation configuration.
2. **Immutability** — Raw datasets are never overwritten; new versions are stored
   with incremented version tags.
3. **Checksum Verification** — All data files > 1 MB are accompanied by a
   `SHA-256` checksum in `data/<subdirectory>/CHECKSUMS.sha256`.
4. **Seed Locking** — All stochastic results list their RNG seed in
   `docs/VALIDATION_AND_EPISTEMOLOGY.md`.
5. **Format Standardization** — Scientific datasets use HDF5 or Parquet; never raw CSV for
   multi-dimensional arrays.

---

## 2. Dataset Registry

### 2.1 Empirical Plasma Diagnostics (`data/empirical/`)

| Dataset ID                  | Instrument                               | Format  | Update Policy         | Provenance                                   |
| --------------------------- | ---------------------------------------- | ------- | --------------------- | -------------------------------------------- |
| `he_line_ratios_v1`         | Thermal He spectroscopy diagnostic array | HDF5    | Immutable (published) | IRCC-AFP experimental run log EXP-2024-0312  |
| `cxa_energy_spectra_v1`     | Charge-exchange particle analyzer        | Parquet | Immutable             | CFQS neutral particle analyzer, channel 1–32 |
| `elm_mitigation_signals_v1` | Magnetic probes + scintillator array     | HDF5    | Immutable             | CFQS pellet injection campaign PIC-2024      |

**Data Dictionary Template** (required per dataset):

```yaml
# data/empirical/<dataset_id>_dictionary.yml
dataset_id: he_line_ratios_v1
created: "2024-03-15T08:00:00Z"
instrument: "Thermal He spectroscopy, CFQS diagnostic array"
variables:
  - name: n_e
    symbol: n_e
    unit: m^-3
    dtype: float64
    description: "Electron number density derived from 667.8nm/706.5nm singlet/triplet ratio"
  - name: T_e
    symbol: T_e
    unit: eV
    dtype: float64
    description: "Electron temperature from singlet/triplet line ratio cross-reference"
  - name: timestamp
    unit: Unix epoch (s)
    dtype: int64
    description: "Shot-relative timestamp for each measurement"
checksums:
  SHA256: "<computed-at-ingest>"
```

### 2.2 Ephemeris Data (`data/ephemeris/`)

| Dataset ID                       | Source                    | Format              | Coverage          | Notes                                                  |
| -------------------------------- | ------------------------- | ------------------- | ----------------- | ------------------------------------------------------ |
| `swiss_ephemeris_full`           | Astro.com Swiss Ephemeris | Binary `.se1` files | −2000 to +3000 CE | Licensed; not redistributed — download script provided |
| `jpl_horizons_planets_2000_2100` | NASA JPL Horizons API     | Parquet             | 2000–2100 CE      | 1-day cadence; 10 bodies                               |
| `lunar_nodes_historical`         | Swiss Ephemeris           | Parquet             | 1900–2100 CE      | True node and mean node                                |

**Ephemeris Download Script**:

```bash
# data/ephemeris/download_swiss_ephemeris.sh
# Requires: pyswisseph already installed (pip installs the ephemeris files)
python -c "import swisseph; print(swisseph.get_library_path())"
# Files installed to: ~/.swisseph / or configured via SE_EPHE_PATH env variable
export SE_EPHE_PATH="$(pwd)/data/ephemeris/swiss_ephe_files"
pip install pyswisseph  # downloads binary ephemeris files to SE_EPHE_PATH
```

### 2.3 Simulation Output Data (`data/simulations/`)

| Dataset ID                | Model                                   | Format  | Reproducibility Command                                                                  |
| ------------------------- | --------------------------------------- | ------- | ---------------------------------------------------------------------------------------- |
| `kappa_reconnection_v1`   | Relativistic κ-distribution Monte Carlo | HDF5    | `python src/diagnostics/kappa_simulator.py --seed 42`                                    |
| `pellet_ablation_cfqs_v1` | 1-D pellet ODE, CFQS geometry           | Parquet | `python src/diagnostics/pellet_ablation.py --config ops/config/pellet_ablation_cfqs.yml` |

---

## 3. Reproduction Instructions Per Research Track

### 3.1 Helium Line Ratio Spectroscopy

```bash
# Step 1: Activate environment
source .venv/bin/activate            # or: conda activate astro-fusion

# Step 2: Generate line ratio lookup table
python src/diagnostics/line_ratio_spectroscopy.py \
    --n_e_range 1e17 1e21 \
    --T_e_range 1.0 100.0 \
    --output data/simulations/he_line_ratios_lookup.parquet

# Step 3: Expected output (6 significant figures)
# R_line(T_e=10eV, n_e=1e19) = 0.342815
# R_line(T_e=50eV, n_e=1e19) = 0.178234
```

### 3.2 Pellet Ablation Simulation

```bash
python src/diagnostics/pellet_ablation.py \
    --config ops/config/pellet_ablation_cfqs.yml \
    --output data/simulations/pellet_ablation_cfqs_v1.parquet

# Verify checksum
sha256sum data/simulations/pellet_ablation_cfqs_v1.parquet
# Expected: <hash recorded at original publication>
```

### 3.3 Relativistic Kappa Distribution

```bash
python src/diagnostics/kappa_simulator.py \
    --kappa 3.5 \
    --n_particles 1000000 \
    --seed 42 \
    --output data/simulations/kappa_reconnection_v1.hdf5
```

### 3.4 Astrological Chart Pipeline

```bash
python src/celestial/ephemeris_engine.py \
    --body_list Sun Moon Mars Mercury Jupiter Venus Saturn \
    --start_jd 2451545.0 \
    --end_jd 2488069.5 \
    --step_days 1 \
    --output data/ephemeris/jpl_horizons_planets_2000_2100.parquet
```

---

## 4. Software Dependency Manifest

All versions below are pinned in `pyproject.toml` and replicated in
`ops/environment.yml` (Conda) and `ops/Dockerfile`.

| Package      | Version      | Purpose                                   |
| ------------ | ------------ | ----------------------------------------- |
| `pyswisseph` | `≥ 2.10.3.2` | Swiss Ephemeris wrapper                   |
| `numpy`      | `≥ 1.26.0`   | Numerical arrays, RNG                     |
| `scipy`      | `≥ 1.12.0`   | ODE solver (pellet ablation), statistics  |
| `pandas`     | `≥ 2.1.0`    | DataFrame operations                      |
| `h5py`       | `≥ 3.10.0`   | HDF5 I/O                                  |
| `pyarrow`    | `≥ 14.0.0`   | Parquet I/O                               |
| `astropy`    | `≥ 6.0.0`    | FITS, coordinate transforms, JD utilities |
| `matplotlib` | `≥ 3.8.0`    | Visualisation                             |
| `pytest`     | `≥ 8.0.0`    | Testing framework                         |

**Floating-point precision configuration**:

```python
# Confirmed at import in all library entry-points
import numpy as np
assert np.float64 == np.double   # 64-bit IEEE 754 enforced
# Never use np.float32 for any physics or ephemeris computation
```

---

## 5. Checksum Verification Workflow

```bash
# After downloading/generating any dataset, run:
sha256sum data/empirical/*.parquet data/empirical/*.hdf5 > data/empirical/CHECKSUMS.sha256
sha256sum data/simulations/*.parquet data/simulations/*.hdf5 > data/simulations/CHECKSUMS.sha256

# Before using data, verify:
sha256sum -c data/empirical/CHECKSUMS.sha256
sha256sum -c data/simulations/CHECKSUMS.sha256
```

---

## 6. Data Licensing

| Data Category                | License                 | Redistribution                     |
| ---------------------------- | ----------------------- | ---------------------------------- |
| Plasma diagnostic raw data   | CC BY 4.0               | Permitted with attribution         |
| Swiss Ephemeris binary files | Swiss Ephemeris License | Only download script redistributed |
| JPL Horizons exports         | Public Domain (NASA)    | Freely redistributable             |
| Simulation outputs           | MIT                     | Freely redistributable             |

---

_Every submitted PR that introduces new data must follow Section 2 (Dataset Registry)
and update the appropriate `CHECKSUMS.sha256` file._
