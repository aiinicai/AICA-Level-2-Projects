import React, { useMemo, useState } from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Building2,
  Calendar,
  CheckCircle2,
  CreditCard,
  DollarSign,
  Download,
  FileSpreadsheet,
  Filter,
  HelpCircle,
  MessageSquare,
  PieChart as PieIcon,
  TrendingDown,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BudgetExecutiveSummary } from '../engine/budgetEngine';
import { Billing, Encounter, HospitalDepartment, Service, UserSession } from '../types';
import { mapRevenueCentreToDepartment, extractUniqueDepartments } from '../utils/departmentMapping';
import { formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface FinancialPerformanceViewProps {
  encounters: Encounter[];
  services: Service[];
  billings: Billing[];
  budgetSummary?: BudgetExecutiveSummary;
  currentUser?: UserSession;
  onNavigateToTab?: (tab: string) => void;
}

export const FinancialPerformanceView: React.FC<FinancialPerformanceViewProps> = ({
  encounters,
  services,
  billings,
  budgetSummary,
  currentUser,
  onNavigateToTab,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'analytics' | 'budget'>('analytics');
  const [timeframe, setTimeframe] = useState<'MONTH' | 'QUARTER' | 'YTD'>('MONTH');

  // Discover all months present in billing and encounter records
  const availableMonths = useMemo(() => {
    const months = new Set<string>();
    billings.forEach((b) => {
      const m = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 7);
      if (m && m.length === 7) months.add(m);
    });
    encounters.forEach((e) => {
      const m = (e.Discharge_Date || e.Admission_Date || '').slice(0, 7);
      if (m && m.length === 7) months.add(m);
    });
    const sorted = Array.from(months).sort().reverse();
    return sorted.length > 0 ? sorted : ['2026-09'];
  }, [billings, encounters]);

  const [selectedMonth, setSelectedMonth] = useState<string>(availableMonths[0] || '2026-09');

  // Service lookup
  const serviceMap = useMemo(() => {
    const map = new Map<string, Service>();
    services.forEach((s) => map.set(s.Service_ID, s));
    return map;
  }, [services]);

  // Encounter lookup
  const encounterMap = useMemo(() => {
    const map = new Map<string, Encounter>();
    encounters.forEach((e) => map.set(e.Encounter_ID, e));
    return map;
  }, [encounters]);

  const knownDepartments = useMemo(() => {
    return extractUniqueDepartments(encounters);
  }, [encounters]);

  // Determine allowed months based on timeframe (MONTH, QUARTER, YTD)
  const activePeriodMonths = useMemo(() => {
    const yearStr = selectedMonth.slice(0, 4);
    const monthNum = parseInt(selectedMonth.slice(5, 7), 10);

    if (timeframe === 'MONTH') {
      return [selectedMonth];
    }

    if (timeframe === 'QUARTER') {
      // Standard Indian Hospital Fiscal Quarters:
      // Q1: Apr–Jun (04, 05, 06)
      // Q2: Jul–Sep (07, 08, 09)
      // Q3: Oct–Dec (10, 11, 12)
      // Q4: Jan–Mar (01, 02, 03)
      let qMonths: number[] = [];
      if (monthNum >= 4 && monthNum <= 6) qMonths = [4, 5, 6];
      else if (monthNum >= 7 && monthNum <= 9) qMonths = [7, 8, 9];
      else if (monthNum >= 10 && monthNum <= 12) qMonths = [10, 11, 12];
      else qMonths = [1, 2, 3];

      return qMonths.map((m) => `${yearStr}-${m.toString().padStart(2, '0')}`);
    }

    // YTD: Beginning of Indian Financial Year (April) through selected month
    const ytdList: string[] = [];
    if (monthNum >= 4) {
      for (let m = 4; m <= monthNum; m++) {
        ytdList.push(`${yearStr}-${m.toString().padStart(2, '0')}`);
      }
    } else {
      // Jan–Mar: include Apr–Dec of previous year plus Jan..monthNum of current year
      const prevYear = parseInt(yearStr, 10) - 1;
      for (let m = 4; m <= 12; m++) {
        ytdList.push(`${prevYear}-${m.toString().padStart(2, '0')}`);
      }
      for (let m = 1; m <= monthNum; m++) {
        ytdList.push(`${yearStr}-${m.toString().padStart(2, '0')}`);
      }
    }
    return ytdList;
  }, [selectedMonth, timeframe]);

  // Filter billings strictly by the selected timeframe
  const filteredBillings = useMemo(() => {
    return billings.filter((b) => {
      const bMonth = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 7);
      return activePeriodMonths.includes(bMonth);
    });
  }, [billings, activePeriodMonths]);

  // Filter encounters strictly by the selected timeframe
  const filteredEncounters = useMemo(() => {
    return encounters.filter((e) => {
      const eMonth = (e.Discharge_Date || e.Admission_Date || '').slice(0, 7);
      return activePeriodMonths.includes(eMonth);
    });
  }, [encounters, activePeriodMonths]);

  // Core Financial Performance Metrics calculated strictly from filtered records
  const totalGrossBilled = useMemo(() => {
    return filteredBillings.reduce((sum, b) => sum + (Number(b.Billed_Amount) || 0), 0);
  }, [filteredBillings]);

  const totalDischarges = useMemo(() => {
    return filteredEncounters.filter((e) => e.Discharge_Status === 'Discharged').length;
  }, [filteredEncounters]);

  const totalEncountersCount = filteredEncounters.length;
  const avgBillValue = totalEncountersCount > 0 ? totalGrossBilled / totalEncountersCount : 0;
  // Revenue per discharge: show 0 (not avgBillValue) when no discharges exist in the period.
  // Showing avgBillValue as a fallback is misleading — it conflates two different metrics.
  const revPerDischarge = totalDischarges > 0 ? totalGrossBilled / totalDischarges : 0;
  const noDischargesInPeriod = totalDischarges === 0 && totalEncountersCount > 0;

  // Revenue by Department
  const revenueByDept = useMemo(() => {
    const deptMap = new Map<string, number>();

    filteredBillings.forEach((b) => {
      const svc = serviceMap.get(b.Service_ID);
      const revCentre = svc?.Revenue_Centre || 'General';
      const dept = mapRevenueCentreToDepartment(revCentre, knownDepartments);
      deptMap.set(dept, (deptMap.get(dept) || 0) + (Number(b.Billed_Amount) || 0));
    });

    return Array.from(deptMap.entries())
      .map(([dept, amount]) => ({
        department: dept,
        amount: Number(amount.toFixed(2)),
        percentage:
          totalGrossBilled > 0
            ? Number(((amount / totalGrossBilled) * 100).toFixed(1))
            : 0,
      }))
      .sort((a, b) => b.amount - a.amount);
  }, [filteredBillings, serviceMap, knownDepartments, totalGrossBilled]);

  // Revenue by Revenue Centre
  const revenueByRevCentre = useMemo(() => {
    const revMap = new Map<string, number>();

    filteredBillings.forEach((b) => {
      const svc = serviceMap.get(b.Service_ID);
      const name = svc?.Revenue_Centre || 'Other';
      revMap.set(name, (revMap.get(name) || 0) + (Number(b.Billed_Amount) || 0));
    });

    return Array.from(revMap.entries())
      .map(([name, amount]) => ({
        name: name.replace(' / Critical Care', '').replace(' / Surgery', ''),
        amount: Number(amount.toFixed(2)),
      }))
      .sort((a, b) => b.amount - a.amount);
  }, [filteredBillings, serviceMap]);

  // Revenue by Payer
  const revenueByPayer = useMemo(() => {
    const payerMap = new Map<string, number>();

    filteredBillings.forEach((b) => {
      const enc = encounterMap.get(b.Encounter_ID);
      const p = enc?.Payer_Type || 'Self Pay';
      payerMap.set(p, (payerMap.get(p) || 0) + (Number(b.Billed_Amount) || 0));
    });

    const colors = ['#0f766e', '#0284c7', '#6366f1', '#f59e0b', '#10b981', '#ec4899'];
    return Array.from(payerMap.entries()).map(([payer, amount], idx) => ({
      name: payer,
      value: Number(amount.toFixed(2)),
      color: colors[idx % colors.length],
    }));
  }, [filteredBillings, encounterMap]);

  // Actual Monthly Revenue Trend - Group actual billing records by their real billing month
  const monthlyTrendData = useMemo(() => {
    const monthTotals = new Map<string, { revenue: number; encounterIds: Set<string> }>();

    billings.forEach((b) => {
      const m = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 7);
      if (!m || m.length !== 7) return;

      if (!monthTotals.has(m)) {
        monthTotals.set(m, { revenue: 0, encounterIds: new Set<string>() });
      }
      const cur = monthTotals.get(m)!;
      cur.revenue += Number(b.Billed_Amount) || 0;
      if (b.Encounter_ID) cur.encounterIds.add(b.Encounter_ID);
    });

    const sortedMonths = Array.from(monthTotals.keys()).sort();

    return sortedMonths.map((m) => {
      const data = monthTotals.get(m)!;
      const dObj = new Date(`${m}-01T00:00:00`);
      const monthLabel = dObj.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
      return {
        month: monthLabel,
        rawMonth: m,
        revenue: Math.round(data.revenue),
        discharges: data.encounterIds.size,
      };
    });
  }, [billings]);

  // Budget vs Actual chart data from budgetSummary
  const deptVarianceChartData = useMemo(() => {
    if (!budgetSummary) return [];
    return budgetSummary.departmentSummaries.map((d) => ({
      department: d.department,
      budget: d.revenueBudget,
      actual: d.revenueActual,
      variance: d.revenueVariance,
      variancePct: d.revenueVariancePercent,
      isSignificant: d.isSignificant,
    }));
  }, [budgetSummary]);

  if (encounters.length === 0 && billings.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Financial Performance &amp; Fiscal Planning
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Department contributions, clinical service gross billings, payer yields, and operating variances.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No financial data available"
          description="Revenue analytics, department performance charts, and payer contribution metrics require hospital billing registers and clinical service orders. Upload your extracts to review performance."
          badge="Performance Inactive"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'Billing Register & Invoices (Invoice_ID, Billed_Amount, Bill_Date)',
            'Clinical Services & Order Items (Service_Code, Revenue_Centre)',
            'Inpatient Encounters (UHID, Admission_Date, Discharge_Date)',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Consolidated Top Banner */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Financial Performance &amp; Fiscal Planning
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Deterministic Financial Metrics
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Department contributions, clinical service gross billings, payer yields, and operating variances.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Primary Sub-tab switcher */}
            <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-semibold">
              <button
                onClick={() => setActiveSubTab('analytics')}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition cursor-pointer ${
                  activeSubTab === 'analytics'
                    ? 'bg-white text-teal-800 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <TrendingUp className="h-3.5 w-3.5" />
                <span>Financial Statements &amp; Analytics</span>
              </button>
              <button
                onClick={() => setActiveSubTab('budget')}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 transition cursor-pointer ${
                  activeSubTab === 'budget'
                    ? 'bg-white text-teal-800 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <BarChart3 className="h-3.5 w-3.5" />
                <span>Budget vs Actual Variance</span>
              </button>
            </div>

            {/* Timeframe Filter for Analytics */}
            {activeSubTab === 'analytics' && (
              <div className="flex items-center gap-2">
                <select
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800 focus:outline-teal-600"
                >
                  {availableMonths.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>

                <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-semibold">
                  {(['MONTH', 'QUARTER', 'YTD'] as const).map((tf) => (
                    <button
                      key={tf}
                      onClick={() => setTimeframe(tf)}
                      className={`rounded px-2.5 py-1 transition cursor-pointer ${
                        timeframe === tf
                          ? 'bg-teal-700 text-white shadow-2xs'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {tf === 'MONTH' ? 'Month' : tf === 'QUARTER' ? 'Quarter' : 'YTD'}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 4 Header Metric KPI Cards (strictly calculated from actual records) */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100 text-xs">
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">
              Gross Billed Revenue ({timeframe})
            </div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{formatINR(totalGrossBilled)}</div>
            <div className="mt-0.5 text-[10px] text-slate-500 font-medium">
              {filteredBillings.length} billing line items
            </div>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Revenue per Discharge</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">
              {noDischargesInPeriod ? 'N/A' : formatINR(revPerDischarge)}
            </div>
            <div className="mt-0.5 text-[10px] text-slate-500 font-medium">
              {noDischargesInPeriod
                ? 'No discharges in this period'
                : `${totalDischarges} verified discharges`}
            </div>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Average Bill Value</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{formatINR(avgBillValue)}</div>
            <div className="mt-0.5 text-[10px] text-slate-500 font-medium">
              Across {totalEncountersCount} encounters
            </div>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Active Departments</div>
            <div className="text-xl font-bold text-teal-800 mt-0.5">{revenueByDept.length} Operating Units</div>
            <div className="mt-0.5 text-[10px] text-slate-500 font-medium">
              Lineage: Inpatient &amp; Outpatient Billing
            </div>
          </div>
        </div>
      </div>

      {/* SUB-VIEW 1: FINANCIAL STATEMENTS & ANALYTICS */}
      {activeSubTab === 'analytics' && (
        <>
          {/* CHARTS ROW 1: Monthly Financial Trajectory & Payer Mix */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-8 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Hospital Revenue Trajectory</h2>
                  <p className="text-[11px] text-slate-500">
                    Actual billing totals grouped by recorded transaction dates
                  </p>
                </div>
                {monthlyTrendData.length <= 1 ? (
                  <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                    Single reporting month present in dataset
                  </span>
                ) : (
                  <span className="text-xs text-teal-800 font-semibold bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                    {monthlyTrendData.length} Accounting Periods
                  </span>
                )}
              </div>
              <div className="h-60">
                {monthlyTrendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={monthlyTrendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#64748b' }} />
                      <YAxis
                        tick={{ fontSize: 10, fill: '#64748b' }}
                        tickFormatter={(val) => `₹${(val / 100000).toFixed(0)}L`}
                      />
                      <Tooltip
                        formatter={(val: any) => [formatINR(Number(val) || 0), 'Gross Billed']}
                        contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', fontSize: '11px' }}
                      />
                      <Line type="monotone" dataKey="revenue" stroke="#0f766e" strokeWidth={3} dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                    Historical trend unavailable
                  </div>
                )}
              </div>
            </div>

            <div className="lg:col-span-4 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
              <div className="mb-4">
                <h2 className="text-sm font-bold text-slate-900">Payer Revenue Yield</h2>
                <p className="text-[11px] text-slate-500">Revenue contribution by payer category ({timeframe})</p>
              </div>
              {revenueByPayer.length > 0 ? (
                <>
                  <div className="h-44 flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={revenueByPayer}
                          cx="50%"
                          cy="50%"
                          innerRadius={40}
                          outerRadius={65}
                          paddingAngle={3}
                          dataKey="value"
                        >
                          {revenueByPayer.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(val: any) => [formatINR(Number(val) || 0)]}
                          contentStyle={{ backgroundColor: '#ffffff', borderRadius: '6px', fontSize: '10px' }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="space-y-1.5 mt-2">
                    {revenueByPayer.map((p) => (
                      <div key={p.name} className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1.5 text-slate-700">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: p.color }} />
                          {p.name}
                        </span>
                        <span className="font-semibold text-slate-900">{formatINR(p.value)}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-slate-400 text-xs">
                  Data not available for the selected period
                </div>
              )}
            </div>
          </div>

          {/* CHARTS ROW 2: Department Contribution & Revenue Centre */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-6 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
              <h2 className="text-sm font-bold text-slate-900 mb-1">Revenue by Operating Department</h2>
              <p className="text-[11px] text-slate-500 mb-4">
                Gross invoiced volume by operating department for {timeframe}
              </p>
              <div className="space-y-3">
                {revenueByDept.length > 0 ? (
                  revenueByDept.map((d) => (
                    <div key={d.department} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-slate-800">{d.department}</span>
                        <span className="font-bold text-slate-900">
                          {formatINR(d.amount)}{' '}
                          <span className="text-slate-400 font-normal">({d.percentage}%)</span>
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div
                          className="bg-teal-700 h-2 rounded-full transition-all"
                          style={{ width: `${Math.min(100, d.percentage)}%` }}
                        />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-slate-400 text-xs">
                    Data not available for the selected period
                  </div>
                )}
              </div>
            </div>

            <div className="lg:col-span-6 bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
              <h2 className="text-sm font-bold text-slate-900 mb-1">Revenue by Service Revenue Centre</h2>
              <p className="text-[11px] text-slate-500 mb-4">Direct billed clinical cost centres</p>
              <div className="h-64">
                {revenueByRevCentre.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart layout="vertical" data={revenueByRevCentre} margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                      <XAxis
                        type="number"
                        tick={{ fontSize: 9, fill: '#64748b' }}
                        tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
                      />
                      <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: '#334155' }} width={90} />
                      <Tooltip
                        formatter={(val: any) => [formatINR(Number(val) || 0), 'Revenue']}
                        contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', fontSize: '11px' }}
                      />
                      <Bar dataKey="amount" fill="#0d9488" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                    Data not available for the selected period
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* SUB-VIEW 2: BUDGET VS ACTUAL VARIANCE */}
      {activeSubTab === 'budget' && (
        <div className="space-y-6">
          {budgetSummary ? (
            <>
              {/* Department Variance Chart */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
                <h2 className="text-sm font-bold text-slate-900 mb-1">
                  Departmental Operating Variance (Actual vs Target)
                </h2>
                <p className="text-[11px] text-slate-500 mb-4">
                  Deterministic comparison between verified budget schedules and actual hospital billing.
                </p>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={deptVarianceChartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                      <XAxis dataKey="department" tick={{ fontSize: 10, fill: '#475569' }} />
                      <YAxis
                        tick={{ fontSize: 10, fill: '#64748b' }}
                        tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`}
                      />
                      <Tooltip
                        formatter={(val: any) => [formatINR(Number(val) || 0)]}
                        contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', fontSize: '11px' }}
                      />
                      <Legend />
                      <Bar dataKey="budget" name="Revenue Budget" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="actual" name="Actual Revenue" fill="#0f766e" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Department Variance Table */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
                <h2 className="text-sm font-bold text-slate-900 mb-1">Department Fiscal Variance Matrix</h2>
                <p className="text-[11px] text-slate-500 mb-4">
                  Breakdown of budget plan against recorded patient billings and direct expenses.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-700">
                    <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
                      <tr>
                        <th className="py-2.5 px-3 font-semibold">Department</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Revenue Budget</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Revenue Actual</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Variance (INR)</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Variance %</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Expense Budget</th>
                        <th className="py-2.5 px-3 font-semibold text-right">Expense Actual</th>
                        <th className="py-2.5 px-3 font-semibold text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-[11px]">
                      {budgetSummary.departmentSummaries.map((row) => (
                        <tr key={row.department} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3 font-semibold text-slate-900">{row.department}</td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {formatINR(row.revenueBudget)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-900">
                            {formatINR(row.revenueActual)}
                          </td>
                          <td
                            className={`py-2.5 px-3 text-right font-mono font-semibold ${
                              row.revenueVariance >= 0 ? 'text-emerald-700' : 'text-red-700'
                            }`}
                          >
                            {formatINR(row.revenueVariance)}
                          </td>
                          <td
                            className={`py-2.5 px-3 text-right font-mono font-bold ${
                              row.revenueVariancePercent >= 0 ? 'text-emerald-700' : 'text-red-700'
                            }`}
                          >
                            {row.revenueVariancePercent > 0 ? `+${row.revenueVariancePercent}` : row.revenueVariancePercent}%
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {formatINR(row.expenseBudget)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-500">
                            {row.expenseActual !== null ? (
                              <span className="font-semibold text-slate-800">{formatINR(row.expenseActual)}</span>
                            ) : (
                              <span className="italic text-slate-400">Not available</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            {row.isSignificant ? (
                              <span className="rounded bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-800 border border-amber-200">
                                Attention Needed
                              </span>
                            ) : (
                              <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
                                On Plan
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500 text-sm">
              Data not available for the selected period
            </div>
          )}
        </div>
      )}
    </div>
  );
};
