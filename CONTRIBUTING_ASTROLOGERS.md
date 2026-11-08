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

The full definition of each predicate, with its classical source, is
printed by `astro-rules list --predicates` and lives in the docstrings of
`libs/vedic_astrology_core/rules/predicates/`.

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
