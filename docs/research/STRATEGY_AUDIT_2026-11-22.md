# Strategy audit (red team), 2026-11-22

- Role: independent auditor. Design only. No code, plan, rule or data file was changed. This file is the only output.
- Goal audited (owner's words, ADR-007): test astrological principles on past data, per principle: valid or not, what effect size is ruled out, limitations; unbiased; modular; no forecasting.
- Read: ADR-004, ADR-006, ADR-007, OWNER_DECISIONS.md, FINDINGS_LEDGER.md, RESEARCH_REVIEW_2026-11-22.md, INCOMING_AUDIT_2026-11-22.md; code in `core/{domains, stats/{seal,episodes,volatility,equivalence,multiplicity,nulls,rates}, paperkit, rules/levels.py, markets/placebo.py, datasets/snapshots.py}`, `tools/check_paper_keys.py`, `scripts/fetch/`, `studies/mundane/hypothesis.yaml`, `studies/earthquake/hypothesis.yaml`, `data/registry/licences.yaml`, `data/snapshot_index.json`, `.gitignore`, `pyproject.toml`, the relevant tests. `core/` = `libs/vedic_astrology_core/`.
- Run: two small simulations against the existing functions (appendix A), to check two suspicions with numbers. Nothing else was executed.
- Not read line by line: `core/mundane/*` (4,500 lines), `tools/ingest/validate.py`, `markets/baselines.py`, `markets/festivals.py`, `stats/power.py`. Findings on those areas come from their ADR and plan text only and are marked "design".

Severity: **critical** = can by itself produce a wrong verdict or make the central guarantee false. **Major** = biases a verdict, or leaves it unconvincing to a sceptic or to a fair-minded astrologer. **Minor** = hygiene or wording.
Fix type: **design** (ADR or plan text), **code**, **owner** (a decision or an action only the owner can take).

## 0. Result in one page

| Area | Critical | Major | Minor |
|---|---|---|---|
| 1 Statistical validity | 5 | 8 | 3 |
| 2 Bias against astrology | 1 | 8 | 1 |
| 3 Bias for astrology | 0 | 6 | 1 |
| 4 Data | 0 | 6 | 3 |
| 5 Modularity and governance | 1 | 8 | 5 |
| 6 Other | 0 | 2 | 2 |
| **Total** | **7** | **38** | **15** |

The seven critical findings:

1. **S-01** The exclusion test and the bound X95 are not valid for skewed outcomes. Measured false "effect excluded" rate at a true effect equal to the SESOI: 13% to 36% at nominal 5%.
2. **S-02** The sign-flip support test is anti-conservative when neighbouring episodes share control bars. Measured size 8% to 10% at nominal 5%.
3. **S-03** "Adding a principle does not change old verdicts" is false for Benjamini-Yekutieli at a fixed M. Old tests can move from N to S.
4. **S-04** The family correction does not survive adaptive registration. After the first run the confirm period is public; a principle, variant or `use:` combination designed after that reuses a seen holdout for the price of one slot.
5. **S-05** Confirm-once is not enforced by what is built, and the built ledger does not implement what ADR-007 specifies.
6. **A-01** The placebo-sky check as coded cannot be passed by any principle that does not depend on sign labels (nakshatra, tithi, retrograde, combustion, conjunction by degree). Wired as R2, it blocks "Supported" for those.
7. **G-01** The pipeline that produces verdicts (`core/validity/`) and its calibration (WP-70) do not exist. No evidence yet that any verdict holds its stated error rate. The existing calibration tests cover components only, with symmetric noise.

What is sound is listed in section 7. The confidence statement and exit criteria are in section 8.

---

## 1. Statistical validity

### Critical

**S-01. Exclusion (verdict E) and X95 assume symmetric episode differences. Event counts, extreme-move flags, absolute returns and drought-year flags are right-skewed.**
- Evidence: `core/stats/equivalence.py:454-539` tests "effect at least the SESOI" by a sign-flip on `d - SESOI`; `core/stats/episodes.py:538-601` states coverage holds "whenever the differences are symmetric about the true mean". Under the support null (no effect) symmetry can follow from exchangeability. Under the exclusion null (effect = SESOI) nothing makes `d - SESOI` symmetric. For a right-skewed `d` the upper limit is too low.
- The tests that guard this use normal or Student-t noise only: `tests/test_stats_equivalence.py:138-149` (normal), `tests/test_stats_episodes.py:278-288` (named "skewed", but symmetric t), `:336-344`.
- Measured (appendix A, existing `episode_equivalence`, alpha 0.05, true effect = SESOI): normal 4.5% to 6%; exponential 13%; lognormal 16% to 22%; rare-event (10% of episodes carry an event) 23% to 36%.
- Consequence: false "Effect excluded above X" and an X95 that is too small. This is the number the owner asked for ("if not valid, how much"). It is biased against the principle exactly in the earthquake, flood, extreme-move and drought outcomes.
- Fix (design + code): per outcome type, name an interval method with proven coverage under skew. Event rates: a conditional exact or an episode-level Poisson/negative-binomial likelihood interval, or a studentised (bootstrap-t) cluster interval on a variance-stabilised scale. Flags: episode-level binomial model. Absolute returns: test on log or rank scale. Add to WP-70: false-exclusion rate at effect = SESOI at most 5% on **skewed and rare-event** simulators with 8 to 20 episodes. Until that passes, verdict E and X95 are not printed for these outcome types.

**S-02. Shared neighbour windows make consecutive episode differences positively correlated; the sign-flip test assumes independence.**
- Evidence: `core/stats/episodes.py:365-447`. The "after" window of episode k and the "before" window of episode k+1 are drawn from the same inactive gap whenever the gap is shorter than two windows; the default window is the episode's own length (`:411`). Both differences subtract the same bars.
- Measured (appendix A, i.i.d. normal outcome, no effect, one-sided 5%): active 5 / gap 5 bars: 8.1% (12 episodes), 7.7% (18); active 20 / gap 5: 9.9%; active 5 / gap 50: 5.1% (no sharing, correct).
- Consequence: inflated "Supported" for calendars with short gaps: retrograde cycles of Mercury, Moon nakshatra groups, tithi windows, eclipse windows. These are the fast indicators that are the only ones able to pass the gate (S-09).
- Fix (code + design): each inactive bar may serve one episode only (split the gap), or use non-overlapping matched blocks, or test by block permutation. Add a WP-70 case with gap shorter than the window. Decide the window and `merge_gap` in the plan, per calendar class, before outcomes.

**S-03. Stability claim of ADR-007 3.4 is false.**
- Evidence: ADR-007 3.4: "All corrections use M ... Empty slots count as p = 1. So adding a principle does not change old verdicts." BY is a step-up procedure: the threshold of a p-value depends on its rank. Example, M = 60 (rank-1 threshold 1.78e-4, rank-2 3.56e-4): a test with p = 3e-4 alone is N. Register any other test with p below 1.78e-4 and the first becomes S with no change to its own rule, data or plan. `core/stats/multiplicity.py:95-104` computes q from all p-values, as it must.
- ADR-007 section 9 then says "A verdict that changes without a rule, data, plan or engine change is a bug and fails the build". With cause `new_principle` allowed the two statements contradict.
- Controls registered as "control principles" (ADR-007 4.2, `core/domains/earthquake.py:207-232`) make this concrete: a detected positive control inside the family lowers the bar for every other test.
- Fix (design): choose one. (a) A procedure whose per-test threshold is fixed at registration: alpha-spending (online Bonferroni, for example alpha_i = alpha * 6 / (pi^2 i^2) or a declared weight table) or an online FDR rule valid under dependence. Old verdicts then never move and the stream of principles can be endless. (b) Keep BY at M but state plainly that verdicts can be gained when principles are added, never lost, and show it in the changelog. In both cases controls stay outside the family.

**S-04. Adaptive registration breaks the family guarantee and the holdout.**
- Evidence: ADR-007 3.3 B to D and 7.2: a new version, a candidate variant or a `use:` combination gets a new slot and its own one-shot confirm on the **same** confirm period. After the first sealed run the confirm-period effects of every principle are published (5.6 `effect.confirm`, cards, site). BY controls false discoveries for hypotheses fixed in advance, not for hypotheses chosen after seeing the data.
- Worked example at M = 60: register 43 unrelated tests. Under a global null the chance that the smallest p is at or below 0.003 is 1 - 0.997^43 = 12%. Then add 17 near-copies of the winner as candidate variants or `use:` children ("a named practitioner uses 10 degrees"). The BY threshold at rank 17 is 17 * 0.05 / (60 * 4.68) = 0.00303, so all 17 are "Supported". False-discovery rate about 12%, not 5%.
- Softer form of the same thing: any well-meaning astrologer who reads the first report and proposes "the same rule but only when the Moon is waxing" is tuning on the confirm period.
- Fix (design): (1) Freeze date per data vintage. Principles, variants and combinations registered after the first confirm run of a domain can be explored and limited on that vintage but cannot be "Supported" on it; they are confirmed only on a later vintage (new years of data, or an untouched dataset). (2) One discovery per lineage: variants and `use:` children of a lineage form a cluster; the cluster gets one test (min-p with a max-statistic permutation) and one verdict. (3) At registration compute the calendar correlation with every already-confirmed calendar; above a plan-fixed value the new test is marked "derivative" and inherits the freeze. (4) Card and summary state how many tests in the domain were registered before and after the first unblinding.

**S-05. Confirm-once is not enforced.**
- The built ledger and the designed ledger differ. `core/stats/seal.py:246-294` allows exactly one confirm per ledger **file**, "whatever plan hash or period" (`:258`). ADR-007 7.2 needs one confirm **per lineage version per test** in one file `studies/validity/confirm_ledger.jsonl`. With the built function the second principle ever confirmed raises; so WP-69 must write new keyed logic, which is the holdout-critical part and is not yet designed in detail.
- Ways around the built guard: (a) another `study_dir` is a fresh ledger (`seal.py:184-186, 274`; the docstring claim at `:13-15` holds only if the caller keeps the directory). (b) An entry that was never committed leaves no trace when the file is deleted; tamper detection reads git history only (`:205-243`), and history can be rewritten in a single-developer repository. (c) `data_sha256` is a caller-supplied string, not checked against a file (`:262`). (d) Outcomes can be read without the ledger at all: `DomainAdapter.outcomes` accepts any 64-hex string (`core/domains/base.py:214-220`); `EarthquakeDomain.catalogue()` and `mainshock_flags()` are public and ungated (`core/domains/earthquake.py:163-178`); the old study pipelines still run on the same snapshots. (e) ADR-007 7.2 lets a `--provisional` run from a dirty tree compute everything; nothing says a provisional run may not read the confirm period. (f) Lineage identity is the rule `id`; a renamed copy is a new lineage. (g) A "dated plan amendment" can change split, SESOI or M after results (S-12).
- Fix (design + code + owner): one ledger keyed by `(domain, dataset sha, period, lineage, version, variant, outcome)`, hash-chained like the lock; the gate hash checked against `gate.json` on disk and bound to the test id; adapters expose confirm-period outcomes only through a handle issued by `begin_confirm`; provisional runs get the explore period only; ledger entry committed and **pushed** (or externally timestamped) before outcomes are read; lineage identity includes a calendar hash, not only the id. Owner: deposit the plan hash, lock hash and ledger head outside the repository before each confirm (OSF registration as ADR-004 D-3 already decided, or a signed tag on a public remote). ADR-007 dropped that step without saying so; a sceptic has no way to verify "fixed before outcomes were read" from a repository its owner can rewrite.

### Major

**S-06. Estimand mismatch.** The card shows a pooled effect (rate ratio active against inactive time, mean difference in bp; ADR-007 5.2) and the SESOI is on that scale. The p-value, X95 and exclusion come from the unweighted mean of per-episode differences against local neighbours (`episodes.py:365`, `equivalence.py:454`). A one-bar episode weighs as much as a two-year one, and a rate **ratio** SESOI of 2.0 has no direct counterpart on the per-episode **difference** scale (most short episodes contain zero events). Fix (design): one estimand per outcome type, stated in the plan, used for estimate, interval, p, X and SESOI alike. Type: design.

**S-07. The rate-ratio interval in use is anti-conservative and already feeds exclusion statements.** `core/stats/rates.py:8-10` says the binomial interval "assumes a Poisson process, so it is anti-conservative for clustered events; use it for the interval, not for the test", which is backwards. The ledger's "for 8 of 13 earthquake indicators a doubling is outside the 95% interval" (FINDINGS_LEDGER 2.4) rests on it, and ADR-007 5.2 prints it "beside" the clustered interval. Fix: drop it from cards or label it "assumes independent events"; correct the docstring; re-derive the ledger statement. Type: code + design.

**S-08. Circular-shift test: known non-stationarity problem, and the routing rule is a forking path.** Review M1 stands: rotation needs a stationary outcome; gold volatility 1968 to 1998 is not (two-tier market, 1980, long decline). ADR-007 5.2 routes "calendar classes that fail calibration" to the sign-flip test; the class list is decided by simulation results (WP-70), by the same people, with simulators that may be kinder than the data. Fix (design): one primary p-method per outcome type fixed in the plan (episode-level), the shift test as a sensitivity cell; the routing table hashed in the plan before any real outcome. Type: design.

**S-09. At the proposed budgets the support test is unattainable for most of the design; this is not shown per domain.** Rank-1 thresholds: 1.78e-4 at M = 60, 2.92e-4 at M = 40. Sign-flip needs at least 13 (M = 60) or 12 (M = 40) episodes in the **confirm** period, not 8 (G4). Gold daily confirm (1987 to 1998, about 3,000 fixings): the shift test can never reach 1.78e-4, whatever `min_shift` (floor about 1/3,000). Monthly gold and silver confirm (about 300 months): shift test never; sign-flip only for calendars with 13 or more runs in 25 years on a monthly grid, most of which are Sun-sign calendars that fail R4. Monsoon confirm (56 years, unit = year): shift never; 12 separate active runs in 56 years is borderline. So "Supported" is realistically reachable only for fast calendars on daily gold and hourly earthquakes. The silver domain can only limit. Fix (design): the gate report prints, per domain before any run, the share of registered tests that can support; budgets are set per domain with that table in view; consider S-14. Type: design + owner.

**S-10. No correction across domains or across the three verdict families.** Each of six domains runs BY at 0.05, separately for support, opposite and equivalence (ADR-007 5.4). A principle listed under several domains in `tests:` has several chances. The project-wide count is only printed (3.4 last row). Fix (design): the summary states the expected number of false S, C and E across the whole run set; either split alpha across domains or state that error control is per domain and per verdict type, in the summary's first paragraph. Type: design.

**S-11. X95 is unadjusted but the verdict text asserts it for every card.** "Effects above X95 are ruled out" (5.4 rows E and N) is a per-test 95% statement; over 60 cards about three are expected to be wrong even when the interval is valid. Fix: verdict sentences cite X-strict; X95 is shown as the per-test value with that label. Type: design.

**S-12. Operational forking paths not yet closed.** Still "proposals" (ADR-007 4.2): split dates, SESOI, M, sampling instant and place, completeness rule, primary declustering, `merge_gap`, neighbour window, the "local baseline" of nearby inactive years for monsoon, the R4 threshold 0.8, the R3 80% rule, the calendar-class routing. OWNER_DECISIONS H16 is "default adopted, pending owner review" and runs made under a default are merely "labelled". A default that the owner can overturn after a confirm run is a forking path. Fix (owner + design): no confirm run under a "default adopted" decision; every item above is a key in the hashed domain plan; plan amendments after the first confirm apply to the next data vintage only. Also: H16 cites "ADR-007 section 5"; the values are in section 4.2. Type: owner.

**S-13. Earthquake SESOI was proposed after the answer was known.** FINDINGS_LEDGER 1.4 and 2.4 already report that a doubling lies outside the interval for 8 of 13 indicators. ADR-007 4.2 then proposes "rate ratio 2.0" as the SESOI and tests exclusion on the whole (seen) period. The same holds for gold: 25 bp a day against a known detectable range of 11 to 30 bp. The asymmetry argument of ADR-007 section 2 ("tuning can only inflate") covers tuning by a proponent; it does not cover a threshold chosen by the project with the results in view. Fix (design + owner): SESOI justified in the plan from sources outside this project's results (practitioner elicitation made blind, or published comparable effects); on data the project has already analysed, verdict E carries a flag `sesoi_post_hoc`, or E is reserved for unseen data. Type: design + owner.

### Minor

- **S-14.** ADR-007 section 14 rejects whole-period support "because the project has already looked at the explore years". That is true for Yahoo gold and the earthquake catalogue, not for the Bundesbank series or IITM rainfall, which have not been analysed here. For a rule whose encoding is frozen and attested before the data are opened, whole-period support is legitimate and would more than double the evidence. Consider a declared class "prespecified, never tuned" for unseen datasets. Type: design.
- **S-15.** `episodes.testable` defaults to `alternative="two-sided"` (`episodes.py:307`) while ADR-007 tests the claimed direction; the gate and the test must use the same side. `episode_differences` silently drops episodes with no usable neighbour (`:418`), so the test can run on fewer episodes than the gate counted. Type: code.
- **S-16.** The GARCH-X test with 199 shifts has a floor of 0.005 and can never pass a family threshold (`volatility.py:226-232`); label it secondary in the plan. Type: design.

---

## 2. Bias against astrology (what a fair-minded practitioner would reject)

### Critical

**A-01. Placebo skies: ties count against the real sky, and two of the three placebo kinds leave many indicators unchanged.**
- Evidence: `core/markets/placebo.py:147-161`: rank = 1 + number of placebos **greater than or equal to** the real statistic. `:12-17`: the tropical placebo leaves retrograde, combustion and tithi unchanged; the scramble placebo leaves nakshatra columns unchanged (and any degree-based aspect or conjunction, since only sign labels are permuted). For such an indicator every placebo equals the real sky, rank = n + 1, p = 1.
- ADR-007 5.3 R2 requires "top 5% of at least 200 placebo skies (time-shifted, tropical, scrambled labels)" for verdict S. As coded, the Moon-mandala principles (nakshatra), tithi principles, stations, combustion and orb conjunctions can never pass. The tropical "placebo" also has one deterministic draw (`:249-252`), so "top 5% of 200" is undefined for it.
- Second issue, modularity: the statistic compared is the **maximum over all indicators** (`:164-168, 222-233`). If R2 is computed on a family, adding a principle changes R2 for the others.
- Third issue: the tropical zodiac is a rival astrological system (the ledger's own disputes list tropical against sidereal dates). It is a variant, not a placebo.
- Fix (design + code): R2 per test, on that test's statistic only; a placebo kind applies only if it changes the calendar (otherwise "not applicable", not "failed"); strict ties do not count against the real sky, or identical placebos are dropped; tropical moves to the sensitivity grid; time-shift placebos come in two declared sets, whole-year shifts (keep the Sun and the season) and others (F-01).

### Major

**A-02. Verdicts at L2 will be read as verdicts on astrology.** ADR-007 5.5 allows family entry at L2 ("as encoded by the project; the source has not been checked at the page"). The ledger records "rule without a text" cases (`shukra_guru_wealth.yaml`, `venus_own_sign.yaml`), conflicting orbs (8, 13, 15 degrees for Mars-Ketu), fabricated quotes in the collected sources (INCOMING_AUDIT, round 4 D4: 49 of 54 quotes absent from the cited page). A "Contradicted" or "Effect excluded" on a project-invented encoding is a result about the project. Also, code still says L3 (`core/rules/levels.py:47` `FAMILY_MIN_LEVEL = 3`) while F-8 says L2. Fix (design): below L4 the verdict words change ("Encoding not supported", "Encoding: effect excluded above X"); the cross-domain summary counts L4 and above in the main table and lower levels in a separate one; no total across levels. Type: design + owner (L2 decision is still "default adopted").

**A-03. Reading the text backwards.** Brihat Samhita ch. 32 classifies an earthquake after it happens; the study tests the mandala as a trigger (`studies/earthquake/hypothesis.yaml` indicator notes; ledger 5; ADR-007 3.2 `reading` block). The `reading` field records it, but the test still takes slots, yields a verdict with the principle's name, and its one "loose end" (Varuna) drives a planned follow-up. The membership lists are also unchecked against the Bhat edition (same file: "should be checked against a translation"; INCOMING_AUDIT: Brihat Samhita rows do not match the scan). Fix (design): when `reading.kind` differs from `reading.text_says`, the card title is the project's hypothesis ("project hypothesis derived from BS 32"), the source's name is not in the verdict line, and the test is excluded from any count "of classical principles". Add a test of the text's own claim if it can be operationalised (consequences by mandala), or list it under "what was not tested". Owner: H11 page check before registration, not after.

**A-04. Single-rule encoding of a system that practitioners apply by synthesis.** Classical rules come with strength conditions, cancellations and a reference chart (new-moon or sankranti chart for a capital, the year chart, Ardra-pravesha for rain, a national chart). The gold family has no chart at all (review M8). `use:` joins conditions by AND/OR only; there is no graded strength, no cancellation, no chart-relative house. Fix (design): every card carries the generated line "tested as a single condition without the cancellations and strength rules the tradition applies"; a declared route for "synthesis" principles (a deterministic scoring function supplied by a practitioner, frozen and hashed before data, tested as one principle); the summary never states or implies coverage of the tradition. Type: design.

**A-05. Timing and place conventions.** (a) The sky is sampled at the fixing instant in London or Frankfurt (ADR-007 6, WP-76). The panchanga convention ties the day's tithi and nakshatra to local sunrise at a place in India. The Moon moves about 13 degrees a day; for Moon-based principles the two conventions disagree on a large share of days. (b) Classical price chapters speak of months or seasons and of goods in a locality, not of the next day's return of a London or Frankfurt fixing in marks. (c) All-India seasonal rainfall dilutes region-specific rain rules; Kurma-chakra region assignment is omitted. Fix (design): `operationalisation` must include `day_convention`, `place`, `horizon` with `fixed_by`; where the source implies a horizon or region, the primary outcome uses it (monthly outcome for monthly claims, subdivision rainfall for regional claims) and the daily or all-India test is a sensitivity cell. Type: design.

**A-06. Currency and market of the gold outcome.** The only verified daily series is the Frankfurt fixing in DEM per kg, 1968 to 1998 (ADR-007 4.2; `scripts/fetch/bundesbank_gold.py`). Its daily changes mix gold with the DEM exchange rate (1969 and 1971 revaluations, the float). For 1968 to about 1990 the Indian gold price, which is what Indian practitioners talk about, was cut off from the world price by the Gold Control Act. Converting to USD needs a daily FX series fixed at a different time of day (D-02). Fix (design): state on every gold card which market and currency the claim is about and which was tested; gold in DEM and gold in USD are different declared outcomes; a null in DEM is not printed as a null "on gold". Type: design.

**A-07. Power asymmetry between support and exclusion.** Support uses the confirm part only, needs 12 to 13 episodes there and four robustness checks. Exclusion uses the whole period against a large SESOI. With true effects that are real but below the SESOI the design returns "Effect excluded above SESOI", which reads as negative. Fix (design): the gate computes the probability of S if the true effect equalled the SESOI; below 80% the card carries `support_underpowered` beside any E or N, and the verdict sentence for E says "effects at or above the project's threshold" (not "of the claimed size": sources rarely state a size, ADR-007 5.4 row E). Type: design.

**A-08. Disputed direction.** Where schools disagree on the sign (ledger 8, "opposite rules"; `rules/**/DISPUTES.md`), a directional test turns one school's support into "Contradicted" for the other. Fix: `expected_effect.direction` gets `fixed_by`; a disputed direction is tested as `either` or as two lineages named after their sources. Type: design.

**A-09. Baselines that are themselves astrological.** Festival days (WP-06; `core/markets/festivals.py`) are defined by tithi and solar month. Removing a festival effect removes exactly what a tithi-based gold principle claims, through the channel of people acting on the calendar. The tidal "positive control" is new or full Moon, which is also a registered silver principle (purnima, amavasya). Fix (design): each card shows the effect with and without the socially mediated baselines and says which claim was tested ("an effect beyond what festival buying explains"); a principle with a known physical or social channel carries a `known_channel` flag, and its support is not counted as support for astrology in the summary. Type: design.

### Minor

- **A-10.** The L4 review is one named person with a self-declared `blind_attestation: true` (`levels.py:169-182`). After the first report every reviewer can see results, so later reviews cannot be blind, and "unfaithful" can become an exit after a null (or "faithful" after a hit). Fix: the scope line says "attested faithful before the result" only if the review commit predates the confirm ledger entry; later reviews are shown with their date. Type: design + code.

---

## 3. Bias for astrology

### Major

**F-01. Season confounding passes two of the four robustness checks by construction.** Circular shifts and time-shift placebos (`placebo.py:112-130`, offsets 400 to 3,650 days, not whole years) break the alignment with the season. A Sun-linked calendar tested on a seasonal outcome (monsoon rain, floods, festival-season gold demand) will beat every such placebo and every shifted calendar because of the season alone. Only R1 and R4 stand in the way, and R4 is a single threshold (association below 0.8) with no stated measure. Partial confounding passes: Mercury and Venus stay within 28 and 47 degrees of the Sun, eclipse seasons drift slowly, solar-month-based tithi rules. Fix (design): for any calendar with non-zero seasonal association the null and the placebos use whole-year shifts (or permute years); R4 reports the share of calendar variance explained by all baselines jointly and the plan fixes the measure; the effect is estimated within season strata. Type: design + code.

**F-02. Other physical proxies.** The lunar node cycle (Rahu and Ketu, 18.6 years) is the lunar nodal tide cycle; Jupiter's period (11.86 years) is close to the sunspot cycle; tithi is the spring-neap tide. A "Supported" on these would have a non-astrological reading. Sunspot number is a declared monsoon control; the nodal cycle is not; ONI starts in 1950 and the long Nino 3.4 snapshot starts in 1948 (`data/snapshot_index.json`), so the explore period 1871 to 1960 has almost no ENSO control while the confirm period has it. Fix (design): add an 18.6-year term and a solar-cycle term as baselines in monsoon, flood and earthquake; a long ENSO reconstruction is required before the monsoon plan is sealed, or the split is moved so both parts have the same controls; the `known_channel` flag of A-09 applies. Type: design + data.

**F-03. Sources that postdate the data.** A practitioner rule published in 2010 and tested on 1968 to 1998 is being tested on data its author could see. Review C6 found exactly this (a rule "from a 53-year study of the same series"; a 2016 call inside the confirm period). ADR-007 has no check. Fix (design + code): `source.published` is required for a `tests` block; if the confirm period is not entirely after it (classical texts pass trivially), the test cannot be "Supported"; the card says "the source could have been fitted to these years". Type: design + code.

**F-04. The encoder knows history.** Rules are written and operationalised by people and language models that know when gold peaked and when large earthquakes happened (review, "checked and found sound", last clause). Choices marked `fixed_by: project` can lean either way. Fix (design): for each `fixed_by: project` choice the alternative values go into the sensitivity grid automatically; choices are made from the source text and recorded before the calendar-outcome join; where possible the encoder of a rule is not the person who has run the domain. Type: design.

**F-05. The pseudo-out-of-sample flag does not limit the verdict, and it is missing where it applies.** ADR-007 5.4: flags "never change" the verdict. The earthquake confirm period has been examined in full, including the Varuna result (RR 1.89, p = 0.010, ledger 7). The monthly Pink Sheet confirm period "from 2000-01" is the same market and years as the Yahoo study (2000 to 2026) whose per-indicator effects are published on the site (`site/data/results.json`, `site/data/market_gold.json`); ADR-007 does not flag it. Fix (design): on a seen confirm period the best verdict is N with a flag ("signal on seen data"), and support needs unseen data (the global catalogue test of ledger 7; future years); set `pseudo_out_of_sample` for monthly gold and silver. Type: design.

**F-06. Fishing across outcomes and domains.** A rule may list any domains and outcomes in `tests:`; gold has five outcomes on two datasets. Each takes a slot, which is right, but nothing ties the list to the source's claim. Fix: each `tests` entry cites the words of the source that justify that outcome and direction; an entry without them is labelled "project extension" and counted separately. Type: design.

### Minor

- **F-07.** R3 passes when the effect has the same sign in 80% of cells, but four of the cells are ayanamsas within about 1.5 degrees of each other (`placebo.py:52`), so most cells are near-copies of the primary. Count distinct calendars (cells that change at least a stated share of active bars), not cells. Type: design.

---

## 4. Data

### Major

**D-01. Monthly Pink Sheet prices are monthly averages.** Returns of averaged prices have built-in positive serial correlation and reduced variance, and a monthly average cannot be aligned with an ingress or a lunar phase inside the month. Fix (design): say so in the domain plan; test only principles whose calendars are meaningful at one month; adjust the inference for the induced autocorrelation; do not treat it as a cross-check of a daily result. Type: design. (To verify at the source: the Pink Sheet documentation.)

**D-02. DEM to USD splice.** Not yet specified (WP-76; fetch script docstring). Risks: FX fixing at another hour and city than the gold fixing, holiday mismatches creating artificial returns, regime change in 1971 to 1973. Fix (design): DEM is the primary outcome as fetched; USD is a declared second outcome with the FX source, fixing time and the gap rule in the plan; returns over mismatched days are dropped by rule, not by inspection. Type: design.

**D-03. Earthquake catalogue.** (a) The region is hand-digitised "approximation of a published fault trace, not a published polygon" (`studies/earthquake/hypothesis.yaml` region.provenance) and includes Tibetan rift events (review M7). (b) 1,563 of 1,645 magnitudes are converted from mb. (c) The cross-check extract disagrees in size: 259 ISC lines against 183 USGS at M 5.5 in the same box (INCOMING_AUDIT round 4), because the ISC filter matches any agency's magnitude. (d) Gardner-Knopoff leaves the 2015 Mw 7.3 in as a mainshock. (e) The adapter picks "the newest snapshot made for this plan" when none is pinned (`core/domains/earthquake.py:95-103`). (f) Completeness changes by decade, which is a time trend that shifted calendars do not share. Fix (design + code): pin the snapshot hash in the plan; a published regionalisation as a sensitivity cell; single magnitude type before the ISC comparison; ETAS (WP-26) before any support claim; decade strata in the rate model. Type: design + code.

**D-04. Reproducibility of hash-only data.** `data/snapshots/*` is git-ignored and every index entry has `committed: false`, including public-domain and CC0 files. USGS ComCat and provider APIs revise their content, so a later fetch will not reproduce the hash and an outside reader cannot rerun a verdict. No licence has been read (`licences.yaml`: every `verified: false`; H4 open), so every dataset is grade B at best. Fix (owner + code): read the licences (H4); commit or deposit (Zenodo) every snapshot whose terms allow it; for the rest keep an owner-held archive and publish derived, non-reconstructing tables where the terms allow. Type: owner.

**D-05. Dataset grade inputs are hand-set.** ADR-007 4.1 and `base.py:12-14` say grades are "never written by hand", but `reproduced`, `open_items` and `quality_flaws` are constructor arguments (`base.py:44-56`, `earthquake.py:67-76`). Passing `reproduced=True` and omitting a flaw yields grade A. Fix: these come from committed registry files with a date and a named checker; the adapter cannot override them. Type: code.

**D-06. Rainfall and flood series.** IITM ends in 2016 and its licence is unclear; DFO starts in 1985, is news-based and grows with reporting; floods are strongly seasonal and tied to ENSO. "Percent of the long-period average" and a centred 31-year running mean both include the year being tested (and future years), which pulls the anomaly toward zero. Fix (design): leave-the-year-out baselines; year strata for DFO as planned plus a reporting-trend term; no extension of IITM with another agency's series without a declared splice test. Type: design.

### Minor

- **D-07.** Frankfurt series: confirm the fixing time, the treatment of "." days, and the two-tier period (1968 to 1971) in the plan. Type: design.
- **D-08.** `check_paper_keys.check_stale` accepts any hash present in the snapshot index, not the hash the plan names (`tools/check_paper_keys.py:155-166`). Type: code.
- **D-09.** In-house festival dates need an external spot-check table before use (the rejected incoming file failed in leap-month years; INCOMING_AUDIT round 4 D1). Type: code + owner.

---

## 5. Modularity and governance

### Critical

**G-01. The verdict pipeline and its calibration do not exist yet.** `core/validity/` and `studies/validity/` are absent; WP-65 to WP-74 are open. The existing calibration suite (`tests/test_stats_calibration.py`, `tests/simulators.py`) is untracked in git and covers returns only (GARCH, regimes, long memory): no clustered events, no rare events, no yearly unit, no shared-neighbour case, no skewed episode differences. `core/domains/simulated.py` is i.i.d. Gaussian. Findings S-01 and S-02 show what such gaps hide. Fix: WP-70 acceptance is extended as in section 8 and is the gate for any real-data run; the suite and simulators are committed before the code they certify. Type: code + design.

### Major

**G-02. The seal does not cover the environment or ignored inputs.** `require_clean_tree` (`seal.py:94-122`) stamps commit and dirty flag only. Not covered: package versions (`pyproject.toml` allows numpy 1.21 to 3, pandas 1.3 to 4, scipy 1.7 to 2, pyswisseph 2.10 to 3; bytecode for Python 3.10, 3.12 and 3.14 is present), the ephemeris model and files (review M10: "swieph" and "moshier" on one machine), git-ignored files. One ignored rule file exists on disk: `rules/mundane/experimental/ch9.capital_saturn_transit_clock.yaml` (last line of `.gitignore`); a rule loader that globs `rules/` would read it from a "clean" tree. `.gitignore` also lists `docs/research/FINDINGS_LEDGER.md` and `ops/requirements.lock.txt` although both are tracked. Fix: the stamp includes interpreter and package versions (or the lock hash, with the run refusing an environment that differs from the lock), ephemeris model and ephemeris file hashes, and the hash of every file the run opened; the run fails if it reads a file git does not track, other than snapshots listed in the index; remove the three ignore lines or delete the file. Type: code + owner.

**G-03. Module-name collision between study scripts.** `core/domains/earthquake.py:44-55` puts `studies/earthquake/scripts` first on `sys.path` and imports `pipeline`, `indicators`, `robustness`, `decluster` by bare name. Six study folders have a `pipeline.py`. In one process (`astro-validity all`) whichever was imported first wins. Fix: import by file path under a unique module name, or move the needed functions into `core/`. Type: code.

**G-04. `use:` does not pin the parent.** ADR-007 3.2 shows `use: seismic.mangal_ketu_primary` with no version. Editing the parent changes the child's calendar with no edit to the child. WP-65 names the risk but its acceptance does not require a pin. Fix: `use: id@version` with the parent's file hash stored in the lock; a parent change makes a new child version explicitly. Type: design + code.

**G-05. Engine and predicate fixes after a confirm.** ADR-007 section 9 stops the run when stored numbers do not reproduce, and allows cause `engine_changed`. It does not say whether recomputing a confirm after a bug fix is a second look. Fix (design): recomputation after an engine fix is allowed once, both results stay on the card with the diff of the calendar (bars changed), and the flag `recomputed_after_confirm` is set; a fix proposed after seeing the confirm result needs a second person's sign-off or is deferred to the next vintage. Type: design.

**G-06. Random streams.** Review (minor list): "one shared rng is consumed sequentially, so adding an indicator changes every other p-value". ADR-007 does not require otherwise. Fix: each test derives its seed from the hash of its test id and the plan seed; WP-69 acceptance adds "adding a test leaves every other test's numbers bit-identical". Type: code.

**G-07. Two multiplicity schemes and two verdict vocabularies for national charts.** ADR-006 5.3 uses omnibus tests, hierarchical BY, Romano-Wolf, budgets 24/60/200 and at least 3 expected events; ADR-007 uses flat BY at M and at least 5. WP-80 "maps" one to the other. The same factor could be "effect found" in one and N in the other. With 5 expected Indian mainshocks and a confirm floor of 30 events (`studies/mundane/hypothesis.yaml`), this domain is descriptive for the foreseeable future. Fix (design): one scheme; until then the national-chart domain reports U with its reason and no mapping. Type: design.

**G-08. The results-key gate can be passed with bare numbers, and results files are not authenticated.** `tools/check_paper_keys.py:44`: the number pattern skips any number preceded by `-`, `.`, `/` or `$` (so "-29.8", ".03", "$0.01$" pass), and everything inside backticks, fenced blocks and link text is blanked first (`:52-69`). Numbers as words pass. `check_dirty` trusts `provisional` and `git.dirty` fields inside a JSON file anyone can edit (`:117-125`); `--no-provenance` switches both checks off (`:188-192`). The planned deny-list is a list of banned words; paraphrases ("confirmed", "debunked", "no evidence for astrology") pass. Fix: generated pages contain no free prose with numbers at all (templates only; the gate checks that the page equals the template render); results files are verified against the hash in the run manifest and the hash-chained changelog; verdict sentences are an allow-list of exact strings, not a deny-list. Type: code.

**G-09. Levels are computed from hand-typed flags.** `levels.py`: L1 needs `checked_by` and `checked_on` strings (`:127`); L3 counts fixture files, and a JHora fixture with no `agrees` key counts as agreeing (`:254`: `is not False`); the 1-arcminute and 5-arcsecond tolerances are not checked by code; L4 compares reviewer and author by name string (`:175`). Fix: fixtures carry the numbers and the code checks the tolerance; `agrees` must be `true`; reviews are signed commits by a second identity or carry an external reference. Type: code.

### Minor

- **G-10.** `studies/earthquake/hypothesis.yaml:1-13` still opens with "Pre-registration ... Written before pipeline.py was run" and `status: registered`, against ADR-004 D-2 and review C2. The new adapter reads this file. Type: code (text) + plan amendment.
- **G-11.** A legitimate unbounded X95 is `inf`; `paperkit.format_number` raises on non-finite values (`paperkit/results.py:38-39`). Define an explicit `unbounded: true` in the record so nobody substitutes a number. Type: design + code.
- **G-12.** Budget exhaustion: 14 gold indicators on five outcomes is 70 slots, above the proposed 60, before the 25 files in `rules/financial`. Who gets a slot when the budget is short is a selection step with no rule. Fix: S-03 option (a), or a written priority rule fixed before registration. Type: design.
- **G-13.** `swe.set_sid_mode` is process-global (`placebo.py:60`, `ayanamsa.py:87`). Safe today because every calculation resets it (`ephemeris.py:140-142`); unsafe with threads. State "no threads" in WP-69 or guard it. Type: code.
- **G-14.** Working tree today: modified `stats/equivalence.py`, `stats/power.py`; untracked `markets/baselines.py`, `markets/festivals.py`, `tests/simulators.py`, `tests/test_stats_calibration.py`. Nothing sealed can run until these are committed. Type: owner.

---

## 6. Other

**O-01 (major). What "valid" means is not defined against a causal channel.** A supported lunar-phase or Sun-sign principle may reflect tides, seasons or people following the almanac. The owner's question ("do astrological principles hold") needs the report to separate "the calendar predicts the outcome" from "beyond known physical and social channels". See A-09 and F-02. Fix: two labelled columns on the card and in the summary. Type: design.

**O-02 (major). Selection of principles is not a sample of astrology.** The tested set is what was easy to encode, what an AI collector found, and what the project wrote itself. Counts such as "0 of N supported" will be read as a rate for the tradition. Fix: the summary's first table is the sampling frame: how principles entered (text, practitioner, project), how many candidates were not encodable, not sourced, or untestable; no percentage over the whole set. Type: design.

**O-03 (minor).** The site already shows price-derived series and indicator overlays for 2000 to 2026 (`site/data/market_gold.json`, `pinksheet_monthly.json`, `earthquake.json`). ADR-007 7.2 says no confirm-period number reaches the site before its sealed run; for these periods that is no longer possible. Record it in the plans (F-05). Type: design.

**O-04 (minor).** Positive controls that are known in advance to be undetectable (tide: detectable ratio 1.4 to 1.5 against a real effect of a few percent; ledger 3.1) will stamp `control_not_detected` on every earthquake card without adding information. Add a planted-effect recovery control on the real calendar and real outcome noise (inject an effect equal to the SESOI and show the pipeline finds it at the stated power), per domain. Type: design.

---

## 7. What was checked and found sound

- The core idea: one pipeline, a gate that reads no outcome, verdict as a pure function, every test published, X reported beside every verdict, "not supported" kept apart from "excluded".
- The exclusion test has the right direction for a directional claim: H0 is "effect at least the SESOI", rejected only when the data lie below it; two-sided margin for `either` (`equivalence.py:420-431, 496-508`).
- Support and exclusion p-values are returned raw so one family correction can be applied to both (`equivalence.py:44-48`).
- BY implementation (`multiplicity.py`); attainable-minimum-p logic and exact enumeration (`nulls.py`, `episodes.py`); no normal approximation with few clusters; unbounded interval when episodes are too few.
- Past-only volatility: values at t use data to t-1, tested (`volatility.py:99-173`); no silent fallback when `arch` is missing.
- The run seal has no environment-variable bypass, counts untracked files, writes the ledger entry before computing, takes the confirm window from the plan (`seal.py`).
- Fetch scripts download from the provider with a generic client name and store bytes unchanged; hashes match the audit.
- Paper-kit accessor raises on missing and null keys.
- The mundane plan is explicit about its ceiling ("descriptive only"), its forbidden inputs and its pseudo-out-of-sample label.
- The ADRs already name several limits honestly (few episodes, L0 to L2 rules, DEM series, seen earthquake confirm period, SESOI as a judgement).

---

## 8. Confidence statement and exit criteria

### What must be true to be confident in a verdict

1. **Each test holds its error rate on data shaped like the real data.** Shown by simulation with the real calendars: clustered rare events, skewed outcomes, regime-switching volatility, yearly units, short gaps between episodes.
2. **The interval behind X covers.** At least 95% (one-sided) on the same simulators, at 8 to 20 episodes.
3. **The family guarantee survives the way principles are added.** Either thresholds fixed at registration, or a freeze per data vintage; no "Supported" on a holdout that was public when the test was designed.
4. **The holdout was shut, and that can be shown to an outsider.** Keyed ledger, gated access in code, plan and lock hashes deposited outside the repository before the confirm.
5. **Every choice the source does not fix is declared before outcomes, and its alternatives are shown.** Including SESOI, split, budget, day convention, place, horizon.
6. **A fair-minded practitioner has agreed in advance that the encoding and the outcome are what the source claims** (L4, dated before the confirm), or the card says in its verdict words that only the project's encoding was tested.
7. **Season, tide, solar cycle, nodal cycle, ENSO and almanac-following are separated from the claimed effect,** or the card says they are not.
8. **The run can be repeated by someone else:** data bytes available or deposited, environment pinned and stamped, results files tied to the run by hash.
9. **The report cannot say more than the numbers:** fixed sentences only, sampling frame first, no totals across citation levels.

Today items 1 to 4 are not met (S-01 to S-05, G-01), items 5 to 7 are partly designed and partly open (S-12, S-13, A-02 to A-09, F-01 to F-05), items 8 and 9 are partly built (G-02, G-08, D-04).

### Exit criteria for this audit loop

A real-data confirm run may start only when all of the following hold.

| # | Criterion | Closes |
|---|---|---|
| E1 | Zero critical findings open. Zero major findings open, or each remaining major has a written owner acceptance that is printed as a limitation on every affected card. | all |
| E2 | Full-pipeline calibration (WP-70, slow run, at least 2,000 simulated families per case) passes at nominal size on every outcome type: "Supported" in at most 5% of null families (upper 95% binomial bound at or below 6%); "Contradicted" likewise; "Effect excluded" in at most 5% of tests at true effect = SESOI; X95 one-sided coverage at least 95%; each on Gaussian, heavy-tailed, **right-skewed, rare-event and clustered-event** simulators, with 8, 12 and 20 episodes, with and without shared-gap calendars, with seasonal outcomes for Sun-linked calendars. | S-01, S-02, S-08, F-01, G-01 |
| E3 | Power check: at a planted effect of twice the gate's minimal detectable effect, "Supported" in at least 80% of runs for tests the gate called supportable; planted-effect recovery control defined per domain. | A-07, O-04 |
| E4 | Sequential rule decided and tested: adding a test leaves every other test's numbers and verdict bit-identical (or the documented monotone exception), including random streams. The adaptive-clone scenario of S-04 is a test and yields at most 5% false discoveries. | S-03, S-04, G-06 |
| E5 | Confirm ledger keyed per test, hash-chained, with tests for each bypass listed in S-05 (other directory, deleted uncommitted entry, fake gate hash, direct adapter access, provisional run, renamed lineage). Plan, lock and ledger-head hashes deposited externally and the deposit reference stored in the run manifest. | S-05 |
| E6 | Domain plans sealed with no "proposal" and no "default adopted" item: SESOI with its outside justification, split, M or alpha-spending table, estimand per outcome, p-method per outcome, windows, merge gap, R1 to R4 measures and thresholds, placebo sets, baselines. Owner sign-off recorded with date (H16, H17, L2, Support). | S-06, S-09 to S-13, A-01, F-07 |
| E7 | Rule schema requires and the register step enforces: `reading`, `operationalisation` (with day convention, place, horizon), `source.published`, direction with `fixed_by`, justification per `tests` entry, pinned `use: id@version`. Verdict wording by level and the `known_channel`, `support_underpowered`, `sesoi_post_hoc` and seen-holdout rules are in the verdict function with a table test. | A-02 to A-09, F-03 to F-06, G-04 |
| E8 | Data: licences read (H4); snapshot hash pinned in each plan; grade inputs come from committed registers; snapshots committed or deposited where allowed; monthly-average and currency caveats in the plans; leave-one-out baselines for rainfall. | D-01 to D-06 |
| E9 | Seal stamp includes environment, ephemeris model and file hashes and the list of files read; a run that reads an untracked file fails; module-name collision removed; the three `.gitignore` lines resolved; working tree committed. | G-02, G-03, G-14 |
| E10 | Report gate: generated pages are template renders only; results verified against the run manifest; verdict sentences from an allow-list; summary opens with the sampling frame and the expected number of false verdicts across domains. | G-08, S-10, S-11, O-01, O-02 |
| E11 | A second audit pass (a different reviewer or model than the author of the fixes) re-runs appendix A and the E2 suite from a clean clone and finds no new critical or major item. | loop |

Until E1 to E11 hold, any number produced on real data is provisional and should be labelled so.

---

## Appendix A. The two simulations

Run with the repository's own functions, unchanged. Script kept outside the repository (session scratchpad); the logic is short enough to restate as tests.

**A.1 False exclusion at a true effect equal to the SESOI** (`episode_equivalence(d, sesoi=0.5, alpha=0.05)`, `d = 0.5 + e`, `e` with mean zero, 800 replications, seed 1):

| Noise `e` | 10 episodes | 13 episodes |
|---|---|---|
| Normal(0, 1) | 0.060 | 0.045 |
| Exponential(1) - 1 | 0.136 | 0.129 |
| Bernoulli(0.1)/0.1 - 1 (rare event) | 0.355 | 0.228 |
| Lognormal(0, 1) - e^0.5 | 0.217 | 0.163 |

Nominal rate 0.05. Three binomial standard errors at 800 replications: about 0.023.

**A.2 Size of the sign-flip support test with shared neighbour windows** (`episode_differences(ind, y, merge_gap=0)` with the default window, then `sign_flip_test(d, alternative="greater")`, reject at p <= 0.05; outcome i.i.d. Normal(0, 1), no effect; periodic calendar; 1,500 replications):

| Active bars | Gap bars | Episodes | Rejection rate |
|---|---|---|---|
| 5 | 5 | 12 | 0.081 |
| 5 | 5 | 18 | 0.077 |
| 20 | 5 | 12 | 0.099 |
| 5 | 50 | 12 | 0.051 |

Three binomial standard errors at 1,500 replications: about 0.017. Expected from theory for the 5/5 case: correlation 1/6 between consecutive differences, size about 7.7%.

## Appendix B. Arithmetic used

- Harmonic numbers: H(40) = 4.279, H(60) = 4.680. Rank-1 BY thresholds: 0.05 / (40 * 4.279) = 2.92e-4; 0.05 / (60 * 4.680) = 1.78e-4. Rank-17 at M = 60: 3.03e-3.
- One-sided sign-flip floor 2^-K: K = 12 gives 2.44e-4; K = 13 gives 1.22e-4.
- Shift-test floor 1 / (admissible shifts + 1): about 3,000 daily fixings in 1987 to 1998 give at best 3.3e-4; 300 months give 3.3e-3; 56 years give 1.8e-2.
- Chance that the smallest of 43 null p-values is at or below 0.003: 1 - 0.997^43 = 0.121.
