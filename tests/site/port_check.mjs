// Runs the browser workbench core (site/components/workbench-core.mjs) in Node
// on a spec file and prints the statistics as JSON, so the Python tests can
// compare the port with vedic_astrology_core.stats.
//
// node tests/site/port_check.mjs spec.json
// spec: {workbench, tree, event, values?, generic?, before?, after?, natal_rule?,
//        min_shift?, draws?, seed?, alternative?}
import { readFileSync } from "node:fs";
import { decode, dashaLevels, dilate, eventBins, evaluate, molchanPoint, shiftTest } from "../../site/components/workbench-core.mjs";

const spec = JSON.parse(readFileSync(process.argv[2], "utf8"));
const wb = JSON.parse(readFileSync(spec.workbench, "utf8"));
const cols = decode(wb);
const ctx = spec.natal_rule ? { dasha: dashaLevels(cols, wb.dasha[spec.natal_rule].runs) } : {};
const raw = evaluate(spec.tree, cols, ctx, spec.values || {}, !!spec.generic);
const ind = dilate(raw, cols.dayNum, spec.before || 0, spec.after || 0);
const ev = eventBins(cols.events[spec.event]);
const st = shiftTest(ev, ind, spec.min_shift || wb.min_shift, spec.draws || 500, spec.seed || 42, spec.alternative || "greater");
const finite = (x) => (Number.isFinite(x) ? x : null);
process.stdout.write(JSON.stringify({
  indicator_sum: ind.reduce((a, b) => a + b, 0),
  n_in: st.exact.nIn, t_in: st.exact.tIn, n_out: st.exact.nOut, t_out: st.exact.tOut,
  rate_ratio: finite(st.exact.rateRatio), ci_low: finite(st.exact.ciLow), ci_high: finite(st.exact.ciHigh),
  p_greater: st.exact.pGreater, p_two_sided: st.exact.pTwoSided,
  p_shift: st.pValue, null_median: st.nullMedian, molchan: molchanPoint(ind, ev)
}));
