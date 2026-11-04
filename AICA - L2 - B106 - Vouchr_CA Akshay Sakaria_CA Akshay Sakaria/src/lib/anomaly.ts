// Bill risk check — rule-based red flags for fake, inflated or wrongly taxed bills. Runs on the device, free, and every
// flag says WHY in plain words. A flag is a reason to look, never proof: genuine bills can trip a rule (e.g. a hotel in
// another state rightly charges CGST + SGST), so the CA decides. Optional AI review (Gemini) adds to this; it doesn't replace it.

import type { Client, Expense, TdsRate, Vendor } from '../data/types';
import { ALL_GST_RATES, GST2_FROM } from '../data/masters';
import { daysBetween } from './dates';
import { round2 } from './money';
import { normBillNo } from './billno';

export type Severity = 'high' | 'medium' | 'low';
export interface RiskFlag {
  id: string;
  code: string;
  severity: Severity;
  expenseId?: string;
  vendorId?: string;
  title: string; // English text = translation key
  detail: string;
  vars?: Record<string, string | number>;
}

/** Indian digit grouping for amounts inside messages (the ₹ sign is in the message text). */
const inr = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
const SEV: Record<Severity, number> = { high: 0, medium: 1, low: 2 };
const normNo = normBillNo; // same rule as the duplicate check at entry
const tailNo = (n?: string) => { const m = /^(.*?)(\d+)\D*$/.exec(n ?? ''); return m ? { prefix: m[1].toLowerCase().replace(/[^a-z]/g, ''), num: Number(m[2]) } : undefined; };
const median = (xs: number[]) => { const s = [...xs].sort((a, b) => a - b); const m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

/** Benford first-digit test (Nigrini). Mean absolute deviation above 0.015 = "nonconformity". Needs ≥ 100 amounts. */
export function benfordMad(amounts: number[]): { n: number; mad: number } | undefined {
  const firsts = amounts.filter((a) => a >= 10).map((a) => Number(String(Math.floor(a))[0]));
  if (firsts.length < 100) return undefined;
  let mad = 0;
  for (let d = 1; d <= 9; d++) mad += Math.abs(firsts.filter((x) => x === d).length / firsts.length - Math.log10(1 + 1 / d));
  return { n: firsts.length, mad: round2((mad / 9) * 10000) / 10000 };
}

export function riskCheck(expenses: Expense[], vendors: Vendor[], client: Client | undefined, tdsRates: TdsRate[]): RiskFlag[] {
  const live = expenses.filter((e) => e.status !== 'draft' && e.status !== 'rejected');
  const vendorOf = new Map(vendors.map((v) => [v.id, v]));
  const flags: RiskFlag[] = [];
  const add = (f: Omit<RiskFlag, 'id'>) => flags.push({ ...f, id: `${f.code}:${f.expenseId ?? f.vendorId ?? 'all'}` });

  const byVendor = new Map<string, Expense[]>();
  for (const e of live) if (e.vendorId) byVendor.set(e.vendorId, [...(byVendor.get(e.vendorId) ?? []), e]);

  for (const e of live) {
    const v = e.vendorId ? vendorOf.get(e.vendorId) : undefined;
    const tax = round2(e.cgst + e.sgst + e.igst);
    const amount = round2(e.totalAmount);

    // 1. GST charged without a GSTIN — the classic fake-invoice sign; ITC is not available on it anyway
    if (tax > 0 && v && !v.gstin && !e.ecoPaysTax) add({ code: 'gst_without_gstin', severity: 'high', expenseId: e.id, vendorId: v.id,
      title: 'GST charged by a vendor without GSTIN', detail: 'Only registered suppliers may charge GST. Ask for a proper tax invoice with the GSTIN before paying the GST part.' });

    // 2. GST rate that does not exist on the bill date (GST 2.0 from 22-09-2025)
    if (tax > 0 && e.taxableValue > 0) {
      const pct = (tax / e.taxableValue) * 100;
      const nearest = ALL_GST_RATES.reduce((b, r) => (Math.abs(r - pct) < Math.abs(b - pct) ? r : b), 0);
      if (Math.abs(nearest - pct) > 0.6) add({ code: 'odd_gst_rate', severity: 'low', expenseId: e.id, vendorId: e.vendorId,
        title: 'GST is {pct}% of the taxable value', detail: 'Not a single GST rate. Fine if the bill has items at different rates; otherwise the tax is miscalculated.', vars: { pct: round2(pct) } });
      else if ((nearest === 12 || nearest === 28) && e.invoiceDate >= GST2_FROM) add({ code: 'old_gst_slab', severity: 'medium', expenseId: e.id, vendorId: e.vendorId,
        title: 'GST at {rate}% on a bill dated after 21-09-2025', detail: 'The 12% and 28% slabs were removed under GST 2.0 from 22-09-2025 (a few items such as tobacco stay under transition rules). Check the rate with the vendor.', vars: { rate: nearest } });
      else if (nearest === 40 && e.invoiceDate < GST2_FROM) add({ code: 'early_40', severity: 'medium', expenseId: e.id, vendorId: e.vendorId,
        title: 'GST at 40% on a bill dated before 22-09-2025', detail: 'The 40% rate started with GST 2.0 on 22-09-2025. Check the bill date and rate.' });
    }

    // 1b. e-invoice QR whose IRP signature does not verify — the QR (and so the bill) may be altered or fake
    if (e.irnSignature === 'invalid') add({ code: 'qr_signature_invalid', severity: 'high', expenseId: e.id, vendorId: e.vendorId,
      title: 'E-invoice QR signature does not match the IRP key', detail: 'The QR on this bill was not signed by the e-invoice portal (or was changed). Check the IRN on the e-invoice portal before paying or claiming ITC.' });

    // 2b. Section 9(5): the app paid the GST — credit on food / cab hire is commonly blocked under 17(5); the CA decides
    if (e.ecoPaysTax && e.itcEligible && tax > 0) add({ code: 'eco_itc', severity: 'low', expenseId: e.id, vendorId: e.vendorId,
      title: 'Input credit marked on a bill where the app paid the GST', detail: 'Section 9(5) supply (food app, cab app, stays). Check section 17(5) before claiming this credit.' });

    // 3. Place of supply looks wrong
    if (v?.stateCode && client?.stateCode) {
      if (v.stateCode === client.stateCode && e.igst > 0) add({ code: 'igst_same_state', severity: 'low', expenseId: e.id, vendorId: v.id,
        title: 'IGST charged by a vendor in your own state', detail: 'Usually CGST + SGST applies within the same state. Check the place of supply on the bill.' });
      if (v.stateCode !== client.stateCode && (e.cgst > 0 || e.sgst > 0)) add({ code: 'cgst_other_state', severity: 'low', expenseId: e.id, vendorId: v.id,
        title: 'CGST + SGST charged by an out-of-state vendor', detail: "Normal for hotel stays, events or work done in the vendor's state; otherwise IGST was expected. ITC of another state's tax may be lost." });
    }

    // 4. Vendor issues e-invoices but this bill has no IRN (Rule 48(5): such a document is not a valid invoice)
    const history = e.vendorId ? byVendor.get(e.vendorId) ?? [] : [];
    if (!e.irn && v?.gstin && tax > 0 && history.some((x) => x.irn && x.id !== e.id && x.invoiceDate <= e.invoiceDate)) add({ code: 'missing_irn', severity: 'medium', expenseId: e.id, vendorId: v.id,
      title: 'No e-invoice IRN, though this vendor issues e-invoices', detail: 'A supplier covered by e-invoicing must generate an IRN for every B2B invoice; without it the bill may not support ITC. Ask for the e-invoice.' });

    // 5. Round figure
    if (amount >= 10000 && amount % 1000 === 0) add({ code: 'round_amount', severity: 'low', expenseId: e.id, vendorId: e.vendorId,
      title: 'Round-figure bill of ₹{amount}', detail: 'Genuine bills rarely come to an exact round figure. Check against the delivery or work done.', vars: { amount: inr(amount) } });

    // 6. Far above this vendor's usual bill
    const others = history.filter((x) => x.id !== e.id).map((x) => x.totalAmount);
    if (others.length >= 3) {
      const med = median(others);
      if (med > 0 && amount > med * 3 && amount - med > 10000) add({ code: 'amount_spike', severity: 'medium', expenseId: e.id, vendorId: e.vendorId,
        title: "{x}× this vendor's usual bill", detail: 'Usual bill is about ₹{median}. Check the quantity and rate.', vars: { x: round2(amount / med), median: inr(round2(med)) } });
    }

    // 7. Inoperative PAN but normal TDS rate
    const rate = e.tdsCode ? tdsRates.find((r) => r.code === e.tdsCode) : undefined;
    if (v?.panStatus === 'Inoperative' && rate?.noPanRatePct && (e.tdsRatePct ?? 0) < rate.noPanRatePct) add({ code: 'inoperative_pan', severity: 'high', expenseId: e.id, vendorId: v.id,
      title: 'Vendor PAN is inoperative — TDS should be at the higher rate', detail: 'Rate used {used}%, higher rate {higher}%. Short deduction leads to interest and disallowance.', vars: { used: e.tdsRatePct ?? 0, higher: rate.noPanRatePct } });
  }

  for (const [vendorId, bills] of byVendor) {
    const v = vendorOf.get(vendorId);
    const sorted = [...bills].sort((a, b) => a.invoiceDate.localeCompare(b.invoiceDate));

    // 8. Same bill number written differently (INV-001 / INV/001) — exact repeats are already blocked at entry
    const seen = new Map<string, Expense>();
    for (const e of sorted) {
      const k = normNo(e.invoiceNo);
      if (!k) continue;
      const first = seen.get(k);
      if (first && first.invoiceNo !== e.invoiceNo) add({ code: 'bill_no_variant', severity: 'high', expenseId: e.id, vendorId,
        title: 'Same bill number recorded twice', detail: '{a} and {b} look like the same bill. Check before paying twice.', vars: { a: first.invoiceNo ?? '', b: e.invoiceNo ?? '' } });
      else if (!first) seen.set(k, e);
    }

    // 9. Bill numbers going backwards in time (same series)
    for (let i = 1; i < sorted.length; i++) {
      const a = tailNo(sorted[i - 1].invoiceNo), b = tailNo(sorted[i].invoiceNo);
      if (a && b && a.prefix === b.prefix && sorted[i].invoiceDate > sorted[i - 1].invoiceDate && b.num < a.num) add({ code: 'bill_no_backwards', severity: 'low', expenseId: sorted[i].id, vendorId,
        title: 'Bill number goes backwards', detail: '{b} is dated after {a} but has a lower number. Can happen with several bill books; otherwise ask the vendor.', vars: { a: sorted[i - 1].invoiceNo ?? '', b: sorted[i].invoiceNo ?? '' } });
    }

    // 10. Several bills just under the single-bill TDS limit within a week (possible splitting)
    const code = sorted.find((e) => e.tdsCode)?.tdsCode;
    const limit = code ? tdsRates.find((r) => r.code === code)?.thresholdSingle : undefined;
    if (limit) {
      const small = sorted.filter((e) => e.taxableValue < limit && !e.tdsAmount);
      let flagged = '';
      for (const e of small) {
        const win = small.filter((x) => x.invoiceDate <= e.invoiceDate && daysBetween(x.invoiceDate, e.invoiceDate) <= 6);
        const sum = round2(win.reduce((s, x) => s + x.taxableValue, 0));
        if (win.length >= 2 && sum >= limit && !win.some((x) => x.id === flagged)) {
          flagged = e.id;
          add({ code: 'tds_split', severity: 'medium', expenseId: e.id, vendorId,
            title: 'Several bills just under the TDS limit', detail: '{n} bills from {vendor} within 7 days total ₹{sum}; each is below the single-bill limit of ₹{limit}. Check whether one job was split.',
            vars: { n: win.length, vendor: v?.name ?? '', sum: inr(sum), limit: inr(limit) } });
        }
      }
    }
  }

  // 11. Portfolio check — amounts that don't follow Benford's law can point to made-up figures
  const b = benfordMad(live.map((e) => e.totalAmount));
  if (b && b.mad > 0.015) add({ code: 'benford', severity: 'medium',
    title: "Bill amounts don't follow the usual pattern (Benford test)", detail: 'First digits of {n} bill amounts deviate from the natural pattern (MAD {mad}; above 0.015 is unusual). Not proof — sample-check bills from the largest vendors.', vars: { n: b.n, mad: b.mad } });

  return flags.sort((x, y) => SEV[x.severity] - SEV[y.severity]);
}
