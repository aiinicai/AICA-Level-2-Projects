import React, { useEffect, useState } from 'react';
import {
  Building2,
  Tag,
  Clock,
  Layers,
  Package,
  AlertTriangle,
  ShieldAlert,
  ArrowUpRight,
  TrendingUp,
  Activity,
  FileSpreadsheet,
  Printer
} from 'lucide-react';
import api from '../services/api';
import { DashboardStats, CompanyStat } from '../types';
import { TabType } from '../components/Sidebar';

interface DashboardPageProps {
  onNavigate: (tab: TabType) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [companyStats, setCompanyStats] = useState<CompanyStat[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [resStats, resComp] = await Promise.all([
        api.get<DashboardStats>('/dashboard/stats'),
        api.get<CompanyStat[]>('/dashboard/company-stats')
      ]);
      setStats(resStats.data);
      setCompanyStats(resComp.data);
    } catch (e) {
      console.error('Error fetching dashboard data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading || !stats) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
        <Activity className="w-5 h-5 animate-spin mr-2 text-blue-600" />
        Loading asset metrics...
      </div>
    );
  }

  const kpis = [
    { title: 'Total Companies', value: stats.total_companies, icon: Building2, color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-100' },
    { title: 'Total Tags Generated', value: stats.total_tags_generated.toLocaleString(), icon: Tag, color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-100' },
    { title: 'Tags Generated Today', value: stats.tags_generated_today.toLocaleString(), icon: Clock, color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100' },
    { title: 'Fixed Assets Tagged', value: stats.fixed_assets_count.toLocaleString(), icon: Layers, color: 'text-sky-600', bg: 'bg-sky-50', border: 'border-sky-100' },
    { title: 'Stock Assets Tagged', value: stats.stock_assets_count.toLocaleString(), icon: Package, color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-100' },
    { title: 'Duplicate Attempts (Blocked)', value: stats.duplicate_attempts_count, icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
    { title: 'Duplicate Overrides (Audited)', value: stats.duplicate_overrides_count, icon: ShieldAlert, color: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-100' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header & Quick Launch */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Executive Operations Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">Real-time asset tagging, numbering sequence, and governance statistics</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => onNavigate('generate')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <Tag className="w-4 h-4" />
            Generate Single Tag
          </button>
          <button
            onClick={() => onNavigate('bulk')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Bulk Excel Upload
          </button>
          <button
            onClick={() => onNavigate('printing')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <Printer className="w-4 h-4 text-slate-500" />
            Sheet Printing
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div
              key={idx}
              className={`bg-white rounded-xl p-5 border ${kpi.border} shadow-sm flex items-center justify-between transition hover:shadow-md`}
            >
              <div>
                <div className="text-xs font-semibold text-slate-500">{kpi.title}</div>
                <div className="text-2xl font-black text-slate-900 mt-1 font-mono tracking-tight">
                  {kpi.value}
                </div>
              </div>
              <div className={`p-3 rounded-xl ${kpi.bg} ${kpi.color}`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Two Column Layout: Company Statistics & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Company Summary Table (2 Columns) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-bold text-slate-900">Company-wise Asset Breakdown</h2>
            </div>
            <span className="text-xs font-semibold text-slate-500">{companyStats.length} Registered Companies</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-4">Company Name</th>
                  <th className="py-3 px-4 text-right">Total Tags</th>
                  <th className="py-3 px-4 text-right">Fixed Assets</th>
                  <th className="py-3 px-4 text-right">Stock</th>
                  <th className="py-3 px-4 text-right">Today</th>
                  <th className="py-3 px-4 text-center">Last Asset ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {companyStats.map((cs) => (
                  <tr key={cs.company_id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3.5 px-4 font-semibold text-slate-900 flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-blue-50 text-blue-600 font-bold text-[10px] flex items-center justify-center border border-blue-200">
                        {cs.short_name.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-bold">{cs.company_name}</div>
                        <div className="text-[10px] text-slate-400">{cs.short_name}</div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right font-bold text-slate-900 font-mono">
                      {cs.total_tags.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-slate-600 font-mono">
                      {cs.fixed_assets.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right font-medium text-slate-600 font-mono">
                      {cs.stock_assets.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        +{cs.tags_today}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="font-mono text-[11px] font-bold bg-slate-100 text-slate-800 px-2 py-0.5 rounded">
                        {cs.last_asset_id || '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Audit Trail Stream (1 Column) */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-900">Live Audit Activity</h2>
            </div>
            <button
              onClick={() => onNavigate('audit')}
              className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-0.5"
            >
              View Full Log
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-4 flex-1 divide-y divide-slate-100 overflow-y-auto max-h-[380px]">
            {stats.recent_activity.map((act) => (
              <div key={act.id} className="py-2.5 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold font-mono text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded">
                    {act.action}
                  </span>
                  <span className="text-[10px] text-slate-400">{act.time}</span>
                </div>
                <div className="text-xs text-slate-600 mt-1 truncate">{act.details}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">By {act.user}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
