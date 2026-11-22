# ADR-004: Paper production and principle validation

- Status: proposed
- Date: 2026-11-22
- Deciders: repository owner (single developer); architect (design only)
- Builds on: [ADR-001](ADR-001-flagship-research-repo.md), [ADR-002](ADR-002-research-bridge.md), [ADR-003](ADR-003-rule-workbench.md)
- Inputs: [RESEARCH_REVIEW_2026-11-22.md](../../RESEARCH_REVIEW_2026-11-22.md) (flaw codes C1 to C6, M1 to M13, roadmap items 1 to 10), [GEMINI_PROMPTS.md](../research/handover/GEMINI_PROMPTS.md)
- Owner-facing explanation: [PAPER_ROADMAP.md](../research/PAPER_ROADMAP.md)

## Context

The review found that the rebuilt gold, silver and earthquake pipelines are sound in outline but that no paper is ready for a journal: the "pre-registration" is not verifiable (C2), the price data are poor (C4), slow indicators have one or two independent episodes (M1, M2), there are no baselines (M4, M5), power is overstated (M6), the rule workbench's guards can be bypassed (C6), and CI does not test the science (M11, M13).

Two fixes are in progress elsewhere and are out of scope here:

- **WP-A**: exact enumeration in the circular-shift test and the attainable minimum p (C1).
- **WP-B**: withdrawn and stale papers out of the `_quarto.yml` render list and navbar; CI no longer runs `scripts/generate_artifacts.py` (site part of C3, C5).

An external agent (Gemini) is collecting data pointers, rule YAML and dated forecasts into `research/incoming/<topic>/`. Its output is untrusted until checked.

This ADR decides what is published, how a classical claim becomes a tested rule, how outside data enters the repository, and how a paper is built. It then splits the work into packages small enough for one agent session each.

## Decision

### D-1. Three papers and an optional tool note, not one omnibus

| Id | Paper | Kind | First venue |
|---|---|---|---|
| P1 | Gold and silver merged (gold primary, silver as second asset) | Retrospective test of a fixed plan, with a prospective segment | Royal Society Open Science or PLOS ONE |
| P2 | Himalayan earthquakes | Retrospective test of a fixed plan | PLOS ONE, Royal Society Open Science, or Geoscience Letters |
| P3 | Monsoon and floods | Registered Report, Stage 1 through PCI Registered Reports | A PCI RR-friendly journal or PLOS ONE |
| P4 | Rule workbench (optional) | Software note | Journal of Open Source Software |

Numerology, the remedy notes and the mundane study are relabelled as notes and are not papers. The stated headline of the programme is "a rigorous null plus an open testing tool".

### D-2. Honest words for the plans

- Existing `hypothesis.yaml` files are described everywhere as "a fixed analysis plan committed with the first run". The words "pre-registered" and "pre-registration" are reserved for a plan deposited on OSF Registries before the data it governs exist or are fetched.
- The historical confirm period is called "pseudo-out-of-sample". The true confirm set is data dated after the OSF deposit.
- Each amended plan (version 2) is deposited on OSF **before** the single clean re-run that feeds a paper. Deviations from version 1 are listed in `amendments` and printed in the paper.
- A run refuses to write non-provisional results from a dirty git tree, and a confirm run is a separate, logged invocation that can happen once per plan lineage.

### D-3. OSF for plans, Zenodo for releases

OSF Registries holds the time-stamped plans (secondary-data template for P1 and P2). Zenodo, through its GitHub link, mints a DOI per tagged release and stores code, `results.json`, the snapshot index and every snapshot whose licence allows it. Each cites the other.

### D-4. Validation levels L0 to L6, computed from evidence

| Level | Name | Required evidence in the rule file or fixtures |
|---|---|---|
| L0 | Recorded | Loads against the schema |
| L1 | Sourced | `source` with text, edition, translator, chapter, verse or page, and a quotation; or URL, publication date and archive link; a maintainer check recorded |
| L2 | Operationalised | Structured `conditions`; every number in `params` with value, min, max, step, unit and `range_source`; `expected_effect.direction`; zodiac, ayanamsa and node model stated |
| L3 | Computationally verified | All reference cases pass; at least three agree with a manual Jagannatha Hora reading to 1 arcminute; the instants involved agree with JPL Horizons to 5 arcseconds |
| L4 | Faithful ("validated principle") | A review entry with verdict faithful, by a named reviewer who is not the rule's author and who attests to having seen no test result |
| L5 | Explored | A logged fit on explore-period data |
| L6 | Confirmed or refuted | One sealed confirm for the rule lineage, with catalogue-wide correction |

The level is computed by code from what the file and fixtures contain; it is never a hand-written field. "Validated principle" means L4 and means faithful encoding only. A rule enters a confirmatory family at L3 or above. Editing a rule after a confirm starts a new lineage that counts toward the family size.

Ex-ante forecasts are scored with proper scoring rules against explicit base rates (Brier skill score for yes/no outcomes, ranked probability skill score for ordered categories, Molchan diagram for earthquake alarms), after blind coding, with uncertainty computed by resampling astrologers. Ex-ante status requires an archive capture dated before the target window. A prospective forecast ledger opens when P1 is submitted.

### D-5. Outside data: pointers in, bytes fetched by us

- `research/incoming/` is a quarantine and is not committed (only its README).
- A validator checks each file against a contract, checks every URL, and records a person's spot checks. Accepted rows are promoted to the committed `data/registry/<topic>/`.
- No value from an incoming file is used as a study input. Fetch scripts download from the primary provider into `data/snapshots/`; each snapshot is listed in the committed `data/snapshot_index.json` with SHA-256, row count, date range, source and licence decision.
- Commit rule: public-domain and CC BY data may be committed; CC BY-SA in its own folder with its licence; anything with restricted or unclear terms is published as hash plus fetch script. Daily returns derived from a licensed price series count as the series.
- Rule YAML from the agent enters `rules/` only through `astro-rules validate`, at L0 or L1, with `status: needs_verification` or `needs_predicates`.

### D-6. Inference for slow indicators

- The episode (a maximal run of the indicator, with runs closer than a plan-fixed gap merged) is the unit of evidence.
- An indicator is testable in a period only if it has at least 8 episodes **and** its attainable minimum p (from WP-A) is below the rank-1 Benjamini-Yekutieli threshold of its family. Otherwise it is reported as "untestable with this sample", outside the family. Testability is decided from the calendar alone, before outcomes are read, and fixed in the plan.
- Volatility outcomes are standardised with past-only estimates.
- Each plan states a smallest effect size of interest. Each test is reported as "effect found", "effect excluded" (TOST) or "inconclusive". The word "null" alone is not used for an inconclusive test.
- An astrological term is reported as such only if it adds to calendar, festival, lunar and macro baselines and beats placebo skies.

### D-7. Papers are built, not typed

- Every number in a paper is read from `results.json` by dotted key through one accessor that raises on a missing key.
- A gate fails the build when a paper asks for a missing key, contains a bare number outside its allow-list, or when `results.json` is provisional, was written from a dirty tree, or disagrees with the current plan hash or snapshot index.
- Journal formats come from Quarto journal extensions set in each paper's own front matter. `_quarto.yml` is not used for journal formatting.
- The environment is frozen: a hashed lock file and a Docker image pinning Python, Quarto, TeX and ephemeris files. CI renders papers from committed results; it does not re-run studies.

### D-8. Flood study firewall

Until the Stage 1 plan is accepted, the flood pipeline runs on simulated data only. The code refuses real outcome data unless the plan file carries the acceptance record. Fetching and checksumming real files is allowed; computing any outcome-versus-indicator statistic is not.

### D-9. Build order: modules first, wiring last

New statistics land as new modules with their own tests, in parallel. One wiring package per study then connects them. This keeps parallel agents out of each other's files and puts the risky integration (family size, sealing, random streams) in one reviewed place.

## Consequences

Good:

- Every claim a paper makes can be traced: verse to rule to level to test to key to sentence.
- A stale or hand-edited number cannot reach a PDF without the gate failing.
- The flood study can be a real Registered Report.
- An invented URL, verse or price from an outside agent cannot reach a result.

Costs and risks:

- P1 cannot be reproduced exactly without the reader's own access to licensed gold prices. Mitigation: hashes, fetch scripts, and an openly reproducible monthly check on World Bank data.
- The family will shrink. Several headline indicators (Jupiter in a sign) become "untestable". This is correct, but the paper will look smaller.
- Several steps need people: an OSF deposit, an astrologer reviewer, someone with Jagannatha Hora, licence reading. L3 and L4 stall without them, and P3 cannot be submitted without L4.
- About thirty packages is a lot of coordination for one developer. The wave plan below limits what must be held in mind at once.
- The repository is MIT and the ephemeris library is AGPL. This is unresolved (Gemini prompt 5, question 6) and blocks P4, not P1 to P3.
- Venue limits and fees were written from memory and must be checked.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| One combined paper for gold, earthquakes and floods | No referee covers all three fields; it repeats the withdrawn omnibus; one weak part sinks the rest |
| A Registered Report for gold or earthquakes | The data have already been analysed here; claiming otherwise would repeat C2 |
| Submitting P1 to a finance letters journal first | A 2,500-word limit cannot hold the deviations table, baselines and power; high desk-rejection risk for the topic |
| Zenodo only, or OSF only | Zenodo has no registration templates or review-ready prereg format; OSF has no release-per-tag DOI flow |
| Using the agent's CSV values as study data | Unverifiable provenance and licence; fabrication risk |
| Committing licensed prices or derived daily returns "for reproducibility" | Breaches provider terms; a hash gives verification without redistribution |
| A hand-set `validation.status` field | It is how "validated" came to mean nothing; computed levels cannot drift from the evidence |
| PyJHora alone as the Jagannatha Hora check | It is a port, and it shares a dependency (Swiss Ephemeris) with the engine under test; a manual reading of the real program is independent |
| Dropping slow indicators silently | Hides the limit of the data; "untestable" is a finding the reader needs |
| Keeping bar-level tests with a larger block length | Does not fix one-episode indicators; the calibration suite will show it |
| Adding intraday, regime-switching and machine-learning models to P1 | Each is a paper; they delay a clean result and enlarge the family |
| Hand-written LaTeX per journal | Breaks the single source and the key gate |
| Re-running studies in CI | Licensed data cannot be in CI; refetching gives different bytes |
| Editing `stats/study.py` in every statistics package | Guaranteed merge conflicts between parallel agents; see D-9 |

---

## Work-package plan

### Ground rules for every package

- **Tests:** run only the tests named in the package (the tests of the changed files and tests that read them). The full suite runs once in CI.
- **Shared files have one owner.** Only WP-18 edits `pyproject.toml`, `Makefile` and `.github/workflows/`. Only WP-14 and WP-27 add exports to `libs/vedic_astrology_core/stats/__init__.py` and `markets/__init__.py`; module packages import by full module path. Only WP-10 edits `.gitignore`. Only WP-30, WP-19 and WP-28 (in that order) edit `_quarto.yml`, and only after WP-B.
- A package that needs a new dependency names it in its report; WP-18 adds it.
- No package commits a file under `data/snapshots/` or `research/incoming/`.
- Model routing: "implementer (Sonnet)" unless a concrete subtle risk is named, then "senior-implementer (Opus)". Design tasks stay with the architect. Integration, gates and commits stay with the main session under the owner's git rules.
- Paths below are relative to the repo root; `core/` stands for `libs/vedic_astrology_core/`.

### Design tasks (architect, no code)

| Id | Output | Needed by |
|---|---|---|
| D1 | Gold and silver plan v2: series, sampling instant, testable family, episode merge gap, SESOI values, baseline set, placebo set, forecast-scoring protocol, deviations from v1 | WP-15 |
| D2 | Earthquake plan v2, and a separate registration for the Varuna-mandala test on a global catalogue | WP-27 |
| D3 | Flood Stage 1 protocol, after the flood feasibility file is verified | WP-29 |

### Owner actions

| Id | Action | Needed by |
|---|---|---|
| H1 | Create the OSF project; deposit each v2 plan | WP-15, WP-27 |
| H2 | Recruit an astrologer reviewer | L4; M6 |
| H3 | Manual Jagannatha Hora readings | L3; WP-21 fixtures |
| H4 | Read and record licence terms; choose journal | WP-11, WP-12 |
| H5 | Confirm SESOI values and family in D1 | WP-15 |
| H6 | Approve deletions listed in WP-01 | WP-01 |

### Packages

#### WP-01 Honesty leftovers (review item 1, remainder)
- **Goal:** remove what WP-B does not: old PDFs and release files, false sentences.
- **Files:** `README.md` (the "before any data are analysed" and "one command reproduces" claims; the gold verdict wording), `CORRECTIONS.md` (add the release manuscript and the C1 correction once WP-A lands), `papers/pdf/*` and `application/web/static/releases/*` (delete, after H6), the stale `research/` tree except `research/incoming/` (delete, after H6).
- **Acceptance:** `git grep -n "pre-registered before"` and `git grep -n "before any data"` return nothing outside CORRECTIONS and the review; no PDF under `papers/pdf/`; CORRECTIONS lists the release manuscript.
- **Tests:** `tests/test_site_pages.py`, `tests/test_rules_docs.py`.
- **Depends on:** WP-A, WP-B, H6. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-02 Calibration test suite (review item 5)
- **Goal:** prove by simulation that each test holds its stated false-alarm rate.
- **Files (new):** `tests/simulators.py` (GARCH(1,1) with heavy tails; two-state volatility regimes; drift; real indicator calendars from the ephemeris), `tests/test_stats_calibration.py`.
- **Acceptance:** with no true effect, at nominal 0.05: the exact shift test on standardised outcomes with indicators of 8 or more episodes rejects in at most 0.05 plus three binomial standard errors; bootstrap 95 percent intervals cover in at least 92 percent of runs; BY keeps the false discovery rate at or below 0.05 for a family of 42; the raw-outcome shift test with a one-episode indicator under regime shifts is pinned as a strict expected failure with the reason (M1); SPA size under drift is a strict expected failure until WP-09. A fast subset (seeded, under five minutes) and a slow marker for the full run.
- **Tests:** `tests/test_stats_calibration.py`, `tests/test_stats_permutation.py`, `tests/test_stats_nulls.py`.
- **Depends on:** WP-A. **Parallel:** wave 1.
- **Implementer:** senior-implementer (Opus). Risk: a simulator that is too kind (no long memory, no regimes) certifies a broken test.

#### WP-03 Run seal (review item 4, code part)
- **Goal:** results cannot come from a dirty tree; confirm happens once.
- **Files:** `core/stats/seal.py` (new), `core/stats/manifest.py`, `tests/test_stats_seal.py` (new), `tests/test_stats_manifest_plots.py`.
- **Acceptance:** `require_clean_tree()` raises unless the run is flagged provisional, and a provisional run writes `provisional: true`; an append-only confirm ledger (`studies/<study>/confirm_ledger.jsonl`: plan hash, data hash, commit, UTC time, period); a second confirm for the same plan lineage raises; the confirm window end comes from the plan, never from "now".
- **Tests:** the two test files above (temporary git repositories).
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** senior-implementer (Opus). Risk: holdout leakage through a bypass (version bump, deleted ledger, environment flag).

#### WP-04 Episode-level inference (review item 6)
- **Goal:** episodes as the unit; a testability rule; cluster-aware uncertainty.
- **Files (new):** `core/stats/episodes.py`, `tests/test_stats_episodes.py`.
- **Acceptance:** `episodes(indicator, merge_gap)` returns runs with merge; `testable(...)` implements D-6 from the calendar alone; an exact sign-flip test on per-episode differences (episode mean minus the mean of its neighbouring inactive windows), enumerated when there are 20 or fewer episodes; a wild cluster bootstrap interval by episode; the Jupiter-in-Capricorn explore calendar from the review yields one episode and "untestable".
- **Tests:** `tests/test_stats_episodes.py`.
- **Depends on:** WP-A (attainable minimum p). **Parallel:** wave 1.
- **Implementer:** senior-implementer (Opus). Risk: cluster inference with few clusters is easy to get anti-conservative.

#### WP-05 Past-only volatility standardisation and GARCH-X
- **Goal:** remove the full-sample fit; add the variance-equation test.
- **Files:** `core/stats/volatility.py` (new), `core/stats/granger.py`, `tests/test_stats_volatility.py` (new), `tests/test_stats_granger.py`.
- **Acceptance:** standardised outcome at bar t uses parameters fitted on data to t-1 (refit on a fixed schedule); changing data after t does not change values up to t (tested); a missing `arch` package raises, with no silent fallback; GARCH-X returns a likelihood-ratio statistic whose p-value comes from the shift null.
- **Tests:** the two test files above.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** senior-implementer (Opus). Risk: look-ahead in the standardisation.

#### WP-06 Calendar, festival and macro baselines (review item 7)
- **Goal:** the comparison terms an astrological effect must beat.
- **Files (new):** `core/markets/baselines.py`, `core/markets/festivals.py`, `tests/test_markets_baselines.py`, `tests/test_markets_festivals.py`, `tests/fixtures/markets/festival_dates.csv`.
- **Acceptance:** month, weekday, turn-of-month and holiday terms; Akshaya Tritiya, Dhanteras, Diwali, Pitru Paksha, Adhik Maas and Pushya days computed by the repo's panchanga code and matching at least ten published dates each (fixture cites its source); lunar-phase terms; a macro join that uses only values known at t-1; `incremental_test()` removes the baselines from outcome and indicator, then applies the shift test.
- **Tests:** the two new test files.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-07 Placebo skies and ayanamsa sensitivity (review item 7)
- **Files (new):** `core/markets/placebo.py`, `tests/test_markets_placebo.py`.
- **Goal and acceptance:** build indicator calendars for time-shifted skies (offsets of at least 400 days), the tropical zodiac and scrambled sign labels; return the rank of the real sky's largest statistic among placebos; rebuild indicators under Lahiri, Raman, KP and true Chitrapaksha and report how many bars change.
- **Tests:** `tests/test_markets_placebo.py`, `tests/test_ephemeris_ayanamsa.py`.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-08 Power, SESOI and TOST, project multiplicity (review item 8)
- **Files:** `core/stats/power.py`, `core/stats/equivalence.py`, `scripts/project_multiplicity.py` (new), `tests/test_stats_power.py`, `tests/test_stats_equivalence.py`, `tests/test_project_multiplicity.py` (new).
- **Acceptance:** power and minimum detectable effect accept the family's rank-1 BY threshold as alpha and episodes as n; an over-dispersed (negative binomial) option for event counts; TOST from an episode-clustered interval, returning one of found, excluded, inconclusive; the script reads every `studies/*/artifacts/results.json` and writes `studies/project_multiplicity.json` with the number of hypotheses tested and expected false discoveries.
- **Tests:** the three test files above.
- **Depends on:** WP-04. **Parallel:** wave 2.
- **Implementer:** senior-implementer (Opus). Risk: a wrong standard error in TOST produces a false "effect excluded", which is the paper's headline.

#### WP-09 SPA benchmark fix (M3)
- **Files:** `core/stats/walk_forward.py`, `tests/test_stats_walk_forward.py`, `tests/test_stats_calibration.py` (remove the expected-failure mark only).
- **Acceptance:** benchmark is buy-and-hold at equal exposure (or demeaned returns); a per-switch cost parameter; SPA size under drift at or below nominal in the calibration suite.
- **Tests:** the first two files, and the SPA case of the calibration file.
- **Depends on:** WP-02. **Parallel:** wave 2.
- **Implementer:** implementer (Sonnet).

#### WP-10 Gemini ingest validator
- **Files (new):** `tools/ingest/__init__.py`, `tools/ingest/contracts.py`, `tools/ingest/validate.py`, `tools/ingest/urlcheck.py`, `research/incoming/README.md`, `tests/test_ingest_validator.py`, `tests/fixtures/ingest/*`; edit `.gitignore` (ignore `research/incoming/*` except the README).
- **Acceptance:** a file found outside `research/incoming/` (as happened on 2026-11-22: three flood CSV files at the repo root and rule files in `studies/monsoon/rules/`) is reported, and a `relocate` command moves it into quarantine; a column set that differs from the contract is reported with a suggested mapping and is never guessed silently; `python -m tools.ingest validate research/incoming/<topic>` checks each file against the contracts in PAPER_ROADMAP section 4.3, applies the rejection rules of section 4.4 that a machine can apply (missing reference, unparsable dates, end before start, duplicate ids, ex-ante date order, files that look like value dumps), runs `astro-rules validate` on rule YAML, and writes `VERIFICATION.json`; `--promote` copies only rows with `verdict: accepted` and a `checked_by` name into `data/registry/<topic>/`; URL checks use a generic client name and send nothing about the project or owner; tests use an injected opener and no network.
- **Tests:** `tests/test_ingest_validator.py`.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-11 Snapshot index, licence register, open-data fetch scripts (review item 10, data part)
- **Files:** `core/datasets/snapshots.py` (new), `scripts/fetch/fred.py`, `scripts/fetch/worldbank_pinksheet.py`, `scripts/fetch/cftc_cot.py`, `scripts/fetch/gfz_kp.py` (new), `data/snapshot_index.json` (new), `data/registry/licences.yaml` (new), `scripts/check_data.py`, `data/README.md`, `docs/DATA_PROVENANCE.md`, `tests/test_snapshots_index.py` (new).
- **Acceptance:** each fetch script writes a snapshot and manifest and adds an index entry (file, SHA-256, rows, date range, source URL, licence, committed yes or no); `check_data.py` fails on a hash mismatch or an unlisted snapshot; the two docs describe only files that exist and name the true gold source.
- **Tests:** `tests/test_snapshots_index.py`, `tests/test_markets_fetch.py`.
- **Depends on:** WP-10; H4 for licence entries. **Parallel:** wave 2.
- **Implementer:** implementer (Sonnet).

#### WP-12 Price data replacement and quality gate (review item 3)
- **Files:** `core/markets/fetch.py`, `core/markets/quality.py` (new), `core/markets/align.py`, `tests/test_markets_fetch.py`, `tests/test_markets_quality.py` (new), `tests/test_markets_align.py`.
- **Acceptance:** an adapter for the verified LBMA PM route from 1968 and one for a second, independent series; zero-volume settlement days are kept; the run fails if more than 1 percent of business days are missing or if the two series disagree beyond a stated tolerance on overlapping days; returns spanning more than four calendar days are flagged; the sky is sampled at the series' own fixing time (15:00 London for the PM price); a back-adjusted futures series only if per-contract data are obtained, with a test that the adjustment uses no future information.
- **Tests:** the three test files above.
- **Depends on:** WP-10 (verified answers to prompt 5, questions 1 and 2), WP-11, H4. **Parallel:** wave 3.
- **Implementer:** senior-implementer (Opus). Risk: a wrong sampling instant or time zone shifts every Moon-based indicator; roll adjustment can leak future prices.

#### WP-13 One rule engine (M9; review item 10)
- **Files:** `core/combinations/` (remove after porting), `core/markets/features.py`, `tests/test_markets_features.py`, `tests/test_combinations_end_to_end.py`.
- **Acceptance:** the two gold "rule" indicators are evaluated by `core/rules`; the blanket `except Exception` is gone and a rule failure stops the run; graha drishti is by sign; a test proves the family cannot shrink silently; `studies/combinations` still imports (it uses its own grammar; confirm before deleting).
- **Tests:** the two test files above, `tests/test_atlas_evaluate.py`.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** senior-implementer (Opus). Risk: the port changes indicator values (degree-based versus sign-based aspects) and with them the registered family.

#### WP-14 Gold and silver study v2 wiring
- **Files:** `core/markets/study.py`, `core/markets/report.py`, `core/stats/__init__.py`, `core/markets/__init__.py`, `tests/test_markets_study.py`, `tests/test_markets_report.py`.
- **Acceptance:** the study uses WP-03 to WP-09, WP-12 and WP-13; explore and confirm are separate invocations; each test draws from its own named random stream, so adding an indicator changes no other p-value; untestable indicators are listed apart and excluded from the family; `results.json` gains the keys named in PAPER_ROADMAP section 2.1 and validates against a new `studies/gold_market/results.schema.json`; no prose in `report.py` claims the shift null handles non-stationary volatility.
- **Tests:** the two test files above, `tests/test_gold_study.py`, `tests/test_silver_study.py`.
- **Depends on:** WP-03, 04, 05, 06, 07, 08, 09, 12, 13. **Parallel:** wave 4 (with WP-27).
- **Implementer:** senior-implementer (Opus). Risk: family size, sealing and random streams all meet here.

#### WP-15 Apply plan v2 and re-run gold and silver
- **Files:** `studies/gold_market/hypothesis.yaml`, `studies/silver_market/hypothesis.yaml`, both `artifacts/` folders (regenerated), both study `README.md` files, `CORRECTIONS.md`.
- **Acceptance:** the plans equal D1 and carry the OSF DOI and filled `amendments`; one explore run and one confirm run, each from a clean tree, each in the ledger; `git.dirty` is false and `provisional` is false; READMEs state the verdict produced, with power figures at the corrected threshold.
- **Tests:** `tests/test_gold_study.py`, `tests/test_silver_study.py`, `tests/test_site_data.py`.
- **Depends on:** WP-14, D1, H1, H5. **Parallel:** wave 5.
- **Implementer:** implementer (Sonnet).

#### WP-16 Paper kit and results-key gate
- **Files (new):** `core/paperkit/__init__.py`, `core/paperkit/results.py`, `tools/check_paper_keys.py`, `tests/test_paperkit.py`, `tests/test_check_paper_keys.py`; edit `templates/imrad_paper.qmd`.
- **Acceptance:** `Results.load(path)` with `.get("a.b.c")` that raises on a missing key and formats numbers consistently; the checker implements the four failures of D-7, with a per-paper `numbers_allowlist.txt`; the template shows the pattern and the IMRaD headings; the checker exits non-zero on a fixture paper citing a missing key.
- **Tests:** the two new test files.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-17 Journal templates and PDF script
- **Files:** `scripts/generate_pdfs.sh`, `_extensions/` (Quarto journal extensions for PLOS and Elsevier), `templates/journal/plos.yml`, `templates/journal/elsevier.yml`, `templates/journal/plain.yml` (new), `papers/targets.yaml` (new, the list of target papers), `tests/test_pdf_script.py` (new).
- **Acceptance:** the script builds only the papers in `papers/targets.yaml`, runs the key gate first, never calls `generate_artifacts.py` and names no withdrawn paper; each format renders the template to PDF locally.
- **Tests:** `tests/test_pdf_script.py`, `tests/test_scientific_report_smoke.py`.
- **Depends on:** WP-B, WP-16. **Parallel:** wave 2.
- **Implementer:** implementer (Sonnet).

#### WP-18 Frozen environment, CI paper gate, release metadata
- **Files:** `ops/requirements.lock.txt`, `ops/Dockerfile.paper` (new), `Makefile`, `pyproject.toml`, `.github/workflows/paper-gate.yml` (new), `CITATION.cff` (new), `.zenodo.json` (new), `docs/COMPUTATIONAL_ENVIRONMENT.md`, `tests/test_release_metadata.py` (new).
- **Acceptance:** lock file with hashes; the image pins Python, Quarto, TeX and ephemeris file hashes, and `make paper STUDY=<name>` runs inside it; the workflow runs the fast calibration subset, the key gate, the snapshot index check and the render of each target paper, with no step that swallows a failure; citation and Zenodo metadata parse and agree on the version.
- **Tests:** `tests/test_release_metadata.py`; a local image build; a workflow lint.
- **Depends on:** WP-02, WP-16, WP-17 (and WP-B for the old workflow). **Parallel:** wave 3.
- **Implementer:** implementer (Sonnet).

#### WP-19 Merged gold and silver manuscript
- **Files:** `studies/precious_metals/paper/manuscript.qmd`, `references.bib`, `numbers_allowlist.txt` (new); the two old `manuscript.qmd` files become short pointer pages; `_quarto.yml` (navbar entry); `papers/targets.yaml`; `scripts/generate_pdfs.sh` is not edited.
- **Acceptance:** follows the outline in PAPER_ROADMAP section 2.1; reads both `results.json` files through the paper kit; passes the key gate; includes the deviations table, the indicator table with validation levels, the power and equivalence section and the project-wide test count; uses "fixed analysis plan" wording; builds to the chosen journal format.
- **Tests:** `tools/check_paper_keys.py` on the paper, `tests/test_site_pages.py`, `tests/test_sources_bib.py`.
- **Depends on:** WP-15, 16, 17, 24, 30. **Parallel:** wave 6 (before WP-28, which shares `_quarto.yml` and `papers/targets.yaml`).
- **Implementer:** implementer (Sonnet).

#### WP-20 Rule schema evidence fields and validation levels
- **Files:** `core/rules/schema.py`, `core/rules/levels.py` (new), `core/rules/cli.py`, `rules/schema.json` (regenerated), `tests/test_rules_schema_v2.py`, `tests/test_rules_levels.py` (new), `tests/test_rules_cli.py`.
- **Acceptance:** optional fields added (`source.edition`, `translator`, `quote`, `archive_url`, `published`; `params.<name>.range_source`); every existing rule file still loads unchanged; `level(rule)` computes L0 to L6 per D-4 and explains what is missing for the next level; `astro-rules level <file>` and `astro-rules validate --min-level N`.
- **Tests:** the three test files above, `tests/test_rules_catalog.py`.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-21 Jagannatha Hora and Horizons cross-check fixtures
- **Files (new):** `tests/fixtures/jhora/README.md` (the manual reading protocol and the JSON format: program version, settings, date, time, place, values, reader's name), `tests/fixtures/jhora/*.json`, `tests/jhora.py`, `tests/test_jhora_crosscheck.py`, `tests/fixtures/horizons/events/*.json`, `tests/test_horizons_events.py`; edit `tests/horizons.py`.
- **Acceptance:** a harness that compares engine output with fixture readings at 1 arcminute; fixtures carry `source: jhora_manual` or `source: pyjhora` and only manual ones count toward L3; Horizons event fixtures (sign ingress, station, exact conjunction, new and full Moon) agree with the engine to 5 arcseconds at the stated instants; the Horizons fetch helper sends a generic client name only.
- **Tests:** the two new test files, `tests/test_horizons_crosscheck.py`.
- **Depends on:** none to build; H3 for the manual readings. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-22 Astrologer review flow
- **Files:** `core/rules/packet.py` (new), `core/rules/cli.py`, `core/rules/workbench.py` (`review_entry` only), `.github/ISSUE_TEMPLATE/rule-review.yml` (new), `CONTRIBUTING_ASTROLOGERS.md`, `tests/test_rules_packet.py` (new), `tests/test_rules_cli.py`.
- **Acceptance:** `astro-rules packet <file>` writes a Markdown review packet with the claim, the source quotation, the plain-language explanation of each reference case and the three questions of PAPER_ROADMAP section 3.2, and contains no test result; `astro-rules review` records verdict (faithful, faithful with changes, not faithful), reviewer name, that the reviewer is not the author, and a blind attestation; a review by the rule's author does not count toward L4.
- **Tests:** the two test files above, `tests/test_rules_levels.py`.
- **Depends on:** WP-20. **Parallel:** wave 2.
- **Implementer:** implementer (Sonnet).

#### WP-23 Workbench guards (C6; review item 10)
- **Files:** `core/rules/studyadapter.py`, `core/rules/workbench.py`, `core/rules/cli.py` (confirm command), `tests/test_rules_studyadapter.py`, `tests/test_rules_workbench.py`.
- **Acceptance:** `up`, `down` and `either` map to one-sided or two-sided tests on signed outcomes, and a wrong-direction effect cannot pass; the family size is the number of active rule lineages in the catalogue for that study, never 1; one confirm per lineage through the WP-03 ledger, and a version bump does not reset it; the market confirm window ends at the plan's date; a rule whose source is dated inside the confirm window is refused for confirm.
- **Tests:** the two test files above.
- **Depends on:** WP-03, WP-22 (same files). **Parallel:** wave 3.
- **Implementer:** senior-implementer (Opus). Risk: multiplicity and holdout leakage.

#### WP-24 Forecast scoring module
- **Files (new):** `core/stats/forecast_scoring.py`, `tests/test_stats_forecast_scoring.py`.
- **Acceptance:** Brier score and skill score; ranked probability score and skill score; base rates per PAPER_ROADMAP section 3.4, each computed only from data dated before the forecast's publication; resampling by astrologer; a count of forecasts that could not be coded; a report of the smallest detectable skill.
- **Tests:** `tests/test_stats_forecast_scoring.py`, `tests/test_stats_molchan.py`.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** implementer (Sonnet).

#### WP-25 Earthquake catalogue upgrade (review item 9)
- **Files:** `studies/earthquake/scripts/fetch_catalogue.py`, `tests/test_earthquake_catalogue.py`.
- **Acceptance:** ISC-GEM and Global CMT adapters with snapshots and index entries; the offline path reads Nepal local time correctly (the 5 hours 45 minutes bug has a regression test); the polygon excludes Tibetan rift events as the plan says; a frozen ComCat snapshot is kept as a check.
- **Tests:** `tests/test_earthquake_catalogue.py`.
- **Depends on:** WP-10, WP-11. **Parallel:** wave 3.
- **Implementer:** implementer (Sonnet).

#### WP-26 ETAS declustering (review item 9)
- **Files:** `studies/earthquake/scripts/decluster.py`, `tests/test_earthquake_decluster.py`.
- **Acceptance:** a space-time ETAS fit with stochastic declustering returning an ensemble of declustered catalogues; parameters recovered within tolerance on a simulated ETAS catalogue; the 2015-05-12 Mw 7.3 event has background probability below one half; the two existing methods are unchanged.
- **Tests:** `tests/test_earthquake_decluster.py`.
- **Depends on:** none. **Parallel:** wave 1.
- **Implementer:** senior-implementer (Opus). Risk: ETAS likelihood fits are unstable on a few hundred events and can converge to nonsense without warning.

#### WP-27 Earthquake v2 wiring and re-run (review item 9)
- **Files:** `studies/earthquake/scripts/pipeline.py`, `robustness.py`, `indicators.py`, `studies/earthquake/hypothesis.yaml`, `studies/earthquake/artifacts/` (regenerated), `studies/earthquake/README.md`, `tests/test_earthquake_pipeline.py`, `tests/test_controls_tidal.py`, `tests/test_controls_earthquake.py`.
- **Acceptance:** uses the seal, the episode testability rule, the corrected power (over-dispersed counts, corrected threshold) and TOST; three declustering methods; the tidal control is restricted by mechanism or removed with a stated reason; the negative control is a distribution of shifts; the plan equals D2 with its OSF DOI; one clean, logged re-run.
- **Tests:** the three test files above.
- **Depends on:** WP-03, 04, 08, 25, 26, D2, H1. **Parallel:** wave 4 (with WP-14).
- **Implementer:** senior-implementer (Opus). Risk: same integration risks as WP-14, plus the ensemble of declustered catalogues changing the family.

#### WP-28 Earthquake paper on the template
- **Files:** `studies/earthquake/paper/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd`, `references.bib`, `numbers_allowlist.txt` (new), `papers/targets.yaml`, `_quarto.yml` (only if the navbar entry changes).
- **Acceptance:** follows PAPER_ROADMAP section 2.2; reads through the paper kit; passes the key gate; fixes the review's minor points (two amendments, the BY dependence wording); builds to the journal format.
- **Tests:** `tools/check_paper_keys.py` on the paper, `tests/test_site_pages.py`.
- **Depends on:** WP-27, 16, 17, 24; after WP-19. **Parallel:** wave 6, after WP-19.
- **Implementer:** implementer (Sonnet).

#### WP-29 Flood study skeleton, simulated data only
- **Files (new):** `studies/monsoon/README.md`, `hypothesis.yaml` (from D3), `scripts/fetch_rainfall.py`, `scripts/simulate.py`, `scripts/pipeline.py`, `tests/test_flood_pipeline.py`.
- **Note:** `studies/monsoon/` already exists with unverified rule files from the outside agent; this package uses that folder name and leaves `rules/` to the ingest flow (WP-10).
- **Acceptance:** the pipeline runs end to end on simulated rainfall and produces the Stage 1 power table; it raises if given a real outcome file while the plan lacks the Stage 1 acceptance record (tested); fetch scripts download and hash, and compute nothing.
- **Tests:** `tests/test_flood_pipeline.py`.
- **Depends on:** WP-10, WP-11, WP-24, D3. **Parallel:** wave 3.
- **Implementer:** implementer (Sonnet). The firewall is enforced by code and by test, so no senior model is needed.

#### WP-30 Park the non-research studies (review item 10)
- **Files:** `studies/numerology_vs_astrology/README.md`, `studies/remedy_conflict_matrix/README.md`, `studies/mundane/README.md`, `studies/README.md`, `_quarto.yml` (labels and menu grouping, after WP-B), `site/index.qmd`.
- **Acceptance:** each is labelled "note, not a research result" with the reason; the site menu separates "Papers" from "Notes"; nothing is deleted.
- **Tests:** `tests/test_site_pages.py`.
- **Depends on:** WP-B. **Parallel:** wave 2.
- **Implementer:** implementer (Sonnet).

### Waves (packages in one wave share no files)

| Wave | Packages | Gate before the next wave |
|---|---|---|
| 0 | WP-A, WP-B (in progress) | merged |
| 1 | WP-01, 02, 03, 04, 05, 06, 07, 10, 13, 16, 20, 21, 24, 26 | each package's own tests |
| 2 | WP-08, 09, 11, 17, 22, 30 | calibration suite green (M2 nearly reached) |
| 3 | WP-12, 18, 23, 25, 29 | CI paper gate live; data verified (M3) |
| 4 | WP-14, 27 | D1 and D2 written; H1 and H5 done |
| 5 | WP-15 | clean re-run in the ledger |
| 6 | WP-19, then WP-28 | key gate passes; submit (M4, M5) |

### Review roadmap coverage

| Review item | Packages |
|---|---|
| 1 Withdrawn material off the site | WP-B, WP-01, WP-30 |
| 2 Shift test | WP-A |
| 3 Price data | WP-11, WP-12 |
| 4 Real registration | WP-03, WP-15, H1 |
| 5 Calibration suite | WP-02, WP-18 |
| 6 Slow-indicator inference | WP-04, WP-05 |
| 7 Baselines and controls | WP-06, WP-07, WP-09 |
| 8 Power, equivalence, project multiplicity | WP-08 |
| 9 Earthquake upgrade | WP-25, WP-26, WP-27, D2 |
| 10 Consolidate and narrow | WP-13, WP-23, WP-11, WP-19, WP-30 |
| Paper template and results-key gate | WP-16, WP-17, WP-18 |
| Principle-validation tooling | WP-20, WP-21, WP-22 |
| Gemini ingest validator | WP-10 |
| Gold and silver merged | WP-19 |
| Forecast scoring | WP-24 |
| Flood Registered Report | WP-29, D3 |
