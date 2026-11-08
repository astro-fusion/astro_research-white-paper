# Studies

One folder per study. Each study compares a set of classical Vedic principles
with recorded events and reports what it finds, positive, null or mixed.

| Study | Question | Status |
|---|---|---|
| [gold_market](gold_market/README.md) | Do classical planetary configurations coincide with changes in XAU/USD returns? | Results withdrawn 2026-11-08, re-analysis pending |
| [earthquake](earthquake/README.md) | Does the rate of M5+ earthquakes change while specific configurations (Mars-Ketu, malefic clusters) hold? | Results withdrawn 2026-11-08, re-analysis pending |
| [numerology_vs_astrology](numerology_vs_astrology/README.md) | Do date numerology and the Moon's nakshatra lord name the same planet more often than chance? | Re-analysis pending (sidereal correction) |
| [remedy_conflict_matrix](remedy_conflict_matrix/README.md) | How should contradictory remedial prescriptions be detected and resolved? | Design notes |

See [CORRECTIONS.md](../CORRECTIONS.md) for what was withdrawn and why.

## Layout of a study

```
studies/<name>/
  README.md     what the study asks, status, how to run
  paper/        the .qmd manuscript, sections/, references; drafts/ holds superseded drafts (not rendered)
  scripts/      pipeline scripts
  data/         generated or fetched inputs (gitignored; documented in the study README)
  figures/      committed only when produced by this study's scripts and referenced by paper/
  tables/       small committed result tables
  artifacts/    generated output (gitignored)
```

Paths are resolved through [`studies/_paths.py`](_paths.py) (`REPO_ROOT`,
`DATA_ROOT`, `SNAPSHOT_ROOT`, `study_dir(name)`, `artifacts_dir(name)`), so
scripts run from any working directory.
