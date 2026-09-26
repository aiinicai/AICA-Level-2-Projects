import React from 'react';
import {
  TrendingUp,
  CreditCard,
  Building,
  PackageCheck,
  AlertTriangle,
  Clock,
  ArrowUpRight,
  ShieldCheck,
  ChevronRight,
  Sparkles,
  FileCheck,
  FileText,
  DollarSign,
  AlertCircle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  Account,
  Customer,
  SalesInvoice,
  StockItem,
  VendorBill,
} from '../../types';
import {
  calculateGSTPosition,
  computeInventoryProvision,
  computeScheduleIIICreditorAgeing,
  computeScheduleIIIDebtorAgeing,
  formatINR,
  formatLakhs,
} from '../../services/accountingEngine';
import { MainNavSection } from '../layout/Sidebar';

interface DashboardViewProps {
  accounts: Account[];
  salesInvoices: SalesInvoice[];
  vendorBills: VendorBill[];
  stockItems: StockItem[];
  customers: Customer[];
  onNavigate: (section: MainNavSection) => void;
  onOpenUpload: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  accounts,
  salesInvoices,
  vendorBills,
  stockItems,
  customers,
  onNavigate,
  onOpenUpload,
}) => {
  // Calculations
  const gstPosition = calculateGSTPosition(salesInvoices, vendorBills);

  const inventoryEval = computeInventoryProvision(stockItems, {
    slowMovingMonths: 3,
    deadStockMonths: 6,
    provision6To12MonthsPct: 25,
    provisionAbove12MonthsPct: 60,
  });

  const debtorAgeing = computeScheduleIIIDebtorAgeing(salesInvoices);
  const creditorAgeing = computeScheduleIIICreditorAgeing(vendorBills);

  // Balances
  const cashAndBank = accounts
    .filter((a) => a.subGroup === 'Cash & Cash Equivalents')
    .reduce((sum, a) => sum + a.balance, 0);

  const totalDebtors = salesInvoices
    .filter((i) => i.status !== 'PAID' && i.status !== 'REVIEW_QUEUE')
    .reduce((sum, i) => sum + (i.totalAmount - i.paymentReceived), 0);

  const totalCreditors = vendorBills
    .filter((b) => b.status !== 'PAID' && b.status !== 'REVIEW_QUEUE')
    .reduce((sum, b) => sum + (b.netPayable - b.paymentMade), 0);

  const msmeCreditors = vendorBills
    .filter((b) => b.isMsme && b.status !== 'PAID' && b.status !== 'REVIEW_QUEUE')
    .reduce((sum, b) => sum + (b.netPayable - b.paymentMade), 0);

  const ytdRevenue = accounts
    .filter((a) => a.category === 'INCOME')
    .reduce((sum, a) => sum + a.balance, 0);

  const mtdRevenue = salesInvoices
    .filter((i) => i.date.startsWith('2026-03') && i.status !== 'REVIEW_QUEUE')
    .reduce((sum, i) => sum + i.taxableAmount, 0);

  // Review Queue Items
  const reviewQueueInvoices = salesInvoices.filter((i) => i.status === 'REVIEW_QUEUE');
  const reviewQueueBills = vendorBills.filter((b) => b.status === 'REVIEW_QUEUE');
  const totalPendingReview = reviewQueueInvoices.length + reviewQueueBills.length;

  // Overdue Debtors (>6 months)
  const overdueDebtorsAmount = debtorAgeing.reduce(
    (sum, row) => sum + row.sixMonthsToOneYear + row.oneToTwoYears + row.twoToThreeYears + row.moreThanThreeYears,
    0
  );

  // 12-Month Revenue Trend Data
  const revenueTrendData = [
    { month: 'Apr 25', revenue: 3.1, ebitda: 0.65 },
    { month: 'May 25', revenue: 3.4, ebitda: 0.72 },
    { month: 'Jun 25', revenue: 3.8, ebitda: 0.81 },
    { month: 'Jul 25', revenue: 3.6, ebitda: 0.75 },
    { month: 'Aug 25', revenue: 4.0, ebitda: 0.88 },
    { month: 'Sep 25', revenue: 4.3, ebitda: 0.95 },
    { month: 'Oct 25', revenue: 4.1, ebitda: 0.89 },
    { month: 'Nov 25', revenue: 4.5, ebitda: 1.02 },
    { month: 'Dec 25', revenue: 4.8, ebitda: 1.10 },
    { month: 'Jan 26', revenue: 4.4, ebitda: 0.98 },
    { month: 'Feb 26', revenue: 4.7, ebitda: 1.05 },
    { month: 'Mar 26 (Est)', revenue: 5.1, ebitda: 1.18 },
  ];

  // Ageing Comparison Chart Data
  const ageingChartData = [
    { bucket: 'Not Due', Debtors: 955800, Creditors: 742080 },
    { bucket: '<6 Months', Debtors: 649000, Creditors: 372800 },
    { bucket: '6m - 1y', Debtors: 295000, Creditors: 0 },
    { bucket: '>1 Year', Debtors: 0, Creditors: 0 },
  ];

  return (
    <div id="cfo-dashboard-view" className="space-y-6">
      {/* Top Welcome & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Executive CFO Cockpit</h2>
            <span className="text-xs bg-indigo-500/10 text-indigo-300 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
              Live Double-Entry Sync
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time Schedule III financial positioning, statutory GST reconciliation & perpetual stock valuation.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate('compliance')}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>GST Filing Due Dates</span>
          </button>
          <button
            onClick={() => onNavigate('accounting')}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5 text-indigo-400" />
            <span>Schedule III Statements</span>
          </button>
        </div>
      </div>

      {/* 6 High-Level CFO KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
        {/* KPI 1: Revenue */}
        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl flex flex-col justify-between hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Revenue (YTD)</span>
            <span className="p-1 rounded bg-indigo-500/10 text-indigo-400">
              <TrendingUp className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-slate-100 font-mono">{formatLakhs(ytdRevenue)}</div>
            <div className="text-[11px] text-emerald-400 font-medium flex items-center gap-1 mt-0.5">
              <span>MTD: {formatLakhs(mtdRevenue)}</span>
              <span className="text-[10px] text-slate-400">• +14.2% YoY</span>
            </div>
          </div>
        </div>

        {/* KPI 2: Net GST Payable */}
        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl flex flex-col justify-between hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Net GST Liability</span>
            <span className="p-1 rounded bg-amber-500/10 text-amber-400">
              <CreditCard className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-amber-300 font-mono">
              {formatINR(gstPosition.totalNetGstPayable)}
            </div>
            <div className="text-[11px] text-slate-400 font-medium mt-0.5">
              Output: {formatLakhs(gstPosition.totalOutputGst)} | ITC: {formatLakhs(gstPosition.totalEligibleItc)}
            </div>
          </div>
        </div>

        {/* KPI 3: Cash & Bank */}
        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl flex flex-col justify-between hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Cash & Liquid Bank</span>
            <span className="p-1 rounded bg-emerald-500/10 text-emerald-400">
              <DollarSign className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-emerald-300 font-mono">{formatLakhs(cashAndBank)}</div>
            <div className="text-[11px] text-slate-400 font-medium mt-0.5">
              HDFC: ₹64.2L • ICICI: ₹21.5L
            </div>
          </div>
        </div>

        {/* KPI 4: Total Debtors */}
        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl flex flex-col justify-between hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Trade Receivables</span>
            <span className="p-1 rounded bg-blue-500/10 text-blue-400">
              <Building className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-slate-100 font-mono">{formatLakhs(totalDebtors)}</div>
            <div className="text-[11px] text-amber-400 font-medium mt-0.5">
              DSO: 42 Days • Overdue: {formatLakhs(overdueDebtorsAmount)}
            </div>
          </div>
        </div>

        {/* KPI 5: Total Creditors */}
        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl flex flex-col justify-between hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Trade Payables</span>
            <span className="p-1 rounded bg-purple-500/10 text-purple-400">
              <Clock className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-slate-100 font-mono">{formatLakhs(totalCreditors)}</div>
            <div className="text-[11px] text-purple-300 font-medium mt-0.5">
              MSME Share: {formatLakhs(msmeCreditors)} (Sec 43B)
            </div>
          </div>
        </div>

        {/* KPI 6: Inventory Value */}
        <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl flex flex-col justify-between hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Inventory (Perpetual)</span>
            <span className="p-1 rounded bg-teal-500/10 text-teal-400">
              <PackageCheck className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-slate-100 font-mono">
              {formatLakhs(inventoryEval.netInventoryValue)}
            </div>
            <div className="text-[11px] text-rose-400 font-medium mt-0.5">
              Provision: -{formatINR(inventoryEval.computedProvision)} (AS 2)
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: Live GST Statutory Engine Widget & Alerts Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* GST Statutory Engine Widget (Section 10 Spec) */}
        <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4 text-indigo-400" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">Real-time GST Liability & ITC Set-Off Engine</h3>
                <p className="text-[11px] text-slate-400">
                  Computed strictly per Rule 88A CGST Act (IGST → CGST → SGST statutory utilization hierarchy)
                </p>
              </div>
            </div>
            <button
              onClick={() => onNavigate('compliance')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 cursor-pointer"
            >
              <span>File GSTR Returns</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Breakdown Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            {/* Output Tax */}
            <div className="bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80">
              <div className="text-xs text-slate-400 font-medium">1. Output Tax Collected</div>
              <div className="text-base font-bold text-slate-100 font-mono mt-1">
                {formatINR(gstPosition.totalOutputGst)}
              </div>
              <div className="mt-2 space-y-1 text-[11px] text-slate-400 font-mono">
                <div className="flex justify-between">
                  <span>CGST (Intra-state):</span>
                  <span className="text-slate-200">{formatINR(gstPosition.outputCgst)}</span>
                </div>
                <div className="flex justify-between">
                  <span>SGST (Intra-state):</span>
                  <span className="text-slate-200">{formatINR(gstPosition.outputSgst)}</span>
                </div>
                <div className="flex justify-between">
                  <span>IGST (Inter-state):</span>
                  <span className="text-slate-200">{formatINR(gstPosition.outputIgst)}</span>
                </div>
              </div>
            </div>

            {/* Input Tax Credit */}
            <div className="bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80">
              <div className="text-xs text-slate-400 font-medium">2. Eligible ITC Available</div>
              <div className="text-base font-bold text-emerald-400 font-mono mt-1">
                {formatINR(gstPosition.totalEligibleItc)}
              </div>
              <div className="mt-2 space-y-1 text-[11px] text-slate-400 font-mono">
                <div className="flex justify-between">
                  <span>CGST ITC:</span>
                  <span className="text-slate-200">{formatINR(gstPosition.inputCgst)}</span>
                </div>
                <div className="flex justify-between">
                  <span>SGST ITC:</span>
                  <span className="text-slate-200">{formatINR(gstPosition.inputSgst)}</span>
                </div>
                <div className="flex justify-between">
                  <span>IGST ITC:</span>
                  <span className="text-slate-200">{formatINR(gstPosition.inputIgst)}</span>
                </div>
              </div>
              <div className="mt-2 pt-1.5 border-t border-slate-800/80 text-[10px] text-slate-400 flex justify-between">
                <span>Sec 17(5) Blocked ITC:</span>
                <span className="text-slate-400 font-mono">{formatINR(gstPosition.blockedItc)}</span>
              </div>
            </div>

            {/* Net GST Cash Payment */}
            <div className="bg-indigo-950/20 p-3.5 rounded-xl border border-indigo-500/30">
              <div className="text-xs text-indigo-300 font-semibold">3. Net GST Cash Payable</div>
              <div className="text-base font-bold text-indigo-200 font-mono mt-1">
                {formatINR(gstPosition.totalNetGstPayable)}
              </div>
              <div className="mt-2 space-y-1 text-[11px] font-mono text-indigo-300/80">
                <div className="flex justify-between">
                  <span>Net CGST:</span>
                  <span className="text-white font-medium">{formatINR(gstPosition.netCgstPayable)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Net SGST:</span>
                  <span className="text-white font-medium">{formatINR(gstPosition.netSgstPayable)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Net IGST:</span>
                  <span className="text-white font-medium">{formatINR(gstPosition.netIgstPayable)}</span>
                </div>
              </div>
              <div className="mt-2 pt-1.5 border-t border-indigo-500/20 text-[10px] text-emerald-400 font-medium">
                ITC Utilization Order Verified
              </div>
            </div>
          </div>

          {/* Statutory Filing Status strip */}
          <div className="mt-4 pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span className="text-slate-300 font-medium">GSTR-1 (Outward):</span>
                <span className="text-slate-400 font-mono text-[11px]">Due 11th Apr (Ready)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
                <span className="text-slate-300 font-medium">GSTR-3B (Summary):</span>
                <span className="text-slate-400 font-mono text-[11px]">Due 20th Apr (Pending Pay)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                <span className="text-slate-300 font-medium">GSTR-2B Recon:</span>
                <span className="text-emerald-400 font-mono text-[11px]">100% Matched</span>
              </div>
            </div>

            <button
              onClick={() => onNavigate('compliance')}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 text-[11px] font-medium transition-colors cursor-pointer"
            >
              Export GSTR-3B JSON
            </button>
          </div>
        </div>

        {/* CFO Critical Alerts & Review Queue Panel */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h3 className="font-semibold text-slate-100 text-sm">CFO Attention & Action Panel</h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20">
                {totalPendingReview} Queued
              </span>
            </div>

            <div className="mt-3.5 space-y-2.5">
              {/* Alert 1: OCR Review Queue */}
              {totalPendingReview > 0 ? (
                <div
                  onClick={() => onNavigate('sales')}
                  className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/30 hover:border-amber-500/50 cursor-pointer transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{totalPendingReview} Document(s) in Low OCR Review Queue</span>
                    </div>
                    <span className="text-[10px] text-amber-400 font-mono">Action req.</span>
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1">
                    Invoices uploaded below threshold (90%) routed to accountant queue. Require human maker-checker approval before GL posting.
                  </p>
                </div>
              ) : (
                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-emerald-400" />
                  <span>OCR extraction queue is fully cleared</span>
                </div>
              )}

              {/* Alert 2: Overdue Debtors > 6 Months */}
              {overdueDebtorsAmount > 0 && (
                <div
                  onClick={() => onNavigate('compliance')}
                  className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/30 hover:border-rose-500/50 cursor-pointer transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div className="text-xs font-semibold text-rose-300 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5" />
                      <span>Overdue Debtors &gt; 6 Months ({formatINR(overdueDebtorsAmount)})</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1">
                    Premier Machine Tools (₹2.95L) disputed & doubtful. Requires provisioning in Schedule III financial statement note.
                  </p>
                </div>
              )}

              {/* Alert 3: Dead Stock Exposure */}
              <div
                onClick={() => onNavigate('stock')}
                className="p-3 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 cursor-pointer transition-all"
              >
                <div className="flex items-start justify-between">
                  <div className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <PackageCheck className="w-3.5 h-3.5 text-teal-400" />
                    <span>Dead Stock Carrying Value ({formatLakhs(inventoryEval.deadStockValue)})</span>
                  </div>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Optical Discs (244 days idle). Provision write-down of {formatINR(inventoryEval.computedProvision)} recognized per AS 2 policy.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800">
            <button
              onClick={onOpenUpload}
              className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Upload New Invoice / Bill for Auto-Post</span>
            </button>
          </div>
        </div>
      </div>

      {/* Row 3: Revenue Trend & Ageing Summary Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Chart 1: Revenue Trend (Trailing 12-Month) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">12-Month Revenue & Operating Margin (₹ Cr)</h3>
              <p className="text-[11px] text-slate-400">Trailing actuals vs current month projected run-rate</p>
            </div>
            <button
              onClick={() => onNavigate('analytics')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 cursor-pointer"
            >
              <span>Sales Analytics</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={revenueTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorEbitda" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="month" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(val: any) => [`₹${val} Cr`, '']}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Area type="monotone" dataKey="revenue" name="Gross Revenue" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorRev)" />
                <Area type="monotone" dataKey="ebitda" name="EBITDA" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorEbitda)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Debtors vs Creditors Ageing Summary (Schedule III) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">Working Capital Ageing Buckets (Schedule III)</h3>
              <p className="text-[11px] text-slate-400">Trade Receivables vs Trade Payables maturity profile</p>
            </div>
            <button
              onClick={() => onNavigate('compliance')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 cursor-pointer"
            >
              <span>Schedule III Ageing Notes</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ageingChartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="bucket" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v / 100000).toFixed(1)}L`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  formatter={(val: any) => [formatINR(val), '']}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="Debtors" name="Trade Receivables" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Creditors" name="Trade Payables" fill="#a855f7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
