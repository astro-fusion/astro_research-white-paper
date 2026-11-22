"""Validate, relocate and promote files from the quarantine folder research/incoming/.

Machine checks only. A person still opens each source; the validator records that
person's verdicts in VERIFICATION.json and promotes only rows with
verdict "accepted" and a ``checked_by`` name.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from tools.ingest.contracts import (
    NOT_FOUND, PROMOTED_COLUMNS, Contract, contract_for, suggest_mapping,
)
from tools.ingest.urlcheck import archive_lookup, check_url, default_opener

REPO_ROOT = Path(__file__).resolve().parents[2]
VERDICTS = ("accepted", "rejected", "unverified")
TOPIC_HINTS = (("flood", "flood"), ("rain", "flood"), ("monsoon", "flood"), ("gold", "gold"),
               ("quake", "earthquake"), ("earthquake", "earthquake"), ("seismic", "earthquake"))
VALUE_COLUMNS = {"open", "high", "low", "close", "adj_close", "volume", "price", "rainfall",
                 "precip", "precipitation", "mag", "magnitude", "latitude", "longitude", "depth"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URL_RE = re.compile(r"https?://[^\s,;<>)\"']+")
_REF_RE = re.compile(
    r"https?://|\b10\.\d{4,9}/|\b(?:chapter|ch\.|adhyaya|verse)\s*\d", re.IGNORECASE)
FORECAST_FILES = ("exante", "claims")

RulesRunner = Callable[[str], Tuple[int, str]]


# ---------------------------------------------------------------- helpers

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_date(text: str) -> Optional[date]:
    text = (text or "").strip()
    if not _DATE_RE.match(text):
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _is_gap(text: str) -> bool:
    return (text or "").strip().upper() == NOT_FOUND


def has_reference(text: str) -> bool:
    text = (text or "").strip()
    return bool(text) and not _is_gap(text) and bool(_REF_RE.search(text))


def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = [{k: (v or "") for k, v in r.items() if k is not None} for r in reader]
    return header, rows


def _numeric_share(rows: Sequence[Dict[str, str]]) -> float:
    cells = [v.strip() for r in rows for k, v in r.items() if v.strip()
             and not _DATE_RE.match(v.strip())]
    if not cells:
        return 0.0

    def num(s: str) -> bool:
        try:
            float(s)
            return True
        except ValueError:
            return False
    return sum(num(c) for c in cells) / len(cells)


def looks_like_value_dump(header: Sequence[str], rows: Sequence[Dict[str, str]],
                          has_contract: bool) -> Optional[str]:
    """Return a reason when the file looks like price, catalogue or rainfall values."""
    names = {h.strip().lower() for h in header}
    share = _numeric_share(rows)
    if has_contract:
        if len(rows) >= 200 and share > 0.8:
            return f"{len(rows)} rows, {share:.0%} numeric cells"
        return None
    if len(rows) >= 50 and (len(names & VALUE_COLUMNS) >= 2 or share > 0.7):
        return f"{len(rows)} rows, value columns {sorted(names & VALUE_COLUMNS)}, {share:.0%} numeric"
    return None


def row_urls(contract: Contract, row: Dict[str, str]) -> List[str]:
    urls: List[str] = []
    for col in contract.reference:
        urls.extend(_URL_RE.findall(row.get(col, "")))
    return list(dict.fromkeys(urls))


def _ex_ante_start(contract: Contract, row: Dict[str, str]) -> Optional[date]:
    if contract.name == "monsoon_forecasts_exante":
        try:
            return date(int(row.get("year", "").strip()), 6, 1)
        except ValueError:
            return None
    if contract.ex_ante:
        return parse_date(row.get(contract.ex_ante[1], ""))
    return None


# ------------------------------------------------------------ row checks

def check_rows(contract: Contract, rows: List[Dict[str, str]], *, check_urls: bool,
               opener: Any = None) -> List[Dict[str, Any]]:
    """Apply the machine rejection rules of section 4.4 to each row."""
    out: List[Dict[str, Any]] = []
    seen_ids: Dict[str, int] = {}
    seen_rows: Dict[Tuple[str, ...], int] = {}
    cache: Dict[str, Dict[str, Optional[str]]] = {}
    for n, row in enumerate(rows, start=1):
        reasons: List[str] = []
        warnings: List[str] = []
        # reference
        if contract.reference and not any(has_reference(row.get(c, "")) for c in contract.reference):
            if not (contract.name == "literature" and has_reference(row.get("citation", ""))):
                reasons.append("no URL, DOI or book-chapter-verse reference")
        # dates
        parsed: Dict[str, Optional[date]] = {}
        for col in contract.dates:
            val = row.get(col, "")
            parsed[col] = parse_date(val)
            if parsed[col] is None and not _is_gap(val):
                reasons.append(f"unparsable date in {col}: {val!r}")
        for start, end in contract.ranges:
            if parsed.get(start) and parsed.get(end) and parsed[end] < parsed[start]:
                reasons.append(f"{end} is before {start}")
        # duplicates
        if contract.id_column:
            key = row.get(contract.id_column, "").strip()
            if not key:
                reasons.append(f"empty {contract.id_column}")
            elif key in seen_ids:
                reasons.append(f"duplicate {contract.id_column} (first at row {seen_ids[key]})")
            else:
                seen_ids[key] = n
        full = tuple(row.get(k, "") for k in sorted(row))
        if full in seen_rows:
            reasons.append(f"duplicate of row {seen_rows[full]}")
        else:
            seen_rows[full] = n
        # url check
        url_status: Optional[str] = None
        archive_url: Optional[str] = None
        if check_urls:
            statuses = []
            for url in row_urls(contract, row):
                if url not in cache:
                    cache[url] = check_url(url, opener)
                statuses.append(cache[url])
            bad = [s for s in statuses if s["url_status"] != "ok"]
            url_status = "ok" if statuses and not bad else (
                bad[0]["url_status"] if bad else None)
            archive_url = next((s["archive_url"] for s in bad if s["archive_url"]), None)
            if bad and not archive_url:
                reasons.append(f"dead link ({bad[0]['url_status']}) with no archive copy")
        # ex-ante
        is_ex_ante = contract.all_ex_ante or (
            contract.ex_ante_flag is not None
            and row.get(contract.ex_ante_flag, "").strip().lower() in ("yes", "true", "1", "y"))
        if is_ex_ante:
            pub = parse_date(row.get("published_date", ""))
            start = _ex_ante_start(contract, row)
            if pub is None:
                reasons.append("ex-ante row without a parsable publication date")
            elif start is not None and not pub < start:
                reasons.append("marked ex-ante but published on or after the target window starts")
            elif start is None and contract.ex_ante_flag is None:
                reasons.append("ex-ante row without a parsable target start")
            proof = row.get("archive_url", "").strip()
            proof = "" if _is_gap(proof) else proof
            if not proof and not archive_url and check_urls:
                for url in row_urls(contract, row):
                    archive_url = archive_lookup(url, opener or default_opener)
                    if archive_url:
                        break
            if not (proof or archive_url):
                msg = "ex-ante without an archive capture proving the date"
                (reasons if check_urls else warnings).append(msg)
        out.append({"row_id": f"{{stem}}-{n:04d}", "reasons": reasons, "warnings": warnings,
                    "url_status": url_status, "archive_url": archive_url or None})
    return out


# ---------------------------------------------------------- rule YAML

def default_rules_runner(path: str) -> Tuple[int, str]:
    code = ("import sys; from vedic_astrology_core.rules.cli import main; "
            "sys.exit(main(['validate', sys.argv[1]]))")
    proc = subprocess.run([sys.executable, "-c", code, path], capture_output=True, text=True,
                          timeout=120)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def repo_rule_ids(repo: Path = REPO_ROOT) -> set:
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return set()
    ids = set()
    for p in (repo / "rules").rglob("*.y*ml"):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("id"):
            ids.add(data["id"])
    return ids


def check_rule_file(path: Path, runner: RulesRunner = default_rules_runner,
                    known_ids: Optional[set] = None) -> Dict[str, Any]:
    import yaml
    issues: List[Dict[str, Any]] = []

    def add(msg: str, fixable: bool) -> None:
        issues.append({"message": msg, "fixable": fixable})

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "fail", "issues": [{"message": f"unparsable YAML: {exc}", "fixable": False}]}
    if not isinstance(data, dict):
        return {"status": "fail", "issues": [{"message": "not a YAML mapping", "fixable": False}]}
    marked = data.get("status") == "needs_predicates"
    code, output = runner(str(path))
    if code != 0:
        if marked:
            add("fails astro-rules validate; allowed because status is needs_predicates", True)
        else:
            add("fails astro-rules validate: " + output[-400:], False)
    if data.get("tier") not in (None, "classical", "experimental"):
        add(f"tier {data.get('tier')!r} is not allowed; practitioner rules use tier experimental "
            "and live in a practitioner/ folder", True)
    if "ex_ante" in data:
        add("ex_ante belongs under notes", True)
    if isinstance(data.get("conditions"), str):
        add("conditions is prose; file with status: needs_predicates", True)
    src = data.get("source")
    if not isinstance(src, dict) or not all(src.get(k) for k in ("text", "edition", "chapter", "verse")):
        add("source is not complete to L1 (text, edition, chapter, verse)", False)
    params = data.get("params") or {}
    for name, spec in (params.items() if isinstance(params, dict) else []):
        if not isinstance(spec, dict) or not all(k in spec for k in ("value", "min", "max", "step", "unit")):
            add(f"param {name} lacks value, min, max, step, unit", False)
    effect = data.get("expected_effect")
    if not isinstance(effect, dict) or not effect.get("direction"):
        add("expected_effect.direction missing", False)
    cases = data.get("reference_cases") or []
    expects = {c.get("expect") for c in cases if isinstance(c, dict)}
    if not {"fires", "silent"} <= expects:
        add("needs at least one fires and one silent reference case", False)
    if known_ids and data.get("id") in known_ids:
        add(f"id {data.get('id')} already exists in rules/", False)
    fatal = [i for i in issues if not i["fixable"]]
    return {"id": data.get("id"), "status": "fail" if fatal else ("fixable" if issues else "ok"),
            "issues": issues}


# ------------------------------------------------------ directory pass

def _spot_required(name: str, n: int) -> int:
    if any(t in name for t in FORECAST_FILES):
        return n
    return min(n, max(10, math.ceil(0.2 * n)))


def validate_dir(topic_dir: Path, *, check_urls: bool = True, opener: Any = None,
                 rules_runner: RulesRunner = default_rules_runner,
                 known_ids: Optional[set] = None, today: Optional[date] = None,
                 write_report: bool = True) -> Dict[str, Any]:
    topic_dir = Path(topic_dir)
    report_path = topic_dir / "VERIFICATION.json"
    previous: Dict[str, Any] = {}
    if report_path.exists():
        try:
            previous = json.loads(report_path.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
    prev_rows = {r["row_id"]: r for f in previous.get("files", {}).values() for r in f.get("rows", [])}
    known_ids = repo_rule_ids() if known_ids is None else known_ids
    files: Dict[str, Any] = {}
    rules: Dict[str, Any] = {}
    for path in sorted(p for p in topic_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(topic_dir).as_posix()
        if path.name == "VERIFICATION.json":
            continue
        if path.suffix in (".yaml", ".yml"):
            rules[rel] = check_rule_file(path, rules_runner, known_ids)
            continue
        if path.suffix not in (".csv", ".md"):
            continue
        contract = contract_for(path.name)
        entry: Dict[str, Any] = {"contract": contract.name if contract else None,
                                 "sha256": _sha256(path), "issues": [], "status": "ok", "rows": []}
        files[rel] = entry
        if path.suffix == ".md":
            if contract is None:
                entry["issues"].append({"code": "no_contract", "message": "no contract for this file"})
                entry["status"] = "unknown"
            else:
                has_ref = bool(re.search(r"https?://|\b10\.\d{4,9}/", path.read_text(encoding="utf-8")))
                if not has_ref:
                    entry["issues"].append({"code": "no_reference",
                                            "message": "free text with no URL or DOI"})
                    entry["status"] = "rejected"
            continue
        header, rows = read_csv(path)
        entry["row_count"] = len(rows)
        dump = looks_like_value_dump(header, rows, contract is not None)
        if dump:
            entry["issues"].append({"code": "value_dump", "message":
                                    f"looks like a file of price, catalogue or rainfall values ({dump}); "
                                    "not used and not committed"})
            entry["status"] = "rejected"
            continue
        if contract is None:
            entry["issues"].append({"code": "no_contract", "message": "no contract for this file"})
            entry["status"] = "unknown"
            continue
        missing = [c for c in contract.columns if c not in header]
        if missing:
            entry["issues"].append({
                "code": "columns_mismatch", "message": f"missing columns: {missing}",
                "suggested_mapping": suggest_mapping(header, contract.columns),
                "note": "suggestion only; columns are never renamed automatically"})
            entry["status"] = "needs_mapping"
            continue
        checked = check_rows(contract, rows, check_urls=check_urls, opener=opener)
        for item in checked:
            item["row_id"] = item["row_id"].format(stem=path.stem)
            old = prev_rows.get(item["row_id"], {})
            verdict = old.get("verdict", "unverified")
            item["verdict"] = verdict if verdict in VERDICTS else "unverified"
            item["checked_by"] = old.get("checked_by", "")
            item["checked_on"] = old.get("checked_on", "")
            item["reject_reason"] = old.get("reject_reason", "") or "; ".join(item["reasons"])
        entry["rows"] = checked
        entry["rows_machine_rejected"] = sum(1 for i in checked if i["reasons"])
        entry["spot_checks_required"] = _spot_required(path.name, len(rows))
        entry["spot_checks_done"] = sum(1 for i in checked if i["checked_by"])
        entry["full_manual_check"] = any("fabricat" in (i["reject_reason"] or "").lower()
                                         and i["verdict"] == "rejected" for i in checked)
        if entry["rows_machine_rejected"]:
            entry["status"] = "has_rejections"
    report = {"topic": topic_dir.name, "generated_on": (today or date.today()).isoformat(),
              "files": files, "rules": rules}
    if write_report:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


# -------------------------------------------------------------- promote

def promote(topic_dir: Path, repo: Path = REPO_ROOT) -> Dict[str, Any]:
    """Copy rows with verdict accepted and a checked_by name into data/registry/<topic>/."""
    topic_dir = Path(topic_dir)
    report = json.loads((topic_dir / "VERIFICATION.json").read_text(encoding="utf-8"))
    dest_dir = Path(repo) / "data" / "registry" / topic_dir.name
    summary: Dict[str, Any] = {"promoted": {}, "skipped_files": {}}
    for rel, entry in report["files"].items():
        src = topic_dir / rel
        if not rel.endswith(".csv") or not entry.get("rows"):
            continue
        if not src.exists() or _sha256(src) != entry["sha256"]:
            summary["skipped_files"][rel] = "file changed since validation; run validate again"
            continue
        ok_rows = [r for r in entry["rows"] if r["verdict"] == "accepted"
                   and r["checked_by"].strip() and not r["reasons"]]
        if entry.get("full_manual_check") and len(ok_rows) != len(entry["rows"]):
            summary["skipped_files"][rel] = "fabrication found: every row needs a manual check"
            continue
        if not ok_rows:
            continue
        header, data = read_csv(src)
        by_id = {f"{src.stem}-{i:04d}": d for i, d in enumerate(data, start=1)}
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = dest_dir / (Path(rel).as_posix().replace("/", "__"))
        extra = [c for c in PROMOTED_COLUMNS if c not in header]
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=header + extra)
            w.writeheader()
            for r in ok_rows:
                row = dict(by_id[r["row_id"]])
                row.update(row_id=r["row_id"], url_status=r.get("url_status") or "",
                           archive_url=r.get("archive_url") or row.get("archive_url", ""),
                           checked_by=r["checked_by"], checked_on=r["checked_on"],
                           verdict="accepted", reject_reason="")
                w.writerow(row)
        summary["promoted"][rel] = len(ok_rows)
    return summary


# ------------------------------------------------- misplaced and relocate

def _tracked(repo: Path, rel: str) -> bool:
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=repo,
                           capture_output=True, text=True)
        return r.returncode == 0
    except OSError:
        return False


def suggest_topic(name: str) -> Optional[str]:
    low = name.lower()
    topics = {t for key, t in TOPIC_HINTS if key in low}
    return topics.pop() if len(topics) == 1 else None


def find_misplaced(repo: Path = REPO_ROOT, tracked: Callable[[Path, str], bool] = _tracked
                   ) -> List[Dict[str, Any]]:
    """Files an outside agent left at the repo root or in studies/*/rules/ (untracked only)."""
    repo = Path(repo)
    found = [p for p in repo.glob("*.csv")]
    found += [p for ext in ("yaml", "yml") for p in repo.glob(f"studies/*/rules/*.{ext}")]
    out = []
    for p in sorted(found):
        rel = p.relative_to(repo).as_posix()
        if tracked(repo, rel):
            continue
        out.append({"path": rel, "suggested_topic": suggest_topic(p.name),
                    "action": "python -m tools.ingest relocate " + rel + " --topic <topic>"})
    return out


def relocate(path: Path, topic: str, repo: Path = REPO_ROOT) -> Path:
    src = Path(path)
    dest_dir = Path(repo) / "research" / "incoming" / topic
    if src.suffix in (".yaml", ".yml"):
        dest_dir = dest_dir / "rules"
    dest = dest_dir / src.name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; not overwriting")
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    return dest


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m tools.ingest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check a quarantine folder, write VERIFICATION.json")
    v.add_argument("topic_dir")
    v.add_argument("--no-urls", action="store_true", help="skip network URL checks")
    v.add_argument("--promote", action="store_true",
                   help="copy accepted, person-checked rows into data/registry/<topic>/")
    sub.add_parser("misplaced", help="report files outside research/incoming/")
    r = sub.add_parser("relocate", help="move a misplaced file into quarantine")
    r.add_argument("path")
    r.add_argument("--topic")
    args = ap.parse_args(argv)
    if args.cmd == "validate":
        topic_dir = Path(args.topic_dir)
        rep = validate_dir(topic_dir, check_urls=not args.no_urls)
        n_rej = sum(f.get("rows_machine_rejected", 0) for f in rep["files"].values())
        print(f"{len(rep['files'])} files, {len(rep['rules'])} rule files, "
              f"{n_rej} rows machine-rejected; wrote {topic_dir / 'VERIFICATION.json'}")
        for rel, f in rep["files"].items():
            for issue in f["issues"]:
                print(f"  {rel}: {issue['message']}")
        if args.promote:
            print(json.dumps(promote(topic_dir), indent=2))
        return 1 if n_rej or any(f["status"] in ("rejected", "needs_mapping") for f in rep["files"].values()) else 0
    if args.cmd == "misplaced":
        items = find_misplaced()
        for i in items:
            print(f"{i['path']}  (topic: {i['suggested_topic'] or '?'})  -> {i['action']}")
        print(f"{len(items)} misplaced files")
        return 1 if items else 0
    topic = args.topic or suggest_topic(Path(args.path).name)
    if not topic:
        print("cannot infer the topic; pass --topic")
        return 2
    print(relocate(Path(args.path), topic))
    return 0
