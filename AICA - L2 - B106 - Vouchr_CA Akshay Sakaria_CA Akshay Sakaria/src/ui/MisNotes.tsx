// H — MIS commentary for the business owner. AI may only refer to our figures as {key}; the app inserts the numbers.
// Any point containing a number AI wrote itself, or a figure we don't have, is dropped (truth check in tasks.ts).
import { DpdpNote } from './DpdpNote';
import { useState } from 'react';
import { useStore } from '../data/store';
import { useLang, useTr } from '../i18n';
import { runAi, useAiStatus, type AiResult } from '../lib/ai';
import { fmtInr } from '../lib/money';
import { AiOff, Doubts } from './AiBits';
import { Icon } from './Icon';

const COUNTS = new Set(['awaitingReview', 'billsWithoutImage', 'billCount']);

export function MisNotes({ figures }: { figures: Record<string, number | string | undefined> }) {
  const { me, client } = useStore();
  const tr = useTr();
  const lang = useLang();
  const ai = useAiStatus();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [res, setRes] = useState<AiResult<{ points: { text_en: string; text_hi: string }[] }>>();
  const clean = Object.fromEntries(Object.entries(figures).filter(([, v]) => v !== undefined)) as Record<string, number | string>;
  const fill = (t: string) => t.replace(/\{(\w+)\}/g, (_, k: string) => { const v = clean[k]; return typeof v === 'number' ? (COUNTS.has(k) ? String(v) : fmtInr(v)) : String(v ?? ''); });

  async function write() {
    setBusy(true); setErr(undefined);
    try { setRes(await runAi('mis_commentary', me!.role, { clientId: client?.id, figures: clean })); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div className="card pad stack">
      <div className="row between wrap">
        <h2>{tr('Notes for the owner')}</h2>
        <button className="btn sm" disabled={!ai.enabled || busy} onClick={write}><Icon name="radar" size={14} /> {busy ? tr('Writing…') : tr('Write with AI')}</button>
      </div>
      {!ai.enabled ? <AiOff reason={ai.reason} /> : <DpdpNote kind="ai" />}
      {err && <div className="banner danger small">{tr(err)}</div>}
      {res && <Doubts doubts={res.doubts} />}
      {res && <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>{res.result.points.map((p, i) => <li key={i}>{fill(lang === 'hi' ? p.text_hi : p.text_en)}</li>)}</ul>}
      {res && <div className="tiny muted">{tr('Every number above is inserted by Vouchr from this dashboard; AI only wrote the words.')}</div>}
    </div>
  );
}
