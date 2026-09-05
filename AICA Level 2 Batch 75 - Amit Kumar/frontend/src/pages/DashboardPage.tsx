import React, { useEffect, useState } from 'react';
import type { Client, FinancialStatements, ValidationItem, RatioItem } from '../types';
import { api } from '../services/api';
import { 
  CheckCircle2, XCircle, ArrowRight, RefreshCw, Download, 
  LayoutDashboard, TrendingUp, ShieldAlert, Sparkles, PieChart, Activity, DollarSign
} from 'lucide-react';

interface DashboardProps {
  client: Client;
  onNavigate: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardProps> = ({ client, onNavigate }) => {
  const [fs, setFs] = useState<FinancialStatements | null>(null);
  const [validations, setValidations] = useState<ValidationItem[]>([]);
  const [ratios, setRatios] = useState<RatioItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [fsRes, valRes, ratioRes] = await Promise.all([
        api.getFinancialStatements(client.id),
        api.getValidations(client.id),
        api.getRatios(client.id)
      ]);
      setFs(fsRes);
      setValidations(valRes);
      setRatios(ratioRes);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (client) loadData();
  }, [client.id]);

  const handleLoadSample = async () => {
    await api.loadSampleData(client.id);
    await loadData();
  };

  const getMetric = (particulars: string, source: 'bs' | 'pl') => {
    if (!fs) return 0;
    const lines = source === 'bs' ? fs.balance_sheet : fs.profit_and_loss;
    const found = lines.find(l => l.particulars.trim().toLowerCase().includes(particulars.toLowerCase()));
    return found ? found.cy_amount : 0;
  };

  const passedCount = validations.filter(v => v.status === 'Passed').length;
  const warningCount = validations.filter(v => v.status === 'Warning').length;
  const criticalCount = validations.filter(v => v.status === 'Critical').length;

  const totalRevenue = getMetric('Revenue from Operations', 'pl');
  const netProfit = getMetric('Profit After Tax', 'pl');
  const totalAssets = getMetric('TOTAL ASSETS', 'bs');

  const healthScore = validations.length > 0 
    ? Math.round((passedCount / validations.length) * 100) 
    : 100;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-tight flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5 text-orange-600" />
            FS BUILDER LITE Executive Dashboard
          </h1>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
            IGAAP Financial Preparation & Audit Compliance Portal for {client.name}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={handleLoadSample} className="ca-button-outline text-xs">
            <RefreshCw className="w-3.5 h-3.5" />
            Reload Sample Data
          </button>
          <button onClick={() => onNavigate('split-workbench')} className="ca-button-secondary text-xs">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            Open Split Workbench
          </button>
          <button onClick={() => onNavigate('export-reports')} className="ca-button-primary text-xs">
            <Download className="w-3.5 h-3.5" />
            Export Workbooks
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 font-semibold text-xs flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-orange-600" /> Calculating engagement parameters...
        </div>
      ) : (
        <>
          {/* Key Financial Studio Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Card 1: BS Tally */}
            <div className="studio-card p-4 space-y-2 relative overflow-hidden">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <span>BS Tally Status</span>
                <Activity className="w-4 h-4 text-orange-600" />
              </div>
              <div className="pt-1">
                {fs?.is_tallied ? (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                    <div>
                      <div className="text-base font-black text-emerald-600 dark:text-emerald-400">TALLIED</div>
                      <div className="text-[10px] text-slate-400 font-mono">Diff: ₹0.00 Lakhs</div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <XCircle className="w-6 h-6 text-rose-500" />
                    <div>
                      <div className="text-sm font-bold text-rose-600">OUT OF TALLY</div>
                      <div className="text-[10px] text-rose-500 font-mono">Diff: ₹{fs?.difference.toFixed(2)} L</div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Card 2: Audit Health Index */}
            <div className="studio-card p-4 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <span>Audit Health Index</span>
                <ShieldAlert className="w-4 h-4 text-blue-600" />
              </div>
              <div className="flex items-center justify-between pt-1">
                <div className="text-2xl font-black text-[#1B365D] dark:text-blue-400">{healthScore}%</div>
                <div className="text-[10px] font-bold text-slate-500 space-y-0.5 text-right font-mono">
                  <div className="text-emerald-600">{passedCount} Passed</div>
                  <div className="text-amber-600">{warningCount} Warnings</div>
                  <div className="text-red-600">{criticalCount} Critical</div>
                </div>
              </div>
            </div>

            {/* Card 3: Total Revenue */}
            <div className="studio-card p-4 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <span>Revenue (Operations)</span>
                <DollarSign className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="pt-1">
                <div className="text-xl font-black text-slate-900 dark:text-white font-mono">
                  ₹{totalRevenue.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-[10px] font-bold text-slate-400 font-mono">Lakhs (FY 2024-25)</div>
              </div>
            </div>

            {/* Card 4: Profit After Tax */}
            <div className="studio-card p-4 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <span>Profit After Tax (PAT)</span>
                <TrendingUp className="w-4 h-4 text-orange-600" />
              </div>
              <div className="pt-1">
                <div className="text-xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
                  ₹{netProfit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-[10px] font-bold text-slate-400 font-mono">Lakhs (PAT Margin)</div>
              </div>
            </div>

            {/* Card 5: Total Balance Sheet Size */}
            <div className="studio-card p-4 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                <span>Total Assets / Equity</span>
                <PieChart className="w-4 h-4 text-purple-600" />
              </div>
              <div className="pt-1">
                <div className="text-xl font-black text-[#1B365D] dark:text-blue-400 font-mono">
                  ₹{totalAssets.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-[10px] font-bold text-slate-400 font-mono">Lakhs (Schedule III Size)</div>
              </div>
            </div>
          </div>

          {/* Middle Section: Quick Ratios Visualizer & Validation Quick Feed */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Schedule III Ratio Cards (Col 7) */}
            <div className="lg:col-span-7 studio-card p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                <h3 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider flex items-center gap-2">
                  <PieChart className="w-4 h-4 text-orange-600" /> Key Schedule III Financial Ratios
                </h3>
                <button onClick={() => onNavigate('ratio-analysis')} className="text-xs font-bold text-orange-600 hover:underline flex items-center gap-1">
                  View All Ratios <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {ratios.slice(0, 4).map(r => (
                  <div key={r.code} className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-slate-700/60 space-y-1">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                      <span className="truncate">{r.name}</span>
                      <span className="text-[10px] text-slate-400 font-mono">{r.code}</span>
                    </div>
                    <div className="flex items-baseline justify-between pt-1">
                      <span className="text-lg font-black text-[#1B365D] dark:text-blue-400 font-mono">
                        {r.cy_value} <span className="text-xs font-normal text-slate-500">{r.unit}</span>
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                        r.movement.includes('Up') || r.movement.includes('Improved') 
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400' 
                          : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                      }`}>
                        {r.movement}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Live Sanity Feed (Col 5) */}
            <div className="lg:col-span-5 studio-card p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                <h3 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-orange-600" /> Compliance Sanity Checks
                </h3>
                <button onClick={() => onNavigate('validation-checks')} className="text-xs font-bold text-orange-600 hover:underline flex items-center gap-1">
                  Inspector <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {validations.slice(0, 5).map(v => (
                  <div key={v.code} className="p-2.5 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-slate-700/60 flex items-center justify-between gap-3 text-xs">
                    <div className="truncate">
                      <div className="font-bold text-slate-800 dark:text-slate-200 truncate">{v.check_name}</div>
                      <div className="text-[10px] text-slate-400 truncate">{v.message}</div>
                    </div>
                    <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded uppercase shrink-0 ${
                      v.status === 'Passed' ? 'badge-passed' : (v.status === 'Warning' ? 'badge-warning' : 'badge-critical')
                    }`}>
                      {v.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
