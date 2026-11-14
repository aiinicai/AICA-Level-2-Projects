// G — Ask your data. AI turns the question into one fixed query + filters. The filters are shown and editable; the answer is
// calculated by the app from the records, so a wrong reading by AI is visible and fixable — it can never invent a figure.
import { DpdpNote } from '../ui/DpdpNote';
import { useMemo, useState } from 'react';
import { useStore } from '../data/store';
import type { PayMode } from '../data/types';
import { useLang, useTr } from '../i18n';
import { ASK_LABEL, ASK_QUERIES, runAsk, type AskFilters, type AskQuery } from '../lib/askData';
import { runAi, useAiStatus, type AiResult, type Fact } from '../lib/ai';
import { fmtInr } from '../lib/money';
import { AiOff, Doubts, FactTag } from '../ui/AiBits';
import { PageHead } from '../ui/common';
import { Icon } from '../ui/Icon';
import { modeLabel, PAY_MODES } from '../ui/PaymentLines';

type Parsed = { query: AskQuery | 'unanswerable'; from: Fact<string>; to: Fact<string>; head: Fact<string>; centre: Fact<string>; vendor: Fact<string>; mode: Fact<string>; understood_en: string; understood_hi: string };
export const ASK_EXAMPLES = ['How much did we spend on repairs this financial year?', 'Top vendors last month', 'How much is unpaid to vendors?', 'Cash payments in October 2026'];

export function Ask() {
  const { scoped, s, client, me } = useStore();
  const tr = useTr();
  const lang = useLang();
  const ai = useAiStatus();
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [res, setRes] = useState<AiResult<Parsed>>();
  const [query, setQuery] = useState<AskQuery>('spend_total');
  const [f, setF] = useState<AskFilters>({});
  const centres = client?.costCentres ?? [];
  const vendors = [...new Set(scoped.vendors.map((v) => v.name))];

  async function ask() {
    if (!q.trim() || !me) return;
    setBusy(true); setErr(undefined);
    try {
      const r = await runAi<Parsed>('ask_data', me.role, { clientId: client?.id, question: q.trim(), heads: s.heads.map((h) => h.name), centres: centres.map((c) => c.name), vendors });
      setRes(r);
      const p = r.result;
      if (p.query !== 'unanswerable') setQuery(p.query);
      // every value AI gave goes into the visible filters; unsure ones are marked amber below
      const v = (x: Fact<string>) => (x.value === null ? undefined : String(x.value));
      setF({ from: v(p.from), to: v(p.to), headId: s.heads.find((h) => h.name === v(p.head))?.id, centreId: centres.find((c) => c.name === v(p.centre))?.id, vendor: v(p.vendor), mode: v(p.mode) as PayMode | undefined });
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  const answer = useMemo(() => runAsk(query, f, { expenses: scoped.expenses, payments: scoped.payments, heads: s.heads, centres }), [query, f, scoped, s.heads, centres]);
  const unsure = res ? (['from', 'to', 'head', 'centre', 'vendor', 'mode'] as const).filter((k) => res.result[k].certainty === 'uncertain') : [];
  const fmt = (n: number) => (answer.unit === 'inr' ? fmtInr(n) : String(n));

  return (
    <div className="content stack" style={{ maxWidth: 900 }}>
      <PageHead title={tr('Ask your data')} sub={client?.name} />
      <div className="card pad stack">
        <div className="row wrap" style={{ gap: 8 }}>
          <input className="input grow" style={{ minWidth: 220 }} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && ask()} placeholder={tr('Ask in English or Hindi, e.g. “Nashik branch repairs this quarter”')} aria-label={tr('Question')} />
          <button className="btn primary" disabled={!ai.enabled || busy || !q.trim()} onClick={ask}><Icon name="radar" size={16} /> {busy ? tr('Reading…') : tr('Ask')}</button>
        </div>
        <div className="chips">{ASK_EXAMPLES.map((x) => <button key={x} className="chip static" onClick={() => setQ(tr(x))}>{tr(x)}</button>)}</div>
        {!ai.enabled ? <AiOff reason={ai.reason} /> : <DpdpNote kind="ai" />}
        {err && <div className="banner danger small">{tr(err)}</div>}
        {res && res.result.query === 'unanswerable' && <div className="banner warn small">{tr('This cannot be answered from the bills and payments in Vouchr. Try one of the examples.')}</div>}
        {res && <div className="small"><b>{tr('I understood')}:</b> {lang === 'hi' ? res.result.understood_hi : res.result.understood_en}</div>}
        {res && <Doubts doubts={res.doubts} />}
      </div>

      <div className="card pad stack">
        <div className="tiny muted">{tr('Filters — change any of them; the answer updates.')}</div>
        <div className="row wrap" style={{ alignItems: 'flex-end' }}>
          <div className="field"><label htmlFor="ask-q">{tr('Show')}</label>
            <select id="ask-q" className="input sm" value={query} onChange={(e) => setQuery(e.target.value as AskQuery)}>{ASK_QUERIES.map((k) => <option key={k} value={k}>{tr(ASK_LABEL[k])}</option>)}</select></div>
          <div className="field"><label htmlFor="ask-from">{tr('From')} {res && <FactTag f={res.result.from} />}</label><input id="ask-from" type="date" className="input sm" value={f.from ?? ''} onChange={(e) => setF({ ...f, from: e.target.value || undefined })} /></div>
          <div className="field"><label htmlFor="ask-to">{tr('To')} {res && <FactTag f={res.result.to} />}</label><input id="ask-to" type="date" className="input sm" value={f.to ?? ''} onChange={(e) => setF({ ...f, to: e.target.value || undefined })} /></div>
          <div className="field"><label htmlFor="ask-head">{tr('Expense head')} {res && <FactTag f={res.result.head} />}</label>
            <select id="ask-head" className="input sm" value={f.headId ?? ''} onChange={(e) => setF({ ...f, headId: e.target.value || undefined })}><option value="">{tr('All')}</option>{s.heads.map((h) => <option key={h.id} value={h.id}>{tr(h.name)}</option>)}</select></div>
          {centres.length > 0 && <div className="field"><label htmlFor="ask-cc">{tr('Project / branch')} {res && <FactTag f={res.result.centre} />}</label>
            <select id="ask-cc" className="input sm" value={f.centreId ?? ''} onChange={(e) => setF({ ...f, centreId: e.target.value || undefined })}><option value="">{tr('All')}</option>{centres.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>}
          <div className="field"><label htmlFor="ask-v">{tr('Vendor')} {res && <FactTag f={res.result.vendor} />}</label>
            <select id="ask-v" className="input sm" value={f.vendor ?? ''} onChange={(e) => setF({ ...f, vendor: e.target.value || undefined })}><option value="">{tr('All')}</option>{vendors.map((v) => <option key={v} value={v}>{v}</option>)}</select></div>
          {query === 'payments_total' && <div className="field"><label htmlFor="ask-m">{tr('Payment mode')} {res && <FactTag f={res.result.mode} />}</label>
            <select id="ask-m" className="input sm" value={f.mode ?? ''} onChange={(e) => setF({ ...f, mode: (e.target.value || undefined) as PayMode | undefined })}><option value="">{tr('All')}</option>{PAY_MODES.map((m) => <option key={m.mode} value={m.mode}>{tr(modeLabel(m.mode))}</option>)}</select></div>}
        </div>
        {unsure.length > 0 && <div className="banner warn small">⚠ {tr('The answer below uses filters AI was unsure about — check them.')}</div>}
        <div className="kpi-value num">{fmt(answer.value)}</div>
        <div className="small muted">{tr(ASK_LABEL[query])} · {tr('from {n} record(s)', { n: answer.basedOn })} · {tr('Calculated by Vouchr from your records, not by AI.')}</div>
        {answer.rows.length > 0 && (
          <div className="list">{answer.rows.map((r) => <div key={r.label} className="list-item small"><span className="grow">{tr(r.label)}</span><b className="num">{fmt(r.value)}</b></div>)}</div>
        )}
      </div>
    </div>
  );
}
