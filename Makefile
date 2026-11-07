
# ==========================================
# 🪐 Vedic Astrology Research - Toolkit
# ==========================================

.PHONY: help install artifacts pdfs build clean test quality-gate

# Default target
help:
	@echo "Vedic Astrology Research Platform - Developer Tools"
	@echo "--------------------------------------------------"
	@echo "Available commands:"
	@echo "  make install      - Setup venv and install dependencies"
	@echo "  make artifacts    - Generate data artifacts and figures (Python)"
	@echo "  make pdfs         - Generate research paper PDFs (Quarto)"
	@echo "  make build        - Run artifacts + pdfs"
	@echo "  make clean        - Remove build artifacts and temporary files"
	@echo "  make test         - Run test suite"
	@echo "  make quality-gate - Run linting, type checking, and tests"

install:
	@echo "🚀 Setting up development environment..."
	python3 -m venv .venv
	@echo "Installing dependencies from ops/requirements.txt..."
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -r ops/requirements.txt
	@echo "✅ Setup complete. Use 'source .venv/bin/activate' to enter the environment."

artifacts:
	@echo "📊 Generating research artifacts..."
	@. .venv/bin/activate && python3 research/scripts/generate_artifacts.py

pdfs:
	@echo "📄 Rendering research papers to PDF..."
	@bash research/scripts/generate_pdfs.sh

build: artifacts pdfs
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
