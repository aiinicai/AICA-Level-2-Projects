import React, { useState, useEffect } from 'react';
import { 
  Calculator, CheckCircle2, AlertTriangle, TrendingUp, ShieldCheck, 
  HelpCircle, ArrowDownRight, Layers, FileCheck, Plus, Trash2, X, Landmark, BookOpen, Sparkles
} from 'lucide-react';
import { Proposal, FinancialEvaluationResponse } from '../types';
import { formatINR, NumberUnitMode } from '../utils/formatters';
import { ApiClient } from '../api/client';
import { NumberInput } from './NumberInput';

interface ExistingLoanItem {
  id: string;
  lender_name: string;
  facility_type: string;
  sanctioned_limit: number;
  outstanding_balance: number;
  interest_rate: number;
  monthly_emi: number;
  residual_tenure_months: number;
}

interface EvaluationTabProps {
  proposal: Proposal;
  onRefresh: () => void;
  unitMode: NumberUnitMode;
}

export const EvaluationTab: React.FC<EvaluationTabProps> = ({
  proposal,
  onRefresh,
  unitMode,
}) => {
  // Financial inputs with sensible defaults
  const [monthlyIncome, setMonthlyIncome] = useState<number>(650000); // 6.5 Lakhs
  const [existingEmi, setExistingEmi] = useState<number>(50000);
  const [interestRate, setInterestRate] = useState<number>(proposal.target_rate || 9.25);
  const [tenureMonths, setTenureMonths] = useState<number>(proposal.tenure_months || 60);
  const [collateralValue, setCollateralValue] = useState<number>(18000000); // 1.8 Cr
  const [maxFoirPct, setMaxFoirPct] = useState<number>(60.0);
  const [maxLtvPct, setMaxLtvPct] = useState<number>(75.0);
  const [minDscrTarget, setMinDscrTarget] = useState<number>(1.35);

  // Business Performance & Balance Sheet inputs
  const [turnover, setTurnover] = useState<number>(48000000); // 4.8 Cr
  const [pat, setPat] = useState<number>(3500000);           // 35 Lakhs
  const [depreciation, setDepreciation] = useState<number>(1200000);
  const [financeCosts, setFinanceCosts] = useState<number>(800000);
  const [ebitda, setEbitda] = useState<number>(5500000);
  const [existingDebtRepay, setExistingDebtRepay] = useState<number>(1000000);

  const [currentAssets, setCurrentAssets] = useState<number>(22000000);
  const [currentLiabilities, setCurrentLiabilities] = useState<number>(14000000);
  const [inventory, setInventory] = useState<number>(2000000);
  const [sundryDebtors, setSundryDebtors] = useState<number>(8500000);
  const [sundryCreditors, setSundryCreditors] = useState<number>(4200000);
  const [tangibleNetWorth, setTangibleNetWorth] = useState<number>(15000000);
  const [totalOutsideLiab, setTotalOutsideLiab] = useState<number>(18000000);
  const [cogs, setCogs] = useState<number>(26000000);
  const [totalPurchases, setTotalPurchases] = useState<number>(24000000);

  // Existing Loans schedule state
  const [existingLoans, setExistingLoans] = useState<ExistingLoanItem[]>([]);
  const [showAddLoanModal, setShowAddLoanModal] = useState(false);
  const [showScoringGuide, setShowScoringGuide] = useState(false);
  const [newLoanForm, setNewLoanForm] = useState({
    lender_name: '',
    facility_type: 'term_loan',
    sanctioned_limit: 1000000,
    outstanding_balance: 750000,
    interest_rate: 9.5,
    monthly_emi: 22000,
    residual_tenure_months: 36,
  });

  const [evaluationResult, setEvaluationResult] = useState<FinancialEvaluationResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  const loadExistingLoans = async () => {
    try {
      const res = await ApiClient.request<ExistingLoanItem[]>(`/proposals/${proposal.id}/evaluation/existing-loans`);
      if (res) {
        setExistingLoans(res);
        if (res.length > 0) {
          const totalEmi = res.reduce((acc, l) => acc + (Number(l.monthly_emi) || 0), 0);
          setExistingEmi(totalEmi);
          setExistingDebtRepay(totalEmi * 12);
        }
      }
    } catch (err) {
      console.error('Failed to load existing loans:', err);
    }
  };

  const loadExtractedMetrics = async () => {
    try {
      const records = await ApiClient.request<any[]>(`/proposals/${proposal.id}/extractions`);
      if (records && records.length > 0) {
        const getVal = (name: string) => {
          const match = records.find(r => r.metric_name === name && r.normalized_value);
          return match ? parseFloat(match.normalized_value) : null;
        };
        const rev = getVal('revenue_from_operations') || getVal('total_income');
        if (rev) {
          setTurnover(rev);
          setMonthlyIncome(Math.round(rev / 12));
        }
        const p = getVal('pat');
        if (p !== null) setPat(p);
        const d = getVal('depreciation');
        if (d !== null) setDepreciation(d);
        const fc = getVal('finance_costs');
        if (fc !== null) setFinanceCosts(fc);
        const tnw = getVal('tangible_net_worth');
        if (tnw !== null) setTangibleNetWorth(tnw);
        const ca = getVal('current_assets');
        if (ca !== null) setCurrentAssets(ca);
        const cl = getVal('current_liabilities');
        if (cl !== null) setCurrentLiabilities(cl);
        const inv = getVal('inventories');
        if (inv !== null) setInventory(inv);
        const dr = getVal('trade_receivables');
        if (dr !== null) setSundryDebtors(dr);
        const cr = getVal('trade_payables');
        if (cr !== null) setSundryCreditors(cr);
        const cogsVal = getVal('cost_of_goods_sold');
        if (cogsVal !== null) setCogs(cogsVal);
      }
    } catch (err) {
      console.error('Failed to load extracted metrics:', err);
    }
  };

  useEffect(() => {
    loadExistingLoans();
    loadExtractedMetrics();
  }, [proposal.id]);

  const handleAddLoan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLoanForm.lender_name) {
      alert('Please enter lender / bank name');
      return;
    }
    try {
      await ApiClient.request(`/proposals/${proposal.id}/evaluation/existing-loans`, {
        method: 'POST',
        body: JSON.stringify(newLoanForm),
      });
      setShowAddLoanModal(false);
      setNewLoanForm({
        lender_name: '',
        facility_type: 'term_loan',
        sanctioned_limit: 1000000,
        outstanding_balance: 750000,
        interest_rate: 9.5,
        monthly_emi: 22000,
        residual_tenure_months: 36,
      });
      await loadExistingLoans();
      await handleRunEvaluation();
    } catch (err: any) {
      alert(err.message || 'Error saving existing loan');
    }
  };

  const handleDeleteLoan = async (id: string) => {
    if (!confirm('Are you sure you want to remove this existing loan facility?')) return;
    try {
      await ApiClient.request(`/proposals/${proposal.id}/evaluation/existing-loans/${id}`, {
        method: 'DELETE',
      });
      await loadExistingLoans();
      await handleRunEvaluation();
    } catch (err: any) {
      alert(err.message || 'Error removing loan');
    }
  };

  const handleRunEvaluation = async () => {
    setIsEvaluating(true);
    try {
      const res = await ApiClient.request<FinancialEvaluationResponse>(
        `/proposals/${proposal.id}/evaluation`,
        {
          method: 'POST',
          body: JSON.stringify({
            proposal_id: proposal.id,
            monthly_income_or_cash_accrual: monthlyIncome,
            total_existing_emi: existingEmi,
            interest_rate: interestRate,
            tenure_months: tenureMonths,
            assessed_collateral_value: collateralValue,
            max_foir_pct: maxFoirPct,
            max_ltv_pct: maxLtvPct,
            min_dscr_target: minDscrTarget,
            pat,
            depreciation,
            finance_costs: financeCosts,
            existing_term_debt_repayment: existingDebtRepay,
            ebitda,
            current_assets: currentAssets,
            current_liabilities: currentLiabilities,
            inventory,
            tangible_net_worth: tangibleNetWorth,
            total_outside_liabilities: totalOutsideLiab,
            turnover,
            sundry_debtors: sundryDebtors,
            sundry_creditors: sundryCreditors,
            cogs,
            total_purchases: totalPurchases,
          }),
        }
      );
      setEvaluationResult(res);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error running evaluation');
    } finally {
      setIsEvaluating(false);
    }
  };

  useEffect(() => {
    handleRunEvaluation();
  }, [proposal.id]);

  return (
    <div className="space-y-6">
      {/* Assessment Disclaimer Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900 leading-relaxed">
          <strong>Institutional Credit Note:</strong> All eligibility calculations and debt capacity estimates
          are preliminary computational models designed to assist debt syndication professionals in comparing bank policies.
          They do not constitute a credit sanction, in-principle approval, or guarantee from any financial institution.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Underwriting Inputs Form */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h4 className="font-bold text-slate-900 text-sm">Financial Evaluation Parameters</h4>
              <p className="text-xs text-slate-500">Tune cash flow, collateral, and balance sheet assumptions.</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowScoringGuide(true)}
                className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors border border-slate-300"
                title="View Bank Scoring Weights & Underwriting Benchmarks"
              >
                <BookOpen className="w-3.5 h-3.5 text-[#a45139]" />
                <span>Bank Scoring Guide</span>
              </button>
              <button
                onClick={handleRunEvaluation}
                disabled={isEvaluating}
                className="px-4 py-2 bg-[#1b2632] hover:bg-[#28384a] text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
              >
                {isEvaluating ? 'Evaluating...' : 'Recalculate Eligibility'}
              </button>
            </div>
          </div>

          {/* Section 1: Repayment Capacity */}
          <div>
            <h5 className="font-semibold text-slate-800 text-xs uppercase mb-3 text-brand-800">
              1. Income &amp; Repayment Capacity (FOIR)
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 mb-1">Monthly Cash Accrual / Income (₹)</label>
                <NumberInput
                  value={monthlyIncome}
                  onChange={setMonthlyIncome}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Existing Monthly EMIs (₹)</label>
                <NumberInput
                  value={existingEmi}
                  onChange={setExistingEmi}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Max Allowed FOIR (%)</label>
                <NumberInput
                  value={maxFoirPct}
                  onChange={setMaxFoirPct}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
            </div>
          </div>

          {/* Section: Existing Loans & Repayment Obligations Schedule */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h5 className="font-bold text-slate-900 text-xs uppercase flex items-center gap-1.5 text-[#1b2632]">
                  <Landmark className="w-4 h-4 text-[#a45139]" />
                  <span>Existing Loans &amp; Facilities Schedule</span>
                </h5>
                <p className="text-[11px] text-slate-500">
                  Track running Bank CC/OD, Term Loans, and NBFC borrowings. Directly factors into FOIR and DSCR debt service.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddLoanModal(true)}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-[#a45139] hover:bg-[#8e4430] text-white rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>+ Add Existing Loan</span>
              </button>
            </div>

            {existingLoans.length === 0 ? (
              <div className="p-3 bg-white rounded-lg border border-slate-200 text-center text-xs text-slate-500">
                No running loan facilities recorded. Click <strong>+ Add Existing Loan</strong> to input current debt obligations.
              </div>
            ) : (
              <div className="overflow-x-auto bg-white rounded-lg border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100/70 border-b border-slate-200 text-[11px] font-semibold text-slate-600">
                    <tr>
                      <th className="p-2.5">Lender Name</th>
                      <th className="p-2.5">Facility Type</th>
                      <th className="p-2.5 text-right">Limit (₹)</th>
                      <th className="p-2.5 text-right">Outstanding (₹)</th>
                      <th className="p-2.5 text-right">Monthly EMI (₹)</th>
                      <th className="p-2.5 text-center">Rate / Tenure</th>
                      <th className="p-2.5 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {existingLoans.map((loan) => (
                      <tr key={loan.id} className="hover:bg-slate-50/50">
                        <td className="p-2.5 font-bold text-slate-800">{loan.lender_name}</td>
                        <td className="p-2.5">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 uppercase">
                            {loan.facility_type.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="p-2.5 text-right font-medium">{formatINR(loan.sanctioned_limit, unitMode)}</td>
                        <td className="p-2.5 text-right font-bold text-slate-900">{formatINR(loan.outstanding_balance, unitMode)}</td>
                        <td className="p-2.5 text-right font-bold text-rose-700">{formatINR(loan.monthly_emi, unitMode)}</td>
                        <td className="p-2.5 text-center text-[11px] text-slate-500">
                          {loan.interest_rate}% • {loan.residual_tenure_months}m
                        </td>
                        <td className="p-2.5 text-center">
                          <button
                            type="button"
                            onClick={() => handleDeleteLoan(loan.id)}
                            className="p-1 text-slate-400 hover:text-rose-600 transition-colors"
                            title="Remove Loan"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-50 font-bold border-t border-slate-200 text-[11px]">
                    <tr>
                      <td colSpan={3} className="p-2.5 text-slate-700">Total Borrowings &amp; Debt Outflow</td>
                      <td className="p-2.5 text-right text-slate-900">
                        {formatINR(existingLoans.reduce((acc, l) => acc + (Number(l.outstanding_balance) || 0), 0), unitMode)}
                      </td>
                      <td className="p-2.5 text-right text-rose-700">
                        {formatINR(existingLoans.reduce((acc, l) => acc + (Number(l.monthly_emi) || 0), 0), unitMode)}
                      </td>
                      <td colSpan={2} className="p-2.5 text-center text-slate-500">
                        Annual EMI: {formatINR(existingLoans.reduce((acc, l) => acc + (Number(l.monthly_emi) || 0), 0) * 12, unitMode)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>

          {/* Section 2: Collateral & Facility Terms */}
          <div>
            <h5 className="font-semibold text-slate-800 text-xs uppercase mb-3 text-brand-800">
              2. Collateral Security & Loan Terms (LTV)
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 mb-1">Assessed Collateral Value (₹)</label>
                <NumberInput
                  value={collateralValue}
                  onChange={setCollateralValue}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Max Policy LTV (%)</label>
                <NumberInput
                  value={maxLtvPct}
                  onChange={setMaxLtvPct}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Interest Rate (% p.a.)</label>
                <NumberInput
                  value={interestRate}
                  onChange={setInterestRate}
                  step={0.05}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Tenure (Months)</label>
                <NumberInput
                  value={tenureMonths}
                  onChange={setTenureMonths}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
            </div>
          </div>

          {/* Section 3: P&L & Cash Flow Debt Service */}
          <div>
            <h5 className="font-semibold text-slate-800 text-xs uppercase mb-3 text-brand-800">
              3. P&L & Cash Accruals (DSCR & ICR)
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 mb-1">Annual Turnover (₹)</label>
                <NumberInput
                  value={turnover}
                  onChange={setTurnover}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Operating EBITDA (₹)</label>
                <NumberInput
                  value={ebitda}
                  onChange={setEbitda}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Profit After Tax (PAT) (₹)</label>
                <NumberInput
                  value={pat}
                  onChange={setPat}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Depreciation (₹)</label>
                <NumberInput
                  value={depreciation}
                  onChange={setDepreciation}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Finance Costs (₹)</label>
                <NumberInput
                  value={financeCosts}
                  onChange={setFinanceCosts}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Target Minimum DSCR</label>
                <NumberInput
                  value={minDscrTarget}
                  onChange={setMinDscrTarget}
                  step={0.05}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
            </div>
          </div>

          {/* Section 4: Balance Sheet & Working Capital */}
          <div>
            <h5 className="font-semibold text-slate-800 text-xs uppercase mb-3 text-brand-800">
              4. Working Capital & Balance Sheet Health
            </h5>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 mb-1">Total Current Assets (₹)</label>
                <NumberInput
                  value={currentAssets}
                  onChange={setCurrentAssets}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Current Liabilities (₹)</label>
                <NumberInput
                  value={currentLiabilities}
                  onChange={setCurrentLiabilities}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Sundry Debtors (₹)</label>
                <NumberInput
                  value={sundryDebtors}
                  onChange={setSundryDebtors}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
              <div>
                <label className="block text-slate-600 mb-1">Sundry Creditors (₹)</label>
                <NumberInput
                  value={sundryCreditors}
                  onChange={setSundryCreditors}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 font-medium"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Results & Limiting Constraint Dashboard */}
        <div className="space-y-4">
          {evaluationResult && (
            <>
              {/* Primary Eligibility Card */}
              <div className="bg-gradient-to-br from-brand-900 to-slate-900 text-white rounded-xl p-5 shadow-lg relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                  <Calculator className="w-24 h-24" />
                </div>
                <p className="text-xs uppercase tracking-wider text-brand-200 font-semibold mb-1">
                  Preliminary Assessed Eligibility
                </p>
                <h3 className="text-3xl font-extrabold text-white mb-2">
                  {formatINR(evaluationResult.preliminary_eligible_amount, unitMode)}
                </h3>

                <div className="mt-4 pt-4 border-t border-brand-700/60 text-xs space-y-2">
                  <div className="flex items-center justify-between text-brand-100">
                    <span>Requested Facility:</span>
                    <span className="font-semibold text-white">{formatINR(evaluationResult.requested_amount, unitMode)}</span>
                  </div>
                  <div className="flex items-center justify-between text-brand-100">
                    <span>Assessed Monthly EMI:</span>
                    <span className="font-semibold text-white">{formatINR(evaluationResult.proposed_emi, 'standard')}</span>
                  </div>
                </div>

                {/* Binding Limiting Constraint Pill */}
                <div className="mt-4 p-2.5 rounded-lg bg-amber-500/20 border border-amber-400/40 text-amber-200 text-xs">
                  <div className="font-semibold flex items-center gap-1.5 mb-0.5">
                    <ArrowDownRight className="w-3.5 h-3.5 text-amber-400" />
                    <span>Binding Limiting Constraint:</span>
                  </div>
                  <p className="text-[11px] text-amber-100">{evaluationResult.limiting_factor}</p>
                </div>
              </div>

              {/* Constraint Comparison Stack */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3">
                <h4 className="font-bold text-slate-900 text-xs uppercase text-slate-600">
                  Eligibility Breakdown by Policy Constraint
                </h4>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div>
                      <span className="font-semibold text-slate-800">FOIR Repayment Capacity</span>
                      <p className="text-[10px] text-slate-500">Max allowed total EMI {maxFoirPct}%</p>
                    </div>
                    <span className="font-bold text-slate-900">{formatINR(evaluationResult.eligible_loan_foir, unitMode)}</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div>
                      <span className="font-semibold text-slate-800">Collateral Valuation (LTV)</span>
                      <p className="text-[10px] text-slate-500">{maxLtvPct}% of market value</p>
                    </div>
                    <span className="font-bold text-slate-900">{formatINR(evaluationResult.eligible_loan_ltv, unitMode)}</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div>
                      <span className="font-semibold text-slate-800">DSCR Debt Service Accrual</span>
                      <p className="text-[10px] text-slate-500">Target DSCR {minDscrTarget}x</p>
                    </div>
                    <span className="font-bold text-slate-900">{formatINR(evaluationResult.eligible_loan_dscr, unitMode)}</span>
                  </div>
                </div>
              </div>

              {/* Underwriting Ratios Health Matrix */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3 text-xs">
                <h4 className="font-bold text-slate-900 uppercase text-[11px] text-slate-600">
                  Key Coverage & Liquidity Ratios
                </h4>

                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">Current Ratio</span>
                    <span className="font-bold text-slate-800 text-sm">{evaluationResult.current_ratio.toFixed(2)}x</span>
                    <span className="text-[10px] text-emerald-600 block">Bench: ≥ 1.33</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">DSCR (Debt Service)</span>
                    <span className="font-bold text-slate-800 text-sm">{evaluationResult.dscr.toFixed(2)}x</span>
                    <span className="text-[10px] text-emerald-600 block">Bench: ≥ 1.35</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">Fixed Obligation (FOIR)</span>
                    <span className="font-bold text-slate-800 text-sm">{evaluationResult.foir_pct.toFixed(1)}%</span>
                    <span className="text-[10px] text-slate-500 block">Policy: ≤ {maxFoirPct}%</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">Interest Coverage (ICR)</span>
                    <span className="font-bold text-slate-800 text-sm">{evaluationResult.icr.toFixed(2)}x</span>
                    <span className="text-[10px] text-emerald-600 block">Bench: ≥ 1.50</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">TOL / Tangible Net Worth</span>
                    <span className="font-bold text-slate-800 text-sm">{evaluationResult.tol_tnw_ratio.toFixed(2)}</span>
                    <span className="text-[10px] text-slate-500 block">Bench: ≤ 3.50</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] text-slate-500 block">Net Working Capital Cycle</span>
                    <span className="font-bold text-slate-800 text-sm">{evaluationResult.net_working_capital_cycle_days} Days</span>
                    <span className="text-[10px] text-slate-500 block">Debtor: {evaluationResult.debtor_days}d</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Add Existing Loan Facility Modal */}
      {showAddLoanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <Landmark className="w-4 h-4 text-[#a45139]" />
                <span>Add Existing Loan / Credit Facility</span>
              </h3>
              <button
                type="button"
                onClick={() => setShowAddLoanModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddLoan} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Lender / Bank Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. HDFC Bank, SBI, ICICI Bank, Bajaj Finance"
                  value={newLoanForm.lender_name}
                  onChange={(e) => setNewLoanForm({ ...newLoanForm, lender_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg p-2 focus:ring-1 focus:ring-[#1b2632]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Facility Type</label>
                  <select
                    value={newLoanForm.facility_type}
                    onChange={(e) => setNewLoanForm({ ...newLoanForm, facility_type: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                  >
                    <option value="cash_credit_od">Cash Credit / Overdraft</option>
                    <option value="term_loan">Term Loan</option>
                    <option value="lap">Loan Against Property (LAP)</option>
                    <option value="business_loan_unsecured">Unsecured Business Loan</option>
                    <option value="machinery_loan">Machinery / Equipment Loan</option>
                    <option value="vehicle_loan">Auto / Vehicle Loan</option>
                    <option value="home_loan">Home Loan</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Sanctioned Limit (₹)</label>
                  <NumberInput
                    value={newLoanForm.sanctioned_limit}
                    onChange={(v) => setNewLoanForm({ ...newLoanForm, sanctioned_limit: v })}
                    className="w-full border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Outstanding Balance (₹)</label>
                  <NumberInput
                    value={newLoanForm.outstanding_balance}
                    onChange={(v) => setNewLoanForm({ ...newLoanForm, outstanding_balance: v })}
                    className="w-full border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Monthly EMI (₹)</label>
                  <NumberInput
                    value={newLoanForm.monthly_emi}
                    onChange={(v) => setNewLoanForm({ ...newLoanForm, monthly_emi: v })}
                    className="w-full border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Interest Rate (% p.a.)</label>
                  <NumberInput
                    value={newLoanForm.interest_rate}
                    onChange={(v) => setNewLoanForm({ ...newLoanForm, interest_rate: v })}
                    step={0.1}
                    className="w-full border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Residual Tenure (Months)</label>
                  <NumberInput
                    value={newLoanForm.residual_tenure_months}
                    onChange={(v) => setNewLoanForm({ ...newLoanForm, residual_tenure_months: v })}
                    className="w-full border border-slate-300 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddLoanModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-50 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#1b2632] hover:bg-[#28384a] text-white rounded-lg font-bold shadow-sm"
                >
                  Save &amp; Recalculate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bank Scoring & Underwriting Criteria Guide Modal */}
      {showScoringGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="bg-gradient-to-r from-[#1b2632] to-[#243344] text-white p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-amber-400" />
                  <span>Indian Banking Credit Rating &amp; Scoring Guide</span>
                </h3>
                <p className="text-xs text-slate-300">
                  Methodology, benchmark cutoffs, and regulatory underwriting standards.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowScoringGuide(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto text-xs space-y-5 text-slate-700">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-xl border border-blue-200 bg-blue-50/50 space-y-1.5">
                  <h4 className="font-bold text-blue-900 text-sm flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-blue-700" />
                    <span>1. Financial &amp; Ratio Risk (35%)</span>
                  </h4>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    <li><strong>DSCR (Debt Service Coverage):</strong> Target ≥ 1.35x (Minimum 1.25x for term facilities). Measures ability of net cash accrual (PAT + Depr + Interest) to service principal + interest.</li>
                    <li><strong>Current Ratio:</strong> Target ≥ 1.33 under Tandon Committee Method II. Minimum 1.10x.</li>
                    <li><strong>TOL / Tangible Net Worth:</strong> Ideal ≤ 3.0x. Higher ratios indicate excessive leverage.</li>
                  </ul>
                </div>

                <div className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/50 space-y-1.5">
                  <h4 className="font-bold text-emerald-900 text-sm flex items-center gap-1.5">
                    <TrendingUp className="w-4 h-4 text-emerald-700" />
                    <span>2. Cash Flow &amp; Repayment Capacity (25%)</span>
                  </h4>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    <li><strong>FOIR (Fixed Obligation to Income Ratio):</strong> Caps total monthly EMI debt outflow at 50%–65% of net monthly income or cash accruals.</li>
                    <li><strong>Interest Coverage Ratio (ICR):</strong> EBIT / Interest. Must exceed 2.0x for commercial viability.</li>
                    <li><strong>Existing Loans Schedule:</strong> Every active loan directly reduces FOIR headroom.</li>
                  </ul>
                </div>

                <div className="p-3.5 rounded-xl border border-purple-200 bg-purple-50/50 space-y-1.5">
                  <h4 className="font-bold text-purple-900 text-sm flex items-center gap-1.5">
                    <Landmark className="w-4 h-4 text-purple-700" />
                    <span>3. Account Conduct &amp; Banking Risk (20%)</span>
                  </h4>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    <li><strong>ABB (Average Bank Balance):</strong> Checked against proposed monthly EMI (minimum 1.5x–2.0x).</li>
                    <li><strong>Cheque / ECS Bounces:</strong> Zero inward/outward technical/financial bounces in last 6 months.</li>
                    <li><strong>CC/OD Limit Utilization:</strong> Optimal between 50% and 85%. Constant &gt;95% utilization flags liquidity stress.</li>
                  </ul>
                </div>

                <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/50 space-y-1.5">
                  <h4 className="font-bold text-amber-900 text-sm flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-amber-700" />
                    <span>4. Promoter CIBIL &amp; Collateral (20%)</span>
                  </h4>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    <li><strong>CIBIL Score:</strong> Individual &amp; Commercial bureau score ≥ 750 for Tier 1 PSU/Private rates.</li>
                    <li><strong>Collateral LTV:</strong> Residential property up to 75%, Commercial up to 65%, Industrial up to 55%.</li>
                    <li><strong>Primary Security:</strong> Hypothecation of stocks and book debts (&lt;90 days old).</li>
                  </ul>
                </div>
              </div>

              {/* Benchmark Summary Table */}
              <div className="rounded-xl border border-slate-200 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#1b2632] text-white text-[11px]">
                    <tr>
                      <th className="p-2.5">Lender Category</th>
                      <th className="p-2.5">Min CIBIL</th>
                      <th className="p-2.5">Min DSCR</th>
                      <th className="p-2.5">Max FOIR</th>
                      <th className="p-2.5">Target Benchmark Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="bg-white">
                      <td className="p-2.5 font-bold text-slate-800">PSU Banks (SBI, PNB, BOB, Canara)</td>
                      <td className="p-2.5">700–725</td>
                      <td className="p-2.5 font-semibold text-emerald-700">≥ 1.35x</td>
                      <td className="p-2.5">≤ 55%</td>
                      <td className="p-2.5 font-mono">8.50% – 9.50%</td>
                    </tr>
                    <tr className="bg-slate-50/50">
                      <td className="p-2.5 font-bold text-slate-800">Top Private Banks (HDFC, ICICI, Axis)</td>
                      <td className="p-2.5">725–750</td>
                      <td className="p-2.5 font-semibold text-emerald-700">≥ 1.30x</td>
                      <td className="p-2.5">≤ 60%</td>
                      <td className="p-2.5 font-mono">9.00% – 10.25%</td>
                    </tr>
                    <tr className="bg-white">
                      <td className="p-2.5 font-bold text-slate-800">NBFCs &amp; Small Finance Banks</td>
                      <td className="p-2.5">650+</td>
                      <td className="p-2.5 font-semibold text-amber-700">≥ 1.15x</td>
                      <td className="p-2.5">≤ 70%</td>
                      <td className="p-2.5 font-mono">11.50% – 15.00%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-slate-50 border-t border-slate-200 px-6 py-3 flex justify-end">
              <button
                type="button"
                onClick={() => setShowScoringGuide(false)}
                className="px-4 py-2 bg-[#1b2632] hover:bg-[#28384a] text-white rounded-lg font-bold text-xs"
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
