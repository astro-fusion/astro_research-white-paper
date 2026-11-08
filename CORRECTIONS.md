# Corrections

## 2026-11-08: results withdrawn pending re-analysis

A review of this repository found that several published figures and statistics
did not come from real data, and that the astronomical inputs used so far were
not what the papers describe. The affected results are withdrawn. Re-analysis
results will replace the withdrawn sections once they are computed from verified
data. The git history preserves the original files for audit.

### (a) Earthquake "predicted vs actual" and "Monte Carlo ΔAIC" figures

The figures `predicted_vs_actual.png` and `monte_carlo_distribution.png` were
generated from random numbers. The "actual" series was drawn from a Poisson
distribution, the "prediction" was that series plus noise, the null
distribution was drawn from a normal distribution, and the "real data" ΔAIC
line was a fixed value (7.5) typed into the plotting script. They are withdrawn,
together with the p-value quoted in their captions (p = 0.17). The plotting
function (`plot_simulated_model_outs` in
`research/use_cases/earthquake/scripts/generate_paper_figures.py`) has been
deleted.

Related figures that overlaid a simulated "Planetary Stress Index (Model)" on
real earthquakes, a simulated Mars "Shadbala" curve, and random "planetary
strength" charts are also withdrawn. The scripts that drew them now draw them
only with an explicit `--simulation` flag, under a `SIMULATED_` filename and a
"SIMULATED, NOT DATA" watermark.

### (b) Gold-market Granger, Molchan, permutation and periodogram results

The gold-market manuscript (`research/reports/manuscript.qmd`) reported a
stationarity table, a Lomb-Scargle periodogram, Granger causality tests, a
Molchan diagram and a Monte Carlo permutation test. These were computed from a
synthetic placeholder series, not market data: when the real input file was
absent, `research/scripts/generate_artifacts.py` wrote a seeded random walk
("gold") and sine waves ("planets") to the real data path, and later runs read
it as data. These results are withdrawn pending re-analysis on verified data.
The pipeline now exits with an error when its input is missing, and the
placeholder file and every artifact derived from it have been removed.

### (c) Tropical instead of sidereal positions; Ketu computed as Rahu

All planetary positions used so far were tropical rather than sidereal, because
the sidereal flag was never passed to the Swiss Ephemeris calls. Ketu was
computed as Rahu instead of the point opposite it. Every astrological feature
derived from these positions (signs, nakshatras, dignities, strengths, yogas,
dashas) is therefore being recomputed.

### (d) "DE440 / sub-arcsecond" ephemeris claim

Papers and documentation stated that positions came from the JPL DE440
ephemeris with sub-arcsecond precision. No Swiss Ephemeris data files were
present, so the library fell back to its built-in Moshier analytic ephemeris.
That claim is withdrawn. Methods sections now read: "Swiss Ephemeris library
with the built-in Moshier analytic ephemeris unless SE data files are
installed."
