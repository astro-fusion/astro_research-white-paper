Vedic Numerology-Astrology Integration System
==============================================

.. image:: https://img.shields.io/badge/python-3.8+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python Version

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License

.. image:: https://img.shields.io/badge/Quarto-1.3+-purple.svg
   :target: https://quarto.org/
   :alt: Quarto

A comprehensive computational framework for integrating Vedic Numerology (Anka Jyotish) with Vedic Astrology (Parashari Jyotish) using high-precision Swiss Ephemeris calculations.

Overview
--------

This system provides quantitative analysis of how planetary positions support or contradict numerological potentials through temporal analysis and interactive visualizations.

Key Features
------------

🔢 **Vedic Numerology Engine**
   - Mulanka (Birth Number) and Bhagyanka (Destiny Number) calculations
   - Sunrise-corrected birth number calculations
   - Advanced numerological combinations and interpretations

🪐 **Sidereal Astrology Integration**
   - Swiss Ephemeris backend with 0.1 arcsecond accuracy
   - Lahiri Ayanamsa traditional Chitra Paksha system
   - Complete birth charts with all planets and key points

📊 **Dignity & Strength Analysis**
   - Classical dignity scoring (Moolatrikona, own sign, exaltation)
   - Quantitative strength metrics (0-100 planetary power)
   - Aspect analysis and planetary relationship patterns

📈 **Temporal Dynamics**
   - Support trajectory analysis over time
   - Planetary transit influence mapping
   - Life period analysis with major and sub-period effects

🎨 **Advanced Visualizations**
   - Interactive Plotly-powered dynamic charts
   - Publication-ready high-DPI static plots
   - Side-by-side numerology vs. astrology comparisons

Installation
------------

.. code-block:: bash

   pip install vedic-numerology-astrology

Quick Start
-----------

.. code-block:: python

   from vedic_numerology import analyze_birth_chart

   # Analyze birth data
   result = analyze_birth_chart("1984-08-27", "10:30", 28.6139, 77.1025)

   print(f"Mulanka: {result['mulanka']['number']} ({result['mulanka']['planet']})")
   print(f"Bhagyanka: {result['bhagyanka']['number']} ({result['bhagyanka']['planet']})")

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/getting_started
   user_guide/numerology_calculations
   user_guide/astrology_integration
   user_guide/visualization
   user_guide/advanced_usage

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules
   api/vedic_numerology
   api/astrology
   api/numerology
   api/dignity
   api/visualization
   api/utils

.. toctree::
   :maxdepth: 2
   :caption: Development

   development/contributing
   development/testing
   development/build_system

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _GitHub Repository: https://github.com/astro-fusion/numerology-white-paper
.. _Issue Tracker: https://github.com/astro-fusion/numerology-white-paper/issues
.. _Documentation: https://numerology-white-paper.readthedocs.io/