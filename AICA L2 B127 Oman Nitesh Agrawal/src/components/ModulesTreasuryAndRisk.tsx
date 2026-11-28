import React, { useMemo, useState } from 'react';
import {
  formatMoney,
  formatPct,
  formatRatio,
  roundOMR,
  runScenarioSimulation,
  safeDiv,
  type ProjectKpiSummary,
} from '../engine/kpiEngine';
import type { CurrencyCode, MisDataset, ScenarioParameters } from '../types/mis';
import { MaskedValue } from './MaskedValue';
import { TrendLineChart } from './Charts';

export const FinancingCovenantsView: React.FC<{
  dataset: MisDataset;
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, currency, masked }) => {
  const totLimit = roundOMR(dataset.facilities.reduce((a, f) => a + f.facilityLimitOMR, 0));
  const totDrawn = roundOMR(dataset.facilities.reduce((a, f) => a + f.drawnAmountOMR, 0));
  const totUndrawn = roundOMR(totLimit - totDrawn);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Financing Facilities, Debt Maturity & Covenant Compliance
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Murabaha, Term Loans, Sukuk tranches, DSCR, LTV, LTC, and undrawn facility headroom
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Total Committed Facilities</div>
          <div className="mt-1 text-lg font-semibold"><MaskedValue formatted={formatMoney(totLimit, currency, false, true)} masked={masked} /></div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Drawn Debt Principal</div>
          <div className="mt-1 text-lg font-semibold"><MaskedValue formatted={formatMoney(totDrawn, currency, false, true)} masked={masked} /></div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Undrawn Available Headroom</div>
          <div className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400"><MaskedValue formatted={formatMoney(totUndrawn, currency, false, true)} masked={masked} /></div>
        </div>
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-2.5 px-3 font-medium">Lender & Facility</th>
                <th className="py-2.5 px-3 font-medium text-right">Limit</th>
                <th className="py-2.5 px-3 font-medium text-right">Drawn</th>
                <th className="py-2.5 px-3 font-medium text-right">Rate</th>
                <th className="py-2.5 px-3 font-medium text-right">Maturity</th>
                <th className="py-2.5 px-3 font-medium text-right">DSCR (Min)</th>
                <th className="py-2.5 px-3 font-medium text-right">LTV % (Max)</th>
                <th className="py-2.5 px-3 font-medium text-right">LTC % (Max)</th>
                <th className="py-2.5 px-3 font-medium">Covenant Status</th>
              </tr>
            </thead>
            <tbody>
              {dataset.facilities.map((f) => {
                const dscr = safeDiv(f.ebitdaAnnualizedOMR, f.annualDebtServiceOMR) ?? 0;
                const ltv = (safeDiv(f.drawnAmountOMR, f.collateralValueOMR) ?? 0) * 100;
                const ltc = (safeDiv(f.drawnAmountOMR, f.totalProjectCostOMR) ?? 0) * 100;
                const compliant = dscr >= f.minDscrCovenant && ltv <= f.maxLtvCovenantPct && ltc <= f.maxLtcCovenantPct;
                return (
                  <tr key={f.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                    <td className="py-2.5 px-3">
                      <div className="font-medium" style={{ color: 'var(--re-text)' }}>{f.lenderName}</div>
                      <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>{f.facilityType}</div>
                    </td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(f.facilityLimitOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(f.drawnAmountOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right font-mono-num">{f.interestRatePct.toFixed(2)}%</td>
                    <td className="py-2.5 px-3 text-right font-mono-num" style={{ color: 'var(--re-text-muted)' }}>{f.maturityDate}</td>
                    <td className="py-2.5 px-3 text-right font-mono-num">{formatRatio(dscr, masked)} ({f.minDscrCovenant.toFixed(2)}x)</td>
                    <td className="py-2.5 px-3 text-right font-mono-num">{ltv.toFixed(1)}% ({f.maxLtvCovenantPct}%)</td>
                    <td className="py-2.5 px-3 text-right font-mono-num">{ltc.toFixed(1)}% ({f.maxLtcCovenantPct}%)</td>
                    <td className={`py-2.5 px-3 font-medium ${compliant ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                      {compliant ? 'Compliant' : 'Breach'}
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

export const FeasibilityScenarioView: React.FC<{
  projectKpis: ProjectKpiSummary[];
  currency: CurrencyCode;
  masked: boolean;
}> = ({ projectKpis, currency, masked }) => {
  const [selectedPrjId, setSelectedPrjId] = useState(projectKpis[0]?.project.id ?? 'prj-marina');
  const [params, setParams] = useState<ScenarioParameters>({
    name: 'Custom Stress Scenario',
    sellingPriceDeltaPct: 0,
    salesVelocityDeltaPct: 0,
    collectionDelayMonths: 0,
    cancellationRatePct: 0,
    constructionCostDeltaPct: 0,
    projectDelayMonths: 0,
    interestRateDeltaBps: 0,
    landAndClaimsDeltaOMR: 0,
    phasingShiftMonths: 0,
    fundingCapOMR: null,
  });

  const prj = projectKpis.find((p) => p.project.id === selectedPrjId) ?? projectKpis[0];

  const baseResult = useMemo(
    () =>
      runScenarioSimulation(prj.netDevelopmentValueOMR, prj.forecastFinalCostEAC, prj.forecastFinalCostEAC * 0.42, 6.1, 30, {
        name: 'Base Case',
        sellingPriceDeltaPct: 0,
        salesVelocityDeltaPct: 0,
        collectionDelayMonths: 0,
        cancellationRatePct: 0,
        constructionCostDeltaPct: 0,
        projectDelayMonths: 0,
        interestRateDeltaBps: 0,
        landAndClaimsDeltaOMR: 0,
        phasingShiftMonths: 0,
        fundingCapOMR: null,
      }),
    [prj]
  );

  const scenarioResult = useMemo(
    () =>
      runScenarioSimulation(prj.netDevelopmentValueOMR, prj.forecastFinalCostEAC, prj.forecastFinalCostEAC * 0.42, 6.1, 30, params),
    [prj, params]
  );

  const applyPreset = (preset: 'base' | 'optimistic' | 'pessimistic') => {
    if (preset === 'base') {
      setParams({
        name: 'Base Case',
        sellingPriceDeltaPct: 0,
        salesVelocityDeltaPct: 0,
        collectionDelayMonths: 0,
        cancellationRatePct: 0,
        constructionCostDeltaPct: 0,
        projectDelayMonths: 0,
        interestRateDeltaBps: 0,
        landAndClaimsDeltaOMR: 0,
        phasingShiftMonths: 0,
        fundingCapOMR: null,
      });
    } else if (preset === 'optimistic') {
      setParams({
        name: 'Optimistic Upside',
        sellingPriceDeltaPct: 8,
        salesVelocityDeltaPct: 20,
        collectionDelayMonths: 0,
        cancellationRatePct: 0,
        constructionCostDeltaPct: -4,
        projectDelayMonths: 0,
        interestRateDeltaBps: -50,
        landAndClaimsDeltaOMR: 0,
        phasingShiftMonths: 0,
        fundingCapOMR: null,
      });
    } else {
      setParams({
        name: 'Pessimistic Downside',
        sellingPriceDeltaPct: -10,
        salesVelocityDeltaPct: -25,
        collectionDelayMonths: 4,
        cancellationRatePct: 6,
        constructionCostDeltaPct: 12,
        projectDelayMonths: 6,
        interestRateDeltaBps: 150,
        landAndClaimsDeltaOMR: 1_200_000,
        phasingShiftMonths: 2,
        fundingCapOMR: 18_000_000,
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Feasibility, IRR / NPV & Dynamic Scenario Simulator
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Simulate price, velocity, collection delays, cancellations, capex, delays, and interest rates without altering locked actuals
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Select project for feasibility scenario"
            value={selectedPrjId}
            onChange={(e) => setSelectedPrjId(e.target.value)}
            className="px-3 py-1.5 rounded-lg border text-xs"
            style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
          >
            {projectKpis.map((p) => (
              <option key={p.project.id} value={p.project.id}>
                {p.project.code} — {p.project.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => applyPreset('base')}
            className="px-3 py-1.5 rounded-lg border text-xs font-medium"
            style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
          >
            Base Case
          </button>
          <button
            type="button"
            onClick={() => applyPreset('optimistic')}
            className="px-3 py-1.5 rounded-lg border text-xs font-medium text-emerald-700 dark:text-emerald-400"
            style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
          >
            Optimistic
          </button>
          <button
            type="button"
            onClick={() => applyPreset('pessimistic')}
            className="px-3 py-1.5 rounded-lg border text-xs font-medium text-rose-700 dark:text-rose-400"
            style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
          >
            Pessimistic
          </button>
        </div>
      </div>

      {/* Comparison KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Project IRR (Base → Sim)</div>
          <div className="mt-1 text-base font-semibold font-mono-num">
            {formatPct(baseResult.projectIrrPct, masked)} → {formatPct(scenarioResult.projectIrrPct, masked)}
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Equity IRR</div>
          <div className="mt-1 text-base font-semibold font-mono-num">
            {formatPct(scenarioResult.equityIrrPct, masked)}
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>NPV @ 10% Hurdle</div>
          <div className="mt-1 text-base font-semibold">
            <MaskedValue formatted={formatMoney(scenarioResult.npvAt10PctOMR, currency, false, true)} masked={masked} />
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Peak Funding Req.</div>
          <div className="mt-1 text-base font-semibold">
            <MaskedValue formatted={formatMoney(scenarioResult.peakFundingOMR, currency, false, true)} masked={masked} />
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Payback Period</div>
          <div className="mt-1 text-base font-semibold font-mono-num">
            {scenarioResult.paybackMonths ? `${scenarioResult.paybackMonths} mos` : 'N/A'}
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Covenant (DSCR {scenarioResult.minDscr?.toFixed(2) ?? 'N/A'}x)</div>
          <div className={`mt-1 text-base font-semibold ${scenarioResult.covenantStatus === 'Compliant' ? 'text-emerald-600' : scenarioResult.covenantStatus === 'Watchlist' ? 'text-amber-600' : 'text-rose-600'}`}>
            {scenarioResult.covenantStatus}
          </div>
        </div>
      </div>

      {/* Sliders + Cash Curve */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="rounded-lg border p-5 space-y-3.5 text-xs" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Sensitivity Levers</h3>

          <label className="block">
            <div className="flex justify-between mb-1">
              <span>Selling Price Adjustment</span>
              <span className="font-mono-num font-semibold">{params.sellingPriceDeltaPct > 0 ? '+' : ''}{params.sellingPriceDeltaPct}%</span>
            </div>
            <input type="range" min={-25} max={25} value={params.sellingPriceDeltaPct} onChange={(e) => setParams({ ...params, sellingPriceDeltaPct: Number(e.target.value) })} className="w-full" />
          </label>

          <label className="block">
            <div className="flex justify-between mb-1">
              <span>Sales Velocity Change</span>
              <span className="font-mono-num font-semibold">{params.salesVelocityDeltaPct > 0 ? '+' : ''}{params.salesVelocityDeltaPct}%</span>
            </div>
            <input type="range" min={-40} max={40} value={params.salesVelocityDeltaPct} onChange={(e) => setParams({ ...params, salesVelocityDeltaPct: Number(e.target.value) })} className="w-full" />
          </label>

          <label className="block">
            <div className="flex justify-between mb-1">
              <span>Collection Delay</span>
              <span className="font-mono-num font-semibold">{params.collectionDelayMonths} months</span>
            </div>
            <input type="range" min={0} max={12} value={params.collectionDelayMonths} onChange={(e) => setParams({ ...params, collectionDelayMonths: Number(e.target.value) })} className="w-full" />
          </label>

          <label className="block">
            <div className="flex justify-between mb-1">
              <span>Unit Cancellation Rate</span>
              <span className="font-mono-num font-semibold">{params.cancellationRatePct}%</span>
            </div>
            <input type="range" min={0} max={20} value={params.cancellationRatePct} onChange={(e) => setParams({ ...params, cancellationRatePct: Number(e.target.value) })} className="w-full" />
          </label>

          <label className="block">
            <div className="flex justify-between mb-1">
              <span>Construction Cost Variance</span>
              <span className="font-mono-num font-semibold">{params.constructionCostDeltaPct > 0 ? '+' : ''}{params.constructionCostDeltaPct}%</span>
            </div>
            <input type="range" min={-15} max={30} value={params.constructionCostDeltaPct} onChange={(e) => setParams({ ...params, constructionCostDeltaPct: Number(e.target.value) })} className="w-full" />
          </label>

          <label className="block">
            <div className="flex justify-between mb-1">
              <span>Project Schedule Delay</span>
              <span className="font-mono-num font-semibold">{params.projectDelayMonths} months</span>
            </div>
            <input type="range" min={0} max={18} value={params.projectDelayMonths} onChange={(e) => setParams({ ...params, projectDelayMonths: Number(e.target.value) })} className="w-full" />
          </label>

          <label className="block">
            <div className="flex justify-between mb-1">
              <span>Interest Rate Shock</span>
              <span className="font-mono-num font-semibold">{params.interestRateDeltaBps > 0 ? '+' : ''}{params.interestRateDeltaBps} bps</span>
            </div>
            <input type="range" min={-200} max={400} step={25} value={params.interestRateDeltaBps} onChange={(e) => setParams({ ...params, interestRateDeltaBps: Number(e.target.value) })} className="w-full" />
          </label>
        </div>

        <div className="xl:col-span-2 rounded-lg border p-5" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold mb-3" style={{ color: 'var(--re-text)' }}>
            Simulated Monthly Cash Flow & Cumulative Net Cash Curve
          </h3>
          <TrendLineChart
            series={scenarioResult.monthlyCashFlows.slice(0, 36).map((m) => ({
              label: m.label,
              primary: m.inflowOMR,
              secondary: m.outflowOMR,
              tertiary: Math.max(0, m.cumulativeOMR),
            }))}
            primaryName="Monthly Inflow"
            secondaryName="Capex & Finance Outflow"
            tertiaryName="Positive Cumulative Cash"
            masked={masked}
          />
        </div>
      </div>
    </div>
  );
};

export const RiskComplianceView: React.FC<{
  dataset: MisDataset;
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, currency, masked }) => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Enterprise Risk Register & Compliance Matrix
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Tracks financial, construction, commercial, liquidity, contractual, and regulatory exposures
        </p>
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-2.5 px-3 font-medium">Category</th>
                <th className="py-2.5 px-3 font-medium">Risk Description</th>
                <th className="py-2.5 px-3 font-medium text-right">Score (L×I)</th>
                <th className="py-2.5 px-3 font-medium text-right">Exposure</th>
                <th className="py-2.5 px-3 font-medium">Owner</th>
                <th className="py-2.5 px-3 font-medium">Due Date</th>
                <th className="py-2.5 px-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {dataset.risks.map((r) => {
                const score = r.likelihood * r.impact;
                return (
                  <tr key={r.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                    <td className="py-2.5 px-3 font-medium" style={{ color: 'var(--re-text)' }}>{r.category}</td>
                    <td className="py-2.5 px-3" style={{ color: 'var(--re-text-muted)' }}>{r.title}</td>
                    <td className={`py-2.5 px-3 text-right font-mono-num font-semibold ${score >= 15 ? 'text-rose-600 dark:text-rose-400' : score >= 10 ? 'text-amber-600 dark:text-amber-400' : ''}`}>
                      {score} ({r.likelihood}×{r.impact})
                    </td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(r.financialExposureOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3" style={{ color: 'var(--re-text-muted)' }}>{r.mitigationOwner}</td>
                    <td className="py-2.5 px-3 font-mono-num" style={{ color: 'var(--re-text-muted)' }}>{r.dueDate}</td>
                    <td className={`py-2.5 px-3 font-medium ${r.status === 'Escalated' ? 'text-rose-600 dark:text-rose-400' : ''}`}>{r.status}</td>
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

export const HandoverWarrantyView: React.FC<{
  dataset: MisDataset;
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, currency, masked }) => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Unit Handover, Completion Certificates & Defects Liability (DLP)
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Completion certificates, snagging queues, warranty claims, and DLP retention obligations
        </p>
      </div>
      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-2.5 px-3 font-medium">Project</th>
                <th className="py-2.5 px-3 font-medium">BCC Status</th>
                <th className="py-2.5 px-3 font-medium text-right">Handed Over</th>
                <th className="py-2.5 px-3 font-medium text-right">Snagging</th>
                <th className="py-2.5 px-3 font-medium text-right">Open Claims</th>
                <th className="py-2.5 px-3 font-medium text-right">DLP Reserve</th>
                <th className="py-2.5 px-3 font-medium text-right">Outstanding Oblig.</th>
              </tr>
            </thead>
            <tbody>
              {dataset.handovers.map((h) => {
                const prj = dataset.projects.find((p) => p.id === h.projectId);
                return (
                  <tr key={h.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                    <td className="py-2.5 px-3 font-medium" style={{ color: 'var(--re-text)' }}>{prj?.name ?? h.projectId}</td>
                    <td className="py-2.5 px-3" style={{ color: 'var(--re-text-muted)' }}>{h.completionCertificateStatus}</td>
                    <td className="py-2.5 px-3 text-right font-mono-num">{h.unitsHandedOver} / {h.totalUnitsForHandover}</td>
                    <td className="py-2.5 px-3 text-right font-mono-num">{h.unitsInSnagging}</td>
                    <td className="py-2.5 px-3 text-right font-mono-num">{h.openWarrantyClaims} ({h.resolvedWarrantyClaims} closed)</td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(h.dlpReserveOMR, currency, false)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(h.outstandingObligationsOMR, currency, false)} masked={masked} /></td>
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

export const RentalPropertiesView: React.FC<{
  dataset: MisDataset;
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, currency, masked }) => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Investment & Rental Properties (IAS 40)
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Occupancy, Net Operating Income (NOI), gross/net rental yield, lease expiries, and tenant arrears
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {dataset.rentals.map((r) => {
          const occPct = (r.occupiedSqm / r.leasableSqm) * 100;
          const noi = roundOMR(r.annualPassingRentOMR - r.operatingExpensesOMR);
          const yieldPct = (noi / r.propertyFairValueOMR) * 100;
          return (
            <div key={r.id} className="rounded-lg border p-5 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
              <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>{r.propertyName}</h3>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div style={{ color: 'var(--re-text-muted)' }}>Occupancy</div>
                  <div className="font-semibold font-mono-num mt-0.5">{occPct.toFixed(1)}% ({r.occupiedSqm.toLocaleString()} / {r.leasableSqm.toLocaleString()} sqm)</div>
                </div>
                <div>
                  <div style={{ color: 'var(--re-text-muted)' }}>Net Rental Yield</div>
                  <div className="font-semibold font-mono-num mt-0.5 text-emerald-600 dark:text-emerald-400">{yieldPct.toFixed(2)}%</div>
                </div>
                <div>
                  <div style={{ color: 'var(--re-text-muted)' }}>Annual NOI</div>
                  <div className="font-semibold mt-0.5"><MaskedValue formatted={formatMoney(noi, currency, false)} masked={masked} /></div>
                </div>
                <div>
                  <div style={{ color: 'var(--re-text-muted)' }}>Fair Value (IAS 40)</div>
                  <div className="font-semibold mt-0.5"><MaskedValue formatted={formatMoney(r.propertyFairValueOMR, currency, false, true)} masked={masked} /></div>
                </div>
                <div>
                  <div style={{ color: 'var(--re-text-muted)' }}>Tenant Arrears</div>
                  <div className="font-semibold text-rose-600 dark:text-rose-400 mt-0.5"><MaskedValue formatted={formatMoney(r.tenantArrearsOMR, currency, false)} masked={masked} /></div>
                </div>
                <div>
                  <div style={{ color: 'var(--re-text-muted)' }}>12-Mo Lease Expiry</div>
                  <div className="font-semibold font-mono-num mt-0.5">{r.expiringWithin12MonthsPct.toFixed(1)}%</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
