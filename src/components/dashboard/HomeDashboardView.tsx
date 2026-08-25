import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Clock,
  Sparkles,
  ArrowRight,
  FileText,
  Users,
  Compass,
  DollarSign,
  Fuel,
  Ship,
  CheckCircle2,
  RefreshCw,
  PlusCircle,
  Briefcase,
  Layers,
  ChevronRight,
  FileSpreadsheet
} from 'lucide-react';
import {
  ModuleId,
  DemandGapAnalysis,
  CRMClientAnalytics,
  MarketData,
  VoucherType
} from '../../types';
import { StorageService } from '../../services/storage';

interface HomeDashboardViewProps {
  onNavigate: (module: ModuleId) => void;
  onCreateVoucher: (type?: VoucherType) => void;
  onOpenAIAnalyst: () => void;
  onSelectClient?: (clientId: string) => void;
}

export const HomeDashboardView: React.FC<HomeDashboardViewProps> = ({
  onNavigate,
  onCreateVoucher,
  onOpenAIAnalyst,
  onSelectClient,
}) => {
  const storage = StorageService.getInstance();
  const [demandGaps, setDemandGaps] = useState<DemandGapAnalysis[]>([]);
  const [overdueAlerts, setOverdueAlerts] = useState<CRMClientAnalytics[]>([]);
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [loadingAiNote, setLoadingAiNote] = useState<string | null>(null);
  const [dynamicAiNotes, setDynamicAiNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    const loadDashboardData = () => {
      setDemandGaps(storage.getDemandGapAnalysis());
      setOverdueAlerts(storage.getRepeatOrderAlerts());
      setMarketData(storage.getCachedMarketData());
    };

    loadDashboardData();
    const unsubscribe = storage.subscribe(loadDashboardData);
    return unsubscribe;
  }, []);

  const handleGenerateAiSalesStrategy = async (gap: DemandGapAnalysis) => {
    setLoadingAiNote(gap.requirement.id);
    try {
      const resp = await fetch('/api/intelligence/demand-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clientName: gap.client.name,
          productName: gap.requirement.productName,
          expectedQty: gap.requirement.expectedQuantity,
          actualSupplied: gap.actualQuantitySupplied,
          gapQty: gap.gapQuantity,
          fulfillmentPercent: gap.fulfillmentPercent,
          unit: gap.requirement.unit,
        }),
      });
      const data = await resp.json();
      if (data.advisory) {
        setDynamicAiNotes((prev) => ({
          ...prev,
          [gap.requirement.id]: data.advisory,
        }));
      }
    } catch (err) {
      console.warn('AI Sales strategy generation error', err);
    } finally {
      setLoadingAiNote(null);
    }
  };

  const criticalUnderSupplied = demandGaps.filter((g) => g.isUnderSupplied);
  const companyProfile = storage.getCompanyProfile();

  return (
    <div id="home-dashboard-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Welcome & Operational Status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <span className="text-[11px] font-bold tracking-wider uppercase text-blue-700 bg-blue-50 px-2.5 py-1 rounded border border-blue-200 inline-block mb-1">
            Operations & Executive Overview
          </span>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            {companyProfile.name}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Tanzania Inland Logistics, TRA Tax Invoicing & Real-time Demand-Supply Analytics
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => onCreateVoucher('SALES')}
            className="flex items-center space-x-1.5 px-4 py-2.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold shadow-xs transition"
          >
            <PlusCircle className="w-4 h-4 text-blue-300" />
            <span>New Tax Invoice (INV)</span>
          </button>
          <button
            onClick={() => onCreateVoucher('PROFORMA')}
            className="flex items-center space-x-1.5 px-3.5 py-2.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-lg text-xs font-bold shadow-2xs transition"
          >
            <FileText className="w-4 h-4 text-slate-500" />
            <span>New Proforma (PI)</span>
          </button>
          <button
            onClick={onOpenAIAnalyst}
            className="flex items-center space-x-1.5 px-3.5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-xs transition"
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Trade Analyst</span>
          </button>
        </div>
      </div>

      {/* 3 Executive High-Priority Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Demand-Supply Gaps */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>Demand-Supply Gaps</span>
            </span>
            <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
              {criticalUnderSupplied.length} Under-Supplied
            </span>
          </div>

          <div className="space-y-1">
            <p className="text-2xl font-bold font-mono text-slate-900">
              {criticalUnderSupplied.length > 0 ? `${criticalUnderSupplied.length} Key Accounts` : 'All Fulfillments Healthy'}
            </p>
            <p className="text-xs text-slate-500">
              {criticalUnderSupplied.length > 0
                ? 'Clients with actual sales < 75% of stated requirement.'
                : 'All contracted requirements are tracking on schedule.'}
            </p>
          </div>

          <button
            onClick={() => onNavigate('clientele')}
            className="text-xs font-bold text-blue-700 hover:text-blue-800 flex items-center space-x-1 pt-1"
          >
            <span>Review Client Requirements</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Card 2: Repeat-Order Cycles */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <Clock className="w-4 h-4 text-rose-600" />
              <span>Repeat-Order Overdue</span>
            </span>
            <span className="text-[10px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
              {overdueAlerts.length} Attention Needed
            </span>
          </div>

          <div className="space-y-1">
            <p className="text-2xl font-bold font-mono text-slate-900">
              {overdueAlerts.length > 0 ? `${overdueAlerts.length} Overdue Accounts` : 'Zero Retention Alerts'}
            </p>
            <p className="text-xs text-slate-500">
              {overdueAlerts.length > 0
                ? 'Clients exceeding their typical re-order cadence.'
                : 'Repeat clients are ordering within standard timeframes.'}
            </p>
          </div>

          <button
            onClick={() => onNavigate('clientele')}
            className="text-xs font-bold text-blue-700 hover:text-blue-800 flex items-center space-x-1 pt-1"
          >
            <span>Open Clientele CRM</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Card 3: Market Benchmark Snapshot */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <Compass className="w-4 h-4 text-emerald-600" />
              <span>Live Market Snapshot</span>
            </span>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              BOT & Port
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 bg-slate-50 rounded border border-slate-100">
              <span className="text-[10px] text-slate-500 block">USD / TZS</span>
              <span className="font-bold font-mono text-slate-900">
                TZS {marketData?.forex?.usd_tzs?.rate?.toLocaleString() || '2,615.50'}
              </span>
            </div>
            <div className="p-2 bg-slate-50 rounded border border-slate-100">
              <span className="text-[10px] text-slate-500 block">Bitumen 60/70</span>
              <span className="font-bold font-mono text-slate-900">
                ${marketData?.commodities?.bitumen_60_70_usd_ton?.price || '465'}/MT
              </span>
            </div>
          </div>

          <button
            onClick={() => onNavigate('intelligence')}
            className="text-xs font-bold text-blue-700 hover:text-blue-800 flex items-center space-x-1 pt-1"
          >
            <span>Open Global Intelligence Feed</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Section 1: AI Demand-Supply Gap Insights (Core Highlight) */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>AI Demand-Supply Gap Insights & Sales Pipeline Protection</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated comparison of stated client product requirements against actual invoiced dispatches.
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-500 font-mono">
            {demandGaps.length} Tracked Product Requirements
          </span>
        </div>

        {demandGaps.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 rounded-lg border border-slate-200 space-y-2">
            <p className="text-xs text-slate-600 font-medium">No client product requirements registered yet.</p>
            <p className="text-[11px] text-slate-400">
              Open the Clientele module to configure expected monthly volumes for your key road contractors and fuel fleet accounts.
            </p>
            <button
              onClick={() => onNavigate('clientele')}
              className="mt-2 px-3.5 py-1.5 bg-blue-900 text-white rounded text-xs font-semibold"
            >
              Add Client Requirements
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {demandGaps.map((gap) => {
              const aiNote = dynamicAiNotes[gap.requirement.id] || gap.aiSalesAdvisory;
              const isAnalyzing = loadingAiNote === gap.requirement.id;

              return (
                <div
                  key={gap.requirement.id}
                  className={`p-4 rounded-xl border transition space-y-3 ${
                    gap.isUnderSupplied
                      ? 'bg-amber-50/40 border-amber-200'
                      : 'bg-slate-50/70 border-slate-200'
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-bold text-slate-900 text-sm">{gap.client.name}</h3>
                        {gap.isUnderSupplied ? (
                          <span className="px-2 py-0.5 bg-rose-100 text-rose-800 font-bold rounded text-[10px] border border-rose-200 flex items-center space-x-1">
                            <AlertTriangle className="w-3 h-3" />
                            <span>Under-Supplied (Lost Revenue Risk)</span>
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold rounded text-[10px] border border-emerald-200 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Target Fulfilled</span>
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-semibold text-slate-700">
                        {gap.requirement.productName}
                      </p>
                    </div>

                    <div className="flex items-center space-x-3 text-xs">
                      <div className="text-right">
                        <span className="text-[10px] text-slate-500 block">Stated Demand</span>
                        <span className="font-bold font-mono text-slate-800">
                          {gap.requirement.expectedQuantity} {gap.requirement.unit} / {gap.requirement.period}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-500 block">Actual Invoiced</span>
                        <span className="font-bold font-mono text-slate-900">
                          {gap.actualQuantitySupplied} {gap.requirement.unit}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-500 block">Unfulfilled Gap</span>
                        <span className={`font-bold font-mono ${gap.gapQuantity > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                          {gap.gapQuantity} {gap.requirement.unit}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Progress Fulfillment Bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-slate-500 font-medium">Monthly Fulfillment Ratio:</span>
                      <span className="font-bold font-mono text-slate-900">
                        {gap.fulfillmentPercent}% ({gap.actualQuantitySupplied} / {gap.requirement.expectedQuantity} {gap.requirement.unit})
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          gap.fulfillmentPercent >= 75
                            ? 'bg-emerald-500'
                            : gap.fulfillmentPercent >= 40
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${Math.min(100, gap.fulfillmentPercent)}%` }}
                      />
                    </div>
                  </div>

                  {/* AI Plain-Language Recommendation */}
                  <div className="p-3 bg-white rounded-lg border border-slate-200/80 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 flex items-center space-x-1.5 text-[11px] uppercase tracking-wider">
                        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                        <span>AI B2B Sales Strategy & Recommendation:</span>
                      </span>
                      <button
                        onClick={() => handleGenerateAiSalesStrategy(gap)}
                        disabled={isAnalyzing}
                        className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold flex items-center space-x-1 transition disabled:opacity-50"
                      >
                        <RefreshCw className={`w-3 h-3 ${isAnalyzing ? 'animate-spin' : ''}`} />
                        <span>{isAnalyzing ? 'Analyzing...' : 'Generate New AI Note'}</span>
                      </button>
                    </div>
                    <p className="text-slate-600 leading-relaxed text-xs">
                      {aiNote}
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-slate-500">
                      Estimated Uncaptured Revenue: <strong className="font-mono text-slate-800">TZS {gap.estimatedLostRevenueTZS.toLocaleString()}</strong>
                    </span>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => onCreateVoucher('PROFORMA')}
                        className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded text-xs font-semibold shadow-2xs"
                      >
                        Issue Proforma (PI)
                      </button>
                      <button
                        onClick={() => onCreateVoucher('SALES')}
                        className="px-3 py-1.5 bg-blue-900 hover:bg-blue-800 text-white rounded text-xs font-semibold shadow-2xs"
                      >
                        Create Tax Invoice
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Section 2: Repeat Order Alerts & Live News Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Repeat Order Overdue Accounts */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <Clock className="w-4 h-4 text-rose-600" />
              <span>Repeat-Order Overdue Alerts ({overdueAlerts.length})</span>
            </h3>
            <span className="text-[10px] text-slate-400">Automated Cadence Detection</span>
          </div>

          {overdueAlerts.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-4 text-center">
              All repeat clients have ordered within their usual purchasing schedule.
            </p>
          ) : (
            <div className="space-y-2.5">
              {overdueAlerts.map((alert) => (
                <div
                  key={alert.client.id}
                  className="p-3 bg-rose-50/50 border border-rose-200 rounded-lg flex items-center justify-between text-xs"
                >
                  <div className="space-y-0.5">
                    <h4 className="font-bold text-slate-900">{alert.client.name}</h4>
                    <p className="text-[11px] text-slate-500">
                      Normal Cycle: every {alert.averageDaysBetweenOrders} days | Last order: {alert.daysSinceLastOrder} days ago
                    </p>
                  </div>
                  <button
                    onClick={() => onCreateVoucher('PROFORMA')}
                    className="px-2.5 py-1 bg-white hover:bg-rose-100 text-rose-800 border border-rose-300 rounded font-semibold text-[11px] transition shadow-2xs"
                  >
                    Follow Up
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Global Trade & News Snapshot */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2">
              <Compass className="w-4 h-4 text-blue-600" />
              <span>East Africa Trade & Corridor Intelligence</span>
            </h3>
            <button
              onClick={() => onNavigate('intelligence')}
              className="text-[11px] text-blue-700 hover:text-blue-800 font-semibold flex items-center space-x-1"
            >
              <span>Full Feed</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="space-y-2.5">
            {marketData?.marketNews && marketData.marketNews.length > 0 ? (
              marketData.marketNews.slice(0, 2).map((item) => (
                <div key={item.id} className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 space-y-1 text-xs">
                  <div className="flex items-center space-x-2">
                    <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 font-bold rounded text-[9px]">
                      {item.category}
                    </span>
                    <span className="text-[10px] text-slate-400">{item.timestamp}</span>
                  </div>
                  <h4 className="font-bold text-slate-800 line-clamp-1">{item.title}</h4>
                  <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">{item.summary}</p>
                </div>
              ))
            ) : (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-500">
                <p>Dar Port corridor & BOT indicative feeds active. Click below to refresh intelligence.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
