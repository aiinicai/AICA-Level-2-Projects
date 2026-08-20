import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  Sparkles,
  Users,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  ShieldCheck,
  Building2,
  Zap,
  HelpCircle,
  Ban,
  FileCheck,
} from 'lucide-react';
import { RegulatoryUpdate, ClientMaster, ClientMatch } from '../types';
import { matchClientWithUpdate } from '../services/advisoryEngine';

interface ClientMatchingViewProps {
  updates: RegulatoryUpdate[];
  clients: ClientMaster[];
  selectedUpdate: RegulatoryUpdate | null;
  setSelectedUpdate: (update: RegulatoryUpdate | null) => void;
  onGenerateAdvisoryForMatch: (client: ClientMaster, update: RegulatoryUpdate) => void;
  generatedAdvisoriesCount: number;
}

export const ClientMatchingView: React.FC<ClientMatchingViewProps> = ({
  updates,
  clients,
  selectedUpdate,
  setSelectedUpdate,
  onGenerateAdvisoryForMatch,
  generatedAdvisoriesCount,
}) => {
  const activeUpdate = selectedUpdate || (updates.length > 0 ? updates[0] : null);
  const [matches, setMatches] = useState<ClientMatch[]>([]);
  const [generatedIds, setGeneratedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (activeUpdate && clients.length > 0) {
      const computedMatches = clients.map((cli) => matchClientWithUpdate(cli, activeUpdate));
      setMatches(computedMatches);
    }
  }, [activeUpdate, clients]);

  const handleGenerate = (client: ClientMaster, update: RegulatoryUpdate) => {
    onGenerateAdvisoryForMatch(client, update);
    setGeneratedIds((prev) => new Set(prev).add(`${update.id}_${client.id}`));
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <GitCompare className="w-4 h-4" />
            <span>MODULE 6 — CLIENT MATCHING ENGINE V2</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">Deterministic Client Impact Matrix</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Hard exclusion rules, missing data detection, and selective advisory generation control.
          </p>
        </div>
      </div>

      {/* Select Update Dropdown Box */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-3">
        <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide">
          Select Regulatory / Market Update to Match Against Clients:
        </label>
        <select
          value={activeUpdate?.id || ''}
          onChange={(e) => {
            const found = updates.find((u) => u.id === e.target.value);
            if (found) setSelectedUpdate(found);
          }}
          className="w-full p-3 bg-slate-50 border border-slate-300 rounded-xl font-bold text-xs text-slate-900 focus:bg-white focus:outline-none focus:border-teal-500"
        >
          {updates.map((upd) => (
            <option key={upd.id} value={upd.id}>
              [{upd.category}] {upd.title} ({upd.issuingAuthority})
            </option>
          ))}
        </select>

        {activeUpdate && (
          <div className="p-3 bg-teal-50/60 border border-teal-200/80 rounded-xl text-xs flex items-center justify-between">
            <div>
              <span className="font-bold text-teal-950">Active Development:</span>{' '}
              <span className="text-teal-900">{activeUpdate.keyDevelopment}</span>
            </div>
            <span className="px-2.5 py-0.5 bg-teal-700 text-white font-bold rounded-md text-[10px] shrink-0">
              {activeUpdate.riskLevel} Risk
            </span>
          </div>
        )}
      </div>

      {/* Matches Matrix List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
            <Users className="w-4 h-4 text-teal-600" />
            <span>Client Match Evaluation Results ({matches.length} Clients Evaluated)</span>
          </h2>
          <span className="text-xs text-slate-500 font-semibold">
            Selective Generation: Only generated advisories enter Approval Centre
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {matches.map((m) => {
            const clientObj = clients.find((c) => c.id === m.clientId);
            const isActionRequired = m.relevanceStatus === 'MATCHED / ACTION REQUIRED' || m.relevanceStatus === 'Highly Relevant' || m.relevanceStatus === 'Relevant';
            const isAlreadyComplied = m.relevanceStatus === 'MATCHED / ALREADY COMPLIED';
            const isDataVerificationRequired = m.relevanceStatus === 'POSSIBLY RELEVANT — DATA VERIFICATION REQUIRED' || m.relevanceStatus === 'Possibly Relevant';
            const isNotApplicable = m.relevanceStatus === 'NOT APPLICABLE' || m.relevanceStatus === 'Not Applicable';
            const canGenerate = m.canGenerateAdvisory ?? isActionRequired;
            const isGenerated = activeUpdate && clientObj && generatedIds.has(`${activeUpdate.id}_${clientObj.id}`);

            return (
              <div
                key={m.id}
                className={`bg-white border rounded-2xl p-5 shadow-xs flex flex-col justify-between transition-all ${
                  isActionRequired
                    ? 'border-emerald-500 ring-1 ring-emerald-100 bg-emerald-50/10'
                    : isAlreadyComplied
                    ? 'border-sky-400 bg-sky-50/20'
                    : isNotApplicable
                    ? 'border-slate-200 bg-slate-50/60 opacity-80'
                    : 'border-amber-400 bg-amber-50/20'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">{m.clientName}</h3>
                      <p className="text-xs text-slate-500">
                        {clientObj?.entityType} • {clientObj?.industry} • Turnover: {clientObj?.annualTurnoverRange}
                      </p>
                    </div>

                    <span
                      className={`text-[10px] font-extrabold px-3 py-1 rounded-full text-center ${
                        isActionRequired
                          ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                          : isAlreadyComplied
                          ? 'bg-sky-100 text-sky-900 border border-sky-300'
                          : isDataVerificationRequired
                          ? 'bg-amber-100 text-amber-900 border border-amber-300'
                          : 'bg-slate-200 text-slate-700 border border-slate-300'
                      }`}
                    >
                      {m.relevanceStatus} ({m.relevanceScore}%)
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-100 rounded-full h-2 mb-3 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        isActionRequired
                          ? 'bg-emerald-500'
                          : isAlreadyComplied
                          ? 'bg-sky-500'
                          : isDataVerificationRequired
                          ? 'bg-amber-500'
                          : 'bg-slate-300'
                      }`}
                      style={{ width: `${m.relevanceScore}%` }}
                    />
                  </div>

                  {/* Match Reasons */}
                  <div className="space-y-2 text-xs">
                    {m.matchReasons.length > 0 && (
                      <div>
                        <div className="font-bold text-slate-800 flex items-center space-x-1">
                          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                          <span>Match Evaluation Findings:</span>
                        </div>
                        <ul className="space-y-1 pl-4 list-disc text-slate-700 leading-relaxed text-[11px] mt-1">
                          {m.matchReasons.map((r, idx) => (
                            <li key={idx}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Exclusion Reasons */}
                    {m.exclusionReasons.length > 0 && (
                      <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-900 text-[11px]">
                        <div className="font-bold flex items-center space-x-1">
                          <Ban className="w-3.5 h-3.5 text-rose-600" />
                          <span>Hard Statutory Exclusion Applied:</span>
                        </div>
                        <ul className="list-disc pl-4 mt-0.5 space-y-0.5">
                          {m.exclusionReasons.map((er, idx) => (
                            <li key={idx}>{er}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Missing Information Panel */}
                    {m.missingInformation.length > 0 && (
                      <div className="p-3 bg-amber-50 border border-amber-300 rounded-xl text-amber-950 text-[11px] space-y-1">
                        <div className="font-bold flex items-center space-x-1 text-amber-900">
                          <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                          <span>Client Master Data Insufficient for Deterministic Matching:</span>
                        </div>
                        <p className="text-[10px] text-amber-800">
                          The following required compliance profile fields are missing or unverified:
                        </p>
                        <ul className="list-none space-y-0.5 pl-1 font-mono text-[10px] text-amber-900">
                          {m.missingInformation.map((mi, idx) => (
                            <li key={idx} className="font-semibold">{mi}</li>
                          ))}
                        </ul>
                        <p className="text-[10px] font-bold text-amber-900 pt-1">
                          Action Required: Update Client Master in Module 5 before generating client advisory.
                        </p>
                      </div>
                    )}

                    <div className="pt-2">
                      <span className="font-semibold text-slate-700">Recommended Next Step:</span>{' '}
                      <span className="text-slate-600 text-[11px] font-medium">{m.recommendedNextStep}</span>
                    </div>
                  </div>
                </div>

                {/* Generate Advisory Action */}
                <div className="mt-4 pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <span className="text-[10px] text-slate-400 italic">
                    {m.needForProfessionalReview}
                  </span>

                  {clientObj && activeUpdate && (
                    <button
                      onClick={() => handleGenerate(clientObj, activeUpdate)}
                      disabled={isGenerated || !canGenerate}
                      className={`flex items-center justify-center space-x-1.5 font-bold text-xs px-4 py-2 rounded-xl transition-all cursor-pointer shrink-0 ${
                        isGenerated
                          ? 'bg-emerald-600 text-white shadow-xs'
                          : !canGenerate
                          ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed opacity-70'
                          : 'bg-teal-600 hover:bg-teal-700 text-white shadow-md'
                      }`}
                      title={!canGenerate ? 'Advisory generation disabled for this match status' : 'Generate Advisory'}
                    >
                      {isGenerated ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>ADVISORY SENT TO APPROVAL CENTRE</span>
                        </>
                      ) : !canGenerate ? (
                        <>
                          <AlertCircle className="w-3.5 h-3.5" />
                          <span>ADVISORY DISABLED</span>
                        </>
                      ) : (
                        <>
                          <Zap className="w-3.5 h-3.5" />
                          <span>GENERATE ADVISORY</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
