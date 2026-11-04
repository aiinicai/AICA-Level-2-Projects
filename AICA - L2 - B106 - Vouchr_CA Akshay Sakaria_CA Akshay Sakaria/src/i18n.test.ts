// Fails when any tr('…') text used in the app has no Hindi translation — so Hindi can never silently go missing.
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { HI } from './i18n-hi';
import { EXPENSE_HEADS, NO_IMAGE_REASONS } from './data/masters';
import { AI_FIELD_LABELS, AI_REASON_PATTERNS } from './ui/AiBits';
import { ASK_LABEL } from './lib/askData';
import { ASK_EXAMPLES } from './pages/Ask';
import { VERDICT } from './ui/LookAlikes';
import { DPDP_NOTES } from './ui/DpdpNote';

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : /\.tsx?$/.test(f) && !/\.test\./.test(f) ? [p] : [];
  });
}

const src = files(join(__dirname));
// tr('…'), business-rule errors shown to users, and success toasts passed to attempt(…, '…')
const literal = /(?:\btr\(|\bRuleError\(|\}, (?:[^,;{}]+\? )?|\s: )'((?:[^'\\]|\\.)*)'(?=\)|, \{|\s*:\s*')/g;
// labels kept in maps and rendered through tr(variable)
const mapLabel = /\b(?:label|title|tTitle|tBody|detail|blurb|reason):\s*'((?:[^'\\]|\\.)*)'/g;
const keys = new Set<string>();
for (const f of src) {
  const s = readFileSync(f, 'utf8');
  for (const m of s.matchAll(literal)) keys.add(m[1].replace(/\\'/g, "'"));
  if (/(Shell|More|Compliance|Reco|PaymentLines|alerts|common|anomaly|importer|ai|Risk|AiBits|askData|LookAlikes|truth|tasks|Privacy|consent)\.tsx?$/.test(f)) for (const m of s.matchAll(mapLabel)) keys.add(m[1].replace(/\\'/g, "'"));
}
const MAPS = ['ITC 180-day', 'Payment overdue', 'TDS payment', 'GST reconciliation', 'Tally posting', 'App (devices)', 'OCR', 'Drive uploads', 'Sheets mirror',
  'GSP 2A/2B fetch', 'Tally export', 'Email', 'Push', 'Compliance watch', 'Super admin · CA firm', 'Client admin', 'Staff (sub-user)', 'Super admin', 'Admin', 'Staff',
  'TDS rates', 'Expense heads', 'RCM categories', 'Blocked credits 17(5)', 'Cash above daily limit', 'Paid before bill date', 'Backdated', 'Unverified', 'Operative', 'Inoperative',
  'Matched', 'Mismatch', 'Missing in 2B', 'Missing in books', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Unclassified', 'All', 'Overdue', 'Partially paid', 'Unpaid', 'Sure', 'Check', 'Snap a bill', 'e-Invoice QR', 'GST split', 'TDS u/s 393', 'Blocked credit 17(5)', 'UPI & bank payments', 'GSTR-2B reco', 'Tally XML', 'Google Drive filing', 'Hindi & English', 'Bank account', 'Cash box', 'Project / branch-wise spend',
  'GSTIN must be 15 characters', 'GSTIN format is not valid', 'Unknown state code', 'Check digit does not match — likely a typo', 'PAN format is not valid (e.g. ABCPE1234F)',
  'Individual', 'HUF', 'Company', 'Firm / LLP', 'AOP', 'BOI', 'Trust', 'Local authority', 'Artificial juridical person', 'Government',
  'User added', 'Vendor saved', 'Logo updated', 'Brand colour applied', 'Saved & logged', 'Approved', 'Returned to client', 'Add a note for the client', 'High', 'Medium'];
MAPS.forEach((k) => keys.add(k));
// AI: field labels, verdicts, examples, and every fixed doubt reason written by the truth checks (shown to users in Hindi too)
[...Object.values(AI_FIELD_LABELS), ...AI_REASON_PATTERNS.map(([, k]) => k), ...Object.values(ASK_LABEL), ...ASK_EXAMPLES, ...Object.values(VERDICT).map(([, l]) => l),
  'uncertain', 'nothing could be heard', ...Object.values(DPDP_NOTES)].forEach((k) => keys.add(k));
for (const f of ['truth.ts', 'tasks.ts']) {
  const s = readFileSync(join(__dirname, '..', 'supabase', 'functions', '_shared', 'ai', f), 'utf8');
  for (const m of s.matchAll(/(?:\bdoubt\([\w.]+, |extra\.push\()'((?:[^'\\]|\\.)*)'/g)) keys.add(m[1].replace(/\\'/g, "'"));
  for (const m of s.matchAll(/problems = \[([\s\S]*?)\]\.filter/g)) for (const p of m[1].matchAll(/&& '([^']+)'/g)) keys.add(p[1]);
}
EXPENSE_HEADS.forEach((h) => keys.add(h.name));

// values that look like text to the scanner but are code (status values, colours, routes)
const NOT_TEXT = new Set(['approved', 'rejected', 'en', 'hi', 'all', 'cash', 'upi', 'bank', 'card', 'cheque']);
export const missingHindi = () => [...keys].filter((k) => !(k in HI) && /[A-Za-z]{2}/.test(k) && !/^[#/]/.test(k) && !NOT_TEXT.has(k)).sort();

describe('Hindi coverage', () => {
  it('every UI string has a Hindi translation', () => {
    const missing = missingHindi();
    expect(missing, `Missing Hindi for:\n${missing.join('\n')}`).toEqual([]);
  });
  it('translations keep the same {placeholders}', () => {
    const bad = Object.entries(HI).filter(([en, hi]) => (en.match(/\{\w+\}/g) ?? []).sort().join() !== (hi.match(/\{\w+\}/g) ?? []).sort().join()).map(([en]) => en);
    expect(bad).toEqual([]);
  });
  it('no-bill reasons are bilingual', () => {
    expect(NO_IMAGE_REASONS.every((r) => r.hi && r.en)).toBe(true);
  });
});
