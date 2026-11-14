// J — the same bill recorded twice under a new photo or a slightly different bill number.
// Step 1 (free, device): near-identical photos (dHash) + same vendor & amount within 30 days with different bill numbers.
// Step 2 (optional AI): compare the two originals; "same" is accepted only with two quoted matches and no quoted difference.
import { DpdpNote } from './DpdpNote';
import { useEffect, useMemo, useState } from 'react';
import { useStore } from '../data/store';
import type { Expense } from '../data/types';
import { useTr } from '../i18n';
import { runAi, useAiStatus, type AiResult } from '../lib/ai';
import { daysBetween, fmtDate } from '../lib/dates';
import { fmtInr } from '../lib/money';
import { dHashOf, hamming, LOOKALIKE_MAX_BITS } from '../lib/phash';
import { getDocumentBlob } from '../lib/storage';
import { AiOff, Doubts } from './AiBits';

type Point = { point: string; evidence_a: string; evidence_b: string };
export const VERDICT = { same: ['danger', 'Same bill — likely recorded twice'], different: ['ok', 'Different bills'], unsure: ['warn', 'AI is unsure — compare them yourself'] } as const;
type Cmp = { verdict: 'same' | 'different' | 'unsure'; same_points: Point[]; different_points: Point[]; note: string };

export function LookAlikes({ expenses }: { expenses: Expense[] }) {
  const { me } = useStore();
  const tr = useTr();
  const ai = useAiStatus();
  const [hashes, setHashes] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string>();
  const [res, setRes] = useState<Record<string, AiResult<Cmp> | string>>({});
  const live = useMemo(() => expenses.filter((e) => e.status !== 'draft' && e.status !== 'rejected'), [expenses]);

  useEffect(() => {
    let on = true;
    (async () => {
      const out: Record<string, string> = {};
      for (const e of live) if (e.imageDataUrl) { try { out[e.id] = await dHashOf(e.imageDataUrl); } catch { /* unreadable thumbnail */ } }
      if (on) setHashes(out);
    })();
    return () => { on = false; };
  }, [live]);

  const pairs = useMemo(() => {
    const out: { a: Expense; b: Expense; why: string; vars?: Record<string, number> }[] = [];
    for (let i = 0; i < live.length; i++) for (let j = i + 1; j < live.length; j++) {
      const a = live[i], b = live[j];
      const ha = hashes[a.id], hb = hashes[b.id];
      const d = ha && hb ? hamming(ha, hb) : 99;
      if (d <= LOOKALIKE_MAX_BITS) out.push({ a, b, why: 'Photos look almost identical ({d} of 64 points differ)', vars: { d } });
      else if (a.vendorId && a.vendorId === b.vendorId && Math.abs(a.totalAmount - b.totalAmount) < 0.01 && a.invoiceNo !== b.invoiceNo
        && Math.abs(daysBetween(a.invoiceDate, b.invoiceDate)) <= 30) out.push({ a, b, why: 'Same vendor and amount within 30 days, different bill numbers' });
    }
    return out.slice(0, 30);
  }, [live, hashes]);

  async function compare(a: Expense, b: Expense) {
    const key = `${a.id}|${b.id}`;
    setBusy(key);
    try {
      let files: Blob[] | undefined;
      if (ai.mode === 'local') {
        const [fa, fb] = await Promise.all([getDocumentBlob(a.fileId), getDocumentBlob(b.fileId)]);
        if (!fa || !fb) throw new Error('The original bill file is not on this device.');
        files = [fa, fb];
      }
      const r = await runAi<Cmp>('compare_bills', me!.role, { clientId: a.clientId }, files ? { files } : { expenseIds: [a.id, b.id] });
      setRes((x) => ({ ...x, [key]: r }));
    } catch (e) { setRes((x) => ({ ...x, [key]: (e as Error).message })); } finally { setBusy(undefined); }
  }

  const line = (e: Expense) => `${e.vendorName} · ${e.invoiceNo ? `#${e.invoiceNo} · ` : ''}${fmtDate(e.invoiceDate)} · ${fmtInr(e.totalAmount)}`;

  return (
    <div className="card">
      <div className="card-head"><h2>{tr('Possible duplicate bills')}</h2></div>
      <div className="pad tiny muted" style={{ paddingTop: 0 }}>{tr('Catches the same photo sent twice, screenshots and re-saved copies. A fresh photo from another angle may not be caught.')}</div>
      <div className="pad" style={{ paddingTop: 0 }}>{!ai.enabled ? <AiOff reason={ai.reason} /> : <DpdpNote kind="ai" />}</div>
      {pairs.length === 0 ? <div className="pad small muted">{tr('No look-alike bills found.')}</div> : (
        <div className="list">
          {pairs.map(({ a, b, why, vars }) => {
            const key = `${a.id}|${b.id}`, r = res[key];
            return (
              <div key={key} className="list-item stack" style={{ alignItems: 'stretch', gap: 6 }}>
                <div className="row wrap" style={{ gap: 10 }}>
                  {[a, b].map((e) => e.imageDataUrl ? <img key={e.id} className="photo-thumb" style={{ width: 44, height: 58 }} src={e.imageDataUrl} alt="" /> : <div key={e.id} className="avatar"><b className="tiny">PDF</b></div>)}
                  <div className="grow small"><div>A: {line(a)}</div><div>B: {line(b)}</div><div className="tiny muted">{tr(why, vars)}</div></div>
                  <button className="btn sm" disabled={!ai.enabled || !!busy || !a.fileId || !b.fileId} onClick={() => compare(a, b)}>{busy === key ? tr('Comparing…') : tr('Compare with AI')}</button>
                </div>
                {typeof r === 'string' && <div className="banner danger small">{tr(r)}</div>}
                {r && typeof r !== 'string' && (
                  <>
                    <span className={`badge ${VERDICT[r.result.verdict][0]}`} style={{ alignSelf: 'flex-start' }}>{tr(VERDICT[r.result.verdict][1])}</span>
                    {[...r.result.same_points.map((p) => ['=', p] as const), ...r.result.different_points.map((p) => ['≠', p] as const)].map(([sym, p], i) => (
                      <div key={i} className="tiny">{sym} {p.point}: A “{p.evidence_a}” · B “{p.evidence_b}”</div>
                    ))}
                    <Doubts doubts={r.doubts} />
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
