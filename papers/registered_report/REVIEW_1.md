# Review 1: Stage 1 Registered Report

Manuscript: papers/registered_report/manuscript.qmd (rendered 2026-11-23, HTML deleted afterwards).
Checked against the committed sources: studies/validity/preview/*/results.json, studies/validity/calibration/certificate.json, studies/validity/domains/*.yaml, research/incoming/texts/round5_local_books/verification.csv, docs/research/FINDINGS_LEDGER.md, docs/research/STRATEGY_AUDIT_2_2026-11-23.md, docs/adr/ADR-008-statistical-hardening.md.

## Scores

| # | Criterion | Score |
|---|---|---|
| 1 | Importance and rationale | 6 |
| 2 | Logic and plausibility of hypotheses | 4 |
| 3 | Soundness and feasibility of methods (incl. calibration) | 4 |
| 4 | Detail sufficient to prevent undisclosed flexibility | 6 |
| 5 | Outcome-neutral checks and positive controls | 4 |
| 6 | Data quality and provenance | 6 |
| 7 | Treatment of astrological sources | 3 |
| 8 | Writing, structure, reproducibility | 7 |
| 9 | Honesty about limitations and status | 8 |
| | **Overall** | **5 / 10** |

**Decision: major revision.** Under PCI RR / RSOS rules this is not yet reviewable as a Stage 1: the yearly primary test is unimplemented, there is no valid certificate, no SESOI, and the hypotheses are not yet the ones the title promises. The design ideas (equal-size sign-flip blocks, effect-removal exclusion, fixed per-batch alpha spending, verdict allow-list, seen-vintage rule) are good.

## Numbers checked

Correct: 815 = 26+705+42+42; 0.05 x 1138 = 56.9; 445,608 hourly units for 1976-01-01 to 2026-10-31; alpha_1/(1-rho) = 0.04/0.8 = 0.05; a_test 0.04/8 = 0.005 and 0.04/27 = 0.00148; blocks needed 9 and 11 (two-sided minimum p 2^(1-K)); expected false positives 0.35 and 0.60; 57 tests; certificate 504 cells = 427 fast + 65 full + 12 property, 39 cases, 46 code hashes; verification.csv 37 rows (23 BS, 14 BPHS; 32 close, 5 not found); all pilot estimates and p-values in Tables 11 and 13 match the preview files. The 47 references are real and their bibliographic details are correct as far as I can check; none looks fabricated.

Errors or misleading statements:
- The subtitle says "the confirmatory analyses are sealed". Nothing is sealed (Section 3.11, H19).
- Section 3.6 says the block gate called "7 of 7 monsoon tests untestable for this kind of reason". The preview gives no_clean_control for 3 and no_sesoi for 4 (Table 10 says the same thing). Only 3 support the claimed motivation for the year test.
- Table 18 and Section 3.12 call the pass rule "upper bound at most 0.085". For fast cells the code tests the observed rate against 0.085 (ADR-008 line 68; tests/test_validity_calibration.py:99). 17 cells marked passed have Clopper-Pearson upper bounds above 0.085, up to 0.103 (B3 ar1_0.3 daily moon_nakshatra_group at 7.75%; Z3 saturn_in_fire at 7.75%; R2N ar1_0.3 tithi_group at 7.5%).
- Earthquake pilot: estimate_with_baselines equals estimate_without_baselines to every digit in all 7 records (the nodal baseline was declared, and the solar one was missing). Either the baseline was not applied or it had no effect; the text does not say which.
- Section 7 lists unsigned plan fields as H16, H18, H19, H20, L2 and Support. Table 17 adds H21, H22, H4 and H11. The two lists should agree.
- Section 3.11/3.12 say only that the second audit "lists open findings". It lists 9 open critical entries (5 distinct problems, N-01 to N-05) and 41 open majors (STRATEGY_AUDIT_2 section 5). Give those numbers.
- The Varuna paragraph leaves out the prior result that matters most. The project already saw Varuna in the confirm years (RR 1.89, p = 0.010, FINDINGS_LEDGER line 80) and a Molchan p = 0.0009. Say so explicitly.

## Fixes the authors can do now

1. Correct the subtitle, the "7 of 7" sentence, the Section 7 decision list and the audit counts (above).
2. Table 18 / 3.12: report each cell's actual pass rule (observed rate for fast cells, bound for full cells). List the 17 cells whose bound exceeds 0.085. State that size inflation under AR(1) 0.3 and GARCH on daily Moon calendars (7 to 8%) is unresolved, and why it matters for gold (volatility clustering).
3. Add a pre-specified positive-control section (criterion 5). Each domain must detect a known non-astrological calendar effect with the same pipeline before any verdict is read: ENSO phase for monsoon, weekday or month for gold, season for Himalayan seismicity. Fix in advance the pass rule, and what happens if a control fails (flag.control_not_detected exists in the code but is not described in Methods). Also describe the planted-effect checks in the real series.
4. Explain the identical with/without-baseline estimates in the earthquake pilot. Report the baseline R^2 (R4) for the earthquake tests, which is "not_computable" in all 7.
5. Gold detrending: a centred 251-bar running mean uses future outcomes. State how it is computed at the explore/confirm boundary, and show that no confirm row enters an explore-period residual (the preview shows confirm_rows_read = false, but the mechanism should be stated). Otherwise use a trailing window.
6. Mandala encoding: Bhat lists Abhijit in the Indra mandala and the code drops it (verification.csv notes). The manuscript does not mention this. Add it to the choices column and the sensitivity grid.
7. Retitle, or reframe the title and abstract. Only 5 of 30 principles cite a classical chapter, all are L0, and 25 come from the project's own study plans. "Testing classical ... principles" overstates the content. Something like "A pre-registered framework for testing ..." with the current list called illustrative would fit.

## Fixes blocked on owner decisions or future runs

8. H18 / H21 / H22 / H20 / H19 / H4 / H11: sign the SESOI table at the page, the year-test envelope, the side rule, the alpha table, the timestamp choice, the licences, and the human check of citations. Raise at least the 5 classical principles to L2 and, ideally, have an independent practitioner attest them at L4 before Stage 1 submission. Today 57/57 tests are below the entry level, so nothing is registrable.
9. Implement and fully certify the year test. Run a full (non-fast) calibration from a clean clone on frozen code. Close audit N-01 to N-06 (including R2 at 9.9%, and exclusion with correlated baselines). Then regenerate the pilot under the current plans and side rule.
10. Design: monsoon gets 35 explore and 34 confirm years on a seen vintage, so it can only ever limit. Consider an ENSO series that starts earlier (an ERSST or HadISST Nino 3.4 back to the 1870s) to use 1871 to 1947, and a post-2016 IMD vintage as an unseen confirm period. Pre-register the Varuna mandala on an untouched catalogue (ISC or a global ComCat region), the one place a "supported" verdict could be informative. Earthquake and monsoon offer no S/C on the current vintages, so be explicit that gold is the only domain where this report can support anything.
