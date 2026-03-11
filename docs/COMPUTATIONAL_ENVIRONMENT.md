# 💻 Computational Environment Specifications

> **Purpose**: Define the exact hardware profiles, software environments, and
> containerisation strategies required to run the astro-fusion research platform.
> Any researcher must be able to replicate results across different machines
> by following this document.

---

## 1. Minimum Hardware Requirements

| Workload                                     | CPU Cores | RAM   | Storage | GPU                    |
| -------------------------------------------- | --------- | ----- | ------- | ---------------------- |
| Line ratio lookup generation                 | 2+        | 4 GB  | 5 GB    | Not required           |
| Pellet ablation ODE (CFQS)                   | 4+        | 8 GB  | 10 GB   | Not required           |
| Relativistic κ Monte Carlo (10⁶ particles)   | 8+        | 16 GB | 20 GB   | Optional (CUDA)        |
| Multi-century ephemeris generation           | 4+        | 8 GB  | 50 GB   | Not required           |
| Full ML Phase IV pipeline (PCA + clustering) | 16+       | 64 GB | 200 GB  | Recommended (CUDA 12+) |

**Recommended Development Environment**: Apple M-series (M2 Pro+) or Linux x86_64 with AVX2 support.

---

## 2. Python Virtual Environment Setup

```bash
# Requires Python 3.11+
python3 --version     # must be >= 3.11.0

# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate     # Linux / macOS
# .venv\Scripts\activate      # Windows

# Install all dependencies
pip install --upgrade pip
pip install -e ".[dev]"       # editable install; includes dev extras

# Verify Swiss Ephemeris
python -c "import swisseph as swe; print('Swiss Ephemeris:', swe.version)"
```

---

## 3. Conda Environment (Recommended for Scientific Computing)

```yaml
# ops/environment.yml  — pin this file, do NOT auto-update
name: astro-fusion
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11.8
  - numpy=1.26.4
  - scipy=1.12.0
  - pandas=2.2.0
  - h5py=3.10.0
  - pyarrow=14.0.2
  - matplotlib=3.8.3
  - astropy=6.0.1
  - pytest=8.0.2
  - pip:
      - pyswisseph>=2.10.3.2
      - quarto>=1.4.0
```

```bash
# Create environment
conda env create -f ops/environment.yml
conda activate astro-fusion

# Export current environment (for reproducibility snapshot)
conda env export --no-builds > ops/environment_frozen.yml
```

---

## 4. Docker Container

```dockerfile
# ops/Dockerfile
FROM python:3.11-slim-bookworm

LABEL maintainer="astro-fusion team"
LABEL description="Astro-Fusion Research Platform — Reproducible Compute Environment"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libhdf5-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install Python dependencies first (layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy repository
COPY . .

# Swiss Ephemeris data path
ENV SE_EPHE_PATH=/workspace/data/ephemeris/swiss_ephe_files

ENTRYPOINT ["python"]
```

```bash
# Build and run
docker build -t astro-fusion:latest -f ops/Dockerfile .
docker run --rm -v $(pwd)/data:/workspace/data astro-fusion:latest \
    src/celestial/ephemeris_engine.py --help
```

---

## 5. Operating System and Compiler Versions (Original Computation)

All published results in the white papers were generated with the following
verified environment:

| Component               | Version / Value                                           |
| ----------------------- | --------------------------------------------------------- |
| OS                      | macOS 14.4.1 (Sonoma) + Ubuntu 22.04 LTS (cross-verified) |
| Python                  | 3.11.8                                                    |
| GCC / Clang             | Apple Clang 15.0.0 (macOS); GCC 11.4.0 (Linux)            |
| NumPy                   | 1.26.4 (OpenBLAS backend)                                 |
| SciPy                   | 1.12.0                                                    |
| pyswisseph              | 2.10.3.2                                                  |
| Swiss Ephemeris binary  | SE 2.10.03                                                |
| Quarto                  | 1.4.551                                                   |
| IEEE 754                | 64-bit double precision throughout                        |
| Random number generator | `numpy.random.default_rng` (PCG64)                        |

---

## 6. Environment Variable Reference

| Variable                | Default                               | Purpose                                            |
| ----------------------- | ------------------------------------- | -------------------------------------------------- |
| `SE_EPHE_PATH`          | `./data/ephemeris/swiss_ephe_files`   | Swiss Ephemeris binary file location               |
| `ASTRO_DATA_DIR`        | `./data`                              | Root for all data subdirectories                   |
| `ASTRO_LOG_LEVEL`       | `INFO`                                | Python logging level                               |
| `KAPPA_SEED`            | `42`                                  | Default Monte Carlo seed (override per experiment) |
| `PELLET_CONFIG`         | `ops/config/pellet_ablation_cfqs.yml` | Default pellet simulation config                   |
| `HOUSE_SYSTEM`          | `placidus`                            | Default astrological house system                  |
| `FALLBACK_HOUSE_SYSTEM` | `whole_sign`                          | Polar latitude fallback house system               |

Set in `.env` (not committed) or export directly:

```bash
export SE_EPHE_PATH="$(pwd)/data/ephemeris/swiss_ephe_files"
export ASTRO_LOG_LEVEL=DEBUG
```

---

## 7. CI/CD Hardware Profile

GitHub Actions runners used for automated testing:

| Workflow                        | Runner                 | Memory | Disk   |
| ------------------------------- | ---------------------- | ------ | ------ |
| `ci.yml` (unit tests)           | `ubuntu-latest`        | 7 GB   | 14 GB  |
| `data-analysis.yml` (weekly)    | `ubuntu-latest`        | 7 GB   | 14 GB  |
| `publish-research.yml` (Quarto) | `ubuntu-latest`        | 7 GB   | 14 GB  |
| Phase IV ML (planned)           | Self-hosted GPU runner | 64 GB  | 500 GB |

---

## 8. Performance Benchmarks

Expected runtimes on the recommended environment (Apple M2 Pro, 16 GB RAM):

| Task                                              | Expected Runtime |
| ------------------------------------------------- | ---------------- |
| Generate He line ratio lookup (full grid)         | ~45 seconds      |
| Run pellet ablation ODE (single shot)             | < 5 seconds      |
| Monte Carlo κ-distrib. (10⁶ particles)            | ~90 seconds      |
| Generate 100-year planetary ephemeris (daily)     | ~3 minutes       |
| Full aspect matrix (10 bodies, 36,500 time-steps) | ~8 minutes       |
| Full retrograde scan (10 planets, 100 years)      | ~2 minutes       |

---

_When in doubt about environment configuration, run `make environment-check`
(defined in `Makefile`) to execute an automated compatibility verification script._
