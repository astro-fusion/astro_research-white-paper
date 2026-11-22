# Code audit, 2026-11-22

Scope: commits `7018b2a..HEAD` (eccc082 to 55fe7c5) on `main`. Review only; no source file was changed.
Probes were run with `.venv/bin/python` (no network); each finding marked "confirmed" was reproduced.

Severity: **critical** = can produce a wrong published result or silently defeat a guard as shipped;
**major** = wrong output or broken contract on a realistic path; **minor** = edge case, misleading field or weak test.

No critical defect was found in the core inference (circular-shift enumeration, Phipson-Smyth floors,
sign-flip enumeration, wild-cluster inversion, matched-set permutation, past-only GARCH). The serious problems
are contract mismatches between the seal, the mundane writer and the paper-key gate. They mean that no
mundane or confirm result can ever pass the gate.

---

## Major

### M1. A confirm run can never be non-provisional: `begin_confirm` dirties the tree it requires to be clean (confirmed)
- **Where:** `libs/vedic_astrology_core/stats/seal.py:292-293` (ledger append) with `seal.py:265`, `stats/manifest.py:121-125` and `tools/check_paper_keys.py:117-125`.
- **Failure:** In a clean repo, `begin_confirm(study, plan, sha)` writes `confirm_ledger.jsonl`. It is untracked, so `tree_state` gives `dirty: True`.
  After that, `build_manifest(...)` stamps `provisional: True`, `require_clean_tree()` raises `DirtyTreeError`,
  and `check_paper_keys` reports DIRTY. Probe: `tree_state -> {'dirty': True, 'changes': ['?? studies/s/confirm_ledger.jsonl']}`, `manifest provisional after confirm: True`.
  The single confirm per lineage is spent, and its result can never be published.
- **Fix:** Exclude the study's own ledger path from the dirtiness check during a confirm (pass `ignore=[ledger]`). Or commit the ledger entry
  inside `begin_confirm` (`git add` + `git commit`) before returning, and record that commit as the run's commit.

### M2. Mundane results.json cannot pass the paper-key gate (no `git`, no `data.sha256`) (confirmed)
- **Where:** `libs/vedic_astrology_core/mundane/aggregate.py:638-657` (`build_report`), `mundane/cli.py:420-427`; the gate is `tools/check_paper_keys.py:122-123` and `:163-166`.
- **Failure:** `studies/mundane/artifacts/results.json` has the top-level keys `plan_sha256, provisional, slice, ...`. The commit and dirty flag are
  stored only under `slice.commit` and `slice.tree_dirty`, and there is no `data` key. `check_dirty` returns `DIRTY m: not written from a clean git tree (git=None)`
  and `check_stale` returns `STALE m: no data.sha256 in results`, even from a clean tree. The ADR-007 domain record (`domains/base.py:75-85`)
  uses a third shape, `dataset.sha256`, which the gate does not read either.
- **Fix:** Pick one provenance block for every writer: `{"git": {"commit", "dirty"}, "data": {"sha256", ...}, "plan": {"sha256"}}` (or teach the gate `dataset.sha256`).
  Have `build_report`/`run_slice` call `seal.require_clean_tree` + `seal.stamp_results`, and write the event-registry/catalogue hash as `data.sha256`.
  Add one end-to-end test that runs `check_paper_keys` on a real writer's output.

### M3. `confirm_window` does not read the mundane (or earthquake) plan schema (confirmed)
- **Where:** `stats/seal.py:166-175` against `studies/mundane/hypothesis.yaml:183-185` (`periods.confirm: {start, end}`) and `studies/earthquake/hypothesis.yaml` (`split.confirm`).
- **Failure:** `confirm_window(mundane_plan)` raises `SealError: plan has no periods.confirm_start`. Only the gold and silver plans use `periods.confirm_start`.
  WP-63's confirm will therefore fail on the plans it is meant for, or tempt an ad-hoc override.
- **Fix:** Accept `periods.confirm.{start,end}` and `split.confirm[0..1]` too, or route through the `DomainAdapter.periods()` contract (`domains/base.py:88-101`). Add a test per committed plan.

### M4. "One confirm per lineage" is bypassed by copying the study folder (confirmed)
- **Where:** `stats/seal.py:184-186`, `:205-221` (history is looked up by the ledger's path only; `git log` without `--follow`).
- **Failure:** Commit a ledger in `studies/s/`, copy the study to `studies/s2/` without the ledger, commit, then call `begin_confirm(studies/s2, ...)`. A second entry is written (`second confirm allowed under new dir: True`).
  The module docstring says that renaming the study does not open a second confirm.
- **Fix:** Key the lineage on something that moves with the plan: `plan.lineage`/`plan.id` from the YAML (the mundane plan has `lineage`). Before writing, search every `confirm_ledger.jsonl` in the repo and in git history (`git log --all -- '*/confirm_ledger.jsonl'`) for that lineage.

### M5. Paper NUMBER gate misses negative numbers, leading-dot decimals and currency (confirmed)
- **Where:** `tools/check_paper_keys.py:44`. The lookbehind `(?<![\w.\-/@#$])` excludes `-`, `.` and `$` before a digit.
- **Failure:** `check_numbers("effect was -0.42 and p was .03 and $5 and 12.5", set())` flags only `12.5`. Hard-coded effect sizes like "-0.42", p-values like "p = .03" and
  prices like "$1,850" pass the gate.
- **Fix:** Drop `-`, `.` and `$` from the lookbehind (keep `\w`, `/`, `@`, `#` for identifiers and paths), and let the number group take an optional leading `[-−]` and `\.\d+`. Add those three cases to `tests/test_check_paper_keys.py`.

### M6. Ex-ante claims with a flag column are never checked against the episode date (look-ahead)
- **Where:** `tools/ingest/contracts.py:65-68` (`episode_astrology_claims`: `ex_ante_flag="ex_ante"`, no `ex_ante=(pub, start)`), `tools/ingest/validate.py:181-189`.
- **Failure:** A row `ex_ante=yes, published_date=2021-05-01` for an episode that started in 2020 passes. `start` is None, and the "no target start" rejection runs only when `ex_ante_flag is None`.
  Its archive capture shows only the publication date, not that the claim came before the episode.
- **Fix:** Join `episode_id` to the episodes file (`tests/fixtures/ingest/episodes/` has that shape) to get the episode start, and reject `pub >= start`. Until then, reject flagged ex-ante rows whose start cannot be found.

---

## Minor

### m1. C2 shift test silently wraps events that fall before the grid
- **Where:** `mundane/aggregate.py:494-496` with `shift_test` at `:266-268`. `_check_period` (`:375-381`) checks only that the grid lies inside the period, not that it covers the events.
- **Failure:** If `grid_start` is later than an event, its index is negative and `g[event_idx]` reads from the grid's end. Probe: `shift_test(grid, np.array([-3,-2]), 2, ...)` returns a statistic with no error.
  `collect_test_data` builds the grid from `draw.period`, so the shipped path is safe; a caller-built `TestData` is not.
- **Fix:** In `_analyse` (or `_check_period`), raise unless `0 <= ev_idx < len(grid)` for every event.

### m2. Cluster-shared permutation choices lose alignment when a control label is missing
- **Where:** `mundane/aggregate.py:418` (`ctrl[i][ctrl[i] >= 0]`) with `matched_permutation` `:237`.
- **Failure:** Two events of one cluster each have 20 aligned controls. If member B's control 7 cannot be evaluated (label None), B's list shrinks to 19, so `floor(u*20)` for A and `floor(u*19)` for B no longer pick the same calendar shift.
  The cluster's dependence, which the shared column was meant to keep, is lost. Labels are rarely None today.
- **Fix:** Keep missing controls in place (carry a mask, or drop the same index across the whole cluster) instead of compacting each set's list on its own.

### m3. A missing circular shift turns the whole test "untestable", although `p_matched` is the hierarchy p
- **Where:** `mundane/aggregate.py:497-502`; offsets are empty when `n < 2*min_shift` (`:629-633`).
- **Failure:** If the explore grid is shorter than twice `min_shift_days`, every test gets p = 1 and verdict untestable, even though the omnibus p (`p_matched`) needs no grid.
- **Fix:** Fail loudly at plan check when the period is too short for C2, or report `p_shift: null` and keep `p_matched`.

### m4. `SpecCurve.p_min` understates the floor when some null medians are non-finite
- **Where:** `stats/speccurve.py:~141`. `p_min = 1/(len(offsets)+1)`, but `p_median` uses `ok.sum()+1`.
- **Fix:** `p_min = 1/(ok.sum()+1)` (as `classify.py` does with `len(ok)`).

### m5. Untracked files count as dirty in the seal but not in the markets/manifest git stamp
- **Where:** `stats/manifest.py:47` (`git status --untracked-files=no`) against `stats/seal.py:87` (`--untracked-files=all`) and `mundane/cli.py:59` (porcelain default).
- **Failure:** With only an untracked `.py` that the run imports, `markets/study.py` writes `git.dirty: false` and `check_paper_keys` passes it. The seal would call the same tree dirty.
- **Fix:** Make `git_commit()` call `seal.tree_state`, so there is one definition of dirty.

### m6. Tropical placebo and ayanamsa sensitivity keep the sidereal lagna sign
- **Where:** `markets/placebo.py:248` and `:306` (`rezodiac(..., lagna_sign)`; `rezodiac` recomputes houses as `(new_sign - lagna_sign)`).
- **Failure:** For a fixed chart with lagna in sidereal Pisces (tropical Aries), the "tropical" placebo counts tropical planet signs from a sidereal lagna. House indicators mix two zodiacs, and `bars_changed` for house columns is overstated.
- **Fix:** Re-zodiac the lagna with the same delta (at the chart's instant) before recomputing houses, or leave house columns out of these two placebos and report that.

### m7. `true_chitrapaksha` mixes a true ayanamsa into a mean-difference
- **Where:** `markets/placebo.py:57-61` (`swe.get_ayanamsa_ut` under `SIDM_TRUE_CITRA` already contains nutation, while the base is mean).
- **Failure:** The delta carries up to about 17 arcseconds of nutation. That is negligible for signs, but the docstring says nutation cancels.
- **Fix:** Fix the docstring, or take the mean form for both sides.

### m8. Nearest-neighbour declustering is fitted on the whole catalogue, confirm years included
- **Where:** `domains/earthquake.py:173` (`decluster.nearest_neighbour(cat)` on the full catalogue, then explore counts at `:191-196`).
- **Failure:** The NN threshold is fitted on data that includes 2011-2026. Adding confirm-period events changes which explore events are mainshocks in the `nn` cell, which leaks across the split. GK uses fixed windows and is unaffected.
- **Fix:** Fit the NN threshold on the explore period only (or freeze it in the plan) and apply it to both periods.

### m9. Gate hash is format-checked only
- **Where:** `domains/base.py:214-220`.
- **Failure:** `outcomes("0"*64)` succeeds. The "gate written first" rule rests on the caller's honesty.
- **Fix:** Pass the gate path and recompute its SHA-256 (and that it is committed, or at least exists) before returning outcomes.

### m10. Founding times in a DST gap or overlap are resolved silently
- **Where:** `mundane/registry.py:348-353`, `:356-362` (`naive.replace(tzinfo=ZoneInfo)` uses `fold=0`).
- **Failure:** A chart stated at 02:30 local on a spring-forward date gets a nonexistent instant, mapped without warning. The founding-time window does not absorb the hour.
- **Fix:** Detect a gap or overlap (compare `utcoffset` for fold 0 and 1) and refuse, or widen `half_window_minutes` by the DST step.

### m11. Tests that cannot fail
- `tests/test_mundane_eventsky.py:78`: `assert es.d2_confirm_recorded() is False or es.D2_CONFIRM_RECORD.exists()` is true whenever the function reports the file's existence. Assert that it returns False with no record present (use a tmp path).
- `tests/test_rules_levels.py:165`: `... or report.name == "Confirmed or refuted"`. The second operand is a constant of the L6 report, so the render check is never exercised.
- `tests/test_paperkit.py:50`: `assert res.has(key) or key == "nan_value"` is always true for the `nan_value` parameter. Split it into two explicit asserts.

---

## Checked and found correct
- `nulls.circular_shift_offsets` / `shift_null_info`: distinct offsets, exact enumeration when admissible <= draws, `p_min = 1/(n_used+1)`. Callers in `permutation`, `rates`, `classify` and `volatility.garch_x_test` report `n_used`.
- `episodes.wild_cluster_interval`: worked the inversion by hand for both enumerated and Monte Carlo branches; the order-statistic index `j = floor(aN)` and the identity padding are right. `sign_flip_test` floors match `sign_flip_p_min`.
- `volatility.past_only_volatility` (GARCH): changing returns after bar 620 leaves sigma up to 620 identical (max diff 0.0). EWMA seed and recursion are past-only.
- `mundane/dasha.py` timeline-slide argument (continuous across nakshatra edges, cycle wrap at Ashwini) and `controls.season_matched_shifts` period and gap guards.
- `mundane/charts._dignity` (varga) agrees with `rules/predicates/timing.sign_dignities` for all 9 grahas x 12 signs.
