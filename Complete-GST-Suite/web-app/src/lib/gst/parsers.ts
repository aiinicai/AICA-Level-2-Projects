/**
 * Parsers: portal JSON (GSTR-1 / GSTR-2B / GSTR-3B), Excel templates (GSTR-3B 12-month summary,
 * manual notices, client master) and Tally exports (registers, Day Book XML, Local Tally Bridge).
 * Pure functions — they take text / rows and return normalised data. File reading lives in excel.ts.
 */
import { DATA_SOURCES, type Client, type DataSource, type Invoice, type ItcType, type Notice, type Return3B, type TaxHeads } from "./demo";
import { MONTHS } from "./format";
import { validateGstin } from "./gstin";

export class ParseError extends Error {}

/* ---------- small helpers ---------- */
export function toNum(v: unknown): number {
  if (v === null || v === undefined || v === "") return 0;
  if (typeof v === "number") return Number.isFinite(v) ? v : 0;
  let s = String(v).replace(/[₹,\s]/g, "");
  if (!s || s === "-") return 0;
  let neg = false;
  if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1); }
  if (/dr$/i.test(s)) s = s.slice(0, -2);
  else if (/cr$/i.test(s)) { s = s.slice(0, -2); neg = !neg; }
  const n = Number(s);
  if (!Number.isFinite(n)) return 0;
  return neg ? -n : n;
}
const r2 = (n: number) => Math.round(n * 100) / 100;
const MN = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

/** Any common date → ISO yyyy-mm-dd ('' when unknown). Excel serials and Date objects work too. */
export function parseDate(v: unknown): string {
  if (v === null || v === undefined || v === "") return "";
  if (v instanceof Date) return isNaN(v.getTime()) ? "" : `${v.getFullYear()}-${String(v.getMonth() + 1).padStart(2, "0")}-${String(v.getDate()).padStart(2, "0")}`;
  if (typeof v === "number") {
    const d = new Date(Date.UTC(1899, 11, 30) + Math.floor(v) * 86400000);
    return d.toISOString().slice(0, 10);
  }
  const s = String(v).trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$/);
  if (m) {
    const y = m[3]!.length === 2 ? `20${m[3]}` : m[3]!;
    return `${y}-${m[2]!.padStart(2, "0")}-${m[1]!.padStart(2, "0")}`;
  }
  m = s.match(/^(\d{1,2})[-\s]([A-Za-z]{3})[a-z]*[-\s](\d{2,4})$/);
  if (m) {
    const mi = MN.indexOf(m[2]!.toUpperCase());
    if (mi >= 0) {
      const y = m[3]!.length === 2 ? `20${m[3]}` : m[3]!;
      return `${y}-${String(mi + 1).padStart(2, "0")}-${m[1]!.padStart(2, "0")}`;
    }
  }
  return "";
}

/** GST return period "MMYYYY" → "YYYY-MM" */
export function retPeriodToMonth(rp: unknown): string {
  const s = String(rp ?? "").trim();
  return /^\d{6}$/.test(s) ? `${s.slice(2)}-${s.slice(0, 2)}` : "";
}
export const monthToRetPeriod = (m: string) => `${m.slice(5, 7)}${m.slice(0, 4)}`;

/** "Apr-25", "Apr 2025", "2025-04", "042025" or a date → "YYYY-MM" */
export function parseMonthCell(v: unknown): string {
  if (v instanceof Date) return parseDate(v).slice(0, 7);
  const s = String(v ?? "").trim();
  const m = s.match(/^([A-Za-z]{3})[a-z]*[-\s']?(\d{2}|\d{4})$/);
  if (m) {
    const mi = MN.indexOf(m[1]!.toUpperCase());
    if (mi >= 0) return `${m[2]!.length === 2 ? "20" + m[2] : m[2]}-${String(mi + 1).padStart(2, "0")}`;
  }
  if (/^\d{4}-\d{2}$/.test(s)) return s;
  if (/^\d{6}$/.test(s)) return retPeriodToMonth(s);
  const d = parseDate(v);
  return d ? d.slice(0, 7) : "";
}

const zeroHeads = (): TaxHeads => ({ taxable: 0, igst: 0, cgst: 0, sgst: 0, cess: 0 });
let seq = 0;
const nid = (p: string) => `${p}-${Date.now().toString(36)}-${(seq++).toString(36)}`;

function inv(p: Partial<Invoice> & { month: string }, credit = false): Invoice {
  const sign = credit ? -1 : 1;
  const v = (x: number | undefined) => r2(sign * Math.abs(x ?? 0));
  return {
    id: p.id ?? nid("u"),
    no: String(p.no ?? "").trim(),
    date: p.date ?? "",
    month: p.month,
    party: (p.party ?? "").trim(),
    gstin: (p.gstin ?? "").trim().toUpperCase(),
    taxable: credit ? v(p.taxable) : r2(p.taxable ?? 0),
    igst: credit ? v(p.igst) : r2(p.igst ?? 0),
    cgst: credit ? v(p.cgst) : r2(p.cgst ?? 0),
    sgst: credit ? v(p.sgst) : r2(p.sgst ?? 0),
    cess: credit ? v(p.cess) : r2(p.cess ?? 0),
    type: p.type,
    itcType: p.itcType,
    itcAvailable: p.itcAvailable,
  };
}

type Obj = Record<string, unknown>;
const arr = (v: unknown): Obj[] => (Array.isArray(v) ? (v as Obj[]) : []);

function itemsSum(items: unknown): TaxHeads {
  const t = zeroHeads();
  for (const it of arr(items)) {
    const d = (it["itm_det"] as Obj | undefined) ?? it;
    t.taxable += toNum(d["txval"]);
    t.igst += toNum(d["iamt"] ?? d["igst"]);
    t.cgst += toNum(d["camt"] ?? d["cgst"]);
    t.sgst += toNum(d["samt"] ?? d["sgst"]);
    t.cess += toNum(d["csamt"] ?? d["cess"]);
  }
  return t;
}

/* ---------- portal JSON ---------- */
export type PortalKind = "GSTR-1" | "GSTR-2B" | "GSTR-3B";

export function detectJsonKind(obj: unknown): PortalKind {
  const o = (obj ?? {}) as Obj;
  const data = o["data"] as Obj | undefined;
  if (data && typeof data === "object" && "docdata" in data) return "GSTR-2B";
  if ("sup_details" in o || "itc_elg" in o) return "GSTR-3B";
  if (("b2b" in o || "b2cs" in o || "cdnr" in o) && "fp" in o) return "GSTR-1";
  throw new ParseError("This JSON is not a GSTR-1, GSTR-2B or GSTR-3B file (expected b2b/b2cs/cdnr with fp, data.docdata, or sup_details/itc_elg).");
}

/** GSTR-1 JSON: b2b + b2cs + cdnr, period "fp". Credit notes become negative. */
export function parseGstr1Json(obj: unknown): { gstin: string; month: string; rows: Invoice[] } {
  const o = obj as Obj;
  const month = retPeriodToMonth(o["fp"]);
  if (!month) throw new ParseError("GSTR-1 JSON has no valid return period ('fp').");
  const rows: Invoice[] = [];
  for (const c of arr(o["b2b"]))
    for (const i of arr(c["inv"])) rows.push(inv({ ...itemsSum(i["itms"]), no: String(i["inum"] ?? ""), date: parseDate(i["idt"]), month, party: String(c["trdnm"] ?? ""), gstin: String(c["ctin"] ?? ""), type: "B2B" }));
  for (const b of arr(o["b2cs"])) rows.push(inv({ ...itemsSum([b]), no: `B2CS-${b["pos"] ?? ""}-${b["rt"] ?? ""}`, date: "", month, party: `B2C small — POS ${b["pos"] ?? ""} @ ${b["rt"] ?? ""}%`, gstin: "", type: "B2CS" }));
  for (const c of arr(o["cdnr"]))
    for (const n of arr(c["nt"])) {
      const credit = String(n["ntty"] ?? n["typ"] ?? "C").toUpperCase() !== "D";
      rows.push(inv({ ...itemsSum(n["itms"]), no: String(n["nt_num"] ?? n["ntnum"] ?? ""), date: parseDate(n["nt_dt"] ?? n["dt"]), month, party: String(c["trdnm"] ?? ""), gstin: String(c["ctin"] ?? ""), type: "CDNR" }, credit));
    }
  return { gstin: String(o["gstin"] ?? "").toUpperCase(), month, rows };
}

/** GSTR-2B JSON: data.docdata, period data.rtnprd. Rows use the 2B period as their month. */
export function parseGstr2bJson(obj: unknown): { gstin: string; month: string; rows: Invoice[] } {
  const o = obj as Obj;
  const data = (o["data"] as Obj | undefined) ?? o;
  const month = retPeriodToMonth(data["rtnprd"]);
  if (!month) throw new ParseError("GSTR-2B JSON has no valid return period ('rtnprd').");
  const dd = (data["docdata"] as Obj | undefined) ?? {};
  const rows: Invoice[] = [];
  const row = (c: Obj, i: Obj, no: unknown, credit: boolean) =>
    inv({ no: String(no ?? ""), date: parseDate(i["dt"]), month, party: String(c["trdnm"] ?? ""), gstin: String(c["ctin"] ?? ""), taxable: toNum(i["txval"]), igst: toNum(i["igst"]), cgst: toNum(i["cgst"]), sgst: toNum(i["sgst"]), cess: toNum(i["cess"]), itcType: "Inputs", itcAvailable: String(i["itcavl"] ?? "Y").toUpperCase() !== "N" }, credit);
  for (const c of arr(dd["b2b"])) for (const i of arr(c["inv"])) rows.push(row(c, i, i["inum"], false));
  for (const c of arr(dd["cdnr"])) for (const n of arr(c["nt"])) rows.push(row(c, n, n["ntnum"], String(n["typ"] ?? "C").toUpperCase() !== "D"));
  return { gstin: String(data["gstin"] ?? "").toUpperCase(), month, rows };
}

/** GSTR-3B JSON: Table 3.1(a) from sup_details.osup_det and Table 4(C) from itc_elg.itc_net, period ret_period. */
export function parseGstr3bJson(obj: unknown): { gstin: string; month: string; summary: Return3B } {
  const o = obj as Obj;
  const month = retPeriodToMonth(o["ret_period"]);
  if (!month) throw new ParseError("GSTR-3B JSON has no valid return period ('ret_period').");
  const sd = ((o["sup_details"] as Obj | undefined)?.["osup_det"] as Obj | undefined) ?? {};
  const net = ((o["itc_elg"] as Obj | undefined)?.["itc_net"] as Obj | undefined) ?? {};
  return {
    gstin: String(o["gstin"] ?? "").toUpperCase(),
    month,
    summary: {
      month,
      out: { taxable: r2(toNum(sd["txval"])), igst: r2(toNum(sd["iamt"])), cgst: r2(toNum(sd["camt"])), sgst: r2(toNum(sd["samt"])), cess: r2(toNum(sd["csamt"])) },
      itc: { taxable: 0, igst: r2(toNum(net["iamt"])), cgst: r2(toNum(net["camt"])), sgst: r2(toNum(net["samt"])), cess: r2(toNum(net["csamt"])) },
    },
  };
}

/* ---------- Excel templates (rows = array of row arrays) ---------- */
export type Rows = unknown[][];
const cellStr = (v: unknown) => (v === null || v === undefined ? "" : String(v)).trim();
function headerIndex(hdr: unknown[], ...names: string[]): number {
  const h = hdr.map((x) => cellStr(x).toLowerCase());
  for (const n of names) { const i = h.indexOf(n.toLowerCase()); if (i >= 0) return i; }
  for (const n of names) { const i = h.findIndex((x) => x.includes(n.toLowerCase())); if (i >= 0) return i; }
  return -1;
}

export const GSTR3B_TEMPLATE_HEADERS = ["Month", "3.1(a) Taxable", "3.1(a) IGST", "3.1(a) CGST", "3.1(a) SGST", "3.1(a) Cess", "4(C) IGST", "4(C) CGST", "4(C) SGST", "4(C) Cess"];

/** GSTR-3B 12-month summary template: Table 3.1(a) and Table 4(C) per month. */
export function parse3bSummaryRows(rows: Rows): { gstin: string; byMonth: Record<string, Return3B> } {
  let gstin = "";
  let hi = -1;
  for (let i = 0; i < Math.min(rows.length, 12); i++) {
    const r = rows[i] ?? [];
    for (const c of r) { const s = cellStr(c).toUpperCase(); if (validateGstin(s).valid) gstin = s; }
    if (r.some((c) => cellStr(c).toLowerCase() === "month")) { hi = i; break; }
  }
  if (hi < 0) throw new ParseError("GSTR-3B summary: the 'Month' header row was not found.");
  const h = rows[hi]!;
  const ix = {
    month: headerIndex(h, "month"), taxable: headerIndex(h, "3.1(a) taxable"), igst: headerIndex(h, "3.1(a) igst"), cgst: headerIndex(h, "3.1(a) cgst"), sgst: headerIndex(h, "3.1(a) sgst"), cess: headerIndex(h, "3.1(a) cess"),
    iigst: headerIndex(h, "4(c) igst"), icgst: headerIndex(h, "4(c) cgst"), isgst: headerIndex(h, "4(c) sgst"), icess: headerIndex(h, "4(c) cess"),
  };
  if (ix.taxable < 0) throw new ParseError("GSTR-3B summary: the '3.1(a) Taxable' column was not found.");
  const g = (r: unknown[], i: number) => (i >= 0 ? r2(toNum(r[i])) : 0);
  const byMonth: Record<string, Return3B> = {};
  for (const r of rows.slice(hi + 1)) {
    if (!r || ix.month >= r.length) continue;
    const m = parseMonthCell(r[ix.month]);
    if (!m) continue;
    const vals = [ix.taxable, ix.igst, ix.cgst, ix.sgst, ix.cess, ix.iigst, ix.icgst, ix.isgst, ix.icess].map((i) => g(r, i));
    if (vals.every((v) => v === 0) && !cellStr(r[ix.taxable])) continue;
    byMonth[m] = { month: m, out: { taxable: g(r, ix.taxable), igst: g(r, ix.igst), cgst: g(r, ix.cgst), sgst: g(r, ix.sgst), cess: g(r, ix.cess) }, itc: { taxable: 0, igst: g(r, ix.iigst), cgst: g(r, ix.icgst), sgst: g(r, ix.isgst), cess: g(r, ix.icess) } };
  }
  if (!Object.keys(byMonth).length) throw new ParseError("GSTR-3B summary: no month rows with figures were found.");
  return { gstin, byMonth };
}

export const NOTICE_TEMPLATE_HEADERS = ["GSTIN", "Form", "Reference No", "Tax Period", "Issue Date", "Reply Due Date", "Nature", "Priority", "Assigned To", "Amount", "Notes"];

/** Manual notices template → partial notices (library defaults are filled later). */
export function parseNoticeRows(rows: Rows): Partial<Notice>[] {
  const hi = rows.findIndex((r, i) => i < 12 && (r ?? []).some((c) => cellStr(c).toLowerCase() === "form"));
  if (hi < 0) throw new ParseError("Notices template: the 'Form' header row was not found.");
  const h = rows[hi]!;
  const ix = Object.fromEntries(NOTICE_TEMPLATE_HEADERS.map((k) => [k, headerIndex(h, k)])) as Record<string, number>;
  if (ix["Reference No"]! < 0) throw new ParseError("Notices template: the 'Reference No' column was not found.");
  const out: Partial<Notice>[] = [];
  for (const r of rows.slice(hi + 1)) {
    const g = (k: string) => (ix[k]! >= 0 ? r?.[ix[k]!] : "");
    if (!cellStr(g("Form"))) continue;
    const pr = cellStr(g("Priority"));
    out.push({
      gstin: cellStr(g("GSTIN")).toUpperCase(), form: cellStr(g("Form")).toUpperCase(), ref: cellStr(g("Reference No")), taxPeriod: cellStr(g("Tax Period")),
      issued: parseDate(g("Issue Date")), due: parseDate(g("Reply Due Date")), subject: cellStr(g("Nature")), assignedTo: cellStr(g("Assigned To")),
      amount: toNum(g("Amount")), notes: cellStr(g("Notes")), source: "Template upload",
      ...(["Critical", "High", "Medium", "Low"].includes(pr) ? { priority: pr as Notice["priority"] } : {}),
    });
  }
  return out;
}

/* ---------- Tally ---------- */
export const REGISTER_FIELDS = ["party", "gstin", "inv_no", "sup_inv_no", "date", "taxable", "igst", "cgst", "sgst", "cess", "voucher_type", "category"] as const;
export type RegisterField = (typeof REGISTER_FIELDS)[number];
export const REGISTER_FIELD_LABELS: Record<RegisterField, string> = {
  party: "Party name", gstin: "Party GSTIN", inv_no: "Invoice / voucher no", sup_inv_no: "Supplier invoice no", date: "Date", taxable: "Taxable value",
  igst: "IGST", cgst: "CGST", sgst: "SGST / UTGST", cess: "Cess", voucher_type: "Voucher type", category: "Purchase ledger / category",
};
export const REQUIRED_FIELDS: RegisterField[] = ["date", "taxable", "inv_no"];
const GUESS: Record<RegisterField, string[]> = {
  party: ["particulars", "party name", "party", "customer", "supplier", "name"],
  gstin: ["gstin/uin", "gstin", "gst no", "gstin of party"],
  inv_no: ["voucher no.", "voucher no", "vch no", "invoice no", "inv no", "bill no"],
  sup_inv_no: ["supplier invoice no.", "supplier invoice no", "supplier inv no", "reference", "ref no"],
  date: ["date", "invoice date", "voucher date"],
  taxable: ["taxable value", "taxable", "assessable value", "value"],
  igst: ["igst", "integrated tax"], cgst: ["cgst", "central tax"], sgst: ["sgst", "utgst", "state tax", "sgst/utgst"], cess: ["cess"],
  voucher_type: ["voucher type", "vch type", "type"], category: ["purchase ledger", "category", "itc type", "ledger"],
};

/** Best guess of column → field from header names. */
export function guessMapping(headers: string[]): Partial<Record<RegisterField, string>> {
  const hl = headers.map((h) => h.trim().toLowerCase());
  const used = new Set<number>();
  const out: Partial<Record<RegisterField, string>> = {};
  for (const f of REGISTER_FIELDS) {
    for (const n of GUESS[f]) {
      let i = hl.findIndex((h, k) => h === n && !used.has(k));
      if (i < 0) i = hl.findIndex((h, k) => h.includes(n) && !used.has(k) && !(f === "inv_no" && h.includes("supplier")));
      if (i >= 0) { out[f] = headers[i]!; used.add(i); break; }
    }
  }
  return out;
}

export function classifyTaxLedger(name: string): "igst" | "cgst" | "sgst" | "cess" | null {
  const n = name.toUpperCase();
  if (n.includes("CESS")) return "cess";
  if (n.includes("IGST") || n.includes("INTEGRATED")) return "igst";
  if (n.includes("CGST") || n.includes("CENTRAL TAX")) return "cgst";
  if (n.includes("SGST") || n.includes("UTGST") || n.includes("STATE TAX")) return "sgst";
  return null;
}

/** Inputs / Capital goods / Input services from ledger names (manual override available on screen). */
export function classifyPurchase(names: string[]): ItcType {
  const t = names.join(" ").toUpperCase();
  if (/CAPITAL|MACHINERY|PLANT|FIXED ASSET|COMPUTER|VEHICLE|FURNITURE|EQUIPMENT/.test(t)) return "Capital goods";
  if (/SERVICE|FREIGHT|RENT|PROFESSIONAL|CONSULT|REPAIR|TRANSPORT|ADVERTIS|TELEPHONE|CONTRACT|COMMISSION|LEGAL|AUDIT FEE|SECURITY/.test(t)) return "Input services";
  return "Inputs";
}

/** Sales / purchase register records → invoices, using a column mapping. */
export function registerToInvoices(records: Record<string, unknown>[], mapping: Partial<Record<RegisterField, string>>, kind: "sales" | "purchase"): Invoice[] {
  const get = (r: Record<string, unknown>, f: RegisterField) => (mapping[f] ? r[mapping[f]!] : "");
  const out: Invoice[] = [];
  for (const r of records) {
    const tx = toNum(get(r, "taxable"));
    const taxes = { igst: toNum(get(r, "igst")), cgst: toNum(get(r, "cgst")), sgst: toNum(get(r, "sgst")), cess: toNum(get(r, "cess")) };
    if (Math.abs(tx) < 0.005 && Object.values(taxes).every((v) => Math.abs(v) < 0.005)) continue;
    const party = cellStr(get(r, "party"));
    if (/^(grand )?total$/i.test(party)) continue;
    const date = parseDate(get(r, "date"));
    if (!date) continue;
    const vt = cellStr(get(r, "voucher_type")).toUpperCase();
    const gstin = cellStr(get(r, "gstin")).toUpperCase();
    const no = cellStr(get(r, "inv_no"));
    if (kind === "sales") {
      const credit = vt.includes("CREDIT") || vt.includes("RETURN");
      out.push(inv({ no, date, month: date.slice(0, 7), party, gstin, taxable: tx, ...taxes, type: credit ? "CDNR" : gstin ? "B2B" : "B2CS" }, credit));
    } else {
      const credit = vt.includes("DEBIT") || vt.includes("RETURN");
      const cat = cellStr(get(r, "category"));
      const itcType: ItcType = (["Inputs", "Capital goods", "Input services"] as ItcType[]).find((x) => x.toLowerCase() === cat.toLowerCase()) ?? classifyPurchase([cat, party, vt]);
      out.push(inv({ no: cellStr(get(r, "sup_inv_no")) || no, date, month: date.slice(0, 7), party, gstin, taxable: tx, ...taxes, itcType, itcAvailable: true }, credit));
    }
  }
  return out;
}

export interface Voucher {
  date: string;
  voucher_type: string;
  voucher_no: string;
  party: string;
  gstin: string;
  reference: string;
  ledgers: { name: string; amount: number | string }[];
}

/** Tally Day Book XML export → vouchers. */
export function parseDaybookXml(text: string): Voucher[] {
  const out: Voucher[] = [];
  const tag = (block: string, t: string) => (block.match(new RegExp(`<${t}[^>]*>([\\s\\S]*?)</${t}>`, "i"))?.[1] ?? "").replace(/&amp;/g, "&").trim();
  for (const m of text.matchAll(/<VOUCHER\b([^>]*)>([\s\S]*?)<\/VOUCHER>/gi)) {
    const attrs = m[1] ?? "";
    const body = m[2] ?? "";
    const ledgers = [...body.matchAll(/<(ALLLEDGERENTRIES|LEDGERENTRIES)\.LIST[^>]*>([\s\S]*?)<\/\1\.LIST>/gi)].map((l) => ({ name: tag(l[2]!, "LEDGERNAME"), amount: tag(l[2]!, "AMOUNT") }));
    out.push({
      date: tag(body, "DATE"), voucher_type: tag(body, "VOUCHERTYPENAME") || (attrs.match(/VCHTYPE="([^"]*)"/i)?.[1] ?? ""),
      voucher_no: tag(body, "VOUCHERNUMBER"), party: tag(body, "PARTYLEDGERNAME"), gstin: tag(body, "PARTYGSTIN"), reference: tag(body, "REFERENCE"), ledgers,
    });
  }
  if (!out.length) throw new ParseError("No <VOUCHER> entries were found in the XML. Export the Day Book from Tally as XML.");
  return out;
}

/** Vouchers (Day Book XML or Local Tally Bridge JSON) → sales and purchase invoices. */
export function vouchersToInvoices(vouchers: Voucher[]): { sales: Invoice[]; purchases: Invoice[] } {
  const sales: Invoice[] = [];
  const purchases: Invoice[] = [];
  for (const v of vouchers) {
    const vt = v.voucher_type.toUpperCase();
    const isSale = vt.includes("SALE") || vt.startsWith("CREDIT NOTE");
    const isPurch = vt.includes("PURCHASE") || vt.startsWith("DEBIT NOTE");
    if (!isSale && !isPurch) continue;
    const t = zeroHeads();
    const others: string[] = [];
    for (const l of v.ledgers) {
      if (l.name === v.party) continue;
      const amt = Math.abs(toNum(l.amount));
      const h = classifyTaxLedger(l.name);
      if (h) t[h] += amt;
      else { t.taxable += amt; others.push(l.name); }
    }
    const date = parseDate(v.date);
    if (!date) continue;
    const base = { date, month: date.slice(0, 7), party: v.party, gstin: v.gstin, ...t };
    if (isSale) {
      const credit = vt.includes("CREDIT");
      sales.push(inv({ ...base, no: v.voucher_no, type: credit ? "CDNR" : v.gstin ? "B2B" : "B2CS" }, credit));
    } else {
      const credit = vt.includes("DEBIT");
      purchases.push(inv({ ...base, no: v.reference || v.voucher_no, itcType: classifyPurchase(others), itcAvailable: true }, credit));
    }
  }
  return { sales, purchases };
}

/** First row with at least three text cells is the header; returns header + records. */
export function rowsToRecords(rows: Rows): { headers: string[]; records: Record<string, unknown>[] } {
  let hi = rows.findIndex((r, i) => i < 15 && (r ?? []).filter((c) => typeof c === "string" && c.trim()).length >= 3);
  if (hi < 0) hi = 0;
  const headers = (rows[hi] ?? []).map((c, j) => cellStr(c) || `Column ${j + 1}`);
  const records = rows.slice(hi + 1).filter((r) => r && r.some((c) => c !== null && c !== undefined && c !== "")).map((r) => Object.fromEntries(headers.map((h, j) => [h, r[j] ?? ""])));
  return { headers, records };
}

/** Minimal CSV reader (quoted fields, commas, CRLF). */
export function parseCsv(text: string): Rows {
  const rows: string[][] = [];
  let row: string[] = [];
  let cur = "";
  let q = false;
  const t = text.replace(/^﻿/, "");
  for (let i = 0; i < t.length; i++) {
    const ch = t[i]!;
    if (q) {
      if (ch === '"' && t[i + 1] === '"') { cur += '"'; i++; }
      else if (ch === '"') q = false;
      else cur += ch;
    } else if (ch === '"') q = true;
    else if (ch === ",") { row.push(cur); cur = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && t[i + 1] === "\n") i++;
      row.push(cur); rows.push(row); row = []; cur = "";
    } else cur += ch;
  }
  if (cur || row.length) { row.push(cur); rows.push(row); }
  return rows;
}

/* ---------- portal file auto-detection ---------- */
export type DetectedFile =
  | { type: "GSTR-1" | "GSTR-2B"; gstin: string; month: string; rows: Invoice[] }
  | { type: "GSTR-3B" | "GSTR-3B summary"; gstin: string; byMonth: Record<string, Return3B> }
  | { type: "Notices"; gstin: string; notices: Partial<Notice>[] };

/**
 * Detect a portal / template file from its CONTENT (any file name works).
 * JSON is passed as text; Excel/CSV as rows. A file of another GSTIN is rejected.
 */
export function detectPortalFile(input: { json?: string | undefined; rows?: Rows | undefined }, clientGstin: string): DetectedFile {
  const cg = clientGstin.toUpperCase();
  let res: DetectedFile;
  if (input.json !== undefined) {
    let obj: unknown;
    try { obj = JSON.parse(input.json); } catch { throw new ParseError("This is not a valid JSON file."); }
    const kind = detectJsonKind(obj);
    if (kind === "GSTR-1") { const p = parseGstr1Json(obj); res = { type: "GSTR-1", gstin: p.gstin, month: p.month, rows: p.rows }; }
    else if (kind === "GSTR-2B") { const p = parseGstr2bJson(obj); res = { type: "GSTR-2B", gstin: p.gstin, month: p.month, rows: p.rows }; }
    else { const p = parseGstr3bJson(obj); res = { type: "GSTR-3B", gstin: p.gstin, byMonth: { [p.month]: p.summary } }; }
  } else if (input.rows) {
    const flat = input.rows.slice(0, 10).flat().map((c) => cellStr(c).toLowerCase()).join(" | ");
    if (flat.includes("3.1(a)") && flat.includes("month")) { const p = parse3bSummaryRows(input.rows); res = { type: "GSTR-3B summary", gstin: p.gstin, byMonth: p.byMonth }; }
    else if (flat.includes("reference no") && flat.includes("form")) { const n = parseNoticeRows(input.rows); res = { type: "Notices", gstin: n[0]?.gstin ?? "", notices: n }; }
    else throw new ParseError("This sheet is not the GSTR-3B summary or the notices template. Tally registers go in the Books card.");
  } else throw new ParseError("Unsupported file. Use GSTR-1 / 2B / 3B JSON, or the Excel templates.");
  if (res.gstin && cg && res.gstin !== cg) throw new ParseError(`This file belongs to GSTIN ${res.gstin}, but this client is ${cg}. Upload it under the correct client.`);
  if (res.type === "Notices") for (const n of res.notices) if (n.gstin && cg && n.gstin !== cg) throw new ParseError(`Notice ${n.ref} is for GSTIN ${n.gstin}, not ${cg}.`);
  return res;
}

/* ---------- client master import ---------- */
export const CLIENT_TEMPLATE_HEADERS = [
  "Client Name*", "Trade Name", "GSTIN*", "GST Portal Username*", "Registered Mobile (last 4)", "Registered Email",
  "Return Frequency (Monthly / QRMP)", "Financial Year", "Tally Company Name", "API Access Enabled (Yes/No)", "API Access Valid Till",
  "Assigned Staff", "Fetch Returns", "Fetch Notices", "Active", "Data Source (Auto / GSP API / Downloaded files)", "Remarks",
];
const CLIENT_KEYS = ["name", "tradeName", "gstin", "portalUsername", "mobile4", "email", "frequency", "fy", "tallyCompany", "apiEnabled", "apiValidTill", "staff", "fetchReturns", "fetchNotices", "active", "dataSource", "remarks"] as const;
export type ClientInput = Pick<Client, (typeof CLIENT_KEYS)[number]>;

export function validateClient(c: ClientInput, existingGstins: Iterable<string> = []): string[] {
  const errs: string[] = [];
  const existing = new Set([...existingGstins].map((g) => g.toUpperCase()));
  if (!c.name.trim()) errs.push("Client Name is required");
  const g = validateGstin(c.gstin);
  if (!c.gstin.trim()) errs.push("GSTIN is required");
  else if (!g.valid) errs.push(g.reason ?? "GSTIN is not valid");
  else if (existing.has(c.gstin.toUpperCase())) errs.push("Duplicate GSTIN — this client already exists");
  if (!c.portalUsername.trim()) errs.push("GST Portal Username is required");
  if (c.mobile4 && !/^\d{4}$/.test(c.mobile4)) errs.push("Registered Mobile must be exactly the last 4 digits");
  if (c.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(c.email)) errs.push("Registered Email is not valid");
  if (!["Monthly", "QRMP"].includes(c.frequency)) errs.push("Return Frequency must be Monthly or QRMP");
  if (!DATA_SOURCES.includes(c.dataSource)) errs.push("Data Source must be Auto, GSP API or Downloaded files");
  if (c.fy && !/^\d{4}-\d{2}$/.test(c.fy)) errs.push("Financial Year must look like 2025-26");
  return errs;
}

const yes = (v: unknown, dflt: boolean) => { const s = cellStr(v).toLowerCase(); return s === "" ? dflt : ["yes", "y", "true", "1"].includes(s); };

/** Client master template → records with row-level errors. There is no password column. */
export function parseClientRows(rows: Rows, existingGstins: Iterable<string> = []): { row: number; client: ClientInput; errors: string[] }[] {
  const hi = rows.findIndex((r, i) => i < 10 && (r ?? []).some((c) => cellStr(c).toLowerCase().includes("gstin")));
  if (hi < 0) throw new ParseError("Client master: the header row (with GSTIN) was not found. Use the downloadable template.");
  const h = (rows[hi] ?? []).map((c) => cellStr(c).toLowerCase().replace(/\*/g, ""));
  const idx = CLIENT_KEYS.map((_, k) => {
    const t = CLIENT_TEMPLATE_HEADERS[k]!.toLowerCase().replace(/\*/g, "");
    let i = h.indexOf(t);
    if (i < 0) i = h.findIndex((x) => x.startsWith(t.split(" (")[0]!));
    return i;
  });
  const seen = new Set([...existingGstins].map((g) => g.toUpperCase()));
  const out: { row: number; client: ClientInput; errors: string[] }[] = [];
  rows.slice(hi + 1).forEach((r, k) => {
    if (!r || !r.some((c) => cellStr(c))) return;
    const v = (key: (typeof CLIENT_KEYS)[number]) => { const i = idx[CLIENT_KEYS.indexOf(key)]!; return i >= 0 ? r[i] : ""; };
    const freq = cellStr(v("frequency")).toLowerCase();
    const ds = cellStr(v("dataSource"));
    const client: ClientInput = {
      name: cellStr(v("name")), tradeName: cellStr(v("tradeName")), gstin: cellStr(v("gstin")).toUpperCase(), portalUsername: cellStr(v("portalUsername")),
      mobile4: cellStr(v("mobile4")).replace(/\.0$/, ""), email: cellStr(v("email")), frequency: freq.startsWith("q") ? "QRMP" : "Monthly", fy: cellStr(v("fy")) || "2025-26",
      tallyCompany: cellStr(v("tallyCompany")), apiEnabled: yes(v("apiEnabled"), false), apiValidTill: parseDate(v("apiValidTill")), staff: cellStr(v("staff")),
      fetchReturns: yes(v("fetchReturns"), true), fetchNotices: yes(v("fetchNotices"), true), active: yes(v("active"), true),
      dataSource: (DATA_SOURCES.find((d) => d.toLowerCase() === (ds || "auto").toLowerCase()) ?? (ds as DataSource)), remarks: cellStr(v("remarks")),
    };
    if (freq && !freq.startsWith("q") && !freq.startsWith("m")) client.frequency = cellStr(v("frequency")) as "Monthly";
    const errors = validateClient(client, seen);
    if (!errors.length) seen.add(client.gstin);
    out.push({ row: hi + k + 2, client, errors });
  });
  return out;
}

export const monthsInFy = MONTHS;
