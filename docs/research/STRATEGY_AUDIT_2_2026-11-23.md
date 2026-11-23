# Strategy audit, second pass (red team), 2026-11-23

- Role: independent auditor (ADR-008 WP-99). Design and review only. No code, plan, rule or data file was changed. This file is the only output.
- Scope (owner decision, unchanged): past data only; nothing here issues or scores a forecast.
- Audited commit: `b86f5ea` on `main`, working tree as found (dirty: 8 modified `site/data/*.json`, untracked `.cursor/`, `docs/CONTEXT7.md`).
- Read: STRATEGY_AUDIT_2026-11-22, CODE_AUDIT_2026-11-22, ADR-007, ADR-008 with amendments A1 and A2, OWNER_DECISIONS; `core/stats/{blocks,exclusion,season}` and `core/validity/{pipeline,calibration,robustness}` line by line; `seal, sealbundle, family, cli, gate, verdict, sentences, report, plan, limitations`, `core/domains/*`, `markets/placebo.py`, `rules/{schema,levels}.py`, the named tests, `certificate.json` (504 cells), `research/incoming/texts/round5_local_books/`. `core/` = `libs/vedic_astrology_core/`.
- Three sub-reviews (governance, words/schema/report, data/domains) were run by a different model than this report's author and than the author of the fixes; their probes are cited as "sub-review". Claims marked "verified" were re-checked here by reading the line or re-running.
- Run here (appendix A): appendix A of the first audit against the new functions; re-runs of certificate cells through the real pipeline (`tests/test_validity_calibration.py` harness, unchanged); four new simulations. `make calibrate` at full size was **not** run (hours; the machine was under heavy load) and no clean clone was made. That alone leaves E11 unmet.

Severity as in the first audit: **critical** = can by itself produce a wrong verdict or make a central guarantee false. **Major** = biases a verdict or leaves it unconvincing. **Minor** = hygiene.

## 0. Result in one page

| | First audit | Closed | Accepted | Partly closed | Open |
|---|---|---|---|---|---|
| Critical | 7 | 3 (S-02, S-03, A-01) | 0 | 4 (S-01, S-04, S-05, G-01) | 0 |
| Major | 38 | 12 | 0 | 22 | 4 (S-12, D-03, D-04, G-05) |
| Minor | 15 | 6 | 1 (S-14) | 6 | 2 (G-10, O-04) |
| **Total** | **60** | **21** | **1** | **32** | **6** |

New in this pass: **5 critical, 15 major, 8 minor** (section 3).

What the fixes achieved. The statistical core is much better than on 2026-11-22. The two measured failures of the first audit are gone on the new functions: the support test holds 5% where blocks exist (5.1% to 5.4% against 8% to 10% before) and exclusion holds 5% on skewed bars without baselines (4.1% to 6.0% against 13% to 36% before). Thresholds are fixed at batch close, seeds are per test, and the certificate checker refuses the present certificate, which is the correct behaviour.

What is not yet true.

1. **N-01** The calibration certificate does not describe the code it is stamped with. 487 of 504 cells have the same counts as the pre-fix certificate; six of seven such cells re-run here on current code give different counts; two of them now fail (R2 pass rate under no effect 9.9%, 139 of 1,400, and 9.3%, 37 of 400).
2. **N-02** Exclusion is anti-conservative whenever a baseline correlates with the calendar: false "effect excluded" at a true effect equal to the SESOI in 13.5%, 33% and 46% of runs at baseline R-squared 0.14, 0.29 and 0.39, all of which pass R4.
3. **N-03** The holdout can be reopened four ways (self-declared `never_opened`, a new domain string, a renamed copy in its own lock, a local-only ledger commit).
4. **N-04** The calibration check is skipped when the bundle's `outcome_types` list is empty, and that list is supplied by the caller.
5. **N-05** There is no path from a plan and a rule file to a run. Every verdict input (level, SESOI, publication date, disputed flag, seen flag, detrending window, baselines, plan hash) is a value the caller types. The plan validator and the registration checks are not on the run path. No domain plan exists; 0 of 162 rules are registrable; every rule is L0.

No real confirm can run today (OpenTimestamps is a stub that raises; the certificate is refused; the environment differs from the lock; the tree is dirty). So nothing wrong has been produced. The findings are about what would happen on the day those four locks are opened.

---

## 1. Status of every first-audit finding

Cert = `studies/validity/calibration/certificate.json` (created 2026-11-23T00:53:40Z). "Full" = the ADR-008 replication count (10,000 per test, 2,000 families, 1,000 power). "Fast" = 400 replications at the 0.085 mark, which `check_certificate` rightly refuses. Of the 504 cells, 65 are full size, 12 are property checks and 427 are fast. Only 17 cells were re-run after the calibration fixes; see N-01 for why the others, full-size ones included, are weak evidence for the current code. Cells that exercise only the block test and exclusion (B1, B2, B3, X rows without R2) are quoted, because the fixes changed those paths only for odd active counts and zero-inflated bars and the re-runs here agree with them within noise.

### 1.1 Statistical validity

| Id | Sev. | Status | Evidence |
|---|---|---|---|
| S-01 Exclusion on skewed outcomes | critical | **Partly closed** | Method replaced (`stats/exclusion.py`, effect removal on the block statistic). Re-run of appendix A.1 on the new function, 1,500 runs: normal 5.5% / 4.3% (K = 10 / 13), exponential 4.3% / 4.9%, lognormal 6.0% / 4.1%, rare event 1.3% / 3.2% with 28% / 7% "unbounded". Old function, cert X8 full: 12.7%, 21.0%, 34.9%. Cert full cells: X1 normal 501/10,000, t3 485/10,000; X2 exponential K=20 507, lognormal K=20 523. Not closed because (a) N-02: with baselines the same test is wrong; (b) events and flags (X3, X4, X5) and K = 8 and 12 for skew exist only at 400 runs; (c) lognormal K=10 at 6.0% (upper bound 7.1%) needs a full cell. |
| S-02 Shared control bars | critical | **Closed** | `stats/blocks.py` `build_blocks`, `_check_disjoint`; cert B4 (792 designs, no shared bar). Re-run of A.2, 4,000 runs: 5/50 5.3%, 5/6 5.1%, 5/10 4.7%; single-bar one-sided (A2) 1/3 5.2%, 1/2 5.4%; 5/5 and 20/5 are Untestable (2 and 0 used blocks). Cert B1 5/6 K=12 full 521/10,000 (bound 5.59%). Old function, B5 full: 7.7% and 10.0%. |
| S-03 BY stability claim | critical | **Closed** | `family.py:89-90`; `a_test` stored at `close_batch` and re-verified on load (`family.py:686-690`); cert F1, F2, F5, F6 (property). |
| S-04 Adaptive registration | critical | **Partly closed** | Eligibility table and F7 hold; on the same vintage copies get no S (F3 0/400, fast). Bypasses: N-03 a, b. F3 and F4 ran 400 of 2,000 families. |
| S-05 Confirm-once | critical | **Partly closed** | (a) other folder: same rule id refused, renamed copy not (N-03 c). (b) deleted entry: committed, not pushed (N-03 d). (c) data hash: closed, recomputed. (d) direct access: only the `GuardedAdapter` wrapper gates rows; `EarthquakeDomain.catalogue()`, `mainshock_flags()`, `metals._raw_prices` are public; six legacy readers remain (the seal refuses those domains, correctly). (e) provisional: closed. (f) renamed lineage: refused only inside one lock file. (g) amendment: P7 real for the plan file; the run's `plan_sha256` is never compared with the bundle (N-11). Outside deposit: OpenTimestamps is not wired (`sealbundle.py:200-214` raises). P4, P5 use a fake adapter; the shared fixture confirms with a certificate that holds zero cases (N-04). |
| S-06 Estimand mismatch | major | **Closed** | One statistic T for estimate, p, X and SESOI (`blocks.py` `BlockDifferences.statistic`, `primary_test`); `K_eff` in the gate. |
| S-07 Binomial interval | major | **Partly closed** | Not used by `core/validity`; docstring corrected. `FINDINGS_LEDGER.md:14` and `:62` still state "8 of 13 ... doubling outside the 95% interval" with no superseded mark. |
| S-08 Shift test and routing | major | **Closed** | Block sign-flip is the only primary method; no routing table in the pipeline. |
| S-09 Support unattainable | major | **Partly closed** | The gate reports `can_support`, `can_limit`, P(S given SESOI). But the gate ignores R2 feasibility (N-07: `can_support = True` in 400 of 400 runs where S is impossible) and detrending loss (N-08). No real supportability table exists because no plan exists. Owner step open. |
| S-10 Domains and verdict types | major | **Partly closed** | `report.py:125` prints the D x 3 x 5% bound, but D is `DomainRun.domains_in_run_set` (default 1) and a summary is rendered per domain; no cross-domain page. A new domain string gets a fresh 0.04 (N-03 b). |
| S-11 X95 unadjusted | major | **Closed** | E and N sentences cite X-strict; X95 labelled per-test (`sentences.py:140-143`). No calibration cell measures X-strict coverage over families (ADR-008 10.2 asked for one). |
| S-12 Open forking paths | major | **Open** | `plan.validate_plan` is called by no run path (grep: only `validity/plan.py` and its test). `detrend_window` is not a plan key. H16, L2, Support are still "default adopted"; H18, H19, H20 are absent from OWNER_DECISIONS.md. `studies/validity/domains/` does not exist; `studies/monsoon/plan.yaml` fails the validator with 17 errors (sub-review). |
| S-13 SESOI after the answer | major | **Partly closed** | Validator rule exists; `sesoi_sources.yaml` has `entries: []`. `TestDefinition.sesoi` reaches `verdict()` unchecked, so E is possible with any typed number (N-05). |
| S-14 Whole-period support | minor | **Accepted with reason** | ADR-008 section 11: cannot be shown to an outsider for files already on disk. Reasonable. |
| S-15 Side and silent drops | minor | **Closed** | No default side (`blocks.alternative_for`); cert B6: 0 of 315,800 records with blocks unlike the gate's; the pipeline stops on a mismatch. |
| S-16 GARCH-X floor | minor | **Partly closed** | Validator checks a key named `garch_x` only; not on the run path. |

### 1.2 Bias against astrology

| Id | Sev. | Status | Evidence |
|---|---|---|---|
| A-01 Placebo ties, inapplicable kinds | critical | **Closed** (original defect) | R2 per test on T; applicability rule; tropical refused (`robustness.RIVAL_SYSTEMS`); cert R2P: nakshatra, tithi and orb calendars pass 3/3 with a strong effect. Replaced by two new defects: N-06 (ties now favour the real sky; R2 is not a 5% check) and N-07 (R2 cannot pass for slow yearly calendars). |
| A-02 L2 read as astrology | major | **Partly closed** | "Encoding" wording below L4 works; the level is typed (`TestDefinition.level`), not `levels.level()`. |
| A-03 Text read backwards | major | **Partly closed** | Title rule exists; `reading_differs` is typed. The H11 register check matches "brihat parashara / bphs" only (`schema.py:765`), not Brihat Samhita (N-16). Book check (round 5, `verification.csv`): 37 rows, 32 "close", 5 "not_found" (both Mars-Ketu rules, r002, r011 which contradicts the text, r016); `checked_by` empty in every row, so no rule reaches L1. |
| A-04 Single rule against synthesis | major | **Closed** | Fixed card line; synthesis hash checked at registration. |
| A-05 Day, place, horizon | major | **Partly closed** | Fields required at registration; the limitations box that carries them is never rendered (N-17). No rule is registrable yet. |
| A-06 Currency and market | major | **Partly closed** | Market is a free-text slot; defaults `"simulated series"`, `"XXX"`. |
| A-07 Power asymmetry | major | **Closed** | `support_underpowered` wired; cert W4: 0 missing flags. Gate power ignores detrending loss (N-08). |
| A-08 Disputed direction | major | **Partly closed** | `cmd_register` calls `registration_problems` without the disputes list (`cli.py:237`) and skips every check when `t.rule is None`. |
| A-09 Astrological baselines | major | **Partly closed** | Two rows on the card; baselines are removed only for continuous and log-ratio outcomes (`pipeline.py:650`), so for events and flags the rows are identical. Cert K1, K2 at 400 runs. See N-02 for what baseline removal does to exclusion. |
| A-10 Blind attestation | minor | **Partly closed** | `levels._l4_review` is right; the pipeline never passes `attested_after`, so every L4 card says "attested before the result" (N-15). |

### 1.3 Bias for astrology

| Id | Sev. | Status | Evidence |
|---|---|---|---|
| F-01 Season | major | **Partly closed** | `stats/season.py` same-season windows, whole-year shifts, leave-year-out anomalies. Cert Z5 (Sun in sign Untestable, no outcome read) and Z4 full (old design 31.5%). Z1, Z2, Z6 only at 400 runs; Z2 Mercury retrograde R2 116/2,000 (bound 6.7%, above the 0.06 mark). |
| F-02 Physical proxies | major | **Partly closed** | Nodal (six harmonics) and solar baselines in code; the monsoon plan fails validation; sunspot series pending; `nino34_long` not pinned; the adapter supplies neither term (sub-review). |
| F-03 Source after the data | major | **Partly closed** | Verdict row correct (probe); `source_published` is typed, not read from the rule. |
| F-04 Encoder knows history | major | **Partly closed** | Registration refuses a project-fixed choice with no alternatives; cells are built by the caller; commit order not checked. |
| F-05 Seen confirm periods | major | **Partly closed** | Eligibility blocks S and C on `seen` vintages (`family.py:785-793`); `seen` and `never_opened` are typed in the vintage (N-03 a); the validator's seen rules cover monthly gold and silver only. |
| F-06 Fishing across outcomes | major | **Partly closed** | Quote or `project_extension` required at registration; the quote is not verified; card flags are typed. |
| F-07 Near-copy cells | minor | **Closed** | R3 counts cells that change at least 5% of active bars. Side effect: N-18. |

### 1.4 Data

| Id | Sev. | Status | Evidence |
|---|---|---|---|
| D-01 Monthly averages | major | **Partly closed** | `metals.month_active`, guard 1; cert D1 at 400 runs (4.0% to 4.75%). The guard is not bound to `TestDefinition.guard_bars`; nothing restricts monthly tests to month-horizon principles. |
| D-02 DEM to USD | major | **Closed** (by scope) | Outcome is `gold_dem_frankfurt`; daily USD declared Untestable. |
| D-03 Earthquake catalogue | major | **Open** | (a) region still hand-digitised; (b), (c) listed open in the register; (d) ETAS pending and the domain is not marked limit-only in code; (e) fallback removed, but `snapshot=` bypasses the pin and the pinned file is not byte-verified (N-21); (f) no decade strata. |
| D-04 Hash-only data | major | **Open** | 16 of 16 index entries `committed: false`, none with `deposit_doi` or `owner_archive`; `deposit_problems()` has no caller; every licence `verified: false` (H4). |
| D-05 Hand-set grades | major | **Partly closed** | Register exists; `grades=`, `licences=`, `index=` constructor arguments still replace it. |
| D-06 Rainfall and flood | major | **Partly closed** | Leave-year-out functions correct; the plan's primary outcome is the non-leave-out anomaly (harmless for block contrasts); `epoch_31y` crosses the split. |
| D-07 Frankfurt details | minor | **Partly closed** | Fixing time is a code setting, not in the plan; long-gap returns flagged, not dropped (N-20). |
| D-08 `check_stale` | minor | **Closed** | `check_paper_keys.py:161-172`. |
| D-09 Festival spot-check | minor | **Partly closed** | Festival terms blocked while `festival_spotcheck.yaml` has no rows; owner step open. |

### 1.5 Governance and other

| Id | Sev. | Status | Evidence |
|---|---|---|---|
| G-01 Pipeline and calibration absent | critical | **Partly closed** | `core/validity/pipeline.py` and the WP-98 harness exist and run. No valid certificate: N-01. Checked here: `check_certificate` raises "certified code changed since calibration: pipeline.py, sentences.py, verdict.py" for every outcome type. No bindings to real data: N-05. |
| G-02 Seal and environment | major | **Closed** (code) | `SealedRun` refuses a mismatched environment (`seal.py:635-657`), records files read, refuses untracked reads. The environment itself fails: N-12. |
| G-03 Module collision | major | **Closed** | `load_study_modules(namespace=...)`, `earthquake.py:47-61`. |
| G-04 `use:` pin | major | **Closed** | `family._pin_parents`; `check_against_rules` at `pipeline.py:592`. |
| G-05 Fix after confirm | major | **Open** | `flag.recomputed_after_confirm` exists only as a sentence; nothing sets it; there is no "recompute once" path, only `ReproductionError`. |
| G-06 Random streams | major | **Closed** | `family.stream_rng(plan seed, test id, purpose)`; cert F6. |
| G-07 Two schemes | major | **Closed** | `domains/mundane.py` returns U only; no mapping. |
| G-08 Report gate | major | **Partly closed** | M5 fixed; allow-list exists. The gate checks a page against a manifest it has just written itself (N-13); free prose passes slots (N-14); `--no-provenance` still exists for papers. |
| G-09 Levels from typed flags | major | **Partly closed** | Fixture numbers and `agrees: true` checked; L1 still rests on typed `checked_by`; `review_proof_from_commit` takes the author identity from the caller. |
| G-10 Old pre-registration header | minor | **Open** | `studies/earthquake/hypothesis.yaml:1-13` unchanged. |
| G-11 Unbounded X | minor | **Closed** | `unbounded: true`; `paperkit/results.py:53-76`. |
| G-12 Budget exhaustion | minor | **Closed** | No budget M. |
| G-13 Global ayanamsa mode | minor | **Closed** | `ThreadStartedError` in `SealedRun`; harness test. |
| G-14 Uncommitted tree | minor | **Partly closed** | The four files are tracked. The tree is dirty again today (N-27). |
| O-01 "Valid" against channels | major | **Closed** (render) | Two columns; `known_channel` is typed. |
| O-02 Not a sample of astrology | major | **Partly closed** | Frame table first; its counts come from `DomainRun.sampling_frame`, default zeros. |
| O-03 Site shows 2000 to 2026 | minor | **Partly closed** | As F-05. |
| O-04 Undetectable control | minor | **Open** | W3 (planted recovery on real noise) is implemented nowhere; `control_not_detected` is a typed boolean, default False. |

### 1.6 Code audit of 2026-11-22

M1 closed (`seal.py:124-148`; ledger committed in the confirm). M2 **open** (`studies/mundane/artifacts/results.json` still reads provisional, no commit, no data hash). M3 closed. M4 partly (N-03 c). M5 closed. M6 closed. m3, m4, m10 closed (read here: `aggregate.py:541-543`, `speccurve.py:141`, `registry.py:345-360`). m6, m8 closed; m7 accepted (docstring). m9 partly (hash recomputed from the file, but any freshly written gate passes and the gate is not compared with the bundle). m11 closed. m1, m2, m5 fixed by commit `9d5566d` per its diff; not re-probed.

---

## 2. The loopholes the brief named

| Question | Answer | Where |
|---|---|---|
| A1/A2 one-sided blocks under drift | Sound for continuous outcomes in the probe: alternating sides cancel a trend. No detrending, monthly-style grid, 1,500 runs, 30 cells (linear, random-walk, AR 0.9, drifting-volatility lognormal, exponential trend): 4.3% to 6.5%; three cells at 6.0% to 6.5% deserve a full cell. Not shown: events and flags with a rate trend; forced (edge) one-sided blocks; anything at full size except one cell (B2 exponential daily eclipse 484/10,000). | N-09 |
| Detrending window as a forking path | Yes. Not a plan key, not in the seal bundle; a caller argument. Picking the best of five windows gives 6.0% (single-day) and 9.6% (20-day episodes). A short window removes most of a real effect (kept share 0.27 at 11 bars, 0.73 at 31 bars, 20-day episodes) and the gate does not see it. | N-08 |
| Placebo overlap 0.5 | Outcome-free, so not a leak. But it was tuned on the calibration simulators after failures, is a module constant, and discards the skies most like the real one. Net effect measured by the authors: 5.26% (0.5) against 5.61% (0.25) on one cell. | N-06 |
| Minimum 19 distinct placebos | At exactly 19, R2 passes in 9.9% of null runs (139/1,400, Jupiter-in-water, yearly rainfall); with 106 distinct it still passes in 9.3% (37/400), so the count is not the cure. Below 19 (15 and 18 found), R2 can never pass and S is impossible while the gate says "can support". | N-06, N-07 |
| Alpha schedule 0.04 x 0.2^(b-1) | Valid, but batch 2 onward is close to unreachable on past data. One-sided sign-flip needs K >= 9 blocks at n_b = 20 in batch 1, 12 in batch 2, 14 in batch 3, 16 in batch 4, 19 in batch 5, all inside a fresh confirm period. | N-19 |
| Lineage keys | Lineage id = SHA-256(rule id, calendar hash). A renamed copy has a new lineage id; refusal is by exact calendar hash inside one lock file and one outcome name. One changed bar, another grid, another merge gap, another domain or another lock file all pass. | N-03 |
| OpenTimestamps stub | A stub that raises, with no skip flag: safe. But `seal_domain` commits and pushes `batch_close` before the stamp, so a seal today closes the batch for good without a proof. Attestation time is never compared with the confirm commit. | N-10, N-24 |
| Environment lock mismatch | Installed `.venv` differs from `ops/requirements.lock.txt` in 18+ packages (numpy 2.5.5 against 2.5.4, astropy, pyyaml; sub-review). A sealed run would refuse. The certificate stores the lock hash only, so it asserts an environment it was not produced in. | N-12 |
| Certificate staleness | Confirmed and worse than staleness: old results are stamped with new code hashes. | N-01 |

---

## 3. New findings

### Critical

**N-01. The calibration certificate does not certify the current code.** (G-01, E2)
- Mechanism: `tests/test_validity_calibration.py:1475` `plan_jobs` skips every chunk already in the work directory; `:1563` `aggregate` sums every finished chunk whatever code produced it; `:1656` `write_certificate` hashes the code at write time. A chunk file holds no code hash.
- Evidence 1: against the first certificate (commit `220492f`, before the fixes) 487 of 504 cells have identical counts, including all 136 fast R2N cells, although `blocks.py`, `exclusion.py`, `pipeline.py` and `robustness.py` changed and the R2 rule was rewritten. Only 17 cells moved (eight zero-inflated B2 and R2N cells, three W1 cells, six Z3 cells).
- Evidence 2: seven cells re-run here on current code through the same harness and seeds (400 runs each). Six differ; the seventh (D1) is identical, as expected for a path the fixes did not touch:

| Cell | Certificate | Current code |
|---|---|---|
| Z3 Saturn-in-fire rainfall, R2 passes / S | 31 / 3 | 0 / 0 (insufficient placebos in 400 of 400) |
| Z3 Rahu-in-dual drought, R2 passes | 26 | 0 (insufficient placebos in 400 of 400) |
| Z3 Jupiter-in-water rainfall, R2 passes / S | 30 / 3 | 44 / 7; over 1,400 runs 139 (9.9%) / 12 (0.9%) |
| B1 normal 5/6 K=18, rejections / R2N | 15 / 5 | 17 / 23 |
| B1 normal 20/21 K=18, rejections / R2N | 23 / 19 | 23 / 37 (R2 passes in 9.3% of null runs) |
| B2 lognormal 5/50 K=18, rejections / R2N | 24 / 9 | 25 / 18 |
| D1 monthly averages K=12, rejections | 19 | 19 |

  A re-run of a cell that was redone after the fix agrees with the certificate (W1 normal: 195/200 against 972/1,000).
- Evidence 3: 427 of 504 cells are fast subsets; `case_passed` is true for all 39 cases. 28 fast cells show 6.0% to 7.75%.
- Evidence 4: the certificate is older than HEAD for `pipeline.py`, `sentences.py`, `verdict.py` (commits `ab750fd`, `b86f5ea`).
- Evidence 5: on current code the Z3 Jupiter-in-water "R2 passes" cell fails its own mark conclusively (139/1,400; lower 95% bound about 8.6% against 0.06), and R2N for B1 20/21 K=18 stands at 37/400 (lower bound about 7%). The commit that says it "closes the three calibration failures" raised the R2 pass rate in cells it did not re-run; the certificate still shows their old counts.
- What saves the day: `check_certificate` refuses fast cells and changed files, so no handle can be issued on this file. What does not: a later `--full` run in the same work directory would have added 9,600 new runs to 400 old ones and stamped the sum.
- Fix: every chunk file carries the code-hash set and the lock hash; `aggregate` refuses a mix; the certificate records the commit, the harness file hash, and the installed versions; `make calibrate` starts from an empty work directory. The summary flag `case_passed` must be false for a case with any fast cell.

**N-02. Baseline removal makes exclusion and X95 anti-conservative.** (S-01)
- Where: `pipeline.py:650` regresses the outcome on the baselines alone (`season.py:711` `remove_baselines`), then `:680` removes the full effect r from the residual. When the calendar correlates with a baseline, the regression has already absorbed a share of a real effect roughly equal to `baseline_r2`. Removing r then over-removes. The detrending step has exactly this correction (`effect_shape`, `:658`); the baseline step does not.
- Measured (repository functions unchanged; outcome = r x calendar + Normal noise; baseline = mix x calendar + noise, with no effect of its own; true effect = SESOI = r; 600 runs per cell):

| Calendar | Mean `baseline_r2` | R4 | False "excluded" at SESOI | X95 below the true effect | Support power |
|---|---|---|---|---|---|
| 5/50, K=12 | 0.00 | pass | 5.5% | 5.5% | 99% |
| 5/50, K=12 | 0.14 | pass | 13.5% | 13.5% | 98% |
| 5/50, K=12 | 0.29 | pass | 33.2% | 33.2% | 88% |
| 5/50, K=12 | 0.39 | pass | 46.3% | 46.3% | 80% |
| 20/21, K=12 | 0.34 | pass | 39.2% | 39.2% | 88% |
| 20/21, K=12 | 0.57 | fail | 82.7% | 82.7% | 54% |

- Who is hit: exactly the principles the baselines were added for. Tithi rules against the festival baseline, node and Jupiter rules against the nodal and solar terms, anything against ENSO. The error is against the principle (false "excluded", X too small, support power lost) and it is of the same size as the S-01 failure the first audit measured.
- No calibration case covers it: X cases have no correlated baseline; K1 measures S only.
- Fix: residualise the calendar indicator on the same baselines (and detrend it) and pass that as the effect shape, so removal subtracts what the residual outcome carries; or put the calendar in the regression. Add an X case with `baseline_r2` 0.1, 0.3, 0.45. Until then no E and no X for a test with `baseline_r2` above about 0.02.

**N-03. Four ways to confirm twice.** (S-04, S-05; sub-review probes, run end to end with the repository's fake timestamp client)
- (a) `family.py:697` (verified by reading): the fresh-data rule is skipped when the vintage says `never_opened: true`, a flag the owner writes. Batch 2 closed on `{id: "v1-reissue"}` with the same period and got S-eligibility at 0.008.
- (b) A new domain string is a new lock, a new 0.04 and a new ledger key on the same data and calendar.
- (c) A renamed rule in its own lock or folder gets a second handle; duplicate search is per lock file.
- (d) The ledger entry is committed but not pushed or timestamped; `git reset --hard HEAD~1` re-opens the confirm with the same proof file.
- Also: a one-bar change to a calendar is a new lineage (expected), and with (a) it is confirmable on the old holdout.
- Fix: one ledger and one alpha budget keyed on (dataset hash, confirm period, calendar hash, outcome) across all domains and locks; "seen" derived from the ledger, never from the plan; any later confirm period that overlaps an earlier one refused whatever the flag; the ledger commit pushed and checked on the remote before the handle is returned; a committed list of domains.

**N-04. The calibration gate can be skipped.** (G-01; verified by reading)
- `sealbundle.py:669`: `for ot in bundle.get("outcome_types") or [None]`. With an empty list, `check_certificate(..., None)` checks hashes only (`calibration.py:408` onward), not that any case exists, passed, or ran at full size. The list is supplied by the caller at seal time; the pipeline never compares a test's outcome type with the bundle. The bypass-test fixture confirms with a certificate that holds zero cases.
- Fix: derive the outcome types from the batch's tests in the lock; refuse an empty list; refuse a test whose type is not in the list.

**N-05. No binding from plan and rule to run; verdict inputs are typed.** (G-01, S-12, S-13, E6, E7; latent until bindings exist)
- `cli.py:104`: "the rule-to-test expansion is not built yet". `TestDefinition` and `DomainRun` (`pipeline.py:164-244`) take as plain values: level, SESOI, x-grid, source date, disputed flag, known channel, reading flag, project-extension flag, market, sensitivity cells, placebo kinds, plan seed, plan hash, vintage (with `seen`, `never_opened`), first-look calendars, baselines, missing bars, detrending window, `control_not_detected`, sampling frame. `validate_plan`, `registration_problems(rule, disputes)` and `levels.level()` are called on no run path. The plan's outcome types (`absolute_return`, `event`, `binary`) are not the pipeline's (`log_ratio`, `events`, `flags`) and nothing maps them.
- State of the inputs: 0 domain plans; `sesoi_sources.yaml` empty; 162 rules loaded, all L0, 41 with a `tests` block, 0 registrable under schema 3.1 (158 lack `source.published`).
- Consequence: every guarantee of ADR-008 sections 5 to 9 that says "the plan fixes" or "the register step refuses" holds for the unit under test and for no real run. This is the remaining half of G-01.
- Fix: one function builds `DomainRun` and every `TestDefinition` from `load_plan()` + `Rule` + `levels.level()`; `seal_domain` refuses a plan that fails `validate_plan`; the test definitions are hashed into the lock at registration and the bundle; the pipeline refuses a run whose plan hash is not the bundle's.

### Major

**N-06. R2 is not a 5% check.** Three causes. (i) The real sky beats its placebos too often: 9.9% at m = 19 distinct calendars (Z3 Jupiter-in-water, 1,400 runs) and 9.3% at m = 106 (B1 20/21 K=18, 400 runs; it was 4.8% before the fix); N-01 table. The rank assumes the real sky is exchangeable with its placebos; the overlap rule and the per-cluster weighting break that. (ii) Ties favour the real sky (`robustness.py:447`, strictly larger only): `r2_placebo(1.0, 150 tied + 50 lower)` gives p = 0.005 (sub-review probe); event and flag statistics tie often (cert notes: ties in 2,000 of 2,000 F8 event runs); cert Z2 Mercury retrograde R2 116/2,000. The first audit offered "ties do not count" for identical skies; it was applied to all ties. (iii) 0.5 and 19 (`robustness.py:164`, `:166`) are module constants chosen from simulator results after failures. R2 cannot create an S by itself (S also needs `p_sup <= a_test`), which is why this is major and not critical; but R2 was the guard for the cases where `p_sup` is wrong. Fix: mid-rank ties for skies that differ from the real one; calibrate R2 per grid type at full size; require m well above 19 (for example 99) or drop the 0.05 mark in favour of a reported rank.

**N-07. R2 cannot pass for slow calendars on yearly grids, and the gate says "can support".** Saturn-in-fire: 18 distinct placebo calendars in 400 of 400 runs; Rahu-in-dual: 15. Status `insufficient_placebos`, S impossible, `gate.can_support = True` in every run. Cause: day offsets are capped at 3,650 days (`robustness.py:161`), so a yearly grid sees at most about 20 shifts, fewer after the overlap rule. The certificate records these cells as passing because 0 of 10,000 null runs pass R2; power is also 0, and W1 has no yearly cell. This is A-01 in a new form: a class of principles (monsoon, slow planets) that cannot be supported by construction. Fix: offsets up to 100 years on yearly grids; the gate computes the distinct-placebo count (it is outcome-free) and reports "limit only"; a W1 cell per grid type.

**N-08. The detrending window is a free parameter.** Not in `plan.REQUIRED_KEYS`, not in the seal bundle; only in `input_sha256`. `_check_detrending` (`pipeline.py:430`) accepts any positive contrast; 0.07 was accepted in a probe (sub-review). Measured here on a daily grid, no effect, 500 runs: each of five windows holds 4.4% to 5.4%; the best of five gives 6.0% (single-day episodes) and 9.6% (20-day episodes). Kept share of a steady effect for 20-day episodes: 0.27 (11 bars), 0.73 (31), 1.00 (61 and above). The gate's power ignores this, so `support_underpowered` can be missing where support is in fact out of reach. Fix: `detrend_window` as a required plan key per dataset, in the bundle; a floor (kept share at least 0.8 for every used block, else Untestable); gate power computed with the shape; two other windows as declared sensitivity cells.

**N-09 (minor, listed here for the brief). A2 under trend.** See section 2. Events and flags are never detrended and no drift cell exists for them; the amendment's own condition ("B1, B2, B3, X1, X2 at full size for daily-event calendars, and a drift case") is met by one full cell.

**N-10. Seal and confirm are not atomic.** (i) `seal_domain` commits and pushes `batch_close` before calling the timestamp client; with the stub that is a closed batch with no proof and no retry. (ii) `issue_confirm_handle` writes and commits the ledger before `SealedRun` checks the environment, which fails today. (iii) Verified here: `run_domain` with `previous` set to a results file of the same inputs from a provisional run raises `ReproductionError` (`pipeline.py` record loop) after the confirm rows were read; `tests outside the handle's batch` (`pipeline.py:876`) is another such stop. In each case the one-shot holdout is spent and no result exists; the tempting repair is a manual second run. Fix: every check that can fail runs before the ledger write; a stopped confirm leaves a ledger entry `aborted` with the reason and a defined, logged, one-time resume.

**N-11. Run integrity after the seal.** `--bindings` may supply its own `sealer`, replacing `SealedRun` (clean tree, environment, files read) (`cli.py:130, 214`). The bundle commit need only be an ancestor of HEAD (`sealbundle.py:521`), so rule-evaluation, ephemeris and markets code can change after sealing; only calendar hashes are re-checked. The run's gate files and `plan_sha256` are not compared with the bundle's. Fix: `SealedRun` hard-wired on the confirm path; HEAD = bundle commit plus the confirm commits only; gate and plan hashes compared.

**N-12. Environment.** The installed environment is not the locked one; the certificate was produced in it and records only the lock hash; the Python version is recorded and not enforced. Fix: sync and re-lock; certificate stores installed versions and refuses to be written when they differ from the lock.

**N-13. The report gate authenticates nothing.** (G-08) `cli._report_run` writes the report and its manifest, then checks the report against that manifest. Sub-review probe: an N record edited to L4 "Supported", renamed, with a fake commit, re-rendered and passed. Fix: check `results.json` against `lock.verify_batch_results` and the run stamp; re-derive each verdict from the stored numbers with `verdict()`.

**N-14. Free prose passes the sentence allow-list.** The name, source and channel slots accept free text (pattern `[A-Z][A-Za-z0-9 .,'()-]{0,79}`); a probe rendered "Project hypothesis derived from Astrology proven true by this study". Fix: slot values from rule ids and a closed vocabulary only.

**N-15. L4 "attested before the result" is printed for every L4 card** because the pipeline never passes `attested_after`; any non-empty `outside_reference` gives L4 with no date (A-10).

**N-16. The H11 page check targets BPHS, not Brihat Samhita** (`schema.py:765`), so the rules the first audit named (A-03) are not held to it.

**N-17. The limitations box is computed and never rendered** (`render_card` does not print `limitations`). ADR-007's third deliverable per principle is missing from every card.

**N-18. R3 passes with no evidence.** With no distinct sensitivity cell, including the default empty grid, R3 is "not applicable" and counts as passed (`robustness.py:310` onward). Fix: an S needs at least one distinct declared cell, or R3 is shown as "not run" and S carries a flag.

**N-19. Alpha schedule and owner log.** The schedule is valid (sum 0.05) but 80% of it is spent in batch 1, and later batches need both fresh data and 12 to 19 blocks inside the fresh period (table in appendix A.6). For past-only research this means "first batch or never", which invites padding batch 1 (and every added test lowers `a_test` for all). H18, H19, H20 are not in OWNER_DECISIONS.md at all; H16, L2, Support remain defaults. Fix: owner decides H20 with the reachability table per domain in view; consider a flatter ratio (0.5) with a smaller first share.

**N-20. Metals: returns over long gaps stay in the outcome.** `long_gap` is flagged, never masked; Easter closures (tied to the full moon) span about five days. Fix: declare those bars in `missing_bars`.

**N-21. Earthquake and grades.** `snapshot=` bypasses the pin; the pinned file is not hash-verified on read; `catalogue()` and `mainshock_flags()` are public; grade inputs can still be passed to the adapter constructor (D-03, D-05).

### Minor

- **N-22.** The centred detrend crosses the explore/confirm split, so explore numbers differ between a provisional and a confirm run.
- **N-23.** The certificate has no commit id and does not hash the harness (`tests/test_validity_calibration.py`), where the scenarios live.
- **N-24.** The timestamp's attestation time is never compared with the confirm commit time; the legacy-reader check is a substring marker and exists for listed domains only; any file named `confirm_ledger.jsonl` counts as clean when modified (`seal.py:124-126`).
- **N-25.** An E card with an unbounded X-strict prints "excluded above 0.1" beside "There is no family-level bound".
- **N-26.** A confirm handle is an entry in a module dictionary (`sealbundle._ISSUED`; the harness writes it directly, `test_validity_calibration.py:831`). In-process forgery cannot be prevented; say so in the methods page and rely on the outside timestamp, which an outsider can check.
- **N-27.** Working tree: 8 modified `site/data/*.json`, untracked `.cursor/` and `docs/CONTEXT7.md`. **`docs/CONTEXT7.md` contains what looks like a live API key (two occurrences). Do not commit it; remove or ignore the file and rotate the key.** Every sealed run refuses until the tree is clean.
- **N-28.** "Contradicted" under no effect was not a certificate metric for Z cells. Seen here at `a_test` = 0.04: 57/1,400 (4.1%), 16/400, 5/400, 18/400. Consistent with nominal; add the metric.

---

## 4. Exit criteria

| # | Criterion (short) | Status | Why |
|---|---|---|---|
| E1 | No critical open; majors closed or owner-accepted on cards | **Not met** | 4 first-audit criticals partly closed; 5 new criticals; 26 first-audit majors not closed; 15 new majors; no owner acceptance recorded. |
| E2 | Full-pipeline calibration at nominal size | **Not met** | 65 of 504 cells at full size, 17 of them from the current code; the rest fast or from pre-fix code (N-01); two R2 cells fail on current code; missing cases: correlated baselines (N-02), events/flags drift, X-strict family coverage, C in Z cells, yearly and daily power. |
| E3 | Power and planted recovery | **Not met** | W1 passes on three periodic cells (0.908 to 0.972 of 1,000; 195/200 re-run). W3 is not implemented; no power cell on yearly or daily real calendars; power is 0 where R2 cannot pass (N-07). |
| E4 | Sequential rule, bit-identical numbers, clone scenario | **Not met** | F1, F2, F5, F6, F7 hold. F3 and F4 at 400 of 2,000 families. The clone scenario is beaten by `never_opened` and by a new domain (N-03). |
| E5 | Keyed ledger, bypass tests, outside deposit | **Not met; partly blocked on owner (H19)** | Four bypasses (N-03); P4, P5 on a fake adapter; timestamp client not wired; no deposit reference can exist. |
| E6 | Sealed plans, owner sign-off | **Not met; blocked on owner (H16, H18, H20, L2, Support, H17) and on design task D11** | No plan exists; the validator is off the run path; SESOI table empty. |
| E7 | Schema and verdict rules enforced | **Not met** | Schema 3.1 and the verdict table exist and test green; the register step and the verdict take typed inputs (N-05); 0 registrable rules. |
| E8 | Data | **Not met; blocked on owner (H4, deposits, H11, festival almanac dates)** | No licence read; nothing deposited; pins bypassable; D-03 open. |
| E9 | Seal stamp, clean tree | **Not met** | Stamp built and refusing correctly; tree dirty; environment not the locked one. |
| E10 | Report gate | **Not met** | Self-written manifest (N-13); free prose in slots (N-14); limitations not rendered (N-17); no cross-domain summary. |
| E11 | Second audit finds no new critical or major | **Not met** | This pass: 5 critical, 15 major. No clean-clone `make calibrate` was run. A third pass is needed after the fixes. |

## 5. Counts and confidence

**Remaining.** Critical: 9 entries (S-01, S-04, S-05, G-01 partly closed; N-01 to N-05 new). They are five distinct problems: N-01 and N-04 are why G-01 stays open, N-03 is why S-04 and S-05 stay open, N-02 is why S-01 stays open, N-05 is new ground. Major: 41 entries (26 from the first audit, 15 new). Minor: 16 open or partly closed (8 from the first audit, 8 new including N-09), plus S-14 accepted.

**What can be trusted today.**
- The block design: no bar is shared; the support test holds 5% on i.i.d., skewed, AR and trending continuous bars in every probe here, including A2 one-sided blocks.
- Exclusion by effect removal **without baselines** on continuous outcomes: about 5% on normal, exponential and lognormal bars; conservative on rare events.
- Fixed thresholds, per-test seeds, the eligibility table as a function.
- The certificate checker and the sealed-run checks refuse when they should. Today they refuse everything.
- The project's own record of its limits: failed cells were written as failed in the first certificate; fast cells are marked; the stub says it is a stub.

**What cannot be trusted yet.**
- Any statement that the pipeline "passed calibration". It has not, at the size and on the code ADR-008 requires; two R2 cells fail now.
- Any "effect excluded" or X on a test with baselines (N-02), and any X on events or flags beyond 400 runs of evidence.
- R2 as a safeguard (N-06), and "can support" from the gate for yearly slow-planet tests (N-07) or short detrending windows (N-08).
- The holdout: it is protected against accident, not against the four routes in N-03.
- Anything that depends on a plan or a rule file being enforced (N-05): levels, SESOI, source dates, disputes, seen data, channels, limitations.
- Any report page as evidence of what the run produced (N-13).

**Honest position.** The design of ADR-008 is right in its main lines and the hardest statistical part (S-01, S-02, S-03) is largely built. The work is perhaps two thirds of the way to a first sealed run: the pieces exist and test green one by one, and they are not yet joined into a path that an outsider could not bend. Every number produced on real data before E1 to E11 hold is provisional and should be labelled so. Suggested order: N-02 and N-06/N-07 (method), then N-05 (bindings, which closes most "partly closed" rows at once), then N-03/N-04/N-10/N-11 (holdout), then a clean full calibration (N-01, N-12) and a third audit.

---

## Appendix A. What was run

Scripts were kept outside the repository (session scratchpad). All use the repository's functions unchanged. Seeds fixed. "Bound" = upper one-sided 95% Clopper-Pearson.

**A.1 First audit's A.1 on the new exclusion** (`build_blocks` on a 5/50 calendar, effect 0.5 planted in the active bars, `exclusion(..., sesoi=0.5)`, no baselines, 1,500 runs):

| Noise | K = 10 | K = 13 | Old function (first audit; cert X8) |
|---|---|---|---|
| Normal | 0.055 | 0.043 | 0.060 / 0.045 |
| Exponential - 1 | 0.043 | 0.049 | 0.136 / 0.129; 0.127 |
| Lognormal - mean | 0.060 (bound 0.071) | 0.041 | 0.217 / 0.163; 0.210 |
| Rare event | 0.013 (28% unbounded) | 0.032 (7% unbounded) | 0.355 / 0.228; 0.349 |

**A.2 First audit's A.2 on the new blocks** (i.i.d. Normal, one-sided 5%, 4,000 runs):

| Active / gap | Used blocks | Rejection rate | Old function |
|---|---|---|---|
| 5 / 5 (K = 12, 18) | 2 of 12, 2 of 18 | Untestable in the gate | 0.081, 0.077 |
| 20 / 5 | 0 | Untestable | 0.099 |
| 5 / 50 | 12 | 0.053 | 0.051 |
| 5 / 6 | 12 | 0.051 | - |
| 5 / 10 | 12 | 0.047 | - |
| 1 / 3 (A2, 24 one-sided) | 24 | 0.052 | - |
| 1 / 2 (A2, 30 one-sided) | 30 | 0.054 (bound 0.0605) | - |

**A.3 Certificate cells re-run through `run_domain`** (harness `Ctx`, `run_once`, seeds as the harness): table in N-01. Also Z3 Jupiter-in-water runs 400 to 1,399: R2 passes 46 and 49 per 500; S 4 and 1; C 20 and 13; `n_distinct` = 19 in every run.

**A.4 Baseline absorption:** table in N-02.

**A.5 Trend without detrending, alternating one-sided blocks** (24 blocks, Monte Carlo sign-flip, 1,500 runs, both sides):

| Calendar | Linear | Random walk | AR 0.9 | Drifting-volatility lognormal | Exponential trend x exponential |
|---|---|---|---|---|---|
| 1/3 (one-sided) | 0.050 / 0.051 | 0.043 / 0.049 | 0.049 / 0.065 | 0.053 / 0.045 | 0.050 / 0.049 |
| 1/5 (one-sided) | 0.061 / 0.045 | 0.045 / 0.060 | 0.051 / 0.054 | 0.055 / 0.058 | 0.047 / 0.049 |
| 2/2 (two-sided) | 0.062 / 0.044 | 0.047 / 0.049 | 0.060 / 0.051 | 0.047 / 0.056 | 0.047 / 0.064 |

Two binomial standard errors at 1,500 runs: about 0.011.

**A.6 Blocks needed to reach `a_test`** (one-sided sign-flip floor 2^-K):

| Batch | alpha_b | n_b = 10 | n_b = 20 | n_b = 40 |
|---|---|---|---|---|
| 1 | 0.04 | 8 | 9 | 10 |
| 2 | 0.008 | 11 | 12 | 13 |
| 3 | 0.0016 | 13 | 14 | 15 |
| 4 | 0.00032 | 15 | 16 | 17 |
| 5 | 0.000064 | 18 | 19 | 20 |

These are floors (every block must agree); useful power needs several more. Two-sided: add one.

**A.7 Detrending window:** numbers in N-08 (calendars 1/28 with 60 blocks and 20/60 with 30 blocks; windows 11, 31, 61, 121, 251 bars; 500 runs).

**A.8 Other checks made here:** `check_certificate` on the committed certificate for `None`, `continuous`, `events` (all refuse: code changed); `git hash-object` of the 46 certified files against the certificate (3 differ) and against commit `220492f` (4 changed between the two certificates); confirm with `previous` = provisional results (`ReproductionError`).

**Not done:** full `make calibrate`; a clean clone; P1 to P9 by hand beyond the sub-review's probes; daily-grid cell re-runs (too slow on the loaded machine); any run on real outcome data.
