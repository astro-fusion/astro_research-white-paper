# Combination atlas

**Question.** Classical texts combine conditions: a planet in a sign or
house, aspecting or conjoined with another, during a given dasha. If any such
combination changed the rate of the events a study looks at, which one? The
atlas tests every combination in a grammar declared in advance, corrects for
having tested all of them, confirms the survivors on a frozen holdout, and
publishes the whole table, winners and losers.

It replaces the withdrawn 2,426-combination gold catalogue (see
[CORRECTIONS.md](../../CORRECTIONS.md)), whose combinations were chosen and
tested without a declared family, null or holdout.

**Status.** Run on the earthquake study (seed 42). Headline below; the gold
study is declared in `grammar.yaml` and not yet run.

## Headline (earthquake, seed 42)

**Nothing survives.** Of 4,977 declared candidates, 705 were testable on the
1976-2010 exploration period (128 Gardner-Knopoff mainshocks; the rest are
active too rarely to expect 3 events inside them, mostly the depth-2 and
depth-3 combinations with a dasha or a narrow placement). 25 had a nominal
p < 0.05, fewer than the 35 expected by chance alone (the discrete counts make
the test conservative). **None survived Benjamini-Yekutieli**, so none was
carried to 2011-2026 and none is confirmed.

The best exploration candidate was "Moon in house 5 from the moment's lagna
at Kathmandu" (`atl-00062`): RR 1.80 (95% CI 1.03-2.98), p = 0.005, BY
q = 1, Romano-Wolf adjusted p = 0.84. In a family of 705 tests a p of 0.005
is what the best of them is expected to look like when nothing is there.
Hansen's SPA on the confirmation period for the 20 best exploration
candidates (frozen rates as daily Poisson forecasts against a constant rate)
gives p = 0.91: none forecasts the 58 confirmation-period mainshocks better
than a constant rate.

What this means: within this grammar, this region and this catalogue, no
combination of placement, aspect, conjunction and dasha changes the rate of
mainshocks by an amount 128 events can detect after accounting for having
looked at all of them. It does not exclude small effects (the single
indicators of the earthquake study could detect only rate ratios of about
1.7 or more, and rarer combinations need far larger ones), and it says
nothing about combinations outside the grammar. A practitioner who believes
a specific combination works should register it as a rule and test it on new
data; picking it out of this table after the fact is exactly the search this
atlas corrects for. Every row is in `artifacts/atlas.csv`, including the 25
nominal results, so nobody needs to rerun the search to see them.

## What the grammar declares

`grammar.yaml` is the search space, fixed before any candidate was evaluated:

- **Clauses.** Placement of a planet (sidereal sign; whole-sign house from
  the moment's lagna at the reference location; house from the Moon;
  nakshatra group by Vimshottari lord), relation between two planets
  (Parashari whole-sign aspect, with Mars 4/8, Jupiter 5/9 and Saturn 3/10;
  conjunction within 8 degrees), and the dasha lord at level 1 or 2 of a
  reference chart.
- **Templates.** A candidate is the AND of at most three clauses, in seven
  templates (single placement, relation or dasha; placement with relation;
  placement with its own dasha; relation with a dasha of either planet;
  placement with relation and its own mahadasha). 4,977 candidates.
- **Earthquake inputs.** The Gardner-Knopoff mainshocks, region, magnitude
  threshold and hourly UTC grid of `studies/earthquake/hypothesis.yaml`;
  lagna at Kathmandu (the centre of the arc); dasha of the India chart
  (1947-08-15 00:00 IST, New Delhi). Exploration 1976-2010, confirmation
  2011-2026.
- **Test.** Two-sided event-rate ratio against a circular-shift null with
  2,000 shared offsets (seed 42). Not 10,000: thousands of candidates times
  10,000 draws is needless when 1/2001 is already below any BY threshold this
  family can reach. Candidates with fewer than 3 expected events inside or
  outside are listed as untestable and are not in the family.
- **Correction.** Benjamini-Yekutieli across every testable candidate; a
  single-step Romano-Wolf (max-|z|) adjusted p for the best one; only BY
  survivors are tested on the confirmation period (BY across them, same
  direction); Hansen's SPA scores the frozen exploration rates of the 20 best
  candidates on the confirmation period.

## Files

- `grammar.yaml`: the declared search space and test.
- `scripts/enumerate.py`: deterministic expansion with ids `atl-00001`...;
  `python studies/combinations/scripts/enumerate.py` prints the counts.
- `scripts/atlas.py`: sky arrays, clause evaluation, the shared-offset family
  test.
- `scripts/pipeline.py`: the run.
- `artifacts/atlas.csv`: **every** candidate, one row each: `id`,
  `template`, `depth`, `key`, `definition` (plain words), exposure
  (`explore_n_active_hours`, `explore_n_active_days` (active hours / 24, rounded up),
  `explore_time_fraction`), `explore_rate_ratio`, `explore_ci_low`,
  `explore_ci_high`, `explore_p_value`, `explore_q_value`, `explore_p_rw`,
  the `confirm_*` columns when a candidate was carried, and `status`
  (`untestable`, `not significant in explore`,
  `survived explore, not confirmed`, `confirmed`).
- `artifacts/results.json`, `artifacts/manifest.json`: counts, best
  candidate, SPA, provenance.

The website renders the atlas from `artifacts/atlas.csv`; keep that path and
its column names stable.

## How to run

```bash
pip install -e ".[dev]"
python studies/combinations/scripts/pipeline.py --seed 42
```

It needs the earthquake catalogue snapshot (run the earthquake pipeline once)
and builds an hourly ephemeris and lagna for 1976-2026, so it takes a few
minutes.
