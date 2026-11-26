// Clause 44 ledger method – what is kept between visits and the report built from it.
// No new tables:
//  • expense_rows: one row per ledger × party (include = ledger chosen; category_override = column worked out here)
//  • engagements.clause_answers.c44_books: what this year's Tally import said about ledgers and parties
//  • column_mappings "c44_ledger_method" (per client, carried to later years): ledger choices, taxability
//    changes, the auditor's checked GST status of parties, bank-charges setting
import type { Category } from "../clause44";
import { isValidGstin } from "../validators";
import {
  type Books, buildBreakup, candidateLedgers,
  type BookParty, type GstStatus, type LedgerKind, type PartyFacts, type RegType, type Taxability,
  categoryOf, reviewReasons, statusOf,
} from "./books";

export const SETTINGS_NAME = "c44_ledger_method";

export interface StoredLedger { k: LedgerKind; g: string; p: string; t: Taxability; x: string | null; total: number; out?: number }
export interface StoredParty { n: string; gstin: string; reg: RegType; via: BookParty["via"]; gb: number; b: number; tr?: boolean }
export interface C44Books {
  upload_id: string; file: string; at: string;
  ledgers: Record<string, StoredLedger>;   // every P&L expense ledger and Fixed Asset ledger of the books
  parties: Record<string, StoredParty>;    // key = normalized party name
  b2b?: { gstins: string[]; files: string[] } | null;
  /** What the app itself last saved on each row ("category|1" / "category|0"); a row that differs was changed by hand. */
  synced?: Record<string, string>;
}
export interface C44Settings {
  sel: Record<string, boolean>;            // ledger (lower case) → chosen
  tax: Record<string, "taxable" | "exempt">; // ledger (lower case) → the auditor's taxability
  checked: Record<string, GstStatus>;      // party key → status checked on the GST portal
  bankRegular: boolean;
}
export const DEFAULT_SETTINGS: C44Settings = { sel: {}, tax: {}, checked: {}, bankRegular: true };
export const readSettings = (m: any): C44Settings => ({ ...DEFAULT_SETTINGS, ...(m ?? {}), sel: { ...(m?.sel ?? {}) }, tax: { ...(m?.tax ?? {}) }, checked: { ...(m?.checked ?? {}) } });

export const ledgerChosen = (name: string, l: StoredLedger | { x: string | null }, s: C44Settings) => s.sel[name.toLowerCase()] ?? !l.x;
export const ledgerTax = (name: string, l: { t: Taxability }, s: C44Settings): Taxability => s.tax[name.toLowerCase()] ?? l.t;

export interface PartyMasterLite { normalized_name: string; party_name: string; gstin: string | null; is_composition: boolean; is_exempt: boolean }
export interface RowLite { id: string; party_name: string; normalized_name: string; gstin: string | null; expense_head: string | null; amount: number; include: boolean; category: string; category_override: string | null; upload_id: string | null; nature: string | null }

export function factsOf(key: string, books: C44Books, pm: PartyMasterLite | undefined, s: C44Settings): PartyFacts {
  const bp = books.parties[key];
  const gstin = (pm?.gstin && pm.gstin.trim()) || bp?.gstin || null;
  return {
    name: pm?.party_name || bp?.n || key, gstin, tallyReg: bp?.reg ?? "", via: bp?.via ?? "party", trade: bp?.tr,
    gstBills: bp?.gb ?? 0, bills: bp?.b ?? 0, isComposition: !!pm?.is_composition, isExempt: !!pm?.is_exempt, checked: s.checked[key] ?? null,
  };
}

/** Column of a stored row (only rows of the Tally ledger import). */
export function rowCategory(r: RowLite, books: C44Books, pm: PartyMasterLite | undefined, s: C44Settings): Category {
  const l = books.ledgers[r.expense_head ?? ""];
  return categoryOf(factsOf(r.normalized_name, books, pm, s), r.expense_head ?? "", l ? ledgerTax(r.expense_head ?? "", l, s) : "", { bankChargesRegular: s.bankRegular });
}

export const rowState = (category: string, include: boolean) => `${category}|${include ? 1 : 0}`;

/** Rows whose include / category no longer match the choices – to be saved. Rows changed by hand in Review are kept. */
export function rowsToSync(rows: RowLite[], books: C44Books, pms: Record<string, PartyMasterLite>, s: C44Settings) {
  const out: { id: string; include: boolean; category: Category }[] = [];
  for (const r of rows) {
    if (r.upload_id !== books.upload_id) continue;
    const now = rowState(r.category_override ?? r.category, r.include);
    const last = books.synced?.[r.id];
    if (last !== undefined && last !== now) continue;          // changed by hand – the auditor's choice stands
    const l = books.ledgers[r.expense_head ?? ""];
    const include = l ? ledgerChosen(r.expense_head ?? "", l, s) : r.include;
    const category = rowCategory(r, books, pms[r.normalized_name], s);
    if (rowState(category, include) !== now) out.push({ id: r.id, include, category });
  }
  return out;
}

export type Cols = Record<Category, number> & { total: number };
const zero = (): Cols => ({ total: 0, exempt: 0, composition: 0, other_registered: 0, unregistered: 0 });
const addTo = (c: Cols, cat: Category, a: number) => { c.total += a; c[cat] += a; };
const r2 = (n: number) => Math.round(n * 100) / 100;

export interface LedgerLine { name: string; kind: LedgerKind | "other"; group: string; tax: Taxability; cols: Cols; parties: { key: string; name: string; gstin: string; status: GstStatus | ""; category: Category; amount: number }[] }
export interface ReviewParty { key: string; name: string; gstin: string; status: GstStatus; reasons: string[]; amount: number; checked: GstStatus | null }
export interface LedgerReport {
  revenue: LedgerLine[]; capital: LedgerLine[]; other: LedgerLine[];
  totals: { revenue: Cols; capital: Cols; other: Cols; all: Cols };
  review: ReviewParty[]; checked: ReviewParty[];
  excluded: { name: string; reason: string; amount: number }[];
  recon: { booksRevenue: number; excludedRevenue: number; capitalAdditions: number; otherRows: number; reported: number };
}

/** Ledger-wise break-up, parties to check and the reconciliation. rows = all expense rows of the year. */
export function buildLedgerReport(rows: RowLite[], books: C44Books, pms: Record<string, PartyMasterLite>, s: C44Settings): LedgerReport {
  const lines = new Map<string, LedgerLine>();
  const partyAmt = new Map<string, number>();
  const in2b = books.b2b?.gstins?.length ? new Set(books.b2b.gstins) : null;
  for (const r of rows) {
    if (!r.include) continue;
    const fromBooks = r.upload_id === books.upload_id;
    const head = r.expense_head || "(no expense head)";
    const l = fromBooks ? books.ledgers[head] : undefined;
    // the saved rows are the truth (the Form 3CD table and the exports read the same rows)
    const cat = (r.category_override ?? r.category) as Category;
    const key = `${fromBooks ? "b" : "o"}|${head}`;
    let line = lines.get(key);
    if (!line) { line = { name: head, kind: l ? l.k : "other", group: l?.p ?? "", tax: l ? ledgerTax(head, l, s) : "", cols: zero(), parties: [] }; lines.set(key, line); }
    const amt = Number(r.amount);
    addTo(line.cols, cat, amt);
    const f = fromBooks ? factsOf(r.normalized_name, books, pms[r.normalized_name], s) : null;
    const ex = line.parties.find((p) => p.key === r.normalized_name && p.category === cat);
    if (ex) ex.amount += amt;
    else line.parties.push({ key: r.normalized_name, name: pms[r.normalized_name]?.party_name || r.party_name, gstin: (f?.gstin ?? r.gstin) || "", status: f ? statusOf(f) : "", category: cat, amount: amt });
    if (fromBooks) partyAmt.set(r.normalized_name, (partyAmt.get(r.normalized_name) ?? 0) + amt);
  }
  const all = Array.from(lines.values());
  all.forEach((l) => { (Object.keys(l.cols) as (keyof Cols)[]).forEach((k) => { l.cols[k] = r2(l.cols[k]); }); l.parties.forEach((p) => { p.amount = r2(p.amount); }); l.parties.sort((a, b) => b.amount - a.amount); });
  const sortL = (a: LedgerLine, b: LedgerLine) => a.group.localeCompare(b.group) || b.cols.total - a.cols.total;
  const pick = (k: LedgerLine["kind"]) => all.filter((l) => l.kind === k).sort(sortL);
  const sum = (ls: LedgerLine[]) => { const c = zero(); ls.forEach((l) => (Object.keys(c) as (keyof Cols)[]).forEach((k) => { c[k] += l.cols[k]; })); (Object.keys(c) as (keyof Cols)[]).forEach((k) => { c[k] = r2(c[k]); }); return c; };
  const revenue = pick("revenue"), capital = pick("capital"), other = pick("other");
  const totals = { revenue: sum(revenue), capital: sum(capital), other: sum(other), all: sum([...revenue, ...capital, ...other]) };

  const review: ReviewParty[] = []; const checked: ReviewParty[] = [];
  for (const [key, amount] of partyAmt) {
    const f = factsOf(key, books, pms[key], s);
    const g = (f.gstin ?? "").toUpperCase();
    const reasons = reviewReasons({ ...f, checked: null }, in2b && g && isValidGstin(g) ? in2b.has(g) : null);
    const item = { key, name: f.name, gstin: g, status: statusOf(f), reasons, amount: r2(amount), checked: f.checked ?? null };
    if (f.checked) checked.push(item); else if (reasons.length) review.push(item);
  }
  review.sort((a, b) => b.amount - a.amount); checked.sort((a, b) => b.amount - a.amount);

  // left out = what the books have minus what the saved rows report, ledger by ledger (so the working always ties)
  const inc = new Map<string, number>();
  rows.forEach((r) => { if (r.include && r.upload_id === books.upload_id) inc.set(r.expense_head ?? "", (inc.get(r.expense_head ?? "") ?? 0) + Number(r.amount)); });
  const excluded = Object.entries(books.ledgers).filter(([, l]) => l.k === "revenue")
    .map(([name, l]) => { const left = r2(l.total - (inc.get(name) ?? 0)); return { name, reason: !inc.has(name) ? (ledgerChosen(name, l, s) ? "Left out in Review" : l.x ?? "Left out by you") : "Some entries left out in Review", amount: left }; })
    .filter((e) => Math.abs(e.amount) >= 0.005).sort((a, b) => b.amount - a.amount);
  const booksRevenue = r2(Object.values(books.ledgers).filter((l) => l.k === "revenue").reduce((t, l) => t + l.total, 0));
  const excludedRevenue = r2(excluded.reduce((t, e) => t + e.amount, 0));
  return { revenue, capital, other, totals, review, checked, excluded,
    recon: { booksRevenue, excludedRevenue, capitalAdditions: totals.capital.total, otherRows: totals.other.total, reported: totals.all.total } };
}

// ---------- import ----------

export interface ImportDraft { party_name: string; normalized_name: string; gstin: string | null; expense_head: string; amount: number; nature: null; remark: string; include: boolean; row_no: number }

/** Everything to save for a Tally import: the rows (all candidate ledgers; left-out ones with include = false) and the year's summary. */
export function prepareImport(b: Books, s: C44Settings, meta: { upload_id: string; file: string; b2b?: C44Books["b2b"] }) {
  const cand = candidateLedgers(b);
  const all = new Set(cand.map((c) => c.name.toLowerCase()));
  const res = buildBreakup(b, all);
  const ledgers: Record<string, StoredLedger> = {};
  for (const c of cand) {
    const net = res.ledgerTotals[c.name] ?? 0;
    // Fixed Assets: additions only (credits – sale, depreciation – are shown separately)
    const total = c.kind === "capital" ? (res.capitalAdded[c.name] ?? 0) : net;
    ledgers[c.name] = { k: c.kind, g: c.group, p: c.primary, t: c.tax, x: c.exclusion, total, ...(res.notCounted[c.name] ? { out: res.notCounted[c.name] } : {}) };
  }
  const parties: Record<string, StoredParty> = {};
  Object.values(res.parties).forEach((p) => { parties[p.key] = { n: p.name, gstin: p.gstin, reg: p.reg, via: p.via, gb: p.gstBills, b: p.bills, ...(p.trade ? { tr: true } : {}) }; });
  const books: C44Books = { upload_id: meta.upload_id, file: meta.file, at: new Date().toISOString(), ledgers, parties, b2b: meta.b2b ?? null };
  const rows: ImportDraft[] = res.rows.map((r, i) => {
    const p = res.parties[r.party];
    const l = ledgers[r.ledger];
    return { party_name: p.name.slice(0, 300), normalized_name: p.key.slice(0, 300), gstin: p.gstin || null, expense_head: r.ledger.slice(0, 300), amount: r.amount,
      nature: null, remark: `${l.p}${l.g && l.g !== l.p ? ` › ${l.g}` : ""} · ${r.entries} ${r.entries === 1 ? "entry" : "entries"}`.slice(0, 500),
      include: ledgerChosen(r.ledger, l, s), row_no: i + 1 };
  });
  return { books, rows, counts: { ledgers: cand.length, chosen: cand.filter((c) => ledgerChosen(c.name, ledgers[c.name], s)).length, parties: Object.keys(parties).length, vouchers: b.vouchers.length } };
}
