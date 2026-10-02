/* ==================================================================
   LookThrough core — state, formatting, audit, small helpers
   ================================================================== */
const SAMPLE = /*__DATA__*/null;
let DB = JSON.parse(JSON.stringify(SAMPLE));
const AUDIT = [];
const state = {
  view: "dashboard", member: "ALL", units: "cr",
  sort: {}, search: {}, tab: {}, sel: {},
  company: "HDFCBANK", fund: "S04", pair: null, heldOnly: true,
  ltGroup: "stock", assetFilter: "ALL", actScheme: "S04",
  screen: "quality", filters: [], stressSc: "m20", custom: { market: -15, sector: "Financial Services", shock: -10 },
  sim: null, whatIf: 5000000, extracted: null, srcText: null,
};
const prefs = {
  get(k, d) { try { const v = localStorage.getItem("lt." + k); return v == null ? d : v; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("lt." + k, v); } catch (e) { /* storage unavailable */ } },
};

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const isNum = v => v != null && v !== "" && isFinite(v);

/* ---------- number formatting (Indian system) ---------- */
const nf = (v, d = 2) => Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtN = (v, d = 2) => isNum(v) ? (v < 0 && nf(Math.abs(v), d) !== nf(0, d) ? "−" : "") + nf(Math.abs(v), d) : "—";  // true minus sign
const fmtPct = (v, d = 1) => !isNum(v) ? "—" : v !== 0 && nf(Math.abs(v), d) === nf(0, d) ? (v < 0 ? "−" : "") + "<" + nf(Math.pow(10, -d), d) + "%"  // a real but tiny share: "<0.1%", not "0.0%"
  : (v < 0 ? "−" : "") + nf(Math.abs(v), d) + "%";  // a true minus sign, as in fmtSPct
const fmtSPct = (v, d = 1) => !isNum(v) ? "—" : v !== 0 && nf(Math.abs(v), d) === nf(0, d) ? (v > 0 ? "+" : "−") + "<" + nf(Math.pow(10, -d), d) + "%"  // tiny: "+<0.1%", not "+0.0%"
  : (v > 0 ? "+" : v < 0 ? "−" : "") + nf(Math.abs(v), d) + "%";
const fmtX = (v, d = 2) => isNum(v) ? nf(v, d) + "×" : "—";
const fmtCr = (v, d = 2) => isNum(v) ? (v < 0 ? "−" : "") + "₹" + nf(Math.abs(v) / 1e7, d) + "\u00a0Cr" : "—";  // no-break space: "₹3.18 L" never splits
/** Amount in the unit the viewer picked (Cr / Lakh / ₹). */
/** Crore for large amounts, lakh below ₹1 crore (used where values are small, e.g. tax). */
const fmtAuto = (v, o = {}) => !isNum(v) ? "—" : fmtAmt(v, { ...o, unit: state.units === "inr" ? "inr" : Math.abs(v) >= 1e7 ? "cr" : "lakh" });
/** Set by table() while it formats one column: every amount in that column uses the same unit. */
let AMT_UNIT = null;
function fmtAmt(v, opts = {}) {
  if (!isNum(v)) return "—";
  const neg = v < 0, a = Math.abs(v), u = opts.unit || AMT_UNIT || state.units;
  if (AMT_UNIT === "cr" && !opts.unit && a > 0 && a < 5e4) return (neg ? "−" : "") + "<₹0.01\u00a0Cr";  // tiny, in a crore column
  let s;
  // Below Rs 0.10 Cr the crore view would print Rs 0.00-0.09 Cr; show lakh instead so small amounts stay readable
  // (outside tables; a table column keeps one unit, see table()).
  const cr = u === "cr" && (AMT_UNIT === "cr" || !(a > 0 && a < 1e6));
  if (cr) s = "₹" + nf(a / 1e7, opts.d ?? 2) + "\u00a0Cr";
  else if (u === "cr") s = "₹" + nf(a / 1e5, opts.d ?? 2) + "\u00a0L";
  else if (u === "lakh") s = "₹" + nf(a / 1e5, opts.d ?? 2) + "\u00a0L";
  else s = "₹" + nf(a, opts.d ?? 0);
  const zero = /^₹0(\.0+)?(\s|$)/.test(s);  // never print a negative (or signed) zero
  return (neg && !zero ? "−" : opts.sign && v > 0 && !zero ? "+" : "") + s;
}
/** Lakh (or rupees) for columns of tax-sized amounts, so a column never mixes Cr and L. */
const fmtL = (v, o = {}) => fmtAmt(v, { ...o, unit: state.units === "inr" ? "inr" : "lakh" });
const unitLabel = () => ({ cr: "₹ crore", lakh: "₹ lakh", inr: "₹" }[state.units]);
const unitDiv = () => ({ cr: 1e7, lakh: 1e5, inr: 1 }[state.units]);
const fmtDate = s => { if (!s) return "—"; const [y, m, d] = s.split("-"); return `${d} ${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+m - 1]} ${y}`; };
const fmtMon = s => { const [y, m] = s.split("-"); return `${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+m - 1]} ${y.slice(2)}`; };
const clsNum = v => !isNum(v) ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "";
const ACRONYMS = new Set(["ITC", "NTPC", "DLF", "HDFC", "ICICI", "SBI", "HCL", "LIC", "PB", "TVS", "BSE", "NSE", "NHPC", "GAIL", "ONGC", "BPCL", "HPCL",
  "IOC", "IRCTC", "IRFC", "REC", "PFC", "BHEL", "MRF", "ABB", "UPL", "JSW", "SRF", "ACC", "UTI", "AU", "IDFC", "IDBI", "RBL", "KPIT", "HUL", "NMDC", "SAIL",
  "BEL", "HAL", "EIH", "PVR", "INOX", "IT", "AMC", "L&T", "SEZ", "NBFC", "PSU", "CG", "PI", "KEI", "APL", "GMR", "JK", "MM", "TTK", "SKF", "IFB", "ICRA", "CRISIL", "CDSL", "CAMS", "MCX", "IEX", "LTI", "SJVN", "IREDA", "RVNL", "HUDCO", "NLC", "NBCC", "GE", "HFCL", "BLS", "PNB", "DCB", "CSB", "IIFL", "UCO", "ITI"]);
/** Standard short forms, used only when a name does not fit its space ("Sun Pharmaceutical Industries" -> "Sun Pharma Inds"). */
const SHORT_FORMS = [[/ Consultancy Services\b/, " Consultancy"], [/\bCorporation of India\b/, "Corp of India"], [/\bMutual Fund\b/, "MF"],
  [/\bPharmaceuticals?\b/, "Pharma"], [/\bIndustries\b/, "Inds"], [/\bCorporation\b/, "Corp"], [/\bTechnolog(y|ies)\b/, "Tech"], [/\bPrudential\b/, "Pru"],
  [/\bInsurance\b/, "Ins"], [/\bInternational\b/, "Intl"], [/\bManagement\b/, "Mgmt"], [/\bEngineering\b/, "Engg"], [/\bInfrastructure\b/, "Infra"],
  [/\bEnterprises\b/, "Ent"], [/\bFinancial\b/, "Fin"], [/\bServices\b/, "Svcs"], [/\bLaboratories\b/, "Labs"], [/\bAeronautics\b/, "Aero"],
  [/\bAggressive\b/, "Aggr"], [/\bAutomobiles?\b/, "Auto"], [/\bElectronics\b/, "Elec"], [/\bChemicals\b/, "Chem"], [/\bPetroleum\b/, "Petro"],
  [/\bDevelopment\b/, "Dev"], [/\bCompany\b/, "Co"], [/\bVentures\b/, "Ventures"]];
const compactName = s => SHORT_FORMS.reduce((t, [re, r]) => t.replace(re, r), String(s)).replace(/\s{2,}/g, " ").trim();
/** A label in at most n characters: as is, else with standard short forms, else cut at a word boundary. */
const fitLabel = (s, n) => s.length <= n ? s : (c => c.length <= n ? c : fitText(c, n))(compactName(s));
/** Normal case for names published in capitals (acronyms kept); names already in mixed case are left as they are. */
const niceCase = s => (/[a-z]/.test(s) ? s : s.replace(/[A-Za-z][A-Za-z.&']*/g, w => ACRONYMS.has(w.replace(/\.$/, "")) ? w : w.charAt(0) + w.slice(1).toLowerCase()))
  .replace(/ (Of|And|The|For|In|On|At|To)(?= )/g, m => m.toLowerCase());  // small words lower case in every name: "Life Insurance Corporation of India"
const shortName = s => niceCase(String(s)).replace(/,?\s+(Limited|Ltd\.?)$/i, "").replace(/ Fund$/, "");

function log(action, detail) { AUDIT.unshift({ ts: new Date().toISOString(), action, detail }); }
function toast(msg, kind = "") {
  const t = $("#toast"); t.textContent = msg; t.className = "toast on " + kind;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.className = "toast"), 3200);
}
const fmtHHI = v => isNum(v) ? v.toFixed(4) : "—";
const benchLabel = () => DB.meta.bench_label || "Nifty 50 (index-fund holdings)";
function memberName(id) { return id === "ALL" ? "Whole family" : IX.mem[id]?.name || id; }
const inFrame = (() => { try { return window.self !== window.top; } catch (e) { return true; } })();
