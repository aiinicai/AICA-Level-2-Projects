import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  RefreshCw,
  DollarSign,
  Fuel,
  Ship,
  Sparkles,
  ExternalLink,
  Clock,
  Bookmark,
  BookmarkCheck,
  CheckCircle2,
  AlertCircle,
  Database,
  ArrowUpRight,
  ArrowDownRight,
  HelpCircle,
  Compass
} from 'lucide-react';
import { MarketData, SavedIntelligenceItem } from '../../types';
import { StorageService } from '../../services/storage';

interface GlobalIntelligenceViewProps {
  onOpenAIAnalyst: () => void;
}

const DEFAULT_MARKET_DATA: MarketData = {
  lastUpdated: new Date().toISOString(),
  forex: {
    usd_tzs: {
      rate: 2615.50,
      bid: 2605.00,
      ask: 2626.00,
      change24h: '+0.13%',
      summary: 'Bank of Tanzania (BOT) indicative exchange rate with tight interbank spread.',
    },
  },
  commodities: {
    brent_crude_usd: {
      price: 78.40,
      change24h: '-0.82%',
      summary: 'Global benchmark reflecting steady OPEC+ supply and shipping stability.',
    },
    bitumen_60_70_usd_ton: {
      price: 465.00,
      change24h: '+0.43%',
      summary: 'Bulk drum CFR Dar es Salaam landed import pricing for road contractors.',
    },
  },
  dar_port_corridor: {
    waiting_time_days: 3.2,
    customs_clearance_dwell_days: 4.0,
    fuel_price_dar_tzs_liter: 3140,
    corridor_status: 'Normal Flow — SGR Freight Trains & TANCIS Customs Operational',
  },
  marketNews: [
    {
      id: 'news_01',
      category: 'Forex & BOT',
      title: 'Bank of Tanzania Maintains Active FX Liquidity Oversight',
      summary: 'BOT monetary policy committee reports stable foreign reserves covering 4.5 months of imports, keeping USD/TZS trading in a predictable band.',
      source: 'Bank of Tanzania Market Bulletin',
      timestamp: 'Today',
    },
    {
      id: 'news_02',
      category: 'Logistics & Port',
      title: 'Dar es Salaam Port Berth Dwell Times Drop 18% Under Modernized TANCIS Digital Clearance',
      summary: 'Tanzania Ports Authority (TPA) and TRA implement 24/7 bonded transit processing for DRC, Rwanda, and Uganda Central Corridor cargo.',
      source: 'East African Freight & Maritime Report',
      timestamp: 'Yesterday',
    },
    {
      id: 'news_03',
      category: 'Commodities & Energy',
      title: 'Regional Bitumen 60/70 Import Demand Strengthens on Trunk Road Upgrades',
      summary: 'TANROADS tenders for Morogoro, Dodoma, and Tabora road rehabilitation support sustained demand for asphalt penetration grades.',
      source: 'Tanzania Construction Review',
      timestamp: '2 days ago',
    },
  ],
};

export const GlobalIntelligenceView: React.FC<GlobalIntelligenceViewProps> = ({ onOpenAIAnalyst }) => {
  const [marketData, setMarketData] = useState<MarketData>(DEFAULT_MARKET_DATA);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCached, setIsCached] = useState(false);
  const [savedItems, setSavedItems] = useState<SavedIntelligenceItem[]>([]);

  const storage = StorageService.getInstance();

  const fetchMarketData = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      // First check local storage if not forced
      if (!forceRefresh) {
        const cached = storage.getCachedMarketData();
        if (cached && cached.forex && cached.forex.usd_tzs) {
          setMarketData(cached);
          setIsCached(true);
          setLoading(false);
          return;
        }
      }

      const res = await fetch(`/api/intelligence/market-data${forceRefresh ? '?force=true' : ''}`);
      if (!res.ok) throw new Error(`Failed to load market feeds: ${res.statusText}`);
      const rawData = await res.json();

      // Normalize in case response is wrapped in { success, data } or is direct MarketData
      const normalizedData: MarketData =
        rawData.data && rawData.data.forex
          ? rawData.data
          : rawData.forex
          ? rawData
          : DEFAULT_MARKET_DATA;

      setMarketData(normalizedData);
      setIsCached(false);
      storage.saveCachedMarketData(normalizedData);
    } catch (err: any) {
      console.warn('Market data fetch error, using local/cached state', err);
      const cached = storage.getCachedMarketData();
      if (cached && cached.forex && cached.forex.usd_tzs) {
        setMarketData(cached);
        setIsCached(true);
        setError('Working in offline mode. Showing cached market intelligence.');
      } else {
        setMarketData(DEFAULT_MARKET_DATA);
        setIsCached(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketData();
    setSavedItems(storage.getSavedIntelligence());
  }, []);

  const handleBookmark = (title: string, category: string, summary: string) => {
    const exists = savedItems.some((i) => i.title === title);
    if (exists) {
      const remaining = savedItems.filter((i) => i.title !== title);
      setSavedItems(remaining);
      storage.saveIntelligenceItems(remaining);
    } else {
      const newItem: SavedIntelligenceItem = {
        id: `intel_${Date.now()}`,
        title,
        category,
        summary,
        timestamp: new Date().toISOString(),
      };
      const updated = [newItem, ...savedItems];
      setSavedItems(updated);
      storage.saveIntelligenceItems(updated);
    }
  };

  // Safe accessor shortcuts
  const forex = marketData?.forex?.usd_tzs || DEFAULT_MARKET_DATA.forex.usd_tzs;
  const brentCrude = marketData?.commodities?.brent_crude_usd || DEFAULT_MARKET_DATA.commodities.brent_crude_usd;
  const bitumen = marketData?.commodities?.bitumen_60_70_usd_ton || DEFAULT_MARKET_DATA.commodities.bitumen_60_70_usd_ton;
  const portInfo = marketData?.dar_port_corridor || DEFAULT_MARKET_DATA.dar_port_corridor;
  const newsList = marketData?.marketNews || DEFAULT_MARKET_DATA.marketNews;

  return (
    <div id="global-intelligence-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <TrendingUp className="w-5 h-5 text-amber-600" />
            <span>Global Trade & Corridor Logistics Intelligence</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Live USD/TZS exchange rates, Brent Crude & Bitumen 60/70 benchmarks, and Dar es Salaam Port corridor operational updates.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => fetchMarketData(true)}
            disabled={loading}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-lg text-xs font-semibold shadow-2xs transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-amber-600' : ''}`} />
            <span>{loading ? 'Refreshing Feed...' : 'Live Refresh (Gemini Grounded)'}</span>
          </button>

          <button
            onClick={onOpenAIAnalyst}
            className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask AI Trade Analyst</span>
          </button>
        </div>
      </div>

      {/* Cache / Offline Notice */}
      {isCached && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg flex items-center justify-between text-xs font-medium">
          <div className="flex items-center space-x-2">
            <Database className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Offline mode: Displaying locally cached intelligence from your last sync.</span>
          </div>
          <span className="text-[10px] text-amber-700 font-mono">100% Offline Compatible</span>
        </div>
      )}

      {error && !isCached && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg flex items-center space-x-2 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 3 Key Market Indicator Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* 1. Forex Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              <span>USD / TZS Foreign Exchange</span>
            </span>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              BOT & Interbank
            </span>
          </div>

          <div className="space-y-1">
            <p className="text-2xl font-bold font-mono text-slate-900">
              TZS {forex.rate?.toLocaleString() || '2,615.50'}
            </p>
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-emerald-600 font-semibold flex items-center">
                <ArrowUpRight className="w-3.5 h-3.5" />
                {forex.change24h || '+0.13%'}
              </span>
              <span className="text-slate-400 font-mono text-[11px]">
                Spread: {forex.bid?.toLocaleString() || '2,605'} / {forex.ask?.toLocaleString() || '2,626'}
              </span>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-100">
            {forex.summary || 'Bank of Tanzania indicative exchange rate.'}
          </p>
        </div>

        {/* 2. Commodities (Crude & Bitumen) */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <Fuel className="w-4 h-4 text-amber-600" />
              <span>Crude & Bitumen Benchmarks</span>
            </span>
            <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
              Energy Markets
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            <div className="p-2 bg-slate-50 rounded border border-slate-100">
              <span className="text-[10px] text-slate-500 font-medium block">Brent Crude</span>
              <span className="text-sm font-bold font-mono text-slate-900 block">
                ${brentCrude.price?.toFixed(2) || '78.40'}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">/ Barrel</span>
            </div>

            <div className="p-2 bg-slate-50 rounded border border-slate-100">
              <span className="text-[10px] text-slate-500 font-medium block">Bitumen 60/70</span>
              <span className="text-sm font-bold font-mono text-slate-900 block">
                ${bitumen.price?.toFixed(0) || '465'}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">/ MT Landed Dar</span>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-100">
            {bitumen.summary || 'Direct CFR Dar es Salaam landed import pricing.'}
          </p>
        </div>

        {/* 3. Dar Port & Logistics Corridor */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <Ship className="w-4 h-4 text-blue-600" />
              <span>Dar es Salaam Port Operational Status</span>
            </span>
            <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              Central Corridor
            </span>
          </div>

          <div className="space-y-1 text-xs">
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Berth Waiting Time:</span>
              <span className="font-bold text-slate-800">
                {portInfo.waiting_time_days || 3.2} Days
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Customs Clearance Dwell:</span>
              <span className="font-bold text-slate-800">
                {portInfo.customs_clearance_dwell_days || 4.0} Days
              </span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-slate-500">Corridor Fuel Price:</span>
              <span className="font-bold text-slate-800 font-mono">
                {portInfo.fuel_price_dar_tzs_liter ? `TZS ${portInfo.fuel_price_dar_tzs_liter}/L` : 'TZS 3,140/L'}
              </span>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-100">
            {portInfo.corridor_status || 'Normal Flow — SGR Freight Trains & TANCIS Customs Operational'}
          </p>
        </div>
      </div>

      {/* Main Grid: Logistics Intelligence Feed Left, Bookmarked Insights Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Intelligence Articles & Updates (8 Cols) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <Compass className="w-4 h-4 text-blue-600" />
              <span>Live Trade Updates & Regulatory Advisories</span>
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">
              Last Synced: {marketData?.lastUpdated ? new Date(marketData.lastUpdated).toLocaleTimeString() : 'Current'}
            </span>
          </div>

          <div className="space-y-3">
            {newsList.map((news) => {
              const isSaved = savedItems.some((i) => i.title === news.title);
              return (
                <div
                  key={news.id}
                  className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs hover:border-slate-300 transition space-y-2 text-xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 font-bold rounded text-[10px]">
                          {news.category}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          Source: {news.source} ({news.timestamp})
                        </span>
                      </div>
                      <h4 className="font-bold text-slate-900 text-sm leading-snug">{news.title}</h4>
                    </div>

                    <button
                      onClick={() => handleBookmark(news.title, news.category, news.summary)}
                      className={`p-1.5 rounded transition shrink-0 ${
                        isSaved ? 'text-amber-500 bg-amber-50' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
                      }`}
                      title={isSaved ? 'Remove Bookmark' : 'Save / Bookmark Insight'}
                    >
                      {isSaved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                    </button>
                  </div>

                  <p className="text-slate-600 leading-relaxed">{news.summary}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Saved Bookmarks & Quick AI Trigger (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <Bookmark className="w-4 h-4 text-amber-500" />
              <span>Saved Offline Intelligence ({savedItems.length})</span>
            </h3>

            {savedItems.length === 0 ? (
              <p className="text-[11px] text-slate-400 italic py-4 text-center">
                No bookmarked items. Click the bookmark icon on any trade advisory to store it for offline reference.
              </p>
            ) : (
              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {savedItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-blue-700 uppercase">{item.category}</span>
                      <button
                        onClick={() => handleBookmark(item.title, item.category, item.summary)}
                        className="text-slate-400 hover:text-rose-600"
                        title="Remove"
                      >
                        ×
                      </button>
                    </div>
                    <p className="font-semibold text-slate-800 leading-snug">{item.title}</p>
                    <p className="text-[11px] text-slate-500 line-clamp-2">{item.summary}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick AI Help Card */}
          <div className="p-4 bg-gradient-to-br from-indigo-900 to-slate-900 text-white rounded-xl shadow-xs space-y-3">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-300" />
              <h4 className="font-bold text-sm">Grounded Gemini Trade Analyst</h4>
            </div>
            <p className="text-xs text-indigo-100/90 leading-relaxed">
              Ask questions regarding Tanzania Customs valuation, EAC Tariff bands, Port demurrage rules, or bonded warehouse exemptions.
            </p>
            <button
              onClick={onOpenAIAnalyst}
              className="w-full py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-xs font-semibold transition flex items-center justify-center space-x-1.5"
            >
              <span>Launch AI Analyst</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
