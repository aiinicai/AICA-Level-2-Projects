/** Display-only TypeScript mirror of the deterministic Python valuation engine,
 * used ONLY in the static GitHub Pages preview so the Simulation Lab stays live.
 *
 * The authoritative engine is backend/app/services/valuation/engine.py — this file
 * is a faithful port of its arithmetic (5-yr FCFF DCF, EV/EBITDA multiple, constant
 * NAV, weighted central estimate, scenarios, tornado, impact table) over the
 * snapshotted base-case inputs. It never persists anything.
 */

export interface EngineInputs {
  base_revenue: number;
  ebitda_margin: number;
  depreciation_pct: number;
  capex_pct: number;
  nwc_pct: number;
  tax_rate: number;
  revenue_growth: number;
  wacc: number;
  terminal_growth: number;
  total_debt: number;
  cash: number;
  shares_outstanding: number;
  ev_ebitda_multiple: number;
}

export interface EngineContext {
  inputs: EngineInputs;
  weights: Record<string, number>; // dcf / market_multiple / adjusted_nav
  navEquity: number | null; // adjusted NAV equity — independent of the sliders
  baseRunEv: number; // persisted current-run EV, for "vs current" deltas
}

const FORECAST_YEARS = 5;

function dcf(inp: EngineInputs): { ev: number; equity: number } {
  if (inp.wacc <= inp.terminal_growth) {
    throw new Error("WACC must exceed terminal growth rate");
  }
  let revenue = inp.base_revenue;
  let prevNwc = inp.nwc_pct * revenue;
  let pvSum = 0;
  let fcffLast = 0;
  for (let t = 1; t <= FORECAST_YEARS; t++) {
    revenue = revenue * (1 + inp.revenue_growth);
    const ebitda = revenue * inp.ebitda_margin;
    const dep = revenue * inp.depreciation_pct;
    const ebit = ebitda - dep;
    const tax = Math.max(ebit, 0) * inp.tax_rate;
    const nopat = ebit - tax;
    const capex = revenue * inp.capex_pct;
    const nwc = revenue * inp.nwc_pct;
    const deltaNwc = nwc - prevNwc;
    prevNwc = nwc;
    const fcff = nopat + dep - capex - deltaNwc;
    pvSum += fcff / Math.pow(1 + inp.wacc, t);
    fcffLast = fcff;
  }
  const tv = (fcffLast * (1 + inp.terminal_growth)) / (inp.wacc - inp.terminal_growth);
  const ev = pvSum + tv / Math.pow(1 + inp.wacc, FORECAST_YEARS);
  return { ev, equity: ev - inp.total_debt + inp.cash };
}

function marketMultiple(inp: EngineInputs): { ev: number; equity: number } {
  const ev = inp.base_revenue * inp.ebitda_margin * inp.ev_ebitda_multiple;
  return { ev, equity: ev - inp.total_debt + inp.cash };
}

interface RunResult {
  methods: Record<string, { enterprise_value: number; equity_value: number }>;
  weights: Record<string, number>;
  central_ev: number;
  central_equity: number;
  range_low: number;
  range_high: number;
  per_share: number | null;
}

export function runValuation(ctx: EngineContext, inp: EngineInputs): RunResult {
  const methods: RunResult["methods"] = { dcf: dcfToMethod(inp) };
  if (inp.ev_ebitda_multiple) {
    const mm = marketMultiple(inp);
    methods.market_multiple = { enterprise_value: mm.ev, equity_value: mm.equity };
  }
  if (ctx.navEquity !== null) {
    methods.adjusted_nav = {
      enterprise_value: ctx.navEquity + inp.total_debt - inp.cash,
      equity_value: ctx.navEquity,
    };
  }
  // normalise weights over available methods (mirrors run_valuation)
  const raw = Object.fromEntries(Object.keys(methods).map((m) => [m, ctx.weights[m] ?? 0]));
  const total = Object.values(raw).reduce((s, w) => s + w, 0);
  const weights = Object.fromEntries(
    Object.entries(raw).map(([m, w]) => [m, total > 0 ? w / total : 1 / Object.keys(methods).length]),
  );
  const evs = Object.entries(methods).map(([m, r]) => [m, r.enterprise_value] as const);
  const eqs = Object.entries(methods).map(([m, r]) => [m, r.equity_value] as const);
  const centralEv = evs.reduce((s, [m, v]) => s + v * weights[m], 0);
  const centralEq = eqs.reduce((s, [m, v]) => s + v * weights[m], 0);
  return {
    methods,
    weights,
    central_ev: centralEv,
    central_equity: centralEq,
    range_low: Math.min(...evs.map(([, v]) => v)),
    range_high: Math.max(...evs.map(([, v]) => v)),
    per_share: inp.shares_outstanding ? centralEq / inp.shares_outstanding : null,
  };
}

function dcfToMethod(inp: EngineInputs) {
  const r = dcf(inp);
  return { enterprise_value: r.ev, equity_value: r.equity };
}

const TORNADO_SPEC: [keyof EngineInputs, string, number][] = [
  ["revenue_growth", "Revenue Growth (CAGR)", 0.02],
  ["ebitda_margin", "EBITDA Margin", 0.02],
  ["ev_ebitda_multiple", "EV / EBITDA Multiple (Exit)", 1.0],
  ["wacc", "WACC", 0.01],
  ["terminal_growth", "Terminal Growth Rate", 0.005],
];

const IMPACT_SPEC: [keyof EngineInputs, string, number, string][] = [
  ["revenue_growth", "Revenue Growth (CAGR)", +0.02, "+2%"],
  ["ebitda_margin", "EBITDA Margin", +0.02, "+2%"],
  ["wacc", "WACC", -0.01, "-1%"],
  ["ev_ebitda_multiple", "EV / EBITDA Multiple (Exit)", +1.0, "+1.0x"],
  ["terminal_growth", "Terminal Growth Rate", +0.005, "+0.5%"],
];

const SCENARIO_DELTAS: Record<string, Partial<Record<keyof EngineInputs, number>>> = {
  bear: { revenue_growth: -0.06, ebitda_margin: -0.04, wacc: +0.02, terminal_growth: -0.01, ev_ebitda_multiple: -2.0 },
  base: {},
  bull: { revenue_growth: +0.06, ebitda_margin: +0.03, wacc: -0.02, terminal_growth: +0.01, ev_ebitda_multiple: +2.0 },
};

function scenarioInputs(inp: EngineInputs, preset: string): EngineInputs {
  const out = { ...inp };
  for (const [k, d] of Object.entries(SCENARIO_DELTAS[preset] ?? {})) {
    (out as any)[k] = (out as any)[k] + d;
  }
  out.terminal_growth = Math.max(out.terminal_growth, 0);
  out.ebitda_margin = Math.max(out.ebitda_margin, 0.01);
  if (out.wacc <= out.terminal_growth) out.wacc = out.terminal_growth + 0.02;
  return out;
}

function tryCentralEv(ctx: EngineContext, inp: EngineInputs): number | null {
  try {
    return runValuation(ctx, inp).central_ev;
  } catch {
    return null;
  }
}

/** Mirrors POST /api/valuations/{id}/simulate for the static preview. */
export function simulateStatic(ctx: EngineContext, overrides: Record<string, number>) {
  const inp: EngineInputs = { ...ctx.inputs };
  for (const [k, v] of Object.entries(overrides)) {
    if (v !== null && v !== undefined && k in inp) (inp as any)[k] = v;
  }
  const base = runValuation(ctx, inp);

  const tornado = TORNADO_SPEC.map(([key, label, delta]) => {
    const lo = tryCentralEv(ctx, { ...inp, [key]: (inp[key] as number) - delta });
    const hi = tryCentralEv(ctx, { ...inp, [key]: (inp[key] as number) + delta });
    const span = Math.abs((hi ?? base.central_ev) - (lo ?? base.central_ev));
    return { key, label, delta, low: lo, high: hi, base: base.central_ev, span };
  }).filter((r) => r.low !== null || r.high !== null)
    .sort((a, b) => b.span - a.span);

  const impacts = IMPACT_SPEC.map(([key, label, delta, change]) => {
    const v = tryCentralEv(ctx, { ...inp, [key]: (inp[key] as number) + delta });
    if (v === null) return null;
    return {
      key, label, change,
      impact: v - base.central_ev,
      impact_pct: base.central_ev ? (v - base.central_ev) / base.central_ev : null,
    };
  }).filter((r): r is NonNullable<typeof r> => r !== null)
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

  const scenarios: Record<string, unknown> = {};
  for (const name of ["bear", "base", "bull"]) {
    const sInp = scenarioInputs(inp, name);
    const r = runValuation(ctx, sInp);
    scenarios[name] = {
      assumptions: {
        revenue_growth: sInp.revenue_growth,
        ebitda_margin: sInp.ebitda_margin,
        wacc: sInp.wacc,
        terminal_growth: sInp.terminal_growth,
        ev_ebitda_multiple: sInp.ev_ebitda_multiple,
      },
      enterprise_value: r.central_ev,
      equity_value: r.central_equity,
      vs_base_pct: base.central_ev ? (r.central_ev - base.central_ev) / base.central_ev : null,
    };
  }

  return {
    enterprise_value: base.central_ev,
    equity_value: base.central_equity,
    per_share_value: base.per_share,
    range_low: base.range_low,
    range_high: base.range_high,
    methods: base.methods,
    bridge: {
      total_debt: inp.total_debt,
      cash: inp.cash,
      shares_outstanding: inp.shares_outstanding,
    },
    vs_current_pct: ctx.baseRunEv ? (base.central_ev - ctx.baseRunEv) / ctx.baseRunEv : null,
    tornado,
    assumption_impacts: impacts,
    scenarios,
  };
}
