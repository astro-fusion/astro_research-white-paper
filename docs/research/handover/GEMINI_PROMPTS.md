# Handover prompts for Gemini (Antigravity) — next research phase

Written 2026-11-22. Paste the **Shared rules** block followed by ONE topic prompt per session.
Ask Gemini to save its outputs under `research/incoming/<topic>/` (nothing it produces is trusted until a maintainer checks the sources and converts the rules with `astro-rules validate`).

Why these exist: the current gold, silver and earthquake studies are null on short, single-source data with only astrological regressors. A publishable next round needs (1) longer, licensed data, (2) the known non-astrological drivers as controls, (3) astrology rules stated precisely enough to compute, and (4) dated ex-ante forecasts by astrologers that can be scored out of sample.


---

## Shared rules for every prompt (paste this block above each prompt)

You are a research assistant feeding an open, pre-registered scientific project that tests Vedic (sidereal, Lahiri) astrology claims against real data. The project reports null results honestly; your job is to collect evidence and claims, not to prove astrology right or wrong.

Hard rules:
1. Never invent a number, date, quote, verse or URL. Every row needs a working source URL (or a book with edition, chapter, verse/page). If you cannot find it, write "NOT FOUND" — a gap is useful, a fabrication destroys the paper.
2. Separate EX-ANTE predictions (published, dated BEFORE the event) from EX-POST explanations (written after). Record the publication date of every astrological claim. Ex-post claims are kept but labelled; only ex-ante claims count as evidence.
3. For every dataset give: provider, exact series ID, frequency, start/end date, units, time zone and sampling time (e.g. "LBMA PM fix 15:00 London"), licence/terms of use (can it be redistributed in a public GitHub repo? yes/no/unclear), and download method (API endpoint, CSV link, needs account).
4. Astrology must be stated precisely enough to compute: zodiac (sidereal/tropical), ayanamsa, node model (mean/true), orb in degrees, which chart (transit-only, a national chart, a "gold chart", an ingress chart), time window before/after, and expected direction and size of the effect. Vague claims ("Jupiter is good for gold") are recorded but marked "not computable" with what is missing.
5. Prefer primary sources: classical texts in a named translation (e.g. Brihat Samhita tr. M. Ramakrishna Bhat; BPHS tr. R. Santhanam), and the practitioner's own book/article/video with timestamp.
6. Output in the exact file formats requested (CSV with the given columns; YAML following the rule template). No prose padding. At the end, add a "Gaps and doubts" section.

Rule template (one per astrological claim; the project's rules/schema.json is the authority):
```yaml
id: <domain>.<short_snake_name>
name: <human name>
domain: financial | seismic | mundane | general
claim: <one sentence, the testable claim>
source: {text: <book or author>, edition: <...>, chapter: <...>, verse: <...>, url: <...>, published: <YYYY-MM-DD>}
tier: classical | practitioner | experimental
params:            # every number the astrologer chose, with a plausible range
  orb: {value: 8, min: 2, max: 12, step: 1, unit: deg}
conditions: <plain-language list of planetary conditions; exact degrees/signs/houses/nakshatras>
window: {unit: days, before: 0, after: 30}
expected_effect: {series: gold_usd | quake_rate | rainfall | flood_events, direction: up | down | volatility | count_up, size: <if stated>}
reference_cases:   # dates the author says it worked (fires) and did not apply (silent)
  - {moment: <ISO datetime UTC>, expect: fires, note: <author's words + URL>}
ex_ante: true | false

---

## Prompt 1 — Gold: price history, major up/down episodes, and the non-astrological drivers

Context: the project's gold study currently uses only Yahoo COMEX front-month futures (GC=F), daily, 2000-09-05 to 2026-10-30 (6,150 bars), because the FRED LBMA series GOLDPMGBD228NLBM returned HTTP 404. It tests next-day log return, absolute return and "extreme move" (|return| above the past-250-day 95th percentile) against 14 planetary indicators, with explore 2000–2015 and confirm 2016–2026. Result: null. We need a longer, cleaner series and the macro drivers, so an astrology effect can be tested AGAINST known economics, not in a vacuum.

Tasks:
A. Price series. Find the best public sources, with licence, for:
   - LBMA Gold Price AM and PM (USD, GBP, EUR) from 1968-04-01 to today (where is it now that FRED dropped it? LBMA/ICE, World Gold Council, Nasdaq Data Link, Bundesbank, Kitco?).
   - COMEX gold futures settlement, volume and open interest (CFTC Commitments of Traders for positioning).
   - Gold in INR (MCX India, IBJA daily rates, RBI) and CNY (Shanghai Gold Exchange SGE Au99.99), back as far as available.
   - Intraday/hourly gold (XAU/USD) free sources, if any.
   - World Bank Pink Sheet monthly gold (we already have it; confirm the series and start date).
B. Major moves catalogue. Build gold_episodes.csv of every major gold move from 1968 to today:
   columns: episode_id, direction (bull|bear|crash|spike), start_date, peak_or_trough_date, end_date, start_price_usd, extreme_price_usd, pct_change, max_drawdown_pct, duration_days, series_used, macro_narrative (one line), key_drivers (e.g. "Fed hikes; real yields up; USD up"), sources (URLs)
   Use an objective definition and state it (e.g. bull/bear = >=20% move from a pivot; also list every single-day move >= 4%). Must include at least: 1971 Nixon shock, 1979–80 peak and 1980–82 crash, 1999 Washington Agreement, 2008 GFC drop and rebound, 2011-09 peak, 2013-04 crash, 2015-12 low, 2020-08 peak, 2022 drawdown, 2024–2026 central-bank-led rally and any 2025–2026 records and corrections, with exact dates.
C. Drivers (daily or monthly series with IDs): US 10y TIPS real yield (FRED DFII10), DXY/broad dollar (DTWEXBGS), CPI, Fed funds and FOMC meeting dates, VIX, S&P 500, oil (Brent), Geopolitical Risk Index (Caldara–Iacoviello), Economic Policy Uncertainty, gold ETF holdings (GLD, World Gold Council ETF flows), central-bank purchases (WGC/IMF IFS quarterly), India import duty changes, Indian festival/wedding demand dates (Akshaya Tritiya, Dhanteras/Diwali, wedding season) 1990–2027.
D. Models literature (2015–2026, peer-reviewed or strong working papers): what currently best explains/forecasts gold returns and volatility? Cover GARCH/EGARCH/GJR-GARCH with exogenous variables, HAR-RV, Markov regime switching, quantile regression, machine learning with walk-forward validation, and calendar/lunar anomalies in gold (e.g. Dichev & Janes 2003 lunar returns; Yuan, Zheng & Zhu 2006; any gold-specific lunar/Diwali/weekday studies). For each: citation, DOI, data, sample, out-of-sample result, effect size.
E. Recent context (2024–2026): list the dated news events behind every gold record high and every drop of more than 5% in this period (central-bank buying, tariffs, Fed decisions, wars), with sources.

Deliver: sources_gold.csv (dataset, provider, series_id, freq, start, end, units, tz_sampling_time, licence, redistributable, url), gold_episodes.csv, drivers.csv (same columns as sources), literature_gold.csv (citation, doi, method, data, sample, oos_result, effect_size, notes), and a short Gaps and doubts list.

---

## Prompt 2 — Gold: what serious astrologers say, with exact formulas

Context: the project already has these gold/market rules encoded (check for duplicates, add what is missing): Venus-Jupiter conjunction within 8°, Venus own sign, Venus/Mercury/Mars/Jupiter/Saturn retrograde, Venus/Jupiter combust, Sun exalted (Aries)/debilitated (Libra)/own sign (Leo), Jupiter exalted (Cancer)/debilitated (Capricorn), and practitioner rules from Merriman (Jupiter in Leo precious metals; solar-lunar reversals), Crawford (solar eclipse shock), Gidel (Mercury three-pass degree), Tempora (Jupiter in Cancer/own sign gold peak), MMA (Venus retrograde station turn; Venus-Saturn hard aspect dip), Vyapar Ratna (inverse dignity for gold), Sarvatobhadra Chakra vedha on commodities, Panchak five-day trend, Mars-Jupiter-Ketu in Leo bullion volatility, new-moon returns, Rahu-Ketu sign shift.

Tasks:
A. Classical sources. Find every classical statement on gold (suvarna/hema), silver, metals, prices (argha/arghakanda), or scarcity/abundance of commodities in: Brihat Samhita (Varahamihira; esp. the chapters on commodity prices "Arghakanda" and on planetary transits), Bhadrabahu Samhita, Meghamala, Vyapar Ratna (Hardev Sharma Trivedi), Jyotish Tattva/Mundane texts (B.V. Raman "Mundane Astrology", Kalidas?). For each: text, translation used, chapter/verse, the Sanskrit term, the literal translation, and your operationalisation as a rule (planet, sign/nakshatra, which month/ingress, direction of price).
B. Modern practitioners (Vedic and Western financial astrology): K.N. Rao school, C.S. Patel / Sarvatobhadra market methods, Bepin Behari, Ray Merriman, Bill Meridian, Arch Crawford, Christeen Skinner, Louise McWhirter (ingress/node cycle), W.D. Gann (planetary cycles in commodities), Indian TV/YouTube market astrologers who publish DATED gold forecasts. For each method: exact formula (planets, aspects with orbs, signs, nakshatras, harmonic, ingress/eclipse/lunation charts, which "gold chart" if any — e.g. the 1971 or 1974 US gold legalisation, COMEX gold futures start 1974-12-31, Sun as the gold karaka), claimed lead/lag, claimed success examples with dates.
C. Track record. Collect DATED ex-ante gold forecasts by named astrologers 2010–2026 (prediction text, publication date and URL, target window, predicted direction/level), so we can score them against the price later. Aim for 50+ predictions. Do not score them yourself; just record them.
D. Specifically for major moves: for each episode in the gold episode list (1971, 1980 peak, 2008, 2011 peak, 2013 crash, 2020 peak, 2022 low, 2024–2026 rally), what did astrologers say BEFORE and AFTER? Which configurations do they cite (e.g. Jupiter-Saturn conjunctions 1980/2000/2020, Saturn-Neptune, Jupiter in Cancer 2013–14/2025–26, Rahu-Ketu axis, eclipses)? Record with dates and sources.
E. Disagreements: where practitioners contradict each other (e.g. Jupiter retrograde bullish vs bearish for gold), list both sides with sources.

Deliver: rules_gold/*.yaml (one file per claim, template above), gold_forecasts_exante.csv (astrologer, published_date, url, quote, target_start, target_end, predicted_direction, predicted_level, method_cited), episode_astrology_claims.csv (episode_id, astrologer, published_date, ex_ante, configuration_cited, quote, url), disputes.md, Gaps and doubts.

---

## Prompt 3 — Earthquakes: catalogues and the astrological earthquake theories

Context: the project's earthquake study uses the USGS ComCat catalogue 1976–2026, M>=4 (completeness-corrected), depth <=70 km, in a band along the Himalayan Main Frontal Thrust (74–96°E), declustered with Gardner–Knopoff and Zaliapin–Ben-Zion. It tests 13 indicators: Mars-Saturn and Mars-Ketu conjunctions, eclipse windows, Sun ingress, stations of Mars/Mercury/Venus/Jupiter/Saturn, and the Moon in the four Brihat Samhita ch.32 nakshatra mandalas (Vayu, Agni, Indra, Varuna), plus tidal positive controls. Explore 1976–2010, confirm 2011–2026. Result: null; Varuna mandala had the highest rate ratio in both periods but did not survive correction.

Tasks:
A. Catalogues (with licence): ISC-GEM (homogeneous Mw, 1904–present), ISC Bulletin, NEIC, GCMT, India's National Center for Seismology (NCS/IMD) catalogue, Nepal DMG/NSC catalogue, China CENC for Tibet, historical Himalayan great earthquakes before 1900 (Bilham; Ambraseys & Jackson) with uncertainties. Also global M>=7 since 1900 for a global replication.
B. Science baseline: the best-documented real astronomical influence on earthquakes — tidal triggering (Ide et al. 2016 Nature Geoscience; Tanaka; Cochran et al. 2004) — with effect sizes, so the project's tidal positive control can be compared. Also any peer-reviewed tests of planetary alignment/eclipse/lunar-phase triggering, and their results.
C. Classical theory: Brihat Samhita ch.32 (Bhukampa lakshana) — the exact nakshatra lists of the four mandalas, the claimed signs, lead times (e.g. effects within N days/weeks), regions; Bhadrabahu Samhita; Narada/Garga Samhita if available. Give verse-level citations and translation.
D. Modern astrologers: B.V. Raman ("eighteen earthquake configurations"), Maheshri (angles M7), Kapoor (graha yuddha and Koorma chakra), Indian astrologers who forecast Nepal 2015, Turkey 2023, Myanmar 2025, etc. Exact formulas, orbs, and DATED ex-ante predictions (place, date window, magnitude claimed) with URLs; aim for 50+.
E. Score-ready list: for every M>=7 earthquake in the Himalaya–Tibet–Myanmar region since 1897, list any published prediction that preceded it.

Deliver: sources_quake.csv, literature_quake.csv, rules_quake/*.yaml, quake_forecasts_exante.csv (astrologer, published_date, url, quote, region, window_start, window_end, magnitude_claimed, method), Gaps and doubts.

---

## Prompt 4 — Floods, monsoon and rainfall: data and the astrological rain theories (new study)

Context: the project has no flood study yet. It already encodes a few rules: Mars in Rohini → weak monsoon, Sapta Nadi chakra with Saturn → cyclone (jala nadi), Ashadha lunar transit weather predictor, Stambha yogas for agriculture, Samvatsara "king planet" economic/agricultural index. We need to know if a flood/monsoon study is feasible and what to test.

Tasks:
A. Data (with licence and series IDs): IMD all-India and sub-divisional monsoon rainfall (IITM/IMD, 1871–present), IMD monsoon onset dates over Kerala 1901–present, Nepal DHM rainfall, EM-DAT and Dartmouth Flood Observatory event lists for India/Nepal/Bangladesh/Pakistan, GloFAS/ERA5 river discharge, Indian cyclone tracks (IMD RSMC best tracks 1891–present), ENSO and IOD indices (the main physical drivers, to be used as controls).
B. Science baseline: how much of Indian monsoon variance ENSO/IOD explain; known lunar/tidal links to rainfall (e.g. lunar-phase rainfall studies) with effect sizes.
C. Classical theory, verse-level: Brihat Samhita ch.21–28 (garbha lakshana / rain pregnancy, garbha dharana, pravarshana, Rohini yoga, Swati yoga, Ashadhi yoga, sadyo varsha), Meghamala, Sapta Nadi Chakra, Adra (Ardra) pravesha chart, Samvatsara king and minister of rain (meghesha). For each: exact rule (which nakshatra/tithi/month, which planet, observation window, predicted lag e.g. "195 days after garbha"), and how to compute it.
D. Modern practitioners and Panchang publishers who forecast monsoon quality each year (e.g. yearly Panchang "varsha phal", Indian astrologers on TV/YouTube); collect DATED ex-ante forecasts for 2000–2026 (year, predicted rainfall category, flood/drought regions) to score against IMD data.
E. Feasibility: propose the primary outcome (e.g. JJAS all-India rainfall anomaly categorised deficient/normal/excess; or annual count of major floods), the sample size, and which classical rule is best defined for a pre-registered test.

Deliver: sources_flood.csv, literature_flood.csv, rules_flood/*.yaml, monsoon_forecasts_exante.csv (source, published_date, url, year, predicted_category, regions, method), feasibility.md, Gaps and doubts.

---

## Prompt 5 — Methods, licences and literature questions from the internal review

Context: an internal review (RESEARCH_REVIEW_2026-11-22.md at the repo root) found that the gold study's Yahoo GC=F series is thin before 2008 (46 bars in 2000, 83 "daily" returns spanning more than 4 days), that the one gold "discovery" was a permutation-count artefact, and that slow planetary indicators give very few independent episodes. Answer each question below with sources (URL/DOI), the exact series codes or terms, and a one-line verdict. Mark anything you cannot verify as NOT FOUND.

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

Deliver: answers.md (one section per question number), plus any new rows for sources_*.csv and literature_*.csv in the formats used by Prompts 1–4.
