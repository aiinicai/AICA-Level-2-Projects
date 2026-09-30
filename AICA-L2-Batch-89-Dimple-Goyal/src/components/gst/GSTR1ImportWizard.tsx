import React, { useState } from 'react';
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  Receipt,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  X,
  FileSpreadsheet,
  Sparkles,
  Download,
  Users
} from 'lucide-react';
import { Customer, Invoice, GSTRecord } from '../../types';
import { parseFile, autoDetectMappings } from '../../utils/excelEngine';
import { parseUniversalFile } from '../../utils/fileImportEngine';
import { formatINR } from '../../utils/formatters';

interface GSTR1ImportWizardProps {
  isOpen: boolean;
  customers: Customer[];
  existingInvoices: Invoice[];
  existingGstRecords: GSTRecord[];
  onClose: () => void;
  onImportComplete: (importedRecords: GSTRecord[]) => void;
}

export const GSTR1ImportWizard: React.FC<GSTR1ImportWizardProps> = ({
  isOpen,
  customers,
  existingInvoices,
  existingGstRecords,
  onClose,
  onImportComplete
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [file, setFile] = useState<File | null>(null);
  const [fileFormat, setFileFormat] = useState<'json' | 'excel' | 'csv'>('json');
  const [headers, setHeaders] = useState<string[]>([]);
  const [rawRows, setRawRows] = useState<any[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [parsedRecords, setParsedRecords] = useState<GSTRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  if (!isOpen) return null;

  const GSTR1_COLUMN_MAPPINGS = [
    { field: 'customerGstin', label: 'Recipient GSTIN (Debtor)', required: true, synonyms: ['gstin of recipient', 'receiver gstin', 'ctin', 'customer gstin', 'buyer gstin', 'gstin'] },
    { field: 'customerName', label: 'Receiver Name (Debtor)', required: false, synonyms: ['receiver name', 'trade name', 'party name', 'customer name', 'cname'] },
    { field: 'invoiceNumber', label: 'Invoice Number', required: true, synonyms: ['invoice number', 'inv no', 'inum', 'bill no', 'doc no'] },
    { field: 'invoiceDate', label: 'Invoice Date', required: true, synonyms: ['invoice date', 'inv date', 'idt', 'date'] },
    { field: 'taxableValue', label: 'Taxable Value (₹)', required: true, synonyms: ['taxable value', 'txval', 'taxable amount', 'base amount'] },
    { field: 'igst', label: 'Integrated Tax / IGST (₹)', required: false, synonyms: ['integrated tax', 'iamt', 'igst amount', 'igst'] },
    { field: 'cgst', label: 'Central Tax / CGST (₹)', required: false, synonyms: ['central tax', 'camt', 'cgst amount', 'cgst'] },
    { field: 'sgst', label: 'State Tax / SGST (₹)', required: false, synonyms: ['state tax', 'samt', 'sgst amount', 'sgst'] },
    { field: 'totalValue', label: 'Invoice Value (₹)', required: true, synonyms: ['invoice value', 'val', 'total value', 'gross amount', 'bill value'] }
  ];

  const handleFileChange = async (selectedFile: File) => {
    setFile(selectedFile);
    setLoading(true);
    const ext = selectedFile.name.split('.').pop()?.toLowerCase();

    try {
      setFileFormat(ext === 'json' ? 'json' : ext === 'csv' ? 'csv' : 'excel');
      const parsed = await parseUniversalFile(selectedFile);
      setHeaders(parsed.headers);
      setRawRows(parsed.rows);

      const detected = autoDetectMappings(parsed.headers, GSTR1_COLUMN_MAPPINGS);
      setMapping(detected);
      setStep(2);
    } catch (err) {
      alert('Failed to parse GSTR-1 file. Please upload a valid GST Portal JSON, Excel (.xlsx/.xls) or CSV file.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadSampleGSTR1 = (format: 'json' | 'excel' | 'csv') => {
    setLoading(true);
    setFileFormat(format);
    const mockCust1 = customers[0] || { name: 'ABC Private Limited', gstin: '27AAACA1234B1Z2' };
    const mockCust2 = customers[1] || { name: 'XYZ Enterprises', gstin: '27AABCX5678C1Z6' };
    const mockCust3 = customers[2] || { name: 'Apex Corp Retail Traders', gstin: '27AACCA9876K1Z9' };

    const sampleRows = [
      {
        customerGstin: mockCust1.gstin,
        customerName: mockCust1.name,
        invoiceNumber: 'INV-2026-001',
        invoiceDate: '2026-04-10',
        taxableValue: 100000,
        igst: 0,
        cgst: 9000,
        sgst: 9000,
        totalValue: 118000
      },
      {
        customerGstin: mockCust1.gstin,
        customerName: mockCust1.name,
        invoiceNumber: 'INV-2026-004',
        invoiceDate: '2026-04-15',
        taxableValue: 50000,
        igst: 0,
        cgst: 4500,
        sgst: 4500,
        totalValue: 59000
      },
      {
        customerGstin: mockCust2.gstin,
        customerName: mockCust2.name,
        invoiceNumber: 'INV-2026-009',
        invoiceDate: '2026-05-18',
        taxableValue: 200000,
        igst: 36000,
        cgst: 0,
        sgst: 0,
        totalValue: 236000
      },
      {
        customerGstin: mockCust3.gstin,
        customerName: mockCust3.name,
        invoiceNumber: 'INV-2026-015',
        invoiceDate: '2026-05-22',
        taxableValue: 80000,
        igst: 14400,
        cgst: 0,
        sgst: 0,
        totalValue: 94400
      },
      {
        customerGstin: mockCust3.gstin,
        customerName: mockCust3.name,
        invoiceNumber: 'INV-2026-022',
        invoiceDate: '2026-06-26',
        taxableValue: 110000,
        igst: 0,
        cgst: 9900,
        sgst: 9900,
        totalValue: 129800
      }
    ];

    setFile(new File(['sample'], `GSTR1_Filing_Export.${format === 'json' ? 'json' : format === 'excel' ? 'xlsx' : 'csv'}`));
    const sampleHeaders = Object.keys(sampleRows[0]);
    setHeaders(sampleHeaders);
    setRawRows(sampleRows);
    const directMap: Record<string, string> = {};
    sampleHeaders.forEach(h => { directMap[h] = h; });
    setMapping(directMap);
    setLoading(false);
    setStep(2);
  };

  const handleValidateAndTransform = () => {
    const transformed: GSTRecord[] = [];

    rawRows.forEach((row, idx) => {
      const mapped: any = {};
      Object.entries(mapping).forEach(([sourceCol, targetField]) => {
        mapped[targetField] = row[sourceCol];
      });

      const customerGstin = String(mapped.customerGstin || row.customerGstin || row.ctin || '').trim().toUpperCase();
      let customerName = String(mapped.customerName || row.customerName || row.cname || '').trim();
      const invoiceNumber = String(mapped.invoiceNumber || row.invoiceNumber || row.inum || `INV-GSTR1-${idx}`).trim().toUpperCase();
      const invoiceDate = String(mapped.invoiceDate || row.invoiceDate || row.idt || '2026-04-15').trim();
      
      const taxableValue = parseFloat(String(mapped.taxableValue ?? row.taxableValue ?? row.txval ?? 0).replace(/[^0-9.-]/g, '')) || 0;
      const igst = parseFloat(String(mapped.igst ?? row.igst ?? row.iamt ?? 0).replace(/[^0-9.-]/g, '')) || 0;
      const cgst = parseFloat(String(mapped.cgst ?? row.cgst ?? row.camt ?? 0).replace(/[^0-9.-]/g, '')) || 0;
      const sgst = parseFloat(String(mapped.sgst ?? row.sgst ?? row.samt ?? 0).replace(/[^0-9.-]/g, '')) || 0;
      const totalValue = parseFloat(String(mapped.totalValue ?? row.totalValue ?? row.val ?? (taxableValue + igst + cgst + sgst)).replace(/[^0-9.-]/g, '')) || (taxableValue + igst + cgst + sgst);

      // Match debtor from customers
      if (!customerName) {
        const foundCust = customers.find(c => c.gstin.toUpperCase() === customerGstin);
        if (foundCust) customerName = foundCust.name;
        else customerName = `Debtor (GSTIN: ${customerGstin})`;
      }

      // Check matching in internal sales register
      const matchedBooksInv = existingInvoices.find(inv =>
        inv.invoiceNumber.toUpperCase() === invoiceNumber ||
        inv.invoiceNumber.toUpperCase().replace(/[-/\s]/g, '') === invoiceNumber.replace(/[-/\s]/g, '')
      );

      let status: GSTRecord['status'] = 'Matched';
      let discrepancyRemarks: string | undefined;

      if (!matchedBooksInv) {
        status = 'GST Data Missing in Books';
        discrepancyRemarks = 'Invoice reported in GSTR-1 portal filing but missing in Sales Register';
      } else {
        const taxDiff = Math.abs((matchedBooksInv.igst + matchedBooksInv.cgst + matchedBooksInv.sgst) - (igst + cgst + sgst));
        const valDiff = Math.abs(matchedBooksInv.totalInvoiceValue - totalValue);

        if (taxDiff > 5 || valDiff > 5) {
          status = 'Tax Mismatch';
          discrepancyRemarks = `Books Value ₹${matchedBooksInv.totalInvoiceValue} vs GSTR-1 ₹${totalValue} (Diff: ₹${Math.abs(matchedBooksInv.totalInvoiceValue - totalValue)})`;
        } else {
          status = 'Matched';
        }
      }

      transformed.push({
        id: `gstr1-imp-${Date.now()}-${idx}`,
        gstin: customerGstin,
        customerGstin,
        customerName,
        tradeName: customerName,
        invoiceNumber,
        invoiceDate,
        taxableValue,
        cgst,
        sgst,
        igst,
        total: totalValue,
        totalValue,
        cgstAmount: cgst,
        sgstAmount: sgst,
        igstAmount: igst,
        gstr1ReportedValue: totalValue,
        source: 'GSTR-1 Portal',
        status,
        discrepancyRemarks,
        discrepancyReason: discrepancyRemarks,
        differenceAmount: matchedBooksInv ? Math.abs(matchedBooksInv.totalInvoiceValue - totalValue) : 0
      });
    });

    setParsedRecords(transformed);
    setStep(3);
  };

  const handleConfirmImport = () => {
    if (parsedRecords.length > 0) {
      onImportComplete(parsedRecords);
      setStep(4);
    }
  };

  // Group by Debtor for preview
  const debtorGroups = React.useMemo(() => {
    const map = new Map<string, { name: string; count: number; total: number }>();
    parsedRecords.forEach(r => {
      const gstin = r.customerGstin || 'UNKNOWN';
      const existing = map.get(gstin) || { name: r.customerName || gstin, count: 0, total: 0 };
      existing.count += 1;
      existing.total += r.totalValue || r.total;
      map.set(gstin, existing);
    });
    return Array.from(map.entries()).map(([gstin, data]) => ({ gstin, ...data }));
  }, [parsedRecords]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Receipt className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Upload GSTR-1 (Debtor-Wise Reconciliation)</h3>
              <p className="text-[11px] text-slate-500">Step {step} of 4 • Table 4 B2B outward supplies, JSON/Excel/CSV parser & debtor matching</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Steps Tracker */}
        <div className="flex border-b border-slate-200 bg-white text-xs px-6 py-3 font-semibold">
          {[
            { s: 1, label: '1. Select GSTR-1 File' },
            { s: 2, label: '2. Review Columns' },
            { s: 3, label: '3. Preview Debtor Groups' },
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

        {/* Step 1: Upload */}
        {step === 1 && (
          <div className="p-6 flex-1 flex flex-col items-center justify-center text-center space-y-4">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-amber-100 text-amber-900 border border-amber-300">
                .JSON (GSTN Portal)
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-blue-100 text-blue-800 border border-blue-300">
                .XLSX / .XLS
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-emerald-100 text-emerald-800 border border-emerald-300">
                .CSV (B2B Table 4)
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
              className={`w-full border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center transition-all ${
                dragOver ? 'border-emerald-600 bg-emerald-50/50' : 'border-slate-300 bg-slate-50/50 hover:bg-slate-50'
              }`}
            >
              <Upload className="w-10 h-10 text-emerald-600 mb-3" />
              <p className="font-bold text-slate-800 text-sm">Drag & drop your GSTR-1 file here</p>
              <p className="text-xs text-slate-500 mt-1">Accepts GST Portal JSON export, standard B2B Excel or CSV</p>

              <label className="mt-4 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold cursor-pointer transition-colors shadow-xs">
                <span>Browse GSTR-1 Files</span>
                <input
                  type="file"
                  accept=".json,.xlsx,.xls,.csv"
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
                Or quickly test with realistic GSTR-1 filings:
              </span>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  onClick={() => loadSampleGSTR1('json')}
                  className="px-3 py-1.5 bg-white hover:bg-amber-50 text-slate-700 hover:text-amber-900 border border-slate-300 hover:border-amber-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-amber-600" />
                  <span>Load Sample GSTN JSON</span>
                </button>
                <button
                  onClick={() => loadSampleGSTR1('excel')}
                  className="px-3 py-1.5 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-900 border border-slate-300 hover:border-blue-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample Excel (.xlsx)
                </button>
                <button
                  onClick={() => loadSampleGSTR1('csv')}
                  className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-900 border border-slate-300 hover:border-emerald-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample CSV (Table 4 B2B)
                </button>
              </div>
            </div>

            <div className="text-left bg-slate-50 p-3 rounded-lg border border-slate-200 w-full text-xs text-slate-600 space-y-1">
              <span className="font-bold text-slate-700 block">Debtor-Wise Reconciliation Features:</span>
              <p>• Automatically groups outward supplies by <strong>Debtor GSTIN & Trade Name</strong></p>
              <p>• Compares Books Outward Turnover vs GSTR-1 Filed Turnover</p>
              <p>• Flags Invoices missing on GST portal (prevents customer 16(2)(aa) input tax credit block)</p>
            </div>
          </div>
        )}

        {/* Step 2: Mapping */}
        {step === 2 && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs">
            <div className="flex items-center justify-between bg-emerald-50 p-3 rounded-lg border border-emerald-200">
              <div>
                <p className="font-bold text-emerald-950">Review GSTR-1 Columns</p>
                <p className="text-[11px] text-emerald-800">
                  File: {file?.name} ({rawRows.length} supplies detected)
                </p>
              </div>
              <button
                onClick={() => setMapping(autoDetectMappings(headers, GSTR1_COLUMN_MAPPINGS))}
                className="flex items-center gap-1 text-[11px] font-bold text-emerald-800 hover:underline"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Re-detect</span>
              </button>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                  <tr>
                    <th className="p-3">Required GSTR-1 Field</th>
                    <th className="p-3">File Column Detected</th>
                    <th className="p-3">Sample Value (Row 1)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {GSTR1_COLUMN_MAPPINGS.map((def) => {
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
                              if (newHeader) updated[newHeader] = def.field;
                              setMapping(updated);
                            }}
                            className="w-full p-1.5 rounded border border-slate-300 bg-white font-medium focus:ring-1 focus:ring-emerald-500"
                          >
                            <option value="">-- Ignore / Not Mapped --</option>
                            {headers.map(h => (
                              <option key={h} value={h}>{h}</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-3 font-mono text-slate-500 truncate max-w-xs">
                          {String(sampleVal)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-slate-200">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-700 font-semibold flex items-center gap-1.5"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </button>
              <button
                onClick={handleValidateAndTransform}
                className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold flex items-center gap-1.5 shadow-xs"
              >
                <span>Continue to Debtor Summary</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Debtor Summary Preview */}
        {step === 3 && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs">
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Total GSTR-1 Invoices</span>
                <p className="text-base font-bold text-slate-900 mt-0.5">{parsedRecords.length}</p>
              </div>
              <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-emerald-800 block">Unique Debtors (Buyers)</span>
                <p className="text-base font-bold text-emerald-950 mt-0.5">{debtorGroups.length} Debtors</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Total Turnover Filed</span>
                <p className="text-base font-bold text-slate-900 mt-0.5">
                  {formatINR(parsedRecords.reduce((sum, r) => sum + (r.totalValue || r.total), 0))}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <span className="font-bold text-slate-700 block">Debtor-Wise Ingestion Preview:</span>
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                    <tr>
                      <th className="p-3">Debtor Name & GSTIN</th>
                      <th className="p-3 text-center">Invoice Count</th>
                      <th className="p-3 text-right">Filed Turnover (₹)</th>
                      <th className="p-3 text-right">Reconciliation Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {debtorGroups.map((d, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="p-3">
                          <p className="font-semibold text-slate-900">{d.name}</p>
                          <span className="font-mono text-[10px] text-slate-400">{d.gstin}</span>
                        </td>
                        <td className="p-3 text-center font-bold text-slate-700">{d.count} bills</td>
                        <td className="p-3 text-right font-mono font-bold text-slate-900">{formatINR(d.total)}</td>
                        <td className="p-3 text-right">
                          <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold text-[10px]">
                            Ready for 3-Way Audit
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-slate-200">
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-700 font-semibold flex items-center gap-1.5"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </button>
              <button
                onClick={handleConfirmImport}
                className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold flex items-center gap-1.5 shadow-xs"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Import {parsedRecords.length} GSTR-1 Records</span>
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Summary */}
        {step === 4 && (
          <div className="p-8 flex-1 flex flex-col items-center justify-center text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shadow-xs">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">GSTR-1 Records Successfully Imported!</h3>
            <p className="text-xs text-slate-500 max-w-md">
              {parsedRecords.length} GSTR-1 outward records across {debtorGroups.length} debtors have been imported. Debtor-wise reconciliation matrix has been updated.
            </p>
            <div className="pt-2">
              <button
                onClick={onClose}
                className="px-6 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold text-xs shadow-xs"
              >
                View Debtor-Wise Reconciliation
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
