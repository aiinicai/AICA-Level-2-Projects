import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Search,
} from 'lucide-react';
import { DischargeMonitorRow } from '../types';
import { formatIndianDate, formatINR } from '../utils/formatters';

interface DischargeMonitorViewProps {
  rows: DischargeMonitorRow[];
  onSelectEncounter: (encounterId: string) => void;
}

export const DischargeMonitorView: React.FC<DischargeMonitorViewProps> = ({
  rows,
  onSelectEncounter,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDept, setSelectedDept] = useState('ALL');
  const [selectedPayer, setSelectedPayer] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [hasExceptionFilter, setHasExceptionFilter] = useState<'ALL' | 'YES' | 'NO'>('ALL');

  // Unique departments and payers for dropdowns
  const departments = Array.from(new Set(rows.map((r) => r.Department))).sort();
  const payers = Array.from(new Set(rows.map((r) => r.Payer_Type))).sort();

  const filteredRows = rows.filter((r) => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const match =
        r.Encounter_ID.toLowerCase().includes(q) ||
        r.Department.toLowerCase().includes(q) ||
        r.Ward.toLowerCase().includes(q) ||
        r.Payer_Type.toLowerCase().includes(q);
      if (!match) return false;
    }
    if (selectedDept !== 'ALL' && r.Department !== selectedDept) return false;
    if (selectedPayer !== 'ALL' && r.Payer_Type !== selectedPayer) return false;
    if (selectedStatus !== 'ALL' && r.Discharge_Status !== selectedStatus) return false;
    if (hasExceptionFilter === 'YES' && r.Exception_Count === 0) return false;
    if (hasExceptionFilter === 'NO' && r.Exception_Count > 0) return false;
    return true;
  }).filter((r, idx, arr) => arr.findIndex((x) => x.Encounter_ID === r.Encounter_ID) === idx);

  return (
    <div className="space-y-4">
      {/* Header and Filter Controls */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              Financial Review Queue &amp; Encounter Ledger Audit
            </h2>
            <p className="text-xs text-slate-500">
              Correlates billing completeness, TPA claims clearance, and uncollected receivables for active and discharged encounters.
            </p>
          </div>
          <div className="text-xs text-slate-500">
            Showing <span className="font-bold text-slate-900">{filteredRows.length}</span> of {rows.length} encounters
          </div>
        </div>

        {/* Filter Inputs Grid */}
        <div className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search encounter, ward..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:border-teal-600 focus:outline-none"
            />
          </div>

          {/* Department Filter */}
          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="ALL">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>

          {/* Payer Filter */}
          <select
            value={selectedPayer}
            onChange={(e) => setSelectedPayer(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="ALL">All Payers</option>
            {payers.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>

          {/* Discharge Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="ALL">All Discharge Statuses</option>
            <option value="Discharged">Discharged</option>
            <option value="Admitted">Admitted</option>
          </select>

          {/* Exception Toggle */}
          <select
            value={hasExceptionFilter}
            onChange={(e) => setHasExceptionFilter(e.target.value as 'ALL' | 'YES' | 'NO')}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-teal-600 focus:outline-none cursor-pointer"
          >
            <option value="ALL">Exceptions: All Encounters</option>
            <option value="YES">With Exceptions Only</option>
            <option value="NO">Clean Only (No Exceptions)</option>
          </select>
        </div>
      </div>

      {/* Monitor Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="py-3 px-3.5 font-semibold">Encounter</th>
                <th className="py-3 px-3.5 font-semibold">Dept / Ward</th>
                <th className="py-3 px-3.5 font-semibold">Payer Type</th>
                <th className="py-3 px-3.5 font-semibold">Discharge</th>
                <th className="py-3 px-3.5 font-semibold text-right">Billed Amount</th>
                <th className="py-3 px-3.5 font-semibold">Billing Completeness</th>
                <th className="py-3 px-3.5 font-semibold">TPA Clearance</th>
                <th className="py-3 px-3.5 font-semibold">Collection Status</th>
                <th className="py-3 px-3.5 font-semibold text-center">Exception Risk</th>
                <th className="py-3 px-3.5 font-semibold text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-xs text-slate-400">
                    No encounters matched current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row, idx) => {
                  const hasCrit = row.Highest_Severity === 'CRITICAL';
                  const hasHigh = row.Highest_Severity === 'HIGH';

                  return (
                    <tr
                      key={`${row.Encounter_ID}-${idx}`}
                      onClick={() => onSelectEncounter(row.Encounter_ID)}
                      className="hover:bg-slate-50 transition cursor-pointer"
                    >
                      {/* Encounter ID */}
                      <td className="py-3 px-3.5 font-mono font-bold text-teal-800">
                        {row.Encounter_ID}
                      </td>

                      {/* Dept / Ward */}
                      <td className="py-3 px-3.5">
                        <div className="font-semibold text-slate-900">{row.Department}</div>
                        <div className="text-[11px] text-slate-500">{row.Ward}</div>
                      </td>

                      {/* Payer Type */}
                      <td className="py-3 px-3.5 text-slate-700">
                        {row.Payer_Type}
                      </td>

                      {/* Discharge Status */}
                      <td className="py-3 px-3.5">
                        <span
                          className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            row.Discharge_Status === 'Discharged'
                              ? 'bg-slate-100 text-slate-800 border border-slate-200'
                              : 'bg-teal-50 text-teal-800 border border-teal-200'
                          }`}
                        >
                          {row.Discharge_Status}
                        </span>
                        {row.Discharge_Date && (
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            {formatIndianDate(row.Discharge_Date)}
                          </div>
                        )}
                      </td>

                      {/* Bill Amount */}
                      <td className="py-3 px-3.5 text-right font-semibold text-slate-900">
                        {formatINR(row.Billed_Amount)}
                        {row.Expected_Amount !== row.Billed_Amount && (
                          <div className="text-[10px] text-slate-500 font-normal">
                            Exp: {formatINR(row.Expected_Amount)}
                          </div>
                        )}
                      </td>

                      {/* Billing Completeness */}
                      <td className="py-3 px-3.5">
                        <span
                          className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-medium ${
                            row.Billing_Completeness === 'Complete'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : row.Billing_Completeness === 'Provisional Only'
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {row.Billing_Completeness}
                        </span>
                      </td>

                      {/* TPA Status */}
                      <td className="py-3 px-3.5">
                        <span
                          className={`inline-flex rounded px-2 py-0.5 text-[10px] font-medium ${
                            row.TPA_Status === 'Approved'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : row.TPA_Status === 'Partially Approved'
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : row.TPA_Status === 'Pending'
                              ? 'bg-sky-50 text-sky-800 border border-sky-200'
                              : row.TPA_Status === 'Rejected'
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : 'text-slate-400'
                          }`}
                        >
                          {row.TPA_Status}
                        </span>
                      </td>

                      {/* Collection Status */}
                      <td className="py-3 px-3.5">
                        <span
                          className={`inline-flex rounded px-2 py-0.5 text-[10px] font-medium ${
                            row.Collection_Status === 'Fully Collected'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : row.Collection_Status === 'Overdue >30d'
                              ? 'bg-rose-50 text-rose-700 border border-rose-200 font-semibold'
                              : 'bg-slate-100 text-slate-700 border border-slate-200'
                          }`}
                        >
                          {row.Collection_Status}
                        </span>
                      </td>

                      {/* Exception Status */}
                      <td className="py-3 px-3.5 text-center">
                        {row.Exception_Count === 0 ? (
                          <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-semibold">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Billing Cleared &amp; Verified
                          </span>
                        ) : (
                          <div className="flex flex-col items-center">
                            <span
                              className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold ${
                                hasCrit
                                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                  : hasHigh
                                  ? 'bg-amber-50 text-amber-800 border border-amber-200'
                                  : 'bg-slate-100 text-slate-700 border border-slate-200'
                              }`}
                            >
                              <AlertTriangle className="h-3 w-3" />
                              {row.Exception_Count} Exception{row.Exception_Count > 1 ? 's' : ''}
                            </span>
                            <span className="text-[10px] font-semibold text-amber-900 mt-0.5">
                              {formatINR(row.Total_Exposure)} impact
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-3 px-3.5 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEncounter(row.Encounter_ID);
                          }}
                          className="inline-flex items-center gap-1 rounded bg-slate-100 hover:bg-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-800 border border-slate-200 transition cursor-pointer"
                        >
                          <span>Financials</span>
                          <ExternalLink className="h-3 w-3 text-slate-500" />
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
