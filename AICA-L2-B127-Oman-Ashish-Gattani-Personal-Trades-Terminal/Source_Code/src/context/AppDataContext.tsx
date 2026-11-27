import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  User,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from 'firebase/auth';
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  onSnapshot,
  query,
  serverTimestamp,
  setDoc,
  updateDoc,
  where,
} from 'firebase/firestore';
import {
  DEFAULT_PORTFOLIO_HOLDINGS,
  DEFAULT_WATCHLIST,
  ExtendedLiveUniverseChunkResponse,
  INDIAN_STOCKS,
  LiveUniverseResponse,
  applyExtendedLiveMarketData,
  applyLiveMarketData,
} from '../data/indianMarketData';
import { INITIAL_CUSTOM_INDICATORS } from '../engine/customIndicatorEngine';
import {
  OperationType,
  auth,
  clampStr,
  db,
  googleProvider,
  handleFirestoreError,
  sanitizeDocId,
} from '../firebase';
import {
  AlertCategory,
  AlertItem,
  BreakoutScanConfig,
  ConnectorState,
  CustomIndicatorDefinition,
  CustomWatchlist,
  PortfolioHolding,
} from '../types/market';

const LOCAL_CUSTOM_WATCHLISTS_KEY = 'tft_custom_watchlists_v1';

const SEED_CUSTOM_WATCHLISTS: CustomWatchlist[] = [
  {
    id: 'wl_slot_1',
    name: 'Core NSE Leaders',
    slotIndex: 1,
    notes: 'Primary Stage 2 SEPA leaders & institutional accumulation watchlist.',
    tickers: DEFAULT_WATCHLIST.slice(0, 60),
  },
];

function loadLocalCustomWatchlists(): CustomWatchlist[] {
  try {
    const raw = localStorage.getItem(LOCAL_CUSTOM_WATCHLISTS_KEY);
    if (!raw) return SEED_CUSTOM_WATCHLISTS;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length === 0) return SEED_CUSTOM_WATCHLISTS;
    return parsed.slice(0, 5).map((item, idx) => ({
      id: sanitizeDocId(String(item?.id || `wl_slot_${idx + 1}`)),
      name: clampStr(String(item?.name || `Watchlist ${idx + 1}`), 48) || `Watchlist ${idx + 1}`,
      slotIndex: Math.min(5, Math.max(1, Number(item?.slotIndex) || idx + 1)),
      notes: clampStr(String(item?.notes || ''), 240),
      tickers: Array.isArray(item?.tickers)
        ? Array.from(
            new Set<string>(
              (item.tickers as unknown[])
                .map((t) => String(t || '').trim().toUpperCase().replace(/[^A-Z0-9&\-]/g, '').slice(0, 20))
                .filter((t): t is string => t.length > 0)
            )
          ).slice(0, 60)
        : [],
    }));
  } catch {
    return SEED_CUSTOM_WATCHLISTS;
  }
}

function persistLocalCustomWatchlists(items: CustomWatchlist[]): void {
  try {
    localStorage.setItem(LOCAL_CUSTOM_WATCHLISTS_KEY, JSON.stringify(items.slice(0, 5)));
  } catch {
    // ignore storage quota errors
  }
}

const SEED_ALERTS: AlertItem[] = [
  {
    id: 'alert_seed_1',
    ticker: 'TRENT',
    category: 'vcp_pivot',
    title: 'TRENT — 4T VCP Pivot Breakout on 2.35× Volume',
    message:
      'Price crossed tight 2.6% final-contraction pivot with strong institutional volume dry-up preceding breakout.',
    read: false,
    createdAtIso: '2026-11-20T09:42:00+05:30',
  },
  {
    id: 'alert_seed_2',
    ticker: 'BAJFINANCE',
    category: 'breakout_52w',
    title: 'BAJFINANCE — First 52-Week High in 24 Months',
    message:
      'Closed above prior 52W high on 2.32× 50-day average volume after a 24-month consolidation base.',
    read: false,
    createdAtIso: '2026-11-20T09:28:00+05:30',
  },
  {
    id: 'alert_seed_3',
    ticker: 'HAL',
    category: 'trend_template',
    title: 'HAL — 8/8 Minervini Trend Template Passed (Stage 2)',
    message:
      'RS Rating climbed to top decile vs NIFTY 500 with 200-day SMA trending upward and accelerating Q2 EPS (+34.5% YoY).',
    read: false,
    createdAtIso: '2026-11-19T15:35:00+05:30',
  },
  {
    id: 'alert_seed_4',
    ticker: 'PERSISTENT',
    category: 'custom_indicator',
    title: 'PERSISTENT — RSMANS Mansfield RS Zero-Line Crossover',
    message:
      'Custom indicator RSMANS crossed above 0.00 against NIFTY 500 while holding above rising 50-day SMA.',
    read: true,
    createdAtIso: '2026-11-19T14:15:00+05:30',
  },
  {
    id: 'alert_seed_5',
    ticker: 'HDFCBANK',
    category: 'news',
    title: 'HDFCBANK — NSE Corporate Filing & Margin Update',
    message:
      'CD ratio normalized below 96%; net interest margin stabilized at 3.52% with FII stake rising +0.94% QoQ.',
    read: true,
    createdAtIso: '2026-11-19T11:05:00+05:30',
  },
];

const SEED_SCANS: BreakoutScanConfig[] = [
  {
    id: 'scan_seed_12m',
    name: '12M+ Fresh Base Breakouts (1.5× Vol)',
    lookbackMonths: 12,
    priceBasis: 'close',
    minVolumeRatio: 1.5,
    minPriceInr: 100,
    minTurnoverCr: 50,
    capBucket: 'All',
    sector: 'All',
    scheduleEnabled: true,
    scheduleTimeIst: '15:35 IST',
  },
  {
    id: 'scan_seed_6m_large',
    name: '6M Large/Mid Institutional Leaders',
    lookbackMonths: 6,
    priceBasis: 'close',
    minVolumeRatio: 1.8,
    minPriceInr: 200,
    minTurnoverCr: 200,
    capBucket: 'Large',
    sector: 'All',
    scheduleEnabled: true,
    scheduleTimeIst: '09:30 IST',
  },
];

interface AppDataContextValue {
  user: User | null;
  authLoading: boolean;
  authError: string | null;
  syncStatus: 'local' | 'syncing' | 'synced';
  signInWithGoogle: () => Promise<void>;
  signOutUser: () => Promise<void>;
  theme: 'dark' | 'light';
  toggleTheme: () => Promise<void>;
  watchlist: string[];
  toggleWatchlist: (ticker: string) => Promise<void>;
  addManyToWatchlist: (tickers: string[]) => Promise<void>;
  customWatchlists: CustomWatchlist[];
  saveCustomWatchlist: (
    wl: Omit<CustomWatchlist, 'id'> & { id?: string }
  ) => Promise<CustomWatchlist | null>;
  deleteCustomWatchlist: (watchlistId: string) => Promise<void>;
  accountCapitalInr: number;
  defaultRiskPct: number;
  updateRiskPreferences: (capitalInr: number, riskPct: number) => Promise<void>;
  connectors: ConnectorState;
  updateConnectors: (next: ConnectorState) => Promise<void>;
  holdings: PortfolioHolding[];
  upsertHolding: (holding: Omit<PortfolioHolding, 'id'> & { id?: string }) => Promise<void>;
  removeHolding: (holdingId: string) => Promise<void>;
  importHoldings: (
    entries: { ticker: string; shares: number; avgCostInr: number; stopLossInr?: number }[],
    mode: 'overwrite' | 'merge'
  ) => Promise<{ importedCount: number; totalCount: number }>;
  applyRebalanceShares: (updates: { ticker: string; targetShares: number }[]) => Promise<void>;
  savedScans: BreakoutScanConfig[];
  saveBreakoutScan: (scan: BreakoutScanConfig) => Promise<void>;
  deleteBreakoutScan: (scanId: string) => Promise<void>;
  toggleScanSchedule: (scanId: string, enabled: boolean, timeIst: string) => Promise<void>;
  customIndicators: CustomIndicatorDefinition[];
  saveCustomIndicator: (ind: CustomIndicatorDefinition) => Promise<void>;
  deleteCustomIndicator: (id: string) => Promise<void>;
  alerts: AlertItem[];
  addAlert: (alert: { ticker: string; category: AlertCategory; title: string; message: string }) => Promise<void>;
  markAlertRead: (alertId: string, read: boolean) => Promise<void>;
  markAllAlertsRead: () => Promise<void>;
  deleteAlert: (alertId: string) => Promise<void>;
  marketVersion: number;
  marketDataStatus: 'loading' | 'live' | 'fallback';
  lastPriceSyncIst: string | null;
  liveSymbolsCount: number;
  totalUniverseCount: number;
  isHydratingExtended: boolean;
  refreshLiveMarketData: (force?: boolean) => Promise<void>;
}

const AppDataContext = createContext<AppDataContextValue | null>(null);

export const AppDataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<'local' | 'syncing' | 'synced'>('local');

  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [watchlist, setWatchlist] = useState<string[]>(DEFAULT_WATCHLIST);
  const [customWatchlists, setCustomWatchlists] = useState<CustomWatchlist[]>(() =>
    loadLocalCustomWatchlists()
  );
  const [accountCapitalInr, setAccountCapitalInr] = useState<number>(25_00_000);
  const [defaultRiskPct, setDefaultRiskPct] = useState<number>(1.0);
  const [connectors, setConnectors] = useState<ConnectorState>({
    nseConnectorEnabled: true,
    bseConnectorEnabled: true,
    brokerConnectorName: 'Zerodha Kite',
  });
  const [holdings, setHoldings] = useState<PortfolioHolding[]>(DEFAULT_PORTFOLIO_HOLDINGS);
  const [savedScans, setSavedScans] = useState<BreakoutScanConfig[]>(SEED_SCANS);
  const [userIndicators, setUserIndicators] = useState<CustomIndicatorDefinition[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>(SEED_ALERTS);
  const [marketVersion, setMarketVersion] = useState(0);
  const [marketDataStatus, setMarketDataStatus] = useState<'loading' | 'live' | 'fallback'>('loading');
  const [lastPriceSyncIst, setLastPriceSyncIst] = useState<string | null>(null);
  const [liveSymbolsCount, setLiveSymbolsCount] = useState(0);
  const [isHydratingExtended, setIsHydratingExtended] = useState(false);

  const hydrateExtendedUniverse = useCallback(async (force = false) => {
    setIsHydratingExtended(true);
    try {
      const chunkSize = 250;
      const appliedTickers = new Set<string>();
      const maxPasses = 8;

      for (let pass = 0; pass < maxPasses; pass++) {
        let offset: number | null = 0;
        let serverCompleted = false;
        let newlyAppliedInPass = 0;
        let latestIst: string | null = null;

        while (offset !== null) {
          const qs = `offset=${offset}&limit=${chunkSize}${force && pass === 0 && offset === 0 ? '&refresh=1' : ''}`;
          const resp = await fetch(`/api/market/live-universe-extended?${qs}`);
          if (!resp.ok) break;
          const chunk = (await resp.json()) as ExtendedLiveUniverseChunkResponse;
          serverCompleted = chunk.completed;
          if (chunk.fetchedAtIst) latestIst = chunk.fetchedAtIst;

          // Only apply newly arrived tickers
          const freshStocks: ExtendedLiveUniverseChunkResponse['stocks'] = {};
          for (const [t, q] of Object.entries(chunk.stocks || {})) {
            if (!appliedTickers.has(t)) {
              freshStocks[t] = q;
              appliedTickers.add(t);
            }
          }
          const appliedCount = applyExtendedLiveMarketData({ ...chunk, stocks: freshStocks });
          newlyAppliedInPass += appliedCount;
          offset = chunk.nextOffset;
        }

        if (newlyAppliedInPass > 0) {
          const totalLive = INDIAN_STOCKS.filter((s) => s.isLiveHydrated).length;
          setLiveSymbolsCount(totalLive);
          if (latestIst) setLastPriceSyncIst(latestIst);
          setMarketVersion((v) => v + 1);
        }

        if (serverCompleted) break;
        await new Promise((r) => setTimeout(r, 2600));
      }
    } catch {
      // keep Tier-1 live data active
    } finally {
      setIsHydratingExtended(false);
    }
  }, []);

  const refreshLiveMarketData = useCallback(
    async (force = false) => {
      setMarketDataStatus('loading');
      try {
        const url = force ? '/api/market/live-universe?refresh=1' : '/api/market/live-universe';
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const payload = (await resp.json()) as LiveUniverseResponse;
        const updated = applyLiveMarketData(payload);
        if (updated > 0) {
          const totalLive = INDIAN_STOCKS.filter((s) => s.isLiveHydrated).length;
          setLiveSymbolsCount(totalLive);
          setLastPriceSyncIst(payload.fetchedAtIst || null);
          setMarketDataStatus('live');
          setMarketVersion((v) => v + 1);
          void hydrateExtendedUniverse(force);
        } else {
          setMarketDataStatus('fallback');
        }
      } catch {
        setMarketDataStatus('fallback');
      }
    },
    [hydrateExtendedUniverse]
  );

  useEffect(() => {
    void refreshLiveMarketData(false);
  }, [refreshLiveMarketData]);

  // Keep <html class="dark"> strictly synchronized with theme state
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  const customIndicators = useMemo(() => {
    const userByCode = new Map(userIndicators.map((u) => [u.code, u]));
    const mergedBuiltIns = INITIAL_CUSTOM_INDICATORS.map((b) => userByCode.get(b.code) ?? b);
    const builtInCodes = new Set(INITIAL_CUSTOM_INDICATORS.map((b) => b.code));
    const extras = userIndicators.filter((u) => !builtInCodes.has(u.code));
    return [...mergedBuiltIns, ...extras];
  }, [userIndicators]);

  // Ensure /users/{uid} exists before attaching subcollection writes (Master Gate invariant)
  const ensureProfileAndSeed = useCallback(async (u: User) => {
    const userRef = doc(db, 'users', u.uid);
    try {
      const snap = await getDoc(userRef);
      if (!snap.exists()) {
        await setDoc(userRef, {
          uid: u.uid,
          displayName: clampStr(u.displayName || 'NSE Investor', 120),
          email: clampStr(u.email || 'investor@arthaterminal.in', 254),
          photoURL: clampStr(u.photoURL || '', 512),
          theme: 'dark',
          watchlist: DEFAULT_WATCHLIST.slice(0, 60),
          accountCapitalInr: 25_00_000,
          defaultRiskPct: 1.0,
          nseConnectorEnabled: true,
          bseConnectorEnabled: true,
          brokerConnectorName: 'Zerodha Kite',
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp(),
        });

        // Seed initial holdings, scans, and alerts once for new user
        const existingHoldings = await getDocs(
          query(collection(db, 'users', u.uid, 'holdings'), where('userId', '==', u.uid))
        );
        if (existingHoldings.empty) {
          for (const h of DEFAULT_PORTFOLIO_HOLDINGS) {
            const hId = sanitizeDocId(h.id);
            await setDoc(doc(db, 'users', u.uid, 'holdings', hId), {
              userId: u.uid,
              ticker: h.ticker,
              shares: h.shares,
              avgCostInr: h.avgCostInr,
              targetWeightPct: h.targetWeightPct,
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        }

        const existingScans = await getDocs(
          query(collection(db, 'users', u.uid, 'savedScans'), where('userId', '==', u.uid))
        );
        if (existingScans.empty) {
          for (const s of SEED_SCANS) {
            const sId = sanitizeDocId(s.id || `scan_${Date.now()}`);
            await setDoc(doc(db, 'users', u.uid, 'savedScans', sId), {
              userId: u.uid,
              name: clampStr(s.name, 80),
              lookbackMonths: s.lookbackMonths,
              priceBasis: s.priceBasis,
              minVolumeRatio: s.minVolumeRatio,
              minPriceInr: s.minPriceInr,
              minTurnoverCr: s.minTurnoverCr,
              capBucket: clampStr(s.capBucket, 20),
              sector: clampStr(s.sector, 40),
              scheduleEnabled: s.scheduleEnabled,
              scheduleTimeIst: clampStr(s.scheduleTimeIst, 20),
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        }

        const existingAlerts = await getDocs(
          query(collection(db, 'users', u.uid, 'alerts'), where('userId', '==', u.uid))
        );
        if (existingAlerts.empty) {
          for (const a of SEED_ALERTS) {
            const aId = sanitizeDocId(a.id);
            await setDoc(doc(db, 'users', u.uid, 'alerts', aId), {
              userId: u.uid,
              ticker: a.ticker,
              category: a.category,
              title: clampStr(a.title, 140),
              message: clampStr(a.message, 400),
              read: a.read,
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        }

        const existingWatchlists = await getDocs(
          query(collection(db, 'users', u.uid, 'watchlists'), where('userId', '==', u.uid))
        );
        if (existingWatchlists.empty) {
          for (const wl of SEED_CUSTOM_WATCHLISTS) {
            const wId = sanitizeDocId(wl.id);
            await setDoc(doc(db, 'users', u.uid, 'watchlists', wId), {
              userId: u.uid,
              name: clampStr(wl.name, 48),
              slotIndex: wl.slotIndex,
              notes: clampStr(wl.notes, 240),
              tickers: wl.tickers.slice(0, 60),
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        }
      }
    } catch (error) {
      handleFirestoreError(error, OperationType.WRITE, `users/${u.uid}`);
    }
  }, []);

  // Auth listener & Firestore real-time subscriptions (strictly gated on authReady && user)
  useEffect(() => {
    let unsubProfile: (() => void) | null = null;
    let unsubHoldings: (() => void) | null = null;
    let unsubScans: (() => void) | null = null;
    let unsubIndicators: (() => void) | null = null;
    let unsubAlerts: (() => void) | null = null;
    let unsubWatchlists: (() => void) | null = null;

    const cleanupSubs = () => {
      unsubProfile?.();
      unsubHoldings?.();
      unsubScans?.();
      unsubIndicators?.();
      unsubAlerts?.();
      unsubWatchlists?.();
      unsubProfile = null;
      unsubHoldings = null;
      unsubScans = null;
      unsubIndicators = null;
      unsubAlerts = null;
      unsubWatchlists = null;
    };

    const unsubAuth = onAuthStateChanged(auth, async (u) => {
      cleanupSubs();
      setUser(u);
      setAuthLoading(false);

      if (!u) {
        setSyncStatus('local');
        return;
      }

      setSyncStatus('syncing');
      try {
        await ensureProfileAndSeed(u);
      } catch (err) {
        setAuthError(err instanceof Error ? err.message : 'Failed to initialize cloud profile.');
        setSyncStatus('local');
        return;
      }

      // 1. User Profile doc listener
      const profilePath = `users/${u.uid}`;
      unsubProfile = onSnapshot(
        doc(db, 'users', u.uid),
        (snap) => {
          if (snap.exists()) {
            const d = snap.data();
            if (d.theme === 'dark' || d.theme === 'light') setTheme(d.theme);
            if (Array.isArray(d.watchlist)) setWatchlist(d.watchlist);
            if (typeof d.accountCapitalInr === 'number') setAccountCapitalInr(d.accountCapitalInr);
            if (typeof d.defaultRiskPct === 'number') setDefaultRiskPct(d.defaultRiskPct);
            setConnectors({
              nseConnectorEnabled: Boolean(d.nseConnectorEnabled),
              bseConnectorEnabled: Boolean(d.bseConnectorEnabled),
              brokerConnectorName: d.brokerConnectorName || 'Zerodha Kite',
            });
            setSyncStatus('synced');
          }
        },
        (err) => handleFirestoreError(err, OperationType.GET, profilePath)
      );

      // 2. Holdings subcollection listener (secure where clause matching rules)
      const holdingsPath = `users/${u.uid}/holdings`;
      unsubHoldings = onSnapshot(
        query(collection(db, 'users', u.uid, 'holdings'), where('userId', '==', u.uid)),
        (snap) => {
          const items: PortfolioHolding[] = snap.docs.map((d) => {
            const data = d.data();
            return {
              id: d.id,
              ticker: String(data.ticker),
              shares: Number(data.shares),
              avgCostInr: Number(data.avgCostInr),
              targetWeightPct: Number(data.targetWeightPct),
              ...(typeof data.stopLossInr === 'number' && data.stopLossInr > 0
                ? { stopLossInr: Number(data.stopLossInr) }
                : {}),
            };
          });
          setHoldings(items);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, holdingsPath)
      );

      // 3. Saved Scans listener
      const scansPath = `users/${u.uid}/savedScans`;
      unsubScans = onSnapshot(
        query(collection(db, 'users', u.uid, 'savedScans'), where('userId', '==', u.uid)),
        (snap) => {
          const items: BreakoutScanConfig[] = snap.docs.map((d) => {
            const data = d.data();
            return {
              id: d.id,
              name: String(data.name),
              lookbackMonths: Number(data.lookbackMonths),
              priceBasis: data.priceBasis === 'high' ? 'high' : 'close',
              minVolumeRatio: Number(data.minVolumeRatio),
              minPriceInr: Number(data.minPriceInr),
              minTurnoverCr: Number(data.minTurnoverCr),
              capBucket: data.capBucket || 'All',
              sector: data.sector || 'All',
              scheduleEnabled: Boolean(data.scheduleEnabled),
              scheduleTimeIst: String(data.scheduleTimeIst || '15:35 IST'),
            };
          });
          setSavedScans(items);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, scansPath)
      );

      // 4. Custom Indicators listener
      const indPath = `users/${u.uid}/customIndicators`;
      unsubIndicators = onSnapshot(
        query(collection(db, 'users', u.uid, 'customIndicators'), where('userId', '==', u.uid)),
        (snap) => {
          const items: CustomIndicatorDefinition[] = snap.docs.map((d) => {
            const data = d.data();
            return {
              id: d.id,
              code: String(data.code),
              name: String(data.name),
              description: String(data.description || ''),
              formula: String(data.formula),
              buyRule: String(data.buyRule || ''),
              sellRule: String(data.sellRule || ''),
              plotType: data.plotType === 'overlay' ? 'overlay' : 'subchart',
              color: String(data.color || '#3b82f6'),
              param1Name: String(data.param1Name || 'p1'),
              param1Value: Number(data.param1Value ?? 14),
              param2Name: String(data.param2Name || 'p2'),
              param2Value: Number(data.param2Value ?? 1.5),
            };
          });
          setUserIndicators(items);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, indPath)
      );

      // 5. Alerts listener
      const alertsPath = `users/${u.uid}/alerts`;
      unsubAlerts = onSnapshot(
        query(collection(db, 'users', u.uid, 'alerts'), where('userId', '==', u.uid)),
        (snap) => {
          const items: AlertItem[] = snap.docs
            .map((d) => {
              const data = d.data();
              const ts = data.createdAt?.toDate ? data.createdAt.toDate().toISOString() : new Date().toISOString();
              return {
                id: d.id,
                ticker: String(data.ticker),
                category: data.category as AlertCategory,
                title: String(data.title),
                message: String(data.message),
                read: Boolean(data.read),
                createdAtIso: ts,
              };
            })
            .sort((a, b) => b.createdAtIso.localeCompare(a.createdAtIso));
          setAlerts(items);
        },
        (err) => handleFirestoreError(err, OperationType.LIST, alertsPath)
      );

      // 6. Custom Watchlists listener (up to 5 named watchlists)
      const watchlistsPath = `users/${u.uid}/watchlists`;
      unsubWatchlists = onSnapshot(
        query(collection(db, 'users', u.uid, 'watchlists'), where('userId', '==', u.uid)),
        (snap) => {
          const items: CustomWatchlist[] = snap.docs
            .map((d, idx) => {
              const data = d.data();
              return {
                id: d.id,
                name: String(data.name || `Watchlist ${idx + 1}`),
                slotIndex: Math.min(5, Math.max(1, Number(data.slotIndex) || idx + 1)),
                notes: String(data.notes || ''),
                tickers: Array.isArray(data.tickers)
                  ? data.tickers.map((t: unknown) => String(t)).slice(0, 60)
                  : [],
              };
            })
            .sort((a, b) => a.slotIndex - b.slotIndex)
            .slice(0, 5);
          if (items.length > 0) {
            setCustomWatchlists(items);
            persistLocalCustomWatchlists(items);
          }
        },
        (err) => handleFirestoreError(err, OperationType.LIST, watchlistsPath)
      );
    });

    return () => {
      cleanupSubs();
      unsubAuth();
    };
  }, [ensureProfileAndSeed]);

  const signInWithGoogle = useCallback(async () => {
    setAuthError(null);
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Google Sign-In failed.';
      if (!msg.includes('popup-closed-by-user')) {
        setAuthError(msg);
      }
    }
  }, []);

  const signOutUser = useCallback(async () => {
    setAuthError(null);
    await signOut(auth);
  }, []);

  const toggleTheme = useCallback(async () => {
    const next: 'dark' | 'light' = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    if (user) {
      const path = `users/${user.uid}`;
      try {
        await updateDoc(doc(db, 'users', user.uid), {
          theme: next,
          updatedAt: serverTimestamp(),
        });
      } catch (err) {
        handleFirestoreError(err, OperationType.UPDATE, path);
      }
    }
  }, [theme, user]);

  const toggleWatchlist = useCallback(
    async (ticker: string) => {
      const cleanTicker = ticker.toUpperCase().slice(0, 20);
      const next = watchlist.includes(cleanTicker)
        ? watchlist.filter((t) => t !== cleanTicker)
        : [cleanTicker, ...watchlist].slice(0, 60);
      setWatchlist(next);
      if (user) {
        const path = `users/${user.uid}`;
        try {
          await updateDoc(doc(db, 'users', user.uid), {
            watchlist: next,
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.UPDATE, path);
        }
      }
    },
    [watchlist, user]
  );

  const addManyToWatchlist = useCallback(
    async (tickers: string[]) => {
      const merged = Array.from(new Set([...tickers, ...watchlist])).slice(0, 60);
      setWatchlist(merged);
      if (user) {
        const path = `users/${user.uid}`;
        try {
          await updateDoc(doc(db, 'users', user.uid), {
            watchlist: merged,
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.UPDATE, path);
        }
      }
    },
    [watchlist, user]
  );

  const saveCustomWatchlist = useCallback(
    async (wl: Omit<CustomWatchlist, 'id'> & { id?: string }): Promise<CustomWatchlist | null> => {
      const existingById = wl.id ? customWatchlists.find((item) => item.id === wl.id) : undefined;
      if (!existingById && customWatchlists.length >= 5) {
        return null;
      }

      const usedSlots = new Set(customWatchlists.map((w) => w.slotIndex));
      let resolvedSlot = existingById?.slotIndex ?? wl.slotIndex;
      if (!resolvedSlot || resolvedSlot < 1 || resolvedSlot > 5) {
        for (let s = 1; s <= 5; s++) {
          if (!usedSlots.has(s)) {
            resolvedSlot = s;
            break;
          }
        }
      }
      const safeSlot = Math.min(5, Math.max(1, resolvedSlot || 1));
      const cleanName = clampStr((wl.name || '').trim() || `Watchlist ${safeSlot}`, 48);
      const cleanNotes = clampStr((wl.notes || '').trim(), 240);
      const cleanTickers = Array.from(
        new Set(
          (wl.tickers || [])
            .map((t) =>
              String(t || '')
                .trim()
                .toUpperCase()
                .replace(/^(NSE|BSE|NS|BO)[:.\-\s]+/i, '')
                .replace(/\.(NS|BO)$/i, '')
                .replace(/[^A-Z0-9&\-]/g, '')
                .slice(0, 20)
            )
            .filter(Boolean)
        )
      ).slice(0, 60);

      const docId = sanitizeDocId(existingById?.id || wl.id || `wl_${Date.now()}_${safeSlot}`);
      const nextItem: CustomWatchlist = {
        id: docId,
        name: cleanName,
        slotIndex: safeSlot,
        notes: cleanNotes,
        tickers: cleanTickers,
      };

      setCustomWatchlists((prev) => {
        const exists = prev.some((w) => w.id === docId);
        const updated = (
          exists ? prev.map((w) => (w.id === docId ? nextItem : w)) : [...prev, nextItem]
        )
          .sort((a, b) => a.slotIndex - b.slotIndex)
          .slice(0, 5);
        persistLocalCustomWatchlists(updated);
        return updated;
      });

      if (user) {
        const path = `users/${user.uid}/watchlists/${docId}`;
        const ref = doc(db, 'users', user.uid, 'watchlists', docId);
        try {
          const snap = await getDoc(ref);
          if (snap.exists()) {
            await updateDoc(ref, {
              name: cleanName,
              notes: cleanNotes,
              slotIndex: safeSlot,
              tickers: cleanTickers,
              updatedAt: serverTimestamp(),
            });
          } else {
            await setDoc(ref, {
              userId: user.uid,
              name: cleanName,
              slotIndex: safeSlot,
              notes: cleanNotes,
              tickers: cleanTickers,
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        } catch (err) {
          handleFirestoreError(err, OperationType.WRITE, path);
        }
      }

      return nextItem;
    },
    [customWatchlists, user]
  );

  const deleteCustomWatchlist = useCallback(
    async (watchlistId: string) => {
      const cleanId = sanitizeDocId(watchlistId);
      setCustomWatchlists((prev) => {
        const updated = prev.filter((w) => w.id !== cleanId);
        persistLocalCustomWatchlists(updated);
        return updated;
      });
      if (user) {
        const path = `users/${user.uid}/watchlists/${cleanId}`;
        try {
          await deleteDoc(doc(db, 'users', user.uid, 'watchlists', cleanId));
        } catch (err) {
          handleFirestoreError(err, OperationType.DELETE, path);
        }
      }
    },
    [user]
  );

  const updateRiskPreferences = useCallback(
    async (capitalInr: number, riskPct: number) => {
      const safeCap = Math.min(10_000_000_000, Math.max(10_000, capitalInr));
      const safeRisk = Math.min(10, Math.max(0.1, riskPct));
      setAccountCapitalInr(safeCap);
      setDefaultRiskPct(safeRisk);
      if (user) {
        const path = `users/${user.uid}`;
        try {
          await updateDoc(doc(db, 'users', user.uid), {
            accountCapitalInr: safeCap,
            defaultRiskPct: safeRisk,
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.UPDATE, path);
        }
      }
    },
    [user]
  );

  const updateConnectors = useCallback(
    async (next: ConnectorState) => {
      setConnectors(next);
      if (user) {
        const path = `users/${user.uid}`;
        try {
          await updateDoc(doc(db, 'users', user.uid), {
            nseConnectorEnabled: next.nseConnectorEnabled,
            bseConnectorEnabled: next.bseConnectorEnabled,
            brokerConnectorName: next.brokerConnectorName,
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.UPDATE, path);
        }
      }
    },
    [user]
  );

  const upsertHolding = useCallback(
    async (holding: Omit<PortfolioHolding, 'id'> & { id?: string }) => {
      const docId = sanitizeDocId(holding.id || `hold_${holding.ticker}`);
      const existing = holdings.find((h) => h.id === docId || h.ticker === holding.ticker);
      const finalId = existing ? existing.id : docId;
      const safeShares = Math.max(0, Math.min(100_000_000, Math.round(holding.shares)));
      const safeCost = Math.max(1, Math.min(10_000_000, Number(holding.avgCostInr)));
      const safeWeight = Math.max(0, Math.min(100, Number(holding.targetWeightPct)));

      const safeStop =
        holding.stopLossInr !== undefined && Number.isFinite(holding.stopLossInr) && holding.stopLossInr > 0
          ? Number(holding.stopLossInr)
          : undefined;

      const nextObj: PortfolioHolding = {
        id: finalId,
        ticker: holding.ticker,
        shares: safeShares,
        avgCostInr: safeCost,
        targetWeightPct: safeWeight,
        ...(safeStop !== undefined ? { stopLossInr: safeStop } : {}),
      };

      setHoldings((prev) => {
        const idx = prev.findIndex((p) => p.id === finalId);
        if (idx >= 0) {
          const copy = [...prev];
          copy[idx] = nextObj;
          return copy;
        }
        return [...prev, nextObj];
      });

      if (user) {
        const path = `users/${user.uid}/holdings/${finalId}`;
        try {
          if (existing) {
            await updateDoc(doc(db, 'users', user.uid, 'holdings', finalId), {
              shares: safeShares,
              avgCostInr: safeCost,
              targetWeightPct: safeWeight,
              stopLossInr: safeStop ?? 0,
              updatedAt: serverTimestamp(),
            });
          } else {
            await setDoc(doc(db, 'users', user.uid, 'holdings', finalId), {
              userId: user.uid,
              ticker: holding.ticker,
              shares: safeShares,
              avgCostInr: safeCost,
              targetWeightPct: safeWeight,
              ...(safeStop !== undefined ? { stopLossInr: safeStop } : {}),
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        } catch (err) {
          handleFirestoreError(err, existing ? OperationType.UPDATE : OperationType.CREATE, path);
        }
      }
    },
    [holdings, user]
  );

  const removeHolding = useCallback(
    async (holdingId: string) => {
      setHoldings((prev) => prev.filter((h) => h.id !== holdingId));
      if (user) {
        const path = `users/${user.uid}/holdings/${holdingId}`;
        try {
          await deleteDoc(doc(db, 'users', user.uid, 'holdings', holdingId));
        } catch (err) {
          handleFirestoreError(err, OperationType.DELETE, path);
        }
      }
    },
    [user]
  );

  const importHoldings = useCallback(
    async (
      entries: { ticker: string; shares: number; avgCostInr: number; stopLossInr?: number }[],
      mode: 'overwrite' | 'merge'
    ): Promise<{ importedCount: number; totalCount: number }> => {
      const cleaned = entries
        .map((e) => ({
          ticker: e.ticker.trim().toUpperCase().replace(/^(NSE|BSE):/i, ''),
          shares: Math.max(1, Math.min(100_000_000, Math.round(e.shares || 1))),
          avgCostInr: Math.max(1, Math.min(10_000_000, Number(e.avgCostInr) || 1)),
          stopLossInr:
            e.stopLossInr !== undefined && Number.isFinite(e.stopLossInr) && e.stopLossInr > 0
              ? Number(e.stopLossInr)
              : undefined,
        }))
        .filter((e) => e.ticker.length > 0);

      if (cleaned.length === 0) {
        return { importedCount: 0, totalCount: holdings.length };
      }

      // Build next holdings map (either fresh on overwrite or merged on merge)
      const byTicker = new Map<string, PortfolioHolding>();
      if (mode === 'merge') {
        for (const h of holdings) {
          byTicker.set(h.ticker.toUpperCase(), { ...h });
        }
      }

      for (const item of cleaned) {
        const key = item.ticker;
        const existing = byTicker.get(key);
        const docId = existing?.id || sanitizeDocId(`hold_${key}`);
        if (mode === 'merge' && existing) {
          // Weighted average cost + combined shares on merge
          const totalSh = existing.shares + item.shares;
          const avgCost =
            totalSh > 0
              ? Number(
                  (
                    (existing.shares * existing.avgCostInr + item.shares * item.avgCostInr) /
                    totalSh
                  ).toFixed(2)
                )
              : item.avgCostInr;
          byTicker.set(key, {
            id: docId,
            ticker: key,
            shares: totalSh,
            avgCostInr: avgCost,
            targetWeightPct: existing.targetWeightPct,
            stopLossInr: item.stopLossInr ?? existing.stopLossInr,
          });
        } else {
          byTicker.set(key, {
            id: docId,
            ticker: key,
            shares: item.shares,
            avgCostInr: Number(item.avgCostInr.toFixed(2)),
            targetWeightPct: 0,
            ...(item.stopLossInr !== undefined ? { stopLossInr: Number(item.stopLossInr.toFixed(2)) } : {}),
          });
        }
      }

      // Auto-recompute target weights proportionally to position cost/value so weights sum cleanly to 100%
      const list = Array.from(byTicker.values());
      const totalVal = list.reduce((s, h) => s + h.shares * h.avgCostInr, 0);
      const normalizedList: PortfolioHolding[] = list.map((h) => ({
        ...h,
        targetWeightPct:
          totalVal > 0
            ? Number((((h.shares * h.avgCostInr) / totalVal) * 100).toFixed(1))
            : Number((100 / list.length).toFixed(1)),
      }));

      const prevIds = new Set(holdings.map((h) => h.id));
      const nextIds = new Set(normalizedList.map((h) => h.id));

      setHoldings(normalizedList);

      if (user) {
        // Delete removed holdings on overwrite
        if (mode === 'overwrite') {
          for (const oldId of prevIds) {
            if (!nextIds.has(oldId)) {
              const delPath = `users/${user.uid}/holdings/${oldId}`;
              try {
                await deleteDoc(doc(db, 'users', user.uid, 'holdings', oldId));
              } catch (err) {
                handleFirestoreError(err, OperationType.DELETE, delPath);
              }
            }
          }
        }
        // Upsert all resulting holdings (updateDoc preserves immutable createdAt on existing docs)
        for (const h of normalizedList) {
          const path = `users/${user.uid}/holdings/${h.id}`;
          const isExistingDoc = prevIds.has(h.id);
          try {
            if (isExistingDoc) {
              await updateDoc(doc(db, 'users', user.uid, 'holdings', h.id), {
                shares: h.shares,
                avgCostInr: h.avgCostInr,
                targetWeightPct: h.targetWeightPct,
                stopLossInr: h.stopLossInr ?? 0,
                updatedAt: serverTimestamp(),
              });
            } else {
              await setDoc(doc(db, 'users', user.uid, 'holdings', h.id), {
                userId: user.uid,
                ticker: h.ticker,
                shares: h.shares,
                avgCostInr: h.avgCostInr,
                targetWeightPct: h.targetWeightPct,
                ...(h.stopLossInr !== undefined ? { stopLossInr: h.stopLossInr } : {}),
                createdAt: serverTimestamp(),
                updatedAt: serverTimestamp(),
              });
            }
          } catch (err) {
            handleFirestoreError(err, isExistingDoc ? OperationType.UPDATE : OperationType.CREATE, path);
          }
        }
      }

      return { importedCount: cleaned.length, totalCount: normalizedList.length };
    },
    [holdings, user]
  );

  const applyRebalanceShares = useCallback(
    async (updates: { ticker: string; targetShares: number }[]) => {
      const map = new Map(updates.map((u) => [u.ticker, Math.max(0, Math.round(u.targetShares))]));
      setHoldings((prev) =>
        prev.map((h) => (map.has(h.ticker) ? { ...h, shares: map.get(h.ticker)! } : h))
      );

      if (user) {
        for (const h of holdings) {
          if (!map.has(h.ticker)) continue;
          const nextShares = map.get(h.ticker)!;
          if (nextShares === h.shares) continue;
          const path = `users/${user.uid}/holdings/${h.id}`;
          try {
            await updateDoc(doc(db, 'users', user.uid, 'holdings', h.id), {
              shares: nextShares,
              updatedAt: serverTimestamp(),
            });
          } catch (err) {
            handleFirestoreError(err, OperationType.UPDATE, path);
          }
        }
      }
    },
    [holdings, user]
  );

  const saveBreakoutScan = useCallback(
    async (scan: BreakoutScanConfig) => {
      const scanId = sanitizeDocId(scan.id || `scan_${Date.now()}`);
      const existing = savedScans.find((s) => s.id === scanId);
      const clean: BreakoutScanConfig = {
        ...scan,
        id: scanId,
        name: clampStr(scan.name || 'Custom Breakout Scan', 80),
        lookbackMonths: Math.max(1, Math.min(36, Number(scan.lookbackMonths))),
        minVolumeRatio: Math.max(0, Math.min(20, Number(scan.minVolumeRatio))),
        minPriceInr: Math.max(0, Math.min(1_000_000, Number(scan.minPriceInr))),
        minTurnoverCr: Math.max(0, Math.min(50_000, Number(scan.minTurnoverCr))),
      };

      setSavedScans((prev) => {
        const idx = prev.findIndex((s) => s.id === scanId);
        if (idx >= 0) {
          const copy = [...prev];
          copy[idx] = clean;
          return copy;
        }
        return [clean, ...prev];
      });

      if (user) {
        const path = `users/${user.uid}/savedScans/${scanId}`;
        try {
          if (existing) {
            await updateDoc(doc(db, 'users', user.uid, 'savedScans', scanId), {
              name: clean.name,
              lookbackMonths: clean.lookbackMonths,
              priceBasis: clean.priceBasis,
              minVolumeRatio: clean.minVolumeRatio,
              minPriceInr: clean.minPriceInr,
              minTurnoverCr: clean.minTurnoverCr,
              capBucket: clampStr(clean.capBucket, 20),
              sector: clampStr(clean.sector, 40),
              updatedAt: serverTimestamp(),
            });
          } else {
            await setDoc(doc(db, 'users', user.uid, 'savedScans', scanId), {
              userId: user.uid,
              name: clean.name,
              lookbackMonths: clean.lookbackMonths,
              priceBasis: clean.priceBasis,
              minVolumeRatio: clean.minVolumeRatio,
              minPriceInr: clean.minPriceInr,
              minTurnoverCr: clean.minTurnoverCr,
              capBucket: clampStr(clean.capBucket, 20),
              sector: clampStr(clean.sector, 40),
              scheduleEnabled: clean.scheduleEnabled,
              scheduleTimeIst: clampStr(clean.scheduleTimeIst, 20),
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        } catch (err) {
          handleFirestoreError(err, existing ? OperationType.UPDATE : OperationType.CREATE, path);
        }
      }
    },
    [savedScans, user]
  );

  const deleteBreakoutScan = useCallback(
    async (scanId: string) => {
      setSavedScans((prev) => prev.filter((s) => s.id !== scanId));
      if (user) {
        const path = `users/${user.uid}/savedScans/${scanId}`;
        try {
          await deleteDoc(doc(db, 'users', user.uid, 'savedScans', scanId));
        } catch (err) {
          handleFirestoreError(err, OperationType.DELETE, path);
        }
      }
    },
    [user]
  );

  const toggleScanSchedule = useCallback(
    async (scanId: string, enabled: boolean, timeIst: string) => {
      setSavedScans((prev) =>
        prev.map((s) =>
          s.id === scanId ? { ...s, scheduleEnabled: enabled, scheduleTimeIst: timeIst } : s
        )
      );
      if (user) {
        const path = `users/${user.uid}/savedScans/${scanId}`;
        try {
          await updateDoc(doc(db, 'users', user.uid, 'savedScans', scanId), {
            scheduleEnabled: enabled,
            scheduleTimeIst: clampStr(timeIst, 20),
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.UPDATE, path);
        }
      }
    },
    [user]
  );

  const saveCustomIndicator = useCallback(
    async (ind: CustomIndicatorDefinition) => {
      const safeCode =
        ind.code
          .toUpperCase()
          .replace(/[^A-Z0-9_]/g, '')
          .slice(0, 16) || `IND_${Date.now().toString().slice(-4)}`;
      const docId = sanitizeDocId(
        ind.id.startsWith('builtin_') ? `custom_${safeCode}` : ind.id || `ind_${safeCode}`
      );
      const existing = userIndicators.find((u) => u.id === docId);

      const clean: CustomIndicatorDefinition = {
        ...ind,
        id: docId,
        code: safeCode,
        name: clampStr(ind.name || safeCode, 80),
        description: clampStr(ind.description || '', 400),
        formula: clampStr(ind.formula || 'close', 600),
        buyRule: clampStr(ind.buyRule || '', 400),
        sellRule: clampStr(ind.sellRule || '', 400),
        color: clampStr(ind.color || '#3b82f6', 16),
        param1Name: clampStr(ind.param1Name || 'p1', 24),
        param1Value: Math.max(-100000, Math.min(100000, Number(ind.param1Value) || 14)),
        param2Name: clampStr(ind.param2Name || 'p2', 24),
        param2Value: Math.max(-100000, Math.min(100000, Number(ind.param2Value) || 1.5)),
        isBuiltIn: ind.isBuiltIn,
      };

      setUserIndicators((prev) => {
        const idx = prev.findIndex((x) => x.id === docId);
        if (idx >= 0) {
          const copy = [...prev];
          copy[idx] = clean;
          return copy;
        }
        return [...prev, clean];
      });

      if (user) {
        const path = `users/${user.uid}/customIndicators/${docId}`;
        try {
          if (existing) {
            await updateDoc(doc(db, 'users', user.uid, 'customIndicators', docId), {
              code: clean.code,
              name: clean.name,
              description: clean.description,
              formula: clean.formula,
              buyRule: clean.buyRule,
              sellRule: clean.sellRule,
              plotType: clean.plotType,
              color: clean.color,
              param1Name: clean.param1Name,
              param1Value: clean.param1Value,
              param2Name: clean.param2Name,
              param2Value: clean.param2Value,
              updatedAt: serverTimestamp(),
            });
          } else {
            await setDoc(doc(db, 'users', user.uid, 'customIndicators', docId), {
              userId: user.uid,
              code: clean.code,
              name: clean.name,
              description: clean.description,
              formula: clean.formula,
              buyRule: clean.buyRule,
              sellRule: clean.sellRule,
              plotType: clean.plotType,
              color: clean.color,
              param1Name: clean.param1Name,
              param1Value: clean.param1Value,
              param2Name: clean.param2Name,
              param2Value: clean.param2Value,
              createdAt: serverTimestamp(),
              updatedAt: serverTimestamp(),
            });
          }
        } catch (err) {
          handleFirestoreError(err, existing ? OperationType.UPDATE : OperationType.CREATE, path);
        }
      }
    },
    [userIndicators, user]
  );

  const deleteCustomIndicator = useCallback(
    async (id: string) => {
      setUserIndicators((prev) => prev.filter((x) => x.id !== id));
      if (user) {
        const path = `users/${user.uid}/customIndicators/${id}`;
        try {
          await deleteDoc(doc(db, 'users', user.uid, 'customIndicators', id));
        } catch (err) {
          handleFirestoreError(err, OperationType.DELETE, path);
        }
      }
    },
    [user]
  );

  const addAlert = useCallback(
    async (alert: { ticker: string; category: AlertCategory; title: string; message: string }) => {
      const validTicker = INDIAN_STOCKS.some((s) => s.ticker === alert.ticker)
        ? alert.ticker
        : alert.ticker.toUpperCase().replace(/[^A-Z0-9&-]/g, '').slice(0, 20) || 'NIFTY50';
      const alertId = sanitizeDocId(`alert_${Date.now()}_${Math.floor(Math.random() * 1000)}`);
      const item: AlertItem = {
        id: alertId,
        ticker: validTicker,
        category: alert.category,
        title: clampStr(alert.title, 140),
        message: clampStr(alert.message, 400),
        read: false,
        createdAtIso: new Date().toISOString(),
      };
      setAlerts((prev) => [item, ...prev]);

      if (user) {
        const path = `users/${user.uid}/alerts/${alertId}`;
        try {
          await setDoc(doc(db, 'users', user.uid, 'alerts', alertId), {
            userId: user.uid,
            ticker: item.ticker,
            category: item.category,
            title: item.title,
            message: item.message,
            read: false,
            createdAt: serverTimestamp(),
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.CREATE, path);
        }
      }
    },
    [user]
  );

  const markAlertRead = useCallback(
    async (alertId: string, read: boolean) => {
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, read } : a)));
      if (user) {
        const path = `users/${user.uid}/alerts/${alertId}`;
        try {
          await updateDoc(doc(db, 'users', user.uid, 'alerts', alertId), {
            read,
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.UPDATE, path);
        }
      }
    },
    [user]
  );

  const markAllAlertsRead = useCallback(async () => {
    const unreadIds = alerts.filter((a) => !a.read).map((a) => a.id);
    setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
    if (user) {
      for (const id of unreadIds) {
        const path = `users/${user.uid}/alerts/${id}`;
        try {
          await updateDoc(doc(db, 'users', user.uid, 'alerts', id), {
            read: true,
            updatedAt: serverTimestamp(),
          });
        } catch (err) {
          handleFirestoreError(err, OperationType.UPDATE, path);
        }
      }
    }
  }, [alerts, user]);

  const deleteAlert = useCallback(
    async (alertId: string) => {
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      if (user) {
        const path = `users/${user.uid}/alerts/${alertId}`;
        try {
          await deleteDoc(doc(db, 'users', user.uid, 'alerts', alertId));
        } catch (err) {
          handleFirestoreError(err, OperationType.DELETE, path);
        }
      }
    },
    [user]
  );

  const value: AppDataContextValue = {
    user,
    authLoading,
    authError,
    syncStatus,
    signInWithGoogle,
    signOutUser,
    theme,
    toggleTheme,
    watchlist,
    toggleWatchlist,
    addManyToWatchlist,
    customWatchlists,
    saveCustomWatchlist,
    deleteCustomWatchlist,
    accountCapitalInr,
    defaultRiskPct,
    updateRiskPreferences,
    connectors,
    updateConnectors,
    holdings,
    upsertHolding,
    removeHolding,
    importHoldings,
    applyRebalanceShares,
    savedScans,
    saveBreakoutScan,
    deleteBreakoutScan,
    toggleScanSchedule,
    customIndicators,
    saveCustomIndicator,
    deleteCustomIndicator,
    alerts,
    addAlert,
    markAlertRead,
    markAllAlertsRead,
    deleteAlert,
    marketVersion,
    marketDataStatus,
    lastPriceSyncIst,
    liveSymbolsCount,
    totalUniverseCount: INDIAN_STOCKS.length,
    isHydratingExtended,
    refreshLiveMarketData,
  };

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
};

export function useAppData(): AppDataContextValue {
  const ctx = useContext(AppDataContext);
  if (!ctx) throw new Error('useAppData must be used inside AppDataProvider');
  return ctx;
}
