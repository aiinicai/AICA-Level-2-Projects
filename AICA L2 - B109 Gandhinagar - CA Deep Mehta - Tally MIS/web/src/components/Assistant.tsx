import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useCompany } from '../state';
import { filterQuery } from './nav';

interface Reply {
  answer: string;
  kind: 'company' | 'general' | 'refused' | 'warning' | 'offline';
  label?: string | null;
  facts?: string[] | null;
  unmatched?: string[];
}
type Entry = { id: number; q: string; a: Reply | null; error?: string };

const STARTERS = ['Explain the net profit', 'Why did revenue change?', 'Who owes us the most?', 'What are the biggest expenses?'];

const ChatIcon = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" /><path d="M9 11h6M9 14h4" />
  </svg>
);

/** The floating chat button. A local AI (LM Studio) puts the app's calculated figures into words; it never calculates. */
export function Assistant() {
  const { companyId, company } = useCompany();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [log, setLog] = useState<Entry[]>([]);
  const [busy, setBusy] = useState(false);
  const [sp] = useSearchParams();
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { setLog([]); }, [companyId]);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  useEffect(() => { end.current?.scrollIntoView({ block: 'nearest' }); }, [log]);

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setText('');
    setBusy(true);
    const id = Date.now();
    setLog((l) => [...l, { id, q: question, a: null }]);
    const filters = Object.fromEntries(new URLSearchParams(filterQuery(sp).slice(1)));
    try {
      const a = await api<Reply>('/api/assistant/chat', { body: { companyId, question, ...filters } });
      setLog((l) => l.map((e) => (e.id === id ? { ...e, a } : e)));
    } catch (e: any) {
      setLog((l) => l.map((x) => (x.id === id ? { ...x, error: e.message } : x)));
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return <button type="button" className="chat-fab no-print" onClick={() => setOpen(true)} aria-label="Open the assistant" title="Ask the assistant"><ChatIcon /></button>;
  }
  return (
    <section className="ask no-print" aria-label="Assistant">
      <header>
        <div><b>Assistant</b><small>{company ? company.name : 'No company open'} · runs on this PC</small></div>
        <button type="button" className="btn sm" onClick={() => setOpen(false)}>Close</button>
      </header>
      <div className="ask-log" aria-live="polite">
        {log.length === 0 && (
          <div className="ask-a">
            <p>I explain the figures this app has calculated for the period selected on screen. I never do the maths myself.</p>
            {!companyId && <p className="muted">Open or sync a company first.</p>}
            <div className="ask-chips">{STARTERS.map((s) => <button key={s} type="button" onClick={() => ask(s)} disabled={!companyId}>{s}</button>)}</div>
          </div>
        )}
        {log.map((e) => (
          <div key={e.id}>
            <p className="ask-q">{e.q}</p>
            <div className="ask-a">
              {e.error ? <p className="neg">{e.error}</p> : !e.a ? <p className="muted">Thinking…</p> : (
                <>
                  {e.a.label && <p className={`tag ${e.a.kind}`}>{e.a.label}</p>}
                  <p style={{ whiteSpace: 'pre-wrap' }}>{e.a.answer}</p>
                  {e.a.unmatched?.length ? <p className="small muted">Numbers I could not match: {e.a.unmatched.join(', ')}</p> : null}
                  {e.a.facts?.length ? (
                    <details className="small">
                      <summary>Figures used ({e.a.facts.length})</summary>
                      <ul className="facts">{e.a.facts.map((f, i) => <li key={i}>{f}</li>)}</ul>
                    </details>
                  ) : null}
                </>
              )}
            </div>
          </div>
        ))}
        <div ref={end} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); void ask(text); }}>
        <input ref={input} value={text} onChange={(e) => setText(e.target.value)} maxLength={400} placeholder="Ask about the figures" aria-label="Your question" />
        <button className="btn primary" disabled={!text.trim() || busy || !companyId}>Ask</button>
      </form>
    </section>
  );
}
