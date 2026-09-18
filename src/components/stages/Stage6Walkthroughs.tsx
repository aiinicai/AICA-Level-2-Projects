import React from 'react';
import { EngagementData, WalkthroughItem } from '../../types';
import { Footprints, CheckCircle2, AlertTriangle, XCircle, FileText } from 'lucide-react';

interface Stage6Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage6Walkthroughs: React.FC<Stage6Props> = ({
  engagement,
  onChange,
}) => {
  const walkthroughs = engagement.walkthroughs || [];

  const updateWalkthrough = (id: string, updates: Partial<WalkthroughItem>) => {
    const updated = walkthroughs.map((w) => {
      if (w.id !== id) return w;
      const merged = { ...w, ...updates };
      // Keep aliases in sync
      if (updates.date) merged.datePerformed = updates.date;
      if (updates.datePerformed) merged.date = updates.datePerformed;
      if (updates.performedBy) merged.auditor = updates.performedBy;
      if (updates.auditor) merged.performedBy = updates.auditor;
      if (updates.sampleDocRef) merged.sampleDocumentRef = updates.sampleDocRef;
      if (updates.sampleDocumentRef) merged.sampleDocRef = updates.sampleDocumentRef;
      if (updates.observations) merged.observedControls = updates.observations;
      if (updates.observedControls) merged.observations = updates.observedControls;
      return merged;
    });
    onChange({ ...engagement, walkthroughs: updated });
  };

  const performedCount = walkthroughs.filter((w) => w.performed).length;
  const verifiedCount = walkthroughs.filter(
    (w) =>
      w.conclusion === 'Design and implementation verified' ||
      w.conclusion === ('Satisfactory' as any)
  ).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 06 • SA 315 (Revised)
          </span>
          <span className="text-xs text-stone-500">Para 18 & Para 21: Design & Implementation (D&I) of Internal Controls</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Process Walkthroughs & Control Design Evaluation
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Trace a sample transaction from initiation through processing and recording in the general ledger to verify that controls are designed appropriately and have been implemented in practice.
        </p>
      </div>

      {/* Summary KPI Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-[#15191f] rounded-lg border border-[#dedbd2] dark:border-[#272f38] p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-stone-100 dark:bg-stone-800 flex items-center justify-center text-stone-700 dark:text-stone-300">
            <Footprints className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-stone-500">Total Scoped</div>
            <div className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
              {walkthroughs.length} Cycles
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-[#15191f] rounded-lg border border-[#dedbd2] dark:border-[#272f38] p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-amber-100 dark:bg-amber-950 flex items-center justify-center text-amber-800 dark:text-amber-300">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-stone-500">Walkthroughs Performed</div>
            <div className="font-serif font-bold text-lg text-amber-800 dark:text-amber-300">
              {performedCount} / {walkthroughs.length}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-[#15191f] rounded-lg border border-[#dedbd2] dark:border-[#272f38] p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center text-emerald-800 dark:text-emerald-300">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs text-stone-500">D&I Verified</div>
            <div className="font-serif font-bold text-lg text-emerald-800 dark:text-emerald-300">
              {verifiedCount} Cycles
            </div>
          </div>
        </div>
      </div>

      {/* Walkthrough Cards */}
      <div className="space-y-4">
        {walkthroughs.map((w, idx) => {
          const dateVal = w.date || w.datePerformed || '';
          const auditorVal = w.performedBy || w.auditor || '';
          const sampleRefVal = w.sampleDocRef || w.sampleDocumentRef || '';
          const obsVal = w.observations || w.observedControls || '';
          const gapsVal = w.controlGaps || '';

          return (
            <div
              key={w.id}
              className={`bg-white dark:bg-[#15191f] rounded-xl border p-5 transition-all shadow-xs space-y-4 ${
                w.performed
                  ? 'border-stone-300 dark:border-stone-700'
                  : 'border-dashed border-stone-300 dark:border-stone-700 opacity-85'
              }`}
            >
              {/* Header row */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-stone-200 dark:border-stone-800">
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={w.performed}
                      onChange={(e) => updateWalkthrough(w.id, { performed: e.target.checked })}
                      className="w-4 h-4 rounded border-stone-300 text-amber-800 focus:ring-amber-700"
                    />
                    <span className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                      {idx + 1}. {w.processName}
                    </span>
                  </label>
                  {w.performed && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                      Walkthrough Performed
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="text-stone-500">Date:</span>
                    <input
                      type="date"
                      value={dateVal}
                      onChange={(e) => updateWalkthrough(w.id, { date: e.target.value, datePerformed: e.target.value })}
                      className="px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-mono-num"
                    />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-stone-500">Auditor:</span>
                    <input
                      type="text"
                      value={auditorVal}
                      onChange={(e) => updateWalkthrough(w.id, { performedBy: e.target.value, auditor: e.target.value })}
                      placeholder="Auditor initials"
                      className="w-32 px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                    />
                  </div>
                </div>
              </div>

              {/* Inputs & Observations Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                    Sample Document / Transaction Reference Inspected
                  </label>
                  <input
                    type="text"
                    value={sampleRefVal}
                    onChange={(e) => updateWalkthrough(w.id, { sampleDocRef: e.target.value, sampleDocumentRef: e.target.value })}
                    placeholder="e.g. Sales Invoice #SI-2025-0842, GDN #4912, Bank Advice..."
                    className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-mono-num"
                  />
                </div>

                <div>
                  <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                    Design & Implementation (D&I) Conclusion *
                  </label>
                  <select
                    value={w.conclusion}
                    onChange={(e) => updateWalkthrough(w.id, { conclusion: e.target.value as any })}
                    className={`w-full px-3 py-1.5 rounded border font-semibold ${
                      w.conclusion === 'Design and implementation verified' || w.conclusion === ('Satisfactory' as any)
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300'
                        : w.conclusion === 'Control gaps identified'
                        ? 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300'
                        : 'bg-stone-100 text-stone-700 border-stone-300 dark:bg-stone-800 dark:text-stone-300'
                    }`}
                  >
                    <option value="Design and implementation verified">Design and implementation verified</option>
                    <option value="Control gaps identified">Control gaps identified</option>
                    <option value="Pending walkthrough">Pending walkthrough</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                    Walkthrough Procedures & Observed Controls
                  </label>
                  <textarea
                    rows={3}
                    value={obsVal}
                    onChange={(e) => updateWalkthrough(w.id, { observations: e.target.value, observedControls: e.target.value })}
                    placeholder="Describe step-by-step verification: authorization, automated match, segregation..."
                    className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 leading-relaxed"
                  />
                </div>

                <div>
                  <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
                    Control Gaps / Deficiencies Noted
                  </label>
                  <textarea
                    rows={3}
                    value={gapsVal}
                    onChange={(e) => updateWalkthrough(w.id, { controlGaps: e.target.value })}
                    placeholder="Document any control gaps, manual bypasses, or lack of documentation..."
                    className="w-full px-3 py-1.5 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 leading-relaxed"
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
