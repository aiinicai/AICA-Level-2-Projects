import React, { useState } from 'react';
import {
  FileSearch,
  Search,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Building,
  DollarSign,
  Settings2,
  CheckCircle2,
  Info,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  Tag,
  AlertCircle,
  Calendar,
  FileCheck,
} from 'lucide-react';
import { RegulatoryUpdate } from '../types';

interface ImpactAnalysisViewProps {
  updates: RegulatoryUpdate[];
  selectedUpdate: RegulatoryUpdate | null;
  setSelectedUpdate: (update: RegulatoryUpdate | null) => void;
  onMatchClientsForUpdate: (update: RegulatoryUpdate) => void;
}

export const ImpactAnalysisView: React.FC<ImpactAnalysisViewProps> = ({
  updates,
  selectedUpdate,
  setSelectedUpdate,
  onMatchClientsForUpdate,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedRisk, setSelectedRisk] = useState<string>('All');

  // Filter updates
  const filteredUpdates = updates.filter((u) => {
    const matchesSearch =
      u.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.keyDevelopment.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.category.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || u.category === selectedCategory;
    const matchesRisk = selectedRisk === 'All' || u.riskLevel === selectedRisk;
    return matchesSearch && matchesCategory && matchesRisk;
  });

  const activeUpdate = selectedUpdate || (filteredUpdates.length > 0 ? filteredUpdates[0] : null);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <FileSearch className="w-4 h-4" />
            <span>CA IMPACT ANALYSIS & VERIFICATION ENGINE</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Regulatory Impact & Fact Verification</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Strict separation of official facts, AI impact interpretation, and CA recommended actions.
          </p>
        </div>
      </div>

      {/* Main Grid: Left List (35%), Right Detailed Analysis (65%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Updates List */}
        <div className="lg:col-span-5 space-y-3">
          {/* Search & Filters */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-2 shadow-xs">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search circulars, GST, TDS, MCA..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:bg-white focus:outline-none"
              />
            </div>

            <div className="flex items-center space-x-2 text-xs overflow-x-auto pb-1">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-slate-50 border border-slate-200 text-slate-700 px-2 py-1 rounded-lg text-xs"
              >
                <option value="All">All Categories</option>
                <option value="GST">GST</option>
                <option value="Income Tax">Income Tax</option>
                <option value="MCA / Companies Act">MCA / Companies Act</option>
                <option value="RBI / Banking">RBI / Banking</option>
                <option value="Forex">Forex & Markets</option>
              </select>

              <select
                value={selectedRisk}
                onChange={(e) => setSelectedRisk(e.target.value)}
                className="bg-slate-50 border border-slate-200 text-slate-700 px-2 py-1 rounded-lg text-xs"
              >
                <option value="All">All Risk Levels</option>
                <option value="Critical">Critical</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
              </select>
            </div>
          </div>

          {/* List Cards */}
          <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
            {filteredUpdates.map((upd) => {
              const isSelected = activeUpdate?.id === upd.id;
              return (
                <div
                  key={upd.id}
                  onClick={() => setSelectedUpdate(upd)}
                  className={`p-3.5 rounded-2xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-teal-50/90 border-teal-500 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="font-bold text-[10px] uppercase text-teal-800 px-2 py-0.5 bg-teal-100 rounded">
                      {upd.category}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        upd.riskLevel === 'Critical'
                          ? 'bg-rose-100 text-rose-700'
                          : upd.riskLevel === 'High'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {upd.riskLevel}
                    </span>
                  </div>

                  <h3 className="font-bold text-slate-900 leading-snug line-clamp-2">{upd.title}</h3>

                  <p className="text-[11px] text-slate-600 mt-1.5 line-clamp-2">{upd.keyDevelopment}</p>

                  <div className="mt-2.5 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-500">
                    <span>Deadline: {upd.dates?.statutoryDeadline || 'Pending'}</span>
                    <span className="font-semibold text-slate-700">Ref: {upd.referenceNo}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Detail Analysis Panel */}
        <div className="lg:col-span-7">
          {activeUpdate ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
              {/* Header Title */}
              <div className="border-b border-slate-100 pb-4">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-3 py-1 bg-teal-700 text-white font-bold text-xs rounded-lg">
                      {activeUpdate.category}
                    </span>
                    <span className="text-xs text-slate-500">{activeUpdate.subCategory}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-slate-600">Verification Score:</span>
                    <span className="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 font-bold text-xs rounded-full">
                      {activeUpdate.confidenceScore}% ({activeUpdate.verificationStatus})
                    </span>
                  </div>
                </div>

                <h2 className="text-lg font-bold text-slate-900 leading-snug">{activeUpdate.title}</h2>

                <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-600">
                  <div>
                    <span className="font-semibold text-slate-800">Source:</span> {activeUpdate.issuingAuthority}
                  </div>
                  <div>
                    <span className="font-semibold text-slate-800">Reference No:</span> {activeUpdate.referenceNo}
                  </div>
                </div>
              </div>

              {/* Warning Notice Callout if Unconfirmed or Demo */}
              {activeUpdate.unconfirmedNotice && (
                <div className="p-3.5 bg-amber-50 border border-amber-300 text-amber-900 rounded-xl text-xs flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span className="font-semibold">{activeUpdate.unconfirmedNotice}</span>
                </div>
              )}

              {/* DATE CLASSIFICATION ENGINE PANEL (Requirement E) */}
              <div className="bg-slate-900 text-white p-4 rounded-xl space-y-2">
                <div className="text-[11px] uppercase font-bold text-teal-400 flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>DATE CLASSIFICATION ENGINE</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                  <div className="bg-slate-800 p-2 rounded-lg">
                    <span className="text-[9px] text-slate-400 uppercase font-bold block">Notification Date</span>
                    <span className="font-mono text-slate-200 font-semibold">{activeUpdate.dates?.notificationDate || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-800 p-2 rounded-lg">
                    <span className="text-[9px] text-slate-400 uppercase font-bold block">Effective Date</span>
                    <span className="font-mono text-emerald-300 font-semibold">{activeUpdate.dates?.effectiveDate || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-800 p-2 rounded-lg">
                    <span className="text-[9px] text-slate-400 uppercase font-bold block">Statutory Deadline</span>
                    <span className="font-mono text-rose-300 font-bold">{activeUpdate.dates?.statutoryDeadline || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-800 p-2 rounded-lg">
                    <span className="text-[9px] text-slate-400 uppercase font-bold block">Internal Action Date</span>
                    <span className="font-mono text-amber-300 font-semibold">{activeUpdate.dates?.recommendedInternalActionDate || 'N/A'}</span>
                  </div>
                  <div className="bg-slate-800 p-2 rounded-lg">
                    <span className="text-[9px] text-slate-400 uppercase font-bold block">Review Date</span>
                    <span className="font-mono text-slate-300 font-semibold">{activeUpdate.dates?.reviewDate || 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* THREE CLEAR SECTIONS: Fact vs AI Analysis vs CA Recommendation */}

              {/* SECTION 1: SOURCE FACTS */}
              <div className="space-y-1.5">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-1.5">
                  <FileCheck className="w-4 h-4 text-teal-600" />
                  <span>1. Official Source Facts (Statutory Content)</span>
                </h3>
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-medium leading-relaxed">
                  {activeUpdate.sourceFacts || activeUpdate.keyDevelopment}
                </div>
              </div>

              {/* SECTION 2: AI IMPACT ANALYSIS */}
              <div className="space-y-1.5">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-1.5">
                  <Info className="w-4 h-4 text-blue-600" />
                  <span>2. AI Impact Analysis (Business, Financial & Compliance Consequences)</span>
                </h3>
                <div className="p-3.5 bg-blue-50/60 border border-blue-200 rounded-xl text-xs text-blue-950 leading-relaxed font-medium">
                  {activeUpdate.aiImpactAnalysisText || activeUpdate.impactAnalysis.financialImpact}
                </div>
              </div>

              {/* SECTION 3: CA RECOMMENDED ACTION */}
              <div className="space-y-1.5">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>3. Recommended Action Plan for Chartered Accountant</span>
                </h3>
                <div className="p-3.5 bg-emerald-50/80 border border-emerald-200 rounded-xl text-xs text-emerald-950 font-bold leading-relaxed whitespace-pre-line">
                  {activeUpdate.caRecommendedAction || activeUpdate.impactAnalysis.recommendedAction}
                </div>
              </div>

              {/* 3 Pillars Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1 text-xs">
                  <span className="font-bold text-slate-900 block">Compliance Requirement</span>
                  <p className="text-[11px] text-slate-600">{activeUpdate.impactAnalysis.complianceImpact}</p>
                </div>
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1 text-xs">
                  <span className="font-bold text-slate-900 block">Financial Exposure</span>
                  <p className="text-[11px] text-slate-600">{activeUpdate.impactAnalysis.financialImpact}</p>
                </div>
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-1 text-xs">
                  <span className="font-bold text-slate-900 block">Operational Alignment</span>
                  <p className="text-[11px] text-slate-600">{activeUpdate.impactAnalysis.operationalImpact}</p>
                </div>
              </div>

              {/* Action Button: Trigger Client Matching */}
              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => onMatchClientsForUpdate(activeUpdate)}
                  className="flex items-center space-x-2 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-md transition-all cursor-pointer"
                >
                  <span>RUN CLIENT MATCHING ENGINE FOR THIS UPDATE</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-20 bg-white border border-slate-200 rounded-2xl">
              <FileSearch className="w-12 h-12 text-slate-300 mx-auto mb-2" />
              <p className="text-slate-500 text-xs">Select an update from the left list to view detailed CA impact analysis.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
