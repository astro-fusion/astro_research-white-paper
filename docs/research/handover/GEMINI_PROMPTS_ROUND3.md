# Gemini (Antigravity) prompts, round 3: mundane chart engine inputs

Written 2026-11-22 for ADR-006 (retrospective mundane chart engine). Each prompt is self-contained: copy ONE whole block into a fresh Gemini session. Outputs go to `research/incoming/mundane/round3/<prompt>/`. Nothing is used until a maintainer opens the cited source (ADR-004 promotion rules, research/incoming/README.md).

---

## Prompt M1 — Founding moments of countries (owner task H10)

```text
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

TASK: Founding-moment evidence for national charts (mundane astrology).

The project computes a "national chart" for a country from the exact moment it was founded, then reads its divisional charts (D1 to D9) and Vimshottari dasha at past events. The ascendant changes every ~4 minutes, D9 ascendant every ~13 minutes, so the TIME and its EVIDENCE matter more than anything else. Your job is to find primary evidence for the moment, not astrologers' opinions about it (record those separately).

Countries, in priority order: India, Nepal, Pakistan, Bangladesh, Sri Lanka, Bhutan, Myanmar, China (PRC), Afghanistan, then USA, UK, Japan, Turkey, Iran, Indonesia.

For each country list EVERY candidate founding moment that astrologers use or that history supports (independence, republic declaration, constitution in force, unification, revolution). Examples: India 1947-08-15 00:00 IST New Delhi (transfer of power at midnight) and 1950-01-26 (Republic; the time 10:18 IST is often quoted, find its basis); Nepal 2008-05-28 (Constituent Assembly declares republic: find the HOUR of the vote/declaration) and 2015-09-20 (constitution promulgated: find the hour), and older Nepal charts (1768 Kathmandu conquest by Prithvi Narayan Shah, date-only?).

Primary evidence means: the official gazette, the parliamentary or assembly record (proceedings with times), a contemporaneous newspaper report giving the clock time (with page), a government press release, or archive footage with a stated time. Secondary: history books with page. Astrology books are NOT evidence for the time; list them in the second file.

Deliver two CSV files:

1. founding_moments.csv with columns:
   country, candidate_id (e.g. IN-1947), event_description, date_local, time_local (HH:MM or "UNKNOWN"), timezone_or_offset_at_the_time (e.g. "IST +05:30", or "LMT Kathmandu +05:41:16"), place, latitude, longitude, time_precision (minute | quarter_hour | hour | day_only), evidence_type (gazette | assembly_record | newspaper | press_release | footage | history_book | other), evidence_citation (title, issue, page), evidence_url, archive_url (web.archive.org snapshot or "NONE"), verbatim_quote_giving_time, notes, confidence (high|medium|low)

2. astrologer_national_charts.csv with columns:
   country, chart_name, date, time, place, used_by (astrologer/book), source_citation, url, published_date, rectified (yes|no|unknown), rectification_method, notes

Hard requirements: never guess a time. If no primary source gives a clock time, put "UNKNOWN" and say what you searched. Quote the exact sentence that gives the time. Note any timezone trap (Nepal used +05:30 until 1986, then +05:45; India's IST history; LMT before standard time).
End with "Gaps and doubts".
```

---

## Prompt M2 — Classical text citations for the methods (owner task H11)

```text
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

TASK: Exact citations (edition, chapter, verse, page) for the classical methods the engine computes.

We need, for each method below, the defining passage in a named edition: Sanskrit (IAST or Devanagari) if available, the English translation as printed, the translator, publisher, year, chapter, verse numbers and page number. If a scan is online (archive.org, wisdomlib, Google Books preview), give the URL to the exact page (archive.org "page/N" link). Do NOT paraphrase from memory; if you cannot see the page, write NOT FOUND.

Methods:
1. BPHS (Brihat Parashara Hora Shastra, tr. R. Santhanam, Ranjan Publications; and/or tr. G.C. Sharma, Sagar Publications): the chapter that lists the 16 divisional charts (shodashavarga) and defines how to compute D1 Rashi, D2 Hora, D3 Drekkana, D4 Chaturthamsa, D7 Saptamsa, D9 Navamsa (plus D10, D12 for reference). Quote each definition.
2. BPHS: the chapter defining Vimshottari dasha (120-year cycle, lord order, years per lord, starting from the Moon's nakshatra, balance at birth) and the antardasha/pratyantardasha calculation.
3. BPHS: the "uses" of each varga (which matter each divisional chart signifies).
4. D5 (Panchamsa), D6 (Shashtamsa), D8 (Ashtamsa): are they defined in any classical text (Tajika Neelakanthi, Jaimini Sutras, Phaladeepika, Sarvartha Chintamani)? Give the text and verse or say NOT FOUND. Note they are not in BPHS's sixteen.
5. Brihat Samhita (tr. M. Ramakrishna Bhat, Motilal Banarsidass 1981): chapter 32 (earthquakes, the four mandalas and their nakshatras) with page numbers; and any chapter on national/royal omens tied to planets.
6. B.V. Raman, "Mundane Astrology" (exact title, publisher, year, edition): the chapters on national horoscopes, ingress (Mesha sankranti) charts, and eclipses in mundane astrology, with page numbers; the India 1947 chart as Raman gives it.
7. Any other recognised mundane-astrology classic that defines (a) annual ingress charts for countries, (b) eclipse effects on countries, (c) Jupiter–Saturn conjunction cycles: e.g. Varahamihira, Bhadrabahu Samhita, Manasagari, Narapati Jayacharya; M.C. Jain / others. Give exact citation and page.

Deliver citations.csv with columns:
method_id (e.g. varga.d9, dasha.vimshottari, varga.uses, varga.d5, bs.ch32.mandala, raman.national_chart, ingress.mesha, eclipse.mundane, jup_sat.cycle), text, translator, publisher, year, edition, chapter, verses, page, sanskrit_or_original, english_as_printed, scan_url_to_page, archive_url, how_verified (saw_scan | saw_preview | secondary_citation | NOT FOUND), notes
End with "Gaps and doubts", including disagreements between editions (chapter numbering differs between Santhanam and Sharma).
```

---

## Prompt M3 — Past-event datasets for countries (owner task H14)

```text
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

TASK: Exhaustive, licensed datasets of past mundane events per country, to analyse against national charts.

For each event type find the best exhaustive public dataset (not a list of famous cases): provider, dataset name and version, URL, download method, coverage (years, countries), unit of record, date precision (day/hour), fields for severity, licence (can it be redistributed in a public GitHub repo? yes/no/unclear, quote the licence line), citation to use, and known biases (reporting completeness by decade).

Event types:
1. Earthquakes: USGS ComCat, ISC-GEM (version), ISC Bulletin, NSC Nepal, IMD/NCS India.
2. Floods and other disasters: EM-DAT (licence!), Dartmouth Flood Observatory, DesInventar (India, Nepal), Global Flood Database, NDMA India.
3. Wars and armed conflict: UCDP (GED and armed conflict dataset), Correlates of War, ACLED (licence!).
4. Coups and regime changes: Powell & Thyne coup dataset, Cline Center Coup d'État Project, Polity/V-Dem regime transitions, Archigos (leaders).
5. Political events for India and Nepal specifically: dates of government changes, emergencies (India 1975-06-25), assassinations, elections, with a source per date.
6. Economic crises: Reinhart–Rogoff crisis dates, Laeven–Valencia banking crises database.
7. Epidemics and famines: WHO outbreak news, EM-DAT epidemics, famine datasets.

Deliver datasets.csv with columns:
event_type, provider, dataset, version, url, download_method, years, countries, record_unit, date_precision, severity_fields, licence, redistributable, licence_quote, citation, biases, notes
And india_nepal_political_events.csv: country, date, time_if_known, event, category, source_citation, url, archive_url.
End with "Gaps and doubts".
```
