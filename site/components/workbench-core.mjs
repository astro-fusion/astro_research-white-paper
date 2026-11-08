// Rule workbench core: evaluates a rule on the explore-period daily arrays and
// computes the same statistics as vedic_astrology_core.stats, in the browser.
//
// Ports, kept line-for-line in meaning:
//   rateRatio        <- stats/rates.py rate_ratio (exact conditional binomial
//                       CI, Clopper-Pearson; one-sided and two-sided p)
//   shiftTest        <- stats/rates.py rate_ratio_shift_test with
//                       stats/nulls.py circular_shift_offsets (offsets uniform
//                       in [minShift, n - minShift]) and
//                       stats/permutation.py empirical_p_value
//   molchanPoint     <- stats/molchan.py molchan_point
// The RNG differs from numpy's, so null draws (and the shift p) differ by
// Monte Carlo error only; the rate ratio, CI and exact p agree to rounding.
// tests/test_site_workbench_port.py checks the agreement against Python.

export const SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
  "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
export const CLIENT_PREDICATES = ["conjunct_within", "separation_within", "in_sign",
  "in_house_from", "in_kendra_from", "in_trikona_from", "retrograde", "moon_phase",
  "in_nakshatra", "dasha_lord_is"];

// ------------------------------------------------------------ special functions
const LANCZOS = [676.5203681218851, -1259.1392167224028, 771.32342877765313,
  -176.61502916214059, 12.507343278686905, -0.13857109526572012,
  9.9843695780195716e-6, 1.5056327351493116e-7];

export function lgamma(x) {
  if (x < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * x))) - lgamma(1 - x);
  x -= 1;
  let a = 0.99999999999980993;
  const t = x + 7.5;
  for (let i = 0; i < 8; i++) a += LANCZOS[i] / (x + i + 1);
  return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
}

function betacf(a, b, x) {
  const FPMIN = 1e-300;
  let c = 1, d = 1 - ((a + b) * x) / (a + 1);
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= 10000; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((a + m2 - 1) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; h *= d * c;
    aa = (-(a + m) * (a + b + m) * x) / ((a + m2) * (a + m2 + 1));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < 1e-15) break;
  }
  return h;
}

// Regularised incomplete beta I_x(a, b).
export function betai(a, b, x) {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const lbt = lgamma(a + b) - lgamma(a) - lgamma(b) + a * Math.log(x) + b * Math.log(1 - x);
  if (x < (a + 1) / (a + b + 2)) return Math.exp(lbt) * betacf(a, b, x) / a;
  return 1 - Math.exp(lbt) * betacf(b, a, 1 - x) / b;
}

// Beta(a, b) quantile by bisection on betai (monotone; 200 halvings).
export function betaPpf(q, a, b) {
  let lo = 0, hi = 1;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (betai(a, b, mid) < q) lo = mid; else hi = mid;
    if (hi - lo < 1e-17) break;
  }
  return (lo + hi) / 2;
}

const logPmf = (k, n, p) => lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)
  + (k ? k * Math.log(p) : 0) + (n - k ? (n - k) * Math.log1p(-p) : 0);

// P(X >= k) for X ~ Binomial(n, p): scipy binom.sf(k - 1, n, p).
export const binomSfGe = (k, n, p) => (k <= 0 ? 1 : k > n ? 0 : betai(k, n - k + 1, p));

// scipy.stats.binomtest(k, n, p, "two-sided"): sum of pmf(i) <= pmf(k) (1 + 1e-7).
export function binomTwoSided(k, n, p) {
  if (k === p * n) return 1;
  const d = logPmf(k, n, p) + Math.log(1 + 1e-7);
  let s = 0;
  for (let i = 0; i <= n; i++) {
    const l = logPmf(i, n, p);
    if (l <= d) s += Math.exp(l);
  }
  return Math.min(1, s);
}

// ------------------------------------------------------------------ statistics
export function rateRatio(nIn, tIn, nOut, tOut, ciLevel = 0.95) {
  if (tIn <= 0 || tOut <= 0) throw new Error("both exposures must be positive");
  const n = nIn + nOut, oddsScale = tOut / tIn;
  const rr = nOut > 0 ? (nIn / tIn) / (nOut / tOut) : Infinity;
  if (n === 0) return { nIn, tIn, nOut, tOut, rateRatio: NaN, ciLow: 0, ciHigh: Infinity, pGreater: 1, pTwoSided: 1 };
  const a = 1 - ciLevel;
  const pLo = nIn > 0 ? betaPpf(a / 2, nIn, n - nIn + 1) : 0;
  const pHi = nIn < n ? betaPpf(1 - a / 2, nIn + 1, n - nIn) : 1;
  const lo = (pLo / (1 - pLo)) * oddsScale;
  const hi = pHi < 1 ? (pHi / (1 - pHi)) * oddsScale : Infinity;
  const p0 = tIn / (tIn + tOut);
  return { nIn, tIn, nOut, tOut, rateRatio: rr, ciLow: lo, ciHigh: hi,
    pGreater: binomSfGe(nIn, n, p0), pTwoSided: binomTwoSided(nIn, n, p0) };
}

// Event "bins" are row indices, repeated once per event (a day with 3 events
// appears 3 times), exactly as the Python functions take them.
export function eventBins(counts) {
  const out = [];
  counts.forEach((c, i) => { for (let j = 0; j < c; j++) out.push(i); });
  return Int32Array.from(out);
}

export function indicatorRateRatio(ev, ind, ciLevel = 0.95) {
  let nIn = 0, tIn = 0;
  for (const e of ev) nIn += ind[e] ? 1 : 0;
  for (let i = 0; i < ind.length; i++) tIn += ind[i] ? 1 : 0;
  return rateRatio(nIn, tIn, ev.length - nIn, ind.length - tIn, ciLevel);
}

export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function circularShiftOffsets(n, minShift, nDraws, rand) {
  if (minShift < 1) throw new Error("minShift must be at least 1");
  if (n - minShift < minShift) throw new Error(`series of length ${n} is too short for minShift ${minShift}`);
  const span = n - 2 * minShift + 1;
  return Int32Array.from({ length: nDraws }, () => minShift + Math.floor(rand() * span));
}

export function empiricalP(observed, nullStats, alternative = "greater") {
  const n = nullStats.length;
  let ext = 0;
  if (alternative === "greater") for (const s of nullStats) ext += s >= observed ? 1 : 0;
  else if (alternative === "less") for (const s of nullStats) ext += s <= observed ? 1 : 0;
  else {
    let c = 0; for (const s of nullStats) c += s; c /= n;
    for (const s of nullStats) ext += Math.abs(s - c) >= Math.abs(observed - c) ? 1 : 0;
  }
  return (ext + 1) / (n + 1);
}

// numpy.percentile with linear interpolation.
export function percentile(sorted, q) {
  if (!sorted.length) return NaN;
  const h = (q / 100) * (sorted.length - 1), i = Math.floor(h);
  return i + 1 < sorted.length ? sorted[i] + (h - i) * (sorted[i + 1] - sorted[i]) : sorted[i];
}

export function shiftTest(ev, ind, minShift, nDraws = 500, seed = 42, alternative = "greater") {
  const n = ind.length, exact = indicatorRateRatio(ev, ind);
  const offsets = circularShiftOffsets(n, minShift, nDraws, mulberry32(seed));
  const counts = new Float64Array(nDraws);
  offsets.forEach((off, k) => {
    let c = 0;
    for (const e of ev) c += ind[(((e - off) % n) + n) % n] ? 1 : 0;
    counts[k] = c;
  });
  const nullRR = Array.from(counts, (c) => (c / exact.tIn) / ((ev.length - c) / exact.tOut));
  const finite = nullRR.filter(Number.isFinite).sort((a, b) => a - b);
  return { exact, pValue: empiricalP(exact.nIn, counts, alternative), nullRR,
    nullMedian: percentile(finite, 50), nullQ025: percentile(finite, 2.5), nullQ975: percentile(finite, 97.5),
    nDraws, minShift, alternative };
}

export function molchanPoint(ind, ev) {
  if (!ev.length) throw new Error("need at least one event");
  let on = 0, hit = 0;
  for (let i = 0; i < ind.length; i++) on += ind[i] ? 1 : 0;
  for (const e of ev) hit += ind[e] ? 1 : 0;
  return { tau: on / ind.length, nu: 1 - hit / ev.length };
}

// ------------------------------------------------------------- rule evaluation
// Decode workbench_<study>.json rows (arrays of arrays) into columns.
export function decode(wb) {
  const f = Object.fromEntries(wb.fields.map((k, i) => [k, i]));
  const col = (k) => wb.rows.map((r) => r[f[k]]);
  const lon = Object.fromEntries(wb.planets.map((p) => [p, Float64Array.from(col(p))]));
  const dayNum = Int32Array.from(wb.rows, (r) => Math.round(Date.parse(r[0] + "T00:00:00Z") / 864e5));
  const events = Object.fromEntries(wb.events.map((k) => [k, Int32Array.from(col(k))]));
  return { n: wb.rows.length, dates: col("date"), dayNum, lon, retro: Int32Array.from(col("retro_mask")),
    tithi: Int32Array.from(col("tithi")), nak: Int32Array.from(col("nakshatra")), events,
    planets: wb.planets, nakshatras: wb.nakshatras, dasha: wb.dasha || {} };
}

// Expand the dasha runs of one rule's natal chart into per-row lords.
export function dashaLevels(cols, runs) {
  const l1 = new Int8Array(cols.n).fill(-1), l2 = new Int8Array(cols.n).fill(-1);
  runs.forEach(([start, a, b], k) => {
    const end = k + 1 < runs.length ? runs[k + 1][0] : cols.n;
    l1.fill(a, start, end); l2.fill(b, start, end);
  });
  return [l1, l2];
}

const sep = (a, b) => { const d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; };
const signOf = (x) => Math.floor((((x % 360) + 360) % 360) / 30);
const HOUSES = { in_kendra_from: [1, 4, 7, 10], in_trikona_from: [1, 5, 9] };

function leaf(pred, p, cols, ctx) {
  const out = new Uint8Array(cols.n), L = cols.lon;
  for (let t = 0; t < cols.n; t++) {
    let v = false;
    switch (pred) {
      case "conjunct_within": v = sep(L[p.planets[0]][t], L[p.planets[1]][t]) <= p.orb; break;
      case "separation_within": v = Math.abs(sep(L[p.planets[0]][t], L[p.planets[1]][t]) - p.angle) <= p.orb; break;
      case "in_sign": v = p.signs.includes(SIGNS[signOf(L[p.planet][t])]); break;
      case "in_house_from": case "in_kendra_from": case "in_trikona_from": {
        const h = ((signOf(L[p.planet][t]) - signOf(L[p.from][t])) % 12 + 12) % 12 + 1;
        v = (p.houses || HOUSES[pred]).includes(h); break;
      }
      case "retrograde": v = (cols.retro[t] >> cols.planets.indexOf(p.planet)) & 1; break;
      case "moon_phase": {
        const ti = cols.tithi[t], checks = [];
        if (p.phase) checks.push(p.phase === "new" ? ti === 30 : p.phase === "full" ? ti === 15 : (ti <= 15 ? "waxing" : "waning") === p.phase);
        if (p.tithis && p.tithis.length) checks.push(p.tithis.includes(ti));
        v = checks.every(Boolean); break;
      }
      case "in_nakshatra": {
        const k = p.planet === "Moon" ? cols.nak[t] : Math.floor(L[p.planet][t] / (360 / 27)) % 27;
        v = p.nakshatras.includes(cols.nakshatras[k]); break;
      }
      case "dasha_lord_is": {
        const lv = ctx.dasha && ctx.dasha[(p.level || 1) - 1];
        if (!lv) throw new Error("no dasha data for this rule's natal chart");
        v = lv[t] >= 0 && p.lords.includes(cols.planets[lv[t]]); break;
      }
      default: throw new Error(`predicate ${pred} is not evaluated in the browser`);
    }
    out[t] = v ? 1 : 0;
  }
  return out;
}

// Substitute slider values into "$name" slots (rules.json machine_template,
// schema v2). With generic = true (rules without published params), a slider
// named like a leaf key (orb) overrides that key in every leaf that has it.
export function applyParams(params, values, generic = false) {
  const out = {};
  for (const [k, v] of Object.entries(params)) {
    if (typeof v === "string" && v.startsWith("$")) {
      if (!(v.slice(1) in values)) throw new Error(`no value for parameter ${v}`);
      out[k] = values[v.slice(1)];
    } else if (generic && k in values && typeof v === "number") out[k] = values[k];
    else out[k] = v;
  }
  return out;
}

export function evaluate(node, cols, ctx = {}, values = {}, generic = false) {
  if (node.pred) return leaf(node.pred, applyParams(node.params, values, generic), cols, ctx);
  const kids = node.of.map((c) => evaluate(c, cols, ctx, values, generic));
  const out = new Uint8Array(cols.n);
  for (let t = 0; t < cols.n; t++) {
    let s = 0; for (const k of kids) s += k[t];
    out[t] = node.op === "all" ? +(s === kids.length) : node.op === "any" ? +(s > 0)
      : node.op === "not" ? +(s === 0) : +(s >= node.n);
  }
  return out;
}

// Window: an event on row t counts as "in the rule's window" when the rule held
// on some row d with dayNum[d] in [dayNum[t] - after, dayNum[t] + before].
export function dilate(ind, dayNum, before = 0, after = 0) {
  if (!before && !after) return ind;
  const n = ind.length, pre = new Int32Array(n + 1), out = new Uint8Array(n);
  for (let i = 0; i < n; i++) pre[i + 1] = pre[i] + ind[i];
  let lo = 0, hi = 0;
  for (let t = 0; t < n; t++) {
    while (lo < n && dayNum[lo] < dayNum[t] - after) lo++;
    while (hi < n && dayNum[hi] <= dayNum[t] + before) hi++;
    out[t] = pre[hi] - pre[lo] > 0 ? 1 : 0;
  }
  return out;
}
