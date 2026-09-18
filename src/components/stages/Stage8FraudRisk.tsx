import React, { useState } from 'react';
import { EngagementData, AdditionalFraudRisk } from '../../types';
import { ShieldAlert, Sparkles, AlertTriangle, Plus, Trash2, Loader2, Info, Lock } from 'lucide-react';

interface Stage8Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

export const Stage8FraudRisk: React.FC<Stage8Props> = ({
  engagement,
  onChange,
}) => {
  const [aiLoading, setAiLoading] = useState(false);

  // Normalize access to fraudRisks
  const fraudData = engagement.fraudRisks || (engagement as any).fraudRisk || {
    revenuePresumption: {
      rebutted: false,
      rationale: '',
      plannedResponse: '',
    },
    managementOverride: {
      rationale: '',
      plannedResponse: '',
    },
    additionalRisks: [],
  };

  const isRebutted =
    typeof fraudData.revenuePresumption === 'object'
      ? Boolean(fraudData.revenuePresumption?.rebutted)
      : fraudData.revenuePresumption === 'Rebutted';

  const revenueRationale =
    typeof fraudData.revenuePresumption === 'object'
      ? fraudData.revenuePresumption?.rationale || ''
      : fraudData.revenueRationale || '';

  const revenuePlannedResponse =
    typeof fraudData.revenuePresumption === 'object'
      ? fraudData.revenuePresumption?.plannedResponse || ''
      : '';

  const managementRationale =
    typeof fraudData.managementOverride === 'object'
      ? fraudData.managementOverride?.rationale || ''
      : '';

  const managementPlannedResponse =
    typeof fraudData.managementOverride === 'object'
      ? fraudData.managementOverride?.plannedResponse || ''
      : fraudData.managementOverrideProcedures || '';

  const additionalRisks: AdditionalFraudRisk[] =
    fraudData.additionalRisks || (fraudData as any).identifiedRisks || [];

  const updateFraudData = (updated: any) => {
    const merged = { ...fraudData, ...updated };
    onChange({
      ...engagement,
      fraudRisks: merged,
      fraudRisk: merged,
    });
  };

  const setRevenueRebutted = (rebutted: boolean) => {
    if (typeof fraudData.revenuePresumption === 'object') {
      updateFraudData({
        revenuePresumption: {
          ...fraudData.revenuePresumption,
          rebutted,
        },
      });
    } else {
      updateFraudData({
        revenuePresumption: rebutted ? 'Rebutted' : 'Presumed',
      });
    }
  };

  const setRevenueRationale = (rationale: string) => {
    if (typeof fraudData.revenuePresumption === 'object') {
      updateFraudData({
        revenuePresumption: {
          ...fraudData.revenuePresumption,
          rationale,
        },
        revenueRationale: rationale,
      });
    } else {
      updateFraudData({
        revenueRationale: rationale,
      });
    }
  };

  const setRevenueResponse = (plannedResponse: string) => {
    if (typeof fraudData.revenuePresumption === 'object') {
      updateFraudData({
        revenuePresumption: {
          ...fraudData.revenuePresumption,
          plannedResponse,
        },
      });
    }
  };

  const setManagementRationale = (rationale: string) => {
    if (typeof fraudData.managementOverride === 'object') {
      updateFraudData({
        managementOverride: {
          ...fraudData.managementOverride,
          rationale,
        },
      });
    }
  };

  const setManagementResponse = (plannedResponse: string) => {
    if (typeof fraudData.managementOverride === 'object') {
      updateFraudData({
        managementOverride: {
          ...fraudData.managementOverride,
          plannedResponse,
        },
        managementOverrideProcedures: plannedResponse,
      });
    } else {
      updateFraudData({
        managementOverrideProcedures: plannedResponse,
      });
    }
  };

  const updateAdditionalRisk = (id: string, updates: Partial<AdditionalFraudRisk>) => {
    const updated = additionalRisks.map((r) => {
      if (r.id !== id) return r;
      const merged = { ...r, ...updates };
      if (updates.riskDescription) merged.fraudType = updates.riskDescription;
      if (updates.fraudType) merged.riskDescription = updates.fraudType;
      if (updates.impactedAccounts) merged.lineItemName = updates.impactedAccounts;
      if (updates.lineItemName) merged.impactedAccounts = updates.lineItemName;
      if (updates.plannedProcedures) merged.plannedResponse = updates.plannedProcedures;
      if (updates.plannedResponse) merged.plannedProcedures = updates.plannedResponse;
      return merged;
    });
    updateFraudData({ additionalRisks: updated });
  };

  const addAdditionalRisk = () => {
    const newItem: AdditionalFraudRisk = {
      id: `fr-${Date.now()}`,
      lineItemName: 'Revenue / Inventory / Related Party',
      fraudType: 'Fictitious transactions or valuation distortion',
      identified: true,
      rationale: 'Management pressure or opportunity due to weak internal controls.',
      plannedResponse: 'Perform substantive audit testing and independent confirmations.',
      riskDescription: 'Fictitious transactions or valuation distortion',
      fraudTriangleCategory: 'Incentives / Pressures',
      impactedAccounts: 'Revenue / Inventory',
      plannedProcedures: 'Perform substantive audit testing and independent confirmations.',
    };
    updateFraudData({ additionalRisks: [...additionalRisks, newItem] });
  };

  const removeAdditionalRisk = (id: string) => {
    updateFraudData({
      additionalRisks: additionalRisks.filter((r) => r.id !== id),
    });
  };

  const handleAiSuggestFraud = async () => {
    setAiLoading(true);
    try {
      const res = await fetch('/api/gemini/suggest-fraud-risks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clientName: engagement.clientName,
          industry: 'Manufacturing and Trading',
          entityUnderstanding: engagement.entityUnderstanding,
        }),
      });

      const data = await res.json();
      if (Array.isArray(data.risks) && data.risks.length > 0) {
        const newFormatted: AdditionalFraudRisk[] = data.risks.map((r: any, idx: number) => ({
          id: `fr-ai-${Date.now()}-${idx}`,
          lineItemName: r.impactedAccounts || r.lineItemName || 'Operating Accounts',
          fraudType: r.riskDescription || r.fraudType || 'Identified fraud factor',
          identified: true,
          rationale: r.rationale || r.riskDescription || '',
          plannedResponse: r.plannedProcedures || r.plannedResponse || '',
          riskDescription: r.riskDescription || r.fraudType || '',
          fraudTriangleCategory: r.fraudTriangleCategory || 'Opportunities',
          impactedAccounts: r.impactedAccounts || r.lineItemName || '',
          plannedProcedures: r.plannedProcedures || r.plannedResponse || '',
        }));

        updateFraudData({
          additionalRisks: [...additionalRisks, ...newFormatted],
        });
      }
    } catch (err) {
      console.error('Error fetching AI suggestions:', err);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono-num text-xs font-bold text-rose-800 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 px-2 py-0.5 rounded border border-rose-200 dark:border-rose-800">
              Stage 08 • SA 240
            </span>
            <span className="text-xs text-stone-500">The Auditor's Responsibilities Relating to Fraud</span>
          </div>
          <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
            Fraud Risk Assessment & Mandatory Presumptions
          </h2>
          <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
            Address the mandatory rebuttable presumption in revenue recognition, the non-rebuttable risk of management override of controls, and specific fraud risk factors.
          </p>
        </div>

        <button
          type="button"
          disabled={aiLoading}
          onClick={handleAiSuggestFraud}
          className="px-3.5 py-2 rounded-lg bg-amber-800 hover:bg-amber-900 dark:bg-amber-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs shrink-0 self-start transition-colors disabled:opacity-50"
        >
          {aiLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing SA 240...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Gemini Suggest Fraud Risks</span>
            </>
          )}
        </button>
      </div>

      {/* Mandatory Presumption 1: Revenue Recognition (SA 240 Para 26) */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-stone-200 dark:border-stone-800">
          <div>
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-700 dark:text-rose-400" />
              <span>1. Presumption of Fraud in Revenue Recognition (SA 240 Para 26)</span>
            </h3>
            <p className="text-xs text-stone-500 mt-0.5">
              Auditors shall evaluate which types of revenue, revenue transactions, or assertions give rise to fraud risks.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setRevenueRebutted(false)}
              className={`px-3 py-1.5 rounded-md text-xs font-bold border transition-colors ${
                !isRebutted
                  ? 'bg-rose-700 text-white border-rose-700'
                  : 'bg-stone-50 dark:bg-[#1a2027] text-stone-700 dark:text-stone-300 border-stone-300 dark:border-stone-700'
              }`}
            >
              Presumption Maintained
            </button>
            <button
              type="button"
              onClick={() => setRevenueRebutted(true)}
              className={`px-3 py-1.5 rounded-md text-xs font-bold border transition-colors ${
                isRebutted
                  ? 'bg-amber-700 text-white border-amber-700'
                  : 'bg-stone-50 dark:bg-[#1a2027] text-stone-700 dark:text-stone-300 border-stone-300 dark:border-stone-700'
              }`}
            >
              Presumption Rebutted
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Revenue Risk Rationale & Evaluation of Assertions
            </label>
            <textarea
              rows={4}
              value={revenueRationale}
              onChange={(e) => setRevenueRationale(e.target.value)}
              placeholder="Describe revenue channels, seasonal spikes, cut-off risks, FOB/CIF shipment terms..."
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 leading-relaxed"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Planned Audit Response (Mandatory Substantive Response under SA 330)
            </label>
            <textarea
              rows={4}
              value={revenuePlannedResponse}
              onChange={(e) => setRevenueResponse(e.target.value)}
              placeholder="e.g. Cut-off testing on dispatches 10 days before and after 31 March, e-Way bill and ICEGATE matching..."
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 leading-relaxed"
            />
          </div>
        </div>
      </div>

      {/* Mandatory Non-Rebuttable Risk 2: Management Override of Controls */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-stone-200 dark:border-stone-800">
          <div>
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
              <Lock className="w-4 h-4 text-amber-700 dark:text-amber-400" />
              <span>2. Risk of Management Override of Controls (SA 240 Para 31 - Non-Rebuttable)</span>
            </h3>
            <p className="text-xs text-stone-500 mt-0.5">
              Management is in a unique position to perpetrate fraud. Mandatory substantive testing of journal entries, estimates, and unusual transactions is required.
            </p>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300">
            Non-Rebuttable
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Override Vulnerability & Entity Environment Rationale
            </label>
            <textarea
              rows={4}
              value={managementRationale}
              onChange={(e) => setManagementRationale(e.target.value)}
              placeholder="Describe access rights, CFO/MD signing authority, non-standard adjustments..."
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 leading-relaxed"
            />
          </div>

          <div>
            <label className="font-semibold text-stone-700 dark:text-stone-300 block mb-1">
              Planned Audit Procedures (Journal Entries & Estimates Testing)
            </label>
            <textarea
              rows={4}
              value={managementPlannedResponse}
              onChange={(e) => setManagementResponse(e.target.value)}
              placeholder="e.g. Electronic extraction of entire GL journal entry population, filtering weekend postings, round-sum entries, retrospective review of estimates..."
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 focus:border-amber-700 leading-relaxed"
            />
          </div>
        </div>
      </div>

      {/* Additional Fraud Risks Register */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-700 dark:text-amber-400" />
              <span>Additional Specific Fraud Risk Factors ({additionalRisks.length})</span>
            </h3>
            <span className="text-xs text-stone-500">
              Incentives, Pressures, Opportunities & Rationalizations
            </span>
          </div>
          <button
            type="button"
            onClick={addAdditionalRisk}
            className="px-3 py-1.5 rounded-md bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 hover:bg-stone-800 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Fraud Risk</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-stone-200 dark:border-stone-800 bg-stone-50 dark:bg-[#1a2027] text-stone-600 dark:text-stone-400">
                <th className="py-2.5 px-3 font-semibold w-1/4">Financial Statement Line Item</th>
                <th className="py-2.5 px-3 font-semibold w-1/4">Fraud Scheme / Type</th>
                <th className="py-2.5 px-3 font-semibold">Fraud Rationale & Motive</th>
                <th className="py-2.5 px-3 font-semibold">Planned Audit Response (SA 330)</th>
                <th className="py-2.5 px-2 font-semibold w-10 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
              {additionalRisks.map((item) => {
                const lineItem = item.lineItemName || item.impactedAccounts || '';
                const fraudType = item.fraudType || item.riskDescription || '';
                const rationale = item.rationale || '';
                const plannedResponse = item.plannedResponse || item.plannedProcedures || '';

                return (
                  <tr key={item.id} className="hover:bg-stone-50/50 dark:hover:bg-[#191e25]">
                    <td className="py-2.5 px-3 align-top">
                      <input
                        type="text"
                        value={lineItem}
                        onChange={(e) => updateAdditionalRisk(item.id, { lineItemName: e.target.value, impactedAccounts: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium"
                      />
                    </td>
                    <td className="py-2.5 px-3 align-top">
                      <input
                        type="text"
                        value={fraudType}
                        onChange={(e) => updateAdditionalRisk(item.id, { fraudType: e.target.value, riskDescription: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100"
                      />
                    </td>
                    <td className="py-2.5 px-3 align-top">
                      <textarea
                        rows={2}
                        value={rationale}
                        onChange={(e) => updateAdditionalRisk(item.id, { rationale: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
                      />
                    </td>
                    <td className="py-2.5 px-3 align-top">
                      <textarea
                        rows={2}
                        value={plannedResponse}
                        onChange={(e) => updateAdditionalRisk(item.id, { plannedResponse: e.target.value, plannedProcedures: e.target.value })}
                        className="w-full px-2 py-1 rounded bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
                      />
                    </td>
                    <td className="py-2.5 px-2 align-top text-center">
                      <button
                        type="button"
                        onClick={() => removeAdditionalRisk(item.id)}
                        className="p-1 rounded text-stone-400 hover:text-rose-600 transition-colors"
                        title="Delete fraud risk"
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
