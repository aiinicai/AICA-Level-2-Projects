import React from 'react';
import { EngagementData, AuditStrategyResponse, RiskLevel } from '../../types';
import { Compass, AlertTriangle, ShieldCheck, CheckCircle2, FileText } from 'lucide-react';

interface Stage11Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage11AuditStrategy: React.FC<Stage11Props> = ({
  engagement,
  onChange,
}) => {
  const updateStrategy = (id: string, updates: Partial<AuditStrategyResponse>) => {
    const updated = engagement.auditStrategy.map((s) =>
      s.id === id ? { ...s, ...updates } : s
    );
    onChange({ ...engagement, auditStrategy: updated });
  };

  // Check SA 330 rule violations: Significant risk without TOD!
  const violations = engagement.auditStrategy.filter(
    (s) => s.assessedRiskLevel === 'Significant' && !s.testOfDetails
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 11 • SA 330
          </span>
          <span className="text-xs text-stone-500">The Auditor's Responses to Assessed Risks</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Overall Audit Strategy & Assertion-Level Audit Responses
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Formulate the nature, timing, and extent of further audit procedures (TOC, SAP, and TOD) responsive to assessed risks of material misstatement at the assertion level.
        </p>
      </div>

      {/* SA 330 Mandatory Rule Banner */}
      {violations.length > 0 ? (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-300 dark:border-rose-800 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-700 dark:text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-bold text-rose-900 dark:text-rose-200">
              SA 330 Para 18 Compliance Alert: Missing Tests of Details (TOD)
            </p>
            <p className="text-rose-800 dark:text-rose-300 leading-relaxed">
              Standard on Auditing 330 Para 18 dictates: <em>"If the auditor has determined that an assessed risk is a significant risk, the auditor shall perform substantive procedures that include tests of details."</em>
            </p>
            <p className="text-rose-900 dark:text-rose-200 font-semibold">
              The following {violations.length} significant risk(s) currently lack TOD: {violations.map((v) => v.lineItemOrRisk).join(', ')}.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2.5 text-xs text-emerald-900 dark:text-emerald-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>
            <strong>SA 330 Compliance Validated:</strong> All identified significant risks include responsive Tests of Details (TOD).
          </span>
        </div>
      )}

      {/* Audit Strategy Cards */}
      <div className="space-y-4">
        {engagement.auditStrategy.map((strat, idx) => {
          const isSignificant = strat.assessedRiskLevel === 'Significant';
          const missingTodOnSignificant = isSignificant && !strat.testOfDetails;

          return (
            <div
              key={strat.id}
              className={`bg-white dark:bg-[#15191f] rounded-xl border transition-all p-5 shadow-xs space-y-4 ${
                missingTodOnSignificant
                  ? 'border-rose-300 dark:border-rose-800 bg-rose-50/10'
                  : 'border-[#dedbd2] dark:border-[#272f38]'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-stone-200 dark:border-stone-800">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono-num text-xs font-bold text-stone-400 w-5">
                    {idx + 1}.
                  </span>
                  <div>
                    <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                      {strat.lineItemOrRisk}
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                      strat.assessedRiskLevel === 'Significant'
                        ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                        : strat.assessedRiskLevel === 'Moderate'
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                        : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                    }`}
                  >
                    {strat.assessedRiskLevel} Risk
                  </span>
                </div>
              </div>

              {/* Procedure Type Checkboxes (TOC / SAP / TOD) */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* TOC */}
                <label className="flex items-center gap-2.5 p-3 rounded-lg border border-stone-200 dark:border-stone-800 bg-stone-50/60 dark:bg-[#1a2027] cursor-pointer hover:border-amber-700 select-none">
                  <input
                    type="checkbox"
                    checked={strat.testOfControls}
                    onChange={(e) => updateStrategy(strat.id, { testOfControls: e.target.checked })}
                    className="w-4 h-4 rounded text-amber-800 focus:ring-amber-700"
                  />
                  <div>
                    <span className="text-xs font-bold text-stone-900 dark:text-stone-100 block">
                      Tests of Controls (TOC)
                    </span>
                    <span className="text-[10px] text-stone-500">Operating effectiveness (SA 330.8)</span>
                  </div>
                </label>

                {/* SAP */}
                <label className="flex items-center gap-2.5 p-3 rounded-lg border border-stone-200 dark:border-stone-800 bg-stone-50/60 dark:bg-[#1a2027] cursor-pointer hover:border-amber-700 select-none">
                  <input
                    type="checkbox"
                    checked={strat.analyticalProcedures}
                    onChange={(e) => updateStrategy(strat.id, { analyticalProcedures: e.target.checked })}
                    className="w-4 h-4 rounded text-amber-800 focus:ring-amber-700"
                  />
                  <div>
                    <span className="text-xs font-bold text-stone-900 dark:text-stone-100 block">
                      Substantive Analytics (SAP)
                    </span>
                    <span className="text-[10px] text-stone-500">Plausible relationships (SA 520)</span>
                  </div>
                </label>

                {/* TOD */}
                <label
                  className={`flex items-center gap-2.5 p-3 rounded-lg border cursor-pointer select-none transition-colors ${
                    missingTodOnSignificant
                      ? 'border-rose-400 bg-rose-50/50 dark:bg-rose-950/30'
                      : 'border-stone-200 dark:border-stone-800 bg-stone-50/60 dark:bg-[#1a2027] hover:border-amber-700'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={strat.testOfDetails}
                    onChange={(e) => updateStrategy(strat.id, { testOfDetails: e.target.checked })}
                    className="w-4 h-4 rounded text-amber-800 focus:ring-amber-700"
                  />
                  <div>
                    <span className="text-xs font-bold text-stone-900 dark:text-stone-100 block flex items-center gap-1.5">
                      <span>Tests of Details (TOD)</span>
                      {isSignificant && (
                        <span className="text-[9px] px-1 py-0.2 rounded bg-rose-200 text-rose-900 dark:bg-rose-900 dark:text-rose-200 uppercase font-bold">
                          Mandatory
                        </span>
                      )}
                    </span>
                    <span className="text-[10px] text-stone-500">Vouching & external confirms (SA 330.18)</span>
                  </div>
                </label>
              </div>

              {/* Timing, Extent & Detailed Procedures Notes */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                    Timing of Procedures
                  </label>
                  <select
                    value={strat.timing}
                    onChange={(e) => updateStrategy(strat.id, { timing: e.target.value as any })}
                    className="w-full px-2.5 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                  >
                    <option value="Year-End Only">Year-End Only</option>
                    <option value="Interim + Year-End Roll-Forward">Interim + Year-End Roll-Forward</option>
                    <option value="Continuous Throughout Year">Continuous Throughout Year</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                    Extent & Sampling Methodology
                  </label>
                  <select
                    value={strat.extent}
                    onChange={(e) => updateStrategy(strat.id, { extent: e.target.value as any })}
                    className="w-full px-2.5 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                  >
                    <option value="Representative Sampling (SA 530)">Representative Sampling (SA 530)</option>
                    <option value="High-Value Key Items (> PM)">High-Value Key Items (&gt; PM)</option>
                    <option value="100% Examination of Population">100% Examination of Population</option>
                    <option value="Analytical Comparison Only">Analytical Comparison Only</option>
                  </select>
                </div>

                <div className="md:col-span-3">
                  <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                    Detailed Planned Audit Procedures Responsive to the Assessed Risk
                  </label>
                  <textarea
                    rows={2}
                    value={strat.proceduresNotes}
                    onChange={(e) => updateStrategy(strat.id, { proceduresNotes: e.target.value })}
                    placeholder="Document specific vouching procedures, confirmation requests, analytical tests..."
                    className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs focus:border-amber-700"
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
