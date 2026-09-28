/* ==================================================================
   LookThrough engine — pure functions over DB. Mirrors verify/recompute.py
   Works with real, incomplete data: every figure that cannot be computed
   returns null and the UI shows "—" instead of guessing.
   ================================================================== */
const IX = {}; // indexes rebuilt by reindex()

function reindex() {
  const dates = DB.meta.dates || [];
  IX.t = Object.fromEntries(dates.map((d, i) => [d, i]));
  IX.T = dates.length - 1;
  // AMC files publish some names in capitals; fund-only companies carry the legal "Limited" suffix the rest of the app does not show
  DB.companies.forEach(c => { if (c.name) c.name = niceCase(c.name).replace(/,?\s+(Limited|Ltd\.?)$/i, ""); });
  IX.co = Object.fromEntries(DB.companies.map(c => [c.code, c]));
  IX.sch = Object.fromEntries(DB.schemes.map(s => [s.scheme_id, s]));
  IX.mem = Object.fromEntries(DB.members.map(m => [m.member_id, m]));
  const blank = () => Array(dates.length).fill(null);
  IX.px = {}; DB.prices.forEach(r => { if (r.date in IX.t) (IX.px[r.code] ||= blank())[IX.t[r.date]] = +r.close; });
  IX.nav = {}; DB.nav_history.forEach(r => { if (r.date in IX.t) (IX.nav[r.scheme_id + "|" + r.plan] ||= blank())[IX.t[r.date]] = +r.nav; });
  IX.idx = {}; IX.idxName = {};
  DB.indices.forEach(r => { if (r.date in IX.t) { (IX.idx[r.index_code] ||= blank())[IX.t[r.date]] = +r.level; IX.idxName[r.index_code] = r.index_name; } });
  IX.mktCode = IX.idx.NIFTY500 ? "NIFTY500" : IX.idx.NIFTY50 ? "NIFTY50" : Object.keys(IX.idx)[0] || null;
  IX.mkt = IX.mktCode ? IX.idx[IX.mktCode] : null;
  IX.portBy = {};
  const asOn = DB.meta.as_on;
  DB.scheme_portfolios.forEach(r => { if (r.portfolio_date <= asOn) (((IX.portBy[r.scheme_id] ||= {})[r.portfolio_date]) ||= []).push({ code: r.code, w: +r.weight_pct }); });
  IX.portDates = Object.fromEntries(Object.entries(IX.portBy).map(([s, o]) => [s, Object.keys(o).sort()]));
  IX.fin = {}; DB.financials.forEach(r => (IX.fin[r.code] ||= []).push(r));
  Object.values(IX.fin).forEach(a => a.sort((x, y) => x.fy.localeCompare(y.fy)));
  IX.idxW = {}; DB.index_constituents.forEach(r => ((IX.idxW[r.index_code] ||= {})[r.code] = +r.weight_pct));
  CACHE.clear();
}
const CACHE = new Map();
function memo(key, fn) { if (!CACHE.has(key)) CACHE.set(key, fn()); return CACHE.get(key); }
const hasData = () => DB.meta.mode !== "empty" && DB.transactions.length > 0;
const mktName = () => (IX.idxName[IX.mktCode] || "market index").replace(" (price index)", "");

/* ---------------- dates & maths ---------------- */
const parseD = s => { const [y, m, d] = s.split("-").map(Number); return Date.UTC(y, m - 1, d); };
const daysBetween = (a, b) => Math.round((parseD(b) - parseD(a)) / 864e5);
function addMonths(s, n) {
  const [y, m, d] = s.split("-").map(Number); const tot = m - 1 + n;
  const yy = y + Math.floor(tot / 12), mm = ((tot % 12) + 12) % 12 + 1;
  const last = new Date(Date.UTC(yy, mm, 0)).getUTCDate();
  return `${yy}-${String(mm).padStart(2, "0")}-${String(Math.min(d, last)).padStart(2, "0")}`;
}
const isLT = (buy, on) => addMonths(buy, DB.policy.lt_months) < on;
const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
const std = a => { const m = mean(a); return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1)); };
const cov = (a, b) => { const ma = mean(a), mb = mean(b); return a.reduce((s, x, i) => s + (x - ma) * (b[i] - mb), 0) / (a.length - 1); };
const corrOf = (a, b) => cov(a, b) / (std(a) * std(b));
/** Month-on-month returns where both ends exist; returns aligned index list too. */
function rets(arr) { const r = [], ix = []; for (let i = 1; i < arr.length; i++) if (isNum(arr[i]) && isNum(arr[i - 1]) && arr[i - 1] !== 0) { r.push(arr[i] / arr[i - 1] - 1); ix.push(i); } return { r, ix }; }
function pairedRets(a, b) { const x = [], y = []; for (let i = 1; i < a.length; i++) if ([a[i], a[i - 1], b[i], b[i - 1]].every(isNum)) { x.push(a[i] / a[i - 1] - 1); y.push(b[i] / b[i - 1] - 1); } return [x, y]; }
const ratio = (a, b) => (isNum(a) && isNum(b) && b !== 0) ? a / b : null;
const growth = (a, b, yrs) => (isNum(a) && isNum(b) && a > 0 && b > 0) ? (Math.pow(a / b, 1 / yrs) - 1) * 100 : null;

function xirr(flows) {
  if (!flows.length) return null;
  const t0 = Math.min(...flows.map(f => parseD(f[0])));
  const ts = flows.map(([d, v]) => [(parseD(d) - t0) / 864e5 / 365, v]);
  const npv = r => ts.reduce((s, [t, v]) => s + v / Math.pow(1 + r, t), 0);
  // A rate is only published if the NPV at that rate is actually ~0: step-size convergence alone can stop on a non-root.
  const tol = 1e-7 * ts.reduce((s, [, v]) => s + Math.abs(v), 0), root = r => Math.abs(npv(r)) <= tol ? r : null;
  let lo = -0.9999, hi = 10;
  if (npv(lo) * npv(hi) > 0) return null;
  let r = 0.1;
  for (let i = 0; i < 100; i++) {
    const f = npv(r), df = ts.reduce((s, [t, v]) => s - t * v / Math.pow(1 + r, t + 1), 0);
    if (df === 0) break;
    const nr = r - f / df;
    if (!(nr > lo && nr < hi)) break;
    if (Math.abs(nr - r) < 1e-10 && root(nr) !== null) return nr;
    r = nr;
  }
  for (let i = 0; i < 300; i++) { const mid = (lo + hi) / 2; if (npv(lo) * npv(mid) <= 0) hi = mid; else lo = mid; }
  return root((lo + hi) / 2);
}

/* ELSS units are locked in for three years from each allotment (redeemable from the third anniversary). */
const ELSS_LOCK_MONTHS = 36;
function isLocked(assetType, instrument, buyDate, onDate) {
  return assetType === "MF" && IX.sch[instrument]?.category === "ELSS" && addMonths(buyDate, ELSS_LOCK_MONTHS) > onDate;
}
/* ---------------- holdings (FIFO) ---------------- */
function curPrice(assetType, inst, plan) { const a = assetType === "MF" ? IX.nav[inst + "|" + plan] : IX.px[inst]; return a ? a[IX.T] : null; }
function holdingsAll() {
  return memo("holdings", () => {
    const AS = DB.meta.as_on;
    const tx = [...DB.transactions].sort((a, b) => a.date.localeCompare(b.date) || a.txn_id.localeCompare(b.txn_id));
    const groups = {};
    tx.forEach(r => (groups[[r.member_id, r.asset_type, r.instrument, r.plan || ""].join("|")] ||= []).push(r));
    const H = [], R = [];
    Object.entries(groups).sort().forEach(([key, g]) => {
      const [member_id, asset_type, instrument, plan] = key.split("|");
      const lots = [], flows = [];
      g.forEach(r => {
        if (r.txn_type === "Sell") {
          let q = +r.units; flows.push([r.date, +r.amount]);
          while (q > 1e-9 && lots.length) {
            const lot = lots[0], take = Math.min(q, lot.u);
            R.push({ member_id, asset_type, instrument, plan, sell_date: r.date, buy_date: lot.d, units: take, gain: take * (r.price - lot.p), term: isLT(lot.d, r.date) ? "LT" : "ST", proceeds: take * r.price, cost: take * lot.p });
            lot.u -= take; q -= take; if (lot.u <= 1e-9) lots.shift();
          }
        } else { lots.push({ d: r.date, u: +r.units, p: +r.price }); flows.push([r.date, -r.amount]); }
      });
      if (!lots.length) return;
      const cp = curPrice(asset_type, instrument, plan);
      if (!isNum(cp)) return;
      const units = lots.reduce((s, l) => s + l.u, 0), cost = lots.reduce((s, l) => s + l.u * l.p, 0), value = units * cp;
      let lt_gain = 0, st_gain = 0, lt_value = 0, locked_value = 0, locked_lt = 0, locked_st = 0;
      lots.forEach(l => {
        const gn = l.u * (cp - l.p), lt = isLT(l.d, AS);
        if (lt) { lt_gain += gn; lt_value += l.u * cp; } else st_gain += gn;
        if (isLocked(asset_type, instrument, l.d, AS)) { locked_value += l.u * cp; if (lt) locked_lt += gn; else locked_st += gn; }
      });
      const first = g[0].date;
      H.push({ key, member_id, asset_type, instrument, plan, units, cost, value, price: cp, avg: cost / units, unrealised: value - cost, lt_gain, st_gain, lt_value, locked_value, locked_lt, locked_st, first, days: daysBetween(first, AS), lots: lots.map(l => ({ ...l })), flows, xirr: xirr([...flows, [AS, value]]) });
    });
    return { H, R };
  });
}
function holdings(member = "ALL") { const { H } = holdingsAll(); return member === "ALL" ? H : H.filter(h => h.member_id === member); }
function realised(member = "ALL") { const { R } = holdingsAll(); return member === "ALL" ? R : R.filter(h => h.member_id === member); }
function memberXirr(member = "ALL") {
  return memo("xirr|" + member, () => {
    const tx = DB.transactions.filter(r => member === "ALL" || r.member_id === member);
    const v = holdings(member).reduce((s, h) => s + h.value, 0);
    return xirr([...tx.map(r => [r.date, r.txn_type === "Sell" ? +r.amount : -r.amount]), [DB.meta.as_on, v]]);
  });
}
function instName(h) { return h.asset_type === "MF" ? IX.sch[h.instrument].name : (IX.co[h.instrument]?.name || h.instrument); }
function terOf(h) { const s = IX.sch[h.instrument]; const v = h.plan === "Regular" ? s.ter_regular : s.ter_direct; return isNum(v) ? +v : null; }
/** Annual cost gap between Regular and Direct plans implied by their NAVs over the last 12 months. */
function impliedGap(sid) {
  return memo("gap|" + sid, () => {
    const d = IX.nav[sid + "|Direct"], r = IX.nav[sid + "|Regular"], T = IX.T;
    if (!d || !r || ![d[T], d[T - 12], r[T], r[T - 12]].every(isNum)) return null;
    return ((d[T] / d[T - 12]) / (r[T] / r[T - 12]) - 1) * 100;
  });
}

/* ---------------- portfolio value history ---------------- */
function valueHistory(member = "ALL") {
  return memo("vh|" + member, () => {
    const tx = DB.transactions.filter(r => member === "ALL" || r.member_id === member);
    const dates = DB.meta.dates, units = {}, out = [];
    let invested = 0, k = 0;
    const sorted = [...tx].sort((a, b) => a.date.localeCompare(b.date));
    const lastPx = {};
    dates.forEach((d, t) => {
      while (k < sorted.length && sorted[k].date <= d) {
        const r = sorted[k++], key = r.asset_type + "|" + r.instrument + "|" + (r.plan || "");
        const sgn = r.txn_type === "Sell" ? -1 : 1;
        units[key] = (units[key] || 0) + sgn * r.units;
        invested += sgn === 1 ? +r.amount : -r.amount;
      }
      let v = 0;
      Object.entries(units).forEach(([key, u]) => {
        const [a, i, p] = key.split("|"), arr = a === "MF" ? IX.nav[i + "|" + p] : IX.px[i];
        const px = arr && isNum(arr[t]) ? arr[t] : lastPx[key];
        if (isNum(px)) { lastPx[key] = px; v += u * px; }
      });
      out.push({ d, value: v, invested });
    });
    return out;
  });
}

/* ---------------- look-through ---------------- */
function portOf(sid, which = 0) { const ds = IX.portDates[sid]; if (!ds || ds.length <= which) return null; const d = ds[ds.length - 1 - which]; return { date: d, rows: IX.portBy[sid][d] }; }
function latestPort() { return memo("latestPort", () => Object.fromEntries(Object.keys(IX.portBy).map(s => [s, portOf(s).rows]))); }
/** Which disclosure each held fund is looked through on. AMCs publish a month's portfolio within about 10 days of month-end,
    so early in a month the latest file can be a month older than the prices. Compared by month: some AMCs date the file
    on the last business day rather than the calendar month-end. */
function holdingsBasis(member = "ALL") {
  return memo("hb|" + member, () => {
    const AS = DB.meta.as_on, held = heldSchemes(member).filter(s => portOf(s)), ds = held.map(s => portOf(s).date).sort();
    const behind = held.filter(s => portOf(s).date.slice(0, 7) < (AS || "").slice(0, 7));
    return { asOn: AS, held, oldest: ds[0] || null, latest: ds[ds.length - 1] || null, behind, behindDates: [...new Set(behind.map(s => portOf(s).date))].sort() };
  });
}
/** One line naming both dates, for page subtitles and the report. */
function basisLine(member = "ALL") {
  const b = holdingsBasis(member); if (!b.latest) return `Prices and NAVs at ${fmtDate(b.asOn)}.`;
  return `Prices and NAVs at ${fmtDate(b.asOn)}; fund holdings as disclosed on ${b.oldest === b.latest ? fmtDate(b.latest) : `${fmtDate(b.oldest)} to ${fmtDate(b.latest)}`}.`;
}
/** Warning shown wherever look-through figures appear when any held fund's holdings are from an earlier month than the prices. */
function holdingsLagNote(member = "ALL") {
  const b = holdingsBasis(member); if (!b.behind.length) return "";
  const n = b.behind.length === b.held.length ? `All ${b.held.length}` : `${b.behind.length} of ${b.held.length}`;
  return `<p class="note warn lag-note"><b>Fund holdings are older than the prices.</b> ${n} held funds are looked through on their ${b.behindDates.map(fmtDate).join(" / ")} disclosure, while prices and NAVs are at ${fmtDate(b.asOn)}. Each AMC publishes a month's portfolio within about 10 days of month-end; until the new files are added, look-through, overlap and policy figures use the earlier holdings.</p>`;
}
function lookThrough(member = "ALL", extra = null) {
  return memo("lt|" + member + (extra ? "|" + JSON.stringify(extra) : ""), () => lookThroughOf(holdings(member), extra));
}
/** Look-through of a set of holdings (at valuation-date values, or revalued ones: see lookThroughLatest). */
function lookThroughOf(H, extra = null) {
  {
    const port = latestPort();
    const m = {}; const get = c => (m[c] ||= { code: c, direct: 0, viaMF: 0, total: 0, contrib: {}, members: {} });
    let debt = 0, cash = 0, mfTotal = 0, directTotal = 0, unmapped = 0;
    const mfVal = {}, unmappedSchemes = new Set();
    H.forEach(h => {
      if (h.asset_type === "MF") { mfVal[h.instrument] = (mfVal[h.instrument] || 0) + h.value; mfTotal += h.value; }
      else { const r = get(h.instrument); r.direct += h.value; r.members[h.member_id] = (r.members[h.member_id] || 0) + h.value; directTotal += h.value; }
    });
    H.filter(h => h.asset_type === "MF" && port[h.instrument]).forEach(h => {
      port[h.instrument].forEach(p => { const r = get(p.code), a = h.value * p.w / 100; r.members[h.member_id] = (r.members[h.member_id] || 0) + a; });
    });
    Object.entries(mfVal).forEach(([sid, v]) => {
      const s = IX.sch[sid], rows = port[sid];
      if (!rows) { unmapped += v; unmappedSchemes.add(sid); return; }
      // Equity from the disclosed weights, debt from the AMC file; cash & other is the balancing residual (TREPS, net receivables, REITs, rounding).
      const eqW = rows.reduce((t, p) => t + p.w, 0), dv = v * (s.debt_pct || 0) / 100;
      debt += dv; cash += v - v * eqW / 100 - dv;
      rows.forEach(p => { const r = get(p.code), a = v * p.w / 100; r.viaMF += a; r.contrib[sid] = (r.contrib[sid] || 0) + a; });
    });
    if (extra) Object.entries(extra).forEach(([c, v]) => { get(c).direct += v; directTotal += v; });
    const rows = Object.values(m).map(r => (r.total = r.direct + r.viaMF, r)).filter(r => r.total > 0).sort((a, b) => b.total - a.total);
    const eq = rows.reduce((s, r) => s + r.total, 0);
    rows.forEach(r => r.pct = eq ? r.total / eq * 100 : 0);
    return { rows, eq, debt, cash, unmapped, unmappedSchemes: [...unmappedSchemes], mfTotal, directTotal, total: mfTotal + directTotal };
  }
}
/** The four concentration limits (single stock, sector, top 10, HHI) for one look-through: each test's value, limit and status. */
function limitTests(lt) {
  const P = DB.policy, con = concentration(lt), sec = groupBy(lt, "sector")[0];
  if (!con.top) return [];
  const st = (v, l) => v > l ? "crit" : v > l * 0.9 ? "warn" : "ok";
  return [
    { k: "stock", code: con.top.code, t: "Largest single stock", who: IX.co[con.top.code]?.name || con.top.code, v: con.top.pct, lim: P.max_single_stock_pct, f: v => fmtPct(v, 2) },
    { k: "sector", t: "Largest sector", who: sec.key, v: sec.pct, lim: P.max_sector_pct, f: v => fmtPct(v, 2) },
    { k: "top10", t: "Top 10 stocks combined", who: "", v: con.top10, lim: P.max_top10_pct, f: v => fmtPct(v, 2) },
    { k: "hhi", t: "Herfindahl-Hirschman Index", who: "", v: con.hhi, lim: P.max_hhi, f: v => fmtHHI(v) },
  ].map(x => ({ ...x, s: st(x.v, x.lim) }));
}
function concentration(lt) {
  if (!lt.rows.length) return { hhi: null, effN: null, top10: null, top: null, n: 0 };
  const w = lt.rows.map(r => r.total / lt.eq), hhi = w.reduce((s, x) => s + x * x, 0);
  return { hhi, effN: 1 / hhi, top10: w.slice(0, 10).reduce((s, x) => s + x, 0) * 100, top: lt.rows[0], n: lt.rows.length };
}
const coField = (code, field) => IX.co[code]?.[field] || (field === "cap" ? "Unclassified" : "Others");
function groupBy(lt, field) {
  const s = {}; lt.rows.forEach(r => { const k = coField(r.code, field); s[k] = (s[k] || 0) + r.total; });
  return Object.entries(s).map(([k, v]) => ({ key: k, v, pct: v / lt.eq * 100 })).sort((a, b) => b.v - a.v);
}
function benchWeights(field = "sector") {
  const s = {}; Object.entries(IX.idxW.BENCH || {}).forEach(([c, w]) => { const k = coField(c, field); s[k] = (s[k] || 0) + w; }); return s;
}

/* ---------------- stock analytics ---------------- */
function stockStats(code) {
  return memo("ss|" + code, () => {
    const p = IX.px[code], T = IX.T;
    if (!p || !isNum(p[T]) || !IX.mkt) return null;
    const [x, y] = pairedRets(p, IX.mkt), first = p.findIndex(isNum), last13 = p.slice(-13).filter(isNum);
    return { r1y: isNum(p[T - 12]) ? p[T] / p[T - 12] - 1 : null, r3m: isNum(p[T - 3]) ? p[T] / p[T - 3] - 1 : null,
      cagr3: first === 0 ? Math.pow(p[T] / p[0], 1 / 3) - 1 : null, vol: x.length > 12 ? std(x) * Math.sqrt(12) : null,
      beta: x.length > 12 ? cov(x, y) / (std(y) ** 2) : null, hi52: Math.max(...last13), lo52: Math.min(...last13), offHigh: p[T] / Math.max(...last13) - 1 };
  });
}
/** Look-through equity beta; stocks without price history are assumed to move with the market (beta 1). */
function portBeta(lt) {
  if (!lt.eq) return null;
  return lt.rows.reduce((s, r) => s + r.total / lt.eq * (stockStats(r.code)?.beta ?? 1), 0);
}
function betaCoverage(lt) { return lt.eq ? lt.rows.filter(r => isNum(stockStats(r.code)?.beta)).reduce((s, r) => s + r.total, 0) / lt.eq * 100 : 0; }

/* ---------------- fund analytics ---------------- */
function fundStats(sid, plan = "Direct") {
  return memo("fs|" + sid + plan, () => {
    const n = IX.nav[sid + "|" + plan], s = IX.sch[sid], bn = IX.idx[s.benchmark] || IX.mkt, T = IX.T;
    if (!n || !isNum(n[T])) return null;
    const RF = DB.policy.risk_free_pct / 100, rfm = Math.pow(1 + RF, 1 / 12) - 1;
    const full = isNum(n[0]) && bn && isNum(bn[0]) && isNum(bn[T]);
    const cagr = isNum(n[0]) ? Math.pow(n[T] / n[0], 1 / 3) - 1 : null, bcagr = full ? Math.pow(bn[T] / bn[0], 1 / 3) - 1 : null;
    const [r, br] = pairedRets(n, bn);
    const vol = r.length > 12 ? std(r) * Math.sqrt(12) : null;
    const dd = r.length > 12 ? Math.sqrt(mean(r.map(x => Math.min(0, x - rfm) ** 2))) * Math.sqrt(12) : null;
    const beta = r.length > 12 ? cov(r, br) / (std(br) ** 2) : null;
    const te = r.length > 12 ? std(r.map((x, i) => x - br[i])) * Math.sqrt(12) : null;
    let peak = -Infinity, mdd = 0; n.forEach(v => { if (isNum(v)) { peak = Math.max(peak, v); mdd = Math.max(mdd, 1 - v / peak); } });
    const up = r.filter((x, i) => br[i] > 0), bup = br.filter(x => x > 0), dn = r.filter((x, i) => br[i] < 0), bdn = br.filter(x => x < 0);
    const roll = [], rollB = []; for (let t = 12; t <= T; t++) { roll.push(isNum(n[t]) && isNum(n[t - 12]) ? n[t] / n[t - 12] - 1 : null); rollB.push(bn && isNum(bn[t]) && isNum(bn[t - 12]) ? bn[t] / bn[t - 12] - 1 : null); }
    const rb = roll.map((x, i) => isNum(x) && isNum(rollB[i]) ? x > rollB[i] : null).filter(x => x !== null);
    const at = k => isNum(n[T - k]) ? n[T] / n[T - k] - 1 : null;
    return {
      r1m: at(1), r3m: at(3), r6m: at(6), r1y: at(12), cagr3: cagr, bench3: bcagr, bench1y: bn && isNum(bn[T - 12]) ? bn[T] / bn[T - 12] - 1 : null,
      vol, sharpe: isNum(cagr) && vol ? (cagr - RF) / vol : null, sortino: isNum(cagr) && dd ? (cagr - RF) / dd : null, mdd, beta,
      alpha: isNum(cagr) && isNum(bcagr) && isNum(beta) ? cagr - (RF + beta * (bcagr - RF)) : null, te, ir: isNum(cagr) && isNum(bcagr) && te ? (cagr - bcagr) / te : null,
      upCap: up.length && bup.length ? mean(up) / mean(bup) : null, downCap: dn.length && bdn.length ? mean(dn) / mean(bdn) : null,
      rollBeat: rb.length ? rb.filter(Boolean).length / rb.length : null, roll, rollB, r, br,
    };
  });
}
function categoryRank(sid) {
  const cat = IX.sch[sid].category, peers = DB.schemes.filter(s => s.category === cat).map(s => [s.scheme_id, fundStats(s.scheme_id)?.cagr3]).filter(p => isNum(p[1])).sort((a, b) => b[1] - a[1]);
  const i = peers.findIndex(p => p[0] === sid);
  return { rank: i >= 0 ? i + 1 : null, of: peers.length };
}

/* ---------------- overlap & activity ---------------- */
function overlap(a, b) {
  const port = latestPort(), wa = {}, wb = {};
  (port[a] || []).forEach(p => wa[p.code] = p.w); (port[b] || []).forEach(p => wb[p.code] = p.w);
  let o = 0; const common = [];
  Object.keys(wa).forEach(k => { if (k in wb) { const mn = Math.min(wa[k], wb[k]); o += mn; common.push({ code: k, a: wa[k], b: wb[k], min: mn }); } });
  return { overlap: port[a] && port[b] ? o : null, common: common.sort((x, y) => y.min - x.min), nA: Object.keys(wa).length, nB: Object.keys(wb).length, onlyA: Object.keys(wa).filter(k => !(k in wb)), onlyB: Object.keys(wb).filter(k => !(k in wa)) };
}
function heldSchemes(member = "ALL") { return [...new Set(holdings(member).filter(h => h.asset_type === "MF").map(h => h.instrument))].sort(); }
function activity() {
  return memo("activity", () => {
    const perScheme = {}, stock = {};
    DB.schemes.forEach(s => {
      const L = portOf(s.scheme_id, 0), P = portOf(s.scheme_id, 1);
      if (!L || !P) { perScheme[s.scheme_id] = null; return; }
      const a = Object.fromEntries(L.rows.map(p => [p.code, p.w])), b = Object.fromEntries(P.rows.map(p => [p.code, p.w]));
      const codes = [...new Set([...Object.keys(a), ...Object.keys(b)])];
      // Active change = actual weight minus the weight price moves alone would give: prev x (1 + stock return) / (1 + fund return).
      // A stock without a price series is assumed to move with the fund, so its signal is the raw weight change.
      const i0 = DB.meta.dates.indexOf(P.date), i1 = DB.meta.dates.indexOf(L.date), nav = IX.nav[s.scheme_id + "|Direct"];
      const ret = arr => arr && i0 >= 0 && i1 >= 0 && isNum(arr[i0]) && isNum(arr[i1]) && arr[i0] ? arr[i1] / arr[i0] - 1 : null;
      const rf = ret(nav) ?? 0;
      const passive = c => { const rs = ret(IX.px[c]) ?? rf; return (b[c] || 0) * (1 + rs) / (1 + rf); };
      const ch = codes.map(c => ({ code: c, now: a[c] || 0, prev: b[c] || 0, passive: passive(c), dw: (a[c] || 0) - passive(c) }));
      perScheme[s.scheme_id] = { from: P.date, to: L.date, entries: ch.filter(x => x.now > 0 && x.prev === 0), exits: ch.filter(x => x.now === 0 && x.prev > 0), changes: ch.sort((x, y) => y.dw - x.dw), turnover: ch.reduce((t, x) => t + Math.abs(x.dw), 0) / 2 };
      ch.forEach(x => { const st = (stock[x.code] ||= { code: x.code, adding: 0, reducing: 0, entries: 0, exits: 0, netW: 0, holders: 0 }); if (x.dw > 0.25) st.adding++; if (x.dw < -0.25) st.reducing++; if (x.now > 0 && x.prev === 0) st.entries++; if (x.now === 0 && x.prev > 0) st.exits++; if (x.now > 0) st.holders++; st.netW += x.dw; });
    });
    const withData = Object.values(perScheme).filter(Boolean);
    return { perScheme, stock, schemes: withData.length, from: withData.map(x => x.from).sort()[0] || null, to: withData.map(x => x.to).sort().pop() || null };
  });
}

/* ---------------- company ratios & scoring ---------------- */
function ratios(code) {
  return memo("rt|" + code, () => {
    const g = IX.fin[code], c = IX.co[code]; if (!g || g.length < 2 || !c) return null;
    const n = g.length, t = g[n - 1], p = g[n - 2], q = n >= 3 ? g[n - 3] : null;
    const avg = (a, b) => isNum(a) && isNum(b) ? (a + b) / 2 : (isNum(a) ? a : null);
    const avgNW = avg(t.net_worth, p.net_worth), avgTA = avg(t.total_assets, p.total_assets);
    const shares = c.shares_cr || t.shares_cr, eps = ratio(t.pat, shares);
    const o = { eps, bvps: ratio(t.net_worth, shares), roe: ratio(t.pat, avgNW) != null ? t.pat / avgNW * 100 : null, roa: ratio(t.pat, avgTA) != null ? t.pat / avgTA * 100 : null,
      pe: isNum(c.price) && eps > 0 ? c.price / eps : null, pb: isNum(c.price) && t.net_worth > 0 ? c.price / (t.net_worth / shares) : null,
      rev_cagr3: n >= 4 ? growth(t.revenue, g[n - 4].revenue, 3) : null, pat_cagr3: n >= 4 ? growth(t.pat, g[n - 4].pat, 3) : null,
      rev_cagr5: n >= 6 ? growth(t.revenue, g[n - 6].revenue, 5) : null, rev_growth1: growth(t.revenue, p.revenue, 1), pat_growth1: growth(t.pat, p.pat, 1),
      pat_margin: ratio(t.pat, t.revenue) != null ? t.pat / t.revenue * 100 : null,
      div_yield: isNum(t.dividend_ps) && c.price ? t.dividend_ps / c.price * 100 : null, payout: isNum(t.dividend_ps) && t.pat > 0 && shares ? t.dividend_ps * shares / t.pat * 100 : null,
      earn_yield: isNum(eps) && c.price ? eps / c.price * 100 : null, fy: t.fy, years: n };
    if (!c.is_financial) {
      const ebit = isNum(t.pbt) && isNum(t.interest) ? t.pbt + t.interest : null;
      const ce = (x) => isNum(x.net_worth) ? x.net_worth + (x.total_debt || 0) : null;
      const avgCE = avg(ce(t), ce(p));
      Object.assign(o, { roce: ratio(ebit, avgCE) != null ? ebit / avgCE * 100 : null, de: isNum(t.total_debt) && t.net_worth > 0 ? t.total_debt / t.net_worth : null,
        int_cover: isNum(ebit) && t.interest > 0 ? ebit / t.interest : null, current_ratio: ratio(t.current_assets, t.current_liabilities),
        ev_ebitda: isNum(c.mcap_cr) && t.ebitda > 0 ? (c.mcap_cr + (t.total_debt || 0) - (t.cash_eq || 0)) / t.ebitda : null,
        fcf: isNum(t.cfo) && isNum(t.capex) ? t.cfo - t.capex : null, fcf_yield: isNum(t.cfo) && isNum(t.capex) && c.mcap_cr ? (t.cfo - t.capex) / c.mcap_cr * 100 : null,
        cfo_pat: t.pat > 0 ? ratio(t.cfo, t.pat) : null, ebitda_margin: ratio(t.ebitda, t.revenue) != null ? t.ebitda / t.revenue * 100 : null,
        dupont_margin: o.pat_margin, dupont_turnover: ratio(t.revenue, avgTA), dupont_leverage: ratio(avgTA, avgNW) });
      if (q) {
        const roaT = ratio(t.pat, p.total_assets), roaP = ratio(p.pat, q.total_assets), cmp = (a, b, f) => isNum(a) && isNum(b) ? f(a, b) : null;
        const F = [
          ["Positive ROA", isNum(roaT) ? roaT > 0 : null], ["Positive operating cash flow", isNum(t.cfo) ? t.cfo > 0 : null], ["ROA improved", cmp(roaT, roaP, (a, b) => a > b)],
          ["Cash flow exceeds profit (quality)", cmp(t.cfo, t.pat, (a, b) => a > b)],
          ["Leverage fell or unchanged", cmp(ratio(t.total_debt || 0, t.total_assets), ratio(p.total_debt || 0, p.total_assets), (a, b) => a <= b)],
          ["Current ratio improved", cmp(ratio(t.current_assets, t.current_liabilities), ratio(p.current_assets, p.current_liabilities), (a, b) => a > b)],
          ["No share dilution", cmp(t.shares_cr, p.shares_cr, (a, b) => a <= b * 1.001)], ["Operating margin improved", cmp(ratio(t.ebitda, t.revenue), ratio(p.ebitda, p.revenue), (a, b) => a > b)],
          ["Asset turnover improved", cmp(ratio(t.revenue, p.total_assets), ratio(p.revenue, q.total_assets), (a, b) => a > b)],
        ];
        const known = F.filter(x => x[1] !== null);
        o.fscoreTests = F; o.fscoreKnown = known.length;
        o.fscore = known.length >= 7 ? known.filter(x => x[1]).length : null;
      }
    } else {
      ["gnpa_pct", "nnpa_pct", "car_pct", "nim_pct"].forEach(k => { if (isNum(t[k])) o[k.replace("_pct", "")] = +t[k]; });
    }
    return o;
  });
}
function sectorMedian(sector, key) {
  const v = DB.companies.filter(c => c.sector === sector).map(c => ratios(c.code)?.[key]).filter(x => isNum(x) && x > 0).sort((a, b) => a - b);
  if (v.length < 3) return null; const m = Math.floor(v.length / 2); return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}
function scorecard(code, member = "ALL") {
  return memo("sc|" + code + "|" + member + "|" + JSON.stringify(DB.policy), () => {
    const c = IX.co[code], r = ratios(code); if (!r) return null;
    const P = DB.policy, tests = [];
    const add = (k, v, pass, grp) => { if (pass !== null && pass !== undefined) tests.push({ k, v, pass, grp }); };
    const t = (v, f) => isNum(v) ? f(v) : null;
    const medPE = sectorMedian(c.sector, "pe"), medPB = sectorMedian(c.sector, "pb");
    if (!c.is_financial) {
      add("ROE ≥ 15%", fmtPct(r.roe), t(r.roe, v => v >= 15), "Profitability");
      add("ROCE ≥ 15%", fmtPct(r.roce), t(r.roce, v => v >= 15), "Profitability");
      add("Revenue CAGR (3Y) ≥ 10%", fmtPct(r.rev_cagr3), t(r.rev_cagr3, v => v >= 10), "Growth");
      add("PAT CAGR (3Y) ≥ 10%", fmtPct(r.pat_cagr3), t(r.pat_cagr3, v => v >= 10), "Growth");
      add("Debt / equity ≤ 1.0×", fmtX(r.de), t(r.de, v => v <= 1), "Balance sheet");
      add("Interest cover ≥ 3×", r.int_cover == null ? "No interest cost" : fmtX(r.int_cover), r.int_cover == null ? (isNum(r.roce) ? true : null) : r.int_cover >= 3, "Balance sheet");
      add("CFO / PAT ≥ 0.8×", fmtX(r.cfo_pat), t(r.cfo_pat, v => v >= 0.8), "Earnings quality");
      add("Piotroski F-score ≥ 6", isNum(r.fscore) ? r.fscore + " / 9" : "—", t(r.fscore, v => v >= 6), "Earnings quality");
      add(`P/E ≤ 1.2× sector median (${fmtN(medPE, 1)})`, isNum(r.pe) ? fmtN(r.pe, 1) : "Loss-making", r.pe == null ? false : medPE ? r.pe <= 1.2 * medPE : null, "Valuation");
    } else {
      add("ROE ≥ 14%", fmtPct(r.roe), t(r.roe, v => v >= 14), "Profitability");
      if (/bank/i.test(c.industry || "")) add("ROA ≥ 1.2%", fmtPct(r.roa, 2), t(r.roa, v => v >= 1.2), "Profitability");
      add("PAT CAGR (3Y) ≥ 12%", fmtPct(r.pat_cagr3), t(r.pat_cagr3, v => v >= 12), "Growth");
      add("Gross NPA ≤ 3%", fmtPct(r.gnpa, 2), t(r.gnpa, v => v <= 3), "Asset quality");
      add("Net NPA ≤ 1%", fmtPct(r.nnpa, 2), t(r.nnpa, v => v <= 1), "Asset quality");
      add("Capital adequacy ≥ 15%", fmtPct(r.car), t(r.car, v => v >= 15), "Balance sheet");
      add(`P/B ≤ 1.2× sector median (${fmtN(medPB, 2)})`, fmtN(r.pb, 2), isNum(r.pb) && medPB ? r.pb <= 1.2 * medPB : null, "Valuation");
    }
    add(`Promoter pledge ≤ ${P.max_pledge_pct}%`, fmtPct(c.pledge_pct), t(c.pledge_pct, v => v <= P.max_pledge_pct), "Governance");
    if (!tests.length) return null;
    const passed = tests.filter(x => x.pass).length, score = passed / tests.length * 100;
    // A lender cannot be judged without asset quality and capital: missing GNPA / NNPA / CAR means no verdict.
    const missingCore = c.is_financial ? [["gnpa", "Gross NPA"], ["nnpa", "Net NPA"], ["car", "capital adequacy"]].filter(([k]) => !isNum(r[k])).map(x => x[1]) : [];
    const band = tests.length < 4 || missingCore.length ? "Insufficient data" : score >= 80 ? "Strong" : score >= 60 ? "Adequate" : "Weak";
    const ss = stockStats(code), mk = IX.mkt, bench1y = mk && isNum(mk[IX.T - 12]) ? mk[IX.T] / mk[IX.T - 12] - 1 : null;
    const act = activity().stock[code] || { adding: 0, reducing: 0, holders: 0, netW: 0 };
    const val = c.is_financial ? (medPB && isNum(r.pb) ? r.pb / medPB : null) : (medPE && isNum(r.pe) ? r.pe / medPE : null);
    const lt = lookThrough(member), row = lt.rows.find(x => x.code === code), cur = row ? row.total : 0;
    const L = P.max_single_stock_pct / 100, headroom = lt.eq ? (L * lt.eq - cur) / (1 - L) : null;
    const signals = [
      { k: "Fundamentals", v: `${passed}/${tests.length} tests passed`, s: band === "Strong" ? "ok" : band === "Adequate" ? "warn" : band === "Weak" ? "crit" : "neutral" },
      { k: "Valuation vs sector", v: isNum(val) ? `${fmtN(val, 2)}× sector median ${c.is_financial ? "P/B" : "P/E"}` : "Not compared (fewer than three sector peers with data)", s: !isNum(val) ? "neutral" : val <= 1.1 ? "ok" : val <= 1.5 ? "warn" : "crit" },
      { k: `Price momentum (1Y vs ${mktName()})`, v: ss && isNum(ss.r1y) ? `${fmtPct(ss.r1y * 100)} vs ${isNum(bench1y) ? fmtPct(bench1y * 100) : "—"}` : "—", s: ss && isNum(ss.r1y) && isNum(bench1y) ? (ss.r1y >= bench1y ? "ok" : "warn") : "neutral" },
      { k: "Fund-manager activity (latest month)", v: activity().schemes ? `${act.adding} adding · ${act.reducing} reducing` : "Needs two months of AMC files", s: act.adding > act.reducing ? "ok" : act.adding < act.reducing ? "warn" : "neutral" },
      { k: "Concentration headroom", v: isNum(headroom) ? (headroom > 0 ? fmtCr(headroom) : "None") : "—", s: !isNum(headroom) ? "neutral" : headroom > 0 ? "ok" : "crit" },
    ];
    let decision;
    // Screening outcomes, not advice: each label states what the tests found; the investment committee decides.
    if (isNum(headroom) && headroom <= 0) decision = { s: "crit", t: "Policy limit breached", d: `Look-through exposure is already ${fmtPct(row.pct, 2)}, above the ${fmtPct(P.max_single_stock_pct)} single-stock limit in the investment policy. A purchase would widen the breach.` };
    else if (band === "Insufficient data") decision = { s: "neutral", t: "Insufficient data", d: missingCore.length ? `A lender is screened on asset quality and capital; ${missingCore.join(", ")} ${missingCore.length > 1 ? "are" : "is"} not in the data (enter from the annual report).` : "Too few tests could be run on the available financial data." };
    else if (band === "Weak") decision = { s: "crit", t: "Fails screen", d: "The company passes fewer than 60% of the fundamental tests it has data for. See the failed tests below." };
    else if (band === "Strong" && isNum(val) && val <= 1.15) decision = { s: "ok", t: "Passes screen", d: `Fundamentals clear the screen and valuation is within 1.15× the sector median.${isNum(headroom) ? ` Policy headroom: ${fmtCr(headroom)} before the ${fmtPct(P.max_single_stock_pct)} single-stock limit.` : ""}` };
    else if (band === "Strong") decision = { s: "warn", t: "Passes screen · valuation above peers", d: isNum(val) ? `Strong fundamentals; ${c.is_financial ? "P/B" : "P/E"} is ${fmtN(val, 2)}× the sector median.` : "Strong fundamentals, but valuation could not be compared with sector peers." };
    else decision = { s: "warn", t: "Mixed result", d: "Fundamentals are mixed. See the failed tests below." };
    return { c, r, tests, passed, score, band, medPE, medPB, val, signals, decision, cur, pctNow: row ? row.pct : 0, headroom, ss, act };
  });
}
function whatIfBuy(code, amount, member = "ALL") {
  const before = lookThrough(member), after = lookThrough(member, { [code]: amount });
  const cb = concentration(before), ca = concentration(after);
  const sec = coField(code, "sector"), sb = groupBy(before, "sector").find(x => x.key === sec), sa = groupBy(after, "sector").find(x => x.key === sec);
  const rb = before.rows.find(r => r.code === code), ra = after.rows.find(r => r.code === code);
  return { before: { pct: rb ? rb.pct : 0, sector: sb ? sb.pct : 0, hhi: cb.hhi, top10: cb.top10 }, after: { pct: ra.pct, sector: sa.pct, hhi: ca.hhi, top10: ca.top10 } };
}

/* ---------------- policy alerts ---------------- */
function alerts(member = "ALL") {
  return memo("al|" + member + JSON.stringify(DB.policy), () => {
    const P = DB.policy, lt = lookThrough(member), con = concentration(lt), out = [];
    if (!lt.rows.length) return out;
    lt.rows.forEach(r => {
      const nm = IX.co[r.code]?.name || r.code;
      if (r.pct > P.max_single_stock_pct) out.push({ sev: "crit", kind: "Single stock", title: `${nm} is ${fmtPct(r.pct, 2)} of look-through equity`, detail: `Limit ${fmtPct(P.max_single_stock_pct)}. Direct ${fmtCr(r.direct)}, through funds ${fmtCr(r.viaMF)}. Excess ${fmtCr(lt.eq * (r.pct - P.max_single_stock_pct) / 100)}.`, go: ["company", r.code] });
      else if (r.pct > P.max_single_stock_pct * 0.8) out.push({ sev: "warn", kind: "Single stock", title: `${nm} at ${fmtPct(r.pct, 2)}, close to the limit`, detail: `Headroom ${fmtCr(lt.eq * (P.max_single_stock_pct - r.pct) / 100)}.`, go: ["company", r.code] });
    });
    groupBy(lt, "sector").forEach(s => {
      if (s.pct > P.max_sector_pct) out.push({ sev: "crit", kind: "Sector", title: `${s.key} is ${fmtPct(s.pct)} of equity`, detail: `Limit ${fmtPct(P.max_sector_pct)}. Excess ${fmtCr(lt.eq * (s.pct - P.max_sector_pct) / 100)}.`, go: ["concentration"] });
      else if (s.pct > P.max_sector_pct * 0.9) out.push({ sev: "warn", kind: "Sector", title: `${s.key} at ${fmtPct(s.pct)}, close to the limit`, detail: `Limit ${fmtPct(P.max_sector_pct)}.`, go: ["concentration"] });
    });
    if (con.top10 > P.max_top10_pct) out.push({ sev: "crit", kind: "Top 10", title: `Top 10 stocks hold ${fmtPct(con.top10)} of equity`, detail: `Limit ${fmtPct(P.max_top10_pct)}.`, go: ["concentration"] });
    else if (con.top10 > P.max_top10_pct * 0.95) out.push({ sev: "warn", kind: "Top 10", title: `Top 10 stocks hold ${fmtPct(con.top10)} of equity`, detail: `Close to the ${fmtPct(P.max_top10_pct)} limit.`, go: ["concentration"] });
    if (con.hhi > P.max_hhi) out.push({ sev: "crit", kind: "HHI", title: `HHI ${con.hhi.toFixed(4)} above ${P.max_hhi}`, detail: `Effective number of stocks ${con.effN.toFixed(1)}.`, go: ["concentration"] });
    const held = heldSchemes(member).filter(s => latestPort()[s]), pairs = [];
    held.forEach((a, i) => held.slice(i + 1).forEach(b => { const o = overlap(a, b).overlap; if (o > P.max_pair_overlap_pct) pairs.push({ a, b, o }); }));
    pairs.sort((x, y) => y.o - x.o).slice(0, 3).forEach(p => out.push({ sev: "warn", kind: "Fund overlap", title: `${IX.sch[p.a].name} and ${IX.sch[p.b].name} overlap ${fmtPct(p.o)}`, detail: `Limit ${fmtPct(P.max_pair_overlap_pct)}. Two expense ratios are being paid for largely the same stocks.`, go: ["overlap", p.a + "|" + p.b] }));
    if (pairs.length > 3) out.push({ sev: "warn", kind: "Fund overlap", title: `${pairs.length - 3} more held fund pairs overlap above ${fmtPct(P.max_pair_overlap_pct)}`, detail: `${pairs.length} of ${held.length * (held.length - 1) / 2} held pairs are above the limit.`, go: ["overlap"] });
    const wter = weightedTer(member);
    if (isNum(wter) && wter > P.max_weighted_ter_pct) out.push({ sev: "warn", kind: "Cost", title: `Weighted expense ratio ${fmtPct(wter, 2)} above ${fmtPct(P.max_weighted_ter_pct, 2)}`, detail: "Regular-plan holdings raise cost.", go: ["funds"] });
    const sv = directSaving(member);
    if (sv > 0) out.push({ sev: "warn", kind: "Cost", title: `Regular-plan units cost about ${fmtAuto(sv)} a year more than Direct`, detail: "Estimated from the gap between Regular and Direct NAV returns over the last 12 months.", go: ["funds"] });
    const pb = portBeta(lt); if (isNum(pb) && pb > P.max_portfolio_beta) out.push({ sev: "warn", kind: "Market risk", title: `Equity beta ${fmtN(pb, 2)} above ${P.max_portfolio_beta}`, detail: "The equity book moves more than the market.", go: ["stress"] });
    lt.rows.forEach(r => { const c = IX.co[r.code]; if (c && isNum(c.pledge_pct) && c.pledge_pct > P.max_pledge_pct) out.push({ sev: "warn", kind: "Governance", title: `${c.name}: ${fmtPct(c.pledge_pct)} of promoter holding pledged`, detail: `Family exposure ${fmtCr(r.total)}. Limit ${fmtPct(P.max_pledge_pct)}.`, go: ["company", r.code] }); });
    if (lt.unmapped > 0) out.push({ sev: "warn", kind: "Data", title: `${fmtCr(lt.unmapped)} of fund holdings not looked through`, detail: `No AMC portfolio file applied for ${lt.unmappedSchemes.map(s => IX.sch[s].name).join(", ")}.`, go: ["data"] });
    const hb = holdingsBasis(member);
    if (hb.behind.length) out.push({ sev: "warn", kind: "Data", title: `Fund holdings are from ${hb.behindDates.map(fmtDate).join(" / ")}, prices from ${fmtDate(hb.asOn)}`, detail: `${hb.behind.length} of ${hb.held.length} held funds are looked through on an earlier month's disclosure. Add the new AMC files when they are published (within about 10 days of month-end).`, go: ["data"] });
    const rank = { crit: 0, warn: 1 };
    return out.sort((a, b) => rank[a.sev] - rank[b.sev]);
  });
}
function directSaving(member = "ALL") { return holdings(member).filter(h => h.asset_type === "MF" && h.plan === "Regular").reduce((s, h) => { const g = impliedGap(h.instrument); return s + (isNum(g) ? h.value * g / 100 : 0); }, 0); }
function weightedTer(member = "ALL") { const H = holdings(member).filter(h => h.asset_type === "MF"); if (!H.length || H.some(h => terOf(h) == null)) return null; const v = H.reduce((s, h) => s + h.value, 0); return H.reduce((s, h) => s + h.value * terOf(h), 0) / v; }

/* ---------------- tax (indicative) ---------------- */
function taxView(member) {
  const P = DB.policy, H = holdings(member), R = realised(member).filter(r => r.sell_date >= P.tax_year_start);
  const rST = R.filter(r => r.term === "ST").reduce((s, r) => s + r.gain, 0), rLT = R.filter(r => r.term === "LT").reduce((s, r) => s + r.gain, 0);
  const uST = H.reduce((s, h) => s + h.st_gain, 0), uLT = H.reduce((s, h) => s + h.lt_gain, 0);
  // "If sold" covers only units that can be sold: ELSS units still in their 3-year lock-in are excluded.
  const lockedST = H.reduce((s, h) => s + h.locked_st, 0), lockedLT = H.reduce((s, h) => s + h.locked_lt, 0), lockedValue = H.reduce((s, h) => s + h.locked_value, 0);
  let tST = uST - lockedST + rST, tLT = uLT - lockedLT + rLT; if (tST < 0) { tLT += tST; tST = 0; }
  const taxable = Math.max(0, tLT - P.ltcg_exemption);
  // Realised gains net of the mandatory set-off of realised losses.
  const netRealisedLT = rLT + Math.min(0, rST);
  // Statutory exemption still unused (never above the exemption itself).
  const exemptLeft = Math.max(0, P.ltcg_exemption - Math.max(0, netRealisedLT));
  // Long-term gain that could still be realised tax-free: the unused exemption PLUS any realised losses that the
  // new gain would first be set off against. This can exceed the exemption.
  const room = Math.max(0, P.ltcg_exemption - netRealisedLT);
  return { rST, rLT, uST, uLT, lockedST, lockedLT, lockedValue, taxIfSold: tST * P.stcg_rate_pct / 100 + taxable * P.ltcg_rate_pct / 100, harvest: Math.min(room, Math.max(0, uLT - lockedLT)), exemptLeft };
}

/* ---------------- stress testing ---------------- */
function stress(member, sc) {
  const lt = lookThrough(member), mk = IX.mkt, rows = lt.rows.map(r => {
    const c = IX.co[r.code] || {}, b = stockStats(r.code)?.beta ?? 1; let shock = 0;
    if (sc.type === "market") shock = b * sc.market;
    if (sc.type === "sector") shock = c.sector === sc.sector ? sc.shock : 0;
    if (sc.type === "stock") shock = r.code === sc.code ? sc.shock : 0;
    if (sc.type === "custom") shock = b * sc.market + (c.sector === sc.sector ? sc.shock : 0);
    if (sc.type === "hist") { const p = IX.px[r.code]; shock = p && isNum(p[sc.t0]) && isNum(p[sc.t1]) ? p[sc.t1] / p[sc.t0] - 1 : (mk ? mk[sc.t1] / mk[sc.t0] - 1 : 0); }
    shock = Math.max(-1, shock);  // a share cannot lose more than its whole value (beta 1.3 x -100% is still -100%)
    return { code: r.code, exp: r.total, shock, loss: r.total * shock };
  });
  // Funds without a portfolio file still move with the market: treated as fully equity at beta 1 (an assumption,
  // shown as its own row). Their sectors are unknown, so sector and single-stock shocks leave them unchanged.
  if (lt.unmapped > 0) {
    const shock = Math.max(-1, sc.type === "market" || sc.type === "custom" ? sc.market : sc.type === "hist" && mk ? mk[sc.t1] / mk[sc.t0] - 1 : 0);
    rows.push({ code: "__UNMAPPED__", exp: lt.unmapped, shock, loss: lt.unmapped * shock, assumption: true });
  }
  const loss = rows.reduce((s, r) => s + r.loss, 0);
  const eqBase = lt.eq + lt.unmapped;  // stressed equity includes the funds not looked through
  return { rows: rows.sort((a, b) => a.loss - b.loss), loss, pctEq: eqBase ? loss / eqBase * 100 : 0, pctTotal: lt.total ? loss / lt.total * 100 : 0, lt };
}

/* ---------------- consolidation simulator ---------------- */
function simulateSwitch(member, fromSid, toSid, fraction = 1) {
  const H = holdings(member), from = H.filter(h => h.asset_type === "MF" && h.instrument === fromSid);
  // Only units that can be redeemed today are switched: ELSS units inside their 3-year lock-in stay put.
  const locked = from.reduce((s, h) => s + h.locked_value, 0);
  const amount = from.reduce((s, h) => s + h.value - h.locked_value, 0) * fraction;
  const before = lookThrough(member), port = latestPort();
  const shift = {};
  (port[fromSid] || []).forEach(p => shift[p.code] = (shift[p.code] || 0) - amount * p.w / 100);
  (port[toSid] || []).forEach(p => shift[p.code] = (shift[p.code] || 0) + amount * p.w / 100);
  const m = {}; before.rows.forEach(r => m[r.code] = r.total);
  Object.entries(shift).forEach(([c, v]) => m[c] = (m[c] || 0) + v);
  const eq = Object.values(m).reduce((s, v) => s + Math.max(0, v), 0), w = Object.values(m).map(v => Math.max(0, v) / eq).sort((a, b) => b - a);
  const hhi = w.reduce((s, x) => s + x * x, 0);
  // Cost saving needs the expense ratios of BOTH funds. Without them it is "not available", never a fallback that
  // ignores the destination fund (the old Regular-Direct-gap fallback gave the same saving for every target).
  const sellShare = h => h.value ? (h.value - h.locked_value) / h.value * fraction : 0;
  const terFrom = from.every(h => terOf(h) != null) ? from.reduce((s, h) => s + h.value * sellShare(h) * terOf(h) / 100, 0) : null;
  const terTo = isNum(IX.sch[toSid].ter_direct) ? amount * IX.sch[toSid].ter_direct / 100 : null;
  const terSaving = isNum(terFrom) && isNum(terTo) ? terFrom - terTo : null;
  let gainLT = 0, gainST = 0;
  from.forEach(h => { gainLT += (h.lt_gain - h.locked_lt) * fraction; gainST += (h.st_gain - h.locked_st) * fraction; });
  const P = DB.policy, tax = Math.max(0, gainST) * P.stcg_rate_pct / 100 + Math.max(0, gainLT + Math.min(0, gainST) - P.ltcg_exemption) * P.ltcg_rate_pct / 100;
  const cb = concentration(before);
  const hb = heldSchemes(member), remaining = hb.filter(s => s !== fromSid || fraction < 1).concat(hb.includes(toSid) ? [] : [toSid]);
  const maxOvOf = list => { let mx = 0; list.forEach((a, i) => list.slice(i + 1).forEach(b => { const o = overlap(a, b).overlap; if (isNum(o)) mx = Math.max(mx, o); })); return mx; };
  return { amount, locked, terSaving, terBasis: isNum(terSaving) ? "TER" : "expense ratios not loaded", gainLT, gainST, tax,
    before: { hhi: cb.hhi, effN: cb.effN, top10: cb.top10, maxOv: maxOvOf(hb), funds: hb.length },
    after: { hhi, effN: 1 / hhi, top10: w.slice(0, 10).reduce((s, x) => s + x, 0) * 100, maxOv: maxOvOf([...new Set(remaining)]), funds: new Set(remaining).size } };
}

/* ---------------- rebalancing ---------------- */
const ALLOC_MIN_COVERAGE = 90;
function allocation(member) {
  const lt = lookThrough(member), P = DB.policy, caps = groupBy(lt, "cap");
  const tgt = { Large: P.target_large_pct, Mid: P.target_mid_pct, Small: P.target_small_pct };
  const other = caps.filter(x => !(x.key in tgt)).reduce((s, x) => s + x.pct, 0);
  const rows = ["Large", "Mid", "Small"].map(k => { const a = caps.find(x => x.key === k)?.pct || 0; return { key: k, actual: a, target: tgt[k], drift: a - tgt[k], move: (tgt[k] - a) / 100 * lt.eq, status: Math.abs(a - tgt[k]) > P.band_pct ? "crit" : Math.abs(a - tgt[k]) > P.band_pct * 0.6 ? "warn" : "ok" }; });
  rows.other = other;
  rows.parts = caps.filter(x => !(x.key in tgt)).map(x => ({ key: x.key, pct: x.pct, amt: x.v }));
  rows.coverage = 100 - other;  // share of look-through equity whose market-cap class is known
  // Below 90% coverage the drift and the amounts to move would be driven by the missing data, so none are given.
  if (rows.coverage < ALLOC_MIN_COVERAGE) rows.forEach(r => { r.status = "neutral"; r.move = null; });
  return rows;
}

/* ---------------- screener metrics ---------------- */
function screenerRows(member = "ALL") {
  return memo("scr|" + member + JSON.stringify(DB.policy), () => {
    const lt = lookThrough(member), act = activity().stock;
    return DB.companies.filter(c => IX.fin[c.code] && IX.fin[c.code].length >= 2).map(c => {
      const r = ratios(c.code) || {}, ss = stockStats(c.code) || {}, sc = scorecard(c.code, member), row = lt.rows.find(x => x.code === c.code), a = act[c.code] || {};
      return { code: c.code, name: c.name, sector: c.sector, cap: c.cap, price: c.price, mcap: c.mcap_cr, r1y: isNum(ss.r1y) ? ss.r1y * 100 : null, cagr3: isNum(ss.cagr3) ? ss.cagr3 * 100 : null, beta: ss.beta ?? null, offHigh: isNum(ss.offHigh) ? ss.offHigh * 100 : null,
        pe: r.pe ?? null, pb: r.pb ?? null, ev_ebitda: r.ev_ebitda ?? null, div_yield: r.div_yield ?? null, roe: r.roe ?? null, roce: r.roce ?? null, de: r.de ?? null, rev_cagr3: r.rev_cagr3 ?? null, pat_cagr3: r.pat_cagr3 ?? null,
        fscore: r.fscore ?? null, score: sc ? sc.score : null, band: sc ? sc.band : "Insufficient data", decision: sc ? sc.decision.t : "Insufficient data", decisionS: sc ? sc.decision.s : "neutral", holders: a.holders || 0, mfNet: (a.adding || 0) - (a.reducing || 0),
        exposure: row ? row.total : 0, expPct: row ? row.pct : 0, pledge: c.pledge_pct, is_financial: c.is_financial, fy: r.fy };
    });
  });
}
