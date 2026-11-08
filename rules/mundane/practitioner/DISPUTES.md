# Disagreements between mundane practitioners

Recorded as found, without a verdict. Each line names who holds which
position and where; the rule files carry the details. A dispute is closed
only by data: both sides are encoded as rules and tested on the same events.

## Is earthquake prediction part of Jyotish at all?

- **Yes, dated and testable.** Jagdish Maheshri builds a regression on USGS M7+
  events and planetary angles
  (https://saptarishisshop.com/earthquake-prediction-model-by-jagdish-maheshri/;
  `maheshri_geocentric_angles_m7.yaml`). Prashant Kapoor publishes dated
  earthquake calls (https://astrokapoor.com/accurate-earthquake-prediction-astrologer-prashant-kapoor/).
  VedAstro implements B.V. Raman's configurations as a scanner
  (https://vedastro.org/EarthquakePredictor.html).
- **No, omens only.** Dr. R.P. Sharma calls dated tremor alerts a "chronic
  failure mode"; Brihat Samhita 32 catalogues omens and types, and risk belongs
  to seismology (https://drrpsharma.com/blog/earthquakes-in-vedic-astrology.html,
  https://drrpsharma.com/blog/news-mundane-astrology.html).

## Where does the Koorma Chakra start?

- The AstroRidhis table (https://astroridhis.com/astrology/kurma-chakra/)
  starts with Ashwini, Bharani, Krittika in the **north** (head, Himalaya) and
  Rohini, Mrigashira, Ardra in the north-east.
- Brihat Samhita 14.2 in N. Chidambaram Iyer's 1884 translation
  (https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc228914.html,
  opened 2026-11-08) puts Krittika, Rohini, Mrigashira in the **centre**
  (Madhyadesha) and Ardra, Punarvasu, Pushya in the east.
- The two tables send the same transit to different regions.
  `kurma_north_sector_malefics.yaml` encodes the practitioner table; the
  Brihat Samhita table is the obvious companion rule.
- The engine encodes both: the predicate `kurma_direction` takes
  `start: krittika` (Brihat Samhita 14.1, the default: centre, east,
  south-east, south, south-west, west, north-west, north, north-east) or
  `start: ashwini` (the practitioner table, read clockwise from the north;
  the page does not say where its last triple goes, so it is put in the
  centre). Test both on the same events.

## Koorma Chakra or zodiac-sign rulership of countries?

- astrologicalmusings.com prefers the Koorma Chakra and calls Ptolemy's
  sign rulerships of countries inconsistent
  (https://astrologicalmusings.com/solar-eclipse-earthquake-and-koorma-chakra/).
- Western geodetic practice (Sepharial's geodetic equivalents, astrocartography)
  maps longitude to the zodiac instead. None of these is in the engine yet.

## Which national chart, and which zodiac?

- India: midnight 15 August 1947 (most practitioners) against 00:01 (K.N. Rao),
  noon, and Republic Day 1950. See `studies/mundane/data/countries.yaml`.
- Ayanamsa: Lahiri (most Indian practitioners; Steve Hora "True Lahiri"),
  Pushya Paksha (PVR Narasimha Rao, Tempora Research), modified Lahiri
  (theartofvedicastrology.com), tropical (Todd Elliott, Thea Anderson).
- Houses: whole sign (most Vedic), Bhava Chalit, Regiomontanus (Todd Elliott).
- Dasha: Vimshottari (most) against Panchottari (Vishal Aksh, who puts India's
  Moon mahadasha at 2020-2037 against 2015-2025 in Vimshottari), Chara (Abhigya
  Anand), Yogini.

The engine uses sidereal Lahiri, whole-sign houses, mean nodes and
Vimshottari. Rules from practitioners who use something else are marked
`needs_predicates` rather than silently translated.

## Brihat Samhita 32: the earthquake mandalas

The transcription used for `bs32_agni_mandala_earthquake.yaml` lists
Uttara Ashadha under both the Indra and the Varuna mandala. One of the two is a
copying error; the verse must be checked before those two mandalas are encoded.

Checked 2026-11-08 against N. Chidambaram Iyer's translation (1884) on
wisdomlib.org (https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc229177.html):
the doubling is in the translation itself. Verse 16 (Indra) and verse 20
(Varuna) both name Uttarashadha, and Uttara Bhadrapada appears in no list.
Each of the 27 asterisms belongs to exactly one circle, so the predicate
`moon_mandala` reads the Varuna entry as Uttara Bhadrapada, the same reading
as `studies/earthquake/hypothesis.yaml`. M. Ramakrishna Bhat's translation
(1981) has not been checked; if it differs, the table in
`libs/vedic_astrology_core/astrology/mundane.py` changes and every rule using
`moon_mandala` gets a new version.
