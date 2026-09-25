import React, { useState, useEffect, useMemo } from 'react';
import {
  User,
  CreditCard,
  FileText,
  Scale,
  Download,
  Calendar,
  Building,
  MapPin,
  CheckCircle,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  ShieldCheck,
  Edit3,
  Eye,
  History,
  FileSpreadsheet,
  Sparkles,
} from 'lucide-react';
import {
  EmployeeMaster,
  EmployeeDeclaration,
  TaxConfig,
  MonthlySalaryRecord,
  PayrollRunSummary,
} from '../types/payroll';
import { TaxSimulatorTab } from './TaxSimulatorTab';
import { SmartTaxAdvisorTab } from './SmartTaxAdvisorTab';
import { FY_MONTHS, formatInr, getEmployeeAllMonthlyRecords } from '../utils/payrollEngine';

interface EmployeePortalTabProps {
  employee: EmployeeMaster;
  declaration?: EmployeeDeclaration;
  taxConfig: TaxConfig;
  payrollSummary: PayrollRunSummary;
  selectedMonth: number;
  onViewPayslip: (record: MonthlySalaryRecord) => void;
  onEditDeclaration: (declaration: EmployeeDeclaration) => void;
}

export const EmployeePortalTab: React.FC<EmployeePortalTabProps> = ({
  employee,
  declaration,
  taxConfig,
  payrollSummary,
  selectedMonth,
  onViewPayslip,
  onEditDeclaration,
}) => {
  const [subTab, setSubTab] = useState<'overview' | 'ai-advisor' | 'simulator' | 'declaration'>('overview');
  const [historyRange, setHistoryRange] = useState<'ytd' | 'full'>('ytd');
  const [activeBreakdownMonth, setActiveBreakdownMonth] = useState<number>(selectedMonth);

  // Sync activeBreakdownMonth if user changes selected month in global navigation
  useEffect(() => {
    setActiveBreakdownMonth(selectedMonth);
  }, [selectedMonth]);

  // Compute progressive historical salary records for all 12 months with true YTD accumulation
  const allMonthlyRecords = useMemo(() => {
    return getEmployeeAllMonthlyRecords(employee, declaration, taxConfig, 12);
  }, [employee, declaration, taxConfig]);

  // Current global record from payrollSummary (or fallback to computed record)
  const currentRecord = useMemo(() => {
    return (
      payrollSummary.records.find((r) => r.employeeCode === employee.employeeCode) ||
      allMonthlyRecords.find((r) => r.month === selectedMonth)
    );
  }, [payrollSummary.records, employee.employeeCode, allMonthlyRecords, selectedMonth]);

  // The record currently inspected in the detailed breakdown panel
  const activeRecord = useMemo(() => {
    return allMonthlyRecords.find((r) => r.month === activeBreakdownMonth) || currentRecord;
  }, [allMonthlyRecords, activeBreakdownMonth, currentRecord]);

  const activeMonthInfo = activeRecord ? FY_MONTHS[activeRecord.month - 1] : FY_MONTHS[selectedMonth - 1];
  const globalMonthInfo = FY_MONTHS[selectedMonth - 1];

  // Processed (YTD) months up to selectedMonth
  const processedRecords = useMemo(() => {
    return allMonthlyRecords.filter((r) => r.month <= selectedMonth);
  }, [allMonthlyRecords, selectedMonth]);

  // Records to display in the historical table based on range filter
  const displayedHistoryRecords = useMemo(() => {
    return historyRange === 'ytd' ? processedRecords : allMonthlyRecords;
  }, [historyRange, processedRecords, allMonthlyRecords]);

  // YTD Cumulative Totals (up to selected month)
  const ytdTotals = useMemo(() => {
    return processedRecords.reduce(
      (acc, r) => ({
        gross: acc.gross + r.grossEarned,
        pf: acc.pf + r.employeePf,
        pt: acc.pt + r.professionalTax,
        tds: acc.tds + r.tdsDeducted,
        deductions: acc.deductions + r.totalDeductions,
        net: acc.net + r.netPay,
      }),
      { gross: 0, pf: 0, pt: 0, tds: 0, deductions: 0, net: 0 }
    );
  }, [processedRecords]);

  // Full table totals for whatever is currently displayed
  const tableTotals = useMemo(() => {
    return displayedHistoryRecords.reduce(
      (acc, r) => ({
        gross: acc.gross + r.grossEarned,
        pf: acc.pf + r.employeePf,
        pt: acc.pt + r.professionalTax,
        tds: acc.tds + r.tdsDeducted,
        deductions: acc.deductions + r.totalDeductions,
        net: acc.net + r.netPay,
      }),
      { gross: 0, pf: 0, pt: 0, tds: 0, deductions: 0, net: 0 }
    );
  }, [displayedHistoryRecords]);

  // Export full historical statement to CSV
  const handleExportCsv = () => {
    const headers = [
      'Month',
      'Year',
      'Financial Year',
      'Payable Days',
      'LOP Days',
      'Gross Salary (INR)',
      'Basic (INR)',
      'HRA (INR)',
      'Conveyance (INR)',
      'Special Allowance (INR)',
      'EPF 12% (INR)',
      'Professional Tax (INR)',
      'Income Tax TDS (INR)',
      'Total Deductions (INR)',
      'Net Take-Home Pay (INR)',
      'Status',
    ];

    const rows = displayedHistoryRecords.map((r) => [
      `"${r.monthName}"`,
      r.year,
      `"${taxConfig.financialYear}"`,
      r.payableDays,
      r.lopDays,
      r.grossEarned,
      r.basicEarned,
      r.hraEarned,
      r.conveyanceEarned,
      r.specialAllowanceEarned,
      r.employeePf,
      r.professionalTax,
      r.tdsDeducted,
      r.totalDeductions,
      r.netPay,
      r.month <= selectedMonth ? 'Disbursed' : 'Projected',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Salary_Statement_${employee.employeeCode}_${taxConfig.financialYear}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Personalized Welcome Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-800 text-white font-bold text-2xl flex items-center justify-center shadow-md shrink-0">
              {employee.employeeName.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl font-bold text-slate-900">{employee.employeeName}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {employee.employeeCode}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {employee.employmentStatus}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1 font-medium">
                {employee.designation} • {employee.department} • Cost Center: {employee.costCenter}
              </p>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-slate-500">
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3 text-slate-400" />
                  {employee.locationCity} ({employee.metroFlag === 'Y' ? 'Metro' : 'Non-Metro'})
                </span>
                <span>•</span>
                <span className="font-mono">PAN: {employee.pan}</span>
                <span>•</span>
                <span>Joined: {employee.dateOfJoining}</span>
                <span>•</span>
                <span className="font-semibold text-slate-700">
                  Tax Regime: <span className="text-indigo-600">{employee.taxRegimeOpted} Regime</span>
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 self-start md:self-auto">
            <button
              type="button"
              onClick={() => setSubTab('ai-advisor')}
              className="inline-flex items-center gap-2 px-3.5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
              title="Open AI Smart Tax Advisor powered by Gemini"
            >
              <Sparkles className="h-4 w-4 text-amber-300 animate-pulse" />
              <span>AI Tax Advisor</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-extrabold bg-amber-400 text-slate-950 uppercase">
                Gemini
              </span>
            </button>

            {currentRecord && (
              <button
                type="button"
                onClick={() => onViewPayslip(currentRecord)}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-colors shadow-xs cursor-pointer"
                title="View official printable payslip for current month"
              >
                <Download className="h-4 w-4" />
                <span>View {globalMonthInfo.short} Payslip</span>
              </button>
            )}
          </div>
        </div>

        {/* Sub-navigation inside ESS */}
        <div className="flex border-t border-slate-100 mt-6 pt-2 gap-2 overflow-x-auto">
          <button
            onClick={() => setSubTab('overview')}
            className={`px-3 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
              subTab === 'overview'
                ? 'bg-indigo-50 text-indigo-700 font-bold'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <CreditCard className="h-4 w-4" />
            My Salary & Payslips Archive
          </button>

          <button
            onClick={() => setSubTab('ai-advisor')}
            className={`px-3 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
              subTab === 'ai-advisor'
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold shadow-xs'
                : 'text-indigo-700 bg-indigo-50/70 hover:bg-indigo-100/70 font-semibold'
            }`}
          >
            <Sparkles className={`h-4 w-4 ${subTab === 'ai-advisor' ? 'text-amber-300' : 'text-indigo-600'}`} />
            <span>AI Smart Tax Advisor</span>
            <span
              className={`px-1.5 py-0.2 rounded text-[9px] font-extrabold uppercase ${
                subTab === 'ai-advisor' ? 'bg-amber-400 text-slate-900' : 'bg-indigo-200 text-indigo-800'
              }`}
            >
              Gemini
            </span>
          </button>

          <button
            onClick={() => setSubTab('simulator')}
            className={`px-3 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
              subTab === 'simulator'
                ? 'bg-indigo-50 text-indigo-700 font-bold'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Scale className="h-4 w-4" />
            My Dual-Regime Tax Simulator
          </button>

          <button
            onClick={() => setSubTab('declaration')}
            className={`px-3 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
              subTab === 'declaration'
                ? 'bg-indigo-50 text-indigo-700 font-bold'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <FileText className="h-4 w-4" />
            My Tax Declarations (HRA, 80C, 80D)
          </button>
        </div>
      </div>

      {/* Subtab 1: Salary Overview & Historical Payslips Archive */}
      {subTab === 'overview' && (
        <div className="space-y-6">
          {/* Section 1: YTD Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Total Net Paid YTD (Apr – {globalMonthInfo.short})
              </span>
              <div className="text-2xl font-black text-emerald-600 mt-1">
                {formatInr(ytdTotals.net)}
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Across {processedRecords.length} completed pay periods
              </span>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Gross Salary Earned YTD
              </span>
              <div className="text-2xl font-black text-slate-900 mt-1">
                {formatInr(ytdTotals.gross)}
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Base salary + allowances received
              </span>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Income Tax (TDS) Deducted YTD
              </span>
              <div className="text-2xl font-black text-rose-600 mt-1">
                {formatInr(ytdTotals.tds)}
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Deposited under {employee.taxRegimeOpted} Regime
              </span>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Total EPF Accumulated YTD
              </span>
              <div className="text-2xl font-black text-indigo-600 mt-1">
                {formatInr(ytdTotals.pf)}
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Employee 12% statutory PF deposit
              </span>
            </div>
          </div>

          {/* Section 2: Historical Monthly Payslips Summary Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            {/* Table Header Bar */}
            <div className="p-4 sm:p-5 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-indigo-600 shrink-0" />
                <div>
                  <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                    Historical Monthly Payslips & Salary Register
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Financial Year {taxConfig.financialYear} • Click "View Payslip" to open official PDF/Print payslips
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Range Filter: YTD vs Full FY */}
                <div className="inline-flex items-center bg-slate-200/80 p-0.5 rounded-lg text-xs font-medium">
                  <button
                    type="button"
                    onClick={() => setHistoryRange('ytd')}
                    className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                      historyRange === 'ytd'
                        ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    YTD Processed ({processedRecords.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setHistoryRange('full')}
                    className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                      historyRange === 'full'
                        ? 'bg-white text-indigo-700 shadow-xs font-semibold'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    Full FY (12 Months)
                  </button>
                </div>

                {/* Export Statement CSV */}
                <button
                  type="button"
                  onClick={handleExportCsv}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-300 rounded-lg shadow-xs transition-colors cursor-pointer"
                  title="Download full salary history in CSV format"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Export CSV</span>
                </button>
              </div>
            </div>

            {/* Historical Payslips Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-100/75 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-4">Pay Period</th>
                    <th className="py-3 px-3 text-center">Status</th>
                    <th className="py-3 px-3 text-center">Payable Days</th>
                    <th className="py-3 px-4 text-right">Gross Earned</th>
                    <th className="py-3 px-3 text-right">EPF (12%)</th>
                    <th className="py-3 px-3 text-right">PT</th>
                    <th className="py-3 px-3 text-right">TDS (Tax)</th>
                    <th className="py-3 px-3 text-right">Deductions</th>
                    <th className="py-3 px-4 text-right">Net Take-Home</th>
                    <th className="py-3 px-4 text-center">Payslip Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {displayedHistoryRecords.map((rec) => {
                    const isCurrentGlobalMonth = rec.month === selectedMonth;
                    const isInspectingMonth = rec.month === activeBreakdownMonth;
                    const isPastOrCurrent = rec.month <= selectedMonth;

                    return (
                      <tr
                        key={rec.month}
                        className={`transition-colors hover:bg-slate-50/80 ${
                          isInspectingMonth ? 'bg-indigo-50/50' : ''
                        }`}
                      >
                        {/* Month & Year */}
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 text-xs">
                              {rec.monthName} {rec.year}
                            </span>
                            {isCurrentGlobalMonth && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-100 text-indigo-700 uppercase">
                                Current
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono">
                            Month {rec.month} of FY {taxConfig.financialYear}
                          </span>
                        </td>

                        {/* Status */}
                        <td className="py-3 px-3 text-center">
                          {isPastOrCurrent ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <CheckCircle2 className="h-3 w-3" />
                              Disbursed
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-500 border border-slate-200">
                              <Clock className="h-3 w-3" />
                              Projected
                            </span>
                          )}
                        </td>

                        {/* Payable Days */}
                        <td className="py-3 px-3 text-center">
                          <span className="font-semibold text-slate-800">
                            {rec.payableDays} / {rec.totalDaysInMonth}
                          </span>
                          {rec.lopDays > 0 && (
                            <span className="block text-[10px] text-rose-500 font-medium">
                              LOP: {rec.lopDays}d
                            </span>
                          )}
                        </td>

                        {/* Gross Earned */}
                        <td className="py-3 px-4 text-right font-bold text-slate-900">
                          {formatInr(rec.grossEarned)}
                        </td>

                        {/* EPF */}
                        <td className="py-3 px-3 text-right text-slate-600 font-mono">
                          {formatInr(rec.employeePf)}
                        </td>

                        {/* PT */}
                        <td className="py-3 px-3 text-right text-slate-600 font-mono">
                          {formatInr(rec.professionalTax)}
                        </td>

                        {/* TDS */}
                        <td className="py-3 px-3 text-right font-mono font-semibold text-rose-600">
                          {formatInr(rec.tdsDeducted)}
                        </td>

                        {/* Total Deductions */}
                        <td className="py-3 px-3 text-right text-slate-700 font-mono">
                          {formatInr(rec.totalDeductions)}
                        </td>

                        {/* Net Pay */}
                        <td className="py-3 px-4 text-right">
                          <span className="font-black text-emerald-700 text-xs">
                            {formatInr(rec.netPay)}
                          </span>
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-4 text-center">
                          <div className="flex items-center justify-center gap-1.5">
                            {/* Open Official Payslip Modal */}
                            <button
                              type="button"
                              onClick={() => onViewPayslip(rec)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-2xs transition-colors cursor-pointer"
                              title={`View, Print or Download official payslip for ${rec.monthName} ${rec.year}`}
                            >
                              <FileText className="h-3 w-3" />
                              <span>Payslip</span>
                            </button>

                            {/* Inspect Detailed Breakdown Below */}
                            <button
                              type="button"
                              onClick={() => setActiveBreakdownMonth(rec.month)}
                              className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold border transition-colors cursor-pointer ${
                                isInspectingMonth
                                  ? 'bg-indigo-100 text-indigo-800 border-indigo-300'
                                  : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200'
                              }`}
                              title={`Show earnings & deductions breakdown for ${rec.monthName} below`}
                            >
                              <Eye className="h-3 w-3 text-slate-500" />
                              <span>Details</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>

                {/* Table Summary Footer */}
                <tfoot>
                  <tr className="bg-slate-100 font-bold border-t-2 border-slate-300 text-slate-900 text-xs">
                    <td className="py-3 px-4" colSpan={3}>
                      <span className="uppercase text-[10px] text-slate-500 font-bold tracking-wider">
                        Total {historyRange === 'ytd' ? `YTD Processed (Months 1–${selectedMonth})` : 'Full Year (12 Months)'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-slate-900 font-bold">
                      {formatInr(tableTotals.gross)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      {formatInr(tableTotals.pf)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      {formatInr(tableTotals.pt)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-rose-600">
                      {formatInr(tableTotals.tds)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      {formatInr(tableTotals.deductions)}
                    </td>
                    <td className="py-3 px-4 text-right text-emerald-700 font-black text-sm">
                      {formatInr(tableTotals.net)}
                    </td>
                    <td className="py-3 px-4 text-center text-[10px] text-slate-500">
                      {displayedHistoryRecords.length} Pay Slips
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Section 3: Detailed Breakdown for Selected/Active Month */}
          {activeRecord && (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
              <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-indigo-600" />
                  <div>
                    <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Itemized Breakdown for {activeMonthInfo.name} {activeRecord.year} (Month {activeRecord.month} of FY {taxConfig.financialYear})
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      {activeRecord.month === selectedMonth
                        ? 'Currently selected pay period in top navbar'
                        : `Viewing historical archive for ${activeMonthInfo.name}`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {activeRecord.month !== selectedMonth && (
                    <button
                      type="button"
                      onClick={() => setActiveBreakdownMonth(selectedMonth)}
                      className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-2.5 py-1 bg-white border border-slate-200 rounded-lg cursor-pointer transition-colors"
                    >
                      Reset to Current ({globalMonthInfo.short})
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => onViewPayslip(activeRecord)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-colors cursor-pointer"
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span>Print {activeMonthInfo.short} Payslip</span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-200">
                {/* Earnings Column */}
                <div className="p-5 space-y-3">
                  <h4 className="text-xs font-bold text-emerald-800 uppercase tracking-wider border-b border-emerald-100 pb-2">
                    Earnings (Earned for {activeRecord.payableDays} Payable Days)
                  </h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between text-slate-600">
                      <span>Basic Salary</span>
                      <span className="font-semibold text-slate-900">{formatInr(activeRecord.basicEarned)}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>House Rent Allowance (HRA)</span>
                      <span className="font-semibold text-slate-900">{formatInr(activeRecord.hraEarned)}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Special Allowance</span>
                      <span className="font-semibold text-slate-900">{formatInr(activeRecord.specialAllowanceEarned)}</span>
                    </div>
                    {activeRecord.conveyanceEarned > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>Conveyance Allowance</span>
                        <span className="font-semibold text-slate-900">{formatInr(activeRecord.conveyanceEarned)}</span>
                      </div>
                    )}
                    {activeRecord.ceaEarned > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>Children Education Allowance</span>
                        <span className="font-semibold text-slate-900">{formatInr(activeRecord.ceaEarned)}</span>
                      </div>
                    )}
                    {activeRecord.ltaEarned > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>Leave Travel Allowance (LTA)</span>
                        <span className="font-semibold text-slate-900">{formatInr(activeRecord.ltaEarned)}</span>
                      </div>
                    )}
                    {activeRecord.variablePayEarned > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>Variable Pay (Annual Performance)</span>
                        <span className="font-semibold text-slate-900">{formatInr(activeRecord.variablePayEarned)}</span>
                      </div>
                    )}
                    {activeRecord.joiningBonusEarned > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>Joining Bonus</span>
                        <span className="font-semibold text-slate-900">{formatInr(activeRecord.joiningBonusEarned)}</span>
                      </div>
                    )}
                  </div>
                  <div className="pt-3 border-t border-slate-200 flex justify-between font-bold text-slate-900">
                    <span>Total Gross Earnings</span>
                    <span className="text-emerald-600">{formatInr(activeRecord.grossEarned)}</span>
                  </div>
                </div>

                {/* Deductions Column */}
                <div className="p-5 space-y-3">
                  <h4 className="text-xs font-bold text-rose-800 uppercase tracking-wider border-b border-rose-100 pb-2">
                    Deductions & Statutory Taxes
                  </h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between text-slate-600">
                      <span>Provident Fund (Employee PF 12%)</span>
                      <span className="font-semibold text-slate-900">{formatInr(activeRecord.employeePf)}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Income Tax Deducted (TDS Sec 192)</span>
                      <span className="font-semibold text-rose-600">{formatInr(activeRecord.tdsDeducted)}</span>
                    </div>
                    <div className="flex justify-between text-slate-600">
                      <span>Professional Tax (PT)</span>
                      <span className="font-semibold text-slate-900">{formatInr(activeRecord.professionalTax)}</span>
                    </div>
                    {activeRecord.esi > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>ESI</span>
                        <span className="font-semibold text-slate-900">{formatInr(activeRecord.esi)}</span>
                      </div>
                    )}
                    {activeRecord.otherDeductions > 0 && (
                      <div className="flex justify-between text-slate-600">
                        <span>Other Recurring Deductions</span>
                        <span className="font-semibold text-slate-900">{formatInr(activeRecord.otherDeductions)}</span>
                      </div>
                    )}
                  </div>
                  <div className="pt-3 border-t border-slate-200 flex justify-between font-bold text-slate-900">
                    <span>Total Deductions</span>
                    <span className="text-rose-600">{formatInr(activeRecord.totalDeductions)}</span>
                  </div>
                </div>
              </div>

              {/* Net Payout Banner */}
              <div className="bg-slate-900 text-white p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div>
                  <span className="text-xs text-slate-400">
                    Net Take-Home Pay for {activeMonthInfo.name} (Credited to {employee.bankName}):
                  </span>
                  <div className="text-xl font-black text-emerald-400">{formatInr(activeRecord.netPay)}</div>
                </div>
                <button
                  type="button"
                  onClick={() => onViewPayslip(activeRecord)}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  <Download className="h-4 w-4" />
                  Print Official Payslip
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Subtab 2: AI Smart Tax Optimizer & Advisor */}
      {subTab === 'ai-advisor' && (
        <SmartTaxAdvisorTab
          employee={employee}
          declaration={declaration}
          taxConfig={taxConfig}
          currentMonth={selectedMonth}
          onEditDeclaration={() => declaration && onEditDeclaration(declaration)}
        />
      )}

      {/* Subtab 3: Dual Regime Tax Simulator (Strictly scoped to this employee) */}
      {subTab === 'simulator' && (
        <div className="space-y-4">
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 text-xs text-indigo-900 flex items-start gap-2">
            <Scale className="h-4 w-4 text-indigo-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block">Personal Tax Comparison: Old vs New Tax Regime (AY 2026–27)</span>
              <p className="text-indigo-800 mt-0.5 leading-relaxed">
                This simulator is locked to your personal salary structure, investments, and declarations.
                Compare your exact tax liabilities side-by-side to verify if switching tax regimes before payroll lock would increase your take-home pay.
              </p>
            </div>
          </div>

          <TaxSimulatorTab
            employees={[employee]}
            declarations={declaration ? [declaration] : []}
            taxConfig={taxConfig}
            currentMonth={selectedMonth}
            selectedEmployeeCode={employee.employeeCode}
            onSelectEmployee={() => {}}
          />
        </div>
      )}

      {/* Subtab 3: Tax Declarations Form */}
      {subTab === 'declaration' && declaration && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-6 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Income Tax Declarations & Investment Proofs (FY {declaration.financialYear})
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Regime Opted:{' '}
                <strong className="text-indigo-700 font-bold">{declaration.regimeDeclared} Regime</strong> • Status:{' '}
                <span
                  className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                    declaration.proofStatus === 'Verified'
                      ? 'bg-emerald-50 text-emerald-700'
                      : declaration.proofStatus === 'Submitted'
                      ? 'bg-blue-50 text-blue-700'
                      : 'bg-amber-50 text-amber-700'
                  }`}
                >
                  {declaration.proofStatus}
                </span>
              </p>
            </div>

            <button
              type="button"
              onClick={() => onEditDeclaration(declaration)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-colors shadow-xs self-start cursor-pointer"
            >
              <Edit3 className="h-4 w-4" />
              <span>Update My Declarations</span>
            </button>
          </div>

          {/* Quick Declarations Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Section 80C Deductions
              </span>
              <div className="text-lg font-black text-slate-900 mt-1">
                {formatInr(
                  declaration.ppf +
                    declaration.licPremium +
                    declaration.elssMutualFund +
                    declaration.housingLoanPrincipal +
                    declaration.tuitionFees +
                    declaration.taxSaverFd5yr +
                    declaration.other80C
                )}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">Statutory cap: ₹1,50,000 (Old Regime)</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                HRA Rent Paid (Annual)
              </span>
              <div className="text-lg font-black text-slate-900 mt-1">
                {formatInr(declaration.rentPaidAnnual)}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">
                {declaration.rentedCityMetro === 'Y' ? 'Metro (50% Basic)' : 'Non-Metro (40% Basic)'}
              </span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Section 80D Mediclaim
              </span>
              <div className="text-lg font-black text-slate-900 mt-1">
                {formatInr(declaration.mediclaimSelfFamily + declaration.mediclaimParents)}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">Self, Family & Parents</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                NPS u/s 80CCD(1B)
              </span>
              <div className="text-lg font-black text-slate-900 mt-1">
                {formatInr(declaration.npsSelf80CCD1B)}
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block">Additional ₹50,000 deduction</span>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
            <span className="text-slate-600">
              Declaration submitted on <strong>{declaration.declarationDate}</strong>.
            </span>
            <button
              type="button"
              onClick={() => onEditDeclaration(declaration)}
              className="text-indigo-600 hover:text-indigo-800 font-bold"
            >
              Modify Declaration Values →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

