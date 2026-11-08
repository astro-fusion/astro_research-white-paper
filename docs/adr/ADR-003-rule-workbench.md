# ADR-003: The rule workbench. Astrologers tune, the holdout decides.

Status: accepted 2026-11-08; delivered. Applies to `astro_research-white-paper`.

## Vision (owner's words, kept)

A tool for astrologers to test, validate and fine-tune rules so that they map
better onto scientifically accepted results. Phase 1 runs the studies as they are.
Phase 2 is the tool.

## The one rule that makes tuning honest

Every study's time axis is split once, in `hypothesis.yaml`, into an EXPLORE period
and a CONFIRM period. The workbench, the CLI and the website all operate on EXPLORE
only. CONFIRM data is never exported to the site and never read by `fit`. A rule
earns `validation.status: confirmed` from exactly one `astro-rules confirm` run per
rule version. To try again after a failed confirm, the astrologer must publish a new
rule version with a new tuning log, and the confirm period may be advanced (older
confirm data joins explore) only by a dated amendment to the study's hypothesis file.
This is pre-registration with a tuning phase, and it is what lets a positive result
survive review.

## Rule schema v2 additions (`rules/schema.json`)

```yaml
version: 2                      # bump on any change to conditions, params or strength
params:                         # tunable knobs with declared ranges; nothing else is tunable
  orb: {value: 8, min: 2, max: 12, step: 1, unit: deg}
  window_after: {value: 7, min: 0, max: 30, step: 1, unit: days}
strength:                       # optional graded output in [0, 1]; absent means binary
  combine: product | min | mean
  terms:
    - orb_closeness: {planets: [Mars, Saturn], orb: $orb}
    - dignity_weight: {planet: Mars}
    - dasha_weight: {lord: Mars, levels: [1, 2]}
tuning_log:                     # append-only, written by `astro-rules fit`
  - at: 2026-11-08T10:00:00Z
    by: "@handle"
    study: earthquake
    grid: {orb: [2..12], window_after: [0..30]}
    chosen: {orb: 6, window_after: 10}
    explore: {rate_ratio: 1.31, ci: [0.9, 1.9], p: 0.08, q_within_grid: 0.41, n_cells: 341}
    spec_curve_artifact: studies/earthquake/artifacts/speccurve_<rule>_v2.png
validation:                     # written once per version by `astro-rules confirm`
  status: unvalidated | confirmed | not_confirmed
  study: earthquake
  confirm: {rate_ratio: ..., ci: [...], p: ..., q_family: ...}
  at: ...
  commit: ...
review:                         # adversarial sign-off that the operationalisation is faithful
  - by: "@astrologer"
    at: ...
    verdict: faithful | not_faithful
    note: ...
```

## CLI (`astro-rules`)

| Command | What it does | Data it may touch |
|---|---|---|
| `fit <rule> --study <s> [--by @handle]` | grid over `params` ranges on EXPLORE; rate ratio, CI, p per cell; specification curve plot; within-grid FDR; appends a `tuning_log` entry and updates `params.*.value` to the chosen cell (never silently: prints the top 5 cells and the curve) | explore only |
| `confirm <rule> --study <s>` | one run of the frozen pipeline on CONFIRM for this rule version; stamps `validation`; refuses if the version already has a stamp | confirm, once |
| `explain`, `test`, `validate`, `list` | as today, plus `--strength` to show the graded value | any moment |
| `dose <rule> --study <s>` | dose-response: event rate across strength quintiles, trend test | explore |
| `review <rule> --by @handle --verdict ...` | appends a review entry | none |

## Stats additions (`vedic_astrology_core.stats`)

- `speccurve.py`: enumerate a declared grid of analytic choices (orb, window, catalogue, declustering, ayanamsa, node model, house system), run the estimator per cell, return the sorted curve with the share of cells crossing the null and a joint permutation p for the median.
- `power.py`: minimum detectable rate ratio for a given event count, indicator duty cycle, alpha and target power, via simulation on the same null; printed in every study README and paper.
- `controls.py`: positive control (earthquakes: semidiurnal and fortnightly tidal phase, which has a documented small real effect; floods: monsoon season flag), negative control (the same rule on a shuffled sky). A study reports its controls beside its indicators; a null is reported as "method detected the positive control at RR x" or "method did not detect it", which decides what the null is worth.
- `classify.py`: out-of-sample AUC of a regularised classifier from sky features to event days, versus the same classifier on circularly shifted sky; a rule-free test.
- `bayes.py`: posterior rate-ratio summaries under a sceptical prior (log RR ~ N(0, 0.1)) and an enthusiastic prior (N(0, 0.5)); Bayes factor against RR = 1.
- `dose.py`: trend tests across strength quintiles.

## Combination atlas (`studies/combinations/`)

A declared grammar enumerated in advance: {planet} × {sign | house-from-lagna | house-from-Moon | nakshatra group} × {aspect | conjunction within orb} × {dasha lord level 1..2}, depth ≤ 3, both directions. Thousands of candidates. Explore-period test for all, Romano-Wolf or SPA for the best, confirm on holdout, and the whole table published (winners and losers) as an atlas that the website renders. This replaces the withdrawn 2,426-combination gold catalogue with a sound version.

## Website: the workbench explorer

- Loads explore-period daily arrays only: nine sidereal longitudes, speeds, Moon tithi and nakshatra, dasha lord for the study's reference chart, declustered event days, extreme-move days. Confirm-period rows are not in the export; a test enforces the cut.
- Sliders for the rule's `params` (orb, window, strength threshold); the rate ratio, CI, Molchan point and an overlay chart update client-side with a circular-shift null of 500 draws computed in the browser (fast enough for daily arrays).
- Shows the published tuning log and validation stamp for the rule.
- "Submit this tuning" opens a prefilled GitHub issue with the YAML diff, which a maintainer turns into a versioned rule and a `fit` run. No one tunes against the holdout, because the holdout is not there.

## Predicates to add (unblocks most `needs_predicates` rules)

`planets_in_one_sign_gte`, `eclipse_within_days` (with pair interval and strength from magnitude), `eclipse_degree_transited_by`, `kurma_direction` (Brihat Samhita ch. 14, with the starting-nakshatra convention as a parameter because practitioners dispute it), `moon_mandala` (ch. 32 Vayu/Agni/Indra/Varuna, lists checked against the Bhat translation), `planet_distance_au_lte`, `samvatsara_is`, `month_paksha`, `nakshatra_on_tithi`, `lord_of_house_in`, `malefic_in_house`, `lords_conjoined`, `afflicted_element`, `cycle_resonance` (years since a reference conjunction modulo period), `conjunction_or_mutual_aspect`.

## Engine fix

`get_ayanamsa()` returns the mean ayanamsa while positions use the true one (nutation included), a 17″ mismatch; expose both and make the sidereal path use one declared value.

## Work packages

| WP | Scope | Repo | Model |
|---|---|---|---|
| W-1 | schema v2, params, strength, tuning_log, validation, review; `fit`/`confirm`/`dose`/`review`; new predicates; ayanamsa fix; contributor guide update | public | Opus |
| W-2 | stats additions; controls applied to the earthquake study; combination atlas; power in every README | public | Opus |
| W-3 | workbench explorer; explore-only export with the holdout cut enforced; principles browser shows version, tuning log, validation, reviews; combination atlas page | public | Opus |

## Outcome

Delivered 2026-11-08 (commit range `d778c32..HEAD`).

| WP | What landed | Commits |
|---|---|---|
| W-1 | Rule schema v2 (params, strength, tuning log, validation, review); `fit`/`confirm`/`dose`/`review`; study adapter and grid evaluator; mundane predicates batch 1 and 2; ayanamsa fix; worked tune-and-validate session | be3d74a, 7bcea26, 68aa8a3, 96b3264, 279a15f, cde45bd, d8c107f, 64b9e2e |
| W-2 | Specification curves, power, controls, classifier, Bayes, dose-response; earthquake controls; combination atlas; power sections in READMEs | 7b5bb48, 4acdc21, 375585f, 6c2c9c3 |
| W-3 | Explore-only workbench export with the holdout cut enforced; workbench explorer; atlas page; principles v2 with validation strip | f4bbaa1, 83182a5, 48f94d7 |

Headline numbers:

- 121 rules at schema v2; 104 params created; 15 new predicates.
- 17 of 64 blocked rules activated.
- 34 rules evaluable in the browser workbench.
- Atlas: 4,977 candidates, 705 testable, 0 survivors.
- Earthquake positive control (tidal) not detected; minimum detectable rate ratios 1.4 to 3.5.
- Classifier AUC 0.52 versus 0.49 shuffled.

Open items:

- `fit` uses a daily grid while the earthquake study registered hourly.
- `eclipse_strong_delayed_impact` needs an offset eclipse window.
- 6 mundane rules are still blocked.
- BS 32 mandala lists are unverified against the Bhat translation.
- Strength terms are not evaluated in the browser.
- The gold atlas is declared but not run.
