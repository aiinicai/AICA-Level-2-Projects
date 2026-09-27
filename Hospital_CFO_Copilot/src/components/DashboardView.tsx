import React, { useState, useMemo } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  FileCheck2,
  Clock,
  ArrowRight,
  ShieldAlert,
  Building2,
  ChevronRight,
  Sparkles,
  PieChart as PieIcon,
  UploadCloud,
  FileSpreadsheet,
  Info,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { DepartmentClearanceSummary } from '../engine/clearanceEngine';
import { TariffIntelligenceSummary } from '../engine/tariffEngine';
import {
  Billing,
  Claim,
  Collection,
  DashboardMetrics,
  Encounter,
  FinancialException,
  UserSession,
} from '../types';
import { FirestoreControlRun } from '../services/firestoreDataService';
import { calculateArAgeing, ArAgeingSummary } from '../utils/arCalculations';
import { formatIndianNumber, formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface DashboardViewProps {
  metrics: DashboardMetrics;
  clearanceSummary?: DepartmentClearanceSummary;
  tariffSummary?: TariffIntelligenceSummary;
  hasData?: boolean;
  encounters?: Encounter[];
  billings?: Billing[];
  claims?: Claim[];
  collections?: Collection[];
  controlRuns?: FirestoreControlRun[];
  asOfDate?: string;
  onSelectEncounter: (encounterId: string) => void;
  onSelectException: (exception: FinancialException) => void;
  onNavigateToTab: (tabId: string) => void;
  onOpenManagementPack?: () => void;
  onOpenCfoReview?: () => void;
  currentUser?: UserSession;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  metrics,
  clearanceSummary,
  hasData = true,
  encounters = [],
  billings = [],
  claims = [],
  collections = [],
  controlRuns = [],
  asOfDate,
  onSelectEncounter,
  onSelectException,
  onNavigateToTab,
  onOpenManagementPack,
  onOpenCfoReview,
  currentUser,
}) => {
  // Drill-down department filter
  const [selectedDept, setSelectedDept] = useState<string | null>(null);
  const [activeLineageTooltip, setActiveLineageTooltip] = useState<string | null>(null);

  // Clean empty state if no hospital data exists yet
  if (!hasData) {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center p-6 text-center">
        <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-xs">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 border border-teal-200 text-teal-700 mb-4">
            <UploadCloud className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900">
            No financial data available
          </h2>
          <p className="mt-2 text-sm text-slate-500 leading-relaxed">
            Upload your hospital financial extracts to begin analysis.
          </p>
          <div className="mt-6 flex justify-center">
            <button
              onClick={() => onNavigateToTab('data-intelligence')}
              className="inline-flex items-center gap-2 rounded-lg bg-teal-700 hover:bg-teal-800 px-5 py-2.5 text-sm font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer"
            >
              <UploadCloud className="h-4 w-4" />
              <span>Upload Financial Extracts</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 1. Net Billing Calculation
  // Net Billing: grossBilling minus identified financial exposure. Floored at zero.
  // When exposure > grossBilling the result is zero (not gross), to avoid silently
  // reporting an inflated figure. The CFO should see an alert in this scenario.
  const netBilling = Math.max(0, metrics.grossBilling - metrics.potentialFinancialExposure);
  const netBillingIsCapped = metrics.potentialFinancialExposure >= metrics.grossBilling;
  const unbilledAmount = Math.max(0, metrics.totalExpectedAmount - metrics.grossBilling);

  // 2. Billing Capture Rate (%)
  // Use pre-computed capture rate from controlEngine (single source of truth)
  const billingCaptureRate = metrics.billingCaptureRate ?? (
    metrics.totalExpectedAmount > 0
      ? Number(((metrics.grossBilling / metrics.totalExpectedAmount) * 100).toFixed(1))
      : 100
  );

  // 3. Departmental Review Pending count
  const deptReviewPendingCount = clearanceSummary ? clearanceSummary.pendingCount : 0;

  // 4. Critical & High Exceptions count
  const criticalAndHighExceptions = metrics.criticalExceptionsCount + metrics.highExceptionsCount;

  // 5. Deterministic AR Ageing Calculation (Same as AR / Working Capital module)
  const arSummary: ArAgeingSummary = useMemo(() => {
    return calculateArAgeing(encounters, billings, collections, claims, asOfDate);
  }, [encounters, billings, collections, claims, asOfDate]);

  // 6. Deterministic Revenue / Billing Trend - Group actual billing records by their real billing date / month
  const revenueTrendData = useMemo(() => {
    if (billings.length === 0) return [];

    const monthMap = new Map<string, { gross: number; collected: number }>();

    // Index collections by month
    const collectionsByMonth = new Map<string, number>();
    collections.forEach((c) => {
      const m = (c.Receipt_Date || '').slice(0, 7);
      if (m) {
        collectionsByMonth.set(m, (collectionsByMonth.get(m) || 0) + (Number(c.Amount) || 0));
      }
    });

    billings.forEach((b) => {
      const m = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 7);
      if (!m || m.length !== 7) return;

      if (!monthMap.has(m)) {
        monthMap.set(m, { gross: 0, collected: 0 });
      }
      const cur = monthMap.get(m)!;
      cur.gross += Number(b.Billed_Amount) || 0;
    });

    // Populate collections where available
    monthMap.forEach((val, m) => {
      val.collected = collectionsByMonth.get(m) || 0;
    });

    const sorted = Array.from(monthMap.entries()).sort((a, b) => a[0].localeCompare(b[0]));

    return sorted.map(([m, val]) => {
      const d = new Date(`${m}-01T00:00:00`);
      const label = d.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
      return {
        period: label,
        gross: Math.round(val.gross),
        collected: Math.round(val.collected),
      };
    });
  }, [billings, collections]);

  // Chart 2: Billing Capture Analysis (Funnel Waterfall)
  const billingCaptureWaterfall = [
    { stage: 'Expected Charge', amount: metrics.totalExpectedAmount, fill: '#0f766e' },
    { stage: 'Gross Billed', amount: metrics.grossBilling, fill: '#0d9488' },
    { stage: 'Amount Claimed', amount: metrics.funnel.claimed, fill: '#0284c7' },
    { stage: 'Authorised', amount: metrics.funnel.approved, fill: '#2563eb' },
    { stage: 'Realised', amount: metrics.funnel.collected, fill: '#059669' },
  ];

  // Chart 3: Financial Impact by Department
  const deptImpactData = metrics.exceptionsByDepartment.map((d) => ({
    department: d.department,
    impact: d.exposure,
    count: d.count,
  }));

  // Chart 4: Receivables Ageing Data from actual deterministic calculation
  const arAgeingData = arSummary.ageingBuckets;

  // Chart 5: Insurance / TPA Outstanding Adjudication - Derived strictly from actual claims
  const tpaData = useMemo(() => {
    if (claims.length === 0) {
      return [
        { label: 'Pending Authorisation', amount: metrics.tpaPendingAmount, color: '#0284c7' },
        { label: 'Under Query / Adjudication', amount: 0, color: '#f59e0b' },
        { label: 'Disallowed / Deductions', amount: 0, color: '#ea580c' },
      ];
    }

    const pendingAuth = claims
      .filter((c) => c.Claim_Status === 'Submitted' || c.Claim_Status === 'Pending Info' || c.Claim_Status === 'In Adjudication')
      .reduce((s, c) => s + (Number(c.Claim_Amount) || 0), 0);

    const underQuery = claims
      .filter((c) => c.Claim_Status === 'Under Query')
      .reduce((s, c) => s + (Number(c.Claim_Amount) || 0), 0);

    const disallowed = claims.reduce((s, c) => s + (Number(c.Rejected_Amount) || 0), 0);

    return [
      { label: 'Pending Authorisation', amount: Math.round(pendingAuth), color: '#0284c7' },
      { label: 'Under Query / Adjudication', amount: Math.round(underQuery), color: '#f59e0b' },
      { label: 'Disallowed / Deductions', amount: Math.round(disallowed), color: '#ea580c' },
    ];
  }, [claims, metrics.tpaPendingAmount]);

  // Chart 6: Exception Trend - Uses actual Firestore control run history
  const exceptionTrendData = useMemo(() => {
    if (!controlRuns || controlRuns.length <= 1) {
      return null;
    }

    // Sort control runs ascending by executedAt
    const sorted = [...controlRuns].sort((a, b) => a.executedAt.localeCompare(b.executedAt));
    return sorted.slice(-5).map((run, idx) => {
      const dt = new Date(run.executedAt);
      const timeLabel = isNaN(dt.getTime())
        ? `Run ${idx + 1}`
        : dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
      return {
        period: timeLabel,
        exceptions: run.exceptionsGenerated || 0,
        exposure: Math.round(run.potentialExposure || 0),
        records: run.recordsProcessed || 0,
      };
    });
  }, [controlRuns]);

  // Chart 7: Departmental Review Status
  const deptReviewData = [
    { status: 'Verified', count: clearanceSummary?.verifiedCount || 0, fill: '#059669' },
    { status: 'Pending Review', count: clearanceSummary?.pendingCount || 0, fill: '#f59e0b' },
    { status: 'Disputed', count: clearanceSummary?.disputedCount || 0, fill: '#dc2626' },
    { status: 'Correction Required', count: clearanceSummary?.correctionRequiredCount || 0, fill: '#ea580c' },
  ];

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Finance Control Tower
              </h1>
              <span className="rounded bg-teal-50 px-2.5 py-0.5 text-[11px] font-bold text-teal-800 border border-teal-200 uppercase tracking-wide">
                Institutional Overview
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Revenue, Billing, Receivables &amp; Financial Controls &bull; Traceable to Firestore Transaction Records
            </p>
          </div>

          <div className="flex items-center gap-2">
            {onOpenCfoReview && (
              <button
                onClick={onOpenCfoReview}
                disabled={!hasData}
                title={!hasData ? 'Upload financial extracts to run review' : undefined}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-bold transition active:scale-95 cursor-pointer ring-1 ${
                  !hasData
                    ? 'bg-slate-200 text-slate-400 ring-slate-200 cursor-not-allowed'
                    : 'bg-teal-700 hover:bg-teal-800 text-white shadow-xs ring-teal-600/30'
                }`}
              >
                <Sparkles className="h-3.5 w-3.5 text-teal-200" />
                <span>Run CFO Financial Review</span>
              </button>
            )}
            <button
              onClick={() => onNavigateToTab('cfo-copilot')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50/70 hover:bg-teal-100/70 px-3.5 py-2 text-xs font-semibold text-teal-800 transition cursor-pointer"
            >
              <Sparkles className="h-3.5 w-3.5 text-teal-700" />
              <span>CFO Executive Briefing</span>
            </button>
            {onOpenManagementPack && (
              <button
                onClick={onOpenManagementPack}
                disabled={!hasData}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold shadow-2xs transition cursor-pointer ${
                  !hasData
                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                    : 'bg-teal-700 hover:bg-teal-800 text-white'
                }`}
              >
                <FileSpreadsheet className="h-3.5 w-3.5" />
                <span>Management Dossier</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {!hasData ? (
        <EmptyWorkspaceState
          title="No Financial Data Available"
          description="No financial data available. Upload your hospital financial extracts to begin analysis."
          badge="Awaiting Data Ingestion"
          actionText="Upload Financial Extracts"
          onAction={() => onNavigateToTab('data-intelligence')}
        />
      ) : (
        <>
          {/* 6 PRIMARY KPI CARDS WITH DATA LINEAGE INDICATORS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
        {/* 1. Net Billing */}
        <div
          onClick={() => onNavigateToTab('financial-performance')}
          className="group relative rounded-xl border border-slate-200 bg-white p-4 shadow-2xs hover:border-teal-400 hover:shadow-xs transition cursor-pointer"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider">Net Billing</span>
            <span title="Lineage: Gross Billed (Billing Register) − Identified Financial Exposure" className="text-slate-400 hover:text-teal-700">
              <Info className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="text-xl font-bold tracking-tight text-slate-900">
            {formatINR(netBilling)}
          </div>
          {netBillingIsCapped && (
            <div className="mt-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
              ⚠ Exposure ≥ Gross Billing
            </div>
          )}
          <div className="mt-1 text-[11px] text-slate-500">
            Gross: <span className="font-medium text-slate-700">{formatINR(metrics.grossBilling)}</span>
          </div>
        </div>

        {/* 2. Potential Financial Impact */}
        <div
          onClick={() => onNavigateToTab('revenue-controls')}
          className="rounded-xl border border-amber-200 bg-amber-50/25 p-4 shadow-2xs hover:border-amber-400 hover:shadow-xs transition cursor-pointer"
        >
          <div className="flex items-center justify-between text-amber-800 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider">
              Potential Financial Impact
            </span>
            <span title="Lineage: C01–C08 Control Results (Sum of Exposure_Amount)" className="text-amber-500 hover:text-amber-800">
              <Info className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="text-xl font-bold tracking-tight text-amber-950">
            {formatINR(metrics.potentialFinancialExposure)}
          </div>
          <div className="mt-1 text-[11px] text-amber-700 font-medium">
            Across {metrics.openExceptionsCount} open items
          </div>
        </div>

        {/* 3. Open High/Critical Exceptions */}
        <div
          onClick={() => onNavigateToTab('revenue-controls')}
          className="rounded-xl border border-rose-200 bg-rose-50/25 p-4 shadow-2xs hover:border-rose-400 hover:shadow-xs transition cursor-pointer"
        >
          <div className="flex items-center justify-between text-rose-800 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider">
              High / Critical Exceptions
            </span>
            <AlertTriangle className="h-4 w-4 text-rose-600" />
          </div>
          <div className="text-xl font-bold tracking-tight text-rose-950">
            {criticalAndHighExceptions}
          </div>
          <div className="mt-1 text-[11px] text-rose-700">
            {metrics.criticalExceptionsCount} Critical &bull; {metrics.highExceptionsCount} High
          </div>
        </div>

        {/* 4. Billing Capture % */}
        <div
          onClick={() => onNavigateToTab('revenue-controls')}
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs hover:border-teal-400 hover:shadow-xs transition cursor-pointer"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider">Billing Capture %</span>
            <span className="text-xs font-bold text-teal-700">{billingCaptureRate}%</span>
          </div>
          <div className="text-xl font-bold tracking-tight text-slate-900">
            {billingCaptureRate}%
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            Unbilled: <span className="font-semibold text-rose-600">{formatINR(unbilledAmount)}</span>
          </div>
        </div>

        {/* 5. Trade Receivables */}
        <div
          onClick={() => onNavigateToTab('receivables-collections')}
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs hover:border-teal-400 hover:shadow-xs transition cursor-pointer"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider">Trade Receivables</span>
            <span title="Lineage: Invoiced Billing − Verified Collection Receipts" className="text-slate-400 hover:text-sky-700">
              <Info className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="text-xl font-bold tracking-tight text-slate-900">
            {formatINR(arSummary.totalAR)}
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            Overdue: <span className="font-medium text-rose-700">{formatINR(arSummary.overdueAR)}</span>
          </div>
        </div>

        {/* 6. Departmental Review Pending */}
        <div
          onClick={() => onNavigateToTab('department-clearance')}
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs hover:border-teal-400 hover:shadow-xs transition cursor-pointer"
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-wider">
              Dept Review Pending
            </span>
            <FileCheck2 className="h-4 w-4 text-teal-600" />
          </div>
          <div className="text-xl font-bold tracking-tight text-slate-900">
            {deptReviewPendingCount}
          </div>
          <div className="mt-1 text-[11px] text-teal-700 font-medium">
            {clearanceSummary?.verifiedCount || 0} Verified
          </div>
        </div>
      </div>

      {/* ROW 1: 1. REVENUE / BILLING TREND + 2. BILLING CAPTURE ANALYSIS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 1. Revenue / Billing Trend */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">1. Revenue &amp; Billing Trend</h2>
              <p className="text-xs text-slate-500">
                Gross Billing vs. Realised Collections (₹) &bull; Actual Accounting Periods
              </p>
            </div>
            <span className="text-[10px] text-slate-400 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded">
              Lineage: Billing Register
            </span>
          </div>

          {revenueTrendData.length > 1 ? (
            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={revenueTrendData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <XAxis dataKey="period" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(val) => formatINR(val, { compact: true })} />
                  <Tooltip
                    formatter={(val: any) => [formatINR(Number(val)), '']}
                    labelStyle={{ fontWeight: 'bold' }}
                  />
                  <Line type="monotone" dataKey="gross" name="Gross Billed" stroke="#0d9488" strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="collected" name="Realised" stroke="#059669" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : revenueTrendData.length === 1 ? (
            <div className="h-60 w-full flex flex-col justify-center items-center text-center p-6 bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
              <div className="text-xs font-semibold text-slate-800">
                Current Active Period: {revenueTrendData[0].period}
              </div>
              <div className="text-lg font-bold text-teal-800 mt-1">
                {formatINR(revenueTrendData[0].gross)}
              </div>
              <p className="text-xs text-slate-500 mt-2 max-w-sm">
                Historical trend requires multiple accounting periods. Currently showing actual data for the active import period.
              </p>
            </div>
          ) : (
            <div className="h-60 w-full flex items-center justify-center text-slate-400 text-xs">
              Historical trend unavailable for the selected period
            </div>
          )}

          <div className="mt-3 flex items-center justify-center gap-6 text-[11px] text-slate-600">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-teal-600" /> Gross Billed</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-600" /> Realised</span>
          </div>
        </div>

        {/* 2. Billing Capture Analysis (Waterfall) */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">2. Billing Capture Analysis</h2>
              <p className="text-xs text-slate-500">
                Billing conversion funnel from Expected Charge to Realised Collection
              </p>
            </div>
            <span className="text-xs font-semibold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
              {billingCaptureRate}% Capture Rate
            </span>
          </div>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={billingCaptureWaterfall} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <XAxis dataKey="stage" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(val) => formatINR(val, { compact: true })} />
                <Tooltip formatter={(val: any) => [formatINR(Number(val)), 'Amount']} />
                <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                  {billingCaptureWaterfall.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 text-center text-[11px] text-slate-500">
            Unbilled Charge Variance: <strong className="text-rose-600">{formatINR(unbilledAmount)}</strong>
          </div>
        </div>
      </div>

      {/* ROW 2: 3. FINANCIAL IMPACT BY DEPARTMENT + 4. RECEIVABLES AGEING */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 3. Financial Impact by Department (Cost Centre) */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">3. Financial Impact by Department</h2>
              <p className="text-xs text-slate-500">
                Departmental breakdown of unbilled charges and rate variances
              </p>
            </div>
            <button
              onClick={() => onNavigateToTab('department-clearance')}
              className="text-xs font-medium text-teal-700 hover:text-teal-900 inline-flex items-center gap-1 cursor-pointer"
            >
              <span>Review Depts</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="h-60 w-full">
            {deptImpactData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={deptImpactData}
                  layout="vertical"
                  margin={{ top: 5, right: 20, left: 35, bottom: 5 }}
                >
                  <XAxis type="number" stroke="#94a3b8" fontSize={11} tickFormatter={(val) => formatINR(val, { compact: true })} />
                  <YAxis dataKey="department" type="category" stroke="#94a3b8" fontSize={11} width={80} />
                  <Tooltip formatter={(val: any) => [formatINR(Number(val)), 'Potential Impact']} />
                  <Bar
                    dataKey="impact"
                    fill="#0d9488"
                    radius={[0, 4, 4, 0]}
                    onClick={(entry: any) => {
                      if (entry && entry.department) {
                        setSelectedDept(entry.department);
                      }
                      onNavigateToTab('department-clearance');
                    }}
                    className="cursor-pointer"
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                No exceptions identified across departments
              </div>
            )}
          </div>
          <div className="mt-2 text-center text-[11px] text-slate-500">
            Click any department to drill down into Departmental Billing Review.
          </div>
        </div>

        {/* 4. Receivables Ageing - DETERMINISTIC AR AGEING */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">4. Receivables Ageing</h2>
              <p className="text-xs text-slate-500">
                Trade receivables breakdown by ageing bucket &bull; Total {formatINR(arSummary.totalAR)}
              </p>
            </div>
            <button
              onClick={() => onNavigateToTab('receivables-collections')}
              className="text-xs font-medium text-teal-700 hover:text-teal-900 inline-flex items-center gap-1 cursor-pointer"
            >
              <span>Ageing Ledger</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="space-y-3 py-2">
            {arAgeingData.map((item) => (
              <div key={item.bucket} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-700">{item.label}</span>
                  <span className="font-bold text-slate-900">
                    {formatINR(item.amount)} <span className="text-slate-500 font-normal">({item.shareFormatted})</span>
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: item.shareFormatted,
                      backgroundColor: item.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
            <span>Receivable Ageing Threshold: 30 Days</span>
            <span className="font-semibold text-rose-700">
              Overdue (&gt;30d): {formatINR(arSummary.overdueAR)}
            </span>
          </div>
        </div>
      </div>

      {/* ROW 3: 5. INSURANCE/TPA OUTSTANDING + 6. EXCEPTION TREND + 7. DEPARTMENTAL REVIEW STATUS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* 5. Insurance / TPA Outstanding */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">5. Insurance / TPA Outstanding</h2>
              <p className="text-xs text-slate-500">Payor claim adjudication status</p>
            </div>
            <span className="text-[10px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
              Lineage: Claims Master
            </span>
          </div>
          <div className="space-y-3 pt-2">
            {tpaData.map((item) => (
              <div key={item.label} className="p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                <div className="text-[11px] text-slate-500">{item.label}</div>
                <div className="text-base font-bold text-slate-900 mt-0.5">{formatINR(item.amount)}</div>
              </div>
            ))}
          </div>
          <div className="mt-3">
            <button
              onClick={() => onNavigateToTab('receivables-collections')}
              className="w-full text-center text-xs font-semibold text-teal-700 hover:text-teal-900 py-1 cursor-pointer"
            >
              View Payor Adjudication &rarr;
            </button>
          </div>
        </div>

        {/* 6. Exception Trend */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">6. Exception Trend</h2>
              <p className="text-xs text-slate-500">Historical Control Run Execution</p>
            </div>
            <span className="text-[10px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200">
              Lineage: Firestore control_runs
            </span>
          </div>

          {exceptionTrendData && exceptionTrendData.length > 1 ? (
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={exceptionTrendData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                  <XAxis dataKey="period" stroke="#94a3b8" fontSize={10} />
                  <YAxis stroke="#94a3b8" fontSize={10} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="exceptions" name="Exceptions" fill="#ea580c" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-44 w-full flex flex-col items-center justify-center text-center p-4 bg-slate-50/50 rounded-lg border border-dashed border-slate-200">
              <div className="text-xs font-bold text-slate-700">
                {controlRuns.length === 1 ? 'Single Control Run Executed' : 'No Prior Runs'}
              </div>
              <p className="text-[11px] text-slate-400 mt-1 max-w-[200px]">
                Trend requires multiple control runs.
              </p>
              <div className="mt-2 text-[10px] text-teal-700 font-mono">
                {metrics.openExceptionsCount} active exceptions in current run
              </div>
            </div>
          )}

          <div className="mt-3">
            <button
              onClick={() => onNavigateToTab('revenue-controls')}
              className="w-full text-center text-xs font-semibold text-teal-700 hover:text-teal-900 py-1 cursor-pointer"
            >
              Investigate Exceptions ({metrics.openExceptionsCount} Open) &rarr;
            </button>
          </div>
        </div>

        {/* 7. Departmental Review Status */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">7. Departmental Review Status</h2>
              <p className="text-xs text-slate-500">Charge attribution sign-off</p>
            </div>
          </div>
          <div className="space-y-2.5 pt-1">
            {deptReviewData.map((item) => (
              <div key={item.status} className="flex items-center justify-between text-xs py-1 border-b border-slate-100 last:border-0">
                <span className="flex items-center gap-2 text-slate-700 font-medium">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                  {item.status}
                </span>
                <span className="font-bold text-slate-900">{formatIndianNumber(item.count)}</span>
              </div>
            ))}
          </div>
          <div className="mt-4">
            <button
              onClick={() => onNavigateToTab('department-clearance')}
              className="w-full text-center text-xs font-semibold text-teal-700 hover:text-teal-900 py-1 cursor-pointer"
            >
              Open Departmental Billing Review &rarr;
            </button>
          </div>
        </div>
      </div>
        </>
      )}
    </div>
  );
};
