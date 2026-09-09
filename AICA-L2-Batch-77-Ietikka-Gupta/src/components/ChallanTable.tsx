import React, { useState, useMemo } from 'react';
import { 
  Search, 
  Filter, 
  Edit3, 
  Trash2, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  Info,
  Calendar,
  Hash,
  Building,
  ArrowUpDown,
  Download,
  Layers
} from 'lucide-react';
import { ChallanRecord } from '../types';

interface ChallanTableProps {
  records: ChallanRecord[];
  onEditRecord: (record: ChallanRecord) => void;
  onDeleteRecord: (id: string) => void;
}

export const ChallanTable: React.FC<ChallanTableProps> = ({
  records,
  onEditRecord,
  onDeleteRecord,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [fundFilter, setFundFilter] = useState<'ALL' | 'PF' | 'ESI'>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ON_TIME' | 'DELAYED'>('ALL');
  const [sortBy, setSortBy] = useState<'wageMonthKey' | 'actualPaymentDate' | 'employeeContribution' | 'delayDays'>('wageMonthKey');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  const filteredRecords = useMemo(() => {
    return records
      .filter((rec) => {
        // Fund filter
        if (fundFilter !== 'ALL' && rec.fundType !== fundFilter) return false;
        // Status filter
        if (statusFilter !== 'ALL' && rec.status !== statusFilter) return false;
        // Search term
        if (searchTerm.trim() !== '') {
          const q = searchTerm.toLowerCase();
          const matchMonth = rec.wageMonth.toLowerCase().includes(q);
          const matchRef = rec.challanReference.toLowerCase().includes(q);
          const matchEst = rec.establishmentName.toLowerCase().includes(q) || rec.establishmentId.toLowerCase().includes(q);
          const matchType = rec.fundType.toLowerCase().includes(q);
          if (!matchMonth && !matchRef && !matchEst && !matchType) return false;
        }
        return true;
      })
      .sort((a, b) => {
        let valA: any = a[sortBy];
        let valB: any = b[sortBy];
        if (typeof valA === 'string') {
          valA = valA.toLowerCase();
          valB = (valB || '').toLowerCase();
        }
        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
  }, [records, fundFilter, statusFilter, searchTerm, sortBy, sortOrder]);

  const toggleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const pfCount = records.filter(r => r.fundType === 'PF').length;
  const esiCount = records.filter(r => r.fundType === 'ESI').length;
  const delayedCount = records.filter(r => r.status === 'DELAYED').length;
  const onTimeCount = records.filter(r => r.status === 'ON_TIME').length;

  if (records.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center shadow-xs">
        <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600 mx-auto mb-3">
          <Calendar className="w-7 h-7" />
        </div>
        <h3 className="text-base font-bold text-slate-800">No Challan Records Available</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          Upload PDF challans above or load the full FY 2024-25 audit pack to explore and verify Section 36(1)(va) compliance.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      
      {/* Table Top Controls & Bento Filter Tabs */}
      <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-50/60 space-y-3">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          
          {/* Fund Type Bento Tabs */}
          <div className="flex items-center gap-1 bg-slate-200/80 p-1 rounded-xl text-xs font-medium self-start shadow-2xs">
            <button
              onClick={() => setFundFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer ${
                fundFilter === 'ALL' ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Funds ({records.length})
            </button>
            <button
              onClick={() => setFundFilter('PF')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                fundFilter === 'PF' ? 'bg-indigo-600 text-white shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-200"></span>
              PF Only ({pfCount})
            </button>
            <button
              onClick={() => setFundFilter('ESI')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                fundFilter === 'ESI' ? 'bg-indigo-600 text-white shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-200"></span>
              ESI Only ({esiCount})
            </button>
          </div>

          {/* Search Box */}
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search month, TRRN, or Est ID..."
              className="w-full pl-9 pr-3.5 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-2xs"
            />
          </div>

        </div>

        {/* Secondary Filter Row: Status Badges */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-bold text-[11px] uppercase tracking-wider">Compliance:</span>
            <button
              onClick={() => setStatusFilter('ALL')}
              className={`px-3 py-1 rounded-xl text-xs transition cursor-pointer ${
                statusFilter === 'ALL' 
                  ? 'bg-slate-900 text-white font-bold' 
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              All ({records.length})
            </button>
            <button
              onClick={() => setStatusFilter('ON_TIME')}
              className={`px-3 py-1 rounded-xl text-xs transition cursor-pointer flex items-center gap-1.5 ${
                statusFilter === 'ON_TIME' 
                  ? 'bg-emerald-600 text-white font-bold shadow-xs' 
                  : 'bg-emerald-50 border border-emerald-200 text-emerald-800 hover:bg-emerald-100'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              On Time ({onTimeCount})
            </button>
            <button
              onClick={() => setStatusFilter('DELAYED')}
              className={`px-3 py-1 rounded-xl text-xs transition cursor-pointer flex items-center gap-1.5 ${
                statusFilter === 'DELAYED' 
                  ? 'bg-rose-600 text-white font-bold shadow-xs' 
                  : 'bg-rose-50 border border-rose-200 text-rose-800 hover:bg-rose-100'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Delayed / Disallowed ({delayedCount})
            </button>
          </div>

          <div className="text-xs text-slate-500 font-medium">
            Showing <strong className="text-slate-900 font-bold">{filteredRecords.length}</strong> of {records.length} challans
          </div>
        </div>

      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200 uppercase tracking-wider text-[11px]">
            <tr>
              <th className="py-3.5 px-4 w-12 text-center">#</th>
              <th className="py-3.5 px-4">Fund & Est. ID</th>
              <th 
                onClick={() => toggleSort('wageMonthKey')} 
                className="py-3.5 px-4 cursor-pointer hover:bg-slate-200 transition"
              >
                <div className="flex items-center gap-1">
                  <span>Wage Month</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              <th className="py-3.5 px-4">Statutory Due Date</th>
              <th 
                onClick={() => toggleSort('actualPaymentDate')} 
                className="py-3.5 px-4 cursor-pointer hover:bg-slate-200 transition"
              >
                <div className="flex items-center gap-1">
                  <span>Payment Date</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              <th className="py-3.5 px-4">TRRN / Ref</th>
              <th 
                onClick={() => toggleSort('employeeContribution')} 
                className="py-3.5 px-4 text-right cursor-pointer hover:bg-slate-200 transition"
              >
                <div className="flex items-center justify-end gap-1">
                  <span>Employee Share (₹)</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              <th className="py-3.5 px-4 text-right">Total Paid (₹)</th>
              <th 
                onClick={() => toggleSort('delayDays')} 
                className="py-3.5 px-4 text-center cursor-pointer hover:bg-slate-200 transition"
              >
                <div className="flex items-center justify-center gap-1">
                  <span>Status</span>
                  <ArrowUpDown className="w-3 h-3 text-slate-400" />
                </div>
              </th>
              <th className="py-3.5 px-4 text-right text-rose-800">36(1)(va) Disallowance</th>
              <th className="py-3.5 px-4 text-center w-20">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {filteredRecords.map((rec, index) => {
              const isDelayed = rec.status === 'DELAYED';

              return (
                <tr 
                  key={rec.id} 
                  className={`hover:bg-slate-50 transition ${
                    isDelayed ? 'bg-rose-50/30' : ''
                  }`}
                >
                  {/* S.No */}
                  <td className="py-3 px-4 text-center text-slate-500 font-mono">
                    {index + 1}
                  </td>

                  {/* Fund Type & Est Code */}
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase ${
                        rec.fundType === 'PF' 
                          ? 'bg-indigo-100 text-indigo-800 border border-indigo-200' 
                          : 'bg-sky-100 text-sky-800 border border-sky-200'
                      }`}>
                        {rec.fundType}
                      </span>
                      <div>
                        <div className="font-bold text-slate-900 truncate max-w-[140px]" title={rec.establishmentName}>
                          {rec.establishmentName}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          {rec.establishmentId}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Wage Month */}
                  <td className="py-3 px-4 font-bold text-slate-900 whitespace-nowrap">
                    {rec.wageMonth}
                  </td>

                  {/* Statutory Due Date */}
                  <td className="py-3 px-4 font-mono text-slate-700 whitespace-nowrap">
                    <span className="bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                      {rec.statutoryDueDate}
                    </span>
                  </td>

                  {/* Actual Payment Date */}
                  <td className="py-3 px-4 font-mono whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded-md font-bold ${
                      isDelayed 
                        ? 'bg-rose-100 text-rose-800 border border-rose-200' 
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}>
                      {rec.actualPaymentDate}
                    </span>
                  </td>

                  {/* Reference / TRRN */}
                  <td className="py-3 px-4 font-mono text-slate-600 text-[11px] whitespace-nowrap">
                    {rec.challanReference}
                  </td>

                  {/* Employee Contribution */}
                  <td className="py-3 px-4 text-right font-black text-slate-900 whitespace-nowrap">
                    ₹ {rec.employeeContribution.toLocaleString('en-IN')}
                  </td>

                  {/* Total Challan Amount */}
                  <td className="py-3 px-4 text-right text-slate-700 font-mono whitespace-nowrap">
                    ₹ {rec.totalChallanAmount.toLocaleString('en-IN')}
                  </td>

                  {/* Compliance Status Badge */}
                  <td className="py-3 px-4 text-center whitespace-nowrap">
                    {isDelayed ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800 border border-rose-200">
                        <Clock className="w-3 h-3 text-rose-600" />
                        {rec.delayDays} day(s) late
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        On Time
                      </span>
                    )}
                  </td>

                  {/* Disallowance Amount */}
                  <td className="py-3 px-4 text-right font-black whitespace-nowrap">
                    {rec.disallowableAmount > 0 ? (
                      <span className="text-rose-700 bg-rose-100/70 px-2 py-0.5 rounded-md border border-rose-200">
                        ₹ {rec.disallowableAmount.toLocaleString('en-IN')}
                      </span>
                    ) : (
                      <span className="text-slate-400 font-normal">NIL</span>
                    )}
                  </td>

                  {/* Action Buttons */}
                  <td className="py-3 px-4 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => onEditRecord(rec)}
                        className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition cursor-pointer"
                        title="Edit Record"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onDeleteRecord(rec.id)}
                        className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
                        title="Delete Record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>

                </tr>
              );
            })}
          </tbody>
          
          {/* Table Footer Totals */}
          <tfoot className="bg-slate-100 border-t-2 border-slate-300 font-bold text-slate-900 text-xs">
            <tr>
              <td colSpan={6} className="py-3.5 px-4 text-right uppercase tracking-wider">
                Total for Filtered Records ({filteredRecords.length}):
              </td>
              <td className="py-3.5 px-4 text-right font-mono font-black">
                ₹ {filteredRecords.reduce((s, r) => s + r.employeeContribution, 0).toLocaleString('en-IN')}
              </td>
              <td className="py-3.5 px-4 text-right font-mono font-black">
                ₹ {filteredRecords.reduce((s, r) => s + r.totalChallanAmount, 0).toLocaleString('en-IN')}
              </td>
              <td className="py-3.5 px-4 text-center">
                {filteredRecords.filter(r => r.status === 'DELAYED').length} delayed
              </td>
              <td className="py-3.5 px-4 text-right text-rose-700 font-mono font-black">
                ₹ {filteredRecords.reduce((s, r) => s + r.disallowableAmount, 0).toLocaleString('en-IN')}
              </td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

    </div>
  );
};
