# Market and exchange charts used by practitioners

Candidate "birth" charts for exchanges and contracts, recorded as practitioners
state them. None is adopted: a chart is promoted only after a maintainer opens
its source and, where possible, a contemporaneous record of the time.
Confidence labels follow `studies/mundane/data/countries.yaml`:
`documented` (time from a record of the day), `conventional` (market open,
midnight, noon or untimed) and `disputed` (rectified, contradictory, or the
time's origin is not stated). Full references are in `papers/sources.bib`.

## NYSE: Buttonwood Agreement, 17 May 1792, New York

The date is the exchange's own founding date; the signing time is not in any
record the project has seen, and the historical account itself is partly
legend ("How the Buttonwood tree grew: the making of a New York Stock
Exchange legend", *Prospects*,
https://www.cambridge.org/core/journals/prospects/article/how-the-buttonwood-tree-grew-the-making-of-a-new-york-stock-exchange-legend/68D4F4577C720CFC004C6BB6076D46F6).
Local mean
time in New York is UTC-04:56:02. Planet signs are stable across the day; the
ascendant, the houses and (through the Moon) the Vimshottari dasha balance are
not.

| Variant | Time (LMT) | Used by | Source | Confidence | Notes |
|---|---|---|---|---|---|
| Standard | 10:30 | "majority of US financial astrologers"; stockastrologer.com (NYSE dasha forecasts) | https://stockastrologer.com/monthly-analysis/ | disputed | Cancer rising (tropical); Libra rising in the sidereal reading the same page uses. |
| McWhirter rectification | 07:52 | Louise McWhirter (1938) | https://en.wikipedia.org/wiki/Louise_McWhirter | disputed | Gemini rising (tropical). |
| Alternative | about 10:10 | as reported, no page located | none | disputed | Untraced; listed so the spread is visible. |
| Alternative | 08:52 | as reported, no page located | none | disputed | Untraced. Exactly one hour after 07:52, which may be the same chart under a different clock convention (not verified). |

Astro-Databank is said to rate the data as conflicting ("dirty data"); that
page was not located. The NYSE dasha rule
(`nyse_dasha_turning_points.yaml`) is `needs_predicates` because 1987 lies in
the second 120-year Vimshottari cycle, which the engine does not compute yet.

## India: independence, 15 August 1947, 00:00 IST, New Delhi

Used for the Nifty and Sensex and for the national economy (for example the
Mars mahadasha read for 2025-2032). The national-chart variants (00:01, noon,
Republic Day 1950) are in `studies/mundane/data/countries.yaml` under `IN`.

## Contract and index first-trade charts

| Instrument | Date | Time | Place | Used by | Source | Confidence |
|---|---|---|---|---|---|---|
| COMEX gold futures, first trade | 1974-12-31 | 09:25 EST | New York | Susan Abbott Gidel; AstroCapitalX; BullionSignals | https://www.moneyshow.com/articles/tradingidea-50940/ | documented (Gidel cites exchange archives) |
| NYMEX light sweet crude, first trade | 1983-03-30 | 09:30 EST | New York | Susan Abbott Gidel | https://www.moneyshow.com/articles/tradingidea-50940/ | documented (as above) |
| NYMEX light sweet crude, first trade | 1983-03-30 | 09:45 EST | New York | AstroCapitalX | https://www.astrocapitalx.com/blog/best-industries-according-to-your-horoscope | disputed |
| S&P 500 cash index launch | 1957-03-04 | 10:00 EST (market open) | New York | Susan Abbott Gidel | https://www.moneyshow.com/articles/tebiwkly08-53660/ | conventional |
| BSE | 1875-07-09 | not stated | Mumbai | AstroCapitalX | https://www.astrocapitalx.com/stock-market-astrology | conventional |
| NSE | 1994 (day not stated) | not stated | Mumbai | AstroCapitalX | https://www.astrocapitalx.com/stock-market-astrology | conventional |
| MCX | 2003 (day not stated) | not stated | Mumbai | AstroCapitalX | https://www.astrocapitalx.com/commodity-astrology | conventional |

Also mentioned without a traceable page (kept out of the rules): S&P 500
futures first trade 21 April 1982, Chicago; Nifty 22 April 1996, 09:15,
Mumbai.
