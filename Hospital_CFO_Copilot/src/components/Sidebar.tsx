import React from 'react';
import {
  LayoutDashboard,
  Receipt,
  FileCheck2,
  Tag,
  CreditCard,
  TrendingUp,
  BarChart3,
  Bot,
  UploadCloud,
  FileText,
  Sliders,
  LogOut,
  Building2,
  Shield,
  ChevronRight,
  X,
} from 'lucide-react';
import { UserSession } from '../types';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tabId: string) => void;
  currentUser: UserSession | null;
  onLogout: () => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  restrictedRoles?: string[];
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  currentUser,
  onLogout,
  isOpenMobile,
  onCloseMobile,
}) => {
  const isDeptManager = currentUser?.role === 'Department Manager';

  // Grouped Navigation Sections as specified in Section 1
  const sections: NavSection[] = [
    {
      title: 'Overview',
      items: [
        {
          id: 'dashboard',
          label: 'Finance Control Tower',
          icon: LayoutDashboard,
          restrictedRoles: isDeptManager ? ['Department Manager'] : undefined,
        },
      ],
    },
    {
      title: 'Revenue & Billing',
      items: [
        {
          id: 'revenue-controls',
          label: 'Billing & Revenue Controls',
          icon: Receipt,
        },
        {
          id: 'department-clearance',
          label: 'Departmental Billing Review',
          icon: FileCheck2,
        },
        {
          id: 'tariff-intelligence',
          label: 'Tariff & Rate Review',
          icon: Tag,
        },
      ],
    },
    {
      title: 'Receivables',
      items: [
        {
          id: 'receivables-collections',
          label: 'Receivables & Collections',
          icon: CreditCard,
          restrictedRoles: isDeptManager ? ['Department Manager'] : undefined,
        },
      ],
    },
    {
      title: 'Management',
      items: [
        {
          id: 'financial-performance',
          label: 'Financial Performance',
          icon: TrendingUp,
          restrictedRoles: isDeptManager ? ['Department Manager'] : undefined,
        },
        {
          id: 'budget-vs-actual',
          label: 'Budget vs Actual',
          icon: BarChart3,
          restrictedRoles: isDeptManager ? ['Department Manager'] : undefined,
        },
        {
          id: 'cfo-copilot',
          label: 'CFO Copilot',
          icon: Bot,
        },
      ],
    },
    {
      title: 'Governance',
      items: [
        {
          id: 'data-intelligence',
          label: 'Data Import & Mapping',
          icon: UploadCloud,
          restrictedRoles: isDeptManager ? ['Department Manager'] : undefined,
        },
        {
          id: 'audit-evidence',
          label: 'Audit Trail',
          icon: FileText,
        },
        {
          id: 'control-settings',
          label: 'Control Settings & Rules',
          icon: Sliders,
          restrictedRoles: isDeptManager ? ['Department Manager'] : undefined,
        },
      ],
    },
  ];

  const handleTabClick = (tabId: string) => {
    onSelectTab(tabId);
    if (isOpenMobile) {
      onCloseMobile();
    }
  };

  const isTabActive = (item: NavItem) => {
    if (currentTab === item.id) return true;
    if (item.id === 'dashboard' && (currentTab === 'dashboard' || currentTab === 'overview')) return true;
    if (item.id === 'data-intelligence' && (currentTab === 'data-intelligence' || currentTab === 'data-import' || currentTab === 'data-controls')) return true;
    if (item.id === 'control-settings' && (currentTab === 'control-settings' || currentTab === 'admin' || currentTab === 'administration')) return true;
    if (item.id === 'receivables-collections' && (currentTab === 'receivables-collections' || currentTab === 'ar-working-capital' || currentTab === 'tpa-collections')) return true;
    return false;
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-xs lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar Container: Fixed on Desktop, Drawer on Mobile */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex w-64 flex-col bg-[#0b1329] border-r border-slate-800 text-slate-300 transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Sidebar Brand Header */}
        <div className="flex h-16 shrink-0 items-center justify-between px-5 border-b border-slate-800/80 bg-[#080d1d]">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600/20 border border-teal-500/30 text-teal-400">
              <Building2 className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-white leading-tight">
                Hospital CFO Copilot
              </div>
              <div className="text-[10px] text-teal-400/90 font-medium">
                Financial Control Tower
              </div>
            </div>
          </div>
          {/* Mobile Close Button */}
          <button
            onClick={onCloseMobile}
            className="p-1 rounded-md text-slate-400 hover:text-white lg:hidden cursor-pointer"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Navigation Groups */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5 scrollbar-thin scrollbar-thumb-slate-800">
          {sections.map((section) => {
            const visibleItems = section.items.filter((item) => {
              if (!item.restrictedRoles) return true;
              return !item.restrictedRoles.includes(currentUser?.role || '');
            });

            if (visibleItems.length === 0) return null;

            return (
              <div key={section.title} className="space-y-1">
                <div className="px-2.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  {section.title}
                </div>
                <div className="space-y-0.5">
                  {visibleItems.map((item) => {
                    const active = isTabActive(item);
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => handleTabClick(item.id)}
                        className={`group flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-xs font-medium transition cursor-pointer ${
                          active
                            ? 'bg-teal-500/15 text-teal-300 border-l-2 border-teal-400 font-semibold shadow-xs'
                            : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <Icon
                            className={`h-4 w-4 shrink-0 transition ${
                              active ? 'text-teal-400' : 'text-slate-400 group-hover:text-slate-300'
                            }`}
                          />
                          <span className="truncate">{item.label}</span>
                        </div>
                        {active && (
                          <ChevronRight className="h-3 w-3 text-teal-400/80 shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Pinned User Profile & Logout */}
        <div className="shrink-0 border-t border-slate-800 bg-[#080d1d] p-3">
          {currentUser ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2.5 px-1 py-1">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-800 text-white text-xs font-bold ring-1 ring-teal-500/40">
                  {currentUser.avatarInitials || 'CF'}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-semibold text-white">
                    {currentUser.name}
                  </div>
                  <div className="truncate text-[10px] text-teal-400/90 font-medium">
                    {currentUser.role}
                    {currentUser.department ? ` • ${currentUser.department}` : ''}
                  </div>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-800/40 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5 text-slate-400" />
                <span>Log Out</span>
              </button>
            </div>
          ) : (
            <div className="px-2 py-1 text-center text-xs text-slate-500">
              Authorized Session Only
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
