"""Command line of the mundane engine (ADR-006 section 7.4, WP-56).

Run as ``python -m vedic_astrology_core.mundane.cli <command>``. The console
entry point ``astro-mundane`` is added to pyproject.toml by ADR-004 WP-18,
not here.

Commands: validate, catalogue list|show, chart, casefile, burden, controls,
report. ``report --period confirm`` exits with "not available until WP-63".
Only ``report`` (and the slice run built on it) reads outcomes; ``controls``
reads event dates only; ``casefile`` reads one event.

The slice run (:func:`run_slice`) is the first slice end to end and is called
by ``studies/mundane/scripts/run_slice.py``.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..stats.manifest import file_sha256
from . import aggregate as agg
from . import burden as bur
from . import casefile as cf
from . import controls as ctl
from . import registry as reg
from . import render
from .catalogue import CatalogueError, load_catalogue, repo_root
from .charts import founding_table
from .stability import founding_table_stability

ROOT = repo_root()
ARTIFACTS = ROOT / "studies" / "mundane" / "artifacts"
CONFIRM_MESSAGE = "report --period confirm: not available until WP-63"
DESCRIPTIVE = "descriptive only"


class CliError(ValueError):
    """A command cannot proceed; the message is printed and the exit code is 2."""


# ------------------------------------------------------------------ helpers
def git_state(root: Path = ROOT) -> Dict[str, Any]:
    """Commit and whether the working tree has uncommitted changes."""
    def run(*args: str) -> Optional[str]:
        try:
            out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout if out.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {"commit": commit.strip() if commit else None,
            "dirty": True if status is None else bool(status.strip())}


def plan_input_status(plan: bur.Plan, catalogue=None) -> List[Dict[str, Any]]:
    """Compare the plan's input hashes with the files. A null hash means "not registered"."""
    cat = catalogue or load_catalogue()
    inp = plan["inputs"]
    current = {
        "chart_registry": file_sha256(ROOT / inp["chart_registry"]["path"]),
        "event_registry": file_sha256(ROOT / inp["event_registry"]["path"]),
        "method_catalogue": cat.hash(),
        "earthquake_catalogue": file_sha256(ROOT / inp["earthquake_catalogue"]["path"]),
    }
    rows = []
    for key, now in current.items():
        want = inp[key].get("sha256")
        state = "unregistered" if want is None else ("match" if want == now else "MISMATCH")
        rows.append({"input": key, "plan": want, "current": now, "state": state})
    return rows


def _plan(args: argparse.Namespace) -> bur.Plan:
    return bur.load_plan(args.plan)


def primary_for(plan: bur.Plan, charts: Sequence[reg.Chart]) -> reg.Chart:
    """The primary chart by the plan's rule; the plan's expected chart must agree."""
    iso = plan["scope"]["country_iso"]
    primary = ctl.primary_chart(charts, iso, plan)
    if primary is None:
        raise CliError(f"no eligible primary chart for {iso}")
    exp = plan["charts"]["expected_primary"]
    if primary.chart_id != exp["chart_id"] or reg.chart_grade(primary) != exp["expected_grade"]:
        raise CliError(
            f"primary-chart rule resolves to {primary.chart_id} (grade {reg.chart_grade(primary)}), "
            f"plan expects {exp['chart_id']} (grade {exp['expected_grade']}); on_mismatch={exp['on_mismatch']}")
    return primary


def secondary_charts(plan: bur.Plan, charts: Sequence[reg.Chart], primary: reg.Chart) -> List[reg.Chart]:
    sel = plan["charts"]["secondary"]["selector"]
    return [c for c in charts if c.country_iso == sel["country_iso"] and c.chart_id != primary.chart_id
            and reg.chart_grade(c) in sel["grades"]]


def _countries(e: reg.Event) -> List[str]:
    iso = e.country_iso
    return [] if iso is None else (list(iso) if isinstance(iso, (list, tuple)) else [iso])


def slice_events(plan: bur.Plan, events: Sequence[reg.Event], period: str = "explore") -> List[reg.Event]:
    """Events that enter the counts of the period (exhaustive, mainshocks, magnitude, country)."""
    return ctl.select_events(events, plan, period)


def casefile_events(plan: bur.Plan, events: Sequence[reg.Event]) -> List[reg.Event]:
    """Every Himalayan mainshock at or above the magnitude floor in the plan's country, any period."""
    d = plan["events"]["definition"]
    mag = float((d.get("magnitude") or {}).get("min") or 0)
    out = [e for e in events if e.exhaustive and e.event_type == d["event_type"]
           and d["country_iso"] in _countries(e) and float(e.severity.get("value") or 0) >= mag
           and e.flags.get("mainshock_gk", False)]
    return sorted(out, key=lambda e: (e.time_utc, e.event_id))


def case_file_only_pairs(plan: bur.Plan, events: Sequence[reg.Event], charts: Sequence[reg.Chart]):
    """(event, chart) pairs the plan lists as case-file-only (Gorkha 2015 against Nepal 2008)."""
    sel = plan["charts"]["case_file_only"]
    pairs = []
    for spec, ce in zip(sel, plan["events"]["case_file_only"]):
        s = ce["selector"]
        found = [e for e in events if e.time_utc.date().isoformat() == s["date_utc"]
                 and float(e.severity.get("value") or 0) >= float(s["magnitude_min"])]
        if len(found) != 1:
            raise CliError(f"case-file-only event {ce['key']}: selector matches {len(found)} events")
        ev = found[0]
        if ce.get("expected_event_id") and ev.event_id != ce["expected_event_id"]:
            raise CliError(f"{ce['key']}: selector gives {ev.event_id}, plan expects {ce['expected_event_id']}")
        cs = spec["selector"]
        ch = [c for c in charts if c.country_iso == cs["country_iso"] and c.date.isoformat() == cs["founding_date"]]
        for c in ch:
            pairs.append((ev, c))
    return pairs


def _find_chart(charts: Sequence[reg.Chart], chart_id: str) -> reg.Chart:
    for c in charts:
        if c.chart_id == chart_id:
            return c
    raise CliError(f"unknown chart {chart_id!r}; known: {', '.join(c.chart_id for c in charts)}")


def _find_event(events: Sequence[reg.Event], event_id: str) -> reg.Event:
    for e in events:
        if e.event_id == event_id:
            return e
    raise CliError(f"unknown event {event_id!r}")


def _out_dir(args: argparse.Namespace) -> Path:
    return Path(args.out) if getattr(args, "out", None) else ARTIFACTS


# ----------------------------------------------------------------- commands
def cmd_validate(args: argparse.Namespace) -> int:
    problems: List[str] = []
    charts = reg.load_charts()
    events = reg.load_events()
    cat = load_catalogue()
    plan = _plan(args)
    print(f"charts: {len(charts)}   events: {len(events)}   methods: {len(cat)}   plan: {plan['id']} ({plan['status']})")
    print("chart grades:")
    for c in charts:
        print(f"  {c.chart_id:<22} {c.country_iso}  grade {reg.chart_grade(c)}  half-window {reg.half_window_minutes(c)} min")
    print("method statuses:")
    for m in sorted(cat, key=lambda x: x.id):
        print(f"  {m.id:<28} {m.tier:<9} {m.citation_status(cat.root):<10} L{m.level(cat.root)}")
    try:
        p = primary_for(plan, charts)
        print(f"primary chart: {p.chart_id} (grade {reg.chart_grade(p)})")
    except CliError as exc:
        problems.append(str(exc))
    try:
        for ev, ch in case_file_only_pairs(plan, events, charts):
            print(f"case-file-only: {ev.event_id} against {ch.chart_id} (grade {reg.chart_grade(ch)})")
    except CliError as exc:
        problems.append(str(exc))
    try:
        counts = bur.check_declared(plan)
        bur.check_budget(plan, counts)
        print(f"declared counts: {counts['omnibus_tests']} omnibus tests in {counts['families']} families: ok")
    except bur.PlanError as exc:
        problems.append(str(exc))
    for row in plan_input_status(plan, cat):
        print(f"input {row['input']}: {row['state']}")
        if row["state"] == "MISMATCH":
            problems.append(f"input {row['input']}: plan hash {row['plan']} differs from {row['current']}")
    sel = slice_events(plan, events)
    print(f"explore-period events in the counts: {len(sel)}")
    for line in problems:
        print("ERROR: " + line, file=sys.stderr)
    return 1 if problems else 0


def cmd_catalogue(args: argparse.Namespace) -> int:
    cat = load_catalogue()
    if args.what == "list":
        for m in sorted(cat, key=lambda x: x.id):
            print(f"{m.id:<28} {m.tier:<9} {m.citation_status(cat.root):<10} L{m.level(cat.root)}  {m.name.english}")
        return 0
    if not args.method_id:
        raise CliError("catalogue show needs a method id")
    try:
        m = cat.get(args.method_id)
    except CatalogueError as exc:
        raise CliError(str(exc)) from exc
    s = m.source
    print(f"{m.id}: {m.name.english}")
    print(f"  family {m.family}, tradition {m.tradition}, tier {m.tier}, scope {', '.join(m.scope)}")
    print(f"  status {m.citation_status(cat.root)}, level L{m.level(cat.root)}")
    print(f"  source: {s.text or '-'} / {s.edition or '-'} / chapter {s.chapter or '-'} verse {s.verse or '-'}")
    print(f"  formula: {(m.definition.formula or '-').strip()}")
    print(f"  implementation: {m.implementation.module + '.' + m.implementation.function if m.implementation else 'none'}")
    missing = []
    if not (s.text or "").strip() or not (s.edition or "").strip():
        missing.append("text and edition")
    if not ((s.chapter or "").strip() or (s.verse or "").strip()):
        missing.append("chapter or verse")
    if not (s.quote or "").strip():
        missing.append("quotation")
    if not ((s.checked_by or "").strip() and (s.checked_at or "").strip()):
        missing.append("checked_by and checked_at")
    if m.citation_status(cat.root) == "page_cited":
        missing.append("two existing reference cases for 'verified'")
    print(f"  missing for the next level: {', '.join(missing) if missing else 'nothing'}")
    return 0


def cmd_chart(args: argparse.Namespace) -> int:
    chart = _find_chart(reg.load_charts(), args.chart_id)
    vargas = tuple(v.strip() for v in args.vargas.split(","))
    table = founding_table(chart, vargas)
    stab = founding_table_stability(chart, vargas)
    print(f"{chart.chart_id}  grade {table.grade}  {table.moment_utc.isoformat()}  time known: {table.time_known}")
    head = "point        longitude  " + "  ".join(f"{v:<22}" for v in vargas)
    print(head)
    for row in table.points:
        cells = []
        for v in vargas:
            p = row.vargas[v]
            mark = "" if stab[(row.point, v, "sign")].stable else " unstable"
            house = f" h{p.house}" if p.house is not None else ""
            cells.append(f"{p.sign_name + house + mark:<22}")
        print(f"{row.point:<11} {row.longitude:9.4f}  " + "  ".join(cells))
    return 0


def cmd_casefile(args: argparse.Namespace) -> int:
    charts, events = reg.load_charts(), reg.load_events()
    ev = _find_event(events, args.event_id)
    plan = _plan(args)
    if args.chart == "all":
        chosen = [c for c in charts if c.country_iso in _countries(ev) and reg.chart_grade(c) != "X"]
    elif args.chart:
        chosen = [_find_chart(charts, args.chart)]
    else:
        prim = ctl.primary_chart(charts, plan["scope"]["country_iso"], plan) if plan["scope"]["country_iso"] in _countries(ev) else None
        chosen = [prim] if prim else [c for c in charts if c.country_iso in _countries(ev) and reg.chart_grade(c) != "X"]
    if not chosen:
        raise CliError(f"no chart applies to {ev.event_id}")
    formats = {f.strip() for f in args.format.split(",") if f.strip()}
    bad = formats - {"json", "html", "pdf"}
    if bad:
        raise CliError(f"unknown format {sorted(bad)}")
    out = _out_dir(args) / "cases" if not args.out else Path(args.out)
    cat = load_catalogue()
    for ch in chosen:
        try:
            paths = write_case(ev, ch, out, formats, cat, plan)
        except reg.ChartNotApplicable as exc:
            print(f"skipped {ch.chart_id}: {exc}")
            continue
        for p in paths:
            print(p)
    return 0


def write_case(ev: reg.Event, ch: reg.Chart, out: Path, formats, cat, plan) -> List[Path]:
    case = cf.build_casefile(ev, ch, catalogue=cat, plan_path=plan.path or bur.PLAN_FILE)
    cf.assert_valid(case)
    out.mkdir(parents=True, exist_ok=True)
    jp = cf.write_casefile(case, out)
    paths = [jp]
    if "html" in formats:
        paths.append(render.render_html_file(jp))
    if "pdf" in formats:
        res = render.render_pdf(jp)
        print(res.message)
        if res.path:
            paths.append(res.path)
    return paths


def cmd_burden(args: argparse.Namespace) -> int:
    plan = _plan(args)
    try:
        rep = bur.burden_report(plan)
    except bur.PlanError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    c = rep["plan_counts"]
    print(f"plan {rep['plan_id']}: {c['omnibus_tests']} omnibus tests, {c['families']} families, {c['cells_total']} cells")
    print(f"budget: within caps {rep['budget']['caps']}")
    ss = rep["search_space_full_d1_d9"]
    print("full D1-D9 search space: " + ", ".join(f"{k}={v}" for k, v in ss.items() if not isinstance(v, (dict, list))))
    print(f"event floor for any p-value: {rep['event_floor']}")
    if args.out:
        print(bur.write_burden(rep, args.out))
    return 0


def _draw(plan: bur.Plan, events: Sequence[reg.Event], period: str):
    sel = slice_events(plan, events, period)
    excl = ctl.exclusion_events(events, plan, period)
    return sel, ctl.draw_season_matched(sel, plan, period=period, exclusion=excl)


def cmd_controls(args: argparse.Namespace) -> int:
    plan = _plan(args)
    ctl.period_bounds(plan, args.period)
    sel, draw = _draw(plan, reg.load_events(), args.period)
    path = ctl.write_controls(draw, plan, _out_dir(args))
    short = {k: v for k, v in draw.shortfall.items() if v}
    print(f"{len(sel)} events, {len(draw.all_times())} control dates, shortfall {short or 'none'}")
    print(path)
    return 0


def compute_report(plan: bur.Plan, chart: reg.Chart, events, draw, cat, *, period: str,
                   grid: bool, placebos=(), provisional: bool) -> Dict[str, Any]:
    data = agg.collect_test_data(plan, chart, events, draw, catalogue=cat, grid=grid, placebos=placebos)
    return agg.build_report(plan, data, period=period, provisional=provisional, chart_id=chart.chart_id)


def cmd_report(args: argparse.Namespace) -> int:
    plan = _plan(args)
    ctl.period_bounds(plan, args.period)  # confirm raises ConfirmNotAvailable
    charts, events, cat = reg.load_charts(), reg.load_events(), load_catalogue()
    bad = [r for r in plan_input_status(plan, cat) if r["state"] == "MISMATCH"]
    if bad:
        raise CliError("plan input hashes differ from the files: " + ", ".join(r["input"] for r in bad))
    chart = _find_chart(charts, args.chart) if args.chart else primary_for(plan, charts)
    sel, draw = _draw(plan, events, args.period)
    git = git_state()
    floor = int(plan["budgets"]["min_events_for_test"])
    rep = compute_report(plan, chart, sel, draw, cat, period=args.period,
                         grid=len(sel) >= floor, provisional=git["dirty"])
    out = _out_dir(args)
    rp, fp = agg.write_report(rep, out / "results.json", out / "factor_table.csv")
    for line in rep["headline"]:
        print(line)
    print(rp)
    print(fp)
    return 0


# ---------------------------------------------------------------- slice run
def run_slice(plan_path: Path = bur.PLAN_FILE, out: Path = ARTIFACTS, *, formats=("json", "html")) -> Dict[str, Any]:
    """The first slice end to end. Returns a summary dict (also in results.json under "slice")."""
    plan = bur.load_plan(plan_path)
    charts, events, cat = reg.load_charts(), reg.load_events(), load_catalogue()
    status = plan_input_status(plan, cat)
    bad = [r["input"] for r in status if r["state"] == "MISMATCH"]
    if bad:
        raise CliError("plan input hashes differ from the files: " + ", ".join(bad))
    primary = primary_for(plan, charts)
    secondary = secondary_charts(plan, charts, primary)
    git = git_state()
    out = Path(out)

    burden = bur.burden_report(plan)
    bur.write_burden(burden, out / "burden.json")

    sel, draw = _draw(plan, events, "explore")
    ctl.write_controls(draw, plan, out)

    # Case files: every India Himalayan mainshock against every India candidate, plus the plan's case-file-only pairs.
    cases: List[Dict[str, Any]] = []
    cf_events = casefile_events(plan, events)
    pairs = [(e, c) for e in cf_events for c in [primary, *secondary]]
    pairs += case_file_only_pairs(plan, events, charts)
    for ev, ch in pairs:
        try:
            write_case(ev, ch, out / "cases", set(formats), cat, plan)
            cases.append({"event_id": ev.event_id, "chart_id": ch.chart_id, "grade": reg.chart_grade(ch)})
        except reg.ChartNotApplicable as exc:
            cases.append({"event_id": ev.event_id, "chart_id": ch.chart_id, "skipped": str(exc)})

    floor = int(plan["budgets"]["min_events_for_test"])
    grid = len(sel) >= floor
    rep = compute_report(plan, primary, sel, draw, cat, period="explore", grid=grid,
                         provisional=git["dirty"])
    secondary_out = {}
    for ch in secondary:
        sr = compute_report(plan, ch, sel, draw, cat, period="explore", grid=grid, provisional=git["dirty"])
        rp, fp = agg.write_report(sr, out / "secondary" / f"{ch.chart_id}_results.json",
                                  out / "secondary" / f"{ch.chart_id}_factor_table.csv")
        secondary_out[ch.chart_id] = {"grade": reg.chart_grade(ch), "descriptive_only": sr["descriptive_only"],
                                      "results": str(rp.relative_to(ROOT)), "factor_table": str(fp.relative_to(ROOT))}
    summary = {
        "n_events_counts": len(sel),
        "n_events_case_files": len(cf_events),
        "event_ids_counts": [e.event_id for e in sel],
        "primary_chart": {"chart_id": primary.chart_id, "grade": reg.chart_grade(primary)},
        "secondary_charts": {c.chart_id: reg.chart_grade(c) for c in secondary},
        "case_file_only": [{"event_id": e.event_id, "chart_id": c.chart_id, "grade": reg.chart_grade(c)}
                           for e, c in case_file_only_pairs(plan, events, charts)],
        "verdict": DESCRIPTIVE if len(sel) < floor or rep["descriptive_only"] else "see report",
        "event_floor": floor,
        "case_files": cases,
        "secondary": secondary_out,
        "input_hashes": status,
        "commit": git["commit"],
        "tree_dirty": git["dirty"],
    }
    rep["slice"] = summary
    rep["provisional"] = bool(git["dirty"])
    rp, fp = agg.write_report(rep, out / "results.json", out / "factor_table.csv")
    summary["outputs"] = {"results": str(rp), "factor_table": str(fp),
                          "burden": str(out / "burden.json"), "controls": str(ctl.controls_path(plan, out)),
                          "cases": str(out / "cases")}
    return summary


# --------------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astro-mundane", description="Retrospective mundane chart engine (ADR-006)")
    p.add_argument("--plan", default=str(bur.PLAN_FILE), help="plan file (default studies/mundane/hypothesis.yaml)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check registries, catalogue and plan; print grades and statuses")
    c = sub.add_parser("catalogue", help="method catalogue")
    c.add_argument("what", choices=["list", "show"])
    c.add_argument("method_id", nargs="?")
    c = sub.add_parser("chart", help="founding chart table with stability marks")
    c.add_argument("chart_id")
    c.add_argument("--vargas", default="D1,D9")
    c = sub.add_parser("casefile", help="case file of one event")
    c.add_argument("event_id")
    c.add_argument("--chart", default=None, help="chart id, or 'all' (default: the plan's primary chart)")
    c.add_argument("--format", default="json", help="comma list of json,html,pdf")
    c.add_argument("--out", default=None)
    c = sub.add_parser("burden", help="factor and test counts, MDE table, budget check")
    c.add_argument("--out", default=None, help="also write burden.json here")
    c = sub.add_parser("controls", help="draw and write control dates (reads event dates only)")
    c.add_argument("--period", default="explore", choices=["explore", "confirm"])
    c.add_argument("--out", default=None)
    c = sub.add_parser("report", help="aggregate report (reads outcomes)")
    c.add_argument("--period", default="explore", choices=["explore", "confirm"])
    c.add_argument("--chart", default=None)
    c.add_argument("--out", default=None)
    return p


COMMANDS = {"validate": cmd_validate, "catalogue": cmd_catalogue, "chart": cmd_chart,
            "casefile": cmd_casefile, "burden": cmd_burden, "controls": cmd_controls,
            "report": cmd_report}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(COMMANDS[args.command](args) or 0)
    except ctl.ConfirmNotAvailable:
        print(CONFIRM_MESSAGE, file=sys.stderr)
        return 2
    except (CliError, bur.PlanError, ctl.ControlError, reg.RegistryError, agg.AggregateError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
