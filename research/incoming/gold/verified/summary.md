# Summary of Gold Astrology Forecasts and Rules Verification

**Audit Date:** 2026-11-22  
**Verification Standard:** Strict primary-source checking (Hard Rules 1–4). No homepages accepted; quotes verified verbatim; ex-ante status requires independent proof of publication prior to target window.

---

## 1. Summary Counts by File

| File | Total Items | Verified | Unverified | Proven Ex-Ante |
|---|---|---|---|---|
| `gold_forecasts_exante.csv` | 56 | 2 | 54 | **1** |
| `episode_astrology_claims.csv` | 28 | 0 | 28 | **0** |
| `rules_gold/*.yaml` | 21 | 7 | 14 | N/A |
| `disputes.md` | 6 | 3 | 3 | N/A |

---

## 2. Forecasts with Proven Ex-Ante Publication Dates

Only forecasts with independent proof of publication prior to the target evaluation window qualify for empirical scoring under ADR-001/ADR-003.

### Qualifies for Scoring (Count: 1)

* **Row 19: Sachin Malhotra (Hindu New Year Chart 2016)**
  * **Astrologer:** Sachin Malhotra
  * **Claimed Publication Date:** 2016-04-05
  * **Independent Proof:** Internet Archive Wayback Machine snapshot `20160329211738` (2016-03-29).
  * **Target Evaluation Window:** 2016-08-11 to 2017-09-12 (Jupiter transit in sidereal Virgo).
  * **Proof Status:** Snapshot (March 29, 2016) is strictly prior to target window start (August 11, 2016).
  * **Exact URL:** `https://astrologicalmusings.com/hindu-new-year-chart-2016-and-forecast-for-india/`
  * **Archive URL:** `http://web.archive.org/web/20160329211738/https://astrologicalmusings.com/hindu-new-year-chart-2016-and-forecast-for-india/`
  * **Verbatim Quote:** *"The prices of Gold will start increasing though after Jupiter, which along with Sun is the karaka of this yellow metal, will come into Virgo in the second week of August 2016."*
  * **Predicted Direction:** Up (`predicted_level`: NOT STATED in text).

### Verified Quote but Ex-Ante Date NOT Proven Independently (Count: 1)

* **Row 56: Tempora Research (Jupiter in Cancer Forward Call)**
  * **Astrologer:** Tempora Research
  * **Target Evaluation Window:** 2025-06-01 to 2026-09-30
  * **Verbatim Quote Verified:** Yes, verified on live web at `https://www.tempora.ltd/findings/gold-jupiter`.
  * **Earliest Archive Snapshot:** 2026-05-30 (`http://web.archive.org/web/20260530070213/https://www.tempora.ltd/findings/gold-jupiter`).
  * **Why Ex-Ante Fails:** The earliest independent snapshot is May 30, 2026—almost a year *after* the June 1, 2025 baseline entry. Because independent publication proof prior to June 1, 2025 is absent, it cannot be scored as a proven ex-ante forecast under Hard Rule 3.

---

## 3. Verified Classical Rules (Count: 7 of 21)

All 7 verified rules originate from Varahamihira's *Brihat Samhita*, verified against M. Ramakrishna Bhat (Part 1, Motilal Banarsidass, 1981) and N. Chidambaram Iyer (1884) with accessible page scans on archive.org:

1. `brihat_samhita_aries_benefic_abundance_gold.yaml` (Ch. 41, v. 2 & 12; Bhat p. 347, 350) — `verified: true`
2. `brihat_samhita_aries_malefic_scarcity_gold.yaml` (Ch. 41, v. 2 & 11; Bhat p. 347, 350) — `verified: true`
3. `brihat_samhita_capricorn_malefic_gold_surge.yaml` (Ch. 41, v. 7 & 11; Bhat p. 349, 350) — `verified: true`
4. `brihat_samhita_moon_benefic_argha_rise.yaml` (Ch. 42, v. 14; Bhat p. 358) — `verified: true`
5. `brihat_samhita_sun_malefic_argha_fall.yaml` (Ch. 42, v. 14; Bhat p. 358) — `verified: true`
6. `brihat_samhita_sun_leo_store_gold.yaml` (Ch. 42, v. 6; Bhat p. 354) — `verified: true`
7. `brihat_samhita_pausha_jupiter_cheap_commodities.yaml` (Ch. 8, v. 5; Bhat p. 89) — `verified: true`

The remaining 14 rules (*Bhadrabahu Samhita*, *Meghamala*, *Vyapar Ratna*, Gann, McWhirter, Meridian, Crawford, Skinner, Gidel, Rosen, Malhotra, Patel, Raman) are marked `verified: false` due to lack of verifiable book page scans, dead URLs, or citations pointing to commercial sales pages and homepages.

---

## 4. Verified Methodological Disputes (Count: 3 of 6)

1. **Direct Dignity vs. Inverse Scarcity Dignity:** Verified (Tempora Research vs. *Brihat Samhita* Ch. 41).
2. **Is Virgo Favorable or Adverse for Gold:** Verified (Sachin Malhotra 2016 vs. Tempora Research 2026).
3. **Zodiac & Ayanamsa Ingress Discrepancies:** Verified (Tropical Merriman vs. Sidereal Lahiri vs. True Pushya Paksha Tempora).
