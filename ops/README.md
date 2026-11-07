# ⚙️ ops/ — DevOps, Configuration & Deployment

The `ops/` directory contains all **infrastructure, configuration, and automation** files. This keeps DevOps concerns cleanly separated from application and research code.

---

## 📁 Structure

```
ops/
├── Makefile                 ← Build & workflow automation (start here!)
├── config/                  ← YAML configuration files
│   ├── planets.yml          ← Planet definitions and dignities
│   ├── nakshatras.yml       ← Nakshatra catalog
│   └── ...
├── requirements.txt         ← Base runtime dependencies
├── requirements-api.txt     ← API-specific dependencies
├── requirements-app.txt     ← Web app dependencies
├── requirements-colab.txt   ← Google Colab / notebook dependencies
├── railway.json             ← Railway.app deployment config
└── render.yaml              ← Render.com deployment config
```

---

## 🛠️ Makefile Targets

```bash
make help         # Show all available targets
make install      # Install all dependencies (base + dev)
make build        # Run full research pipeline and render reports
make build-html   # Build HTML research site only
make test         # Run the full test suite
make lint         # Run flake8 linter
make format       # Auto-format with Black + isort
make quality-gate # lint + type-check + tests (run before every PR)
make clean        # Remove build artifacts, caches
make docs         # Build Sphinx API documentation
```

---

## 📦 Requirements Files

| File                     | Use Case                         | Install Command                             |
| ------------------------ | -------------------------------- | ------------------------------------------- |
| `requirements.txt`       | Base runtime — all main features | `pip install -r ops/requirements.txt`       |
| `requirements-api.txt`   | API server only                  | `pip install -r ops/requirements-api.txt`   |
| `requirements-app.txt`   | Web application                  | `pip install -r ops/requirements-app.txt`   |
| `requirements-colab.txt` | Google Colab / Jupyter notebooks | `pip install -r ops/requirements-colab.txt` |

For development, use the `pyproject.toml` extras instead:

```bash
pip install -e ".[dev]"   # Includes all dev tools (pytest, black, mypy, etc.)
```

---

## 🚀 Deployment

### Railway.app

```bash
# Deploy to Railway (requires Railway CLI)
railway up
```

Config in `railway.json` — sets environment variables, build command, and start command.

### Render.com

Config in `render.yaml` — defines web service, environment, and build steps.

### GitHub Actions (CI/CD)

CI/CD is defined in [`.github/workflows/`](../.github/workflows/). See the [workflows README](../.github/workflows/README.md) for details.

---

## ⚙️ Configuration Files (`config/`)

The YAML files in `config/` define the **classical knowledge base** used by the library:

| File                | Contents                                                     |
| ------------------- | ------------------------------------------------------------ |
| `planets.yml`       | Planet definitions: ruling signs, exaltations, debilitations |
| `nakshatras.yml`    | 27 Nakshatra definitions with lords and characteristics      |
| `dignity_rules.yml` | Classical dignity scoring rules                              |
| `dasha_periods.yml` | Vimshottari Dasha period lengths (in years)                  |

These files are the **authoritative source of truth** for classical Vedic rules. If you spot a classical rule that's missing or wrong, open a [bug report](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=bug_report.yml).

---

## 🔧 Pre-commit Hooks

Hooks are configured in `.pre-commit-config.yaml`. Install them once:

```bash
pip install pre-commit
pre-commit install
# Now they run automatically on every `git commit`
```

Hooks included: `black`, `isort`, `flake8`, `yamllint`, `trailing-whitespace`, `end-of-file-fixer`.
