import React from 'react';
import { ShieldCheck, Lock, Database, FileText, AlertTriangle, UserCheck } from 'lucide-react';

interface HeaderProps {
  auditorName: string;
  organizationFiduciary: string;
  consentGranted: boolean;
  onOpenConsentModal: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  datasetName?: string;
  datasetHash?: string;
}

export const Header: React.FC<HeaderProps> = ({
  auditorName,
  organizationFiduciary,
  consentGranted,
  onOpenConsentModal,
  activeTab,
  setActiveTab,
  datasetName,
  datasetHash
}) => {
  const navTabs = [
    { id: 'ingest', label: '1. Ingestion & Mapping', icon: Database },
    { id: 'dpdp', label: '2. DPDP Privacy Vault', icon: Lock },
    { id: 'benford', label: '3. Benford Analytics', icon: ShieldCheck },
    { id: 'forensics', label: '4. Forensic Scanner', icon: AlertTriangle },
    { id: 'ledger', label: '5. Audit Trail Ledger', icon: UserCheck },
    { id: 'report', label: '6. Executive Report', icon: FileText }
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-900/95 sticky top-0 z-40 backdrop-blur-md">
      {/* Top Banner */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-brand-600 to-forensic-cyan flex items-center justify-center shadow-lg shadow-brand-500/20">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              Enterprise Forensic Audit &amp; Benford's Law Suite
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/30 font-medium">
                DPDP Act, 2023 Compliant
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Institutional Forensic Accounting &bull; Nigrini Statistical Standards &bull; Air-Gapped Zero-Egress Engine
            </p>
          </div>
        </div>

        {/* Security & Auditor Chips */}
        <div className="flex items-center gap-2">
          {/* Air-gap Badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Air-Gapped (Local)
          </div>

          {/* DPDP Consent Status */}
          <button
            onClick={onOpenConsentModal}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium border transition-all ${
              consentGranted
                ? 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-750'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-300 animate-pulse'
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            {consentGranted ? `Fiduciary: ${organizationFiduciary || 'Declared'}` : 'Action Required: DPDP Consent'}
          </button>
        </div>
      </div>

      {/* Navigation Tab Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex overflow-x-auto no-scrollbar space-x-1 border-t border-slate-800/60 pt-1">
        {navTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold whitespace-nowrap border-b-2 transition-all duration-150 ${
                isActive
                  ? 'border-brand-500 text-white bg-slate-800/50'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/20'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-brand-400' : 'text-slate-500'}`} />
              {tab.label}
            </button>
          );
        })}
      </div>
    </header>
  );
};
