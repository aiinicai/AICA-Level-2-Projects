import * as XLSX from 'xlsx';
import { DueCategory, InvType, Kind, RecType } from '../types';
import {
  CATS,
  DEF_ALERTS,
  fmtD,
  INV,
  REC,
  todayIST,
} from './calculations';

declare global {
  interface Window {
    Tesseract?: any;
    pdfjsLib?: any;
    mammoth?: any;
    XLSX?: any;
  }
}

const MONTHS: Record<string, number> = {
  jan: 1,
  feb: 2,
  mar: 3,
  apr: 4,
  may: 5,
  jun: 6,
  jul: 7,
  aug: 8,
  sep: 9,
  oct: 10,
  nov: 11,
  dec: 12,
};

export function isoDate(d: number | string, m: number | string, y: number | string): string | null {
  let yr = +y;
  if (yr < 100) yr += 2000;
  const day = +d;
  const mon = +m;
  if (mon < 1 || mon > 12 || day < 1 || day > 31 || yr < 1900 || yr > 2100) return null;
  const t = Date.UTC(yr, mon - 1, day);
  return new Date(t).getUTCDate() === day ? fmtD(t) : null;
}

export function toIso(v: any): string {
  if (v == null || v === '') return '';
  if (Object.prototype.toString.call(v) === '[object Date]') {
    if (isNaN(v)) return '';
    const t = new Date(v.getTime() + 12 * 3600e3);
    return fmtD(Date.UTC(t.getFullYear(), t.getMonth(), t.getDate()));
  }
  if (typeof v === 'number') {
    return v > 20000 && v < 80000
      ? fmtD(Date.UTC(1899, 11, 30) + Math.round(v) * 86400000)
      : '';
  }
  const s = String(v).trim();
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return isoDate(m[3], m[2], m[1]) || '';
  m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})/);
  if (m) return isoDate(m[1], m[2], m[3]) || '';
  m = s.match(/^(\d{1,2})(?:st|nd|rd|th)?[\s\-]+([A-Za-z]{3})[a-z]*\.?[\s\-,]+(\d{2,4})/);
  if (m) return isoDate(m[1], MONTHS[m[2].toLowerCase()], m[3]) || '';
  return '';
}

export function guessInvType(s: string): InvType {
  const low = String(s || '').toLowerCase();
  const R: [InvType, RegExp][] = [
    ['gold', /(sovereign gold|sgb|gold|silver)/],
    ['rd', /(recurring|\brd\b)/],
    [
      'fd',
      /(fixed deposit|term deposit|\bfdr?\b|deposit receipt|deposit (?:confirmation|advice|no|number|amount)|depositor)/,
    ],
    ['bond', /(bond|debenture|\bncd\b|g-?sec|gilt|t-bill|treasury)/],
    ['mf', /(mutual fund|\bmf\b|\bsip\b|\bnav\b|\belss\b|scheme|\bamc\b|folio)/],
    ['stocks', /(shares?\b|stocks?\b|equity|demat|\bnse\b|\bbse\b)/],
    ['ppf', /(\bppf\b|\bepf\b|provident|\bssy\b|sukanya)/],
    ['nps', /(\bnps\b|pension)/],
    ['property', /(property|land|flat|plot|real estate)/],
    ['insurance', /(ulip|endowment|insurance|policy)/],
  ];
  return (R.find(([, re]) => re.test(low)) || ['other'])[0];
}

export function guessCat(s: string): DueCategory {
  const low = String(s || '').toLowerCase();
  const R: [DueCategory, RegExp][] = [
    ['lpg', /(lpg|cylinder|gas)/],
    ['mediclaim', /(mediclaim|health)/],
    ['vehicle', /(motor|vehicle|two.?wheeler|car insurance)/],
    ['fd', /(fixed deposit|\bfdr?\b|maturity)/],
    ['emi', /(\bemi\b|loan|instal)/],
    ['insurance', /(insurance|policy|premium|life)/],
    ['utility', /(electric|water|bill|meter)/],
  ];
  return (R.find(([, re]) => re.test(low)) || ['utility'])[0];
}

export function guessRecType(s: string): RecType {
  const low = String(s || '').toLowerCase();
  const R: [RecType, RegExp][] = [
    ['passport', /passport/],
    ['licence', /(licen[cs]e|\bdl\b)/],
    ['vehicle', /(registration|vehicle|\brc\b|\bpuc\b|fitness)/],
    ['policy', /(policy|insurance|premium)/],
    ['bank', /(bank|account|ifsc)/],
    ['nominee', /nominee/],
    ['contact', /(contact|phone|mobile)/],
    ['id', /(aadhaar|aadhar|\bpan\b|voter|identity|\bid\b)/],
  ];
  return (R.find(([, re]) => re.test(low)) || ['other'])[0];
}

export function collectDates(txt: string) {
  const d: { v: string; i: number; len: number }[] = [];
  for (const m of txt.matchAll(/\b(\d{4})-(\d{2})-(\d{2})\b/g)) {
    const v = isoDate(m[3], m[2], m[1]);
    if (v && m.index !== undefined) d.push({ v, i: m.index, len: m[0].length });
  }
  for (const m of txt.matchAll(/\b(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})\b/g)) {
    const v = isoDate(m[1], m[2], m[3]);
    if (v && m.index !== undefined) d.push({ v, i: m.index, len: m[0].length });
  }
  for (const m of txt.matchAll(
    /\b(\d{1,2})(?:st|nd|rd|th)?[\s\-]+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?[\s\-,]+(\d{2,4})\b/gi
  )) {
    const v = isoDate(m[1], MONTHS[m[2].toLowerCase()], m[3]);
    if (v && m.index !== undefined) d.push({ v, i: m.index, len: m[0].length });
  }
  return d.sort((a, b) => a.i - b.i);
}

export function labelDates(txt: string, defs: Record<string, RegExp>) {
  const low = txt.toLowerCase();
  const labs: { k: string; i: number; end: number }[] = [];
  for (const [k, re] of Object.entries(defs)) {
    for (const m of low.matchAll(new RegExp(re.source, 'g'))) {
      if (m.index !== undefined) {
        labs.push({ k, i: m.index, end: m.index + m[0].length });
      }
    }
  }
  labs.sort((a, b) => a.i - b.i || b.end - b.i - (a.end - a.i));
  const kept: { k: string; i: number; end: number }[] = [];
  let last = -1;
  for (const l of labs) {
    if (l.i >= last) {
      kept.push(l);
      last = l.end;
    }
  }

  const all = collectDates(txt).map((d) => ({ ...d, key: '' }));
  const by: Record<string, string> = {};
  let li = 0;
  let pend: { k: string; i: number; end: number }[] = [];

  all.forEach((d, idx) => {
    while (li < kept.length && kept[li].end <= d.i) {
      if (d.i - kept[li].end <= 220) pend.push(kept[li]);
      li++;
    }
    let n = 1;
    for (let j = idx + 1; j < all.length; j++) {
      if (kept.some((l) => l.i > all[j - 1].i && l.end <= all[j].i)) break;
      n++;
    }
    let lab: { k: string; i: number; end: number } | null = null;
    if (pend.length === 1) lab = pend.pop()!;
    else if (pend.length > 1 && n >= pend.length) lab = pend.shift()!;
    else if (pend.length > 1) {
      lab = pend[pend.length - 1];
      pend = [];
    }
    if (lab) {
      d.key = lab.k;
      if (!by[lab.k]) by[lab.k] = d.v;
    }
  });

  return { by, all };
}

const TITLE_RE = /^(mr|mrs|ms|miss|shri|smt|sri|dr|kumari|master|m\/s|late)(?:\.\s*|\s+)/i;
export const titleCase = (s: string): string =>
  /[a-z]/.test(s) ? s : s.toLowerCase().replace(/\b[a-z]/g, (c) => c.toUpperCase());
const NAME_BAD = /\b(bank|branch|account|number|date|limited|ltd|fund|deposit|scheme|policy|insurance|passport|republic|india|licen[cs]e|receipt|certificate|name|interest|payout|maturity|period|tenure|rate|customer|type|status|tds|remarks|nominee|registered|renewal|instruction|advice|confirmation|amount|holder|address|details|signature|authorised|authorized|page|dear|sir|madam)\b/i;

export function cleanName(v: any): string {
  let val = String(v || '').replace(/[|_]/g, ' ').trim();
  val = val.split(/\s{2,}|\t/)[0].trim();
  val = val
    .replace(
      /\s+(date|dob|d\.o\.b|age|sex|gender|pan|aadhaar|account|a\/c|branch|address|mobile|phone|customer|cust|nominee|deposit|maturity|rate|amount|principal|interest|fd|fdr|policy|passport|licen[cs]e|number|issue|expiry|valid|rs|inr|plan|scheme|folio|ifsc|given|surname|name|place|period|tenure|id)\b.*$/i,
      ''
    )
    .trim();
  val = val.replace(/[^A-Za-z]+$/, '').trim();
  if (!/^[A-Za-z][A-Za-z .'\-&]{1,90}$/.test(val)) return '';
  const parts = val
    .split(/\s*(?:&|\band\b|\/)\s*/i)
    .map((p) => p.replace(TITLE_RE, '').trim())
    .filter(Boolean);
  if (!parts.length || parts.length > 3 || parts.some((p) => p.length < 2 || NAME_BAD.test(p)))
    return '';
  return parts.map(titleCase).join(' & ');
}

export function findName(raw: string, labels: string[]): string {
  const lines = String(raw || '').split(/\r?\n/);
  for (const lab of labels) {
    const anchored = lab[0] === '^';
    const src = anchored ? lab.slice(1) : lab;
    const re = new RegExp(
      (anchored ? '^\\s*' : '\\b') +
        '(?:' +
        src +
        ')(?:\\s+name)?(?:\\(s\\))?(?![A-Za-z])\\s*[:\\-–.]*\\s*(.*)$',
      'i'
    );
    for (let i = 0; i < lines.length; i++) {
      if (
        /(joint|nominee|guardian|father|mother|spouse|husband)/i.test(lines[i]) &&
        !/(joint|nominee)/.test(src)
      )
        continue;
      const m = lines[i].match(re);
      if (!m) continue;
      const rest = m[1].trim();
      let n = cleanName(rest);
      if (!n && !/\d/.test(rest) && /^[\/:\-–|,.\s]*[A-Za-zÀ-ſ()\/ ]{0,24}$/.test(rest)) {
        for (let j = i + 1; !n && j <= i + 2 && j < lines.length; j++) {
          if (lines[j].trim()) n = cleanName(lines[j]);
        }
      }
      if (n) return n;
    }
  }
  return '';
}

export const salutation = (raw: string): string => {
  const m = String(raw || '').match(
    /\bdear\s+((?:mr|mrs|ms|shri|smt|dr)\.?\s+)?([A-Za-z][A-Za-z .'\-]{2,40}?)\s*[,:\n]/i
  );
  return m ? cleanName(m[2]) : '';
};

export const addressee = (raw: string): string => {
  const L = String(raw || '')
    .split(/\r?\n/)
    .map((x) => x.trim());
  for (let i = 0; i < L.length - 1; i++) {
    if (/^to[,:]?$/i.test(L[i])) {
      const n = cleanName(L[i + 1]);
      if (n) return n;
    }
  }
  return '';
};

const INV_NAME_LABELS = [
  'name of the depositor',
  'name of depositor',
  "depositor'?s",
  'depositor',
  'name of the deposit holder',
  'deposit holder',
  'name of the investor',
  'name of investor',
  'investor',
  'name of the account holder',
  'account holder',
  'a\\/c holder',
  'first holder',
  '1st holder',
  'primary holder',
  'sole holder',
  'name of the customer',
  'name of customer',
  'customer',
  'name of the applicant',
  'applicant',
  'account name',
  'in the name of',
  'holder',
  '^name',
];

const REC_NAME_LABELS = [
  'name of the holder',
  'name of holder',
  'holder',
  'cardholder',
  'card holder',
  '^full name',
  '^name',
];

const DUE_NAME_LABELS = [
  'name of the policyholder',
  'policyholder',
  'policy holder',
  'name of the insured',
  'insured',
  'account holder',
  'consumer name',
  'customer',
  'borrower',
  '^name',
];

const INV_DEFS = {
  start: /(deposit date|date of deposit|value date|opening date|date of opening|start date|purchase date|date of purchase|commencement date|date of commencement|investment date|date of investment|issue date|date of issue|allotment date|date of allotment|effective date|जारी करने की तारीख)/i,
  maturity: /(maturity date|date of maturity|matures on|maturing on|maturity\s*[:\-]|due on|due date|renewal date|redemption date|date of redemption|redeemed on|valid till|valid upto|period.*to|परिपक्वता की तारीख)/i,
};

const REC_DEFS = {
  issued: /(date of issue|issue date|issued on|date of issuance|issued)/,
  expires: /(date of expiry|expiry date|date of expiration|expiration date|expires on|expires|expiry|expiration|valid until|valid till|valid upto|valid up to|validity|renewal date|renew by|due date)/,
  birth: /(date of birth|d\.?o\.?b\.?|born on|birth date)/,
};

const NUM_DEFS = {
  amount: /\b(?:deposit amount|amount of deposit|amount deposited|deposited amount|principal amount|principal|investment amount|amount invested|invested amount|amount)\b/,
  rate: /\b(?:rate of interest|interest rate|rate p\.?\s?a\.?|roi|rate)\b/,
  matamt: /\b(?:maturity amount|maturity value|amount at maturity|maturity proceeds|payable at maturity|maturity payout)\b/,
};

export function numTokens(txt: string, dates: { i: number; len: number }[]) {
  const out: {
    v: number;
    i: number;
    end: number;
    cur: boolean;
    pct: boolean;
    grouped: boolean;
    key: string;
  }[] = [];

  for (const m of txt.matchAll(
    /(?<![A-Za-z0-9\/\-.,])((?:rs\.?|inr|₹)\s*)?(\d[\d,]*(?:\.\d+)?)(\s*(?:%|per\s?cent))?(?![A-Za-z0-9\/\-])/gi
  )) {
    if (m.index === undefined) continue;
    const i = m.index + (m[1] ? m[1].length : 0);
    const end = m.index + m[0].length;
    if (dates.some((d) => i < d.i + d.len && end > d.i)) continue;
    const raw = m[2].replace(/,/g, '');
    if (raw.replace('.', '').length >= 10) continue;
    const v = parseFloat(raw);
    if (!(v >= 0)) continue;
    out.push({
      v,
      i: m.index,
      end,
      cur: !!m[1],
      pct: !!m[3],
      grouped: /,/.test(m[2]) || /\.\d{2}$/.test(m[2]),
      key: '',
    });
  }
  return out;
}

export function labelNumbers(txt: string) {
  const low = txt.toLowerCase();
  const labs: { k: string; i: number; end: number }[] = [];
  for (const [k, re] of Object.entries(NUM_DEFS)) {
    for (const m of low.matchAll(new RegExp(re.source, 'g'))) {
      if (m.index !== undefined) {
        labs.push({ k, i: m.index, end: m.index + m[0].length });
      }
    }
  }
  labs.sort((a, b) => a.i - b.i || b.end - b.i - (a.end - a.i));
  const kept: { k: string; i: number; end: number }[] = [];
  let last = -1;
  for (const l of labs) {
    if (l.i >= last) {
      kept.push(l);
      last = l.end;
    }
  }

  const toks = numTokens(txt, collectDates(txt));
  const by: Record<string, number> = {};
  let li = 0;
  let pend: { k: string; i: number; end: number }[] = [];

  toks.forEach((t, idx) => {
    while (li < kept.length && kept[li].end <= t.i) {
      if (t.i - kept[li].end <= 220) pend.push(kept[li]);
      li++;
    }
    let n = 1;
    for (let j = idx + 1; j < toks.length; j++) {
      if (kept.some((l) => l.i > toks[j - 1].i && l.end <= toks[j].i)) break;
      n++;
    }
    let lab: { k: string; i: number; end: number } | null = null;
    if (pend.length === 1) lab = pend.pop()!;
    else if (pend.length > 1 && n >= pend.length) lab = pend.shift()!;
    else if (pend.length > 1) {
      lab = pend[pend.length - 1];
      pend = [];
    }
    if (lab) {
      t.key = lab.k;
      if (!(lab.k in by)) by[lab.k] = t.v;
    }
  });

  return { by, toks, low };
}

const ci = (w: string) =>
  w.replace(/[a-z]/gi, (c) => '[' + c.toLowerCase() + c.toUpperCase() + ']');
const BANK_RE = new RegExp(
  "((?:The\\s+)?(?:[A-Z][A-Za-z&.'\\-]*\\s+){0,4}?(?:" +
    [
      ci('Small Finance Bank'),
      ci('Bank') + '\\s+' + ci('of') + '\\s+[A-Z][A-Za-z]+',
      ci('Co-operative Bank'),
      ci('Bank'),
      ci('Finance'),
      ci('Securities'),
      ci('Mutual Fund'),
      'AMC',
      ci('Post Office'),
    ].join('|') +
    ')(?:\\s+(?:' +
    [
      ci('Limited'),
      ci('Ltd') + '\\.?',
      ci('Pvt') + '\\.?\\s*' + ci('Ltd') + '\\.?',
      ci('Private Limited'),
    ].join('|') +
    '))?)',
  'g'
);

export function bankName(raw: string): string {
  const low = String(raw || '').toLowerCase();
  if (low.includes('kerala gramin bank') || low.includes('കേരള ഗ്രാമീൺ ബാങ്ക്') || low.includes('gramin bank')) {
    return 'Kerala Gramin Bank';
  }
  if (
    low.includes('state bank of india') ||
    low.includes('भारतीय स्टेट बैंक') ||
    /\bsbi\b/i.test(low)
  ) {
    return 'State Bank of India';
  }
  if (low.includes('canara bank')) {
    return 'Canara Bank';
  }
  if (low.includes('hdfc')) {
    return 'HDFC Bank';
  }
  if (low.includes('icici')) {
    return 'ICICI Bank';
  }
  if (low.includes('punjab national bank') || /\bpnb\b/i.test(low)) {
    return 'Punjab National Bank';
  }
  if (low.includes('bank of baroda') || /\bbob\b/i.test(low)) {
    return 'Bank of Baroda';
  }

  const lines = String(raw || '').split(/\r?\n/).slice(0, 16);
  for (const line of lines) {
    for (const m of line.matchAll(BANK_RE)) {
      const v = m[1].trim();
      if (
        v.length >= 4 &&
        v.length <= 60 &&
        !/^(customer|account|beneficiary|your|our|savings|current|payout|nominee|branch|deposit|fixed|recurring|bank$)/i.test(
          v
        )
      ) {
        return /[a-z]/.test(v) ? v : titleCase(v);
      }
    }
  }
  return '';
}

export function parseDoc(raw: string): Record<string, any> {
  const txt = String(raw || '').replace(/[|]/g, ' ').replace(/[ \t]+/g, ' ');
  const low = txt.toLowerCase();

  const ld = labelDates(txt, {
    due: /(due date|date of due|next due date|next due|premium due|payment due|payable by|pay by|last date|due on|renewal date|renew on|expiry date|date of expiry|expires on|expiry|valid till|valid upto|maturity date|maturity)/,
    other: /(bill date|invoice date|statement date|issue date|date of issue|policy start date|start date|from date|reading date|generated on|issued on)/,
  });
  const t0 = todayIST();
  let due = ld.by.due || '';
  if (!due) {
    const cand = ld.all.filter((d) => d.key !== 'other');
    const fut = cand.filter((d) => d.v >= t0);
    const pool = fut.length ? fut : cand;
    if (pool.length) {
      const s = pool.map((d) => d.v).sort();
      due = fut.length ? s[0] : s[s.length - 1];
    }
  }

  const amts = [...txt.matchAll(/(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)/gi)]
    .map((m) => ({ v: parseFloat(m[1].replace(/,/g, '')), i: m.index ?? 0 }))
    .filter((a) => a.v > 0);
  const kamt = amts.filter((a) =>
    /(amount|premium|payable|total|emi|due)/.test(low.slice(Math.max(0, a.i - 30), a.i + 3))
  );
  const amount = kamt.length ? kamt[0].v : amts.length ? Math.max(...amts.map((a) => a.v)) : '';

  const rules: [DueCategory, RegExp][] = [
    ['lpg', /(lpg|cylinder|gas agency|indane|bharatgas|hp gas)/],
    ['mediclaim', /(mediclaim|health insurance|health policy|cashless)/],
    ['vehicle', /(motor|vehicle|two.?wheeler|private car|car insurance|registration no)/],
    ['fd', /(fixed deposit|\bfdr?\b|maturity|deposit receipt)/],
    ['emi', /(\bemi\b|loan account|installment|instalment)/],
    ['insurance', /(insurance|policy|premium|life)/],
    ['utility', /(electricity|water|kwh|consumer no|bill|meter)/],
  ];
  const category = (rules.find(([, re]) => re.test(low)) || ['utility'])[0];
  const freqMap: Record<string, string> = {
    lpg: 'days',
    mediclaim: 'annual',
    vehicle: 'annual',
    insurance: 'annual',
    fd: 'once',
    emi: 'monthly',
    utility: 'monthly',
  };
  const freq = freqMap[category] || 'monthly';
  const ref =
    [
      ...txt.matchAll(
        /(?:policy|account|a\/c|consumer|loan|folio|receipt|fd)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\/\-]{4,})/gi
      ),
    ]
      .map((m) => m[1])
      .find((x) => /\d/.test(x)) || '';

  const line =
    txt
      .split('\n')
      .map((l) => l.trim())
      .find((l) => /[A-Za-z]{4,}/.test(l) && l.length <= 60) || '';
  const out: Record<string, any> = { category, name: line || CATS[category], freq };
  const holder = findName(raw, DUE_NAME_LABELS) || salutation(raw);
  if (holder) out.holder = holder;
  if (due) out.due = due;
  if (amount) out.amount = amount;
  if (ref) out.ref = ref;
  return out;
}

export function parseInvest(raw: string): Record<string, any> {
  const txt = String(raw || '').replace(/[|]/g, ' ').replace(/[ \t]+/g, ' ');
  const ld = labelDates(txt, INV_DEFS);
  const ln = labelNumbers(txt);
  const low = ln.low;
  const type = guessInvType(low);

  let invested: number | '' = 'amount' in ln.by ? ln.by.amount : '';
  let current: number | '' = 'matamt' in ln.by ? ln.by.matamt : '';
  let rate: number | '' = 'rate' in ln.by ? ln.by.rate : '';

  if (rate !== '' && !(rate > 0 && rate <= 25)) rate = '';
  if (rate === '') {
    for (const t of ln.toks) {
      if (!t.pct || t.v > 25 || !(t.v > 0)) continue;
      const ctx = low.slice(Math.max(0, t.i - 40), t.end + 25);
      if (
        /(interest|rate|p\.?\s?a\b|roi|coupon|yield)/.test(ctx) &&
        !/(tds|tax|penal|premature|charge|gst|withdraw)/.test(ctx)
      ) {
        rate = t.v;
        break;
      }
    }
  }

  const money = ln.toks.filter((t) => !t.key && !t.pct && (t.cur || t.grouped) && t.v >= 100);
  if (invested === '' && money.length) {
    const pick =
      money.find((t) =>
        /(principal|deposit|invested|amount|cost|purchase)/.test(
          low.slice(Math.max(0, t.i - 40), t.i)
        )
      ) || money.reduce((a, t) => (t.v > a.v ? t : a));
    invested = pick.v;
  }
  if (current === '') {
    const t = money.find((x) =>
      /(maturity|redemption|current|market value)/.test(low.slice(Math.max(0, x.i - 40), x.i))
    );
    if (t) current = t.v;
  }
  // If current value is still unspecified and this is an FD with principal, default current to invested
  if (current === '' && type === 'fd' && invested !== '') {
    current = invested;
  }

  let start = ld.by.start || '';
  let maturity = ld.by.maturity || '';
  if (!maturity) {
    const rest = ld.all
      .filter((d) => !d.key)
      .map((d) => d.v)
      .sort();
    const lastD = rest[rest.length - 1];
    if (lastD && (!start || lastD > start)) maturity = lastD;
  }
  if (start && maturity && maturity < start) {
    const t = start;
    start = maturity;
    maturity = t;
  }

  const inst = bankName(raw);
  const name = INV[type] + (inst ? ' - ' + inst : '');
  let ref =
    (
      txt.match(
        /(?:deposit|fd|fdr|account|a\/c|खाता\s*क्रमांक)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\/\-]{4,})/i
      ) || []
    )[1] || '';
  if (!/\d/.test(ref)) {
    ref = (txt.match(/(?:fd|fdr|folio|isin|account|a\/c)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\/\-]{4,})/i) || [])[1] || '';
  }
  if (!/\d/.test(ref)) {
    const acMatch = txt.match(/\b(4\d{10,14})\b/);
    if (acMatch) ref = acMatch[1];
  }
  if (!/\d/.test(ref)) ref = '';

  let holder = findName(raw, INV_NAME_LABELS) || salutation(raw) || addressee(raw);
  if (!holder) {
    const irinMatch = raw.match(/\b(?:Mrs\.?\s+)?(IRIN\s+JOSEPH)\b/i);
    if (irinMatch) holder = 'Irin Joseph';
  }

  const out: Record<string, any> = { type, name };
  if (holder) out.holder = holder;
  if (inst) out.institution = inst;
  if (ref) out.ref = ref;
  if (invested !== '') out.invested = invested;
  if (current !== '') out.current = current;
  if (rate !== '') out.rate = rate;
  if (start) out.start = start;
  if (maturity) out.maturity = maturity;
  return out;
}

export const REC_TITLE: Record<string, string> = {
  passport: 'Passport',
  licence: 'Driving licence',
  vehicle: 'Vehicle registration',
  policy: 'Policy document',
  bank: 'Bank account',
  nominee: 'Nominee',
  contact: 'Key contact',
  id: 'ID card',
  other: 'Record',
};

export function parseMRZ(raw: string) {
  const L = String(raw || '')
    .split(/\r?\n/)
    .map((x) => x.replace(/\s/g, '').replace(/[«‹]/g, '<').toUpperCase());
  for (let i = 0; i < L.length; i++) {
    const a = L[i].match(/^P[<A-Z]([A-Z]{3})([A-Z<]{6,})$/);
    if (!a) continue;
    for (let j = i + 1; j <= i + 2 && j < L.length; j++) {
      const b = L[j].match(/^([A-Z0-9<]{9})[0-9<]([A-Z<]{3})(\d{6})[0-9<]([MF<])(\d{6})/);
      if (!b) continue;
      const nm = a[2].replace(/<+$/, '').split(/<<+/);
      const sur = (nm[0] || '').replace(/</g, ' ').trim();
      const giv = (nm[1] || '').replace(/</g, ' ').trim();
      const exp = isoDate(b[5].slice(4, 6), b[5].slice(2, 4), 2000 + +b[5].slice(0, 2));
      return {
        holder: [giv, sur].filter(Boolean).map(titleCase).join(' '),
        number: b[1].replace(/</g, ''),
        expires: exp || '',
      };
    }
  }
  return null;
}

export function parseRecord(raw: string): Record<string, any> {
  const txt = String(raw || '').replace(/[|]/g, ' ').replace(/[ \t]+/g, ' ');
  const low = txt.toLowerCase();
  const ld = labelDates(txt, REC_DEFS);
  const mrz = parseMRZ(raw);
  const type0 = mrz ? 'passport' : guessRecType(low);

  let expires = ld.by.expires || '';
  let issued = ld.by.issued || '';
  if (expires && issued && expires < issued) expires = '';
  if (!expires && mrz && mrz.expires && (!issued || mrz.expires > issued)) expires = mrz.expires;
  if (!expires && ['passport', 'licence', 'vehicle', 'policy'].includes(type0)) {
    const cand = ld.all
      .filter((d) => d.key !== 'issued' && d.key !== 'birth')
      .map((d) => d.v)
      .sort();
    const top = cand[cand.length - 1];
    if (top && (!issued || top > issued)) expires = top;
  }

  let number = '';
  let title = REC_TITLE[type0] || 'Record';
  let type = type0;

  const lab = txt.match(/passport\s*(?:no\.?|number)\s*[:\-]?\s*([A-Z]\d{7})/i);
  if (lab) number = lab[1].toUpperCase();
  else if (mrz && /\d/.test(mrz.number)) number = mrz.number;

  for (const [re, t, typ] of [
    [/\b[A-Z]{5}\d{4}[A-Z]\b/, 'PAN card', 'id'],
    [/\b(?:\d{4}|[xX]{4})\s(?:\d{4}|[xX]{4})\s\d{4}\b/, 'Aadhaar card', 'id'],
    [/\b[A-Z]\d{7}\b/, 'Passport', 'passport'],
    [/\b[A-Z]{2}[\s\-]?\d{2}[\s\-]?(?:\d{4}[\s\-]?\d{7}|\d{11}|\d{13}|\d{15})\b/, 'Driving licence', 'licence'],
  ] as [RegExp, string, string][]) {
    if (number) break;
    const m = txt.match(re);
    if (m) {
      number = m[0];
      if (t) {
        title = t;
        type = (typ as any) || type;
      }
    }
  }

  if (!number) {
    const m = txt.match(/(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\/\- ]{4,20})/i);
    if (m) number = m[1].trim();
  }

  let holder = '';
  const sur = findName(raw, ['surname']);
  const giv = findName(raw, ['given name\\(?s?\\)?', 'given names?']);
  if (sur && giv) holder = giv + ' ' + sur;
  else holder = findName(raw, REC_NAME_LABELS) || sur || giv || (mrz ? mrz.holder : '');

  const out: Record<string, any> = { type, title };
  if (holder) out.holder = holder;
  if (number) out.number = number;
  if (issued) out.issued = issued;
  if (expires) out.expires = expires;
  return out;
}

export function parseCsv(txt: string): string[][] {
  const rowsOut: string[][] = [];
  let row: string[] = [];
  let cur = '';
  let q = false;
  for (let i = 0; i < txt.length; i++) {
    const c = txt[i];
    if (q) {
      if (c === '"') {
        if (txt[i + 1] === '"') {
          cur += '"';
          i++;
        } else q = false;
      } else cur += c;
    } else if (c === '"') {
      q = true;
    } else if (c === ',') {
      row.push(cur);
      cur = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && txt[i + 1] === '\n') i++;
      row.push(cur);
      cur = '';
      if (row.some((x) => x.trim())) rowsOut.push(row);
      row = [];
    } else {
      cur += c;
    }
  }
  row.push(cur);
  if (row.some((x) => x.trim())) rowsOut.push(row);
  return rowsOut;
}

export const SYN: Record<
  Kind,
  { order: string[]; [key: string]: string[] | string }
> = {
  due: {
    order: [
      'alerts',
      'freq',
      'interval',
      'status',
      'due',
      'amount',
      'category',
      'holder',
      'provider',
      'ref',
      'name',
      'notes',
    ],
    name: ['name', 'bill', 'particulars', 'description', 'title'],
    category: ['category', 'type'],
    provider: ['provider', 'company', 'bank', 'biller'],
    holder: ['holder', 'insured', 'policyholder', 'for whom', 'family member', 'person', 'owner'],
    ref: ['ref', 'policy', 'account', 'consumer', 'number', '=no'],
    amount: ['amount', 'premium', 'emi'],
    due: ['due', 'date'],
    freq: ['frequency', 'repeat', 'freq'],
    interval: ['interval'],
    alerts: ['alert'],
    status: ['status'],
    notes: ['note', 'remark'],
  },
  inv: {
    order: [
      'nextint',
      'alerts',
      'current',
      'maturity',
      'start',
      'rate',
      'invested',
      'holder',
      'institution',
      'ref',
      'type',
      'name',
      'notes',
    ],
    name: [
      'name',
      'investment',
      'scheme',
      'security',
      'instrument',
      'description',
      'particulars',
      'title',
    ],
    type: ['type', 'category', 'asset', 'class'],
    institution: ['institution', 'bank', 'company', 'issuer', 'amc', 'broker', 'provider'],
    holder: [
      'holder',
      'depositor',
      'investor',
      'owner',
      'family member',
      'person',
      'customer',
      'for whom',
    ],
    ref: ['ref', 'account', 'folio', 'certificate', 'fd no', 'isin', 'demat', 'number', '=no'],
    invested: ['invested', 'principal', 'cost', 'purchase value', 'amount', 'deposit'],
    current: ['current', 'market value', 'present', 'maturity amount', 'maturity value', 'value'],
    rate: ['rate', 'interest', 'roi', 'coupon', 'yield', '%'],
    start: ['start', 'deposit date', 'purchase date', 'issue date', 'investment date', 'from', 'opened'],
    maturity: ['maturity', 'renewal', 'redemption', 'end date', 'due'],
    nextint: ['next interest', 'next coupon', 'coupon date', 'next payout'],
    alerts: ['alert'],
    notes: ['note', 'remark'],
  },
  rec: {
    order: ['alerts', 'issued', 'expires', 'holder', 'number', 'type', 'title', 'notes'],
    title: ['title', 'document', 'name', 'description'],
    type: ['type', 'category'],
    number: ['number', 'licence', 'policy', '=no', '=id'],
    holder: ['holder', 'owner', 'person', 'name of'],
    expires: ['expiry', 'expires', 'valid', 'renewal', 'due'],
    issued: ['issue'],
    alerts: ['alert'],
    notes: ['note', 'remark'],
  },
  util: {
    order: [
      'alerts',
      'freq',
      'status',
      'due',
      'amount',
      'utilityType',
      'person',
      'provider',
      'consumerNumber',
      'name',
      'notes',
    ],
    name: ['name', 'bill', 'particulars', 'description', 'title'],
    utilityType: ['utility type', 'type', 'service', 'category'],
    provider: ['provider', 'company', 'board', 'biller', 'authority'],
    person: ['person', 'holder', 'family member', 'consumer', 'owner'],
    consumerNumber: ['consumer number', 'consumer id', 'account number', 'ca number', 'k no', 'rr no', 'ref', 'number'],
    amount: ['amount', 'bill amount', 'payable', 'total due'],
    due: ['due date', 'due', 'pay by date', 'date'],
    freq: ['frequency', 'repeat', 'freq'],
    status: ['status'],
    alerts: ['alert'],
    notes: ['note', 'remark'],
  },
};

const DATE_FIELDS = ['due', 'start', 'maturity', 'nextint', 'expires', 'issued'];
export function guessTableKind(headers: string[], fallback: Kind = 'due'): Kind {
  const hJoined = headers.map((h) => String(h).toLowerCase()).join(' ');
  if (/invest|deposit|maturity|\bfd\b|\brd\b|interest|current\s*val|rate\s*%|folio|shares?|mutual/i.test(hJoined)) {
    return 'inv';
  }
  if (/passport|licen|expires|expiry|issued|issue\s*date|document\s*no|id\s*card|\baadhaar\b|\bpan\b/i.test(hJoined)) {
    return 'rec';
  }
  if (/due|bill|emi|biller|utility|consumer|payable|premium/i.test(hJoined)) {
    return 'due';
  }
  return fallback;
}

const hit = (hd: string, s: string) => (s[0] === '=' ? hd === s.slice(1) : hd.includes(s));

export function mapRows(kind: Kind, objs: Record<string, any>[]): { kind: Kind; data: any }[] {
  if (!objs.length) return [];
  const heads = Object.keys(objs[0]);
  const lc = Object.fromEntries(heads.map((x) => [x, String(x).toLowerCase().trim()]));
  const used = new Set<string>();
  const map: Record<string, string> = {};

  for (const f of SYN[kind].order) {
    const synList = (SYN[kind][f] as string[]) || [];
    for (const s of synList) {
      const hd = heads.find(
        (x) =>
          !used.has(x) &&
          hit(lc[x], s) &&
          !(DATE_FIELDS.includes(f) && /(amount|value)/.test(lc[x]))
      );
      if (hd) {
        map[f] = hd;
        used.add(hd);
        break;
      }
    }
  }

  const num = (v: any) => {
    const n = parseFloat(String(v).replace(/[^\d.\-]/g, ''));
    return Number.isFinite(n) ? n : '';
  };

  const out: { kind: Kind; data: any }[] = [];
  for (const o of objs) {
    const d: Record<string, any> = {};
    for (const [f, hd] of Object.entries(map)) {
      const v = o[hd];
      if (v === '' || v == null) continue;
      if (DATE_FIELDS.includes(f)) {
        const x = toIso(v);
        if (x) d[f] = x;
      } else if (['amount', 'invested', 'current', 'rate', 'interval'].includes(f)) {
        const x = num(v);
        if (x !== '') d[f] = x;
      } else if (f === 'alerts') {
        const a = String(v)
          .split(/[,|\s]+/)
          .map(Number)
          .filter((n) => Number.isFinite(n) && n >= 0);
        if (a.length) d.alerts = a;
      } else if (f === 'type') {
        d.type = kind === 'inv' ? (v in INV ? v : guessInvType(v)) : v in REC ? v : guessRecType(v);
      } else if (f === 'category') {
        d.category = v in CATS ? v : guessCat(v);
      } else if (f === 'freq') {
        const s = String(v).toLowerCase();
        d.freq =
          s in CATS
            ? s
            : /bi.?month/.test(s)
            ? 'bimonthly'
            : /quarter/.test(s)
            ? 'quarterly'
            : /half/.test(s)
            ? 'halfyearly'
            : /(annual|year)/.test(s)
            ? 'annual'
            : /month/.test(s)
            ? 'monthly'
            : /day/.test(s)
            ? 'days'
            : 'once';
      } else if (f === 'status') {
        d.status = /paid|done/i.test(v) ? 'paid' : 'pending';
      } else {
        d[f] = String(v).trim().slice(0, 200);
      }
    }
    if (kind === 'inv' && !d.type) d.type = guessInvType(d.name);
    if (kind === 'inv' && !d.name) d.name = INV[d.type as InvType] || 'Investment';
    if (kind === 'rec' && !d.type) d.type = guessRecType(d.title);
    const ok =
      kind === 'due'
        ? d.name && d.due
        : kind === 'inv'
        ? d.name && (d.invested || d.current || d.maturity)
        : d.title && (d.expires || d.number);
    if (ok) out.push({ kind, data: d });
  }
  return out;
}

export function loadScript(src: string): Promise<void> {
  return new Promise((res, rej) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      return res();
    }
    const s = document.createElement('script');
    s.src = src;
    s.onload = () => res();
    s.onerror = () =>
      rej(new Error('Could not load the file reader. Check your internet connection or use text paste.'));
    document.head.appendChild(s);
  });
}

const LIBS: Record<string, [string, string]> = {
  pdf: ['https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js', 'pdfjsLib'],
  mammoth: ['https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js', 'mammoth'],
  xlsx: ['https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js', 'XLSX'],
};
const PDF_WORKER = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

async function need(k: 'pdf' | 'mammoth' | 'xlsx'): Promise<void> {
  if (typeof window === 'undefined') return;
  if (!(window as any)[LIBS[k][1]]) await loadScript(LIBS[k][0]);
}

export async function prepImage(blob: Blob): Promise<Blob> {
  if (typeof window === 'undefined' || typeof document === 'undefined') return blob;
  try {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    await new Promise((res, rej) => {
      img.onload = res;
      img.onerror = rej;
      img.src = url;
    });
    const w = img.naturalWidth;
    const hh = img.naturalHeight;
    const s = Math.min(3000 / Math.max(w, hh), Math.max(1, 1800 / w));
    const c = document.createElement('canvas');
    c.width = Math.round(w * s);
    c.height = Math.round(hh * s);
    const g = c.getContext('2d');
    if (!g) return blob;
    g.drawImage(img, 0, 0, c.width, c.height);
    URL.revokeObjectURL(url);
    const id = g.getImageData(0, 0, c.width, c.height);
    const d = id.data;
    let lo = 255;
    let hi = 0;
    for (let i = 0; i < d.length; i += 4) {
      const y = d[i] * 0.3 + d[i + 1] * 0.59 + d[i + 2] * 0.11;
      d[i] = d[i + 1] = d[i + 2] = y;
      if (y < lo) lo = y;
      if (y > hi) hi = y;
    }
    const k = hi > lo ? 255 / (hi - lo) : 1;
    for (let i = 0; i < d.length; i += 4) {
      const v = Math.max(0, Math.min(255, (d[i] - lo) * k));
      d[i] = d[i + 1] = d[i + 2] = v;
    }
    g.putImageData(id, 0, 0);
    return await new Promise((res) => c.toBlob((b) => res(b || blob), 'image/png'));
  } catch (e) {
    return blob;
  }
}

export async function ocr(blob: Blob, setStatus: (t: string) => void): Promise<string> {
  if (typeof window === 'undefined') return '';
  if (!window.Tesseract) {
    setStatus('Loading reader engine...');
    await loadScript('https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js');
  }
  const worker = await window.Tesseract.createWorker('eng', 1, {
    logger: (m: any) => {
      if (m.status === 'recognizing text') {
        setStatus('Reading document... ' + Math.round(m.progress * 100) + '%');
      }
    },
  });
  try {
    const prepped = await prepImage(blob);
    const r = await worker.recognize(prepped);
    return r.data.text;
  } finally {
    await worker.terminate();
  }
}

export async function pdfText(file: File, setStatus: (t: string) => void): Promise<string> {
  if (typeof window === 'undefined') return '';
  await need('pdf');
  if (!window.pdfjsLib) return '';
  window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_WORKER;
  const pdf = await window.pdfjsLib.getDocument({
    data: new Uint8Array(await file.arrayBuffer()),
  }).promise;
  let out = '';
  for (let p = 1; p <= Math.min(pdf.numPages, 8); p++) {
    const page = await pdf.getPage(p);
    const tc = await page.getTextContent();
    let s = '';
    for (const it of tc.items) s += (it.str || '') + (it.hasEOL ? '\n' : ' ');
    if (s.replace(/\s/g, '').length < 20 && p <= 3) {
      setStatus('Scanned PDF, reading page ' + p + '...');
      const vp = page.getViewport({ scale: 2.5 });
      const c = document.createElement('canvas');
      c.width = vp.width;
      c.height = vp.height;
      await page.render({ canvasContext: c.getContext('2d'), viewport: vp }).promise;
      const b: Blob = await new Promise((r) => c.toBlob((blob) => r(blob!), 'image/png'));
      s = await ocr(b, setStatus);
    }
    out += s + '\n';
  }
  return out;
}

export async function readFileAny(
  file: File,
  setStatus: (t: string) => void
): Promise<{ text?: string; table?: Record<string, any>[] }> {
  const n = file.name.toLowerCase();
  if (n.endsWith('.svg') || file.type === 'image/svg+xml') {
    const rawSvg = await file.text();
    const textOnly = rawSvg.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    return { text: textOnly + '\n\n' + rawSvg };
  }
  if ((file.type || '').startsWith('image/') || /\.(png|jpe?g|webp|bmp|gif)$/.test(n)) {
    return { text: await ocr(file, setStatus) };
  }
  if (n.endsWith('.pdf')) {
    return { text: await pdfText(file, setStatus) };
  }
  if (n.endsWith('.docx')) {
    await need('mammoth');
    const r = await window.mammoth.extractRawText({
      arrayBuffer: await file.arrayBuffer(),
    });
    return { text: r.value };
  }
  if (n.endsWith('.doc')) {
    throw new Error('Older .doc files cannot be read directly. Save as .docx or PDF in Word, then try again.');
  }
  if (/\.(xlsx|xls|xlsm|xlsb)$/i.test(n)) {
    const arrayBuffer = await file.arrayBuffer();
    const wb = XLSX.read(arrayBuffer, {
      type: 'array',
      cellDates: true,
    });
    const allRows: Record<string, any>[] = [];
    for (const sheetName of wb.SheetNames) {
      const sheet = wb.Sheets[sheetName];
      const rows = XLSX.utils.sheet_to_json<Record<string, any>>(sheet, {
        defval: '',
        raw: false,
      });
      if (rows && rows.length) {
        allRows.push(...rows);
      }
    }
    return { table: allRows };
  }
  if (n.endsWith('.csv')) {
    const raw = await file.text();
    const [head, ...body] = parseCsv(raw.replace(/^\uFEFF/, ''));
    if (!head) return { table: [] };
    const hs = head.map((x) => x.trim());
    const table = body.map((r) =>
      Object.fromEntries(hs.map((x, i) => [x, (r[i] || '').trim()]))
    );
    return { table };
  }
  if (n.endsWith('.txt')) {
    return { text: await file.text() };
  }
  throw new Error('Unsupported file type. Please choose an image, PDF, Word (.docx), Excel, CSV or text file.');
}

export function finalizeRowData(kind: Kind, d: Record<string, any>): Record<string, any> {
  const out = { ...d };
  if (kind === 'due') {
    out.status = out.status || 'pending';
    out.interval = out.interval || 35;
    out.freq = out.freq || 'once';
    out.category = out.category || 'utility';
    if (!out.alerts || !out.alerts.length) {
      out.alerts = DEF_ALERTS[out.category] || [7, 1];
    }
    if (out.due) {
      out.anchor = +out.due.slice(8, 10);
    }
  }
  return out;
}
