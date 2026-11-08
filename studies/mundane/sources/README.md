# Sources and open research questions

This folder holds material contributors gather for the mundane study:
citations for founding times, and the output of the research questions below.

## Folder convention

- `sources/<topic>/<YYYY-MM-DD>-<short-name>.md`: one file per pasted result.
- Each file starts with front matter: `question`, `run_by`, `date`, `tool`
  (for example the Deep Research product used), and `status` (`raw`,
  `checked`, or `rejected`).
- Paste the result unedited under a `## Raw output` heading. Add your checking
  notes under `## Checked claims`, one line per claim with the URL you opened.
  Unchecked claims stay labelled `raw`; nothing here is evidence until a human
  has opened the cited source.
- A founding time found this way goes into
  `data/countries.yaml` under `candidate_charts` with its citation.

## Open research questions for practitioners' methods

These are the four prompts the owner ran on 2026-11-08 (Gemini Deep
Research; the financial one also through Grok), reproduced verbatim. They
ask for what practitioners claim, not for what is true. Save each result
as described above.

### Prompt 1: Contemporary practitioners' mundane methods (2026-11-08)

> "Research how contemporary Vedic (Jyotish) astrologers make mundane
> predictions for countries, markets and natural disasters, using their public
> YouTube videos, podcasts, X/Twitter threads, Telegram and Facebook posts, and
> blog articles from 2015 to today, not classical texts. Cover at least 15
> named practitioners across India, Nepal, the diaspora and English-language
> channels. For each, document: which national chart they use (independence,
> constitution, coronation, or other, with the exact date, time and place they
> state), which ayanamsa, which house system, whether they use divisional
> charts and which ones, which dasha systems, how they treat eclipses,
> planetary ingresses, stations, retrogrades and conjunctions (especially
> Saturn, Mars, Rahu, Ketu), how they define the window of effect before and
> after an event, and what they count as a successful prediction. Extract their
> recurring rules as 'if X then Y within Z days' statements with the video or
> post URL and timestamp as the citation. Note disagreements between
> practitioners. Output a structured table plus a narrative summary of common
> methods and open disputes."

### Prompt 2: Natural-disaster predictions and post-hoc explanations (2026-11-08)

> "Collect and analyse public predictions and post-hoc explanations by Vedic
> and Western astrologers for earthquakes, floods, cyclones and volcanic
> eruptions from 2010 to today, from YouTube, X/Twitter, blogs and astrology
> forums. For each case, record the astrological configuration cited (eclipses,
> Saturn-Mars aspects, Rahu/Ketu axis, Kurma Chakra direction, planetary war,
> ingress of a planet into a sign, nakshatra of the Moon, specific transits to
> a national chart), the claimed window, whether the statement was made before
> or after the event, and the event it refers to with its USGS or official
> identifier. Separately document the methods astrologers describe for mapping
> sky to geography: Brihat Samhita Kurma Chakra, nakshatra-to-region tables,
> country ruling signs, capital-city charts. Summarise which configurations are
> cited most often, which are cited only after the fact, and any practitioner
> who publishes a running record of hits and misses. Provide URLs for every
> claim."

### Prompt 3: Financial astrology forecasts and track records (2026-11-08)

> "Survey how financial astrologers, both Vedic and Western, publicly forecast
> gold, silver, crude oil and stock indices, using YouTube, X/Twitter,
> Substack, Telegram and blogs from 2012 to today. Document the indicators they
> use (Jupiter and Venus transits for gold and silver, Saturn-Jupiter cycles,
> nodal axis, eclipses, Mercury retrograde, lunar phases, planetary ingress
> dates, Vimshottari dasha of a market's 'birth chart' such as the exchange
> founding chart or a country chart), the exact rules they state, the time
> horizons, and the national or exchange charts they use with date, time and
> place. Record any published track records or audits of financial astrology
> accuracy, academic or journalistic, and any known backtests. Note the
> difference between astrologers who give dates in advance and those who
> explain moves afterwards. Provide a table of rules with citations and a
> summary of what would be needed to test each rule statistically."

### Prompt 4: National charts in use for 40 countries (2026-11-08)

> "Compile the national birth charts used by practising mundane astrologers for
> 40 countries (prioritise India, Nepal, USA, China, UK, Pakistan, Bangladesh,
> Sri Lanka, Japan, Russia, Germany, France, Brazil, Australia, Canada,
> Indonesia, Iran, Israel, Ukraine, Turkey, Egypt, Nigeria, South Africa,
> Mexico, Argentina, South Korea, Taiwan, Saudi Arabia, UAE, Italy, Spain,
> Switzerland, Netherlands, Sweden, Norway, Poland, Greece, Thailand, Vietnam,
> Philippines). For each, list every chart in public use with its date, time,
> place, the event it represents (independence, constitution, republic,
> coronation, reunification, revolution), who uses it, and the source they
> cite. Where astrologers disagree, state the competing charts and the
> arguments made for each. Flag charts whose stated time is a convention
> (midnight, noon) rather than a documented moment. Output as a table suitable
> for conversion to YAML, with URLs."
## The 2026-11-08 Deep Research runs

The owner ran Prompts 1-4 above through Gemini Deep Research (and Prompt 3
also through Grok) on 2026-11-08. The prompt text above is verbatim; an
earlier version of this file carried prompts reconstructed from the topic
names, which this replaces.

### Convention for commissioned results

- The generated reports are **held locally by the owner and are not
  committed** to this repository, in any folder, raw or edited. They are
  AI-written surveys: useful as a map of where to look, not as evidence.
- Only **extracted, root-cited data** enters the repo: a candidate chart in
  `data/countries.yaml`, a rule in `rules/*/practitioner/`, a row in
  `prediction_cases.csv`, an entry in `papers/sources.bib`. Each cites the
  page, video, text or paper the claim traces to, never the survey.
- A claim the survey makes without a traceable root goes on the "untraced
  claims" list in `docs/research/SOURCES_OF_RULE_DEVELOPMENT.md` and stays out
  of the rules.
- A source carries `checked: true` only after a maintainer has opened it.

`prediction_cases.csv` lists the dated calls found so far (practitioner,
statement date, event date or window, event identifier or description,
`pre` / `post` / `claimed_pre` / `mixed`, URL), ready to be scored against
the events table.
