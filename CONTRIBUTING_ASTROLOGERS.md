# Contributing rules as an astrologer

You can add an astrological principle to this project without writing any
code. A principle becomes a **rule**: one short YAML file in `rules/` that
says what the sky must look like, where the idea comes from, and two or more
dates on which you know whether it holds. The engine then tests it against
recorded events (earthquakes, floods, gold prices, national events) and
reports the result as found: positive, null or mixed.

If you would rather not use GitHub pull requests at all, skip to
[Propose a rule without a pull request](#propose-a-rule-without-a-pull-request).

All positions are **sidereal (Lahiri ayanamsa)**, houses are **whole sign**
(bhava = rashi), Rahu and Ketu are the **mean nodes** unless a rule says
`node_model: true`, and dasha years are Julian years of 365.25 days.

## A worked example, from idea to `astro-rules test`

The idea: *"Gold tends to rise for a month after Jupiter is strong in a
kendra from the Moon: in a kendra, not combust, and in its own or
exaltation sign."*

### 1. Write the rule

Create `rules/financial/gold.jupiter_kendra_from_moon.yaml`:

```yaml
# yaml-language-server: $schema=../schema.json
id: financial.gold.jupiter_kendra_from_moon
name: Jupiter strong in a kendra from the Moon (Gaja Kesari variant)
domain: financial
claim: Gold tends to rise in the 30 days after this configuration begins.
source:
  text: Brihat Parashara Hora Shastra
  chapter: "36"
  verse: "3-4"
author: "@your-handle"
tier: classical
conditions:
  all:
    - planet: Jupiter
      in_kendra_from: Moon
    - planet: Jupiter
      not: combust
    - planet: Jupiter
      dignity_in: [own, exaltation]
window: {unit: days, before: 0, after: 30}
expected_effect: {series: gold_usd, direction: up}
reference_cases:
  - moment: "2014-09-01T06:00:00Z"
    expect: fires
    note: Jupiter exalted in Cancer 16, 10th from the Moon in Libra, 28 deg from the Sun.
  - moment: "2014-07-20T06:00:00Z"
    expect: silent
    note: Jupiter exalted and 4th from the Moon in Aries, but combust (3.4 deg from the Sun).
```

What each part means:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique, lowercase, with dots: `domain.topic.name`. |
| `name`, `claim` | yes | The rule's name and what it predicts, in plain words. |
| `domain` | yes | `financial`, `seismic`, `mundane`, `natal` or `general`. |
| `source` | yes | `{text, chapter, verse}` for a classical text, `{url}` for a web source, or `{app_registry, id}` for an application's rule list. `edition` and `note` are optional. |
| `author` | yes | Your name or GitHub handle. |
| `tier` | yes | `classical` or `experimental` (see [Tiers](#tiers)). |
| `conditions` | yes | The boolean tree of predicates (see the [vocabulary](#predicate-vocabulary)). |
| `window` | no | When the effect is expected: `{unit, before, after}`. |
| `expected_effect` | no | `{series, direction}` or `{event, direction}` for the statistics. |
| `reference_cases` | yes | Moments where you know the rule fires or stays silent. |
| `natal` | no | A default natal chart (`{moment, place}`) for dasha and transit rules. |
| `status` | no | `active` (default), `needs_verification` or `needs_predicates`. |
| `notes` | no | Anything else, kept with the rule. |

Conditions combine with `all` (every item), `any` (at least one), `not`
(the opposite) and `at_least: {n: 2, of: [...]}`, nested as deep as you
like. A condition can be written in full:

```yaml
in_kendra_from: {planet: Jupiter, from: Moon}
```

or in the short form used above (`planet:` plus one predicate, and
`not: <predicate>` for a negation). Sanskrit names work too: `Guru`,
`Chandra`, `Mesha`, `Aswini`.

**Moments always carry a time zone**: `2014-09-01T06:00:00Z` (UTC) or
`2014-09-01T11:45:00+05:45` (Kathmandu). A rule that uses the Lagna, houses
from the Lagna or sunrise also needs a `place: {lat, lon, tz}` on each
reference case, for example `{lat: 27.7172, lon: 85.324, tz: Asia/Kathmandu}`.
A rule that uses a dasha or a transit to a natal chart needs
`natal: {moment, place}` on each case (or once, on the rule).

### 2. Check the file

```console
$ astro-rules validate rules/financial/gold.jupiter_kendra_from_moon.yaml
1 rules valid
```

Mistakes are reported with the file, line, field and a suggestion:

```console
$ astro-rules validate rules/seismic/my_rule.yaml
rules/seismic/my_rule.yaml:10: conditions.all[0].conjunct_within.orb_degs: unknown field 'orb_degs'. Did you mean 'orb'? Allowed: planets, orb
rules/seismic/my_rule.yaml:11: conditions.all[1]: unknown predicate 'house_frm'. Did you mean 'in_house_from'? ...
rules/seismic/my_rule.yaml:12: conditions.all[2].in_sign.planet: unknown planet or Lagna 'Jupitor'. Did you mean 'Jupiter'? ...
rules/seismic/my_rule.yaml:13: conditions.all[3].graha_drishti: Mars casts only the 4th, 7th, 8th aspect(s); 10th is not one
```

The first line of the file connects editors such as VS Code (with the YAML
extension) to `rules/schema.json`, so you get completion and red underlines
while typing.

### 3. Run the reference cases

```console
$ astro-rules test rules/financial/gold.jupiter_kendra_from_moon.yaml
PASS financial.gold.jupiter_kendra_from_moon (2 cases)

cases: 2 passed, 0 failed, 0 known (needs_verification); rules skipped: 0 (needs_predicates)
```

If a case does not match, the engine shows why, condition by condition:

```console
FAIL financial.gold.jupiter_kendra_from_moon case 0 (2014-07-30T06:00:00+00:00): expected fires, got silent
  [FAILS] all of: 1 of 3 held
    [FAILS] in_kendra_from(planet=Jupiter, from=Moon): Jupiter is in Cancer 9.0 deg, 12th from Moon in Leo, which is not a kendra (1, 4, 7, 10)
    [FAILS] not
      [HOLDS] combust(planet=Jupiter): Jupiter is 4.0 deg from the Sun; its combustion orb is 11 deg
    [HOLDS] dignity_in(planet=Jupiter, dignities=[own, exaltation]): Jupiter in Cancer 9.0 deg is exaltation (sign lord Moon of Cancer)
```

Either the date was wrong (fix the case) or the rule is not what you meant
(fix the conditions). Check the date in JHora before deciding (see the
[checklist](#verify-in-jhora-checklist)).

### 4. Explore any date

```console
$ astro-rules explain financial.gold.jupiter_kendra_from_moon 2014-07-20T11:45:00+05:45
financial.gold.jupiter_kendra_from_moon is SILENT
  [FAILS] all of: 2 of 3 held
    [HOLDS] in_kendra_from(planet=Jupiter, from=Moon): Jupiter is in Cancer 6.8 deg, 4th from Moon in Aries, which is a kendra (1, 4, 7, 10)
    [FAILS] not
      [HOLDS] combust(planet=Jupiter): Jupiter is 3.4 deg from the Sun; its combustion orb is 11 deg
    [HOLDS] dignity_in(planet=Jupiter, dignities=[own, exaltation]): Jupiter in Cancer 6.8 deg is exaltation (sign lord Moon of Cancer)
```

Add `--lat 27.7172 --lon 85.324 --tz Asia/Kathmandu` for rules that use the
Lagna, and `--natal-moment 1947-08-15T00:00:00+05:30 --natal-lat 28.6139
--natal-lon 77.209 --natal-tz Asia/Kolkata` for dasha and transit-to-natal
rules. `astro-rules list --domain seismic` lists rules and
`astro-rules list --predicates` prints the vocabulary below.

To install the command: `pip install -e .` in the repository, once.

## Predicate vocabulary

Every condition is one of these predicates. The list is closed: an unknown
name is an error, not a silent "false". If you need a new one, ask for it
(see below); a developer adds it in Python with tests.

`planet` accepts the nine grahas; where the table says *point*, `Lagna` is
also allowed. `signs`, `nakshatras`, `lords` and `houses` take one value or
a list.

| Predicate | Kind | Holds when | Example |
|---|---|---|---|
| `in_sign` | placement | the planet (or the Lagna) occupies one of the listed sidereal signs | `{in_sign: {planet: Jupiter, signs: [Cancer]}}` |
| `in_house` | placement | the planet is in one of the listed houses counted from the Lagna (needs a place) | `{in_house: {planet: Saturn, houses: [10]}}` |
| `in_house_from` | placement | the planet is in one of the listed houses counted from another point (`houses: [1]` = same sign) | `{in_house_from: {planet: Moon, from: Sun, houses: [3]}}` |
| `in_kendra_from` | placement | the planet is in a kendra (1st, 4th, 7th or 10th) from the point, counted by sign | `{in_kendra_from: {planet: Jupiter, from: Moon}}` |
| `in_trikona_from` | placement | the planet is in a trikona (1st, 5th, 9th) from the point | `{in_trikona_from: {planet: Venus, from: Lagna}}` |
| `in_nakshatra` | placement | the point lies in one of the listed nakshatras | `{in_nakshatra: {planet: Saturn, nakshatras: [Krittika]}}` |
| `nakshatra_lord_is` | placement | the lord of the point's nakshatra is one of the listed planets | `{nakshatra_lord_is: {planet: Moon, lords: [Saturn]}}` |
| `dignity_in` | placement | the planet's dignity is one of own, exaltation, debilitation, moolatrikona, friend, enemy, neutral | `{dignity_in: {planet: Jupiter, dignities: [own, exaltation]}}` |
| `varga_sign` | placement | the point is in one of the listed signs of the D-n chart (D1 to D60, the 16 Shodasavargas) | `{varga_sign: {planet: Venus, varga: 9, signs: [Pisces]}}` |
| `longitude_between` | placement | the point's sidereal longitude lies in [start, end) degrees | `{longitude_between: {planet: Sun, start: 141.5, end: 144.5}}` |
| `combust` | relation | the planet is within its combustion orb of the Sun (Moon 12, Mars 17, Mercury 14/12 R, Jupiter 11, Venus 10/8 R, Saturn 15) | `{combust: {planet: Mercury}}` |
| `retrograde` | relation | the planet moves backwards (vakri) | `{retrograde: {planet: Saturn}}` |
| `conjunct_within` | relation | the two planets are within `orb` degrees of longitude | `{conjunct_within: {planets: [Mars, Ketu], orb: 13}}` |
| `separation_within` | relation | the arc between two planets is within `orb` of `angle` (180 opposition, 90 square) | `{separation_within: {planets: [Jupiter, Saturn], angle: 180, orb: 10}}` |
| `graha_drishti` | relation | the planet casts a whole-sign aspect on the target: all the 7th; Mars also 4th and 8th; Jupiter 5th and 9th; Saturn 3rd and 10th | `{graha_drishti: {planet: Mars, target: Ketu, aspects: [8]}}` |
| `planet_speed_below` | relation | the planet moves slower than `speed` degrees per day (near its station) | `{planet_speed_below: {planet: Saturn, speed: 0.05}}` |
| `dasha_lord_is` | time | the natal chart's running Vimshottari lord at `level` (1 maha, 2 antar, 3 pratyantar) is listed (needs natal) | `{dasha_lord_is: {level: 1, lords: [Saturn]}}` |
| `antardasha_lord_is` | time | the running antardasha (bhukti) lord is listed (needs natal) | `{antardasha_lord_is: {lords: [Rahu]}}` |
| `moon_phase` | time | the paksha (`waxing`, `waning`, `new`, `full`) or the tithi (1-30) matches | `{moon_phase: {phase: full}}` |
| `weekday_lord_is` | time | the lord of the vara, counted sunrise to sunrise when a place is given, is listed | `{weekday_lord_is: {lords: [Saturn]}}` |
| `transit_in_house_from_natal` | mundane | the transiting planet is in one of the houses from a natal point (Lagna by default) | `{transit_in_house_from_natal: {planet: Saturn, from: Moon, houses: [8]}}` |
| `transit_conjunct_natal` | mundane | the transiting planet is within `orb` degrees of a natal point | `{transit_conjunct_natal: {planet: Saturn, natal_point: Sun, orb: 3}}` |
| `eclipse_in_sign` | mundane | a solar or lunar eclipse falls in the window and in the listed signs or nakshatras | `{eclipse_in_sign: {kind: solar, signs: [Leo], days_before: 15, days_after: 15}}` |
| `ingress` | mundane | the planet enters a sign (sankranti for the Sun) within the window | `{ingress: {planet: Sun, signs: [Aries], days_before: 1}}` |
| `planets_in_one_sign_gte` | mundane | at least `count` of `bodies` (default the seven visible grahas) share one sign (Brihat Jataka 12 sankhya yogas; the pancha graha cluster) | `{planets_in_one_sign_gte: {count: 5}}` |
| `eclipse_within_days` | mundane | an eclipse falls in the window; optionally paired with one of the other kind within `pair_within_days`, and of at least `min_magnitude` (BS 5) | `{eclipse_within_days: {days_before: 30, days_after: 30, pair_within_days: 16}}` |
| `eclipse_degree_transited_by` | mundane | a listed planet stands within `orb` of `angles` (0 conjunction, 180 opposition) from the degree of an eclipse in the last `lookback_days` | `{eclipse_degree_transited_by: {planets: [Mars, Saturn], orb: 3, angles: [0, 180]}}` |
| `kurma_direction` | mundane | the point's nakshatra lies in a listed Kurma Chakra division (BS 14; `start: krittika` as the text, `ashwini` as the practitioner table) | `{kurma_direction: {planet: Saturn, directions: [north], start: krittika}}` |
| `moon_mandala` | mundane | the Moon's nakshatra is in a listed earthquake circle: vayu, agni, indra, varuna (BS 32) | `{moon_mandala: {mandalas: [agni]}}` |
| `planet_distance_au_lte` | mundane | the planet's geocentric distance is at most `au` astronomical units (BS 6 reads a large, bright Mars) | `{planet_distance_au_lte: {planet: Mars, au: 0.45}}` |
| `samvatsara_is` | time | the sixty-year samvatsara (BS 8; luni-solar, Prabhava = 1987-88) is listed | `{samvatsara_is: {names: [Krodhi]}}` |
| `month_paksha` | time | the amanta lunar month (named by the Sun's sign at its new Moon) and optionally its paksha and adhika status match | `{month_paksha: {months: [Ashadha], paksha: shukla}}` |
| `nakshatra_on_tithi` | time | the Moon is in a listed nakshatra on a listed tithi, optionally of a listed month (BS 24, 26) | `{nakshatra_on_tithi: {nakshatras: [Rohini], tithis: [19], months: [Ashadha]}}` |
| `lord_of_house_in` | placement | the lord of `house` (whole sign from the Lagna or `from`) sits in one of `houses`; `chart: natal` reads the natal chart (BPHS 24) | `{lord_of_house_in: {house: 4, houses: [12], chart: natal}}` |
| `malefic_in_house` | placement | at least `count_gte` natural malefics (Sun, Mars, Saturn, Rahu, Ketu) occupy the listed houses | `{malefic_in_house: {houses: [6]}}` |
| `lords_conjoined` | placement | the lords of the listed houses share one sign, optionally one of `in_houses` (BPHS 41) | `{lords_conjoined: {houses: [6, 1]}}` |
| `afflicted_element` | mundane | at least `count_gte` malefics occupy signs of the element (fire, earth, air, water) | `{afflicted_element: {element: fire, count_gte: 2}}` |
| `cycle_resonance` | time | the years since `reference`, modulo `period_years`, are within `tolerance_years` of a return | `{cycle_resonance: {reference: "2020-12-21T18:20:00Z", period_years: 60, tolerance_years: 3}}` |
| `conjunction_or_mutual_aspect` | relation | the planet shares a sign with (or, with `orb`, is within `orb` of) any of `others`, or they aspect each other | `{conjunction_or_mutual_aspect: {planet: Mars, others: [Saturn, Jupiter]}}` |

The full definition of each predicate, with its classical source, is
printed by `astro-rules list --predicates` and lives in the docstrings of
`libs/vedic_astrology_core/rules/predicates/`.

## Tune and validate a rule

### The principle: tune on one period, decide on another

Every study (earthquakes, gold, silver) splits its years once, in its
`hypothesis.yaml`, into an **explore** period and a **confirm** period. For
the earthquake study explore is 1976-2010 and confirm is 2011-2026.

- You may try as many orbs, windows and thresholds as you like on the
  explore period. That is tuning, and it is allowed.
- The confirm period is the exam. `astro-rules confirm` runs your rule on it
  **once per rule version**, with the values you chose, and writes the
  result into the rule file. Nobody, including you, gets a second look at
  the same version.
- If the exam is failed, the rule does not get retried quietly. You start a
  new version, tune again on explore, and that new version gets its own
  single confirm run. The old result stays in the file.

The reason is simple: if you try twenty orbs and keep the best, the best
will look good by luck. A period the tuning never saw is the only fair test
of whether it was luck. This is pre-registration with a tuning phase, and it
is what lets a positive result survive review.

### Declare what may be tuned

Only `params` are tunable. Each has a value and the range `fit` may try;
conditions refer to it as `$name`:

```yaml
version: 2                  # bump on any change to conditions, params or strength
params:
  orb: {value: 13, min: 3, max: 20, step: 1, unit: deg}
conditions:
  conjunct_within:
    planets: [Mars, Ketu]
    orb: $orb
```

`astro-rules validate` rejects a `$name` that is not declared, a declared
parameter that is never used, a value outside its range, and a range whose
ends would make the rule invalid (an orb above 30 degrees, for example).

### A worked session: `fit`, then `confirm`

This is the real output for the Mars-Ketu conjunction rule on the earthquake
study (the result is now in `rules/seismic/mangal_ketu_primary.yaml`):

```console
$ astro-rules fit seismic.mangal_ketu_primary --study earthquake --by @astro-research
fit seismic.mangal_ketu_primary v2 on earthquake: EXPLORE 1976-01-01 to 2010-12-31 only
events: 128 declustered (Gardner-Knopoff) earthquakes per day; grid steps: 12784; cells: 18; alternative: greater; null: circular shift, min shift 767 steps, 2000 draws

top 5 cells (p from the circular-shift null; q = BH within the grid)
  cell                                      RR            95% CI        p        q     on
  orb=15                                  1.09     [0.532, 2.03]    0.457    0.966   7.9%
  orb=14                                  1.07     [0.502, 2.05]    0.479    0.966   7.3%
  orb=16                                  1.01     [0.489, 1.87]    0.521    0.966   8.5%
  orb=19                                 0.972     [0.502, 1.73]    0.588    0.966  10.4%
  orb=12                                 0.934     [0.368, 1.98]    0.592    0.966   5.8%

specification curve: median RR 0.891, joint circular-shift p 0.607 (200 draws); 0% of cells exclude RR = 1
specification curve: studies/earthquake/artifacts/speccurve_seismic.mangal_ketu_primary_v2.png
chosen: orb = 15
wrote rules/seismic/mangal_ketu_primary.yaml: params updated, tuning_log entry appended
```

How to read it:

- **RR** is the rate ratio: earthquakes per day while the rule holds,
  divided by earthquakes per day while it does not. 1 means no difference.
- **p** comes from shifting the rule's on/off pattern in time against the
  fixed earthquake dates thousands of times (by at least two years, so the
  shifted pattern is unrelated to the sky), which keeps aftershock clusters
  and the rule's own rhythm intact.
- **q** corrects p for having tried 18 orbs. A tuned cell is only
  interesting if its q is small.
- **on** is the share of days the rule holds.
- The **specification curve** (the PNG) plots every cell's RR with its
  interval. A real effect shows as a curve that sits above 1 for most
  reasonable orbs, not one lucky point.

`fit` set `orb` to 15 and appended this to the file:

```yaml
tuning_log:
  - at: '2026-11-08T07:34:31Z'
    by: '@astro-research'
    study: earthquake
    version: 2
    grid:
      orb: {min: 3, max: 20, step: 1}
    chosen: {orb: 15}
    explore:
      rate_ratio: 1.09482
      ci: [0.531911, 2.03187]
      p: 0.456772
      q_within_grid: 0.965517
      n_cells: 18
      n_events: 128
      period: ['1976-01-01', '2010-12-31']
```

Then the single exam on the confirm period:

```console
$ astro-rules confirm seismic.mangal_ketu_primary --study earthquake
confirm seismic.mangal_ketu_primary v2 on earthquake: one frozen run on CONFIRM 2011-01-01 to 2026-10-31
events: 58; RR 0.988 [0.308, 2.45]; p 0.6; q 0.6 in this rule alone (not in the study's registered family)
validation.status: not_confirmed
wrote rules/seismic/mangal_ketu_primary.yaml: validation stamped for v2
```

The stamp in the file records the numbers, the time and the git commit:

```yaml
validation:
  status: not_confirmed
  version: 2
  study: earthquake
  confirm:
    period: ['2011-01-01', '2026-10-31']
    n_events: 58
    direction: greater
    rate_ratio: 0.988133
    ci: [0.308227, 2.45413]
    p: 0.59984
    q_family: 0.59984
    family: this rule alone (not in the study's registered family)
    family_size: 1
  at: '2026-11-08T07:34:37Z'
  commit: 48f94d7fb96290ca3779dd2601602721b6a037ba
```

`confirmed` needs q below the study's alpha (0.05) with the rate ratio in
the direction the rule predicts (`expected_effect.direction`). When the
study's `hypothesis.yaml` lists the rule in its registered family, q is
corrected across that whole family; otherwise the rule is a family of one.

### After a failed confirm

A second confirm on the same version is refused:

```console
$ astro-rules confirm seismic.mangal_ketu_primary --study earthquake
astro-rules confirm: seismic.mangal_ketu_primary v2 was already confirmed on earthquake at 2026-11-08 07:34:37+00:00 (not_confirmed); a new attempt needs a new version: run astro-rules fit --new-version (or change the rule and bump 'version'), then confirm the new version
```

and so is more tuning of the stamped version:

```console
$ astro-rules fit seismic.mangal_ketu_primary --study earthquake --by @astro-research
astro-rules fit: seismic.mangal_ketu_primary v2 already has a confirm stamp (not_confirmed); tuning it again needs a new version: rerun with --new-version
```

`fit --new-version` raises `version` by one, moves the old stamp to
`validation_history` (it is never deleted), tunes the new version on explore
and leaves it `unvalidated`, ready for its own single confirm. Think before
you do this: each new version is another try, and readers see every try in
the file. A better reason for a new version is a better reading of the
source (a corrected condition), not a different orb.

The confirm period itself only moves by a dated amendment to the study's
`hypothesis.yaml` (older confirm years join explore, a newer stretch becomes
confirm), and every rule then confirms again on the new period.

### Graded strength and `dose`

A rule may say how strongly it holds, from 0 to 1, with a `strength` block.
The terms are `orb_closeness` (1 at an exact conjunction, 0 at the orb),
`aspect_closeness` (the same around an angle), `dignity_weight` (uccha bala:
1 at deep exaltation, 0 at deep debilitation), `dasha_weight` (1 when the
lord runs the mahadasha, 1/2 the antardasha) and `eclipse_magnitude` (the
largest eclipse magnitude in a window); `combine` is `product`, `min` or
`mean`:

```yaml
strength:
  combine: product
  terms:
    - orb_closeness: {planets: [Mars, Saturn], orb: $orb}
```

`astro-rules explain <rule> <moment> --strength` prints the value at one
moment. `dose` asks the question a real effect should answer: is the event
rate higher when the configuration is stronger? (explore period only):

```console
$ astro-rules dose seismic.mangal_shani_malefic --study earthquake
dose seismic.mangal_shani_malefic v3 on earthquake: EXPLORE 1976-01-01 to 2010-12-31 only
silent steps: 11461, events 118, rate 10.30 per 1000 steps
  quintile    strength  steps events  per 1000  RR vs silent           95% CI
         1   0.00-0.18    265      2      7.55         0.733   [0.0877, 2.71]
         2   0.18-0.37    264      4     15.15          1.47    [0.394, 3.87]
         3   0.37-0.59    265      1      3.77         0.367   [0.0092, 2.08]
         4   0.59-0.79    264      1      3.79         0.368  [0.00924, 2.09]
         5   0.79-1.00    265      2      7.55         0.733   [0.0877, 2.71]
trend: cochran_armitage z -0.673, p 0.501 (independent days); Kendall tau-b -0.0119, scipy p 0.598; circular-shift p 0.699 (999 shifts, one-sided: rate rises with strength)
```

Here the closest Mars-Saturn conjunctions are no more seismic than the
widest ones. Trust the circular-shift p: earthquakes cluster in time, so the
two p-values that assume independent days are too optimistic.

### The review sign-off

Statistics cannot tell whether the YAML says what the text says. A second
astrologer reads the rule against its source and signs:

```console
$ astro-rules review seismic.mangal_ketu_primary --by @your-handle --verdict not_faithful --note "BS 17 is on planetary war, not earthquakes; the citation does not support the claim"
seismic.mangal_ketu_primary v2: review by @your-handle (not_faithful) appended
```

```yaml
review:
  - by: '@your-handle'
    at: '2026-11-08T07:36:07Z'
    verdict: not_faithful
    note: BS 17 is on planetary war, not earthquakes; the citation does not support the claim
    version: 2
```

Reviews are appended, never edited. A rule whose encoding has a `faithful`
review and a `confirmed` stamp on the same version is the strongest claim
this project makes; a `not_faithful` review means the test, whatever it
found, was not a test of the source.

### New predicates

Each was added with its classical source in the docstring
(`astro-rules list --predicates`) and tests on known dates. One example
each:

`planets_in_one_sign_gte`: five or more grahas in one sign (all seven
were in Capricorn on 5 February 1962).

    {planets_in_one_sign_gte: {count: 5}}

`eclipse_within_days`: an eclipse within 30 days either side, with a
partner of the other kind within 16 days (an eclipse pair).

    {eclipse_within_days: {days_before: 30, days_after: 30, pair_within_days: 16}}

`eclipse_degree_transited_by`: Mars or Saturn conjunct or opposite the
degree of an eclipse of the last year, within 3 degrees.

    {eclipse_degree_transited_by: {planets: [Mars, Saturn], orb: 3, angles: [0, 180], lookback_days: 365}}

`kurma_direction`: Saturn's nakshatra in the northern division of the
Kurma Chakra, Brihat Samhita 14 (start the wheel at `krittika`, as the
text, or `ashwini`, as some practitioners; see `DISPUTES.md`).

    {kurma_direction: {planet: Saturn, directions: [north], start: krittika}}

`moon_mandala`: the Moon in an Agni-mandala nakshatra (Brihat Samhita 32).

    {moon_mandala: {mandalas: [agni]}}

`planet_distance_au_lte`: Mars within 0.45 au of the Earth.

    {planet_distance_au_lte: {planet: Mars, au: 0.45}}

`samvatsara_is`: the sixty-year samvatsara (luni-solar; 2024-25 is Krodhi).

    {samvatsara_is: {names: [Krodhi]}}

`month_paksha`: the bright half of the lunar month Ashadha (amanta).

    {month_paksha: {months: [Ashadha], paksha: shukla}}

`nakshatra_on_tithi`: the Moon in Rohini on the 4th tithi of the dark
half (tithi 19) of Ashadha.

    {nakshatra_on_tithi: {nakshatras: [Rohini], tithis: [19], months: [Ashadha]}}

`lord_of_house_in`: the natal 4th lord in the 12th.

    {lord_of_house_in: {house: 4, houses: [12], chart: natal}}

`malefic_in_house`: a natural malefic in the 6th from the Lagna.

    {malefic_in_house: {houses: [6]}}

`lords_conjoined`: the 6th and 1st lords in one sign.

    {lords_conjoined: {houses: [6, 1]}}

`afflicted_element`: two or more malefics in fire signs.

    {afflicted_element: {element: fire, count_gte: 2}}

`cycle_resonance`: within 3 years of a sixty-year return of the 2020
Jupiter-Saturn conjunction.

    {cycle_resonance: {reference: "2020-12-21T18:20:00Z", period_years: 60, tolerance_years: 3}}

`conjunction_or_mutual_aspect`: Mars sharing a sign with, or in mutual
aspect with, Saturn or Jupiter.

    {conjunction_or_mutual_aspect: {planet: Mars, others: [Saturn, Jupiter]}}

With these, 17 of the 64 rules that were waiting for predicates now have
conditions and reference cases (see `notes.encoding` in each for the
reading chosen where the source was ambiguous).

## Tiers

- **classical**: the `source` names a text **and** a chapter (a verse is
  strongly encouraged, with the edition in `edition`). A classical rule needs
  at least one reference case that fires and one that is silent. Only
  classical rules are used for confirmatory claims in the papers.
- **experimental**: everything else: modern or folk claims, an
  application's rule list, or a citation that does not actually support the
  claim (say so in `source.note`). At least one reference case is needed.
  Experimental rules are tested and reported, always labelled exploratory.

The tier is checked: `tier: classical` without `text` and `chapter` is an
error.

**Status** says how ready the rule is:

- `active`: conditions written and reference cases pass.
- `needs_verification`: a reference case does not pass and nobody has yet
  decided whether the case or the rule is wrong. `astro-rules test` lists it
  but does not fail. Paste the failing explain output into `notes`.
- `needs_predicates`: the vocabulary cannot express the rule yet. Write
  `conditions: null`, keep the original wording in
  `notes.original_condition`, and list what is missing in
  `notes.missing_predicates`. Such rules must be `experimental` and are
  skipped by `astro-rules test`.

## Verify in JHora checklist

Reference cases are only as good as the dates in them. Before a rule moves
to `active`, check each case in JHora (or another program you trust) with
the same conventions as this engine:

1. **Ayanamsa**: Lahiri (Chitrapaksha). JHora: *Preferences, Calculation:
   Ayanamsa = Lahiri*.
2. **Nodes**: mean Rahu and Ketu (unless the rule sets `node_model: true`).
3. **Houses**: whole sign (rashi = bhava) for every house count.
4. **Time zone**: the moment's UTC offset matches the place and the date
   (watch daylight saving and historical offsets such as India +05:30 or
   Nepal +05:30 before 1986).
5. **Place**: latitude and longitude of the actual place, east positive.
6. **Signs and nakshatras**: each planet's sign, degree and nakshatra agree
   with JHora to within a few arc-minutes; anything near a sign or
   nakshatra edge is a weak case, so pick a date further from the edge.
7. **Combustion**: compare the Sun-planet distance with the orbs above
   (JHora's own combustion list uses different orbs; compare the distance).
8. **Aspects**: whole-sign graha drishti, not degree aspects.
9. **Dasha**: Vimshottari from the Moon's nakshatra, 365.25-day years; the
   running maha/antar/pratyantar lords match JHora's dasha screen.
10. **Varga**: D-n signs from JHora's divisional chart screens with the
    traditional Parashara methods.
11. **Record it**: put `verified_with: "JHora 8.0, Lahiri, mean node"` on
    the case. Migrated rules carry `verified_with: astro-research engine ...;
    not yet checked in JHora`, which means the case is only engine
    self-consistency until someone does this check.

## Propose a rule without a pull request

Open an issue with the **Propose a rule** template
(`.github/ISSUE_TEMPLATE/propose-rule.yml`, the *New issue* button on
GitHub). It asks for the same things as the YAML file: name, claim, domain,
source with chapter and verse, the condition in your own words, the time
window, and dates on which it should fire and stay silent. A maintainer
turns it into a rule file, runs `astro-rules test`, and links the result in
the issue. You can also ask there for a predicate the vocabulary lacks.
