import { MONTHS, daysBetween, isoDay, monthLabel } from "./format";
import { getClientData, type ClientData, type Invoice, type ReturnKind } from "./demo";
import { dataVersion } from "./uploads";

/* ---------- tax heads ---------- */
export const HEADS = ["taxable", "igst", "cgst", "sgst", "cess"] as const;
export const TAX_HEADS = ["igst", "cgst", "sgst", "cess"] as const;
export type Head = (typeof HEADS)[number];
export type Tax = Record<Head, number>;
export const HEAD_LABEL: Record<Head, string> = { taxable: "Taxable", igst: "IGST", cgst: "CGST", sgst: "SGST", cess: "Cess" };

export const zero = (): Tax => ({ taxable: 0, igst: 0, cgst: 0, sgst: 0, cess: 0 });
export const totalTax = (t: { igst: number; cgst: number; sgst: number; cess?: number | undefined }) => t.igst + t.cgst + t.sgst + (t.cess ?? 0);
const map = (f: (h: Head) => number): Tax => ({ taxable: f("taxable"), igst: f("igst"), cgst: f("cgst"), sgst: f("sgst"), cess: f("cess") });
export const add = (a: Tax, b: Tax): Tax => map((h) => a[h] + b[h]);
export const sub = (a: Tax, b: Tax): Tax => map((h) => a[h] - b[h]);
export const neg = (a: Tax): Tax => map((h) => -a[h]);
export const taxOnly = (a: Tax): Tax => ({ ...a, taxable: 0 });

export function sumInv(list: { taxable: number; igst: number; cgst: number; sgst: number; cess?: number }[]): Tax {
  const s = zero();
  for (const i of list) {
    s.taxable += i.taxable;
    s.igst += i.igst;
    s.cgst += i.cgst;
    s.sgst += i.sgst;
    s.cess += i.cess ?? 0;
  }
  return s;
}

/** Upper case, drop leading zeros in each number group, strip separators: "SGT/25-26/0093" = "sgt-25-26-93" → "SGT252693". */
export function normaliseInvoiceNo(no: string): string {
  const groups = no.toUpperCase().match(/[A-Z]+|\d+/g) ?? [];
  return groups.map((g) => (/^\d+$/.test(g) ? g.replace(/^0+(?=\d)/, "") : g)).join("");
}

/* ---------- monthly status ---------- */
export type RowStatus = "Matched" | "Difference" | "Partial data";

export function statusOf(diff: Tax, partial: boolean, tolerance = 1): RowStatus {
  if (partial) return "Partial data";
  return Math.abs(totalTax(diff)) > tolerance ? "Difference" : "Matched";
}

export type Source = "books-sales" | "gstr1" | "books-purchases" | "gstr2b" | "gstr3b" | "computed" | "manual";
export const SOURCE_LABEL: Record<Source, string> = {
  "books-sales": "Books (sales register)",
  gstr1: "GSTR-1",
  "books-purchases": "Books (purchase register)",
  gstr2b: "GSTR-2B",
  gstr3b: "GSTR-3B",
  computed: "Calculated",
  manual: "Manual entry",
};

export type RId = "R1" | "R2" | "R3" | "R4" | "R5" | "R6";
export const R_IDS: RId[] = ["R1", "R2", "R3", "R4", "R5", "R6"];

interface RDef {
  title: string;
  sideA: string;
  sideB: string;
  sourceA: Source;
  sourceB: Source;
  kind: "sales" | "itc";
  taxOnly: boolean;
  needs: ReturnKind[];
  pos: string;
  neg: string;
}

export const R_DEFS: Record<RId, RDef> = {
  R1: { title: "Sales: GSTR-1 vs GSTR-3B", sideA: "GSTR-1", sideB: "GSTR-3B 3.1(a)", sourceA: "gstr1", sourceB: "gstr3b", kind: "sales", taxOnly: false, needs: ["gstr1", "gstr3b"],
    pos: "Liability reported in GSTR-1 but not paid in 3B: DRC-01B risk", neg: "More tax paid in 3B than reported in GSTR-1: check invoices missing in GSTR-1" },
  R2: { title: "Sales: GSTR-3B vs Books", sideA: "GSTR-3B 3.1(a)", sideB: "Books", sourceA: "gstr3b", sourceB: "books-sales", kind: "sales", taxOnly: false, needs: ["gstr3b"],
    pos: "3B shows more tax than books: check duplicate or excess reporting", neg: "Books liability not paid in 3B: pay through DRC-03 with interest u/s 50" },
  R3: { title: "Sales: GSTR-1 vs Books", sideA: "GSTR-1", sideB: "Books", sourceA: "gstr1", sourceB: "books-sales", kind: "sales", taxOnly: false, needs: ["gstr1"],
    pos: "GSTR-1 shows more sales than books", neg: "Sales in books not reported in GSTR-1: add in the next GSTR-1" },
  R4: { title: "ITC: GSTR-2B vs Books", sideA: "GSTR-2B", sideB: "Books", sourceA: "gstr2b", sourceB: "books-purchases", kind: "itc", taxOnly: false, needs: ["gstr2b"],
    pos: "ITC in GSTR-2B not booked", neg: "ITC booked but not in GSTR-2B: follow up with supplier (ITC at risk)" },
  R5: { title: "ITC: GSTR-2B vs GSTR-3B 4(C)", sideA: "GSTR-2B", sideB: "GSTR-3B 4(C)", sourceA: "gstr2b", sourceB: "gstr3b", kind: "itc", taxOnly: true, needs: ["gstr2b", "gstr3b"],
    pos: "ITC available in 2B but not claimed in 3B", neg: "ITC claimed beyond GSTR-2B: DRC-01C risk" },
  R6: { title: "ITC: GSTR-3B vs Books", sideA: "GSTR-3B 4(C)", sideB: "Books", sourceA: "gstr3b", sourceB: "books-purchases", kind: "itc", taxOnly: true, needs: ["gstr3b"],
    pos: "ITC claimed in 3B exceeds books: reverse excess", neg: "ITC in books not claimed in 3B" },
};

const RETURN_LABEL: Record<ReturnKind, string> = { gstr1: "GSTR-1", gstr2b: "GSTR-2B", gstr3b: "GSTR-3B" };

export interface CompRow {
  month: string;
  a: Tax;
  b: Tax;
  diff: Tax;
  status: RowStatus;
  meaning: string;
  missing: ReturnKind[];
}

export interface Comparison extends RDef {
  id: RId;
  rows: CompRow[];
  total: { a: Tax; b: Tax; diff: Tax };
}

/* per-month figures for each side */
const byMonth = (list: Invoice[], m: string) => list.filter((i) => i.month === m);
export function itc2b(cd: ClientData) {
  return cd.gstr2b.filter((i) => i.itcAvailable !== false);
}
function sideValue(cd: ClientData, src: Source, kind: "sales" | "itc", m: string): Tax {
  switch (src) {
    case "books-sales": return sumInv(byMonth(cd.sales, m));
    case "gstr1": return cd.missing.gstr1.includes(m) ? zero() : sumInv(byMonth(cd.gstr1, m));
    case "books-purchases": return sumInv(byMonth(cd.purchases, m));
    case "gstr2b": return cd.missing.gstr2b.includes(m) ? zero() : sumInv(byMonth(itc2b(cd), m));
    case "gstr3b": {
      if (cd.missing.gstr3b.includes(m)) return zero();
      const r = cd.gstr3b.find((x) => x.month === m)!;
      return { ...(kind === "sales" ? r.out : r.itc) };
    }
    default: return zero();
  }
}

export function meaningFor(id: RId, diff: Tax, status: RowStatus, missing: ReturnKind[] = [], month = ""): string {
  if (status === "Partial data") return `${missing.map((k) => RETURN_LABEL[k]).join(" and ")} for ${monthLabel(month)} not available: this check is incomplete.`;
  if (status === "Matched") return "Both sides agree (within tolerance).";
  return totalTax(diff) > 0 ? R_DEFS[id].pos : R_DEFS[id].neg;
}

const compCache = new Map<string, Comparison[]>();
export function comparisons(clientId: string, tolerance = 1): Comparison[] {
  const ck = `${clientId}|${tolerance}|${dataVersion()}`;
  const hit = compCache.get(ck);
  if (hit) return hit;
  const cd = getClientData(clientId);
  const res = R_IDS.map((id): Comparison => {
    const def = R_DEFS[id];
    const t = (x: Tax) => (def.taxOnly ? taxOnly(x) : x);
    const rows = MONTHS.map((m): CompRow => {
      const a = t(sideValue(cd, def.sourceA, def.kind, m));
      const b = t(sideValue(cd, def.sourceB, def.kind, m));
      const diff = sub(a, b);
      const missing = def.needs.filter((k) => cd.missing[k].includes(m));
      const status = statusOf(diff, missing.length > 0, tolerance);
      return { month: m, a, b, diff, status, missing, meaning: meaningFor(id, diff, status, missing, m) };
    });
    const total = { a: sumInv(rows.map((r) => r.a)), b: sumInv(rows.map((r) => r.b)), diff: sumInv(rows.map((r) => r.diff)) };
    return { id, ...def, rows, total };
  });
  compCache.set(ck, res);
  return res;
}
export const comparison = (clientId: string, id: RId, tol = 1) => comparisons(clientId, tol).find((c) => c.id === id)!;

/* ---------- three-way view ---------- */
export interface ThreeWayRow {
  month: string;
  books: Tax;
  first: Tax; // GSTR-1 or GSTR-2B
  r3b: Tax;
  d1: number; // first − books
  d2: number; // 3B − first
  d3: number; // 3B − books
  partial: boolean;
  status: RowStatus;
  meaning: string;
}

export function threeWay(clientId: string, kind: "sales" | "itc", tolerance = 1): ThreeWayRow[] {
  const [ra, rb, rc] = (kind === "sales" ? ["R3", "R1", "R2"] : ["R4", "R5", "R6"]) as [RId, RId, RId];
  const A = comparison(clientId, ra, tolerance); // first − books
  const B = comparison(clientId, rb, tolerance); // first − 3B  (shown negated)
  const C = comparison(clientId, rc, tolerance); // 3B − books
  return MONTHS.map((m, i) => {
    const a = A.rows[i]!, b = B.rows[i]!, c = C.rows[i]!;
    const rows = [a, b, c];
    const partial = rows.some((r) => r.status === "Partial data");
    const diff = rows.some((r) => r.status === "Difference");
    const parts: string[] = [];
    const miss = [...new Set(rows.flatMap((r) => r.missing))];
    if (partial) parts.push(`${miss.map((k) => RETURN_LABEL[k]).join(" and ")} for ${monthLabel(m)} not available.`);
    for (const r of [a, b, c]) if (r.status === "Difference") parts.push(r.meaning + ".");
    return {
      month: m,
      books: a.b,
      first: a.a,
      r3b: c.a,
      d1: totalTax(a.diff),
      d2: -totalTax(b.diff),
      d3: totalTax(c.diff),
      partial,
      status: partial ? "Partial data" : diff ? "Difference" : "Matched",
      meaning: parts.length ? parts.join(" ") : "Books and both returns agree.",
    };
  });
}

/* ---------- invoice matching ---------- */
export type MatchKind =
  | "Matched"
  | "Matched – Period Diff"
  | "Value Mismatch"
  | "Probable Match (Inv No)"
  | "Only in Books"
  | "Only in GSTR-1"
  | "Only in GSTR-2B";
export const MATCH_KINDS: Record<"sales" | "itc", MatchKind[]> = {
  sales: ["Matched", "Matched – Period Diff", "Value Mismatch", "Probable Match (Inv No)", "Only in Books", "Only in GSTR-1"],
  itc: ["Matched", "Matched – Period Diff", "Value Mismatch", "Probable Match (Inv No)", "Only in Books", "Only in GSTR-2B"],
};
export interface MatchRow {
  kind: MatchKind;
  books?: Invoice | undefined;
  ret?: Invoice | undefined;
  /** books tax − return tax */
  taxDiff: number;
}

const matchCache = new Map<string, MatchRow[]>();
export function invoiceMatch(clientId: string, side: "sales" | "itc" = "itc", tol = 1): MatchRow[] {
  const ck = `${clientId}|${side}|${tol}|${dataVersion()}`;
  const hit = matchCache.get(ck);
  if (hit) return hit;
  const cd = getClientData(clientId);
  const books =
    side === "sales"
      ? cd.sales.filter((i) => i.gstin && i.type !== "B2CS" && !cd.missing.gstr1.includes(i.month))
      : cd.purchases.filter((i) => !cd.missing.gstr2b.includes(i.month));
  const rets = side === "sales" ? cd.gstr1.filter((i) => i.gstin && i.type !== "B2CS") : itc2b(cd);
  const onlyRet: MatchKind = side === "sales" ? "Only in GSTR-1" : "Only in GSTR-2B";
  const key = (i: Invoice) => `${i.gstin}|${normaliseInvoiceNo(i.no)}`;
  const byKey = new Map<string, Invoice[]>();
  for (const r of rets) byKey.set(key(r), [...(byKey.get(key(r)) ?? []), r]);
  const used = new Set<Invoice>();
  const out: MatchRow[] = [];
  const pending: Invoice[] = [];
  for (const b of books) {
    const r = (byKey.get(key(b)) ?? []).find((x) => !used.has(x));
    if (!r) { pending.push(b); continue; }
    used.add(r);
    const same = Math.abs(b.taxable - r.taxable) <= tol && Math.abs(totalTax(b) - totalTax(r)) <= tol;
    out.push({ kind: !same ? "Value Mismatch" : b.month === r.month ? "Matched" : "Matched – Period Diff", books: b, ret: r, taxDiff: totalTax(b) - totalTax(r) });
  }
  for (const b of pending) {
    const r = rets.find(
      (x) => !used.has(x) && x.gstin === b.gstin && Math.abs(x.taxable - b.taxable) <= tol && Math.abs(totalTax(x) - totalTax(b)) <= tol && Math.abs(daysBetween(b.date, x.date)) <= 3,
    );
    if (r) {
      used.add(r);
      out.push({ kind: "Probable Match (Inv No)", books: b, ret: r, taxDiff: totalTax(b) - totalTax(r) });
    } else out.push({ kind: "Only in Books", books: b, taxDiff: totalTax(b) });
  }
  for (const r of rets) if (!used.has(r)) out.push({ kind: onlyRet, ret: r, taxDiff: -totalTax(r) });
  matchCache.set(ck, out);
  return out;
}

export function countKinds(rows: MatchRow[]): Partial<Record<MatchKind, number>> {
  const c: Partial<Record<MatchKind, number>> = {};
  for (const r of rows) c[r.kind] = (c[r.kind] ?? 0) + 1;
  return c;
}

/* ---------- ITC at risk & supplier follow-up ---------- */
const riskOf = (r: MatchRow) => (r.kind === "Only in Books" ? totalTax(r.books!) : r.kind === "Value Mismatch" ? Math.max(0, r.taxDiff) : 0);

export function itcAtRisk(clientId: string, tol = 1): { amount: number; invoices: (Invoice & { note: string })[]; rows: MatchRow[] } {
  const rows = invoiceMatch(clientId, "itc", tol).filter((r) => r.kind === "Only in Books" || r.kind === "Value Mismatch");
  return { amount: rows.reduce((s, r) => s + riskOf(r), 0), invoices: rows.map((r) => ({ ...r.books!, note: r.kind })), rows };
}

export interface SupplierGroup { gstin: string; party: string; rows: MatchRow[]; atRisk: number }
export function supplierSummary(clientId: string, tol = 1): SupplierGroup[] {
  const groups = new Map<string, SupplierGroup>();
  for (const r of itcAtRisk(clientId, tol).rows) {
    const g = groups.get(r.books!.gstin) ?? { gstin: r.books!.gstin, party: r.books!.party, rows: [], atRisk: 0 };
    g.rows.push(r);
    g.atRisk += riskOf(r);
    groups.set(g.gstin, g);
  }
  return [...groups.values()].sort((a, b) => b.atRisk - a.atRisk);
}

/* ---------- DRC-03 / Table 10-14 ---------- */
export interface Drc03 { tax: Tax; total: number; interest: Tax; interestTotal: number; months: { month: string; tax: Tax; days: number }[] }
export function drc03(clientId: string, today = new Date()): Drc03 {
  const cd = getClientData(clientId);
  const tax = zero();
  const interest = zero();
  const months: Drc03["months"] = [];
  for (const m of MONTHS) {
    const books = sideValue(cd, "books-sales", "sales", m);
    const r3 = sideValue(cd, "gstr3b", "sales", m);
    const t = zero();
    for (const h of TAX_HEADS) t[h] = Math.max(0, books[h] - r3[h]);
    if (totalTax(t) <= 0) continue;
    const [y, mo] = m.split("-").map(Number) as [number, number];
    const due = isoDay(new Date(mo === 12 ? y + 1 : y, mo === 12 ? 0 : mo, 20));
    const days = Math.max(0, daysBetween(due, isoDay(today)));
    for (const h of TAX_HEADS) {
      tax[h] += t[h];
      interest[h] += (t[h] * 0.18 * days) / 365;
    }
    months.push({ month: m, tax: t, days });
  }
  for (const h of TAX_HEADS) interest[h] = Math.round(interest[h]);
  return { tax, total: totalTax(tax), interest, interestTotal: totalTax(interest), months };
}

/* ---------- run summary ---------- */
export interface RunSummary {
  differences: number;
  pending: number;
  itcAtRisk: number;
  /** sum of |monthly tax difference| over months flagged in R2 (GSTR-3B vs books) */
  netTaxDiff: number;
  drc03: number;
  interest: number;
  byR: Record<string, RowStatus>;
  /** year total tax difference (A − B) per check */
  yearDiff: Record<string, number>;
  /** months with a difference, per check */
  diffMonths: Record<string, string[]>;
  partialMonths: string[];
  missing: Record<ReturnKind, string[]>;
  reconciled: boolean;
}

export function summarise(clientId: string, tolerance = 1): RunSummary {
  const byR: Record<string, RowStatus> = {};
  const yearDiff: Record<string, number> = {};
  const diffMonths: Record<string, string[]> = {};
  let differences = 0, pending = 0, netTaxDiff = 0;
  for (const c of comparisons(clientId, tolerance)) {
    const d = c.rows.filter((r) => r.status === "Difference");
    const p = c.rows.filter((r) => r.status === "Partial data").length;
    differences += d.length;
    pending += p;
    if (c.id === "R2") netTaxDiff = d.reduce((s, r) => s + Math.abs(totalTax(r.diff)), 0);
    byR[c.id] = d.length ? "Difference" : p ? "Partial data" : "Matched";
    yearDiff[c.id] = totalTax(c.total.diff);
    diffMonths[c.id] = d.map((r) => r.month);
  }
  const cd = getClientData(clientId);
  const partialMonths = [...new Set([...cd.missing.gstr1, ...cd.missing.gstr2b, ...cd.missing.gstr3b])].sort();
  const drc = drc03(clientId);
  return {
    differences, pending, itcAtRisk: itcAtRisk(clientId, tolerance).amount, netTaxDiff, drc03: drc.total, interest: drc.interestTotal,
    byR, yearDiff, diffMonths, partialMonths, missing: cd.missing, reconciled: differences === 0 && partialMonths.length === 0,
  };
}

/* ---------- GSTR-9 / 9C drafts ---------- */
export interface DraftLine {
  id: string;
  table: string;
  label: string;
  v: Tax;
  heads: Head[];
  source: Source;
  rows?: Invoice[] | undefined;
  note?: string | undefined;
  /** unreconciled line — needs a reason when non-zero */
  diff?: boolean | undefined;
  overridden: Head[];
}
export type Overrides = Record<string, number>; // `${lineId}.${head}` → value

function builder(overrides: Overrides) {
  const lines: DraftLine[] = [];
  const add = (l: Omit<DraftLine, "overridden">): Tax => {
    const v = { ...l.v };
    const overridden: Head[] = [];
    for (const h of l.heads) {
      const o = overrides[`${l.id}.${h}`];
      if (o !== undefined && Number.isFinite(o)) { v[h] = o; overridden.push(h); }
    }
    for (const h of HEADS) if (!l.heads.includes(h)) v[h] = 0;
    lines.push({ ...l, v, overridden });
    return v;
  };
  return { lines, add };
}

const ALL = [...HEADS];
const TAXH = [...TAX_HEADS];
const AMT: Head[] = ["taxable"];
const amt = (n: number): Tax => ({ ...zero(), taxable: n });

export function gstr9(clientId: string, overrides: Overrides = {}, today = new Date()): DraftLine[] {
  const cd = getClientData(clientId);
  const { lines, add: L } = builder(overrides);
  const type = (list: Invoice[], t: string) => list.filter((i) => i.type === t);
  const t4n = (list: Invoice[]) => sub(add(sumInv(type(list, "B2CS")), sumInv(type(list, "B2B"))), neg(sumInv(type(list, "CDNR"))));

  const a4 = L({ id: "4A", table: "Table 4", label: "4A — Supplies to unregistered persons (B2C)", v: sumInv(type(cd.sales, "B2CS")), heads: ALL, source: "books-sales", rows: type(cd.sales, "B2CS") });
  const b4 = L({ id: "4B", table: "Table 4", label: "4B — Supplies to registered persons (B2B)", v: sumInv(type(cd.sales, "B2B")), heads: ALL, source: "books-sales", rows: type(cd.sales, "B2B") });
  const i4 = L({ id: "4I", table: "Table 4", label: "4I — Credit notes issued", v: neg(sumInv(type(cd.sales, "CDNR"))), heads: ALL, source: "books-sales", rows: type(cd.sales, "CDNR") });
  const n4 = L({ id: "4N", table: "Table 4", label: "4N — Supplies on which tax is payable (4A + 4B − 4I)", v: sub(add(a4, b4), i4), heads: ALL, source: "computed", rows: cd.sales });
  const g1 = t4n(cd.gstr1);
  const out3 = sumInv(cd.gstr3b.map((r) => r.out));
  const chk = (x: Tax) => {
    const d = totalTax(x) - totalTax(n4);
    return Math.abs(d) <= 1 && Math.abs(x.taxable - n4.taxable) <= 1 ? "Agrees with 4N (books)." : `Tax differs from 4N (books) by ${d > 0 ? "+" : "−"}₹${Math.abs(Math.round(d)).toLocaleString("en-IN")} — explain or correct.`;
  };
  L({ id: "4N-G1", table: "Table 4", label: "Cross-check: 4N as per GSTR-1", v: g1, heads: ALL, source: "gstr1", rows: cd.gstr1, note: chk(g1) });
  L({ id: "4N-3B", table: "Table 4", label: "Cross-check: 4N as per GSTR-3B (3.1(a))", v: out3, heads: ALL, source: "gstr3b", note: chk(out3) });
  L({ id: "5N", table: "Table 5", label: "5N — Total turnover (4N + exempt, nil-rated, non-GST)", v: n4, heads: ALL, source: "computed" });

  const a6 = L({ id: "6A", table: "Table 6", label: "6A — ITC availed in GSTR-3B (Table 4(C) total)", v: taxOnly(sumInv(cd.gstr3b.map((r) => r.itc))), heads: TAXH, source: "gstr3b" });
  // 6B split in the books' ratio, exactly totalling 6A per head
  const cats = ["Inputs", "Capital goods", "Input services"] as const;
  const bookCat = cats.map((c) => sumInv(cd.purchases.filter((p) => p.itcType === c)));
  const bookAll = sumInv(cd.purchases);
  const split = cats.map(() => zero());
  for (const h of TAX_HEADS) {
    let left = a6[h];
    cats.forEach((_, k) => {
      if (k === cats.length - 1) { split[k]![h] = left; return; }
      const share = bookAll[h] ? Math.round((a6[h] * bookCat[k]![h]) / bookAll[h]) : k === 0 ? a6[h] : 0;
      split[k]![h] = share;
      left -= share;
    });
  }
  const b6 = cats.map((c, k) =>
    L({ id: `6B-${k}`, table: "Table 6", label: `6B — ${c}`, v: split[k]!, heads: TAXH, source: "computed", rows: cd.purchases.filter((p) => p.itcType === c), note: k === 0 ? "Split of 6A in the ratio of the purchase register." : undefined }),
  );
  const b6t = b6.reduce((s, x) => add(s, x), zero());
  L({ id: "6J", table: "Table 6", label: "6J — Difference (6A − 6B)", v: sub(a6, b6t), heads: TAXH, source: "computed", diff: true });
  const j7 = L({ id: "7J", table: "Table 7", label: "7J — Net ITC available for utilisation", v: a6, heads: TAXH, source: "computed" });
  const a8 = L({ id: "8A", table: "Table 8", label: "8A — ITC as per GSTR-2B", v: taxOnly(sumInv(itc2b(cd))), heads: TAXH, source: "gstr2b", rows: itc2b(cd) });
  const b8 = L({ id: "8B", table: "Table 8", label: "8B — ITC availed (= 6B)", v: b6t, heads: TAXH, source: "computed" });
  const c8 = L({ id: "8C", table: "Table 8", label: "8C — ITC of this year availed in next year", v: zero(), heads: TAXH, source: "manual", note: "Enter manually if any." });
  const d8 = sub(a8, add(b8, c8));
  L({ id: "8D", table: "Table 8", label: "8D — Difference 8A − (8B + 8C)", v: d8, heads: TAXH, source: "computed", note: totalTax(d8) > 1 ? "Positive: this ITC lapses (not claimed in time)." : totalTax(d8) < -1 ? "Negative: ITC availed beyond GSTR-2B — review for DRC-01C / reversal." : "No difference." });

  // Table 9 — paid through ITC / cash (estimated per head, per month)
  const paidItc = zero(), paidCash = zero();
  for (const r of cd.gstr3b)
    for (const h of TAX_HEADS) {
      const used = Math.max(0, Math.min(r.out[h], r.itc[h]));
      paidItc[h] += used;
      paidCash[h] += r.out[h] - used;
    }
  L({ id: "9P", table: "Table 9", label: "9 — Tax payable (per GSTR-3B)", v: taxOnly(out3), heads: TAXH, source: "gstr3b" });
  L({ id: "9I", table: "Table 9", label: "9 — Paid through ITC", v: paidItc, heads: TAXH, source: "gstr3b", note: "Verify against electronic credit ledger." });
  L({ id: "9C", table: "Table 9", label: "9 — Paid in cash", v: paidCash, heads: TAXH, source: "gstr3b", note: "Verify against electronic cash ledger." });

  const drc = drc03(clientId, today);
  L({ id: "10/14", table: "Table 10/14", label: "10/14 — Additional liability (month-wise Books − 3B), pay via DRC-03", v: drc.tax, heads: TAXH, source: "computed", diff: true, rows: cd.sales.filter((s) => drc.months.some((m) => m.month === s.month)),
    note: drc.total ? `Months: ${drc.months.map((m) => monthLabel(m.month)).join(", ")}.` : "No additional liability." });
  L({ id: "10/14-INT", table: "Table 10/14", label: "Interest u/s 50 @ 18% p.a. (from 20th of next month to today)", v: drc.interest, heads: TAXH, source: "computed", note: "Indicative — recalculate on the actual payment date." });
  void j7;
  return lines;
}

export interface Gstr9cInputs {
  auditedTurnover?: number | undefined;
  unbilled?: number | undefined;
  otherIncome?: number | undefined;
  itcAudited?: number | undefined;
}

export function gstr9c(clientId: string, inputs: Gstr9cInputs = {}, overrides: Overrides = {}, overrides9: Overrides = {}): DraftLine[] {
  const cd = getClientData(clientId);
  const g9 = gstr9(clientId, overrides9);
  const v9 = (id: string) => g9.find((l) => l.id === id)!.v;
  const n5 = v9("5N"), n4 = v9("4N"), j7 = v9("7J"), p9 = v9("9P");
  const { lines, add: L } = builder(overrides);
  const a5 = L({ id: "5A", table: "Table 5 (9C)", label: "5A — Turnover as per audited financial statements", v: amt(inputs.auditedTurnover ?? n5.taxable), heads: AMT, source: inputs.auditedTurnover === undefined ? "computed" : "manual", note: inputs.auditedTurnover === undefined ? "Defaults to GSTR-9 5N." : undefined });
  const b5 = L({ id: "5B", table: "Table 5 (9C)", label: "5B — Unbilled revenue at the beginning of the year (+)", v: amt(inputs.unbilled ?? 0), heads: AMT, source: "manual" });
  const o5 = L({ id: "5O", table: "Table 5 (9C)", label: "5O — Other income not part of GST turnover (−)", v: amt(inputs.otherIncome ?? 0), heads: AMT, source: "manual" });
  const q5 = L({ id: "5Q", table: "Table 5 (9C)", label: "5Q — Annual turnover after adjustments (5A + 5B − 5O)", v: amt(a5.taxable + b5.taxable - o5.taxable), heads: AMT, source: "computed" });
  const r5 = L({ id: "5R", table: "Table 5 (9C)", label: "5R — Turnover declared in GSTR-9 (5N)", v: amt(n5.taxable), heads: AMT, source: "computed" });
  L({ id: "5S", table: "Table 5 (9C)", label: "5S — Unreconciled turnover (5Q − 5R)", v: amt(q5.taxable - r5.taxable), heads: AMT, source: "computed", diff: true });
  const a7 = L({ id: "7A", table: "Table 7 (9C)", label: "7A — Annual turnover after adjustments (5Q)", v: amt(q5.taxable), heads: AMT, source: "computed" });
  const e7 = L({ id: "7E", table: "Table 7 (9C)", label: "7E — Taxable turnover as per adjustments", v: amt(a7.taxable), heads: AMT, source: "computed" });
  const f7 = L({ id: "7F", table: "Table 7 (9C)", label: "7F — Taxable turnover as per GSTR-9 (4N)", v: amt(n4.taxable), heads: AMT, source: "computed" });
  L({ id: "7G", table: "Table 7 (9C)", label: "7G — Unreconciled taxable turnover (7E − 7F)", v: amt(e7.taxable - f7.taxable), heads: AMT, source: "computed", diff: true });
  const books = taxOnly(sumInv(cd.sales));
  const pb = L({ id: "9-BOOKS", table: "Table 9 (9C)", label: "9 — Tax payable as per books", v: books, heads: TAXH, source: "books-sales", rows: cd.sales });
  const pp = L({ id: "9-PAID", table: "Table 9 (9C)", label: "9 — Tax paid as per GSTR-9", v: p9, heads: TAXH, source: "computed" });
  L({ id: "9R", table: "Table 9 (9C)", label: "9R — Unreconciled tax (books − paid)", v: sub(pb, pp), heads: TAXH, source: "computed", diff: true });
  const a12 = L({ id: "12A", table: "Table 12 (9C)", label: "12A — ITC as per audited financial statements", v: amt(inputs.itcAudited ?? totalTax(j7)), heads: AMT, source: inputs.itcAudited === undefined ? "computed" : "manual", note: inputs.itcAudited === undefined ? "Defaults to GSTR-9 7J." : undefined });
  const e12 = L({ id: "12E", table: "Table 12 (9C)", label: "12E — Net ITC as per audited statements", v: amt(a12.taxable), heads: AMT, source: "computed" });
  const f12 = L({ id: "12F", table: "Table 12 (9C)", label: "12F — ITC claimed in GSTR-9 (7J)", v: amt(totalTax(j7)), heads: AMT, source: "computed" });
  L({ id: "12G", table: "Table 12 (9C)", label: "12G — Unreconciled ITC (12E − 12F)", v: amt(e12.taxable - f12.taxable), heads: AMT, source: "computed", diff: true });
  return lines;
}

export function lineValue(l: DraftLine): number {
  return l.heads.length === 1 && l.heads[0] === "taxable" ? l.v.taxable : totalTax(l.v);
}

export function invoicesFor(clientId: string, source: Source, month?: string): Invoice[] | undefined {
  const cd = getClientData(clientId);
  const list =
    source === "books-sales" ? cd.sales : source === "gstr1" ? cd.gstr1 : source === "books-purchases" ? cd.purchases : source === "gstr2b" ? itc2b(cd) : undefined;
  if (!list) return undefined;
  return month ? list.filter((i) => i.month === month) : list;
}
