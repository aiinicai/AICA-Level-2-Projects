// C — GSTR-2B mismatch → message to the supplier. The DIFFERENCE is worked out by the app (reconcile());
// AI only words a polite message from those facts, and any number not in our records is flagged before sending.
import { DpdpNote } from './DpdpNote';
import { useState } from 'react';
import { useStore } from '../data/store';
import { useLang, useTr } from '../i18n';
import type { RecoRow } from '../lib/reco';
import { runAi, useAiStatus, type AiResult } from '../lib/ai';
import { fmtDate } from '../lib/dates';
import { Doubts } from './AiBits';

/** Plain-language list of what differs — deterministic, also the only facts the AI may use. */
export function recoDiffs(r: RecoRow): string[] {
  if (r.status === 'missing_in_2b') return [`Invoice ${r.invoiceNo} dated ${r.invoiceDate ?? ''} (tax ${r.booksTax}) is in our books but not in our GSTR-2B — it seems not filed in your GSTR-1, or filed under another GSTIN / invoice number.`];
  if (r.status === 'mismatch') return [`Invoice ${r.invoiceNo}: tax in our books ${r.booksTax}, tax in GSTR-2B ${r.portalTax} (difference ${r.diff}).`];
  if (r.status === 'missing_in_books') return [`Invoice ${r.invoiceNo} dated ${r.invoiceDate ?? ''} (tax ${r.portalTax}) appears in our GSTR-2B but we have no such bill — please send a copy.`];
  return [];
}

export function RecoMessage({ row, onClose }: { row: RecoRow; onClose: () => void }) {
  const { me, client } = useStore();
  const tr = useTr();
  const lang = useLang();
  const ai = useAiStatus();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [res, setRes] = useState<AiResult<{ message_en: string; message_hi: string }>>();
  const [text, setText] = useState('');
  const diffs = recoDiffs(row);

  async function draft() {
    setBusy(true); setErr(undefined);
    try {
      const r = await runAi<{ message_en: string; message_hi: string }>('reco_message', me!.role, {
        clientId: client?.id, clientName: client?.name, vendorName: row.supplierName, diffs,
        bill: { invoiceNo: row.invoiceNo, date: row.invoiceDate ? fmtDate(row.invoiceDate) : '', supplierGstin: row.supplierGstin }
      });
      setRes(r);
      setText(lang === 'hi' ? r.result.message_hi : r.result.message_en);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div className="card pad stack" style={{ borderColor: 'var(--brand)' }}>
      <div className="row between wrap"><b>{tr('Message to supplier')} · {row.supplierName}</b><button className="btn sm" onClick={onClose}>{tr('Close')}</button></div>
      <div className="small"><b>{tr('What differs (worked out by the app)')}:</b> {diffs.join(' ')}</div>
      <button className="btn sm" style={{ alignSelf: 'flex-start' }} disabled={!ai.enabled || busy} onClick={draft} title={ai.enabled ? undefined : tr(ai.reason)}>{busy ? tr('Writing…') : tr('Draft message with AI')}</button>
      {ai.enabled && <DpdpNote kind="ai" />}
      {err && <div className="banner danger small">{tr(err)}</div>}
      {res && <Doubts doubts={res.doubts} />}
      {res && <textarea className="input" rows={5} value={text} onChange={(e) => setText(e.target.value)} aria-label={tr('Message')} />}
      {res && (
        <div className="row wrap">
          <button className="btn sm" onClick={() => navigator.clipboard?.writeText(text)}>{tr('Copy')}</button>
          <a className="btn sm primary" href={`https://wa.me/?text=${encodeURIComponent(text)}`} target="_blank" rel="noopener noreferrer">{tr('Open in WhatsApp')}</a>
          <span className="tiny muted">{tr('Read and edit before sending — you send it, not the app.')}</span>
        </div>
      )}
    </div>
  );
}
