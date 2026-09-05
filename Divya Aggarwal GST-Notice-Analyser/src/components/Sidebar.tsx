import React from 'react';
import {
  LayoutDashboard,
  Columns,
  SearchCode,
  Calculator,
  ListTodo,
  FileCheck2,
  CalendarClock,
  HelpCircle,
  MessageSquare,
} from 'lucide-react';
import { FEATURES } from '../config';

export type ActiveTab =
  | 'dashboard'
  | 'split_view'
  | 'figure_source'
  | 'reconciliation'
  | 'tracker'
  | 'reply_gen'
  | 'deadlines'
  | 'client_discussion'
  | 'setup_guide';

interface SidebarProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  caseCount: number;
  issueCount: number;
  pendingDocCount: number;
  urgentDeadlineCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  caseCount,
  issueCount,
  pendingDocCount,
  urgentDeadlineCount,
}) => {
  const navItems = [
    {
      id: 'dashboard' as ActiveTab,
      label: 'Cases Overview',
      icon: LayoutDashboard,
      badge: caseCount > 0 ? `${caseCount}` : undefined,
      badgeColor: 'bg-gray-100 text-gray-700',
    },
    {
      id: 'split_view' as ActiveTab,
      label: 'Side-by-Side Analysis',
      icon: Columns,
      badge: issueCount > 0 ? `${issueCount} issues` : undefined,
      badgeColor: 'bg-indigo-100 text-indigo-800 font-bold',
    },
    ...(FEATURES.figureSource ? [{
      id: 'figure_source' as ActiveTab,
      label: 'Department Figure Source',
      icon: SearchCode,
      badge: undefined,
      badgeColor: '',
    }] : []),
    ...(FEATURES.reconciliation ? [{
      id: 'reconciliation' as ActiveTab,
      label: 'Reconciliations',
      icon: Calculator,
      badge: undefined,
      badgeColor: '',
    }] : []),
    {
      id: 'tracker' as ActiveTab,
      label: 'Document Tracker',
      icon: ListTodo,
      badge: pendingDocCount > 0 ? `${pendingDocCount} pending` : undefined,
      badgeColor: 'bg-amber-100 text-amber-800',
    },
    {
      id: 'reply_gen' as ActiveTab,
      label: 'Reply & Email Studio',
      icon: FileCheck2,
      badge: undefined,
      badgeColor: '',
    },
    {
      id: 'deadlines' as ActiveTab,
      label: 'Statutory Deadlines',
      icon: CalendarClock,
      badge: urgentDeadlineCount > 0 ? `${urgentDeadlineCount} Urgent` : undefined,
      badgeColor: 'bg-red-100 text-red-700 font-bold',
    },
    {
      id: 'client_discussion' as ActiveTab,
      label: 'Client Discussion',
      icon: MessageSquare,
      badge: undefined,
      badgeColor: 'bg-teal-100 text-teal-700',
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col justify-between select-none shrink-0 h-full">
      <div className="p-3 space-y-1">
        <div className="px-3 py-1.5 text-[10px] font-bold tracking-wider text-gray-400 uppercase">
          CA Workstation Navigation
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? 'bg-[#E0E7FF] text-[#312E81] font-bold shadow-2xs'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`w-4 h-4 ${isActive ? 'text-[#4338CA]' : 'text-gray-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded-md ${item.badgeColor}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="p-3 border-t border-gray-100 bg-[#F9FAFB]">
        <button
          onClick={() => onSelectTab('setup_guide')}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            activeTab === 'setup_guide' ? 'bg-[#E0E7FF] text-[#312E81] font-bold' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <HelpCircle className="w-4 h-4 text-[#4338CA]" />
          <span>GST Law & Notice Guide</span>
        </button>

        <div className="mt-2 text-[10px] text-gray-400 px-3">
          Version 3.0 · Cloud workspace
        </div>
      </div>
    </aside>
  );
};
