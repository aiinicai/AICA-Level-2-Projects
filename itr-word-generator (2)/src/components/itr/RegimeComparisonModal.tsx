/**
 * RegimeComparisonModal Component
 * Compares New Tax Regime (u/s 115BAC) vs Old Tax Regime
 * with slab breakdowns, deduction impact, and tax savings recommendation.
 */

import React from 'react';
import { X, CheckCircle2, TrendingDown, ArrowRight, ShieldCheck } from 'lucide-react';
import { CompleteITRData } from '../../itr-types';
import { compareTaxRegimes } from '../../utils/taxCalculator';
import { formatIndianCurrency } from '../../utils/numberParsing';

interface RegimeComparisonModalProps {
  data: CompleteITRData;
  isOpen: boolean;
  onClose: () => void;
  onApplyRegime: (regime: 'New Regime' | 'Old Regime') => void;
}

export const RegimeComparisonModal: React.FC<RegimeComparisonModalProps> = ({
  data,
  isOpen,
  onClose,
  onApplyRegime,
}) => {
  if (!isOpen) return null;

  const comparison = compareTaxRegimes(data);
  const isNewRecommended = comparison.recommendedRegime === 'New Regime';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-5 py-4 bg-[#0F172A] text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="text-sm font-bold text-white">Tax Regime Comparison & Analysis</h3>
              <p className="text-[11px] text-slate-400">
                New Tax Regime (u/s 115BAC) vs. Old Tax Regime for AY {data.personalInfo.assessmentYear}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs text-slate-700">
          {/* Recommendation Banner */}
          <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold text-emerald-900 text-xs block uppercase tracking-wider">
                Recommended: {comparison.recommendedRegime}
              </span>
              <p className="text-emerald-800 text-[11px] leading-relaxed">
                {comparison.explanation}
              </p>
              {comparison.taxSavings > 0 && (
                <div className="text-xs font-bold text-emerald-700 pt-1">
                  Estimated Tax Savings: {formatIndianCurrency(comparison.taxSavings)}
                </div>
              )}
            </div>
          </div>

          {/* Comparison Table */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <th className="p-2.5 text-left">Particulars</th>
                  <th className="p-2.5 text-right w-36 bg-blue-50/70 text-blue-950">New Regime (115BAC)</th>
                  <th className="p-2.5 text-right w-36 bg-purple-50/70 text-purple-950">Old Regime</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr>
                  <td className="p-2 pl-3">Gross Total Income (GTI)</td>
                  <td className="p-2 text-right font-mono font-semibold bg-blue-50/20">{formatIndianCurrency(data.incomeHeads.grossTotalIncome, { showSymbol: false })}</td>
                  <td className="p-2 text-right font-mono font-semibold bg-purple-50/20">{formatIndianCurrency(data.incomeHeads.grossTotalIncome, { showSymbol: false })}</td>
                </tr>
                <tr>
                  <td className="p-2 pl-3">Allowable Deductions</td>
                  <td className="p-2 text-right font-mono text-slate-500 bg-blue-50/20">
                    {data.deductions.sec80CCD2 > 0 ? formatIndianCurrency(data.deductions.sec80CCD2, { showSymbol: false }) : 'Nil (Except 80CCD(2))'}
                  </td>
                  <td className="p-2 text-right font-mono text-emerald-600 bg-purple-50/20">
                    {formatIndianCurrency(data.deductions.totalDeductions, { showSymbol: false })}
                  </td>
                </tr>
                <tr className="font-semibold bg-slate-50">
                  <td className="p-2 pl-3">Total Taxable Income (288A)</td>
                  <td className="p-2 text-right font-mono bg-blue-50/40 text-blue-900">{formatIndianCurrency(comparison.newRegime.taxableIncome, { showSymbol: false })}</td>
                  <td className="p-2 text-right font-mono bg-purple-50/40 text-purple-900">{formatIndianCurrency(comparison.oldRegime.taxableIncome, { showSymbol: false })}</td>
                </tr>
                <tr>
                  <td className="p-2 pl-3">Base Slab Tax</td>
                  <td className="p-2 text-right font-mono bg-blue-50/20">{formatIndianCurrency(comparison.newRegime.slabTax, { showSymbol: false })}</td>
                  <td className="p-2 text-right font-mono bg-purple-50/20">{formatIndianCurrency(comparison.oldRegime.slabTax, { showSymbol: false })}</td>
                </tr>
                {(comparison.newRegime.specialRateTax > 0 || comparison.oldRegime.specialRateTax > 0) && (
                  <tr>
                    <td className="p-2 pl-3">Special Rate Tax (Capital Gains 111A/112A)</td>
                    <td className="p-2 text-right font-mono bg-blue-50/20">{formatIndianCurrency(comparison.newRegime.specialRateTax, { showSymbol: false })}</td>
                    <td className="p-2 text-right font-mono bg-purple-50/20">{formatIndianCurrency(comparison.oldRegime.specialRateTax, { showSymbol: false })}</td>
                  </tr>
                )}
                <tr>
                  <td className="p-2 pl-3">Less: Rebate u/s 87A</td>
                  <td className="p-2 text-right font-mono text-emerald-600 bg-blue-50/20">({formatIndianCurrency(comparison.newRegime.rebate87A, { showSymbol: false })})</td>
                  <td className="p-2 text-right font-mono text-emerald-600 bg-purple-50/20">({formatIndianCurrency(comparison.oldRegime.rebate87A, { showSymbol: false })})</td>
                </tr>
                {comparison.newRegime.marginalRelief > 0 && (
                  <tr>
                    <td className="p-2 pl-3">Less: 87A Marginal Relief</td>
                    <td className="p-2 text-right font-mono text-emerald-600 bg-blue-50/20">({formatIndianCurrency(comparison.newRegime.marginalRelief, { showSymbol: false })})</td>
                    <td className="p-2 text-right font-mono text-slate-400 bg-purple-50/20">-</td>
                  </tr>
                )}
                {(comparison.newRegime.surcharge > 0 || comparison.oldRegime.surcharge > 0) && (
                  <tr>
                    <td className="p-2 pl-3">Add: Surcharge</td>
                    <td className="p-2 text-right font-mono bg-blue-50/20">{formatIndianCurrency(comparison.newRegime.surcharge, { showSymbol: false })}</td>
                    <td className="p-2 text-right font-mono bg-purple-50/20">{formatIndianCurrency(comparison.oldRegime.surcharge, { showSymbol: false })}</td>
                  </tr>
                )}
                <tr>
                  <td className="p-2 pl-3">Add: Health & Edu Cess (4%)</td>
                  <td className="p-2 text-right font-mono bg-blue-50/20">{formatIndianCurrency(comparison.newRegime.cess, { showSymbol: false })}</td>
                  <td className="p-2 text-right font-mono bg-purple-50/20">{formatIndianCurrency(comparison.oldRegime.cess, { showSymbol: false })}</td>
                </tr>
                <tr className="font-bold text-sm bg-slate-100">
                  <td className="p-2.5 pl-3">Total Tax Liability</td>
                  <td className={`p-2.5 text-right font-mono ${isNewRecommended ? 'text-emerald-700 bg-emerald-50' : 'text-slate-800'}`}>
                    {formatIndianCurrency(comparison.newRegime.totalTaxPayable)}
                  </td>
                  <td className={`p-2.5 text-right font-mono ${!isNewRecommended ? 'text-emerald-700 bg-emerald-50' : 'text-slate-800'}`}>
                    {formatIndianCurrency(comparison.oldRegime.totalTaxPayable)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded bg-white hover:bg-slate-100"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => {
              onApplyRegime(comparison.recommendedRegime);
              onClose();
            }}
            className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded shadow-xs flex items-center gap-1.5 cursor-pointer"
          >
            <span>Apply {comparison.recommendedRegime}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
