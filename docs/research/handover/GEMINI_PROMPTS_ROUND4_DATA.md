# Gemini (Antigravity) prompts, round 4: data quality to 8/10

Written 2026-11-22. Each prompt is self-contained: paste ONE block into a fresh Gemini session in this repo. Round 3 (GEMINI_PROMPTS_ROUND3.md: founding times, text citations, event datasets) still applies; D4 part C overlaps M2 and supersedes it if both are run.

## Why the data score stayed low after rounds 1–2
- Rounds 1–2 asked for lists of sources and claims. They produced metadata, not data: nothing was downloaded, and many URLs, quotes and DOIs were invented (see INCOMING_AUDIT_2026-11-22.md).
- The studies themselves still run on the original inputs (Yahoo futures for gold; USGS only for earthquakes; no monsoon data).
- Round 4 asks Gemini to download, hash and script each source, so every row comes with proof that it works.

## What raises which score
| Matrix | Now | Raised by |
|---|---|---|
| Data (D) | 5 | D1, D2, D3 here, then WP-11/12/25 fetch and gate them |
| Astrological fidelity (A) | 3 | D4 part C + round-3 M2, then owner check of the pages (H11) |
| Practitioner evidence | ~0 | D4 parts A–B, then WP-10 validation and scoring |
| Statistics (S), reproducibility (R), writing (W) | 5–7 | Code: ADR-004 WP-01..04, 10, 11, 16 (running now) |

---

## D1 — Gold and silver prices and controls
```text
RULES (read first)
You are collecting DATA SOURCES for an open, reproducible scientific project that tests Vedic (sidereal, Lahiri) astrology claims. Our earlier rounds failed for one reason: links, quotes and series IDs that looked right but did not work. So this round is about PROOF, not lists.
1. You have a terminal. For every data source, actually download it (curl/python) into /tmp, then report: the exact URL or API call, HTTP status, file size, SHA-256, row count, first date, last date, and the first 3 and last 3 rows pasted verbatim. A source you did not download is "UNTESTED" and goes in a separate list.
2. Licence: quote the exact licence/terms sentence and its URL. Answer "redistributable in a public GitHub repo: yes / no / unclear". Do NOT commit raw data that is not redistributable; deliver the fetch script instead.
3. Deliver a fetch script per source (Python, stdlib + pandas/requests only) that re-downloads the file and prints its SHA-256. Scripts must not need a paid key; if a free key is needed, say so and read it from an environment variable.
4. Never invent a series ID, DOI, URL or number. If something does not work, report the error message. A documented failure is valuable.
5. Save everything under research/incoming/<folder>/round4/ : probe_report.md, sources.csv, fetch_*.py, and small samples (<=100 rows) only when the licence allows.
6. End with "Gaps and doubts": what you could not get and why.

TASK D1 — Gold and silver: a long, clean, daily price series plus the economic controls.
Folder: research/incoming/gold_prices/round4/

Why: our study ran on Yahoo GC=F front-month futures (2000–2026), which is thin before 2008 and is not spot. FRED dropped the LBMA series GOLDPMGBD228NLBM (HTTP 404). Bundesbank SDMX keys BBEX3/D.XAU... and BBDK01/WT5512 returned 404 for us. We need a daily gold (and silver) price back to 1968 if at all possible, from a source we may legally use.

A. Gold daily, USD, as long as possible. Test each and report results: LBMA/IBA (prices.lbma.org.uk JSON endpoints used by their charts, and their licence), Nasdaq Data Link (LBMA/GOLD, LBMA/SILVER: does a free key still work?), Bundesbank time-series database (find the CURRENT correct series key for the London gold price, via their web search and SDMX REST API), Swiss National Bank data portal, Bank of England, ECB, World Bank Pink Sheet (monthly), datahub.io core/gold-prices, investing.com/stooq historical CSV (stooq: xauusd daily), Kitco, MacroTrends, the gold price in INR from RBI DBIE / IBJA, Shanghai Gold Exchange.
B. Silver daily: same list (LBMA silver fix, stooq xagusd).
C. COMEX futures with volume and open interest, continuous, roll-adjusted if any free source exists; CFTC Commitments of Traders for gold (weekly, cftc.gov, free).
D. Controls via FRED (test each ID with fredgraph.csv?id=...): DFII10, DTWEXBGS, DGS10, CPIAUCSL, FEDFUNDS, VIXCLS, SP500, DCOILBRENTEU; plus Geopolitical Risk Index (matteoiacoviello.com/gpr.htm), Economic Policy Uncertainty (policyuncertainty.com), gold ETF holdings (GLD daily holdings CSV from spdrgoldshares.com).
E. Indian festival dates 1990–2027 (Akshaya Tritiya, Dhanteras, Diwali) from an official or computable source (drikpanchang is not official; say so).

Deliver: sources.csv with columns
source_id, asset, provider, dataset, series_id, url_or_api_call, http_status, sha256, rows, first_date, last_date, frequency, units, sampling_time_tz, licence_quote, licence_url, redistributable, needs_key, fetch_script, notes
plus probe_report.md with pasted head/tail rows for each tested source, and a final recommendation: the ONE best gold series from 1968 and the ONE best silver series, with reasons.
```

## D2 — Earthquake catalogues and ETAS
```text
RULES (read first)
You are collecting DATA SOURCES for an open, reproducible scientific project that tests Vedic (sidereal, Lahiri) astrology claims. Our earlier rounds failed for one reason: links, quotes and series IDs that looked right but did not work. So this round is about PROOF, not lists.
1. You have a terminal. For every data source, actually download it (curl/python) into /tmp, then report: the exact URL or API call, HTTP status, file size, SHA-256, row count, first date, last date, and the first 3 and last 3 rows pasted verbatim. A source you did not download is "UNTESTED" and goes in a separate list.
2. Licence: quote the exact licence/terms sentence and its URL. Answer "redistributable in a public GitHub repo: yes / no / unclear". Do NOT commit raw data that is not redistributable; deliver the fetch script instead.
3. Deliver a fetch script per source (Python, stdlib + pandas/requests only) that re-downloads the file and prints its SHA-256. Scripts must not need a paid key; if a free key is needed, say so and read it from an environment variable.
4. Never invent a series ID, DOI, URL or number. If something does not work, report the error message. A documented failure is valuable.
5. Save everything under research/incoming/<folder>/round4/ : probe_report.md, sources.csv, fetch_*.py, and small samples (<=100 rows) only when the licence allows.
6. End with "Gaps and doubts": what you could not get and why.

TASK D2 — Earthquakes: a second catalogue, uniform magnitudes, and ETAS inputs for the Himalaya.
Folder: research/incoming/earthquake/round4/

Why: our study uses only the USGS ComCat (1976–2026, 297 events of Mw >= 5.2 in a Himalayan polygon). Most magnitudes are mb converted to Mw. Gardner-Knopoff declustering left the 2015-05-12 Mw 7.3 Kodari event as a mainshock. Reviewers will ask for ISC-GEM and ETAS.

Polygon (lon, lat), closed: use 72E–98E, 25N–37N as the bounding box and report what you get inside it.

A. ISC-GEM Global Instrumental Earthquake Catalogue: the current version number, the exact download URL (isc.ac.uk/iscgem/download.php or the CSV file link), licence, and a filtered extract for the box above (1900–present): row count, magnitude type (Mw proxy), first/last event. Compare it against USGS ComCat for the same box and Mw >= 5.5 since 1976: list events present in one but not the other.
B. ISC Bulletin / ISC-EHB for the same box (API URL, licence).
C. USGS ComCat FDSN query for the same box (give the exact URL) for cross-check.
D. Nepal National Seismological Centre (seismonepal.gov.np) catalogue and India NCS (seismo.gov.in) catalogue: is there a downloadable list? Licence? Test.
E. ETAS for the Himalaya: find published ETAS parameter estimates (mu, K, alpha, c, p, d, q, gamma) for the Himalaya or Nepal/Tibet region, with the paper DOI (open the DOI and confirm it resolves to that paper), the table number and the values. Also find the best open-source ETAS fitting code (e.g. "etas" R package, SEISMOLOGY python packages, the "bayesianETAS" or "ETAS.inlabru" packages): repository URL, licence, last release.
F. Published lists of Himalayan aftershock sequences of the 2015 Gorkha earthquake (to check declustering), with DOIs.

Deliver: sources.csv (same columns as other round-4 tasks: source_id, dataset, provider, url_or_api_call, http_status, sha256, rows, first_date, last_date, magnitude_types, licence_quote, licence_url, redistributable, needs_key, fetch_script, notes), catalogue_diff.csv (event_id_usgs, event_id_isc, time, lat, lon, mag_usgs, mag_isc, present_in), etas_parameters.csv (paper, doi, doi_resolves_yes_no, region, table, mu, K, alpha, c, p, d, q, gamma, magnitude_threshold, notes), probe_report.md.
```

## D3 — Monsoon, rainfall, floods, climate controls
```text
RULES (read first)
You are collecting DATA SOURCES for an open, reproducible scientific project that tests Vedic (sidereal, Lahiri) astrology claims. Our earlier rounds failed for one reason: links, quotes and series IDs that looked right but did not work. So this round is about PROOF, not lists.
1. You have a terminal. For every data source, actually download it (curl/python) into /tmp, then report: the exact URL or API call, HTTP status, file size, SHA-256, row count, first date, last date, and the first 3 and last 3 rows pasted verbatim. A source you did not download is "UNTESTED" and goes in a separate list.
2. Licence: quote the exact licence/terms sentence and its URL. Answer "redistributable in a public GitHub repo: yes / no / unclear". Do NOT commit raw data that is not redistributable; deliver the fetch script instead.
3. Deliver a fetch script per source (Python, stdlib + pandas/requests only) that re-downloads the file and prints its SHA-256. Scripts must not need a paid key; if a free key is needed, say so and read it from an environment variable.
4. Never invent a series ID, DOI, URL or number. If something does not work, report the error message. A documented failure is valuable.
5. Save everything under research/incoming/<folder>/round4/ : probe_report.md, sources.csv, fetch_*.py, and small samples (<=100 rows) only when the licence allows.
6. End with "Gaps and doubts": what you could not get and why.

TASK D3 — Monsoon, rainfall, floods and climate controls for India and Nepal, 1871 to today.
Folder: research/incoming/flood/round4/

Why: our next study (a Registered Report) tests classical rain rules against Indian summer monsoon rainfall. It needs a long homogeneous rainfall series and the climate drivers as controls. Nothing has been downloaded yet.

A. All-India summer monsoon rainfall (June–September), annual and monthly, 1871 to the latest year: IITM homogeneous Indian monthly rainfall data set (tropmet.res.in; find the current file link), plus the 30 meteorological subdivisions series. Also IMD gridded 0.25 deg rainfall (imdpune.gov.in; the Python package imdlib can download it: test it). Report the exact file, rows, first/last year.
B. IMD's official seasonal forecasts and "long period average" (LPA) percentages per year (1988 onward): the press-release URL per year, the forecast issued in April/May/June, and the realised % of LPA. This is the official baseline any astrologer must beat.
C. Climate controls, monthly, as long as possible: ENSO (NOAA ONI, Nino3.4 from HadISST/ERSSTv5), Indian Ocean Dipole (DMI from NOAA PSL or JAMSTEC), plus sunspot number (SILSO). Test each URL.
D. Nepal: DHM Nepal monsoon onset/withdrawal and rainfall data; any open long series.
E. Floods: Dartmouth Flood Observatory archive (download link, licence), Global Flood Database, EM-DAT (licence terms: can a derived count table be published?), DesInventar India/Nepal, India CWC flood reports.
F. Monsoon onset dates over Kerala, per year since 1901 (IMD), with source.

Deliver: sources.csv (source_id, dataset, provider, url_or_api_call, http_status, sha256, rows, first_year, last_year, frequency, units, licence_quote, licence_url, redistributable, needs_key, fetch_script, notes), imd_forecasts.csv (year, forecast_issue_date, forecast_pct_lpa, forecast_error_band, realised_pct_lpa, press_release_url, archive_url), kerala_onset.csv (year, onset_date, source_url), probe_report.md.
```

## D4 — Ex-ante forecasts and classical text pages
```text
RULES (read first)
You are collecting DATA SOURCES for an open, reproducible scientific project that tests Vedic (sidereal, Lahiri) astrology claims. Our earlier rounds failed for one reason: links, quotes and series IDs that looked right but did not work. So this round is about PROOF, not lists.
1. You have a terminal. For every data source, actually download it (curl/python) into /tmp, then report: the exact URL or API call, HTTP status, file size, SHA-256, row count, first date, last date, and the first 3 and last 3 rows pasted verbatim. A source you did not download is "UNTESTED" and goes in a separate list.
2. Licence: quote the exact licence/terms sentence and its URL. Answer "redistributable in a public GitHub repo: yes / no / unclear". Do NOT commit raw data that is not redistributable; deliver the fetch script instead.
3. Deliver a fetch script per source (Python, stdlib + pandas/requests only) that re-downloads the file and prints its SHA-256. Scripts must not need a paid key; if a free key is needed, say so and read it from an environment variable.
4. Never invent a series ID, DOI, URL or number. If something does not work, report the error message. A documented failure is valuable.
5. Save everything under research/incoming/<folder>/round4/ : probe_report.md, sources.csv, fetch_*.py, and small samples (<=100 rows) only when the licence allows.
6. End with "Gaps and doubts": what you could not get and why.

TASK D4 — Ex-ante astrologer forecasts with PROVEN dates (Wayback), and classical-text page scans.
Folder: research/incoming/forecasts/round4/

Why: we have only 4 astrologer forecasts whose publication date is proven before the event. We need at least 30 per topic to score anything. Forecasts must be checkable: specific event, place, time window, published before it.

A. Forecast harvest. Use the Wayback Machine CDX API (http://web.archive.org/cdx/search/cdx?url=<site>/*&output=json&from=YYYY&to=YYYY) on these kinds of pages, and open the archived snapshot itself, not the live page:
   - annual "yearly predictions" / "Nav Varsh" / "Samvat" / "Mesha Sankranti" forecast articles by Indian and Nepali astrologers and newspapers (e.g. Times of India astrology, Hindustan Times, Nepali papers Kantipur/Gorkhapatra, Express Star Teller, astrology magazines, well-known astrologer blogs), 2005–2026;
   - monsoon forecasts (rain %, drought, floods) published before 1 June each year;
   - gold price forecasts with a direction and a date window;
   - earthquake forecasts naming a region and a window.
   For each forecast: open the earliest snapshot that contains the text, and record the snapshot URL with its 14-digit timestamp and the verbatim sentence.
B. Do NOT include "I predicted it" posts written after the event, except in a separate file post_hoc.csv.
C. Classical text scans: for Brihat Samhita (tr. M. Ramakrishna Bhat, 1981) chapters 8, 21–28 (rain), 32 (earthquake), 41–42 (prices), and BPHS (tr. R. Santhanam) chapters on vargas and Vimshottari dasha: find archive.org items (give the item identifier) and the exact page links (archive.org/details/<id>/page/<n>) where each verse sits. Paste the verse text as printed (English and Sanskrit if shown).

Deliver: forecasts.csv with columns
forecast_id, topic (monsoon|gold|earthquake|politics|other), astrologer_or_outlet, original_url, snapshot_url, snapshot_timestamp, language, verbatim_quote, english_translation, predicted_event, region, window_start, window_end, magnitude_or_size, direction, astrological_basis_stated, specificity (high|medium|low), notes
post_hoc.csv (same columns), text_pages.csv (text, translator, archive_item_id, chapter, verse, page_number, page_url, printed_text), probe_report.md with counts per topic and per year.
Target: at least 30 dated forecasts each for monsoon and gold, and as many earthquake ones as truly exist.
```
