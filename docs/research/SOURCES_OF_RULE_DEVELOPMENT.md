# Sources of rule development

How the rules, the candidate national charts and the papers in this repository
are sourced, and how AI-generated research reports are used and not used.

## The principle

Every claim that enters a rule, a dataset or a paper cites the **root source** it
traces to:

- a **classical text**, with chapter and verse and the edition or translation
  used (for example Brihat Samhita 14.2, tr. N. Chidambaram Iyer, 1884);
- a **named practitioner's** dated post, video or article, with its URL;
- a **journal article** (with DOI when it has one) or a **dataset** (with DOI
  or URL).

The bibliography is [`papers/sources.bib`](../../papers/sources.bib). The
tests in `tests/test_sources_bib.py` check that it parses and that every
practitioner rule's source URL and cited keys resolve to an entry in it.

The AstroFusion application, which is proprietary, runs rule registries
without citations. This open repository does the opposite on purpose: nothing
is tested or published here unless a reader can follow it back to its origin
and disagree with it.

## Tiers and labels

- **classical**: the rule's `source` names a text **and** a chapter. Only
  classical rules are used for confirmatory claims in the papers.
- **experimental**: everything else. All practitioner rules are experimental.
  Their `source` is the practitioner's statement (URL, name, title, date); the
  classical text they invoke, if any, is in `notes.root_source` with its bib
  key. A practitioner who cites a classical text does not make a rule
  classical: the text has to say it.
- **status**: `active` (conditions written, reference cases computed with
  `astro-rules explain`); `needs_predicates` (the vocabulary cannot express it
  yet, the missing predicates are listed); `needs_verification` (a case is in
  doubt).
- **reference cases** record what the engine says (sidereal Lahiri, mean
  nodes, whole-sign houses). When that differs from what the practitioner's
  statement implies, the case note says so ("DISAGREES with the claim"). The
  case is kept: it is evidence about the claim, the chart or the zodiac used.
- **checked**: `true` only when a maintainer has opened the page. Most
  practitioner pages were located but not yet opened; they carry
  `checked: false`.

National-chart candidates in `studies/mundane/data/countries.yaml` carry
`confidence`: `documented` (time from a record of the day), `conventional`
(midnight, noon or untimed) or `disputed` (rectified, contradictory, or of
unstated origin). No candidate replaces a country's `founding` block until a
maintainer promotes it.

## Commissioned surveys (held locally, not published)

On 2026-11-08 the owner commissioned AI-generated survey reports to find out
where to look. They are **held locally by the owner, not committed, and never
cited as evidence**. Every claim taken from them was traced to a root source
first; claims that could not be traced are listed below.

| Report | Generator | Date | Prompt topic |
|---|---|---|---|
| Charting the Contenders: national horoscopes | Gemini Deep Research | 2026-11-08 | National charts in use for about 40 countries, with disputes |
| The Praxis of Prediction: Vedic mundane practitioners 2015-2026 | Gemini Deep Research | 2026-11-08 | Practitioners' methods on social media, 2015 to today |
| From Celestial Signs to Terrestrial Maps: earthquakes and floods | Gemini Deep Research | 2026-11-08 | Earthquake and flood predictions, post-hoc explanations, sky-to-map methods |
| Financial Astrology Market Forecasting Survey | Gemini Deep Research | 2026-11-08 | Forecasts for gold, silver, oil and indices; audits and academic tests |
| Gold, silver and markets | Grok | 2026-11-08 | Same financial topic |
| Earthquake prediction algorithm; earthquake map; event data sources; scientific data mapping; ayanamsa validation | Deep Research format, generator not recorded | about 2025-12-27 (older notes) | Geodetic and data-engineering background |

The reconstructed prompts and the handling convention are in
[`studies/mundane/sources/README.md`](../../studies/mundane/sources/README.md).

## What came from where

- **Candidate national charts**: 65 candidates for 29 countries, each with
  the practitioner page or record it came from
  (`studies/mundane/data/countries.yaml`; summary in
  `countries_candidates_summary.md`).
- **Practitioner rules**: `rules/mundane/practitioner/` and
  `rules/financial/practitioner/`, one file per rule:

| Rule | Status | Practitioner source (bib key) | Root source |
|---|---|---|---|
| `financial.practitioner.crawford_solar_eclipse_shock` | active | Larry Berman reporting Arch Crawford (`berman2017eclipse`) | none cited |
| `financial.practitioner.gidel_mercury_three_pass_degree` | needs_predicates | Susan Abbott Gidel (MoneyShow) (`gidel2020superbirthday`) | none cited |
| `financial.practitioner.india_mars_mahadasha_markets` | active | Prashant Kapoor (Instagram) (`kapoor2025reel`) | `bphs_santhanam` |
| `financial.practitioner.jupiter_combust_nifty_cooling` | active | unnamed author (Scribd upload) (`scribd2026niftywindow`) | none cited |
| `financial.practitioner.jupiter_saturn_conjunction_and_waxing_square` | active | Raymond Merriman (MMA Cycles) (`mma_worldstock`) | `ptolemy_tetrabiblos` |
| `financial.practitioner.jupiter_virgo_gold_rise_2016` | active | astrologicalmusings.com (`astrologicalmusings2016newyear`) | none cited |
| `financial.practitioner.kartik_amavasya_debilitated_mars_aspect` | active | astrologicalmusings.com (`astrologicalmusings2026kartik`) | none cited |
| `financial.practitioner.lunar_phase_new_moon_returns` | active | Yuan, Zheng and Zhu (2006), Journal of Empirical Finance (`yuan2006moonstruck`) | `yuan2006moonstruck` |
| `financial.practitioner.mars_jupiter_ketu_leo_bullion_volatility` | active | astrologicalmusings.com (`astrologicalmusings2026kartik`) | none cited |
| `financial.practitioner.mercury_retrograde_market_chop` | active | Raymond Merriman (MMA Weekly Gold sample) (`mma2024weeklygold`) | `mahendra2021mercury` |
| `financial.practitioner.merriman_jupiter_leo_precious_metals` | needs_predicates | Raymond Merriman (MMA Cycles) (`mma2026aug10`) | none cited |
| `financial.practitioner.merriman_solar_lunar_reversals` | needs_predicates | Raymond Merriman (MMA Weekly Gold sample) (`mma2024weeklygold`) | none cited |
| `financial.practitioner.mma_venus_retrograde_station_turn` | active | Raymond Merriman (MMA weekly, via lecochonsideral) (`mma2026weekly`) | none cited |
| `financial.practitioner.mma_venus_saturn_hard_aspect_dip_buy` | active | Raymond Merriman (MMA Cycles) (`mma2026aug17`) | none cited |
| `financial.practitioner.nyse_dasha_turning_points` | needs_predicates | Barry William Rosen (`rosen_sacredtraders`) | `bphs_santhanam` |
| `financial.practitioner.panchak_five_day_trend` | needs_predicates | unnamed author (Scribd presentation) (`scribd_panchak`) | none cited |
| `financial.practitioner.rahu_ketu_sign_shift_nifty_risk` | active | unnamed author (Scribd upload), naming Ashish Mehta and Prashant Kapoor (`scribd2026niftywindow`) | none cited |
| `financial.practitioner.sarvatobhadra_vedha_commodities` | needs_predicates | YouTube video (channel not named in the extract) (`youtube_sbc`) | none cited |
| `financial.practitioner.tempora_jupiter_cancer_gold_peak` | active | Tempora Research (`tempora2026goldjupiter`) | none cited |
| `financial.practitioner.tempora_jupiter_own_sign_gold_bull_peak` | active | Tempora Research (`tempora2026goldjupiter`) | none cited |
| `financial.practitioner.vyapar_ratna_inverse_dignity_gold` | active | AstroCapitalX (`astrocapitalx_commodity`) | `trivedi_ojha_vyaparratna` |
| `mundane.practitioner.bs32_agni_mandala_earthquake` | active | Dr. R.P. Sharma (`drrpsharma_earthquakes`) | `brihatsamhita_iyer1884` |
| `mundane.practitioner.eclipse_on_sensitive_degree_delayed_trigger` | needs_predicates | Paramarsh (`paramarsh_nationalcharts`) | none cited |
| `mundane.practitioner.eclipses_virgo_pisces_us_venezuela` | needs_predicates | Thea Anderson (Substack) (`anderson2026predictions`) | none cited |
| `mundane.practitioner.elliott_mars_uranus_gemini_2026` | needs_predicates | Todd Elliott, The Cunning Farmer (Substack) (`elliott_cunningfarmer`) | none cited |
| `mundane.practitioner.india_lunar_eclipse_10th_pm_resignation` | active | astrologicalmusings.com (author not named on the extract) (`astrologicalmusings2025marsdasha`) | none cited |
| `mundane.practitioner.india_saturn_over_natal_rahu_border_tension` | active | astrologicalmusings.com (`astrologicalmusings2025marsdasha`) | none cited |
| `mundane.practitioner.kapoor_graha_yuddha_koorma_northwest` | needs_predicates | Prashant Kapoor (AstroKapoor) (`astrokapoor_earthquake`) | `brihatsamhita_iyer1884` |
| `mundane.practitioner.ketu_4th_lord_12th_territory_loss` | needs_predicates | Anvaya Jyotish (`anvaya_nationalcharts`) | none cited |
| `mundane.practitioner.kurma_north_sector_malefics` | active | AstroRidhis (`astroridhis_kurma`) | `brihatsamhita_iyer1884` |
| `mundane.practitioner.maheshri_geocentric_angles_m7` | needs_predicates | Jagdish Maheshri (via Saptarishis) (`maheshri_saptarishis`) | `maheshri_eqmodel` |
| `mundane.practitioner.mars_in_rohini_weak_monsoon` | active | astrologicalmusings.com (`astrologicalmusings2019saptanadi`) | `brihatsamhita_iyer1884` |
| `mundane.practitioner.mars_jupiter_ketu_leo_nov_2026` | active | astrologertripathi.com (`tripathi2026genz`) | none cited |
| `mundane.practitioner.mars_saturn_conjunction_scorpio_2016` | active | astrologicalmusings.com (`astrologicalmusings2016newyear`) | none cited |
| `mundane.practitioner.raman_eighteen_earthquake_configurations` | needs_predicates | VedAstro (`vedastro_earthquake`) | `raman_weather_earthquakes` |
| `mundane.practitioner.sapta_nadi_saturn_jala_cyclone` | needs_predicates | DKScore Jyotish Medium (`dkscore2024weather`) | `rath_predicting_rain` |
| `mundane.practitioner.saturn_5th_or_11th_youth_unrest` | active | astrologertripathi.com (`tripathi2026genz`) | none cited |
| `mundane.practitioner.solar_eclipse_purva_phalguni_southeast` | active | astrologicalmusings.com (`astrologicalmusings2016koorma`) | `brihatsamhita_iyer1884` |
| `mundane.practitioner.sun_afflicted_10th_lord_dusthana_regime_change` | needs_predicates | Anvaya Jyotish (`anvaya_nationalcharts`) | none cited |

- **Disagreements** between practitioners:
  `rules/mundane/practitioner/DISPUTES.md`,
  `rules/financial/practitioner/DISPUTES.md`; exchange charts in
  `rules/financial/practitioner/CHARTS.md`.
- **Dated prediction cases**: `studies/mundane/sources/prediction_cases.csv`.

## Mapping methods (sky to geography)

How practitioners turn a sky position into a place. None of these is in the
engine yet; each needs a predicate or a lookup table built from its root text.

- **Kurma (Koorma) Chakra**, the tortoise wheel: nine regions, three
  asterisms each; malefics in a region's asterisms afflict it. Root:
  Varahamihira, *Brihat Samhita* ch. 14 (Kurma-vibhaga), tr. Iyer 1884
  (`brihatsamhita_iyer1884`; verse 2 puts Krittika, Rohini and Mrigashira in
  the centre). Practitioner tables differ from the text (see DISPUTES).
- **Asterism-to-people and region lists**: *Brihat Samhita*'s lists of what
  each asterism governs (online at wisdomlib.org; chapter number not yet
  verified for this repository).
- **Earthquake mandalas**: four groups of seven asterisms (Vayu, Agni, Indra,
  Varuna), each with its own regions. Root: *Brihat Samhita* ch. 32
  (Bhukampa-lakshana). Encoded for the Agni group as
  `bs32_agni_mandala_earthquake`.
- **Sapta Nadi Chakra** (seven weather channels over 28 asterisms) and the
  **Rohini Chakra** (rain): presented by Sanjay Rath (`rath_predicting_rain`);
  the classical source of the chakra is not named there.
- **Sanghatta and Kota Chakras**: used for direction of an earthquake and for
  war; presented in K.N. Rao's circle (Journal of Astrology articles 499 and
  591); the classical root is not named in what was found.
- **Sarvatobhadra Chakra**: a 9x9 grid of asterisms, letters, signs and
  tithis; vedha lines link a planet to a commodity or a place. Root text not
  yet identified.
- **Country ruling signs**: Ptolemy, *Tetrabiblos* book II (`ptolemy_tetrabiblos`).
- **Geodetic equivalents** (Sepharial): Greenwich at 0 Aries on the
  Midheaven, each degree of longitude to a degree of the zodiac; and
  **astrocartography** (Jim Lewis). Western, tropical; not encoded.

## Untraced claims (21)

Claims found in the surveys that could not be traced to a root source. They
are not in any rule, chart list or paper. Each can move into the rules once
someone finds the root and cites it.

1. **R.G. Krishnan's gold rules (bullish with Mars, Jupiter or Sun in own, exalted or friendly signs, benefic aspects, certain retrogrades, Rahu in watery signs; bearish in the reverse)** No page, article or book by R.G. Krishnan was found (web searches 2026-11-08). Kept out of the rules; the direct-strength side of the dispute is represented by Tempora Research.
2. **'Jupiter in Cancer, or in favourable houses from Aries or Capricorn, supports gold for months to a year', attributed to Future Point, Prajna Jyothi and Vedic Siddhanta** No page from those sites located. The Jupiter-in-Cancer claim is encoded from Tempora Research instead (`tempora_jupiter_cancer_gold_peak`).
3. **Saturn-Jupiter cycle claims attributed to Future Point** No page located; the cycle rule is encoded from Merriman (MMA).
4. **'One peer-reviewed Indian study (Nifty, Sensex 1998-2018) found positive returns and asymmetry during Mercury retrograde'** The paper is traced (Mahendra, Mohanty and Sudalaimuthu 2021, doi:10.1007/s10690-020-09310-8) but its findings were not read; the stated result stays untraced.
5. **NYSE variants at about 10:10 and 08:52 LMT, and Astro-Databank's 'conflicting times' rating** No page located; listed in `rules/financial/practitioner/CHARTS.md` as untraced.
6. **Jupiter mahadasha of the NYSE chart associated with the 1980s-1990s bull market 'in some accounts'** No account named.
7. **Nifty chart 22 April 1996 09:15 Mumbai; S&P 500 futures first trade 21 April 1982 Chicago** No practitioner page named.
8. **A personal back-test on X (thousands of trades, 29 event types, placebo shifts) finding most events null and a marginal NYSE-transit signal** No link or author given.
9. **'Saturn in Rohini is a classic Vedic indicator of massive disasters'** Only an anonymous Scribd upload is cited; no practitioner or verse.
10. **'Seven planets in water signs in D1, or all nine in D9, is a critical threshold for tsunamis'** No named source.
11. **'The Taurus-Scorpio axis is the most notorious for earthquakes; Saturn in fixed signs is particularly dangerous'** Cited to a course PDF and a Scribd upload without an author.
12. **Geodetic rule: a fault inside a solar eclipse's path of totality is sensitised and triggered when Mars crosses the eclipse degree** No practitioner named; the geodetic method itself traces to Sepharial (see mapping methods).
13. **Nigeria national chart for the return to civilian rule, 29 May 1999** The only citation is an unrelated history paper; left out of `countries.yaml`.
14. **United Kingdom chart for 'the unification under King Edgar in 927'** The 927 unification is usually credited to Aethelstan, and no date or time is given; left out.
15. **Merriman reading the Mars-Jupiter-Ketu alignment in Leo for 14-25 November 2026** The citation points at an unrelated video; the Vedic statement of the same alignment is encoded from astrologicalmusings.com.
16. **Dr. Ashish Patni: Jupiter-Rahu conjunction in Cancer gives Bank Nifty a 90.9% win rate and +14.8% mean 90-day return** Only the site's home page is cited, and in 2026 Rahu is in Aquarius, so the conjunction as stated cannot be checked; not encoded.
17. **Pandit Hardeo Sharma Trivedi chose midnight 15 August 1947 as the auspicious moment for India's independence** Facebook group post only; noted, not relied on.
18. **The Ptolemaic three-tier hierarchy of Jupiter-Saturn conjunctions (20, 200, 800 years)** Attributed to Ptolemy without a passage; `ptolemy_tetrabiblos` is cited with that caveat.
19. **Prashant Kapoor's 'M7.2 Uttarakhand earthquake of 12 February 2021'** No such event is known to the maintainers; recorded in `prediction_cases.csv` to be matched against USGS before scoring.
20. **Arch Crawford's call of the October 1987 crash** Cited in secondary literature without the primary newsletter; not used.
21. **Vishal Aksh's Panchottari dasha 'based on Brihat Parashara Hora Shastra'** Chapter and verse not given; recorded as a dispute only.

## The book in the owner's reading folder

The owner also holds a PDF titled *Mundane Astrology Book: A Book for
Astrologers* by K.B. Gopalakrishnan (Chennai; author's site sathyaprema.com),
copyrighted, not in this repository. Only its title page and table of
contents were read, to check whether it is the source behind the chapter
numbers of the AstroFusion mundane rule registry (registry chapter 4: elemental
hazards and eclipses; 5: eclipse impact and the Himalaya; 6: factions; 7:
governance and the Himalayan tract; 8: capital resilience; 9: power shift and
vocabulary; 10: geopolitics and the dvi-dvadasha axis).

Its contents list chapters 4 "How to predict for elections", 5 "Oath taking
charts", 6 "Predicting mass death", 7 "Earthquakes", 8 "Predicting wars",
9 "Yearly predictions" and 10 "Predicting sports events" (also 1 "A broad
view of mundane astrology areas", 2 "How to become a very good astrologer",
3 "Celebrity horoscope - an analysis", 11 "How to predict rains", 12 "Why
India is what it is", 13 "Predictions of 2005", 14 "Hits of 2006",
15 "Miscellaneous predictions", 16 "List of horoscope of nations and states
of India").

**Finding: the chapters do not match.** No chapter of the book lines up with
the registry chapter of the same number. There is topical overlap without a
numbering match (oath charts are book chapter 5 but registry chapter 7;
elections and coalitions are book chapter 4, factions are registry chapter 6;
earthquakes are book chapter 7, hazards are registry chapter 4). The book is
therefore **not** identified as the registry's source; the registry rules
keep their "edition not identified" note.
