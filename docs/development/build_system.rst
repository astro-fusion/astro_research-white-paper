Build System
============

The Vedic Numerology-Astrology Integration System uses a comprehensive build system designed for research software development.

Build Scripts
-------------

**Primary Build Scripts:**

.. code-block::

   build.sh          # Single-format builds
   build-all.sh      # Comprehensive builds with quality gates
   Makefile         # Development shortcuts

**Usage Examples:**

.. code-block:: bash

   # Quick HTML build
   ./build.sh html

   # Full build with all checks
   ./build-all.sh

   # Development shortcuts
   make build        # Build all formats
   make test         # Run tests
   make docs         # Build documentation

Build Formats
-------------

**HTML Format:**
- Interactive features enabled
- Responsive design
- Web-optimized assets

**PDF Format:**
- Print-ready layout
- High-resolution figures
- LaTeX-based rendering

**DOCX Format:**
- Microsoft Word compatible
- Editable content
- Office integration

**EPUB Format:**
- E-reader optimized
- Mobile-friendly
- Standards compliant

Quarto Configuration
--------------------

**Main Configuration:** ``_quarto.yml``

Key features:
- Multi-format output
- Custom styling and themes
- Conditional content rendering
- Advanced cross-referencing

**Custom Filters:**
- Format-specific processing
- Interactive content handling
- Content adaptation

**Styling System:**
- Custom CSS for HTML output
- LaTeX templates for PDF
- Responsive design patterns

Automated Builds
----------------

**GitHub Actions Workflows:**

.. code-block::

   .github/workflows/
   ├── ci.yml              # Main CI/CD pipeline
   ├── docs.yml            # Documentation builds
   ├── research-pdf.yml    # Research manuscript builds
   ├── publish-research.yml # Research publication
   └── data-analysis.yml   # Data analysis workflows

**CI/CD Pipeline Stages:**

1. **Quality Gates**
   - Code formatting (Black)
   - Import sorting (isort)
   - Linting (flake8)
   - Type checking (mypy)
   - Security scanning (Bandit, Safety)

2. **Testing**
   - Unit tests across Python versions
   - Integration tests
   - Coverage reporting
   - Performance benchmarks

3. **Building**
   - Multi-format manuscript compilation
   - API documentation generation
   - Artifact packaging

4. **Publishing**
   - PyPI package publishing
   - GitHub releases
   - Documentation deployment

Local Development
-----------------

**Development Setup:**

.. code-block:: bash

   # One-command setup
   make setup-dev

   # Manual setup
   pip install -r requirements.txt
   pip install -e ".[dev]"

**Development Workflow:**

.. code-block:: bash

   # Continuous development
   quarto preview manuscript.qmd    # Live preview
   make test                       # Run tests
   make quality-gate              # Code quality

**Build Optimization:**

.. code-block:: bash

   # Quick iteration
   ./build.sh html                # Fast HTML builds

   # Full validation
   make build-all                 # Complete build pipeline

   # Clean rebuild
   make clean && make build-all

Build Artifacts
---------------

**Output Structure:**

.. code-block::

   _book/
   ├── html/                      # Web version
   │   ├── manuscript.html
   │   ├── styles/
   │   └── assets/
   ├── pdf/                       # Print version
   │   └── manuscript.pdf
   ├── docx/                      # Office version
   │   └── manuscript.docx
   └── epub/                      # E-reader version
       └── manuscript.epub

   docs/_build/html/             # API documentation
   htmlcov/                      # Test coverage reports

**Artifact Management:**

- Automatic retention policies
- Versioned artifact naming
- Download links in CI/CD
- Integration with GitHub releases

Build Configuration
-------------------

**Environment Variables:**

.. code-block:: bash

   # Version information
   export VERSION="v1.0.0"

   # Build options
   export BUILD_DOCS=true
   export BUILD_NOTEBOOKS=false

   # Quarto options
   export QUARTO_PROFILE="production"

**Configuration Files:**

- ``pyproject.toml`` - Python packaging
- ``_quarto.yml`` - Quarto configuration
- ``styles/`` - Custom styling
- ``Makefile`` - Build shortcuts

Troubleshooting
---------------

**Common Build Issues:**

1. **Quarto Not Found:**
   .. code-block:: bash

      # Install Quarto
      # Visit: https://quarto.org/docs/get-started/

2. **Missing Dependencies:**
   .. code-block:: bash

      # Install all dependencies
      pip install -r requirements.txt
      pip install -e ".[dev]"

3. **PDF Build Failures:**
   .. code-block:: bash

      # Install TinyTeX
      quarto install tinytex

4. **Permission Errors:**
   .. code-block:: bash

      # Fix script permissions
      chmod +x build.sh build-all.sh

5. **Cache Issues:**
   .. code-block:: bash

      # Clear caches
      make clean
      quarto render --clean

**Debug Builds:**

.. code-block:: bash

   # Verbose output
   ./build-all.sh --verbose

   # Debug specific format
   quarto render manuscript.qmd --to html --log-level debug

   # Check Quarto configuration
   quarto check

Performance Optimization
------------------------

**Build Speed Improvements:**

1. **Caching:** Quarto and pip caching enabled
2. **Parallel Processing:** Multiple format builds in parallel
3. **Incremental Builds:** Only rebuild changed content
4. **Selective Builds:** Build only required formats

**Resource Optimization:**

- Memory-efficient processing
- Disk space management
- Network optimization for CI/CD
- Artifact compression

**Monitoring:**

- Build time tracking
- Resource usage monitoring
- Failure analysis and reporting

Advanced Features
-----------------

**Custom Build Scripts:**

Create custom build configurations for specific needs:

.. code-block:: bash

   #!/bin/bash
   # custom-build.sh

   # Custom build logic
   quarto render manuscript.qmd \
       --to html \
       --profile custom \
       --metadata title="Custom Title"

**Build Hooks:**

Integrate with external tools and services:

.. code-block:: python

   # build-hooks.py
   import subprocess
   import os

   def pre_build():
       """Run before build starts."""
       # Custom pre-build logic
       pass

   def post_build():
       """Run after build completes."""
       # Custom post-build logic
       # e.g., upload to CDN, send notifications
       pass

**CI/CD Integration:**

- Automated deployment to GitHub Pages
- Integration with external documentation hosts
- Notification systems for build status
- Integration with project management tools