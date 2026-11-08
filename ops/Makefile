
.PHONY: help check-data pdfs clean release

help:
	@echo "Available commands:"
	@echo "  make check-data - Verify required input data (paths from studies/_paths.py)"
	@echo "  make pdfs     - Generate all whitepaper PDFs locally"
	@echo "  make release  - Generate PDFs, add to git, and push (interactive)"
	@echo "  make clean    - Remove generated PDFs"

check-data:
	@python3 scripts/check_data.py

pdfs:
	@./scripts/generate_pdfs.sh

release: pdfs
	@echo "Generated PDFs. Preparing to commit..."
	@git add pdfs/*.pdf
	@echo "PDFs added to staging. Please run 'git commit' and 'git push' manually to complete the release, or I can do it."
	@echo "Run: git commit -m 'chore: update whitepaper PDFs' && git push"

clean:
	rm -rf pdfs/*.pdf

install:
	pip install -e ".[dev]"
	pip install pre-commit
	pre-commit install

format:
	isort libs/ tools/ application/ scripts/ studies/ tests/
	black libs/ tools/ application/ scripts/ studies/ tests/

lint:
	isort --check-only --diff libs/ tools/ application/ scripts/ studies/ tests/
	black --check libs/ tools/ application/ scripts/ studies/ tests/

test:
	pytest

validate: lint test
	@echo "Running local validation..."
	@if command -v act >/dev/null 2>&1; then \
		echo "Running GitHub Actions locally with act..."; \
		act -j test-sample-data; \
	else \
		echo "act not found, skipping local CI simulation."; \
	fi
