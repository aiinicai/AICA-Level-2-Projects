import React, { useState, useMemo } from 'react';
import {
  AlertTriangle, Copy, Split, Calendar, DollarSign,
  Search, Download, ExternalLink, ChevronRight, ShieldAlert, ArrowUpRight
} from 'lucide-react';
import { ForensicTestsResponse, IngestionResult } from '../types';

interface ForensicScannerViewProps {
  forensicsData: ForensicTestsResponse | null;
  ingestionResult: IngestionResult | null;
  isLoading: boolean;
  onProceedToLedger: () => void;
}

export const ForensicScannerView: React.FC<ForensicScannerViewProps> = ({
  forensicsData,
  ingestionResult,
  isLoading,
  onProceedToLedger
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'composite' | 'rsf' | 'duplicates' | 'splits' | 'rounds' | 'temporal'>('composite');
  const [searchTerm, setSearchTerm] = useState('');

  // Top-level hook execution (guarantees identical hook count across all renders)
  const flaggedTransactions = useMemo(() => {
    return forensicsData?.flagged_transactions || [];
  }, [forensicsData]);

  const filteredTransactions = useMemo(() => {
    if (!searchTerm.trim()) return flaggedTransactions;
    const term = searchTerm.toLowerCase();
    return flaggedTransactions.filter(t =>
      String(t.vendor || '').toLowerCase().includes(term) ||
      String(t.invoice_no || '').toLowerCase().includes(term) ||
      String(t.amount || '').toLowerCase().includes(term) ||
      (t.anomaly_factors || []).some(f => f.toLowerCase().includes(term))
    );
  }, [flaggedTransactions, searchTerm]);

  // Conditional Rendering AFTER all hooks have executed
  if (!forensicsData || !forensicsData.success) {
    return (
      <div className="forensic-card p-12 text-center max-w-2xl mx-auto my-8">
        <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4 animate-pulse" />
        <h3 className="text-base font-bold text-white mb-1">
          {isLoading ? 'Scanning Multi-Dimensional Forensic Anomalies...' : 'Forensic Tests Pending'}
        </h3>
        <p className="text-xs text-slate-400">
          Run forensic tests to detect Relative Size Factor outliers, duplicate payments, and split transaction smurfing.
        </p>
      </div>
    );
  }

  const {
    rsf_analysis,
    duplicate_analysis,
    split_transaction_analysis,
    round_number_analysis,
    temporal_analysis,
    composite_risk_summary
  } = forensicsData;

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Enterprise Forensic Anomaly Suite
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            RSF Outliers &bull; Duplicate Invoices &bull; Statutory Threshold Smurfing &bull; Round Provisions &bull; Multi-Factor Risk Scoring
          </p>
        </div>

        <button
          onClick={onProceedToLedger}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-all flex items-center gap-2 self-start sm:self-auto"
        >
          <span>View Chained Audit Ledger</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Forensic KPI Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        <div className="forensic-card p-3.5 border-l-4 border-l-rose-500">
          <span className="text-[10px] text-slate-400 font-semibold block uppercase">RSF Vendor Outliers</span>
          <div className="text-lg font-bold text-rose-400 mt-0.5">
            {rsf_analysis?.outlier_vendor_count || 0}
          </div>
          <span className="text-[10px] text-slate-500">Vendors with RSF &gt; 5.0</span>
        </div>

        <div className="forensic-card p-3.5 border-l-4 border-l-amber-500">
          <span className="text-[10px] text-slate-400 font-semibold block uppercase">Exact Duplicate Sets</span>
          <div className="text-lg font-bold text-amber-400 mt-0.5">
            {duplicate_analysis?.exact_duplicate_clusters || 0}
          </div>
          <span className="text-[10px] text-slate-500">{duplicate_analysis?.exact_duplicated_rows || 0} Total rows</span>
        </div>

        <div className="forensic-card p-3.5 border-l-4 border-l-amber-400">
          <span className="text-[10px] text-slate-400 font-semibold block uppercase">Split Smurfing</span>
          <div className="text-lg font-bold text-amber-300 mt-0.5">
            {split_transaction_analysis?.total_split_anomalies || 0}
          </div>
          <span className="text-[10px] text-slate-500">Below PAN/Cash Limits</span>
        </div>

        <div className="forensic-card p-3.5 border-l-4 border-l-cyan-500">
          <span className="text-[10px] text-slate-400 font-semibold block uppercase">Round Amount Density</span>
          <div className="text-lg font-bold text-cyan-400 mt-0.5">
            {round_number_analysis?.round_percentage || 0}%
          </div>
          <span className="text-[10px] text-slate-500">{round_number_analysis?.total_round_transactions || 0} Round items</span>
        </div>

        <div className="forensic-card p-3.5 border-l-4 border-l-purple-500">
          <span className="text-[10px] text-slate-400 font-semibold block uppercase">Calendar Outliers</span>
          <div className="text-lg font-bold text-purple-400 mt-0.5">
            {(temporal_analysis?.weekend_postings_count || 0) + (temporal_analysis?.holiday_postings_count || 0)}
          </div>
          <span className="text-[10px] text-slate-500">Weekend/Holiday Postings</span>
        </div>
      </div>

      {/* Sub-Tab Selector */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        {[
          { id: 'composite', label: 'Composite Risk Matrix', count: flaggedTransactions.length },
          { id: 'rsf', label: 'RSF Vendor Outliers', count: rsf_analysis?.outlier_vendor_count || 0 },
          { id: 'duplicates', label: 'Duplicate Payments', count: duplicate_analysis?.exact_duplicate_clusters || 0 },
          { id: 'splits', label: 'Split Transactions', count: split_transaction_analysis?.total_split_anomalies || 0 },
          { id: 'rounds', label: 'Round Numbers', count: round_number_analysis?.total_round_transactions || 0 },
          { id: 'temporal', label: 'Calendar Outliers', count: (temporal_analysis?.weekend_postings_count || 0) + (temporal_analysis?.holiday_postings_count || 0) }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id as any)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
              activeSubTab === tab.id
                ? 'bg-brand-600 text-white shadow-lg shadow-brand-500/20'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            <span>{tab.label}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-950/80 border border-slate-800 font-mono">
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* SubTab 1: Composite Risk Matrix */}
      {activeSubTab === 'composite' && (
        <div className="forensic-card p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Multi-Factor Risk Scored Transactions</span>
                <span className="text-xs text-slate-400">({filteredTransactions.length} flagged records)</span>
              </h3>
              <p className="text-xs text-slate-400">
                Composite anomaly score synthesizes RSF outliers, duplicates, statutory smurfing, and round provisions.
              </p>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search vendor, invoice, red-flags..."
                className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 w-48 sm:w-64"
              />
            </div>
          </div>

          <div className="overflow-x-auto border border-slate-800 rounded-lg max-h-96">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[10px] sticky top-0">
                <tr>
                  <th className="px-3 py-2">Row #</th>
                  <th className="px-3 py-2">Risk Score</th>
                  <th className="px-3 py-2">Severity</th>
                  <th className="px-3 py-2">Amount (₹)</th>
                  <th className="px-3 py-2">Vendor / Party</th>
                  <th className="px-3 py-2">Invoice / Ref</th>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Triggered Red Flags</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredTransactions.slice(0, 100).map((tx, idx) => {
                  let badgeBg = 'bg-slate-800 text-slate-300';
                  if (tx.risk_tier === 'CRITICAL') badgeBg = 'bg-rose-500/20 text-rose-400 border border-rose-500/30';
                  else if (tx.risk_tier === 'HIGH') badgeBg = 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
                  else if (tx.risk_tier === 'MEDIUM') badgeBg = 'bg-blue-500/20 text-blue-400 border border-blue-500/30';

                  return (
                    <tr key={idx} className="hover:bg-slate-800/30">
                      <td className="px-3 py-2 text-slate-500">{tx.row_index + 1}</td>
                      <td className="px-3 py-2 font-bold text-white">
                        <span className="text-amber-400 font-mono">{tx.risk_score}</span>/100
                      </td>
                      <td className="px-3 py-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${badgeBg}`}>
                          {tx.risk_tier}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-bold text-white">
                        ₹{Number(tx.amount || 0).toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-slate-200">{String(tx.vendor || '-')}</td>
                      <td className="px-3 py-2 text-slate-400">{String(tx.invoice_no || '-')}</td>
                      <td className="px-3 py-2 text-slate-400">{String(tx.date || '-')}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1 font-sans">
                          {(tx.anomaly_factors || []).map((f, i) => (
                            <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                              {f}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SubTab 2: RSF Vendor Outliers */}
      {activeSubTab === 'rsf' && (
        <div className="forensic-card p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">
              Relative Size Factor (RSF) Outliers (Largest Invoice / 2nd Largest Invoice)
            </h3>
            <p className="text-xs text-slate-400">
              Flags vendors where a single invoice is disproportionately large compared to all other historical invoices.
            </p>
          </div>

          <div className="overflow-x-auto border border-slate-800 rounded-lg">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-3 py-2">Vendor / Party</th>
                  <th className="px-3 py-2">RSF Multiplier</th>
                  <th className="px-3 py-2">Risk Level</th>
                  <th className="px-3 py-2 text-right">Largest Invoice (₹)</th>
                  <th className="px-3 py-2 text-right">2nd Largest (₹)</th>
                  <th className="px-3 py-2 text-right">Invoice Count</th>
                  <th className="px-3 py-2 text-right">Total Spend (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {(rsf_analysis?.high_risk_vendors || []).map((v, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="px-3 py-2 font-bold text-white">{v.vendor_name}</td>
                    <td className="px-3 py-2 font-bold text-rose-400">{v.rsf_value}x</td>
                    <td className="px-3 py-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                        v.risk_level === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {v.risk_level}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-bold text-white">₹{v.largest_amount?.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-slate-400">₹{v.second_largest_amount?.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-slate-300">{v.transaction_count}</td>
                    <td className="px-3 py-2 text-right font-bold text-emerald-400">₹{v.total_spend?.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SubTab 3: Duplicate Payments */}
      {activeSubTab === 'duplicates' && (
        <div className="forensic-card p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">
              Duplicate Invoices &amp; Payments (Exact &amp; Fuzzy 30-Day Matches)
            </h3>
            <p className="text-xs text-slate-400">
              Detects identical vouchers or payments issued within short calendar windows.
            </p>
          </div>

          <div className="overflow-x-auto border border-slate-800 rounded-lg">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-3 py-2">Match Type</th>
                  <th className="px-3 py-2">Vendor</th>
                  <th className="px-3 py-2">Invoice / Ref</th>
                  <th className="px-3 py-2 text-right">Amount (₹)</th>
                  <th className="px-3 py-2">Duplicate Rows / Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {(duplicate_analysis?.exact_duplicates || []).map((dup, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="px-3 py-2">
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold">
                        EXACT MATCH
                      </span>
                    </td>
                    <td className="px-3 py-2 font-bold text-white">{String(dup.vendor || '-')}</td>
                    <td className="px-3 py-2 text-slate-300">{String(dup.invoice_no || '-')}</td>
                    <td className="px-3 py-2 text-right font-bold text-rose-400">₹{Number(dup.amount || 0).toLocaleString()}</td>
                    <td className="px-3 py-2 text-slate-400 font-sans text-xs">
                      Duplicated in {dup.cluster_size} records (Rows: {dup.row_indices?.map(r => r + 1).join(', ')})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SubTab 4: Split Transactions / Smurfing */}
      {activeSubTab === 'splits' && (
        <div className="forensic-card p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">
              Split Transactions / Statutory Threshold Evasion (Smurfing)
            </h3>
            <p className="text-xs text-slate-400">
              Detects transactions grouped within 10% below statutory reporting limits (e.g. ₹45,000–₹49,999 for ₹50,000 PAN threshold).
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {(split_transaction_analysis?.threshold_evaluations || []).map((th, i) => (
              <div key={i} className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-xs text-slate-400 font-semibold">{th.threshold_label}</span>
                <div className="text-lg font-bold text-amber-400">
                  {th.flagged_count} Transactions
                </div>
                <span className="text-[11px] font-mono text-slate-500 block">
                  Band: ₹{th.lower_band_evaluated?.toLocaleString()} - ₹{(th.threshold_amount - 1)?.toLocaleString()}
                </span>
                <span className="text-[11px] font-mono text-emerald-400 block pt-1">
                  Total Volume: ₹{th.flagged_total_amount?.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SubTab 5: Round Numbers */}
      {activeSubTab === 'rounds' && (
        <div className="forensic-card p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">
              Round Number Distribution &amp; Artificial Provisions
            </h3>
            <p className="text-xs text-slate-400">
              Excessive round numbers indicate estimation heuristic, fictitious billing, or unvouched round-figure entries.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block font-sans">Multiples of ₹1,00,000:</span>
              <div className="text-base font-bold text-cyan-400 mt-1">{round_number_analysis?.breakdown?.multiples_of_1Lakh || 0}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block font-sans">Multiples of ₹50,000:</span>
              <div className="text-base font-bold text-cyan-400 mt-1">{round_number_analysis?.breakdown?.multiples_of_50k || 0}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block font-sans">Multiples of ₹10,000:</span>
              <div className="text-base font-bold text-cyan-400 mt-1">{round_number_analysis?.breakdown?.multiples_of_10k || 0}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block font-sans">Multiples of ₹1,000:</span>
              <div className="text-base font-bold text-cyan-400 mt-1">{round_number_analysis?.breakdown?.multiples_of_1k || 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* SubTab 6: Temporal / Calendar Postings */}
      {activeSubTab === 'temporal' && (
        <div className="forensic-card p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">
              Weekend &amp; Indian Statutory Holiday Postings
            </h3>
            <p className="text-xs text-slate-400">
              Examines entries booked on Saturdays, Sundays, or Indian national holidays (Republic Day Jan 26, Independence Day Aug 15, Gandhi Jayanti Oct 2).
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
              <span className="text-slate-400 font-semibold">Weekend Postings (Saturday / Sunday):</span>
              <div className="text-lg font-bold text-purple-400">{temporal_analysis?.weekend_postings_count || 0} Records</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
              <span className="text-slate-400 font-semibold">Statutory National Holiday Postings:</span>
              <div className="text-lg font-bold text-purple-400">{temporal_analysis?.holiday_postings_count || 0} Records</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
