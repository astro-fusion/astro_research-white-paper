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

Run each prompt in a Deep Research tool, then save the result as described
above. They ask for what practitioners claim, not for what is true.

1. **Practitioners' methods on social media.** Which mundane-astrology methods
   (transits to national charts, eclipses, ingresses, Mars-Saturn
   configurations) do practitioners describe on YouTube, X, Instagram and
   blogs? For each method, list the exact rule as stated, who states it, and a
   link. Do not judge accuracy.
2. **Earthquake and flood predictions and after-the-fact explanations.** Find
   dated, public predictions of earthquakes or floods made by astrologers
   before the event, and separately the explanations offered afterwards. Record
   the posting date, the claim, the event it was matched to, and whether the
   prediction named place, date window and size.
3. **Financial astrology forecasts.** Find published forecasts for equity
   indices, gold, silver or currencies with a dated posting, the indicators
   used and the stated window, so they can be pre-registered and scored later.
4. **National charts in use, and the disputes.** For each country, which
   founding chart (date, time, place) do practitioners use? Where charts are
   disputed (India: midnight vs other times; USA: Sibly vs alternatives), list
   each candidate with its source and the argument for it.

## The 2026-11-08 Deep Research runs

The owner ran the four questions above through Gemini Deep Research (and the
financial one also through Grok) on 2026-11-08. The exact prompt text was not
available when this section was written, so the prompts below are
reconstructed from the topic names; replace them with the verbatim text when
it is to hand.

1. *Practitioners' methods on social media, 2015 to today.* "Survey Vedic
   mundane astrologers active on YouTube, X, Instagram, Substack and blogs
   from 2015 to today. For each, record the national chart they use (date,
   time, place), ayanamsa, house system, dasha system and secondary charts,
   and every concretely stated predictive rule with a link and a date. Record
   disagreements between practitioners. Do not judge accuracy."
2. *Earthquake and flood predictions and post-hoc explanations.* "Find dated,
   public predictions of earthquakes and floods by astrologers, and
   separately the explanations offered after events. For each, record the
   posting date, the claim, the event matched, and whether it named a place,
   a date window and a size. Describe the methods used to map the sky to
   geography (Kurma Chakra, nakshatra-to-region tables, country ruling signs,
   geodetic charts)."
3. *Financial astrology forecasts for gold, silver, oil and indices.* "Find
   published forecasts for gold, silver, crude oil and equity indices with a
   dated posting, the indicators used and the stated window, the charts used
   (exchange and first-trade charts), any audited track records and any
   peer-reviewed tests, so the rules can be pre-registered and scored."
4. *National charts in use for 40 countries, with disputes.* "For about 40
   countries, list each founding chart practitioners use (event, date, time,
   place), who uses it, the source, and the argument for it; list every
   competing chart where charts are disputed."

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
