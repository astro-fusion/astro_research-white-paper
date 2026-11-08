# Rule migration, November 2026 (one-shot)

These scripts produced the first contents of `rules/` in commit `4f55153`
("migrate the combination catalog, src yogas and 67 mundane drafts"). They
are kept as a record of how each rule file was derived. They are one-shot:
do not run them again. The rule files are now edited by hand and through
the `astro-rules` command, and a re-run would overwrite those edits and
recompute the reference cases.

| Script | Produced |
| --- | --- |
| `migrate_catalog.py` | `rules/financial/*.yaml` (4) and `rules/seismic/*.yaml` (8) from the old `libs/vedic_astrology_core/combinations/catalog/*_yogas.yaml`; `rules/general/*.yaml` (Budha-Aditya and two Gaja Kesari variants) from the old `src` `detect_yogas` |
| `migrate_mundane.py` | the 67 files in `rules/mundane/experimental/` from the AstroFusion mundane draft registry (open export, 2026-11-08; not in this repository, read from `$MUNDANE_DRAFTS`) |
| `common.py` | shared helpers: YAML writer, schema validation, and the computed `reference_cases` (engine 2026-11-08, Lahiri, mean node) |

Reference cases were computed by this repository's engine and were not
checked against JHora at the time of migration; each case notes that.
