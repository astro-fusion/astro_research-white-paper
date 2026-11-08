# Event types

The `event_type` in `events.jsonl` comes from the AstroFusion crawler and has
not been reviewed. To correct one, edit that row's `event_type` and set
`event_type_reviewed` to `true`. Allowed values are the keys below plus any new
type you add here first.

## Counts (825 events)

| Type | Count |
|---|---|
| Political | 469 |
| War | 205 |
| Treaty | 55 |
| Natural Disaster | 37 |
| Independence | 26 |
| Terrorism | 18 |
| Economic | 9 |
| Scientific | 2 |
| Achievement | 2 |
| Military | 1 |
| Social | 1 |

## Known misclassifications

The export report found 19 of 55 disaster-like titles not typed Natural
Disaster. The ones found by title match:

| id | Title | Date | Typed | Likely |
|---|---|---|---|---|
| wd:Q4555229 | 1868 Hayward earthquake | 1868-10-21 | War | Natural Disaster (earthquake) |
| wd:Q4554867 | 1853 Copenhagen cholera outbreak | 1853-06-11 | Political | Epidemic |
| wd:Q9254276 | 1963 Wroclaw smallpox epidemic | 1963-07-15 | Political | Epidemic |
| wd:Q834456 | 2002-2004 SARS outbreak | 2002-11-16 | Political | Epidemic |
| wd:Q81068910 | COVID-19 pandemic | 2019-11-15 | Political | Epidemic |
| wd:Q84055514 | COVID-19 pandemic in India | 2020-01-30 | Political | Epidemic |
| wd:Q87243915 | COVID-19 pandemic in South Africa | 2020-03-05 | Political | Epidemic |
| wd:Q4559640 | 1913 Binghamton Factory fire | 1913-07-22 | Political | Industrial disaster |
| wd:Q50947700 | 2018 Kemerovo fire | 2018-03-25 | Political | Industrial disaster |

Other known quirks: Wikipedia "List of" pages mix wars, treaties and
independence events, so `Political` is a catch-all; 12 titles occur more than
once; one event is dated before 1000 (680-10-10).
