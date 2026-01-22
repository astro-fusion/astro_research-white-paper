# Contributing to Vedic Numerology-Astrology Integration System

Thank you for your interest in contributing to the Vedic Numerology-Astrology Integration System! This document provides guidelines and information for contributors.

## 🌟 Ways to Contribute

### 📝 Content Contributions

* **Research Enhancement**: Add new case studies, improve methodologies, or expand theoretical foundations
* **Code Examples**: Create additional notebooks, scripts, or usage examples
* **Documentation**: Improve documentation, add tutorials, or create educational content
* **Bug Fixes**: Identify and fix issues in calculations, algorithms, or data processing
* **Feature Requests**: Propose new features or improvements to existing functionality

### 🔧 Technical Contributions

* **Code Quality**: Improve code structure, add tests, or enhance performance
* **Build System**: Improve build scripts, CI/CD pipelines, or deployment processes
* **Documentation**: Update API docs, improve README, or add code comments
* **Testing**: Add unit tests, integration tests, or performance benchmarks
* **Packaging**: Improve package configuration, dependencies, or distribution

### 🌍 Community Contributions

* **Issue Triage**: Help categorize and prioritize issues
* **Community Support**: Answer questions from other users
* **Translation**: Help translate documentation or content
* **Review**: Review pull requests and provide constructive feedback

## 🚀 Quick Start

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/astro-research-white-paper.git
cd astro-research-white-paper

# Set up upstream remote
git remote add upstream https://github.com/astro-fusion/astro_research-white-paper.git
```

### 2. Set Up Development Environment

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Install additional tools
pip install -r requirements-colab.txt

# Install Quarto (if not already installed)
# Download from: https://quarto.org/docs/get-started/
```

### 3. Verify Setup

```bash
# Run tests
pytest tests/ -v

# Build documentation
make docs

# Build manuscript
make build-pdf

# Run quality checks
make quality-gate
```

## 📋 Development Workflow

### 1. Choose an Issue

* Check the [Issues](https://github.com/astro-fusion/astro_research-white-paper/issues) page
* Look for issues labeled `good first issue` or `help wanted`
* Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
# Create and switch to a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-number-description
```

### 3. Make Changes

* Follow the coding standards outlined below
* Add tests for new functionality
* Update documentation as needed
* Ensure all tests pass

### 4. Commit Changes

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add new case study analysis

- Add Mars 1990 case study
- Include temporal analysis for 5-year period
- Add visualizations for planetary support patterns
- Update documentation with new example

Closes #123"

# Follow conventional commit format
# Types: feat, fix, docs, style, refactor, test, chore
```

### 5. Push and Create Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create a Pull Request on GitHub
# Include a clear description of changes
# Reference any related issues
```

## 📏 Coding Standards

### Python Code Style

* Follow [PEP 8](https://pep8.org/) style guidelines
* Use [Black](https://black.readthedocs.io/) for code formatting
* Use [isort](https://pycqa.github.io/isort/) for import sorting
* Use [flake8](https://flake8.pycqa.org/) for linting
* Use [mypy](https://mypy.readthedocs.io/) for type checking

### Code Formatting

```bash
# Format code
make format

# Or manually
black src/ tests/
isort src/ tests/

# Check formatting
black --check --diff src/ tests/
isort --check-only --diff src/ tests/
```

### Type Hints

```python
# Good: Use type hints
from typing import Optional, List, Dict

def calculate_mulanka(birth_date: str, birth_time: str, latitude: float, longitude: float) -> Dict[str, any]:
    # Function implementation
    pass

# Avoid: No type hints
def calculate_mulanka(birth_date, birth_time, latitude, longitude):
    pass
```

### Documentation

* Use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#381-docstrings)
* Document all public functions, classes, and modules
* Include examples in docstrings where appropriate

```python
def analyze_birth_chart(birth_date: str, birth_time: str, latitude: float, longitude: float) -> Dict:
    """Analyze birth chart using numerology and astrology integration.

    This function performs a comprehensive analysis of a birth chart by combining
    Vedic numerology calculations with sidereal astrology positions.

    Args:
        birth_date: Birth date in YYYY-MM-DD format
        birth_time: Birth time in HH:MM format (24-hour)
        latitude: Birth location latitude in decimal degrees
        longitude: Birth location longitude in decimal degrees

    Returns:
        Dictionary containing numerology results, planetary positions,
        dignity scores, and support analysis.

    Raises:
        ValueError: If birth_date or birth_time format is invalid

    Example:
        >>> result = analyze_birth_chart("1984-08-27", "10:30", 28.6139, 77.1025)
        >>> print(f"Mulanka: {result['mulanka']['number']}")
        Mulanka: 9
    """
    pass
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vedic_numerology --cov-report=html

# Run specific test file
pytest tests/test_numerology.py

# Run specific test
pytest tests/test_numerology.py::TestNumerologyCalculations::test_calculate_mulanka

# Run tests matching pattern
pytest -k "mulanka"
```

### Writing Tests

* Use `pytest` framework
* Follow naming convention: `test_*.py` for files, `test_*` for functions
* Use descriptive test names that explain what is being tested
* Include docstrings for complex tests
* Test edge cases and error conditions

```python
import pytest
from vedic_numerology.calculator import NumerologyCalculator

class TestNumerologyCalculations:
    """Test cases for numerology calculations."""

    def test_calculate_mulanka_basic(self):
        """Test basic Mulanka calculation."""
        calc = NumerologyCalculator()
        result = calc.calculate_mulanka("1984-08-27")

        assert result["number"] == 9
        assert result["planet"] == "Mars"
        assert "score" in result

    def test_calculate_mulanka_invalid_date(self):
        """Test Mulanka calculation with invalid date."""
        calc = NumerologyCalculator()

        with pytest.raises(ValueError, match="Invalid date format"):
            calc.calculate_mulanka("invalid-date")

    @pytest.mark.parametrize("birth_date,expected", [
        ("1984-08-27", 9),
        ("1990-05-15", 3),
        ("1975-01-11", 2),
    ])
    def test_calculate_mulanka_parametrized(self, birth_date, expected):
        """Test Mulanka calculation with multiple test cases."""
        calc = NumerologyCalculator()
        result = calc.calculate_mulanka(birth_date)

        assert result["number"] == expected
```

### Test Coverage

* Aim for >90% code coverage
* Include tests for edge cases and error conditions
* Test both success and failure scenarios
* Use mocking for external dependencies

## 📚 Documentation

### Building Documentation

```bash
# Build Sphinx documentation
make docs

# Serve documentation locally
make serve-docs

# Open in browser
open docs/_build/html/index.html
```

### Documentation Guidelines

* Keep README.md concise and focused on getting started
* Use Sphinx for API documentation
* Include code examples in docstrings
* Document configuration options and parameters
* Keep documentation up-to-date with code changes

## 🔧 Build System

### Using Make

```bash
# Show available targets
make help

# Full build
make build

# Quick HTML build
make build-html

# Clean build artifacts
make clean
```

### Using Build Scripts

```bash
# Quick single-format build
./build.sh html

# Comprehensive build with all checks
./build-all.sh

# Build with notebooks
./build-all.sh --notebooks
```

## 🎨 Manuscript Development

### Quarto Workflow

```bash
# Preview manuscript
quarto preview manuscript.qmd

# Build specific format
quarto render manuscript.qmd --to pdf

# Build all formats
quarto render
```

### Content Guidelines

* Maintain academic and professional tone
* Include proper citations and references
* Use clear, concise language
* Include visual elements (charts, diagrams)
* Test content in multiple formats (HTML, PDF, DOCX)

## 🔄 Pull Request Process

### Before Submitting

* ✅ All tests pass (`make test`)
* ✅ Code formatting is correct (`make format`)
* ✅ No linting errors (`make lint`)
* ✅ Documentation is updated
* ✅ Commit messages follow conventional format

### Pull Request Template

```
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update
- [ ] Code refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All tests pass

## Documentation
- [ ] README updated (if needed)
- [ ] API documentation updated
- [ ] Code comments added/updated

## Additional Notes
Any additional information or context.
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and quality checks
2. **Code Review**: Maintainers review code for quality and correctness
3. **Testing**: Additional testing may be requested
4. **Approval**: PR approved and merged by maintainers

## 🎯 Code of Conduct

This project follows a code of conduct to ensure a welcoming environment:

* **Respect**: Be respectful of differing viewpoints and experiences
* **Collaboration**: Work together constructively
* **Inclusivity**: Welcome contributions from people of all backgrounds
* **Professionalism**: Maintain professional communication
* **Ethics**: Respect the ethical nature of spiritual and research work

## 📞 Getting Help

* **Issues**: [GitHub Issues](https://github.com/astro-fusion/astro_research-white-paper/issues)
* **Discussions**: [GitHub Discussions](https://github.com/astro-fusion/astro_research-white-paper/discussions)
* **Documentation**: [Read the Docs](https://astro-research-white-paper.readthedocs.io/)

## 🙏 Recognition

Contributors are recognized in:
* GitHub repository contributors list
* CHANGELOG.md for significant contributions
* Manuscript acknowledgments section

Thank you for contributing to the Vedic Numerology-Astrology Integration System! 🌟