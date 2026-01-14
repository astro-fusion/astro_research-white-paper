Getting Started
===============

Welcome to the Vedic Numerology-Astrology Integration System! This guide will help you get started with using the system for your research and analysis.

Installation
------------

Install the package using pip:

.. code-block:: bash

   pip install vedic-numerology-astrology

For development installation with all dependencies:

.. code-block:: bash

   git clone https://github.com/astro-fusion/numerology-white-paper.git
   cd numerology-white-paper
   pip install -e ".[dev]"

Quick Start
-----------

Basic numerology analysis:

.. code-block:: python

   from vedic_numerology import analyze_birth_chart

   # Analyze birth data (Delhi, India)
   result = analyze_birth_chart("1984-08-27", "10:30", 28.6139, 77.1025)

   print(f"Mulanka: {result['mulanka']['number']} ({result['mulanka']['planet']})")
   print(f"Bhagyanka: {result['bhagyanka']['number']} ({result['bhagyanka']['planet']})")

Advanced analysis with full astrological integration:

.. code-block:: python

   from vedic_numerology import VedicNumerologyAstrology

   vna = VedicNumerologyAstrology(
       birth_date="1984-08-27",
       birth_time="10:30",
       latitude=28.6139,
       longitude=77.1025
   )

   # Get comprehensive analysis
   support_analysis = vna.analyze_support_contradiction()
   report = vna.generate_report()

System Requirements
-------------------

- Python 3.8+
- Swiss Ephemeris library (automatically installed)
- For visualization: matplotlib, seaborn, plotly (optional)

Troubleshooting
---------------

Common issues and solutions:

**Import Error**: Make sure the package is properly installed.

.. code-block:: bash

   pip install --upgrade vedic-numerology-astrology

**Swiss Ephemeris Error**: The ephemeris data should be downloaded automatically. If not:

.. code-block:: bash

   pip install pyswisseph>=2.08.00

**Permission Error**: On some systems, you may need to install system dependencies:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install libswisseph-dev

   # macOS
   brew install swisseph

Next Steps
----------

- :doc:`numerology_calculations` - Learn about Vedic numerology calculations
- :doc:`astrology_integration` - Understand astrological integration
- :doc:`visualization` - Create charts and visualizations
- :doc:`advanced_usage` - Advanced features and customization