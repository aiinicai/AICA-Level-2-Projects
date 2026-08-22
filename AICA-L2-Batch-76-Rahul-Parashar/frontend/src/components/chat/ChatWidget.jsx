import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { MessageCircle, X, Send } from 'lucide-react';
import { useFinancials } from '../../context/FinancialsContext';
import { routeLabel } from '../../routes';
import ChatMessage from './ChatMessage';

export default function ChatWidget({ open, onOpenChange }) {
  const { financials, dashboardReady } = useFinancials();
  const location = useLocation();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const listRef = useRef(null);

  // A new workbook re-grounds the assistant — stale answers from the previous file must not linger.
  useEffect(() => {
    setMessages([]);
    setError(null);
  }, [financials]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, sending]);

  if (!dashboardReady) return null;

  async function send() {
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    const nextMessages = [...messages, { role: 'user', content: trimmed }];
    setMessages(nextMessages);
    setInput('');
    setSending(true);
    setError(null);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: trimmed,
          history,
          currentPage: routeLabel(location.pathname),
          financials,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Request failed.');
      setMessages((m) => [...m, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setError(
        err.message?.includes('fetch') || err.message === 'Failed to fetch'
          ? "Couldn't reach the analyst assistant — check that the backend is running and ANTHROPIC_API_KEY is set."
          : err.message
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button
        onClick={() => onOpenChange(!open)}
        aria-label="Ask CFO Copilot"
        className="fixed bottom-5 right-5 z-40 bg-verdigris text-paper rounded-full w-12 h-12 flex items-center justify-center shadow-lg hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-verdigris focus:ring-offset-2"
      >
        {open ? <X size={20} /> : <MessageCircle size={20} />}
      </button>

      {open && (
        <div className="fixed bottom-20 right-5 z-40 w-[90vw] max-w-sm bg-paper rounded-lg border border-line shadow-lg flex flex-col" style={{ height: 480 }}>
          <div className="px-4 py-3 border-b border-line">
            <p className="font-heading text-sm font-semibold text-ink">CFO Copilot</p>
            <p className="text-xs text-slate font-body">Grounded on {financials?.company || 'the loaded workbook'}</p>
          </div>

          <div ref={listRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
            {messages.length === 0 && (
              <p className="text-xs text-slate font-body text-center mt-6">
                Ask about revenue, margins, ratios, or anything in the uploaded workbook.
              </p>
            )}
            {messages.map((m, i) => (
              <ChatMessage key={i} role={m.role} content={m.content} />
            ))}
            {sending && <ChatMessage role="assistant" content="…" />}
          </div>

          {error && <div className="px-3 py-2 text-xs text-clay bg-clay-soft border-t border-line font-body">{error}</div>}

          <div className="p-2.5 border-t border-line flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              placeholder="Ask a question…"
              className="flex-1 border border-line rounded-lg px-3 py-2 text-sm font-body focus:outline-none focus:ring-2 focus:ring-verdigris"
            />
            <button
              onClick={send}
              disabled={sending || !input.trim()}
              aria-label="Send"
              className="bg-verdigris text-paper rounded-lg p-2 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-verdigris"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
