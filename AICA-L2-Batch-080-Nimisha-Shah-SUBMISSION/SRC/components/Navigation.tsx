import React from "react";
import {
  LayoutDashboard,
  TrendingUp,
  ShieldAlert,
  PieChart,
  BarChart3,
  Users2,
  AlertTriangle,
  TableProperties,
  FileCheck2,
  Layers,
  Clock,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export type NavTabId =
  | "executive"
  | "profitability"
  | "solvency"
  | "growth"
  | "valuation"
  | "working_capital"
  | "peer_benchmark"
  | "red_flags"
  | "explorer"
  | "data_quality"
  | "admin";

interface NavigationProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  redFlagCount: number;
  companyCount: number;
  dataQualityScore?: number;
}

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onSelectTab,
  redFlagCount,
  companyCount,
  dataQualityScore = 99.4,
}) => {
  const { isAdmin } = useAuth();

  const navGroups = [
    {
      groupName: "EXECUTIVE SUITE",
      items: [
        { id: "executive" as NavTabId, label: "Executive Dashboard", icon: LayoutDashboard },
        {
          id: "red_flags" as NavTabId,
          label: "Risk & Red Flag Audit",
          icon: AlertTriangle,
          badge: redFlagCount > 0 ? `${redFlagCount}` : undefined,
          badgeColor: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
        },
      ],
    },
    {
      groupName: "FINANCIAL STATEMENTS",
      items: [
        { id: "profitability" as NavTabId, label: "P&L & Waterfall Bridge", icon: TrendingUp },
        { id: "solvency" as NavTabId, label: "Solvency & Capital Structure", icon: ShieldAlert },
        { id: "growth" as NavTabId, label: "Growth & Operating Scissors", icon: BarChart3 },
        { id: "valuation" as NavTabId, label: "Valuation & Multiples", icon: PieChart },
        {
          id: "working_capital" as NavTabId,
          label: "Working Capital & Cash Flow",
          icon: Clock,
          badge: "Simulator",
          badgeColor: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
        },
      ],
    },
    {
      groupName: "CROSS-COMPANY ANALYTICS",
      items: [
        {
          id: "peer_benchmark" as NavTabId,
          label: "Industry & Peer Benchmark",
          icon: Users2,
          badge: "25+ Sectors",
          badgeColor: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
        },
        {
          id: "explorer" as NavTabId,
          label: "Universe Explorer",
          icon: TableProperties,
          badge: `${companyCount.toLocaleString()}`,
          badgeColor: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
        },
        {
          id: "data_quality" as NavTabId,
          label: "Data Schema & Quality",
          icon: FileCheck2,
          badge: `${dataQualityScore}%`,
          badgeColor: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
        },
      ],
    },
    ...(isAdmin ? [
      {
        groupName: "ADMINISTRATION",
        items: [
          {
            id: "admin" as NavTabId,
            label: "Admin Console",
            icon: ShieldCheck,
            badge: "Admin",
            badgeColor: "bg-purple-500/20 text-purple-300 border border-purple-500/30",
          },
        ],
      },
    ] : []),
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col h-screen border-r border-slate-800 shrink-0 font-sans select-none">
      <div className="h-16 flex items-center px-4 border-b border-slate-800 bg-slate-950/40">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-white tracking-tight text-sm">CFO Intelligence</span>
              <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
                PRO
              </span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium">Enterprise Analytics Engine</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
        {navGroups.map((group) => (
          <div key={group.groupName}>
            <div className="px-2 mb-1 text-[10px] font-bold text-slate-400 tracking-wider uppercase">
              {group.groupName}
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    className={`w-full flex items-center justify-between px-2.5 py-2 rounded text-xs font-medium transition-colors text-left cursor-pointer ${
                      isActive
                        ? "bg-emerald-600 text-white font-semibold shadow-xs"
                        : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-white" : "text-slate-400"}`} />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ml-1.5 ${
                          isActive
                            ? "bg-white/20 text-white"
                            : item.badgeColor || "bg-slate-800 text-slate-400 border border-slate-700"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
};
