# Audit of the Gemini research outputs, 2026-11-22

The outputs of the four Gemini sessions (gold prices, gold astrology, earthquakes, floods) are now in `research/incoming/{gold_prices,gold,earthquake,flood}/`. That folder is gitignored, so this audit is the tracked record. The flood session first wrote its files to the repo root and `studies/monsoon/`. The root copies were identical to the `studies/monsoon` ones and were removed; the rest were moved to `research/incoming/flood/`.

The checks were automatic:
- every DOI was resolved on Crossref and its authors and title compared with the citation;
- every URL was fetched;
- for every ex-ante forecast, the cited page was searched for any run of 6 consecutive words from the quote.

## Verdict

**Treat everything as leads, not data.** The structure of the work is good: the right datasets, the right literature, sensible feasibility reasoning, and honest gap lists. But the specific citations and quotes fail checking at a rate that rules out using any row without a human or agent confirming it at the source.

| File | Rows | Finding |
|---|---|---|
| gold/gold_forecasts_exante.csv | 56 | The quote was found on the cited page for **2** of 56. 23 distinct URLs, mostly home pages (rajeevprakash.com/blog ×10, mmacycles.com ×9, mahendraprophecy.com ×8). |
| earthquake/quake_forecasts_exante.csv | 54 | Quote found for **2**; 10 rows have no URL; 23 rows cite only the home page ssgeos.org. |
| flood/monsoon_forecasts_exante.csv | 27 | Quote found for **0**. 15 rows cite only the home pages of astrologicalmagazine.com or modernastrology.co.in; 5 astrologicalmusings.com monsoon URLs return 404. |
| gold_prices/news_2024_2026.csv | 15 | **0** URLs load: 8 Reuters (paywall, 401) and 7 CNBC, Bloomberg or Al Jazeera that return 404. The URL slugs look generated. |
| gold_prices/drivers.csv | 19 | 13 URLs failed. Most are FRED, which timed out from here and is likely fine; also the IMF, BLS, WGC and EPU pages. Series IDs look right; recheck them in the fetch scripts. |
| gold_prices/sources_gold.csv | 19 | 7 failed (Nasdaq LBMA/GOLD and CHRIS pages 404, Bundesbank search 404, WGC premium 404). The licence statements are plausible but must be read at the source. |
| earthquake/m7_events_vs_predictions.csv | 36 | The "YES (vague)" ex-ante predictions attributed to Raman (1950, 1976, 1997), Vasudev (2005, 2008) and Kapoor (2015, 2016, 2021) have no retrievable source. **Unverified.** |

### Citations with a wrong or unresolvable DOI

The DOIs below resolve to a different paper, or to nothing. Most of the papers themselves are probably real; only the DOI is wrong.

| Cited as | DOI given | Crossref says |
|---|---|---|
| Chen 2010, regime-switching GARCH, *Economic Modelling* | 10.1016/j.econmod.2010.01.008 | Shin & Kim 2010, subsidy policies |
| Reboredo 2013, gold and the US dollar, *JBF* | 10.1016/j.jbankfin.2013.02.003 | Groba et al. 2013, EU sovereign market |
| Baur & McDermott 2010, *JBF* | 10.1016/j.jbankfin.2010.01.019 | Jang & Yoon 2010, range notes |
| Plakandaras et al. 2015, *Resources Policy* | 10.1016/j.resourpol.2015.06.005 | Crompton 2015, steel consumption |
| Harvey, Liu & Zhu 2016 | 10.1111/jofi.12365 | McLean & Pontiff 2016 (the paper is in *RFS*, doi 10.1093/rfs/hhv059) |
| Hunter 1972, *Nature* | 10.1038/236447a0 | an X-ray astronomy paper |
| Wang, Liu & Wu 2020, *J. Commodity Markets* | 10.1016/j.jcomm.2020.100142 | not found |
| Zechar et al. 2010 (CSEP) | 10.1785/gssrl.81.4.543 | not found |
| Ambraseys & Jackson 2003 | 10.1023/A:1021204128527 | not found |
| Bailey & López de Prado 2014 | 10.3905/jpm.2014.40.5.125 | not found |
| IMD skill paper (*Mausam* 60(3)) | 10.54302/mausam.v60i3.1257 | not found |

The following resolved correctly: Cochran 2004; Ide 2016; Hough 2018; Tanaka 2012; Vidale 1998; Geller 1997; Molchan 1997; Ogata 1988; Zhuang 2002; Gardner–Knopoff 1974; Zaliapin & Ben-Zion 2013; Bilham 2019; Scordilis 2006; Ashok 2001; Kumar 1999; Rajeevan 2006; Pai 2014; Kohyama & Wallace 2016; Bradley 1962; Visvanathan 1966; Dichev & Janes 2003; Yuan et al. 2006; Lucey 2010; Baur 2013; Novy-Marx 2014; Baur & Lucey 2010; Schmidbauer & Rösch 2018; Romano & Wolf 2005; White 2000; Hansen 2005; Hansen et al. 2011 (MCS). Effect sizes quoted for these papers still need checking against the papers themselves.

### Precise numbers to distrust until checked
- IMD forecast "hit rate 63.2% (24/38 years)" and the RMSE figures.
- Every "ex-ante" monsoon hit attributed to G.D. Vasudev for 2002 and 2009.
- Classical verses quoted in Devanagari for Brihat Samhita ch. 41–42, Bhadrabahu ch. 12, Meghamala ch. 7, and Vyapar Ratna "p. 112 / p. 145". These must be matched against a physical or scanned edition. The archive.org and wisdomlib links given for several of them return 404.
- The Sapta Nadi nakshatra-to-nadi table: check it against a named edition of Narapati-jayacharya.
- The Maheshri "4 outer planets at 15° multiples" rule and the Kapoor Koorma-limb nakshatra assignments.

## What checks out or is useful now

- **Brihat Samhita ch. 32 mandala lists** (Vayu, Agni, Indra, Varuna) match `MANDALAS` in `libs/vedic_astrology_core/astrology/mundane.py`, including Uttara Bhadrapada in Varuna.
- **A substantive point for the earthquake paper.** Gemini notes that in BS ch. 32 the mandala is read from the Moon's nakshatra *at the time of an earthquake that has already happened*, to forecast its consequences. Our study uses the mandala as a forward trigger. If that reading holds, our operationalisation inverts the text, and that has to be stated in the paper and reviewed by an astrologer (ADR-004 validation level L4).
- **The Gorkha–Kodari geometry agrees with our review.** The Gardner–Knopoff window for Mw 7.8 is about 89 km. Kodari (Mw 7.3, 2015-05-12) is about 140 km from the Gorkha epicentre, so it is kept as a mainshock. This supports moving to ETAS (WP-26).
- **The dataset inventories** are the right lists to build fetch scripts for (WP-11): ISC-GEM (CC BY-SA), GCMT, IMD/IITM rainfall, IBTrACS, NOAA Niño 3.4/ONI/DMI, CFTC COT, FRED series, the GPR index, and RBI DBIE gold. The licence claims must be confirmed at the source.
- **The flood feasibility reasoning** is sound and agrees with ADR-004:
  - Megheshvara/Varsheshvara and Mars in Rohini are fully computable, so they are candidates for the first Registered Report rule.
  - Garbha, Rohini-yoga wind and Meghamala need observations, so they are not computable.
  - ENSO, IOD and trend are the required controls.
- **The practitioner disputes** (direct versus inverse dignity, Jupiter retrograde, tropical versus sidereal, which "gold chart") are real and belong in `rules/financial/practitioner/DISPUTES.md` once sourced.

## Rules on how to use these files

1. Nothing in `research/incoming/` feeds a study, a rule file or a paper directly. A row is promoted only when:
   - its source has been opened and the quote, number or verse found there, by a person or an agent with a fetch log;
   - the row records `verified_by`, `verified_at` and the exact page or archive snapshot (web.archive.org URL) used.
2. An ex-ante forecast counts only when its **publication date is proven independently of the author's own site**: an archive.org snapshot dated before the event, a print issue, or a dated social post. Book forecasts need the edition and page.
3. Rules from `rules_gold/` and `rules/` enter `rules/<domain>/` only through `astro-rules validate` and with `tier: experimental` until the verse is checked (ADR-004 level L1 → L2).

---

## Round 2: Gemini's verification pass, spot-checked 2026-11-22

Gemini wrote `verified/` folders under each topic (63 files). I checked them independently.

**Much better than round 1.** Of the 127 new URLs, 95 load. The other 32:
- 10 are FRED CSV endpoints that time out from this machine and are probably fine;
- 15 return 404 or 403: the Bundesbank and WGC terms pages, Nasdaq CHRIS (locked, as Gemini says), the IITM, IMD and DFO download links, the Myanmar news article, and the archive.org book scans;
- the rest are archive.org snapshot URLs with a placeholder timestamp ("20260301000000"), so they are not real captures.

### Corrected DOIs (checked on Crossref or doi.org)
- **Confirmed:**
  - Baur & McDermott 2010: 10.1016/j.jbankfin.2009.12.008
  - Plakandaras et al. 2020 "Gold Against the Machine": 10.1007/s10614-020-10019-z
  - Saji et al. 1999: 10.1038/43854
  - Kennedy, Vidale & Parker 2004, *SRL*: 10.1785/gssrl.75.5.607
  - Simpson 1967: 10.1016/0012-821x(67)90071-4
  - Zechar et al. 2010, *BSSA*: 10.1785/0120090192
  - Zechar et al. 2010, *CPE*: 10.1002/cpe.1519
  - Hughes 1977, *Nature*: 10.1038/265013a0
  - Schorlemmer et al. 2018: 10.1785/0220180053
- **Resolve on doi.org (not checked further):** Harvey, Liu & Zhu (10.1093/rfs/hhv059); Bailey & López de Prado (10.3905/jpm.2014.40.5.094); Reboredo (10.1016/j.jbankfin.2013.03.020); the DFO Zenodo record (10.5281/zenodo.19288170).
- **Still wrong:**
  - 10.1016/j.jcomm.2021.100142 returns 404. Drop the "Wang, Liu & Wu 2020" paper; Gemini itself calls it invented.
  - 10.1007/s12040-009-0020-y is **Pai & Nair 2009** ("Summer monsoon onset over Kerala: new definition and prediction"), not "Pai & Rajeevan". The paper is right; fix the authors.
- **Withdrawn by Gemini as invented:** Chen 2010 (regime-switching GARCH) and Wang, Liu & Wu 2020.

### Ex-ante forecasts: quotes re-found in the archive.org snapshots
| Claim | Snapshot | Quote on the page |
|---|---|---|
| Malhotra, gold up after Jupiter enters Virgo, Aug 2016 | 2016-03-29 | **yes** |
| Malhotra, monsoon 2023 "around 95% of the LPA" | 2023-05-31 | **yes** |
| Malhotra, monsoon 2022 "higher than the normal" | 2022-05-21 | **yes** |
| Malhotra, monsoon 2021 "90% to 95% of the LPA" | 2021-05-23 | **yes** |
| Malhotra, monsoon 2019 | 2019-04-23 | not found by 5-word match; needs a manual read |
| Malhotra, monsoon 2016 | 2016-03-29 | not found by 5-word match; needs a manual read |

The earthquake set has **0 of 36** Himalaya–Tibet–Myanmar M≥7 events with a proven ex-ante prediction.
- The Myanmar TikTok "false alarm" source URL and its archive both return 404, so it is unproven.
- Hoogerbeets (SSGEOS, 2023-02-03) is planetary-geometry forecasting, not Jyotish. His alarm was open-ended, with no end date or polygon, so it cannot be scored as a forecast.

### LBMA gold from 1968: still unsolved
Gemini's Bundesbank codes (BBDK01.WT5512 / WT5511, BBEX3.D.XAU.EUR.EA.AC.C04) and the obvious variants all return "no results" from the Bundesbank SDMX API (api.statistiken.bundesbank.de). Either the codes are wrong or the series is no longer published. **Do not rely on this route until a working download has been shown.** The fallbacks are World Bank Pink Sheet monthly gold (already snapshotted) and Stooq GC.F (from 1974-12-31; licence unread).

### What is now usable
- **Earthquake literature:** all 18 rows have resolving DOIs. Cochran, Ide, Hough and Kennedy now carry quoted effect sizes; spot-check the quotes before citing.
- **Brihat Samhita ch. 32: the mandala direction is settled.** The mandala is read from the Moon's nakshatra at the time of an earthquake that has already happened, to forecast its consequences over about six months (v. 23). Gemini gives verse citations; an astrologer should confirm the reading. The earthquake paper must say that the study tests a forward-trigger reading the text does not make. That reading is still a legitimate test of practitioners who use it that way, as Raman's list does.
- **Brihat Samhita gold rules:** 7 of 21 are tied to Bhat (1981) pages (ch. 8 v. 5; ch. 41 vv. 2, 7, 11, 12; ch. 42 vv. 6, 14). Check the pages against the scan before promoting them to rules/ at level L2. The other 14 are `verified: false`.
- **Flood:** the computable versus observation-only split of the 12 rules, and the recommendation to start the first Registered Report with Megheshvara plus Mars in Rohini. The verified ENSO/IOD figures are Kumar 1999 (r −0.60 → −0.32) and Ashok 2001 (R 0.59). The "63.2% IMD hit rate" is confirmed as invented.
- **Gold episodes:** two dates corrected (2015-12-17 low; 2024-10-30 PM-fix peak).
- **Gold news 2024–2026:** now cites Kitco articles that load. The 2025–2026 levels (e.g. "$4,690 in May 2026") must be checked against the price series before any use.


---

## Round 4 audit (2026-11-22): D2 earthquake and D3 monsoon/flood

Method: every hashed source was re-downloaded independently with curl (generic client name), SHA-256 compared; DOIs checked on Crossref; ETAS values compared against the published table; key dates spot-checked against IMD records known to the auditor. Gemini's fetch scripts were NOT executed.

### Downloads: 7 of 7 hashes reproduce

| Source | HTTP | SHA-256 matches Gemini | Lines |
|---|---|---|---|
| IITM all-India + macro-regions (1871–2016) | 200 | yes | 960 |
| IITM 30 subdivisions (1871–2016) | 200 | yes | 4,800 |
| IITM longest instrumental series (1813–2006) | 200 | yes | 196 |
| NOAA ONI | 200 | yes | 86 |
| DFO Global Flood Records (Zenodo 19288171, CC0) | 200 | yes | 5,503 |
| USGS ComCat box M≥5.5, 1976–2025 | 200 | yes | 183 |
| ISC Bulletin box M≥5.5, 1976–2025 | 200 | yes | 259 |
| IMD Forecast_Performance.html | timeout | not checked (server unreachable from here) | |

This is the first round with no fabricated source. The data score for earthquake and monsoon can move up once WP-11 fetch scripts land these sources in data/snapshots.

### ETAS parameters
- Ogata & Tsuruoka 2016, EPS 68, **article 44** (Gemini wrote 41): all four rows match Table 1(a) and 1(d) exactly. These are **aftershock-sequence fits with μ = 0**, not background-rate fits for a 50-year regional catalogue, so they cannot decluster the study catalogue by themselves.
- Bansal, Dimri & Babu, J. Seismol. 17(2):255–264: DOI resolves to the right paper (issued 2012 online, 2013 issue). Values not yet checked against the table (paywalled).
- Muralidharan & Das, arXiv 2505.24412: exists ("A Time-Scaled ETAS Model for Earthquake Forecasting"); values not checked.

### Claims rejected or needing work
1. **"ETAS correctly classifies Kodari as an aftershock (P > 0.98)"**: unsupported. No ETAS fit was run; the probe has no computation behind it. WP-26 must compute this.
2. **IMD forecasts (imd_forecasts.csv)**: the forecast column mixes the April first-stage forecast and the June update while the issue date is always April. Examples: 2022 shows 103 (the May update) with an April date (April said 99); 2009 shows 93 (June) not 96 (April); 2015 shows 88 (June) not 93 (April). 1988–2002 issue dates are all "05-25", a placeholder. Fix: one row per issued forecast with stage (April/May/June). Realised values spot-checked correct (2002 81, 2009 78, 2019 110, 2024 108, 2025 108); 2023 realised is 94 in IMD's end-of-season statement, not 95.
3. **"5-category hit rate 63.2%"**: this figure was flagged as invented in round 2; it is now computed from the file above, so it inherits the April/June mix-up. Recompute after the fix.
4. **IITM licence quote** ("Government of India Open Data directives"): not found on the cited page. Treat licence as unclear until H4.
5. Kerala onset 2014–2025: 12 of 12 dates correct. 1901–2013 from the IMD Forecasting Manual: not yet spot-checked.
6. ISC-GEM v13 requires a manual CAPTCHA download (owner task). The "isc_only" rows (56) arise because the ISC FDSN filter matches any agency's magnitude; the comparison must use a single magnitude type before conclusions.
7. Nepal DHM onset/withdrawal 1968–2025: source PDF not yet opened by the auditor.

### Status
Usable now (after WP-11 fetch): IITM series, ONI/Niño 3.4/DMI/SILSO, DFO floods, USGS and ISC catalogue extracts, Kerala onset 2014–2025. Needs fixing: IMD forecasts table. Needs owner action: ISC-GEM download, licence reading (H4).
