// Header detection, smart column mapping and conversion of raw rows into expense rows.

import { parseAmount, parseDate } from "../format";
import { cleanGstin, gstinStatus, GstinStatus } from "../validators";
import { normalizeParty } from "../party";
import type { Matrix, Cell } from "./sources";

export type FieldKey = "party" | "gstin" | "head" | "amount" | "debit" | "credit" | "drcr" | "date" | "nature";

export const FIELDS: { key: FieldKey; label: string; required?: boolean; hint: string }[] = [
  { key: "party", label: "Party name", required: true, hint: "Supplier / vendor / ledger name" },
  { key: "gstin", label: "GSTIN", hint: "Supplier GSTIN (blank = unregistered)" },
  { key: "head", label: "Expense head", hint: "Ledger / account / expense category" },
  { key: "amount", label: "Amount", hint: "Single amount column" },
  { key: "debit", label: "Debit", hint: "Use instead of Amount when Dr/Cr are separate" },
  { key: "credit", label: "Credit", hint: "Credits are deducted from debits" },
  { key: "drcr", label: "Dr/Cr indicator", hint: "Column containing Dr or Cr" },
  { key: "date", label: "Date", hint: "Voucher / invoice date" },
  { key: "nature", label: "Goods / Services", hint: "Nature of supply (optional)" },
];

export type Mapping = Partial<Record<FieldKey, number>> & { headerRow: number };

const SYNONYMS: Record<FieldKey, string[]> = {
  party: ["party name", "party", "supplier name", "supplier", "vendor name", "vendor", "particulars", "name of party",
    "ledger name", "account name", "trade name", "trade/legal name", "legal name", "payee", "creditor", "name"],
  gstin: ["gstin", "gst no", "gst number", "gstin/uin", "supplier gstin", "gstin of supplier", "party gstin", "gst in", "gstn", "ctin"],
  head: ["expense head", "expense", "ledger", "account", "head", "expense ledger", "account head", "category", "gl account",
    "g/l account", "nature of expense", "purchase ledger", "group"],
  amount: ["amount", "taxable value", "taxable amount", "value", "total", "net amount", "expense amount", "invoice value", "amt", "gross amount"],
  debit: ["debit", "dr amount", "debit amount", "dr", "withdrawal"],
  credit: ["credit", "cr amount", "credit amount", "cr", "deposit"],
  drcr: ["dr/cr", "dr / cr", "type", "drcr"],
  date: ["date", "voucher date", "invoice date", "bill date", "txn date", "transaction date", "posting date", "doc date", "vch date"],
  nature: ["goods/services", "nature", "nature of supply", "type of supply", "goods or services", "supply type"],
};

const norm = (c: Cell) => String(c ?? "").toLowerCase().replace(/[_\-.:]+/g, " ").replace(/\s+/g, " ").trim();

/** Score each of the first rows as a header row; return the best index. */
export function detectHeaderRow(rows: Matrix, scan = 25): number {
  let best = 0, bestScore = -1;
  for (let r = 0; r < Math.min(scan, rows.length); r++) {
    const cells = rows[r].map(norm).filter(Boolean);
    if (cells.length < 2) continue;
    let score = 0;
    for (const c of cells) {
      for (const syns of Object.values(SYNONYMS)) {
        if (syns.includes(c)) { score += 3; break; }
        if (syns.some((s) => s.length > 3 && c.includes(s))) { score += 1; break; }
      }
      if (parseAmount(c) !== null && !/[a-z]/.test(c)) score -= 1;
    }
    if (score > bestScore) { bestScore = score; best = r; }
  }
  return best;
}

export function autoMap(rows: Matrix, headerRow = detectHeaderRow(rows)): Mapping {
  const header = (rows[headerRow] ?? []).map(norm);
  const map: Mapping = { headerRow };
  const used = new Set<number>();
  const order: FieldKey[] = ["gstin", "date", "debit", "credit", "drcr", "nature", "party", "head", "amount"];
  for (const key of order) {
    const syns = SYNONYMS[key];
    let idx = header.findIndex((h, i) => !used.has(i) && syns.includes(h));
    if (idx < 0 && key !== "drcr")
      idx = header.findIndex((h, i) => !used.has(i) && h && syns.some((s) => s.length > 3 && h.includes(s)));
    if (idx >= 0) { map[key] = idx; used.add(idx); }
  }
  // Debit/Credit pair present → don't also use a generic amount column
  if (map.debit !== undefined && map.amount !== undefined && map.credit !== undefined) delete map.amount;
  return map;
}

export interface ExpenseDraft {
  row_no: number;
  party_name: string;
  normalized_name: string;
  gstin: string | null;
  gstin_status: GstinStatus;
  expense_head: string | null;
  amount: number;
  txn_date: string | null;
  nature: "goods" | "services" | null;
  errors: string[];
  warnings: string[];
}

export interface ApplyOptions { skipZero?: boolean; skipTotals?: boolean; absolute?: boolean }

const TOTAL_RE = /^(grand\s+)?total\b|^sub\s*total|^closing balance|^opening balance|^carried over|^brought forward/i;

export function applyMapping(rows: Matrix, map: Mapping, opts: ApplyOptions = {}): ExpenseDraft[] {
  const { skipZero = true, skipTotals = true, absolute = false } = opts;
  const out: ExpenseDraft[] = [];
  const get = (r: Cell[], k: FieldKey) => (map[k] === undefined ? null : r[map[k] as number] ?? null);
  for (let i = map.headerRow + 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || r.every((c) => String(c ?? "").trim() === "")) continue;
    const partyRaw = String(get(r, "party") ?? "").trim();
    const headRaw = String(get(r, "head") ?? "").trim();
    if (skipTotals && (TOTAL_RE.test(partyRaw) || (TOTAL_RE.test(headRaw) && !partyRaw))) continue;
    const errors: string[] = [];
    const warnings: string[] = [];

    let amount: number | null = null;
    if (map.debit !== undefined || map.credit !== undefined) {
      const dr = parseAmount(get(r, "debit"))?.value ?? 0;
      const cr = parseAmount(get(r, "credit"))?.value ?? 0;
      if (get(r, "debit") !== null || get(r, "credit") !== null) amount = dr - cr;
      if (String(get(r, "debit") ?? "").trim() === "" && String(get(r, "credit") ?? "").trim() === "") amount = null;
    }
    if (amount === null && map.amount !== undefined) {
      const p = parseAmount(get(r, "amount"));
      if (p) {
        amount = p.value;
        const ind = String(get(r, "drcr") ?? "").trim().toLowerCase();
        const side = p.side ?? (ind.startsWith("cr") ? "cr" : ind.startsWith("dr") ? "dr" : null);
        if (side === "cr") amount = -Math.abs(amount);
      }
    }
    if (amount === null) {
      if (!partyRaw) continue; // decorative / blank row
      errors.push("Amount missing or not a number");
      amount = 0;
    }
    if (absolute) amount = Math.abs(amount);
    if (skipZero && amount === 0 && errors.length === 0) continue;
    if (amount < 0) warnings.push("Negative amount (credit)");

    const party = partyRaw || headRaw;
    if (!party) errors.push("Party name missing");
    const gstinRaw = cleanGstin(get(r, "gstin"));
    const st = gstinStatus(gstinRaw);
    if (st === "invalid") warnings.push("GSTIN invalid – will be treated as unregistered until corrected");

    const dateCell = get(r, "date");
    const date = parseDate(dateCell);
    if (dateCell !== null && String(dateCell).trim() !== "" && !date) warnings.push("Date not recognised");

    const natureRaw = String(get(r, "nature") ?? "").toLowerCase();
    const nature = /serv/.test(natureRaw) ? "services" : /good/.test(natureRaw) ? "goods" : null;

    out.push({
      row_no: i + 1,
      party_name: party,
      normalized_name: normalizeParty(party) || party.toLowerCase(),
      gstin: gstinRaw || null,
      gstin_status: st,
      expense_head: headRaw || null,
      amount: Math.round(amount * 100) / 100,
      txn_date: date,
      nature,
      errors,
      warnings,
    });
  }
  return out;
}

export function columnLetters(n: number): string {
  let s = "";
  n += 1;
  while (n > 0) { const m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

/** Collect distinct parties with the first valid GSTIN seen (for party master upsert). */
export function distinctParties(rows: ExpenseDraft[]): { party_name: string; normalized_name: string; gstin: string | null }[] {
  const m = new Map<string, { party_name: string; normalized_name: string; gstin: string | null }>();
  for (const r of rows) {
    const cur = m.get(r.normalized_name);
    if (!cur) m.set(r.normalized_name, { party_name: r.party_name, normalized_name: r.normalized_name, gstin: r.gstin_status === "valid" ? r.gstin : null });
    else if (!cur.gstin && r.gstin_status === "valid") cur.gstin = r.gstin;
  }
  return Array.from(m.values());
}
