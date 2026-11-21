import React, { useState, useEffect } from 'react';
import { 
  Building2, CheckCircle2, AlertTriangle, XCircle, 
  Percent, FileText, ArrowUpRight, HelpCircle
} from 'lucide-react';
import { PolicyFitEvaluation } from '../types';
import { formatINR, NumberUnitMode } from '../utils/formatters';
import { ApiClient } from '../api/client';

interface LenderMatrixTabProps {
  proposalId: string;
  unitMode: NumberUnitMode;
}

export const LenderMatrixTab: React.FC<LenderMatrixTabProps> = ({
  proposalId,
  unitMode,
}) => {
  const [evaluations, setEvaluations] = useState<PolicyFitEvaluation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchLenderComparison = async () => {
    setIsLoading(true);
    try {
      const data = await ApiClient.request<PolicyFitEvaluation[]>(`/lenders/compare/${proposalId}`);
      setEvaluations(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLenderComparison();
  }, [proposalId]);

  return (
    <div className="space-y-4">
      {/* Header Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div>
          <h4 className="font-bold text-slate-900 text-sm">Lender Underwriting Policies & Fit Matrix</h4>
          <p className="text-xs text-slate-500">
            Automated compliance check against standard Indian commercial banks and NBFC credit rules.
          </p>
        </div>
        <div className="text-right text-xs">
          <span className="font-semibold text-slate-700">{evaluations.length} Active Policies Evaluated</span>
        </div>
      </div>

      {/* Grid of Bank Cards */}
      {isLoading ? (
        <div className="text-center py-12 text-slate-400 text-xs">Evaluating lender policies...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {evaluations.map((item, idx) => {
            const isEligible = item.fit_status === 'ELIGIBLE';
            const isBorderline = item.fit_status === 'BORDERLINE';
            return (
              <div
                key={idx}
                className={`bg-white rounded-xl border p-4 shadow-sm space-y-3 flex flex-col justify-between transition-all ${
                  isEligible
                    ? 'border-emerald-200 bg-emerald-50/20'
                    : isBorderline
                    ? 'border-amber-200 bg-amber-50/20'
                    : 'border-slate-200'
                }`}
              >
                <div>
                  {/* Top Bar: Bank Name & Fit Badge */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-4 h-4 text-brand-800" />
                        <span className="font-bold text-slate-900 text-sm">{item.lender_name}</span>
                      </div>
                      <p className="text-[11px] text-slate-500">{item.policy_name}</p>
                    </div>

                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                        isEligible
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                          : isBorderline
                          ? 'bg-amber-100 text-amber-800 border border-amber-300'
                          : 'bg-rose-100 text-rose-800 border border-rose-300'
                      }`}
                    >
                      {item.fit_status}
                    </span>
                  </div>

                  {/* Benchmark Limit & Rate */}
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs space-y-1.5 mb-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Max Policy Limit:</span>
                      <span className="font-bold text-slate-900">{formatINR(item.max_eligible_amount, unitMode)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Benchmark ROI:</span>
                      <span className="font-semibold text-brand-800">{item.benchmark_rate}% p.a.</span>
                    </div>
                  </div>

                  {/* Policy Deviations */}
                  {item.deviations && item.deviations.length > 0 && (
                    <div className="space-y-1 text-xs">
                      <span className="font-semibold text-rose-800 text-[11px] flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 text-rose-600" />
                        Deviations Flagged:
                      </span>
                      <ul className="list-disc pl-4 text-[11px] text-rose-700 space-y-0.5">
                        {item.deviations.map((dev, i) => (
                          <li key={i}>{dev}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Missing Inputs */}
                  {item.missing_inputs && item.missing_inputs.length > 0 && (
                    <div className="mt-2 space-y-1 text-xs">
                      <span className="font-semibold text-amber-800 text-[11px] flex items-center gap-1">
                        <HelpCircle className="w-3 h-3 text-amber-600" />
                        Missing Inputs:
                      </span>
                      <ul className="list-disc pl-4 text-[11px] text-amber-700 space-y-0.5">
                        {item.missing_inputs.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex items-center justify-between">
                  <span>Illustrative Policy Terms</span>
                  <span className="text-brand-700 font-medium">Preliminary Fit</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
