import React, { useState } from 'react';
import { X, Building2, Save, ShieldCheck } from 'lucide-react';
import { EntityDetails, EntityType } from '../types/accounting';

interface EntityDetailsModalProps {
  entity: EntityDetails;
  isOpen: boolean;
  onClose: () => void;
  onSave: (updated: EntityDetails) => void;
}

export const EntityDetailsModal: React.FC<EntityDetailsModalProps> = ({
  entity,
  isOpen,
  onClose,
  onSave,
}) => {
  const [formData, setFormData] = useState<EntityDetails>({ ...entity });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#141414]/70 backdrop-blur-xs p-4 animate-in fade-in" id="modal-entity-details">
      <div className="bg-[#F5F4F0] max-w-2xl w-full border border-[#141414] overflow-hidden shadow-2xl">
        
        {/* Modal Header */}
        <div className="bg-[#141414] text-[#E4E3E0] p-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <Building2 className="w-4 h-4 text-[#A3A29E]" />
            <h3 className="font-bold text-xs uppercase tracking-wider font-mono text-white">Entity Master Details & Statutory Info</h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#A3A29E] hover:text-white p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-3.5 text-xs max-h-[80vh] overflow-y-auto bg-white">
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Entity Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                required
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-semibold focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Entity Constitution / Type *</label>
              <select
                value={formData.entityType}
                onChange={e => setFormData({ ...formData, entityType: e.target.value as EntityType })}
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-semibold focus:outline-none focus:border-[#141414]"
              >
                <option value="Proprietorship">Sole Proprietorship</option>
                <option value="Partnership Firm">Partnership Firm</option>
                <option value="LLP">Limited Liability Partnership (LLP)</option>
                <option value="HUF">Hindu Undivided Family (HUF)</option>
                <option value="Trust">Trust / Non-Profit</option>
                <option value="AOP/BOI">Association of Persons (AOP) / BOI</option>
                <option value="Society">Registered Society</option>
                <option value="Other Non-Corporate">Other Non-Corporate</option>
              </select>
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Permanent Account Number (PAN) *</label>
              <input
                type="text"
                value={formData.pan}
                onChange={e => setFormData({ ...formData, pan: e.target.value.toUpperCase() })}
                required
                maxLength={10}
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono uppercase focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">GSTIN</label>
              <input
                type="text"
                value={formData.gstin}
                onChange={e => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                maxLength={15}
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono uppercase focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Registered Business Address</label>
              <textarea
                rows={2}
                value={formData.address}
                onChange={e => setFormData({ ...formData, address: e.target.value })}
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Financial Year *</label>
              <input
                type="text"
                value={formData.financialYear}
                onChange={e => setFormData({ ...formData, financialYear: e.target.value })}
                placeholder="2024-25"
                required
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Balance Sheet Date *</label>
              <input
                type="text"
                value={formData.balanceSheetDate}
                onChange={e => setFormData({ ...formData, balanceSheetDate: e.target.value })}
                placeholder="31st March 2025"
                required
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Previous Year Date (Optional)</label>
              <input
                type="text"
                value={formData.previousYearDate || ''}
                onChange={e => setFormData({ ...formData, previousYearDate: e.target.value })}
                placeholder="31st March 2024"
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Chartered Accountant / Auditor Name</label>
              <input
                type="text"
                value={formData.auditorName || ''}
                onChange={e => setFormData({ ...formData, auditorName: e.target.value })}
                placeholder="CA R. K. Sharma & Associates"
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">CA Membership No.</label>
              <input
                type="text"
                value={formData.membershipNumber || ''}
                onChange={e => setFormData({ ...formData, membershipNumber: e.target.value })}
                placeholder="098765"
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Firm Registration No (FRN)</label>
              <input
                type="text"
                value={formData.firmRegistrationNo || ''}
                onChange={e => setFormData({ ...formData, firmRegistrationNo: e.target.value })}
                placeholder="102938W"
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">UDIN (Unique Document ID)</label>
              <input
                type="text"
                value={formData.udin || ''}
                onChange={e => setFormData({ ...formData, udin: e.target.value })}
                placeholder="25512948BGXYZW1234"
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono uppercase focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Place of Signing</label>
              <input
                type="text"
                value={formData.placeOfSigning || ''}
                onChange={e => setFormData({ ...formData, placeOfSigning: e.target.value })}
                placeholder="New Delhi / Mumbai"
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs focus:outline-none focus:border-[#141414]"
              />
            </div>

            <div>
              <label className="block font-bold font-mono text-[11px] uppercase text-[#141414] mb-1">Date of Signing</label>
              <input
                type="text"
                value={formData.dateOfSigning || ''}
                onChange={e => setFormData({ ...formData, dateOfSigning: e.target.value })}
                placeholder="25th August 2025"
                className="w-full bg-white border border-[#141414]/30 p-2 text-xs font-mono focus:outline-none focus:border-[#141414]"
              />
            </div>
          </div>

          <div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#141414]/20">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 bg-[#ECEAE5] hover:bg-[#E4E3E0] text-[#141414] text-xs font-mono font-bold border border-[#141414]/30"
            >
              CANCEL
            </button>
            <button
              type="submit"
              className="inline-flex items-center px-4 py-1.5 bg-[#141414] hover:bg-[#282828] text-white text-xs font-mono font-bold border border-[#141414]"
            >
              <Save className="w-3.5 h-3.5 mr-1" />
              SAVE DETAILS
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
