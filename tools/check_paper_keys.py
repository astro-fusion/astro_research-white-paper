#!/usr/bin/env python3
"""The results-key gate (ADR-004 D-7, PAPER_ROADMAP section 6).

Fails (exit 1) when, for a paper in Quarto Markdown:

1. KEY      the paper asks for a results key that does not exist (or is null);
2. NUMBER   its prose contains a bare number that is not on the allow-list;
3. DIRTY    a results.json is provisional or was written from a dirty tree
            (or from outside git);
4. STALE    a results.json disagrees with the current plan hash or with the
            snapshot index (or carries no hash to compare).

Keys are requested through the paper kit, for example
R.get("headline.n_significant_explore") or R.num("spa.p", 3). With more than
one results file, give each a label (--results gold=a.json --results
silver=b.json) and write the key as "gold:headline.verdict".

Provenance follows the one contract in core/paperkit/results.py
(PROVENANCE_KEYS): top-level provisional and git {commit, dirty}; plan hash
(sha256 of the bytes of hypothesis.yaml) as plan.sha256 or plan_sha256; data
hash as data.sha256 or dataset.sha256 (the ADR-007 domain record), which must
appear as a "sha256" value in data/snapshot_index.json.

Numbers: a negative sign, a leading-dot decimal and a currency sign are part
of the number ("-0.42", ".03", "$1,850" are bare numbers). A hyphen or dot
glued to a word ("ADR-004", "v1.2") is not a sign.

Allow-list: one token per line (a year, a section number), "#" starts a
comment. Default <paper dir>/numbers_allowlist.txt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "libs"))

from vedic_astrology_core.paperkit import Results, provenance  # noqa: E402

KEY_CALL = re.compile(
    r"""\b[A-Za-z_]\w*\.(?:get|num|count|pct|p|text)\(\s*(["'])([^"']+)\1"""
)
_DIGITS = r"(?:\d+(?:[.,]\d+)*|\.\d+)"
NUMBER = re.compile(
    r"(?:(?<![\w/@#.])(?:[-−+]\$?|\$[-−]?)" + _DIGITS  # -0.42, +3, $5, -$5
    + r"|(?<![\w/@#.\-−$])" + _DIGITS + r")"  # 12.5, .03 (not ADR-004, v1.2)
    + r"(?![\w])"
)


def _blank(match: "re.Match[str]") -> str:
    """Replace matched text by spaces, keeping newlines (line numbers survive)."""
    return re.sub(r"[^\n]", " ", match.group(0))


def prose_of(text: str) -> str:
    """The paper's prose: no front matter, code, comments, links, citations."""
    out = text
    if out.startswith("---"):
        out = re.sub(r"\A---\n.*?\n---[ \t]*(?:\n|\Z)", _blank, out, count=1, flags=re.S)
    for pattern in (
        r"^(?P<f>\x60{3,}|~{3,}).*?^(?P=f)[ \t]*$",  # fenced blocks
        r"<!--.*?-->",
        r"\x60[^\x60\n]*\x60(?:\{[^}\n]*\})?",  # inline code, incl. {python}
        r"!?\[[^\]\n]*\]\([^)\n]*\)",  # links and images (text and URL)
        r"<https?://[^>\s]+>|https?://\S+",
        r"\[[^\]\n]*@[^\]\n]*\]",  # [@cite]
        r"@[\w:.\-]+",  # @fig-1, @smith2020
        r"\{#[^}\n]*\}|\{\{<[^}\n]*>\}\}",  # {#label}, shortcodes
        r"^[ \t]*(?:[|:\- ]+\|[|:\- ]*)$",  # table rules
    ):
        out = re.sub(pattern, _blank, out, flags=re.S | re.M)
    return out


def load_allowlist(path: Optional[Path]) -> set:
    if path is None or not path.exists():
        return set()
    tokens = set()
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            tokens.add(line)
    return tokens


def check_keys(text: str, results: Dict[str, Results], default: Optional[str]) -> List[str]:
    failures = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in KEY_CALL.finditer(line):
            key = m.group(2)
            label = default
            if ":" in key:
                label, key = key.split(":", 1)
            if label is None:
                failures.append(
                    f"KEY line {lineno}: {m.group(2)!r} needs a label:key prefix "
                    "(several results files given)"
                )
                continue
            if label not in results:
                failures.append(f"KEY line {lineno}: unknown results label {label!r}")
                continue
            try:
                results[label].get(key)
            except (KeyError, ValueError) as exc:
                failures.append(f"KEY line {lineno}: {exc}")
    return failures


def check_numbers(text: str, allow: set) -> List[str]:
    failures = []
    for lineno, line in enumerate(prose_of(text).splitlines(), 1):
        for m in NUMBER.finditer(line):
            token = m.group(0).rstrip(".,")
            if token not in allow:
                failures.append(f"NUMBER line {lineno}: bare number {token!r} not on allow-list")
    return failures


def check_dirty(label: str, res: Results) -> List[str]:
    failures = []
    prov = provenance(res.data)
    if prov["provisional"] is not False:
        failures.append(f"DIRTY {label}: results are provisional or lack provisional=false")
    if prov["dirty"] is not False or not prov["commit"]:
        failures.append(
            f"DIRTY {label}: not written from a clean git tree (git={res.data.get('git')!r})"
        )
    return failures


def _sha256_values(node) -> Iterable[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "sha256" and isinstance(v, str):
                yield v
            else:
                yield from _sha256_values(v)
    elif isinstance(node, list):
        for v in node:
            yield from _sha256_values(v)


def pinned_hashes(plan: Path) -> set:
    """SHA-256 values the plan pins: its `snapshots` list, else any `sha256` key."""
    import yaml

    doc = yaml.safe_load(plan.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("plan is not a mapping")
    node = doc.get("snapshots") if doc.get("snapshots") else doc
    return set(_sha256_values(node))


def _check_pinned(label: str, data_sha: Optional[str], plan: Path) -> List[str]:
    """D-08: the results' data hash must be one the plan pins, not just any indexed hash."""
    try:
        pins = pinned_hashes(plan)
    except Exception as exc:  # unreadable or not YAML
        return [f"STALE {label}: cannot read the data hashes {plan.name} pins: {exc}"]
    if not pins:
        return [f"STALE {label}: {plan.name} pins no snapshot hash"]
    if data_sha is not None and data_sha not in pins:
        return [f"STALE {label}: data hash is not one {plan.name} pins"]
    return []


def check_stale(
    label: str, res: Results, plan: Optional[Path], index: Optional[Path]
) -> List[str]:
    failures = []
    prov = provenance(res.data)
    failures += [f"STALE {label}: {p}" for p in prov["problems"]]
    if plan is not None:
        want = hashlib.sha256(plan.read_bytes()).hexdigest()
        have = prov["plan_sha256"]
        if have is None:
            failures.append(f"STALE {label}: no plan hash in results to compare with {plan.name}")
        elif have != want:
            failures.append(f"STALE {label}: plan hash differs from current {plan.name}")
        failures += _check_pinned(label, prov["data_sha256"], plan)
    if index is not None:
        if not index.exists():
            failures.append(f"STALE {label}: snapshot index {index} not found")
        else:
            try:
                known = set(_sha256_values(json.loads(index.read_text())))
            except json.JSONDecodeError as exc:
                return failures + [f"STALE {label}: snapshot index is not JSON: {exc}"]
            if prov["data_sha256"] is None:
                failures.append(f"STALE {label}: no data.sha256 (or dataset.sha256) in results")
            elif prov["data_sha256"] not in known:
                failures.append(f"STALE {label}: data hash not in {index.name}")
    return failures


def parse_results(specs: List[str], paper: Path) -> Tuple[Dict[str, Results], Optional[str]]:
    if not specs:
        specs = [str(paper.parent.parent / "artifacts" / "results.json")]
    out: Dict[str, Results] = {}
    for spec in specs:
        label, _, path = spec.partition("=") if "=" in spec else ("results", "", spec)
        out[label] = Results.load(path)
    default = next(iter(out)) if len(out) == 1 else None
    return out, default


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paper", type=Path)
    ap.add_argument("--results", action="append", default=[], metavar="[LABEL=]PATH")
    ap.add_argument("--allowlist", type=Path)
    ap.add_argument("--plan", type=Path, help="hypothesis.yaml (default: beside artifacts)")
    ap.add_argument("--snapshot-index", type=Path, default=REPO / "data" / "snapshot_index.json")
    ap.add_argument(
        "--no-provenance",
        action="store_true",
        help="skip checks 3 and 4 (key and number checks only; for fixtures)",
    )
    args = ap.parse_args(argv)

    text = args.paper.read_text()
    try:
        results, default = parse_results(args.results, args.paper)
    except (OSError, ValueError) as exc:
        print(f"ERROR cannot load results: {exc}", file=sys.stderr)
        return 1
    allow = load_allowlist(args.allowlist or args.paper.parent / "numbers_allowlist.txt")

    failures = check_keys(text, results, default)
    failures += check_numbers(text, allow)
    if not args.no_provenance:
        plan = args.plan
        if plan is None:
            cand = args.paper.parent.parent / "hypothesis.yaml"
            plan = cand if cand.exists() else None
        for label, res in results.items():
            failures += check_dirty(label, res)
            failures += check_stale(label, res, plan, args.snapshot_index)

    for f in failures:
        print(f, file=sys.stderr)
    if failures:
        print(f"FAIL: {len(failures)} problem(s) in {args.paper}", file=sys.stderr)
        return 1
    print(f"OK: {args.paper}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
