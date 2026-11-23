# Round 5: citations located in the owner's local book scans

`verification.csv` gives, for each method in `rules/mundane/methods/` and each rule in `rules/`
whose source cites BPHS or Brihat Samhita, the passage found: chapter, verses, printed page, PDF
page, a short quotation (at most about 40 words) and a match quality.

## Provenance

- **BPHS**: R. Santhanam's translation (Ranjan Publications, 2 vols), the owner's private scans
  `BPHS - 1 RSanthanam.pdf` and `BPHS - 2 RSanthanam.pdf` (Documents/Astro/Books). Text from the
  scans' own OCR layer (`pdftotext`). The year of the edition is not printed in that text layer; the
  catalogue keeps the year it had (1984). Printed page = PDF page + 1 (vol. 1) and + 490 (vol. 2).
- **Brihat Samhita, English**: M. Ramakrishna Bhat's translation (Motilal Banarsidass, 1981), read
  from the archive.org OCR text of Part 1 (item
  `flWL_brihat-samhita-of-varaha-mihir-part-1-edited-by-m-ramakrishna-bhat-motilal-banarasidas-delhi`)
  and Part 2 (item `brihat-samhita-of-varaha-mihir-mr.-bhat-part-2-of-2-1981`). This is **not** a
  local copy; the owner's Brihat Samhita scans are Hindi and Sanskrit and have no text layer.
  Printed pages come from the running heads in the OCR; where a head is missing the page is a range
  or marked inferred. There is no PDF page for these rows.
- **Brihat Samhita, Sanskrit with Hindi**: the owner's scan
  `बृहत्संहिता_Brihat_Samhita_Dr._Surkant_Jha.pdf`, chapter 32 only, OCR with tesseract (hin+san)
  for this check. The Sanskrit quotations are corrected by hand for OCR slips. Printed page = PDF
  page + 19 (read from noisy header digits; confirm).

Nothing here was checked by a person. Every row was located by machine (search in OCR text, then a
reading of the passage) and awaits the owner's confirmation against the books. In the edited YAML
files `checked_by` / `checked_on` (`checked_at` in the method catalogue) stay empty, so no
citation level rises (ADR-004: a source becomes page-cited only with a recorded check). The method
catalogue has no `page` field, so its page goes into `edition`.

No scans or long extracts are stored in the repository: only page numbers, short quotations and
the local file names.

## Match quality

- `close`: the passage is found and supports what the target cites; the quotation is OCR text with
  spacing and obvious OCR slips corrected (noted per row).
- `not_found`: no passage at the cited place supports the claim. The notes give where the subject
  is actually treated, if anywhere. These targets were not edited.
- No row is `exact`: all quotations pass through OCR.

## Findings that differ from the repository

- **Mandalas (BS 32)**: Bhat and Jha both put Uttara Bhadrapada (Ahirbudhnya) in Varuna and
  Uttarashadha (Vaishva) in Indra, as `MANDALAS` in `astrology/mundane.py` already does; the Iyer
  1884 duplicate is a misprint there. No list differs.
- **Samvatsara (BS 8)**: the text defines the Jovian cycle (Prabhava begins when Jupiter rises in
  Dhanishtha in Magha, v. 27). `astrology/mundane.py` attributes its luni-solar, Chaitra-start count
  to ch. 8.
- **Year lord (BS 19)**: gives effects of the year's lord; how the lord is chosen and the Chaitra
  Pratipada chart for the capital are not in ch. 19.
- **core.r011 (Agastya)**: BS 12.22 has Canopus rise with the Sun in Hasta, not at Simha 23 deg.
- **core.r002, core.r016**: the cited chapters are the registry's own; the passages are BS 16 and
  BS 24.5 (Moon with Rohini in dark Ashadha).
- **seismic.mangal_ketu_***: BS 17 has no Mars-Ketu or earthquake passage.
- No rule or method cites the commodity-price chapters (BS 41-42), so none were looked up.
