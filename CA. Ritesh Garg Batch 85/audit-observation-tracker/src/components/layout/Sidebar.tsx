import React from 'react';
import { 
  LayoutDashboard, 
  Briefcase, 
  FileText, 
  FileSpreadsheet, 
  CheckSquare,
  Settings, 
  ShieldAlert,
  ChevronRight
} from 'lucide-react';

export type NavView = 'dashboard' | 'engagements' | 'observations' | 'checklists' | 'reports' | 'settings';
export type TabType = NavView;

interface SidebarProps {
  currentView: NavView;
  onNavigate: (view: NavView) => void;
  engagementsCount: number;
  observationsCount: number;
  auditTypesCount?: number;
  checklistItemsCount?: number;
  openObservationsCount?: number;
  partnerName?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onNavigate,
  engagementsCount,
  observationsCount,
  auditTypesCount,
  checklistItemsCount,
  openObservationsCount,
  partnerName = 'CA Ritesh Garg, FCA',
}) => {
  const navItems = [
    {
      id: 'dashboard' as NavView,
      label: 'Dashboard',
      icon: LayoutDashboard,
      badge: null,
      description: 'Audit overview & KPIs',
    },
    {
      id: 'engagements' as NavView,
      label: 'Engagements',
      icon: Briefcase,
      badge: engagementsCount,
      description: 'Client audit assignments',
    },
    {
      id: 'observations' as NavView,
      label: 'Observations',
      icon: FileText,
      badge: observationsCount,
      subBadge: openObservationsCount && openObservationsCount > 0 ? `${openObservationsCount} Open` : null,
      description: 'Observation log & tracking',
    },
    {
      id: 'checklists' as NavView,
      label: 'Checklists & Templates',
      icon: CheckSquare,
      badge: checklistItemsCount ?? null,
      description: 'Audit procedures & Excel templates',
    },
    {
      id: 'reports' as NavView,
      label: 'Reports & Exports',
      icon: FileSpreadsheet,
      badge: null,
      description: 'PDF, Word & Excel generator',
    },
    {
      id: 'settings' as NavView,
      label: 'Settings & Masters',
      icon: Settings,
      badge: auditTypesCount ?? null,
      description: 'Audit types & firm profile',
    },
  ];

  return (
    <aside id="main-sidebar" className="w-64 shrink-0 hidden md:block">
      <div className="sticky top-20 bg-white border border-stone-200 rounded-2xl p-4 shadow-sm">
        <div className="px-3 py-1.5 text-xs font-semibold text-stone-400 uppercase tracking-wider">
          Navigation
        </div>
        <nav className="space-y-1.5 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                id={`sidebar-nav-${item.id}`}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-left text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-[#5A5A40] text-white shadow-xs'
                    : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon
                    className={`w-4 h-4 shrink-0 ${
                      isActive ? 'text-amber-300' : 'text-stone-400'
                    }`}
                  />
                  <div className="truncate">
                    <div className="leading-tight">{item.label}</div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  {item.subBadge && !isActive && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-rose-100 text-rose-700 font-bold uppercase">
                      {item.subBadge}
                    </span>
                  )}
                  {item.badge !== null && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-md font-semibold ${
                        isActive
                          ? 'bg-[#474732] text-stone-200'
                          : 'bg-stone-100 text-stone-600'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                  {isActive && <ChevronRight className="w-3.5 h-3.5 text-stone-300" />}
                </div>
              </button>
            );
          })}
        </nav>

        {/* Audit Practice Quick Help Tip */}
        <div className="mt-5 pt-4 border-t border-stone-100 px-1">
          <div className="p-3 bg-[#F5F2ED] rounded-xl border border-[#DED9D0]">
            <div className="flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-[#5A5A40] shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-stone-800">CA Audit Protocol</p>
                <p className="text-[11px] text-stone-600 leading-relaxed mt-0.5">
                  Record discussion dates and management feedback before report sign-off.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Logged in User Bar */}
        <div className="mt-4 pt-3 border-t border-stone-100 px-1 text-xs text-stone-500 flex items-center justify-between">
          <span className="truncate">Logged in: <strong className="text-stone-700 font-semibold">{partnerName}</strong></span>
          <span className="text-[10px] bg-stone-100 text-stone-600 px-1.5 py-0.5 rounded-md border border-stone-200">Partner</span>
        </div>
      </div>
    </aside>
  );
};
