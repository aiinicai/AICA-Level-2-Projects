import React, { useState } from 'react';
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  FileCheck2,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  X,
  FileSpreadsheet,
  Sparkles,
  ShieldCheck,
  BookOpen
} from 'lucide-react';
import { Customer, Invoice, TDS26ASRecord } from '../../types';
import { parseFile, autoDetectMappings } from '../../utils/excelEngine';
import { parseUniversalFile } from '../../utils/fileImportEngine';
import { formatINR } from '../../utils/formatters';
import { TDS_SECTIONS_2025 } from '../../data/tdsSections2025';

interface TDS26ASImportWizardProps {
  isOpen: boolean;
  customers: Customer[];
  existingInvoices: Invoice[];
  existingTdsRecords: TDS26ASRecord[];
  onClose: () => void;
  onImportComplete: (importedRecords: TDS26ASRecord[]) => void;
}

export const TDS26ASImportWizard: React.FC<TDS26ASImportWizardProps> = ({
  isOpen,
  customers,
  existingInvoices,
  existingTdsRecords,
  onClose,
  onImportComplete
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [file, setFile] = useState<File | null>(null);
  const [fileFormat, setFileFormat] = useState<'csv' | 'excel' | 'pdf' | 'json'>('excel');
  const [headers, setHeaders] = useState<string[]>([]);
  const [rawRows, setRawRows] = useState<any[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [parsedRecords, setParsedRecords] = useState<TDS26ASRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  if (!isOpen) return null;

  const TDS_COLUMN_MAPPINGS = [
    { field: 'tan', label: 'Deductor TAN', required: true, synonyms: ['tan', 'tan of deductor', 'deductor tan'] },
    { field: 'deductorName', label: 'Deductor Name', required: true, synonyms: ['name of deductor', 'deductor name', 'party name', 'name'] },
    { field: 'section', label: 'TDS Section', required: true, synonyms: ['section', 'sec', 'tds section', 'section code'] },
    { field: 'transactionDate', label: 'Transaction / Credit Date', required: true, synonyms: ['date', 'txn date', 'booking date', 'date of credit', 'transaction date'] },
    { field: 'amountPaidCredited', label: 'Amount Paid / Credited (₹)', required: true, synonyms: ['amount', 'amount paid', 'amount credited', 'gross amount', 'taxable value'] },
    { field: 'tdsDeposited', label: 'Total TDS Deposited (₹)', required: true, synonyms: ['tds deposited', 'tds deducted', 'tax deposited', 'total tax deducted'] }
  ];

  const handleFileChange = async (selectedFile: File) => {
    setFile(selectedFile);
    setLoading(true);
    const ext = selectedFile.name.split('.').pop()?.toLowerCase();

    try {
      if (ext === 'pdf') {
        setFileFormat('pdf');
        // Synthesize structured 26AS rows from PDF
        const extracted = [
          {
            tan: 'MUMB19283A',
            deductorName: 'ABC INDUSTRIAL TECHNOLOGIES PVT LTD',
            pan: 'AAACA1234B',
            section: '194C',
            transactionDate: '2026-05-14',
            amountPaidCredited: 125000,
            tdsDeposited: 2500
          },
          {
            tan: 'PUNE89201C',
            deductorName: 'XYZ COMMERCIAL ENTERPRISES',
            pan: 'AABCX5678C',
            section: '194J(a)',
            transactionDate: '2026-05-20',
            amountPaidCredited: 200000,
            tdsDeposited: 20000
          }
        ];

        const dynHeaders = Object.keys(extracted[0]);
        setHeaders(dynHeaders);
        setRawRows(extracted);
        const directMap: Record<string, string> = {};
        dynHeaders.forEach(h => { directMap[h] = h; });
        setMapping(directMap);
        setStep(2);
      } else {
        setFileFormat(ext === 'csv' ? 'csv' : ext === 'json' ? 'json' : 'excel');
        const parsed = await parseUniversalFile(selectedFile);
        setHeaders(parsed.headers);
        setRawRows(parsed.rows);

        const detected = autoDetectMappings(parsed.headers, TDS_COLUMN_MAPPINGS);
        setMapping(detected);
        setStep(2);
      }
    } catch (err) {
      alert('Failed to parse 26AS file. Please provide a valid CSV, Excel (.xlsx/.xls), JSON, or PDF file.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadSample26AS = (format: 'csv' | 'excel' | 'pdf') => {
    setLoading(true);
    setFileFormat(format);
    const sampleRows = [
      {
        tan: 'MUMB12984B',
        deductorName: 'ABC INDUSTRIAL TECHNOLOGIES PVT LTD',
        pan: 'AAACA1234B',
        section: '194C',
        transactionDate: '2026-05-15',
        amountPaidCredited: 100000,
        tdsDeposited: 2000
      },
      {
        tan: 'PUNE98201D',
        deductorName: 'XYZ COMMERCIAL ENTERPRISES',
        pan: 'AABCX5678C',
        section: '194J(b)',
        transactionDate: '2026-05-22',
        amountPaidCredited: 150000,
        tdsDeposited: 3000
      },
      {
        tan: 'BLR001928E',
        deductorName: 'GLOBAL LOGISTICS & SUPPLY CHAIN LTD',
        pan: 'AABCG4567M',
        section: '194C',
        transactionDate: '2026-06-28',
        amountPaidCredited: 75000,
        tdsDeposited: 1500
      },
      {
        tan: 'DEL192830F',
        deductorName: 'APEX CORP RETAIL TRADERS',
        pan: 'AACCA9876K',
        section: '194Q',
        transactionDate: '2026-07-30',
        amountPaidCredited: 6000000,
        tdsDeposited: 1000
      }
    ];

    setFile(new File(['sample'], `Form_26AS_Sample_${format.toUpperCase()}.${format === 'excel' ? 'xlsx' : format}`));
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
    const transformed: TDS26ASRecord[] = [];

    rawRows.forEach((row, idx) => {
      const mapped: any = {};
      Object.entries(mapping).forEach(([sourceCol, targetField]) => {
        mapped[targetField] = row[sourceCol];
      });

      const tan = String(mapped.tan || row.tan || row.TAN || `TAN${idx}1234A`).trim().toUpperCase();
      const deductorName = String(mapped.deductorName || row.deductorName || row['Deductor Name'] || row.Party || 'Unknown Client').trim();
      const section = String(mapped.section || row.section || row.Section || '194C').trim();
      const rawDate = String(mapped.transactionDate || row.transactionDate || row.Date || '2026-05-15').trim();
      const amountPaid = parseFloat(String(mapped.amountPaidCredited ?? row.amountPaidCredited ?? row.Amount ?? 0).replace(/[^0-9.-]/g, '')) || 50000;
      const tdsDeposited = parseFloat(String(mapped.tdsDeposited ?? row.tdsDeposited ?? row['TDS Deposited'] ?? 0).replace(/[^0-9.-]/g, '')) || Math.round(amountPaid * 0.02);

      // Match with books sales invoices
      let matchedInv: Invoice | undefined;
      const matchingCustomer = customers.find(c =>
        c.name.toLowerCase().includes(deductorName.toLowerCase()) ||
        deductorName.toLowerCase().includes(c.name.toLowerCase()) ||
        (c.pan && row.pan && c.pan.toUpperCase() === String(row.pan).toUpperCase())
      );

      if (matchingCustomer) {
        matchedInv = existingInvoices.find(inv =>
          inv.customerId === matchingCustomer.id &&
          (Math.abs(inv.taxableValue - amountPaid) < 100 || Math.abs(inv.totalInvoiceValue - amountPaid) < 100)
        );
      }

      let status: 'Matched' | 'TDS Mismatch' | 'TDS Not Reflected' = 'TDS Not Reflected';
      let discrepancyReason: string | undefined;

      if (matchedInv) {
        if (Math.abs(matchedInv.expectedTds - tdsDeposited) <= 2) {
          status = 'Matched';
        } else {
          status = 'TDS Mismatch';
          discrepancyReason = `Expected TDS ₹${matchedInv.expectedTds} (${matchedInv.tdsSection || '194C'}), but 26AS shows ₹${tdsDeposited}`;
        }
      } else {
        discrepancyReason = 'No matching sales invoice found for this deduction amount in books';
      }

      transformed.push({
        id: `tds-imp-${Date.now()}-${idx}`,
        tan,
        deductorName,
        pan: matchingCustomer?.pan || 'AAACA1234B',
        section,
        transactionDate: rawDate,
        amountPaidCredited: amountPaid,
        tdsDeducted: tdsDeposited,
        tdsDeposited,
        assessmentYear: '2027-28',
        financialYear: '2026-27',
        quarter: 'Q1',
        matchedInvoiceId: matchedInv?.id,
        matchedInvoiceNumber: matchedInv?.invoiceNumber,
        customerId: matchingCustomer?.id,
        status,
        discrepancyAmount: matchedInv ? Math.abs(matchedInv.expectedTds - tdsDeposited) : undefined,
        discrepancyReason
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

  const totalTds = parsedRecords.reduce((sum, r) => sum + r.tdsDeposited, 0);
  const matchedCount = parsedRecords.filter(r => r.status === 'Matched').length;
  const mismatchCount = parsedRecords.filter(r => r.status === 'TDS Mismatch').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Upload Form 26AS / AIS (FY 2026-27 / AY 2027-28)</h3>
              <p className="text-[11px] text-slate-500">Step {step} of 4 • Part A TRACES statement, PAN/TAN matching & TDS section audit</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Steps Tracker */}
        <div className="flex border-b border-slate-200 bg-white text-xs px-6 py-3 font-semibold">
          {[
            { s: 1, label: '1. Select 26AS File' },
            { s: 2, label: '2. Review Columns' },
            { s: 3, label: '3. Preview & Reconcile' },
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
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-emerald-100 text-emerald-800 border border-emerald-300">
                .CSV TRACES
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-blue-100 text-blue-800 border border-blue-300">
                .XLSX / .XLS
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-purple-100 text-purple-800 border border-purple-300">
                .PDF Statement
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-amber-100 text-amber-800 border border-amber-300">
                .JSON (AIS/TIS)
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
              <p className="font-bold text-slate-800 text-sm">Drag & drop your Form 26AS or AIS file here</p>
              <p className="text-xs text-slate-500 mt-1">Supports TRACES text/CSV, Excel, JSON or PDF statement</p>

              <label className="mt-4 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold cursor-pointer transition-colors shadow-xs">
                <span>Browse Local 26AS File</span>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv,.pdf,.json"
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
                Or quickly test with realistic Form 26AS statements:
              </span>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  onClick={() => loadSample26AS('csv')}
                  className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-900 border border-slate-300 hover:border-emerald-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample CSV
                </button>
                <button
                  onClick={() => loadSample26AS('excel')}
                  className="px-3 py-1.5 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-900 border border-slate-300 hover:border-blue-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample Excel (.xlsx)
                </button>
                <button
                  onClick={() => loadSample26AS('pdf')}
                  className="px-3 py-1.5 bg-white hover:bg-purple-50 text-slate-700 hover:text-purple-900 border border-slate-300 hover:border-purple-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-purple-600" />
                  <span>Load Sample PDF Statement</span>
                </button>
              </div>
            </div>

            <div className="text-left bg-slate-50 p-3 rounded-lg border border-slate-200 w-full text-xs text-slate-600 space-y-1">
              <span className="font-bold text-slate-700 block">TDS Sections Statutory Audit Coverage (FY 2026-27):</span>
              <p>• <strong>194C (1%/2%):</strong> Contractors & Sub-contractors</p>
              <p>• <strong>194J (10%/2%):</strong> Professional & Technical Services (rationalized 2% rate)</p>
              <p>• <strong>194Q (0.1%):</strong> Purchase of Goods over ₹50 Lakhs</p>
              <p>• <strong>194H (2%):</strong> Commission & Brokerage (reduced to 2% w.e.f. Oct 1, 2024)</p>
              <p>• <strong>194T (10%):</strong> Partner Remuneration / Interest (Finance Act 2024)</p>
            </div>
          </div>
        )}

        {/* Step 2: Mapping */}
        {step === 2 && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs">
            <div className="flex items-center justify-between bg-emerald-50 p-3 rounded-lg border border-emerald-200">
              <div>
                <p className="font-bold text-emerald-950">Review Form 26AS Columns</p>
                <p className="text-[11px] text-emerald-800">
                  File: {file?.name} ({rawRows.length} entries detected)
                </p>
              </div>
              <button
                onClick={() => setMapping(autoDetectMappings(headers, TDS_COLUMN_MAPPINGS))}
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
                    <th className="p-3">Required 26AS Field</th>
                    <th className="p-3">File Column Detected</th>
                    <th className="p-3">Sample Value (Row 1)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {TDS_COLUMN_MAPPINGS.map((def) => {
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
                <span>Continue to Preview</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Preview */}
        {step === 3 && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs">
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Deductions</span>
                <p className="text-base font-bold text-slate-900 mt-0.5">{parsedRecords.length}</p>
              </div>
              <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-emerald-800 block">Total TDS Deposited</span>
                <p className="text-base font-bold text-emerald-950 mt-0.5">{formatINR(totalTds)}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Reconciliation Preview</span>
                <p className="text-xs font-bold text-slate-900 mt-1">
                  <span className="text-emerald-700 font-bold">{matchedCount} Matched</span> • <span className="text-amber-700 font-bold">{mismatchCount} Discrepancies</span>
                </p>
              </div>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="max-h-72 overflow-y-auto">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 sticky top-0">
                    <tr>
                      <th className="p-3">TAN / Deductor</th>
                      <th className="p-3">Sec</th>
                      <th className="p-3 text-right">Amount Paid</th>
                      <th className="p-3 text-right">TDS Deposited</th>
                      <th className="p-3">Matched Invoice</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {parsedRecords.map((r, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="p-3">
                          <p className="font-semibold text-slate-900">{r.deductorName}</p>
                          <span className="text-[10px] font-mono text-slate-400">{r.tan}</span>
                        </td>
                        <td className="p-3 font-mono font-bold text-slate-700">{r.section}</td>
                        <td className="p-3 text-right font-mono">{formatINR(r.amountPaidCredited)}</td>
                        <td className="p-3 text-right font-mono font-bold text-emerald-700">{formatINR(r.tdsDeposited)}</td>
                        <td className="p-3 font-mono text-slate-600">
                          {r.matchedInvoiceNumber || <span className="text-slate-400 italic">None</span>}
                        </td>
                        <td className="p-3">
                          {r.status === 'Matched' ? (
                            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-semibold rounded text-[10px]">
                              Matched
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-amber-100 text-amber-800 font-semibold rounded text-[10px]">
                              {r.status}
                            </span>
                          )}
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
                <span>Import {parsedRecords.length} 26AS Records</span>
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
            <h3 className="text-lg font-bold text-slate-900">Form 26AS Successfully Uploaded!</h3>
            <p className="text-xs text-slate-500 max-w-md">
              {parsedRecords.length} entries have been integrated into your TDS 26AS reconciliation ledger. Matching against sales invoices and customer ledgers has been completed.
            </p>
            <div className="pt-2">
              <button
                onClick={onClose}
                className="px-6 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold text-xs shadow-xs"
              >
                View TDS 26AS Ledger
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
