import React, { useState } from 'react';
import {
  Scale,
  TrendingDown,
  CheckCircle,
  HelpCircle,
  ArrowRight,
  ShieldAlert,
  Info,
  Layers,
  Sparkles,
  Table,
} from 'lucide-react';
import { EmployeeMaster, EmployeeDeclaration, TaxConfig } from '../types/payroll';
import { computeTaxBreakdown } from '../utils/taxEngine';
import { FY_MONTHS } from '../utils/payrollEngine';
import { SmartTaxAdvisorTab } from './SmartTaxAdvisorTab';

interface TaxSimulatorTabProps {
  employees: EmployeeMaster[];
  declarations: EmployeeDeclaration[];
  taxConfig: TaxConfig;
  currentMonth: number;
  selectedEmployeeCode?: string;
  onSelectEmployee?: (code: string) => void;
  onEditDeclaration?: (declaration: EmployeeDeclaration) => void;
}

export const TaxSimulatorTab: React.FC<TaxSimulatorTabProps> = ({
  employees,
  declarations,
  taxConfig,
  currentMonth,
  selectedEmployeeCode,
  onSelectEmployee,
  onEditDeclaration,
}) => {
  const [empCode, setEmpCode] = useState<string>(
    selectedEmployeeCode || (employees.length > 0 ? employees[0].employeeCode : '')
  );
  const [viewMode, setViewMode] = useState<'matrix' | 'ai-advisory'>('matrix');

  const currentEmp = employees.find((e) => e.employeeCode === empCode) || employees[0];
  const currentDecl = declarations.find((d) => d.employeeCode === empCode);

  if (!currentEmp) {
    return <div className="p-8 text-center text-slate-500">No employee selected.</div>;
  }

  const projectedAnnualBasic = currentEmp.basicMonthly * 12;
  const projectedAnnualHra = currentEmp.hraMonthly * 12;
  const projectedAnnualGross =
    (currentEmp.basicMonthly +
      currentEmp.hraMonthly +
      currentEmp.conveyanceAllowanceMonthly +
      currentEmp.childrenEducationAllowanceMonthly +
      currentEmp.ltaMonthly +
      currentEmp.specialAllowanceMonthly +
      currentEmp.otherAllowanceMonthly) *
      12 +
    currentEmp.variablePayAnnual +
    currentEmp.joiningBonus;

  const annualPf = currentEmp.pfApplicable === 'Y'
    ? (currentEmp.pfWageCeilingApplied === 'Y' ? Math.min(currentEmp.basicMonthly, 15000) : currentEmp.basicMonthly) * 0.12 * 12
    : 0;

  const remainingMonths = 12 - currentMonth + 1;

  // Compute breakdown under both regimes
  const oldBreakdown = computeTaxBreakdown(
    currentEmp,
    currentDecl,
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
    currentEmp,
    currentDecl,
    taxConfig,
    'New',
    projectedAnnualGross,
    projectedAnnualBasic,
    projectedAnnualHra,
    annualPf,
    remainingMonths,
    0
  );

  const taxDiff = oldBreakdown.totalAnnualTaxLiability - newBreakdown.totalAnnualTaxLiability;
  const appliedRegime = currentDecl?.regimeDeclared || currentEmp.taxRegimeOpted;

  return (
    <div className="space-y-6">
      {/* Top Selector Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Scale className="h-5 w-5 text-indigo-600" />
            Dual-Regime Income Tax & TDS Simulator
          </h2>
          <p className="text-xs text-slate-500">
            Side-by-side statutory evaluation under Section 115BAC (New) vs. Regular Old Regime for FY {taxConfig.financialYear}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Mode Switcher */}
          <div className="inline-flex items-center bg-slate-100 p-1 rounded-xl text-xs font-semibold border border-slate-200">
            <button
              type="button"
              onClick={() => setViewMode('matrix')}
              className={`px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
                viewMode === 'matrix'
                  ? 'bg-white text-slate-900 shadow-xs font-bold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Table className="h-3.5 w-3.5" />
              <span>Statutory Matrix</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('ai-advisory')}
              className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                viewMode === 'ai-advisory'
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-xs font-bold'
                  : 'text-indigo-700 hover:text-indigo-900 font-semibold'
              }`}
            >
              <Sparkles className="h-3.5 w-3.5 text-amber-300" />
              <span>AI Advisor</span>
              <span
                className={`px-1 py-0.2 rounded text-[9px] font-extrabold uppercase ${
                  viewMode === 'ai-advisory' ? 'bg-amber-400 text-slate-950' : 'bg-indigo-100 text-indigo-800'
                }`}
              >
                Gemini
              </span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-600">Select Employee:</label>
            <select
              value={empCode}
              onChange={(e) => {
                setEmpCode(e.target.value);
                if (onSelectEmployee) onSelectEmployee(e.target.value);
              }}
              className="text-xs font-semibold bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {employees.map((emp) => (
                <option key={emp.employeeCode} value={emp.employeeCode}>
                  {emp.employeeCode} — {emp.employeeName} ({emp.designation})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {viewMode === 'ai-advisory' ? (
        <SmartTaxAdvisorTab
          employee={currentEmp}
          declaration={currentDecl}
          taxConfig={taxConfig}
          currentMonth={currentMonth}
          onEditDeclaration={() => currentDecl && onEditDeclaration && onEditDeclaration(currentDecl)}
        />
      ) : (
        <>
          {/* Recommendation Banner */}
          <div
            className={`rounded-xl p-4 border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
              taxDiff > 500
                ? 'bg-blue-50/80 border-blue-200 text-blue-900'
                : taxDiff < -500
                ? 'bg-purple-50/80 border-purple-200 text-purple-900'
                : 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-white shadow-xs shrink-0 mt-0.5">
                <TrendingDown
                  className={`h-5 w-5 ${
                    taxDiff > 500 ? 'text-blue-600' : taxDiff < -500 ? 'text-purple-600' : 'text-emerald-600'
                  }`}
                />
              </div>
              <div>
                <div className="text-sm font-bold">
                  {taxDiff > 500 ? (
                    <>New Tax Regime Recommended — Saves ₹{Math.abs(taxDiff).toLocaleString('en-IN')} per year</>
                  ) : taxDiff < -500 ? (
                    <>Old Tax Regime Recommended — Saves ₹{Math.abs(taxDiff).toLocaleString('en-IN')} per year</>
                  ) : (
                    <>Both Regimes Produce Equal Tax Liability (₹{oldBreakdown.totalAnnualTaxLiability.toLocaleString('en-IN')})</>
                  )}
                </div>
                <p className="text-xs mt-0.5 opacity-90">
                  Employee has currently opted for the <strong className="underline">{appliedRegime} Regime</strong> in their{' '}
                  {currentDecl ? 'Tax Declaration' : 'Master Profile'}.
                  {taxDiff > 500 && appliedRegime === 'Old' && (
                    <span className="font-semibold text-rose-700 ml-1">
                      (Note: Switching to New Regime will save ₹{Math.abs(taxDiff).toLocaleString('en-IN')}!)
                    </span>
                  )}
                  {taxDiff < -500 && appliedRegime === 'New' && (
                    <span className="font-semibold text-rose-700 ml-1">
                      (Note: Switching to Old Regime will save ₹{Math.abs(taxDiff).toLocaleString('en-IN')}!)
                    </span>
                  )}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-center">
              <button
                type="button"
                onClick={() => setViewMode('ai-advisory')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white text-xs font-bold shadow-xs transition-all cursor-pointer whitespace-nowrap"
              >
                <Sparkles className="h-3.5 w-3.5 text-amber-300" />
                <span>AI Advisor Plan</span>
              </button>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-white border border-slate-200 shadow-xs">
                Applied: <strong>{appliedRegime} Regime</strong>
              </span>
            </div>
          </div>

      {/* Side-by-Side Comparison Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">
            Line-by-Line Statutory Comparison — {currentEmp.employeeName} ({currentEmp.employeeCode})
          </h3>
          <span className="text-xs text-slate-500">All figures in INR (₹)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100 text-slate-700 border-b border-slate-200">
                <th className="py-2.5 px-4 font-bold w-1/2">Income Head / Exemption / Deduction</th>
                <th className="py-2.5 px-4 font-bold text-right w-1/4 bg-purple-50/60 text-purple-900 border-l border-r border-slate-200">
                  Old Tax Regime
                </th>
                <th className="py-2.5 px-4 font-bold text-right w-1/4 bg-blue-50/60 text-blue-900">
                  New Regime (u/s 115BAC)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-800 font-mono">
              {/* Gross Salary */}
              <tr className="bg-slate-50/50 font-sans">
                <td className="py-2 px-4 font-semibold text-slate-900">
                  1. Gross Salary (Projected Annual + Prev Employer)
                </td>
                <td className="py-2 px-4 text-right font-mono font-bold bg-purple-50/20 border-l border-r border-slate-200">
                  ₹{oldBreakdown.annualGrossSalary.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right font-mono font-bold bg-blue-50/20">
                  ₹{newBreakdown.annualGrossSalary.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Section 10 Exemptions */}
              <tr>
                <td className="py-2 px-4 pl-8 font-sans text-slate-600">
                  Less: HRA Exemption u/s 10(13A) (Least of 3)
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{oldBreakdown.exemptionsSec10.hra.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right text-slate-400 bg-blue-50/20">
                  Not Allowed (₹0)
                </td>
              </tr>

              <tr>
                <td className="py-2 px-4 pl-8 font-sans text-slate-600">
                  Less: Children Education Allowance & LTA
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{(oldBreakdown.exemptionsSec10.cea + oldBreakdown.exemptionsSec10.lta).toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right text-slate-400 bg-blue-50/20">
                  Not Allowed (₹0)
                </td>
              </tr>

              {/* Standard Deduction */}
              <tr className="bg-slate-50/30 font-sans">
                <td className="py-2 px-4 font-semibold text-slate-900">
                  2. Standard Deduction u/s 16(ia)
                </td>
                <td className="py-2 px-4 text-right font-mono text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{oldBreakdown.standardDeduction.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right font-mono font-semibold text-emerald-700 bg-blue-50/20">
                  -₹{newBreakdown.standardDeduction.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* House Property */}
              <tr>
                <td className="py-2 px-4 font-sans text-slate-700">
                  3. House Property Loss / Interest u/s 24(b) (Max ₹2L)
                </td>
                <td className="py-2 px-4 text-right bg-purple-50/20 border-l border-r border-slate-200">
                  {oldBreakdown.incomeFromHouseProperty < 0 ? (
                    <span className="text-emerald-700">-₹{Math.abs(oldBreakdown.incomeFromHouseProperty).toLocaleString('en-IN')}</span>
                  ) : (
                    <span>₹0</span>
                  )}
                </td>
                <td className="py-2 px-4 text-right text-slate-400 bg-blue-50/20">
                  Not Allowed (₹0)
                </td>
              </tr>

              {/* Other Sources */}
              <tr>
                <td className="py-2 px-4 font-sans text-slate-700">
                  4. Income from Other Sources (Savings / FD Interest)
                </td>
                <td className="py-2 px-4 text-right bg-purple-50/20 border-l border-r border-slate-200">
                  ₹{oldBreakdown.incomeFromOtherSources.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right bg-blue-50/20">
                  ₹{newBreakdown.incomeFromOtherSources.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Gross Total Income */}
              <tr className="bg-slate-100/60 font-sans font-semibold">
                <td className="py-2 px-4 text-slate-900">Gross Total Income (GTI)</td>
                <td className="py-2 px-4 text-right font-mono bg-purple-50/30 border-l border-r border-slate-200">
                  ₹{oldBreakdown.grossTotalIncome.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right font-mono bg-blue-50/30">
                  ₹{newBreakdown.grossTotalIncome.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Chapter VI-A Deductions */}
              <tr>
                <td className="py-2 px-4 pl-8 font-sans text-slate-600">
                  Sec 80C (EPF, PPF, ELSS, Home Principal - Capped ₹1.5L)
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{oldBreakdown.chapterViaDeductions.sec80C.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right text-slate-400 bg-blue-50/20">
                  Not Allowed (₹0)
                </td>
              </tr>

              <tr>
                <td className="py-2 px-4 pl-8 font-sans text-slate-600">
                  Sec 80CCD(1B) — Self NPS (Capped ₹50,000)
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{oldBreakdown.chapterViaDeductions.sec80CCD1B.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right text-slate-400 bg-blue-50/20">
                  Not Allowed (₹0)
                </td>
              </tr>

              <tr>
                <td className="py-2 px-4 pl-8 font-sans text-slate-600">
                  Sec 80CCD(2) — Employer NPS (10% Old vs 14% New)
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{oldBreakdown.chapterViaDeductions.sec80CCD2.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-blue-50/20 font-semibold">
                  -₹{newBreakdown.chapterViaDeductions.sec80CCD2.toLocaleString('en-IN')}
                </td>
              </tr>

              <tr>
                <td className="py-2 px-4 pl-8 font-sans text-slate-600">
                  Sec 80D (Health Insurance Self & Parents)
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{oldBreakdown.chapterViaDeductions.sec80D.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right text-slate-400 bg-blue-50/20">
                  Not Allowed (₹0)
                </td>
              </tr>

              {/* Net Taxable Income */}
              <tr className="bg-slate-100 font-sans font-bold">
                <td className="py-2.5 px-4 text-slate-900">5. Net Taxable Income</td>
                <td className="py-2.5 px-4 text-right font-mono text-indigo-900 bg-purple-100/40 border-l border-r border-slate-200">
                  ₹{oldBreakdown.netTaxableIncome.toLocaleString('en-IN')}
                </td>
                <td className="py-2.5 px-4 text-right font-mono text-indigo-900 bg-blue-100/40">
                  ₹{newBreakdown.netTaxableIncome.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Slab Tax */}
              <tr>
                <td className="py-2 px-4 font-sans text-slate-700">Tax Computed on Slabs</td>
                <td className="py-2 px-4 text-right bg-purple-50/20 border-l border-r border-slate-200">
                  ₹{oldBreakdown.taxOnIncome.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right bg-blue-50/20">
                  ₹{newBreakdown.taxOnIncome.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Rebate 87A */}
              <tr>
                <td className="py-2 px-4 font-sans text-slate-700">
                  Less: Rebate u/s 87A (Up to ₹5L Old vs Up to ₹12L New)
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-purple-50/20 border-l border-r border-slate-200">
                  -₹{oldBreakdown.rebate87A.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right text-emerald-700 bg-blue-50/20">
                  -₹{newBreakdown.rebate87A.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Surcharge & Cess */}
              <tr>
                <td className="py-2 px-4 font-sans text-slate-700">Health & Education Cess (4%)</td>
                <td className="py-2 px-4 text-right bg-purple-50/20 border-l border-r border-slate-200">
                  ₹{oldBreakdown.cess.toLocaleString('en-IN')}
                </td>
                <td className="py-2 px-4 text-right bg-blue-50/20">
                  ₹{newBreakdown.cess.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Total Annual Tax Liability */}
              <tr className="bg-slate-200/80 font-sans font-bold text-sm">
                <td className="py-3 px-4 text-slate-900">Total Annual Tax Liability</td>
                <td className="py-3 px-4 text-right font-mono text-purple-900 bg-purple-200/50 border-l border-r border-slate-200">
                  ₹{oldBreakdown.totalAnnualTaxLiability.toLocaleString('en-IN')}
                </td>
                <td className="py-3 px-4 text-right font-mono text-blue-900 bg-blue-200/50">
                  ₹{newBreakdown.totalAnnualTaxLiability.toLocaleString('en-IN')}
                </td>
              </tr>

              {/* Monthly Spreading */}
              <tr className="bg-slate-50 font-sans">
                <td className="py-2.5 px-4 font-semibold text-slate-800">
                  Monthly TDS Spreading ({remainingMonths} months remaining)
                </td>
                <td className="py-2.5 px-4 text-right font-mono font-bold text-purple-800 bg-purple-50/30 border-l border-r border-slate-200">
                  ₹{oldBreakdown.currentMonthTds.toLocaleString('en-IN')} / mo
                </td>
                <td className="py-2.5 px-4 text-right font-mono font-bold text-blue-800 bg-blue-50/30">
                  ₹{newBreakdown.currentMonthTds.toLocaleString('en-IN')} / mo
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* TDS Spreading Schedule Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
        <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
          TDS Monthly Deduction Schedule (FY {taxConfig.financialYear} — {appliedRegime} Regime)
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2 text-xs">
          {FY_MONTHS.map((m) => {
            const isPast = m.index < currentMonth;
            const isCurrent = m.index === currentMonth;
            const deduction = appliedRegime === 'Old' ? oldBreakdown.currentMonthTds : newBreakdown.currentMonthTds;

            return (
              <div
                key={m.index}
                className={`p-2.5 rounded-lg border flex flex-col items-center justify-center ${
                  isCurrent
                    ? 'bg-indigo-50 border-indigo-300 text-indigo-900 font-bold ring-1 ring-indigo-400'
                    : isPast
                    ? 'bg-slate-50 border-slate-200 text-slate-400'
                    : 'bg-white border-slate-200 text-slate-700'
                }`}
              >
                <span className="text-[11px] font-semibold">{m.name}</span>
                <span className="text-xs font-mono mt-1">₹{deduction.toLocaleString('en-IN')}</span>
                <span className="text-[9px] uppercase mt-0.5 opacity-70">
                  {isCurrent ? 'Current' : isPast ? 'Past' : 'Projected'}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </>
  )}
</div>
  );
};
