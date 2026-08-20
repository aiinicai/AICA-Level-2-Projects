var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/engine/cmaEngine.ts
var cmaEngine_exports = {};
__export(cmaEngine_exports, {
  DEFAULT_BLOCKS: () => DEFAULT_BLOCKS,
  RATIO_TARGETS: () => RATIO_TARGETS,
  assessFeasibility: () => assessFeasibility,
  autoFixParams: () => autoFixParams,
  buildDepSchedule: () => buildDepSchedule,
  buildEmiSchedule: () => buildEmiSchedule,
  defaultSimParams: () => defaultSimParams,
  fyLabel: () => fyLabel,
  makeEmptyActual: () => makeEmptyActual,
  runCma: () => runCma
});
module.exports = __toCommonJS(cmaEngine_exports);
var RATIO_TARGETS = {
  currentRatio: { target: 1.23, direction: "min", label: "Current Ratio" },
  dscr: { target: 1.75, direction: "min", label: "DSCR" },
  debtEquity: { target: 3, direction: "max", label: "Debt / Equity" },
  tolTnw: { target: 4.5, direction: "max", label: "TOL / TNW" },
  interestCoverage: { target: 2.6, direction: "min", label: "Interest Coverage" }
};
var DEFAULT_BLOCKS = [
  { id: "plantMachinery", name: "Plant & Machinery", rate: 15, opening: 0 },
  { id: "furniture", name: "Furniture & Fixtures", rate: 10, opening: 0 },
  { id: "building", name: "Building", rate: 10, opening: 0 },
  { id: "computer", name: "Computers", rate: 40, opening: 0 },
  { id: "other1", name: "Other Asset 1", rate: 15, opening: 0 },
  { id: "other2", name: "Other Asset 2", rate: 15, opening: 0 }
];
var EXPENSE_KEYS = [
  "powerFuel",
  "directLabour",
  "salary",
  "freight",
  "salesPromo",
  "travelAdmin",
  "repairs",
  "professionalFees",
  "operatingExp",
  "otherExp",
  "customExp1",
  "customExp2"
];
var VARIABLE_KEYS = ["powerFuel", "directLabour", "freight", "salesPromo"];
function makeEmptyActual(label) {
  return {
    label,
    months: 12,
    salesDomestic: 0,
    salesExport: 0,
    otherIncome: 0,
    rmOpening: 0,
    rmPurchases: 0,
    rmClosing: 0,
    powerFuel: 0,
    directLabour: 0,
    salary: 0,
    freight: 0,
    salesPromo: 0,
    travelAdmin: 0,
    repairs: 0,
    professionalFees: 0,
    operatingExp: 0,
    otherExp: 0,
    customExp1: 0,
    customExp2: 0,
    customExp1Name: "Other Expense 1",
    customExp2Name: "Other Expense 2",
    depreciation: 0,
    interestCC: 0,
    interestTL: 0,
    bankCharges: 0,
    tax: 0,
    dividend: 0,
    fixedAssets: 0,
    deposits: 0,
    investments: 0,
    debtors: 0,
    cash: 0,
    otherCurrentAssets: 0,
    shareCapital: 0,
    reserves: 0,
    termLoan: 0,
    cc: 0,
    unsecured: 0,
    creditors: 0,
    otherCurrentLiab: 0,
    customValues: {}
  };
}
function defaultSimParams() {
  return {
    salesGrowth: 10,
    marginAdj: 0,
    inventoryDays: 60,
    debtorDays: 45,
    creditorDays: 30,
    taxRate: 25,
    dividendPct: 0,
    minCashBalance: 1e5,
    tlAssetBlockId: "plantMachinery",
    manualAssetAdditions: {}
  };
}
function fyLabel(startYear, i) {
  const y = startYear + i;
  return `${y}-${(y + 1).toString().slice(-2)}`;
}
function buildEmiSchedule(config) {
  const loan = config.loan;
  if (loan.tlAmount <= 0 || loan.loanType === "cc" || loan.tlTenureMonths <= 0) return [];
  const monthlyRate = loan.tlRate / 12 / 100;
  const moratorium = Math.min(loan.tlMoratoriumMonths, loan.tlTenureMonths - 1);
  const repayMonths = loan.tlTenureMonths - moratorium;
  const emi = monthlyRate === 0 ? loan.tlAmount / repayMonths : monthlyRate * loan.tlAmount * Math.pow(1 + monthlyRate, repayMonths) / (Math.pow(1 + monthlyRate, repayMonths) - 1);
  const grantYear = config.startYear + config.actualYears;
  const grantDate = new Date(grantYear, 3 + loan.grantMonthIndex, loan.grantDay || 1);
  const rows = [];
  let balance = loan.tlAmount;
  for (let m = 1; m <= loan.tlTenureMonths; m++) {
    const date = new Date(grantDate.getFullYear(), grantDate.getMonth() + m, loan.emiDay || 10);
    const interest = balance * monthlyRate;
    const inMoratorium = m <= moratorium;
    let principal = inMoratorium ? 0 : Math.min(emi - interest, balance);
    if (principal < 0) principal = 0;
    const paid = inMoratorium ? interest : interest + principal;
    balance -= principal;
    const monthsFromApril = (date.getFullYear() - grantYear) * 12 + (date.getMonth() - 3);
    const fyIndex = config.actualYears + Math.floor(monthsFromApril / 12);
    rows.push({
      month: m,
      date: date.toISOString().slice(0, 10),
      fyIndex,
      opening: balance + principal,
      emi: paid,
      interest,
      principal,
      closing: balance,
      moratorium: inMoratorium
    });
  }
  return rows;
}
function buildDepSchedule(config, sim) {
  const totalYears = config.actualYears + config.estimatedYears + config.projectedYears;
  const blocks = config.assetBlocks.map((b) => ({ ...b }));
  const out = [];
  let openings = {};
  blocks.forEach((b) => {
    openings[b.id] = b.opening;
  });
  for (let i = 0; i < totalYears; i++) {
    const isFirstEstimate = i === config.actualYears;
    const blockYears = blocks.map((b) => {
      let addition = 0;
      if (isFirstEstimate && b.id === sim.tlAssetBlockId && config.loan.loanType !== "cc") {
        addition += config.loan.tlAmount;
      }
      addition += sim.manualAssetAdditions[b.id]?.[i] || 0;
      const opening = openings[b.id];
      const depreciation = (opening + addition) * (b.rate / 100);
      const closing = opening + addition - depreciation;
      openings[b.id] = closing;
      return { id: b.id, name: b.name, rate: b.rate, opening, addition, depreciation, closing };
    });
    out.push({
      yearIndex: i,
      blocks: blockYears,
      totalDep: blockYears.reduce((s, b) => s + b.depreciation, 0),
      totalNetBlock: blockYears.reduce((s, b) => s + b.closing, 0)
    });
  }
  return out;
}
function sumEmi(schedule, fyIndex, field) {
  return schedule.filter((r) => r.fyIndex === fyIndex).reduce((s, r) => s + r[field], 0);
}
function runCma(config, sim) {
  const { emi, dep, years } = computeYears(config, sim);
  const feasibility = assessFeasibility(config, sim, years);
  const totalYears = config.actualYears + config.estimatedYears + config.projectedYears;
  return { config, sim, totalYears, emiSchedule: emi, depSchedule: dep, years, feasibility };
}
function computeYears(config, sim) {
  const totalYears = config.actualYears + config.estimatedYears + config.projectedYears;
  const emi = buildEmiSchedule(config);
  const dep = buildDepSchedule(config, sim);
  const years = [];
  const base = config.actuals[config.actuals.length - 1];
  const baseSales = base.salesDomestic + base.salesExport;
  const baseRmConsumed = base.rmOpening + base.rmPurchases - base.rmClosing;
  const rate = (v) => baseSales > 0 ? v / baseSales : 0;
  const baseRmRate = rate(baseRmConsumed);
  const expenseRates = {};
  EXPENSE_KEYS.forEach((k) => {
    expenseRates[k] = rate(base[k]);
  });
  const customHeads = config.customHeads || [];
  const customExpRates = {};
  customHeads.filter((h) => h.kind === "expense").forEach((h) => {
    customExpRates[h.id] = rate(base.customValues?.[h.id] || 0);
  });
  let prevSales = baseSales;
  let prevReserves = base.reserves;
  let prevRmClosing = base.rmClosing;
  for (let i = 0; i < totalYears; i++) {
    const isActual = i < config.actualYears;
    const a = isActual ? config.actuals[i] : void 0;
    const tlInterest = sumEmi(emi, i, "interest");
    const tlPrincipal = sumEmi(emi, i, "principal");
    const cpltd = sumEmi(emi, i + 1, "principal");
    const lastEmi = [...emi].reverse().find((r) => r.fyIndex === i);
    const y = {};
    y.yearIndex = i;
    y.year = fyLabel(config.startYear, i);
    y.type = isActual ? "Actual" : i < config.actualYears + config.estimatedYears ? "Estimated" : "Projected";
    y.months = a?.months ?? 12;
    if (isActual && a) {
      y.salesDomestic = a.salesDomestic;
      y.salesExport = a.salesExport;
      y.sales = a.salesDomestic + a.salesExport;
      y.otherIncome = a.otherIncome;
      y.rmOpening = a.rmOpening;
      y.rmPurchases = a.rmPurchases;
      y.rmClosing = a.rmClosing;
      y.rmConsumed = a.rmOpening + a.rmPurchases - a.rmClosing;
      EXPENSE_KEYS.forEach((k) => {
        y[k] = a[k];
      });
      y.depreciation = a.depreciation > 0 ? a.depreciation : dep[i]?.totalDep || 0;
      y.interestCC = a.interestCC;
      y.interestTL = a.interestTL;
      y.bankCharges = a.bankCharges;
      y.interest = a.interestCC + a.interestTL + a.bankCharges;
      y.tax = a.tax;
      y.dividend = a.dividend;
      y.customHeadValues = {};
      customHeads.forEach((h) => {
        y.customHeadValues[h.id] = a.customValues?.[h.id] || 0;
      });
    } else {
      const g = sim.salesGrowth / 100;
      const eff = 1 - sim.marginAdj / 100;
      y.sales = prevSales * (1 + g);
      y.salesDomestic = y.sales;
      y.salesExport = 0;
      y.otherIncome = 0;
      y.rmConsumed = y.sales * baseRmRate * eff;
      y.rmOpening = prevRmClosing;
      y.rmClosing = y.sales / 365 * sim.inventoryDays;
      y.rmPurchases = y.rmConsumed + y.rmClosing - y.rmOpening;
      EXPENSE_KEYS.forEach((k) => {
        y[k] = y.sales * expenseRates[k] * eff;
      });
      y.depreciation = dep[i]?.totalDep || 0;
      y.customHeadValues = {};
      customHeads.forEach((h) => {
        const baseVal = base.customValues?.[h.id] || 0;
        if (h.kind === "expense") y.customHeadValues[h.id] = y.sales * (customExpRates[h.id] || 0) * eff;
        else if (h.kind === "asset") y.customHeadValues[h.id] = baseVal;
        else y.customHeadValues[h.id] = h.current ? baseVal * Math.pow(1.05, i - config.actualYears + 1) : baseVal;
      });
      let ccInt = 0;
      if (config.loan.loanType !== "tl") {
        const grantFy = config.actualYears;
        if (i < grantFy) ccInt = 0;
        else if (i === grantFy) ccInt = config.loan.ccLimit * (config.loan.ccRate / 100) * ((12 - config.loan.grantMonthIndex) / 12);
        else ccInt = config.loan.ccLimit * (config.loan.ccRate / 100);
      }
      y.interestCC = ccInt;
      y.interestTL = tlInterest;
      y.bankCharges = base.bankCharges;
      y.interest = ccInt + tlInterest + y.bankCharges;
      const pbtEst = 0;
      void pbtEst;
    }
    const customExpTotal = customHeads.filter((h) => h.kind === "expense").reduce((s, h) => s + (y.customHeadValues[h.id] || 0), 0);
    y.totalExpenses = EXPENSE_KEYS.reduce((s, k) => s + y[k], 0) + customExpTotal;
    y.ebitda = y.sales + y.otherIncome - (y.rmConsumed + y.totalExpenses);
    y.pbt = y.ebitda - y.interest - y.depreciation;
    if (!isActual) {
      y.tax = y.pbt > 0 ? y.pbt * (sim.taxRate / 100) : 0;
      y.dividend = 0;
    }
    y.pat = y.pbt - y.tax;
    if (!isActual) y.dividend = y.pat > 0 ? y.pat * (sim.dividendPct / 100) : 0;
    y.retained = y.pat - y.dividend;
    y.netCashAccrual = y.pat + y.depreciation;
    y.salesGrowthPct = i === 0 ? null : prevSales > 0 ? (y.sales / prevSales - 1) * 100 : 0;
    y.shareCapital = base.shareCapital;
    y.reserves = isActual && a ? a.reserves : prevReserves + y.retained;
    if (isActual && a) {
      y.termLoan = a.termLoan;
    } else if (config.loan.loanType === "cc") {
      y.termLoan = 0;
    } else {
      y.termLoan = lastEmi ? lastEmi.closing : i < config.actualYears ? 0 : Math.max(0, config.loan.tlAmount);
      if (!lastEmi && i >= config.actualYears) {
        const granted = emi.length > 0 && i >= emi[0].fyIndex;
        y.termLoan = granted ? config.loan.tlAmount - sumEmi(emi, i, "principal") : 0;
      }
    }
    y.cpltd = isActual ? 0 : cpltd;
    y.cc = isActual && a ? a.cc : config.loan.loanType !== "tl" ? config.loan.ccLimit : 0;
    y.unsecured = base.unsecured;
    y.creditors = isActual && a ? a.creditors : y.rmPurchases / 365 * sim.creditorDays;
    y.otherCurrentLiab = isActual && a ? a.otherCurrentLiab : base.otherCurrentLiab * Math.pow(1.05, i - config.actualYears + 1);
    y.fixedAssets = isActual && a ? a.fixedAssets : dep[i]?.totalNetBlock || 0;
    y.deposits = base.deposits;
    y.investments = base.investments;
    y.stock = isActual && a ? a.rmClosing : y.rmClosing;
    y.debtors = isActual && a ? a.debtors : y.sales / 365 * sim.debtorDays;
    y.otherCurrentAssets = base.otherCurrentAssets;
    const customAssetTotal = customHeads.filter((h) => h.kind === "asset").reduce((s, h) => s + (y.customHeadValues[h.id] || 0), 0);
    const customLiabTotal = customHeads.filter((h) => h.kind === "liability").reduce((s, h) => s + (y.customHeadValues[h.id] || 0), 0);
    const customCurrentAssetTotal = customHeads.filter((h) => h.kind === "asset" && h.current).reduce((s, h) => s + (y.customHeadValues[h.id] || 0), 0);
    const customCurrentLiabTotal = customHeads.filter((h) => h.kind === "liability" && h.current).reduce((s, h) => s + (y.customHeadValues[h.id] || 0), 0);
    const totalLiabExCashPlug = y.shareCapital + y.reserves + y.termLoan + y.cc + y.unsecured + y.creditors + y.otherCurrentLiab + customLiabTotal;
    const assetsExCash = y.fixedAssets + y.stock + y.debtors + y.deposits + y.investments + y.otherCurrentAssets + customAssetTotal;
    if (isActual && a) {
      y.cash = a.cash;
    } else {
      let balCash = totalLiabExCashPlug - assetsExCash;
      if (balCash < sim.minCashBalance) {
        y.unsecured += sim.minCashBalance - balCash;
        y.cash = sim.minCashBalance;
      } else {
        y.cash = balCash;
      }
    }
    y.totalLiabilities = y.shareCapital + y.reserves + y.termLoan + y.cc + y.unsecured + y.creditors + y.otherCurrentLiab + customLiabTotal;
    y.totalAssets = y.fixedAssets + y.stock + y.debtors + y.cash + y.deposits + y.investments + y.otherCurrentAssets + customAssetTotal;
    y.bsDifference = y.totalLiabilities - y.totalAssets;
    y.netWorth = y.shareCapital + y.reserves;
    y.totalOutsideLiab = y.totalLiabilities - y.netWorth;
    y.currentAssets = y.stock + y.debtors + y.cash + y.otherCurrentAssets + customCurrentAssetTotal;
    y.currentLiabilities = y.cc + y.creditors + y.otherCurrentLiab + y.cpltd + customCurrentLiabTotal;
    y.workingCapitalGap = y.currentAssets - (y.creditors + y.otherCurrentLiab);
    y.netWorkingCapital = y.currentAssets - y.currentLiabilities;
    const longTermDebt = Math.max(0, y.termLoan - y.cpltd);
    y.currentRatio = y.currentLiabilities > 0 ? y.currentAssets / y.currentLiabilities : 0;
    const dscrNum = y.pat + y.depreciation + y.interestTL;
    const dscrDen = y.interestTL + tlPrincipal;
    y.dscr = dscrDen > 0 ? dscrNum / dscrDen : 0;
    y.debtEquity = y.netWorth > 0 ? (longTermDebt + y.unsecured) / y.netWorth : 0;
    y.tolTnw = y.netWorth > 0 ? y.totalOutsideLiab / y.netWorth : 0;
    y.interestCoverage = y.interest > 0 ? (y.pbt + y.interest) / y.interest : 0;
    y.netProfitRatio = y.sales > 0 ? y.pat / y.sales * 100 : 0;
    const capitalEmployed = y.netWorth + y.termLoan;
    y.returnOnInvestment = capitalEmployed > 0 ? y.pat / capitalEmployed * 100 : 0;
    y.debtorDaysActual = y.sales > 0 ? y.debtors / y.sales * 365 : 0;
    y.inventoryDaysActual = y.sales > 0 ? y.stock / y.sales * 365 : 0;
    y.creditorDaysActual = y.rmPurchases > 0 ? y.creditors / y.rmPurchases * 365 : 0;
    const variableCost = y.rmConsumed + VARIABLE_KEYS.reduce((s, k) => s + y[k], 0);
    const fixedCost = y.totalExpenses - VARIABLE_KEYS.reduce((s, k) => s + y[k], 0) + y.depreciation + y.interest;
    const contribution = y.sales + y.otherIncome - variableCost;
    y.breakEvenPct = contribution > 0 ? fixedCost / contribution * 100 : 0;
    y.mpbfGap = y.currentAssets - (y.creditors + y.otherCurrentLiab);
    y.mpbfMinNwc = 0.25 * y.currentAssets;
    y.mpbf = Math.max(0, 0.75 * y.currentAssets - (y.creditors + y.otherCurrentLiab));
    y.mpbfTurnover = Math.max(0, 0.2 * y.sales);
    const dpDebtorsBase = Math.min(y.debtors, y.sales / 365 * config.loan.ccDebtorCoverDays);
    y.dpStock = y.stock * (1 - config.loan.ccStockMarginPct / 100);
    y.dpDebtors = dpDebtorsBase * (1 - config.loan.ccDebtorMarginPct / 100);
    y.dpTotal = y.dpStock + y.dpDebtors;
    y.dpShortfall = y.cc > 0 ? y.cc - y.dpTotal : 0;
    const W = (formula, numerator, denominator, result) => ({
      formula,
      numerator,
      denominator,
      numeratorTotal: numerator.reduce((s, l) => s + l.value, 0),
      denominatorTotal: denominator.reduce((s, l) => s + l.value, 0),
      result
    });
    y.workings = {
      currentRatio: W(
        "Current Assets \xF7 Current Liabilities (incl. CPLTD)",
        [
          { label: "Stock / Inventory", value: y.stock },
          { label: "Debtors / Receivables", value: y.debtors },
          { label: "Cash & Bank", value: y.cash },
          { label: "Other Current Assets", value: y.otherCurrentAssets }
        ],
        [
          { label: "Cash Credit (Bank)", value: y.cc },
          { label: "Creditors / Payables", value: y.creditors },
          { label: "Other Current Liabilities", value: y.otherCurrentLiab },
          { label: "CPLTD (Term Loan due next year)", value: y.cpltd }
        ],
        y.currentRatio
      ),
      dscr: W(
        "(PAT + Depreciation + TL Interest) \xF7 (TL Interest + TL Principal)",
        [
          { label: "Profit After Tax", value: y.pat },
          { label: "Depreciation", value: y.depreciation },
          { label: "Term Loan Interest", value: y.interestTL }
        ],
        [
          { label: "Term Loan Interest", value: y.interestTL },
          { label: "Term Loan Principal Repaid", value: tlPrincipal }
        ],
        y.dscr
      ),
      debtEquity: W(
        "(Long-term Debt + Unsecured Loans) \xF7 Net Worth",
        [
          { label: "Term Loan (excl. CPLTD)", value: longTermDebt },
          { label: "Unsecured Loans", value: y.unsecured }
        ],
        [
          { label: "Share Capital", value: y.shareCapital },
          { label: "Reserves & Surplus", value: y.reserves }
        ],
        y.debtEquity
      ),
      tolTnw: W(
        "Total Outside Liabilities \xF7 Total Net Worth",
        [
          { label: "Term Loan", value: y.termLoan },
          { label: "Cash Credit", value: y.cc },
          { label: "Unsecured Loans", value: y.unsecured },
          { label: "Creditors", value: y.creditors },
          { label: "Other Current Liabilities", value: y.otherCurrentLiab }
        ],
        [
          { label: "Share Capital", value: y.shareCapital },
          { label: "Reserves & Surplus", value: y.reserves }
        ],
        y.tolTnw
      ),
      interestCoverage: W(
        "(PBT + Interest) \xF7 Interest",
        [
          { label: "Profit Before Tax", value: y.pbt },
          { label: "Total Interest", value: y.interest }
        ],
        [
          { label: "Total Interest (CC + TL + Bank Charges)", value: y.interest }
        ],
        y.interestCoverage
      )
    };
    years.push(y);
    prevSales = y.sales;
    prevReserves = y.reserves;
    prevRmClosing = y.rmClosing;
  }
  return { emi, dep, years };
}
function assessFeasibility(config, sim, years) {
  const est = years[config.actualYears];
  if (!est) {
    return { feasible: false, checks: [], maxCcSupportable: 0, maxTlSupportable: 0, minGrowthNeeded: null };
  }
  const checks = Object.entries(RATIO_TARGETS).map(([key, t]) => {
    const value = est[key];
    const pass = t.direction === "min" ? value >= t.target : value <= t.target;
    return { key, name: t.label, value, target: t.target, direction: t.direction, pass };
  });
  if (config.loan.loanType !== "tl") {
    checks.push({
      key: "dp",
      name: "Drawing Power covers CC",
      value: est.dpTotal,
      target: est.cc,
      direction: "min",
      pass: est.dpTotal >= est.cc
    });
  }
  const maxCcSupportable = Math.max(0, Math.min(est.dpTotal || Infinity, est.mpbf || Infinity, est.mpbfTurnover || Infinity));
  const dscrYears = years.slice(config.actualYears);
  let maxTl = 0;
  const avgEbitda = dscrYears.reduce((s, y) => s + y.ebitda, 0) / Math.max(1, dscrYears.length);
  const avgTax = dscrYears.reduce((s, y) => s + y.tax, 0) / Math.max(1, dscrYears.length);
  const serviceCapacity = Math.max(0, (avgEbitda - avgTax) / RATIO_TARGETS.dscr.target);
  if (config.loan.tlRate > 0 && config.loan.tlTenureMonths > config.loan.tlMoratoriumMonths) {
    const r = config.loan.tlRate / 12 / 100;
    const n = config.loan.tlTenureMonths - config.loan.tlMoratoriumMonths;
    const annuityFactor = r > 0 ? (Math.pow(1 + r, n) - 1) / (r * Math.pow(1 + r, n)) : n;
    maxTl = serviceCapacity / 12 * annuityFactor;
  }
  let minGrowth = null;
  const allPass = (growth) => {
    const { years: ys } = computeYears(config, { ...sim, salesGrowth: growth });
    const e = ys[config.actualYears];
    if (!e) return false;
    return e.currentRatio >= RATIO_TARGETS.currentRatio.target && (e.dscr === 0 || e.dscr >= RATIO_TARGETS.dscr.target) && e.debtEquity <= RATIO_TARGETS.debtEquity.target && e.tolTnw <= RATIO_TARGETS.tolTnw.target && (e.interestCoverage === 0 || e.interestCoverage >= RATIO_TARGETS.interestCoverage.target) && (config.loan.loanType === "tl" || e.dpTotal >= e.cc);
  };
  if (allPass(sim.salesGrowth)) {
    minGrowth = sim.salesGrowth;
  } else {
    let lo = sim.salesGrowth, hi = 100;
    if (allPass(hi)) {
      for (let k = 0; k < 40; k++) {
        const mid = (lo + hi) / 2;
        if (allPass(mid)) hi = mid;
        else lo = mid;
      }
      minGrowth = Math.ceil(hi * 10) / 10;
    }
  }
  return {
    feasible: checks.every((c) => c.pass || c.key === "dscr" && c.value === 0 || c.key === "interestCoverage" && c.value === 0),
    checks,
    maxCcSupportable,
    maxTlSupportable: maxTl,
    minGrowthNeeded: minGrowth
  };
}
function autoFixParams(config, sim) {
  let candidate = { ...sim };
  for (let step = 0; step < 25; step++) {
    const res = runCma(config, candidate);
    if (res.feasibility.feasible) return candidate;
    candidate = {
      ...candidate,
      salesGrowth: Math.min(60, candidate.salesGrowth + 2),
      marginAdj: Math.min(15, candidate.marginAdj + 1),
      inventoryDays: Math.max(15, candidate.inventoryDays - 2),
      debtorDays: Math.max(15, candidate.debtorDays - 2)
    };
  }
  return candidate;
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  DEFAULT_BLOCKS,
  RATIO_TARGETS,
  assessFeasibility,
  autoFixParams,
  buildDepSchedule,
  buildEmiSchedule,
  defaultSimParams,
  fyLabel,
  makeEmptyActual,
  runCma
});
