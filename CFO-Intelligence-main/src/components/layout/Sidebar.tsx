import React from 'react';
import {
  LayoutDashboard,
  FileText,
  TrendingUp,
  SlidersHorizontal,
  Target,
  Scale,
  ShieldCheck,
  UploadCloud,
  CheckCircle2,
  Database,
  History,
  Settings,
  PieChart,
} from 'lucide-react';
import { NavigationTab } from '../../types';

interface SidebarProps {
  activeTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  dataQualityScore?: number;
  firmName?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  dataQualityScore = 96,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const navSections = [
    {
      heading: 'Executive Intelligence',
      items: [
        { id: 'executive_summary' as NavigationTab, label: 'Executive Summary', icon: LayoutDashboard },
        { id: 'financial_statements' as NavigationTab, label: 'Financial Statements', icon: FileText },
        { id: 'kpi_benchmarks' as NavigationTab, label: 'KPIs & Benchmarks', icon: Target },
      ],
    },
    {
      heading: 'FP&A & Strategic Modeling',
      items: [
        { id: 'forecasting' as NavigationTab, label: '12-Month Forecast', icon: TrendingUp },
        { id: 'scenarios' as NavigationTab, label: 'What-If & Scenarios', icon: SlidersHorizontal },
        { id: 'breakeven' as NavigationTab, label: 'Break-Even Calculator', icon: Scale },
        { id: 'budget_vs_actual' as NavigationTab, label: 'Budget vs Actual', icon: PieChart },
      ],
    },
    {
      heading: 'Data Integrity & Privacy',
      items: [
        {
          id: 'data_quality' as NavigationTab,
          label: 'Data Quality Engine',
          icon: CheckCircle2,
          badge: `${dataQualityScore}%`,
          badgeClass: dataQualityScore >= 90 ? 'pill pill-success' : 'pill pill-warning',
        },
        {
          id: 'privacy_shield' as NavigationTab,
          label: 'Privacy Shield',
          icon: ShieldCheck,
          badge: 'Active',
          badgeClass: 'pill pill-info',
        },
        { id: 'data_import' as NavigationTab, label: 'Data Import & Files', icon: UploadCloud },
      ],
    },
    {
      heading: 'Advisory Deliverables',
      items: [
        { id: 'cfo_pack' as NavigationTab, label: 'CFO Report Pack', icon: FileText, highlight: true },
        { id: 'integrations' as NavigationTab, label: 'Accounting Connectors', icon: Database },
        { id: 'audit_trail' as NavigationTab, label: 'Audit Trail', icon: History },
        { id: 'settings' as NavigationTab, label: 'Firm Settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-[230px] bg-[#0F172A] text-slate-300 flex flex-col shrink-0 border-r border-slate-800/80 min-h-screen">
      {/* Brand Header */}
      <div className="p-5 pb-3 border-b border-slate-800/70">
        <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
          <span>CFO</span>
          <span className="text-sky-400">Intelligence</span>
        </h1>
        <p className="text-[10px] uppercase tracking-widest text-slate-400 mt-0.5 font-semibold">
          FP&A Engine v4.0
        </p>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 py-3 overflow-y-auto space-y-4">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-0.5">
            <div className="px-5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              {section.heading}
            </div>
            <nav className="mt-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    className={`w-full flex items-center justify-between px-5 py-2.5 text-[13px] font-medium transition-colors cursor-pointer text-left ${
                      isActive
                        ? 'bg-[#1E293B] text-white border-l-[3px] border-sky-400 font-semibold'
                        : item.highlight
                        ? 'text-sky-300 hover:bg-slate-800/80 hover:text-white border-l-[3px] border-transparent font-medium'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-[3px] border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <Icon
                        className={`w-4 h-4 shrink-0 ${
                          isActive ? 'text-sky-400' : item.highlight ? 'text-sky-400' : 'text-slate-400'
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className={`${item.badgeClass} text-[10px] py-0.5 px-1.5 shrink-0`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Sidebar Footer Partner Profile */}
      <div className="p-4 border-t border-slate-800/80 bg-[#0B1120]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-sky-500 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-xs">
            JD
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-semibold text-white truncate">Jasleen Daswal</p>
            <p className="text-[10px] text-slate-400 truncate">Lead Principal • {firmName}</p>
          </div>
        </div>
      </div>
    </aside>
  );
};

