import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Filter,
  History,
  Lock,
  Printer,
  Search,
  Shield,
  ShieldAlert,
  UserCheck,
} from 'lucide-react';
import {
  AuditTrailRun,
  ComprehensiveAuditLog,
  Encounter,
  FinancialException,
  UserRole,
  UserSession,
} from '../types';
import { exportDatasetToCSV } from '../utils/fileImport';
import { formatINR } from '../utils/formatters';
import { EmptyWorkspaceState } from './EmptyWorkspaceState';

interface AuditEvidenceViewProps {
  auditLogs: ComprehensiveAuditLog[];
  controlRuns: AuditTrailRun[];
  exceptions: FinancialException[];
  encounters: Encounter[];
  currentUser: UserSession;
  onSelectEncounter: (encounterId: string) => void;
  onNavigateToTab?: (tab: string) => void;
}

export const AuditEvidenceView: React.FC<AuditEvidenceViewProps> = ({
  auditLogs,
  controlRuns,
  exceptions,
  encounters,
  currentUser,
  onSelectEncounter,
  onNavigateToTab,
}) => {
  const [activeTab, setActiveTab] = useState<'audit-logs' | 'control-runs' | 'evidence-summary'>('audit-logs');
  const [actionFilter, setActionFilter] = useState<string>('ALL');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected encounter for evidence packet modal
  const [selectedEvidenceEnc, setSelectedEvidenceEnc] = useState<string | null>(null);

  const filteredLogs = useMemo(() => {
    return auditLogs.filter((log) => {
      if (actionFilter !== 'ALL' && log.action !== actionFilter) return false;
      if (roleFilter !== 'ALL' && log.role !== roleFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        if (
          !log.user.toLowerCase().includes(q) &&
          !log.details.toLowerCase().includes(q) &&
          !log.entityId.toLowerCase().includes(q) &&
          !log.action.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [auditLogs, actionFilter, roleFilter, searchQuery]);

  const handleExportAuditCSV = () => {
    exportDatasetToCSV(filteredLogs, 'Hospital_CFO_Audit_Trail_Report');
  };

  const handlePrintEvidence = () => {
    window.print();
  };

  // Evidence data for selected encounter
  const uniqueEncounters = useMemo(() => {
    const seen = new Set<string>();
    return encounters.filter((e) => {
      if (!e.Encounter_ID || seen.has(e.Encounter_ID)) return false;
      seen.add(e.Encounter_ID);
      return true;
    });
  }, [encounters]);

  const encEvidence = useMemo(() => {
    if (!selectedEvidenceEnc) return null;
    const enc = encounters.find((e) => e.Encounter_ID === selectedEvidenceEnc);
    const encExceptions = exceptions.filter((e) => e.Encounter_ID === selectedEvidenceEnc);
    const relatedLogs = auditLogs.filter(
      (l) => l.entityId.includes(selectedEvidenceEnc) || l.details.includes(selectedEvidenceEnc)
    );
    return { enc, exceptions: encExceptions, logs: relatedLogs };
  }, [selectedEvidenceEnc, encounters, exceptions, auditLogs]);

  if (auditLogs.length === 0 && controlRuns.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Audit Trail
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            End-to-end audit trail for statutory audits, internal financial controls, exception lifecycle changes and control runs.
          </p>
        </div>
        <EmptyWorkspaceState
          title="No Audit Events Recorded"
          description="The audit log records immutable governance events, data ingestions, control engine executions, exception investigations, and executive reviews. Activity will appear here as users interact with the system."
          badge="Audit Trail Active"
          actionText="Upload Hospital Financial Extracts"
          onAction={() => onNavigateToTab?.('data-intelligence')}
          suggestedDatasets={[
            'Data ingestion events and dataset checksums',
            'Control engine verification runs',
            'Exception lifecycle audits (Reviewed, Disputed, Approved)',
            'CFO Financial Review approvals and sign-offs',
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Audit Trail
              </h1>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold tracking-wider text-teal-800 border border-teal-200 uppercase">
                Immutable Governance Log
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              End-to-end audit trail for statutory audits, internal financial controls, exception lifecycle changes and control runs.
              {currentUser.role === 'Auditor' && (
                <span className="text-amber-800 font-bold ml-1">
                  (Auditor Profile: Strictly Read-Only)
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportAuditCSV}
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition shadow-2xs cursor-pointer"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              <span>Export Audit Trail (CSV)</span>
            </button>
          </div>
        </div>

        {/* Sub-tabs */}
        <div className="mt-4 flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-semibold w-fit">
          <button
            onClick={() => setActiveTab('audit-logs')}
            className={`rounded-md px-3.5 py-1.5 transition cursor-pointer ${
              activeTab === 'audit-logs'
                ? 'bg-white text-teal-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            System Action Log ({auditLogs.length})
          </button>
          <button
            onClick={() => setActiveTab('control-runs')}
            className={`rounded-md px-3.5 py-1.5 transition cursor-pointer ${
              activeTab === 'control-runs'
                ? 'bg-white text-teal-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Deterministic Control Runs ({controlRuns.length})
          </button>
          <button
            onClick={() => setActiveTab('evidence-summary')}
            className={`rounded-md px-3.5 py-1.5 transition cursor-pointer ${
              activeTab === 'evidence-summary'
                ? 'bg-white text-teal-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Encounter Evidence Dossier
          </button>
        </div>
      </div>

      {/* TAB 1: AUDIT TRAIL LOGS */}
      {activeTab === 'audit-logs' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          {/* Filters Bar */}
          <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <Filter className="h-4 w-4 text-slate-400" />
                <span>Action:</span>
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="border border-slate-300 rounded-md px-2 py-1 text-xs bg-white text-slate-900 focus:outline-teal-600"
                >
                  <option value="ALL">All Actions</option>
                  <option value="LOGIN">LOGIN</option>
                  <option value="LOGOUT">LOGOUT</option>
                  <option value="CONTROL_RUN">CONTROL RUN</option>
                  <option value="EXCEPTION_CREATION">EXCEPTION CREATION</option>
                  <option value="EXCEPTION_ASSIGNMENT">EXCEPTION ASSIGNMENT</option>
                  <option value="DEPARTMENT_VERIFICATION">DEPARTMENT VERIFICATION</option>
                  <option value="DEPARTMENT_DISPUTE">DEPARTMENT DISPUTE</option>
                  <option value="FINANCE_RESOLUTION">FINANCE RESOLUTION</option>
                  <option value="CFO_PACK_GENERATION">CFO PACK GENERATION</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <span>Role:</span>
                <select
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                  className="border border-slate-300 rounded-md px-2 py-1 text-xs bg-white text-slate-900 focus:outline-teal-600"
                >
                  <option value="ALL">All Roles</option>
                  <option value="CFO">CFO</option>
                  <option value="Finance/Billing Manager">Finance/Billing Manager</option>
                  <option value="Department Manager">Department Manager</option>
                  <option value="Auditor">Auditor</option>
                </select>
              </div>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search user, entity, details..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 border border-slate-300 rounded-md text-xs focus:ring-1 focus:ring-teal-600"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Log ID</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">User</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Entity</th>
                  <th className="py-2.5 px-3">Entity ID</th>
                  <th className="py-2.5 px-3">Audit Record Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px]">{log.id}</td>
                    <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px] whitespace-nowrap">
                      {log.timestamp}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{log.user}</td>
                    <td className="py-2.5 px-3 text-slate-700">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                        {log.role}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          log.action.includes('DISPUTE')
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : log.action.includes('VERIFICATION') || log.action.includes('RESOLUTION')
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : log.action.includes('RUN')
                            ? 'bg-teal-50 text-teal-800 border border-teal-200'
                            : 'bg-slate-100 text-slate-800 border border-slate-200'
                        }`}
                      >
                        {log.action.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{log.entityType}</td>
                    <td className="py-2.5 px-3 font-mono font-semibold text-teal-800">{log.entityId}</td>
                    <td className="py-2.5 px-3 text-slate-700 max-w-md">
                      <div>{log.details}</div>
                      {log.previousValue && log.newValue && (
                        <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                          Changed: &quot;{log.previousValue}&quot; &rarr; &quot;{log.newValue}&quot;
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: DETERMINISTIC CONTROL RUNS */}
      {activeTab === 'control-runs' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50/60 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900">
              Deterministic C01–C08 Control Execution Run History
            </h2>
            <span className="text-xs text-slate-500">
              Complete batch execution logs verified by deterministic engine
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Run ID</th>
                  <th className="py-2.5 px-3">Execution Time</th>
                  <th className="py-2.5 px-3">Data Period</th>
                  <th className="py-2.5 px-3 text-right">Records Processed</th>
                  <th className="py-2.5 px-3 text-right">Controls Executed</th>
                  <th className="py-2.5 px-3 text-right">Exceptions Generated</th>
                  <th className="py-2.5 px-3">Triggered User</th>
                  <th className="py-2.5 px-3 text-center">Engine Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {controlRuns.map((run) => (
                  <tr key={run.Run_ID} className="hover:bg-slate-50/80 transition">
                    <td className="py-2.5 px-3 font-mono font-bold text-teal-800">{run.Run_ID}</td>
                    <td className="py-2.5 px-3 text-slate-700 font-mono text-[11px]">{run.Run_Date_Time}</td>
                    <td className="py-2.5 px-3 text-slate-600">{run.Data_Period}</td>
                    <td className="py-2.5 px-3 text-right font-medium text-slate-800">
                      {run.Records_Processed.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-teal-800">{run.Controls_Executed}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-amber-900">
                      {run.Exceptions_Generated}
                    </td>
                    <td className="py-2.5 px-3 text-slate-800 font-medium">{run.User}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-200">
                        <CheckCircle2 className="h-3 w-3" /> VERIFIED
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: ENCOUNTER EVIDENCE SUMMARY DOSSIER */}
      {activeTab === 'evidence-summary' && (
        <div className="space-y-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
            <h2 className="text-sm font-bold text-slate-900 mb-1">
              Select Encounter for Full Audit Dossier
            </h2>
            <p className="text-xs text-slate-500 mb-3">
              Generates printable comprehensive audit evidence packet including service lines, exception resolutions and department clearance audit timestamps.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <select
                value={selectedEvidenceEnc || ''}
                onChange={(e) => setSelectedEvidenceEnc(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs bg-white text-slate-900 font-semibold focus:outline-teal-600"
              >
                <option value="">-- Choose Encounter ID --</option>
                {uniqueEncounters.map((e, idx) => (
                  <option key={`${e.Encounter_ID}-${idx}`} value={e.Encounter_ID}>
                    {e.Encounter_ID} &mdash; {e.Department} ({e.Payer_Type})
                  </option>
                ))}
              </select>

              {selectedEvidenceEnc && (
                <button
                  onClick={handlePrintEvidence}
                  className="flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-3 py-1.5 text-xs font-semibold text-white transition shadow-xs cursor-pointer"
                >
                  <Printer className="h-3.5 w-3.5" />
                  <span>Print Audit Evidence Dossier</span>
                </button>
              )}
            </div>
          </div>

          {encEvidence && encEvidence.enc && (
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-6 print:border-none print:shadow-none">
              {/* Dossier Header */}
              <div className="flex justify-between items-start border-b border-slate-200 pb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Encounter Financial Audit Evidence Packet
                  </h3>
                  <div className="mt-1 font-mono text-sm font-bold text-teal-800">
                    {encEvidence.enc.Encounter_ID}
                  </div>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <div>Department: <span className="font-semibold text-slate-800">{encEvidence.enc.Department}</span></div>
                  <div>Payer: <span className="font-semibold text-slate-800">{encEvidence.enc.Payer_Type}</span></div>
                  <div>Status: <span className="font-semibold text-slate-800">{encEvidence.enc.Discharge_Status}</span></div>
                </div>
              </div>

              {/* Exception Findings */}
              <div>
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
                  Identified Financial Exceptions ({encEvidence.exceptions.length})
                </h4>
                {encEvidence.exceptions.length === 0 ? (
                  <div className="text-xs text-emerald-700 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                    ✓ Clean Audit: No financial exceptions identified for this encounter.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {encEvidence.exceptions.map((exc, idx) => (
                      <div key={`${exc.Exception_ID}-${idx}`} className="p-3 rounded-lg border border-slate-200 bg-slate-50/60 text-xs">
                        <div className="flex justify-between font-semibold">
                          <span className="text-teal-800 font-mono">{exc.Exception_ID} ({exc.Control_ID})</span>
                          <span className="text-amber-900 font-bold">{formatINR(exc.Exposure_Amount)}</span>
                        </div>
                        <div className="mt-1 text-slate-700">{exc.Description}</div>
                        <div className="mt-1.5 flex justify-between text-[11px] text-slate-500">
                          <span>Status: <strong className="text-slate-800">{exc.Status}</strong></span>
                          <span>Assigned: <strong className="text-slate-800">{exc.Assigned_To}</strong></span>
                          <span>Resolution: <strong className="text-slate-800">{exc.Resolution || 'Pending'}</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Linked Audit Trail */}
              <div>
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
                  Associated Audit Activity Log ({encEvidence.logs.length})
                </h4>
                <div className="space-y-1.5">
                  {encEvidence.logs.map((l) => (
                    <div key={l.id} className="flex justify-between items-center p-2 rounded border border-slate-100 text-xs">
                      <div>
                        <span className="font-mono text-slate-400 mr-2 text-[10px]">{l.timestamp}</span>
                        <strong className="text-slate-800">{l.user}</strong>: {l.details}
                      </div>
                      <span className="font-mono text-[10px] text-slate-400">{l.action}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
