# SESOI proposal: candidate yardsticks per domain and outcome

- Date: 2026-11-23. Author: architect (design only). Status: **proposal; nothing here is in force.**
- Rule it serves: [ADR-008](../adr/ADR-008-statistical-hardening.md) section 7.2 and amendment A3.4. A smallest effect size of interest (SESOI) comes from the rule's own source or from a published yardstick, never from this project's results.
- What happens next: the owner reads each number at the page (H18), fills `page`, `number_as_printed`, `conversion`, `converted_value`, `checker`, `date` in `studies/validity/sesoi_sources.yaml`, and records the choice in `OWNER_DECISIONS.md` before the batch closes. Until then every plan keeps `sesoi: null`.
- Scope: past data only.

## How to read this file

- **No number below was taken from this repository's results.** None of them was checked at the page by the author either.
- "Value" is either a definitional number (a published category boundary) or "read at page". Where a rough size is given from memory it is marked **memory, not a value** and must not be typed into a plan.
- Citation confidence: **[index]** = title, journal, volume and pages matched a publisher or index listing in a search on 2026-11-23. **[memory]** = the paper is believed to exist as cited; volume and pages are from memory and must be confirmed. No page inside a paper is given anywhere, on purpose: that is the H18 check.
- Every row has status **to verify by owner (H18)**.

## 1. Monsoon (yearly, percent of the long-period average, LPA)

| Id | Outcome | Candidate value | Outside basis | Citation | Status |
|---|---|---|---|---|---|
| M-1 | `all_india_jjas_anomaly_pct` (shift, points of LPA) | Read at page: the mean June to September anomaly of El Nino years | The best-established non-astrological effect on the same outcome; the kind ADR-008 7.2 names for monsoon | Rasmusson and Carpenter (1983), "The relationship between eastern equatorial Pacific sea surface temperatures and rainfall over India and Sri Lanka", Monthly Weather Review 111, 517-528 [memory]. Kumar, Rajagopalan and Cane (1999), "On the weakening relationship between the Indian monsoon and ENSO", Science 284, 2156-2159 [memory]. Kumar, Rajagopalan, Hoerling, Bates and Cane (2006), "Unraveling the mystery of Indian monsoon failure during El Nino", Science 314, 115-119 [index] | to verify by owner (H18). A printed composite mean must be found; if a paper gives only a figure or a correlation, it does not qualify |
| M-2 | same | 10 points (the boundary of the "deficient" class: seasonal rain below 90% of LPA) | Official category band of the India Meteorological Department; about one year-to-year standard deviation of the series | IMD long-range forecast statements and the IMD monsoon FAQ (imdpune.gov.in/faq_monsoon.php) for the band; Parthasarathy, Munot and Kothawale (1994), "All-India monthly and seasonal rainfall series: 1871-1993", Theoretical and Applied Climatology 49, 217-224, doi:10.1007/BF00867461 [index] for mean and standard deviation | to verify by owner (H18). The 90% line is consistent across sources seen; the other band edges differ between sources. Usable **only** under A3.4 item 4: the rule's source must itself say "deficient" or "drought" |
| M-3 | `peninsular_india_jjas_anomaly_pct` | Read at page: El Nino composite for the peninsular or south-peninsula series; none found yet | As M-1 for the region | IITM homogeneous-region series documentation (Parthasarathy and co-authors; IITM research report on monthly and seasonal rainfall series for homogeneous regions) [memory, report number to confirm] | to verify by owner (H18). **No value proposed.** A regional yardstick may not exist in print; then `sesoi: null` |
| M-4 | `all_india_drought`, `peninsular_india_drought` (risk ratio of a season below -10%) | Read at page: share of El Nino years that were drought years divided by the share among other years | Same yardstick as M-1 on the yes/no scale | Kumar et al. (2006) as above [index] (its opening figure sets rainfall anomalies against Pacific temperature for 1871 onward, to confirm); the -10% drought line is IMD's own all-India drought criterion (to confirm at the IMD page) | to verify by owner (H18). The ratio must be computable from printed counts only. The plan's drought `base_rate` must come from the same printed table |

Recommended order (A3.4 item 2): **M-1** for the anomaly. M-2 is a class boundary, not an effect size, and is larger than any El Nino mean is likely to be, so it would make exclusion easier; it is offered only for rules whose source uses the class word. Because the monsoon vintage is `seen`, the owner may reject a candidate but not pick the more convenient of two qualifying ones.

Related, not a SESOI: the year-test envelope of A3.1 rests on Mooley and Parthasarathy (1984), "Fluctuations in All-India summer monsoon rainfall during 1871-1978", Climatic Change 6, 287-301, doi:10.1007/BF00142477 [index]. Its statement on year-to-year persistence is from memory and is to be read at the page (H21).

## 2. Gold (daily, Frankfurt fixing in DEM, 1968 to 1998)

| Id | Outcome | Candidate value | Outside basis | Citation | Status |
|---|---|---|---|---|---|
| G-1 | `gold_dem_frankfurt_log_return` (shift of the daily log return) | Read at page: the mean return difference of the anomalous weekday against the other days. Memory, not a value: a few to about fifteen basis points a day | Published day-of-the-week effect in gold; the kind ADR-008 7.2 names for daily returns | (a) Ball, Torous and Tschoegl (1982), "Gold and the 'weekend effect'", Journal of Futures Markets 2(2), 175-182 [memory for volume and pages; title in index]: London fixings 1975 to 1979, the closest market type. (b) Ma (1986), "A further investigation of the day-of-the-week effect in the gold market", Journal of Futures Markets 6(3), 409-419 [memory]. (c) Lucey and Tully (2006), "Seasonality, risk and return in daily COMEX gold and silver data 1982-2002", Applied Financial Economics 16, 319-333 [index; issue number to confirm]. (d) Blose and Gondhalekar (2013), "Weekend gold returns in bull and bear markets", Accounting and Finance 53(3), 609-622 [index]: 1975 to 2011 | to verify by owner (H18). **Read (a) first: secondary sources disagree on whether it found a Monday effect, a Tuesday effect or none.** If (a) prints no significant weekday difference it does not qualify and the order moves to (b), (c), (d) |
| G-2 | `gold_dem_frankfurt_abs_return` (ratio of standardised absolute returns) | Read at page: ratio of the standard deviation of returns on the anomalous weekday to the other days | Published weekday seasonality in gold variance (reported as stronger than the seasonality in the mean) | Lucey and Tully (2006) as above [index]. Alternatives for scheduled-news days: Christie-David, Chaudhry and Koch (2000), "Do macroeconomics news releases affect gold and silver prices?", Journal of Economics and Business 52, 405-421 [memory]; Cai, Cheung and Wong (2001), "What moves the gold market?", Journal of Futures Markets 21(3), 257-278 [memory] (intraday, so less comparable) | to verify by owner (H18). Conversion: a ratio of standard deviations equals the ratio of mean absolute returns only if the shape of the distribution is the same on both kinds of day; the entry must say so |
| G-3 | `gold_dem_frankfurt_extreme_move` (risk ratio of a move beyond the past 95th percentile) | None | No published yardstick on this scale is known to the author. Deriving one from G-2 needs a distribution assumption, which would be the project's choice | - | **No SESOI proposed.** The outcome keeps `sesoi: null`: X95 and X-strict only |

Caveats for the owner.

- Every gold yardstick is on dollar prices in London or New York. The tested series is the Frankfurt fixing in DEM. No conversion exists; the entry must state the mismatch, and the card sentence must keep "Frankfurt fixing in DEM" (A-06).
- Samples (a) and (b) overlap the tested period; (c) and (d) partly.
- **Not proposed: a transaction-cost yardstick.** No citable published spread for the Frankfurt fixing in 1968 to 1998 is in hand, and ADR-008 7.2 allows a source size or an effect yardstick, not a cost. Using a cost would need its own amendment.
- **Not a yardstick:** Lucey (2010), "Lunar seasonality in precious metal returns?", Applied Economics Letters 17(9), 835-838 [index]. It is a lunar-phase effect, so it is not "non-astrological". It matters instead as a `known_channel` reference for tithi and lunar rules.
- Also seen, not used: Baur (2013), "The autumn effect of gold", Research in International Business and Finance 27, 1-11 [memory]: a monthly effect, relevant only if monthly gold is ever registered.

## 3. Earthquake (hourly grid, Himalayan arc, mainshock rate ratio)

| Id | Outcome | Candidate value | Outside basis | Citation | Status |
|---|---|---|---|---|---|
| E-1 | `mainshock_rate` (rate ratio) | Read at page: winter-to-summer seismicity rate ratio, at the magnitude cut-off nearest to the plan's completeness magnitude. Memory and secondary sources, not a value: between about 1.4 and 2 | Published seasonal modulation of seismicity on the same arc; the kind ADR-008 7.2 names for earthquake rate | Bollinger, Perrier, Avouac, Sapkota, Gautam and Tiwari (2007), "Seasonal modulation of seismicity in the Himalaya of Nepal", Geophysical Research Letters 34, L08304, doi:10.1029/2006GL029192 [index]. Supporting: Bettinelli and co-authors (2008), "Seasonal variations of seismicity and geodetic strain in the Himalaya induced by surface hydrology", Earth and Planetary Science Letters 266, 332-344 [memory] | to verify by owner (H18). The paper counts small events from the Nepal network; the plan counts declustered mainshocks from a global catalogue. The entry must state that mismatch |
| E-2 | same | Read at page. Memory, not a value: about 1.01 to 1.1 | Published tidal triggering of earthquakes: the best-established effect of a sky-linked cycle on seismicity | Cochran, Vidale and Tanaka (2004), "Earth tides can trigger shallow thrust fault earthquakes", Science 306, 1164-1166 [index]. Tanaka, Ohtake and Sato (2002), "Evidence for tidal triggering of earthquakes as revealed from statistical analysis of global data", Journal of Geophysical Research 107(B10), 2211 [memory]. Metivier and co-authors (2009), "Evidence of earthquake triggering by the solid earth tides", Earth and Planetary Science Letters 278, 370-375 [memory]. Vidale, Agnew, Johnston and Oppenheimer (1998), "Absence of earthquake correlation with Earth tides: an indication of high preslip", Journal of Geophysical Research 103, 24567-24572 [memory]. Ide, Yabe and Tanaka (2016), "Earthquake potential revealed by tidal influence on earthquake size-frequency statistics", Nature Geoscience 9, 834-837 [index for existence] | to verify by owner (H18). **Not recommended as the SESOI:** not the same arc, and at the catalogue's base rate (about 0.004 mainshocks an hour) a ratio this small can never be limited, so every test would be `unbounded`. Its use is as the `known_channel` reference for lunar rules |
| E-3 | same | None | Practitioner claims of "strong" triggering | - | **Not usable.** A word is not a size. It qualifies under 7.2 rule 1 only if a rule's own source prints a number (for example "twice as many"), quoted with its page, and then for that rule only |

Recommended: **E-1** (same arc, first in the A3.4 order). The domain is `limit_only` until ETAS declustering lands (D-03), so the SESOI is the only route to a verdict there.

## 4. What the owner decides, in one list

1. Monsoon anomaly: accept M-1 if a printed El Nino composite mean is found; otherwise `sesoi: null`. M-2 only for rules whose source says "deficient".
2. Monsoon drought flag: accept M-4 if printed counts allow the ratio; expect `unbounded` for most tests anyway (A3.2 item 5).
3. Peninsular outcomes: `sesoi: null` unless a regional composite is found.
4. Gold return: read Ball, Torous and Tschoegl first; apply the A3.4 order.
5. Gold absolute return: Lucey and Tully variance table, with the stated conversion caveat.
6. Gold extreme move: no SESOI.
7. Earthquake: E-1 at the cut-off nearest the plan's completeness magnitude.
8. For every accepted row: add the plan's `grid_x` values on both sides of the converted value before the batch closes.

## 5. What this proposal cannot do

- It cannot make a yardstick fit the tested series exactly (currency, market, catalogue). Each mismatch goes on the card.
- It cannot rescue tests whose information is too small: a SESOI makes exclusion possible, not likely.
- If the owner rejects every candidate for an outcome, that outcome reports X95 and X-strict only. That is a complete and honest result.
