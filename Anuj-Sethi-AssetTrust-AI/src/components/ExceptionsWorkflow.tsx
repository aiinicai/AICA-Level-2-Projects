import React, { useState } from 'react';
import { 
  Workflow, 
  ArrowRight, 
  ShieldCheck, 
  History, 
  FileCheck2, 
  X 
} from 'lucide-react';
import { RiskFinding, ExceptionWorkflowStage, AuditTrailEntry } from '../types';
import { formatINR } from '../services/reliabilityScore';

interface ExceptionsWorkflowProps {
  risks: RiskFinding[];
  setRisks: React.Dispatch<React.SetStateAction<RiskFinding[]>>;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onNavigateToAsset: (assetId: string) => void;
  targetRiskId?: string | null;
}

const STAGES: ExceptionWorkflowStage[] = [
  'Detected',
  'Assigned',
  'Investigating',
  'Management Review',
  'Approved',
  'Closed'
];

export const ExceptionsWorkflow: React.FC<ExceptionsWorkflowProps> = ({
  risks,
  setRisks,
  currencyMode,
  onNavigateToAsset,
  targetRiskId
}) => {
  const [selectedRisk, setSelectedRisk] = useState<RiskFinding | null>(
    (targetRiskId ? risks.find((r) => r.id === targetRiskId) : null) || risks[0] || null
  );

  // Transition / Sign-Off Modal State
  const [showSignOffModal, setShowSignOffModal] = useState(false);
  const [nextStage, setNextStage] = useState<ExceptionWorkflowStage>('Investigating');
  const [actionUser, setActionUser] = useState('Pooja Iyer (Lead Controller)');
  const [actionRemarks, setActionRemarks] = useState('Field reconciliation complete; verified supporting documents.');

  const handleAdvanceStage = (risk: RiskFinding, targetStage: ExceptionWorkflowStage) => {
    setSelectedRisk(risk);
    setNextStage(targetStage);
    setShowSignOffModal(true);
  };

  const handleConfirmTransition = () => {
    if (!selectedRisk) return;

    const newAuditEntry: AuditTrailEntry = {
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 16),
      user: actionUser,
      action: `Moved to ${nextStage}`,
      note: actionRemarks
    };

    const updatedRisk: RiskFinding = {
      ...selectedRisk,
      status: nextStage,
      updatedDate: new Date().toISOString().split('T')[0],
      auditTrail: [newAuditEntry, ...(selectedRisk.auditTrail || [])]
    };

    setRisks((prev) => prev.map((r) => (r.id === selectedRisk.id ? updatedRisk : r)));
    setSelectedRisk(updatedRisk);
    setShowSignOffModal(false);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
            <Workflow className="w-4 h-4 text-blue-600" />
            <span>Formal Internal Control Governance Pipeline</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            Exception Remediation & Audit Sign-Off Workflow
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Strict 6-stage lifecycle tracking with mandatory sign-offs and immutable audit trails for every control discrepancy.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-slate-50 px-4 py-2 rounded-xl border border-slate-200 text-xs">
          <span className="text-slate-500 font-medium">Total Open Breaches:</span>
          <span className="font-bold text-rose-600 font-mono">
            {risks.filter((r) => r.status !== 'Closed').length} Active
          </span>
        </div>
      </div>

      {/* 6-Stage Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {STAGES.map((stage, sIdx) => {
          const stageRisks = risks.filter((r) => r.status === stage);
          return (
            <div key={stage} className="bg-white border border-slate-200 rounded-xl p-3.5 flex flex-col min-h-[420px] shadow-2xs">
              {/* Stage Header */}
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100 mb-3">
                <div className="flex items-center space-x-1.5">
                  <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold flex items-center justify-center border border-slate-200">
                    {sIdx + 1}
                  </span>
                  <h3 className="text-xs font-bold text-slate-800 truncate" title={stage}>
                    {stage}
                  </h3>
                </div>
                <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200">
                  {stageRisks.length}
                </span>
              </div>

              {/* Cards inside Column */}
              <div className="space-y-2.5 flex-1 overflow-y-auto pr-0.5">
                {stageRisks.map((risk) => (
                  <div
                    key={risk.id}
                    onClick={() => setSelectedRisk(risk)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer text-xs space-y-2 ${
                      selectedRisk?.id === risk.id
                        ? 'bg-blue-50/70 border-blue-500 shadow-sm ring-1 ring-blue-500/20'
                        : 'bg-slate-50 border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold text-blue-700">
                        {risk.assetId}
                      </span>
                      <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                        risk.severity === 'Critical' ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {risk.severity}
                      </span>
                    </div>

                    <h4 className="font-semibold text-slate-900 line-clamp-2 leading-tight" title={risk.title}>
                      {risk.title}
                    </h4>

                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-200 font-mono">
                      <span>{formatINR(risk.financialExposureINR, currencyMode)}</span>
                      <span>{risk.updatedDate.slice(5)}</span>
                    </div>

                    {/* Quick Move Button */}
                    {sIdx < STAGES.length - 1 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAdvanceStage(risk, STAGES[sIdx + 1]);
                        }}
                        className="w-full py-1 px-2 rounded-lg bg-white hover:bg-slate-900 text-slate-700 hover:text-white border border-slate-200 text-[10px] font-semibold flex items-center justify-center space-x-1 transition-all shadow-2xs"
                      >
                        <span>Move → {STAGES[sIdx + 1]}</span>
                      </button>
                    )}
                  </div>
                ))}

                {stageRisks.length === 0 && (
                  <div className="h-32 border border-dashed border-slate-200 rounded-xl flex items-center justify-center text-slate-400 text-[11px]">
                    No items
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Exception Dossier & Immutable Audit Trail */}
      {selectedRisk && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-100 gap-3">
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                  {selectedRisk.id}
                </span>
                <span className="text-xs font-mono text-slate-500">
                  Asset: {selectedRisk.assetId} ({selectedRisk.location})
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                  Current Stage: {selectedRisk.status}
                </span>
              </div>
              <h2 className="text-lg font-bold text-slate-900 mt-1">
                {selectedRisk.title}
              </h2>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => onNavigateToAsset(selectedRisk.assetId)}
                className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
              >
                View Asset Master
              </button>

              <button
                onClick={() => {
                  const currIdx = STAGES.indexOf(selectedRisk.status);
                  const next = currIdx < STAGES.length - 1 ? STAGES[currIdx + 1] : 'Closed';
                  handleAdvanceStage(selectedRisk, next);
                }}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-lg flex items-center space-x-2 transition-all shadow-xs"
              >
                <span>Advance Governance Stage</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Details & Remediation Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
              <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                Exception Root-Cause & Exposure
              </span>
              <p className="text-slate-700 leading-relaxed">{selectedRisk.explanation}</p>
              <div className="pt-2 border-t border-slate-200 flex justify-between font-mono text-[11px]">
                <span className="text-slate-500">Exposure:</span>
                <span className="text-rose-600 font-bold">{formatINR(selectedRisk.financialExposureINR, currencyMode)}</span>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
              <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                Required Corrective Action
              </span>
              <p className="text-slate-700 leading-relaxed">{selectedRisk.recommendedAction}</p>
              <div className="pt-2 border-t border-slate-200 flex justify-between text-[11px]">
                <span className="text-slate-500">Assigned Lead:</span>
                <span className="text-slate-900 font-semibold">{selectedRisk.owner}</span>
              </div>
            </div>
          </div>

          {/* Immutable Audit Trail Timeline */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-1.5">
              <History className="w-4 h-4 text-blue-600" />
              <span>Immutable Governance Audit Trail ({selectedRisk.auditTrail?.length || 0} Actions)</span>
            </h4>

            <div className="space-y-2.5">
              {selectedRisk.auditTrail?.map((trail, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-lg p-3 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-blue-700">{trail.action}</span>
                      <span className="text-slate-500">• by <strong className="text-slate-800">{trail.user}</strong></span>
                    </div>
                    <p className="text-slate-600 text-[11px]">{trail.note}</p>
                  </div>
                  <span className="font-mono text-[11px] text-slate-400 shrink-0">
                    {trail.timestamp}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Transition & Sign-Off Modal */}
      {showSignOffModal && selectedRisk && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4 text-slate-800 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <FileCheck2 className="w-4 h-4 text-blue-600" />
                <span>Governance Sign-Off: Advance Stage</span>
              </h3>
              <button onClick={() => setShowSignOffModal(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                <span className="text-slate-500 text-[11px] block font-semibold">Exception Target:</span>
                <span className="font-bold text-slate-900 block mt-0.5">{selectedRisk.title}</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-700 block mb-1 font-semibold">Target Stage:</label>
                  <select
                    value={nextStage}
                    onChange={(e) => setNextStage(e.target.value as ExceptionWorkflowStage)}
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
                  >
                    {STAGES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-slate-700 block mb-1 font-semibold">Signing Officer:</label>
                  <input
                    type="text"
                    value={actionUser}
                    onChange={(e) => setActionUser(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 shadow-2xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-700 block mb-1 font-semibold">Audit Sign-Off Remarks / Justification:</label>
                <textarea
                  value={actionRemarks}
                  onChange={(e) => setActionRemarks(e.target.value)}
                  rows={3}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-200">
              <button
                onClick={() => setShowSignOffModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmTransition}
                className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold flex items-center space-x-2 shadow-xs"
              >
                <ShieldCheck className="w-4 h-4 text-blue-400" />
                <span>Sign & Advance Stage</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
