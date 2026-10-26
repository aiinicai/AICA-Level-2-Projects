import React, { useState, useMemo } from 'react';
import {
  X,
  Calculator,
  Percent,
  Calendar,
  DollarSign,
  TrendingUp,
  Plus,
  Check,
  Building,
} from 'lucide-react';
import { inr, inrS } from '../utils/calculations';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onAddToInvestments: (data: {
    name: string;
    type: 'fd' | 'rd';
    invested: number;
    current: number;
    rate: number;
    start: string;
    maturity: string;
    notes: string;
  }) => void;
}

export const FDCalculatorModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onAddToInvestments,
}) => {
  const [calcType, setCalcType] = useState<'fd' | 'rd'>('fd');
  const [depositAmount, setDepositAmount] = useState<number>(100000);
  const [interestRate, setInterestRate] = useState<number>(7.1);
  const [tenureYears, setTenureYears] = useState<number>(1);
  const [tenureMonths, setTenureMonths] = useState<number>(0);
  const [compoundingFreq, setCompoundingFreq] = useState<number>(4); // 4 = quarterly (standard for Indian banks)
  const [isSeniorCitizen, setIsSeniorCitizen] = useState<boolean>(false);
  const [bankName, setBankName] = useState<string>('State Bank of India');

  const effectiveRate = interestRate + (isSeniorCitizen ? 0.5 : 0);

  const totalMonths = tenureYears * 12 + tenureMonths;
  const tenureInYears = totalMonths / 12;

  // Calculation results
  const calculation = useMemo(() => {
    if (depositAmount <= 0 || tenureInYears <= 0 || effectiveRate <= 0) {
      return {
        invested: 0,
        maturity: 0,
        interest: 0,
        apy: 0,
      };
    }

    const r = effectiveRate / 100;
    const n = compoundingFreq; // times compounded per year

    if (calcType === 'fd') {
      // Lump sum compound interest formula: A = P * (1 + r/n)^(n*t)
      let maturity = 0;
      if (n === 0) {
        // Simple interest
        maturity = depositAmount * (1 + r * tenureInYears);
      } else {
        maturity = depositAmount * Math.pow(1 + r / n, n * tenureInYears);
      }
      const interest = maturity - depositAmount;
      const apy = (Math.pow(1 + (n > 0 ? r / n : r), n > 0 ? n : 1) - 1) * 100;

      return {
        invested: depositAmount,
        maturity: Math.round(maturity),
        interest: Math.round(interest),
        apy: +apy.toFixed(2),
      };
    } else {
      // Recurring Deposit (RD) formula standard:
      // In India, RD interest is compounded quarterly.
      // Total invested = depositAmount * totalMonths
      // Formula: M = P * ((1 + r/4)^(4*t) - 1) / (1 - (1 + r/4)^(-1/3))
      // Simplified monthly summation:
      let maturity = 0;
      const monthlyRate = r / 12;
      for (let m = 1; m <= totalMonths; m++) {
        // Each monthly installment earns interest for remaining months
        // Standard quarterly compounding approximation
        const quartersRemaining = (totalMonths - m + 1) / 3;
        maturity += depositAmount * Math.pow(1 + r / 4, quartersRemaining);
      }
      const totalInvested = depositAmount * totalMonths;
      const interest = maturity - totalInvested;

      return {
        invested: totalInvested,
        maturity: Math.round(maturity),
        interest: Math.round(interest),
        apy: effectiveRate,
      };
    }
  }, [
    calcType,
    depositAmount,
    effectiveRate,
    tenureInYears,
    totalMonths,
    compoundingFreq,
  ]);

  // Projected maturity date
  const maturityDateStr = useMemo(() => {
    const d = new Date();
    d.setMonth(d.getMonth() + totalMonths);
    return d.toISOString().slice(0, 10);
  }, [totalMonths]);

  const startDateStr = useMemo(() => {
    return new Date().toISOString().slice(0, 10);
  }, []);

  if (!isOpen) return null;

  const handleSaveToPortfolio = () => {
    onAddToInvestments({
      name: `${bankName} ${calcType.toUpperCase()} (${effectiveRate}% p.a.)`,
      type: calcType,
      invested: calculation.invested,
      current: calculation.maturity,
      rate: effectiveRate,
      start: startDateStr,
      maturity: maturityDateStr,
      notes: `Calculated with Paisa Pal FD tool. ${calcType.toUpperCase()} of ${inr(
        depositAmount
      )} for ${tenureYears}y ${tenureMonths}m at ${effectiveRate}% p.a.`,
    });
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-xl w-full p-6 shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#DCE2EA] dark:border-[#25324A]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#0E7C86]/10 text-[#0E7C86] flex items-center justify-center font-bold flex-shrink-0">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-lg leading-tight">
                Deposit & Return Calculator
              </h3>
              <p className="text-xs text-[#6F7E92] dark:text-[#8594AA]">
                Fixed Deposits (FD) and Recurring Deposits (RD) with bank compounding
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Selector */}
        <div className="grid grid-cols-2 gap-2 mt-5 p-1 bg-[#EEF1F5] dark:bg-[#0B1220] rounded-xl text-xs font-semibold">
          <button
            type="button"
            onClick={() => setCalcType('fd')}
            className={`py-2 rounded-lg transition ${
              calcType === 'fd'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                : 'text-[#6F7E92] dark:text-[#8594AA] hover:text-[#0F1B2D]'
            }`}
          >
            Fixed Deposit (Lump sum)
          </button>
          <button
            type="button"
            onClick={() => setCalcType('rd')}
            className={`py-2 rounded-lg transition ${
              calcType === 'rd'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] shadow-xs'
                : 'text-[#6F7E92] dark:text-[#8594AA] hover:text-[#0F1B2D]'
            }`}
          >
            Recurring Deposit (Monthly)
          </button>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5 text-xs">
          {/* Deposit Amount */}
          <div>
            <label className="block font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
              {calcType === 'fd' ? 'Total Deposit Amount (₹)' : 'Monthly Installment (₹)'}
            </label>
            <div className="relative">
              <span className="absolute left-3 top-2.5 text-[#6F7E92] font-semibold">₹</span>
              <input
                type="number"
                min="500"
                step="500"
                value={depositAmount || ''}
                onChange={(e) => setDepositAmount(+e.target.value)}
                className="w-full pl-7 pr-3 py-2 bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl font-semibold text-sm focus:outline-2 focus:outline-[#0E7C86]"
              />
            </div>
          </div>

          {/* Interest Rate */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="font-semibold text-[#46566C] dark:text-[#A9B6C9]">
                Interest Rate (% p.a.)
              </label>
              <label className="flex items-center gap-1 cursor-pointer text-[11px] text-[#0E7C86] font-medium">
                <input
                  type="checkbox"
                  checked={isSeniorCitizen}
                  onChange={(e) => setIsSeniorCitizen(e.target.checked)}
                  className="rounded text-[#0E7C86] focus:ring-[#0E7C86]"
                />
                <span>Senior citizen (+0.5%)</span>
              </label>
            </div>
            <div className="relative">
              <input
                type="number"
                step="0.05"
                min="1"
                max="25"
                value={interestRate || ''}
                onChange={(e) => setInterestRate(+e.target.value)}
                className="w-full pr-8 pl-3 py-2 bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl font-semibold text-sm focus:outline-2 focus:outline-[#0E7C86]"
              />
              <span className="absolute right-3 top-2.5 text-[#6F7E92] font-semibold">%</span>
            </div>
          </div>

          {/* Tenure */}
          <div>
            <label className="block font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
              Tenure (Years & Months)
            </label>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={tenureYears}
                onChange={(e) => setTenureYears(+e.target.value)}
                className="w-full px-2.5 py-2 bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl font-semibold text-xs focus:outline-2 focus:outline-[#0E7C86]"
              >
                {[0, 1, 2, 3, 4, 5, 7, 10].map((y) => (
                  <option key={y} value={y}>
                    {y} {y === 1 ? 'Year' : 'Years'}
                  </option>
                ))}
              </select>
              <select
                value={tenureMonths}
                onChange={(e) => setTenureMonths(+e.target.value)}
                className="w-full px-2.5 py-2 bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl font-semibold text-xs focus:outline-2 focus:outline-[#0E7C86]"
              >
                {[0, 1, 3, 6, 9].map((m) => (
                  <option key={m} value={m}>
                    {m} Months
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Bank / Institution Name */}
          <div>
            <label className="block font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
              Bank / Institution (Optional)
            </label>
            <input
              type="text"
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
              placeholder="e.g. SBI, HDFC, Post Office"
              className="w-full px-3 py-2 bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl text-xs focus:outline-2 focus:outline-[#0E7C86]"
            />
          </div>
        </div>

        {/* Calculation Result Summary Card */}
        <div className="mt-5 p-4 rounded-xl bg-gradient-to-br from-[#0B3B66]/10 via-[#0E7C86]/10 to-transparent border border-[#0E7C86]/25">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-[10px] uppercase font-bold text-[#6F7E92] dark:text-[#8594AA]">
                Total Invested
              </div>
              <div className="text-base sm:text-lg font-bold text-[#0F1B2D] dark:text-[#E8EDF5] mt-0.5">
                {inr(calculation.invested)}
              </div>
            </div>

            <div className="border-x border-[#DCE2EA] dark:border-[#25324A] px-2">
              <div className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-400">
                Interest Earned
              </div>
              <div className="text-base sm:text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                +{inr(calculation.interest)}
              </div>
            </div>

            <div>
              <div className="text-[10px] uppercase font-bold text-[#0E7C86] dark:text-[#5B9BE0]">
                Maturity Value
              </div>
              <div className="text-base sm:text-lg font-bold text-[#0E7C86] dark:text-[#5B9BE0] mt-0.5">
                {inr(calculation.maturity)}
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-[#DCE2EA]/60 dark:border-[#25324A]/60 flex items-center justify-between text-xs text-[#46566C] dark:text-[#A9B6C9]">
            <span>
              Tenure: <strong>{totalMonths} months</strong> ({tenureInYears.toFixed(2)} yrs)
            </span>
            <span>
              Maturity Date: <strong>{maturityDateStr}</strong>
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-5 pt-4 border-t border-[#DCE2EA] dark:border-[#25324A] flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleSaveToPortfolio}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add to My Investments</span>
          </button>
        </div>
      </div>
    </div>
  );
};
