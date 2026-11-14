// Record a credit / debit note received from a vendor (admins). Linked to the bill it corrects, or kept at vendor level.
import { useMemo, useState } from 'react';
import { RuleError, useStore } from '../data/store';
import type { VendorNote } from '../data/types';
import { useTr } from '../i18n';
import { fmtDate, fyLabel, todayIso } from '../lib/dates';
import { fmtInr, round2 } from '../lib/money';
import { docName, saveDocument } from '../lib/storage';
import { NOTE_REASONS, REASON_LABEL } from '../lib/vendorNotes';
import { Drawer, useAttempt, useToast } from '../ui/common';

const num = (s: string) => Number(s.replace(/[^0-9.]/g, '')) || 0;

export function NoteDrawer({ vendorId, expenseId, onClose }: { vendorId: string; expenseId?: string; onClose: () => void }) {
  const st = useStore();
  const { scoped, s, client } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const toast = useToast();
  const bills = useMemo(() => scoped.expenses.filter((e) => e.vendorId === vendorId && e.status !== 'rejected' && e.status !== 'draft')
    .sort((a, b) => b.invoiceDate.localeCompare(a.invoiceDate)), [scoped.expenses, vendorId]);
  const [kind, setKind] = useState<VendorNote['kind']>('credit');
  const [billId, setBillId] = useState(expenseId ?? '');
  const bill = bills.find((b) => b.id === billId);
  const [noteNo, setNoteNo] = useState('');
  const [noteDate, setNoteDate] = useState(todayIso());
  const [reason, setReason] = useState<VendorNote['reason']>('return');
  const [taxable, setTaxable] = useState('');
  const [gst, setGst] = useState('');
  const [igstMode, setIgstMode] = useState<boolean>();
  const isIgst = igstMode ?? (bill ? bill.igst > 0 : false);
  const [headId, setHeadId] = useState('');
  const [itc, setItc] = useState(false);
  const [remark, setRemark] = useState('');
  const [file, setFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const gstAmt = round2(num(gst));
  const half = round2(gstAmt / 2);
  const total = round2(num(taxable) + (isIgst ? gstAmt : half * 2));

  async function save() {
    if (!client) return;
    setBusy(true);
    let doc: { fileId?: string; filePath?: string } = {};
    try {
      if (file) {
        const vendor = s.vendors.find((v) => v.id === vendorId);
        const d = await saveDocument({ clientId: client.id, clientName: client.name, fy: fyLabel(noteDate), kind: 'Bills', file, name: docName(noteDate, vendor?.name, `${kind === 'credit' ? 'CN' : 'DN'}-${noteNo}`, file.name) });
        doc = { fileId: d.fileId, filePath: d.path };
      }
    } catch { toast(tr('Could not save the file — the note is saved without it.'), true); }
    const ok = attempt(() => {
      if (!(num(taxable) > 0) && !(gstAmt > 0)) throw new RuleError('Enter the note amount');
      st.saveVendorNote({ vendorId, kind, noteNo, noteDate, expenseId: billId || undefined, reason, headId: billId ? undefined : headId || undefined,
        taxableValue: num(taxable), cgst: isIgst ? 0 : half, sgst: isIgst ? 0 : half, igst: isIgst ? gstAmt : 0, totalAmount: total,
        itcEligible: billId ? undefined : itc, remark: remark.trim() || undefined, ...doc });
    }, kind === 'credit' ? 'Credit note saved' : 'Debit note saved');
    setBusy(false);
    if (ok) onClose();
  }

  return (
    <Drawer title={tr('Credit / debit note from vendor')} onClose={onClose}
      footer={<><button className="btn" onClick={onClose}>{tr('Cancel')}</button>
        <button className="btn primary grow" disabled={busy || !noteNo.trim() || !(total > 0)} onClick={save}>{tr('Save note')} · {fmtInr(total)}</button></>}>
      <div className="chips" role="radiogroup" aria-label={tr('Type of note')}>
        {(['credit', 'debit'] as const).map((k) => (
          <button key={k} role="radio" aria-checked={kind === k} className={`chip ${kind === k ? 'on' : ''}`} onClick={() => setKind(k)}>
            {tr(k === 'credit' ? 'Credit note (we owe less)' : 'Debit note (we owe more)')}
          </button>
        ))}
      </div>
      <div className="hint">{tr(kind === 'credit' ? 'For goods returned, a lower rate or a discount after the bill. Its GST reduces your input credit.' : 'For a higher rate or an extra charge after the bill. Its GST adds to input credit only if the supplier reports it in GSTR-2B.')}</div>

      <div className="field"><label htmlFor="nt-bill">{tr('Against bill')}</label>
        <select id="nt-bill" className="input" value={billId} onChange={(e) => { setBillId(e.target.value); setIgstMode(undefined); }}>
          <option value="">{tr('No single bill (vendor level — link it later)')}</option>
          {bills.map((b) => <option key={b.id} value={b.id}>{b.invoiceNo ?? '—'} · {fmtDate(b.invoiceDate)} · {fmtInr(b.totalAmount)}</option>)}
        </select>
        {bill?.tdsAmount ? <span className="hint">{tr('TDS on this bill was worked out on the original amount — the CA decides any change.')}</span> : null}
      </div>
      {!billId && (
        <>
          <div className="field"><label htmlFor="nt-head" className="req">{tr('Expense head (for Tally)')}</label>
            <select id="nt-head" className="input" value={headId} onChange={(e) => setHeadId(e.target.value)}>
              <option value="">{tr('Choose')}</option>
              {s.heads.map((h) => <option key={h.id} value={h.id}>{tr(h.name)}</option>)}
            </select></div>
          <label className="row small"><input type="checkbox" checked={itc} onChange={(e) => setItc(e.target.checked)} /> {tr('Input credit was claimed on the purchase this note relates to')}</label>
        </>
      )}

      <div className="row wrap">
        <div className="field grow"><label htmlFor="nt-no" className="req">{tr('Note number')}</label><input id="nt-no" className="input" value={noteNo} onChange={(e) => setNoteNo(e.target.value)} /></div>
        <div className="field"><label htmlFor="nt-date" className="req">{tr('Note date')}</label><input id="nt-date" type="date" className="input" max={todayIso()} value={noteDate} onChange={(e) => setNoteDate(e.target.value || todayIso())} /></div>
      </div>
      <div className="field"><label htmlFor="nt-reason">{tr('Reason')}</label>
        <select id="nt-reason" className="input" value={reason} onChange={(e) => setReason(e.target.value as VendorNote['reason'])}>
          {NOTE_REASONS.map((r) => <option key={r} value={r}>{tr(REASON_LABEL[r])}</option>)}
        </select></div>
      <div className="row wrap">
        <div className="field grow"><label htmlFor="nt-tx">{tr('Taxable value (₹)')}</label><input id="nt-tx" className="input num" inputMode="decimal" value={taxable} onChange={(e) => setTaxable(e.target.value.replace(/[^0-9.]/g, ''))} /></div>
        <div className="field grow"><label htmlFor="nt-gst">{tr('GST on the note (₹)')}</label><input id="nt-gst" className="input num" inputMode="decimal" value={gst} onChange={(e) => setGst(e.target.value.replace(/[^0-9.]/g, ''))} /></div>
      </div>
      <div className="chips" role="radiogroup" aria-label={tr('Tax type')}>
        <button role="radio" aria-checked={!isIgst} className={`chip ${!isIgst ? 'on' : ''}`} onClick={() => setIgstMode(false)}>CGST + SGST</button>
        <button role="radio" aria-checked={isIgst} className={`chip ${isIgst ? 'on' : ''}`} onClick={() => setIgstMode(true)}>IGST</button>
      </div>
      <div className="totals num">
        {!isIgst && gstAmt > 0 && <div className="row"><span className="muted">CGST / SGST</span><span>{fmtInr(half)} + {fmtInr(half)}</span></div>}
        <div className="row"><span className="muted">{tr('Note total')}</span><b>{fmtInr(total)}</b></div>
        <span className="hint">{tr('Check that this matches the total printed on the note.')}</span>
      </div>
      <div className="field"><label htmlFor="nt-rem">{tr('Remark (optional)')}</label><input id="nt-rem" className="input" maxLength={250} value={remark} onChange={(e) => setRemark(e.target.value)} /></div>
      <div className="field"><label htmlFor="nt-file">{tr('Copy of the note (photo or PDF, optional)')}</label>
        <input id="nt-file" type="file" accept="image/jpeg,image/png,application/pdf" onChange={(e) => setFile(e.target.files?.[0])} /></div>
    </Drawer>
  );
}
