// @ts-nocheck
import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { toNum, clampInt, parseISO, toISO, addMonths, cmpD, fmtDate, fmtMon, fyKey, fyEnd, quarterOf, quarterKey, nextQuarter, money, pctS, uid, r2, br, StoreEngine, Store, periodicRate, buildPayments, computeLease, snapshot, buildQuarterReport, download, toCSV, buildWorkbook, R, H, TOT } from "./core";
import { inputCls, miniCls, Field, Section, Card, JE, Th, Td, TrendChart } from "./ui";
import { blankCfg, newMod, ASSET_CLASSES, DT_TREATMENTS } from "./defaults";

function App() {
  var a1 = useState(blankCfg), cfg = a1[0], setCfg = a1[1];
  var a2 = useState(null), res = a2[0], setRes = a2[1];
  var a3 = useState({}), errs = a3[0], setErrs = a3[1];
  var a4 = useState(""), fatal = a4[0], setFatal = a4[1];
  var a5 = useState("dash"), tab = a5[0], setTab = a5[1];
  var a6 = useState("monthly"), view = a6[0], setView = a6[1];
  var a7 = useState([]), portfolio = a7[0], setPortfolio = a7[1];
  var a8 = useState(""), toast = a8[0], setToast = a8[1];

  var c1 = useState(""), qSel = c1[0], setQSel = c1[1];
  var c2 = useState("accrual"), qBasis = c2[0], setQBasis = c2[1];
  var c3 = useState(true), incCurrent = c3[0], setIncCurrent = c3[1];
  var c4 = useState(""), asOn = c4[0], setAsOn = c4[1];
  var c5 = useState("Your Company Limited"), entity = c5[0], setEntity = c5[1];
  var d1 = useState("fy"), dtView = d1[0], setDtView = d1[1];
  var outRef = useRef(null);

  var S = cfg.symbol;

  function upd(key) {
    return function (ev) {
      var v = ev.target.type === "checkbox" ? ev.target.checked : ev.target.value;
      setCfg(function (p) { var n = Object.assign({}, p); n[key] = v; return n; });
    };
  }
  function setKey(key, val) { setCfg(function (p) { var n = Object.assign({}, p); n[key] = val; return n; }); }

  function validate(k) {
    var er = {};
    if (!parseISO(k.startDate)) er.startDate = "A valid commencement date is required.";
    var n = toNum(k.termMonths, 0);
    if (!(n >= 1 && n <= 600)) er.termMonths = "Enter 1 to 600 months.";
    if (toNum(k.basePayment, -1) < 0) er.basePayment = "Cannot be negative.";
    var r = toNum(k.rate, -1);
    if (!(r >= 0 && r <= 100)) er.rate = "Enter 0 to 100 percent.";
    if (toNum(k.rentFreeMonths) >= n) er.rentFreeMonths = "Must be less than the lease term.";
    if (k.dtOn) {
      var tr = toNum(k.dtRate, -1);
      if (!(tr >= 0 && tr <= 100)) er.dtRate = "Enter a tax rate between 0 and 100 percent.";
      if (k.dtRestrict) {
        var rp = toNum(k.dtRecognisePct, -1);
        if (!(rp >= 0 && rp <= 100)) er.dtRecognisePct = "Enter 0 to 100 percent.";
      }
      (k.dtRateSchedule || []).forEach(function (s) {
        if (s.enabled === false) return;
        if (!parseISO(s.from)) er.dtRateSchedule = "Every enacted rate change needs a valid effective date.";
        if (!(toNum(s.rate, -1) >= 0 && toNum(s.rate, -1) <= 100)) er.dtRateSchedule = "Every enacted rate must be between 0 and 100 percent.";
      });
    }
    (k.mods || []).forEach(function (m) {
      var mm = toNum(m.month, 0);
      if (mm < 1 || mm > n) er.mods = "Every modification month must fall inside the lease term.";
    });
    return er;
  }

  var run = useCallback(function (k, scroll) {
    var er = validate(k); setErrs(er);
    if (Object.keys(er).length) { setRes(null); return; }
    try {
      var out = computeLease(k);
      setFatal(""); setRes(out);
      if (!parseISO(k.reportingDate)) setKey("reportingDate", toISO(fyEnd(out.meta.start, k.fyBasis)));
      if (scroll && outRef.current) {
        setTimeout(function () { outRef.current.scrollIntoView({ behavior: "smooth", block: "start" }); }, 60);
      }
    } catch (ex) { setRes(null); setFatal(ex && ex.message ? ex.message : String(ex)); }
  }, []);

  var aLB = useState(""), lastBackup = aLB[0], setLastBackup = aLB[1];
  function loadPortfolio() { Store.all().then(function (l) { setPortfolio(l || []); }); }
  useEffect(function () {
    run(cfg, false); loadPortfolio();
    try { setLastBackup(localStorage.getItem("indas116v4_lastBackup") || ""); } catch (e) {}
  }, []);

  var reportingISO = parseISO(cfg.reportingDate) ? cfg.reportingDate
    : (res ? toISO(fyEnd(res.meta.start, cfg.fyBasis)) : "");

  var snap = useMemo(function () {
    try { return res ? snapshot(res, reportingISO, "accrual") : null; } catch (ex) { return null; }
  }, [res, reportingISO]);

  var gridPmts = useMemo(function () {
    try { return buildPayments(cfg); } catch (ex) { return []; }
  }, [cfg]);

  var allLeases = useMemo(function () {
    var list = portfolio.map(function (p) {
      try { var full = Object.assign(blankCfg(), p); return { cfg: full, res: computeLease(full) }; }
      catch (ex) { return null; }
    }).filter(function (x) { return x; });
    if (incCurrent && res) {
      var dup = false;
      list.forEach(function (L) { if (L.cfg.id === cfg.id) dup = true; });
      if (!dup) list.push({ cfg: cfg, res: res });
      else list = list.map(function (L) { return L.cfg.id === cfg.id ? { cfg: cfg, res: res } : L; });
    }
    return list;
  }, [portfolio, res, cfg, incCurrent]);

  var quarters = useMemo(function () {
    var seen = {}, list = [];
    allLeases.forEach(function (L) {
      var q = quarterOf(L.res.meta.start, L.cfg.fyBasis || "mar"), guard = 0;
      while (q && cmpD(q.start, L.res.meta.end) <= 0 && guard < 400) {
        var k = quarterKey(q);
        if (!seen[k]) { seen[k] = 1; list.push(q); }
        q = nextQuarter(q); guard++;
      }
    });
    list.sort(function (a, b) { return cmpD(a.start, b.start); });
    return list;
  }, [allLeases]);

  useEffect(function () {
    if (!quarters.length) return;
    var exists = false;
    quarters.forEach(function (q) { if (quarterKey(q) === qSel) exists = true; });
    if (!exists) {
      var today = parseISO(new Date().toISOString().slice(0, 10)), pick = quarters[0];
      quarters.forEach(function (q) { if (cmpD(q.start, today) <= 0) pick = q; });
      setQSel(quarterKey(pick));
    }
  }, [quarters]);

  var qObj = useMemo(function () {
    var f = null;
    quarters.forEach(function (q) { if (quarterKey(q) === qSel) f = q; });
    return f || (quarters.length ? quarters[0] : null);
  }, [quarters, qSel]);

  useEffect(function () { if (qObj && !parseISO(asOn)) setAsOn(toISO(qObj.end)); }, [qObj]);

  var qRep = useMemo(function () {
    if (!qObj || !allLeases.length) return null;
    try { return buildQuarterReport(allLeases, qObj, qBasis, parseISO(asOn) ? asOn : toISO(qObj.end)); }
    catch (ex) { return null; }
  }, [qObj, allLeases, qBasis, asOn]);

  var portRes = useMemo(function () {
    return allLeases.map(function (L) {
      var iso = parseISO(reportingISO) ? reportingISO : toISO(fyEnd(L.res.meta.start, L.cfg.fyBasis));
      return { cfg: L.cfg, res: L.res, snap: snapshot(L.res, iso, "accrual") };
    }).filter(function (x) { return x.snap; });
  }, [allLeases, reportingISO]);

  var consol = useMemo(function () {
    if (!portRes.length) return null;
    var t = { liab: 0, current: 0, nonCurrent: 0, nbv: 0, aro: 0, interest: 0, dep: 0,
      pmt: 0, gross: 0, wSum: 0, dt: 0, dtMove: 0, buckets: [0, 0, 0, 0, 0], byClass: {} };
    portRes.forEach(function (o) {
      var s = o.snap, cc = o.cfg;
      t.liab += s.liab; t.current += s.current; t.nonCurrent += s.nonCurrent;
      t.nbv += s.nbv; t.aro += s.aro; t.gross += s.gross; t.wSum += s.liab * toNum(cc.rate);
      t.dt += s.dt;
      if (s.fyFig) {
        t.interest += s.fyFig.interest; t.dep += s.fyFig.dep; t.pmt += s.fyFig.pmt;
        t.dtMove += toNum(s.fyFig.dtMove);
      }
      s.buckets.forEach(function (v, x) { t.buckets[x] += v; });
      var key = cc.assetClass || "Unclassified";
      if (!t.byClass[key]) t.byClass[key] = { nbv: 0, dep: 0, liab: 0, dt: 0, n: 0 };
      t.byClass[key].nbv += s.nbv; t.byClass[key].liab += s.liab; t.byClass[key].n++;
      t.byClass[key].dt += s.dt;
      if (s.fyFig) t.byClass[key].dep += s.fyFig.dep;
    });
    t.wavg = t.liab > 0 ? t.wSum / t.liab : 0;
    return t;
  }, [portRes]);

  function flash(m) { setToast(m); setTimeout(function () { setToast(""); }, 4200); }

  function saveLease() {
    Store.put(Object.assign({}, cfg, { savedAt: new Date().toISOString() })).then(function () {
      flash("Saved " + cfg.name + " with identifier " + cfg.id + " to " + StoreEngine + ".");
      loadPortfolio();
    });
  }
  function loadLease(rec) { var k = Object.assign(blankCfg(), rec); setCfg(k); setTab("dash"); run(k, false); }
  function delLease(id) { Store.del(id).then(loadPortfolio); }
  function brandNew() { var k = blankCfg(); setCfg(k); run(k, false); setTab("dash"); }

  function depositAdjust() {
    var sd = toNum(cfg.securityDeposit);
    if (sd <= 0) { flash("Enter a security deposit amount first."); return; }
    var i = periodicRate(cfg.rate, cfg.rateBasis), n = clampInt(cfg.termMonths, 1, 600);
    var fv = i === 0 ? sd : sd / Math.pow(1 + i, n), pre = sd - fv;
    var next = Object.assign({}, cfg, { prepaid: r2(toNum(cfg.prepaid) + pre) });
    setCfg(next); run(next, false);
    flash("Added " + money(pre) + " of deemed prepaid rent to the ROU asset, being the discount on the interest free deposit under Ind AS 109.");
  }

  /* ---- exports ---- */
  function exportScheduleCSV() {
    if (!res) return;
    var dtOn = res.dt && res.dt.on;
    var head = ["Period", "FY", "Quarter", "Month", "Payment Date", "Opening Liability",
      "Interest Expense", "Lease Payment", "Modification Adjustment", "Closing Liability",
      "Depreciation", "Accumulated Depreciation", "ROU Net Block", "Restoration Provision"];
    if (dtOn) head = head.concat(["ROU Tax Base", "Liability Tax Base", "Taxable TD on ROU",
      "Deductible TD on Liability", "Deductible TD on Provision", "Net Temporary Difference",
      "Tax Rate", "Deferred Tax Asset", "Deferred Tax Liability", "Net Deferred Tax",
      "Deferred Tax Movement", "Of which rate change"]);
    var rows = [head];
    res.rows.forEach(function (r) {
      var line = [r.k, r.fy, r.q ? r.q.label : "", fmtMon(r.pStart), fmtDate(r.payDate),
        r2(r.open), r2(r.interest), r2(r.pmt), r2(r.modLiabAdj), r2(r.close),
        r2(r.dep), r2(r.accDep), r2(r.nbv), r2(r.aro)];
      if (dtOn && r.dt) line = line.concat([r2(r.dt.rouTB), r2(r.dt.liabTB), r2(r.dt.tdRou),
        r2(r.dt.tdLiab), r2(r.dt.tdAro), r2(r.dt.netTd), r2(r.dt.rate * 100),
        r2(r.dt.dta), r2(r.dt.dtl), r2(r.dt.close), r2(r.dt.move), r2(r.dt.rateEffect)]);
      rows.push(line);
    });
    download(new Blob([toCSV(rows)], { type: "text/csv;charset=utf-8;" }), "IndAS116_" + cfg.id + "_Schedule.csv");
  }
  function exportJSON() {
    var data = portfolio.length ? portfolio : [cfg];
    download(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }), "IndAS116_Portfolio.json");
  }
  function importJSON(ev) {
    var file = ev.target.files && ev.target.files[0]; if (!file) return;
    var rd = new FileReader();
    rd.onload = function () {
      try {
        var parsed = JSON.parse(rd.result), arr = Array.isArray(parsed) ? parsed : [parsed];
        Promise.all(arr.map(function (r) { return Store.put(Object.assign(blankCfg(), r, { id: r.id || uid() })); }))
          .then(function () { loadPortfolio(); flash("Imported " + arr.length + " lease record(s)."); });
      } catch (ex) { flash("That file is not valid JSON."); }
    };
    rd.readAsText(file); ev.target.value = "";
  }
  function markBackup() {
    var ts = new Date().toISOString();
    try { localStorage.setItem("indas116v4_lastBackup", ts); } catch (e) {}
    setLastBackup(ts);
  }
  function backupPortfolio() {
    var data = portfolio.length ? portfolio : [cfg];
    var env = { app: "IndAS116", version: 4, exportedAt: new Date().toISOString(), count: data.length, leases: data };
    var stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    download(new Blob([JSON.stringify(env, null, 2)], { type: "application/json" }),
      "IndAS116_Backup_" + stamp + ".json");
    markBackup();
  }
  function readBackupFile(file, replace) {
    var rd = new FileReader();
    rd.onload = function () {
      var arr;
      try {
        var parsed = JSON.parse(rd.result);
        arr = Array.isArray(parsed) ? parsed : (parsed && Array.isArray(parsed.leases) ? parsed.leases : [parsed]);
      } catch (ex) { flash("That file is not a valid backup."); return; }
      var pre = replace
        ? Promise.all(portfolio.map(function (r) { return Store.del(r.id); }))
        : Promise.resolve();
      pre.then(function () {
        return Promise.all(arr.map(function (r) {
          return Store.put(Object.assign(blankCfg(), r, { id: r.id || uid() }));
        }));
      }).then(function () {
        loadPortfolio();
        flash((replace ? "Restored " : "Merged ") + arr.length + " lease record(s).");
      });
    };
    rd.readAsText(file);
  }
  function restoreBackup(ev) {
    var file = ev.target.files && ev.target.files[0]; ev.target.value = "";
    if (!file) return;
    var replace = portfolio.length
      ? window.confirm("Replace the " + portfolio.length + " record(s) currently stored?\n\nOK = replace everything, Cancel = merge into the existing portfolio.")
      : false;
    readBackupFile(file, replace);
  }
  function qStem() { return "IndAS116_" + (qObj ? qObj.label.replace(/[^A-Za-z0-9]+/g, "_") : "Quarter"); }

  function exportQuarterCSV() {
    if (!qRep) return;
    var T = qRep.T, rows = [];
    rows.push(["Ind AS 116 and Ind AS 12 quarterly lease report"]);
    rows.push(["Entity", entity]);
    rows.push(["Quarter", qObj.label, "From", fmtDate(qObj.start), "To", fmtDate(qObj.end)]);
    rows.push(["Balances as on", fmtDate(qRep.asOn), "Accrual basis", qBasis === "accrual" ? "Day weighted" : "Whole period"]);
    rows.push(["Leases included", qRep.lines.length, "Currency", S, "Deferred tax", T.dtOn ? "Recognised" : "Not enabled"]);
    rows.push([]);
    rows.push(["Lease identifier", "Lease name", "Lessor", "Asset class", "Borrowing rate percent",
      "Commencement", "Expiry", "Quarter interest", "Quarter depreciation", "Quarter provision unwinding",
      "Quarter modification gain", "Quarter charge before tax", "Quarter deferred tax income",
      "Quarter charge after tax", "Quarter cash outflow",
      "YTD interest", "YTD depreciation", "YTD charge before tax", "YTD deferred tax income",
      "YTD charge after tax", "YTD cash outflow",
      "Opening liability", "Additions", "Remeasurement", "Closing liability",
      "Opening ROU", "ROU additions", "ROU remeasurement", "Closing ROU",
      "Liability as on date", "Current", "Non current", "ROU as on date", "Restoration provision",
      "Opening net deferred tax", "Closing net deferred tax", "Liability movement check", "Deferred tax movement check"]);
    qRep.lines.forEach(function (L) {
      rows.push([L.id, L.name, L.lessor, L.cls, L.rate, fmtDate(L.start), fmtDate(L.end),
        r2(L.qInterest), r2(L.qDep), r2(L.qUnwind), r2(L.qModPL), r2(L.qExp), r2(L.qDtMove), r2(L.qExpNet), r2(L.qPmt),
        r2(L.yInterest), r2(L.yDep), r2(L.yExp), r2(L.yDtMove), r2(L.yExpNet), r2(L.yPmt),
        r2(L.openLiab), r2(L.addLiab), r2(L.modLiabAdj), r2(L.closeLiab),
        r2(L.openRou), r2(L.addRou), r2(L.modRouAdj), r2(L.closeRou),
        r2(L.onLiab), r2(L.current), r2(L.nonCurrent), r2(L.onRou), r2(L.onAro),
        r2(L.dtOpen), r2(L.dtClose), r2(L.tie), r2(L.tieDt)]);
    });
    rows.push(["TOTAL", "", "", "", "", "", "",
      r2(T.interest), r2(T.dep), r2(T.unwind), r2(T.modPL), r2(T.qExp), r2(T.dtMove), r2(T.qExpNet), r2(T.pmt),
      r2(T.ytdInterest), r2(T.ytdDep), r2(T.ytdExp), r2(T.ytdDtMove), r2(T.ytdExpNet), r2(T.ytdPmt),
      r2(T.openLiab), r2(T.addLiab), r2(T.modLiabAdj), r2(T.closeLiab),
      r2(T.openRou), r2(T.addRou), r2(T.modRouAdj), r2(T.closeRou),
      r2(T.closeLiab), r2(T.current), r2(T.nonCurrent), r2(T.closeRou), r2(T.aro),
      r2(T.dtOpen), r2(T.dtClose), r2(T.tie), r2(T.tieDt)]);
    rows.push([]);
    rows.push(["Journal register for the quarter"]);
    rows.push(["Lease identifier", "Lease name", "Asset class", "Posting date", "Account", "Debit", "Credit", "Narration"]);
    qRep.jr.forEach(function (j) { rows.push([j.id, j.name, j.cls, j.date, j.acc, j.dr || "", j.cr || "", j.nar]); });
    download(new Blob([toCSV(rows)], { type: "text/csv;charset=utf-8;" }), qStem() + "_Report.csv");
  }

  function exportQuarterXLS() {
    if (!qRep) return;
    var T = qRep.T, sheets = [];

    sheets.push({
      name: "Cover", freeze: 1, widths: [300, 150, 150],
      rows: [
        R([{ v: "Ind AS 116 and Ind AS 12 quarterly lease report", s: "t" }]), R([]),
        R([{ v: "Entity", s: "lbl" }, entity]),
        R([{ v: "Reporting quarter", s: "lbl" }, qObj.label]),
        R([{ v: "Quarter from", s: "lbl" }, fmtDate(qObj.start)]),
        R([{ v: "Quarter to", s: "lbl" }, fmtDate(qObj.end)]),
        R([{ v: "Balances as on", s: "lbl" }, fmtDate(qRep.asOn)]),
        R([{ v: "Year to date from", s: "lbl" }, fmtDate(qRep.ys)]),
        R([{ v: "Accrual basis", s: "lbl" }, qBasis === "accrual" ? "Day weighted across the quarter cut off" : "Whole monthly period allocated to the quarter of its start"]),
        R([{ v: "Number of leases", s: "lbl" }, qRep.lines.length]),
        R([{ v: "Reporting currency", s: "lbl" }, S]),
        R([{ v: "Deferred tax", s: "lbl" }, T.dtOn ? "Recognised under Ind AS 12, including para 22A" : "Module not enabled"]),
        R([{ v: "Generated on", s: "lbl" }, fmtDate(parseISO(new Date().toISOString().slice(0, 10)))]),
        R([]),
        R([{ v: "Amounts recognised in profit or loss", s: "t" }]),
        H(["Particulars", "Quarter", "Year to date"]),
        R(["Depreciation on right-of-use assets, para 53(a)", T.dep, T.ytdDep]),
        R(["Interest on lease liabilities, para 53(b)", T.interest, T.ytdInterest]),
        R(["Unwinding of restoration provisions, Ind AS 37", T.unwind, T.ytdUnwind]),
        R(["Gains on lease modifications, deduction", -T.modPL, -T.ytdModPL]),
        TOT(["Charge before tax", T.qExp, T.ytdExp]),
        R(["Deferred tax income, credit to profit or loss, Ind AS 12.58", -T.dtMove, -T.ytdDtMove]),
        TOT(["Net charge after deferred tax", T.qExpNet, T.ytdExpNet]),
        R(["Total cash outflow for leases, para 53(g)", T.pmt, T.ytdPmt]),
        R([]),
        R([{ v: "Balance sheet as on " + fmtDate(qRep.asOn), s: "t" }]),
        H(["Particulars", "Amount"]),
        R(["Right-of-use assets, net block", T.closeRou]),
        R(["Lease liabilities, current", T.current]),
        R(["Lease liabilities, non current", T.nonCurrent]),
        TOT(["Total lease liabilities", T.closeLiab]),
        R(["Provision for site restoration", T.aro]),
        R(["Net deferred tax asset, Ind AS 12.70 non current", T.dtClose]),
        R(["Weighted average incremental borrowing rate percent", T.wavg]),
        R([]),
        R([{ v: "Caution", s: "lbl" }, "Machine generated. Every figure requires professional review before use in financial statements. Interim income tax should also be tested against the estimated annual effective tax rate required by Ind AS 34.B12."])
      ]
    });

    var pl = [H(["Lease identifier", "Lease name", "Asset class", "Interest quarter", "Depreciation quarter",
      "Unwinding quarter", "Modification gain quarter", "Charge before tax quarter",
      "Deferred tax income quarter", "Charge after tax quarter", "Cash outflow quarter",
      "Interest YTD", "Depreciation YTD", "Charge before tax YTD", "Deferred tax income YTD",
      "Charge after tax YTD", "Cash outflow YTD"])];
    qRep.lines.forEach(function (L) {
      pl.push(R([L.id, L.name, L.cls, L.qInterest, L.qDep, L.qUnwind, L.qModPL, L.qExp,
        -L.qDtMove, L.qExpNet, L.qPmt, L.yInterest, L.yDep, L.yExp, -L.yDtMove, L.yExpNet, L.yPmt]));
    });
    pl.push(TOT(["TOTAL", "", "", T.interest, T.dep, T.unwind, T.modPL, T.qExp,
      -T.dtMove, T.qExpNet, T.pmt, T.ytdInterest, T.ytdDep, T.ytdExp, -T.ytdDtMove, T.ytdExpNet, T.ytdPmt]));
    sheets.push({ name: "Quarter P and L", freeze: 1, widths: [80, 180, 140], rows: pl });

    var bs = [H(["Lease identifier", "Lease name", "Opening liability", "Additions", "Remeasurement",
      "Interest", "Payments", "Closing liability", "Current", "Non current", "Opening ROU",
      "ROU additions", "ROU remeasurement", "Depreciation", "Closing ROU", "Restoration provision",
      "Opening net deferred tax", "Deferred tax movement", "Closing net deferred tax",
      "Liability check", "Deferred tax check"])];
    qRep.lines.forEach(function (L) {
      bs.push(R([L.id, L.name, L.openLiab, L.addLiab, L.modLiabAdj, L.qInterest, L.qPmt, L.closeLiab,
        L.current, L.nonCurrent, L.openRou, L.addRou, L.modRouAdj, L.qDep, L.closeRou, L.onAro,
        L.dtOpen, L.qDtMove, L.dtClose, L.tie, L.tieDt]));
    });
    bs.push(TOT(["TOTAL", "", T.openLiab, T.addLiab, T.modLiabAdj, T.interest, T.pmt, T.closeLiab,
      T.current, T.nonCurrent, T.openRou, T.addRou, T.modRouAdj, T.dep, T.closeRou, T.aro,
      T.dtOpen, T.dtMove, T.dtClose, T.tie, T.tieDt]));
    sheets.push({ name: "Balances", freeze: 1, widths: [80, 180], rows: bs });

    if (T.dtOn) {
      var dtRows = [
        R([{ v: "Deferred tax on leases, Ind AS 12", s: "t" }]),
        R([{ v: "Basis", s: "lbl" }, "Right-of-use asset gives a taxable temporary difference. Lease liability and restoration provision give deductible temporary differences. The initial recognition exemption does not apply, per the amended Ind AS 12.22A."]),
        R([]),
        H(["Particulars", "Quarter", "Year to date"]),
        R(["Origination and reversal of temporary differences, para 81(g)(ii)", -T.dtOrig, ""]),
        R(["Effect of changes in the enacted tax rate, para 81(d)", -T.dtRateEffect, ""]),
        TOT(["Deferred tax charge, credit, in profit or loss", -T.dtMove, -T.ytdDtMove]),
        R([]),
        H(["Movement in the net deferred tax balance", "Amount"]),
        R(["Opening balance", T.dtOpen]),
        R(["Recognised on new leases in the quarter, day one", T.dtDay1]),
        R(["Origination and reversal during the quarter", T.dtOrig - T.dtDay1]),
        R(["Effect of the change in tax rate", T.dtRateEffect]),
        TOT(["Closing balance", T.dtClose]),
        R(["Reconciliation difference, should be nil", T.tieDt]),
        R([]),
        H(["Lease identifier", "Lease name", "Tax treatment", "Rate percent", "Opening", "Movement", "Closing"])
      ];
      qRep.lines.forEach(function (L) {
        dtRows.push(R([L.id, L.name,
          L.dtTreat === "rentAccrual" ? "Rent deductible, nil tax base"
            : (L.dtTreat === "taxDep" ? "Tax depreciation on written down value" : "No temporary difference"),
          L.dtRate * 100, L.dtOpen, L.qDtMove, L.dtClose]));
      });
      dtRows.push(TOT(["TOTAL", "", "", "", T.dtOpen, T.dtMove, T.dtClose]));
      sheets.push({ name: "Deferred Tax", freeze: 1, widths: [300, 180, 240, 90, 120, 120, 120], rows: dtRows });
    }

    var jrRows = [H(["Lease identifier", "Lease name", "Asset class", "Posting date", "Account", "Debit", "Credit", "Narration"])];
    qRep.jr.forEach(function (j) { jrRows.push(R([j.id, j.name, j.cls, j.date, j.acc, j.dr || "", j.cr || "", j.nar])); });
    var jdr = qRep.jr.reduce(function (s, j) { return s + toNum(j.dr); }, 0);
    var jcr = qRep.jr.reduce(function (s, j) { return s + toNum(j.cr); }, 0);
    jrRows.push(TOT(["TOTAL", "", "", "", "", jdr, jcr, ""]));
    sheets.push({ name: "Journal Register", freeze: 1, widths: [80, 170, 130, 80, 300, 90, 90, 420], rows: jrRows });

    var cj = [H(["Particulars", "Debit", "Credit"])];
    qRep.consol.forEach(function (l) {
      if (Math.abs(toNum(l.dr) + toNum(l.cr)) < 0.005) return;
      cj.push(R([(l.cr ? "To " : "Dr. ") + l.acc, l.dr || "", l.cr || ""]));
    });
    cj.push(TOT(["Total",
      qRep.consol.reduce(function (s, l) { return s + toNum(l.dr); }, 0),
      qRep.consol.reduce(function (s, l) { return s + toNum(l.cr); }, 0)]));
    sheets.push({ name: "Consolidated JE", freeze: 1, widths: [430, 110, 110], rows: cj });

    var mt = [H(["Contractual maturity, undiscounted", "Amount"])];
    ["Not later than 1 year", "Later than 1 year and not later than 2 years",
     "Later than 2 years and not later than 3 years", "Later than 3 years and not later than 5 years",
     "Later than 5 years"].forEach(function (l, x) { mt.push(R([l, T.buckets[x]])); });
    mt.push(TOT(["Total undiscounted lease payments", T.gross]));
    mt.push(R(["Less future finance charges", -T.imputed]));
    mt.push(TOT(["Carrying amount of lease liabilities", T.closeLiab]));
    mt.push(R([]));
    mt.push(H(["Asset class", "Count", "Depreciation quarter", "Interest quarter", "ROU carrying amount", "Lease liability", "Net deferred tax"]));
    Object.keys(T.byClass).forEach(function (k) {
      var v = T.byClass[k];
      mt.push(R([k, v.n, v.dep, v.interest, v.nbv, v.liab, v.dt]));
    });
    sheets.push({ name: "Maturity and Class", freeze: 1, widths: [320, 100, 140, 130, 150, 130, 130], rows: mt });

    if (qRep.flags.length) {
      var fl = [H(["Review point"])];
      qRep.flags.forEach(function (f) { fl.push(R([f])); });
      sheets.push({ name: "Review Points", freeze: 1, widths: [760], rows: fl });
    }
    download(new Blob([buildWorkbook(sheets)], { type: "application/vnd.ms-excel;charset=utf-8;" }), qStem() + "_Report.xls");
  }

  function exportDtCSV() {
    if (!res || !res.dt.on) return;
    var rows = [["Deferred tax on leases, Ind AS 12"], ["Lease", cfg.name, "Identifier", cfg.id], []];
    rows.push(["Period", "Date", "FY", "ROU carrying", "ROU tax base", "Taxable TD",
      "Liability carrying", "Liability tax base", "Deductible TD", "Provision TD",
      "Net temporary difference", "Tax rate percent", "Deferred tax asset", "Deferred tax liability",
      "Net deferred tax", "Movement", "Origination", "Rate change effect", "Unrecognised"]);
    var d0 = res.dt.day1;
    rows.push([0, fmtDate(d0.date), fyKey(d0.date, res.fyBasis), r2(d0.rou), r2(d0.rouTB), r2(d0.tdRou),
      r2(d0.liab), r2(d0.liabTB), r2(d0.tdLiab), r2(d0.tdAro), r2(d0.netTd), r2(d0.rate * 100),
      r2(d0.dta), r2(d0.dtl), r2(d0.close), r2(d0.move), r2(d0.origination), r2(d0.rateEffect), r2(d0.unrec)]);
    res.dt.rows.forEach(function (d) {
      rows.push([d.k, fmtDate(d.date), d.fy, r2(d.rou), r2(d.rouTB), r2(d.tdRou),
        r2(d.liab), r2(d.liabTB), r2(d.tdLiab), r2(d.tdAro), r2(d.netTd), r2(d.rate * 100),
        r2(d.dta), r2(d.dtl), r2(d.close), r2(d.move), r2(d.origination), r2(d.rateEffect), r2(d.unrec)]);
    });
    download(new Blob([toCSV(rows)], { type: "text/csv;charset=utf-8;" }), "IndAS12_DeferredTax_" + cfg.id + ".csv");
  }

  var TABS = [["dash", "Dashboard"], ["sched", "Amortisation Schedule"], ["pmt", "Payment Grid"],
    ["mod", "Modifications"], ["dt", "Deferred Tax"], ["quarter", "Quarterly Report"],
    ["disc", "Annual Disclosures"], ["port", "Portfolio (" + portfolio.length + ")"]];
  var shortTerm = toNum(cfg.termMonths) <= 12;
  var dtOn = !!(res && res.dt && res.dt.on);
  var dtFy = null;
  if (dtOn && snap) res.dt.fyRows.forEach(function (g) { if (g.fy === snap.fy) dtFy = g; });

  return (
    <div className="min-h-screen">
      {/* HEADER */}
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1760px] flex-wrap items-center justify-between gap-3 px-5 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 text-[10px] font-black leading-none text-white shadow-lg">
              <span>116<br />+12</span>
            </div>
            <div>
              <h1 className="flex items-center gap-2 text-sm font-bold leading-tight text-white">
                Lease Accounting Engine
                <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-[9px] font-bold text-indigo-300">V4</span>
              </h1>
              <p className="text-[10.5px] text-slate-400">Ind AS 116 measurement with Ind AS 12 deferred tax, quarterly reporting and portfolio disclosures</p>
            </div>
          </div>
          <div className="no-print flex flex-wrap items-center gap-2">
            <button onClick={brandNew} className="rounded-lg border border-slate-700 px-3 py-2 text-[11px] font-bold text-slate-200 hover:bg-slate-800">New Lease</button>
            <button onClick={saveLease} className="rounded-lg bg-emerald-600 px-3 py-2 text-[11px] font-bold text-white hover:bg-emerald-700">Save to Portfolio</button>
            <button onClick={function () { setTab("dt"); }} className="rounded-lg bg-violet-600 px-3 py-2 text-[11px] font-bold text-white hover:bg-violet-700">Deferred Tax</button>
            <button onClick={function () { setTab("quarter"); }} className="rounded-lg bg-indigo-600 px-3 py-2 text-[11px] font-bold text-white hover:bg-indigo-700">Quarterly Report</button>
            <button onClick={exportScheduleCSV} disabled={!res} className="rounded-lg border border-slate-700 px-3 py-2 text-[11px] font-bold text-slate-200 hover:bg-slate-800 disabled:opacity-40">Schedule CSV</button>
            <button onClick={function () { window.print(); }} disabled={!res} className="rounded-lg border border-slate-700 px-3 py-2 text-[11px] font-bold text-slate-200 hover:bg-slate-800 disabled:opacity-40">Print</button>
          </div>
        </div>
        {toast ? <div className="bg-emerald-600 px-5 py-1.5 text-center text-[11px] font-semibold text-white">{toast}</div> : null}
        {fatal ? <div className="bg-rose-600 px-5 py-1.5 text-center text-[11px] font-semibold text-white">Calculation error: {fatal}</div> : null}
      </header>

      <main className="mx-auto grid max-w-[1760px] grid-cols-12 gap-5 px-5 py-5">
        {/* SIDEBAR */}
        <aside className="no-print col-span-12 xl:col-span-3">
          <div className="sticky top-[76px] max-h-[calc(100vh-96px)] overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 bg-slate-50 px-5 py-3">
              <h2 className="text-xs font-bold text-slate-800">Lease Master Data</h2>
              <p className="text-[10px] text-slate-500">Contract identifier <span className="font-mono font-semibold">{cfg.id}</span></p>
              {cfg.sourceDoc ? <p className="mt-0.5 text-[10px] text-indigo-600">Source document: {cfg.sourceDoc}</p> : null}
            </div>

            <Section title="1 - Identification" open={true}>
              <Field label="Lease or asset description"><input value={cfg.name} onChange={upd("name")} className={inputCls} /></Field>
              <Field label="Lessor"><input value={cfg.lessor} onChange={upd("lessor")} className={inputCls} /></Field>
              <Field label="Class of underlying asset" hint="Drives the disclosure by class under para 53(a) and 53(j).">
                <select value={cfg.assetClass} onChange={upd("assetClass")} className={inputCls}>
                  {ASSET_CLASSES.map(function (v) { return <option key={v} value={v}>{v}</option>; })}
                </select>
              </Field>
            </Section>

            <Section title="2 - Core Lease Terms" badge="Para 26" open={true}>
              <Field label="Lease commencement date" error={errs.startDate}>
                <input type="date" value={cfg.startDate} onChange={upd("startDate")} className={inputCls} />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Tenure in months" error={errs.termMonths}>
                  <input type="number" value={cfg.termMonths} onChange={upd("termMonths")} className={inputCls} />
                </Field>
                <Field label={"Base rent per month, " + S} error={errs.basePayment}>
                  <input type="number" value={cfg.basePayment} onChange={upd("basePayment")} className={inputCls} />
                </Field>
              </div>
              <Field label="Incremental borrowing rate, annual percent" error={errs.rate}>
                <input type="number" step="0.01" value={cfg.rate} onChange={upd("rate")} className={inputCls} />
              </Field>
              <Field label="Payment timing">
                <select value={cfg.timing} onChange={upd("timing")} className={inputCls}>
                  <option value="begin">Beginning of month, in advance</option>
                  <option value="end">End of month, in arrears</option>
                </select>
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Rate basis">
                  <select value={cfg.rateBasis} onChange={upd("rateBasis")} className={inputCls}>
                    <option value="simple">Nominal divided by 12</option>
                    <option value="effective">Effective</option>
                  </select>
                </Field>
                <Field label="Day one basis">
                  <select value={cfg.day1Basis} onChange={upd("day1Basis")} className={inputCls} disabled={cfg.timing !== "begin"}>
                    <option value="market">Market practice</option>
                    <option value="strict">Strict para 26</option>
                  </select>
                </Field>
              </div>
            </Section>

            <Section title="3 - Escalation and Rent Free Periods">
              <Field label="Escalation type">
                <select value={cfg.escMode} onChange={upd("escMode")} className={inputCls}>
                  <option value="none">None, flat rent</option>
                  <option value="percent">Fixed percentage step up</option>
                  <option value="amount">Fixed amount step up</option>
                </select>
              </Field>
              {cfg.escMode !== "none" ? (
                <div className="grid grid-cols-2 gap-3">
                  <Field label={cfg.escMode === "percent" ? "Step up percent" : "Step up amount"}>
                    <input type="number" step="0.01" value={cfg.escMode === "percent" ? cfg.escPct : cfg.escAmt}
                      onChange={upd(cfg.escMode === "percent" ? "escPct" : "escAmt")} className={inputCls} />
                  </Field>
                  <Field label="Every, months"><input type="number" value={cfg.escFreq} onChange={upd("escFreq")} className={inputCls} /></Field>
                </div>
              ) : null}
              <div className="grid grid-cols-2 gap-3">
                <Field label="Rent free months" error={errs.rentFreeMonths}>
                  <input type="number" value={cfg.rentFreeMonths} onChange={upd("rentFreeMonths")} className={inputCls} />
                </Field>
                <Field label="Position">
                  <select value={cfg.rentFreePos} onChange={upd("rentFreePos")} className={inputCls}>
                    <option value="start">At start, fit out</option>
                    <option value="end">At end</option>
                  </select>
                </Field>
              </div>
              <Field label="Additional rent free periods" hint="Comma separated period numbers.">
                <input value={cfg.rentFreeList} onChange={upd("rentFreeList")} placeholder="13, 25" className={inputCls} />
              </Field>
            </Section>

            <Section title="4 - ROU Asset Cost Build Up" badge="Para 24">
              <Field label={"Initial direct costs, " + S} hint="Brokerage, stamp duty, registration, para 24(c).">
                <input type="number" value={cfg.idc} onChange={upd("idc")} className={inputCls} />
              </Field>
              <Field label={"Prepaid lease payments, " + S}><input type="number" value={cfg.prepaid} onChange={upd("prepaid")} className={inputCls} /></Field>
              <Field label={"Lease incentives received, " + S}><input type="number" value={cfg.incentive} onChange={upd("incentive")} className={inputCls} /></Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Restoration cost, undiscounted"><input type="number" value={cfg.aroCost} onChange={upd("aroCost")} className={inputCls} /></Field>
                <Field label="Restoration discount rate percent"><input type="number" step="0.01" value={cfg.aroRate} onChange={upd("aroRate")} className={inputCls} /></Field>
              </div>
              <Field label={"Security deposit, " + S} hint="A financial asset under Ind AS 109, not a lease payment.">
                <input type="number" value={cfg.securityDeposit} onChange={upd("securityDeposit")} className={inputCls} />
              </Field>
              {toNum(cfg.securityDeposit) > 0 ? (
                <button onClick={depositAdjust} className="w-full rounded-lg border border-sky-300 bg-sky-50 px-3 py-2 text-[11px] font-bold text-sky-800 hover:bg-sky-100">
                  Compute the Ind AS 109 discount and add it to prepaid rent
                </button>
              ) : null}
            </Section>

            <Section title="5 - Depreciation Policy" badge="Para 32">
              <label className="flex items-start gap-2.5 rounded-lg bg-slate-50 p-3">
                <input type="checkbox" checked={!!cfg.transferOwnership} onChange={upd("transferOwnership")} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600" />
                <span className="text-[11.5px] font-semibold leading-snug text-slate-700">Lease transfers ownership, or a purchase option is reasonably certain</span>
              </label>
              <Field label="Useful life of the asset in months" hint="Zero means depreciate over the lease term.">
                <input type="number" value={cfg.usefulLifeMonths} onChange={upd("usefulLifeMonths")} className={inputCls} />
              </Field>
            </Section>

            {/* ---- NEW SECTION: DEFERRED TAX ---- */}
            <Section title="6 - Deferred Tax" badge="Ind AS 12" open={true}>
              <label className="flex items-start gap-2.5 rounded-lg bg-violet-50 p-3">
                <input type="checkbox" checked={!!cfg.dtOn} onChange={upd("dtOn")} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-violet-600" />
                <span className="text-[11.5px] font-semibold leading-snug text-violet-900">Recognise deferred tax on the lease temporary differences</span>
              </label>
              {cfg.dtOn ? (
                <React.Fragment>
                  <Field label="Applicable tax rate, percent" error={errs.dtRate}
                    hint="India, section 115BAA: 22 percent plus 10 percent surcharge plus 4 percent cess gives 25.168 percent. Use the rate expected to apply on reversal, per Ind AS 12.47.">
                    <input type="number" step="0.001" value={cfg.dtRate} onChange={upd("dtRate")} className={inputCls} />
                  </Field>

                  <Field label="Tax treatment of the lease" hint="Determines the tax base of the right-of-use asset and the lease liability.">
                    <select value={cfg.dtTreatment} onChange={upd("dtTreatment")} className={inputCls}>
                      {DT_TREATMENTS.map(function (t) { return <option key={t[0]} value={t[0]}>{t[1]}</option>; })}
                    </select>
                  </Field>

                  {cfg.dtTreatment === "taxDep" ? (
                    <div className="grid grid-cols-2 gap-3">
                      <Field label="Tax depreciation method">
                        <select value={cfg.dtTaxDepMethod} onChange={upd("dtTaxDepMethod")} className={inputCls}>
                          <option value="wdv">Written down value</option>
                          <option value="slm">Straight line</option>
                        </select>
                      </Field>
                      {cfg.dtTaxDepMethod === "wdv" ? (
                        <Field label="Annual block rate percent"><input type="number" step="0.01" value={cfg.dtTaxDepRate} onChange={upd("dtTaxDepRate")} className={inputCls} /></Field>
                      ) : (
                        <Field label="Tax life in months"><input type="number" value={cfg.dtTaxLifeMonths} onChange={upd("dtTaxLifeMonths")} className={inputCls} /></Field>
                      )}
                    </div>
                  ) : null}

                  <label className="flex items-start gap-2.5 rounded-lg bg-slate-50 p-3">
                    <input type="checkbox" checked={cfg.dtIncludeAro !== false} onChange={upd("dtIncludeAro")} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-violet-600" />
                    <span className="text-[11.5px] font-semibold leading-snug text-slate-700">Include the restoration provision, deductible only when the cost is incurred</span>
                  </label>

                  <Field label="Presentation" hint="Both give the same net figure. Gross shows the components required by para 81(g).">
                    <select value={cfg.dtApproach} onChange={upd("dtApproach")} className={inputCls}>
                      <option value="gross">Gross, separate asset and liability components</option>
                      <option value="net">Net, single temporary difference</option>
                    </select>
                  </Field>

                  <label className="flex items-start gap-2.5 rounded-lg bg-slate-50 p-3">
                    <input type="checkbox" checked={cfg.dtOffset !== false} onChange={upd("dtOffset")} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-violet-600" />
                    <span className="text-[11.5px] font-semibold leading-snug text-slate-700">Offset in the balance sheet, the para 74 conditions are met</span>
                  </label>

                  <label className="flex items-start gap-2.5 rounded-lg bg-amber-50 p-3">
                    <input type="checkbox" checked={!!cfg.dtRestrict} onChange={upd("dtRestrict")} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-amber-600" />
                    <span className="text-[11.5px] font-semibold leading-snug text-amber-900">Restrict the deferred tax asset, sufficient future taxable profit is not probable</span>
                  </label>
                  {cfg.dtRestrict ? (
                    <Field label="Proportion recognised, percent" error={errs.dtRecognisePct}
                      hint="Ind AS 12.24 and 12.27. Any unrecognised amount is disclosed under para 81(e).">
                      <input type="number" step="1" value={cfg.dtRecognisePct} onChange={upd("dtRecognisePct")} className={inputCls} />
                    </Field>
                  ) : null}

                  <div className="rounded-lg border border-slate-200 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10.5px] font-bold uppercase tracking-wider text-slate-600">Enacted rate changes</span>
                      <button onClick={function () {
                        setCfg(function (p) {
                          return Object.assign({}, p, { dtRateSchedule: (p.dtRateSchedule || []).concat([{ id: uid(), enabled: true, from: "", rate: 22 }]) });
                        });
                      }} className="rounded bg-slate-900 px-2 py-1 text-[10px] font-bold text-white">Add</button>
                    </div>
                    {errs.dtRateSchedule ? <p className="mt-1 text-[10.5px] font-semibold text-rose-600">{errs.dtRateSchedule}</p> : null}
                    {!(cfg.dtRateSchedule || []).length ? (
                      <p className="mt-2 text-[10.5px] leading-snug text-slate-400">
                        No future rate change. Add one to model a rate enacted or substantively enacted by the reporting date,
                        as required by Ind AS 12.47. The remeasurement of the opening balance goes to profit or loss under para 60.
                      </p>
                    ) : (
                      <div className="mt-2 space-y-2">
                        {cfg.dtRateSchedule.map(function (s, x) {
                          function sset(k, v) {
                            setCfg(function (p) {
                              var arr = p.dtRateSchedule.slice();
                              arr[x] = Object.assign({}, arr[x]); arr[x][k] = v;
                              return Object.assign({}, p, { dtRateSchedule: arr });
                            });
                          }
                          return (
                            <div key={s.id} className="flex items-center gap-1.5">
                              <input type="checkbox" checked={s.enabled !== false} onChange={function (e) { sset("enabled", e.target.checked); }}
                                className="h-3.5 w-3.5 rounded border-slate-300 text-violet-600" />
                              <input type="date" value={s.from} onChange={function (e) { sset("from", e.target.value); }}
                                className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-[11px]" />
                              <input type="number" step="0.001" value={s.rate} onChange={function (e) { sset("rate", e.target.value); }}
                                className={miniCls + " w-20"} />
                              <button onClick={function () {
                                setCfg(function (p) {
                                  return Object.assign({}, p, { dtRateSchedule: p.dtRateSchedule.filter(function (_, j) { return j !== x; }) });
                                });
                              }} className="text-[10px] font-bold text-rose-600">Remove</button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </React.Fragment>
              ) : null}
            </Section>

            <Section title="7 - Reporting and Disclosure Add Ons" badge="Para 53">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Financial year convention">
                  <select value={cfg.fyBasis} onChange={upd("fyBasis")} className={inputCls}>
                    <option value="mar">April to March, India</option>
                    <option value="dec">January to December</option>
                  </select>
                </Field>
                <Field label="Currency">
                  <select value={cfg.symbol} onChange={upd("symbol")} className={inputCls}>
                    <option value="\u20B9">{"\u20B9 Rupee"}</option>
                    <option value="$">$ Dollar</option>
                    <option value="\u20AC">{"\u20AC Euro"}</option>
                    <option value="\u00A3">{"\u00A3 Pound"}</option>
                    <option value="AED ">AED Dirham</option>
                  </select>
                </Field>
              </div>
              <Field label="Annual reporting date"><input type="date" value={cfg.reportingDate} onChange={upd("reportingDate")} className={inputCls} /></Field>
              <Field label="Short term lease expense" tag="53(c)"><input type="number" value={cfg.shortTermExp} onChange={upd("shortTermExp")} className={inputCls} /></Field>
              <Field label="Low value asset expense" tag="53(d)"><input type="number" value={cfg.lowValueExp} onChange={upd("lowValueExp")} className={inputCls} /></Field>
              <Field label="Variable lease payments" tag="53(e)"><input type="number" value={cfg.variableExp} onChange={upd("variableExp")} className={inputCls} /></Field>
              <Field label="Sublease income" tag="53(f)"><input type="number" value={cfg.subleaseIncome} onChange={upd("subleaseIncome")} className={inputCls} /></Field>
            </Section>

            <div className="sticky bottom-0 flex gap-2 border-t border-slate-200 bg-white/95 px-5 py-4 backdrop-blur">
              <button onClick={function () { run(cfg, true); }}
                className="flex-1 rounded-lg bg-indigo-600 px-4 py-3 text-xs font-bold text-white shadow-sm transition hover:bg-indigo-700 active:scale-[0.99]">
                Calculate Schedule
              </button>
              <button onClick={function () { setRes(null); setErrs({}); setFatal(""); }}
                className="rounded-lg border border-slate-300 px-3 py-3 text-xs font-bold text-slate-600 hover:bg-slate-50">Clear</button>
            </div>
          </div>
        </aside>

        {/* OUTPUT */}
        <section ref={outRef} className="print-full col-span-12 xl:col-span-9">
          <div className="no-print mb-5 flex flex-wrap gap-1 rounded-xl border border-slate-200 bg-white p-1.5 shadow-sm">
            {TABS.map(function (t) {
              return (
                <button key={t[0]} onClick={function () { setTab(t[0]); }}
                  className={"rounded-lg px-3.5 py-2 text-[11.5px] font-bold transition " +
                    (tab === t[0] ? (t[0] === "dt" ? "bg-violet-700 text-white shadow" : "bg-slate-900 text-white shadow")
                                  : "text-slate-500 hover:bg-slate-100 hover:text-slate-700")}>
                  {t[1]}
                </button>
              );
            })}
          </div>

          {/* ============ DEFERRED TAX TAB ============ */}
          {tab === "dt" ? (
            !res ? (
              <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white/60 p-10 text-center">
                <p className="text-sm font-bold text-slate-700">Calculate the lease first</p>
              </div>
            ) : !dtOn ? (
              <div className="rounded-xl border-2 border-dashed border-violet-300 bg-violet-50/50 p-10 text-center">
                <p className="text-sm font-bold text-violet-900">The deferred tax module is switched off</p>
                <p className="mx-auto mt-2 max-w-lg text-[11.5px] leading-relaxed text-violet-800">
                  Enable it in sidebar section six. Recognition is not optional in most fact patterns. The amended
                  Ind AS 12 para 22A removes the initial recognition exemption for leases and decommissioning
                  obligations, so a lessee that capitalises a right-of-use asset and recognises a lease liability with
                  nil tax bases must recognise the resulting deferred tax.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* cards */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <Card tone="violet" symbol={S}
                    label={snap ? "Net deferred tax as on " + fmtDate(snap.asAt) : "Net deferred tax"}
                    value={br(snap ? snap.dt : res.dt.closing)}
                    sub={(snap ? snap.dt : 0) >= 0 ? "Net deferred tax asset, presented as non current under para 70" : "Net deferred tax liability, presented as non current under para 70"}
                    foot={"Peak net asset over the lease " + S + money(res.dt.peak)} />
                  <Card tone="emerald" symbol={S} label={"Deferred tax income for " + (snap ? snap.fy : "the year")}
                    value={br(dtFy ? dtFy.move : 0)}
                    sub="Positive is a credit to profit or loss, reducing the total tax charge"
                    foot={dtFy && Math.abs(dtFy.rateEffect) > 0.005 ? "Includes " + S + br(dtFy.rateEffect) + " from the rate change" : "No rate change effect in this year"} />
                  <Card tone="sky" label="Applicable tax rate"
                    value={pctS(res.dt.finalRate, 3)}
                    sub={"Day one rate " + pctS(res.dt.day1Rate, 3) + (res.dt.rateChanges ? ", changed during the term" : ", constant across the term")}
                    foot={res.dt.treat === "rentAccrual" ? "Rentals deductible, nil tax bases"
                      : (res.dt.treat === "taxDep" ? "Tax depreciation on written down value" : "No temporary difference")} />
                  <Card tone="amber" symbol={S} label="Day one deferred tax recognised"
                    value={br(res.dt.day1.move)}
                    sub="Recognised because Ind AS 12.22A withdraws the initial recognition exemption for leases"
                    foot={"Driven by incentives of " + S + money(res.build.incentive) + " less costs of " + S + money(res.build.idc + res.build.prepaid)} />
                </div>

                <TrendChart rows={res.rows} symbol={S} showDt={true} />

                {/* temporary difference computation at reporting date */}
                {snap ? (function () {
                  var pick = null;
                  res.rows.forEach(function (r) { if (cmpD(r.pEnd, snap.asAt) <= 0) pick = r; });
                  var d = pick && pick.dt ? pick.dt : res.dt.day1;
                  var gross = cfg.dtApproach === "gross";
                  return (
                    <div className="overflow-hidden rounded-xl border border-violet-200 bg-white shadow-sm">
                      <div className="border-b border-violet-100 bg-violet-50/60 px-5 py-3">
                        <h4 className="text-xs font-bold text-violet-900">
                          {"Computation of Temporary Differences as on " + fmtDate(d.date) + ", Ind AS 12.5 and 12.15"}
                        </h4>
                        <p className="text-[10.5px] text-violet-700">
                          {gross ? "Gross presentation, showing each component separately as required for the para 81(g) disclosure."
                                 : "Net presentation, treating the lease as a single integrated transaction."}
                        </p>
                      </div>
                      <table className="w-full text-xs">
                        <thead className="bg-slate-100 text-slate-600">
                          <tr><Th>Item</Th><Th right>Carrying amount</Th><Th right>Tax base</Th>
                            <Th right>Temporary difference</Th><Th center>Nature</Th><Th right>Deferred tax</Th></tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          <tr>
                            <Td cls="font-semibold text-slate-800">Right-of-use asset</Td>
                            <Td right>{money(d.rou)}</Td><Td right>{money(d.rouTB)}</Td>
                            <Td right>{money(d.tdRou)}</Td>
                            <Td center><span className="rounded bg-rose-100 px-1.5 py-0.5 text-[9.5px] font-bold text-rose-700">TAXABLE</span></Td>
                            <Td right cls="font-semibold text-rose-700">{"(" + money(d.tdRou * d.rate) + ")"}</Td>
                          </tr>
                          <tr className="bg-slate-50/60">
                            <Td cls="font-semibold text-slate-800">Lease liability</Td>
                            <Td right>{money(d.liab)}</Td><Td right>{money(d.liabTB)}</Td>
                            <Td right>{money(d.tdLiab)}</Td>
                            <Td center><span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[9.5px] font-bold text-emerald-700">DEDUCTIBLE</span></Td>
                            <Td right cls="font-semibold text-emerald-700">{money(d.tdLiab * d.rate)}</Td>
                          </tr>
                          {res.dt.incAro ? (
                            <tr>
                              <Td cls="font-semibold text-slate-800">Provision for site restoration</Td>
                              <Td right>{money(d.aro)}</Td><Td right>{money(0)}</Td>
                              <Td right>{money(d.tdAro)}</Td>
                              <Td center><span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[9.5px] font-bold text-emerald-700">DEDUCTIBLE</span></Td>
                              <Td right cls="font-semibold text-emerald-700">{money(d.tdAro * d.rate)}</Td>
                            </tr>
                          ) : null}
                          <tr className="bg-slate-100 font-bold">
                            <Td>Net temporary difference</Td><Td right>{"\u2014"}</Td><Td right>{"\u2014"}</Td>
                            <Td right>{money(d.netTdFull)}</Td>
                            <Td center><span className="text-[9.5px] uppercase text-slate-600">{"at " + pctS(d.rate, 3)}</span></Td>
                            <Td right>{br(d.netTdFull * d.rate)}</Td>
                          </tr>
                          {d.unrec > 0.005 ? (
                            <tr className="bg-amber-50">
                              <Td cls="font-semibold text-amber-900">Less, asset not recognised because taxable profit is not probable, para 81(e)</Td>
                              <Td right>{"\u2014"}</Td><Td right>{"\u2014"}</Td><Td right>{"\u2014"}</Td><Td center>{"\u2014"}</Td>
                              <Td right cls="font-bold text-amber-800">{"(" + money(d.unrec) + ")"}</Td>
                            </tr>
                          ) : null}
                          <tr className="bg-violet-700 font-bold text-white">
                            <Td>{d.net >= 0 ? "Net deferred tax asset recognised" : "Net deferred tax liability recognised"}</Td>
                            <Td right>{"\u2014"}</Td><Td right>{"\u2014"}</Td><Td right>{"\u2014"}</Td><Td center>{"\u2014"}</Td>
                            <Td right>{br(d.net)}</Td>
                          </tr>
                        </tbody>
                      </table>
                      <div className="border-t border-slate-100 bg-slate-50 px-5 py-3 text-[10.5px] leading-relaxed text-slate-600">
                        {cfg.dtOffset !== false
                          ? "Presented as a single net amount because the entity has a legally enforceable right to set off current tax assets against current tax liabilities and the balances relate to income taxes levied by the same taxation authority, satisfying Ind AS 12.74."
                          : "Presented gross because the offsetting conditions in Ind AS 12.74 are not met. The deferred tax asset of " + S + money(d.dta) + " and the deferred tax liability of " + S + money(d.dtl) + " are shown separately."}
                      </div>
                    </div>
                  );
                })() : null}

                {/* journal entries */}
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <JE symbol={S} tone="violet" tag="Ind AS 12.22A"
                    title={"Day One Deferred Tax Entry, " + fmtDate(res.dt.day1.date)}
                    narration="Being recognition of deferred tax on the temporary differences arising on initial recognition of the right-of-use asset, the lease liability and the restoration provision. The initial recognition exemption in Ind AS 12.15 and 12.24 does not apply, following the amendment inserting para 22A for transactions that give rise to equal and offsetting temporary differences"
                    lines={[
                      { acc: "Deferred Tax Asset", dr: Math.max(res.dt.day1.move, 0) },
                      { acc: "Deferred Tax - credit to the statement of profit and loss", cr: Math.max(res.dt.day1.move, 0) },
                      { acc: "Deferred Tax - charge to the statement of profit and loss", dr: Math.max(-res.dt.day1.move, 0) },
                      { acc: "Deferred Tax Liability", cr: Math.max(-res.dt.day1.move, 0) }
                    ]} />
                  {dtFy ? (
                    <JE symbol={S} tone="violet" tag={"Annual, " + dtFy.fy}
                      title={"Deferred Tax Entry for " + dtFy.fy}
                      narration={"Being the deferred tax movement for the year on lease temporary differences, comprising origination and reversal of " +
                        S + br(dtFy.origination) + " and the effect of the change in the enacted tax rate of " + S + br(dtFy.rateEffect) +
                        ", recognised in profit or loss under Ind AS 12.58 and 12.60"}
                      lines={[
                        { acc: "Deferred Tax Asset", dr: Math.max(dtFy.move, 0) },
                        { acc: "Deferred Tax - credit to the statement of profit and loss", cr: Math.max(dtFy.move, 0) },
                        { acc: "Deferred Tax - charge to the statement of profit and loss", dr: Math.max(-dtFy.move, 0) },
                        { acc: "Deferred Tax Asset - reversal", cr: Math.max(-dtFy.move, 0) }
                      ]} />
                  ) : null}
                </div>

                {/* movement schedule */}
                <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                    <div>
                      <h4 className="text-xs font-bold text-slate-800">Movement in the Net Deferred Tax Balance</h4>
                      <p className="text-[10.5px] text-slate-500">
                        The movement is decomposed into origination and reversal measured at the current rate, and the effect
                        of remeasuring the opening balance for a change in the enacted rate, as required by para 81(d).
                      </p>
                    </div>
                    <div className="no-print flex items-center gap-2">
                      <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1">
                        {[["fy", "Financial year"], ["monthly", "Monthly"]].map(function (v) {
                          return (
                            <button key={v[0]} onClick={function () { setDtView(v[0]); }}
                              className={"rounded-md px-3 py-1.5 text-[11px] font-bold transition " + (dtView === v[0] ? "bg-white text-violet-700 shadow-sm" : "text-slate-500")}>
                              {v[1]}
                            </button>
                          );
                        })}
                      </div>
                      <button onClick={exportDtCSV} className="rounded-lg border border-slate-300 px-3 py-1.5 text-[11px] font-bold text-slate-600 hover:bg-slate-50">Export CSV</button>
                    </div>
                  </div>

                  {dtView === "fy" ? (
                    <div className="overflow-auto">
                      <table className="w-full min-w-[900px] text-xs">
                        <thead className="bg-slate-800 text-white">
                          <tr><Th>Financial year</Th><Th right>Opening balance</Th><Th right>Origination and reversal</Th>
                            <Th right>Rate change effect</Th><Th right>Total credit to profit or loss</Th>
                            <Th right>Closing balance</Th><Th right>Gross asset</Th><Th right>Gross liability</Th><Th center>Rate</Th></tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {res.dt.fyRows.map(function (g, x) {
                            return (
                              <tr key={g.fy} className="odd:bg-white even:bg-slate-50/70 hover:bg-violet-50/60">
                                <Td cls="font-semibold text-slate-700">{g.fy}</Td>
                                <Td right>{br(x === 0 ? 0 : res.dt.fyRows[x - 1].close)}</Td>
                                <Td right cls="text-emerald-700">{br(g.origination)}</Td>
                                <Td right cls={Math.abs(g.rateEffect) > 0.005 ? "font-bold text-amber-700" : "text-slate-300"}>
                                  {Math.abs(g.rateEffect) > 0.005 ? br(g.rateEffect) : "\u2014"}
                                </Td>
                                <Td right cls="font-bold text-slate-900">{br(g.move)}</Td>
                                <Td right cls="font-semibold text-violet-700">{br(g.close)}</Td>
                                <Td right cls="text-slate-500">{money(g.dta)}</Td>
                                <Td right cls="text-slate-500">{money(g.dtl)}</Td>
                                <Td center cls="text-[10px] text-slate-500">{pctS(g.rate, 2)}</Td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot className="bg-slate-100 font-bold">
                          <tr>
                            <td className="px-3 py-3 text-[10px] uppercase tracking-wider">Total over the lease</td>
                            <Td right>0.00</Td>
                            <Td right>{br(res.dt.totals.origination)}</Td>
                            <Td right>{br(res.dt.totals.rateEffect)}</Td>
                            <Td right>{br(res.dt.totals.move)}</Td>
                            <Td right>{br(res.dt.closing)}</Td>
                            <Td right>{money(res.dt.closingDta)}</Td>
                            <Td right>{money(res.dt.closingDtl)}</Td>
                            <Td center>{"\u2014"}</Td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  ) : (
                    <div className="scroll-box max-h-[560px] overflow-auto">
                      <table className="w-full min-w-[1220px] text-xs">
                        <thead className="sticky top-0 z-10 bg-slate-800 text-white">
                          <tr><Th>No</Th><Th>Date</Th><Th right>ROU carrying</Th><Th right>ROU tax base</Th>
                            <Th right>Liability carrying</Th><Th right>Provision</Th><Th right>Net temporary difference</Th>
                            <Th center>Rate</Th><Th right>Opening</Th><Th right>Movement</Th>
                            <Th right>Rate effect</Th><Th right>Closing</Th></tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          <tr className="bg-violet-50 font-semibold">
                            <Td cls="num text-violet-400">0</Td>
                            <Td cls="num text-violet-700">{fmtDate(res.dt.day1.date)}</Td>
                            <Td right>{money(res.dt.day1.rou)}</Td>
                            <Td right>{money(res.dt.day1.rouTB)}</Td>
                            <Td right>{money(res.dt.day1.liab)}</Td>
                            <Td right>{money(res.dt.day1.tdAro)}</Td>
                            <Td right>{money(res.dt.day1.netTd)}</Td>
                            <Td center cls="text-[10px]">{pctS(res.dt.day1.rate, 2)}</Td>
                            <Td right>0.00</Td>
                            <Td right cls="font-bold text-violet-700">{br(res.dt.day1.move)}</Td>
                            <Td right cls="text-slate-300">{"\u2014"}</Td>
                            <Td right cls="font-bold text-violet-700">{br(res.dt.day1.close)}</Td>
                          </tr>
                          {res.dt.rows.map(function (d) {
                            return (
                              <tr key={d.k} className={d.rateChanged ? "bg-amber-50" : "odd:bg-white even:bg-slate-50/70 hover:bg-violet-50/50"}>
                                <Td cls="num text-slate-400">{d.k}</Td>
                                <Td cls="num text-slate-500">{fmtDate(d.date)}</Td>
                                <Td right>{money(d.rou)}</Td>
                                <Td right cls="text-slate-500">{money(d.rouTB)}</Td>
                                <Td right>{money(d.liab)}</Td>
                                <Td right cls="text-slate-500">{money(d.tdAro)}</Td>
                                <Td right cls="font-semibold">{money(d.netTd)}</Td>
                                <Td center cls={d.rateChanged ? "text-[10px] font-bold text-amber-700" : "text-[10px] text-slate-400"}>{pctS(d.rate, 2)}</Td>
                                <Td right cls="text-slate-500">{br(d.open)}</Td>
                                <Td right cls={d.move >= 0 ? "text-emerald-700" : "text-rose-700"}>{br(d.move)}</Td>
                                <Td right cls={Math.abs(d.rateEffect) > 0.005 ? "font-bold text-amber-700" : "text-slate-300"}>
                                  {Math.abs(d.rateEffect) > 0.005 ? br(d.rateEffect) : "\u2014"}
                                </Td>
                                <Td right cls="font-semibold text-violet-700">{br(d.close)}</Td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* proof and disclosure */}
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-5">
                    <h4 className="text-xs font-bold text-emerald-900">Proof that the Temporary Difference Reverses</h4>
                    <dl className="mt-3 space-y-2 text-xs">
                      {[["Cumulative book charge, depreciation plus interest", res.totals.dep + res.totals.interest, 0],
                        ["Cumulative tax deduction, contractual rentals", res.totals.payments, 0],
                        ["Cumulative difference, which must be nil over the term",
                          (res.totals.dep + res.totals.interest) - res.totals.payments, 1],
                        ["Deferred tax recognised over the term at the applicable rate", res.dt.totals.move, 1],
                        ["Closing net deferred tax balance at expiry", res.dt.closing, 2]].map(function (r, x) {
                        var cls = r[2] === 2 ? "border-t-2 border-emerald-300 pt-2 text-[13px] font-bold text-emerald-900"
                          : (r[2] === 1 ? "border-t border-emerald-200 pt-2 font-semibold text-emerald-900" : "text-emerald-800");
                        return <div key={x} className={"flex justify-between gap-4 " + cls}><dt>{r[0]}</dt><dd className="num">{S}{br(r[1])}</dd></div>;
                      })}
                    </dl>
                    <p className="mt-3 text-[10.5px] leading-relaxed text-emerald-700">
                      {Math.abs(res.dt.closing) < 1
                        ? "The balance closes to nil, confirming that the whole difference is timing only."
                        : "A residual balance of " + S + br(res.dt.closing) + " remains at expiry. This is expected, and arises from the restoration provision, which is still outstanding until the cost is actually incurred" +
                          (res.residualNBV > 1 ? ", and from the residual right-of-use carrying amount because depreciation runs over useful life following transfer of ownership" : "") + "."}
                    </p>
                  </div>

                  <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">Disclosure Extract, Ind AS 12.81</h4>
                    <table className="w-full text-xs">
                      <tbody className="divide-y divide-slate-100">
                        <tr><Td cls="text-slate-700">Deferred tax relating to right-of-use assets <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">81(g)(i)</span></Td>
                          <Td right cls="text-rose-700">{"(" + money(snap && res.dt ? (function () { var p = null; res.rows.forEach(function (r) { if (cmpD(r.pEnd, snap.asAt) <= 0) p = r; }); return p && p.dt ? p.dt.tdRou * p.dt.rate : 0; })() : 0) + ")"}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Deferred tax relating to lease liabilities <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">81(g)(i)</span></Td>
                          <Td right cls="text-emerald-700">{money(snap ? (function () { var p = null; res.rows.forEach(function (r) { if (cmpD(r.pEnd, snap.asAt) <= 0) p = r; }); return p && p.dt ? p.dt.tdLiab * p.dt.rate : 0; })() : 0)}</Td></tr>
                        {res.dt.incAro ? (
                          <tr><Td cls="text-slate-700">Deferred tax relating to restoration provisions <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">81(g)(i)</span></Td>
                            <Td right cls="text-emerald-700">{money(snap ? (function () { var p = null; res.rows.forEach(function (r) { if (cmpD(r.pEnd, snap.asAt) <= 0) p = r; }); return p && p.dt ? p.dt.tdAro * p.dt.rate : 0; })() : 0)}</Td></tr>
                        ) : null}
                        <tr className="bg-slate-800 font-bold text-white"><Td>Net deferred tax recognised in the balance sheet</Td><Td right>{br(snap ? snap.dt : 0)}</Td></tr>
                        <tr><Td cls="text-slate-700">Deferred tax credited to profit or loss for the year <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">81(g)(ii)</span></Td>
                          <Td right cls="font-semibold">{br(dtFy ? dtFy.move : 0)}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Of which, effect of the change in the enacted rate <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">81(d)</span></Td>
                          <Td right>{br(dtFy ? dtFy.rateEffect : 0)}</Td></tr>
                        {res.dt.totals.unrecMax > 0.005 ? (
                          <tr className="bg-amber-50"><Td cls="font-semibold text-amber-900">Deductible temporary differences for which no asset is recognised <span className="ml-1 rounded bg-amber-100 px-1 text-[9px] font-bold text-amber-700">81(e)</span></Td>
                            <Td right cls="font-bold text-amber-800">{money(res.dt.totals.unrecMax)}</Td></tr>
                        ) : null}
                      </tbody>
                    </table>
                    <p className="border-t border-slate-100 px-5 py-2.5 text-[10.5px] leading-snug text-slate-500">
                      Deferred tax assets and liabilities are not discounted, per Ind AS 12.53, and are classified as
                      non current irrespective of the reversal profile, per Ind AS 12.70.
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h4 className="text-xs font-bold text-slate-800">Judgements and Limitations of the Deferred Tax Module</h4>
                  <ul className="mt-3 grid list-outside list-disc gap-1.5 pl-4 text-[11.5px] leading-relaxed text-slate-600 md:grid-cols-2">
                    <li>The tax base assumed for each item follows the treatment selected in the sidebar. Confirm it against the entity's own tax position, since the deductibility of rent, brokerage and restoration costs is fact specific.</li>
                    <li>Restoration costs are assumed deductible only when incurred. If the tax authority allows a deduction on provisioning, switch the provision out of the computation.</li>
                    <li>Rate changes are applied from the effective date entered. Ind AS 12.47 requires rates enacted or substantively enacted by the reporting date, so a merely proposed rate must not be used.</li>
                    <li>Recoverability is a judgement. The restriction switch reduces the asset uniformly, whereas in practice the assessment should be based on projected taxable profits and the reversal pattern of the differences.</li>
                    <li>Minimum alternate tax credit under section 115JB, unabsorbed depreciation and carried forward losses are not modelled. Entities under the section 115BAA regime are outside the ambit of minimum alternate tax.</li>
                    <li>For interim periods, Ind AS 34.B12 requires income tax to be accrued using the estimated average annual effective tax rate. The quarterly figures here are schedule driven, so reconcile them to the effective tax rate approach before reporting.</li>
                    <li>On first time adoption of Ind AS 116 the deferred tax on the transition adjustment is recognised in retained earnings rather than profit or loss, per Ind AS 12.61A. This module recognises movements in profit or loss only.</li>
                    <li>Offsetting is presentational. It requires a legally enforceable right of set off and the same taxation authority, per Ind AS 12.74.</li>
                  </ul>
                </div>
              </div>
            )
          ) : null}

          {/* ============ QUARTERLY ============ */}
          {tab === "quarter" ? (
            !qRep || !qObj ? (
              <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white/60 p-10 text-center">
                <p className="text-sm font-bold text-slate-700">No leases available for a quarterly report</p>
                <p className="mx-auto mt-1 max-w-md text-[11.5px] text-slate-500">Calculate the current lease, or save leases to the portfolio, then return here.</p>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
                    <Field label="Reporting entity"><input value={entity} onChange={function (e) { setEntity(e.target.value); }} className={inputCls} /></Field>
                    <Field label="Quarter">
                      <select value={qSel} onChange={function (e) { setQSel(e.target.value); }} className={inputCls}>
                        {quarters.map(function (q) {
                          return <option key={quarterKey(q)} value={quarterKey(q)}>{q.label + " (" + fmtDate(q.start) + " to " + fmtDate(q.end) + ")"}</option>;
                        })}
                      </select>
                    </Field>
                    <Field label="Balances as on"><input type="date" value={asOn} onChange={function (e) { setAsOn(e.target.value); }} className={inputCls} /></Field>
                    <Field label="Accrual basis">
                      <select value={qBasis} onChange={function (e) { setQBasis(e.target.value); }} className={inputCls}>
                        <option value="accrual">Day weighted accrual</option>
                        <option value="period">Whole period allocation</option>
                      </select>
                    </Field>
                    <Field label="Population">
                      <label className="flex h-[38px] items-center gap-2 rounded-lg border border-slate-300 px-3">
                        <input type="checkbox" checked={incCurrent} onChange={function (e) { setIncCurrent(e.target.checked); }} className="h-4 w-4 rounded border-slate-300 text-indigo-600" />
                        <span className="text-[11px] font-semibold text-slate-700">Include working lease</span>
                      </label>
                    </Field>
                    <Field label="Export">
                      <span className="flex gap-2">
                        <button onClick={exportQuarterXLS} className="flex-1 rounded-lg bg-emerald-600 px-3 py-2 text-[11px] font-bold text-white hover:bg-emerald-700">Excel</button>
                        <button onClick={exportQuarterCSV} className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-[11px] font-bold text-slate-600 hover:bg-slate-50">CSV</button>
                      </span>
                    </Field>
                  </div>
                  <p className="mt-3 border-t border-slate-100 pt-3 text-[10.5px] leading-snug text-slate-500">
                    {entity + " | " + qObj.label + " | quarter " + fmtDate(qObj.start) + " to " + fmtDate(qObj.end) +
                     " | year to date from " + fmtDate(qRep.ys) + " | balances as on " + fmtDate(qRep.asOn) +
                     " | " + qRep.lines.length + " lease(s) | deferred tax " + (qRep.T.dtOn ? "recognised" : "not enabled")}
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
                  <Card tone="amber" symbol={S} label="Charge before tax for the quarter" value={money(qRep.T.qExp)}
                    sub={"Interest " + S + money(qRep.T.interest) + " and depreciation " + S + money(qRep.T.dep)}
                    foot={"Year to date " + S + money(qRep.T.ytdExp)} />
                  <Card tone="violet" symbol={S} label="Deferred tax income for the quarter" value={br(qRep.T.dtMove)}
                    sub="A credit to profit or loss, reducing the net charge"
                    foot={"Year to date " + S + br(qRep.T.ytdDtMove)} />
                  <Card tone="rose" symbol={S} label="Net charge after deferred tax" value={money(qRep.T.qExpNet)}
                    sub={"Effective relief of " + (qRep.T.qExp > 0 ? (qRep.T.dtMove / qRep.T.qExp * 100).toFixed(1) : "0.0") + " percent"}
                    foot={"Year to date " + S + money(qRep.T.ytdExpNet)} />
                  <Card tone="emerald" symbol={S} label={"Lease liability as on " + fmtDate(qRep.asOn)} value={money(qRep.T.closeLiab)}
                    sub={"Current " + S + money(qRep.T.current) + " and non current " + S + money(qRep.T.nonCurrent)}
                    foot={"Weighted average rate " + qRep.T.wavg.toFixed(2) + " percent"} />
                  <Card tone="indigo" symbol={S} label={"ROU assets and net deferred tax"} value={money(qRep.T.closeRou)}
                    sub={"Net deferred tax " + S + br(qRep.T.dtClose)}
                    foot={"Restoration provision " + S + money(qRep.T.aro)} />
                </div>

                {qRep.flags.length ? (
                  <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
                    <h4 className="text-[11.5px] font-bold text-amber-900">Review points for this quarter</h4>
                    <ul className="mt-2 list-outside list-disc space-y-1 pl-4 text-[11px] font-semibold leading-snug text-amber-800">
                      {qRep.flags.map(function (f, x) { return <li key={x}>{f}</li>; })}
                    </ul>
                  </div>
                ) : null}

                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">Amounts Recognised in Profit and Loss, Quarter and Year to Date</h4>
                    <table className="w-full text-xs">
                      <thead className="bg-slate-100 text-slate-600"><tr><Th>Particulars</Th><Th right>{qObj.label}</Th><Th right>Year to date</Th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        <tr><Td cls="text-slate-700">Depreciation on right-of-use assets <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">53(a)</span></Td><Td right>{money(qRep.T.dep)}</Td><Td right>{money(qRep.T.ytdDep)}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Interest on lease liabilities <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">53(b)</span></Td><Td right>{money(qRep.T.interest)}</Td><Td right>{money(qRep.T.ytdInterest)}</Td></tr>
                        <tr><Td cls="text-slate-700">Unwinding of restoration provisions <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">Ind AS 37</span></Td><Td right>{money(qRep.T.unwind)}</Td><Td right>{money(qRep.T.ytdUnwind)}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Gains on lease modifications <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">53(i)</span></Td><Td right cls="text-emerald-700">{"(" + money(qRep.T.modPL) + ")"}</Td><Td right cls="text-emerald-700">{"(" + money(qRep.T.ytdModPL) + ")"}</Td></tr>
                        <tr className="bg-slate-200 font-bold text-slate-900"><Td>Charge before tax</Td><Td right>{money(qRep.T.qExp)}</Td><Td right>{money(qRep.T.ytdExp)}</Td></tr>
                        <tr className="bg-violet-50"><Td cls="font-semibold text-violet-900">Deferred tax income, credit to profit or loss <span className="ml-1 rounded bg-violet-100 px-1 text-[9px] font-bold text-violet-700">Ind AS 12.58</span></Td>
                          <Td right cls="font-semibold text-violet-800">{"(" + money(qRep.T.dtMove) + ")"}</Td>
                          <Td right cls="font-semibold text-violet-800">{"(" + money(qRep.T.ytdDtMove) + ")"}</Td></tr>
                        <tr className="bg-slate-800 font-bold text-white"><Td>Net charge after deferred tax</Td><Td right>{money(qRep.T.qExpNet)}</Td><Td right>{money(qRep.T.ytdExpNet)}</Td></tr>
                        <tr><Td cls="font-semibold text-slate-700">Total cash outflow for leases <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">53(g)</span></Td><Td right cls="font-bold">{money(qRep.T.pmt)}</Td><Td right cls="font-bold">{money(qRep.T.ytdPmt)}</Td></tr>
                        <tr><Td cls="font-semibold text-slate-700">Additions to right-of-use assets <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">53(h)</span></Td><Td right cls="font-bold">{money(qRep.T.addRou + Math.max(qRep.T.modRouAdj, 0))}</Td><Td right cls="text-slate-400">{"\u2014"}</Td></tr>
                      </tbody>
                    </table>
                    <p className="border-t border-slate-100 px-5 py-2.5 text-[10.5px] leading-snug text-slate-500">
                      Ind AS 34 requires both the current quarter and the cumulative year to date. Note that Ind AS 34.B12
                      requires interim income tax to be accrued using the estimated average annual effective tax rate, so the
                      schedule driven deferred tax above should be reconciled to that approach.
                    </p>
                  </div>

                  <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">Movement Reconciliation for the Quarter</h4>
                    <table className="w-full text-xs">
                      <thead className="bg-slate-100 text-slate-600"><tr><Th>Particulars</Th><Th right>Lease liability</Th><Th right>ROU asset</Th><Th right>Net deferred tax</Th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        <tr><Td cls="text-slate-700">{"Opening on " + fmtDate(qObj.start)}</Td><Td right>{money(qRep.T.openLiab)}</Td><Td right>{money(qRep.T.openRou)}</Td><Td right>{br(qRep.T.dtOpen)}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Additions on new leases</Td><Td right>{money(qRep.T.addLiab)}</Td><Td right>{money(qRep.T.addRou)}</Td><Td right>{br(qRep.T.dtDay1)}</Td></tr>
                        <tr><Td cls="text-slate-700">Remeasurement on modifications</Td><Td right>{money(qRep.T.modLiabAdj)}</Td><Td right>{money(qRep.T.modRouAdj)}</Td><Td right cls="text-slate-300">{"\u2014"}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Interest accretion</Td><Td right>{money(qRep.T.interest)}</Td><Td right cls="text-slate-300">{"\u2014"}</Td><Td right cls="text-slate-300">{"\u2014"}</Td></tr>
                        <tr><Td cls="text-slate-700">Rentals paid</Td><Td right>{"(" + money(qRep.T.pmt) + ")"}</Td><Td right cls="text-slate-300">{"\u2014"}</Td><Td right cls="text-slate-300">{"\u2014"}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Depreciation</Td><Td right cls="text-slate-300">{"\u2014"}</Td><Td right>{"(" + money(qRep.T.dep) + ")"}</Td><Td right cls="text-slate-300">{"\u2014"}</Td></tr>
                        <tr><Td cls="text-slate-700">Origination and reversal of temporary differences</Td><Td right cls="text-slate-300">{"\u2014"}</Td><Td right cls="text-slate-300">{"\u2014"}</Td><Td right>{br(qRep.T.dtOrig - qRep.T.dtDay1)}</Td></tr>
                        <tr className="bg-slate-50/60"><Td cls="text-slate-700">Effect of the change in the enacted tax rate</Td><Td right cls="text-slate-300">{"\u2014"}</Td><Td right cls="text-slate-300">{"\u2014"}</Td><Td right cls={Math.abs(qRep.T.dtRateEffect) > 0.005 ? "font-bold text-amber-700" : "text-slate-300"}>{Math.abs(qRep.T.dtRateEffect) > 0.005 ? br(qRep.T.dtRateEffect) : "\u2014"}</Td></tr>
                        <tr className="bg-slate-800 font-bold text-white"><Td>{"Closing on " + fmtDate(qObj.end)}</Td><Td right>{money(qRep.T.closeLiab)}</Td><Td right>{money(qRep.T.closeRou)}</Td><Td right>{br(qRep.T.dtClose)}</Td></tr>
                        <tr className={Math.abs(qRep.T.tie) < 1 && Math.abs(qRep.T.tieRou) < 1 && Math.abs(qRep.T.tieDt) < 1 ? "bg-emerald-50 font-bold text-emerald-800" : "bg-rose-50 font-bold text-rose-700"}>
                          <Td>{Math.abs(qRep.T.tie) < 1 && Math.abs(qRep.T.tieRou) < 1 && Math.abs(qRep.T.tieDt) < 1 ? "Reconciliation check passed" : "Reconciliation difference, investigate"}</Td>
                          <Td right>{money(qRep.T.tie)}</Td><Td right>{money(qRep.T.tieRou)}</Td><Td right>{money(qRep.T.tieDt)}</Td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                    <h4 className="text-xs font-bold text-slate-800">Lease by Lease Breakdown for the Quarter</h4>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[9.5px] font-bold uppercase tracking-wide text-slate-600">{qRep.lines.length + " leases"}</span>
                  </div>
                  <div className="scroll-box max-h-[520px] overflow-auto">
                    <table className="w-full min-w-[1480px] text-xs">
                      <thead className="sticky top-0 z-10 bg-slate-800 text-white">
                        <tr><Th>Lease</Th><Th>Class</Th><Th right>Interest</Th><Th right>Depreciation</Th>
                          <Th right>Unwinding</Th><Th right>Before tax</Th><Th right>Deferred tax</Th>
                          <Th right>After tax</Th><Th right>Cash outflow</Th><Th right>Closing liability</Th>
                          <Th right>Current</Th><Th right>ROU net block</Th><Th right>Net deferred tax</Th><Th center>Status</Th></tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {qRep.lines.map(function (L) {
                          return (
                            <tr key={L.id} className="odd:bg-white even:bg-slate-50/70 hover:bg-indigo-50/60">
                              <Td><span className="font-semibold text-slate-800">{L.name}</span><br /><span className="text-[10px] text-slate-400">{L.id + " | " + L.lessor}</span></Td>
                              <Td cls="text-[11px] text-slate-600">{L.cls}</Td>
                              <Td right cls="text-amber-700">{money(L.qInterest)}</Td>
                              <Td right cls="text-rose-700">{money(L.qDep)}</Td>
                              <Td right cls="text-slate-500">{money(L.qUnwind)}</Td>
                              <Td right cls="font-semibold">{money(L.qExp)}</Td>
                              <Td right cls={L.hasDt ? "font-semibold text-violet-700" : "text-slate-300"}>{L.hasDt ? "(" + money(L.qDtMove) + ")" : "\u2014"}</Td>
                              <Td right cls="font-bold text-slate-900">{money(L.qExpNet)}</Td>
                              <Td right>{money(L.qPmt)}</Td>
                              <Td right cls="font-semibold">{money(L.closeLiab)}</Td>
                              <Td right>{money(L.current)}</Td>
                              <Td right cls="font-semibold text-indigo-700">{money(L.onRou)}</Td>
                              <Td right cls={L.hasDt ? "font-semibold text-violet-700" : "text-slate-300"}>{L.hasDt ? br(L.onDt) : "\u2014"}</Td>
                              <Td center>
                                {L.commenced ? <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[9px] font-bold text-emerald-700">NEW</span>
                                  : (L.ended ? <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[9px] font-bold text-slate-600">ENDED</span>
                                  : <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[9px] font-bold text-sky-700">LIVE</span>)}
                              </Td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot className="sticky bottom-0 bg-slate-100 font-bold text-slate-900">
                        <tr>
                          <td colSpan={2} className="px-3 py-3 text-[10px] uppercase tracking-wider">{"Total, " + S}</td>
                          <Td right>{money(qRep.T.interest)}</Td><Td right>{money(qRep.T.dep)}</Td>
                          <Td right>{money(qRep.T.unwind)}</Td><Td right>{money(qRep.T.qExp)}</Td>
                          <Td right>{"(" + money(qRep.T.dtMove) + ")"}</Td><Td right>{money(qRep.T.qExpNet)}</Td>
                          <Td right>{money(qRep.T.pmt)}</Td><Td right>{money(qRep.T.closeLiab)}</Td>
                          <Td right>{money(qRep.T.current)}</Td><Td right>{money(qRep.T.closeRou)}</Td>
                          <Td right>{br(qRep.T.dtClose)}</Td><Td center>{null}</Td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <JE symbol={S} tone="indigo" tag={"Consolidated, " + qObj.label}
                    title={"Portfolio Journal Entry for the Quarter Ended " + fmtDate(qObj.end)}
                    narration={"Being the consolidated entry across " + qRep.lines.length +
                      " lease(s) recording interest accretion, depreciation, unwinding of restoration provisions, additions and remeasurements, rentals paid, and the related deferred tax under Ind AS 12, for " + qObj.label}
                    lines={qRep.consol} />
                  <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">{"Maturity Analysis as on " + fmtDate(qRep.asOn) + ", Para 58"}</h4>
                    <table className="w-full text-xs">
                      <thead className="bg-slate-100 text-slate-600"><tr><Th>Contractual maturity</Th><Th right>{"Amount, " + S}</Th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {["Not later than 1 year", "Later than 1 year and not later than 2 years",
                          "Later than 2 years and not later than 3 years",
                          "Later than 3 years and not later than 5 years", "Later than 5 years"].map(function (l, x) {
                          return <tr key={l} className="odd:bg-white even:bg-slate-50/60"><Td cls="text-slate-700">{l}</Td><Td right>{money(qRep.T.buckets[x])}</Td></tr>;
                        })}
                        <tr className="bg-slate-50 font-bold"><Td>Total undiscounted lease payments</Td><Td right>{money(qRep.T.gross)}</Td></tr>
                        <tr><Td cls="text-slate-600">Less future finance charges</Td><Td right cls="text-amber-700">{"(" + money(qRep.T.imputed) + ")"}</Td></tr>
                        <tr className="bg-slate-800 font-bold text-white"><Td>Carrying amount of lease liabilities</Td><Td right>{money(qRep.T.closeLiab)}</Td></tr>
                      </tbody>
                    </table>
                    <h4 className="border-y border-slate-100 bg-slate-50 px-5 py-2.5 text-[11px] font-bold text-slate-700">By class of underlying asset</h4>
                    <table className="w-full text-xs">
                      <thead className="bg-slate-100 text-slate-600"><tr><Th>Class</Th><Th center>Count</Th><Th right>Depreciation</Th><Th right>ROU carrying</Th><Th right>Net deferred tax</Th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {Object.keys(qRep.T.byClass).map(function (k) {
                          var v = qRep.T.byClass[k];
                          return (
                            <tr key={k} className="odd:bg-white even:bg-slate-50/60">
                              <Td cls="text-slate-700">{k}</Td><Td center>{v.n}</Td>
                              <Td right cls="text-rose-700">{money(v.dep)}</Td>
                              <Td right cls="font-semibold text-indigo-700">{money(v.nbv)}</Td>
                              <Td right cls="font-semibold text-violet-700">{br(v.dt)}</Td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                    <div>
                      <h4 className="text-xs font-bold text-slate-800">Journal Register for the Quarter, Whole Portfolio</h4>
                      <p className="text-[10.5px] text-slate-500">One line per account per lease, including the deferred tax entries, ready to load into your accounting system.</p>
                    </div>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[9.5px] font-bold uppercase tracking-wide text-slate-600">{qRep.jr.length + " lines"}</span>
                  </div>
                  <div className="scroll-box max-h-[520px] overflow-auto">
                    <table className="w-full min-w-[1180px] text-xs">
                      <thead className="sticky top-0 z-10 bg-slate-800 text-white">
                        <tr><Th>Lease</Th><Th>Posting date</Th><Th>Account</Th><Th right>Debit</Th><Th right>Credit</Th><Th>Narration</Th></tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {qRep.jr.map(function (j, x) {
                          var isDt = j.acc.indexOf("Deferred Tax") === 0;
                          return (
                            <tr key={x} className={isDt ? "bg-violet-50/70" : "odd:bg-white even:bg-slate-50/70"}>
                              <Td cls="text-[11px]"><span className="font-semibold text-slate-700">{j.id}</span><br /><span className="text-[10px] text-slate-400">{j.name}</span></Td>
                              <Td cls="num text-slate-500">{j.date}</Td>
                              <Td cls={j.cr ? "pl-8 text-slate-600" : "font-semibold text-slate-800"}>{(j.cr ? "To " : "Dr. ") + j.acc}</Td>
                              <Td right>{j.dr ? money(j.dr) : "\u2014"}</Td>
                              <Td right>{j.cr ? money(j.cr) : "\u2014"}</Td>
                              <Td cls="max-w-[420px] text-[10.5px] italic leading-snug text-slate-500">{j.nar}</Td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot className="sticky bottom-0 bg-slate-100 font-bold">
                        <tr>
                          <td colSpan={3} className="px-3 py-3 text-[10px] uppercase tracking-wider">{"Total, " + S}</td>
                          <Td right>{money(qRep.jr.reduce(function (s, j) { return s + toNum(j.dr); }, 0))}</Td>
                          <Td right>{money(qRep.jr.reduce(function (s, j) { return s + toNum(j.cr); }, 0))}</Td>
                          <Td>{null}</Td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              </div>
            )
          ) : null}

          {/* ============ DASHBOARD ============ */}
          {tab === "dash" ? (
            !res ? (
              <div className="flex h-80 flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white/60 p-6 text-center">
                <p className="text-sm font-bold text-slate-700">No measurement generated</p>
                <p className="mt-1 max-w-md text-[11.5px] text-slate-500">Complete the master data and press Calculate Schedule.</p>
                {Object.keys(errs).length ? (
                  <ul className="mt-3 list-inside list-disc text-left text-[11px] font-semibold text-rose-600">
                    {Object.keys(errs).map(function (k) { return <li key={k}>{errs[k]}</li>; })}
                  </ul>
                ) : null}
              </div>
            ) : (
              <div className="space-y-5">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
                  <Card tone="indigo" symbol={S} label="Day one ROU asset" value={money(res.rou0)}
                    sub={"Capitalised costs " + S + money(res.build.idc + res.build.prepaid + res.build.aro)} />
                  <Card tone="emerald" symbol={S} label="Initial lease liability" value={money(res.liabPresented)}
                    sub={"Present value of " + res.N + " rentals at " + pctS(res.rate0)} />
                  <Card tone="amber" symbol={S} label="Total finance cost" value={money(res.totals.interest)}
                    sub={(res.totals.payments > 0 ? (res.totals.interest / res.totals.payments * 100).toFixed(1) : "0.0") + " percent of gross rentals"} />
                  <Card tone="violet" symbol={S} label="Day one deferred tax" value={dtOn ? br(res.dt.day1.move) : "Not enabled"}
                    sub={dtOn ? "Peak net asset " + S + money(res.dt.peak) + " at " + pctS(res.dt.finalRate, 2) : "Enable the Ind AS 12 module in section six"} />
                  <Card tone="slate" symbol={S} label="Total cash rentals" value={money(res.totals.payments)}
                    sub={"Discounting effect " + S + money(res.totals.payments - res.liabGross)} />
                </div>

                <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-slate-200 bg-slate-200 text-center md:grid-cols-6">
                  {[["Lease term", res.N + " months"], ["Commencement", fmtDate(res.meta.start)],
                    ["Expiry", fmtDate(res.meta.end)], ["Annuity type", res.advance ? "Due, advance" : "Ordinary, arrears"],
                    ["Depreciation base", res.depMonths + " months"],
                    ["Tax rate", dtOn ? pctS(res.dt.finalRate, 2) : "n a"]].map(function (p) {
                    return (
                      <div key={p[0]} className="bg-white px-3 py-3">
                        <p className="text-[9.5px] font-bold uppercase tracking-wider text-slate-400">{p[0]}</p>
                        <p className="num mt-1 text-xs font-bold text-slate-800">{p[1]}</p>
                      </div>
                    );
                  })}
                </div>

                <TrendChart rows={res.rows} symbol={S} showDt={dtOn} />

                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h4 className="text-xs font-bold text-slate-800">Right-of-Use Asset Cost Build Up, Ind AS 116.24</h4>
                    <dl className="mt-3 space-y-2 text-xs">
                      {[["Initial measurement of the lease liability", res.build.pv, "24(a)"],
                        ["Add, payments made at or before commencement", res.build.prepaid, "24(b)"],
                        ["Less, lease incentives received", -res.build.incentive, "24(b)"],
                        ["Add, initial direct costs", res.build.idc, "24(c)"],
                        ["Add, present value of the restoration obligation", res.build.aro, "24(d)"]].map(function (r, x) {
                        return (
                          <div key={x} className="flex items-baseline justify-between gap-3 text-slate-700">
                            <dt className="flex-1">{r[0]} <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">{r[2]}</span></dt>
                            <dd className="num font-medium">{S}{money(r[1])}</dd>
                          </div>
                        );
                      })}
                      <div className="flex justify-between border-t-2 border-slate-800 pt-2 text-[13px] font-bold text-slate-900">
                        <dt>Day one ROU asset, gross block</dt><dd className="num">{S}{money(res.build.total)}</dd>
                      </div>
                    </dl>
                  </div>
                  <div className="space-y-4">
                    <JE symbol={S} tone="indigo" tag="Initial recognition" title={"Day One Entry, " + fmtDate(res.meta.start)}
                      narration="Being recognition of the right-of-use asset and lease liability at the present value of lease payments, together with initial direct costs, incentives received and the restoration obligation, Ind AS 116.22 to 26 read with Ind AS 37"
                      lines={[
                        { acc: "Right-of-Use Asset", dr: res.rou0 },
                        { acc: "Bank, lease incentive received", dr: res.build.incentive },
                        { acc: "Lease Liability", cr: res.liabPresented },
                        { acc: "Bank, rental paid on commencement", cr: res.strict ? res.day1Pmt : 0 },
                        { acc: "Bank, initial direct costs", cr: res.build.idc },
                        { acc: "Prepaid Rent transferred to the ROU asset", cr: res.build.prepaid },
                        { acc: "Provision for Site Restoration", cr: res.build.aro }
                      ]} />
                    {dtOn && Math.abs(res.dt.day1.move) > 0.005 ? (
                      <JE symbol={S} tone="violet" tag="Ind AS 12.22A" title={"Day One Deferred Tax, " + fmtDate(res.meta.start)}
                        narration="Being deferred tax on the temporary differences arising on initial recognition, the initial recognition exemption having been withdrawn for leases and decommissioning obligations"
                        lines={[
                          { acc: "Deferred Tax Asset", dr: Math.max(res.dt.day1.move, 0) },
                          { acc: "Deferred Tax - credit to profit or loss", cr: Math.max(res.dt.day1.move, 0) },
                          { acc: "Deferred Tax - charge to profit or loss", dr: Math.max(-res.dt.day1.move, 0) },
                          { acc: "Deferred Tax Liability", cr: Math.max(-res.dt.day1.move, 0) }
                        ]} />
                    ) : null}
                  </div>
                </div>

                <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-5">
                  <h4 className="text-xs font-bold text-emerald-900">Arithmetic Proof and Audit Tie Out</h4>
                  <dl className="mt-3 space-y-2 text-xs">
                    {[["Gross contractual rentals", res.totals.payments, 0],
                      ["Less, initial lease liability at present value", -res.liabGross, 0],
                      ["Equals total finance cost", res.totals.interest, 1],
                      ["Total ROU depreciation", res.totals.dep, 1],
                      ["Unwinding of the restoration provision", res.totals.unwind, 1],
                      ["Net gain on modifications, deducted", -res.totals.modPL, 1],
                      ["Charge before tax over the term",
                        res.totals.interest + res.totals.dep + res.totals.unwind - res.totals.modPL, 1]]
                      .concat(dtOn ? [["Less, deferred tax credited over the term", -res.dt.totals.move, 1],
                                      ["Net charge after deferred tax",
                                        res.totals.interest + res.totals.dep + res.totals.unwind - res.totals.modPL - res.dt.totals.move, 2]]
                                   : [["Net charge", res.totals.interest + res.totals.dep + res.totals.unwind - res.totals.modPL, 2]])
                      .map(function (r, x) {
                      var cls = r[2] === 2 ? "border-t-2 border-emerald-300 pt-2 text-[13px] font-bold text-emerald-900"
                        : (r[2] === 1 ? "border-t border-emerald-200 pt-2 font-semibold text-emerald-900" : "text-emerald-800");
                      return <div key={x} className={"flex justify-between gap-4 " + cls}><dt>{r[0]}</dt><dd className="num">{S}{br(r[1])}</dd></div>;
                    })}
                  </dl>
                </div>
              </div>
            )
          ) : null}

          {/* ============ SCHEDULE ============ */}
          {tab === "sched" && res ? (
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                <div>
                  <h3 className="text-xs font-bold text-slate-800">Lease Liability Amortisation, ROU Depreciation{dtOn ? " and Deferred Tax" : ""}</h3>
                  <p className="text-[10.5px] text-slate-500">
                    {"Effective interest method. Interest equals " + (res.advance ? "the opening balance less the rental" : "the opening balance") + " multiplied by " + pctS(res.rateNow) + "."}
                  </p>
                </div>
                <div className="no-print grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1">
                  {[["monthly", "Monthly"], ["fy", "Financial year"]].map(function (v) {
                    return (
                      <button key={v[0]} onClick={function () { setView(v[0]); }}
                        className={"rounded-md px-3 py-1.5 text-[11px] font-bold transition " + (view === v[0] ? "bg-white text-indigo-700 shadow-sm" : "text-slate-500")}>
                        {v[1]}
                      </button>
                    );
                  })}
                </div>
              </div>
              {view === "monthly" ? (
                <div className="scroll-box max-h-[620px] overflow-auto">
                  <table className={"w-full text-xs " + (dtOn ? "min-w-[1440px]" : "min-w-[1240px]")}>
                    <thead className="sticky top-0 z-10 bg-slate-800 text-white">
                      <tr>
                        <Th>No</Th><Th>Month</Th><Th>Quarter</Th><Th>Pay date</Th><Th right>Opening liability</Th>
                        <Th right>Interest</Th><Th right>Rental</Th><Th right>Closing liability</Th>
                        <Th right>Depreciation</Th><Th right>ROU net block</Th><Th right>Restoration</Th>
                        {dtOn ? <Th right>Net temporary difference</Th> : null}
                        {dtOn ? <Th right>Deferred tax movement</Th> : null}
                        {dtOn ? <Th right>Net deferred tax</Th> : null}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {res.rows.map(function (r) {
                        var isMod = Math.abs(r.modLiabAdj) > 0.005;
                        return (
                          <tr key={r.k} className={isMod ? "bg-amber-50 hover:bg-amber-100" : "odd:bg-white even:bg-slate-50/70 hover:bg-indigo-50/60"}>
                            <Td cls="num text-slate-400">{r.k}</Td>
                            <Td cls="font-semibold text-slate-700">{fmtMon(r.pStart)}</Td>
                            <Td cls="text-[10px] text-slate-400">{r.q ? r.q.label : ""}</Td>
                            <Td cls="num text-slate-500">{fmtDate(r.payDate)}</Td>
                            <Td right>{money(r.open)}</Td>
                            <Td right cls="text-amber-700">{money(r.interest)}</Td>
                            <Td right>{r.pmt === 0 ? <span className="rounded bg-sky-100 px-1.5 text-[10px] font-bold text-sky-700">RENT FREE</span> : "(" + money(r.pmt) + ")"}</Td>
                            <Td right cls="font-semibold text-slate-900">{money(r.close)}</Td>
                            <Td right cls="text-rose-700">{money(r.dep)}</Td>
                            <Td right cls="font-semibold text-indigo-700">{money(r.nbv)}</Td>
                            <Td right cls="text-slate-500">{money(r.aro)}</Td>
                            {dtOn ? <Td right cls="text-slate-600">{r.dt ? money(r.dt.netTd) : "\u2014"}</Td> : null}
                            {dtOn ? <Td right cls={r.dt && r.dt.move >= 0 ? "text-emerald-700" : "text-rose-700"}>{r.dt ? br(r.dt.move) : "\u2014"}</Td> : null}
                            {dtOn ? <Td right cls="font-semibold text-violet-700">{r.dt ? br(r.dt.close) : "\u2014"}</Td> : null}
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className="sticky bottom-0 bg-slate-100 font-bold text-slate-900">
                      <tr>
                        <td colSpan={4} className="px-3 py-3 text-[10px] uppercase tracking-wider">{"Total, " + S}</td>
                        <Td right cls="text-slate-400">{"\u2014"}</Td>
                        <Td right>{money(res.totals.interest)}</Td>
                        <Td right>{"(" + money(res.totals.payments) + ")"}</Td>
                        <Td right>0.00</Td><Td right>{money(res.totals.dep)}</Td>
                        <Td right>{money(res.residualNBV)}</Td><Td right>{money(res.aro.undisc)}</Td>
                        {dtOn ? <Td right>{"\u2014"}</Td> : null}
                        {dtOn ? <Td right>{br(res.dt.totals.move)}</Td> : null}
                        {dtOn ? <Td right>{br(res.dt.closing)}</Td> : null}
                      </tr>
                    </tfoot>
                  </table>
                </div>
              ) : (
                <div className="overflow-auto">
                  <table className="w-full min-w-[1100px] text-xs">
                    <thead className="bg-slate-800 text-white">
                      <tr><Th>Financial year</Th><Th center>Months</Th><Th right>Finance cost</Th><Th right>Depreciation</Th>
                        <Th right>Unwinding</Th><Th right>Charge before tax</Th>
                        {dtOn ? <Th right>Deferred tax</Th> : null}
                        {dtOn ? <Th right>Charge after tax</Th> : null}
                        <Th right>Cash outflow</Th><Th right>Closing liability</Th><Th right>Closing ROU</Th>
                        {dtOn ? <Th right>Net deferred tax</Th> : null}</tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {res.fyRows.map(function (g) {
                        var before = g.interest + g.dep + g.unwind - g.modPL;
                        return (
                          <tr key={g.fy} className="odd:bg-white even:bg-slate-50/70">
                            <Td cls="font-semibold text-slate-700">{g.fy}</Td>
                            <Td center cls="text-slate-500">{g.months}</Td>
                            <Td right cls="text-amber-700">{money(g.interest)}</Td>
                            <Td right cls="text-rose-700">{money(g.dep)}</Td>
                            <Td right cls="text-slate-500">{money(g.unwind)}</Td>
                            <Td right cls="font-semibold">{money(before)}</Td>
                            {dtOn ? <Td right cls="text-violet-700">{"(" + money(toNum(g.dtMove)) + ")"}</Td> : null}
                            {dtOn ? <Td right cls="font-bold">{money(before - toNum(g.dtMove))}</Td> : null}
                            <Td right>{money(g.pmt)}</Td>
                            <Td right cls="font-semibold">{money(g.close)}</Td>
                            <Td right cls="font-semibold text-indigo-700">{money(g.nbv)}</Td>
                            {dtOn ? <Td right cls="font-semibold text-violet-700">{br(toNum(g.dtClose))}</Td> : null}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : null}

          {/* ============ PAYMENT GRID ============ */}
          {tab === "pmt" ? (
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                <div>
                  <h3 className="text-xs font-bold text-slate-800">Contractual Payment Grid, Override Any Period</h3>
                  <p className="text-[10.5px] text-slate-500">Typed overrides take precedence over the escalation formula and are highlighted amber.</p>
                </div>
                <div className="no-print flex gap-2">
                  <button onClick={function () { setKey("overrides", {}); }} className="rounded-lg border border-slate-300 px-3 py-1.5 text-[11px] font-bold text-slate-600 hover:bg-slate-50">Clear overrides</button>
                  <button onClick={function () { run(cfg, false); }} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-indigo-700">Apply and recalculate</button>
                </div>
              </div>
              <div className="scroll-box max-h-[600px] overflow-auto p-4">
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                  {gridPmts.map(function (v, x) {
                    var k = x + 1, ov = (cfg.overrides || {})[k];
                    var hasOv = ov !== undefined && ov !== "";
                    var dt = addMonths(parseISO(cfg.startDate), x);
                    return (
                      <div key={k} className={"rounded-lg border p-2.5 " + (hasOv ? "border-amber-300 bg-amber-50" : (v === 0 ? "border-sky-200 bg-sky-50" : "border-slate-200 bg-white"))}>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-slate-500">{"#" + k + " " + fmtMon(dt)}</span>
                          {v === 0 ? <span className="text-[9px] font-bold text-sky-600">FREE</span> : null}
                        </div>
                        <input type="number" className={miniCls + " mt-1.5"} value={ov === undefined ? "" : ov} placeholder={v.toFixed(2)}
                          onChange={function (ev) {
                            var val = ev.target.value;
                            setCfg(function (p) {
                              var o = Object.assign({}, p.overrides || {});
                              if (val === "") delete o[k]; else o[k] = val;
                              return Object.assign({}, p, { overrides: o });
                            });
                          }} />
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="border-t border-slate-100 bg-slate-50 px-5 py-3 text-[11.5px] font-semibold text-slate-600">
                {"Total contractual rentals " + S + money(gridPmts.reduce(function (s, v) { return s + v; }, 0)) +
                 "  |  rent free periods " + gridPmts.filter(function (v) { return v === 0; }).length +
                 "  |  overrides applied " + Object.keys(cfg.overrides || {}).length}
              </div>
            </div>
          ) : null}

          {/* ============ MODIFICATIONS ============ */}
          {tab === "mod" && res ? (
            <div className="space-y-5">
              <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
                  <div>
                    <h3 className="text-xs font-bold text-slate-800">Lease Modifications and Reassessments, Ind AS 116.39 to 46</h3>
                    <p className="text-[10.5px] text-slate-500">Each event remeasures the liability from its effective month, with a catch up adjustment to the ROU asset. Deferred tax follows automatically.</p>
                  </div>
                  <div className="no-print flex gap-2">
                    <button onClick={function () { setCfg(function (p) { return Object.assign({}, p, { mods: p.mods.concat([newMod()]) }); }); }}
                      className="rounded-lg bg-slate-900 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-slate-800">Add event</button>
                    <button onClick={function () { run(cfg, false); }} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-indigo-700">Apply and recalculate</button>
                  </div>
                </div>
                {errs.mods ? <p className="bg-rose-50 px-5 py-2 text-[11px] font-semibold text-rose-700">{errs.mods}</p> : null}
                {!cfg.mods.length ? (
                  <p className="px-5 py-8 text-center text-xs text-slate-500">No modification events. Add one to model a rent renegotiation, an extension, a downsizing or an index linked reassessment.</p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {cfg.mods.map(function (m, x) {
                      function mset(key, val) {
                        setCfg(function (p) {
                          var arr = p.mods.slice();
                          arr[x] = Object.assign({}, arr[x]); arr[x][key] = val;
                          return Object.assign({}, p, { mods: arr });
                        });
                      }
                      var eff = addMonths(parseISO(cfg.startDate), Math.max(0, toNum(m.month, 1) - 1));
                      return (
                        <div key={m.id} className="p-5">
                          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <input type="checkbox" checked={m.enabled !== false} onChange={function (e) { mset("enabled", e.target.checked); }}
                                className="h-4 w-4 rounded border-slate-300 text-indigo-600" />
                              <input value={m.label} onChange={function (e) { mset("label", e.target.value); }}
                                className="rounded-md border border-slate-200 px-2 py-1 text-xs font-bold text-slate-800" />
                              <span className="rounded bg-slate-100 px-2 py-0.5 text-[9.5px] font-bold text-slate-500">{"Effective " + fmtMon(eff)}</span>
                            </div>
                            <button onClick={function () { setCfg(function (p) { return Object.assign({}, p, { mods: p.mods.filter(function (_, j) { return j !== x; }) }); }); }}
                              className="text-[11px] font-bold text-rose-600 hover:underline">Remove</button>
                          </div>
                          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
                            <Field label="Type">
                              <select value={m.type} onChange={function (e) { mset("type", e.target.value); }} className={inputCls}>
                                <option value="remeasure">Modification 46(b)</option>
                                <option value="scopeDecrease">Scope decrease 46(a)</option>
                                <option value="reassess">Reassessment 40 to 43</option>
                              </select>
                            </Field>
                            <Field label="Effective month"><input type="number" value={m.month} onChange={function (e) { mset("month", e.target.value); }} className={inputCls} /></Field>
                            <Field label="Revised remaining term"><input type="number" value={m.newTerm} onChange={function (e) { mset("newTerm", e.target.value); }} className={inputCls} /></Field>
                            <Field label="Revised rental"><input type="number" value={m.newPayment} onChange={function (e) { mset("newPayment", e.target.value); }} className={inputCls} /></Field>
                            <Field label="Revised rate percent"><input type="number" step="0.01" value={m.newRate} onChange={function (e) { mset("newRate", e.target.value); }} className={inputCls} /></Field>
                            <Field label="Escalation and frequency">
                              <span className="flex gap-1">
                                <input type="number" value={m.escPct} onChange={function (e) { mset("escPct", e.target.value); }} className={inputCls} />
                                <input type="number" value={m.escFreq} onChange={function (e) { mset("escFreq", e.target.value); }} className={inputCls} />
                              </span>
                            </Field>
                            <Field label="Scope decrease percent">
                              <input type="number" value={m.scopePct} onChange={function (e) { mset("scopePct", e.target.value); }} className={inputCls} disabled={m.type !== "scopeDecrease"} />
                            </Field>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {res.events.length ? (
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                  <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">Remeasurement Impact Summary</h4>
                  <div className="overflow-auto">
                    <table className="w-full min-w-[1100px] text-xs">
                      <thead className="bg-slate-800 text-white">
                        <tr><Th>Event</Th><Th>Effective</Th><Th>Quarter</Th><Th>Rate before</Th><Th>Rate after</Th>
                          <Th right>Pre liability</Th><Th right>Post liability</Th><Th right>Liability adjustment</Th>
                          <Th right>ROU adjustment</Th><Th right>Profit and loss</Th>
                          {dtOn ? <Th right>Deferred tax effect</Th> : null}</tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {res.events.map(function (ev, x) {
                          var dtEff = 0;
                          if (dtOn) {
                            var row = null;
                            res.rows.forEach(function (r) { if (r.k === ev.k) row = r; });
                            if (row && row.dt) dtEff = (ev.liabAdj - ev.rouAdj) * row.dt.rate;
                          }
                          return (
                            <tr key={x} className="odd:bg-white even:bg-slate-50/70">
                              <Td cls="font-semibold text-slate-700">{ev.label}</Td>
                              <Td cls="num text-slate-500">{fmtDate(ev.date)}</Td>
                              <Td cls="text-[10px] text-slate-400">{ev.q ? ev.q.label : ""}</Td>
                              <Td cls="num text-slate-500">{pctS(ev.rateBefore, 3)}</Td>
                              <Td cls="num text-slate-500">{pctS(ev.rateAfter, 3)}</Td>
                              <Td right>{money(ev.preLiab)}</Td><Td right>{money(ev.postLiab)}</Td>
                              <Td right cls={ev.liabAdj >= 0 ? "font-semibold text-rose-600" : "font-semibold text-emerald-600"}>{money(ev.liabAdj)}</Td>
                              <Td right cls="font-semibold text-indigo-700">{money(ev.rouAdj)}</Td>
                              <Td right cls={Math.abs(ev.pl) < 0.005 ? "text-slate-300" : (ev.pl > 0 ? "font-bold text-emerald-600" : "font-bold text-rose-600")}>
                                {Math.abs(ev.pl) < 0.005 ? "\u2014" : money(ev.pl)}
                              </Td>
                              {dtOn ? <Td right cls="font-semibold text-violet-700">{br(dtEff)}</Td> : null}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <p className="border-t border-slate-100 px-5 py-2.5 text-[10.5px] leading-snug text-slate-500">
                    A modification changes both carrying amounts, so it changes the temporary difference. Where the liability
                    and ROU adjustments are equal the deferred tax effect is nil. A difference arises only where the ROU asset
                    is floored at nil or a partial termination gain is recognised.
                  </p>
                </div>
              ) : null}
            </div>
          ) : null}

          {/* ============ ANNUAL DISCLOSURES ============ */}
          {tab === "disc" && res && snap ? (
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
                <Card tone="sky" symbol={S} label={"ROU asset as on " + fmtDate(snap.asAt)} value={money(snap.nbv)} sub={cfg.assetClass} />
                <Card tone="emerald" symbol={S} label="Lease liability, current" value={money(snap.current)} />
                <Card tone="indigo" symbol={S} label="Lease liability, non current" value={money(snap.nonCurrent)} />
                <Card tone="slate" symbol={S} label="Total lease liability" value={money(snap.liab)} foot={"Restoration provision " + S + money(snap.aro)} />
                <Card tone="violet" symbol={S} label="Net deferred tax" value={dtOn ? br(snap.dt) : "Not enabled"}
                  sub={dtOn ? "Non current, Ind AS 12.70" : ""} />
              </div>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                  <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">Maturity Analysis, Para 58, Undiscounted</h4>
                  <table className="w-full text-xs">
                    <thead className="bg-slate-100 text-slate-600"><tr><Th>Contractual maturity</Th><Th right>{"Amount, " + S}</Th></tr></thead>
                    <tbody className="divide-y divide-slate-100">
                      {snap.maturity.map(function (r) {
                        return <tr key={r[0]} className="odd:bg-white even:bg-slate-50/60"><Td cls="text-slate-700">{r[0]}</Td><Td right>{money(r[1])}</Td></tr>;
                      })}
                      <tr className="bg-slate-50 font-bold"><Td>Total undiscounted lease payments</Td><Td right>{money(snap.gross)}</Td></tr>
                      <tr><Td cls="text-slate-600">Less future finance charges</Td><Td right cls="text-amber-700">{"(" + money(snap.imputed) + ")"}</Td></tr>
                      <tr className="bg-slate-800 font-bold text-white"><Td>Present value, the carrying amount</Td><Td right>{money(snap.liab)}</Td></tr>
                    </tbody>
                  </table>
                </div>
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                  <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">{"Amounts Recognised in Profit and Loss, " + snap.fy}</h4>
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-slate-100">
                      {[["Depreciation on right-of-use assets", snap.fyFig ? snap.fyFig.dep : 0, "53(a)"],
                        ["Interest on lease liabilities", snap.fyFig ? snap.fyFig.interest : 0, "53(b)"],
                        ["Unwinding of the restoration provision", snap.fyFig ? snap.fyFig.unwind : 0, "Ind AS 37"],
                        ["Short term lease expense", toNum(cfg.shortTermExp), "53(c)"],
                        ["Low value asset expense", toNum(cfg.lowValueExp), "53(d)"],
                        ["Variable lease payments", toNum(cfg.variableExp), "53(e)"],
                        ["Sublease income", -toNum(cfg.subleaseIncome), "53(f)"],
                        ["Gains on lease modifications", -(snap.fyFig ? snap.fyFig.modPL : 0), "53(i)"]].map(function (r) {
                        return (
                          <tr key={r[0]} className="odd:bg-white even:bg-slate-50/60">
                            <Td cls="text-slate-700">{r[0]} <span className="ml-1 rounded bg-slate-100 px-1 text-[9px] font-bold text-slate-500">{r[2]}</span></Td>
                            <Td right>{money(r[1])}</Td>
                          </tr>
                        );
                      })}
                      <tr className="bg-slate-200 font-bold"><Td>Charge before tax</Td>
                        <Td right>{money((snap.fyFig ? snap.fyFig.dep + snap.fyFig.interest + snap.fyFig.unwind - snap.fyFig.modPL : 0)
                          + toNum(cfg.shortTermExp) + toNum(cfg.lowValueExp) + toNum(cfg.variableExp) - toNum(cfg.subleaseIncome))}</Td></tr>
                      {dtOn ? (
                        <tr className="bg-violet-50"><Td cls="font-semibold text-violet-900">Deferred tax credited to profit or loss <span className="ml-1 rounded bg-violet-100 px-1 text-[9px] font-bold text-violet-700">Ind AS 12.81(g)</span></Td>
                          <Td right cls="font-semibold text-violet-800">{"(" + money(dtFy ? dtFy.move : 0) + ")"}</Td></tr>
                      ) : null}
                      <tr className="bg-slate-800 font-bold text-white"><Td>Net charge after deferred tax</Td>
                        <Td right>{money((snap.fyFig ? snap.fyFig.dep + snap.fyFig.interest + snap.fyFig.unwind - snap.fyFig.modPL : 0)
                          + toNum(cfg.shortTermExp) + toNum(cfg.lowValueExp) + toNum(cfg.variableExp) - toNum(cfg.subleaseIncome)
                          - (dtOn && dtFy ? dtFy.move : 0))}</Td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : null}

          {/* ============ PORTFOLIO ============ */}
          {tab === "port" ? (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div>
                  <h3 className="text-xs font-bold text-slate-800">Lease Portfolio and Consolidated Disclosures</h3>
                  <p className="text-[10.5px] text-slate-500">{portfolio.length + " record(s) persisted in " + StoreEngine + ", consolidated as on " + fmtDate(parseISO(reportingISO))}</p>
                  <p className="text-[10.5px] text-slate-500">{lastBackup ? "Last backup taken on " + fmtDate(parseISO(lastBackup.slice(0, 10))) : "No backup has been taken yet"}</p>
                </div>
                <div className="no-print flex flex-wrap gap-2">
                  <button onClick={saveLease} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-emerald-700">Save current</button>
                  <button onClick={backupPortfolio} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-[11px] font-bold text-white hover:bg-indigo-700">Backup all</button>
                  <label className="cursor-pointer rounded-lg border border-indigo-300 px-3 py-1.5 text-[11px] font-bold text-indigo-700 hover:bg-indigo-50">
                    Restore backup<input type="file" accept="application/json" onChange={restoreBackup} className="hidden" />
                  </label>
                  <button onClick={exportJSON} className="rounded-lg border border-slate-300 px-3 py-1.5 text-[11px] font-bold text-slate-600 hover:bg-slate-50">Export JSON</button>
                  <label className="cursor-pointer rounded-lg border border-slate-300 px-3 py-1.5 text-[11px] font-bold text-slate-600 hover:bg-slate-50">
                    Import JSON<input type="file" accept="application/json" onChange={importJSON} className="hidden" />
                  </label>
                  <button onClick={loadPortfolio} className="rounded-lg border border-slate-300 px-3 py-1.5 text-[11px] font-bold text-slate-600 hover:bg-slate-50">Refresh</button>
                </div>
              </div>


              {!portRes.length ? (
                <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white/60 p-10 text-center">
                  <p className="text-sm font-bold text-slate-700">The portfolio is empty</p>
                </div>
              ) : (
                <React.Fragment>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
                    <Card tone="indigo" symbol={S} label="Total ROU assets" value={money(consol.nbv)} sub={portRes.length + " lease(s)"} />
                    <Card tone="emerald" symbol={S} label="Total lease liabilities" value={money(consol.liab)}
                      foot={"Current " + S + money(consol.current) + " | non current " + S + money(consol.nonCurrent)} />
                    <Card tone="amber" symbol={S} label="Annual charge before tax" value={money(consol.dep + consol.interest)} />
                    <Card tone="violet" symbol={S} label="Net deferred tax" value={br(consol.dt)}
                      sub={"Annual deferred tax income " + S + br(consol.dtMove)} />
                    <Card tone="slate" label="Weighted average rate" value={consol.wavg.toFixed(2) + " percent"} />
                  </div>

                  <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                    <h4 className="border-b border-slate-100 px-5 py-3 text-xs font-bold text-slate-800">Portfolio Register</h4>
                    <div className="overflow-auto">
                      <table className="w-full min-w-[1240px] text-xs">
                        <thead className="bg-slate-800 text-white">
                          <tr><Th>Lease</Th><Th>Class</Th><Th>Source</Th><Th>Commencement</Th><Th center>Term</Th>
                            <Th right>Rate</Th><Th right>Tax rate</Th><Th right>Liability</Th><Th right>ROU</Th>
                            <Th right>Net deferred tax</Th><Th center>Actions</Th></tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {portRes.map(function (o) {
                            return (
                              <tr key={o.cfg.id} className="odd:bg-white even:bg-slate-50/70 hover:bg-indigo-50/50">
                                <Td><span className="font-semibold text-slate-800">{o.cfg.name}</span><br /><span className="text-[10px] text-slate-400">{o.cfg.lessor + " | " + o.cfg.id}</span></Td>
                                <Td cls="text-slate-600">{o.cfg.assetClass}</Td>
                                <Td cls="text-[10px] text-indigo-600">{o.cfg.sourceDoc || "\u2014"}</Td>
                                <Td cls="num text-slate-500">{fmtDate(o.res.meta.start)}</Td>
                                <Td center cls="num">{o.res.N + "m"}</Td>
                                <Td right>{toNum(o.cfg.rate).toFixed(2) + "%"}</Td>
                                <Td right cls="text-slate-500">{o.cfg.dtOn ? toNum(o.cfg.dtRate).toFixed(2) + "%" : "\u2014"}</Td>
                                <Td right cls="font-semibold">{money(o.snap.liab)}</Td>
                                <Td right cls="font-semibold text-indigo-700">{money(o.snap.nbv)}</Td>
                                <Td right cls="font-semibold text-violet-700">{o.cfg.dtOn ? br(o.snap.dt) : "\u2014"}</Td>
                                <Td center>
                                  <span className="no-print flex justify-center gap-2">
                                    <button onClick={function () { loadLease(o.cfg); }} className="rounded bg-slate-900 px-2 py-1 text-[10px] font-bold text-white">Load</button>
                                    <button onClick={function () { delLease(o.cfg.id); }} className="rounded border border-rose-300 px-2 py-1 text-[10px] font-bold text-rose-600">Delete</button>
                                  </span>
                                </Td>
                              </tr>
                            );
                          })}
                        </tbody>
                        <tfoot className="bg-slate-100 font-bold">
                          <tr>
                            <td colSpan={7} className="px-3 py-3 text-[10px] uppercase tracking-wider">Consolidated total</td>
                            <Td right>{money(consol.liab)}</Td><Td right>{money(consol.nbv)}</Td>
                            <Td right>{br(consol.dt)}</Td><Td>{null}</Td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>
                </React.Fragment>
              )}
            </div>
          ) : null}

          {res ? (
            <div className="mt-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h4 className="text-xs font-bold text-slate-800">Scope, Assumptions and Areas Requiring Professional Judgement</h4>
              <ul className="mt-3 grid list-outside list-disc gap-1.5 pl-4 text-[11.5px] leading-relaxed text-slate-600 md:grid-cols-2">
                <li>The lease term is an input. Concluding that extension or termination options are reasonably certain under para 18 and B37 to B40 is a judgement to be documented separately.</li>
                <li>Index linked rentals must be modelled through the payment grid, since para 42(b) requires remeasurement only when cash flows actually change.</li>
                <li>Variable payments linked to sales or usage are excluded from the liability under para 27(b) and expensed as incurred.</li>
                <li>Security deposits are financial assets under Ind AS 109. Only the discount on an interest free deposit becomes prepaid rent inside the ROU asset.</li>
                <li>Deferred tax assumes the tax base selected in section six. Verify the deductibility of rent, brokerage and restoration costs against the entity's own tax position.</li>
                <li>For interim periods, Ind AS 34.B12 requires tax to be accrued at the estimated annual effective tax rate, which may differ from the schedule driven figure shown here.</li>
                <li>Impairment under Ind AS 36, sale and leaseback under para 98 to 103, and lessor or sublease accounting remain outside scope.</li>
                <li>Minimum alternate tax credit, carried forward losses and unabsorbed depreciation are not modelled.</li>
                {shortTerm ? <li className="font-bold text-amber-700">The term is twelve months or less. Evaluate the short term exemption in para 5 and 6 before capitalising, which would also remove the deferred tax difference.</li> : null}
                {res.residualNBV > 1 ? <li className="font-bold text-amber-700">The ROU asset retains a carrying amount at expiry, leaving a residual taxable temporary difference. Verify the transfer of ownership conclusion.</li> : null}
              </ul>
            </div>
          ) : null}
        </section>
      </main>

      <footer className="no-print border-t border-slate-200 bg-white py-5 text-center">
        <p className="text-[10.5px] text-slate-400">
          {"Ind AS 116 and Ind AS 12 lessee engine, version 4. Storage engine " + StoreEngine +
           ". Output must be reviewed by a qualified professional before it is incorporated into financial statements."}
        </p>
      </footer>
    </div>
  );
}


export default App;
