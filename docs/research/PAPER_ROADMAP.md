# Paper roadmap: what to publish, in what order, and what it takes

Written 2026-11-22 by the architect, for the repository owner. It builds on the independent review ([RESEARCH_REVIEW_2026-11-22.md](../../RESEARCH_REVIEW_2026-11-22.md)); flaw codes such as C1 or M4 refer to that review. The decisions are recorded in [ADR-004](../adr/ADR-004-paper-production-and-principle-validation.md), which also holds the work-package plan.

Two fixes are already under way and are not repeated here: **WP-A** (exact enumeration in the circular-shift test and the smallest attainable p-value, C1) and **WP-B** (withdrawn and stale papers out of the `_quarto.yml` render list and navbar, and CI no longer running `scripts/generate_artifacts.py`, the site part of C3/C5).

Journal limits and fees quoted below are from memory. Check each journal's author-guidelines page before formatting anything.

---

## 1. Honest assessment

### 1.1 What is going well

- **You withdrew bad results in public.** `CORRECTIONS.md` names synthetic data, random-number figures and tropical positions as what they were. Most projects never do this. It is the single best credential the repository has, and a referee will read it as a sign of good faith.
- **The rebuilt pipelines have the right skeleton.** A fixed list of indicators in `studies/*/hypothesis.yaml`, a null that respects the long runs of planetary states (circular shift), Benjamini-Yekutieli correction over a declared family, an explore period and a confirm period, and a data-snooping test (SPA).
- **The three study papers print their numbers from `results.json`.** Gold, silver and earthquake manuscripts type no number by hand. This is rare and it is exactly what makes a correction cheap.
- **The astronomy is now right and is tested.** Sidereal flag, Ketu as Rahu plus 180 degrees, a cross-check against JPL Horizons (`tests/test_horizons_crosscheck.py`), golden charts generated with PyJHora (`tests/fixtures/golden_charts.json`), and the moolatrikona table now cites its verse.
- **No look-ahead in the indicator tests.** The state on day t-1 is tested against the outcome on day t, and the extreme-move threshold uses only past bars.
- **The rule files are honest about their sources.** Several say in writing that no verse supports the claim. The rule format already carries parameters with ranges, reference cases, and a review log.
- **The earthquake study is the strongest piece**: 297 events, two declustering methods, a family of 26, zero discoveries, and a candidate pattern labelled as only a candidate.

### 1.2 What must be done better

In order of how much damage each does to a submission:

1. **The repository as published is not yet honest** (C3, C5). WP-B fixes the site. Old PDFs, release files and a few sentences in the README still overstate (ADR-004 package WP-01).
2. **The "pre-registration" is not one** (C2). The plans were committed a minute before the results, on data the project had already analysed in the withdrawn papers. Call it what it is: *a fixed analysis plan committed with the first run*. A true registration is only possible for data nobody here has looked at yet. That is future data, and the flood study.
3. **The gold and silver price data are not fit for a daily-return paper** (C4). Sparse bars before 2008, an illiquid contract, unadjusted rolls, and 26 years instead of the registered 58.
4. **Slow indicators have almost no independent evidence** (M1, M2). "Jupiter in Capricorn" happened once in the explore period, during the 2008 crisis. One episode is one observation, however many trading days it contains.
5. **Nothing is compared against ordinary explanations** (M4, M5). "Sun in sidereal Aries" is mid-April to mid-May, which is also Akshaya Tritiya. Without calendar and macro baselines no result, null or positive, can be read.
6. **Power is overstated and missing from the papers** (M6). A null only means something if the paper says what size of effect it could have found.
7. **The rule workbench's guarantees do not hold as built** (C6): direction ignored, family size 1, confirm can be retried.
8. **CI does not test the science** (M11, M13).

### 1.3 What the data can and cannot show

Plain statements you should be ready to make in every paper:

- **Can show:** that a specific, written-down rule, computed exactly as stated, was not followed by a detectably different gold return, earthquake rate or monsoon outcome, and how large an effect would have been detected.
- **Can show:** whether dated forecasts that astrologers published in advance did better than a simple base rate.
- **Cannot show:** that astrology "does not work". A null on fourteen indicators says nothing about the thousands of rules not tested, and nothing about effects smaller than the detection limit.
- **Cannot show:** anything about indicators with one or two episodes. They are untestable with this data and must be labelled so, not reported as nulls.
- **Cannot show:** anything causal, and nothing about "market efficiency".
- **Cannot rescue the historical confirm period.** The 2016-2026 holdout was known to you and to several rule authors. It is pseudo-out-of-sample at best. Only data after a public deposit date is a real confirm set.

### 1.4 The realistic headline

Yes: **a rigorous null plus an open testing tool.** More exactly: *"Sourced astrological claims about gold, earthquakes and rain were written as computable rules, checked for fidelity, and tested with methods built for slow cyclical predictors. None beat chance; here is the size of effect the tests could have seen; here is the tool so anyone can test another rule."*

This is a modest paper. It is also publishable, useful, and true. The tool and the method (exact shift tests, episode-level inference, placebo skies) are the lasting contribution; the nulls are the worked examples. Do not sell it as more. If one rule does survive a real prospective confirm one day, the same pipeline makes that claim credible, which is the reason to build it properly now.

### 1.5 One paper or several

**Several.** One omnibus paper is what was withdrawn. Gold, earthquakes and floods have different referees, different data problems and different statistics. A finance referee will not review ETAS declustering, and a seismologist will not review roll adjustment.

| # | Paper | Type | Why separate |
|---|---|---|---|
| P1 | Gold and silver, merged | Retrospective test with a prospective segment | Same pipeline, same indicators; silver alone is not a paper, but it is a good second asset |
| P2 | Himalayan earthquakes | Retrospective test | Different field and methods; already the strongest piece |
| P3 | Monsoon and floods | **Registered Report** | The only study where the project has not yet touched the data |
| P4 | The testing tool (optional) | Software note | Short; write it after P1 so it can cite a real use |

Numerology, the remedy notes and the mundane study are **not** papers. Park them as notes (WP-30). The mundane study can come back if founding times are ever sourced.

### 1.6 Should one be a Registered Report

**Yes: the flood and monsoon study (P3), and only that one.** In a Registered Report the journal reviews the question and the methods before any analysis, and promises to publish whatever the result. That fits a topic where a null is the likely result and where reviewers will otherwise suspect cherry-picking.

It cannot honestly be used for gold or earthquakes: those data have been analysed here already, twice.

Conditions that make P3 credible:

- **Nobody runs any analysis of rainfall or flood outcomes against any astrological indicator until the Stage 1 plan is accepted.** Download scripts and file checks are fine. Outcome-versus-indicator statistics are not. The pipeline will be built and tested on simulated data only (WP-29).
- State in the Stage 1 manuscript that the rainfall record is public and that the authors have not analysed it. Registered Report reviewers grade this ("level of bias control"); an honest statement about existing public data is accepted practice.
- The go/no-go depends on the Gemini `feasibility.md`: if no classical rain rule is defined well enough to compute for every year, there is no Stage 1 to write.

**Route:** Peer Community In Registered Reports (PCI RR). It is free, it is independent of any journal, and an accepted Stage 1 can then go to a "PCI RR-friendly" journal, which includes Royal Society Open Science. PLOS ONE also takes Registered Reports directly. For a single developer without a grant, PCI RR first is the cheapest path. Both publishers have fee waivers for authors in lower-income countries; check whether Nepal qualifies before choosing.

### 1.7 OSF or Zenodo

**Both. They do different jobs.**

- **OSF Registries** for the analysis plans. A registration there is time-stamped, cannot be edited, has a DOI, and uses templates reviewers know. Use the *Preregistration for Secondary Data Analysis* template for P1 and P2 (it asks, correctly, what you already know about the data).
- **Zenodo** for code and data releases. Its GitHub link gives every tagged release a DOI, and a "concept DOI" that always points to the latest. Deposit the frozen code, the `results.json` files, the snapshot hash index, and every data snapshot whose licence allows it.
- Link them: the OSF registration cites the Zenodo DOI of the tagged commit; the paper cites both.

### 1.8 Recommended order

1. Make the repository honest (WP-A, WP-B, WP-01, WP-30).
2. Make the methods sound (calibration tests, episode inference, baselines, power).
3. Replace the data.
4. Deposit the amended plans on OSF, then re-run gold and silver once on a clean tree. Submit P1.
5. Upgrade and submit P2.
6. Submit the P3 Stage 1 plan. Its drafting can start as soon as step 2 is done, because Stage 1 needs methods, not results; review takes months, so starting early costs nothing.
7. P4 when there is spare time.

---

## 2. Paper architecture

Every paper follows the same rule: **no number is typed.** Each is read from a `results.json` key through one accessor (section 6).

### 2.1 P1: gold and silver

| Item | Content |
|---|---|
| Working title | "Do sidereal planetary indicators predict gold and silver? A test with exact shift nulls, episode-level inference and calendar and macro baselines, 1968-2026" |
| Question | Are fourteen sourced planetary conditions followed by a different next-day return, absolute return or extreme-move rate in gold, and does silver agree? |
| H1 | For each indicator and outcome, the mean outcome differs between active and inactive days (two-sided unless the rule states a direction). |
| H2 | Any effect found in the explore period has the same sign and survives correction in the confirm period. |
| H3 | (Equivalence) The effect lies inside a pre-stated smallest effect size of interest (section 5.1). |
| H4 | (Forecasts) Dated ex-ante gold forecasts by named astrologers score better than the base rate (section 3.4). |
| First choice venue | Royal Society Open Science, or PLOS ONE. Both publish null results on the soundness of the method alone. |
| Format | Neither sets a hard word limit; aim for 6,000 to 8,000 words. PLOS ONE: abstract up to 300 words, a data availability statement, figures as separate TIFF or EPS files. |
| Second choice | Journal of Behavioral and Experimental Finance. Finance Research Letters only as a cut-down letter (about 2,500 words) and with a real risk of desk rejection for the topic. |
| Preprint | SSRN and OSF Preprints on submission day |
| Checklist | OSF secondary-data preregistration template (as the plan); TOP guidelines at level 2 for data, code and materials; a deviations-from-plan table; the journal's data availability statement |

IMRaD outline, mapped to files and keys (existing keys are in `studies/gold_market/artifacts/results.json` and the silver twin; keys marked *new* are added by the work packages):

| Section | Content | Source file | results.json keys |
|---|---|---|---|
| Abstract, Summary | Verdict, family size, discoveries, detection limit | `markets/report.py` | `headline.*`, `family.size_explore`, *new* `power.summary`, `equivalence.summary` |
| Introduction | Practitioner claims; lunar and calendar anomaly literature; Novy-Marx (2014) on spurious cosmic predictors | `paper/references.bib`, Gemini `literature_gold.csv` after checking | none |
| Methods: plan and deviations | What was fixed, when, and every deviation | `hypothesis.yaml` (`registered`, `amendments`) | `git.commit`, `git.dirty`, *new* `plan.sha256`, `plan.osf_doi`, `plan.deviations[]` |
| Methods: data | Series, sampling time, gaps, second-source check | `markets/fetch.py`, *new* `markets/quality.py` | `data.*`, `bars`, `periods.*`, *new* `data_quality.*` |
| Methods: indicators | The fourteen, their sources and validation level | `rules/financial/*.yaml`, `hypothesis.yaml` indicators | `family.indicators`, `indicator_activity.*`, *new* `episodes.<indicator>.<period>`, `indicators.<id>.validation_level` |
| Methods: statistics | Exact shift test, episode unit, BY, baselines, SPA benchmark | `stats/permutation.py`, `stats/nulls.py`, *new* `stats/episodes.py`, `markets/baselines.py` | `family.method`, `family.alpha`, `seed`, *new* `tests[].p_min_attainable`, `tests[].n_shifts` |
| Results: main family | Effects, exact p, q, intervals; untestable indicators listed apart | `tbl_indicator_tests.csv` | `tests[]`, `confirmation[]`, `family.indicators_not_evaluated` |
| Results: baselines | Does the indicator add anything over calendar, festival and macro terms | *new* `markets/baselines.py` | *new* `baselines.*` |
| Results: placebo skies | The real sky against shifted, tropical and scrambled skies | *new* `markets/placebo.py` | *new* `placebo_sky.*` |
| Results: stations, longitude regressions, SPA | Secondary families | `markets/event_study.py`, `stats/granger.py`, `stats/walk_forward.py` | `event_study[]`, `granger[]`, `spa.*`, `stationarity[]` |
| Results: silver | Same tables, second asset | silver `results.json` | same keys |
| Results: power and equivalence | Detection limit at the corrected threshold; TOST | `stats/power.py`, `stats/equivalence.py` | *new* `power[]`, `equivalence[]` |
| Results: forecasts | Score of ex-ante calls against base rates | *new* `stats/forecast_scoring.py` | *new* `forecasts.*` |
| Discussion | What is excluded, what is not; one-episode indicators; all tests ever run | `report.py` | *new* `project_multiplicity.*`, `sensitivity.ayanamsa.*` |
| Reproducibility | Commit, environment, data hashes, DOIs | `manifest.json` | `git.*`, `data.sha256`, `data.snapshot` |

Figures: (1) price with indicator episodes shaded; (2) forest plot of effects with intervals, exact p and q, untestable indicators greyed; (3) episodes per indicator and period against the testability line; (4) detection limit against the smallest effect of interest; (5) real sky against placebo skies; (6) forecast scores against base rate.
Tables: (1) data sources and quality; (2) indicators with source, verse and validation level; (3) main family; (4) baselines; (5) secondary families; (6) deviations from the plan; (7) project-wide count of tests.

### 2.2 P2: Himalayan earthquakes

| Item | Content |
|---|---|
| Working title | "Classical and practitioner astrological indicators and Himalayan seismicity, 1904-2026: a null result with stated detection limits" |
| Question | Does the rate of declustered mainshocks differ when any of thirteen astrological indicators is active? |
| H1 | Rate ratio differs from 1 for each indicator (family of 26 across two declustering methods). |
| H2 | An explore-period finding repeats in the confirm period. |
| H3 | (Prospective, separately registered) The Moon in the Varuna mandala raises the rate of M 6 or larger events worldwide. Registered before the global catalogue is fetched. |
| H4 | Dated ex-ante earthquake forecasts beat the Poisson base rate for their stated place, time window and magnitude. |
| Venue | PLOS ONE or Royal Society Open Science; Geoscience Letters as an alternative; Seismological Research Letters only as a short negative-result note |
| Preprint | EarthArXiv |
| Checklist | OSF secondary-data template; TOP level 2; CSEP conventions for alarm-based forecasts (Molchan diagram, probability gain); catalogue completeness and declustering reported for each method |

| Section | Source file | results.json keys (`studies/earthquake/artifacts/results.json`) |
|---|---|---|
| Summary | the paper .qmd | `headline.*` |
| Data: catalogue, region, magnitudes | `scripts/fetch_catalogue.py` | `catalogue.*`, `figures.region`, `figures.mc` |
| Declustering | `scripts/decluster.py` | `declustering.*`, `figures.declustering`, *new* `declustering.etas.*` |
| Indicators | `scripts/indicators.py`, `rules/seismic/`, `rules/mundane/practitioner/bs32_*.yaml` | `indicator_time_fraction.*`, `eclipses.*`, `grid.*`, `ephemeris.*` |
| Statistical design | `hypothesis.yaml` (`test`, `split`, `amendments`) | `hypothesis_sha256`, `seed`, `n_draws`, `headline.correction`, `headline.alpha` |
| Results: rate ratios | `family_explore.csv`, `confirmation.csv` | `family[]`, `confirmation[]`, `raw_descriptive[]` |
| Results: Molchan, forecast check, count model | `stats/molchan.py`, `scripts/count_models.py` | `molchan.*`, `spa.*`, `count_model.*` |
| Results: Bayes, classifier | `stats/bayes.py`, `stats/classify.py` | `bayes[]`, `classifier.*` |
| Controls | `stats/controls.py` | `controls.positive`, `controls.negative` |
| Power and equivalence | `stats/power.py`, `scripts/robustness.py` | `power[]` (recomputed at the corrected threshold), *new* `equivalence[]` |
| Forecasts | *new* `stats/forecast_scoring.py` | *new* `forecasts.*` |

Figures: region map; magnitude of completeness; declustering comparison (three methods); rate-ratio forest plot; Molchan diagrams; detection limit curve. Tables: catalogue summary; indicators with source and validation level; family results; controls; deviations.

### 2.3 P3: monsoon and floods (Registered Report)

| Item | Content |
|---|---|
| Working title | "Do classical Indian rain-forecasting rules predict all-India monsoon rainfall? A Registered Report" |
| Question | Do rules from Brihat Samhita chapters 21 to 28 and related texts, computed for each year, predict the June-to-September all-India rainfall category better than climatology and better than an ENSO and IOD model? |
| H1 | A rule's yearly forecast has positive skill over climatology (ranked probability skill score above zero). |
| H2 | It adds skill to a model that already has ENSO and IOD. |
| H3 | Published almanac (panchang) monsoon forecasts beat climatology. |
| Likely primary outcome | IITM all-India summer monsoon rainfall anomaly, 1871 onward, in the three IMD categories. To be fixed after `feasibility.md` is verified. |
| Sample | About 155 yearly values. That is small. The Stage 1 power analysis must say what skill is detectable; if only very large skill is detectable, say so and let reviewers judge. |
| Route | PCI Registered Reports Stage 1, then a PCI RR-friendly journal (Royal Society Open Science) or PLOS ONE |
| Checklist | The PCI RR Stage 1 criteria and its study-design table (question, hypothesis, sampling plan, analysis plan, sensitivity, interpretation for each outcome, theory that could be shown wrong); TOP level 3 |

Stage 1 manuscript: Introduction; Methods (data sources and licences, rule operationalisation with validation levels, primary and secondary outcomes, analysis plan, power analysis on simulated data, what counts as support and as refutation, data-access statement); pilot results on **simulated** data only. No `results.json` from real data exists before acceptance; the keys are fixed in the plan (`skill.rpss`, `skill.vs_enso`, `forecasts.*`, `power.*`) so the gate in section 6 applies from the first real run.

### 2.4 P4: the testing tool (optional)

A short software paper for the Journal of Open Source Software (250 to 1,000 words, reviewed on the repository itself: tests, documentation, licence, evidence of research use). Submit only after the workbench guards are fixed (WP-23) and P1 is at least a preprint. Open question to settle first: the repository is MIT but the ephemeris library is AGPL (Gemini prompt 5, question 6).

---

## 3. From a verse to a tested rule: the validation chain

"Validated" is a dangerous word here. A rule can be a faithful encoding of a verse and still predict nothing. The chain below gives each meaning its own level, so a paper can say exactly what was validated.

### 3.1 The levels

| Level | Name | What it means | Evidence required | Who signs |
|---|---|---|---|---|
| L0 | Recorded | The claim is written down | A rule YAML that loads | Anyone |
| L1 | Sourced | We know where it comes from | `source` with text, edition, translator, chapter and verse (or page), and a short quotation; for practitioners, the URL, publication date and an archive link. A maintainer has opened the source and found the quotation. | Maintainer |
| L2 | Operationalised | It is computable, and every choice is on the table | `conditions` resolve against the engine; **every number is a `params` entry with a value, a range and a citation for that range** (the verse, a named commentary, or "author's choice" stated as such); `expected_effect` has a direction; zodiac, ayanamsa and node model are stated | Maintainer |
| L3 | Computationally verified | The engine computes what it says | (a) every reference case passes `astro-rules test`; (b) at least three reference cases agree with Jagannatha Hora (JHora) to 1 arcminute, recorded as a fixture; (c) the bodies and instants involved agree with JPL Horizons to 5 arcseconds | Automated, plus one person with JHora |
| L4 | Faithful | An astrologer agrees the rule says what the source says | A review entry by a named reviewer who did not write the rule and has not seen any test result for it: verdict *faithful*, *faithful with changes* or *not faithful* | Astrologer |
| L5 | Explored | Tried on explore-period data | A logged `fit`; the parameter grid searched is recorded; result labelled exploratory | Workbench |
| L6 | Confirmed or refuted | One sealed test on data not used before | One `confirm` per rule lineage, in the ledger, with family-wide correction | Workbench |

How to speak about each: "sourced rule" (L1), "computable rule" (L2), "verified rule" (L3), **"validated principle" (L4, meaning faithfully encoded, nothing more)**, "explored" (L5), "confirmed" or "not confirmed" (L6). No paper may write "validated" for anything below L4, and none may let "validated" suggest "true".

A level is **computed from the evidence in the file**, never typed in by hand (WP-20). A rule may enter a paper's confirmatory family only at L3 or above. Rules at L1 or L2 may be tested, but are reported as "practitioner-extracted, not reviewed".

### 3.2 Rules of the chain

- **A cited range for every parameter.** Mars-Ketu orbs of 8, 13 and 15 degrees in different files (M8) is the failure this prevents. If the text gives no orb, the range is the spread of named commentators, and the test reports the whole range (a specification curve), not the best cell.
- **Tier is about the source, not the quality.** Classical means a verse exists and is quoted. If no verse supports the market claim, the tier is practitioner or experimental, whatever tradition says.
- **JHora cross-check.** JHora is a Windows desktop program with no scripting. The check is therefore a manual, recorded export: program version, ayanamsa setting, node setting, date, time, place, and the values read, stored as a JSON fixture with the name of the person who read them (WP-21). PyJHora, already used for the golden charts, is the automated stand-in between manual checks.
- **Horizons cross-check.** Extend the existing fixture from positions on fixed dates to the events rules depend on: sign ingress, station, exact conjunction, new and full Moon.
- **The reviewer must be blind to results.** The review packet (WP-22) shows the claim, the source text, the plain-language explanation from `astro-rules explain` for each reference case, and three questions: Is this what the text says? Are the ranges reasonable? Which chart and which ayanamsa would you use? It shows no data and no test output.
- **Changing a rule after confirm starts a new lineage**, and the family size counts every lineage. This closes the "bump the version, confirm again" hole (C6).
- **Disagreement is data.** Where practitioners contradict each other, both versions are encoded and both are tested, each with its own direction.

### 3.3 Direction matters

A rule that says "gold falls" and one that says "gold peaks" must be tested on different statistics. Today both run two-sided on an unsigned measure (C6). After WP-23 a rule with a stated direction gets a one-sided test on signed returns, and an effect in the wrong direction counts against the rule.

### 3.4 Scoring ex-ante practitioner forecasts

Forecasts are the only evidence in which the astrologer, not the analyst, chose the specification. They deserve careful scoring.

**What counts as ex-ante.** A public statement with a date, proven by an archive capture (Wayback Machine or similar) taken before the target window opens. No capture, no ex-ante status. Everything else is kept and labelled ex-post, and is never scored.

**Coding, before any price is looked at.** Each forecast is coded by a person who does not have the outcome in front of them into: target series, window start and end, direction or category, level if stated, and the probability if the author gave one. A plain statement with no hedge is coded as probability 1; hedged wording uses a fixed table written into the plan ("likely" = 0.75, and so on). Forecasts that cannot be coded are counted and reported, never dropped silently.

**Base rates, which are the heart of it.** A forecast earns credit only for beating what anyone could have said:

| Domain | Reference forecast (base rate) |
|---|---|
| Gold direction over a window | The share of all windows of the same length, in the 20 years before publication, in which gold rose. Gold drifts up, so "gold will rise this year" has a base rate well above one half. |
| Gold level or peak | Probability from a random walk with drift and the volatility of the previous year |
| Earthquake in a region, time window and magnitude range | Poisson probability of at least one such event from the catalogue rate for that region. A vague forecast (large region, long window, low magnitude) has a base rate near 1 and so earns almost nothing. |
| Monsoon category | The IMD climatological frequency of each category |

**Scores.** Proper scoring rules, which reward honest probabilities:

- Yes/no outcomes: the **Brier score**, and the **Brier skill score** against the base rate (above zero means better than the base rate).
- Ordered categories (deficient, normal, excess): the **ranked probability score** and its skill score.
- Earthquake alarms: the **Molchan diagram** and probability gain (`stats/molchan.py` exists), weighing misses against the share of space and time under alarm.
- Also reported: the raw hit rate next to the base-rate hit rate, because readers understand it.

**Inference.** Forecasts by one astrologer are not independent, so uncertainty is computed by resampling astrologers, not forecasts. With around 50 forecasts only large skill is detectable; the paper states the detectable skill.

**The honest caveat.** A collected set of old forecasts is not a census. Failed forecasts get deleted and successful ones get repeated, so any skill found is an upper bound. The clean test is a **prospective ledger**: from the registration date, forecasts are logged with an archive link as they are published and scored when their window closes. Start it at M4; it costs nothing and its value grows every year.

---

## 4. Data pipeline for the Gemini outputs

### 4.1 The one principle

**Gemini's files are pointers, never data.** Nothing it writes is used as a study input. A price, a magnitude or a rainfall value enters a study only when one of our own fetch scripts downloads it from the primary provider and the bytes are hashed. An AI research agent can invent a URL, a verse or a number; the pipeline is built so that an invention cannot reach a result.

### 4.2 Stages

```
research/incoming/<topic>/      quarantine: untrusted, not committed
        |  1. tools/ingest validator: file contract, types, duplicates
        |  2. URL and licence check: link opens, archive link saved, licence page read by a person
        |  3. spot checks by a person: quotations, dates, verse numbers, a sample of numbers
        v
data/registry/<topic>/          verified pointers: committed (source lists, episodes, forecasts, literature)
rules/<domain>/...              rule YAML after "astro-rules validate", status needs_verification, level L0 or L1
        |  4. scripts/fetch/<source>.py downloads from the primary provider
        v
data/snapshots/<name>_<sha12>.<ext> + .manifest.json     frozen bytes
data/snapshot_index.json        committed list: file, SHA-256, rows, date range, source, licence, committed or not
        |  5. a study names its snapshot by hash in hypothesis.yaml
        v
studies/<study>/artifacts/results.json   records the hash it actually read
```

Topics: `gold_prices` (prompt 1), `gold_astrology` (prompt 2), `earthquake` (prompt 3), `flood` (prompt 4), `methods` (prompt 5).

**Seen on 2026-11-22, while this was being written:** the first flood outputs did not land in the quarantine. `sources_flood.csv`, `literature_flood.csv` and `monsoon_forecasts_exante.csv` are at the repository root and four rule files are in `studies/monsoon/rules/`. Their columns also differ from the handover contract (`sources_flood.csv` has `id, span, resolution` where the contract asks for `series_id, freq, start, end, units, tz_sampling_time`). Do not commit them where they are. Move them to `research/incoming/flood/` and run them through the validator like everything else. Two of the four rules depend on observed wind direction or unseasonal rain, which an ephemeris cannot compute; they are `needs_predicates` at best, and this bears directly on the feasibility of P3.

Note: the existing `research/` folder is a stale pre-correction copy that the review asks to delete. `research/incoming/` is new and separate; only its README is committed.

### 4.3 File contracts

All CSV files: UTF-8, comma-separated, a header row, dates as `YYYY-MM-DD`, one fact per row, the literal `NOT FOUND` for a gap, no merged or blank header cells.

| File | Required columns |
|---|---|
| `sources_gold.csv`, `drivers.csv`, `sources_quake.csv`, `sources_flood.csv` | `dataset, provider, series_id, freq, start, end, units, tz_sampling_time, licence, redistributable (yes, no or unclear), url` |
| `gold_episodes.csv` | `episode_id, direction, start_date, peak_or_trough_date, end_date, start_price_usd, extreme_price_usd, pct_change, max_drawdown_pct, duration_days, series_used, macro_narrative, key_drivers, sources` |
| `literature_*.csv` | `citation, doi, method, data, sample, oos_result, effect_size, notes` |
| `gold_forecasts_exante.csv` | `astrologer, published_date, url, quote, target_start, target_end, predicted_direction, predicted_level, method_cited` |
| `episode_astrology_claims.csv` | `episode_id, astrologer, published_date, ex_ante, configuration_cited, quote, url` |
| `quake_forecasts_exante.csv` | `astrologer, published_date, url, quote, region, window_start, window_end, magnitude_claimed, method` |
| `monsoon_forecasts_exante.csv` | `source, published_date, url, year, predicted_category, regions, method` |
| `disputes.md`, `feasibility.md`, `answers.md` | Free text; every claim carries a URL or DOI |

The validator adds, in the promoted copy only: `row_id, url_status, archive_url, checked_by, checked_on, verdict (accepted, rejected or unverified), reject_reason`.

**Rule YAML contract** (`rules_gold/`, `rules_quake/`, `rules_flood/`): must pass `astro-rules validate` against `rules/schema.json`. Note three differences between the handover template and the real schema, which the validator reports as fixable, not fatal: the schema's `tier` allows only `classical` or `experimental` (practitioner rules are `experimental` and live in a `practitioner/` folder); `conditions` must be structured predicates, not prose, so a prose rule is filed with `status: needs_predicates`; and `ex_ante` belongs under `notes`. Required beyond the schema: `source` complete to L1, every number in `params` with `value, min, max, step, unit`, `expected_effect.direction`, and at least one `fires` and one `silent` reference case.

### 4.4 What gets rejected

- A row with no URL, DOI or book-chapter-verse reference.
- A dead link with no archive copy.
- A quotation that is not on the cited page, or a verse number that does not match the named edition. One confirmed fabrication in a file puts the **whole file** back to full manual checking.
- A forecast marked ex-ante whose publication date is not before its target window, or with no archive capture proving the date.
- Dates that cannot be parsed, or an end before a start.
- Duplicate ids, or a rule that repeats one already in `rules/`.
- A rule that fails validation and is not explicitly marked `needs_predicates`.
- **Any file of price, catalogue or rainfall values.** Wanted or not, it is not used and not committed.
- Numbers in `gold_episodes.csv` are treated as claims: the episode list is re-derived by our own code from the snapshot using the stated definition, and Gemini's version is kept only for comparison.

Spot-check rates: every row of the forecast files (each one becomes a scored data point), every rule's source, and for source and literature lists at least 20 percent of rows and never fewer than 10.

### 4.5 What may be committed

| Data | Licence position | Commit the file? |
|---|---|---|
| Our own computed data (ephemeris tables, festival calendar, results tables) | Ours | Yes |
| Verified pointer files in `data/registry/` (facts and short quotations with attribution) | Facts are not copyrightable; keep quotations short | Yes |
| World Bank Pink Sheet | CC BY 4.0 | Yes, with attribution |
| USGS ComCat, CFTC Commitments of Traders, US government series on FRED (TIPS yield, Fed dollar index) | Public domain | Yes |
| ISC-GEM catalogue | CC BY-SA 3.0 | Yes, in its own folder with the licence file; the share-alike term applies to that file |
| GFZ Kp index | CC BY 4.0 | Yes |
| LBMA prices (any route), WGC Goldhub, Yahoo, MCX, CME data | No redistribution | **No.** Publish the hash and the fetch script |
| Daily returns derived from a licensed price series | They reproduce the series | **No** |
| VIX and GVZ (CBOE, via FRED), SILSO sunspots (CC BY-NC), Geopolitical Risk index, IITM and IMD rainfall, EM-DAT | Restricted or unclear | No, until the terms are read and recorded |
| Summary statistics and figures made from licensed data | Normal research use | Yes |

The rule when unsure: **hash plus fetch script, no file.** A reader who cannot download a licensed series can still verify that their copy matches ours by its hash. `data/registry/licences.yaml` records, per source, the terms URL, the date read and the decision.

One consequence to state in P1: the main gold series cannot be redistributed, so a reader needs their own access to reproduce the paper exactly. The World Bank monthly series, which can be shared, is run as an openly reproducible low-frequency check.

---

## 5. Statistical upgrade, in the order to do it

Common to all studies, first: **(0)** WP-A exact shift test; **(1)** the calibration suite (WP-02), which simulates data with no effect and checks that each test raises a false alarm no more often than it claims. Nothing below is trusted until the suite passes on it.

### 5.1 Gold and silver

| Step | What | Why (review) | Package |
|---|---|---|---|
| 1 | Replace the price series: LBMA PM from 1968 as registered, checked against a second source; keep zero-volume settlement days; fail the run if more than 1 percent of business days are missing | C4 | WP-12 |
| 2 | The **episode** becomes the unit for slow indicators. An indicator with fewer than 8 episodes in a period is reported as "untestable with this sample", outside the family | M1, M2 | WP-04 |
| 3 | Outcomes standardised by past-only volatility, so that "2008 was volatile" stops looking like "Jupiter in Capricorn is volatile" | M1 | WP-05 |
| 4 | Baselines, in order: calendar (month, weekday, turn of month, holidays), Indian festival and wedding season, lunar phase, then macro (real yield, dollar, VIX, geopolitical risk, announcement days). The question becomes "does the indicator add anything" | M4, M5 | WP-06 |
| 5 | Placebo skies: rerun on shifted, tropical and scrambled-rulership skies. The real sky must beat the placebos | M4 | WP-07 |
| 6 | SPA benchmark: compare each rule with a buy-and-hold position of equal exposure, with costs | M3 | WP-09 |
| 7 | Power at the corrected threshold, in episodes; a pre-stated smallest effect size of interest (SESOI); equivalence tests (TOST) | M6 | WP-08 |
| 8 | Volatility model with the indicator in the variance equation (GARCH-X) as a secondary analysis | review 4.2 | WP-05 |
| 9 | Ayanamsa sensitivity (Lahiri, Raman, KP, true Chitrapaksha) | M8 | WP-07 |
| 10 | Project-wide statement: how many hypotheses the whole repository has tested and how many false alarms to expect | M12 | WP-08 |
| 11 | Wire it together, deposit the amended plan, one clean re-run | C2 | WP-14, WP-15 |

**On the SESOI.** TOST asks "is the effect smaller than X?", so X must be fixed in the plan before the re-run. Proposed starting values, for you to confirm in the amended plan (design task D1): 5 basis points a day on return while an indicator is active (about 12 percent a year, well below what "gold rises" or "gold peaks" claims imply); 10 percent of the average absolute daily move; 2 percentage points on the extreme-move rate. Three outcomes are then possible for each test and the paper must use the right word: **effect found**, **effect excluded** (the interval lies inside the SESOI), or **inconclusive** (the interval is wider than the SESOI). "Inconclusive" will be the honest label for several slow indicators.

**Left out on purpose** for P1: intraday realised volatility, regime-switching models, machine-learning forecasts, Indian premium data. Each is a paper of its own, and adding them delays a clean null. The behavioural-calendar idea (festival demand visible in Indian premia) is the most promising follow-up and is noted as future work.

### 5.2 Earthquake

| Step | What | Why | Package |
|---|---|---|---|
| 1 | ISC-GEM as the primary catalogue, ComCat frozen as a check, Global CMT for mechanisms; fix the offline time-zone bug; tighten the region | M7 | WP-25 |
| 2 | ETAS declustering as a third method beside the two existing ones | M7 | WP-26 |
| 3 | Power at the corrected threshold, with clustered rather than Poisson counts; SESOI as a rate ratio (proposed 1.5); TOST | M6 | WP-08, WP-27 |
| 4 | Tidal positive control: restrict by fault mechanism so it could succeed, or drop it and say why | M6 | WP-27 |
| 5 | Negative control as a distribution of shifts, not one shift | review, minor | WP-27 |
| 6 | Amended plan deposited; one clean re-run | C2 | WP-27 |
| 7 | Varuna-mandala candidate registered separately against the global catalogue, before that catalogue is fetched | review item 9 | D2 |

### 5.3 Flood and monsoon

Design only until Stage 1 is accepted: primary outcome and categories; rules that give a forecast for every year; skill measured by leave-one-year-out ranked probability skill score against climatology and against an ENSO and IOD model; block permutation by year; a power analysis on simulated rainfall with realistic autocorrelation; a decision table stating what result would count for the rule and what against. With about 155 years, expect to detect only fairly large skill. Say so in Stage 1.

---

## 6. PDF and reproducibility pipeline

1. **One accessor for numbers.** A small `paperkit` module loads `results.json` and returns values by dotted key (for example `headline.n_significant_explore`). A missing key raises an error; it never prints a blank or a default. The existing `report.*` helpers move onto it.
2. **The results-key gate** (WP-16). `tools/check_paper_keys.py` fails when: a paper asks for a key that does not exist; a paper's prose contains a bare number that is not on the paper's short allow-list (years, section numbers); `results.json` was written from a dirty tree; the plan hash or the data hash in `results.json` differs from the current `hypothesis.yaml` or `data/snapshot_index.json`. The last two checks catch a stale `results.json`, the fault behind several withdrawn numbers.
3. **Journal templates.** Quarto's journal extensions cover Elsevier and PLOS. Royal Society Open Science has no official Quarto format; use a plain single-column article PDF for first submission and their LaTeX class only if asked at acceptance. Each paper sets its format in its own front matter, so `_quarto.yml` is not touched again. `scripts/generate_pdfs.sh` is rewritten to build only the target papers and to stop calling `generate_artifacts.py`.
4. **Frozen environment.** A lock file with hashes for every Python package; a Docker image that pins Python, Quarto, TeX and the ephemeris files (by hash); `make paper STUDY=...` runs the same steps inside it. Each `results.json` records the image digest.
5. **CI paper gate.** A new workflow, with no "or skip" fallbacks: calibration suite, key gate, snapshot hash check, render of each target paper from committed `results.json`. CI does not re-run studies on licensed data; it proves the paper matches the committed results and that the committed results match the declared inputs.
6. **Release and DOI.** `CITATION.cff` and `.zenodo.json`; a tag such as `paper-metals-v1.0`; Zenodo mints the DOI; shareable snapshots go into the Zenodo record; the OSF registration and the paper cite that DOI.

---

## 7. Milestones and exit criteria

A milestone is reached only when every criterion holds. No dates are given; the review's estimate of about a month of focused work to P1 is fair if the Gemini data questions are answered quickly.

| Milestone | Exit criteria |
|---|---|
| **M1 The repository is honest** | WP-A and WP-B merged. No withdrawn result is rendered, linked or shipped as a PDF. README and study plans say "fixed analysis plan", not "pre-registered before any data". Gold verdict corrected to null in `results.json`, README and `CORRECTIONS.md`. Numerology, remedy and mundane labelled as notes. |
| **M2 The methods are sound** | Calibration suite in CI and passing: shift test, episode test, bootstrap intervals, BY and SPA hold their stated false-alarm rate on simulated data with volatility clustering and regime shifts. Episode inference, baselines, placebo skies, power, TOST and the run seal merged with their tests. One rule engine. Workbench guards in place. |
| **M3 The data are upgraded** | Ingest validator run on every Gemini topic, with a verification report. Gold and silver from 1968 from a verified source, cross-checked against a second, under 1 percent of business days missing. ISC-GEM catalogue fetched. Every snapshot in `data/snapshot_index.json` with its hash and licence decision. |
| **M4 Gold and silver paper submitted** | Amended plan on OSF with a DOI, before the re-run. One logged clean-tree re-run. Every indicator in the family at validation level L3 or above, with its level in Table 2. Merged manuscript passes the key gate and builds in the frozen image. Zenodo DOI. Preprint posted. Submitted. Prospective forecast ledger opened. |
| **M5 Earthquake paper submitted** | ETAS declustering added. Power at the corrected threshold in the paper. Amended plan on OSF. Clean re-run. Varuna global test registered before its data are fetched. Preprint on EarthArXiv. Submitted. |
| **M6 Flood Registered Report, Stage 1 submitted** | Feasibility confirmed from verified Gemini output. At least one rain rule at L4, reviewed by an astrologer. Pipeline runs end to end on simulated data. Power analysis written. A signed statement that no outcome analysis has been run. Stage 1 submitted to PCI RR. |
| **M7 (optional) Tool paper** | Licence question settled; JOSS submission. |

### Things only you can do

| Id | Action | Needed before |
|---|---|---|
| H1 | Create the OSF project and deposit each amended plan | WP-15, WP-27 |
| H2 | Find one astrologer (ideally two) willing to review rule packets and be named | M4 for L4 claims; M6 without exception |
| H3 | Find someone with Jagannatha Hora on Windows to read off the cross-check values | WP-21 fixtures |
| H4 | Read and record licence terms for each source; decide journal and check fee waivers | M3, M4 |
| H5 | Confirm the SESOI values and the amended family (design task D1) | WP-15 |
| H6 | Approve deleting the stale `research/` copy, old PDFs and release files | WP-01 |
