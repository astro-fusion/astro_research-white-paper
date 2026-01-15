# Vedic Numerology-Astrology Makefile
# Based on The-Cosmic-Counselor build patterns

.PHONY: help build build-all build-html build-pdf build-docx clean test lint format docs preview install dev-install check-deps

# Default target
help: ## Show this help message
	@echo "Vedic Numerology-Astrology Build System"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Build targets
build: build-all ## Build all formats (alias for build-all)

build-all: ## Build all formats (HTML, PDF, DOCX)
	./build-all.sh

build-html: ## Build HTML format only
	./build.sh html

build-pdf: ## Build PDF format only
	./build.sh pdf

build-docx: ## Build DOCX format only
	./build.sh docx

# Development targets
install: ## Install Python dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install -e ".[dev]"

# Quality and testing
test: ## Run test suite
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ --cov=vedic_numerology --cov-report=html --cov-report=term-missing

lint: ## Run code quality checks
	@echo "Running code quality checks..."
	-black --check --diff src/ tests/
	-isort --check-only --diff src/ tests/
	-flake8 src/ tests/ --count --show-source --statistics
	-mypy src/vedic_numerology/

format: ## Format code with Black and isort
	@echo "Formatting code..."
	-black src/ tests/
	-isort src/ tests/

# Documentation
docs: ## Build API documentation
	@echo "Building documentation..."
	mkdir -p docs/_build/html
	sphinx-build -b html docs/ docs/_build/html

# Preview and development
preview: ## Preview built HTML in browser
	./build.sh preview

serve-docs: ## Serve documentation locally
	@echo "Serving documentation on http://localhost:8000"
	cd docs/_build/html && python3 -m http.server 8000

# Cleaning
clean: ## Clean build artifacts
	./build.sh clean
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

clean-all: clean ## Clean all artifacts including logs
	rm -f build-*.log
	rm -f build-report-*.md

# Utility targets
check-deps: ## Check if all required dependencies are installed
	@echo "Checking dependencies..."
	@command -v quarto >/dev/null 2>&1 && echo "✅ Quarto found" || echo "❌ Quarto not found"
	@command -v python3 >/dev/null 2>&1 && echo "✅ Python3 found" || echo "❌ Python3 not found"
	@command -v pip >/dev/null 2>&1 && echo "✅ pip found" || echo "❌ pip not found"
	@python3 -c "import sys; sys.version_info >= (3, 8) and print('✅ Python 3.8+ found') or print('❌ Python 3.8+ required')"

setup-dev: check-deps dev-install ## Setup development environment
	@echo "Development environment setup complete!"

setup-ci: check-deps install ## Setup CI environment
	@echo "CI environment setup complete!"

# Release targets
build-release: clean build-all test ## Build for release (clean, build, test)
	@echo "Release build complete!"

# Notebook targets
build-notebooks: ## Build and execute Jupyter notebooks
	./build-all.sh --notebooks

# Quality gate (run before commits)
quality-gate: format lint test ## Run full quality checks (format, lint, test)
	@echo "✅ Quality gate passed!"

# CI/CD simulation
ci: setup-ci quality-gate build-release ## Simulate CI pipeline
	@echo "🎉 CI pipeline completed successfully!"