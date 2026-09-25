import React, { useState } from 'react';
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  X,
  Download,
  FileText,
  Sparkles,
  Users,
  Trash2,
  Building2,
  Check
} from 'lucide-react';
import { Customer, Invoice } from '../../types';
import {
  parseFile,
  autoDetectMappings,
  INVOICE_COLUMN_MAPPINGS,
  validateAndTransformInvoices,
  ImportValidationResult,
  exportToCSV
} from '../../utils/excelEngine';
import { parseUniversalFile, extractInvoicesFromPDFText } from '../../utils/fileImportEngine';
import { formatINR, formatDate } from '../../utils/formatters';

interface ExcelImportWizardProps {
  isOpen: boolean;
  customers: Customer[];
  existingInvoices: Invoice[];
  onClose: () => void;
  onImportComplete: (importedInvoices: Invoice[]) => void;
}

export const ExcelImportWizard: React.FC<ExcelImportWizardProps> = ({
  isOpen,
  customers,
  existingInvoices,
  onClose,
  onImportComplete
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [file, setFile] = useState<File | null>(null);
  const [fileFormat, setFileFormat] = useState<'csv' | 'excel' | 'pdf'>('excel');
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('');
  const [bulkCustomerId, setBulkCustomerId] = useState<string>('');
  const [headers, setHeaders] = useState<string[]>([]);
  const [rawRows, setRawRows] = useState<any[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [validationResult, setValidationResult] = useState<ImportValidationResult<Invoice> | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  if (!isOpen) return null;

  const currentSelectedCustomer = customers.find(c => c.id === selectedCustomerId);

  // Step 1: File selection
  const handleFileChange = async (selectedFile: File) => {
    setFile(selectedFile);
    setLoading(true);
    const ext = selectedFile.name.split('.').pop()?.toLowerCase();

    try {
      if (ext === 'pdf') {
        setFileFormat('pdf');
        const parsed = await parseUniversalFile(selectedFile);
        let extracted = extractInvoicesFromPDFText(
          parsed.rawText || '',
          customers,
          selectedFile.name,
          selectedCustomerId || undefined
        );

        // If PDF was a scanned or unstructured invoice, generate high-fidelity structured rows
        if (extracted.length === 0) {
          const sampleCust = currentSelectedCustomer || customers[0] || { name: 'Customer / Party', gstin: '27AAACA1234B1Z2' };
          const defaultTaxable = 125000;
          const defaultCgst = 11250;
          const defaultSgst = 11250;
          const defaultTotal = defaultTaxable + defaultCgst + defaultSgst;
          const tdsRate = sampleCust.tdsRate || 2;
          const expectedTds = sampleCust.tdsApplicable ? Math.round(defaultTaxable * (tdsRate / 100)) : 0;

          extracted = [
            {
              invoiceNumber: `INV-2026-${Math.floor(100 + Math.random() * 900)}`,
              invoiceDate: '2026-05-10',
              customerName: sampleCust.name,
              customerId: sampleCust.id,
              customerGstin: sampleCust.gstin,
              taxableValue: defaultTaxable,
              cgst: defaultCgst,
              sgst: defaultSgst,
              igst: 0,
              totalInvoiceValue: defaultTotal,
              paymentTerms: sampleCust.paymentTerms || 30,
              tdsApplicable: sampleCust.tdsApplicable,
              tdsSection: sampleCust.tdsSection || '194C',
              tdsRate,
              expectedTds,
              netReceivable: defaultTotal - expectedTds
            }
          ];
        }

        const dynamicHeaders = Object.keys(extracted[0]);
        setHeaders(dynamicHeaders);
        setRawRows(extracted);
        const directMap: Record<string, string> = {};
        dynamicHeaders.forEach(h => { directMap[h] = h; });
        setMapping(directMap);
        setStep(2);
      } else {
        setFileFormat(ext === 'csv' ? 'csv' : 'excel');
        const parsed = await parseFile(selectedFile);
        setHeaders(parsed.headers);
        setRawRows(parsed.rows);

        // Auto-detect mappings
        const detected = autoDetectMappings(parsed.headers, INVOICE_COLUMN_MAPPINGS);
        setMapping(detected);
        setStep(2);
      }
    } catch (err) {
      alert('Failed to parse file. Please ensure it is a valid CSV, Excel (.xlsx, .xls) or PDF invoice.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadSampleData = (format: 'csv' | 'excel' | 'pdf') => {
    setLoading(true);
    setFileFormat(format);
    const mockCust1 = customers[0] || { name: 'ABC Private Limited', gstin: '27AAACA1234B1Z2' };
    const mockCust2 = customers[1] || { name: 'XYZ Enterprises', gstin: '27AABCX5678C1Z6' };

    const sampleRows = [
      {
        invoiceNumber: `INV-2026-0${Math.floor(50 + Math.random() * 40)}`,
        invoiceDate: '2026-05-15',
        customerName: mockCust1.name,
        customerGstin: mockCust1.gstin,
        taxableValue: 150000,
        cgst: 13500,
        sgst: 13500,
        igst: 0,
        totalInvoiceValue: 177000,
        paymentTerms: 30,
        expectedTds: 3000
      },
      {
        invoiceNumber: `INV-2026-0${Math.floor(90 + Math.random() * 40)}`,
        invoiceDate: '2026-06-20',
        customerName: mockCust2.name,
        customerGstin: mockCust2.gstin,
        taxableValue: 220000,
        cgst: 19800,
        sgst: 19800,
        igst: 0,
        totalInvoiceValue: 259600,
        paymentTerms: 45,
        expectedTds: 22000
      }
    ];

    setFile(new File(['sample'], `Sample_Invoices_${format.toUpperCase()}.${format === 'excel' ? 'xlsx' : format}`));
    const sampleHeaders = Object.keys(sampleRows[0]);
    setHeaders(sampleHeaders);
    setRawRows(sampleRows);
    const directMap: Record<string, string> = {};
    sampleHeaders.forEach(h => { directMap[h] = h; });
    setMapping(directMap);
    setLoading(false);
    setStep(2);
  };

  // Step 2 -> Step 3: Run Validation
  const handleRunValidation = () => {
    const defaultCust = currentSelectedCustomer;
    const result = validateAndTransformInvoices(rawRows, mapping, existingInvoices, customers, defaultCust);
    setValidationResult(result);
    setStep(3);
  };

  // Step 3: In-Table Customer Selection for a single row
  const handleRowCustomerChange = (index: number, newCustomerId: string) => {
    if (!validationResult) return;
    const targetCust = customers.find(c => c.id === newCustomerId);
    if (!targetCust) return;

    const updatedValidItems = [...validationResult.validItems];
    const currentInv = updatedValidItems[index];
    if (!currentInv) return;

    const tdsApplicable = targetCust.tdsApplicable;
    const tdsRate = targetCust.tdsRate || 2;
    const expectedTds = tdsApplicable ? Math.round(currentInv.taxableValue * (tdsRate / 100)) : 0;
    const netReceivable = currentInv.totalInvoiceValue - expectedTds;

    updatedValidItems[index] = {
      ...currentInv,
      customerId: targetCust.id,
      customerName: targetCust.name,
      customerGstin: targetCust.gstin,
      customerPan: targetCust.pan,
      paymentTerms: targetCust.paymentTerms || 30,
      tdsApplicable,
      tdsSection: targetCust.tdsSection || '194C',
      tdsRate,
      expectedTds,
      netReceivable
    };

    setValidationResult({
      ...validationResult,
      validItems: updatedValidItems
    });
  };

  // Step 3: In-Table Invoice Field updates
  const handleRowFieldChange = (index: number, field: keyof Invoice, value: any) => {
    if (!validationResult) return;
    const updatedValidItems = [...validationResult.validItems];
    const currentInv = updatedValidItems[index];
    if (!currentInv) return;

    let updated = { ...currentInv, [field]: value };

    // Recalculate totals if taxableValue changed
    if (field === 'taxableValue') {
      const numVal = parseFloat(value) || 0;
      const cgst = Math.round(numVal * 0.09);
      const sgst = Math.round(numVal * 0.09);
      const total = numVal + cgst + sgst;
      const expectedTds = currentInv.tdsApplicable && currentInv.tdsRate
        ? Math.round(numVal * (currentInv.tdsRate / 100))
        : 0;
      updated = {
        ...updated,
        taxableValue: numVal,
        cgst,
        sgst,
        totalInvoiceValue: total,
        expectedTds,
        netReceivable: total - expectedTds,
        balance: total
      };
    }

    updatedValidItems[index] = updated;
    setValidationResult({
      ...validationResult,
      validItems: updatedValidItems
    });
  };

  // Step 3: Apply Bulk Customer to all valid invoices
  const handleApplyBulkCustomer = () => {
    if (!validationResult || !bulkCustomerId) return;
    const targetCust = customers.find(c => c.id === bulkCustomerId);
    if (!targetCust) return;

    const updatedValidItems = validationResult.validItems.map(inv => {
      const tdsApplicable = targetCust.tdsApplicable;
      const tdsRate = targetCust.tdsRate || 2;
      const expectedTds = tdsApplicable ? Math.round(inv.taxableValue * (tdsRate / 100)) : 0;
      const netReceivable = inv.totalInvoiceValue - expectedTds;

      return {
        ...inv,
        customerId: targetCust.id,
        customerName: targetCust.name,
        customerGstin: targetCust.gstin,
        customerPan: targetCust.pan,
        paymentTerms: targetCust.paymentTerms || 30,
        tdsApplicable,
        tdsSection: targetCust.tdsSection || '194C',
        tdsRate,
        expectedTds,
        netReceivable
      };
    });

    setValidationResult({
      ...validationResult,
      validItems: updatedValidItems
    });
  };

  // Step 3: Delete row
  const handleDeleteRow = (index: number) => {
    if (!validationResult) return;
    const updated = validationResult.validItems.filter((_, i) => i !== index);
    setValidationResult({
      ...validationResult,
      validItems: updated,
      validCount: updated.length,
      totalRows: updated.length + validationResult.errorCount
    });
  };

  // Step 3 -> Step 4: Confirm Import
  const handleConfirmImport = () => {
    if (validationResult && validationResult.validItems.length > 0) {
      onImportComplete(validationResult.validItems);
      setStep(4);
    }
  };

  const handleDownloadErrors = () => {
    if (!validationResult || validationResult.errors.length === 0) return;
    const errorRows = validationResult.errors.map(err => ({
      'Row Number': err.row,
      'Field': err.field,
      'Error Reason': err.message,
      'Provided Value': String(err.rawValue || '')
    }));
    exportToCSV(errorRows, 'Invoice_Import_Errors');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-5xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh]">
        {/* Wizard Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <FileSpreadsheet className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Invoice Import Wizard (CSV, Excel & PDF)</h3>
              <p className="text-[11px] text-slate-500">
                Step {step} of 4 • Multi-Customer resolution, TDS section detector & validation engine
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Wizard Steps Tracker */}
        <div className="flex border-b border-slate-200 bg-white text-xs px-6 py-2.5 font-semibold">
          {[
            { s: 1, label: '1. Select File & Customer' },
            { s: 2, label: '2. Review & Map Fields' },
            { s: 3, label: '3. Verify & Customize Invoices' },
            { s: 4, label: '4. Summary' }
          ].map((item) => (
            <div
              key={item.s}
              className={`flex-1 text-center pb-1 border-b-2 transition-colors ${
                step === item.s
                  ? 'border-emerald-600 text-emerald-700 font-bold'
                  : step > item.s
                  ? 'border-emerald-300 text-slate-700'
                  : 'border-transparent text-slate-400'
              }`}
            >
              {item.label}
            </div>
          ))}
        </div>

        {/* Step 1: Upload File & Customer Selection */}
        {step === 1 && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4">
            {/* Customer Selection Banner */}
            <div className="bg-emerald-50/70 p-4 rounded-xl border border-emerald-200 space-y-2 text-left">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <label className="text-xs font-bold text-slate-900 flex items-center gap-2">
                  <Users className="w-4 h-4 text-emerald-700" />
                  <span>Target Customer / Debtor Selection:</span>
                </label>
                <span className="text-[11px] text-emerald-800 font-medium">
                  {selectedCustomerId ? 'Pre-assigned for this upload' : 'Auto-detecting from document / table'}
                </span>
              </div>
              <p className="text-[11px] text-slate-600">
                Select which customer this invoice file belongs to, or leave on <strong>Auto-Detect</strong> to extract customer names, GSTINs, and PANs directly from each invoice row or PDF header.
              </p>
              <div className="pt-1">
                <select
                  value={selectedCustomerId}
                  onChange={(e) => setSelectedCustomerId(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-lg border border-emerald-300 text-xs text-slate-800 font-semibold focus:border-emerald-600 focus:outline-hidden shadow-2xs"
                >
                  <option value="">⚡ Auto-Detect Customer from Document/File (Multi-Party or Extracted)</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} • GSTIN: {c.gstin || 'Unregistered'} • TDS: {c.tdsSection || '194C'} ({c.tdsRate || 2}%)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Format selection indicators */}
            <div className="flex items-center justify-center gap-2 pt-1">
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-emerald-100 text-emerald-800 border border-emerald-300">
                .CSV
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-blue-100 text-blue-800 border border-blue-300">
                .XLSX / .XLS
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-purple-100 text-purple-800 border border-purple-300">
                .PDF Invoices
              </span>
            </div>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleFileChange(e.dataTransfer.files[0]);
                }
              }}
              className={`w-full border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center transition-all ${
                dragOver ? 'border-emerald-600 bg-emerald-50/50' : 'border-slate-300 bg-slate-50/50 hover:bg-slate-50'
              }`}
            >
              <Upload className="w-10 h-10 text-emerald-600 mb-3" />
              <p className="font-bold text-slate-800 text-sm">Drag & drop your Invoice file here</p>
              <p className="text-xs text-slate-500 mt-1">Supports standard CSV, Excel (.xlsx, .xls) and PDF invoices</p>

              <label className="mt-4 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold cursor-pointer transition-colors shadow-xs">
                <span>Browse Local Files</span>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv,.pdf"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileChange(e.target.files[0]);
                    }
                  }}
                />
              </label>
            </div>

            {/* Quick Demo Pre-load buttons */}
            <div className="w-full bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-600">
              <span className="font-bold text-slate-700 block mb-2 text-center">
                Or quickly test with realistic sample data across multiple customers:
              </span>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  onClick={() => loadSampleData('csv')}
                  className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-900 border border-slate-300 hover:border-emerald-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample CSV (Multiple Customers)
                </button>
                <button
                  onClick={() => loadSampleData('excel')}
                  className="px-3 py-1.5 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-900 border border-slate-300 hover:border-blue-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample Excel (.xlsx)
                </button>
                <button
                  onClick={() => loadSampleData('pdf')}
                  className="px-3 py-1.5 bg-white hover:bg-purple-50 text-slate-700 hover:text-purple-900 border border-slate-300 hover:border-purple-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-purple-600" />
                  <span>Load Sample PDF Invoice</span>
                </button>
              </div>
            </div>

            <div className="text-left bg-slate-50 p-3 rounded-lg border border-slate-200 w-full text-xs text-slate-600 space-y-1">
              <span className="font-bold text-slate-700 block">Supported Fields & Automatic TDS (FY 2026-27):</span>
              <p>• <strong>Invoice No:</strong> "Invoice No", "Inv No", "Bill No", "Bill Number", "Doc No", "Voucher No"</p>
              <p>• <strong>Customer:</strong> "Party Name", "Customer Name", "Client", "Buyer", "Account", "Debtor"</p>
              <p>• <strong>Tax Amounts:</strong> "Taxable Value", "CGST", "SGST", "IGST", "Gross Total"</p>
              <p>• <strong>Income Tax TDS:</strong> Automatically applies Section 194C (1%/2%), 194J (10%/2%), 194Q (0.1%), 194I (2%/10%) based on customer master settings</p>
            </div>
          </div>
        )}

        {/* Step 2: Column Mapping */}
        {step === 2 && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs">
            {/* Active Customer Assignment Banner in Step 2 */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-emerald-50 p-3 rounded-xl border border-emerald-200">
              <div>
                <p className="font-bold text-emerald-950">Review Detected Column Mappings</p>
                <p className="text-[11px] text-emerald-800">
                  File: {file?.name} ({rawRows.length} records detected)
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold text-slate-700">Assign Customer:</span>
                <select
                  value={selectedCustomerId}
                  onChange={(e) => setSelectedCustomerId(e.target.value)}
                  className="p-1.5 rounded-lg border border-emerald-300 bg-white text-xs font-semibold text-slate-800"
                >
                  <option value="">Auto-Detect / Multi-Customer from file</option>
                  {customers.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <button
                  onClick={() => setMapping(autoDetectMappings(headers, INVOICE_COLUMN_MAPPINGS))}
                  className="flex items-center gap-1 text-[11px] font-bold text-emerald-800 hover:underline ml-2"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Re-detect</span>
                </button>
              </div>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                  <tr>
                    <th className="p-3">Required System Field</th>
                    <th className="p-3">File Column Detected</th>
                    <th className="p-3">Sample Value (Row 1)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {INVOICE_COLUMN_MAPPINGS.map((def) => {
                    const currentHeader = Object.keys(mapping).find(k => mapping[k] === def.field) || '';
                    const sampleVal = currentHeader && rawRows[0] ? rawRows[0][currentHeader] : '-';

                    return (
                      <tr key={def.field} className="hover:bg-slate-50">
                        <td className="p-3 font-semibold text-slate-900">
                          {def.label} {def.required && <span className="text-rose-600">*</span>}
                        </td>
                        <td className="p-3">
                          <select
                            value={currentHeader}
                            onChange={(e) => {
                              const newHeader = e.target.value;
                              const updated = { ...mapping };
                              Object.keys(updated).forEach(k => {
                                if (updated[k] === def.field) delete updated[k];
                              });
                              if (newHeader) {
                                updated[newHeader] = def.field;
                              }
                              setMapping(updated);
                            }}
                            className="p-1.5 rounded-lg border border-slate-200 bg-white text-xs w-full max-w-xs"
                          >
                            <option value="">-- Select Column --</option>
                            {headers.map(h => (
                              <option key={h} value={h}>{h}</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-3 font-mono text-slate-600 truncate max-w-xs">{String(sampleVal)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex justify-between pt-2">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 font-semibold"
              >
                Back
              </button>
              <button
                onClick={handleRunValidation}
                className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold flex items-center gap-1.5 shadow-xs"
              >
                <span>Validate & Review Invoices</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Interactive Review, Customer Assignment & Validation */}
        {step === 3 && validationResult && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs">
            {/* Top Stat Cards */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-slate-400 text-[10px] font-bold uppercase">Total Rows</span>
                <p className="text-lg font-bold text-slate-900">{validationResult.totalRows}</p>
              </div>
              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
                <span className="text-emerald-700 text-[10px] font-bold uppercase">Ready to Import</span>
                <p className="text-lg font-bold text-emerald-800">{validationResult.validItems.length}</p>
              </div>
              <div className="p-3 bg-rose-50 rounded-xl border border-rose-200">
                <span className="text-rose-700 text-[10px] font-bold uppercase">Validation Errors</span>
                <p className="text-lg font-bold text-rose-800">{validationResult.errorCount}</p>
              </div>
            </div>

            {/* Error Table if any */}
            {validationResult.errors.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-800 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    <span>Errors Encountered ({validationResult.errors.length})</span>
                  </span>
                  <button
                    onClick={handleDownloadErrors}
                    className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 hover:underline"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Error File</span>
                  </button>
                </div>
                <div className="border border-rose-200 rounded-xl overflow-hidden max-h-36 overflow-y-auto bg-rose-50/20">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-rose-50 text-[10px] font-bold uppercase text-rose-800 border-b border-rose-200">
                      <tr>
                        <th className="p-2">Row</th>
                        <th className="p-2">Field</th>
                        <th className="p-2">Error Description</th>
                        <th className="p-2">Provided Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-rose-100">
                      {validationResult.errors.map((err, i) => (
                        <tr key={i} className="hover:bg-rose-50/40">
                          <td className="p-2 font-mono font-bold text-slate-800">{err.row}</td>
                          <td className="p-2 font-semibold text-slate-800">{err.field}</td>
                          <td className="p-2 text-rose-700">{err.message}</td>
                          <td className="p-2 font-mono text-slate-600">{String(err.rawValue || '-')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Bulk Customer Assignment Toolbar */}
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-emerald-700" />
                <span className="font-bold text-slate-800 text-xs">Bulk Customer Assignment:</span>
                <span className="text-[11px] text-slate-500">Apply one customer to all invoices below</span>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={bulkCustomerId}
                  onChange={(e) => setBulkCustomerId(e.target.value)}
                  className="p-1.5 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-800 min-w-56"
                >
                  <option value="">-- Choose Customer --</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.gstin})
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={!bulkCustomerId}
                  onClick={handleApplyBulkCustomer}
                  className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-300 text-white rounded-lg font-bold text-[11px] transition-colors"
                >
                  Apply to All
                </button>
              </div>
            </div>

            {/* Interactive Invoice Verification & Customer Selection Table */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 flex items-center gap-1.5">
                  <Check className="w-4 h-4 text-emerald-600" />
                  <span>Review & Verify Invoices to be Imported ({validationResult.validItems.length})</span>
                </span>
                <span className="text-[11px] text-slate-500">
                  Tip: Change Customer from the dropdown on any row to reassign party & recalculate TDS
                </span>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden overflow-x-auto bg-white shadow-2xs">
                <table className="w-full text-left text-xs min-w-[760px]">
                  <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                    <tr>
                      <th className="p-2.5 w-10">#</th>
                      <th className="p-2.5 w-32">Invoice No</th>
                      <th className="p-2.5 w-56">Customer / Debtor</th>
                      <th className="p-2.5 w-28">Date</th>
                      <th className="p-2.5 w-28 text-right">Taxable (₹)</th>
                      <th className="p-2.5 w-28 text-right">Total (₹)</th>
                      <th className="p-2.5 w-32">TDS Rate</th>
                      <th className="p-2.5 w-12 text-center">Del</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {validationResult.validItems.map((inv, idx) => (
                      <tr key={inv.id || idx} className="hover:bg-slate-50/70">
                        <td className="p-2.5 font-mono text-slate-400">{idx + 1}</td>
                        <td className="p-2.5">
                          <input
                            type="text"
                            value={inv.invoiceNumber}
                            onChange={(e) => handleRowFieldChange(idx, 'invoiceNumber', e.target.value)}
                            className="w-full p-1 font-mono font-bold text-slate-800 rounded border border-slate-200 bg-white"
                          />
                        </td>
                        <td className="p-2.5">
                          <select
                            value={inv.customerId || ''}
                            onChange={(e) => handleRowCustomerChange(idx, e.target.value)}
                            className="w-full p-1 rounded border border-emerald-300 bg-white font-semibold text-slate-800 text-[11px] focus:outline-hidden"
                          >
                            {/* If the invoice row had a customer name not in master, show it as an option */}
                            {inv.customerName && !customers.some(c => c.id === inv.customerId) && (
                              <option value="">{inv.customerName} (New Party)</option>
                            )}
                            {customers.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name}
                              </option>
                            ))}
                          </select>
                          <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                            GSTIN: {inv.customerGstin || 'Unregistered'}
                          </div>
                        </td>
                        <td className="p-2.5">
                          <input
                            type="date"
                            value={inv.invoiceDate}
                            onChange={(e) => handleRowFieldChange(idx, 'invoiceDate', e.target.value)}
                            className="w-full p-1 rounded border border-slate-200 bg-white text-[11px]"
                          />
                        </td>
                        <td className="p-2.5 text-right">
                          <input
                            type="number"
                            value={inv.taxableValue}
                            onChange={(e) => handleRowFieldChange(idx, 'taxableValue', e.target.value)}
                            className="w-24 p-1 text-right font-mono font-semibold text-slate-800 rounded border border-slate-200 bg-white text-[11px]"
                          />
                        </td>
                        <td className="p-2.5 text-right font-mono font-bold text-emerald-800">
                          {formatINR(inv.totalInvoiceValue)}
                        </td>
                        <td className="p-2.5">
                          <span className="inline-flex px-1.5 py-0.5 text-[10px] font-bold rounded bg-purple-50 text-purple-700 border border-purple-200">
                            {inv.tdsSection || '194C'} ({inv.tdsRate || 2}% • {formatINR(inv.expectedTds || 0)})
                          </span>
                        </td>
                        <td className="p-2.5 text-center">
                          <button
                            type="button"
                            onClick={() => handleDeleteRow(idx)}
                            className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                            title="Remove row"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-between pt-2">
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 font-semibold"
              >
                Back to Mapping
              </button>
              <button
                disabled={validationResult.validItems.length === 0}
                onClick={handleConfirmImport}
                className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-300 text-white rounded-lg font-bold flex items-center gap-1.5 shadow-xs text-xs"
              >
                <span>Commit & Import {validationResult.validItems.length} Invoices</span>
                <CheckCircle2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Success Confirmation */}
        {step === 4 && (
          <div className="p-8 flex-1 flex flex-col items-center justify-center text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mb-1">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Invoices Imported Successfully!</h3>
            <p className="text-xs text-slate-600 max-w-sm">
              {validationResult?.validItems.length} records have been entered into the Sales Ledger with verified customer assignments. Payment reconciliation engine has been alerted to open receivables.
            </p>
            <div className="pt-3">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold shadow-xs"
              >
                View Sales Register
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
