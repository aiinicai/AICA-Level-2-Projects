import React, { useMemo, useRef, useState } from 'react';
import * as XLSX from 'xlsx';
import {
  AlertTriangle,
  BellPlus,
  Check,
  Download,
  Edit3,
  FileSpreadsheet,
  FolderPlus,
  Layers,
  LineChart,
  ListPlus,
  Plus,
  RefreshCw,
  Search,
  Star,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, STOCK_BY_TICKER } from '../data/indianMarketData';
import { resolveStockSectorContext } from '../engine/sectorTrendEngine';
import {
  TopBuyWatchlistItem,
  computeMultiIndicatorMatrix,
  computeTopBuyWatchlist,
} from '../engine/tradeRadarEngine';
import { CustomWatchlist } from '../types/market';
import { formatINR, formatPct } from '../utils/formatters';

interface WatchlistAnalysisSectionProps {
  onInspectStock: (ticker: string) => void;
}

type ImportMode = 'merge' | 'replace';
type ImportSubTab = 'tickers' | 'excel' | 'single';
type RowFilter = 'all' | 'buy_only' | 'stage2' | 'risk';
type SortKey = 'score' | 'matrix' | 'rs' | 'change1d' | 'eps';

interface EnrichedWatchlistRow {
  ticker: string;
  known: boolean;
  rec: TopBuyWatchlistItem | null;
  sma200Signal: 'Bullish' | 'Neutral' | 'Bearish' | null;
  stSignal: 'Bullish' | 'Neutral' | 'Bearish' | null;
  dcSignal: 'Bullish' | 'Neutral' | 'Bearish' | null;
  rsi14: number | null;
  riskFlags: string[];
}

interface WatchlistSummaryStats {
  watchlist: CustomWatchlist;
  matchedCount: number;
  unmatchedCount: number;
  avgCompositeScore: number;
  avgMatrixPct: number;
  strongBuyCount: number;
  buyCount: number;
  stage2Count: number;
  stage2Pct: number;
  avgRs: number;
  avgChange1D: number;
  riskCount: number;
  topSector: string;
  topSectorQuadrant: string | null;
}

const MAX_WATCHLISTS = 5;

function normalizeTickerToken(raw: string): string {
  return raw
    .trim()
    .toUpperCase()
    .replace(/^(NSE|BSE|NS|BO)[:.\-\s]+/i, '')
    .replace(/\.(NS|BO)$/i, '')
    .replace(/[^A-Z0-9&\-]/g, '')
    .slice(0, 20);
}

function parseCommaSeparatedTickers(raw: string): string[] {
  const tokens = raw
    .split(/[\s,;\n\r\t|]+/)
    .map(normalizeTickerToken)
    .filter((t) => t.length >= 1 && /[A-Z]/.test(t));
  return Array.from(new Set(tokens)).slice(0, 60);
}

function findTickerColumn(keys: string[]): string | undefined {
  const patterns = [
    /^ticker$/,
    /^symbol$/,
    /^trading\s*symbol$/,
    /^tradingsymbol$/,
    /^nse\s*symbol$/,
    /^stock$/,
    /^scrip$/,
    /ticker|symbol|scrip|stock/,
  ];
  for (const pat of patterns) {
    const hit = keys.find((k) => pat.test(k.trim().toLowerCase()));
    if (hit) return hit;
  }
  return keys[0];
}

export const WatchlistAnalysisSection: React.FC<WatchlistAnalysisSectionProps> = ({
  onInspectStock,
}) => {
  const {
    watchlist: mainWatchlist,
    customWatchlists,
    saveCustomWatchlist,
    deleteCustomWatchlist,
    addAlert,
    toggleWatchlist,
    marketVersion,
  } = useAppData();

  const [selectedId, setSelectedId] = useState<string>(
    () => customWatchlists[0]?.id ?? 'wl_slot_1'
  );
  const [showImportDrawer, setShowImportDrawer] = useState<boolean>(false);
  const [importSubTab, setImportSubTab] = useState<ImportSubTab>('tickers');
  const [importMode, setImportMode] = useState<ImportMode>('merge');
  const [csvInput, setCsvInput] = useState<string>(
    'NSE:RELIANCE, NSE:TCS, NSE:HAL, NSE:TRENT, NSE:BEL, NSE:ICICIBANK'
  );
  const [newWlName, setNewWlName] = useState<string>('');
  const [newWlNotes, setNewWlNotes] = useState<string>('');
  const [showNewForm, setShowNewForm] = useState<boolean>(false);
  const [editingMeta, setEditingMeta] = useState<boolean>(false);
  const [editName, setEditName] = useState<string>('');
  const [editNotes, setEditNotes] = useState<string>('');

  const [excelTickers, setExcelTickers] = useState<string[]>([]);
  const [excelFileName, setExcelFileName] = useState<string>('');
  const [excelError, setExcelError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [singleSearch, setSingleSearch] = useState<string>('');
  const [rowFilter, setRowFilter] = useState<RowFilter>('all');
  const [sortBy, setSortBy] = useState<SortKey>('score');
  const [toast, setToast] = useState<string | null>(null);
  const [alertedTickers, setAlertedTickers] = useState<Record<string, boolean>>({});

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3200);
  };

  // Ensure selected watchlist always points to an existing slot
  const activeWatchlist = useMemo(() => {
    if (customWatchlists.length === 0) return null;
    return customWatchlists.find((w) => w.id === selectedId) ?? customWatchlists[0];
  }, [customWatchlists, selectedId]);

  // Cached full NSE 60/15/25 Call / Score lookup across entire universe (O(1) per stock)
  const recByTicker = useMemo(() => {
    void marketVersion;
    const all = computeTopBuyWatchlist(
      INDIAN_STOCKS,
      INDIAN_STOCKS.length,
      (sec, ind) => resolveStockSectorContext(INDIAN_STOCKS, sec, ind, marketVersion)
    );
    return new Map(all.map((r) => [r.stock.ticker, r]));
  }, [marketVersion]);

  // Helper to enrich a single watchlist's tickers with 60/15/25 Call/Score + Matrix + Risk signals
  const analyzeTickers = useMemo(() => {
    return (tickers: string[]): EnrichedWatchlistRow[] => {
      return tickers.map((t) => {
        const clean = normalizeTickerToken(t);
        const rec = recByTicker.get(clean) ?? null;
        const stock = STOCK_BY_TICKER[clean];
        if (!stock || !rec) {
          return {
            ticker: clean,
            known: false,
            rec: null,
            sma200Signal: null,
            stSignal: null,
            dcSignal: null,
            rsi14: null,
            riskFlags: [],
          };
        }

        const sectorCtx = resolveStockSectorContext(
          INDIAN_STOCKS,
          stock.sector,
          stock.industry,
          marketVersion
        );
        const matrix = computeMultiIndicatorMatrix(
          stock.bars,
          {
            minerviniScore: rec.minerviniScore,
            passedCount: rec.templatePassed,
            stage: rec.stage,
            rsRating: rec.rsRating,
          },
          sectorCtx
        );

        const sma200Signal = matrix.signals.find((s) => s.id === 'sma_200')?.signal ?? null;
        const stSignal = matrix.signals.find((s) => s.id === 'supertrend_10_3')?.signal ?? null;
        const dcSignal = matrix.signals.find((s) => s.id === 'donchian_20')?.signal ?? null;
        const rsi14 = matrix.rsi14 ?? null;

        const riskFlags: string[] = [];
        if (sma200Signal === 'Bearish') riskFlags.push('Below 200 SMA');
        if (stSignal === 'Bearish') riskFlags.push('Supertrend SELL');
        if (dcSignal === 'Bearish') riskFlags.push('DC(20) Lower');
        if (rec.stage === 4) riskFlags.push('Stage 4');
        if (rec.technicalConsensus === 'Sell' || rec.technicalConsensus === 'Strong Sell') {
          riskFlags.push(`Matrix ${rec.technicalConsensus}`);
        }

        return {
          ticker: clean,
          known: true,
          rec,
          sma200Signal,
          stSignal,
          dcSignal,
          rsi14,
          riskFlags,
        };
      });
    };
  }, [recByTicker, marketVersion]);

  // Compute side-by-side summary stats for ALL watchlists (up to 5)
  const allWatchlistStats = useMemo<WatchlistSummaryStats[]>(() => {
    return customWatchlists.map((wl) => {
      const rows = analyzeTickers(wl.tickers);
      const matched = rows.filter((r) => r.known && r.rec);
      const count = matched.length;
      if (count === 0) {
        return {
          watchlist: wl,
          matchedCount: 0,
          unmatchedCount: rows.length,
          avgCompositeScore: 0,
          avgMatrixPct: 0,
          strongBuyCount: 0,
          buyCount: 0,
          stage2Count: 0,
          stage2Pct: 0,
          avgRs: 0,
          avgChange1D: 0,
          riskCount: 0,
          topSector: '—',
          topSectorQuadrant: null,
        };
      }

      const avgCompositeScore = Math.round(
        matched.reduce((s, r) => s + (r.rec?.compositeScore ?? 0), 0) / count
      );
      const avgMatrixPct = Math.round(
        matched.reduce((s, r) => s + (r.rec?.matrixScorePct ?? 0), 0) / count
      );
      const strongBuyCount = matched.filter((r) => r.rec?.rating === 'Strong Buy').length;
      const buyCount = matched.filter((r) => r.rec?.rating === 'Buy').length;
      const stage2Count = matched.filter((r) => r.rec?.stage === 2).length;
      const stage2Pct = Math.round((stage2Count / count) * 100);
      const avgRs = Math.round(matched.reduce((s, r) => s + (r.rec?.rsRating ?? 0), 0) / count);
      const avgChange1D =
        matched.reduce((s, r) => s + (r.rec?.stock.dailyChangePct ?? 0), 0) / count;
      const riskCount = matched.filter((r) => r.riskFlags.length > 0).length;

      const secCounts = new Map<string, { count: number; quadrant: string | null }>();
      for (const r of matched) {
        if (!r.rec) continue;
        const sec = r.rec.stock.sector;
        const prev = secCounts.get(sec) ?? { count: 0, quadrant: r.rec.sectorQuadrant ?? null };
        prev.count += 1;
        if (!prev.quadrant && r.rec.sectorQuadrant) prev.quadrant = r.rec.sectorQuadrant;
        secCounts.set(sec, prev);
      }
      const topSecEntry = Array.from(secCounts.entries()).sort((a, b) => b[1].count - a[1].count)[0];

      return {
        watchlist: wl,
        matchedCount: count,
        unmatchedCount: rows.length - count,
        avgCompositeScore,
        avgMatrixPct,
        strongBuyCount,
        buyCount,
        stage2Count,
        stage2Pct,
        avgRs,
        avgChange1D,
        riskCount,
        topSector: topSecEntry ? topSecEntry[0] : '—',
        topSectorQuadrant: topSecEntry ? topSecEntry[1].quadrant : null,
      };
    });
  }, [customWatchlists, analyzeTickers]);

  // Active watchlist rows & sector breakdown
  const activeRows = useMemo(() => {
    if (!activeWatchlist) return [];
    return analyzeTickers(activeWatchlist.tickers);
  }, [activeWatchlist, analyzeTickers]);

  const activeStats = useMemo(() => {
    if (!activeWatchlist) return null;
    return allWatchlistStats.find((s) => s.watchlist.id === activeWatchlist.id) ?? null;
  }, [allWatchlistStats, activeWatchlist]);

  const activeSectorMix = useMemo(() => {
    const matched = activeRows.filter((r) => r.known && r.rec);
    if (matched.length === 0) return [];
    const map = new Map<
      string,
      { sector: string; count: number; pct: number; quadrant?: string; score?: number }
    >();
    for (const r of matched) {
      if (!r.rec) continue;
      const sec = r.rec.stock.sector;
      const prev = map.get(sec) ?? {
        sector: sec,
        count: 0,
        pct: 0,
        quadrant: r.rec.sectorQuadrant,
        score: r.rec.sectorScore,
      };
      prev.count += 1;
      prev.pct = Math.round((prev.count / matched.length) * 100);
      map.set(sec, prev);
    }
    return Array.from(map.values()).sort((a, b) => b.count - a.count);
  }, [activeRows]);

  const filteredSortedRows = useMemo(() => {
    let list = activeRows;
    if (rowFilter === 'buy_only') {
      list = list.filter((r) => r.rec && (r.rec.rating === 'Strong Buy' || r.rec.rating === 'Buy'));
    } else if (rowFilter === 'stage2') {
      list = list.filter((r) => r.rec?.stage === 2);
    } else if (rowFilter === 'risk') {
      list = list.filter((r) => r.riskFlags.length > 0);
    }

    return [...list].sort((a, b) => {
      if (a.known !== b.known) return a.known ? -1 : 1;
      if (!a.rec || !b.rec) return a.ticker.localeCompare(b.ticker);
      if (sortBy === 'matrix') return b.rec.matrixScorePct - a.rec.matrixScorePct;
      if (sortBy === 'rs') return b.rec.rsRating - a.rec.rsRating;
      if (sortBy === 'change1d') return b.rec.stock.dailyChangePct - a.rec.stock.dailyChangePct;
      if (sortBy === 'eps') return b.rec.qtrEpsYoY - a.rec.qtrEpsYoY;
      return b.rec.compositeScore - a.rec.compositeScore;
    });
  }, [activeRows, rowFilter, sortBy]);

  const parsedCsvTickers = useMemo(() => parseCommaSeparatedTickers(csvInput), [csvInput]);

  const searchSuggestions = useMemo(() => {
    const q = singleSearch.trim().toUpperCase();
    if (!q) return [];
    return INDIAN_STOCKS.filter(
      (s) =>
        s.ticker.includes(q) || s.name.toUpperCase().includes(q) || s.sector.toUpperCase().includes(q)
    ).slice(0, 8);
  }, [singleSearch]);

  const handleCreateWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (customWatchlists.length >= MAX_WATCHLISTS) {
      notify(`Maximum ${MAX_WATCHLISTS} watchlists reached. Delete or edit an existing slot.`);
      return;
    }
    const usedSlots = new Set(customWatchlists.map((w) => w.slotIndex));
    let nextSlot = 1;
    for (let s = 1; s <= MAX_WATCHLISTS; s++) {
      if (!usedSlots.has(s)) {
        nextSlot = s;
        break;
      }
    }
    const created = await saveCustomWatchlist({
      name: newWlName.trim() || `Watchlist ${nextSlot}`,
      slotIndex: nextSlot,
      notes: newWlNotes.trim(),
      tickers: [],
    });
    if (created) {
      setSelectedId(created.id);
      setNewWlName('');
      setNewWlNotes('');
      setShowNewForm(false);
      setShowImportDrawer(true);
      notify(`Created "${created.name}" (Slot ${created.slotIndex}/${MAX_WATCHLISTS}). Import or add tickers below.`);
    }
  };

  const handleSaveMeta = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWatchlist) return;
    const saved = await saveCustomWatchlist({
      ...activeWatchlist,
      name: editName.trim() || activeWatchlist.name,
      notes: editNotes.trim(),
    });
    if (saved) {
      setEditingMeta(false);
      notify(`Updated "${saved.name}".`);
    }
  };

  const handleDeleteWatchlist = async (wl: CustomWatchlist) => {
    await deleteCustomWatchlist(wl.id);
    const remaining = customWatchlists.filter((item) => item.id !== wl.id);
    if (remaining.length > 0 && selectedId === wl.id) {
      setSelectedId(remaining[0].id);
    }
    notify(`Deleted watchlist "${wl.name}".`);
  };

  const handleApplyTickers = async (incomingTickers: string[], target: 'current' | 'new') => {
    if (incomingTickers.length === 0) return;
    if (target === 'new') {
      if (customWatchlists.length >= MAX_WATCHLISTS) {
        notify(`Maximum ${MAX_WATCHLISTS} watchlists reached. Merge into an existing watchlist instead.`);
        return;
      }
      const usedSlots = new Set(customWatchlists.map((w) => w.slotIndex));
      let nextSlot = 1;
      for (let s = 1; s <= MAX_WATCHLISTS; s++) {
        if (!usedSlots.has(s)) {
          nextSlot = s;
          break;
        }
      }
      const baseName = excelFileName
        ? excelFileName.replace(/\.(xlsx|xls|csv)$/i, '').slice(0, 42)
        : `Imported Watchlist ${nextSlot}`;
      const created = await saveCustomWatchlist({
        name: baseName,
        slotIndex: nextSlot,
        notes: `Imported ${incomingTickers.length} tickers via ${excelFileName ? 'Excel/CSV' : 'comma-separated list'}.`,
        tickers: incomingTickers.slice(0, 60),
      });
      if (created) {
        setSelectedId(created.id);
        setExcelTickers([]);
        setExcelFileName('');
        if (fileInputRef.current) fileInputRef.current.value = '';
        notify(`Created "${created.name}" with ${created.tickers.length} tickers.`);
      }
      return;
    }

    if (!activeWatchlist) {
      const created = await saveCustomWatchlist({
        name: 'Watchlist 1',
        slotIndex: 1,
        notes: '',
        tickers: incomingTickers.slice(0, 60),
      });
      if (created) {
        setSelectedId(created.id);
        notify(`Created "${created.name}" with ${created.tickers.length} tickers.`);
      }
      return;
    }

    const nextTickers =
      importMode === 'replace'
        ? incomingTickers.slice(0, 60)
        : Array.from(new Set([...incomingTickers, ...activeWatchlist.tickers])).slice(0, 60);

    await saveCustomWatchlist({
      ...activeWatchlist,
      tickers: nextTickers,
    });
    setExcelTickers([]);
    setExcelFileName('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    notify(
      `${importMode === 'replace' ? 'Replaced' : 'Merged'} ${incomingTickers.length} ticker(s) in "${activeWatchlist.name}" (${nextTickers.length} total).`
    );
  };

  const handleExcelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setExcelError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    setExcelFileName(file.name);
    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: 'array' });
      const firstSheet = workbook.SheetNames[0];
      if (!firstSheet) {
        setExcelError('The uploaded file contains no readable sheets.');
        return;
      }
      const sheet = workbook.Sheets[firstSheet];
      const jsonRows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: '' });

      let extracted: string[] = [];
      if (jsonRows.length > 0) {
        const keys = Object.keys(jsonRows[0]);
        const tickerCol = findTickerColumn(keys);
        if (tickerCol) {
          extracted = jsonRows
            .map((row) => normalizeTickerToken(String(row[tickerCol] ?? '')))
            .filter((t) => t.length >= 1 && /[A-Z]/.test(t));
        }
      }

      // Fallback: headerless single-column / comma-separated rows
      if (extracted.length === 0) {
        const rawMatrix = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' });
        for (const row of rawMatrix) {
          for (const cell of row) {
            const parts = parseCommaSeparatedTickers(String(cell ?? ''));
            extracted.push(...parts);
          }
        }
      }

      const unique = Array.from(new Set(extracted)).slice(0, 60);
      if (unique.length === 0) {
        setExcelError('No valid NSE/BSE ticker symbols found. Ensure a Ticker or Symbol column exists.');
        setExcelTickers([]);
        return;
      }
      setExcelTickers(unique);
    } catch (err) {
      setExcelError(err instanceof Error ? err.message : 'Failed to parse Excel / CSV file.');
      setExcelTickers([]);
    }
  };

  const handleAddSingleTicker = async (ticker: string) => {
    const clean = normalizeTickerToken(ticker);
    if (!clean) return;
    if (!activeWatchlist) {
      const created = await saveCustomWatchlist({
        name: 'Watchlist 1',
        slotIndex: 1,
        notes: '',
        tickers: [clean],
      });
      if (created) setSelectedId(created.id);
    } else {
      if (activeWatchlist.tickers.includes(clean)) {
        notify(`${clean} is already in "${activeWatchlist.name}".`);
        return;
      }
      await saveCustomWatchlist({
        ...activeWatchlist,
        tickers: [clean, ...activeWatchlist.tickers].slice(0, 60),
      });
    }
    setSingleSearch('');
    notify(`Added ${clean} to "${activeWatchlist?.name || 'Watchlist 1'}".`);
  };

  const handleRemoveTicker = async (ticker: string) => {
    if (!activeWatchlist) return;
    await saveCustomWatchlist({
      ...activeWatchlist,
      tickers: activeWatchlist.tickers.filter((t) => t !== ticker),
    });
    notify(`Removed ${ticker} from "${activeWatchlist.name}".`);
  };

  const handleSyncFromMainWatchlist = async () => {
    if (!activeWatchlist) return;
    const merged = Array.from(new Set([...mainWatchlist, ...activeWatchlist.tickers])).slice(0, 60);
    await saveCustomWatchlist({
      ...activeWatchlist,
      tickers: merged,
    });
    notify(`Synced ${mainWatchlist.length} main NSE watchlist tickers into "${activeWatchlist.name}".`);
  };

  const handleExportActiveCsv = () => {
    if (!activeWatchlist || activeRows.length === 0) return;
    const headers = [
      'Watchlist',
      'Ticker',
      'Sector',
      'SectorQuadrant',
      'Call',
      'CompositeScore_100',
      'TechTrend_60',
      'Setup_15',
      'Funda_25',
      'MatrixConsensus',
      'MatrixScore_100',
      'MatrixSignals',
      'LTP_INR',
      'Change1D_Pct',
      'Stage',
      'SEPA_Passed',
      'RSRating',
      'RSI14',
      'PrimarySetup',
      'QtrEpsYoY_Pct',
      'ROE_Pct',
      'EntryTrigger_INR',
      'StopLoss_INR',
      'R2_INR',
      'RiskFlags',
    ];
    const rows = activeRows.map((row) => [
      `"${activeWatchlist.name.replace(/"/g, '""')}"`,
      row.ticker,
      `"${row.rec?.stock.sector ?? 'External'}"`,
      row.rec?.sectorQuadrant ?? '',
      row.rec?.rating ?? '',
      row.rec?.compositeScore ?? '',
      row.rec?.techScore ?? '',
      row.rec?.setupScore ?? '',
      row.rec?.fundaScore ?? '',
      row.rec?.technicalConsensus ?? '',
      row.rec?.matrixScorePct ?? '',
      row.rec ? `${row.rec.bullishSignals}/${row.rec.totalSignals}B` : '',
      row.rec ? row.rec.stock.latestClose.toFixed(2) : '',
      row.rec ? row.rec.stock.dailyChangePct.toFixed(2) : '',
      row.rec?.stage ?? '',
      row.rec ? `${row.rec.templatePassed}/8` : '',
      row.rec?.rsRating ?? '',
      row.rsi14 !== null ? row.rsi14.toFixed(1) : '',
      `"${row.rec?.primarySetup ?? ''}"`,
      row.rec ? row.rec.qtrEpsYoY.toFixed(1) : '',
      row.rec ? row.rec.roePct.toFixed(1) : '',
      row.rec ? row.rec.entryTriggerInr.toFixed(2) : '',
      row.rec ? row.rec.stopLossInr.toFixed(2) : '',
      row.rec ? row.rec.r2Inr.toFixed(2) : '',
      `"${row.riskFlags.join('; ')}"`,
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `watchlist-${activeWatchlist.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSetRowAlert = async (row: EnrichedWatchlistRow) => {
    if (!row.rec) return;
    await addAlert({
      ticker: row.ticker,
      category: 'vcp_pivot',
      title: `${row.ticker} (${activeWatchlist?.name || 'Watchlist'}) — ${row.rec.rating} ${row.rec.compositeScore}/100`,
      message: `Matrix ${row.rec.technicalConsensus} ${row.rec.matrixScorePct}/100 · Entry ${formatINR(row.rec.entryTriggerInr)} · Stop ${formatINR(row.rec.stopLossInr)} (-${row.rec.stopRiskPct.toFixed(1)}%)`,
    });
    setAlertedTickers((prev) => ({ ...prev, [row.ticker]: true }));
    notify(`Alert created for ${row.ticker}.`);
  };

  return (
    <div className="space-y-6">
      {toast && (
        <div className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
          <Check className="w-4 h-4 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      {/* 1. 5-WATCHLIST SLOT MANAGER & ACTION BAR */}
      <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-500 shrink-0" />
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Multi-Watchlist Analysis Desk ({customWatchlists.length}/{MAX_WATCHLISTS} Watchlists)
              </h2>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              Create, import (Excel/CSV or TradingView comma-separated tickers), and compare up to 5 independent NSE watchlists using 60/15/25 Call Score, Indicators Matrix Summary (16 Signals), SEPA Stage 2 breadth &amp; exit risk flags.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setShowImportDrawer((v) => !v)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors whitespace-nowrap ${
                showImportDrawer
                  ? 'border-blue-600 bg-blue-600/10 text-blue-700 dark:text-blue-300'
                  : 'border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              Import Excel / Tickers
            </button>

            <button
              type="button"
              onClick={() => setShowNewForm((v) => !v)}
              disabled={customWatchlists.length >= MAX_WATCHLISTS}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 whitespace-nowrap"
              title={
                customWatchlists.length >= MAX_WATCHLISTS
                  ? `Limit of ${MAX_WATCHLISTS} watchlists reached`
                  : 'Create a new named watchlist slot'
              }
            >
              <FolderPlus className="w-3.5 h-3.5" />
              New Watchlist ({customWatchlists.length}/{MAX_WATCHLISTS})
            </button>
          </div>
        </div>

        {/* Watchlist Slot Tabs */}
        <div className="px-5 py-3 bg-slate-50/70 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {customWatchlists.map((wl) => {
              const isSelected = activeWatchlist?.id === wl.id;
              const stats = allWatchlistStats.find((s) => s.watchlist.id === wl.id);
              return (
                <button
                  key={wl.id}
                  type="button"
                  onClick={() => {
                    setSelectedId(wl.id);
                    setEditingMeta(false);
                  }}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-colors whitespace-nowrap ${
                    isSelected
                      ? 'border-blue-600 bg-blue-600 text-white font-semibold'
                      : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:border-blue-500/50'
                  }`}
                >
                  <span className="font-mono text-[10px] opacity-75">#{wl.slotIndex}</span>
                  <span>{wl.name}</span>
                  <span
                    className={`font-mono text-[10px] tabular-nums ${
                      isSelected ? 'text-blue-100' : 'text-slate-500'
                    }`}
                  >
                    ({wl.tickers.length})
                  </span>
                  {stats && stats.matchedCount > 0 && (
                    <span
                      className={`font-mono text-[10px] tabular-nums font-semibold ${
                        isSelected
                          ? 'text-emerald-200'
                          : stats.avgCompositeScore >= 72
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-slate-500'
                      }`}
                    >
                      {stats.avgCompositeScore}pt
                    </span>
                  )}
                </button>
              );
            })}
            {customWatchlists.length === 0 && (
              <span className="text-xs text-slate-500">
                No watchlists yet. Click &ldquo;New Watchlist&rdquo; or &ldquo;Import Excel / Tickers&rdquo; to begin.
              </span>
            )}
          </div>

          {activeWatchlist && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <button
                type="button"
                onClick={handleSyncFromMainWatchlist}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-amber-500/50 whitespace-nowrap"
                title="Merge your starred Main NSE Watchlist tickers into this watchlist"
              >
                <RefreshCw className="w-3 h-3 text-amber-500" />
                Sync Main ({mainWatchlist.length})
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditName(activeWatchlist.name);
                  setEditNotes(activeWatchlist.notes);
                  setEditingMeta((v) => !v);
                }}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-blue-500/50 whitespace-nowrap"
              >
                <Edit3 className="w-3 h-3" />
                Rename
              </button>
              <button
                type="button"
                onClick={handleExportActiveCsv}
                disabled={activeRows.length === 0}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-blue-500/50 disabled:opacity-40 whitespace-nowrap"
              >
                <Download className="w-3 h-3" />
                CSV
              </button>
              <button
                type="button"
                onClick={() => void handleDeleteWatchlist(activeWatchlist)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium rounded-md border border-red-500/30 bg-red-500/5 text-red-600 dark:text-red-400 hover:bg-red-500/10 whitespace-nowrap"
                title={`Delete "${activeWatchlist.name}"`}
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          )}
        </div>

        {/* Create New Watchlist Inline Form */}
        {showNewForm && (
          <form
            onSubmit={(e) => void handleCreateWatchlist(e)}
            className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 bg-blue-50/40 dark:bg-blue-950/20 flex flex-wrap items-end gap-3 text-xs"
          >
            <div className="flex-1 min-w-[180px]">
              <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                New Watchlist Name (Slot {customWatchlists.length + 1}/{MAX_WATCHLISTS})
              </label>
              <input
                type="text"
                maxLength={48}
                required
                value={newWlName}
                onChange={(e) => setNewWlName(e.target.value)}
                placeholder="e.g. Q3 Earnings Breakouts, PSU Defence Leaders"
                className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>
            <div className="flex-[1.5] min-w-[220px]">
              <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                Thesis / Notes (optional)
              </label>
              <input
                type="text"
                maxLength={240}
                value={newWlNotes}
                onChange={(e) => setNewWlNotes(e.target.value)}
                placeholder="e.g. Stage 2 VCP setups in Leading NSE sectors"
                className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="px-3.5 py-1.5 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700"
              >
                Create Slot
              </button>
              <button
                type="button"
                onClick={() => setShowNewForm(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Rename Active Watchlist Form */}
        {editingMeta && activeWatchlist && (
          <form
            onSubmit={(e) => void handleSaveMeta(e)}
            className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/70 flex flex-wrap items-end gap-3 text-xs"
          >
            <div className="flex-1 min-w-[180px]">
              <label className="block text-[11px] font-medium text-slate-500 mb-1">Watchlist Name</label>
              <input
                type="text"
                maxLength={48}
                required
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>
            <div className="flex-[1.5] min-w-[220px]">
              <label className="block text-[11px] font-medium text-slate-500 mb-1">Notes</label>
              <input
                type="text"
                maxLength={240}
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                type="submit"
                className="px-3.5 py-1.5 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => setEditingMeta(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Direct Import Drawer: Comma-Separated Tickers | Excel/CSV Upload | Single Search */}
        {showImportDrawer && (
          <div className="p-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setImportSubTab('tickers')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                    importSubTab === 'tickers'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-700 dark:text-blue-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <ListPlus className="w-3.5 h-3.5" />
                  1. Comma-Separated Tickers
                </button>
                <button
                  type="button"
                  onClick={() => setImportSubTab('excel')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                    importSubTab === 'excel'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-700 dark:text-blue-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  2. Excel / CSV Upload (.xlsx, .xls, .csv)
                </button>
                <button
                  type="button"
                  onClick={() => setImportSubTab('single')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                    importSubTab === 'single'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-700 dark:text-blue-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <Search className="w-3.5 h-3.5" />
                  3. Quick Add Single NSE Stock
                </button>
              </div>

              {importSubTab !== 'single' && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500">Target Mode:</span>
                  <div className="inline-flex p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <button
                      type="button"
                      onClick={() => setImportMode('merge')}
                      className={`px-2.5 py-1 rounded-md font-medium ${
                        importMode === 'merge'
                          ? 'bg-blue-600 text-white'
                          : 'text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      Merge
                    </button>
                    <button
                      type="button"
                      onClick={() => setImportMode('replace')}
                      className={`px-2.5 py-1 rounded-md font-medium ${
                        importMode === 'replace'
                          ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900'
                          : 'text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      Replace
                    </button>
                  </div>
                </div>
              )}
            </div>

            {importSubTab === 'tickers' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Paste Comma-Separated Tickers (TradingView format supported, e.g.{' '}
                    <span className="font-mono">NSE:RELIANCE, NSE:TCS, NSE:HAL</span>)
                  </label>
                  <textarea
                    rows={2}
                    value={csvInput}
                    onChange={(e) => setCsvInput(e.target.value)}
                    placeholder="NSE:RELIANCE, NSE:TCS, NSE:HAL, NSE:TRENT, NSE:BEL"
                    className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Detected <strong className="font-mono">{parsedCsvTickers.length}</strong> unique symbols ·{' '}
                    <strong className="font-mono text-emerald-600 dark:text-emerald-400">
                      {parsedCsvTickers.filter((t) => Boolean(STOCK_BY_TICKER[t])).length}
                    </strong>{' '}
                    matched in live NSE universe (max 60 per watchlist).
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  {customWatchlists.length < MAX_WATCHLISTS && (
                    <button
                      type="button"
                      onClick={() => void handleApplyTickers(parsedCsvTickers, 'new')}
                      disabled={parsedCsvTickers.length === 0}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40"
                    >
                      <FolderPlus className="w-3.5 h-3.5 text-blue-500" />
                      Save as New Watchlist ({customWatchlists.length + 1}/{MAX_WATCHLISTS})
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => void handleApplyTickers(parsedCsvTickers, 'current')}
                    disabled={parsedCsvTickers.length === 0}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40"
                  >
                    <Check className="w-3.5 h-3.5" />
                    {importMode === 'replace' ? 'Replace' : 'Merge into'} &ldquo;{activeWatchlist?.name || 'Watchlist 1'}&rdquo; ({parsedCsvTickers.length})
                  </button>
                </div>
              </div>
            )}

            {importSubTab === 'excel' && (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-slate-600 dark:text-slate-400">
                    Upload any <span className="font-mono">.xlsx</span>, <span className="font-mono">.xls</span>, or{' '}
                    <span className="font-mono">.csv</span> file with a{' '}
                    <span className="font-mono text-slate-900 dark:text-slate-100">Ticker / Symbol / Stock</span> column
                    (or a plain single-column ticker list).
                  </div>
                  <label className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 cursor-pointer whitespace-nowrap">
                    <FileSpreadsheet className="w-3.5 h-3.5" />
                    Choose Excel / CSV File
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".xlsx,.xls,.csv"
                      onChange={(e) => void handleExcelUpload(e)}
                      className="hidden"
                    />
                  </label>
                </div>

                {excelError && (
                  <div className="text-xs text-red-600 dark:text-red-400 font-medium">{excelError}</div>
                )}

                {excelTickers.length > 0 && (
                  <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span>
                        File: <strong className="font-mono">{excelFileName}</strong> ·{' '}
                        <strong className="font-mono">{excelTickers.length}</strong> unique symbols (
                        <strong className="font-mono text-emerald-600 dark:text-emerald-400">
                          {excelTickers.filter((t) => Boolean(STOCK_BY_TICKER[t])).length}
                        </strong>{' '}
                        live NSE matches)
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          setExcelTickers([]);
                          setExcelFileName('');
                          if (fileInputRef.current) fileInputRef.current.value = '';
                        }}
                        className="text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
                      >
                        Clear
                      </button>
                    </div>
                    <div className="font-mono text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                      {excelTickers.slice(0, 24).join(', ')}
                      {excelTickers.length > 24 ? ` … +${excelTickers.length - 24} more` : ''}
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      {customWatchlists.length < MAX_WATCHLISTS && (
                        <button
                          type="button"
                          onClick={() => void handleApplyTickers(excelTickers, 'new')}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200"
                        >
                          <FolderPlus className="w-3.5 h-3.5 text-blue-500" />
                          Create New Watchlist ({customWatchlists.length + 1}/{MAX_WATCHLISTS})
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => void handleApplyTickers(excelTickers, 'current')}
                        className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700"
                      >
                        <Check className="w-3.5 h-3.5" />
                        {importMode === 'replace' ? 'Replace' : 'Merge into'} &ldquo;{activeWatchlist?.name || 'Watchlist 1'}&rdquo;
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {importSubTab === 'single' && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 max-w-md">
                  <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={singleSearch}
                      onChange={(e) => setSingleSearch(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && singleSearch.trim()) {
                          e.preventDefault();
                          void handleAddSingleTicker(singleSearch);
                        }
                      }}
                      placeholder="Type NSE ticker or company (e.g. TRENT, HAL, DIXON)…"
                      className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleAddSingleTicker(singleSearch)}
                    disabled={!singleSearch.trim()}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add
                  </button>
                </div>
                {searchSuggestions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {searchSuggestions.map((s) => (
                      <button
                        key={s.ticker}
                        type="button"
                        onClick={() => void handleAddSingleTicker(s.ticker)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-blue-500 text-slate-800 dark:text-slate-200"
                      >
                        <span className="font-mono font-bold">{s.ticker}</span>
                        <span className="text-slate-500">{s.sector}</span>
                        <Plus className="w-3 h-3 text-blue-500" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 2. SIDE-BY-SIDE COMPARISON TABLE ACROSS ALL WATCHLISTS (UP TO 5) */}
        {allWatchlistStats.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-50/80 dark:bg-slate-900/70 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                <tr>
                  <th className="py-2 pl-5 pr-3">Watchlist Slot (Compare All)</th>
                  <th className="py-2 px-3 text-right">Stocks</th>
                  <th className="py-2 px-3 text-right">Avg Call Score</th>
                  <th className="py-2 px-3 text-right">Avg Indicators Matrix</th>
                  <th className="py-2 px-3 text-right">Strong Buy / Buy</th>
                  <th className="py-2 px-3 text-right">Stage 2 Breadth</th>
                  <th className="py-2 px-3 text-right">Avg RS</th>
                  <th className="py-2 px-3 text-right">1D Avg</th>
                  <th className="py-2 px-3">Top Sector / Quadrant</th>
                  <th className="py-2 pl-3 pr-5 text-right">Exit Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono tabular-nums">
                {allWatchlistStats.map((st) => {
                  const isActive = activeWatchlist?.id === st.watchlist.id;
                  return (
                    <tr
                      key={st.watchlist.id}
                      onClick={() => setSelectedId(st.watchlist.id)}
                      className={`cursor-pointer transition-colors ${
                        isActive
                          ? 'bg-blue-50/60 dark:bg-blue-950/25'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <td className="py-2.5 pl-5 pr-3 font-sans">
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isActive ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
                            }`}
                          />
                          <span className="font-semibold text-slate-900 dark:text-slate-100">
                            #{st.watchlist.slotIndex} {st.watchlist.name}
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-700 dark:text-slate-300">
                        {st.matchedCount}
                        {st.unmatchedCount > 0 && (
                          <span className="text-[10px] text-amber-500"> (+{st.unmatchedCount})</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold text-slate-900 dark:text-slate-100">
                        {st.matchedCount > 0 ? `${st.avgCompositeScore}/100` : '—'}
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right font-semibold ${
                          st.avgMatrixPct >= 65
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : st.avgMatrixPct >= 50
                            ? 'text-blue-600 dark:text-blue-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {st.matchedCount > 0 ? `${st.avgMatrixPct}/100` : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                          {st.strongBuyCount}
                        </span>
                        <span className="text-slate-400"> / </span>
                        <span className="text-blue-600 dark:text-blue-400 font-semibold">
                          {st.buyCount}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-800 dark:text-slate-200">
                        {st.matchedCount > 0 ? `${st.stage2Count}/${st.matchedCount} (${st.stage2Pct}%)` : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-800 dark:text-slate-200">
                        {st.matchedCount > 0 ? st.avgRs : '—'}
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right font-semibold ${
                          st.avgChange1D >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {st.matchedCount > 0 ? formatPct(st.avgChange1D) : '—'}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-slate-700 dark:text-slate-300">
                        {st.topSector}
                        {st.topSectorQuadrant && (
                          <span
                            className={`ml-1.5 text-[10px] font-semibold ${
                              st.topSectorQuadrant === 'Leading'
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : st.topSectorQuadrant === 'Improving'
                                ? 'text-blue-600 dark:text-blue-400'
                                : st.topSectorQuadrant === 'Weakening'
                                ? 'text-amber-600 dark:text-amber-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            · {st.topSectorQuadrant}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pl-3 pr-5 text-right">
                        {st.riskCount > 0 ? (
                          <span className="text-red-600 dark:text-red-400 font-semibold">
                            {st.riskCount} flag{st.riskCount > 1 ? 's' : ''}
                          </span>
                        ) : (
                          <span className="text-emerald-600 dark:text-emerald-400">Clean</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 3. ACTIVE WATCHLIST DEEP ANALYTICS */}
      {activeWatchlist && activeStats && (
        <>
          {/* Active Watchlist 6-Card KPI Strip */}
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
              <div className="text-[11px] text-slate-500">Active Watchlist</div>
              <div className="text-base font-bold text-slate-900 dark:text-slate-100 mt-1 truncate">
                {activeWatchlist.name}
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                {activeStats.matchedCount} NSE live{activeStats.unmatchedCount > 0 ? ` · ${activeStats.unmatchedCount} ext` : ''}
              </div>
            </div>

            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
              <div className="text-[11px] text-slate-500">Avg Call / Score</div>
              <div className="text-lg font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
                {activeStats.avgCompositeScore}/100
              </div>
              <div className="text-[11px] text-slate-500">60 Tech · 15 Setup · 25 Funda</div>
            </div>

            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
              <div className="text-[11px] text-slate-500">Avg Indicators Matrix</div>
              <div className="text-lg font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 mt-1">
                {activeStats.avgMatrixPct}/100
              </div>
              <div className="text-[11px] text-slate-500">16-Indicator Consensus</div>
            </div>

            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
              <div className="text-[11px] text-slate-500">Stage 2 Uptrend</div>
              <div className="text-lg font-bold font-mono tabular-nums text-blue-600 dark:text-blue-400 mt-1">
                {activeStats.stage2Pct}%
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                {activeStats.stage2Count}/{activeStats.matchedCount} · Avg RS {activeStats.avgRs}
              </div>
            </div>

            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
              <div className="text-[11px] text-slate-500">Strong Buy / Buy</div>
              <div className="text-lg font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 mt-1">
                {activeStats.strongBuyCount} / {activeStats.buyCount}
              </div>
              <div className="text-[11px] font-mono text-slate-500">
                1D Avg {formatPct(activeStats.avgChange1D)}
              </div>
            </div>

            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-3.5">
              <div className="text-[11px] text-slate-500">Breakdown / Risk Flags</div>
              <div
                className={`text-lg font-bold font-mono tabular-nums mt-1 ${
                  activeStats.riskCount > 0
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-emerald-600 dark:text-emerald-400'
                }`}
              >
                {activeStats.riskCount} / {activeStats.matchedCount}
              </div>
              <div className="text-[11px] text-slate-500">200 SMA · ST · DC(20)</div>
            </div>
          </div>

          {/* Sector Exposure & NSE Quadrant Strip */}
          {activeSectorMix.length > 0 && (
            <div className="px-5 py-3 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                Sector Exposure &amp; Quadrant:
              </span>
              {activeSectorMix.slice(0, 6).map((sec) => (
                <span key={sec.sector} className="inline-flex items-center gap-1.5 font-mono tabular-nums">
                  <span className="font-sans text-slate-700 dark:text-slate-300">{sec.sector}</span>
                  <strong className="text-slate-900 dark:text-slate-100">{sec.pct}%</strong>
                  {sec.quadrant && (
                    <span
                      className={`font-sans text-[10px] font-semibold ${
                        sec.quadrant === 'Leading'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : sec.quadrant === 'Improving'
                          ? 'text-blue-600 dark:text-blue-400'
                          : sec.quadrant === 'Weakening'
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      ({sec.quadrant}
                      {sec.score !== undefined ? ` ${sec.score}` : ''})
                    </span>
                  )}
                </span>
              ))}
            </div>
          )}

          {/* Full Institutional Watchlist Analysis Table */}
          <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {activeWatchlist.name} — Stock-by-Stock TechnoFunda &amp; Risk Breakdown
                </h3>
                {activeWatchlist.notes && (
                  <p className="text-[11px] text-slate-500 mt-0.5">{activeWatchlist.notes}</p>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs">
                <div className="inline-flex items-center p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-[11px]">
                  {(
                    [
                      { id: 'all', label: `All (${activeRows.length})` },
                      {
                        id: 'buy_only',
                        label: `Buy/Strong Buy (${activeStats.strongBuyCount + activeStats.buyCount})`,
                      },
                      { id: 'stage2', label: `Stage 2 (${activeStats.stage2Count})` },
                      { id: 'risk', label: `Exit Risk (${activeStats.riskCount})` },
                    ] as { id: RowFilter; label: string }[]
                  ).map((f) => (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setRowFilter(f.id)}
                      className={`px-2.5 py-1 rounded-md transition-colors whitespace-nowrap ${
                        rowFilter === f.id
                          ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                          : 'text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>

                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortKey)}
                  aria-label="Sort watchlist stocks"
                  className="px-2.5 py-1 text-[11px] font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-200"
                >
                  <option value="score">Sort: Call Score</option>
                  <option value="matrix">Sort: Indicators Matrix Summary</option>
                  <option value="rs">Sort: RS Rating</option>
                  <option value="change1d">Sort: 1D Return</option>
                  <option value="eps">Sort: Qtr EPS YoY</option>
                </select>
              </div>
            </div>

            {filteredSortedRows.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">
                {activeRows.length === 0
                  ? 'This watchlist is empty. Click "Import Excel / Tickers" above to add comma-separated tickers or upload an Excel/CSV file.'
                  : 'No stocks in this watchlist match the selected filter.'}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                    <tr>
                      <th className="py-2.5 pl-5 pr-3">Stock &amp; Sector</th>
                      <th className="py-2.5 px-3">Call / Score &amp; Matrix</th>
                      <th className="py-2.5 px-3 text-right">LTP / 1D</th>
                      <th className="py-2.5 px-3">SEPA &amp; Setup</th>
                      <th className="py-2.5 px-3">Trend &amp; Risk Signals</th>
                      <th className="py-2.5 px-3 text-right">Growth &amp; ROE</th>
                      <th className="py-2.5 px-3 text-right">Entry / Stop / 2R</th>
                      <th className="py-2.5 pl-2 pr-5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                    {filteredSortedRows.map((row) => {
                      const rec = row.rec;
                      const inMain = mainWatchlist.includes(row.ticker);
                      const alerted = Boolean(alertedTickers[row.ticker]);

                      if (!rec) {
                        return (
                          <tr
                            key={row.ticker}
                            onClick={() => onInspectStock(row.ticker)}
                            className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer"
                          >
                            <td className="py-3 pl-5 pr-3 font-mono font-bold text-slate-900 dark:text-slate-100">
                              {row.ticker}
                              <div className="font-sans text-[11px] font-normal text-amber-600 dark:text-amber-400">
                                External NSE/BSE — click to open live on-demand chart
                              </div>
                            </td>
                            <td colSpan={6} className="py-3 px-3 text-[11px] text-slate-500">
                              Not in pre-loaded 1,102-stock NSE index cache; full live Yahoo Finance chart &amp; Indicators Matrix Summary load on click.
                            </td>
                            <td
                              className="py-3 pl-2 pr-5 text-right whitespace-nowrap"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                type="button"
                                onClick={() => void handleRemoveTicker(row.ticker)}
                                className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-400 hover:text-red-500"
                                title="Remove from watchlist"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        );
                      }

                      const ratingTone =
                        rec.rating === 'Strong Buy'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : rec.rating === 'Buy'
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-amber-600 dark:text-amber-400';

                      const matrixTone =
                        rec.technicalConsensus === 'Strong Buy' || rec.technicalConsensus === 'Buy'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : rec.technicalConsensus === 'Neutral'
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-red-600 dark:text-red-400';

                      return (
                        <tr
                          key={row.ticker}
                          onClick={() => onInspectStock(row.ticker)}
                          className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group"
                        >
                          <td className="py-3 pl-5 pr-3 align-top whitespace-nowrap">
                            <div className="font-mono font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                              {row.ticker}
                            </div>
                            <div className="text-[11px] text-slate-500">
                              {rec.stock.sector} · {rec.stock.capBucket}
                            </div>
                          </td>

                          <td
                            className="py-3 px-3 align-top whitespace-nowrap"
                            title={`Call / Score (${rec.compositeScore}/100): Technical & Trend ${rec.techScore}/60 (incl. Matrix ${rec.matrixScore}/20) · Setup ${rec.setupScore}/15 · Fundamentals ${rec.fundaScore}/25`}
                          >
                            <div className="flex items-baseline gap-1.5">
                              <span className={`font-bold ${ratingTone}`}>{rec.rating}</span>
                              <span className="font-mono tabular-nums text-[11px] font-semibold text-slate-900 dark:text-slate-100">
                                {rec.compositeScore}/100
                              </span>
                            </div>
                            <div className="font-mono tabular-nums text-[10px] text-slate-500 mt-0.5">
                              T{rec.techScore} · S{rec.setupScore} · F{rec.fundaScore}
                            </div>
                            <div className={`font-mono tabular-nums text-[10px] font-medium mt-0.5 ${matrixTone}`}>
                              Matrix: {rec.technicalConsensus} · {rec.matrixScorePct}% ({rec.bullishSignals}/{rec.totalSignals}B)
                            </div>
                          </td>

                          <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                            <div className="font-semibold text-slate-900 dark:text-slate-100">
                              {formatINR(rec.stock.latestClose)}
                            </div>
                            <div
                              className={`text-[11px] font-semibold mt-0.5 ${
                                rec.stock.dailyChangePct >= 0
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-red-600 dark:text-red-400'
                              }`}
                            >
                              {formatPct(rec.stock.dailyChangePct)}
                            </div>
                          </td>

                          <td className="py-3 px-3 font-mono tabular-nums align-top whitespace-nowrap">
                            <div className="font-semibold text-slate-900 dark:text-slate-100">
                              S{rec.stage} · {rec.templatePassed}/8 · RS {rec.rsRating}
                            </div>
                            <div className="font-sans text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5">
                              {rec.primarySetup}
                            </div>
                            {rec.isExtended && (
                              <div className="font-sans text-[10px] text-amber-600 dark:text-amber-400">
                                Extended ({rec.distFrom50SmaAtrs.toFixed(1)} ATR)
                              </div>
                            )}
                          </td>

                          <td className="py-3 px-3 align-top whitespace-nowrap">
                            <div className="font-mono text-[11px] tabular-nums flex items-center gap-2">
                              <span
                                className={
                                  row.sma200Signal === 'Bullish'
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : 'text-red-600 dark:text-red-400 font-semibold'
                                }
                              >
                                200D {row.sma200Signal === 'Bullish' ? '↑' : '↓'}
                              </span>
                              <span
                                className={
                                  row.stSignal === 'Bullish'
                                    ? 'text-emerald-600 dark:text-emerald-400'
                                    : 'text-red-600 dark:text-red-400 font-semibold'
                                }
                              >
                                ST {row.stSignal === 'Bullish' ? 'BUY' : 'SELL'}
                              </span>
                              <span className="text-slate-600 dark:text-slate-400">
                                RSI {row.rsi14 !== null ? row.rsi14.toFixed(0) : '—'}
                              </span>
                            </div>
                            <div className="text-[10px] mt-0.5">
                              {row.riskFlags.length > 0 ? (
                                <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400 font-medium">
                                  <AlertTriangle className="w-3 h-3 shrink-0" />
                                  {row.riskFlags.slice(0, 2).join(' · ')}
                                </span>
                              ) : (
                                <span className="text-slate-500">
                                  Sector:{' '}
                                  <strong className="text-slate-700 dark:text-slate-300">
                                    {rec.sectorQuadrant || '—'}
                                  </strong>
                                  {rec.sectorScore !== undefined ? ` (${rec.sectorScore})` : ''}
                                </span>
                              )}
                            </div>
                          </td>

                          <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                            <div
                              className={`font-semibold ${
                                rec.qtrEpsYoY >= 0
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-red-600 dark:text-red-400'
                              }`}
                            >
                              EPS {rec.qtrEpsYoY >= 0 ? '+' : ''}
                              {rec.qtrEpsYoY.toFixed(0)}%
                            </div>
                            <div className="text-[11px] text-slate-500 mt-0.5">
                              Rev {rec.qtrRevYoY >= 0 ? '+' : ''}
                              {rec.qtrRevYoY.toFixed(0)}% · ROE {rec.roePct.toFixed(0)}%
                            </div>
                          </td>

                          <td className="py-3 px-3 text-right font-mono tabular-nums align-top whitespace-nowrap">
                            <div className="text-blue-600 dark:text-blue-400 font-semibold">
                              E {formatINR(rec.entryTriggerInr, 0)} · 2R {formatINR(rec.r2Inr, 0)}
                            </div>
                            <div className="text-[10px] text-red-600 dark:text-red-400 mt-0.5">
                              SL {formatINR(rec.stopLossInr, 0)} (-{rec.stopRiskPct.toFixed(1)}%)
                            </div>
                          </td>

                          <td
                            className="py-3 pl-2 pr-5 text-right align-top whitespace-nowrap"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <div className="inline-flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => void toggleWatchlist(row.ticker)}
                                className={`p-1.5 rounded border transition-colors ${
                                  inMain
                                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-500'
                                    : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:text-amber-500'
                                }`}
                                title={inMain ? 'Starred in Main Watchlist' : 'Also star in Main Watchlist'}
                              >
                                <Star className="w-3.5 h-3.5" fill={inMain ? 'currentColor' : 'none'} />
                              </button>
                              <button
                                type="button"
                                onClick={() => void handleSetRowAlert(row)}
                                className={`p-1.5 rounded border transition-colors ${
                                  alerted
                                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500'
                                    : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:text-blue-500'
                                }`}
                                title="Create Entry Alert"
                              >
                                {alerted ? (
                                  <Check className="w-3.5 h-3.5" />
                                ) : (
                                  <BellPlus className="w-3.5 h-3.5" />
                                )}
                              </button>
                              <button
                                type="button"
                                onClick={() => onInspectStock(row.ticker)}
                                className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-blue-500"
                                title={`Open full chart for ${row.ticker}`}
                              >
                                <LineChart className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => void handleRemoveTicker(row.ticker)}
                                className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-400 hover:text-red-500 hover:border-red-500/40"
                                title={`Remove ${row.ticker} from "${activeWatchlist.name}"`}
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
};
