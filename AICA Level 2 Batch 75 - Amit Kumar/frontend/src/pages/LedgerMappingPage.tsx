import React, { useEffect, useState } from 'react';
import type { Client, TrialBalanceLine } from '../types';
import { fetchMapping, autoMap, updateMappingItem, SCHEDULE_III_CLASSIFICATIONS } from '../services/api';
import { GitMerge, Check, AlertCircle, Search, Sparkles, Filter } from 'lucide-react';

interface LedgerMappingProps {
  client: Client;
  onNavigate: (tab: string) => void;
}

export const LedgerMappingPage: React.FC<LedgerMappingProps> = ({ client, onNavigate }) => {
  const [lines, setLines] = useState<TrialBalanceLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'mapped' | 'unmapped' | 'override'>('all');
  const [savingId, setSavingId] = useState<number | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchMapping(client.id);
      setLines(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (client) loadData();
  }, [client.id]);

  const handleAutoSuggest = async () => {
    setLoading(true);
    await autoMap(client.id);
    await loadData();
  };

  const handleSelectClassification = async (line: TrialBalanceLine, className: string) => {
    const matchedSpec = SCHEDULE_III_CLASSIFICATIONS.find(c => c.name === className);
    if (!matchedSpec) return;

    setSavingId(line.id);
    const updatedLine = {
      ...line,
      final_classification: matchedSpec.name,
      financial_statement: matchedSpec.statement,
      note_number: matchedSpec.note,
      current_non_current: matchedSpec.type,
      user_override: true
    };

    setLines(prev => prev.map(l => l.id === line.id ? updatedLine : l));

    await updateMappingItem({
      id: line.id,
      final_classification: matchedSpec.name,
      financial_statement: matchedSpec.statement,
      note_number: matchedSpec.note,
      current_non_current: matchedSpec.type
    });
    setSavingId(null);
  };

  const filteredLines = lines.filter(l => {
    const matchesSearch = l.ledger_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (l.original_group || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (l.final_classification || '').toLowerCase().includes(searchQuery.toLowerCase());
    
    if (filterType === 'mapped') return matchesSearch && !!l.final_classification;
    if (filterType === 'unmapped') return matchesSearch && (!l.final_classification || l.final_classification === 'Other Expenses');
    if (filterType === 'override') return matchesSearch && l.user_override;
    return matchesSearch;
  });

  const mappedCount = lines.filter(l => l.final_classification && l.final_classification !== 'Other Expenses').length;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-tight flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-orange-600" />
            SCHEDULE III LEDGER MAPPING ENGINE
          </h1>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
            {client.name} | {mappedCount} of {lines.length} Ledgers Classified
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={handleAutoSuggest} className="ca-button-secondary text-xs">
            <Sparkles className="w-3.5 h-3.5 text-orange-600" />
            Run Keyword Auto-Mapper
          </button>

          <button onClick={() => onNavigate('financial-statements')} className="ca-button-primary text-xs">
            Generate Statements &rarr;
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 studio-card p-3.5">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search ledgers, original groups, or target classifications..."
            className="studio-input pl-9 text-xs"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-bold text-slate-500">Filter:</span>
          <button
            onClick={() => setFilterType('all')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              filterType === 'all' ? 'bg-[#1B365D] text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
            }`}
          >
            All ({lines.length})
          </button>
          <button
            onClick={() => setFilterType('mapped')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              filterType === 'mapped' ? 'bg-emerald-700 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
            }`}
          >
            Classified ({mappedCount})
          </button>
          <button
            onClick={() => setFilterType('override')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              filterType === 'override' ? 'bg-orange-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
            }`}
          >
            Auditor Overrides ({lines.filter(l => l.user_override).length})
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 font-semibold text-xs">Mapping trial balance ledgers...</div>
      ) : (
        <div className="studio-card p-0 overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#1B365D] text-white">
                <th className="py-2.5 px-3">Ledger Name</th>
                <th className="py-2.5 px-3">Original Group</th>
                <th className="py-2.5 px-3 text-right">CY Amount</th>
                <th className="py-2.5 px-3 text-right">PY Amount</th>
                <th className="py-2.5 px-3">Target Schedule III Classification</th>
                <th className="py-2.5 px-3">Statement</th>
                <th className="py-2.5 px-3 text-center">Note</th>
                <th className="py-2.5 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {filteredLines.map((line) => (
                <tr key={line.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                  <td className="py-2 px-3 font-bold text-slate-800 dark:text-slate-200">
                    {line.ledger_name}
                    {line.ledger_code && <span className="text-[10px] text-slate-400 ml-1.5">({line.ledger_code})</span>}
                  </td>
                  <td className="py-2 px-3 text-slate-500">{line.original_group || '-'}</td>
                  <td className="py-2 px-3 text-right font-mono font-bold text-[#1B365D] dark:text-blue-400">
                    {line.cy_amount < 0 ? `(${Math.abs(line.cy_amount).toFixed(2)})` : line.cy_amount.toFixed(2)}
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-slate-500">
                    {line.py_amount < 0 ? `(${Math.abs(line.py_amount).toFixed(2)})` : line.py_amount.toFixed(2)}
                  </td>
                  <td className="py-2 px-3">
                    <select
                      className="studio-input text-xs font-semibold"
                      value={line.final_classification || ''}
                      onChange={(e) => handleSelectClassification(line, e.target.value)}
                    >
                      <option value="">-- Select Schedule III Classification --</option>
                      {SCHEDULE_III_CLASSIFICATIONS.map(c => (
                        <option key={c.name} value={c.name}>{c.name} ({c.statement})</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 px-3 text-xs font-semibold text-slate-700 dark:text-slate-300">
                    {line.financial_statement}
                  </td>
                  <td className="py-2 px-3 text-center font-mono font-bold text-orange-600 dark:text-orange-400">
                    {line.note_number || '-'}
                  </td>
                  <td className="py-2 px-3 text-center">
                    {savingId === line.id ? (
                      <span className="text-[10px] text-slate-400">Saving...</span>
                    ) : line.user_override ? (
                      <span className="bg-orange-100 dark:bg-orange-950 text-orange-800 dark:text-orange-300 text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 justify-center">
                        <Check className="w-3 h-3" /> Override
                      </span>
                    ) : line.final_classification ? (
                      <span className="bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 justify-center">
                        <Check className="w-3 h-3" /> Auto
                      </span>
                    ) : (
                      <span className="bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 justify-center">
                        <AlertCircle className="w-3 h-3" /> Unmapped
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
