import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Sparkles,
  Scale,
  TrendingDown,
  TrendingUp,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  Send,
  Loader2,
  RefreshCw,
  ArrowRight,
  Lightbulb,
  Building,
  HeartPulse,
  PiggyBank,
  FileCheck,
  MessageSquare,
  Zap,
  X,
} from 'lucide-react';
import { EmployeeMaster, EmployeeDeclaration, TaxConfig } from '../types/payroll';
import { computeTaxBreakdown } from '../utils/taxEngine';
import { formatInr } from '../utils/payrollEngine';
import { TaxOptimizationReport } from '../types/aiAdvisor';

interface SmartTaxAdvisorTabProps {
  employee: EmployeeMaster;
  declaration?: EmployeeDeclaration;
  taxConfig: TaxConfig;
  currentMonth: number;
  onEditDeclaration?: () => void;
}

export const SmartTaxAdvisorTab: React.FC<SmartTaxAdvisorTabProps> = ({
  employee,
  declaration,
  taxConfig,
  currentMonth,
  onEditDeclaration,
}) => {
  const [report, setReport] = useState<TaxOptimizationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Chatbot state
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'model'; text: string }>>([
    {
      role: 'model',
      text: `Hello ${employee.employeeName.split(' ')[0]}! I am your AI Tax & Payroll Advisor for FY ${taxConfig.financialYear} (AY 2026-27). Ask me anything about your salary structure, HRA rent proofs, Section 80C/80D deductions, or how to maximize your monthly take-home pay.`,
    },
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isChatLoading]);

  // Computed tax calculations from local deterministic engine
  const projectedAnnualBasic = employee.basicMonthly * 12;
  const projectedAnnualHra = employee.hraMonthly * 12;
  const projectedAnnualGross =
    (employee.basicMonthly +
      employee.hraMonthly +
      employee.conveyanceAllowanceMonthly +
      employee.childrenEducationAllowanceMonthly +
      employee.ltaMonthly +
      employee.specialAllowanceMonthly +
      employee.otherAllowanceMonthly) *
      12 +
    employee.variablePayAnnual +
    employee.joiningBonus;

  const annualPf =
    employee.pfApplicable === 'Y'
      ? (employee.pfWageCeilingApplied === 'Y' ? Math.min(employee.basicMonthly, 15000) : employee.basicMonthly) *
        0.12 *
        12
      : 0;

  const remainingMonths = 12 - currentMonth + 1;

  const oldBreakdown = computeTaxBreakdown(
    employee,
    declaration,
    taxConfig,
    'Old',
    projectedAnnualGross,
    projectedAnnualBasic,
    projectedAnnualHra,
    annualPf,
    remainingMonths,
    0
  );

  const newBreakdown = computeTaxBreakdown(
    employee,
    declaration,
    taxConfig,
    'New',
    projectedAnnualGross,
    projectedAnnualBasic,
    projectedAnnualHra,
    annualPf,
    remainingMonths,
    0
  );

  const diff = oldBreakdown.totalAnnualTaxLiability - newBreakdown.totalAnnualTaxLiability;
  const currentOptedRegime = declaration?.regimeDeclared || employee.taxRegimeOpted || 'New';

  // Fallback report generator in case server is warming up
  const generateDeterministicFallback = useCallback((): TaxOptimizationReport => {
    const isOldBetter = diff < -500;
    const isNewBetter = diff > 500;
    const recommended = isOldBetter ? 'Old' : 'New';
    const annualSavings = Math.abs(diff);
    const monthlyGain = Math.round(annualSavings / 12);

    const total80C =
      (declaration?.ppf || 0) +
      (declaration?.licPremium || 0) +
      (declaration?.elssMutualFund || 0) +
      (declaration?.housingLoanPrincipal || 0) +
      (declaration?.tuitionFees || 0) +
      (declaration?.taxSaverFd5yr || 0);

    const tips = [];

    // NPS tip
    const nps = declaration?.npsSelf80CCD1B || 0;
    if (nps < 50000) {
      const room = 50000 - nps;
      tips.push({
        section: 'Section 80CCD(1B) Tier-1 NPS',
        title: 'Invest in Voluntary NPS',
        maxLimit: '₹50,000 (Over & above 80C)',
        currentDeclared: formatInr(nps),
        potentialSavings: formatInr(room * 0.312),
        actionRecommendation: `Invest an additional ${formatInr(room)} in Tier-1 NPS to reduce taxable income directly in the Old Regime.`,
        priority: 'High' as const,
      });
    }

    // 80C tip
    if (total80C < 150000) {
      const gap = 150000 - total80C;
      tips.push({
        section: 'Section 80C',
        title: 'Utilize 80C Limit Fully',
        maxLimit: '₹1,50,000',
        currentDeclared: formatInr(total80C),
        potentialSavings: formatInr(gap * 0.312),
        actionRecommendation: `You have ${formatInr(gap)} of unused 80C headroom. Consider ELSS mutual funds (3-yr lock-in) or PPF before March 31.`,
        priority: 'High' as const,
      });
    }

    // Mediclaim
    const mediclaim = (declaration?.mediclaimSelfFamily || 0) + (declaration?.mediclaimParents || 0);
    tips.push({
      section: 'Section 80D Health Insurance',
      title: 'Health Insurance & Preventive Checkups',
      maxLimit: '₹25,000 (Self) + ₹50,000 (Senior Parents)',
      currentDeclared: formatInr(mediclaim),
      potentialSavings: formatInr(Math.min(25000, 25000 - (declaration?.mediclaimSelfFamily || 0)) * 0.312),
      actionRecommendation: 'Include preventive health check-up receipts (up to ₹5,000) for self and parents.',
      priority: 'Medium' as const,
    });

    return {
      recommendedRegime: recommended,
      annualTaxSavings: annualSavings,
      monthlyTakeHomeGain: monthlyGain,
      headline: isOldBetter
        ? `Old Tax Regime saves you ${formatInr(annualSavings)} annually (${formatInr(monthlyGain)}/month extra in your bank account).`
        : isNewBetter
        ? `New Tax Regime saves you ${formatInr(annualSavings)} annually with zero investment proof requirements.`
        : 'Both tax regimes result in an identical tax liability for your current income profile.',
      executiveSummary: isOldBetter
        ? `Your significant declared deductions (HRA exemption of ${formatInr(
            oldBreakdown.exemptionsSec10.hra
          )} and Chapter VI-A deductions of ${formatInr(
            oldBreakdown.chapterViaDeductions.total
          )}) overcome the New Regime's lower base tax slabs.`
        : `Under FY 2026-27 rules, the New Regime provides an elevated standard deduction of ₹75,000, full Section 87A rebate up to ₹12,00,000 net taxable income, and lower slab rates that surpass your declared deductions.`,
      keyDrivers: [
        isOldBetter
          ? `High Section 10 HRA exemption of ${formatInr(oldBreakdown.exemptionsSec10.hra)}`
          : `Enhanced standard deduction of ₹75,000 in New Regime (vs ₹50,000 in Old)`,
        isOldBetter
          ? `Chapter VI-A investments (80C, 80D, NPS) total ${formatInr(oldBreakdown.chapterViaDeductions.total)}`
          : `Expanded tax slabs with 0% tax up to ₹4,00,000 and 5% up to ₹8,00,000 under Section 115BAC`,
        `Current regime declared: ${currentOptedRegime} Regime (${
          currentOptedRegime === recommended ? 'Optimal Choice ✓' : 'Suboptimal Choice — Switch Recommended ⚠️'
        })`,
      ],
      actionableTips: tips,
      hraDeepDive: {
        annualHraReceived: projectedAnnualHra,
        exemptAmount: oldBreakdown.exemptionsSec10.hra,
        taxableHra: Math.max(0, projectedAnnualHra - oldBreakdown.exemptionsSec10.hra),
        landlordPanRequired: (declaration?.rentPaidAnnual || 0) > 100000,
        complianceNote:
          (declaration?.rentPaidAnnual || 0) > 100000
            ? 'Annual rent exceeds ₹1,00,000; Landlord PAN is legally mandatory for TDS relief.'
            : 'Annual rent is within ₹1,00,000; Landlord PAN is not mandatory.',
      },
      regimeSwitchGuidance: {
        actionNeeded:
          currentOptedRegime === recommended
            ? `No action needed! You are already on the optimal ${recommended} Regime.`
            : `Submit a regime change request to HR to switch to the ${recommended} Regime before the next payroll cutoff.`,
        deadline: 'Before the 20th of the active payroll month',
        impactOnMonthlyTds: `Switching to ${recommended} Regime will immediately increase your monthly in-hand credit by ${formatInr(
          monthlyGain
        )}.`,
      },
      personalizedFaqs: [
        {
          question: 'Can I switch my tax regime during the financial year?',
          answer:
            'Yes, salaried employees without business income can change their tax regime with their employer before the annual payroll freeze, or at the time of filing their annual ITR u/s 139(1).',
        },
        {
          question: 'Is it better to opt for the New Regime if I do not have rent receipts?',
          answer:
            'Yes! The New Regime provides ₹75,000 standard deduction and lower tax slabs without requiring you to lock funds in ELSS or submit rent agreements.',
        },
      ],
    };
  }, [
    diff,
    declaration,
    employee,
    oldBreakdown,
    newBreakdown,
    currentOptedRegime,
    projectedAnnualGross,
    projectedAnnualHra,
  ]);

  // Fetch AI-driven analysis from backend Gemini route
  const fetchAiReport = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/ai/tax-optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee,
          declaration,
          taxConfig,
          oldBreakdown,
          newBreakdown,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data: TaxOptimizationReport = await response.json();
      setReport(data);
    } catch (err: any) {
      console.warn('Gemini server route fallback to deterministic engine:', err);
      // Seamlessly fall back to deterministic report with CA logic
      setReport(generateDeterministicFallback());
    } finally {
      setLoading(false);
    }
  }, [employee, declaration, taxConfig, oldBreakdown, newBreakdown, generateDeterministicFallback]);

  useEffect(() => {
    fetchAiReport();
  }, [employee.employeeCode, declaration?.regimeDeclared, declaration?.rentPaidAnnual]);

  // Handle interactive chat question
  const handleSendChat = async (questionText?: string) => {
    const q = (questionText || chatInput).trim();
    if (!q || isChatLoading) return;

    const newMessages = [...chatMessages, { role: 'user' as const, text: q }];
    setChatMessages(newMessages);
    setChatInput('');
    setIsChatLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    try {
      const res = await fetch('/api/ai/tax-ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          question: q,
          employee,
          declaration,
          taxConfig,
          oldBreakdown,
          newBreakdown,
        }),
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }

      const data = await res.json();
      setChatMessages((prev) => [...prev, { role: 'model', text: data.answer }]);
    } catch (e: any) {
      clearTimeout(timeoutId);
      // Smart local fallback answering
      let fallbackAns = `Based on your CTC of ${formatInr(employee.annualCtc)}, your Old Regime tax is ${formatInr(
        oldBreakdown.totalAnnualTaxLiability
      )} vs New Regime tax of ${formatInr(newBreakdown.totalAnnualTaxLiability)}. `;

      if (q.toLowerCase().includes('nps')) {
        fallbackAns += `Investing up to ₹50,000 in Tier-1 NPS under Section 80CCD(1B) provides an exclusive deduction beyond Section 80C in the Old Regime, saving up to ₹15,600 in tax (31.2% slab).`;
      } else if (q.toLowerCase().includes('hra')) {
        fallbackAns += `Your HRA exemption is calculated as the minimum of: (1) Actual HRA received (${formatInr(
          projectedAnnualHra
        )}), (2) Rent paid minus 10% of basic, or (3) ${declaration?.rentedCityMetro === 'Y' ? '50%' : '40%'} of basic. Currently, your exempt HRA is ${formatInr(
          oldBreakdown.exemptionsSec10.hra
        )}.`;
      } else if (q.toLowerCase().includes('switch')) {
        fallbackAns += `You can request HR to update your regime before the monthly payroll cut-off, or elect your preferred regime when filing your annual ITR on the Income Tax portal.`;
      } else {
        fallbackAns += `Under FY 2026-27 rules, the ${report?.recommendedRegime || 'optimal'} regime provides the highest take-home pay for your declared deductions.`;
      }

      setChatMessages((prev) => [...prev, { role: 'model', text: fallbackAns }]);
    } finally {
      setIsChatLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const activeReport = report || generateDeterministicFallback();
  const isOptimal = currentOptedRegime === activeReport.recommendedRegime;

  return (
    <div className="space-y-6">
      {/* Hero Banner: AI Regime Recommendation */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white p-6 sm:p-8 shadow-xl border border-indigo-500/20">
        <div className="absolute -right-16 -bottom-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-16 -top-16 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-center gap-2">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
                <Sparkles className="h-3.5 w-3.5 text-indigo-400 animate-pulse" />
                <span>Gemini Tax Intelligence • AY 2026-27</span>
              </div>
              <span className="text-xs text-slate-400">
                Emp: <strong className="text-white">{employee.employeeName}</strong>
              </span>
            </div>

            <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
              {activeReport.headline}
            </h2>

            <p className="text-slate-300 text-xs sm:text-sm leading-relaxed">
              {activeReport.executiveSummary}
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <div
                className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold border ${
                  isOptimal
                    ? 'bg-emerald-500/20 border-emerald-400/40 text-emerald-300'
                    : 'bg-amber-500/20 border-amber-400/40 text-amber-300'
                }`}
              >
                {isOptimal ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                <span>
                  Current: {currentOptedRegime} Regime •{' '}
                  {isOptimal ? 'Optimal Selection' : `Switch to ${activeReport.recommendedRegime} to save`}
                </span>
              </div>

              {onEditDeclaration && !isOptimal && (
                <button
                  type="button"
                  onClick={onEditDeclaration}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-white text-indigo-900 hover:bg-slate-100 transition-colors shadow-sm cursor-pointer"
                >
                  <span>Update Declaration to {activeReport.recommendedRegime}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Quick Stats Metric Badge */}
          <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/15 p-5 flex flex-col justify-between gap-4 shrink-0 min-w-[260px]">
            <div>
              <span className="text-[11px] font-semibold text-indigo-200 uppercase tracking-wider block">
                Recommended Choice
              </span>
              <div className="text-2xl sm:text-3xl font-black text-white mt-0.5">
                {activeReport.recommendedRegime} Regime
              </div>
            </div>

            <div className="border-t border-white/10 pt-3 flex justify-between items-end">
              <div>
                <span className="text-[10px] text-slate-300 uppercase tracking-wider block">Annual Tax Savings</span>
                <div className="text-xl font-bold text-emerald-400">
                  {formatInr(activeReport.annualTaxSavings)}
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-300 uppercase tracking-wider block">Monthly Gain</span>
                <div className="text-base font-bold text-emerald-300">
                  +{formatInr(activeReport.monthlyTakeHomeGain)}/mo
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={fetchAiReport}
              disabled={loading}
              className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-bold text-white transition-colors cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Analyzing with Gemini...' : 'Re-run AI Analysis'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Side-by-Side Regime Comparison Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Old Regime Card */}
        <div
          className={`bg-white rounded-2xl border p-5 shadow-xs relative transition-all ${
            activeReport.recommendedRegime === 'Old'
              ? 'border-indigo-400 ring-2 ring-indigo-500/20 shadow-md'
              : 'border-slate-200 opacity-90'
          }`}
        >
          {activeReport.recommendedRegime === 'Old' && (
            <span className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
              AI Recommended ★
            </span>
          )}

          <div className="flex items-center gap-2 mb-4">
            <Scale className="h-4 w-4 text-indigo-600" />
            <h3 className="font-bold text-slate-900 text-sm">Old Tax Regime (Exemptions & Deductions)</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Gross Salary:</span>
              <span className="font-semibold text-slate-900">{formatInr(oldBreakdown.annualGrossSalary)}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Standard Deduction:</span>
              <span className="font-semibold text-slate-900">{formatInr(oldBreakdown.standardDeduction)}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">HRA Exemption (Sec 10(13A)):</span>
              <span className="font-semibold text-emerald-600">
                -{formatInr(oldBreakdown.exemptionsSec10.hra)}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Chapter VI-A Deductions (80C, 80D, NPS):</span>
              <span className="font-semibold text-emerald-600">
                -{formatInr(oldBreakdown.chapterViaDeductions.total)}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100 bg-slate-50 px-2 rounded-md">
              <span className="font-bold text-slate-700">Net Taxable Income:</span>
              <span className="font-bold text-slate-900">{formatInr(oldBreakdown.netTaxableIncome)}</span>
            </div>
            <div className="flex justify-between pt-2">
              <span className="font-bold text-slate-800">Total Annual Tax Liability:</span>
              <span className="font-black text-slate-900 text-sm">
                {formatInr(oldBreakdown.totalAnnualTaxLiability)}
              </span>
            </div>
          </div>
        </div>

        {/* New Regime Card */}
        <div
          className={`bg-white rounded-2xl border p-5 shadow-xs relative transition-all ${
            activeReport.recommendedRegime === 'New'
              ? 'border-indigo-400 ring-2 ring-indigo-500/20 shadow-md'
              : 'border-slate-200 opacity-90'
          }`}
        >
          {activeReport.recommendedRegime === 'New' && (
            <span className="absolute top-4 right-4 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
              AI Recommended ★
            </span>
          )}

          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-4 w-4 text-amber-500" />
            <h3 className="font-bold text-slate-900 text-sm">New Tax Regime (Section 115BAC Default)</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Gross Salary:</span>
              <span className="font-semibold text-slate-900">{formatInr(newBreakdown.annualGrossSalary)}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Standard Deduction (Revised):</span>
              <span className="font-semibold text-indigo-600">{formatInr(newBreakdown.standardDeduction)}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">HRA Exemption:</span>
              <span className="text-slate-400">Not Allowed u/s 115BAC</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Chapter VI-A Deductions:</span>
              <span className="text-slate-400">Not Allowed (Except 80CCD(2))</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100 bg-slate-50 px-2 rounded-md">
              <span className="font-bold text-slate-700">Net Taxable Income:</span>
              <span className="font-bold text-slate-900">{formatInr(newBreakdown.netTaxableIncome)}</span>
            </div>
            <div className="flex justify-between pt-2">
              <span className="font-bold text-slate-800">Total Annual Tax Liability:</span>
              <span className="font-black text-slate-900 text-sm">
                {formatInr(newBreakdown.totalAnnualTaxLiability)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Drivers Explanations */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-3">
        <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          <span>Why this recommendation was generated for you</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {activeReport.keyDrivers.map((driver, idx) => (
            <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed">
              <span className="font-bold text-indigo-700 block mb-1">Point {idx + 1}</span>
              {driver}
            </div>
          ))}
        </div>
      </div>

      {/* Actionable Tax Optimization Tips */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <PiggyBank className="h-4 w-4 text-emerald-600" />
              <span>Personalized Tax Optimization & Headroom Opportunities</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Specific deductions you can claim to further increase your monthly take-home pay
            </p>
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {activeReport.actionableTips.map((tip, idx) => (
            <div key={idx} className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/60 transition-colors">
              <div className="space-y-1 max-w-xl">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {tip.section}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      tip.priority === 'High'
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {tip.priority} Priority
                  </span>
                  <h4 className="font-bold text-slate-900 text-xs">{tip.title}</h4>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">{tip.actionRecommendation}</p>
                <div className="flex items-center gap-4 text-[11px] text-slate-400 font-medium pt-1">
                  <span>Cap: {tip.maxLimit}</span>
                  <span>•</span>
                  <span>Currently Declared: {tip.currentDeclared}</span>
                </div>
              </div>

              <div className="text-right shrink-0 bg-emerald-50 border border-emerald-200 px-3.5 py-2 rounded-xl">
                <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">Potential Relief</span>
                <span className="text-base font-black text-emerald-700">{tip.potentialSavings}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interactive AI Tax Copilot (Ask Anything) */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-4 bg-gradient-to-r from-slate-900 to-indigo-950 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-300">
              <MessageSquare className="h-4 w-4" />
            </div>
            <div>
              <h3 className="font-bold text-xs uppercase tracking-wider">AI Tax & Payroll Copilot</h3>
              <p className="text-[11px] text-slate-300">Ask any question about your salary, TDS, or AY 2026-27 rules</p>
            </div>
          </div>
          <span className="text-[10px] text-indigo-300 font-mono bg-white/10 px-2 py-0.5 rounded">
            Personalized to {employee.employeeCode}
          </span>
        </div>

        {/* Chat History */}
        <div className="p-5 max-h-[320px] overflow-y-auto space-y-3 bg-slate-50/50">
          {chatMessages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xl rounded-2xl p-3.5 text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-xs shadow-xs'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-xs shadow-xs'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {isChatLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-2xl p-3 text-xs text-slate-500 flex items-center gap-2 shadow-xs">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                <span>AI Advisor is reviewing tax rules and your salary records...</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="px-5 py-2 bg-slate-100 border-t border-slate-200 flex items-center gap-2 overflow-x-auto text-[11px]">
          <span className="text-slate-400 font-semibold shrink-0">Quick Ask:</span>
          {[
            'How is my HRA calculated?',
            'What if I invest ₹50k in Tier-1 NPS?',
            'Can I switch regimes before payroll lock?',
            'Do I need my landlord’s PAN for rent relief?',
          ].map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSendChat(chip)}
              className="px-2.5 py-1 bg-white hover:bg-indigo-50 hover:text-indigo-700 border border-slate-200 rounded-lg text-slate-700 transition-colors whitespace-nowrap cursor-pointer shadow-2xs"
            >
              {chip}
            </button>
          ))}
        </div>

        {/* Chat Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendChat();
          }}
          className="p-3 bg-white border-t border-slate-200 flex items-center gap-2"
        >
          <div className="relative flex-1 flex items-center min-w-0">
            <input
              ref={inputRef}
              type="text"
              id="tax-copilot-input"
              name="taxCopilotInput"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendChat();
                }
              }}
              autoComplete="off"
              placeholder={`Ask about deductions, allowances, or tax savings for ${employee.employeeName}...`}
              className="w-full text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 bg-white border border-slate-300 rounded-xl pl-3.5 pr-8 py-2.5 outline-none ring-1 ring-slate-200 focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 transition-all shadow-xs cursor-text"
            />
            {chatInput && (
              <button
                type="button"
                onClick={() => {
                  setChatInput('');
                  inputRef.current?.focus();
                }}
                className="absolute right-2.5 text-slate-400 hover:text-slate-600 p-0.5 rounded cursor-pointer"
                title="Clear input"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={!chatInput.trim() || isChatLoading}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs sm:text-sm font-bold rounded-xl transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer shrink-0"
          >
            <span>Send</span>
            <Send className="h-3.5 w-3.5" />
          </button>
        </form>
      </div>

      {/* Statutory Disclaimer */}
      <div className="p-4 bg-slate-100 rounded-xl border border-slate-200 text-[11px] text-slate-500 leading-relaxed flex items-start gap-2.5">
        <ShieldCheck className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-700 block">Statutory Compliance Note (AY 2026-27):</strong>
          This tax advisory calculation is simulated per Indian Income Tax Act guidelines for FY 2026-27 (Finance Act provisions). Final TDS deductions remain contingent upon employer verification of original investment proofs and landlord declarations before the final annual payroll cutoff.
        </div>
      </div>
    </div>
  );
};
