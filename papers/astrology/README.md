# 🌌 papers/astrology/ — Computational Astrology White Papers

Mathematical and algorithmic frameworks for exhaustive astrological analysis.

## Paper Index

| #   | File                                                                                                     | Topic                                        | Key Formulas                                           |
| --- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------ | --------------------- | --------------------------------- | --------------------- | --- |
| 01  | [01_celestial_mechanics_and_ephemeris.md](01_celestial_mechanics_and_ephemeris.md)                       | Coordinate transforms + Swiss Ephemeris      | Ecliptic → equatorial transformation matrices          |
| 02  | [02_house_systems_and_polar_singularities.md](02_house_systems_and_polar_singularities.md)               | House systems + polar singularity routing    | ${\rm DSA}(\lambda, \varphi)$; fallback matrix         |
| 03  | [03_aspect_geometry_graph_theory.md](03_aspect_geometry_graph_theory.md)                                 | Aspect adjacency matrix + graph theory       | $a\_{ij} = \min(                                       | \lambda_i - \lambda_j | , 360° -                          | \lambda_i - \lambda_j | )$  |
| 04  | [04_temporal_inflection_retrogrades_progressions.md](04_temporal_inflection_retrogrades_progressions.md) | Retrograde detection + progressions calculus | $d\lambda_{\rm ecl}/dt$ sign changes; SP/SAD formulas  |
| 05  | [05_declination_out_of_bounds.md](05_declination_out_of_bounds.md)                                       | Declination OOB + parallel aspects           | $                                                      | \delta\_{\rm decl}    | > \varepsilon$; PAR/CPAR matrices |
| 06  | [06_essential_dignity_scoring.md](06_essential_dignity_scoring.md)                                       | Essential dignity O(1) hash maps             | $D(p, \lambda_{\rm ecl}) \in [-4, +10]$; normalisation |

## Exhaustiveness Coverage

These six papers collectively cover **all major astrological computational cases**:

- ✅ Celestial body positions (tropical and sidereal)
- ✅ All major house systems + polar fallback
- ✅ All classical aspects (9 types) + applying/separating orbs
- ✅ Synastry / composite cross-chart analysis
- ✅ Transit detection over multi-century time-series
- ✅ Retrograde stations, secondary progressions, solar arc directions
- ✅ Declination-based parallels and contra-parallels
- ✅ Out-of-Bounds Moon (and planet) detection
- ✅ Essential dignity scoring (Western and Vedic)

Symbol definitions: [SYMBOLOGY.md §II](../../SYMBOLOGY.md)
