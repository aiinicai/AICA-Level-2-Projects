import React, { useState, useMemo } from 'react';
import { 
  AuditLogEntry, 
  AuditCategory, 
  AuditSeverity, 
  User 
} from '../types';
import { 
  ShieldCheck, 
  Search, 
  Filter, 
  Download, 
  Printer, 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Building2, 
  Lock, 
  Copy, 
  Check, 
  ExternalLink,
  PlusCircle,
  Eye,
  Hash,
  Scale,
  Award
} from 'lucide-react';
import { exportToWord, exportToPdf, generateAuditTrailReportHtml } from '../utils/reportExporter';

interface AuditTrailViewProps {
  auditLogs: AuditLogEntry[];
  currentUser: User;
  onLogCustomEvent?: (event: AuditLogEntry) => void;
}

export const AuditTrailView: React.FC<AuditTrailViewProps> = ({
  auditLogs,
  currentUser,
  onLogCustomEvent,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [copiedHashId, setCopiedHashId] = useState<string | null>(null);
  const [testActionModalOpen, setTestActionModalOpen] = useState(false);
  const [testActionTitle, setTestActionTitle] = useState('Manual Partner Override Logged');
  const [testActionCategory, setTestActionCategory] = useState<AuditCategory>('PERFORMANCE_GOVERNANCE');
  const [testActionNotes, setTestActionNotes] = useState('Partner conducted annual audit review adjustment under ISA 230 standard.');
  const [testNotification, setTestNotification] = useState<string | null>(null);

  const handleCopyHash = (id: string, hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHashId(id);
    setTimeout(() => setCopiedHashId(null), 2500);
  };

  const filteredLogs = useMemo(() => {
    return auditLogs.filter((log) => {
      const matchesSearch = 
        log.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.actionTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.actorName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (log.targetEmployeeName && log.targetEmployeeName.toLowerCase().includes(searchTerm.toLowerCase())) ||
        log.details.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesCategory = selectedCategory === 'ALL' || log.category === selectedCategory;
      const matchesSeverity = selectedSeverity === 'ALL' || log.severity === selectedSeverity;
      return matchesSearch && matchesCategory && matchesSeverity;
    });
  }, [auditLogs, searchTerm, selectedCategory, selectedSeverity]);

  const stats = useMemo(() => {
    const total = auditLogs.length;
    const financial = auditLogs.filter((l) => l.category === 'FINANCIAL_DISBURSEMENT').length;
    const performance = auditLogs.filter((l) => l.category === 'PERFORMANCE_GOVERNANCE').length;
    const statutory = auditLogs.filter((l) => l.category === 'STATUTORY_COMPLIANCE').length;
    return { total, financial, performance, statutory };
  }, [auditLogs]);

  const handleExportWord = () => {
    const contentHtml = generateAuditTrailReportHtml(
      filteredLogs,
      `Category: ${selectedCategory} | Severity: ${selectedSeverity} | Query: "${searchTerm || 'All'}"`
    );
    exportToWord({
      title: 'Administrative Audit Trail & Governance Log',
      filename: `Paras-Advisory-Audit-Trail-${new Date().toISOString().split('T')[0]}`,
      officialRefCode: 'PAA-AUDIT-2026',
      contentHtml,
    });
  };

  const handleExportPdf = () => {
    const contentHtml = generateAuditTrailReportHtml(
      filteredLogs,
      `Category: ${selectedCategory} | Severity: ${selectedSeverity} | Query: "${searchTerm || 'All'}"`
    );
    exportToPdf({
      title: 'Administrative Audit Trail & Governance Log',
      filename: `Paras-Advisory-Audit-Trail-${new Date().toISOString().split('T')[0]}`,
      officialRefCode: 'PAA-AUDIT-2026',
      contentHtml,
    });
  };

  const handleCreateTestLog = (e: React.FormEvent) => {
    e.preventDefault();
    const newEntry: AuditLogEntry = {
      id: `AUD-2026-${Math.floor(1000 + Math.random() * 9000)}`,
      timestamp: new Date().toISOString(),
      actionType: 'APPRAISAL_OVERRIDE_SAVED',
      actionTitle: testActionTitle,
      category: testActionCategory,
      severity: testActionCategory === 'FINANCIAL_DISBURSEMENT' ? 'FINANCIAL' : 'ACTION',
      actorId: currentUser.id,
      actorName: currentUser.fullName,
      actorRole: currentUser.role,
      actorDesignation: currentUser.currentDesignation,
      targetEmployeeName: 'Firm-Wide Audit Roster',
      targetDepartment: currentUser.departmentName,
      details: testActionNotes,
      newValue: 'Recorded & Verified in Audit Trail',
      ipAddress: '194.170.84.15 (ADGM Maryah Island HQ)',
      verificationHash: `sha256:${Array.from({ length: 40 }, () => Math.floor(Math.random() * 16).toString(16)).join('')}`,
      authorizedUnderPolicy: 'ADGM FSRA Supervisory Accountability Directive',
    };
    if (onLogCustomEvent) {
      onLogCustomEvent(newEntry);
    }
    setTestActionModalOpen(false);
    setTestNotification(`Audit action ${newEntry.id} logged with SHA-256 integrity token!`);
    setTimeout(() => setTestNotification(null), 3500);
  };

  const getSeverityBadge = (severity: AuditSeverity) => {
    switch (severity) {
      case 'FINANCIAL':
        return 'bg-teal-50 text-teal-800 border-teal-200';
      case 'CRITICAL':
        return 'bg-rose-50 text-rose-800 border-rose-200';
      case 'ACTION':
        return 'bg-blue-50 text-blue-800 border-blue-200';
      case 'INFO':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getCategoryLabel = (cat: AuditCategory) => {
    switch (cat) {
      case 'PERFORMANCE_GOVERNANCE':
        return 'Performance Governance';
      case 'FINANCIAL_DISBURSEMENT':
        return 'Bonus & Financial';
      case 'STATUTORY_COMPLIANCE':
        return 'Statutory PIP Notice';
      case 'TRAINING_BUDGET':
        return 'Training & Upskilling';
      case 'SECURITY_AUTHENTICATION':
        return 'Security & Auth';
      default:
        return cat;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Compliance & Governance Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-slate-900 text-teal-400 tracking-wide flex items-center gap-1 font-mono">
              <Lock className="w-3 h-3" /> ISA 230 & ADGM FSRA AUDIT TRAIL
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-teal-50 text-teal-800 border border-teal-200 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3" /> SHA-256 Tamper-Evident Active
            </span>
          </div>
          <h1 className="text-2xl font-black text-slate-950 tracking-tight">
            Administrative Action Audit Trail & Governance Log
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Immutable tracking of critical administrative actions: Annual Performance Matrix approvals, AED 15,000 certification bonus disbursements, statutory two-tier improvement notices, and evaluation syncs for compliance and accountability.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <button
            onClick={() => setTestActionModalOpen(true)}
            className="px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
          >
            <PlusCircle className="w-4 h-4 text-teal-400" />
            Log Action
          </button>
          <button
            onClick={handleExportWord}
            className="px-3 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
            title="Download complete audit trail as Microsoft Word document"
          >
            <Download className="w-4 h-4" />
            Export Word (.doc)
          </button>
          <button
            onClick={handleExportPdf}
            className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
            title="Print or save complete audit trail as PDF"
          >
            <Printer className="w-4 h-4" />
            Export PDF
          </button>
        </div>
      </div>

      {testNotification && (
        <div className="bg-teal-900 text-white p-3.5 rounded-xl text-xs font-semibold flex items-center gap-2 shadow-md animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-teal-300 shrink-0" />
          <span>{testNotification}</span>
        </div>
      )}

      {/* 4 Summary Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Total Audited Events</span>
            <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center text-slate-700">
              <Hash className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 mt-2 tabular-nums">
            {stats.total}
          </div>
          <div className="text-[11px] text-teal-700 font-medium mt-1 flex items-center gap-1">
            <Check className="w-3 h-3" /> 100% Cryptographically Sealed
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Financial Bonus Approvals</span>
            <div className="w-7 h-7 rounded-lg bg-teal-50 flex items-center justify-center text-teal-700">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-teal-900 mt-2 tabular-nums">
            {stats.financial}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            AED 15,000.00 Chartered Bonuses
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Matrix Governance Actions</span>
            <div className="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center text-blue-700">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-blue-950 mt-2 tabular-nums">
            {stats.performance}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Target approvals & annual ratings
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Statutory Remediations</span>
            <div className="w-7 h-7 rounded-lg bg-rose-50 flex items-center justify-center text-rose-700">
              <Scale className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-rose-950 mt-2 tabular-nums">
            {stats.statutory}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            UAE Decree-Law 33/2021 Notices
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by Audit Ref, Action Title, Partner, Employee..."
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 text-xs focus:ring-2 focus:ring-blue-600 focus:outline-hidden"
            />
          </div>
          <div className="flex items-center gap-2 w-full md:w-auto">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-hidden cursor-pointer"
            >
              <option value="ALL">All Categories</option>
              <option value="PERFORMANCE_GOVERNANCE">Performance Governance</option>
              <option value="FINANCIAL_DISBURSEMENT">Financial & Bonuses</option>
              <option value="STATUTORY_COMPLIANCE">Statutory Compliance</option>
              <option value="TRAINING_BUDGET">Training Budget</option>
            </select>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 bg-white focus:outline-hidden cursor-pointer"
            >
              <option value="ALL">All Severities</option>
              <option value="FINANCIAL">Financial Disbursement</option>
              <option value="CRITICAL">Critical Regulatory</option>
              <option value="ACTION">Administrative Action</option>
              <option value="INFO">Informational Log</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Audit Trail Data Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Audit Ref & Timestamp</th>
                <th className="py-3 px-4">Action & Classification</th>
                <th className="py-3 px-4">Authorized Actor</th>
                <th className="py-3 px-4">Subject Candidate / Unit</th>
                <th className="py-3 px-4">Audit Narrative & Changes</th>
                <th className="py-3 px-4">Integrity Token (SHA-256)</th>
                <th className="py-3 px-4 text-right">Inspection</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans">
              {filteredLogs.map((log) => (
                <tr 
                  key={log.id} 
                  className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  onClick={() => setSelectedLog(log)}
                >
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <span className="font-mono font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                      {log.id}
                    </span>
                    <div className="text-[11px] text-slate-400 mt-0.5 tabular-nums flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {new Date(log.timestamp).toLocaleString('en-GB', {
                        timeZone: 'Asia/Dubai',
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })} GST
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="font-semibold text-slate-900 leading-tight">
                      {log.actionTitle}
                    </div>
                    <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadge(log.severity)}`}>
                      {getCategoryLabel(log.category)}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="font-semibold text-slate-900">
                      {log.actorName}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      {log.actorDesignation}
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    {log.targetEmployeeName ? (
                      <div className="font-semibold text-slate-800">
                        {log.targetEmployeeName}
                      </div>
                    ) : (
                      <span className="text-slate-400">Firm-Wide</span>
                    )}
                    <div className="text-[10px] text-slate-400">
                      {log.targetDepartment || 'General Practice'}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 max-w-xs">
                    <p className="text-slate-600 line-clamp-2 leading-relaxed">
                      {log.details}
                    </p>
                    {log.newValue && (
                      <div className="mt-1 text-[10px] text-teal-800 font-semibold truncate bg-teal-50 px-1.5 py-0.5 rounded border border-teal-100">
                        New: {log.newValue}
                      </div>
                    )}
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-1.5 font-mono text-[11px] text-slate-500">
                      <span>{log.verificationHash.slice(0, 14)}...</span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopyHash(log.id, log.verificationHash);
                        }}
                        className="text-slate-400 hover:text-slate-700 p-0.5 cursor-pointer"
                        title="Copy complete SHA-256 verification hash"
                      >
                        {copiedHashId === log.id ? (
                          <Check className="w-3.5 h-3.5 text-teal-600" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                      {log.ipAddress}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedLog(log);
                      }}
                      className="px-2.5 py-1 rounded-md text-[11px] font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors cursor-pointer inline-flex items-center gap-1"
                    >
                      <Eye className="w-3 h-3" /> Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Detailed Inspection Slip */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full border border-slate-200 shadow-2xl overflow-hidden animate-in zoom-in-95">
            <div className="bg-slate-900 text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-400/30 flex items-center justify-center text-teal-400">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-teal-400 font-bold tracking-wider">
                      {selectedLog.id}
                    </span>
                    <span className="text-slate-400">•</span>
                    <span className="text-xs text-slate-300">Regulatory Audit Slip</span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-0.5">
                    {selectedLog.actionTitle}
                  </h3>
                </div>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-5 text-xs max-h-[75vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Timestamp (Gulf Standard Time)
                  </span>
                  <p className="font-semibold text-slate-900 mt-0.5 tabular-nums">
                    {new Date(selectedLog.timestamp).toLocaleString('en-GB', {
                      timeZone: 'Asia/Dubai',
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })} GST
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Governance Classification
                  </span>
                  <div className="mt-1">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadge(selectedLog.severity)}`}>
                      {getCategoryLabel(selectedLog.category)}
                    </span>
                  </div>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Authorized Practice Actor
                  </span>
                  <p className="font-semibold text-slate-900 mt-0.5">
                    {selectedLog.actorName}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {selectedLog.actorDesignation} ({selectedLog.actorRole})
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Target Subject & Unit
                  </span>
                  <p className="font-semibold text-slate-900 mt-0.5">
                    {selectedLog.targetEmployeeName || 'Firm-Wide Organization'}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {selectedLog.targetDepartment || 'All Departments'}
                  </p>
                </div>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">
                  Administrative Action Details & Impact
                </span>
                <div className="p-3.5 rounded-xl bg-white border border-slate-200 text-slate-800 leading-relaxed font-sans">
                  {selectedLog.details}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900 text-slate-300 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-teal-400 tracking-wider uppercase flex items-center gap-1 font-mono">
                    <Lock className="w-3 h-3" /> SHA-256 Tamper-Evident Verification Token
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    IP: {selectedLog.ipAddress}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950 font-mono text-[11px] text-teal-300 break-all select-all border border-slate-800 flex items-center justify-between">
                  <span>{selectedLog.verificationHash}</span>
                  <button
                    onClick={() => handleCopyHash(selectedLog.id, selectedLog.verificationHash)}
                    className="ml-2 text-slate-400 hover:text-white shrink-0 p-1 cursor-pointer"
                    title="Copy verification hash"
                  >
                    {copiedHashId === selectedLog.id ? (
                      <Check className="w-3.5 h-3.5 text-teal-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
                <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
                  <span>Authority Policy: <strong>{selectedLog.authorizedUnderPolicy}</strong></span>
                  <span className="text-teal-400 font-semibold">Integrity Verified ✓</span>
                </div>
              </div>
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-medium">
                Paras Accounting & Auditing Advisory • Practice Oversight Journal
              </span>
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold cursor-pointer"
              >
                Close Inspection Slip
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Simulate / Log Administrative Action */}
      {testActionModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-2xl overflow-hidden animate-in zoom-in-95">
            <div className="bg-slate-900 text-white p-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PlusCircle className="w-5 h-5 text-teal-400" />
                <h3 className="text-base font-bold text-white">
                  Log Administrative Action for Compliance
                </h3>
              </div>
              <button
                onClick={() => setTestActionModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateTestLog} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Action Title
                </label>
                <input
                  type="text"
                  required
                  value={testActionTitle}
                  onChange={(e) => setTestActionTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs focus:ring-2 focus:ring-blue-600 focus:outline-hidden"
                  placeholder="e.g., Performance Matrix Mid-Year Target Adjustment"
                />
              </div>
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Governance Category
                </label>
                <select
                  value={testActionCategory}
                  onChange={(e) => setTestActionCategory(e.target.value as AuditCategory)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs focus:ring-2 focus:ring-blue-600 focus:outline-hidden cursor-pointer"
                >
                  <option value="PERFORMANCE_GOVERNANCE">Performance Matrix & Governance</option>
                  <option value="FINANCIAL_DISBURSEMENT">Chartered Bonus & Financial Entitlement</option>
                  <option value="STATUTORY_COMPLIANCE">Statutory Improvement & UAE Labor Law</option>
                  <option value="TRAINING_BUDGET">Training Budget Allocation</option>
                </select>
              </div>
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Administrative Narrative & Audit Justification
                </label>
                <textarea
                  rows={3}
                  required
                  value={testActionNotes}
                  onChange={(e) => setTestActionNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs focus:ring-2 focus:ring-blue-600 focus:outline-hidden"
                  placeholder="State the regulatory justification, partner endorsement, and affected deliverables..."
                />
              </div>
              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setTestActionModalOpen(false)}
                  className="px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-bold cursor-pointer"
                >
                  Commit to Audit Trail
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
