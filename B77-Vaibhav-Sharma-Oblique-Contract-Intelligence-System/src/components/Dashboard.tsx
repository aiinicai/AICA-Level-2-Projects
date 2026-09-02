import React, { useState } from 'react';
import { 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  CheckCircle2, 
  ArrowRight, 
  Building2, 
  Coins, 
  Calendar, 
  Clock, 
  Percent, 
  ShieldAlert, 
  GitMerge, 
  FileSpreadsheet, 
  FileCheck,
  ChevronRight,
  TrendingUp,
  FileText,
  Sparkles,
  Search,
  Check
} from 'lucide-react';
import { ContractDocument, Finding, AnalysisDomain } from '../types/contract';

interface DashboardProps {
  contract: ContractDocument | null;
  onSelectFinding: (finding: Finding) => void;
  setActiveTab: (tab: string) => void;
  onNewAnalysis: () => void;
  onLoadDemo: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  contract,
  onSelectFinding,
  setActiveTab,
  onNewAnalysis,
  onLoadDemo
}) => {
  const [selectedDashboardFindingIndex, setSelectedDashboardFindingIndex] = useState<number>(0);
  const [domainFilter, setDomainFilter] = useState<string>('All');

  if (!contract) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 text-center">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-10 space-y-5">
          <div className="w-14 h-14 bg-blue-50 rounded-xl flex items-center justify-center mx-auto text-blue-600">
            <FileText className="w-7 h-7" />
          </div>
          <div className="space-y-1.5">
            <h2 className="text-xl font-bold text-gray-900 tracking-tight">No Contract Analyzed Yet</h2>
            <p className="text-gray-500 max-w-lg mx-auto text-xs leading-relaxed">
              Upload a commercial agreement or load our pre-configured turnkey agreement to see structured Indian accounting, GST, TDS, MSME, and audit impact in the Bento Grid workspace.
            </p>
          </div>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={onNewAnalysis}
              className="w-full sm:w-auto px-5 py-2 rounded-md text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-xs transition"
            >
              Upload & Analyze Contract
            </button>
            <button
              onClick={onLoadDemo}
              className="w-full sm:w-auto px-5 py-2 rounded-md text-xs font-semibold bg-white hover:bg-gray-50 text-gray-800 border border-gray-300 transition"
            >
              Load Demo Contract (₹5.20 Cr)
            </button>
          </div>
        </div>
      </div>
    );
  }

  const redFindings = contract.findings.filter(f => f.attention === 'RED');
  const amberFindings = contract.findings.filter(f => f.attention === 'AMBER');
  const blueFindings = contract.findings.filter(f => f.attention === 'BLUE');
  const totalFindings = contract.findings.length || 1;

  const redPercent = Math.round((redFindings.length / totalFindings) * 100);
  const amberPercent = Math.round((amberFindings.length / totalFindings) * 100);
  const bluePercent = 100 - redPercent - amberPercent;

  // Filtered findings for table
  const displayedFindings = contract.findings.filter(f => {
    if (domainFilter === 'All') return true;
    return f.domains.includes(domainFilter as AnalysisDomain);
  });

  const activeFinding = displayedFindings[selectedDashboardFindingIndex] || contract.findings[0];

  // Domain distribution
  const domainCounts: Record<string, number> = {};
  contract.findings.forEach(f => {
    f.domains.forEach(d => {
      domainCounts[d] = (domainCounts[d] || 0) + 1;
    });
  });

  const domainsList: AnalysisDomain[] = [
    'MSME',
    'Related Party',
    'Accounting',
    'GST',
    'TDS',
    'Audit',
    'Financial Reporting',
    'Working Capital'
  ];

  // Key reasoning quote
  const featuredReasoning = contract.crossClauseInsights[0]?.whyItMatters || 
    "The 90-day payment term combined with 10% retention creates a mismatch with MSME Section 15 compliance. Retention may be treated as deferred payment under Ind AS 109 and Section 43B(h).";

  return (
    <div className="space-y-4">
      {/* Bento Grid Top Row: Snapshot + Attention + Key Reasoning Highlight */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Bento Tile 1: Contract Snapshot */}
        <div className="col-span-12 md:col-span-4 bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">
                Contract Snapshot
              </h2>
              <span className="text-[10px] px-2 py-0.5 bg-blue-50 text-blue-700 font-semibold rounded border border-blue-100">
                {contract.identity.contractType || 'Turnkey EPC'}
              </span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center border-b border-gray-100 pb-2">
                <span className="text-gray-500">Primary Party (Vendor)</span>
                <span className="font-bold text-gray-800 text-right truncate max-w-[160px]" title={contract.parties[0]?.name}>
                  {contract.parties[0]?.name || 'ABC Manufacturing'}
                </span>
              </div>

              <div className="flex justify-between items-center border-b border-gray-100 pb-2">
                <span className="text-gray-500">Contract Value</span>
                <span className="font-bold text-emerald-700 font-mono">
                  {contract.commercialTerms.contractValue}
                </span>
              </div>

              <div className="flex justify-between items-center border-b border-gray-100 pb-2">
                <span className="text-gray-500">Payment Term</span>
                <span className="font-bold text-orange-600">
                  {contract.commercialTerms.creditPeriodDays ? `${contract.commercialTerms.creditPeriodDays} Days (Deferred)` : 'Milestone Basis'}
                </span>
              </div>

              <div className="flex justify-between items-center border-b border-gray-100 pb-2">
                <span className="text-gray-500">Retention Rate</span>
                <span className="font-bold text-blue-600">
                  {contract.commercialTerms.retentionMoney?.percentage || '10%'} of Invoice
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-gray-500">Mobilization Advance</span>
                <span className="font-bold text-gray-800">
                  {contract.commercialTerms.advances?.percentage || '15%'} on Signing
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-[11px]">
            <span className="text-gray-400 font-mono">Ref: {contract.identity.contractNumber || 'CON-2024-88'}</span>
            <button 
              onClick={() => setActiveTab('viewer')} 
              className="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1 cursor-pointer"
            >
              <span>View Source Text</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Bento Tile 2: Impact Attention Scorecard */}
        <div 
          onClick={() => setActiveTab('findings')}
          className="col-span-12 md:col-span-4 bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between cursor-pointer hover:border-gray-300 transition"
        >
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">
                Impact Attention
              </h2>
              <span className="text-[10px] text-gray-400 font-mono">
                {contract.findings.length} Total Issues
              </span>
            </div>

            {/* Metric Split */}
            <div className="flex items-center justify-between py-2 px-2">
              <div className="text-center flex-1">
                <div className="text-3xl font-bold text-red-600 tracking-tight">
                  {redFindings.length}
                </div>
                <div className="text-[9px] font-bold text-gray-400 uppercase tracking-wider mt-1">
                  High Attention
                </div>
              </div>

              <div className="w-px h-10 bg-gray-200"></div>

              <div className="text-center flex-1">
                <div className="text-3xl font-bold text-orange-500 tracking-tight">
                  {amberFindings.length}
                </div>
                <div className="text-[9px] font-bold text-gray-400 uppercase tracking-wider mt-1">
                  Review Req.
                </div>
              </div>

              <div className="w-px h-10 bg-gray-200"></div>

              <div className="text-center flex-1">
                <div className="text-3xl font-bold text-blue-500 tracking-tight">
                  {blueFindings.length}
                </div>
                <div className="text-[9px] font-bold text-gray-400 uppercase tracking-wider mt-1">
                  Informational
                </div>
              </div>
            </div>

            {/* Composite Progress Bar */}
            <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden flex mt-4">
              <div className="h-full bg-red-600 transition-all duration-500" style={{ width: `${Math.max(10, redPercent)}%` }}></div>
              <div className="h-full bg-orange-500 transition-all duration-500" style={{ width: `${Math.max(10, amberPercent)}%` }}></div>
              <div className="h-full bg-blue-500 transition-all duration-500" style={{ width: `${Math.max(10, bluePercent)}%` }}></div>
            </div>
          </div>

          <p className="text-[11px] text-gray-500 mt-4 leading-relaxed">
            {redFindings.length > 0 ? (
              <span className="text-red-700 font-medium">
                • {redFindings[0]?.title} requires priority review under {redFindings[0]?.frameworkToConfirm[0] || 'Statute'}.
              </span>
            ) : (
              'All primary statutory compliance points reviewed.'
            )}
          </p>
        </div>

        {/* Bento Tile 3: Key Reasoning Highlight / Featured Bento */}
        <div className="col-span-12 md:col-span-4 bg-blue-900 rounded-xl p-5 shadow-lg text-white flex flex-col justify-between">
          <div>
            <h2 className="text-[11px] font-bold text-blue-300 uppercase tracking-widest mb-3 underline decoration-blue-400 underline-offset-4">
              Key Reasoning Highlight
            </h2>
            <p className="text-xs sm:text-sm italic font-serif leading-relaxed text-blue-100 mb-4 line-clamp-4">
              "{featuredReasoning}"
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-1.5 bg-blue-800/50 p-2 rounded-lg border border-blue-700/50">
              <span className="text-[10px] bg-blue-400 text-blue-950 px-2 py-0.5 font-bold rounded">
                MSME Sec 15
              </span>
              <span className="text-[10px] bg-blue-400 text-blue-950 px-2 py-0.5 font-bold rounded">
                Ind AS 115
              </span>
              <span className="text-[10px] bg-blue-400 text-blue-950 px-2 py-0.5 font-bold rounded">
                Sec 43B(h)
              </span>
            </div>

            <button
              onClick={() => setActiveTab('cross-clause')}
              className="w-full text-center py-1.5 bg-blue-800/80 hover:bg-blue-800 rounded text-[11px] font-bold text-blue-200 hover:text-white uppercase tracking-wider transition cursor-pointer"
            >
              Explore 2nd Pass Reasoning →
            </button>
          </div>
        </div>
      </div>

      {/* Bento Grid Middle Row: Findings Table Bento (Col 8) + Detailed Finding View Bento (Col 4) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Bento Tile 4: Impact Analysis Findings Table Bento (Col 8) */}
        <div className="col-span-12 md:col-span-8 bg-white rounded-xl border border-gray-200 flex flex-col shadow-xs overflow-hidden">
          {/* Header & Filter strip */}
          <div className="bg-gray-50 border-b border-gray-200 px-5 py-3 flex flex-wrap justify-between items-center gap-2">
            <h2 className="text-[11px] font-bold text-gray-500 uppercase tracking-widest">
              Impact Analysis Findings
            </h2>
            <div className="flex items-center gap-2">
              <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                className="text-[10px] bg-white border border-gray-300 px-2 py-1 rounded font-medium text-gray-700 focus:ring-1 focus:ring-blue-500 cursor-pointer"
              >
                <option value="All">Filter: All Domains</option>
                {domainsList.map(d => (
                  <option key={d} value={d}>Domain: {d}</option>
                ))}
              </select>
              <button
                onClick={() => setActiveTab('findings')}
                className="text-[10px] bg-white border border-gray-300 hover:bg-gray-50 px-2.5 py-1 rounded font-semibold text-blue-600 transition cursor-pointer"
              >
                View Full Matrix ({contract.findings.length})
              </button>
            </div>
          </div>

          {/* Table Container */}
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-white text-[10px] uppercase text-gray-400 font-bold border-b border-gray-100">
                <tr>
                  <th className="px-5 py-3">Finding Title</th>
                  <th className="px-5 py-3">Domain</th>
                  <th className="px-5 py-3">Attention</th>
                  <th className="px-5 py-3">Source</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="text-xs divide-y divide-gray-50">
                {displayedFindings.slice(0, 6).map((finding, idx) => {
                  const isSelected = activeFinding.id === finding.id;
                  return (
                    <tr 
                      key={finding.id}
                      onClick={() => setSelectedDashboardFindingIndex(idx)}
                      className={`hover:bg-gray-50 cursor-pointer transition ${
                        isSelected ? 'bg-blue-50/60 font-semibold' : ''
                      }`}
                    >
                      <td className="px-5 py-3.5 font-bold text-gray-900 max-w-[220px] truncate" title={finding.title}>
                        {finding.title}
                      </td>
                      <td className="px-5 py-3.5 text-gray-500 italic font-serif text-xs">
                        {finding.domains[0] || 'Accounting'}
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`px-2 py-0.5 rounded-full font-bold text-[9px] inline-block ${
                          finding.attention === 'RED' ? 'bg-red-100 text-red-700' :
                          finding.attention === 'AMBER' ? 'bg-orange-100 text-orange-700' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {finding.attention}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-gray-400 font-mono text-[11px]">
                        Cl. {finding.source.clause || finding.source.page}
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`font-medium text-[11px] ${
                          finding.status === 'Cleared' ? 'text-emerald-600' :
                          finding.status === 'Under Review' ? 'text-blue-600' :
                          finding.status === 'Escalated' ? 'text-rose-600 font-bold' :
                          'text-gray-500'
                        }`}>
                          {finding.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Bento Tile 5: Detailed Finding View Bento (Col 4) */}
        <div className="col-span-12 md:col-span-4 bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">
                Detailed Finding View
              </h2>
              <span className="text-[10px] text-gray-400 font-mono">
                {activeFinding.id}
              </span>
            </div>

            {/* Highlight Banner */}
            <div className={`p-3 rounded-lg border mb-3 ${
              activeFinding.attention === 'RED' ? 'bg-red-50 border-red-100 text-red-900' :
              activeFinding.attention === 'AMBER' ? 'bg-orange-50 border-orange-100 text-orange-900' :
              'bg-blue-50 border-blue-100 text-blue-900'
            }`}>
              <h3 className="text-xs font-bold mb-0.5">{activeFinding.title}</h3>
              <p className="text-[10px] opacity-80 font-mono">
                {activeFinding.id} | Domain: {activeFinding.domains.join(', ')}
              </p>
            </div>

            <div className="space-y-3 text-xs">
              {/* Source clause */}
              <div>
                <p className="text-[9px] uppercase font-bold text-gray-400 mb-1">
                  Source Clause (Pg {activeFinding.source.page}, Cl {activeFinding.source.clause})
                </p>
                <p className="text-[11px] bg-gray-50 p-2.5 border-l-2 border-red-400 italic text-gray-600 leading-normal rounded-r font-mono">
                  "{activeFinding.source.extractedText.slice(0, 140)}..."
                </p>
              </div>

              {/* Why it matters */}
              <div>
                <p className="text-[9px] uppercase font-bold text-gray-400 mb-1">Why it matters</p>
                <p className="text-[11px] text-gray-800 leading-snug font-medium line-clamp-3">
                  {activeFinding.whyItMatters}
                </p>
              </div>

              {/* Management Questions */}
              <div>
                <p className="text-[9px] uppercase font-bold text-gray-400 mb-1">Management Questions</p>
                <ul className="text-[11px] space-y-1 list-disc ml-3.5 text-gray-700">
                  {activeFinding.managementQuestions.slice(0, 2).map((q, idx) => (
                    <li key={idx} className="line-clamp-2">{q}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-4 pt-3 border-t border-gray-100 flex gap-2">
            <button
              onClick={() => onSelectFinding(activeFinding)}
              className="flex-1 bg-gray-900 hover:bg-black text-white text-[10px] py-2 rounded font-bold uppercase tracking-widest transition cursor-pointer"
            >
              Full Inspection
            </button>
            <button
              onClick={() => setActiveTab('findings')}
              className="flex-1 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-[10px] py-2 rounded font-bold uppercase tracking-widest transition cursor-pointer"
            >
              Review Req.
            </button>
          </div>
        </div>
      </div>

      {/* Bento Grid Bottom Row: Domain Breakdown Bento + Quick Workflows Bento */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Bento Tile 6: Compliance Domain Coverage */}
        <div className="col-span-12 md:col-span-6 bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest">
              Compliance Domain Coverage
            </h2>
            <span className="text-[10px] text-gray-400 font-mono">{contract.findings.length} findings mapped</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            {domainsList.map(domain => {
              const count = domainCounts[domain] || 0;
              return (
                <div 
                  key={domain}
                  onClick={() => {
                    setDomainFilter(domain);
                    setActiveTab('findings');
                  }}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-gray-50 hover:bg-blue-50/50 border border-gray-100 hover:border-blue-200 cursor-pointer transition"
                >
                  <span className="text-gray-700 font-medium">{domain}</span>
                  <div className="flex items-center gap-1.5">
                    <span className={`font-mono font-bold text-xs px-1.5 py-0.2 rounded ${
                      count > 0 ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-500'
                    }`}>
                      {count}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bento Tile 7: Next Review Steps / Workflows */}
        <div className="col-span-12 md:col-span-6 bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <h2 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-3">
              Professional Workflows
            </h2>

            <div className="space-y-2">
              <div 
                onClick={() => setActiveTab('comparison')}
                className="p-2.5 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50/30 cursor-pointer transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-xs">
                    <FileSpreadsheet className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-bold text-xs text-gray-900 block">Compare with Vendor Invoice</span>
                    <span className="text-[11px] text-gray-500">Reconcile price, GST, 10% retention, 90d credit</span>
                  </div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition" />
              </div>

              <div 
                onClick={() => setActiveTab('cross-clause')}
                className="p-2.5 rounded-lg border border-gray-200 hover:border-purple-300 hover:bg-purple-50/30 cursor-pointer transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-purple-50 text-purple-600 flex items-center justify-center font-bold text-xs">
                    <GitMerge className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-bold text-xs text-gray-900 block">Cross-Clause 2nd Pass Reasoning</span>
                    <span className="text-[11px] text-gray-500">Discover hidden multi-clause compounding risks</span>
                  </div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-purple-600 group-hover:translate-x-0.5 transition" />
              </div>

              <div 
                onClick={() => setActiveTab('report')}
                className="p-2.5 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50/30 cursor-pointer transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xs">
                    <FileCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-bold text-xs text-gray-900 block">Generate CA Working Paper Report</span>
                    <span className="text-[11px] text-gray-500">15-section audit documentation & export</span>
                  </div>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
