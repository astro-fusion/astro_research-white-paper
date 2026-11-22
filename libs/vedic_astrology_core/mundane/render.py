"""Renderers of the case file (ADR-006 section 2.1 and 6.4, WP-54).

HTML and PDF are rendered from the case-file JSON and add nothing: no function
here computes a chart, a dasha, a transit or a factor. The same JSON gives the
same bytes on every run (no timestamp, no random id, sorted where order is not
the data's own).

* :func:`render_html`: one self-contained file (inline CSS, no script, no
  external resource). Unverified and extended methods carry a visible label
  wherever they appear.
* :func:`render_markdown`: the same content as Quarto markdown.
* :func:`render_pdf`: Quarto renders that markdown to PDF; when Quarto is not
  installed the result says so and nothing is written.

The template is ``templates/casefile.html``, filled with :class:`string.Template`
(``jinja2`` is not a dependency of the repository).
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

TEMPLATE_PATH = Path(__file__).with_name("templates") / "casefile.html"
SKIP_MESSAGE = "Quarto is not installed (or not on PATH): PDF skipped. Install Quarto to render PDF."
SCHEMA_ID = "casefile/1"

CSS = """
:root { color-scheme: light; }
body { font: 15px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: #1b1b1b; max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; }
h2 { font-size: 1.15rem; margin: 2rem 0 .5rem; border-bottom: 2px solid #1b1b1b; padding-bottom: .15rem; }
h3 { font-size: 1rem; margin: 1.2rem 0 .3rem; }
table { border-collapse: collapse; width: 100%; margin: .4rem 0 1rem; font-size: .86rem; }
th, td { border: 1px solid #bbb; padding: .25rem .45rem; text-align: left; vertical-align: top; }
th { background: #eee; }
.lede, .note { color: #444; }
.nc { background: #f4f4f4; border-left: 4px solid #777; padding: .5rem .75rem; }
.badge { display: inline-block; font-size: .72rem; font-weight: 700; border: 1px solid #333; border-radius: 3px; padding: 0 .35rem; margin-left: .3rem; text-transform: uppercase; }
.b-unverified { background: #fff3cd; border-color: #8a6d00; color: #5c4900; }
.b-extended { background: #f8d7da; border-color: #8b1a24; color: #6b101a; }
.b-page_cited { background: #e2f0d9; border-color: #3a6b25; color: #264a16; }
.b-verified { background: #d1ecf1; border-color: #0c5460; color: #0c5460; }
.unstable { background: #fff0e0; border-bottom: 2px dotted #b45309; }
.mono { font-family: ui-monospace, Menlo, Consolas, monospace; }
footer { margin-top: 2rem; font-size: .8rem; color: #555; }
"""


# ------------------------------------------------------------------ helpers
def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt(value: Any) -> str:
    """Plain text of a JSON value (for both HTML and markdown)."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4g}" if abs(value) < 1000 else f"{value:.1f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(fmt(v) for v in value) if value else "-"
    if isinstance(value, Mapping):
        return "; ".join(f"{k}: {fmt(v)}" for k, v in value.items())
    return str(value)


def _level(value: Any) -> str:
    return value if isinstance(value, str) else f"L{value}"


def _badges(status: Optional[str], tier: Optional[str]) -> str:
    out = ""
    if status:
        label = {"unverified": "unverified", "page_cited": "page cited", "verified": "verified"}.get(status, status)
        out += f'<span class="badge b-{_e(status)}">{_e(label)}</span>'
    if tier == "extended":
        out += '<span class="badge b-extended">extended: not cited, never in a test</span>'
    elif tier in ("phase2", "phase3"):
        out += f'<span class="badge b-extended">{_e(tier)}</span>'
    return out


def _md_badges(status: Optional[str], tier: Optional[str]) -> str:
    out = f"[{status}]" if status else ""
    if tier == "extended":
        out += " [EXTENDED: not cited, never in a test]"
    elif tier in ("phase2", "phase3"):
        out += f" [{tier}]"
    return out


def _table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Rows are already-escaped HTML cells."""
    head = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _kv(rows: Iterable[Sequence[Any]]) -> str:
    return _table(["Field", "Value"], ([f"{_e(k)}", f"{_e(fmt(v))}"] for k, v in rows))


def _nc(reason: Optional[str]) -> str:
    return f'<p class="nc"><strong>Not computable.</strong> {_e(reason)}</p>'


def _alts_text(alts: Sequence[Mapping[str, Any]]) -> str:
    return "; ".join(f"{a['field']}: {fmt(a['value'])} ({a['share'] * 100:.0f}%)" for a in alts)


def _unstable(text: str, alts: Sequence[Mapping[str, Any]]) -> str:
    return f'<span class="unstable" title="{_e(_alts_text(alts))}">{_e(text)}<br><small>unstable: {_e(_alts_text(alts))}</small></span>'


def _generic_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return '<p class="note">No rows.</p>'
    keys = list(rows[0])
    return _table(keys, ([_e(fmt(r.get(k))) for k in keys] for r in rows))


# --------------------------------------------------------------- the sections
def _sec_header(case: Mapping[str, Any]) -> str:
    ev, ch = case["event"], case["chart"]
    e_rows = [
        ("Event id", ev["event_id"]), ("Type", ev["event_type"]), ("Subtype", ev.get("subtype")),
        ("Time (UTC)", ev["time_utc"]), ("Time precision", ev["time_precision"]),
        ("Place (lat, lon)", f"{fmt(ev.get('lat'))}, {fmt(ev.get('lon'))}"),
        ("Location precision (km)", ev.get("location_precision_km")),
        ("Severity", ev.get("severity")), ("Country", ev.get("country_iso")),
        ("Catalogue", (ev.get("catalogue") or {}).get("name")),
        ("Source", ev.get("source_url")), ("Archive", ev.get("archive_url")),
    ]
    c_rows = [
        ("Chart id", ch["chart_id"]), ("Grade", ch["grade"]),
        ("Half-window (minutes)", ch["half_window_minutes"]),
        ("Founding", f"{ch['founding_date']} {fmt(ch.get('founding_time'))} {ch['time_zone']}, {ch['place']}"),
        ("Time evidence", ch.get("time_evidence_kind")),
        ("Stated precision (minutes)", ch.get("stated_precision_minutes")),
        ("Time source", ch.get("source_title")), ("Source URL", ch.get("source_url")),
        ("Source checked by", ch.get("checked_by")), ("Rectified", ch.get("rectified")),
        ("Valid from", ch["valid_from"]),
    ]
    return "<h3>Event</h3>" + _kv(e_rows) + "<h3>Chart</h3>" + _kv(c_rows)


def _sec_natal(sec: Mapping[str, Any]) -> str:
    if not sec["computable"]:
        return _nc(sec["reason"])
    out = []
    if sec.get("note"):
        out.append(f'<p class="note">{_e(sec["note"])}</p>')
    out.append(f'<p class="note">Window: half-window {_e(fmt(sec["window"]["half_window_minutes"]))} min, grid {_e(fmt(sec["window"]["grid_minutes"]))} min. Combustion: {_e(sec.get("combust_convention"))}. A shaded cell changes inside the window and lists every value it takes.</p>')
    vargas = sec["vargas"]
    headers = ["Point", "Longitude", "Nakshatra, pada", "Retro", "Combust"] + [f"{v}: sign, house, dignity" for v in vargas]
    rows = []
    for p in sec["points"]:
        nk = f"{p['nakshatra']} {p['pada']}"
        nk_cell = _unstable(nk, p["point_alternatives"]) if not p["point_stable"] else _e(nk)
        cells = [_e(p["point"]), _e(f"{p['longitude']:.2f} ({p['degree_in_sign']:.2f} in sign)"), nk_cell,
                 _e(fmt(p.get("retrograde"))), _e(fmt(p.get("combust")))]
        for v in vargas:
            c = p["vargas"][v]
            text = ", ".join([c["sign"], f"house {c['house']}" if c["house"] is not None else "no house",
                              fmt(c["dignity"]) if c.get("dignity") is not None else (f"hora {c['hora_lord']}" if c.get("hora_lord") else "-")])
            cells.append(_unstable(text, c["alternatives"]) if not c["stable"] else _e(text))
        rows.append(cells)
    out.append(_table(headers, rows))
    return "".join(out)


def _sec_dasha(sec: Mapping[str, Any]) -> str:
    if not sec["computable"]:
        return _nc(sec["reason"])
    out = ['<p class="note">Method dasha.vimshottari '
           + _badges("unverified", "core") + f" Dasha year {_e(fmt(sec['dasha_year_days']))} days.</p>"]
    if sec.get("note"):
        out.append(_nc(sec["note"]))
    rows = []
    for lv in sec["levels"]:
        ls = lv.get("lord_state") or {}
        def cell(v: str) -> str:
            d = ls.get(v) if ls.get("computable") else None
            if not d:
                return _e(ls.get("reason") or "-")
            return _e(f"{d['sign']}, house {d['house']}, rules {fmt(d['houses_ruled'])}, {fmt(d['dignity'])}")
        stable = "yes" if lv["stable"] else ("unsupported" if not lv["supported"] else "no")
        stable_cell = _e(stable) if lv["stable"] or not lv["reason"] else f'<span class="unstable">{_e(stable)}<br><small>{_e(lv["reason"])}</small></span>'
        rows.append([_e(lv["name"]), _e(fmt(lv.get("lord"))), _e(fmt(lv.get("start"))), _e(fmt(lv.get("end"))),
                     _e(fmt(lv.get("boundary_uncertainty_days"))), stable_cell, cell("D1"), cell("D9")])
    out.append(_table(["Level", "Lord", "Start", "End", "Boundary uncertainty (days)", "Stable", "Lord in D1", "Lord in D9"], rows))
    return "".join(out)


def _method_line(info: Optional[Mapping[str, Any]]) -> str:
    if not info:
        return ""
    return f"{_e(info.get('id'))} " + _badges(info.get("citation_status"), info.get("tier")) + f' <span class="note">level {_e(_level(info.get("level")))}</span>'


def _sec_transits(sec: Mapping[str, Any]) -> str:
    if not sec["computable"]:
        return _nc(sec["reason"])
    out = []
    if sec.get("note"):
        out.append(f'<p class="note">{_e(sec["note"])}</p>')
    rows = []
    for p in sec["positions"]:
        def house(key: str) -> str:
            v, st = p.get(key), p.get(key + "_stable")
            if v is None:
                return "-"
            return _e(v) if st else f'<span class="unstable">{_e(v)} (unstable)</span>'
        rows.append([_e(p["graha"]), _e(f"{p['longitude']:.2f}"), _e(p["sign"]), _e(p["nakshatra"]), _e(fmt(p["speed"])),
                     _e(fmt(p["retrograde"])), house("house_from_lagna"), house("house_from_moon")])
    out.append(_table(["Graha", "Longitude", "Sign", "Nakshatra", "Speed", "Retro", "House from lagna", "House from Moon"], rows))
    for block, title in (("core", "Catalogued readings"), ("extended", "Extended readings (not cited; never in a test)")):
        items = sec["readings"].get(block) or {}
        if not items:
            continue
        out.append(f"<h3>{_e(title)}</h3>")
        for mid, rd in items.items():
            out.append(f"<h4>{_method_line(rd.get('method'))}</h4>")
            if rd.get("note"):
                out.append(f'<p class="note">{_e(rd["note"])}</p>')
            out.append(_generic_rows(rd.get("rows") or []))
    return "".join(out)


def _sec_event_sky(sec: Mapping[str, Any]) -> str:
    if not sec["computable"]:
        return _nc(sec["reason"])
    def marked(d: Mapping[str, Any]) -> str:
        v = fmt(d.get("value"))
        return v if d.get("stable", True) else f"{v} (unstable: {fmt(d.get('values_across_window'))})"
    lagna = sec["lagna"]
    ecl = sec["eclipses"]
    def ecl_text(x: Optional[Mapping[str, Any]]) -> str:
        return "-" if not x else f"{x['subtype']} {x['kind']} at {x['moment_utc']} ({x['days_from_event']} days)"
    rows = [
        ("Lagna at the epicentre", marked(lagna) if lagna.get("computed") else f"not computed: {lagna.get('reason')}"),
        ("Moon nakshatra", f"{marked(sec['moon_nakshatra'])}, pada {sec['moon_nakshatra']['pada']}"),
        ("Brihat Samhita ch. 32 mandala", marked(sec["mandala"])),
        ("Tithi", f"{sec['tithi']['name']} ({marked(sec['tithi'])})"),
        ("Weekday lord", f"{marked(sec['weekday_lord'])} ({sec['weekday_lord']['convention']})"),
        ("Eclipse before", ecl_text(ecl.get("before"))), ("Eclipse after", ecl_text(ecl.get("after"))),
        ("Samvatsara", f"{sec['samvatsara']['name']} ({sec['samvatsara']['convention']})"),
    ]
    out = [_kv(rows)]
    meths = sec.get("methods") or {}
    if meths:
        out.append("<p>Methods: " + "; ".join(_method_line(m) for m in meths.values()) + "</p>")
    return "".join(out)


def _sec_factors(sec: Mapping[str, Any]) -> str:
    if not sec["computable"]:
        return _nc(sec["reason"]) + _not_evaluated(sec)
    out = [f'<p class="note">{_e(sec.get("base_rate_note"))}. Plan {_e(sec.get("plan_id"))}: {_e(sec.get("tests_declared"))} tests declared, {len(sec["rows"])} fired.</p>']
    rows = []
    for r in sec["rows"]:
        stable = "yes" if r["stable"] else f'<span class="unstable">no</span>'
        if not r["stable"]:
            d = r["stability"]["detail"]
            why = ", ".join(k.replace("_", " ") for k, v in d.items() if v is False)
            alts = fmt(r["stability"]["alternatives"])
            stable += f'<br><small>unstable: {_e(why)}; also takes {_e(alts)}</small>'
        br = r["base_rate"]
        br_text = f"{br['value'] * 100:.1f}%" if br.get("value") is not None else f"unknown: {br.get('reason')}"
        rows.append([
            f'<span class="mono">{_e(r["factor_id"])}</span>',
            _e(r["method"]) + "<br>" + "".join(_badges(m["citation_status"], m["tier"]) for m in [{"citation_status": r["citation_status"], "tier": r["tier"]}]),
            _e(" + ".join(m["id"] for m in r["methods"])),
            _e(_level(r["level"])), stable, _e(br_text), _e(r["evidence"]),
        ])
    out.append(_table(["Factor", "Method and status", "Methods used", "Level", "Stable", "Base rate", "Evidence (rule engine)"], rows))
    out.append(_not_evaluated(sec))
    return "".join(out)


def _not_evaluated(sec: Mapping[str, Any]) -> str:
    ne = sec.get("not_evaluated") or []
    if not ne:
        return ""
    return "<h3>Tests not evaluated</h3>" + _table(["Test", "Reason"], ([_e(n["test_id"]), _e(n["reason"])] for n in ne))


def _sec_claims(sec: Mapping[str, Any]) -> str:
    if not sec["computable"]:
        return _nc(sec["reason"])
    if not sec["rows"]:
        return '<p class="note">No claim in the registry names this event.</p>'
    return _generic_rows(sec["rows"])


def _sec_provenance(case: Mapping[str, Any]) -> str:
    p, s = case["provenance"], case["settings"]
    return _kv(list(p.items()) + [("settings", s)])


# -------------------------------------------------------------------- HTML
def render_html(case: Mapping[str, Any]) -> str:
    """The case file as one self-contained HTML page (pure function of the JSON)."""
    if case.get("schema") != SCHEMA_ID:
        raise ValueError(f"not a {SCHEMA_ID} document")
    handlers = {
        "header": lambda: _sec_header(case),
        "natal": lambda: _sec_natal(case["natal"]),
        "dasha": lambda: _sec_dasha(case["dasha"]),
        "transits": lambda: _sec_transits(case["transits"]),
        "event_sky": lambda: _sec_event_sky(case["event_sky"]),
        "annual": lambda: _nc(case["annual"]["reason"]) if not case["annual"]["computable"] else _kv(case["annual"].items()),
        "factors": lambda: _sec_factors(case["factors"]),
        "claims": lambda: _sec_claims(case["claims"]),
        "provenance": lambda: _sec_provenance(case),
    }
    parts: List[str] = []
    for s in case["sections"]:
        parts.append(f'<section id="s{s["number"]}"><h2>{s["number"]}. {_e(s["title"])}</h2>{handlers[s["key"]]()}</section>')
    ev, ch = case["event"], case["chart"]
    lede = f"{ev['event_id']} against chart {ch['chart_id']} (grade {ch['grade']}). A reading aid, not a finding: nothing here is tested."
    return Template(TEMPLATE_PATH.read_text(encoding="utf-8")).safe_substitute(
        title=_e(ev["title"] + " / " + ch["chart_id"]), css=CSS.strip("\n"), lede=_e(lede),
        body="\n".join(parts), schema_id=_e(case["schema"]),
    )


# ---------------------------------------------------------------- markdown
def _md_cell(value: Any) -> str:
    return fmt(value).replace("|", "/").replace("\n", " ")


def _md_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def render_markdown(case: Mapping[str, Any]) -> str:
    """The same content as Quarto markdown (pure function of the JSON)."""
    if case.get("schema") != SCHEMA_ID:
        raise ValueError(f"not a {SCHEMA_ID} document")
    ev, ch = case["event"], case["chart"]
    out = [f'---\ntitle: "{ev["title"]} / {ch["chart_id"]}"\n---\n',
           f"Chart grade {ch['grade']}. A reading aid, not a finding: nothing here is tested.\n"]
    def head(s: Mapping[str, Any]) -> str:
        return f"## {s['number']}. {s['title']}\n"
    for s in case["sections"]:
        out.append(head(s))
        key = s["key"]
        if key == "header":
            out.append(_md_table(["Field", "Value"], list(ev.items())[:12] + [("chart", ch["chart_id"]), ("grade", ch["grade"]), ("half-window (min)", ch["half_window_minutes"]), ("founding", f"{ch['founding_date']} {ch['founding_time']} {ch['time_zone']}")]))
        elif key == "provenance":
            out.append(_md_table(["Field", "Value"], list(case["provenance"].items())))
        elif not s["computable"]:
            out.append(f"Not computable. {s['reason']}\n")
        elif key == "natal":
            sec = case["natal"]
            out.append(_md_table(["Point", "Longitude", "Nakshatra"] + list(sec["vargas"]), (
                [p["point"], f"{p['longitude']:.2f}", f"{p['nakshatra']} {p['pada']}" + ("" if p["point_stable"] else " (unstable)")]
                + [f"{p['vargas'][v]['sign']} h{p['vargas'][v]['house']} {fmt(p['vargas'][v]['dignity'])}" + ("" if p["vargas"][v]["stable"] else " (unstable)") for v in sec["vargas"]]
                for p in sec["points"])))
        elif key == "dasha":
            out.append(_md_table(["Level", "Lord", "Start", "End", "Uncertainty (d)", "Stable"], (
                [lv["name"], lv.get("lord"), lv.get("start"), lv.get("end"), lv.get("boundary_uncertainty_days"), "yes" if lv["stable"] else ("unsupported" if not lv["supported"] else "no")] for lv in case["dasha"]["levels"])))
        elif key == "transits":
            out.append(_md_table(["Graha", "Longitude", "Sign", "Nakshatra", "Retro", "House from lagna", "House from Moon"], (
                [p["graha"], f"{p['longitude']:.2f}", p["sign"], p["nakshatra"], p["retrograde"], p["house_from_lagna"], p["house_from_moon"]] for p in case["transits"]["positions"])))
            if case["transits"]["readings"].get("extended"):
                out.append("Extended readings (not cited, never in a test) are in the JSON.\n")
        elif key == "event_sky":
            sky = case["event_sky"]
            out.append(_md_table(["Field", "Value"], [("lagna", sky["lagna"].get("value")), ("moon nakshatra", sky["moon_nakshatra"]["value"]), ("mandala", sky["mandala"]["value"]), ("tithi", sky["tithi"]["name"]), ("weekday lord", sky["weekday_lord"]["value"]), ("samvatsara", sky["samvatsara"]["name"])]))
        elif key == "factors":
            f = case["factors"]
            out.append(_md_table(["Factor", "Status", "Level", "Stable", "Base rate", "Evidence"], (
                [r["factor_id"], _md_badges(r["citation_status"], r["tier"]), _level(r["level"]), "yes" if r["stable"] else "no",
                 f"{r['base_rate']['value'] * 100:.1f}%" if r["base_rate"].get("value") is not None else "unknown", r["evidence"]] for r in f["rows"])))
            if f["not_evaluated"]:
                out.append("Tests not evaluated:\n\n" + "\n".join(f"- {n['test_id']}: {n['reason']}" for n in f["not_evaluated"]) + "\n")
        elif key == "claims":
            out.append(_md_table(["Claim"], ([fmt(c)] for c in case["claims"]["rows"])) if case["claims"]["rows"] else "No claim names this event.\n")
        else:
            out.append(fmt(case[key]) + "\n")
    return "\n".join(out)


# --------------------------------------------------------------------- files
def load_casefile_json(path: Union[str, Path]) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def render_html_file(json_path: Union[str, Path], out_path: Optional[Union[str, Path]] = None) -> Path:
    """Render ``<name>.json`` to ``<name>.html`` beside it (or ``out_path``)."""
    src = Path(json_path)
    dst = Path(out_path) if out_path else src.with_suffix(".html")
    dst.write_text(render_html(load_casefile_json(src)), encoding="utf-8")
    return dst


@dataclass(frozen=True)
class PdfResult:
    """Outcome of :func:`render_pdf`."""

    path: Optional[Path]
    skipped: bool
    message: str


def render_pdf(json_path: Union[str, Path], out_path: Optional[Union[str, Path]] = None, *, quarto: Optional[str] = None) -> PdfResult:
    """PDF by Quarto from the JSON; skipped with a clear message if Quarto is absent."""
    exe = quarto if quarto is not None else shutil.which("quarto")
    if not exe:
        return PdfResult(None, True, SKIP_MESSAGE)
    src = Path(json_path)
    dst = Path(out_path) if out_path else src.with_suffix(".pdf")
    md = render_markdown(load_casefile_json(src))
    with tempfile.TemporaryDirectory(prefix="casefile_") as tmp:
        qmd = Path(tmp) / "casefile.qmd"
        qmd.write_text(md, encoding="utf-8")
        run = subprocess.run([exe, "render", str(qmd), "--to", "typst"], capture_output=True, text=True, cwd=tmp)
        built = Path(tmp) / "casefile.pdf"
        if run.returncode != 0 or not built.exists():
            tail = (run.stderr or run.stdout or "").strip().splitlines()[-5:]
            return PdfResult(None, True, "Quarto failed, PDF skipped: " + " | ".join(tail))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built, dst)
    return PdfResult(dst, False, f"wrote {dst}")


__all__ = [
    "PdfResult", "SKIP_MESSAGE", "fmt", "load_casefile_json", "render_html", "render_html_file",
    "render_markdown", "render_pdf",
]
