// @ts-nocheck
import { uid } from "./core";

/* ------------------------------------------------- 7. DEFAULTS */
export function blankCfg() {
  return {
    id: uid(), name: "", lessor: "",
    assetClass: "Buildings - Office Premises",
    startDate: new Date().toISOString().slice(0, 10),
    termMonths: 0, basePayment: 0, rate: 0,
    timing: "begin", rateBasis: "simple", day1Basis: "market",
    escMode: "percent", escPct: 0, escAmt: 0, escFreq: 12,
    rentFreeMonths: 0, rentFreePos: "start", rentFreeList: "",
    idc: 0, prepaid: 0, incentive: 0, aroCost: 0, aroRate: 0,
    securityDeposit: 0, usefulLifeMonths: 0, transferOwnership: false,
    fyBasis: "mar", symbol: "\u20B9", reportingDate: "",
    shortTermExp: 0, lowValueExp: 0, variableExp: 0, subleaseIncome: 0,
    mods: [], overrides: {},
    /* Ind AS 12 deferred tax */
    dtOn: true, dtRate: 25.168, dtRateSchedule: [], dtTreatment: "rentAccrual",
    dtIncludeAro: true, dtApproach: "gross", dtOffset: true,
    dtRestrict: false, dtRecognisePct: 100,
    dtTaxDepMethod: "wdv", dtTaxDepRate: 0, dtTaxLifeMonths: 0,
    transitionOn: false, transitionDate: "", transitionRate: 0,
    transitionApproach: "B", prepaidAtTransition: 0, accruedAtTransition: 0,
    sourceDoc: ""
  };
}
export function newMod() {
  return { id: uid(), enabled: true, label: "",
    type: "remeasure", month: 1, newTerm: 0, newPayment: 0,
    newRate: 0, escPct: 0, escFreq: 12, scopePct: 0 };
}
export var ASSET_CLASSES = ["Buildings - Office Premises", "Buildings - Retail Stores",
  "Buildings - Warehouse", "Land", "Plant and Machinery", "Motor Vehicles",
  "IT and Office Equipment", "Others"];
export var DT_TREATMENTS = [
  ["rentAccrual", "Rentals deductible for tax, ROU and liability have a nil tax base"],
  ["taxDep", "Tax depreciation allowed on the asset, tax base is the written down value"],
  ["none", "No temporary difference, tax follows the book treatment"]
];
