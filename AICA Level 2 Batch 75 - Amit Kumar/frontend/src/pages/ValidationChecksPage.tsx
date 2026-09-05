import React, { useEffect, useState } from 'react';
import type { Client, ValidationItem } from '../types';
import { fetchValidations } from '../services/api';
import { ShieldAlert, CheckCircle2, AlertTriangle, XCircle, Filter } from 'lucide-react';

interface ValidationChecksProps {
  client: Client;
}

export const ValidationChecksPage: React.FC<ValidationChecksProps> = ({ client }) => {
  const [validations, setValidations] = useState<ValidationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchValidations(client.id);
      setValidations(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (client) loadData();
  }, [client]);

  const filteredChecks = validations.filter(v => statusFilter === 'ALL' || v.status === statusFilter);

  const passedCount = validations.filter(v => v.status === 'Passed').length;
  const warningCount = validations.filter(v => v.status === 'Warning').length;
  const criticalCount = validations.filter(v => v.status === 'Critical').length;

  return (
    <div className="space-y-6">
      <div className="border-b border-ca-border pb-4">
        <h1 className="text-xl font-bold text-navy-900 uppercase tracking-tight">AUTOMATED AUDIT VALIDATION CHECKS</h1>
        <p className="text-xs text-ca-muted mt-0.5">20 automated sanity and Schedule III compliance rules across trial balance & schedules.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="ca-card bg-slate-900 text-white flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase block">Total Audit Checks</span>
            <span className="text-xl font-bold font-mono">{validations.length}</span>
          </div>
          <ShieldAlert className="w-6 h-6 text-orange-500" />
        </div>

        <button
          onClick={() => setStatusFilter('Passed')}
          className={`ca-card flex items-center justify-between text-left transition-colors ${
            statusFilter === 'Passed' ? 'ring-2 ring-emerald-500' : ''
          }`}
        >
          <div>
            <span className="text-[10px] text-emerald-800 font-bold uppercase block">Passed Checks</span>
            <span className="text-xl font-bold font-mono text-emerald-700">{passedCount}</span>
          </div>
          <CheckCircle2 className="w-6 h-6 text-emerald-600" />
        </button>

        <button
          onClick={() => setStatusFilter('Warning')}
          className={`ca-card flex items-center justify-between text-left transition-colors ${
            statusFilter === 'Warning' ? 'ring-2 ring-amber-500' : ''
          }`}
        >
          <div>
            <span className="text-[10px] text-amber-800 font-bold uppercase block">Warning Checks</span>
            <span className="text-xl font-bold font-mono text-amber-700">{warningCount}</span>
          </div>
          <AlertTriangle className="w-6 h-6 text-amber-600" />
        </button>

        <button
          onClick={() => setStatusFilter('Critical')}
          className={`ca-card flex items-center justify-between text-left transition-colors ${
            statusFilter === 'Critical' ? 'ring-2 ring-rose-500' : ''
          }`}
        >
          <div>
            <span className="text-[10px] text-rose-800 font-bold uppercase block">Critical Alerts</span>
            <span className="text-xl font-bold font-mono text-rose-700">{criticalCount}</span>
          </div>
          <XCircle className="w-6 h-6 text-rose-600" />
        </button>
      </div>

      <div className="flex items-center justify-between bg-slate-50 p-3 rounded border border-ca-border">
        <span className="text-xs font-bold text-navy-900">Showing {filteredChecks.length} of {validations.length} Validation Rules</span>
        
        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="font-semibold text-navy-900">Filter Status:</span>
          <select
            className="bg-white border border-ca-border text-xs px-3 py-1 rounded font-semibold focus:outline-none"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All Statuses ({validations.length})</option>
            <option value="Passed">Passed Only ({passedCount})</option>
            <option value="Warning">Warning Only ({warningCount})</option>
            <option value="Critical">Critical Only ({criticalCount})</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-ca-muted text-xs">Running audit validation checks...</div>
      ) : (
        <div className="overflow-x-auto border border-ca-border rounded-md shadow-sm">
          <table className="ca-table">
            <thead>
              <tr>
                <th className="w-16">Code</th>
                <th className="w-56">Validation Rule Name</th>
                <th className="w-28">Category</th>
                <th className="w-24 text-center">Status</th>
                <th>Observation Summary</th>
                <th>Detailed Audit Log</th>
              </tr>
            </thead>
            <tbody>
              {filteredChecks.map((v) => (
                <tr key={v.code}>
                  <td className="font-mono font-bold text-slate-800">{v.code}</td>
                  <td className="font-bold text-navy-900">{v.check_name}</td>
                  <td><span className="bg-slate-100 text-slate-700 text-[10px] font-bold px-2 py-0.5 rounded">{v.category}</span></td>
                  <td className="text-center">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                      v.status === 'Passed' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                      v.status === 'Warning' ? 'bg-amber-100 text-amber-800 border border-amber-300' : 'bg-rose-100 text-rose-800 border border-rose-300'
                    }`}>
                      {v.status}
                    </span>
                  </td>
                  <td className="font-semibold text-slate-800">{v.message}</td>
                  <td className="text-slate-600 text-[11px] font-mono">{v.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
