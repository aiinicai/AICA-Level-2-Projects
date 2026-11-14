// Every AI task Vouchr can run: prompt + JSON schema + the code checks applied to the answer (see truth.ts).
// Numbers shown to users are computed by the app wherever possible; AI only reads, matches or words things.
import { callGemini, parseJson, type GeminiOut, type Part } from './gemini.ts';
import {
  TRUTH_RULES, asFact, checkAmountFact, checkDateFact, checkEvidence, checkGstinFact, checkMember, checkTotals, doubt, factSchema,
  finish, strayNumbers, type Checked, type Fact
} from './truth.ts';

export type Role = 'super_admin' | 'client_admin' | 'sub_user';
export type TaskName = 'read_bill' | 'voice_entry' | 'analyse_invoice' | 'reco_message' | 'bank_match' | 'narration' | 'hsn_suggest'
  | 'ask_data' | 'mis_commentary' | 'notice_summary' | 'compare_bills' | 'norms_scan';
export interface InlineFile { mime: string; data: string } // base64
// deno-lint-ignore no-explicit-any
type Ctx = Record<string, any>;
// deno-lint-ignore no-explicit-any
type Raw = any;

interface TaskDef {
  roles: Role[];
  files: [number, number]; // min, max inline files
  search?: boolean;
  schema?: unknown;
  prompt: (ctx: Ctx, today: string) => string;
  check: (raw: Raw, ctx: Ctx, today: string, out: GeminiOut) => Checked<unknown>;
}

const ADMINS: Role[] = ['super_admin', 'client_admin'];
const ALL: Role[] = ['super_admin', 'client_admin', 'sub_user'];
const S = (type: string, extra: Record<string, unknown> = {}) => ({ type, ...extra });
const F = factSchema;
const obj = (properties: Record<string, unknown>, required = Object.keys(properties)) => S('OBJECT', { properties, required });
const arr = (items: unknown) => S('ARRAY', { items });
const str = (v: unknown) => (typeof v === 'string' ? v : '');

// ---------------------------------------------------------------- bill fields (shared by A and the CA review)
const BILL_FIELDS = {
  vendor_name: F('STRING'), vendor_gstin: F('STRING'), invoice_no: F('STRING'), invoice_date: F('STRING', 'YYYY-MM-DD'),
  taxable_value: F('NUMBER'), cgst: F('NUMBER'), sgst: F('NUMBER'), igst: F('NUMBER'), total: F('NUMBER'),
  irn: F('STRING', 'e-invoice IRN if printed'), description: F('STRING', 'What was bought, in the words on the bill'),
  non_taxable_charges: F('NUMBER', 'Part of the total with no GST on THIS bill, e.g. fare collected on behalf of an airline / IRCTC, reimbursements'),
  eco_pays_tax: F('BOOLEAN', 'true only if the bill says GST is paid by the e-commerce operator under section 9(5)'),
  eco_gstin: F('STRING', 'GSTIN of the e-commerce operator, if printed'),
  handwritten: S('BOOLEAN'), language: S('STRING')
};
const BILL_PROMPT = `Read this purchase bill (it may be printed, handwritten, in Hindi, English or mixed).
Fill each field as a fact. Dates: convert to YYYY-MM-DD; if day and month could be swapped (both 12 or less and nothing else shows the order) mark "uncertain".
Amounts: digits only, no ₹ or commas. If a figure is overwritten, struck out or written twice differently, mark it "uncertain".
"vendor" is the SELLER who issued the bill, not the buyer.
Travel / booking portals often charge GST only on their own fee and collect the fare for another supplier: put that fare in non_taxable_charges exactly as printed; taxable_value is then only the amount GST was charged on.
If the bill says tax is paid by the e-commerce operator (section 9(5), "ECO"), set eco_pays_tax true with the quote as evidence.`;

function checkBill(raw: Raw, ctx: Ctx, today: string) {
  const r = raw ?? {};
  const b = {
    vendor_name: asFact<string>(r.vendor_name), vendor_gstin: checkGstinFact(asFact<string>(r.vendor_gstin)),
    invoice_no: asFact<string>(r.invoice_no), invoice_date: checkDateFact(asFact<string>(r.invoice_date), today),
    taxable_value: checkAmountFact(asFact<number>(r.taxable_value)), cgst: checkAmountFact(asFact<number>(r.cgst)),
    sgst: checkAmountFact(asFact<number>(r.sgst)), igst: checkAmountFact(asFact<number>(r.igst)), total: checkAmountFact(asFact<number>(r.total)),
    irn: asFact<string>(r.irn), description: asFact<string>(r.description),
    non_taxable_charges: checkAmountFact(asFact<number>(r.non_taxable_charges)), eco_pays_tax: asFact<boolean>(r.eco_pays_tax), eco_gstin: checkGstinFact(asFact<string>(r.eco_gstin)),
    handwritten: r.handwritten === true, language: str(r.language)
  };
  if (b.vendor_gstin.value && ctx.buyerGstin && b.vendor_gstin.value === ctx.buyerGstin) doubt(b.vendor_gstin, 'this is your own GSTIN (buyer), not the vendor’s');
  if (b.irn.value && !/^[0-9a-f]{64}$/i.test(String(b.irn.value))) doubt(b.irn, 'an IRN is 64 hexadecimal characters');
  checkTotals({ taxable: b.taxable_value, cgst: b.cgst, sgst: b.sgst, igst: b.igst, total: b.total, other: b.non_taxable_charges });
  if (ctx.sourceText) checkEvidence(b.eco_pays_tax, ctx.sourceText);
  if ((b.cgst.value ?? 0) > 0 && (b.igst.value ?? 0) > 0) [b.cgst, b.igst].forEach((f) => doubt(f, 'both CGST and IGST present'));
  if (b.cgst.value !== null && b.sgst.value !== null && Math.abs(b.cgst.value - b.sgst.value) > 1) [b.cgst, b.sgst].forEach((f) => doubt(f, 'CGST and SGST differ'));
  if (ctx.sourceText) for (const f of [b.vendor_name, b.vendor_gstin, b.invoice_no, b.irn]) checkEvidence(f, ctx.sourceText);
  return b;
}

// ---------------------------------------------------------------- the tasks
export const TASKS: Record<TaskName, TaskDef> = {
  // A — read any bill, including handwritten / Hindi kachcha bills
  read_bill: {
    roles: ALL, files: [1, 1], schema: obj(BILL_FIELDS, Object.keys(BILL_FIELDS)),
    prompt: () => BILL_PROMPT,
    check: (raw, ctx, today) => finish(checkBill(raw, ctx, today))
  },

  // B — Hindi / English voice entry ("पाँच सौ रुपये ऑटो, गोदाम तक, कैश")
  voice_entry: {
    roles: ALL, files: [1, 1],
    schema: obj({
      transcript: S('STRING', { description: 'Exactly what was said, word for word, in the language spoken' }),
      vendor_name: F('STRING'), amount: F('NUMBER'), purpose: F('STRING'),
      pay_mode: F('STRING', 'cash | upi | bank | cheque | card'), paid: F('BOOLEAN', 'true only if the speaker said it is already paid'),
      bill_date: F('STRING', 'YYYY-MM-DD, only if a date or day was said')
    }),
    prompt: (_c, today) => `A small-business staff member describes an expense by voice. Today is ${today}.
Write the transcript word for word. Then fill the facts ONLY from what was said; evidence must quote the spoken words from the transcript.
Hindi "कल / kal" can mean yesterday or tomorrow — always "uncertain". "Parso" likewise. Number words ("paanch sau") → digits.
If a payment mode is not said, pay_mode is not_found. Do not infer a mode from the vendor type.`,
    check: (raw, _c, today) => {
      const t = str(raw?.transcript);
      const out = {
        transcript: t,
        vendor_name: checkEvidence(asFact<string>(raw?.vendor_name), t), amount: checkEvidence(checkAmountFact(asFact<number>(raw?.amount)), t),
        purpose: checkEvidence(asFact<string>(raw?.purpose), t), pay_mode: checkMember(asFact<string>(raw?.pay_mode), ['cash', 'upi', 'bank', 'cheque', 'card'], 'payment mode'),
        paid: checkEvidence(asFact<boolean>(raw?.paid), t), bill_date: checkDateFact(asFact<string>(raw?.bill_date), today)
      };
      if (!t.trim()) return finish(out, ['nothing could be heard']);
      return finish(out);
    }
  },

  // CA review: everything in A plus head, TDS, RCM, 17(5) and red flags — judged only against OUR masters
  analyse_invoice: {
    roles: ADMINS, files: [1, 1],
    schema: obj({
      ...BILL_FIELDS,
      line_items: arr(obj({ description: F('STRING'), hsn_sac: F('STRING'), amount: F('NUMBER'), gst_rate: F('NUMBER') })),
      expense_head: F('STRING', 'One name from the expense head list'),
      tds_code: F('STRING', 'One code from the TDS table, or NONE'),
      rcm_likely: F('BOOLEAN'), blocked_17_5: F('STRING', 'Which 17(5) item, if the bill shows one'),
      red_flags: arr(obj({ flag: S('STRING'), severity: S('STRING', { enum: ['high', 'medium', 'low'] }), evidence: S('STRING') })),
      summary_en: S('STRING'), summary_hi: S('STRING')
    }, ['vendor_name', 'invoice_date', 'total', 'line_items', 'expense_head', 'tds_code', 'red_flags', 'summary_en', 'summary_hi']),
    prompt: (ctx) => `${BILL_PROMPT}
Also: list line items; choose the expense head ONLY from this list: ${JSON.stringify(ctx.heads ?? [])};
choose the TDS code ONLY from this CA-maintained table (or "NONE"): ${JSON.stringify(ctx.tdsTable ?? [])}. Do not decide thresholds — the app calculates them.
red_flags: only visible signs of a fake or altered bill (overwritten figures, totals that don't add up, missing particulars a tax invoice must carry under Rule 46 CGST Rules, GSTIN state not matching the address). Each flag must quote its evidence.`,
    check: (raw, ctx, today) => {
      const b = checkBill(raw, ctx, today);
      const head = checkMember(asFact<string>(raw?.expense_head), ctx.heads ?? [], 'expense head');
      const codes = [...(ctx.tdsTable ?? []).map((r: { code: string }) => r.code), 'NONE'];
      const tds = checkMember(asFact<string>(raw?.tds_code), codes, 'TDS table');
      const items = (Array.isArray(raw?.line_items) ? raw.line_items : []).map((li: Raw) => ({
        description: asFact<string>(li?.description), hsn_sac: asFact<string>(li?.hsn_sac), amount: checkAmountFact(asFact<number>(li?.amount)), gst_rate: asFact<number>(li?.gst_rate)
      }));
      const extra: string[] = [];
      const flags = (Array.isArray(raw?.red_flags) ? raw.red_flags : []).filter((f: Raw) => {
        if (str(f?.evidence).trim()) return true;
        extra.push(`red flag "${str(f?.flag)}" dropped — no evidence quoted`);
        return false;
      });
      // the app — not the AI — compares what was read with what staff recorded
      const rec = ctx.recorded ?? {};
      const mismatches: string[] = [];
      const cmp = (label: string, f: Fact<unknown>, v: unknown) => { if (f.certainty === 'certain' && v !== undefined && v !== null && String(f.value).toLowerCase() !== String(v).toLowerCase()) mismatches.push(`${label}: bill shows ${f.value}, recorded ${v}`); };
      cmp('Bill no.', b.invoice_no, rec.invoice_no); cmp('Bill date', b.invoice_date, rec.invoice_date);
      for (const [k, f] of [['taxable_value', b.taxable_value], ['total', b.total]] as const) if (f.certainty === 'certain' && typeof rec[k] === 'number' && Math.abs((f.value ?? 0) - rec[k]) > 1) mismatches.push(`${k === 'total' ? 'Total' : 'Taxable value'}: bill shows ${f.value}, recorded ${rec[k]}`);
      return finish({ ...b, line_items: items, expense_head: head, tds_code: tds, rcm_likely: asFact<boolean>(raw?.rcm_likely), blocked_17_5: asFact<string>(raw?.blocked_17_5),
        red_flags: flags, mismatches, summary_en: str(raw?.summary_en), summary_hi: str(raw?.summary_hi) }, extra);
    }
  },

  // C — wording of a vendor message for a GSTR-2B mismatch. The mismatch itself is computed by the app (ctx.diffs).
  reco_message: {
    roles: ADMINS, files: [0, 0], schema: obj({ message_en: S('STRING'), message_hi: S('STRING') }),
    prompt: (ctx) => `Write a short, polite WhatsApp message from ${ctx.clientName} to the supplier ${ctx.vendorName} asking them to correct their GST filing.
State ONLY these differences, exactly as given, nothing else: ${JSON.stringify(ctx.diffs)}. Bill reference: ${JSON.stringify(ctx.bill)}.
Do not add reasons, penalties, legal sections or deadlines that are not given. message_en in English. message_hi entirely in simple Hindi (Devanagari) — translate the differences too, keeping every number, date, GSTIN and invoice number exactly as given.`,
    check: (raw, ctx) => {
      const allowed = numbersIn(ctx);
      const extra: string[] = [];
      for (const k of ['message_en', 'message_hi']) { const s = strayNumbers(str(raw?.[k]), allowed); if (s.length) extra.push(`message has numbers not in our records (${s.join(', ')}) — edit before sending`); }
      return finish({ message_en: str(raw?.message_en), message_hi: str(raw?.message_hi) }, extra);
    }
  },

  // D — bank / UPI narration → vendor, only from our vendor list and only with a quote from the narration
  bank_match: {
    roles: ADMINS, files: [0, 0],
    schema: obj({ matches: arr(obj({ row_id: S('STRING'), vendor: F('STRING') })) }),
    prompt: (ctx) => `Match each bank statement row to a vendor from this list ONLY: ${JSON.stringify(ctx.vendors)}.
Rows: ${JSON.stringify(ctx.rows)}. evidence = the exact part of that row's narration that identifies the vendor (name, UPI handle, account).
If no vendor is clearly identified, the vendor fact is not_found. Never match on amount alone.`,
    check: (raw, ctx) => {
      const names = (ctx.vendors ?? []).map((v: { name: string }) => v.name);
      const rows = new Map((ctx.rows ?? []).map((r: { id: string; narration: string }) => [r.id, r.narration]));
      const matches = (Array.isArray(raw?.matches) ? raw.matches : []).filter((m: Raw) => rows.has(str(m?.row_id))).map((m: Raw) => ({
        row_id: str(m.row_id), vendor: checkEvidence(checkMember(asFact<string>(m.vendor), names, 'vendor'), rows.get(str(m.row_id)) as string)
      }));
      return finish({ matches });
    }
  },

  // E — Tally narration from bill facts; any number not in the bill = rejected as hallucination
  narration: {
    roles: ADMINS, files: [0, 0], schema: obj({ narration: S('STRING', { description: 'At most 200 characters' }) }),
    prompt: (ctx) => `Write one Tally voucher narration (max 200 characters, English, accountant style, no emojis) using ONLY these facts: ${JSON.stringify(ctx.bill)}. Do not add anything not given.`,
    check: (raw, ctx) => {
      const n = str(raw?.narration).trim().slice(0, 250);
      const s = strayNumbers(n, numbersIn(ctx));
      return finish({ narration: n }, s.length ? [`narration has numbers not on the bill (${s.join(', ')}) — not used`] : []);
    }
  },

  // F — HSN/SAC and GST rate per line. A code not printed on the bill is always a marked suggestion.
  hsn_suggest: {
    roles: ADMINS, files: [0, 0],
    schema: obj({ items: arr(obj({ index: S('INTEGER'), hsn_sac: F('STRING'), gst_rate: F('NUMBER') })) }),
    prompt: (ctx) => `For each line item give the HSN (goods) or SAC (services) code and GST rate. Bill date ${ctx.date}; valid GST rates on that date: ${JSON.stringify(ctx.allowedRates)}.
Items (answer EVERY item, and copy its "index" exactly): ${JSON.stringify((ctx.items ?? []).map((it: Ctx, index: number) => ({ index, ...it })))}. If an item has a printed code, use it as evidence. If not, you MAY suggest the most likely code and rate from the GST HSN/SAC schedule — this is allowed here; it is automatically marked as a suggestion for a person to verify (rule 7). If you cannot narrow it down, leave the value null.`,
    check: (raw, ctx) => {
      const items = (Array.isArray(raw?.items) ? raw.items : []).filter((it: Raw) => Number.isInteger(it?.index) && ctx.items?.[it.index]).map((it: Raw) => {
        const src = ctx.items[it.index];
        const code = asFact<string>(it.hsn_sac);
        if (code.value !== null) code.value = String(code.value).replace(/\s/g, '');
        if (code.value !== null && !/^\d{4,8}$/.test(code.value)) doubt(code, 'HSN/SAC must be 4–8 digits');
        if (code.value !== null && !(src.printedHsn && String(src.printedHsn).replace(/\s/g, '') === code.value)) doubt(code, 'suggestion — not printed on the bill');
        const rate = asFact<number>(it.gst_rate);
        if (rate.value !== null && !(ctx.allowedRates ?? []).includes(Number(rate.value))) doubt(rate, `not a valid GST rate on ${ctx.date}`);
        if (rate.value !== null && !(src.printedRate !== undefined && Number(src.printedRate) === Number(rate.value))) doubt(rate, 'suggestion — not printed on the bill');
        return { index: it.index, hsn_sac: code, gst_rate: rate };
      });
      // every line we asked about must be answered — a skipped line is reported, never silently dropped
      const missing = (ctx.items ?? []).map((_: unknown, i: number) => i).filter((i: number) => !items.some((x: { index: number }) => x.index === i));
      return finish({ items }, missing.map((i: number) => `line ${i + 1} was not answered`));
    }
  },

  // G — ask your data: AI only translates the question into one of our fixed queries; the app computes the answer
  ask_data: {
    roles: ADMINS, files: [0, 0],
    schema: obj({
      query: S('STRING', { enum: ['spend_total', 'top_vendors', 'dues', 'tds_total', 'itc_total', 'payments_total', 'bill_count', 'unanswerable'] }),
      period: F('STRING', 'One period name from the list, or "custom"'), from: F('STRING', 'YYYY-MM-DD, only for custom'), to: F('STRING', 'YYYY-MM-DD, only for custom'), head: F('STRING'), centre: F('STRING'), vendor: F('STRING'),
      mode: F('STRING', 'cash | upi | bank | cheque | card'), understood_en: S('STRING'), understood_hi: S('STRING')
    }),
    prompt: (ctx, today) => `Translate the question into ONE query with filters. Today is ${today}. For the period, give its NAME from this list worked out by the app: ${JSON.stringify(Object.keys(periodsFor(today)))} — evidence = the words in the question. Use "custom" with from/to only for a period not in the list (e.g. a named month). Indian FY quarters and calendar quarters share the same boundaries.
Question: ${JSON.stringify(ctx.question)}. Expense heads: ${JSON.stringify(ctx.heads)}. Projects/branches: ${JSON.stringify(ctx.centres)}. Vendors: ${JSON.stringify(ctx.vendors)}.
Filters not mentioned are not_found. If the question names a period not in that list (e.g. a specific month), give its exact dates. If the period is unclear, mark it "uncertain".
If the question cannot be answered by these queries, use "unanswerable". Do NOT answer the question yourself and do not produce any figures.
understood_en / understood_hi: one line restating how you read the question; understood_hi in Hindi (Devanagari script).`,
    check: (raw, ctx, today) => {
      const q = str(raw?.query);
      const out = {
        query: ['spend_total', 'top_vendors', 'dues', 'tds_total', 'itc_total', 'payments_total', 'bill_count'].includes(q) ? q : 'unanswerable',
        from: checkDateFact(asFact<string>(raw?.from), today), to: asFact<string>(raw?.to),
        head: checkMember(asFact<string>(raw?.head), ctx.heads ?? [], 'expense head'), centre: checkMember(asFact<string>(raw?.centre), ctx.centres ?? [], 'project / branch'),
        vendor: checkMember(asFact<string>(raw?.vendor), ctx.vendors ?? [], 'vendor'), mode: checkMember(asFact<string>(raw?.mode), ['cash', 'upi', 'bank', 'cheque', 'card'], 'payment mode'),
        understood_en: str(raw?.understood_en), understood_hi: str(raw?.understood_hi)
      };
      if (out.to.value && !/^\d{4}-\d{2}-\d{2}$/.test(String(out.to.value))) doubt(out.to, 'not a date');
      if (out.from.value && out.to.value && out.from.value > out.to.value) [out.from, out.to].forEach((f) => doubt(f, 'from is after to'));
      // period: AI names it, the APP supplies the dates; the name must agree with the words used ("this" vs "last")
      const periods = periodsFor(today);
      const period = asFact<string>(raw?.period);
      if (period.value && period.value !== 'custom') {
        const p = periods[String(period.value)];
        if (!p) { doubt(period, 'not one of the standard periods — check the dates'); }
        else {
          const ev = period.evidence.toLowerCase();
          const saysLast = /\b(last|previous|pichl|pichhl)|पिछ/.test(ev), saysThis = /\b(this|current)\b|\bis\s|इस\s/.test(ev);
          if ((saysLast && String(period.value).startsWith('this_')) || (saysThis && !saysLast && String(period.value).startsWith('last_'))) doubt(period, 'period name does not match the words in the question');
          out.from = { value: p.from, certainty: period.certainty, evidence: period.evidence, note: period.note };
          out.to = { value: p.to, certainty: period.certainty, evidence: period.evidence, note: period.note };
        }
      } else if (out.from.value && out.to.value && !Object.values(periods).some((p) => p.from === out.from.value && p.to === out.to.value) && out.from.certainty === 'certain') {
        // custom dates: keep, but they were computed by AI — a person confirms
        [out.from, out.to].forEach((f) => doubt(f, 'dates worked out by AI — check them'));
      }
      return finish({ ...out, period }, /\d{3,}/.test(out.understood_en.replace(/\d{4}-\d{2}-\d{2}/g, '')) ? ['restatement contained figures — ignored'] : []);
    }
  },

  // H — MIS commentary: AI may only reference our figures by {key}; the app inserts the numbers
  mis_commentary: {
    roles: ADMINS, files: [0, 0],
    schema: obj({ points: arr(obj({ text_en: S('STRING'), text_hi: S('STRING') })) }),
    prompt: (ctx) => `Write 3 to 5 short observations for a business owner about these figures: ${JSON.stringify(ctx.figures)}.
Refer to a figure ONLY as {key} (e.g. "Spend this month is {thisMonth}"). Never write any digit yourself. Do not give reasons you cannot see in the figures; do not predict. In Hindi use plain accounting words: expense head = खर्च मद, payable = देय, ITC = ITC, TDS = TDS.`,
    check: (raw, ctx) => {
      const keys = Object.keys(ctx.figures ?? {});
      const extra: string[] = [];
      const points = (Array.isArray(raw?.points) ? raw.points : []).filter((p: Raw) => {
        for (const t of [str(p?.text_en), str(p?.text_hi)]) {
          const bad = (t.match(/\{(\w+)\}/g) ?? []).map((m) => m.slice(1, -1)).filter((k) => !keys.includes(k));
          const bare = t.replace(/\{\w+\}/g, '');
          if (bad.length || /[0-9०-९]/.test(bare)) { extra.push(`dropped a point with ${bad.length ? `unknown figure(s) ${bad.join(', ')}` : 'numbers not taken from the figures'}`); return false; }
        }
        return true;
      }).map((p: Raw) => ({ text_en: str(p.text_en), text_hi: str(p.text_hi) }));
      return finish({ points }, extra);
    }
  },

  // I — GST / income-tax notice reader: every point must quote the notice
  notice_summary: {
    roles: ['super_admin'], files: [1, 1],
    schema: obj({
      issuer: F('STRING'), notice_type: F('STRING'), reference_no: F('STRING'), notice_date: F('STRING', 'YYYY-MM-DD'),
      reply_due_date: F('STRING', 'YYYY-MM-DD'), period: F('STRING'), amount_demanded: F('NUMBER'),
      sections_cited: arr(F('STRING')), actions: arr(obj({ action: S('STRING'), evidence: S('STRING') })),
      summary_en: S('STRING'), summary_hi: S('STRING')
    }, ['issuer', 'notice_type', 'notice_date', 'reply_due_date', 'sections_cited', 'actions', 'summary_en', 'summary_hi']),
    prompt: () => `This is a notice from a tax authority (GST or Income-tax). Extract the facts. sections_cited: only sections printed in the notice.
actions: only what the notice itself asks for, each with the exact sentence as evidence. Do not give legal advice or opinions.`,
    check: (raw, ctx, today) => {
      const src = ctx.sourceText as string | undefined;
      const due = asFact<string>(raw?.reply_due_date);
      checkDateFact(due, '9999-12-31');
      const extra: string[] = [];
      const actions = (Array.isArray(raw?.actions) ? raw.actions : []).filter((a: Raw) => {
        const ev = str(a?.evidence).trim();
        if (!ev) { extra.push(`action "${str(a?.action)}" dropped — no quote from the notice`); return false; }
        if (src && !src.toLowerCase().replace(/\s+/g, ' ').includes(ev.toLowerCase().replace(/\s+/g, ' ').slice(0, 60))) extra.push(`quote for action "${str(a?.action)}" not found in the PDF text — check`);
        return true;
      });
      const out = {
        issuer: checkEvidence(asFact<string>(raw?.issuer), src), notice_type: asFact<string>(raw?.notice_type), reference_no: checkEvidence(asFact<string>(raw?.reference_no), src),
        notice_date: checkDateFact(asFact<string>(raw?.notice_date), today), reply_due_date: due, period: asFact<string>(raw?.period),
        amount_demanded: checkAmountFact(asFact<number>(raw?.amount_demanded)),
        sections_cited: (Array.isArray(raw?.sections_cited) ? raw.sections_cited : []).map((s: Raw) => checkEvidence(asFact<string>(s), src)),
        actions, summary_en: str(raw?.summary_en), summary_hi: str(raw?.summary_hi)
      };
      return finish(out, extra);
    }
  },

  // J — are these two photos the same physical bill? "same" needs evidence on both sides, otherwise "unsure"
  compare_bills: {
    roles: ADMINS, files: [2, 2],
    schema: obj({
      verdict: S('STRING', { enum: ['same', 'different', 'unsure'] }),
      same_points: arr(obj({ point: S('STRING'), evidence_a: S('STRING'), evidence_b: S('STRING') })),
      different_points: arr(obj({ point: S('STRING'), evidence_a: S('STRING'), evidence_b: S('STRING') })), note: S('STRING')
    }),
    prompt: () => `Image A and image B are photos or scans of bills. Are they the SAME physical bill (e.g. photographed twice)? Compare bill number, date, seller, amounts, handwriting, stamps and marks.
Every point must quote what is visible in A and in B. If unsure, say "unsure".`,
    check: (raw) => {
      const pts = (k: string) => (Array.isArray(raw?.[k]) ? raw[k] : []).filter((p: Raw) => str(p?.evidence_a).trim() && str(p?.evidence_b).trim());
      const same = pts('same_points'), diff = pts('different_points');
      let verdict = ['same', 'different', 'unsure'].includes(raw?.verdict) ? raw.verdict : 'unsure';
      const extra: string[] = [];
      if (verdict === 'same' && (same.length < 2 || diff.length)) { verdict = 'unsure'; extra.push('"same" needs at least two matching points with evidence and no differences'); }
      if (verdict === 'different' && !diff.length) { verdict = 'unsure'; extra.push('"different" given without a quoted difference'); }
      if (verdict === 'unsure') extra.push('AI could not decide — compare the two bills yourself');
      return finish({ verdict, same_points: same, different_points: diff, note: str(raw?.note) }, extra);
    }
  },

  // Rule-change scan with Google Search (CA firm). Unofficial or incomplete items are marked.
  norms_scan: {
    roles: ['super_admin'], files: [0, 0], search: true,
    prompt: (ctx) => `Search official Indian government sources (incometax.gov.in, cbic.gov.in, gst.gov.in, egazette.gov.in) for changes notified on or after ${ctx.since}
that affect a business recording purchase bills: TDS rates or thresholds under the Income-tax Act 2025 (our table: ${JSON.stringify(ctx.tdsTable ?? [])}), GST rates or slabs,
e-invoicing thresholds, ITC / RCM rules, return or payment due dates.
Reply with ONLY a JSON array: [{"area":"tds|gst|einvoice|due_dates","title":"...","detail":"what changed","notification_no":"...","effective_date":"YYYY-MM-DD","source_url":"..."}].
Use "" for anything you could not find. Empty array if nothing changed.`,
    check: (raw, _c, _t, out) => {
      const official = /(^|\.)(gov\.in|nic\.in)$/;
      const cited = new Set(out.sources.map((s) => s.uri));
      const items = (Array.isArray(raw) ? raw : []).map((it: Raw) => {
        let host = '';
        try { host = new URL(str(it?.source_url)).hostname; } catch { /* none */ }
        const problems = [
          !official.test(host) && 'source is not a government website',
          !str(it?.notification_no) && 'no notification number',
          !/^\d{4}-\d{2}-\d{2}$/.test(str(it?.effective_date)) && 'no effective date',
          cited.size > 0 && !cited.has(str(it?.source_url)) && 'URL not among the pages the search actually returned'
        ].filter(Boolean) as string[];
        return { area: str(it?.area), title: str(it?.title), detail: str(it?.detail), notification_no: str(it?.notification_no), effective_date: str(it?.effective_date), source_url: str(it?.source_url), verified: !problems.length, problems };
      });
      return finish({ items, sources: out.sources }, items.filter((i: { verified: boolean }) => !i.verified).map((i: { title: string; problems: string[] }) => `${i.title}: ${i.problems.join('; ')}`));
    }
  }
};

/** Standard periods computed by code (never by AI). Indian FY: April–March. */
export function periodsFor(today: string): Record<string, { from: string; to: string }> {
  const [y, m] = [Number(today.slice(0, 4)), Number(today.slice(5, 7))];
  const iso = (yy: number, mm: number, dd: number) => new Date(Date.UTC(yy, mm - 1, dd)).toISOString().slice(0, 10);
  const end = (yy: number, mm: number) => iso(yy, mm + 1, 0);
  const qStart = m - ((m - 1) % 3);
  const fy = m >= 4 ? y : y - 1;
  const lm = m === 1 ? [y - 1, 12] : [y, m - 1];
  const lq = qStart === 1 ? [y - 1, 10] : [y, qStart - 3];
  return {
    today: { from: today, to: today },
    this_month: { from: iso(y, m, 1), to: end(y, m) }, last_month: { from: iso(lm[0], lm[1], 1), to: end(lm[0], lm[1]) },
    this_quarter: { from: iso(y, qStart, 1), to: end(y, qStart + 2) }, last_quarter: { from: iso(lq[0], lq[1], 1), to: end(lq[0], lq[1] + 2) },
    this_financial_year: { from: iso(fy, 4, 1), to: iso(fy + 1, 3, 31) }, last_financial_year: { from: iso(fy - 1, 4, 1), to: iso(fy, 3, 31) }
  };
}

/** Every number that legitimately appears in a task's input (amounts, bill no. digits, date parts). */
function numbersIn(ctx: Ctx): number[] {
  const out: number[] = [];
  JSON.stringify(ctx).replace(/\d+(?:\.\d+)?/g, (m) => { out.push(Number(m)); return m; });
  return out;
}

/** Reading images / audio / searching needs the stronger model; text-only tasks use the fast one.
 *  Measured 2 Nov 2026 on a free-tier key: gemini-3.8-flash ~35–60 s per call, gemini-3.5-flash-lite ~1.5 s. */
export const HEAVY_TASKS: TaskName[] = ['read_bill', 'voice_entry', 'analyse_invoice', 'notice_summary', 'compare_bills', 'norms_scan'];
export interface Models { heavy: string; fast: string }
export const DEFAULT_MODELS: Models = { heavy: 'gemini-3.8-flash', fast: 'gemini-3.5-flash-lite' };
export const modelFor = (task: TaskName, m: Models) => (HEAVY_TASKS.includes(task) ? m.heavy : m.fast);

export const MAX_INLINE_BYTES = 14 * 1024 * 1024; // Gemini: max 20 MB per request incl. base64 overhead
export interface TaskResult extends Checked<unknown> { model: string; inTok?: number; outTok?: number }

export async function runTask(key: string, models: Models, task: TaskName, ctx: Ctx, files: InlineFile[], today: string): Promise<TaskResult> {
  const def = TASKS[task];
  const model = modelFor(task, models);
  if (!def) throw new Error('Unknown task');
  if (files.length < def.files[0] || files.length > def.files[1]) throw new Error('Wrong number of files for this task');
  const bytes = files.reduce((s, f) => s + Math.floor((f.data.length * 3) / 4), 0);
  if (bytes > MAX_INLINE_BYTES) throw new Error('Files too large for AI (max 14 MB)');
  const parts: Part[] = [{ text: `${TRUTH_RULES}\n\nTASK:\n${def.prompt(ctx, today)}` }, ...files.map((f) => ({ inline_data: { mime_type: f.mime, data: f.data } }))];
  const out = await callGemini(key, model, parts, { schema: def.schema, search: def.search, timeoutMs: HEAVY_TASKS.includes(task) ? 180000 : 60000 });
  if (out.finish && out.finish !== 'STOP') throw new Error(`AI answer incomplete (${out.finish}) — nothing used`);
  const raw = def.search ? parseJson<unknown>(out.text.slice(out.text.indexOf('['), out.text.lastIndexOf(']') + 1) || '[]') : parseJson<unknown>(out.text);
  return { ...def.check(raw, ctx, today, out), model, inTok: out.inTok, outTok: out.outTok };
}
