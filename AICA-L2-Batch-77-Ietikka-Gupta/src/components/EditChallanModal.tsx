import React, { useState, useEffect } from 'react';
import { X, Save, Calendar, Hash, Building2, Coins, Calculator } from 'lucide-react';
import { ChallanRecord, FundType } from '../types';

interface EditChallanModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (record: ChallanRecord) => void;
  recordToEdit: ChallanRecord | null;
}

export const EditChallanModal: React.FC<EditChallanModalProps> = ({
  isOpen,
  onClose,
  onSave,
  recordToEdit,
}) => {
  const [fundType, setFundType] = useState<FundType>('PF');
  const [establishmentName, setEstablishmentName] = useState('');
  const [establishmentId, setEstablishmentId] = useState('');
  const [wageMonth, setWageMonth] = useState('April 2024');
  const [statutoryDueDate, setStatutoryDueDate] = useState('2024-05-15');
  const [actualPaymentDate, setActualPaymentDate] = useState('2024-05-12');
  const [challanReference, setChallanReference] = useState('');
  const [employeeContribution, setEmployeeContribution] = useState(50000);
  const [employerContribution, setEmployerContribution] = useState(50000);
  const [adminOtherCharges, setAdminOtherCharges] = useState(2000);
  const [totalChallanAmount, setTotalChallanAmount] = useState(102000);
  const [rawExtractedNotes, setRawExtractedNotes] = useState('');

  useEffect(() => {
    if (recordToEdit) {
      setFundType(recordToEdit.fundType);
      setEstablishmentName(recordToEdit.establishmentName);
      setEstablishmentId(recordToEdit.establishmentId);
      setWageMonth(recordToEdit.wageMonth);
      setStatutoryDueDate(recordToEdit.statutoryDueDate);
      setActualPaymentDate(recordToEdit.actualPaymentDate);
      setChallanReference(recordToEdit.challanReference);
      setEmployeeContribution(recordToEdit.employeeContribution);
      setEmployerContribution(recordToEdit.employerContribution);
      setAdminOtherCharges(recordToEdit.adminOtherCharges);
      setTotalChallanAmount(recordToEdit.totalChallanAmount);
      setRawExtractedNotes(recordToEdit.rawExtractedNotes || '');
    } else {
      // Default for new entry
      setFundType('PF');
      setEstablishmentName('Assessee Establishment');
      setEstablishmentId('DLCPM0012345000');
      setWageMonth('April 2024');
      setStatutoryDueDate('2024-05-15');
      setActualPaymentDate('2024-05-14');
      setChallanReference(`TRRN-${Date.now().toString().slice(-8)}`);
      setEmployeeContribution(45000);
      setEmployerContribution(45000);
      setAdminOtherCharges(1875);
      setTotalChallanAmount(91875);
      setRawExtractedNotes('Manual entry by Auditor');
    }
  }, [recordToEdit, isOpen]);

  if (!isOpen) return null;

  const handleCalculateTotal = () => {
    const ee = Number(employeeContribution) || 0;
    const er = Number(employerContribution) || 0;
    const adm = Number(adminOtherCharges) || 0;
    setTotalChallanAmount(ee + er + adm);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const ee = Number(employeeContribution) || 0;
    const er = Number(employerContribution) || 0;
    const adm = Number(adminOtherCharges) || 0;
    const total = Number(totalChallanAmount) || (ee + er + adm);

    // Calculate delay
    const dueTime = new Date(statutoryDueDate).getTime();
    const payTime = new Date(actualPaymentDate).getTime();
    const diffDays = Math.round((payTime - dueTime) / (1000 * 60 * 60 * 24));
    
    const isDelayed = diffDays > 0;
    const delayDays = isDelayed ? diffDays : 0;
    const disallowableAmount = isDelayed ? ee : 0;

    const record: ChallanRecord = {
      id: recordToEdit ? recordToEdit.id : `rec_manual_${Date.now()}`,
      fundType,
      establishmentName: establishmentName || "Assessee",
      establishmentId: establishmentId || (fundType === 'PF' ? 'DLCPM0000000000' : '11000000000000001'),
      wageMonth,
      wageMonthKey: recordToEdit?.wageMonthKey || statutoryDueDate.slice(0, 7),
      financialYear: recordToEdit?.financialYear || "2024-2025",
      statutoryDueDate,
      actualPaymentDate,
      challanReference: challanReference || `REF-${Date.now()}`,
      employeeContribution: ee,
      employerContribution: er,
      adminOtherCharges: adm,
      totalChallanAmount: total,
      status: isDelayed ? 'DELAYED' : 'ON_TIME',
      delayDays,
      disallowableAmount,
      fileName: recordToEdit?.fileName || 'Manual Auditor Entry',
      rawExtractedNotes,
    };

    onSave(record);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-4 sm:p-5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-sky-400" />
            <h3 className="text-base font-bold text-slate-50">
              {recordToEdit ? 'Edit Challan Record' : 'Add New Challan Record'}
            </h3>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 overflow-y-auto">
          
          {/* Fund Type & Reference */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Fund Type</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setFundType('PF')}
                  className={`py-2 text-xs font-bold rounded-lg border text-center transition cursor-pointer ${
                    fundType === 'PF' 
                      ? 'bg-sky-50 border-sky-500 text-sky-700' 
                      : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  EPFO / PF
                </button>
                <button
                  type="button"
                  onClick={() => setFundType('ESI')}
                  className={`py-2 text-xs font-bold rounded-lg border text-center transition cursor-pointer ${
                    fundType === 'ESI' 
                      ? 'bg-indigo-50 border-indigo-500 text-indigo-700' 
                      : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  ESIC / ESI
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                TRRN / Challan Ref No.
              </label>
              <input
                type="text"
                value={challanReference}
                onChange={(e) => setChallanReference(e.target.value)}
                placeholder="e.g. 1012405084920"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
                required
              />
            </div>
          </div>

          {/* Establishment Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Establishment Name</label>
              <input
                type="text"
                value={establishmentName}
                onChange={(e) => setEstablishmentName(e.target.value)}
                placeholder="Company / Employer Name"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Est. ID / Employer Code
              </label>
              <input
                type="text"
                value={establishmentId}
                onChange={(e) => setEstablishmentId(e.target.value)}
                placeholder={fundType === 'PF' ? "e.g. DLCPM0045892000" : "e.g. 11000458920001001"}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
              />
            </div>
          </div>

          {/* Wage Month, Due Date, Payment Date */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Wage Month</label>
              <input
                type="text"
                value={wageMonth}
                onChange={(e) => setWageMonth(e.target.value)}
                placeholder="e.g. April 2024"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Statutory Due Date
              </label>
              <input
                type="date"
                value={statutoryDueDate}
                onChange={(e) => setStatutoryDueDate(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Actual Payment Date
              </label>
              <input
                type="date"
                value={actualPaymentDate}
                onChange={(e) => setActualPaymentDate(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
                required
              />
            </div>
          </div>

          {/* Amounts Section */}
          <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Challan Amount Breakdown</span>
              <button
                type="button"
                onClick={handleCalculateTotal}
                className="text-[11px] text-sky-600 font-semibold hover:underline flex items-center gap-1 cursor-pointer"
              >
                <Calculator className="w-3 h-3" /> Auto-Sum Total
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Employee Contribution (₹) <span className="text-rose-600">*</span>
                </label>
                <input
                  type="number"
                  value={employeeContribution}
                  onChange={(e) => setEmployeeContribution(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono font-semibold"
                  required
                />
                <span className="text-[10px] text-slate-500">Subject to Clause 20(b) & Sec 36(1)(va)</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Employer Contribution (₹)
                </label>
                <input
                  type="number"
                  value={employerContribution}
                  onChange={(e) => setEmployerContribution(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
                />
                <span className="text-[10px] text-slate-500">Section 43B allowable</span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Admin & Other Charges (₹)
                </label>
                <input
                  type="number"
                  value={adminOtherCharges}
                  onChange={(e) => setAdminOtherCharges(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Total Challan Paid (₹)
                </label>
                <input
                  type="number"
                  value={totalChallanAmount}
                  onChange={(e) => setTotalChallanAmount(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono font-bold text-slate-900"
                  required
                />
              </div>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Auditor Remarks / Raw Notes</label>
            <textarea
              value={rawExtractedNotes}
              onChange={(e) => setRawExtractedNotes(e.target.value)}
              rows={2}
              placeholder="Notes or breakdown remarks"
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          {/* Modal Footer */}
          <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-bold shadow-md transition flex items-center gap-1.5 cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Record</span>
            </button>
          </div>

        </form>

      </div>
    </div>
  );
};
