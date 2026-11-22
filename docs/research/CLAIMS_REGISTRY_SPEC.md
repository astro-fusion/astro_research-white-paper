# Claims registry: specification

- Status: proposed, 2026-11-22
- Decision record: [ADR-005](../adr/ADR-005-pattern-discovery-and-claims-registry.md) (packages WP-31, WP-32, WP-33; design task D5; owner actions H8, H9)
- Builds on: [PAPER_ROADMAP.md](PAPER_ROADMAP.md) sections 3.4 and 4; [research/incoming/README.md](../../research/incoming/README.md); [INCOMING_AUDIT_2026-11-22.md](handover/INCOMING_AUDIT_2026-11-22.md)

## 1. Purpose

An open, checkable list of what astrologers have publicly claimed about earthquakes, rain and floods, gold and silver, and other mundane events. For each claim it records where it was made, when, in what words, and whether it could be tested. Claims that can be tested are scored against what happened and against what anyone could have guessed.

It answers three questions a reader cannot answer today:

1. Was this said **before** the event, and can that be proven?
2. Was it **specific** enough to be wrong?
3. Did it do better than the **base rate**?

What the registry is not: a ranking of people, a judgement of sincerity, or a test of astrology as a whole. It scores claims.

## 2. What goes in

| Source type | Code | Examples | What counts as the record |
|---|---|---|---|
| Classical text | `classical` | Brihat Samhita, Bhadrabahu Samhita, Meghamala | Edition, translator, chapter, verse, page; a scan link |
| Modern book | `book` | Practitioner handbooks | Edition, year, page |
| Periodical | `periodical` | The Astrological Magazine, newspaper columns | Title, issue date, page; library or archive reference |
| Blog or website | `web` | Practitioner blogs, forecast pages | Permalink to the article (never a home page) plus an archive capture |
| Video | `video` | YouTube, Facebook video, TV clips | Permalink with start and end timestamps; the spoken words |
| Social post | `social` | X, Facebook, Instagram, TikTok, Telegram | Permalink to the single post plus an archive capture |
| Paid newsletter | `newsletter` | Subscription market letters | Issue date and a dated third-party quote of it; the letter itself is not copied |

One row is one claim: one statement about one outcome in one window. An article with five predictions is five rows that share a `source_id`.

## 3. Schema

File: `claims.csv` (UTF-8, comma-separated, header row, dates `YYYY-MM-DD`, times in UTC, the literal `NOT FOUND` for a gap). A JSON copy carries the same fields.

### 3.1 Who and where

| Column | Type | Rule |
|---|---|---|
| `claim_id` | text | `clm-` plus 6 digits. Never reused. |
| `source_id` | text | `src-` plus 5 digits. Same for all claims from one article, video or page. |
| `claimant_name` | text | Name as published. `unnamed` for anonymous or private persons (section 9). |
| `claimant_kind` | enum | `professional`, `institution`, `media_guest`, `classical_author`, `private` |
| `presented_by` | text | If someone else is reporting the claim (a TV host, a website citing a late author). Else blank. |
| `source_type` | enum | Section 2 codes |
| `outlet` | text | Site, channel, magazine or book title |
| `url` | URL | The exact permalink. A home page, channel page or search page is invalid. |
| `media_locator` | text | Video: `hh:mm:ss-hh:mm:ss`. Print: page. Classical: chapter and verse. |
| `language` | text | ISO 639-1 code of the original words |

### 3.2 When, and proof of when

| Column | Type | Rule |
|---|---|---|
| `claim_date` | date | The date the claim was made public, as the source states it |
| `claim_date_basis` | enum | `archive_capture`, `platform_timestamp`, `print_issue`, `third_party_quote`, `self_reported`, `none` |
| `archive_url` | URL | A real capture (web.archive.org, archive.today). Placeholder timestamps are rejected. |
| `archive_capture_utc` | datetime | The capture's own timestamp, read from the archive |
| `proof_date` | date | The earliest date on which an independent party shows the words existed. Computed (section 5). |
| `proof_note` | text | One sentence: what proves the date |

### 3.3 What was said

| Column | Type | Rule |
|---|---|---|
| `quote_original` | text | Verbatim, original language, at most 60 words. For video, the transcribed segment. |
| `quote_english` | text | Translation if the original is not English; else blank |
| `transcript_basis` | enum | `n/a`, `platform_captions`, `auto_captions`, `human_transcription` |
| `context_note` | text | At most 40 words of neutral context (for example "said in reply to a question about 2026") |

### 3.4 The rule and the prediction

| Column | Type | Rule |
|---|---|---|
| `claimed_rule` | text | The astrological reason given, in the claimant's terms ("Jupiter enters Virgo") |
| `zodiac_stated` | enum | `sidereal`, `tropical`, `not_stated` |
| `rule_file` | path | A file under `rules/` if the rule has been encoded; else blank |
| `domain` | enum | `earthquake`, `rain_flood`, `gold`, `silver`, `other_market`, `political`, `other` |
| `predicted_event` | text | What should happen, in plain words |
| `direction_or_category` | text | `up`, `down`, `deficient`, `normal`, `excess`, `occurs`, `does_not_occur`, or blank |
| `magnitude_or_level` | text | "M 7 or above", "1,400 USD", "95 to 100% of LPA", or `not_stated` |
| `region` | text | As stated, plus a bounding box in `region_bbox` if one can be drawn without guessing |
| `window_start`, `window_end` | date | As stated. `open` if no end is given. |
| `probability_stated` | number | If the claimant gave one; else blank |
| `hedge_words` | text | The hedging words used ("may", "likely", "sooner or later") |

### 3.5 Classification (coded, sections 4 to 6)

| Column | Type | Rule |
|---|---|---|
| `timing_class` | enum | Section 4 codes |
| `specificity` | 0 to 5 | Section 6 |
| `evidence_grade` | A to F | Computed from the fields above (section 5). Never typed by hand. |
| `scorable` | yes/no | Computed: grade A or B and `timing_class` = `E1` |
| `linked_claim_id` | text | For a retroactive claim, the original it refers to, if found |

### 3.6 Outcome (filled later, by a different person or run; section 7)

| Column | Type | Rule |
|---|---|---|
| `outcome_code` | enum | `hit`, `miss`, `partial`, `pending`, `unscorable`, `not_scored` |
| `outcome_evidence` | text | Snapshot name and SHA-256 from `data/snapshot_index.json`, plus the observed value |
| `base_rate` | number | Probability that the predicted event happens anyway (section 7.2) |
| `brier`, `brier_base` | number | Scores of the claim and of the base rate |
| `ledger_seq` | integer | Line in `forecasts/ledger.jsonl` if the claim was entered while still open |

### 3.7 Provenance

| Column | Type | Rule |
|---|---|---|
| `collected_by` | text | `gemini`, a person's handle, or `submission` |
| `collected_round` | text | Folder name under `research/incoming/claims/` |
| `verified_by`, `verified_at` | text, datetime | Who opened the source and found the quote; when |
| `coder_1`, `coder_2` | text | Who coded sections 3.4 and 3.5; second coder on the audit sample |
| `reply` | text | The claimant's reply, verbatim, with date (section 9) |
| `row_sha256` | text | Hash of the row's content fields, for change tracking |
| `status` | enum | `incoming`, `accepted`, `rejected`, `withdrawn` |
| `reject_reason` | text | Why, if rejected |

## 4. Before or after: the timing taxonomy

| Code | Name | Definition | Scored? |
|---|---|---|---|
| `E1` | Ex-ante, proven | `proof_date` is before `window_start` and before the event | Yes |
| `E2` | Ex-ante, late proof | The source's own date is before the window, but the earliest independent proof is after the window opened and before it closed. Scored only on the part of the window after `proof_date`, and flagged. | Partly |
| `E3` | Ex-ante, unproven | The source says it was published before; no independent proof exists | No |
| `O` | Open-ended | Made before the event but with no end date or no region ("sooner or later") | No (cannot be wrong) |
| `P1` | Post-hoc explanation | Made after the event, explaining it by the sky. Does not claim to have predicted it. | No |
| `P2` | Retroactive claim | Made after the event, saying "I predicted this" | No (see below) |
| `R` | General rule | A standing rule with no dated prediction ("Saturn in Rohini brings drought") | Not as a claim. It can be encoded under `rules/` and tested there. |
| `C` | Classical | A verse in a classical text | Same as `R` |

### 4.1 Retroactive "I predicted it" videos and posts

These are common and they are the main way a reputation is built. Handling:

1. Record the retroactive statement itself as a `P2` row, with its own date and quote. It is never scored.
2. Look for the **original**. The retroactive source usually names it or shows a clip.
3. If the original is found with its own permalink and independent date proof, add it as a separate row (`E1`, `E2` or `O` on its merits) and link the two rows with `linked_claim_id`.
4. Compare the two. Record in `context_note` if the original was vaguer than the retelling: a wider region, a longer window, a lower magnitude, or "something will happen".
5. If no original is found, the `P2` row stays with `linked_claim_id` blank. The site shows it as "retroactive claim, original not found". That is a statement about the evidence, not about honesty.
6. **Find the misses too.** For every source with a `P2` row, collect every dated prediction the same source made in the same outlet in the 24 months before. A hit means nothing without the count of attempts.

### 4.2 What counts as proof of date

| Basis | Counts as proof? | Notes |
|---|---|---|
| Archive capture dated before the window | Yes | The strongest. The capture must contain the quote. |
| Platform timestamp | Yes, with care | A video's upload date and spoken content are fixed by the platform. Its **title, description, thumbnail and pinned comment can be edited later** and count only if archived. Posts on platforms that allow edits count only with the edit history or an archive capture. |
| Print issue | Yes | Issue date plus a library holding, ISSN record or scan |
| Dated third-party quote | Yes | A news article or another site, itself dated and archived, quoting the claim |
| The site's own date, CMS field or "posted on" line | **No** | Dates on a claimant's own site can be changed. This gives `E3`. |
| A screenshot | **No** | Easy to fake. Use it only as a lead to find the real post. |

`proof_date` is the earliest date supported by a row of this table marked "Yes".

## 5. Evidence grade, A to F

The grade describes **the record of the claim**: can we prove what was said, when, and can it be checked. It says nothing about the person and nothing about whether the claim came true. It is computed by code from the fields (WP-32).

| Grade | Meaning | Conditions (all must hold) |
|---|---|---|
| **A** | Proven and fully testable | Quote verified at source; `timing_class` = `E1`; `specificity` 4 or 5 |
| **B** | Proven, testable with stated assumptions | Quote verified; `E1` or `E2`; `specificity` 3 |
| **C** | Proven words, not testable | Quote verified; date proven; `specificity` 0 to 2, or `timing_class` = `O` |
| **D** | Words verified, date not proven | Quote verified; `timing_class` = `E3` |
| **E** | After the fact | Quote verified; `timing_class` = `P1` or `P2` |
| **F** | Unverifiable | Quote not found at the source, source dead with no archive, home-page URL only, or second-hand report with no original |

Classical verses and general rules (`C`, `R`) are not graded A to F. They carry the validation level L0 to L6 of their rule file instead (ADR-004 D-4).

Only grades A and B are scored. Grades C to F are published and counted. The counts are a finding in themselves.

## 6. Specificity, 0 to 5

One point for each of the following that the claim itself states. Coders do not fill gaps with what the claimant "must have meant".

| Point | Question | Earns the point | Does not |
|---|---|---|---|
| What | Is the event defined? | "an earthquake of magnitude 7 or more"; "gold closes above 1,400 USD" | "upheaval", "volatility", "nature's fury" |
| Where | Is the place bounded? | "Uttarakhand"; "within 300 km of Kathmandu"; one named market | "the north", "Asia", "many countries" |
| When | Is there a start and an end, at most 12 months apart? | "between 1 and 15 March 2027" | "soon", "in the coming years", no end date |
| How much | Is there a size, level or category? | "M 7 or above"; "deficient monsoon"; "by 10%" | "strong", "significant" |
| How sure | Is it stated plainly or with a probability? | "will"; "70% chance" | "may", "cannot be ruled out", "possible" |

A claim with 3 points needs an assumption to be scored. The assumption is written in `context_note` and comes from the coding manual (design task D5), not from the outcome.

## 7. Outcome scoring

### 7.1 Order of work

1. **Collect** (section 10). The collector does not record outcomes.
2. **Verify** the source and the date. Compute the grade.
3. **Code** the prediction (section 3.4) **without looking up what happened.** For old claims the coder may already know. That is why 20% of rows are coded twice (H9) and agreement is reported.
4. **Freeze.** Coded rows are committed. Claims whose window is still open are entered in the forecast ledger (ADR-005 E-8).
5. **Resolve** from our own data snapshots: the earthquake catalogue, the price snapshot, the rainfall series. Never from a news report or from the claimant.
6. **Score.**

### 7.2 Base rates

A claim earns credit only for beating what anyone could have said. The base rate is computed from data dated **before** `proof_date`.

| Claim type | Base rate |
|---|---|
| Earthquake of magnitude M or more in a region and window | Poisson probability of at least one such event, from the catalogue rate for that region and magnitude. A wide region, long window or low magnitude gives a base rate near 1, so a hit earns almost nothing. |
| Gold or silver direction over a window | Share of all windows of the same length in the 20 years before, in which the price moved that way |
| Gold or silver level | Probability from a random walk with drift and the previous year's volatility |
| Monsoon category | Climatological frequency of the category in the 50 years before |
| Other | Written in the coding manual before the first claim of that type is scored. If none can be defined, the claim is `unscorable`. |

### 7.3 Outcome codes

| Code | Rule |
|---|---|
| `hit` | Every stated element happened inside the stated window and region |
| `miss` | The window closed and the event did not happen as stated. An event just outside the window, region or magnitude is a miss. The near-miss is noted, not rewarded. |
| `partial` | A claim with several stated elements where the main element happened and a secondary one did not. Defined per claim type in the manual. Scored as a miss in the main analysis and as a hit in a sensitivity analysis. |
| `pending` | The window is still open |
| `unscorable` | Grade A or B, but no base rate or no outcome data exists |
| `not_scored` | Grade C to F |

### 7.4 Scores

- **Brier score** of the claim (probability 1 for a plain "will"; the hedge table of the manual otherwise) and of the base rate. **Brier skill** = 1 - brier / brier_base. Above zero beats the base rate.
- **Ranked probability skill** for ordered categories (monsoon).
- **Molchan diagram** for sets of earthquake alarms from one method.
- The plain hit rate is always shown next to the base-rate hit rate.
- Implementation: ADR-004 WP-24 and ADR-005 WP-32, WP-34.

### 7.5 Reporting rules

- Totals first: how many claims at each grade, how many scorable, how many hits, the base-rate expectation.
- Per-method and per-source summaries only when there are **10 or more scored claims**, with an interval from resampling. Below 10, the rows are listed and no summary is given.
- Uncertainty is computed by resampling sources, not claims. Ten claims by one person are not ten independent tests.
- **The collected past is not a census.** Failed forecasts get deleted and successes get repeated. Any skill found in old claims is an upper bound. Only claims entered in the ledger while still open are free of this bias. The site says so above every table.

## 8. Licensing and fair use

- **Store:** the link, the archive link, a short verbatim quote, and our own coding. Facts and dates are not copyrightable.
- **Do not store:** video or audio files, thumbnails, full transcripts, full articles, scans of whole pages, paywalled newsletter text.
- **Quote length:** the shortest passage that carries the claim, at most 60 words. A longer prediction is summarised in `predicted_event` and the quote keeps the key sentence.
- **Transcripts:** only the quoted segment, with timestamps. The link and timestamp let any reader check it.
- **Attribution:** every quote shows its author, outlet, date and link.
- **Paid content:** not copied. A claim from a paid letter enters only through a public, dated third-party quote.
- **Our data:** the registry's structure and coding are released under CC BY 4.0. Quotes remain their authors'.
- **Archiving:** saving a public page to the Internet Archive is done for proof of date. Requests from a rights holder to remove a capture are theirs to make to the archive.
- This is a research practice, not legal advice. Quotation rules differ by country. If a rights holder objects to a quote, replace it with a paraphrase marked as such and keep the link.

## 9. Ethics: score claims, not people

1. **Claims, not character.** No row or page says anyone lied, cheated or is a fraud. The registry reports what the record shows: "original not found", "date not proven", "window closed, event did not occur".
2. **Public claims by public practitioners only.** A person qualifies if they publish predictions under their own name as a professional or institution. Private individuals, commenters and callers are recorded as `unnamed` or not at all.
3. **No personal data.** No addresses, phone numbers, family details, health details, or birth data of living private persons. A claimant's own published birth chart is not copied.
4. **No ranking.** No leaderboard, no "worst" or "best" list, no score per person below 10 scored claims.
5. **Same rules for everyone.** The same grade and scoring rules apply to astrologers, to this project's own frozen models, and to the baselines. The project's own models appear in the same tables.
6. **Hits are reported as readily as misses.** A proven, specific, ex-ante hit is shown with the same prominence, with its base rate.
7. **Right of reply.** Any named claimant may send a reply through the contact route on the site (H8). The reply is published verbatim (up to 300 words) on the claim's row within 14 days. A reply does not change a grade; evidence does.
8. **Corrections.** If a claimant or reader shows an error (wrong quote, wrong date, a missed original, a better archive capture), the row is corrected, the change is logged with date and reason in `data/registry/claims/CHANGELOG.md`, and the old row hash is kept.
9. **Removal.** A row is withdrawn (kept in history, hidden on the site) if it concerns a private person, contains personal data, or cannot be verified after a challenge. A row is not withdrawn because a correct record is unwelcome.
10. **Harm check.** Predictions of death, illness or disaster for a named private person are not recorded. Earthquake alarms are shown with a notice that no method, planetary or otherwise, predicts individual earthquakes, and with a link to the national seismological authority.
11. **AI-collected rows are untrusted.** On 2026-11-22 the first collection round had quotes found on the cited page for 2 of 56 gold rows, 2 of 54 earthquake rows and 0 of 27 monsoon rows. A row is published only after a person or a logged fetch has found the quote at the source.

## 10. Collection

### 10.1 Flow (reuses the existing quarantine)

```
research/incoming/claims/round-NN/claims.csv      untrusted, kept unedited, listed in MANIFEST.csv with SHA-256
        |  tools/ingest validate (WP-10 + WP-31): contract, URL fetch, archive check, quote match, grade
        |  person: open flagged rows; code sections 3.4 and 3.5; second coder on 20%
        v
data/registry/claims/claims.csv                   accepted rows only, committed, with verified_by and row hashes
        |  core/claims/score.py (WP-32): base rates, outcomes from hashed snapshots
        v
site/data/claims.json + claims.csv                public page and downloads (WP-33)
```

- A new collection or correction is a **new round folder**. Earlier rounds are never edited.
- `MANIFEST.csv` is regenerated whenever a round is added (columns `path, topic, round, csv_rows, sha256`; topic `claims`).
- The rows already in `research/incoming/{gold,earthquake,flood}/verified/` (56 + 54 + 27 forecasts, 28 episode claims, 36 M 7 events) and the 19 rows of `studies/mundane/sources/prediction_cases.csv` are migrated into the first claims round as they are, with their current verification status. Nothing is promoted without the checks above.

### 10.2 Prompt for Gemini (standalone; paste as is)

```text
ROLE
You are a research assistant collecting public predictions made by astrologers.
You only collect and document. You do not judge whether a prediction came true.
Do not look up, mention or record outcomes.

TOPIC FOR THIS RUN
<one of: earthquakes in South Asia | Indian monsoon rain and floods | gold and silver prices>
PERIOD OF CLAIMS: <start year> to <end year>
SOURCES TO SEARCH: <list of sites, channels, magazines, or "open search">

HARD RULES
1. Never invent. If you cannot open a page and see the words yourself, write NOT FOUND.
   A row with NOT FOUND is useful. An invented row is harmful.
2. The url must be the exact page, post or video that contains the words.
   A home page, a channel page, a tag page or a search page is not allowed.
3. The quote must be copied character for character from the source, in its
   original language, at most 60 words. Do not tidy, shorten inside, or merge sentences.
   For a video, give start and end timestamps (hh:mm:ss-hh:mm:ss) and say whether the
   words come from platform captions, auto captions, or your own listening.
4. For every url, query the Internet Archive for the earliest capture
   (https://web.archive.org/cdx/search/cdx?url=<url>&limit=1&fl=timestamp,original).
   Record the real capture URL and its timestamp. Open the capture and confirm the
   quote is in it. If there is no capture, write NOT FOUND. Never write a made-up
   timestamp.
5. Record the date the source itself shows, and say where you read it
   (visible page date, platform timestamp, print issue). Do not decide whether
   the claim was made before the event. Do not fill window dates the source does not state.
6. One row per prediction. An article with four predictions is four rows with the
   same source_id.
7. Collect misses and vague claims as carefully as striking ones. When you find a
   source that says "I predicted X", also list every other dated prediction the same
   source published in the same outlet in the two years before, whatever happened to them.
8. If a video or post says "I predicted this earlier", record it as its own row with
   retro_claim = yes, then search for the earlier original and record that as another
   row. If you cannot find the original, say so in notes.
9. Do not copy full articles, full transcripts, images or video. Do not record
   personal details of anyone. Skip predictions about named private persons.
10. Do not send the project's name, the owner's name or any personal detail to any site.

OUTPUT
Write one file: research/incoming/claims/round-<NN>/claims.csv
UTF-8, comma-separated, header row, dates YYYY-MM-DD, NOT FOUND for any gap.
Columns, in this order:

source_id, claimant_name, claimant_kind, presented_by, source_type, outlet, url,
media_locator, language, claim_date, claim_date_read_from, archive_url,
archive_capture_utc, quote_in_archive (yes/no/NOT FOUND), quote_original,
quote_english, transcript_basis, claimed_rule, zodiac_stated, domain,
predicted_event, direction_or_category, magnitude_or_level, region,
window_start, window_end, probability_stated, hedge_words, retro_claim (yes/no),
refers_to_source_id, fetched_at_utc, http_status, notes

Allowed values:
claimant_kind: professional | institution | media_guest | classical_author | private
source_type: classical | book | periodical | web | video | social | newsletter
zodiac_stated: sidereal | tropical | not_stated
domain: earthquake | rain_flood | gold | silver | other_market | political | other
window_end: a date, or "open" if the source gives no end.

Also write research/incoming/claims/round-<NN>/collection_log.md with:
- every search query you ran;
- every source you checked and how many predictions you found there;
- every url that failed to open, with its HTTP status;
- anything you were unsure about.

Do not edit any earlier round. Do not write anywhere else in the repository.

SELF-CHECK BEFORE YOU FINISH
- Open ten of your own rows at random. Is the quote on the page, word for word?
- Is any url a home page? Remove or fix it.
- Does any archive timestamp end in 000000? It is probably invented. Recheck it.
- Did you record any outcome or any judgement of accuracy? Remove it.
Report the result of this self-check at the top of collection_log.md.
```

### 10.3 What the validator checks on arrival (WP-31)

| Check | Action on failure |
|---|---|
| Columns and enums match the contract | Reject the file; suggest a column mapping; never guess |
| `url` is a permalink (path depth, not a known home or channel pattern) | Row grade F |
| `url` and `archive_url` fetch with a generic client name | Row flagged; grade F if both fail |
| Any run of 8 consecutive words of the quote appears on the page or the capture | Row flagged for a person; grade F until found |
| Archive timestamp is real (matches the archive's own index) | Row flagged; `proof_date` blank |
| An outcome or accuracy judgement appears in any field | Field blanked; file flagged |
| A media file is present in the round folder | Round rejected |
| One confirmed fabrication in a file | The whole file goes to full manual checking (PAPER_ROADMAP 4.4) |

## 11. Publication

- **Page:** `site/claims.qmd` ("Claims registry"). Above the table: what the registry is and is not, the grade rubric, the survivorship warning and the right-of-reply notice. Then counts by grade and domain. Then a sortable, filterable table: date, claimant, outlet, quote, timing class, specificity, grade, outcome, base rate, links to source and archive, reply.
- **Downloads:** `site/data/claims.csv` and `site/data/claims.json`, each with a `_meta` block (input hashes, commit, generated time, licence), as the other site data files have. Every release is deposited on Zenodo with the repository (ADR-004 D-3).
- **Change history:** `data/registry/claims/CHANGELOG.md`, and the git history of the registry file.
- **Submissions:** anyone, including astrologers, may submit a claim or a correction through an issue template (extends `CONTRIBUTING_ASTROLOGERS.md`). A practitioner may **register a prediction in advance** this way; it is frozen into the forecast ledger the day it arrives and scored when its window closes. This is the fairest test the project can offer, and the page says so at the top.

## 12. Acceptance for this specification

The registry is ready to publish when:

1. WP-31 validates the first claims round and reports counts by grade.
2. Every published row has `verified_by` filled and a quote found at source.
3. The double-coded sample has Cohen's kappa of at least 0.6 on `timing_class` and on `specificity` (3 or more against less than 3). Below that, the coding manual is revised and the sample recoded.
4. H8 is done: contact route live and policy approved.
5. The page renders with zero per-person rankings and the survivorship warning in place.
