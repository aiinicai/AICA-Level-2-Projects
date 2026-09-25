import React, { useState } from 'react';
import { X, Save, User, Building, Landmark, ShieldCheck, DollarSign } from 'lucide-react';
import { EmployeeMaster, EmploymentStatus, Gender, PaymentMode, RevisionReason, TaxRegime } from '../types/payroll';

interface EmployeeModalProps {
  employee?: EmployeeMaster | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (emp: EmployeeMaster) => void;
}

export const EmployeeModal: React.FC<EmployeeModalProps> = ({ employee, isOpen, onClose, onSave }) => {
  if (!isOpen) return null;

  const [formData, setFormData] = useState<EmployeeMaster>(() => {
    if (employee) return { ...employee };
    return {
      employeeCode: `EMP${String(Math.floor(Math.random() * 900) + 100)}`,
      employeeName: '',
      pan: '',
      dateOfBirth: '1995-01-01',
      gender: 'Male' as Gender,
      dateOfJoining: '2026-04-01',
      employmentStatus: 'Active' as EmploymentStatus,
      department: 'Finance',
      designation: 'Associate',
      locationCity: 'Mumbai',
      metroFlag: 'Y',
      costCenter: 'CC-OPS-01',
      email: '',
      mobile: '',
      bankName: 'HDFC Bank',
      bankAccountNo: '',
      ifsc: 'HDFC0000001',
      uan: '',
      pfNumber: '',
      pfApplicable: 'Y',
      pfWageCeilingApplied: 'N',
      esiApplicable: 'N',
      taxRegimeOpted: 'New' as TaxRegime,
      salaryEffectiveFrom: '2026-04-01',
      revisionReason: 'New Appointment' as RevisionReason,
      annualCtc: 600000,
      basicMonthly: 25000,
      hraMonthly: 10000,
      conveyanceAllowanceMonthly: 1600,
      childrenEducationAllowanceMonthly: 0,
      ltaMonthly: 0,
      specialAllowanceMonthly: 10000,
      otherAllowanceMonthly: 0,
      variablePayAnnual: 0,
      joiningBonus: 0,
      employerPfMonthly: 3000,
      employerNpsMonthly: 0,
      gratuityProvisionMonthly: 1200,
      employeePfMonthly: 3000,
      professionalTaxMonthly: 0,
      otherRecurringDeductionMonthly: 0,
      paymentMode: 'Bank Transfer' as PaymentMode,
      remarks: '',
    };
  });

  const [activeSection, setActiveSection] = useState<'identity' | 'employment' | 'bank' | 'salary'>('identity');

  const handleChange = (field: keyof EmployeeMaster, value: unknown) => {
    setFormData((prev) => {
      const updated = { ...prev, [field]: value };
      // Auto-compute PF if basic changes
      if (field === 'basicMonthly' || field === 'pfApplicable' || field === 'pfWageCeilingApplied') {
        const basic = typeof updated.basicMonthly === 'number' ? updated.basicMonthly : parseFloat(String(updated.basicMonthly)) || 0;
        if (updated.pfApplicable === 'Y') {
          const pfWage = updated.pfWageCeilingApplied === 'Y' ? Math.min(basic, 15000) : basic;
          const pfVal = Math.round(pfWage * 0.12);
          updated.employeePfMonthly = pfVal;
          updated.employerPfMonthly = pfVal;
        } else {
          updated.employeePfMonthly = 0;
          updated.employerPfMonthly = 0;
        }
      }
      return updated;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.employeeCode || !formData.employeeName || !formData.pan) {
      alert('Please fill in mandatory fields: Employee Code, Name, and PAN.');
      return;
    }
    onSave(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Top Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              {employee ? `Edit Employee — ${employee.employeeCode}` : 'Add New Employee to Master'}
            </h2>
            <p className="text-xs text-slate-500">
              Master demographic, statutory flags, and salary structure
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Section Tabs */}
        <div className="flex border-b border-slate-200 bg-white px-6">
          <button
            type="button"
            onClick={() => setActiveSection('identity')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeSection === 'identity'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <User className="h-3.5 w-3.5" /> Identity & Contact
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('employment')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeSection === 'employment'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Building className="h-3.5 w-3.5" /> Employment & Statutory
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('bank')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeSection === 'bank'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Landmark className="h-3.5 w-3.5" /> Bank & Payment
          </button>

          <button
            type="button"
            onClick={() => setActiveSection('salary')}
            className={`py-2.5 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeSection === 'salary'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <DollarSign className="h-3.5 w-3.5" /> Monthly Salary Structure
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1 space-y-4 text-xs">
          {activeSection === 'identity' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Employee Code *</label>
                <input
                  type="text"
                  required
                  value={formData.employeeCode}
                  onChange={(e) => handleChange('employeeCode', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Full Name (As per PAN) *</label>
                <input
                  type="text"
                  required
                  value={formData.employeeName}
                  onChange={(e) => handleChange('employeeName', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">PAN (10-char) *</label>
                <input
                  type="text"
                  required
                  maxLength={10}
                  placeholder="ABCDE1234F"
                  value={formData.pan}
                  onChange={(e) => handleChange('pan', e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono uppercase focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Date of Birth (DOB) *</label>
                <input
                  type="date"
                  required
                  value={formData.dateOfBirth}
                  onChange={(e) => handleChange('dateOfBirth', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Gender</label>
                <select
                  value={formData.gender}
                  onChange={(e) => handleChange('gender', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Mobile Number</label>
                <input
                  type="tel"
                  value={formData.mobile}
                  onChange={(e) => handleChange('mobile', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>
          )}

          {activeSection === 'employment' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Date of Joining (DOJ) *</label>
                <input
                  type="date"
                  required
                  value={formData.dateOfJoining}
                  onChange={(e) => handleChange('dateOfJoining', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Date of Leaving (DOL)</label>
                <input
                  type="date"
                  value={formData.dateOfLeaving || ''}
                  onChange={(e) => handleChange('dateOfLeaving', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
                <span className="text-[10px] text-slate-400">Leave blank if currently active</span>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Employment Status *</label>
                <select
                  value={formData.employmentStatus}
                  onChange={(e) => handleChange('employmentStatus', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="Active">Active</option>
                  <option value="New Joiner">New Joiner</option>
                  <option value="Resigned">Resigned</option>
                  <option value="Exited">Exited</option>
                  <option value="On Leave (LWP)">On Leave (LWP)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Department</label>
                <input
                  type="text"
                  value={formData.department}
                  onChange={(e) => handleChange('department', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Designation</label>
                <input
                  type="text"
                  value={formData.designation}
                  onChange={(e) => handleChange('designation', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">City & Metro Flag *</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formData.locationCity}
                    onChange={(e) => handleChange('locationCity', e.target.value)}
                    placeholder="City"
                    className="w-2/3 px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                  />
                  <select
                    value={formData.metroFlag}
                    onChange={(e) => handleChange('metroFlag', e.target.value)}
                    className="w-1/3 px-2 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="Y">Metro (50% HRA)</option>
                    <option value="N">Non-Metro (40%)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Provident Fund (EPF)</label>
                <select
                  value={formData.pfApplicable}
                  onChange={(e) => handleChange('pfApplicable', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="Y">Applicable (12%)</option>
                  <option value="N">Not Applicable</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">PF Wage Ceiling</label>
                <select
                  value={formData.pfWageCeilingApplied}
                  onChange={(e) => handleChange('pfWageCeilingApplied', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="N">Actual Basic (No ceiling)</option>
                  <option value="Y">Cap at ₹15,000</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tax Regime (Default Opted) *</label>
                <select
                  value={formData.taxRegimeOpted}
                  onChange={(e) => handleChange('taxRegimeOpted', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500 font-semibold"
                >
                  <option value="New">New Regime (u/s 115BAC)</option>
                  <option value="Old">Old Regime</option>
                </select>
              </div>
            </div>
          )}

          {activeSection === 'bank' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Bank Name</label>
                <input
                  type="text"
                  value={formData.bankName}
                  onChange={(e) => handleChange('bankName', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Bank Account Number</label>
                <input
                  type="text"
                  value={formData.bankAccountNo}
                  onChange={(e) => handleChange('bankAccountNo', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">IFSC Code</label>
                <input
                  type="text"
                  value={formData.ifsc}
                  onChange={(e) => handleChange('ifsc', e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono uppercase focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">UAN (Universal Account Number)</label>
                <input
                  type="text"
                  value={formData.uan}
                  onChange={(e) => handleChange('uan', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">PF Member ID / Number</label>
                <input
                  type="text"
                  value={formData.pfNumber}
                  onChange={(e) => handleChange('pfNumber', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg font-mono focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Payment Mode</label>
                <select
                  value={formData.paymentMode}
                  onChange={(e) => handleChange('paymentMode', e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="Bank Transfer">Bank Transfer (NEFT/RTGS)</option>
                  <option value="Cheque">Cheque</option>
                  <option value="Cash">Cash</option>
                </select>
              </div>
            </div>
          )}

          {activeSection === 'salary' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Annual CTC (₹) *</label>
                  <input
                    type="number"
                    required
                    value={formData.annualCtc}
                    onChange={(e) => handleChange('annualCtc', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg font-mono font-bold text-slate-900 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Revision Reason</label>
                  <select
                    value={formData.revisionReason}
                    onChange={(e) => handleChange('revisionReason', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="New Appointment">New Appointment</option>
                    <option value="Annual Revision">Annual Revision</option>
                    <option value="Promotion">Promotion</option>
                    <option value="Correction">Correction</option>
                    <option value="Exit">Exit</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Salary Effective From</label>
                  <input
                    type="date"
                    value={formData.salaryEffectiveFrom}
                    onChange={(e) => handleChange('salaryEffectiveFrom', e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Monthly Earnings Breakdown (₹)
              </h4>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div>
                  <label className="block text-slate-600 mb-1">Basic Monthly *</label>
                  <input
                    type="number"
                    value={formData.basicMonthly}
                    onChange={(e) => handleChange('basicMonthly', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">HRA Monthly</label>
                  <input
                    type="number"
                    value={formData.hraMonthly}
                    onChange={(e) => handleChange('hraMonthly', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">Special Allowance</label>
                  <input
                    type="number"
                    value={formData.specialAllowanceMonthly}
                    onChange={(e) => handleChange('specialAllowanceMonthly', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">Conveyance Allowance</label>
                  <input
                    type="number"
                    value={formData.conveyanceAllowanceMonthly}
                    onChange={(e) => handleChange('conveyanceAllowanceMonthly', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">Children Edu Allowance</label>
                  <input
                    type="number"
                    value={formData.childrenEducationAllowanceMonthly}
                    onChange={(e) =>
                      handleChange('childrenEducationAllowanceMonthly', parseFloat(e.target.value) || 0)
                    }
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">LTA Monthly</label>
                  <input
                    type="number"
                    value={formData.ltaMonthly}
                    onChange={(e) => handleChange('ltaMonthly', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">Variable Pay (Annual)</label>
                  <input
                    type="number"
                    value={formData.variablePayAnnual}
                    onChange={(e) => handleChange('variablePayAnnual', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">Joining Bonus</label>
                  <input
                    type="number"
                    value={formData.joiningBonus}
                    onChange={(e) => handleChange('joiningBonus', parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              <div className="p-3 bg-indigo-50/60 border border-indigo-100 rounded-lg flex items-center justify-between font-mono">
                <span className="font-sans font-semibold text-slate-800">
                  Total Monthly Gross Base:
                </span>
                <strong className="text-sm text-indigo-950 font-bold">
                  ₹
                  {(
                    formData.basicMonthly +
                    formData.hraMonthly +
                    formData.specialAllowanceMonthly +
                    formData.conveyanceAllowanceMonthly +
                    formData.childrenEducationAllowanceMonthly +
                    formData.ltaMonthly +
                    formData.otherAllowanceMonthly
                  ).toLocaleString('en-IN')}{' '}
                  / month
                </strong>
              </div>
            </div>
          )}

          {/* Modal Footer */}
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
              Save Employee Record
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
