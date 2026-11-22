# Owner decisions log

Decisions that gate runs. A decision marked **default adopted** was proposed by the design and taken so work could continue; the owner can overturn it, and any run made under it is labelled with the decision id.

| Id | Decision | Status | Date | Source |
|---|---|---|---|---|
| Scope | Test astrological principles on past data only. No forecasting product, forecast ledger, model registry or scoring of astrologers' predictions. | **Owner decision** | 2026-11-22 | owner message; ADR-007 |
| Transparency | Everything in `research/incoming/` stays committed. | **Owner decision** | 2026-11-22 | owner message |
| H16 | Thresholds (SESOI), budgets and explore/confirm splits as proposed in ADR-007 section 5. | Default adopted, pending owner review | 2026-11-22 | ADR-007 |
| H17 | Monsoon/flood runs once its plan is sealed and calibration passes (replaces the Registered Report firewall of ADR-004 D-8). | Default adopted, pending owner review | 2026-11-22 | ADR-007 |
| L2 | Rules at citation level L2 may be tested, labelled "as encoded". | Default adopted, pending owner review | 2026-11-22 | ADR-007 |
| Support | "Supported" needs the confirm period; "effect excluded" uses the whole period. | Default adopted, pending owner review | 2026-11-22 | ADR-007 |
| H6 | Delete withdrawn PDFs (`papers/pdf/*`), old release files and the stale `research/` tree. | **Waiting for owner**: nothing deleted | | ADR-004 |
| H4 | Read licence terms of each data source (Bundesbank, IITM, World Bank, USGS, ISC, NOAA). | Waiting for owner | | ADR-004 |
| H10 | Founding times with primary sources (India, Nepal). | Waiting for owner | | ADR-006 |
| H11 | Open classical texts and record edition, page and verse (BPHS verified for ch. 6 and 46 pages; Brihat Samhita pending). | Waiting for owner | | ADR-006 |
| ISC-GEM | Manual CAPTCHA download of ISC-GEM v13. | Waiting for owner | | audit round 4 |
