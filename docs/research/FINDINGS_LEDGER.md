# Findings ledger

Everything this project has found so far, in plain words. One row per test family. Each row says what was tested, on how much data, what came out, how big an effect the test could have seen, whether the result still stands, and which file holds it.

- Written: 2026-11-22. Numbers were read from the committed `results.json` files on that date.
- Companion documents: [ADR-005](../adr/ADR-005-pattern-discovery-and-claims-registry.md) (can we build our own model), [CLAIMS_REGISTRY_SPEC.md](CLAIMS_REGISTRY_SPEC.md) (astrologer claims), [RESEARCH_REVIEW_2026-11-22.md](../../RESEARCH_REVIEW_2026-11-22.md) (flaw codes C1 to C6, M1 to M13), [CORRECTIONS.md](../../CORRECTIONS.md).
- Rule for this file: a number appears here only if it is in an artifact or in the review. When an artifact is re-run, update the row and its status. Do not delete old rows; mark them superseded.

## 1. The short version

1. We ran **815 planned tests** across four studies (26 earthquake, 705 combination atlas, 42 gold, 42 silver). **None is a confirmed finding.**
2. That is what "nothing there" looks like. With 815 tests and nothing real, luck alone gives about 41 results below p = 0.05. We saw 29.
3. It is **not proof that astrology has no effect.** The tests could only see large effects: an earthquake rate about 2 to 5 times normal, or a gold move of 15 to 45 basis points a day. Smaller effects would have been missed.
4. For most earthquake indicators the data do argue against a **doubling** of the rate. Large effects of the kind practitioners describe are unlikely. Small ones are untested.
5. Three caveats on the count itself: the gold artifact is stale (it still shows one "discovery" that the corrected test removes); the atlas's main correction could never have passed anything; and none of the plans was registered before the data were seen. Details in section 5.
6. One loose end is worth a single, properly registered test: earthquakes when the Moon is in a Varuna-mandala nakshatra (section 7).
7. Of 137 astrologer forecasts collected so far, the collector marked **8** as proven to predate the event. Our own audit has confirmed **4** of them; 2 more need a manual read; the other 2 cannot be scored. Of 36 large Himalayan-region earthquakes since 1897, **none** has a proven advance prediction (section 8).

## 2. What "0 of about 800" means

### 2.1 The lottery picture

A test at the usual 5% level is a lottery ticket that wins 1 time in 20 when nothing is going on. Buy 815 tickets and you expect about 41 wins from luck.

| Study | Tests | Expected below p = 0.05 by luck | Seen below p = 0.05 | Pass after correction |
|---|---|---|---|---|
| Earthquake, registered family | 26 | 1.3 | 2 | 0 |
| Combination atlas | 705 | 35.3 | 25 | 0 |
| Gold, explore period | 42 | 2.1 | 1 | 1 in the artifact; **0** with the corrected test |
| Silver, explore period | 42 | 2.1 | 1 | 0 |
| **Total** | **815** | **40.8** | **29** | **0** |

We saw fewer lucky wins than expected. That is normal here: many tests are one-sided or have small counts, which makes them cautious.

### 2.2 Why we correct for the number of tests

If you look at 815 things and report the best one, the best one will always look good. The correction (Benjamini-Yekutieli) raises the bar so that, among everything we call a finding, at most about 5% are flukes. With 705 tests the bar for the single best result is about p = 0.00001, not 0.05.

The atlas shows this clearly. Its best candidate ("Moon in house 5 from the lagna at Kathmandu") had p = 0.005. Once the search over 705 candidates is accounted for, that becomes p = 0.84. In other words, 84 searches out of 100 on pure noise would produce a "best pattern" at least that good.

### 2.3 Why a null is not a disproof

A test that finds nothing has two possible reasons: nothing is there, or the test was too weak to see it. So every null must come with the smallest effect the test could have seen.

| Study | Smallest effect the test could detect (80% power) | In plain words |
|---|---|---|
| Earthquake, single indicators | Rate ratio 1.7 to 3.5 as published (no correction for 26 tests); about 2.2 to 5 with it | The rate must roughly double to quintuple while the indicator is on |
| Earthquake, confirm period (58 events) | Rate ratio 2.2 to 5.5 as published | Worse |
| Earthquake, tidal control | Rate ratio 1.40 to 1.50; published tidal effects are a few percent | The study could not see the one outside effect known to be real |
| Atlas combinations | Not tabulated. About 2.6 to 4 for a combination active 5 to 25% of the time (ADR-005 section 1.4) | Rarer combinations need far more |
| Gold, explore period | 11 to 30 bp a day on returns; 13 to 45 bp on absolute returns; 3 to 6 points on a 5% extreme-move rate. About 1.6 times larger after correction for 42 tests. | A quarter to a half of a typical daily move. Published calendar effects are a few bp. |
| Silver | Similar or worse (thinner data) | |

**Bayes factors near 1** say the same thing from another side. A Bayes factor compares how well "there is an effect" and "there is none" explain the data. For the earthquake tests, under a sceptical prior all 52 lie between 0.89 and 1.65 (median 1.00). The data barely move belief in either direction.

### 2.4 What can be said, and what cannot

| Statement | Supported? |
|---|---|
| "No tested indicator showed a confirmed effect." | Yes |
| "The results look like chance." | Yes |
| "For 8 of 13 earthquake indicators, a doubling of the rate is outside the 95% interval." | Yes (explore period, Gardner-Knopoff; upper limits 1.11 to 1.90) |
| "For Mars, Venus, Jupiter and Saturn stations, even a doubling is not excluded." | Yes (upper limits 2.76 to 4.53; too few events) |
| "Planets have no effect on earthquakes or gold." | **No.** Small effects were not testable. |
| "Astrology is disproved." | **No.** Fourteen to twenty-six indicators per study are not the whole of astrology. |
| "Markets are efficient with respect to planets." | **No.** Review C5. |
| "These were pre-registered tests." | **No.** The plans were committed with the first run, not before it (review C2). Call them fixed analysis plans. |

## 3. Ledger by study

Status words: **stands** (valid as reported), **stands with limits** (valid, known weaknesses, re-run planned), **needs re-run** (the artifact is wrong or stale), **not informative** (could not have come out otherwise), **not run**, **withdrawn**.

### 3.1 Earthquake, Himalayan arc

Source: [studies/earthquake/artifacts/results.json](../../studies/earthquake/artifacts/results.json); plan [hypothesis.yaml](../../studies/earthquake/hypothesis.yaml). Catalogue: USGS ComCat, 1976 to 2026, Mw 5.2 and above, 297 events; 186 mainshocks after Gardner-Knopoff declustering (128 explore to 2010, 58 confirm from 2011), 214 after nearest-neighbour declustering (144, 70). Run from commit 6c2c9c3 on a dirty tree; Moshier ephemeris; Lahiri; mean node.

| Family | What was tested | n | Result | Detectable effect | Status |
|---|---|---|---|---|---|
| Registered family | 13 indicators (Mars-Saturn and Mars-Ketu conjunctions, eclipse window, Sun ingress, five planetary stations, four Moon mandalas) x 2 declustering methods = 26 rate-ratio tests, explore period | 128 and 144 events | **0 of 26** pass the correction (every q = 1). 2 below p = 0.05, both the Varuna mandala (RR 1.55, p = 0.037; RR 1.52, p = 0.038). | RR 1.7 to 3.5 uncorrected | Stands with limits. Re-run planned (ADR-004 WP-25 to WP-27): single catalogue, declustering leaves the 2015 Mw 7.3 in, power not corrected for 26 tests. |
| Confirmation period | The same 26 on 2011 to 2026. Nothing was carried, so this is descriptive. | 58 and 70 events | 0 confirmed. 1 below 0.05: Varuna mandala, RR 1.89, p = 0.010 (Gardner-Knopoff); RR 1.50, p = 0.098 (nearest-neighbour). | RR 2.2 to 5.5 | Stands as description |
| Undeclustered catalogue | 13 indicators x 3 periods = 39, descriptive | 297 events | 2 below 0.05, both Varuna (RR 1.54 and 1.59) | n/a | Stands as description |
| Positive control (tide) | 3 tidal-phase indicators x 3 catalogues x 3 periods = 27 | up to 297 | **Not detected.** Best RR 1.06, p = 0.35. 0 of 27 below 0.05. | RR 1.40 to 1.50 | Stands. It shows the method cannot see effects of tidal size. Added after the first run. |
| Negative control | The 26 tests on a sky shifted by 3,001 days | as family | 0 below 0.05 (1.3 expected); smallest p = 0.14 | n/a | Stands with limits (one shift only; a distribution of shifts is planned) |
| Rule-free classifier | Ridge logistic model on 83 daily sky features | 127 event days explore, 57 confirm | Explore AUC 0.517, p = 0.11. Frozen holdout AUC 0.520, p = 0.13. (0.5 is a coin toss.) | n/a | Stands. This is already "our own model". It found nothing. |
| Monthly count model | Negative-binomial regression, 9 sky terms against none | 610 months, 186 events | Likelihood ratio 9.70 on 9 df, p = 0.375. Leave-one-year-out fit is worse with the sky terms (-4.83). | n/a | Stands |
| Forecast check (SPA) | 13 indicators as daily forecasts on the confirm period against a constant rate | 5,783 days | p = 0.080. No indicator beats a constant rate. | n/a | Stands |
| Molchan diagram | Alarm skill, all indicators combined | 186 and 214 | Area skill 0.474 and 0.472 against 0.50 for random (p = 0.91 and 0.95) | n/a | Stands |
| Molchan, single points | 13 indicators x 2, binomial test, whole period, **not corrected and not registered** | 186 and 214 | Varuna mandala: 37% of events in 26% of the time, p = 0.0009 and 0.003 | n/a | Description only. See section 7. |
| Bayes factors | 26 explore + 26 confirm, two priors | as family | Sceptical prior: 0.89 to 1.65. Enthusiastic prior: 0.37 to 3.73; highest is Varuna (3.6 to 3.7). | n/a | Stands. "The catalogue cannot decide." |
| Workbench rule | `rules/seismic/mangal_ketu_primary.yaml` v2: orb tuned over 18 values on explore, then one confirm | 128, then 58 | Explore RR 1.09, p = 0.46. Confirm RR 0.99, p = 0.60: **not confirmed.** | n/a | Stands with limits (family size counted as 1; review C6) |

### 3.2 Combination atlas (earthquake)

Source: [studies/combinations/artifacts/results.json](../../studies/combinations/artifacts/results.json), full table in `atlas.csv`; search space [grammar.yaml](../../studies/combinations/grammar.yaml). Same catalogue and explore period (128 mainshocks). 2,000 shift draws.

| Family | What was tested | n | Result | Status |
|---|---|---|---|---|
| Declared search | 4,977 combinations of placement, aspect or conjunction, and dasha (up to 3 clauses). 705 had enough expected events to test. | 128 events | 25 below p = 0.05 against 35 expected by luck | Stands |
| Correction (BY) | All 705 | | 0 pass | **Not informative.** With 2,000 draws the smallest possible p was 1/2001 = 0.0005. The bar for 705 tests is about 0.00001. Nothing could have passed (review C1). Re-run with far more draws, or drop this line. |
| Best candidate (Romano-Wolf) | "Moon in house 5 from the lagna at Kathmandu" | | RR 1.80 (1.03 to 2.98), p = 0.005; adjusted for the search, p = 0.84 | Stands. This is the valid family-wide answer. |
| Forecast check (SPA) | The 20 best explore candidates as forecasts on 2011 to 2026 | 5,783 days, 58 events | p = 0.91 | Stands |
| Gold atlas | Declared in the grammar | | | Not run |

By template: single placements 393 tested, 16 nominal; single relations 99, 7; dasha 13, 1; two-clause and three-clause templates 200 tested, 1 nominal. Most deeper combinations (4,272 of 4,977 candidates overall) were too rare to test at all.

### 3.3 Gold

Source: [studies/gold_market/artifacts/results.json](../../studies/gold_market/artifacts/results.json), generated 2026-11-08 from commit 370edd9 on a dirty tree. Data: Yahoo `GC=F` futures, 6,150 bars, 2000-09-05 to 2026-10-30. Explore to 2015 (3,462 bars), confirm from 2016 (2,687 bars).

**This artifact is stale.** It predates the fix to the shift test (commit eccc082, 2026-11-22) and has not been regenerated. The price series is also not fit for a daily-return study (review C4).

| Family | What was tested | n | Result in the artifact | Corrected reading | Status |
|---|---|---|---|---|---|
| Registered family | 14 indicators x 3 outcomes (return, absolute return, extreme move) = 42, explore period | 3,462 bars (3,212 for extremes) | 1 passes: Jupiter in Capricorn, absolute return +29.8 bp, p = 0.0001, q = 0.018. Verdict `not_replicated`. | The p-value was not attainable. Exact p = 0.000375, q = 0.068. **0 pass.** Jupiter was in Capricorn once in the period, during the 2008 to 2009 crisis: one episode (review 2.5). | **Needs re-run** (ADR-004 WP-12, WP-14, WP-15) |
| Confirmation | The one carried test | 2,687 bars | +8.8 bp, p = 0.73: not replicated | Moot | Needs re-run |
| Confirm period, all 42 (descriptive) | | 2,687 bars | 3 below 0.05. One at the floor: Jupiter in Cancer, absolute return, p = 0.0001, q = 0.018. | Exact p = 0.00053, q = 0.096. One episode (the 2025 to 2026 rally). | Needs re-run |
| Full period, all 42 (descriptive) | | 6,149 bars | 0 below 0.05 (smallest p = 0.064) | | Needs re-run |
| Station event study | Forward returns over 5, 21 and 63 bars after a station retrograde, 5 planets = 15 tests | 12 to 82 events | 0 pass. 1 below 0.05 (Venus, 63 bars, p = 0.025, 16 events). | | Needs re-run |
| Longitude regression ("Granger") | 4 planets x 2 outcomes = 8 | about 6,100 bars | 0 pass. Nearest: Saturn on volatility, p = 0.0024, q = 0.053. | A slow-trend regression on less than one Saturn cycle (review M4) | Needs re-run |
| Trading-rule check (SPA) | 14 indicators as one-day rules on the confirm period | 2,687 bars | p = 0.53 | The benchmark is mis-specified (review M3) | Needs re-run |

Detectable effect, explore period, from [the study README](../../studies/gold_market/README.md): 11 to 30 bp a day (return), 13 to 45 bp (absolute return), 3 to 6 points (extreme-move rate), all before correction for 42 tests.

### 3.4 Silver

Source: [studies/silver_market/artifacts/results.json](../../studies/silver_market/artifacts/results.json), same date, commit and pipeline. Data: Yahoo `SI=F`, 5,824 bars from 2000-08-30. Median volume 53 contracts (review).

| Family | What was tested | n | Result | Status |
|---|---|---|---|---|
| Registered family | 14 indicators (including purnima and amavasya) x 3 outcomes = 42, explore | 3,258 bars | **0 pass.** 1 below 0.05: amavasya, return +47 bp, p = 0.034. Verdict `null`. | Needs re-run for data quality. No test sat at the p-value floor, so the shift-test fix does not change the headline. |
| Confirm period (descriptive) | 42 | 2,565 bars | 2 below 0.05 (both Venus combust) | Needs re-run |
| Full period (descriptive) | 42 | 5,823 bars | 0 below 0.05 (smallest 0.061) | Needs re-run |
| Station event study | 15 | 12 to 80 events | 0 pass; 1 below 0.05 (Venus, 63 bars, p = 0.043) | Needs re-run |
| Longitude regression | 8 | | 0 pass; nearest Jupiter on volatility, p = 0.015, q = 0.32 | Needs re-run |
| Trading-rule check (SPA) | 14 rules | 2,565 bars | p = 0.90 | Needs re-run |

### 3.5 Numerology against the Moon's nakshatra lord

Source: [studies/numerology_vs_astrology/artifacts/results.json](../../studies/numerology_vs_astrology/artifacts/results.json). 1,827 days, 2020 to 2024.

| Family | What was tested | Result | Status |
|---|---|---|---|
| Agreement (H1) | Does the day's numerology planet agree with the lord of the Moon's nakshatra more than chance? Equivalence test, margin 0.05. | Kappa = -0.012 (90% interval -0.028 to 0.003), p = 0.00003: **no agreement beyond chance**, shown positively. | Stands, but trivial: two calendars with unrelated periods (364 and 350 changes a year). Parked as a note, not a paper (ADR-004 WP-30). |
| Per planet (H2) | 9 correlations between "numerology planet of the day" and that planet's dignity score, margin 0.10 | All 9 within the margin (largest \|r\| = 0.003) | Needs re-run: computed before the moolatrikona correction of 2026-11-09 |

This is the only place where the project shows **absence** of a relation, not just failure to find one. It is also the least interesting question.

### 3.6 Not run, not research, withdrawn

| Item | State | File |
|---|---|---|
| Mundane (national charts) | **Not run.** 113 countries, 3,445 feature rows, 40 events. 0 of 113 countries have a sourced founding time. Statistics are not wired. | [summary.json](../../studies/mundane/artifacts/summary.json) |
| Remedy conflict matrix | Not research. No data, no artifacts. | `studies/remedy_conflict_matrix/` |
| Rule catalogue | 121 rule files: 2 classical tier, 119 experimental; 59 active, 47 waiting for predicates. 120 unvalidated, 1 not confirmed (3.1). | `rules/` |
| Earthquake "predicted vs actual", "Monte Carlo delta-AIC" | **Withdrawn 2026-11-08.** Drawn from random numbers. | [CORRECTIONS.md](../../CORRECTIONS.md) (a) |
| Old gold Granger, Molchan, permutation, periodogram | **Withdrawn.** Computed on a synthetic placeholder series. | CORRECTIONS (b) |
| Every result before 2026-11-08 | **Withdrawn.** Positions were tropical, not sidereal; Ketu was computed as Rahu. | CORRECTIONS (c) |
| "DE440, sub-arcsecond" claim | **Withdrawn.** The Moshier fallback was in use. | CORRECTIONS (d) |
| The 2,426-combination gold catalogue | **Withdrawn.** No declared family, null or holdout. Replaced by the atlas. | [combinations README](../../studies/combinations/README.md) |
| Cross-study papers under `papers/`, `rigor_audit.qmd`, the remedy notes | **Withdrawn from the site 2026-11-22.** They print retracted numbers. | CORRECTIONS, first entry |

## 4. Count of everything tested

| Group | p-values or decisions |
|---|---|
| Planned families (the "815") | 26 + 705 + 42 + 42 |
| Earthquake, outside the family | 26 confirm, 39 undeclustered, 27 tidal, 26 shifted-sky, 26 Molchan points, 2 classifier, 1 count model, 1 SPA, 2 Molchan combined |
| Gold and silver, outside the family | 84 + 84 (confirm and full periods), 15 + 15 events, 8 + 8 regressions, 1 + 1 SPA |
| Atlas, extra | 1 Romano-Wolf, 1 SPA |
| Workbench | 18 tuning cells and 1 confirm for one rule; one tuning run for a second |
| Numerology | 10 equivalence tests |
| **About** | **1,200 in all** |

No correction spans the studies. A project-wide count is planned (ADR-004 WP-08, `studies/project_multiplicity.json`).

## 5. Known problems that change how to read the numbers

| Problem | Effect on the ledger | Fix |
|---|---|---|
| Shift-test p-values below the attainable minimum (C1) | Created the one gold "discovery" | Code fixed (eccc082). **Gold, silver and atlas artifacts not yet regenerated.** |
| Atlas BY line could not pass (C1) | "0 survived BY" carries no information | More draws, or rely on Romano-Wolf |
| Plans were not registered before the data (C2) | "Pre-registered" is the wrong word everywhere. Every `results.json` has `dirty: true`. | ADR-004 D-2, WP-03, OSF deposit |
| Stale public wording | `site/data/results.json` and study READMEs still say "Pre-registered" and "1 of 42 exploration tests pass" for gold | Regenerate after the re-run (WP-15); wording by WP-01 |
| Gold and silver price data (C4) | Sparse before 2008; illiquid contract; rolls not adjusted | WP-12 |
| Slow indicators have 1 or 2 episodes (M1, M2) | Bar counts overstate the evidence; several indicators are untestable | WP-04, ADR-004 D-6 |
| No baselines (M4, M5) | Sun-sign indicators are calendar months; no macro controls | WP-06, WP-07 |
| Power stated without correction (M6) | Detectable effects are larger than printed | WP-08 |
| Earthquake catalogue and declustering (M7) | 1,563 of 1,645 magnitudes are converted from mb; the 2015 Mw 7.3 is kept as a mainshock | WP-25, WP-26 |
| Ephemeris label differs between studies (M10) | Gold says "swieph", the others "moshier", on one machine | State one model in every manifest |
| The text does not say what the earthquake study tests | Brihat Samhita ch. 32 reads the mandala **after** an earthquake to judge its consequences. The study uses it as a forward trigger. | Say so in the paper; astrologer review (L4) |

## 6. Where the evidence about sources stands

All outside evidence is kept unedited in [research/incoming/](../../research/incoming/README.md) with a SHA-256 for every file in `MANIFEST.csv` (124 files). It was collected by an AI research agent (Gemini) in two rounds and audited independently: [INCOMING_AUDIT_2026-11-22.md](handover/INCOMING_AUDIT_2026-11-22.md). Nothing in it has been promoted to a study or a rule yet.

### 6.1 Credibility by kind of source

| Kind of source | What we found | Usable today? |
|---|---|---|
| **Classical text, Brihat Samhita** | Ch. 32 mandala lists match the code. 7 of 21 gold rules are tied to pages of Bhat's 1981 edition (ch. 8 v. 5; ch. 41 vv. 2, 7, 11, 12; ch. 42 vv. 6, 14). | As leads. Check each page against the scan before use (level L1 to L2). |
| **Classical text check against the owner's books, round 5 (2026-11-23)** | Machine-located, not yet checked by a person (research/incoming/texts/round5_local_books/). BPHS (Santhanam, local scan): 14 close. Brihat Samhita (Bhat 1981, archive.org text, not a local copy): 13 close, 5 not found (seismic.mangal_ketu_primary and _fire_sign cite BS 17, which has no Mars-Ketu or earthquake passage; core.r002, r011, r016 cite registry chapters, the passages are BS 16, 12.22 and 24.5). Brihat Samhita ch. 32 (Jha, local scan): 5 close; the four mandala lists match the code. Also found: BS 8 defines the 60-year cycle by Jupiter, not the Chaitra-start count in the code (now labelled a project convention); BS 19 gives year-lord effects only, not the lord's choice or the Chaitra Pratipada chart. Citations corrected in CORRECTIONS.md 2026-11-23. | Citations now point to the right place; levels do not rise until a person records a check. |
| **Other classical texts** (Bhadrabahu Samhita, Meghamala, Garga, Narapati) | Verses quoted in Devanagari could not be matched to an edition. Several archive and wisdomlib links return 404. | No |
| **Practitioner books** (for example Vyapar Ratna) | Cited by page number through a shop listing. No scan. | No |
| **Periodicals** (The Astrological Magazine, Modern Astrology) | 15 monsoon rows cite only the magazine's home page: no issue, no page. | No |
| **Practitioner blogs and sites** | Round 1: quote found on the cited page for 2 of 56 gold rows, 2 of 54 earthquake rows, 0 of 27 monsoon rows. Most URLs were home pages. Round 2 with archive snapshots: 1 gold and 5 monsoon forecasts marked proven ex-ante (all one author). Our own re-check found the quote in 4 of those 6 snapshots (gold 2016; monsoon 2021, 2022, 2023); the 2016 and 2019 monsoon rows need a manual read. | Those few rows, after a manual read |
| **Video (YouTube, TV clips)** | Seven gold rows cited video IDs that do not exist. In our own list, two videos are "prediction came true" retellings with the event not identified. **0 verified.** | No |
| **Social posts** | One verified: a post of 2023-02-03 about "South-Central Turkey, Jordan, Syria, Lebanon", three days before the Mw 7.8 earthquake. It gave no end date ("sooner or later"), so it cannot be scored. A second (a 2025 TikTok video) could not be opened by our audit. | No scorable rows |
| **Commercial research site** | One quote verified on the live page; earliest archive capture is about a year after the forecast window opened. | Not as ex-ante |
| **Academic literature** | Round 1: 31 DOIs correct, 11 wrong. Round 2: 9 corrected and confirmed; 2 papers withdrawn as invented; one statistic ("IMD hit rate 63.2%") confirmed as invented. All 18 earthquake papers now resolve. | Yes for the confirmed list; check each quoted effect size at the paper |
| **Data providers** | The right datasets were named. The route to LBMA gold from 1968 is still unsolved (the series codes given return nothing). | Lists yes; licences must be read |
| **The AI collector itself** | Good at structure, lists and reasoning. Unreliable for any specific URL, quote, DOI, verse or number. | Pointers only (ADR-004 D-5) |

### 6.2 The forecast counts

| Set | Rows | Quote verified at source | Date proven before the event | Scorable |
|---|---|---|---|---|
| Gold forecasts | 56 | 2 | 1 | 1 (confirmed by our audit) |
| Earthquake forecasts | 54 | 2, plus 1 partial | 2 (one unconfirmed by our audit) | 0 (open-ended or unconfirmed) |
| Monsoon forecasts | 27 | 10 | 5 (5 more have a capture only after the season began) | 3 confirmed by our audit; 2 need a manual read |
| **All forecasts** | **137** | **14** | **8 marked proven** | **4 confirmed, 6 at most** |
| Gold "episode" claims (astrological explanations of past moves) | 28 | 0 | 0 | 0 |
| Himalaya-Tibet-Myanmar earthquakes of M 7 and above, 1897 to 2026 | 36 events | n/a | **0 with a proven advance prediction** | n/a |
| Our own earlier list (`studies/mundane/sources/prediction_cases.csv`) | 19 | not yet checked | not yet checked | not yet scored |

No forecast has been formally scored yet. Four to six rows, all from one author, is far too few to say anything about skill.

## 7. The one loose end

**Earthquakes when the Moon is in a Varuna-mandala nakshatra.**

- Explore period: RR 1.55 (p = 0.037) and 1.52 (p = 0.038) in the two declustered catalogues.
- Confirm period: RR 1.89 (p = 0.010) and 1.50 (p = 0.098). Same direction.
- Whole period, simple binomial count: 37% of mainshocks in 26% of the time (p = 0.0009).
- Enthusiastic-prior Bayes factor 3.6 to 3.7, the highest in the study.

Why it is **not a finding**: it did not pass the correction, so by the plan it was never carried to confirmation. It is the best of 13 indicators, and one of four mandalas that split the sky between them. The binomial figure ignores clustering and was not planned. The classical text does not make this claim. And the catalogue, the region and the declustering all have known weaknesses.

Why it is worth one more look: it is the only result that points the same way in both periods.

What to do: one registered test on a catalogue this project has not touched (global, M 6 and above), fixed in advance, run once. This is design task D2 in ADR-004. If it fails there, it is closed.

## 8. How claims are made: patterns in the record

These are patterns in the collected evidence, each with where it shows. They describe claims, not people (see the ethics section of the registry specification). The record is small and partly unverified, so read them as observations to test, not conclusions.

| Pattern | What it looks like | Where it shows in our files |
|---|---|---|
| **Explained afterwards** | The sky is matched to an event that has already happened | All 28 gold "episode" claims are of this kind or unverifiable; the Brihat Samhita itself reads the mandala after the earthquake |
| **"I predicted it"** | A later video or post announces a past success; the original is not shown | Two rows of `prediction_cases.csv` are videos of this kind with the event not identified |
| **No end date** | "Sooner or later", "in the coming period" | The one verified earthquake post |
| **Wide target** | A large region, a window of weeks, no magnitude. Such a forecast is nearly always "right". | "Earthquake in North East India" in a four-week window, no magnitude stated |
| **No permalink** | The claim is cited to a home page, so nobody can check the words or the date | 23 of 54 earthquake rows; 38 of 56 gold rows; 15 monsoon rows |
| **Date cannot be proven** | Only the author's own site carries the date | The commercial site's forward call; 5 monsoon forecasts archived after the season began |
| **Opposite rules** | Schools disagree on the sign of the effect, so any outcome fits one of them | "Strong Jupiter lifts gold" against the Brihat Samhita's "benefics make goods plentiful and cheap"; Jupiter in Virgo read as bullish by one source and as a drawdown period by another; tropical against sidereal sign dates ([disputes.md](../../research/incoming/gold/verified/disputes.md)) |
| **Rule without a text** | A "classical" rule that no verse supports | `shukra_guru_wealth.yaml` and `venus_own_sign.yaml` say so themselves; Mars-Ketu orbs of 8, 13 and 15 degrees in different files (review M8) |
| **Text used for another purpose** | A verse about consequences is used as a trigger | Brihat Samhita ch. 32 mandalas |
| **Back-test presented as prediction** | A rule fitted to past events is reported by its hit count on those events | A "5 of 11 M 7 earthquakes on the predicted day" back-test; a rule drawn from a 53-year study of the same gold series |
| **Second-hand credit** | A success is attributed to a late authority with no original source | Raman's 1989 and 1990 earthquake "predictions" as cited by a third-party site; the "vague yes" entries for 1950 to 2021 in round 1, none retrievable |
| **A claimed hit with no matching event** | | One row describes an "M 7.2 Uttarakhand earthquake on 2021-02-12"; the maintainers know of no such event. Not yet checked against the catalogue. |
| **Specific and checkable** (the good case) | A number, a region, a season, published before | Monsoon totals as a percentage of the long-period average for 2021, 2022 and 2023, archived in May of each year; a 2016 call that gold would rise after Jupiter entered Virgo in August 2016. The review notes gold fell from 1,321.5 to 1,127.8 USD between 2016-08-26 and 2016-12-15; the window ran to 2017-09 and has not been formally scored. |

The last row matters. Testable claims exist. They are a small share, and they are the only ones that can ever count for or against a method. The claims registry is built to find more of them and to let practitioners register new ones in advance.

## 9. What would change these conclusions

| If this happened | Then |
|---|---|
| The gold re-run (WP-15) on proper data finds an effect that survives correction, baselines and placebo skies | Section 3.3 changes; a prospective test follows |
| The registered Varuna test on the global catalogue passes | Section 7 becomes a result needing outside replication |
| A frozen model or a registered practitioner forecast wins its live bet (ADR-005 E-9) | The first real evidence of predictive skill |
| None of these | The project's headline stays: a careful null, an open testing tool, and a public record of claims |

## 10. Evidence index

| What | File |
|---|---|
| Earthquake results, tables, power, controls, Bayes | `studies/earthquake/artifacts/`: `results.json`, `family_explore.csv`, `confirmation.csv`, `raw_descriptive.csv`, `tbl_power.csv`, `tbl_controls.csv`, `tbl_bayes.csv` |
| Atlas results and every candidate | `studies/combinations/artifacts/results.json`, `atlas.csv` |
| Gold results and tables | `studies/gold_market/artifacts/results.json`, `tbl_indicator_tests.csv`, `tbl_confirmation.csv`, `tbl_event_study.csv` |
| Silver results | `studies/silver_market/artifacts/results.json` |
| Numerology results | `studies/numerology_vs_astrology/artifacts/results.json` |
| Mundane state | `studies/mundane/artifacts/summary.json`, `studies/mundane/hypothesis.yaml` |
| Analysis plans | `studies/*/hypothesis.yaml`, `studies/combinations/grammar.yaml` |
| Rules and the one confirm | `rules/`, `rules/seismic/mangal_ketu_primary.yaml` |
| Review, with the exact-shift recomputation | `RESEARCH_REVIEW_2026-11-22.md` (sections 2.5, 3, appendix) |
| Corrections and withdrawals | `CORRECTIONS.md` |
| Outside evidence, both rounds, hashed | `research/incoming/` and `research/incoming/MANIFEST.csv` |
| Audit of the outside evidence | `docs/research/handover/INCOMING_AUDIT_2026-11-22.md` |
| Verified-round summaries | `research/incoming/{gold,earthquake,flood,gold_prices}/verified/summary.md` |
| Earlier practitioner list | `studies/mundane/sources/prediction_cases.csv` |
| Plans for the fixes | `docs/adr/ADR-004-paper-production-and-principle-validation.md`, `docs/research/PAPER_ROADMAP.md` |
| Feasibility of our own model | `docs/adr/ADR-005-pattern-discovery-and-claims-registry.md` |
