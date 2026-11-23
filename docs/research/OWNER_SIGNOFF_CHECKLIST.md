# Owner sign-off checklist

These are the decisions only the owner can make. No confirmatory result can be published until they are signed. Tick each box and add your initials and date. When done, tell Claude "sign-offs done" and the plans are sealed with these dates.

Estimated time: 2 to 3 hours in total.

## A. Read and confirm (evidence)
- [ ] **H11, classical citations (about 60 min).** Open `research/incoming/texts/round5_local_books/verification.csv`. For each row marked `close`, open the PDF page in your local book (file and page are in the row) and confirm the quote. Write `checked_by` and `checked_on` in the row. 32 rows. This moves rules from level L0 to L1/L2.
- [ ] **H4, data licences (about 30 min).** For each source in `data/registry/licences.yaml`, open the `terms_url`, read the terms, and set `verified: true` and `date_read`. Watch: SILSO says CC BY-NC 4.0 (non-commercial); IITM terms are unclear; Bundesbank requires naming the source.
- [ ] **H18, smallest effects of interest (about 30 min).** Open `docs/research/SESOI_PROPOSAL.md`. For each candidate (M-1 to M-4, G-1, G-2, E-1, E-2), open the cited paper at the page given and confirm the number. Reject any you cannot confirm. Without a SESOI, a test can never say "effect excluded".

## B. Approve settings (decisions)
| Id | Decision | Default proposed | Approve? |
|---|---|---|---|
| H16 | Explore/confirm splits and budgets per domain (ADR-007 section 5) | daily gold explore to 1986, confirm from 1987; and so on | [ ] yes / [ ] change |
| H17 | Monsoon runs once its plan is sealed and calibration passes | yes | [ ] |
| H19 | External timestamp: OpenTimestamps of the seal-bundle hash (only a 64-character hash leaves the machine) plus a public git remote | yes | [ ] |
| H20 | Alpha per batch: 0.04 × 0.2^(b-1), split equally over the batch's tests | yes | [ ] |
| H21 | Yearly test: AR(1) envelope ±0.3, ENSO phase threshold 0.5 °C, base period 1991–2020, two epoch halves | yes | [ ] |
| H22 | A test is one-sided only when the source states the direction in a quotation | yes | [ ] |
| L2 | Rules at citation level L2 may be tested, and every verdict says "encoding" | yes | [ ] |
| Support | "Supported" needs the unseen confirm period; "excluded" may use the whole period | yes | [ ] |

## C. Optional, raises quality
- [ ] **H10, founding times.** Primary source for India 1947-08-15 00:00 (Constituent Assembly record) and Nepal 2008-05-28 (your Maitreya file says 23:26; find the Constituent Assembly record).
- [ ] **ISC-GEM catalogue.** Manual download (CAPTCHA) from isc.ac.uk/iscgem; put the CSV in `data/snapshots/` and tell Claude.
- [ ] **H15, astrologer review.** Ask one astrologer to read three case files and the principle cards and record what they think is wrongly encoded.
- [ ] **H6, cleanup.** Approve deleting the withdrawn PDFs (`papers/pdf/*`), old release files and the stale `research/` tree (`research/incoming/` stays).

Related files: `docs/research/OWNER_DECISIONS.md` (log), `docs/adr/ADR-008-statistical-hardening.md` (details).
