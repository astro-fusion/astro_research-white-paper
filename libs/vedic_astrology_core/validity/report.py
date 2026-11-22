"""Report generator and report gate (ADR-008 section 9.3, WP-96; ADR-007 WP-73 subset).

Pages are template renders only. Every number passes through
paperkit.Results (a missing or null key stops the build); every prose line
is a sentence of core/validity/sentences.py or a structural line of
REPORT_TEMPLATES below (headings, table rows, fixed labels), each with typed
slots. The gate renders every page again from the results file and compares
bytes, checks the results file against the hash in the run manifest and the
changelog chain, and checks every line of every page against the allow-list.
There is no switch that turns provenance off.

Results input (schema "validity-report-input/1"):

* provenance keys of paperkit.results (provisional, git, plan, data);
* `records`: list of test records, each with id (lower-case, digits,
  underscore), name, domain, level, entry (text | practitioner | project),
  outcome {market, currency}, justified (bool: the source's words justify
  outcome and direction, F-06), verdict (a validity.verdict.Verdict.to_dict()),
  and optionally estimate {with_baselines, without_baselines};
* `sampling_frame`: {not_encodable, not_sourced, untestable} counts;
* `family`: {domains: D} (the number of domains in the run set);
* `certificate`: optional calibration certificate (for X9 on the methods page).

Rows S-10, A-06, F-06, O-01, O-02 of ADR-008 10 are closed here:

* S-10: the union bound D x 3 x 5% opens the summary, computed from the run set.
* A-06: every card says which market and currency were tested; the verdict
  lines come from the allow-list and contain no market name.
* F-06: a test whose outcome and direction the source does not justify
  (project_extension) appears only in its own table.
* O-01: two labelled columns on cards and in the summary.
* O-02: the summary opens with the sampling frame; no percentage cell, no total
  across levels, no sentence about astrology as a whole.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from ..paperkit.results import Results, provenance
from . import sentences as _s
from .sealbundle import LedgerTamperedError, verify_chain

__all__ = [
    "REPORT_SCHEMA",
    "REPORT_TEMPLATES",
    "ReportError",
    "render_card",
    "render_summary",
    "render_methods",
    "render_pages",
    "write_report",
    "allowed_line",
    "disallowed_lines",
    "check_report",
    "check_results_hash",
    "union_bound",
]

REPORT_SCHEMA = "validity-report-input/1"
MANIFEST_NAME = "report_manifest.json"
ALPHA = 0.05
FAMILIES = 3  # support, opposite, equivalence (ADR-007 5.4)
ENTRIES = ("text", "practitioner", "project")

PathLike = Union[str, Path]


class ReportError(ValueError):
    """A build stopped: bad record, unknown id, a sentence outside the allow-list."""


_ID = re.compile(r"[a-z0-9_]{1,80}")

#: Slot patterns local to the report (the sentence slots stay in sentences.py).
SLOTS: Dict[str, str] = {
    "name": _s.SLOT_PATTERNS["source"],
    "domain": r"[a-z][a-z0-9_]{0,39}",
    "outcome": r"the [A-Za-z0-9][A-Za-z0-9 .,'()-]{0,79} in [A-Z]{3}",
    "entry": "|".join(ENTRIES),
    "n": r"\d+",
    "num": _s.SLOT_PATTERNS["x"],
    "bound": r"\d+(?:\.\d+)?",
    "yn1": "yes|no",
    "yn2": "yes|no",
    "n1": r"\d+",
    "n2": r"\d+",
    "n3": r"\d+",
    "cell": r"[A-Za-z0-9_ .,:=+/-]{1,60}",
    "rate": r"\d{1,3}(?:\.\d+)?%|not recorded",
    "pct": _s.SLOT_PATTERNS["pct"],
    "words": "|".join(
        re.escape(t).replace(re.escape("{x}"), _s.SLOT_PATTERNS["x"])
        for k, t in _s.TEMPLATES.items() if k.startswith("verdict.")
    ),
}

#: Structural lines. Sentences of the allow-list are not repeated here.
REPORT_TEMPLATES: Dict[str, str] = {
    "card.title": "# {name}",
    "card.title.derived": "# Project hypothesis derived from {source}",
    "card.domain": "Domain: {domain}",
    "card.level": "Evidence level: {n}",
    "card.entry": "Entered as: {entry}",
    "card.outcome": "Tested on {outcome}.",
    "card.justified": "Outcome and direction are cited from the source.",
    "card.verdict_h": "## Verdict",
    "card.columns_h": "## Two readings",
    "card.baselines_h": "## Estimate",
    "table.rule2": "|---|---|",
    "table.rule3": "|---|---|---|",
    "table.rule4": "|---|---|---|---|",
    "table.rule5": "|---|---|---|---|---|",
    "card.columns.head": "| " + _s.TEMPLATES["column.associated"] + " | " + _s.TEMPLATES["column.beyond_channels"] + " |",
    "card.columns.row": "| {yn1} | {yn2} |",
    "card.baselines.head": "| Baselines | Estimate |",
    "card.baselines.with": "| " + _s.TEMPLATES["baselines.with"] + " | {num} |",
    "card.baselines.without": "| " + _s.TEMPLATES["baselines.without"] + " | {num} |",
    # summary
    "summary.title": "# Summary of tested principles",
    "summary.union": (
        "Chance of at least one false Supported in a domain: at most 5% over all time. "
        "Across {n} domains and three verdict types: at most {bound} in total; "
        "expected number of false verdicts at most that."
    ),
    "summary.no_rate": (
        "These counts describe the principles that were tested. "
        "They are not a rate over any tradition."
    ),
    "summary.frame_h": "## Sampling frame",
    "summary.frame.head": "| Entered as | Principles tested |",
    "summary.frame.row": "| {entry} | {n} |",
    "summary.notested.head": "| Candidates not tested | Count |",
    "summary.notested.row": "| {cell} | {n} |",
    "summary.l4_h": "## Evidence level 4 and above",
    "summary.enc_h": "## Evidence level below 4: the project's encodings",
    "summary.ext_h": "## Project extensions",
    "summary.none": "None.",
    "summary.verdict.head": (
        "| Verdict | Principles | " + _s.TEMPLATES["column.associated"] + " | "
        + _s.TEMPLATES["column.beyond_channels"] + " |"
    ),
    "summary.verdict.row": "| {label} | {n1} | {n2} | {n3} |",
    "summary.ext.head": "| Principle | Verdict |",
    "summary.ext.row": "| {name} | {label} |",
    # methods
    "methods.title": "# Methods: what the guarantees cover",
    "methods.x9_h": "## Uneven effect (recorded, no pass mark)",
    "methods.x9.head": "| Cell | Share falsely excluded |",
    "methods.x9.row": "| {cell} | {rate} |",
    "methods.na_h": "## Not addressed",
    "methods.na.head": "| Episodes | Not addressed |",
    "methods.na.row": "| {n} | {pct} |",
    "methods.na_line": _s.TEMPLATES["not_addressed"],
}

#: Row labels in the summary tables (no limit value in a count table).
LABELS: Dict[str, Dict[str, str]] = {
    "l4": {"S": "Supported on this dataset", "C": "Contradicted", "E": "Effect excluded",
           "N": "Not supported, not excluded", "U": "Untestable on this data"},
    "enc": {"S": "Encoding supported on this dataset", "C": "Encoding contradicted",
            "E": "Encoding: steady effect excluded", "N": "Encoding not supported, not excluded",
            "U": "Encoding untestable on this data"},
}
for _tier, _d in LABELS.items():
    REPORT_TEMPLATES.update({f"label.{_tier}.{c}": t for c, t in _d.items()})

_SLOT = re.compile(r"\{([a-z_0-9]+)\}")
_LOCAL_SLOT_NAMES = {"source": _s.SLOT_PATTERNS["source"], "label": "|".join(
    re.escape(t) for d in LABELS.values() for t in d.values())}


def _slot_pattern(name: str) -> str:
    if name in _LOCAL_SLOT_NAMES:
        return _LOCAL_SLOT_NAMES[name]
    return SLOTS[name]


def _compile(template: str) -> "re.Pattern[str]":
    parts: List[str] = []
    pos = 0
    for m in _SLOT.finditer(template):
        parts.append(re.escape(template[pos:m.start()]))
        parts.append(f"(?:{_slot_pattern(m.group(1))})")
        pos = m.end()
    parts.append(re.escape(template[pos:]))
    return re.compile("".join(parts))


_COMPILED = {k: _compile(v) for k, v in REPORT_TEMPLATES.items()}


def _line(key: str, **slots: object) -> str:
    """Fill a structural template; each slot must match its pattern in full."""
    template = REPORT_TEMPLATES[key]
    needed = set(_SLOT.findall(template))
    if set(slots) != needed:
        raise ReportError(f"template {key!r} needs slots {sorted(needed)}, got {sorted(slots)}")
    vals = {}
    for k, v in slots.items():
        v = str(v)
        if re.fullmatch(_slot_pattern(k), v) is None:
            raise ReportError(f"slot {k}={v!r} of {key!r} does not match its pattern")
        vals[k] = v
    out = template.format(**vals)
    if _COMPILED[key].fullmatch(out) is None:
        raise ReportError(f"rendered line does not match its template {key!r}: {out!r}")
    return out


def allowed_line(line: str) -> bool:
    """True when the line is an allow-listed sentence or a structural template."""
    s = line.strip()
    if not s:
        return True
    return _s.is_allowed(s) or any(rx.fullmatch(s) for rx in _COMPILED.values())


def disallowed_lines(text: str) -> List[str]:
    return [ln for ln in text.splitlines() if not allowed_line(ln)]


# ------------------------------------------------------------------ helpers
def _num(x: float) -> str:
    return _s.fmt_number(x)


def union_bound(domains: int) -> str:
    """D x 3 x 5% as a number (an expected count), two decimals."""
    return f"{int(domains) * FAMILIES * ALPHA:.2f}"


def _join(blocks: Iterable[str]) -> str:
    return "\n\n".join(b.strip("\n") for b in blocks if b) + "\n"


def _table(*rows: str) -> str:
    return "\n".join(rows)


def _rec(res: Results, i: int) -> str:
    return f"records.{i}"


def _check_record(res: Results, i: int) -> str:
    rid = res.get(f"records.{i}.id")
    if not isinstance(rid, str) or not _ID.fullmatch(rid):
        raise ReportError(f"records.{i}.id {rid!r} is not a safe page id")
    return rid


def _tier(level: int) -> str:
    return "l4" if int(level) >= _s.ENCODING_LEVEL else "enc"


def _yn(b: Any) -> str:
    return "yes" if b is True else "no"


def _verdict_lines(res: Results, i: int) -> List[str]:
    lines = res.get(f"records.{i}.verdict.lines")
    if not isinstance(lines, list) or not lines:
        raise ReportError(f"records.{i}.verdict.lines is empty")
    bad = [ln for ln in lines if not _s.is_allowed(ln)]
    if bad:
        raise ReportError(f"records.{i}: verdict line outside the allow-list: {bad[0]!r}")
    # The verdict function wrote these lines; the words must match the code and level.
    code = res.get(f"records.{i}.verdict.code")
    level = int(res.get(f"records.{i}.level"))
    key = _s.match(lines[0])
    if key is None or key != f"verdict.{_tier(level)}.{code}":
        raise ReportError(f"records.{i}: first verdict line does not match code {code!r} at level {level}")
    return list(lines)


def _title(res: Results, i: int) -> str:
    t = f"records.{i}.verdict.title"
    if res.has(t) and res.data["records"][i]["verdict"].get("title"):
        title = res.get(t)
        m = _COMPILED["card.title.derived"]
        line = "# " + title
        if not m.fullmatch(line) or not _s.is_allowed(title):
            raise ReportError(f"records.{i}: title is not the reading-differs sentence")
        return line
    return _line("card.title", name=res.get(f"records.{i}.name"))


def render_card(res: Results, i: int) -> str:
    """One principle's card, from the results file alone."""
    p = _rec(res, i)
    _check_record(res, i)
    level = int(res.get(f"{p}.level"))
    entry = res.get(f"{p}.entry")
    vlines = _verdict_lines(res, i)
    market, currency = res.get(f"{p}.outcome.market"), res.get(f"{p}.outcome.currency")
    blocks = [
        _title(res, i),
        "\n".join([
            _line("card.domain", domain=res.get(f"{p}.domain")),
            _line("card.level", n=level),
            _line("card.entry", entry=entry),
        ]),
        _line("card.outcome", outcome=f"the {market} in {currency}"),
    ]
    if res.get(f"{p}.justified") is True:
        blocks.append(_line("card.justified"))
    blocks.append(_line("card.verdict_h"))
    blocks.extend(vlines)
    blocks.append(_line("card.columns_h"))
    blocks.append(_table(
        _line("card.columns.head"), _line("table.rule2"),
        _line("card.columns.row", yn1=_yn(res.get(f"{p}.verdict.columns.associated")),
              yn2=_yn(res.get(f"{p}.verdict.columns.beyond_known_channels"))),
    ))
    if res.has(f"{p}.estimate"):
        blocks.append(_line("card.baselines_h"))
        blocks.append(_table(
            _line("card.baselines.head"), _line("table.rule2"),
            _line("card.baselines.with", num=_num(res.get(f"{p}.estimate.with_baselines"))),
            _line("card.baselines.without", num=_num(res.get(f"{p}.estimate.without_baselines"))),
        ))
    out = _join(blocks)
    bad = disallowed_lines(out)
    if bad:
        raise ReportError(f"card {i}: line outside the allow-list: {bad[0]!r}")
    return out


def _n_records(res: Results) -> int:
    recs = res.get("records")
    if not isinstance(recs, list):
        raise ReportError("records must be a list")
    return len(recs)


def render_summary(res: Results) -> str:
    """The cross-domain summary: union bound, sampling frame, split tables."""
    n = _n_records(res)
    for i in range(n):
        _check_record(res, i)
    ids = [res.get(f"records.{i}.id") for i in range(n)]
    if len(set(ids)) != n:
        raise ReportError("duplicate record ids")
    domains = int(res.get("family.domains"))
    if domains < 1:
        raise ReportError("family.domains must be at least 1")
    ext = [i for i in range(n) if "project_extension" in res.get(f"records.{i}.verdict.flags")]
    main = [i for i in range(n) if i not in ext]
    blocks = [
        _line("summary.title"),
        _line("summary.union", n=domains, bound=union_bound(domains)),
        _line("summary.no_rate"),
        _line("summary.frame_h"),
    ]
    # Entry: a reading that differs from the text is a project hypothesis (7.1).
    counts = {e: 0 for e in ENTRIES}
    for i in range(n):
        e = res.get(f"records.{i}.entry")
        if e not in counts:
            raise ReportError(f"records.{i}.entry {e!r} not in {ENTRIES}")
        if "reading_differs" in res.get(f"records.{i}.verdict.flags"):
            e = "project"
        counts[e] += 1
    blocks.append(_table(_line("summary.frame.head"), _line("table.rule2"),
                         *[_line("summary.frame.row", entry=e, n=counts[e]) for e in ENTRIES]))
    blocks.append(_table(
        _line("summary.notested.head"), _line("table.rule2"),
        _line("summary.notested.row", cell="Not encodable", n=int(res.get("sampling_frame.not_encodable"))),
        _line("summary.notested.row", cell="Not sourced", n=int(res.get("sampling_frame.not_sourced"))),
        _line("summary.notested.row", cell="Untestable", n=int(res.get("sampling_frame.untestable"))),
    ))
    for tier, head in (("l4", "summary.l4_h"), ("enc", "summary.enc_h")):
        blocks.append(_line(head))
        group = [i for i in main if _tier(int(res.get(f"records.{i}.level"))) == tier]
        if not group:
            blocks.append(_line("summary.none"))
            continue
        rows = []
        for code in _s_codes():
            sel = [i for i in group if res.get(f"records.{i}.verdict.code") == code]
            if not sel:
                continue
            rows.append(_line(
                "summary.verdict.row", label=LABELS[tier][code], n1=len(sel),
                n2=sum(1 for i in sel if res.get(f"records.{i}.verdict.columns.associated") is True),
                n3=sum(1 for i in sel if res.get(f"records.{i}.verdict.columns.beyond_known_channels") is True)))
        blocks.append(_table(_line("summary.verdict.head"), _line("table.rule4"), *rows))
    blocks.append(_line("summary.ext_h"))
    if ext:
        rows = []
        for i in ext:
            tier = _tier(int(res.get(f"records.{i}.level")))
            rows.append(_line("summary.ext.row", name=res.get(f"records.{i}.name"),
                              label=LABELS[tier][res.get(f"records.{i}.verdict.code")]))
        blocks.append(_table(_line("summary.ext.head"), _line("table.rule2"), *rows))
    else:
        blocks.append(_line("summary.none"))
    out = _join(blocks)
    bad = disallowed_lines(out)
    if bad:
        raise ReportError(f"summary: line outside the allow-list: {bad[0]!r}")
    return out


def _s_codes() -> Tuple[str, ...]:
    return ("S", "C", "E", "N", "U")


def render_methods(res: Results) -> str:
    """Methods page: X9 rates next to the "Not addressed" rule (WP-96 acceptance)."""
    blocks = [_line("methods.title"), _line("methods.x9_h")]
    rows = []
    if res.has("certificate.cases"):
        for j, c in enumerate(res.get("certificate.cases")):
            if c.get("case_id") != "X9":
                continue
            rate = c.get("rate")
            cell = str(c.get("cell") or "all")
            rows.append(_line("methods.x9.row", cell=cell,
                              rate="not recorded" if rate is None else f"{float(rate) * 100:.1f}%"))
    if not rows:
        rows.append(_line("methods.x9.row", cell="no certificate", rate="not recorded"))
    blocks.append(_table(_line("methods.x9.head"), _line("table.rule2"), *rows))
    blocks.append(_line("methods.na_h"))
    nrows = []
    for k in (8, 12, 20):
        f = 1.0 - ALPHA ** (1.0 / k)
        nrows.append(_line("methods.na.row", n=k, pct=_s.fmt_share(f)))
    blocks.append(_table(_line("methods.na.head"), _line("table.rule2"), *nrows))
    blocks.append(_s.render("not_addressed", pct=_s.fmt_share(1.0 - ALPHA ** (1.0 / 8))))
    out = _join(blocks)
    bad = disallowed_lines(out)
    if bad:
        raise ReportError(f"methods: line outside the allow-list: {bad[0]!r}")
    return out


def render_pages(res: Results) -> Dict[str, str]:
    """Every page of the report as {relative path: text}. Sorted by id."""
    n = _n_records(res)
    pages: Dict[str, str] = {}
    order = sorted(range(n), key=lambda i: str(res.get(f"records.{i}.id")))
    for i in order:
        pages[f"card/{res.get(f'records.{i}.id')}.md"] = render_card(res, i)
    pages["summary.md"] = render_summary(res)
    pages["methods.md"] = render_methods(res)
    return pages


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _changelog_head(path: Optional[PathLike]) -> Optional[str]:
    if path is None:
        return None
    verify_chain(path)
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    return _sha(lines[-1].encode("utf-8")) if lines else None


def write_report(results_path: PathLike, out_dir: PathLike, changelog: Optional[PathLike] = None) -> Dict[str, Any]:
    """Build every page from the results file. Stops on provenance problems.

    A provisional or dirty results file, a missing key, or a line outside the
    allow-list stops the build. Writes pages and `report_manifest.json`
    (results hash, changelog head, page hashes) and returns the manifest.
    """
    rp = Path(results_path)
    raw = rp.read_bytes()
    res = Results(json.loads(raw.decode("utf-8")), rp)
    prov = provenance(res.data)
    if prov["problems"] or prov["provisional"] is not False or prov["dirty"] is not False or not prov["commit"]:
        raise ReportError("results are provisional, from a dirty tree, or break the provenance contract")
    pages = render_pages(res)
    out = Path(out_dir)
    for rel, text in pages.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(text.encode("utf-8"))
    manifest = {
        "schema": "validity-report-manifest/1",
        "results": {"path": rp.name, "sha256": _sha(raw)},
        "changelog_head_sha256": _changelog_head(changelog),
        "pages": {rel: _sha(text.encode("utf-8")) for rel, text in sorted(pages.items())},
    }
    (out / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def check_results_hash(results_path: PathLike, manifest: Mapping[str, Any],
                       changelog: Optional[PathLike] = None) -> List[str]:
    """Results bytes against the run manifest, and the changelog chain against its head."""
    problems: List[str] = []
    want = (manifest.get("results") or {}).get("sha256")
    have = _sha(Path(results_path).read_bytes())
    if not want:
        problems.append("HASH manifest has no results hash")
    elif want != have:
        problems.append(f"HASH results file {Path(results_path).name} differs from the run manifest")
    if changelog is not None:
        try:
            head = _changelog_head(changelog)
        except LedgerTamperedError as exc:
            problems.append(f"HASH changelog chain broken: {exc}")
        else:
            if head != manifest.get("changelog_head_sha256"):
                problems.append("HASH changelog head differs from the run manifest")
    return problems


def check_report(results_path: PathLike, pages_dir: PathLike, manifest: Optional[Mapping[str, Any]] = None,
                 changelog: Optional[PathLike] = None) -> List[str]:
    """The report gate (G-08). Returns problems; an empty list passes.

    1. the results file matches the run manifest (default: the manifest in pages_dir);
    2. it is not provisional or dirty and keeps the provenance contract;
    3. every page renders again, byte for byte, from the results file;
    4. no page is missing or extra;
    5. every line of every page is on the allow-list.
    """
    out = Path(pages_dir)
    if manifest is None:
        mp = out / MANIFEST_NAME
        if not mp.exists():
            return [f"HASH no {MANIFEST_NAME} in {out}"]
        manifest = json.loads(mp.read_text(encoding="utf-8"))
    problems = check_results_hash(results_path, manifest, changelog)
    try:
        res = Results.load(results_path)
    except (OSError, ValueError) as exc:
        return problems + [f"ERROR cannot load results: {exc}"]
    prov = provenance(res.data)
    problems += [f"DIRTY {p}" for p in prov["problems"]]
    if prov["provisional"] is not False:
        problems.append("DIRTY results are provisional or lack provisional=false")
    if prov["dirty"] is not False or not prov["commit"]:
        problems.append("DIRTY results were not written from a clean git tree")
    try:
        pages = render_pages(res)
    except (ReportError, KeyError, ValueError, _s.SentenceError) as exc:
        return problems + [f"RENDER cannot render the pages: {exc}"]
    on_disk = {p.relative_to(out).as_posix() for p in out.rglob("*.md")}
    for rel, text in pages.items():
        path = out / rel
        if not path.exists():
            problems.append(f"RENDER page {rel} is missing")
            continue
        got = path.read_bytes()
        if got != text.encode("utf-8"):
            problems.append(f"RENDER page {rel} differs from the template render")
        for ln in disallowed_lines(got.decode("utf-8", "replace")):
            problems.append(f"SENTENCE {rel}: not on the allow-list: {ln!r}")
        if (manifest.get("pages") or {}).get(rel) != _sha(got):
            problems.append(f"HASH page {rel} differs from the run manifest")
    for rel in sorted(on_disk - set(pages)):
        problems.append(f"RENDER page {rel} is not produced by the results file")
        for ln in disallowed_lines((out / rel).read_text(encoding="utf-8", errors="replace")):
            problems.append(f"SENTENCE {rel}: not on the allow-list: {ln!r}")
    return problems
