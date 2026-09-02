import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, Percent, Scale, Link2, RotateCcw, Activity, ArrowRight,
  ArrowUp, ArrowDown, Minus, Lightbulb,
} from "lucide-react";
import { api, fmtCr, fmtPct } from "../services/api";
import { useCase } from "../hooks/useCase";
import { CardTitle, EmptyState, Spinner } from "../components/ui";
import type { RunSummary, Readiness, SimulationResult } from "../types";

interface SliderDef {
  key: string;
  label: string;
  icon: React.ReactNode;
  min: number;
  max: number;
  step: number;
  kind: "pct" | "x";
}

const SLIDERS: SliderDef[] = [
  { key: "revenue_growth", label: "Revenue Growth (CAGR)", icon: <TrendingUp size={15} />, min: 0.05, max: 0.25, step: 0.005, kind: "pct" },
  { key: "ebitda_margin", label: "EBITDA Margin", icon: <Percent size={15} />, min: 0.05, max: 0.30, step: 0.005, kind: "pct" },
  { key: "wacc", label: "WACC", icon: <Scale size={15} />, min: 0.06, max: 0.16, step: 0.0025, kind: "pct" },
  { key: "terminal_growth", label: "Terminal Growth Rate", icon: <Activity size={15} />, min: 0.0, max: 0.06, step: 0.0025, kind: "pct" },
  { key: "ev_ebitda_multiple", label: "EV / EBITDA Multiple (Exit)", icon: <Link2 size={15} />, min: 6, max: 16, step: 0.25, kind: "x" },
];

const SCENARIO_META = [
  { key: "bear", label: "Bear Case", emoji: "🐻", cls: "text-risk-text bg-risk-bg" },
  { key: "base", label: "Base Case", emoji: "⚖️", cls: "text-mint-text bg-mint-bg" },
  { key: "bull", label: "Bull Case", emoji: "🐂", cls: "text-primary bg-primary-50" },
];

function fmtVal(v: number, kind: "pct" | "x", decimals = 1): string {
  return kind === "pct" ? `${(v * 100).toFixed(v * 100 % 1 === 0 ? 0 : decimals)}%` : `${v.toFixed(1)}x`;
}

export default function SimulationLab() {
  const { activeCaseId } = useCase();
  const navigate = useNavigate();
  const [values, setValues] = useState<Record<string, number> | null>(null);
  const [sim, setSim] = useState<SimulationResult | null>(null);
  const [simError, setSimError] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout>>();

  const { data } = useQuery({
    queryKey: ["valuation", activeCaseId],
    queryFn: () => api.get<{ run: RunSummary | null; readiness: Readiness }>(`/api/valuations/${activeCaseId}/valuation`),
    enabled: !!activeCaseId,
  });
  const run = data?.run ?? null;

  const baseValues = useMemo(() => {
    if (!run?.detail) return null;
    const i = run.detail.inputs;
    return {
      revenue_growth: i.revenue_growth ?? 0.16,
      ebitda_margin: i.ebitda_margin ?? 0.18,
      wacc: i.wacc ?? 0.12,
      terminal_growth: i.terminal_growth ?? 0.03,
      ev_ebitda_multiple: i.ev_ebitda_multiple ?? 8.5,
    } as Record<string, number>;
  }, [run]);

  useEffect(() => {
    if (baseValues && !values) setValues(baseValues);
  }, [baseValues, values]);

  // debounced deterministic simulation — no AI calls, ever
  useEffect(() => {
    if (!values || !activeCaseId) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        setSimError("");
        const r = await api.post<SimulationResult>(`/api/valuations/${activeCaseId}/simulate`, { overrides: values });
        setSim(r);
      } catch (e) {
        setSimError((e as Error).message);
      }
    }, 220);
    return () => clearTimeout(timer.current);
  }, [values, activeCaseId]);

  if (!activeCaseId || !data) return <Spinner label="Loading simulation lab…" />;
  if (!run || !baseValues || !values) {
    return <EmptyState title="Run a valuation first"
      body="The Simulation Lab models live what-if changes against the current base-case valuation."
      action={<button className="btn-primary" onClick={() => navigate("/valuations")}>Go to Valuations <ArrowRight size={14} /></button>} />;
  }

  const scenarios = sim?.scenarios ?? run.detail!.scenarios;
  const tornado = sim?.tornado ?? run.detail!.tornado;
  const impacts = sim?.assumption_impacts ?? run.detail!.assumption_impacts;
  const ev = sim?.enterprise_value ?? run.enterprise_value!;
  const equity = sim?.equity_value ?? run.equity_value!;
  const bridge = sim?.bridge ?? run.detail!.result.bridge;
  const perShare = sim?.per_share_value ?? run.per_share_value;
  const vsCurrent = sim?.vs_current_pct ?? 0;
  const maxSpan = Math.max(...tornado.map((t) => t.span), 1);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-12 gap-4 items-start">
        {/* sliders */}
        <div className="col-span-5 card-pad">
          <CardTitle right={
            <button className="text-xs font-semibold text-primary flex items-center gap-1.5" onClick={() => setValues(baseValues)}>
              <RotateCcw size={13} /> Reset to Defaults
            </button>}>
            Base Case Assumptions
          </CardTitle>
          <div className="space-y-5">
            {SLIDERS.map((s) => {
              const v = values[s.key];
              const fill = ((v - s.min) / (s.max - s.min)) * 100;
              return (
                <div key={s.key}>
                  <div className="flex items-center gap-2.5">
                    <span className="h-8 w-8 rounded-lg bg-primary-50 text-primary flex items-center justify-center shrink-0">{s.icon}</span>
                    <span className="text-[13px] font-semibold text-navy flex-1">{s.label}</span>
                    <span className="rounded-lg border border-line bg-page/60 px-2.5 py-1 text-[13px] font-extrabold text-navy min-w-[54px] text-center">
                      {fmtVal(v, s.kind)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-2 pl-10">
                    <span className="text-[10.5px] text-slate3 w-7">{fmtVal(s.min, s.kind, 0)}</span>
                    <input type="range" className="cv-slider flex-1" min={s.min} max={s.max} step={s.step}
                      value={v} style={{ ["--fill" as any]: `${fill}%` }}
                      aria-label={s.label}
                      onChange={(e) => setValues((prev) => ({ ...prev!, [s.key]: Number(e.target.value) }))} />
                    <span className="text-[10.5px] text-slate3 w-8 text-right">{fmtVal(s.max, s.kind, 0)}</span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-5 rounded-lg bg-primary-50/60 border border-primary-100/50 px-3.5 py-2.5 text-[12px] text-primary-700 flex items-center gap-2">
            <Activity size={13} /> Changes update results in real time — deterministic Python engine, no AI calls.
          </div>
          {simError && <p className="text-xs text-risk-text mt-2">{simError}</p>}
        </div>

        {/* company value */}
        <div className="col-span-3 card-pad">
          <CardTitle tip="Weighted central estimate under the current slider values.">Company Value <span className="text-xs text-slate3 font-medium">(Simulated)</span></CardTitle>
          <p className="text-[13px] text-slate2">Enterprise Value</p>
          <p className="text-[30px] font-extrabold text-mint-text leading-9">{fmtCr(ev)}</p>
          <p className="text-[11.5px] text-slate3 mt-0.5">Range: {fmtCr(sim?.range_low ?? run.range_low)} – {fmtCr(sim?.range_high ?? run.range_high)}</p>
          <span className={`mt-2.5 ${vsCurrent > 0.001 ? "chip-mint" : vsCurrent < -0.001 ? "chip-risk" : "chip-blue"} inline-flex items-center gap-1`}>
            {vsCurrent > 0.001 ? <ArrowUp size={11} /> : vsCurrent < -0.001 ? <ArrowDown size={11} /> : <Minus size={11} />}
            {fmtPct(Math.abs(vsCurrent ?? 0))} vs. Current Valuation
          </span>
          <ul className="mt-4 space-y-2 text-[12.5px] border-t border-line pt-3.5">
            <li className="flex justify-between"><span className="text-slate2">Total Debt</span><span className="font-bold text-navy">{fmtCr(bridge.total_debt)}</span></li>
            <li className="flex justify-between"><span className="text-slate2">Cash & Equivalents</span><span className="font-bold text-navy">{fmtCr(bridge.cash)}</span></li>
            <li className="flex justify-between"><span className="text-slate2 font-semibold">Equity Value</span><span className="font-extrabold text-mint-text">{fmtCr(equity)}</span></li>
            <li className="flex justify-between"><span className="text-slate2">Shares Outstanding</span><span className="font-bold text-navy">{bridge.shares_outstanding ? `${(bridge.shares_outstanding / 100000).toFixed(2)} L` : "—"}</span></li>
            <li className="flex justify-between border-t border-line pt-2"><span className="text-slate2 font-semibold">Implied Value per Share</span><span className="font-extrabold text-navy">₹ {perShare ? perShare.toFixed(2) : "—"}</span></li>
          </ul>
          <button className="btn-ghost-blue mt-4" onClick={() => navigate("/valuations")}>
            View Detailed Breakdown <ArrowRight size={13} />
          </button>
        </div>

        {/* scenarios */}
        <div className="col-span-4 card-pad">
          <CardTitle tip="Preset bear/base/bull assumption sets recomputed live.">Scenario Comparison</CardTitle>
          <div className="grid grid-cols-3 gap-3">
            {SCENARIO_META.map(({ key, label, emoji, cls }) => {
              const sc = scenarios[key];
              if (!sc) return null;
              const vs = sc.vs_base_pct ?? 0;
              return (
                <div key={key} className="rounded-xl2 border border-line p-3.5 text-center">
                  <span className={`mx-auto h-10 w-10 rounded-full flex items-center justify-center text-lg ${cls}`}>{emoji}</span>
                  <p className="text-[13px] font-bold text-navy mt-2">{label}</p>
                  <p className={`text-[17px] font-extrabold mt-1 ${key === "bear" ? "text-risk-text" : key === "bull" ? "text-mint-text" : "text-navy"}`}>
                    {fmtCr(sc.enterprise_value)}
                  </p>
                  <p className={`text-[11.5px] font-bold ${vs > 0.001 ? "text-mint-text" : vs < -0.001 ? "text-risk-text" : "text-slate3"}`}>
                    {vs > 0.001 ? "↑" : vs < -0.001 ? "↓" : "—"} {fmtPct(Math.abs(vs))}
                  </p>
                  <ul className="mt-2.5 space-y-1 text-left text-[10.5px] text-slate2 border-t border-line/70 pt-2">
                    <li className="flex justify-between"><span>Rev. Growth</span><b>{fmtPct(sc.assumptions.revenue_growth, 0)}</b></li>
                    <li className="flex justify-between"><span>EBITDA Margin</span><b>{fmtPct(sc.assumptions.ebitda_margin, 0)}</b></li>
                    <li className="flex justify-between"><span>WACC</span><b>{fmtPct(sc.assumptions.wacc, 0)}</b></li>
                    <li className="flex justify-between"><span>EV/EBITDA Exit</span><b>{sc.assumptions.ev_ebitda_multiple?.toFixed(1)}x</b></li>
                    <li className="flex justify-between"><span>Terminal Growth</span><b>{fmtPct(sc.assumptions.terminal_growth, 1)}</b></li>
                  </ul>
                </div>
              );
            })}
          </div>
          <button className="btn-ghost-blue mt-4">Manage Scenarios <ArrowRight size={13} /></button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4 items-start">
        {/* tornado */}
        <div className="col-span-6 card-pad">
          <CardTitle tip="One-at-a-time swings of each assumption around the base value."
            right={<span className="text-xs font-semibold text-slate3">Tornado (EV)</span>}>
            Sensitivity Analysis <span className="text-xs text-slate3 font-medium">(Live)</span>
          </CardTitle>
          <div className="relative">
            <p className="text-center text-[11px] text-slate3 mb-2">
              <span className="mr-24">Lower</span>
              <span className="font-bold text-navy">Base: {fmtCr(tornado[0]?.base ?? ev)}</span>
              <span className="ml-24">Higher</span>
            </p>
            <div className="space-y-3">
              {tornado.map((t) => {
                const base = t.base;
                const lowSpan = t.low !== null ? Math.abs(base - t.low) : 0;
                const highSpan = t.high !== null ? Math.abs((t.high ?? base) - base) : 0;
                const half = 50;
                return (
                  <div key={t.key} className="flex items-center gap-3 text-[12px]">
                    <span className="w-44 text-slate2 font-medium truncate">{t.label}</span>
                    <span className="w-16 text-right font-semibold text-navy">{fmtCr(Math.min(t.low ?? base, t.high ?? base))}</span>
                    <div className="flex-1 relative h-4">
                      <div className="absolute inset-y-0 left-1/2 w-px bg-slate3/50 border-l border-dashed border-slate3" />
                      <div className="absolute inset-y-0 bg-primary-100 rounded-l"
                        style={{ right: "50%", width: `${(lowSpan / maxSpan) * half}%` }} />
                      <div className="absolute inset-y-0 bg-primary rounded-r"
                        style={{ left: "50%", width: `${(highSpan / maxSpan) * half}%` }} />
                    </div>
                    <span className="w-16 font-semibold text-navy">{fmtCr(Math.max(t.low ?? base, t.high ?? base))}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-5 mt-4 text-[11px] text-slate2">
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-primary-100" /> Low Scenario</span>
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-primary" /> High Scenario</span>
              <button className="btn-primary !py-1.5 !px-3 text-xs ml-auto" onClick={() => navigate("/valuations")}>
                Run Full Sensitivity <ArrowRight size={12} />
              </button>
            </div>
          </div>
        </div>

        {/* impact table */}
        <div className="col-span-6 card-pad">
          <CardTitle tip="Directional impact of standard assumption changes."
            right={<span className="text-xs font-semibold text-slate3">vs. Base Case</span>}>
            Impact of Assumption Changes
          </CardTitle>
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-th">Assumption</th>
                <th className="table-th">Change</th>
                <th className="table-th text-right">EV Impact</th>
                <th className="table-th text-right">% Impact</th>
              </tr>
            </thead>
            <tbody>
              {impacts.map((row) => (
                <tr key={row.key}>
                  <td className="table-td font-semibold">{row.label}</td>
                  <td className="table-td"><span className="chip-mint">{row.change}</span></td>
                  <td className={`table-td text-right font-bold ${row.impact >= 0 ? "text-mint-text" : "text-risk-text"}`}>
                    {row.impact >= 0 ? "+ " : "− "}{fmtCr(Math.abs(row.impact))}
                  </td>
                  <td className={`table-td text-right font-bold ${row.impact >= 0 ? "text-mint-text" : "text-risk-text"}`}>
                    {fmtPct(row.impact_pct, 1, true)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-4 rounded-lg bg-warn-bg/50 border border-warn/30 px-3.5 py-2.5 text-[12px] text-warn-text flex items-center gap-2">
            <Lightbulb size={13} /> Assumptions with the highest positive impact drive the most value.
          </div>
        </div>
      </div>
    </div>
  );
}
