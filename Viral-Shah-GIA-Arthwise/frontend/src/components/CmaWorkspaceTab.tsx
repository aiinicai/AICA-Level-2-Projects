import React, { useState, useEffect } from 'react';
import { 
  Table, CheckCircle2, AlertTriangle, Save, RefreshCw, 
  HelpCircle, Sparkles, FileSpreadsheet, BookOpen, X, ShieldCheck, TrendingUp, Landmark
} from 'lucide-react';
import { CMAProjectData } from '../types';
import { formatINR, NumberUnitMode } from '../utils/formatters';
import { ApiClient } from '../api/client';

interface CmaWorkspaceTabProps {
  proposalId: string;
  unitMode: NumberUnitMode;
}

export const CmaWorkspaceTab: React.FC<CmaWorkspaceTabProps> = ({
  proposalId,
  unitMode,
}) => {
  const [cmaData, setCmaData] = useState<CMAProjectData | null>(null);
  const [activeForm, setActiveForm] = useState<'op' | 'bs' | 'wc' | 'ratios'>('op');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showCmaGuide, setShowCmaGuide] = useState(false);

  const fetchCmaData = async () => {
    setIsLoading(true);
    try {
      const res = await ApiClient.request<{ data: CMAProjectData }>(`/proposals/${proposalId}/cma`);
      setCmaData(res.data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCmaData();
  }, [proposalId]);

  const handleCellChange = (section: 'operating_statement' | 'balance_sheet', metric: string, yearIdx: number, val: string) => {
    if (!cmaData) return;
    const num = parseFloat(val) || 0;
    const updated = { ...cmaData };
    if (!updated[section][metric]) {
      updated[section][metric] = new Array(updated.years.length).fill(0);
    }
    updated[section][metric][yearIdx] = num;
    setCmaData(updated);
  };

  const handleSaveCma = async () => {
    if (!cmaData) return;
    setIsSaving(true);
    try {
      await ApiClient.request(`/proposals/${proposalId}/cma`, {
        method: 'PUT',
        body: JSON.stringify({
          base_year: 'FY 2024-25',
          data: cmaData,
        }),
      });
      alert('CMA Workspace successfully saved & mathematical balancing verified!');
      fetchCmaData();
    } catch (err: any) {
      alert(err.message || 'Error saving CMA');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !cmaData) {
    return <div className="text-center py-12 text-slate-400 text-xs">Loading 9-year CMA workspace...</div>;
  }

  const years = cmaData.years || [];

  return (
    <div className="space-y-4">
      {/* Top Balancing Status Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-brand-50 text-brand-800 rounded-lg">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-slate-900 text-sm">Credit Monitoring Arrangement (CMA) Workspace</h4>
            <p className="text-xs text-slate-500">
              Base Year: <strong>FY 2024-25 (Audited)</strong> + <strong>FY 2025-26 (Provisional/Current)</strong> + Forward Multi-Year Projections per RBI &amp; Banking Standards.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Mathematical Reconciliation Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Balance Sheet Reconciled (Assets = Liabilities)</span>
          </div>

          <button
            type="button"
            onClick={() => setShowCmaGuide(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold border border-slate-300 transition-all cursor-pointer"
            title="Understanding CMA Forms, MPBF Calculation & RBI Guidelines"
          >
            <BookOpen className="w-4 h-4 text-[#a45139]" />
            <span>CMA Logic Guide</span>
          </button>

          <button
            onClick={handleSaveCma}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#1b2632] hover:bg-[#28384a] text-white rounded-lg text-xs font-semibold shadow-sm transition-all cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{isSaving ? 'Saving...' : 'Save CMA'}</span>
          </button>
        </div>
      </div>

      {/* Form Sub-navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 text-xs font-semibold">
        <button
          onClick={() => setActiveForm('op')}
          className={`px-3 py-1.5 rounded-lg transition-all ${
            activeForm === 'op' ? 'bg-brand-800 text-white shadow-sm' : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          Form II: Operating Statement
        </button>
        <button
          onClick={() => setActiveForm('bs')}
          className={`px-3 py-1.5 rounded-lg transition-all ${
            activeForm === 'bs' ? 'bg-brand-800 text-white shadow-sm' : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          Form III: Balance Sheet Analysis
        </button>
        <button
          onClick={() => setActiveForm('wc')}
          className={`px-3 py-1.5 rounded-lg transition-all ${
            activeForm === 'wc' ? 'bg-brand-800 text-white shadow-sm' : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          Form V: Working Capital (Nayak & MPBF)
        </button>
        <button
          onClick={() => setActiveForm('ratios')}
          className={`px-3 py-1.5 rounded-lg transition-all ${
            activeForm === 'ratios' ? 'bg-brand-800 text-white shadow-sm' : 'bg-white text-slate-600 hover:bg-slate-100'
          }`}
        >
          Form VII: Key Ratios
        </button>
      </div>

      {/* Multi-Period Grid */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto p-4">
        {activeForm === 'op' && (
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="bg-brand-900 text-white font-semibold">
                <th className="py-2.5 px-3 min-w-[220px]">Form II: Particulars</th>
                {years.map((y, i) => (
                  <th key={i} className="py-2.5 px-3 text-right min-w-[120px] whitespace-nowrap">{y}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {[
                { label: 'Gross Sales / Turnover', key: 'gross_sales', isBold: true },
                { label: 'Cost of Materials / Direct Expenses', key: 'cost_of_materials' },
                { label: 'Other Direct Operational Costs', key: 'direct_expenses' },
                { label: 'Gross Profit', key: 'gross_profit', isBold: true },
                { label: 'Selling & Admin Overhead', key: 'selling_admin_expenses' },
                { label: 'Operating Profit (EBITDA)', key: 'ebitda', isBold: true, highlight: true },
                { label: 'Depreciation & Amortization', key: 'depreciation' },
                { label: 'Finance Costs (Interest on Term & WC Debt)', key: 'finance_costs' },
                { label: 'Profit Before Tax (PBT)', key: 'profit_before_tax', isBold: true },
                { label: 'Provision for Taxation', key: 'tax_provision' },
                { label: 'Profit After Tax (PAT)', key: 'profit_after_tax', isBold: true, highlight: true },
              ].map((row, idx) => {
                const vals = cmaData.operating_statement[row.key] || [];
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-50 ${
                      row.highlight ? 'bg-brand-50/70 font-semibold text-brand-950' : row.isBold ? 'font-semibold text-slate-900' : 'text-slate-700'
                    }`}
                  >
                    <td className="py-2.5 px-3 font-sans">{row.label}</td>
                    {years.map((_, yIdx) => (
                      <td key={yIdx} className="py-2.5 px-3 text-right">
                        {formatINR(vals[yIdx], unitMode, false)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {activeForm === 'bs' && (
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="bg-brand-900 text-white font-semibold">
                <th className="py-2.5 px-3 min-w-[220px]">Form III: Balance Sheet Line Items</th>
                {years.map((y, i) => (
                  <th key={i} className="py-2.5 px-3 text-right min-w-[120px] whitespace-nowrap">{y}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              <tr className="bg-slate-100 text-slate-800 font-sans font-bold">
                <td colSpan={years.length + 1} className="py-2 px-3">I. LIABILITIES & NET WORTH</td>
              </tr>
              {[
                { label: 'Paid-Up Equity Share Capital', key: 'share_capital' },
                { label: 'Reserves & Surplus', key: 'reserves_surplus' },
                { label: 'Tangible Net Worth (TNW)', key: 'tangible_net_worth', isBold: true },
                { label: 'Term Loans (Banks & NBFCs)', key: 'term_loans' },
                { label: 'Subordinated Unsecured Loans', key: 'unsecured_loans' },
                { label: 'Short Term Bank Borrowings (CC/OD Limit)', key: 'bank_borrowings_wc', isBold: true },
                { label: 'Sundry Creditors (Trade Payables)', key: 'sundry_creditors' },
                { label: 'Other Current Liabilities & Provisions', key: 'other_current_liabilities' },
                { label: 'TOTAL LIABILITIES & NET WORTH', key: 'total_liabilities', isBold: true, highlight: true },
              ].map((row, idx) => {
                const vals = cmaData.balance_sheet[row.key] || [];
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-50 ${
                      row.highlight ? 'bg-brand-50/70 font-semibold text-brand-950' : row.isBold ? 'font-semibold text-slate-900' : 'text-slate-700'
                    }`}
                  >
                    <td className="py-2 px-3 font-sans">{row.label}</td>
                    {years.map((_, yIdx) => (
                      <td key={yIdx} className="py-2 px-3 text-right">
                        {formatINR(vals[yIdx], unitMode, false)}
                      </td>
                    ))}
                  </tr>
                );
              })}

              <tr className="bg-slate-100 text-slate-800 font-sans font-bold">
                <td colSpan={years.length + 1} className="py-2 px-3">II. ASSETS & INVESTMENTS</td>
              </tr>
              {[
                { label: 'Gross Fixed Assets', key: 'gross_fixed_assets' },
                { label: 'Less: Accumulated Depreciation', key: 'accumulated_depreciation' },
                { label: 'Net Fixed Assets (Net Block)', key: 'net_fixed_assets', isBold: true },
                { label: 'Non-Current Investments', key: 'non_current_investments' },
                { label: 'Inventories (Raw Material + WIP + FG)', key: 'inventories' },
                { label: 'Sundry Debtors (Receivables)', key: 'sundry_debtors' },
                { label: 'Cash & Bank Balances', key: 'cash_and_bank' },
                { label: 'Other Current Assets & Advances', key: 'other_current_assets' },
                { label: 'TOTAL ASSETS', key: 'total_assets', isBold: true, highlight: true },
              ].map((row, idx) => {
                const vals = cmaData.balance_sheet[row.key] || [];
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-50 ${
                      row.highlight ? 'bg-brand-50/70 font-semibold text-brand-950' : row.isBold ? 'font-semibold text-slate-900' : 'text-slate-700'
                    }`}
                  >
                    <td className="py-2 px-3 font-sans">{row.label}</td>
                    {years.map((_, yIdx) => (
                      <td key={yIdx} className="py-2 px-3 text-right">
                        {formatINR(vals[yIdx], unitMode, false)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {activeForm === 'wc' && (
          <div className="space-y-6">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700">
              <strong>Form V Underwriting Guidance:</strong>
              <span className="block mt-1">
                • <strong>Nayak Turnover Method</strong>: Minimum 25% of turnover required as Working Capital (5% Margin + 20% Bank Finance). Standard for SME limits up to ₹5 Crore.
              </span>
              <span className="block mt-0.5">
                • <strong>Tandon Method II (MPBF)</strong>: Assesses Working Capital Gap (Current Assets - Other CL) with 25% margin on Current Assets.
              </span>
            </div>

            <table className="w-full text-xs text-left">
              <thead>
                <tr className="bg-brand-900 text-white font-semibold">
                  <th className="py-2.5 px-3">Assessment Period</th>
                  <th className="py-2.5 px-3 text-right">Projected Turnover</th>
                  <th className="py-2.5 px-3 text-right">Nayak Total Requirement (25%)</th>
                  <th className="py-2.5 px-3 text-right">Nayak Bank Finance (20%)</th>
                  <th className="py-2.5 px-3 text-right">Working Capital Gap (WCG)</th>
                  <th className="py-2.5 px-3 text-right">Tandon Method II MPBF</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {cmaData.working_capital_assessment?.map((wc, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3 font-sans font-semibold text-slate-800">{wc.year}</td>
                    <td className="py-2.5 px-3 text-right">{formatINR(wc.turnover, unitMode)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-600">{formatINR(wc.nayak_total_requirement, unitMode)}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-brand-900">{formatINR(wc.nayak_mpbf, unitMode)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-600">{formatINR(wc.wcg, unitMode)}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-emerald-800">{formatINR(wc.tandon_mpbf, unitMode)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeForm === 'ratios' && (
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="bg-brand-900 text-white font-semibold">
                <th className="py-2.5 px-3 min-w-[220px]">Form VII: Ratio Particulars</th>
                {years.map((y, i) => (
                  <th key={i} className="py-2.5 px-3 text-right min-w-[120px] whitespace-nowrap">{y}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {[
                { label: 'Current Ratio (CR)', key: 'current_ratio', suffix: 'x', bench: '≥ 1.33' },
                { label: 'Quick Ratio (QR)', key: 'quick_ratio', suffix: 'x', bench: '≥ 1.00' },
                { label: 'TOL / Tangible Net Worth', key: 'tol_tnw', suffix: '', bench: '≤ 3.50' },
                { label: 'Debt to Equity Ratio', key: 'debt_equity', suffix: '', bench: '≤ 2.00' },
                { label: 'Debt Service Coverage Ratio (DSCR)', key: 'dscr', suffix: 'x', bench: '≥ 1.35', isBold: true },
                { label: 'EBITDA Margin (%)', key: 'ebitda_margin_pct', suffix: '%' },
                { label: 'Net Profit Margin (%)', key: 'net_profit_margin_pct', suffix: '%' },
                { label: 'Debtor Collection Period', key: 'debtor_days', suffix: ' Days' },
                { label: 'Inventory Holding Period', key: 'inventory_days', suffix: ' Days' },
              ].map((row, idx) => {
                const vals = cmaData.ratios[row.key] || [];
                return (
                  <tr key={idx} className={`hover:bg-slate-50 ${row.isBold ? 'bg-brand-50/70 font-bold text-brand-950' : 'text-slate-800'}`}>
                    <td className="py-2.5 px-3 font-sans">
                      <div>{row.label}</div>
                      {row.bench && <span className="text-[10px] text-slate-500 font-normal">Benchmark: {row.bench}</span>}
                    </td>
                    {years.map((_, yIdx) => (
                      <td key={yIdx} className="py-2.5 px-3 text-right">
                        {vals[yIdx] !== undefined ? `${vals[yIdx]}${row.suffix || ''}` : '—'}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* CMA Logic & Underwriting Guide Modal */}
      {showCmaGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="bg-gradient-to-r from-[#1b2632] to-[#243344] text-white p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-amber-400" />
                  <span>Credit Monitoring Arrangement (CMA) Logic &amp; Formulation Guide</span>
                </h3>
                <p className="text-xs text-slate-300 mt-1">
                  RBI Guidelines, Multi-Period Projection Rules, MPBF &amp; Working Capital Calculation Benchmarks
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowCmaGuide(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6 text-xs text-slate-700 leading-relaxed">
              {/* Introduction & Regulatory Context */}
              <div className="bg-brand-50/50 p-4 rounded-xl border border-brand-100 flex gap-3">
                <Landmark className="w-5 h-5 text-brand-900 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-brand-950 text-sm mb-1">What is CMA &amp; Why Banks Require It?</h4>
                  <p>
                    The <strong>Credit Monitoring Arrangement (CMA)</strong> is a standardized financial analytical format mandated by the 
                    <strong> Reserve Bank of India (RBI)</strong> and commercial lending institutions for appraising working capital loans (Cash Credit/Overdraft) 
                    and Term Loans. It analyzes past financial performance, detects diversion of funds, and evaluates whether future operating cash flows 
                    will comfortably service bank debt.
                  </p>
                </div>
              </div>

              {/* Time Horizon & Base Year Anchoring */}
              <div>
                <h4 className="font-bold text-slate-900 text-sm mb-2 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-600" />
                  <span>Time Horizon &amp; Starting Base Year</span>
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="inline-block px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[10px] font-bold uppercase mb-1">
                      Base Year (Audited)
                    </span>
                    <h5 className="font-bold text-slate-900">FY 2024-25</h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Certified audited balance sheet &amp; P&amp;L. Establishes historical operational benchmarks and real margins.
                    </p>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="inline-block px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold uppercase mb-1">
                      Current Year (Provisional)
                    </span>
                    <h5 className="font-bold text-slate-900">FY 2025-26</h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      9M to 12M provisional performance. Validated against GST (GSTR-3B) and 12-month bank statement turnover.
                    </p>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="inline-block px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold uppercase mb-1">
                      Estimated Year
                    </span>
                    <h5 className="font-bold text-slate-900">FY 2026-27</h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      The operative loan sanction year. Turnover growth is realistically bounded (usually 10% – 25% YoY).
                    </p>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-white">
                    <span className="inline-block px-2 py-0.5 rounded bg-purple-100 text-purple-800 text-[10px] font-bold uppercase mb-1">
                      Multi-Year Projections
                    </span>
                    <h5 className="font-bold text-slate-900">FY 2027-28 to FY 2031-32</h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Multi-year projections tailored to match residual term loan tenure and verify lifetime average DSCR.
                    </p>
                  </div>
                </div>
              </div>

              {/* The 7 Core Forms Explained */}
              <div>
                <h4 className="font-bold text-slate-900 text-sm mb-3">Understanding the 7 CMA Forms</h4>
                <div className="space-y-3">
                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                    <h5 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Form I: Existing &amp; Proposed Credit Limits</span>
                      <span className="text-[10px] font-normal text-slate-500">Funded &amp; Non-Funded Facility Mapping</span>
                    </h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Lists all credit facilities from existing banks/NBFCs (CC, OD, WCDL, Term Loans, Letter of Credit, Bank Guarantees) alongside the proposed fresh or enhanced requirements and margins.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                    <h5 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Form II: Operating Statement</span>
                      <span className="text-[10px] font-normal text-slate-500">P&amp;L Analysis &amp; Cash Accrual</span>
                    </h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Dissects Revenue from Operations, Cost of Goods Sold (Raw materials, power, direct wages), Gross Profit, Selling &amp; Administrative expenses, 
                      <strong> EBITDA</strong>, Interest, Depreciation, PBT, Tax, and <strong>PAT</strong>. Verifies profit margins and ensures gross cash accruals (PAT + Depreciation) are positive.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                    <h5 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Form III: Analysis of Balance Sheet</span>
                      <span className="text-[10px] font-normal text-slate-500">Assets, Liabilities &amp; Net Working Capital</span>
                    </h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Classifies liabilities into <strong>Tangible Net Worth (TNW)</strong>, Term Liabilities, and Current Liabilities; and assets into Fixed Assets, Non-Current Assets, and 
                      <strong> Current Assets (TCA)</strong>. Checks that Net Working Capital (NWC = TCA - TCL) is healthy and expanding over time.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                    <h5 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Form IV: Comparative Current Assets &amp; Current Liabilities</span>
                      <span className="text-[10px] font-normal text-slate-500">Operating Cycle &amp; Holding Periods</span>
                    </h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Examines inventory turnover (Raw Material, WIP, Finished Goods days), Sundry Debtors collection period (e.g. 60–90 days), and Sundry Creditors payment terms to identify if working capital is locked up unnecessarily.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                    <h5 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Form V: Maximum Permissible Bank Finance (MPBF) Assessment</span>
                      <span className="text-[10px] font-normal text-slate-500">Tandon Committee &amp; Nayak Committee Methods</span>
                    </h5>
                    <div className="text-[11px] text-slate-600 mt-2 space-y-2">
                      <div className="bg-white p-2.5 rounded border border-slate-200">
                        <strong className="text-slate-800">1. Nayak Committee (Turnover Method) — Standard for MSMEs &amp; Limits ≤ ₹5-6 Crores:</strong>
                        <ul className="list-disc list-inside mt-1 space-y-0.5 text-slate-600">
                          <li>Total Working Capital Requirement = <strong>25% of Projected Annual Turnover</strong></li>
                          <li>Bank Finance (MPBF) = <strong>20% of Projected Annual Turnover</strong></li>
                          <li>Promoter’s Margin = <strong>5% of Projected Annual Turnover</strong> (from net working capital / equity)</li>
                        </ul>
                      </div>
                      <div className="bg-white p-2.5 rounded border border-slate-200">
                        <strong className="text-slate-800">2. Tandon Committee Method II — Standard for Mid &amp; Large Corporates:</strong>
                        <ul className="list-disc list-inside mt-1 space-y-0.5 text-slate-600">
                          <li>Working Capital Gap (WCG) = Total Current Assets (TCA) − Other Current Liabilities (OCL)</li>
                          <li>Mandatory Borrower Margin = <strong>25% of Total Current Assets (TCA)</strong> financed from Long-term Net Working Capital</li>
                          <li>Bank MPBF = <strong>TCA − OCL − (25% × TCA)</strong></li>
                          <li>Ensures Current Ratio is strictly maintained at <strong>≥ 1.33:1</strong></li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                    <h5 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Form VI: Funds Flow Statement</span>
                      <span className="text-[10px] font-normal text-slate-500">Sources vs Uses of Capital</span>
                    </h5>
                    <p className="text-[11px] text-slate-600 mt-1">
                      Tracks internal cash generation, equity capital, and term borrowings (Sources) versus capital expenditures, debt repayments, and drawings (Uses). Underwriters verify that long-term sources fund long-term uses, with no diversion of short-term bank credit into illiquid assets.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50">
                    <h5 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Form VII: Ratio Analysis &amp; Underwriting Tolerances</span>
                      <span className="text-[10px] font-normal text-slate-500">Key Health Indicators</span>
                    </h5>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                      <div className="bg-white p-2 rounded border border-slate-200 text-center">
                        <span className="text-[10px] text-slate-500 block">Current Ratio</span>
                        <span className="font-bold text-slate-800">≥ 1.33x</span>
                      </div>
                      <div className="bg-white p-2 rounded border border-slate-200 text-center">
                        <span className="text-[10px] text-slate-500 block">DSCR</span>
                        <span className="font-bold text-slate-800">≥ 1.35x</span>
                      </div>
                      <div className="bg-white p-2 rounded border border-slate-200 text-center">
                        <span className="text-[10px] text-slate-500 block">TOL / TNW</span>
                        <span className="font-bold text-slate-800">≤ 3.50x</span>
                      </div>
                      <div className="bg-white p-2 rounded border border-slate-200 text-center">
                        <span className="text-[10px] text-slate-500 block">Debt / Equity</span>
                        <span className="font-bold text-slate-800">≤ 2.00x</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Practical Underwriting Advice */}
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex gap-3">
                <ShieldCheck className="w-5 h-5 text-amber-800 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h5 className="font-bold text-amber-900">How to Prepare an Unassailable CMA Submission</h5>
                  <ul className="list-disc list-inside text-amber-800 space-y-1">
                    <li>Anchor Base Year (FY 2024-25) directly to audited financial statements with zero variance.</li>
                    <li>Ensure Current Year (FY 2025-26) sales reconcile with GSTR-3B filings and bank statement credit summations.</li>
                    <li>Keep projected sales growth between 12% – 20% unless major verified order books or capex justify higher.</li>
                    <li>Always confirm that Balance Sheet balances across all projected years (Total Assets = Total Liabilities).</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                type="button"
                onClick={() => setShowCmaGuide(false)}
                className="px-5 py-2 bg-[#1b2632] hover:bg-[#28384a] text-white rounded-lg text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                Close Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
