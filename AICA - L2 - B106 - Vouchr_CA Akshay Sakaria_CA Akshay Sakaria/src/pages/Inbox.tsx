// Receipt inbox (Zoho Expense "unreported receipts" idea): drop many bills at once → each is read on the
// device → becomes a draft → someone completes & submits it. Nothing reaches the CA until submitted.
// Order matters: read first (full-quality original), then file a compressed archive copy in Drive.
import { DpdpNote } from '../ui/DpdpNote';
import { useRef, useState, type DragEvent } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '../data/store';
import { useTr } from '../i18n';
import { parseEInvoiceQr } from '../lib/einvoiceQr';
import { parseInvoiceText } from '../lib/extract';
import { pdfQr, pdfText, photoText } from '../lib/docread';
import { compress, findQr, loadImage, sha256Hex } from '../lib/image';
import { fmtDate, fyLabel, todayIso } from '../lib/dates';
import { docName, saveDocument } from '../lib/storage';
import { fmtInr } from '../lib/money';
import { Empty, PageHead, useAttempt, useConfirm, useToast } from '../ui/common';
import { isDemo } from '../lib/backend';
import { Icon } from '../ui/Icon';

const MAX_FILES = 50;
const ACCEPT = /^(image\/(jpeg|png|webp|heic|heif)|application\/pdf)$/;
const mb = (n: number) => (n / (1024 * 1024)).toFixed(1);

export function Inbox() {
  const st = useStore();
  const { scoped, client, me } = st;
  const tr = useTr();
  const attempt = useAttempt();
  const toast = useToast();
  const confirm = useConfirm();
  const ref = useRef<HTMLInputElement>(null);
  const waRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<string>();
  const [readPhotos, setReadPhotos] = useState(false);
  const [drag, setDrag] = useState(false);
  const [saved, setSaved] = useState<{ before: number; after: number }>();
  const drafts = scoped.expenses.filter((e) => e.status === 'draft' && (me?.role !== 'sub_user' || e.createdBy === me.id));
  const admin = me?.role !== 'sub_user';

  async function onFiles(list?: FileList | File[] | null, viaWhatsapp = false) {
    if (!list?.length || !client) return;
    const all = [...list];
    const files = all.filter((f) => ACCEPT.test(f.type)).slice(0, MAX_FILES);
    if (files.length < all.length) toast(tr('{n} file(s) skipped — only photos and PDFs, up to {max} at a time', { n: all.length - files.length, max: MAX_FILES }), true);
    if (!files.length) return;
    const items: Parameters<typeof st.addDrafts>[0] = [];
    const tag = (x: Parameters<typeof st.addDrafts>[0][number]) => ({ ...x, viaWhatsapp });
    const byGstin = (g?: string) => scoped.vendors.find((v) => v.gstin === g)?.name;
    for (const [i, f] of files.entries()) {
      setProgress(tr('Reading {i} of {n}…', { i: i + 1, n: files.length }));
      const hash = await sha256Hex(f);
      try {
        if (f.type === 'application/pdf') {
          const qr = await pdfQr(f).then((q) => (q ? parseEInvoiceQr(q) : null)).catch(() => null);
          if (qr) { items.push({ fileName: f.name, imageHash: hash, vendorGstin: qr.sellerGstin, invoiceNo: qr.docNo, invoiceDate: qr.docDate, totalAmount: qr.totalValue, hsnSac: qr.mainHsn, vendorName: byGstin(qr.sellerGstin) }); continue; }
          const r = parseInvoiceText(await pdfText(f).catch(() => ''), client.gstin);
          items.push({ fileName: f.name, imageHash: hash, ...r, vendorName: byGstin(r.vendorGstin) ?? r.vendorName });
        } else {
          const img = await loadImage(f);
          const q = findQr(img);
          const qr = q ? parseEInvoiceQr(q) : null;
          const base = { fileName: f.name, imageHash: hash, imageDataUrl: compress(img, 320, 0.6) };
          if (qr) items.push({ ...base, vendorGstin: qr.sellerGstin, invoiceNo: qr.docNo, invoiceDate: qr.docDate, totalAmount: qr.totalValue, hsnSac: qr.mainHsn, vendorName: byGstin(qr.sellerGstin) });
          else if (readPhotos) {
            const r = parseInvoiceText(await photoText(f, (p) => setProgress(tr('Reading {i} of {n}…', { i: i + 1, n: files.length }) + ` ${p}%`)).catch(() => ''), client.gstin);
            items.push({ ...base, ...r, vendorName: byGstin(r.vendorGstin) ?? r.vendorName });
          } else items.push(base);
        }
      } catch {
        items.push({ fileName: f.name, imageHash: hash });
      }
    }
    // file the originals in Drive: Vouchr/<Client>/FY …/Bills/ (photos compressed after reading)
    const skip = new Set(scoped.expenses.map((e) => e.imageHash).filter(Boolean));
    let before = 0, after = 0;
    for (const [i, it] of items.entries()) {
      if (it.imageHash && skip.has(it.imageHash)) continue;
      skip.add(it.imageHash!);
      setProgress(tr('Saving {i} of {n} to Drive…', { i: i + 1, n: items.length }));
      const date = it.invoiceDate && it.invoiceDate <= todayIso() ? it.invoiceDate : todayIso();
      try {
        const d = await saveDocument({ clientId: client.id, clientName: client.name, fy: fyLabel(date), kind: 'Bills', file: files[i], name: docName(date, it.vendorName, it.invoiceNo, files[i].name) });
        it.fileId = d.fileId; it.filePath = d.path;
        before += d.before ?? 0; after += d.after ?? 0;
      } catch (err) {
        st.logEvent('error', 'drive_upload', 'File could not be saved: {err}', { err: (err as Error).message });
      }
    }
    setProgress(undefined);
    items.splice(0, items.length, ...items.map(tag));
    setSaved(before ? { before, after } : undefined);
    attempt(() => {
      const r = st.addDrafts(items);
      toast(tr('{n} added to inbox', { n: r.added }) + (r.skipped ? ' · ' + tr('{n} already uploaded, skipped', { n: r.skipped }) : ''));
    });
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    if (!progress) onFiles(e.dataTransfer.files);
  }

  return (
    <div className="content stack" style={{ maxWidth: 860 }}>
      <PageHead title={tr('Inbox')} sub={tr('Upload many bills at once, then complete each one')}>
        <button className="btn primary" onClick={() => ref.current?.click()} disabled={!!progress}><Icon name="upload" size={16} /> {tr('Upload bills')}</button>
      </PageHead>
      <input ref={ref} type="file" multiple accept="image/*,application/pdf" hidden data-testid="inbox-files" onChange={(e) => { onFiles(e.target.files); e.target.value = ''; }} />

      <div className={`dropzone ${drag ? 'on' : ''}`} onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}
        role="button" tabIndex={0} onClick={() => !progress && ref.current?.click()} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && !progress && ref.current?.click()}>
        <Icon name="inbox" size={26} />
        <b>{tr('Drop bill photos or PDFs here')}</b>
        <span className="small muted">{tr('or tap to choose · up to {n} files', { n: MAX_FILES })}</span>
      </div>

      {isDemo && (
        <div className="card pad row wrap" style={{ gap: 10, background: 'var(--surface-2)' }}>
          <span className="grow small">💬 <b>{tr('Demo: simulate a bill sent on WhatsApp')}</b> — {tr('live, staff send bills to the firm’s WhatsApp number and they appear here automatically.')}</span>
          <button className="btn sm" disabled={!!progress} onClick={() => (me?.whatsappVerifiedAt ? waRef.current?.click() : toast(tr('Add and confirm your WhatsApp number first (Settings → Team, then Privacy & consent).'), true))}>{tr('Simulate')}</button>
          <input ref={waRef} type="file" accept="image/jpeg,image/png,application/pdf" hidden onChange={(e) => { onFiles(e.target.files, true); e.target.value = ''; }} />
        </div>
      )}
      <DpdpNote kind="bills" />
      <label className="row small"><input type="checkbox" checked={readPhotos} onChange={(e) => setReadPhotos(e.target.checked)} /> {tr('Also read the text in photos (slower — about 5–10 seconds per photo)')}</label>
      {progress && <div className="banner info busy"><Icon name="refresh" size={18} /> {progress}</div>}
      {saved && saved.after < saved.before && (
        <div className="banner ok"><Icon name="check" size={18} /><span>{tr('Photos compressed for the archive: {before} MB → {after} MB. PDFs are kept exactly as received.', { before: mb(saved.before), after: mb(saved.after) })}</span></div>
      )}
      <div className="hint">{tr('PDFs and e-invoice QR codes are read on your device — nothing is sent anywhere.')}{admin && <> {tr('Have the bills in an Excel register instead?')} <Link to="/import" className="linkish">{tr('Import from Excel')}</Link></>}</div>

      <div className="card">
        {drafts.length === 0 ? <Empty art="tray">{tr('Inbox is empty.')}</Empty> : (
          <div className="list">
            {drafts.map((e) => (
              <div key={e.id} className="list-item">
                {e.imageDataUrl ? <img className="photo-thumb" style={{ width: 40, height: 52 }} src={e.imageDataUrl} alt="" /> : <div className="avatar"><b className="tiny">PDF</b></div>}
                <div className="grow">
                  <div className="ellipsis" style={{ fontWeight: 600 }}>{e.vendorName || e.attachmentName || tr('Unknown vendor')}{e.entrySource === 'whatsapp' && <span className="badge ok" style={{ marginLeft: 6 }}>💬 {tr('via WhatsApp')}</span>}</div>
                  <div className="muted tiny">{e.invoiceNo ? `#${e.invoiceNo} · ` : ''}{fmtDate(e.invoiceDate)}{e.totalAmount ? ` · ${fmtInr(e.totalAmount)}` : ''}</div>
                </div>
                <Link to={`/capture?edit=${e.id}`} className="btn sm primary">{tr('Complete')}</Link>
                <button className="icon-btn" aria-label={tr('Delete')} onClick={async () => { if (await confirm(tr('Delete this draft?'), { danger: true, ok: tr('Delete') })) st.deleteDraft(e.id); }}><Icon name="x" size={16} /></button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
