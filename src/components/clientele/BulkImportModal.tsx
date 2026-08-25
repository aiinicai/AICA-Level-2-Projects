import React, { useState, useRef } from 'react';
import {
  X,
  FileSpreadsheet,
  Download,
  Upload,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Users
} from 'lucide-react';
import { Client } from '../../types';
import { StorageService, formatTIN, validateTIN } from '../../services/storage';

interface BulkImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportComplete: () => void;
}

interface ParsedRow {
  name: string;
  contactPerson: string;
  mobile: string;
  email: string;
  address: string;
  tin: string;
  licenseNo: string;
  isVatRegistered: boolean;
  tags: string[];
  errors: string[];
}

export const BulkImportModal: React.FC<BulkImportModalProps> = ({
  isOpen,
  onClose,
  onImportComplete,
}) => {
  const [parsedRows, setParsedRows] = useState<ParsedRow[]>([]);
  const [rawText, setRawText] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDownloadTemplate = () => {
    const csvContent =
      'Company Name,Contact Person,Mobile,Email,Address,TIN,License No,VAT Registered,Tags\n' +
      'Serengeti Infrastructure Ltd,Salim Mwamba,+255 754 829 104,salim@serengeti.co.tz,"Plot 45 Nyerere Rd, Dar es Salaam",102-491-884,BL-2025-0981,TRUE,"Road Works, Logistics"\n' +
      'Kilimanjaro Aggregates Co,Fatma Rashid,+255 784 102 993,fatma@kiliagg.co.tz,"Moshi Industrial Estate, Kilimanjaro",104-582-190,BL-2024-4410,TRUE,"Quarry, Aggregates"\n' +
      'Zanzibar Spices & Forwarding,Hamad Ali,+255 777 349 102,hamad@zanzispice.tz,"Malindi Port Road, Zanzibar",108-992-341,BL-2025-1102,FALSE,"Export, Port"\n';

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'kilitrade_client_import_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const parseCSVText = (text: string) => {
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
    if (lines.length <= 1) {
      setParsedRows([]);
      return;
    }

    const rows: ParsedRow[] = [];
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      // Basic CSV splitter respecting quoted commas
      const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || line.split(',');
      const cols = matches.map((c) => c.replace(/^"|"$/g, '').trim());

      const name = cols[0] || '';
      const contactPerson = cols[1] || '';
      const mobile = cols[2] || '';
      const email = cols[3] || '';
      const address = cols[4] || '';
      const rawTin = cols[5] || '';
      const licenseNo = cols[6] || '';
      const isVatRegistered = cols[7]?.toLowerCase() === 'true' || cols[7] === '1';
      const tags = cols[8]?.split(';').map((t) => t.trim()).filter(Boolean) || [];

      const formattedTin = formatTIN(rawTin);
      const errors: string[] = [];

      if (!name) errors.push('Company Name missing');
      if (formattedTin && !validateTIN(formattedTin)) errors.push('Invalid 9-digit TIN');

      rows.push({
        name,
        contactPerson,
        mobile,
        email,
        address,
        tin: formattedTin || 'N/A',
        licenseNo,
        isVatRegistered,
        tags,
        errors,
      });
    }

    setParsedRows(rows);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target?.result as string;
      setRawText(text);
      parseCSVText(text);
    };
    reader.readAsText(file);
  };

  const handleCommitImport = () => {
    const validRows = parsedRows.filter((r) => r.errors.length === 0);
    if (validRows.length === 0) {
      setFeedback({ type: 'error', message: 'No valid rows to import.' });
      return;
    }

    const storage = StorageService.getInstance();
    const existingClients = storage.getClients();

    const newClients: Client[] = validRows.map((r, idx) => ({
      id: `cli_imp_${Date.now()}_${idx}`,
      name: r.name,
      contactPerson: r.contactPerson,
      mobile: r.mobile,
      email: r.email,
      address: r.address,
      tin: r.tin,
      licenseNo: r.licenseNo,
      isVatRegistered: r.isVatRegistered,
      tags: r.tags.length > 0 ? r.tags : ['Imported'],
      createdAt: new Date().toISOString(),
    }));

    storage.saveClients([...existingClients, ...newClients]);
    setFeedback({
      type: 'success',
      message: `Successfully imported ${newClients.length} clients into the local database.`,
    });
    setTimeout(() => {
      onImportComplete();
      onClose();
    }, 1500);
  };

  const totalErrors = parsedRows.reduce((sum, r) => sum + r.errors.length, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2.5">
            <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
            <h3 className="font-semibold text-sm">Bulk Client Import & Validation</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
            <div>
              <h4 className="font-bold text-emerald-900">Standard CSV / Excel Spreadsheet Import</h4>
              <p className="text-emerald-800 text-[11px] mt-0.5">
                Download the official CSV template with TRA TIN and address formatting columns.
              </p>
            </div>
            <button
              onClick={handleDownloadTemplate}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-semibold shrink-0 transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Template</span>
            </button>
          </div>

          {/* Upload Input */}
          <div className="border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer bg-slate-50/50 transition">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".csv,.txt"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center space-x-2 text-slate-700 font-bold"
            >
              <Upload className="w-4 h-4 text-emerald-600" />
              <span>Click to select CSV File</span>
            </button>
            <p className="text-[11px] text-slate-400 mt-1">Or paste CSV content directly into the app</p>
          </div>

          {/* Validation Feedback */}
          {feedback && (
            <div
              className={`p-3 rounded-lg flex items-center space-x-2 font-medium ${
                feedback.type === 'success'
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}

          {/* Preview Table */}
          {parsedRows.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between font-bold text-slate-700">
                <span>Data Validation Preview ({parsedRows.length} rows found):</span>
                {totalErrors > 0 && (
                  <span className="text-rose-600 font-medium flex items-center space-x-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>{totalErrors} row error(s) flagged</span>
                  </span>
                )}
              </div>

              <div className="border border-slate-200 rounded-lg overflow-x-auto max-h-60 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[10px]">
                    <tr>
                      <th className="p-2">Status</th>
                      <th className="p-2">Company Name</th>
                      <th className="p-2">TIN</th>
                      <th className="p-2">Contact</th>
                      <th className="p-2">Mobile</th>
                      <th className="p-2">VAT Reg</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {parsedRows.map((row, idx) => (
                      <tr key={idx} className={row.errors.length > 0 ? 'bg-rose-50/60' : 'bg-white'}>
                        <td className="p-2">
                          {row.errors.length > 0 ? (
                            <span className="text-rose-600 font-bold text-[10px]" title={row.errors.join(', ')}>
                              ❌ {row.errors[0]}
                            </span>
                          ) : (
                            <span className="text-emerald-600 font-bold text-[10px]">✓ Valid</span>
                          )}
                        </td>
                        <td className="p-2 font-medium text-slate-900">{row.name || 'MISSING'}</td>
                        <td className="p-2 font-mono">{row.tin}</td>
                        <td className="p-2 text-slate-700">{row.contactPerson}</td>
                        <td className="p-2 font-mono text-slate-700">{row.mobile}</td>
                        <td className="p-2">{row.isVatRegistered ? 'Yes' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-1.5 border border-slate-300 text-slate-700 hover:bg-slate-100 rounded font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={handleCommitImport}
            disabled={parsedRows.length === 0}
            className="flex items-center space-x-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-semibold shadow-xs transition disabled:opacity-50"
          >
            <Users className="w-3.5 h-3.5" />
            <span>
              Import {parsedRows.filter((r) => r.errors.length === 0).length} Valid Clients
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};
