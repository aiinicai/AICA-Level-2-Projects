import React from 'react';
import { EngagementData, ITSystem } from '../../types';
import { Server, Plus, Trash2, ShieldCheck, Database, HardDrive, Cpu } from 'lucide-react';

interface Stage4Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage4InformationSystems: React.FC<Stage4Props> = ({
  engagement,
  onChange,
}) => {
  const systems = engagement.itSystems || [];

  const updateSystem = (id: string, updates: Partial<ITSystem>) => {
    const updated = systems.map((s) => (s.id === id ? { ...s, ...updates } : s));
    onChange({
      ...engagement,
      itSystems: updated,
    });
  };

  const addSystem = () => {
    const newSys: ITSystem = {
      id: `it-${Date.now()}`,
      systemName: 'New Financial / Operational Application',
      purpose: 'Financial record keeping, subledger processing, or inventory',
      criticality: 'Medium',
      hosting: 'Cloud SaaS',
      observations: 'Password policy, dual approval, and audit trail enabled.',
    };
    onChange({
      ...engagement,
      itSystems: [...systems, newSys],
    });
  };

  const removeSystem = (id: string) => {
    onChange({
      ...engagement,
      itSystems: systems.filter((s) => s.id !== id),
    });
  };

  const updateItRelianceNotes = (notes: string) => {
    onChange({
      ...engagement,
      itRelianceNotes: notes,
    });
  };

  const updateItgcObservations = (obs: string) => {
    onChange({
      ...engagement,
      itgcObservations: obs,
    });
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 04 • SA 315 (Revised)
          </span>
          <span className="text-xs text-stone-500">Para 18 & 21: Information Systems Relevant to Financial Reporting</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Information Systems & IT General Controls (ITGC)
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Obtain an understanding of the IT architecture, automated transaction processing, database hosting, and IT General Controls supporting financial reporting integrity.
        </p>
      </div>

      {/* IT Systems Inventory */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-amber-700 dark:text-amber-400" />
            <span>Applications & IT Systems Inventory ({systems.length})</span>
          </h3>
          <button
            type="button"
            onClick={addSystem}
            className="px-3 py-1.5 rounded-md bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 hover:bg-stone-800 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add System</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#1a2027] text-stone-600 dark:text-stone-400">
                <th className="py-2.5 px-3 font-semibold w-1/4">System Name & Version</th>
                <th className="py-2.5 px-3 font-semibold w-1/3">Financial Reporting Purpose</th>
                <th className="py-2.5 px-2.5 font-semibold w-24">Criticality</th>
                <th className="py-2.5 px-2.5 font-semibold w-28">Hosting</th>
                <th className="py-2.5 px-3 font-semibold">Observations & Automated Controls</th>
                <th className="py-2.5 px-2 font-semibold w-10 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
              {systems.map((sys) => (
                <tr key={sys.id} className="hover:bg-stone-50/50 dark:hover:bg-[#191e25]">
                  <td className="py-2.5 px-3 align-top">
                    <input
                      type="text"
                      value={sys.systemName}
                      onChange={(e) => updateSystem(sys.id, { systemName: e.target.value })}
                      className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium"
                    />
                  </td>
                  <td className="py-2.5 px-3 align-top">
                    <textarea
                      rows={2}
                      value={sys.purpose}
                      onChange={(e) => updateSystem(sys.id, { purpose: e.target.value })}
                      className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                    />
                  </td>
                  <td className="py-2.5 px-2.5 align-top">
                    <select
                      value={sys.criticality}
                      onChange={(e) => updateSystem(sys.id, { criticality: e.target.value as any })}
                      className={`w-full px-2 py-1 rounded border font-semibold ${
                        sys.criticality === 'High'
                          ? 'bg-rose-50 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300'
                          : sys.criticality === 'Medium'
                          ? 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300'
                      }`}
                    >
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </td>
                  <td className="py-2.5 px-2.5 align-top">
                    <input
                      type="text"
                      value={sys.hosting}
                      onChange={(e) => updateSystem(sys.id, { hosting: e.target.value })}
                      className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                    />
                  </td>
                  <td className="py-2.5 px-3 align-top">
                    <textarea
                      rows={2}
                      value={sys.observations}
                      onChange={(e) => updateSystem(sys.id, { observations: e.target.value })}
                      className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
                    />
                  </td>
                  <td className="py-2.5 px-2 align-top text-center">
                    <button
                      type="button"
                      onClick={() => removeSystem(sys.id)}
                      className="p-1 rounded text-stone-400 hover:text-rose-600 transition-colors"
                      title="Delete system"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ITGC Observations and IT Reliance Strategy */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* ITGC Observations */}
        <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-3">
          <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-amber-700 dark:text-amber-400" />
            <span>IT General Controls (ITGC) Evaluation</span>
          </h3>
          <p className="text-xs text-stone-500">
            Document auditor review of access security, change management, program development, and computer operations (backups, disaster recovery).
          </p>
          <textarea
            rows={6}
            value={engagement.itgcObservations || ''}
            onChange={(e) => updateItgcObservations(e.target.value)}
            placeholder="Document ITGC observations, password expiry policy, backup test frequency, privileged user reviews..."
            className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs leading-relaxed focus:border-amber-700"
          />
        </div>

        {/* Auditor IT Reliance Strategy */}
        <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-3">
          <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-emerald-700 dark:text-emerald-400" />
            <span>Auditor IT Reliance Strategy</span>
          </h3>
          <p className="text-xs text-stone-500">
            State the extent to which the audit engagement team intends to place reliance on automated IT application controls and system-generated reports (IPE).
          </p>
          <textarea
            rows={6}
            value={engagement.itRelianceNotes || ''}
            onChange={(e) => updateItRelianceNotes(e.target.value)}
            placeholder="Document planned reliance on automated controls (e.g. 3-way match, exchange rate calculation) and testing of Information Produced by Entity (IPE)..."
            className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs leading-relaxed focus:border-amber-700"
          />
        </div>
      </div>
    </div>
  );
};
