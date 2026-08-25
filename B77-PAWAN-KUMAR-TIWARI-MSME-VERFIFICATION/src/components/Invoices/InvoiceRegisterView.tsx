import React, { useState, useRef } from 'react';
import {
  FileText,
  Search,
  Plus,
  Filter,
  Download,
  Upload,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Edit2,
  Trash2,
  CreditCard,
  Building2,
  ShieldAlert,
  ArrowRight,
  Calculator,
  X,
  Sparkles,
  Image,
  Eye,
  FileCheck,
  FileSpreadsheet,
  RefreshCw,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Invoice, MSMECategory } from '../../types';
import { formatINR, formatDate, getDaysDifference } from '../../utils/formatters';
import { exportTableToExcel } from '../../utils/excelService';
import { calculateMSMEDueDate } from '../../utils/calculator';
import { InvoiceDocUploadModal } from './InvoiceDocUploadModal';
import { InvoiceDocViewerModal } from './InvoiceDocViewerModal';
import { ExcelUploadModal } from '../Common/ExcelUploadModal';
import { parseInvoiceFile } from '../../utils/invoiceParserService';

export const InvoiceRegisterView: React.FC = () => {
  const {
    invoices,
    vendors,
    addInvoice,
    updateInvoice,
    deleteInvoice,
    currentUserRole,
    asOfDate,
    overrideInvoiceDueDate,
    statutoryRules,
    setActiveTab,
  } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [vendorFilter, setVendorFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isDocUploadModalOpen, setIsDocUploadModalOpen] = useState(false);
  const [isExcelModalOpen, setIsExcelModalOpen] = useState(false);
  const [viewingDocInvoice, setViewingDocInvoice] = useState<Invoice | null>(null);
  const [editingInvoice, setEditingInvoice] = useState<Invoice | null>(null);
  const [overrideModalInvoice, setOverrideModalInvoice] = useState<Invoice | null>(null);
  const [selectedInvoiceForDetails, setSelectedInvoiceForDetails] = useState<Invoice | null>(null);

  const filteredInvoices = invoices.filter((inv) => {
    const matchesSearch =
      inv.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.vendorName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.poNumber.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesVendor = vendorFilter === 'ALL' || inv.vendorId === vendorFilter;
    const matchesStatus =
      statusFilter === 'ALL' ||
      inv.status === statusFilter ||
      (statusFilter === 'Overdue' && inv.outstandingAmount > 0 && new Date(asOfDate) > new Date(inv.finalDueDate));

    return matchesSearch && matchesVendor && matchesStatus;
  });

  const handleExportInvoices = () => {
    const exportData = filteredInvoices.map((inv) => ({
      'Invoice Number': inv.invoiceNumber,
      'Vendor Code': inv.vendorCode,
      'Vendor Name': inv.vendorName,
      'MSME Category': inv.msmeCategory,
      'Invoice Date': formatDate(inv.invoiceDate),
      'Basic Amount (₹)': inv.invoiceAmount,
      'GST (₹)': inv.gstAmount,
      'Total Amount (₹)': inv.totalInvoiceAmount,
      'PO Number': inv.poNumber,
      'PO Date': formatDate(inv.poDate),
      'Material / Service': inv.materialDescription,
      'MRN Date': formatDate(inv.mrnDate),
      'Acceptance Date': formatDate(inv.acceptanceDate),
      'Agreed Terms': inv.agreedPaymentTerms,
      'Statutory Limit (Days)': inv.statutoryLimitDays,
      'Final Due Date': formatDate(inv.finalDueDate),
      'Amount Paid (₹)': inv.amountPaid,
      'Outstanding (₹)': inv.outstandingAmount,
      Status: inv.status,
      'Has Attachment': inv.attachmentUrl ? 'Yes' : 'No',
      'Financial Year': inv.financialYear,
    }));
    exportTableToExcel(exportData, 'MSME_Invoice_Register', 'Invoices');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">MSME Invoice Register & Statutory Due Dates</h2>
          <p className="text-xs text-slate-500">
            Track material receipt, acceptance, Section 15 statutory caps (45/15 days), document attachments and payment obligations
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Upload PDF & JPEG Invoices with AI OCR */}
          {currentUserRole !== 'Auditor' && (
            <>
              <button
                onClick={() => setIsDocUploadModalOpen(true)}
                className="px-3.5 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-bold rounded-lg shadow-2xs flex items-center gap-1.5 transition-all cursor-pointer"
                title="Upload supplier invoice documents in PDF or JPEG with Gemini AI extraction"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload PDF / JPEG</span>
                <span className="px-1.5 py-0.2 bg-blue-600 text-white rounded text-[9px] font-extrabold flex items-center gap-0.5">
                  <Sparkles className="w-2.5 h-2.5" /> AI
                </span>
              </button>

              <button
                onClick={() => setIsExcelModalOpen(true)}
                className="px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-bold rounded-lg shadow-2xs flex items-center gap-1.5 transition-all cursor-pointer"
                title="Bulk Ingest Invoices via Excel / CSV Spreadsheet"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-700" />
                <span>Import Excel</span>
              </button>
            </>
          )}

          <button
            onClick={handleExportInvoices}
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
              Register Invoice
            </button>
          )}
        </div>
      </div>

      {/* Statutory Rules Indicator Banner */}
      <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-800">Statutory Rules Active:</span>
          <span className="text-slate-600">
            Written Agreement Limit: <strong>{statutoryRules.maxCreditDaysWithAgreement} Days</strong> | No Agreement Limit: <strong>{statutoryRules.maxCreditDaysWithoutAgreement} Days</strong> | Deemed Window: <strong>{statutoryRules.deemedAcceptanceWindowDays} Days</strong>
          </span>
        </div>
        <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">
          Section 15 & 43B(h) Compliant Engine
        </span>
      </div>

      {/* Search and Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search invoice no, vendor, PO..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:bg-white focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto overflow-x-auto">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-semibold shrink-0">Vendor:</span>
            <select
              value={vendorFilter}
              onChange={(e) => setVendorFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700 max-w-[200px]"
            >
              <option value="ALL">All Vendors ({vendors.length})</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.vendorName} ({v.vendorCode})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-semibold shrink-0">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-medium text-slate-700"
            >
              <option value="ALL">All Invoices</option>
              <option value="Unpaid">Unpaid</option>
              <option value="Partially Paid">Partially Paid</option>
              <option value="Overdue">Overdue Past Statutory Limit</option>
              <option value="Paid">Fully Settled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Invoice Register Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
              <tr>
                <th className="px-4 py-3">Invoice Details</th>
                <th className="px-4 py-3">Vendor / Category</th>
                <th className="px-4 py-3">Statutory Timeline Flow</th>
                <th className="px-4 py-3">Due Date & Delay</th>
                <th className="px-4 py-3 text-right">Invoice Amount</th>
                <th className="px-4 py-3 text-right">Outstanding</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    No invoices found matching criteria.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => {
                  const delayDays = getDaysDifference(inv.finalDueDate, asOfDate);
                  const isOverdue = inv.outstandingAmount > 0 && delayDays > 0;
                  const isPdf = inv.attachmentType === 'pdf' || inv.attachmentFileName?.toLowerCase().endsWith('.pdf');

                  return (
                    <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors">
                      {/* Invoice Details */}
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-slate-900 flex items-center gap-1.5 flex-wrap">
                          <span>{inv.invoiceNumber}</span>
                          {inv.isDueDateManuallyOverridden && (
                            <span
                              title={`Due Date manually overridden: ${inv.overrideReason}`}
                              className="px-1.5 py-0.2 bg-purple-100 text-purple-800 text-[9px] font-bold rounded"
                            >
                              Override
                            </span>
                          )}
                          {/* Attachment indicator pill with 1-click preview */}
                          <button
                            onClick={() => setViewingDocInvoice(inv)}
                            className={`px-1.5 py-0.2 rounded text-[9px] font-bold inline-flex items-center gap-1 transition-colors cursor-pointer ${
                              inv.attachmentUrl
                                ? isPdf
                                  ? 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
                                  : 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                            title={inv.attachmentUrl ? `View Original ${isPdf ? 'PDF' : 'JPEG'} Document` : 'View Invoice Document Voucher'}
                          >
                            {inv.attachmentUrl ? (
                              isPdf ? <FileText className="w-2.5 h-2.5" /> : <Image className="w-2.5 h-2.5" />
                            ) : (
                              <Eye className="w-2.5 h-2.5" />
                            )}
                            <span>{inv.attachmentUrl ? (isPdf ? 'PDF' : 'JPEG') : 'Doc'}</span>
                          </button>
                        </div>
                        <div className="text-[11px] text-slate-500">Date: {formatDate(inv.invoiceDate)}</div>
                        <div className="text-[10px] text-slate-400 font-mono">PO: {inv.poNumber}</div>
                      </td>

                      {/* Vendor & Category */}
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-slate-800">{inv.vendorName}</div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                              inv.msmeCategory === 'Micro'
                                ? 'bg-blue-100 text-blue-800'
                                : inv.msmeCategory === 'Small'
                                ? 'bg-teal-100 text-teal-800'
                                : inv.msmeCategory === 'Medium'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {inv.msmeCategory}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {inv.hasWrittenAgreement ? 'Agr: Yes' : 'Agr: No (15d)'}
                          </span>
                        </div>
                      </td>

                      {/* Statutory Timeline Flow */}
                      <td className="px-4 py-3.5">
                        <div className="text-[11px] space-y-0.5">
                          <div className="text-slate-700">
                            Acceptance: <strong>{formatDate(inv.acceptanceDate)}</strong>
                          </div>
                          <div className="text-[10px] text-slate-500 flex items-center gap-1">
                            <span>Credit: {inv.creditDays}d</span>
                            <span>→</span>
                            <span className="font-semibold text-emerald-800">
                              Cap: {inv.statutoryLimitDays}d (Sec 15)
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Due Date & Delay */}
                      <td className="px-4 py-3.5">
                        <div className="font-bold text-slate-900 text-xs">
                          {formatDate(inv.finalDueDate)}
                        </div>
                        {inv.outstandingAmount > 0 ? (
                          isOverdue ? (
                            <span className="px-2 py-0.5 bg-rose-100 text-rose-800 font-extrabold rounded-md text-[10px] inline-block mt-0.5">
                              🔴 {delayDays} Days Overdue
                            </span>
                          ) : (
                            <span className="text-[10px] text-emerald-700 font-semibold inline-block mt-0.5">
                              🟢 {Math.abs(delayDays)} days remaining
                            </span>
                          )
                        ) : (
                          <span className="text-[10px] text-slate-400">Settled</span>
                        )}
                      </td>

                      {/* Total Invoice Amount */}
                      <td className="px-4 py-3.5 text-right">
                        <div className="font-bold text-slate-900">{formatINR(inv.totalInvoiceAmount)}</div>
                        <div className="text-[10px] text-slate-400">GST: {formatINR(inv.gstAmount)}</div>
                      </td>

                      {/* Outstanding */}
                      <td className="px-4 py-3.5 text-right">
                        <div className={`font-bold ${inv.outstandingAmount > 0 ? 'text-rose-700' : 'text-slate-500'}`}>
                          {formatINR(inv.outstandingAmount)}
                        </div>
                        {inv.amountPaid > 0 && (
                          <div className="text-[10px] text-emerald-600 font-semibold">
                            Paid: {formatINR(inv.amountPaid)}
                          </div>
                        )}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold inline-block ${
                            inv.status === 'Paid'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                              : inv.status === 'Partially Paid'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : isOverdue
                              ? 'bg-rose-100 text-rose-800 border border-rose-200'
                              : 'bg-blue-100 text-blue-800 border border-blue-200'
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {/* View Document */}
                          <button
                            onClick={() => setViewingDocInvoice(inv)}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer"
                            title="View Attached Invoice Document (PDF/JPEG)"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          <button
                            onClick={() => setSelectedInvoiceForDetails(inv)}
                            className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                            title="View Calculation & Statutory Breakdown"
                          >
                            <Calculator className="w-4 h-4 text-emerald-700" />
                          </button>
                          {currentUserRole !== 'Auditor' && (
                            <>
                              <button
                                onClick={() => setOverrideModalInvoice(inv)}
                                className="p-1.5 text-purple-700 hover:bg-purple-50 rounded-lg transition-colors cursor-pointer"
                                title="Override Due Date (Audit Controlled)"
                              >
                                <Clock className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setEditingInvoice(inv)}
                                className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                                title="Edit Invoice"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => deleteInvoice(inv.id)}
                                className="p-1.5 text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                                title="Delete Invoice"
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

      {/* Add / Edit Invoice Modal */}
      {(isAddModalOpen || editingInvoice) && (
        <InvoiceFormModal
          isOpen={isAddModalOpen || Boolean(editingInvoice)}
          initialInvoice={editingInvoice}
          vendors={vendors}
          rules={statutoryRules}
          onClose={() => {
            setIsAddModalOpen(false);
            setEditingInvoice(null);
          }}
          onSave={(data) => {
            if (editingInvoice) {
              updateInvoice(editingInvoice.id, data, 'Updated invoice register details');
              setIsAddModalOpen(false);
              setEditingInvoice(null);
            } else {
              const res = addInvoice(data as any);
              if (!res.success) {
                alert(res.message);
                return;
              }
              setIsAddModalOpen(false);
              setEditingInvoice(null);
            }
          }}
        />
      )}

      {/* Document Upload Modal (PDF / JPEG Batch & AI OCR) */}
      <InvoiceDocUploadModal
        isOpen={isDocUploadModalOpen}
        onClose={() => setIsDocUploadModalOpen(false)}
      />

      {/* Document Viewer Modal */}
      <InvoiceDocViewerModal
        invoice={viewingDocInvoice}
        onClose={() => setViewingDocInvoice(null)}
      />

      {/* Manual Due Date Override Modal */}
      {overrideModalInvoice && (
        <DueDateOverrideModal
          invoice={overrideModalInvoice}
          onClose={() => setOverrideModalInvoice(null)}
          onOverride={(newDate, reason) => {
            overrideInvoiceDueDate(overrideModalInvoice.id, newDate, reason);
            setOverrideModalInvoice(null);
          }}
        />
      )}

      {/* Excel Upload Modal */}
      <ExcelUploadModal
        isOpen={isExcelModalOpen}
        onClose={() => setIsExcelModalOpen(false)}
        type="invoices"
      />
    </div>
  );
};

/* --- Invoice Form Modal with Live Statutory Due Date Determination & Direct PDF/JPEG Auto-Fill --- */
interface InvoiceFormModalProps {
  isOpen: boolean;
  initialInvoice: Invoice | null;
  vendors: any[];
  rules: any;
  onClose: () => void;
  onSave: (data: Partial<Invoice>) => void;
}

const InvoiceFormModal: React.FC<InvoiceFormModalProps> = ({
  isOpen,
  initialInvoice,
  vendors,
  rules,
  onClose,
  onSave,
}) => {
  const [vendorId, setVendorId] = useState(initialInvoice?.vendorId || vendors[0]?.id || '');
  const [invoiceNumber, setInvoiceNumber] = useState(initialInvoice?.invoiceNumber || '');
  const [invoiceDate, setInvoiceDate] = useState(initialInvoice?.invoiceDate || new Date().toISOString().split('T')[0]);
  const [invoiceAmount, setInvoiceAmount] = useState(initialInvoice?.invoiceAmount || 100000);
  const [gstRate, setGstRate] = useState(18);
  const [gstAmount, setGstAmount] = useState(initialInvoice?.gstAmount || 18000);
  const [poNumber, setPoNumber] = useState(initialInvoice?.poNumber || '');
  const [poDate, setPoDate] = useState(initialInvoice?.poDate || invoiceDate);
  const [materialDescription, setMaterialDescription] = useState(initialInvoice?.materialDescription || '');
  const [mrnDate, setMrnDate] = useState(initialInvoice?.mrnDate || invoiceDate);
  const [acceptanceDate, setAcceptanceDate] = useState(initialInvoice?.acceptanceDate || invoiceDate);
  const [agreedCreditDays, setAgreedCreditDays] = useState(initialInvoice?.creditDays || 30);
  const [hasWrittenAgreement, setHasWrittenAgreement] = useState(initialInvoice?.hasWrittenAgreement ?? true);
  const [agreedPaymentTerms, setAgreedPaymentTerms] = useState(initialInvoice?.agreedPaymentTerms || '30 Days from Acceptance');

  // Attachment state
  const [attachmentUrl, setAttachmentUrl] = useState<string | undefined>(initialInvoice?.attachmentUrl);
  const [attachmentFileName, setAttachmentFileName] = useState<string | undefined>(initialInvoice?.attachmentFileName);
  const [attachmentType, setAttachmentType] = useState<'pdf' | 'jpeg' | 'png' | undefined>(initialInvoice?.attachmentType);
  const [isExtracting, setIsExtracting] = useState(false);
  const singleFileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const selectedVendor = vendors.find((v) => v.id === vendorId) || vendors[0];
  const isMSME = selectedVendor ? selectedVendor.isMSME : true;

  // Auto calculate GST when basic amount changes
  const handleBasicAmountChange = (val: number) => {
    setInvoiceAmount(val);
    setGstAmount(Math.round((val * gstRate) / 100));
  };

  // Handle single invoice document upload with instant AI OCR auto-fill
  const handleSingleDocUpload = async (file: File) => {
    setIsExtracting(true);
    try {
      const extracted = await parseInvoiceFile(file, vendors, rules);
      setAttachmentUrl(extracted.fileDataUrl);
      setAttachmentFileName(extracted.fileName);
      setAttachmentType(extracted.fileType);

      // Auto-populate fields
      if (extracted.invoiceNumber) setInvoiceNumber(extracted.invoiceNumber);
      if (extracted.invoiceDate) setInvoiceDate(extracted.invoiceDate);
      if (extracted.basicAmount) {
        setInvoiceAmount(extracted.basicAmount);
        setGstAmount(extracted.gstAmount);
      }
      if (extracted.poNumber) setPoNumber(extracted.poNumber);
      if (extracted.poDate) setPoDate(extracted.poDate);
      if (extracted.materialDescription) setMaterialDescription(extracted.materialDescription);
      if (extracted.mrnDate) setMrnDate(extracted.mrnDate);
      if (extracted.acceptanceDate) setAcceptanceDate(extracted.acceptanceDate);
      if (extracted.agreedCreditDays) setAgreedCreditDays(extracted.agreedCreditDays);
      if (extracted.hasWrittenAgreement !== undefined) setHasWrittenAgreement(extracted.hasWrittenAgreement);
      if (extracted.matchedVendorId) setVendorId(extracted.matchedVendorId);
    } catch (err: any) {
      console.error('Error auto-filling from document:', err);
    } finally {
      setIsExtracting(false);
    }
  };

  // Live Statutory Due Date determination
  const liveCalculation = calculateMSMEDueDate(
    mrnDate,
    acceptanceDate,
    hasWrittenAgreement,
    agreedCreditDays,
    isMSME,
    rules
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoiceNumber.trim()) return;

    onSave({
      vendorId: selectedVendor.id,
      vendorName: selectedVendor.vendorName,
      vendorCode: selectedVendor.vendorCode,
      msmeCategory: selectedVendor.msmeCategory,
      isMSME: selectedVendor.isMSME,
      invoiceNumber: invoiceNumber.trim(),
      invoiceDate,
      invoiceAmount: Number(invoiceAmount),
      gstAmount: Number(gstAmount),
      totalInvoiceAmount: Number(invoiceAmount) + Number(gstAmount),
      poNumber: poNumber.trim() || `PO/${invoiceNumber}`,
      poDate,
      materialDescription: materialDescription.trim() || 'General Supply / Service',
      mrnDate,
      acceptanceDate: liveCalculation.effectiveAcceptanceDate,
      deemedAcceptanceDate: liveCalculation.deemedAcceptanceDate,
      hasWrittenAgreement,
      agreedPaymentTerms,
      creditDays: liveCalculation.effectiveCreditDays,
      statutoryLimitDays: liveCalculation.statutoryLimitDays,
      finalDueDate: liveCalculation.finalDueDate,
      attachmentUrl,
      attachmentFileName,
      attachmentType,
      disputeFlag: false,
      financialYear: '2026-27',
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden animate-in fade-in zoom-in-95 max-h-[92vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-700" />
            <div>
              <h3 className="font-bold text-slate-800 text-base">
                {initialInvoice ? 'Edit Registered Invoice' : 'Register MSME Vendor Invoice'}
              </h3>
              <p className="text-xs text-slate-500">Includes Section 15 statutory due date calculator & PDF/JPEG attachment</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
          {/* Document Attachment & AI Auto-fill Box */}
          <div className="bg-blue-50/60 border border-blue-200 rounded-xl p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold shrink-0">
                {attachmentType === 'pdf' ? <FileText className="w-5 h-5" /> : <Image className="w-5 h-5" />}
              </div>
              <div>
                <div className="font-bold text-slate-800 flex items-center gap-1.5">
                  <span>{attachmentFileName || 'Attach Invoice Document (PDF or JPEG)'}</span>
                  {attachmentFileName && (
                    <span className="px-1.5 py-0.2 bg-emerald-100 text-emerald-800 text-[9px] font-bold rounded">
                      Attached
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500">
                  Upload file to auto-populate invoice metadata using Gemini AI OCR
                </div>
              </div>
            </div>

            <div>
              <input
                ref={singleFileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,image/jpeg,image/png,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleSingleDocUpload(e.target.files[0]);
                  }
                }}
              />
              <button
                type="button"
                disabled={isExtracting}
                onClick={() => singleFileInputRef.current?.click()}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold flex items-center gap-1.5 transition-all shadow-xs cursor-pointer text-xs"
              >
                {isExtracting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Extracting...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{attachmentFileName ? 'Change File' : 'Upload & Auto-fill'}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Vendor Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Select Vendor *</label>
              <select
                required
                value={vendorId}
                onChange={(e) => {
                  const vId = e.target.value;
                  setVendorId(vId);
                  const matched = vendors.find((v) => v.id === vId);
                  if (matched) {
                    setHasWrittenAgreement(matched.hasWrittenAgreement);
                    setAgreedCreditDays(matched.agreedCreditDays);
                  }
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-semibold focus:border-blue-500 focus:outline-hidden"
              >
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.vendorName} ({v.msmeCategory} - {v.vendorCode})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Invoice Number * (Duplicate Protected)</label>
              <input
                type="text"
                required
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                placeholder="e.g. INV/2026/089"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono uppercase focus:border-blue-500 focus:outline-hidden"
              />
            </div>
          </div>

          {/* Amounts */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Invoice Date *</label>
              <input
                type="date"
                required
                value={invoiceDate}
                onChange={(e) => setInvoiceDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Basic Invoice Amount (₹) *</label>
              <input
                type="number"
                required
                min={1}
                value={invoiceAmount}
                onChange={(e) => handleBasicAmountChange(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">GST Amount (₹)</label>
              <input
                type="number"
                value={gstAmount}
                onChange={(e) => setGstAmount(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:border-blue-500"
              />
            </div>
          </div>

          {/* PO & Material */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Purchase Order (PO) No.</label>
              <input
                type="text"
                value={poNumber}
                onChange={(e) => setPoNumber(e.target.value)}
                placeholder="e.g. PO/2026/0441"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">PO Date</label>
              <input
                type="date"
                value={poDate}
                onChange={(e) => setPoDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Material / Service Description</label>
              <input
                type="text"
                value={materialDescription}
                onChange={(e) => setMaterialDescription(e.target.value)}
                placeholder="e.g. Precision CNC Machined Shafts"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg"
              />
            </div>
          </div>

          {/* MRN & Acceptance Dates */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Material Receipt / MRN Date *</label>
              <input
                type="date"
                required
                value={mrnDate}
                onChange={(e) => setMrnDate(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Physical delivery received at plant</span>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">
                Acceptance / Deemed Acceptance Date *
              </label>
              <input
                type="date"
                required
                value={acceptanceDate}
                onChange={(e) => setAcceptanceDate(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">
                Deemed limit: MRN + {rules.deemedAcceptanceWindowDays} days if no objection raised
              </span>
            </div>
          </div>

          {/* Commercial & Statutory Decision Engine Preview */}
          <div className="p-4 bg-blue-50/70 border border-blue-200 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-blue-900 text-xs">
                Statutory Due Date Determination (MSMED Act Section 15)
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-200 text-blue-800">
                Auto Computed
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
              <div>
                <span className="text-slate-500 block">Acceptance Date:</span>
                <strong className="text-slate-900">{formatDate(liveCalculation.effectiveAcceptanceDate)}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Agreed Terms:</span>
                <strong className="text-slate-900">{agreedCreditDays} Days</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Statutory Limit:</span>
                <strong className="text-emerald-800">{liveCalculation.statutoryLimitDays} Days Cap</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Final Due Date:</span>
                <strong className="text-rose-700 font-bold text-xs">{formatDate(liveCalculation.finalDueDate)}</strong>
              </div>
            </div>

            <p className="text-[11px] text-blue-800 bg-white p-2.5 rounded-lg border border-blue-100 italic">
              {liveCalculation.statutoryExplanation}
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-xs cursor-pointer"
            >
              Save Invoice
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/* --- Due Date Override Modal (Audit Controlled) --- */
const DueDateOverrideModal: React.FC<{ invoice: Invoice; onClose: () => void; onOverride: (newDate: string, reason: string) => void }> = ({
  invoice,
  onClose,
  onOverride,
}) => {
  const [newDate, setNewDate] = useState(invoice.finalDueDate);
  const [reason, setReason] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      alert('A mandatory reason is required for manual due date overrides under statutory audit rules.');
      return;
    }
    onOverride(newDate, reason);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-purple-50/50">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-purple-700" />
            <div>
              <h3 className="font-bold text-slate-800 text-sm">Audit Due Date Override</h3>
              <p className="text-[11px] text-slate-500">Invoice: {invoice.invoiceNumber}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          <div>
            <span className="text-slate-500 block mb-1 font-medium">Calculated Statutory Due Date:</span>
            <div className="p-2 bg-slate-100 rounded font-bold text-slate-800 font-mono">
              {formatDate(invoice.finalDueDate)}
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">New Overridden Due Date *</label>
            <input
              type="date"
              required
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg font-semibold text-purple-900 focus:border-purple-500"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Mandatory Audit Justification / Reason *</label>
            <textarea
              required
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Formal dispute resolved on 2026-06-15, contractual extension permitted under revised PO amendment..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:border-purple-500"
            />
          </div>

          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-800">
            ⚠️ This override will be recorded permanently in the Statutory Audit Trail with your user signature and timestamp.
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-purple-700 hover:bg-purple-800 text-white font-bold rounded-lg shadow-xs cursor-pointer"
            >
              Record Override
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
