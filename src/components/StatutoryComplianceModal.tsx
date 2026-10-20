import React from 'react';
import { User, StatutoryNotice } from '../types';
import { MOCK_STATUTORY_NOTICES, MOCK_USERS, MOCK_COMPANY_INFO } from '../data/mockData';
import { 
  X, 
  FileText, 
  Printer, 
  Download, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Calendar,
  Building2,
  Scale
} from 'lucide-react';
import { exportToWord, exportToPdf, generateStatutoryNoticeHtml } from '../utils/reportExporter';

interface StatutoryComplianceModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedEmployeeId?: string;
}

export const StatutoryComplianceModal: React.FC<StatutoryComplianceModalProps> = ({
  isOpen,
  onClose,
  selectedEmployeeId,
}) => {
  const [activeTier, setActiveTier] = React.useState<1 | 2 | 3 | 4>(2);
  const [selectedEmpId, setSelectedEmpId] = React.useState<string>(selectedEmployeeId || 'emp-salim');
  const [isCopied, setIsCopied] = React.useState(false);

  React.useEffect(() => {
    if (selectedEmployeeId) {
      setSelectedEmpId(selectedEmployeeId);
      if (selectedEmployeeId === 'emp-omar') setActiveTier(1);
      else if (selectedEmployeeId === 'emp-salim') setActiveTier(2);
      else setActiveTier(1);
    }
  }, [selectedEmployeeId]);

  if (!isOpen) return null;

  const currentEmp = MOCK_USERS.find((u) => u.id === selectedEmpId) || MOCK_USERS[3];

  const getTierDetails = (tier: 1 | 2 | 3 | 4) => {
    switch (tier) {
      case 1:
        return {
          title: 'Notice of Constructive Skill Upgrade Plan',
          refCode: `PAA-HC-2026-T1-${currentEmp.employeeIdCode.replace('EMP-', '')}`,
          legalBasis: 'Paras Advisory Internal Talent Governance & UAE Labor Law Article 27 (Continuous Professional Development)',
          summary: 'In accordance with our Growth-First appraisal doctrine, this collaborative Skill Upgrade Plan is enacted to provide sponsored technical mentorship following a quarterly delivery delta. This notice carries ZERO adverse financial impact or disciplinary penalty.',
          obligations: [
            'Enrollment in sponsored ADGM/ICAEW accredited training module within 14 calendar days.',
            'Bi-weekly technical peer mentoring with Senior Practice Specialist.',
            'Target turnaround SLA recovery to ≥ 90% for subsequent quarterly closing.',
          ],
          supervisoryLead: 'Tariq Al Hammadi (Audit Partner & Practice Leader)',
          periodDays: 45,
          statutoryTone: 'Non-Adverse & Developmental',
          toneBadgeClass: 'bg-teal-50 text-teal-800 border-teal-200',
        };
      case 2:
        return {
          title: 'Performance Improvement Agreement (Constructive 60-Day PIP)',
          refCode: `PAA-HC-2026-T2-${currentEmp.employeeIdCode.replace('EMP-', '')}`,
          legalBasis: 'UAE Federal Decree-Law No. 33 of 2021 & MOHRE Executive Standards (Article 29 - Performance Standards)',
          summary: 'Formal notice of a structured 60-day Performance Improvement Plan following consecutive evaluation cycle review. Formulated with clear, objective milestones and dedicated partner coaching to ensure successful turnaround.',
          obligations: [
            'Mandatory weekly 1-on-1 milestone review with practice partner.',
            'Resolution of client delivery backlogs to achieve ≥ 95% SLA adherence within 30 days.',
            'Completion of accredited technical methodology refresher course.',
          ],
          supervisoryLead: 'Rashid Al Mehairbi (Senior Tax & Advisory Partner)',
          periodDays: 60,
          statutoryTone: 'Structured Remediation with Mentorship',
          toneBadgeClass: 'bg-amber-50 text-amber-800 border-amber-200',
        };
      case 3:
        return {
          title: 'Formal Statutory Review & Performance Notice (Cycle 3)',
          refCode: `PAA-HC-2026-T3-${currentEmp.employeeIdCode.replace('EMP-', '')}`,
          legalBasis: 'UAE Federal Decree-Law No. 33 of 2021, Article 44 / Executive Regulations Article 29',
          summary: 'Formal statutory warning following three consecutive review cycles failing to meet baseline objective criteria despite structured mentoring. Triggers temporary freeze on discretionary merit increments and mandatory Human Capital committee review.',
          obligations: [
            'Final 30-day accelerated performance benchmark audit.',
            'Formal presentation to Practice Quality Review Committee.',
            'Assessment of core audit competency retention or internal practice re-assignment.',
          ],
          supervisoryLead: 'Mariam Al Shamsi (Head of Human Capital & Governance)',
          periodDays: 30,
          statutoryTone: 'Formal Warning / Statutory Review',
          toneBadgeClass: 'bg-rose-50 text-rose-800 border-rose-200',
        };
      case 4:
        return {
          title: 'Final Management Review Flag & Statutory Committee Hearing',
          refCode: `PAA-HC-2026-T4-${currentEmp.employeeIdCode.replace('EMP-', '')}`,
          legalBasis: 'UAE Federal Decree-Law No. 33 of 2021, Articles 43 & 44 (Statutory Notice & Written Investigation)',
          summary: 'Formal notification convening the Executive Managing Board and HR Committee for final determination regarding structural practice re-assignment, grade step reduction, or statutory mutual separation in strict adherence to UAE MOHRE directives.',
          obligations: [
            'Notice of statutory hearing before the Executive Governance Board.',
            'Right to employee written statement & representative witness accompaniment.',
            'Audit of end-of-service gratuity and contractual entitlements in compliance with UAE Labor Law.',
          ],
          supervisoryLead: 'Mansoor Al Nuaimi (Senior Managing Partner & Chief Executive)',
          periodDays: 14,
          statutoryTone: 'Final Statutory Determination',
          toneBadgeClass: 'bg-red-100 text-red-950 border-red-300',
        };
    }
  };

  const currentNotice = getTierDetails(activeTier);

  const handleDownloadWord = () => {
    const noticeObj: any = {
      id: `notice-${currentNotice.refCode}`,
      employeeId: currentEmp.id,
      employeeName: currentEmp.fullName,
      tier: activeTier,
      noticeTitle: currentNotice.title,
      dateIssued: '2026-10-10',
      statutoryReference: currentNotice.legalBasis,
      summaryText: currentNotice.summary,
      actionRequirements: currentNotice.obligations,
      mentorshipSupervisor: currentNotice.supervisoryLead,
      timelineDays: currentNotice.periodDays,
      officialRefCode: currentNotice.refCode,
      status: 'Active',
    };
    const html = generateStatutoryNoticeHtml(noticeObj, currentEmp, MOCK_COMPANY_INFO);
    exportToWord({
      title: currentNotice.title,
      subtitle: `Statutory Notice under UAE Federal Decree-Law No. 33 of 2021 • Tier ${activeTier}`,
      filename: `Statutory_Notice_Tier${activeTier}_${currentEmp.fullName.replace(/\s+/g, '_')}`,
      officialRefCode: currentNotice.refCode,
      contentHtml: html,
    });
  };

  const handleDownloadPdf = () => {
    const noticeObj: any = {
      id: `notice-${currentNotice.refCode}`,
      employeeId: currentEmp.id,
      employeeName: currentEmp.fullName,
      tier: activeTier,
      noticeTitle: currentNotice.title,
      dateIssued: '2026-10-10',
      statutoryReference: currentNotice.legalBasis,
      summaryText: currentNotice.summary,
      actionRequirements: currentNotice.obligations,
      mentorshipSupervisor: currentNotice.supervisoryLead,
      timelineDays: currentNotice.periodDays,
      officialRefCode: currentNotice.refCode,
      status: 'Active',
    };
    const html = generateStatutoryNoticeHtml(noticeObj, currentEmp, MOCK_COMPANY_INFO);
    exportToPdf({
      title: currentNotice.title,
      subtitle: `Statutory Notice under UAE Federal Decree-Law No. 33 of 2021 • Tier ${activeTier}`,
      filename: `Statutory_Notice_Tier${activeTier}_${currentEmp.fullName.replace(/\s+/g, '_')}`,
      officialRefCode: currentNotice.refCode,
      contentHtml: html,
    });
  };

  const handleCopy = () => {
    const textToCopy = `
PARAS ACCOUNTING & AUDITING ADVISORY
Abu Dhabi, United Arab Emirates • Registered Audit Practice
STATUTORY DOCUMENT: ${currentNotice.title}
Reference: ${currentNotice.refCode}
Date: 2026-10-10
Employee: ${currentEmp.fullName} (${currentEmp.employeeIdCode})
Department: ${currentEmp.departmentName}
Designation: ${currentEmp.currentDesignation}

LEGAL CITATION: ${currentNotice.legalBasis}
SUMMARY: ${currentNotice.summary}

OBLIGATIONS:
${currentNotice.obligations.map((o, idx) => `${idx + 1}. ${o}`).join('\n')}

Supervisory Lead: ${currentNotice.supervisoryLead}
Statutory Review Period: ${currentNotice.periodDays} Days
    `;
    navigator.clipboard.writeText(textToCopy);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-rose-700 text-white flex items-center justify-center font-bold">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 leading-tight">
                UAE Labor Law Statutory Compliance Generator
              </h2>
              <p className="text-xs text-slate-500">
                Official Bilingual Notices under UAE Federal Decree-Law No. 33 of 2021
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Configuration Bar */}
        <div className="p-4 bg-white border-b border-slate-100 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-700">Auditor:</span>
            <select
              value={selectedEmpId}
              onChange={(e) => setSelectedEmpId(e.target.value)}
              className="text-xs py-1.5 px-3 rounded-lg border border-slate-200 font-medium text-slate-800 bg-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
            >
              {MOCK_USERS.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.fullName} ({u.employeeIdCode}) — {u.currentDesignation}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
            <button
              onClick={() => setActiveTier(1)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                activeTier === 1
                  ? 'bg-white text-teal-800 font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Tier 1 (Skill Upgrade)
            </button>
            <button
              onClick={() => setActiveTier(2)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                activeTier === 2
                  ? 'bg-white text-amber-800 font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Tier 2 (60-Day PIP)
            </button>
            <button
              onClick={() => setActiveTier(3)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                activeTier === 3
                  ? 'bg-white text-rose-800 font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Tier 3 (Formal Review)
            </button>
            <button
              onClick={() => setActiveTier(4)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                activeTier === 4
                  ? 'bg-white text-red-900 font-bold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Tier 4 (Final Hearing)
            </button>
          </div>
        </div>

        {/* Document Body */}
        <div className="p-6 md:p-8 overflow-y-auto flex-1 bg-slate-50/50">
          <div className="max-w-2xl mx-auto bg-white border border-slate-200 rounded-xl p-8 shadow-sm space-y-6 text-slate-900">
            <div className="border-b-2 border-slate-900 pb-5 flex justify-between items-start">
              <div>
                <h1 className="text-xl font-extrabold tracking-tight text-slate-950 uppercase">
                  Paras Accounting & Auditing Advisory
                </h1>
                <p className="text-xs text-slate-500 font-medium">
                  Registered Auditing Practice • Abu Dhabi Global Market (ADGM) & MOHRE
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Al Maryah Tower, Floors 24-25, Abu Dhabi, United Arab Emirates
                </p>
              </div>
              <div className="text-right text-xs">
                <span className={`px-2.5 py-1 rounded font-bold border text-[10px] uppercase tracking-wider ${currentNotice.toneBadgeClass}`}>
                  {currentNotice.statutoryTone}
                </span>
                <div className="text-[11px] text-slate-500 font-mono mt-2 tabular-nums">
                  Ref: {currentNotice.refCode}
                </div>
                <div className="text-[11px] text-slate-400">Date: October 10, 2026</div>
              </div>
            </div>

            <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 text-xs grid grid-cols-2 gap-3">
              <div>
                <span className="text-slate-400 block text-[11px]">Employee Name:</span>
                <span className="font-bold text-slate-900">{currentEmp.fullName}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Employee ID Code:</span>
                <span className="font-mono font-semibold text-slate-900">{currentEmp.employeeIdCode}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Practice Department:</span>
                <span className="font-semibold text-slate-800">{currentEmp.departmentName}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Current Designation:</span>
                <span className="font-semibold text-slate-800">{currentEmp.currentDesignation}</span>
              </div>
            </div>

            <div>
              <h3 className="text-base font-bold text-slate-950 uppercase tracking-wide">
                {currentNotice.title}
              </h3>
              <div className="text-xs text-rose-800 font-semibold mt-1 flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5" />
                <span>Statutory Authority: {currentNotice.legalBasis}</span>
              </div>
            </div>

            <div className="text-xs text-slate-700 leading-relaxed space-y-3">
              <p>{currentNotice.summary}</p>
              <p className="font-bold text-slate-900 pt-1">
                Agreed Action Plan & Core Deliverables:
              </p>
              <ul className="space-y-2 list-none">
                {currentNotice.obligations.map((ob, idx) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center shrink-0 text-[10px]">
                      {idx + 1}
                    </span>
                    <span className="text-slate-800">{ob}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-4 border-t border-slate-100 grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Designated Mentorship Supervisor:</span>
                <span className="font-bold text-slate-900">{currentNotice.supervisoryLead}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Mandatory Review Period:</span>
                <span className="font-bold text-teal-800 tabular-nums">{currentNotice.periodDays} Calendar Days</span>
              </div>
            </div>

            <div className="pt-6 border-t border-slate-200 grid grid-cols-2 gap-8 text-xs">
              <div className="space-y-6">
                <div>
                  <span className="text-slate-400 block text-[11px]">Authorized by Human Capital:</span>
                  <div className="font-semibold text-slate-900 mt-1">Mariam Al Shamsi</div>
                  <div className="text-[11px] text-slate-500">Director of Human Capital & Governance</div>
                </div>
                <div className="h-9 border-b border-slate-300 flex items-end">
                  <span className="text-[10px] text-slate-400 font-mono italic">Electronic Signature: PAA-HC-OK-2026</span>
                </div>
              </div>
              <div className="space-y-6">
                <div>
                  <span className="text-slate-400 block text-[11px]">Employee Acknowledgment:</span>
                  <div className="font-semibold text-slate-900 mt-1">{currentEmp.fullName}</div>
                  <div className="text-[11px] text-slate-500">I acknowledge receipt of this development plan</div>
                </div>
                <div className="h-9 border-b border-slate-300 flex items-end">
                  <span className="text-[10px] text-slate-400 font-mono italic">Signature: __________________________</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 bg-white border-t border-slate-200 flex items-center justify-between">
          <div className="text-xs text-slate-500">
            Document generated in compliance with UAE Federal Decree-Law No. 33 of 2021
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleCopy}
              className="px-3.5 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              {isCopied ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                  Copied Text!
                </>
              ) : (
                <>
                  <FileText className="w-3.5 h-3.5" />
                  Copy Text
                </>
              )}
            </button>
            <button
              onClick={handleDownloadWord}
              className="px-3.5 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              title="Download official letter in Microsoft Word (.doc) format"
            >
              <Download className="w-3.5 h-3.5" />
              Word (.doc)
            </button>
            <button
              onClick={handleDownloadPdf}
              className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              title="Print or Save official letter as PDF"
            >
              <Printer className="w-3.5 h-3.5" />
              Print / Save PDF
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
