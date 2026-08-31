import React, { useState, useRef, useEffect } from 'react';
import { 
  ShieldCheck, 
  LayoutDashboard, 
  Layers, 
  Sparkles, 
  QrCode, 
  AlertTriangle, 
  FileText, 
  ClipboardCheck, 
  Workflow, 
  Sparkle,
  BookOpen,
  HelpCircle,
  Building2,
  ChevronDown,
  Plus,
  FileSpreadsheet
} from 'lucide-react';
import { AssetReliabilityScore, Company } from '../types';

export type NavTab = 
  | 'control-tower'
  | 'register'
  | 'capex-review'
  | 'physical-verification'
  | 'risk-radar'
  | 'exceptions'
  | 'policy'
  | 'audit-readiness'
  | 'data-studio'
  | 'user-manual';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  reliabilityScore: AssetReliabilityScore;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  setCurrencyMode: (mode: 'Lakhs' | 'Crores' | 'Full') => void;
  onOpenDemoSpotlight?: () => void;
  openDemoShowcase?: () => void;
  onOpenQuickTour?: () => void;
  openRiskCount?: number;
  activeCompany?: Company;
  allCompanies?: Company[];
  onSwitchCompany?: (companyId: string) => void;
  onOpenCreateCompanyModal?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  reliabilityScore,
  currencyMode,
  setCurrencyMode,
  onOpenDemoSpotlight,
  openDemoShowcase,
  onOpenQuickTour,
  openRiskCount = 4,
  activeCompany,
  allCompanies = [],
  onSwitchCompany,
  onOpenCreateCompanyModal
}) => {
  const [isCompanyMenuOpen, setIsCompanyMenuOpen] = useState(false);
  const companyMenuRef = useRef<HTMLDivElement>(null);
  const handleSpotlight = onOpenDemoSpotlight || openDemoShowcase || (() => {});

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (companyMenuRef.current && !companyMenuRef.current.contains(event.target as Node)) {
        setIsCompanyMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const tabs: { id: NavTab; label: string; icon: any; badge?: number; highlight?: boolean }[] = [
    { id: 'control-tower', label: 'Control Tower', icon: LayoutDashboard },
    { id: 'data-studio', label: 'Data Ingestion & Entities', icon: FileSpreadsheet, highlight: true },
    { id: 'register', label: 'Asset Register', icon: Layers },
    { id: 'capex-review', label: 'AI Capex Review', icon: Sparkles },
    { id: 'physical-verification', label: 'Verification Ops', icon: QrCode },
    { id: 'risk-radar', label: 'Risk Radar', icon: AlertTriangle, badge: openRiskCount },
    { id: 'exceptions', label: 'Exceptions Workflow', icon: Workflow },
    { id: 'policy', label: 'Policy & Compliance', icon: FileText },
    { id: 'audit-readiness', label: 'Audit Readiness', icon: ClipboardCheck },
    { id: 'user-manual', label: 'User Manual', icon: BookOpen }
  ];

  return (
    <header className="bg-[#0F172A] border-b border-slate-700/80 sticky top-0 z-40 text-white shadow-md">
      {/* Top Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-3">
          
          {/* Brand & Logo */}
          <div className="flex items-center space-x-3 cursor-pointer shrink-0" onClick={() => setActiveTab('control-tower')}>
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center shadow-inner">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold tracking-tight text-blue-400">
                  AssetTrust <span className="text-white">AI</span>
                </h1>
                <span className="bg-blue-500/10 text-blue-300 text-[10px] font-semibold px-2 py-0.5 rounded border border-blue-500/20 uppercase tracking-wider hidden sm:inline-block">
                  Enterprise Governance
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-normal hidden sm:block">Fixed Asset Subledger & Multi-Entity Ingestion</p>
            </div>
          </div>

          {/* Company Selector Dropdown */}
          {activeCompany && (
            <div className="relative shrink-0" ref={companyMenuRef}>
              <button
                onClick={() => setIsCompanyMenuOpen(!isCompanyMenuOpen)}
                className="flex items-center space-x-2.5 px-3 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-750 border border-slate-700 text-left transition-all max-w-[220px] sm:max-w-[280px]"
              >
                <div className={`w-6 h-6 rounded-lg bg-linear-to-br ${activeCompany.logoColor || 'from-blue-600 to-indigo-700'} flex items-center justify-center text-white text-[10px] font-bold shrink-0`}>
                  {activeCompany.shortCode}
                </div>
                <div className="truncate">
                  <span className="block text-xs font-bold text-slate-200 truncate leading-tight">
                    {activeCompany.name}
                  </span>
                  <span className="block text-[10px] text-slate-400 truncate">
                    {activeCompany.industry.split('&')[0].trim()}
                  </span>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
              </button>

              {/* Company Dropdown Menu */}
              {isCompanyMenuOpen && (
                <div className="absolute left-0 mt-2 w-72 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div className="px-3 py-2 border-b border-slate-800">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Select Corporate Entity
                    </span>
                  </div>

                  <div className="py-1 max-h-56 overflow-y-auto space-y-1">
                    {allCompanies.map((comp) => {
                      const isSelected = comp.id === activeCompany.id;
                      return (
                        <button
                          key={comp.id}
                          onClick={() => {
                            if (onSwitchCompany) onSwitchCompany(comp.id);
                            setIsCompanyMenuOpen(false);
                          }}
                          className={`w-full text-left px-3 py-2 rounded-xl flex items-center space-x-2.5 transition-all text-xs ${
                            isSelected
                              ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30 font-semibold'
                              : 'text-slate-300 hover:bg-slate-800'
                          }`}
                        >
                          <div className={`w-5 h-5 rounded-md bg-linear-to-br ${comp.logoColor || 'from-blue-600 to-indigo-700'} flex items-center justify-center text-white text-[9px] font-bold shrink-0`}>
                            {comp.shortCode}
                          </div>
                          <div className="truncate flex-1">
                            <span className="block truncate">{comp.name}</span>
                            <span className="text-[10px] text-slate-500 truncate block font-mono">{comp.cin}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between px-1">
                    <button
                      onClick={() => {
                        setIsCompanyMenuOpen(false);
                        if (onOpenCreateCompanyModal) onOpenCreateCompanyModal();
                      }}
                      className="w-full py-1.5 px-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center justify-center space-x-1.5 transition-all shadow-xs"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Create New Company</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Center Actions & Demo Badge */}
          <div className="hidden lg:flex items-center space-x-2.5">
            <button
              id="quick-tour-btn"
              onClick={onOpenQuickTour}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 transition-all text-xs font-medium shadow-xs"
            >
              <HelpCircle className="w-3.5 h-3.5 text-blue-400" />
              <span>Quick Tour</span>
            </button>

            <button
              id="demo-showcase-btn"
              onClick={handleSpotlight}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-blue-600/15 border border-blue-500/30 text-blue-200 hover:bg-blue-600/25 transition-all text-xs font-medium shadow-xs"
            >
              <Sparkle className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
              <span>₹48.5L CNC Demo</span>
            </button>

            {/* Currency Unit Toggle */}
            <div className="bg-slate-800 rounded-lg p-0.5 border border-slate-700 flex items-center text-xs">
              {(['Lakhs', 'Crores', 'Full'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setCurrencyMode(mode)}
                  className={`px-2 py-1 rounded-md text-xs font-medium transition-all ${
                    currencyMode === mode
                      ? 'bg-slate-700 text-blue-300 shadow-xs'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {mode === 'Lakhs' ? '₹ Lakhs' : mode === 'Crores' ? '₹ Cr' : '₹ Full'}
                </button>
              ))}
            </div>
          </div>

          {/* Reliability Score Pill & System Health */}
          <div className="flex items-center space-x-3 shrink-0">
            <div 
              onClick={() => setActiveTab('control-tower')}
              className="cursor-pointer flex items-center space-x-2.5 bg-slate-800 hover:bg-slate-750 border border-slate-700 px-3 py-1.5 rounded-xl transition-all shadow-xs"
              title="Asset Reliability Score: Click for Driver Breakdown"
            >
              <div className="flex flex-col text-right hidden sm:flex">
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Reliability</span>
                <span className="text-xs font-bold text-slate-200">{reliabilityScore.grade}</span>
              </div>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
                reliabilityScore.totalScore >= 80 
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40'
                  : reliabilityScore.totalScore >= 65
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
              }`}>
                {reliabilityScore.totalScore}
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 overflow-x-auto scrollbar-none py-1.5 border-t border-slate-800">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`nav-tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-blue-600/25 text-blue-300 border border-blue-500/40 font-bold shadow-2xs'
                    : tab.highlight
                    ? 'text-purple-300 bg-purple-950/40 border border-purple-800/40 hover:bg-purple-900/50'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-400' : tab.highlight ? 'text-purple-400' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    isActive ? 'bg-rose-500 text-white' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  }`}>
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};


