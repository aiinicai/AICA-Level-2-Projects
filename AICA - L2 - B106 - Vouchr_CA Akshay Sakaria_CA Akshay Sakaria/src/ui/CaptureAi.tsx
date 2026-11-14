// A — "Read with AI" (handwritten / Hindi / unclear bills) and B — voice entry, on the Add-expense screen.
// Only facts that passed every check are filled in. Anything uncertain is listed, with a "Use" button, never filled silently.
import { DpdpNote } from './DpdpNote';
import { useEffect, useRef, useState } from 'react';
import { useStore } from '../data/store';
import { useTr } from '../i18n';
import { runAi, sure, useAiStatus, type AiResult, type Fact } from '../lib/ai';
import { round2 } from '../lib/money';
import { ALL_GST_RATES } from '../data/masters';
import type { PayMode } from '../data/types';
import { AiOff, Doubts, FactTag } from './AiBits';
import { Icon } from './Icon';

export interface CaptureFill {
  vendorName?: string; vendorGstin?: string; invoiceNo?: string; invoiceDate?: string; total?: number; rate?: number;
  description?: string; irn?: string; payMode?: PayMode; paid?: boolean;
  nonTaxable?: number; ecoPaysTax?: boolean; ecoGstin?: string;
}
type BillRead = Record<'vendor_name' | 'vendor_gstin' | 'invoice_no' | 'invoice_date' | 'irn' | 'description' | 'eco_gstin', Fact<string>> &
  Record<'taxable_value' | 'cgst' | 'sgst' | 'igst' | 'total' | 'non_taxable_charges', Fact<number>> & { eco_pays_tax: Fact<boolean>; handwritten: boolean; language: string };
type Voice = { transcript: string; vendor_name: Fact<string>; amount: Fact<number>; purpose: Fact<string>; pay_mode: Fact<string>; paid: Fact<boolean>; bill_date: Fact<string> };

const MAX_SECONDS = 60;

export function CaptureAi({ file, buyerGstin, onApply }: { file?: Blob; buyerGstin?: string; onApply: (f: CaptureFill) => void }) {
  const tr = useTr();
  const { me } = useStore();
  const ai = useAiStatus();
  const [busy, setBusy] = useState<'read' | 'voice'>();
  const [err, setErr] = useState<string>();
  const [bill, setBill] = useState<AiResult<BillRead>>();
  const [voice, setVoice] = useState<AiResult<Voice>>();
  const [rec, setRec] = useState<{ r: MediaRecorder; started: number }>();
  const [secs, setSecs] = useState(0);
  const chunks = useRef<Blob[]>([]);

  useEffect(() => {
    if (!rec) return;
    const t = setInterval(() => { const s = Math.round((Date.now() - rec.started) / 1000); setSecs(s); if (s >= MAX_SECONDS) rec.r.stop(); }, 500);
    return () => clearInterval(t);
  }, [rec]);

  if (!me) return null;

  function gstRate(b: BillRead): number | undefined {
    const tx = sure(b.taxable_value), [c, s, i] = [b.cgst, b.sgst, b.igst].map((f) => (f.certainty === 'not_found' ? 0 : sure(f)));
    if (!tx || c === undefined || s === undefined || i === undefined) return undefined;
    const pct = round2(((c + s + i) / tx) * 100);
    return ALL_GST_RATES.find((r) => Math.abs(r - pct) < 0.2);
  }

  async function readBill() {
    if (!file) return;
    setBusy('read'); setErr(undefined); setBill(undefined);
    try {
      const r = await runAi<BillRead>('read_bill', me!.role, { buyerGstin }, { files: [file] });
      setBill(r);
      const b = r.result;
      onApply({ vendorName: sure(b.vendor_name), vendorGstin: sure(b.vendor_gstin), invoiceNo: sure(b.invoice_no), invoiceDate: sure(b.invoice_date),
        total: sure(b.total), rate: gstRate(b), description: sure(b.description), irn: sure(b.irn),
        nonTaxable: sure(b.non_taxable_charges) || undefined, ecoPaysTax: sure(b.eco_pays_tax), ecoGstin: sure(b.eco_gstin) });
    } catch (e) { setErr((e as Error).message); } finally { setBusy(undefined); }
  }

  async function startVoice() {
    setErr(undefined); setVoice(undefined);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream);
      chunks.current = [];
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      r.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRec(undefined); setBusy('voice');
        try {
          const res = await runAi<Voice>('voice_entry', me!.role, {}, { files: [new Blob(chunks.current, { type: r.mimeType })] });
          setVoice(res);
          const v = res.result;
          onApply({ vendorName: sure(v.vendor_name), total: sure(v.amount), description: sure(v.purpose), invoiceDate: sure(v.bill_date),
            payMode: sure(v.pay_mode) as PayMode | undefined, paid: sure(v.paid) });
        } catch (e) { setErr((e as Error).message); } finally { setBusy(undefined); }
      };
      r.start();
      setSecs(0);
      setRec({ r, started: Date.now() });
    } catch {
      setErr(tr('Microphone not available — allow microphone access for this site.'));
    }
  }

  const useBtn = (label: string, f: Fact<unknown>, fill: CaptureFill) => f.certainty === 'uncertain' && f.value !== null && (
    <div className="row wrap small" key={label}>
      <span>{tr(label)}: <b>{String(f.value)}</b></span><FactTag f={f} />
      <button className="btn sm" onClick={() => onApply(fill)}>{tr('Use')}</button>
    </div>
  );

  return (
    <div className="card pad stack" style={{ gap: 10 }}>
      <div className="row wrap" style={{ gap: 8 }}>
        <button className="btn" disabled={!ai.enabled || !file || !!busy || !!rec} onClick={readBill} title={!file ? tr('Add a photo or PDF first') : undefined}>
          <Icon name="radar" size={16} /> {busy === 'read' ? tr('Reading the bill…') : tr('Read with AI')}
        </button>
        {rec ? (
          <button className="btn danger" onClick={() => rec.r.stop()}><Icon name="check" size={16} /> {tr('Stop')} · {secs}s / {MAX_SECONDS}s</button>
        ) : (
          <button className="btn" disabled={!ai.enabled || !!busy || typeof MediaRecorder === 'undefined'} onClick={startVoice}>
            🎙 {busy === 'voice' ? tr('Listening…') : tr('Speak the expense')}
          </button>
        )}
      </div>
      {!ai.enabled ? <AiOff reason={ai.reason} /> : !bill && !voice && <div className="tiny muted">{tr('AI fills only what it is sure about. Anything doubtful is listed for you to check.')}</div>}
      {ai.enabled && <DpdpNote kind="ai" />}
      {ai.enabled && <DpdpNote kind="voice" />}
      {err && <div className="banner danger small">{tr(err)}</div>}

      {bill && (
        <>
          <Doubts doubts={bill.doubts} />
          {useBtn('Vendor', bill.result.vendor_name, { vendorName: String(bill.result.vendor_name.value) })}
          {useBtn('Bill no.', bill.result.invoice_no, { invoiceNo: String(bill.result.invoice_no.value) })}
          {useBtn('Bill date', bill.result.invoice_date, { invoiceDate: String(bill.result.invoice_date.value) })}
          {useBtn('Bill total', bill.result.total, { total: Number(bill.result.total.value) })}
          {bill.result.handwritten && <div className="tiny muted">{tr('Handwritten bill')}{bill.result.language ? ` · ${bill.result.language}` : ''}</div>}
        </>
      )}
      {voice && (
        <>
          <div className="small"><b>{tr('Heard')}:</b> “{voice.result.transcript}”</div>
          <Doubts doubts={voice.doubts} />
          {useBtn('Vendor', voice.result.vendor_name, { vendorName: String(voice.result.vendor_name.value) })}
          {useBtn('Amount', voice.result.amount, { total: Number(voice.result.amount.value) })}
          {useBtn('Bill date', voice.result.bill_date, { invoiceDate: String(voice.result.bill_date.value) })}
          {useBtn('Purpose', voice.result.purpose, { description: String(voice.result.purpose.value) })}
        </>
      )}
    </div>
  );
}
