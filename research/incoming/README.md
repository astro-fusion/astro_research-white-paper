# research/incoming: external research evidence, kept in full

Everything an external research agent (Gemini in Antigravity) produced for this project is kept here **unedited**, so that any claim in a paper can be traced back to it, cross-checked and re-verified.

| Folder | Topic | Prompt |
|---|---|---|
| `gold_prices/` | gold price sources, episodes, macro drivers, literature, 2024–2026 news | GEMINI_PROMPTS.md Prompt 1 |
| `gold/` | gold astrology: classical verses, practitioner methods, ex-ante forecasts, disputes | Prompt 2 |
| `earthquake/` | catalogues, seismology literature, ch. 32 and practitioner rules, ex-ante predictions | Prompt 3 |
| `flood/` | monsoon and flood data, literature, rain rules, ex-ante monsoon forecasts, feasibility | Prompt 4 |

## Rounds
- **Round 1 (raw):** the files at the top of each topic folder, written 2026-11-22. The audit found many invented URLs, quotes and DOIs. **They are kept as the record, not as evidence.**
- **Round 2 (`verified/`):** Gemini's own verification pass. It adds `verified`, `exact_url`, `archive_url`, `verbatim_quote`, `corrected_from` and similar columns. It is better, but still has errors.
- **Independent audit of both rounds:** [docs/research/handover/INCOMING_AUDIT_2026-11-22.md](../../docs/research/handover/INCOMING_AUDIT_2026-11-22.md). It covers Crossref DOI checks, URL checks, and quote matching against archive.org snapshots.

## Rules
1. Nothing here feeds a study, a rule file or a paper directly. A row is promoted (by the WP-10 ingest validator, ADR-004) only when its source has been opened and the quote, number or verse found there. The row then records who verified it and when.
2. A forecast counts as ex-ante only with independent proof of its date: an archive.org snapshot before the event, a dated print issue, or a dated social post.
3. Never edit a file here. Corrections go in a new round folder, so the history stays visible.
4. `MANIFEST.csv` lists every file with its SHA-256 hash. Regenerate it whenever a round is added.

## Licences
These files are metadata, short quotations and citations. They contain no raw price, rainfall or catalogue data. Raw data are fetched by scripts and recorded by hash in `data/snapshots/`.

## Validator (ADR-004 WP-10)
- `python -m tools.ingest misplaced` lists files an outside agent left at the repo root or in `studies/*/rules/`; `python -m tools.ingest relocate <path> --topic <topic>` moves one here.
- `python -m tools.ingest validate research/incoming/<topic> [--no-urls]` checks each file against the contracts in PAPER_ROADMAP section 4.3, applies the machine-checkable rejections of section 4.4, runs `astro-rules validate` on rule YAML and writes `VERIFICATION.json`. A column mismatch is reported with a suggested mapping and never renamed.
- A person records `verdict` (accepted, rejected, unverified), `checked_by` and `checked_on` per row in `VERIFICATION.json`. `--promote` copies only rows with `verdict: accepted`, a `checked_by` name and no machine rejection into `data/registry/<topic>/`. Promoted rows keep the `row_id`, `url_status`, `archive_url`, `checked_by`, `checked_on`, `verdict` and `reject_reason` columns.
- URL checks send the generic client name `link-checker/1.0` and nothing about the project.
- Everything in `research/incoming/` stays committed for full transparency (owner decision, 2026-11-22). The validator controls promotion, not visibility.
