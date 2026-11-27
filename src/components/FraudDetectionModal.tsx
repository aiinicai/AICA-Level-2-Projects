import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  X,
  CheckCircle2,
  RefreshCw,
  Copy,
  TrendingUp,
  Cpu,
  ArrowRight,
  ExternalLink,
  Info
} from 'lucide-react';
import { Account, Transaction } from '../types/finance';

interface FraudDetectionModalProps {
  transactions: Transaction[];
  accounts: Account[];
  onClose: () => void;
  onVerifyTransaction?: (txId: string) => void;
  onReviewTransaction?: (tx: Transaction) => void;
}

export const FraudDetectionModal: React.FC<FraudDetectionModalProps> = ({
  transactions,
  accounts,
  onClose,
  onVerifyTransaction,
  onReviewTransaction
}) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<'all' | 'high' | 'medium'>('all');

  const runScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/ai/fraud-detection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transactions, accounts })
      });
      const json = await res.json();
      if (json.success) {
        setData(json);
      } else {
        setError(json.error || 'Failed to execute Scikit-learn Isolation Forest');
      }
    } catch (err: any) {
      setError(err.message || 'Error running Python ML fraud detection');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runScan();
  }, [transactions]);

  const alerts = data?.alerts || [];
  const filteredAlerts = alerts.filter((a: any) => {
    if (filterSeverity === 'high') return a.severity === 'high';
    if (filterSeverity === 'medium') return a.severity === 'medium';
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/85 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 shadow-2xl flex flex-col max-h-[94vh] sm:max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-white">AI Fraud &amp; Anomaly Detection</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-teal-300 border border-slate-700 flex items-center gap-1 font-mono">
                  <Cpu className="w-3 h-3 text-teal-400" />
                  Python Scikit-Learn
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Isolation Forest outlier detection, duplicate charges &amp; suspicious foreign FX alerts
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Model Metrics & Overview Banner */}
        <div className="py-4 space-y-4 overflow-y-auto flex-1">
          {loading ? (
            <div className="p-12 text-center space-y-3">
              <RefreshCw className="w-8 h-8 text-teal-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-300 font-semibold">Running Python Isolation Forest ML scan on transactions...</p>
              <p className="text-[11px] text-slate-500">Checking multivariate outlier scores, duplicate charges &amp; currency anomalies</p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs">
              <p className="font-bold">Scan Error</p>
              <p className="mt-1">{error}</p>
              <button
                onClick={runScan}
                className="mt-3 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-semibold text-xs cursor-pointer"
              >
                Retry Scan
              </button>
            </div>
          ) : (
            <>
              {/* Status Summary Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block mb-0.5">Overall Status</span>
                  <div className="flex items-center gap-1.5">
                    {data?.risk_summary?.high_risk > 0 ? (
                      <span className="text-xs font-black text-rose-400 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" /> High Risk
                      </span>
                    ) : data?.risk_summary?.medium_risk > 0 ? (
                      <span className="text-xs font-black text-amber-400 flex items-center gap-1">
                        <Info className="w-3.5 h-3.5" /> Attention Needed
                      </span>
                    ) : (
                      <span className="text-xs font-black text-emerald-400 flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" /> Clean Ledger
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block mb-0.5">High Alerts</span>
                  <span className="text-base font-black text-rose-400 tabular-nums">
                    {data?.risk_summary?.high_risk || 0}
                  </span>
                </div>

                <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block mb-0.5">Anomalies</span>
                  <span className="text-base font-black text-amber-400 tabular-nums">
                    {data?.anomalies_detected || 0}
                  </span>
                </div>

                <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block mb-0.5">Transactions Scanned</span>
                  <span className="text-base font-black text-white tabular-nums">
                    {data?.total_analyzed || 0}
                  </span>
                </div>
              </div>

              {/* Isolation Forest Tech Specs Pill */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1.5 text-slate-300">
                  <Cpu className="w-3.5 h-3.5 text-teal-400" />
                  Algorithm: Scikit-learn Isolation Forest (iTrees n=50, random partitioning)
                </span>
                <button
                  onClick={runScan}
                  className="text-teal-400 hover:text-teal-300 font-semibold flex items-center gap-1 cursor-pointer"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Rescan</span>
                </button>
              </div>

              {/* Severity Filter Tabs */}
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs font-bold text-white">Detected Fraud &amp; Anomaly Alerts ({filteredAlerts.length})</span>
                <div className="flex items-center gap-1 text-[11px]">
                  <button
                    onClick={() => setFilterSeverity('all')}
                    className={`px-2.5 py-1 rounded-lg font-semibold transition cursor-pointer ${
                      filterSeverity === 'all' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    All ({alerts.length})
                  </button>
                  <button
                    onClick={() => setFilterSeverity('high')}
                    className={`px-2.5 py-1 rounded-lg font-semibold transition cursor-pointer ${
                      filterSeverity === 'high' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    High Risk
                  </button>
                  <button
                    onClick={() => setFilterSeverity('medium')}
                    className={`px-2.5 py-1 rounded-lg font-semibold transition cursor-pointer ${
                      filterSeverity === 'medium' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Medium
                  </button>
                </div>
              </div>

              {/* Alerts List */}
              {filteredAlerts.length > 0 ? (
                <div className="space-y-3">
                  {filteredAlerts.map((item: any) => {
                    const isHigh = item.severity === 'high';
                    return (
                      <div
                        key={item.transactionId}
                        className={`p-4 rounded-2xl border transition ${
                          isHigh
                            ? 'bg-rose-950/25 border-rose-500/40 shadow-sm'
                            : 'bg-amber-950/20 border-amber-500/30'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-black px-2 py-0.5 rounded-full uppercase ${
                                  isHigh
                                    ? 'bg-rose-500 text-white'
                                    : 'bg-amber-500 text-slate-950'
                                }`}
                              >
                                {item.severity} Risk
                              </span>
                              <span className="text-xs text-slate-400 font-mono">
                                Score: {intToScore(item.isolationScore)}%
                              </span>
                              <span className="text-xs text-slate-400">• {item.date}</span>
                            </div>
                            <h4 className="text-sm font-bold text-white mt-1 truncate">
                              {item.merchant}
                            </h4>
                          </div>

                          <div className="text-right shrink-0">
                            <p className="text-base font-black text-white tabular-nums tracking-tight">
                              AED {item.amount.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                            </p>
                            <p className="text-[11px] text-slate-400">{item.category}</p>
                          </div>
                        </div>

                        {/* Risk Factors Bullet Points */}
                        <div className="space-y-1.5 p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
                          {item.riskFactors.map((rf: any, i: number) => (
                            <div key={i} className="flex items-start gap-1.5 text-slate-300">
                              <AlertTriangle className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${isHigh ? 'text-rose-400' : 'text-amber-400'}`} />
                              <div>
                                <strong className="text-white">{rf.factor}: </strong>
                                <span>{rf.detail}</span>
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Recommendation & Action Buttons */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-3 pt-2 border-t border-slate-800/80 text-[11px]">
                          <span className="text-slate-400">
                            💡 <em>{item.suggestedAction}</em>
                          </span>

                          <div className="flex items-center gap-2 shrink-0">
                            {onVerifyTransaction && (
                              <button
                                type="button"
                                onClick={() => onVerifyTransaction(item.transactionId)}
                                className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 font-semibold transition cursor-pointer flex items-center gap-1"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>Mark Verified</span>
                              </button>
                            )}
                            {onReviewTransaction && (
                              <button
                                type="button"
                                onClick={() => {
                                  const tx = transactions.find(t => t.id === item.transactionId);
                                  if (tx) onReviewTransaction(tx);
                                }}
                                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition cursor-pointer"
                              >
                                Review &amp; Edit
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-8 text-center bg-slate-950 rounded-2xl border border-slate-800 space-y-2">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <h4 className="text-sm font-bold text-white">No Suspicious Patterns Detected</h4>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    Scikit-learn Isolation Forest confirmed all transactions match standard spending bounds with zero duplicate charges or foreign FX risks.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-800 flex items-center justify-between gap-3 shrink-0">
          <button
            onClick={onClose}
            className="flex-1 sm:flex-none px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl border border-slate-700 transition cursor-pointer text-center"
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            className="flex-1 sm:flex-none px-5 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl transition cursor-pointer shadow text-center"
          >
            Close Security Center
          </button>
        </div>
      </div>
    </div>
  );
};

function intToScore(val: number) {
  if (!val) return 50;
  return Math.min(99, Math.round(val * 100));
}
