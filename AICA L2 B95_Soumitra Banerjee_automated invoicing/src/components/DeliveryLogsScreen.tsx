import React, { useState, useRef } from 'react';
import { 
  FileSpreadsheet, 
  UploadCloud, 
  Download, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  ArrowRight, 
  RefreshCw,
  Search,
  Layers,
  Sparkles
} from 'lucide-react';
import { DeliveryLog } from '../types';
import { systemService } from '../lib/services/systemService';

interface DeliveryLogsScreenProps {
  logs: DeliveryLog[];
  loading: boolean;
  onRefresh: () => void;
  onNavigateToBilling: () => void;
}

interface ValidationRow {
  clientCode: string;
  clientId: string;
  clientName: string;
  month: string;
  quarter: string;
  financialYear: string;
  fileCount: number;
  amount: number;
}

interface ValidationError {
  rowNumber: number;
  clientCode?: string;
  field: string;
  message: string;
}

export const DeliveryLogsScreen: React.FC<DeliveryLogsScreenProps> = ({
  logs,
  loading,
  onRefresh,
  onNavigateToBilling,
}) => {
  const [activeTab, setActiveTab] = useState<'upload' | 'records'>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    totalRows: number;
    validRows: ValidationRow[];
    errors: ValidationError[];
  } | null>(null);
  const [importSuccessMsg, setImportSuccessMsg] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Records view filters
  const [searchFilter, setSearchFilter] = useState('');
  const [monthFilter, setMonthFilter] = useState('ALL');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setValidationResult(null);
    setImportSuccessMsg('');
    setErrorMessage('');
    handleValidate(file);
  };

  const handleValidate = async (fileToValidate?: File) => {
    const file = fileToValidate || selectedFile;
    if (!file) {
      setErrorMessage('Please select an Excel file first.');
      return;
    }

    setValidating(true);
    setErrorMessage('');
    setImportSuccessMsg('');

    try {
      const res = await systemService.validateExcel(file);
      setValidationResult(res);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to validate Excel file.');
    } finally {
      setValidating(false);
    }
  };

  const handleImport = () => {
    if (!validationResult || validationResult.validRows.length === 0) {
      setErrorMessage('No valid records to import.');
      return;
    }

    setImporting(true);
    setErrorMessage('');

    try {
      const res = systemService.importDeliveryRecords(validationResult.validRows);
      setImportSuccessMsg(`Successfully imported ${res.importedCount} delivery log records into database!`);
      setValidationResult(null);
      setSelectedFile(null);
      onRefresh();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to import delivery records.');
    } finally {
      setImporting(false);
    }
  };

  const handleQuickLoadSample = () => {
    const sampleRows = [
      { clientCode: 'ABC001', clientId: 'c-abc-001', clientName: 'ABC Limited', month: 'April', quarter: 'Q1', financialYear: '2026-27', fileCount: 1200, amount: 6000 },
      { clientCode: 'ABC001', clientId: 'c-abc-001', clientName: 'ABC Limited', month: 'May', quarter: 'Q1', financialYear: '2026-27', fileCount: 1350, amount: 6750 },
      { clientCode: 'ABC001', clientId: 'c-abc-001', clientName: 'ABC Limited', month: 'June', quarter: 'Q1', financialYear: '2026-27', fileCount: 1500, amount: 7500 },
      { clientCode: 'XYZ001', clientId: 'c-xyz-001', clientName: 'XYZ Limited', month: 'April', quarter: 'Q1', financialYear: '2026-27', fileCount: 900, amount: 6300 },
      { clientCode: 'XYZ001', clientId: 'c-xyz-001', clientName: 'XYZ Limited', month: 'May', quarter: 'Q1', financialYear: '2026-27', fileCount: 950, amount: 6650 },
      { clientCode: 'XYZ001', clientId: 'c-xyz-001', clientName: 'XYZ Limited', month: 'June', quarter: 'Q1', financialYear: '2026-27', fileCount: 1000, amount: 7000 },
      { clientCode: 'GTS001', clientId: 'c-gts-001', clientName: 'Global Tech Solutions', month: 'April', quarter: 'Q1', financialYear: '2026-27', fileCount: 650, amount: 3900 },
      { clientCode: 'GTS001', clientId: 'c-gts-001', clientName: 'Global Tech Solutions', month: 'May', quarter: 'Q1', financialYear: '2026-27', fileCount: 720, amount: 4320 },
      { clientCode: 'GTS001', clientId: 'c-gts-001', clientName: 'Global Tech Solutions', month: 'June', quarter: 'Q1', financialYear: '2026-27', fileCount: 850, amount: 5100 },
    ];

    setValidationResult({
      valid: true,
      totalRows: 9,
      validRows: sampleRows,
      errors: [],
    });
    setErrorMessage('');
    setImportSuccessMsg('');
  };

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.clientName.toLowerCase().includes(searchFilter.toLowerCase()) ||
      log.clientCode.toLowerCase().includes(searchFilter.toLowerCase());
    const matchesMonth = monthFilter === 'ALL' || log.month.toLowerCase() === monthFilter.toLowerCase();
    return matchesSearch && matchesMonth;
  });

  const totalFiles = logs.reduce((acc, curr) => acc + curr.fileCount, 0);
  const totalAmount = logs.reduce((acc, curr) => acc + curr.amount, 0);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Delivery Logs &amp; Excel Import</h1>
          <p className="text-sm text-slate-500">
            Ingest monthly client delivery metrics, validate file counts, and store in SQLite.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => systemService.downloadSampleTemplate()}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Download Sample Template</span>
          </button>
          <button
            onClick={handleQuickLoadSample}
            disabled={validating}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <Sparkles className="w-4 h-4 text-blue-600" />
            <span>1-Click Load Sample Data</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('upload')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
              activeTab === 'upload'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload &amp; Validate Excel</span>
          </button>
          <button
            onClick={() => setActiveTab('records')}
            className={`py-3 px-1 border-b-2 font-medium text-sm transition flex items-center gap-2 ${
              activeTab === 'records'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Processed Delivery Records ({logs.length})</span>
          </button>
        </nav>
      </div>

      {activeTab === 'upload' ? (
        <div className="space-y-6">
          {/* Upload Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileSelect(e.dataTransfer.files[0]);
              }
            }}
            className="border-2 border-dashed border-slate-300 hover:border-blue-500 bg-slate-50 hover:bg-blue-50/40 rounded-2xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center space-y-3"
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".xlsx, .xls"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
              className="hidden"
            />
            <div className="w-14 h-14 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shadow-xs">
              <FileSpreadsheet className="w-7 h-7" />
            </div>
            <div>
              <p className="text-base font-semibold text-slate-900">
                {selectedFile ? selectedFile.name : 'Click to select or drag and drop Excel delivery log'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Supported formats: <span className="font-mono text-slate-700">.xlsx, .xls</span> (Columns: Client Code, Client Name, Month, File Count, Amount)
              </p>
            </div>
            {selectedFile && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            )}
          </div>

          {/* Messages */}
          {errorMessage && (
            <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl flex items-start gap-3 text-sm">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Validation Error</p>
                <p className="text-xs mt-0.5">{errorMessage}</p>
              </div>
            </div>
          )}

          {importSuccessMsg && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center justify-between gap-4 text-sm">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span className="font-medium">{importSuccessMsg}</span>
              </div>
              <button
                onClick={onNavigateToBilling}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <span>Proceed to Billing</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Validation Status & Preview */}
          {validating && (
            <div className="p-8 text-center bg-white rounded-xl border border-slate-200 shadow-xs space-y-2">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600 mx-auto" />
              <p className="text-sm font-semibold text-slate-800">Validating Excel records against client master...</p>
            </div>
          )}

          {validationResult && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden space-y-4 p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900">Delivery Log Validation Preview</h3>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        validationResult.valid
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                          : 'bg-amber-100 text-amber-800 border border-amber-200'
                      }`}
                    >
                      {validationResult.valid ? 'Ready for Import' : `${validationResult.errors.length} Errors Found`}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Total Rows Parsed: {validationResult.totalRows} | Valid: {validationResult.validRows.length} | Errors: {validationResult.errors.length}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleValidate()}
                    disabled={validating}
                    className="px-3.5 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 transition"
                  >
                    Re-Validate
                  </button>
                  <button
                    onClick={handleImport}
                    disabled={importing || validationResult.validRows.length === 0}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition flex items-center gap-2 disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{importing ? 'Importing...' : `Import ${validationResult.validRows.length} Records`}</span>
                  </button>
                </div>
              </div>

              {/* Errors Display */}
              {validationResult.errors.length > 0 && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-2">
                  <h4 className="text-xs font-bold text-rose-800 uppercase tracking-wider flex items-center gap-1.5">
                    <XCircle className="w-4 h-4 text-rose-600" />
                    Validation Errors:
                  </h4>
                  <div className="max-h-40 overflow-y-auto space-y-1 text-xs text-rose-700">
                    {validationResult.errors.map((err, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="font-mono bg-rose-100 px-1.5 py-0.5 rounded text-[11px] font-bold">
                          Row {err.rowNumber}
                        </span>
                        <span className="font-semibold text-rose-900">[{err.field}]:</span>
                        <span>{err.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Valid Rows Preview Table */}
              <div>
                <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">
                  Valid Records to be Ingested ({validationResult.validRows.length})
                </h4>
                <div className="overflow-x-auto border border-slate-200 rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 uppercase text-[11px] font-semibold">
                      <tr>
                        <th className="py-2.5 px-3">Client Code</th>
                        <th className="py-2.5 px-3">Client Name</th>
                        <th className="py-2.5 px-3">Month</th>
                        <th className="py-2.5 px-3">Quarter</th>
                        <th className="py-2.5 px-3 text-right">File Count</th>
                        <th className="py-2.5 px-3 text-right">Amount (₹)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {validationResult.validRows.map((r, idx) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="py-2 px-3 font-mono font-bold text-blue-700">{r.clientCode}</td>
                          <td className="py-2 px-3 font-medium text-slate-800">{r.clientName}</td>
                          <td className="py-2 px-3 text-slate-600">{r.month}</td>
                          <td className="py-2 px-3 text-slate-500">{r.quarter} ({r.financialYear})</td>
                          <td className="py-2 px-3 text-right font-mono font-semibold text-slate-900">
                            {r.fileCount.toLocaleString('en-IN')}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-slate-900">
                            ₹{r.amount.toLocaleString('en-IN')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Records Tab */
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter by client..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <select
                value={monthFilter}
                onChange={(e) => setMonthFilter(e.target.value)}
                className="py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
              >
                <option value="ALL">All Months</option>
                <option value="April">April</option>
                <option value="May">May</option>
                <option value="June">June</option>
                <option value="July">July</option>
                <option value="August">August</option>
                <option value="September">September</option>
              </select>
            </div>

            <div className="flex items-center gap-6 text-xs text-slate-600">
              <div>
                <span>Total Files:</span>{' '}
                <strong className="text-slate-900 font-mono text-sm">{totalFiles.toLocaleString('en-IN')}</strong>
              </div>
              <div>
                <span>Total Value:</span>{' '}
                <strong className="text-slate-900 font-mono text-sm">₹{totalAmount.toLocaleString('en-IN')}</strong>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold uppercase text-slate-600 tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Client Code</th>
                    <th className="py-3 px-4">Client Name</th>
                    <th className="py-3 px-4">Month</th>
                    <th className="py-3 px-4">Cycle</th>
                    <th className="py-3 px-4 text-right">File Count</th>
                    <th className="py-3 px-4 text-right">Amount (₹)</th>
                    <th className="py-3 px-4 text-slate-400">Import Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        Loading delivery logs...
                      </td>
                    </tr>
                  ) : filteredLogs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        No delivery logs found.
                      </td>
                    </tr>
                  ) : (
                    filteredLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50">
                        <td className="py-3 px-4 font-mono font-bold text-blue-700 text-xs">{log.clientCode}</td>
                        <td className="py-3 px-4 font-semibold text-slate-900">{log.clientName}</td>
                        <td className="py-3 px-4">{log.month}</td>
                        <td className="py-3 px-4 text-xs text-slate-500 font-mono">
                          {log.quarter} FY {log.financialYear}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                          {log.fileCount.toLocaleString('en-IN')}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-900">
                          ₹{log.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-3 px-4 text-xs text-slate-400">
                          {new Date(log.createdAt).toLocaleDateString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
