import React, { useState } from 'react';
import {
  Target,
  HelpCircle,
  TrendingUp,
  TrendingDown,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { KpiMetric, ClientProfile } from '../../types';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface KpiDashboardViewProps {
  client: ClientProfile;
  kpis: KpiMetric[];
  onOpenMetricExplain: (metric: KpiMetric) => void;
  firmName?: string;
}

export const KpiDashboardView: React.FC<KpiDashboardViewProps> = ({
  client,
  kpis,
  onOpenMetricExplain,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const categories = [
    { id: 'all', label: 'All Indicators' },
    { id: 'profitability', label: 'Profitability' },
    { id: 'liquidity', label: 'Liquidity & Cash' },
    { id: 'efficiency', label: 'Working Capital & Efficiency' },
    { id: 'industry', label: `${client.industryName} Specific` },
  ];

  const filteredKpis = kpis.filter(k => {
    if (selectedCategory === 'all') return true;
    return k.category === selectedCategory;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Key Performance Indicators & Benchmark Intelligence" firmName={firmName} />

      {/* Top Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 card-geometric p-3.5">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {categories.map(c => (
            <button
              key={c.id}
              onClick={() => setSelectedCategory(c.id)}
              className={`px-3 py-1.5 rounded text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer ${
                selectedCategory === c.id
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Industry Benchmarks: <span className="font-bold text-slate-900">{client.industryName}</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredKpis.map(metric => (
          <div
            key={metric.id}
            className="card-geometric p-4 hover:border-slate-300 transition-colors flex flex-col justify-between"
          >
            <div>
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="metric-label text-[10px]">
                    {metric.category}
                  </span>
                  <h4 className="text-sm font-bold text-slate-900 leading-snug mt-0.5">
                    {metric.name}
                  </h4>
                </div>
                <button
                  onClick={() => onOpenMetricExplain(metric)}
                  title="Plain English explanation & root cause"
                  className="p-1 text-slate-400 hover:text-sky-600 hover:bg-sky-50 rounded transition-colors shrink-0 cursor-pointer"
                >
                  <HelpCircle className="w-4 h-4" />
                </button>
              </div>

              {/* Main Metric Value */}
              <div className="mt-3 flex items-baseline justify-between">
                <div className="metric-value">
                  {metric.formattedValue}
                </div>
                {metric.changePercentage !== undefined && (
                  <span
                    className={
                      metric.benchmarkStatus === 'outperforming'
                        ? 'pill pill-success'
                        : metric.benchmarkStatus === 'critical'
                        ? 'pill pill-danger'
                        : 'pill pill-info'
                    }
                  >
                    {metric.trend === 'up' ? (
                      <ArrowUpRight className="w-3 h-3 mr-0.5" />
                    ) : (
                      <ArrowDownRight className="w-3 h-3 mr-0.5" />
                    )}
                    {metric.changePercentage > 0 ? `+${metric.changePercentage.toFixed(1)}%` : `${metric.changePercentage.toFixed(1)}%`}
                  </span>
                )}
              </div>

              {/* Benchmark Comparison Box */}
              <div className="mt-3 p-2 bg-slate-50 rounded border border-slate-200/80 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium text-[11px]">Benchmark:</span>
                <span className="font-bold text-slate-800 text-[11px]">
                  {metric.benchmarkFormatted || 'Proprietary Target'}
                </span>
              </div>
            </div>

            {/* Bottom Status & Explain Action */}
            <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center justify-between">
              <span
                className={
                  metric.benchmarkStatus === 'outperforming'
                    ? 'pill pill-success text-[10px]'
                    : metric.benchmarkStatus === 'lagging'
                    ? 'pill pill-warning text-[10px]'
                    : metric.benchmarkStatus === 'critical'
                    ? 'pill pill-danger text-[10px]'
                    : 'pill pill-info text-[10px]'
                }
              >
                {metric.benchmarkStatus === 'outperforming' ? 'Optimal Range' : metric.benchmarkStatus === 'lagging' ? 'Watchlist' : metric.benchmarkStatus === 'critical' ? 'Action Required' : 'On Track'}
              </span>

              <button
                onClick={() => onOpenMetricExplain(metric)}
                className="text-xs font-semibold text-sky-600 hover:text-sky-800 flex items-center gap-1 cursor-pointer"
              >
                <Sparkles className="w-3 h-3 text-sky-500" />
                Root Cause →
              </button>
            </div>
          </div>
        ))}
      </div>

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
