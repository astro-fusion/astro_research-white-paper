# Corrections

## 2026-11-09: moolatrikona degree ranges corrected to BPHS 3.51-54

**What was wrong.** `MOOLATRIKONA_TABLE` in
`libs/vedic_astrology_core/dignity/exaltation_matrix.py` did not match the
source it is meant to encode, BPHS ch. 3 v. 51-54 (Santhanam 1984). Mars was
Aries 0-18 (BPHS: "Mars has the first 12 degrees in Aries"), Jupiter
Sagittarius 0-13 (BPHS: "the first one third of Sagittarius", 0-10), Venus
Libra 0-10 (BPHS: "divides Libra into two halves keeping the first", 0-15),
the Moon Taurus 4-30 (BPHS: "after the first 3 degrees", 3-30) and Mercury
Virgo 16-20 (BPHS: "the first 15 degrees are exaltation zone, the next 5
degrees Moola-Trikona", 15-20). `is_in_moolatrikona` also included the end
degree, so the Sun at exactly Leo 20 was moolatrikona and the Moon at exactly
Gemini 0 was in its Taurus moolatrikona. The Sun and Saturn ranges were
right. The deep-exaltation and deep-debilitation degrees (BPHS 3.49-50) were
checked and were right.

**Since when.** The table has carried these values since the project
reorganisation (commit 9ddd511, 2026-02-19); the `dignity_in` rule predicate
has read it since it was added on 2026-11-08 (commit c362c7e).

**What changed.** The five ranges now follow BPHS 3.51-54 and every range is
half-open `[start, end)`. Each row cites its verse. `tests/test_dignity.py`
pins all seven moolatrikona ranges, their boundaries and the seven
deep-exaltation degrees. The Vedic table in
`papers/astrology/06_essential_dignity_scoring.md` now shows Moon 3-30 and
Mercury 15-20.

**Results affected.**

- The rule predicate `dignity_in` with `moolatrikona` (through
  `dignities_of`), `get_dignity_type`, and the `DignityScorer` base score
  change for Mars at Aries 12-18 (now own sign), Jupiter at Sagittarius
  10-13 (now own sign), Venus at Libra 10-15 (now moolatrikona), the Moon at
  Taurus 3-4 and Mercury at Virgo 15-16 (now moolatrikona), and at the exact
  end degrees. The catalogue rules that use `moolatrikona`
  (`rules/financial/practitioner/vyapar_ratna_inverse_dignity_gold.yaml`,
  for the Sun and Jupiter) keep their recorded reference-case outcomes;
  those cases do not fall in the changed ranges.
- The numerology-versus-astrology study scores dignity through
  `DignityScorer`; its dignity figures are already being recomputed under
  (c) of the 2026-11-08 entry and will use the corrected table.
- The public benchmark's dignity gold was generated from this engine and
  carries the old ranges. It will be regenerated and re-pinned to this
  commit.

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
