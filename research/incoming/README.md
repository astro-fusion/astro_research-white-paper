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
