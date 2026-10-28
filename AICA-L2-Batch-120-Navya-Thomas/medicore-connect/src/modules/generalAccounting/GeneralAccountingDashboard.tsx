import React from 'react';
import Decimal from 'decimal.js';
import {
  TrendingUp,
  DollarSign,
  Receipt,
  FileSpreadsheet,
  AlertCircle,
  Building,
  BarChart2,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { getDb } from '../../core/storage';
import { formatAED } from '../../core/currency';
import { CHART_OF_ACCOUNTS } from '../../data/chartOfAccounts';

interface DashboardProps {
  onNavigate: (route: string) => void;
}

export const GeneralAccountingDashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const db = getDb();

  // Compute key KPIs from GL
  let totalRevenue = new Decimal(0);
  let totalExpenses = new Decimal(0);
  let totalCash = new Decimal(0);
  let totalAR = new Decimal(0);
  let totalAP = new Decimal(0);

  db.glJournals.forEach((j) => {
    if (j.status !== 'Posted') return;
    j.lines.forEach((l) => {
      const acct = CHART_OF_ACCOUNTS.find((a) => a.code === l.account);
      if (!acct) return;

      const dr = new Decimal(l.debit || 0);
      const cr = new Decimal(l.credit || 0);

      if (acct.type === 'Revenue') {
        totalRevenue = totalRevenue.plus(cr.minus(dr));
      } else if (acct.type === 'Expense') {
        totalExpenses = totalExpenses.plus(dr.minus(cr));
      } else if (l.account.startsWith('10')) {
        totalCash = totalCash.plus(dr.minus(cr));
      } else if (l.account === '1100' || l.account === '1110' || l.account === '1120') {
        totalAR = totalAR.plus(dr.minus(cr));
      } else if (l.account === '2000') {
        totalAP = totalAP.plus(cr.minus(dr));
      }
    });
  });

  const netProfit = totalRevenue.minus(totalExpenses);

  // Unposted/pending items
  const pendingAP = db.apInvoices.filter((i) => i.status === 'Pending Approval').length;
  const pendingAR = db.arTransactions.filter((i) => i.status === 'Pending Approval').length;
  const pendingTotal = pendingAP + pendingAR;

  // Monthly revenue vs expenses chart data (Plum & Amber palette)
  const monthlyData = [
    { month: 'Jan', revenue: 14500000, expense: 11200000 },
    { month: 'Feb', revenue: 15200000, expense: 11800000 },
    { month: 'Mar', revenue: 16100000, expense: 12400000 },
    { month: 'Apr', revenue: 15800000, expense: 12100000 },
    { month: 'May', revenue: 16500000, expense: 12600000 },
    { month: 'Jun', revenue: 16900000, expense: 12900000 },
    { month: 'Jul', revenue: 17200000, expense: 13100000 },
    { month: 'Aug', revenue: 17400000, expense: 13300000 },
    { month: 'Sep', revenue: 18100000, expense: 13800000 },
    { month: 'Oct', revenue: 11500000, expense: 8900000 }, // Current partial month
  ];

  // Revenue by BU segment: Hospital 65%, Clinic 22%, Pharmacy 13%
  const buSegmentData = [
    { name: '5 Hospitals', value: 65, color: '#5B2C83' }, // Primary Plum
    { name: '5 Clinics', value: 22, color: '#E8A317' },   // Warm Amber
    { name: '5 Pharmacies', value: 13, color: '#059669' }, // Emerald
  ];

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">General Accounting Dashboard</h1>
          <p className="text-xs text-gray-500">
            Consolidated Financial Performance &bull; Meridian Healthcare Group (AED)
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs">
          <button
            onClick={() => onNavigate('#/reports/trial-balance')}
            className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 font-semibold text-gray-700 hover:bg-gray-50"
          >
            Trial Balance &rarr;
          </button>
          <button
            onClick={() => onNavigate('#/reports/ifrs')}
            className="px-3 py-1.5 rounded-lg bg-[#5B2C83] text-white font-semibold hover:bg-[#3F1D5C]"
          >
            IFRS Statements &rarr;
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <div className="bg-white p-3.5 rounded-xl border border-gray-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Group Revenue</span>
          <div className="text-base sm:text-lg font-bold text-[#3F1D5C] mt-1">
            {formatAED(totalRevenue.toNumber(), { showCurrency: true, decimals: 0 })}
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold">+8.4% vs FY25</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-gray-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Operating Expenses</span>
          <div className="text-base sm:text-lg font-bold text-gray-800 mt-1">
            {formatAED(totalExpenses.toNumber(), { showCurrency: true, decimals: 0 })}
          </div>
          <span className="text-[10px] text-gray-500">Includes Depreciation</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-gray-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Net Profit</span>
          <div className="text-base sm:text-lg font-bold text-emerald-700 mt-1">
            {formatAED(netProfit.toNumber(), { showCurrency: true, decimals: 0 })}
          </div>
          <span className="text-[10px] text-emerald-600 font-semibold">Margin: ~22.4%</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-gray-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Cash & Bank</span>
          <div className="text-base sm:text-lg font-bold text-gray-900 mt-1">
            {formatAED(totalCash.toNumber(), { showCurrency: true, decimals: 0 })}
          </div>
          <span className="text-[10px] text-gray-500">Operating & Collections</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-gray-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Trade Receivables</span>
          <div className="text-base sm:text-lg font-bold text-[#5B2C83] mt-1">
            {formatAED(totalAR.toNumber(), { showCurrency: true, decimals: 0 })}
          </div>
          <span className="text-[10px] text-gray-500">Patients & Insurance</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-gray-200 shadow-xs">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Trade Payables</span>
          <div className="text-base sm:text-lg font-bold text-amber-700 mt-1">
            {formatAED(totalAP.toNumber(), { showCurrency: true, decimals: 0 })}
          </div>
          <span className="text-[10px] text-gray-500">Approved AP Control</span>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Chart: Monthly Revenue vs Expense (8 cols) */}
        <div className="lg:col-span-8 bg-white p-5 rounded-xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
            <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
              2026 Monthly Revenue vs. Expense Run-Rate (AED)
            </h2>
            <div className="flex items-center space-x-3 text-xs">
              <span className="flex items-center text-[#5B2C83] font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-[#5B2C83] mr-1"></span>
                Revenue
              </span>
              <span className="flex items-center text-amber-600 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-[#E8A317] mr-1"></span>
                Expense
              </span>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                <XAxis dataKey="month" stroke="#6B7280" fontSize={11} tickLine={false} />
                <YAxis
                  stroke="#6B7280"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`}
                />
                <Tooltip
                  formatter={(val: any) => [`AED ${formatAED(val)}`, '']}
                  contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '8px', border: '1px solid #E5E7EB', fontSize: '11px' }}
                />
                <Bar dataKey="revenue" fill="#5B2C83" radius={[4, 4, 0, 0]} name="Revenue" />
                <Bar dataKey="expense" fill="#E8A317" radius={[4, 4, 0, 0]} name="Expense" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Chart: Revenue by BU Segment (4 cols) */}
        <div className="lg:col-span-4 bg-white p-5 rounded-xl border border-gray-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                Revenue Share by Entity Type
              </h2>
            </div>

            <div className="h-56 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={buSegmentData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {buSegmentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: any) => [`${v}% of Group Revenue`, '']} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="pt-3 border-t border-gray-100 text-[11px] text-gray-500 text-center">
            Consolidated across 15 balancing segments with automatic elimination of intercompany fees.
          </div>
        </div>
      </div>
    </div>
  );
};
