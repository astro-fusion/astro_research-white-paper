# ADR-006: Retrospective mundane chart engine

- Status: proposed; first slice delivered (WP-48 to WP-56); amended by [ADR-007](ADR-007-principle-validity-reports.md) on 2026-11-22
- Date: 2026-11-22
- Deciders: repository owner (single developer); architect (design only)
- Builds on: [ADR-003](ADR-003-rule-workbench.md) (workbench, predicates, atlas), [ADR-004](ADR-004-paper-production-and-principle-validation.md) (levels L0 to L6, quarantine, packages WP-01 to WP-30)
- Amends: [ADR-005](ADR-005-pattern-discovery-and-claims-registry.md) (see section 10). ADR-005 sections 1 and 2 stay in force.
- Inputs: `studies/mundane/` (README, plan draft, 113 countries, 825 events, 65 candidate charts), `libs/vedic_astrology_core/`, [FINDINGS_LEDGER.md](../research/FINDINGS_LEDGER.md), [CLAIMS_REGISTRY_SPEC.md](../research/CLAIMS_REGISTRY_SPEC.md), [RESEARCH_REVIEW_2026-11-22.md](../../RESEARCH_REVIEW_2026-11-22.md) (section 5.3, question 15)
- `core/` below stands for `libs/vedic_astrology_core/`.

> **Superseded parts (ADR-007).**
> - Section 10: every ADR-005 item listed there as "deprioritised" or "can be revived" (model registry, forecast ledger, forecast scoring, search) is now **removed** from the plan. The claims registry is kept only as a source of principles to test.
> - Section 2.1, case file section 8 (practitioner explanations with a before-or-after timing class): not rendered in validity reports; no classification of published predictions is published.
> - Section 2.2 verdict words are mapped to the five ADR-007 verdicts by the national-chart adapter (ADR-007 WP-80).
> - WP-62 (site pages) and WP-63 (confirm run) are replaced by ADR-007 WP-73 and WP-80. WP-57 to WP-61 and WP-64 stay.
> - Everything else in this ADR stays in force.

## The request

The owner's words: "i dont need the engine to predict the future; we are just focused on the data for past events, and the engine should be all well-mentioned methods, and the pattern should all be able to analyze from D1 to D9 to dasha of a country."

## Short answer

1. **Build a retrospective engine. No forecasting product.** Input: a past event and a country. Output: the full classical picture at that moment (founding chart D1 to D9, Vimshottari maha, antar and pratyantar, transits, event-time sky chart) and the list of catalogued rules that fire.
2. **Two outputs.** A per-event **case file** an astrologer can read. An **aggregate pattern report** that counts how often each catalogued factor is active at events and at matched control dates.
3. **Every technique comes from a method catalogue.** Each entry has a source, a citation status and an exact computational definition. A technique with no entry cannot be computed. The engine invents nothing.
4. **Founding-time uncertainty is handled first, not last.** Each chart has a grade and a time window. The engine recomputes every factor across the window and marks it stable or unstable. Aggregate work uses stable factors only.
5. **Past-only analysis still needs controls.** Section 1 explains why in one paragraph and one number.
6. **First slice:** India, Himalayan earthquakes of M 6 and above from the existing catalogue, D1 + D9 + Vimshottari. It delivers case files and a descriptive table. It has too few events for a test (5 to 12). That is stated up front, not discovered later.

---

## 1. Scope

### 1.1 In scope

- Past events only: earthquakes, floods, wars, coups, disasters, gold moves.
- Charts: country founding charts (several candidates per country), event-time sky charts, and later annual charts.
- Methods: only those in the catalogue (section 4).
- Two outputs (section 2).

### 1.2 Out of scope

- Issuing forecasts. No forecast files, no live ledger, no model fitting, no machine learning.
- New techniques. A method that is not in a named text or a named practitioner's published work is not added.
- Rectification. The engine never adjusts a founding time to fit events.

### 1.3 Why a past-only engine still needs controls

Past-only analysis removes the forecasting problem. It does not remove the counting problem.

- With D1 to D9, nine grahas, twelve houses and three dasha levels, **about 2,800 catalogue-style statements are true at any moment** for any country (section 5). An astrologer reading one event chart will always find several that fit.
- So "this factor was active at the event" means nothing alone. The useful question is: **was it active more often at events than on ordinary dates?**
- Many factors are also calendar clocks. The Sun's sign is the month. A mahadasha is one stretch of 6 to 20 years. ADR-005 section 2 lists these traps. They apply to the past exactly as they apply to the future.

What the engine does about it, kept small:

| Control | What it is | What it answers |
|---|---|---|
| C1 Season-matched dates | Same country, same day of year within 15 days, other years, at least 30 days from any event of that type. 20 per event. | Is the factor more common at events than at the same time of year? |
| C2 Shifted sky | The existing circular-shift null (`core/stats/nulls.py`). | Same question, keeping event clustering intact. |
| C3 Placebo chart | The same events read against another country's chart, and against the same chart with the founding date moved by a random number of days. | Does the national chart add anything at all? |
| Explore and confirm split | Events up to a fixed date are for looking. Later events are counted once, by a fixed plan. Both parts are past data. | Was the pattern chosen after seeing it? |

Honest names (ADR-004 D-2): the confirm part is "pseudo-out-of-sample". It is still history that the analyst knows.

### 1.4 What the engine may and may not say

| Allowed | Not allowed |
|---|---|
| "Factor F was active at 9 of 30 events and on 22% of control dates." | "Factor F causes earthquakes." |
| "No factor passed the planned test. Effects above rate ratio X are unlikely." | "Astrology does not work." |
| "This factor is not stable inside the founding-time window." | Reporting an unstable factor as a fact about the event. |
| "Too few events to test. Descriptive only." | A p-value on fewer events than the floor in section 5.4. |

---

## 2. The two outputs

### 2.1 Case file (per event, per candidate chart)

One event, one chart, everything the catalogue can compute. Canonical form is JSON. HTML and PDF are rendered from the JSON and add nothing.

| Section | Content |
|---|---|
| 1 Header | Event id, title, type, date, time and its precision, place, magnitude, source and archive URL. Chart id, grade, time window. |
| 2 Founding chart | Rows: lagna and nine grahas. Columns: D1 to D9 sign, house from that varga's lagna, degree, nakshatra and pada, dignity, retrograde, combust. A cell that changes inside the time window is marked and shows every value it takes. |
| 3 Dasha at the event | Maha, antar and pratyantar lord, start and end, boundary uncertainty in days, stable or not. For each lord: natal house, lordship and dignity in D1 and D9. |
| 4 Transits at the event | Nine grahas: longitude, sign, nakshatra, speed, retrograde. House from natal lagna and from natal Moon. One sub-table per catalogued transit reading (section 4.3). |
| 5 Event-time sky chart | Only when the event has a place and a time to the hour or better. Lagna at the epicentre, Moon nakshatra and its Brihat Samhita ch. 32 mandala, tithi, weekday lord, nearest eclipse before and after, samvatsara. |
| 6 Annual context | Phase 2. The year's Mesha sankranti chart for the capital. |
| 7 Factors that fire | One row per catalogued factor that is true: factor id, method, source, citation status, the engine's evidence sentence, stable or not, and its **base rate** (share of all dates on which the same factor is true for this chart). |
| 8 Practitioner explanations | Rows from the claims registry that name this event, with their timing class (before or after the event). |
| 9 Provenance | Hashes of the chart registry, event registry and catalogue; ayanamsa, node model, house system, dasha year; code commit. |

The base rate in section 7 comes from the calendar alone. It needs no event data, so it can be shown for every event. It is the one-line answer to "is this striking?".

### 2.2 Aggregate pattern report

For each catalogued factor in a declared family (section 5.3):

| Column | Meaning |
|---|---|
| `n_events`, `n_active` | Events tested; events with the factor active |
| `control_rate` | Share of control dates with the factor active (C1) |
| `rate_ratio`, `ci` | Event share over control share, with exact interval |
| `p_matched`, `p_shift` | Permutation p inside matched sets; circular-shift p |
| `q_family` | Benjamini-Yekutieli adjusted value in its family |
| `episodes` | Number of separate runs of the factor in the period (ADR-004 D-6) |
| `stable_share` | Share of events where the factor is stable in the time window |
| `placebo_rank` | Rank of the real chart among placebo charts (C3) |
| `mde` | Smallest rate ratio this test could detect with 80% power |
| `verdict` | `effect found`, `effect excluded`, `inconclusive`, `untestable` or `descriptive only` |

Three cuts: per country, per event type, and pooled across countries (stratified by country, so a country with more earthquakes does not drive the result). All rows are published, winners and losers, as the atlas does.

---

## 3. Founding-time uncertainty

This is the main technical risk. All 113 seeded founding times were placeholders. 65 candidate charts now exist for 29 countries; 8 countries have a candidate labelled "documented"; none has been opened by a maintainer.

### 3.1 How fast things change

Average figures. The engine computes the exact ones per chart.

| Quantity | Changes every | Consequence |
|---|---|---|
| D1 lagna | about 120 minutes | Needs time to about half an hour |
| D3 lagna | about 40 minutes | |
| D9 lagna | about 13 minutes | Needs time to a few minutes |
| D-n lagna in general | about 120/n minutes | D4 30, D5 24, D6 20, D7 17, D8 15 |
| Moon's D9 sign | about 6 hours (3°20' of Moon) | Lost with a date-only chart |
| Moon's nakshatra | about 24 hours (13°20') | A date-only chart leaves the first dasha lord open almost always |
| Sun's D9 sign | about 3.4 days | Usually survives a date-only chart |
| Slow grahas, D1 sign | weeks to years | Stable |

Chance that a varga lagna is the same across the whole window (window width over the change time):

| Time window | D1 | D2 | D3 | D4 | D7 | D9 |
|---|---|---|---|---|---|---|
| plus or minus 2 minutes | 97% | 93% | 90% | 87% | 77% | 70% |
| plus or minus 15 minutes | 75% | 50% | 25% | 0% | 0% | 0% |
| plus or minus 60 minutes | 0% | 0% | 0% | 0% | 0% | 0% |

So house-based work in D9 needs a founding time good to a few minutes. Very few countries will have one.

### 3.2 Dasha boundary uncertainty

Vimshottari starts from the Moon's place in its nakshatra. An error in the founding time moves the Moon, and that moves **every** later dasha boundary by the same amount:

`shift = (time error x Moon's speed / 13°20') x years of the first mahadasha lord`

With the Moon's mean speed this is **about 0.25 days per minute of time error per year of the first lord**: 1.5 days per minute if the first lord is the Sun (6 years), 5 days per minute if Venus (20 years).

| Time window | Boundary shift | Compare with |
|---|---|---|
| plus or minus 1 minute | 1.5 to 5 days | Shortest pratyantar 5.5 days; average 60 days |
| plus or minus 15 minutes | 23 to 75 days | Average pratyantar 60 days; shortest antar 110 days |
| plus or minus 60 minutes | 90 to 300 days | Average antar 1.5 years |
| plus or minus 12 hours (date only) | 3 to 10 years, and the first lord itself is usually unknown | Mahadasha 6 to 20 years |

Reading: maha and antar need the hour; pratyantar needs a few minutes; a date-only chart supports no dasha level.

Two conventions also move the boundaries. They are settings, not searches:

| Convention | Effect | Engine treatment |
|---|---|---|
| Ayanamsa | Each 1° of difference shifts all boundaries by 7.5% of the first lord's years (1.4 years for Saturn) | Lahiri is primary (project standard). Others run as named variants. |
| Dasha year | 360 days against 365.25 days: boundaries drift 1.4% a year, about 1 year after 68 years | Julian year is primary (`DashaYear.JULIAN`). 360-day year is a named variant. |

### 3.3 Chart grades

The grade is **computed from evidence fields** in the registry. It is never typed by hand (same rule as ADR-004 D-4).

| Grade | Evidence required | Default half-window | What can be analysed |
|---|---|---|---|
| A | A contemporaneous primary record (gazette, legal instrument, parliamentary record) states the time to the minute. A maintainer has opened it. Archive URL recorded. | 2 minutes, or as the record says | Everything, subject to the stability check |
| B | Contemporaneous press, or a secondary source that quotes a primary one, gives the time. | 15 minutes | D1 houses mostly; D9 planets; maha and antar. D9 lagna and pratyantar mostly unstable. |
| C | The time is known to the hour or the part of the day. | 60 minutes | Planet signs in D1 to D9 except the Moon's finer vargas; maha, most antar |
| D | Date only. | 12 hours | Slow-planet signs. No lagna, no houses, no dasha. |
| R | The time is rectified or chosen by an astrologer with no record. | as the author states | Case files only, labelled. See below. |
| X | The date itself is uncertain or disputed. | none | Excluded. Listed in the registry with the reason. |

Rules:

- **Rectified charts are circular.** A rectified time was fitted to past events. Testing it on those events proves nothing. A grade R chart enters the aggregate report only for events dated **after** the rectification was published, and only if the publication date is proved by an archive capture.
- **A chart applies only to events after its founding moment.**
- **One primary chart per country** is fixed in the plan before any outcome is read: highest grade; ties go to the candidate with the most named users. Other candidates are reported beside it. They are never searched for the best fit.
- The existing labels `documented`, `conventional`, `disputed` in `countries.yaml` are kept as the contributor's claim. The grade is what the evidence supports.

### 3.4 The stability check

For each chart, event and factor:

1. Evaluate the factor at the stated founding time, at both ends of the window, and on a grid of at most 1 minute inside it (grade D: 10 minutes).
2. The factor is **stable** if its value never changes. Otherwise it is **unstable**, and the case file shows each value with the share of the window it holds.
3. Dasha: the running lords at the event are stable when they are the same at both ends of the window. The shift is monotonic, so two evaluations are exact. The case file prints each boundary as an interval.
4. Aggregate report: **stable factors only** in the main table. A second table, clearly labelled, shows the result when unstable events are added at their stated-time value. If the two tables disagree, the main table wins.
5. A factor that is stable for under 80% of events for a chart is dropped from that chart's family as "untestable: founding time too coarse". This is decided from the chart and the calendar, before outcomes are read.

The event side has the same problem and the same treatment. An event dated to the day has no event-time lagna. A fast transit (Moon) is evaluated across the event's own time window and marked.

---

## 4. Method catalogue

### 4.1 What it is

One YAML file per method in `rules/mundane/methods/`. A **method** is a way to compute something (navamsa; Vimshottari; a transit counted from the natal Moon). A **rule** is a claim built from methods (existing `rules/mundane/**` files). A **factor** is a method with its parameters filled in, evaluated to true or false.

The engine refuses to compute a method that has no catalogue entry, and refuses to put a method below the required level into a tested family.

### 4.2 Citation status and ADR-004 levels

| Status | Meaning | ADR-004 level | Case file | Aggregate report |
|---|---|---|---|---|
| `unverified` | Chapter or author named from memory or from a secondary page. Nobody on the project has opened the text. | L0 | Shown with a warning badge | Not included |
| `page_cited` | Edition, translator, chapter, verse or page and a quotation are recorded, and a maintainer check is logged. Definition and parameters are written out. | L1 to L2 | Shown | Explore period only |
| `verified` | As above, and the computation passes reference cases, at least three of them against a manual Jagannatha Hora reading. | L3 and above (L4 when an outside astrologer attests it is faithful) | Shown | May enter a confirmatory family |

The status is computed from the entry's fields and fixtures, by the level code of ADR-004 WP-20 when that exists, and by the catalogue loader until then.

A second field, `tradition`, says where the method comes from. This matters because the classical mundane text (Brihat Samhita) does not use national founding charts at all, and BPHS is a text about people. Reading a nation's founding chart with vargas and Vimshottari is a twentieth-century practice. The engine supports it, and labels it honestly.

| `tradition` | Meaning |
|---|---|
| `samhita` | A mundane technique stated in a classical samhita text (sky-only: eclipses, mandalas, Kurma chakra, samvatsara) |
| `jataka_applied` | The computation is classical natal astrology (BPHS and similar). Applying it to a nation is modern practice. |
| `practitioner` | Stated by a named modern author, with book and page or dated URL |
| `western_mundane` | From the Perso-Arabic or Western mundane tradition |

### 4.3 Seed catalogue and today's honest status

Statuses below describe what the repository can prove today. Chapter numbers marked (m) are from memory or from a docstring with no page and no quotation, and must be checked at source (owner task H11).

| Id | Method | Source | Tradition | Status today | Tier | Code that exists |
|---|---|---|---|---|---|---|
| `varga.d1` | Rashi | BPHS ch. 6, Santhanam tr. 1984 (m) | jataka_applied | unverified source; computation golden-tested against PyJHora | core | `astrology/divisional.py` |
| `varga.d2` | Hora, Parashara (Sun's and Moon's hora only) | BPHS ch. 6 (m) | jataka_applied | same | core | same |
| `varga.d3` | Drekkana | BPHS ch. 6 (m) | jataka_applied | same | core | same |
| `varga.d4` | Chaturthamsa | BPHS ch. 6 (m) | jataka_applied | same | core | same |
| `varga.d7` | Saptamsa | BPHS ch. 6 (m) | jataka_applied | same | core | same |
| `varga.d9` | Navamsa | BPHS ch. 6 (m) | jataka_applied | same | core | same |
| `varga.d5`, `varga.d6`, `varga.d8` | Panchamsa, Shashthamsa, Ashtamsa | Not in BPHS's sixteen. Believed to be in the Tajika twelve-varga scheme (Tajika Nilakanthi) and in modern Jaimini-school books (m). | practitioner, until a text is page-cited | unverified; several rival computation rules exist | extended | none |
| `dasha.vimshottari` | Vimshottari, three levels | BPHS ch. 46 (m, as cited in `dasha/vimshottari.py`) | jataka_applied | unverified source; golden tests exist | core | `dasha/vimshottari.py`, predicate `dasha_lord_is` (levels 1 to 3) |
| `dasha.lord_state` | Dasha lord's natal house, lordship and dignity | BPHS dasha-result chapters (m) | jataka_applied | unverified | core | needs predicates (WP-52) |
| `transit.gochara_moon` | Transit sign counted from natal Moon | Phaladeepika ch. 26; Brihat Samhita ch. 104 (m) | jataka_applied | unverified | core | predicate `transit_in_house_from_natal` |
| `transit.from_lagna` | Transit sign counted from natal lagna | Modern practice; a source must be named | practitioner | unverified | core | same predicate |
| `transit.conjunct_natal` | Transit graha within orb of a natal point | Practitioner usage (existing rule files) | practitioner | unverified | core | predicate `transit_conjunct_natal` |
| `transit.over_varga` | Transit sign read against a natal varga lagna or varga position | No classical verse known to the architect | practitioner | unverified | extended | needs predicates |
| `transit.in_varga` | The transiting graha's own varga sign ("transit navamsa") against the natal varga | No classical verse known to the architect | practitioner | unverified | extended | needs predicates |
| `sky.bs32_mandala` | Earthquake classed by the Moon's nakshatra circle: Vayu, Agni, Indra, Varuna | Brihat Samhita ch. 32 vv. 8, 12, 16, 20, Iyer tr. 1884, read online 2026-11-08; lists confirmed in the incoming audit | samhita | page_cited once the check is logged; Bhat cross-check open | core | `astrology/mundane.py`, predicate `moon_mandala` |
| `sky.kurma` | Region by nakshatra, Kurma chakra | Brihat Samhita ch. 14, Iyer tr. 1884, read online | samhita | as above; the starting nakshatra is disputed and is a parameter | core | predicate `kurma_direction` |
| `sky.eclipse` | Eclipse near the event; eclipse on a natal point | Brihat Samhita ch. 5 (m) | samhita | unverified | core | `rules/eclipses.py`, predicates `eclipse_within_days`, `eclipse_in_sign` |
| `sky.samvatsara` | Sixty-year Jupiter cycle year | Brihat Samhita ch. 8 (as cited in `astrology/mundane.py`) | samhita | unverified; calendar convention is a parameter | core | `samvatsara`, predicate `samvatsara_is` |
| `sky.graha_yuddha` | Planetary war | Brihat Samhita ch. 17 (m) | samhita | unverified | extended | none |
| `annual.mesha_sankranti` | Chart of the Sun's entry into sidereal Aries, cast for the capital | B.V. Raman (title and pages to be recorded) | practitioner | unverified | phase 2 | `predicates/mundane.py: ingress` |
| `annual.chaitra_pratipada` | Chart of the lunar new year, and the year lord | Brihat Samhita ch. 19 (m); practitioner usage | samhita | unverified | phase 2 | `astrology/mundane.py: year_start` |
| `house.mundane_meaning` | What each house means for a nation (4th land, 8th calamity, 10th government) | Attributed to B.V. Raman and M.C. Jain in the AstroFusion registry; edition not identified | practitioner | unverified | core, labels only | rule `core.r008` (needs predicates) |
| `cycle.jupiter_saturn` | Jupiter-Saturn conjunction cycle | Perso-Arabic and Western mundane astrology; not an Indian classical method | western_mundane | unverified | extended, off by default | predicate `cycle_resonance` |
| `transit.ashtakavarga` | Transit strength by ashtakavarga points | BPHS ashtakavarga chapters (m) | jataka_applied | unverified | phase 3 | none |

### 4.4 Decisions on the charts

- **D1, D2, D3, D4, D7, D9 are classical.** They are six of Parashara's sixteen vargas. They are implemented and golden-tested. They are the core.
- **D2 is limited.** Parashara's hora has two signs only, so "houses in D2" has no meaning. D2 contributes one factor per graha: Sun's hora or Moon's hora.
- **D5, D6, D8 are not in BPHS's sixteen.** They are included as an **extended tier**, switched off until the owner records a text, edition and page that define each one (H11). The existing code deliberately raises on them. When cited, the definition is copied from the cited text, one rule per entry, and rival rules become named variants. Extended methods appear in the case file in a separate, labelled block. They never enter a confirmatory family. This meets the "D1 to D9" request without inventing a definition.
- **D10 and D30 are classical and relevant** (rulership; misfortune). They are outside the request and stay off by default. Each one added raises the search burden.
- **Other timing methods.** Included because they are documented mundane techniques: eclipses, samvatsara, the Mesha sankranti chart and the lunar new year chart. The Jupiter-Saturn cycle is not Indian classical; it is catalogued under its true tradition and kept off by default.
- **The Brihat Samhita ch. 32 mandala fits this engine exactly.** The text reads the mandala from an earthquake that has already happened ([INCOMING_AUDIT_2026-11-22.md](../research/handover/INCOMING_AUDIT_2026-11-22.md), line 118). The case file shows it as a classification of the event, which is what the text says. No forward-trigger claim is attached.

### 4.5 Catalogue entry contract

```yaml
id: varga.d9
name: {sanskrit: Navamsa, english: Ninth division}
family: varga                  # varga | dasha | transit | sky | annual | house | cycle
tradition: jataka_applied      # section 4.2
tier: core                     # core | extended | phase2 | phase3
source:
  text: Brihat Parashara Hora Shastra
  edition: Ranjan Publications, 1984
  translator: R. Santhanam
  chapter: "6"
  verse: null                  # or page
  quote: null                  # required for page_cited
  url: null
  archive_url: null
  checked_by: null             # maintainer name
  checked_at: null
definition:
  inputs: [sidereal_longitude]
  formula: >-
    Divide the sign into 9 parts of 3 deg 20 min. Part k (0-based) maps to
    start + k, where start is Aries for fire signs, Capricorn for earth,
    Libra for air, Cancer for water.
  conventions: {zodiac: sidereal, ayanamsa: lahiri, node: mean, houses: whole_sign}
  variants: []                 # named rival rules, each with its own source
implementation: {module: vedic_astrology_core.astrology.divisional, function: d9_navamsa}
predicates: [varga_sign]
needs: {founding_time_precision_minutes: 360, place: false}   # coarsest input for which it can be stable
change_period: "lagna 13 min; Moon 6 h; Sun 3.4 d"
reference_cases: [tests/fixtures/jhora/india_1947_d9.json]
scope: [case_file, aggregate]
notes: null
# citation_status and level are computed, never written here
```

---

## 5. The search burden

### 5.1 How big it is

The literal product in the request is D1 to D9 (9) x grahas (9) x houses (12) x dasha levels (3) = **2,916**. The real space is larger, because each chart can be read several ways.

| Block | Formula | Count |
|---|---|---|
| A Dasha lord identity | 9 lords x 3 levels | 27 |
| B Dasha lord's natal house from lagna | 3 levels x 9 vargas x 12 houses | 324 |
| C Dasha lord's natal house from Moon | 3 x 9 x 12 | 324 |
| D Dasha lord rules house h | 3 x 9 x 12 | 324 |
| E Dasha lord's dignity (5 states) | 3 x 9 x 5 | 135 |
| F Transit graha in house h from natal lagna of varga v | 9 x 12 x 9 | 972 |
| G Same, from natal Moon | 9 x 12 x 9 | 972 |
| H Transit graha conjunct or aspecting a natal graha in varga v | 9 x 9 x 2 x 9 | 1,458 |
| I Blocks F to H with the transit read in its own varga (D2 to D9) | 3,402 x 8 | 27,216 |
| J Event-sky factors (graha in sign, in nakshatra, pairs, retrograde, combust, mandala, tithi, eclipse) | | about 470 |
| **Single factors** | | **about 32,000** |
| Pairs: one dasha factor and one transit factor | 1,134 x 30,618 | about 35 million |
| Times candidate charts (up to 7), windows (3), ayanamsa (2), node model (2) | x up to 84 | |

Two consequences:

- **About 2,800 of the 32,000 are true at any moment.** Blocks B, C, F and G alone always give 216 true statements, because every graha is always in some house.
- **At p below 0.05 with no correction, about 1,600 factors would look significant by chance.**

A second, quieter fact: **the founding chart never changes.** "Saturn is in the 8th of India's navamsa" is true at every event and every control date. It cannot separate them. The natal vargas matter only as the frame for things that move: which dasha lord is running, and where the transiting grahas are. This removes all purely natal factors from the aggregate report. They stay in the case file.

### 5.2 Three slow-factor facts

| Factor | Runs since 1947 (India) | Status under ADR-004 D-6 (needs 8 or more episodes) |
|---|---|---|
| Mahadasha lord | 6 or 7 | Untestable in one country. Descriptive only. Testable only when pooled over many countries. |
| Antardasha lord | about 55 | Testable |
| Pratyantar lord | about 480 | Testable, if the founding time is good to a few minutes |

### 5.3 How the engine limits it

1. **Only catalogued methods.** No free grammar. Extended and unverified methods are outside every tested family.
2. **Pre-declared factor families.** The plan (`studies/mundane/hypothesis.yaml`, design task D6) lists every family before any outcome is read. The catalogue hash and the registry hashes are written into the plan. A method added later is exploratory for that data vintage.
3. **Partitions are tested as one question.** "Which house is the antardasha lord in?" has 12 answers that exclude each other. It is one omnibus test (permutation chi-square), not 12 tests. Cells are examined only if the omnibus test passes.
4. **Hierarchical testing.** Level 1: families, Benjamini-Yekutieli across families. Level 2: factors inside families that passed, Benjamini-Yekutieli at the level reduced by the share of families that passed. The single best factor is also given a Romano-Wolf adjusted p from the same permutations, as the atlas does.
5. **Budgets.** At most 24 omnibus tests in the first slice, 60 per country and event type, 200 in the whole programme per data vintage. The `burden` command prints the count and refuses a plan over budget.
6. **No pairs or triples by search.** A combination is tested only when a catalogued rule states it (for example "transit of the dasha lord over the natal 8th").
7. **Testability decided from the calendar.** At least 8 episodes, at least 3 events expected inside and outside the factor, stable for 80% of events. Otherwise "untestable", listed, outside the family.
8. **One confirm per plan lineage**, through the run seal of ADR-004 WP-03. Until WP-03 exists the engine has no confirm command at all.
9. **Engine calibration.** On simulated events with no effect, the whole report must flag something in at most 5% of runs (WP-55).

Proposed families for the first slice. The final list is fixed in D6 and may only use methods that have reached `verified` by then:

| Family | Omnibus tests | Note |
|---|---|---|
| Antar and pratyantar lord identity | 2 | Mahadasha shown, not tested |
| Dasha lord's natal house, D1 and D9, antar and pratyantar | 4 | D9 houses only if the chart's D9 lagna is stable |
| Dasha lord's dignity, D1 and D9, antar and pratyantar | 4 | |
| Transit of Mars, Jupiter, Saturn, Rahu by house from natal lagna and from natal Moon (D1) | 8 | Ketu is always opposite Rahu and adds nothing |
| Event-sky mandala | 0 | Already analysed on this catalogue (FINDINGS_LEDGER section 7). Shown, not re-tested. |
| **Total** | **18** | Under the cap of 24 |

### 5.4 Minimal detectable effect per event count

Smallest rate ratio found with 80% power. One-sided exact binomial on the count of events with the factor active, events treated as independent (declustered). "Duty" is the share of time the factor is active. The one-test column at 128 events and 25% duty reproduces ADR-005's figure of 1.63.

| Events | Duty 10%: one test | family of 24 | family of 60 | all 32,000 | Duty 25%: one test | family of 24 | family of 60 | all 32,000 |
|---|---|---|---|---|---|---|---|---|
| 10 | 8.4 | 18.5 | 18.5 | 48 | 6.2 | 16.0 | 33 | 133 |
| 20 | 4.1 | 8.0 | 9.7 | 14.4 | 3.2 | 7.3 | 9.2 | 15.9 |
| 30 | 3.6 | 5.8 | 6.7 | 10.0 | 2.9 | 5.0 | 5.7 | 9.0 |
| 50 | 2.9 | 4.4 | 4.8 | 6.2 | 2.3 | 3.4 | 3.7 | 5.1 |
| 100 | 2.1 | 3.0 | 3.2 | 3.9 | 1.7 | 2.4 | 2.5 | 3.2 |
| 200 | 1.7 | 2.3 | 2.4 | 2.8 | 1.5 | 1.9 | 2.0 | 2.3 |
| 500 | 1.4 | 1.7 | 1.8 | 2.0 | 1.3 | 1.5 | 1.5 | 1.7 |
| 1,000 | 1.3 | 1.5 | 1.5 | 1.7 | 1.2 | 1.3 | 1.4 | 1.5 |

Thresholds used: 0.05; Benjamini-Yekutieli rank 1 for 24 tests (5.5 x 10^-4) and for 60 tests (1.8 x 10^-4); Bonferroni for 32,000 (1.6 x 10^-6).

Reading:

- **Below 30 events, nothing realistic is detectable.** The report prints "descriptive only" and no p-value. This floor is fixed here.
- With 100 events and a planned family, a factor must double or triple the event rate.
- The existing Himalayan catalogue has **12** declustered mainshocks of M 6 and above in 1976 to 2026 (15 before declustering), about **7** of them in or near Nepal and about 5 in India (rough bounding-box counts; country assignment is WP-60). The first slice is therefore descriptive. To test anything on earthquakes the engine must pool countries or lower the magnitude threshold (the catalogue has 186 mainshocks at Mw 5.2 and above). Either choice is made in the plan, before outcomes are read.

---

## 6. Data contracts

All registries are committed, hashed with `core/stats/manifest.py: file_sha256`, and listed in the plan. Outside material arrives through `research/incoming/` and is promoted by the ADR-004 WP-10 validator (`python -m tools.ingest validate ... --promote`) into `data/registry/mundane/`. Nothing in `research/incoming/` is read by the engine. WP-10 is not built yet; until it is, the two seed scripts in WP-49 are the only writers, and they copy only from committed files.

### 6.1 Country chart registry: `data/registry/mundane/charts.yaml`

Seeded from `studies/mundane/data/countries.yaml` (which stays untouched; it carries the upstream stamp).

```yaml
- chart_id: in-1947-midnight          # never reused
  country_iso: IN
  event: Independence Act takes effect
  founding:
    date: "1947-08-15"
    time: "00:00:00"                  # null for date-only
    time_zone: Asia/Kolkata           # IANA zone, or LMT (then local mean time from lon)
    place: New Delhi
    lat: 28.6139
    lon: 77.2090
  time_evidence:
    kind: primary_record | press | secondary | convention | rectified | none
    stated_precision_minutes: 1       # what the source itself supports
    source: {title: ..., url: ..., archive_url: ..., accessed: ..., quote: ...}
    checked_by: null                  # maintainer who opened the source
    checked_at: null
    rectified: false
    rectification_published: null     # date, with archive proof, when rectified is true
  half_window_minutes: null           # optional override; otherwise from the grade
  used_by: [...]                      # practitioners, as in countries.yaml
  claimed_confidence: documented      # the contributor's label, kept
  valid_from: "1947-08-15"            # chart applies to events on or after this
  notes: ...
# grade (A, B, C, D, R, X) is computed by core/mundane/registry.py
```

### 6.2 Event registry: `data/registry/mundane/events.jsonl`

| Field | Meaning |
|---|---|
| `event_id` | Stable id (`usgs:<id>`, `wd:<qid>`, ...) |
| `event_type`, `subtype` | Controlled list: `earthquake`, `flood`, `war_start`, `coup`, `disaster`, `market_move` |
| `country_iso` | Where it happened (a list when it crosses borders). Not the crawl group. |
| `time_utc`, `time_precision` | Instant and `minute`, `hour`, `day`, `month` |
| `lat`, `lon`, `location_precision_km` | Needed for an event-time sky chart |
| `severity` | `{scale: Mw, value: 7.8}`; deaths or loss where the catalogue gives them |
| `cluster_id` | Parent event for aftershocks or one continuing episode |
| `catalogue` | `{name, inclusion_rule, snapshot_sha256}` |
| `exhaustive` | True only when the catalogue has a stated inclusion rule that does not depend on fame |
| `source_url`, `archive_url` | Primary record and its archive capture |
| `reviewed_by`, `reviewed_at` | A person confirmed the type and date |

Rules:

- **Only `exhaustive` events enter the aggregate report.** A hand-picked list of famous events is biased toward memorable dates. Hand-picked events get case files only. The 825 seeded events are of this kind until matched to a catalogue.
- Earthquakes come from the hashed USGS snapshot (later ISC-GEM, ADR-004 WP-25). Country is assigned from the epicentre with the committed world-atlas snapshot.
- Sources for wars and coups must be chosen and their licences read (owner task H14).

| Event type | Likely exhaustive source | Blocker |
|---|---|---|
| Earthquake | USGS ComCat snapshot (in the repo) | None for the Himalayan arc. **The global catalogue stays untouched** until the registered Varuna-mandala test has run (ADR-004 D2). |
| Flood | Dartmouth Flood Observatory | ADR-004 D-8 firewall. Case files are allowed. Any event-against-factor count is not, until the owner decides (H13). |
| Gold move | Gold price series | ADR-004 WP-12. Gold has no country; only event-sky factors apply. |
| War start, coup | Academic conflict and coup datasets | H14 |
| Disaster | EM-DAT | Licence |

### 6.3 Method catalogue

Section 4.5. One file per method in `rules/mundane/methods/`.

### 6.4 Outputs

| Output | Path | Committed |
|---|---|---|
| Case file JSON | `studies/mundane/artifacts/cases/<event_id>__<chart_id>.json` | No (rebuilt from hashes); a small reviewed set is copied to `site/data/mundane_cases/` |
| Case file HTML, PDF | beside the JSON | No |
| Case file schema | `studies/mundane/casefile.schema.json` | Yes |
| Control dates | `studies/mundane/artifacts/controls_<plan_sha12>.csv` with manifest | No; reproducible from seed and plan |
| Aggregate report | `studies/mundane/artifacts/results.json`, `factor_table.csv` | `results.json` yes, as other studies |
| Burden report | `studies/mundane/artifacts/burden.json` | Yes |

Case file JSON, top level:

```json
{"schema": "casefile/1",
 "event": {"event_id": "...", "time_utc": "...", "time_precision": "minute", "...": "..."},
 "chart": {"chart_id": "in-1947-midnight", "grade": "A", "half_window_minutes": 2},
 "settings": {"ayanamsa": "lahiri", "node": "mean", "houses": "whole_sign", "dasha_year": "julian"},
 "natal": {"points": [{"point": "Lagna", "longitude": 0.0,
            "vargas": {"D1": {"sign": "Taurus", "house": 1, "stable": true, "alternatives": []}}}]},
 "dasha": {"levels": [{"level": 1, "lord": "...", "start": "...", "end": "...",
            "boundary_uncertainty_days": 9.5, "stable": true}]},
 "transits": [{"graha": "Saturn", "longitude": 0.0, "retrograde": false,
               "house_from_lagna": 3, "house_from_moon": 1, "readings": {}}],
 "event_sky": {"lagna": "...", "moon_nakshatra": "...", "mandala": "varuna", "tithi": 7},
 "factors": [{"factor_id": "...", "method": "dasha.lord_state", "citation_status": "unverified",
              "level": "L0", "fired": true, "stable": true, "base_rate": 0.25, "evidence": "..."}],
 "claims": [],
 "provenance": {"charts_sha256": "...", "events_sha256": "...", "catalogue_sha256": "...", "commit": "..."}}
```

---

## 7. Modules, study folder and CLI

### 7.1 New package `core/mundane/`

The existing `core/astrology/mundane.py` (tables for Kurma, mandalas, samvatsara) stays where it is.

| Module | Responsibility | Reuses |
|---|---|---|
| `catalogue.py` | Load and check method files; compute citation status; refuse uncatalogued methods | `rules/schema.py: Source`, `rules/levels.py` (WP-20, when built) |
| `registry.py` | Load chart and event registries; compute grade and window; chart-to-event applicability | `stats/manifest.py` |
| `charts.py` | Founding chart table: lagna and nine grahas in each varga, house from the varga lagna, dignity | `astrology/divisional.py: varga_sign`, `rules/context.py: Sky`, `rules/predicates/placement.py: dignities_of` |
| `dasha.py` | Lords and boundaries at the event to level 3; boundary intervals | `dasha/vimshottari.py: compute_vimshottari_nested_periods`, `get_vimshottari_chain_at` |
| `transits.py` | Transit table for each catalogued reading | `rules/context.py`, `astrology/aspects.py` |
| `eventsky.py` | Event-time chart at the event's place | `astrology/mundane.py: mandala_of, samvatsara`, `rules/eclipses.py` |
| `annual.py` (phase 2) | Mesha sankranti and lunar new year charts for the capital | `astrology/mundane.py: year_start`, predicate `ingress` |
| `stability.py` | The check of section 3.4 | |
| `factors.py` | Turn catalogue entries and rule files into evaluated factors with evidence sentences and base rates | `rules/engine.py: explain_condition`, `rules/grid.py: GridEvaluator` |
| `controls.py` | Draw and freeze control dates C1; placebo charts C3 | `stats/nulls.py`, `stats/controls.py: shifted_sky` |
| `aggregate.py` | The pattern report and hierarchical testing | `stats/multiplicity.py`, `stats/permutation.py`, `stats/rates.py`, `stats/power.py` |
| `burden.py` | Count factors and tests; MDE table; budget check | `stats/power.py: minimum_detectable_rate_ratio` |
| `casefile.py`, `render.py` | Build the JSON; render HTML from a template with no new dependency; PDF through Quarto | ADR-004 WP-17 PDF script when built |
| `cli.py` | `astro-mundane` | |

### 7.2 How the workbench and the atlas are reused

- **One rule engine.** A factor is a `conditions` tree of existing predicates, evaluated by `rules/engine.py` for one moment (case file) and by `GridEvaluator` over a time grid (base rates, controls). No second evaluator (ADR-004 WP-13).
- **Evidence sentences** in the case file are the `ExplainNode` text the workbench already produces.
- **New predicates** go into `rules/predicates/` with the others, so rule authors and the browser workbench get them too (WP-52).
- **Existing rule files** in `rules/mundane/` fire in the case file when their status is `active` and each method they use is catalogued.
- **From the atlas:** the testability rule, the shared-offset circular shift, the Romano-Wolf step and the "publish every row" habit. The atlas grammar itself is not reused; the catalogue replaces it.
- **Study adapter:** `rules/studyadapter.py` gets a `mundane` branch in a later package (WP-63) so `astro-rules fit` and `confirm` can run on mundane rules under the same guards.

### 7.3 Study folder

```
studies/mundane/
  hypothesis.yaml          plan v1 (design task D6): charts, events, families, controls, split, budgets
  casefile.schema.json
  scripts/build_registry.py   seed the two registries from committed files
  scripts/run_slice.py        the first slice end to end
  artifacts/                  cases/, controls_*.csv, results.json, factor_table.csv, burden.json
  data/, sources/             unchanged
```

Two legacy files, `studies/earthquake/data/india_dasha_periods.csv` and `nepal_dasha_periods.csv`, start the first mahadasha at the founding moment. That is the old algorithm that `dasha/vimshottari.py` replaced. The engine must not read them.

### 7.4 CLI: `astro-mundane`

Run as `python -m vedic_astrology_core.mundane.cli` until ADR-004 WP-18 adds the entry point.

| Command | Does | Reads outcomes? |
|---|---|---|
| `validate` | Checks registries, catalogue and plan; prints grades and statuses | No |
| `catalogue list / show <id>` | Methods with source, status, level, what is missing for the next level | No |
| `chart <chart_id>` | Founding chart table D1 to D9 with stability marks | No |
| `casefile <event_id> [--chart <id> or all] [--format json,html,pdf]` | One case file | One event |
| `burden --plan <file>` | Factor and test counts, MDE table, budget check | No |
| `controls --plan <file>` | Draws and freezes control dates | Event dates only |
| `report --plan <file> --period explore` | Aggregate report on the explore period | Yes |
| `report ... --period confirm` | Once per plan lineage. Not available until WP-63. | Yes |

---

## 8. Work packages WP-48 onward

Ground rules are those of ADR-004: run only the named tests; shared files have one owner (only WP-18 edits `pyproject.toml`; `_quarto.yml` order is WP-30, WP-19, WP-28, WP-33, then WP-62); "implementer (Sonnet)" unless a concrete subtle risk is named, then "senior-implementer (Opus)"; no subagent on Fable. Packages may not commit under `data/snapshots/` or `research/incoming/`.

### Design tasks and owner tasks

| Id | Who | Output | Needed by |
|---|---|---|---|
| D6 | Architect | `studies/mundane/hypothesis.yaml` v1 for the first slice: primary-chart rule, event definition, families, windows, controls, split, budgets, MDE table. Replaces the draft. | WP-55, WP-56 |
| D7 | Architect | Phase 2 plan: pooled countries, annual charts, other event types | WP-59 to WP-61 |
| H10 | Owner | Founding times with primary sources and archive captures. First India (the record of the midnight transfer of power), then Nepal (hour of the 2008-05-28 Constituent Assembly declaration; hour of the 2015-09-20 promulgation). Through `research/incoming/mundane/`. | WP-49; grade A or B |
| H11 | Owner | Open the texts and record edition, page and quotation for: BPHS varga chapter and Vimshottari chapter; Brihat Samhita ch. 32 in Bhat; the exact title and pages of the B.V. Raman and M.C. Jain mundane works; a defining text for each of D5, D6, D8. | `page_cited`; WP-58 |
| H12 | Owner | Manual Jagannatha Hora readings of the India chart, D1 to D9, and the dasha at three events (extends ADR-004 H3) | `verified` (L3) |
| H13 | Owner | Decide whether floods stay behind the ADR-004 D-8 firewall (Registered Report) or enter this report. Not both. | WP-60 |
| H14 | Owner | Choose exhaustive war and coup datasets; record licences (extends H4) | WP-60 |
| H15 | Owner | An astrologer reads three case files and says what is missing or mislabelled (extends H2) | WP-54 sign-off |

### First slice: India, Himalayan earthquakes M 6 and above, D1 + D9 + Vimshottari

Why India first: it is the only South Asian country with a candidate chart whose time is a documented legal moment (1947-08-15 00:00 IST, New Delhi), and it is already the atlas's reference chart. Nepal has no candidate with a time of day. Nepal is the second case in the slice: the 2015-04-25 Gorkha earthquake against the date-only 2008 chart, to show what a grade D chart can and cannot support.

The slice needs **no unbuilt package** from ADR-004 or ADR-005.

Until H10 is done, no source has been opened, so the India chart grades C (60-minute window). Its D1 lagna and its pratyantar will then show as unstable. That is the correct output, and it is the reason H10 comes first.

#### WP-48 Method catalogue: schema, loader, seed entries
- **Files (new):** `core/mundane/__init__.py`, `core/mundane/catalogue.py`, `rules/mundane/methods/*.yaml` (the entries of section 4.3), `tests/test_mundane_catalogue.py`.
- **Acceptance:** strict schema, unknown keys rejected; `citation_status` and `level` are computed and a file that types them fails; every `implementation` path imports; a `core` entry with no `definition.formula` fails; chapters marked (m) in section 4.3 load as `unverified`; D5, D6 and D8 load as `extended` with no implementation, and asking the loader to compute them raises with the message "not cited"; the catalogue hash is stable across runs.
- **Tests:** `tests/test_mundane_catalogue.py`, `tests/test_rules_schema_v2.py`.
- **Depends on:** none (uses WP-20's level code if present). **Implementer:** implementer (Sonnet).

#### WP-49 Chart and event registries
- **Files (new):** `core/mundane/registry.py`, `studies/mundane/scripts/build_registry.py`, `data/registry/mundane/charts.yaml` (India and Nepal candidates), `data/registry/mundane/events.jsonl` (Himalayan M 6 and above from the committed USGS snapshot, raw and declustered flags), `tests/test_mundane_registry.py`.
- **Acceptance:** contracts of sections 6.1 and 6.2 enforced; grade computed from evidence, with a test per grade; an unchecked source can never grade above C; a rectified chart is excluded from aggregate use before its publication date; a chart is refused for an event before `valid_from`; `LMT` is converted from longitude; `studies/mundane/data/countries.yaml` is not modified (the upstream stamp test still passes); the seed script is deterministic and writes hashes.
- **Tests:** `tests/test_mundane_registry.py`, `tests/test_mundane_data.py`, `tests/test_upstream_stamp.py`.
- **Depends on:** none. **Implementer:** implementer (Sonnet).

#### WP-50 Founding chart table, D1 and D9 first
- **Files (new):** `core/mundane/charts.py`, `tests/test_mundane_charts.py`.
- **Acceptance:** for a chart and a list of vargas, returns lagna and nine grahas with sign, house from the varga lagna, dignity; uses `divisional.varga_sign` only; any varga whose catalogue entry is not computable raises; a date-only chart returns planets with no lagna and no houses; D2 returns the hora lord and no houses; values for the India chart match the existing PyJHora golden data for D1 and D9.
- **Tests:** `tests/test_mundane_charts.py`, `tests/test_golden_vargas.py`.
- **Depends on:** WP-48, WP-49. **Implementer:** implementer (Sonnet).

#### WP-51 Dasha at the event and the stability check
- **Files (new):** `core/mundane/dasha.py`, `core/mundane/stability.py`, `tests/test_mundane_dasha.py`, `tests/test_mundane_stability.py`.
- **Acceptance:** lords and boundaries to level 3 equal `get_vimshottari_chain_at`; moving the founding time by t minutes moves every boundary by the formula of section 3.2 within 1%; a boundary interval that contains the event marks that level unstable; a factor that flips on a single minute inside the window is caught (test with a lagna placed 30 seconds from a D9 boundary); grade D charts report every dasha level as unsupported; all datetimes are timezone-aware and a naive one raises.
- **Tests:** the two test files, `tests/test_vimshottari_dasha_nested.py`.
- **Depends on:** WP-49, WP-50. **Implementer:** senior-implementer (Opus). Risk: time zones and local mean time; window edges; a wrong "stable" mark silently turns noise into data.

#### WP-52 Predicates for dasha lords and transits over vargas
- **Files:** `core/rules/predicates/timing.py`, `core/rules/predicates/mundane.py`, `core/rules/context.py` (natal varga helpers), `rules/schema.json` (regenerated), `tests/test_mundane_predicates.py`, `tests/test_rules_predicates.py`.
- **Acceptance:** new predicates `dasha_lord_in_house`, `dasha_lord_rules_house`, `dasha_lord_dignity` (each with `level` 1 to 3, `varga`, `from` lagna or Moon) and `transit_aspects_natal`; `transit_in_house_from_natal` gains optional `varga` and `transit_varga`, both defaulting to 1; every existing rule file loads and evaluates unchanged; each predicate's docstring names its catalogue id; a varga that is not computable raises.
- **Tests:** the two test files, `tests/test_rules_catalog.py`, `tests/test_rules_loader.py`.
- **Depends on:** WP-48. If WP-20 also regenerates `rules/schema.json`, the later one regenerates it again. **Implementer:** senior-implementer (Opus). Risk: a changed default alters every existing rule that uses these predicates.

#### WP-53 Event-time sky chart
- **Files (new):** `core/mundane/eventsky.py`, `core/mundane/transits.py`, `tests/test_mundane_eventsky.py`, `tests/test_mundane_transits.py`.
- **Acceptance:** lagna at the event's place only when time precision is hour or better; Moon nakshatra, mandala (through `mandala_of`), tithi, weekday lord, nearest eclipse each side, samvatsara; transit table per catalogued reading, with extended readings in a separate block; fast factors evaluated across the event's own time window and marked; **any aggregate count of an event-sky factor over events outside the Himalayan polygon raises** until the ADR-004 D2 test has its confirm record.
- **Tests:** the two test files, `tests/test_mundane_predicates.py`.
- **Depends on:** WP-48, WP-49. **Implementer:** implementer (Sonnet).

#### WP-54 Case file builder and renderers
- **Files (new):** `core/mundane/factors.py`, `core/mundane/casefile.py`, `core/mundane/render.py`, `core/mundane/templates/casefile.html`, `studies/mundane/casefile.schema.json`, `tests/test_mundane_casefile.py`.
- **Acceptance:** JSON validates against the schema; the nine sections of 2.1 are present, and a section that cannot be computed says why; every fired factor carries method id, citation status, level, stability, base rate and the evidence sentence from the rule engine; unverified and extended methods are visibly labelled in HTML; HTML is one self-contained file and needs no network; rendering never recomputes (HTML from the same JSON is byte-identical on two runs); PDF is produced by Quarto from the JSON and is skipped with a clear message if Quarto is absent.
- **Tests:** `tests/test_mundane_casefile.py`.
- **Depends on:** WP-50, WP-51, WP-52, WP-53. **Implementer:** implementer (Sonnet).

#### WP-55 Controls, burden count and the aggregate report
- **Files (new):** `core/mundane/controls.py`, `core/mundane/burden.py`, `core/mundane/aggregate.py`, `tests/test_mundane_controls.py`, `tests/test_mundane_burden.py`, `tests/test_mundane_aggregate.py`.
- **Acceptance:** control dates follow C1 exactly, are reproducible from seed and plan hash, and never fall within the exclusion gap of an event; placebo charts C3 implemented; `burden` reproduces the counts of section 5.1 for the full D1 to D9 setting and the MDE table of 5.4 within rounding, and fails a plan over budget; the report has every column of 2.2; under 30 events it prints "descriptive only" and no p-value; purely natal factors are rejected from families; partitions are tested as one omnibus test; family size can never shrink silently (test); on 200 simulated no-effect datasets with clustered events the report flags anything in at most 5% plus three binomial standard errors; a planted rate ratio of 3 on 100 events is found in at least 80%; explore period only.
- **Tests:** the three test files, `tests/test_stats_multiplicity.py`.
- **Depends on:** WP-51, WP-52, D6. **Implementer:** senior-implementer (Opus). Risk: matched-set permutation done wrongly; family size; leakage of confirm-period events into the explore report.

#### WP-56 CLI and the slice run
- **Files:** `core/mundane/cli.py` (new), `studies/mundane/scripts/run_slice.py` (new), `studies/mundane/README.md`, `tests/test_mundane_cli.py` (new). Entry point `astro-mundane` named for WP-18.
- **Acceptance:** the commands of 7.4 except `report --period confirm`, which exits with "not available until WP-63"; the slice run writes case files for every Himalayan M 6 and above mainshock in India against each India candidate chart, the Gorkha 2015 case file against the Nepal 2008 chart, `burden.json` and a descriptive `factor_table.csv`; `results.json` is marked provisional when the tree is dirty; the README states the event count, the grade of each chart used and "descriptive only".
- **Tests:** `tests/test_mundane_cli.py`, `tests/test_mundane_pipeline.py`.
- **Depends on:** WP-54, WP-55. **Implementer:** implementer (Sonnet).

**Gate S (owner):** read three case files with an astrologer (H15). Check that every method shown has its true status. Only then widen.

### Phase 2: widen

#### WP-57 Ingest contracts for charts, events and citations
- **Files:** `tools/ingest/contracts.py` (add `mundane_charts`, `mundane_events`, `method_citations`), `tools/ingest/mundane.py` (new), `research/incoming/README.md` (add the `mundane` topic), `tests/test_ingest_mundane.py` (new), fixtures.
- **Acceptance:** validates sections 6.1, 6.2 and the `source` block of 4.5; rejects a founding time with no source, a quotation with no page, a home-page URL; `--promote` writes only accepted, person-checked rows into `data/registry/mundane/` and the method files; regenerates `MANIFEST.csv` hashes; no network in tests.
- **Depends on:** WP-10, WP-48, WP-49. **Implementer:** implementer (Sonnet).

#### WP-58 Remaining vargas
- **Files:** `core/mundane/charts.py`, `core/astrology/divisional.py` (a separate `EXTENDED_VARGA_FUNCTIONS` table; the sixteen stay as they are), `rules/mundane/methods/varga.d5.yaml`, `d6`, `d8`, `tests/test_mundane_charts.py`, `tests/test_golden_vargas.py`.
- **Acceptance:** D2, D3, D4, D7 added to the chart table and case file; D5, D6, D8 implemented **only for entries that are `page_cited`**, each exactly as its quoted definition, golden-tested against the matching PyJHora option; `VARGA_FACTORS` and `calculate_vargas` unchanged, so every existing caller gets the same answer.
- **Depends on:** WP-50, WP-57, H11. **Implementer:** implementer (Sonnet).

#### WP-59 Annual charts and slow cycles
- **Files (new):** `core/mundane/annual.py`, `tests/test_mundane_annual.py`.
- **Acceptance:** instant of the Sun's sidereal Aries ingress agrees with JPL Horizons fixtures to 5 arcseconds; chart cast for the capital; lunar new year chart and year lord as the cited text defines them; eclipse-on-natal-point factor; each is computed only when its catalogue entry is `page_cited` or better.
- **Depends on:** WP-54, H11, D7; WP-21 for Horizons fixtures. **Implementer:** implementer (Sonnet).

#### WP-60 More countries and event types
- **Files:** `studies/mundane/scripts/build_registry.py`, `core/mundane/registry.py`, `data/registry/mundane/*`, `tests/test_mundane_registry.py`.
- **Acceptance:** epicentre-to-country assignment from the committed atlas snapshot, tested on border cases; war and coup events from the datasets chosen in H14 with `exhaustive: true` and an inclusion rule; floods only as H13 decides; gold moves only after WP-12, with country left empty; seeded Wikipedia events stay `exhaustive: false`.
- **Depends on:** WP-49, WP-57, H13, H14; WP-11 for snapshots; WP-12 for gold. **Implementer:** implementer (Sonnet).

#### WP-61 Pooled report, placebo charts, convention variants
- **Files:** `core/mundane/aggregate.py`, `core/mundane/controls.py`, `tests/test_mundane_aggregate.py`.
- **Acceptance:** pooled test stratified by country; mahadasha lord becomes testable only when pooled episodes reach 8; placebo-chart rank reported for every family; named variants (ayanamsa, 360-day dasha year, true node) reported through `stats/speccurve.py` and never used to pick a winner; calibration test of WP-55 repeated for the pooled design.
- **Depends on:** WP-55, WP-60, D7. **Implementer:** senior-implementer (Opus). Risk: pooling lets one country's event rate masquerade as a factor effect.

#### WP-62 Site pages
- **Files:** `site/mundane_cases.qmd`, `site/mundane_patterns.qmd` (new), `scripts/export_site_data.py`, `_quarto.yml` (after WP-33), `tests/test_site_pages.py`.
- **Acceptance:** a browsable set of reviewed case files; the full factor table with base rates and verdicts; the method catalogue with statuses; each export has a `_meta` block with input hashes; no confirm-period statistic is exported before the confirm run.
- **Depends on:** WP-56; `_quarto.yml` order. **Implementer:** implementer (Sonnet).

#### WP-63 Confirm run
- **Files:** `core/mundane/cli.py`, `core/mundane/aggregate.py`, `core/rules/studyadapter.py` (mundane branch), `tests/test_mundane_confirm.py` (new), `tests/test_rules_studyadapter.py`.
- **Acceptance:** one confirm per plan lineage through the WP-03 seal; refuses a dirty tree, a catalogue or registry hash that differs from the plan, a family below `verified`, and under 30 confirm events; a version bump does not reset it.
- **Depends on:** WP-03, WP-23, WP-61. **Implementer:** senior-implementer (Opus). Risk: holdout leakage.

#### WP-64 Housekeeping
- **Files:** `docs/adr/ADR-005-pattern-discovery-and-claims-registry.md` (header line "Amended by ADR-006"), `docs/research/FINDINGS_LEDGER.md` (mundane row), `docs/research/PAPER_ROADMAP.md` (mundane line), `studies/README.md`.
- **Acceptance:** each file points to this ADR; no number is changed; WP-30's label for the mundane study reads "in build: retrospective engine, descriptive only".
- **Depends on:** WP-56. **Implementer:** implementer (Sonnet).

### Order

| Wave | Packages | Notes |
|---|---|---|
| S1 | WP-48, WP-49 | No shared files. Can start now. |
| S2 | WP-50, WP-52, WP-53 | WP-52 touches `core/rules/`; keep it apart from ADR-004 WP-13, WP-20, WP-22, WP-23 sessions. |
| S3 | WP-51, then WP-54 | |
| S4 | WP-55 (needs D6), then WP-56 | |
| Gate S | Owner | |
| P2 | WP-57 (after WP-10), WP-58, WP-59, WP-60 | Each waits on its owner task. |
| P3 | WP-61, WP-62, WP-64 | |
| P4 | WP-63 | After ADR-004 WP-03 and WP-23. |

---

## 9. Consequences

Good:

- The owner gets what was asked: every past event read through D1 to D9, three dasha levels, transits and the event sky, from named methods only.
- A reader can see, per method, whether its source has been opened. Nothing is passed off as classical.
- Every fired factor is shown beside its base rate, so a case file cannot overstate itself.
- Founding-time doubt becomes visible per cell instead of being hidden in a noon placeholder.
- The work is smaller than ADR-005 Phase A and needs no unbuilt package to start.

Costs and risks:

- **Most of the catalogue starts as `unverified`.** Until the owner opens the texts (H11), the aggregate report has no confirmatory family at all. The case file still works, with warning badges.
- **Few countries will reach grade A or B.** D9-lagna and pratyantar factors will be "untestable" for most charts.
- **The first slice has 5 to 12 events.** It cannot test anything. It is an engineering slice and a reading aid.
- **Case files invite storytelling.** The base-rate column and the labels are the only defence. The astrologer review (H15) should check they are noticed.
- Applying natal methods to nations is modern practice. Some classical scholars will not accept the frame. The `tradition` field says so in every file.
- Seventeen packages for one developer, nine of them in the first slice.
- Items written from memory in this ADR, to be checked at source before use: every chapter number marked (m) in section 4.3; the attribution of D5, D6 and D8 to the Tajika scheme; the gochara references; the titles of the Raman and Jain mundane works; the hierarchical false-discovery procedure (Yekutieli 2008; Benjamini and Bogomolov 2014); the names of conflict and coup datasets.

---

## 10. What changes in ADR-005

ADR-005 answered "can we build our own predictive model?". The owner has now said no forecasting is wanted. ADR-005 stays as the record of that feasibility answer. Its build plan is amended as follows.

| ADR-005 part | Status now | Reason |
|---|---|---|
| Sections 1 and 2 (feasibility numbers; the calendar traps) | **In force** | They are the reason this engine has controls |
| E-1 "build the ledger first" | **Superseded.** The retrospective engine is built first. | Owner's scope |
| E-2 fitted model form; E-4 nested walk-forward search | **Deprioritised** | Nothing is fitted or searched here |
| E-3 feature grammar v2 | **Replaced** by the method catalogue and declared families | "No invented techniques" |
| E-5 holdout levels | Kept as vocabulary. Level 3 (live data) is not pursued. | |
| E-6 scoring against baselines | **Deprioritised**, except where a baseline defines an event or a control (below) | |
| E-7 model registry (WP-38) | **Deprioritised** | No models |
| E-8 live forecast ledger (WP-39, WP-40, WP-41) | **Deprioritised.** Not deleted; can be revived by a new ADR. | No forecasts |
| E-9 kill criteria | K1 (calibrate on simulated no-effect data) is kept, inside WP-55. K2 to K6 lapse with the search. | |
| Claims registry (WP-31, WP-32; spec) | **Kept, unchanged** | Past claims are retrospective data. Section 8 of the case file reads them. |
| WP-33 site pages | Claims page and findings page kept. Forecast-ledger page dropped. | |
| WP-34 scoring extensions | **Deprioritised** | |
| Baselines WP-35 (ETAS), WP-36 (market), WP-37 (rain) | **Kept as optional controls.** ETAS rates can weight earthquake control dates; the past-only volatility baseline defines a "gold move". Not needed for the first slice. | |
| Phase B and C (WP-42 to WP-46), WP-47 null report | **Deferred with no date** | |
| D4, H7 | Lapse with Phase B. D5, H8, H9 (claims) stay. | |

Unchanged elsewhere:

- The registered Varuna-mandala test on the untouched global catalogue (ADR-004 D2) stays. This engine protects it (WP-53 guard).
- ADR-004 D-1 said the mundane study is a note, not a paper. That stays true until an aggregate report on at least 30 exhaustive events has run. ADR-004 D-4's sentence "a prospective forecast ledger opens when P1 is submitted" is deferred to the owner.
- ADR-004 D-8 (flood firewall) stays until the owner decides H13.

---

## 11. Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Case files only, no controls | Every event "shows something" (about 2,800 true statements). The output would be unfalsifiable. |
| Test all 32,000 single factors and correct | With 100 events the detectable rate ratio is above 3; with 30 it is 9 or more. Nothing real would survive, and the run would burn the data. |
| Use the "best-fitting" candidate chart per country | That is rectification by another name. It multiplies the search by the number of candidates. |
| Treat noon or midnight placeholders as real times | The review's finding on this study. Lagna, D9 and dasha would be noise presented as data. |
| Implement D5, D6, D8 now from a software library's default | Rival rules exist. Picking one without a cited text is inventing a technique. |
| Apply only Brihat Samhita, because national charts are not classical | It would refuse the owner's request (D1 to D9 and dasha of a country). The `tradition` field gives honesty without refusal. |
| Include purely natal factors in the report | They are constant per country and cannot separate event dates from control dates. |
| Compare countries with each other on natal factors | A handful of countries, confounded with geology and history. |
| Keep the ADR-005 ledger as the first build | The owner does not want forecasts. It can be revived later without loss. |
| A new rule evaluator inside `core/mundane/` | A second engine was review flaw M9. The workbench predicates are reused. |
