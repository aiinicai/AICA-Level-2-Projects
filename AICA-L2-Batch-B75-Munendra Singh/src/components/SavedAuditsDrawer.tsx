import React, { useState } from 'react';
import { 
  X, 
  Database, 
  Search, 
  Trash2, 
  FileText, 
  Calendar, 
  ArrowRight, 
  AlertTriangle, 
  CheckCircle2, 
  Download,
  FolderOpen
} from 'lucide-react';
import { AuditReportData } from '../types';
import { getSavedAudits, deleteAuditFromVault } from '../utils/localVault';

interface SavedAuditsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAudit: (report: AuditReportData) => void;
}

export const SavedAuditsDrawer: React.FC<SavedAuditsDrawerProps> = ({
  isOpen,
  onClose,
  onSelectAudit,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [audits, setAudits] = useState<AuditReportData[]>(getSavedAudits());

  if (!isOpen) return null;

  const filteredAudits = audits.filter((a) => {
    const q = searchQuery.toLowerCase();
    return (
      (a.documentTitle && a.documentTitle.toLowerCase().includes(q)) ||
      (a.summary.entityName && a.summary.entityName.toLowerCase().includes(q)) ||
      (a.summary.reportingPeriod && a.summary.reportingPeriod.toLowerCase().includes(q)) ||
      a.id.toLowerCase().includes(q)
    );
  });

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (window.confirm('Delete this audit report from local vault?')) {
      const updated = deleteAuditFromVault(id);
      setAudits(updated);
    }
  };

  const getScoreBadge = (score: string) => {
    if (score === 'High') {
      return (
        <span className="bg-green-700 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase">
          HIGH COMPLIANCE
        </span>
      );
    }
    if (score === 'Moderate') {
      return (
        <span className="bg-orange-500 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase">
          MODERATE RISK
        </span>
      );
    }
    return (
      <span className="bg-red-600 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase">
        NEEDS REVISION
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end animate-fadeIn">
      <div className="bg-[#F9F9F7] w-full max-w-xl h-full shadow-dense flex flex-col border-l-2 border-[#141414] animate-slideLeft">
        {/* Top Header */}
        <div className="bg-[#141414] text-white p-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 bg-[#00FF00] flex items-center justify-center text-[#141414] font-bold">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm uppercase tracking-tight font-sans">
                Local Audit Vault & History
              </h3>
              <p className="text-[10px] text-neutral-400 font-mono">
                {audits.length} AUDITS STORED ON THIS DEVICE
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Toolbar */}
        <div className="p-3.5 bg-white border-b border-[#141414] flex items-center space-x-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by entity name, period, or audit ID..."
              className="w-full bg-[#F4F4F2] border border-neutral-300 pl-8 pr-3 py-1.5 text-xs text-[#141414] font-mono focus:outline-none focus:border-[#141414]"
            />
          </div>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="px-2 py-1 text-[10px] font-mono uppercase bg-neutral-200 hover:bg-neutral-300"
            >
              Clear
            </button>
          )}
        </div>

        {/* Audit List Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filteredAudits.length === 0 ? (
            <div className="text-center py-12 px-4 border-2 border-dashed border-neutral-300 bg-white">
              <FolderOpen className="w-8 h-8 text-neutral-400 mx-auto mb-2" />
              <h4 className="font-bold text-xs font-mono uppercase text-[#141414]">
                No Saved Audits Found
              </h4>
              <p className="text-[11px] text-neutral-500 font-serif italic mt-1 max-w-xs mx-auto">
                {searchQuery
                  ? 'No local audit records matched your search query.'
                  : 'Run an audit using sample statements or uploaded files to automatically save engagement dossiers here.'}
              </p>
            </div>
          ) : (
            filteredAudits.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  onSelectAudit(item);
                  onClose();
                }}
                className="bg-white border border-[#141414] p-3.5 hover:shadow-dense-sm transition cursor-pointer group flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div>
                      <h4 className="font-bold text-xs text-[#141414] group-hover:text-black uppercase tracking-tight">
                        {item.summary.entityName || item.documentTitle}
                      </h4>
                      <p className="text-[10px] text-neutral-500 font-mono">
                        {item.summary.reportingPeriod || 'Annual Audit'} • {item.summary.frameworkIdentified || 'Ind AS'}
                      </p>
                    </div>
                    {getScoreBadge(item.summary.overallComplianceScore)}
                  </div>

                  <div className="grid grid-cols-3 gap-2 my-2 py-1.5 px-2 bg-[#F4F4F2] border border-neutral-200 text-[10px] font-mono">
                    <div>
                      <span className="text-neutral-500 block text-[8px] uppercase">Discrepancies</span>
                      <span className="font-bold text-[#141414]">{item.summary.totalDiscrepancies}</span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block text-[8px] uppercase">Missing Stds</span>
                      <span className="font-bold text-red-700">{item.summary.missingDisclosuresCount}</span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block text-[8px] uppercase">Casting Gaps</span>
                      <span className="font-bold text-orange-700">{item.summary.numericalMismatchesCount}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-neutral-200 mt-1">
                  <div className="flex items-center space-x-1.5 text-[9px] font-mono text-neutral-500">
                    <Calendar className="w-3 h-3" />
                    <span>{new Date(item.timestamp).toLocaleString('en-IN')}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, item.id)}
                      className="p-1 text-neutral-400 hover:text-red-700 transition"
                      title="Delete from local vault"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                    <span className="inline-flex items-center space-x-1 text-[10px] font-mono font-bold uppercase text-[#141414] group-hover:underline">
                      <span>Open Dossier</span>
                      <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#F4F4F2] border-t border-[#141414] text-center">
          <p className="text-[10px] font-mono text-neutral-600 uppercase">
            ALL AUDIT DOSSIERS ARE SECURELY PRESERVED IN YOUR LOCAL STORAGE VAULT
          </p>
        </div>
      </div>
    </div>
  );
};
