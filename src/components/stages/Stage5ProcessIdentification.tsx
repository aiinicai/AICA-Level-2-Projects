import React from 'react';
import { EngagementData, BusinessProcess } from '../../types';
import { Workflow, Plus, Trash2, CheckCircle2 } from 'lucide-react';

interface Stage5Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage5ProcessIdentification: React.FC<Stage5Props> = ({
  engagement,
  onChange,
}) => {
  const processes = engagement.businessProcesses || [];

  const updateProcess = (id: string, updates: Partial<BusinessProcess>) => {
    const updated = processes.map((p) => {
      if (p.id !== id) return p;
      const merged = { ...p, ...updates };
      // Keep aliases in sync
      if (updates.name) merged.processName = updates.name;
      if (updates.processName) merged.name = updates.processName;
      if (updates.nature) merged.classification = updates.nature;
      if (updates.classification) merged.nature = updates.classification as any;
      if (updates.owner) merged.processOwner = updates.owner;
      if (updates.processOwner) merged.owner = updates.processOwner;
      if (updates.itSystemUsed) merged.itSystem = updates.itSystemUsed;
      if (updates.itSystem) merged.itSystemUsed = updates.itSystem;
      return merged;
    });
    onChange({ ...engagement, businessProcesses: updated });
  };

  const addProcess = () => {
    const newProc: BusinessProcess = {
      id: `proc-${Date.now()}`,
      processName: 'New Business Process / Transaction Cycle',
      name: 'New Business Process / Transaction Cycle',
      nature: 'Significant',
      classification: 'Significant',
      owner: 'Process Head',
      processOwner: 'Process Head',
      itSystemUsed: 'ERP System',
      itSystem: 'ERP System',
      notes: 'Key internal controls, authorization matrix, segregation of duties.',
      walkthroughScoped: true,
      assertions: ['Completeness', 'Accuracy'],
    };
    onChange({ ...engagement, businessProcesses: [...processes, newProc] });
  };

  const removeProcess = (id: string) => {
    onChange({
      ...engagement,
      businessProcesses: processes.filter((p) => p.id !== id),
    });
  };

  const significantCount = processes.filter(
    (p) => (p.nature || p.classification) === 'Significant'
  ).length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 05 • SA 315 (Revised)
          </span>
          <span className="text-xs text-stone-500">Para 18(a): Significant Classes of Transactions</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Business Process Identification & Scoping
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Identify all key operational and transaction cycles, assess process significance (routine vs significant), map IT systems utilized, and designate processes requiring mandatory walkthroughs.
        </p>
      </div>

      {/* Processes Table */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
              <Workflow className="w-4 h-4 text-amber-700 dark:text-amber-400" />
              <span>Core Transaction Cycles & Processes ({processes.length})</span>
            </h3>
            <span className="text-xs text-stone-500 font-medium">
              {significantCount} Significant Cycles Identified
            </span>
          </div>
          <button
            type="button"
            onClick={addProcess}
            className="px-3 py-1.5 rounded-md bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 hover:bg-stone-800 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Process</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#1a2027] text-stone-600 dark:text-stone-400">
                <th className="py-2.5 px-3 font-semibold w-1/4">Process Name & Cycle</th>
                <th className="py-2.5 px-3 font-semibold w-32">Nature / Significance</th>
                <th className="py-2.5 px-3 font-semibold w-36">Process Owner</th>
                <th className="py-2.5 px-3 font-semibold w-36">IT System Used</th>
                <th className="py-2.5 px-3 font-semibold">Process Notes & Key Controls</th>
                <th className="py-2.5 px-2 font-semibold w-10 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
              {processes.map((proc) => {
                const procName = proc.processName || proc.name || '';
                const nature = proc.nature || proc.classification || 'Routine';
                const owner = proc.owner || proc.processOwner || '';
                const itSystem = proc.itSystemUsed || proc.itSystem || '';
                const notes = proc.notes || '';

                return (
                  <tr key={proc.id} className="hover:bg-stone-50/50 dark:hover:bg-[#191e25]">
                    <td className="py-2.5 px-3 align-top">
                      <input
                        type="text"
                        value={procName}
                        onChange={(e) => updateProcess(proc.id, { processName: e.target.value, name: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium"
                      />
                    </td>
                    <td className="py-2.5 px-3 align-top">
                      <select
                        value={nature}
                        onChange={(e) => updateProcess(proc.id, { nature: e.target.value as any, classification: e.target.value })}
                        className={`w-full px-2 py-1 rounded border font-semibold ${
                          nature === 'Significant'
                            ? 'bg-amber-50 text-amber-900 border-amber-300 dark:bg-amber-950 dark:text-amber-300'
                            : 'bg-stone-50 text-stone-800 border-stone-300 dark:bg-stone-800 dark:text-stone-300'
                        }`}
                      >
                        <option value="Significant">Significant</option>
                        <option value="Routine">Routine</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-3 align-top">
                      <input
                        type="text"
                        value={owner}
                        onChange={(e) => updateProcess(proc.id, { owner: e.target.value, processOwner: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      />
                    </td>
                    <td className="py-2.5 px-3 align-top">
                      <input
                        type="text"
                        value={itSystem}
                        onChange={(e) => updateProcess(proc.id, { itSystemUsed: e.target.value, itSystem: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      />
                    </td>
                    <td className="py-2.5 px-3 align-top">
                      <textarea
                        rows={2}
                        value={notes}
                        onChange={(e) => updateProcess(proc.id, { notes: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
                      />
                    </td>
                    <td className="py-2.5 px-2 align-top text-center">
                      <button
                        type="button"
                        onClick={() => removeProcess(proc.id)}
                        className="p-1 rounded text-stone-400 hover:text-rose-600 transition-colors"
                        title="Delete process"
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
