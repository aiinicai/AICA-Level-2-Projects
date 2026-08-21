import React, { useRef } from 'react';
import { useGrant } from '../context/GrantContext';
import { Search, Download, Upload, RotateCcw, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const Navbar = () => {
  const {
    ngoProfile,
    handleResetDemoData,
    handleExportBackup,
    handleImportBackup
  } = useGrant();

  const fileInputRef = useRef(null);

  const onFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target.result);
        handleImportBackup(parsed);
      } catch (err) {
        alert('Invalid JSON file format.');
      }
    };
    reader.readAsText(file);
  };

  return (
    <header className="navbar">
      <div className="nav-search">
        <Search size={16} style={{ color: 'var(--text-muted)' }} />
        <input type="text" placeholder="Search Grants, Proposals, FCRA Vouchers..." />
      </div>

      <div className="navbar-actions">
        {ngoProfile.fcraStatus === 'Active' ? (
          <span className="badge badge-fcra" title="FCRA Account Designated at SBI New Delhi Main Branch">
            <CheckCircle2 size={13} /> FCRA Registered ({ngoProfile.fcraRegNo})
          </span>
        ) : (
          <span className="badge badge-pending">
            <ShieldAlert size={13} /> FCRA Renewal Due
          </span>
        )}

        <button className="btn btn-secondary btn-sm" onClick={handleResetDemoData} title="Load realistic sample data for testing">
          <RotateCcw size={14} /> Reset Demo Data
        </button>

        <button className="btn btn-secondary btn-sm" onClick={handleExportBackup} title="Export full offline database as JSON">
          <Download size={14} /> Backup JSON
        </button>

        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept=".json"
          onChange={onFileChange}
        />

        <button className="btn btn-outline btn-sm" onClick={() => fileInputRef.current.click()} title="Restore database from JSON file">
          <Upload size={14} /> Restore
        </button>
      </div>
    </header>
  );
};
