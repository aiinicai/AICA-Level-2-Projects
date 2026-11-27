import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS } from '../data/indianMarketData';

export type SectorHeatmapRange = 'today' | 'week' | 'month';

interface SectorIndexItem {
  code: string;
  label: string;
  yahooSymbol: string;
  appSector: string;
  lastClose: number | null;
  retTodayPct: number | null;
  retWeekPct: number | null;
  retMonthPct: number | null;
  asOfDate: string | null;
  live: boolean;
}

const PSU_BANK_TICKERS = new Set([
  'SBIN',
  'BANKBARODA',
  'PNB',
  'CANBK',
  'UNIONBANK',
  'INDIANB',
  'BANKINDIA',
  'MAHABANK',
  'IOB',
  'UCOBANK',
  'CENTRALBK',
  'PSB',
]);

const BASE_NIFTY_INDICES: Omit<
  SectorIndexItem,
  'lastClose' | 'retTodayPct' | 'retWeekPct' | 'retMonthPct' | 'asOfDate' | 'live'
>[] = [
  { code: 'CNXREALTY', label: 'Realty', yahooSymbol: '^CNXREALTY', appSector: 'Real Estate' },
  { code: 'CNXIT', label: 'IT', yahooSymbol: '^CNXIT', appSector: 'Information Technology' },
  { code: 'CNXMETAL', label: 'Metal', yahooSymbol: '^CNXMETAL', appSector: 'Metals & Mining' },
  { code: 'CNXENERGY', label: 'Energy', yahooSymbol: '^CNXENERGY', appSector: 'Oil, Gas & Energy' },
  { code: 'CNXPHARMA', label: 'Pharma', yahooSymbol: '^CNXPHARMA', appSector: 'Pharma & Healthcare' },
  {
    code: 'CNXINFRA',
    label: 'Infrastructure',
    yahooSymbol: '^CNXINFRA',
    appSector: 'Infrastructure & Construction',
  },
  { code: 'CNXMEDIA', label: 'Media', yahooSymbol: '^CNXMEDIA', appSector: 'Media & Entertainment' },
  {
    code: 'CNXFINANCE',
    label: 'Financial Svcs',
    yahooSymbol: '^CNXFINANCE',
    appSector: 'Financial Services',
  },
  { code: 'BANKNIFTY', label: 'Bank', yahooSymbol: '^NSEBANK', appSector: 'Banking' },
  { code: 'CNXPSUBANK', label: 'PSU Bank', yahooSymbol: '^CNXPSUBANK', appSector: 'Banking' },
  { code: 'CNXAUTO', label: 'Auto', yahooSymbol: '^CNXAUTO', appSector: 'Automobiles & EV' },
  { code: 'CNXFMCG', label: 'FMCG', yahooSymbol: '^CNXFMCG', appSector: 'FMCG & Consumer' },
];

function computeFallbackSectorReturns(
  meta: (typeof BASE_NIFTY_INDICES)[number]
): { today: number; week: number; month: number } {
  const constituents = INDIAN_STOCKS.filter((s) => {
    if (meta.code === 'CNXPSUBANK') return PSU_BANK_TICKERS.has(s.ticker);
    if (meta.code === 'CNXINFRA') {
      return (
        s.sector === 'Infrastructure & Construction' ||
        s.sector === 'Capital Goods & Engineering' ||
        s.sector === 'Cement & Building Materials'
      );
    }
    return s.sector === meta.appSector;
  });

  if (constituents.length === 0) return { today: 0, week: 0, month: 0 };

  let todaySum = 0;
  let weekSum = 0;
  let monthSum = 0;
  let countW = 0;
  let countM = 0;

  for (const s of constituents) {
    todaySum += s.dailyChangePct;
    const bars = s.bars;
    const n = bars.length;
    if (n >= 6) {
      const c0 = bars[n - 1].close;
      const cw = bars[Math.max(0, n - 1 - 5)].close;
      if (cw > 0) {
        weekSum += ((c0 - cw) / cw) * 100;
        countW++;
      }
    }
    if (n >= 22) {
      const c0 = bars[n - 1].close;
      const cm = bars[Math.max(0, n - 1 - 21)].close;
      if (cm > 0) {
        monthSum += ((c0 - cm) / cm) * 100;
        countM++;
      }
    }
  }

  return {
    today: Number((todaySum / constituents.length).toFixed(2)),
    week: countW > 0 ? Number((weekSum / countW).toFixed(2)) : 0,
    month: countM > 0 ? Number((monthSum / countM).toFixed(2)) : 0,
  };
}

interface NiftySectorHeatmapProps {
  onSelectSector?: (appSector: string) => void;
}

export const NiftySectorHeatmap: React.FC<NiftySectorHeatmapProps> = ({ onSelectSector }) => {
  const { theme, marketVersion } = useAppData();
  const isDark = theme === 'dark';

  const [range, setRange] = useState<SectorHeatmapRange>('today');
  const [liveIndices, setLiveIndices] = useState<SectorIndexItem[] | null>(null);
  const [fetchedAtIst, setFetchedAtIst] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchSectorIndices = useCallback(async (force = false) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/market/sector-indices${force ? '?refresh=1' : ''}`);
      if (!res.ok) return;
      const json = (await res.json()) as {
        fetchedAtIst?: string;
        indices?: SectorIndexItem[];
      };
      if (Array.isArray(json.indices) && json.indices.length > 0) {
        setLiveIndices(json.indices);
        setFetchedAtIst(json.fetchedAtIst ?? null);
      }
    } catch {
      // fall back silently to constituent averages
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchSectorIndices(false);
  }, [fetchSectorIndices]);

  const tiles = useMemo(() => {
    void marketVersion;
    const liveMap = new Map((liveIndices || []).map((i) => [i.code, i]));

    const merged = BASE_NIFTY_INDICES.map((meta) => {
      const live = liveMap.get(meta.code);
      const fb = computeFallbackSectorReturns(meta);
      const retToday = live?.live && live.retTodayPct !== null ? live.retTodayPct : fb.today;
      const retWeek = live?.live && live.retWeekPct !== null ? live.retWeekPct : fb.week;
      const retMonth = live?.live && live.retMonthPct !== null ? live.retMonthPct : fb.month;
      const activeRet = range === 'today' ? retToday : range === 'week' ? retWeek : retMonth;

      return {
        ...meta,
        lastClose: live?.lastClose ?? null,
        isLiveIndex: Boolean(live?.live),
        retToday,
        retWeek,
        retMonth,
        activeRet,
      };
    });

    return merged.sort((a, b) => b.activeRet - a.activeRet);
  }, [liveIndices, range, marketVersion]);

  const maxAbs = useMemo(() => {
    const m = Math.max(...tiles.map((t) => Math.abs(t.activeRet)), 1.5);
    return range === 'today' ? Math.max(m, 2.5) : range === 'week' ? Math.max(m, 4.0) : Math.max(m, 7.0);
  }, [tiles, range]);

  const rangeLabel =
    range === 'today' ? 'Today' : range === 'week' ? 'This Week' : 'This Month';

  const getTileStyle = (pct: number): React.CSSProperties => {
    const intensity = Math.min(1, Math.max(0.14, Math.abs(pct) / maxAbs));
    if (pct >= 0) {
      if (isDark) {
        const bgAlpha = 0.14 + intensity * 0.34;
        const borderAlpha = 0.28 + intensity * 0.45;
        return {
          backgroundColor: `rgba(16, 185, 129, ${bgAlpha.toFixed(2)})`,
          borderColor: `rgba(52, 211, 153, ${borderAlpha.toFixed(2)})`,
        };
      }
      // Crisp teal-green scale matching the attached Nifty sector heatmap screenshot
      const bgAlpha = 0.12 + intensity * 0.52;
      const borderAlpha = 0.25 + intensity * 0.55;
      return {
        backgroundColor: `rgba(13, 148, 136, ${bgAlpha.toFixed(2)})`,
        borderColor: `rgba(15, 118, 110, ${borderAlpha.toFixed(2)})`,
      };
    } else {
      if (isDark) {
        const bgAlpha = 0.14 + intensity * 0.34;
        const borderAlpha = 0.28 + intensity * 0.45;
        return {
          backgroundColor: `rgba(239, 68, 68, ${bgAlpha.toFixed(2)})`,
          borderColor: `rgba(248, 113, 113, ${borderAlpha.toFixed(2)})`,
        };
      }
      // Soft rose-red scale matching the attached screenshot
      const bgAlpha = 0.1 + intensity * 0.32;
      const borderAlpha = 0.22 + intensity * 0.48;
      return {
        backgroundColor: `rgba(244, 63, 94, ${bgAlpha.toFixed(2)})`,
        borderColor: `rgba(225, 29, 72, ${borderAlpha.toFixed(2)})`,
      };
    }
  };

  return (
    <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-baseline gap-2">
          <h2 className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Nifty sector heatmap
          </h2>
          <span className="text-sm text-slate-400" aria-hidden="true">
            ·
          </span>
          <span className="text-sm font-medium text-slate-600 dark:text-slate-300">Nifty</span>
          <span className="text-sm text-slate-400" aria-hidden="true">
            ·
          </span>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
            {rangeLabel}
          </span>
          {fetchedAtIst && (
            <span className="text-[11px] font-mono text-slate-400 ml-1">
              ({fetchedAtIst.slice(-8)} IST)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div
            className="inline-flex items-center gap-0.5 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 text-xs"
            role="group"
            aria-label="Nifty sector heatmap timeframe"
          >
            {(
              [
                { id: 'today', label: 'Today' },
                { id: 'week', label: 'This Week' },
                { id: 'month', label: 'This Month' },
              ] as const
            ).map((opt) => (
              <button
                key={opt.id}
                onClick={() => setRange(opt.id)}
                className={`px-3 py-1 rounded-md font-medium transition-colors whitespace-nowrap ${
                  range === opt.id
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <button
            onClick={() => void fetchSectorIndices(true)}
            disabled={loading}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 disabled:opacity-50"
            title="Refresh live Nifty sector indices"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* 6 x 2 Tile Grid matching NSE Sectoral Heatmap */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {tiles.map((tile) => {
          const isPos = tile.activeRet >= 0;
          return (
            <button
              key={tile.code}
              type="button"
              onClick={() => onSelectSector?.(tile.appSector)}
              style={getTileStyle(tile.activeRet)}
              className="group text-left rounded-lg border p-3.5 min-h-[118px] flex flex-col justify-between transition-transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500/60"
              title={`${tile.code} (${tile.label}) · Today ${tile.retToday >= 0 ? '+' : ''}${tile.retToday.toFixed(2)}% · Week ${tile.retWeek >= 0 ? '+' : ''}${tile.retWeek.toFixed(2)}% · Month ${tile.retMonth >= 0 ? '+' : ''}${tile.retMonth.toFixed(2)}%`}
            >
              <div>
                <div className="text-xs font-extrabold tracking-tight text-slate-900 dark:text-white font-mono">
                  {tile.code}
                </div>
                <div className="text-xs text-slate-800/80 dark:text-slate-200/85 mt-0.5 truncate">
                  {tile.label}
                </div>
              </div>

              <div className="flex items-end justify-between gap-1 pt-4">
                <span
                  className={`text-base font-bold font-mono tabular-nums ${
                    isPos
                      ? 'text-teal-950 dark:text-emerald-200'
                      : 'text-rose-800 dark:text-rose-200'
                  }`}
                >
                  {isPos ? '+' : ''}
                  {tile.activeRet.toFixed(1)}%
                </span>
                {tile.lastClose !== null && (
                  <span className="text-[10px] font-mono tabular-nums text-slate-700/75 dark:text-slate-300/75">
                    {Math.round(tile.lastClose).toLocaleString('en-IN')}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};
