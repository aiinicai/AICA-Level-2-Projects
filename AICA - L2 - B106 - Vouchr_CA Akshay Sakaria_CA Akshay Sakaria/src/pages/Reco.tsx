import { useMemo, useRef, useState } from 'react';
import { reconcileNotes } from '../lib/vendorNotes';
import { useTr } from '../i18n';
import { useStore } from '../data/store';
import type { RecoStatus } from '../data/types';
import { parse2B, reconcile } from '../lib/reco';
import { downloadCsv } from '../lib/csv';
import { fmtDate, fyLabel, todayIso } from '../lib/dates';
import { docName, saveDocument } from '../lib/storage';
import { fmtInr, round2 } from '../lib/money';
import { Empty, PageHead, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';
import { RecoMessage } from '../ui/RecoMessage';
import type { RecoRow } from '../lib/reco';

const STATUS: Record<RecoStatus, { label: string; tone: string }> = {
  matched: { label: 'Matched', tone: 'ok' },
  mismatch: { label: 'Mismatch', tone: 'warn' },
  missing_in_2b: { label: 'Missing in 2B', tone: 'danger' },
  missing_in_books: { label: 'Missing in books', tone: 'info' }
};

export function Reco() {
  const tr = useTr();
  const { client, scoped, s, saveRecoRun } = useStore();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [runId, setRunId] = useState<string>();
  const [filter, setFilter] = useState<'all' | RecoStatus>('all');
  const [ask, setAsk] = useState<RecoRow>();
  const run = scoped.recoRuns.find((r) => r.id === runId) ?? scoped.recoRuns[0];

  const rows = useMemo(() => {
    if (!run) return [];
    // compare only books from the periods present in the file (by invoice month), so other months are not shown as "missing"
    const months = new Set(run.lines.map((l) => l.invoiceDate?.slice(0, 7)).filter(Boolean));
    const books = scoped.expenses.filter((e) => months.has(e.invoiceDate.slice(0, 7)));
    const gstinOf = (vid?: string) => s.vendors.find((v) => v.id === vid)?.gstin;
    // credit / debit notes (2B section CDNR) are matched the same way, by note date month
    const noteMonths = new Set(run.lines.filter((l) => l.docType === 'credit' || l.docType === 'debit').map((l) => l.invoiceDate?.slice(0, 7)).filter(Boolean));
    const notes = scoped.vendorNotes.filter((n) => months.has(n.noteDate.slice(0, 7)) || noteMonths.has(n.noteDate.slice(0, 7)));
    return [...reconcile(books, (e) => gstinOf(e.vendorId), run.lines), ...reconcileNotes(notes, (vid) => gstinOf(vid), run.lines)];
  }, [run, scoped.expenses, scoped.vendorNotes, s.vendors]);

  const counts = rows.reduce((m, r) => ({ ...m, [r.status]: (m[r.status] ?? 0) + 1 }), {} as Record<string, number>);
  const shown = rows.filter((r) => filter === 'all' || r.status === filter);
  // ITC at risk = invoices / debit notes not yet in 2B (a credit note missing from 2B reduces ITC anyway, so it is not "at risk")
  const itcAtRisk = round2(rows.filter((r) => r.status === 'missing_in_2b' && !r.invoiceNo.startsWith('CN ')).reduce((a, r) => a + r.booksTax, 0));

  async function onFile(f?: File) {
    if (!f) return;
    try {
      let json: unknown;
      try { json = JSON.parse(await f.text()); } catch { toast(tr('This is not a GSTR-2B JSON file. Download “JSON” (not Excel) from the GST portal.'), true); return; }
      const parsed = parse2B(json);
      if (parsed.gstin && client?.gstin && parsed.gstin !== client.gstin) {
        toast(tr('This file is for GSTIN {a}, not {b}', { a: parsed.gstin, b: client.gstin }), true);
        return;
      }
      if (!parsed.lines.length) { toast(tr('No B2B invoices found in this file'), true); return; }
      saveRecoRun({ period: parsed.period ?? f.name, source: 'json_upload', lines: parsed.lines });
      if (client) {
        const p = parsed.period ?? '';
        const fy = /^\d{6}$/.test(p) ? fyLabel(`${p.slice(2)}-${p.slice(0, 2)}-01`) : fyLabel(todayIso());
        saveDocument({ clientId: client.id, clientName: client.name, fy, kind: 'GSTR-2B', file: f, name: docName(todayIso(), `GSTR2B-${p}`, undefined, f.name) })
          .catch(() => toast(tr('2B imported, but the file could not be saved to Drive.'), true));
      }
      setRunId(undefined);
      toast(tr('{n} invoices imported', { n: parsed.lines.length }));
    } catch (err) {
      toast(`${tr('Could not read file')}: ${(err as Error).message}`, true);
    }
  }

  return (
    <div className="content stack">
      <PageHead title={tr('GST reconciliation (2A / 2B)')} sub={`${client?.name} · GSTIN ${client?.gstin ?? '—'}`}>
        <button className="btn primary" onClick={() => fileRef.current?.click()}><Icon name="upload" size={16} /> {tr('Upload 2B JSON')}</button>
        <input ref={fileRef} type="file" accept=".json,application/json" hidden data-testid="reco-file" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
      </PageHead>

      <div className="card pad row between wrap">
        <div><b>{tr('GSP auto-fetch')}</b><div className="small muted">{tr('Monthly auto-fetch via the shared GSP account after the client\'s one-time OTP consent. Until a GSP is selected, download the 2B JSON from the GST portal and upload it here.')}</div></div>
        <span className="badge warn">{tr('Not connected')}</span>
      </div>

      {!run ? (
        <div className="card"><Empty>{tr('No 2B uploaded yet. Upload the JSON downloaded from the GST portal (Returns → GSTR-2B → Download JSON).')}</Empty></div>
      ) : (
        <>
          <div className="row wrap">
            <select className="input sm" style={{ width: 'auto' }} value={run.id} onChange={(e) => setRunId(e.target.value)}>
              {scoped.recoRuns.map((r) => <option key={r.id} value={r.id}>Period {r.period} · {fmtDate(r.createdAt)}</option>)}
            </select>
            <button className="btn sm" onClick={() => downloadCsv(`reco_${run.period}.csv`, ['Status', 'Supplier GSTIN', 'Supplier', 'Invoice', 'Date', 'Tax in books', 'Tax in 2B', 'Difference', 'Note'],
              rows.map((r) => [STATUS[r.status].label, r.supplierGstin, r.supplierName, r.invoiceNo, r.invoiceDate, r.booksTax, r.portalTax, r.diff, r.note]))}>
              <Icon name="download" size={14} /> {tr('Export CSV')}
            </button>
          </div>
          <div className="grid kpi">
            {(Object.keys(STATUS) as RecoStatus[]).map((k) => (
              <button key={k} className="card kpi-tile" style={{ textAlign: 'left', cursor: 'pointer', outline: filter === k ? '2px solid var(--brand)' : undefined }} onClick={() => setFilter(filter === k ? 'all' : k)}>
                <div className="kpi-label">{tr(STATUS[k].label)}</div><div className="kpi-value num">{counts[k] ?? 0}</div>
              </button>
            ))}
            <div className="card kpi-tile"><div className="kpi-label">{tr('ITC at risk')}</div><div className="kpi-value num" style={{ color: itcAtRisk ? 'var(--danger)' : undefined }}>{fmtInr(itcAtRisk)}</div><div className="kpi-sub">{tr('booked but not in 2B')}</div></div>
          </div>
          {ask && <RecoMessage row={ask} onClose={() => setAsk(undefined)} />}
          <div className="card table-wrap">
            <table className="t num cards-sm">
              <thead><tr><th>{tr('Status')}</th><th>{tr('Supplier')}</th><th>{tr('Invoice')}</th><th className="right">{tr('Books tax')}</th><th className="right">{tr('2B tax')}</th><th>{tr('Note')}</th><th></th></tr></thead>
              <tbody>{shown.map((r, i) => (
                <tr key={i}>
                  <td><span className={`badge ${STATUS[r.status].tone}`}>{tr(STATUS[r.status].label)}</span></td>
                  <td><b>{r.supplierName}</b><div className="tiny muted mono">{r.supplierGstin}</div></td>
                  <td>{r.invoiceNo}<div className="tiny muted">{r.invoiceDate ? fmtDate(r.invoiceDate) : ''}</div></td>
                  <td className="right">{fmtInr(r.booksTax)}</td><td className="right">{fmtInr(r.portalTax)}</td>
                  <td className="small">{r.note ?? '—'}</td>
                  <td>{r.status !== 'matched' && <button className="btn sm" onClick={() => setAsk(r)}>{tr('Ask supplier')}</button>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <div className="hint">{tr('Matching: supplier GSTIN + invoice number (ignoring case, spaces, “/”, “-”, leading zeros), then tax within ₹1. File layout follows open-source tools, not an official GSTN spec — validate with a real portal download.')}</div>
        </>
      )}
    </div>
  );
}
