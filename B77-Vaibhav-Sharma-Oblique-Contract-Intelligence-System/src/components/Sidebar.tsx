import React from 'react';
import { 
  Layers, 
  Sparkles, 
  ListOrdered, 
  FileText, 
  GitMerge, 
  FileSpreadsheet, 
  FileCheck2, 
  BookOpen, 
  Settings as SettingsIcon,
  X
} from 'lucide-react';
import { ContractDocument } from '../types/contract';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  contract: ContractDocument | null;
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  contract,
  mobileOpen,
  setMobileOpen
}) => {
  const redCount = contract?.findings.filter(f => f.attention === 'RED').length || 0;
  const amberCount = contract?.findings.filter(f => f.attention === 'AMBER').length || 0;

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Layers },
    { id: 'new-analysis', label: 'New Analysis', icon: Sparkles },
    { id: 'findings', label: 'Findings Matrix', icon: ListOrdered, count: contract?.findings.length },
    { id: 'viewer', label: 'Contract Viewer', icon: FileText },
    { id: 'cross-clause', label: 'Cross-Clause 2nd Pass', icon: GitMerge, badge: 'AI' },
    { id: 'comparison', label: 'Invoice Comparison', icon: FileSpreadsheet },
    { id: 'report', label: 'Audit Report', icon: FileCheck2 },
    { id: 'knowledge', label: 'Compliance Rules', icon: BookOpen },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  const handleNavClick = (tabId: string) => {
    setActiveTab(tabId);
    setMobileOpen(false);
  };

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-[#111827] flex flex-col border-r border-gray-800 text-gray-200
        transition-transform duration-200 ease-in-out
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Brand Header */}
        <div className="p-6 border-b border-gray-800/80">
          <div className="flex items-center justify-between">
            <div 
              className="flex items-center gap-2.5 cursor-pointer"
              onClick={() => handleNavClick('dashboard')}
            >
              <div className="w-7 h-7 bg-blue-600 rounded-sm flex items-center justify-center text-[11px] text-white font-black tracking-tight shadow-sm">
                OBL
              </div>
              <div>
                <h1 className="text-white font-bold text-base tracking-wider leading-none">
                  OBLIQUE
                </h1>
                <p className="text-[9px] text-gray-400 uppercase tracking-widest mt-0.5 font-medium">
                  CONTRACT INTELLIGENCE SYSTEM
                </p>
                <p className="text-[8.5px] text-blue-400 font-semibold tracking-wider uppercase mt-0.5">
                  BY CA VAIBHAV SHARMA
                </p>
              </div>
            </div>

            {/* Mobile close button */}
            <button 
              onClick={() => setMobileOpen(false)}
              className="lg:hidden text-gray-400 hover:text-white p-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* CA Edition Pill */}
          <div className="mt-3 inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-blue-950/80 border border-blue-800/60 text-[10px] font-semibold text-blue-300">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            <span>India CA / Tax Edition</span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                id={`nav-tab-${item.id}`}
                onClick={() => handleNavClick(item.id)}
                className={`
                  w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition cursor-pointer
                  ${isActive 
                    ? 'bg-blue-600 text-white font-semibold shadow-xs' 
                    : 'text-gray-400 hover:text-white hover:bg-gray-800/60'
                  }
                `}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-gray-400'}`} />
                  <span>{item.label}</span>
                </div>

                {item.count !== undefined && item.count > 0 && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                    isActive ? 'bg-blue-700 text-white' : 'bg-gray-800 text-gray-300'
                  }`}>
                    {item.count}
                  </span>
                )}

                {item.badge && (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-900/80 text-purple-300 border border-purple-700/60 font-bold uppercase">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Active Contract Quick Stats in Sidebar */}
        {contract && (
          <div className="p-3 mx-3 mb-3 bg-gray-800/60 rounded-lg border border-gray-700/60 text-[11px] space-y-1.5">
            <div className="text-gray-400 uppercase font-bold text-[9px] tracking-wider">
              Active Contract Risk
            </div>
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 bg-red-950 text-red-300 border border-red-800 rounded font-bold text-[10px]">
                {redCount} High
              </span>
              <span className="px-1.5 py-0.5 bg-amber-950 text-amber-300 border border-amber-800 rounded font-bold text-[10px]">
                {amberCount} Review
              </span>
              <span className="text-gray-400 text-[10px] ml-auto truncate font-mono">
                {contract.commercialTerms.contractValue}
              </span>
            </div>
          </div>
        )}

        {/* System Status Footer */}
        <div className="p-4 border-t border-gray-800">
          <div className="bg-gray-800/90 rounded-lg p-3 border border-gray-700/50">
            <p className="text-[10px] text-gray-400 uppercase font-bold mb-1 tracking-wider">
              System Status
            </p>
            <div className="flex items-center gap-2">
              <div className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </div>
              <span className="text-xs text-gray-300 font-medium">Gemini 2.5 Flash Active</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
