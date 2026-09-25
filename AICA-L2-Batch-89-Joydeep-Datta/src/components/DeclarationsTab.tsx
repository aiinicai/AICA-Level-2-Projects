import React, { useState } from 'react';
import {
  Download,
  Upload,
  Search,
  CheckCircle,
  Clock,
  XCircle,
  FileCheck2,
  Edit2,
  AlertCircle,
} from 'lucide-react';
import { EmployeeDeclaration, EmployeeMaster } from '../types/payroll';
import { exportEmployeeDeclarationExcel } from '../utils/excelHandler';

interface DeclarationsTabProps {
  declarations: EmployeeDeclaration[];
  employees: EmployeeMaster[];
  selectedFy: string;
  onEditDeclaration: (decl: EmployeeDeclaration) => void;
  onUploadExcel: () => void;
}

export const DeclarationsTab: React.FC<DeclarationsTabProps> = ({
  declarations,
  employees,
  selectedFy,
  onEditDeclaration,
  onUploadExcel,
}) => {
  const [search, setSearch] = useState('');
  const [regimeFilter, setRegimeFilter] = useState('ALL');
  const [proofFilter, setProofFilter] = useState('ALL');

  const filtered = declarations.filter((d) => {
    const emp = employees.find((e) => e.employeeCode === d.employeeCode);
    const name = d.employeeName || emp?.employeeName || '';
    const matchesSearch =
      name.toLowerCase().includes(search.toLowerCase()) ||
      d.employeeCode.toLowerCase().includes(search.toLowerCase()) ||
      (d.pan && d.pan.toLowerCase().includes(search.toLowerCase()));
    const matchesRegime = regimeFilter === 'ALL' || d.regimeDeclared === regimeFilter;
    const matchesProof = proofFilter === 'ALL' || d.proofStatus === proofFilter;
    return matchesSearch && matchesRegime && matchesProof;
  });

  const countNewRegime = declarations.filter((d) => d.regimeDeclared === 'New').length;
  const countOldRegime = declarations.filter((d) => d.regimeDeclared === 'Old').length;
  const countVerified = declarations.filter((d) => d.proofStatus === 'Verified').length;
  const countPending = declarations.filter((d) => d.proofStatus === 'Pending').length;

  const getProofBadge = (status: string) => {
    switch (status) {
      case 'Verified':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'Submitted':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Pending':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'Partially Rejected':
      case 'Rejected':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">New Tax Regime</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-blue-700">{countNewRegime}</span>
            <span className="text-xs text-slate-500">employees</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Default regime u/s 115BAC</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Old Tax Regime</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-purple-700">{countOldRegime}</span>
            <span className="text-xs text-slate-500">employees</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Claiming 80C, HRA, 24(b)</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Verified Proofs</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-700">{countVerified}</span>
            <span className="text-xs text-slate-500">employees</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Actual proof receipts accepted</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending Proofs</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-700">{countPending}</span>
            <span className="text-xs text-slate-500">employees</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Proposed declarations active</p>
        </div>
      </div>

      {/* Header Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative min-w-[240px]">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search declarations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white"
            />
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

          {/* Proof Status */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium">Proof:</span>
            <select
              value={proofFilter}
              onChange={(e) => setProofFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="Verified">Verified</option>
              <option value="Pending">Pending</option>
              <option value="Submitted">Submitted</option>
              <option value="Rejected">Rejected</option>
            </select>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => exportEmployeeDeclarationExcel(declarations)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            title="Download 02_Employee_Declaration.xlsx template"
          >
            <Download className="h-3.5 w-3.5 text-slate-600" />
            Download Template (.xlsx)
          </button>

          <button
            onClick={onUploadExcel}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors shadow-xs"
          >
            <Upload className="h-3.5 w-3.5 text-indigo-600" />
            Upload Declarations (.xlsx)
          </button>
        </div>
      </div>

      {/* Declarations Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Tax Deductions & Regime Declarations — FY {selectedFy}
            </h2>
            <p className="text-xs text-slate-500">
              Declaration regime supersedes master setting. New regime disables HRA and Chapter VI-A deductions.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700 border-collapse">
            <thead className="bg-slate-100/70 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">Employee</th>
                <th className="py-2.5 px-3 text-center">Declared Regime</th>
                <th className="py-2.5 px-3 text-center">Proof Status</th>
                <th className="py-2.5 px-3 text-right">Annual Rent (HRA)</th>
                <th className="py-2.5 px-3 text-right">Sec 80C</th>
                <th className="py-2.5 px-3 text-right">NPS 80CCD(1B)</th>
                <th className="py-2.5 px-3 text-right">Mediclaim 80D</th>
                <th className="py-2.5 px-3 text-right">Home Loan 24(b)</th>
                <th className="py-2.5 px-3 text-right">Prev Employer TDS</th>
                <th className="py-2.5 px-3">Remarks / Verification Note</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-8 text-center text-slate-400">
                    No declarations match filter.
                  </td>
                </tr>
              ) : (
                filtered.map((d) => {
                  const emp = employees.find((e) => e.employeeCode === d.employeeCode);
                  const name = d.employeeName || emp?.employeeName || d.employeeCode;
                  const total80c =
                    d.housingLoanPrincipal +
                    d.ppf +
                    d.licPremium +
                    d.elssMutualFund +
                    d.nsc +
                    d.tuitionFees +
                    d.sukanyaSamriddhi +
                    d.taxSaverFd5yr +
                    d.other80C;

                  const total80d = d.mediclaimSelfFamily + d.mediclaimParents + d.preventiveHealthCheckup;

                  return (
                    <tr key={d.employeeCode} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-slate-900">{name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          {d.employeeCode} • {d.declarationType}
                        </div>
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            d.regimeDeclared === 'New'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-purple-100 text-purple-800'
                          }`}
                        >
                          {d.regimeDeclared}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getProofBadge(
                            d.proofStatus
                          )}`}
                        >
                          {d.proofStatus}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono">
                        {d.rentPaidAnnual > 0 ? (
                          <div>
                            <span className="font-medium text-slate-900">
                              ₹{d.rentPaidAnnual.toLocaleString('en-IN')}
                            </span>
                            {d.landlordPan && (
                              <div className="text-[10px] text-slate-400 font-mono">PAN: {d.landlordPan}</div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono">
                        {total80c > 0 ? (
                          <div>
                            <span className="font-medium text-slate-900">
                              ₹{Math.min(total80c, 150000).toLocaleString('en-IN')}
                            </span>
                            {total80c > 150000 && (
                              <div className="text-[10px] text-amber-600">
                                Declared: ₹{total80c.toLocaleString('en-IN')} (capped)
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono">
                        {d.npsSelf80CCD1B > 0 ? (
                          <span className="font-medium text-slate-900">
                            ₹{Math.min(d.npsSelf80CCD1B, 50000).toLocaleString('en-IN')}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono">
                        {total80d > 0 ? (
                          <div>
                            <span className="font-medium text-slate-900">
                              ₹{total80d.toLocaleString('en-IN')}
                            </span>
                            {d.parentsSeniorCitizen === 'Y' && (
                              <div className="text-[10px] text-emerald-600">Sr Citizen parent</div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono">
                        {d.housingLoanInterestSelfOccupied > 0 ? (
                          <div>
                            <span className="font-medium text-slate-900">
                              ₹{Math.min(d.housingLoanInterestSelfOccupied, 200000).toLocaleString('en-IN')}
                            </span>
                            {d.housingLoanInterestSelfOccupied > 200000 && (
                              <div className="text-[10px] text-amber-600">Max ₹2L setoff</div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono">
                        {d.prevEmployerTdsDeducted > 0 ? (
                          <div>
                            <span className="font-semibold text-emerald-700">
                              ₹{d.prevEmployerTdsDeducted.toLocaleString('en-IN')}
                            </span>
                            <div className="text-[10px] text-slate-400">
                              Gross: ₹{d.prevEmployerGrossSalary.toLocaleString('en-IN')}
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      <td className="py-2.5 px-3 text-[11px] text-slate-600 max-w-xs truncate">
                        {d.remarks || '—'}
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <button
                          onClick={() => onEditDeclaration(d)}
                          className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                          title="Edit declaration"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
