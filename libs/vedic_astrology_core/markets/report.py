"""Markdown text and tables for a market-study paper, built from results.json.

The manuscripts call these functions in their Results and Discussion cells,
so every number in the text is read from the artifact the pipeline wrote and
the wording follows the outcome (positive, null, mixed, not replicated).
"""

import json
from pathlib import Path
from typing import Dict, List

TARGET_NAMES = {
    "ret": "return",
    "absret": "absolute return",
    "extreme": "extreme-move rate",
}


def load(path) -> Dict:
    """Read a results.json file."""
    return json.loads(Path(path).read_text())


def _f(value, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _p(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}" if value >= 0.0001 else f"{value:.1e}"


def _table(header: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def provisional_banner(res: Dict) -> str:
    """Return a warning paragraph when the run used the offline fixture."""
    if not res["provisional"]:
        return ""
    return ("**PROVISIONAL.** The data sources were unreachable when this run "
            "was made, so it used the small offline fixture "
            f"({res['data']['date_min']} to {res['data']['date_max']}). "
            "No conclusion should be drawn from these numbers.\n")


def data_paragraph(res: Dict) -> str:
    """Describe the series actually used, with its hash."""
    d = res["data"]
    tried = [t for t in d.get("sources_tried", []) if t.get("series_id") != "*"]
    fallback = ""
    if tried:
        names = ", ".join(f"`{t['series_id']}`" for t in tried)
        error = tried[0]["error"].rsplit(": ", 1)[-1]
        fallback = (f" The pre-registered primary source ({names}) did not answer "
                    f"({error}), so the next source in the pre-registered order "
                    "was used.")
    futures = ""
    if d["is_futures"]:
        futures = (" This is a front-month continuous futures series, not a spot "
                   "price: roll days are not back-adjusted, and it is described "
                   "as futures throughout.")
    return (f"The series is **{d['label']}** (`{d['series_id']}`), "
            f"{d['rows']:,} trading days from {d['date_min']} to {d['date_max']}, "
            f"SHA-256 `{d['sha256'][:16]}...` (snapshot `{d['snapshot']}`). "
            f"Planetary state is sampled at {d['sample_time']} {d['tz']} on each "
            f"trading day.{futures}{fallback}")


def headline_table(res: Dict) -> str:
    """One-row-per-family summary of what was tested and what held."""
    h = res["headline"]
    fam = res["family"]
    rows = [
        ["Indicator tests, explore period", str(h["n_tests_explore"]),
         str(h["n_significant_explore"]), f"BY q < {fam['alpha']}"],
        ["Carried to confirm period", str(h["n_significant_explore"]),
         str(h["n_confirmed"]), "same sign and BY q < alpha"],
        ["Indicator tests, full sample (descriptive)", str(h["n_tests_explore"]),
         str(h["n_significant_full"]), "BY q < alpha"],
        ["SPA, best one-day rule vs flat (confirm)", str(res["spa"].get("n_rules")),
         "1" if (h["spa_p"] or 1) < fam["alpha"] else "0",
         f"p = {_p(h['spa_p'])}"],
        ["Event study, retrograde stations", str(h["n_event_tests"]),
         str(h["n_event_significant"]), "BY q < alpha"],
        ["Exogenous Granger (ADL + HAC)", str(len(res["granger"])),
         str(sum(bool(g.get("significant")) for g in res["granger"])),
         "BY q < alpha"],
    ]
    return _table(["Family", "Tests", "Significant", "Criterion"], rows)


def verdict_sentence(res: Dict) -> str:
    """One sentence stating the pre-registered outcome."""
    h = res["headline"]
    v = h["verdict"]
    n = h["n_tests_explore"]
    if v == "null":
        return (f"None of the {n} pre-registered indicator tests was significant "
                "in the explore period after Benjamini-Yekutieli correction, so "
                "nothing was carried forward: the result is **null**.")
    if v == "not_replicated":
        k = h["n_significant_explore"]
        return (f"{k} of {n} indicator tests {'was' if k == 1 else 'were'} "
                "significant in the explore period, and none held in the frozen "
                "confirm period: the result is **null (not replicated)**.")
    if v == "not_testable":
        return "The sample was too short to run the pre-registered tests."
    return (f"{h['n_confirmed']} of {h['n_significant_explore']} explore-period "
            f"findings held in the confirm period: the result is **{v}**.")


def tests_table(res: Dict, period: str = "explore", top: int = 10) -> str:
    """The ``top`` smallest p-values of a period, with effects and CIs."""
    rows = [t for t in res["tests"] if t["period"] == period and t["testable"]]
    rows.sort(key=lambda t: t["p_value"])
    out = []
    for t in rows[:top]:
        out.append([
            t["indicator"].replace("_", " "), TARGET_NAMES[t["target"]],
            f"{t['n_active']}/{t['n']}",
            f"{_f(t['effect'])} [{_f(t['ci_low'])}, {_f(t['ci_high'])}] {t['unit']}",
            _p(t["p_value"]), _p(t["q_value"]),
        ])
    return _table(["Indicator", "Outcome", "Active bars", "Effect [95% CI]", "p",
                   "q (BY)"], out)


def confirmation_table(res: Dict) -> str:
    """Explore-significant tests and how they fared in the confirm period."""
    if not res["confirmation"]:
        return "No explore-period test was significant, so none was carried forward."
    out = []
    for c in res["confirmation"]:
        out.append([
            c["indicator"].replace("_", " "), TARGET_NAMES[c["target"]],
            f"{_f(c['effect_explore'])} {c['unit']}",
            f"{_f(c['effect'])} [{_f(c['ci_low'])}, {_f(c['ci_high'])}] {c['unit']}",
            _p(c["p_value"]), _p(c["q_confirm"]), "yes" if c["confirmed"] else "no",
        ])
    return _table(["Indicator", "Outcome", "Explore effect", "Confirm effect [95% CI]",
                   "Confirm p", "Confirm q", "Confirmed"], out)


def spa_sentence(res: Dict) -> str:
    """Describe the SPA test of the best one-day indicator rule."""
    s = res["spa"]
    if s.get("p_consistent") is None:
        return f"The SPA test was not run ({s.get('skipped', 'no rules')})."
    claim = ("so a best-rule claim would be supported"
             if s["p_consistent"] < res["family"]["alpha"]
             else "so no indicator rule beats being flat once the search over "
                  f"{s['n_rules']} rules is accounted for")
    return (f"In the confirm period the best of {s['n_rules']} one-day long/short "
            f"indicator rules was `{s['best_rule']}`, with a mean daily return of "
            f"{_f(s['best_mean_return_bp'])} bp; Hansen's SPA consistent p = "
            f"{_p(s['p_consistent'])} ({s['n_boot']} bootstrap draws), {claim}.")


def event_table(res: Dict) -> str:
    """Mean forward return after stations against the bootstrap null band."""
    out = []
    for e in res["event_study"]:
        out.append([
            e["body"].title(), str(e["horizon"]), str(e["n_events"]),
            _f(e["mean"], 1), f"[{_f(e['null_lo'], 1)}, {_f(e['null_hi'], 1)}]",
            _f(e["unconditional"], 1), _p(e["p_value"]), _p(e["q_value"]),
        ])
    return _table(["Station retrograde", "h (bars)", "N", "Mean (bp)",
                   "95% null band (bp)", "All bars (bp)", "p", "q (BY)"], out)


def granger_table(res: Dict) -> str:
    """Exogenous ADL Wald tests."""
    out = []
    for g in res["granger"]:
        if g.get("p_value") is None:
            out.append([g["body"], g["target"], "n/a", "n/a", "n/a",
                        g.get("reason", "")])
            continue
        out.append([g["body"].title(), g["target"], _f(g["f_stat"]), _p(g["p_value"]),
                    _p(g["q_value"]), str(g["n"])])
    return _table(["Body (sin, cos of longitude)", "Outcome", "F", "p", "q (BY)", "n"],
                  out)


def stationarity_table(res: Dict) -> str:
    """ADF and KPSS on log price, returns and absolute returns."""
    out = []
    for s in res["stationarity"]:
        out.append([s["series"], _f(s["adf_stat"]), _p(s["adf_p"]),
                    _f(s["kpss_stat"]), _p(s["kpss_p"]),
                    "yes" if s["stationary"] else "no"])
    return _table(["Series", "ADF", "ADF p", "KPSS", "KPSS p", "Stationary"], out)


def discussion(res: Dict) -> str:
    """Discussion paragraphs that follow the outcome."""
    h = res["headline"]
    parts = [verdict_sentence(res)]
    if h["verdict"] in ("null", "not_replicated"):
        parts.append(
            "Within this design the data give no support to the idea that the "
            "pre-registered sidereal conditions shift next-day returns, "
            "volatility or the frequency of extreme moves. The confidence "
            "intervals show the effects the data cannot rule out: for common "
            "conditions they are a few basis points a day, for rare ones (a "
            "planet in one sign, a conjunction) they are wide, so for those the "
            "null is weak evidence of absence.")
    if h["n_significant_full"] or h["n_event_significant"]:
        parts.append(
            "Some full-sample or event-study tests pass their own correction; "
            "they are descriptive, were not confirmed out of sample and are not "
            "claims.")
    carried = {(c["indicator"], c["target"]) for c in res["confirmation"]}
    extra = [t for t in res["tests"] if t["period"] == "confirm" and t["testable"]
             and t["significant"] and (t["indicator"], t["target"]) not in carried]
    if extra:
        names = "; ".join(
            f"{t['indicator'].replace('_', ' ')} on {TARGET_NAMES[t['target']]} "
            f"({_f(t['effect'])} {t['unit']}, q = {_p(t['q_value'])})" for t in extra)
        parts.append(
            f"Within the confirm period alone, {len(extra)} test"
            f"{'' if len(extra) == 1 else 's'} passed the BY correction without "
            f"having been significant in the explore period: {names}. Under the "
            "pre-registered rule this is not a finding; it is a candidate that a "
            "future, separately registered test would have to confirm on new data.")
    stat = {s["series"]: s for s in res["stationarity"]}
    if "absret" in stat and not stat["absret"]["stationary"]:
        parts.append(
            "KPSS rejects level-stationarity of absolute returns (long memory in "
            "volatility). The circular-shift null keeps that dependence, which "
            "is why it is used instead of an i.i.d. test.")
    if res["provisional"]:
        parts.append(provisional_banner(res))
    return "\n\n".join(parts)


def indicator_table(hypothesis_path) -> str:
    """Return the pre-registered indicator family from hypothesis.yaml."""
    import yaml

    cfg = yaml.safe_load(Path(hypothesis_path).read_text())
    rows = []
    for s in cfg["indicators"]:
        what = s.get("rule") or ", ".join(s.get("signs", []))
        if s["kind"] == "tithi":
            what = "tithi " + ", ".join(str(t) for t in s["tithis"])
        rows.append([s["id"].replace("_", " "), s["kind"],
                     str(s.get("body", "-")).title(), what or "-"])
    return _table(["Indicator", "Kind", "Body", "Definition"], rows)


def reproducibility(res: Dict, study: str) -> str:
    """Describe how this result was produced: command, commit, data hash."""
    g = res.get("git") or {}
    dirty = " (working tree had uncommitted changes)" if g.get("dirty") else ""
    return (f"Generated {res['generated_utc']} by `studies/{study}/scripts/"
            f"pipeline.py --seed {res['seed']}` at commit "
            f"`{(g.get('commit') or 'n/a')[:10]}`{dirty}. Data SHA-256 "
            f"`{res['data']['sha256']}`. The manifest is `artifacts/manifest.json`.")
