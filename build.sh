#!/bin/bash

# Vedic Astrology Core Build Script
# Supports building use cases and core documentation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration - hardcoded to numerology use case (only supported use case)
USE_CASE="numerology"
FORMATS=("html" "pdf")
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

# Set paths based on use case (currently only numerology is supported)
PROJECT_DIR="use_cases/numerology/manuscripts"
BUILD_DIR="use_cases/numerology/_book"
SOURCE_FILE="manuscript.qmd"  # Relative to PROJECT_DIR

# Check if quarto is installed
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v quarto &> /dev/null; then
        log_error "Quarto is not installed. Please install it from https://quarto.org/docs/get-started/"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed."
        exit 1
    fi

    log_success "All dependencies found"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_warning "requirements.txt not found, skipping Python dependencies"
    fi
}

# Clean previous builds
clean_build() {
    log_info "Cleaning previous builds..."

    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
        log_success "Previous build directory cleaned"
    fi

    # Clean Quarto cache
    quarto render --clean 2>/dev/null || true
}

# Build specific format
build_format() {
    local format=$1
    log_info "Building $format format..."

    # Save current directory and change to project directory for quarto
    local original_dir=$(pwd)
    cd "$PROJECT_DIR" || { log_error "Failed to change to project directory: $PROJECT_DIR"; return 1; }

    case $format in
        "html")
            quarto render "$SOURCE_FILE" --to html --output-dir "$BUILD_DIR/html"
            ;;
        "pdf")
            quarto render "$SOURCE_FILE" --to pdf --output-dir "$BUILD_DIR/pdf"
            ;;
        "docx")
            quarto render "$SOURCE_FILE" --to docx --output-dir "$BUILD_DIR/docx"
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
    else
        log_error "$format build failed"
        return 1
    fi
}

# Build all formats
build_all() {
    log_info "Building all formats..."

    for format in "${FORMATS[@]}"; do
        if ! build_format "$format"; then
            log_error "Build failed for format: $format"
            return 1
        fi
    done

    log_success "All formats built successfully"
}

# Preview build
preview_build() {
    log_info "Starting preview server..."

    if [ -d "$BUILD_DIR" ]; then
        # Find the first HTML file
        HTML_FILE=$(find "$BUILD_DIR" -name "*.html" | head -1)
        if [ -n "$HTML_FILE" ]; then
            log_info "Opening preview: $HTML_FILE"
            # On macOS, use open; on Linux use xdg-open
            if [[ "$OSTYPE" == "darwin"* ]]; then
                open "$HTML_FILE"
            else
                xdg-open "$HTML_FILE" 2>/dev/null || log_warning "Could not open browser automatically"
            fi
        fi
    else
        log_error "No build directory found. Run build first."
        exit 1
    fi
}

# Show usage
usage() {
    echo "Vedic Numerology-Astrology Build Script"
    echo ""
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  all        Build all formats (html, pdf)"
    echo "  html       Build HTML format only"
    echo "  pdf        Build PDF format only"
    echo "  docx       Build DOCX format only"
    echo "  clean      Clean build artifacts"
    echo "  preview    Preview built HTML in browser"
    echo "  check      Check dependencies"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verbose  Enable verbose output"
    echo ""
    echo "Examples:"
    echo "  $0 all          # Build everything"
    echo "  $0 html         # Build HTML only"
    echo "  $0 clean && $0 all  # Clean and rebuild"
    echo "  $0 preview      # Preview after building"
}

# Main function
main() {
    local command="all"
    local verbose=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            all|html|pdf|docx|clean|preview|check)
                command=$1
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    log_info "Vedic Numerology-Astrology Build System"
    log_info "======================================"

    case $command in
        "check")
            check_dependencies
            ;;
        "clean")
            clean_build
            ;;
        "html")
            check_dependencies
            install_dependencies
            build_format "html"
            ;;
        "pdf")
            check_dependencies
            install_dependencies
            build_format "pdf"
            ;;
        "docx")
            check_dependencies
            install_dependencies
            build_format "docx"
            ;;
        "all")
            check_dependencies
            install_dependencies
            clean_build
            build_all
            ;;
        "preview")
            preview_build
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac

    if [ $? -eq 0 ]; then
        log_success "Build script completed successfully!"
        if [ "$command" = "all" ] || [ "$command" = "html" ]; then
            log_info "Output available in: $BUILD_DIR/"
        fi
    else
        log_error "Build script failed!"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"