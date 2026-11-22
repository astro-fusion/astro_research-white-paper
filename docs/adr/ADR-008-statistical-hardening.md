# ADR-008: Statistical hardening of the validity pipeline

- Status: proposed
- Date: 2026-11-22
- Deciders: repository owner (single developer); architect (design only)
- Amends: [ADR-007](ADR-007-principle-validity-reports.md) sections 3.4, 4.2, 5.1 to 5.4, 7.2, 9 and work packages WP-66, 68, 69, 70, 73, 78, 80, 83. Keeps [ADR-004](ADR-004-paper-production-and-principle-validation.md) D-3 (outside deposit) and D-6 (few episodes).
- Inputs: [STRATEGY_AUDIT_2026-11-22.md](../research/STRATEGY_AUDIT_2026-11-22.md) (7 critical, 38 major, 15 minor; exit criteria E1 to E11), [CODE_AUDIT_2026-11-22.md](../research/CODE_AUDIT_2026-11-22.md), [OWNER_DECISIONS.md](../research/OWNER_DECISIONS.md), the code in `core/stats`, `core/domains`, `core/mundane`, `core/markets/placebo.py`.
- `core/` stands for `libs/vedic_astrology_core/`.
- Scope (owner decision, unchanged): past data only. Nothing here issues, stores or scores a forecast.

## 0. Short answer

Seven decisions close the seven critical findings. Each is one choice, not a menu.

| Id | Decision | Closes |
|---|---|---|
| H-1 | **Balanced disjoint blocks.** Every episode gets its own control bars. No inactive bar serves two episodes. One block-level sign-flip test is the primary p-method for every outcome type. | S-02, S-06, S-08, S-15 |
| H-2 | **Exclusion by effect removal.** To test "the effect is at least r", remove an effect of size r from the active bars, then run the same block test for "no effect" in the other direction. X95 is the smallest r that is rejected. Printed only when enough blocks carry information. | S-01, S-07, S-11 |
| H-3 | **Closed batches with fixed thresholds.** The tests registered before a domain's first confirm on a data vintage form a closed batch. Each test's threshold is alpha_b / n_b, fixed when the batch closes. Benjamini-Yekutieli is dropped. Later batches get a smaller alpha and need unseen data. | S-03, S-04, S-09, S-10, G-12 |
| H-4 | **Seen data cannot support.** "Supported" and "Contradicted" need a confirm period that nobody could see when the test was registered. Tests registered after a batch closes get numbers on that vintage but no S, C or E. | S-04, F-05 |
| H-5 | **One keyed ledger, one seal bundle, one outside timestamp.** A confirm starts only after the hash of the seal bundle has a verified OpenTimestamps proof and has been pushed. | S-05 |
| H-6 | **Calibration certificate.** The whole-pipeline calibration (old WP-70) writes a certificate tied to the hashes of the code it tested. No certificate, or changed code, means no real confirm outcome can be read. | G-01 |
| H-7 | **Words follow the evidence level.** Below L4 every verdict says "encoding". SESOI comes only from the source or from a published yardstick. A null on one encoding is never printed as a null on astrology. | A-02, S-13 |

A-01 (placebo ties) is being fixed in code by the concurrent agent "FIX-code". Section 5 fixes only the contract that code must meet.

**What FIX-code owns and this ADR does not redesign:** code-audit M1 to M6 and m1 to m11; the code parts of S-05 (keyed ledger, lineage search across folders and history, gate hash recomputed from `gate.json`, confirm outcomes only through a handle from `begin_confirm`, ledger path excluded from the dirty check or committed inside `begin_confirm`); A-01 tie rule in `rank_of_real`. Packages below that touch the same files (`stats/seal.py`, `markets/placebo.py`, `domains/base.py`, `tools/check_paper_keys.py`) list "FIX-code merged" as a dependency.

## 1. Block design and the primary test (H-1)

### 1.1 The design

New module `core/stats/blocks.py`. It reads the calendar only, never an outcome, so the gate can run it.

1. **Episodes** as today (`episodes()` with the plan's `merge_gap` for the calendar class).
2. **Control bars.** Each inactive gap between two episodes is cut at its midpoint. The left half belongs to the episode on its left, the right half to the episode on its right. An odd middle bar is dropped. Each episode takes at most `ceil(n_active / 2)` control bars on each side, the ones nearest to it. So no bar is ever in two blocks.
3. **Guard bars.** The plan may set `guard_bars` per dataset (1 for monthly-average prices, section 8; 0 otherwise). That many bars next to the episode are skipped.
4. **Balance.** `balance = n_control / n_active`. A block with balance below **0.5**, or with control bars on one side only when the other side exists, is dropped. Dropped blocks are counted and printed. The decision uses the calendar only.
5. **Season-linked calendars** use same-season control windows in other years instead of neighbours (section 6).
6. **Year unit (monsoon).** The same rule on a yearly grid: a run of active years is compared with the nearest inactive years, each inactive year used once.
7. **Block difference.** `d_k` = mean of the outcome over active bars minus mean over the block's control bars. Event outcomes use counts per unit exposure.
8. **Weights and the estimand.** The test statistic is `T = sum(w_k d_k) / sum(w_k)` with `w_k` = number of active bars used. So T is the pooled difference "all active bars against all matched control bars". **This one number is the estimate on the card, the thing the p-value tests, the thing X95 bounds and the scale of the SESOI.** Event outcomes: pooled rate ratio = active events / control events at equal exposure. This is the S-06 fix.
9. **Effective episodes.** `K_eff = (sum w)^2 / sum(w^2)`. Gate G4 becomes `K_eff >= 8` (was: raw count). One two-year episode can no longer hide seven one-day ones, or the reverse.
10. **Primary test.** Sign-flip of the block differences (exact enumeration up to 2^20 patterns, Monte Carlo above, floors as in `nulls.py`). The side comes from the plan (claimed direction, or two-sided for `either`); there is no default side. The circular-shift test stays as a declared sensitivity cell and can never change a verdict. **The calendar-class routing table of ADR-007 5.2 is deleted** (S-08).

### 1.2 Why this closes S-02, S-06, S-08

- S-02: two block differences share no bar, so under independent bars they are independent. The measured 8% to 10% came only from shared bars.
- Sign-flip is exact when, inside each block, swapping "active" and "control" does not change the joint distribution under no effect. That needs balanced blocks and local exchangeability, not symmetric or normal outcomes. Skewed bars are fine.
- S-06: estimate, p, X and SESOI use the same statistic T.
- S-08: one method fixed here for every outcome type. Nobody chooses a method after seeing simulations or data.

Residual dependence across blocks (volatility clustering, aftershock tails) is not removed by design. Whether it matters is decided by the tests below, not by argument.

### 1.3 Proof test

`tests/test_stats_blocks.py` (fast) and the certificate suite (section 4). No effect planted. One-sided 5%.

| Case | Calendars | Outcome generator | Replications | Pass |
|---|---|---|---|---|
| B1 Appendix A.2 again | Periodic: active/gap 5/5, 20/5, 5/50, 20/20, 60/10; 12 and 18 episodes | i.i.d. Normal | 10,000 | Upper one-sided 95% Clopper-Pearson bound on the rejection rate at or below 0.06 (about 562 rejections or fewer) |
| B2 Skew | same | Lognormal(0, 1); Exponential(1); a bar is 0 with probability 0.98, else Exponential(1) | 10,000 | same |
| B3 Dependence | same, plus real Mercury retrograde, Moon-nakshatra group, tithi and eclipse calendars on the 1968 to 1998 daily grid | GARCH(1,1) with alpha 0.08, beta 0.90; two volatility regimes; AR(1) with 0.1 and 0.3 | 10,000 | same |
| B4 No sharing | every case | - | once | Property test: no bar index appears in two blocks; `sum(n_control)` never exceeds the number of inactive bars |
| B5 Old design fails | 5/5 and 20/5 with the old `episode_differences` | i.i.d. Normal | 10,000 | Rejection rate above 0.07. This test documents the loophole; it must keep failing for the old function |
| B6 Side and drops | hand-built | - | - | The test and the gate report the same side and the same number of used blocks (S-15) |

Fast subset for every pull request: 400 replications, three cases, pass at or below 0.085.

Note on 20/5: with a gap of 5 the half-gap gives 2 control bars a side against 20 active bars, balance 0.2. Those blocks are dropped. Such a calendar is Untestable ("no clean control time"), which is the honest answer.

## 2. Exclusion and X95 (H-2)

### 2.1 The problem in one line

No method can bound the **mean** of an unknown skewed distribution from 8 to 20 values. A bootstrap or studentised interval fails exactly in the rare-event case, where most resamples contain no event. So the fix is not a better interval on the same numbers. It is a test whose validity does not depend on the shape of the distribution.

### 2.2 The method

New module `core/stats/exclusion.py`. To test H0 "the effect is at least r" under the plan's effect model:

| Outcome type | Effect model (printed on the card) | How an effect of size r is removed |
|---|---|---|
| Continuous (returns, rainfall anomaly) | Constant shift in the outcome's unit | Subtract r from every active bar |
| Absolute returns (past-only standardised) | Constant ratio, tested on the log scale with the plan's floor | Subtract log r from every active bar |
| Events (mainshocks, floods) | Constant rate ratio | Keep each active-side event with probability 1/r (thinning). Unequal exposure is first equalised by thinning the longer side |
| Yes or no per bar or year (extreme move, drought year) | Constant risk ratio | Keep each active-side "yes" with probability 1/r |

Then run the block sign-flip test of section 1 on the adjusted data, one-sided, alternative "active below control". Its p-value is the exclusion p-value. If the true effect is exactly r and constant, the adjusted data have no effect, so the test is exact for the same reason the support test is exact. Skew and rare events do not enter.

Details that make it one deterministic procedure:

- **Thinning is repeated 199 times.** Each event gets one uniform number per repetition, from the test's own seed (section 3.5). An event is kept at ratio r when its number is below 1/r, so the kept sets are nested as r grows. The reported p is **twice the median** of the 199 p-values, capped at 1. Twice the median of p-values is valid under any dependence between them (Meinshausen, Meier and Buehlmann 2009, quantile aggregation at one half). It is conservative. That costs exclusion power, never validity.
- **X95** is the smallest r whose exclusion p is at or below 0.05, found on a grid fixed in the plan (bisection between grid points). **X-strict** is the same at the test's family threshold (section 3).
- **Two-sided intervals** on cards are the pair of one-sided limits from this inversion. The exact binomial rate-ratio interval is removed from cards (S-07). `rates.py` keeps the function with a corrected docstring: "assumes independent events; too narrow for clustered events; not used for any verdict".
- **Minimum-information rule.** Let I be the number of blocks whose difference is not zero after adjustment at r = SESOI. A limit at level a is printed only if `K_eff >= 8` and `I >= ceil(log2(1/a))` (5 for X95; 10 at a threshold of 0.001). Otherwise the record has `unbounded: true` and no number (G-11), and verdict E is impossible. The gate predicts I from the plan's base rate and reports "can limit: no" in advance.
- **Counting unit for events.** The plan names it per domain: declustered mainshock (earthquake); flood events of one basin merged within 14 days (flood). Thinning acts on that unit.

### 2.3 What stays outside any guarantee, and how the card says it

The guarantee is for a **steady** effect (every episode shifted by the same amount or ratio). An effect that appears strongly in a few episodes and not at all in the rest can be missed by any method with few episodes. Every card with an X prints two fixed lines:

- "Ruled out: a steady effect of X or more in every episode."
- "Not addressed: an effect that appears in fewer than f of the episodes." with `f = 1 - 0.05^(1/K)` (K = 8: 31%; K = 12: 22%; K = 20: 14%).

Verdict E reads "A steady effect at or above the project's threshold is ruled out", never "of the claimed size" (A-07).

### 2.4 Proof test

`tests/test_stats_exclusion.py` and the certificate suite. Effects are planted in the **bars**, then the full block and exclusion code runs. 10,000 replications per cell; K = 8, 12, 20 used blocks; pass = upper one-sided 95% Clopper-Pearson bound at or below 0.06.

| Case | Generator | Planted effect | Measured | Pass |
|---|---|---|---|---|
| X1 Gaussian, heavy tails | Normal; Student-t with 3 degrees of freedom | SESOI, constant | False "excluded" rate at r = SESOI | bound <= 0.06 |
| X2 Right skew | Lognormal(0, 1); Exponential(1) | SESOI, constant | same | bound <= 0.06 |
| X3 Rare events | Poisson events, mean 0.1, 0.5 and 2 events per active window | rate ratio = SESOI (2.0 and 1.5) | same | bound <= 0.06. At mean 0.1 the expected result is "unbounded" in most runs; an "excluded" there counts as a failure |
| X4 Clustered events | Neyman-Scott: Poisson parents, geometric offspring with mean 3, offspring delay Exponential(10 bars); background rate doubling over the record; run through the pipeline's declustering | rate ratio on parents = SESOI | same | bound <= 0.06 |
| X5 Rare yes/no | Flags with base rate 5% taken from a GARCH series (so they cluster); drought-year flags at 15% on the yearly generator | risk ratio = SESOI | same | bound <= 0.06 |
| X6 Coverage | X1 to X5 | true effect 0, half SESOI, SESOI, twice SESOI | Share of runs with X95 below the true effect | bound <= 0.06 at every value |
| X7 Balance edge | X2 and X3 with block balance 0.5, 0.75, 1.0 | SESOI | False "excluded" | bound <= 0.06. If 0.5 fails, the balance floor in section 1.1 is raised by amending this ADR, before any real run |
| X8 Old method fails | `episode_equivalence` on Appendix A.1 inputs | SESOI | False "excluded" | above 0.10 for the three skewed rows (keeps the loophole documented) |
| X9 Uneven effect (reported, not a gate) | X2, X3 with the whole effect in 20% of episodes | mean = SESOI | False "excluded" | The rate is stored in the certificate and shown on the methods page next to the "Not addressed" line. No pass mark, because no method can pass it |
| X10 Monotone | all | - | exclusion p as r grows over the grid | never increases (property test) |

Until X1 to X7 pass for an outcome type, the pipeline prints neither E nor any X for that type.

## 3. Multiplicity over time and holdout reuse (H-3, H-4)

### 3.1 The choice

Considered and rejected: online FDR (LOND, LORD). Its thresholds are fixed at test time, which would solve S-03. But it assumes each new p-value is valid given the past. A test designed after the confirm period is public breaks that, so it does not solve S-04. Only unseen data solves S-04. Chosen:

**Closed registration batches, a fixed per-test threshold, alpha spent across batches, and fresh data for every batch after the first.**

### 3.2 Rules

1. **Vintage.** A data vintage is one (dataset hash, confirm period). The plan lists its vintages.
2. **Batch.** Tests are registered into the open batch of a domain. A batch is closed by a ledger entry `batch_close` that records the test ids, n_b (their number), alpha_b and the seal bundle hash (section 4.2). **Closing happens before any confirm outcome of that vintage is read, and all tests of the batch are confirmed in one run.**
3. **Alpha spending.** Batch b of a domain gets `alpha_b = 0.04 x 0.2^(b-1)`: 0.04, 0.008, 0.0016, ... The sum over all batches, for ever, is 0.05.
4. **Fixed threshold.** Every test in batch b is judged at `a_test = alpha_b / n_b` (Bonferroni). It is stored in the test's record at batch close and never recomputed. Support, opposite-direction and exclusion p-values each use a_test. Benjamini-Yekutieli and the budget M of ADR-007 3.4 are withdrawn. There are no slots to run out of (G-12); unused budget no longer costs power.
5. **Fresh data for later batches.** Batch b >= 2 can give S or C only on a vintage whose confirm outcomes were not available to anyone when the batch closed: observation dates after the previous vintage's end and fetched after the close, or a dataset the plan lists as never opened and whose first read goes through the confirm handle.
6. **Registered after unblinding.** A test registered after a batch closes may run on the old vintage. It gets estimate, interval and X95, all labelled "descriptive". Its verdict is N with flag `registered_after_unblinding`. It cannot be S, C or E there.
7. **Seen confirm period.** If the project published effects for a confirm period before sealing (earthquake 2011 onward; monthly gold and silver from 2000, see F-05 and O-03), the plan marks the vintage `seen: true`. On it S and C are impossible; a signal gives N with flag `signal_on_seen_data`. E is allowed only for a test whose calendar hash equals one committed before the project's first look, and carries the flag `seen_data`.
8. **Variants.** At most 3 candidate variants per lineage per batch. More go to the sensitivity grid. Every variant and every `use:` child takes its own share of alpha_b, so cloning a winner only makes every threshold in that batch stricter.
9. **Controls** (tidal phase, ENSO, shifted sky, planted effect) are outside every batch.
10. **Replication.** An old principle may be registered again in a later batch on a fresh vintage. It is a new test with that batch's threshold. The old record does not change.

Eligibility in one table (implemented in the verdict function, section 9):

| Registered | Confirm period of the vintage | S, C | E | Numbers |
|---|---|---|---|---|
| Before batch close | Unseen | yes | yes | confirmatory |
| Before batch close | Seen, calendar hash older than the first look | no (`signal_on_seen_data`) | yes (`seen_data`) | confirmatory for E only |
| After batch close | Same vintage | no | no | descriptive (`registered_after_unblinding`) |
| Any later batch | Fresh vintage | yes, at that batch's threshold | yes | confirmatory |

### 3.3 Why this closes S-03, S-04, S-09, S-10

- S-03: a test's threshold is a stored constant. It does not depend on any other p-value, so no other result can move a verdict. Old batches are never recomputed. The sentence "adding a principle does not change old verdicts" becomes true without exception.
- S-04: the clone attack needs a test designed after the holdout is public to be judged on that holdout. Rule 6 forbids that. On fresh data the clone has a valid p-value and a small threshold. Total chance of any false S per domain, all batches together: at most 0.05, under any dependence.
- S-09: the rank-1 bar is higher than before. With n_b = 20, 40, 60 the threshold is 2.0e-3, 1.0e-3, 6.7e-4, reached by the sign-flip test with 9, 10, 11 used blocks (was 12 to 13). The gate prints, per domain and before close, the **supportability table**: how many registered tests can support, can only limit, or are untestable at the current n_b. The owner closes the batch with that table in view. Silver is declared limit-only in its plan.
- S-10: the guarantee is stated as it is: per domain, per verdict type, family-wise. The summary's first paragraph prints: "Chance of at least one false Supported in a domain: at most 5% over all time. Across D domains and three verdict types: at most D x 3 x 5% in total; expected number of false verdicts at most that." No hidden cross-domain claim.

### 3.4 How old verdicts stay fixed

- The record of a confirmed test stores `a_test`, batch id, vintage id, the seal bundle hash and the ledger position. The results file of a closed batch is hashed into the changelog chain.
- A run that finds a closed batch recomputes nothing. It re-verifies the stored record byte for byte.
- The only permitted recomputation is the engine-fix rule (G-05, section 9), which keeps `a_test` and shows both results.
- Plan amendments made after a batch close apply to the next batch only (S-12).

### 3.5 Random streams (G-06)

Every random draw of a test comes from `seed = first 8 bytes of SHA-256(plan seed | test id | purpose)`, with purpose one of `signflip`, `thinning`, `placebo`, `bootstrap`. No generator is shared between tests.

### 3.6 Proof test

`tests/test_validity_family.py` (extends WP-66's file) and the certificate suite.

| Case | Design | Pass |
|---|---|---|
| F1 Fixed threshold | Batch of 43 tests; change any other test's p-value to 1e-9 | Every other verdict and record byte-identical |
| F2 Add a test | Close batch 1, run, register 5 more tests, run again | Batch-1 results file byte-identical; the 5 land in batch 2 with flag `registered_after_unblinding` on the old vintage |
| F3 Clone attack (S-04 worked example) | 2,000 simulated null families of 43 tests on real calendars; after the confirm, an adversary registers 17 copies of the test with the smallest p, as variants, `use:` children and renamed files | On the same vintage: zero S among the copies in every family. Families with any false S: upper 95% bound <= 0.06 |
| F4 Clone attack with fresh data | As F3, then an independent fresh vintage is simulated and batch 2 is confirmed on it | Families with any false S over both batches: upper 95% bound <= 0.06 |
| F5 Alpha table | 50 batches | Sum of alpha_b <= 0.05; a_test equals alpha_b / n_b to the last bit |
| F6 Seeds | Run with tests A, B; run with A, B, C | Every number of A and B byte-identical (E4) |
| F7 Eligibility | Table test over every row of 3.2 | Exact verdict and flag per row |
| F8 Null families | 2,000 null families per outcome type through the whole pipeline | Any S: bound <= 0.06; any C: bound <= 0.06 |

## 4. Confirm-once and the calibration gate (H-5, H-6)

### 4.1 Ledger contract (code by FIX-code; this section is what it must satisfy)

- One file, `studies/validity/confirm_ledger.jsonl`, hash-chained (each entry holds the SHA-256 of the previous line).
- Key of a confirm entry: `(domain, dataset_sha256, period, lineage_id, version, variant, outcome)`. One entry per key, for ever.
- `lineage_id` = SHA-256 of (root rule id, **calendar hash**). The calendar hash is the hash of the active-bar vector on the vintage's grid. A renamed copy has the same calendar hash and is refused as a duplicate at registration. This also pins `use:` parents: the child's calendar hash changes when the parent does (G-04).
- `dataset_sha256` is recomputed from the snapshot file by the ledger code. A caller-supplied string is not accepted.
- The gate hash in the entry is recomputed from `gate.json` on disk and bound to the test id.
- Adapters return confirm-period outcomes only to a `ConfirmHandle` issued by `begin_confirm`. Without a handle an adapter returns explore-period rows only. `--provisional` runs never get a handle. Public helper functions that load a whole catalogue or series (for example `EarthquakeDomain.catalogue()`) take the same handle or cut at the explore end.
- Old study pipelines that read the same snapshots are moved behind the same adapters or deleted before the first batch close (WP-88 lists them).

### 4.2 Seal bundle and outside timestamp

One choice: **OpenTimestamps**. It needs no account, sends only a hash, and anyone can verify the proof against the Bitcoin chain without trusting the owner or the repository host. The OSF deposit of ADR-004 D-3 stays as the human-readable copy; it is not the gate.

1. `astro-validity seal <domain>` builds the **seal bundle**: one JSON file with the commit id, domain plan hash, family lock head, ledger head, the batch's test ids with their calendar hashes and `gate.json` hashes, rule-file hashes, dataset hashes, environment lock hash, ephemeris file hashes and the calibration certificate hash.
2. It writes the bundle's SHA-256 to the ledger as `batch_close`, commits, **pushes** to the public remote and creates `<bundle>.ots` with the OpenTimestamps client.
3. `astro-validity confirm <domain>` refuses to issue a handle unless: the tree is clean; the bundle recomputed now equals the stamped one; `ots verify` reports a completed Bitcoin attestation for that hash; the commit that holds the `batch_close` entry is an ancestor of the remote branch head.
4. The proof file and the block height go into the run manifest and onto every card footer.

A completed attestation takes some hours. So sealing and confirming are never the same sitting. That delay is intended.

Why this closes S-05: (a) another folder: one ledger, keyed by lineage, not by path. (b) Deleted uncommitted entry: the entry is committed, pushed and timestamped before any handle exists. (c) Fake data hash: recomputed. (d) Direct adapter access: handle only. (e) Provisional run: no handle. (f) Renamed lineage: calendar hash. (g) Amendment after results: the plan hash is inside the timestamped bundle, and amendments apply to the next batch only. A rewritten git history cannot recreate a Bitcoin attestation with an earlier date.

### 4.3 Proof test for S-05 (exit criterion E5)

`tests/test_confirm_bypass.py`, one test per bypass, each must raise the named error on a temporary repository:

| Test | Attack | Expected |
|---|---|---|
| P1 | Copy the study or the rule to a new folder and confirm again | `ConfirmAlreadyRunError` |
| P2 | Start a confirm, delete the uncommitted ledger line, start again | Not reachable: no handle before commit; if the committed line is removed, `LedgerTamperedError` |
| P3 | Pass a 64-hex string that is not the hash of `gate.json` | `GateHashError` |
| P4 | Call `outcomes()`, `catalogue()` or `mainshock_flags()` with no handle and ask for a confirm-period row | Rows end at the explore end; asking beyond raises |
| P5 | `--provisional` run on a dirty tree | No confirm row is read (spy on the adapter) |
| P6 | Rename the rule id, same conditions | Refused at registration as a duplicate calendar |
| P7 | Change the plan's SESOI after `batch_close`, then confirm | Bundle mismatch, refused |
| P8 | Confirm with a missing, pending or wrong `.ots` proof (verifier mocked) | Refused |
| P9 | Break one link of the hash chain | `LedgerTamperedError` |

### 4.4 Calibration certificate (G-01, exit gate)

- `make calibrate` runs the slow suite (sections 1.3, 2.4, 3.6, 6.3, 8 and the power cases below) and writes `studies/validity/calibration/certificate.json`: every case with its replications, rate, bound and pass mark; the git blob hash of every file in `core/stats/`, `core/validity/`, `core/domains/` and `tests/simulators.py`; the environment lock hash; the seed.
- `begin_confirm` recomputes those blob hashes. A missing certificate, a failed case for the outcome type of the test, or a changed file means no handle. So changing the statistics after calibrating means calibrating again.
- The simulators and the suite are committed **before** the code they certify (WP-84 before WP-85, 86, 87).
- Replications: 10,000 for per-test rates, 2,000 families for family rates, 1,000 for power. Target run time: under two hours on eight cores; cases run in parallel processes, no threads (G-13).

Power and recovery cases (E3, O-04):

| Case | Design | Pass |
|---|---|---|
| W1 Power | Constant effect of twice the gate's minimal detectable effect planted in the confirm period, each outcome type, tests the gate called supportable | S in at least 80% of 1,000 runs |
| W2 Gate honesty | Tests the gate called "limit only" | S in 0 runs |
| W3 Planted recovery on real noise | Per domain, on the **explore** period of the real outcome with a real calendar shifted by a whole number of years: plant an effect equal to the SESOI | Detected at the power the gate states, within 10 points. Runs inside the sealed run as the domain's positive control. If it fails, every card of the domain carries `control_not_detected` |
| W4 Support flag | Tests where the gate computes P(S given effect = SESOI) below 0.8 | Flag `support_underpowered` present (A-07) |

## 5. Placebo skies: the contract (A-01)

FIX-code changes the tie rule. The pipeline must also meet this contract (`core/validity/robustness.py`):

- R2 is computed **per test**, on that test's statistic T only. No maximum over indicators.
- A placebo kind applies to a test only if it changes at least 1% of the test's active bars. Otherwise it is "not applicable", never "failed".
- The tropical zodiac is a rival system. It moves to the sensitivity grid.
- Time-shift placebos: 200 skies. For season-linked calendars (section 6) the shifts are whole years, k = 1 to 100 in both directions, so the Sun and the season stay in place. For other calendars the existing random offsets.
- R2 passes when `(1 + number of placebos with a strictly larger statistic) / (n + 1) <= 0.05`.
- R3 counts **distinct calendars**: a sensitivity cell counts only if it changes at least 5% of active bars against the primary (F-07).

Proof test (`tests/test_validity_robustness.py`): a nakshatra-only, a tithi-only and an orb-conjunction calendar with a planted strong effect all pass R2 (they could not before); under no effect R2 passes in at most 5% of 10,000 runs (bound <= 0.06); adding a second test leaves the first test's R2 byte-identical.

## 6. Season and calendar confounding (F-01, F-02)

### 6.1 Design

New module `core/stats/season.py`, calendar-only.

1. **Measure.** `season_r2` = share of the calendar's variance explained by the first three yearly harmonics of day-of-year. A calendar with `season_r2 >= 0.05` is **season-linked**. The number is printed on the card.
2. **Controls for season-linked calendars.** The control window of an episode is the same day-of-year span in the nearest years where the calendar is inactive on at least 90% of the span: one earlier year and one later year, searched up to three years away, each span used by one episode only. No such span on either side: the block is dropped. A Sun-in-sign calendar finds none, so it is Untestable with the reason "cannot be separated from the season". That replaces a silent pass or a misleading N.
3. **Placebos and shift cells** use whole-year shifts (section 5).
4. **Outcome.** Seasonal outcomes are tested as anomalies from a day-of-year (or month) mean computed **without the year being tested** (also D-06).
5. **R4, with its measure fixed.** `baseline_r2` = R-squared of the calendar regressed on all of the domain's baselines together. R4 fails at `baseline_r2 >= 0.5`. Both numbers are printed.
6. **Slow physical cycles (F-02).** Monsoon, flood and earthquake plans add as baselines an 18.6-year term (sine and cosine) and a solar-cycle term (smoothed sunspot number). A principle whose calendar has `baseline_r2 >= 0.5` against these fails R4. A principle with a known physical or social route (lunar phase and tide, tithi and festival buying, node cycle and nodal tide) carries `known_channel` in its rule file (section 7).
7. **Same controls in both periods.** The monsoon plan uses one ENSO series covering explore and confirm years: a long sea-surface-temperature Nino 3.4 reconstruction from 1870 fetched by our own script and hash-pinned (WP-95). If it cannot be fetched or its terms forbid use, the monsoon analysis period is cut to the years the pinned ENSO series covers. ONI stays as a cross-check.

### 6.2 Why it closes the loophole

A season-linked calendar used to beat every non-yearly shift and placebo because of the season alone. Now its controls, its placebos and its outcome anomaly all hold the season fixed, so the season cannot produce a difference. What cannot be separated is called Untestable.

### 6.3 Proof test

`tests/test_stats_season.py` and the certificate suite. Real calendars from the ephemeris: Mercury retrograde, Venus combust, eclipse windows of 3 days either side, Sun in one nakshatra, Sun in one sign, tithi group; grids: daily 1968 to 1998, yearly 1871 to 2016.

| Case | Outcome generator | Pass |
|---|---|---|
| Z1 Seasonal mean | Yearly sine with amplitude 1 standard deviation plus a four-month pulse; no calendar effect | S in at most 5% of 10,000 runs (bound <= 0.06); R2 pass rate likewise |
| Z2 Seasonal events | Poisson events with rate times 8 in four months, clustered as X4 | same |
| Z3 Yearly unit | Rainfall anomaly: Normal with standard deviation 10 points, AR(1) ENSO-like driver worth 4 points per standard deviation, a 31-year epoch wave; drought flag below minus 10 | same, and false "excluded" at SESOI bound <= 0.06 |
| Z4 Old design fails | Z1 with neighbour controls and non-yearly placebos | S or R2 pass above 20% for at least one Sun-linked calendar (documents the loophole) |
| Z5 Sun in sign | any | 100% Untestable with the season reason; no outcome read (spy) |
| Z6 Nodal proxy | Outcome with an 18.6-year wave, Rahu-in-sign calendar | S in at most 5% with the nodal baseline; R4 fails |

## 7. What the words may say (H-7): encoding, SESOI, channels

### 7.1 "As encoded" (A-02, A-03, A-04, O-01, O-02)

- **Verdict words by level.** L4 and above (a practitioner attested the encoding before the confirm): the five ADR-007 verdicts. Below L4 the words are: "Encoding supported on this dataset", "Encoding contradicted", "Encoding: steady effect excluded above X", "Encoding not supported, not excluded", "Untestable on this data".
- **Fixed second line below L4:** "This result is about the project's encoding of the rule. It is not a result about the source text or about astrology."
- **Reading differs from the text** (`reading.kind != reading.text_says`): the card title is "Project hypothesis derived from <source>", the source's name is not in the verdict line, and the test is left out of any count of classical principles. The text's own claim is listed under "what was not tested" unless it has its own rule file.
- **Single condition:** every card prints "Tested as a single condition, without the cancellations and strength rules the tradition applies." A synthesis rule is allowed as one principle: a deterministic scoring function supplied by a practitioner, hashed into the lock before the batch closes.
- **Summary.** First table is the sampling frame: how each principle entered (text, practitioner, project), how many candidates were not encodable, not sourced or untestable. Then one table for L4 and above and a separate one for lower levels. No total across levels, no percentage over the whole set, and never a sentence about "astrology" as a whole.
- **Two columns** on cards and summary: "calendar is associated with the outcome" and "beyond known physical and social channels". A supported principle with `known_channel` is counted only in the first.
- **Allow-list.** Reports may contain only sentences from `core/validity/sentences.py` with filled slots. The deny-list is removed.
- **L2 entry and FAMILY_MIN_LEVEL.** L2 stays the entry level (owner decision "L2", to be signed, section 12); `levels.py` is set to 2 to match.

Proof test (`tests/test_validity_verdict.py`, `tests/test_validity_report.py`): table test over level x verdict x flags gives the exact string; a render of 200 random records contains no verdict sentence without the word "encoding" below L4; the summary of a mixed set has no cell that adds L2 and L4 counts; every sentence on every generated page matches the allow-list.

### 7.2 SESOI from outside (S-13)

One rule, applied by the plan validator. No value is chosen by the project.

1. If the source states a size, that size (with page and quotation, level L1 or above).
2. Otherwise the domain **yardstick**: the published size of the best-established non-astrological effect of the same kind on the same outcome, from a named publication. Stored in `studies/validity/sesoi_sources.yaml` with citation, page, the number as printed, the conversion to the plan's effect scale, the checker's name and the date.
3. Neither: the test has **no SESOI**. Verdict E is impossible; the card shows X95 and X-strict only.

Yardstick kinds, to be filled from the publications by design task D11 and checked at the page by the owner (H18). No number is written here, on purpose: daily returns: a published calendar anomaly of the same market type (turn of month or holiday effect); monthly returns: the same at monthly scale; earthquake rate: a published seasonal or tidal modulation of seismicity for the same arc; monsoon rainfall: the published mean deficit of El Nino years; flood rate: the published ENSO-phase rate ratio.

The ADR-007 4.2 proposals (25 basis points, rate ratio 2.0, 5%) are withdrawn as SESOI values. They were written with the project's own results in view. The flag `sesoi_post_hoc` is not needed, because such a value cannot enter a plan.

Proof test (`tests/test_validity_plan.py`): a plan whose SESOI has no `sesoi_sources` entry, or an entry without page and checker, or an entry citing a file inside this repository, is refused; a test with no SESOI can never return E (table test).

### 7.3 Channels and baselines (A-09)

Every card shows the effect with and without the socially mediated baselines (festival days) and states which was tested: "an effect beyond what festival buying explains". The primary test is the one **with** baselines.

Proof test: simulated returns with a festival-day effect only, tithi calendar: S without baselines in more than 50% of runs, S with baselines in at most 5% (bound <= 0.06); the card carries both rows and `known_channel`.

## 8. Data rules (D-01 to D-06)

| Finding | Chosen fix | Why it closes | Proof test |
|---|---|---|---|
| D-01 Monthly prices are monthly averages | Unit is the month. A month is active when the calendar is active on at least half of its days. Only principles whose `operationalisation.horizon` is a month or longer are registered on monthly data. `guard_bars: 1`. A monthly result is never called a cross-check of a daily one. | Averaging makes neighbouring monthly returns correlated; the guard month keeps the correlated bar out of the comparison, and the block test is local. | Simulate 30 years of a daily random walk, average by month, take returns. Assert lag-1 autocorrelation between 0.15 and 0.35 (the artefact is present). Null calendars with 8 to 20 blocks, 10,000 runs: rejection bound <= 0.06 with the guard. |
| D-02 DEM to USD | `gold_dem_frankfurt` is the primary outcome as fetched. `gold_usd` is a second declared outcome with its own FX source, fixing time and the rule "a return over a day missing in either series is dropped". | Different outcome ids cannot be mixed in one sentence; the gap rule is in the plan, not chosen by eye. | Unit test with planted holiday mismatches: the dropped set equals the rule's set; no return spans a mismatched day. |
| D-03 Earthquake catalogue | Snapshot hash pinned in the plan (no "newest snapshot" fallback). One magnitude type before any ISC comparison. A published regionalisation is a sensitivity cell. ETAS declustering (ADR-004 WP-26) is required before the earthquake batch closes; until then the domain is limit-only. Completeness change over decades is handled by the block design (controls are next to their episode) plus X4's rate trend. | Removes the silent data choice; the trend cannot produce a block difference. | Adapter raises without a pinned hash; X4 passes with a doubling background rate; code-audit m8 (FIX-code) test for the declustering fit on explore years only. |
| D-04 Hash-only data | Owner reads the licences (H4). Every snapshot whose terms allow it is deposited on Zenodo and the DOI is stored in `snapshot_index.json`; the rest stay in an owner-held archive with a derived, non-reconstructing table published where allowed. A domain with no depositable primary snapshot is grade B at best and says so. | An outsider can get the bytes behind the hash. | `check_snapshots`: every snapshot used by a sealed plan has `deposit_doi` or `owner_archive: true` with a reason; build fails otherwise. |
| D-05 Hand-set grade inputs | `reproduced`, `open_items`, `quality_flaws` are read from `data/registry/dataset_grades.yaml` (committed; each row has a date and a named checker). The adapter constructor no longer accepts them. | A grade cannot be raised by a keyword argument. | Passing the old arguments raises `TypeError`; a registry row without checker or date gives grade C. |
| D-06 Rainfall and flood series | Anomalies and running means leave out the year being tested. DFO: year strata plus a linear reporting-trend term in the baselines. No splice of IITM with another agency's series. | The tested year can no longer pull its own baseline toward itself. | Planted single-year spike: the leave-one-out anomaly equals the spike; the old centred mean understates it. Z3 passes. |

## 9. Verdict function, seal stamp and report gate

### 9.1 Verdict function, second version (amends ADR-007 5.4)

Symbols: `p_sup` (confirm period, claimed direction), `p_opp` (opposite direction, whole period), `p_ex` (exclusion at the SESOI, whole period), each compared with the stored `a_test`. Eligibility (section 3.2) is checked first.

| Code | Condition (all must hold) |
|---|---|
| U | Gate fails for both abilities, or every block was dropped |
| S | S-eligible; "can support"; `p_sup <= a_test`; explore effect has the same sign; R1 to R4 pass; `source.published` is before the confirm period starts (F-03) |
| C | C-eligible; directional claim whose direction is not disputed; `p_opp <= a_test` |
| E | E-eligible; a SESOI exists (7.2); minimum-information rule met; `p_ex <= a_test` |
| N | everything else |

Sentences: E and N cite **X-strict** ("with the family guarantee"). X95 is shown as "per-test value". When X-strict is unbounded the sentence says "no family-level bound" (S-11).

Flags (the ADR-007 six stay): `support_underpowered`, `known_channel`, `seen_data`, `signal_on_seen_data`, `registered_after_unblinding`, `source_postdates_data`, `project_extension`, `reading_differs`, `recomputed_after_confirm`.

**Engine fix after a confirm (G-05).** If stored numbers do not reproduce because of an engine or predicate fix: one recomputation per test, same `a_test`, both results on the card with the number of calendar bars that changed, flag `recomputed_after_confirm`. A fix proposed after its author saw the confirm result needs the sign-off of a second person in the changelog entry, or waits for the next vintage.

### 9.2 Seal stamp (G-02, G-03)

The stamp adds: Python version; the hash of `ops/requirements.lock.txt` and a refusal when installed versions differ from it; ephemeris model and the hash of every ephemeris file; the path and hash of every file the run opened (recorded by an audit hook on `open`). A sealed run fails if it opened a file git does not track, other than snapshots listed in the index. Study scripts are imported by file path under a unique module name, never through `sys.path`. The three stale `.gitignore` lines are removed and the ignored experimental rule file is deleted or committed.

### 9.3 Report gate (G-08)

Generated pages are template renders only: the gate renders every page again from the results file and compares bytes. Results files are checked against the hash in the run manifest and the changelog chain. `--no-provenance` is removed. Sentences come from the allow-list (7.1). The number-pattern fix is code-audit M5 (FIX-code).

## 10. Every critical and major finding: fix, reason, proof, package

"Cert" means the certificate suite of section 4.4. Bound <= 0.06 means the upper one-sided 95% Clopper-Pearson bound at the replications named in the section cited.

### 10.1 Critical

| Finding | Chosen fix | Why it closes | Proof | WP (owner) |
|---|---|---|---|---|
| S-01 | Exclusion by effect removal on balanced blocks; minimum-information rule; "steady effect" wording (section 2) | Validity comes from swapping active and control, not from the shape of the outcome | X1 to X8, X10 | WP-86 (Opus) |
| S-02 | Disjoint control bars, gap cut at the midpoint, balance floor 0.5 (section 1) | No bar is subtracted twice | B1 to B5 | WP-85 (Opus) |
| S-03 | Fixed threshold alpha_b / n_b stored at batch close (section 3) | A threshold no longer depends on other p-values | F1, F2, F5 | WP-88 (Opus) |
| S-04 | Closed batches; later tests need fresh data; alpha 0.04 x 0.2^(b-1) (section 3) | A test designed on a public holdout cannot be confirmed on it | F3, F4, F7 | WP-88 (Opus) |
| S-05 | Keyed ledger, handle-only access, seal bundle, OpenTimestamps proof before any handle (section 4) | Every listed bypass meets a check that does not rely on the owner's word | P1 to P9 | FIX-code (code parts); WP-89 (Opus) |
| A-01 | Tie rule by FIX-code; R2 per test, applicability rule, tropical to sensitivity, whole-year shifts (section 5) | A placebo that does not change the calendar cannot count against it | Section 5 tests | FIX-code; WP-94 (Opus) |
| G-01 | Calibration certificate tied to code hashes; checked by `begin_confirm` (section 4.4) | Verdict code cannot run on real confirm data without evidence of its error rates, and cannot change afterwards | Cert complete; a changed blob refuses the handle (unit test) | WP-84, WP-98 (Opus) |

### 10.2 Major: statistical validity

| Finding | Chosen fix | Why it closes | Proof | WP (owner) |
|---|---|---|---|---|
| S-06 Estimand mismatch | One statistic T per outcome type for estimate, p, X and SESOI; K_eff in the gate (1.1) | Card and test speak about the same number | Unit test: card effect equals T to the last bit; a rate-ratio SESOI is tested on the rate-ratio scale (X3) | WP-85, WP-86 |
| S-07 Binomial interval | Removed from cards; docstring corrected; the ledger sentence "8 of 13" is marked superseded and re-derived by the first sealed run | The too-narrow interval can no longer support an exclusion | On X4 data the old interval covers below 90% (documented) and the new limits pass X6 | WP-86 |
| S-08 Shift test and routing | Block sign-flip is the only primary method; shift test is a sensitivity cell; routing table deleted | No method choice is left | B3 with regime-switching volatility; grep test: no routing key in any plan | WP-85, WP-93 |
| S-09 Support unattainable | Bonferroni per batch raises the bar's reach (9 to 11 blocks); gate prints the supportability table before close; silver plan says limit-only | The reader sees in advance what could ever be supported | Gate test on the real calendars: table counts equal hand counts; W2 | WP-88, WP-94 |
| S-10 Domains and verdict types | Guarantee stated per domain and verdict type; union bound printed first in the summary | No implied project-wide error rate | Render test: the sentence and the number D x 3 x 5% are present and computed from the run set | WP-96 |
| S-11 X95 unadjusted | Sentences cite X-strict; X95 labelled per-test | The asserted bound carries the family guarantee | Verdict table test; over 2,000 null families the share with any X-strict below the true effect has bound <= 0.06 | WP-94 |
| S-12 Open forking paths | Plan validator refuses the words "proposal" and "default adopted" and any missing key (split, SESOI source, vintages, estimand, windows, merge gap, guard bars, R measures, placebo sets, baselines, day convention, grid for X). No batch close under an unsigned owner decision. Amendments apply to the next batch | Nothing a result could bend is left unset when outcomes are read | Validator tests, one per key; P7 | WP-93; owner H16 |
| S-13 SESOI after the answer | Source size or published yardstick only; else no SESOI and no E (7.2) | The project cannot pick a threshold with its results in view | 7.2 tests | WP-93; D11; owner H18 |

### 10.3 Major: bias against astrology

| Finding | Chosen fix | Why it closes | Proof | WP (owner) |
|---|---|---|---|---|
| A-02 L2 read as astrology | "Encoding" verdict words below L4, fixed second line, split summary (7.1) | A null on a project encoding cannot be quoted as a null on a text | 7.1 tests | WP-94, WP-96 |
| A-03 Text read backwards | Title "Project hypothesis derived from ..."; not counted as classical; text's own claim under "not tested"; H11 page check before registration | The source's name is not attached to a claim it does not make | Render table test on `reading` mismatch; register refuses BS-sourced rules without a page | WP-91, WP-94; owner H11 |
| A-04 Single rule against synthesis | Fixed card line; synthesis route as one hashed scoring function | The card states the limit; a practitioner can submit the full rule | Schema test: synthesis function hash in the lock; changed function is a new version | WP-91 |
| A-05 Day, place, horizon | `operationalisation` requires `day_convention`, `place`, `horizon`, each with `fixed_by`. Where the source implies them, the primary outcome uses them (sunrise day at the source's place; monthly outcome for a monthly claim; regional rainfall for a regional claim). The fixing-instant test becomes a sensitivity cell | The tested calendar is the one the source describes | Register refuses a missing field; calendar-only test reports the share of days on which sunrise and fixing-instant conventions differ for Moon rules, and the card prints it | WP-91; WP-76 (amended) |
| A-06 Currency and market | Outcome ids name market and currency; fixed sentence "tested on the Frankfurt fixing in DEM"; the bare word "gold" is not in the allow-list for verdict lines | A DEM null cannot be printed as a null on gold | Allow-list test | WP-93, WP-96 |
| A-07 Power asymmetry | Gate computes P(S given effect = SESOI); below 0.8 gives `support_underpowered`; E wording "steady effect at or above the project's threshold" | The reader sees that support was not achievable | W4; sentence table test | WP-94 |
| A-08 Disputed direction | `expected_effect.direction` needs `fixed_by`. A rule listed in a `DISPUTES.md` is tested as `either`, or as two lineages named after their sources. No C for a disputed direction | One school's support cannot become another's contradiction | Register test against the disputes list; verdict table test | WP-91, WP-94 |
| A-09 Astrological baselines | With and without social baselines on the card; primary is with; `known_channel` (7.3) | The card says which claim was tested | 7.3 test | WP-94 |

### 10.4 Major: bias for astrology

| Finding | Chosen fix | Why it closes | Proof | WP (owner) |
|---|---|---|---|---|
| F-01 Season | Same-season controls, whole-year placebos, leave-year-out anomalies, R4 as `baseline_r2 < 0.5` (section 6) | The season is held fixed in every comparison | Z1 to Z5 | WP-87 (Opus) |
| F-02 Physical proxies | Nodal and solar-cycle baselines; one ENSO series for both periods; `known_channel` | A proxy cycle is removed or named | Z6; plan validator refuses a monsoon plan whose ENSO series does not cover both periods | WP-87, WP-93, WP-95 |
| F-03 Source after the data | `source.published` required; S impossible unless it precedes the confirm period; flag `source_postdates_data` | A rule fitted to the years cannot be confirmed on them | Verdict table test | WP-91, WP-94 |
| F-04 Encoder knows history | Every `fixed_by: project` choice puts its alternatives in the sensitivity grid automatically; the choice is committed before the calendar is joined to any outcome (commit order checked from the lock); card names encoder and runner | A leaning choice is visible beside its alternatives | Register test: a project-fixed parameter without alternatives is refused | WP-91 |
| F-05 Seen confirm periods | `seen: true` vintages: no S or C (3.2 rule 7); set for earthquake 2011 onward and monthly gold and silver from 2000 | Published numbers cannot be confirmed again | F7; validator requires the `seen` key for every vintage | WP-88, WP-93 |
| F-06 Fishing across outcomes | Each `tests` entry quotes the source words that justify outcome and direction; otherwise `project_extension`, shown in a separate table. Each still takes its share of alpha | Extensions are visible and paid for | Register and render tests | WP-91, WP-96 |

### 10.5 Major: data, governance, other

| Finding | Chosen fix | Why it closes | Proof | WP (owner) |
|---|---|---|---|---|
| D-01 to D-06 | Section 8 | Section 8 | Section 8 | WP-93 (D-01, D-02), WP-95 (D-03 to D-06); owner H4 |
| G-02 Seal and environment | Stamp of 9.2; refusal on untracked reads and on lock mismatch | The record names everything that produced the number | Tests: untracked rule file read fails the run; changed numpy version fails; ephemeris hashes present | WP-90 (Opus) |
| G-03 Module collision | Import by path under unique names | First import can no longer win | Test: load gold and earthquake `pipeline` in one process, both resolve to their own file | WP-90 |
| G-04 `use:` not pinned | `use: id@version`; parent file hash in the lock; calendar hash in the lineage id | A parent edit forces an explicit new child version | Edit parent, run: build fails until the child is re-versioned | WP-91, WP-88 |
| G-05 Fix after confirm | One recomputation, both shown, flag, second sign-off (9.1) | A fix cannot be a quiet second look | Pipeline test with a changed predicate | WP-94 |
| G-06 Random streams | Seed from test id (3.5) | Adding a test changes no other number | F6 | WP-88 |
| G-07 Two schemes for national charts | One scheme, this one. The ADR-006 omnibus and hierarchical output stays as a page labelled "descriptive". The national-chart domain returns U with its reason until its gate passes here. The WP-80 word mapping is withdrawn | Two vocabularies cannot disagree | Adapter test: every test is U with reason "too few events"; no mapping function exists | WP-97 (Sonnet) |
| G-08 Report gate | 9.3 | Free prose and edited results files cannot pass | Tests: an edited results file fails; a page with one extra word fails; paraphrases ("debunked") fail the allow-list | WP-96; FIX-code (M5) |
| G-09 Levels from typed flags | Fixtures carry numbers and the code checks tolerances; `agrees` must be `true`; an L4 review is a commit by a second git identity dated before the batch close, or carries an outside reference | A level cannot be typed in | Tests: fixture without `agrees` is not counted; out-of-tolerance fixture fails; same-identity review rejected | WP-92 (Sonnet) |
| O-01 "Valid" against channels | Two labelled columns (7.1) | The report separates association from "beyond known channels" | Render test | WP-94, WP-96 |
| O-02 Not a sample of astrology | Sampling-frame table first; no rate over the whole set | Counts cannot be read as a rate for the tradition | Render test: no percentage cell in the summary header | WP-96 |

## 11. Minor findings

| Finding | Disposition | Where or why |
|---|---|---|
| S-14 Whole-period support for unseen datasets | Accept, not adopted | A file already on the owner's disk cannot be shown to an outsider as "never analysed". The split stays. Revisit only for a dataset whose first fetch happens after its batch close. |
| S-15 Default side; silent drops | Fix now | WP-85: no default side; dropped blocks counted by gate and test alike (B6). |
| S-16 GARCH-X floor 0.005 | Fix now | WP-93: the plan labels it secondary; it has no `a_test` and no verdict. |
| A-10 Blind attestation | Fix now | WP-92: "attested before the result" only when the review commit predates the batch close; later reviews shown with their date. |
| F-07 Near-copy sensitivity cells | Fix now | Section 5 (distinct calendars), WP-94. |
| D-07 Frankfurt fixing time, "." days, two-tier years | Fix now | WP-93 plan keys; D11 fills them. |
| D-08 `check_stale` accepts any indexed hash | Fix now | WP-95, after FIX-code: compare with the hash the plan pins. |
| D-09 Festival dates spot-check | Fix now | WP-95: external spot-check table for leap-month years before the festival baseline is used; owner supplies the reference almanac dates. |
| G-10 Old "pre-registration" header in the earthquake plan | Fix now | D11 rewrites the plan under WP-93's schema; the old file is kept with a superseded note. |
| G-11 Unbounded X | Fix now | Section 2.2: `unbounded: true`; WP-86 and the paper-kit accessor. |
| G-12 Budget exhaustion | Closed by design | Section 3: no budget M. |
| G-13 Global ayanamsa mode | Fix now | WP-98 and WP-90: processes, no threads; a test asserts the pipeline starts no thread. |
| G-14 Uncommitted working tree | Fix now | Owner or main session commits before WP-84 starts. |
| O-03 Site already shows 2000 to 2026 series | Fix now | Section 3.2 rule 7: those vintages are `seen: true` in the plans. |
| O-04 Undetectable positive control | Fix now | W3 planted-effect recovery replaces the tidal control as the gate for `control_not_detected`; the tidal row stays as information. |
| Code-audit m1 to m11 | Fix now | FIX-code. |

## 12. Owner decisions needed

No batch closes while any of these is unsigned. Each goes into `OWNER_DECISIONS.md` with a date.

| Id | Decision | Default proposed here |
|---|---|---|
| H16 (replaced) | Splits and vintages per domain, including which vintages are `seen` | As ADR-007 4.2 for splits; seen: earthquake 2011 onward, monthly gold and silver 2000 onward |
| H18 (new) | SESOI yardsticks: check each cited number at the page | none; without it there is no E |
| H19 (new) | Public remote and OpenTimestamps as the outside timestamp | as section 4.2 |
| H20 (new) | Alpha table 0.04 x 0.2^(b-1), Bonferroni per batch, at most 3 candidate variants per lineage | as section 3.2 |
| L2 | Entry at L2 with "encoding" wording | as section 7.1 |
| Support | Support needs an unseen confirm period; exclusion may use the whole period | as section 3.2 |
| H17 | Monsoon runs after sealed plan and certificate | unchanged |
| H4, H11 | Licences read; Brihat Samhita pages checked | required before the batch that uses them |

## 13. Work packages WP-84 onward

Ground rules of ADR-004 and ADR-007 hold: run only the named tests; one owner per shared file; Sonnet unless a concrete subtle risk is named; nothing on Fable. "FIX-code merged" means the concurrent code-audit fixes are on the branch.

#### WP-84 Simulators and certificate harness
- **Files:** `tests/simulators.py` (extend), `tests/test_simulators.py` (new), `core/validity/calibration.py` (new: case registry, Clopper-Pearson bound, certificate writer and checker).
- **Acceptance:** generators of sections 1.3, 2.4, 6.3 and 8 exist with fixed seeds and parameters; each has a test of its own stated property (skewness above 1 for the skewed ones; index of dispersion above 2 for clustered events before declustering; lag-1 autocorrelation 0.15 to 0.35 for monthly averages; season amplitude; mean events per window); effects are planted in bars, never in block differences; certificate round-trips and fails on a changed blob hash.
- **Depends on:** G-14 commit. **Owner:** Opus. Risk: a generator that is kinder than the real data certifies a wrong method.

#### WP-85 Balanced blocks and the primary test
- **Files:** `core/stats/blocks.py` (new), `tests/test_stats_blocks.py` (new). `episodes.py` is not edited.
- **Acceptance:** section 1.1 items 1 to 10; B1 to B6 pass (fast subset in the file, full in the certificate); the module reads no outcome when building blocks (spy test).
- **Depends on:** WP-84. **Owner:** Opus. Risk: an off-by-one at a gap midpoint shares a bar and restores S-02.

#### WP-86 Exclusion by effect removal
- **Files:** `core/stats/exclusion.py` (new), `tests/test_stats_exclusion.py` (new), `core/stats/rates.py` (docstring only), `core/paperkit/results.py` (accept `unbounded: true`).
- **Acceptance:** section 2.2; X1 to X8 and X10 pass, X9 is recorded; `episode_equivalence` and `upper_limit_episodes` are marked deprecated and are not imported by `core/validity` (import test).
- **Depends on:** WP-84, WP-85. **Owner:** Opus. Risk: a wrong side or a non-nested thinning gives a false "excluded".

#### WP-87 Season-matched controls and baselines
- **Files:** `core/stats/season.py` (new), `tests/test_stats_season.py` (new).
- **Acceptance:** section 6.1 items 1 to 6; Z1 to Z6 pass.
- **Depends on:** WP-84, WP-85. **Owner:** Opus. Risk: a control span that overlaps an active span lets the season back in.

#### WP-88 Batches, fixed thresholds, eligibility, seeds
- **Files:** `core/validity/family.py`, `tests/test_validity_family.py` (this re-specifies ADR-007 WP-66; if WP-66 has landed, it is edited, otherwise written to this spec).
- **Acceptance:** section 3.2 rules 1 to 10, 3.4, 3.5; lineage id with calendar hash; `use: id@version` parent hash in the lock; F1 to F7 pass.
- **Depends on:** WP-65 (done), WP-84. **Owner:** Opus. Risk: multiplicity and holdout reuse; an error here inflates every "Supported".

#### WP-89 Seal bundle, outside timestamp, bypass tests
- **Files:** `core/validity/sealbundle.py` (new), `tests/test_confirm_bypass.py` (new); the list of old study pipelines that read confirm-period rows, each moved behind an adapter or deleted.
- **Acceptance:** section 4.2 steps 1 to 4; P1 to P9 pass; the OpenTimestamps client is called through one function that tests replace; no network in tests; only the bundle hash leaves the machine.
- **Depends on:** FIX-code merged, WP-88, WP-90. **Owner:** Opus. Risk: the one-shot holdout; a gap cannot be repaired after a confirm.

#### WP-90 Seal stamp: environment, ephemeris, files read
- **Files:** `core/stats/seal.py`, `core/stats/manifest.py`, `core/domains/earthquake.py` (imports only), `.gitignore`.
- **Acceptance:** section 9.2; tests named in the G-02 and G-03 rows; no thread is started (G-13).
- **Depends on:** FIX-code merged (same files). **Owner:** Opus. Risk: an audit hook that misses a read path (pandas, yaml, swisseph) gives false assurance; each path has a test.

#### WP-91 Rule schema 3.1 and register checks
- **Files:** `core/rules/schema.py`, the register step, `tests/test_rules_schema_v31.py` (new).
- **Acceptance:** required for a `tests` block: `reading`, `operationalisation.{day_convention, place, horizon}` with `fixed_by`, `source.published`, `expected_effect.direction` with `fixed_by`, a source quotation per `tests` entry or `project_extension: true`, `use: id@version`, optional `known_channel` and `synthesis`; project-fixed parameters must list alternatives; disputed rules cannot be directional; old rule files still load and are reported as "not registrable" with the missing fields.
- **Depends on:** WP-65 (done). **Owner:** Sonnet (field checks against an exact list).

#### WP-92 Levels from evidence
- **Files:** `core/rules/levels.py`, `tests/test_rules_levels.py`.
- **Acceptance:** G-09 and A-10 rows; `FAMILY_MIN_LEVEL = 2`; code-audit m11 line for this test file stays fixed.
- **Depends on:** FIX-code merged. **Owner:** Sonnet.

#### WP-93 Domain plan schema and validator
- **Files:** `core/validity/plan.py` (new), `studies/validity/sesoi_sources.yaml` (schema and empty table), `tests/test_validity_plan.py` (new).
- **Acceptance:** every key of the S-12 row is required; "proposal" and "default adopted" are refused; vintages with `seen`; SESOI rule of 7.2; outcome ids carry market and currency; `guard_bars`; no routing key; GARCH-X labelled secondary; pinned snapshot hashes; ENSO coverage check for monsoon.
- **Depends on:** none. **Owner:** Sonnet.

#### WP-94 Gate, verdict function, robustness contract, sentences
- **Files:** `core/validity/gate.py`, `verdict.py`, `robustness.py`, `sentences.py`, `tests/test_validity_verdict.py`, `tests/test_validity_robustness.py` (re-specifies the affected parts of ADR-007 WP-68 and WP-69).
- **Acceptance:** sections 5, 7.1, 7.3, 9.1; K_eff and predicted I in the gate; supportability table; P(S given SESOI); a table test with one row per verdict, flag, level and eligibility combination and every boundary (p equal to a_test counts as passing).
- **Depends on:** WP-85, 86, 87, 88, 91; FIX-code merged. **Owner:** Opus. Risk: this function writes every headline.

#### WP-95 Data registers, pins, deposits, long ENSO series
- **Files:** `core/domains/base.py` (grade inputs), `data/registry/dataset_grades.yaml` (new), `data/snapshot_index.json` (deposit fields), `scripts/fetch/nino34_long.py` (new), `tools/check_paper_keys.py` (`check_stale` only), `core/domains/monsoon.py` (leave-year-out baselines), tests of each.
- **Acceptance:** D-03 to D-06, D-08, D-09 rows; the fetch stores bytes unchanged with a generic client name.
- **Depends on:** FIX-code merged. **Owner:** Sonnet.

#### WP-96 Report gate and summary
- **Files:** the report generator of ADR-007 WP-73, `tools/check_paper_keys.py` (render-equality and results-hash checks), `tests/test_validity_report.py`.
- **Acceptance:** section 9.3; rows S-10, A-06, F-06, O-01, O-02; methods page shows X9 rates and the "Not addressed" rule.
- **Depends on:** WP-94, FIX-code merged. **Owner:** Sonnet.

#### WP-97 National charts under one scheme
- **Files:** the national-chart adapter of ADR-007 WP-80, its test; one label line in the ADR-006 aggregate template.
- **Acceptance:** G-07 row.
- **Depends on:** WP-94. **Owner:** Sonnet.

#### WP-98 Whole-pipeline calibration and certificate (replaces the acceptance of ADR-007 WP-70)
- **Files:** `tests/test_validity_calibration.py` (new), `Makefile` target `calibrate`, `studies/validity/calibration/certificate.json` (generated, committed).
- **Acceptance:** every case B, X, F, Z, W, the section 5 and section 8 simulations run through `core/validity/pipeline.py` end to end, on Gaussian, heavy-tailed, right-skewed, rare-event and clustered-event generators, with 8, 12 and 20 blocks, with short-gap calendars, with seasonal outcomes; all pass marks met; certificate written; `begin_confirm` refuses without it.
- **Depends on:** WP-84 to WP-90, WP-94, ADR-007 WP-69. **Owner:** Opus. Risk: this is the evidence behind every verdict.

#### WP-99 Second audit pass
- **Files:** one report under `docs/research/`; no code.
- **Acceptance:** from a clean clone, an Opus session that wrote none of WP-84 to WP-98 re-runs appendix A of the strategy audit against old and new functions, runs `make calibrate`, attempts P1 to P9 by hand, and lists findings by the audit's severity scale. Exit: no new critical or major item.
- **Depends on:** WP-98. **Owner:** Opus (review only).

**Design and owner tasks.** D11 (architect): domain plans for gold, silver, earthquake and monsoon under the WP-93 schema, the SESOI source table with citations, the sentence allow-list text, the methods page skeleton. H16, H18, H19, H20, L2, Support, H4, H11 as in section 12.

### 13.1 Order

| Wave | Packages (no shared files inside a wave) | Gate |
|---|---|---|
| H0 | FIX-code merge; G-14 commit | Its own tests |
| H1 | WP-84; WP-91; WP-92; WP-93; WP-95 | Generators proven; schemas refuse bad input |
| H2 | WP-85; WP-88; WP-90 | B and F cases |
| H3 | WP-86; WP-87; WP-89 | X, Z, P cases |
| H4 | WP-94; then WP-96, WP-97 | Verdict table test |
| H5 | ADR-007 WP-69 (pipeline) on these modules; WP-98 | **Certificate green** |
| H6 | D11 plans sealed; owner sign-offs; WP-99 | E1 to E11 |
| H7 | ADR-007 WP-78 first sealed run | - |

Each package runs only its own test files. The full suite and `make calibrate` run once in the main session after a wave is integrated.

## 14. Exit criteria: where each is met

| Criterion | Met by |
|---|---|
| E1 No open critical; majors closed or owner-accepted on cards | Section 10; S-14 is the only accepted item and is minor |
| E2 Whole-pipeline calibration | WP-98 certificate (B, X, Z, F8 cases) |
| E3 Power and planted recovery | W1 to W4 |
| E4 Sequential rule, bit-identical numbers, clone scenario | F1 to F6 |
| E5 Ledger bypass tests and outside deposit | P1 to P9; section 4.2 |
| E6 Sealed plans with no open item | WP-93, D11, section 12 |
| E7 Schema and verdict rules | WP-91, WP-94 |
| E8 Data | WP-95, H4 |
| E9 Seal stamp | WP-90 |
| E10 Report gate | WP-96 |
| E11 Second audit | WP-99 |

Until all hold, every number on real data is provisional and labelled so.

## 15. What this changes in ADR-007

| ADR-007 | Change |
|---|---|
| 3.4 Multiplicity rules | Replaced by section 3. Budget M, slots and Benjamini-Yekutieli are withdrawn. The lock stays append-only and hash-chained and now records batches. |
| 4.2 SESOI and budget columns | Withdrawn. SESOI by section 7.2; no budget. |
| 5.1 Gate | G4 uses K_eff; G5 uses `a_test` for the current n_b; adds predicted informative blocks, supportability table, P(S given SESOI). |
| 5.2 Numbers | One statistic T per outcome type; block sign-flip is primary; routing rule deleted; binomial interval removed; X by effect removal; X-strict at `a_test`. |
| 5.3 Robustness | R2 and R3 by section 5; R4 by section 6.1. |
| 5.4 Verdict scale | Section 9.1. Flags may now record an eligibility limit; the sentence "flags never change the verdict" is replaced by the eligibility table. |
| 7.2 Confirm-once | Sections 4.1 to 4.3. |
| 9 Changelog | A closed batch is never recomputed; cause `new_principle` can no longer change an old verdict; cause `engine_changed` follows 9.1. |
| WP-66, 68, 69, 70, 80 | Re-specified by WP-88, 94, 94, 98, 97. |
| WP-78, WP-83 | Add dependencies: certificate, section 12 sign-offs, WP-99. |

## 16. Consequences

- Fewer principles will be testable. Calendars with no clean control time, Sun-in-sign calendars and tests with too few informative blocks become Untestable or "unbounded". That is the correct answer and each card gives the reason.
- Exclusion is conservative (twice the median over thinnings; Bonferroni). Some true nulls will stay N with a wide X. The error goes toward saying less.
- Almost every first-batch card will carry "encoding" wording, because most rules are L0 to L2.
- Principles added after the first report on a domain get descriptive numbers until new data exist. For past-only research that can mean years. This is the price of an honest holdout and is stated on the card.
- Sealing takes two sittings because of the timestamp.
- The owner must check SESOI yardsticks at the page (H18). Without them the reports still give X95 and X-strict for every tested principle, which answers "how much is ruled out".

## 17. Alternatives rejected

| Alternative | Why not |
|---|---|
| Bootstrap-t or studentised interval for X95 | Fails with rare events: most resamples have zero variance. Coverage cannot be shown at 8 to 20 episodes. |
| Rank-based (signed-rank) exclusion | Needs symmetric differences, which is the assumption that failed. |
| Poisson or negative-binomial likelihood interval | Depends on a dispersion estimate from a handful of blocks; too narrow when clustering is misjudged (the S-07 error again). |
| Block permutation of bars as the primary test | Bars inside a block are serially dependent; the swap of whole windows asks for less. |
| Online FDR (LOND, LORD) | Fixes S-03 but not S-04: a test designed on a public holdout has no valid p-value. |
| Keep Benjamini-Yekutieli and document "verdicts can be gained" | Leaves the stability promise false and keeps a stricter rank-1 bar than Bonferroni. |
| Full alpha 0.05 for every new batch | Error would grow without limit as principles are added. |
| OSF registration or a signed git tag as the gate | OSF is manual and slow per batch; a tag lives in a repository the owner can rewrite. OSF stays as the readable deposit. |
| SESOI by blind practitioner elicitation | Nobody on the project is blind to the published results any more. |
| Whole-period support on "unseen" datasets (S-14) | Cannot be shown to an outsider for files already on disk. |


---

## Amendment A1 (2026-11-22): equal-size blocks

**Finding (WP-85 calibration, 20,000 replications):** with skewed outcomes, a block whose control side has fewer bars than its active side inflates the one-sided false-alarm rate: balance 0.5 gives 7.3% (lognormal) and 6.0% (exponential); balance 0.8 gives 5.7% and 5.5%; balance 1.0 gives 4.9% to 5.2%. B2 at full size fails on the 5/5 calendar.

**Decision:** the balance floor of section 1.1 is raised from 0.5 to **1.0**. Every block is equal-size: the active side and the control side have the same number of bars. The longer side is trimmed, dropping the bars farthest from the active/control boundary. A block that cannot reach equal size within its gap-midpoint limits and guard bars is dropped and counted with the reason `unbalanced`. Season-matched windows (WP-87) obey the same rule.

**Consequence:** fewer usable blocks for short gaps, so some principles move to Untestable. This is the honest price of a test that holds its size on skewed data. B2 must pass at full size before any certificate is issued.


## Amendment A2 (2026-11-22): single-day and edge episodes stay testable

A1 dropped every block with one active bar (a one-sided block was forbidden) and most edge episodes. That makes daily-event principles (tithi days, new/full moon, ingress days, eclipse days) Untestable by construction, which is a bias against testing exactly the principles practitioners use most.

**Decision:** a block may take its equal-size control from ONE side when the other side is unavailable or when the active run is a single bar. The side is chosen before any outcome is read: alternate sides in calendar order, starting side fixed by the plan seed. Each control bar still lies within the gap-midpoint limit and outside guard bars, and is used by one block only. B1, B2, B3 and X1, X2 must pass at full size for daily-event calendars (new moon, tithi, eclipse window) under this rule, including a drift simulator (one-sided controls are sensitive to trend: the leave-year-out anomaly or detrending baseline must be applied first, and a drift case D1 must hold size).
