
.PHONY: help pdfs clean release

help:
	@echo "Available commands:"
	@echo "  make pdfs     - Generate all whitepaper PDFs locally"
	@echo "  make release  - Generate PDFs, add to git, and push (interactive)"
	@echo "  make clean    - Remove generated PDFs"

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
	pip install -r config/requirements/requirements.txt
	pip install pre-commit
	pre-commit install

format:
	isort src/ tests/
	black src/ tests/

lint:
	isort --check-only --diff src/ tests/
	black --check src/ tests/

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
