import React, { useState } from 'react';
import {
  Download,
  Upload,
  UserPlus,
  Search,
  Building,
  Calendar,
  CheckCircle,
  AlertTriangle,
  FileSpreadsheet,
  Edit2,
} from 'lucide-react';
import { EmployeeMaster } from '../types/payroll';
import { exportEmployeeMasterExcel } from '../utils/excelHandler';

interface EmployeeMasterTabProps {
  employees: EmployeeMaster[];
  onAddEmployee: () => void;
  onEditEmployee: (emp: EmployeeMaster) => void;
  onUploadExcel: () => void;
}

export const EmployeeMasterTab: React.FC<EmployeeMasterTabProps> = ({
  employees,
  onAddEmployee,
  onEditEmployee,
  onUploadExcel,
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [regimeFilter, setRegimeFilter] = useState('ALL');

  const filtered = employees.filter((emp) => {
    const matchesSearch =
      emp.employeeName.toLowerCase().includes(search.toLowerCase()) ||
      emp.employeeCode.toLowerCase().includes(search.toLowerCase()) ||
      emp.pan.toLowerCase().includes(search.toLowerCase()) ||
      emp.department.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || emp.employmentStatus === statusFilter;
    const matchesRegime = regimeFilter === 'ALL' || emp.taxRegimeOpted === regimeFilter;
    return matchesSearch && matchesStatus && matchesRegime;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Active':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'New Joiner':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Resigned':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'Exited':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative min-w-[240px]">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, code, PAN, department..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="Active">Active</option>
              <option value="New Joiner">New Joiner</option>
              <option value="Resigned">Resigned</option>
              <option value="Exited">Exited</option>
              <option value="On Leave (LWP)">On Leave (LWP)</option>
            </select>
          </div>

          {/* Regime Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium">Regime:</span>
            <select
              value={regimeFilter}
              onChange={(e) => setRegimeFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="ALL">All Regimes</option>
              <option value="New">New Regime</option>
              <option value="Old">Old Regime</option>
            </select>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => exportEmployeeMasterExcel(employees)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            title="Download 01_Employee_Master.xlsx template"
          >
            <Download className="h-3.5 w-3.5 text-slate-600" />
            Download Master (.xlsx)
          </button>

          <button
            onClick={onUploadExcel}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors"
          >
            <Upload className="h-3.5 w-3.5 text-indigo-600" />
            Upload Master (.xlsx)
          </button>

          <button
            onClick={onAddEmployee}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-xs"
          >
            <UserPlus className="h-3.5 w-3.5" />
            Add Employee
          </button>
        </div>
      </div>

      {/* Employee Master Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Employee Master Registry</h2>
            <p className="text-xs text-slate-500">
              {filtered.length} employees found • Primary key: Employee_Code
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700 border-collapse">
            <thead className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Emp Code</th>
                <th className="py-2.5 px-3">Full Name & PAN</th>
                <th className="py-2.5 px-3">Role & Dept</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Dates (DOJ / DOL)</th>
                <th className="py-2.5 px-3 text-right">Annual CTC</th>
                <th className="py-2.5 px-3 text-right">Basic Monthly</th>
                <th className="py-2.5 px-3 text-center">PF Setup</th>
                <th className="py-2.5 px-3 text-center">Opted Regime</th>
                <th className="py-2.5 px-3">Effective Revision</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-8 text-center text-slate-400">
                    No employees matching filter criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((emp) => (
                  <tr key={emp.employeeCode} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-bold text-indigo-700">
                      {emp.employeeCode}
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-slate-900">{emp.employeeName}</div>
                      <div className="text-[11px] text-slate-500 font-mono">
                        {emp.pan} • {emp.gender}
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <div>{emp.designation}</div>
                      <div className="text-[11px] text-slate-400">
                        {emp.department} • {emp.locationCity} ({emp.metroFlag === 'Y' ? 'Metro' : 'Non-Metro'})
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getStatusBadge(
                          emp.employmentStatus
                        )}`}
                      >
                        {emp.employmentStatus}
                      </span>
                    </td>

                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      <div>DOJ: {emp.dateOfJoining}</div>
                      {emp.dateOfLeaving && (
                        <div className="text-rose-600 font-medium">DOL: {emp.dateOfLeaving}</div>
                      )}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono font-medium text-slate-900">
                      ₹{emp.annualCtc.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                      ₹{emp.basicMonthly.toLocaleString('en-IN')}
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      <span className="text-[11px] font-medium">
                        {emp.pfApplicable === 'Y' ? (
                          <span className="text-emerald-700">
                            12%{emp.pfWageCeilingApplied === 'Y' ? ' (Capped ₹15k)' : ' (Actual)'}
                          </span>
                        ) : (
                          <span className="text-slate-400">Exempt</span>
                        )}
                      </span>
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          emp.taxRegimeOpted === 'New'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-purple-100 text-purple-800'
                        }`}
                      >
                        {emp.taxRegimeOpted}
                      </span>
                    </td>

                    <td className="py-2.5 px-3 text-[11px]">
                      <div className="font-medium text-slate-800">{emp.revisionReason}</div>
                      <div className="text-slate-400">{emp.salaryEffectiveFrom}</div>
                    </td>

                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => onEditEmployee(emp)}
                        className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                        title="Edit employee record"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
