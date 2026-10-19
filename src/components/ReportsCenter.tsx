import React from 'react';
import { 
  User, 
  AppraisalRecord, 
  TaskEvaluation, 
  AttendanceRecord, 
  Department, 
  AnnualPerformancePlan, 
  ProfessionalCertification,
  StatutoryNotice,
  AuditLogEntry
} from '../types';
import { 
  FileText, 
  Download, 
  Printer, 
  FileCheck, 
  Scale, 
  Award, 
  Building2, 
  Sliders, 
  Users, 
  CheckCircle2, 
  Search,
  ExternalLink,
  ChevronRight,
  Lock
} from 'lucide-react';
import { 
  exportToWord, 
  exportToPdf, 
  generateAppraisalReportHtml, 
  generateStatutoryNoticeHtml, 
  generatePerformanceMatrixHtml, 
  generatePracticeAnalyticsReportHtml, 
  generateCertificationReportHtml,
  generateAuditTrailReportHtml
} from '../utils/reportExporter';
import { getTierMetadata, getLoyaltyTierInfo } from '../utils/scoringEngine';

interface ReportsCenterProps {
  companyInfo: any;
  currentUser: User;
  allUsers: User[];
  departments: Department[];
  allAppraisals: AppraisalRecord[];
  allPlans: AnnualPerformancePlan[];
  certifications: ProfessionalCertification[];
  statutoryNotices: StatutoryNotice[];
  auditLogs?: AuditLogEntry[];
}

export const ReportsCenter: React.FC<ReportsCenterProps> = ({
  companyInfo,
  currentUser,
  allUsers,
  departments,
  allAppraisals,
  allPlans,
  certifications,
  statutoryNotices,
  auditLogs = [],
}) => {
  type ReportCategory = 'appraisal' | 'statutory' | 'matrix' | 'firm_analytics' | 'certifications' | 'audit_register';
  const [selectedCategory, setSelectedCategory] = React.useState<ReportCategory>('appraisal');
  const [selectedEmpId, setSelectedEmpId] = React.useState<string>(
    currentUser.role === 'employee' ? currentUser.id : 'emp-zayed'
  );
  const [selectedNoticeId, setSelectedNoticeId] = React.useState<string>(statutoryNotices[0]?.id || 'not-01');

  const selectedEmployee = allUsers.find((u) => u.id === selectedEmpId) || allUsers[0];
  const selectedAppraisal = allAppraisals.find((a) => a.employeeId === selectedEmployee?.id) || allAppraisals[0];
  const selectedPlan = allPlans.find((p) => p.employeeId === selectedEmployee?.id) || allPlans[0];
  const selectedNotice = statutoryNotices.find((n) => n.id === selectedNoticeId) || statutoryNotices[0];

  let currentTitle = 'Annual Performance Appraisal Report';
  let currentSubtitle = 'Paras Accounting & Auditing Advisory — Abu Dhabi, UAE';
  let currentRef = `PAA-APP-2026-${selectedEmployee?.employeeIdCode?.replace('EMP-', '') || '01'}`;
  let currentFilename = `Appraisal_Report_${selectedEmployee?.fullName?.replace(/\s+/g, '_')}_2026`;
  let currentHtml = '';

  if (selectedCategory === 'appraisal' && selectedAppraisal && selectedEmployee) {
    currentTitle = `Performance Appraisal Scorecard: ${selectedEmployee.fullName}`;
    currentSubtitle = `${selectedEmployee.currentDesignation} • ${selectedEmployee.departmentName} • Q3-2026 Cycle`;
    currentRef = `PAA-APP-2026-${selectedEmployee.employeeIdCode.replace('EMP-', '')}`;
    currentFilename = `Appraisal_Report_${selectedEmployee.fullName.replace(/\s+/g, '_')}_2026`;
    currentHtml = generateAppraisalReportHtml(selectedAppraisal, selectedEmployee, 'Tariq Al Hammadi');
  } else if (selectedCategory === 'statutory' && selectedNotice && selectedEmployee) {
    currentTitle = selectedNotice.noticeTitle;
    currentSubtitle = `Statutory Notice under UAE Federal Decree-Law No. 33 of 2021 • Tier ${selectedNotice.tier} Escalation`;
    currentRef = selectedNotice.officialRefCode;
    currentFilename = `Statutory_Notice_Tier${selectedNotice.tier}_${selectedEmployee.fullName.replace(/\s+/g, '_')}`;
    currentHtml = generateStatutoryNoticeHtml(selectedNotice, selectedEmployee, companyInfo);
  } else if (selectedCategory === 'matrix' && selectedPlan && selectedEmployee) {
    currentTitle = `Annual Performance Matrix & Achievement Report: ${selectedEmployee.fullName}`;
    currentSubtitle = `Key Performance Goals, Target Deliverables & Manager Assessment Rating • Year ${selectedPlan.year}`;
    currentRef = `PAA-MAT-${selectedPlan.year}-${selectedEmployee.employeeIdCode.replace('EMP-', '')}`;
    currentFilename = `Annual_Matrix_${selectedEmployee.fullName.replace(/\s+/g, '_')}_${selectedPlan.year}`;
    currentHtml = generatePerformanceMatrixHtml(selectedPlan, selectedEmployee, 'Tariq Al Hammadi');
  } else if (selectedCategory === 'firm_analytics') {
    currentTitle = 'Firm-Wide HR Intelligence & Performance Analytics Report';
    currentSubtitle = 'Paras Accounting & Auditing Advisory • Annual Operational & T&D Budget Review';
    currentRef = 'PAA-EXEC-INTEL-2026';
    currentFilename = 'Paras_Advisory_Firmwide_Performance_Report_2026';
    currentHtml = generatePracticeAnalyticsReportHtml(companyInfo, departments, allAppraisals, allUsers);
  } else if (selectedCategory === 'certifications') {
    currentTitle = 'Chartered Professional Certification & AED 15,000 Bonus Ledger';
    currentSubtitle = 'Special Performance Bonus Disbursement & Talent Upskilling Records';
    currentRef = 'PAA-BONUS-CERT-2026';
    currentFilename = 'Chartered_Certification_Bonus_Ledger_2026';
    currentHtml = generateCertificationReportHtml(certifications, selectedCategory === 'certifications' && currentUser.role === 'employee' ? selectedEmployee : undefined);
  } else if (selectedCategory === 'audit_register') {
    currentTitle = 'Administrative Action & Governance Audit Trail Register';
    currentSubtitle = 'ADGM FSRA Supervisory Accountability & UAE Decree-Law No. 33/2021';
    currentRef = 'PAA-AUDIT-REG-2026';
    currentFilename = 'Paras_Advisory_Audit_Trail_Register_2026';
    currentHtml = generateAuditTrailReportHtml(auditLogs || []);
  }

  const handleDownloadWord = () => {
    exportToWord({
      title: currentTitle,
      subtitle: currentSubtitle,
      filename: currentFilename,
      officialRefCode: currentRef,
      contentHtml: currentHtml,
    });
  };

  const handleDownloadPdf = () => {
    exportToPdf({
      title: currentTitle,
      subtitle: currentSubtitle,
      filename: currentFilename,
      officialRefCode: currentRef,
      contentHtml: currentHtml,
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-blue-900 uppercase tracking-wider">
              <FileText className="w-3.5 h-3.5 text-blue-700" />
              <span>Official Document & Report Generation Desk</span>
              <span className="text-slate-300">•</span>
              <span className="text-teal-700">Word (.doc) & PDF Formats</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">
              Executive & Statutory Reporting Center
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Generate, preview, and download evaluation dossiers, two-tier 90-day improvement letters, and firm analytics in Microsoft Word and PDF formats.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <a
              href="/paras_advisory_capstone.zip"
              download="paras_advisory_capstone.zip"
              className="px-4 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition-colors flex items-center gap-2 shadow-xs cursor-pointer border border-slate-700"
              title="Download entire project source code and git assets packaged as a zip file for GitHub jury upload"
            >
              <Download className="w-4 h-4 text-teal-400" />
              Download GitHub Zip Pack
            </a>
            <button
              onClick={handleDownloadWord}
              className="px-4 py-2.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs transition-colors flex items-center gap-2 shadow-xs cursor-pointer"
              title="Download formatted Microsoft Word document (.doc)"
            >
              <Download className="w-4 h-4 text-blue-200" />
              Download Word (.doc)
            </button>
            <button
              onClick={handleDownloadPdf}
              className="px-4 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs transition-colors flex items-center gap-2 shadow-xs cursor-pointer"
              title="Print or Save as PDF vector document"
            >
              <Printer className="w-4 h-4 text-teal-200" />
              Print / Save PDF
            </button>
          </div>
        </div>

        {/* 6 Report Type Selector Tabs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 mt-6 pt-6 border-t border-slate-100">
          <button
            onClick={() => setSelectedCategory('appraisal')}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              selectedCategory === 'appraisal'
                ? 'bg-blue-900 text-white border-blue-900 shadow-sm'
                : 'bg-slate-50 hover:bg-slate-100/80 text-slate-700 border-slate-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <FileCheck className={`w-4 h-4 ${selectedCategory === 'appraisal' ? 'text-teal-400' : 'text-blue-700'}`} />
              <span className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                selectedCategory === 'appraisal' ? 'bg-blue-800 text-blue-100' : 'bg-slate-200 text-slate-700'
              }`}>
                Scorecard
              </span>
            </div>
            <div className="font-bold text-xs">Appraisal Report</div>
            <div className={`text-[11px] mt-0.5 line-clamp-1 ${selectedCategory === 'appraisal' ? 'text-blue-200' : 'text-slate-400'}`}>
              50% Deliverables + SLA
            </div>
          </button>

          <button
            onClick={() => setSelectedCategory('statutory')}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              selectedCategory === 'statutory'
                ? 'bg-rose-950 text-white border-rose-900 shadow-sm'
                : 'bg-slate-50 hover:bg-slate-100/80 text-slate-700 border-slate-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <Scale className={`w-4 h-4 ${selectedCategory === 'statutory' ? 'text-rose-400' : 'text-rose-700'}`} />
              <span className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                selectedCategory === 'statutory' ? 'bg-rose-900 text-rose-100' : 'bg-slate-200 text-slate-700'
              }`}>
                MOHRE
              </span>
            </div>
            <div className="font-bold text-xs">Two-Tier 90D PIP</div>
            <div className={`text-[11px] mt-0.5 line-clamp-1 ${selectedCategory === 'statutory' ? 'text-rose-200' : 'text-slate-400'}`}>
              Decree-Law 33/2021
            </div>
          </button>

          <button
            onClick={() => setSelectedCategory('matrix')}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              selectedCategory === 'matrix'
                ? 'bg-teal-950 text-white border-teal-900 shadow-sm'
                : 'bg-slate-50 hover:bg-slate-100/80 text-slate-700 border-slate-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <Sliders className={`w-4 h-4 ${selectedCategory === 'matrix' ? 'text-teal-400' : 'text-teal-700'}`} />
              <span className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                selectedCategory === 'matrix' ? 'bg-teal-900 text-teal-100' : 'bg-slate-200 text-slate-700'
              }`}>
                Annual
              </span>
            </div>
            <div className="font-bold text-xs">Annual Matrix</div>
            <div className={`text-[11px] mt-0.5 line-clamp-1 ${selectedCategory === 'matrix' ? 'text-teal-200' : 'text-slate-400'}`}>
              Manager Approved Goals
            </div>
          </button>

          <button
            onClick={() => setSelectedCategory('firm_analytics')}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              selectedCategory === 'firm_analytics'
                ? 'bg-slate-900 text-white border-slate-900 shadow-sm'
                : 'bg-slate-50 hover:bg-slate-100/80 text-slate-700 border-slate-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <Building2 className={`w-4 h-4 ${selectedCategory === 'firm_analytics' ? 'text-teal-400' : 'text-indigo-700'}`} />
              <span className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                selectedCategory === 'firm_analytics' ? 'bg-slate-800 text-slate-100' : 'bg-slate-200 text-slate-700'
              }`}>
                Executive
              </span>
            </div>
            <div className="font-bold text-xs">Practice Analytics</div>
            <div className={`text-[11px] mt-0.5 line-clamp-1 ${selectedCategory === 'firm_analytics' ? 'text-slate-300' : 'text-slate-400'}`}>
              50 Staff • Budget
            </div>
          </button>

          <button
            onClick={() => setSelectedCategory('certifications')}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              selectedCategory === 'certifications'
                ? 'bg-amber-950 text-white border-amber-900 shadow-sm'
                : 'bg-slate-50 hover:bg-slate-100/80 text-slate-700 border-slate-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <Award className={`w-4 h-4 ${selectedCategory === 'certifications' ? 'text-amber-400' : 'text-amber-700'}`} />
              <span className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                selectedCategory === 'certifications' ? 'bg-amber-900 text-amber-100' : 'bg-slate-200 text-slate-700'
              }`}>
                Incentive
              </span>
            </div>
            <div className="font-bold text-xs">AED 15k Bonus</div>
            <div className={`text-[11px] mt-0.5 line-clamp-1 ${selectedCategory === 'certifications' ? 'text-amber-200' : 'text-slate-400'}`}>
              ACA/ACCA/CPA
            </div>
          </button>

          <button
            onClick={() => setSelectedCategory('audit_register')}
            className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
              selectedCategory === 'audit_register'
                ? 'bg-slate-950 text-white border-slate-900 shadow-sm'
                : 'bg-slate-50 hover:bg-slate-100/80 text-slate-700 border-slate-200'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <Lock className={`w-4 h-4 ${selectedCategory === 'audit_register' ? 'text-teal-400' : 'text-slate-700'}`} />
              <span className={`text-[10px] font-bold uppercase px-1.5 py-0.2 rounded ${
                selectedCategory === 'audit_register' ? 'bg-teal-900 text-teal-200' : 'bg-slate-200 text-slate-700'
              }`}>
                ISA 230
              </span>
            </div>
            <div className="font-bold text-xs">Audit Register</div>
            <div className={`text-[11px] mt-0.5 line-clamp-1 ${selectedCategory === 'audit_register' ? 'text-teal-200' : 'text-slate-400'}`}>
              SHA-256 Verified
            </div>
          </button>
        </div>
      </div>

      {/* Filter / Employee Selector Bar */}
      {(selectedCategory === 'appraisal' || selectedCategory === 'matrix' || selectedCategory === 'statutory') && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-slate-700">Select Practice Auditor:</span>
            <select
              value={selectedEmpId}
              onChange={(e) => setSelectedEmpId(e.target.value)}
              className="text-xs py-1.5 px-3 rounded-lg border border-slate-200 bg-slate-50 font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
            >
              {allUsers.filter((u) => u.role === 'employee').map((u) => (
                <option key={u.id} value={u.id}>
                  {u.fullName} ({u.employeeIdCode}) — {u.departmentName}
                </option>
              ))}
            </select>
          </div>

          {selectedCategory === 'statutory' && (
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-slate-700">Notice Tier:</span>
              <select
                value={selectedNoticeId}
                onChange={(e) => setSelectedNoticeId(e.target.value)}
                className="text-xs py-1.5 px-3 rounded-lg border border-slate-200 bg-slate-50 font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
              >
                {statutoryNotices.map((n) => (
                  <option key={n.id} value={n.id}>
                    Tier {n.tier}: {n.noticeTitle.slice(0, 45)}...
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="text-xs text-slate-500 font-mono">
            Ref: <strong className="text-slate-800">{currentRef}</strong>
          </div>
        </div>
      )}

      {/* Live Document Preview Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-md overflow-hidden">
        <div className="p-4 bg-slate-900 text-white flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-400 inline-block animate-pulse" />
            <span className="font-bold tracking-wide uppercase text-slate-200">Official Report Preview (Live Render)</span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400">Ready for instant Word (.doc) or PDF export</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadWord}
              className="px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-[11px] transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" /> Word (.doc)
            </button>
            <button
              onClick={handleDownloadPdf}
              className="px-3 py-1.5 rounded-md bg-teal-600 hover:bg-teal-700 text-white font-semibold text-[11px] transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <Printer className="w-3.5 h-3.5" /> PDF (.pdf)
            </button>
          </div>
        </div>

        <div className="p-8 sm:p-12 bg-white max-w-4xl mx-auto border-x border-slate-100 min-h-[500px]">
          <div className="border-b-4 border-blue-900 pb-4 mb-6 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <div className="text-xl font-black text-blue-950 tracking-tight uppercase">
                PARAS ACCOUNTING & AUDITING ADVISORY
              </div>
              <div className="text-xs text-slate-500 mt-1 leading-relaxed">
                Abu Dhabi Global Market (ADGM) & UAE MOHRE Registered Practice<br />
                Al Maryah Tower, Floors 24-25, Abu Dhabi, United Arab Emirates<br />
                Statutory Governance: UAE Federal Decree-Law No. 33 of 2021
              </div>
            </div>
            <div className="text-right text-xs text-slate-500 font-mono">
              <div><strong>Ref:</strong> {currentRef}</div>
              <div><strong>Cycle:</strong> Q3-2026 Evaluation</div>
              <div><strong>Jurisdiction:</strong> Abu Dhabi, UAE</div>
            </div>
          </div>

          <h2 className="text-xl font-extrabold text-slate-900 pb-2 border-b-2 border-teal-600">
            {currentTitle}
          </h2>
          <p className="text-xs text-slate-500 mt-1 mb-6">
            {currentSubtitle}
          </p>

          <div 
            className="prose prose-slate max-w-none text-xs leading-relaxed"
            dangerouslySetInnerHTML={{ __html: currentHtml }}
          />

          <div className="mt-14 pt-6 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-6 text-center text-xs">
            <div>
              <div className="h-10 border-b border-dashed border-slate-300"></div>
              <div className="font-bold text-slate-800 mt-2">
                {selectedCategory === 'firm_analytics' ? 'Mansoor Al Nuaimi' : selectedEmployee?.fullName || 'Evaluated Specialist'}
              </div>
              <div className="text-[11px] text-slate-400">
                {selectedCategory === 'firm_analytics' ? 'Senior Managing Partner' : 'Specialist Signature & Date'}
              </div>
            </div>
            <div>
              <div className="h-10 border-b border-dashed border-slate-300"></div>
              <div className="font-bold text-slate-800 mt-2">Tariq Al Hammadi</div>
              <div className="text-[11px] text-slate-400">Audit Partner & Practice Leader</div>
            </div>
            <div>
              <div className="h-10 border-b border-dashed border-slate-300"></div>
              <div className="font-bold text-slate-800 mt-2">Mariam Al Shamsi</div>
              <div className="text-[11px] text-slate-400">Head of Human Capital & Governance</div>
            </div>
          </div>

          <div className="mt-10 pt-4 border-t border-slate-100 text-center text-[10px] text-slate-400">
            Paras Accounting & Auditing Advisory • 2026 • Confidential Internal Record • Authorized under UAE Labor Law & ADGM Practice Directives
          </div>
        </div>
      </div>
    </div>
  );
};
