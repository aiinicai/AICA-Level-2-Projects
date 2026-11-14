// Bank statement CSV import + suggested matches to unpaid bills (QuickBooks "bank feed" / Zoho bank reco idea,
// offline and free). Works with the CSV/Excel-saved-as-CSV exports Indian banks provide: we detect the header row
// and the date / narration / debit / credit / reference columns by name.

import type { Expense, PayMode, Vendor } from '../data/types';
import { parseDate } from './extract';
import { round2 } from './money';

export interface BankRow {
  date: string;
  narration: string;
  ref?: string;
  debit: number;
  credit: number;
  mode: PayMode;
}

/** Minimal RFC-4180 CSV parser (quotes, commas and newlines inside quotes). */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], cell = '', q = false;
  const s = text.replace(/^﻿/, '');
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (q) {
      if (c === '"' && s[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') q = false;
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && s[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((x) => x.trim()));
}

const num = (s?: string) => {
  const n = Number((s ?? '').replace(/[,₹\s]|cr|dr/gi, ''));
  return Number.isFinite(n) ? Math.abs(n) : 0;
};

export function detectMode(narration: string): PayMode {
  const n = narration.toUpperCase();
  if (/\bUPI\b/.test(n)) return 'upi';
  if (/\b(CHQ|CHEQUE|CLG)\b/.test(n)) return 'cheque';
  if (/\b(ATM|CASH)\b/.test(n)) return 'cash';
  if (/\b(POS|CARD)\b/.test(n)) return 'card';
  return 'bank';
}

/** Which column holds what. Either Debit (+ Credit) columns, or one Amount column with a Dr/Cr column (or a sign). */
export interface BankMapping {
  headerRow: number;
  date: number; narration: number; ref?: number;
  debit?: number; credit?: number;
  amount?: number; drCr?: number;
  /** only with a single Amount column and no Dr/Cr column: true = a minus sign means money paid out */
  minusIsDebit?: boolean;
}

/** Find the header row and the columns by name. Returns undefined when the columns cannot be told apart — then the person maps them. */
export function guessMapping(rows: string[][]): BankMapping | undefined {
  for (let hi = 0; hi < Math.min(rows.length, 30); hi++) {
    const h = rows[hi].map((c) => String(c ?? '').trim().toLowerCase());
    const col = (re: RegExp) => h.findIndex((c) => re.test(c));
    const date = col(/^(txn\s*|transaction\s*|value\s*|tran\s*)?date/);
    if (date < 0) continue;
    const narration = col(/(narration|description|particulars|remarks|details)/);
    const ref = col(/(ref|chq|cheque|utr)/);
    const debit = col(/(withdraw|debit|dr\b)/);
    const credit = col(/(deposit|credit|cr\b)/);
    const drCr = h.findIndex((c) => /^(dr\s*\/\s*cr|cr\s*\/\s*dr|type|debit\s*\/\s*credit|d\/c)$/.test(c));
    const amount = h.findIndex((c, i) => i !== drCr && /^(transaction\s*)?amount(\s*\(.*\))?$|^amt$/.test(c));
    if (narration < 0) continue;
    if (drCr >= 0 && amount >= 0) return { headerRow: hi, date, narration, ref: ref >= 0 ? ref : undefined, amount, drCr };
    if (debit >= 0 && debit !== drCr) return { headerRow: hi, date, narration, ref: ref >= 0 ? ref : undefined, debit, credit: credit >= 0 && credit !== debit ? credit : undefined };
    if (amount >= 0) return undefined; // one Amount column with no Dr/Cr: the sign rule must come from the person
  }
  return undefined;
}

const isDebitWord = (v: string) => /^(dr|d|debit|withdrawal|wdl|out)\.?$/i.test(v.trim());
const isCreditWord = (v: string) => /^(cr|c|credit|deposit|in)\.?$/i.test(v.trim());

export function applyMapping(rows: string[][], m: BankMapping): BankRow[] {
  const out: BankRow[] = [];
  for (const r of rows.slice(m.headerRow + 1)) {
    const cell = (i?: number) => (i === undefined || i < 0 ? '' : String(r[i] ?? '').trim());
    const date = parseDate(cell(m.date));
    if (!date) continue; // totals / footer lines
    const narration = cell(m.narration);
    let debit = 0, credit = 0;
    if (m.amount !== undefined) {
      const raw = cell(m.amount);
      const v = num(raw);
      if (m.drCr !== undefined) { const t = cell(m.drCr); if (isDebitWord(t)) debit = v; else if (isCreditWord(t)) credit = v; else continue; } // unknown marker → skipped, not guessed
      else if (/-/.test(raw) === !!m.minusIsDebit) debit = v; else credit = v;
    } else {
      debit = num(cell(m.debit));
      credit = m.credit !== undefined ? num(cell(m.credit)) : 0;
    }
    out.push({ date, narration, ref: cell(m.ref) || undefined, debit, credit, mode: detectMode(narration) });
  }
  return out;
}

export type SavedColumns = NonNullable<import('../data/types').BankAccount['statementColumns']>;

/** Header names → mapping, for a statement from the same bank (finds the header row that has all the saved names). */
export function mappingFromNames(rows: string[][], c: SavedColumns): BankMapping | undefined {
  for (let hi = 0; hi < Math.min(rows.length, 30); hi++) {
    const h = rows[hi].map((x) => String(x ?? '').trim().toLowerCase());
    const at = (n?: string) => (n ? h.indexOf(n.trim().toLowerCase()) : undefined);
    const m: BankMapping = { headerRow: hi, date: at(c.date)!, narration: at(c.narration)!, ref: at(c.ref), debit: at(c.debit), credit: at(c.credit), amount: at(c.amount), drCr: at(c.drCr), minusIsDebit: c.minusIsDebit };
    const need = [m.date, m.narration, ...(c.amount ? [m.amount] : [m.debit]), ...(c.drCr ? [m.drCr] : [])];
    if (need.every((i) => i !== undefined && i >= 0)) {
      for (const k of ['ref', 'credit', 'drCr', 'amount', 'debit'] as const) if (m[k] === -1) m[k] = undefined;
      return m;
    }
  }
  return undefined;
}

export function namesFromMapping(rows: string[][], m: BankMapping): SavedColumns {
  const h = rows[m.headerRow].map((x) => String(x ?? '').trim());
  const n = (i?: number) => (i === undefined || i < 0 ? undefined : h[i]);
  return { date: n(m.date)!, narration: n(m.narration)!, ref: n(m.ref), debit: n(m.debit), credit: n(m.credit), amount: n(m.amount), drCr: n(m.drCr), minusIsDebit: m.minusIsDebit };
}

export function parseBankStatement(text: string): BankRow[] {
  const rows = parseCsv(text);
  const m = guessMapping(rows);
  if (!m) throw new Error('Could not find the header row (needs Date and Debit/Withdrawal columns)');
  return applyMapping(rows, m);
}

/** CSV or Excel (.xlsx) → rows of text. Excel is read in the browser (read-excel-file), nothing is uploaded. */
export async function readStatementFile(f: File): Promise<string[][]> {
  if (/\.xlsx$/i.test(f.name) || f.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
    const { readSheet } = await import('read-excel-file/browser');
    const rows = (await readSheet(f)) as unknown[][];
    const text = (v: unknown) => (v instanceof Date ? `${String(v.getDate()).padStart(2, '0')}/${String(v.getMonth() + 1).padStart(2, '0')}/${v.getFullYear()}` : v === null || v === undefined ? '' : String(v));
    return rows.map((r) => r.map(text)).filter((r) => r.some((x) => x.trim()));
  }
  if (/\.xls$/i.test(f.name)) throw new Error('Old .xls files cannot be read — save it as .xlsx or CSV');
  return parseCsv(await f.text());
}

export interface BankMatch {
  row: BankRow;
  vendor?: Vendor;
  bills: { expense: Expense; amount: number }[];
  confidence: 'high' | 'medium' | 'low';
  reason: string;
}

const tokens = (s: string) => s.toUpperCase().replace(/[^A-Z0-9 ]/g, ' ').split(/\s+/).filter((t) => t.length >= 4 && !/^(PVT|LTD|PRIVATE|LIMITED|SERVICES|TRADERS|ENTERPRISES|NEFT|IMPS|RTGS|TRANSFER)$/.test(t));

/**
 * Suggest which unpaid bills a bank debit settles.
 * 1) vendor named in the narration (name tokens) or a bill number found in it; 2) amount equals one bill's
 * balance, or the sum of that vendor's oldest balances. Suggestions only — the user confirms each one.
 */
export function matchBankRows(rows: BankRow[], vendors: Vendor[], bills: { expense: Expense; due: number }[]): BankMatch[] {
  return rows.filter((r) => r.debit > 0).map((row) => {
    const nar = row.narration.toUpperCase();
    const byBillNo = bills.find((b) => b.expense.invoiceNo && b.expense.invoiceNo.length >= 3 && nar.includes(b.expense.invoiceNo.toUpperCase()));
    const vendor = byBillNo
      ? vendors.find((v) => v.id === byBillNo.expense.vendorId)
      : vendors.find((v) => tokens(v.name).some((t) => nar.includes(t)));
    const pool = bills.filter((b) => (vendor ? b.expense.vendorId === vendor.id : true) && b.due > 0)
      .sort((a, b) => a.expense.invoiceDate.localeCompare(b.expense.invoiceDate));

    const exact = pool.find((b) => Math.abs(b.due - row.debit) < 0.01);
    if (exact) {
      return { row, vendor: vendor ?? vendors.find((v) => v.id === exact.expense.vendorId), bills: [{ expense: exact.expense, amount: row.debit }],
        confidence: vendor ? 'high' : 'medium', reason: vendor ? 'Vendor and amount match' : 'Amount matches one unpaid bill' };
    }
    if (vendor) {
      // oldest-first allocation across the vendor's bills; remainder becomes an advance
      let left = row.debit;
      const alloc: { expense: Expense; amount: number }[] = [];
      for (const b of pool) {
        if (left <= 0) break;
        const a = round2(Math.min(left, b.due));
        alloc.push({ expense: b.expense, amount: a });
        left = round2(left - a);
      }
      return { row, vendor, bills: alloc, confidence: alloc.length ? 'medium' : 'low',
        reason: alloc.length ? `Vendor found in narration; applied oldest bills first${left > 0 ? `, ₹${left} as advance` : ''}` : 'Vendor found, no unpaid bills — would be an advance' };
    }
    return { row, bills: [], confidence: 'low', reason: 'No vendor or amount match — choose manually or skip' };
  });
}
