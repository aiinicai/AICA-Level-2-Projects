import React, { useState } from 'react';
import { 
  FileSpreadsheet, 
  FileDown, 
  FileText, 
  Briefcase, 
  Calendar, 
  Filter, 
  CheckCircle2, 
  Building, 
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Download
} from 'lucide-react';
import { Engagement, Observation, AuditType, FirmProfile } from '../../types/audit';
import { formatINR, formatDate } from '../../utils/formatters';
import { ExportService } from '../../services/exportService';

interface ReportsViewProps {
  engagements?: Engagement[];
  observations?: Observation[];
  auditTypes?: AuditType[];
  firmProfile: FirmProfile;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  engagements = [],
  observations = [],
  auditTypes = [],
  firmProfile,
}) => {
  const engList = engagements || [];
  const obsList = observations || [];
  const typeList = auditTypes || [];

  const [selectedEngagementId, setSelectedEngagementId] = useState<string>(engList[0]?.id || '');
  const [filterAuditType, setFilterAuditType] = useState('ALL');
  const [filterFY, setFilterFY] = useState('ALL');
  const [filterSeverity, setFilterSeverity] = useState('ALL');

  const auditTypeMap = new Map<string, AuditType>(typeList.map(at => [at.id, at]));
  const engagementMap = new Map<string, Engagement>(engList.map(e => [e.id, e]));

  const selectedEngagement = engList.find(e => e.id === selectedEngagementId) || engList[0];
  const selectedEngObs = selectedEngagement ? obsList.filter(o => o.engagementId === selectedEngagement.id) : [];
  const selectedEngAuditType = selectedEngagement ? auditTypeMap.get(selectedEngagement.auditTypeId) : undefined;

  const distinctFYs = Array.from(new Set(engList.map(e => e.financialYear))).sort().reverse();

  // Custom filter dataset
  const customFilteredObs = obsList.filter((obs) => {
    const eng = engagementMap.get(obs.engagementId);
    if (filterAuditType !== 'ALL' && eng?.auditTypeId !== filterAuditType) return false;
    if (filterFY !== 'ALL' && eng?.financialYear !== filterFY) return false;
    if (filterSeverity !== 'ALL' && obs.severity !== filterSeverity) return false;
    return true;
  });

  const totalExposure = obsList.reduce((acc, o) => acc + (o.financialImpact || 0), 0);

  return (
    <div id="reports-view-container" className="space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-2xl border border-stone-200 shadow-sm">
        <h1 className="text-xl font-bold text-stone-800 tracking-tight">Audit Reporting & Documentation Hub</h1>
        <p className="text-sm text-stone-500 mt-0.5">
          Generate formal audit observation memorandums, executive summaries, Word reports, and Excel data registers.
        </p>
      </div>

      {/* Section 1: Engagement-Specific Report Generator */}
      <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm space-y-5">
        <div className="flex items-center gap-2 pb-3 border-b border-stone-200">
          <div className="w-8 h-8 rounded-lg bg-[#F5F2ED] text-[#5A5A40] flex items-center justify-center">
            <Briefcase className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-stone-800">Assignment / Engagement Audit Report</h2>
            <p className="text-xs text-stone-500">
              Generate comprehensive audit memorandum with executive summary and detailed annexure sheets for a client.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
          <div className="space-y-2 md:col-span-2">
            <label className="text-xs font-bold text-stone-700 block">Select Audit Assignment:</label>
            <select
              value={selectedEngagementId}
              onChange={(e) => setSelectedEngagementId(e.target.value)}
              disabled={engList.length === 0}
              className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-stone-300 bg-stone-50 text-stone-800 focus:bg-white focus:outline-hidden font-medium disabled:opacity-60"
            >
              {engList.length === 0 ? (
                <option value="">-- No Audit Engagements Available (Create Client First) --</option>
              ) : (
                engList.map((eng) => (
                  <option key={eng.id} value={eng.id}>
                    {eng.clientName} ({eng.financialYear}) — {auditTypeMap.get(eng.auditTypeId)?.name || 'Audit'} [{eng.overallStatus}]
                  </option>
                ))
              )}
            </select>

            {selectedEngagement ? (
              <div className="p-3 bg-[#F5F2ED] rounded-xl border border-[#DED9D0] text-xs text-stone-600 flex flex-wrap items-center gap-4">
                <span>Total Findings: <strong className="text-stone-800">{selectedEngObs.length}</strong></span>
                <span>Open: <strong className="text-rose-600">{selectedEngObs.filter(o => o.status !== 'Closed' && o.status !== 'Rectified').length}</strong></span>
                <span>Exposure: <strong className="text-stone-800">{formatINR(selectedEngObs.reduce((s, o) => s + (o.financialImpact || 0), 0))}</strong></span>
                <span>Partner: <strong className="text-stone-800">{selectedEngagement.engagementPartner}</strong></span>
              </div>
            ) : (
              <div className="p-3 bg-stone-50 rounded-xl border border-stone-200 text-xs text-stone-500">
                No active audit engagement selected. Create a client engagement to generate formal memos and reports.
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2.5 justify-center">
            <button
              disabled={!selectedEngagement}
              onClick={() => {
                if (selectedEngagement) {
                  ExportService.exportEngagementReportPDF(selectedEngagement, selectedEngObs, selectedEngAuditType, firmProfile);
                }
              }}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
            >
              <FileDown className="w-4 h-4 text-amber-300" />
              <span>Download Formal PDF Report</span>
            </button>

            <button
              disabled={!selectedEngagement}
              onClick={() => {
                if (selectedEngagement) {
                  ExportService.exportEngagementReportDocx(selectedEngagement, selectedEngObs, selectedEngAuditType, firmProfile);
                }
              }}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
            >
              <FileText className="w-4 h-4 text-stone-600" />
              <span>Download Word Report (.docx)</span>
            </button>

            <button
              disabled={!selectedEngagement}
              onClick={() => {
                if (selectedEngagement) {
                  ExportService.exportObservationsToExcel(selectedEngObs, [selectedEngagement], typeList, `Engagement_${selectedEngagement.clientCode}`);
                }
              }}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
              <span>Export Assignment Excel (.xlsx)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Section 2: Master Firm-Wide Data Export */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <FileSpreadsheet className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-stone-800">Master CA Practice Excel Register</h3>
            <p className="text-xs text-stone-500 leading-relaxed">
              Export all {obsList.length} observations across all {engList.length} engagements into a multi-tab Excel (.xlsx) workbook featuring an Executive Summary KPI dashboard + Full Observation Register.
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={() => ExportService.exportObservationsToExcel(obsList, engList, typeList, 'Master_Audit_Tracker')}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold shadow-xs transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Download Master Excel (.xlsx)</span>
            </button>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-stone-200 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-700 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-stone-800">Risk Exposure & High-Severity Register</h3>
            <p className="text-xs text-stone-500 leading-relaxed">
              Export all Critical and High severity observations across all client audits with financial impact details, root causes, and discussion notes in landscape PDF.
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={() => {
                const highRiskObs = obsList.filter(o => o.severity === 'Critical' || o.severity === 'High');
                ExportService.exportFilteredObservationsPDF(highRiskObs, engList, typeList, firmProfile, 'Critical & High Risk Audit Findings');
              }}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-rose-700 hover:bg-rose-800 text-white text-xs font-bold shadow-xs transition-colors"
            >
              <FileDown className="w-4 h-4" />
              <span>Download High Risk PDF Register</span>
            </button>
          </div>
        </div>
      </div>

      {/* Section 3: Custom Query & Filtered Report Generator */}
      <div className="bg-white p-6 rounded-xl border border-stone-200 shadow-xs space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-stone-200">
          <div className="w-8 h-8 rounded-lg bg-[#5A5A40]/10 text-[#5A5A40] flex items-center justify-center">
            <Filter className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-stone-900">Custom Filtered Report Builder</h3>
            <p className="text-xs text-stone-500">
              Filter by audit type, financial year, or risk severity, and download custom formatted reports.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs font-bold text-stone-700 block mb-1">Audit Type</label>
            <select
              value={filterAuditType}
              onChange={(e) => setFilterAuditType(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 bg-white text-stone-900"
            >
              <option value="ALL">All Audit Types</option>
              {typeList.map((at) => (
                <option key={at.id} value={at.id}>
                  {at.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-stone-700 block mb-1">Financial Year</label>
            <select
              value={filterFY}
              onChange={(e) => setFilterFY(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 bg-white text-stone-900"
            >
              <option value="ALL">All Financial Years</option>
              {distinctFYs.map((fy) => (
                <option key={fy} value={fy}>
                  {fy}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold text-stone-700 block mb-1">Risk Severity</label>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-stone-300 bg-white text-stone-900"
            >
              <option value="ALL">All Severities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>

        <div className="p-3.5 bg-stone-50 rounded-lg border border-stone-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="text-xs text-stone-600">
            Selected Records: <strong className="text-stone-900">{customFilteredObs.length} Observations</strong> (Total Exposure: <strong className="text-stone-900">{formatINR(customFilteredObs.reduce((s, o) => s + (o.financialImpact || 0), 0))}</strong>)
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => ExportService.exportObservationsToExcel(customFilteredObs, engList, typeList, 'Custom_Filtered_Audit_Report')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold transition-colors shadow-2xs"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
              <span>Export Filtered Excel</span>
            </button>

            <button
              onClick={() => ExportService.exportFilteredObservationsPDF(customFilteredObs, engList, typeList, firmProfile, 'Custom Audit Register')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-[#F5F2ED] text-stone-700 text-xs font-semibold transition-colors shadow-2xs"
            >
              <FileDown className="w-3.5 h-3.5 text-rose-600" />
              <span>Export Filtered PDF</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
