#!/bin/bash

# Comprehensive Build Script for Vedic Numerology-Astrology
# Based on The-Cosmic-Counselor automation patterns

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BUILD_ID="build-${TIMESTAMP}"
LOG_FILE="build-${TIMESTAMP}.log"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_header() {
    echo -e "${PURPLE}================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}$1${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}================================${NC}" | tee -a "$LOG_FILE"
}

# Check system requirements
check_system() {
    log_header "System Requirements Check"

    # Check OS
    case "$OSTYPE" in
        linux-gnu*)
            log_info "Detected Linux system"
            ;;
        darwin*)
            log_info "Detected macOS system"
            ;;
        *)
            log_warning "Unknown OS: $OSTYPE - proceeding anyway"
            ;;
    esac

    # Check required tools
    local required_tools=("quarto" "python3" "pip")
    local missing_tools=()

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install missing tools and try again"
        exit 1
    fi

    log_success "All system requirements met"
}

# Setup Python environment
setup_python() {
    log_header "Python Environment Setup"

    # Check Python version
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_info "Python version: $python_version"

    # Install/upgrade pip
    log_info "Upgrading pip..."
    python3 -m pip install --upgrade pip

    # Install requirements
    if [ -f "requirements.txt" ]; then
        log_info "Installing Python dependencies..."
        pip install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_warning "requirements.txt not found"
    fi

    # Install Quarto Python dependencies if available
    if [ -f "requirements-colab.txt" ]; then
        log_info "Installing Colab dependencies..."
        pip install -r requirements-colab.txt
    fi

    # Install development dependencies if building docs
    if [ "$build_documentation" = "true" ] && [ -f "pyproject.toml" ]; then
        log_info "Installing development dependencies..."
        pip install -e ".[dev]"
    fi
}

# Build manuscript in multiple formats
build_manuscript() {
    local format=$1
    local use_case=${2:-numerology}

    log_info "Building $use_case manuscript in $format format..."

    # Set paths based on use case
    local project_dir=""
    local output_dir=""
    case $use_case in
        "numerology")
            project_dir="use_cases/numerology/manuscripts"
            output_dir="use_cases/numerology/_book/${format}"
            ;;
        *)
            log_error "Unknown use case: $use_case"
            return 1
            ;;
    esac

    # Create output directory
    mkdir -p "$output_dir"

    # Save current directory and change to project directory
    local original_dir=$(pwd)
    cd "$project_dir" || { log_error "Failed to change to project directory: $project_dir"; return 1; }

    case $format in
        "html")
            quarto render manuscript.qmd --to html \
                --output-dir "$output_dir" \
                --execute \
                --cache \
                2>&1 | tee -a "$LOG_FILE"
            ;;
        "pdf")
            quarto render manuscript.qmd --to pdf \
                --output-dir "$output_dir" \
                --execute \
                --cache \
                2>&1 | tee -a "$LOG_FILE"
            ;;
        "docx")
            quarto render manuscript.qmd --to docx \
                --output-dir "$output_dir" \
                --execute \
                --cache \
                2>&1 | tee -a "$LOG_FILE"
            ;;
        *)
            log_error "Unknown format: $format"
            cd "$original_dir"
            return 1
            ;;
    esac

    # Return to original directory
    cd "$original_dir"

    if [ $? -eq 0 ]; then
        log_success "$format build completed"
        return 0
    else
        log_error "$format build failed"
        return 1
    fi
}

# Build API documentation
build_docs() {
    log_header "Building API Documentation"

    if [ ! -d "docs/" ]; then
        log_warning "docs/ directory not found, skipping documentation build"
        return 0
    fi

    # Create docs output directory
    mkdir -p docs/_build/html

    # Build Sphinx documentation
    if [ -f "docs/conf.py" ]; then
        log_info "Building Sphinx documentation..."
        sphinx-build -b html docs/ docs/_build/html 2>&1 | tee -a "$LOG_FILE"
        log_success "Sphinx documentation built"
    else
        log_warning "Sphinx configuration not found, skipping Sphinx build"
    fi
}

# Run tests
run_tests() {
    log_header "Running Test Suite"

    if [ ! -d "tests/" ]; then
        log_warning "tests/ directory not found, skipping tests"
        return 0
    fi

    log_info "Running tests with coverage..."
    if python3 -m pytest tests/ --cov=vedic_numerology --cov-report=html --cov-report=term-missing -v 2>&1 | tee -a "$LOG_FILE"; then
        log_success "All tests passed"
        return 0
    else
        log_error "Some tests failed"
        return 1
    fi
}

# Run code quality checks
run_quality_checks() {
    log_header "Code Quality Checks"

    local quality_passed=true

    # Black code formatting check
    if command -v black &> /dev/null; then
        log_info "Checking code formatting with Black..."
        if black --check --diff src/ tests/ 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Code formatting check passed"
        else
            log_error "Code formatting issues found"
            quality_passed=false
        fi
    fi

    # isort import sorting check
    if command -v isort &> /dev/null; then
        log_info "Checking import sorting with isort..."
        if isort --check-only --diff src/ tests/ 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Import sorting check passed"
        else
            log_error "Import sorting issues found"
            quality_passed=false
        fi
    fi

    # mypy type checking
    if command -v mypy &> /dev/null; then
        log_info "Running type checking with mypy..."
        if mypy src/vedic_numerology/ 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Type checking passed"
        else
            log_error "Type checking failed"
            quality_passed=false
        fi
    fi

    # flake8 linting
    if command -v flake8 &> /dev/null; then
        log_info "Running linting with flake8..."
        if flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Linting check passed"
        else
            log_error "Linting issues found"
            quality_passed=false
        fi
    fi

    if [ "$quality_passed" = true ]; then
        log_success "All quality checks passed"
        return 0
    else
        log_error "Some quality checks failed"
        return 1
    fi
}

# Build notebooks
build_notebooks() {
    log_header "Building Jupyter Notebooks"

    local notebooks_dir="use_cases/numerology/notebooks"
    if [ ! -d "$notebooks_dir" ]; then
        log_warning "notebooks/ directory not found at $notebooks_dir, skipping notebook build"
        return 0
    fi

    log_info "Executing notebooks..."
    for notebook in "$notebooks_dir"/*.ipynb; do
        if [ -f "$notebook" ]; then
            log_info "Processing $notebook..."
            jupyter nbconvert --to notebook --execute --inplace "$notebook" 2>&1 | tee -a "$LOG_FILE" || true
        fi
    done

    log_success "Notebook build completed"
}

# Generate build report
generate_report() {
    log_header "Build Report"

    local report_file="build-report-${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Vedic Numerology-Astrology Build Report

**Build ID:** $BUILD_ID
**Timestamp:** $(date)
**Build Status:** ${BUILD_STATUS:-Unknown}

## Build Configuration

- **Python Version:** $(python3 --version)
- **Quarto Version:** $(quarto --version 2>/dev/null || echo "Not available")
- **Operating System:** $OSTYPE

## Build Components

### Manuscript Formats
EOF

    # Check for built formats
    for format in html pdf docx; do
        if [ -d "_book/$format" ]; then
            echo "- ✅ **$format**: Built successfully" >> "$report_file"
            # List files
            find "_book/$format" -name "*.$format" -o -name "*.html" -o -name "*.pdf" -o -name "*.docx" | head -5 | sed 's/^/  - /' >> "$report_file"
        else
            echo "- ❌ **$format**: Not built" >> "$report_file"
        fi
    done

    cat >> "$report_file" << EOF

### Documentation
EOF

    if [ -d "docs/_build/html" ]; then
        echo "- ✅ **API Documentation**: Built successfully" >> "$report_file"
    else
        echo "- ❌ **API Documentation**: Not built" >> "$report_file"
    fi

    cat >> "$report_file" << EOF

### Testing & Quality
EOF

    if [ -d "htmlcov/" ]; then
        echo "- ✅ **Test Coverage**: Generated ($(find htmlcov/ -name "*.html" | wc -l) files)" >> "$report_file"
    else
        echo "- ❌ **Test Coverage**: Not generated" >> "$report_file"
    fi

    cat >> "$report_file" << EOF

## File Structure
\`\`\`
$(find _book/ -type f -name "*.html" -o -name "*.pdf" -o -name "*.docx" | head -10)
\`\`\`

## Logs
See detailed logs in: \`$LOG_FILE\`

---
*Generated by Vedic Numerology-Astrology Build System*
EOF

    log_success "Build report generated: $report_file"
}

# Main build function
main_build() {
    local build_manuscripts=true
    local build_documentation=true
    local run_tests_flag=true
    local run_quality=true
    local build_notebooks_flag=false

    log_header "Vedic Numerology-Astrology Comprehensive Build"
    log_info "Build ID: $BUILD_ID"
    log_info "Log file: $LOG_FILE"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-manuscript)
                build_manuscripts=false
                shift
                ;;
            --no-docs)
                build_documentation=false
                shift
                ;;
            --no-tests)
                run_tests_flag=false
                shift
                ;;
            --no-quality)
                run_quality=false
                shift
                ;;
            --notebooks)
                build_notebooks_flag=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Initialize build status
    BUILD_STATUS="In Progress"

    # Pre-build checks
    check_system
    setup_python

    # Build components
    local build_failed=false

    # Build manuscripts
    if [ "$build_manuscripts" = true ]; then
        log_header "Building Manuscripts"
        for format in html pdf; do
            if ! build_manuscript "$format"; then
                build_failed=true
            fi
        done
    fi

    # Build documentation
    if [ "$build_documentation" = true ]; then
        if ! build_docs; then
            build_failed=true
        fi
    fi

    # Run tests
    if [ "$run_tests_flag" = true ]; then
        if ! run_tests; then
            build_failed=true
        fi
    fi

    # Run quality checks
    if [ "$run_quality" = true ]; then
        if ! run_quality_checks; then
            build_failed=true
        fi
    fi

    # Build notebooks
    if [ "$build_notebooks_flag" = true ]; then
        build_notebooks
    fi

    # Generate report
    if [ "$build_failed" = false ]; then
        BUILD_STATUS="Success"
        log_success "🎉 All builds completed successfully!"
    else
        BUILD_STATUS="Failed"
        log_error "❌ Some builds failed - check logs for details"
    fi

    generate_report

    log_info "Build log available at: $LOG_FILE"
    log_info "Build report available at: build-report-${TIMESTAMP}.md"

    return $([ "$build_failed" = false ])
}

# Show usage
usage() {
    echo "Vedic Numerology-Astrology Comprehensive Build Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --no-manuscript    Skip manuscript builds"
    echo "  --no-docs         Skip documentation builds"
    echo "  --no-tests        Skip test execution"
    echo "  --no-quality      Skip code quality checks"
    echo "  --notebooks       Build and execute notebooks"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Full build (default)"
    echo "  $0 --no-tests              # Skip tests"
    echo "  $0 --notebooks             # Include notebook execution"
    echo "  $0 --no-manuscript --no-docs  # Minimal build"
}

# Main entry point
main() {
    case "${1:-}" in
        "-h"|"--help")
            usage
            exit 0
            ;;
        "")
            main_build "$@"
            ;;
        *)
            main_build "$@"
            ;;
    esac
}

# Run main function
main "$@"