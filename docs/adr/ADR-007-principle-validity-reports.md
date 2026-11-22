# ADR-007: Principle validity reports

- Status: proposed
- Date: 2026-11-22
- Deciders: repository owner (single developer); architect (design only)
- Builds on: [ADR-003](ADR-003-rule-workbench.md) (rule files, explore and confirm), [ADR-004](ADR-004-paper-production-and-principle-validation.md) (levels L0 to L6, D-5 data quarantine, D-6 slow indicators, D-7 results-key gate), [ADR-006](ADR-006-retrospective-mundane-chart-engine.md) (method catalogue, national charts)
- Supersedes: the forecasting parts of [ADR-005](ADR-005-pattern-discovery-and-claims-registry.md) (section 12 below). Amends ADR-004 D-1, D-4, D-8 and ADR-006 section 10.
- Inputs: [FINDINGS_LEDGER.md](../research/FINDINGS_LEDGER.md), [RESEARCH_REVIEW_2026-11-22.md](../../RESEARCH_REVIEW_2026-11-22.md), [INCOMING_AUDIT_2026-11-22.md](../research/handover/INCOMING_AUDIT_2026-11-22.md) (round 4), `rules/`, `studies/*/hypothesis.yaml`, the committed `results.json` files
- `core/` below stands for `libs/vedic_astrology_core/`.

## The scope (owner's words, binding)

"The research is about how much astrology can predict the incident: which astrological theories can be used to explain or predict gold price fluctuations, weather (monsoon, flood) or earthquakes, tested on past events. We do not forecast the future. Focus only on what can prove or disprove astrological principles. The application must be modular: when an astrologer brings a new theory, permutation or combination, it can be added or modified with little effort and the reports update. Everything found (principles, data) must be documented, and established reports generated. Reports must be unbiased and say whether each astrological principle is valid on the given dataset, if not how much (what effect size is ruled out), and the limitations of the principle as we operationalised it."

## Short answer

1. **The product is a set of validity reports.** One card per principle, one report per domain, one summary across domains, one catalogue page. HTML site and PDF.
2. **One principle is one rule file.** Adding a principle, a combination or a permutation is a YAML edit. Python is needed only for a new predicate, and that is one module.
3. **One pipeline for every principle.** Calendar, testability gate, effect size, p-value, family correction, equivalence bound, sensitivity, verdict. No principle gets a special path.
4. **Five verdicts, fixed in advance.** Supported; Not supported, not excluded; Effect excluded above X; Contradicted; Untestable on this data. Each is a formula, not a judgement (section 5).
5. **Every tested principle gets a number X.** "Effects larger than X are ruled out by this dataset." This is the answer to "if not valid, how much".
6. **Permutations are declared and counted.** Every variant takes a slot in a fixed family budget. Nothing is searched silently.
7. **No forecasting.** No forecast ledger, no model registry, no scoring of published predictions. These are removed from the plan (section 12).
8. **First slice:** gold, silver and earthquake on the existing principles through the new pipeline, with the first full report set. Second slice: monsoon on the IITM rainfall series.

## 1. Vocabulary

| Word | Meaning |
|---|---|
| Principle | One claim from a text or a practitioner, written as one rule file in `rules/`. It has an id, a source, conditions and a claimed direction. |
| Lineage | A principle across its versions. A changed condition or parameter value is a new version of the same lineage. |
| Variant | A declared alternative setting of one principle (another orb, another window, another node model). |
| Method | A way to compute something for a national chart (ADR-006 catalogue, `rules/mundane/methods/`). |
| Domain | Gold, silver, earthquake, monsoon, flood, national charts. |
| Outcome | One measured thing in a domain (next-day gold return; a mainshock; June to September rainfall). |
| Test | One principle version, one variant, one outcome, one primary dataset. A test takes one **slot**. |
| Family | All tests of one domain. Its size is the domain's **budget**, fixed before any outcome is read. |
| Episode | One unbroken run of a principle being active (ADR-004 D-6). The unit of evidence. |
| SESOI | Smallest effect size of interest. Fixed per outcome in the domain plan. |
| Run | One sealed execution of the pipeline for one domain. Has a run id and hashes. |

## 2. Why explore and confirm stay

We test only the past. But we still split each past dataset once into an explore period and a confirm period. This is not forecasting. It is the only honest way to test a rule that people were allowed to adjust. An astrologer may tune an orb or a window on the explore years. Tuning always makes the explore result look better than it is. The confirm years are kept shut until the rule is frozen, then opened once. If the rule still works there, the result was not made by the tuning. Both periods are history. Nothing is said about any date after the data end. Where the project has already looked at a confirm period (earthquakes 2011 to 2026, described in the ledger), the report says "pseudo-out-of-sample", as ADR-004 D-2 requires.

One asymmetry is deliberate and is printed in every report. **Support needs the confirm period. Ruling out a large effect may use the whole period.** Tuning can only inflate an effect in the claimed direction. So a tuned estimate makes an exclusion harder, never easier. The exclusion is therefore safe on all the data; the support is not.

## 3. One principle is one rule file

### 3.1 What exists and is reused

| Piece | Where | State |
|---|---|---|
| Rule file format and JSON Schema | `rules/schema.json`, `core/rules/schema.py` | Built. 43 predicates, connectives `all_of`, `any_of`, `at_least`, `params` with ranges, `$name` references. |
| Rule files | `rules/financial` (25), `rules/seismic` (8), `rules/mundane` (85), `rules/general` (3) | Built. Most are L0 or L1. |
| Method catalogue | `rules/mundane/methods/` (27 files), `core/mundane/catalogue.py` | Built (WP-48). |
| CLI | `astro-rules validate, test, explain, list, fit, confirm, dose, review, schema` | Built. |
| Predicate registry | `core/rules/predicates/`, decorator `@predicate` | Built. |

The existing study indicators (14 gold, 14 silver, 13 earthquake) live inside `studies/*/hypothesis.yaml`, not in `rules/`. WP-71 moves each into a rule file, unchanged, so that every principle has one home.

### 3.2 Additions to the rule file (schema v3, all optional)

Old files load unchanged. A principle enters a validity report only when it has a `tests` block.

```yaml
reading:                         # which reading of the source is tested
  kind: forward_trigger          # forward_trigger | concurrent | post_event_classification
  text_says: post_event_classification
  note: >-
    Brihat Samhita ch. 32 reads the mandala after an earthquake to judge its
    results. We test it as a trigger. The text does not make that claim.
operationalisation:              # every choice the source does not fix
  - choice: orb
    value: 8 deg
    fixed_by: project            # text | practitioner | project
    note: The verse gives no orb.
  - choice: node
    value: mean
    fixed_by: project
tests:                           # where this principle is tested; one slot each
  - domain: earthquake
    outcome: mainshock_rate
    direction: increase
  - domain: gold
    outcome: abs_return
    direction: increase
variants:                        # declared permutations; never searched
  - id: orb_10
    role: candidate              # candidate: one slot per outcome, own verdict
    params: {orb: 10}
    reason: A named practitioner uses 10 degrees.
    source: {text: "...", url: "...", archive_url: "..."}
  - id: true_node
    role: sensitivity            # sensitivity: no slot, no verdict, shown on the curve
    conventions: {node_model: "true"}
```

One new leaf lets a combination point at existing principles instead of copying them:

```yaml
conditions:
  all_of:
    - use: seismic.mangal_ketu_primary      # the frozen primary conditions of that principle
    - moon_mandala: {mandalas: [agni]}
```

### 3.3 Steps for an astrologer

**A. A new principle (no Python).**

| Step | Action | Command |
|---|---|---|
| 1 | Create `rules/<domain>/<name>.yaml` (`practitioner/` subfolder for a modern source). Fill `id`, `name`, `domain`, `claim`, `source`, `tier`, `conditions`, `params`, `expected_effect`, `reading`, `operationalisation`, `tests`, and at least two `reference_cases` (one fires, one silent). | editor, with schema hints |
| 2 | Check the file. | `astro-rules validate <file>` |
| 3 | Run the reference cases. | `astro-rules test <file>` |
| 4 | See the citation level and what is missing for the next one. | `astro-rules level <file>` (WP-20) |
| 5 | Register it. This gives each test a slot and writes `studies/validity/family.lock.json`. It reads no outcome. | `astro-validity register <file>` |
| 6 | See whether the data can test it at all (episodes, attainable p). Still no outcome read. | `astro-validity gate <id>` |
| 7 | Run and rebuild the reports. | `astro-validity all` |

**B. A new combination of existing predicates or principles (no Python).** Same seven steps. The file's `conditions` join predicates with `all_of`, `any_of`, `at_least`, or join whole principles with `use:`. A combination is a new principle with its own id, its own slot and its own card. The card links to its parents.

**C. A parameter permutation (no Python).** Three legal ways, and no others.

| Way | How | What it costs |
|---|---|---|
| Declared candidate variant | Add an entry to `variants` with `role: candidate` and a reason. | One slot per outcome. Own verdict. |
| Declared sensitivity variant | Add an entry with `role: sensitivity`. | No slot. No verdict. It can lower robustness, never raise a verdict. |
| Tuning on explore data | `astro-rules fit <file> --study <domain>` sweeps the declared `params` ranges on the explore period only. The chosen value becomes a new version. | One slot for the new version. The number of cells tried is logged and printed on the card. The old version keeps its slot. |

**D. Changing a principle.** Edit the file and raise `version`. The old version's results stay in the record. The changelog shows old and new side by side (section 9).

**E. When Python is needed: a new predicate.** Only when no existing predicate can express the condition. One module, one pattern:

1. Add one file `core/rules/predicates/<name>.py` with a parameter class and one function under `@predicate("<name>", <Params>, category=..., example=...)`. The docstring names the source. The function reads the sky from `EvalContext` and returns an `Outcome`. It may not read any outcome data.
2. Add one test file `tests/test_rules_predicates_<name>.py` with known dates.
3. Run `astro-rules schema > rules/schema.json`.

WP-65 makes the registry discover modules in the folder, so step 1 touches no shared file. A method for national charts follows ADR-006 section 4.5 instead (one YAML entry plus its implementation).

### 3.4 Multiplicity rules

| Rule | Enforced by |
|---|---|
| Each domain plan declares a **budget** M of slots before any outcome is read. | Plan loader |
| Every test (principle version x candidate variant x outcome) takes one slot, in order of registration. | `family.lock.json` |
| All corrections use M, not the number used so far. Empty slots count as p = 1. So adding a principle does not change old verdicts. | `core/validity/family.py` |
| A slot is never freed. A withdrawn, superseded or untestable test keeps its slot. | Lock file is append-only and hash-chained |
| A run fails if the rule files and the lock disagree. | `astro-validity run` |
| Raising M is a dated plan amendment. Every verdict in the domain is recomputed and the changelog shows each change. | Section 9 |
| Sensitivity variants and tuning cells take no slot but are counted and printed: "specifications examined: 1 primary, c candidates, s sensitivity, g tuning cells". | Card |
| A project-wide count of all hypotheses ever tested is kept (ADR-004 WP-08, `scripts/project_multiplicity.py`). | Summary report |

## 4. Domain adapters

A domain adapter is one Python module in `core/domains/` plus one plan file `studies/validity/domains/<domain>.yaml`. The adapter gives the pipeline five things: the dataset with its hash and grade, the time grid, the outcomes, the controls, and the explore and confirm periods. It has two separate entry points, `calendar()` and `outcomes()`. The gate step can only call the first.

### 4.1 Dataset grades

| Grade | Meaning | Verdicts allowed |
|---|---|---|
| A | Fetched by our script from the primary provider; hash in `data/snapshot_index.json`; reproduced independently; licence read by the owner | All |
| B | As A, but the licence is unread, or a unit conversion or a second-source cross-check is still open | All, with the open item printed as a limitation |
| C | Not verified, or a known quality flaw (review C4) | None. Numbers are shown as "descriptive". Verdict is Untestable (reason: data quality). |

### 4.2 The adapters

Source status is from the round 4 audit. Splits, SESOI values and budgets below are **proposals**. Design tasks D8 and D9 fix them in the plan files, and the owner approves them (H16), before any outcome is joined.

| Domain | Primary dataset (audit status) | Outcomes | Baselines and controls | Explore / confirm (proposed) | SESOI (proposed) | Budget M (proposed) |
|---|---|---|---|---|---|---|
| **Gold** | Daily: Bundesbank Frankfurt fixing, DEM per kg, 1968-06-18 to 1998-12-30, 7,622 values, SHA-256 `87c15f38...` (real; grade B until the licence is read and a DEM/USD series is verified). Monthly: World Bank Pink Sheet, CC BY 4.0, used from 1968-04 (before that the price was officially fixed), snapshot `worldbank_pinksheet_3c8d9d8dbb48.xlsx` (grade A). Yahoo `GC=F` is grade C. | Daily log return; absolute return standardised with past-only volatility (WP-05); extreme-move flag (past-only 95th percentile). Monthly log return and absolute return. | Month, weekday, turn of month; festival days computed in-house (WP-06; the Gemini festival file is rejected); macro terms known at t-1 once their fetch is verified; placebo skies (WP-07). | Daily: to 1986-12-31 / from 1987-01-01. Monthly: to 1999-12 / from 2000-01. | Mean return 25 bp a day; extreme-move rate +3 points on 5%; monthly return 2 points | 60 |
| **Silver** | Monthly: World Bank Pink Sheet (grade A). Daily: none verified. Yahoo `SI=F` is grade C (median volume 53 contracts). | Monthly log return and absolute return. Daily outcomes are Untestable (data quality) until a verified daily series exists. | As gold; gold return as a co-movement control | to 1999-12 / from 2000-01 | Monthly return 3 points | 60 |
| **Earthquake** | USGS ComCat, Himalayan arc polygon of the existing plan, 1976 onward (existing snapshot; round 4 box extract hash reproduced). ISC Bulletin extract as the cross-check catalogue (hash reproduced). Grade B: magnitudes are mostly converted from mb (review M7). | Mainshock rate on an hourly grid, Mw at or above the completeness threshold | **Aftershock declustering:** Gardner-Knopoff (primary), nearest-neighbour, ETAS when WP-26 lands; the other methods are sensitivity cells. Tidal phase as positive control. Shifted sky as negative control (a distribution of shifts). Monsoon-season flag. | 1976 to 2010 / 2011 to end. The confirm period has been seen descriptively: pseudo-out-of-sample. | Rate ratio 2.0 | 40 |
| **Monsoon** | IITM all-India and macro-region rainfall, 1871 to 2016 (hash reproduced; grade B, licence unclear until H4). 30 subdivisions as secondary. | June to September all-India rainfall as percent of the long-period average; drought year (below -10%) and excess year (above +10%); monthly totals June to September | **ENSO:** NOAA ONI (hash reproduced, from 1950) and a long Nino 3.4 series (named usable; hash at fetch). **IOD:** DMI. Sunspot number (SILSO). A 31-year running mean for rainfall epochs. Last year's anomaly. | 1871 to 1960 / 1961 to 2016 | 5% of the long-period average; drought-year risk ratio 2.0 | 40 |
| **Flood** | DFO Global Flood Records (Zenodo, CC0, hash reproduced; grade A after fetch). South Asia subset. | Large-flood event rate per country and per basin group | Season-matched control dates in other years (ADR-006 control C1, `core/mundane/controls.py`); ENSO and IOD; year strata, because reporting grows over time | First 60% of years / last 40%, cut on a calendar year | Rate ratio 2.0 | 30 |
| **National charts** | ADR-006 registries: `data/registry/mundane/charts.yaml`, `events.jsonl`, with chart grades A to X | Event against matched control dates, per catalogued factor | C1 season-matched dates, C3 placebo charts, founding-time stability (ADR-006 sections 1.3, 3.4) | As `studies/mundane/hypothesis.yaml` | As that plan | As that plan |

Notes:

- Monsoon onset over Kerala is verified only for 2014 to 2025 (12 dates). Onset principles are Untestable until the 1901 to 2013 dates are checked.
- A principle is tested on one primary dataset per outcome. A second dataset (monthly gold for a daily test, ISC for USGS) is a sensitivity cell.
- No value from `research/incoming/` is an input. Our own fetch scripts download from the provider (ADR-004 D-5). Gemini's scripts are not run.
- The IMD forecast table, the Raman "forecasts" and the fabricated quotes named in the audit are not used anywhere.

### 4.3 Amendment to ADR-004 D-8 (flood firewall)

D-8 kept the monsoon and flood pipeline on simulated data until a journal accepted a Stage 1 plan. The owner's scope now asks for a retrospective monsoon test. The firewall is kept in a simpler form: the monsoon and flood adapters refuse real outcomes until (a) the domain plan is committed with `status: registered` and its hash, (b) the calibration test of WP-70 passes on simulated rainfall, and (c) the family lock exists. Owner confirmation is task H17.

## 5. The evaluation pipeline

The same eight steps for every test. Steps 1 and 2 read no outcome.

| Step | What | Output | Reuses |
|---|---|---|---|
| 1 Activity calendar | Evaluate the principle on the domain's time grid over the whole period. Record duty cycle and the list of episodes. | `calendar` block | `core/rules/grid.py`, `stats/episodes.py` |
| 2 Testability gate | Decide from the calendar alone whether the data can test the principle. Write `gate.json` and its hash before outcomes are loaded. | `gate` block, or verdict Untestable | `episodes.testable`, `mundane/burden.py` (MDE) |
| 3 Effect size with interval | Estimate the effect on the outcome's own scale, with a 95% interval that respects episodes. | `effect` block | `stats/rates.py`, `episodes.wild_cluster_interval` |
| 4 p-value | Exact or episode-level p in the claimed direction. | `p` block | `stats/permutation.py` (exact shift), `episodes.sign_flip_test` |
| 5 Family correction | Benjamini-Yekutieli at the domain budget M. | `q` values | `stats/multiplicity.py` |
| 6 Equivalence bound | The number X: effects above X are ruled out. Test against the SESOI. | `bound` block | `stats/equivalence.py`, WP-08 |
| 7 Sensitivity and robustness | Declared grid only: ayanamsa, node model, orb, window, declustering, second dataset, baselines, placebo skies. | `sensitivity` block | `stats/speccurve.py`, WP-06, WP-07 |
| 8 Verdict | A pure function of the numbers above. | `verdict` block | new, `core/validity/verdict.py` |

### 5.1 Step 2: the gate

A test is checked for two abilities. "Can support" uses the confirm period. "Can limit" uses the whole period.

| Gate | Rule | If it fails |
|---|---|---|
| G1 Encoded | The rule loads, is `active`, has conditions, and its reference cases pass | Untestable: not encoded |
| G2 Operationalised | Level L2 or above (ADR-004 D-4): parameters, direction and conventions are stated | Untestable: not operationalised |
| G3 Data grade | Primary dataset is grade A or B | Untestable: data quality |
| G4 Episodes | At least 8 episodes in the period (ADR-004 D-6) | Untestable: too few episodes |
| G5 Attainable p | The smallest p the test can reach is below the rank-1 threshold 0.05 / (M x (1 + 1/2 + ... + 1/M)) | Untestable: p not attainable |
| G6 Expected counts | For event outcomes, at least 5 events expected inside and outside the active time | Untestable: too few events |
| G7 National charts only | ADR-006 stability and chart-grade rules | Untestable: founding time too coarse |

- If "can support" fails but "can limit" passes, the test runs. It cannot return Supported. The card says: "This dataset could not have supported the principle. It could only limit it."
- If both fail, the verdict is Untestable and no outcome statistic is computed.
- The gate also prints the minimal detectable effect at 80% power for the confirm period, so a reader sees what the test could have found.

### 5.2 Steps 3 to 6: the numbers

| Outcome type | Effect scale | Interval | p-value |
|---|---|---|---|
| Event rate (earthquake, flood) | Rate ratio, active against inactive time | Episode-clustered bootstrap on the log rate ratio; the exact binomial interval is shown beside it | Exact circular shift of the calendar when the calendar class passes calibration; otherwise episode-level sign-flip |
| Continuous (returns, rainfall anomaly) | Mean difference in the outcome's unit (bp a day; percent of the long-period average), and the same in standard-deviation units | Wild cluster interval over episodes | As above |
| Yes or no per period (extreme move, drought year) | Risk difference and risk ratio | As above | As above |

- Which p-method a calendar gets is decided from the calendar, before outcomes. The calibration suite found the shift test anti-conservative for retrograde calendars of about ten long episodes. Such classes use the sign-flip test. WP-70 holds the list.
- For monsoon the unit is the year. An active year is compared with nearby inactive years (a local baseline), so slow rainfall epochs do not pass as an effect.
- The effect is signed so that positive means "in the claimed direction". A claim with `direction: either` is tested two-sided on the absolute effect.
- **X95** is the one-sided 95% upper limit of the effect in the claimed direction, on the whole period. It is printed on every card for every tested principle, whatever the verdict.
- **X-strict** is the same limit at level 1 - 0.05/M. It is printed beside X95.
- The equivalence p-value tests "the effect is at least the SESOI". It gets the same family correction as the support p-value. **Support and exclusion face the same bar.**

### 5.3 Step 7: robustness checks

All cells are declared in the domain plan or in the rule's `variants`. None can upgrade a verdict.

| Check | Rule for "passes" |
|---|---|
| R1 Baselines | After removing the domain's baselines from outcome and calendar, the effect keeps its sign and its 95% interval excludes zero |
| R2 Placebo skies | The real sky ranks in the top 5% of at least 200 placebo skies (time-shifted, tropical, scrambled labels) |
| R3 Sensitivity grid | The effect has the same sign in at least 80% of declared cells (ayanamsa: Lahiri, Raman, KP, true Chitrapaksha; node: mean, true; orb and window at their declared min and max; each declustering method; second dataset) |
| R4 Separability | The calendar is not the same variable as a baseline (association below 0.8). Sun-in-sign principles fail this against calendar month. |

Positive and negative controls (tidal phase, shifted sky) are run through the same steps and shown in the domain report. If the positive control is not detected, every card in that domain carries the line "the method did not detect the known control effect of size ...".

### 5.4 Step 8: the verdict scale

Fixed symbols: alpha = 0.05. M = domain budget. All q-values are Benjamini-Yekutieli at M.

- `q_sup`: support p-value, claimed direction, **confirm period**.
- `q_opp`: p-value for the opposite direction, whole period.
- `q_eq`: equivalence p-value against the SESOI, whole period.

The first row that matches is the verdict.

| Order | Code | Verdict (exact words in reports) | Condition | What the report may say |
|---|---|---|---|---|
| 0 | U | **Untestable on this data** | The gate fails for both abilities | "This dataset cannot test this principle, because ...". Nothing about truth. |
| 1 | S | **Supported on this dataset** | "Can support" passed, and `q_sup` < 0.05, and the explore effect has the same sign, and R1 to R4 pass | "The effect was found in the held-out period and survived the controls." Never "proven". |
| 2 | C | **Contradicted** | Directional claim, and `q_opp` < 0.05 | "The data show an effect in the opposite direction." |
| 3 | E | **Effect excluded above X** | `q_eq` < 0.05 | "An effect of the claimed size (SESOI) or larger is ruled out. The data rule out effects above X95." |
| 4 | N | **Not supported, not excluded** | Everything else | "No effect was shown. Effects above X95 are ruled out. Effects between zero and X95 are not." |

Flags, printed next to the verdict, never changing it:

| Flag | When |
|---|---|
| `signal_not_robust` | `q_sup` < 0.05 but one of R1 to R4 failed. The verdict is N or E, and the failed check is named. |
| `below_sesoi` | Verdict S, but the estimate is smaller than the SESOI |
| `limit_only` | "Can support" failed in the gate |
| `tuned` | The tested version came from `astro-rules fit`; cells tried are shown |
| `pseudo_out_of_sample` | The confirm period had been seen before the run |
| `control_not_detected` | The domain's positive control was not detected |

Why this is unbiased:

- The scale, alpha, M and each SESOI are fixed in a hashed plan before outcomes are read.
- The verdict is computed by one pure function. No person chooses it. The function has a test for every row and every boundary.
- A failure to find an effect is never called a disproof. It is N, with the bound X95, unless the equivalence test passes.
- Support and exclusion use the same correction.
- Every test is published: winners, losers and untestable ones.
- Words such as "proven", "disproved", "astrology works", "astrology fails" are on the paper gate's deny-list.

### 5.5 The scope line

A verdict is about the principle **as encoded**. The second line of every verdict states how far that reaches, from the computed level (ADR-004 D-4, WP-20):

| Level | Scope line |
|---|---|
| L2 | "As encoded by the project. The source has not been checked at the page, and the computation has not been cross-checked." |
| L3 | "As encoded, computation cross-checked. Faithfulness to the source is not attested." |
| L4 and above | "An independent astrologer attests that the encoding is faithful to the source." |

This amends ADR-004 D-4 in one point: a rule may enter a family at L2, not L3, but below L4 no report may say that the classical principle itself was tested. Only the encoding was.

### 5.6 The result record

One record per test in `studies/validity/runs/<run_id>/<domain>/results.json` (schema `validity-result/1`):

```yaml
test_id: seismic.mangal_ketu_primary@v2/primary/earthquake.mainshock_rate
slot: 14
principle: {id, version, lineage, file_sha256, level, tier, source}
variant: {id: primary, role: primary, params: {orb: 15}}
dataset: {id, grade, sha256, span, n_units, n_events}
calendar: {duty_cycle, episodes_explore, episodes_confirm, episodes_full, p_method}
gate: {can_support, can_limit, failed: [], attainable_p, threshold, mde_confirm}
effect: {scale, explore: {est, ci}, confirm: {est, ci}, full: {est, ci}, standardised}
p: {support_confirm, opposite_full, equivalence_full}
q: {support, opposite, equivalence, budget: 40}
bound: {sesoi, x95, x_strict}
robustness: {baselines, placebo_rank, sensitivity_same_sign_share, separability, cells: [...]}
verdict: {code: N, words, flags: [], scope_line}
limitations: [...]            # section 6
examined: {primary: 1, candidates: 0, sensitivity: 5, tuning_cells: 18}
```

## 6. Limitations, recorded automatically

Each card has a "Limits of this test" box. Code builds it from the rule file, the plan and the calendar. Nobody writes it by hand.

| Limitation | Built from | Example line |
|---|---|---|
| Citation level | `core/rules/levels.py` (WP-20); for methods, ADR-006 `citation_status` | "Level L1. The chapter is named but no page or quotation has been checked. The cited chapter (BS 17) is about planetary war, not earthquakes." |
| Tradition | `tier`, method `tradition` | "Modern practice. The classical mundane text does not use national founding charts." |
| Reading tested | `reading` | "The text reads the mandala after an earthquake. We tested it as a trigger. A null here does not test the text's own claim." |
| Choices the text does not fix | `operationalisation` entries with `fixed_by: project`; every `params` entry without `range_source` | "Orb 8 degrees: chosen by the project. Other schools use 13 and 15." |
| Conventions | Plan and rule: zodiac, ayanamsa, node, house system, sampling time and place | "Lahiri ayanamsa, mean node, sky sampled at 15:00 London." |
| Data span and quality | Dataset entry and grade | "1968 to 1998 only. Prices in German marks. Licence not yet read." |
| Evidence amount | Calendar | "Active 4% of the time, 9 episodes in the confirm period. Smallest detectable effect: rate ratio 3.1." |
| What was not tested | Outcomes of the domain with no `tests` entry; gate failures | "Not tested on monsoon onset: verified onset dates cover 12 years." |
| Separability | R4 | "Sun in Leo is almost the same variable as mid-August to mid-September. A calendar effect cannot be told apart." |
| Seen before | Plan `pseudo_out_of_sample` | "The confirm years were looked at in an earlier study." |
| Disputes | `rules/**/DISPUTES.md` entries linked by rule id | "Schools disagree on the sign of this effect." |

A rule file that has a `tests` block but no `reading` or no `operationalisation` block fails `astro-validity register`.

## 7. Reports

### 7.1 What is produced

| Report | One per | Content |
|---|---|---|
| **Principle card** | Principle lineage | Claim in the source's words; source and level; conditions in plain words; verdict and scope line for each test and candidate variant; effect with interval; X95 and X-strict; activity calendar strip; sensitivity curve; robustness checks; limits box; version history. |
| **Domain report** | Domain | Dataset, hash, grade, licence; outcome definitions; baselines; split; SESOI and budget with slots used; table of every test sorted by slot (not by p); count of each verdict; controls; expected false findings by luck. |
| **Cross-domain summary** | Run set | One table: principles in rows, domains in columns, verdict codes in cells. Counts by verdict. Project-wide count of everything tested. What the data cannot say. |
| **Principle catalogue** | Repository | Every rule file and method: id, source, tradition, level, status (active, needs predicates, needs verification, withdrawn), domains tested, latest verdict per domain, link to card. Principles with no test are listed too. Replaces the data behind `site/principles.qmd`. |
| **Data catalogue** | Repository | Every snapshot: provider, span, rows, hash, licence decision, grade, which domains use it. Built from `data/snapshot_index.json` and `data/registry/licences.yaml`. |
| **Changelog** | Repository | Section 9. |

### 7.2 How they are built

```text
rules/*.yaml + studies/validity/plan.yaml + domains/*.yaml + data/snapshots (hashed)
        |  astro-validity run            (sealed; writes results.json per domain)
        v
studies/validity/runs/<run_id>/<domain>/results.json + gate.json + manifest.json
        |  astro-validity report         (reads JSON only; computes nothing)
        v
site/validity/*.qmd (generated) --> HTML site ;  reports/validity/<run_id>/validity-report.pdf
```

- **One command:** `astro-validity all` (also `make validity`). It registers nothing; it runs every domain whose inputs changed, rebuilds every report, and writes the changelog entry.
- **Reports read numbers only through `core/paperkit/results.py`.** A missing or null key stops the build (ADR-004 D-7, WP-16). `tools/check_paper_keys.py` runs on the generated pages: no bare number, no deny-listed word.
- **Run seal (WP-03).** A run refuses a dirty tree unless `--provisional`. Provisional results are watermarked and cannot be published. Each result is stamped with commit, plan hash, lock hash, rule-file hashes, dataset hashes, ephemeris model and seed.
- **Confirm is one-shot per lineage version.** The confirm period of a test is opened once, logged in `studies/validity/confirm_ledger.jsonl` (WP-03 ledger). A later run reuses the stored record and checks that it reproduces exactly. A changed rule is a new version and a new slot.
- **Versioned and hashed.** `run_id` = date plus the first 12 characters of the hash over all inputs. `reports/validity/<run_id>/report_manifest.json` lists the SHA-256 of every results file and every rendered file. The PDF title page prints the run id and the manifest hash.
- **HTML and PDF from the same generated pages**, through Quarto. The PDF is one book: summary, domain reports, cards, catalogue, changelog.
- **No confirm-period number reaches the site before its sealed run.**

## 8. Modules and files

| Path | Role | New? |
|---|---|---|
| `core/validity/plan.py` | Strict loader for `studies/validity/plan.yaml` and `domains/*.yaml` | new |
| `core/validity/family.py` | Slots, budget, lock file, BY at M | new |
| `core/validity/variants.py` | Expand a rule into primary, candidate and sensitivity specs; resolve `use:` | new |
| `core/validity/gate.py` | Step 2 | new |
| `core/validity/effects.py` | Steps 3, 4, 6 per outcome type (thin; calls `stats/`) | new |
| `core/validity/robustness.py` | Step 7 | new |
| `core/validity/verdict.py` | Step 8, pure function | new |
| `core/validity/limitations.py` | Section 6 | new |
| `core/validity/pipeline.py`, `record.py` | Orchestration, result schema, cache by input hash | new |
| `core/validity/changelog.py` | Section 9 | new |
| `core/validity/report.py`, `templates/` | Section 7 | new |
| `core/validity/cli.py` | `astro-validity register, gate, run, report, diff, catalogue, all` | new |
| `core/domains/base.py` | Adapter protocol, dataset grades | new |
| `core/domains/metals.py`, `earthquake.py`, `monsoon.py`, `flood.py`, `mundane.py` | Adapters | new |
| `studies/validity/` | Plans, lock, runs, ledgers | new |
| `core/rules/`, `core/stats/`, `core/paperkit/`, `core/mundane/`, `core/datasets/` | Reused as they are, except the listed schema and predicate changes | existing |

The old study folders (`studies/gold_market`, `silver_market`, `earthquake`, `combinations`) stay as the historical record. Their `results.json` files are not regenerated. The findings ledger marks their rows "superseded by run <run_id>" once the first slice has run.

## 9. Changelog

Two files, both generated.

- `studies/validity/changelog.jsonl`: append-only. Each line carries the hash of the line before it.
- `site/validity/changelog.qmd` and the PDF chapter: rendered from it.

One entry per `astro-validity all` that changed anything:

```yaml
run_id: 2026-12-03-4f2a9c1d77e0
previous_run_id: 2026-11-29-90ab13c2d4f1
inputs_changed:
  rules: [{id: seismic.mangal_ketu_primary, from_version: 2, to_version: 3,
           fields: [{path: params.orb.value, from: 15, to: 8}]}]
  datasets: []
  plans: []
  engine: null
tests:
  - test_id: seismic.mangal_ketu_primary@v3/primary/earthquake.mainshock_rate
    change: added                 # added | superseded | recomputed | unchanged
    cause: rule_changed           # rule_changed | new_principle | data_changed | plan_changed | budget_changed | engine_changed
    slot: 21
    verdict: {from: null, to: N}
    effect: {from: null, to: 0.97}
    x95: {from: null, to: 1.84}
  - test_id: seismic.mangal_ketu_primary@v2/primary/earthquake.mainshock_rate
    change: superseded
    verdict: {from: N, to: N}
summary: {slots_used: {earthquake: [20, 21]}, verdict_changes: 0}
```

Rules:

- `astro-validity diff <run_a> <run_b>` prints the same comparison for any two runs.
- A test whose inputs did not change must reproduce its stored numbers exactly. If it does not, the run stops. This catches an engine change that was not declared.
- A verdict that changes without a rule, data, plan or engine change is a bug and fails the build.
- Each card shows its own lines from the changelog under "Version history".

## 10. Decisions

| Id | Decision |
|---|---|
| F-1 | The product is validity reports on past data. No forecast is issued, stored or scored. |
| F-2 | One principle is one rule file. National-chart techniques are method-catalogue entries (ADR-006). Study indicators move into rule files. |
| F-3 | Permutations are declared as candidate variants (one slot), sensitivity variants (no verdict) or logged tuning (new version, one slot). Nothing else is allowed. |
| F-4 | Each domain has a fixed slot budget M. All corrections use M. Slots are never freed. |
| F-5 | One pipeline of eight steps for every test. The gate reads no outcome. |
| F-6 | Five verdicts and six flags, computed by one pure function, with the words fixed here. |
| F-7 | Every tested principle reports X95. Support needs the confirm period; exclusion may use the whole period. Both get the same family correction. |
| F-8 | Verdicts are about the encoding. The scope line follows the citation level. Family entry is allowed at L2 (amends ADR-004 D-4). |
| F-9 | Limitations are generated from the rule file, plan and calendar. A rule without `reading` and `operationalisation` cannot be registered. |
| F-10 | Reports are generated from sealed results JSON through the paper-kit gate. One command. Run id and hashes on every page. |
| F-11 | A hash-chained changelog records what changed in rules, data and plans, and what that did to each verdict. |
| F-12 | Datasets carry a grade. Grade C data give no verdict. |
| F-13 | The monsoon and flood firewall becomes "sealed plan plus passed calibration" (amends ADR-004 D-8). |
| F-14 | Journal papers are optional later outputs built from the same results. They are not on the critical path (amends ADR-004 D-1). |

## 11. Work packages WP-65 onward

Ground rules are those of ADR-004: run only the named tests; shared files have one owner; "implementer (Sonnet)" unless a concrete subtle risk is named, then "senior-implementer (Opus)"; no subagent on Fable. Only WP-74 edits `pyproject.toml`, `Makefile` and `_quarto.yml`. Only WP-65 edits `core/rules/schema.py` and `core/rules/predicates/__init__.py` (after WP-20).

### 11.1 What is reused

| Package | State | Role here |
|---|---|---|
| WP-A exact shift test; WP-02 calibration suite; WP-03 run seal; WP-04 episode inference; WP-10 ingest validator; WP-11 snapshot index; WP-16 paper kit | Done | Used as they are |
| WP-48 to WP-56 mundane engine, first slice | Done | Wrapped by the national-chart adapter (WP-80) |
| WP-05 past-only volatility; WP-06 baselines; WP-07 placebo skies; WP-08 power, SESOI, TOST; WP-20 levels; WP-26 ETAS declustering | Open in ADR-004 | **Kept as specified.** Needed by the first slice, except WP-26 (a sensitivity cell when it lands). WP-08 gains one function: the one-sided upper limit at a given level. |
| WP-21 JHora and Horizons fixtures; WP-22 astrologer review flow; WP-25 catalogue upgrade; WP-30 parking non-research studies | Open in ADR-004 | Kept. They raise levels and data grades. Not blocking. |
| WP-12 price data | Open | **Re-scoped:** adapters for the Bundesbank daily series and the Pink Sheet monthly series, plus the quality gate. No LBMA route. |
| WP-13 one rule engine | Open | **Absorbed by WP-71** (indicators become rule files, with an equality test). |
| WP-23 workbench guards | Open | **Absorbed by WP-66 and WP-69** (family at M, one confirm per lineage version, direction handling). |
| WP-14, 15, 27 study wiring and re-runs | Open | **Replaced by WP-76, 77, 78.** |
| WP-57 to WP-61, WP-64 mundane phase 2 | Open in ADR-006 | Kept. WP-62 (site pages) and WP-63 (confirm run) are **replaced by WP-80**. |
| WP-09, 17, 18, 19, 24, 28, 29; WP-31 to WP-47 | Open | **Withdrawn or re-scoped.** See section 12. |

### 11.2 Design tasks and owner tasks

| Id | Who | Output | Needed by |
|---|---|---|---|
| D8 | Architect | `studies/validity/plan.yaml` and domain plans for gold, silver, earthquake: datasets, outcomes, baselines, split, SESOI, budget M, sensitivity grid, calibration targets | WP-76, 77, 78 |
| D9 | Architect | Domain plans for monsoon and flood, with the list of monsoon principles to encode and their sources | WP-79, WP-83 |
| D10 | Architect | Card, domain-report and summary layouts as page skeletons with every results key named | WP-73 |
| H4 | Owner (exists) | Read the Bundesbank and IITM licences; record the decisions | Grades of gold daily and monsoon |
| H16 | Owner | Approve SESOI values, budgets and splits in D8 and D9 **before** the first run | WP-78, WP-83 |
| H17 | Owner | Confirm the D-8 amendment (section 4.3) | WP-83 |
| H11 | Owner (exists) | Open the texts; record page and quotation for cited principles | Scope lines above L2 |

### 11.3 Phase 1: the pipeline

#### WP-65 Rule schema v3: reading, operationalisation, tests, variants, `use`
- **Files:** `core/rules/schema.py`, `core/rules/tuning.py`, `core/rules/predicates/__init__.py` (discover modules in the folder), `core/rules/predicates/compose.py` (new, the `use` leaf), `rules/schema.json` (regenerated), `tests/test_rules_schema_v3.py` (new), `tests/test_rules_catalog.py`.
- **Acceptance:** every existing rule file loads unchanged; the four new blocks validate as in section 3.2; `use` resolves to the referenced rule's primary conditions with its bound parameters, refuses a missing id and a reference cycle; a predicate module dropped into the folder is registered with no edit elsewhere; a duplicate predicate name fails.
- **Tests:** the two test files; `tests/test_rules_loader.py`.
- **Depends on:** WP-20 (same file). **Implementer:** senior-implementer (Opus). Risk: a cross-file contract; a `use` cycle or a silently changed parent would change a tested calendar.

#### WP-66 Family budget, slots and lock
- **Files (new):** `core/validity/__init__.py`, `core/validity/plan.py`, `core/validity/family.py`, `core/validity/variants.py`, `tests/test_validity_family.py`, `tests/test_validity_variants.py`.
- **Acceptance:** strict plan loader (unknown key fails); a rule expands to primary, candidate and sensitivity specs; each (version, candidate, outcome) gets one slot; the lock is append-only and hash-chained; a run-time mismatch between rules and lock raises; BY at M with empty slots as p = 1 matches a hand-computed case; a test proves a slot cannot be freed and an undeclared parameter value cannot be evaluated; the budget overflow error names the plan amendment needed.
- **Tests:** the two new files.
- **Depends on:** WP-65. **Implementer:** senior-implementer (Opus). Risk: multiplicity. An undercount here inflates every "Supported".

#### WP-67 Domain adapter protocol and dataset grades
- **Files (new):** `core/domains/__init__.py`, `core/domains/base.py`, `core/domains/simulated.py` (a toy domain for tests), `tests/test_domains_base.py`.
- **Acceptance:** protocol with `dataset()`, `grid()`, `calendar_context()`, `outcomes()`, `controls()`, `periods()`; `outcomes()` raises unless a gate hash is passed; grade is computed from the snapshot index and licence register, never written by hand; grade C blocks verdicts.
- **Tests:** the new file. **Depends on:** none. **Implementer:** implementer (Sonnet).

#### WP-68 Gate, effects and verdict
- **Files (new):** `core/validity/gate.py`, `core/validity/effects.py`, `core/validity/verdict.py`, `core/validity/record.py`, `studies/validity/result.schema.json`, `tests/test_validity_gate.py`, `tests/test_validity_verdict.py`, `tests/test_validity_effects.py`.
- **Acceptance:** the gate takes a calendar and a plan and nothing else; each of G1 to G7 has a failing case; `verdict()` is a pure function with a table-driven test covering every row of section 5.4, every flag, and each boundary (q exactly 0.05; estimate exactly at the SESOI; S and E both true gives S with `below_sesoi`); X95 and X-strict agree with a closed-form case; the p-method choice is decided from the calendar class list.
- **Tests:** the three new files.
- **Depends on:** WP-08, WP-66, WP-67. **Implementer:** senior-implementer (Opus). Risk: this function writes every headline; a wrong side in the equivalence test gives a false "excluded".

#### WP-69 Pipeline, robustness and sealed runs
- **Files (new):** `core/validity/pipeline.py`, `core/validity/robustness.py`, `tests/test_validity_pipeline.py`.
- **Acceptance:** runs the eight steps in order on the simulated domain; writes `gate.json` and its hash before the adapter's `outcomes()` is called (tested with a spy); stamps results through `stats/seal.py`; one confirm per lineage version through the confirm ledger, and a version bump takes a new slot instead of resetting it; unchanged inputs reuse the stored record and must reproduce it exactly; robustness cells come only from the plan and the rule's variants; a rule that fails to evaluate stops the run.
- **Tests:** the new file; `tests/test_validity_family.py`.
- **Depends on:** WP-06, WP-07, WP-68. **Implementer:** senior-implementer (Opus). Risk: holdout leakage and confirm-ledger logic.

#### WP-70 Calibration of the whole pipeline
- **Files:** `tests/test_validity_calibration.py` (new), `tests/simulators.py` (add clustered events and yearly rainfall with ENSO-like forcing), `core/validity/gate.py` (the calendar-class list only).
- **Acceptance:** on simulated data with no effect and real calendars, "Supported" appears in at most 5% of families and "Contradicted" likewise; with a true effect equal to the SESOI, "Effect excluded" appears for at most 5% of tests; with a planted effect of twice the gate's minimal detectable effect, "Supported" appears in at least 80% of runs for tests the gate called supportable; calendar classes that fail the shift-test calibration are listed and routed to the sign-flip test.
- **Tests:** the new file (fast subset; full run marked slow).
- **Depends on:** WP-69. **Implementer:** senior-implementer (Opus). Risk: this is the evidence that the verdicts are unbiased.

#### WP-71 Existing indicators become rule files
- **Files:** `rules/financial/study/*.yaml` and `rules/seismic/study/*.yaml` (new, about 41 files), `tests/test_validity_port_equivalence.py` (new).
- **Acceptance:** one rule file per indicator of the gold, silver and earthquake plans, with `reading`, `operationalisation` and `tests` blocks and two reference cases; for each, the calendar from `core/rules` equals the old study calendar on the explore grid, bit for bit, or the difference is listed with its cause (for example aspects by degree against by sign) and approved in the report; no outcome is read.
- **Tests:** the new file; `tests/test_rules_catalog.py`.
- **Depends on:** WP-65. **Implementer:** implementer (Sonnet).

#### WP-72 Limitations builder
- **Files (new):** `core/validity/limitations.py`, `tests/test_validity_limitations.py`.
- **Acceptance:** produces every row of section 6 from a rule, a plan and a calendar; the Brihat Samhita ch. 32 mandala rule yields the "reading tested" line; a Sun-in-sign rule yields the separability line; missing `reading` or `operationalisation` raises at registration.
- **Tests:** the new file. **Depends on:** WP-20, WP-65. **Implementer:** implementer (Sonnet).

#### WP-73 Report generator
- **Files (new):** `core/validity/report.py`, `core/validity/templates/{card,domain,summary,catalogue,data,changelog}.qmd.j2`, `site/validity/_metadata.yml`, `tests/test_validity_report.py`; edit `tools/check_paper_keys.py` (deny-list words), `scripts/export_site_data.py` (catalogue export).
- **Acceptance:** builds all six report kinds from results JSON alone; every number goes through `paperkit.Results`; a missing key, a provisional result or a hash mismatch stops the build; tables are sorted by slot; the verdict words are exactly those of section 5.4; HTML and one PDF book render from the same pages; `report_manifest.json` lists every hash; a principle with no test still appears in the catalogue.
- **Tests:** the new file; `tests/test_check_paper_keys.py`; `tests/test_paperkit.py`.
- **Depends on:** WP-68 (record schema), D10. **Implementer:** implementer (Sonnet).

#### WP-74 CLI, changelog and build wiring
- **Files:** `core/validity/cli.py`, `core/validity/changelog.py` (new), `tests/test_validity_cli.py`, `tests/test_validity_changelog.py` (new), `pyproject.toml` (entry point `astro-validity`; also `astro-mundane`), `Makefile` (target `validity`), `_quarto.yml` (the `site/validity` section).
- **Acceptance:** commands of section 8; `all` is idempotent on unchanged inputs; the changelog entry matches section 9 for four cases (new principle, changed parameter, new data snapshot, raised budget); a verdict change with no input change fails; `diff` works on any two runs.
- **Tests:** the two new files.
- **Depends on:** WP-69, WP-73. **Implementer:** implementer (Sonnet).

### 11.4 Phase 2: first slice (gold, silver, earthquake)

#### WP-75 Fetch scripts for the verified sources
- **Files (new):** `scripts/fetch/bundesbank_gold.py`, `iitm_rainfall.py`, `noaa_enso.py`, `dfo_floods.py`, `usgs_catalogue.py`, `isc_catalogue.py`, `tests/test_fetch_round4.py`; `data/snapshot_index.json` and `data/registry/licences.yaml` entries.
- **Acceptance:** each script is written here (the incoming scripts are not run), downloads from the provider with a generic client name, writes a snapshot through `datasets.snapshots.write_snapshot`; the Bundesbank hash equals the audited `87c15f38...` and has 7,622 values; the other hashes equal the audit's; tests use an injected opener and no network.
- **Tests:** the new file; `tests/test_snapshots_index.py`.
- **Depends on:** none. **Implementer:** implementer (Sonnet).

#### WP-76 Metals adapter (gold and silver)
- **Files (new):** `core/domains/metals.py`, `tests/test_domains_metals.py`; uses WP-12 (re-scoped), WP-05, WP-06.
- **Acceptance:** daily Bundesbank and monthly Pink Sheet series behind one interface; the sky is sampled at the series' own fixing time and place; returns over gaps longer than four calendar days are flagged; outcomes use past-only standardisation; baselines from WP-06; Yahoo series load only as grade C.
- **Tests:** the new file; `tests/test_markets_align.py`.
- **Depends on:** WP-05, 06, 12, 67, 75. **Implementer:** senior-implementer (Opus). Risk: a wrong sampling instant or time zone shifts every Moon-based calendar.

#### WP-77 Earthquake adapter
- **Files (new):** `core/domains/earthquake.py`, `tests/test_domains_earthquake.py`; reads `studies/earthquake/scripts/decluster.py` and `fetch_catalogue.py` unchanged.
- **Acceptance:** same polygon, completeness rule and hourly grid as the existing plan; declustering method is a declared cell; tidal and shifted-sky controls exposed as control "principles"; reproduces the mainshock counts in the findings ledger (186 and 214) from the existing snapshot.
- **Tests:** the new file; `tests/test_earthquake_decluster.py`.
- **Depends on:** WP-67. **Implementer:** implementer (Sonnet).

#### WP-78 First slice run and first report set
- **Files:** `studies/validity/plan.yaml`, `domains/{gold,silver,earthquake}.yaml` (from D8), `studies/validity/family.lock.json`, `studies/validity/runs/<run_id>/`, `site/validity/` (generated), `reports/validity/<run_id>/`, `docs/research/FINDINGS_LEDGER.md` (status column only).
- **Acceptance:** all existing gold, silver and earthquake principles (WP-71) and every rule file in `rules/financial` and `rules/seismic` with status `active` are registered; calibration (WP-70) is green; one clean sealed run per domain; the full report set builds and passes the gate; every test has a verdict and, unless Untestable, an X95; the changelog has its first entry; ledger rows 3.1, 3.3 and 3.4 carry "superseded by run ...".
- **Tests:** `tests/test_validity_report.py`, `tests/test_validity_cli.py`.
- **Depends on:** WP-65 to WP-77, D8, H16. **Implementer:** senior-implementer (Opus); the sealed run and the commit are done by the main session. Risk: the one-shot confirm cannot be repeated.

### 11.5 Phase 3: monsoon, then flood and national charts

#### WP-79 Monsoon adapter and monsoon principles
- **Files (new):** `core/domains/monsoon.py`, `tests/test_domains_monsoon.py`, `rules/monsoon/*.yaml` (principles named in D9; `domain` enum gains `monsoon` and `flood` through WP-65).
- **Acceptance:** yearly grid; a principle is evaluated at the instant or window its source names (for example the Sun's entry into Ardra); outcomes and controls of section 4.2; the adapter refuses real rainfall until the three conditions of section 4.3 hold; simulated-rainfall tests pass first.
- **Tests:** the new file.
- **Depends on:** WP-67, WP-75, D9. **Implementer:** senior-implementer (Opus). Risk: with one value a year, a wrong unit of evidence makes every p-value wrong.

#### WP-83 Monsoon run on IITM data
- **Files:** `studies/validity/domains/monsoon.yaml`, lock, runs, generated reports.
- **Acceptance:** as WP-78 for the monsoon domain; the ENSO control appears in the domain report with its own effect, as the positive control.
- **Depends on:** WP-78, WP-79, H4, H16, H17. **Implementer:** main session with senior-implementer (Opus).

#### WP-80 National-chart adapter
- **Files (new):** `core/domains/mundane.py`, `tests/test_domains_mundane.py`.
- **Acceptance:** maps the ADR-006 aggregate report to the result record (found to S after robustness, excluded to E, inconclusive to N, untestable and descriptive-only to U with the reason); stability and chart grade appear as limitations; case files are linked from cards; confirm goes through the validity confirm ledger.
- **Depends on:** WP-69, WP-61. **Implementer:** senior-implementer (Opus). Risk: two verdict vocabularies must not disagree.

#### WP-81 Flood adapter and run
- **Files (new):** `core/domains/flood.py`, `tests/test_domains_flood.py`, `studies/validity/domains/flood.yaml`.
- **Acceptance:** DFO South Asia subset; season-matched controls; year strata; the same firewall as monsoon; one sealed run.
- **Depends on:** WP-79, D9. **Implementer:** implementer (Sonnet).

#### WP-82 Contributor guide and housekeeping
- **Files:** `CONTRIBUTING_ASTROLOGERS.md` (section 3.3 of this ADR as the worked path), `docs/research/CLAIMS_REGISTRY_SPEC.md` (header: re-scoped by ADR-007; sections 7 and 11 withdrawn), `docs/research/PAPER_ROADMAP.md` (forecast lines removed), `studies/README.md`, `site/principles.qmd` (reads the catalogue).
- **Acceptance:** an astrologer can follow the guide from an empty file to a rebuilt card using only the commands shown; no document describes a forecast ledger as planned; `tests/test_rules_docs.py` passes.
- **Depends on:** WP-74. **Implementer:** implementer (Sonnet).

### 11.6 Order

| Wave | Packages | Gate before the next wave |
|---|---|---|
| V0 | WP-05, 06, 07, 08, 20 (ADR-004, kept); WP-67, WP-75 | Each package's tests |
| V1 | WP-65; then WP-66, WP-71, WP-72; WP-12 (re-scoped), WP-77 | Old rule files still load |
| V2 | WP-68; then WP-69; WP-73, WP-76 | Verdict table test green |
| V3 | WP-70, WP-74 | **Calibration green.** D8 written. H16 done. |
| V4 | WP-78 | First report set published |
| V5 | WP-79, then WP-83; WP-82 | H17 done |
| V6 | WP-80, WP-81 | |

## 12. What this removes or changes in earlier ADRs

### ADR-005

| Part | Status now |
|---|---|
| Sections 1 and 2 (feasibility numbers; why naive search overfits) | **In force.** They are why section 3.4 exists. |
| E-1, E-6, E-7, E-8, E-9 (ledger first; proper scoring of forecasts; model registry; live forecast ledger; kill criteria K2 to K6) | **Superseded. Removed from the plan.** |
| E-2, E-3, E-4 (fitted model; feature grammar v2; nested walk-forward search) | **Superseded.** A pattern search does not test a stated principle. A combination enters as a declared principle (section 3.3 B). |
| E-5 (holdout levels) | Levels 1 and 2 kept as vocabulary. Level 3 (live data) removed. |
| K1 (calibrate on simulated no-effect data) | Kept, as WP-70. |
| WP-31 claims contract and validator | **Re-scoped.** The registry keeps only what a source states as a **rule**: who, where, when, the words, the conditions. It feeds `rules/**/practitioner/` at L0 or L1. |
| WP-32 claims grading and outcome scoring; WP-34 scoring extensions | **Removed.** Published predictions are not scored. |
| WP-33 site pages | **Replaced** by the principle catalogue (WP-73). |
| WP-35, 36, 37 baselines | **Merged** into WP-26, WP-06 and WP-79 as controls. |
| WP-38 to WP-41 (model registry, forecast ledger, resolvers, kill monitor) | **Removed.** |
| WP-42 to WP-46 (search engine and runs); WP-47 null report | **Removed.** The cross-domain summary replaces WP-47. |
| D4, D5, H7, H8, H9 | Lapse. |

### ADR-004

| Part | Status now |
|---|---|
| D-1 three papers | Papers become optional later outputs from the same results (F-14). WP-17, 18, 19, 28 are **deferred**; the CI gate part of WP-18 is covered by WP-73 and WP-74. |
| D-4 last paragraph (scoring ex-ante forecasts; a prospective ledger) | **Removed.** WP-24 is **withdrawn** (forecast-only). The levels table stays, with the L2 entry rule of F-8. |
| D-6 | In force; extended by section 5. |
| D-8 | Amended by section 4.3. WP-29 is replaced by WP-79 and WP-81. |
| WP-09 (SPA trading-rule benchmark) | **Withdrawn.** It scores indicators as trading forecasts. |
| WP-13, 14, 15, 23, 27 | Absorbed or replaced (section 11.1). |

### ADR-006

| Part | Status now |
|---|---|
| Engine, catalogue, registries, case files, aggregate report (WP-48 to WP-61) | **In force.** |
| Section 10, rows marked "deprioritised, can be revived" | Now **removed** as above. |
| Case file section 8 (practitioner explanations with timing class) | Not rendered in validity reports. No before-or-after classification of predictions is published. |
| WP-62, WP-63 | Replaced by WP-80 and WP-73. |
| Aggregate verdict words | Mapped to the five verdicts by WP-80. |

## 13. Consequences

Good:

- The owner's question gets a direct answer per principle: a verdict, a size that is ruled out, and the limits of the test.
- An astrologer adds or changes a principle with a YAML edit and one command, and sees exactly what changed.
- The plan is smaller. About twenty forecasting and search packages are gone.
- Every statistic module already built is reused.

Costs and risks:

- **Most first-slice verdicts will be "Untestable" or "Not supported, not excluded".** Slow planets give few episodes. A fixed budget M makes the bar high. This is the honest state of the data, and the X95 column is what makes the report useful anyway.
- **Most principles are at level L0 to L2.** The reports will say "as encoded" on almost every card until texts are opened (H11) and reviews are done (WP-22).
- **Gold daily data are in German marks and end in 1998.** Modern daily gold is untested until a verified series exists. Silver has no verified daily series at all.
- **The earthquake confirm period has been seen.** Its support verdicts carry the pseudo-out-of-sample flag.
- **The SESOI is a judgement.** It is fixed in advance and approved by the owner, and X95 lets a reader apply another threshold.
- **A fixed budget can run out.** Raising it recomputes every verdict in the domain. The changelog shows it, but a "Supported" could be lost that way.
- Allowing family entry at L2 loosens ADR-004 D-4. The scope line is the safeguard.
- Written from memory, to be checked before use: the start year of the DFO archive; the availability and provider of a long Nino 3.4 series before 1950; the official-price period of gold before April 1968 in the Pink Sheet.

## 14. Alternatives rejected

| Alternative | Why not |
|---|---|
| Keep the forecast ledger as "the only real proof" (ADR-005) | Out of the owner's scope. It also needs years to say anything. |
| One verdict of "significant or not" | It cannot tell "no effect" from "too little data", which is the main question here. |
| Correct only over the tests run so far | Each new principle would shift old verdicts, and the family could be shaped after the fact. |
| Let every orb and window be tried and report the best | This is the forking-paths problem the atlas and the review already documented. |
| Require L3 or L4 before any test | Nearly nothing could be reported for months. The scope line states the same limit without hiding the numbers. |
| Use the whole period for support when a rule was never tuned | The project has already looked at the explore years for the existing indicators. One rule for all is simpler and safe. |
| Hand-written limitations per principle | They drift and they flatter. Generated text cannot be softened for a favoured rule. |
| Keep per-study pipelines and add a report layer on top | Three pipelines already disagree on details (ephemeris label, family rule). One pipeline is the point. |
