import React, { useEffect, useState } from 'react';
import type { Client, AccountingPolicy } from '../types';
import { fetchAccountingPolicies, updateAccountingPolicy, resetAccountingPolicy, toggleAccountingPolicyApplicability } from '../services/api';
import { FileText, Save, RotateCcw, Check, Search, ShieldCheck, Filter } from 'lucide-react';

interface AccountingPoliciesProps {
  client: Client;
}

export const AccountingPoliciesPage: React.FC<AccountingPoliciesProps> = ({ client }) => {
  const [policies, setPolicies] = useState<AccountingPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [successId, setSuccessId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'applicable' | 'non-applicable'>('all');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchAccountingPolicies(client.id);
      setPolicies(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (client) loadData();
  }, [client.id]);

  const handleSave = async (policy: AccountingPolicy) => {
    setSavingId(policy.id);
    await updateAccountingPolicy(policy.id, policy.content);
    setSavingId(null);
    setSuccessId(policy.id);
    setTimeout(() => setSuccessId(null), 2500);
    await loadData();
  };

  const handleReset = async (policy: AccountingPolicy) => {
    setSavingId(policy.id);
    await resetAccountingPolicy(policy.id);
    setSavingId(null);
    await loadData();
  };

  const handleToggle = async (policy: AccountingPolicy) => {
    const nextState = !policy.is_applicable;
    setPolicies(prev => prev.map(p => p.id === policy.id ? { ...p, is_applicable: nextState } : p));
    await toggleAccountingPolicyApplicability(policy.id, nextState);
    await loadData();
  };

  const filteredPolicies = policies.filter(p => {
    const matchesSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          p.policy_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          p.content.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (filterType === 'applicable') return matchesSearch && p.is_applicable;
    if (filterType === 'non-applicable') return matchesSearch && !p.is_applicable;
    return matchesSearch;
  });

  const applicableCount = policies.filter(p => p.is_applicable).length;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <div className="bg-[#1B365D] text-white p-4 rounded-xl shadow-xs space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-base font-black tracking-wider uppercase flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-400" />
              SIGNIFICANT ACCOUNTING POLICIES (IGAAP SCHEDULE III DIVISION I)
            </h1>
            <span className="bg-orange-600 text-white font-mono text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" /> {applicableCount} / {policies.length} Policies Active
            </span>
          </div>
          <p className="text-xs text-slate-300">
            Professional IGAAP accounting policy disclosures for {client.name}. Toggle applicability or customize text for audit drafting.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 studio-card p-3.5">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search policies by keyword, AS reference, or number..."
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
            All ({policies.length})
          </button>
          <button
            onClick={() => setFilterType('applicable')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              filterType === 'applicable' ? 'bg-emerald-700 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
            }`}
          >
            Applicable ({applicableCount})
          </button>
          <button
            onClick={() => setFilterType('non-applicable')}
            className={`px-3 py-1.5 rounded-md font-bold transition-all ${
              filterType === 'non-applicable' ? 'bg-rose-700 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
            }`}
          >
            Not Applicable ({policies.length - applicableCount})
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 font-semibold text-xs">Loading 21 standard IGAAP accounting policies...</div>
      ) : (
        <div className="space-y-4">
          {filteredPolicies.map((policy) => (
            <div
              key={policy.id}
              className={`studio-card p-5 space-y-3 transition-all ${
                !policy.is_applicable ? 'opacity-60 bg-slate-50/50 dark:bg-slate-900/30 border-dashed' : ''
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <span className="bg-[#1B365D] text-white font-mono text-xs font-black px-2.5 py-1 rounded">
                    {policy.policy_number}
                  </span>
                  <h3 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wide">
                    {policy.title}
                  </h3>
                  {policy.is_modified && (
                    <span className="bg-orange-100 text-orange-900 border border-orange-300 text-[10px] font-bold px-2 py-0.5 rounded">
                      MODIFIED BY AUDITOR
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {/* Applicability Toggle Button */}
                  <button
                    onClick={() => handleToggle(policy)}
                    className={`px-3 py-1 rounded-full text-[11px] font-extrabold transition-all cursor-pointer border ${
                      policy.is_applicable
                        ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-400'
                        : 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-400'
                    }`}
                  >
                    {policy.is_applicable ? 'Applicable' : 'Not Applicable'}
                  </button>

                  <button
                    onClick={() => handleReset(policy)}
                    className="ca-button-outline text-xs text-slate-700 dark:text-slate-300"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reset to Default
                  </button>

                  <button
                    onClick={() => handleSave(policy)}
                    disabled={savingId === policy.id}
                    className="ca-button-primary text-xs"
                  >
                    {successId === policy.id ? (
                      <>
                        <Check className="w-3.5 h-3.5" /> Saved!
                      </>
                    ) : (
                      <>
                        <Save className="w-3.5 h-3.5" /> Save Policy
                      </>
                    )}
                  </button>
                </div>
              </div>

              <textarea
                className="studio-input w-full h-28 font-mono text-xs p-3 leading-relaxed"
                value={policy.content}
                disabled={!policy.is_applicable}
                onChange={(e) => {
                  const val = e.target.value;
                  setPolicies(prev => prev.map(p => p.id === policy.id ? { ...p, content: val } : p));
                }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
