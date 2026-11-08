
# ==========================================
# 🪐 Vedic Astrology Research - Toolkit
# ==========================================

.PHONY: help install check-data artifacts pdfs build clean test quality-gate

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
	@echo "  make test         - Run test suite"
	@echo "  make quality-gate - Run linting, type checking, and tests"

install:
	@echo "🚀 Setting up development environment..."
	python3 -m venv .venv
	@echo "Installing dependencies from pyproject.toml (lock: ops/requirements.lock.txt)..."
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -e ".[dev]"
	@echo "✅ Setup complete. Use 'source .venv/bin/activate' to enter the environment."

REQUIRED_DATA = data/raw/gold_prices.csv data/processed/aligned_planetary_data.csv

check-data:
	@echo "Checking required input data..."
	@missing=0; for f in $(REQUIRED_DATA); do \
	  if [ ! -f "$$f" ]; then echo "MISSING: $$f"; missing=1; continue; fi; \
	  sha=$$(shasum -a 256 "$$f" | cut -d' ' -f1); \
	  rows=$$(( $$(wc -l < "$$f") - 1 )); \
	  echo "$$f  sha256=$$sha  rows=$$rows"; \
	done; \
	if [ $$missing -ne 0 ]; then echo "check-data failed: required data files are missing"; exit 1; fi

artifacts:
	@echo "📊 Generating research artifacts..."
	@. .venv/bin/activate && python3 research/scripts/generate_artifacts.py

pdfs:
	@echo "📄 Rendering research papers to PDF..."
	@bash research/scripts/generate_pdfs.sh

build: check-data pdfs  # generate_pdfs.sh already runs generate_artifacts.py
	@echo "🎉 Platform build complete. Check the 'pdfs/' directory for outputs."

clean:
	@echo "🧹 Cleaning up..."
	rm -rf pdfs/*.pdf
	rm -rf research/reports/artifacts/*.csv
	rm -rf research/reports/artifacts/*.pdf
	rm -rf research/reports/artifacts/*.json
	rm -rf _site/
	rm -rf _freeze/
	rm -rf .quarto/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "✨ Workspace cleaned."

test:
	@. .venv/bin/activate && pytest tests/ -v

quality-gate:
	@echo "🛡️ Running quality checks..."
	@. .venv/bin/activate && flake8 libs/ src/ application/ research/ tests/
	@. .venv/bin/activate && mypy libs/vedic_astrology_core/ src/ application/
	@. .venv/bin/activate && pytest tests/
