import React, { useState } from 'react';
import { EngagementData, FSLineItemRisk, AssertionType, RiskLevel } from '../../types';
import { TableProperties, Sparkles, Filter, Search, Loader2, Check } from 'lucide-react';

interface Stage7Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

const ALL_ASSERTIONS: AssertionType[] = [
  'Existence / Occurrence',
  'Completeness',
  'Valuation / Allocation',
  'Rights & Obligations',
  'Presentation & Disclosure',
];

const SHORT_ASSERTIONS: Record<string, string> = {
  'Existence / Occurrence': 'E/O',
  'Existence': 'E',
  'Completeness': 'C',
  'Accuracy': 'A',
  'Valuation / Allocation': 'V/A',
  'Valuation': 'V',
  'Rights & Obligations': 'R&O',
  'Cutoff': 'CO',
  'Classification': 'CL',
  'Presentation & Disclosure': 'P&D',
};

export const Stage7RiskAssessmentFS: React.FC<Stage7Props> = ({
  engagement,
  onChange,
}) => {
  const [categoryFilter, setCategoryFilter] = useState<string>('All');
  const [riskFilter, setRiskFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loadingAiId, setLoadingAiId] = useState<string | null>(null);

  const updateItem = (id: string, updates: Partial<FSLineItemRisk>) => {
    const updated = engagement.fsLineItemRisks.map((item) =>
      item.id === id ? { ...item, ...updates } : item
    );
    onChange({ ...engagement, fsLineItemRisks: updated });
  };

  const toggleAssertion = (id: string, assertion: AssertionType) => {
    const item = engagement.fsLineItemRisks.find((i) => i.id === id);
    if (!item) return;

    const exists = item.relevantAssertions.includes(assertion);
    const updatedAssertions = exists
      ? item.relevantAssertions.filter((a) => a !== assertion)
      : [...item.relevantAssertions, assertion];

    updateItem(id, { relevantAssertions: updatedAssertions });
  };

  const handleAiSuggestRationale = async (item: FSLineItemRisk) => {
    setLoadingAiId(item.id);
    try {
      const res = await fetch('/api/gemini/suggest-risk-rationale', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lineItem: item.lineItem,
          category: item.category,
          inherentRisk: item.inherentRisk,
          assertions: item.relevantAssertions,
          industry: engagement.clientName.includes('Fabric') ? 'Textile & Apparel Manufacturing' : 'Corporate Manufacturing & Trading',
        }),
      });

      const data = await res.json();
      if (data.rationale) {
        updateItem(item.id, { rationale: data.rationale });
      }
    } catch (e) {
      console.error('AI suggest error', e);
    } finally {
      setLoadingAiId(null);
    }
  };

  const categories = ['All', ...Array.from(new Set(engagement.fsLineItemRisks.map((r) => r.category)))];

  const filteredItems = engagement.fsLineItemRisks.filter((item) => {
    if (categoryFilter !== 'All' && item.category !== categoryFilter) return false;
    if (riskFilter !== 'All' && item.inherentRisk !== riskFilter) return false;
    if (searchQuery && !item.lineItem.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const significantCount = engagement.fsLineItemRisks.filter((r) => r.inherentRisk === 'Significant').length;
  const moderateCount = engagement.fsLineItemRisks.filter((r) => r.inherentRisk === 'Moderate').length;
  const lowCount = engagement.fsLineItemRisks.filter((r) => r.inherentRisk === 'Low').length;

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 07 • SA 315 (Revised)
          </span>
          <span className="text-xs text-stone-500">Para 27-29: Assertion Level Risk Assessment</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Inherent Risk Assessment at Financial Statement Line Item Level
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Assess inherent risk for each material balance sheet and profit & loss line item under Schedule III of the Companies Act 2013, map relevant assertions, and document specific risk rationale.
        </p>
      </div>

      {/* Filter and Summary Bar */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-4 shadow-xs space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
              <input
                type="text"
                placeholder="Search line items..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs w-48"
              />
            </div>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  Category: {c}
                </option>
              ))}
            </select>

            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
            >
              <option value="All">All Inherent Risks</option>
              <option value="Significant">Significant Risk Only</option>
              <option value="Moderate">Moderate Risk Only</option>
              <option value="Low">Low Risk Only</option>
            </select>
          </div>

          <div className="flex items-center gap-2 font-mono-num text-xs">
            <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 font-bold">
              {significantCount} Significant
            </span>
            <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 font-bold">
              {moderateCount} Moderate
            </span>
            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-bold">
              {lowCount} Low
            </span>
          </div>
        </div>
      </div>

      {/* Line Items Table */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#1a2027] text-stone-600 dark:text-stone-400">
                <th className="py-2.5 px-3 font-semibold w-1/5">Schedule III Line Item</th>
                <th className="py-2.5 px-3 font-semibold w-28">Category</th>
                <th className="py-2.5 px-3 font-semibold w-40">Relevant Assertions</th>
                <th className="py-2.5 px-3 font-semibold w-32">Inherent Risk</th>
                <th className="py-2.5 px-3 font-semibold">Auditor Rationale & Risk Factor</th>
                <th className="py-2.5 px-2 font-semibold w-24 text-center">AI Assist</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-stone-50/50 dark:hover:bg-[#191e25]">
                  <td className="py-3 px-3 align-top">
                    <p className="font-semibold text-stone-900 dark:text-stone-100">
                      {item.lineItem}
                    </p>
                  </td>
                  <td className="py-3 px-3 align-top">
                    <span className="text-[11px] text-stone-500 block">
                      {item.category}
                    </span>
                  </td>
                  <td className="py-3 px-3 align-top">
                    <div className="flex flex-wrap gap-1">
                      {ALL_ASSERTIONS.map((a) => {
                        const active = item.relevantAssertions.includes(a);
                        return (
                          <button
                            key={a}
                            type="button"
                            onClick={() => toggleAssertion(item.id, a)}
                            title={a}
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono-num font-bold border transition-colors ${
                              active
                                ? 'bg-amber-800 text-white border-amber-800 dark:bg-amber-600'
                                : 'bg-stone-100 text-stone-400 border-stone-300 dark:bg-stone-800 dark:border-stone-700'
                            }`}
                          >
                            {SHORT_ASSERTIONS[a]}
                          </button>
                        );
                      })}
                    </div>
                  </td>
                  <td className="py-3 px-3 align-top">
                    <select
                      value={item.inherentRisk}
                      onChange={(e) => updateItem(item.id, { inherentRisk: e.target.value as RiskLevel })}
                      className={`w-full px-2 py-1 rounded border font-semibold ${
                        item.inherentRisk === 'Significant'
                          ? 'bg-rose-50 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300'
                          : item.inherentRisk === 'Moderate'
                          ? 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300'
                          : 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300'
                      }`}
                    >
                      <option value="Low">Low</option>
                      <option value="Moderate">Moderate</option>
                      <option value="Significant">Significant (SA 315)</option>
                    </select>
                  </td>
                  <td className="py-3 px-3 align-top">
                    <textarea
                      rows={2}
                      value={item.rationale}
                      onChange={(e) => updateItem(item.id, { rationale: e.target.value })}
                      placeholder="Specify susceptibility to misstatement, complexity, subjectivity..."
                      className="w-full px-2.5 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs focus:border-amber-700"
                    />
                  </td>
                  <td className="py-3 px-2 align-top text-center">
                    <button
                      type="button"
                      disabled={loadingAiId === item.id}
                      onClick={() => handleAiSuggestRationale(item)}
                      className="px-2 py-1 rounded bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/60 dark:hover:bg-amber-900/50 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-300 text-[11px] font-medium flex items-center justify-center gap-1 transition-colors w-full shadow-2xs disabled:opacity-50"
                      title="Generate technical SA 315 risk rationale with Gemini"
                    >
                      {loadingAiId === item.id ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Sparkles className="w-3 h-3 text-amber-700 dark:text-amber-400" />
                      )}
                      <span>AI Draft</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
