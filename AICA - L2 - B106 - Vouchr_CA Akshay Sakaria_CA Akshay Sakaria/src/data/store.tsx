// App state. In demo mode everything lives in this browser (localStorage).
// With Supabase connected, the same actions map 1:1 to table writes; the database re-enforces
// every rule below (RLS + triggers in supabase/migrations), so the UI checks are for friendliness only.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type {
  ApiProvider, AuditEntry, Client, ComplianceFinding, ComplianceSource, Expense, ExpenseHead, JobRun, Lang,
  Allocation, BankAccount, Consent, FirmInfo, PayMode, PrivacyRequest, Payment, RecoRun, Role, SystemEvent, TdsChallan, TdsRate, User, Vendor, VendorNote, ItcReversal, FyClose
} from './types';
import { BLOCKED_RULES, EXPENSE_HEADS, NO_IMAGE_REASONS, RCM_RULES, TDS_RATES } from './masters';
import {
  DEMO_CLIENTS, DEMO_EVENTS, DEMO_EXPENSES, DEMO_JOBS, DEMO_PAYMENTS, DEMO_PROVIDERS, DEMO_SOURCES, DEMO_USERS, DEMO_VENDORS
} from './demoSeed';
import { fmtDate, fyLabel, isBackdatedEntry, monthKey, toIso, todayIso } from '../lib/dates';
import { suggestHead, suggestItc, suggestRcm, suggestTds } from '../lib/rules';
import { fmtInr, round2 } from '../lib/money';
import { netPayable, outstanding, unallocated } from '../lib/alerts';
import { checkGstin, checkPan } from '../lib/validators';
import { allocateLines } from '../lib/payalloc';
import { normBillNo } from '../lib/billno';
import { grossUpTds, previewApply } from '../lib/tdsAdvance';
import { checkNote, noteAdjustFor } from '../lib/vendorNotes';
import { autoApproveDecision } from '../lib/autoApprove';
import { riskCheck } from '../lib/anomaly';
import { carryForward, fyChecklist, fyEnd, fyMonths } from '../lib/fyClose';
import { checkCode, CODE_TTL_MIN, hashCode, makeCode, parseVerifyText, type VerifyOutcome } from '../lib/waVerify';
import { dueIn90, NOTICE_VERSION } from '../lib/consent';
import { ROUND_OFF_LIMIT } from '../lib/tallyXml';

export interface State {
  clients: Client[];
  users: User[];
  vendors: Vendor[];
  expenses: Expense[];
  payments: Payment[];
  challans: TdsChallan[];
  recoRuns: RecoRun[];
  heads: ExpenseHead[];
  tdsRates: TdsRate[];
  monthLocks: { clientId: string; month: string }[];
  audit: AuditEntry[];
  events: SystemEvent[];
  jobs: JobRun[];
  providers: ApiProvider[];
  sources: ComplianceSource[];
  findings: ComplianceFinding[];
  currentUserId?: string;
  activeClientId?: string; // super admin's selected client
  lang: Lang;
  seedVersion?: number;
  consents: Consent[];
  privacyRequests: PrivacyRequest[];
  firm: FirmInfo;
  vendorNotes: VendorNote[];
  itcReversals: ItcReversal[];
  fyCloses: FyClose[];
}

export const STORE_KEY = 'vouchr-demo-v2';
/** Bump whenever demo seed data or the stored shape changes; older saved demo data is then replaced. */
const SEED_VERSION = 10;

const initial = (): State => ({
  clients: DEMO_CLIENTS, users: DEMO_USERS, vendors: DEMO_VENDORS, expenses: DEMO_EXPENSES, payments: DEMO_PAYMENTS,
  challans: [], recoRuns: [], heads: EXPENSE_HEADS, tdsRates: TDS_RATES, monthLocks: [{ clientId: 'c1', month: '2026-08' }],
  audit: [], events: DEMO_EVENTS, jobs: DEMO_JOBS, providers: DEMO_PROVIDERS, sources: DEMO_SOURCES, findings: [],
  lang: 'en',
  seedVersion: SEED_VERSION,
  consents: [], privacyRequests: [], firm: { name: 'CA Firm (demo)' }, vendorNotes: [], itcReversals: [], fyCloses: []
});

function load(): State {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const saved = JSON.parse(raw) as State;
      // the API list follows the current code (keeps saved usage for known entries)
      if (saved.seedVersion === SEED_VERSION) return { ...initial(), ...saved, providers: DEMO_PROVIDERS.map((d) => saved.providers?.find((x) => x.code === d.code) ?? d) };
    }
  } catch { /* storage unavailable — fall back to fresh demo data */ }
  return initial();
}

const uid = () => crypto.randomUUID();
const nowIso = () => new Date().toISOString();

export interface PaymentLine {
  mode: PayMode;
  accountId?: string;
  ref?: string;
  paidOn: string;
  amount: number;
}

export interface NewExpenseInput {
  vendorId?: string;
  vendorName: string;
  vendorGstin?: string;
  invoiceNo?: string;
  invoiceDate: string;
  entrySource: Expense['entrySource'];
  irn?: string;
  irnSignature?: Expense['irnSignature'];
  imageHash?: string;
  imageDataUrl?: string;
  attachmentName?: string;
  noImageReason?: string;
  fileId?: string;
  filePath?: string;
  narration?: string;
  costCentreId?: string;
  description?: string;
  hsnSac?: string;
  grossAmount: number;
  discount: number;
  taxableValue: number;
  cgst: number;
  sgst: number;
  igst: number;
  totalAmount: number;
  /** Paid at the time of entry — may be split across modes and dates. */
  payments?: PaymentLine[];
  /** User confirmed this is a different bill from the look-alike with this id. */
  notDuplicateOf?: string;
  nonTaxableAmount?: number;
  ecoPaysTax?: boolean;
  ecoGstin?: string;
}

export interface RecordPaymentInput extends PaymentLine {
  vendorId: string;
  allocations: Allocation[];
  source?: Payment['source'];
  /** Deduct TDS on the advance (unapplied) part of this payment under this TDS code. */
  tdsOnAdvance?: { code: string };
}

/** Business-rule error. `message` is the English text (also the translation key); `vars` fill {placeholders}. */
/** Non-cash payments must say where the money came from; cash only when the client keeps several cash boxes. */
export function needsSource(client: Client, mode: PayMode): boolean {
  const kinds = sourceKinds(mode);
  return client.bankAccounts.some((a) => kinds.includes(a.kind) && a.active !== false) && (mode !== 'cash' || client.bankAccounts.filter((a) => a.kind === 'cash').length > 1);
}

/** Which payment sources fit a payment mode. */
/** Reads a payment mode the way people write it in Excel: "NEFT", "GPay", "Chq", "Petty cash"... */
export function parseMode(raw: string): PayMode | undefined {
  const m = raw.trim().toLowerCase();
  if (!m) return undefined;
  if (/^(cash|नकद|petty)/.test(m)) return 'cash';
  if (/(upi|gpay|google pay|phonepe|paytm|bhim)/.test(m)) return 'upi';
  if (/^(cheque|check|chq|चेक)/.test(m)) return 'cheque';
  if (/(card|कार्ड)/.test(m)) return 'card';
  if (/(bank|neft|rtgs|imps|transfer|net ?banking|बैंक)/.test(m)) return 'bank';
  return undefined;
}

export function sourceKinds(mode: PayMode): BankAccount['kind'][] {
  return mode === 'upi' ? ['upi', 'bank'] : mode === 'card' ? ['card'] : mode === 'cash' ? ['cash'] : ['bank'];
}

export class RuleError extends Error {
  constructor(message: string, public vars?: Record<string, string | number>) {
    super(message);
  }
}

/** Thrown when a bill looks like one already recorded (same vendor, date and amount) — user may confirm it is different. */
export class LookAlikeError extends RuleError {
  constructor(public existing: Expense) {
    super('Looks like a bill already recorded: {vendor} {no} on {date} for ₹{amount}', { vendor: existing.vendorName, no: existing.invoiceNo ?? '', date: existing.invoiceDate, amount: existing.totalAmount });
  }
}

const lockedIn = (locks: State['monthLocks'], cid: string, isoDate: string) => locks.some((l) => l.clientId === cid && l.month === monthKey(isoDate));

export { normBillNo } from '../lib/billno';

export interface BillKey { vendorId?: string; vendorGstin?: string; vendorName: string; invoiceNo?: string; fy?: string; imageHash?: string }

/** Same vendor = same vendor record, or same GSTIN, or same name (names on bills vary, the GSTIN does not). */
function sameVendor(e: Expense, k: BillKey, vendors: Vendor[]) {
  if (k.vendorId && e.vendorId === k.vendorId) return true;
  const g = k.vendorGstin?.toUpperCase();
  if (g && vendors.find((v) => v.id === e.vendorId)?.gstin === g) return true;
  return e.vendorName.trim().toLowerCase() === k.vendorName.trim().toLowerCase();
}

/** Already recorded: the same photo/file, or the same vendor + bill number in the same financial year
 *  (GST invoice serials are unique per financial year, so "001" next April is a new bill). `excludeId` skips the entry being edited. */
export function dupIn(expenses: Expense[], vendors: Vendor[], cid: string, k: BillKey, excludeId?: string) {
  const n = normBillNo(k.invoiceNo);
  return expenses.find((e) => e.clientId === cid && e.id !== excludeId && e.status !== 'rejected' && (
    (k.imageHash && e.imageHash === k.imageHash) ||
    (n && normBillNo(e.invoiceNo) === n && (!k.fy || e.fyLabel === k.fy) && sameVendor(e, k, vendors))
  ));
}

/** Zoho-style look-alike: same vendor, same bill date and same amount (bill number may differ or be missing). */
export function alikeIn(expenses: Expense[], vendors: Vendor[], cid: string, k: BillKey, date: string, total: number, excludeId?: string) {
  return expenses.find((e) => e.clientId === cid && e.id !== excludeId && e.status !== 'rejected' && e.status !== 'draft' &&
    e.invoiceDate === date && Math.abs(e.totalAmount - total) < 0.01 && sameVendor(e, k, vendors));
}

/** Client settings that only the CA firm may change (mirrors guard_client_update in migration 0006). */
export const CONTROL_FIELDS = ['name', 'gstin', 'stateCode', 'backdateWindowDays', 'cashLimitPerDay', 'noteAboveAmount', 'tallyMode', 'engagementEndsOn', 'autoApprove', 'driveShareWithAdmins'] as const;

export type ImportKind = 'vendors' | 'bills' | 'payments' | 'centres' | 'sources';
/** One spreadsheet row after cell clean-up: text, numbers, ISO dates (yyyy-mm-dd). Keys are the template column keys. */
export type ImportRow = Record<string, string | number | undefined>;
export interface ImportRowResult { row: number; ok: boolean; label: string; message?: string; vars?: Record<string, string | number> }

function useStoreValue() {
  const [s, setS] = useState<State>(load);

  useEffect(() => {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(s)); } catch { /* quota or private mode */ }
  }, [s]);

  const me = s.users.find((u) => u.id === s.currentUserId && u.active !== false);
  const clientId = me?.role === 'super_admin' ? s.activeClientId ?? s.clients[0]?.id : me?.clientId;
  const client = s.clients.find((c) => c.id === clientId);

  const audit = (st: State, a: Omit<AuditEntry, 'id' | 'at' | 'actor'>): AuditEntry[] =>
    [{ ...a, id: uid(), at: nowIso(), actor: st.currentUserId ?? 'system' }, ...st.audit].slice(0, 500);

  const isLocked = useCallback((cid: string, isoDate: string) => lockedIn(s.monthLocks, cid, isoDate), [s.monthLocks]);
  const findDuplicate = useCallback((cid: string, vendorName: string, invoiceNo?: string, imageHash?: string, excludeId?: string) =>
    dupIn(s.expenses, s.vendors, cid, { vendorName, invoiceNo, imageHash }, excludeId), [s.expenses, s.vendors]);
  const findLookAlike = useCallback((cid: string, vendorName: string, date: string, total: number, excludeId?: string) =>
    alikeIn(s.expenses, s.vendors, cid, { vendorName }, date, total, excludeId), [s.expenses, s.vendors]);

  /** Builds a Payment with its audit flags (cash limit, backdated, paid before bill date). */
  function makePayment(st: State, input: RecordPaymentInput, vendorName: string, billDates: string[]): Payment {
    const cl = st.clients.find((c) => c.id === clientId)!;
    const flags: string[] = [];
    if (input.mode === 'cash') {
      const sameDay = st.payments.filter((p) => p.clientId === cl.id && p.vendorId === input.vendorId && p.mode === 'cash' && p.paidOn === input.paidOn)
        .reduce((x, p) => x + p.amount, 0);
      if (sameDay + input.amount > cl.cashLimitPerDay) flags.push('cash_limit');
    }
    if (billDates.some((d) => input.paidOn < d)) flags.push('paid_before_bill_date');
    const isBackdated = input.paidOn < todayIso();
    if (isBackdated) flags.push('backdated_payment');
    return {
      id: uid(), clientId: cl.id, vendorId: input.vendorId, vendorName, mode: input.mode, accountId: input.accountId,
      ref: input.ref?.trim() || undefined, paidOn: input.paidOn, amount: round2(input.amount),
      allocations: input.allocations.filter((a) => a.amount > 0).map((a) => ({ ...a, amount: round2(a.amount) })),
      isBackdated, flags: flags.length ? flags : undefined, source: input.source ?? 'manual', createdBy: me!.id, createdAt: nowIso()
    };
  }

  /** Shared validation + suggestion step for new and resubmitted entries. `base` lets a batch import check each row
   *  against the rows before it (vendors created, duplicates inside the same file). */
  function prepare(input: NewExpenseInput, editing?: Expense, base: State = s) {
    if (!me || !client) throw new RuleError('Not signed in');
    const today = todayIso();
    if (!input.vendorName.trim()) throw new RuleError('Enter the vendor name');
    if (!(input.totalAmount > 0)) throw new RuleError('Enter the bill total');
    if (input.discount < 0 || input.discount > input.grossAmount) throw new RuleError('Discount cannot be more than the bill amount');
    if ((input.nonTaxableAmount ?? 0) < 0 || (input.nonTaxableAmount ?? 0) >= input.totalAmount) throw new RuleError('Non-GST charges must be less than the bill total');
    if (input.ecoGstin && !checkGstin(input.ecoGstin).ok) throw new RuleError('GSTIN of the app / operator is not valid');
    if (!input.imageDataUrl && !input.attachmentName && !input.noImageReason) throw new RuleError('Add a photo of the bill, or choose why there is no bill');
    if (input.totalAmount > client.noteAboveAmount && !input.description?.trim()) throw new RuleError('Bills above {amount} need a note: what was it for?', { amount: fmtInr(client.noteAboveAmount) });
    if (input.invoiceDate > today) throw new RuleError('Bill date cannot be in the future');
    if (lockedIn(base.monthLocks, client.id, input.invoiceDate)) throw new RuleError('This month is locked. Ask your admin.');
    const backdated = isBackdatedEntry(input.invoiceDate, today, client.backdateWindowDays);
    const dateChanged = !editing || editing.invoiceDate !== input.invoiceDate;
    if (backdated && dateChanged && me.role === 'sub_user') throw new RuleError('Bills from earlier months can only be added by your admin.');
    for (const pl of input.payments ?? []) {
      if (!(pl.amount > 0)) throw new RuleError('Enter the amount paid');
      if (pl.paidOn > today) throw new RuleError('Payment date cannot be in the future');
      if (lockedIn(base.monthLocks, client.id, pl.paidOn)) throw new RuleError('Payment date falls in a locked month');
      if (needsSource(client, pl.mode) && !pl.accountId) throw new RuleError('Choose where the money was paid from');
      if (pl.accountId && !client.bankAccounts.some((a) => a.id === pl.accountId)) throw new RuleError('Choose where the money was paid from');
    }
    // existing vendor: same id, else same GSTIN (names on bills vary: "ABC Traders" / "ABC TRADERS PVT"), else same name.
    // Not found → created automatically below, so nobody has to set up the vendor master first.
    let vendor = base.vendors.find((v) => v.id === input.vendorId) ??
      (input.vendorGstin ? base.vendors.find((v) => v.clientId === client.id && v.gstin === input.vendorGstin!.toUpperCase()) : undefined) ??
      base.vendors.find((v) => v.clientId === client.id && v.name.toLowerCase() === input.vendorName.trim().toLowerCase());
    // duplicate / look-alike: same vendor (record, GSTIN or name) — checked before anything new is created
    const key: BillKey = { vendorId: vendor?.id, vendorGstin: input.vendorGstin ?? vendor?.gstin, vendorName: input.vendorName, invoiceNo: input.invoiceNo, fy: fyLabel(input.invoiceDate), imageHash: input.imageHash };
    const dup = dupIn(base.expenses, base.vendors, client.id, key, editing?.id);
    if (dup) throw new RuleError('Already recorded on {date} ({vendor} {no})', { date: fmtDate(toIso(new Date(dup.createdAt))), vendor: dup.vendorName, no: dup.invoiceNo ?? '' });
    const alike = alikeIn(base.expenses, base.vendors, client.id, key, input.invoiceDate, input.totalAmount, editing?.id);
    if (alike && input.notDuplicateOf !== alike.id) throw new LookAlikeError(alike);

    let newVendor: Vendor | undefined;
    if (!vendor) {
      const pan = input.vendorGstin?.slice(2, 12);
      newVendor = {
        id: uid(), clientId: client.id, name: input.vendorName.trim(), gstin: input.vendorGstin,
        gstRegistered: !!input.vendorGstin, pan, panEntityType: pan ? checkPan(pan).entityType : undefined,
        panStatus: 'Unverified', stateCode: input.vendorGstin?.slice(0, 2)
      };
      vendor = newVendor;
    } else if (input.vendorGstin && !vendor.gstin) {
      // staff typed a GSTIN for a vendor saved without one → keep the master up to date
      newVendor = { ...vendor, gstin: input.vendorGstin, gstRegistered: true, stateCode: input.vendorGstin.slice(0, 2), pan: vendor.pan ?? input.vendorGstin.slice(2, 12) };
      vendor = newVendor;
    }

    const fy = fyLabel(input.invoiceDate);
    const others = base.expenses.filter((e) => e.vendorId === vendor!.id && e.id !== editing?.id && e.status !== 'rejected');
    const lastFromVendor = others.find((e) => e.headId);
    const text = `${input.vendorName} ${input.description ?? ''}`;
    const h = suggestHead(text, input.hsnSac, base.heads, lastFromVendor?.headId);
    const head = base.heads.find((x) => x.id === h.headId);
    const fyOthers = others.filter((e) => e.fyLabel === fy);
    const ytd = fyOthers.reduce((sum, e) => sum + e.taxableValue, 0);
    const ytdUntaxed = fyOthers.filter((e) => !e.tdsAmount).reduce((sum, e) => sum + e.taxableValue, 0);
    const tds = suggestTds(head, vendor, input.taxableValue, ytd, base.tdsRates, ytdUntaxed, input.invoiceDate);
    const rcm = suggestRcm(head, vendor, RCM_RULES);
    const itc = suggestItc(head, text, vendor.gstRegistered, BLOCKED_RULES);

    const e: Expense = {
      id: editing?.id ?? uid(), clientId: client.id, fyLabel: fy, vendorId: vendor.id, vendorName: vendor.name,
      invoiceNo: input.invoiceNo?.trim() || undefined, invoiceDate: input.invoiceDate, entrySource: input.entrySource,
      irn: input.irn, irnSignature: input.irnSignature, imageHash: input.imageHash, imageDataUrl: input.imageDataUrl, attachmentName: input.attachmentName,
      noImageReason: input.imageDataUrl || input.attachmentName ? undefined : input.noImageReason,
      fileId: input.fileId, filePath: input.filePath, narration: input.narration?.trim() || undefined,
      costCentreId: input.costCentreId && client.costCentres.some((c) => c.id === input.costCentreId && c.active) ? input.costCentreId : undefined,
      description: input.description, hsnSac: input.hsnSac, grossAmount: input.grossAmount, discount: input.discount,
      taxableValue: input.taxableValue, cgst: input.cgst, sgst: input.sgst, igst: input.igst, totalAmount: input.totalAmount,
      headId: h.headId, headConfidence: h.confidence, tdsCode: tds.code, tdsRatePct: tds.ratePct, tdsAmount: tds.amount,
      // 9(5): the operator already paid the GST — the buyer never self-assesses RCM on it
      rcmApplicable: rcm.applicable && !input.ecoPaysTax, rcmCode: input.ecoPaysTax ? undefined : rcm.code, rcmRatePct: input.ecoPaysTax ? undefined : rcm.ratePct,
      nonTaxableAmount: input.nonTaxableAmount ? round2(input.nonTaxableAmount) : undefined, ecoPaysTax: input.ecoPaysTax || undefined, ecoGstin: input.ecoPaysTax ? input.ecoGstin : undefined,
      rcmTax: rcm.applicable && !input.ecoPaysTax && rcm.ratePct ? round2((input.taxableValue * rcm.ratePct) / 100) : 0,
      itcEligible: itc.eligible, blockedCode: itc.blockedCode,
      status: 'submitted', isBackdated: backdated, createdBy: editing?.createdBy ?? me.id, createdAt: editing?.createdAt ?? nowIso(),
      resubmittedAt: editing?.status === 'rejected' ? nowIso() : undefined, notDuplicateOf: input.notDuplicateOf
    };
    // auto-approval (only if the CA firm switched it on for this client): every condition must hold, else the bill waits
    const flagsOnBill = riskCheck([...others, e], base.vendors.filter((v) => v.clientId === client.id), client, base.tdsRates).filter((f) => f.expenseId === e.id).length;
    const auto = autoApproveDecision(e, client, others, flagsOnBill);
    if (auto.approve && !isLocked(client.id, e.invoiceDate)) Object.assign(e, auto.patch, { status: 'approved', autoApproved: true, reviewedAt: nowIso() });
    else if (auto.sampled) e.sampleCheck = true;
    const paidNow = round2((input.payments ?? []).reduce((x, p) => x + p.amount, 0));
    const alreadyPaid = editing ? round2(netPayable(editing) - outstanding(editing, base.payments)) : 0;
    if (paidNow + alreadyPaid > round2(e.totalAmount - e.tdsAmount) + 0.01) {
      throw new RuleError('Paid amount is more than the bill (after TDS: ₹{net})', { net: round2(e.totalAmount - e.tdsAmount) });
    }
    return { e, newVendor, backdated };
  }

  const addExpense = useCallback((input: NewExpenseInput): Expense => {
    const { e, newVendor, backdated } = prepare(input);
    setS((st) => {
      let next: State = {
        ...st,
        vendors: newVendor ? [...st.vendors.filter((v) => v.id !== newVendor.id), newVendor] : st.vendors,
        expenses: [e, ...st.expenses]
      };
      next.audit = audit(next, { clientId: e.clientId, table: 'expenses', rowId: e.id, action: 'INSERT',
        flag: backdated ? 'backdated_expense' : e.noImageReason ? 'no_bill_image' : undefined,
        summary: `${e.vendorName} ${e.invoiceNo ?? ''} ₹${e.totalAmount}${e.noImageReason ? ` — no image: ${e.noImageReason}` : ''}` });
      if (e.autoApproved) next.audit = audit(next, { clientId: e.clientId, table: 'expenses', rowId: e.id, action: 'AUTO_APPROVED', flag: 'auto_approved',
        summary: `${e.vendorName} ${e.invoiceNo ?? ''} ₹${e.totalAmount} — meets every auto-approval condition` });
      for (const pl of input.payments ?? []) {
        const p = makePayment(next, { ...pl, vendorId: e.vendorId!, allocations: [{ expenseId: e.id, amount: pl.amount }] }, e.vendorName, [e.invoiceDate]);
        next = { ...next, payments: [p, ...next.payments] };
        next.audit = audit(next, { clientId: e.clientId, table: 'payments', rowId: p.id, action: 'INSERT',
          flag: p.flags?.[0], summary: `${p.mode} ₹${p.amount} on ${p.paidOn} — ${e.vendorName}` });
      }
      return next;
    });
    return e;
  }, [me, client, s.vendors, s.expenses, s.heads, s.tdsRates, isLocked, findDuplicate]); // eslint-disable-line react-hooks/exhaustive-deps

  /** Fix & resubmit an entry the CA returned, or complete a draft from the bulk-upload inbox. */
  const completeExpense = useCallback((id: string, input: NewExpenseInput) => {
    const old = s.expenses.find((x) => x.id === id);
    if (!old) throw new RuleError('Entry not found');
    if (old.status !== 'rejected' && old.status !== 'draft') throw new RuleError('Only returned or draft entries can be edited here');
    if (me?.role === 'sub_user' && old.createdBy !== me.id) throw new RuleError('You can only fix your own entries');
    const { e, newVendor } = prepare(input, old);
    setS((st) => {
      let next: State = {
        ...st,
        vendors: newVendor ? [...st.vendors.filter((v) => v.id !== newVendor.id), newVendor] : st.vendors,
        expenses: st.expenses.map((x) => (x.id === id ? { ...e, reviewNote: old.reviewNote } : x))
      };
      next.audit = audit(next, { clientId: e.clientId, table: 'expenses', rowId: id, action: old.status === 'draft' ? 'SUBMIT_DRAFT' : 'RESUBMIT', summary: `${e.vendorName} ${e.invoiceNo ?? ''} ₹${e.totalAmount}` });
      for (const pl of input.payments ?? []) {
        const p = makePayment(next, { ...pl, vendorId: e.vendorId!, allocations: [{ expenseId: e.id, amount: pl.amount }] }, e.vendorName, [e.invoiceDate]);
        next = { ...next, payments: [p, ...next.payments] };
        next.audit = audit(next, { clientId: e.clientId, table: 'payments', rowId: p.id, action: 'INSERT', flag: p.flags?.[0], summary: `${p.mode} ₹${p.amount} on ${p.paidOn} — ${e.vendorName}` });
      }
      return next;
    });
  }, [me, s.expenses, s.vendors, s.payments, s.heads, s.tdsRates, isLocked, findDuplicate]); // eslint-disable-line react-hooks/exhaustive-deps

  /** Bulk upload: each file becomes a draft pre-filled with whatever could be read; staff/admin complete them from the Inbox. */
  const addDrafts = useCallback((items: { viaWhatsapp?: boolean; fileName: string; imageDataUrl?: string; imageHash?: string; fileId?: string; filePath?: string; vendorName?: string; vendorGstin?: string; invoiceNo?: string; invoiceDate?: string; totalAmount?: number; hsnSac?: string; nonTaxable?: number; ecoPaysTax?: boolean; ecoGstin?: string }[]) => {
    if (!me || !client) throw new RuleError('Not signed in');
    const seen = new Set(s.expenses.filter((e) => e.clientId === client.id && e.imageHash).map((e) => e.imageHash));
    // skip files already recorded AND repeats inside the same upload batch
    const fresh = items.filter((it) => {
      if (!it.imageHash) return true;
      if (seen.has(it.imageHash)) return false;
      seen.add(it.imageHash);
      return true;
    });
    const drafts: Expense[] = fresh.map((it) => {
      const date = it.invoiceDate && it.invoiceDate <= todayIso() ? it.invoiceDate : todayIso();
      return {
        id: uid(), clientId: client.id, fyLabel: fyLabel(date), vendorName: it.vendorName ?? '', invoiceNo: it.invoiceNo, invoiceDate: date,
        entrySource: it.viaWhatsapp ? 'whatsapp' : it.imageDataUrl ? 'photo' : 'pdf', imageHash: it.imageHash, imageDataUrl: it.imageDataUrl, attachmentName: it.imageDataUrl ? undefined : it.fileName,
        fileId: it.fileId, filePath: it.filePath,
        description: it.vendorGstin ? `GSTIN ${it.vendorGstin}` : undefined, hsnSac: it.hsnSac, grossAmount: it.totalAmount ?? 0, discount: 0,
        taxableValue: it.totalAmount ?? 0, cgst: 0, sgst: 0, igst: 0, totalAmount: it.totalAmount ?? 0, tdsAmount: 0, rcmApplicable: false, rcmTax: 0,
        nonTaxableAmount: it.nonTaxable, ecoPaysTax: it.ecoPaysTax, ecoGstin: it.ecoGstin,
        status: 'draft', isBackdated: false, createdBy: me.id, createdAt: nowIso()
      };
    });
    setS((st) => {
      const next = { ...st, expenses: [...drafts, ...st.expenses] };
      next.audit = audit(next, { clientId: client.id, table: 'expenses', action: 'BULK_UPLOAD', summary: `${drafts.length} file(s) to inbox${items.length - drafts.length ? `, ${items.length - drafts.length} duplicate photo(s) skipped` : ''}` });
      return next;
    });
    return { added: drafts.length, skipped: items.length - drafts.length };
  }, [me, client, s.expenses]);

  const deleteDraft = useCallback((id: string) => {
    setS((st) => ({ ...st, expenses: st.expenses.filter((e) => !(e.id === id && e.status === 'draft')) }));
  }, []);

  /** Pay one or many bills of a vendor in one go (Zoho "Payments made" / QuickBooks "Pay bills"). Extra = advance. */
  const recordPayment = useCallback((input: RecordPaymentInput): Payment => {
    if (!me || !client) throw new RuleError('Not signed in');
    const today = todayIso();
    const vendor = s.vendors.find((v) => v.id === input.vendorId);
    if (!vendor) throw new RuleError('Choose the vendor');
    if (!(input.amount > 0)) throw new RuleError('Enter the amount paid');
    if (input.paidOn > today) throw new RuleError('Payment date cannot be in the future');
    if (isLocked(client.id, input.paidOn)) throw new RuleError('Payment date falls in a locked month');
    if (needsSource(client, input.mode) && !input.accountId) throw new RuleError('Choose where the money was paid from');
    const allocTotal = round2(input.allocations.reduce((x, a) => x + a.amount, 0));
    if (allocTotal > input.amount + 0.01) throw new RuleError('Amounts applied to bills are more than the payment');
    const dates: string[] = [];
    for (const a of input.allocations) {
      if (a.amount < 0) throw new RuleError('Amounts cannot be negative');
      if (!a.amount) continue;
      const e = s.expenses.find((x) => x.id === a.expenseId);
      if (!e || e.vendorId !== vendor.id) throw new RuleError('A selected bill belongs to another vendor');
      if (e.status === 'rejected' || e.status === 'draft') throw new RuleError('Bill {no} is not active — fix it first', { no: e.invoiceNo ?? '' });
      const due = outstanding(e, s.payments);
      if (a.amount > due + 0.01) throw new RuleError('More than the balance of bill {no} (₹{due})', { no: e.invoiceNo ?? '', due });
      dates.push(e.invoiceDate);
    }
    const made = makePayment(s, input, vendor.name, dates);
    if (input.tdsOnAdvance) {
      const adv = unallocated(made);
      if (adv <= 0) throw new RuleError('TDS on advance applies only to the part not applied to bills');
      const r = s.tdsRates.find((x) => x.code === input.tdsOnAdvance!.code);
      if (!r) throw new RuleError('This TDS section is not in the tax masters.');
      const ratePct = (!vendor.pan || vendor.panStatus === 'Inoperative') && r.noPanRatePct ? r.noPanRatePct : r.ratePct;
      const amount = grossUpTds(adv, ratePct);
      made.tdsOnAdvance = { code: r.code, ratePct, amount, base: round2(adv + amount) };
    }
    setS((st) => {
      const next = { ...st, payments: [made, ...st.payments] };
      const adv = unallocated(made);
      next.audit = audit(next, { clientId: client.id, table: 'payments', rowId: made.id, action: 'INSERT', flag: made.flags?.[0],
        summary: `${made.mode} ₹${made.amount} on ${made.paidOn} — ${vendor.name}: ${made.allocations.length} bill(s)${adv > 0 ? `, advance ₹${adv}` : ''}${made.tdsOnAdvance ? ` + TDS ₹${made.tdsOnAdvance.amount} (${made.tdsOnAdvance.code})` : ''}${made.source === 'bank_import' ? ' (bank import)' : ''}` });
      return next;
    });
    return made;
  }, [me, client, s.vendors, s.expenses, s.payments, isLocked]); // eslint-disable-line react-hooks/exhaustive-deps

  /** Apply an existing advance (unallocated part of a payment) to a bill of the same vendor. */
  const applyAdvance = useCallback((paymentId: string, expenseId: string, amount: number) => {
    const p = s.payments.find((x) => x.id === paymentId);
    const e = s.expenses.find((x) => x.id === expenseId);
    if (!p || !e || p.vendorId !== e.vendorId) throw new RuleError('Advance and bill must be for the same vendor');
    if (amount <= 0 || amount > unallocated(p) + 0.01) throw new RuleError('Only ₹{left} of this advance is left', { left: unallocated(p) });
    if (p.tdsOnAdvance && e.postedAt && e.tdsAmount > 0) throw new RuleError('This bill is already in Tally with its own TDS — the CA must adjust the advance TDS in Tally');
    if (previewApply(e, s.payments, p, amount).after < -0.01) throw new RuleError('More than the bill balance');
    setS((st) => {
      // TDS credit from the latest state, so applying one advance to several bills in a row never reuses the same TDS
      const fresh = st.payments.find((x) => x.id === paymentId) ?? p;
      const { credit } = previewApply(e, st.payments, fresh, amount);
      const alloc: Allocation = { expenseId, amount: round2(amount), ...(credit > 0 ? { tdsCredit: credit } : {}) };
      // TDS deducted on the advance under another section than the bill's: the credit is carried (no double deduction),
      // but it is marked for the CA — the rate and the return entry may need correcting.
      const differs = credit > 0 && !!e.tdsCode && fresh.tdsOnAdvance?.code !== e.tdsCode;
      const next = { ...st, payments: st.payments.map((x) => (x.id === paymentId ? { ...x, allocations: [...x.allocations, alloc], ...(differs ? { flags: [...new Set([...(x.flags ?? []), 'adv_tds_section_differs'])] } : {}) } : x)) };
      next.audit = audit(next, { clientId: e.clientId, table: 'payments', rowId: paymentId, action: 'APPLY_ADVANCE', summary: `₹${amount} to ${e.vendorName} ${e.invoiceNo ?? ''}${credit > 0 ? ` (TDS already deducted ₹${credit})` : ''}` });
      return next;
    });
  }, [s.payments, s.expenses]);

  /** Reverse a wrongly entered payment (admins only, and only before it is posted to Tally). */
  /** Credit / debit note from a vendor. Admins only; the bill's balance and the ITC follow the note (lib/vendorNotes.ts). */
  const saveVendorNote = useCallback((input: Omit<VendorNote, 'id' | 'clientId' | 'fyLabel' | 'vendorName' | 'itcEligible' | 'status' | 'createdBy' | 'createdAt' | 'flags'> & { itcEligible?: boolean }) => {
    if (!me || me.role === 'sub_user') throw new RuleError('Only admins can record credit / debit notes');
    if (!client) throw new RuleError('Choose a client');
    const vendor = s.vendors.find((v) => v.id === input.vendorId && v.clientId === client.id);
    if (!vendor) throw new RuleError('Vendor not found');
    if (isLocked(client.id, input.noteDate)) throw new RuleError('This month is locked. Ask your admin.');
    if (input.noteDate > todayIso()) throw new RuleError('Date cannot be in the future');
    const bill = input.expenseId ? s.expenses.find((e) => e.id === input.expenseId) : undefined;
    if (input.expenseId && (!bill || bill.status === 'rejected' || bill.status === 'draft')) throw new RuleError('Choose an active bill');
    const draft = { ...input, noteNo: input.noteNo.trim(), clientId: client.id, fyLabel: fyLabel(input.noteDate), vendorName: vendor.name,
      // ITC follows the bill it corrects; for a vendor-level note the admin says whether the ITC was claimed
      itcEligible: bill ? bill.itcEligible === true : input.itcEligible === true,
      taxableValue: round2(input.taxableValue), cgst: round2(input.cgst), sgst: round2(input.sgst), igst: round2(input.igst), totalAmount: round2(input.totalAmount) };
    if (!bill && !input.headId) throw new RuleError('Choose an expense head');
    const chk = checkNote(draft, bill, s.vendorNotes.filter((x) => x.expenseId && x.expenseId === bill?.id), s.vendorNotes.filter((x) => x.clientId === client.id));
    if (chk.errors.length) throw new RuleError(chk.errors[0], chk.vars);
    const note: VendorNote = { ...draft, id: uid(), status: 'active', flags: chk.flags.length ? chk.flags : undefined, createdBy: me.id, createdAt: nowIso() };
    setS((st) => {
      const notes = [...st.vendorNotes, note];
      const next = { ...st, vendorNotes: notes, expenses: bill ? st.expenses.map((e) => (e.id === bill.id ? { ...e, noteAdjust: noteAdjustFor(e.id, notes) } : e)) : st.expenses };
      next.audit = audit(next, { clientId: client.id, table: 'vendor_notes', rowId: note.id, action: note.kind === 'credit' ? 'CREDIT_NOTE' : 'DEBIT_NOTE',
        summary: `${vendor.name} ${note.noteNo} ₹${note.totalAmount}${bill ? ` on bill ${bill.invoiceNo ?? ''}` : ' (vendor level)'}` });
      return next;
    });
    return note;
  }, [me, client, s.vendors, s.expenses, s.vendorNotes, isLocked]);

  /** Link a vendor-level note to the bill it corrects. */
  const linkVendorNote = useCallback((noteId: string, expenseId: string) => {
    if (!me || me.role === 'sub_user') throw new RuleError('Only admins can record credit / debit notes');
    const n = s.vendorNotes.find((x) => x.id === noteId);
    const bill = s.expenses.find((e) => e.id === expenseId);
    if (!n || n.status === 'void' || n.expenseId) throw new RuleError('Note not found');
    if (!bill || bill.status === 'rejected' || bill.status === 'draft') throw new RuleError('Choose an active bill');
    if (n.postedAt) throw new RuleError('Already posted to Tally — reverse it in Tally and ask the CA');
    const chk = checkNote({ ...n, expenseId }, bill, s.vendorNotes.filter((x) => x.expenseId === bill.id), s.vendorNotes.filter((x) => x.id !== n.id && x.clientId === n.clientId));
    if (chk.errors.length) throw new RuleError(chk.errors[0], chk.vars);
    setS((st) => {
      const notes = st.vendorNotes.map((x) => (x.id === noteId ? { ...x, expenseId, itcEligible: bill.itcEligible === true, flags: chk.flags.length ? chk.flags : undefined } : x));
      const next = { ...st, vendorNotes: notes, expenses: st.expenses.map((e) => (e.id === expenseId ? { ...e, noteAdjust: noteAdjustFor(e.id, notes) } : e)) };
      next.audit = audit(next, { clientId: n.clientId, table: 'vendor_notes', rowId: noteId, action: 'NOTE_LINKED', summary: `${n.vendorName} ${n.noteNo} → bill ${bill.invoiceNo ?? ''}` });
      return next;
    });
  }, [me, s.vendorNotes, s.expenses]);

  /** Cancel a wrongly entered note (admins, before Tally posting). Kept in the audit trail. */
  const voidVendorNote = useCallback((noteId: string, reason: string) => {
    if (!me || me.role === 'sub_user') throw new RuleError('Only admins can record credit / debit notes');
    const n = s.vendorNotes.find((x) => x.id === noteId);
    if (!n || n.status === 'void') throw new RuleError('Note not found');
    if (n.postedAt) throw new RuleError('Already posted to Tally — reverse it in Tally and ask the CA');
    if (reason.trim().length < 3) throw new RuleError('Give a reason');
    setS((st) => {
      const notes = st.vendorNotes.map((x) => (x.id === noteId ? { ...x, status: 'void' as const, voidReason: reason.trim() } : x));
      const next = { ...st, vendorNotes: notes, expenses: n.expenseId ? st.expenses.map((e) => (e.id === n.expenseId ? { ...e, noteAdjust: noteAdjustFor(e.id, notes) } : e)) : st.expenses };
      next.audit = audit(next, { clientId: n.clientId, table: 'vendor_notes', rowId: noteId, action: 'VOID', summary: `${n.vendorName} ${n.noteNo}: ${reason.trim()}` });
      return next;
    });
  }, [me, s.vendorNotes]);

  /** CA records the 180-day ITC reversal shown in GST registers (return period it was reversed in). */
  const recordItcReversal = useCallback((expenseId: string, amount: number, month: string) => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can record ITC reversals');
    const e = s.expenses.find((x) => x.id === expenseId);
    if (!e) throw new RuleError('Entry not found');
    if (!(amount > 0)) throw new RuleError('Enter the amount reversed');
    if (!/^\d{4}-\d{2}$/.test(month)) throw new RuleError('Choose the return period');
    if (s.itcReversals.some((r) => r.expenseId === expenseId)) throw new RuleError('Already recorded for this bill');
    const rec: ItcReversal = { id: uid(), clientId: e.clientId, expenseId, amount: round2(amount), reversedIn: month, by: me.id, at: nowIso() };
    setS((st) => {
      const next = { ...st, itcReversals: [...st.itcReversals, rec] };
      next.audit = audit(next, { clientId: e.clientId, table: 'itc_reversals', rowId: rec.id, action: 'ITC_REVERSED', summary: `${e.vendorName} ${e.invoiceNo ?? ''}: ₹${rec.amount} in ${month}` });
      return next;
    });
  }, [me, s.expenses, s.itcReversals]);

  /** CA records the re-claim of reversed ITC after the bill was paid. */
  const recordItcReclaim = useCallback((id: string, amount: number, month: string) => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can record ITC reversals');
    const r = s.itcReversals.find((x) => x.id === id);
    if (!r) throw new RuleError('Entry not found');
    if (!(amount > 0) || amount > r.amount - (r.reclaimedAmount ?? 0) + 0.01) throw new RuleError('Re-claim cannot be more than what was reversed');
    if (!/^\d{4}-\d{2}$/.test(month) || month < r.reversedIn) throw new RuleError('Choose the return period');
    setS((st) => {
      const next = { ...st, itcReversals: st.itcReversals.map((x) => (x.id === id ? { ...x, reclaimedAmount: round2((x.reclaimedAmount ?? 0) + amount), reclaimedIn: month } : x)) };
      next.audit = audit(next, { clientId: r.clientId, table: 'itc_reversals', rowId: id, action: 'ITC_RECLAIMED', summary: `₹${round2(amount)} in ${month}` });
      return next;
    });
  }, [me, s.itcReversals]);

  /** CA firm: assign bills in the review queue to a reviewer (or unassign with undefined). */
  const assignReview = useCallback((expenseIds: string[], userId?: string) => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can approve entries');
    if (userId && !s.users.some((u) => u.id === userId && u.role === 'super_admin' && u.active !== false)) throw new RuleError('User not found');
    setS((st) => ({ ...st, expenses: st.expenses.map((e) => (expenseIds.includes(e.id) && e.status === 'submitted' ? { ...e, assignedTo: userId } : e)) }));
  }, [me, s.users]);

  const voidPayment = useCallback((id: string, reason: string) => {
    if (!me || me.role === 'sub_user') throw new RuleError('Only admins can cancel a payment');
    const p = s.payments.find((x) => x.id === id);
    if (!p) throw new RuleError('Payment not found');
    if (p.postedAt) throw new RuleError('Already posted to Tally — reverse it in Tally and ask the CA');
    if (reason.trim().length < 3) throw new RuleError('Give a reason');
    setS((st) => {
      const next = { ...st, payments: st.payments.filter((x) => x.id !== id) };
      next.audit = audit(next, { clientId: p.clientId, table: 'payments', rowId: id, action: 'VOID', flag: 'payment_voided', summary: `${p.mode} ₹${p.amount} on ${p.paidOn} — ${p.vendorName}: ${reason}` });
      return next;
    });
  }, [me, s.payments]);

  const reviewExpense = useCallback((id: string, patch: Partial<Expense>, status: 'approved' | 'rejected') => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can approve entries');
    const cur = s.expenses.find((x) => x.id === id);
    if (!cur) throw new RuleError('Entry not found');
    if (isLocked(cur.clientId, cur.invoiceDate)) throw new RuleError('Month is locked — unlock it in client settings first');
    const merged = { ...cur, ...patch };
    if (status === 'approved') {
      const diff = round2(merged.totalAmount - merged.taxableValue - (merged.nonTaxableAmount ?? 0) - merged.cgst - merged.sgst - merged.igst);
      if (Math.abs(diff) > ROUND_OFF_LIMIT) throw new RuleError(diff < 0 ? 'Taxable + non-GST charges + GST is more than the bill total by {amt} — correct before approving' : 'Taxable + non-GST charges + GST is less than the bill total by {amt} — correct before approving', { amt: fmtInr(Math.abs(diff)) });
      if (!merged.headId) throw new RuleError('Choose an expense head');
      if (merged.rcmApplicable && !(merged.rcmRatePct && merged.rcmTax > 0)) throw new RuleError('Enter the RCM GST rate');
    }
    setS((st) => {
      let payments = st.payments;
      let moved = 0;
      // returned bill → its payments become vendor advances; approved with a lower net (e.g. TDS added) → excess becomes advance
      const limit = status === 'rejected' ? 0 : round2(merged.totalAmount - merged.tdsAmount);
      let paid = round2(payments.reduce((x, p) => x + p.allocations.filter((a) => a.expenseId === id).reduce((y, a) => y + a.amount, 0), 0));
      if (paid > limit + 0.01) {
        payments = [...payments].sort((a, b) => b.paidOn.localeCompare(a.paidOn)).map((p) => {
          if (paid <= limit + 0.01) return p;
          return { ...p, allocations: p.allocations.flatMap((a) => {
            if (a.expenseId !== id || paid <= limit + 0.01) return [a];
            const cut = round2(Math.min(a.amount, paid - limit));
            paid = round2(paid - cut); moved = round2(moved + cut);
            return a.amount - cut > 0.009 ? [{ ...a, amount: round2(a.amount - cut) }] : [];
          }) };
        });
      }
      // a person's decision replaces the rule's: an auto-approved bill re-decided by the CA is no longer marked auto
      const next = { ...st, payments, expenses: st.expenses.map((e) => (e.id === id ? { ...merged, status, reviewedAt: nowIso(), autoApproved: undefined, sampleCheck: undefined } : e)) };
      next.audit = audit(next, { clientId: cur.clientId, table: 'expenses', rowId: id, action: status.toUpperCase(),
        flag: moved ? 'payment_moved_to_advance' : undefined,
        summary: `${cur.vendorName} ${cur.invoiceNo ?? ''}${patch.reviewNote ? ' — ' + patch.reviewNote : ''}${moved ? ` — ₹${moved} of payments moved to vendor advance` : ''}` });
      return next;
    });
  }, [me, s.expenses, isLocked]);

  const markPosted = useCallback((expenseIds: string[], paymentIds: string[], noteIds: string[] = []) => {
    const at = nowIso();
    setS((st) => {
      const next = {
        ...st,
        expenses: st.expenses.map((e) => (expenseIds.includes(e.id) ? { ...e, status: 'posted' as const, postedAt: at } : e)),
        payments: st.payments.map((p) => (paymentIds.includes(p.id) ? { ...p, postedAt: at } : p)),
        vendorNotes: st.vendorNotes.map((n) => (noteIds.includes(n.id) ? { ...n, postedAt: at } : n))
      };
      next.audit = audit(next, { clientId, table: 'expenses', action: 'POSTED_TO_TALLY', summary: `${expenseIds.length} journals + ${paymentIds.length} payments + ${noteIds.length} notes confirmed imported` });
      next.events = [{ id: uid(), level: 'info', component: 'tally_export', clientId, message: 'Tally import confirmed: {e} journals, {p} payments, {n} notes', vars: { e: expenseIds.length, p: paymentIds.length, n: noteIds.length }, at }, ...st.events];
      return next;
    });
  }, [clientId]);

  const toggleLock = useCallback((month: string) => {
    if (!me || !clientId) return;
    const locked = s.monthLocks.some((l) => l.clientId === clientId && l.month === month);
    if (locked && me.role !== 'super_admin') throw new RuleError('Only the CA firm can unlock a month');
    if (!locked && me.role === 'sub_user') throw new RuleError('Only admins can lock months');
    setS((st) => {
      const next = {
        ...st,
        monthLocks: locked ? st.monthLocks.filter((l) => !(l.clientId === clientId && l.month === month)) : [...st.monthLocks, { clientId, month }]
      };
      next.audit = audit(next, { clientId, table: 'month_locks', action: locked ? 'UNLOCK' : 'LOCK', summary: month });
      return next;
    });
  }, [me, clientId, s.monthLocks]);

  /** CA firm closes a financial year: blockers must be zero, warnings acknowledged; all 12 months are locked. */
  const closeFy = useCallback((fy: string, acknowledged: string[]) => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can close a financial year');
    if (!client) throw new RuleError('Choose a client');
    if (fyEnd(fy) >= todayIso()) throw new RuleError('The financial year has not ended yet');
    if ((s.fyCloses ?? []).some((c) => c.clientId === client.id && c.fy === fy)) throw new RuleError('This financial year is already closed');
    const d = { client, expenses: s.expenses.filter((e) => e.clientId === client.id), payments: s.payments.filter((p) => p.clientId === client.id),
      challans: s.challans.filter((c) => c.clientId === client.id), itcReversals: (s.itcReversals ?? []).filter((r) => r.clientId === client.id) };
    const checks = fyChecklist(fy, d, todayIso());
    const block = checks.find((c) => c.blocker && c.count > 0);
    if (block) throw new RuleError(block.label, { n: block.count });
    const warn = checks.filter((c) => !c.blocker && c.count > 0).map((c) => c.key);
    if (warn.some((k) => !acknowledged.includes(k))) throw new RuleError('Tick each warning to confirm you have seen it');
    const carry = carryForward(fy, { ...d, vendorNotes: (s.vendorNotes ?? []).filter((n) => n.clientId === client.id) });
    const sum = (k: string) => round2(carry.filter((c) => c.kind === k).reduce((x, c) => x + c.amount, 0));
    const rec: FyClose = { clientId: client.id, fy, closedBy: me.id, at: nowIso(), warningsAcknowledged: warn,
      carry: { openBills: sum('open_bill'), advances: sum('advance'), advanceTds: sum('advance_tds'), notes: sum('vendor_note') } };
    setS((st) => {
      const have = new Set(st.monthLocks.filter((l) => l.clientId === client.id).map((l) => l.month));
      const next = { ...st, fyCloses: [...(st.fyCloses ?? []), rec], monthLocks: [...st.monthLocks, ...fyMonths(fy).filter((m) => !have.has(m)).map((month) => ({ clientId: client.id, month }))] };
      next.audit = audit(next, { clientId: client.id, table: 'fiscal_years', action: 'FY_CLOSED',
        summary: `FY ${fy} closed; open bills ₹${rec.carry.openBills}, advances ₹${rec.carry.advances}${warn.length ? `; warnings seen: ${warn.join(', ')}` : ''}` });
      return next;
    });
  }, [me, client, s.expenses, s.payments, s.challans, s.itcReversals, s.fyCloses, s.vendorNotes]);

  const saveVendor = useCallback((v: Vendor) => {
    // PAN / GSTIN verification status drives the TDS rate and ITC — set only by the CA firm or the verification API
    const prev = s.vendors.find((x) => x.id === v.id);
    if (me?.role !== 'super_admin' && ((prev?.panStatus ?? 'Unverified') !== (v.panStatus ?? 'Unverified') || (prev?.gstinStatus ?? '') !== (v.gstinStatus ?? ''))) {
      throw new RuleError('Only the CA firm can set PAN / GSTIN verification status');
    }
    if (v.gstin && s.vendors.some((x) => x.clientId === v.clientId && x.id !== v.id && x.gstin === v.gstin)) {
      throw new RuleError('Another vendor already has this GSTIN');
    }
    if (s.vendors.some((x) => x.clientId === v.clientId && x.id !== v.id && x.name.trim().toLowerCase() === v.name.trim().toLowerCase())) {
      throw new RuleError('A vendor with this name already exists');
    }
    setS((st) => {
      const before = st.vendors.find((x) => x.id === v.id);
      const renamed = before && before.name !== v.name;
      const next = {
        ...st,
        vendors: before ? st.vendors.map((x) => (x.id === v.id ? v : x)) : [...st.vendors, v],
        // keep unposted entries in step with the master (posted ones already carry the old ledger name in Tally)
        expenses: renamed ? st.expenses.map((e) => (e.vendorId === v.id && e.status !== 'posted' ? { ...e, vendorName: v.name } : e)) : st.expenses
      };
      next.audit = audit(next, { clientId: v.clientId, table: 'vendors', rowId: v.id, action: before ? 'UPDATE' : 'INSERT',
        summary: renamed ? `${before!.name} → ${v.name}` : `${v.name}${v.panStatus ? ` · PAN ${v.panStatus}` : ''}` });
      return next;
    });
  }, [s.vendors, me]);

  /** Bulk Excel import (admins). Every row is checked against the rows above it in the same file;
   *  `commit: false` is a dry run for the preview screen. Rows that fail are skipped, never half-saved. */
  const importData = useCallback((kind: ImportKind, rows: ImportRow[], commit: boolean): ImportRowResult[] => {
    if (!me || !client || me.role === 'sub_user') throw new RuleError('Only admins can import');
    const today = todayIso();
    let work: State = s;
    let cl: Client = client;
    const added = { vendors: new Map<string, Vendor>(), expenses: [] as Expense[], payments: [] as Payment[] };
    const results: ImportRowResult[] = [];
    const txt = (v: ImportRow[string]) => (v === undefined ? '' : String(v).trim());
    const amt = (v: ImportRow[string]) => (typeof v === 'number' ? round2(v) : undefined);
    const same = (a: string, b?: string) => a.trim().toLowerCase() === (b ?? '').trim().toLowerCase();
    const mine = (st: State) => st.vendors.filter((v) => v.clientId === cl.id);
    const isoDate = /^\d{4}-\d{2}-\d{2}$/;

    rows.forEach((r, i) => {
      const row = typeof r._row === 'number' ? r._row : i + 2; // spreadsheet row number (row 1 holds the headings)
      let label = txt(r.name) || txt(r.vendor) || `#${row}`;
      try {
        if (kind === 'vendors') {
          const name = txt(r.name);
          if (name.length < 2) throw new RuleError('Enter the vendor name');
          const gstin = txt(r.gstin).toUpperCase().replace(/\s/g, '');
          const g = gstin ? checkGstin(gstin) : undefined;
          if (g && !g.ok) throw new RuleError(g.reason ?? 'GSTIN format is not valid');
          const pan = txt(r.pan).toUpperCase() || g?.pan || '';
          const p = pan ? checkPan(pan) : undefined;
          if (p && !p.ok) throw new RuleError(p.reason ?? 'PAN format is not valid (e.g. ABCPE1234F)');
          if (g?.pan && pan !== g.pan) throw new RuleError('PAN does not match the PAN inside the GSTIN');
          if (mine(work).some((v) => same(v.name, name))) throw new RuleError('Already in your vendor list — skipped');
          if (gstin && mine(work).some((v) => v.gstin === gstin)) throw new RuleError('Another vendor already has this GSTIN');
          const days = r.creditDays;
          if (days !== undefined && !(typeof days === 'number' && Number.isInteger(days) && days >= 0 && days <= 365)) throw new RuleError('Credit days must be a whole number from 0 to 365');
          const v: Vendor = {
            id: uid(), clientId: cl.id, name, gstin: gstin || undefined, gstRegistered: !!gstin, pan: pan || undefined,
            panEntityType: p?.entityType, panStatus: 'Unverified', stateCode: g?.stateCode, creditDays: days as number | undefined,
            tallyLedger: txt(r.tallyLedger) || undefined
          };
          added.vendors.set(v.id, v);
          work = { ...work, vendors: [...work.vendors, v] };
        } else if (kind === 'bills') {
          const vendorName = txt(r.vendor);
          const gstin = txt(r.gstin).toUpperCase().replace(/\s/g, '');
          if (gstin) { const g = checkGstin(gstin); if (!g.ok) throw new RuleError(g.reason ?? 'GSTIN format is not valid'); }
          const invoiceDate = txt(r.invoiceDate);
          if (!isoDate.test(invoiceDate)) throw new RuleError('Enter the bill date (dd-mm-yyyy)');
          const taxable = amt(r.taxable);
          if (!(taxable && taxable > 0)) throw new RuleError('Enter the taxable value');
          const [cgst, sgst, igst, discount] = [amt(r.cgst) ?? 0, amt(r.sgst) ?? 0, amt(r.igst) ?? 0, amt(r.discount) ?? 0];
          if ([cgst, sgst, igst, discount].some((x) => x < 0)) throw new RuleError('Amounts cannot be negative');
          if ((cgst || sgst) && igst) throw new RuleError('Use either CGST + SGST or IGST, not both');
          if (Math.abs(cgst - sgst) > 1) throw new RuleError('CGST and SGST should be equal');
          const nonTax = amt(r.nonTaxable) ?? 0;
          if (nonTax < 0) throw new RuleError('Amounts cannot be negative');
          const eco = /^(y|yes|haan|हाँ|true|1)$/i.test(txt(r.eco));
          const ecoGstin = txt(r.ecoGstin).toUpperCase().replace(/\s/g, '');
          if (ecoGstin && !checkGstin(ecoGstin).ok) throw new RuleError('GSTIN of the app / operator is not valid');
          const computed = round2(taxable + cgst + sgst + igst + nonTax);
          const given = amt(r.total);
          if (given !== undefined && Math.abs(given - computed) > ROUND_OFF_LIMIT) throw new RuleError('Total does not match taxable value + GST + non-GST charges (difference ₹{diff})', { diff: round2(given - computed) });
          const hsn = txt(r.hsn).replace(/\s/g, '');
          if (hsn && !/^\d{4,8}$/.test(hsn)) throw new RuleError('HSN / SAC should be 4 to 8 digits');
          const centreName = txt(r.centre);
          const centre = centreName ? cl.costCentres.find((c) => c.active && same(c.name, centreName)) : undefined;
          if (centreName && !centre) throw new RuleError('Project / branch "{name}" not found — add it first', { name: centreName });
          const { e, newVendor } = prepare({
            vendorName, vendorGstin: gstin || undefined, invoiceNo: txt(r.invoiceNo) || undefined, invoiceDate, entrySource: 'manual',
            noImageReason: NO_IMAGE_REASONS.find((x) => x.code === 'imported')!.en, description: txt(r.description) || undefined,
            hsnSac: hsn || undefined, grossAmount: round2(taxable + discount), discount, taxableValue: taxable, cgst, sgst, igst,
            totalAmount: given ?? computed, costCentreId: centre?.id, narration: txt(r.narration) || undefined,
            nonTaxableAmount: nonTax || undefined, ecoPaysTax: eco || undefined, ecoGstin: ecoGstin || undefined
          }, undefined, work);
          label = `${e.vendorName} ${e.invoiceNo ?? ''} ₹${e.totalAmount}`;
          if (newVendor) added.vendors.set(newVendor.id, newVendor);
          added.expenses.push(e);
          work = { ...work, vendors: newVendor ? [...work.vendors.filter((v) => v.id !== newVendor.id), newVendor] : work.vendors, expenses: [e, ...work.expenses] };
        } else if (kind === 'payments') {
          const vendor = mine(work).find((v) => same(v.name, txt(r.vendor)));
          if (!vendor) throw new RuleError('Vendor "{name}" not found — import or add the vendor first', { name: txt(r.vendor) });
          const amount = amt(r.amount);
          if (!(amount && amount > 0)) throw new RuleError('Enter the amount paid');
          const paidOn = txt(r.paidOn);
          if (!isoDate.test(paidOn)) throw new RuleError('Enter the payment date (dd-mm-yyyy)');
          if (paidOn > today) throw new RuleError('Payment date cannot be in the future');
          if (lockedIn(work.monthLocks, cl.id, paidOn)) throw new RuleError('Payment date falls in a locked month');
          const mode = parseMode(txt(r.mode));
          if (!mode) throw new RuleError('Mode must be Cash, UPI, Bank, Cheque or Card');
          const fits = cl.bankAccounts.filter((a) => a.active !== false && sourceKinds(mode).includes(a.kind));
          const srcName = txt(r.source);
          let account = srcName ? fits.find((a) => same(a.name, srcName) || same(a.upiId ?? '', srcName)) : undefined;
          if (srcName && !account) throw new RuleError('Paid-from "{name}" not found in payment sources', { name: srcName });
          if (!account && needsSource(cl, mode)) {
            if (fits.length === 1) account = fits[0];
            else throw new RuleError('Choose where the money was paid from');
          }
          let targets = work.expenses.filter((e) => e.vendorId === vendor.id && e.status !== 'rejected' && e.status !== 'draft')
            .map((e) => ({ e, due: outstanding(e, work.payments) })).filter((x) => x.due > 0.005)
            .sort((a, b) => a.e.invoiceDate.localeCompare(b.e.invoiceDate));
          const billNo = txt(r.billNo);
          if (billNo) {
            const hit = work.expenses.find((e) => e.vendorId === vendor.id && e.status !== 'rejected' && e.status !== 'draft' && same(e.invoiceNo ?? '', billNo));
            if (!hit) throw new RuleError('Bill {no} of this vendor not found', { no: billNo });
            targets = targets.filter((x) => x.e.id === hit.id);
            if (!targets.length) throw new RuleError('Bill {no} is already fully paid', { no: billNo });
          }
          const allocations = allocateLines([amount], targets.map((x) => ({ expenseId: x.e.id, amount: x.due })))[0];
          const p = makePayment(work, { vendorId: vendor.id, mode, accountId: account?.id, ref: txt(r.ref), paidOn, amount, allocations, source: 'excel_import' },
            vendor.name, targets.filter((x) => allocations.some((a) => a.expenseId === x.e.id)).map((x) => x.e.invoiceDate));
          label = `${vendor.name} ₹${amount} · ${paidOn}`;
          added.payments.push(p);
          work = { ...work, payments: [p, ...work.payments] };
        } else if (kind === 'centres') {
          const k = txt(r.kind).toLowerCase();
          const ck = /^(project|प्रोजेक्ट|परियोजना)/.test(k) ? 'project' : /^(branch|शाखा)/.test(k) ? 'branch' : undefined;
          if (!ck) throw new RuleError('Type must be Project or Branch');
          const name = txt(r.name);
          if (name.length < 2) throw new RuleError('Enter the name');
          if (cl.costCentres.some((c) => same(c.name, name))) throw new RuleError('Already exists — skipped');
          cl = { ...cl, costCentres: [...cl.costCentres, { id: uid(), kind: ck, name, active: true }] };
        } else {
          const k = txt(r.kind).toLowerCase();
          const sk: BankAccount['kind'] | undefined = /upi/.test(k) ? 'upi' : /(card|कार्ड)/.test(k) ? 'card' : /(cash|नकद|petty)/.test(k) ? 'cash' : /(bank|बैंक)/.test(k) ? 'bank' : undefined;
          if (!sk) throw new RuleError('Type must be Bank, UPI, Card or Cash');
          const name = txt(r.name);
          if (name.length < 2) throw new RuleError('Enter the name');
          if (cl.bankAccounts.some((a) => same(a.name, name))) throw new RuleError('Already exists — skipped');
          const upiId = txt(r.upiId).toLowerCase();
          if (sk === 'upi' && !/^[a-z0-9._-]{2,}@[a-z]{2,}$/.test(upiId)) throw new RuleError('Enter a valid UPI ID (e.g. name@okhdfc)');
          const linkName = txt(r.linkedBank);
          const linked = sk === 'upi' && linkName ? cl.bankAccounts.find((a) => a.kind === 'bank' && same(a.name, linkName)) : undefined;
          if (sk === 'upi' && linkName && !linked) throw new RuleError('Bank account "{name}" not found — list banks above UPI rows', { name: linkName });
          const tallyLedger = txt(r.tallyLedger) || linked?.tallyLedger || '';
          if (!tallyLedger) throw new RuleError('Enter the Tally ledger name');
          cl = { ...cl, bankAccounts: [...cl.bankAccounts, { id: uid(), kind: sk, name, upiId: sk === 'upi' ? upiId : undefined, linkedBankId: linked?.id, tallyLedger, active: true }] };
        }
        results.push({ row, ok: true, label });
      } catch (err) {
        if (err instanceof RuleError) results.push({ row, ok: false, label, message: err.message, vars: err.vars });
        else throw err;
      }
    });

    const ok = results.filter((x) => x.ok).length;
    if (commit && ok) {
      setS((st) => {
        const next: State = {
          ...st,
          vendors: [...st.vendors.filter((v) => !added.vendors.has(v.id)), ...added.vendors.values()],
          expenses: [...added.expenses, ...st.expenses],
          payments: [...added.payments, ...st.payments],
          clients: st.clients.map((c) => (c.id === cl.id ? { ...c, costCentres: cl.costCentres, bankAccounts: cl.bankAccounts } : c))
        };
        next.audit = audit(next, { clientId: cl.id, table: kind, action: 'IMPORT', summary: `${ok} row(s) imported from Excel${results.length - ok ? `, ${results.length - ok} skipped` : ''}` });
        return next;
      });
    }
    return results;
  }, [me, client, s]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateTdsRate = useCallback((r: TdsRate) => {
    setS((st) => {
      const next = { ...st, tdsRates: st.tdsRates.map((x) => (x.code === r.code ? r : x)) };
      next.audit = audit(next, { table: 'tds_rates', action: 'UPDATE', summary: `${r.code} → ${r.ratePct}%${r.verified ? ' (verified)' : ''}` });
      return next;
    });
  }, []);

  const addChallan = useCallback((c: Omit<TdsChallan, 'id' | 'clientId'>) => {
    if (!/^\d{5}$/.test(c.challanNo.trim())) throw new RuleError('Challan serial number must be 5 digits');
    if (!clientId) return;
    if (!/^\d{7}$/.test(c.bsrCode)) throw new RuleError('BSR code must be 7 digits');
    if (!(c.amount > 0)) throw new RuleError('Enter the amount');
    if (c.paidOn > todayIso()) throw new RuleError('Payment date cannot be in the future');
    if (c.paidOn < c.month + '-01') throw new RuleError('Challan date is before the TDS month — check the month or the receipt');
    if (s.challans.some((x) => x.clientId === clientId && x.bsrCode === c.bsrCode && x.challanNo === c.challanNo && x.paidOn === c.paidOn)) {
      throw new RuleError('This challan is already recorded');
    }
    const row = { ...c, challanNo: c.challanNo.trim(), id: uid(), clientId };
    setS((st) => {
      const next = { ...st, challans: [row, ...st.challans] };
      next.audit = audit(next, { clientId, table: 'tds_challans', rowId: row.id, action: 'INSERT', summary: `${c.month} ₹${c.amount} BSR ${c.bsrCode} #${c.challanNo}` });
      return next;
    });
  }, [clientId, s.challans]);

  const saveRecoRun = useCallback((run: Omit<RecoRun, 'id' | 'clientId' | 'createdAt'>) => {
    if (!clientId) return;
    const row: RecoRun = { ...run, id: uid(), clientId, createdAt: nowIso() };
    setS((st) => {
      const next = { ...st, recoRuns: [row, ...st.recoRuns.filter((r) => !(r.clientId === clientId && r.period === run.period))] };
      next.audit = audit(next, { clientId, table: 'gstr2b', action: 'IMPORT', summary: `${run.period}: ${run.lines.length} invoices (${run.source})` });
      next.jobs = [{ id: uid(), job: 'gst_reco_monthly', startedAt: row.createdAt, ok: true, rows: run.lines.length }, ...st.jobs];
      return next;
    });
  }, [clientId]);

  /** Admin sets a team member's WhatsApp number (India: 10 digits → +91). The person must confirm it from their own login. */
  const setUserWhatsapp = useCallback((userId: string, raw: string) => {
    if (!me || me.role === 'sub_user') throw new RuleError('Only admins can do this');
    const u = s.users.find((x) => x.id === userId);
    if (!u || (me.role === 'client_admin' && u.clientId !== me.clientId)) throw new RuleError('User not found');
    let n = raw.replace(/\D/g, '');
    if (n.length === 10) n = `91${n}`;
    if (n && !/^\d{11,15}$/.test(n)) throw new RuleError('Enter a 10-digit mobile number (or with country code)');
    if (n && s.users.some((x) => x.id !== userId && x.whatsapp === n)) throw new RuleError('This number is already used by another person');
    setS((st) => {
      const next = { ...st, users: st.users.map((x) => (x.id === userId ? { ...x, whatsapp: n || undefined, whatsappVerifiedAt: undefined, whatsappCode: undefined } : x)) };
      next.audit = audit(next, { clientId: u.clientId, table: 'profiles', rowId: userId, action: 'WHATSAPP_SET', summary: `${u.name}: ${n ? `+${n.slice(0, 2)}••••••${n.slice(-4)}` : 'removed'}` });
      return next;
    });
  }, [me, s.users]);

  /** Offline outbox: a file queued as "pending:<id>" has reached Drive — point every record at the real file id. */
  const resolvePendingFile = useCallback((pendingId: string, fileId: string) => {
    if (!pendingId.startsWith('pending:')) return;
    setS((st) => JSON.parse(JSON.stringify(st).split(JSON.stringify(pendingId)).join(JSON.stringify(fileId))) as State);
  }, []);

  /** The person removes their own number (not theirs, or they no longer want WhatsApp intake). */
  const removeMyWhatsapp = useCallback(() => {
    if (!me?.whatsapp) throw new RuleError('No WhatsApp number on your account');
    setS((st) => {
      const next = { ...st, users: st.users.map((x) => (x.id === me.id ? { ...x, whatsapp: undefined, whatsappVerifiedAt: undefined, whatsappCode: undefined } : x)) };
      next.audit = audit(next, { clientId: me.clientId, table: 'profiles', rowId: me.id, action: 'WHATSAPP_REMOVE', summary: me.name });
      return next;
    });
  }, [me]);

  /** Step 1 of the number check: a one-time code for the signed-in person (only its hash is kept). */
  const startWhatsappVerify = useCallback(async (): Promise<string> => {
    if (!me?.whatsapp) throw new RuleError('No WhatsApp number on your account');
    const code = makeCode();
    const pending = { hash: await hashCode(code), expires: new Date(Date.now() + CODE_TTL_MIN * 60_000).toISOString(), tries: 0 };
    setS((st) => {
      const next = { ...st, users: st.users.map((x) => (x.id === me.id ? { ...x, whatsappCode: pending, whatsappVerifiedAt: undefined } : x)) };
      next.audit = audit(next, { clientId: me.clientId, table: 'profiles', rowId: me.id, action: 'WHATSAPP_CODE', summary: `${me.name}: code issued` });
      return next;
    });
    return code;
  }, [me]);

  /** Step 2 (what the whatsapp-webhook does live): a text arrives FROM a number; "VERIFY <code>" confirms that number. */
  const receiveWhatsappText = useCallback(async (from: string, text: string): Promise<VerifyOutcome | 'not_verify' | 'unknown_number'> => {
    const code = parseVerifyText(text);
    if (!code) return 'not_verify';
    const u = s.users.find((x) => x.whatsapp === from.replace(/\D/g, ''));
    if (!u) return 'unknown_number';
    const outcome = await checkCode(code, u.whatsappCode ?? {});
    setS((st) => {
      const next = { ...st, users: st.users.map((x) => (x.id !== u.id ? x
        : outcome === 'verified' ? { ...x, whatsappVerifiedAt: nowIso(), whatsappCode: undefined }
        : outcome === 'wrong' && x.whatsappCode ? { ...x, whatsappCode: { ...x.whatsappCode, tries: x.whatsappCode.tries + 1 } } : x)) };
      next.audit = audit(next, { clientId: u.clientId, table: 'profiles', rowId: u.id, action: outcome === 'verified' ? 'WHATSAPP_CONFIRM' : 'WHATSAPP_CODE_FAIL', summary: `${u.name}: ${outcome}` });
      return next;
    });
    return outcome;
  }, [s.users]);

  const addUser = useCallback((name: string, role: Role) => {
    if (!me || !clientId) return;
    if (me.role === 'sub_user') throw new RuleError('Only admins can add users');
    if (role === 'super_admin') throw new RuleError('Not allowed');
    if (name.trim().length < 2) throw new RuleError('Enter the full name');
    const u: User = { id: uid(), name: name.trim(), role, clientId, active: true };
    setS((st) => {
      const next = { ...st, users: [...st.users, u] };
      next.audit = audit(next, { clientId, table: 'profiles', rowId: u.id, action: 'INSERT', summary: `${u.name} (${role})` });
      return next;
    });
  }, [me, clientId]);

  const toggleUser = useCallback((id: string) => {
    if (id === me?.id) throw new RuleError('You cannot deactivate yourself');
    setS((st) => {
      const u = st.users.find((x) => x.id === id);
      if (!u) return st;
      const next = { ...st, users: st.users.map((x) => (x.id === id ? { ...x, active: x.active === false } : x)) };
      next.audit = audit(next, { clientId: u.clientId, table: 'profiles', rowId: id, action: u.active === false ? 'ACTIVATE' : 'DEACTIVATE', summary: u.name });
      return next;
    });
  }, [me]);

  /** Demo of the quarterly compliance watch. Production: Edge Function `compliance-watch` on pg_cron. */
  /** Possible rule changes found by the AI scan — always filed as open findings for the CA; masters are never touched. */
  const addAiFindings = useCallback((items: { area: string; title: string; detail: string }[]) => {
    const at = nowIso();
    setS((st) => {
      const fresh = items.filter((it) => !st.findings.some((f) => f.status === 'open' && f.title === `AI: ${it.title}`));
      const next = { ...st, findings: [...fresh.map((it) => ({ id: uid(), area: it.area || 'other', kind: 'ai_suggestion' as const, status: 'open' as const, createdAt: at, title: `AI: ${it.title}`, detail: it.detail })), ...st.findings] };
      next.audit = audit(next, { table: 'compliance_findings', action: 'AI_SCAN', summary: `${fresh.length} possible change(s) filed for review` });
      return next;
    });
  }, []);

  const runComplianceCheck = useCallback(() => {
    const at = nowIso();
    setS((st) => {
      const unverified = st.tdsRates.filter((r) => !r.verified);
      const stillOpen = (title: string) => st.findings.some((f) => f.status === 'open' && f.title === title);
      const candidates: ComplianceFinding[] = [
        { id: uid(), area: 'due_dates', kind: 'review_due', status: 'open', createdAt: at,
          title: 'Quarterly review: TDS & GST due dates',
          detail: 'Confirm TDS payment due date, Form 140 quarterly due dates and GSTR-2B generation date are unchanged.' },
        { id: uid(), area: 'rcm', kind: 'review_due', status: 'open', createdAt: at,
          title: 'Quarterly review: RCM categories, RCM rates & 17(5) list',
          detail: 'Check latest CBIC rate notifications for additions/removals in reverse-charge services and blocked credits.' },
        ...(unverified.length ? [{ id: uid(), area: 'tds', kind: 'unverified_master' as const, status: 'open' as const, createdAt: at,
          title: `${unverified.length} TDS rates not yet verified by CA`,
          detail: unverified.map((r) => `${r.code} (${r.ratePct}%)`).join(', ') }] : []),
        { id: uid(), area: 'forms', kind: 'source_unreachable', status: 'open', createdAt: at,
          title: 'Demo mode: official pages were not fetched',
          detail: 'Page-change detection runs server-side once Supabase is connected (pages are fetched, hashed and compared with last quarter).' }
      ];
      // re-running must not pile up duplicates of findings that are still open
      const fresh = candidates.filter((f) => !stillOpen(f.title));
      return {
        ...st,
        findings: [...fresh, ...st.findings],
        sources: st.sources.map((x) => ({ ...x, lastCheckedAt: at })),
        jobs: [{ id: uid(), job: 'compliance_quarterly', startedAt: at, ok: true, rows: fresh.length }, ...st.jobs]
      };
    });
  }, []);

  const resolveFinding = useCallback((id: string, status: 'accepted' | 'dismissed') => {
    setS((st) => {
      const f = st.findings.find((x) => x.id === id);
      const next = { ...st, findings: st.findings.map((x) => (x.id === id ? { ...x, status } : x)) };
      next.audit = audit(next, { table: 'compliance_findings', rowId: id, action: status.toUpperCase(), summary: f?.title ?? '' });
      return next;
    });
  }, []);

  const updateClient = useCallback((c: Client) => {
    const before = s.clients.find((x) => x.id === c.id);
    if (me?.role !== 'super_admin' && before && CONTROL_FIELDS.some((k) => JSON.stringify(before[k]) !== JSON.stringify(c[k]))) {
      throw new RuleError('Only the CA firm can change control settings');
    }
    setS((st) => {
      const next = { ...st, clients: st.clients.map((x) => (x.id === c.id ? c : x)) };
      next.audit = audit(next, { clientId: c.id, table: 'clients', rowId: c.id, action: 'UPDATE', summary: 'Branding / settings' });
      return next;
    });
  }, [me, s.clients]);

  // ---------------------------------------------------------------- DPDP: consent, withdrawal, rights requests
  /** Sign-on consent: the user's own (and, for a client admin, the company's data-processing terms). Explicit action only. */
  const giveConsent = useCallback((o: { lang: Lang; ai: boolean; ageConfirmed: boolean; clientTerms?: { ai: boolean } }) => {
    if (!me) throw new RuleError('Not signed in');
    if (!o.ageConfirmed) throw new RuleError('You must be 18 or older to use Vouchr');
    const at = nowIso();
    const cl = me.clientId ? s.clients.find((c) => c.id === me.clientId) : undefined;
    const base = { noticeVersion: NOTICE_VERSION, lang: o.lang, method: 'in_app' as const, acceptedBy: me.id, acceptedAt: at, validUntil: cl?.engagementEndsOn };
    const rows: Consent[] = [{ ...base, id: uid(), scope: 'user', userId: me.id, clientId: me.clientId, purposes: { core: true, ai: o.ai }, ageConfirmed: true }];
    if (o.clientTerms && me.role === 'client_admin' && me.clientId) rows.push({ ...base, id: uid(), scope: 'client', clientId: me.clientId, purposes: { core: true, ai: o.clientTerms.ai } });
    setS((st) => {
      const next = { ...st, consents: [...rows, ...st.consents] };
      next.audit = audit(next, { clientId: me.clientId, table: 'consents', action: 'CONSENT', summary: `${me.name} agreed to notice ${NOTICE_VERSION}${o.ai ? ' incl. AI' : ' without AI'}${rows.length > 1 ? ' + company terms' : ''}` });
      return next;
    });
  }, [me, s.clients]);

  /** Withdraw consent — as easy as giving it (s.6(4)). aiOnly keeps using the app but stops AI. */
  const withdrawConsent = useCallback((scope: 'user' | 'client', o: { aiOnly?: boolean; reason?: string } = {}) => {
    if (!me) throw new RuleError('Not signed in');
    if (scope === 'client' && me.role !== 'client_admin' && me.role !== 'super_admin') throw new RuleError('Only an admin can do this for the company');
    const cid = scope === 'client' ? clientId : undefined;
    const current = [...s.consents].filter((c) => c.scope === scope && !c.withdrawnAt && (scope === 'user' ? c.userId === me.id : c.clientId === cid))
      .sort((a, b) => b.acceptedAt.localeCompare(a.acceptedAt))[0];
    if (!current) throw new RuleError('There is no active consent to withdraw');
    const at = nowIso();
    setS((st) => {
      let consents = st.consents.map((c) => (c.id === current.id ? { ...c, withdrawnAt: at, withdrawnBy: me.id, withdrawReason: o.reason || (o.aiOnly ? 'AI switched off' : undefined) } : c));
      // switching only AI off = a fresh record with AI off, so the history shows both decisions
      if (o.aiOnly) consents = [{ ...current, id: uid(), purposes: { ...current.purposes, ai: false }, acceptedBy: me.id, acceptedAt: at }, ...consents];
      const next = { ...st, consents, currentUserId: scope === 'user' && !o.aiOnly ? undefined : st.currentUserId };
      next.audit = audit(next, { clientId: me.clientId ?? cid, table: 'consents', action: o.aiOnly ? 'AI_OFF' : 'WITHDRAW', summary: `${me.name}: ${scope === 'client' ? 'company' : 'own'} consent${o.aiOnly ? ' — AI switched off' : ' withdrawn'}` });
      return next;
    });
  }, [me, clientId, s.consents]);

  /** CA firm records the client's acceptance from the signed engagement letter (instead of in-app acceptance). */
  const recordClientConsent = useCallback((cid: string, o: { reference: string; ai: boolean; validUntil?: string }) => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can record this');
    if (o.reference.trim().length < 5) throw new RuleError('Give the engagement letter reference and date');
    const at = nowIso();
    setS((st) => {
      const c: Consent = { id: uid(), scope: 'client', clientId: cid, noticeVersion: NOTICE_VERSION, purposes: { core: true, ai: o.ai }, lang: st.lang, method: 'engagement_letter',
        reference: o.reference.trim(), acceptedBy: me.id, acceptedAt: at, validUntil: o.validUntil || st.clients.find((x) => x.id === cid)?.engagementEndsOn };
      const next = { ...st, consents: [c, ...st.consents], clients: o.validUntil ? st.clients.map((x) => (x.id === cid ? { ...x, engagementEndsOn: o.validUntil } : x)) : st.clients };
      next.audit = audit(next, { clientId: cid, table: 'consents', action: 'CLIENT_TERMS', summary: `Recorded from ${c.reference}${o.ai ? ' incl. AI' : ' without AI'}` });
      return next;
    });
  }, [me]);

  const updateFirm = useCallback((f: FirmInfo) => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can change this');
    if (f.name.trim().length < 2) throw new RuleError('Enter the firm name');
    if (f.privacyEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.privacyEmail)) throw new RuleError('Enter a valid e-mail');
    setS((st) => { const next = { ...st, firm: f }; next.audit = audit(next, { table: 'firm', action: 'UPDATE', summary: `Privacy contact: ${f.privacyContactName ?? '—'} ${f.privacyEmail ?? ''}` }); return next; });
  }, [me]);

  const addPrivacyRequest = useCallback((kind: PrivacyRequest['kind'], details: string) => {
    if (!me) throw new RuleError('Not signed in');
    if (details.trim().length < 5) throw new RuleError('Describe your request');
    const at = nowIso();
    setS((st) => {
      const next = { ...st, privacyRequests: [{ id: uid(), userId: me.id, clientId: me.clientId, kind, details: details.trim(), createdAt: at, dueBy: dueIn90(at), status: 'open' as const }, ...st.privacyRequests] };
      next.audit = audit(next, { clientId: me.clientId, table: 'privacy_requests', action: 'INSERT', summary: `${kind} request by ${me.name}` });
      return next;
    });
  }, [me]);

  const resolvePrivacyRequest = useCallback((id: string, resolution: string) => {
    if (me?.role !== 'super_admin') throw new RuleError('Only the CA firm can close requests');
    if (resolution.trim().length < 5) throw new RuleError('Write what was done');
    setS((st) => {
      const next = { ...st, privacyRequests: st.privacyRequests.map((r) => (r.id === id ? { ...r, status: 'resolved' as const, resolution: resolution.trim(), resolvedAt: nowIso() } : r)) };
      next.audit = audit(next, { table: 'privacy_requests', rowId: id, action: 'RESOLVE', summary: resolution.trim().slice(0, 120) });
      return next;
    });
  }, [me]);

  const logEvent = useCallback((level: SystemEvent['level'], component: string, message: string, vars?: SystemEvent['vars']) => {
    setS((st) => ({ ...st, events: [{ id: uid(), level, component, clientId, message, vars, at: nowIso() }, ...st.events].slice(0, 300) }));
  }, [clientId]);

  const login = (userId: string) => setS((st) => {
    const u = st.users.find((x) => x.id === userId);
    if (!u || u.active === false) return st;
    const next = { ...st, currentUserId: userId };
    next.audit = audit(next, { clientId: u.clientId, table: 'session', action: 'LOGIN', summary: u.name });
    return next;
  });
  const logout = () => setS((st) => ({ ...st, currentUserId: undefined }));
  const setLang = (lang: Lang) => setS((st) => ({ ...st, lang }));
  const setActiveClient = (id: string) => setS((st) => ({ ...st, activeClientId: id }));
  const resetDemo = () => setS({ ...initial(), currentUserId: s.currentUserId });

  const scoped = useMemo(() => ({
    expenses: s.expenses.filter((e) => e.clientId === clientId),
    payments: s.payments.filter((p) => p.clientId === clientId),
    vendors: s.vendors.filter((v) => v.clientId === clientId),
    challans: s.challans.filter((c) => c.clientId === clientId),
    recoRuns: s.recoRuns.filter((r) => r.clientId === clientId),
    vendorNotes: (s.vendorNotes ?? []).filter((n) => n.clientId === clientId),
    itcReversals: (s.itcReversals ?? []).filter((r) => r.clientId === clientId)
  }), [s.expenses, s.payments, s.vendors, s.challans, s.recoRuns, s.vendorNotes, s.itcReversals, clientId]);

  return {
    s, me, client, clientId, scoped, isLocked, findDuplicate,
    addExpense, completeExpense, addDrafts, importData, deleteDraft, recordPayment, applyAdvance, voidPayment, saveVendorNote, linkVendorNote, voidVendorNote, recordItcReversal, recordItcReclaim, assignReview, closeFy, findLookAlike, reviewExpense, markPosted, toggleLock, saveVendor, updateTdsRate,
    addChallan, saveRecoRun, addUser, toggleUser, setUserWhatsapp, removeMyWhatsapp, startWhatsappVerify, receiveWhatsappText, resolvePendingFile,
    giveConsent, withdrawConsent, recordClientConsent, updateFirm, addPrivacyRequest, resolvePrivacyRequest,
    runComplianceCheck, addAiFindings, resolveFinding, updateClient, logEvent, login, logout, setLang, setActiveClient, resetDemo
  };
}

type Store = ReturnType<typeof useStoreValue>;
const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const value = useStoreValue();
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore(): Store {
  const v = useContext(Ctx);
  if (!v) throw new Error('useStore outside StoreProvider');
  return v;
}
