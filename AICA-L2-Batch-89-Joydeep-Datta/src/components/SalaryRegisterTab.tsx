import React, { useState } from 'react';
import {
  Download,
  FileText,
  TrendingUp,
  CreditCard,
  Users,
  Search,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { PayrollRunSummary, MonthlySalaryRecord } from '../types/payroll';
import { exportSalaryRegisterExcel } from '../utils/excelHandler';

interface SalaryRegisterTabProps {
  payrollSummary: PayrollRunSummary;
  onViewPayslip: (record: MonthlySalaryRecord) => void;
  onViewTaxBreakdown: (employeeCode: string) => void;
  onRerunPayroll: () => void;
}

export const SalaryRegisterTab: React.FC<SalaryRegisterTabProps> = ({
  payrollSummary,
  onViewPayslip,
  onViewTaxBreakdown,
  onRerunPayroll,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('ALL');

  const departments = ['ALL', ...Array.from(new Set(payrollSummary.records.map((r) => r.department).filter(Boolean)))];

  const filteredRecords = payrollSummary.records.filter((r) => {
    const matchesSearch =
      r.employeeName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.employeeCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.pan.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDept = departmentFilter === 'ALL' || r.department === departmentFilter;
    return matchesSearch && matchesDept;
  });

  return (
    <div className="space-y-6">
      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Employees</span>
            <Users className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{payrollSummary.headcount}</span>
            <span className="text-xs text-slate-500">processed</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Total payable in {payrollSummary.monthLabel}</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Gross Earned</span>
            <TrendingUp className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              ₹{payrollSummary.totalGross.toLocaleString('en-IN')}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Calendar days prorated</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total TDS Deducted</span>
            <CreditCard className="h-4 w-4 text-amber-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              ₹{payrollSummary.totalTds.toLocaleString('en-IN')}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Monthly tax spreading</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total PF Deductions</span>
            <ShieldIcon className="h-4 w-4 text-blue-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              ₹{payrollSummary.totalPf.toLocaleString('en-IN')}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Employee 12% statutory</p>
        </div>

        <div className="bg-indigo-900 text-white border border-indigo-800 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-200 uppercase tracking-wider">Net Bank Payout</span>
            <CheckCircle2 className="h-4 w-4 text-indigo-300" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">
              ₹{payrollSummary.totalNetPayout.toLocaleString('en-IN')}
            </span>
          </div>
          <p className="mt-1 text-xs text-indigo-300">Ready for NEFT / Bank upload</p>
        </div>
      </div>

      {/* Action Bar & Filters */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative min-w-[240px]">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, code or PAN..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white"
            />
          </div>

          {/* Department Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium">Department:</span>
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {departments.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={onRerunPayroll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Refresh Calculations
          </button>

          <button
            onClick={() => exportSalaryRegisterExcel(payrollSummary)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-xs"
          >
            <Download className="h-3.5 w-3.5" />
            Export Salary Sheet (.xlsx)
          </button>
        </div>
      </div>

      {/* Salary Register Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Salary Register — {payrollSummary.monthLabel}
            </h2>
            <p className="text-xs text-slate-500">
              Showing {filteredRecords.length} records. Calendar days proration and dual tax regime TDS spreading.
            </p>
          </div>
          <span className="text-xs font-medium text-slate-500">Professional Tax: Exempt (₹0)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700 border-collapse">
            <thead className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Employee</th>
                <th className="py-2.5 px-3">Department</th>
                <th className="py-2.5 px-3 text-center">Days (Pay/Total)</th>
                <th className="py-2.5 px-3 text-right">Basic</th>
                <th className="py-2.5 px-3 text-right">HRA</th>
                <th className="py-2.5 px-3 text-right">Gross Earned</th>
                <th className="py-2.5 px-3 text-right">PF (12%)</th>
                <th className="py-2.5 px-3 text-right">Monthly TDS</th>
                <th className="py-2.5 px-3 text-right font-bold text-slate-900">Net Take-Home</th>
                <th className="py-2.5 px-3 text-center">Regime</th>
                <th className="py-2.5 px-3">Tax Recommendation</th>
                <th className="py-2.5 px-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan={12} className="py-8 text-center text-slate-400">
                    No employees matching the search filters.
                  </td>
                </tr>
              ) : (
                filteredRecords.map((r) => (
                  <tr key={r.employeeCode} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900">{r.employeeName}</div>
                      <div className="text-[11px] text-slate-500">
                        {r.employeeCode} • {r.pan}
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <div>{r.department || '—'}</div>
                      <div className="text-[11px] text-slate-400">{r.designation}</div>
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`inline-block font-mono px-2 py-0.5 rounded text-[11px] font-medium ${
                          r.payableDays < r.totalDaysInMonth
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {r.payableDays} / {r.totalDaysInMonth}
                      </span>
                      {r.payableDays < r.totalDaysInMonth && (
                        <span className="block text-[10px] text-amber-600">Prorated</span>
                      )}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono">
                      ₹{r.basicEarned.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono">
                      ₹{r.hraEarned.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono font-medium text-slate-900">
                      ₹{r.grossEarned.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                      ₹{r.employeePf.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono text-amber-700 font-semibold">
                      ₹{r.tdsDeducted.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-700 bg-emerald-50/40">
                      ₹{r.netPay.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          r.regimeApplied === 'New'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-purple-100 text-purple-800'
                        }`}
                      >
                        {r.regimeApplied}
                      </span>
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1 text-[11px] text-slate-700 font-medium">
                        {r.regimeSavingRecommendation.includes('saves') ? (
                          <span className="text-emerald-700 flex items-center gap-1">
                            <TrendingUp className="h-3 w-3 shrink-0" />
                            {r.regimeSavingRecommendation}
                          </span>
                        ) : (
                          <span className="text-slate-500">{r.regimeSavingRecommendation}</span>
                        )}
                      </div>
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => onViewPayslip(r)}
                          title="Generate printable Payslip"
                          className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                        >
                          <FileText className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => onViewTaxBreakdown(r.employeeCode)}
                          title="View Dual-Regime Tax Computation"
                          className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            {filteredRecords.length > 0 && (
              <tfoot className="bg-slate-50 font-bold text-slate-900 border-t-2 border-slate-300">
                <tr>
                  <td colSpan={3} className="py-2.5 px-3">
                    TOTAL ({filteredRecords.length} employees)
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono">
                    ₹{filteredRecords.reduce((sum, r) => sum + r.basicEarned, 0).toLocaleString('en-IN')}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono">
                    ₹{filteredRecords.reduce((sum, r) => sum + r.hraEarned, 0).toLocaleString('en-IN')}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono">
                    ₹{filteredRecords.reduce((sum, r) => sum + r.grossEarned, 0).toLocaleString('en-IN')}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono">
                    ₹{filteredRecords.reduce((sum, r) => sum + r.employeePf, 0).toLocaleString('en-IN')}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-amber-800">
                    ₹{filteredRecords.reduce((sum, r) => sum + r.tdsDeducted, 0).toLocaleString('en-IN')}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-emerald-800 bg-emerald-100/40">
                    ₹{filteredRecords.reduce((sum, r) => sum + r.netPay, 0).toLocaleString('en-IN')}
                  </td>
                  <td colSpan={3}></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>
    </div>
  );
};

function ShieldIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
      />
    </svg>
  );
}
