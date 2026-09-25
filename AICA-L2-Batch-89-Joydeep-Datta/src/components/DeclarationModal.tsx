import React, { useState } from 'react';
import { X, Save, FileCheck2, Home, Shield, HeartPulse, Building2, Briefcase } from 'lucide-react';
import { EmployeeDeclaration, EmployeeMaster, TaxConfig } from '../types/payroll';

interface DeclarationModalProps {
  declaration?: EmployeeDeclaration | null;
  employees: EmployeeMaster[];
  taxConfig: TaxConfig;
  isOpen: boolean;
  onClose: () => void;
  onSave: (decl: EmployeeDeclaration) => void;
}

export const DeclarationModal: React.FC<DeclarationModalProps> = ({
  declaration,
  employees,
  taxConfig,
  isOpen,
  onClose,
  onSave,
}) => {
  if (!isOpen || !declaration) return null;

  const [formData, setFormData] = useState<EmployeeDeclaration>({ ...declaration });
  const [activeTab, setActiveTab] = useState<'regime' | 'hra' | '80c' | '80d' | 'prev'>('regime');

  const employee = employees.find((e) => e.employeeCode === formData.employeeCode);

  const handleChange = (field: keyof EmployeeDeclaration, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Tax Declaration — {employee?.employeeName || formData.employeeCode} ({formData.employeeCode})
            </h2>
            <p className="text-xs text-slate-500">
              Financial Year: {formData.financialYear} • Statutory deductions and proofs
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 bg-white px-6 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('regime')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              activeTab === 'regime'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileCheck2 className="h-3.5 w-3.5" /> Regime & Status
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('hra')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              activeTab === 'hra'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Home className="h-3.5 w-3.5" /> HRA & Home Loan 24(b)
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('80c')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              activeTab === '80c'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Shield className="h-3.5 w-3.5" /> Sec 80C & NPS
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('80d')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              activeTab === '80d'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <HeartPulse className="h-3.5 w-3.5" /> Sec 80D Mediclaim
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('prev')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              activeTab === 'prev'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Briefcase className="h-3.5 w-3.5" /> Previous Employer (Form 12B)
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1 space-y-4 text-xs">
          {activeTab === 'regime' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Tax Regime Declared for FY {formData.financialYear} *
                  </label>
                  <select
                    value={formData.regimeDeclared}
                    onChange={(e) => handleChange('regimeDeclared', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-bold text-slate-900 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="New">New Tax Regime (u/s 115BAC — Default)</option>
                    <option value="Old">Old Tax Regime (Allows deductions)</option>
                  </select>
                  <span className="text-[10px] text-slate-400">
                    Declaration regime will override the employee master profile.
                  </span>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Declaration Type *</label>
                  <select
                    value={formData.declarationType}
                    onChange={(e) => handleChange('declarationType', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="Proposed">Proposed (Beginning of Year / Estimates)</option>
                    <option value="Actual (Proofs Submitted)">Actual (Proofs Submitted)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Proof Verification Status</label>
                  <select
                    value={formData.proofStatus}
                    onChange={(e) => handleChange('proofStatus', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500 font-semibold"
                  >
                    <option value="Pending">Pending</option>
                    <option value="Submitted">Submitted</option>
                    <option value="Verified">Verified</option>
                    <option value="Partially Rejected">Partially Rejected</option>
                    <option value="Rejected">Rejected</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Declaration Date</label>
                  <input
                    type="date"
                    value={formData.declarationDate}
                    onChange={(e) => handleChange('declarationDate', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Remarks / Audit Note</label>
                <textarea
                  rows={2}
                  value={formData.remarks || ''}
                  onChange={(e) => handleChange('remarks', e.target.value)}
                  placeholder="e.g. Proofs verified on 10-Aug; rent receipt matched bank statement"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
          )}

          {activeTab === 'hra' && (
            <div className="space-y-4">
              <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-lg text-[11px] text-blue-900">
                <strong>Note:</strong> HRA exemptions and Housing Loan Interest (Sec 24b) are permitted under the{' '}
                <strong>Old Tax Regime only</strong>. Under the New Regime, these are disregarded per Sec 115BAC.
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Total Annual Rent Paid (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.rentPaidAnnual}
                    onChange={(e) => handleChange('rentPaidAnnual', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono font-bold"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Rented City (Metro Flag)</label>
                  <select
                    value={formData.rentedCityMetro}
                    onChange={(e) => handleChange('rentedCityMetro', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg"
                  >
                    <option value="Y">Metro (50% of Basic) — Mumbai/Delhi/Kol/Chn</option>
                    <option value="N">Non-Metro (40% of Basic)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Landlord Name</label>
                  <input
                    type="text"
                    value={formData.landlordName || ''}
                    onChange={(e) => handleChange('landlordName', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Landlord PAN {formData.rentPaidAnnual > 100000 && <span className="text-rose-600">*</span>}
                  </label>
                  <input
                    type="text"
                    maxLength={10}
                    placeholder="Mandatory if rent > ₹1,00,000"
                    value={formData.landlordPan || ''}
                    onChange={(e) => handleChange('landlordPan', e.target.value.toUpperCase())}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono uppercase"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Housing Loan Interest (Self-Occupied) u/s 24(b) (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.housingLoanInterestSelfOccupied}
                    onChange={(e) =>
                      handleChange('housingLoanInterestSelfOccupied', parseFloat(e.target.value) || 0)
                    }
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                  <span className="text-[10px] text-slate-400">Statutory setoff cap: ₹2,00,000</span>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Net Income / Loss from Let-Out Property (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.letOutPropertyNetIncome}
                    onChange={(e) =>
                      handleChange('letOutPropertyNetIncome', parseFloat(e.target.value) || 0)
                    }
                    placeholder="Negative for loss"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === '80c' && (
            <div className="space-y-4">
              <div className="p-3 bg-purple-50/60 border border-purple-200 rounded-lg text-[11px] text-purple-900">
                <strong>Sec 80C Limit:</strong> Maximum aggregate deduction is ₹1,50,000. Employee PF is automatically
                calculated from payroll and factored in.
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-700 mb-1">Housing Loan Principal</label>
                  <input
                    type="number"
                    value={formData.housingLoanPrincipal}
                    onChange={(e) => handleChange('housingLoanPrincipal', parseFloat(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 mb-1">Public Provident Fund (PPF)</label>
                  <input
                    type="number"
                    value={formData.ppf}
                    onChange={(e) => handleChange('ppf', parseFloat(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 mb-1">Life Insurance Premium (LIC)</label>
                  <input
                    type="number"
                    value={formData.licPremium}
                    onChange={(e) => handleChange('licPremium', parseFloat(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 mb-1">ELSS Mutual Funds</label>
                  <input
                    type="number"
                    value={formData.elssMutualFund}
                    onChange={(e) => handleChange('elssMutualFund', parseFloat(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 mb-1">Tuition Fees (Max 2 children)</label>
                  <input
                    type="number"
                    value={formData.tuitionFees}
                    onChange={(e) => handleChange('tuitionFees', parseFloat(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-700 mb-1">Tax Saver FD (5 years)</label>
                  <input
                    type="number"
                    value={formData.taxSaverFd5yr}
                    onChange={(e) => handleChange('taxSaverFd5yr', parseFloat(e.target.value) || 0)}
                    className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider pt-2 border-t border-slate-200">
                National Pension System (NPS)
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Self NPS Contribution u/s 80CCD(1B) (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.npsSelf80CCD1B}
                    onChange={(e) => handleChange('npsSelf80CCD1B', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                  <span className="text-[10px] text-slate-400">
                    Additional deduction up to ₹50,000 (Old regime only)
                  </span>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Opt-In Employer NPS u/s 80CCD(2)
                  </label>
                  <select
                    value={formData.optInEmployerNps80CCD2}
                    onChange={(e) => handleChange('optInEmployerNps80CCD2', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-semibold"
                  >
                    <option value="N">No (Do not opt-in)</option>
                    <option value="Y">Yes (14% in New Regime / 10% in Old Regime)</option>
                  </select>
                  <span className="text-[10px] text-emerald-700 font-medium">
                    Allowed in BOTH Old and New Regimes!
                  </span>
                </div>
              </div>
            </div>
          )}

          {activeTab === '80d' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Mediclaim for Self & Family (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.mediclaimSelfFamily}
                    onChange={(e) => handleChange('mediclaimSelfFamily', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                  <span className="text-[10px] text-slate-400">Max ₹25,000 (₹50,000 for senior citizen)</span>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Mediclaim for Parents (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.mediclaimParents}
                    onChange={(e) => handleChange('mediclaimParents', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Are Parents Senior Citizens (&gt;=60 yrs)?
                  </label>
                  <select
                    value={formData.parentsSeniorCitizen}
                    onChange={(e) => handleChange('parentsSeniorCitizen', e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg"
                  >
                    <option value="N">No (Limit ₹25,000)</option>
                    <option value="Y">Yes (Higher Limit ₹50,000)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Preventive Health Checkup (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.preventiveHealthCheckup}
                    onChange={(e) =>
                      handleChange('preventiveHealthCheckup', parseFloat(e.target.value) || 0)
                    }
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                  <span className="text-[10px] text-slate-400">Capped at ₹5,000 within overall 80D limit</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'prev' && (
            <div className="space-y-4">
              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-[11px] text-amber-900">
                <strong>Mid-Year Joiner (Form 12B):</strong> Income and TDS deducted by previous employer during this
                same Financial Year are incorporated so the payroll engine can spread only the balance tax.
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Previous Employer Name</label>
                  <input
                    type="text"
                    value={formData.prevEmployerName || ''}
                    onChange={(e) => handleChange('prevEmployerName', e.target.value)}
                    placeholder="e.g. Prior Tech Pvt Ltd"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Previous Employer Gross Salary (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.prevEmployerGrossSalary}
                    onChange={(e) =>
                      handleChange('prevEmployerGrossSalary', parseFloat(e.target.value) || 0)
                    }
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Previous Employer TDS Deducted (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.prevEmployerTdsDeducted}
                    onChange={(e) =>
                      handleChange('prevEmployerTdsDeducted', parseFloat(e.target.value) || 0)
                    }
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono text-emerald-700 font-bold"
                  />
                  <span className="text-[10px] text-slate-400">Credited against total tax liability</span>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Previous Employer PF Deducted (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.prevEmployerPfDeducted}
                    onChange={(e) =>
                      handleChange('prevEmployerPfDeducted', parseFloat(e.target.value) || 0)
                    }
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-xs"
            >
              <Save className="h-4 w-4" />
              Save Declaration
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
