// "Risk check" panel in the CA review drawer: rule-based red flags for this bill, plus AI (when connected):
// full bill analysis, E — Tally narration and F — HSN/SAC suggestion. Nothing changes unless the CA taps "Use".
import { DpdpNote } from './DpdpNote';
import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import type { Expense } from '../data/types';
import { gstRatesOn } from '../data/masters';
import { useLang, useTr } from '../i18n';
import { riskCheck } from '../lib/anomaly';
import { runAi, sure, useAiStatus, type AiResult, type Fact } from '../lib/ai';
import { fmtDate } from '../lib/dates';
import { getDocumentBlob } from '../lib/storage';
import { AiOff, Doubts, FactTag } from './AiBits';
import { Icon } from './Icon';

const TONE = { high: 'danger', medium: 'warn', low: 'info' } as const;
type Line = { description: Fact<string>; hsn_sac: Fact<string>; amount: Fact<number>; gst_rate: Fact<number> };
type Analysis = Record<string, unknown> & {
  total: Fact<number>; invoice_no: Fact<string>; invoice_date: Fact<string>; line_items: Line[]; expense_head: Fact<string>; tds_code: Fact<string>;
  rcm_likely: Fact<boolean>; blocked_17_5: Fact<string>; red_flags: { flag: string; severity: keyof typeof TONE; evidence: string }[];
  mismatches: string[]; summary_en: string; summary_hi: string;
};
type Hsn = { items: { index: number; hsn_sac: Fact<string>; gst_rate: Fact<number> }[] };

export function AiCheck({ e, onUseHead, onUseTds, onNarration, onHsn }: {
  e: Expense; onUseHead: (headId: string) => void; onUseTds: (code: string) => void; onNarration: (text: string) => void; onHsn: (code: string) => void;
}) {
  const { s, me } = useStore();
  const tr = useTr();
  const lang = useLang();
  const ai = useAiStatus();
  const [busy, setBusy] = useState<string>();
  const [err, setErr] = useState<string>();
  const [res, setRes] = useState<AiResult<Analysis>>();
  const [narr, setNarr] = useState<AiResult<{ narration: string }>>();
  const [hsn, setHsn] = useState<AiResult<Hsn>>();
  const client = s.clients.find((c) => c.id === e.clientId);

  const flags = useMemo(() => riskCheck(s.expenses.filter((x) => x.clientId === e.clientId), s.vendors.filter((v) => v.clientId === e.clientId), client, s.tdsRates)
    .filter((f) => f.expenseId === e.id), [s.expenses, s.vendors, client, s.tdsRates, e.id, e.clientId]);

  async function go<T>(key: string, fn: () => Promise<T>) {
    setBusy(key); setErr(undefined);
    try { return await fn(); } catch (x) { setErr((x as Error).message); } finally { setBusy(undefined); }
  }

  async function analyse() {
    const r = await go('analyse', async () => {
      const blob = ai.mode === 'local' ? await getDocumentBlob(e.fileId) : undefined;
      if (ai.mode === 'local' && !blob) throw new Error('The original bill file is not on this device.');
      const ctx = { clientId: e.clientId, buyerGstin: client?.gstin, heads: s.heads.map((h) => h.name), tdsTable: s.tdsRates,
        recorded: { invoice_no: e.invoiceNo, invoice_date: e.invoiceDate, taxable_value: e.taxableValue, total: e.totalAmount } };
      return runAi<Analysis>('analyse_invoice', me!.role, ctx, blob ? { files: [blob] } : { expenseIds: [e.id] });
    });
    if (r) setRes(r);
  }

  async function writeNarration() {
    const items = (res?.result.line_items ?? []).map((l) => sure(l.description)).filter(Boolean);
    const r = await go('narr', () => runAi<{ narration: string }>('narration', me!.role, { clientId: e.clientId, bill: {
      vendor: e.vendorName, billNo: e.invoiceNo, date: fmtDate(e.invoiceDate), description: e.description, items,
      taxable: e.taxableValue, total: e.totalAmount, project: client?.costCentres.find((c) => c.id === e.costCentreId)?.name
    } }));
    if (r) setNarr(r);
  }

  async function suggestHsn() {
    const lines = res?.result.line_items?.length ? res.result.line_items : undefined;
    const items = lines ? lines.map((l) => ({ description: sure(l.description) ?? String(l.description.value ?? ''), printedHsn: sure(l.hsn_sac), printedRate: sure(l.gst_rate) }))
      : [{ description: e.description || e.vendorName, printedHsn: e.hsnSac }];
    const r = await go('hsn', () => runAi<Hsn>('hsn_suggest', me!.role, { clientId: e.clientId, date: e.invoiceDate, allowedRates: gstRatesOn(e.invoiceDate), items }));
    if (r) setHsn(r);
  }

  const a = res?.result;
  const head = a && sure(a.expense_head) !== undefined ? s.heads.find((h) => h.name === sure(a.expense_head)) : undefined;
  const tds = a ? sure(a.tds_code) : undefined;

  return (
    <div className="card pad stack">
      <div className="row between wrap">
        <h3>{tr('Risk check')}</h3>
        <div className="row wrap" style={{ gap: 6 }}>
          <button className="btn sm" disabled={!ai.enabled || !!busy || !e.fileId} onClick={analyse} title={!e.fileId ? tr('No bill file to read') : undefined}>
            <Icon name="radar" size={14} /> {busy === 'analyse' ? tr('Reading the bill…') : tr('AI check')}
          </button>
          <button className="btn sm" disabled={!ai.enabled || !!busy} onClick={writeNarration}>{busy === 'narr' ? '…' : tr('Write narration')}</button>
          <button className="btn sm" disabled={!ai.enabled || !!busy} onClick={suggestHsn}>{busy === 'hsn' ? '…' : tr('Suggest HSN')}</button>
        </div>
      </div>
      {flags.length === 0 ? <div className="small muted">{tr('No red flags from the rule checks.')}</div> : flags.map((f) => (
        <div key={f.id} className={`banner ${TONE[f.severity]} small`}><Icon name="alert" size={16} /><span><b>{tr(f.title, f.vars)}</b> — {tr(f.detail, f.vars)}</span></div>
      ))}
      {!ai.enabled ? <AiOff reason={ai.reason} /> : <DpdpNote kind="ai" />}
      {err && <div className="banner danger small">{tr(err)}</div>}

      {a && res && (
        <div className="stack" style={{ gap: 8 }}>
          <div className="small">{lang === 'hi' ? a.summary_hi : a.summary_en}</div>
          <Doubts doubts={res.doubts} />
          {a.mismatches.length > 0 && <div className="banner warn small"><span><b>{tr('Differs from what was recorded')}:</b> {a.mismatches.join(' · ')}</span></div>}
          {a.red_flags.map((f, i) => <div key={i} className={`banner ${TONE[f.severity] ?? 'info'} small`}><span><b>{f.flag}</b> — “{f.evidence}”</span></div>)}
          <div className="row wrap small">
            <span>{tr('AI head')}: <b>{String(a.expense_head.value ?? '—')}</b></span><FactTag f={a.expense_head} />
            {head && head.id !== e.headId && <button className="btn sm" onClick={() => onUseHead(head.id)}>{tr('Use this head')}</button>}
          </div>
          <div className="row wrap small">
            <span>{tr('AI TDS')}: <b>{String(a.tds_code.value ?? '—')}</b></span><FactTag f={a.tds_code} />
            {tds && tds !== 'NONE' && tds !== e.tdsCode && <button className="btn sm" onClick={() => onUseTds(tds)}>{tr('Use this TDS')}</button>}
          </div>
          <div className="tiny muted">{tr('TDS thresholds are worked out by the app from your TDS table, not by AI.')}</div>
        </div>
      )}

      {narr && (
        <div className="stack" style={{ gap: 6 }}>
          <div className="small"><b>{tr('Narration')}:</b> {narr.result.narration}</div>
          <Doubts doubts={narr.doubts} />
          {!narr.needsHumanCheck && <button className="btn sm" style={{ alignSelf: 'flex-start' }} onClick={() => onNarration(narr.result.narration)}>{tr('Use')}</button>}
        </div>
      )}
      {hsn && (
        <div className="stack" style={{ gap: 6 }}>
          <Doubts doubts={hsn.doubts} />
          {hsn.result.items.map((it) => (
            <div key={it.index} className="row wrap small">
              <span>#{it.index + 1} HSN/SAC <b className="mono">{String(it.hsn_sac.value ?? '—')}</b></span><FactTag f={it.hsn_sac} />
              <span>GST <b>{it.gst_rate.value ?? '—'}%</b></span><FactTag f={it.gst_rate} />
              {it.hsn_sac.value && <button className="btn sm" onClick={() => onHsn(String(it.hsn_sac.value))}>{tr('Use')}</button>}
            </div>
          ))}
        </div>
      )}
      <div className="tiny muted">{tr('AI suggestions can be wrong. The CA decides; nothing is changed unless you tap a button.')}</div>
    </div>
  );
}
