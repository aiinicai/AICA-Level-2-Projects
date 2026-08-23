/**
 * DataReviewPanel Component - High Density Design Theme
 * Features a high-density summary table with Field IDs, values, and confidence status,
 * detailed interactive schedule tabs, regime comparison trigger, and Word doc styling.
 */

import React, { useState } from 'react';
import {
  User,
  Briefcase,
  ShieldAlert,
  Calculator,
  Palette,
  RotateCcw,
  Check,
  Building,
  Info,
  TrendingUp,
  FileCheck,
  Table,
  SlidersHorizontal,
  TrendingDown,
  Printer,
  Sparkles,
} from 'lucide-react';
import { CompleteITRData } from '../../itr-types';
import { formatIndianCurrency, numberToIndianRupeesWords, parseIndianNumber } from '../../utils/numberParsing';
import { recalculateITR } from '../../utils/itrParser';
import { RegimeComparisonModal } from './RegimeComparisonModal';

interface DataReviewPanelProps {
  data: CompleteITRData;
  onChange: (updatedData: CompleteITRData) => void;
  onRefresh?: () => void;
  onClearAll?: () => void;
}

export const DataReviewPanel: React.FC<DataReviewPanelProps> = ({
  data,
  onChange,
  onRefresh,
  onClearAll,
}) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'personal' | 'income' | 'deductions' | 'tax' | 'ca' | 'style'>('summary');
  const [isRegimeModalOpen, setIsRegimeModalOpen] = useState(false);

  const updateField = (section: keyof CompleteITRData, field: string, value: any) => {
    const updated = {
      ...data,
      [section]: {
        ...(data[section] as any),
        [field]: value,
      },
    };
    const isTaxManual = section === 'taxComputation' && field !== 'totalTaxableIncome';
    onChange(recalculateITR(updated, !isTaxManual, isTaxManual));
  };

  const updateNumericField = (section: keyof CompleteITRData, field: string, rawVal: string) => {
    const num = parseIndianNumber(rawVal);
    updateField(section, field, num);
  };

  const handleAutoRecomputeTax = () => {
    onChange(recalculateITR(data, true, false));
  };

  const tabs = [
    { id: 'summary', label: 'Overview Table', icon: Table },
    { id: 'personal', label: '1. Assessee Info', icon: User },
    { id: 'income', label: '2. Five Heads', icon: Briefcase },
    { id: 'deductions', label: '3. Deductions (80C)', icon: ShieldAlert },
    { id: 'tax', label: '4. Tax & TDS', icon: Calculator },
    { id: 'style', label: '5. Document Style', icon: Palette },
  ] as const;

  const p = data.personalInfo;
  const inc = data.incomeHeads;
  const ded = data.deductions;
  const tax = data.taxComputation;
  const paid = data.taxesPaid;
  const ca = data.caDetails;
  const cfg = data.styleConfig;

  // High density summary table data rows
  const summaryRows = [
    {
      id: 'GTI_001',
      desc: 'Gross Total Income (GTI)',
      val: inc.grossTotalIncome,
      conf: 'high',
      highlight: false,
    },
    {
      id: 'DED_80C',
      desc: 'Deductions under Section 80C',
      val: ded.sec80C,
      conf: 'high',
      highlight: false,
    },
    {
      id: 'DED_80D',
      desc: 'Health Insurance Premium (80D)',
      val: ded.sec80D,
      conf: 'high',
      highlight: false,
    },
    {
      id: 'TI_CALC',
      desc: 'Total Taxable Income (Rounded Sec 288A)',
      val: tax.totalTaxableIncome,
      conf: 'calc',
      highlight: true,
      color: 'text-blue-600',
    },
    {
      id: 'TAX_PAY',
      desc: 'Total Tax & Cess Payable',
      val: tax.totalTaxAndInterest,
      conf: 'high',
      highlight: false,
    },
    {
      id: 'TDS_TOT',
      desc: 'Total TDS & Advance Tax Paid',
      val: paid.totalTaxesPaid,
      conf: 'high',
      highlight: false,
    },
    {
      id: paid.refundDue > 0 ? 'REF_EST' : 'DEM_BAL',
      desc: paid.refundDue > 0 ? 'Net Refund Due (Claimed)' : 'Net Balance Tax Payable',
      val: paid.refundDue > 0 ? paid.refundDue : paid.taxPayable,
      conf: 'high',
      highlight: true,
      color: paid.refundDue > 0 ? 'text-emerald-600' : 'text-amber-600',
    },
  ];

  const handlePrint = () => {
    window.print();
  };

  return (
    <section className="bg-white rounded-lg border border-slate-200 flex flex-col shadow-sm overflow-hidden">
      {/* High Density Header */}
      <div className="px-4 sm:px-5 py-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2.5">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            2. Data Review Panel
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-bold">
            {p.formType || 'ITR-1'} • AY {p.assessmentYear}
          </span>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-200 text-slate-700">
            {p.taxRegime}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Regime comparison trigger */}
          <button
            type="button"
            id="open-regime-comparison-btn"
            onClick={() => setIsRegimeModalOpen(true)}
            className="text-[11px] px-2.5 py-1 border border-emerald-300 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold flex items-center gap-1 shadow-2xs cursor-pointer transition-colors"
          >
            <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
            <span>Compare Regimes</span>
          </button>

          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              title="Recalculate all tax totals u/s 288A/B"
              className="text-[11px] px-2.5 py-1 border border-slate-300 rounded bg-white text-slate-600 hover:bg-slate-50 shadow-2xs font-medium cursor-pointer"
            >
              Recalculate
            </button>
          )}

          <button
            type="button"
            onClick={handlePrint}
            title="Print computation sheet"
            className="text-[11px] px-2 py-1 border border-slate-300 rounded bg-white text-slate-600 hover:bg-slate-50 shadow-2xs font-medium cursor-pointer flex items-center gap-1"
          >
            <Printer className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Print</span>
          </button>

          {onClearAll && (
            <button
              type="button"
              onClick={onClearAll}
              title="Reset data"
              className="text-[11px] px-2 py-1 border border-slate-300 rounded bg-white text-slate-600 hover:bg-slate-50 shadow-2xs font-medium cursor-pointer"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Tabs bar */}
      <div className="flex items-center overflow-x-auto border-b border-slate-200 bg-slate-50/30 px-3 pt-1.5 scrollbar-none gap-1">
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold border-b-2 transition-all whitespace-nowrap rounded-t cursor-pointer ${
                isActive
                  ? 'border-blue-600 text-blue-600 bg-white shadow-2xs'
                  : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100/50'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Panel Content */}
      <div className="p-4 sm:p-6 overflow-auto">
        {/* SUMMARY OVERVIEW TABLE (High Density Signature Layout) */}
        {activeTab === 'summary' && (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="text-left border-b border-slate-200">
                    <th className="py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Field ID</th>
                    <th className="py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Description</th>
                    <th className="py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider text-right">Value (INR)</th>
                    <th className="py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider text-center">Conf.</th>
                  </tr>
                </thead>
                <tbody className="text-sm text-slate-700">
                  {summaryRows.map((row) => (
                    <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50/70 transition-colors">
                      <td className="py-2.5 font-mono text-xs text-slate-500">{row.id}</td>
                      <td className={`py-2.5 ${row.highlight ? 'font-semibold text-slate-900' : ''}`}>
                        {row.desc}
                      </td>
                      <td className={`py-2.5 text-right font-bold font-mono ${row.color || 'text-slate-900'}`}>
                        {formatIndianCurrency(row.val, { showSymbol: false })}
                      </td>
                      <td className="py-2.5 text-center">
                        {row.conf === 'high' ? (
                          <span className="text-emerald-500 font-bold text-xs" title="High confidence extraction">●</span>
                        ) : (
                          <span className="text-blue-500 font-bold text-xs" title="Computed field">○</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Quick Profile Summary Bar */}
            <div className="p-3 bg-slate-50 rounded border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div>
                <span className="text-slate-500 font-medium">Assessee: </span>
                <span className="font-bold text-slate-800">{p.name || 'Unnamed Assessee'}</span>
                <span className="font-mono text-blue-700 font-bold ml-2">({p.pan || 'PAN PENDING'})</span>
              </div>
              <div className="text-slate-500">
                <span>Regime: <strong className="text-slate-700">{p.taxRegime}</strong></span>
                <span className="mx-2">•</span>
                <span>Ack: <strong className="font-mono text-slate-700">{p.ackNumber || 'N/A'}</strong></span>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('personal')}
                className="text-[11px] text-blue-600 hover:underline font-semibold cursor-pointer"
              >
                Edit Complete Details →
              </button>
            </div>
          </div>
        )}

        {/* TAB 1: Personal Details */}
        {activeTab === 'personal' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Full Name of Assessee *</label>
                <input
                  type="text"
                  value={p.name}
                  onChange={(e) => updateField('personalInfo', 'name', e.target.value)}
                  className="w-full text-xs font-semibold p-2 rounded border border-slate-300 focus:ring-1 focus:ring-blue-500 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">PAN *</label>
                <input
                  type="text"
                  value={p.pan}
                  onChange={(e) => updateField('personalInfo', 'pan', e.target.value.toUpperCase())}
                  className="w-full text-xs font-mono font-bold p-2 rounded border border-slate-300 bg-white text-blue-700 uppercase"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Aadhaar Number</label>
                <input
                  type="text"
                  value={p.aadhaar || ''}
                  onChange={(e) => updateField('personalInfo', 'aadhaar', e.target.value)}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Assessment Year *</label>
                <input
                  type="text"
                  value={p.assessmentYear}
                  onChange={(e) => updateField('personalInfo', 'assessmentYear', e.target.value)}
                  className="w-full text-xs font-semibold p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Financial Year</label>
                <input
                  type="text"
                  value={p.financialYear}
                  onChange={(e) => updateField('personalInfo', 'financialYear', e.target.value)}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">ITR Form Type</label>
                <select
                  value={p.formType}
                  onChange={(e) => updateField('personalInfo', 'formType', e.target.value)}
                  className="w-full text-xs font-semibold p-2 rounded border border-slate-300 bg-white"
                >
                  <option value="ITR-1">ITR-1 (Sahaj)</option>
                  <option value="ITR-2">ITR-2 (Capital Gains & Multiple HP)</option>
                  <option value="ITR-3">ITR-3 (Business & Profession PGBP)</option>
                  <option value="ITR-4">ITR-4 (Sugam - Presumptive 44AD/ADA)</option>
                  <option value="ITR-5">ITR-5 (LLP / Partnership Firm / AOP)</option>
                  <option value="ITR-6">ITR-6 (Company)</option>
                  <option value="ITR-7">ITR-7 (Trust / Society)</option>
                  <option value="ITR-V">ITR-V Acknowledgment</option>
                  <option value="Computation">Computation of Total Income Sheet</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Tax Regime *</label>
                <select
                  value={p.taxRegime === 'Old Regime' ? 'Old Regime' : 'New Regime'}
                  onChange={(e) => updateField('personalInfo', 'taxRegime', e.target.value)}
                  className="w-full text-xs font-semibold p-2 rounded border border-slate-300 bg-white"
                >
                  <option value="New Regime">New Regime</option>
                  <option value="Old Regime">Old Regime</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Acknowledgment No.</label>
                <input
                  type="text"
                  value={p.ackNumber || ''}
                  onChange={(e) => updateField('personalInfo', 'ackNumber', e.target.value)}
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Filing Date</label>
                <input
                  type="text"
                  value={p.filingDate || ''}
                  onChange={(e) => updateField('personalInfo', 'filingDate', e.target.value)}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Filing Section</label>
                <input
                  type="text"
                  value={p.filingStatus}
                  onChange={(e) => updateField('personalInfo', 'filingStatus', e.target.value)}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Nominated Bank Name</label>
                <input
                  type="text"
                  value={p.bankName || ''}
                  onChange={(e) => updateField('personalInfo', 'bankName', e.target.value)}
                  placeholder="e.g. State Bank of India"
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Bank Account Number</label>
                <input
                  type="text"
                  value={p.bankAccountNumber || ''}
                  onChange={(e) => updateField('personalInfo', 'bankAccountNumber', e.target.value)}
                  placeholder="e.g. 123456789012"
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Bank IFSC Code</label>
                <input
                  type="text"
                  value={p.bankIfsc || ''}
                  onChange={(e) => updateField('personalInfo', 'bankIfsc', e.target.value.toUpperCase())}
                  placeholder="e.g. SBIN0001234"
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 bg-white uppercase"
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Income Heads */}
        {activeTab === 'income' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                <span className="text-[11px] font-bold text-slate-800 block">1. Salary Income</span>
                <div>
                  <label className="block text-[10px] text-slate-500">Gross Salary u/s 17(1)</label>
                  <input
                    type="text"
                    value={inc.salaryGross || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'salaryGross', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">Standard Deduction u/s 16(ia)</label>
                  <input
                    type="text"
                    value={inc.salaryStandardDeduction || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'salaryStandardDeduction', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                  />
                </div>
                <div className="text-right text-[11px] font-bold text-slate-800">
                  Net Salary: {formatIndianCurrency(inc.salaryNet)}
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                <span className="text-[11px] font-bold text-slate-800 block">2. House Property</span>
                <div>
                  <label className="block text-[10px] text-slate-500">Gross Rent / Income</label>
                  <input
                    type="text"
                    value={inc.housePropertyGross || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'housePropertyGross', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">Housing Loan Interest u/s 24(b)</label>
                  <input
                    type="text"
                    value={inc.housePropertyInterest || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'housePropertyInterest', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                  />
                </div>
                <div className="text-right text-[11px] font-bold text-slate-800">
                  Net HP: {formatIndianCurrency(inc.housePropertyNet)}
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                <span className="text-[11px] font-bold text-slate-800 block">3. Business / Profession (PGBP)</span>
                <div>
                  <label className="block text-[10px] text-slate-500">Gross Turnover / Receipts</label>
                  <input
                    type="text"
                    value={inc.businessGrossReceipts || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'businessGrossReceipts', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">Net Profit / Presumptive 44AD/ADA</label>
                  <input
                    type="text"
                    value={inc.businessNetProfit || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'businessNetProfit', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                  />
                </div>
                <div className="text-right text-[11px] font-bold text-slate-800">
                  Net PGBP: {formatIndianCurrency(inc.businessNetProfit)}
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                <span className="text-[11px] font-bold text-slate-800 block">4. Capital Gains (Budget 2024 Updated)</span>
                <div>
                  <label className="block text-[10px] text-slate-500">STCG @ 20% u/s 111A (Post 23-Jul-2024)</label>
                  <input
                    type="text"
                    value={inc.capitalGainsSTCG_20Pct || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'capitalGainsSTCG_20Pct', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">STCG @ 15% u/s 111A (Pre 23-Jul-2024)</label>
                  <input
                    type="text"
                    value={inc.capitalGainsSTCG_15Pct || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'capitalGainsSTCG_15Pct', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">LTCG @ 12.5% u/s 112A (Post 23-Jul-2024)</label>
                  <input
                    type="text"
                    value={inc.capitalGainsLTCG_12_5Pct || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'capitalGainsLTCG_12_5Pct', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">LTCG @ 10% u/s 112A (Pre 23-Jul-2024)</label>
                  <input
                    type="text"
                    value={inc.capitalGainsLTCG_10Pct || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'capitalGainsLTCG_10Pct', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                    placeholder="0"
                  />
                </div>
                <div className="text-right text-[11px] font-bold text-slate-800 pt-1 border-t border-slate-200">
                  Net CG: {formatIndianCurrency(inc.capitalGainsNet)}
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                <span className="text-[11px] font-bold text-slate-800 block">5. Other Sources</span>
                <div>
                  <label className="block text-[10px] text-slate-500">Interest from Savings Accounts</label>
                  <input
                    type="text"
                    value={inc.otherSourcesInterestSavings || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'otherSourcesInterestSavings', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">Interest on Fixed / Term Deposits</label>
                  <input
                    type="text"
                    value={inc.otherSourcesInterestDeposits || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'otherSourcesInterestDeposits', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                    placeholder="0"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-500">Dividend Income from Equities/MFs</label>
                  <input
                    type="text"
                    value={inc.otherSourcesDividends || ''}
                    onChange={(e) => updateNumericField('incomeHeads', 'otherSourcesDividends', e.target.value)}
                    className="w-full text-xs font-mono p-1.5 rounded border border-slate-300 bg-white text-right"
                    placeholder="0"
                  />
                </div>
                <div className="text-right text-[11px] font-bold text-slate-800 pt-1 border-t border-slate-200">
                  Net OS: {formatIndianCurrency(inc.otherSourcesNet)}
                </div>
              </div>

              <div className="p-3 bg-blue-50 rounded border border-blue-200 flex flex-col justify-between">
                <span className="text-[11px] font-bold text-blue-900 uppercase">Gross Total Income (GTI)</span>
                <span className="text-lg font-bold text-blue-900 text-right">
                  {formatIndianCurrency(inc.grossTotalIncome)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Deductions */}
        {activeTab === 'deductions' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Section 80C (Max ₹1.5L)</label>
                <input
                  type="text"
                  value={ded.sec80C || ''}
                  onChange={(e) => updateNumericField('deductions', 'sec80C', e.target.value)}
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 text-right bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Section 80D (Mediclaim)</label>
                <input
                  type="text"
                  value={ded.sec80D || ''}
                  onChange={(e) => updateNumericField('deductions', 'sec80D', e.target.value)}
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 text-right bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Section 80CCD(1B) (NPS 50K)</label>
                <input
                  type="text"
                  value={ded.sec80CCD1B || ''}
                  onChange={(e) => updateNumericField('deductions', 'sec80CCD1B', e.target.value)}
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 text-right bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Section 80CCD(2) (Employer NPS)</label>
                <input
                  type="text"
                  value={ded.sec80CCD2 || ''}
                  onChange={(e) => updateNumericField('deductions', 'sec80CCD2', e.target.value)}
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 text-right bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Section 80G (Donations)</label>
                <input
                  type="text"
                  value={ded.sec80G || ''}
                  onChange={(e) => updateNumericField('deductions', 'sec80G', e.target.value)}
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 text-right bg-white"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Section 80TTA / 80TTB</label>
                <input
                  type="text"
                  value={ded.sec80TTA || ''}
                  onChange={(e) => updateNumericField('deductions', 'sec80TTA', e.target.value)}
                  className="w-full text-xs font-mono p-2 rounded border border-slate-300 text-right bg-white"
                />
              </div>
              <div className="p-2.5 bg-slate-50 rounded border border-slate-200 flex items-center justify-between sm:col-span-3">
                <span className="text-xs font-bold text-slate-700">Total Allowable Deductions:</span>
                <span className="text-sm font-bold text-emerald-600 font-mono">
                  {formatIndianCurrency(ded.totalDeductions)}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: Tax & TDS */}
        {activeTab === 'tax' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-blue-50 border border-blue-200 p-3 rounded">
              <div className="text-xs text-blue-900">
                <span className="font-bold">Regime: </span>{p.taxRegime} | <span className="font-bold">Taxable Income: </span>{formatIndianCurrency(tax.totalTaxableIncome)}
              </div>
              <button
                type="button"
                onClick={handleAutoRecomputeTax}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold transition flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Auto Recompute Slab Tax</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                <span className="text-xs font-bold text-slate-800 block">Tax Liability Breakdown</span>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">1. Tax on Total Income</span>
                  <input
                    type="text"
                    value={tax.taxOnTotalIncome || ''}
                    onChange={(e) => updateNumericField('taxComputation', 'taxOnTotalIncome', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">2. Special Rate Tax (Cap Gains)</span>
                  <input
                    type="text"
                    value={tax.specialRateTax || ''}
                    onChange={(e) => updateNumericField('taxComputation', 'specialRateTax', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">3. Less: Rebate u/s 87A</span>
                  <input
                    type="text"
                    value={tax.rebate87A || ''}
                    onChange={(e) => updateNumericField('taxComputation', 'rebate87A', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white text-emerald-600 font-semibold"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">4. Add: Surcharge</span>
                  <input
                    type="text"
                    value={tax.surcharge || ''}
                    onChange={(e) => updateNumericField('taxComputation', 'surcharge', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">5. Health & Education Cess @ 4%</span>
                  <input
                    type="text"
                    value={tax.cess || ''}
                    onChange={(e) => updateNumericField('taxComputation', 'cess', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">6. Less: Relief u/s 89 / 90 / 91</span>
                  <input
                    type="text"
                    value={tax.relief89 || ''}
                    onChange={(e) => updateNumericField('taxComputation', 'relief89', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white text-emerald-600"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">7. Interest u/s 234A/B/C + Fee 234F</span>
                  <div className="flex gap-1">
                    <input
                      type="text"
                      placeholder="234A"
                      value={tax.interest234A || ''}
                      onChange={(e) => updateNumericField('taxComputation', 'interest234A', e.target.value)}
                      className="w-14 text-[11px] font-mono p-1 rounded border border-slate-300 text-right bg-white"
                      title="Interest 234A"
                    />
                    <input
                      type="text"
                      placeholder="234B"
                      value={tax.interest234B || ''}
                      onChange={(e) => updateNumericField('taxComputation', 'interest234B', e.target.value)}
                      className="w-14 text-[11px] font-mono p-1 rounded border border-slate-300 text-right bg-white"
                      title="Interest 234B"
                    />
                    <input
                      type="text"
                      placeholder="234C"
                      value={tax.interest234C || ''}
                      onChange={(e) => updateNumericField('taxComputation', 'interest234C', e.target.value)}
                      className="w-14 text-[11px] font-mono p-1 rounded border border-slate-300 text-right bg-white"
                      title="Interest 234C"
                    />
                    <input
                      type="text"
                      placeholder="234F"
                      value={tax.fee234F || ''}
                      onChange={(e) => updateNumericField('taxComputation', 'fee234F', e.target.value)}
                      className="w-14 text-[11px] font-mono p-1 rounded border border-slate-300 text-right bg-white"
                      title="Late Fee 234F"
                    />
                  </div>
                </div>
                <div className="flex justify-between text-xs font-bold pt-2 border-t border-slate-200">
                  <span>Total Tax & Interest Payable</span>
                  <span className="font-mono text-blue-800">{formatIndianCurrency(tax.totalTaxAndInterest)}</span>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
                <span className="text-xs font-bold text-slate-800 block">Taxes Paid / Tax Credits</span>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">Advance Tax Paid</span>
                  <input
                    type="text"
                    value={paid.advanceTax || ''}
                    onChange={(e) => updateNumericField('taxesPaid', 'advanceTax', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">TDS on Salaries (Form 16)</span>
                  <input
                    type="text"
                    value={paid.tdsSalary || ''}
                    onChange={(e) => updateNumericField('taxesPaid', 'tdsSalary', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">TDS on Other Than Salary (16A/26AS)</span>
                  <input
                    type="text"
                    value={paid.tdsNonSalary || ''}
                    onChange={(e) => updateNumericField('taxesPaid', 'tdsNonSalary', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">TCS (Tax Collected at Source)</span>
                  <input
                    type="text"
                    value={paid.tcs || ''}
                    onChange={(e) => updateNumericField('taxesPaid', 'tcs', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-600">Self Assessment Tax (u/s 140A)</span>
                  <input
                    type="text"
                    value={paid.selfAssessmentTax || ''}
                    onChange={(e) => updateNumericField('taxesPaid', 'selfAssessmentTax', e.target.value)}
                    className="w-28 text-xs font-mono p-1 rounded border border-slate-300 text-right bg-white"
                  />
                </div>
                <div className="flex justify-between text-xs font-bold pt-2 border-t border-slate-200">
                  <span>Total Taxes Paid</span>
                  <span className="font-mono text-emerald-700">{formatIndianCurrency(paid.totalTaxesPaid)}</span>
                </div>

                <div className="mt-3 p-2 rounded bg-white border border-slate-200">
                  {paid.refundDue > 0 ? (
                    <div className="flex justify-between text-xs font-bold text-emerald-700">
                      <span>Net Refund Due (Sec 288B):</span>
                      <span className="font-mono text-sm">{formatIndianCurrency(paid.refundDue)}</span>
                    </div>
                  ) : (
                    <div className="flex justify-between text-xs font-bold text-blue-900">
                      <span>Net Tax Payable (Sec 288B):</span>
                      <span className="font-mono text-sm">{formatIndianCurrency(paid.taxPayable)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: Word Document Styles */}
        {activeTab === 'style' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Document Header Title</label>
                <input
                  type="text"
                  value={cfg.documentTitle}
                  onChange={(e) => updateField('styleConfig', 'documentTitle', e.target.value)}
                  className="w-full text-xs font-bold p-2 rounded border border-slate-300 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Subtitle</label>
                <input
                  type="text"
                  value={cfg.subtitle}
                  onChange={(e) => updateField('styleConfig', 'subtitle', e.target.value)}
                  className="w-full text-xs p-2 rounded border border-slate-300 bg-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1.5">Color Theme</label>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                {[
                  { id: 'navy', label: 'Navy' },
                  { id: 'slate', label: 'Slate' },
                  { id: 'emerald', label: 'Emerald' },
                  { id: 'burgundy', label: 'Burgundy' },
                  { id: 'classic', label: 'Classic' },
                ].map((th) => (
                  <button
                    key={th.id}
                    type="button"
                    onClick={() => updateField('styleConfig', 'themeColor', th.id)}
                    className={`py-1.5 px-2 text-xs rounded border text-center transition-all cursor-pointer ${
                      cfg.themeColor === th.id
                        ? 'border-blue-600 bg-blue-50 text-blue-700 font-bold'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {th.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 space-y-2">
              <label className="block text-[11px] font-bold text-slate-700 mb-1">Document Sections to Include</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <label className="flex items-center gap-2 p-2 rounded bg-slate-50 border border-slate-200 text-xs text-slate-700 cursor-pointer hover:bg-slate-100">
                  <input
                    type="checkbox"
                    checked={cfg.includeBankDetails ?? true}
                    onChange={(e) => updateField('styleConfig', 'includeBankDetails', e.target.checked)}
                    className="rounded text-blue-600"
                  />
                  <div>
                    <span className="font-semibold block">Bank Account for Refund</span>
                    <span className="text-[10px] text-slate-500">Displays nominated bank & IFSC code</span>
                  </div>
                </label>

                <label className="flex items-center gap-2 p-2 rounded bg-slate-50 border border-slate-200 text-xs text-slate-700 cursor-pointer hover:bg-slate-100">
                  <input
                    type="checkbox"
                    checked={cfg.includeIndianRupeeWords ?? true}
                    onChange={(e) => updateField('styleConfig', 'includeIndianRupeeWords', e.target.checked)}
                    className="rounded text-blue-600"
                  />
                  <div>
                    <span className="font-semibold block">Amount in Words</span>
                    <span className="text-[10px] text-slate-500">Includes Rupees in Words for net refund / tax</span>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Regime Comparison Modal */}
      <RegimeComparisonModal
        data={data}
        isOpen={isRegimeModalOpen}
        onClose={() => setIsRegimeModalOpen(false)}
        onApplyRegime={(regime) => {
          updateField('personalInfo', 'taxRegime', regime);
        }}
      />
    </section>
  );
};
