// The one screen staff use every day. Rules: big targets, few fields, bill total (not taxable value),
// no tax jargon, everything else is inferred and checked later by the CA team.
import { DpdpNote } from '../ui/DpdpNote';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { LookAlikeError, RuleError, useStore, type NewExpenseInput } from '../data/store';
import type { Expense } from '../data/types';
import { useLang, useT, useTr } from '../i18n';
import { ALL_GST_RATES, gstRatesOn, NO_IMAGE_REASONS } from '../data/masters';
import { checkGstin } from '../lib/validators';
import { parseEInvoiceQr, verifyQrSignature, type QrSignature } from '../lib/einvoiceQr';
import { compress, findQr, loadImage, sha256Hex } from '../lib/image';
import { isDemo } from '../lib/backend';
import { fmtDate, fyLabel, isBackdatedEntry, toIso, todayIso } from '../lib/dates';
import { parseInvoiceText, type InvoiceFields } from '../lib/extract';
import { downloadOcr, ocrDownloaded, pdfQr, pdfText, photoText, ReadCancelled } from '../lib/docread';
import { dHashOf, hamming, LOOKALIKE_MAX_BITS } from '../lib/phash';
import { stateName } from '../lib/states';
import { docName, saveDocument } from '../lib/storage';
import { cleanAmount, fmtInr, round2, splitFromTotal } from '../lib/money';
import { CaptureAi, type CaptureFill } from '../ui/CaptureAi';
import { Icon } from '../ui/Icon';
import { useToast } from '../ui/common';
import { newLine, PaymentLines, toPaymentLines, type LineDraft } from '../ui/PaymentLines';

const MAX_FILE = 10 * 1024 * 1024;


export function Capture() {
  const st = useStore();
  const { me, client, scoped } = st;
  const t = useT();
  const lang = useLang();
  const toast = useToast();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const cameraRef = useRef<HTMLInputElement>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const readAbort = useRef<AbortController>();
  const [ocrReady, setOcrReady] = useState<boolean>();
  const [ocrDl, setOcrDl] = useState<string>();
  useEffect(() => { ocrDownloaded().then(setOcrReady).catch(() => setOcrReady(false)); }, []);

  /** F8: a photo that looks almost the same as a bill photo of the last 90 days (re-photographed or re-sent) — warn only. */
  async function lookAlikePhoto(thumb: string): Promise<Expense | undefined> {
    if (!client) return undefined;
    const since = toIso(new Date(Date.now() - 90 * 864e5));
    const h = await dHashOf(thumb).catch(() => undefined);
    if (!h) return undefined;
    for (const x of scoped.expenses.filter((e) => e.imageDataUrl && e.invoiceDate >= since && e.status !== 'rejected' && e.id !== editing?.id)) {
      const hx = await dHashOf(x.imageDataUrl!).catch(() => undefined);
      if (hx && hamming(h, hx) <= LOOKALIKE_MAX_BITS) return x;
    }
    return undefined;
  }

  const editing: Expense | undefined = scoped.expenses.find((x) => x.id === params.get('edit') && (x.status === 'rejected' || x.status === 'draft'));

  const [saved, setSaved] = useState<Expense>();
  const [busy, setBusy] = useState(false);
  const [photo, setPhoto] = useState<string | undefined>(editing?.imageDataUrl);
  const [fileName, setFileName] = useState<string | undefined>(editing?.attachmentName);
  const [imageHash, setImageHash] = useState<string | undefined>(editing?.imageHash);
  const [source, setSource] = useState<Expense['entrySource']>(editing?.entrySource ?? 'manual');
  const [notice, setNotice] = useState<{ tone: 'ok' | 'info' | 'warn'; text: string }>();
  const [irn, setIrn] = useState<string | undefined>(editing?.irn);
  const [irnSig, setIrnSig] = useState<QrSignature | undefined>(editing?.irnSignature);
  const checkSig = (jwt: string) => { verifyQrSignature(jwt, st.s.firm.irpPublicKeyPem).then(setIrnSig).catch(() => setIrnSig('unchecked')); };

  const [vendorName, setVendorName] = useState(editing?.vendorName ?? '');
  const [vendorGstin, setVendorGstin] = useState(editing?.status === 'draft' ? /GSTIN (\S{15})/.exec(editing.description ?? '')?.[1] ?? '' : '');
  const [invoiceNo, setInvoiceNo] = useState(editing?.invoiceNo ?? '');
  const [invoiceDate, setInvoiceDate] = useState(editing?.invoiceDate ?? todayIso());
  const [total, setTotal] = useState(editing ? String(editing.totalAmount) : '');
  const [rate, setRate] = useState<number | undefined>(editing ? gstRateOf(editing) : undefined);
  const [showDiscount, setShowDiscount] = useState(!!editing?.discount);
  // travel / booking portals: part of the total has no GST on this bill · section 9(5): the app (ECO) pays the GST
  const [nonTax, setNonTax] = useState(editing?.nonTaxableAmount ? String(editing.nonTaxableAmount) : '');
  const [showNonTax, setShowNonTax] = useState(!!editing?.nonTaxableAmount);
  const [eco, setEco] = useState(!!editing?.ecoPaysTax);
  // follow the bill: place of supply decides CGST+SGST vs IGST, which is not always the vendor's state (e.g. bookings)
  const [taxKind, setTaxKind] = useState<'intra' | 'inter' | undefined>(editing ? (editing.igst ? 'inter' : editing.cgst ? 'intra' : undefined) : undefined);
  const [ecoGstin, setEcoGstin] = useState(editing?.ecoGstin ?? '');
  const [discount, setDiscount] = useState(editing?.discount ? String(editing.discount) : '');
  const [hsn, setHsn] = useState(editing?.hsnSac ?? '');
  const [desc, setDesc] = useState(editing?.status === 'draft' ? '' : editing?.description ?? '');
  const [reason, setReason] = useState(() => NO_IMAGE_REASONS.find((r) => r.en === editing?.noImageReason)?.code ?? (editing?.noImageReason ? 'other' : ''));
  const [otherReason, setOtherReason] = useState(editing?.noImageReason && !NO_IMAGE_REASONS.some((r) => r.en === editing.noImageReason) ? editing.noImageReason : '');
  const tr = useTr();
  const [paidNow, setPaidNow] = useState(false);
  const [lines, setLines] = useState<LineDraft[]>([]);
  const [lookAlike, setLookAlike] = useState<Expense>();
  const [confirmedDifferent, setConfirmedDifferent] = useState<string>();
  const [ocrPct, setOcrPct] = useState<number>();
  const [original, setOriginal] = useState<File>(); // the full file, filed in Drive on save
  const [storedDoc, setStoredDoc] = useState<{ fileId: string; filePath: string }>(); // uploaded once, reused on retries
  const [narration, setNarration] = useState(editing?.narration ?? '');
  const [costCentreId, setCostCentreId] = useState(editing?.costCentreId ?? '');
  const centres = client?.costCentres.filter((c) => c.active || c.id === editing?.costCentreId) ?? [];

  // open the camera / picker straight away when coming from Home
  useEffect(() => {
    if (editing) return;
    if (params.get('mode') === 'photo') cameraRef.current?.click();
    if (params.get('mode') === 'file') uploadRef.current?.click();
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  const knownVendor = scoped.vendors.find((v) => v.name.toLowerCase() === vendorName.trim().toLowerCase());
  useEffect(() => {
    if (knownVendor?.gstin && !vendorGstin) setVendorGstin(knownVendor.gstin);
  }, [knownVendor?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const gstinCheck = vendorGstin.trim() ? checkGstin(vendorGstin) : undefined;
  // GST default: 18% when the vendor is GST-registered, otherwise "No GST" — until the user picks one
  const effectiveRate = rate ?? (gstinCheck?.ok || knownVendor?.gstRegistered ? 18 : 0);
  const interState = taxKind ? taxKind === 'inter' : !!(gstinCheck?.ok && client?.stateCode && gstinCheck.stateCode !== client.stateCode);
  const totalNum = Number(total) || 0;
  // slabs valid on the bill date (GST 2.0 from 22-09-2025); a rate read from the bill is always kept selectable
  const rateChoices = useMemo(() => { const base = gstRatesOn(invoiceDate); return base.includes(effectiveRate) ? base : [...base, effectiveRate].sort((a, b) => a - b); }, [invoiceDate, effectiveRate]);
  const nonTaxNum = showNonTax ? Number(nonTax) || 0 : 0;
  // GST is split only from the part of the total that carries GST on this bill
  const split = useMemo(() => splitFromTotal(Math.max(totalNum - nonTaxNum, 0), effectiveRate, interState), [totalNum, nonTaxNum, effectiveRate, interState]);
  const discountNum = showDiscount ? Number(discount) || 0 : 0;

  const staff = me?.role === 'sub_user';
  const today = todayIso();
  const backdated = client ? isBackdatedEntry(invoiceDate, today, client.backdateWindowDays) : false;
  const minDate = staff && client && !editing
    ? (() => { const d = new Date(today + 'T00:00:00'); d.setDate(d.getDate() - client.backdateWindowDays); const w = toIso(d); const m = today.slice(0, 8) + '01'; return w < m ? w : m; })()
    : undefined;
  const locked = client ? st.isLocked(client.id, invoiceDate) : false;
  const hasFile = !!photo || !!fileName;
  const reasonText = reason === 'other' ? otherReason.trim() : NO_IMAGE_REASONS.find((r) => r.code === reason)?.en;

  /** Fill only empty fields — never overwrite what the user already typed. */
  function fillFrom(r: Partial<InvoiceFields> & { description?: string }) {
    if (r.vendorGstin && !vendorGstin) setVendorGstin(r.vendorGstin);
    const v = r.vendorGstin ? scoped.vendors.find((x) => x.gstin === r.vendorGstin) : undefined;
    if (!vendorName && (v?.name || r.vendorName)) setVendorName(v?.name ?? r.vendorName!);
    if (r.invoiceNo && !invoiceNo) setInvoiceNo(r.invoiceNo);
    if (r.invoiceDate && r.invoiceDate <= todayIso()) setInvoiceDate(r.invoiceDate);
    if (r.totalAmount && !total) setTotal(String(r.totalAmount));
    if (r.gstRatePct !== undefined && ALL_GST_RATES.includes(r.gstRatePct)) setRate(r.gstRatePct);
    if (r.hsnSac && !hsn) setHsn(r.hsnSac);
    if (r.discount) { setShowDiscount(true); setDiscount(String(r.discount)); }
    if (r.description && !desc) setDesc(r.description);
    if (r.irn && !irn) setIrn(r.irn); // e-invoice IRN printed on the PDF
    if (r.taxKind) setTaxKind(r.taxKind);
    if (r.nonTaxable && !nonTax) { setShowNonTax(true); setNonTax(String(r.nonTaxable)); }
    if (r.ecoPaysTax) { setEco(true); if (r.ecoGstin && !ecoGstin) setEcoGstin(r.ecoGstin); }
  }

  async function onFile(f?: File) {
    if (!f || !client) return;
    if (f.size > MAX_FILE) { toast(t('fileTooBig'), true); return; }
    setNotice(undefined);
    if (f.type === 'application/pdf') {
      setBusy(true);
      try {
        const hash = await sha256Hex(f);
        const dup = st.findDuplicate(client.id, '', undefined, hash, editing?.id);
        if (dup) { setNotice({ tone: 'warn', text: `${t('photoDup')} (${dup.vendorName} ${dup.invoiceNo ?? ''}).` }); return; }
        setPhoto(undefined); setFileName(f.name); setImageHash(hash); setSource('pdf'); setReason(''); setOriginal(f); setStoredDoc(undefined);
        // 1) e-invoice QR printed in the PDF  2) the PDF's own text layer (e-mailed / downloaded bills)
        const qrText = await pdfQr(f).catch(() => null);
        const qr = qrText ? parseEInvoiceQr(qrText) : null;
        if (qr) {
          setSource('qr');
          fillFrom({ vendorGstin: qr.sellerGstin, invoiceNo: qr.docNo, invoiceDate: qr.docDate, totalAmount: qr.totalValue, hsnSac: qr.mainHsn });
          setIrn(qr.irn);
          checkSig(qrText!);
          setNotice({ tone: 'ok', text: t('qrFound') });
          return;
        }
        const text = await pdfText(f).catch(() => '');
        const r = text.trim() ? parseInvoiceText(text, client.gstin) : undefined;
        if (r && r.found >= 2) {
          fillFrom(r);
          setNotice({ tone: 'ok', text: tr('Read {n} details from the PDF — please check them.', { n: r.found }) });
        } else {
          setNotice({ tone: 'info', text: text.trim() ? t('readFail') : tr('This PDF is a scanned image — please type the details.') });
        }
      } catch (err) {
        st.logEvent('warn', 'client_app', 'PDF read failed: {err}', { err: (err as Error).message });
        setNotice({ tone: 'info', text: t('readFail') });
      } finally { setBusy(false); }
      return;
    }
    setBusy(true);
    try {
      const hash = await sha256Hex(f);
      const dup = st.findDuplicate(client.id, '', undefined, hash, editing?.id);
      if (dup) { setNotice({ tone: 'warn', text: `${t('photoDup')} (${dup.vendorName} ${dup.invoiceNo ?? ''}).` }); return; }
      // F6: iPhone HEIC photos — most browsers other than Safari cannot open them. Keep the file as the bill; no preview.
      const heic = /image\/hei[cf]/i.test(f.type) || /\.hei[cf]$/i.test(f.name);
      const img = await loadImage(f).catch((err) => { if (heic) return null; throw err; });
      if (!img) {
        setPhoto(undefined); setFileName(f.name); setImageHash(hash); setSource('photo'); setReason(''); setOriginal(f); setStoredDoc(undefined);
        setNotice({ tone: 'warn', text: tr('iPhone HEIC photo: this browser cannot show or read it. It is kept as the bill file — please type the details. Tip: on the iPhone, Settings → Camera → Formats → Most Compatible saves photos as JPEG.') });
        return;
      }
      const thumb = compress(img, 320, 0.6);
      setPhoto(thumb); setFileName(f.name); setImageHash(hash); setSource('photo'); setReason(''); setOriginal(f); setStoredDoc(undefined);
      lookAlikePhoto(thumb).then((x) => { if (x) toast(tr('This photo looks like a bill already recorded: {vendor} {no} ({date}). Check it is not the same bill.', { vendor: x.vendorName, no: x.invoiceNo ?? '', date: fmtDate(x.invoiceDate) }), true); }).catch(() => undefined);

      // 1) e-Invoice QR — free, exact
      const qrText = findQr(img);
      const qr = qrText ? parseEInvoiceQr(qrText) : null;
      if (qr) {
        setSource('qr');
        setVendorGstin(qr.sellerGstin);
        setInvoiceNo(qr.docNo);
        if (qr.docDate) setInvoiceDate(qr.docDate);
        setTotal(String(qr.totalValue));
        if (qr.mainHsn) setHsn(qr.mainHsn);
        setIrn(qr.irn);
        checkSig(qrText!);
        const v = scoped.vendors.find((x) => x.gstin === qr.sellerGstin);
        if (v) setVendorName(v.name);
        setNotice({ tone: 'ok', text: t('qrFound') });
        return;
      }
      // 3) free on-device OCR (no AI connected): slower, so we show progress and the user checks every field
        setOcrPct(0);
        readAbort.current = new AbortController();
        let stopped: ReadCancelled | undefined;
        const text = await photoText(f, setOcrPct, readAbort.current.signal).catch((err) => { if (err instanceof ReadCancelled) stopped = err; return ''; });
        readAbort.current = undefined;
        setOcrPct(undefined);
        ocrDownloaded().then(setOcrReady).catch(() => undefined);
        if (stopped) { setNotice({ tone: 'info', text: tr(stopped.timedOut ? 'Reading took too long on this phone — please type the details.' : 'Reading stopped — please type the details.') }); return; }
        const r = text.trim() ? parseInvoiceText(text, client.gstin) : undefined;
        if (r && r.found >= 2) {
          fillFrom(r);
          setNotice({ tone: r.gstinRepaired ? 'warn' : 'ok', text: tr('Read {n} details from the photo — please check them carefully.', { n: r.found }) + (r.gstinRepaired ? ' ' + tr('The GSTIN was corrected from a photo misread and passes the check digit — compare it with the bill.') : '') });
        } else {
          setNotice({ tone: 'info', text: isDemo ? t('readingDemo') : t('readFail') });
        }
    } catch (err) {
      st.logEvent('error', 'client_app', 'Photo processing failed: {err}', { err: (err as Error).message });
      setNotice({ tone: 'warn', text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  // first blocking problem, shown under the Save button so nobody is left guessing
  const problem =
    vendorName.trim().length < 2 ? t('needVendor')
    : !(totalNum > 0) ? t('needAmount')
    : gstinCheck && !gstinCheck.ok ? t('badGstin')
    : discountNum >= totalNum ? t('discountTooBig')
    : nonTaxNum >= totalNum && nonTaxNum > 0 ? tr('Non-GST charges must be less than the bill total')
    : eco && ecoGstin.trim() && !checkGstin(ecoGstin).ok ? tr('GSTIN of the app / operator is not valid')
    : !hasFile && !reasonText ? t('needPhotoOrReason')
    : client && totalNum > client.noteAboveAmount && !desc.trim() ? tr('Bills above {amount} need a note: what was it for?', { amount: fmtInr(client.noteAboveAmount) })
    : paidNow && round2(lines.reduce((x, l) => x + (Number(l.amount) || 0), 0)) > totalNum + 0.01 ? tr('Paid amount is more than the bill total')
    : locked ? t('monthLocked')
    : staff && backdated && (!editing || editing.invoiceDate !== invoiceDate) ? t('pastMonthStaff')
    : undefined;

  /** AI fills only facts that passed every truth check (see CaptureAi); the person still reviews and saves. */
  function applyAi(f: CaptureFill) {
    if (f.vendorName) setVendorName(f.vendorName);
    if (f.vendorGstin) setVendorGstin(f.vendorGstin);
    if (f.invoiceNo) setInvoiceNo(f.invoiceNo.slice(0, 30));
    if (f.invoiceDate && f.invoiceDate <= todayIso()) setInvoiceDate(f.invoiceDate);
    if (f.total) setTotal(String(f.total));
    if (f.rate !== undefined) setRate(f.rate);
    if (f.description) setDesc(f.description.slice(0, 120));
    if (f.irn) setIrn(f.irn);
    if (f.nonTaxable) { setShowNonTax(true); setNonTax(String(f.nonTaxable)); }
    if (f.ecoPaysTax) { setEco(true); if (f.ecoGstin) setEcoGstin(f.ecoGstin); }
    if (f.paid && f.payMode) { setPaidNow(true); setLines([newLine(f.total ? String(f.total) : total, client?.bankAccounts, f.payMode)]); }
  }

  async function save() {
    if (!client) return;
    // 1) file the original in Google Drive (client / FY / Bills) — only for a newly attached file
    let stored: { fileId?: string; filePath?: string } = storedDoc ?? { fileId: editing?.fileId, filePath: editing?.filePath };
    if (original && !storedDoc) {
      setBusy(true);
      try {
        const d = await saveDocument({ clientId: client.id, clientName: client.name, fy: fyLabel(invoiceDate), kind: 'Bills', file: original,
          name: docName(invoiceDate, vendorName.trim(), invoiceNo.trim(), original.name) });
        stored = { fileId: d.fileId, filePath: d.path };
        setStoredDoc({ fileId: d.fileId, filePath: d.path });
      } catch (err) {
        setBusy(false);
        st.logEvent('error', 'drive_upload', 'File could not be saved: {err}', { err: (err as Error).message });
        toast(tr('Could not save the bill file — check your connection and try again.'), true);
        return;
      }
      setBusy(false);
    }
    const input: NewExpenseInput = {
      ...stored, narration: narration.trim() || undefined, costCentreId: costCentreId || undefined,
      vendorId: knownVendor?.id, vendorName: vendorName.trim(), vendorGstin: gstinCheck?.ok ? vendorGstin.trim().toUpperCase() : undefined,
      invoiceNo: invoiceNo.trim(), invoiceDate, entrySource: hasFile ? source : 'manual', irn, irnSignature: irn ? irnSig : undefined, imageHash,
      imageDataUrl: photo, attachmentName: photo ? undefined : fileName, noImageReason: hasFile ? undefined : reasonText,
      description: desc.trim() || undefined, hsnSac: hsn.trim() || undefined,
      grossAmount: round2(split.taxableValue + discountNum), discount: discountNum, ...split, totalAmount: round2(split.totalAmount + nonTaxNum),
      nonTaxableAmount: nonTaxNum || undefined, ecoPaysTax: eco || undefined, ecoGstin: eco && ecoGstin.trim() ? ecoGstin.trim().toUpperCase() : undefined,
      payments: paidNow ? toPaymentLines(lines) : undefined,
      notDuplicateOf: confirmedDifferent
    };
    try {
      if (editing) {
        st.completeExpense(editing.id, input);
        toast(editing.status === 'draft' ? tr('Submitted to CA') : t('resubmitted'));
        nav(editing.status === 'draft' ? '/inbox' : '/entries');
        return;
      }
      setSaved(st.addExpense(input));
    } catch (err) {
      if (err instanceof LookAlikeError) { setLookAlike(err.existing); return; }
      if (err instanceof RuleError) toast(tr(err.message, err.vars), true);
      else throw err;
    }
  }

  function reset() {
    setSaved(undefined); setPhoto(undefined); setFileName(undefined); setImageHash(undefined); setNotice(undefined); setIrn(undefined);
    setVendorName(''); setVendorGstin(''); setInvoiceNo(''); setInvoiceDate(todayIso()); setTotal(''); setRate(undefined); setTaxKind(undefined); setNonTax(''); setShowNonTax(false); setEco(false); setEcoGstin('');
    setShowDiscount(false); setDiscount(''); setHsn(''); setDesc(''); setPaidNow(false); setLines([]); setLookAlike(undefined); setConfirmedDifferent(undefined); setSource('manual');
    setReason(''); setOtherReason(''); setOriginal(undefined); setStoredDoc(undefined); setNarration(''); setCostCentreId('');
  }

  const fileInputs = (
    <>
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
      <input ref={uploadRef} type="file" accept="image/*,application/pdf" hidden onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
    </>
  );

  if (saved) {
    const netToPay = round2(saved.totalAmount - saved.tdsAmount);
    return (
      <div className="content narrow">
        <div className="success card">
          <div className="tick"><Icon name="check" size={44} stroke={2.4} /></div>
          <h1>{t('saved')}</h1>
          <p className="muted" style={{ maxWidth: 320, margin: '8px auto 16px' }}>{t('savedHint')}</p>
          {saved.tdsAmount > 0 && !paidNow && (
            <div className="banner warn" style={{ maxWidth: 340, margin: '0 auto 16px', textAlign: 'left' }}>
              <Icon name="info" size={18} />
              <span>{lang === 'hi'
                ? <>विक्रेता को केवल <b>{fmtInr(netToPay)}</b> दें। {fmtInr(saved.tdsAmount)} TDS काटा जाएगा (CA पुष्टि करेंगे)।</>
                : <>{tr('Pay the vendor only')} <b>{fmtInr(netToPay)}</b>. {tr('{amount} TDS is to be deducted (CA will confirm).', { amount: fmtInr(saved.tdsAmount) })}</>}</span>
            </div>
          )}
          <div className="stack" style={{ maxWidth: 320, margin: '0 auto' }}>
            <button className="btn primary lg block" onClick={() => { reset(); cameraRef.current?.click(); }}><Icon name="camera" /> {t('another')}</button>
            <button className="btn lg block" onClick={() => nav('/')}>{t('done')}</button>
          </div>
        </div>
        {fileInputs}
      </div>
    );
  }

  return (
    <div className="content narrow stack">
      <div className="row">
        <button className="icon-btn" onClick={() => nav(-1)} aria-label="Back"><Icon name="arrowLeft" /></button>
        <h1 className="grow">{editing?.status === 'draft' ? tr('Complete & submit') : editing ? t('fixResubmit') : hasFile ? t('snap') : t('typeIt')}</h1>
      </div>
      {fileInputs}

      {editing?.reviewNote && <div className="banner warn"><Icon name="alert" size={18} /><span><b>{t('caNote')}:</b> {editing.reviewNote}</span></div>}

      {hasFile ? (
        <div className="card pad row">
          {photo ? <img className="photo-thumb" src={photo} alt="" /> : <div className="photo-thumb" style={{ display: 'grid', placeItems: 'center' }}><b className="small">PDF</b></div>}
          <div className="grow stack" style={{ gap: 6 }}>
            <span className={`badge ${source === 'qr' ? 'ok' : 'info'}`}>{source === 'qr' ? 'e-Invoice QR' : photo ? t('photo') : t('attached')}</span>
            {fileName && <span className="small ellipsis">{fileName}</span>}
            {!original && editing?.filePath && <span className="tiny muted ellipsis" title={editing.filePath}>📁 {editing.filePath}</span>}
            <div className="row">
              <button className="linkish" onClick={() => cameraRef.current?.click()}>{t('retake')}</button>
              <button className="linkish" onClick={() => { setPhoto(undefined); setFileName(undefined); setImageHash(undefined); setSource('manual'); setNotice(undefined); setOriginal(undefined); setStoredDoc(undefined); }}>✕</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="stack">
          <div className="alt-actions">
            <button className="btn lg" onClick={() => cameraRef.current?.click()} disabled={busy}><Icon name="camera" /> {t('photo')}</button>
            <button className="btn lg" onClick={() => uploadRef.current?.click()} disabled={busy}><Icon name="upload" /> PDF</button>
          </div>
          <div className="card pad stack" style={{ gap: 8 }}>
            <label className="small" style={{ fontWeight: 600 }} htmlFor="reason">{t('noBill')}{!hasFile && <span className="req" aria-hidden="true" />}</label>
            <select id="reason" className="input" aria-required={!hasFile} value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="">{t('chooseReason')}</option>
              {NO_IMAGE_REASONS.filter((r) => r.code !== 'imported').map((r) => <option key={r.code} value={r.code}>{lang === 'hi' ? r.hi : r.en}</option>)}
            </select>
            {reason === 'other' && <input className="input" value={otherReason} onChange={(e) => setOtherReason(e.target.value)} placeholder={t('otherReason')} />}
          </div>
        </div>
      )}

      <CaptureAi file={original} buyerGstin={client?.gstin} onApply={applyAi} />
      <DpdpNote kind="bills" />

      {busy && <div className="banner info busy"><Icon name="refresh" size={18} /> <span className="grow">{t('reading')}{ocrPct !== undefined ? ` ${ocrPct}%` : ''}</span>
        {ocrPct !== undefined && <button className="btn sm" onClick={() => readAbort.current?.abort()}>{tr('Cancel reading')}</button>}</div>}
      {ocrReady === false && !busy && location.protocol !== 'file:' && (
        <div className="hint">{ocrDl ?? <>{tr('Photos without a QR code are read on this phone. First use downloads the reader (about 7 MB).')} <button className="linkish" onClick={() => downloadOcr((d, n) => setOcrDl(tr('Downloading {d} of {n}…', { d, n }))).then(() => { setOcrDl(undefined); setOcrReady(true); toast(tr('Offline reading ready')); }).catch(() => { setOcrDl(undefined); toast(tr('Download failed — try again on Wi-Fi.'), true); })}>{tr('Download now (Wi-Fi)')}</button></>}</div>
      )}
      {notice && <div className={`banner ${notice.tone}`}><Icon name={notice.tone === 'ok' ? 'check' : 'info'} size={18} /><span>{notice.text}</span></div>}
      {irn && irnSig && (
        <div className={`banner small ${irnSig === 'valid' ? 'ok' : irnSig === 'invalid' ? 'danger' : 'info'}`} role="status">
          <Icon name={irnSig === 'valid' ? 'check' : 'alert'} size={16} />
          <span>{irnSig === 'valid' ? tr('E-invoice QR signature verified with the IRP key.')
            : irnSig === 'invalid' ? tr('E-invoice QR signature does NOT match the IRP key — check the IRN on the e-invoice portal before paying.')
            : tr('E-invoice QR read — signature not checked (the CA firm has not saved the IRP public key).')}</span>
        </div>
      )}

      <p className="tiny muted req-legend"><b>*</b> {tr('Required')}</p>
      <div className="card pad stack">
        <div className="field">
          <label htmlFor="v" className="req">{t('vendor')}</label>
          <input id="v" aria-required="true" className="input" list="vendors" value={vendorName} onChange={(e) => setVendorName(e.target.value)} autoComplete="off" placeholder="e.g. Paper House Stationers" />
          <datalist id="vendors">{scoped.vendors.map((v) => <option key={v.id} value={v.name} />)}</datalist>
          {knownVendor && <span className="hint ok">✓ {t('savedVendor')}{knownVendor.gstin ? ` · GSTIN ${knownVendor.gstin}` : ` · ${t('notRegistered')}`}</span>}
        </div>

        {!knownVendor?.gstin && (
          <div className="field">
            <label htmlFor="g">{t('vendorGstin')}</label>
            <input id="g" className="input mono" style={{ fontSize: 16, textTransform: 'uppercase' }} maxLength={15} value={vendorGstin}
              onChange={(e) => setVendorGstin(e.target.value.toUpperCase().replace(/[^0-9A-Z]/g, ''))} placeholder="27ABCDE1234F1Z5" />
            {gstinCheck && <span className={`hint ${gstinCheck.ok ? 'ok' : 'err'}`}>{gstinCheck.ok ? `✓ ${t('gstinOk')} · ${stateName(vendorGstin) ?? ''}${interState ? ' · IGST' : ''}` : tr(gstinCheck.reason ?? '')}</span>}
          </div>
        )}

        <div className="row" style={{ alignItems: 'flex-start' }}>
          <div className="field grow">
            <label htmlFor="n">{t('invoiceNo')}</label>
            <input id="n" className="input" value={invoiceNo} maxLength={30} onChange={(e) => setInvoiceNo(e.target.value)} />
          </div>
          <div className="field grow">
            <label htmlFor="d" className="req">{t('invoiceDate')}</label>
            <input id="d" type="date" className="input" value={invoiceDate} min={minDate} max={today} onChange={(e) => setInvoiceDate(e.target.value || today)} />
          </div>
        </div>
        {staff && backdated && (!editing || editing.invoiceDate !== invoiceDate) && <div className="hint err">{t('pastMonthStaff')}</div>}
        {locked && <div className="hint err">{t('monthLocked')}</div>}
        {!staff && backdated && !locked && <div className="hint" style={{ color: 'var(--warn)' }}>{t('pastDatedAdmin')}</div>}
      </div>

      <div className="card pad stack">
        <div className="field">
          <label htmlFor="amt" className="req">{t('total')}</label>
          <input id="amt" aria-required="true" className="input amount" inputMode="decimal" value={total} onChange={(e) => setTotal(cleanAmount(e.target.value))} placeholder="₹ 0" />
        </div>
        <div className="field">
          <label>{t('gstRate')}</label>
          <div className="chips" role="radiogroup" aria-label={t('gstRate')}>
            {rateChoices.map((r) => (
              <button key={r} type="button" role="radio" aria-checked={effectiveRate === r} className={`chip ${effectiveRate === r ? 'on' : ''}`} onClick={() => setRate(r)}>{r === 0 ? t('noGst') : `${r}%`}</button>
            ))}
          </div>
          {effectiveRate > 0 && !gstinCheck?.ok && !knownVendor?.gstin && <span className="hint" style={{ color: 'var(--warn)' }}>{t('gstNoGstin')}</span>}
        </div>

        {showDiscount ? (
          <div className="field">
            <label htmlFor="disc">{t('discount')}</label>
            <input id="disc" className="input" inputMode="decimal" value={discount} onChange={(e) => setDiscount(cleanAmount(e.target.value))} placeholder="₹ 0" />
          </div>
        ) : <button className="linkish" onClick={() => setShowDiscount(true)}>{t('addDiscount')}</button>}

        {showNonTax ? (
          <div className="field">
            <label htmlFor="nontax">{tr('Charges without GST on this bill')}</label>
            <input id="nontax" className="input" inputMode="decimal" value={nonTax} onChange={(e) => setNonTax(cleanAmount(e.target.value))} placeholder="₹ 0" />
            <span className="hint">{tr('e.g. air / rail fare a travel site collects for the airline or IRCTC. Enter it exactly as printed; GST is worked out only on the rest.')}</span>
          </div>
        ) : <button className="linkish" onClick={() => setShowNonTax(true)}>{tr('+ Part of the bill has no GST (travel bookings)')}</button>}

        <label className="row small consent-check"><input type="checkbox" checked={eco} onChange={(e) => setEco(e.target.checked)} /> <span>{tr('GST paid by the app — Zomato, Swiggy, Uber, Ola etc. (section 9(5))')}</span></label>
        {eco && (
          <div className="field">
            <label htmlFor="ecog">{tr('App / operator GSTIN (if printed)')}</label>
            <input id="ecog" className="input mono" maxLength={15} value={ecoGstin} onChange={(e) => setEcoGstin(e.target.value.toUpperCase().replace(/[^0-9A-Z]/g, ''))} />
          </div>
        )}

        {totalNum > 0 && (
          <div className="totals num">
            {discountNum > 0 && <div className="row"><span className="muted">{t('beforeDiscount')}</span><span>{fmtInr(split.taxableValue + discountNum)}</span></div>}
            {discountNum > 0 && <div className="row"><span className="muted">{t('discount')}</span><span>− {fmtInr(discountNum)}</span></div>}
            <div className="row"><span className="muted">{t('taxable')}</span><span>{fmtInr(split.taxableValue)}</span></div>
            {split.igst > 0 && <div className="row"><span className="muted">IGST</span><span>{fmtInr(split.igst)}</span></div>}
            {split.cgst > 0 && <div className="row"><span className="muted">CGST + SGST</span><span>{fmtInr(split.cgst)} + {fmtInr(split.sgst)}</span></div>}
            {nonTaxNum > 0 && <div className="row"><span className="muted">{tr('Charges without GST')}</span><span>{fmtInr(nonTaxNum)}</span></div>}
            <div className="row grand"><span>{t('total')}</span><span>{fmtInr(round2(split.totalAmount + nonTaxNum))}</span></div>
          </div>
        )}

        <div className="field">
          <label htmlFor="desc" className={client && totalNum > client.noteAboveAmount ? 'req' : undefined}>{t('whatFor')}</label>
          <input id="desc" className="input" value={desc} maxLength={120} onChange={(e) => setDesc(e.target.value)} placeholder="e.g. printer paper, courier, repair" />
        </div>
        {centres.length > 0 && (
          <div className="field">
            <label>{tr('Project / branch (optional)')}</label>
            <div className="chips" role="radiogroup" aria-label={tr('Project / branch (optional)')}>
              <button type="button" role="radio" aria-checked={!costCentreId} className={`chip ${!costCentreId ? 'on' : ''}`} onClick={() => setCostCentreId('')}>{tr('None')}</button>
              {centres.map((c) => (
                <button key={c.id} type="button" role="radio" aria-checked={costCentreId === c.id} className={`chip ${costCentreId === c.id ? 'on' : ''}`} onClick={() => setCostCentreId(c.id)}>
                  {c.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {editing?.status !== 'rejected' && (
        <div className="card pad stack">
          <div className="field">
            <label>{t('paid')}</label>
            <div className="seg" role="radiogroup" aria-label={t('paid')}>
              <button role="radio" aria-checked={!paidNow} className={!paidNow ? 'on' : ''} onClick={() => setPaidNow(false)}>{t('notPaid')}</button>
              <button role="radio" aria-checked={paidNow} className={paidNow ? 'on' : ''} onClick={() => { setPaidNow(true); if (!lines.length) setLines([newLine(total, client?.bankAccounts)]); }}>{tr('Yes, paid')}</button>
            </div>
          </div>
          {paidNow && (
            <>
              <PaymentLines lines={lines} onChange={setLines} accounts={client?.bankAccounts ?? []} cashLimit={client?.cashLimitPerDay} />
              {totalNum > 0 && round2(lines.reduce((x, l) => x + (Number(l.amount) || 0), 0)) < totalNum && (
                <span className="hint">{tr('Balance {amount} stays due.', { amount: fmtInr(round2(totalNum - lines.reduce((x, l) => x + (Number(l.amount) || 0), 0))) })}</span>
              )}
            </>
          )}
        </div>
      )}

      {lookAlike && (
        <div className="banner warn" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <b>{tr('This looks like a bill already recorded')}</b>
          <span>{lookAlike.vendorName} · {lookAlike.invoiceNo ?? '—'} · {fmtDate(lookAlike.invoiceDate)} · {fmtInr(lookAlike.totalAmount)}</span>
          <div className="row wrap">
            <button className="btn sm" onClick={() => nav('/')}>{tr("It's the same bill — don't save")}</button>
            <button className="btn sm primary" onClick={() => { setConfirmedDifferent(lookAlike.id); setLookAlike(undefined); }}>{tr("It's a different bill")}</button>
          </div>
        </div>
      )}

      <details className="card pad" open={!!hsn || !!narration}>
        <summary className="small muted" style={{ cursor: 'pointer' }}>{t('moreDetails')}</summary>
        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="hsn">{t('hsnLabel')}</label>
          <input id="hsn" className="input mono" style={{ fontSize: 16 }} inputMode="numeric" value={hsn} onChange={(e) => setHsn(e.target.value.replace(/\D/g, '').slice(0, 8))} />
        </div>
        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="narr">{tr('Narration (optional)')}</label>
          <textarea id="narr" className="input" rows={2} maxLength={250} value={narration} onChange={(e) => setNarration(e.target.value)} placeholder={tr('e.g. Paid against PO 114 for Nashik godown')} />
          <span className="hint">{tr('Goes into the Tally voucher narration.')} {narration.length}/250</span>
        </div>
      </details>

      <div className="sticky-save">
        <button className="btn primary lg block" disabled={!!problem || busy} onClick={save}><Icon name="check" /> {editing?.status === 'draft' ? tr('Complete & submit') : editing ? t('fixResubmit') : t('save')}</button>
        {problem && <div className="hint" style={{ textAlign: 'center', marginTop: 6 }}>{problem}</div>}
      </div>
    </div>
  );
}

function gstRateOf(e: Expense): number {
  const tax = e.cgst + e.sgst + e.igst;
  if (!tax || !e.taxableValue) return 0;
  const pct = (tax / e.taxableValue) * 100;
  return ALL_GST_RATES.reduce((best: number, r: number) => (Math.abs(r - pct) < Math.abs(best - pct) ? r : best), 0);
}
