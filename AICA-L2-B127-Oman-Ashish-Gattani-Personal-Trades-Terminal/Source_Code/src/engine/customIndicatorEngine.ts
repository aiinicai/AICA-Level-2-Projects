import { BENCHMARKS } from '../data/indianMarketData';
import {
  BacktestResult,
  BacktestTrade,
  CustomIndicatorDefinition,
  IndianStock,
  OHLCVBar,
} from '../types/market';
import {
  computeAtrSeries,
  computeEmaSeries,
  computeRsiSeries,
  computeSmaSeries,
  computeStdevSeries,
} from './analyticsEngine';
import { calculateIndianDeliveryCost } from './portfolioRiskEngine';

/**
 * Three production-ready initial Custom Indicators with formulas, parameters, and buy/sell signal rules.
 */
export const INITIAL_CUSTOM_INDICATORS: CustomIndicatorDefinition[] = [
  {
    id: 'builtin_ppvdu',
    code: 'PPVDU',
    name: 'Pocket Pivot & Volume Dry-Up Ratio',
    description:
      'Measures institutional accumulation volume relative to the highest down-day volume over p1 sessions, and identifies constructive volume dry-ups below p2× 50D average volume near the 10-EMA.',
    formula: 'volume / max(max_down_vol(p1), 1)',
    buyRule: 'close > open && val > 1.0 && abs(close - ema(close, 10)) / ema(close, 10) < 0.045',
    sellRule: 'close < ema(close, 20) && volume > sma(volume, 50) * p2',
    plotType: 'subchart',
    color: '#10b981',
    param1Name: 'lookback',
    param1Value: 10,
    param2Name: 'distVolMult',
    param2Value: 1.35,
    isBuiltIn: true,
  },
  {
    id: 'builtin_rsmans',
    code: 'RSMANS',
    name: 'Mansfield Relative Strength vs NIFTY 500',
    description:
      'Normalizes the stock-to-NIFTY 500 relative strength ratio against its p1-day moving average. Zero-line cross-ups confirm institutional leadership; breaks below -p2 flag relative weakness.',
    formula: '((rs_ratio / sma(rs_ratio, p1)) - 1) * 100',
    buyRule: 'val > 0 && prev(val, 1) <= 0 && close > sma(close, 50)',
    sellRule: 'val < -p2 || close < sma(close, 50)',
    plotType: 'subchart',
    color: '#3b82f6',
    param1Name: 'rsPeriod',
    param1Value: 50,
    param2Name: 'exitThresh',
    param2Value: 2.5,
    isBuiltIn: true,
  },
  {
    id: 'builtin_atrsqz',
    code: 'ATRSQZ',
    name: 'ATR Volatility Squeeze & Keltner Release',
    description:
      'Ratio of Bollinger Band deviation (2× StDev over p1) to Keltner Channel width (p2× ATR). Values below 1.0 signal a volatility squeeze; releases above 1.0 with close > EMA(p1) trigger momentum breakouts.',
    formula: '(stdev(close, p1) * 2) / max(atr(p1) * p2, 0.01)',
    buyRule: 'val >= 1.0 && prev(val, 1) < 1.0 && close > ema(close, p1)',
    sellRule: 'close < ema(close, p1) && rsi(close, 14) < 48',
    plotType: 'subchart',
    color: '#f59e0b',
    param1Name: 'length',
    param1Value: 20,
    param2Name: 'keltnerMult',
    param2Value: 1.5,
    isBuiltIn: true,
  },
];

interface EvalSeriesContext {
  bars: OHLCVBar[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
  nifty50: number[];
  nifty500: number[];
  rs_ratio: number[];
  p1: number;
  p2: number;
  p1Name: string;
  p2Name: string;
  val?: number[];
}

type TokenType = 'NUM' | 'IDENT' | 'OP' | 'LPAREN' | 'RPAREN' | 'COMMA' | 'EOF';

interface Token {
  type: TokenType;
  value: string;
}

function tokenize(expr: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < expr.length) {
    const ch = expr[i];
    if (/\s/.test(ch)) {
      i++;
      continue;
    }
    if (/[0-9.]/.test(ch)) {
      let num = '';
      while (i < expr.length && /[0-9.]/.test(expr[i])) {
        num += expr[i++];
      }
      tokens.push({ type: 'NUM', value: num });
      continue;
    }
    if (/[a-zA-Z_]/.test(ch)) {
      let id = '';
      while (i < expr.length && /[a-zA-Z0-9_]/.test(expr[i])) {
        id += expr[i++];
      }
      tokens.push({ type: 'IDENT', value: id });
      continue;
    }
    const two = expr.slice(i, i + 2);
    if (['>=', '<=', '==', '!=', '&&', '||'].includes(two)) {
      tokens.push({ type: 'OP', value: two });
      i += 2;
      continue;
    }
    if ('+-*/><!? :'.replace(' ', '').includes(ch)) {
      tokens.push({ type: 'OP', value: ch });
      i++;
      continue;
    }
    if (ch === '(') {
      tokens.push({ type: 'LPAREN', value: ch });
      i++;
      continue;
    }
    if (ch === ')') {
      tokens.push({ type: 'RPAREN', value: ch });
      i++;
      continue;
    }
    if (ch === ',') {
      tokens.push({ type: 'COMMA', value: ch });
      i++;
      continue;
    }
    throw new Error(`Unexpected character "${ch}" at position ${i + 1}`);
  }
  tokens.push({ type: 'EOF', value: '' });
  return tokens;
}

// Vectorized safe recursive-descent evaluator producing a full series (length N)
function evaluateSeriesExpression(expr: string, ctx: EvalSeriesContext): number[] {
  const N = ctx.bars.length;
  const trimmed = expr.trim();
  if (!trimmed) return new Array<number>(N).fill(0);

  const tokens = tokenize(trimmed);
  let pos = 0;

  const peek = () => tokens[pos];
  const consume = () => tokens[pos++];

  const scalarToSeries = (v: number): number[] => new Array<number>(N).fill(v);

  function parseTernary(): number[] {
    const cond = parseOr();
    if (peek().type === 'OP' && peek().value === '?') {
      consume();
      const whenTrue = parseTernary();
      if (!(peek().type === 'OP' && peek().value === ':')) {
        throw new Error('Expected ":" in ternary expression');
      }
      consume();
      const whenFalse = parseTernary();
      return cond.map((c, i) => (c ? whenTrue[i] : whenFalse[i]));
    }
    return cond;
  }

  function parseOr(): number[] {
    let left = parseAnd();
    while (peek().type === 'OP' && peek().value === '||') {
      consume();
      const right = parseAnd();
      left = left.map((a, i) => (a || right[i] ? 1 : 0));
    }
    return left;
  }

  function parseAnd(): number[] {
    let left = parseComparison();
    while (peek().type === 'OP' && peek().value === '&&') {
      consume();
      const right = parseComparison();
      left = left.map((a, i) => (a && right[i] ? 1 : 0));
    }
    return left;
  }

  function parseComparison(): number[] {
    let left = parseAdditive();
    while (
      peek().type === 'OP' &&
      ['>', '<', '>=', '<=', '==', '!='].includes(peek().value)
    ) {
      const op = consume().value;
      const right = parseAdditive();
      left = left.map((a, i) => {
        const b = right[i];
        if (Number.isNaN(a) || Number.isNaN(b)) return 0;
        if (op === '>') return a > b ? 1 : 0;
        if (op === '<') return a < b ? 1 : 0;
        if (op === '>=') return a >= b ? 1 : 0;
        if (op === '<=') return a <= b ? 1 : 0;
        if (op === '==') return Math.abs(a - b) < 1e-9 ? 1 : 0;
        return Math.abs(a - b) >= 1e-9 ? 1 : 0;
      });
    }
    return left;
  }

  function parseAdditive(): number[] {
    let left = parseMultiplicative();
    while (peek().type === 'OP' && (peek().value === '+' || peek().value === '-')) {
      const op = consume().value;
      const right = parseMultiplicative();
      left = left.map((a, i) => (op === '+' ? a + right[i] : a - right[i]));
    }
    return left;
  }

  function parseMultiplicative(): number[] {
    let left = parseUnary();
    while (peek().type === 'OP' && (peek().value === '*' || peek().value === '/')) {
      const op = consume().value;
      const right = parseUnary();
      left = left.map((a, i) => {
        if (op === '*') return a * right[i];
        return right[i] === 0 ? NaN : a / right[i];
      });
    }
    return left;
  }

  function parseUnary(): number[] {
    if (peek().type === 'OP' && peek().value === '-') {
      consume();
      return parseUnary().map((v) => -v);
    }
    if (peek().type === 'OP' && peek().value === '!') {
      consume();
      return parseUnary().map((v) => (v ? 0 : 1));
    }
    return parsePrimary();
  }

  function evalFunction(fnName: string, args: number[][]): number[] {
    const fn = fnName.toLowerCase();
    const getInt = (arr: number[] | undefined, fallback: number) =>
      Math.max(1, Math.min(250, Math.round(arr ? arr[arr.length - 1] : fallback)));

    switch (fn) {
      case 'sma':
        return computeSmaSeries(args[0] ?? ctx.close, getInt(args[1], 20));
      case 'ema':
        return computeEmaSeries(args[0] ?? ctx.close, getInt(args[1], 20));
      case 'rsi':
        return computeRsiSeries(args[0] ?? ctx.close, getInt(args[1], 14));
      case 'stdev':
        return computeStdevSeries(args[0] ?? ctx.close, getInt(args[1], 20));
      case 'atr':
        return computeAtrSeries(ctx.bars, getInt(args[0], 14));
      case 'abs':
        return (args[0] ?? ctx.close).map((v) => Math.abs(v));
      case 'max':
        return (args[0] ?? scalarToSeries(0)).map((v, i) =>
          Math.max(v, args[1]?.[i] ?? v)
        );
      case 'min':
        return (args[0] ?? scalarToSeries(0)).map((v, i) =>
          Math.min(v, args[1]?.[i] ?? v)
        );
      case 'prev': {
        const src = args[0] ?? ctx.close;
        const shift = getInt(args[1], 1);
        return src.map((_, i) => (i >= shift ? src[i - shift] : NaN));
      }
      case 'highest': {
        const src = args[0] ?? ctx.high;
        const period = getInt(args[1], 20);
        return src.map((_, i) => {
          if (i < period - 1) return NaN;
          let mx = -Infinity;
          for (let j = i - period + 1; j <= i; j++) if (src[j] > mx) mx = src[j];
          return mx;
        });
      }
      case 'lowest': {
        const src = args[0] ?? ctx.low;
        const period = getInt(args[1], 20);
        return src.map((_, i) => {
          if (i < period - 1) return NaN;
          let mn = Infinity;
          for (let j = i - period + 1; j <= i; j++) if (src[j] < mn) mn = src[j];
          return mn;
        });
      }
      case 'roc': {
        const src = args[0] ?? ctx.close;
        const period = getInt(args[1], 10);
        return src.map((v, i) =>
          i >= period && src[i - period] !== 0
            ? ((v - src[i - period]) / src[i - period]) * 100
            : NaN
        );
      }
      case 'vwap': {
        const period = getInt(args[0], 20);
        return ctx.bars.map((_, i) => {
          if (i < period - 1) return NaN;
          let pv = 0;
          let vol = 0;
          for (let j = i - period + 1; j <= i; j++) {
            const tp = (ctx.high[j] + ctx.low[j] + ctx.close[j]) / 3;
            pv += tp * ctx.volume[j];
            vol += ctx.volume[j];
          }
          return vol > 0 ? pv / vol : NaN;
        });
      }
      case 'max_down_vol': {
        const period = getInt(args[0], 10);
        return ctx.bars.map((_, i) => {
          if (i < period) return NaN;
          let maxDv = 0;
          for (let j = i - period; j < i; j++) {
            if (ctx.close[j] < ctx.open[j] && ctx.volume[j] > maxDv) {
              maxDv = ctx.volume[j];
            }
          }
          return maxDv > 0 ? maxDv : ctx.volume[i - 1] * 0.8;
        });
      }
      case 'cross_above': {
        const a = args[0] ?? ctx.close;
        const b = args[1] ?? scalarToSeries(0);
        return a.map((v, i) => (i > 0 && v > b[i] && a[i - 1] <= b[i - 1] ? 1 : 0));
      }
      case 'cross_below': {
        const a = args[0] ?? ctx.close;
        const b = args[1] ?? scalarToSeries(0);
        return a.map((v, i) => (i > 0 && v < b[i] && a[i - 1] >= b[i - 1] ? 1 : 0));
      }
      default:
        throw new Error(`Unknown function "${fnName}"`);
    }
  }

  function parsePrimary(): number[] {
    const tok = peek();
    if (tok.type === 'NUM') {
      consume();
      return scalarToSeries(parseFloat(tok.value));
    }
    if (tok.type === 'LPAREN') {
      consume();
      const val = parseTernary();
      if (peek().type !== 'RPAREN') throw new Error('Missing closing ")"');
      consume();
      return val;
    }
    if (tok.type === 'IDENT') {
      consume();
      if (peek().type === 'LPAREN') {
        consume();
        const args: number[][] = [];
        if (peek().type !== 'RPAREN') {
          args.push(parseTernary());
          while (peek().type === 'COMMA') {
            consume();
            args.push(parseTernary());
          }
        }
        if (peek().type !== 'RPAREN') throw new Error(`Missing ")" after ${tok.value}(...)`);
        consume();
        return evalFunction(tok.value, args);
      }

      const id = tok.value.toLowerCase();
      if (id === 'open') return ctx.open;
      if (id === 'high') return ctx.high;
      if (id === 'low') return ctx.low;
      if (id === 'close') return ctx.close;
      if (id === 'volume') return ctx.volume;
      if (id === 'nifty50') return ctx.nifty50;
      if (id === 'nifty500') return ctx.nifty500;
      if (id === 'rs_ratio') return ctx.rs_ratio;
      if (id === 'val' && ctx.val) return ctx.val;
      if (id === 'p1' || (ctx.p1Name && id === ctx.p1Name.toLowerCase())) {
        return scalarToSeries(ctx.p1);
      }
      if (id === 'p2' || (ctx.p2Name && id === ctx.p2Name.toLowerCase())) {
        return scalarToSeries(ctx.p2);
      }
      throw new Error(`Unknown identifier "${tok.value}"`);
    }
    throw new Error(`Unexpected token "${tok.value || 'EOF'}"`);
  }

  const res = parseTernary();
  if (peek().type !== 'EOF') {
    throw new Error(`Unexpected trailing token "${peek().value}"`);
  }
  return res;
}

export interface EvaluatedIndicatorOutput {
  values: number[];
  buySignals: boolean[];
  sellSignals: boolean[];
  latestValue: number;
  latestSignal: 'BUY' | 'SELL' | 'NEUTRAL';
  error?: string;
}

/**
 * Aligns a benchmark OHLCV series to a target stock's exact trading dates with
 * carry-forward fallback so array indexing never overflows or produces NaN when
 * live Yahoo Finance bar counts differ between an equity and NIFTY 50 / NIFTY 500.
 */
function buildAlignedBenchmarkCloses(bars: OHLCVBar[], bmBars: OHLCVBar[]): number[] {
  if (bars.length === 0) return [];
  if (bmBars.length === 0) return new Array<number>(bars.length).fill(1);

  const byDate = new Map<string, number>();
  for (const b of bmBars) {
    if (b.close > 0) byDate.set(b.date, b.close);
  }

  // Fallback starting value: earliest benchmark close
  let lastKnown = bmBars[0].close > 0 ? bmBars[0].close : 1;
  const out = new Array<number>(bars.length);
  for (let i = 0; i < bars.length; i++) {
    const exact = byDate.get(bars[i].date);
    if (exact !== undefined && exact > 0) {
      lastKnown = exact;
    }
    out[i] = lastKnown;
  }
  return out;
}

export function evaluateCustomIndicatorBars(
  bars: OHLCVBar[],
  indicator: CustomIndicatorDefinition
): EvaluatedIndicatorOutput {
  if (!bars || bars.length === 0) {
    return {
      values: [],
      buySignals: [],
      sellSignals: [],
      latestValue: 0,
      latestSignal: 'NEUTRAL',
      error: 'No OHLCV price bars available for this symbol.',
    };
  }

  const n50 = buildAlignedBenchmarkCloses(bars, BENCHMARKS.NIFTY50.bars);
  const n500 = buildAlignedBenchmarkCloses(bars, BENCHMARKS.NIFTY500.bars);
  const close = bars.map((b) => b.close);
  const rs_ratio = close.map((c, i) => (n500[i] > 0 ? (c / n500[i]) * 100 : 0));

  const ctx: EvalSeriesContext = {
    bars,
    open: bars.map((b) => b.open),
    high: bars.map((b) => b.high),
    low: bars.map((b) => b.low),
    close,
    volume: bars.map((b) => b.volume),
    nifty50: n50,
    nifty500: n500,
    rs_ratio,
    p1: Number.isFinite(indicator.param1Value) ? indicator.param1Value : 10,
    p2: Number.isFinite(indicator.param2Value) ? indicator.param2Value : 1.5,
    p1Name: indicator.param1Name,
    p2Name: indicator.param2Name,
  };

  try {
    const values = evaluateSeriesExpression(indicator.formula, ctx);
    ctx.val = values;
    const buyRaw = indicator.buyRule.trim()
      ? evaluateSeriesExpression(indicator.buyRule, ctx)
      : new Array<number>(bars.length).fill(0);
    const sellRaw = indicator.sellRule.trim()
      ? evaluateSeriesExpression(indicator.sellRule, ctx)
      : new Array<number>(bars.length).fill(0);

    const buySignals = buyRaw.map((v) => Boolean(v && !Number.isNaN(v)));
    const sellSignals = sellRaw.map((v) => Boolean(v && !Number.isNaN(v)));

    const lastIdx = values.length - 1;
    const latestValue = Number.isFinite(values[lastIdx])
      ? Number(values[lastIdx].toFixed(3))
      : 0;
    const latestSignal = buySignals[lastIdx]
      ? 'BUY'
      : sellSignals[lastIdx]
      ? 'SELL'
      : 'NEUTRAL';

    return { values, buySignals, sellSignals, latestValue, latestSignal };
  } catch (err) {
    return {
      values: new Array<number>(bars.length).fill(NaN),
      buySignals: new Array<boolean>(bars.length).fill(false),
      sellSignals: new Array<boolean>(bars.length).fill(false),
      latestValue: 0,
      latestSignal: 'NEUTRAL',
      error: err instanceof Error ? err.message : 'Formula syntax error',
    };
  }
}

export function evaluateCustomIndicator(
  stock: IndianStock,
  indicator: CustomIndicatorDefinition
): EvaluatedIndicatorOutput {
  return evaluateCustomIndicatorBars(stock.bars, indicator);
}

/**
 * Full Backtest Engine for any Custom Indicator on an Indian stock (includes Indian delivery transaction costs!)
 */
export function backtestCustomIndicator(
  stock: IndianStock,
  indicator: CustomIndicatorDefinition,
  initialCapitalInr = 10_00_000,
  lookbackDays = 504 // ~2 years
): BacktestResult {
  const bars = stock.bars;
  const evaluated = evaluateCustomIndicatorBars(bars, indicator);

  if (bars.length < 25 || evaluated.error) {
    return {
      ticker: stock.ticker,
      initialCapitalInr,
      finalEquityInr: initialCapitalInr,
      totalReturnPct: 0,
      benchmarkReturnPct: 0,
      cagrPct: 0,
      winRatePct: 0,
      profitFactor: 0,
      maxDrawdownPct: 0,
      sharpeRatio: 0,
      totalTrades: 0,
      totalCostsInr: 0,
      trades: [],
      equityCurve: [],
    };
  }

  const n500Closes = buildAlignedBenchmarkCloses(bars, BENCHMARKS.NIFTY500.bars);
  const startIdx = Math.max(
    0,
    Math.min(bars.length - 2, Math.max(60, bars.length - lookbackDays))
  );

  let cash = initialCapitalInr;
  let shares = 0;
  let entryDate = '';
  let entryPrice = 0;
  let entryCost = 0;
  let entryIdx = 0;
  let totalCostsInr = 0;
  const trades: BacktestTrade[] = [];
  const equityCurve: { date: string; strategyEquity: number; benchmarkEquity: number }[] = [];
  const benchStart = n500Closes[startIdx] > 0 ? n500Closes[startIdx] : 1;

  let peakEquity = initialCapitalInr;
  let maxDrawdownPct = 0;
  const dailyReturns: number[] = [];
  let prevEquity = initialCapitalInr;

  for (let i = startIdx; i < bars.length; i++) {
    const bar = bars[i];
    const isBuy = evaluated.buySignals[i];
    const isSell = evaluated.sellSignals[i];

    if (shares === 0 && isBuy && bar.close > 0 && cash > bar.close) {
      const approxShares = Math.floor((cash * 0.995) / bar.close);
      if (approxShares > 0) {
        const tradeVal = approxShares * bar.close;
        const cost = calculateIndianDeliveryCost(tradeVal, 'BUY', 0);
        cash -= tradeVal + cost.totalCost;
        shares = approxShares;
        entryDate = bar.date;
        entryPrice = bar.close;
        entryCost = cost.totalCost;
        entryIdx = i;
        totalCostsInr += cost.totalCost;
      }
    } else if (shares > 0 && (isSell || i === bars.length - 1)) {
      const tradeVal = shares * bar.close;
      const cost = calculateIndianDeliveryCost(tradeVal, 'SELL', 0);
      cash += tradeVal - cost.totalCost;
      totalCostsInr += cost.totalCost;
      const grossPnl = (bar.close - entryPrice) * shares;
      const netPnl = grossPnl - entryCost - cost.totalCost;
      const retPct = entryPrice * shares > 0 ? (netPnl / (entryPrice * shares)) * 100 : 0;
      trades.push({
        entryDate,
        exitDate: bar.date,
        entryPrice,
        exitPrice: bar.close,
        shares,
        grossPnlInr: Number(grossPnl.toFixed(2)),
        costsInr: Number((entryCost + cost.totalCost).toFixed(2)),
        netPnlInr: Number(netPnl.toFixed(2)),
        returnPct: Number(retPct.toFixed(2)),
        holdingDays: i - entryIdx,
      });
      shares = 0;
    }

    const stratEquity = cash + shares * bar.close;
    const benchClose = n500Closes[i] > 0 ? n500Closes[i] : benchStart;
    const benchEquity = (benchClose / benchStart) * initialCapitalInr;
    if (stratEquity > peakEquity) peakEquity = stratEquity;
    const dd = peakEquity > 0 ? ((peakEquity - stratEquity) / peakEquity) * 100 : 0;
    if (dd > maxDrawdownPct) maxDrawdownPct = dd;

    if (i > startIdx && prevEquity > 0) {
      dailyReturns.push((stratEquity - prevEquity) / prevEquity);
    }
    prevEquity = stratEquity;

    if (i % 3 === 0 || i === bars.length - 1) {
      equityCurve.push({
        date: bar.date,
        strategyEquity: Math.round(stratEquity),
        benchmarkEquity: Math.round(benchEquity),
      });
    }
  }

  const finalEquityInr = Math.max(1, Math.round(cash + shares * bars[bars.length - 1].close));
  const totalReturnPct = Number((((finalEquityInr - initialCapitalInr) / initialCapitalInr) * 100).toFixed(2));
  const benchEnd = n500Closes[bars.length - 1] > 0 ? n500Closes[bars.length - 1] : benchStart;
  const benchmarkReturnPct = Number(
    (((benchEnd - benchStart) / benchStart) * 100).toFixed(2)
  );
  const years = Math.max(0.25, (bars.length - startIdx) / 252);
  const cagrPct = Number(((Math.pow(finalEquityInr / initialCapitalInr, 1 / years) - 1) * 100).toFixed(2));

  const wins = trades.filter((t) => t.netPnlInr > 0);
  const losses = trades.filter((t) => t.netPnlInr <= 0);
  const winRatePct = trades.length > 0 ? Number(((wins.length / trades.length) * 100).toFixed(1)) : 0;
  const grossWin = wins.reduce((s, t) => s + t.netPnlInr, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.netPnlInr, 0));
  const profitFactor = grossLoss > 0 ? Number((grossWin / grossLoss).toFixed(2)) : grossWin > 0 ? 9.99 : 0;

  const avgDaily =
    dailyReturns.length > 0
      ? dailyReturns.reduce((s, r) => s + r, 0) / dailyReturns.length
      : 0;
  const varDaily =
    dailyReturns.length > 1
      ? dailyReturns.reduce((s, r) => s + Math.pow(r - avgDaily, 2), 0) / (dailyReturns.length - 1)
      : 0;
  const stdDaily = Math.sqrt(varDaily);
  const rfDaily = 0.065 / 252; // Indian 10Y G-Sec / T-Bill ~6.5% risk-free rate
  const sharpeRatio = stdDaily > 0 ? Number((((avgDaily - rfDaily) / stdDaily) * Math.sqrt(252)).toFixed(2)) : 0;

  return {
    ticker: stock.ticker,
    initialCapitalInr,
    finalEquityInr,
    totalReturnPct,
    benchmarkReturnPct,
    cagrPct,
    winRatePct,
    profitFactor,
    maxDrawdownPct: Number(maxDrawdownPct.toFixed(2)),
    sharpeRatio,
    totalTrades: trades.length,
    totalCostsInr: Number(totalCostsInr.toFixed(2)),
    trades,
    equityCurve,
  };
}
