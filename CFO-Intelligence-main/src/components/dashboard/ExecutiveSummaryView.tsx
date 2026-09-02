import React, { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Sparkles,
  AlertTriangle,
  Award,
  Lightbulb,
  DollarSign,
  PieChart as PieIcon,
  Activity,
  CheckCircle2,
  Edit3,
  Save,
  ArrowUpRight,
  ArrowDownRight,
  Flame,
  FileSpreadsheet,
  FileText,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  FinancialModel,
  KpiMetric,
  CfoCommentary,
  WinHighlight,
  RedFlagAlert,
  OpportunityInsight,
} from '../../types';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface ExecutiveSummaryViewProps {
  model: FinancialModel;
  kpis: KpiMetric[];
  commentary: CfoCommentary;
  wins?: WinHighlight[];
  concerns?: string[];
  redFlags?: RedFlagAlert[];
  opportunities?: OpportunityInsight[];
  onOpenMetricExplain?: (metric: KpiMetric) => void;
  onUpdateCommentary?: (newCommentary: CfoCommentary) => void;
  onRegenerateAi?: () => void;
  onOpenAskCfo?: () => void;
  onNavigateToTab?: (tab: any) => void;
  firmName?: string;
}

export const ExecutiveSummaryView: React.FC<ExecutiveSummaryViewProps> = ({
  model,
  kpis,
  commentary,
  wins: propWins,
  redFlags: propRedFlags,
  opportunities: propOpportunities,
  onOpenMetricExplain,
  onUpdateCommentary,
  onRegenerateAi,
  onOpenAskCfo,
  onNavigateToTab,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const client = model.client;
  const latestMonth = model.historicalMonthly[model.historicalMonthly.length - 1] || {} as any;
  const prevMonth = model.historicalMonthly[model.historicalMonthly.length - 2] || latestMonth;

  const [isEditingCommentary, setIsEditingCommentary] = useState(false);
  const [editedCommentary, setEditedCommentary] = useState<CfoCommentary>(commentary);
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);

  const formatCurrency = (val: number) => {
    if (!val && val !== 0) return '$0';
    if (Math.abs(val) >= 1_000_000) {
      return `${client.currencySymbol}${(val / 1_000_000).toFixed(2)}M`;
    }
    return `${client.currencySymbol}${(val / 1_000).toFixed(0)}k`;
  };

  const handleSaveCommentary = () => {
    if (onUpdateCommentary) {
      onUpdateCommentary(editedCommentary);
    }
    setIsEditingCommentary(false);
  };

  const handleAiRefresh = async () => {
    if (onRegenerateAi) {
      setIsGeneratingAi(true);
      await onRegenerateAi();
      setIsGeneratingAi(false);
    }
  };

  // Trajectory Chart Data
  const chartData = model.historicalMonthly.map(m => ({
    name: m.periodLabel,
    Revenue: m.revenue,
    GrossProfit: m.grossProfit,
    EBITDA: m.ebitda,
    NetIncome: m.netIncome,
    Cash: m.cashAndEquivalents,
  }));

  // Fallback Wins if not explicitly passed
  const wins: WinHighlight[] = propWins || [
    {
      id: 'w1',
      title: 'Gross Margin Expansion',
      metric: `${latestMonth.grossMarginPercent?.toFixed(1)}% Gross Margin`,
      change: '+3.2% vs Baseline',
      businessImpact: 'Pricing optimization and clinical throughput improvements contributed $18.4k in incremental gross profit.',
      category: 'margin',
    },
    {
      id: 'w2',
      title: 'Operating Cash Inflow',
      metric: `${formatCurrency(latestMonth.operatingCashFlow || 45000)} OCF`,
      change: 'Positive OCF',
      businessImpact: 'Operating cash flow remained comfortably positive, funding all minor equipment upgrades organically.',
      category: 'cash',
    },
    {
      id: 'w3',
      title: 'DSO Collection Cycle Tightening',
      metric: `${Math.round(latestMonth.dso || 38)} Days DSO`,
      change: '-4 Days Faster',
      businessImpact: 'Accounts receivable days dropped, releasing liquid working capital back to reserve accounts.',
      category: 'efficiency',
    },
  ];

  // Fallback Red Flags if not explicitly passed
  const redFlags: RedFlagAlert[] = propRedFlags || [
    {
      id: 'rf1',
      severity: 'high',
      title: 'Rising Personnel OPEX Ratio',
      metric: 'Salaries & Benefits / Revenue',
      currentValue: '46.8%',
      threshold: '< 42.0%',
      impact: 'Staffing overhead has risen faster than patient service volumes over the past 60 days.',
      recommendation: 'Evaluate overtime scheduling, re-negotiate locum rates, and link variable incentives directly to billable production.',
      category: 'expenses',
    },
    {
      id: 'rf2',
      severity: 'medium',
      title: 'Concentration in Top Payer Contract',
      metric: 'Payer A % of Total AR',
      currentValue: '34.2%',
      threshold: '< 25.0%',
      impact: 'Delays in commercial payer reconciliation create 30-day liquidity swings.',
      recommendation: 'Diversify in-network insurance volume and establish electronic automated claim scrubbing.',
      category: 'collections',
    },
  ];

  // Fallback Opportunities if not explicitly passed
  const opportunities: OpportunityInsight[] = propOpportunities || [
    {
      id: 'op1',
      title: 'Supplier Terms & Early Settlement Discounts',
      potentialImpact: '+$14,500 annual profit',
      effort: 'Low',
      timeframe: 'Immediate (<30d)',
      actionPlan: 'Re-negotiate medical supply vendors from Net 15 to 2/10 Net 45 terms with electronic ACH payments.',
    },
    {
      id: 'op2',
      title: 'Ancillary Service Revenue Bundle',
      potentialImpact: '+$68,000 run-rate EBITDA',
      effort: 'Medium',
      timeframe: 'Quarterly (90d)',
      actionPlan: 'Launch diagnostic scanning add-ons and preventative wellness care plans for existing client database.',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Firm Header */}
      <FirmReportHeader client={client} reportTitle="Executive CFO & FP&A Dashboard" firmName={firmName} />

      {/* Top 4 Geometric Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Revenue */}
        <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="metric-label">Monthly Revenue</span>
            <span className="pill pill-success">
              <ArrowUpRight className="w-3 h-3 mr-0.5" />
              +5.4%
            </span>
          </div>
          <div className="metric-value mt-2">
            {formatCurrency(latestMonth.revenue)}
          </div>
          <div className="text-[10px] text-slate-500 mt-2 font-medium">
            Run rate: {formatCurrency(latestMonth.revenue * 12)} / year
          </div>
        </div>

        {/* Card 2: Gross Margin */}
        <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="metric-label">Gross Margin</span>
            <span className="pill pill-info">
              {latestMonth.grossMarginPercent?.toFixed(1)}%
            </span>
          </div>
          <div className="metric-value mt-2">
            {formatCurrency(latestMonth.grossProfit)}
          </div>
          <div className="text-[10px] text-slate-500 mt-2 font-medium">
            Gross Profit Generated (MoM)
          </div>
        </div>

        {/* Card 3: EBITDA */}
        <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="metric-label">EBITDA & Margin</span>
            <span className="pill pill-success">
              {latestMonth.ebitdaMarginPercent?.toFixed(1)}%
            </span>
          </div>
          <div className="metric-value mt-2">
            {formatCurrency(latestMonth.ebitda)}
          </div>
          <div className="text-[10px] text-slate-500 mt-2 font-medium">
            Operating Cash Core Engine
          </div>
        </div>

        {/* Card 4: Liquid Cash & Runway */}
        <div className="card-geometric p-4 hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="metric-label">Cash & Runway</span>
            <span className="pill pill-warning">
              {(latestMonth.cashAndEquivalents / (latestMonth.totalOpex || 1)).toFixed(1)} mos
            </span>
          </div>
          <div className="metric-value mt-2">
            {formatCurrency(latestMonth.cashAndEquivalents)}
          </div>
          <div className="text-[10px] text-slate-500 mt-2 font-medium">
            Liquid Operating Cash Reserve
          </div>
        </div>
      </div>

      {/* 12-Column Geometric Layout: Chart + Data Grid (8 cols) & Dark AI Intelligence Card (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left 8-Column Block: Performance Trajectory Chart & Table */}
        <div className="lg:col-span-8 space-y-6 flex flex-col justify-between">
          {/* Trajectory Chart Card */}
          <div className="card-geometric p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Historical Performance Trajectory</h3>
                <p className="text-xs text-slate-500">Monthly Revenue, Gross Profit, and EBITDA progression</p>
              </div>
              {onNavigateToTab && (
                <button
                  onClick={() => onNavigateToTab('financial_statements')}
                  className="text-xs font-semibold text-sky-600 hover:text-sky-800 flex items-center gap-1 cursor-pointer"
                >
                  Full Statements →
                </button>
              )}
            </div>

            <div className="h-64 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="geomColorRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0284C7" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#0284C7" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="geomColorGp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="geomColorEb" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#64748B" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#64748B" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={v => `${client.currencySymbol}${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    formatter={(value: any) => [`${client.currencySymbol}${Number(value).toLocaleString()}`, '']}
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#1e293b',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Area
                    type="monotone"
                    dataKey="Revenue"
                    stroke="#0284C7"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#geomColorRev)"
                  />
                  <Area
                    type="monotone"
                    dataKey="GrossProfit"
                    stroke="#10B981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#geomColorGp)"
                  />
                  <Area
                    type="monotone"
                    dataKey="EBITDA"
                    stroke="#64748B"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#geomColorEb)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Quick Summary Grid Table */}
          <div className="card-geometric overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Recent Monthly Breakdown
              </span>
              <span className="text-[11px] text-slate-400 font-medium">Last 4 Fiscal Periods</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold text-[10px] border-b border-slate-200/80">
                  <tr>
                    <th className="px-4 py-2.5">Period</th>
                    <th className="px-4 py-2.5 text-right">Revenue</th>
                    <th className="px-4 py-2.5 text-right">Gross Profit</th>
                    <th className="px-4 py-2.5 text-right">EBITDA</th>
                    <th className="px-4 py-2.5 text-right">Net Margin</th>
                    <th className="px-4 py-2.5 text-right">Ending Cash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {model.historicalMonthly.slice(-4).map((m, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-2.5 font-semibold text-slate-900">{m.periodLabel}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-slate-700">{formatCurrency(m.revenue)}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-slate-700">{formatCurrency(m.grossProfit)} ({m.grossMarginPercent?.toFixed(0)}%)</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-sky-700">{formatCurrency(m.ebitda)}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-slate-700">{m.netMarginPercent?.toFixed(1)}%</td>
                      <td className="px-4 py-2.5 text-right font-bold text-slate-900">{formatCurrency(m.cashAndEquivalents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right 4-Column Block: Dark AI Intelligence Card (Geometric Balance Theme) */}
        <div className="lg:col-span-4 flex flex-col">
          <div className="card-dark-geometric p-5 h-full flex flex-col justify-between shadow-md">
            <div>
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-sky-400" />
                  <span className="text-xs font-bold uppercase tracking-widest text-sky-400">
                    AI Intelligence Brief
                  </span>
                </div>
                <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                  Synthesized
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed italic mb-4">
                "{commentary.headlineSummary || 'Financial performance remains sound with strong gross margin expansion and stable operating cash flow runway.'}"
              </p>

              {/* 3 Core Highlights with Geometric Left Accent Borders */}
              <div className="space-y-3">
                <div className="border-l-2 border-emerald-500 pl-3">
                  <div className="text-[11px] font-bold text-emerald-400">Margin Resiliency</div>
                  <p className="text-[11px] text-slate-400 leading-normal mt-0.5">
                    Gross margins improved to {latestMonth.grossMarginPercent?.toFixed(1)}%, offsetting minor variable freight and supply increases.
                  </p>
                </div>

                <div className="border-l-2 border-rose-500 pl-3">
                  <div className="text-[11px] font-bold text-rose-400">Payroll Ratio Alert</div>
                  <p className="text-[11px] text-slate-400 leading-normal mt-0.5">
                    Personnel costs represent 46.8% of monthly top-line revenue; recommend locking non-essential contractor hires.
                  </p>
                </div>

                <div className="border-l-2 border-sky-400 pl-3">
                  <div className="text-[11px] font-bold text-sky-400">Advisory Action</div>
                  <p className="text-[11px] text-slate-400 leading-normal mt-0.5">
                    Execute vendor discount terms and accelerate collections to extend runway past 4.5 months.
                  </p>
                </div>
              </div>
            </div>

            {/* Action Buttons in Dark Card */}
            <div className="pt-5 mt-4 border-t border-slate-800/80 space-y-2">
              {onOpenAskCfo && (
                <button
                  onClick={onOpenAskCfo}
                  className="w-full py-2 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white rounded text-[11px] font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-xs"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Ask Your Virtual CFO
                </button>
              )}
              <button
                onClick={handleAiRefresh}
                disabled={isGeneratingAi}
                className="w-full py-2 bg-sky-600/30 hover:bg-sky-600/50 border border-sky-500/40 text-sky-200 rounded text-[11px] font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5 shadow-xs"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {isGeneratingAi ? 'Synthesizing...' : 'Refresh AI Analysis'}
              </button>
              <button
                onClick={() => setIsEditingCommentary(!isEditingCommentary)}
                className="w-full py-2 bg-white/10 hover:bg-white/15 border border-white/10 text-slate-300 hover:text-white rounded text-[11px] font-bold transition-colors cursor-pointer flex items-center justify-center gap-1.5"
              >
                <Edit3 className="w-3.5 h-3.5" />
                {isEditingCommentary ? 'Cancel Editing' : 'Edit Partner Memo'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Structured Executive Commentary (The Core CFO Advisory Value) */}
      <div className="card-geometric p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Virtual CFO Advisory Narrative
              </span>
              <span className="pill pill-info text-[10px]">
                {commentary.isAiGenerated ? 'AI Assisted + Deterministic Model' : 'Partner Signed'}
              </span>
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-0.5">
              Comprehensive Financial Performance Review
            </h3>
          </div>

          <div className="flex items-center gap-2">
            {isEditingCommentary ? (
              <button
                onClick={handleSaveCommentary}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                Save Signed Commentary
              </button>
            ) : (
              <button
                onClick={() => setIsEditingCommentary(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold transition-colors cursor-pointer"
              >
                <Edit3 className="w-3.5 h-3.5 text-slate-500" />
                Edit Commentary
              </button>
            )}
          </div>
        </div>

        {/* 4-Section Structured Narrative Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-5">
          {/* Section 1: What Happened */}
          <div className="space-y-2">
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-sky-500"></span>
              1. What Happened
            </div>
            {isEditingCommentary ? (
              <textarea
                value={editedCommentary.whatHappened}
                onChange={e => setEditedCommentary({ ...editedCommentary, whatHappened: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 rounded p-2.5 text-slate-900 text-xs focus:outline-hidden focus:border-sky-500"
                rows={4}
              />
            ) : (
              <p className="text-xs text-slate-600 leading-relaxed">{commentary.whatHappened}</p>
            )}
          </div>

          {/* Section 2: Why It Happened */}
          <div className="space-y-2">
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
              2. Why It Happened
            </div>
            {isEditingCommentary ? (
              <textarea
                value={editedCommentary.whyItHappened}
                onChange={e => setEditedCommentary({ ...editedCommentary, whyItHappened: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 rounded p-2.5 text-slate-900 text-xs focus:outline-hidden focus:border-sky-500"
                rows={4}
              />
            ) : (
              <p className="text-xs text-slate-600 leading-relaxed">{commentary.whyItHappened}</p>
            )}
          </div>

          {/* Section 3: Why It Matters */}
          <div className="space-y-2">
            <div className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              3. Why It Matters
            </div>
            {isEditingCommentary ? (
              <textarea
                value={editedCommentary.whyItMatters}
                onChange={e => setEditedCommentary({ ...editedCommentary, whyItMatters: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 rounded p-2.5 text-slate-900 text-xs focus:outline-hidden focus:border-sky-500"
                rows={4}
              />
            ) : (
              <p className="text-xs text-slate-600 leading-relaxed">{commentary.whyItMatters}</p>
            )}
          </div>
        </div>

        {/* Recommended Actions */}
        <div className="mt-6 pt-5 border-t border-slate-200">
          <div className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-sky-600" />
            4. Recommended Management Actions (Virtual CFO Directives)
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {commentary.recommendedActions.map((action, i) => (
              <div
                key={i}
                className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 flex items-start gap-2.5"
              >
                <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-800 font-bold text-[11px] flex items-center justify-center shrink-0">
                  {i + 1}
                </span>
                <span className="leading-snug">{action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3-Section Analysis: Wins, Red Flags, and Opportunities */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Wins & Accomplishments */}
        <div className="card-geometric p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Award className="w-4 h-4 text-emerald-600" />
              Key Financial Wins
            </h4>
            <span className="pill pill-success">
              {wins.length} Wins
            </span>
          </div>
          <div className="space-y-3">
            {wins.map(w => (
              <div key={w.id} className="p-3 bg-emerald-50/50 rounded-lg border border-emerald-100 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">{w.title}</span>
                  <span className="text-[10px] font-bold text-emerald-800 bg-white px-1.5 py-0.5 rounded border border-emerald-200">
                    {w.change}
                  </span>
                </div>
                <div className="text-[11px] font-semibold text-emerald-800">{w.metric}</div>
                <p className="text-xs text-slate-600 leading-relaxed">{w.businessImpact}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Red Flags & Risk Warnings */}
        <div className="card-geometric p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              Red Flags & Risks
            </h4>
            <span className="pill pill-danger">
              {redFlags.length} Alerts
            </span>
          </div>
          <div className="space-y-3">
            {redFlags.map(rf => (
              <div key={rf.id} className="p-3 bg-rose-50/50 rounded-lg border border-rose-100 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">{rf.title}</span>
                  <span className="pill pill-danger text-[9px] uppercase">
                    {rf.severity}
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">{rf.impact}</p>
                <div className="text-[11px] text-rose-900 bg-white p-2 rounded border border-rose-200 font-medium">
                  <span className="font-bold">Directive: </span>
                  {rf.recommendation}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Strategic Growth Opportunities */}
        <div className="card-geometric p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              Growth Opportunities
            </h4>
            <span className="pill pill-warning">
              {opportunities.length} Items
            </span>
          </div>
          <div className="space-y-3">
            {opportunities.map(op => (
              <div key={op.id} className="p-3 bg-amber-50/50 rounded-lg border border-amber-100 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900">{op.title}</span>
                  <span className="text-[10px] font-bold text-amber-800 bg-white px-1.5 py-0.5 rounded border border-amber-200">
                    {op.timeframe}
                  </span>
                </div>
                <div className="text-[11px] font-bold text-emerald-700">{op.potentialImpact}</div>
                <p className="text-xs text-slate-600 leading-relaxed">{op.actionPlan}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Report Footer */}
      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
