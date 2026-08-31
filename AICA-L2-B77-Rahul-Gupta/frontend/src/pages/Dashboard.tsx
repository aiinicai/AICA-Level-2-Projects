import { useQuery, useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Briefcase, CheckCircle2, Clock, IndianRupee, ShieldCheck, ArrowRight,
  TrendingUp, Percent, Scale, Lightbulb, FileText, Download, ChevronDown,
  BarChart3, Sparkles,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, LabelList, Area, AreaChart,
} from "recharts";
import { api, downloadReport, fmtCr, fmtCrPlain, fmtDate, fmtPct } from "../services/api";
import { useCase } from "../hooks/useCase";
import { CardTitle, ProgressRing, Spinner, StatusChip } from "../components/ui";
import type { CaseSummary, DashboardData, Insight, RunSummary } from "../types";

const METHOD_LABEL: Record<string, string> = {
  dcf: "DCF", market_multiple: "Market Multiple", adjusted_nav: "NAV",
};
const METHOD_COLOR: Record<string, string> = {
  dcf: "#2563EB", market_multiple: "#14B8A6", adjusted_nav: "#8B5CF6",
};

function StatCard({ icon, iconBg, title, value, sub, subClass = "text-slate2", link }: any) {
  return (
    <div className="card-pad flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <span className={`h-11 w-11 rounded-xl flex items-center justify-center ${iconBg}`}>{icon}</span>
        <div>
          <p className="text-[22px] font-extrabold text-navy leading-6">{value}</p>
          <p className="text-[13px] font-semibold text-slate2">{title}</p>
        </div>
      </div>
      {link ? (
        <Link to={link.to} className="text-xs font-semibold text-primary flex items-center gap-1 hover:underline">
          {link.label} <ArrowRight size={12} />
        </Link>
      ) : (
        <p className={`text-xs font-semibold ${subClass}`}>{sub}</p>
      )}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { activeCaseId } = useCase();
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/api/dashboard"),
  });
  const { data: caseDetail } = useQuery({
    queryKey: ["case", activeCaseId],
    queryFn: () => api.get<CaseSummary>(`/api/valuations/${activeCaseId}`),
    enabled: !!activeCaseId,
  });
  const { data: insights = [] } = useQuery({
    queryKey: ["insights", activeCaseId],
    queryFn: () => api.get<Insight[]>(`/api/valuations/${activeCaseId}/insights`),
    enabled: !!activeCaseId,
  });
  const { data: valuation } = useQuery({
    queryKey: ["valuation", activeCaseId],
    queryFn: () => api.get<{ run: RunSummary | null }>(`/api/valuations/${activeCaseId}/valuation`),
    enabled: !!activeCaseId,
  });

  const download = useMutation({
    mutationFn: async () => {
      const rep = await api.post<{ id: string; has_pdf: boolean; title?: string }>(
        `/api/valuations/${activeCaseId}/reports`,
        { template: "comprehensive", options: { ai_narrative: true } },
      );
      // not window.open: generation takes many seconds, so the popup would be
      // blocked for running outside the user-gesture window (see downloadReport)
      await downloadReport(rep.id, rep.has_pdf, rep.title);
    },
  });

  if (isLoading || !data) return <Spinner label="Loading dashboard…" />;

  const run = valuation?.run ?? null;
  const readiness = caseDetail?.readiness;
  const keyInsights = insights.filter((i) => ["positive_driver", "key_insight", "risk_flag"].includes(i.section)).slice(0, 4);
  const pctCompleted = data.total_cases ? ((data.completed / data.total_cases) * 100).toFixed(1) : "0";
  const pctProgress = data.total_cases ? ((data.in_progress / data.total_cases) * 100).toFixed(1) : "0";
  const readinessComponents: [string, number][] = readiness
    ? [
        ["Data Completeness", readiness.components.data_completeness],
        ["Financial Quality", readiness.components.financial_verification],
        ["Assumption Clarity", readiness.components.forecast_inputs],
        ["Model Consistency", readiness.components.business_interview],
      ]
    : [];
  const simInputs = run?.detail?.inputs;

  return (
    <div className="space-y-5">
      {/* stat row */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard icon={<Briefcase size={19} className="text-primary" />} iconBg="bg-primary-50"
          title="Valuation Cases" value={data.total_cases}
          link={{ to: "/valuations", label: "View all cases" }} />
        <StatCard icon={<CheckCircle2 size={19} className="text-mint-text" />} iconBg="bg-mint-bg"
          title="Completed" value={data.completed} sub={`${pctCompleted}% of total`} />
        <StatCard icon={<Clock size={19} className="text-warn-text" />} iconBg="bg-warn-bg"
          title="In Progress" value={data.in_progress} sub={`${pctProgress}% of total`} />
        <StatCard icon={<IndianRupee size={19} className="text-primary" />} iconBg="bg-primary-50"
          title="Avg Valuation" value={fmtCr(data.avg_valuation)} sub="Across all cases" />
        <StatCard icon={<ShieldCheck size={19} className="text-mint-text" />} iconBg="bg-mint-bg"
          title="Valuation Readiness" value={`${Math.round(data.readiness)}%`}
          sub="Excellent" subClass="text-mint-text" />
      </div>

      {/* middle row */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-5 card-pad">
          <CardTitle right={<Link to="/valuations" className="text-xs font-semibold text-primary flex items-center gap-1">View all <ArrowRight size={12} /></Link>}>
            Recent Valuations
          </CardTitle>
          <table className="w-full">
            <thead>
              <tr>
                <th className="table-th">Company / Case</th>
                <th className="table-th">Status</th>
                <th className="table-th text-right">Valuation</th>
                <th className="table-th">Method</th>
                <th className="table-th">Updated On</th>
              </tr>
            </thead>
            <tbody>
              {data.recent.slice(0, 5).map((c) => (
                <tr key={c.id} className="hover:bg-page/50">
                  <td className="table-td font-semibold">{c.company_name}</td>
                  <td className="table-td"><StatusChip status={c.status} /></td>
                  <td className="table-td text-right font-semibold">
                    {fmtCr(c.current_run?.enterprise_value)}
                  </td>
                  <td className="table-td text-slate2">
                    {Array.isArray(c.current_run?.methods) && c.current_run.methods.length
                      ? METHOD_LABEL[c.current_run.methods[0]] ?? "DCF"
                      : "—"}
                  </td>
                  <td className="table-td text-slate2">{fmtDate(c.current_run?.created_at ?? c.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-slate3 mt-3">Showing {Math.min(5, data.recent.length)} of {data.total_cases} cases</p>
        </div>

        <div className="col-span-4 card-pad">
          <CardTitle icon={<TrendingUp size={16} className="text-primary" />}>Valuation Trend (All Cases)</CardTitle>
          <ResponsiveContainer width="100%" height={210}>
            <AreaChart data={data.trend} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <defs>
                <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563EB" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#EDF1F7" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#8A97AB" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#8A97AB" }} axisLine={false} tickLine={false}
                tickFormatter={(v) => (v / 1e7).toFixed(1)} />
              <Tooltip formatter={(v: number) => fmtCr(v)} labelStyle={{ fontWeight: 600 }} />
              <Area type="monotone" dataKey="value" stroke="#2563EB" strokeWidth={2.5}
                fill="url(#trendFill)" dot={{ r: 3.5, fill: "#2563EB", strokeWidth: 2, stroke: "#fff" }} />
            </AreaChart>
          </ResponsiveContainer>
          <p className="text-[11px] text-slate3 text-center">— Average Valuation (₹ Cr)</p>
        </div>

        <div className="col-span-3 card-pad">
          <CardTitle icon={<BarChart3 size={16} className="text-primary" />}>Method Comparison</CardTitle>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={data.method_comparison.map((m) => ({
              name: METHOD_LABEL[m.method] ?? m.method,
              value: m.value, color: METHOD_COLOR[m.method] ?? "#2563EB",
            }))} margin={{ top: 18, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="#EDF1F7" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10.5, fill: "#8A97AB" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#8A97AB" }} axisLine={false} tickLine={false}
                tickFormatter={(v) => (v / 1e7).toFixed(1)} />
              <Tooltip formatter={(v: number) => fmtCr(v)} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={34}>
                {data.method_comparison.map((m, i) => (
                  <Cell key={i} fill={METHOD_COLOR[m.method] ?? "#2563EB"} />
                ))}
                <LabelList dataKey="value" position="top"
                  formatter={(v: number) => fmtCrPlain(v)} style={{ fontSize: 11, fontWeight: 700, fill: "#0F1F3D" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-[11px] text-slate3 text-center">Values in ₹ Cr (Avg Valuation)</p>
        </div>
      </div>

      {/* bottom row */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-3 card-pad">
          <CardTitle tip="Explainable completeness score — see components below.">Valuation Readiness</CardTitle>
          <div className="flex items-center gap-4">
            <ProgressRing value={readiness?.score ?? 0} size={116} stroke={12} gradient>
              <span className="text-2xl font-extrabold text-navy">{readiness?.score ?? 0}%</span>
              <span className="text-[11px] font-bold text-mint-text">{readiness?.label ?? ""}</span>
            </ProgressRing>
            <ul className="space-y-2">
              {readinessComponents.map(([label, v], i) => (
                <li key={label} className="flex items-center gap-2 text-[12px]">
                  <span className={`h-2 w-2 rounded-full ${["bg-primary", "bg-teal2", "bg-violet2", "bg-mint"][i]}`} />
                  <span className="text-slate2">{label}</span>
                  <span className="font-bold text-navy ml-auto">{v}%</span>
                </li>
              ))}
            </ul>
          </div>
          <span className="chip-mint mt-3">Excellent</span>
          <p className="text-xs text-slate3 mt-2">Keep it up! Your data quality is excellent.</p>
        </div>

        <div className="col-span-3 card-pad">
          <CardTitle tip="Read-only view of the current base-case assumptions.">Simulation Summary <span className="text-slate3 font-medium text-xs">(Base Case)</span></CardTitle>
          {simInputs ? (
            <>
              {[
                ["Revenue Growth", simInputs.revenue_growth, TrendingUp],
                ["EBITDA Margin", simInputs.ebitda_margin, Percent],
                ["WACC", simInputs.wacc, Scale],
              ].map(([label, v, Icon]: any) => (
                <div key={label} className="flex items-center gap-2.5 mb-2.5">
                  <Icon size={14} className="text-slate2 shrink-0" />
                  <span className="text-[12.5px] text-slate2 w-28">{label}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden">
                    <div className="h-full bg-primary rounded-full" style={{ width: `${Math.min((v ?? 0) * 400, 100)}%` }} />
                  </div>
                  <span className="text-[12.5px] font-bold text-navy w-10 text-right">{fmtPct(v, 0)}</span>
                </div>
              ))}
              <div className="border-t border-line mt-3 pt-3 flex items-baseline justify-between">
                <span className="text-[13px] text-slate2">Company Value</span>
                <span className="text-lg font-extrabold text-mint-text">{fmtCr(run?.enterprise_value)}</span>
              </div>
              <p className="text-[11px] text-slate3 text-right">
                Range: {fmtCr(run?.range_low)} – {fmtCr(run?.range_high)}
              </p>
              <button className="btn-ghost-blue mt-3 !bg-mint-bg !text-mint-text !border-mint-bg"
                onClick={() => navigate("/simulation")}>
                Open Simulation Lab <ArrowRight size={14} />
              </button>
            </>
          ) : (
            <p className="text-sm text-slate2">Run a valuation to see the simulation summary.</p>
          )}
        </div>

        <div className="col-span-3 card-pad">
          <CardTitle icon={<Lightbulb size={16} className="text-warn" />}>Key Insights</CardTitle>
          <ul className="space-y-3">
            {keyInsights.map((i) => (
              <li key={i.id} className="flex gap-2.5">
                <span className={`mt-0.5 h-6 w-6 shrink-0 rounded-lg flex items-center justify-center ${
                  i.severity === "positive" ? "bg-mint-bg text-mint-text"
                  : i.severity === "high" ? "bg-risk-bg text-risk-text"
                  : i.severity === "moderate" ? "bg-warn-bg text-warn-text"
                  : "bg-primary-50 text-primary"}`}>
                  <Sparkles size={13} />
                </span>
                <p className="text-[12.5px] text-slate2 leading-snug">
                  <span className="font-semibold text-navy">{i.title}. </span>
                  {i.body.length > 90 ? i.body.slice(0, 90) + "…" : i.body}
                </p>
              </li>
            ))}
          </ul>
          <button className="btn-ghost-blue mt-4" onClick={() => navigate("/insights")}>
            View AI Insights <ArrowRight size={14} />
          </button>
        </div>

        <div className="col-span-3 card-pad flex flex-col">
          <CardTitle icon={<FileText size={16} className="text-primary" />}>Report Preview</CardTitle>
          <div className="flex-1 rounded-xl border border-line bg-page/70 p-4 text-[11px] overflow-hidden">
            <p className="text-primary font-bold text-[10px]">CompanyVal AI · Valuation Report</p>
            <p className="text-navy font-extrabold text-sm mt-1.5">{caseDetail?.company_name}</p>
            <p className="text-slate2">Comprehensive Valuation Analysis</p>
            <p className="text-slate3 mt-1">Valuation Date: {fmtDate(caseDetail?.valuation_date)}</p>
            <div className="mt-2.5 rounded-lg bg-surface border border-line p-2.5">
              <p className="font-bold text-navy text-[10.5px] mb-1">Executive Summary</p>
              <ul className="list-disc ml-4 space-y-0.5 text-slate2">
                <li>Fair enterprise value {fmtCr(run?.range_low)} – {fmtCr(run?.range_high)}</li>
                <li>Central estimate of {fmtCr(run?.central_estimate)}</li>
                <li>{run?.confidence_label ?? "—"} · Readiness {Math.round(run?.readiness_score ?? 0)}%</li>
              </ul>
            </div>
          </div>
          <button className="btn-primary w-full mt-4" onClick={() => download.mutate()} disabled={download.isPending}>
            <Download size={15} /> {download.isPending ? "Generating…" : "Download Full Report"}
          </button>
        </div>
      </div>
    </div>
  );
}
