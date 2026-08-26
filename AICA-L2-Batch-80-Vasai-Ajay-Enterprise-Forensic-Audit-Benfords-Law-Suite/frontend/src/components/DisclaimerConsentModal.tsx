import React, { useState } from 'react';
import { Shield, Lock, AlertOctagon, CheckCircle2, FileCheck } from 'lucide-react';

interface DisclaimerConsentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAcceptConsent: (data: {
    auditorName: string;
    organizationFiduciary: string;
    auditPurpose: string;
  }) => Promise<void>;
  initialAuditorName?: string;
  initialOrganization?: string;
}

export const DisclaimerConsentModal: React.FC<DisclaimerConsentModalProps> = ({
  isOpen,
  onClose,
  onAcceptConsent,
  initialAuditorName = "Senior Forensic Auditor",
  initialOrganization = "Enterprise Audit & Governance Council"
}) => {
  const [auditorName, setAuditorName] = useState(initialAuditorName);
  const [organization, setOrganization] = useState(initialOrganization);
  const [auditPurpose, setAuditPurpose] = useState("Statutory Forensic Financial Audit & Fraud Risk Assessment");
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [dpdpAccepted, setDpdpAccepted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disclaimerAccepted || !dpdpAccepted) {
      setErrorMsg("You must accept both the Disclaimer and the DPDP Governance Mandate to proceed.");
      return;
    }
    setErrorMsg("");
    setIsSubmitting(true);
    try {
      await onAcceptConsent({
        auditorName,
        organizationFiduciary: organization,
        auditPurpose
      });
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to record DPDP consent declaration.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl max-w-2xl w-full p-6 sm:p-8 relative">
        <div className="flex items-center gap-3 border-b border-slate-800 pb-4 mb-5">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <AlertOctagon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">
              Mandatory Legal Disclaimer &amp; DPDP Consent Declaration
            </h2>
            <p className="text-xs text-slate-400">
              Indian Digital Personal Data Protection Act, 2023 Statutory Compliance Protocol
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Disclaimer Box */}
          <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-300 space-y-2 max-h-48 overflow-y-auto leading-relaxed">
            <p className="font-semibold text-amber-300 flex items-center gap-1.5">
              <Shield className="w-4 h-4" /> STATUTORY FORENSIC &amp; RISK ADVISORY DISCLAIMER:
            </p>
            <p>
              1. <b>Advisory Nature:</b> This software performs algorithmic and statistical analysis based on Benford's Law,
              Nigrini Mean Absolute Deviation (MAD), Relative Size Factors, and mathematical pattern detection. Statistical
              deviations or anomaly triggers indicate areas warranting professional scrutiny and review by qualified Chartered
              Accountants / Certified Fraud Examiners.
            </p>
            <p>
              2. <b>Limitation of Liability:</b> The developer, publisher, and suite authors disclaim all liability for any direct,
              indirect, incidental, or consequential losses or damages arising from reliance on algorithmic findings. This app does not
              constitute formal legal advice or a judicial verdict.
            </p>
            <p>
              3. <b>Indian DPDP Act, 2023 Mandate:</b> Processing of audit logs adheres strictly to Sections 4, 7, and 8 of the
              Digital Personal Data Protection Act, 2023. Data processed remains local, in-memory, or pseudonymized via cryptographic
              salted HMAC-SHA256 tokens.
            </p>
          </div>

          {/* Form Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Lead Forensic Auditor / CA Name:
              </label>
              <input
                type="text"
                value={auditorName}
                onChange={(e) => setAuditorName(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                placeholder="e.g. CA Rajesh Sharma"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Data Fiduciary Entity / Firm:
              </label>
              <input
                type="text"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
                placeholder="e.g. KPMG / Forensic Division"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Specified Processing Purpose (DPDP Sec. 4):
            </label>
            <input
              type="text"
              value={auditPurpose}
              onChange={(e) => setAuditPurpose(e.target.value)}
              required
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* Checkboxes */}
          <div className="space-y-3 pt-2">
            <label className="flex items-start gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={disclaimerAccepted}
                onChange={(e) => setDisclaimerAccepted(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded bg-slate-950 border-slate-700 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-xs text-slate-300">
                I have read and agree to the <b>Statutory Forensic Disclaimer</b> regarding professional discretion,
                limitation of liability, and non-legal advisory status.
              </span>
            </label>

            <label className="flex items-start gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={dpdpAccepted}
                onChange={(e) => setDpdpAccepted(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded bg-slate-950 border-slate-700 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-xs text-slate-300">
                I authorize local processing under <b>Indian DPDP Act, 2023</b> purpose limitation, PII minimization,
                and blockchain-style tamper-evident audit logging.
              </span>
            </label>
          </div>

          {/* Action Button */}
          <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
            <button
              type="submit"
              disabled={isSubmitting || !disclaimerAccepted || !dpdpAccepted}
              className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-all flex items-center justify-center gap-2"
            >
              <FileCheck className="w-4 h-4" />
              {isSubmitting ? 'Recording Consent...' : 'Accept & Initialize Forensic Session'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
