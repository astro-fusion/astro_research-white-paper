# 📦 Data Provenance & Reproducibility Governance

> This document governs how all empirical data and
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

### 2.1 Ephemeris Data (`data/ephemeris/`)

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

---

## 3. Reproduction Instructions Per Research Track

### 3.1 Astrological Chart Pipeline

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
| `scipy`      | `≥ 1.12.0`   | Statistics                                |
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
# Never use np.float32 for any ephemeris computation
```

---

## 5. Checksum Verification Workflow

```bash
# After downloading/generating any dataset, run:
sha256sum data/ephemeris/*.parquet > data/ephemeris/CHECKSUMS.sha256

# Before using data, verify:
sha256sum -c data/ephemeris/CHECKSUMS.sha256
```

---

## 6. Data Licensing

| Data Category                | License                 | Redistribution                     |
| ---------------------------- | ----------------------- | ---------------------------------- |
| Swiss Ephemeris binary files | Swiss Ephemeris License | Only download script redistributed |
| JPL Horizons exports         | Public Domain (NASA)    | Freely redistributable             |
| Derived analysis outputs     | MIT                     | Freely redistributable             |

---

_Every submitted PR that introduces new data must follow Section 2 (Dataset Registry)
and update the appropriate `CHECKSUMS.sha256` file._
