
# ==========================================
# 🪐 Vedic Astrology Research - Toolkit
# ==========================================

.PHONY: help install check-data artifacts pdfs build clean test quality-gate validity

# Default target
help:
	@echo "Vedic Astrology Research Platform - Developer Tools"
	@echo "--------------------------------------------------"
	@echo "Available commands:"
	@echo "  make install      - Setup venv and install dependencies"
	@echo "  make artifacts    - Generate data artifacts and figures (Python)"
	@echo "  make pdfs         - Generate research paper PDFs (Quarto)"
	@echo "  make build        - Run check-data + pdfs (pdfs regenerates artifacts)"
	@echo "  make clean        - Remove build artifacts and temporary files"
	@echo "  make validity     - Run changed validity domains, append changelog, rebuild reports"
	@echo "  make test         - Run test suite"
	@echo "  make quality-gate - Run linting, type checking, and tests"

install:
	@echo "🚀 Setting up development environment..."
	python3 -m venv .venv
	@echo "Installing dependencies from pyproject.toml (lock: ops/requirements.lock.txt)..."
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -e ".[dev]"
	@echo "✅ Setup complete. Use 'source .venv/bin/activate' to enter the environment."

check-data:
	@python3 scripts/check_data.py

artifacts:
	@echo "📊 Generating research artifacts..."
	@. .venv/bin/activate && python3 scripts/generate_artifacts.py

pdfs:
	@echo "📄 Rendering research papers to PDF..."
	@bash scripts/generate_pdfs.sh

build: check-data pdfs  # generate_pdfs.sh already runs generate_artifacts.py
	@echo "🎉 Platform build complete. Check the 'pdfs/' directory for outputs."

clean:
	@echo "🧹 Cleaning up..."
	rm -rf pdfs/*.pdf
	find studies -path '*/artifacts/*' ! -name .gitkeep -type f -delete
	rm -rf _site/
	rm -rf _freeze/
	rm -rf .quarto/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "✨ Workspace cleaned."

# Principle validity reports (ADR-007 WP-74). Registers nothing. Once pyproject.toml
# gains the astro-validity entry point (WP-18) this is `astro-validity all`.
validity:
	@. .venv/bin/activate && python -m vedic_astrology_core.validity.cli all

test:
	@. .venv/bin/activate && pytest tests/ -v

quality-gate:
	@echo "🛡️ Running quality checks..."
	@. .venv/bin/activate && black --check libs/ tools/ application/ scripts/ studies/ tests/
	@. .venv/bin/activate && isort --check-only libs/ tools/ application/ scripts/ studies/ tests/
	@. .venv/bin/activate && flake8 libs/ tools/ application/ scripts/ studies/ tests/
	@. .venv/bin/activate && mypy libs/vedic_astrology_core/ application/
	@. .venv/bin/activate && pytest tests/
