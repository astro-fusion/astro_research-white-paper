"""The browser workbench agrees with the Python statistics it ports.

``site/components/workbench-core.mjs`` re-implements the rate ratio
(``stats.rates``), the circular-shift null (``stats.nulls``) and the Molchan
point (``stats.molchan``) for the browser. These tests run it under Node on
the exported explore arrays and compare it with the Python functions, and
check that the exported arrays reproduce the rule engine's own verdicts.
"""

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from vedic_astrology_core.stats.molchan import molchan_point
from vedic_astrology_core.stats.nulls import make_rng
from vedic_astrology_core.stats.rates import (
    indicator_rate_ratio,
    rate_ratio_shift_test,
)

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "site" / "data"
NODE = shutil.which("node")


def workbench(key):
    """Return a workbench file and its columns by field name."""
    doc = json.loads((DATA / f"workbench_{key}.json").read_text(encoding="utf-8"))
    cols = {k: [r[i] for r in doc["rows"]] for i, k in enumerate(doc["fields"])}
    return doc, cols


def rule(rule_id):
    """Return one exported rule."""
    rules = json.loads((DATA / "rules.json").read_text(encoding="utf-8"))["rules"]
    return next(r for r in rules if r["id"] == rule_id)


def separation(a, b):
    """Shortest arc between two longitude arrays."""
    d = np.abs(np.asarray(a) - np.asarray(b)) % 360
    return np.minimum(d, 360 - d)


def dilate(ind, dates, after):
    """Python twin of the browser window: rule held within ``after`` days before."""
    day = np.array([np.datetime64(d, "D").astype(int) for d in dates], dtype=np.int64)
    out = np.zeros(len(ind), dtype=bool)
    for t in range(len(ind)):
        lo = np.searchsorted(day, day[t] - after, side="left")
        out[t] = ind[lo : t + 1].any()
    return out


def run_node(tmp_path, spec):
    """Run tests/site/port_check.mjs on a spec and return its JSON."""
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    out = subprocess.run(
        [NODE, "tests/site/port_check.mjs", str(path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


CASES = {
    "mars_saturn_gk": dict(
        key="earthquake",
        rule="seismic.mangal_shani_malefic",
        event="ev_gk",
        alternative="greater",
        after=0,
        values={"orb": 10},  # the slider moved off the published 15
        python=lambda c: separation(c["Mars"], c["Saturn"]) <= 10,
    ),
    "mars_ketu_raw_window7": dict(
        key="earthquake",
        rule="seismic.mangal_ketu_primary",
        event="ev_raw",
        alternative="greater",
        after=7,
        values={"orb": 13},
        python=lambda c: separation(c["Mars"], c["Ketu"]) <= 13,
    ),
    "jupiter_retro_gold": dict(
        key="gold",
        rule="financial.jupiter_retrograde_contraction",
        event="extreme",
        alternative="two-sided",
        after=0,
        values={},
        python=lambda c: (np.asarray(c["retro_mask"]) >> 4) & 1 == 1,
    ),
}


@pytest.mark.skipif(NODE is None, reason="Node is not installed")
@pytest.mark.parametrize("name", CASES)
def test_browser_rate_ratio_matches_python(tmp_path, name):
    """Rate ratio, exact CI and p-values agree; the shift p within MC error."""
    case = CASES[name]
    doc, cols = workbench(case["key"])
    ind = dilate(case["python"](cols), cols["date"], case["after"])
    ev = np.repeat(np.arange(len(ind)), np.asarray(cols[case["event"]], dtype=int))
    py = indicator_rate_ratio(ev, ind)
    js = run_node(
        tmp_path,
        {
            "workbench": str(DATA / f"workbench_{case['key']}.json"),
            "tree": rule(case["rule"])["machine_template"],
            "values": case["values"],
            "event": case["event"],
            "after": case["after"],
            "draws": 2000,
            "alternative": case["alternative"],
        },
    )
    assert js["indicator_sum"] == int(ind.sum())
    assert (js["n_in"], js["t_in"]) == (py.n_in, py.t_in)
    for k in ("rate_ratio", "ci_low", "ci_high", "p_greater", "p_two_sided"):
        assert js[k] == pytest.approx(getattr(py, k), rel=1e-9, abs=1e-12), k
    tau, nu = molchan_point(ind, ev)
    assert js["molchan"]["tau"] == pytest.approx(tau, abs=1e-12)
    assert js["molchan"]["nu"] == pytest.approx(nu, abs=1e-12)
    shift = rate_ratio_shift_test(
        ev, ind, doc["min_shift"], 2000, make_rng(42), case["alternative"]
    )
    assert js["p_shift"] == pytest.approx(shift.p_value, abs=0.06)


def test_exported_arrays_reproduce_the_rule_engine():
    """The browser's inputs give the engine's verdict on sampled days."""
    from vedic_astrology_core.rules.engine import evaluate
    from vedic_astrology_core.rules.loader import load_rules

    loaded, _ = load_rules([REPO / "rules/seismic/mangal_shani_malefic.yaml"])
    r = loaded[0].rule
    _, cols = workbench("earthquake")
    sep = separation(cols["Mars"], cols["Saturn"])
    rows = np.random.default_rng(7).choice(len(sep), 150, replace=False)
    for i in rows:
        if abs(sep[i] - 15) < 0.02:
            continue  # within the 0.01 deg rounding of the export
        y, m, d = (int(x) for x in cols["date"][i].split("-"))
        fired = evaluate(r, datetime(y, m, d, 12, tzinfo=timezone.utc)).fired
        assert fired == bool(sep[i] <= 15), cols["date"][i]
