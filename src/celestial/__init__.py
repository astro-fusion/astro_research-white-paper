"""src/celestial/__init__.py.

Astrological Logic Engines
============================
This package provides executable implementations of the mathematical models
described in `papers/astrology/`. All modules are pure-computation engines.

Modules
-------
ephemeris_engine   : Swiss Ephemeris wrapper — celestial position computation
house_systems      : House cusp calculation with polar singularity fallback
aspect_matrix      : Graph-theory aspect adjacency matrix (NumPy vectorised)
retrograde_detector: Station detection via longitudinal velocity derivative
dignity_scoring    : Essential dignity O(1) hash-map scoring engine
"""
