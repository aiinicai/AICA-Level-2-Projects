import React from 'react';
import { User, ProfessionalCertification } from '../types';
import { 
  Award, 
  DollarSign, 
  CheckCircle2, 
  Clock, 
  PlusCircle, 
  ShieldCheck, 
  Sparkles,
  FileCheck,
  Send,
  AlertCircle
} from 'lucide-react';

interface CertificationBonusPanelProps {
  currentUser: User;
  employeeUser: User;
  certifications: ProfessionalCertification[];
  onProposeCertification: (cert: Omit<ProfessionalCertification, 'id'>) => void;
  onApproveCertification: (certId: string, notes: string) => void;
  onVerifyAndDisburseBonus: (certId: string) => void;
}

export const CertificationBonusPanel: React.FC<CertificationBonusPanelProps> = ({
  currentUser,
  employeeUser,
  certifications,
  onProposeCertification,
  onApproveCertification,
  onVerifyAndDisburseBonus,
}) => {
  const isManagerOrAdmin = currentUser.role === 'department_manager' || currentUser.role === 'super_admin' || currentUser.role === 'hr_manager';
  const isEmployee = currentUser.id === employeeUser.id;

  const [showProposeModal, setShowProposeModal] = React.useState<boolean>(false);
  const [certName, setCertName] = React.useState<string>('ACA / ACCA Senior Chartered Fellowship');
  const [issuingBody, setIssuingBody] = React.useState<string>('ICAEW Middle East & ACCA Global');
  const [notification, setNotification] = React.useState<string | null>(null);

  const employeeCerts = certifications.filter((c) => c.employeeId === employeeUser.id);
  const totalBonusesEarned = employeeCerts
    .filter((c) => c.status === 'Completed_Verified' || c.status === 'Bonus_Disbursed')
    .reduce((acc, curr) => acc + curr.bonusAmountAED, 0);

  const handleProposeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onProposeCertification({
      employeeId: employeeUser.id,
      employeeName: employeeUser.fullName,
      certificationName: certName,
      issuingBody,
      status: 'Proposed',
      bonusAmountAED: 15000,
      managerApprovalNotes: 'Awaiting practice partner approval.',
    });
    setShowProposeModal(false);
    setNotification('Certification proposed to practice partner for formal sponsorship approval.');
    setTimeout(() => setNotification(null), 3500);
  };

  const handleApprove = (certId: string) => {
    onApproveCertification(certId, `Approved by ${currentUser.fullName}. Entitled to AED 15,000 bonus upon completion.`);
    setNotification('Certification track approved! Auditor is entitled to AED 15,000.00 upon verified completion.');
    setTimeout(() => setNotification(null), 3500);
  };

  const handleDisburse = (certId: string) => {
    onVerifyAndDisburseBonus(certId);
    setNotification('Special Bonus of AED 15,000.00 verified and authorized for disbursement in payroll!');
    setTimeout(() => setNotification(null), 4000);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Incentive Callout */}
      <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 rounded-2xl p-6 text-white border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-bold text-teal-400 uppercase tracking-wider">
            <Award className="w-4 h-4 text-teal-400" />
            <span>Chartered Excellence Incentive Program</span>
          </div>
          <h2 className="text-xl font-extrabold tracking-tight">
            Professional Certification Sponsorship & AED 15,000 Bonus
          </h2>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            Paras Accounting & Auditing Advisory entitles employees to a special one-time bonus of <strong>AED 15,000.00</strong> upon successful completion of manager-approved professional credentials.
          </p>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="p-3.5 rounded-xl bg-teal-500/10 border border-teal-500/30 text-right">
            <span className="text-[10px] text-teal-300 uppercase tracking-wider font-semibold block">Bonus Disbursed to Date</span>
            <span className="text-2xl font-black text-teal-400 tabular-nums">
              AED {totalBonusesEarned.toLocaleString()}
            </span>
          </div>
          {(isEmployee || isManagerOrAdmin) && (
            <button
              onClick={() => setShowProposeModal(true)}
              className="px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs transition-colors flex items-center gap-1.5 shadow-md cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              Propose Certification
            </button>
          )}
        </div>
      </div>

      {notification && (
        <div className="p-3 bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold rounded-lg flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Certifications Roster */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              {employeeUser.fullName} • Active Certification & Bonus Portfolio
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Approved credentials eligible for AED 15,000 one-time special merit payment
            </p>
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {employeeCerts.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No certifications proposed yet. Click "Propose Certification" to apply for the AED 15,000 sponsorship program.
            </div>
          ) : (
            employeeCerts.map((c) => (
              <div key={c.id} className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/50 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{c.certificationName}</span>
                    <span className="text-xs text-slate-400">•</span>
                    <span className="text-xs text-slate-600">{c.issuingBody}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="font-semibold text-teal-700 tabular-nums">Entitlement: AED {c.bonusAmountAED.toLocaleString()}</span>
                    {c.bonusPaidDate && (
                      <>
                        <span aria-hidden="true">•</span>
                        <span className="text-emerald-700 font-medium">Disbursed on {c.bonusPaidDate}</span>
                      </>
                    )}
                  </div>
                  {c.managerApprovalNotes && (
                    <p className="text-[11px] text-slate-500 italic mt-1">"{c.managerApprovalNotes}"</p>
                  )}
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-md border ${
                    c.status === 'Bonus_Disbursed'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : c.status === 'Completed_Verified'
                      ? 'bg-teal-50 text-teal-800 border-teal-200'
                      : c.status === 'Manager_Approved'
                      ? 'bg-blue-50 text-blue-800 border-blue-200'
                      : 'bg-slate-100 text-slate-700 border-slate-200'
                  }`}>
                    {c.status.replace(/_/g, ' ')}
                  </span>

                  {isManagerOrAdmin && c.status === 'Proposed' && (
                    <button
                      onClick={() => handleApprove(c.id)}
                      className="px-3 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs cursor-pointer"
                    >
                      Approve Track
                    </button>
                  )}

                  {isManagerOrAdmin && c.status === 'Completed_Verified' && (
                    <button
                      onClick={() => handleDisburse(c.id)}
                      className="px-3.5 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs flex items-center gap-1 shadow-xs cursor-pointer"
                    >
                      <DollarSign className="w-3.5 h-3.5" />
                      Disburse AED 15,000 Bonus
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Propose Modal */}
      {showProposeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg p-6 space-y-4 text-xs animate-in fade-in">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Propose Professional Certification
            </h3>
            <p className="text-slate-500">
              Submit your credential target for manager review and AED 15,000 bonus entitlement.
            </p>
            <form onSubmit={handleProposeSubmit} className="space-y-3">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Certification Name:</label>
                <select
                  value={certName}
                  onChange={(e) => {
                    setCertName(e.target.value);
                    if (e.target.value.includes('ACCA') || e.target.value.includes('ACA')) {
                      setIssuingBody('ICAEW Middle East & ACCA Global');
                    } else if (e.target.value.includes('Tax')) {
                      setIssuingBody('Federal Tax Authority (FTA) UAE');
                    } else if (e.target.value.includes('Fraud')) {
                      setIssuingBody('Association of Certified Fraud Examiners (ACFE)');
                    } else if (e.target.value.includes('CFA')) {
                      setIssuingBody('CFA Institute');
                    } else {
                      setIssuingBody('AICPA & NASBA');
                    }
                  }}
                  className="w-full p-2 border border-slate-200 rounded-lg text-xs bg-white"
                >
                  <option value="ACA / ACCA Senior Chartered Fellowship">ACA / ACCA Senior Chartered Fellowship</option>
                  <option value="UAE Federal Tax Authority (FTA) Certified Tax Agent">UAE Federal Tax Authority (FTA) Certified Tax Agent</option>
                  <option value="Certified Fraud Examiner (CFE)">Certified Fraud Examiner (CFE)</option>
                  <option value="Certified Public Accountant (CPA US)">Certified Public Accountant (CPA US)</option>
                  <option value="Chartered Financial Analyst (CFA Level III)">Chartered Financial Analyst (CFA Level III)</option>
                </select>
              </div>
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Issuing Accredited Body:</label>
                <input
                  type="text"
                  value={issuingBody}
                  onChange={(e) => setIssuingBody(e.target.value)}
                  className="w-full p-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>
              <div className="p-3 bg-teal-50 border border-teal-200 rounded-lg text-teal-800 text-xs">
                <strong>Bonus Guarantee:</strong> Upon manager approval and credential verification, employee will receive a one-time special bonus of <strong>AED 15,000.00</strong>.
              </div>
              <div className="pt-2 flex justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowProposeModal(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold cursor-pointer"
                >
                  Submit for Approval
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
