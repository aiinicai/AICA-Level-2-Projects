import React, { useState, useRef } from 'react';
import {
  X,
  Upload,
  FileText,
  Image,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Building2,
  Trash2,
  Eye,
  EyeOff,
  Calendar,
  IndianRupee,
  ShieldCheck,
  FileSpreadsheet,
  ArrowRight,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { ExtractedInvoiceData, Vendor } from '../../types';
import {
  parseInvoiceFile,
  convertExtractedToInvoice,
} from '../../utils/invoiceParserService';
import { formatINR, formatDate } from '../../utils/formatters';

interface InvoiceDocUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InvoiceDocUploadModal: React.FC<InvoiceDocUploadModalProps> = ({
  isOpen,
  onClose,
}) => {
  const {
    vendors,
    addInvoice,
    addVendor,
    statutoryRules,
    selectedFinancialYear,
  } = useApp();

  const [extractedInvoices, setExtractedInvoices] = useState<ExtractedInvoiceData[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState({ current: 0, total: 0 });
  const [previewFileId, setPreviewFileId] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFilesSelected = async (files: FileList | File[]) => {
    const fileArray = Array.from(files).filter((file) => {
      const ext = file.name.toLowerCase();
      return (
        ext.endsWith('.pdf') ||
        ext.endsWith('.jpg') ||
        ext.endsWith('.jpeg') ||
        ext.endsWith('.png') ||
        file.type === 'application/pdf' ||
        file.type.startsWith('image/')
      );
    });

    if (fileArray.length === 0) {
      alert('Please select valid PDF, JPEG, JPG, or PNG invoice files.');
      return;
    }

    setIsProcessing(true);
    setProcessingProgress({ current: 0, total: fileArray.length });

    const newExtractedList: ExtractedInvoiceData[] = [];

    for (let i = 0; i < fileArray.length; i++) {
      setProcessingProgress({ current: i + 1, total: fileArray.length });
      const file = fileArray[i];
      try {
        const extracted = await parseInvoiceFile(file, vendors, statutoryRules);
        newExtractedList.push(extracted);
      } catch (err: any) {
        console.error('Failed to parse file:', file.name, err);
      }
    }

    setExtractedInvoices((prev) => [...prev, ...newExtractedList]);
    setIsProcessing(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  // Helper to load sample test PDF / JPEG invoices for instant evaluation
  const handleLoadSampleInvoices = async () => {
    setIsProcessing(true);
    setProcessingProgress({ current: 1, total: 3 });

    // Generate 3 realistic mock files
    const today = new Date().toISOString().split('T')[0];

    const sample1: ExtractedInvoiceData = {
      fileId: 'SAMPLE-PDF-1',
      fileName: 'Tax_Invoice_Apex_Precision_SS316.pdf',
      fileType: 'pdf',
      fileSize: 245000,
      fileDataUrl: '',
      invoiceNumber: 'APEX/2026/0892',
      vendorName: 'Apex Precision Engineering Works',
      vendorGstin: '27AACFA1234D1Z8',
      vendorPan: 'AACFA1234D',
      invoiceDate: today,
      basicAmount: 450000,
      gstRate: 18,
      gstAmount: 81000,
      totalAmount: 531000,
      poNumber: 'PO/2026/0710',
      poDate: today,
      materialDescription: 'High Precision CNC Turned Shafts SS316 & Turbine Bushes',
      mrnDate: today,
      acceptanceDate: today,
      agreedCreditDays: 30,
      hasWrittenAgreement: true,
      agreedPaymentTerms: '30 Days Net from MRN',
      udyamNumber: 'UDYAM-MH-01-0012847',
      isMsmeClaimed: true,
      matchedVendorId: vendors[0]?.id || 'VEND-001',
      matchedVendorName: vendors[0]?.vendorName || 'Apex Precision Engineering Works',
      matchedVendorCode: vendors[0]?.vendorCode || 'V-1001',
      msmeCategory: 'Micro',
      confidenceScore: 98,
      extractionEngine: 'Gemini 3.7 Flash AI',
      extractionNotes: [
        'Matched with Micro Enterprise in Vendor Master.',
        'HSN Code 8483 verified. GST calculated at standard 18%.',
      ],
      status: 'EXTRACTED',
    };

    const sample2: ExtractedInvoiceData = {
      fileId: 'SAMPLE-JPEG-2',
      fileName: 'Invoice_ShreeSai_Polymers_Scanned.jpeg',
      fileType: 'jpeg',
      fileSize: 189000,
      fileDataUrl: '',
      invoiceNumber: 'SSP/26-27/0533',
      vendorName: 'Shree Sai Industrial Polymers Pvt Ltd',
      vendorGstin: '24AABCS9876E1Z2',
      vendorPan: 'AABCS9876E',
      invoiceDate: today,
      basicAmount: 820000,
      gstRate: 18,
      gstAmount: 147600,
      totalAmount: 967600,
      poNumber: 'PO/2026/0718',
      poDate: today,
      materialDescription: 'Custom Injection Moulded Polymer Terminal Casings',
      mrnDate: today,
      acceptanceDate: today,
      agreedCreditDays: 45,
      hasWrittenAgreement: true,
      agreedPaymentTerms: '45 Days as per Contract',
      udyamNumber: 'UDYAM-GJ-03-0045892',
      isMsmeClaimed: true,
      matchedVendorId: vendors[1]?.id || 'VEND-002',
      matchedVendorName: vendors[1]?.vendorName || 'Shree Sai Industrial Polymers Pvt Ltd',
      matchedVendorCode: vendors[1]?.vendorCode || 'V-1002',
      msmeCategory: 'Small',
      confidenceScore: 95,
      extractionEngine: 'Gemini 3.7 Flash AI',
      extractionNotes: [
        'Udyam UDYAM-GJ-03-0045892 confirmed on invoice header.',
        'Section 15 45-day statutory due date limit applies.',
      ],
      status: 'EXTRACTED',
    };

    const sample3: ExtractedInvoiceData = {
      fileId: 'SAMPLE-PDF-3',
      fileName: 'Invoice_Dynamic_Tooling_Micro.pdf',
      fileType: 'pdf',
      fileSize: 312000,
      fileDataUrl: '',
      invoiceNumber: 'DTDE/2026/0204',
      vendorName: 'Dynamic Tooling & Dies Enterprises',
      vendorGstin: '27AABCD1234F1Z1',
      vendorPan: 'AABCD1234F',
      invoiceDate: today,
      basicAmount: 180000,
      gstRate: 18,
      gstAmount: 32400,
      totalAmount: 212400,
      poNumber: 'PO/2026/0725',
      poDate: today,
      materialDescription: 'Progressive Stamping Tool Maintenance & Calibration',
      mrnDate: today,
      acceptanceDate: today,
      agreedCreditDays: 15,
      hasWrittenAgreement: false,
      agreedPaymentTerms: 'No written contract (Statutory 15 days default)',
      udyamNumber: 'UDYAM-MH-01-0098765',
      isMsmeClaimed: true,
      matchedVendorId: vendors[2]?.id || 'VEND-003',
      matchedVendorName: vendors[2]?.vendorName || 'Dynamic Tooling & Dies Enterprises',
      matchedVendorCode: vendors[2]?.vendorCode || 'V-1003',
      msmeCategory: 'Micro',
      confidenceScore: 96,
      extractionEngine: 'Gemini 3.7 Flash AI',
      extractionNotes: [
        'Micro Enterprise without written contract.',
        'Statutory 15-day Section 15 payment deadline calculated.',
      ],
      status: 'EXTRACTED',
    };

    setTimeout(() => {
      setExtractedInvoices((prev) => [...prev, sample1, sample2, sample3]);
      setIsProcessing(false);
    }, 400);
  };

  const handleUpdateItem = (fileId: string, field: keyof ExtractedInvoiceData, value: any) => {
    setExtractedInvoices((prev) =>
      prev.map((item) => {
        if (item.fileId !== fileId) return item;
        const updated = { ...item, [field]: value };

        // Recalculate GST or Total if basicAmount or gstRate changes
        if (field === 'basicAmount' || field === 'gstRate') {
          const basic = field === 'basicAmount' ? Number(value) : item.basicAmount;
          const rate = field === 'gstRate' ? Number(value) : (item.gstRate || 18);
          updated.gstAmount = Math.round(basic * (rate / 100));
          updated.totalAmount = basic + updated.gstAmount;
        }

        // If vendor changes
        if (field === 'matchedVendorId') {
          const v = vendors.find((vend) => vend.id === value);
          if (v) {
            updated.vendorName = v.vendorName;
            updated.matchedVendorName = v.vendorName;
            updated.matchedVendorCode = v.vendorCode;
            updated.msmeCategory = v.msmeCategory;
            updated.agreedCreditDays = v.agreedCreditDays;
            updated.hasWrittenAgreement = v.hasWrittenAgreement;
          }
        }

        return updated;
      })
    );
  };

  const handleRemoveItem = (fileId: string) => {
    setExtractedInvoices((prev) => prev.filter((i) => i.fileId !== fileId));
    if (previewFileId === fileId) {
      setPreviewFileId(null);
    }
  };

  const handleBatchImport = () => {
    if (extractedInvoices.length === 0) return;

    let successCount = 0;
    const errors: string[] = [];

    extractedInvoices.forEach((ext) => {
      let vendorObj =
        vendors.find((v) => v.id === ext.matchedVendorId) ||
        vendors.find((v) => v.vendorName.toLowerCase() === (ext.vendorName || '').toLowerCase().trim()) ||
        (ext.vendorGstin ? vendors.find((v) => v.gstin.toUpperCase() === ext.vendorGstin.toUpperCase().trim()) : null);

      if (!vendorObj) {
        // Auto-register this supplier if not in master
        const newVendorCode = `V-${1000 + vendors.length + 1}`;
        const newVendor: any = {
          vendorName: ext.vendorName || 'Supplier Enterprise',
          vendorCode: newVendorCode,
          pan: ext.vendorPan || (ext.vendorGstin ? ext.vendorGstin.substring(2, 12) : 'AAACG1234F'),
          gstin: ext.vendorGstin || '07AKGPG0799L1ZR',
          udyamNumber: ext.udyamNumber || '',
          msmeCategory: ext.msmeCategory === 'Not Applicable' ? 'Micro' : (ext.msmeCategory || 'Micro'),
          isMSME: true,
          enterpriseType: 'Manufacturer',
          majorActivity: 'Manufacturing',
          agreedCreditDays: ext.agreedCreditDays || 30,
          hasWrittenAgreement: ext.hasWrittenAgreement ?? true,
          contactPerson: ext.vendorName || 'Accounts Department',
          email: 'accounts@' + (ext.vendorName || 'vendor').toLowerCase().replace(/[^a-z0-9]/g, '') + '.com',
          phone: '9810012345',
          state: 'Delhi',
          status: 'Active',
          verificationStatus: 'Verified',
          msmeCertificateUrl: '',
        };
        addVendor(newVendor);
        vendorObj = { ...newVendor, id: `VEND-AUTO-${Date.now()}` };
      }

      const invData = convertExtractedToInvoice(
        ext,
        vendorObj,
        statutoryRules,
        selectedFinancialYear === 'All' ? '2026-27' : selectedFinancialYear
      );

      const res = addInvoice(invData as any);
      if (res.success) {
        successCount++;
      } else {
        errors.push(res.message || 'Error adding invoice');
      }
    });

    if (successCount > 0) {
      alert(`Successfully imported ${successCount} invoice(s) into the Invoice Register with attached documents and statutory due dates!`);
      setExtractedInvoices([]);
      onClose();
    } else if (errors.length > 0) {
      alert(`Import issues:\n${errors.join('\n')}`);
    }
  };

  const selectedPreviewItem = extractedInvoices.find((i) => i.fileId === previewFileId);

  return (
    <div
      id="invoice-doc-upload-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/80 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div
        id="invoice-doc-upload-modal"
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-6xl h-[92vh] flex flex-col overflow-hidden"
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">
                  Upload Invoices (PDF & JPEG / Image)
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 border border-blue-200 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-blue-600" />
                  Gemini 3.7 Flash AI OCR
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Upload supplier tax invoices in PDF, JPEG, JPG, or PNG to extract commercial data, verify MSME terms, and calculate Section 15 statutory caps
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
          {/* Left / Main Workspace */}
          <div className="flex-1 flex flex-col p-5 overflow-y-auto space-y-5">
            {/* Dropzone Container */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center ${
                isDragOver
                  ? 'border-blue-500 bg-blue-50/80 scale-[0.99]'
                  : 'border-slate-300 hover:border-blue-400 bg-slate-50/60 hover:bg-slate-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png,image/jpeg,image/png,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFilesSelected(e.target.files);
                  }
                }}
              />

              <div className="w-14 h-14 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-center mb-3 text-blue-600">
                <Upload className="w-7 h-7" />
              </div>

              <h4 className="text-sm font-bold text-slate-800">
                Drag and drop PDF or JPEG/PNG invoices here, or <span className="text-blue-600 underline">browse files</span>
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                Supports single or bulk uploads (.PDF, .JPEG, .JPG, .PNG up to 50MB each)
              </p>

              <div className="flex items-center gap-3 mt-4 flex-wrap justify-center">
                <span className="px-2.5 py-1 rounded-md bg-white border border-slate-200 text-[11px] font-medium text-slate-600 flex items-center gap-1.5 shadow-2xs">
                  <FileText className="w-3.5 h-3.5 text-red-500" /> PDF Invoices
                </span>
                <span className="px-2.5 py-1 rounded-md bg-white border border-slate-200 text-[11px] font-medium text-slate-600 flex items-center gap-1.5 shadow-2xs">
                  <Image className="w-3.5 h-3.5 text-blue-500" /> JPEG / JPG / PNG Scans
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleLoadSampleInvoices();
                  }}
                  className="px-3 py-1 rounded-md bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-[11px] font-bold flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Load 3 Sample Invoices (Demo)
                </button>
              </div>
            </div>

            {/* Processing Spinner Banner */}
            {isProcessing && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between text-xs text-blue-900 animate-pulse">
                <div className="flex items-center gap-3">
                  <RefreshCw className="w-4 h-4 text-blue-600 animate-spin" />
                  <div>
                    <div className="font-bold">
                      Analyzing & Extracting Statutory Fields via AI...
                    </div>
                    <div className="text-[11px] text-blue-700">
                      Processing file {processingProgress.current} of {processingProgress.total} with Gemini 3.7 Flash
                    </div>
                  </div>
                </div>
                <span className="font-extrabold text-blue-700">
                  {Math.round((processingProgress.current / (processingProgress.total || 1)) * 100)}%
                </span>
              </div>
            )}

            {/* Extracted Invoices Review List */}
            {extractedInvoices.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Extracted Invoices ({extractedInvoices.length})
                    </h4>
                    <p className="text-[11px] text-slate-400">
                      Review, edit, or map supplier details before adding to Invoice Register
                    </p>
                  </div>
                  <button
                    onClick={() => setExtractedInvoices([])}
                    className="text-xs font-semibold text-rose-600 hover:text-rose-700 cursor-pointer"
                  >
                    Clear All
                  </button>
                </div>

                <div className="space-y-3">
                  {extractedInvoices.map((item, idx) => {
                    const isSelectedForPreview = previewFileId === item.fileId;
                    const isPdf = item.fileType === 'pdf';

                    return (
                      <div
                        key={item.fileId}
                        className={`bg-white rounded-xl border p-4 shadow-xs transition-all ${
                          isSelectedForPreview
                            ? 'border-blue-500 ring-2 ring-blue-500/20'
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {/* Header of Item */}
                        <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3 mb-3 flex-wrap">
                          <div className="flex items-center gap-2.5">
                            <div
                              className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                                isPdf ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-blue-50 text-blue-600 border border-blue-200'
                              }`}
                            >
                              {isPdf ? <FileText className="w-4 h-4" /> : <Image className="w-4 h-4" />}
                            </div>
                            <div>
                              <div className="text-xs font-bold text-slate-900 truncate max-w-xs">
                                {item.fileName}
                              </div>
                              <div className="text-[10px] text-slate-400 flex items-center gap-2">
                                <span>{(item.fileSize / 1024).toFixed(0)} KB</span>
                                <span>•</span>
                                <span className="text-emerald-700 font-semibold flex items-center gap-1">
                                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                  {item.extractionEngine} ({item.confidenceScore}% conf)
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() =>
                                setPreviewFileId(isSelectedForPreview ? null : item.fileId)
                              }
                              className={`px-2.5 py-1 text-xs font-semibold rounded-lg border flex items-center gap-1.5 transition-colors cursor-pointer ${
                                isSelectedForPreview
                                  ? 'bg-blue-600 text-white border-blue-600'
                                  : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                              }`}
                            >
                              {isSelectedForPreview ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                              <span>{isSelectedForPreview ? 'Hide Preview' : 'View Preview'}</span>
                            </button>
                            <button
                              onClick={() => handleRemoveItem(item.fileId)}
                              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                              title="Remove item"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {/* Extraction Form Fields */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                          {/* Invoice Number */}
                          <div>
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                              Invoice No *
                            </label>
                            <input
                              type="text"
                              value={item.invoiceNumber}
                              onChange={(e) => handleUpdateItem(item.fileId, 'invoiceNumber', e.target.value)}
                              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-800 focus:outline-hidden focus:bg-white focus:border-blue-500"
                            />
                          </div>

                          {/* Vendor Match */}
                          <div className="sm:col-span-2">
                            <div className="flex items-center justify-between mb-1">
                              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                                Supplier / Vendor Mapping *
                              </label>
                              <span className="text-[10px] text-blue-600 font-semibold">
                                {item.vendorGstin ? `GSTIN: ${item.vendorGstin}` : ''}
                              </span>
                            </div>
                            <select
                              value={item.matchedVendorId || 'AUTO_NEW'}
                              onChange={(e) => {
                                if (e.target.value === 'AUTO_NEW') {
                                  handleUpdateItem(item.fileId, 'matchedVendorId', undefined);
                                } else {
                                  handleUpdateItem(item.fileId, 'matchedVendorId', e.target.value);
                                }
                              }}
                              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-semibold text-slate-800 focus:outline-hidden focus:bg-white focus:border-blue-500"
                            >
                              <option value="AUTO_NEW">
                                🏢 {item.vendorName || 'Extracted Vendor'} (Register / Add as {item.msmeCategory || 'Micro'})
                              </option>
                              <optgroup label="Or Link with Existing Vendor Master:">
                                {vendors.map((v) => (
                                  <option key={v.id} value={v.id}>
                                    {v.vendorName} ({v.msmeCategory} - {v.agreedCreditDays}d terms)
                                  </option>
                                ))}
                              </optgroup>
                            </select>
                          </div>

                          {/* Invoice Date */}
                          <div>
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                              Invoice Date *
                            </label>
                            <input
                              type="date"
                              value={item.invoiceDate}
                              onChange={(e) => handleUpdateItem(item.fileId, 'invoiceDate', e.target.value)}
                              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-semibold text-slate-800 focus:outline-hidden focus:bg-white focus:border-blue-500"
                            />
                          </div>

                          {/* Basic Amount */}
                          <div>
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                              Basic Amount (₹) *
                            </label>
                            <input
                              type="number"
                              value={item.basicAmount}
                              onChange={(e) => handleUpdateItem(item.fileId, 'basicAmount', parseFloat(e.target.value) || 0)}
                              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-800 focus:outline-hidden focus:bg-white focus:border-blue-500"
                            />
                          </div>

                          {/* GST Amount */}
                          <div>
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                              GST Amount (₹)
                            </label>
                            <input
                              type="number"
                              value={item.gstAmount}
                              onChange={(e) => handleUpdateItem(item.fileId, 'gstAmount', parseFloat(e.target.value) || 0)}
                              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg font-semibold text-slate-800 focus:outline-hidden focus:bg-white focus:border-blue-500"
                            />
                          </div>

                          {/* Total Amount */}
                          <div>
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                              Total Invoice (₹) *
                            </label>
                            <input
                              type="number"
                              value={item.totalAmount}
                              onChange={(e) => handleUpdateItem(item.fileId, 'totalAmount', parseFloat(e.target.value) || 0)}
                              className="w-full px-2.5 py-1.5 bg-blue-50/70 border border-blue-200 rounded-lg font-extrabold text-blue-900 focus:outline-hidden focus:bg-white focus:border-blue-500"
                            />
                          </div>

                          {/* PO Number */}
                          <div>
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                              PO / Reference No
                            </label>
                            <input
                              type="text"
                              value={item.poNumber || ''}
                              onChange={(e) => handleUpdateItem(item.fileId, 'poNumber', e.target.value)}
                              placeholder="PO-2026-000"
                              className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-hidden focus:bg-white focus:border-blue-500"
                            />
                          </div>
                        </div>

                        {/* Description & Statutory Notes */}
                        <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 flex-wrap gap-2">
                          <div className="truncate max-w-lg">
                            <span className="font-semibold text-slate-700">Goods/Services:</span>{' '}
                            {item.materialDescription}
                          </div>
                          <div className="text-[10px] text-blue-700 font-bold bg-blue-50 px-2 py-0.5 rounded">
                            Section 15 Cap: {item.agreedCreditDays || 30} Days (Micro/Small)
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Right Side / Document Preview Panel */}
          {selectedPreviewItem && (
            <div className="w-full lg:w-96 bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-700 p-4 flex flex-col shrink-0 overflow-hidden">
              <div className="flex items-center justify-between text-white pb-3 border-b border-slate-700">
                <div className="text-xs font-bold truncate">
                  {selectedPreviewItem.fileName}
                </div>
                <button
                  onClick={() => setPreviewFileId(null)}
                  className="text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-auto mt-3 flex items-center justify-center bg-slate-800/50 rounded-xl p-2">
                {selectedPreviewItem.fileDataUrl ? (
                  selectedPreviewItem.fileType === 'pdf' ? (
                    <iframe
                      src={selectedPreviewItem.fileDataUrl}
                      title="PDF Preview"
                      className="w-full h-full rounded-lg bg-white"
                    />
                  ) : (
                    <img
                      src={selectedPreviewItem.fileDataUrl}
                      alt="Invoice Scan"
                      className="max-h-[60vh] max-w-full object-contain rounded-lg shadow-md"
                    />
                  )
                ) : (
                  <div className="bg-white text-slate-800 p-5 rounded-lg text-xs space-y-4 w-full">
                    <div className="font-bold text-center border-b pb-2 text-slate-900">
                      TAX INVOICE PREVIEW
                    </div>
                    <div className="space-y-1 text-[11px]">
                      <div>
                        <strong>Supplier:</strong> {selectedPreviewItem.vendorName}
                      </div>
                      <div>
                        <strong>GSTIN:</strong> {selectedPreviewItem.vendorGstin}
                      </div>
                      <div>
                        <strong>Invoice No:</strong> {selectedPreviewItem.invoiceNumber}
                      </div>
                      <div>
                        <strong>Date:</strong> {formatDate(selectedPreviewItem.invoiceDate)}
                      </div>
                      <div>
                        <strong>Description:</strong> {selectedPreviewItem.materialDescription}
                      </div>
                    </div>
                    <div className="border-t pt-2 flex justify-between font-bold text-xs">
                      <span>Grand Total:</span>
                      <span className="text-blue-700">{formatINR(selectedPreviewItem.totalAmount)}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="text-xs text-slate-500">
            {extractedInvoices.length > 0 ? (
              <span>
                <strong>{extractedInvoices.length} invoice(s)</strong> ready for batch registration into Compliance Engine.
              </span>
            ) : (
              <span>Select or drop PDF/JPEG files above to start.</span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              disabled={extractedInvoices.length === 0 || isProcessing}
              onClick={handleBatchImport}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-sm transition-all cursor-pointer flex items-center gap-2"
            >
              <span>Import to Invoice Register ({extractedInvoices.length})</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
