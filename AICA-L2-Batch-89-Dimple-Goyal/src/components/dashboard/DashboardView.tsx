import React, { useState, useMemo } from 'react';
import {
  TrendingUp,
  Clock,
  Landmark,
  ShieldCheck,
  Scale,
  ArrowRight,
  AlertTriangle,
  FileText,
  Calendar,
  Users,
  Filter,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Layers,
  ChevronRight,
  X,
  CheckCircle2,
  RefreshCw,
  Eye
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from 'recharts';
import { useApp } from '../../context/AppContext';
import { formatINR, formatINRCompact } from '../../utils/formatters';
import { computeBucketSummaries } from '../../utils/ageingEngine';
import { ActiveTab } from '../layout/Sidebar';
import { Invoice } from '../../types';

interface DashboardViewProps {
  onNavigate: (tab: ActiveTab) => void;
}

type Timeframe = 'ALL' | 'Q3' | 'Q2' | 'Q1' | 'M30';
type ChartTab = 'overview' | 'cashflow' | 'ageing' | 'statutory';

const AGEING_COLORS = {
  'Not Due': '#10b981', // Emerald
  '0–30 Days': '#f59e0b', // Amber
  '31–60 Days': '#f97316', // Orange
  '61–90 Days': '#ea580c', // Deep orange
  'Over 90 Days': '#e11d48', // Crimson rose
};

export const DashboardView: React.FC<DashboardViewProps> = ({ onNavigate }) => {
  const { kpis, invoices, customers, bankTransactions, tdsRecords, gstRecords, allocations } = useApp();

  // Interactive filters
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>('ALL');
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('ALL');
  const [activeChartTab, setActiveChartTab] = useState<ChartTab>('overview');
  const [ageingChartType, setAgeingChartType] = useState<'donut' | 'bars'>('donut');
  const [metricMode, setMetricMode] = useState<'gross' | 'net'>('gross');

  // Drill-down Modal State
  const [drillDownTitle, setDrillDownTitle] = useState<string | null>(null);
  const [drillDownInvoices, setDrillDownInvoices] = useState<Invoice[]>([]);
  const [hoveredAgeingBucket, setHoveredAgeingBucket] = useState<string | null>(null);

  // Filtered invoices based on customer & timeframe
  const filteredInvoices = useMemo(() => {
    return invoices.filter(inv => {
      if (selectedCustomerId !== 'ALL' && inv.customerId !== selectedCustomerId) {
        return false;
      }
      if (selectedTimeframe === 'Q1') {
        return inv.invoiceDate >= '2026-04-01' && inv.invoiceDate <= '2026-06-30';
      }
      if (selectedTimeframe === 'Q2') {
        return inv.invoiceDate >= '2026-07-01' && inv.invoiceDate <= '2026-09-30';
      }
      if (selectedTimeframe === 'Q3') {
        return inv.invoiceDate >= '2026-10-01' && inv.invoiceDate <= '2026-12-31';
      }
      if (selectedTimeframe === 'M30') {
        return inv.invoiceDate >= '2026-08-15';
      }
      return true;
    });
  }, [invoices, selectedCustomerId, selectedTimeframe]);

  // Compute dynamic KPIs for the filtered selection
  const dynamicStats = useMemo(() => {
    const totalBilled = filteredInvoices.reduce((s, i) => s + (metricMode === 'gross' ? i.totalInvoiceValue : (i.netReceivable || i.totalInvoiceValue)), 0);
    const totalOutstanding = filteredInvoices.reduce((s, i) => s + i.balance, 0);
    const totalCollected = filteredInvoices.reduce((s, i) => s + (i.amountAllocated || i.amountReceived || 0), 0);
    const overdueInvoices = filteredInvoices.filter(i => i.status === 'Overdue');
    const totalOverdue = overdueInvoices.reduce((s, i) => s + i.balance, 0);
    const efficiency = totalBilled > 0 ? (totalCollected / totalBilled) * 100 : 0;

    return {
      totalBilled,
      totalOutstanding,
      totalCollected,
      totalOverdue,
      overdueCount: overdueInvoices.length,
      efficiency,
      count: filteredInvoices.length
    };
  }, [filteredInvoices, metricMode]);

  // Receivables Ageing Bucket Summaries
  const bucketSummaries = useMemo(() => {
    return computeBucketSummaries(filteredInvoices);
  }, [filteredInvoices]);

  // Monthly Billed vs Collected Trend Data
  const monthlyTrendData = useMemo(() => {
    const monthKeys = [
      { key: '2026-04', label: 'Apr 26', q: 'Q1' },
      { key: '2026-05', label: 'May 26', q: 'Q1' },
      { key: '2026-06', label: 'Jun 26', q: 'Q1' },
      { key: '2026-07', label: 'Jul 26', q: 'Q2' },
      { key: '2026-08', label: 'Aug 26', q: 'Q2' },
      { key: '2026-09', label: 'Sep 26', q: 'Q2' },
      { key: '2026-10', label: 'Oct 26', q: 'Q3' },
      { key: '2026-11', label: 'Nov 26', q: 'Q3' },
      { key: '2026-12', label: 'Dec 26', q: 'Q3' },
      { key: '2027-01', label: 'Jan 27', q: 'Q4' },
      { key: '2027-02', label: 'Feb 27', q: 'Q4' },
      { key: '2027-03', label: 'Mar 27', q: 'Q4' }
    ];

    return monthKeys.map(m => {
      const monthInvoices = invoices.filter(inv => {
        const matchesMonth = inv.invoiceDate.startsWith(m.key);
        const matchesCust = selectedCustomerId === 'ALL' || inv.customerId === selectedCustomerId;
        return matchesMonth && matchesCust;
      });

      const billed = monthInvoices.reduce((s, i) => s + (metricMode === 'gross' ? i.totalInvoiceValue : (i.netReceivable || i.totalInvoiceValue)), 0);
      const collected = monthInvoices.reduce((s, i) => s + (i.amountAllocated || i.amountReceived || 0), 0);
      const efficiency = billed > 0 ? Math.min(100, Math.round((collected / billed) * 100)) : (collected > 0 ? 100 : 0);

      return {
        month: m.label,
        key: m.key,
        quarter: m.q,
        billed,
        collected,
        efficiency,
        invoices: monthInvoices
      };
    });
  }, [invoices, selectedCustomerId, metricMode]);

  // Top Debtors Exposure Data
  const topDebtorsData = useMemo(() => {
    return customers.map(cust => {
      const custInvoices = filteredInvoices.filter(i => i.customerId === cust.id);
      const totalBalance = custInvoices.reduce((s, i) => s + i.balance, 0);
      const overdueBalance = custInvoices.filter(i => i.status === 'Overdue').reduce((s, i) => s + i.balance, 0);
      const notDueBalance = Math.max(0, totalBalance - overdueBalance);
      const totalBilled = custInvoices.reduce((s, i) => s + i.totalInvoiceValue, 0);
      const creditUtil = cust.creditLimit > 0 ? Math.min(100, Math.round((totalBalance / cust.creditLimit) * 100)) : 0;

      return {
        id: cust.id,
        name: cust.name.length > 18 ? `${cust.name.substring(0, 16)}...` : cust.name,
        fullName: cust.name,
        totalBalance,
        overdue: overdueBalance,
        notDue: notDueBalance,
        creditLimit: cust.creditLimit,
        creditUtil,
        invoiceCount: custInvoices.length,
        invoices: custInvoices
      };
    })
    .filter(d => d.totalBalance > 0)
    .sort((a, b) => b.totalBalance - a.totalBalance)
    .slice(0, 6);
  }, [customers, filteredInvoices]);

  // Weekly Inflow Velocity Data
  const weeklyInflowData = useMemo(() => {
    return [
      { week: 'Wk 1 (Oct)', amount: 480000, target: 450000 },
      { week: 'Wk 2 (Oct)', amount: 620000, target: 450000 },
      { week: 'Wk 3 (Oct)', amount: 390000, target: 450000 },
      { week: 'Wk 4 (Oct)', amount: 750000, target: 450000 },
      { week: 'Wk 1 (Nov)', amount: 530000, target: 500000 },
      { week: 'Wk 2 (Nov)', amount: 890000, target: 500000 },
      { week: 'Wk 3 (Nov)', amount: 410000, target: 500000 },
      { week: 'Wk 4 (Nov)', amount: 980000, target: 500000 },
      { week: 'Wk 1 (Dec)', amount: 640000, target: 500000 },
      { week: 'Wk 2 (Dec)', amount: 780000, target: 500000 },
      { week: 'Wk 3 (Dec)', amount: 510000, target: 500000 },
      { week: 'Wk 4 (Dec)', amount: 840000, target: 500000 }
    ];
  }, []);

  // Statutory 3-Way Reconciliation Comparison Data
  const statutoryComparisonData = useMemo(() => {
    const totalGstReported = gstRecords.reduce((s, g) => s + (g.totalValue ?? g.total ?? 0), 0);
    const totalBankDeposits = bankTransactions
      .filter(t => t.isCredit || t.credit > 0 || t.type === 'Customer Receipt')
      .reduce((s, t) => s + (t.credit || t.amount || 0), 0);
    const totalBankAllocated = bankTransactions.reduce((s, t) => s + (t.allocatedAmount || 0), 0);

    return [
      {
        stream: 'Turnover (Sales)',
        booksValue: kpis.totalSales,
        statutoryValue: totalGstReported,
        variance: Math.abs(kpis.totalSales - totalGstReported),
        status: Math.abs(kpis.totalSales - totalGstReported) < 50000 ? 'Matched' : 'Variance'
      },
      {
        stream: 'TDS (Sec 194C/J)',
        booksValue: kpis.expectedTds,
        statutoryValue: kpis.reflectedTds,
        variance: kpis.mismatchTds,
        status: kpis.mismatchTds === 0 ? 'Matched' : 'Mismatch'
      },
      {
        stream: 'Bank vs Ledger',
        booksValue: totalBankDeposits,
        statutoryValue: totalBankAllocated,
        variance: kpis.unallocatedReceiptsAmount,
        status: kpis.unallocatedReceiptsAmount === 0 ? 'Settled' : 'Unallocated'
      }
    ];
  }, [kpis, gstRecords, bankTransactions]);

  // Open drilldown for specific bucket or selection
  const handleOpenBucketDrilldown = (bucketName: string) => {
    const matched = filteredInvoices.filter(inv => {
      if (bucketName === 'Not Due') return inv.status !== 'Overdue' && inv.balance > 0;
      if (bucketName === 'Over 90 Days') return inv.status === 'Overdue' && inv.balance > 0;
      return inv.balance > 0;
    });
    setDrillDownTitle(`Ageing Bucket: ${bucketName} (${matched.length} Invoices)`);
    setDrillDownInvoices(matched);
  };

  const handleOpenCustomerDrilldown = (customerName: string, customerInvoices: Invoice[]) => {
    setDrillDownTitle(`Debtor Invoices: ${customerName} (${customerInvoices.length} Bills)`);
    setDrillDownInvoices(customerInvoices);
  };

  return (
    <div className="space-y-6">
      {/* Top Header / Welcome & Quick Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Financial Receivables Dashboard</h1>
            <span className="text-[11px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-md">
              FY 2026-27 Live
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Interactive multi-graph intelligence across Sales Billed, Collections, Ageing Buckets, and Statutory TDS/GST.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate('reconciliation')}
            className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Scale className="w-4 h-4" />
            <span>Reconciliation Centre</span>
          </button>
        </div>
      </div>

      {/* Interactive Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Timeframe Filter Pills */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
            <span className="text-slate-400 px-1.5 font-bold uppercase text-[10px]">Period:</span>
            {[
              { id: 'ALL', label: 'All FY 26-27' },
              { id: 'Q3', label: 'Q3 (Oct-Dec)' },
              { id: 'Q2', label: 'Q2 (Jul-Sep)' },
              { id: 'Q1', label: 'Q1 (Apr-Jun)' },
              { id: 'M30', label: 'Last 30 Days' }
            ].map(t => (
              <button
                key={t.id}
                onClick={() => setSelectedTimeframe(t.id as Timeframe)}
                className={`px-2.5 py-1 rounded-md font-bold transition-colors ${
                  selectedTimeframe === t.id
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Customer Filter Dropdown */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedCustomerId}
              onChange={e => setSelectedCustomerId(e.target.value)}
              className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-white focus:bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="ALL">All Debtors ({customers.length})</option>
              {customers.map(c => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Metric Mode Toggle */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs">
            <button
              onClick={() => setMetricMode('gross')}
              className={`px-2 py-0.5 rounded font-bold text-[11px] transition-colors ${
                metricMode === 'gross' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Gross Value
            </button>
            <button
              onClick={() => setMetricMode('net')}
              className={`px-2 py-0.5 rounded font-bold text-[11px] transition-colors ${
                metricMode === 'net' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Net Ex-TDS
            </button>
          </div>
        </div>

        {/* Reset Filter Button if active */}
        {(selectedTimeframe !== 'ALL' || selectedCustomerId !== 'ALL') && (
          <button
            onClick={() => {
              setSelectedTimeframe('ALL');
              setSelectedCustomerId('ALL');
            }}
            className="text-xs font-bold text-rose-600 hover:text-rose-800 flex items-center gap-1 self-end lg:self-auto"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Reset Filters</span>
          </button>
        )}
      </div>

      {/* Action Required Alert Section */}
      <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-4 shadow-xs">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
            </span>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
              Immediate Action Required ({kpis.openExceptionsCount} Issues Detected)
            </h2>
          </div>
          <span className="text-[11px] text-slate-500">Click any card to resolve directly</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div
            onClick={() => onNavigate('ageing')}
            className="p-3 bg-white rounded-lg border border-rose-200 hover:border-rose-400 hover:shadow-sm cursor-pointer transition-all flex items-center justify-between"
          >
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-rose-700">
                <span className="w-2 h-2 rounded-full bg-rose-600 inline-block" />
                <span>{dynamicStats.overdueCount} Invoices Overdue</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium">{formatINR(dynamicStats.totalOverdue)} total overdue</p>
            </div>
            <ArrowRight className="w-4 h-4 text-rose-500" />
          </div>

          <div
            onClick={() => onNavigate('reconciliation')}
            className="p-3 bg-white rounded-lg border border-rose-200 hover:border-rose-400 hover:shadow-sm cursor-pointer transition-all flex items-center justify-between"
          >
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-rose-700">
                <span className="w-2 h-2 rounded-full bg-rose-600 inline-block" />
                <span>{kpis.unallocatedReceiptsCount} Unmatched Receipts</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium">{formatINR(kpis.unallocatedReceiptsAmount)} in suspense</p>
            </div>
            <ArrowRight className="w-4 h-4 text-rose-500" />
          </div>

          <div
            onClick={() => onNavigate('tds')}
            className="p-3 bg-white rounded-lg border border-amber-200 hover:border-amber-400 hover:shadow-sm cursor-pointer transition-all flex items-center justify-between"
          >
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800">
                <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                <span>TDS 26AS Variance</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium">{formatINR(kpis.mismatchTds)} to be reconciled</p>
            </div>
            <ArrowRight className="w-4 h-4 text-amber-600" />
          </div>

          <div
            onClick={() => onNavigate('invoices')}
            className="p-3 bg-white rounded-lg border border-amber-200 hover:border-amber-400 hover:shadow-sm cursor-pointer transition-all flex items-center justify-between"
          >
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800">
                <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                <span>{kpis.partiallyAllocatedCount} Partial Payments</span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium">Follow up for unpaid balances</p>
            </div>
            <ArrowRight className="w-4 h-4 text-amber-600" />
          </div>
        </div>
      </div>

      {/* 5 Core Pillars KPI Groups (Dynamically Responsive) */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        {/* Pillar 1: Sales */}
        <div
          onClick={() => onNavigate('invoices')}
          className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Total Billed</span>
            <TrendingUp className="w-4 h-4 text-slate-400 group-hover:text-emerald-700 transition-colors" />
          </div>
          <div className="text-xl font-bold text-slate-900">{formatINR(dynamicStats.totalBilled, false)}</div>
          <div className="mt-2 text-[11px] text-slate-500 space-y-0.5">
            <div className="flex justify-between">
              <span>Selected Scope:</span>
              <span className="font-semibold text-slate-800">{dynamicStats.count} Invoices</span>
            </div>
            <div className="flex justify-between">
              <span>This Month:</span>
              <span className="font-semibold text-slate-800">{formatINR(kpis.currentMonthSales, false)}</span>
            </div>
          </div>
        </div>

        {/* Pillar 2: Receivables Outstanding */}
        <div
          onClick={() => onNavigate('ageing')}
          className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Outstanding</span>
            <Clock className="w-4 h-4 text-slate-400 group-hover:text-amber-700 transition-colors" />
          </div>
          <div className="text-xl font-bold text-amber-800">{formatINR(dynamicStats.totalOutstanding, false)}</div>
          <div className="mt-2 text-[11px] text-slate-500 space-y-0.5">
            <div className="flex justify-between text-rose-700 font-medium">
              <span>Overdue:</span>
              <span className="font-bold">{formatINR(dynamicStats.totalOverdue, false)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Not Due:</span>
              <span className="font-semibold">{formatINR(Math.max(0, dynamicStats.totalOutstanding - dynamicStats.totalOverdue), false)}</span>
            </div>
          </div>
        </div>

        {/* Pillar 3: Collections */}
        <div
          onClick={() => onNavigate('payments')}
          className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Collections</span>
            <Landmark className="w-4 h-4 text-slate-400 group-hover:text-emerald-700 transition-colors" />
          </div>
          <div className="text-xl font-bold text-emerald-800">{formatINR(dynamicStats.totalCollected, false)}</div>
          <div className="mt-2 text-[11px] text-slate-500 space-y-0.5">
            <div className="flex justify-between">
              <span>Efficiency Rate:</span>
              <span className="font-bold text-emerald-700">{dynamicStats.efficiency.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between text-rose-600">
              <span>Unallocated:</span>
              <span className="font-semibold">{kpis.unallocatedReceiptsCount} Txns</span>
            </div>
          </div>
        </div>

        {/* Pillar 4: TDS (Form 26AS / AIS) */}
        <div
          onClick={() => onNavigate('tds')}
          className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">TDS 26AS / AIS</span>
            <ShieldCheck className="w-4 h-4 text-slate-400 group-hover:text-purple-700 transition-colors" />
          </div>
          <div className="text-xl font-bold text-slate-900">{formatINR(kpis.reflectedTds, false)}</div>
          <div className="mt-2 text-[11px] text-slate-500 space-y-0.5">
            <div className="flex justify-between">
              <span>Expected:</span>
              <span className="font-semibold">{formatINR(kpis.expectedTds, false)}</span>
            </div>
            <div className="flex justify-between text-rose-600 font-medium">
              <span>Mismatch:</span>
              <span className="font-bold">{formatINR(kpis.mismatchTds, false)}</span>
            </div>
          </div>
        </div>

        {/* Pillar 5: Reconciliation Health & DSO */}
        <div
          onClick={() => onNavigate('reconciliation')}
          className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 shadow-xs cursor-pointer transition-all group"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">DSO & Auto-Match</span>
            <Scale className="w-4 h-4 text-slate-400 group-hover:text-blue-700 transition-colors" />
          </div>
          <div className="text-xl font-bold text-slate-900">{kpis.dsoDays} Days</div>
          <div className="mt-2 text-[11px] text-slate-500 space-y-0.5">
            <div className="flex justify-between">
              <span>Matched:</span>
              <span className="font-semibold text-emerald-700">{kpis.matchedTransactionsCount} Settled</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Exceptions:</span>
              <span className="font-semibold text-rose-700">{kpis.openExceptionsCount} Open</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chart Navigation Tabs */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-5 text-xs font-semibold gap-3 shadow-xs">
        {[
          { id: 'overview', label: 'Overview Cockpit (All Graphs)', icon: Layers },
          { id: 'cashflow', label: 'Cashflow & Collections Trend', icon: BarChart3 },
          { id: 'ageing', label: 'Receivables Ageing & Risk Profile', icon: PieChartIcon },
          { id: 'statutory', label: 'Statutory & TDS 26AS Matching', icon: ShieldCheck }
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveChartTab(tab.id as ChartTab)}
              className={`py-3.5 border-b-2 flex items-center gap-2 transition-colors ${
                activeChartTab === tab.id
                  ? 'border-emerald-600 text-emerald-700 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* GRAPH SECTION: Overview Cockpit or Specific Graph Tab */}
      <div className="space-y-6">
        {/* GRAPH 1: Monthly Billed vs Collections Trend */}
        {(activeChartTab === 'overview' || activeChartTab === 'cashflow') && (
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
              <div>
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-emerald-700" />
                  <span>Monthly Sales Billed vs. Cash Collections Trend</span>
                </h3>
                <p className="text-xs text-slate-500">
                  Direct comparison of monthly invoicing (₹) against bank collections (₹) and collection ratio (%)
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-xs bg-slate-800 inline-block" />
                  <span className="text-slate-600 font-medium">Billed Amount</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-xs bg-emerald-600 inline-block" />
                  <span className="text-slate-600 font-medium">Collected Cash</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 bg-amber-500 inline-block rounded-full" />
                  <span className="text-slate-600 font-medium">Collection %</span>
                </div>
              </div>
            </div>

            <div className="h-[290px] w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={monthlyTrendData}
                  margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={{ stroke: '#e2e8f0' }} />
                  <YAxis
                    yAxisId="left"
                    tickFormatter={(val) => `₹${(val / 100000).toFixed(0)}L`}
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    axisLine={{ stroke: '#e2e8f0' }}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    domain={[0, 120]}
                    tickFormatter={(val) => `${val}%`}
                    tick={{ fontSize: 11, fill: '#f59e0b' }}
                    axisLine={{ stroke: '#fef3c7' }}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        const billedVal = Number(payload[0]?.value || 0);
                        const colVal = Number(payload[1]?.value || 0);
                        const effVal = Number(payload[2]?.value || 0);
                        const gap = billedVal - colVal;
                        return (
                          <div className="bg-white p-3 rounded-xl shadow-lg border border-slate-200 text-xs space-y-1.5 min-w-[200px]">
                            <p className="font-bold text-slate-900 border-b border-slate-100 pb-1">{label} (FY 2026-27)</p>
                            <div className="flex justify-between text-slate-700">
                              <span>Total Billed:</span>
                              <strong className="font-mono font-bold text-slate-900">{formatINR(billedVal)}</strong>
                            </div>
                            <div className="flex justify-between text-emerald-700">
                              <span>Cash Collected:</span>
                              <strong className="font-mono font-bold">{formatINR(colVal)}</strong>
                            </div>
                            <div className="flex justify-between text-amber-700 border-t border-slate-100 pt-1">
                              <span>Collection Ratio:</span>
                              <strong className="font-bold">{effVal}%</strong>
                            </div>
                            <div className="flex justify-between text-rose-600">
                              <span>Unsettled Gap:</span>
                              <strong className="font-mono font-bold">{formatINR(Math.max(0, gap))}</strong>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar yAxisId="left" dataKey="billed" fill="#1e293b" radius={[4, 4, 0, 0]} maxBarSize={32} />
                  <Bar yAxisId="left" dataKey="collected" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={32} />
                  <Line yAxisId="right" type="monotone" dataKey="efficiency" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 3, fill: '#f59e0b' }} activeDot={{ r: 5 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Peak Collection: <strong>September 2026 (₹24.8 Lakhs)</strong></span>
              </span>
              <span>Click any bar or slice to view underlying invoice ledger</span>
            </div>
          </div>
        )}

        {/* GRAPH 2 & 3: Ageing Distribution (Donut) and Top Debtors Exposure (Horizontal Bars) */}
        {(activeChartTab === 'overview' || activeChartTab === 'ageing') && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Ageing Donut Chart */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    <PieChartIcon className="w-4 h-4 text-emerald-700" />
                    <span>Receivables Ageing Distribution</span>
                  </h3>
                  <p className="text-xs text-slate-500">Breakdown of outstanding invoices by due date buckets</p>
                </div>
                <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
                  <button
                    onClick={() => setAgeingChartType('donut')}
                    className={`px-2 py-0.5 rounded font-bold text-[11px] transition-colors ${
                      ageingChartType === 'donut' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500'
                    }`}
                  >
                    Donut
                  </button>
                  <button
                    onClick={() => setAgeingChartType('bars')}
                    className={`px-2 py-0.5 rounded font-bold text-[11px] transition-colors ${
                      ageingChartType === 'bars' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500'
                    }`}
                  >
                    Bars
                  </button>
                </div>
              </div>

              {ageingChartType === 'donut' ? (
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 py-2">
                  <div className="h-[230px] w-[230px] relative flex items-center justify-center shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={bucketSummaries}
                          dataKey="amount"
                          nameKey="bucketName"
                          cx="50%"
                          cy="50%"
                          innerRadius={62}
                          outerRadius={88}
                          paddingAngle={3}
                          onMouseEnter={(_, index) => {
                            setHoveredAgeingBucket(bucketSummaries[index]?.bucketName || null);
                          }}
                          onMouseLeave={() => setHoveredAgeingBucket(null)}
                          onClick={(entry: any) => {
                            const bName = entry?.bucketName || entry?.name || (entry?.payload && entry.payload.bucketName);
                            if (bName) handleOpenBucketDrilldown(bName);
                          }}
                          cursor="pointer"
                        >
                          {bucketSummaries.map((entry) => (
                            <Cell
                              key={`cell-${entry.bucketName}`}
                              fill={(AGEING_COLORS as any)[entry.bucketName] || '#94a3b8'}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: any) => [formatINR(Number(value)), 'Outstanding']}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    {/* Inner Label */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Total Unpaid</span>
                      <span className="text-sm font-bold text-slate-900 font-mono">
                        {formatINRCompact(dynamicStats.totalOutstanding)}
                      </span>
                      <span className="text-[10px] text-rose-600 font-semibold">
                        {((dynamicStats.totalOverdue / (dynamicStats.totalOutstanding || 1)) * 100).toFixed(0)}% Overdue
                      </span>
                    </div>
                  </div>

                  {/* Bucket Summary Legend */}
                  <div className="space-y-2 flex-1 w-full text-xs">
                    {bucketSummaries.map((b) => (
                      <div
                        key={b.bucketName}
                        onClick={() => handleOpenBucketDrilldown(b.bucketName)}
                        className={`p-1.5 rounded-lg border flex items-center justify-between cursor-pointer transition-all ${
                          hoveredAgeingBucket === b.bucketName
                            ? 'bg-slate-50 border-slate-400 shadow-xs'
                            : 'border-slate-100 hover:bg-slate-50/70'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: (AGEING_COLORS as any)[b.bucketName] || '#94a3b8' }}
                          />
                          <span className="font-semibold text-slate-800">{b.bucketName}</span>
                          <span className="text-slate-400 text-[10px]">({b.invoiceCount})</span>
                        </div>
                        <div className="text-right">
                          <span className="font-mono font-bold text-slate-900">{formatINR(b.amount, false)}</span>
                          <span className="text-[10px] text-slate-500 ml-1">({b.percentage.toFixed(0)}%)</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-3 py-3">
                  {bucketSummaries.map((b) => (
                    <div
                      key={b.bucketName}
                      onClick={() => handleOpenBucketDrilldown(b.bucketName)}
                      className="space-y-1 cursor-pointer group"
                    >
                      <div className="flex justify-between text-xs font-medium">
                        <span className="text-slate-700 group-hover:text-emerald-800 font-semibold">
                          {b.bucketName} ({b.invoiceCount} invoices)
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-slate-900">{formatINR(b.amount, false)}</span>
                          <span className="text-slate-400 text-[11px]">({b.percentage.toFixed(1)}%)</span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                        <div
                          className="h-2.5 rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.max(b.percentage > 0 ? 3 : 0, b.percentage)}%`,
                            backgroundColor: (AGEING_COLORS as any)[b.bucketName] || '#94a3b8'
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>DSO: <strong className="text-slate-800">{kpis.dsoDays} days</strong></span>
                <button
                  onClick={() => onNavigate('ageing')}
                  className="font-bold text-emerald-800 hover:text-emerald-950 flex items-center gap-1"
                >
                  <span>View Ageing Table</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Top Debtors Exposure (Horizontal Stacked BarChart) */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                      <Users className="w-4 h-4 text-emerald-700" />
                      <span>Debtor Concentration & Overdue Exposure</span>
                    </h3>
                    <p className="text-xs text-slate-500">Top 6 customers by unpaid receivables and overdue risk</p>
                  </div>
                  <button
                    onClick={() => onNavigate('customers')}
                    className="text-xs font-bold text-emerald-800 hover:text-emerald-950"
                  >
                    View All
                  </button>
                </div>

                <div className="h-[230px] w-full pt-1">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      layout="vertical"
                      data={topDebtorsData}
                      margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                      <XAxis
                        type="number"
                        tickFormatter={(val) => `₹${(val / 100000).toFixed(0)}L`}
                        tick={{ fontSize: 10, fill: '#64748b' }}
                        axisLine={{ stroke: '#e2e8f0' }}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 10, fill: '#334155', fontWeight: 600 }}
                        axisLine={{ stroke: '#e2e8f0' }}
                        width={90}
                      />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const data = payload[0]?.payload;
                            return (
                              <div className="bg-white p-3 rounded-xl shadow-lg border border-slate-200 text-xs space-y-1 min-w-[210px]">
                                <p className="font-bold text-slate-900 border-b border-slate-100 pb-1">{data.fullName}</p>
                                <div className="flex justify-between text-slate-700">
                                  <span>Total Outstanding:</span>
                                  <strong className="font-mono">{formatINR(data.totalBalance)}</strong>
                                </div>
                                <div className="flex justify-between text-rose-600 font-bold">
                                  <span>Overdue Amount:</span>
                                  <strong className="font-mono">{formatINR(data.overdue)}</strong>
                                </div>
                                <div className="flex justify-between text-emerald-700">
                                  <span>Current / Not Due:</span>
                                  <strong className="font-mono">{formatINR(data.notDue)}</strong>
                                </div>
                                <div className="flex justify-between text-slate-500 pt-1 border-t border-slate-100 text-[10px]">
                                  <span>Credit Limit:</span>
                                  <span>{formatINR(data.creditLimit, false)} ({data.creditUtil}% used)</span>
                                </div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Bar dataKey="notDue" stackId="a" fill="#3b82f6" name="Not Due" radius={[0, 0, 0, 0]} />
                      <Bar dataKey="overdue" stackId="a" fill="#e11d48" name="Overdue" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 text-[11px] text-blue-700 font-medium">
                    <span className="w-2 h-2 rounded-full bg-blue-500" /> Current
                  </span>
                  <span className="flex items-center gap-1 text-[11px] text-rose-700 font-medium">
                    <span className="w-2 h-2 rounded-full bg-rose-600" /> Overdue
                  </span>
                </div>
                <button
                  onClick={() => onNavigate('customers')}
                  className="font-bold text-slate-600 hover:text-slate-900 flex items-center gap-1"
                >
                  <span>Open Customer 360</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* GRAPH 4 & 5: Weekly Inflow Velocity & Statutory 3-Way Match */}
        {(activeChartTab === 'overview' || activeChartTab === 'statutory' || activeChartTab === 'cashflow') && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Weekly Cashflow Velocity Area Chart */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    <Activity className="w-4 h-4 text-emerald-700" />
                    <span>Weekly Cash Inflow Velocity (₹)</span>
                  </h3>
                  <p className="text-xs text-slate-500">Deposit run-rate against collection targets across recent weeks</p>
                </div>
                <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Target: ₹5L/Wk
                </span>
              </div>

              <div className="h-[210px] w-full pt-1">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={weeklyInflowData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                    <defs>
                      <linearGradient id="colorCashInflow" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="week" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={{ stroke: '#e2e8f0' }} />
                    <YAxis
                      tickFormatter={(val) => `₹${(val / 100000).toFixed(0)}L`}
                      tick={{ fontSize: 10, fill: '#64748b' }}
                      axisLine={{ stroke: '#e2e8f0' }}
                    />
                    <Tooltip
                      formatter={(value: any) => [formatINR(Number(value)), 'Deposited']}
                      labelFormatter={(label) => `Week: ${label}`}
                    />
                    <ReferenceLine y={500000} stroke="#94a3b8" strokeDasharray="3 3" label={{ value: 'Target', fill: '#64748b', fontSize: 10 }} />
                    <Area
                      type="monotone"
                      dataKey="amount"
                      stroke="#059669"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#colorCashInflow)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>Avg Weekly Deposits: <strong>₹6.5 Lakhs</strong></span>
                <span className="text-emerald-700 font-bold">+14% above target</span>
              </div>
            </div>

            {/* Statutory 3-Way Reconciliation Integrity Comparison */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-purple-700" />
                    <span>Statutory 3-Way Reconciliation Comparison</span>
                  </h3>
                  <p className="text-xs text-slate-500">Books of Accounts vs GST Portal (GSTR-1) & Form 26AS</p>
                </div>
                <button
                  onClick={() => onNavigate('tds')}
                  className="text-xs font-bold text-purple-800 hover:text-purple-950"
                >
                  Audit Centre
                </button>
              </div>

              <div className="space-y-3 py-2">
                {statutoryComparisonData.map((item) => (
                  <div key={item.stream} className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-900">{item.stream}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          item.status === 'Matched' || item.status === 'Settled'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-900'
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-[10px] text-slate-400 block">Ledger Books</span>
                        <span className="font-mono font-bold text-slate-800">{formatINR(item.booksValue, false)}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 block">Portal / Bank</span>
                        <span className="font-mono font-bold text-slate-800">{formatINR(item.statutoryValue, false)}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 block">Variance</span>
                        <span
                          className={`font-mono font-bold ${
                            item.variance === 0 ? 'text-emerald-700' : 'text-rose-600'
                          }`}
                        >
                          {formatINR(item.variance, false)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>GST Outward Liability: <strong className="text-slate-800">Reconciled</strong></span>
                <span className="text-purple-700 font-semibold cursor-pointer" onClick={() => onNavigate('gst')}>
                  Open GSTR-1 Audit →
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Drilldown Modal */}
      {drillDownTitle && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-100">
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col border border-slate-200">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50 rounded-t-xl">
              <div>
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-700" />
                  <span>{drillDownTitle}</span>
                </h3>
                <p className="text-xs text-slate-500">Detailed records breakdown for this graph selection</p>
              </div>
              <button
                onClick={() => setDrillDownTitle(null)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 text-xs">
              {drillDownInvoices.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  <p>No individual open invoices found in this specific segment.</p>
                </div>
              ) : (
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-100/70 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase">
                        <th className="py-2.5 px-3">Invoice #</th>
                        <th className="py-2.5 px-3">Customer</th>
                        <th className="py-2.5 px-3">Date</th>
                        <th className="py-2.5 px-3">Due Date</th>
                        <th className="py-2.5 px-3 text-right">Total (₹)</th>
                        <th className="py-2.5 px-3 text-right">Balance (₹)</th>
                        <th className="py-2.5 px-3 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {drillDownInvoices.map((inv) => (
                        <tr key={inv.id} className="hover:bg-slate-50 transition-colors">
                          <td className="py-2.5 px-3 font-mono font-bold text-slate-900">{inv.invoiceNumber}</td>
                          <td className="py-2.5 px-3 font-semibold text-slate-800">{inv.customerName}</td>
                          <td className="py-2.5 px-3 text-slate-500">{inv.invoiceDate}</td>
                          <td className="py-2.5 px-3 text-slate-500">{inv.dueDate}</td>
                          <td className="py-2.5 px-3 font-mono text-right text-slate-700">{formatINR(inv.totalInvoiceValue, false)}</td>
                          <td className="py-2.5 px-3 font-mono font-bold text-right text-rose-600">{formatINR(inv.balance, false)}</td>
                          <td className="py-2.5 px-3 text-center">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                inv.status === 'Overdue'
                                  ? 'bg-rose-100 text-rose-800'
                                  : inv.status === 'Partially Paid'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-emerald-100 text-emerald-800'
                              }`}
                            >
                              {inv.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-slate-200 bg-slate-50 rounded-b-xl flex items-center justify-between text-xs">
              <span className="text-slate-500">
                Total Shown: <strong>{drillDownInvoices.length} invoices</strong>
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setDrillDownTitle(null);
                    onNavigate('invoices');
                  }}
                  className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow-xs flex items-center gap-1"
                >
                  <span>Open in Invoices Hub</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
