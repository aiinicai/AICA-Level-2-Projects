// @ts-nocheck
/* ------------------------------------------------------------ 1. UTILITIES */
export var MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

export function toNum(v, d) { var n = parseFloat(v); return isFinite(n) ? n : (d === undefined ? 0 : d); }
export function clampInt(v, lo, hi) { var n = Math.round(toNum(v, lo)); return Math.min(Math.max(n, lo), hi); }
export function dim(y, m) { return new Date(y, m + 1, 0).getDate(); }

export function parseISO(s) {
  if (!s || typeof s !== "string") return null;
  var p = s.split("-"); if (p.length !== 3) return null;
  var y = parseInt(p[0], 10), m = parseInt(p[1], 10), d = parseInt(p[2], 10);
  if (!isFinite(y) || !isFinite(m) || !isFinite(d)) return null;
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  return { y: y, m: m - 1, d: d };
}
export function toISO(o) {
  if (!o) return "";
  return o.y + "-" + String(o.m + 1).padStart(2, "0") + "-" + String(o.d).padStart(2, "0");
}
export function addMonths(o, k) {
  if (!o) return null;
  var t = o.y * 12 + o.m + k, y = Math.floor(t / 12), m = ((t % 12) + 12) % 12;
  return { y: y, m: m, d: Math.min(o.d, dim(y, m)) };
}
export function addDays(o, k) {
  if (!o) return null;
  var d = new Date(o.y, o.m, o.d); d.setDate(d.getDate() + k);
  return { y: d.getFullYear(), m: d.getMonth(), d: d.getDate() };
}
export function cmpD(a, b) { if (!a || !b) return 0; return (a.y - b.y) || (a.m - b.m) || (a.d - b.d); }
export function serial(o) { return o ? Math.floor(Date.UTC(o.y, o.m, o.d) / 86400000) : 0; }
export function dayDiff(a, b) { return serial(b) - serial(a); }
export function monthsBetween(a, b) {
  if (!a || !b) return 0;
  return (b.y - a.y) * 12 + (b.m - a.m) + (b.d >= a.d ? 0 : -1);
}
export function fmtDate(o) { return o ? String(o.d).padStart(2, "0") + "-" + MON[o.m] + "-" + o.y : "\u2014"; }
export function fmtMon(o) { return o ? MON[o.m] + "-" + String(o.y).slice(2) : "\u2014"; }

export function fyKey(o, basis) {
  if (!o) return "\u2014";
  if (basis === "dec") return "CY " + o.y;
  var s = o.m >= 3 ? o.y : o.y - 1;
  return "FY " + s + "-" + String((s + 1) % 100).padStart(2, "0");
}
export function fyStart(o, basis) {
  if (!o) return null;
  if (basis === "dec") return { y: o.y, m: 0, d: 1 };
  var s = o.m >= 3 ? o.y : o.y - 1;
  return { y: s, m: 3, d: 1 };
}
export function fyEnd(o, basis) {
  if (!o) return null;
  if (basis === "dec") return { y: o.y, m: 11, d: 31 };
  var s = o.m >= 3 ? o.y : o.y - 1;
  return { y: s + 1, m: 2, d: 31 };
}
export function quarterOf(o, basis) {
  if (!o) return null;
  var qn, sm;
  if (basis === "dec") { qn = Math.floor(o.m / 3) + 1; sm = (qn - 1) * 3; }
  else { qn = Math.floor(((o.m - 3 + 12) % 12) / 3) + 1; sm = (3 + (qn - 1) * 3) % 12; }
  var start;
  if (basis === "dec") start = { y: o.y, m: sm, d: 1 };
  else { var fys = fyStart(o, basis).y; start = { y: qn === 4 ? fys + 1 : fys, m: sm, d: 1 }; }
  var em = addMonths({ y: start.y, m: start.m, d: 1 }, 2);
  var end = { y: em.y, m: em.m, d: dim(em.y, em.m) };
  return { qn: qn, fy: fyKey(o, basis), label: "Q" + qn + " " + fyKey(o, basis),
           start: start, end: end, basis: basis };
}
export function quarterKey(q) { return q ? q.fy + "|Q" + q.qn : ""; }
export function nextQuarter(q) { return quarterOf(addDays(q.end, 1), q.basis); }

export var NF = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export function money(v) { var n = toNum(v, 0); return NF.format(Math.abs(n) < 0.005 ? 0 : n); }
export function pctS(v, dp) { return (toNum(v, 0) * 100).toFixed(dp === undefined ? 4 : dp) + "%"; }
export function uid() { return "LSE-" + Math.random().toString(36).slice(2, 8).toUpperCase(); }
export function r2(v) { return Math.round(toNum(v, 0) * 100) / 100; }
/* Signed presentation: brackets for negatives */
export function br(v) { var n = toNum(v, 0); return n < -0.005 ? "(" + money(-n) + ")" : money(n); }

/* ------------------------------------------------- 2. PERSISTENCE */
export var StoreEngine = "IndexedDB";
export var Store = (function () {
  var DB = "indas116v4", ST = "leases", LS = "indas116v4_leases", dbp = null;
  function open() {
    if (dbp) return dbp;
    dbp = new Promise(function (res, rej) {
      if (typeof indexedDB === "undefined") { rej(new Error("no-idb")); return; }
      var r; try { r = indexedDB.open(DB, 1); } catch (e) { rej(e); return; }
      r.onupgradeneeded = function () {
        var db = r.result;
        if (!db.objectStoreNames.contains(ST)) db.createObjectStore(ST, { keyPath: "id" });
      };
      r.onsuccess = function () { res(r.result); };
      r.onerror = function () { rej(r.error || new Error("idb-open")); };
    });
    return dbp;
  }
  function tx(mode, fn) {
    return open().then(function (db) {
      return new Promise(function (res, rej) {
        var t = db.transaction(ST, mode), rq = fn(t.objectStore(ST));
        t.oncomplete = function () { res(rq ? rq.result : null); };
        t.onerror = function () { rej(t.error); };
        t.onabort = function () { rej(t.error); };
      });
    });
  }
  function lsAll() { try { return JSON.parse(localStorage.getItem(LS) || "[]"); } catch (e) { return []; } }
  function lsSet(a) { try { localStorage.setItem(LS, JSON.stringify(a)); } catch (e) {} }
  return {
    all: function () {
      return tx("readonly", function (s) { return s.getAll(); })
        .then(function (r) { return r || []; })
        .catch(function () { StoreEngine = "localStorage"; return lsAll(); });
    },
    put: function (rec) {
      return tx("readwrite", function (s) { return s.put(rec); })
        .catch(function () {
          StoreEngine = "localStorage";
          var a = lsAll().filter(function (x) { return x.id !== rec.id; });
          a.push(rec); lsSet(a);
        });
    },
    del: function (id) {
      return tx("readwrite", function (s) { return s.delete(id); })
        .catch(function () { lsSet(lsAll().filter(function (x) { return x.id !== id; })); });
    }
  };
})();

/* ------------------------------------------------- 3. LEASE ENGINE */
export function periodicRate(annualPct, basis) {
  var a = toNum(annualPct) / 100;
  return basis === "effective" ? Math.pow(1 + a, 1 / 12) - 1 : a / 12;
}
export function buildPayments(cfg) {
  var n = clampInt(cfg.termMonths, 1, 600);
  var base = toNum(cfg.basePayment), freq = clampInt(cfg.escFreq, 1, 600);
  var out = [], k, steps;
  for (k = 1; k <= n; k++) {
    steps = Math.floor((k - 1) / freq);
    if (cfg.escMode === "percent") out.push(base * Math.pow(1 + toNum(cfg.escPct) / 100, steps));
    else if (cfg.escMode === "amount") out.push(base + toNum(cfg.escAmt) * steps);
    else out.push(base);
  }
  var rf = Math.min(Math.max(Math.round(toNum(cfg.rentFreeMonths)), 0), n - 1);
  if (rf > 0) {
    if (cfg.rentFreePos === "end") { for (k = n - rf; k < n; k++) out[k] = 0; }
    else { for (k = 0; k < rf; k++) out[k] = 0; }
  }
  String(cfg.rentFreeList || "").split(",").forEach(function (s) {
    var v = parseInt(String(s).trim(), 10);
    if (isFinite(v) && v >= 1 && v <= n) out[v - 1] = 0;
  });
  var ov = cfg.overrides || {};
  Object.keys(ov).forEach(function (key) {
    var i = parseInt(key, 10) - 1, val = ov[key];
    if (i >= 0 && i < n && val !== "" && val !== null && val !== undefined && isFinite(Number(val))) out[i] = Number(val);
  });
  return out;
}
export function applyMods(payments, mods) {
  var arr = payments.slice();
  var list = (mods || []).filter(function (m) { return m.enabled !== false; })
    .sort(function (a, b) { return toNum(a.month, 1) - toNum(b.month, 1); });
  list.forEach(function (m) {
    var st = Math.min(Math.max(Math.round(toNum(m.month, 1)), 1), arr.length);
    var rem = Math.max(0, Math.round(toNum(m.newTerm, arr.length - st + 1)));
    var amt = (m.newPayment === "" || m.newPayment === null || m.newPayment === undefined)
      ? (arr[st - 1] || 0) : toNum(m.newPayment);
    var freq = Math.max(1, Math.round(toNum(m.escFreq, 12))), esc = toNum(m.escPct);
    var tail = [], j;
    for (j = 0; j < rem; j++) tail.push(amt * Math.pow(1 + esc / 100, Math.floor(j / freq)));
    arr = arr.slice(0, st - 1).concat(tail);
  });
  return arr.length ? arr : [0];
}
export function pvFrom(payments, p, i, advance) {
  var pv = 0, k, t;
  for (k = p; k <= payments.length; k++) {
    t = advance ? (k - p) : (k - p + 1);
    pv += (i === 0) ? payments[k - 1] : payments[k - 1] / Math.pow(1 + i, t);
  }
  return pv;
}

/* ---- 3.4 Ind AS 12 deferred tax layer ---- */
export function dtRateAt(cfg, d) {
  var r = toNum(cfg.dtRate, 25.168);
  var sch = (cfg.dtRateSchedule || []).filter(function (s) {
    return s.enabled !== false && parseISO(s.from) && isFinite(parseFloat(s.rate));
  }).sort(function (a, b) { return cmpD(parseISO(a.from), parseISO(b.from)); });
  sch.forEach(function (s) { if (cmpD(parseISO(s.from), d) <= 0) r = toNum(s.rate, r); });
  return r / 100;
}

/*
  Sign convention used throughout.
  Temporary difference = carrying amount less tax base, per Ind AS 12.5.
  For the right-of-use asset a positive difference is TAXABLE, giving a liability.
  For the lease liability and the restoration provision a positive difference is
  DEDUCTIBLE, giving an asset.
  net is positive when the overall position is a deferred tax ASSET.
  A positive movement is therefore deferred tax INCOME, a credit in profit or loss.
*/
export function buildDeferredTax(res, cfg) {
  if (!cfg.dtOn) return { on: false, rows: [], day1: null };

  var treat = cfg.dtTreatment || "rentAccrual";      /* rentAccrual | taxDep | none */
  var incAro = cfg.dtIncludeAro !== false;
  var restrict = !!cfg.dtRestrict;
  var ceiling = restrict ? Math.min(Math.max(toNum(cfg.dtRecognisePct, 100), 0), 100) / 100 : 1;

  function measure(rou, liab, aro, rouTB, liabTB, rate) {
    var tdRou = rou - rouTB;                         /* taxable when positive */
    var tdLiab = liab - liabTB;                      /* deductible when positive */
    var tdAro = incAro ? aro : 0;                    /* provision tax base is nil */
    var netTdFull = (tdLiab + tdAro) - tdRou;
    var netTd = netTdFull >= 0 ? netTdFull * ceiling : netTdFull;
    var dtl = tdRou * rate;
    var dta = (tdLiab + tdAro) * rate;
    var unrec = (netTdFull - netTd) * rate;
    if (unrec > 0) dta = dta - unrec;                /* restriction hits the asset side */
    return { tdRou: tdRou, tdLiab: tdLiab, tdAro: tdAro,
             netTdFull: netTdFull, netTd: netTd, rate: rate,
             dtl: dtl, dta: dta, net: netTd * rate, unrec: unrec };
  }

  var d1Rate = dtRateAt(cfg, res.meta.start);
  var d1RouTB = treat === "taxDep" ? res.rou0 : (treat === "none" ? res.rou0 : 0);
  var d1LiabTB = treat === "none" ? res.liabGross : 0;
  var m0 = measure(res.rou0, res.liabGross, res.aro.pv, d1RouTB, d1LiabTB, d1Rate);
  var day1 = Object.assign({ k: 0, date: res.meta.start, rou: res.rou0, liab: res.liabGross,
    aro: res.aro.pv, rouTB: d1RouTB, liabTB: d1LiabTB,
    open: 0, close: m0.net, move: m0.net, origination: m0.net, rateEffect: 0, taxDep: 0 }, m0);

  var rows = [], taxWdv = res.rou0;
  var prevTd = m0.netTd, prevRate = d1Rate, prevNet = m0.net;
  var peak = Math.max(m0.net, 0), trough = Math.min(m0.net, 0);
  var totRateEffect = 0, totOrig = m0.net, totUnrecMax = m0.unrec;

  res.rows.forEach(function (r) {
    var taxDep = 0;
    if (treat === "taxDep") {
      if (cfg.dtTaxDepMethod === "slm") {
        var life = Math.max(1, Math.round(toNum(cfg.dtTaxLifeMonths, res.N)));
        taxDep = Math.min(taxWdv, res.rou0 / life);
      } else {
        taxDep = taxWdv * (toNum(cfg.dtTaxDepRate) / 100 / 12);
      }
      taxWdv = Math.max(taxWdv - taxDep, 0);
    }
    var rouTB = treat === "taxDep" ? taxWdv : (treat === "none" ? r.nbv : 0);
    var liabTB = treat === "none" ? r.close : 0;
    var rate = dtRateAt(cfg, r.pEnd);
    var m = measure(r.nbv, r.close, r.aro, rouTB, liabTB, rate);

    var rateEffect = prevTd * (rate - prevRate);
    var origination = (m.netTd - prevTd) * rate;
    var move = m.net - prevNet;                      /* equals origination plus rateEffect */

    rows.push(Object.assign({
      k: r.k, date: r.pEnd, fy: r.fy, q: r.q,
      rou: r.nbv, liab: r.close, aro: r.aro, rouTB: rouTB, liabTB: liabTB, taxDep: taxDep,
      open: prevNet, close: m.net, move: move, origination: origination, rateEffect: rateEffect,
      rateChanged: Math.abs(rate - prevRate) > 1e-9
    }, m));

    peak = Math.max(peak, m.net); trough = Math.min(trough, m.net);
    totRateEffect += rateEffect; totOrig += origination;
    totUnrecMax = Math.max(totUnrecMax, m.unrec);
    prevTd = m.netTd; prevRate = rate; prevNet = m.net;
  });

  /* FY rollup for the deferred tax note */
  var order = [], map = {};
  rows.forEach(function (d) {
    if (!map[d.fy]) {
      map[d.fy] = { fy: d.fy, open: d.open, close: d.close, move: 0,
                    origination: 0, rateEffect: 0, dta: 0, dtl: 0, rate: d.rate };
      order.push(d.fy);
    }
    var g = map[d.fy];
    g.move += d.move; g.origination += d.origination; g.rateEffect += d.rateEffect;
    g.close = d.close; g.dta = d.dta; g.dtl = d.dtl; g.rate = d.rate;
  });
  /* day one recognition belongs to the first financial year */
  if (order.length) {
    var f = map[order[0]];
    f.open = 0; f.move += day1.move; f.origination += day1.origination;
  }
  var fyRows = order.map(function (k) { return map[k]; });

  var last = rows.length ? rows[rows.length - 1] : day1;
  return {
    on: true, treat: treat, incAro: incAro, restrict: restrict, ceiling: ceiling,
    day1: day1, rows: rows, fyRows: fyRows,
    day1Rate: d1Rate, finalRate: last.rate,
    peak: peak, trough: trough,
    closing: last.net, closingDta: last.dta, closingDtl: last.dtl,
    totals: { move: last.net, origination: totOrig, rateEffect: totRateEffect, unrecMax: totUnrecMax },
    rateChanges: rows.filter(function (d) { return d.rateChanged; }).length
  };
}

export function computeLease(cfg) {
  var start = parseISO(cfg.startDate);
  if (!start) throw new Error("Lease commencement date is missing or invalid.");
  var advance = cfg.timing === "begin";
  var fyBasis = cfg.fyBasis || "mar";
  var payments = applyMods(buildPayments(cfg), cfg.mods);
  var N = payments.length;
  var i0 = periodicRate(cfg.rate, cfg.rateBasis), i = i0;

  var pvGross = pvFrom(payments, 1, i, advance);
  var aroUndisc = toNum(cfg.aroCost);
  var aroRateM = periodicRate(toNum(cfg.aroRate, toNum(cfg.rate)), "effective");
  var aroPV = aroUndisc > 0 ? aroUndisc / Math.pow(1 + aroRateM, N) : 0;
  var idc = toNum(cfg.idc), prepaid = toNum(cfg.prepaid), incentive = toNum(cfg.incentive);

  var rou0 = pvGross + idc + prepaid - incentive + aroPV;
  var day1Pmt = advance ? payments[0] : 0;
  var strict = advance && cfg.day1Basis === "strict";
  var liabPresented = strict ? (pvGross - day1Pmt) : pvGross;

  var ul = Math.round(toNum(cfg.usefulLifeMonths));
  var depMonths = (cfg.transferOwnership && ul > 0) ? ul : (ul > 0 ? Math.min(ul, N) : N);

  var modMap = {};
  (cfg.mods || []).filter(function (m) { return m.enabled !== false; }).forEach(function (m) {
    modMap[Math.min(Math.max(Math.round(toNum(m.month, 1)), 1), N)] = m;
  });

  var rows = [], events = [];
  var openLiab = pvGross, nbv = rou0, accDep = 0, aro = aroPV, remDep = depMonths;
  var totInt = 0, totDep = 0, totUnwind = 0, totPL = 0, k;

  for (k = 1; k <= N; k++) {
    var pStart = addMonths(start, k - 1);
    var pEnd = addDays(addMonths(start, k), -1);
    var ev = modMap[k];
    var modLiabAdj = 0, modRouAdj = 0, modPL = 0, rateBefore = i;

    if (ev) {
      var preLiab = openLiab, preNbv = nbv;
      if (ev.type === "scopeDecrease") {
        var p = Math.min(Math.max(toNum(ev.scopePct) / 100, 0), 1);
        var lr = preLiab * p, rr = preNbv * p;
        openLiab -= lr; nbv -= rr; modPL += (lr - rr);
      }
      var iNew = (ev.newRate === "" || ev.newRate === null || ev.newRate === undefined)
        ? i : periodicRate(ev.newRate, cfg.rateBasis);
      var newLiab = pvFrom(payments, k, iNew, advance);
      var delta = newLiab - openLiab, rouAdj = delta;
      if (nbv + delta < 0) { rouAdj = -nbv; modPL += -(nbv + delta); }
      nbv += rouAdj; openLiab = newLiab; i = iNew;
      modLiabAdj = openLiab - preLiab; modRouAdj = nbv - preNbv; totPL += modPL;
      remDep = cfg.transferOwnership ? Math.max(remDep, 1) : Math.max(1, N - k + 1);
      events.push({ k: k, date: pStart, fy: fyKey(pStart, fyBasis), q: quarterOf(pStart, fyBasis),
        type: ev.type, label: ev.label || "Modification", preLiab: preLiab, postLiab: openLiab,
        liabAdj: modLiabAdj, rouAdj: modRouAdj, pl: modPL, rateBefore: rateBefore, rateAfter: iNew });
    }

    var pmt = payments[k - 1], interest, close;
    if (advance) { interest = (openLiab - pmt) * i; close = openLiab - pmt + interest; }
    else { interest = openLiab * i; close = openLiab + interest - pmt; }
    if (k === N && Math.abs(close) < 1) { interest = pmt - openLiab; close = 0; }

    var nbvOpen = nbv;
    var dep = remDep > 0 ? nbv / remDep : 0;
    if (k === N && depMonths <= N) dep = nbv;
    nbv -= dep; accDep += dep; remDep = Math.max(0, remDep - 1);

    var aroOpen = aro;
    var unwind = aro * aroRateM;
    if (k === N && aroUndisc > 0) unwind = aroUndisc - aro;
    aro += unwind;

    totInt += interest; totDep += dep; totUnwind += unwind;

    rows.push({
      k: k, fy: fyKey(pStart, fyBasis), q: quarterOf(pStart, fyBasis),
      pStart: pStart, pEnd: pEnd, days: dayDiff(pStart, pEnd) + 1,
      payDate: advance ? pStart : pEnd,
      open: openLiab, interest: interest, pmt: pmt, close: close,
      nbvOpen: nbvOpen, dep: dep, accDep: accDep, nbv: Math.max(nbv, 0),
      aroOpen: aroOpen, aro: aro, unwind: unwind,
      modLiabAdj: modLiabAdj, modRouAdj: modRouAdj, modPL: modPL, dt: null
    });
    openLiab = close;
  }

  var fyOrder = [], fyMap = {};
  rows.forEach(function (r) {
    if (!fyMap[r.fy]) {
      fyMap[r.fy] = { fy: r.fy, months: 0, interest: 0, pmt: 0, dep: 0, unwind: 0, modPL: 0,
                      modLiabAdj: 0, modRouAdj: 0, close: 0, nbv: 0, endRow: r };
      fyOrder.push(r.fy);
    }
    var g = fyMap[r.fy];
    g.months++; g.interest += r.interest; g.pmt += r.pmt; g.dep += r.dep;
    g.unwind += r.unwind; g.modPL += r.modPL;
    g.modLiabAdj += r.modLiabAdj; g.modRouAdj += r.modRouAdj;
    g.close = r.close; g.nbv = r.nbv; g.endRow = r;
  });
  var totalPmts = payments.reduce(function (a, b) { return a + b; }, 0);
  var slm = totalPmts / N;
  var fyRows = fyOrder.map(function (key) { var g = fyMap[key]; g.as17 = slm * g.months; return g; });

  var out = {
    cfg: cfg, payments: payments, rows: rows, fyRows: fyRows, events: events,
    N: N, advance: advance, fyBasis: fyBasis, depMonths: depMonths,
    rate0: i0, rateNow: i,
    liabGross: pvGross, liabPresented: liabPresented, day1Pmt: day1Pmt, strict: strict, rou0: rou0,
    build: { pv: pvGross, prepaid: prepaid, incentive: incentive, idc: idc, aro: aroPV, total: rou0 },
    aro: { pv: aroPV, undisc: aroUndisc, unwind: totUnwind, rateM: aroRateM },
    totals: { interest: totInt, dep: totDep, payments: totalPmts, unwind: totUnwind, modPL: totPL },
    meta: { start: start, end: addDays(addMonths(start, N), -1) },
    residualNBV: rows.length ? Math.max(rows[rows.length - 1].nbv, 0) : 0
  };

  /* deferred tax computed on the finished schedule, then stitched onto each row */
  out.dt = buildDeferredTax(out, cfg);
  if (out.dt.on) {
    out.dt.rows.forEach(function (d, x) { if (out.rows[x]) out.rows[x].dt = d; });
    out.fyRows.forEach(function (g) {
      var f = null;
      out.dt.fyRows.forEach(function (h) { if (h.fy === g.fy) f = h; });
      g.dtMove = f ? f.move : 0;
      g.dtClose = f ? f.close : 0;
      g.dtRateEffect = f ? f.rateEffect : 0;
    });
  }
  return out;
}

/* 3.5 Balances as on a date */
export function balanceAt(res, d, basis) {
  var zero = { liab: 0, nbv: 0, aro: 0, dt: 0, dta: 0, dtl: 0, inPeriod: null, frac: 0 };
  if (!res || !d || !res.rows.length) return zero;
  if (cmpD(d, res.meta.start) < 0) return zero;
  var last = res.rows[res.rows.length - 1];
  if (cmpD(d, last.pEnd) >= 0) {
    return { liab: last.close, nbv: last.nbv, aro: last.aro,
             dt: last.dt ? last.dt.close : 0, dta: last.dt ? last.dt.dta : 0,
             dtl: last.dt ? last.dt.dtl : 0, inPeriod: null, frac: 1 };
  }
  if (basis === "period") {
    var pick = null;
    res.rows.forEach(function (r) { if (cmpD(r.pStart, d) <= 0) pick = r; });
    if (!pick) return zero;
    return { liab: pick.close, nbv: pick.nbv, aro: pick.aro,
             dt: pick.dt ? pick.dt.close : 0, dta: pick.dt ? pick.dt.dta : 0,
             dtl: pick.dt ? pick.dt.dtl : 0, inPeriod: pick, frac: 1 };
  }
  var row = null;
  res.rows.forEach(function (r) { if (cmpD(r.pStart, d) <= 0 && cmpD(d, r.pEnd) <= 0) row = r; });
  if (!row) {
    var p2 = null;
    res.rows.forEach(function (r) { if (cmpD(r.pEnd, d) <= 0) p2 = r; });
    if (!p2) return zero;
    return { liab: p2.close, nbv: p2.nbv, aro: p2.aro,
             dt: p2.dt ? p2.dt.close : 0, dta: p2.dt ? p2.dt.dta : 0,
             dtl: p2.dt ? p2.dt.dtl : 0, inPeriod: null, frac: 1 };
  }
  var frac = (dayDiff(row.pStart, d) + 1) / row.days;
  var paid = cmpD(row.payDate, d) <= 0 ? row.pmt : 0;
  var dtv = row.dt ? (row.dt.open + row.dt.move * frac) : 0;
  var dtaV = row.dt ? (row.dt.dta * frac + (row.dt.dta - row.dt.move) * 0) : 0;
  return {
    liab: row.open - paid + row.interest * frac,
    nbv: Math.max(row.nbvOpen - row.dep * frac, 0),
    aro: row.aroOpen + row.unwind * frac,
    dt: dtv,
    dta: dtv >= 0 ? dtv : 0, dtl: dtv < 0 ? -dtv : 0,
    inPeriod: row, frac: frac
  };
}

export function maturityAt(res, d) {
  var b = [0, 0, 0, 0, 0], gross = 0;
  res.rows.forEach(function (r) {
    if (cmpD(r.payDate, d) <= 0) return;
    gross += r.pmt;
    var mo = monthsBetween(d, r.payDate);
    if (mo < 12) b[0] += r.pmt;
    else if (mo < 24) b[1] += r.pmt;
    else if (mo < 36) b[2] += r.pmt;
    else if (mo < 60) b[3] += r.pmt;
    else b[4] += r.pmt;
  });
  return { buckets: b, gross: gross };
}

export function snapshot(res, iso, basis) {
  var d = parseISO(iso);
  if (!res || !d) return null;
  var bal = balanceAt(res, d, basis || "accrual");
  var fwd = balanceAt(res, addMonths(d, 12), basis || "accrual");
  var mat = maturityAt(res, d);
  var fy = fyKey(d, res.fyBasis), fyFig = null;
  res.fyRows.forEach(function (g) { if (g.fy === fy) fyFig = g; });
  var nonCur = Math.min(fwd.liab, bal.liab);
  return {
    asAt: d, liab: bal.liab, nbv: bal.nbv, aro: bal.aro, dt: bal.dt,
    nonCurrent: nonCur, current: Math.max(bal.liab - nonCur, 0),
    maturity: [
      ["Not later than 1 year", mat.buckets[0]],
      ["Later than 1 year and not later than 2 years", mat.buckets[1]],
      ["Later than 2 years and not later than 3 years", mat.buckets[2]],
      ["Later than 3 years and not later than 5 years", mat.buckets[3]],
      ["Later than 5 years", mat.buckets[4]]
    ],
    buckets: mat.buckets, gross: mat.gross, imputed: mat.gross - bal.liab,
    fy: fy, fyFig: fyFig,
    isFirstFy: res.fyRows.length > 0 && res.fyRows[0].fy === fy
  };
}

/* 3.6 Accrual between two dates */
export function accrueBetween(res, from, to, basis) {
  var o = { interest: 0, dep: 0, unwind: 0, pmt: 0, modLiabAdj: 0, modRouAdj: 0, modPL: 0,
            addLiab: 0, addRou: 0, months: 0, dtMove: 0, dtOrig: 0, dtRateEffect: 0, dtDay1: 0 };
  if (!res || !from || !to || cmpD(from, to) > 0) return o;

  var commencedInWindow = cmpD(res.meta.start, from) >= 0 && cmpD(res.meta.start, to) <= 0;
  if (commencedInWindow) {
    o.addLiab += res.liabGross; o.addRou += res.rou0;
    if (res.dt && res.dt.on) {
      o.dtDay1 += res.dt.day1.move;
      o.dtMove += res.dt.day1.move;
      o.dtOrig += res.dt.day1.origination;
    }
  }
  res.rows.forEach(function (r) {
    var f = 0;
    if (basis === "period") {
      f = (cmpD(r.pStart, from) >= 0 && cmpD(r.pStart, to) <= 0) ? 1 : 0;
    } else {
      var s = cmpD(r.pStart, from) > 0 ? r.pStart : from;
      var e = cmpD(r.pEnd, to) < 0 ? r.pEnd : to;
      var ov = dayDiff(s, e) + 1;
      f = ov > 0 ? ov / r.days : 0;
    }
    if (f > 0) {
      o.interest += r.interest * f; o.dep += r.dep * f; o.unwind += r.unwind * f;
      o.months += f;
      if (r.dt) {
        o.dtMove += r.dt.move * f;
        o.dtOrig += r.dt.origination * f;
        o.dtRateEffect += r.dt.rateEffect * f;
      }
    }
    var payIn = (basis === "period")
      ? (cmpD(r.pStart, from) >= 0 && cmpD(r.pStart, to) <= 0)
      : (cmpD(r.payDate, from) >= 0 && cmpD(r.payDate, to) <= 0);
    if (payIn) o.pmt += r.pmt;
    if (cmpD(r.pStart, from) >= 0 && cmpD(r.pStart, to) <= 0) {
      o.modLiabAdj += r.modLiabAdj; o.modRouAdj += r.modRouAdj; o.modPL += r.modPL;
    }
  });
  return o;
}

/* 3.7 Portfolio quarterly report */
export function buildQuarterReport(leases, q, basis, asOnISO) {
  var qs = q.start, qe = q.end;
  var asOn = parseISO(asOnISO) || qe;
  var ys = fyStart(qe, q.basis);
  var lines = [], jr = [], flags = [];
  var T = {
    interest: 0, dep: 0, unwind: 0, pmt: 0, modPL: 0, addLiab: 0, addRou: 0,
    modLiabAdj: 0, modRouAdj: 0, openLiab: 0, closeLiab: 0, openRou: 0, closeRou: 0,
    aro: 0, current: 0, nonCurrent: 0, buckets: [0, 0, 0, 0, 0], gross: 0,
    ytdInterest: 0, ytdDep: 0, ytdUnwind: 0, ytdPmt: 0, ytdModPL: 0, wSum: 0, byClass: {},
    dtOpen: 0, dtClose: 0, dtMove: 0, dtOrig: 0, dtRateEffect: 0, dtDay1: 0,
    ytdDtMove: 0, dta: 0, dtl: 0, dtOn: false
  };

  leases.forEach(function (L) {
    var res = L.res, c = L.cfg;
    if (cmpD(res.meta.start, qe) > 0) return;
    var qAcc = accrueBetween(res, qs, qe, basis);
    var yAcc = accrueBetween(res, ys, qe, basis);
    var openB = balanceAt(res, addDays(qs, -1), basis);
    var closeB = balanceAt(res, qe, basis);
    var onB = balanceAt(res, asOn, basis);
    var fwd = balanceAt(res, addMonths(asOn, 12), basis);
    var mat = maturityAt(res, asOn);
    var nonCur = Math.min(fwd.liab, onB.liab), cur = Math.max(onB.liab - nonCur, 0);
    var hasDt = !!(res.dt && res.dt.on);
    if (hasDt) T.dtOn = true;

    var expQ = qAcc.interest + qAcc.dep + qAcc.unwind - qAcc.modPL;
    var expY = yAcc.interest + yAcc.dep + yAcc.unwind - yAcc.modPL;
    var tie = (openB.liab + qAcc.addLiab + qAcc.modLiabAdj + qAcc.interest - qAcc.pmt) - closeB.liab;
    var tieDt = (openB.dt + qAcc.dtMove) - closeB.dt;

    lines.push({
      id: c.id, name: c.name, lessor: c.lessor, cls: c.assetClass || "Unclassified",
      rate: toNum(c.rate), start: res.meta.start, end: res.meta.end, term: res.N,
      qInterest: qAcc.interest, qDep: qAcc.dep, qUnwind: qAcc.unwind, qPmt: qAcc.pmt,
      qModPL: qAcc.modPL, qExp: expQ,
      qDtMove: qAcc.dtMove, qDtOrig: qAcc.dtOrig, qDtRate: qAcc.dtRateEffect,
      qExpNet: expQ - qAcc.dtMove,
      yInterest: yAcc.interest, yDep: yAcc.dep, yUnwind: yAcc.unwind, yPmt: yAcc.pmt,
      yModPL: yAcc.modPL, yExp: expY, yDtMove: yAcc.dtMove, yExpNet: expY - yAcc.dtMove,
      openLiab: openB.liab, addLiab: qAcc.addLiab, modLiabAdj: qAcc.modLiabAdj, closeLiab: closeB.liab,
      openRou: openB.nbv, addRou: qAcc.addRou, modRouAdj: qAcc.modRouAdj, closeRou: closeB.nbv,
      onLiab: onB.liab, onRou: onB.nbv, onAro: onB.aro, current: cur, nonCurrent: nonCur,
      dtOpen: openB.dt, dtClose: closeB.dt, onDt: onB.dt, hasDt: hasDt,
      dtTreat: hasDt ? res.dt.treat : "", dtRate: hasDt ? res.dt.finalRate : 0,
      buckets: mat.buckets, gross: mat.gross, tie: tie, tieDt: tieDt,
      ended: cmpD(res.meta.end, qe) < 0, commenced: cmpD(res.meta.start, qs) >= 0
    });

    T.interest += qAcc.interest; T.dep += qAcc.dep; T.unwind += qAcc.unwind;
    T.pmt += qAcc.pmt; T.modPL += qAcc.modPL;
    T.addLiab += qAcc.addLiab; T.addRou += qAcc.addRou;
    T.modLiabAdj += qAcc.modLiabAdj; T.modRouAdj += qAcc.modRouAdj;
    T.openLiab += openB.liab; T.closeLiab += closeB.liab;
    T.openRou += openB.nbv; T.closeRou += closeB.nbv;
    T.aro += onB.aro; T.current += cur; T.nonCurrent += nonCur;
    T.gross += mat.gross; T.wSum += onB.liab * toNum(c.rate);
    mat.buckets.forEach(function (v, x) { T.buckets[x] += v; });
    T.ytdInterest += yAcc.interest; T.ytdDep += yAcc.dep; T.ytdUnwind += yAcc.unwind;
    T.ytdPmt += yAcc.pmt; T.ytdModPL += yAcc.modPL;
    T.dtOpen += openB.dt; T.dtClose += closeB.dt; T.dtMove += qAcc.dtMove;
    T.dtOrig += qAcc.dtOrig; T.dtRateEffect += qAcc.dtRateEffect; T.dtDay1 += qAcc.dtDay1;
    T.ytdDtMove += yAcc.dtMove;
    T.dta += onB.dt > 0 ? onB.dt : 0; T.dtl += onB.dt < 0 ? -onB.dt : 0;

    var key = c.assetClass || "Unclassified";
    if (!T.byClass[key]) T.byClass[key] = { n: 0, dep: 0, interest: 0, nbv: 0, liab: 0, dt: 0 };
    T.byClass[key].n++; T.byClass[key].dep += qAcc.dep; T.byClass[key].interest += qAcc.interest;
    T.byClass[key].nbv += onB.nbv; T.byClass[key].liab += onB.liab; T.byClass[key].dt += onB.dt;

    function J(acc, dr, cr, nar) {
      if (Math.abs(toNum(dr) + toNum(cr)) < 0.005) return;
      jr.push({ id: c.id, name: c.name, cls: key, date: fmtDate(qe), acc: acc,
                dr: r2(dr), cr: r2(cr), nar: nar });
    }
    if (qAcc.addRou > 0.005 || qAcc.addLiab > 0.005) {
      J("Right-of-Use Asset", qAcc.addRou, 0, "Initial recognition on commencement, Ind AS 116.22 to 26");
      J("Lease Liability", 0, qAcc.addLiab, "Initial recognition on commencement, Ind AS 116.26");
      var diff = qAcc.addRou - qAcc.addLiab;
      if (Math.abs(diff) > 0.005) J("Bank, prepaid rent, incentives and restoration provision, net", 0, diff,
        "Net of initial direct costs, incentives received and the restoration provision, Ind AS 116.24");
    }
    J("Finance Cost - interest on lease liability", qAcc.interest, 0, "Interest accretion for the quarter, Ind AS 116.36(a)");
    J("Lease Liability", 0, qAcc.interest, "Interest accretion for the quarter, Ind AS 116.36(a)");
    J("Depreciation - right-of-use asset", qAcc.dep, 0, "Straight line depreciation for the quarter, Ind AS 116.31");
    J("Accumulated Depreciation - right-of-use asset", 0, qAcc.dep, "Straight line depreciation for the quarter, Ind AS 116.31");
    J("Finance Cost - unwinding of restoration provision", qAcc.unwind, 0, "Unwinding of discount, Ind AS 37");
    J("Provision for Site Restoration", 0, qAcc.unwind, "Unwinding of discount, Ind AS 37");
    J("Lease Liability", qAcc.pmt, 0, "Rentals paid during the quarter, Ind AS 116.36(b)");
    J("Bank or Lessor Payable", 0, qAcc.pmt, "Rentals paid during the quarter, Ind AS 116.36(b)");
    if (Math.abs(qAcc.modLiabAdj) > 0.005 || Math.abs(qAcc.modRouAdj) > 0.005) {
      J("Right-of-Use Asset", Math.max(qAcc.modRouAdj, 0), 0, "Remeasurement on modification, Ind AS 116.45 and 46");
      J("Lease Liability", Math.max(-qAcc.modLiabAdj, 0), 0, "Remeasurement on modification, Ind AS 116.45 and 46");
      J("Lease Liability", 0, Math.max(qAcc.modLiabAdj, 0), "Remeasurement on modification, Ind AS 116.45 and 46");
      J("Right-of-Use Asset", 0, Math.max(-qAcc.modRouAdj, 0), "Remeasurement on modification, Ind AS 116.45 and 46");
      J("Gain on lease modification or termination", 0, Math.max(qAcc.modPL, 0), "Ind AS 116.46(a)");
      J("Loss on lease modification", Math.max(-qAcc.modPL, 0), 0, "Ind AS 116.46(a)");
    }
    if (hasDt && Math.abs(qAcc.dtMove) > 0.005) {
      if (qAcc.dtMove > 0) {
        J("Deferred Tax Asset", qAcc.dtMove, 0, "Deferred tax on lease temporary differences for the quarter, Ind AS 12.15, 12.24 and 12.22A");
        J("Deferred Tax - credit to the statement of profit and loss", 0, qAcc.dtMove, "Deferred tax income for the quarter, Ind AS 12.58");
      } else {
        J("Deferred Tax - charge to the statement of profit and loss", -qAcc.dtMove, 0, "Reversal of deferred tax on lease temporary differences, Ind AS 12.58");
        J("Deferred Tax Asset", 0, -qAcc.dtMove, "Reversal of deferred tax on lease temporary differences, Ind AS 12.58");
      }
    }
    if (Math.abs(tie) > 1) flags.push(c.id + " : lease liability movement reconciliation is out by " + money(tie));
    if (hasDt && Math.abs(tieDt) > 1) flags.push(c.id + " : deferred tax movement reconciliation is out by " + money(tieDt));
    if (hasDt && Math.abs(qAcc.dtRateEffect) > 0.005)
      flags.push(c.id + " : a change in the enacted tax rate affected this quarter by " + money(qAcc.dtRateEffect) + ". Ind AS 12.60 requires this to be recognised in profit or loss, and disclosed separately under para 81(d).");
    if (cmpD(res.meta.end, qe) >= 0 && cmpD(res.meta.end, addMonths(qe, 3)) <= 0)
      flags.push(c.id + " : the lease expires on " + fmtDate(res.meta.end) + ". Confirm the renewal or exit accounting and the reversal of the related deferred tax.");
  });

  T.wavg = T.closeLiab > 0 ? T.wSum / T.closeLiab : 0;
  T.qExp = T.interest + T.dep + T.unwind - T.modPL;
  T.ytdExp = T.ytdInterest + T.ytdDep + T.ytdUnwind - T.ytdModPL;
  T.qExpNet = T.qExp - T.dtMove;
  T.ytdExpNet = T.ytdExp - T.ytdDtMove;
  T.tie = (T.openLiab + T.addLiab + T.modLiabAdj + T.interest - T.pmt) - T.closeLiab;
  T.tieRou = (T.openRou + T.addRou + T.modRouAdj - T.dep) - T.closeRou;
  T.tieDt = (T.dtOpen + T.dtMove) - T.dtClose;
  T.imputed = T.gross - T.closeLiab;

  var consol = [
    { acc: "Finance Cost - interest on lease liabilities", dr: T.interest },
    { acc: "Depreciation - right-of-use assets", dr: T.dep },
    { acc: "Finance Cost - unwinding of restoration provisions", dr: T.unwind },
    { acc: "Right-of-Use Assets - additions and remeasurements", dr: Math.max(T.addRou + T.modRouAdj, 0) },
    { acc: "Lease Liabilities - rentals paid", dr: T.pmt },
    { acc: "Loss on lease modifications", dr: Math.max(-T.modPL, 0) },
    { acc: "Deferred Tax Asset", dr: Math.max(T.dtMove, 0) },
    { acc: "Deferred Tax - charge to profit or loss", dr: Math.max(-T.dtMove, 0) },
    { acc: "Lease Liabilities - interest accretion", cr: T.interest },
    { acc: "Accumulated Depreciation - right-of-use assets", cr: T.dep },
    { acc: "Provisions for Site Restoration", cr: T.unwind },
    { acc: "Lease Liabilities - additions and remeasurements", cr: Math.max(T.addLiab + T.modLiabAdj, 0) },
    { acc: "Bank or Lessor Payable", cr: T.pmt },
    { acc: "Gain on lease modifications", cr: Math.max(T.modPL, 0) },
    { acc: "Deferred Tax - credit to profit or loss", cr: Math.max(T.dtMove, 0) },
    { acc: "Deferred Tax Asset - reversal", cr: Math.max(-T.dtMove, 0) }
  ];
  var drSum = consol.reduce(function (s, l) { return s + toNum(l.dr); }, 0);
  var crSum = consol.reduce(function (s, l) { return s + toNum(l.cr); }, 0);
  if (Math.abs(drSum - crSum) > 0.005) {
    if (drSum > crSum) consol.push({ acc: "Bank, prepaid rent, incentives and restoration provisions, net", cr: drSum - crSum });
    else consol.push({ acc: "Bank, prepaid rent, incentives and restoration provisions, net", dr: crSum - drSum });
  }

  return { q: q, basis: basis, asOn: asOn, ys: ys, lines: lines, T: T, jr: jr, consol: consol, flags: flags };
}

/* ------------------------------------------------- 5. EXPORT HELPERS */
export function download(blob, name) {
  var u = URL.createObjectURL(blob), el = document.createElement("a");
  el.href = u; el.download = name; document.body.appendChild(el); el.click();
  document.body.removeChild(el); URL.revokeObjectURL(u);
}
export function csvCell(v) {
  if (v === null || v === undefined) return "";
  var s = String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
export function toCSV(rows) { return rows.map(function (r) { return r.map(csvCell).join(","); }).join("\r\n"); }
export function xmlEsc(s) {
  return String(s === null || s === undefined ? "" : s)
    .replace(/&/g, "&#38;").replace(/</g, "&#60;").replace(/>/g, "&#62;")
    .replace(/"/g, "&#34;").replace(/'/g, "&#39;");
}
export function buildWorkbook(sheets) {
  var head = '<?xml version="1.0"?>\n<?mso-application progid="Excel.Sheet"?>\n' +
    '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" ' +
    'xmlns:o="urn:schemas-microsoft-com:office:office" ' +
    'xmlns:x="urn:schemas-microsoft-com:office:excel" ' +
    'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">\n' +
    '<Styles>' +
    '<Style ss:ID="t"><Font ss:Bold="1" ss:Size="13" ss:Color="#1E293B"/></Style>' +
    '<Style ss:ID="h"><Font ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1E293B" ss:Pattern="Solid"/>' +
    '<Alignment ss:Vertical="Center" ss:WrapText="1"/></Style>' +
    '<Style ss:ID="n"><NumberFormat ss:Format="#,##0.00;(#,##0.00)"/></Style>' +
    '<Style ss:ID="nb"><Font ss:Bold="1"/><NumberFormat ss:Format="#,##0.00;(#,##0.00)"/>' +
    '<Interior ss:Color="#F1F5F9" ss:Pattern="Solid"/></Style>' +
    '<Style ss:ID="b"><Font ss:Bold="1"/><Interior ss:Color="#F1F5F9" ss:Pattern="Solid"/></Style>' +
    '<Style ss:ID="lbl"><Font ss:Bold="1" ss:Color="#334155"/></Style>' +
    '</Styles>\n';
  var body = sheets.map(function (sh) {
    var rows = sh.rows.map(function (r) {
      var cells = r.cells.map(function (c) {
        var v = c && typeof c === "object" ? c.v : c;
        var st = c && typeof c === "object" ? c.s : null;
        var isNum = typeof v === "number" && isFinite(v);
        var style = st ? st : (isNum ? "n" : "");
        return "<Cell" + (style ? ' ss:StyleID="' + style + '"' : "") + ">" +
          "<Data ss:Type=\"" + (isNum ? "Number" : "String") + "\">" +
          (isNum ? r2(v) : xmlEsc(v)) + "</Data></Cell>";
      }).join("");
      return "<Row>" + cells + "</Row>";
    }).join("\n");
    var cols = (sh.widths || []).map(function (w) { return '<Column ss:Width="' + w + '"/>'; }).join("");
    return '<Worksheet ss:Name="' + xmlEsc(sh.name).slice(0, 31) + '">\n<Table>' + cols + "\n" + rows + "</Table>" +
      '<WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel"><FreezePanes/><FrozenNoSplit/>' +
      '<SplitHorizontal>' + (sh.freeze || 1) + '</SplitHorizontal>' +
      '<TopRowBottomPane>' + (sh.freeze || 1) + '</TopRowBottomPane><ActivePane>2</ActivePane>' +
      '</WorksheetOptions></Worksheet>';
  }).join("\n");
  return head + body + "\n</Workbook>";
}
export function R(cells) { return { cells: cells }; }
export function H(arr) { return { cells: arr.map(function (v) { return { v: v, s: "h" }; }) }; }
export function TOT(arr) { return { cells: arr.map(function (v) { return { v: v, s: typeof v === "number" ? "nb" : "b" }; }) }; }
