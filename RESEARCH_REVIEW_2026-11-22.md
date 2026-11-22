> Independent review written 2026-11-22 by a Fable reviewer, with three Opus sub-reviewers whose headline claims it spot-checked. Read-only: no code was changed. Next-phase research prompts: [docs/research/handover/GEMINI_PROMPTS.md](docs/research/handover/GEMINI_PROMPTS.md).

# Independent review: astro-research (papers, tools, gold study, data)

Reviewer stance: econometrics / empirical finance / statistical seismology / research methods / Jyotish operationalisation. Read-only review of the working tree on 2026-11-22 (HEAD 7018b2a). Paths are relative to the repo root. Line numbers are from the files as read. Three sub-reviews (earthquake, numerology/mundane/rules, cross-study papers/engineering) were delegated and their headline claims spot-checked; the gold deep dive and the exact-shift recomputation are my own.

Short verdict: the rebuilt *pipelines* (gold, silver, earthquake) are a serious, honest attempt and are far better than what CORRECTIONS.md withdrew. The *repository as published* is not: it still renders and links withdrawn results, the "pre-registration" is not verifiable, the gold price series is poor, and the one "significant" gold result is a Monte Carlo artefact. No paper is journal-ready today. Two (gold+silver merged, earthquake) can become publishable null-result papers with about a month of focused work.

---

## 1. Ratings

Sub-scores are out of 10: Q = question and pre-registration, D = data quality/provenance, S = statistical validity, A = astrological operationalisation fidelity, R = reproducibility (renders from results.json, no stale content), W = writing/journal-readiness.

| # | Paper | Q | D | S | A | R | W | Overall | Realistic venue today / after fixes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | studies/gold_market/paper/manuscript.qmd | 6 | 3 | 5 | 4 | 6 | 7 | **5.0** | Today: preprint (SSRN/OSF). After fixes: Finance Research Letters, J. Behavioral & Experimental Finance, Applied Economics Letters, PLOS ONE / Royal Society Open Science (null results) |
| 2 | studies/silver_market/paper/manuscript.qmd | 6 | 2.5 | 5 | 4.5 | 6 | 7 | **5.0** | Not a separate paper: merge into #1 as a second asset |
| 3 | studies/earthquake/paper/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd | 7 | 5.5 | 6 | 4.5 | 7 | 7 | **6.0** | Today: preprint (EarthArXiv). After ISC-GEM + ETAS + power fix: PLOS ONE, RSOS, Geoscience Letters; SRL only as a short "negative result" note |
| 4 | studies/earthquake/paper/rigor_audit.qmd | 2 | 1 | 1 | 1 | 0 | 3 | **1.5** | None. Withdrawn content still rendered and linked |
| 5 | studies/combinations (atlas; README + results) | 6 | 5.5 | 3.5 | 4 | 7 | 7 | **4.5** | Supplement to #3 only |
| 6 | studies/numerology_vs_astrology/paper/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.qmd | 3 | 7 | 6 | 2 | 7 | 6 | **4.0** | Teaching note / blog. The result follows from the definitions |
| 7 | studies/numerology_vs_astrology/paper/numerology_planet_timeline.qmd | 0 | 2 | 0 | 2 | 1 | 2 | **1.0** | None |
| 8 | studies/mundane (pre-paper: hypothesis.yaml, README) | 5 | 2 | n/a | 3 | 2 | 6 | **3.0** | None yet; a Registered Report Stage 1 is conceivable once founding times are sourced |
| 9 | studies/remedy_conflict_matrix/paper/remedy_collision_logic.md | 0 | 0 | 0 | 2 | 0 | 2 | **1.0** | None; not research |
| 10 | studies/remedy_conflict_matrix/paper/side_effect_analysis.md | 0 | 0 | 0 | 1 | 0 | 2 | **1.0** | None; not research |
| 11 | papers/00_executive_summary.qmd | 2 | 1 | 1 | 2 | 1 | 3 | **1.5** | None |
| 12 | papers/COMPREHENSIVE_RESEARCH_THESIS.qmd | 2 | 1 | 1 | 2 | 1 | 2 | **1.5** | None |
| 13 | papers/VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.qmd | 2 | 1 | 1 | 2 | 0 | 4 | **1.0** | None until regenerated from results.json |
| 14 | papers/research_paper.md | 1 | 1 | 1 | 1 | 0 | 3 | **1.0** | None |
| 15 | papers/astrology/01_celestial_mechanics_and_ephemeris.md | 6 | - | - | 5 | 3 | 6 | **5.0** | Internal docs |
| 16 | papers/astrology/02_house_systems_and_polar_singularities.md | 5 | - | - | 3 | 3 | 5 | **4.0** | Internal docs |
| 17 | papers/astrology/03_aspect_geometry_graph_theory.md | 4 | - | - | 2 | 3 | 5 | **3.5** | Internal docs |
| 18 | papers/astrology/04_temporal_inflection_retrogrades_progressions.md | 4 | - | - | 2 | 3 | 5 | **3.5** | Internal docs |
| 19 | papers/astrology/05_declination_out_of_bounds.md | 3 | - | - | 1 | 3 | 4 | **3.0** | Internal docs |
| 20 | papers/astrology/06_essential_dignity_scoring.md | 4 | - | - | 3 | 2 | 4 | **3.5** | Internal docs |
| 21 | Rule workbench as a method (ADR-003, libs/.../rules) | 6 | 4 | 5 | 3 | 7 | 7 | **5.0** | JOSS-style software note after the guard fixes |

Rubric notes.

- **Gold (5.0).** Good design skeleton (fixed family, autocorrelation-preserving null, BY, explore/confirm, SPA, results rendered from results.json at manuscript.qmd:38-63). Marked down for the price series (Section 2.1), the miscomputed p-value that produced the only "discovery" (C1), a pre-registration that is one minute older than its results (C2), no macro controls, no power statement in the paper, and a thin, partly non-classical indicator family.
- **Silver (5.0).** Same pipeline; adds purnima/amavasya (the only indicators with a published prior, Dichev & Janes 2003). Data are worse: median Yahoo volume 53 contracts, 3,681 of 5,824 bars under 100 contracts, 86 gaps longer than 5 days.
- **Earthquake (6.0).** The strongest paper. 297 events (Mw >= 5.195, 1976-2026), 186 after Gardner-Knopoff, family of 26, 0 significant, honest about the Varuna-mandala pattern being only a candidate. Marked down for power computed at unadjusted alpha, a positive control that could not succeed, GK windows that leave the 2015 Mw 7.3 in as a mainshock, single catalogue, and "classical" indicators that the repo's own rule files say have no verse.
- **Numerology (4.0).** Statistically tidy TOST on a question whose answer is derived in the paper itself (two deterministic calendars with incommensurate periods). kappa = -0.012, TOST p = 3.4e-5, n = 1,827. Results predate the moolatrikona fix and were not recomputed (CORRECTIONS.md:41-43).
- **Cross-study papers (1.0-1.5).** None reads a results.json; all hard-code numbers; several still print withdrawn results (see C3).
- **papers/astrology (3.0-5.0).** Tutorial notes, mostly Western technique (orb aspects, progressions, out-of-bounds, Lilly-style dignity points) in a project whose studies are sidereal Jyotish. Contain factual errors (obliquity series units; Placidus cusp formula; SE body 11 described as the descending node, the documentary root of the Ketu bug).

---

## 2. Gold study deep dive

Files: studies/gold_market/hypothesis.yaml, studies/gold_market/scripts/pipeline.py (a 27-line shim), libs/vedic_astrology_core/markets/{study,features,align,event_study,fetch,report}.py, libs/vedic_astrology_core/stats/{permutation,nulls,multiplicity,walk_forward,granger,stationarity,power}.py, studies/gold_market/artifacts/{results.json,manifest.json,tbl_*.csv}, data/snapshots/gold_market_3085b0d501ec.csv.

### 2.1 Price series actually used

| Item | Value | Where |
|---|---|---|
| Registered first choice | LBMA PM fix via FRED GOLDPMGBD228NLBM, 1968-04-01 onward | hypothesis.yaml:20-24, 30 |
| What ran | Yahoo GC=F, "COMEX front-month continuous futures", USD/oz, daily close | results.json data; FRED returned HTTP 404 |
| Range / rows | 2000-09-05 to 2026-10-30, 6,150 bars | results.json data |
| Spot or futures | Futures, unadjusted for rolls | hypothesis.yaml:37-40 |
| Currency | USD only | |
| Snapshot | data/snapshots/gold_market_3085b0d501ec.csv, SHA-256 3085b0d5..., gitignored (.gitignore:39), not released | manifest.json |
| Sampling instant for the sky | 13:30 America/New_York on each bar date | hypothesis.yaml:28-29; align.py:32-43 |

Problems with this series (computed from the snapshot):

1. **It is not a daily series before 2008.** Bars per year: 2000: 46, 2001: 143, 2002: 168, 2003: 225, 2004: 229, 2005: 200, 2006: 217, 2007: 224, then about 250. There are 54 gaps longer than 5 calendar days (up to 26 days: 2001-04-27 to 2001-05-23) and 83 "daily" returns that span more than 4 calendar days, 74 of them in the explore period. Each is treated as a one-bar return (study.py:144), so early absolute returns and the rolling "extreme" threshold are contaminated.
2. **It is the nearest-expiry contract, not the active one.** Median volume in the file is 251 contracts; 2,191 of 6,150 bars have volume under 100 and 3,974 under 1,000 (the first row has volume 2). Active-month COMEX gold trades roughly 10^5 contracts a day. Yahoo's GC=F tracks the front (often spot-month, illiquid) contract.
3. **The cleaning rule creates the gaps.** hypothesis.yaml:38 asserts "Zero-volume Yahoo rows are stale quotes and are dropped" (fetch.py:165-168). An exchange settlement price exists on zero-volume days; dropping them removes real trading days non-randomly and is the likely source of problem 1. This needs checking against an independent series.
4. **Rolls.** Front-month rolls are not back-adjusted (hypothesis.yaml:38-40). At 2-5% carry a bi-monthly roll is a 30-80 bp jump, the same size as the mean absolute daily move (about 88 bp, README:58). It is not correlated with planets, but it adds noise to absret and puts mechanical entries into the "extreme" flag.
5. **The registered sample (1968 onward) was silently replaced by a 26-year one.** study.py:90 passes \`start or "1990-01-01"\` to Yahoo, which has nothing before 2000-08-30. The explore period is therefore 2000-09 to 2015: 1.3 Jupiter revolutions and half a Saturn revolution. This is a deviation from the registration and should be listed as one; \`amendments: []\` (hypothesis.yaml:10) is wrong.
6. **Docs disagree about the source.** data/README.md:19 still says "Gold price, XAU/USD (XAUUSD=X, fallback GC=F)" fetched by studies/gold_market/scripts/fetch_gold_data.py, a file that does not exist; data/README.md:26 says "No snapshot backs a published result yet" while results.json says \`provisional: false\`.

### 2.2 Fluctuation measures

| Measure | Definition | Code |
|---|---|---|
| ret | log C[t] - log C[t-1], bp/day | study.py:142-148 |
| absret | abs(ret) | same |
| extreme | abs(ret) above the 95th percentile of the previous 250 bars (shifted, past-only) | study.py:146-147; hypothesis.yaml:68-70 |
| Test statistic | mean(outcome on bar t given indicator on t-1) minus mean(outcome given inactive), two-sided | study.py:152-154, 172 |
| Station event study | forward log return over 5, 21, 63 bars from the first bar a planet is seen retrograde (Mercury to Saturn); stations direct are not studied | study.py:293-298; event_study.py:25-31 |
| "Granger" | ADL: outcome on 5 own lags plus sin and cos of sidereal longitude at lag 1 (Sun, Mars, Jupiter, Saturn); HAC Wald; outcomes = returns and abs GARCH(1,1)-standardised residuals | study.py:322-364; granger.py:62-145 |
| SPA | each indicator as a one-day long/short rule in the confirm period, direction = sign of its explore effect, benchmark = flat | study.py:250-290 |

Not computed: realised volatility (no intraday or OHLC), range-based estimators (Parkinson, Garman-Klass), conditional volatility models with the indicator in the variance equation, signed tail events, drawdowns, turning points, multi-day outcomes for the state indicators, or anything relative to macro news.

Indicators (14, hypothesis.yaml:46-60): five retrogrades, Venus and Jupiter combust, Sun in Aries / Libra / Leo, Jupiter in Cancer / Capricorn, Venus-Jupiter within 8 degrees, Venus in own sign. Activity shares run from 5.4% (conjunction) to 37.6% (Saturn retrograde). No Moon, tithi, nakshatra, node, dasha or chart-based indicator is in the gold family, although \`node_model: mean\` is declared (line 42) and the feature layer supports tithi and houses (features.py:27).

### 2.3 Nulls

- **Indicator tests:** circular shift of the lagged indicator inside the period, offsets uniform in [400, n-400], 10,000 draws, p = (k+1)/(10001) (permutation.py:116-123; nulls.py:31-61; hypothesis.yaml:71-73).
- **Effect CI:** paired stationary bootstrap, mean block 20 bars, 1,000 resamples (permutation.py:130-138).
- **Event study:** stationary block bootstrap of returns rebuilt into a path, same event bars (event_study.py:70-73).
- **SPA:** stationary bootstrap, mean block 20 (walk_forward.py:71-129).

### 2.4 Multiplicity, split, results

- Family: 14 indicators x 3 outcomes = 42, Benjamini-Yekutieli within each period (study.py:223-234). Explore = 2000-09-05 to 2015-12-31 (3,462 usable bars), confirm = 2016-01-01 to 2026-10-30 (2,687 bars). A third "full" pass is also tested and corrected.
- Secondary families: 15 event tests (BY), 8 Granger tests (BY).
- Reported outcome: verdict \`not_replicated\`. One explore test passes: jupiter_debilitated on absret, +29.8 bp/day, p = 0.0001, q = 0.018; confirm +8.8 bp, p = 0.73. SPA p = 0.53 (best rule venus_combust, +1.3 bp/day). Events 0/15. Granger 0/8, nearest Saturn on garch_abs p = 0.0024, q = 0.053.

### 2.5 The one "discovery" is an artefact (my recomputation)

Jupiter was in sidereal Capricorn in the explore period exactly once: 2008-12-09 to 2009-12 (two runs, 198 bars), i.e. the post-Lehman volatility regime. In the confirm period it was there in 2020-03 to 2021 (COVID). The confirm-period "candidate" the paper's discussion would surface, jupiter_exalted on absret (q = 0.018), is Jupiter in Cancer from 2025-10, i.e. the 2025-26 gold blow-off. These are single-episode coincidences with volatility regimes: effective sample size is 1.

The reported p = 0.0001 is not attainable. With n = 3,462 and min shift 400 there are only 2,663 distinct shifts; the code draws 10,000 with replacement and divides by 10,001. Enumerating all shifts from artifacts/overlay_frame.csv (script: scratchpad/exact_shift.py) gives k = 0 of 2,663, so the exact p is 1/2,664 = 3.75e-4 and the BY q is 3.75e-4 x 42 x 4.327 = **0.068**, above 0.05. For the confirm-period jupiter_exalted case: 1,888 shifts, exact p = 5.3e-4, q = 0.096. With the correct p-values the gold verdict is plain \`null\`, with zero explore discoveries. The results.json, README.md:9-12 and the rendered paper all state otherwise.

### 2.6 Power

- README.md:48-77 gives minimum detectable differences of 11-30 bp/day (returns), 13-45 bp/day (absolute returns) and 3-6 pp (extreme rate) for the explore period. This table is not in the paper; the paper's Limitations paragraph (manuscript.qmd:228-232) has no numbers.
- They are optimistic for three reasons: (a) computed at unadjusted two-sided alpha 0.05 (2.80 SE) while the registered decision needs BY across 42 tests, about p < 2.7e-4 for a lone effect, i.e. (3.64 + 0.84) = 4.5 SE, 1.6 times larger, and then replication in the confirm period; (b) the SE is read from a bootstrap with 20-bar blocks while indicator runs last 60-250 bars and absolute returns have autocorrelation of 0.10 at lag 20 and 0.06 at lag 60 (my calculation), so the SE is understated; (c) for the Jupiter-in-sign indicators the effective n is 1-2 episodes and no bar-level power statement is meaningful.
- Against plausible effects: the lunar-cycle literature reports return differences of a few bp/day in equities. A 4 bp/day effect with SE of about 4 bp has under 20% power at unadjusted alpha and close to none after BY. The honest summary is "the design can exclude effects of roughly a quarter to a half of a typical daily move; it cannot speak to effects of the size any credible literature reports".

---

## 3. Flaws, ranked

### Critical

**C1. Circular-shift p-values are wrong when draws exceed distinct shifts; the gold "not replicated" verdict rests on it.** permutation.py:116-119 with nulls.py:45; hypothesis.yaml:72-73; results.json headline. Fix: enumerate all admissible shifts when their number is below n_perm (exact test), report the attainable minimum p, and re-run gold and silver. The same structural error, in the opposite direction, is in the combination atlas: studies/combinations/grammar.yaml:110-114 claims 1/2001 is "far below any BY threshold" when the BY rank-1 threshold for 705 tests is about 9.9e-6, so "0 survived BY" was guaranteed before the data were seen.

**C2. The pre-registration is not a pre-registration.** hypothesis.yaml:2-4 says it was written before the first run. Git shows the gold hypothesis committed at 08:02:41 +0545 (f7983c1) and results generated at 02:18:33 UTC = 08:03:33 +0545, on a dirty tree at a different commit (results.json git: 370edd9, dirty true). Earthquake: hypothesis 08:00, results 08:12, then the hypothesis was amended in the commit that added new results (4acdc21). Numerology and combinations: hypothesis and results in one commit. No external timestamp (OSF, AsPredicted, Zenodo) exists. The same gold series and the same Himalayan catalogue had been analysed in the withdrawn papers. Every results.json has \`dirty: true\`. Explore, confirm and full periods are all computed in one invocation (study.py:402-409), so the confirm period is not sealed in any operational sense. README.md:115 ("before any data are analysed, and one command reproduces") is false on both counts. This should be called "a fixed analysis plan committed alongside the first run", and a real prospective registration made for data after a stated date.

**C3. Withdrawn results are still rendered, linked and shipped.** _quarto.yml:17-19 renders papers/*.qmd and papers/*.md; the navbar links studies/earthquake/paper/rigor_audit.qmd (:50), numerology_planet_timeline.qmd (:54), the remedy notes (:56) and papers/VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.qmd (:62).
- VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.qmd:378-406 still prints the stationarity, Granger and Molchan tables from the synthetic gold series (CORRECTIONS (b)); :309-322 the negative-binomial coefficients from tropical positions and the delta-AIC 22.13 vs 27.95 from the random-number Monte Carlo (CORRECTIONS (a), (c)).
- rigor_audit.qmd:138-166 shows withdrawn regression and confusion tables under a withdrawal banner; :57 attributes a quotation to Brihat Samhita 17.14 that rules/seismic/mangal_ketu_primary.yaml:12-13 says does not support the claim.
- papers/research_paper.md:56-68 reports n = 552, Schuster p = 0.067, delta-AIC 22.13: no artifact supports any of it; :87 cites a non-existent author for Swiss Ephemeris.
- COMPREHENSIVE_RESEARCH_THESIS.qmd:124-141 includes the legacy earthquake sections, which read an untracked tropical daily_astro_base.csv and launch generator scripts at render time.
- All 12 PDFs in papers/pdf/ and the three files in application/web/static/releases/ predate the corrections (DE440 claim, synthetic Granger, 370-event earthquake run) and carry no banner. The release manuscript contains a placeholder figure and an unsupported "more frequently than chance" claim, and is not listed in CORRECTIONS.md.
- scripts/generate_artifacts.py (run by .github/workflows/scientific-reporting.yml:62) reads a still-tropical data/processed/aligned_planetary_data.csv and writes into studies/gold_market/artifacts/, the registered study's folder.

**C4. The gold and silver price data are not fit for a daily-return paper.** Section 2.1 items 1-4 (fetch.py:165-168; hypothesis.yaml:37-40; study.py:90). Sparse pre-2008 bars, illiquid nearest contract, unadjusted rolls, no cross-check against any second source. A referee in finance will stop here.

**C5. Headline claims in the cross-study papers contradict the artifacts.** "120:1 frequency mismatch" (00_executive_summary.qmd:25; thesis :12) versus 364.45 against 350.26 changes a year in numerology results.json; "over 2,500 combinations, 2015-2024, M > 6" (:29) versus 4,977 candidates and 297 events of Mw >= 5.2 from 1976; "XAU/USD spot 2000-2024" versus GC=F futures to 2026; "markets are efficient / no causal link / no predictive power" (:32-34) reads low-power nulls as proof of absence.

**C6. The rule workbench's guarantees fail as built.**
- Direction is ignored: studyadapter.py:121-125 maps only increase/decrease; rules with up/down/either run two-sided, and the market outcome is an unsigned extreme-move flag (studyadapter.py:186-188). "Gold falls" (vyapar_ratna_inverse_dignity_gold.yaml) and "gold peaks" (tempora_jupiter_cancer_gold_peak.yaml) are tested on the same statistic.
- Family size defaults to 1 for any rule outside a study's registered family (workbench.py:404); 59 active rules, no correction across rules, versions or studies.
- Confirm can be retried by bumping the rule version (workbench.py:329-332; ADR-003:16-19); the market confirm period ends at "now" (studyadapter.py:112).
- The holdout is known to rule authors: jupiter_virgo_gold_rise_2016.yaml encodes a 2016 call inside the 2016+ confirm period (and the call failed: 1,321.5 on 2016-08-26 to 1,127.8 on 2016-12-15); Tempora's rule comes from a 53-year study of the same series.

### Major

**M1. The circular-shift null is not valid under non-stationary volatility, and the paper says the opposite.** Rotation tests need the outcome to be stationary. results.json stationarity shows KPSS rejecting for absret; report.py:349-354 then claims the null "keeps that dependence". It keeps short-range clustering, not regime shifts (2008, 2020, 2025-26). With single-run indicators the test is a test of "is this year different", which is always true for volatility. Two of 84 period tests hit the floor p for exactly this reason. Fix: test on volatility-standardised outcomes (GARCH or HAR residuals), or put the indicator into the variance equation with macro controls; require at least about 8 independent episodes per indicator in each period.

**M2. Effective sample size is not reported or enforced.** min_active_bars = 20 (hypothesis.yaml:76) counts bars, not episodes. Explore-period episodes: jupiter_debilitated 1 transit, jupiter_exalted 2, mars_retrograde 7, venus_retrograde 10, jupiter_combust 14. The right unit for slow indicators is the episode (cluster), with cluster-robust or episode-level inference.

**M3. SPA benchmark and direction are mis-specified.** study.py:256-275: loss = -(position x raw return) against a flat benchmark. Gold drifted about +4.8 bp/day in 2016-2026, so any long rule earns drift x duty cycle (the "best" rule's +1.3 bp/day is exactly that scale). Direction comes from the explore *difference* (active minus inactive), but the pay-off is the raw return while active. A rule can "beat flat" with no information. Use excess over exposure-matched buy-and-hold (or demeaned returns), and add transaction costs.

**M4. Solar-sign indicators and the longitude regression cannot separate astrology from the calendar.** Sun in sidereal Aries is 14 April to 14 May every year; Libra is 17 October to 16 November. These are calendar-month dummies shifted by two weeks, and they coincide with Akshaya Tritiya and Dhanteras/Diwali gold demand by construction (the Hindu calendar is sidereal-solar/lunar). sin/cos of sidereal longitude span the same space as sin/cos of tropical longitude (constant phase), so the "Granger" test (study.py:339-340) is a seasonal harmonic test for the Sun and a slow-trend test for Jupiter and Saturn (Saturn completes 0.89 of a cycle in the sample; its near-miss p = 0.0024 on garch_abs is a low-frequency regression on a secular volatility pattern). No month-of-year, day-of-week, turn-of-month, holiday or festival controls exist anywhere.

**M5. No confounders.** Nothing in markets/ conditions on real yields, the dollar, VIX/GVZ, inflation surprises, FOMC and payroll days, geopolitical risk, ETF flows or central-bank buying. For a null result this mainly costs power (residual variance); for any future positive result it is fatal.

**M6. Power statements are optimistic and absent from the papers.** Gold: Section 2.6. Earthquake: studies/earthquake/hypothesis.yaml:304-306 and robustness.py:269-275 use unadjusted alpha 0.05 against a BY family of 26; MDRR 1.7-3.5 is a best case; power.py:8-15 assumes Poisson events. The tidal positive control (MDRR 1.43-1.50 against published effects of a few percent) could not have been detected and was added after the null.

**M7. Earthquake catalogue and declustering.** USGS ComCat only; 1,563 of 1,645 events are mb converted to Mw; Gardner-Knopoff windows (decluster.py:51-52) leave the 2015-05-12 Mw 7.3 and two same-week events as mainshocks; the region includes Tibetan rift events (2025 Tingri Mw 7.1) despite hypothesis.yaml:33; the offline fallback parses Nepal local time as UTC (fetch_catalogue.py:190), a +5h45m shift that would corrupt hourly mandala indicators in any offline run.

**M8. Operationalisation is thin and partly non-classical.**
- Gold family: no Moon, tithi, nakshatra, node, dasha, hora or weekday lord, although these are what practitioners actually use for short-horizon calls; the 14 chosen are dominated by slow states with one or two episodes.
- "Which chart is gold's chart" is unanswered: no chart of a market inception, of India (the largest physical market), or of the US dollar (1971-08-15) is used; whole-sign houses are mentioned in the paper (manuscript.qmd:146) but no house indicator is tested.
- Sources: shukra_guru_wealth.yaml:7-9 admits "no text, chapter or verse"; venus_own_sign.yaml:8-11 admits BPHS does not make the market claim. Mars-Ketu and Mars-Saturn earthquake rules have no verified verse. Orbs conflict across files (8, 13, 15 degrees for Mars-Ketu).
- Ayanamsa: Lahiri only, no sensitivity run (Raman, KP, true Chitrapaksha); for sign-boundary indicators a 1-degree change moves ingress dates by about 1 day for the Sun and by weeks for Jupiter near stations.
- Node model: mean only; irrelevant to gold (no node indicator) but declared.
- Combustion orbs (combustion.py:16-23) are fine; exaltation is by whole sign, not by degree-graded strength.
- Mundane: 0 of 113 countries have a sourced founding time; noon placeholders drive Moon-sign indicators and published dasha timelines (studies/mundane/scripts/features.py:98-99).

**M9. Two rule engines, one silently optional.** The gold study evaluates its two "rule" indicators through the legacy libs/vedic_astrology_core/combinations registry inside a blanket \`except Exception\` that returns an empty frame (features.py:146-160); study.py:131-137 then drops those indicators with a log warning, which would silently change the family size from 42 to 36. The legacy AspectCondition approximates graha drishti by degrees ((house-1) x 30 plus orb, combinations/conditions.py:186-197) instead of by sign. ARCHITECTURE and README claim "one engine".

**M10. Provenance of the ephemeris is inconsistent.** Gold manifest.json says ephemeris_model "swieph"; earthquake and numerology results say "moshier" on the same machine; no .se1 files are in the tree; ephemeris.py:19-24 documents a retflag bug class that would produce exactly this mislabel. Gold results were generated at 370edd9, before the ayanamsa fix (cde45bd) and the dignity fix (7018b2a), and have not been re-run. Numerology results also predate the dignity fix.

**M11. Tests do not check statistical calibration.** About 81 test files; tests/test_stats_permutation.py has five tests, one realisation each (:29, :55). Nothing simulates type-I error of the shift test under GARCH or regime-switching volatility with long-run indicators, BY family behaviour, bootstrap CI coverage, or SPA size under drift. C1, M1 and M3 would all have been caught by a 200-line calibration suite.

**M12. Cross-study multiplicity is not accounted for.** Gold 42 + 15 + 8, silver 42 + 15 + 8, earthquake 26 plus controls, classifier, Bayes; atlas 705; workbench rules at family size 1; three periods per market. Each is corrected alone. A project-level statement (number of hypotheses examined, expected false discoveries) is missing from every paper.

**M13. CI proves nothing about the science.** No workflow runs a study pipeline or checks that results.json regenerates; scientific-reporting.yml:62-100 wraps steps in \`|| echo skipped\`; snapshots are untracked so a rerun refetches different data (Yahoo and ComCat both revise).

### Minor

- hypothesis.yaml:30 start date 1968 versus actual 2000; \`amendments: []\`.
- Extreme-move flag loses the first 250 bars of each series (n = 3,212 vs 3,462) and mixes roll jumps in.
- Event study uses only stations retrograde, and "first bar seen" can be late by days in the gappy 2000-2007 data (study.py:293-298).
- GARCH(1,1) standardisation is fitted on the full sample (granger.py:52), a mild look-ahead.
- CI for the "significant" gold effect includes zero (-0.29 to 62.7 bp) while p = 0.0001: the two procedures disagree and the paper does not comment.
- The two-sided p centres on the null mean (permutation.py:65-66); fine, but undocumented in the paper.
- One shared rng is consumed sequentially (study.py:385), so adding an indicator changes every other p-value.
- Earthquake paper: "one amendment" (two exist); BY described as valid under positive dependence (that is BH); count-model sun_ingress coefficient 13.3 with SE 19.3 (collinear); negative control is one fixed shift.
- Numerology: figures dated before the re-analysis commit; placeholder figure tracked; eight dead scripts; tables/research_results.json holds "Planet position not available".
- Bibliography: references.bib still titles Swiss Ephemeris "DE440 ... 0.001 arcseconds"; a probably invented Lahiri 1960 entry; wrong authors on one sources.bib entry.
- Docs: VALIDATION_AND_EPISTEMOLOGY.md:30 "sub-arcsecond" versus ADR-001:201 Moon error 1.94 arcsec; DATA_PROVENANCE.md:28-45 points at files that do not exist.
- Clutter: research/ (92 files, stale pre-correction copy), use_cases/, build/, htmlcov/, _site/, _freeze/, test.qmd, pages.yml.bak, docs/archive, tests/test.tex.

### Checked and found sound

- No look-ahead in the indicator tests: state at t-1 against outcome at t (study.py:172), past-only extreme threshold (study.py:146). The planetary states are deterministic anyway, so the real look-ahead risk is analyst knowledge of history, not code.
- Sidereal flag and Ketu = Rahu + 180 are now correct (ephemeris.py:51, 16-18); a Horizons cross-check test exists.
- BY implementation is correct (multiplicity.py:33-37, 95-104); (k+1)/(n+1) is used; Hansen SPA code follows the paper.
- Trading-calendar alignment in bars, not calendar days (align.py:151-163).
- The earthquake paper and the two market papers do render every number from results.json.

---

## 4. How far can the theory go

### 4.1 Defensible scope

There is no physical mechanism, so the only defensible framings are:

1. **A falsification test of specific, sourced practitioner claims** (the current intent). Publishable as a null if the design can exclude effects of the size practitioners claim. Practitioners claim large, tradeable effects (turning points, "gold peaks when Jupiter is in Cancer"), so the right power target is "would a rule this strong have been found", not 4 bp/day. State it that way.
2. **A behavioural-calendar channel.** A meaningful share of physical gold demand (India, Nepal, parts of South-East Asia) is timed by the panchanga: Akshaya Tritiya, Dhanteras, Pushya nakshatra days, wedding muhurta seasons, and avoidance of Pitru Paksha, Adhik Maas and Kharmas. That is a real, testable mechanism: astrology as a coordination device for buyers. It predicts effects in **Indian premia and volumes** (MCX-London basis, import data, jewellery sales), not in COMEX returns. This is the only version with a prior above noise and is a genuinely novel paper.
3. **A methods contribution.** How to test deterministic, long-run-length cyclical regressors against financial and point-process data (episode-level inference, shifted-sky nulls, exact shift tests). Novy-Marx (2014, JFE) showed that sunspots and planetary aspects "predict" anomaly returns in standard regressions; this repo could be the constructive counterpart.

What is not defensible: any causal language; "markets are efficient" conclusions from these tests; the remedy material; national-chart dasha claims without sourced times; pooling practitioner rules written after the events they describe.

### 4.2 Models missing for a modern gold paper

| Gap | What to add |
|---|---|
| Conditional variance | GARCH(1,1), EGARCH, GJR-GARCH with the indicator in the variance equation (GARCH-X), Student-t or skewed-t errors; compare with and without macro regressors |
| Realised volatility | HAR-RV (Corsi 2009) on 5-minute realised variance with the indicator as an exogenous term (HAR-X); range-based proxies where intraday is missing |
| Regimes | Markov-switching mean/variance (2-3 states); test whether indicator state shifts transition probabilities; this directly addresses M1 |
| Tails | Quantile regression at 5/50/95%; peaks-over-threshold with indicator covariate; signed up/down extremes |
| Event studies | Stations, ingresses, eclipses, exact conjunctions with market-model abnormal returns, non-overlapping windows, placebo dates, and a horse race against FOMC/CPI/NFP announcement days |
| Dynamics | Local projections (Jorda 2005) of cumulative return and volatility on event dummies, horizons 1-60 days, with controls |
| Macro baseline | Daily regression on changes in 10-year TIPS yield, broad dollar, VIX/GVZ, GPR, ETF flows; then ask whether astrology explains the residual |
| Calendar baseline | Month, weekday, turn-of-month, holiday, Indian festival and wedding-season dummies; lunar phase as in Dichev & Janes (2003) and Yuan, Zheng & Zhu (2006); precious-metal lunar seasonality (Lucey 2010); Baur (2013) autumn effect; SAD (Kamstra, Kramer & Levi 2003); geomagnetic storms (Krivelyova & Robotti 2003) as a rival "cosmic" regressor |
| Forecasting | Walk-forward (expanding and rolling) elastic net / gradient boosting with macro-only versus macro+astro feature sets; purged, embargoed CV |
| Shifted-sky baseline | Refit every model on the sky displaced by many random offsets (and on a tropical-zodiac and a scrambled-rulership sky); the astro increment must beat the distribution of placebo skies |
| Forecast comparison | Diebold-Mariano (with Harvey-Leybourne-Newbold correction), Clark-West for nested models, Giacomini-White conditional test |
| Data-snooping control | White Reality Check, Hansen SPA with a proper benchmark, Romano-Wolf stepdown, Model Confidence Set (Hansen, Lunde & Nason 2011), deflated Sharpe ratio, and a t > 3 hurdle (Harvey, Liu & Zhu 2016) |
| Uncertainty | Conformal prediction intervals for return and volatility forecasts; check whether astro features shrink interval width at fixed coverage |
| Inference for slow regressors | Episode-clustered standard errors, exact shift tests, wild cluster bootstrap by episode, HAC with bandwidth at least the run length |
| Economic significance | Net-of-cost Sharpe, turnover, capacity; break-even transaction cost |
| Evidence for the null | Equivalence tests (TOST) against a pre-stated smallest effect of interest; Bayes factors with a prior taken from practitioner claims |
| Replication breadth | Silver, platinum, gold in INR/CNY/EUR/GBP/JPY, pre-2000 London fix, and at least one equity index (Nifty, S&P) for the ten equity rules that currently have no adapter |

### 4.3 What the astrology term should be compared against

In order: (1) the unconditional mean and a volatility model with no regressors; (2) calendar and seasonal dummies including Indian festival demand; (3) lunar phase alone, since it has a published effect size and is astronomically trivial; (4) macro news and state variables; (5) other "cosmic" regressors (sunspots, Kp/Ap); (6) placebo skies. Only an increment over (2)-(4) that also beats (6) is worth reporting as astrological.

---

## 5. Data gaps

### 5.1 Gold and silver

| Dataset | Why needed | Likely source | Licence concern |
|---|---|---|---|
| LBMA Gold Price AM/PM, daily from 1968 (USD, GBP, EUR) | The registered primary series; triples the sample; 5 Jupiter and 2 Saturn cycles | LBMA / ICE Benchmark Administration; Bundesbank time-series database (London fixing); World Gold Council Goldhub; Stooq XAUUSD | IBA licence restricts redistribution (the reason FRED dropped it in 2022). Bundesbank and WGC allow research use; do not commit the file, publish hash + fetch script |
| LBMA Silver Price daily from 1968 | Same for silver | LBMA/IBA; Bundesbank | Same |
| World Bank Pink Sheet monthly gold/silver/platinum from 1960 | Long low-frequency check; already in data/snapshots (worldbank_pinksheet_3c8d9d8dbb48.xlsx) but unused by any study | World Bank | CC BY 4.0; safe to commit |
| COMEX GC and SI per-contract daily settlement, volume, open interest; proper back-adjusted continuous series | Replace Yahoo GC=F; fix rolls; volume and OI as outcomes | CME DataMine; Barchart; Norgate; Databento | Paid, no redistribution |
| CFTC Commitments of Traders (weekly from 1986) | Positioning control | cftc.gov | Public domain |
| Intraday gold (1-5 minute) from about 2003 | Realised volatility, HAR-RV, announcement windows, intraday timing of exact stations/ingresses | Dukascopy tick XAUUSD (free); FirstRate Data, TickData (paid) | Dukascopy: personal/research use, no redistribution |
| Gold in INR, CNY, EUR, GBP, JPY | Separate dollar moves from gold moves; local-investor channel | WGC Goldhub (daily multi-currency from 1978); RBI reference rate x USD price; BIS/FRED FX | WGC terms: no redistribution; FX rates public |
| Indian domestic gold: MCX futures (2003+), IBJA daily rates, landed-cost premium/discount | The behavioural-calendar hypothesis lives here | MCX bhavcopy archive; ibjarates.com; Reuters/WGC premium series | MCX data terms restrict redistribution; IBJA has no formal bulk licence, ask |
| Shanghai Gold Exchange Au99.99 and SGE premium | Second physical market | SGE website; WGC | Terms unclear |
| Festival and muhurta calendar (Akshaya Tritiya, Dhanteras, Diwali, Pushya days, wedding seasons, Pitru Paksha, Adhik Maas) 1968-2026 | Demand seasonality control and the main behavioural regressor | Compute with the repo's own panchanga engine; cross-check against Rashtriya Panchang / drikpanchang | Computed data is yours; do not scrape drikpanchang in bulk |
| Indian gold imports (monthly) and import-duty change dates | Demand outcome and policy confounder | DGCI&S / Ministry of Commerce; CBIC notifications; WGC | Government open data |
| Central-bank gold purchases | Structural demand since 2010, dominant 2022-26 | WGC quarterly; IMF IFS monthly reserves | WGC terms; IMF free with attribution |
| Gold ETF holdings (GLD from 2004, IAU, global totals) | Investment-flow control | SPDR site daily CSV; WGC monthly flows | Free to use, cite; redistribution unclear |
| Real yields: 10-year TIPS (DFII10, 2003+); pre-2003 proxy | The main macro driver | FRED | Public domain |
| Dollar: Fed broad index (DTWEXBGS, DTWEXM history) | Driver | FRED | Public domain. ICE DXY itself is licensed; use the Fed index |
| CPI, breakevens (T10YIE), inflation surprises | Driver | FRED/BLS; surprises need a consensus series (paid) | CPI public; consensus data licensed |
| VIX (1990+), GVZ gold volatility index (2008+), MOVE | Risk state; GVZ is a direct volatility benchmark | CBOE via FRED (VIXCLS, GVZCLS) | CBOE terms: research use fine, cite |
| Geopolitical Risk index, daily from 1985 (Caldara & Iacoviello) | Safe-haven driver | matteoiacoviello.com/gpr.htm | Free, citation required |
| Economic Policy Uncertainty, daily | Driver | policyuncertainty.com | Free, citation |
| FOMC dates, CPI/NFP release dates and times | Announcement-day horse race | Federal Reserve; ALFRED release calendar; BLS schedule archive | Public domain |
| Sunspot number, Kp/Ap geomagnetic indices | Rival cosmic regressors | SILSO; GFZ Potsdam | SILSO CC BY-NC; GFZ CC BY 4.0 |
| Swiss Ephemeris .se1 files (or JPL DE440/441 via SPICE) | End the Moshier fallback ambiguity; state one model in every manifest | astro.com; NAIF | SE is AGPL or commercial: check compatibility with the repo's MIT licence |
| Pre-1968 gold | Not useful (fixed price under Bretton Woods); say so explicitly | - | - |

### 5.2 Earthquakes

| Dataset | Why | Source | Licence |
|---|---|---|---|
| ISC-GEM catalogue (1904 onward, homogeneous Mw with uncertainties) | Removes mb-to-Mw conversion; longer M >= 5.5/6 record | isc.ac.uk/iscgem | CC BY-SA 3.0 |
| ISC Reviewed Bulletin | Multi-agency reviewed locations and magnitudes; time-varying completeness | ISC FDSN | Free for research, cite |
| Frozen ComCat snapshot | ComCat revises events; current snapshot is untracked | USGS; deposit on Zenodo | Public domain |
| Global CMT | Mechanisms: separate thrust from Tibetan normal faulting; tidal Coulomb stress for a real positive control | globalcmt.org | Free, cite |
| Nepal NSC/NEMRC, India NCS | Local magnitudes down to M 3-4 since the 1990s: 10x more events | seismonepal.gov.np; seismo.gov.in | Terms unclear / registration; request permission |
| Historical catalogues (Ambraseys & Douglas 2004; Bilham 2019) | Great events before 1976 for an M >= 7 test | Published tables | Publisher copyright on tables; facts are reusable |
| ETAS-declustered version | GK is inadequate for 2015 | Fit yourself (e.g. etas packages) | - |
| Global replication set | A Himalayan-only test has 186 events; the classical claims are not region-specific except Kurma Chakra | ISC-GEM global M >= 6 | CC BY-SA |

### 5.3 Mundane

| Dataset | Why | Source | Licence |
|---|---|---|---|
| Sourced founding/independence/constitution times with archival citations | 0 of 113 countries have one; everything downstream depends on it | National gazettes, parliamentary records, contemporaneous newspapers; Campion's Book of World Horoscopes as a pointer only (copyrighted, itself secondary) | Facts are free; do not copy Campion's tables |
| Astro-Databank Rodden-rated entries | Reliability grading of chart times | astro.com/astro-databank | Check terms; cite per entry |
| Systematic event sets instead of Wikipedia lists | Remove fame/US selection bias; give denominators | Correlates of War (wars), UCDP/PRIO, Archigos and REIGN (leader changes), Polity/V-Dem (regime change), EM-DAT (disasters), Reinhart-Rogoff / Laeven-Valencia (crises), ACLED | COW/UCDP/V-Dem free with citation; EM-DAT free for non-commercial after registration; ACLED restricts redistribution |
| Scoring protocol and timestamps for practitioner predictions | prediction_cases.csv has 19 self-labelled rows | Archived web pages (Wayback) with capture dates | Quote, do not republish full texts |

---

## 6. Roadmap and open questions

### 6.1 Top 10, in order

1. **Take the withdrawn material off the site today.** Remove papers/*.qmd, papers/*.md, rigor_audit.qmd, numerology_planet_timeline.qmd and the remedy notes from _quarto.yml render and navbar; delete or watermark papers/pdf/* and application/web/static/releases/*; stop CI from running scripts/generate_artifacts.py; delete the tropical CSVs and the stale research/ copy. Add the release manuscript to CORRECTIONS.md. (C3, C5)
2. **Fix the shift test and re-run.** Exact enumeration when admissible shifts are fewer than n_perm; report the attainable minimum p next to every q; raise atlas draws or switch the atlas to max-statistic (Romano-Wolf) inference only. Re-run gold, silver, combinations on a clean tree and correct README/results. Log it in CORRECTIONS.md. (C1)
3. **Replace the price data.** LBMA PM fix 1968+ as registered (Bundesbank or WGC route), plus a proper back-adjusted COMEX series for 1975+; cross-validate the two; never drop zero-volume settlement days; fail the run if more than about 1% of business days are missing. (C4)
4. **Make the registration real.** Freeze the amended plan, deposit it on OSF/Zenodo with a DOI, tag the commit, and declare the confirm set as data after the deposit date (prospective), with the historical confirm period relabelled "pseudo-out-of-sample". Run confirm in a separate, logged invocation. Refuse to write results from a dirty tree. (C2)
5. **Add a calibration test suite.** Simulate GARCH and regime-switching series with real indicator calendars; assert size at or below nominal for the shift test, bootstrap CI coverage, BY behaviour, SPA size under drift; add it to CI. (M11, M1, M3)
6. **Redo inference for slow indicators.** Episode as the unit; minimum number of episodes per period as the testability rule; volatility-standardised outcomes; drop or relabel as "untestable" every indicator with fewer than about 8 episodes. (M1, M2)
7. **Add baselines and controls.** Calendar/festival dummies, lunar phase, macro state and announcement days, placebo skies (shifted, tropical, scrambled rulerships); fix the SPA benchmark. (M3, M4, M5)
8. **State power honestly inside each paper.** BY-adjusted minimum detectable effects, TOST against a pre-stated smallest effect of interest taken from practitioner claims, project-level multiplicity statement. (M6, M12)
9. **Earthquake upgrade.** ISC-GEM + GCMT, ETAS declustering, mechanism-restricted tidal control (or drop the control), fix the offline time-zone bug, tighten the polygon, and pre-register the Varuna-mandala candidate against a global catalogue. (M7)
10. **Consolidate and narrow.** One rule engine (delete combinations/, remove the blanket except); workbench: signed targets, catalogue-level family size, a hard one-confirm-per-rule-lineage guard; commit snapshots that are legally committable and publish hashes plus fetch scripts for the rest; merge gold and silver into one paper; park numerology, remedy and mundane as "notes/not research" until they have data. (C6, M9, M13)

### 6.2 Questions for an external web-research agent

Data access
1. What is the current open, citable route to the daily LBMA Gold and Silver Price back to 1968 (Bundesbank series codes, WGC Goldhub terms, IBA academic licence)? Can a derived returns series be redistributed?
2. Exactly what is Yahoo GC=F (nearest contract or most active; settlement or last trade; how zero-volume days are reported)? Is there a free, documented, back-adjusted COMEX gold continuous series from 1975?
3. Which free intraday XAUUSD sources go back before 2010, and what are their redistribution terms?
4. Where can MCX gold daily history (2003+), IBJA rates and an India gold premium/discount series be obtained, and under what terms?
5. Are archived historical panchangas (e.g. Rashtriya Panchang, from 1957) available to validate computed festival dates, and how often do regional calendars disagree on Akshaya Tritiya and Dhanteras dates?
6. Licence compatibility: can an MIT repo depend on AGPL Swiss Ephemeris files, or should it move to JPL DE440 via SPICE/Skyfield?

Literature
7. Full list and effect sizes of peer-reviewed lunar-cycle return studies (Dichev & Janes 2003; Yuan, Zheng & Zhu 2006; Lucey 2010 on precious metals; later replications and failures to replicate, including post-publication decay).
8. Peer-reviewed tests of planetary or astrological variables on asset prices, including Novy-Marx (2014) and any studies of Mercury retrograde or eclipses and returns; what nulls and corrections did they use?
9. Evidence on Indian festival and wedding-season effects on gold prices, premia, imports and volatility (Akshaya Tritiya, Dhanteras, Pitru Paksha), and on the "autumn effect" in gold (Baur 2013).
10. Best current practice for inference with slow deterministic cyclical regressors: validity conditions for circular-shift tests under conditional heteroskedasticity and regime shifts; episode-level or cluster approaches; spurious periodicity regressions.
11. Standard specification for daily gold return and volatility models since 2015 (real yields, dollar, VIX/GVZ, GPR, ETF flows, central-bank buying): which variables and what explained variance should a referee expect?
12. What do recent papers require for data-snooping control in trading-rule studies (Reality Check, SPA, Romano-Wolf, MCS, deflated Sharpe, t > 3)?
13. Seismology: results of tests of lunar/solar/planetary periodicity in earthquakes (Hough 2018; Ide, Yabe & Tanaka 2016; Cochran, Vidale & Tanaka 2004; Kossobokov-style Molchan tests), CSEP standards for alarm-based forecasts, and the preferred declustering for Himalayan sequences.
14. Jyotish sourcing: exact verses (text, chapter, verse, edition, translation) for gold/commodity price claims in Brihat Samhita (argha-kanda, ch. 41-42), Vyapar Ratna and Bhavishya-phala literature; for earthquake claims in Brihat Samhita ch. 32; and which ayanamsa and node model each cited modern practitioner (Tempora, Merriman, Raman) actually uses.
15. Mundane: which national charts have archivally documented times (minute-level) and what are the primary sources; which event databases give exhaustive, dated political events suitable as denominators.
16. Venues: which journals have published pre-registered null results on calendar or behavioural anomalies in the last five years, and which accept Registered Reports in finance or geoscience?

---

## Appendix: reproduction of the exact-shift check

Script (pure Python, reads studies/gold_market/artifacts/overlay_frame.csv): scratchpad/exact_shift.py. Output:

- jupiter_debilitated, explore, absret: n = 3,462, active 198 bars in 2 runs (one transit), observed +29.82 bp, 2,663 admissible shifts, none as extreme, exact p = 3.75e-4, BY q (m = 42) = 0.068.
- jupiter_exalted, confirm, absret: n = 2,687, active 136, observed +38.2 bp, 1,888 shifts, exact p = 5.29e-4, BY q = 0.096.
- Jupiter-in-Capricorn episode starts in the data: 2008-12-09, 2009-07-30, 2020-03-30, 2020-11-20, 2021-09-14. Jupiter-in-Cancer: 2002-07-08, 2014-06-19, 2025-10-20, 2026-06-02.
- Explore-period autocorrelation of absolute returns: 0.097 (lag 1), 0.110 (5), 0.097 (20), 0.060 (60), 0.016 (120).
