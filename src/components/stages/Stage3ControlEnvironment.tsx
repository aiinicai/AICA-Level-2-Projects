import React from 'react';
import { EngagementData, ControlEnvironmentFactor } from '../../types';
import { ShieldCheck, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

interface Stage3Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage3ControlEnvironment: React.FC<Stage3Props> = ({
  engagement,
  onChange,
}) => {
  const updateFactor = (id: string, updates: Partial<ControlEnvironmentFactor>) => {
    const updatedFactors = engagement.controlEnvironment.factors.map((f) =>
      f.id === id ? { ...f, ...updates } : f
    );
    onChange({
      ...engagement,
      controlEnvironment: {
        ...engagement.controlEnvironment,
        factors: updatedFactors,
      },
    });
  };

  const updateOverall = (
    conclusion: EngagementData['controlEnvironment']['overallConclusion'],
    notes: string
  ) => {
    onChange({
      ...engagement,
      controlEnvironment: {
        ...engagement.controlEnvironment,
        overallConclusion: conclusion,
        overallNotes: notes,
      },
    });
  };

  const effectiveCount = engagement.controlEnvironment.factors.filter((f) => f.rating === 'Effective').length;
  const partialCount = engagement.controlEnvironment.factors.filter((f) => f.rating === 'Partially Effective').length;
  const ineffectiveCount = engagement.controlEnvironment.factors.filter((f) => f.rating === 'Ineffective').length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 03 • SA 315 (Revised)
          </span>
          <span className="text-xs text-stone-500">Para 14: Control Environment</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Control Environment Evaluation
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Evaluate the governance and management attitudes, awareness, and actions concerning internal control and its importance in the entity.
        </p>
      </div>

      {/* Factors Table */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
            8 Standard Control Environment Factors
          </h3>
          <div className="flex items-center gap-2 text-xs font-medium">
            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
              {effectiveCount} Effective
            </span>
            <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              {partialCount} Partially Effective
            </span>
            {ineffectiveCount > 0 && (
              <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">
                {ineffectiveCount} Ineffective
              </span>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#1a2027] text-stone-600 dark:text-stone-400">
                <th className="py-2.5 px-3 font-semibold w-10">#</th>
                <th className="py-2.5 px-3 font-semibold w-1/3">Factor & Description</th>
                <th className="py-2.5 px-3 font-semibold w-48 text-center">Operating Rating</th>
                <th className="py-2.5 px-3 font-semibold">Auditor Observations & Evidence Inspected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
              {engagement.controlEnvironment.factors.map((factor, idx) => (
                <tr key={factor.id} className="hover:bg-stone-50/50 dark:hover:bg-[#191e25]">
                  <td className="py-3 px-3 font-mono-num text-stone-400 font-semibold align-top">
                    {idx + 1}
                  </td>
                  <td className="py-3 px-3 align-top">
                    <p className="font-semibold text-stone-900 dark:text-stone-100">
                      {factor.factorName}
                    </p>
                    <p className="text-[11px] text-stone-500 dark:text-stone-400 mt-0.5 leading-snug">
                      {factor.description}
                    </p>
                  </td>
                  <td className="py-3 px-3 align-top text-center">
                    <div className="inline-flex rounded-md shadow-xs" role="group">
                      {(['Effective', 'Partially Effective', 'Ineffective'] as const).map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => updateFactor(factor.id, { rating: opt })}
                          className={`px-2 py-1 text-[11px] font-semibold border first:rounded-l-md last:rounded-r-md transition-colors ${
                            factor.rating === opt
                              ? opt === 'Effective'
                                ? 'bg-emerald-700 text-white border-emerald-700 dark:bg-emerald-600'
                                : opt === 'Partially Effective'
                                ? 'bg-amber-600 text-white border-amber-600'
                                : 'bg-rose-700 text-white border-rose-700 dark:bg-rose-600'
                              : 'bg-white dark:bg-[#1a2027] text-stone-700 dark:text-stone-300 border-stone-300 dark:border-stone-700 hover:bg-stone-100 dark:hover:bg-stone-800'
                          }`}
                        >
                          {opt === 'Partially Effective' ? 'Partial' : opt}
                        </button>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 align-top">
                    <textarea
                      rows={2}
                      value={factor.notes}
                      onChange={(e) => updateFactor(factor.id, { notes: e.target.value })}
                      placeholder="Note specific governance evidence, committee minutes, or observations..."
                      className="w-full px-2.5 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs focus:border-amber-700"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Overall Conclusion Card */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
          Overall Control Environment Conclusion (SA 315 Para 14)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Synthesized Assessment *
            </label>
            <select
              value={engagement.controlEnvironment.overallConclusion}
              onChange={(e) => updateOverall(e.target.value as any, engagement.controlEnvironment.overallNotes)}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-semibold focus:border-amber-700"
            >
              <option value="Effective">Effective (Provides appropriate foundation)</option>
              <option value="Partially Deficient">Partially Deficient (Compensating substantive tests required)</option>
              <option value="Ineffective / High Risk">Ineffective / High Risk (Substantive-only audit response)</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Overall Evaluation Justification & Impact on Audit Strategy
            </label>
            <textarea
              rows={3}
              value={engagement.controlEnvironment.overallNotes}
              onChange={(e) => updateOverall(engagement.controlEnvironment.overallConclusion, e.target.value)}
              placeholder="State how the control environment influences the nature, timing and extent of audit procedures..."
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs focus:border-amber-700"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
