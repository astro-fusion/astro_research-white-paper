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
