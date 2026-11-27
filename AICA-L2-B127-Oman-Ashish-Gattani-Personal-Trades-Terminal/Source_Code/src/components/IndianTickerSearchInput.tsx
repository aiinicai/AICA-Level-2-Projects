import React, { useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw, Search, X } from 'lucide-react';
import { INDIAN_STOCKS } from '../data/indianMarketData';
import { formatINR } from '../utils/formatters';

interface LiveSearchItem {
  ticker: string;
  yahooSymbol: string;
  name: string;
  exchange: string;
  sector: string;
}

interface IndianTickerSearchInputProps {
  currentTicker?: string;
  onSelectTicker: (ticker: string) => void;
  placeholder?: string;
  className?: string;
  compact?: boolean;
}

/**
 * Reusable All-India NSE/BSE Stock Search & Autocomplete Selector.
 * Combines instant matches over the core NSE universe with live directory lookup
 * across 2,000+ NSE & BSE equities via /api/market/search, plus direct symbol load.
 */
export const IndianTickerSearchInput: React.FC<IndianTickerSearchInputProps> = ({
  currentTicker,
  onSelectTicker,
  placeholder = 'Search any NSE / BSE stock (e.g. MARUTI, SBIN, ZOMATO)...',
  className = '',
  compact = false,
}) => {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [remoteResults, setRemoteResults] = useState<LiveSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const localMatches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return INDIAN_STOCKS.slice(0, 8);
    return INDIAN_STOCKS.filter(
      (s) =>
        s.ticker.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.sector.toLowerCase().includes(q) ||
        s.bseCode.includes(q)
    ).slice(0, 8);
  }, [query]);

  // Live All-India NSE/BSE directory lookup
  useEffect(() => {
    const q = query.trim();
    if (!open || q.length < 2) {
      setRemoteResults([]);
      setSearching(false);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(() => {
      setSearching(true);
      fetch(`/api/market/search?q=${encodeURIComponent(q)}`)
        .then((res) => (res.ok ? res.json() : { results: [] }))
        .then((data: { results?: LiveSearchItem[] }) => {
          if (!cancelled) {
            const localSet = new Set(localMatches.map((m) => m.ticker.toUpperCase()));
            const filtered = (data.results || []).filter(
              (r) => !localSet.has(r.ticker.toUpperCase())
            );
            setRemoteResults(filtered.slice(0, 10));
            setSearching(false);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setRemoteResults([]);
            setSearching(false);
          }
        });
    }, 180);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, open, localMatches]);

  const cleanTypedSymbol = query
    .trim()
    .toUpperCase()
    .replace(/\.(NS|BO)$/i, '')
    .replace(/[^A-Z0-9&-]/g, '');

  const flatOptions = useMemo(() => {
    const list: {
      key: string;
      ticker: string;
      name: string;
      meta: string;
      price?: number;
      isRemote: boolean;
    }[] = localMatches.map((s) => ({
      key: `local_${s.ticker}`,
      ticker: s.ticker,
      name: s.name,
      meta: `NSE · ${s.sector}`,
      price: s.latestClose,
      isRemote: false,
    }));

    for (const r of remoteResults) {
      list.push({
        key: `remote_${r.yahooSymbol}`,
        ticker: r.ticker,
        name: r.name,
        meta: `${r.exchange} · ${r.sector}`,
        isRemote: true,
      });
    }

    if (
      cleanTypedSymbol.length >= 2 &&
      !list.some((item) => item.ticker.toUpperCase() === cleanTypedSymbol)
    ) {
      list.push({
        key: `direct_${cleanTypedSymbol}`,
        ticker: cleanTypedSymbol,
        name: `Analyze ${cleanTypedSymbol} directly from live NSE / BSE feed`,
        meta: 'Direct Symbol Lookup',
        isRemote: true,
      });
    }

    return list;
  }, [localMatches, remoteResults, cleanTypedSymbol]);

  useEffect(() => {
    setHighlightIdx(0);
  }, [query, flatOptions.length]);

  const choose = (ticker: string) => {
    const clean = ticker.trim().toUpperCase();
    if (!clean) return;
    onSelectTicker(clean);
    setQuery('');
    setOpen(false);
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <div className="relative flex items-center">
        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
        <input
          type="text"
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setOpen(true);
              setHighlightIdx((i) => Math.min(Math.max(0, flatOptions.length - 1), i + 1));
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              setHighlightIdx((i) => Math.max(0, i - 1));
            } else if (e.key === 'Enter') {
              e.preventDefault();
              if (flatOptions[highlightIdx]) {
                choose(flatOptions[highlightIdx].ticker);
              } else if (cleanTypedSymbol.length >= 2) {
                choose(cleanTypedSymbol);
              }
            } else if (e.key === 'Escape') {
              setOpen(false);
            }
          }}
          placeholder={currentTicker ? `${currentTicker} · ${placeholder}` : placeholder}
          className={`w-full pl-8 pr-7 ${
            compact ? 'py-1.5 text-xs' : 'py-2 text-xs'
          } rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500`}
        />
        {searching ? (
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-500 absolute right-2.5" />
        ) : query ? (
          <button
            type="button"
            onClick={() => setQuery('')}
            aria-label="Clear search"
            className="absolute right-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : null}
      </div>

      {open && (
        <div className="absolute right-0 left-0 mt-1.5 z-50 min-w-[300px] max-h-[340px] overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#0F1522] shadow-xl divide-y divide-slate-200/70 dark:divide-slate-800/70">
          <div className="px-3 py-1.5 bg-slate-50 dark:bg-slate-900 text-[10px] font-medium text-slate-500 flex items-center justify-between">
            <span>
              {query.trim().length < 2
                ? 'Popular NSE Leaders — Type 2+ chars for all 2,000+ NSE/BSE stocks'
                : searching
                ? 'Searching All-India NSE & BSE directory…'
                : `${flatOptions.length} matching Indian equities`}
            </span>
            <span className="font-mono">Enter</span>
          </div>

          {flatOptions.map((item, idx) => (
            <button
              key={item.key}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                choose(item.ticker);
              }}
              onMouseEnter={() => setHighlightIdx(idx)}
              className={`w-full px-3 py-2 text-left flex items-center justify-between gap-2 transition-colors ${
                idx === highlightIdx
                  ? 'bg-blue-600/10 dark:bg-blue-500/20'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-mono text-xs font-bold ${
                      item.isRemote
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-slate-900 dark:text-slate-100'
                    }`}
                  >
                    {item.ticker}
                  </span>
                  <span className="text-[10px] text-slate-500 truncate">{item.meta}</span>
                </div>
                <div className="text-[11px] text-slate-600 dark:text-slate-400 truncate">
                  {item.name}
                </div>
              </div>
              {item.price !== undefined ? (
                <span className="font-mono tabular-nums text-[11px] font-semibold text-slate-700 dark:text-slate-300 shrink-0">
                  {formatINR(item.price, 0)}
                </span>
              ) : (
                <span className="font-mono text-[10px] text-blue-600 dark:text-blue-400 shrink-0">
                  Live →
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
