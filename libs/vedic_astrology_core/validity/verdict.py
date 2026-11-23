"""The verdict function, second version (ADR-008 section 9.1; amends ADR-007 5.4).

Work package WP-94. One pure function, verdict(), turns the numbers of one
test into its verdict code, its flags and its sentences. No person chooses a
verdict. Risk named by the ADR: this function writes every headline.

Symbols (each compared with the stored a_test of the test's batch, ADR-008
3.2 rule 4; p equal to a_test passes):

* p_sup: support p-value, claimed direction, **confirm period**.
* p_opp: p-value for the opposite direction, whole period.
* p_ex: exclusion p-value at the SESOI, whole period (core/stats/exclusion.py).

Eligibility (ADR-008 3.2, core/validity/family.py Eligibility) is checked
first: a row whose numbers hold but whose verdict the eligibility row forbids
is skipped and its blocking flag is added (signal_on_seen_data,
registered_after_unblinding, seen_data, ...). The first row that holds and is
eligible is the verdict:

====  =======================================================================
Code  Condition (all must hold)
====  =======================================================================
U     Gate fails for both abilities, or every block was dropped
S     S-eligible; gate "can support"; p_sup <= a_test; the explore effect has
      the same sign; R1 to R4 pass; source.published is before the confirm
      period starts (F-03)
C     C-eligible; directional claim whose direction is not disputed (A-08);
      p_opp <= a_test
E     E-eligible; a SESOI exists (7.2); minimum-information rule met at
      a_test; p_ex <= a_test
N     everything else
====  =======================================================================

Conservative readings chosen where the ADR leaves a gap:

* A missing number (p, explore sign, robustness check) counts as "does not
  hold". A missing or unreadable source.published counts as not before the
  confirm period: S is impossible and the card says the source could have
  been fitted to these years.
* Only a year known for source.published: it must be strictly earlier than
  the confirm start's year.
* The E verdict words cite X-strict; when X-strict is unbounded the SESOI is
  printed (p_ex <= a_test rules out a steady effect at the SESOI with the
  family guarantee).

Flags (ADR-007's six stay; ADR-008 adds the rest): FLAGS. Words follow the
level (section 7.1) through core/validity/sentences.py; every line a verdict
produces is from the allow-list.

Engine fix after a confirm (G-05): check_recomputation() allows one
recomputation per test, with the same a_test; a fix proposed after its author
saw the confirm result needs a second person's sign-off.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from ..stats.exclusion import MIN_K_EFF, LimitRecord, card_lines, min_informative
from . import sentences as _s
from .family import Eligibility, passes

__all__ = [
    "VERDICT_SCHEMA",
    "CODES",
    "FLAGS",
    "VerdictError",
    "RecomputationRefused",
    "VerdictInput",
    "Verdict",
    "verdict",
    "source_precedes",
    "check_recomputation",
]

VERDICT_SCHEMA = "validity-verdict/2"
CODES = ("U", "S", "C", "E", "N")

#: Every flag a verdict may carry, in the order they are printed.
FLAGS: Tuple[str, ...] = (
    # ADR-007 5.4 (the six stay)
    "signal_not_robust",
    "below_sesoi",
    "limit_only",
    "tuned",
    "pseudo_out_of_sample",
    "control_not_detected",
    # ADR-008 9.1
    "support_underpowered",
    "known_channel",
    "seen_data",
    "signal_on_seen_data",
    "registered_after_unblinding",
    "source_postdates_data",
    "project_extension",
    "reading_differs",
    "recomputed_after_confirm",
    # eligibility rows of core/validity/family.py
    "batch_open",
    "not_batch_vintage",
    "control",
)

_SIDES = ("greater", "less", "two-sided")
_CHECKS = ("R1", "R2", "R3", "R4")


class VerdictError(ValueError):
    """An input the verdict function refuses (unknown flag, p outside [0, 1], ...)."""


class RecomputationRefused(VerdictError):
    """G-05: a second recomputation, or a post-result fix without a second sign-off."""


DateLike = Union[str, int, _dt.date, None]


@dataclass(frozen=True)
class VerdictInput:
    """Everything the verdict of one test depends on. Nothing else is read.

    side: "greater", "less" or "two-sided" (the claimed direction).
    robustness: R1..R4 to pass/fail; a missing key fails.
    r2_status: the R2 status; "insufficient_placebos" prints "check not possible" instead of "failed".
    estimate_magnitude: the confirm estimate on the SESOI's scale, signed so
        that a larger value is further in the claimed direction (for
        below_sesoi only).
    x95, x_strict: the limits from core/stats/exclusion.py (None: not computed).
    """

    level: int
    eligibility: Eligibility
    side: str
    can_support: bool
    can_limit: bool
    all_blocks_dropped: bool = False
    untestable_reason: Optional[str] = None
    direction_disputed: bool = False
    p_sup: Optional[float] = None
    p_opp: Optional[float] = None
    p_ex: Optional[float] = None
    explore_same_sign: Optional[bool] = None
    robustness: Mapping[str, bool] = field(default_factory=dict)
    r2_status: Optional[str] = None
    source_published: DateLike = None
    confirm_start: DateLike = None
    sesoi: Optional[float] = None
    informative_at_sesoi: Optional[int] = None
    k_eff: Optional[float] = None
    estimate_magnitude: Optional[float] = None
    x95: Optional[LimitRecord] = None
    x_strict: Optional[LimitRecord] = None
    n_blocks: Optional[int] = None
    support_underpowered: bool = True
    p_support_at_sesoi: Optional[float] = None
    known_channel: Optional[str] = None
    reading_differs: bool = False
    source_name: Optional[str] = None
    project_extension: bool = False
    tuned: bool = False
    pseudo_out_of_sample: bool = False
    control_not_detected: bool = False
    recomputed_bars_changed: Optional[int] = None
    attested_after: Optional[str] = None


@dataclass(frozen=True)
class Verdict:
    code: str
    words: str
    flags: Tuple[str, ...]
    lines: Tuple[str, ...]
    title: Optional[str]
    columns: Dict[str, bool]
    conditions: Dict[str, Dict[str, bool]]
    failed_checks: Tuple[str, ...]
    a_test: Optional[float]
    eligibility_row: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": VERDICT_SCHEMA,
            "code": self.code,
            "words": self.words,
            "flags": list(self.flags),
            "lines": list(self.lines),
            "title": self.title,
            "columns": dict(self.columns),
            "conditions": {k: dict(v) for k, v in self.conditions.items()},
            "failed_checks": list(self.failed_checks),
            "a_test": self.a_test,
            "eligibility_row": self.eligibility_row,
        }

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()


# ------------------------------------------------------------------ dates
_YEAR = re.compile(r"^\s*(-?\d{1,4})\s*$")
_ISO = re.compile(r"^\s*(-?\d{1,4})-(\d{2})(?:-(\d{2}))?\s*$")


def _parse(value: DateLike) -> Optional[Tuple[int, Optional[_dt.date]]]:
    """(year, full date or None); None when absent or unreadable."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, _dt.datetime):
        return value.year, value.date()
    if isinstance(value, _dt.date):
        return value.year, value
    if isinstance(value, int):
        return value, None
    s = str(value)
    m = _YEAR.match(s)
    if m:
        return int(m.group(1)), None
    m = _ISO.match(s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3) or 1)
        try:
            return y, (_dt.date(y, mo, d) if y >= 1 else None)
        except ValueError:
            return None
    return None


def source_precedes(published: DateLike, confirm_start: DateLike) -> bool:
    """F-03: True only when source.published is known and before the confirm period starts.

    With a full date on both sides the date decides; otherwise the years
    decide and the same year does not count as before.
    """
    p, c = _parse(published), _parse(confirm_start)
    if p is None or c is None:
        return False
    (py, pd_), (cy, cd) = p, c
    if pd_ is not None and cd is not None:
        return pd_ < cd
    return py < cy


# ------------------------------------------------------------------ checks
def _p(value: Optional[float], what: str) -> Optional[float]:
    if value is None:
        return None
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise VerdictError(f"{what} = {value!r} outside [0, 1]")
    return v


def _ok(p: Optional[float], a: Optional[float]) -> bool:
    return p is not None and a is not None and passes(p, a)


def _order(flags) -> Tuple[str, ...]:
    unknown = set(flags) - set(FLAGS)
    if unknown:
        raise VerdictError(f"unknown flags {sorted(unknown)}")
    return tuple(f for f in FLAGS if f in set(flags))


def check_recomputation(previous: int, fix_after_seeing_result: bool, second_signoff: Optional[str]) -> None:
    """G-05: one recomputation per test; a post-result fix needs a second person's sign-off."""
    if int(previous) >= 1:
        raise RecomputationRefused("a test may be recomputed once after a confirm; wait for the next vintage")
    if fix_after_seeing_result and not (second_signoff and str(second_signoff).strip()):
        raise RecomputationRefused(
            "a fix proposed after its author saw the confirm result needs a second person's sign-off "
            "in the changelog entry, or waits for the next vintage"
        )


# ---------------------------------------------------------------- verdict
def verdict(inp: VerdictInput) -> Verdict:
    """The verdict of one test (ADR-008 9.1). Pure: same input, same bytes."""
    if inp.side not in _SIDES:
        raise VerdictError(f"side must be one of {_SIDES}")
    el = inp.eligibility
    if not isinstance(el, Eligibility):
        raise VerdictError("eligibility must come from core/validity/family.py")
    a = el.a_test
    p_sup, p_opp, p_ex = _p(inp.p_sup, "p_sup"), _p(inp.p_opp, "p_opp"), _p(inp.p_ex, "p_ex")
    rob = {k: bool(inp.robustness.get(k, False)) for k in _CHECKS}
    failed_checks = tuple(k for k in _CHECKS if not rob[k])
    flags: List[str] = list(el.flags)

    untestable = (not inp.can_support and not inp.can_limit) or bool(inp.all_blocks_dropped)
    source_ok = source_precedes(inp.source_published, inp.confirm_start)
    directional = inp.side != "two-sided"
    sesoi_exists = inp.sesoi is not None
    if inp.informative_at_sesoi is not None and inp.k_eff is not None and a is not None:
        min_info = float(inp.k_eff) >= MIN_K_EFF and int(inp.informative_at_sesoi) >= min_informative(a)
    else:
        min_info = False

    rows: Dict[str, Dict[str, bool]] = {
        "S": {
            "can_support": bool(inp.can_support),
            "p_sup": _ok(p_sup, a),
            "explore_same_sign": inp.explore_same_sign is True,
            "robustness": not failed_checks,
            "source_precedes": source_ok,
        },
        "C": {
            "directional": directional,
            "not_disputed": not inp.direction_disputed,
            "p_opp": _ok(p_opp, a),
        },
        "E": {
            "sesoi": sesoi_exists,
            "min_information": min_info,
            "p_ex": _ok(p_ex, a),
        },
    }
    blocked = dict(el.blocked)

    if not untestable and rows["S"]["p_sup"] and failed_checks:
        flags.append("signal_not_robust")
    if not source_ok:
        flags.append("source_postdates_data")
    if not inp.can_support and not untestable:
        flags.append("limit_only")
    if inp.support_underpowered:
        flags.append("support_underpowered")
    if inp.known_channel:
        flags.append("known_channel")
    for name in ("reading_differs", "project_extension", "tuned", "pseudo_out_of_sample",
                 "control_not_detected"):
        if getattr(inp, name):
            flags.append(name)
    if inp.recomputed_bars_changed is not None:
        flags.append("recomputed_after_confirm")

    code = "N"
    if untestable:
        code = "U"
    else:
        for cand in ("S", "C", "E"):
            if not all(rows[cand].values()):
                continue
            if el.allows(cand):
                code = cand
                break
            extra = blocked.get(cand)
            if extra:
                flags.append(extra)
    if code == "S" and sesoi_exists and inp.estimate_magnitude is not None \
            and float(inp.estimate_magnitude) < float(inp.sesoi):
        flags.append("below_sesoi")

    ordered = _order(flags)
    words, lines = _lines(code, inp, ordered, failed_checks)
    title = None
    if inp.reading_differs:
        if not inp.source_name:
            raise VerdictError("reading_differs needs source_name for the card title")
        title = _s.render("title.reading_differs", source=inp.source_name)
    associated = code == "S"
    columns = {"associated": associated, "beyond_known_channels": associated and not inp.known_channel}
    return Verdict(code, words, ordered, tuple(lines), title, columns, rows, failed_checks,
                   None if a is None else float(a), el.row)


def _x_value(x: Optional[LimitRecord]) -> Optional[float]:
    if x is None or x.unbounded or x.value is None:
        return None
    return float(x.value)


def _lines(code: str, inp: VerdictInput, flags: Tuple[str, ...], failed: Tuple[str, ...]):
    lvl = int(inp.level)
    enc = lvl < _s.ENCODING_LEVEL
    xs = _x_value(inp.x_strict)
    if code == "E":
        x_words = xs if xs is not None else float(inp.sesoi)
        words = _s.verdict_words("E", lvl, x_words)
    else:
        words = _s.verdict_words(code, lvl)
    lines: List[str] = [words, _s.scope_line(lvl, inp.attested_after if not enc else None)]
    lines.append(_s.render("single_condition"))
    tier = "enc" if enc else "l4"
    if code == "U":
        reason = _s.UNTESTABLE_REASONS.get(inp.untestable_reason or "", None)
        if reason is None:
            reason = _s.UNTESTABLE_REASONS["no_clean_control" if inp.all_blocks_dropped else "too_few_episodes"]
        lines.append(_s.render(f"explain.{tier}.U", reason=reason))
    elif code == "S":
        lines.append(_s.render(f"explain.{tier}.S"))
    elif code == "C":
        lines.append(_s.render("explain.C"))
    elif code == "E":
        lines.append(_s.render("explain.E"))
    else:
        lines.append(_s.render("explain.N"))
    if code != "U":
        # X-strict carries the family guarantee; X95 is the per-test value (S-11).
        if inp.x_strict is not None:
            lines.append(_s.render("x_strict.value", x=_s.fmt_number(xs)) if xs is not None
                         else _s.render("x_strict.unbounded"))
        x95 = _x_value(inp.x95)
        if inp.x95 is not None:
            lines.append(_s.render("x95.value", x=_s.fmt_number(x95)) if x95 is not None
                         else _s.render("x95.unbounded"))
            if x95 is not None and inp.n_blocks:
                lines.extend(card_lines(inp.x95, int(inp.n_blocks)))
    for f in flags:
        if f == "signal_not_robust":
            for chk in failed:
                if chk == "R2" and inp.r2_status == "insufficient_placebos":
                    lines.append(_s.render("flag.signal_not_robust.insufficient_placebos"))
                    continue
                lines.append(_s.render("flag.signal_not_robust", check=_s.CHECK_NAMES[chk]))
        elif f == "support_underpowered":
            if inp.p_support_at_sesoi is None:
                lines.append(_s.render("flag.support_underpowered.unknown"))
            else:
                lines.append(_s.render("flag.support_underpowered", pct=_s.fmt_share(inp.p_support_at_sesoi)))
        elif f == "known_channel":
            ch = str(inp.known_channel)
            try:
                lines.append(_s.render("flag.known_channel", channel=ch))
            except _s.SentenceError:
                lines.append(_s.render("flag.known_channel.generic"))
        elif f == "recomputed_after_confirm":
            lines.append(_s.render("flag.recomputed_after_confirm", n=int(inp.recomputed_bars_changed)))
        else:
            lines.append(_s.render(_s.FLAG_SENTENCES[f]))
    return words, lines
