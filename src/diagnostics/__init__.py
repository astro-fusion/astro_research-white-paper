"""src/diagnostics/__init__.py.

Plasma Physics Diagnostic Engines
===================================
This package provides executable implementations of the mathematical models
described in `papers/physics/`. All modules are designed as pure-computation
engines — no external I/O, no database calls.

Modules
-------
line_ratio_spectroscopy : Helium CR model line ratio lookup generation
pellet_ablation         : 1-D pellet ODE solver with shielding
kappa_simulator         : Relativistic κ-distribution Monte Carlo
electron_density_solver : n_e and T_i extraction from spectral data
"""
