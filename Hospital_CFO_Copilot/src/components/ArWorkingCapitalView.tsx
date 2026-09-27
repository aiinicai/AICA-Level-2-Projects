import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  DollarSign,
  ExternalLink,
  Filter,
  Layers,
  Search,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  UserCheck,
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
import {
  Billing,
  Claim,
  Collection,
  Encounter,
} from '../types';
import { calculateArAgeing, ArAgeingSummary } from '../utils/arCalculations';
import { formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface ArWorkingCapitalViewProps {
  encounters: Encounter[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  onSelectEncounter: (encounterId: string) => void;
  asOfDate?: string;
  onNavigateToTab?: (tab: string) => void;
}

export const ArWorkingCapitalView: React.FC<ArWorkingCapitalViewProps> = ({
  encounters,
  billings,
  claims,
  collections,
  onSelectEncounter,
  asOfDate: propAsOfDate,
  onNavigateToTab,
}) => {
  const [selectedPayerFilter, setSelectedPayerFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [customAsOfDate, setCustomAsOfDate] = useState<string | undefined>(propAsOfDate);

  // Deterministic AR ageing computation
  const arSummary: ArAgeingSummary = useMemo(() => {
    return calculateArAgeing(encounters, billings, collections, claims, customAsOfDate);
  }, [encounters, billings, collections, claims, customAsOfDate]);

  // Unique payers for filtering
  const availablePayers = useMemo(() => {
    const pSet = new Set<string>();
    arSummary.items.forEach((item) => {
      if (item.payerType) pSet.add(item.payerType);
    });
    return Array.from(pSet);
  }, [arSummary.items]);

  // Filtered encounters
  const filteredEncounters = useMemo(() => {
    return arSummary.items.filter((enc) => {
      const matchPayer =
        selectedPayerFilter === 'ALL' || enc.payerType === selectedPayerFilter;
      const matchSearch =
        searchQuery === '' ||
        enc.encounterId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        enc.department.toLowerCase().includes(searchQuery.toLowerCase()) ||
        enc.payerType.toLowerCase().includes(searchQuery.toLowerCase());
      return matchPayer && matchSearch;
    });
  }, [arSummary.items, selectedPayerFilter, searchQuery]);

  if (encounters.length === 0 && billings.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Accounts Receivable &amp; Working Capital
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Deterministic ageing, uncollected billing balances, and credit exposure grounded on transaction records.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No receivables data available."
          description="AR ageing analysis and credit exposure calculations are derived from inpatient encounters, billing invoices, and collections. Upload your financial registers to analyze working capital."
          badge="AR Inactive"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'Inpatient Encounters (UHID, Admission/Discharge Date)',
            'Billing Register & Invoices (Invoice_ID, Billed_Amount, Bill_Date)',
            'Payment Receipts & Collections (Collection_Amount, Payment_Date)',
            'TPA Claims (Claim_Amount, Approved_Amount, Claim_Status)',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Accounts Receivable &amp; Working Capital
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                As of: {arSummary.asOfDateDisplay}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Deterministic ageing, uncollected billing balances, and credit exposure grounded on transaction records.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Calendar className="h-3.5 w-3.5 text-teal-700" />
              <span className="font-medium">Reporting Date:</span>
              <input
                type="date"
                value={arSummary.asOfDate}
                onChange={(e) => setCustomAsOfDate(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1 text-xs bg-white text-slate-800 font-semibold focus:outline-teal-600"
              />
            </div>
          </div>
        </div>

        {/* 4 Working Capital KPIs */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-slate-100 text-xs">
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
            <div className="text-[10px] uppercase font-bold text-slate-500">Total Outstanding AR</div>
            <div className="text-xl font-bold text-slate-900 mt-0.5">{formatINR(arSummary.totalAR)}</div>
            <div className="mt-0.5 text-[10px] text-slate-500">
              Total Billed: {formatINR(arSummary.totalBilled)}
            </div>
          </div>

          <div className="bg-emerald-50/50 p-3 rounded-lg border border-emerald-200">
            <div className="text-[10px] uppercase font-bold text-emerald-800">Current AR (0–30 Days)</div>
            <div className="text-xl font-bold text-emerald-900 mt-0.5">{formatINR(arSummary.currentAR)}</div>
            <div className="mt-0.5 text-[10px] text-emerald-700">
              {arSummary.totalAR > 0 ? ((arSummary.currentAR / arSummary.totalAR) * 100).toFixed(1) : 0}% of receivables
            </div>
          </div>

          <div className="bg-rose-50/50 p-3 rounded-lg border border-rose-200">
            <div className="text-[10px] uppercase font-bold text-rose-800">Overdue AR (&gt;30 Days)</div>
            <div className="text-xl font-bold text-rose-900 mt-0.5">{formatINR(arSummary.overdueAR)}</div>
            <div className="mt-0.5 text-[10px] text-rose-700">
              {arSummary.totalAR > 0 ? ((arSummary.overdueAR / arSummary.totalAR) * 100).toFixed(1) : 0}% requiring follow-up
            </div>
          </div>

          <div className="bg-teal-50/50 p-3 rounded-lg border border-teal-200">
            <div className="text-[10px] uppercase font-bold text-teal-800">Collection Realization Rate</div>
            <div className="text-xl font-bold text-teal-900 mt-0.5">{arSummary.collectionRate}%</div>
            <div className="mt-0.5 text-[10px] text-teal-700">
              Realised: {formatINR(arSummary.totalCollected)}
            </div>
          </div>
        </div>
      </div>

      {/* Visual Analytics: Ageing Distribution & Payer/Dept Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AR Ageing Buckets Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Receivables Ageing Distribution</h2>
              <p className="text-[11px] text-slate-500">Deterministic days elapsed between bill date and as-of date</p>
            </div>
            <div className="flex items-center gap-1 text-[11px] text-slate-400">
              <span>Data Lineage: Billing &amp; Collections</span>
            </div>
          </div>

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={arSummary.ageingBuckets} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`}
                />
                <Tooltip
                  formatter={(val: any) => [formatINR(Number(val) || 0), 'Outstanding AR']}
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', fontSize: '11px' }}
                />
                <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                  {arSummary.ageingBuckets.map((b) => (
                    <Cell key={b.bucket} fill={b.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Bucket Summary Row */}
          <div className="grid grid-cols-4 gap-2 pt-3 border-t border-slate-100 mt-2 text-center text-xs">
            {arSummary.ageingBuckets.map((b) => (
              <div key={b.bucket} className="p-2 rounded bg-slate-50 border border-slate-100">
                <div className="text-[10px] font-semibold text-slate-500">{b.label}</div>
                <div className="text-sm font-bold text-slate-900 mt-0.5">{formatINR(b.amount)}</div>
                <div className="text-[10px] text-slate-400">{b.count} accounts ({b.shareFormatted})</div>
              </div>
            ))}
          </div>
        </div>

        {/* Payer Category Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
          <div className="mb-3">
            <h2 className="text-sm font-bold text-slate-900">Outstanding AR by Payer</h2>
            <p className="text-[11px] text-slate-500">Concentration across payer categories</p>
          </div>

          <div className="space-y-3 mt-4">
            {arSummary.payerBreakdown.length > 0 ? (
              arSummary.payerBreakdown.map((p) => (
                <div key={p.payer} className="text-xs">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold text-slate-800">{p.payer}</span>
                    <span className="font-bold text-slate-900">{formatINR(p.ar)}</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-teal-700 h-1.5 rounded-full"
                      style={{ width: `${Math.min(100, p.percentage)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400 mt-0.5">
                    <span>Billed: {formatINR(p.billed)}</span>
                    <span>{p.percentage}% of AR</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-slate-400 text-xs">
                No payer data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* DETAILED ENCOUNTERS AR LEDGER TABLE */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Encounter Receivables Ledger &amp; Ageing Audit
            </h2>
            <p className="text-[11px] text-slate-500">
              Total {filteredEncounters.length} patient accounts &bull; Traceable to individual hospital invoices and receipts
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search Encounter / Dept..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1 text-xs border border-slate-300 rounded-md bg-white focus:outline-teal-600 text-slate-900 w-48"
              />
            </div>

            {/* Payer Filter */}
            <select
              value={selectedPayerFilter}
              onChange={(e) => setSelectedPayerFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-md px-2.5 py-1 bg-white font-medium text-slate-800 focus:outline-teal-600"
            >
              <option value="ALL">All Payers</option>
              {availablePayers.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="py-2.5 px-3">Encounter</th>
                <th className="py-2.5 px-3">Department</th>
                <th className="py-2.5 px-3">Payer</th>
                <th className="py-2.5 px-3 text-right">Billed Amount</th>
                <th className="py-2.5 px-3 text-right">Collected</th>
                <th className="py-2.5 px-3 text-right">Outstanding AR</th>
                <th className="py-2.5 px-3 text-center">Days Overdue</th>
                <th className="py-2.5 px-3">Ageing Bucket</th>
                <th className="py-2.5 px-3">Claim Adjudication</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredEncounters.length > 0 ? (
                filteredEncounters.map((enc, idx) => (
                  <tr key={`${enc.encounterId}-${idx}`} className="hover:bg-slate-50/80 transition">
                    <td className="py-2.5 px-3 font-mono font-semibold text-teal-800">
                      <button
                        onClick={() => onSelectEncounter(enc.encounterId)}
                        className="hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        {enc.encounterId}
                        <ExternalLink className="h-3 w-3 opacity-60" />
                      </button>
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-800">{enc.department}</td>
                    <td className="py-2.5 px-3 text-slate-600">{enc.payerType}</td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                      {formatINR(enc.billedAmount)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                      {formatINR(enc.collectedAmount)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-amber-900">
                      {formatINR(enc.outstandingAR)}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono font-semibold text-slate-700">
                      {enc.daysOutstanding}d
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          enc.bucket === '90+'
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : enc.bucket === '61-90'
                            ? 'bg-orange-50 text-orange-700 border border-orange-200'
                            : enc.bucket === '31-60'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-teal-50 text-teal-800 border border-teal-200'
                        }`}
                      >
                        {enc.bucket} Days
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 font-medium">
                      <span
                        className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] ${
                          enc.claimStatus === 'Approved'
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : enc.claimStatus === 'Partially Approved'
                            ? 'bg-amber-50 text-amber-800 border border-amber-200'
                            : enc.claimStatus === 'Rejected'
                            ? 'bg-red-50 text-red-800 border border-red-200'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {enc.claimStatus}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => onSelectEncounter(enc.encounterId)}
                        className="text-xs text-teal-700 font-semibold hover:text-teal-900 cursor-pointer"
                      >
                        Ledger &rarr;
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-400">
                    No encounter accounts match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
