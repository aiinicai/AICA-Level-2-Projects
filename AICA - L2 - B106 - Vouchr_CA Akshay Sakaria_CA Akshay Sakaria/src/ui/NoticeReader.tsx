// I — Notice reader (CA firm): upload a GST / income-tax notice; AI extracts the facts, each with a quote from the notice.
// For PDFs the quotes are checked against the PDF's own text. No legal advice is produced.
import { DpdpNote } from './DpdpNote';
import { useRef, useState } from 'react';
import { useStore } from '../data/store';
import { useLang, useTr } from '../i18n';
import { runAi, useAiStatus, type AiResult, type Fact } from '../lib/ai';
import { pdfText } from '../lib/docread';
import { fmtDate } from '../lib/dates';
import { fmtInr } from '../lib/money';
import { AiOff, Doubts, FactTag } from './AiBits';
import { Icon } from './Icon';

type Notice = {
  issuer: Fact<string>; notice_type: Fact<string>; reference_no: Fact<string>; notice_date: Fact<string>; reply_due_date: Fact<string>;
  period: Fact<string>; amount_demanded: Fact<number>; sections_cited: Fact<string>[]; actions: { action: string; evidence: string }[];
  summary_en: string; summary_hi: string;
};

export function NoticeReader() {
  const { me } = useStore();
  const tr = useTr();
  const lang = useLang();
  const ai = useAiStatus();
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [res, setRes] = useState<AiResult<Notice> & { file: string }>();

  async function onFile(f?: File) {
    if (!f || !me) return;
    setBusy(true); setErr(undefined); setRes(undefined);
    try {
      const sourceText = f.type === 'application/pdf' ? await pdfText(f, 10).catch(() => '') : '';
      const r = await runAi<Notice>('notice_summary', me.role, { sourceText: sourceText || undefined }, { files: [f] });
      setRes({ ...r, file: f.name });
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  const row = (label: string, f: Fact<unknown>, show = (v: unknown) => String(v)) => (
    <div className="row wrap small" key={label}><span className="muted" style={{ minWidth: 120 }}>{tr(label)}</span><b>{f.value === null ? '—' : show(f.value)}</b><FactTag f={f} /></div>
  );
  const n = res?.result;

  return (
    <div className="card pad stack">
      <div className="row between wrap">
        <div><h2>{tr('Read a tax notice')}</h2><div className="small muted">{tr('GST / income-tax notice → facts, due date and what it asks for, each with a quote from the notice.')}</div></div>
        <button className="btn" disabled={!ai.enabled || busy} onClick={() => ref.current?.click()}><Icon name="upload" size={16} /> {busy ? tr('Reading…') : tr('Upload notice')}</button>
      </div>
      <input ref={ref} type="file" hidden accept="application/pdf,image/*" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
      {!ai.enabled ? <AiOff reason={ai.reason} /> : <DpdpNote kind="ai" />}
      {err && <div className="banner danger small">{tr(err)}</div>}
      {n && res && (
        <div className="stack" style={{ gap: 6 }}>
          <div className="tiny muted">{res.file}</div>
          <Doubts doubts={res.doubts} />
          {row('Issued by', n.issuer)}{row('Notice type', n.notice_type)}{row('Reference no.', n.reference_no)}
          {row('Notice date', n.notice_date, (v) => fmtDate(String(v)))}{row('Reply due by', n.reply_due_date, (v) => fmtDate(String(v)))}
          {row('Period', n.period)}{row('Amount demanded', n.amount_demanded, (v) => fmtInr(Number(v)))}
          {n.sections_cited.length > 0 && <div className="row wrap small"><span className="muted" style={{ minWidth: 120 }}>{tr('Sections cited')}</span>{n.sections_cited.map((s, i) => <span key={i} className="row" style={{ gap: 4 }}><b>{String(s.value)}</b><FactTag f={s} /></span>)}</div>}
          {n.actions.length > 0 && (
            <div className="stack" style={{ gap: 4 }}>
              <b className="small">{tr('What the notice asks for')}</b>
              {n.actions.map((a, i) => <div key={i} className="small">• {a.action} <span className="muted">— “{a.evidence}”</span></div>)}
            </div>
          )}
          <div className="small">{lang === 'hi' ? n.summary_hi : n.summary_en}</div>
          <div className="tiny muted">{tr('Summary only — not legal advice. Read the notice itself before replying.')}</div>
        </div>
      )}
    </div>
  );
}
