// The truth contract is enforced by code, so it can be tested without calling Gemini: feed deliberately bad answers,
// check that every one is marked (never silently accepted).
import { describe, expect, it } from 'vitest';
import { asFact, checkEvidence, gstinValid, strayNumbers } from '../../supabase/functions/_shared/ai/truth.ts';
import { TASKS } from '../../supabase/functions/_shared/ai/tasks.ts';
import { gstinCheckChar } from './validators';

const today = '2026-11-02';
const noOut = { text: '', sources: [] };
const F = (value: unknown, certainty = 'certain', evidence = String(value ?? '')) => ({ value, certainty, evidence });
const good = '27AAKFS4821M1Z' + gstinCheckChar('27AAKFS4821M1Z');

describe('truth contract — facts', () => {
  it('never accepts "certain" without evidence, and fixes contradictory answers', () => {
    expect(asFact({ value: 'X', certainty: 'certain', evidence: '' }).certainty).toBe('uncertain');
    expect(asFact({ value: null, certainty: 'certain', evidence: '' }).certainty).toBe('not_found');
    expect(asFact({ value: 'X', certainty: 'not_found', evidence: '' }).certainty).toBe('uncertain');
    expect(asFact({ value: 'X', certainty: 'sure', evidence: 'X' }).certainty).toBe('uncertain');
    expect(asFact(undefined).certainty).toBe('uncertain'); // an omitted field is unknown, not "absent"
  });
  it('checks that a quote really is in the source', () => {
    expect(checkEvidence(asFact(F('Sharma Traders')), 'Bill from SHARMA  TRADERS, Pune').certainty).toBe('certain');
    expect(checkEvidence(asFact(F('Verma Traders')), 'Bill from SHARMA TRADERS, Pune').certainty).toBe('uncertain');
  });
  it('validates GSTIN check digit (same algorithm as the app)', () => {
    expect(gstinValid(good)).toBe(true);
    expect(gstinValid(good.slice(0, 14) + (good[14] === 'A' ? 'B' : 'A'))).toBe(false);
  });
  it('finds numbers that are not in our data', () => {
    expect(strayNumbers('Paid 11,800 against SOS/245 on 19-10-2026', [11800, 245, 19, 10, 2026])).toEqual([]);
    expect(strayNumbers('Paid 12,500 against SOS/245', [11800, 245])).toEqual(['12500']);
  });
});

describe('A — read bill', () => {
  const raw = {
    vendor_name: F('Sharma Traders'), vendor_gstin: F(good), invoice_no: F('ST/12'), invoice_date: F('2026-10-05'),
    taxable_value: F(1000), cgst: F(90), sgst: F(90), igst: F(null, 'not_found', ''), total: F(1180), irn: F(null, 'not_found', ''), description: F('paper'),
    non_taxable_charges: F(null, 'not_found', ''), eco_pays_tax: F(null, 'not_found', ''), eco_gstin: F(null, 'not_found', '')
  };
  it('a clean bill stays certain', () => {
    const r = TASKS.read_bill.check(raw, {}, today, noOut);
    expect(r.needsHumanCheck).toBe(false);
  });
  it('marks a misread GSTIN, a future date, totals that do not add up, and the buyer’s own GSTIN', () => {
    const r = TASKS.read_bill.check({ ...raw, vendor_gstin: F('27AAKFS4821M1ZZ'), invoice_date: F('2027-01-05'), total: F(1500) }, {}, today, noOut);
    const d = r.doubts.join(' | ');
    expect(d).toMatch(/vendor_gstin: GSTIN fails/);
    expect(d).toMatch(/invoice_date: date is in the future/);
    expect(d).toMatch(/total: .*don't add up/);
    expect(TASKS.read_bill.check(raw, { buyerGstin: good }, today, noOut).doubts.join()).toMatch(/your own GSTIN/);
  });
});

describe('B — voice entry', () => {
  it('a fact not found in the transcript is marked; "kal" style answers stay uncertain', () => {
    const r = TASKS.voice_entry.check({
      transcript: 'paanch sau rupaye auto ko diye, cash', vendor_name: F('auto'), amount: F(500, 'certain', 'paanch sau'),
      purpose: F('Godown trip', 'certain', 'godown'), pay_mode: F('cash'), paid: F(true, 'certain', 'diye'), bill_date: F('2026-11-01', 'uncertain', 'kal')
    }, {}, today, noOut);
    expect(r.doubts.join(' | ')).toMatch(/purpose: quoted text not found/);
    expect((r.result as { bill_date: { certainty: string } }).bill_date.certainty).toBe('uncertain');
    expect((r.result as { amount: { certainty: string } }).amount.certainty).toBe('certain');
  });
});

describe('CA review, D, E, F, G, H, J — model cannot invent', () => {
  it('expense head / TDS code must come from our lists; mismatches are computed by the app', () => {
    const r = TASKS.analyse_invoice.check({ vendor_name: F('X'), invoice_date: F('2026-10-05'), total: F(1180), taxable_value: F(1000), cgst: F(90), sgst: F(90),
      expense_head: F('Magic expenses'), tds_code: F('194Z'), red_flags: [{ flag: 'looks fake', severity: 'high', evidence: '' }], line_items: [] },
      { heads: ['Repairs'], tdsTable: [{ code: 'CONTRACT_IND' }], recorded: { total: 1300 } }, today, noOut);
    const res = r.result as { expense_head: { value: unknown }; tds_code: { value: unknown }; red_flags: unknown[]; mismatches: string[] };
    expect(res.expense_head.value).toBeNull();
    expect(res.tds_code.value).toBeNull();
    expect(res.red_flags).toHaveLength(0);
    expect(res.mismatches[0]).toMatch(/Total: bill shows 1180, recorded 1300/);
    expect(r.doubts.join()).toMatch(/dropped — no evidence/);
  });
  it('D: a vendor outside our list or without a quote from the narration is marked', () => {
    const ctx = { vendors: [{ name: 'Sharma Traders' }], rows: [{ id: 'r1', narration: 'UPI/sharmatraders@okhdfc/pay' }, { id: 'r2', narration: 'NEFT ABC LTD' }] };
    const r = TASKS.bank_match.check({ matches: [{ row_id: 'r1', vendor: F('Sharma Traders', 'certain', 'sharmatraders@okhdfc') }, { row_id: 'r2', vendor: F('ABC Ltd', 'certain', 'ABC LTD') }, { row_id: 'r9', vendor: F('Sharma Traders') }] }, ctx, today, noOut);
    const m = (r.result as { matches: { row_id: string; vendor: { certainty: string } }[] }).matches;
    expect(m.map((x) => [x.row_id, x.vendor.certainty])).toEqual([['r1', 'certain'], ['r2', 'uncertain']]);
  });
  it('E: a narration with an invented number is flagged', () => {
    const ctx = { bill: { vendor: 'Sharma', no: 'ST/12', total: 1180 } };
    expect(TASKS.narration.check({ narration: 'Being paper purchased from Sharma vide ST/12 for Rs 1180' }, ctx, today, noOut).needsHumanCheck).toBe(false);
    expect(TASKS.narration.check({ narration: 'Being 20 reams purchased for Rs 1180' }, ctx, today, noOut).doubts[0]).toMatch(/numbers not on the bill \(20\)/);
  });
  it('F: an HSN not printed on the bill is always a marked suggestion; invalid GST rate is marked', () => {
    const r = TASKS.hsn_suggest.check({ items: [{ index: 0, hsn_sac: F('4802'), gst_rate: F(12) }] }, { date: '2026-10-05', allowedRates: [0, 5, 18, 40], items: [{ description: 'A4 paper' }] }, today, noOut);
    expect(r.doubts.join(' | ')).toMatch(/suggestion — not printed/);
    expect(r.doubts.join(' | ')).toMatch(/not a valid GST rate/);
  });
  it('G: unknown filters are rejected and the AI never supplies figures', () => {
    const r = TASKS.ask_data.check({ query: 'spend_total', head: F('Party expenses'), from: F('2026-07-01'), to: F('2026-09-30'), understood_en: 'Spend was 45000 in Q2' },
      { heads: ['Repairs'], centres: [], vendors: [] }, today, noOut);
    expect((r.result as { head: { value: unknown } }).head.value).toBeNull();
    expect(r.doubts.join()).toMatch(/restatement contained figures/);
    expect((TASKS.ask_data.check({ query: 'predict_next_year' }, {}, today, noOut).result as { query: string }).query).toBe('unanswerable');
  });
  it('H: commentary with raw digits or unknown figure keys is dropped', () => {
    const r = TASKS.mis_commentary.check({ points: [{ text_en: 'Spend this month is {thisMonth}', text_hi: 'इस महीने खर्च {thisMonth}' }, { text_en: 'Spend rose 20%', text_hi: 'खर्च बढ़ा' }, { text_en: '{profit} is up', text_hi: '{profit}' }] },
      { figures: { thisMonth: 1000 } }, today, noOut);
    expect((r.result as { points: unknown[] }).points).toHaveLength(1);
    expect(r.doubts).toHaveLength(2);
  });
  it('J: "same bill" needs two quoted matches and no differences', () => {
    const p = (x: string) => ({ point: x, evidence_a: x, evidence_b: x });
    expect((TASKS.compare_bills.check({ verdict: 'same', same_points: [p('no 12')], different_points: [] }, {}, today, noOut).result as { verdict: string }).verdict).toBe('unsure');
    expect((TASKS.compare_bills.check({ verdict: 'same', same_points: [p('no 12'), p('₹500')], different_points: [] }, {}, today, noOut).result as { verdict: string }).verdict).toBe('same');
  });
  it('norms scan: unofficial source or missing notification number is marked', () => {
    const r = TASKS.norms_scan.check([{ title: 'New TDS rate', source_url: 'https://someblog.com/x', notification_no: '', effective_date: '' }], {}, today, { text: '', sources: [] });
    expect(r.doubts[0]).toMatch(/not a government website.*no notification number.*no effective date/);
  });
});

describe('G calculator and J fingerprint (no AI involved)', async () => {
  const { runAsk } = await import('./askData');
  const { dHashFromGray, hamming } = await import('./phash');
  const e = (o: Record<string, unknown>) => ({ id: String(Math.random()), clientId: 'c', status: 'approved', vendorName: 'A', invoiceDate: '2026-10-05', taxableValue: 100, cgst: 9, sgst: 9, igst: 0, totalAmount: 118, tdsAmount: 0, itcEligible: true, ...o }) as never;
  const data = { expenses: [e({}), e({ vendorName: 'B', taxableValue: 50, totalAmount: 59, invoiceDate: '2026-09-01' }), e({ status: 'draft', taxableValue: 999 })], payments: [], heads: [], centres: [] };
  it('computes totals from records, honouring filters and skipping drafts', () => {
    expect(runAsk('spend_total', {}, data).value).toBe(150);
    expect(runAsk('spend_total', { from: '2026-10-01' }, data).value).toBe(100);
    expect(runAsk('top_vendors', {}, data).rows[0]).toEqual({ label: 'A', value: 118 });
    expect(runAsk('itc_total', {}, data).value).toBe(36); // 18 + 18; the draft is excluded
    expect(runAsk('bill_count', { vendor: 'B' }, data).value).toBe(1);
  });
  it('dHash: identical images 0 bits apart, inverted image far apart', () => {
    const g = Array.from({ length: 72 }, (_, i) => (i * 37) % 256);
    const h = dHashFromGray(g);
    expect(hamming(h, dHashFromGray(g))).toBe(0);
    expect(hamming(h, dHashFromGray(g.map((x) => 255 - x)))).toBeGreaterThan(40);
  });
});

describe('G periods are computed by code', async () => {
  const { periodsFor, TASKS: T } = await import('../../supabase/functions/_shared/ai/tasks.ts');
  it('2 Nov 2026: this quarter Oct–Dec, last quarter Jul–Sep, FY 2026-27', () => {
    const p = periodsFor('2026-11-02');
    expect(p.this_quarter).toEqual({ from: '2026-10-01', to: '2026-12-31' });
    expect(p.last_quarter).toEqual({ from: '2026-07-01', to: '2026-09-30' });
    expect(p.this_financial_year).toEqual({ from: '2026-04-01', to: '2027-03-31' });
    expect(periodsFor('2027-02-10').last_quarter).toEqual({ from: '2026-10-01', to: '2026-12-31' });
    expect(periodsFor('2027-01-15').last_month).toEqual({ from: '2026-12-01', to: '2026-12-31' });
  });
  it('a wrong quarter (the mistake seen live) is marked', () => {
    const F = (v: string) => ({ value: v, certainty: 'certain', evidence: 'this quarter' });
    const ctx = { heads: [], centres: [], vendors: [] }, none = { text: '', sources: [] };
    const bad = T.ask_data.check({ query: 'spend_total', period: F('last_quarter') }, ctx, '2026-11-02', none);
    expect(bad.doubts.join()).toMatch(/does not match the words/);
    const good = T.ask_data.check({ query: 'spend_total', period: F('this_quarter') }, ctx, '2026-11-02', none);
    expect(good.doubts.filter((d) => /^(period|from|to):/.test(d))).toEqual([]);
    expect((good.result as { from: { value: string } }).from.value).toBe('2026-10-01'); // dates come from the app
    const custom = T.ask_data.check({ query: 'spend_total', period: F('custom'), from: F('2026-08-01'), to: F('2026-08-31') }, ctx, '2026-11-02', none);
    expect(custom.doubts.join()).toMatch(/worked out by AI/);
  });
});
