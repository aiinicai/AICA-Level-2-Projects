/**
 * Reconciliation engine.
 *
 * Stage 1 (primary): GSTIN + normalised invoice no.  → exact / within tolerance / ITC mismatch,
 *                    and leftovers "missing in books" / "missing in 2B".
 * Stage 2 (smart):   only the stage-1 leftovers go through three passes
 *                    1. invoice core serial (prefixes, FY tags, leading zeros removed)
 *                    2. GSTIN + total ITC + invoice date
 *                    3. GSTIN + taxable + IGST + CGST + SGST (invoice no. ignored)
 *
 * Fix over the AI Studio version: every invoice ends up in exactly ONE final status
 * (see buildLedger). A smart-matched invoice is no longer also counted as "missing".
 */
import type { BlockedCredit, Datasets, FinalStatus, PrimaryResult, Row, SmartResult, Supplier } from '../types';
import { checkGstin, stateOf } from './gstin';
import { financialYearStart, monthOf, parseIndianDate } from './dates';

export const itc = (r: { igst?: number; cgst?: number; sgst?: number }) => (r.igst || 0) + (r.cgst || 0) + (r.sgst || 0);
const r2 = (n: number) => Math.round(n * 100) / 100;

/** Invoice no. for exact matching: upper case, no spaces, "2025-26" → "25-26", leading zeros per "/" part removed. */
export function invKey(inv: string) {
  return String(inv ?? '')
    .trim()
    .toUpperCase()
    .replace(/\s+/g, '')
    .replace(/\b(20\d{2})-(\d{2})\b/g, (_m, y: string, n: string) => `${y.slice(2)}-${n}`)
    .split('/')
    .map((p) => p.replace(/^0+(\d+)$/, '$1'))
    .join('/');
}

/**
 * Invoice "core" for smart pass 1: financial-year tags removed, then the digits only,
 * without leading zeros. TAX-2024-25/0091, ST/2025-26/0091, INV/91 and 91 all become "91".
 */
export function invCore(inv: string) {
  const s = String(inv ?? '')
    .toUpperCase()
    // FY tags are two consecutive years: 2025-26, 25-26, 2025-2026, 25/26
    .replace(/(?<!\d)(?:20)?(\d{2})\s*[-/]\s*(?:20)?(\d{2})(?!\d)/g, (m: string, a: string, b: string) =>
      (Number(b) - Number(a) + 100) % 100 === 1 ? ' ' : m
    )
    .replace(/FY\s*\d{2,4}/g, ' ');
  const digits = (s.match(/\d+/g) || []).join('').replace(/^0+(?=\d)/, '');
  if (digits) return digits;
  return s.replace(/[^A-Z]/g, '');
}

export const rowKey = (r: { gstin: string; inv: string }) => `${String(r.gstin).toUpperCase()}||${invKey(r.inv)}`;

/* -------------------------------- Stage 1 ---------------------------------- */

export function primaryRecon(g2b: Row[], bks: Row[], tol: number): PrimaryResult[] {
  const out: PrimaryResult[] = [];
  const books = new Map<string, Row>();
  for (const b of bks) books.set(rowKey(b), b);
  const used = new Set<string>();
  for (const g of g2b) {
    const k = rowKey(g);
    const b = books.get(k);
    if (!b || used.has(k)) {
      out.push({ s: 'mb', g2b: g, bk: null, diff: 0, tm: false });
      continue;
    }
    used.add(k);
    const diff = r2(itc(b) - itc(g));
    const within = Math.abs(diff) <= tol;
    out.push({ s: within ? 'ok' : 'am', g2b: g, bk: b, diff, tm: within && Math.abs(diff) > 0.001 });
  }
  for (const b of bks) if (!used.has(rowKey(b))) out.push({ s: 'm2', g2b: null, bk: b, diff: 0, tm: false });
  return out;
}

/* -------------------------------- Stage 2 ---------------------------------- */

export function smartRecon(primary: PrimaryResult[], tol: number): SmartResult[] {
  const gs = primary.filter((p) => p.s === 'mb').map((p) => p.g2b!);
  const bs = primary.filter((p) => p.s === 'm2').map((p) => p.bk!);
  const out: SmartResult[] = [];
  const gDone = new Set<number>();
  const bDone = new Set<number>();

  const pass = (keyOf: (r: Row) => string | null, emit: (g: Row, b: Row) => SmartResult) => {
    const index = new Map<string, number[]>();
    bs.forEach((b, i) => {
      if (bDone.has(i)) return;
      const k = keyOf(b);
      if (!k) return;
      const list = index.get(k);
      if (list) list.push(i);
      else index.set(k, [i]);
    });
    gs.forEach((g, gi) => {
      if (gDone.has(gi)) return;
      const k = keyOf(g);
      if (!k) return;
      const list = index.get(k);
      const bi = list?.find((i) => !bDone.has(i));
      if (bi === undefined) return;
      gDone.add(gi);
      bDone.add(bi);
      out.push(emit(g, bs[bi]));
    });
  };

  const G = (r: Row) => r.gstin.toUpperCase();
  // Pass 1: invoice core serial
  pass(
    (r) => {
      const c = invCore(r.inv);
      return c ? `${G(r)}||${c}` : null;
    },
    (g, b) => {
      const diff = r2(itc(b) - itc(g));
      return { s: Math.abs(diff) <= tol ? 'cm' : 'cx', g2b: g, bk: b, diff, gc: invCore(g.inv), bc: invCore(b.inv) };
    }
  );
  // Pass 2: GSTIN + gross ITC + date
  pass(
    (r) => (r.date && itc(r) ? `${G(r)}||${itc(r).toFixed(2)}||${r.date}` : null),
    (g, b) => ({ s: 'ad', g2b: g, bk: b, diff: r2(itc(b) - itc(g)) })
  );
  // Pass 3: GSTIN + taxable + each tax head
  pass(
    (r) =>
      r.taxable || itc(r)
        ? `${G(r)}||${r.taxable.toFixed(2)}||${(r.igst || 0).toFixed(2)}||${(r.cgst || 0).toFixed(2)}||${(r.sgst || 0).toFixed(2)}`
        : null,
    (g, b) => ({ s: 'ti', g2b: g, bk: b, diff: r2(itc(b) - itc(g)) })
  );

  gs.forEach((g, i) => !gDone.has(i) && out.push({ s: 'smb', g2b: g, bk: null, diff: 0, gc: invCore(g.inv) }));
  bs.forEach((b, i) => !bDone.has(i) && out.push({ s: 'sm2', g2b: null, bk: b, diff: 0, bc: invCore(b.inv) }));
  return out;
}

/* ------------------------------ Final ledger ------------------------------- */

export interface LedgerLine {
  key: string;
  status: FinalStatus;
  /** For smart matches: which pass matched it. */
  pass?: 'cm' | 'cx' | 'ad' | 'ti';
  g2b: Row | null;
  bk: Row | null;
  diff: number;
}

export function buildLedger(primary: PrimaryResult[], smart: SmartResult[]): LedgerLine[] {
  const lines: LedgerLine[] = [];
  for (const p of primary) {
    if (p.s === 'ok' || p.s === 'am') {
      lines.push({ key: rowKey(p.g2b!), status: p.s === 'am' ? 'mismatch' : p.tm ? 'tol' : 'exact', g2b: p.g2b, bk: p.bk, diff: p.diff });
    }
  }
  for (const s of smart) {
    const ref = (s.g2b || s.bk)!;
    if (s.s === 'smb') lines.push({ key: rowKey(ref), status: 'missBooks', g2b: s.g2b, bk: null, diff: 0 });
    else if (s.s === 'sm2') lines.push({ key: rowKey(ref), status: 'miss2b', g2b: null, bk: s.bk, diff: 0 });
    else lines.push({ key: rowKey(s.g2b!), status: 'smart', pass: s.s, g2b: s.g2b, bk: s.bk, diff: s.diff });
  }
  return lines;
}

export const STATUS_LABEL: Record<FinalStatus, string> = {
  exact: 'Matched (exact)',
  tol: 'Matched (within tolerance)',
  mismatch: 'ITC mismatch',
  smart: 'Smart matched',
  missBooks: 'Missing in books',
  miss2b: 'Missing in GSTR-2B',
};

export const PASS_LABEL: Record<string, string> = {
  cm: 'Pass 1: invoice core',
  cx: 'Pass 1: invoice core (tax differs)',
  ad: 'Pass 2: amount + date',
  ti: 'Pass 3: tax values',
};

/* ------------------------------- Summaries --------------------------------- */

export interface Heads {
  igst: number;
  cgst: number;
  sgst: number;
}
const zero = (): Heads => ({ igst: 0, cgst: 0, sgst: 0 });
const add = (h: Heads, r: { igst?: number; cgst?: number; sgst?: number }) => {
  h.igst += r.igst || 0;
  h.cgst += r.cgst || 0;
  h.sgst += r.sgst || 0;
  return h;
};
export const headsTotal = (h: Heads) => h.igst + h.cgst + h.sgst;

/** RCM bills: separately uploaded file plus rows auto-detected in GSTR-2B / books (no duplicates). */
export function rcmRegister(ds: Datasets): (Row & { origin: string })[] {
  const seen = new Set<string>();
  const out: (Row & { origin: string })[] = [];
  const push = (r: Row, origin: string) => {
    const k = rowKey(r);
    if (seen.has(k)) return;
    seen.add(k);
    out.push({ ...r, origin });
  };
  ds.rcm.forEach((r) => push(r, 'RCM file'));
  ds.g2b.filter((r) => r.rcm).forEach((r) => push(r, 'GSTR-2B (auto)'));
  ds.bks.filter((r) => r.rcm).forEach((r) => push(r, 'Books (auto)'));
  return out;
}

export interface Table4 {
  eligible: Heads; // 4(A)(5)
  rcm: Heads; // 4(A)(3)
  review: Heads; // mismatches + smart matches
  missBooks: Heads;
  miss2b: Heads;
  cdn: Heads;
  blocked: Heads; // 4(B)(1)
  net: Heads; // 4(C)
}

export function table4(lines: LedgerLine[], ds: Datasets, activeBlocked: Set<string>): Table4 {
  const t: Table4 = { eligible: zero(), rcm: zero(), review: zero(), missBooks: zero(), miss2b: zero(), cdn: zero(), blocked: zero(), net: zero() };
  for (const l of lines) {
    if ((l.status === 'exact' || l.status === 'tol') && l.g2b) {
      if (l.g2b.rcm) continue; // reverse-charge ITC belongs in 4(A)(3)
      add(t.eligible, l.g2b);
      if (activeBlocked.has(l.key)) add(t.blocked, l.g2b);
    } else if ((l.status === 'mismatch' || l.status === 'smart') && l.g2b) add(t.review, l.g2b);
    else if (l.status === 'missBooks' && l.g2b) add(t.missBooks, l.g2b);
    else if (l.status === 'miss2b' && l.bk) add(t.miss2b, l.bk);
  }
  rcmRegister(ds).forEach((r) => add(t.rcm, r));
  [...ds.g2b_cdn, ...ds.cdn_g2b].forEach((r) => add(t.cdn, r));
  t.net = {
    igst: t.eligible.igst + t.rcm.igst - t.blocked.igst,
    cgst: t.eligible.cgst + t.rcm.cgst - t.blocked.cgst,
    sgst: t.eligible.sgst + t.rcm.sgst - t.blocked.sgst,
  };
  return t;
}

export interface Counts {
  exact: number;
  tol: number;
  mismatch: number;
  smart: number;
  missBooks: number;
  miss2b: number;
  total: number;
}

export function countLines(lines: LedgerLine[]): Counts {
  const c: Counts = { exact: 0, tol: 0, mismatch: 0, smart: 0, missBooks: 0, miss2b: 0, total: lines.length };
  for (const l of lines) c[l.status]++;
  return c;
}

export interface SummaryRow {
  key: string;
  label: string;
  name: string;
  g2bInv: number;
  bksInv: number;
  matched: number;
  smart: number;
  mismatch: number;
  missBooks: number;
  miss2b: number;
  itc2b: number;
  itcBooks: number;
}

export function summarise(lines: LedgerLine[], by: 'gstin' | 'month'): SummaryRow[] {
  const map = new Map<string, SummaryRow>();
  for (const l of lines) {
    const ref = (l.g2b || l.bk)!;
    let key: string;
    let label: string;
    if (by === 'gstin') {
      key = label = ref.gstin;
    } else {
      const m = monthOf(l.g2b?.date || l.bk?.date || '');
      key = m ? m.key : '9999-99';
      label = m ? m.label : 'No date';
    }
    let s = map.get(key);
    if (!s) {
      s = { key, label, name: ref.name, g2bInv: 0, bksInv: 0, matched: 0, smart: 0, mismatch: 0, missBooks: 0, miss2b: 0, itc2b: 0, itcBooks: 0 };
      map.set(key, s);
    }
    if (!s.name && ref.name) s.name = ref.name;
    if (l.g2b) {
      s.g2bInv++;
      s.itc2b += itc(l.g2b);
    }
    if (l.bk) {
      s.bksInv++;
      s.itcBooks += itc(l.bk);
    }
    if (l.status === 'exact' || l.status === 'tol') s.matched++;
    else if (l.status === 'smart') s.smart++;
    else if (l.status === 'mismatch') s.mismatch++;
    else if (l.status === 'missBooks') s.missBooks++;
    else s.miss2b++;
  }
  const rows = Array.from(map.values());
  return by === 'gstin' ? rows.sort((a, b) => b.itc2b - a.itc2b) : rows.sort((a, b) => a.key.localeCompare(b.key));
}

/** Suppliers in the purchase books with no invoice at all in GSTR-2B (Rule 37A risk). */
export function nonFilers(g2b: Row[], bks: Row[]) {
  const filed = new Set(g2b.map((r) => r.gstin.toUpperCase()));
  const map = new Map<string, { gstin: string; name: string; invCount: number; itc: number }>();
  for (const r of bks) {
    const g = r.gstin.toUpperCase();
    if (filed.has(g)) continue;
    const e = map.get(g) ?? { gstin: g, name: r.name, invCount: 0, itc: 0 };
    e.invCount++;
    e.itc += itc(r);
    map.set(g, e);
  }
  return Array.from(map.values()).sort((a, b) => b.itc - a.itc);
}

/* ------------------------------ Health checks ------------------------------- */

export function gstinRegister(g2b: Row[], bks: Row[]) {
  const map = new Map<string, { gstin: string; name: string; src: string[] }>();
  const addR = (r: Row, src: string) => {
    const g = r.gstin.toUpperCase();
    const e = map.get(g) ?? { gstin: g, name: r.name, src: [] };
    if (!e.src.includes(src)) e.src.push(src);
    if (!e.name && r.name) e.name = r.name;
    map.set(g, e);
  };
  g2b.forEach((r) => addR(r, 'GSTR-2B'));
  bks.forEach((r) => addR(r, 'Books'));
  return Array.from(map.values()).map((e) => {
    const chk = checkGstin(e.gstin);
    return { ...e, valid: chk.valid, error: chk.valid ? '' : chk.error, state: stateOf(e.gstin) };
  });
}

/** Same invoice no. booked against different GSTINs within one register. */
export function crossPartyDuplicates(g2b: Row[], bks: Row[]) {
  const find = (rows: Row[], source: string) => {
    const map = new Map<string, Row[]>();
    for (const r of rows) {
      const k = invKey(r.inv);
      if (!k) continue;
      const list = map.get(k);
      if (list) list.push(r);
      else map.set(k, [r]);
    }
    return Array.from(map.entries())
      .filter(([, list]) => new Set(list.map((r) => r.gstin.toUpperCase())).size > 1)
      .map(([inv, list]) => ({ source, inv, rows: list }));
  };
  return [...find(g2b, 'GSTR-2B'), ...find(bks, 'Books')];
}

/**
 * Section 16(4): ITC on an invoice of FY X-(X+1) can be claimed only up to 30 November of
 * year X+1. Lists GSTR-2B invoices whose last date has passed as of `today`.
 */
export function timeBarred(g2b: Row[], today = new Date()) {
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const out: (Row & { fy: string; deadline: string; daysOver: number })[] = [];
  for (const r of g2b) {
    const d = parseIndianDate(r.date);
    if (!d) continue;
    const fy = financialYearStart(d);
    const deadline = new Date(fy + 1, 10, 30);
    if (t > deadline) {
      out.push({
        ...r,
        fy: `${fy}-${String(fy + 1).slice(2)}`,
        deadline: `30/11/${fy + 1}`,
        daysOver: Math.round((t.getTime() - deadline.getTime()) / 864e5),
      });
    }
  }
  return out.sort((a, b) => b.daysOver - a.daysOver);
}

/* ------------------------------- Follow-ups -------------------------------- */

export interface FollowUp {
  gstin: string;
  name: string;
  items: (Row & { issue: string })[];
  itcAtRisk: number;
}

/**
 * Suppliers to chase. "missing" = invoices in books still missing from GSTR-2B after all
 * smart passes; "all" also includes ITC mismatches.
 */
export function followUps(lines: LedgerLine[], mode: 'missing' | 'all'): FollowUp[] {
  const map = new Map<string, FollowUp>();
  for (const l of lines) {
    if (!l.bk) continue;
    const issue = l.status === 'miss2b' ? 'Not in GSTR-2B' : l.status === 'mismatch' && mode === 'all' ? `ITC differs by ${l.diff.toFixed(2)}` : '';
    if (!issue) continue;
    const g = l.bk.gstin.toUpperCase();
    const f = map.get(g) ?? { gstin: g, name: l.bk.name, items: [], itcAtRisk: 0 };
    f.items.push({ ...l.bk, issue });
    f.itcAtRisk += l.status === 'miss2b' ? itc(l.bk) : Math.abs(l.diff);
    map.set(g, f);
  }
  return Array.from(map.values()).sort((a, b) => b.itcAtRisk - a.itcAtRisk);
}

/* ---------------------------------- CDN ------------------------------------ */

export function cdnRecon(ds: Datasets, tol: number) {
  const g2b = [...ds.g2b_cdn, ...ds.cdn_g2b];
  const bks = [...ds.bks_cdn, ...ds.cdn_bks];
  const books = new Map<string, Row>();
  bks.forEach((b) => books.set(rowKey(b), b));
  const used = new Set<string>();
  const out: { s: 'ok' | 'am' | 'mb' | 'm2'; g2b: Row | null; bk: Row | null; diff: number }[] = [];
  for (const g of g2b) {
    const k = rowKey(g);
    const b = books.get(k);
    if (!b || used.has(k)) {
      out.push({ s: 'mb', g2b: g, bk: null, diff: 0 });
      continue;
    }
    used.add(k);
    const diff = r2(itc(b) - itc(g));
    out.push({ s: Math.abs(diff) <= tol ? 'ok' : 'am', g2b: g, bk: b, diff });
  }
  bks.forEach((b) => !used.has(rowKey(b)) && out.push({ s: 'm2', g2b: null, bk: b, diff: 0 }));
  return out;
}

/* ------------------------------- Everything -------------------------------- */

export function runAll(ds: Datasets, tol: number, blocked: BlockedCredit[]) {
  const primary = primaryRecon(ds.g2b, ds.bks, tol);
  const smart = smartRecon(primary, tol);
  const lines = buildLedger(primary, smart);
  const activeBlocked = new Set(blocked.filter((b) => b.active).map((b) => `${b.gstin}||${b.invKey}`));
  return { primary, smart, lines, activeBlocked, counts: countLines(lines), t4: table4(lines, ds, activeBlocked) };
}

export type Recon = ReturnType<typeof runAll>;

export const msmeLabel = (s?: Supplier) =>
  !s || s.msmeStatus === 'unverified'
    ? 'Not checked'
    : s.msmeStatus === 'unregistered'
      ? 'Not MSME'
      : s.msmeStatus === 'micro'
        ? 'Micro enterprise'
        : s.msmeStatus === 'small'
          ? 'Small enterprise'
          : 'Medium enterprise';
