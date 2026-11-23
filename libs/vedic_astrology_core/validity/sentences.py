"""The sentence allow-list for verdicts and cards (ADR-008 section 7.1, H-7).

Work package WP-94. Reports may contain only sentences from this module with
their slots filled. The deny-list of ADR-007 is removed: a sentence that is not
here cannot be printed, so a paraphrase ("debunked", "astrology fails",
"proven") fails by construction.

Words follow the evidence level (A-02):

* L4 and above (a practitioner attested the encoding before the confirm): the
  five ADR-007 verdict words.
* Below L4: every verdict line says "encoding", and the fixed second line says
  the result is about the project's encoding, not the source or astrology.
  ADR-008 7.1 lists "Untestable on this data" unchanged below L4; this module
  uses "Encoding untestable on this data" so that every verdict line below L4
  says "encoding" (the stricter reading; it says less, never more).

Sentences that cite a limit cite **X-strict** ("with the family guarantee");
X95 is shown only as the per-test value (S-11). An unbounded X-strict gives
"There is no family-level bound." E reads "a steady effect at or above the
project's threshold", never "of the claimed size" (A-07).

Slots are typed: each slot value must match its pattern, so a slot cannot
smuggle free prose into a card. render() fills a template; is_allowed()
checks any line against every template; disallowed() lists the lines of a
page that match none.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

__all__ = [
    "SentenceError",
    "TEMPLATES",
    "SLOT_PATTERNS",
    "UNTESTABLE_REASONS",
    "CHECK_NAMES",
    "FLAG_SENTENCES",
    "ENCODING_LEVEL",
    "verdict_words",
    "scope_line",
    "render",
    "fmt_number",
    "fmt_share",
    "is_allowed",
    "disallowed",
    "match",
]

#: Lowest level at which a practitioner attested the encoding (ADR-004 D-4).
ENCODING_LEVEL = 4


class SentenceError(ValueError):
    """A template key that does not exist, or a slot value outside its pattern."""


#: Reasons for Untestable, as printed after "because" (gate codes to words).
UNTESTABLE_REASONS: Dict[str, str] = {
    "not_encoded": "the rule is not encoded",
    "not_operationalised": "the rule is not operationalised",
    "data_quality": "the primary dataset is below grade B",
    "too_few_episodes": "there are fewer than 8 effective episodes",
    "p_not_attainable": "the smallest attainable p-value is above the test's threshold",
    "too_few_events": "too few events are expected inside or outside the active time",
    "chart_time": "the founding time is too coarse",
    "season": "it cannot be separated from the season",
    "no_clean_control": "there is no clean control time",
    "too_little_information": "too few blocks carry information to limit an effect",
    "no_sesoi": "no outside threshold exists and support is not reachable",
}

#: Robustness checks by name, as printed in "the ... check failed".
CHECK_NAMES: Dict[str, str] = {
    "R1": "baselines",
    "R2": "placebo-sky",
    "R3": "sensitivity-grid",
    "R4": "separability",
}

_NUM = r"-?(?:\d+(?:\.\d+)?(?:e[+-]?\d+)?|inf)"
_REASON = "|".join(re.escape(v) for v in UNTESTABLE_REASONS.values())
_CHECK = "|".join(re.escape(v) for v in CHECK_NAMES.values())

#: Slot name to the pattern its value must match in full.
SLOT_PATTERNS: Dict[str, str] = {
    "x": _NUM,
    "pct": r"\d{1,3}%",
    "n": r"\d+",
    "date": r"\d{4}-\d{2}-\d{2}",
    "reason": rf"(?:{_REASON})",
    "check": rf"(?:{_CHECK})",
    # A source's short name: a capital, then letters, digits and light punctuation.
    "source": r"[A-Z][A-Za-z0-9 .,'()\-]{0,79}",
    # A known channel in plain lower-case words ("festival buying", "the tide").
    "channel": r"[a-z][a-z \-]{0,59}",
}

#: Every allowed sentence. Keys are stable ids; values are templates.
TEMPLATES: Dict[str, str] = {
    # ---- verdict words, L4 and above (ADR-007 5.4)
    "verdict.l4.S": "Supported on this dataset",
    "verdict.l4.C": "Contradicted",
    "verdict.l4.E": "Effect excluded above {x}",
    "verdict.l4.N": "Not supported, not excluded",
    "verdict.l4.U": "Untestable on this data",
    # ---- verdict words below L4 (ADR-008 7.1)
    "verdict.enc.S": "Encoding supported on this dataset",
    "verdict.enc.C": "Encoding contradicted",
    "verdict.enc.E": "Encoding: steady effect excluded above {x}",
    "verdict.enc.N": "Encoding not supported, not excluded",
    "verdict.enc.U": "Encoding untestable on this data",
    # ---- scope lines (ADR-008 7.1; ADR-007 5.5; A-10)
    "scope.enc": (
        "This result is about the project's encoding of the rule. "
        "It is not a result about the source text or about astrology."
    ),
    "scope.l4.before": (
        "An independent astrologer attested before the result that the encoding is faithful to the source."
    ),
    "scope.l4.after": (
        "An independent astrologer attested on {date}, after the result, that the encoding is "
        "faithful to the source."
    ),
    "single_condition": (
        "Tested as a single condition, without the cancellations and strength rules the tradition applies."
    ),
    "title.reading_differs": "Project hypothesis derived from {source}",
    # ---- what each verdict may say
    "explain.l4.U": "This dataset cannot test this principle, because {reason}.",
    "explain.enc.U": "This dataset cannot test the project's encoding, because {reason}.",
    "explain.l4.S": "The effect was found in the held-out period and survived the controls.",
    "explain.enc.S": "The encoded effect was found in the held-out period and survived the controls.",
    "explain.C": "The data show an effect in the opposite direction.",
    "explain.E": "A steady effect at or above the project's threshold is ruled out, with the family guarantee.",
    "explain.N": "No effect was shown.",
    # ---- limits (S-11, G-11, section 2.3)
    "x_strict.value": "With the family guarantee, a steady effect above {x} is ruled out.",
    "x_strict.unbounded": "There is no family-level bound.",
    # N-25: verdict E whose X-strict found no value on the plan's grid; the exclusion at the SESOI
    # carries the family guarantee by itself.
    "x_strict.sesoi_only": (
        "With the family guarantee, a steady effect at the project's threshold of {x} is ruled out; "
        "the plan's grid gives no other family-level bound."
    ),
    "x95.value": "Per-test value: a steady effect above {x} is ruled out at the 95% level.",
    "x95.unbounded": "Per-test value: no bound.",
    "ruled_out": "Ruled out: a steady effect of {x} or more in every episode.",
    "not_addressed": "Not addressed: an effect that appears in fewer than {pct} of the episodes.",
    # ---- flags, one sentence each
    "flag.support_underpowered": (
        "Support was hardly reachable: the chance of Supported at the project's threshold was {pct}."
    ),
    "flag.support_underpowered.unknown": (
        "Support was hardly reachable: the chance of Supported at the project's threshold is not known."
    ),
    "flag.signal_not_robust": "A signal was found, but the {check} check failed.",
    # R2 status insufficient_placebos (ADR-008 section 5): the check could not be run, it did not fail.
    "flag.signal_not_robust.insufficient_placebos": (
        "Placebo-sky check not possible: fewer than 19 distinct placebo calendars on this grid; "
        "Supported is not available."
    ),
    "flag.signal_on_seen_data": (
        "A signal on data the project had already seen cannot support or contradict the principle."
    ),
    "flag.seen_data": "The confirm period had been seen before; only an exclusion could be reported.",
    "flag.registered_after_unblinding": (
        "Registered after the confirm data were opened; the numbers are descriptive."
    ),
    "flag.source_postdates_data": "The source could have been fitted to these years.",
    "flag.project_extension": "The outcome or direction is a project extension, not stated by the source.",
    "flag.reading_differs": "The source reads the rule differently; this is the project's hypothesis.",
    "flag.known_channel": "Tested as an effect beyond what {channel} explains.",
    "flag.known_channel.generic": "A known physical or social channel could produce this effect.",
    "flag.below_sesoi": "The estimate is smaller than the project's threshold.",
    "flag.limit_only": "This dataset could not have supported the principle. It could only limit it.",
    "flag.tuned": "The tested version came from tuning; the cells tried are shown.",
    "flag.pseudo_out_of_sample": "The confirm period had been seen before the run.",
    "flag.control_not_detected": "The method did not detect the planted control effect of this domain.",
    # N-18: R3 passes when no distinct cell exists; the card says it was not run.
    "flag.sensitivity_not_run": "Sensitivity-grid check not run: no sensitivity cell was declared.",
    "flag.sensitivity_not_run.copies": (
        "Sensitivity-grid check not run: none of the {n} declared cells changes at least 5% of the active bars."
    ),
    "flag.recomputed_after_confirm": (
        "Recomputed once after an engine fix; both results are shown and {n} calendar bars changed."
    ),
    "flag.batch_open": "The batch of this test is still open; the numbers are descriptive.",
    "flag.not_batch_vintage": (
        "This data vintage does not belong to the test's batch; the numbers are descriptive."
    ),
    "flag.control": "This is a control, outside every batch.",
    # ---- columns (O-01, A-09)
    "column.associated": "Calendar is associated with the outcome",
    "column.beyond_channels": "Beyond known physical and social channels",
    "baselines.with": "With the domain's baselines (primary).",
    "baselines.without": "Without the socially mediated baselines.",
}

#: Flag to the template that states it on a card.
FLAG_SENTENCES: Dict[str, str] = {
    k.split(".", 1)[1]: k for k in TEMPLATES if k.startswith("flag.") and k.count(".") == 1
}

_SLOT = re.compile(r"\{([a-z_]+)\}")


def _compile(template: str) -> "re.Pattern[str]":
    parts: List[str] = []
    pos = 0
    for m in _SLOT.finditer(template):
        parts.append(re.escape(template[pos:m.start()]))
        name = m.group(1)
        if name not in SLOT_PATTERNS:
            raise SentenceError(f"template uses unknown slot {name!r}")
        parts.append(f"(?:{SLOT_PATTERNS[name]})")
        pos = m.end()
    parts.append(re.escape(template[pos:]))
    return re.compile("".join(parts))


_COMPILED: Dict[str, "re.Pattern[str]"] = {k: _compile(v) for k, v in TEMPLATES.items()}


def fmt_number(x: float) -> str:
    """How a limit or estimate is printed: three significant digits."""
    x = float(x)
    if x != x:
        raise SentenceError("cannot print NaN")
    return f"{x:.3g}"


def fmt_share(share: float) -> str:
    """A share as a whole percentage ("31%")."""
    s = float(share)
    if not 0.0 <= s <= 1.0:
        raise SentenceError(f"share {s!r} outside [0, 1]")
    return f"{s:.0%}"


def render(key: str, **slots: object) -> str:
    """Fill template key; every slot value must match its pattern in full."""
    try:
        template = TEMPLATES[key]
    except KeyError:
        raise SentenceError(f"no sentence {key!r} in the allow-list") from None
    needed = set(_SLOT.findall(template))
    if set(slots) != needed:
        raise SentenceError(f"sentence {key!r} needs slots {sorted(needed)}, got {sorted(slots)}")
    values = {}
    for name, value in slots.items():
        v = str(value)
        if re.fullmatch(SLOT_PATTERNS[name], v) is None:
            raise SentenceError(f"slot {name}={v!r} does not match its pattern")
        values[name] = v
    out = template.format(**values)
    if _COMPILED[key].fullmatch(out) is None:  # pragma: no cover - guards the compiler
        raise SentenceError(f"rendered sentence does not match its own template: {out!r}")
    return out


def verdict_words(code: str, level: int, x: Optional[float] = None) -> str:
    """Verdict words for a verdict code at an evidence level (E needs x)."""
    tier = "l4" if int(level) >= ENCODING_LEVEL else "enc"
    key = f"verdict.{tier}.{code}"
    if key not in TEMPLATES:
        raise SentenceError(f"unknown verdict code {code!r}")
    if code == "E":
        if x is None:
            raise SentenceError("verdict E needs the excluded value")
        return render(key, x=fmt_number(x))
    return render(key)


def scope_line(level: int, attested_after: Optional[str] = None) -> str:
    """Fixed second line: "encoding" below L4; attestation line at L4 and above (A-10)."""
    if int(level) < ENCODING_LEVEL:
        return render("scope.enc")
    if attested_after is None:
        return render("scope.l4.before")
    return render("scope.l4.after", date=attested_after)


def match(line: str) -> Optional[str]:
    """Key of the template a line matches in full, or None."""
    s = str(line).strip()
    for key, rx in _COMPILED.items():
        if rx.fullmatch(s):
            return key
    return None


def is_allowed(line: str) -> bool:
    """True when the line is exactly one allowed sentence with valid slots."""
    return match(line) is not None


def disallowed(lines: Iterable[str]) -> List[str]:
    """The non-empty lines that match no template (a page passes when this is empty)."""
    return [ln for ln in lines if str(ln).strip() and not is_allowed(ln)]
