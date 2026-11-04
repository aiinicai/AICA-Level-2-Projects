// Shared AI display pieces. Doubt is always visible: amber tag on the field + a list of everything AI was unsure about.
import type { ReactNode } from 'react';
import { useTr } from '../i18n';
import type { Fact } from '../lib/ai';
import { Icon } from './Icon';

export const AI_FIELD_LABELS: Record<string, string> = {
  vendor_name: 'Vendor', vendor_gstin: 'Vendor GSTIN', invoice_no: 'Bill no.', invoice_date: 'Bill date', taxable_value: 'Taxable value',
  cgst: 'CGST', sgst: 'SGST', igst: 'IGST', total: 'Bill total', irn: 'IRN', description: 'What was bought', amount: 'Amount', purpose: 'Purpose',
  pay_mode: 'Payment mode', paid: 'Paid', bill_date: 'Bill date', expense_head: 'Expense head', tds_code: 'TDS', hsn_sac: 'HSN / SAC', gst_rate: 'GST rate',
  head: 'Expense head', centre: 'Project / branch', vendor: 'Vendor', mode: 'Payment mode', from: 'From', to: 'To', issuer: 'Issued by',
  reference_no: 'Reference no.', notice_date: 'Notice date', reply_due_date: 'Reply due by', amount_demanded: 'Amount demanded'
};

// fixed reasons produced by the truth checks (dynamic parts captured as {x})
export const AI_REASON_PATTERNS: [RegExp, string][] = [
  [/^amounts don't add up \(total differs by ₹(-?[\d.]+)\)$/, "amounts don't add up (total differs by ₹{x})"],
  [/^"(.+)" is not in the (.+) list$/, '"{x}" is not in our list'],
  [/^not a valid GST rate on (.+)$/, 'not a valid GST rate on that date'],
  [/^line (\d+) was not answered$/, 'line {x} was not answered'],
  [/^red flag "(.+)" dropped — no evidence quoted$/, 'red flag "{x}" dropped — no evidence quoted'],
  [/^message has numbers not in our records \((.+)\) — edit before sending$/, 'message has numbers not in our records ({x}) — edit before sending'],
  [/^narration has numbers not on the bill \((.+)\) — not used$/, 'narration has numbers not on the bill ({x}) — not used'],
  [/^dropped a point with unknown figure\(s\) (.+)$/, 'dropped a point with unknown figure(s) {x}'],
  [/^action "(.+)" dropped — no quote from the notice$/, 'action "{x}" dropped — no quote from the notice'],
  [/^quote for action "(.+)" not found in the PDF text — check$/, 'quote for action "{x}" not found in the PDF text — check']
];

export function useTrDoubt() {
  const tr = useTr();
  return (d: string) => {
    const i = d.indexOf(': ');
    const path = i > 0 ? d.slice(0, i) : '';
    const leaf = path.split('.').filter((p) => !/^\d+$/.test(p)).pop() ?? '';
    const label = AI_FIELD_LABELS[leaf] ? tr(AI_FIELD_LABELS[leaf]) : path;
    const reasons = (i > 0 ? d.slice(i + 2) : d).split('; ').map((r) => {
      for (const [re, key] of AI_REASON_PATTERNS) { const m = re.exec(r); if (m) return tr(key, { x: m[1] }); }
      return tr(r);
    });
    return label ? `${label}: ${reasons.join('; ')}` : reasons.join('; ');
  };
}

/** Small tag after an AI-filled value: green = read clearly, amber = unsure (with reason), grey = not on the document. */
export function FactTag({ f }: { f?: Fact<unknown> | null }) {
  const tr = useTr();
  const trD = useTrDoubt();
  if (!f) return null;
  if (f.certainty === 'certain') return <span className="badge ok" title={`${tr('Read from')}: “${f.evidence}”`}>{tr('AI read')}</span>;
  if (f.certainty === 'not_found') return <span className="badge" title={tr('Not on the document')}>{tr('Not found')}</span>;
  return <span className="badge warn" title={trD(`x: ${f.note ?? ''}`).replace(/^x: /, '')}>⚠ {tr('AI unsure — check')}</span>;
}

/** Everything AI was unsure about, in one amber list. Shown whenever there is any doubt. */
export function Doubts({ doubts, children }: { doubts: string[]; children?: ReactNode }) {
  const tr = useTr();
  const trD = useTrDoubt();
  if (!doubts.length) return <div className="banner ok small"><Icon name="check" size={16} /><span>{tr('AI passed every check — still confirm before saving.')}{children}</span></div>;
  return (
    <div className="banner warn small" role="status" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 4 }}>
      <b>⚠ {tr('AI is unsure about {n} item(s) — please check these yourself:', { n: doubts.length })}</b>
      <ul style={{ margin: 0, paddingLeft: 18 }}>{doubts.map((d, i) => <li key={i}>{trD(d)}</li>)}</ul>
      {children}
    </div>
  );
}

export function AiOff({ reason }: { reason: string }) {
  const tr = useTr();
  return <div className="tiny muted">{tr(reason)}</div>;
}
