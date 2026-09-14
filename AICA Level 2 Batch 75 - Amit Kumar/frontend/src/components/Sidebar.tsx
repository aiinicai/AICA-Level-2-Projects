import React, { useState } from 'react';
import {
  LayoutDashboard, UserPlus, Upload, Columns, GitMerge, Sliders,
  FileSpreadsheet, FileText, ArrowLeftRight, FileCheck, BookOpen,
  PieChart, ShieldAlert, Download, Users, Settings, ChevronLeft, ChevronRight
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  validationsCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, validationsCount = 0 }) => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('sidebar_collapsed') === 'true';
  });

  const toggleSidebar = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem('sidebar_collapsed', String(newState));
    // Trigger window resize event so canvas/charts recalculate cleanly
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 200);
  };

  const menuItems = [
    { id: 'dashboard', label: '1. Dashboard', icon: LayoutDashboard },
    { id: 'client-setup', label: '2. Client Setup', icon: UserPlus },
    { id: 'upload-center', label: '3. Upload Center', icon: Upload },
    { id: 'split-workbench', label: '4. Split Workbench', icon: Columns, badge: 'Live' },
    { id: 'ledger-mapping', label: '5. Ledger Mapping', icon: GitMerge },
    { id: 'rule-studio', label: '6. Rule Studio', icon: Sliders, badge: 'Rule' },
    { id: 'supporting-schedules', label: '7. Schedules', icon: FileSpreadsheet },
    { id: 'financial-statements', label: '8. Balance Sheet & PL', icon: FileText },
    { id: 'cash-flow', label: '9. AS 3 Cash Flow', icon: ArrowLeftRight, badge: 'AS 3' },
    { id: 'accounting-policies', label: '10. Policies', icon: FileCheck },
    { id: 'notes-accounts', label: '11. Notes to Accounts', icon: BookOpen },
    { id: 'ratio-analysis', label: '12. Ratios', icon: PieChart },
    { id: 'validation-checks', label: '13. Validations', icon: ShieldAlert, count: validationsCount },
    { id: 'export-reports', label: '14. Export Center', icon: Download },
    { id: 'users', label: '15. User Admin', icon: Users, badge: 'Admin' },
    { id: 'settings', label: '16. Settings', icon: Settings },
  ];

  return (
    <aside
      className={`min-h-screen bg-slate-900 text-slate-100 border-r border-slate-800 flex flex-col justify-between shrink-0 transition-all duration-200 ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      <div>
        {/* Header Monogram & Title */}
        <div className="p-4 border-b border-slate-800 flex items-center gap-3 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white font-extrabold text-sm shadow-sm flex items-center justify-center shrink-0">
            FS
          </div>
          {!isCollapsed && (
            <div className="truncate">
              <h2 className="font-black tracking-wider text-white text-xs uppercase truncate">
                FS BUILDER PRO
              </h2>
              <p className="text-[10px] font-mono text-slate-400 truncate">
                IGAAP Schedule III v0.2
              </p>
            </div>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="p-2 space-y-1 overflow-y-auto max-h-[calc(100vh-140px)]">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                title={isCollapsed ? item.label : undefined}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-bold transition-all text-left cursor-pointer ${
                  isActive
                    ? 'bg-blue-900 text-white font-semibold shadow-xs border-l-4 border-blue-500'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 font-medium'
                }`}
              >
                <div className="flex items-center gap-3 truncate">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </div>
                {!isCollapsed && (
                  <div className="flex items-center gap-1">
                    {item.count !== undefined && item.count > 0 && (
                      <span className="text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 px-1.5 py-0.5 rounded-full">
                        {item.count}
                      </span>
                    )}
                    {item.badge && (
                      <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded uppercase ${
                        isActive
                          ? 'bg-blue-800 text-blue-200'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer & Sidebar Collapse Toggle Button */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between">
        {!isCollapsed && (
          <div className="text-[10px] font-mono text-slate-500 truncate">
            FS BUILDER LITE AUDIT SYSTEM
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-md bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors mx-auto"
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
};

