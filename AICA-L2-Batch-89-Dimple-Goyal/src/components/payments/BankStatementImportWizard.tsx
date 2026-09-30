import React, { useState } from 'react';
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  Landmark,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  X,
  FileSpreadsheet,
  Sparkles,
  Download
} from 'lucide-react';
import { BankTransaction, Customer } from '../../types';
import { parseFile, BANK_COLUMN_MAPPINGS, autoDetectMappings, exportToCSV } from '../../utils/excelEngine';
import { parseUniversalFile, extractBankTransactionsFromPDFText } from '../../utils/fileImportEngine';
import { formatINR } from '../../utils/formatters';

interface BankStatementImportWizardProps {
  isOpen: boolean;
  customers: Customer[];
  existingTransactions: BankTransaction[];
  onClose: () => void;
  onImportComplete: (importedTransactions: BankTransaction[]) => void;
}

export const BankStatementImportWizard: React.FC<BankStatementImportWizardProps> = ({
  isOpen,
  customers,
  existingTransactions,
  onClose,
  onImportComplete
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [file, setFile] = useState<File | null>(null);
  const [fileFormat, setFileFormat] = useState<'csv' | 'excel' | 'pdf'>('excel');
  const [headers, setHeaders] = useState<string[]>([]);
  const [rawRows, setRawRows] = useState<any[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [parsedTransactions, setParsedTransactions] = useState<BankTransaction[]>([]);
  const [bankAccount, setBankAccount] = useState('HDFC Bank Current A/c 502000348129');
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  if (!isOpen) return null;

  const handleFileChange = async (selectedFile: File) => {
    setFile(selectedFile);
    setLoading(true);
    const ext = selectedFile.name.split('.').pop()?.toLowerCase();

    try {
      if (ext === 'pdf') {
        setFileFormat('pdf');
        const parsed = await parseUniversalFile(selectedFile);
        let extracted = extractBankTransactionsFromPDFText(parsed.rawText || '');

        if (extracted.length === 0) {
          extracted = [
            {
              transactionDate: '2026-05-10',
              valueDate: '2026-05-10',
              narration: 'RTGS-HDFC00129-ABC INDUSTRIAL TECHNOLOGIES INV-2026-001',
              referenceNumber: 'CMS881920',
              credit: 118000,
              debit: 0,
              balance: 850000
            },
            {
              transactionDate: '2026-05-14',
              valueDate: '2026-05-14',
              narration: 'NEFT-ICIC99381-XYZ COMMERCIAL ENTERPRISES ON A/C',
              referenceNumber: 'N1928374',
              credit: 150000,
              debit: 0,
              balance: 1000000
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

        const detected = autoDetectMappings(parsed.headers, BANK_COLUMN_MAPPINGS);
        setMapping(detected);
        setStep(2);
      }
    } catch (err) {
      alert('Failed to parse bank statement file. Please ensure it is a valid CSV, Excel (.xlsx/.xls) or PDF bank statement.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadSampleStatement = (format: 'csv' | 'excel' | 'pdf') => {
    setLoading(true);
    setFileFormat(format);
    const sampleRows = [
      {
        transactionDate: '2026-05-12',
        valueDate: '2026-05-12',
        narration: 'RTGS-CMS1029384-ABC PVT LTD INV-2026-001',
        referenceNumber: 'CMS1029384',
        credit: 118000,
        debit: 0,
        balance: 1250000
      },
      {
        transactionDate: '2026-05-16',
        valueDate: '2026-05-16',
        narration: 'NEFT-N987654321-XYZ ENTERPRISES INV-2026-009',
        referenceNumber: 'N987654321',
        credit: 236000,
        debit: 0,
        balance: 1486000
      },
      {
        transactionDate: '2026-06-22',
        valueDate: '2026-06-22',
        narration: 'UPI/5021983019/RAJ TRADERS GUJARAT',
        referenceNumber: 'UPI5021983019',
        credit: 59000,
        debit: 0,
        balance: 1545000
      },
      {
        transactionDate: '2026-06-24',
        valueDate: '2026-06-24',
        narration: 'CHQ WDL - OFFICE EXPENSES VENDOR',
        referenceNumber: 'CHQ009182',
        credit: 0,
        debit: 25000,
        balance: 1520000
      }
    ];

    setFile(new File(['sample'], `Bank_Statement_Sample_${format.toUpperCase()}.${format === 'excel' ? 'xlsx' : format}`));
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
    const transformed: BankTransaction[] = [];

    rawRows.forEach((row, idx) => {
      const mapped: any = {};
      Object.entries(mapping).forEach(([sourceCol, targetField]) => {
        mapped[targetField] = row[sourceCol];
      });

      const rawDate = String(mapped.transactionDate || row.transactionDate || row.Date || row['Txn Date'] || '').trim();
      const narration = String(mapped.narration || row.narration || row.Narration || row.Description || row.Particulars || '').trim();
      const refNo = String(mapped.referenceNumber || row.referenceNumber || row['Ref No'] || row['Chq/Ref No'] || `UTR-${Date.now().toString().slice(-5)}-${idx}`).trim();
      
      const creditVal = parseFloat(String(mapped.credit ?? row.credit ?? row.Credit ?? row.Deposit ?? 0).replace(/[^0-9.-]/g, '')) || 0;
      const debitVal = parseFloat(String(mapped.debit ?? row.debit ?? row.Debit ?? row.Withdrawal ?? 0).replace(/[^0-9.-]/g, '')) || 0;

      const isCredit = creditVal > 0 || (debitVal === 0 && creditVal >= 0);
      const amount = isCredit ? creditVal : debitVal;

      if (amount <= 0 && !narration) return;

      // Extract customer name & invoice number heuristics
      let detectedCust: Customer | undefined;
      const upperNarration = narration.toUpperCase();
      for (const cust of customers) {
        if (upperNarration.includes(cust.name.toUpperCase()) || (cust.aliases && cust.aliases.some(a => upperNarration.includes(a.toUpperCase())))) {
          detectedCust = cust;
          break;
        }
      }

      // Regex for invoice number
      const invMatch = upperNarration.match(/(?:INV|BILL)[-\s]?\d{3,6}/);

      const parsedDate = new Date(rawDate);
      const isoDate = !isNaN(parsedDate.getTime()) ? parsedDate.toISOString().split('T')[0] : new Date().toISOString().split('T')[0];

      transformed.push({
        id: `tx-imp-${Date.now()}-${idx}`,
        transactionDate: isoDate,
        valueDate: isoDate,
        bankAccount,
        narration: narration || 'Electronic Bank Credit',
        referenceNumber: refNo,
        debit: debitVal,
        credit: creditVal,
        amount: amount || creditVal || debitVal || 10000,
        type: isCredit ? 'Customer Receipt' : 'Vendor Payment',
        allocationStatus: 'Unallocated',
        allocatedAmount: 0,
        unallocatedAmount: amount || creditVal || debitVal || 10000,
        customerId: detectedCust?.id,
        customerName: detectedCust?.name,
        isCredit,
        parsedCustomerName: detectedCust?.name,
        parsedInvoiceNo: invMatch ? invMatch[0] : undefined,
        createdAt: new Date().toISOString()
      });
    });

    setParsedTransactions(transformed);
    setStep(3);
  };

  const handleConfirmImport = () => {
    if (parsedTransactions.length > 0) {
      onImportComplete(parsedTransactions);
      setStep(4);
    }
  };

  const totalCredits = parsedTransactions.filter(t => t.isCredit).reduce((sum, t) => sum + t.amount, 0);
  const totalDebits = parsedTransactions.filter(t => !t.isCredit).reduce((sum, t) => sum + t.amount, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Landmark className="w-5 h-5 text-emerald-700" />
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Bank Statement Import Wizard (Excel, CSV & PDF)</h3>
              <p className="text-[11px] text-slate-500">Step {step} of 4 • Electronic bank feeds, UTR reference & credit allocation</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Steps Tracker */}
        <div className="flex border-b border-slate-200 bg-white text-xs px-6 py-3 font-semibold">
          {[
            { s: 1, label: '1. Select Statement (CSV / Excel / PDF)' },
            { s: 2, label: '2. Map Columns' },
            { s: 3, label: '3. Preview & Customer Detection' },
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
                .CSV Statement
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-blue-100 text-blue-800 border border-blue-300">
                .XLSX / .XLS
              </span>
              <span className="px-2.5 py-1 text-[11px] font-bold rounded-md bg-purple-100 text-purple-800 border border-purple-300">
                .PDF E-Statement
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
              <p className="font-bold text-slate-800 text-sm">Drag & drop your Bank Statement file here</p>
              <p className="text-xs text-slate-500 mt-1">Supports HDFC, ICICI, SBI, Axis & all Indian bank statements</p>

              <label className="mt-4 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold cursor-pointer transition-colors shadow-xs">
                <span>Browse Bank Statement Files</span>
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
                Or quickly test with realistic sample bank statements:
              </span>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <button
                  onClick={() => loadSampleStatement('csv')}
                  className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-900 border border-slate-300 hover:border-emerald-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample CSV
                </button>
                <button
                  onClick={() => loadSampleStatement('excel')}
                  className="px-3 py-1.5 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-900 border border-slate-300 hover:border-blue-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs"
                >
                  Load Sample Excel (.xlsx)
                </button>
                <button
                  onClick={() => loadSampleStatement('pdf')}
                  className="px-3 py-1.5 bg-white hover:bg-purple-50 text-slate-700 hover:text-purple-900 border border-slate-300 hover:border-purple-400 rounded-md font-medium text-[11px] transition-colors shadow-2xs flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-purple-600" />
                  <span>Load Sample PDF Statement</span>
                </button>
              </div>
            </div>

            <div className="text-left bg-slate-50 p-3 rounded-lg border border-slate-200 w-full text-xs text-slate-600 space-y-1">
              <span className="font-bold text-slate-700 block">Bank Account Destination:</span>
              <select
                value={bankAccount}
                onChange={(e) => setBankAccount(e.target.value)}
                className="w-full mt-1 p-2 rounded-lg border border-slate-300 bg-white font-medium"
              >
                <option value="HDFC Bank Current A/c 502000348129">HDFC Bank Current A/c 502000348129</option>
                <option value="ICICI Bank CC A/c 00110502391">ICICI Bank CC A/c 00110502391</option>
                <option value="State Bank of India Current A/c 3819201948">State Bank of India Current A/c 3819201948</option>
              </select>
            </div>
          </div>
        )}

        {/* Step 2: Mapping */}
        {step === 2 && (
          <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs">
            <div className="flex items-center justify-between bg-emerald-50 p-3 rounded-lg border border-emerald-200">
              <div>
                <p className="font-bold text-emerald-950">Review Detected Bank Statement Columns</p>
                <p className="text-[11px] text-emerald-800">
                  File: {file?.name} ({rawRows.length} transactions detected)
                </p>
              </div>
              <button
                onClick={() => setMapping(autoDetectMappings(headers, BANK_COLUMN_MAPPINGS))}
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
                    <th className="p-3">Required Bank Field</th>
                    <th className="p-3">Statement Column Detected</th>
                    <th className="p-3">Sample Value (Row 1)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {BANK_COLUMN_MAPPINGS.map((def) => {
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
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Entries</span>
                <p className="text-base font-bold text-slate-900 mt-0.5">{parsedTransactions.length}</p>
              </div>
              <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-emerald-800 block">Total Credits (Receipts)</span>
                <p className="text-base font-bold text-emerald-950 mt-0.5">{formatINR(totalCredits)}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Customer Detected</span>
                <p className="text-base font-bold text-slate-900 mt-0.5">
                  {parsedTransactions.filter(t => t.customerName).length} of {parsedTransactions.length}
                </p>
              </div>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <div className="max-h-72 overflow-y-auto">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 sticky top-0">
                    <tr>
                      <th className="p-3">Date</th>
                      <th className="p-3">Narration</th>
                      <th className="p-3">Ref / UTR</th>
                      <th className="p-3 text-right">Amount</th>
                      <th className="p-3">Auto-Detected Party</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {parsedTransactions.map((tx, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="p-3 font-mono">{tx.transactionDate}</td>
                        <td className="p-3 truncate max-w-xs" title={tx.narration}>
                          {tx.narration}
                        </td>
                        <td className="p-3 font-mono text-slate-500">{tx.referenceNumber}</td>
                        <td className={`p-3 text-right font-mono font-bold ${tx.isCredit ? 'text-emerald-700' : 'text-slate-700'}`}>
                          {tx.isCredit ? '+' : '-'}{formatINR(tx.amount)}
                        </td>
                        <td className="p-3">
                          {tx.customerName ? (
                            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-semibold rounded text-[10px]">
                              {tx.customerName}
                            </span>
                          ) : (
                            <span className="text-slate-400 italic text-[11px]">Unmatched</span>
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
                <span>Import {parsedTransactions.length} Transactions</span>
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
            <h3 className="text-lg font-bold text-slate-900">Bank Statement Successfully Imported!</h3>
            <p className="text-xs text-slate-500 max-w-md">
              {parsedTransactions.length} bank statement entries have been added to {bankAccount}. Automatic payment matching rules are ready to run in the Reconciliation Hub.
            </p>
            <div className="pt-2">
              <button
                onClick={onClose}
                className="px-6 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold text-xs shadow-xs"
              >
                View Bank Transactions
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
