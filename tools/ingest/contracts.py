"""File contracts (PAPER_ROADMAP section 4.3) and the checks that hang on them."""

from __future__ import annotations

import difflib
import fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

NOT_FOUND = "NOT FOUND"

SOURCES_COLUMNS = (
    "dataset", "provider", "series_id", "freq", "start", "end", "units",
    "tz_sampling_time", "licence", "redistributable", "url",
)

#: Columns added by the validator in the promoted copy only.
PROMOTED_COLUMNS = (
    "row_id", "url_status", "archive_url", "checked_by", "checked_on",
    "verdict", "reject_reason",
)


@dataclass(frozen=True)
class Contract:
    name: str
    patterns: Tuple[str, ...]
    columns: Tuple[str, ...]
    #: columns of which at least one must hold a URL, DOI or book reference
    reference: Tuple[str, ...] = ()
    #: columns that must parse as YYYY-MM-DD (or NOT FOUND)
    dates: Tuple[str, ...] = ()
    #: (start, end) date column pairs; end must not precede start
    ranges: Tuple[Tuple[str, str], ...] = ()
    #: column whose values must be unique
    id_column: Optional[str] = None
    #: (published column, target-start column): published must be strictly earlier
    ex_ante: Optional[Tuple[str, str]] = None
    #: column holding a yes/no ex-ante flag (rows count as ex-ante only if yes)
    ex_ante_flag: Optional[str] = None
    #: True when every row of the file claims to be ex-ante
    all_ex_ante: bool = False
    free_text: bool = False


CONTRACTS: Tuple[Contract, ...] = (
    Contract("sources", ("sources_*.csv", "drivers.csv"), SOURCES_COLUMNS,
             reference=("url",), dates=("start", "end"), ranges=(("start", "end"),)),
    Contract("gold_episodes", ("gold_episodes.csv",),
             ("episode_id", "direction", "start_date", "peak_or_trough_date", "end_date",
              "start_price_usd", "extreme_price_usd", "pct_change", "max_drawdown_pct",
              "duration_days", "series_used", "macro_narrative", "key_drivers", "sources"),
             reference=("sources",),
             dates=("start_date", "peak_or_trough_date", "end_date"),
             ranges=(("start_date", "end_date"),), id_column="episode_id"),
    Contract("literature", ("literature_*.csv",),
             ("citation", "doi", "method", "data", "sample", "oos_result", "effect_size", "notes"),
             reference=("doi",)),
    Contract("gold_forecasts_exante", ("gold_forecasts_exante.csv",),
             ("astrologer", "published_date", "url", "quote", "target_start", "target_end",
              "predicted_direction", "predicted_level", "method_cited"),
             reference=("url",), dates=("published_date", "target_start", "target_end"),
             ranges=(("target_start", "target_end"),),
             ex_ante=("published_date", "target_start"), all_ex_ante=True),
    Contract("episode_astrology_claims", ("episode_astrology_claims.csv",),
             ("episode_id", "astrologer", "published_date", "ex_ante", "configuration_cited",
              "quote", "url"),
             reference=("url",), dates=("published_date",), ex_ante_flag="ex_ante"),
    Contract("quake_forecasts_exante", ("quake_forecasts_exante.csv",),
             ("astrologer", "published_date", "url", "quote", "region", "window_start",
              "window_end", "magnitude_claimed", "method"),
             reference=("url",), dates=("published_date", "window_start", "window_end"),
             ranges=(("window_start", "window_end"),),
             ex_ante=("published_date", "window_start"), all_ex_ante=True),
    Contract("monsoon_forecasts_exante", ("monsoon_forecasts_exante.csv",),
             ("source", "published_date", "url", "year", "predicted_category", "regions", "method"),
             reference=("url",), dates=("published_date",), all_ex_ante=True),
    Contract("free_text", ("disputes.md", "feasibility.md", "answers.md"), (), free_text=True),
)


def contract_for(filename: str) -> Optional[Contract]:
    for c in CONTRACTS:
        if any(fnmatch.fnmatch(filename, p) for p in c.patterns):
            return c
    return None


def suggest_mapping(found: Sequence[str], required: Sequence[str]) -> Dict[str, Optional[str]]:
    """Suggest, for each missing required column, the closest unused found column.

    The result is advice only: the validator never renames columns itself.
    """
    missing = [c for c in required if c not in found]
    extra = [c for c in found if c not in required]
    out: Dict[str, Optional[str]] = {}
    for col in missing:
        close = difflib.get_close_matches(col, extra, n=1, cutoff=0.5)
        out[col] = close[0] if close else None
    return out
