import React from 'react';
import {
  EngagementData,
  ControlRiskEntry,
  ProbabilityLevel,
  MagnitudeLevel,
  RiskLevel,
} from '../../types';
import { combineRisk } from '../../utils/calculations';
import { SlidersHorizontal, AlertTriangle, Plus, Trash2, CheckCircle2 } from 'lucide-react';

interface Stage9Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage9ControlRiskRegister: React.FC<Stage9Props> = ({
  engagement,
  onChange,
}) => {
  const updateRisk = (id: string, updates: Partial<ControlRiskEntry>) => {
    const updated = engagement.controlRiskRegister.map((r) => {
      if (r.id !== id) return r;

      const merged = { ...r, ...updates };

      // Re-evaluate suggested rating if prob or mag changes
      if ('probability' in updates || 'magnitude' in updates) {
        merged.suggestedRating = combineRisk(merged.probability, merged.magnitude);
        if (!merged.isOverridden) {
          merged.finalRating = merged.suggestedRating;
        }
      }

      // Check if overridden
      merged.isOverridden = merged.finalRating !== merged.suggestedRating;

      return merged;
    });

    onChange({ ...engagement, controlRiskRegister: updated });
  };

  const addRisk = () => {
    const newEntry: ControlRiskEntry = {
      id: `cr-${Date.now()}`,
      lineItemOrProcess: 'New Identified Accounting Process / Item',
      inherentRisk: 'Moderate',
      controlDesign: 'Effective',
      controlOperatingEffectiveness: 'Operating Effectively',
      probability: 'Moderate',
      magnitude: 'Moderate',
      suggestedRating: 'Moderate',
      finalRating: 'Moderate',
      isOverridden: false,
      overrideRationale: '',
      associatedControls: 'Automated 3-way match, system authorization check',
    };
    onChange({ ...engagement, controlRiskRegister: [...engagement.controlRiskRegister, newEntry] });
  };

  const removeRisk = (id: string) => {
    onChange({
      ...engagement,
      controlRiskRegister: engagement.controlRiskRegister.filter((r) => r.id !== id),
    });
  };

  const overriddenCount = engagement.controlRiskRegister.filter((r) => r.isOverridden).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 09 • SA 315 (Revised)
          </span>
          <span className="text-xs text-stone-500">Para 27 & 28: Spectrum of Inherent Risk & Control Risk</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Control Risk Register & Combined 3x3 Risk Matrix
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Combine assessed likelihood (probability) and magnitude of potential misstatement across the 3x3 matrix to establish the final assessed risk of material misstatement.
        </p>
      </div>

      {/* 3x3 Risk Matrix Visual Reference Card */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-3">
        <h3 className="font-serif font-bold text-sm text-stone-900 dark:text-stone-100 flex items-center justify-between">
          <span>Standard ICAI 3x3 Combined Risk Matrix</span>
          <span className="text-xs font-normal text-stone-500">
            Score = Probability (0-2) + Magnitude (0-2)
          </span>
        </h3>

        <div className="overflow-x-auto">
          <div className="min-w-[450px] grid grid-cols-4 gap-2 text-center text-xs">
            <div className="p-2 font-semibold text-stone-500">Prob \ Mag</div>
            <div className="p-2 font-semibold text-stone-600 dark:text-stone-400 bg-stone-50 dark:bg-[#1a2027] rounded">
              Low Magnitude (0)
            </div>
            <div className="p-2 font-semibold text-stone-600 dark:text-stone-400 bg-stone-50 dark:bg-[#1a2027] rounded">
              Moderate Magnitude (1)
            </div>
            <div className="p-2 font-semibold text-stone-600 dark:text-stone-400 bg-stone-50 dark:bg-[#1a2027] rounded">
              High Magnitude (2)
            </div>

            {/* Row: High Prob */}
            <div className="p-2 font-semibold text-stone-600 dark:text-stone-400 bg-stone-50 dark:bg-[#1a2027] rounded flex items-center justify-center">
              High Prob (2)
            </div>
            <div className="p-2.5 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-800 font-bold">
              Moderate (2)
            </div>
            <div className="p-2.5 rounded bg-rose-100 dark:bg-rose-950/60 text-rose-900 dark:text-rose-200 border border-rose-300 dark:border-rose-800 font-bold">
              Significant (3)
            </div>
            <div className="p-2.5 rounded bg-rose-200 dark:bg-rose-900/60 text-rose-950 dark:text-rose-100 border border-rose-400 dark:border-rose-700 font-bold">
              Significant (4)
            </div>

            {/* Row: Moderate Prob */}
            <div className="p-2 font-semibold text-stone-600 dark:text-stone-400 bg-stone-50 dark:bg-[#1a2027] rounded flex items-center justify-center">
              Moderate Prob (1)
            </div>
            <div className="p-2.5 rounded bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold">
              Low (1)
            </div>
            <div className="p-2.5 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-800 font-bold">
              Moderate (2)
            </div>
            <div className="p-2.5 rounded bg-rose-100 dark:bg-rose-950/60 text-rose-900 dark:text-rose-200 border border-rose-300 dark:border-rose-800 font-bold">
              Significant (3)
            </div>

            {/* Row: Low Prob */}
            <div className="p-2 font-semibold text-stone-600 dark:text-stone-400 bg-stone-50 dark:bg-[#1a2027] rounded flex items-center justify-center">
              Low Prob (0)
            </div>
            <div className="p-2.5 rounded bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold">
              Low (0)
            </div>
            <div className="p-2.5 rounded bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold">
              Low (1)
            </div>
            <div className="p-2.5 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border border-amber-300 dark:border-amber-800 font-bold">
              Moderate (2)
            </div>
          </div>
        </div>
      </div>

      {/* Control Risk Register Table */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
              Control Risk & Combined RMM Assessment
            </h3>
            {overriddenCount > 0 && (
              <p className="text-xs text-amber-700 dark:text-amber-400 font-semibold mt-0.5 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>{overriddenCount} auditor override(s) active with documented justification</span>
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={addRisk}
            className="px-3 py-1.5 rounded-md bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 hover:bg-stone-800 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs self-start"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Register Entry</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#1a2027] text-stone-600 dark:text-stone-400">
                <th className="py-2.5 px-2.5 font-semibold w-1/5">Line Item / Business Cycle</th>
                <th className="py-2.5 px-2 font-semibold w-24">Inherent Risk</th>
                <th className="py-2.5 px-2 font-semibold w-28">Control Design</th>
                <th className="py-2.5 px-2 font-semibold w-28">Operating Eff.</th>
                <th className="py-2.5 px-2 font-semibold w-24">Probability</th>
                <th className="py-2.5 px-2 font-semibold w-24">Magnitude</th>
                <th className="py-2.5 px-2 font-semibold w-24 text-center">Suggested</th>
                <th className="py-2.5 px-2 font-semibold w-28 text-center">Final Rating</th>
                <th className="py-2.5 px-2 font-semibold">Override Rationale / Controls</th>
                <th className="py-2.5 px-1 font-semibold w-8 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
              {engagement.controlRiskRegister.map((cr) => {
                const isOverridden = cr.finalRating !== cr.suggestedRating;
                return (
                  <tr key={cr.id} className="hover:bg-stone-50/50 dark:hover:bg-[#191e25]">
                    <td className="py-2.5 px-2.5 align-top">
                      <input
                        type="text"
                        value={cr.lineItemOrProcess}
                        onChange={(e) => updateRisk(cr.id, { lineItemOrProcess: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium"
                      />
                    </td>
                    <td className="py-2.5 px-2 align-top">
                      <select
                        value={cr.inherentRisk}
                        onChange={(e) => updateRisk(cr.id, { inherentRisk: e.target.value as any })}
                        className="w-full px-1.5 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      >
                        <option value="Low">Low</option>
                        <option value="Moderate">Moderate</option>
                        <option value="Significant">Significant</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-2 align-top">
                      <select
                        value={cr.controlDesign}
                        onChange={(e) => updateRisk(cr.id, { controlDesign: e.target.value as any })}
                        className="w-full px-1.5 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      >
                        <option value="Effective">Effective</option>
                        <option value="Partially Effective">Partial</option>
                        <option value="Ineffective">Ineffective</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-2 align-top">
                      <select
                        value={cr.controlOperatingEffectiveness}
                        onChange={(e) => updateRisk(cr.id, { controlOperatingEffectiveness: e.target.value as any })}
                        className="w-full px-1.5 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      >
                        <option value="Operating Effectively">Effective</option>
                        <option value="Deviations Observed">Deviations</option>
                        <option value="Not Tested / Substantive Only">Not Tested</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-2 align-top">
                      <select
                        value={cr.probability}
                        onChange={(e) => updateRisk(cr.id, { probability: e.target.value as ProbabilityLevel })}
                        className="w-full px-1.5 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      >
                        <option value="Low">Low (0)</option>
                        <option value="Moderate">Mod (1)</option>
                        <option value="High">High (2)</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-2 align-top">
                      <select
                        value={cr.magnitude}
                        onChange={(e) => updateRisk(cr.id, { magnitude: e.target.value as MagnitudeLevel })}
                        className="w-full px-1.5 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      >
                        <option value="Low">Low (0)</option>
                        <option value="Moderate">Mod (1)</option>
                        <option value="High">High (2)</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-2 align-top text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[11px] font-bold ${
                          cr.suggestedRating === 'Significant'
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                            : cr.suggestedRating === 'Moderate'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                            : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                        }`}
                      >
                        {cr.suggestedRating}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 align-top text-center">
                      <select
                        value={cr.finalRating}
                        onChange={(e) => updateRisk(cr.id, { finalRating: e.target.value as RiskLevel })}
                        className={`w-full px-1.5 py-1 rounded border font-bold ${
                          cr.finalRating === 'Significant'
                            ? 'bg-rose-50 text-rose-800 border-rose-400 dark:bg-rose-950 dark:text-rose-300'
                            : cr.finalRating === 'Moderate'
                            ? 'bg-amber-50 text-amber-800 border-amber-400 dark:bg-amber-950 dark:text-amber-300'
                            : 'bg-emerald-50 text-emerald-800 border-emerald-400 dark:bg-emerald-950 dark:text-emerald-300'
                        }`}
                      >
                        <option value="Low">Low</option>
                        <option value="Moderate">Moderate</option>
                        <option value="Significant">Significant (SA 315)</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-2 align-top">
                      <div className="space-y-1">
                        <textarea
                          rows={isOverridden ? 2 : 1}
                          value={isOverridden ? cr.overrideRationale : cr.associatedControls}
                          onChange={(e) =>
                            isOverridden
                              ? updateRisk(cr.id, { overrideRationale: e.target.value })
                              : updateRisk(cr.id, { associatedControls: e.target.value })
                          }
                          placeholder={
                            isOverridden
                              ? 'Mandatory professional judgment rationale for overriding 3x3 matrix rating...'
                              : 'Key controls relied upon...'
                          }
                          className={`w-full px-2 py-1 rounded text-xs ${
                            isOverridden
                              ? 'border border-amber-400 bg-amber-50/50 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200'
                              : 'border border-stone-300 dark:border-stone-700 bg-stone-50 dark:bg-[#1a2027] text-stone-900 dark:text-stone-100'
                          }`}
                        />
                        {isOverridden && (
                          <span className="text-[10px] text-amber-700 dark:text-amber-400 font-semibold block">
                            Matrix Rating Overridden (Doc required)
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2.5 px-1 align-top text-center">
                      <button
                        onClick={() => removeRisk(cr.id)}
                        className="p-1 rounded text-stone-400 hover:text-rose-600 transition-colors"
                        title="Delete register item"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
