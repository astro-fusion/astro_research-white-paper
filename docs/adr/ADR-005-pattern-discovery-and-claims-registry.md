# ADR-005: Pattern discovery, forecast ledger and claims registry

- Status: partly superseded by [ADR-007](ADR-007-principle-validity-reports.md) on 2026-11-22 (earlier amended by ADR-006). Sections 1 and 2 remain in force as the feasibility record.
- Date: 2026-11-22
- Deciders: repository owner (single developer); architect (design only)
- Builds on: [ADR-003](ADR-003-rule-workbench.md) (workbench, combination atlas), [ADR-004](ADR-004-paper-production-and-principle-validation.md) (decisions D-1 to D-9, packages WP-01 to WP-30)
- Inputs: [RESEARCH_REVIEW_2026-11-22.md](../../RESEARCH_REVIEW_2026-11-22.md), [INCOMING_AUDIT_2026-11-22.md](../research/handover/INCOMING_AUDIT_2026-11-22.md), the committed `results.json` files
- Companion documents: [FINDINGS_LEDGER.md](../research/FINDINGS_LEDGER.md) (what was found), [CLAIMS_REGISTRY_SPEC.md](../research/CLAIMS_REGISTRY_SPEC.md) (astrologer claims)

> **Superseded parts (ADR-007, owner's scope: past events only, no forecasting).**
> - **Removed:** E-1, E-6, E-7, E-8, E-9 (K2 to K6): forecast ledger, forecast scoring, model registry, kill monitor. Packages WP-32, WP-34, WP-38 to WP-41.
> - **Removed:** E-2, E-3, E-4: fitted models and the capped pattern search. Packages WP-42 to WP-47.
> - **Re-scoped:** the claims registry (WP-31) survives only as a source of **principles** that astrologers state, to be encoded as rule files and tested. Published predictions are not scored. WP-33 is replaced by the principle catalogue.
> - **Kept:** sections 1 and 2; E-5 levels 1 and 2 as vocabulary; K1 (calibration on simulated data); baselines WP-35 to WP-37 as controls inside ADR-007 packages.
> - Read the text below as history. ADR-007 section 12 has the full table.

## The question

The owner asked: no classical formula passed a test. Can we build our own model that finds planetary patterns which predict earthquakes, monsoon rain or gold? If the correlation is about zero and there is no point, say so.

## Short answer

1. **A general machine-learning "pattern finder" is not worth building.** It would find patterns every time it ran, and almost all of them would be false. The repo has already run two searches of this kind on earthquakes (705 combinations; a classifier on 83 sky features). Both found nothing.
2. **A small, strict version is worth building, in two parts.**
   - **Part 1, build now: a forecast ledger with baselines.** It records dated forecasts before the event and scores them afterwards against a strong baseline. It scores our own frozen models, classical rules and astrologers' public claims with one method. It is cheap, and it is the only thing that can ever prove or disprove a predictive claim.
   - **Part 2, build only after Part 1 and the ADR-004 re-runs: a capped, one-shot search per domain.** One declared search space, one run, one sealed check, then the ledger. It has a kill rule. The expected result is a clean published null.
3. **Per domain:** Himalayan earthquakes: no search (too few events). Annual monsoon: no search (155 data points, and the Registered Report firewall forbids it). Gold and silver: one search on fast features is defensible, after the price data are fixed. Global earthquakes: one search is defensible, after the registered Varuna test has run.

The rest of this document gives the numbers behind that answer, then the design.

---

## 1. Feasibility, with numbers

Every figure below is either read from a committed artifact or computed with a short exact calculation (binomial for event counts, normal for returns and rainfall). Assumptions are stated where used.

### 1.1 What we have

| Domain | Outcome data | Count | Rate of new data |
|---|---|---|---|
| Himalayan earthquakes | Declustered mainshocks, Mw 5.2 and above, 1976 to 2026 ([results.json](../../studies/earthquake/artifacts/results.json)) | 186 (Gardner-Knopoff), 214 (nearest-neighbour) | about 3.7 a year |
| Monsoon | All-India June to September rainfall, 1871 to 2025 (not yet fetched; see ADR-004 D-8) | about 155 seasons | 1 a year |
| Gold | Daily closes, 2000 to 2026 ([results.json](../../studies/gold_market/artifacts/results.json)) | 6,150 bars (poor quality before 2008, review C4) | about 250 a year |

### 1.2 The sky is huge and never repeats

Take only the sign (one of 12) of each of the nine grahas.

- Possible sign-level skies: about 45 million. (Mercury and Venus stay near the Sun, so they add 3 and 5 options, not 12. Rahu fixes Ketu.)
- Sign-level skies that actually occurred in 1976 to 2026: about 10,000. The Moon changes sign about 8,150 times in 50 years; all other bodies together add about 2,400 changes.
- Each of those 10,000 skies occurred **once**. Jupiter, Saturn and the nodes do not return to the same joint position inside 50 years.

So the 186 earthquakes fell on 186 skies that will never come back. Any rule detailed enough to pick out those skies is a list of dates, not a pattern. Add degrees, nakshatra padas, houses, aspects, dashas and divisional charts, and the space grows by many more orders of magnitude.

A concrete example. There are about 145,000 rules of the form "planet A in sign X, planet B in sign Y and planet C in sign Z". Each is active about 11 days in 50 years and expects 0.11 earthquakes. By chance alone, about 780 of them will contain two or more earthquakes. Each of those 780 shows a rate at least **18 times** normal. None means anything. This is why an astrologer, or a model, can always find a striking pattern after the fact.

### 1.3 How many independent tests a search really makes

Candidates overlap, so 705 tests are not 705 independent tests. The atlas gives a direct estimate. Its best candidate had nominal p = 0.005 and a Romano-Wolf adjusted p of 0.84 ([results.json](../../studies/combinations/artifacts/results.json)). Solving 1 - (1 - 0.005)^M = 0.84 gives M of about **365**. The 705 atlas candidates behave like roughly 350 to 400 independent tests.

A richer grammar (degrees, orbs, windows, lags, depth 4 or 5) easily produces 10^5 to 10^7 candidates. A fair guess is 10^3 to 10^5 independent tests. The significance bar then moves from 0.05 to between 5 x 10^-5 and 5 x 10^-7.

### 1.4 What each domain could detect

**Earthquakes.** Smallest rate ratio detectable with 80% power, one-sided, exact binomial on the in-count. "Duty" is the share of time the pattern is active.

| Events | Duty | One test (alpha 0.05) | Family of 26 (BY rank-1, 5.0 x 10^-4) | Family of 705 (BY rank-1, 9.9 x 10^-6) | Search of 10^6 (5 x 10^-8) |
|---|---|---|---|---|---|
| 128 (explore) | 25% | 1.63 | 2.20 | 2.59 | 3.12 |
| 128 | 10% | 1.99 | 2.70 | 3.22 | 3.93 |
| 128 | 5% | 2.44 | 3.52 | 4.21 | 5.18 |
| 128 | 2% | 3.19 | 5.23 | 6.83 | 8.49 |
| 186 (all) | 25% | 1.50 | 1.94 | 2.22 | 2.59 |
| 186 | 10% | 1.79 | 2.32 | 2.74 | 3.27 |
| 58 (confirm) | 25% | 2.07 | 3.15 | 4.15 | 5.51 |

Read it this way. A searched pattern that is active 10% of the time must **triple or quadruple** the earthquake rate to be found on the explore data, and then must show the same on 58 confirm events. The committed power table (unadjusted alpha) says 1.7 to 3.5; with the family correction the honest range is about 2.2 to 5.

For comparison, the only accepted outside influence on earthquake timing is the tide. Published tidal effects are a few percent. This study could not detect its own tidal positive control (best RR 1.06, p = 0.35). To detect a rate ratio of 1.1 on a pattern active 25% of the time takes about 3,500 events for one planned test, and about 11,800 at a search-level threshold of 10^-4. We have 186.

**Monsoon (annual).** Smallest correlation between a yearly sky feature and seasonal rainfall detectable with 80% power, two-sided, 155 seasons.

| Number of candidate rules (Bonferroni) | Detectable correlation r | Share of variance |
|---|---|---|
| 1 | 0.22 | 5% |
| 12 | 0.29 | 9% |
| 100 | 0.34 | 11% |
| 1,000 | 0.38 | 14% |
| 100,000 | 0.44 | 20% |

ENSO, the strongest known driver, correlates with Indian monsoon rainfall at about -0.3 to -0.6 depending on the period (Kumar 1999, as verified in the audit). A search over 1,000 candidates could only find a planetary effect **as strong as El Nino**. An effect that size would not have been missed by 150 years of meteorology.

The real sample is smaller than 155. Yearly sky features are slow: Jupiter completes 13 cycles in 155 years, the nodes 8, Saturn 5. Venus returns to nearly the same place on the same solar date every 8 years, so it has about 8 distinct yearly states.

**Gold (daily).** Smallest difference in mean next-day return detectable with 80% power, two-sided. Daily standard deviation is taken as 110 bp (it is about 114 bp in the committed results).

| Bars | Duty | One test | Family of 42 (BY rank-1) | Search of 1,000 | Search of 100,000 |
|---|---|---|---|---|---|
| 6,150 (2000 to 2026) | 50% | 7.9 bp | 12.6 bp | 13.7 bp | 16.5 bp |
| 6,150 | 25% | 9.1 bp | 14.5 bp | 15.9 bp | 19.0 bp |
| 6,150 | 8% (Moon in one sign) | 14.2 bp | 22.7 bp | 24.9 bp | 29.8 bp |
| 6,150 | 4% (Moon in one nakshatra) | 20.8 bp | 33.3 bp | 36.4 bp | 43.6 bp |
| 14,600 (1968 to 2026, if obtained) | 25% | 5.9 bp | 9.4 bp | 10.3 bp | 12.3 bp |

Published calendar and lunar effects on returns are a few bp a day at most. A searched pattern must move the next day's return by 15 to 40 bp to be found. An always-on edge of 10 bp a day is an annual Sharpe ratio of about 1.4. That does not exist in public view in the most traded metal on Earth.

These bar-level figures hold only for **fast** features (Moon sign, nakshatra, tithi, weekday). For slow features the unit is the episode, not the bar (ADR-004 D-6). Jupiter was in Capricorn once in the explore period. No amount of modelling fixes n = 1.

### 1.5 How long a live test would take

A live forecast is the only real proof. This is how long proof takes for a single frozen model. "Events needed" is the expected number of events before a likelihood-ratio bet against the baseline reaches 20 to 1 (see E-6).

| Domain | True effect | Data needed | Calendar time |
|---|---|---|---|
| Himalayan earthquakes (3.7 a year) | Rate x3 on 25% of the time | about 21 events | about 6 years |
| | Rate x2 | about 55 events | about 15 years |
| | Rate x1.5 | about 170 events | about 47 years |
| Global earthquakes, M 6 and above (assumed about 100 mainshocks a year; confirm from ISC-GEM) | Rate x1.5 | about 170 events | about 2 years |
| | Rate x1.2 | about 900 events | about 9 years |
| | Rate x1.1 | about 3,400 events | about 34 years |
| Monsoon (1 a year) | r = 0.5 | 24 seasons | 24 years |
| | r = 0.3 | 68 seasons | 68 years |
| Gold (250 bars a year) | 10 bp a day | t = 3 | about 4 years |
| | 4 bp a day | t = 3 | about 27 years |

### 1.6 Verdict per domain

| Domain | Can a data-driven search find anything? | Why |
|---|---|---|
| **Himalayan earthquakes** | **No.** | 186 events. A searched pattern needs a rate ratio of 2.5 to 5. Two searches already ran (atlas: 25 nominal against 35 expected by chance, Romano-Wolf p 0.84; classifier: holdout AUC 0.52, p 0.13). A live test needs 15 or more years unless the effect is enormous. |
| **Monsoon, annual** | **No.** | 155 points, slow features, detectable effect as large as ENSO. Also blocked: ADR-004 D-8 forbids any outcome-versus-indicator statistic before Stage 1 acceptance, and a search would destroy the Registered Report. |
| **Gold and silver, daily** | **Marginal. One capped search on fast features only.** | The only domain with thousands of observations. Detectable effect (15 to 40 bp a day) is far above anything credible, so the likely result is a null. Blocked until the price data are replaced (WP-12) and P1 has been re-run (WP-15). |
| **Global earthquakes, M 6 and above** | **Marginal. One capped search.** | Thousands of events, so a rate ratio near 1.2 becomes detectable, and a live test resolves in under ten years. Blocked until the registered Varuna-mandala test (ADR-004 design task D2) has run, because that test needs the global catalogue untouched. |
| **Monsoon, daily or regional** | **Not now.** | More data points, but strong space and time correlation, a known small lunar tidal effect to beat, and the D-8 firewall. Revisit after P3 Stage 2. |

**Is the correlation about zero?** For every effect size this project can measure, yes. For smaller effects the data cannot say. The honest position is: no evidence of any effect, and good evidence against the large effects that practitioners claim.

---

## 2. Why naive machine learning is guaranteed to overfit

1. **More patterns than events.** Section 1.2: 45 million skies, 186 events, every sky unique. A flexible model memorises dates.
2. **Slow features give tiny real samples.** A feature that is on for a year and off for eleven has about four independent episodes in 50 years, however many daily rows it fills. Random cross-validation puts days from the same episode in both train and test, so the model appears to predict while only recognising the episode. The gold "discovery" (Jupiter in Capricorn = the 2008 to 2009 crisis) was exactly this.
3. **Volatility and seismicity cluster.** One aftershock sequence or one crisis looks like many confirmations of whatever sky was overhead.
4. **The sky contains the calendar.** This is the main trap.

| Sky feature | What it really is | Real-world thing it tracks |
|---|---|---|
| Sun's sidereal sign | The calendar month, shifted about two weeks. Precession moves it only about 2 days in 155 years. | Monsoon season; festival gold demand (Akshaya Tritiya, Dhanteras); any seasonal effect |
| Tithi, lunar phase | The synodic month | Tides (a real, small effect on earthquakes and rain); published lunar effects on returns |
| Moon's declination, nodes | The 18.6-year lunar nodal cycle | A real tidal cycle |
| Jupiter's sign | An 11.86-year clock | The roughly 11-year solar cycle. The two drift apart by one full cycle only every 150 years or so, so inside any 30 to 50 year sample Jupiter's sign is a fair stand-in for solar-cycle phase. Decadal climate swings also live at this timescale. |
| Saturn, Jupiter-Saturn cycle | 29.5-year and 19.9-year clocks | Any slow trend or regime in a 26 to 50 year sample |
| Lagna, hora | Time of day | Network detection differences by hour; market sessions |

A model that "discovers" that the Sun in Cancer brings rain has discovered July. A model that links Jupiter's sign to drought may have found the solar cycle or one long ENSO swing. None of this is astrology working.

5. **The analyst knows history.** Planet positions are public for all time, so the usual protection of unseen data is weak. The person choosing features already knows when 2008, 2015 and 2020 happened.

**Consequence: the comparison is never against zero.** An astrological model counts only if it beats the best ordinary model that has no planets in it.

| Domain | Baseline the model must beat |
|---|---|
| Earthquakes | Space-time ETAS (clustering); below that, a constant-rate Poisson model as a sanity floor |
| Monsoon | Climatology; then a regression on ENSO and IOD state known by May; trend |
| Gold return | Random walk with drift |
| Gold volatility | GARCH(1,1) or HAR, plus calendar, festival and lunar-phase terms |
| All | Placebo skies: the same model fitted to a time-shifted sky, a tropical-zodiac sky and a sky with scrambled sign labels. The real sky must beat nearly all of them. |

---

## 3. Decision

### E-1. Build the ledger first; the search is conditional

- **Phase A (build):** scoring, baselines, model registry, forecast ledger, claims registry. Packages WP-31 to WP-41.
- **Phase B (conditional):** feature grammar v2, capped search, calibration gate. Packages WP-42 to WP-44. Starts only when Phase A is live and ADR-004 wave 5 is done.
- **Phase C (two one-shot runs):** gold and silver fast features (WP-45); global earthquakes (WP-46).
- **Phase D:** the null report and close-out (WP-47).

No general ML platform. No neural networks, no boosted trees on raw longitudes, no automated re-search.

### E-2. One model form: baseline times a small sky term

- The model is `forecast = baseline x exp(sum of b_j x f_j)`, with at most 5 features `f_j` chosen from the declared grammar. For returns the sky term is added, not multiplied.
- The sky term is re-normalised so the model predicts the same total as the baseline over each scoring period. The model can only **move probability in time**. It cannot gain by guessing the overall level.
- A fitted model is exported as a rule file (schema v2) with `tier: experimental` and `notes.origin: discovered`. It is at validation level L0. It has no source, so it can never be called "classical" or "validated".
- Reason for the limit: with a few hundred events, extra flexibility only adds noise. The existing ridge classifier on 83 features is kept as the flexible reference, and it found nothing.

### E-3. Feature grammar v2 (reuse the atlas and the workbench)

- Start from [grammar.yaml](../../studies/combinations/grammar.yaml): placements, relations, dasha, templates T1 to T7, the testability rule.
- Add **fast features only** for gold: Moon sign, nakshatra, tithi, weekday lord, Moon-planet conjunctions, and gandanta and sankranti windows.
- Add for earthquakes: the mandalas, eclipse windows, stations, Moon declination and distance (as physical controls, labelled so).
- Features are evaluated by `rules/grid.py` (`GridEvaluator`) with predicates from `rules/predicates/`. No second engine (ADR-004 WP-13).
- A feature is **eligible** only if it passes the ADR-004 D-6 testability rule: at least 8 episodes in every training fold, decided from the calendar alone.
- **Budget:** the plan (design task D4) fixes the candidate count per domain before any outcome is read. Ceiling: 2,000 eligible candidates per domain. The grammar file is hashed, as today.

### E-4. Nested walk-forward, with whole-pipeline placebo

- **Outer loop:** expanding-window folds in time order (`stats/walk_forward.py`). Fold boundaries fall between episodes, with a purge gap at least as long as the longest feature window.
- **Inner loop:** inside each training window, feature selection and the size of the sky term are chosen by a second walk-forward. Selection uses stability across inner folds: a feature must be chosen in at least 70% of them.
- **Score:** the out-of-fold skill against the baseline (E-6), summed over outer folds.
- **Inference:** the **whole pipeline**, selection included, is re-run on at least 200 placebo skies (ADR-004 WP-07). The p-value is the rank of the real sky among them. This accounts for the search without counting tests.
- **One search per domain per data vintage.** A second search needs new data (a new independent dataset, or five more years) and a new ADR.

### E-5. Three levels of holdout, named honestly

| Level | What | What it protects against | What it cannot do |
|---|---|---|---|
| 1 | Outer walk-forward folds on data already analysed here | Fitting noise inside the run | The analyst has seen this history. Called "pseudo-out-of-sample" (ADR-004 D-2). |
| 2 | **Fresh-data check, sealed by hash.** Data this repo has never loaded: for earthquakes, the global catalogue outside the Himalayan polygon; for metals, whatever series P1 has not used (decided in D4; if none, skip level 2). | Tuning to the holdout; code leaks | The world still knows the history. |
| 3 | **The live ledger.** Forecasts for dates that have not happened. | Everything | Nothing. It is slow. |

How the seal works (level 2 and level 3):

1. **Seal the forecast, not the data.** The sky is deterministic. A frozen model can print every forecast for the fresh period, and for the next ten years, **before any outcome is read**. That file is hashed. The hash is committed, tagged, and deposited (E-7).
2. The fresh outcome file is fetched by a fetch script that only downloads and hashes (ADR-004 D-5). Its SHA-256 goes into `data/snapshot_index.json` with `sealed: true`.
3. `seal.unseal(model_id)` (extends ADR-004 WP-03) is the only code path that reads a sealed file. It requires a frozen model with a deposited forecast hash, runs once per model lineage, and appends to the confirm ledger.
4. Scoring is then a plain join of two hashed files. Nothing can be tuned.

Where a baseline needs live inputs (ETAS needs recent seismicity; GARCH needs recent returns), the **sky term** is still fixed in advance. The combined forecast is issued step by step into the ledger.

### E-6. Proper scoring rules, always against the baseline

| Domain | Forecast issued | Scores | Comparison tests |
|---|---|---|---|
| Earthquakes | Expected number of mainshocks per region cell per day | Log score (information gain per earthquake over the baseline); CSEP-style number test; **Molchan diagram measured against the baseline's rate**, not against uniform time, with the area skill score (`stats/molchan.py` already has the unweighted version) | Paired information-gain test; placebo rank |
| Monsoon (after P3) | Tercile probabilities and quantiles for June to September rain, issued by 31 May | Ranked probability skill score; CRPS | Diebold-Mariano against climatology and against the ENSO/IOD model |
| Gold | Next-day probability of a rise; probability of an extreme move; 5/50/95% quantiles | Brier and log score; CRPS or quantile loss; QLIKE for volatility | Diebold-Mariano; Clark-West for nested models; Hansen SPA and model confidence set when more than one model is live |
| All | Yes/no and category claims by astrologers | Brier skill and ranked probability skill against base rates (ADR-004 WP-24) | Resampling by astrologer |

A hit rate is always shown next to the baseline's hit rate. A hit rate alone is never reported.

**The running score is a bet.** Each frozen model starts with a stake of 1. After each scored forecast the stake is multiplied by (probability the model gave the outcome) / (probability the baseline gave it). If the baseline is right, the stake reaches 20 with probability at most 5%, whenever we look. This allows checking at any time without inflating false alarms. The method is valid only when the baseline is a fair description of the no-effect world, which is why a weak baseline (plain Poisson for clustered earthquakes) is not accepted, and why the bet itself is calibrated on simulated data (WP-34).

### E-7. Model registry: frozen, hashed, timestamped

- One folder per model: `models/registry/<model_id>/` with `model.yaml` (the card), the exported rule file, and `forecasts.csv`.
- A model is **frozen** when its card, parameters and forecast file are hashed, committed on a clean tree, tagged `model/<model_id>`, and deposited: plan on OSF, release on Zenodo (ADR-004 D-3). The DOI and the deposit time are written back into the card in a second commit that changes nothing else.
- A frozen model is never edited. A change is a new `model_id` with `parent` set, and it starts its bet again at 1. Lineages count toward the limits in E-9.
- Baselines are registered and frozen the same way. So are classical rules and coded astrologer claims that enter the ledger.

### E-8. The live forecast ledger

- `forecasts/ledger.jsonl`: append-only, one forecast per line, each line carrying the hash of the line before it. Editing any old line breaks every later hash.
- Forecasts are issued on a fixed schedule (daily file for gold, weekly for earthquakes, once a year for monsoon) by one command. The ledger is committed and pushed the same day. The public push time is the timestamp.
- External anchors: each quarter the ledger head hash goes into a Zenodo release, and the public ledger URL is saved to the Internet Archive.
- Outcomes are resolved by scripts that fetch from the primary provider into hashed snapshots (ADR-004 WP-11). Scores go to `forecasts/scores.jsonl`.
- **What enters the ledger:** (a) every registered baseline; (b) frozen discovered models; (c) frozen classical rules that the owner chooses to run forward, starting with the Varuna-mandala candidate; (d) astrologers' dated, public, ex-ante claims from the claims registry, coded blind.
- The ledger runs even if Phase B is never built. It is the permanent product.

### E-9. Kill criteria

Numbers marked (D4) are fixed per domain in the plan before any outcome is read.

| Gate | When | Pass | Fail means |
|---|---|---|---|
| **K1 Calibration** | Before any real outcome is read | On simulated data with no effect (clustered events; GARCH and regime-switching returns; real calendars), the pipeline declares a discovery in at most 5% of runs, and the bet reaches 20 in at most 5% of runs | The engine is not run. Fix or stop. |
| **K2 Sensitivity** | Same time | On simulated data with a planted effect of the plan's target size (D4), the pipeline finds it in at least 80% of runs | The domain is recorded as "not testable by search with this data". No run. |
| **K3 Historical** | After the one search | Real sky ranks in the top 5% of placebo skies, **and** out-of-fold skill over the baseline is above zero | Stop the domain. Publish the null. No second search. |
| **K4 Fresh data** | One unseal | Skill over the baseline above zero, one-sided p below 0.05, same sign as in K3 | Stop the domain. Publish the null. |
| **K5 Live** | Continuous | The bet reaches 20 x (number of models live in the domain) | **Stop for futility** when the bet falls below 1/20, or at the horizon: 3 years for metals, 5 years for global earthquakes (D4). At most 2 discovered models live per domain. |
| **K6 Programme** | When every domain has stopped at K1 to K5 | n/a | Publish the null report (WP-47) within one release. Archive `core/discovery`. Keep the ledger, the baselines and the claims registry running. |

What a pass at K5 would mean: an unexplained statistical result that others should try to break. It would be reported with the baseline, the placebo ranks and all code, and with no causal language. It would not mean "astrology works".

What is never allowed: re-running a search after a fail with "improved" features; moving a horizon; replacing a baseline with a weaker one; counting a model that was not frozen before its outcomes.

---

## 4. Modules and data contracts

`core/` stands for `libs/vedic_astrology_core/`.

### 4.1 Modules

| Module | Responsibility | Reuses |
|---|---|---|
| `core/discovery/grammar.py` | Load and hash grammar v2; enumerate candidates; apply the eligibility rule | `studies/combinations/scripts/enumerate.py`, `grammar.yaml`, `stats/episodes.py` (WP-04) |
| `core/discovery/features.py` | Build the feature table on a time grid | `rules/grid.py`, `rules/predicates/`, `rules/context.py` |
| `core/discovery/search.py` | Nested walk-forward selection and fit (E-2, E-4) | `stats/walk_forward.py`, `stats/nulls.py`, `markets/placebo.py` (WP-07) |
| `core/discovery/export.py` | Write a fitted model as a rule file and a model card | `rules/schema.py`, `rules/yamlio.py` |
| `core/forecast/baselines/` | `quake.py` (Poisson, ETAS rates), `market.py` (random walk, GARCH, calendar), `rain.py` (climatology, ENSO/IOD) | WP-26, WP-05, WP-06 |
| `core/forecast/scoring.py` | Log score, CRPS, QLIKE, information gain, number test, baseline-weighted Molchan, Diebold-Mariano, Clark-West, the running bet | `stats/forecast_scoring.py` (WP-24), `stats/molchan.py` |
| `core/forecast/registry.py` | Freeze, hash and verify models and their forecast files | `stats/manifest.py`, `stats/seal.py` (WP-03) |
| `core/forecast/ledger.py` | Hash-chained append, verify, issue | `stats/manifest.py` |
| `core/forecast/resolve.py` | Match closed forecasts to outcome snapshots | `core/datasets/snapshots.py` (WP-11) |
| `core/forecast/cli.py` | `astro-forecast freeze / issue / resolve / score / verify / status` | |
| `core/claims/` | Claims registry grading and scoring (see the spec) | `tools/ingest` (WP-10), WP-24 |
| `studies/discovery/` | The plan (`plan.yaml`), run scripts, artifacts, README | Paper kit (WP-16) |

Shared-file rules from ADR-004 still hold. Only WP-18 edits `pyproject.toml`, `Makefile` and workflows; packages below name the entry points and dependencies they need. New modules are imported by full path. `_quarto.yml` is edited only by WP-33, after WP-28.

### 4.2 Data contracts

**Feature table** (`data/features/<domain>_<grammar_sha12>.parquet`, not committed; rebuilt from the hash)

| Field | Meaning |
|---|---|
| `t_utc` | Grid instant (hourly for earthquakes, the fixing instant for metals) |
| `<feature_id>` | 0/1 or a strength in 0 to 1 |
| manifest | grammar SHA-256, ephemeris model and files, ayanamsa, node model, grid, commit |

**Model card** (`models/registry/<model_id>/model.yaml`, committed)

```yaml
model_id: gold-fast-2027a            # never reused
kind: discovered | baseline | classical_rule | coded_claim
parent: null                         # model_id of the lineage it replaces
domain: gold | silver | earthquake_global | earthquake_himalaya | monsoon
target: {id: gold_next_day_up, unit: probability, schedule: daily}
baseline_id: gold-rw-garch-v1
plan: {file: studies/discovery/plan.yaml, sha256: ..., osf_doi: ...}
grammar_sha256: ...
features: [{id: ..., definition: ..., coefficient: ...}]   # at most 5
training: {window: [.., ..], snapshots: [{name: ..., sha256: ...}]}
search: {candidates: 1840, placebo_rank: 3, placebo_n: 200}
calibration_report_sha256: ...
forecast_file: {path: forecasts.csv, sha256: ..., covers: [.., ..]}
code_commit: ...
frozen_at_utc: ...
deposit: {zenodo_doi: ..., archive_url: ...}
horizon_end: 2030-12-31
```

**Ledger line** (`forecasts/ledger.jsonl`, committed)

```json
{"seq": 1042, "prev_hash": "...", "issued_at_utc": "2027-03-01T06:00:00Z",
 "model_id": "gold-fast-2027a", "model_sha256": "...",
 "target_id": "gold_next_day_up", "window": ["2027-03-02", "2027-03-02"],
 "cell": null, "forecast": {"p": 0.53}, "baseline": {"id": "gold-rw-garch-v1", "p": 0.52},
 "entry_hash": "..."}
```

**Outcome and score lines** (`forecasts/outcomes.jsonl`, `forecasts/scores.jsonl`, committed)

| File | Fields |
|---|---|
| outcomes | `target_id, window, cell, observed, snapshot_sha256, resolver_version, resolved_at_utc` |
| scores | `seq, score_type, model_score, baseline_score, skill, log_bet_increment, log_bet_total` |

Licensed price values are not written to the ledger. For metals the outcome line stores the direction and the return in bp rounded to 1 bp only if the licence register (ADR-004 WP-11) allows it; otherwise the direction and the snapshot hash.

### 4.3 How it plugs into what exists

- **Atlas and workbench:** the grammar, the enumerator, the testability rule and the predicate engine are reused as they are. The atlas stays as the published record of the first search.
- **Workbench guards (WP-23):** a discovered model exported as a rule obeys the same one-confirm-per-lineage ledger.
- **Seal (WP-03):** `unseal` is the only reader of sealed data. The engine refuses to run from a dirty tree.
- **Paper kit (WP-16):** the null report reads every number from `studies/discovery/artifacts/results.json`.
- **Site:** two pages, "Forecast ledger" and "Claims registry", built from committed JSON by `scripts/export_site_data.py`.

---

## 5. Work packages WP-31 onward

Ground rules are those of ADR-004: run only the named tests; shared files have one owner; "implementer (Sonnet)" unless a concrete subtle risk is named, then "senior-implementer (Opus)"; no subagent on Fable.

### Design tasks and owner actions

| Id | Who | Output | Needed by |
|---|---|---|---|
| D4 | Architect | `studies/discovery/plan.yaml` per domain: grammar v2 and candidate budget, baseline definition, target effect for K2, horizons, fresh-data choice | WP-43 to WP-46 |
| D5 | Architect | Claims coding manual: hedge-word probabilities, specificity anchors, base-rate definitions per claim type | WP-32 |
| H7 | Owner | OSF deposit of D4; Zenodo deposit for each frozen model and each quarterly ledger anchor | WP-38, WP-45, WP-46 |
| H8 | Owner | A public contact route and written approval of the right-of-reply and naming policy | WP-33 |
| H9 | Owner | Second coder for a 20% sample of claims (any careful reader) | WP-32 |

### Phase A: ledger, baselines, claims (build)

#### WP-31 Claims registry contract and validator
- **Goal:** the schema of CLAIMS_REGISTRY_SPEC as a machine-checked contract.
- **Files:** `tools/ingest/contracts.py` (add the `claims` contract), `tools/ingest/claims.py` (new), `tests/test_ingest_claims.py` (new), `tests/fixtures/ingest/claims/*`, `research/incoming/README.md` (add the `claims` topic).
- **Acceptance:** validates every column and enum in the spec; rejects a row marked ex-ante whose proof date is not before the window start; rejects a quote over the length limit and any media file; flags a home-page URL; refuses any hand-typed evidence grade (the grade is computed by WP-32); `--promote` writes only accepted rows to `data/registry/claims/claims.csv` and regenerates `MANIFEST.csv` hashes; no network in tests.
- **Tests:** `tests/test_ingest_claims.py`, `tests/test_ingest_validator.py`.
- **Depends on:** WP-10. **Implementer:** implementer (Sonnet).

#### WP-32 Claims grading and outcome scoring
- **Files (new):** `core/claims/__init__.py`, `core/claims/grade.py`, `core/claims/score.py`, `tests/test_claims_grade.py`, `tests/test_claims_score.py`.
- **Acceptance:** grade A to F computed exactly as the spec's rubric; outcome codes and Brier skill against base rates through WP-24; base rates use only data dated before the claim; uncodable and post-hoc claims are counted and never scored; per-source summaries appear only at 10 or more scored claims, with intervals from resampling; inter-coder agreement (Cohen's kappa) reported from the double-coded sample.
- **Tests:** the two test files; `tests/test_stats_forecast_scoring.py`.
- **Depends on:** WP-24, WP-31, D5. **Implementer:** implementer (Sonnet).

#### WP-33 Site pages and downloads
- **Files:** `site/claims.qmd`, `site/forecasts.qmd`, `site/findings.qmd` (new), `scripts/export_site_data.py`, `site/data/claims.json`, `site/data/claims.csv`, `site/data/forecast_ledger.json` (generated), `_quarto.yml` (three navbar entries), `tests/test_site_pages.py`, `tests/test_site_data.py`.
- **Acceptance:** the claims page shows a sortable table, the grade rubric, the right-of-reply notice and CSV and JSON download links; the forecasts page shows each live model, its baseline, its running bet and its horizon; the findings page renders FINDINGS_LEDGER.md; each exported file carries a `_meta` block with input hashes, as existing site data does; no page shows a per-person ranking.
- **Tests:** the two test files.
- **Depends on:** WP-31, WP-32, WP-39, H8; after WP-28 (`_quarto.yml` order). **Implementer:** implementer (Sonnet).

#### WP-34 Forecast scoring extensions
- **Files (new):** `core/forecast/__init__.py`, `core/forecast/scoring.py`, `tests/test_forecast_scoring.py`.
- **Acceptance:** log score, CRPS (closed form for a normal, and from quantiles), quantile loss, QLIKE; information gain per event; number test; Molchan trajectory and area skill score with time measured in baseline probability, equal to the existing unweighted version when the baseline is constant; Diebold-Mariano with the small-sample correction; Clark-West; the running bet with its 20-to-1 rule; on simulated no-effect data each test rejects at most 5% of the time (plus three binomial standard errors) and the bet reaches 20 in at most 5% of runs; a deliberately weak baseline is pinned as a failing case with the reason.
- **Tests:** `tests/test_forecast_scoring.py`, `tests/test_stats_molchan.py`.
- **Depends on:** WP-24, WP-02 (simulators). **Implementer:** senior-implementer (Opus). Risk: an improper or mis-normalised score rewards hedging or level-guessing; a miscalibrated bet gives false wins.

#### WP-35 Earthquake baselines
- **Files (new):** `core/forecast/baselines/__init__.py`, `core/forecast/baselines/quake.py`, `tests/test_baseline_quake.py`.
- **Acceptance:** constant-rate Poisson forecast per cell; ETAS conditional daily rates from parameters fitted only on data before the forecast date (refit on a fixed schedule); on a simulated ETAS catalogue the ETAS baseline beats Poisson by log score and the Poisson baseline is shown to give false wins to a clustering-only model; changing data after date t changes no forecast up to t.
- **Tests:** `tests/test_baseline_quake.py`, `tests/test_earthquake_decluster.py`.
- **Depends on:** WP-26, WP-34. **Implementer:** senior-implementer (Opus). Risk: look-ahead in the refit; unstable ETAS fits passing silently.

#### WP-36 Market baselines
- **Files (new):** `core/forecast/baselines/market.py`, `tests/test_baseline_market.py`.
- **Acceptance:** random walk with drift (past-only mean); GARCH(1,1) one-step density with past-only parameters; optional calendar, festival and lunar-phase terms from WP-06; emits the three gold targets of E-6; no value uses data after the issue time (tested).
- **Tests:** `tests/test_baseline_market.py`, `tests/test_stats_volatility.py`.
- **Depends on:** WP-05, WP-06, WP-34. **Implementer:** implementer (Sonnet).

#### WP-37 Monsoon baselines, simulated data only
- **Files (new):** `core/forecast/baselines/rain.py`, `tests/test_baseline_rain.py`.
- **Acceptance:** climatological tercile and quantile forecast from a trailing window; regression on ENSO and IOD indices known by 31 May; runs on the WP-29 simulator; **raises if given a real outcome file** while the flood plan lacks its Stage 1 acceptance record (ADR-004 D-8), tested.
- **Tests:** `tests/test_baseline_rain.py`, `tests/test_flood_pipeline.py`.
- **Depends on:** WP-29, WP-34. **Implementer:** implementer (Sonnet).

#### WP-38 Model registry and forecast seal
- **Files:** `core/forecast/registry.py` (new), `core/stats/seal.py` (add `unseal` and the `sealed` snapshot flag), `models/registry/README.md` (new), `tests/test_forecast_registry.py` (new), `tests/test_stats_seal.py`.
- **Acceptance:** `freeze` refuses a dirty tree, writes the card and the forecast-file hash, and is idempotent; any later byte change to card, rule or forecast file fails `verify`; `unseal` refuses without a frozen model whose deposit field is filled, runs once per lineage, and logs to the confirm ledger; no other module can open a snapshot flagged `sealed` (tested by attempting it); a version bump, a deleted ledger file or an environment flag does not bypass the seal.
- **Tests:** the two test files (temporary git repositories).
- **Depends on:** WP-03, WP-11. **Implementer:** senior-implementer (Opus). Risk: holdout leakage through a bypass.

#### WP-39 Forecast ledger and CLI
- **Files (new):** `core/forecast/ledger.py`, `core/forecast/cli.py`, `forecasts/README.md`, `forecasts/ledger.jsonl` (empty, with the genesis line), `tests/test_forecast_ledger.py`, `tests/test_forecast_cli.py`. Entry point `astro-forecast` is named for WP-18 to add.
- **Acceptance:** append computes `entry_hash` over the canonical JSON plus `prev_hash`; `verify` detects any edited, removed or reordered line; `issue` refuses a model that is not frozen, a window that has already started, and a duplicate (model, target, window); issue time comes from the system clock in UTC and is checked against the window; the baseline's forecast is written in the same line.
- **Tests:** the two test files.
- **Depends on:** WP-34, WP-38. **Implementer:** implementer (Sonnet).

#### WP-40 Outcome resolvers and scoring job
- **Files (new):** `core/forecast/resolve.py`, `scripts/forecast_resolve.py`, `tests/test_forecast_resolve.py`.
- **Acceptance:** resolves only windows that have closed, plus a per-source settling delay (catalogues are revised); reads outcomes only from snapshots listed in the snapshot index; writes outcome and score lines; re-running is idempotent; a revised catalogue produces a new dated outcome line and never rewrites an old one.
- **Tests:** `tests/test_forecast_resolve.py`, `tests/test_snapshots_index.py`.
- **Depends on:** WP-11, WP-25 (earthquakes), WP-12 (metals), WP-39. **Implementer:** implementer (Sonnet).

#### WP-41 Kill monitor and status export
- **Files (new):** `scripts/forecast_status.py`, `forecasts/status.json` (generated), `tests/test_forecast_status.py`.
- **Acceptance:** per live model: forecasts issued, resolved, running bet, threshold, horizon, and one of `live`, `won`, `stopped_futility`, `stopped_horizon`; thresholds scale with the number of live models in the domain (E-9); a stopped model cannot be issued again (checked through WP-39).
- **Tests:** `tests/test_forecast_status.py`.
- **Depends on:** WP-39, WP-40. **Implementer:** implementer (Sonnet).

**Gate A (owner):** baselines frozen and issuing; the Varuna-mandala candidate and all proven ex-ante practitioner claims entered; the ledger verified and anchored once. Phase B may start only after this and ADR-004 wave 5.

### Phase B: the capped search (conditional)

#### WP-42 Feature grammar v2 and feature table
- **Files (new):** `core/discovery/__init__.py`, `core/discovery/grammar.py`, `core/discovery/features.py`, `studies/discovery/grammar_v2.yaml` (from D4), `tests/test_discovery_grammar.py`, `tests/test_discovery_features.py`.
- **Acceptance:** enumeration is deterministic and its count equals the plan's; the v1 grammar reproduces the atlas's 4,977 candidates; eligibility uses the calendar only and never an outcome (the function takes no outcome argument); features come from `GridEvaluator`; the table's manifest carries the grammar hash and ephemeris settings; the budget ceiling raises when exceeded.
- **Tests:** the two test files, `tests/test_atlas_enumerate.py`.
- **Depends on:** WP-04, WP-13, D4. **Implementer:** implementer (Sonnet).

#### WP-43 Nested walk-forward search
- **Files (new):** `core/discovery/search.py`, `core/discovery/export.py`, `tests/test_discovery_search.py`, `tests/test_discovery_export.py`.
- **Acceptance:** outer and inner loops as E-4, with episode-aligned fold edges and a purge gap; at most 5 features; totals re-normalised to the baseline per scoring period; the whole pipeline runs unchanged on a placebo sky and returns the real sky's rank; a test proves no outer-test row influences selection (perturbing test-fold outcomes changes no selected feature); each placebo and fold draws from its own named random stream; the exported rule passes `astro-rules validate` and carries `notes.origin: discovered`.
- **Tests:** the two test files, `tests/test_stats_walk_forward.py`.
- **Depends on:** WP-07, WP-34, WP-42. **Implementer:** senior-implementer (Opus). Risk: selection leakage across folds; episode straddling; placebo runs that skip the selection step.

#### WP-44 Engine calibration gate (K1, K2)
- **Files (new):** `tests/test_discovery_calibration.py`, `studies/discovery/scripts/calibrate.py`, `studies/discovery/artifacts/calibration.json` (generated). Extends `tests/simulators.py` (WP-02) with a planted-effect option.
- **Acceptance:** with no effect, across at least 200 simulated datasets per domain, the K3 rule passes in at most 5% (plus three binomial standard errors); with a planted effect of the D4 target size, in at least 80%; the report states the smallest planted effect found 80% of the time; the simulators include clustering, regimes and the real feature calendars; a fast seeded subset runs in CI and the full run is marked slow.
- **Tests:** `tests/test_discovery_calibration.py`.
- **Depends on:** WP-02, WP-35, WP-36, WP-43. **Implementer:** senior-implementer (Opus). Risk: a kind simulator certifies a broken engine.

### Phase C: two one-shot runs

#### WP-45 Run: gold and silver, fast features
- **Files:** `studies/discovery/scripts/run_metals.py` (new), `studies/discovery/artifacts/metals/` (generated), `models/registry/<id>/` (if K3 passes), `studies/discovery/README.md`.
- **Acceptance:** runs from a clean tree against the deposited D4 plan; K1 and K2 reports present and hashed; one search; results state the K3 outcome in the words of E-9; if K3 passes: model frozen and deposited before `unseal` (K4), then first ledger issue; if K3 fails: nothing is frozen and the null is written; in both cases every candidate's out-of-fold score is published.
- **Tests:** `tests/test_discovery_search.py`, `tests/test_forecast_registry.py`.
- **Depends on:** WP-12, WP-15 (P1 re-run finished first), WP-36, WP-38, WP-44, D4, H7. **Implementer:** senior-implementer (Opus). Risk: the single allowed run; any mistake burns the data vintage.

#### WP-46 Run: global earthquakes
- **Files:** `studies/discovery/scripts/run_quakes.py` (new), `studies/discovery/artifacts/quakes/` (generated), `models/registry/<id>/` (if K3 passes).
- **Acceptance:** as WP-45; trains on the Himalayan catalogue already analysed; the global catalogue outside the polygon is the sealed fresh data; **refuses to start unless the registered Varuna-mandala test (D2) has a confirm-ledger entry**; ETAS baseline; three declustering settings reported.
- **Tests:** `tests/test_discovery_search.py`, `tests/test_baseline_quake.py`.
- **Depends on:** WP-25, WP-27 (and D2 executed), WP-35, WP-38, WP-44, D4, H7. **Implementer:** senior-implementer (Opus). Risk: burning the global catalogue before the registered test; sealed-data order.

### Phase D: close-out

#### WP-47 Null report and programme close-out
- **Files:** `studies/discovery/paper/discovery_null.qmd`, `numbers_allowlist.txt` (new), `papers/targets.yaml` (one entry), `studies/discovery/README.md`.
- **Acceptance:** reads every number through the paper kit; passes the key gate; reports the feasibility table, K1 to K5 outcomes per domain, the placebo ranks and the detectable effects; states "no evidence of an effect at or above X" and never "no effect"; if K6 is reached, marks `core/discovery` as archived in its README.
- **Tests:** `tools/check_paper_keys.py` on the paper, `tests/test_site_pages.py`.
- **Depends on:** WP-16, WP-17, WP-45, WP-46. **Implementer:** implementer (Sonnet).

### Order

| Wave | Packages | Earliest ADR-004 wave it can join |
|---|---|---|
| A1 | WP-31, WP-34 | wave 2 (needs WP-10, WP-24, WP-02) |
| A2 | WP-32, WP-35, WP-36, WP-37, WP-38 | wave 3 |
| A3 | WP-39, then WP-40, WP-41 | wave 4 |
| A4 | WP-33 | after wave 6 (WP-28) |
| Gate A | owner | |
| B1 | WP-42 | after wave 5 |
| B2 | WP-43, then WP-44 | |
| C | WP-45 and WP-46 (no shared files except the README; WP-45 writes it first) | after WP-15, WP-27 and D2 |
| D | WP-47 | |

---

## Consequences

Good:

- The owner gets a straight answer to "can we find our own pattern": one fair attempt per testable domain, with the result decided by rules written first.
- The ledger outlives the search. In five years it will hold the only dated, scored record of planetary forecasts and astrologers' claims against real baselines.
- A false discovery cannot be published by accident: it must beat placebo skies, a sealed check and a live bet.

Costs and risks:

- Seventeen more packages for one developer. Phase A is ten of them and is useful alone.
- The most likely output is another null. That is the honest expectation, stated before any work.
- The live test is slow: years, not weeks.
- Owner actions are needed for every freeze (deposit) and each quarter (anchor).
- The global earthquake count, CSEP test details and several citations are from memory. Check them at source before use, under the same rule as `research/incoming/`: Gneiting and Raftery 2007 (proper scoring rules); Zechar and Jordan 2008 (Molchan against a reference model); Rhoades et al. 2011 (information-gain tests); Meinshausen and Buhlmann 2010 (stability selection); Diebold and Mariano 1995; Clark and West 2007; Patton 2011 (QLIKE); Shafer 2021 and Ramdas et al. 2023 (betting scores and e-values).

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| A general ML platform (boosted trees, neural nets) over all planetary features | Section 1.2: guaranteed false patterns; nothing to learn from 186 events or 155 seasons |
| Search on Himalayan earthquakes again with a richer grammar | Detectable rate ratio only grows (2.6 to 5); the atlas and classifier already ran |
| Search on annual monsoon rainfall | 155 points; breaks the D-8 firewall and the Registered Report |
| Compare against zero or against shuffled days | Rewards the calendar and clustering; the review's flaws M1, M3 and M4 again |
| Plain Poisson as the earthquake baseline | A clustering-aware model beats it with no information from the sky |
| A historical holdout presented as proof | The analyst and the world know the history; only future data is unseen |
| Re-search after a failed gate | This is the forking path the atlas was built to end |
| Fixed-date significance tests on the live ledger | Tempts repeated peeking; the running bet is valid at any look |
| Skip the search and build nothing | Leaves "we never tried our own model" unanswered, and leaves no tool to score the next claim |
| Encrypting the sealed data | Overkill for one developer; a pre-committed forecast hash gives the same guarantee with less machinery |
