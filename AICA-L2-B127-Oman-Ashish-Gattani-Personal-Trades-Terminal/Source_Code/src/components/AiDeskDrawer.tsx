import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, Send, Sparkles, Trash2, X } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, STOCK_BY_TICKER } from '../data/indianMarketData';
import { computeMultiIndicatorMatrix } from '../engine/tradeRadarEngine';
import { postAiJson } from '../utils/aiClient';
import { formatINR, formatPct } from '../utils/formatters';

interface AiDeskDrawerProps {
  open: boolean;
  onClose: () => void;
  activeTicker: string | null;
  activeWorkspaceLabel: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

export function renderStructuredAiLines(text: string): React.ReactNode {
  const lines = text.split('\n');
  return (
    <div className="space-y-1.5 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
      {lines.map((raw, idx) => {
        const line = raw.trim();
        if (!line) return <div key={idx} className="h-1" />;

        // Headings like "### Heading" or "**Heading**" on its own line
        if (line.startsWith('### ') || line.startsWith('## ')) {
          return (
            <div
              key={idx}
              className="pt-1 font-sans font-bold text-[12px] text-slate-900 dark:text-slate-100"
            >
              {line.replace(/^#{2,3}\s+/, '').replace(/\*\*/g, '')}
            </div>
          );
        }
        if (/^\*\*[^*]+\*\*:?$/.test(line)) {
          return (
            <div
              key={idx}
              className="pt-1 font-sans font-bold text-[12px] text-slate-900 dark:text-slate-100"
            >
              {line.replace(/\*\*/g, '')}
            </div>
          );
        }

        // Bullet points
        const isBullet = /^[-*•]\s+/.test(line);
        const content = isBullet ? line.replace(/^[-*•]\s+/, '') : line;
        const segments = content.split(/(\*\*[^*]+\*\*)/g);
        const formatted = segments.map((seg, sIdx) => {
          if (seg.startsWith('**') && seg.endsWith('**') && seg.length > 4) {
            return (
              <strong key={sIdx} className="font-semibold text-slate-900 dark:text-slate-100">
                {seg.slice(2, -2)}
              </strong>
            );
          }
          return <React.Fragment key={sIdx}>{seg}</React.Fragment>;
        });

        if (isBullet) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-1">
              <span className="mt-1.5 w-1 h-1 rounded-full bg-blue-500 shrink-0" />
              <div className="min-w-0 flex-1">{formatted}</div>
            </div>
          );
        }
        return <p key={idx}>{formatted}</p>;
      })}
    </div>
  );
}

export const AiDeskDrawer: React.FC<AiDeskDrawerProps> = ({
  open,
  onClose,
  activeTicker,
  activeWorkspaceLabel,
}) => {
  const { holdings, watchlist, marketVersion } = useAppData();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const contextSummary = useMemo(() => {
    void marketVersion;
    const parts: string[] = [`Active Screen: ${activeWorkspaceLabel}`];
    if (activeTicker) {
      const s = STOCK_BY_TICKER[activeTicker];
      if (s) {
        const matrix = computeMultiIndicatorMatrix(s.bars);
        const dcLast = matrix?.donchianSummary?.latestAlert;
        parts.push(
          `Active Stock: ${s.ticker} (${s.name}) | Sector: ${s.sector} (${s.capBucket}) | LTP: ${formatINR(s.latestClose)} (${formatPct(s.dailyChangePct)})`
        );
        if (matrix) {
          parts.push(
            `Technical Matrix: ${matrix.consensus} (${matrix.scorePct}/100, ${matrix.bullishCount} Bull / ${matrix.bearishCount} Bear) | Supertrend: ${
              matrix.supertrendSummary?.direction === 1 ? 'Bullish' : 'Bearish'
            } | Donchian 20: ${matrix.donchianSummary?.regime || 'N/A'}${
              dcLast ? ` (Last ${dcLast.type} @ ${formatINR(dcLast.triggerPrice)}, ${dcLast.barsAgo}D ago)` : ''
            }`
          );
        }
        const peStr =
          s.dividend.epsInr > 0 ? (s.latestClose / s.dividend.epsInr).toFixed(1) : 'N/A';
        parts.push(
          `Fundamentals: P/E ${peStr}, ROE ${s.fundamentals.roePct.toFixed(1)}%, Qtr Rev YoY ${s.fundamentals.qtrRevYoY.toFixed(1)}%, Qtr EPS YoY ${s.fundamentals.qtrEpsYoY.toFixed(1)}%, Promoter ${s.fundamentals.promoterHoldingPct.toFixed(1)}%`
        );
      } else {
        parts.push(`Active Stock: ${activeTicker}`);
      }
    }
    if (holdings.length > 0) {
      const holdingTickers = holdings
        .slice(0, 12)
        .map((h) => {
          const st = STOCK_BY_TICKER[h.ticker];
          const ltp = st?.latestClose ?? h.avgCostInr;
          const pnl = h.avgCostInr > 0 ? ((ltp - h.avgCostInr) / h.avgCostInr) * 100 : 0;
          return `${h.ticker}(${h.shares}sh, avg ${formatINR(h.avgCostInr, 0)}, LTP ${formatINR(ltp, 0)}, ${pnl >= 0 ? '+' : ''}${pnl.toFixed(1)}%${h.stopLossInr ? `, SL ${formatINR(h.stopLossInr, 0)}` : ''})`;
        })
        .join('; ');
      parts.push(`User Portfolio (${holdings.length} stocks): ${holdingTickers}`);
    }
    if (watchlist.length > 0) {
      parts.push(`Watchlist (${watchlist.length}): ${watchlist.slice(0, 15).join(', ')}`);
    }
    parts.push(`Universe Tracked: ${INDIAN_STOCKS.length} NSE/BSE equities`);
    return parts.join('\n');
  }, [activeTicker, activeWorkspaceLabel, holdings, watchlist, marketVersion]);

  const quickPrompts = useMemo(() => {
    if (activeTicker) {
      return [
        `Summarize ${activeTicker}'s TechnoFunda setup & key risks`,
        `What invalidates ${activeTicker}'s current trend?`,
        `Compare ${activeTicker}'s technicals vs fundamentals`,
        'Check my portfolio exit risks',
      ];
    }
    return [
      'Review my portfolio for weak trends & concentration risks',
      'How should I combine Donchian, Supertrend, ADX & RSI > 60?',
      'What makes a high-conviction Minervini Stage 2 breakout?',
      'Key checklist before entering a 52-week high breakout in NSE',
    ];
  }, [activeTicker]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  if (!open) return null;

  const sendQuestion = async (qText: string) => {
    const trimmed = qText.trim();
    if (!trimmed || loading) return;
    setError(null);

    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      text: trimmed,
      timestamp: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
    };
    const nextHistory = [...messages, userMsg];
    setMessages(nextHistory);
    setInput('');
    setLoading(true);

    try {
      const data = await postAiJson<{ answer?: string; error?: string }>('/api/ai/ask', {
        question: trimmed,
        contextSummary,
        history: nextHistory.slice(-6).map((m) => ({ role: m.role, text: m.text })),
      });
      const aiMsg: ChatMessage = {
        id: `a_${Date.now()}`,
        role: 'assistant',
        text: data.answer || 'No response generated.',
        timestamp: new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reach AI Desk right now.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/50 backdrop-blur-[1px]">
      <div className="w-full max-w-md bg-white dark:bg-[#0F1522] h-full border-l border-slate-200 dark:border-slate-800 flex flex-col shadow-2xl">
        {/* Header */}
        <div className="px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles className="w-4 h-4 text-blue-500 shrink-0" />
            <div className="min-w-0">
              <div className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                AI TechnoFunda Desk
              </div>
              <div className="text-[11px] text-slate-500 truncate">
                {activeTicker
                  ? `Context: ${activeTicker} + Portfolio`
                  : `Context: ${activeWorkspaceLabel}`}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {messages.length > 0 && (
              <button
                onClick={() => {
                  setMessages([]);
                  setError(null);
                }}
                className="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Clear conversation"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800"
              aria-label="Close AI Desk"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 p-3.5 space-y-1.5">
                <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                  Ask about any NSE/BSE setup, indicator signal, or portfolio risk
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Automatically grounded with your active stock’s technicals, shareholding flow, and
                  portfolio holdings. Strictly technical structure, earnings momentum &amp; risk
                  management—no speculative price targets.
                </p>
              </div>

              <div className="space-y-1.5">
                <div className="text-[11px] font-semibold text-slate-500">Quick Prompts</div>
                <div className="space-y-1.5">
                  {quickPrompts.map((p) => (
                    <button
                      key={p}
                      onClick={() => void sendQuestion(p)}
                      disabled={loading}
                      className="w-full text-left px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-blue-500/60 hover:bg-blue-500/5 text-xs text-slate-700 dark:text-slate-300 transition-colors"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-lg px-3.5 py-2.5 ${
                  m.role === 'user'
                    ? 'ml-8 bg-blue-600 text-white text-xs'
                    : 'mr-2 border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/70'
                }`}
              >
                {m.role === 'user' ? (
                  <div className="leading-relaxed">{m.text}</div>
                ) : (
                  renderStructuredAiLines(m.text)
                )}
                <div
                  className={`mt-1.5 text-[10px] font-mono ${
                    m.role === 'user' ? 'text-blue-200 text-right' : 'text-slate-400'
                  }`}
                >
                  {m.timestamp}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="mr-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 px-3.5 py-2.5 flex items-center gap-2 text-xs text-slate-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
              Analyzing TechnoFunda data…
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-400">
              {error}
            </div>
          )}
        </div>

        {/* Input */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void sendQuestion(input);
          }}
          className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              activeTicker
                ? `Ask about ${activeTicker} or your portfolio…`
                : 'Ask a TechnoFunda question…'
            }
            maxLength={500}
            className="flex-1 px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
