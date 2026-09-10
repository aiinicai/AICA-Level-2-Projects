import React from 'react';
import { EngagementData, MaterialityBenchmark, SpecificMaterialityItem } from '../../types';
import { computeMateriality, formatINR, formatCompactINR } from '../../utils/calculations';
import { Scale, Info, Plus, Trash2, ShieldAlert, Sparkles } from 'lucide-react';

interface Stage10Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
}

const BENCHMARK_GUIDELINES: Record<string, { range: string; notes: string }> = {
  'Profit before Tax': {
    range: '5.0% – 10.0%',
    notes: 'Standard choice for commercial profit-oriented entities with stable trading history.',
  },
  'Profit Before Tax (PBT) from Continuing Operations': {
    range: '5.0% – 10.0%',
    notes: 'Standard choice for commercial profit-oriented entities with stable trading history.',
  },
  'Revenue from Operations': {
    range: '0.5% – 1.0%',
    notes: 'Preferred when PBT is volatile or near breakeven, or in high-volume, low-margin sectors.',
  },
  'Total Revenue / Turnover': {
    range: '0.5% – 1.0%',
    notes: 'Preferred when PBT is volatile or near breakeven, or in high-volume, low-margin sectors.',
  },
  'Gross Profit': {
    range: '1.0% – 2.0%',
    notes: 'Used in retail or distribution when operating expenses fluctuate significantly.',
  },
  'Total Assets': {
    range: '0.5% – 1.0%',
    notes: 'Common for asset-intensive manufacturing, property, investment holding companies.',
  },
  'Net Assets (Equity)': {
    range: '1.0% – 2.0%',
    notes: 'Applicable for start-ups, entities in development stage, or non-profit entities.',
  },
  'Total Equity / Net Assets': {
    range: '1.0% – 2.0%',
    notes: 'Applicable for start-ups, entities in development stage, or non-profit entities.',
  },
};

export const Stage10Materiality: React.FC<Stage10Props> = ({
  engagement,
  onChange,
}) => {
  const computed = computeMateriality(engagement.materiality);

  const updateMateriality = (updates: Partial<EngagementData['materiality']>) => {
    onChange({
      ...engagement,
      materiality: {
        ...engagement.materiality,
        ...updates,
      },
    });
  };

  const addSpecificItem = () => {
    const newItem: SpecificMaterialityItem = {
      id: `spec-${Date.now()}`,
      areaOrAccount: 'Related Party Transactions (Sec 188)',
      materialityAmount: 250000,
      rationale: 'Heightened sensitivity and statutory disclosure under Companies Act 2013 and AS 18',
    };
    const current = engagement.materiality.specificMateriality || [];
    updateMateriality({ specificMateriality: [...current, newItem] });
  };

  const updateSpecificItem = (id: string, updates: Partial<SpecificMaterialityItem>) => {
    const current = engagement.materiality.specificMateriality || [];
    const updated = current.map((s) => (s.id === id ? { ...s, ...updates } : s));
    updateMateriality({ specificMateriality: updated });
  };

  const removeSpecificItem = (id: string) => {
    const current = engagement.materiality.specificMateriality || [];
    updateMateriality({ specificMateriality: current.filter((s) => s.id !== id) });
  };

  const currentGuideline = BENCHMARK_GUIDELINES[engagement.materiality.benchmarkBasis] || {
    range: '5.0% – 10.0%',
    notes: 'Standard commercial entity benchmark under SA 320',
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
            Stage 10 • SA 320 & SA 450
          </span>
          <span className="text-xs text-stone-500">Materiality in Planning and Evaluating Misstatements</span>
        </div>
        <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
          Materiality Determination & Computation Engine
        </h2>
        <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
          Establish Overall Materiality (OM), Performance Materiality (PM) to reduce aggregate uncorrected misstatements to an acceptably low level, and the Clearly Trivial threshold (CT).
        </p>
      </div>

      {/* 3 Materiality Calculation Result Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Overall Materiality */}
        <div className="bg-white dark:bg-[#15191f] p-5 rounded-xl border-2 border-stone-800 dark:border-stone-600 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-stone-500 tracking-wider">
              Overall Materiality (OM)
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 font-mono-num">
              {engagement.materiality.omPercent}% of {engagement.materiality.benchmarkBasis.split(' ')[0]}
            </span>
          </div>
          <p className="text-2xl sm:text-3xl font-serif font-bold text-stone-900 dark:text-stone-100 font-mono-num">
            {formatINR(computed.overallMateriality)}
          </p>
          <p className="text-xs text-stone-500">
            Compact: <span className="font-semibold text-stone-800 dark:text-stone-200">{formatCompactINR(computed.overallMateriality)}</span> • SA 320 Para 10
          </p>
        </div>

        {/* Performance Materiality */}
        <div className="bg-white dark:bg-[#15191f] p-5 rounded-xl border-2 border-amber-700 dark:border-amber-500 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-amber-800 dark:text-amber-400 tracking-wider">
              Performance Mat. (PM)
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 font-mono-num">
              {engagement.materiality.pmPercent}% of OM
            </span>
          </div>
          <p className="text-2xl sm:text-3xl font-serif font-bold text-amber-900 dark:text-amber-300 font-mono-num">
            {formatINR(computed.performanceMateriality)}
          </p>
          <p className="text-xs text-stone-500">
            Compact: <span className="font-semibold text-amber-800 dark:text-amber-300">{formatCompactINR(computed.performanceMateriality)}</span> • Scope of TOD testing
          </p>
        </div>

        {/* Clearly Trivial */}
        <div className="bg-white dark:bg-[#15191f] p-5 rounded-xl border border-stone-300 dark:border-stone-700 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-bold text-stone-500 tracking-wider">
              Clearly Trivial (CT)
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 font-mono-num">
              {engagement.materiality.clearlyTrivialPercent}% of OM
            </span>
          </div>
          <p className="text-2xl sm:text-3xl font-serif font-bold text-stone-700 dark:text-stone-300 font-mono-num">
            {formatINR(computed.clearlyTrivialThreshold)}
          </p>
          <p className="text-xs text-stone-500">
            Compact: <span className="font-semibold text-stone-700 dark:text-stone-300">{formatCompactINR(computed.clearlyTrivialThreshold)}</span> • SA 450 SAD limit
          </p>
        </div>
      </div>

      {/* Interactive Parameters Input */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-5">
        <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
          Benchmark Selection & Percentages Configuration
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs">
          {/* Benchmark Selection */}
          <div className="space-y-1.5">
            <label className="font-semibold text-stone-700 dark:text-stone-300 block">
              1. Primary Benchmark Basis (SA 320 Para A3)
            </label>
            <select
              value={engagement.materiality.benchmarkBasis}
              onChange={(e) => updateMateriality({ benchmarkBasis: e.target.value as MaterialityBenchmark })}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium focus:border-amber-700"
            >
              <option value="Profit Before Tax (PBT) from Continuing Operations">
                Profit Before Tax (PBT) from Continuing Operations
              </option>
              <option value="Total Revenue / Turnover">Total Revenue / Turnover</option>
              <option value="Gross Profit">Gross Profit</option>
              <option value="Total Assets">Total Assets</option>
              <option value="Total Equity / Net Assets">Total Equity / Net Assets</option>
            </select>
            <p className="text-[11px] text-stone-500">
              Guidance Range: <span className="font-bold text-amber-800 dark:text-amber-400">{currentGuideline.range}</span> — {currentGuideline.notes}
            </p>
          </div>

          {/* Benchmark Amount */}
          <div className="space-y-1.5">
            <label className="font-semibold text-stone-700 dark:text-stone-300 block">
              2. Benchmark Financial Figure (in INR ₹)
            </label>
            <input
              type="number"
              step="10000"
              value={engagement.materiality.benchmarkAmount}
              onChange={(e) => updateMateriality({ benchmarkAmount: parseFloat(e.target.value) || 0 })}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-mono-num text-sm focus:border-amber-700"
            />
            <p className="text-[11px] text-stone-500 font-mono-num">
              Formatted: {formatINR(engagement.materiality.benchmarkAmount)} ({formatCompactINR(engagement.materiality.benchmarkAmount)})
            </p>
          </div>

          {/* OM Percentage */}
          <div className="space-y-2 p-3.5 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-800">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-stone-700 dark:text-stone-300">
                Overall Materiality Percentage: <span className="font-mono-num font-bold text-amber-800 dark:text-amber-400">{engagement.materiality.omPercent}%</span>
              </label>
              <span className="text-[10px] text-stone-500">Normal range: 0.5% - 10%</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="15.0"
              step="0.1"
              value={engagement.materiality.omPercent}
              onChange={(e) => updateMateriality({ omPercent: parseFloat(e.target.value) })}
              className="w-full accent-amber-800"
            />
            <div className="flex justify-between text-[10px] text-stone-400 font-mono-num">
              <span>0.1%</span>
              <span>1.0% (Turnover)</span>
              <span>5.0% (PBT)</span>
              <span>10.0%</span>
              <span>15.0%</span>
            </div>
          </div>

          {/* PM Percentage */}
          <div className="space-y-2 p-3.5 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-800">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-stone-700 dark:text-stone-300">
                Performance Materiality (% of OM): <span className="font-mono-num font-bold text-amber-800 dark:text-amber-400">{engagement.materiality.pmPercent}%</span>
              </label>
              <span className="text-[10px] text-stone-500">Typical range: 50% – 75%</span>
            </div>
            <input
              type="range"
              min="40"
              max="85"
              step="5"
              value={engagement.materiality.pmPercent}
              onChange={(e) => updateMateriality({ pmPercent: parseInt(e.target.value) })}
              className="w-full accent-amber-800"
            />
            <div className="flex justify-between text-[10px] text-stone-400 font-mono-num">
              <span>50% (High Risk)</span>
              <span>65%</span>
              <span>75% (Low Risk)</span>
            </div>
          </div>

          {/* CT Percentage */}
          <div className="space-y-2 p-3.5 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-800 md:col-span-2">
            <div className="flex items-center justify-between">
              <label className="font-semibold text-stone-700 dark:text-stone-300">
                Clearly Trivial Threshold (% of OM, SA 450): <span className="font-mono-num font-bold text-stone-800 dark:text-stone-200">{engagement.materiality.clearlyTrivialPercent}%</span>
              </label>
              <span className="text-[10px] text-stone-500">Standard ICAI practice: 3% to 5%</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              step="0.5"
              value={engagement.materiality.clearlyTrivialPercent}
              onChange={(e) => updateMateriality({ clearlyTrivialPercent: parseFloat(e.target.value) })}
              className="w-full accent-stone-700"
            />
          </div>
        </div>

        {/* Professional Rationale Documentation */}
        <div className="pt-2 text-xs space-y-1">
          <label className="font-semibold text-stone-700 dark:text-stone-300 block">
            Auditor Professional Justification for Benchmark & Percentages Selection (SA 320 Para 14)
          </label>
          <textarea
            rows={3}
            value={engagement.materiality.rationale}
            onChange={(e) => updateMateriality({ rationale: e.target.value })}
            placeholder="Document qualitative rationale, user focus, covenant requirements, and historical audit misstatement history..."
            className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs focus:border-amber-700 leading-relaxed"
          />
        </div>
      </div>

      {/* Specific Materiality for Particular Classes */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
              Specific Materiality for Sensitive Classes of Transactions (SA 320 Para 10)
            </h3>
            <p className="text-xs text-stone-500">
              Lower thresholds applicable to particular accounts influenced by law, regulation, or stakeholder sensitivity.
            </p>
          </div>
          <button
            type="button"
            onClick={addSpecificItem}
            className="px-3 py-1.5 rounded-md bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 hover:bg-stone-800 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Specific Class</span>
          </button>
        </div>

        <div className="space-y-3">
          {(engagement.materiality.specificMateriality || []).map((spec) => (
            <div
              key={spec.id}
              className="p-3.5 rounded-lg border border-stone-200 dark:border-stone-800 bg-stone-50/50 dark:bg-[#1a2027] grid grid-cols-1 md:grid-cols-4 gap-3 text-xs items-center"
            >
              <div>
                <label className="font-semibold text-stone-600 dark:text-stone-400 block mb-0.5">
                  Account / Class
                </label>
                <input
                  type="text"
                  value={spec.areaOrAccount}
                  onChange={(e) => updateSpecificItem(spec.id, { areaOrAccount: e.target.value })}
                  className="w-full px-2 py-1 rounded bg-white dark:bg-[#15191f] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-medium"
                />
              </div>

              <div>
                <label className="font-semibold text-stone-600 dark:text-stone-400 block mb-0.5">
                  Specific Materiality (₹)
                </label>
                <input
                  type="number"
                  value={spec.materialityAmount}
                  onChange={(e) => updateSpecificItem(spec.id, { materialityAmount: parseFloat(e.target.value) || 0 })}
                  className="w-full px-2 py-1 rounded bg-white dark:bg-[#15191f] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 font-mono-num"
                />
                <span className="text-[10px] text-stone-500 font-mono-num">
                  {formatINR(spec.materialityAmount)}
                </span>
              </div>

              <div className="md:col-span-2 flex items-center gap-2">
                <div className="flex-1">
                  <label className="font-semibold text-stone-600 dark:text-stone-400 block mb-0.5">
                    Basis & Statutory Reference
                  </label>
                  <input
                    type="text"
                    value={spec.rationale}
                    onChange={(e) => updateSpecificItem(spec.id, { rationale: e.target.value })}
                    className="w-full px-2 py-1 rounded bg-white dark:bg-[#15191f] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeSpecificItem(spec.id)}
                  className="p-1 text-stone-400 hover:text-rose-600 transition-colors mt-4"
                  title="Remove specific class"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
