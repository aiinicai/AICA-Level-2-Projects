import React from 'react';
import { 
  ShieldCheck, 
  AlertOctagon, 
  CheckCircle2, 
  ArrowUpRight, 
  FileWarning, 
  Sparkles, 
  ChevronRight, 
  ShieldAlert, 
  TrendingUp, 
  FileCheck, 
  Award, 
  Zap,
  BookOpen
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import { Asset, RiskFinding, AssetReliabilityScore, CapexItem } from '../types';
import { formatINR } from '../services/reliabilityScore';

interface ControlTowerProps {
  assets: Asset[];
  risks: RiskFinding[];
  capexQueue?: CapexItem[];
  reliabilityScore: AssetReliabilityScore;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onNavigateTab?: (tab: string) => void;
  onSelectAsset?: (asset: Asset) => void;
  onOpenDemoSpotlight?: () => void;
  onNavigateToAsset?: (assetId: string) => void;
  onNavigateToRisks?: () => void;
  onNavigateToVerification?: () => void;
  onNavigateToCapex?: () => void;
}

export const ControlTower: React.FC<ControlTowerProps> = ({
  assets,
  risks,
  capexQueue = [],
  reliabilityScore,
  currencyMode,
  onNavigateTab,
  onSelectAsset,
  onOpenDemoSpotlight,
  onNavigateToAsset,
  onNavigateToRisks,
  onNavigateToVerification,
  onNavigateToCapex
}) => {
  // Navigation helper wrappers
  const handleGoToAsset = (assetId: string) => {
    if (onSelectAsset) {
      const found = assets.find((a) => a.id === assetId);
      if (found) onSelectAsset(found);
      else if (onNavigateTab) onNavigateTab('register');
    } else if (onNavigateToAsset) {
      onNavigateToAsset(assetId);
    } else if (onNavigateTab) {
      onNavigateTab('register');
    }
  };

  const handleGoToRisks = onNavigateToRisks || (() => onNavigateTab && onNavigateTab('risk-radar'));
  const handleGoToExceptions = () => onNavigateTab && onNavigateTab('exceptions');
  const handleGoToVerification = onNavigateToVerification || (() => onNavigateTab && onNavigateTab('physical-verification'));
  const handleGoToCapex = onNavigateToCapex || (() => onNavigateTab && onNavigateTab('capex-review'));
  const handleGoToAudit = () => onNavigateTab && onNavigateTab('audit-readiness');

  // Calculations
  const totalGrossBlock = assets.reduce((sum, a) => sum + a.costINR, 0);
  const totalNBV = assets.reduce((sum, a) => sum + a.nbvINR, 0);
  const totalAccumulatedDep = assets.reduce((sum, a) => sum + a.accumulatedDepINR, 0);
  
  const verifiedAssets = assets.filter((a) => a.verificationStatus === 'Verified');
  const verifiedCount = verifiedAssets.length;
  const unverifiedAssets = assets.filter((a) => a.verificationStatus !== 'Verified');
  const unverifiedValue = unverifiedAssets.reduce((sum, a) => sum + a.costINR, 0);
  const pvPercentage = Math.round((verifiedCount / (assets.length || 1)) * 100);

  const activeRisks = risks.filter((r) => r.status !== 'Closed');
  const criticalRisks = activeRisks.filter((r) => r.severity === 'Critical');
  const totalFinancialExposure = activeRisks.reduce((sum, r) => sum + r.financialExposureINR, 0);

  // Category Distribution Data
  const categoryMap: Record<string, number> = {};
  assets.forEach((a) => {
    categoryMap[a.category] = (categoryMap[a.category] || 0) + a.costINR;
  });
  const categoryData = Object.keys(categoryMap).map((cat) => ({
    name: cat.replace(' & Civil Structures', '').replace(' & Machinery', ''),
    value: Math.round(categoryMap[cat] / 100000), // in Lakhs
    fullName: cat,
    fullINR: categoryMap[cat]
  }));

  // Plant Distribution Data
  const plantMap: Record<string, { totalCost: number; verified: number; total: number }> = {};
  assets.forEach((a) => {
    if (!plantMap[a.plant]) {
      plantMap[a.plant] = { totalCost: 0, verified: 0, total: 0 };
    }
    plantMap[a.plant].totalCost += a.costINR;
    plantMap[a.plant].total += 1;
    if (a.verificationStatus === 'Verified') {
      plantMap[a.plant].verified += 1;
    }
  });

  const plantData = Object.keys(plantMap).map((plant) => ({
    plant: plant.split(' - ')[0].replace(' Automotive Hub', '').replace(' Tooling Hub', '').replace(' EV Plant', ''),
    fullName: plant,
    grossValue: Math.round(plantMap[plant].totalCost / 100000),
    pvRatio: Math.round((plantMap[plant].verified / plantMap[plant].total) * 100),
    count: plantMap[plant].total
  }));

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner with Executive Context */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
            <ShieldCheck className="w-4 h-4 text-blue-600" />
            <span>CFO Fixed Asset Governance & Audit Assurance</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            CFO Fixed Asset Control Tower
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-3xl">
            Real-time surveillance over asset subledger integrity, Ind AS 16 component accounting, continuous physical count verification, and CARO 2020 reporting.
          </p>
        </div>
        <div className="flex items-center space-x-3 self-start md:self-auto shrink-0">
          <button
            onClick={() => onNavigateTab && onNavigateTab('user-manual')}
            className="px-3.5 py-2 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold border border-blue-200 flex items-center space-x-2 transition-all shadow-2xs"
          >
            <BookOpen className="w-3.5 h-3.5 text-blue-600" />
            <span>User Manual & Guide</span>
          </button>
          <button
            onClick={handleGoToCapex}
            className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold border border-slate-300 flex items-center space-x-2 transition-all shadow-2xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>AI Review Queue ({capexQueue.length || 4})</span>
          </button>
          <button
            onClick={handleGoToRisks}
            className="px-3.5 py-2 rounded-lg bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 text-xs font-semibold flex items-center space-x-2 transition-all shadow-2xs"
          >
            <AlertOctagon className="w-3.5 h-3.5 text-rose-600" />
            <span>Active Control Flags ({activeRisks.length})</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Gross Block */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Gross Asset Value</p>
            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold font-mono">Gross Block</span>
          </div>
          <h3 className="text-2xl font-bold text-slate-900 mt-2 font-mono">
            {formatINR(totalGrossBlock, currencyMode)}
          </h3>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
            <span>Net Book Value (NBV):</span>
            <span className="font-bold text-slate-800 font-mono">{formatINR(totalNBV, currencyMode)}</span>
          </div>
        </div>

        {/* Physical Verification % */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Physical Verification</p>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold border border-emerald-200/80">
              CARO 3(i)(b)
            </span>
          </div>
          <div className="flex items-baseline space-x-2 mt-2">
            <h3 className="text-2xl font-bold text-emerald-700 font-mono">{pvPercentage}%</h3>
            <span className="text-xs text-slate-500 font-medium">({verifiedCount}/{assets.length} items)</span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-3">
            <div 
              className="bg-emerald-600 h-full rounded-full transition-all duration-500" 
              style={{ width: `${pvPercentage}%` }}
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
            <span>Unverified Value:</span>
            <span className="font-bold text-amber-700 font-mono">{formatINR(unverifiedValue, currencyMode)}</span>
          </div>
        </div>

        {/* High Risk & Financial Exposure */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Unverified / At Risk Value</p>
            <span className="text-[10px] px-2 py-0.5 rounded bg-rose-50 text-rose-700 font-bold border border-rose-200">
              {criticalRisks.length} Critical
            </span>
          </div>
          <h3 className="text-2xl font-bold text-rose-600 mt-2 font-mono">
            {formatINR(totalFinancialExposure, currencyMode)}
          </h3>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
            <span>Discrepancy Findings:</span>
            <span className="font-bold text-rose-700">{activeRisks.length} Exceptions</span>
          </div>
        </div>

        {/* Asset Reliability Score Card - Dark High Contrast Theme Style */}
        <div className="bg-[#0F172A] p-5 rounded-xl border border-slate-700 shadow-md text-white relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-600 opacity-10 -mr-12 -mt-12 rounded-full"></div>
          <div>
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Reliability Score</p>
              <span className="text-xs font-bold text-blue-300 bg-blue-600/20 px-2 py-0.5 rounded border border-blue-500/30">
                {reliabilityScore.grade}
              </span>
            </div>
            <div className="flex items-baseline space-x-2 mt-2">
              <h3 className="text-3xl font-black text-white font-mono">{reliabilityScore.totalScore}</h3>
              <span className="text-sm font-bold text-slate-400">/ 100</span>
            </div>
          </div>
          <div className="mt-3">
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div 
                className="bg-blue-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${reliabilityScore.totalScore}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-400 mt-2 line-clamp-1">
              {reliabilityScore.summary}
            </p>
          </div>
        </div>
      </div>

      {/* Hero: Transparent Reliability Score Breakdown & Drivers */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between pb-4 border-b border-slate-100 gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
              <ShieldAlert className="w-4 h-4 text-blue-600" />
              <span>Transparent Governance Framework</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-0.5">
              Asset Reliability Score Drivers & Weighted Impact
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Auditable mathematical score calculated across 6 weighted control pillars.
            </p>
          </div>
          <div className="flex items-center space-x-4 bg-slate-50 px-4 py-2 rounded-xl border border-slate-200">
            <div className="text-right">
              <span className="text-[10px] text-slate-500 block uppercase font-bold">Composite Score</span>
              <span className="text-xl font-bold font-mono text-blue-600">{reliabilityScore.totalScore} / 100</span>
            </div>
            <div className="h-8 w-px bg-slate-200" />
            <div>
              <span className="text-[10px] text-slate-500 block uppercase font-bold">Rating Band</span>
              <span className="text-xs font-bold text-slate-800">{reliabilityScore.grade}</span>
            </div>
          </div>
        </div>

        {/* Drivers Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 mt-4">
          {reliabilityScore.drivers.map((driver, idx) => (
            <div 
              key={idx} 
              className="bg-slate-50/80 border border-slate-200/90 rounded-xl p-3.5 flex flex-col justify-between hover:border-blue-400 hover:bg-white transition-all shadow-2xs"
            >
              <div>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-800 truncate pr-1" title={driver.name}>
                    {driver.name}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 whitespace-nowrap">
                    Wt {Math.round(driver.weight * 100)}%
                  </span>
                </div>
                <div className="flex items-baseline justify-between mt-2">
                  <span className="text-lg font-bold text-slate-900 font-mono">{driver.score}</span>
                  <span className="text-xs font-semibold text-slate-500 font-mono">
                    +{driver.weightedScore} pts
                  </span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden mt-1.5">
                  <div 
                    className={`h-full rounded-full ${
                      driver.score >= 80 ? 'bg-emerald-600' : driver.score >= 60 ? 'bg-amber-500' : 'bg-rose-500'
                    }`}
                    style={{ width: `${driver.score}%` }}
                  />
                </div>
              </div>
              <p className="text-[11px] text-slate-500 mt-2.5 line-clamp-2 leading-relaxed">
                {driver.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Main Grid: Active Exceptions Feed & Compliance Pulse */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active AI Exceptions Workflow (2 Columns) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center">
            <div>
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-tight">Active AI Exception Workflow</h4>
              <p className="text-xs text-slate-500">Autonomous risk detection & remediation queues</p>
            </div>
            <button 
              onClick={handleGoToExceptions}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold"
            >
              View Kanban Board →
            </button>
          </div>

          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-slate-50 text-[10px] text-slate-500 font-bold uppercase tracking-wider border-b border-slate-100">
                <tr>
                  <th className="px-4 py-3">Asset / ID</th>
                  <th className="px-4 py-3">Anomaly Detected</th>
                  <th className="px-4 py-3">Financial Exposure</th>
                  <th className="px-4 py-3">AI Confidence</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="text-xs divide-y divide-slate-100">
                {activeRisks.slice(0, 4).map((risk) => (
                  <tr key={risk.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-900">{risk.title}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{risk.assetId} • {risk.location}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        risk.severity === 'Critical'
                          ? 'text-rose-700 bg-rose-50 border border-rose-200'
                          : 'text-amber-700 bg-amber-50 border border-amber-200'
                      }`}>
                        {risk.riskType}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono font-bold text-slate-800">
                      {formatINR(risk.financialExposureINR, currencyMode)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${
                              risk.aiConfidencePct >= 85 ? 'bg-emerald-500' : 'bg-amber-500'
                            }`}
                            style={{ width: `${risk.aiConfidencePct}%` }}
                          />
                        </div>
                        <span className="text-[11px] font-mono text-slate-500">{risk.aiConfidencePct}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button 
                        onClick={() => handleGoToAsset(risk.assetId)}
                        className="bg-slate-900 hover:bg-slate-800 text-white px-3 py-1 rounded-lg font-medium text-[11px] transition-all shadow-xs"
                      >
                        Review Evidence
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Compliance Pulse Card - Dark Navy Theme Accent */}
        <div className="bg-[#0F172A] rounded-xl border border-slate-700 shadow-sm p-5 text-white flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-300">Compliance Pulse</h4>
              <span className="text-[10px] px-2 py-0.5 rounded bg-blue-600/30 text-blue-300 border border-blue-500/30 font-semibold">
                FY 2024-25
              </span>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-end mb-1">
                  <span className="text-xs text-slate-300">Companies Act (Schedule II)</span>
                  <span className="text-xs font-bold text-emerald-400">100% Ready</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-400 w-full h-full rounded-full" />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-end mb-1">
                  <span className="text-xs text-slate-300">Ind AS 16 Componentisation</span>
                  <span className="text-xs font-bold text-amber-400">88% Compliant</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-amber-400 w-[88%] h-full rounded-full" />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-end mb-1">
                  <span className="text-xs text-slate-300">Physical Count Coverage</span>
                  <span className="text-xs font-bold text-blue-400">{pvPercentage}% Done</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-blue-400 h-full rounded-full" style={{ width: `${pvPercentage}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-end mb-1">
                  <span className="text-xs text-slate-300">CARO 2020 Clause 3(i)</span>
                  <span className="text-xs font-bold text-emerald-400">Auditor Ready</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-400 w-[94%] h-full rounded-full" />
                </div>
              </div>
            </div>
          </div>

          <button 
            onClick={handleGoToAudit}
            className="w-full bg-white hover:bg-slate-100 text-slate-900 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider mt-5 transition-all shadow-sm"
          >
            Generate Executive Audit Memo →
          </button>
        </div>
      </div>

      {/* Analytics & Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Asset Category Distribution */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Gross Block by Asset Category</h3>
              <p className="text-xs text-slate-500">Distribution across major PPE classes under Ind AS 16</p>
            </div>
            <span className="text-xs text-slate-500 font-mono">₹ Lakhs</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryData} layout="vertical" margin={{ left: 20, right: 20, top: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" stroke="#64748b" tickFormatter={(val) => `₹${val}L`} fontSize={11} />
                <YAxis dataKey="name" type="category" stroke="#475569" fontSize={11} width={110} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '0.5rem', color: '#0f172a', fontSize: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(val: any) => [`₹${val} Lakhs`, 'Gross Value']}
                />
                <Bar dataKey="value" fill="#2563EB" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Plant Location & Physical Verification Rate */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Plant-Wise Physical Count Coverage %</h3>
              <p className="text-xs text-slate-500">Continuous verification status across operating hubs</p>
            </div>
            <button 
              onClick={handleGoToVerification}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center space-x-1"
            >
              <span>Scan Portal</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={plantData} margin={{ left: 10, right: 10, top: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="plant" stroke="#475569" fontSize={11} />
                <YAxis stroke="#64748b" domain={[0, 100]} tickFormatter={(v) => `${v}%`} fontSize={11} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '0.5rem', color: '#0f172a', fontSize: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(val: any) => [`${val}%`, 'Verification Coverage']}
                />
                <Bar dataKey="pvRatio" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
