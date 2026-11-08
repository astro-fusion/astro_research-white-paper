"""``astro-rules``: validate, test, explain and list astrological rules.

Examples::

    astro-rules validate                    # every rules/**/*.yaml
    astro-rules test rules/general          # run the reference cases
    astro-rules explain general.gaja_kesari.moon_kendra 2024-05-03T06:00:00Z
    astro-rules explain mundane.ch7.oath_aquarius_baseline_penalty
        2024-06-09T19:15:00 --lat 28.61 --lon 77.21 --tz Asia/Kolkata
    astro-rules list --domain seismic --tier experimental
    astro-rules list --predicates

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
    if args.json:
        print(
            json.dumps(
                {"rule": rule.id, "fired": result.fired, "tree": result.tree.to_dict()},
                indent=2,
            )
        )
    else:
        print(result.render())
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
