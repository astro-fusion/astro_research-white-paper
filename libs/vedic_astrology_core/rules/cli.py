"""``astro-rules``: validate, test, explain and list astrological rules.

Examples::

    astro-rules validate                    # every rules/**/*.yaml
    astro-rules test rules/general          # run the reference cases
    astro-rules explain general.gaja_kesari.moon_kendra 2024-05-03T06:00:00Z
    astro-rules explain mundane.ch7.oath_aquarius_baseline_penalty
        2024-06-09T19:15:00 --lat 28.61 --lon 77.21 --tz Asia/Kolkata
    astro-rules list --domain seismic --tier experimental
    astro-rules list --predicates
    astro-rules fit seismic.mangal_ketu_primary --study earthquake --by @me
    astro-rules confirm seismic.mangal_ketu_primary --study earthquake
    astro-rules dose seismic.mangal_shani_malefic --study earthquake
    astro-rules review seismic.mangal_ketu_primary --by @me --verdict faithful
        --note "orb and planets match BS 17"

fit, dose and confirm follow ADR-003: fit and dose see the EXPLORE period
only; confirm runs once per rule version on the CONFIRM period and stamps
the result into the rule file.

Exit codes: 0 success, 1 validation or test failures, 2 usage errors.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

import pytz

from .context import MissingInputError
from .engine import RuleNotEvaluable, evaluate, run_reference_cases
from .loader import RuleRegistry, default_rules_dir, load_rules
from .predicates import PREDICATES
from .schema import ChartSpec, Place, json_schema


def _paths(args: argparse.Namespace) -> List[str]:
    paths = list(getattr(args, "paths", None) or [])
    if not paths and getattr(args, "rules_dir", None):
        paths = [args.rules_dir]
    return paths or [str(default_rules_dir())]


def _validate(args: argparse.Namespace) -> int:
    loaded, problems = load_rules(_paths(args))
    for problem in problems:
        print(problem)
    if problems:
        files = len({p.path for p in problems})
        print(f"\n{len(problems)} problems in {files} files; {len(loaded)} rules valid")
        return 1
    print(f"{len(loaded)} rules valid")
    return 0


def _test(args: argparse.Namespace) -> int:
    loaded, problems = load_rules(_paths(args))
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} validation problems; fix them before testing")
        return 1
    passed = failed = known = skipped = 0
    flagged: List[str] = []
    for item in sorted(loaded, key=lambda x: x.rule.id):
        rule = item.rule
        if rule.status == "needs_predicates":
            skipped += 1
            print(f"SKIP {rule.id} (needs_predicates)")
            continue
        if rule.status == "needs_verification":
            flagged.append(rule.id)
        results = run_reference_cases(rule)
        bad = [r for r in results if not r.passed]
        passed += len(results) - len(bad)
        if not bad:
            print(f"PASS {rule.id} ({len(results)} cases)")
            if rule.status == "needs_verification":
                print("  note: all cases pass now; remove 'status: needs_verification'")
            continue
        for res in bad:
            case = rule.reference_cases[res.index]
            if rule.status == "needs_verification":
                known += 1
                print(f"KNOWN {rule.id} case {res.index} (needs_verification)")
                continue
            failed += 1
            got = (
                f"error: {res.error}"
                if res.error
                else f"got {'fires' if res.fired else 'silent'}"
            )
            print(
                f"FAIL {rule.id} case {res.index} ({case.moment.isoformat()}): "
                f"expected {res.expected}, {got}"
            )
            print(f"  file: {item.path}")
            print(f"  note: {case.note}")
            if res.tree is not None:
                print(res.tree.render(1))
    print(
        f"\ncases: {passed} passed, {failed} failed, {known} known "
        f"(needs_verification); rules skipped: {skipped} (needs_predicates)"
    )
    if flagged:
        print("needs_verification rules: " + ", ".join(flagged))
    return 1 if failed else 0


def parse_moment(text: str, tz: Optional[str]) -> datetime:
    """Parse ISO-8601; a naive time is read in ``tz`` (required then)."""
    value = text.strip().replace("Z", "+00:00").replace("z", "+00:00")
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"cannot read the moment '{text}'; use ISO-8601 such as "
            "2024-05-03T06:00:00+05:45"
        ) from None
    if moment.tzinfo is None:
        if not tz:
            raise ValueError(
                f"the moment '{text}' has no time zone: add an offset "
                "(+05:45, Z) or --tz Asia/Kathmandu"
            )
        moment = pytz.timezone(tz).localize(moment)
    return moment


def _explain(args: argparse.Namespace) -> int:
    try:
        registry = RuleRegistry.load(_paths(args))
        rule = registry.get(args.rule_id)
        moment = parse_moment(args.moment, args.tz)
        place = None
        if args.lat is not None or args.lon is not None:
            if args.lat is None or args.lon is None:
                raise ValueError("give both --lat and --lon")
            place = Place(lat=args.lat, lon=args.lon, tz=args.tz or "UTC")
        natal = None
        if args.natal_moment:
            natal_place = None
            if args.natal_lat is not None and args.natal_lon is not None:
                natal_place = Place(
                    lat=args.natal_lat, lon=args.natal_lon, tz=args.natal_tz or "UTC"
                )
            natal = ChartSpec(
                moment=parse_moment(args.natal_moment, args.natal_tz),
                place=natal_place,
            )
        result = evaluate(rule, moment, place, natal)
    except (KeyError, ValueError, MissingInputError, RuleNotEvaluable) as exc:
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else exc
        print(f"astro-rules explain: {message}", file=sys.stderr)
        return 2
    graded = None
    if args.strength:
        from .engine import build_context
        from .strength import strength_value

        if rule.strength is None:
            graded = (1.0 if result.fired else 0.0, ["binary rule (no strength)"])
        elif not result.fired:
            graded = (0.0, ["the rule is silent"])
        else:
            graded = strength_value(
                rule.strength, build_context(rule, moment, place, natal)
            )
    if args.json:
        doc = {"rule": rule.id, "fired": result.fired, "tree": result.tree.to_dict()}
        if graded is not None:
            doc["strength"] = {"value": graded[0], "terms": graded[1]}
        print(json.dumps(doc, indent=2))
    else:
        print(result.render())
        if graded is not None:
            print(f"strength {graded[0]:.3f}: " + "; ".join(graded[1]))
    return 0


def _list(args: argparse.Namespace) -> int:
    if args.predicates:
        for name, spec in PREDICATES.items():
            first = spec.doc.splitlines()[0] if spec.doc else ""
            print(f"{name:<28} {spec.category:<9} {first}")
            print(f"{'':<28} e.g. {json.dumps(spec.example)}")
        return 0
    try:
        registry = RuleRegistry.load(_paths(args))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        print(
            "astro-rules list: fix the problems above (astro-rules validate)",
            file=sys.stderr,
        )
        return 1
    rules = registry.filter(args.domain, args.tier, args.status)
    for rule in rules:
        print(
            f"{rule.id:<58} {rule.domain:<9} {rule.tier:<12} "
            f"{rule.status:<18} {rule.name}"
        )
    print(f"\n{len(rules)} of {len(registry)} rules")
    return 0


def _schema(args: argparse.Namespace) -> int:
    text = json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"
    if args.write:
        Path(args.write).write_text(text)
        print(f"wrote {args.write}")
    else:
        print(text, end="")
    return 0


def _load_rule(args: argparse.Namespace):
    registry = RuleRegistry.load(_paths(args))
    rule = registry.get(args.rule_id)
    return rule, registry.path_of(args.rule_id)


def _fail(command: str, exc: BaseException) -> int:
    message = exc.args[0] if isinstance(exc, KeyError) and exc.args else exc
    print(f"astro-rules {command}: {message}", file=sys.stderr)
    return 2


def _fmt(value, digits: int = 3) -> str:
    if value is None:
        return "-"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if value != value:
        return "-"
    return f"{value:.{digits}g}"


def _fit(args: argparse.Namespace) -> int:
    from .studyadapter import StudyAdapter
    from .workbench import WorkbenchError, fit, stamped
    from .yamlio import edit_rule_file, flow, plain

    try:
        rule, path = _load_rule(args)
        if stamped(rule) and not args.new_version:
            raise WorkbenchError(
                f"{rule.id} v{rule.version} already has a confirm stamp "
                f"({rule.validation.status}); tuning it again needs a new "
                "version: rerun with --new-version"
            )
        bump = stamped(rule) and args.new_version
        if bump:
            rule = rule.model_copy(update={"version": rule.version + 1})
        adapter = StudyAdapter(args.study)
        print(
            f"fit {rule.id} v{rule.version} on {adapter.study}: EXPLORE "
            f"{' to '.join(adapter.explore_period().label())} only"
        )
        result = fit(rule, adapter, args.by, n_draws=args.draws)
    except (KeyError, ValueError, MissingInputError, RuleNotEvaluable) as exc:
        return _fail("fit", exc)
    print(
        f"events: {result.n_events} {adapter.event_label}; grid steps: "
        f"{result.n_steps}; cells: {len(result.cells)}; alternative: "
        f"{result.alternative}; null: circular shift, min shift "
        f"{adapter.min_shift} steps, {args.draws} draws"
    )
    print("\ntop 5 cells (p from the circular-shift null; q = BH within the grid)")
    print(f"  {'cell':<36} {'RR':>7} {'95% CI':>17} {'p':>8} {'q':>8} {'on':>6}")
    for _, row in result.top(5).iterrows():
        ci = f"[{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}]"
        print(
            f"  {row['cell']:<36} {_fmt(row['rate_ratio']):>7} {ci:>17} "
            f"{_fmt(row['p']):>8} {_fmt(row['q_within_grid']):>8} "
            f"{row['time_fraction']:>6.1%}"
        )
    for note in result.notes:
        print(f"note: {note}")
    if result.curve is not None:
        print(f"\n{result.entry['note']}")
    print(f"specification curve: {result.entry['spec_curve_artifact']}")
    chosen = ", ".join(f"{k} = {v:g}" for k, v in result.chosen.items())
    print(f"chosen: {chosen or '(no params to tune)'}")
    if args.dry_run:
        print("--dry-run: the rule file is unchanged")
        return 0

    def mutate(data):
        if bump:
            history = data.get("validation_history") or []
            history.append(data["validation"])
            data["validation_history"] = history
            data["version"] = rule.version
            data["validation"] = {"status": "unvalidated"}
        for name, value in result.chosen.items():
            data["params"][name]["value"] = plain(value)
        entry = plain(result.entry)
        for key in ("grid",):
            entry[key] = {k: flow(v) for k, v in entry[key].items()}
        entry["chosen"] = flow(entry["chosen"])
        entry["explore"]["ci"] = flow(entry["explore"]["ci"])
        entry["explore"]["period"] = flow(entry["explore"]["period"])
        log = data.get("tuning_log")
        if log is None:
            from .yamlio import insert_key

            insert_key(data, "tuning_log", [entry], before=("validation", "notes"))
        else:
            log.append(entry)

    edit_rule_file(path, mutate)
    what = "params updated, " if result.chosen else ""
    print(f"wrote {path}: {what}tuning_log entry appended")
    return 0


def _confirm(args: argparse.Namespace) -> int:
    from .studyadapter import StudyAdapter
    from .workbench import confirm, stamped
    from .yamlio import edit_rule_file, flow, insert_key, plain

    try:
        rule, path = _load_rule(args)
        if stamped(rule):
            confirm(rule, None)  # raises the refusal with its explanation
        adapter = StudyAdapter(args.study)
        print(
            f"confirm {rule.id} v{rule.version} on {adapter.study}: one frozen run "
            f"on CONFIRM {' to '.join(adapter.confirm_period().label())}"
        )
        stamp = confirm(rule, adapter)
    except (KeyError, ValueError, MissingInputError, RuleNotEvaluable) as exc:
        return _fail("confirm", exc)
    res = stamp["confirm"]
    print(
        f"events: {res['n_events']}; RR {_fmt(res.get('rate_ratio'))} "
        f"[{_fmt((res.get('ci') or [None])[0])}, "
        f"{_fmt((res.get('ci') or [None, None])[1])}]; p {_fmt(res.get('p'))}; "
        f"q {_fmt(res.get('q_family'))} in {res.get('family')}"
    )
    print(f"validation.status: {stamp['status']}")

    def mutate(data):
        old = data.get("validation")
        if old and old.get("status", "unvalidated") != "unvalidated":
            history = data.get("validation_history") or []
            history.append(old)
            insert_key(data, "validation_history", history, before=("notes",))
        new = plain(stamp)
        new["confirm"]["ci"] = flow(new["confirm"]["ci"])
        new["confirm"]["period"] = flow(new["confirm"]["period"])
        insert_key(data, "validation", new, before=("notes",))

    edit_rule_file(path, mutate)
    print(f"wrote {path}: validation stamped for v{rule.version}")
    return 0


def _dose(args: argparse.Namespace) -> int:
    from .studyadapter import StudyAdapter
    from .workbench import dose

    try:
        rule, _path = _load_rule(args)
        adapter = StudyAdapter(args.study)
        print(
            f"dose {rule.id} v{rule.version} on {adapter.study}: EXPLORE "
            f"{' to '.join(adapter.explore_period().label())} only"
        )
        rep = dose(rule, adapter, n_perm=args.draws)
    except (KeyError, ValueError, MissingInputError, RuleNotEvaluable) as exc:
        return _fail("dose", exc)
    base = rep.baseline
    print(
        f"silent steps: {int(base['steps'])}, events {base['events']}, "
        f"rate {base['rate_per_1000']:.2f} per 1000 steps"
    )
    print(
        f"  {'quintile':>8} {'strength':>11} {'steps':>6} {'events':>6} "
        f"{'per 1000':>9} {'RR vs silent':>13} {'95% CI':>16}"
    )
    for _, row in rep.table.iterrows():
        ci = f"[{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}]"
        print(
            f"  {row['quintile']:>8} {row['strength']:>11} {row['steps']:>6} "
            f"{row['events']:>6} {row['rate_per_1000']:>9.2f} "
            f"{_fmt(row['rr_vs_silent']):>13} {ci:>16}"
        )
    print(
        f"trend: {rep.method} z {_fmt(rep.statistic)}, p {_fmt(rep.p_value)} "
        f"(independent days); Kendall tau-b {_fmt(rep.kendall_tau)}, scipy p "
        f"{_fmt(rep.kendall_p)}; circular-shift p {_fmt(rep.shift_p)} "
        f"({rep.n_perm} shifts, one-sided: rate rises with strength)"
    )
    return 0


def _review(args: argparse.Namespace) -> int:
    from .workbench import review_entry
    from .yamlio import edit_rule_file, insert_key, plain

    try:
        rule, path = _load_rule(args)
        entry = plain(review_entry(rule, args.by, args.verdict, args.note))
    except (KeyError, ValueError) as exc:
        return _fail("review", exc)

    def mutate(data):
        reviews = data.get("review")
        if reviews is None:
            insert_key(data, "review", [entry], before=("notes",))
        else:
            reviews.append(entry)

    edit_rule_file(path, mutate)
    print(f"{rule.id} v{rule.version}: review by {args.by} ({args.verdict}) appended")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser (exposed for documentation tools)."""
    parser = argparse.ArgumentParser(
        prog="astro-rules",
        description="Validate, test, explain and list astrological rules.",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    p = sub.add_parser("validate", help="check schema, ids, predicates and names")
    p.add_argument(
        "paths", nargs="*", help="rule files or directories (default rules/)"
    )
    p.set_defaults(func=_validate)

    p = sub.add_parser("test", help="run every reference case through the engine")
    p.add_argument(
        "paths", nargs="*", help="rule files or directories (default rules/)"
    )
    p.set_defaults(func=_test)

    p = sub.add_parser("explain", help="explain one rule at one moment")
    p.add_argument("rule_id")
    p.add_argument("moment", help="ISO-8601, e.g. 2024-05-03T06:00:00+05:45")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float, help="east positive")
    p.add_argument("--tz", help="IANA time zone, e.g. Asia/Kathmandu")
    p.add_argument("--natal-moment", help="natal (birth or founding) moment")
    p.add_argument("--natal-lat", type=float)
    p.add_argument("--natal-lon", type=float)
    p.add_argument("--natal-tz")
    p.add_argument("--rules-dir", help="where the rules live (default rules/)")
    p.add_argument("--json", action="store_true", help="print the tree as JSON")
    p.add_argument(
        "--strength", action="store_true", help="also print the graded strength"
    )
    p.set_defaults(func=_explain)

    p = sub.add_parser("list", help="list rules or the predicate vocabulary")
    p.add_argument("--domain")
    p.add_argument("--tier", choices=["classical", "experimental"])
    p.add_argument(
        "--status", choices=["active", "needs_predicates", "needs_verification"]
    )
    p.add_argument("--predicates", action="store_true", help="list the predicates")
    p.add_argument("--rules-dir")
    p.set_defaults(func=_list)

    p = sub.add_parser("fit", help="tune a rule's params on a study's EXPLORE period")
    p.add_argument("rule_id")
    p.add_argument("--study", required=True, help="earthquake, gold or silver")
    p.add_argument("--by", required=True, help="your handle, e.g. @astrologer")
    p.add_argument("--draws", type=int, default=2000, help="null draws per cell")
    p.add_argument(
        "--new-version",
        action="store_true",
        help="start the next version when this one already has a confirm stamp",
    )
    p.add_argument("--dry-run", action="store_true", help="do not write the file")
    p.add_argument("--rules-dir")
    p.set_defaults(func=_fit)

    p = sub.add_parser(
        "confirm", help="one frozen run on the CONFIRM period; stamps validation"
    )
    p.add_argument("rule_id")
    p.add_argument("--study", required=True)
    p.add_argument("--rules-dir")
    p.set_defaults(func=_confirm)

    p = sub.add_parser("dose", help="event rate across strength quintiles (EXPLORE)")
    p.add_argument("rule_id")
    p.add_argument("--study", required=True)
    p.add_argument("--draws", type=int, default=999, help="circular shifts")
    p.add_argument("--rules-dir")
    p.set_defaults(func=_dose)

    p = sub.add_parser("review", help="sign off that the encoding is faithful")
    p.add_argument("rule_id")
    p.add_argument("--by", required=True)
    p.add_argument("--verdict", required=True, choices=["faithful", "not_faithful"])
    p.add_argument("--note", required=True)
    p.add_argument("--rules-dir")
    p.set_defaults(func=_review)

    p = sub.add_parser("schema", help="print the JSON Schema of a rule file")
    p.add_argument("--write", help="write it to this path (rules/schema.json)")
    p.set_defaults(func=_schema)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the command line; return the exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        raise SystemExit(2)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
