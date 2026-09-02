import React, { useState } from 'react';
import { 
  X, 
  ChevronRight, 
  ChevronLeft, 
  Sparkles, 
  ShieldCheck, 
  Layers, 
  QrCode, 
  AlertTriangle, 
  ClipboardCheck, 
  CheckCircle2, 
  ArrowRight,
  BookOpen
} from 'lucide-react';
import { NavTab } from './Navbar';

interface QuickStartGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateTab: (tab: NavTab) => void;
  onOpenManual: () => void;
}

export const QuickStartGuideModal: React.FC<QuickStartGuideModalProps> = ({
  isOpen,
  onClose,
  onNavigateTab,
  onOpenManual
}) => {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const steps = [
    {
      title: 'Welcome to AssetTrust AI',
      subtitle: 'Continuous Fixed Asset Subledger Integrity & CARO Compliance',
      icon: ShieldCheck,
      badge: 'Overview',
      color: 'blue',
      content: (
        <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
          <p>
            <strong className="text-slate-900">AssetTrust AI</strong> is an enterprise governance and internal controls platform for CFOs, Financial Controllers, and Statutory Auditors.
          </p>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2">
            <span className="font-bold text-slate-900 block text-xs">Core Value Pillars:</span>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="flex items-center space-x-1.5 text-slate-700">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Ind AS 16 Componentisation</span>
              </div>
              <div className="flex items-center space-x-1.5 text-slate-700">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>CARO 2020 Clause 3(i) Assurance</span>
              </div>
              <div className="flex items-center space-x-1.5 text-slate-700">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Mobile QR Physical Verification</span>
              </div>
              <div className="flex items-center space-x-1.5 text-slate-700">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>Dual Books Depreciation (Books vs Tax)</span>
              </div>
            </div>
          </div>
        </div>
      ),
      action: {
        label: 'Explore Control Tower',
        tab: 'control-tower' as NavTab
      }
    },
    {
      title: '1. Executive Control Tower & Reliability Index',
      subtitle: 'Real-time 0–100 health index measuring asset assurance',
      icon: ShieldCheck,
      badge: 'Governance',
      color: 'blue',
      content: (
        <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
          <p>
            The <strong className="text-slate-900">Asset Reliability Score</strong> aggregates 5 fundamental sub-drivers: Physical Verification, Document Completeness, Subledger Reconciliation, Policy Compliance, and Anomaly Velocity.
          </p>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-1.5 text-[11px]">
            <span className="font-bold text-slate-900 block">What to look for:</span>
            <ul className="list-disc list-inside space-y-1 text-slate-600">
              <li>High-level Net Book Value (NBV) and Gross Block metrics in ₹ Crores or Lakhs.</li>
              <li>Multi-Plant health scores across Pune, Chennai, Manesar, and Sanand.</li>
              <li>Immediate statutory compliance status for CARO 2020 and Ind AS 16.</li>
            </ul>
          </div>
        </div>
      ),
      action: {
        label: 'Open Control Tower',
        tab: 'control-tower' as NavTab
      }
    },
    {
      title: '2. AI Capitalisation Review & Ind AS 16 Split',
      subtitle: 'Automated 3-way match, component splits & human approval',
      icon: Sparkles,
      badge: 'Procurement',
      color: 'blue',
      content: (
        <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
          <p>
            Ingest inbound Capex procurement items (PO, GRN, Tax Invoices) and let AI analyze them against <strong className="text-slate-900">Ind AS 16 Para 43</strong> and <strong className="text-slate-900">Schedule II</strong>.
          </p>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-1.5 text-[11px]">
            <span className="font-bold text-slate-900 block">Try this workflow:</span>
            <p className="text-slate-600">
              Select an item from the Capex Queue, review the AI component split (e.g. Machine Bed vs Spindle vs CNC Controller), choose an approver, and click <em>"Approve & Capitalise"</em> to push into the live register.
            </p>
          </div>
        </div>
      ),
      action: {
        label: 'Try Capex Review',
        tab: 'capex-review' as NavTab
      }
    },
    {
      title: '3. Field Verification Ops & Shop Floor QR Scanner',
      subtitle: 'Mobile QR scanning with GPS stamping & variance logging',
      icon: QrCode,
      badge: 'Field Ops',
      color: 'emerald',
      content: (
        <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
          <p>
            Field auditors and plant custodians use digital QR matrix scanning to verify physical presence, check OEM serial numbers, and detect location drift.
          </p>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-1.5 text-[11px]">
            <span className="font-bold text-slate-900 block">Discrepancy Auto-Escalation:</span>
            <p className="text-slate-600">
              Any variance (e.g. asset scanned in Chennai instead of Pune, or missing nameplate) is instantly flagged in the Risk Radar and routed to the Exception Kanban for investigation.
            </p>
          </div>
        </div>
      ),
      action: {
        label: 'Open Field Terminal',
        tab: 'physical-verification' as NavTab
      }
    },
    {
      title: '4. Anomaly Radar & Exception Kanban Workflow',
      subtitle: 'Deterministic risk detection and 6-stage remediation',
      icon: AlertTriangle,
      badge: 'Risk Control',
      color: 'amber',
      content: (
        <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
          <p>
            Detects ghost assets, duplicate capitalisations, scrap variances, and Ind AS 36 impairment indicators with quantified financial exposure.
          </p>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-1.5 text-[11px]">
            <span className="font-bold text-slate-900 block">Formal Governance Pipeline:</span>
            <p className="text-slate-600">
              Move findings from <em>Detected → Assigned → Under Investigation → Management Review → Board Sign-off → Closed</em> with complete audit trails.
            </p>
          </div>
        </div>
      ),
      action: {
        label: 'View Risk Radar',
        tab: 'risk-radar' as NavTab
      }
    },
    {
      title: '5. CARO 2020 Statutory Audit Readiness Pack',
      subtitle: 'Executive audit memorandum & Big-4 workpapers generator',
      icon: ClipboardCheck,
      badge: 'Assurance',
      color: 'blue',
      content: (
        <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
          <p>
            Prepare for statutory audits by Deloitte, EY, PwC, or KPMG with automated evidence dossiers, 10% discrepancy checks under CARO Clause 3(i)(b), and AI-generated audit memos.
          </p>
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-1.5 text-[11px]">
            <span className="font-bold text-slate-900 block">Deliverables Generated:</span>
            <p className="text-slate-600">
              Subledger vs GL tie-out, Title deeds register, Componentisation files, and Executive Audit Summary memos with Markdown and PDF export.
            </p>
          </div>
        </div>
      ),
      action: {
        label: 'Open Audit Readiness',
        tab: 'audit-readiness' as NavTab
      }
    }
  ];

  const current = steps[currentStep];
  const Icon = current.icon;

  const handleStepAction = () => {
    onNavigateTab(current.action.tab);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col text-slate-800 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-100 bg-slate-50 flex items-start justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                  {current.badge} • Step {currentStep + 1} of {steps.length}
                </span>
              </div>
              <h2 className="text-base font-bold text-slate-900 mt-0.5">{current.title}</h2>
              <p className="text-xs text-slate-500">{current.subtitle}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-100 h-1">
          <div 
            className="bg-blue-600 h-1 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
          ></div>
        </div>

        {/* Body Content */}
        <div className="p-6 space-y-4">
          {current.content}
        </div>

        {/* Footer Navigation */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <button
              onClick={onOpenManual}
              className="text-blue-600 hover:text-blue-800 font-semibold flex items-center space-x-1"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Full User Manual</span>
            </button>
          </div>

          <div className="flex items-center space-x-2">
            {currentStep > 0 && (
              <button
                onClick={() => setCurrentStep((prev) => prev - 1)}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg flex items-center space-x-1 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Back</span>
              </button>
            )}

            <button
              onClick={handleStepAction}
              className="px-3.5 py-1.5 bg-white hover:bg-blue-50 text-blue-700 border border-blue-200 font-bold rounded-lg flex items-center space-x-1 transition-colors shadow-2xs"
            >
              <span>{current.action.label}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            {currentStep < steps.length - 1 ? (
              <button
                onClick={() => setCurrentStep((prev) => prev + 1)}
                className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg flex items-center space-x-1 shadow-xs transition-colors"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={onClose}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-xs transition-colors"
              >
                Get Started
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
