import React from 'react';
import {
  LayoutDashboard,
  Tag,
  FileSpreadsheet,
  Layers,
  Printer,
  Building2,
  Sliders,
  History,
  Users,
  Settings,
  Database
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export type TabType =
  | 'dashboard'
  | 'generate'
  | 'bulk'
  | 'register'
  | 'printing'
  | 'companies'
  | 'templates'
  | 'audit'
  | 'users'
  | 'settings';

interface SidebarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const { isAdmin } = useAuth();

  const navSections = [
    {
      title: 'CORE OPERATIONS',
      items: [
        { id: 'dashboard' as TabType, label: 'Dashboard', icon: LayoutDashboard },
        { id: 'generate' as TabType, label: 'Generate Asset Tag', icon: Tag },
        { id: 'bulk' as TabType, label: 'Bulk Excel Upload', icon: FileSpreadsheet },
        { id: 'register' as TabType, label: 'Asset Register & History', icon: Layers },
      ],
    },
    {
      title: 'PRINTING & HARDWARE',
      items: [
        { id: 'printing' as TabType, label: 'Sheet & Label Printing', icon: Printer },
        { id: 'templates' as TabType, label: 'Tag Templates & Sizes', icon: Sliders },
      ],
    },
    {
      title: 'ADMINISTRATION',
      items: [
        { id: 'companies' as TabType, label: 'Company Management', icon: Building2 },
        { id: 'audit' as TabType, label: 'Audit Trail & Logs', icon: History },
        ...(isAdmin
          ? [
              { id: 'users' as TabType, label: 'User Management', icon: Users },
              { id: 'settings' as TabType, label: 'System Backup & Settings', icon: Database },
            ]
          : []),
      ],
    },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-300 flex flex-col justify-between py-5 px-3 min-h-[calc(100vh-4rem)] select-none">
      <nav className="space-y-6">
        {navSections.map((sec, sIdx) => (
          <div key={sIdx}>
            <div className="text-[10px] font-bold tracking-wider text-slate-500 uppercase px-3 mb-2">
              {sec.title}
            </div>
            <div className="space-y-1">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer Info */}
      <div className="px-3 pt-4 border-t border-slate-800 text-[11px] text-slate-500">
        <div className="font-semibold text-slate-400">Asset Tagging Suite</div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Database WAL Engine Online</span>
        </div>
      </div>
    </aside>
  );
};
