# Registered report (Stage 1): testing classical Vedic astrological principles on past mundane events

Draft manuscript for the Registered Report track (Royal Society Open Science, or PCI Registered Reports).
Scope: past data only; no forecasting. The confirmatory runs are sealed and **have not been performed**.

| File | What it is |
|---|---|
| `manuscript.qmd` | The Stage 1 manuscript (Quarto). Every number is read at render time from committed files. |
| `references.bib` | Bibliography. Entries marked `TODO(owner)` must be checked at the publisher before submission. No DOI or page was invented; uncertain ones were left out. |
| `numbers_allowlist.txt` | The few bare tokens allowed in prose (stage numbers, chapter numbers, the name "Nino 3.4", three design constants of the planned year test). |

## Where the numbers come from

| Label in the manuscript | File |
|---|---|
| `eq`, `mon`, `gold` | `studies/validity/preview/{earthquake,monsoon,metals}/results.json` (explore period only; pilot, descriptive, no verdict) |
| `cert` | `studies/validity/calibration/certificate.json` |
| `mult` | `studies/project_multiplicity.json` |
| `eqold`, `goldold`, `silverold` | `studies/{earthquake,gold_market,silver_market}/artifacts/results.json` (earlier exploratory work; only the family sizes and the stale gold headline are read) |
| `plan(...)` helper | `studies/validity/domains/{earthquake,monsoon,metals}.yaml`, through the same strict accessor |
| computed in code cells | rule files under `rules/`, `research/incoming/texts/round5_local_books/verification.csv`, `studies/validity/sesoi_sources.yaml`, `data/registry/licences.yaml`, the sentence allow-list and design constants imported from `libs/vedic_astrology_core` |

One number is computed live: how many certified source files differ from the hashes in the certificate
(`git hash-object`), so it changes as the code changes.

## Render

```bash
QUARTO_PYTHON="$PWD/.venv/bin/python" quarto render papers/registered_report/manuscript.qmd --to html
```

Run from the repository root. PDF needs a TeX engine (none was installed when this was written).
The render writes `manuscript.html` and `manuscript_files/` beside the source. `*_files/` is ignored by git;
`manuscript.html` is not covered by a `.gitignore` rule today, so do not add it (or add a rule for `papers/**/*.html`).

## Results-key gate

```bash
.venv/bin/python tools/check_paper_keys.py papers/registered_report/manuscript.qmd \
  --results eq=studies/validity/preview/earthquake/results.json \
  --results mon=studies/validity/preview/monsoon/results.json \
  --results gold=studies/validity/preview/metals/results.json \
  --results cert=studies/validity/calibration/certificate.json \
  --results mult=studies/project_multiplicity.json \
  --results eqold=studies/earthquake/artifacts/results.json \
  --results goldold=studies/gold_market/artifacts/results.json \
  --results silverold=studies/silver_market/artifacts/results.json \
  --no-provenance
```

This checks every results key and every bare number in the prose and passes.

`--no-provenance` is needed for a Stage 1 and is not a loophole to keep: without it the gate reports, correctly,
that the previews are provisional, were not written from a clean tree and carry no data hash, and that the old
study artifacts came from a dirty tree. That is the true state of a pilot. The Stage 2 manuscript must read sealed
run results and pass the gate **without** this flag.

## Known gaps to close before submission

- Regenerate the three previews: each was written from an earlier revision of its draft plan (the manuscript says so),
  before the side rule and the year test of ADR-008 A3.
- The `r_measures.R2.measure` text in the three domain plans is cut at a comma by the YAML parser (flow mapping);
  quote the string in the plans.
- Owner sign-offs H16, H18, H20, H21, H22, H4 (and H19, H11, L2, Support) are pending; see the manuscript's last section.
- Check every `TODO(owner)` in `references.bib` and in the manuscript's comments.
