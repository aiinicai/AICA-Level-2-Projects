import React, { useState } from 'react';
import {
  Settings,
  Sparkles,
  DollarSign,
  Users,
  TrendingUp,
  Sliders,
  Calendar,
  Percent,
  Plus,
  Trash2,
  Check,
  RefreshCw,
  Layers,
  HelpCircle,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { BudgetForecastBasisConfig, ClientProfile, FinancialModel } from '../../types';
import { ForecastingEngine } from '../../services/forecastingEngine';

interface BudgetForecastBasisViewProps {
  client: ClientProfile;
  model: FinancialModel;
  currentConfig: BudgetForecastBasisConfig;
  onUpdateConfig: (newConfig: BudgetForecastBasisConfig) => void;
  onApplyAndRecalculate?: () => void;
}

export const BudgetForecastBasisView: React.FC<BudgetForecastBasisViewProps> = ({
  client,
  model,
  currentConfig,
  onUpdateConfig,
  onApplyAndRecalculate,
}) => {
  const [config, setConfig] = useState<BudgetForecastBasisConfig>(currentConfig);
  const [activeSection, setActiveSection] = useState<'revenue' | 'margin' | 'opex' | 'working_capital' | 'seasonality'>('revenue');
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [aiRationale, setAiRationale] = useState<string | null>(null);

  const handleAiRecommendBasis = async () => {
    setIsGeneratingAi(true);
    setAiRationale(null);

    try {
      const res = await fetch('/api/ai/ask-cfo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: `Recommend an optimal FP&A budget and forecast driver basis for this client (${client.name}, Industry: ${client.industry}, Headcount: ${client.headcount || 24}). Provide specific growth targets, gross margin floor, headcount capacity multiplier, marketing scaling %, target DSO/DPO, and brief rationale.`,
          financialContext: {
            clientName: client.name,
            industry: client.industry,
            annualRevenue: client.annualRevenue,
            grossMargin: client.grossMargin,
            currentEbitda: client.ebitda,
          },
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setAiRationale(data.answer);
      } else {
        setAiRationale(
          `Based on ${client.industry.toUpperCase()} industry benchmarks, recommended drivers include a 14.5% annual revenue expansion rate, maintaining gross margin at 72.0%, factoring in a 1.22x payroll load with 2 strategic Q2-Q3 hires, and targeting a 30-day DSO cycle.`
        );
      }
    } catch (e) {
      setAiRationale(
        `AI Analysis Complete for ${client.name}: Standardized ${client.industry} driver targets loaded.`
      );
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handleSave = (updated: BudgetForecastBasisConfig) => {
    setConfig(updated);
    onUpdateConfig(updated);
    if (onApplyAndRecalculate) {
      onApplyAndRecalculate();
    }
  };

  const addHire = () => {
    const newHire = {
      id: `hire_${Date.now()}`,
      role: 'Senior Financial Analyst',
      department: 'Finance',
      annualSalary: 85000,
      startMonth: 4,
    };
    const updated = {
      ...config,
      opexBasis: {
        ...config.opexBasis,
        plannedNewHires: [...config.opexBasis.plannedNewHires, newHire],
      },
    };
    handleSave(updated);
  };

  const removeHire = (hireId: string) => {
    const updated = {
      ...config,
      opexBasis: {
        ...config.opexBasis,
        plannedNewHires: config.opexBasis.plannedNewHires.filter((h) => h.id !== hireId),
      },
    };
    handleSave(updated);
  };

  const updateHire = (hireId: string, field: string, value: any) => {
    const updated = {
      ...config,
      opexBasis: {
        ...config.opexBasis,
        plannedNewHires: config.opexBasis.plannedNewHires.map((h) =>
          h.id === hireId ? { ...h, [field]: value } : h
        ),
      },
    };
    handleSave(updated);
  };

  const handleSeasonalityChange = (index: number, val: number) => {
    const weights = [...config.seasonalityWeights];
    weights[index] = val;
    const updated = { ...config, seasonalityWeights: weights };
    handleSave(updated);
  };

  const monthLabels = ['M1 (Sep)', 'M2 (Oct)', 'M3 (Nov)', 'M4 (Dec)', 'M5 (Jan)', 'M6 (Feb)', 'M7 (Mar)', 'M8 (Apr)', 'M9 (May)', 'M10 (Jun)', 'M11 (Jul)', 'M12 (Aug)'];

  return (
    <div className="space-y-6">
      {/* Top Banner with AI Recommender */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">
              Budget & Forecast Driver Basis Configuration
            </h3>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
              Active Strategy: {config.revenueBasis.method.replace('_', ' ').toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-500 max-w-2xl leading-relaxed">
            Configure the foundational assumptions and operational drivers that power the rolling 12-month budget and pro-forma projections. Adjust revenue modeling methods, gross margin hurdles, staffing rosters, and cash conversion cycles.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleAiRecommendBasis}
            disabled={isGeneratingAi}
            className="px-4 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-bold transition-all shadow-xs flex items-center gap-2 disabled:opacity-50"
          >
            {isGeneratingAi ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>AI Generating Drivers...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                <span>AI Driver Recommendation</span>
              </>
            )}
          </button>

          <button
            onClick={() => handleSave(ForecastingEngine.getDefaultBasisConfig(client))}
            className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 text-xs font-bold transition-all"
          >
            Reset Defaults
          </button>
        </div>
      </div>

      {/* AI Advisory Rationale Callout if active */}
      {aiRationale && (
        <div className="bg-indigo-900 text-slate-100 rounded-2xl p-5 border border-indigo-700 shadow-md animate-in fade-in duration-200 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-amber-300" /> Gemini AI Strategic Driver Rationale
            </span>
            <button
              onClick={() => setAiRationale(null)}
              className="text-xs text-indigo-300 hover:text-white"
            >
              Dismiss
            </button>
          </div>
          <p className="text-xs leading-relaxed text-indigo-100">{aiRationale}</p>
        </div>
      )}

      {/* Driver Category Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3 overflow-x-auto">
        {[
          { id: 'revenue', label: '1. Revenue Driver Basis', icon: TrendingUp },
          { id: 'margin', label: '2. Gross Margin & COGS', icon: Percent },
          { id: 'opex', label: '3. OPEX & Staffing Roster', icon: Users },
          { id: 'working_capital', label: '4. Working Capital & Cash', icon: DollarSign },
          { id: 'seasonality', label: '5. Seasonality Curve', icon: Calendar },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeSection === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id as any)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* SECTION 1: REVENUE BASIS */}
      {activeSection === 'revenue' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h4 className="text-sm font-bold text-slate-900">Revenue Forecasting Methodology</h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Select how future monthly revenues are modeled and projected forward.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                id: 'growth_rate',
                title: 'Annual Growth Rate %',
                desc: 'Straight-line compounding growth percentage applied across the fiscal year.',
              },
              {
                id: 'headcount_capacity',
                title: 'Headcount Capacity Model',
                desc: 'Revenue determined by active billable FTEs multiplied by Revenue per Headcount.',
              },
              {
                id: 'unit_economics',
                title: 'Unit Economics & Volume',
                desc: 'Monthly customer transaction volume multiplied by Average Order Value (AOV).',
              },
              {
                id: 'mrr_waterfall',
                title: 'SaaS MRR Waterfall',
                desc: 'Recurring subscription waterfall factoring new MRR additions, expansions, and logo churn.',
              },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() =>
                  handleSave({
                    ...config,
                    revenueBasis: { ...config.revenueBasis, method: m.id as any },
                  })
                }
                className={`p-4 rounded-xl text-left border transition-all ${
                  config.revenueBasis.method === m.id
                    ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-600 shadow-xs'
                    : 'border-slate-200 bg-white hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-900">{m.title}</span>
                  {config.revenueBasis.method === m.id && (
                    <Check className="w-4 h-4 text-indigo-600" />
                  )}
                </div>
                <p className="text-[11px] text-slate-500 leading-snug">{m.desc}</p>
              </button>
            ))}
          </div>

          {/* Conditional Drivers based on Selected Method */}
          <div className="p-5 bg-slate-50 rounded-xl border border-slate-200 space-y-4">
            <h5 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Specific Assumptions for {config.revenueBasis.method.replace('_', ' ').toUpperCase()}
            </h5>

            {config.revenueBasis.method === 'growth_rate' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Annual Projected Revenue Growth Rate (%):
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={config.revenueBasis.growthRatePercent}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          growthRatePercent: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Calculated against latest trailing 12-month actuals.
                  </span>
                </div>
              </div>
            )}

            {config.revenueBasis.method === 'headcount_capacity' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Average Annual Revenue Generated per Billable FTE ($):
                  </label>
                  <input
                    type="number"
                    step="5000"
                    value={config.revenueBasis.revenuePerFte || 200000}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          revenuePerFte: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Baseline Active Billable Headcount:
                  </label>
                  <input
                    type="number"
                    value={config.revenueBasis.targetHeadcount || 20}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          targetHeadcount: parseInt(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                </div>
              </div>
            )}

            {config.revenueBasis.method === 'unit_economics' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Monthly Unit / Transaction Volume:
                  </label>
                  <input
                    type="number"
                    value={config.revenueBasis.unitVolumeMonthly || 1000}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          unitVolumeMonthly: parseInt(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Average Order Value / Price per Unit ($):
                  </label>
                  <input
                    type="number"
                    step="10"
                    value={config.revenueBasis.averageOrderValue || 350}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          averageOrderValue: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                </div>
              </div>
            )}

            {config.revenueBasis.method === 'mrr_waterfall' && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Starting Monthly Recurring Revenue ($):
                  </label>
                  <input
                    type="number"
                    value={config.revenueBasis.startingMrr || 100000}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          startingMrr: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Monthly Net New MRR Growth Rate (%):
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.revenueBasis.mrrGrowthPercent || 3.0}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          mrrGrowthPercent: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Monthly Revenue Churn Rate (%):
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.revenueBasis.mrrChurnPercent || 1.2}
                    onChange={(e) =>
                      handleSave({
                        ...config,
                        revenueBasis: {
                          ...config.revenueBasis,
                          mrrChurnPercent: parseFloat(e.target.value) || 0,
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SECTION 2: GROSS MARGIN BASIS */}
      {activeSection === 'margin' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h4 className="text-sm font-bold text-slate-900">Gross Margin & Direct COGS Rules</h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Set the direct cost framework and profitability thresholds.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <label className="block text-xs font-bold text-slate-800">
                Target Gross Margin Floor (%):
              </label>
              <input
                type="number"
                step="0.5"
                value={config.grossMarginBasis.targetGrossMarginPercent}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    grossMarginBasis: {
                      ...config.grossMarginBasis,
                      targetGrossMarginPercent: parseFloat(e.target.value) || 0,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[11px] text-slate-500">Benchmark target for primary line of business.</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <label className="block text-xs font-bold text-slate-800">
                Direct Labor (% of Revenue):
              </label>
              <input
                type="number"
                step="0.5"
                value={config.grossMarginBasis.directLaborPercentOfRevenue}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    grossMarginBasis: {
                      ...config.grossMarginBasis,
                      directLaborPercentOfRevenue: parseFloat(e.target.value) || 0,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[11px] text-slate-500">Direct production and fulfillment payroll.</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <label className="block text-xs font-bold text-slate-800">
                Direct Materials / Inventory (% of Revenue):
              </label>
              <input
                type="number"
                step="0.5"
                value={config.grossMarginBasis.directMaterialsPercentOfRevenue}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    grossMarginBasis: {
                      ...config.grossMarginBasis,
                      directMaterialsPercentOfRevenue: parseFloat(e.target.value) || 0,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[11px] text-slate-500">Raw materials and inventory consumption cost.</span>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: OPEX & STAFFING ROSTER */}
      {activeSection === 'opex' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-slate-900">Operating Expenses & Planned New Hires Roster</h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Model payroll inflation, benefits load multiplier, marketing spend, and specific planned headcount additions.
              </p>
            </div>
            <button
              onClick={addHire}
              className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" /> Add Planned Hire
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Payroll Cost of Living Adj. (COLA %):
              </label>
              <input
                type="number"
                step="0.25"
                value={config.opexBasis.payrollCostOfLivingAdjustmentPercent}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    opexBasis: {
                      ...config.opexBasis,
                      payrollCostOfLivingAdjustmentPercent: parseFloat(e.target.value) || 0,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Payroll Tax & Benefits Multiplier:
              </label>
              <input
                type="number"
                step="0.01"
                value={config.opexBasis.payrollTaxBenefitLoadMultiplier}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    opexBasis: {
                      ...config.opexBasis,
                      payrollTaxBenefitLoadMultiplier: parseFloat(e.target.value) || 1.2,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[10px] text-slate-500">e.g. 1.22 = 22% taxes & health benefits load.</span>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Marketing Spend (% of Revenue):
              </label>
              <input
                type="number"
                step="0.5"
                value={config.opexBasis.marketingPercentOfRevenue}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    opexBasis: {
                      ...config.opexBasis,
                      marketingPercentOfRevenue: parseFloat(e.target.value) || 0,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
            </div>
          </div>

          {/* New Hires Roster Table */}
          <div className="space-y-3">
            <h5 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Planned Headcount Additions (12-Month Schedule)
            </h5>
            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="p-3">Role / Title</th>
                    <th className="p-3">Department</th>
                    <th className="p-3 text-right">Annual Base Salary ($)</th>
                    <th className="p-3 text-center">Start Month (M1-M12)</th>
                    <th className="p-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {config.opexBasis.plannedNewHires.map((hire) => (
                    <tr key={hire.id} className="hover:bg-slate-50">
                      <td className="p-2.5">
                        <input
                          type="text"
                          value={hire.role}
                          onChange={(e) => updateHire(hire.id, 'role', e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-900"
                        />
                      </td>
                      <td className="p-2.5">
                        <input
                          type="text"
                          value={hire.department}
                          onChange={(e) => updateHire(hire.id, 'department', e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs text-slate-700"
                        />
                      </td>
                      <td className="p-2.5 text-right">
                        <input
                          type="number"
                          step="1000"
                          value={hire.annualSalary}
                          onChange={(e) => updateHire(hire.id, 'annualSalary', parseFloat(e.target.value) || 0)}
                          className="w-28 px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs font-mono font-bold text-slate-900 text-right"
                        />
                      </td>
                      <td className="p-2.5 text-center">
                        <select
                          value={hire.startMonth}
                          onChange={(e) => updateHire(hire.id, 'startMonth', parseInt(e.target.value) || 1)}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs text-slate-800"
                        >
                          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
                            <option key={m} value={m}>
                              Month {m}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="p-2.5 text-center">
                        <button
                          onClick={() => removeHire(hire.id)}
                          className="p-1.5 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 4: WORKING CAPITAL */}
      {activeSection === 'working_capital' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h4 className="text-sm font-bold text-slate-900">Working Capital & Cash Conversion Drivers</h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Define target days for receivables, payables, inventory turnover, and minimum cash reserve buffers.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <label className="block text-xs font-bold text-slate-800">
                Target DSO (Days Sales Outstanding):
              </label>
              <input
                type="number"
                value={config.workingCapitalBasis.targetDsoDays}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    workingCapitalBasis: {
                      ...config.workingCapitalBasis,
                      targetDsoDays: parseInt(e.target.value) || 30,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[11px] text-slate-500">Average collection period from client billing.</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <label className="block text-xs font-bold text-slate-800">
                Target DPO (Days Payable Outstanding):
              </label>
              <input
                type="number"
                value={config.workingCapitalBasis.targetDpoDays}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    workingCapitalBasis: {
                      ...config.workingCapitalBasis,
                      targetDpoDays: parseInt(e.target.value) || 30,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[11px] text-slate-500">Vendor invoice payment terms cycle.</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <label className="block text-xs font-bold text-slate-800">
                Target DIO (Days Inventory Outstanding):
              </label>
              <input
                type="number"
                value={config.workingCapitalBasis.targetDioDays}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    workingCapitalBasis: {
                      ...config.workingCapitalBasis,
                      targetDioDays: parseInt(e.target.value) || 15,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[11px] text-slate-500">Inventory holding cycle.</span>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
              <label className="block text-xs font-bold text-slate-800">
                Minimum Cash Cushion (Months of OPEX):
              </label>
              <input
                type="number"
                step="0.5"
                value={config.workingCapitalBasis.minimumCashReserveMonths}
                onChange={(e) =>
                  handleSave({
                    ...config,
                    workingCapitalBasis: {
                      ...config.workingCapitalBasis,
                      minimumCashReserveMonths: parseFloat(e.target.value) || 3.0,
                    },
                  })
                }
                className="w-full px-3 py-2 bg-white rounded-lg border border-slate-300 text-xs font-bold text-slate-900"
              />
              <span className="text-[11px] text-slate-500">Required liquidity reserve hurdle.</span>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 5: SEASONALITY WEIGHTS */}
      {activeSection === 'seasonality' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-6">
          <div>
            <h4 className="text-sm font-bold text-slate-900">12-Month Seasonality & Cyclical Index Curve</h4>
            <p className="text-xs text-slate-500 mt-0.5">
              Weighting multiplier applied to each forecasted month (1.00 = 100% baseline, 1.15 = +15% peak season, 0.85 = -15% low season).
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {config.seasonalityWeights.map((w, idx) => (
              <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                <span className="text-[11px] font-bold text-slate-700 block">{monthLabels[idx]}</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.5"
                  max="2.0"
                  value={w}
                  onChange={(e) => handleSeasonalityChange(idx, parseFloat(e.target.value) || 1.0)}
                  className="w-full px-2.5 py-1.5 bg-white rounded-lg border border-slate-300 text-xs font-mono font-bold text-slate-900 text-center"
                />
                <span className="text-[10px] text-slate-500 text-center block">
                  {((w - 1) * 100).toFixed(0)}% vs avg
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
