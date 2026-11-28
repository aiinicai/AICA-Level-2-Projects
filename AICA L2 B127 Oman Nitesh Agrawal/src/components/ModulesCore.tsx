import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, CheckCircle2 } from 'lucide-react';
import {
  computeFinancialStatements,
  formatMoney,
  formatPct,
  roundOMR,
  type ExecutiveCommentaryBundle,
  type FinancialStatements,
  type ProjectKpiSummary,
  type ReconciliationResult,
} from '../engine/kpiEngine';
import type { CurrencyCode, MisDataset, ModuleId, ReportingBasis, TraceableKpi } from '../types/mis';
import { MaskedValue, TraceableKpiCard } from './MaskedValue';
import { TrendLineChart, WaterfallChart } from './Charts';

interface CoreViewProps {
  dataset: MisDataset;
  statements: FinancialStatements;
  projectKpis: ProjectKpiSummary[];
  traceableKpis: TraceableKpi[];
  reconciliation: ReconciliationResult;
  commentary: ExecutiveCommentaryBundle;
  selectedPeriod: string;
  basis: ReportingBasis;
  currency: CurrencyCode;
  companyFilterId: string | 'CONSOLIDATED';
  projectFilterId: string | 'ALL';
  masked: boolean;
  isArabic: boolean;
  onNavigate: (mod: ModuleId) => void;
  onSelectProject: (projectId: string) => void;
}

export const ExecutiveDashboardView: React.FC<CoreViewProps> = ({
  dataset,
  statements,
  projectKpis,
  traceableKpis,
  reconciliation,
  commentary,
  selectedPeriod,
  currency,
  companyFilterId,
  projectFilterId,
  masked,
  isArabic,
  onNavigate,
  onSelectProject,
}) => {
  // Build 24-month trend series from verified TB data
  const trendSeries = dataset.periods.map((p) => {
    const st = computeFinancialStatements(
      dataset.trialBalance,
      dataset.periods,
      p,
      'Monthly',
      companyFilterId,
      projectFilterId,
      dataset.policies,
      dataset.adjustments
    );
    return {
      label: p.slice(2),
      primary: st.revenue,
      secondary: st.netProfit,
      tertiary: st.cashUnrestricted,
    };
  });

  const waterfallSteps = [
    { label: 'Revenue', amount: statements.revenue, type: 'total' as const },
    { label: 'COGS', amount: -statements.cogs, type: 'minus' as const },
    { label: 'Gross Profit', amount: statements.grossProfit, type: 'total' as const },
    { label: 'OpEx', amount: -statements.opex, type: 'minus' as const },
    { label: 'EBITDA', amount: statements.ebitda, type: 'total' as const },
    { label: 'Fin & Tax', amount: -(statements.financeCostNet + statements.taxExpense), type: 'minus' as const },
    { label: 'Net Profit', amount: statements.netProfit, type: 'total' as const },
  ];

  return (
    <div className="space-y-6">
      {/* Executive Summary Banner */}
      <div
        className="rounded-lg border p-4 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
        style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
      >
        <div className="space-y-1">
          <div className="text-xs font-medium" style={{ color: 'var(--re-text-muted)' }}>
            {isArabic
              ? `الفترة ${selectedPeriod} · ${dataset.companies.length} شركات · ${dataset.projects.length} مشاريع · ${dataset.units.length.toLocaleString()} وحدة`
              : `Period ${selectedPeriod} · ${dataset.companies.length} Legal Entities · ${dataset.projects.length} Active Developments · ${dataset.units.length.toLocaleString()} Property Units`}
          </div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            {isArabic
              ? `ملخص الأداء (${selectedPeriod}): الإيرادات ${formatMoney(statements.revenue, currency, masked, true)} · صافي الربح ${formatMoney(statements.netProfit, currency, masked, true)}`
              : commentary.headline}
          </h2>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {reconciliation.canPublish ? (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              TB Reconciled (0.000 OMR)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-700 dark:text-rose-400">
              <AlertTriangle className="w-4 h-4" />
              Reconciliation Exception
            </span>
          )}
          <button
            type="button"
            onClick={() => onNavigate('reports-exports')}
            className="px-3.5 py-2 rounded-lg text-xs font-medium transition-opacity hover:opacity-90 whitespace-nowrap shrink-0"
            style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
          >
            Generate Board Pack
          </button>
        </div>
      </div>

      {/* 8 Traceable KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {traceableKpis.map((kpi) => (
          <TraceableKpiCard key={kpi.id} kpi={kpi} masked={masked} isArabic={isArabic} />
        ))}
      </div>

      {/* Charts Row: P&L Waterfall + 24-Month Financial Trajectory */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section
          className="rounded-lg border p-5"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
                Income Statement Waterfall Bridge
              </h3>
              <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
                IFRS 15 Recognized Revenue to Net Profit ({currency})
              </p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('financial-mis')}
              className="text-xs font-medium inline-flex items-center gap-1 hover:underline"
              style={{ color: 'var(--re-accent)' }}
            >
              Open Financial MIS <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <WaterfallChart steps={waterfallSteps} currency={currency} masked={masked} />
        </section>

        <section
          className="rounded-lg border p-5"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
                24-Month Revenue, Net Profit & Liquidity Trend
              </h3>
              <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
                Monthly rolling trajectory ({dataset.periods[0]} to {selectedPeriod})
              </p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('cashflow-treasury')}
              className="text-xs font-medium inline-flex items-center gap-1 hover:underline"
              style={{ color: 'var(--re-accent)' }}
            >
              Treasury & Forecast <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <TrendLineChart
            series={trendSeries}
            primaryName="Recognized Revenue"
            secondaryName="Net Profit"
            tertiaryName="Unrestricted Cash"
            masked={masked}
          />
        </section>
      </div>

      {/* Project Portfolio Health Matrix + Management Alerts */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <section
          className="xl:col-span-2 rounded-lg border overflow-hidden"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
        >
          <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--re-border)' }}>
            <div>
              <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
                Project Portfolio Health & Earned Value Summary
              </h3>
              <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
                Click any development to filter or drill into project cost control
              </p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('project-performance')}
              className="text-xs font-medium hover:underline"
              style={{ color: 'var(--re-accent)' }}
            >
              Full Matrix
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                  <th className="py-2.5 px-3 font-medium">Project</th>
                  <th className="py-2.5 px-3 font-medium text-right">GDV</th>
                  <th className="py-2.5 px-3 font-medium text-right">Contracted</th>
                  <th className="py-2.5 px-3 font-medium text-right">Collected</th>
                  <th className="py-2.5 px-3 font-medium text-right">EAC Cost</th>
                  <th className="py-2.5 px-3 font-medium text-right">Phys %</th>
                  <th className="py-2.5 px-3 font-medium text-right">SPI / CPI</th>
                </tr>
              </thead>
              <tbody>
                {projectKpis.map((p) => (
                  <tr
                    key={p.project.id}
                    className="border-b last:border-b-0 hover:opacity-90 transition-opacity"
                    style={{ borderColor: 'var(--re-border)' }}
                  >
                    <td className="py-2.5 px-3">
                      <button
                        type="button"
                        onClick={() => {
                          onSelectProject(p.project.id);
                          onNavigate('project-performance');
                        }}
                        className="text-left font-medium hover:underline"
                        style={{ color: 'var(--re-text)' }}
                      >
                        {p.project.code} — {p.project.name}
                      </button>
                      <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>
                        {p.project.category} · {p.soldUnits}/{p.project.totalUnits} sold
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <MaskedValue formatted={formatMoney(p.gdvOMR, currency, false, true)} masked={masked} />
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <MaskedValue formatted={formatMoney(p.contractedSalesOMR, currency, false, true)} masked={masked} />
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <MaskedValue formatted={formatMoney(p.collectedOMR, currency, false, true)} masked={masked} />
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <MaskedValue formatted={formatMoney(p.forecastFinalCostEAC, currency, false, true)} masked={masked} />
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono-num">
                      {formatPct(p.physicalProgressPct, masked)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono-num">
                      <span className={(p.spi ?? 1) < 0.95 ? 'text-amber-600 dark:text-amber-400 font-semibold' : ''}>
                        {p.spi !== null ? p.spi.toFixed(2) : 'N/A'}
                      </span>
                      {' / '}
                      <span className={(p.cpi ?? 1) < 0.95 ? 'text-rose-600 dark:text-rose-400 font-semibold' : ''}>
                        {p.cpi !== null ? p.cpi.toFixed(2) : 'N/A'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Critical Alerts & Automated CFO Highlights */}
        <section
          className="rounded-lg border p-4 space-y-3"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
        >
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
              Priority Alerts & CFO Commentary
            </h3>
            <button
              type="button"
              onClick={() => onNavigate('ai-analyst')}
              className="text-xs font-medium hover:underline"
              style={{ color: 'var(--re-accent)' }}
            >
              AI Analyst
            </button>
          </div>
          <div className="space-y-2.5 text-xs" style={{ color: 'var(--re-text-muted)' }}>
            {commentary.costAndScheduleAlerts.map((alert, i) => (
              <div key={i} className="pb-2 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span className="font-semibold text-amber-700 dark:text-amber-400">Schedule & Cost: </span>
                {alert}
              </div>
            ))}
            {commentary.cashFlowWarnings.map((w, i) => (
              <div key={i} className="pb-2 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span className="font-semibold text-sky-700 dark:text-sky-400">Treasury: </span>
                {w}
              </div>
            ))}
            <div>
              <span className="font-semibold" style={{ color: 'var(--re-text)' }}>Next Action: </span>
              {commentary.actionPlan[0]?.action}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export const FinancialMisView: React.FC<{
  dataset: MisDataset;
  statements: FinancialStatements;
  reconciliation: ReconciliationResult;
  selectedPeriod: string;
  basis: ReportingBasis;
  currency: CurrencyCode;
  companyFilterId: string | 'CONSOLIDATED';
  masked: boolean;
}> = ({ dataset, statements, reconciliation, selectedPeriod, basis, currency, companyFilterId, masked }) => {
  const [tab, setTab] = useState<'pnl' | 'bs' | 'cf' | 'ifrs'>('pnl');

  const pnlRows = [
    { label: 'Recognized Development & Rental Revenue (IFRS 15 / IAS 40)', value: statements.revenue, bold: true },
    { label: 'Cost of Development Sales', value: -statements.cogs, bold: false },
    { label: 'Gross Profit', value: statements.grossProfit, bold: true },
    { label: 'Sales, Marketing & General Admin Expenses', value: -statements.opex, bold: false },
    { label: 'EBITDA', value: statements.ebitda, bold: true },
    { label: 'Gross Finance Cost (Before IAS 23)', value: -(statements.financeCostNet + statements.borrowingCostCapitalized), bold: false },
    { label: 'Less: Borrowing Costs Capitalized to WIP (IAS 23)', value: statements.borrowingCostCapitalized, bold: false },
    { label: 'Oman Corporate Income Tax (15%)', value: -statements.taxExpense, bold: false },
    { label: 'Net Profit After Tax', value: statements.netProfit, bold: true },
  ];

  const bsRows = [
    { section: 'Assets', label: 'Unrestricted Corporate Cash & Bank', value: statements.cashUnrestricted },
    { section: 'Assets', label: 'Restricted Project Escrow Accounts', value: statements.cashEscrowRestricted },
    { section: 'Assets', label: 'Trade Receivables (Gross)', value: statements.receivablesGross },
    { section: 'Assets', label: 'Less: Expected Credit Loss Allowance (IFRS 9)', value: -statements.eclAllowanceIFRS9 },
    { section: 'Assets', label: 'IFRS 15 Contract Assets (Unbilled PoC)', value: statements.contractAssetsIFRS15 },
    { section: 'Assets', label: 'Development Inventory & WIP (IAS 2)', value: statements.inventoryWipIAS2 },
    { section: 'Assets', label: 'Investment Properties (IAS 40)', value: statements.investmentPropertyIAS40 },
    { section: 'Assets', label: 'Property, Plant & Equipment', value: statements.fixedAssets },
    { section: 'Total', label: 'Total Assets', value: statements.totalAssets },
    { section: 'Liabilities', label: 'Trade & Contractor Payables', value: statements.payables },
    { section: 'Liabilities', label: 'Customer Advances / Contract Liabilities (IFRS 15)', value: statements.customerAdvancesIFRS15 },
    { section: 'Liabilities', label: 'Contractor Retention Payable', value: statements.retentionPayable },
    { section: 'Liabilities', label: 'Development Debt & Murabaha Facilities', value: statements.debtTotal },
    { section: 'Total', label: 'Total Liabilities', value: statements.totalLiabilities },
    { section: 'Equity', label: 'Share Capital & Retained Earnings (Total Equity)', value: statements.equityTotal },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Financial MIS Statements & IFRS Controls
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Period {selectedPeriod} · Basis: {basis} · {companyFilterId === 'CONSOLIDATED' ? `Consolidated (Eliminated IC: ${formatMoney(statements.intercompanyEliminatedOMR, currency, masked)})` : 'Single Entity'}
          </p>
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg border" style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)' }}>
          {(['pnl', 'bs', 'cf', 'ifrs'] as const).map((tKey) => (
            <button
              key={tKey}
              type="button"
              onClick={() => setTab(tKey)}
              className="px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap"
              style={
                tab === tKey
                  ? { backgroundColor: 'var(--re-surface)', color: 'var(--re-text)' }
                  : { color: 'var(--re-text-muted)' }
              }
            >
              {tKey === 'pnl' ? 'Income Statement' : tKey === 'bs' ? 'Balance Sheet' : tKey === 'cf' ? 'Cash Flow & WC' : 'IFRS & Oman Tax'}
            </button>
          ))}
        </div>
      </div>

      {tab === 'pnl' && (
        <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-3 px-4 font-medium">Statement of Profit or Loss Line Item</th>
                <th className="py-3 px-4 font-medium text-right">Amount ({currency})</th>
                <th className="py-3 px-4 font-medium text-right">% of Revenue</th>
              </tr>
            </thead>
            <tbody>
              {pnlRows.map((row) => (
                <tr key={row.label} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                  <td className={`py-2.5 px-4 ${row.bold ? 'font-semibold' : ''}`} style={{ color: 'var(--re-text)' }}>
                    {row.label}
                  </td>
                  <td className={`py-2.5 px-4 text-right ${row.bold ? 'font-semibold' : ''}`}>
                    <MaskedValue formatted={formatMoney(row.value, currency, false)} masked={masked} />
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono-num text-xs" style={{ color: 'var(--re-text-muted)' }}>
                    {statements.revenue > 0 ? formatPct((row.value / statements.revenue) * 100, masked) : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'bs' && (
        <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-3 px-4 font-medium">Section</th>
                <th className="py-3 px-4 font-medium">Statement of Financial Position</th>
                <th className="py-3 px-4 font-medium text-right">Closing Balance ({currency})</th>
              </tr>
            </thead>
            <tbody>
              {bsRows.map((row) => (
                <tr key={row.label} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                  <td className="py-2.5 px-4 text-xs" style={{ color: 'var(--re-text-muted)' }}>{row.section}</td>
                  <td className={`py-2.5 px-4 ${row.section === 'Total' || row.section === 'Equity' ? 'font-semibold' : ''}`} style={{ color: 'var(--re-text)' }}>
                    {row.label}
                  </td>
                  <td className={`py-2.5 px-4 text-right ${row.section === 'Total' || row.section === 'Equity' ? 'font-semibold' : ''}`}>
                    <MaskedValue formatted={formatMoney(row.value, currency, false)} masked={masked} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'cf' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border p-5 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>IAS 7 Statement of Cash Flows Summary</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span style={{ color: 'var(--re-text-muted)' }}>Operating Cash Flow</span>
                <MaskedValue formatted={formatMoney(statements.operatingCashFlow, currency, false)} masked={masked} />
              </div>
              <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span style={{ color: 'var(--re-text-muted)' }}>Investing Cash Flow</span>
                <MaskedValue formatted={formatMoney(statements.investingCashFlow, currency, false)} masked={masked} />
              </div>
              <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span style={{ color: 'var(--re-text-muted)' }}>Financing Cash Flow</span>
                <MaskedValue formatted={formatMoney(statements.financingCashFlow, currency, false)} masked={masked} />
              </div>
              <div className="flex justify-between py-1.5 font-semibold" style={{ color: 'var(--re-text)' }}>
                <span>Net Period Cash Movement</span>
                <MaskedValue formatted={formatMoney(statements.netCashFlow, currency, false)} masked={masked} />
              </div>
            </div>
          </div>
          <div className="rounded-lg border p-5 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Working Capital & Liquidity Position</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span style={{ color: 'var(--re-text-muted)' }}>Net Working Capital</span>
                <MaskedValue formatted={formatMoney(statements.workingCapital, currency, false)} masked={masked} />
              </div>
              <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span style={{ color: 'var(--re-text-muted)' }}>Unrestricted Cash</span>
                <MaskedValue formatted={formatMoney(statements.cashUnrestricted, currency, false)} masked={masked} />
              </div>
              <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--re-border)' }}>
                <span style={{ color: 'var(--re-text-muted)' }}>Restricted Escrow Cash</span>
                <MaskedValue formatted={formatMoney(statements.cashEscrowRestricted, currency, false)} masked={masked} />
              </div>
              <div className="flex justify-between py-1.5 font-semibold" style={{ color: 'var(--re-text)' }}>
                <span>Net Debt (Excl. Escrow)</span>
                <MaskedValue formatted={formatMoney(statements.netDebt, currency, false)} masked={masked} />
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'ifrs' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border p-5 space-y-2.5 text-xs" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text-muted)' }}>
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Active IFRS Policies</h3>
            <div><strong style={{ color: 'var(--re-text)' }}>IFRS 15 Revenue Recognition:</strong> Over-Time PoC applied only where enforceable right to payment & {dataset.policies.ifrs15OverTimeThresholdPct}% progress threshold met; otherwise Point-in-Time Handover.</div>
            <div><strong style={{ color: 'var(--re-text)' }}>IFRS 9 ECL Provisioning:</strong> Stage 1 ({dataset.policies.ifrs9EclStage1Pct}%), Stage 2 ({dataset.policies.ifrs9EclStage2Pct}%), Stage 3 ({dataset.policies.ifrs9EclStage3Pct}%). Current ECL: <MaskedValue formatted={formatMoney(statements.eclAllowanceIFRS9, currency, false)} masked={masked} />.</div>
            <div><strong style={{ color: 'var(--re-text)' }}>IAS 2 Development Inventory NRV:</strong> Tested against net realizable value with {dataset.policies.ias2NrvHaircutThresholdPct}% stress buffer.</div>
            <div><strong style={{ color: 'var(--re-text)' }}>IAS 23 Borrowing Costs:</strong> {dataset.policies.ias23CapitalizeBorrowingCosts ? 'Capitalized during active construction' : 'Expensed as incurred'}.</div>
            <div><strong style={{ color: 'var(--re-text)' }}>IAS 40 Investment Property:</strong> {dataset.policies.ias40FairValueModel ? 'Fair Value Model' : 'Cost Model'}.</div>
          </div>
          <div className="rounded-lg border p-5 space-y-2.5 text-xs" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text-muted)' }}>
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Oman / GCC Statutory & Reconciliation Controls</h3>
            <div><strong style={{ color: 'var(--re-text)' }}>Oman VAT Rate:</strong> {dataset.policies.omanVatRatePct}% (Commercial supply standard-rated; Residential first supply / bare land configured per unit type).</div>
            <div><strong style={{ color: 'var(--re-text)' }}>Corporate Income Tax:</strong> {dataset.policies.omanCorporateTaxRatePct}% · <strong style={{ color: 'var(--re-text)' }}>Withholding Tax:</strong> {dataset.policies.omanWithholdingTaxPct}% on cross-border services.</div>
            <div><strong style={{ color: 'var(--re-text)' }}>Materiality Gate:</strong> OMR {dataset.policies.materialityThresholdOMR.toFixed(3)}</div>
            <div><strong style={{ color: 'var(--re-text)' }}>TB Debit/Credit Variance:</strong> OMR {reconciliation.trialBalanceDiff.toFixed(3)} ({reconciliation.canPublish ? 'Cleared for Publication' : 'Blocked'})</div>
          </div>
        </div>
      )}
    </div>
  );
};

export const CashFlowTreasuryView: React.FC<{
  dataset: MisDataset;
  statements: FinancialStatements;
  projectKpis: ProjectKpiSummary[];
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, statements, projectKpis, currency, masked }) => {
  const [horizon, setHorizon] = useState<'13w' | '24m'>('13w');

  const forecastRows = Array.from({ length: horizon === '13w' ? 13 : 24 }, (_, idx) => {
    const label = horizon === '13w' ? `W${idx + 1}` : `M+${idx + 1}`;
    const baseInflow = roundOMR((statements.revenue * (horizon === '13w' ? 0.25 : 1.04)) * (0.9 + 0.18 * Math.sin(idx * 0.7)));
    const baseOutflow = roundOMR((statements.cogs * (horizon === '13w' ? 0.23 : 0.96)) * (0.92 + 0.15 * Math.cos(idx * 0.5)));
    const net = roundOMR(baseInflow - baseOutflow);
    return { label, primary: baseInflow, secondary: baseOutflow, net };
  });

  let runningUnrestricted = statements.cashUnrestricted;
  const runwaySeries = forecastRows.map((r) => {
    runningUnrestricted = roundOMR(runningUnrestricted + r.net * 0.55);
    return { ...r, endingUnrestricted: runningUnrestricted };
  });

  const minForecastCash = Math.min(...runwaySeries.map((r) => r.endingUnrestricted));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Cash Flow & Treasury Management
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Strictly segregates corporate unrestricted liquidity from project escrow accounts
          </p>
        </div>
        <div className="flex items-center gap-1 p-1 rounded-lg border" style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)' }}>
          <button
            type="button"
            onClick={() => setHorizon('13w')}
            className="px-3 py-1.5 rounded-md text-xs font-medium"
            style={horizon === '13w' ? { backgroundColor: 'var(--re-surface)', color: 'var(--re-text)' } : { color: 'var(--re-text-muted)' }}
          >
            13-Week Liquidity
          </button>
          <button
            type="button"
            onClick={() => setHorizon('24m')}
            className="px-3 py-1.5 rounded-md text-xs font-medium"
            style={horizon === '24m' ? { backgroundColor: 'var(--re-surface)', color: 'var(--re-text)' } : { color: 'var(--re-text-muted)' }}
          >
            24-Month Forecast
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Unrestricted Corporate Cash</div>
          <div className="mt-1.5 text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            <MaskedValue formatted={formatMoney(statements.cashUnrestricted, currency, false, true)} masked={masked} />
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Restricted Escrow Balances</div>
          <div className="mt-1.5 text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            <MaskedValue formatted={formatMoney(statements.cashEscrowRestricted, currency, false, true)} masked={masked} />
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Minimum Forecast Unrestricted</div>
          <div className="mt-1.5 text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            <MaskedValue formatted={formatMoney(minForecastCash, currency, false, true)} masked={masked} />
          </div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Funding Gap Risk</div>
          <div className="mt-1.5 text-lg font-semibold text-emerald-600 dark:text-emerald-400">
            {minForecastCash > 0 ? 'None (Surplus)' : formatMoney(Math.abs(minForecastCash), currency, masked, true)}
          </div>
        </div>
      </div>

      <div className="rounded-lg border p-5" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <h3 className="font-display text-sm font-semibold mb-3" style={{ color: 'var(--re-text)' }}>
          {horizon === '13w' ? '13-Week' : '24-Month'} Projected Inflows, Outflows & Unrestricted Cash Runway
        </h3>
        <TrendLineChart
          series={runwaySeries.map((r) => ({ label: r.label, primary: r.primary, secondary: r.secondary, tertiary: r.endingUnrestricted }))}
          primaryName="Projected Collections & Drawdowns"
          secondaryName="Capex, Debt & OpEx Outflows"
          tertiaryName="Ending Unrestricted Cash"
          masked={masked}
        />
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="p-4 border-b" style={{ borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Escrow Accounts by Project</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-2.5 px-3 font-medium">Project</th>
                <th className="py-2.5 px-3 font-medium">Escrow Bank</th>
                <th className="py-2.5 px-3 font-medium">Escrow Account</th>
                <th className="py-2.5 px-3 font-medium text-right">Collected to Date</th>
                <th className="py-2.5 px-3 font-medium text-right">Remaining Commitments</th>
              </tr>
            </thead>
            <tbody>
              {projectKpis.map((p) => (
                <tr key={p.project.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                  <td className="py-2.5 px-3 font-medium" style={{ color: 'var(--re-text)' }}>{p.project.name}</td>
                  <td className="py-2.5 px-3" style={{ color: 'var(--re-text-muted)' }}>{p.project.escrowBank}</td>
                  <td className="py-2.5 px-3 font-mono-num" style={{ color: 'var(--re-text-muted)' }}>{p.project.escrowAccountNo}</td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(p.collectedOMR, currency, false)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(p.committedRemainingOMR, currency, false)} masked={masked} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export const ProjectPerformanceView: React.FC<{
  projectKpis: ProjectKpiSummary[];
  currency: CurrencyCode;
  masked: boolean;
}> = ({ projectKpis, currency, masked }) => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Project Performance & Life-Cycle Profitability
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Actual cost + accruals + uncertified commitments + uncommitted ETC = Forecast Final Cost (zero double-counting)
        </p>
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-3 px-3 font-medium">Project</th>
                <th className="py-3 px-3 font-medium">Rev. Method</th>
                <th className="py-3 px-3 font-medium text-right">Net Dev Value</th>
                <th className="py-3 px-3 font-medium text-right">Actual + Accruals</th>
                <th className="py-3 px-3 font-medium text-right">Committed Rem.</th>
                <th className="py-3 px-3 font-medium text-right">Addl. ETC</th>
                <th className="py-3 px-3 font-medium text-right">Forecast EAC</th>
                <th className="py-3 px-3 font-medium text-right">Forecast Profit</th>
                <th className="py-3 px-3 font-medium text-right">Margin %</th>
                <th className="py-3 px-3 font-medium text-right">Forecast Completion</th>
              </tr>
            </thead>
            <tbody>
              {projectKpis.map((p) => (
                <tr key={p.project.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                  <td className="py-2.5 px-3">
                    <div className="font-medium" style={{ color: 'var(--re-text)' }}>{p.project.code} · {p.project.name}</div>
                    <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>{p.project.location}</div>
                  </td>
                  <td className="py-2.5 px-3" style={{ color: 'var(--re-text-muted)' }}>
                    {p.project.revenueMethod === 'IFRS15_OverTime_PoC' ? 'Over-Time PoC' : 'Point-in-Time'}
                  </td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(p.netDevelopmentValueOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(p.actualCostOMR + p.accrualsOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(p.committedRemainingOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(p.estimatedCostToCompleteOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right font-semibold"><MaskedValue formatted={formatMoney(p.forecastFinalCostEAC, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right font-semibold"><MaskedValue formatted={formatMoney(p.forecastGrossProfitOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right font-mono-num">{formatPct(p.developmentMarginPct, masked)}</td>
                  <td className="py-2.5 px-3 text-right font-mono-num" style={{ color: 'var(--re-text-muted)' }}>{p.project.forecastCompletion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
