import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Clock,
  CheckCircle2,
  AlertCircle,
  CreditCard,
  Building2,
  Search,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  PlusCircle,
  Calendar,
  Layers
} from 'lucide-react';
import { StorageService } from '../../services/storage';
import { PaymentTrendAnalyticsData, ClientPaymentMetric, PaymentRecord } from '../../types';
import { RecordPaymentModal } from './RecordPaymentModal';

export const PaymentTrendsView: React.FC = () => {
  const storage = StorageService.getInstance();
  const currentCompany = storage.getCompanyProfile();
  const currentUser = storage.getCurrentUser();

  const [analytics, setAnalytics] = useState<PaymentTrendAnalyticsData>(storage.getPaymentTrendAnalytics());
  const [payments, setPayments] = useState<PaymentRecord[]>(storage.getPayments());
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'critical' | 'warning' | 'healthy'>('all');
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [targetClientId, setTargetClientId] = useState<string | undefined>(undefined);

  const reloadData = () => {
    setAnalytics(storage.getPaymentTrendAnalytics());
    setPayments(storage.getPayments());
  };

  useEffect(() => {
    reloadData();
    const unsubscribe = storage.subscribe(reloadData);
    return unsubscribe;
  }, []);

  const filteredClients = analytics.clientMetrics.filter((c) => {
    if (statusFilter !== 'all' && c.paymentStatus !== statusFilter) return false;
    if (searchQuery) {
      return c.clientName.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  return (
    <div id="payment-trends-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-emerald-600 font-semibold text-xs mb-1">
            <TrendingUp className="w-4 h-4" />
            <span>Corporate Receivables & Liquidity Governance</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Client Payment Trends & Credit Risk Analytics
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Monitor client payment speed (days-to-pay), overdue debt aging, and approved credit limit utilization for <span className="font-semibold text-slate-800">{currentCompany.name}</span>.
          </p>
        </div>

        <button
          onClick={() => {
            setTargetClientId(undefined);
            setIsRecordModalOpen(true);
          }}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-sm flex items-center space-x-2 transition shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Record Payment Settlement</span>
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Average Days to Pay */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Avg Days-to-Pay</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-black text-slate-900 font-mono">
              {analytics.averageDaysToPay} Days
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Industry Benchmark: <span className="font-semibold text-slate-700">21 Days</span> (Tanzania Trade)
          </p>
        </div>

        {/* Total Outstanding */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Receivables</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-black text-slate-900 font-mono">
              TZS {(analytics.totalOutstandingAmount / 1000000).toFixed(1)}M
            </span>
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            Full: TZS {analytics.totalOutstandingAmount.toLocaleString()}
          </p>
        </div>

        {/* Overdue Receivables */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Overdue Debt</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-black text-rose-600 font-mono">
              TZS {(analytics.totalOverdueAmount / 1000000).toFixed(1)}M
            </span>
            <span className="text-xs font-bold text-rose-600 font-mono">
              ({analytics.overdueInvoicesCount} inv)
            </span>
          </div>
          <p className="text-[11px] text-rose-500 font-semibold">
            {analytics.overdueInvoicesCount > 0 ? 'Requires immediate follow-up' : 'Zero overdue invoices'}
          </p>
        </div>

        {/* Total Settled */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Settled Collections</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-black text-emerald-700 font-mono">
              TZS {(analytics.totalPaidAmount / 1000000).toFixed(1)}M
            </span>
          </div>
          <p className="text-[11px] text-emerald-600">
            {payments.length} Verified Payments Recorded
          </p>
        </div>
      </div>

      {/* Credit Utilization Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xs font-bold text-slate-900">Total Credit Exposure vs. Approved Portfolio Limit</h4>
            <p className="text-[11px] text-slate-500">
              Outstanding receivables TZS {analytics.totalOutstandingAmount.toLocaleString()} against approved portfolio credit limit of TZS {analytics.totalCreditLimit.toLocaleString()}.
            </p>
          </div>
          <span className="text-sm font-black font-mono text-slate-800">
            {analytics.averageCreditUtilization}% Utilized
          </span>
        </div>

        <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              analytics.averageCreditUtilization > 85
                ? 'bg-rose-500'
                : analytics.averageCreditUtilization > 60
                ? 'bg-amber-500'
                : 'bg-emerald-500'
            }`}
            style={{ width: `${Math.min(100, analytics.averageCreditUtilization)}%` }}
          />
        </div>
      </div>

      {/* Client Breakdown Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Table Filter Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-72">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by contractor name..."
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white font-medium text-slate-700 focus:outline-hidden"
            >
              <option value="all">All Payment Profiles</option>
              <option value="critical">Critical Overdue</option>
              <option value="warning">Warning / Near Limit</option>
              <option value="healthy">Healthy Standing</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3 px-4">Client Name</th>
                <th className="py-3 px-4">Payment Terms</th>
                <th className="py-3 px-4 text-right">Approved Limit</th>
                <th className="py-3 px-4 text-right">Outstanding</th>
                <th className="py-3 px-4 text-center">Credit Util.</th>
                <th className="py-3 px-4 text-center">Avg Days-to-Pay</th>
                <th className="py-3 px-4 text-center">Overdue</th>
                <th className="py-3 px-4 text-center">Health Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredClients.map((client) => (
                <tr key={client.clientId} className="hover:bg-slate-50/80 transition">
                  <td className="py-3.5 px-4 font-bold text-slate-900">
                    <div>{client.clientName}</div>
                    {client.lastPaymentDate && (
                      <div className="text-[10px] text-slate-400 font-normal">
                        Last Payment: {client.lastPaymentDate}
                      </div>
                    )}
                  </td>

                  <td className="py-3.5 px-4">
                    <span className="capitalize font-semibold text-slate-700">
                      {client.paymentTermsType}
                    </span>
                    {client.paymentTermsType === 'credit' && (
                      <span className="text-slate-400 text-[10px] block">
                        ({client.creditDays} Days Net)
                      </span>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-right font-mono text-slate-600">
                    {client.approvedCreditLimit > 0
                      ? `TZS ${client.approvedCreditLimit.toLocaleString()}`
                      : '—'}
                  </td>

                  <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900">
                    TZS {client.currentOutstanding.toLocaleString()}
                  </td>

                  <td className="py-3.5 px-4 text-center">
                    {client.approvedCreditLimit > 0 ? (
                      <div className="flex items-center justify-center space-x-1.5">
                        <span className="font-mono font-bold text-[11px]">
                          {client.creditUtilizationPercent}%
                        </span>
                        <div className="w-12 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              client.creditUtilizationPercent > 90
                                ? 'bg-rose-500'
                                : client.creditUtilizationPercent > 60
                                ? 'bg-amber-500'
                                : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, client.creditUtilizationPercent)}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-800">
                    {client.averageDaysToPay} d
                  </td>

                  <td className="py-3.5 px-4 text-center">
                    {client.overdueInvoicesCount > 0 ? (
                      <span className="inline-flex items-center space-x-1 text-rose-600 font-bold font-mono text-[11px]">
                        <AlertTriangle className="w-3 h-3" />
                        <span>TZS {(client.overdueAmount / 1000000).toFixed(1)}M</span>
                      </span>
                    ) : (
                      <span className="text-emerald-600 font-semibold text-[11px]">0 overdue</span>
                    )}
                  </td>

                  <td className="py-3.5 px-4 text-center">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        client.paymentStatus === 'critical'
                          ? 'bg-rose-100 text-rose-800'
                          : client.paymentStatus === 'warning'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {client.paymentStatus}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => {
                        setTargetClientId(client.clientId);
                        setIsRecordModalOpen(true);
                      }}
                      className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-lg text-[11px] font-bold transition"
                    >
                      Settle
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Settlement Modal */}
      <RecordPaymentModal
        isOpen={isRecordModalOpen}
        onClose={() => setIsRecordModalOpen(false)}
        initialClientId={targetClientId}
        onPaymentRecorded={() => reloadData()}
      />
    </div>
  );
};
