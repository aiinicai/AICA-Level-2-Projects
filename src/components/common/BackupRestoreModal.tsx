import React, { useState, useRef } from 'react';
import {
  X,
  HardDrive,
  Download,
  Upload,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  Database
} from 'lucide-react';
import { StorageService } from '../../services/storage';

interface BackupRestoreModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefreshData: () => void;
}

export const BackupRestoreModal: React.FC<BackupRestoreModalProps> = ({
  isOpen,
  onClose,
  onRefreshData,
}) => {
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const storage = StorageService.getInstance();
  const dbState = storage.getState();

  const handleExportJSON = () => {
    try {
      const jsonStr = storage.exportDatabaseJson();
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const filename = `kilitrade_backup_${new Date().toISOString().slice(0, 10)}.json`;
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setFeedback({
        type: 'success',
        message: `Database backup file (${filename}) exported successfully.`,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', message: `Export failed: ${err.message}` });
    }
  };

  const handleExportSQLiteSchema = () => {
    try {
      // Generate SQL Dump string for SQLite compatibility
      let sqlDump = `-- KiliTrade Desktop Suite SQLite Migration Dump\n`;
      sqlDump += `-- Exported on: ${new Date().toISOString()}\n\n`;

      sqlDump += `CREATE TABLE IF NOT EXISTS company_profile (\n  id TEXT PRIMARY KEY,\n  name TEXT,\n  tin TEXT,\n  vrn TEXT,\n  address TEXT,\n  phone TEXT,\n  email TEXT,\n  website TEXT,\n  bank_details TEXT,\n  theme TEXT\n);\n\n`;
      sqlDump += `CREATE TABLE IF NOT EXISTS clients (\n  id TEXT PRIMARY KEY,\n  name TEXT,\n  contact_person TEXT,\n  mobile TEXT,\n  email TEXT,\n  address TEXT,\n  tin TEXT,\n  license_no TEXT,\n  is_vat_registered INTEGER,\n  tags TEXT,\n  created_at TEXT\n);\n\n`;
      sqlDump += `CREATE TABLE IF NOT EXISTS vouchers (\n  id TEXT PRIMARY KEY,\n  type TEXT,\n  doc_number TEXT,\n  doc_date TEXT,\n  client_id TEXT,\n  currency TEXT,\n  subtotal REAL,\n  total_vat REAL,\n  grand_total REAL,\n  round_off_adjustment REAL,\n  status TEXT\n);\n\n`;

      // Insert Company Profile
      const cp = storage.getCompanyProfile();
      sqlDump += `INSERT OR REPLACE INTO company_profile VALUES ('${cp.id}', '${cp.name.replace(/'/g, "''")}', '${cp.tin}', '${cp.vrn || ''}', '${cp.address.replace(/'/g, "''")}', '${cp.phone}', '${cp.email}', '${cp.website}', '${JSON.stringify(cp.bankDetails).replace(/'/g, "''")}', '${JSON.stringify(cp.theme).replace(/'/g, "''")}');\n\n`;

      // Insert Clients
      dbState.clients.forEach(c => {
        sqlDump += `INSERT OR REPLACE INTO clients VALUES ('${c.id}', '${c.name.replace(/'/g, "''")}', '${c.contactPerson.replace(/'/g, "''")}', '${c.mobile}', '${c.email}', '${c.address.replace(/'/g, "''")}', '${c.tin}', '${c.licenseNo}', ${c.isVatRegistered ? 1 : 0}, '${JSON.stringify(c.tags).replace(/'/g, "''")}', '${c.createdAt}');\n`;
      });

      // Insert Vouchers
      dbState.vouchers.forEach(v => {
        sqlDump += `INSERT OR REPLACE INTO vouchers VALUES ('${v.id}', '${v.type}', '${v.docNumber}', '${v.docDate}', '${v.clientId}', '${v.currency}', ${v.subtotal}, ${v.totalVat}, ${v.finalGrandTotal}, ${v.roundOffAdjustment}, '${v.status}');\n`;
      });

      const blob = new Blob([sqlDump], { type: 'application/sql' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const filename = `kilitrade_sqlite_dump_${new Date().toISOString().slice(0, 10)}.sql`;
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setFeedback({
        type: 'success',
        message: `SQLite SQL dump (${filename}) generated successfully.`,
      });
    } catch (err: any) {
      setFeedback({ type: 'error', message: `SQL Export failed: ${err.message}` });
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    const reader = new FileReader();
    reader.onload = (evt) => {
      const content = evt.target?.result as string;
      const res = storage.importDatabaseJson(content);
      setIsProcessing(false);
      if (res.success) {
        setFeedback({ type: 'success', message: res.message });
        onRefreshData();
      } else {
        setFeedback({ type: 'error', message: res.message });
      }
    };
    reader.onerror = () => {
      setIsProcessing(false);
      setFeedback({ type: 'error', message: 'Failed to read the backup file.' });
    };
    reader.readAsText(file);
  };

  const handleReset = () => {
    if (window.confirm('Are you sure you want to reset the database to the initial seed records? All unsaved test changes will be replaced.')) {
      storage.resetToSeedData();
      setFeedback({ type: 'success', message: 'Database reset to default seed data.' });
      onRefreshData();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-xl w-full overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <HardDrive className="w-5 h-5 text-amber-400" />
            <h3 className="font-semibold text-base">Local SQLite Database & Backup Manager</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
            <div>
              <p className="text-xs text-slate-500 font-medium">Clients Stored</p>
              <p className="text-lg font-bold text-slate-800">{dbState.clients.length}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">Vouchers & Invoices</p>
              <p className="text-lg font-bold text-slate-800">{dbState.vouchers.length}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">KYC Documents</p>
              <p className="text-lg font-bold text-slate-800">{dbState.clientDocuments?.length || 0}</p>
            </div>
          </div>

          {feedback && (
            <div
              className={`p-3.5 rounded-lg flex items-start space-x-2.5 text-xs font-medium ${
                feedback.type === 'success'
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}

          {/* Action Cards */}
          <div className="space-y-3">
            {/* Export JSON */}
            <div className="flex items-center justify-between p-3.5 border border-slate-200 rounded-lg hover:border-slate-300 transition">
              <div>
                <h4 className="text-xs font-bold text-slate-800">Export Full JSON Database Backup</h4>
                <p className="text-[11px] text-slate-500">
                  Saves all clients, vouchers, settings, KYC documents, and branding images into a single portable file.
                </p>
              </div>
              <button
                onClick={handleExportJSON}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold shrink-0 transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export JSON</span>
              </button>
            </div>

            {/* Export SQL */}
            <div className="flex items-center justify-between p-3.5 border border-slate-200 rounded-lg hover:border-slate-300 transition">
              <div>
                <h4 className="text-xs font-bold text-slate-800">Export SQLite Compatible Schema & SQL</h4>
                <p className="text-[11px] text-slate-500">
                  Generates native DDL and DML statements ready for import into standard SQLite / DB Browser tools.
                </p>
              </div>
              <button
                onClick={handleExportSQLiteSchema}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded text-xs font-semibold shrink-0 transition"
              >
                <Database className="w-3.5 h-3.5 text-amber-400" />
                <span>Export SQL</span>
              </button>
            </div>

            {/* Restore File */}
            <div className="flex items-center justify-between p-3.5 border border-slate-200 rounded-lg hover:border-slate-300 transition">
              <div>
                <h4 className="text-xs font-bold text-slate-800">Restore / Import Database</h4>
                <p className="text-[11px] text-slate-500">
                  Upload a previously saved JSON backup to restore all records and profile configurations.
                </p>
              </div>
              <div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".json"
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isProcessing}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 rounded text-xs font-semibold shrink-0 transition"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Restore File</span>
                </button>
              </div>
            </div>
          </div>

          {/* Reset Action */}
          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
            <button
              onClick={handleReset}
              className="text-xs text-rose-600 hover:text-rose-700 flex items-center space-x-1.5 font-medium transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset Database to Seed Data</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded text-xs font-semibold transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
