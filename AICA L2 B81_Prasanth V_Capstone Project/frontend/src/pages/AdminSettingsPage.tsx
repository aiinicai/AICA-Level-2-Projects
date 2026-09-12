import React, { useState, useEffect } from 'react';
import { Database, Download, UploadCloud, CheckCircle2, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-react';
import api from '../services/api';
import { useCompany } from '../context/CompanyContext';

export const AdminSettingsPage: React.FC = () => {
  const { companies } = useCompany();
  const [settings, setSettings] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const res = await api.get('/admin/settings');
      setSettings(res.data);
    } catch (e) {
      console.error('Failed to load settings:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleDownloadBackup = () => {
    window.open('/api/admin/backup', '_blank');
  };

  const handleRestoreDatabase = async () => {
    if (!restoreFile) return;
    if (!confirm('CAUTION: Restoring a database snapshot will overwrite existing records. Proceed?')) {
      return;
    }

    setRestoring(true);
    try {
      const formData = new FormData();
      formData.append('file', restoreFile);
      await api.post('/admin/restore', formData);
      setSuccessMsg('Database restored successfully! Refreshing view...');
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to restore database.');
    } finally {
      setRestoring(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">System Backup & Master Settings</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Execute one-click SQLite database snapshots, disaster recovery, and system default configurations
        </p>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          {successMsg}
        </div>
      )}

      {/* Database Backup & Restore Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backup Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3">
              <Download className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">Download Database Backup</h2>
            <p className="text-xs text-slate-500 mt-1">
              Exports the complete SQLite WAL database with all companies, assets, templates, and audit logs.
            </p>
          </div>

          <button
            onClick={handleDownloadBackup}
            className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs rounded-lg shadow-sm transition flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4 text-blue-400" />
            <span>Download .DB Snapshot</span>
          </button>
        </div>

        {/* Restore Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center mb-3">
              <UploadCloud className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">Restore Database Snapshot</h2>
            <p className="text-xs text-slate-500 mt-1">
              Upload a previously downloaded <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">.db</code> file to restore state.
            </p>
          </div>

          <div className="space-y-2">
            <input
              type="file"
              id="restore-file-input"
              accept=".db"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setRestoreFile(e.target.files[0]);
                }
              }}
              className="hidden"
            />
            <label
              htmlFor="restore-file-input"
              className="w-full py-2 border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-lg cursor-pointer transition text-center block truncate px-2"
            >
              {restoreFile ? restoreFile.name : 'Choose .db Backup File'}
            </label>

            {restoreFile && (
              <button
                onClick={handleRestoreDatabase}
                disabled={restoring}
                className="w-full py-2.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-bold text-xs rounded-lg shadow-sm transition flex items-center justify-center gap-2"
              >
                {restoring ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                <span>{restoring ? 'Restoring...' : 'Confirm & Restore DB'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Persistence and Architecture Note */}
      <div className="bg-slate-900 text-white p-6 rounded-xl border border-slate-800 space-y-2">
        <div className="text-xs font-bold text-blue-400 uppercase tracking-wider">Enterprise Persistence</div>
        <p className="text-xs text-slate-300 leading-relaxed">
          The database operates with SQLite Write-Ahead Logging (WAL) and atomic numbering sequence guarantees. Closing the browser or shutting down the application maintains 100% data integrity.
        </p>
      </div>
    </div>
  );
};
