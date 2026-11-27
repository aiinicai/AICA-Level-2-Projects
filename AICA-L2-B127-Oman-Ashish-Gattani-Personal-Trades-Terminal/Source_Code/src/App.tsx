import React, { useEffect, useState } from 'react';
import {
  Bell,
  Calendar,
  Coins,
  Compass,
  Crosshair,
  FileArchive,
  Flame,
  GitCommitHorizontal,
  Keyboard,
  Layers,
  LayoutDashboard,
  LogIn,
  LogOut,
  Menu,
  Moon,
  PieChart,
  Plug,
  RefreshCw,
  Search,
  Sparkles,
  Sun,
  TrendingUp,
  X,
} from 'lucide-react';
import { AiDeskDrawer } from './components/AiDeskDrawer';
import { ErrorBoundary } from './components/ErrorBoundary';
import {
  ConnectorsCalendarModal,
  KeyboardShortcutsModal,
  NotificationsDrawer,
  SearchCommandModal,
} from './components/OverlaysAndDrawers';
import { AppDataProvider, useAppData } from './context/AppDataContext';
import { ActiveWorkspace } from './types/market';
import { getIndianMarketStatus } from './utils/formatters';
import { BreakoutScannerView } from './views/BreakoutScannerView';
import { ClosingBellLabView } from './views/ClosingBellLabView';
import { ConnectorsView } from './views/ConnectorsView';
import { DonchianBreakoutsView } from './views/DonchianBreakoutsView';
import { FundamentalLabView } from './views/FundamentalLabView';
import { HighVolumeScannerView } from './views/HighVolumeScannerView';
import { MarketOverviewView } from './views/MarketOverviewView';
import { MinerviniSepaView } from './views/MinerviniSepaView';
import { PortfolioRiskView } from './views/PortfolioRiskView';
import { StockDetailView } from './views/StockDetailView';
import { TradeRadarView } from './views/TradeRadarView';
import { TrendingSectorsView } from './views/TrendingSectorsView';

const NAV_ITEMS: {
  id: ActiveWorkspace;
  label: string;
  shortcut: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: 'overview', label: 'Market Overview', shortcut: '1', icon: LayoutDashboard },
  { id: 'sectors', label: 'Trending Sectors', shortcut: '2', icon: Layers },
  { id: 'radar', label: 'Trade Radar & Regime', shortcut: '3', icon: Crosshair },
  { id: 'breakout', label: '52W & ATH Breakouts', shortcut: '4', icon: TrendingUp },
  { id: 'minervini', label: 'Minervini SEPA', shortcut: '5', icon: Compass },
  { id: 'donchian', label: 'DC Channel Breakouts', shortcut: 'D', icon: GitCommitHorizontal },
  { id: 'hv_scanner', label: 'HVE / HVY / HVQ Screener', shortcut: '6', icon: Flame },
  { id: 'portfolio', label: 'Portfolio & Risk', shortcut: '7', icon: PieChart },
  { id: 'fundamental', label: 'Fundamental Lab', shortcut: '8', icon: Coins },
  { id: 'closingbell', label: 'Closing Bell Lab', shortcut: '9', icon: FileArchive },
  { id: 'connectors', label: 'Connectors (3)', shortcut: '0', icon: Plug },
];

const WORKSPACE_LABELS: Record<ActiveWorkspace, string> = {
  overview: 'Market Overview',
  sectors: 'Trending Sectors & Subsectors (Technical Score)',
  radar: 'Trade Setup Radar, Market Regime & Journal',
  breakout: '52-Week & All-Time High Breakout Scanner',
  minervini: 'Mark Minervini SEPA',
  donchian: 'Donchian Channel Breakouts (This Week & Today)',
  hv_scanner: 'HVE / HVY / HVQ Institutional Volume Screener',
  portfolio: 'Portfolio & Risk Management',
  fundamental: 'Fundamental Lab — Audited Financials, Ratios & FCF',
  closingbell: 'The Closing Bell Research Lab (21 Bhavcopy Metrics)',
  connectors: 'Market Data Connectors (3) & NSE Calendar',
};

function TerminalShell() {
  const {
    user,
    authLoading,
    authError,
    syncStatus,
    signInWithGoogle,
    signOutUser,
    theme,
    toggleTheme,
    alerts,
    connectors,
    marketDataStatus,
    lastPriceSyncIst,
    liveSymbolsCount,
    totalUniverseCount,
    isHydratingExtended,
    refreshLiveMarketData,
  } = useAppData();

  const [workspace, setWorkspace] = useState<ActiveWorkspace>('overview');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [connectorsOpen, setConnectorsOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [aiDeskOpen, setAiDeskOpen] = useState(false);
  const [inspectState, setInspectState] = useState<{
    ticker: string | null;
    prior52WHigh?: number;
  }>({ ticker: null });

  const [istClock, setIstClock] = useState(() => getIndianMarketStatus());

  // Update IST clock every 15 seconds
  useEffect(() => {
    const id = setInterval(() => setIstClock(getIndianMarketStatus()), 15000);
    return () => clearInterval(id);
  }, []);

  // Global Institutional Keyboard Shortcuts ('/', 'Esc', 'N', '?', '1'-'6')
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isEditable =
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable);

      if (e.key === 'Escape') {
        setSearchOpen(false);
        setNotificationsOpen(false);
        setConnectorsOpen(false);
        setShortcutsOpen(false);
        setAiDeskOpen(false);
        setInspectState({ ticker: null });
        setMobileNavOpen(false);
        return;
      }

      if (isEditable || e.metaKey || e.ctrlKey || e.altKey) return;

      if (e.key === '/') {
        e.preventDefault();
        setSearchOpen(true);
      } else if (e.key === '?') {
        e.preventDefault();
        setShortcutsOpen((v) => !v);
      } else if (e.key.toLowerCase() === 'a') {
        e.preventDefault();
        setAiDeskOpen((v) => !v);
      } else if (e.key.toLowerCase() === 'n') {
        e.preventDefault();
        setNotificationsOpen((v) => !v);
      } else if (e.key.toLowerCase() === 'd') {
        e.preventDefault();
        setInspectState({ ticker: null });
        setWorkspace('donchian');
      } else if ((e.key >= '1' && e.key <= '9') || e.key === '0') {
        const hit = NAV_ITEMS.find((item) => item.shortcut === e.key);
        if (hit) {
          e.preventDefault();
          setInspectState({ ticker: null });
          setWorkspace(hit.id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const unreadCount = alerts.filter((a) => !a.read).length;
  const activeConnectorsCount =
    (connectors.nseConnectorEnabled ? 1 : 0) +
    (connectors.bseConnectorEnabled ? 1 : 0) +
    (connectors.brokerConnectorName !== 'Disconnected' ? 1 : 0);

  const openStockInspector = (ticker: string, context?: { prior52WHigh?: number }) => {
    setInspectState({ ticker: ticker.trim().toUpperCase(), prior52WHigh: context?.prior52WHigh });
  };

  const navigateWorkspace = (ws: ActiveWorkspace) => {
    setInspectState({ ticker: null });
    setWorkspace(ws);
    setMobileNavOpen(false);
  };

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100">
      {/* Mobile Sidebar Backdrop */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/60 lg:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      {/* Left Workspace Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-64 shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0F1522] flex flex-col transition-transform duration-150 ${
          mobileNavOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Single-line Brand Wordmark */}
        <div className="h-14 px-5 flex items-center justify-between border-b border-slate-200 dark:border-slate-800 shrink-0">
          <button
            onClick={() => navigateWorkspace('overview')}
            className="text-[15px] font-extrabold tracking-tight text-slate-900 dark:text-white whitespace-nowrap"
          >
            Personal Trades Terminal
          </button>
          <button
            onClick={() => setMobileNavOpen(false)}
            className="lg:hidden p-1 text-slate-500"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = !inspectState.ticker && workspace === item.id;
            return (
              <button
                key={item.id}
                onClick={() => navigateWorkspace(item.id)}
                className={`w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                  active
                    ? 'bg-blue-600/10 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 font-semibold'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                <span className="flex items-center gap-2.5 truncate">
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </span>
                <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500">
                  {item.shortcut}
                </span>
              </button>
            );
          })}

          <div className="pt-4 mt-4 border-t border-slate-200 dark:border-slate-800 space-y-1">
            <button
              onClick={() => navigateWorkspace('connectors')}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 text-left"
            >
              <Calendar className="w-4 h-4 shrink-0" />
              <div className="min-w-0">
                <div className="font-mono text-[11px] font-semibold text-slate-800 dark:text-slate-200 tabular-nums">
                  {istClock.istTimeStr.slice(0, 5)} IST
                </div>
                <div className="text-[11px] text-slate-500 truncate">{istClock.sessionLabel}</div>
              </div>
            </button>
          </div>
        </nav>

        {/* Bottom Firebase Auth & Cloud Sync Panel */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 shrink-0 space-y-2">
          {authError && (
            <div className="text-[11px] text-red-500 px-1 leading-snug">{authError}</div>
          )}
          {authLoading ? (
            <div className="px-3 py-2 text-xs text-slate-500">Checking session…</div>
          ) : user ? (
            <div className="flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg bg-slate-100/70 dark:bg-slate-900/70">
              <div className="min-w-0">
                <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {user.displayName || 'Investor'}
                </div>
                <div className="text-[11px] text-slate-500 truncate">
                  {syncStatus === 'synced' ? 'Firestore Cloud Synced' : 'Syncing…'}
                </div>
              </div>
              <button
                onClick={signOutUser}
                className="p-1.5 rounded-md text-slate-500 hover:text-red-500 hover:bg-slate-200 dark:hover:bg-slate-800 shrink-0"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={signInWithGoogle}
              className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors whitespace-nowrap"
            >
              <LogIn className="w-3.5 h-3.5" />
              Sign in with Google
            </button>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Clean Contextual Top Header */}
        <header className="sticky top-0 z-30 h-14 px-4 lg:px-6 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0B0F17]/95 backdrop-blur-xs flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setMobileNavOpen(true)}
              className="lg:hidden p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300"
              aria-label="Open navigation"
            >
              <Menu className="w-4 h-4" />
            </button>
            <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
              <span>NSE · BSE</span>
              <span className="mx-2">/</span>
              {inspectState.ticker ? (
                <>
                  <button
                    onClick={() => setInspectState({ ticker: null })}
                    className="hover:text-slate-900 dark:hover:text-slate-100 hover:underline"
                  >
                    {WORKSPACE_LABELS[workspace]}
                  </button>
                  <span className="mx-2">/</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                    {inspectState.ticker}
                  </span>
                </>
              ) : (
                <span className="font-semibold text-slate-900 dark:text-slate-100">
                  {WORKSPACE_LABELS[workspace]}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => refreshLiveMarketData(true)}
              disabled={marketDataStatus === 'loading'}
              className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:border-slate-400 dark:hover:border-slate-700 disabled:opacity-60 whitespace-nowrap"
              title="Refresh live NSE & BSE market prices"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${
                  marketDataStatus === 'loading' || isHydratingExtended
                    ? 'animate-spin text-blue-500'
                    : marketDataStatus === 'live'
                    ? 'text-emerald-500'
                    : 'text-amber-500'
                }`}
              />
              <span>
                {marketDataStatus === 'loading'
                  ? 'Syncing NSE…'
                  : isHydratingExtended
                  ? `Syncing ${liveSymbolsCount}/${totalUniverseCount}…`
                  : marketDataStatus === 'live'
                  ? `Live ${liveSymbolsCount}/${totalUniverseCount} · ${lastPriceSyncIst?.slice(-8) || 'IST'}`
                  : 'Refresh Prices'}
              </span>
            </button>

            <button
              onClick={() => navigateWorkspace('connectors')}
              className={`hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                workspace === 'connectors'
                  ? 'border-blue-500 bg-blue-600/10 text-blue-700 dark:text-blue-300'
                  : 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:border-slate-400 dark:hover:border-slate-700'
              }`}
              title="Manage NSE, BSE & Indian Broker Connectors (8)"
            >
              <Plug className="w-3.5 h-3.5 text-emerald-500" />
              <span>Connectors</span>
              <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">
                {activeConnectorsCount}/3
              </span>
            </button>

            <button
              onClick={() => setSearchOpen(true)}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 hover:border-blue-500 dark:hover:border-blue-500 transition-colors whitespace-nowrap"
            >
              <Search className="w-3.5 h-3.5 text-blue-500" />
              <span className="hidden sm:inline">Analyze any NSE / BSE stock</span>
              <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300">
                /
              </kbd>
            </button>

            <button
              onClick={() => setAiDeskOpen(true)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300 hover:bg-blue-500/20 transition-colors whitespace-nowrap"
              title="Open AI TechnoFunda Desk (A)"
            >
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
              <span className="hidden sm:inline">AI Desk</span>
              <kbd className="hidden md:inline font-mono text-[10px] px-1 py-0.5 rounded bg-white/80 dark:bg-slate-900 border border-blue-500/30 text-blue-600 dark:text-blue-300">
                A
              </kbd>
            </button>

            <button
              onClick={() => setNotificationsOpen(true)}
              className="relative inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 whitespace-nowrap"
              title="Notifications (N)"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="font-mono text-[11px] font-bold text-blue-600 dark:text-blue-400">
                  {unreadCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setShortcutsOpen(true)}
              className="hidden sm:inline-flex p-2 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
              title="Keyboard shortcuts (?)"
            >
              <Keyboard className="w-4 h-4" />
            </button>

            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100"
              title="Toggle light/dark theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Main Workspace Viewport (Full-Page Stock Intelligence View when a ticker is clicked) */}
        <main className="flex-1 p-4 lg:p-6 max-w-[1440px] w-full mx-auto">
          {inspectState.ticker ? (
            <StockDetailView
              ticker={inspectState.ticker}
              prior52WHigh={inspectState.prior52WHigh}
              backLabel={WORKSPACE_LABELS[workspace]}
              onBack={() => setInspectState({ ticker: null })}
              onSelectTicker={(nextTicker) => openStockInspector(nextTicker)}
            />
          ) : (
            <>
              {workspace === 'overview' && (
                <MarketOverviewView
                  onNavigate={navigateWorkspace}
                  onInspectStock={(ticker) => openStockInspector(ticker)}
                  onOpenConnectors={() => setConnectorsOpen(true)}
                />
              )}
              {workspace === 'sectors' && (
                <TrendingSectorsView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'radar' && (
                <TradeRadarView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'donchian' && (
                <DonchianBreakoutsView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'breakout' && (
                <BreakoutScannerView onInspectStock={openStockInspector} />
              )}
              {workspace === 'minervini' && (
                <MinerviniSepaView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'hv_scanner' && (
                <HighVolumeScannerView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'portfolio' && (
                <PortfolioRiskView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'fundamental' && (
                <FundamentalLabView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'closingbell' && (
                <ClosingBellLabView onInspectStock={(ticker) => openStockInspector(ticker)} />
              )}
              {workspace === 'connectors' && <ConnectorsView onNavigate={navigateWorkspace} />}
            </>
          )}
        </main>
      </div>

      {/* Modals & Drawers */}
      <SearchCommandModal
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelectStock={(t) => openStockInspector(t)}
        onNavigate={navigateWorkspace}
      />
      <NotificationsDrawer
        open={notificationsOpen}
        onClose={() => setNotificationsOpen(false)}
        onInspectStock={(t) => openStockInspector(t)}
      />
      <ConnectorsCalendarModal
        open={connectorsOpen}
        onClose={() => setConnectorsOpen(false)}
      />
      <KeyboardShortcutsModal
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
      <AiDeskDrawer
        open={aiDeskOpen}
        onClose={() => setAiDeskOpen(false)}
        activeTicker={inspectState.ticker}
        activeWorkspaceLabel={WORKSPACE_LABELS[workspace]}
      />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppDataProvider>
        <TerminalShell />
      </AppDataProvider>
    </ErrorBoundary>
  );
}
