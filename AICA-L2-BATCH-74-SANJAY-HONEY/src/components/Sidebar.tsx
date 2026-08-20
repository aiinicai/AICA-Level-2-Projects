import React from 'react';
import {
  LayoutDashboard,
  Mail,
  Inbox,
  FileSearch,
  Users,
  GitCompare,
  FileText,
  Smartphone,
  CheckCircle2,
  History,
  Settings,
  Sparkles,
  ShieldCheck,
  Zap,
} from 'lucide-react';

import { BriefingSource } from '../types';

export type NavTab =
  | 'dashboard'
  | 'briefing'
  | 'inbox'
  | 'impact'
  | 'clients'
  | 'matching'
  | 'advisories'
  | 'status-studio'
  | 'approval'
  | 'history'
  | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  pendingApprovalsCount: number;
  totalUpdatesCount: number;
  isLiveSystem?: boolean;
  briefingSource?: BriefingSource;
  isDemoMode?: boolean;
  onLoadDemo: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  pendingApprovalsCount,
  totalUpdatesCount,
  isLiveSystem,
  briefingSource = 'DEMO',
  isDemoMode,
  onLoadDemo,
}) => {
  const isLive = isLiveSystem !== undefined ? isLiveSystem : !isDemoMode;

  const statusTitle = isLive
    ? briefingSource === 'GMAIL'
      ? 'LIVE SYSTEM — Gmail Ingested'
      : 'LIVE SYSTEM — Gmail Connected'
    : 'DEMO MODE ACTIVE';

  const statusDescription = isLive
    ? briefingSource === 'GMAIL'
      ? 'CA Intelligence Agent active with Live Gmail Daily Briefing Ingestion.'
      : 'Google OAuth Connected. Ready to search & import daily briefings.'
    : 'CA Intelligence Agent running in Demo Mode with sample regulatory briefing data.';
  const navItems: { id: NavTab; label: string; icon: React.FC<{ className?: string }>; badge?: number | string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'briefing', label: "Today's Briefing", icon: Mail },
    { id: 'inbox', label: 'Update Inbox', icon: Inbox, badge: totalUpdatesCount > 0 ? totalUpdatesCount : undefined },
    { id: 'impact', label: 'Impact Analysis', icon: FileSearch },
    { id: 'clients', label: 'Client Master', icon: Users, badge: '5 Demo' },
    { id: 'matching', label: 'Client Matching', icon: GitCompare },
    { id: 'advisories', label: 'Client Advisories', icon: FileText },
    { id: 'status-studio', label: 'Daily Status Studio', icon: Smartphone, badge: '9:16' },
    { id: 'approval', label: 'Approval Centre', icon: CheckCircle2, badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined },
    { id: 'history', label: 'Audit History', icon: History },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-300 flex flex-col h-screen sticky top-0 z-30 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white font-black text-lg shadow-md shadow-teal-900/40 shrink-0">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div className="overflow-hidden">
          <h1 className="text-base font-black text-white tracking-tight leading-none">
            BUILD PRO <span className="text-teal-400">AI</span>
          </h1>
          <p className="text-[10px] uppercase tracking-widest text-slate-400 font-semibold mt-1">
            CA Intelligence Agent
          </p>
        </div>
      </div>

      {/* Demo Banner Button */}
      <div className="px-3 pt-3 pb-1">
        <button
          onClick={onLoadDemo}
          className="w-full flex items-center justify-between px-3.5 py-2.5 bg-teal-950/40 border border-teal-500/30 rounded-xl text-teal-300 text-xs font-bold hover:bg-teal-900/40 transition-all cursor-pointer group shadow-xs"
        >
          <span className="flex items-center space-x-2">
            <Sparkles className="w-3.5 h-3.5 text-teal-400 group-hover:rotate-12 transition-transform" />
            <span>Load Demo Briefing</span>
          </span>
          <span className="text-[10px] bg-teal-500/20 px-2 py-0.5 rounded-full text-teal-200 font-bold">5 Updates</span>
        </button>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs transition-all cursor-pointer ${
                isActive
                  ? 'bg-teal-600 text-white shadow-md font-bold'
                  : 'text-slate-400 font-medium hover:text-white hover:bg-slate-800/80'
              }`}
            >
              <div className="flex items-center space-x-3 min-w-0">
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span className="truncate">{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                    isActive
                      ? 'bg-teal-800 text-teal-100'
                      : item.id === 'approval'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Footer Status */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/60">
        <div className="bg-teal-900/20 p-3 rounded-xl border border-teal-500/20 space-y-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="flex items-center space-x-1.5 font-bold uppercase text-teal-400 tracking-wider">
              <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              <span>{statusTitle}</span>
            </span>
            <span className="text-slate-500 font-mono text-[10px]">v2.5 CA</span>
          </div>
          <p className="text-[10px] text-slate-400 leading-tight">
            {statusDescription}
          </p>
        </div>
      </div>
    </aside>
  );
};
