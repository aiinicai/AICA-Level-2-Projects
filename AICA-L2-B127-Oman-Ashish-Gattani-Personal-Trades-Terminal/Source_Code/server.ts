import 'dotenv/config';
import { GoogleGenAI, ThinkingLevel } from '@google/genai';
import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';
import { NSE_1100_CATALOG } from './src/data/nse1050Catalog.ts';

const FREE_TIER_GEMINI_MODELS = ['gemini-4-hydrogen', 'gemini-3.1-flash-lite'] as const;

let cachedGeminiClient: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || !apiKey.trim()) {
    throw new Error('GEMINI_API_KEY is not configured on the server.');
  }
  if (!cachedGeminiClient) {
    cachedGeminiClient = new GoogleGenAI({
      apiKey: apiKey.trim(),
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    });
  }
  return cachedGeminiClient;
}

function formatGeminiError(err: unknown, fallback: string): string {
  const raw = err instanceof Error ? err.message : fallback;
  try {
    const parsed = JSON.parse(raw);
    if (parsed?.error?.message) return String(parsed.error.message);
  } catch {
    // not JSON
  }
  return raw || fallback;
}

async function generateFreeTierAiText(
  prompt: string
): Promise<{ text: string; model: string }> {
  const ai = getGeminiClient();
  let lastErr: unknown = null;
  for (const model of FREE_TIER_GEMINI_MODELS) {
    let timer: ReturnType<typeof setTimeout> | null = null;
    try {
      const config =
        model === 'gemini-4-hydrogen'
          ? {
              systemInstruction: TECHNOFUNDA_SYSTEM_INSTRUCTION,
              thinkingConfig: { thinkingLevel: ThinkingLevel.LOW },
            }
          : {
              systemInstruction: TECHNOFUNDA_SYSTEM_INSTRUCTION,
            };
      const timeoutPromise = new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error(`TIMEOUT: ${model} exceeded 20s`)), 20000);
      });
      const response = await Promise.race([
        ai.models.generateContent({
          model,
          contents: prompt,
          config,
        }),
        timeoutPromise,
      ]);
      return { text: response.text?.trim() || '', model };
    } catch (err) {
      lastErr = err;
      const msg = err instanceof Error ? err.message : '';
      // Retry fallback active free-tier model on transient 503/429/UNAVAILABLE/timeout/not-found errors
      if (/503|429|UNAVAILABLE|overloaded|high demand|NOT_FOUND|404|no longer available|TIMEOUT/i.test(msg)) {
        continue;
      }
      throw err;
    } finally {
      if (timer) clearTimeout(timer);
    }
  }
  throw lastErr ?? new Error('AI service temporarily unavailable.');
}

function serializeSnapshotField(val: unknown, maxLen: number): string {
  if (typeof val === 'string') return val.trim().slice(0, maxLen);
  if (val && typeof val === 'object') {
    try {
      return JSON.stringify(val, null, 2).slice(0, maxLen);
    } catch {
      return '';
    }
  }
  return '';
}

const TECHNOFUNDA_SYSTEM_INSTRUCTION = [
  'You are an institutional Indian equity TechnoFunda desk analyst covering NSE and BSE stocks.',
  'Always quote Indian Rupees (₹), Indian market conventions (Crores, NIFTY 500, Promoter/DII/FII shareholding, SEBI/NSE context), and the exact metrics provided.',
  'Focus strictly on technical trend structure (Stage 1-4, Minervini SEPA, Donchian Channel, Supertrend, 200/50 SMA, RSI > 60 momentum, ADX +DI/-DI, volume behavior), fundamental earnings/margin momentum, Smart Money (Promoter + DII + FII) flow, and clear risk invalidation levels.',
  'NEVER invent or cite DCF valuations, intrinsic fair values, or speculative analyst price targets.',
  'Keep responses concise, structured with bold headings and crisp bullet points, and grounded only in the provided data.',
].join(' ');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BROWSER_UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36';

const NSE_HEADERS: Record<string, string> = {
  'User-Agent': BROWSER_UA,
  Accept: 'application/zip,application/octet-stream,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9',
  Referer: 'https://www.nseindia.com/all-reports',
};

const CORE_NSE_TICKERS = [
  // Original 38 core leaders
  'TRENT',
  'HAL',
  'DIXON',
  'PERSISTENT',
  'BEL',
  'CDSL',
  'BSE',
  'CGPOWER',
  'CUMMINSIND',
  'SOLARINDS',
  'RELIANCE',
  'TCS',
  'HDFCBANK',
  'ICICIBANK',
  'INFY',
  'BHARTIARTL',
  'M&M',
  'SUNPHARMA',
  'ITC',
  'COALINDIA',
  'POWERGRID',
  'NTPC',
  'POLYCAB',
  'BAJFINANCE',
  'LT',
  'KALYANKJIL',
  'INDIGO',
  'MCX',
  'DRREDDY',
  'TATAMOTORS',
  'TATAELXSI',
  'DMART',
  'TITAN',
  'PIDILITIND',
  'ANGELONE',
  'SUZLON',
  'SHAKTIPUMP',
  'ELECON',
  // Expanded 62 NIFTY 50, NIFTY Next 50 & High-Momentum Mid/Smallcap leaders (100 total)
  'SBIN',
  'AXISBANK',
  'KOTAKBANK',
  'BANKBARODA',
  'FEDERALBNK',
  'SHRIRAMFIN',
  'CHOLAFIN',
  'JIOFIN',
  'SBILIFE',
  'HDFCLIFE',
  'PFC',
  'RECLTD',
  'IRFC',
  'HCLTECH',
  'WIPRO',
  'TECHM',
  'LTIM',
  'COFORGE',
  'KPITTECH',
  'MARUTI',
  'BAJAJ-AUTO',
  'EICHERMOT',
  'TVSMOTOR',
  'MOTHERSON',
  'BHARATFORG',
  'CIPLA',
  'DIVISLAB',
  'LUPIN',
  'APOLLOHOSP',
  'MAXHEALTH',
  'TATASTEEL',
  'JSWSTEEL',
  'HINDALCO',
  'VEDL',
  'JINDALSTEL',
  'ULTRACEMCO',
  'GRASIM',
  'ASTRAL',
  'HAVELLS',
  'DLF',
  'OBEROIRLTY',
  'LODHA',
  'ADANIPORTS',
  'ADANIENT',
  'ABB',
  'SIEMENS',
  'MAZDOCK',
  'COCHINSHIP',
  'RVNL',
  'ONGC',
  'BPCL',
  'TATAPOWER',
  'HINDUNILVR',
  'NESTLEIND',
  'BRITANNIA',
  'VBL',
  'ASIANPAINT',
  'INDHOTEL',
  'ETERNAL',
  'NAUKRI',
  'SRF',
  'PIIND',
  'PNB',
  'CANBK',
  'INDUSINDBK',
  'BAJAJFINSV',
  'HEROMOTOCO',
  'TORNTPHARM',
  'AUROPHARMA',
  'AMBUJACEM',
  'SHREECEM',
  'GODREJPROP',
  'BHEL',
  'BDL',
  'IOC',
  'GAIL',
  'TATACONSUM',
  'DEEPAKNTR',
  'KAYNES',
  'VOLTAS',
  'NMDC',
  'TORNTPOWER',
  'ADANIPOWER',
  'PAYTM',
  'TRIDENT',
];

const TICKER_YAHOO_FALLBACKS: Record<string, string[]> = {
  TATAMOTORS: ['TMPV.NS', 'TMCV.NS', 'TATAMOTORS.BO', 'TATAMOTORS.NS'],
  ETERNAL: ['ETERNAL.NS', 'ZOMATO.NS', 'ETERNAL.BO'],
  'M&M': ['M&M.NS', 'M&M.BO'],
  'BAJAJ-AUTO': ['BAJAJ-AUTO.NS', 'BAJAJ-AUTO.BO'],
};

interface LiveBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface LiveQuotePayload {
  symbol: string;
  yahooSymbol: string;
  bars: LiveBar[];
  latestClose: number;
  prevClose: number;
  dailyChangePct: number;
  avgDailyTurnoverCr: number;
}

interface LiveUniverseCache {
  expiresAt: number;
  data: {
    fetchedAtIst: string;
    source: string;
    liveCount: number;
    benchmarks: Record<'NIFTY50' | 'NIFTY500' | 'SENSEX', LiveQuotePayload | null>;
    stocks: Record<string, LiveQuotePayload>;
  };
}

let universeCache: LiveUniverseCache | null = null;
let universeInFlight: Promise<LiveUniverseCache['data']> | null = null;

interface CompactLiveQuote {
  s: string;
  lc: number;
  pc: number;
  dc: number;
  tc: number;
  d: string[];
  o: number[];
  h: number[];
  l: number[];
  c: number[];
  v: number[];
}

const CORE_TICKER_SET = new Set(CORE_NSE_TICKERS);
const EXTENDED_NSE_TICKERS: string[] = NSE_1100_CATALOG.map((row) => row[0]).filter(
  (t) => !CORE_TICKER_SET.has(t)
);

const extendedLiveStore = new Map<string, CompactLiveQuote>();
let extendedHydrationState = {
  isHydrating: false,
  completed: false,
  expiresAt: 0,
  fetchedAtIst: '',
};
let extendedHydrationPromise: Promise<void> | null = null;

function toCompactQuote(q: LiveQuotePayload): CompactLiveQuote {
  const len = q.bars.length;
  const d = new Array<string>(len);
  const o = new Array<number>(len);
  const h = new Array<number>(len);
  const l = new Array<number>(len);
  const c = new Array<number>(len);
  const v = new Array<number>(len);
  for (let i = 0; i < len; i++) {
    const b = q.bars[i];
    d[i] = b.date;
    o[i] = b.open;
    h[i] = b.high;
    l[i] = b.low;
    c[i] = b.close;
    v[i] = b.volume;
  }
  return {
    s: q.symbol,
    lc: q.latestClose,
    pc: q.prevClose,
    dc: q.dailyChangePct,
    tc: q.avgDailyTurnoverCr,
    d,
    o,
    h,
    l,
    c,
    v,
  };
}

function nowIstFormatted(): string {
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date());
}

async function fetchNseTickerRange(
  ticker: string,
  range: string,
  hostHint = 0
): Promise<LiveQuotePayload | null> {
  const candidates = TICKER_YAHOO_FALLBACKS[ticker] || [`${ticker}.NS`];
  for (const sym of candidates) {
    const hosts =
      hostHint % 2 === 0
        ? ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']
        : ['query2.finance.yahoo.com', 'query1.finance.yahoo.com'];
    for (const host of hosts) {
      const url = `https://${host}/v8/finance/chart/${encodeURIComponent(sym)}?range=${range}&interval=1d&includeAdjustedClose=true`;
      try {
        const resp = await fetchWithTimeout(
          url,
          { 'User-Agent': BROWSER_UA, Accept: 'application/json' },
          6500
        );
        if (!resp.ok) continue;
        const json = (await resp.json()) as {
          chart?: {
            result?: Array<{
              meta?: { regularMarketPrice?: number };
              timestamp?: number[];
              indicators?: {
                quote?: Array<{
                  open?: Array<number | null>;
                  high?: Array<number | null>;
                  low?: Array<number | null>;
                  close?: Array<number | null>;
                  volume?: Array<number | null>;
                }>;
              };
            }>;
          };
        };
        const result = json?.chart?.result?.[0];
        if (!result || !Array.isArray(result.timestamp) || !result.indicators?.quote?.[0]) continue;
        const ts = result.timestamp;
        const q = result.indicators.quote[0];
        const byDate = new Map<string, LiveBar>();
        for (let i = 0; i < ts.length; i++) {
          const cl = q.close?.[i];
          const op = q.open?.[i] ?? cl;
          const hiRaw = q.high?.[i] ?? cl;
          const loRaw = q.low?.[i] ?? cl;
          const vo = q.volume?.[i] ?? 0;
          if (typeof cl !== 'number' || !Number.isFinite(cl) || cl <= 0 || typeof op !== 'number' || !Number.isFinite(op) || op <= 0) {
            continue;
          }
          const istMs = ts[i] * 1000 + 5.5 * 3600 * 1000;
          const dateStr = new Date(istMs).toISOString().slice(0, 10);
          const hi = typeof hiRaw === 'number' && Number.isFinite(hiRaw) ? Math.max(hiRaw, op, cl) : Math.max(op, cl);
          const lo = typeof loRaw === 'number' && Number.isFinite(loRaw) ? Math.min(loRaw, op, cl) : Math.min(op, cl);
          byDate.set(dateStr, {
            date: dateStr,
            open: Number(op.toFixed(2)),
            high: Number(hi.toFixed(2)),
            low: Number(lo.toFixed(2)),
            close: Number(cl.toFixed(2)),
            volume: typeof vo === 'number' && Number.isFinite(vo) && vo >= 0 ? Math.round(vo) : 0,
          });
        }
        const bars = Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
        if (bars.length < 20) continue;
        const lastBar = bars[bars.length - 1];
        const prevBar = bars[bars.length - 2];
        const latestClose =
          typeof result.meta?.regularMarketPrice === 'number' &&
          Number.isFinite(result.meta.regularMarketPrice) &&
          result.meta.regularMarketPrice > 0
            ? Number(result.meta.regularMarketPrice.toFixed(2))
            : lastBar.close;
        if (Math.abs(lastBar.close - latestClose) / Math.max(1, latestClose) < 0.25) {
          lastBar.close = latestClose;
          lastBar.high = Number(Math.max(lastBar.high, latestClose).toFixed(2));
          lastBar.low = Number(Math.min(lastBar.low, latestClose).toFixed(2));
        }
        const prevClose = prevBar.close;
        const dailyChangePct =
          prevClose > 0 ? Number((((latestClose - prevClose) / prevClose) * 100).toFixed(2)) : 0;
        const recent50 = bars.slice(-50);
        const avgTurnInr =
          recent50.reduce((sum, b) => sum + b.close * b.volume, 0) / Math.max(1, recent50.length);
        return {
          symbol: ticker,
          yahooSymbol: sym,
          bars,
          latestClose,
          prevClose,
          dailyChangePct,
          avgDailyTurnoverCr: Number((avgTurnInr / 1e7).toFixed(2)),
        };
      } catch {
        // try next host
      }
    }
  }
  return null;
}

function ensureExtendedHydration(forceRefresh = false): void {
  if (!forceRefresh && extendedHydrationState.completed && extendedHydrationState.expiresAt > Date.now()) {
    return;
  }
  if (extendedHydrationPromise) return;

  extendedHydrationState.isHydrating = true;
  if (forceRefresh) {
    extendedHydrationState.completed = false;
  }

  extendedHydrationPromise = (async () => {
    const concurrency = 28;
    let cursor = 0;
    const worker = async () => {
      while (cursor < EXTENDED_NSE_TICKERS.length) {
        const idx = cursor++;
        const ticker = EXTENDED_NSE_TICKERS[idx];
        const res = await fetchNseTickerRange(ticker, '18mo', idx);
        if (res) {
          extendedLiveStore.set(ticker, toCompactQuote(res));
        }
      }
    };
    await Promise.all(
      Array.from({ length: Math.min(concurrency, EXTENDED_NSE_TICKERS.length) }, worker)
    );
    extendedHydrationState = {
      isHydrating: false,
      completed: true,
      expiresAt: Date.now() + 15 * 60 * 1000,
      fetchedAtIst: nowIstFormatted(),
    };
  })()
    .catch(() => {
      extendedHydrationState.isHydrating = false;
    })
    .finally(() => {
      extendedHydrationPromise = null;
    });
}

function formatDDMMYY(d: Date): string {
  const dd = String(d.getUTCDate()).padStart(2, '0');
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
  const yy = String(d.getUTCFullYear()).slice(-2);
  return `${dd}${mm}${yy}`;
}

function formatYYYYMMDD(d: Date): string {
  const yyyy = String(d.getUTCFullYear());
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(d.getUTCDate()).padStart(2, '0');
  return `${yyyy}${mm}${dd}`;
}

function getCandidateTradingDates(requestedIso?: string): Date[] {
  const start =
    requestedIso && /^\d{4}-\d{2}-\d{2}$/.test(requestedIso)
      ? new Date(`${requestedIso}T00:00:00Z`)
      : new Date();
  const candidates: Date[] = [];
  const cursor = new Date(start.getTime());
  let guard = 0;
  while (candidates.length < 7 && guard < 18) {
    const day = cursor.getUTCDay();
    if (day !== 0 && day !== 6) {
      candidates.push(new Date(cursor.getTime()));
    }
    cursor.setUTCDate(cursor.getUTCDate() - 1);
    guard++;
  }
  return candidates;
}

async function fetchWithTimeout(url: string, headers: Record<string, string>, ms = 7500) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { headers, signal: controller.signal, redirect: 'follow' });
  } finally {
    clearTimeout(timer);
  }
}

async function fetchYahooChart(
  yahooSymbol: string,
  range = '3y'
): Promise<LiveQuotePayload | null> {
  const hosts = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com'];
  for (const host of hosts) {
    const url = `https://${host}/v8/finance/chart/${encodeURIComponent(yahooSymbol)}?range=${range}&interval=1d&includeAdjustedClose=true`;
    try {
      const resp = await fetchWithTimeout(
        url,
        { 'User-Agent': BROWSER_UA, Accept: 'application/json' },
        8000
      );
      if (!resp.ok) continue;
      const json = (await resp.json()) as {
        chart?: {
          result?: Array<{
            meta?: {
              regularMarketPrice?: number;
              chartPreviousClose?: number;
              previousClose?: number;
            };
            timestamp?: number[];
            indicators?: {
              quote?: Array<{
                open?: Array<number | null>;
                high?: Array<number | null>;
                low?: Array<number | null>;
                close?: Array<number | null>;
                volume?: Array<number | null>;
              }>;
            };
          }>;
        };
      };

      const result = json?.chart?.result?.[0];
      if (!result || !Array.isArray(result.timestamp) || !result.indicators?.quote?.[0]) continue;

      const ts = result.timestamp;
      const q = result.indicators.quote[0];
      const byDate = new Map<string, LiveBar>();

      for (let i = 0; i < ts.length; i++) {
        const c = q.close?.[i];
        const o = q.open?.[i] ?? c;
        const h = q.high?.[i] ?? c;
        const l = q.low?.[i] ?? c;
        const v = q.volume?.[i] ?? 0;
        if (
          typeof c !== 'number' ||
          !Number.isFinite(c) ||
          c <= 0 ||
          typeof o !== 'number' ||
          !Number.isFinite(o) ||
          o <= 0
        ) {
          continue;
        }
        // Shift UTC timestamp +5.5h to IST before extracting trading date YYYY-MM-DD
        const istMs = ts[i] * 1000 + 5.5 * 3600 * 1000;
        const dateStr = new Date(istMs).toISOString().slice(0, 10);
        const hi = typeof h === 'number' && Number.isFinite(h) ? Math.max(h, o, c) : Math.max(o, c);
        const lo = typeof l === 'number' && Number.isFinite(l) ? Math.min(l, o, c) : Math.min(o, c);
        byDate.set(dateStr, {
          date: dateStr,
          open: Number(o.toFixed(2)),
          high: Number(hi.toFixed(2)),
          low: Number(lo.toFixed(2)),
          close: Number(c.toFixed(2)),
          volume: typeof v === 'number' && Number.isFinite(v) && v >= 0 ? Math.round(v) : 0,
        });
      }

      const bars = Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
      if (bars.length < 5) continue;

      const lastBar = bars[bars.length - 1];
      const prevBar = bars[bars.length - 2];

      const latestClose =
        typeof result.meta?.regularMarketPrice === 'number' &&
        Number.isFinite(result.meta.regularMarketPrice) &&
        result.meta.regularMarketPrice > 0
          ? Number(result.meta.regularMarketPrice.toFixed(2))
          : lastBar.close;

      // Keep latest bar close aligned with regularMarketPrice
      if (Math.abs(lastBar.close - latestClose) / Math.max(1, latestClose) < 0.25) {
        lastBar.close = latestClose;
        lastBar.high = Number(Math.max(lastBar.high, latestClose).toFixed(2));
        lastBar.low = Number(Math.min(lastBar.low, latestClose).toFixed(2));
      }

      const prevClose = prevBar.close;
      const dailyChangePct =
        prevClose > 0 ? Number((((latestClose - prevClose) / prevClose) * 100).toFixed(2)) : 0;

      const recent50 = bars.slice(-50);
      const avgTurnInr =
        recent50.reduce((sum, b) => sum + b.close * b.volume, 0) / Math.max(1, recent50.length);
      const avgDailyTurnoverCr = Number((avgTurnInr / 1e7).toFixed(2));

      return {
        symbol: yahooSymbol,
        yahooSymbol,
        bars,
        latestClose,
        prevClose,
        dailyChangePct,
        avgDailyTurnoverCr,
      };
    } catch {
      // failover to secondary host
    }
  }
  return null;
}

async function fetchNseTickerWithFallback(ticker: string): Promise<LiveQuotePayload | null> {
  const candidates = TICKER_YAHOO_FALLBACKS[ticker] || [`${ticker}.NS`, `${ticker}.BO`];
  for (const sym of candidates) {
    const res = await fetchYahooChart(sym, '3y');
    if (res && res.bars.length >= 20) {
      return { ...res, symbol: ticker };
    }
  }
  return null;
}

async function fetchLiveUniverse(forceRefresh = false) {
  if (!forceRefresh && universeCache && universeCache.expiresAt > Date.now()) {
    return universeCache.data;
  }
  if (!forceRefresh && universeInFlight) {
    return universeInFlight;
  }

  const run = async () => {
    const [nifty50, nifty500, sensex] = await Promise.all([
      fetchYahooChart('^NSEI', '3y'),
      fetchYahooChart('^CRSLDX', '3y'),
      fetchYahooChart('^BSESN', '3y'),
    ]);

    const stocks: Record<string, LiveQuotePayload> = {};
    const uniqueTickers = Array.from(new Set(CORE_NSE_TICKERS));
    const concurrency = 16;
    let cursor = 0;

    const worker = async () => {
      while (cursor < uniqueTickers.length) {
        const idx = cursor++;
        const ticker = uniqueTickers[idx];
        const res = await fetchNseTickerWithFallback(ticker);
        if (res) {
          stocks[ticker] = res;
        }
      }
    };

    await Promise.all(Array.from({ length: Math.min(concurrency, uniqueTickers.length) }, worker));

    const fetchedAtIst = new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(new Date());

    const data = {
      fetchedAtIst,
      source: 'NSE / BSE Live Market Feed',
      liveCount: Object.keys(stocks).length,
      benchmarks: {
        NIFTY50: nifty50,
        NIFTY500: nifty500,
        SENSEX: sensex,
      },
      stocks,
    };

    // Cache for 5 minutes if we got meaningful live quotes
    if (data.liveCount >= 10) {
      universeCache = {
        expiresAt: Date.now() + 5 * 60 * 1000,
        data,
      };
    }
    return data;
  };

  universeInFlight = run().finally(() => {
    universeInFlight = null;
  });
  return universeInFlight;
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '15mb' }));

  /**
   * Live NSE / BSE Market Universe Endpoint (Core 123 equities + NIFTY 50, NIFTY 500, SENSEX)
   * Returns real-time latest prices and up to 3 years of real daily OHLCV candles.
   */
  app.get('/api/market/live-universe', async (req, res) => {
    try {
      const forceRefresh = req.query.refresh === '1';
      const data = await fetchLiveUniverse(forceRefresh);
      ensureExtendedHydration(forceRefresh);
      res.json(data);
    } catch (err) {
      res.status(502).json({
        error: err instanceof Error ? err.message : 'Failed to fetch live NSE/BSE prices',
      });
    }
  });

  /**
   * Extended 1,000+ NSE Universe Chunked Compact Endpoint
   * Delivers live 18-month daily NSE OHLCV candles for ALL NIFTY 500, F&O, Midcap 150,
   * Smallcap 500, Microcap 250, and Mainboard EQ equities in compact parallel arrays.
   */
  app.get('/api/market/live-universe-extended', (req, res) => {
    const forceRefresh = req.query.refresh === '1';
    ensureExtendedHydration(forceRefresh);

    const offset = Math.max(0, Number(req.query.offset) || 0);
    const limit = Math.min(300, Math.max(50, Number(req.query.limit) || 250));
    const sliceTickers = EXTENDED_NSE_TICKERS.slice(offset, offset + limit);
    const stocks: Record<string, CompactLiveQuote> = {};
    for (const t of sliceTickers) {
      const hit = extendedLiveStore.get(t);
      if (hit) stocks[t] = hit;
    }
    const nextOffset = offset + limit < EXTENDED_NSE_TICKERS.length ? offset + limit : null;

    res.json({
      totalExtended: EXTENDED_NSE_TICKERS.length,
      hydratedCount: extendedLiveStore.size,
      isHydrating: extendedHydrationState.isHydrating,
      completed: extendedHydrationState.completed,
      fetchedAtIst: extendedHydrationState.fetchedAtIst || nowIstFormatted(),
      offset,
      limit,
      nextOffset,
      stocks,
    });
  });

  /**
   * On-demand live NSE/BSE OHLCV quote lookup for any ticker
   */
  app.get('/api/market/quote/:symbol', async (req, res) => {
    const raw = String(req.params.symbol || '').trim().toUpperCase();
    if (!raw || !/^[A-Z0-9&.\-^]{1,24}$/.test(raw)) {
      return res.status(400).json({ error: 'Invalid symbol format' });
    }
    const result = raw.startsWith('^') || raw.endsWith('.NS') || raw.endsWith('.BO')
      ? await fetchYahooChart(raw, '3y')
      : await fetchNseTickerWithFallback(raw);

    if (!result) {
      return res.status(404).json({ error: `No live NSE/BSE OHLCV data found for ${raw}` });
    }
    return res.json(result);
  });

  /**
   * Live Nifty Sector Indices Heatmap Endpoint (Today, This Week, This Month)
   * Covers all 12 official NSE Sectoral Indices shown on the Nifty Sector Heatmap.
   */
  const NIFTY_SECTOR_INDICES_META: {
    code: string;
    label: string;
    yahooSymbol: string;
    appSector: string;
  }[] = [
    { code: 'CNXREALTY', label: 'Realty', yahooSymbol: '^CNXREALTY', appSector: 'Real Estate' },
    { code: 'CNXIT', label: 'IT', yahooSymbol: '^CNXIT', appSector: 'Information Technology' },
    { code: 'CNXMETAL', label: 'Metal', yahooSymbol: '^CNXMETAL', appSector: 'Metals & Mining' },
    { code: 'CNXENERGY', label: 'Energy', yahooSymbol: '^CNXENERGY', appSector: 'Oil, Gas & Energy' },
    { code: 'CNXPHARMA', label: 'Pharma', yahooSymbol: '^CNXPHARMA', appSector: 'Pharma & Healthcare' },
    { code: 'CNXINFRA', label: 'Infrastructure', yahooSymbol: '^CNXINFRA', appSector: 'Infrastructure & Construction' },
    { code: 'CNXMEDIA', label: 'Media', yahooSymbol: '^CNXMEDIA', appSector: 'Media & Entertainment' },
    { code: 'CNXFINANCE', label: 'Financial Svcs', yahooSymbol: '^CNXFINANCE', appSector: 'Financial Services' },
    { code: 'BANKNIFTY', label: 'Bank', yahooSymbol: '^NSEBANK', appSector: 'Banking' },
    { code: 'CNXPSUBANK', label: 'PSU Bank', yahooSymbol: '^CNXPSUBANK', appSector: 'Banking' },
    { code: 'CNXAUTO', label: 'Auto', yahooSymbol: '^CNXAUTO', appSector: 'Automobiles & EV' },
    { code: 'CNXFMCG', label: 'FMCG', yahooSymbol: '^CNXFMCG', appSector: 'FMCG & Consumer' },
  ];

  let sectorIndicesCache: { expiresAt: number; payload: unknown } | null = null;

  app.get('/api/market/sector-indices', async (req, res) => {
    try {
      const force = req.query.refresh === '1';
      if (!force && sectorIndicesCache && sectorIndicesCache.expiresAt > Date.now()) {
        return res.json(sectorIndicesCache.payload);
      }

      const items = await Promise.all(
        NIFTY_SECTOR_INDICES_META.map(async (meta) => {
          const data = await fetchYahooChart(meta.yahooSymbol, '3mo');
          if (!data || data.bars.length < 2) {
            return {
              code: meta.code,
              label: meta.label,
              yahooSymbol: meta.yahooSymbol,
              appSector: meta.appSector,
              lastClose: null,
              retTodayPct: null,
              retWeekPct: null,
              retMonthPct: null,
              asOfDate: null,
              live: false,
            };
          }

          const bars = data.bars;
          const n = bars.length;
          const latest = bars[n - 1];
          const prevDay = bars[n - 2];

          // Week return: vs close 5 trading sessions ago (or start of current ISO week if available)
          const weekBaseIdx = Math.max(0, n - 1 - 5);
          const weekBase = bars[weekBaseIdx];

          // Month return: vs close 21 trading sessions ago
          const monthBaseIdx = Math.max(0, n - 1 - 21);
          const monthBase = bars[monthBaseIdx];

          const pct = (cur: number, base: number) =>
            base > 0 ? Number((((cur - base) / base) * 100).toFixed(2)) : 0;

          return {
            code: meta.code,
            label: meta.label,
            yahooSymbol: meta.yahooSymbol,
            appSector: meta.appSector,
            lastClose: Number(latest.close.toFixed(2)),
            retTodayPct: pct(latest.close, prevDay.close),
            retWeekPct: pct(latest.close, weekBase.close),
            retMonthPct: pct(latest.close, monthBase.close),
            asOfDate: latest.date,
            live: true,
          };
        })
      );

      const payload = {
        fetchedAtIst: nowIstFormatted(),
        liveCount: items.filter((i) => i.live).length,
        indices: items,
      };

      if (payload.liveCount > 0) {
        sectorIndicesCache = {
          expiresAt: Date.now() + 3 * 60 * 1000,
          payload,
        };
      }

      return res.json(payload);
    } catch (err) {
      return res.status(502).json({
        error: err instanceof Error ? err.message : 'Failed to fetch Nifty sector indices',
      });
    }
  });

  /* Yahoo Finance Crumb + Live Fundamentals Cache for any NSE/BSE Stock */
  let yahooAuthCache: { cookie: string; crumb: string; expiresAt: number } | null = null;
  const fundamentalsCache = new Map<string, { expiresAt: number; payload: unknown }>();

  async function getYahooAuth(force = false): Promise<{ cookie: string; crumb: string } | null> {
    if (!force && yahooAuthCache && yahooAuthCache.expiresAt > Date.now()) {
      return { cookie: yahooAuthCache.cookie, crumb: yahooAuthCache.crumb };
    }
    try {
      const cRes = await fetchWithTimeout('https://fc.yahoo.com', { 'User-Agent': BROWSER_UA }, 6000);
      const setCookies =
        typeof cRes.headers.getSetCookie === 'function'
          ? cRes.headers.getSetCookie()
          : (cRes.headers.get('set-cookie') || '').split(/,(?=[^;]+=)/);
      const cookie = setCookies
        .map((c) => c.split(';')[0].trim())
        .filter(Boolean)
        .join('; ');
      if (!cookie) return null;

      const crumbRes = await fetchWithTimeout(
        'https://query1.finance.yahoo.com/v1/test/getcrumb',
        { 'User-Agent': BROWSER_UA, Cookie: cookie },
        6000
      );
      if (!crumbRes.ok) return null;
      const crumb = (await crumbRes.text()).trim();
      if (!crumb || crumb.startsWith('<')) return null;

      yahooAuthCache = { cookie, crumb, expiresAt: Date.now() + 25 * 60 * 1000 };
      return { cookie, crumb };
    } catch {
      return null;
    }
  }

  function calcGrowthPct(curr: number | null, prev: number | null): number | null {
    if (curr === null || prev === null || !Number.isFinite(curr) || !Number.isFinite(prev)) {
      return null;
    }
    if (Math.abs(prev) < 1e-6) return null;
    return Number((((curr - prev) / Math.abs(prev)) * 100).toFixed(2));
  }

  function extractSeriesMap(
    tsResults: Array<Record<string, unknown>>,
    keys: string[]
  ): Map<string, number> {
    const out = new Map<string, number>();
    for (const key of keys) {
      const entry = tsResults.find((r) => {
        const meta = r.meta as { type?: string[] } | undefined;
        return meta?.type?.[0] === key;
      });
      if (!entry) continue;
      const rows = entry[key] as Array<{ asOfDate?: string; reportedValue?: { raw?: number } }> | undefined;
      if (!Array.isArray(rows)) continue;
      for (const row of rows) {
        const d = row.asOfDate;
        const v = row.reportedValue?.raw;
        if (d && typeof v === 'number' && Number.isFinite(v) && !out.has(d)) {
          out.set(d, v);
        }
      }
    }
    return out;
  }

  function computeMetricGrowth(
    qMap: Map<string, number>,
    aMap: Map<string, number>,
    isPerShare = false
  ) {
    const scale = isPerShare ? 1 : 1e7; // Convert INR to ₹ Crores except EPS
    const qDates = Array.from(qMap.keys()).sort();
    const aDates = Array.from(aMap.keys()).sort();

    const latestQDate = qDates[qDates.length - 1] || null;
    const prevQDate = qDates.length >= 2 ? qDates[qDates.length - 2] : null;

    // Match same quarter 1 year earlier (within ±45 days of latestQDate - 365d)
    let yoyQDate: string | null = null;
    if (latestQDate) {
      const targetMs = new Date(`${latestQDate}T00:00:00Z`).getTime() - 365 * 86400 * 1000;
      let bestDiff = 46 * 86400 * 1000;
      for (const d of qDates) {
        if (d === latestQDate) continue;
        const diff = Math.abs(new Date(`${d}T00:00:00Z`).getTime() - targetMs);
        if (diff < bestDiff) {
          bestDiff = diff;
          yoyQDate = d;
        }
      }
    }

    const latestQVal = latestQDate ? Number(((qMap.get(latestQDate) ?? 0) / scale).toFixed(2)) : null;
    const prevQVal = prevQDate ? Number(((qMap.get(prevQDate) ?? 0) / scale).toFixed(2)) : null;
    const yoyQVal = yoyQDate ? Number(((qMap.get(yoyQDate) ?? 0) / scale).toFixed(2)) : null;

    const latestADate = aDates[aDates.length - 1] || null;
    const prevADate = aDates.length >= 2 ? aDates[aDates.length - 2] : null;
    const latestAVal = latestADate ? Number(((aMap.get(latestADate) ?? 0) / scale).toFixed(2)) : null;
    const prevAVal = prevADate ? Number(((aMap.get(prevADate) ?? 0) / scale).toFixed(2)) : null;

    const qoqPct = calcGrowthPct(latestQVal, prevQVal);
    const annualYoYPct = calcGrowthPct(latestAVal, prevAVal);
    const qtrYoYPct = calcGrowthPct(latestQVal, yoyQVal);

    return {
      latestQuarterDate: latestQDate,
      latestQuarterVal: latestQVal,
      qoqPct,
      yoyPct: qtrYoYPct ?? annualYoYPct,
      yoyBasis: qtrYoYPct !== null ? 'Quarterly YoY' : annualYoYPct !== null ? 'Annual FY YoY' : 'N/A',
      latestAnnualDate: latestADate,
      latestAnnualVal: latestAVal,
      annualYoYPct,
    };
  }

  /**
   * Live NSE/BSE Fundamental Ratios & Quarterly/Annual Financials Endpoint
   * Returns Market Cap, P/E, EV/EBITDA, P/B, ROE, Dividend Yield + YoY & QoQ growth on Sales, EBITDA, Net Profit, EPS
   */
  app.get('/api/market/fundamentals/:symbol', async (req, res) => {
    const raw = String(req.params.symbol || '').trim().toUpperCase();
    if (!raw || !/^[A-Z0-9&.\-^]{1,24}$/.test(raw)) {
      return res.status(400).json({ error: 'Invalid symbol format' });
    }

    const cached = fundamentalsCache.get(raw);
    if (cached && cached.expiresAt > Date.now()) {
      return res.json(cached.payload);
    }

    const auth = await getYahooAuth(false);
    if (!auth) {
      return res.status(502).json({ error: 'Unable to authenticate with live fundamentals feed' });
    }

    const candidates = TICKER_YAHOO_FALLBACKS[raw] || (
      raw.endsWith('.NS') || raw.endsWith('.BO') ? [raw] : [`${raw}.NS`, `${raw}.BO`]
    );

    const modules = 'price,summaryDetail,defaultKeyStatistics,financialData,assetProfile,majorHoldersBreakdown';
    const incomeTsTypes = [
      'quarterlyTotalRevenue',
      'quarterlyCostOfRevenue',
      'quarterlyGrossProfit',
      'quarterlyOperatingExpense',
      'quarterlyEBITDA',
      'quarterlyNormalizedEBITDA',
      'quarterlyReconciledDepreciation',
      'quarterlyOperatingIncome',
      'quarterlyEBIT',
      'quarterlyInterestExpense',
      'quarterlyPretaxIncome',
      'quarterlyTaxProvision',
      'quarterlyNetIncome',
      'quarterlyDilutedEPS',
      'quarterlyBasicEPS',
      'annualTotalRevenue',
      'annualCostOfRevenue',
      'annualGrossProfit',
      'annualOperatingExpense',
      'annualEBITDA',
      'annualNormalizedEBITDA',
      'annualReconciledDepreciation',
      'annualOperatingIncome',
      'annualEBIT',
      'annualInterestExpense',
      'annualPretaxIncome',
      'annualTaxProvision',
      'annualNetIncome',
      'annualDilutedEPS',
      'annualBasicEPS',
    ].join(',');

    const bsCfTsTypes = [
      'quarterlyCashCashEquivalentsAndShortTermInvestments',
      'quarterlyCashAndCashEquivalents',
      'quarterlyAccountsReceivable',
      'quarterlyInventory',
      'quarterlyCurrentAssets',
      'quarterlyNetPPE',
      'quarterlyTotalAssets',
      'quarterlyCurrentLiabilities',
      'quarterlyTotalDebt',
      'quarterlyNetDebt',
      'quarterlyTotalLiabilitiesNetMinorityInterest',
      'quarterlyStockholdersEquity',
      'quarterlyRetainedEarnings',
      'quarterlyOperatingCashFlow',
      'quarterlyCapitalExpenditure',
      'quarterlyFreeCashFlow',
      'quarterlyInvestingCashFlow',
      'quarterlyFinancingCashFlow',
      'quarterlyCashDividendsPaid',
      'quarterlyChangesInCash',
      'quarterlyDilutedAverageShares',
      'quarterlyBasicAverageShares',
      'quarterlyOrdinarySharesNumber',
      'annualCashCashEquivalentsAndShortTermInvestments',
      'annualCashAndCashEquivalents',
      'annualAccountsReceivable',
      'annualInventory',
      'annualCurrentAssets',
      'annualNetPPE',
      'annualTotalAssets',
      'annualCurrentLiabilities',
      'annualTotalDebt',
      'annualNetDebt',
      'annualTotalLiabilitiesNetMinorityInterest',
      'annualStockholdersEquity',
      'annualRetainedEarnings',
      'annualOperatingCashFlow',
      'annualCapitalExpenditure',
      'annualFreeCashFlow',
      'annualInvestingCashFlow',
      'annualFinancingCashFlow',
      'annualCashDividendsPaid',
      'annualChangesInCash',
    ].join(',');

    const p1 = Math.floor(Date.now() / 1000) - 86400 * 365 * 5;
    const p2 = Math.floor(Date.now() / 1000);

    for (const sym of candidates) {
      try {
        const qsUrl = `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${encodeURIComponent(sym)}?modules=${modules}&crumb=${encodeURIComponent(auth.crumb)}`;
        const incomeTsUrl = `https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/${encodeURIComponent(sym)}?type=${incomeTsTypes}&period1=${p1}&period2=${p2}&crumb=${encodeURIComponent(auth.crumb)}`;
        const bsCfTsUrl = `https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/${encodeURIComponent(sym)}?type=${bsCfTsTypes}&period1=${p1}&period2=${p2}&crumb=${encodeURIComponent(auth.crumb)}`;
        const headers = { 'User-Agent': BROWSER_UA, Cookie: auth.cookie, Accept: 'application/json' };

        const [qsResp, incResp, bsCfResp] = await Promise.all([
          fetchWithTimeout(qsUrl, headers, 8000),
          fetchWithTimeout(incomeTsUrl, headers, 8000),
          fetchWithTimeout(bsCfTsUrl, headers, 8000),
        ]);

        if (!qsResp.ok) continue;
        const qsJson = (await qsResp.json()) as {
          quoteSummary?: { result?: Array<Record<string, Record<string, { raw?: number } | string>>> };
        };
        const r = qsJson?.quoteSummary?.result?.[0];
        if (!r) continue;

        const num = (obj: Record<string, { raw?: number } | string> | undefined, field: string): number | null => {
          const v = obj?.[field];
          if (v && typeof v === 'object' && typeof v.raw === 'number' && Number.isFinite(v.raw)) {
            return v.raw;
          }
          return null;
        };
        const str = (obj: Record<string, { raw?: number } | string> | undefined, field: string): string => {
          const v = obj?.[field];
          return typeof v === 'string' ? v : '';
        };

        const priceMod = r.price;
        const summaryMod = r.summaryDetail;
        const statsMod = r.defaultKeyStatistics;
        const finMod = r.financialData;
        const profileMod = r.assetProfile;
        const holdersMod = r.majorHoldersBreakdown;

        const mktCapRaw = num(priceMod, 'marketCap') ?? num(summaryMod, 'marketCap');
        const marketCapCr = mktCapRaw ? Number((mktCapRaw / 1e7).toFixed(0)) : null;
        const evRaw = num(statsMod, 'enterpriseValue');
        const enterpriseValueCr = evRaw ? Number((evRaw / 1e7).toFixed(0)) : null;
        const pe = num(summaryMod, 'trailingPE') ?? num(statsMod, 'forwardPE');
        const forwardPe = num(summaryMod, 'forwardPE') ?? num(statsMod, 'forwardPE');
        const pb = num(statsMod, 'priceToBook');
        const ps = num(summaryMod, 'priceToSalesTrailing12Months');
        const evToEbitda = num(statsMod, 'enterpriseToEbitda');
        const evToSales = num(statsMod, 'enterpriseToRevenue');
        const roeRaw = num(finMod, 'returnOnEquity');
        const roaRaw = num(finMod, 'returnOnAssets');
        const divYieldRaw = num(summaryMod, 'dividendYield') ?? num(summaryMod, 'trailingAnnualDividendYield');
        const payoutRatioRaw = num(summaryMod, 'payoutRatio');
        const grossMarginRaw = num(finMod, 'grossMargins');
        const ebitdaMarginRaw = num(finMod, 'ebitdaMargins');
        const opMarginRaw = num(finMod, 'operatingMargins');
        const netMarginRaw = num(finMod, 'profitMargins');
        const debtToEquity = num(finMod, 'debtToEquity');
        const currentRatio = num(finMod, 'currentRatio');
        const quickRatio = num(finMod, 'quickRatio');
        const bookValue = num(statsMod, 'bookValue');
        const trailingEps = num(statsMod, 'trailingEps');
        const beta = num(summaryMod, 'beta') ?? num(statsMod, 'beta');
        const revenueGrowthRaw = num(finMod, 'revenueGrowth');
        const earningsGrowthRaw = num(finMod, 'earningsGrowth');
        const fcfRaw = num(finMod, 'freeCashflow');
        const fcfYieldPct =
          fcfRaw !== null && mktCapRaw && mktCapRaw > 0
            ? Number(((fcfRaw / mktCapRaw) * 100).toFixed(2))
            : null;

        const incJson = incResp.ok
          ? ((await incResp.json()) as { timeseries?: { result?: Array<Record<string, unknown>> } })
          : null;
        const bsCfJson = bsCfResp.ok
          ? ((await bsCfResp.json()) as { timeseries?: { result?: Array<Record<string, unknown>> } })
          : null;
        const tsResults = [
          ...(incJson?.timeseries?.result || []),
          ...(bsCfJson?.timeseries?.result || []),
        ];

        const toCr = (v: number | undefined): number | null =>
          v !== undefined && Number.isFinite(v) ? Number((v / 1e7).toFixed(1)) : null;

        // Build full Income Statement series (Quarterly & Annual)
        const buildIncomeStatement = (prefix: 'quarterly' | 'annual', maxCols: number) => {
          const rev = extractSeriesMap(tsResults, [`${prefix}TotalRevenue`]);
          const cogs = extractSeriesMap(tsResults, [`${prefix}CostOfRevenue`]);
          const gp = extractSeriesMap(tsResults, [`${prefix}GrossProfit`]);
          const opex = extractSeriesMap(tsResults, [`${prefix}OperatingExpense`]);
          const ebitda = extractSeriesMap(tsResults, [
            `${prefix}EBITDA`,
            `${prefix}NormalizedEBITDA`,
            `${prefix}OperatingIncome`,
          ]);
          const depr = extractSeriesMap(tsResults, [`${prefix}ReconciledDepreciation`]);
          const ebit = extractSeriesMap(tsResults, [`${prefix}OperatingIncome`, `${prefix}EBIT`]);
          const interest = extractSeriesMap(tsResults, [`${prefix}InterestExpense`]);
          const pbt = extractSeriesMap(tsResults, [`${prefix}PretaxIncome`]);
          const tax = extractSeriesMap(tsResults, [`${prefix}TaxProvision`]);
          const pat = extractSeriesMap(tsResults, [`${prefix}NetIncome`]);
          const eps = extractSeriesMap(tsResults, [`${prefix}DilutedEPS`, `${prefix}BasicEPS`]);

          const dates = Array.from(new Set([...rev.keys(), ...pat.keys(), ...ebitda.keys()]))
            .sort()
            .slice(-maxCols);

          return {
            rev,
            ebitda,
            ebit,
            pat,
            eps,
            rows: dates.map((date) => {
              const salesCr = toCr(rev.get(date));
              const costOfRevCr = toCr(cogs.get(date));
              const grossProfitCr =
                toCr(gp.get(date)) ??
                (salesCr !== null && costOfRevCr !== null
                  ? Number((salesCr - costOfRevCr).toFixed(1))
                  : null);
              const operatingExpenseCr = toCr(opex.get(date));
              const ebitdaCr = toCr(ebitda.get(date));
              const depreciationCr = toCr(depr.get(date));
              const ebitCr = toCr(ebit.get(date));
              const interestExpenseCr = toCr(interest.get(date));
              const pretaxIncomeCr = toCr(pbt.get(date));
              const taxCr = toCr(tax.get(date));
              const netProfitCr = toCr(pat.get(date));
              const dilutedEps = eps.has(date) ? Number((eps.get(date) ?? 0).toFixed(2)) : null;
              const ebitdaMarginPct =
                salesCr && ebitdaCr !== null && salesCr > 0
                  ? Number(((ebitdaCr / salesCr) * 100).toFixed(1))
                  : null;
              const opMarginPct =
                salesCr && ebitCr !== null && salesCr > 0
                  ? Number(((ebitCr / salesCr) * 100).toFixed(1))
                  : null;
              const netMarginPct =
                salesCr && netProfitCr !== null && salesCr > 0
                  ? Number(((netProfitCr / salesCr) * 100).toFixed(1))
                  : null;

              return {
                date,
                salesCr,
                costOfRevCr,
                grossProfitCr,
                operatingExpenseCr,
                ebitdaCr,
                ebitdaMarginPct,
                depreciationCr,
                ebitCr,
                opMarginPct,
                interestExpenseCr,
                pretaxIncomeCr,
                taxCr,
                netProfitCr,
                netMarginPct,
                dilutedEps,
              };
            }),
          };
        };

        // Build full Balance Sheet series (Quarterly & Annual)
        const buildBalanceSheet = (prefix: 'quarterly' | 'annual', maxCols: number) => {
          const cash = extractSeriesMap(tsResults, [
            `${prefix}CashCashEquivalentsAndShortTermInvestments`,
            `${prefix}CashAndCashEquivalents`,
          ]);
          const receivables = extractSeriesMap(tsResults, [`${prefix}AccountsReceivable`]);
          const inventory = extractSeriesMap(tsResults, [`${prefix}Inventory`]);
          const currentAssets = extractSeriesMap(tsResults, [`${prefix}CurrentAssets`]);
          const netPpe = extractSeriesMap(tsResults, [`${prefix}NetPPE`]);
          const totalAssets = extractSeriesMap(tsResults, [`${prefix}TotalAssets`]);
          const currentLiab = extractSeriesMap(tsResults, [`${prefix}CurrentLiabilities`]);
          const totalDebt = extractSeriesMap(tsResults, [`${prefix}TotalDebt`]);
          const netDebt = extractSeriesMap(tsResults, [`${prefix}NetDebt`]);
          const totalLiab = extractSeriesMap(tsResults, [
            `${prefix}TotalLiabilitiesNetMinorityInterest`,
          ]);
          const equity = extractSeriesMap(tsResults, [`${prefix}StockholdersEquity`]);
          const retained = extractSeriesMap(tsResults, [`${prefix}RetainedEarnings`]);

          const dates = Array.from(
            new Set([...totalAssets.keys(), ...equity.keys(), ...totalDebt.keys()])
          )
            .sort()
            .slice(-maxCols);

          return {
            totalAssets,
            currentLiab,
            equity,
            totalDebt,
            rows: dates.map((date) => {
              const cashCr = toCr(cash.get(date));
              const totalDebtCr = toCr(totalDebt.get(date));
              const netDebtCr =
                toCr(netDebt.get(date)) ??
                (totalDebtCr !== null && cashCr !== null
                  ? Number((totalDebtCr - cashCr).toFixed(1))
                  : null);
              return {
                date,
                cashAndInvCr: cashCr,
                receivablesCr: toCr(receivables.get(date)),
                inventoryCr: toCr(inventory.get(date)),
                currentAssetsCr: toCr(currentAssets.get(date)),
                netPpeCr: toCr(netPpe.get(date)),
                totalAssetsCr: toCr(totalAssets.get(date)),
                currentLiabilitiesCr: toCr(currentLiab.get(date)),
                totalDebtCr,
                netDebtCr,
                totalLiabilitiesCr: toCr(totalLiab.get(date)),
                shareholdersEquityCr: toCr(equity.get(date)),
                retainedEarningsCr: toCr(retained.get(date)),
              };
            }),
          };
        };

        // Build full Cash Flow Statement series (Quarterly & Annual)
        const buildCashFlow = (
          prefix: 'quarterly' | 'annual',
          maxCols: number,
          patMap: Map<string, number>
        ) => {
          const cfo = extractSeriesMap(tsResults, [`${prefix}OperatingCashFlow`]);
          const capex = extractSeriesMap(tsResults, [`${prefix}CapitalExpenditure`]);
          const fcf = extractSeriesMap(tsResults, [`${prefix}FreeCashFlow`]);
          const cfi = extractSeriesMap(tsResults, [`${prefix}InvestingCashFlow`]);
          const cff = extractSeriesMap(tsResults, [`${prefix}FinancingCashFlow`]);
          const divPaid = extractSeriesMap(tsResults, [`${prefix}CashDividendsPaid`]);
          const netChange = extractSeriesMap(tsResults, [`${prefix}ChangesInCash`]);

          const dates = Array.from(new Set([...cfo.keys(), ...fcf.keys(), ...cfi.keys()]))
            .sort()
            .slice(-maxCols);

          return dates.map((date) => {
            const operatingCfCr = toCr(cfo.get(date));
            const capexCr = toCr(capex.get(date));
            const freeCfCr =
              toCr(fcf.get(date)) ??
              (operatingCfCr !== null && capexCr !== null
                ? Number((operatingCfCr + capexCr).toFixed(1))
                : null);
            const patCr = toCr(patMap.get(date));
            const cfoToPatPct =
              operatingCfCr !== null && patCr !== null && patCr > 0
                ? Number(((operatingCfCr / patCr) * 100).toFixed(1))
                : null;
            return {
              date,
              operatingCfCr,
              capexCr,
              freeCfCr,
              investingCfCr: toCr(cfi.get(date)),
              financingCfCr: toCr(cff.get(date)),
              dividendsPaidCr: toCr(divPaid.get(date)),
              netChangeInCashCr: toCr(netChange.get(date)),
              cfoToPatPct,
            };
          });
        };

        const qInc = buildIncomeStatement('quarterly', 6);
        const aInc = buildIncomeStatement('annual', 5);
        const qBs = buildBalanceSheet('quarterly', 6);
        const aBs = buildBalanceSheet('annual', 5);
        const qCf = buildCashFlow('quarterly', 6, qInc.pat);
        const aCf = buildCashFlow('annual', 5, aInc.pat);

        // Compute ROCE % from latest annual EBIT / Capital Employed (Total Assets - Current Liabilities)
        let rocePct: number | null = null;
        const lastAnnualInc = aInc.rows[aInc.rows.length - 1];
        const lastAnnualBs = aBs.rows[aBs.rows.length - 1];
        if (
          lastAnnualInc?.ebitCr !== null &&
          lastAnnualInc?.ebitCr !== undefined &&
          lastAnnualBs?.totalAssetsCr !== null &&
          lastAnnualBs?.totalAssetsCr !== undefined
        ) {
          const capEmp = lastAnnualBs.totalAssetsCr - (lastAnnualBs.currentLiabilitiesCr ?? 0);
          if (capEmp > 0) {
            rocePct = Number(((lastAnnualInc.ebitCr / capEmp) * 100).toFixed(2));
          }
        }

        const salesGrowth = computeMetricGrowth(qInc.rev, aInc.rev, false);
        const ebitdaGrowth = computeMetricGrowth(qInc.ebitda, aInc.ebitda, false);
        const netProfitGrowth = computeMetricGrowth(qInc.pat, aInc.pat, false);
        const epsGrowth = computeMetricGrowth(qInc.eps, aInc.eps, true);

        if (salesGrowth.yoyPct === null && revenueGrowthRaw !== null) {
          salesGrowth.yoyPct = Number((revenueGrowthRaw * 100).toFixed(2));
          salesGrowth.yoyBasis = 'Reported YoY';
        }
        if (netProfitGrowth.yoyPct === null && earningsGrowthRaw !== null) {
          netProfitGrowth.yoyPct = Number((earningsGrowthRaw * 100).toFixed(2));
          netProfitGrowth.yoyBasis = 'Reported YoY';
        }
        if (epsGrowth.yoyPct === null && earningsGrowthRaw !== null) {
          epsGrowth.yoyPct = Number((earningsGrowthRaw * 100).toFixed(2));
          epsGrowth.yoyBasis = 'Reported YoY';
        }

        const quarterlyHistory = qInc.rows.slice(-5).map((row) => ({
          date: row.date,
          salesCr: row.salesCr,
          ebitdaCr: row.ebitdaCr,
          ebitdaMarginPct: row.ebitdaMarginPct,
          netProfitCr: row.netProfitCr,
          eps: row.dilutedEps,
        }));

        const payload = {
          symbol: raw,
          yahooSymbol: sym,
          name: str(priceMod, 'longName') || str(priceMod, 'shortName') || raw,
          sector: str(profileMod, 'sector') || 'Indian Equity',
          industry: str(profileMod, 'industry') || '',
          ratios: {
            marketCapCr,
            enterpriseValueCr,
            pe: pe !== null ? Number(pe.toFixed(2)) : null,
            forwardPe: forwardPe !== null ? Number(forwardPe.toFixed(2)) : null,
            evToEbitda: evToEbitda !== null ? Number(evToEbitda.toFixed(2)) : null,
            evToSales: evToSales !== null ? Number(evToSales.toFixed(2)) : null,
            pb: pb !== null ? Number(pb.toFixed(2)) : null,
            ps: ps !== null ? Number(ps.toFixed(2)) : null,
            roePct: roeRaw !== null ? Number((roeRaw * 100).toFixed(2)) : null,
            roaPct: roaRaw !== null ? Number((roaRaw * 100).toFixed(2)) : null,
            rocePct,
            dividendYieldPct: divYieldRaw !== null ? Number((divYieldRaw * 100).toFixed(2)) : null,
            payoutRatioPct: payoutRatioRaw !== null ? Number((payoutRatioRaw * 100).toFixed(2)) : null,
            fcfYieldPct,
            grossMarginPct: grossMarginRaw !== null ? Number((grossMarginRaw * 100).toFixed(2)) : null,
            ebitdaMarginPct: ebitdaMarginRaw !== null ? Number((ebitdaMarginRaw * 100).toFixed(2)) : null,
            opMarginPct: opMarginRaw !== null ? Number((opMarginRaw * 100).toFixed(2)) : null,
            netMarginPct: netMarginRaw !== null ? Number((netMarginRaw * 100).toFixed(2)) : null,
            debtToEquity: debtToEquity !== null ? Number(debtToEquity.toFixed(2)) : null,
            currentRatio: currentRatio !== null ? Number(currentRatio.toFixed(2)) : null,
            quickRatio: quickRatio !== null ? Number(quickRatio.toFixed(2)) : null,
            bookValuePerShare: bookValue !== null ? Number(bookValue.toFixed(2)) : null,
            trailingEps: trailingEps !== null ? Number(trailingEps.toFixed(2)) : null,
            beta: beta !== null ? Number(beta.toFixed(2)) : null,
          },
          growth: {
            sales: salesGrowth,
            ebitda: ebitdaGrowth,
            netProfit: netProfitGrowth,
            eps: epsGrowth,
          },
          quarterlyHistory,
          shareholdingMeta: (() => {
            const insidersRaw = num(holdersMod, 'insidersPercentHeld') ?? num(statsMod, 'heldPercentInsiders');
            const instRaw = num(holdersMod, 'institutionsPercentHeld') ?? num(statsMod, 'heldPercentInstitutions');
            const sharesMap = extractSeriesMap(tsResults, [
              'quarterlyDilutedAverageShares',
              'quarterlyBasicAverageShares',
              'quarterlyOrdinarySharesNumber',
            ]);
            const shareDates = Array.from(sharesMap.keys()).sort().slice(-5);
            const quarterlySharesCr = shareDates.map((d) => {
              const v = sharesMap.get(d);
              return {
                date: d,
                sharesCr: v !== undefined && Number.isFinite(v) ? Number((v / 1e7).toFixed(2)) : null,
              };
            });
            return {
              insidersPct: insidersRaw !== null ? Number((insidersRaw * 100).toFixed(2)) : null,
              institutionsPct: instRaw !== null ? Number((instRaw * 100).toFixed(2)) : null,
              quarterlySharesCr,
            };
          })(),
          statements: {
            income: {
              annual: aInc.rows,
              quarterly: qInc.rows,
            },
            balanceSheet: {
              annual: aBs.rows,
              quarterly: qBs.rows,
            },
            cashFlow: {
              annual: aCf,
              quarterly: qCf,
            },
          },
        };

        fundamentalsCache.set(raw, { expiresAt: Date.now() + 10 * 60 * 1000, payload });
        return res.json(payload);
      } catch {
        // try next suffix
      }
    }

    return res.status(404).json({ error: `No live fundamentals found for ${raw}` });
  });

  /**
   * Live NSE/BSE Symbol Autocomplete Search (supports any of 2,000+ NSE/BSE listed equities & ETFs)
   */
  app.get('/api/market/search', async (req, res) => {
    const q = String(req.query.q || '').trim();
    if (q.length < 2 || q.length > 40) {
      return res.json({ results: [] });
    }
    try {
      const url = `https://query1.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=15&newsCount=0&enableFuzzyQuery=true`;
      const resp = await fetchWithTimeout(
        url,
        { 'User-Agent': BROWSER_UA, Accept: 'application/json' },
        5000
      );
      if (!resp.ok) return res.json({ results: [] });
      const data = (await resp.json()) as {
        quotes?: Array<{
          symbol?: string;
          shortname?: string;
          longname?: string;
          exchange?: string;
          exchDisp?: string;
          quoteType?: string;
          sector?: string;
        }>;
      };
      const seen = new Set<string>();
      const results = (data.quotes || [])
        .filter((item) => {
          const sym = String(item.symbol || '');
          const exch = String(item.exchange || '').toUpperCase();
          return (
            sym.endsWith('.NS') ||
            sym.endsWith('.BO') ||
            exch === 'NSI' ||
            exch === 'BSE' ||
            exch === 'BOM'
          );
        })
        .map((item) => {
          const rawSym = String(item.symbol || '');
          const cleanTicker = rawSym.replace(/\.(NS|BO)$/i, '').toUpperCase();
          const exchange = rawSym.endsWith('.BO') || item.exchange === 'BSE' ? 'BSE' : 'NSE';
          return {
            ticker: cleanTicker,
            yahooSymbol: rawSym,
            name: String(item.longname || item.shortname || cleanTicker),
            exchange,
            sector: String(item.sector || item.quoteType || 'Indian Equity'),
          };
        })
        .filter((r) => {
          if (!r.ticker || seen.has(r.ticker)) return false;
          seen.add(r.ticker);
          return true;
        })
        .slice(0, 10);

      return res.json({ results });
    } catch {
      return res.json({ results: [] });
    }
  });

  const bhavcopyCache = new Map<
    string,
    { expiresAt: number; payload: Record<string, unknown> }
  >();

  /**
   * Automatic NSE Bhavcopy ZIP Archive Ingestion Endpoint
   * Directly fetches official NSE PR Bhavcopy ZIP (PRddmmyy.zip) and UDiFF CM Bhavcopy ZIP
   * from nsearchives.nseindia.com without requiring manual extraction.
   */
  app.get('/api/bhavcopy/fetch', async (req, res) => {
    const rawDate = typeof req.query.date === 'string' ? req.query.date.trim() : '';
    const forceRefresh = req.query.force === '1' || req.query.force === 'true';

    // Clamp future dates to today (IST) so we never waste requests on dates that do not exist yet
    const nowIst = new Date(Date.now() + 5.5 * 60 * 60 * 1000);
    const todayIstIso = nowIst.toISOString().slice(0, 10);
    let requestedDate: string | undefined = /^\d{4}-\d{2}-\d{2}$/.test(rawDate)
      ? rawDate
      : todayIstIso;
    if (requestedDate > todayIstIso) {
      requestedDate = todayIstIso;
    }

    const cacheKey = requestedDate;
    if (!forceRefresh) {
      const cached = bhavcopyCache.get(cacheKey);
      if (cached && cached.expiresAt > Date.now()) {
        return res.json({ ...cached.payload, cached: true });
      }
    }

    const candidates = getCandidateTradingDates(requestedDate);
    const attemptedUrls: string[] = [];

    // nsearchives.nseindia.com serves Bhavcopy ZIPs directly without www.nseindia.com session cookies
    // (fetching www.nseindia.com and splitting Set-Cookie on ',' corrupts Expires dates and stalls Akamai).
    for (const d of candidates) {
      const ddmmyy = formatDDMMYY(d);
      const yyyymmdd = formatYYYYMMDD(d);
      const isoDate = d.toISOString().slice(0, 10);

      const urls = [
        {
          kind: 'NSE_PR_ZIP' as const,
          filename: `PR${ddmmyy}.zip`,
          url: `https://nsearchives.nseindia.com/archives/equities/bhavcopy/pr/PR${ddmmyy}.zip`,
        },
        {
          kind: 'NSE_UDIFF_ZIP' as const,
          filename: `BhavCopy_NSE_CM_0_0_0_${yyyymmdd}_F_0000.csv.zip`,
          url: `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_${yyyymmdd}_F_0000.csv.zip`,
        },
      ];

      for (const target of urls) {
        attemptedUrls.push(target.url);
        try {
          const resp = await fetchWithTimeout(target.url, NSE_HEADERS, 4500);
          if (!resp.ok) continue;
          const arrayBuf = await resp.arrayBuffer();
          const buf = Buffer.from(arrayBuf);
          if (buf.length > 100 && buf[0] === 0x50 && buf[1] === 0x4b) {
            const payload = {
              liveAvailable: true,
              source: 'nse_live',
              archiveKind: target.kind,
              requestedDate,
              tradeDate: isoDate,
              filename: target.filename,
              sourceUrl: target.url,
              byteLength: buf.length,
              zipBase64: buf.toString('base64'),
              attemptedUrls,
              cached: false,
            };
            bhavcopyCache.set(cacheKey, {
              expiresAt: Date.now() + 15 * 60 * 1000,
              payload,
            });
            return res.json(payload);
          }
        } catch {
          // Continue trying fallback archive URL / prior trading date
        }
      }
    }

    return res.json({
      liveAvailable: false,
      source: 'nse_archive_fallback',
      requestedDate,
      reason:
        'Live NSE archive endpoints (nsearchives.nseindia.com) did not return a ZIP for the requested dates. Loaded full-schema NSE PR Bhavcopy ZIP archive mirror hydrated with live market prices, or upload any official PRddmmyy.zip / BhavCopy_NSE_CM_*.zip directly.',
      attemptedUrls,
    });
  });

  // =========================================================================
  // Free-Tier Server-Side Gemini AI Routes (gemini-4-hydrogen)
  // =========================================================================

  app.post('/api/ai/stock-brief', async (req, res) => {
    try {
      const body = req.body as Record<string, unknown>;
      const ticker = String(body?.ticker || '').trim().toUpperCase().slice(0, 24);
      const snapshot = serializeSnapshotField(body?.snapshot, 4500);
      if (!ticker || !snapshot) {
        return res.status(400).json({ error: 'Stock ticker and snapshot are required.' });
      }
      const prompt = [
        `Generate a concise institutional TechnoFunda Brief for NSE/BSE stock ${ticker} based strictly on this live snapshot:`,
        snapshot,
        '',
        'Format strictly with 4 short sections:',
        '### TechnoFunda Verdict',
        '### Key Bullish Strengths (2-3 bullets)',
        '### Key Risks & Trend Invalidation (2-3 bullets)',
        '### Execution & Monitoring Checklist (2 bullets)',
        'Keep total length under 220 words.',
      ].join('\n');

      const { text, model } = await generateFreeTierAiText(prompt);
      return res.json({
        ticker,
        summary: text || 'No summary generated.',
        model,
        generatedAtIst: new Date().toLocaleTimeString('en-IN', {
          timeZone: 'Asia/Kolkata',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
      });
    } catch (err) {
      return res
        .status(500)
        .json({ error: formatGeminiError(err, 'Failed to generate AI stock brief.') });
    }
  });

  app.post('/api/ai/portfolio-review', async (req, res) => {
    try {
      const body = req.body as Record<string, unknown>;
      const portfolioSnapshot = serializeSnapshotField(body?.portfolioSnapshot, 5000);
      if (!portfolioSnapshot) {
        return res.status(400).json({ error: 'Portfolio snapshot is required.' });
      }
      const prompt = [
        'Review this Indian equity portfolio and its Indicators Matrix Summary Exit & Negative Trend alerts:',
        portfolioSnapshot,
        '',
        'Provide a crisp risk-desk briefing with 3 short sections:',
        '### High-Priority Exit & Stop-Loss Actions',
        '### Sector Concentration & Risk Balance',
        '### Next Risk-Management Steps (2-3 bullets)',
        'Keep total length under 220 words.',
      ].join('\n');

      const { text, model } = await generateFreeTierAiText(prompt);
      return res.json({
        review: text || 'No portfolio review generated.',
        model,
        generatedAtIst: new Date().toLocaleTimeString('en-IN', {
          timeZone: 'Asia/Kolkata',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
      });
    } catch (err) {
      return res
        .status(500)
        .json({ error: formatGeminiError(err, 'Failed to generate AI portfolio review.') });
    }
  });

  app.post('/api/ai/ask', async (req, res) => {
    try {
      const body = req.body as Record<string, unknown>;
      const question = String(body?.question || '').trim().slice(0, 600);
      const contextSummary = String(body?.contextSummary || '').trim().slice(0, 3500);
      const rawHistory = Array.isArray(body?.history) ? body.history.slice(-6) : [];
      if (!question) {
        return res.status(400).json({ error: 'Question is required.' });
      }

      const historyBlock = rawHistory
        .map((m) => {
          const item = m as { role?: string; text?: string };
          const role = item.role === 'assistant' ? 'Analyst' : 'User';
          const text = String(item.text || '').trim().slice(0, 600);
          return text ? `${role}: ${text}` : '';
        })
        .filter(Boolean)
        .join('\n');

      const prompt = [
        contextSummary ? `LIVE TERMINAL CONTEXT:\n${contextSummary}` : '',
        historyBlock ? `RECENT CONVERSATION:\n${historyBlock}` : '',
        `USER QUESTION:\n${question}`,
        '',
        'Respond concisely (under 180 words) using structured bullets where helpful.',
      ]
        .filter(Boolean)
        .join('\n\n');

      const { text, model } = await generateFreeTierAiText(prompt);
      return res.json({
        answer: text || 'No response generated.',
        model,
      });
    } catch (err) {
      return res
        .status(500)
        .json({ error: formatGeminiError(err, 'Failed to answer AI question.') });
    }
  });

  // Guarantee JSON responses for any unmatched /api/* route or Express API middleware error
  app.all('/api/*', (_req, res) => {
    return res.status(404).json({ error: 'API endpoint not found.' });
  });

  app.use(
    (
      err: unknown,
      req: express.Request,
      res: express.Response,
      next: express.NextFunction
    ) => {
      if (req.path.startsWith('/api/')) {
        const msg = err instanceof Error ? err.message : 'Internal API server error.';
        return res.status(500).json({ error: msg });
      }
      return next(err);
    }
  );

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      const idx = path.join(distPath, 'index.html');
      if (fs.existsSync(idx)) res.sendFile(idx);
      else res.status(404).send('Build output not found');
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Personal Trades Terminal server running on http://0.0.0.0:${PORT}`);
    // Pre-warm Tier 1 (123 core leaders + benchmarks) then Tier 2 (all 1,100+ NSE stocks)
    // Delay slightly so cold-start API requests are handled immediately
    setTimeout(() => {
      void fetchLiveUniverse(false)
        .then(() => ensureExtendedHydration(false))
        .catch(() => {});
    }, 1500);
  });
}

void startServer();
