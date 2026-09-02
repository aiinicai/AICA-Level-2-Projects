import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  BarChart3, Calendar, ShieldCheck, ArrowRight, TrendingUp, Percent,
  Landmark, Scale, Coins, IndianRupee, Link2, Sparkles, RefreshCw,
} from "lucide-react";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, LabelList,
} from "recharts";
import { api, fmtCr, fmtCrPlain, fmtDate, fmtPct } from "../services/api";
import { useCase } from "../hooks/useCase";
import { CardTitle, EmptyState, ProgressRing, Spinner, StatusChip } from "../components/ui";
import type { Insight, Readiness, RunSummary } from "../types";

const METHOD_META: Record<string, { label: string; color: string; icon: React.ReactNode; bg: string }> = {
  dcf: { label: "Discounted Cash Flow (DCF)", color: "#2563EB", icon: <BarChart3 size={18} />, bg: "bg-primary-50 text-primary" },
  market_multiple: { label: "Market Multiple", color: "#14B8A6", icon: <Scale size={18} />, bg: "bg-mint-bg text-mint-text" },
  adjusted_nav: { label: "Adjusted NAV", color: "#8B5CF6", icon: <Landmark size={18} />, bg: "bg-violet2-bg text-violet2" },
};

function heatColor(v: number | null, min: number, max: number): string {
  if (v === null) return "#F4F7FB";
  const t = max > min ? (v - min) / (max - min) : 0.5;
  // pale slate → teal scale, matching the mockup's "Lower Value → Higher Value"
  const from = [226, 235, 244]; const to = [20, 184, 166];
  const mix = from.map((f, i) => Math.round(f + (to[i] - f) * t));
  return `rgba(${mix[0]}, ${mix[1]}, ${mix[2]}, ${0.35 + t * 0.55})`;
}

export default function Valuations() {
  const { activeCaseId, activeCase } = useCase();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ["valuation", activeCaseId],
    queryFn: () => api.get<{ run: RunSummary | null; readiness: Readiness }>(`/api/valuations/${activeCaseId}/valuation`),
    enabled: !!activeCaseId,
  });
  const { data: runs = [] } = useQuery({
    queryKey: ["runs", activeCaseId],
    queryFn: () => api.get<RunSummary[]>(`/api/valuations/${activeCaseId}/runs`),
    enabled: !!activeCaseId,
  });
  const { data: insights = [] } = useQuery({
    queryKey: ["insights", activeCaseId],
    queryFn: () => api.get<Insight[]>(`/api/valuations/${activeCaseId}/insights`),
    enabled: !!activeCaseId,
  });

  const calculate = useMutation({
    mutationFn: () => api.post(`/api/valuations/${activeCaseId}/calculate`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["valuation", activeCaseId] });
      qc.invalidateQueries({ queryKey: ["runs", activeCaseId] });
      qc.invalidateQueries({ queryKey: ["insights", activeCaseId] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  if (!activeCaseId || isLoading) return <Spinner label="Loading valuation…" />;

  const run = data?.run;
  if (!run) {
    return (
      <EmptyState title="No valuation run yet"
        body="Lock the financials and complete the interview, then run the deterministic valuation engine — DCF, market multiple and adjusted NAV in one pass."
        action={<button className="btn-primary" onClick={() => calculate.mutate()} disabled={calculate.isPending}>
          <Sparkles size={15} /> {calculate.isPending ? "Calculating…" : "Run Valuation Engine"}
        </button>} />
    );
  }

  const detail = run.detail!;
  const methods = detail.result.methods;
  const weights = detail.result.weights;
  const heatmap = detail.sensitivity_heatmap;
  const conf = detail.confidence;
  const inputs = detail.inputs;
  const riskFlags = insights.filter((i) => i.section === "risk_flag").slice(0, 4);
  const rangeWidth = run.central_estimate ? ((run.range_high! - run.range_low!) / run.central_estimate) : 0;

  const chartData = Object.entries(methods).map(([k, m]: [string, any]) => ({
    key: k,
    name: METHOD_META[k]?.label.replace(" (DCF)", "").replace("Discounted Cash Flow", "DCF") ?? k,
    value: m.enterprise_value,
  }));
  const flatVals = heatmap.grid.flat().filter((v): v is number => v !== null);
  const hMin = Math.min(...flatVals); const hMax = Math.max(...flatVals);
  const nearestIdx = (arr: number[], target: number) =>
    arr.reduce((best, v, i) => (Math.abs(v - target) < Math.abs(arr[best] - target) ? i : best), 0);
  const selCol = nearestIdx(heatmap.wacc_values, inputs.wacc ?? 0.12);
  const selRow = nearestIdx(heatmap.growth_values, inputs.terminal_growth ?? 0.03);

  const assumptions: [React.ReactNode, string, string][] = [
    [<TrendingUp size={14} key="a" />, "Revenue CAGR (Forecast)", fmtPct(inputs.revenue_growth, 0)],
    [<Percent size={14} key="b" />, "EBITDA Margin", fmtPct(inputs.ebitda_margin, 0)],
    [<Coins size={14} key="c" />, "Tax Rate", fmtPct(inputs.tax_rate, 0)],
    [<Scale size={14} key="d" />, "WACC", fmtPct(inputs.wacc, 1)],
    [<TrendingUp size={14} key="e" />, "Terminal Growth Rate", fmtPct(inputs.terminal_growth, 1)],
    [<Link2 size={14} key="f" />, "EV/EBITDA Multiple", `${(inputs.ev_ebitda_multiple ?? 0).toFixed(1)}x`],
  ];

  return (
    <div className="space-y-4">
      {/* headline row */}
      <div className="grid grid-cols-5 gap-4">
        <div className="card-pad">
          <p className="text-[13px] font-semibold text-slate2 flex items-center gap-1.5">Indicative Valuation Range</p>
          <p className="text-[21px] font-extrabold text-navy mt-2 leading-tight">
            {fmtCr(run.range_low)} – {fmtCr(run.range_high)}
          </p>
          <p className="text-xs text-slate2 mt-2 flex items-center gap-2">
            Range Width: {fmtPct(rangeWidth)}
            <span className={rangeWidth < 0.6 ? "chip-mint" : "chip-warn"}>{rangeWidth < 0.6 ? "Healthy" : "Wide"}</span>
          </p>
        </div>
        <div className="card-pad">
          <p className="text-[13px] font-semibold text-slate2">Central Estimate</p>
          <p className="text-[26px] font-extrabold text-navy mt-2">{fmtCr(run.central_estimate)}</p>
          <p className="text-xs text-slate2 mt-2">Weighted midpoint of methods</p>
        </div>
        <div className="card-pad flex items-center gap-3.5">
          <ProgressRing value={conf.score} size={76} stroke={8} color="#10B981">
            <span className="text-base font-extrabold text-navy">{conf.score}%</span>
          </ProgressRing>
          <div>
            <p className="text-[13px] font-semibold text-slate2">Valuation Confidence</p>
            <p className="text-[15px] font-extrabold text-mint-text mt-0.5">{run.confidence_label}</p>
            <p className="text-[11px] text-slate3 mt-0.5 leading-tight">Method agreement {conf.basis.method_agreement}% · data {conf.basis.data_verification}%</p>
          </div>
        </div>
        <div className="card-pad flex items-start gap-3.5">
          <span className="h-11 w-11 rounded-xl bg-primary-50 text-primary flex items-center justify-center"><Calendar size={19} /></span>
          <div>
            <p className="text-[13px] font-semibold text-slate2">Last Updated</p>
            <p className="text-[15px] font-extrabold text-navy mt-0.5">{fmtDate(run.created_at, true)}</p>
            <p className="text-[11px] text-slate3 mt-0.5">Auto-saved</p>
          </div>
        </div>
        <div className="card-pad flex items-start gap-3.5">
          <span className="h-11 w-11 rounded-xl bg-mint-bg text-mint-text flex items-center justify-center"><ShieldCheck size={19} /></span>
          <div>
            <p className="text-[13px] font-semibold text-slate2">Valuation Readiness</p>
            <p className="text-[24px] font-extrabold text-navy leading-7">{data!.readiness.score}%</p>
            <p className="text-[12px] font-bold text-mint-text">{data!.readiness.band}</p>
          </div>
        </div>
      </div>

      {/* method cards + assumptions */}
      <div className="grid grid-cols-4 gap-4">
        {Object.entries(methods).map(([key, m]: [string, any], idx) => {
          const meta = METHOD_META[key];
          return (
            <div key={key} className="card-pad">
              <div className="flex items-center gap-3">
                <span className={`h-10 w-10 rounded-xl flex items-center justify-center ${meta.bg}`}>{meta.icon}</span>
                <div className="flex-1">
                  <p className="text-[13.5px] font-bold text-navy">{meta.label}</p>
                  <p className="text-lg font-extrabold text-navy">{fmtCr(m.enterprise_value)}</p>
                </div>
                {idx === 0 && <span className="chip-mint">Primary Method</span>}
              </div>
              <ul className="mt-4 space-y-2 text-[12.5px]">
                <li className="flex justify-between"><span className="text-slate2">Enterprise Value</span>
                  <span className="font-bold">{idx === 0 ? fmtPct(weights[key], 0) : <span className="chip-blue">{fmtPct(weights[key], 0)}</span>}</span></li>
                <li className="flex justify-between"><span className="text-slate2">Implied Equity Value</span>
                  <span className="font-bold text-navy">{fmtCr(m.equity_value)}</span></li>
                <li className="flex justify-between"><span className="text-slate2">Per Share Value</span>
                  <span className="font-bold text-navy">₹ {m.per_share_value ? m.per_share_value.toFixed(2) : "—"}</span></li>
                <li className="flex justify-between"><span className="text-slate2">{key === "dcf" ? "Key Driver" : key === "market_multiple" ? "Multiple Used" : "NAV Type"}</span>
                  <span className="font-bold text-navy">{key === "market_multiple" ? m.multiple_used : key === "adjusted_nav" ? m.nav_type : m.key_driver}</span></li>
              </ul>
              <button className="btn-ghost-blue mt-4" onClick={() => navigate("/simulation")}>
                View Details <ArrowRight size={13} />
              </button>
            </div>
          );
        })}

        <div className="card-pad">
          <CardTitle tip="Accepted assumptions driving the current run.">Key Assumptions</CardTitle>
          <ul className="divide-y divide-line/70">
            {assumptions.map(([icon, label, v]) => (
              <li key={label} className="flex items-center gap-2.5 py-2 text-[12.5px]">
                <span className="text-slate3">{icon}</span>
                <span className="text-slate2">{label}</span>
                <span className="ml-auto font-bold text-navy">{v}</span>
              </li>
            ))}
          </ul>
          <button className="btn-ghost-blue mt-3" onClick={() => navigate("/simulation")}>
            View All Assumptions <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* bottom row */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-4 card-pad">
          <CardTitle tip="Enterprise value by method with range bounds."
            right={<button className="btn-secondary !py-1 !px-2.5 text-xs" onClick={() => calculate.mutate()} disabled={calculate.isPending}>
              <RefreshCw size={12} className={calculate.isPending ? "animate-spin" : ""} /> Recalculate</button>}>
            Method Comparison
          </CardTitle>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} margin={{ top: 22, right: 12, bottom: 0, left: -14 }}>
              <CartesianGrid stroke="#EDF1F7" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#8A97AB" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#8A97AB" }} axisLine={false} tickLine={false} tickFormatter={(v) => (v / 1e7).toFixed(1)} />
              <Tooltip formatter={(v: number) => fmtCr(v)} />
              <ReferenceLine y={run.range_high!} stroke="#2563EB" strokeDasharray="5 4"
                label={{ value: `High: ${fmtCr(run.range_high)}`, position: "insideTopRight", fontSize: 10, fill: "#2563EB", fontWeight: 700 }} />
              <ReferenceLine y={run.range_low!} stroke="#14B8A6" strokeDasharray="5 4"
                label={{ value: `Low: ${fmtCr(run.range_low)}`, position: "insideBottomRight", fontSize: 10, fill: "#0B8F6B", fontWeight: 700 }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={44}>
                {chartData.map((d) => <Cell key={d.key} fill={METHOD_META[d.key]?.color} />)}
                <LabelList dataKey="value" position="top" formatter={(v: number) => fmtCrPlain(v)}
                  style={{ fontSize: 11, fontWeight: 700, fill: "#0F1F3D" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="col-span-4 card-pad">
          <CardTitle tip="DCF equity value across WACC × terminal growth.">Sensitivity Analysis (DCF)</CardTitle>
          <div className="text-center text-[11px] font-bold text-slate2 mb-1">WACC</div>
          <div className="flex">
            <div className="flex items-center">
              <span className="-rotate-90 text-[11px] font-bold text-slate2 whitespace-nowrap w-4">Terminal Growth Rate</span>
            </div>
            <table className="flex-1 border-separate" style={{ borderSpacing: 3 }}>
              <thead>
                <tr>
                  <th className="text-[11px] text-slate3 font-semibold" />
                  {heatmap.wacc_values.map((w) => (
                    <th key={w} className="text-[11px] text-slate2 font-bold pb-1">{fmtPct(w, 1)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmap.grid.map((row, ri) => (
                  <tr key={ri}>
                    <td className="text-[11px] text-slate2 font-bold pr-1.5 text-right">{fmtPct(heatmap.growth_values[ri], 1)}</td>
                    {row.map((v, ci) => (
                      <td key={ci}
                        className={`text-center text-[11.5px] font-bold text-navy rounded-md px-1.5 py-2 ${ri === selRow && ci === selCol ? "ring-2 ring-primary bg-surface" : ""}`}
                        style={{ background: ri === selRow && ci === selCol ? undefined : heatColor(v, hMin, hMax) }}>
                        {v === null ? "—" : fmtCrPlain(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-2 mt-3 text-[11px] text-slate3">
            <span>Lower Value</span>
            <span className="flex-1 h-2 rounded-full" style={{ background: "linear-gradient(to right, #E2EBF4, #14B8A6)" }} />
            <span>Higher Value</span>
          </div>
        </div>

        <div className="col-span-2 card-pad">
          <CardTitle tip="From the deterministic rules engine.">Risk Highlights</CardTitle>
          <ul className="space-y-3">
            {(riskFlags.length ? riskFlags : [{ id: "none", title: "No open risk flags", body: "All rule checks are within thresholds.", severity: "positive" } as Insight]).map((r) => (
              <li key={r.id} className="flex items-start gap-2.5">
                <span className={`h-8 w-8 shrink-0 rounded-lg flex items-center justify-center ${
                  r.severity === "high" ? "bg-risk-bg text-risk-text" : r.severity === "moderate" ? "bg-warn-bg text-warn-text" : "bg-mint-bg text-mint-text"}`}>
                  <ShieldCheck size={15} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[12.5px] font-bold text-navy flex items-center justify-between gap-2">
                    <span className="truncate">{r.title}</span>
                    <StatusChip status={r.severity} />
                  </p>
                  <p className="text-[11px] text-slate3 leading-snug mt-0.5">{r.body.slice(0, 60)}{r.body.length > 60 ? "…" : ""}</p>
                </div>
              </li>
            ))}
          </ul>
          <button className="btn-ghost-blue mt-4" onClick={() => navigate("/insights")}>
            View All Risks <ArrowRight size={13} />
          </button>
        </div>

        <div className="col-span-2 card-pad">
          <CardTitle>Recent Valuation Runs</CardTitle>
          <ol className="relative ml-2 border-l-2 border-line space-y-4 pl-4 py-1">
            {runs.slice(0, 4).map((r, i) => (
              <li key={r.id} className="relative">
                <span className={`absolute -left-[23px] top-1 h-3 w-3 rounded-full ring-4 ring-surface ${i === 0 ? "bg-primary" : "bg-line"}`} />
                <p className="text-[12px] font-bold text-navy flex items-center gap-2">
                  {fmtDate(r.created_at, true)}
                  {i === 0 && <span className="chip-blue">Current Run</span>}
                </p>
                <p className="text-[11px] text-slate3">Analyst: {r.analyst || "Arjun Demo"} · {fmtCr(r.enterprise_value)}</p>
                <p className="text-[10.5px] text-slate3">Methods: DCF, MM, NAV</p>
              </li>
            ))}
          </ol>
          <button className="btn-ghost-blue mt-3">View All Runs <ArrowRight size={13} /></button>
        </div>
      </div>
    </div>
  );
}
