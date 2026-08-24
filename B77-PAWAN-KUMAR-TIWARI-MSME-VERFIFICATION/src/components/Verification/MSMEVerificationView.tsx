import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Search,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileCheck2,
  ExternalLink,
  History,
  Building2,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Vendor, VerificationStatus, MSMECategory } from '../../types';
import { formatDate, isValidPAN, isValidUdyam, checkPanGstinMatch } from '../../utils/formatters';

export const MSMEVerificationView: React.FC = () => {
  const { vendors, verifyVendorPortal, currentUserRole } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [isBatchVerifying, setIsBatchVerifying] = useState(false);
  const [activeVendorForCheck, setActiveVendorForCheck] = useState<Vendor | null>(null);

  // Live Portal Simulator inputs
  const [simUdyam, setSimUdyam] = useState('UDYAM-MH-01-0012847');
  const [simPan, setSimPan] = useState('AACFA1234D');
  const [simResult, setSimResult] = useState<any | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);

  const filteredVendors = vendors.filter((v) => {
    const matchesSearch =
      v.vendorName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.vendorCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.pan.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.udyamNumber.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = selectedStatus === 'ALL' || v.verificationStatus === selectedStatus;
    return matchesSearch && matchesStatus;
  });

  const pendingCount = vendors.filter((v) => v.verificationStatus === 'Pending').length;
  const mismatchCount = vendors.filter((v) => v.verificationStatus === 'Mismatch').length;

  const handleBatchVerify = async () => {
    const pending = vendors.filter((v) => v.verificationStatus === 'Pending' || v.verificationStatus === 'Not Verified');
    if (pending.length === 0) return;

    setIsBatchVerifying(true);
    for (const v of pending) {
      await verifyVendorPortal(v.id);
    }
    setIsBatchVerifying(false);
  };

  const handleRunSimulator = () => {
    if (!simUdyam.trim()) return;
    setIsSimLoading(true);

    setTimeout(() => {
      const valid = isValidUdyam(simUdyam);
      if (!valid) {
        setSimResult({
          status: 'NOT_FOUND',
          message: 'Invalid Udyam Registration format. Official database query returned no matching record.',
        });
      } else {
        setSimResult({
          status: 'ACTIVE',
          udyamNumber: simUdyam.toUpperCase(),
          enterpriseName: 'Simulated Verified Enterprise (Govt. of India DB)',
          enterpriseType: 'Micro Enterprise',
          majorActivity: 'Manufacturing',
          dicName: 'District Industries Centre, Pune (Maharashtra)',
          dateOfIncorporation: '15-Aug-2020',
          nicCode: '25999 - Manufacture of other fabricated metal products n.e.c.',
          verifiedTimestamp: new Date().toISOString(),
        });
      }
      setIsSimLoading(false);
    }, 600);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Batch Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">MSME & Udyam Verification Hub</h2>
          <p className="text-xs text-slate-500">
            Real-time validation against Ministry of Micro, Small & Medium Enterprises portal standards
          </p>
        </div>

        <div className="flex items-center gap-2">
          {currentUserRole !== 'Auditor' && (
            <button
              disabled={isBatchVerifying || pendingCount === 0}
              onClick={handleBatchVerify}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isBatchVerifying ? 'animate-spin' : ''}`} />
              {isBatchVerifying ? 'Verifying on Portal...' : `Verify Pending (${pendingCount})`}
            </button>
          )}
        </div>
      </div>

      {/* Verification Status Overview Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
          <div className="text-xs font-semibold text-emerald-800">Verified MSMEs</div>
          <div className="text-2xl font-black text-emerald-700 mt-1">
            {vendors.filter((v) => v.verificationStatus === 'Verified').length}
          </div>
          <div className="text-[11px] text-emerald-600 mt-0.5">Compliant for Section 15</div>
        </div>

        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
          <div className="text-xs font-semibold text-amber-800">Pending Verification</div>
          <div className="text-2xl font-black text-amber-700 mt-1">{pendingCount}</div>
          <div className="text-[11px] text-amber-600 mt-0.5">Requires portal check</div>
        </div>

        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl">
          <div className="text-xs font-semibold text-rose-800">Mismatch Flagged</div>
          <div className="text-2xl font-black text-rose-700 mt-1">{mismatchCount}</div>
          <div className="text-[11px] text-rose-600 mt-0.5">PAN / Name discrepancy</div>
        </div>

        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
          <div className="text-xs font-semibold text-slate-700">Non-MSME / Large</div>
          <div className="text-2xl font-black text-slate-800 mt-1">
            {vendors.filter((v) => !v.isMSME).length}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">Exempt from 45-day cap</div>
        </div>
      </div>

      {/* Live Udyam Portal Verification Simulator Console */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-xl p-5 border border-slate-700 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h3 className="font-bold text-white text-sm">Direct Udyam Portal Query Console</h3>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            Govt API Simulation
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-[11px] font-medium text-slate-300 mb-1">Udyam Registration Number</label>
            <input
              type="text"
              value={simUdyam}
              onChange={(e) => setSimUdyam(e.target.value.toUpperCase())}
              placeholder="UDYAM-XX-00-0000000"
              className="w-full px-3 py-1.5 text-xs bg-slate-800 border border-slate-600 rounded-lg text-white font-mono uppercase focus:outline-hidden focus:border-emerald-400"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-300 mb-1">Vendor PAN</label>
            <input
              type="text"
              value={simPan}
              onChange={(e) => setSimPan(e.target.value.toUpperCase())}
              placeholder="e.g. AACFA1234D"
              className="w-full px-3 py-1.5 text-xs bg-slate-800 border border-slate-600 rounded-lg text-white font-mono uppercase focus:outline-hidden focus:border-emerald-400"
            />
          </div>

          <div className="flex items-end">
            <button
              onClick={handleRunSimulator}
              disabled={isSimLoading}
              className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg shadow-sm flex items-center justify-center gap-1.5 transition-all cursor-pointer"
            >
              {isSimLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
              <span>Query Portal Database</span>
            </button>
          </div>
        </div>

        {/* Simulator Results */}
        {simResult && (
          <div className="mt-4 p-4 bg-slate-800/90 rounded-lg border border-slate-700 text-xs animate-in fade-in">
            {simResult.status === 'ACTIVE' ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Official Record Found: ACTIVE & VERIFIED</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-[11px] text-slate-300 pt-1">
                  <div>
                    <span className="text-slate-400">Enterprise:</span> <strong>{simResult.enterpriseName}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Category:</span> <strong className="text-emerald-300">{simResult.enterpriseType}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Activity:</span> <strong>{simResult.majorActivity}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">DIC Center:</span> <strong>{simResult.dicName}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">Inc. Date:</span> <strong>{simResult.dateOfIncorporation}</strong>
                  </div>
                  <div>
                    <span className="text-slate-400">NIC Code:</span> <strong>{simResult.nicCode}</strong>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-rose-400">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{simResult.message}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Verification Filter & Search */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search vendor, PAN, Udyam number..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:bg-white focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-semibold">Status:</span>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
          >
            <option value="ALL">All Statuses ({vendors.length})</option>
            <option value="Verified">Verified</option>
            <option value="Pending">Pending</option>
            <option value="Mismatch">Mismatch</option>
            <option value="Not Verified">Not Verified</option>
            <option value="Not Found">Not Found</option>
          </select>
        </div>
      </div>

      {/* Verification Directory Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
              <tr>
                <th className="px-4 py-3">Vendor / Entity</th>
                <th className="px-4 py-3">PAN & GSTIN Check</th>
                <th className="px-4 py-3">Udyam Registration</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last Verified</th>
                <th className="px-4 py-3 text-right">Verification Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredVendors.map((vendor) => {
                const panMatch = checkPanGstinMatch(vendor.pan, vendor.gstin);

                return (
                  <tr key={vendor.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="font-bold text-slate-900">{vendor.vendorName}</div>
                      <div className="text-[11px] text-slate-500 font-mono">{vendor.vendorCode}</div>
                    </td>

                    <td className="px-4 py-3.5 text-[11px] font-mono">
                      <div>PAN: {vendor.pan || '—'}</div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span>GST: {vendor.gstin || '—'}</span>
                        {vendor.pan && vendor.gstin && (
                          <span
                            className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                              panMatch ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {panMatch ? 'Match' : 'Mismatch'}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-3.5">
                      {vendor.udyamNumber ? (
                        <div className="font-mono text-emerald-800 font-bold text-[11px]">
                          {vendor.udyamNumber}
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">No Udyam Provided</span>
                      )}
                    </td>

                    <td className="px-4 py-3.5">
                      <span className="px-2 py-0.5 bg-slate-100 font-bold rounded text-[11px] text-slate-800">
                        {vendor.msmeCategory}
                      </span>
                    </td>

                    <td className="px-4 py-3.5">
                      <span
                        className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold inline-flex items-center gap-1 ${
                          vendor.verificationStatus === 'Verified'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : vendor.verificationStatus === 'Pending'
                            ? 'bg-amber-100 text-amber-800 border border-amber-200'
                            : vendor.verificationStatus === 'Mismatch'
                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                            : 'bg-slate-100 text-slate-700 border border-slate-200'
                        }`}
                      >
                        {vendor.verificationStatus}
                      </span>
                    </td>

                    <td className="px-4 py-3.5 text-slate-500 text-[11px]">
                      {vendor.verificationDate ? formatDate(vendor.verificationDate) : 'Pending'}
                      {vendor.verifiedBy && (
                        <div className="text-[10px] text-slate-400">By: {vendor.verifiedBy.split(' ')[0]}</div>
                      )}
                    </td>

                    <td className="px-4 py-3.5 text-right">
                      {currentUserRole !== 'Auditor' && (
                        <button
                          onClick={() => setActiveVendorForCheck(vendor)}
                          className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-emerald-50 hover:border-emerald-300 hover:text-emerald-800 text-slate-700 text-xs font-bold rounded-lg shadow-xs transition-all cursor-pointer"
                        >
                          Manual Verification
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Verification Modal */}
      {activeVendorForCheck && (
        <ManualVerificationModal
          vendor={activeVendorForCheck}
          onClose={() => setActiveVendorForCheck(null)}
          onVerify={async (status, notes) => {
            await verifyVendorPortal(activeVendorForCheck.id, status, notes);
            setActiveVendorForCheck(null);
          }}
        />
      )}
    </div>
  );
};

/* --- Manual Verification Modal --- */
interface ManualVerificationModalProps {
  vendor: Vendor;
  onClose: () => void;
  onVerify: (status: VerificationStatus, notes: string) => Promise<void>;
}

const ManualVerificationModal: React.FC<ManualVerificationModalProps> = ({ vendor, onClose, onVerify }) => {
  const [selectedStatus, setSelectedStatus] = useState<VerificationStatus>(vendor.verificationStatus || 'Verified');
  const [notes, setNotes] = useState(`Verified against physical Udyam registration certificate on ${new Date().toLocaleDateString('en-IN')}`);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    await onVerify(selectedStatus, notes);
    setIsSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-700" />
            <h3 className="font-bold text-slate-800 text-sm">Update Vendor Verification Status</h3>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
            <div className="font-bold text-slate-900 text-sm">{vendor.vendorName}</div>
            <div className="text-slate-500 font-mono">
              Code: {vendor.vendorCode} | Udyam: {vendor.udyamNumber || 'N/A'}
            </div>
            <div className="text-slate-500 font-mono">PAN: {vendor.pan} | GSTIN: {vendor.gstin}</div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Set Verification Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as VerificationStatus)}
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg font-semibold focus:outline-hidden"
            >
              <option value="Verified">🟢 Verified (Authenticated on Portal)</option>
              <option value="Mismatch">🔴 Mismatch (Discrepancy in PAN/GSTIN/Category)</option>
              <option value="Not Found">⚪ Not Found (Record does not exist)</option>
              <option value="Pending">🟡 Pending (Awaiting confirmation)</option>
              <option value="Not Verified">Not Verified</option>
            </select>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Verification Remarks / Audit Notes *</label>
            <textarea
              rows={3}
              required
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Validated against official Udyam portal. Category confirmed as Micro."
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg shadow-xs"
            >
              {isSubmitting ? 'Saving...' : 'Commit Status Update'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
