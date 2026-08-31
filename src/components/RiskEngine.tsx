import React, { useState } from 'react';
import { 
  AlertOctagon, 
  Search, 
  ArrowRight, 
  ChevronRight, 
  ShieldAlert
} from 'lucide-react';
import { RiskFinding, RiskType } from '../types';
import { formatINR } from '../services/reliabilityScore';

interface RiskEngineProps {
  risks: RiskFinding[];
  setRisks: React.Dispatch<React.SetStateAction<RiskFinding[]>>;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onNavigateToAsset: (assetId: string) => void;
  onNavigateToExceptions: (riskId?: string) => void;
}

export const RiskEngine: React.FC<RiskEngineProps> = ({
  risks,
  currencyMode,
  onNavigateToAsset,
  onNavigateToExceptions
}) => {
  const [selectedRiskType, setSelectedRiskType] = useState<string>('All');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('All');
  const [selectedStage, setSelectedStage] = useState<string>('All');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRiskId, setExpandedRiskId] = useState<string | null>(risks[0]?.id || null);

  const riskTypes: (RiskType | 'All')[] = [
    'All',
    'Ghost Asset',
    'Duplicate Capitalisation',
    'Disposed Still Depreciating',
    'Wrong Location',
    'Abnormal Useful Life',
    'Missing Documents',
    'Potential Impairment'
  ];

  const filteredRisks = risks.filter((r) => {
    const matchSearch =
      r.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.assetId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.assetName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.explanation.toLowerCase().includes(searchTerm.toLowerCase());

    const matchType = selectedRiskType === 'All' || r.riskType === selectedRiskType;
    const matchSev = selectedSeverity === 'All' || r.severity === selectedSeverity;
    const matchStage = selectedStage === 'All' || r.status === selectedStage;

    return matchSearch && matchType && matchSev && matchStage;
  });

  const totalExposure = filteredRisks.reduce((sum, r) => sum + r.financialExposureINR, 0);
  const criticalCount = filteredRisks.filter((r) => r.severity === 'Critical').length;

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-rose-600">
            <AlertOctagon className="w-4 h-4 text-rose-600" />
            <span>Deterministic Rules + AI Anomaly Detection Radar</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            Fixed Asset Risk & Anomaly Radar
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Transparent detection of ghost assets, duplicate invoices, location shifts, disposed assets still depreciating, and Ind AS 36 impairment triggers.
          </p>
        </div>

        <button
          onClick={() => onNavigateToExceptions()}
          className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center space-x-2 transition-all shadow-xs self-start md:self-auto"
        >
          <span>Open Exception Governance Kanban</span>
          <ArrowRight className="w-4 h-4 text-blue-400" />
        </button>
      </div>

      {/* Summary KPI Exposure Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Total Filtered Financial Exposure</span>
          <div className="text-2xl font-bold text-rose-600 font-mono mt-1">
            {formatINR(totalExposure, currencyMode)}
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Across {filteredRisks.length} active risk findings
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Critical Breaches</span>
          <div className="text-2xl font-bold text-rose-700 font-mono mt-1">
            {criticalCount} Critical
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Includes Ghost Assets & Duplicate Capitalisation
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-slate-500 font-semibold uppercase">Statutory Reporting Impact</span>
          <div className="text-base font-bold text-amber-700 mt-1">
            CARO 2020 Clause 3(i) Triggered
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            Requires management disclosure if unresolved
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search risk by Asset ID, title, explanation, or plant location..."
              className="w-full pl-9 pr-4 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedRiskType}
              onChange={(e) => setSelectedRiskType(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              {riskTypes.map((rt) => (
                <option key={rt} value={rt}>Type: {rt}</option>
              ))}
            </select>

            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              <option value="All">Severity: All</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>

            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
            >
              <option value="All">Stage: All</option>
              <option value="Detected">Detected</option>
              <option value="Assigned">Assigned</option>
              <option value="Investigating">Investigating</option>
              <option value="Management Review">Management Review</option>
              <option value="Approved">Approved</option>
              <option value="Closed">Closed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Risks List & Detailed Inspection */}
      <div className="space-y-3">
        {filteredRisks.map((risk) => {
          const isExpanded = expandedRiskId === risk.id;
          return (
            <div
              key={risk.id}
              className={`bg-white border rounded-xl transition-all overflow-hidden ${
                isExpanded ? 'border-blue-500 shadow-md ring-1 ring-blue-500/20' : 'border-slate-200 hover:border-slate-300 shadow-2xs'
              }`}
            >
              {/* Risk Summary Header Bar */}
              <div
                onClick={() => setExpandedRiskId(isExpanded ? null : risk.id)}
                className="p-5 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-slate-50/80 transition-colors"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                      risk.severity === 'Critical'
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}>
                      {risk.severity} Severity
                    </span>
                    <span className="text-xs font-mono font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                      {risk.riskType}
                    </span>
                    <span className="text-xs font-mono font-bold text-blue-700">
                      {risk.assetId}
                    </span>
                    <span className="text-xs text-slate-500">
                      • {risk.location}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900">
                    {risk.title}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-1">
                    {risk.explanation}
                  </p>
                </div>

                <div className="flex items-center space-x-5 self-end md:self-center shrink-0">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Financial Exposure</span>
                    <span className="text-base font-bold text-rose-600 font-mono">
                      {formatINR(risk.financialExposureINR, currencyMode)}
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Stage</span>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                      {risk.status}
                    </span>
                  </div>

                  <ChevronRight className={`w-5 h-5 text-slate-400 transform transition-transform ${isExpanded ? 'rotate-90 text-blue-600' : ''}`} />
                </div>
              </div>

              {/* Expanded Deep Risk Dossier */}
              {isExpanded && (
                <div className="p-6 border-t border-slate-200 bg-slate-50/70 space-y-5 text-xs text-slate-700 animate-in fade-in duration-150">
                  
                  {/* Detailed Explanation & Evidence Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2 shadow-2xs">
                      <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                        Detailed Root-Cause & Risk Analysis
                      </span>
                      <p className="text-slate-700 leading-relaxed">
                        {risk.explanation}
                      </p>
                    </div>

                    <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2 shadow-2xs">
                      <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                        Auditable Evidence & Trigger Trail
                      </span>
                      <p className="text-slate-700 leading-relaxed font-mono text-[11px]">
                        {risk.evidence}
                      </p>
                    </div>
                  </div>

                  {/* Statutory Reference & Action Plan */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="bg-white border border-slate-200 p-3.5 rounded-xl shadow-2xs">
                      <span className="text-slate-500 text-[11px] block font-semibold">Statutory / Policy Ref:</span>
                      <span className="font-bold text-amber-800 block mt-1">{risk.statutoryReference}</span>
                    </div>
                    <div className="bg-white border border-slate-200 p-3.5 rounded-xl shadow-2xs">
                      <span className="text-slate-500 text-[11px] block font-semibold">Assigned Risk Owner:</span>
                      <span className="font-bold text-slate-900 block mt-1">{risk.owner}</span>
                    </div>
                    <div className="bg-white border border-slate-200 p-3.5 rounded-xl shadow-2xs">
                      <span className="text-slate-500 text-[11px] block font-semibold">Created / Updated:</span>
                      <span className="font-mono text-slate-700 block mt-1">{risk.createdDate} (Last: {risk.updatedDate})</span>
                    </div>
                  </div>

                  {/* Recommended Corrective Action */}
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                    <span className="font-bold text-blue-900 uppercase tracking-wider text-[11px] block mb-1">
                      Recommended Internal Control Remediation:
                    </span>
                    <p className="text-xs text-blue-800">{risk.recommendedAction}</p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-200 gap-3">
                    <button
                      onClick={() => onNavigateToAsset(risk.assetId)}
                      className="text-xs text-blue-600 hover:text-blue-800 font-semibold underline"
                    >
                      View Complete Asset Subledger Record ({risk.assetId}) →
                    </button>

                    <button
                      onClick={() => onNavigateToExceptions(risk.id)}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg flex items-center space-x-2 transition-all shadow-xs"
                    >
                      <span>Take Action in Exception Workflow</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>

                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
