import React, { useState } from 'react';
import {
  Building2,
  Search,
  Filter,
  Plus,
  FileSpreadsheet,
  Download,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Edit2,
  Trash2,
  Eye,
  History,
  X,
  Upload,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Vendor, MSMECategory, MSMEStatus, VerificationStatus, MajorActivity } from '../../types';
import { formatDate, isValidPAN, isValidGSTIN, isValidUdyam, checkPanGstinMatch } from '../../utils/formatters';
import { exportTableToExcel } from '../../utils/excelService';
import { ExcelUploadModal } from '../Common/ExcelUploadModal';

export const VendorMasterView: React.FC = () => {
  const { vendors, addVendor, updateVendor, deleteVendor, verifyVendorPortal, currentUserRole } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isExcelModalOpen, setIsExcelModalOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [selectedHistoryVendor, setSelectedHistoryVendor] = useState<Vendor | null>(null);
  const [selectedCertVendor, setSelectedCertVendor] = useState<Vendor | null>(null);

  // Filtered vendors
  const filteredVendors = vendors.filter((v) => {
    const matchesSearch =
      v.vendorName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.vendorCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.pan.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.gstin.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.udyamNumber.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory = categoryFilter === 'ALL' || v.msmeCategory === categoryFilter;
    const matchesStatus = statusFilter === 'ALL' || v.verificationStatus === statusFilter;

    return matchesSearch && matchesCategory && matchesStatus;
  });

  const handleExportVendors = () => {
    const exportData = filteredVendors.map((v) => ({
      'Vendor Code': v.vendorCode,
      'Vendor Name': v.vendorName,
      PAN: v.pan,
      GSTIN: v.gstin,
      'Udyam Reg. Number': v.udyamNumber,
      'MSME Category': v.msmeCategory,
      'Major Activity': v.majorActivity,
      'Verification Status': v.verificationStatus,
      'Verification Date': formatDate(v.verificationDate),
      'Agreed Credit Days': v.agreedCreditDays,
      'Written Agreement': v.hasWrittenAgreement ? 'Yes' : 'No',
      'Contact Person': v.contactPerson || '—',
      Email: v.email || '—',
      Phone: v.phone || '—',
      Remarks: v.remarks,
    }));
    exportTableToExcel(exportData, 'MSME_Vendor_Master_Register', 'Vendors');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">MSME Vendor Master Directory</h2>
          <p className="text-xs text-slate-500">
            Maintain vendor profiles, Udyam registration credentials, and statutory verification status
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setIsExcelModalOpen(true)}
            className="px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Bulk Ingest Vendors via Excel / CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-700" />
            Import Excel
          </button>

          <button
            onClick={handleExportVendors}
            className="px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5 text-slate-600" />
            Export Excel
          </button>

          {currentUserRole !== 'Auditor' && (
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Add Vendor
            </button>
          )}
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search name, code, PAN, GSTIN, Udyam..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:bg-white focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto overflow-x-auto">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-semibold shrink-0">Category:</span>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:outline-hidden"
            >
              <option value="ALL">All Categories</option>
              <option value="Micro">Micro</option>
              <option value="Small">Small</option>
              <option value="Medium">Medium</option>
              <option value="Not Applicable">Non-MSME</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-semibold shrink-0">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:outline-hidden"
            >
              <option value="ALL">All Statuses</option>
              <option value="Verified">Verified</option>
              <option value="Pending">Pending</option>
              <option value="Mismatch">Mismatch</option>
              <option value="Not Verified">Not Verified</option>
              <option value="Not Found">Not Found</option>
            </select>
          </div>
        </div>
      </div>

      {/* Vendor Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
              <tr>
                <th className="px-4 py-3">Vendor Details</th>
                <th className="px-4 py-3">Tax Identifiers</th>
                <th className="px-4 py-3">Udyam Registration</th>
                <th className="px-4 py-3">MSME Category</th>
                <th className="px-4 py-3">Verification</th>
                <th className="px-4 py-3">Credit Terms</th>
                <th className="px-4 py-3">Certificate</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredVendors.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    No vendors found matching the current search & filters.
                  </td>
                </tr>
              ) : (
                filteredVendors.map((vendor) => {
                  const panMatch = checkPanGstinMatch(vendor.pan, vendor.gstin);

                  return (
                    <tr key={vendor.id} className="hover:bg-slate-50/80 transition-colors">
                      {/* Vendor Code & Name */}
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-slate-900">{vendor.vendorName}</div>
                        <div className="text-[11px] text-slate-500 font-mono">{vendor.vendorCode}</div>
                        {vendor.contactPerson && (
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Contact: {vendor.contactPerson}
                          </div>
                        )}
                      </td>

                      {/* Tax Identifiers */}
                      <td className="px-4 py-3.5 space-y-0.5">
                        <div className="font-mono text-[11px] text-slate-700">
                          PAN: <strong className="text-slate-900">{vendor.pan || '—'}</strong>
                        </div>
                        <div className="font-mono text-[11px] text-slate-700 flex items-center gap-1">
                          GST: <span className="text-slate-800">{vendor.gstin || '—'}</span>
                          {vendor.pan && vendor.gstin && !panMatch && (
                            <span
                              title="PAN embedded in GSTIN does not match declared PAN!"
                              className="px-1 py-0.2 bg-rose-100 text-rose-700 font-bold rounded text-[9px]"
                            >
                              Mismatch
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Udyam Registration */}
                      <td className="px-4 py-3.5">
                        {vendor.udyamNumber ? (
                          <div className="space-y-0.5">
                            <span className="font-mono font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded text-[11px] border border-emerald-200 inline-block">
                              {vendor.udyamNumber}
                            </span>
                            {vendor.udyamRegistrationDate && (
                              <div className="text-[10px] text-slate-400">
                                Reg: {formatDate(vendor.udyamRegistrationDate)}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px] italic">Not Registered</span>
                        )}
                      </td>

                      {/* MSME Category */}
                      <td className="px-4 py-3.5">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[11px] font-bold inline-block ${
                            vendor.msmeCategory === 'Micro'
                              ? 'bg-blue-100 text-blue-800 border border-blue-200'
                              : vendor.msmeCategory === 'Small'
                              ? 'bg-teal-100 text-teal-800 border border-teal-200'
                              : vendor.msmeCategory === 'Medium'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {vendor.msmeCategory}
                        </span>
                        <div className="text-[10px] text-slate-400 mt-0.5">{vendor.majorActivity}</div>
                      </td>

                      {/* Verification Status */}
                      <td className="px-4 py-3.5">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold inline-flex items-center gap-1.5 ${
                            vendor.verificationStatus === 'Verified'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : vendor.verificationStatus === 'Pending'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : vendor.verificationStatus === 'Mismatch'
                              ? 'bg-rose-100 text-rose-800 border border-rose-200'
                              : 'bg-slate-100 text-slate-700 border border-slate-200'
                          }`}
                        >
                          {vendor.verificationStatus === 'Verified' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                          {vendor.verificationStatus === 'Pending' && <AlertTriangle className="w-3 h-3 text-amber-600" />}
                          {vendor.verificationStatus === 'Mismatch' && <ShieldAlert className="w-3 h-3 text-rose-600" />}
                          {vendor.verificationStatus}
                        </span>
                        {vendor.verificationDate && (
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Verified: {formatDate(vendor.verificationDate)}
                          </div>
                        )}
                      </td>

                      {/* Credit Terms */}
                      <td className="px-4 py-3.5 text-[11px]">
                        <div className="font-semibold text-slate-800">
                          {vendor.agreedCreditDays} Days Credit
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {vendor.hasWrittenAgreement ? 'Written Agreement: Yes' : 'No written agreement (15d limit)'}
                        </div>
                      </td>

                      {/* Certificate */}
                      <td className="px-4 py-3.5">
                        {vendor.certificateFileName ? (
                          <button
                            onClick={() => setSelectedCertVendor(vendor)}
                            className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[11px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                          >
                            <FileText className="w-3 h-3 text-emerald-600" />
                            View Doc
                          </button>
                        ) : (
                          <span className="text-[11px] text-amber-600 font-semibold flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> Missing
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {vendor.verificationStatus !== 'Verified' && currentUserRole !== 'Auditor' && (
                            <button
                              onClick={() => verifyVendorPortal(vendor.id)}
                              className="p-1.5 text-emerald-700 hover:bg-emerald-50 rounded-lg transition-colors cursor-pointer"
                              title="Verify on Udyam Portal"
                            >
                              <ShieldCheck className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => setSelectedHistoryVendor(vendor)}
                            className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                            title="View Verification History"
                          >
                            <History className="w-4 h-4" />
                          </button>
                          {currentUserRole !== 'Auditor' && (
                            <>
                              <button
                                onClick={() => setEditingVendor(vendor)}
                                className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                                title="Edit Vendor"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => deleteVendor(vendor.id)}
                                className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                                title="Delete Vendor"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Vendor Modal */}
      {(isAddModalOpen || editingVendor) && (
        <VendorFormModal
          isOpen={isAddModalOpen || Boolean(editingVendor)}
          initialVendor={editingVendor}
          onClose={() => {
            setIsAddModalOpen(false);
            setEditingVendor(null);
          }}
          onSave={(data) => {
            if (editingVendor) {
              updateVendor(editingVendor.id, data, 'Updated vendor master details');
            } else {
              addVendor(data as any);
            }
            setIsAddModalOpen(false);
            setEditingVendor(null);
          }}
        />
      )}

      {/* Verification History Modal */}
      {selectedHistoryVendor && (
        <VerificationHistoryModal
          vendor={selectedHistoryVendor}
          onClose={() => setSelectedHistoryVendor(null)}
        />
      )}

      {/* Certificate Viewer Modal */}
      {selectedCertVendor && (
        <CertificateViewerModal
          vendor={selectedCertVendor}
          onClose={() => setSelectedCertVendor(null)}
        />
      )}

      {/* Excel Upload Modal */}
      <ExcelUploadModal
        isOpen={isExcelModalOpen}
        onClose={() => setIsExcelModalOpen(false)}
        type="vendors"
      />
    </div>
  );
};

/* --- Vendor Form Modal --- */
interface VendorFormModalProps {
  isOpen: boolean;
  initialVendor: Vendor | null;
  onClose: () => void;
  onSave: (data: Partial<Vendor>) => void;
}

const VendorFormModal: React.FC<VendorFormModalProps> = ({ isOpen, initialVendor, onClose, onSave }) => {
  const [vendorCode, setVendorCode] = useState(initialVendor?.vendorCode || `V-${Math.floor(1000 + Math.random() * 9000)}`);
  const [vendorName, setVendorName] = useState(initialVendor?.vendorName || '');
  const [pan, setPan] = useState(initialVendor?.pan || '');
  const [gstin, setGstin] = useState(initialVendor?.gstin || '');
  const [udyamNumber, setUdyamNumber] = useState(initialVendor?.udyamNumber || '');
  const [msmeCategory, setMsmeCategory] = useState<MSMECategory>(initialVendor?.msmeCategory || 'Micro');
  const [majorActivity, setMajorActivity] = useState<MajorActivity>(initialVendor?.majorActivity || 'Manufacturing');
  const [udyamDate, setUdyamDate] = useState(initialVendor?.udyamRegistrationDate || '');
  const [hasWrittenAgreement, setHasWrittenAgreement] = useState(initialVendor?.hasWrittenAgreement ?? true);
  const [agreedCreditDays, setAgreedCreditDays] = useState(initialVendor?.agreedCreditDays || 30);
  const [contactPerson, setContactPerson] = useState(initialVendor?.contactPerson || '');
  const [email, setEmail] = useState(initialVendor?.email || '');
  const [phone, setPhone] = useState(initialVendor?.phone || '');
  const [remarks, setRemarks] = useState(initialVendor?.remarks || '');
  const [certificateFileName, setCertificateFileName] = useState(initialVendor?.certificateFileName || '');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendorName.trim()) return;

    const isMSME = msmeCategory !== 'Not Applicable';

    onSave({
      vendorCode,
      vendorName,
      pan: pan.trim().toUpperCase(),
      gstin: gstin.trim().toUpperCase(),
      udyamNumber: udyamNumber.trim().toUpperCase(),
      isMSME,
      msmeStatus: isMSME ? 'MSME' : 'Non-MSME',
      msmeCategory,
      majorActivity,
      udyamRegistrationDate: udyamDate,
      verificationStatus: initialVendor?.verificationStatus || (udyamNumber ? 'Pending' : 'Not Verified'),
      hasWrittenAgreement,
      agreedCreditDays: Number(agreedCreditDays),
      contactPerson,
      email,
      phone,
      certificateFileName: certificateFileName || (udyamNumber ? `Udyam_${vendorName.replace(/\s+/g, '_')}.pdf` : ''),
      remarks,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in-95 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-emerald-700" />
            <h3 className="font-bold text-slate-800 text-base">
              {initialVendor ? 'Edit Vendor Master Record' : 'Onboard New Vendor'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Vendor Code *</label>
              <input
                type="text"
                required
                value={vendorCode}
                onChange={(e) => setVendorCode(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg font-mono focus:border-emerald-500 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Vendor Entity Name *</label>
              <input
                type="text"
                required
                value={vendorName}
                onChange={(e) => setVendorName(e.target.value)}
                placeholder="e.g. Apex Precision Engineering Pvt Ltd"
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Permanent Account Number (PAN) *</label>
              <input
                type="text"
                required
                maxLength={10}
                value={pan}
                onChange={(e) => setPan(e.target.value.toUpperCase())}
                placeholder="e.g. AACFA1234D"
                className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg uppercase focus:border-emerald-500 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">GSTIN Number</label>
              <input
                type="text"
                maxLength={15}
                value={gstin}
                onChange={(e) => setGstin(e.target.value.toUpperCase())}
                placeholder="e.g. 27AACFA1234D1Z5"
                className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg uppercase focus:border-emerald-500 focus:outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Udyam Registration Number</label>
              <input
                type="text"
                value={udyamNumber}
                onChange={(e) => setUdyamNumber(e.target.value.toUpperCase())}
                placeholder="UDYAM-MH-01-0012345"
                className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg uppercase focus:border-emerald-500 focus:outline-hidden"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">MSME Classification Category</label>
              <select
                value={msmeCategory}
                onChange={(e) => setMsmeCategory(e.target.value as MSMECategory)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500 focus:outline-hidden"
              >
                <option value="Micro">Micro Enterprise (Investment ≤ 1 Cr & TO ≤ 5 Cr)</option>
                <option value="Small">Small Enterprise (Investment ≤ 10 Cr & TO ≤ 50 Cr)</option>
                <option value="Medium">Medium Enterprise (Investment ≤ 50 Cr & TO ≤ 250 Cr)</option>
                <option value="Not Applicable">Non-MSME / Large Corporate</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Major Activity</label>
              <select
                value={majorActivity}
                onChange={(e) => setMajorActivity(e.target.value as MajorActivity)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500 focus:outline-hidden"
              >
                <option value="Manufacturing">Manufacturing</option>
                <option value="Services">Services</option>
                <option value="Trading">Trading</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Udyam Registration Date</label>
              <input
                type="date"
                value={udyamDate}
                onChange={(e) => setUdyamDate(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500 focus:outline-hidden"
              />
            </div>
          </div>

          {/* Payment Terms Section */}
          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
            <h4 className="text-xs font-bold text-slate-800">Commercial & Payment Agreement</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="writtenAgr"
                  checked={hasWrittenAgreement}
                  onChange={(e) => setHasWrittenAgreement(e.target.checked)}
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                />
                <label htmlFor="writtenAgr" className="text-xs font-medium text-slate-700 cursor-pointer">
                  Has Written Agreement / PO Terms
                </label>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Agreed Credit Days (Max 45 under Sec 15)
                </label>
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={agreedCreditDays}
                  onChange={(e) => setAgreedCreditDays(Number(e.target.value))}
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500 focus:outline-hidden"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Contact Person</label>
              <input
                type="text"
                value={contactPerson}
                onChange={(e) => setContactPerson(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Phone</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Remarks & Compliance Notes</label>
            <textarea
              rows={2}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="e.g. Certificate verified against Ministry of MSME Udyam portal."
              className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:border-emerald-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold rounded-lg shadow-xs"
            >
              Save Vendor Record
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/* --- Verification History Modal --- */
const VerificationHistoryModal: React.FC<{ vendor: Vendor; onClose: () => void }> = ({ vendor, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div>
            <h3 className="font-bold text-slate-800 text-sm">Udyam Verification Audit Trail</h3>
            <p className="text-xs text-slate-500">{vendor.vendorName} ({vendor.vendorCode})</p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
          {vendor.verificationHistory.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No historical verification checks logged yet.
            </div>
          ) : (
            vendor.verificationHistory.map((item, idx) => (
              <div key={item.id || idx} className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">{formatDate(item.timestamp)}</span>
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded">
                    {item.newStatus}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Verified by: <strong>{item.verifiedBy}</strong> | Udyam Checked: <span className="font-mono">{item.udyamChecked}</span>
                </div>
                {item.portalResponse && (
                  <div className="p-2 bg-white rounded border border-slate-200 font-mono text-[10px] text-slate-700">
                    {item.portalResponse}
                  </div>
                )}
                {item.remarks && <p className="text-[11px] text-slate-600 italic">{item.remarks}</p>}
              </div>
            ))
          )}
        </div>

        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 text-right">
          <button onClick={onClose} className="px-4 py-1.5 bg-slate-800 text-white text-xs font-semibold rounded-lg">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

/* --- Certificate Viewer Modal --- */
const CertificateViewerModal: React.FC<{ vendor: Vendor; onClose: () => void }> = ({ vendor, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div>
            <h3 className="font-bold text-slate-800 text-sm">MSME Udyam Registration Certificate</h3>
            <p className="text-xs text-slate-500">{vendor.vendorName}</p>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="border-2 border-dashed border-emerald-300 bg-emerald-50/40 rounded-xl p-6 text-center space-y-2">
            <ShieldCheck className="w-12 h-12 text-emerald-600 mx-auto" />
            <h4 className="font-bold text-slate-900 text-sm">Government of India - Ministry of MSME</h4>
            <div className="font-mono text-xs font-bold text-emerald-800 bg-white px-3 py-1 rounded-full border border-emerald-200 inline-block">
              {vendor.udyamNumber || 'UDYAM-REGISTRATION'}
            </div>
            <div className="text-xs text-slate-600 pt-2 space-y-1 text-left bg-white p-4 rounded-lg border border-slate-200">
              <div className="flex justify-between">
                <span className="text-slate-400">Enterprise Name:</span>
                <span className="font-bold text-slate-800">{vendor.vendorName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Classification:</span>
                <span className="font-bold text-slate-800">{vendor.msmeCategory} Enterprise</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Major Activity:</span>
                <span className="font-bold text-slate-800">{vendor.majorActivity}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">PAN / GSTIN:</span>
                <span className="font-bold text-slate-800 font-mono">{vendor.pan} / {vendor.gstin}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Certificate File:</span>
                <span className="font-mono text-emerald-700">{vendor.certificateFileName}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="px-6 py-3 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-xs">
          <span className="text-slate-400">Document authenticated by Corporate Accounts</span>
          <button onClick={onClose} className="px-4 py-1.5 bg-slate-800 text-white font-semibold rounded-lg">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
