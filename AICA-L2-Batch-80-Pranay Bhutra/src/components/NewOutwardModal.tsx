import React, { useState } from 'react';
import {
  X,
  Truck,
  Building2,
  User,
  DollarSign,
  Send,
  CheckCircle2,
  Calendar,
  ShieldCheck
} from 'lucide-react';
import { OutwardShipment, UserProfile, ConfidentialityLevel } from '../types';
import { MOCK_CARRIERS, MOCK_CLIENT_JOBS } from '../data/mockData';
import { ParcelStorageService } from '../services/storage';

interface NewOutwardModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile;
  onSuccess: () => void;
}

export const NewOutwardModal: React.FC<NewOutwardModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onSuccess,
}) => {
  const orgUsers = ParcelStorageService.getOrganizationUsers(currentUser?.organizationId);
  const staffList = orgUsers.length > 0 ? orgUsers : (currentUser ? [currentUser] : []);

  const [trackingNumber, setTrackingNumber] = useState(
    `${Math.floor(1000000000 + Math.random() * 9000000000)}`
  );
  const [carrier, setCarrier] = useState(MOCK_CARRIERS[0]);
  const [customCarrier, setCustomCarrier] = useState('');
  const [selectedJobCode, setSelectedJobCode] = useState(MOCK_CLIENT_JOBS[0].code);
  const [customClientName, setCustomClientName] = useState('');
  const [assignedStaffId, setAssignedStaffId] = useState(currentUser?.id || staffList[0]?.id || 'USR-01');
  const [recipientName, setRecipientName] = useState('');
  const [recipientOrg, setRecipientOrg] = useState('');
  const [recipientAddress, setRecipientAddress] = useState('');
  const [recipientCity, setRecipientCity] = useState('Mumbai - 400001');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [contentDesc, setContentDesc] = useState('');
  const [confidentiality, setConfidentiality] = useState<ConfidentialityLevel>('confidential');
  const [packageType, setPackageType] = useState<OutwardShipment['packageType']>('Legal Docket');
  const [weightKg, setWeightKg] = useState(0.5);
  const [courierCost, setCourierCost] = useState(250);
  const [billable, setBillable] = useState(true);
  const [notes, setNotes] = useState('');

  if (!isOpen) return null;

  const jobInfo = MOCK_CLIENT_JOBS.find((j) => j.code === selectedJobCode) || MOCK_CLIENT_JOBS[0];
  const staffInfo = staffList.find((u) => u.id === assignedStaffId) || staffList[0] || currentUser;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipientName.trim() || !contentDesc.trim()) return;

    const resolvedCarrier = carrier.includes('Others')
      ? (customCarrier.trim() || 'Other Carrier')
      : carrier;

    ParcelStorageService.addOutwardShipment({
      organizationId: currentUser?.organizationId || 'org_singhania_ca',
      trackingNumber,
      carrier: resolvedCarrier,
      clientName: customClientName.trim() || jobInfo.client,
      clientJobCode: jobInfo.code,
      partnerInCharge: jobInfo.partner,
      assignedStaffId: staffInfo?.id || currentUser?.id || 'USR-01',
      assignedStaffName: staffInfo?.name || currentUser?.name || 'Staff User',
      recipientName,
      recipientOrganization: recipientOrg || (customClientName.trim() || jobInfo.client),
      recipientAddress,
      recipientCity,
      recipientEmail: recipientEmail || undefined,
      department: staffInfo?.department || currentUser?.department || 'Audit',
      contentDescription: contentDesc,
      confidentiality,
      packageType,
      weightKg: Number(weightKg),
      courierCost: Number(courierCost),
      billableToClient: billable,
      dispatchedAt:
        new Date().toLocaleDateString() +
        ' ' +
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      estimatedDeliveryDate: 'Tomorrow 05:00 PM',
      status: 'dispatched',
      notes
    });

    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Create Outward Dispatch Docket</h2>
              <p className="text-xs text-slate-400">
                Outbound logistics with CA cost allocation and real-time assignee tracking.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="py-4 space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {/* Client Job Code (CA Cost Allocation) */}
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <label className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5" />
              Client Matter Code (100% Expense Recovery Billing)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <select
                value={selectedJobCode}
                onChange={(e) => setSelectedJobCode(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-750 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
              >
                {MOCK_CLIENT_JOBS.map((j) => (
                  <option key={j.code} value={j.code}>
                    {j.code} - {j.client}
                  </option>
                ))}
              </select>

              <div className="text-xs text-slate-400 flex items-center">
                <span>Engagement Partner: <b className="text-slate-200">{jobInfo.partner}</b></span>
              </div>
            </div>
          </div>

          {/* Carrier & AWB */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Courier Carrier Service:
              </label>
              <select
                value={carrier}
                onChange={(e) => setCarrier(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                {MOCK_CARRIERS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Carrier AWB Number:
              </label>
              <input
                type="text"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-100 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* If "Others" is selected: Custom Carrier Name */}
          {carrier.includes('Others') && (
            <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 animate-in fade-in duration-150">
              <label className="text-xs font-semibold text-blue-300 block mb-1">
                Enter Custom Carrier / Courier Person Name:
              </label>
              <input
                type="text"
                value={customCarrier}
                onChange={(e) => setCustomCarrier(e.target.value)}
                required
                placeholder="e.g. Swiggy Genie, Local Peon Hand Delivery, Urgent Porter"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          )}

          {/* Addressee Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Consignee Name / Addressee:
              </label>
              <input
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                required
                placeholder="e.g. Mr. Arvind Singhania (VP Tax)"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Consignee Organization:
              </label>
              <input
                type="text"
                value={recipientOrg}
                onChange={(e) => setRecipientOrg(e.target.value)}
                placeholder="e.g. Reliance Retail / ROC Mumbai"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Address & City */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2">
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Destination Street Address:
              </label>
              <input
                type="text"
                value={recipientAddress}
                onChange={(e) => setRecipientAddress(e.target.value)}
                placeholder="e.g. Maker Chambers IV, Nariman Point"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                City & Pin Code:
              </label>
              <input
                type="text"
                value={recipientCity}
                onChange={(e) => setRecipientCity(e.target.value)}
                placeholder="Mumbai - 400021"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Assigned Staff & Content Description */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Assigned Staff Member:
              </label>
              <select
                value={assignedStaffId}
                onChange={(e) => setAssignedStaffId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                {staffList.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.department})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Client Email (For Automated Alert):
              </label>
              <input
                type="email"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                placeholder="client.contact@company.com"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">
              Document / Content Description:
            </label>
            <input
              type="text"
              value={contentDesc}
              onChange={(e) => setContentDesc(e.target.value)}
              required
              placeholder="e.g. Signed Tax Audit Report Form 3CD with Certified Annexures (3 hard copies)"
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* Costing & Billable Tag */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-xl bg-slate-950/70 border border-slate-800">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Weight (Kg):
              </label>
              <input
                type="number"
                step="0.1"
                value={weightKg}
                onChange={(e) => setWeightKg(parseFloat(e.target.value) || 0.1)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-750 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Courier Charge (₹):
              </label>
              <input
                type="number"
                value={courierCost}
                onChange={(e) => setCourierCost(parseInt(e.target.value, 10) || 0)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-750 text-xs text-slate-100 font-mono text-emerald-400 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="flex flex-col justify-center">
              <label className="flex items-center gap-2 cursor-pointer mt-3">
                <input
                  type="checkbox"
                  checked={billable}
                  onChange={(e) => setBillable(e.target.checked)}
                  className="rounded border-slate-700 text-blue-600 focus:ring-blue-500 bg-slate-900"
                />
                <span className="text-xs font-medium text-slate-200">Billable to Client</span>
              </label>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
            >
              Cancel
            </button>

            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-all shadow-lg shadow-blue-600/30 flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Dispatch & Notify Stakeholders</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
