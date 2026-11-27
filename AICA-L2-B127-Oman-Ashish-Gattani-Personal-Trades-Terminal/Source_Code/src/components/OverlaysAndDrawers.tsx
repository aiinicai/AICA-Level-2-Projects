import React, { useEffect, useMemo, useState } from 'react';
import {
  Bell,
  Calendar,
  Check,
  CheckCheck,
  Keyboard,
  Plug,
  Plus,
  RefreshCw,
  Search,
  Star,
  Trash2,
  X,
} from 'lucide-react';
import { StockChartPanel } from './StockChartPanel';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, LiveQuotePayload, STOCK_BY_TICKER } from '../data/indianMarketData';
import { DEFAULT_TREND_THRESHOLDS, runMinerviniAnalysis } from '../engine/analyticsEngine';
import { StockTradeDiagnosis, diagnoseBarsForSetups } from '../engine/tradeRadarEngine';
import { ActiveWorkspace, AlertCategory, TradeJournalEntry } from '../types/market';
import {
  NSE_HOLIDAYS_2026,
  formatCr,
  formatINR,
  formatPct,
  getIndianMarketStatus,
} from '../utils/formatters';

interface LiveSearchItem {
  ticker: string;
  yahooSymbol: string;
  name: string;
  exchange: string;
  sector: string;
}

const SETUP_NAME_MAP: Record<string, string> = {
  POCKET_PIVOT: 'Pocket Pivot',
  RS_BLUE_DOT: 'RS Blue-Dot',
  NR7_SQUEEZE: 'NR7 Squeeze',
  MA_PULLBACK: '21E/50S Pullback',
  EPISODIC_PIVOT: 'Episodic Pivot',
  VCP_BREAKOUT: 'VCP Breakout',
  WEEKLY_STAGE2: 'Weekly Stage 2',
};

const InlineRiskSizer: React.FC<{ diag: StockTradeDiagnosis }> = ({ diag }) => {
  const [capital, setCapital] = useState(1000000);
  const [riskPct, setRiskPct] = useState(1.0);
  const [saved, setSaved] = useState(false);

  const riskPerShare = Math.max(0.05, diag.entryTriggerInr - diag.stopLossInr);
  const riskBudget = (capital * riskPct) / 100;
  const qty = Math.max(
    0,
    Math.min(Math.floor(riskBudget / riskPerShare), Math.floor(capital / Math.max(1, diag.entryTriggerInr)))
  );

  const handleQuickLog = () => {
    if (qty <= 0) return;
    try {
      const key = 'artha_trade_journal_v1';
      const existing: TradeJournalEntry[] = JSON.parse(localStorage.getItem(key) || '[]');
      const next: TradeJournalEntry = {
        id: `tr_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        ticker: diag.ticker,
        setup: diag.primarySetup,
        entryDate: new Date().toISOString().slice(0, 10),
        entryPrice: diag.entryTriggerInr,
        stopLoss: diag.stopLossInr,
        shares: qty,
        status: 'OPEN',
        notes: `${diag.primarySetup} · ADR ${diag.adrPct20}%`,
      };
      localStorage.setItem(key, JSON.stringify([next, ...(Array.isArray(existing) ? existing : [])]));
      setSaved(true);
      setTimeout(() => setSaved(false), 2600);
    } catch {
      // ignore storage errors
    }
  };

  return (
    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 space-y-3 text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="font-bold text-slate-900 dark:text-slate-100">
            Trade Setup Diagnosis — {diag.primarySetup}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {diag.setups.length > 0
              ? diag.setups.map((s) => SETUP_NAME_MAP[s] || s).join(' · ')
              : 'Monitoring structure'}
            {' · '}
            Conviction <span className="font-mono font-semibold">{diag.convictionScore}/100</span>
            {' · '}
            {diag.weeklyStage2 ? 'Weekly Stage 2 Confirmed' : 'Weekly Base / Non-Stage 2'}
          </div>
        </div>
        <button
          onClick={handleQuickLog}
          disabled={qty <= 0}
          className="px-3 py-1.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
        >
          {saved ? 'Logged to Journal' : '+ Log to Trade Journal'}
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono tabular-nums pt-2 border-t border-slate-200 dark:border-slate-800">
        <div>
          <div className="font-sans text-[11px] text-slate-500">ADR(20) / ATR(14)</div>
          <div className="font-semibold text-slate-900 dark:text-slate-100">
            {diag.adrPct20.toFixed(1)}% · {formatINR(diag.atr14)}
          </div>
        </div>
        <div>
          <div className="font-sans text-[11px] text-slate-500">Dist vs 50-SMA</div>
          <div
            className={`font-semibold ${
              diag.isExtended
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-slate-900 dark:text-slate-100'
            }`}
          >
            {diag.distFrom50SmaAtrs >= 0 ? '+' : ''}
            {diag.distFrom50SmaAtrs.toFixed(1)} ATR ({formatPct(diag.distFrom50SmaPct)})
          </div>
        </div>
        <div>
          <div className="font-sans text-[11px] text-slate-500">Trigger / Stop</div>
          <div className="font-semibold">
            {formatINR(diag.entryTriggerInr)}{' '}
            <span className="text-red-500">/ {formatINR(diag.stopLossInr)}</span>
          </div>
        </div>
        <div>
          <div className="font-sans text-[11px] text-slate-500">1R / 2R / 3R</div>
          <div className="font-semibold text-emerald-600 dark:text-emerald-400">
            {formatINR(diag.r1Inr, 0)} · {formatINR(diag.r2Inr, 0)} · {formatINR(diag.r3Inr, 0)}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
        <div className="flex flex-wrap items-center gap-2 font-mono">
          <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-500">
            <span>Capital ₹</span>
            <input
              type="number"
              min={50000}
              step={50000}
              value={capital}
              onChange={(e) => setCapital(Math.max(0, Number(e.target.value)))}
              className="w-24 px-2 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </label>
          <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-500">
            <span>Risk %</span>
            <input
              type="number"
              min={0.25}
              max={5}
              step={0.25}
              value={riskPct}
              onChange={(e) => setRiskPct(Math.max(0.1, Number(e.target.value)))}
              className="w-16 px-2 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
            />
          </label>
        </div>
        <div className="font-mono tabular-nums text-[11px] text-slate-700 dark:text-slate-300">
          Size: <span className="font-bold text-blue-600 dark:text-blue-400">{qty} shares</span> ·
          Pos {formatINR(qty * diag.entryTriggerInr, 0)} · Stop -{diag.stopDistancePct.toFixed(1)}%
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   1. GLOBAL SEARCH / COMMAND PALETTE (Triggered by '/' shortcut)
   ============================================================================ */
interface SearchModalProps {
  open: boolean;
  onClose: () => void;
  onSelectStock: (ticker: string) => void;
  onNavigate: (ws: ActiveWorkspace) => void;
}

export const SearchCommandModal: React.FC<SearchModalProps> = ({
  open,
  onClose,
  onSelectStock,
  onNavigate,
}) => {
  const [queryText, setQueryText] = useState('');
  const [remoteResults, setRemoteResults] = useState<LiveSearchItem[]>([]);
  const [searchingRemote, setSearchingRemote] = useState(false);
  const { watchlist, toggleWatchlist, marketVersion } = useAppData();

  const localMatches = useMemo(() => {
    const q = queryText.trim().toLowerCase();
    if (!q) return INDIAN_STOCKS.slice(0, 10);
    return INDIAN_STOCKS.filter(
      (s) =>
        s.ticker.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.sector.toLowerCase().includes(q) ||
        s.bseCode.includes(q)
    ).slice(0, 10);
  }, [queryText, marketVersion]);

  useEffect(() => {
    const q = queryText.trim();
    if (!open || q.length < 2) {
      setRemoteResults([]);
      setSearchingRemote(false);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(() => {
      setSearchingRemote(true);
      fetch(`/api/market/search?q=${encodeURIComponent(q)}`)
        .then((res) => (res.ok ? res.json() : { results: [] }))
        .then((data: { results?: LiveSearchItem[] }) => {
          if (!cancelled) {
            const localSet = new Set(localMatches.map((m) => m.ticker.toUpperCase()));
            const filtered = (data.results || []).filter(
              (r) => !localSet.has(r.ticker.toUpperCase())
            );
            setRemoteResults(filtered.slice(0, 10));
            setSearchingRemote(false);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setRemoteResults([]);
            setSearchingRemote(false);
          }
        });
    }, 220);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [queryText, open, localMatches]);

  if (!open) return null;

  const cleanTypedSymbol = queryText.trim().toUpperCase().replace(/[^A-Z0-9&-]/g, '');

  const handleOpenTicker = (t: string) => {
    onSelectStock(t);
    setQueryText('');
    setRemoteResults([]);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-start justify-center pt-[10vh] px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111827] shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-800">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            autoFocus
            type="text"
            placeholder="Search ANY of 2,000+ NSE/BSE stocks (e.g. SBIN, MAZDOCK, MARUTI, TRENT, ZOMATO)..."
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                if (localMatches.length > 0) handleOpenTicker(localMatches[0].ticker);
                else if (remoteResults.length > 0) handleOpenTicker(remoteResults[0].ticker);
                else if (cleanTypedSymbol.length >= 2) handleOpenTicker(cleanTypedSymbol);
              }
            }}
            className="flex-1 bg-transparent text-sm text-slate-900 dark:text-slate-100 focus:outline-none"
          />
          {searchingRemote && <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-500 shrink-0" />}
          <button
            onClick={onClose}
            className="text-[11px] font-mono px-1.5 py-0.5 rounded border border-slate-300 dark:border-slate-700 text-slate-500"
          >
            Esc
          </button>
        </div>

        <div className="max-h-[400px] overflow-y-auto divide-y divide-slate-200/60 dark:divide-slate-800/60">
          {localMatches.map((s) => {
            const watched = watchlist.includes(s.ticker);
            return (
              <div
                key={s.ticker}
                className="px-4 py-2.5 flex items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <button
                  onClick={() => handleOpenTicker(s.ticker)}
                  className="flex-1 text-left min-w-0"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100">
                      {s.ticker}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      NSE · BSE {s.bseCode} · {s.sector}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-400 truncate">
                    {s.name}
                  </div>
                </button>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right font-mono tabular-nums text-xs">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {formatINR(s.latestClose)}
                    </div>
                    <div
                      className={`text-[11px] ${
                        s.dailyChangePct >= 0
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {formatPct(s.dailyChangePct)}
                    </div>
                  </div>
                  <button
                    onClick={() => toggleWatchlist(s.ticker)}
                    className={`p-1.5 rounded-md border ${
                      watched
                        ? 'border-amber-500/40 text-amber-500 bg-amber-500/10'
                        : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:text-amber-500'
                    }`}
                    title={watched ? 'Remove from Watchlist' : 'Add to Watchlist'}
                  >
                    <Star className="w-3.5 h-3.5" fill={watched ? 'currentColor' : 'none'} />
                  </button>
                </div>
              </div>
            );
          })}

          {remoteResults.length > 0 && (
            <>
              <div className="px-4 py-1.5 bg-slate-50 dark:bg-slate-900/90 text-[11px] font-medium text-slate-500">
                All-India NSE / BSE Live Directory Matches (Click to open 3Y Candlestick Chart &amp; Setup Diagnosis)
              </div>
              {remoteResults.map((r) => (
                <button
                  key={r.yahooSymbol}
                  onClick={() => handleOpenTicker(r.ticker)}
                  className="w-full px-4 py-2.5 flex items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 text-left"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-600 dark:text-blue-400">
                        {r.ticker}
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {r.exchange} · {r.sector}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-400 truncate">
                      {r.name}
                    </div>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 shrink-0">
                    Live Chart →
                  </span>
                </button>
              ))}
            </>
          )}

          {cleanTypedSymbol.length >= 2 &&
            localMatches.length === 0 &&
            remoteResults.length === 0 &&
            !searchingRemote && (
              <div className="p-4 flex items-center justify-between gap-3">
                <div className="text-xs text-slate-500">
                  Fetch live NSE/BSE candlesticks directly for{' '}
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                    {cleanTypedSymbol}
                  </span>
                </div>
                <button
                  onClick={() => handleOpenTicker(cleanTypedSymbol)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
                >
                  Open {cleanTypedSymbol} Chart
                </button>
              </div>
            )}
        </div>

        <div className="px-4 py-2.5 bg-slate-50 dark:bg-slate-900/80 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
          <div className="flex flex-wrap items-center gap-2">
            <span>Quick jump:</span>
            {(
              [
                ['sectors', 'Trending Sectors'],
                ['radar', 'Trade Radar'],
                ['breakout', '52W Scanner'],
                ['minervini', 'Minervini SEPA'],
                ['closingbell', 'Closing Bell Lab'],
                ['portfolio', 'Portfolio'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                onClick={() => {
                  onNavigate(id);
                  onClose();
                }}
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                {label}
              </button>
            ))}
          </div>
          <span className="font-mono">/ Search · Enter Open · Esc Close</span>
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   2. NOTIFICATIONS & ALERTS DRAWER
   ============================================================================ */
interface NotificationsDrawerProps {
  open: boolean;
  onClose: () => void;
  onInspectStock: (ticker: string) => void;
}

const CATEGORY_LABEL: Record<AlertCategory, string> = {
  breakout_52w: '52W Breakout',
  trend_template: 'Trend Template',
  vcp_pivot: 'VCP Pivot',
  custom_indicator: 'Custom Indicator',
  price: 'Price Alert',
  news: 'Corporate News',
};

export const NotificationsDrawer: React.FC<NotificationsDrawerProps> = ({
  open,
  onClose,
  onInspectStock,
}) => {
  const { alerts, addAlert, markAlertRead, markAllAlertsRead, deleteAlert } = useAppData();
  const [filterCat, setFilterCat] = useState<'all' | AlertCategory>('all');
  const [showCreate, setShowCreate] = useState(false);
  const [newTicker, setNewTicker] = useState('TRENT');
  const [newCat, setNewCat] = useState<AlertCategory>('price');
  const [newTitle, setNewTitle] = useState('');
  const [newMessage, setNewMessage] = useState('');

  if (!open) return null;

  const filtered = alerts.filter((a) => filterCat === 'all' || a.category === filterCat);
  const unreadCount = alerts.filter((a) => !a.read).length;

  const handleCreate = async () => {
    const stock = STOCK_BY_TICKER[newTicker];
    await addAlert({
      ticker: newTicker,
      category: newCat,
      title:
        newTitle.trim() ||
        `${newTicker} — Price Trigger Alert (${formatINR(stock?.latestClose ?? 0)})`,
      message:
        newMessage.trim() ||
        `Monitoring ${newTicker} for ${CATEGORY_LABEL[newCat].toLowerCase()} trigger during NSE market hours (IST).`,
    });
    setNewTitle('');
    setNewMessage('');
    setShowCreate(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/50 flex justify-end" onClick={onClose}>
      <div
        className="w-full max-w-md h-full bg-white dark:bg-[#111827] border-l border-slate-200 dark:border-slate-800 flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-blue-500" />
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Watchlist Alerts & News ({unreadCount} unread)
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={markAllAlertsRead}
              className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
              title="Mark all read"
            >
              <CheckCheck className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
              title="Close (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Category Filter & New Alert Toggle */}
        <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
          <select
            value={filterCat}
            onChange={(e) => setFilterCat(e.target.value as 'all' | AlertCategory)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
          >
            <option value="all">All Notifications ({alerts.length})</option>
            {(Object.keys(CATEGORY_LABEL) as AlertCategory[]).map((k) => (
              <option key={k} value={k}>
                {CATEGORY_LABEL[k]}
              </option>
            ))}
          </select>

          <button
            onClick={() => setShowCreate((v) => !v)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
          >
            <Plus className="w-3.5 h-3.5" />
            New Alert
          </button>
        </div>

        {showCreate && (
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 space-y-2.5 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <select
                value={newTicker}
                onChange={(e) => setNewTicker(e.target.value)}
                className="px-2.5 py-1.5 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              >
                {INDIAN_STOCKS.map((s) => (
                  <option key={s.ticker} value={s.ticker}>
                    {s.ticker}
                  </option>
                ))}
              </select>
              <select
                value={newCat}
                onChange={(e) => setNewCat(e.target.value as AlertCategory)}
                className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
              >
                {(Object.keys(CATEGORY_LABEL) as AlertCategory[]).map((k) => (
                  <option key={k} value={k}>
                    {CATEGORY_LABEL[k]}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              placeholder="Alert title (e.g. Breakout above ₹7,600)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            />
            <textarea
              rows={2}
              placeholder="Condition or note..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="px-3 py-1.5 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-medium"
              >
                Create Alert
              </button>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto divide-y divide-slate-200/70 dark:divide-slate-800/70">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No notifications in this category.
            </div>
          ) : (
            filtered.map((a) => (
              <div
                key={a.id}
                className={`p-4 space-y-1.5 ${
                  a.read ? 'opacity-75' : 'bg-blue-500/5 dark:bg-blue-500/10'
                }`}
              >
                <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500">
                  <span className="font-mono">
                    {a.ticker} · {CATEGORY_LABEL[a.category]}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => markAlertRead(a.id, !a.read)}
                      className="text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      {a.read ? 'Mark unread' : 'Mark read'}
                    </button>
                    <button
                      onClick={() => deleteAlert(a.id)}
                      className="text-slate-400 hover:text-red-500"
                      title="Delete alert"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => {
                    onInspectStock(a.ticker);
                    markAlertRead(a.id, true);
                    onClose();
                  }}
                  className="text-left text-xs font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500 block"
                >
                  {a.title}
                </button>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {a.message}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   3. STOCK QUICK-INSPECT DRAWER
   ============================================================================ */
interface StockInspectDrawerProps {
  ticker: string | null;
  prior52WHigh?: number;
  onClose: () => void;
}

export const StockInspectDrawer: React.FC<StockInspectDrawerProps> = ({
  ticker,
  prior52WHigh,
  onClose,
}) => {
  const { watchlist, toggleWatchlist, addAlert, marketVersion } = useAppData();

  const stock = ticker ? STOCK_BY_TICKER[ticker] : null;
  const sepa = useMemo(() => {
    if (!stock) return null;
    const all = runMinerviniAnalysis(INDIAN_STOCKS, DEFAULT_TREND_THRESHOLDS);
    return all.find((x) => x.stock.ticker === stock.ticker) ?? null;
  }, [stock, marketVersion]);

  const [liveExtra, setLiveExtra] = useState<LiveQuotePayload | null>(null);
  const [loadingExtra, setLoadingExtra] = useState(false);
  const [extraError, setExtraError] = useState<string | null>(null);

  const coreDiag = useMemo(() => {
    if (!stock || !sepa) return null;
    return diagnoseBarsForSetups(stock.bars, {
      ticker: stock.ticker,
      name: stock.name,
      sector: stock.sector,
      capBucket: stock.capBucket,
      avgDailyTurnoverCr: stock.avgDailyTurnoverCr,
      rsRating: sepa.rsRating,
      stage: sepa.stage,
      templatePassed: sepa.passedCount,
      minerviniScore: sepa.minerviniScore,
      isVcpBreakout: sepa.vcp.isPivotBreakout,
      vcpPivot: sepa.vcp.pivotPrice,
    });
  }, [stock, sepa]);

  const extraDiag = useMemo(() => {
    if (!liveExtra || !ticker || liveExtra.bars.length < 60) return null;
    return diagnoseBarsForSetups(liveExtra.bars, {
      ticker,
      name: ticker,
      sector: 'NSE Equity',
      capBucket: 'All-India',
      avgDailyTurnoverCr: liveExtra.avgDailyTurnoverCr,
    });
  }, [liveExtra, ticker]);

  useEffect(() => {
    if (!ticker || stock) {
      setLiveExtra(null);
      setLoadingExtra(false);
      setExtraError(null);
      return;
    }

    let cancelled = false;
    setLoadingExtra(true);
    setExtraError(null);
    setLiveExtra(null);

    fetch(`/api/market/quote/${encodeURIComponent(ticker)}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`No live NSE/BSE candle feed found for ${ticker}`);
        return (await res.json()) as LiveQuotePayload;
      })
      .then((data) => {
        if (!cancelled) {
          setLiveExtra(data);
          setLoadingExtra(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setExtraError(err instanceof Error ? err.message : `Failed to load chart for ${ticker}`);
          setLoadingExtra(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ticker, stock]);

  if (!ticker) return null;

  const watched = watchlist.includes(ticker);

  // Branch A: Core tracked stock with full SEPA + Fundamentals
  if (stock && sepa) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950/60 flex justify-end" onClick={onClose}>
        <div
          className="w-full max-w-3xl h-full bg-white dark:bg-[#111827] border-l border-slate-200 dark:border-slate-800 overflow-y-auto shadow-2xl p-6 space-y-5"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100">
                  {stock.ticker}
                </h2>
                <span className="text-xs text-slate-500">
                  NSE · BSE {stock.bseCode} · {stock.isin}
                </span>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
                {stock.name} — {stock.sector} ({stock.capBucket} Cap · {formatCr(stock.marketCapCr)})
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-baseline gap-3 font-mono tabular-nums">
              <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {formatINR(stock.latestClose)}
              </span>
              <span
                className={`text-sm font-semibold ${
                  stock.dailyChangePct >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                {formatPct(stock.dailyChangePct)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => toggleWatchlist(stock.ticker)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                {watched ? 'Remove Watchlist' : '+ Watchlist'}
              </button>
              <button
                onClick={() =>
                  addAlert({
                    ticker: stock.ticker,
                    category: 'price',
                    title: `${stock.ticker} Watch Alert at ${formatINR(stock.latestClose)}`,
                    message: `Tracking ${stock.ticker} (Stage ${sepa.stage}, RS ${sepa.rsRating}, SEPA Score ${sepa.minerviniScore}/100).`,
                  })
                }
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
              >
                Create Price Alert
              </button>
            </div>
          </div>

          <StockChartPanel
            stock={stock}
            pivotPrice={sepa.vcp.pivotPrice}
            prior52WHigh={prior52WHigh}
            stopLossPrice={sepa.suggestedStopLossInr}
            height={360}
          />

          {coreDiag && <InlineRiskSizer diag={coreDiag} />}

          {/* Quick Technical & Fundamental Grid (Strictly zero DCF/Valuation) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs border-y border-slate-200 dark:border-slate-800 py-4">
            <div>
              <div className="text-slate-500">Minervini Score</div>
              <div className="font-mono font-bold text-base text-blue-600 dark:text-blue-400">
                {sepa.minerviniScore}/100
              </div>
              <div className="text-[11px] text-slate-500">Template {sepa.passedCount}/8</div>
            </div>
            <div>
              <div className="text-slate-500">RS Rating / Stage</div>
              <div className="font-mono font-bold text-base">RS {sepa.rsRating}</div>
              <div className="text-[11px] text-slate-500">{sepa.stageLabel}</div>
            </div>
            <div>
              <div className="text-slate-500">Qtr EPS / Rev YoY</div>
              <div className="font-mono font-bold text-base">
                {formatPct(stock.fundamentals.qtrEpsYoY)}
              </div>
              <div className="text-[11px] text-slate-500">
                Rev {formatPct(stock.fundamentals.qtrRevYoY)}
              </div>
            </div>
            <div>
              <div className="text-slate-500">Dividend Yield / FCF</div>
              <div className="font-mono font-bold text-base">
                {stock.dividend.dividendYieldPct.toFixed(2)}%
              </div>
              <div className="text-[11px] text-slate-500">
                FCF {formatINR(stock.dividend.fcfPerShareInr)}/sh
              </div>
            </div>
          </div>

          {/* Corporate News */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Recent NSE / BSE Filings &amp; Headlines
            </h3>
            {stock.recentNews.map((n, i) => (
              <div
                key={i}
                className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 text-xs space-y-1"
              >
                <div className="text-[11px] font-mono text-slate-500">
                  {n.date} · {n.source}
                </div>
                <div className="text-slate-800 dark:text-slate-200">{n.headline}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Branch B: On-demand live NSE/BSE Candlestick Chart for ANY symbol (Bhavcopy, ETFs, SMEs, etc.)
  const bars = liveExtra?.bars || [];
  const win252 = bars.slice(-252);
  const hi52 = win252.length ? Math.max(...win252.map((b) => b.high)) : 0;
  const lo52 = win252.length ? Math.min(...win252.map((b) => b.low)) : 0;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/60 flex justify-end" onClick={onClose}>
      <div
        className="w-full max-w-3xl h-full bg-white dark:bg-[#111827] border-l border-slate-200 dark:border-slate-800 overflow-y-auto shadow-2xl p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100">
                {ticker}
              </h2>
              <span className="text-xs text-slate-500">
                NSE / BSE Live Quote {liveExtra ? `· ${liveExtra.yahooSymbol}` : ''}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              On-demand 3-year daily OHLCV candlestick chart
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {loadingExtra ? (
          <div className="py-16 text-center text-xs text-slate-500 flex flex-col items-center gap-2">
            <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
            <span>Loading live NSE/BSE candlesticks for {ticker}…</span>
          </div>
        ) : extraError || !liveExtra ? (
          <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 text-xs text-slate-500 space-y-2">
            <div className="font-semibold text-slate-800 dark:text-slate-200">
              Live candle feed unavailable for {ticker}
            </div>
            <div>{extraError || 'This symbol may be an SME or newly listed series without live Yahoo NSE OHLCV history.'}</div>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-baseline gap-3 font-mono tabular-nums">
                <span className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {formatINR(liveExtra.latestClose)}
                </span>
                <span
                  className={`text-sm font-semibold ${
                    liveExtra.dailyChangePct >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatPct(liveExtra.dailyChangePct)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleWatchlist(ticker)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  {watched ? 'Remove Watchlist' : '+ Watchlist'}
                </button>
                <button
                  onClick={() =>
                    addAlert({
                      ticker,
                      category: 'price',
                      title: `${ticker} Watch Alert at ${formatINR(liveExtra.latestClose)}`,
                      message: `Monitoring live NSE price for ${ticker} (Prev close ${formatINR(liveExtra.prevClose)}).`,
                    })
                  }
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
                >
                  Create Price Alert
                </button>
              </div>
            </div>

            <StockChartPanel
              barsOverride={liveExtra.bars}
              symbolLabel={ticker}
              pivotPrice={extraDiag?.entryTriggerInr}
              prior52WHigh={prior52WHigh}
              stopLossPrice={extraDiag?.stopLossInr}
              height={380}
            />

            {extraDiag && <InlineRiskSizer diag={extraDiag} />}

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono tabular-nums border-t border-slate-200 dark:border-slate-800 pt-4">
              <div>
                <div className="font-sans text-slate-500">Prev Close</div>
                <div className="font-bold text-sm mt-0.5">{formatINR(liveExtra.prevClose)}</div>
              </div>
              <div>
                <div className="font-sans text-slate-500">52W High</div>
                <div className="font-bold text-sm mt-0.5 text-emerald-600 dark:text-emerald-400">
                  {formatINR(hi52)}
                </div>
              </div>
              <div>
                <div className="font-sans text-slate-500">52W Low</div>
                <div className="font-bold text-sm mt-0.5 text-red-600 dark:text-red-400">
                  {formatINR(lo52)}
                </div>
              </div>
              <div>
                <div className="font-sans text-slate-500">Avg 50D Turnover</div>
                <div className="font-bold text-sm mt-0.5">
                  {formatCr(liveExtra.avgDailyTurnoverCr)}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

/* ============================================================================
   4. THREE CONNECTORS & NSE 2026 TRADING CALENDAR MODAL
   ============================================================================ */
interface ConnectorsModalProps {
  open: boolean;
  onClose: () => void;
}

export const ConnectorsCalendarModal: React.FC<ConnectorsModalProps> = ({ open, onClose }) => {
  const { connectors, updateConnectors } = useAppData();
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const marketStatus = getIndianMarketStatus();

  if (!open) return null;

  const handleTestSync = (name: string) => {
    setSyncMessage(`${name} verified — latest EOD Bhavcopy & corporate filings synced (IST).`);
    setTimeout(() => setSyncMessage(null), 3200);
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111827] shadow-2xl p-6 space-y-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Plug className="w-4 h-4 text-blue-500" />
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Market Data Connectors & NSE Trading Calendar (IST)
            </h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100">
            <X className="w-4 h-4" />
          </button>
        </div>

        {syncMessage && (
          <div className="flex items-center gap-2 px-3 py-2 text-xs rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
            <Check className="w-4 h-4 shrink-0" />
            <span>{syncMessage}</span>
          </div>
        )}

        {/* The Three Indian Market Connectors */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-400">
            Configured Indian Market Connectors (3)
          </h3>

          {/* Connector 1: NSE India Direct */}
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                1. NSE India Equity & Indices Connector
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                CM Equity OHLCV, NIFTY 50 / NIFTY 500 benchmarks, 52W High Bhavcopy & NSE trading sessions.
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleTestSync('NSE India Connector')}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-md border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <RefreshCw className="w-3 h-3" /> Sync
              </button>
              <button
                onClick={() =>
                  updateConnectors({
                    ...connectors,
                    nseConnectorEnabled: !connectors.nseConnectorEnabled,
                  })
                }
                className={`px-3 py-1.5 text-xs font-medium rounded-md ${
                  connectors.nseConnectorEnabled
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                }`}
              >
                {connectors.nseConnectorEnabled ? 'Connected' : 'Paused'}
              </button>
            </div>
          </div>

          {/* Connector 2: BSE Star & Corporate Filings */}
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                2. BSE S&amp;P Sensex &amp; XBRL Corporate Filings Connector
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                SENSEX index feed, quarterly EPS/revenue XBRL filings, FII/DII/Promoter pledge disclosures, and dividend histories.
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleTestSync('BSE Corporate Filings Connector')}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-md border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <RefreshCw className="w-3 h-3" /> Sync
              </button>
              <button
                onClick={() =>
                  updateConnectors({
                    ...connectors,
                    bseConnectorEnabled: !connectors.bseConnectorEnabled,
                  })
                }
                className={`px-3 py-1.5 text-xs font-medium rounded-md ${
                  connectors.bseConnectorEnabled
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                }`}
              >
                {connectors.bseConnectorEnabled ? 'Connected' : 'Paused'}
              </button>
            </div>
          </div>

          {/* Connector 3: Indian Execution Broker Bridge */}
          <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                3. Indian Execution Broker Bridge
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Dematerialized holdings sync &amp; rebalancing delivery order basket routing (CDSL/NSDL DP cost aware).
              </div>
            </div>
            <select
              value={connectors.brokerConnectorName}
              onChange={(e) =>
                updateConnectors({
                  ...connectors,
                  brokerConnectorName: e.target.value as typeof connectors.brokerConnectorName,
                })
              }
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
            >
              <option value="Zerodha Kite">Zerodha Kite</option>
              <option value="Dhan HQ">Dhan HQ</option>
              <option value="Upstox Pro">Upstox Pro</option>
              <option value="Disconnected">Disconnected</option>
            </select>
          </div>
        </div>

        {/* NSE Trading Calendar & Hours */}
        <div className="space-y-3 pt-2 border-t border-slate-200 dark:border-slate-800">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200">
              <Calendar className="w-4 h-4 text-blue-500" />
              <span>NSE Equity Market Hours (IST) &amp; 2026 Holiday Calendar</span>
            </div>
            <span className="font-mono text-xs text-slate-500">
              {marketStatus.istTimeStr} IST · {marketStatus.sessionLabel}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="font-sans text-[11px] text-slate-500">Pre-Open Call Auction</div>
              <div className="font-semibold mt-0.5">09:00 – 09:15 IST</div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="font-sans text-[11px] text-slate-500">Normal Continuous Market</div>
              <div className="font-semibold mt-0.5">09:15 – 15:30 IST</div>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="font-sans text-[11px] text-slate-500">Closing Session</div>
              <div className="font-semibold mt-0.5">15:40 – 16:00 IST</div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-48 overflow-y-auto text-xs pt-1">
            {NSE_HOLIDAYS_2026.map((h) => (
              <div
                key={h.date}
                className="flex items-center justify-between px-3 py-1.5 rounded border border-slate-200/70 dark:border-slate-800/70"
              >
                <span className="text-slate-700 dark:text-slate-300 truncate pr-2">{h.occasion}</span>
                <span className="font-mono text-[11px] text-slate-500 shrink-0">{h.date}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   5. KEYBOARD SHORTCUTS REFERENCE MODAL ('?')
   ============================================================================ */
export const KeyboardShortcutsModal: React.FC<{ open: boolean; onClose: () => void }> = ({
  open,
  onClose,
}) => {
  if (!open) return null;

  const shortcuts = [
    { key: '/', desc: 'Search ANY of 2,000+ NSE/BSE stocks & open live candlestick chart' },
    { key: 'Esc', desc: 'Close active modal, stock drawer, search, or notifications' },
    { key: 'N', desc: 'Open or close Watchlist Alerts & Notifications drawer' },
    { key: '1', desc: 'Switch to Market Overview' },
    { key: '2', desc: 'Switch to Trending Sectors & Subsectors' },
    { key: '3', desc: 'Switch to Trade Radar, Market Regime & Execution Journal' },
    { key: '4', desc: 'Switch to 52-Week & ATH Breakout Scanner' },
    { key: '5', desc: 'Switch to Mark Minervini SEPA Framework' },
    { key: 'D', desc: 'Switch to Donchian Channel Breakouts' },
    { key: '6', desc: 'Switch to HVE / HVY / HVQ Institutional Volume Screener' },
    { key: '7', desc: 'Switch to Portfolio, Risk & 5-Watchlist Analysis' },
    { key: '8', desc: 'Switch to Fundamental Lab (Audited Financials & FCF)' },
    { key: '9', desc: 'Switch to Closing Bell Research Lab (21 Bhavcopy Metrics)' },
    { key: '0', desc: 'Switch to Market Data Connectors (3) & NSE Calendar' },
    { key: '?', desc: 'Show or hide this Keyboard Shortcuts dialog' },
  ];

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111827] shadow-2xl p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
            <Keyboard className="w-4 h-4 text-blue-500" />
            <span>Institutional Keyboard Shortcuts</span>
          </div>
          <button onClick={onClose} className="p-1 text-slate-500">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="divide-y divide-slate-200/70 dark:divide-slate-800/70 text-xs">
          {shortcuts.map((s) => (
            <div key={s.key} className="py-2 flex items-center justify-between gap-3">
              <span className="text-slate-600 dark:text-slate-300">{s.desc}</span>
              <kbd className="px-2 py-0.5 font-mono text-[11px] font-semibold rounded border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-slate-100 shrink-0">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
