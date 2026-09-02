import React from 'react';
import {
  Building2,
  ChevronDown,
  Download,
  CalendarCheck,
  ShieldCheck,
  ArrowUpRight,
  ExternalLink,
  Sparkles,
} from 'lucide-react';
import { ClientProfile } from '../../types';

interface NavbarProps {
  currentClient?: ClientProfile;
  client?: ClientProfile;
  allClients?: ClientProfile[];
  onSelectClient?: (clientId: string) => void;
  onOpenClientManager?: () => void;
  onOpenClientSelector?: () => void;
  onOpenWorkflow?: () => void;
  onOpenPrivacyShield?: () => void;
  onOpenAskCfo?: () => void;
  onQuickExport?: () => void;
  onExportReport?: () => void;
  onShowLanding?: () => void;
  firmName?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentClient,
  client,
  allClients = [],
  onSelectClient,
  onOpenClientManager,
  onOpenClientSelector,
  onOpenWorkflow,
  onOpenPrivacyShield,
  onOpenAskCfo,
  onQuickExport,
  onExportReport,
  onShowLanding,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const activeClient = currentClient || client || {
    id: 'demo-med',
    name: 'ABC Medical Group',
    industryName: 'Healthcare & Clinical Services',
    privacyMode: 'strict',
  } as ClientProfile;

  const handleExport = onExportReport || onQuickExport || (() => {});
  const handleClientModal = onOpenClientSelector || onOpenClientManager || (() => {});

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-8 flex items-center justify-between z-30 shrink-0">
      {/* Left: Brand Identity & Active Client Badge */}
      <div className="flex items-center gap-4">
        {/* Clickable Brand Logo */}
        <button
          onClick={onShowLanding}
          title="Return to Firm Landing Page"
          className="flex items-center gap-2.5 text-left group cursor-pointer focus:outline-hidden"
        >
          <div className="w-8 h-8 rounded-md bg-[#0F172A] text-white font-bold flex items-center justify-center text-xs shadow-xs group-hover:bg-slate-800 transition-colors">
            CFO
          </div>
          <div>
            <div className="flex items-center gap-1.5 leading-none">
              <span className="font-bold text-sm text-slate-900 tracking-tight">CFO Intelligence</span>
              <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-sky-100 text-sky-800 border border-sky-200">
                FP&A
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium truncate mt-0.5">
              Curated by <span className="font-semibold text-slate-600">{firmName}</span>
            </p>
          </div>
        </button>

        {/* Separator */}
        <div className="hidden md:block h-6 w-[1px] bg-slate-200"></div>

        {/* Geometric Client Selector Badge */}
        <div
          onClick={handleClientModal}
          className="bg-slate-100/90 hover:bg-slate-200/80 border border-slate-200 rounded-md px-3 py-1.5 flex items-center gap-2 cursor-pointer transition-colors"
          title="Click to Switch Client Profile or Onboard New Client"
        >
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Client</span>
          <span className="text-xs font-semibold text-slate-900 truncate max-w-[140px] sm:max-w-[200px]">
            {activeClient.name}
          </span>
          <span className="text-slate-300">|</span>
          <span className="hidden sm:inline text-xs font-medium text-slate-500 italic truncate max-w-[140px]">
            {activeClient.industryName}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-0.5 shrink-0" />
        </div>

        {/* Privacy Shield Pill */}
        <div
          onClick={onOpenPrivacyShield}
          className="hidden lg:inline-flex pill pill-info cursor-pointer hover:bg-sky-100 transition-colors"
          title="PII Redaction Shield Active"
        >
          <ShieldCheck className="w-3 h-3 text-sky-600 mr-0.5" />
          <span>Standard Privacy Mode</span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2.5">
        {/* Ask Your CFO AI Button */}
        {onOpenAskCfo && (
          <button
            onClick={onOpenAskCfo}
            className="inline-flex items-center gap-1.5 text-xs font-bold bg-[#0F172A] hover:bg-slate-800 text-sky-400 border border-slate-700 px-3 py-1.5 rounded-md shadow-xs transition-colors cursor-pointer"
            title="Ask Your Virtual CFO AI"
          >
            <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            <span>Ask CFO</span>
          </button>
        )}

        {/* Monthly Workflow Checklist */}
        {onOpenWorkflow && (
          <button
            onClick={onOpenWorkflow}
            className="hidden sm:inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 border border-slate-200 px-3 py-1.5 rounded-md hover:bg-slate-50 transition-colors cursor-pointer"
          >
            <CalendarCheck className="w-3.5 h-3.5 text-sky-600" />
            <span>Monthly Checklist</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          </button>
        )}

        {/* Export Pack */}
        <button
          onClick={handleExport}
          className="inline-flex items-center gap-1.5 text-xs font-bold bg-sky-600 hover:bg-sky-700 text-white px-3.5 py-1.5 rounded-md shadow-xs shadow-sky-200 transition-all cursor-pointer"
        >
          <Download className="w-3.5 h-3.5 text-sky-200" />
          <span>Export Pack</span>
        </button>
      </div>
    </header>
  );
};

