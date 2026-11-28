import React, { useMemo, useState } from 'react';
import { Download, Search } from 'lucide-react';
import { formatMoney, formatPct, roundOMR, safeDiv, type ProjectKpiSummary } from '../engine/kpiEngine';
import { exportRowsToCsv } from '../utils/exportEngine';
import type { CurrencyCode, MisDataset, UnitStatus } from '../types/mis';
import { MaskedValue } from './MaskedValue';
import { SCurveChart } from './Charts';

export const SalesInventoryView: React.FC<{
  dataset: MisDataset;
  projectKpis: ProjectKpiSummary[];
  projectFilterId: string | 'ALL';
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, projectKpis, projectFilterId, currency, masked }) => {
  const [statusFilter, setStatusFilter] = useState<'ALL' | UnitStatus>('ALL');
  const [unitSearch, setUnitSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const filteredUnits = useMemo(() => {
    const q = unitSearch.trim().toLowerCase();
    return dataset.units.filter((u) => {
      if (projectFilterId !== 'ALL' && u.projectId !== projectFilterId) return false;
      if (statusFilter !== 'ALL' && u.status !== statusFilter) return false;
      if (q) {
        const hay = `${u.unitCode} ${u.building} ${u.phase} ${u.customerName ?? ''} ${u.unitType}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [dataset.units, projectFilterId, statusFilter, unitSearch]);

  const totalPages = Math.max(1, Math.ceil(filteredUnits.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageRows = filteredUnits.slice((safePage - 1) * pageSize, safePage * pageSize);

  const totGdv = roundOMR(projectKpis.reduce((a, p) => a + p.gdvOMR, 0));
  const totContracted = roundOMR(projectKpis.reduce((a, p) => a + p.contractedSalesOMR, 0));
  const totUnsold = roundOMR(projectKpis.reduce((a, p) => a + p.unsoldInventoryValueOMR, 0));
  const totSold = projectKpis.reduce((a, p) => a + p.soldUnits, 0);
  const totUnits = projectKpis.reduce((a, p) => a + p.project.totalUnits, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Sales & Unit Inventory Matrix ({dataset.units.length.toLocaleString()} Units)
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Contracted sales, absorption velocity, average selling price per sqm, and unsold inventory
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            exportRowsToCsv(
              'RealEstate360_Units_Inventory.csv',
              ['UnitCode', 'ProjectID', 'Phase', 'Building', 'Floor', 'Type', 'AreaSqm', 'ListPriceOMR', 'ContractedOMR', 'CollectedOMR', 'Status'],
              filteredUnits.map((u) => [u.unitCode, u.projectId, u.phase, u.building, u.floor, u.unitType, u.areaSqm, u.listPriceOMR, u.contractedPriceOMR, u.collectedOMR, u.status])
            )
          }
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-medium"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
        >
          <Download className="w-3.5 h-3.5" /> Export Filtered CSV ({filteredUnits.length})
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Total Gross Dev. Value (GDV)</div>
          <div className="mt-1 text-lg font-semibold"><MaskedValue formatted={formatMoney(totGdv, currency, false, true)} masked={masked} /></div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Executed Contracted Sales</div>
          <div className="mt-1 text-lg font-semibold"><MaskedValue formatted={formatMoney(totContracted, currency, false, true)} masked={masked} /></div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Portfolio Absorption</div>
          <div className="mt-1 text-lg font-semibold font-mono-num">{formatPct(safeDiv(totSold * 100, totUnits), masked)} ({totSold}/{totUnits})</div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Unsold Inventory Value</div>
          <div className="mt-1 text-lg font-semibold"><MaskedValue formatted={formatMoney(totUnsold, currency, false, true)} masked={masked} /></div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1 p-1 rounded-lg border" style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)' }}>
          {(['ALL', 'Sold', 'Handed Over', 'Booked', 'Available', 'Cancelled'] as const).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className="px-2.5 py-1.5 rounded-md text-xs font-medium whitespace-nowrap"
              style={statusFilter === st ? { backgroundColor: 'var(--re-surface)', color: 'var(--re-text)' } : { color: 'var(--re-text-muted)' }}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--re-text-muted)' }} />
          <input
            type="text"
            value={unitSearch}
            onChange={(e) => {
              setUnitSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Filter unit code, customer, building..."
            aria-label="Filter units"
            className="w-full pl-8 pr-3 py-1.5 rounded-lg border text-xs"
            style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
          />
        </div>
      </div>

      {/* Unit Registry Table */}
      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-2.5 px-3 font-medium">Unit Code</th>
                <th className="py-2.5 px-3 font-medium">Building / Floor</th>
                <th className="py-2.5 px-3 font-medium">Type</th>
                <th className="py-2.5 px-3 font-medium text-right">Sqm</th>
                <th className="py-2.5 px-3 font-medium text-right">List Price</th>
                <th className="py-2.5 px-3 font-medium text-right">Contracted</th>
                <th className="py-2.5 px-3 font-medium text-right">Collected</th>
                <th className="py-2.5 px-3 font-medium">Status</th>
                <th className="py-2.5 px-3 font-medium">Customer</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-xs" style={{ color: 'var(--re-text-muted)' }}>
                    No property units match the selected filters.
                  </td>
                </tr>
              ) : (
                pageRows.map((u) => (
                  <tr key={u.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                    <td className="py-2 px-3 font-mono-num font-medium" style={{ color: 'var(--re-text)' }}>{u.unitCode}</td>
                    <td className="py-2 px-3" style={{ color: 'var(--re-text-muted)' }}>{u.building} · F{u.floor}</td>
                    <td className="py-2 px-3" style={{ color: 'var(--re-text-muted)' }}>{u.unitType}</td>
                    <td className="py-2 px-3 text-right font-mono-num">{u.areaSqm}</td>
                    <td className="py-2 px-3 text-right"><MaskedValue formatted={formatMoney(u.listPriceOMR, currency, false)} masked={masked} /></td>
                    <td className="py-2 px-3 text-right"><MaskedValue formatted={u.contractedPriceOMR > 0 ? formatMoney(u.contractedPriceOMR, currency, false) : '—'} masked={masked} /></td>
                    <td className="py-2 px-3 text-right"><MaskedValue formatted={u.collectedOMR > 0 ? formatMoney(u.collectedOMR, currency, false) : '—'} masked={masked} /></td>
                    <td className="py-2 px-3 font-medium">
                      <span
                        className={
                          u.status === 'Handed Over' || u.status === 'Sold'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : u.status === 'Available'
                            ? 'text-sky-600 dark:text-sky-400'
                            : u.status === 'Cancelled'
                            ? 'text-rose-600 dark:text-rose-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }
                      >
                        {u.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 truncate max-w-[160px]" style={{ color: 'var(--re-text-muted)' }}>{u.customerName ?? '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="p-3 border-t flex items-center justify-between text-xs" style={{ borderColor: 'var(--re-border)', color: 'var(--re-text-muted)' }}>
          <span>
            Showing {(safePage - 1) * pageSize + 1}–{Math.min(safePage * pageSize, filteredUnits.length)} of {filteredUnits.length.toLocaleString()} units
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={safePage <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-2.5 py-1 rounded border disabled:opacity-40"
              style={{ borderColor: 'var(--re-border)' }}
            >
              Prev
            </button>
            <span className="font-mono-num">
              {safePage} / {totalPages}
            </span>
            <button
              type="button"
              disabled={safePage >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="px-2.5 py-1 rounded border disabled:opacity-40"
              style={{ borderColor: 'var(--re-border)' }}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export const CollectionsView: React.FC<{
  dataset: MisDataset;
  projectKpis: ProjectKpiSummary[];
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, projectKpis, currency, masked }) => {
  const totalInvoiced = roundOMR(projectKpis.reduce((a, p) => a + p.invoicedOMR, 0));
  const totalCollected = roundOMR(projectKpis.reduce((a, p) => a + p.collectedOMR, 0));
  const totalOverdue = roundOMR(projectKpis.reduce((a, p) => a + p.overdueReceivablesOMR, 0));

  const agingBuckets = [
    { label: '0–30 Days', share: 0.42 },
    { label: '31–60 Days', share: 0.28 },
    { label: '61–90 Days', share: 0.17 },
    { label: '90+ Days (Legal / Watch)', share: 0.13 },
  ];

  const topOverdueUnits = dataset.units
    .filter((u) => u.overdueOMR > 0)
    .sort((a, b) => b.overdueOMR - a.overdueOMR)
    .slice(0, 12);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Customer Collections & Receivable Aging
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Installment collection efficiency, overdue aging buckets, and top delinquent customer accounts
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Cumulative Due / Invoiced</div>
          <div className="mt-1 text-lg font-semibold"><MaskedValue formatted={formatMoney(totalInvoiced, currency, false, true)} masked={masked} /></div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Cash Collected (Efficiency {formatPct(safeDiv(totalCollected * 100, totalInvoiced), masked)})</div>
          <div className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400"><MaskedValue formatted={formatMoney(totalCollected, currency, false, true)} masked={masked} /></div>
        </div>
        <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Overdue Installments</div>
          <div className="mt-1 text-lg font-semibold text-rose-600 dark:text-rose-400"><MaskedValue formatted={formatMoney(totalOverdue, currency, false, true)} masked={masked} /></div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-lg border p-4 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Overdue Aging Distribution</h3>
          {agingBuckets.map((b) => (
            <div key={b.label} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span style={{ color: 'var(--re-text-muted)' }}>{b.label}</span>
                <MaskedValue formatted={formatMoney(roundOMR(totalOverdue * b.share), currency, false)} masked={masked} />
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--re-surface-alt)' }}>
                <div className="h-full rounded-full" style={{ width: `${b.share * 100}%`, backgroundColor: 'var(--re-accent)' }} />
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2 rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="p-4 border-b" style={{ borderColor: 'var(--re-border)' }}>
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Top Overdue Customer Accounts</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                  <th className="py-2.5 px-3 font-medium">Unit</th>
                  <th className="py-2.5 px-3 font-medium">Customer</th>
                  <th className="py-2.5 px-3 font-medium text-right">Invoiced</th>
                  <th className="py-2.5 px-3 font-medium text-right">Collected</th>
                  <th className="py-2.5 px-3 font-medium text-right">Overdue</th>
                </tr>
              </thead>
              <tbody>
                {topOverdueUnits.map((u) => (
                  <tr key={u.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                    <td className="py-2 px-3 font-mono-num" style={{ color: 'var(--re-text)' }}>{u.unitCode}</td>
                    <td className="py-2 px-3" style={{ color: 'var(--re-text-muted)' }}>{u.customerName}</td>
                    <td className="py-2 px-3 text-right"><MaskedValue formatted={formatMoney(u.invoicedOMR, currency, false)} masked={masked} /></td>
                    <td className="py-2 px-3 text-right"><MaskedValue formatted={formatMoney(u.collectedOMR, currency, false)} masked={masked} /></td>
                    <td className="py-2 px-3 text-right font-semibold text-rose-600 dark:text-rose-400">
                      <MaskedValue formatted={formatMoney(u.overdueOMR, currency, false)} masked={masked} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export const ConstructionPlanningView: React.FC<{
  dataset: MisDataset;
  projectKpis: ProjectKpiSummary[];
  masked: boolean;
}> = ({ dataset, projectKpis, masked }) => {
  const [activePrjId, setActivePrjId] = useState(dataset.projects[0]?.id ?? 'prj-marina');
  const logs = dataset.constructionLogs.filter((l) => l.projectId === activePrjId);
  const kpi = projectKpis.find((p) => p.project.id === activePrjId);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Construction Progress, S-Curves & Earned Value (SPI / CPI)
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Separates physical site progress, QS-certified progress, and financial cost burn
          </p>
        </div>
        <select
          aria-label="Select project for S-curve"
          value={activePrjId}
          onChange={(e) => setActivePrjId(e.target.value)}
          className="px-3 py-1.5 rounded-lg border text-xs"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
        >
          {dataset.projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.code} — {p.name}
            </option>
          ))}
        </select>
      </div>

      {kpi && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
            <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Physical Progress</div>
            <div className="mt-1 text-lg font-semibold font-mono-num">{formatPct(kpi.physicalProgressPct, masked)}</div>
          </div>
          <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
            <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Certified Progress</div>
            <div className="mt-1 text-lg font-semibold font-mono-num">{formatPct(kpi.certifiedProgressPct, masked)}</div>
          </div>
          <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
            <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Financial Cost %</div>
            <div className="mt-1 text-lg font-semibold font-mono-num">{formatPct(kpi.financialProgressPct, masked)}</div>
          </div>
          <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
            <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Schedule Perf. (SPI)</div>
            <div className={`mt-1 text-lg font-semibold font-mono-num ${(kpi.spi ?? 1) < 0.95 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
              {kpi.spi !== null ? kpi.spi.toFixed(2) : 'N/A'}
            </div>
          </div>
          <div className="rounded-lg border p-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
            <div className="text-xs" style={{ color: 'var(--re-text-muted)' }}>Cost Perf. (CPI)</div>
            <div className={`mt-1 text-lg font-semibold font-mono-num ${(kpi.cpi ?? 1) < 0.95 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
              {kpi.cpi !== null ? kpi.cpi.toFixed(2) : 'N/A'}
            </div>
          </div>
        </div>
      )}

      <div className="rounded-lg border p-5" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <h3 className="font-display text-sm font-semibold mb-3" style={{ color: 'var(--re-text)' }}>
          24-Month Construction S-Curve (Planned vs Physical vs Certified)
        </h3>
        <SCurveChart
          points={logs.map((l) => ({
            period: l.period.slice(2),
            plannedPct: l.plannedPhysicalPct,
            actualPct: l.actualPhysicalPct,
            certifiedPct: l.certifiedProgressPct,
          }))}
        />
      </div>

      {/* Gantt Milestone Timeline */}
      <div className="rounded-lg border p-5 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
          Portfolio Delivery Gantt & Delay Analysis
        </h3>
        <div className="space-y-3">
          {projectKpis.map((p) => {
            const pct = p.physicalProgressPct ?? 0;
            const delayed = p.project.forecastCompletion > p.project.plannedCompletion;
            return (
              <div key={p.project.id} className="grid grid-cols-12 items-center gap-3 text-xs">
                <div className="col-span-12 sm:col-span-4 font-medium truncate" style={{ color: 'var(--re-text)' }}>
                  {p.project.code} — {p.project.name}
                </div>
                <div className="col-span-8 sm:col-span-6">
                  <div className="h-5 rounded border relative overflow-hidden" style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)' }}>
                    <div
                      className="h-full transition-all"
                      style={{
                        width: `${Math.min(100, pct)}%`,
                        backgroundColor: delayed ? '#d97706' : 'var(--re-accent)',
                      }}
                    />
                    <span className="absolute inset-y-0 right-2 flex items-center text-[10px] font-mono-num" style={{ color: 'var(--re-text)' }}>
                      {formatPct(p.physicalProgressPct, masked)}
                    </span>
                  </div>
                </div>
                <div className="col-span-4 sm:col-span-2 text-right font-mono-num text-[11px]" style={{ color: delayed ? '#d97706' : 'var(--re-text-muted)' }}>
                  {p.project.plannedCompletion} → {p.project.forecastCompletion}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export const BudgetCostControlView: React.FC<{
  dataset: MisDataset;
  projectFilterId: string | 'ALL';
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, projectFilterId, currency, masked }) => {
  const [selectedPrj, setSelectedPrj] = useState(projectFilterId === 'ALL' ? dataset.projects[0].id : projectFilterId);
  const lines = dataset.budgets.filter((b) => b.projectId === selectedPrj);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Budget & Cost Control (Original vs Revised vs EAC)
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Category-level tracking across Land, Infrastructure, Superstructure, MEP, Consultancy & Contingency
          </p>
        </div>
        <select
          aria-label="Select project for budget view"
          value={selectedPrj}
          onChange={(e) => setSelectedPrj(e.target.value)}
          className="px-3 py-1.5 rounded-lg border text-xs"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
        >
          {dataset.projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.code} — {p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-2.5 px-3 font-medium">Cost Category</th>
                <th className="py-2.5 px-3 font-medium text-right">Original</th>
                <th className="py-2.5 px-3 font-medium text-right">Revised</th>
                <th className="py-2.5 px-3 font-medium text-right">Actual</th>
                <th className="py-2.5 px-3 font-medium text-right">Accruals</th>
                <th className="py-2.5 px-3 font-medium text-right">Committed Rem.</th>
                <th className="py-2.5 px-3 font-medium text-right">Addl. ETC</th>
                <th className="py-2.5 px-3 font-medium text-right">Forecast EAC</th>
                <th className="py-2.5 px-3 font-medium text-right">Variance</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => {
                const eac = roundOMR(l.actualCostOMR + l.accrualsOMR + l.committedContractsOMR + l.estimatedCostToCompleteOMR);
                const variance = roundOMR(eac - l.revisedBudgetOMR);
                return (
                  <tr key={l.costCategory} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                    <td className="py-2.5 px-3 font-medium" style={{ color: 'var(--re-text)' }}>{l.costCategory}</td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(l.originalBudgetOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(l.revisedBudgetOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(l.actualCostOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(l.accrualsOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(l.committedContractsOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(l.estimatedCostToCompleteOMR, currency, false, true)} masked={masked} /></td>
                    <td className="py-2.5 px-3 text-right font-semibold"><MaskedValue formatted={formatMoney(eac, currency, false, true)} masked={masked} /></td>
                    <td className={`py-2.5 px-3 text-right font-semibold ${variance > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                      <MaskedValue formatted={formatMoney(variance, currency, false, true)} masked={masked} />
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

export const ContractsProcurementView: React.FC<{
  dataset: MisDataset;
  projectFilterId: string | 'ALL';
  currency: CurrencyCode;
  masked: boolean;
}> = ({ dataset, projectFilterId, currency, masked }) => {
  const rows = dataset.contractors.filter((c) => projectFilterId === 'ALL' || c.projectId === projectFilterId);
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Contracts, Variations, Retentions & Claims
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Contractor IPC certification, unrecovered advances, retention held, and performance bonds
        </p>
      </div>
      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text-muted)' }}>
                <th className="py-2.5 px-3 font-medium">Contractor & Package</th>
                <th className="py-2.5 px-3 font-medium text-right">Revised Contract</th>
                <th className="py-2.5 px-3 font-medium text-right">Pending Claims</th>
                <th className="py-2.5 px-3 font-medium text-right">Certified</th>
                <th className="py-2.5 px-3 font-medium text-right">Paid</th>
                <th className="py-2.5 px-3 font-medium text-right">Retention Held</th>
                <th className="py-2.5 px-3 font-medium text-right">Perf. Bond</th>
                <th className="py-2.5 px-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0" style={{ borderColor: 'var(--re-border)' }}>
                  <td className="py-2.5 px-3">
                    <div className="font-medium" style={{ color: 'var(--re-text)' }}>{c.contractorName}</div>
                    <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>{c.packageTitle}</div>
                  </td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(c.originalContractOMR + c.approvedVariationsOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right text-amber-600 dark:text-amber-400"><MaskedValue formatted={formatMoney(c.pendingClaimsOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(c.certifiedToDateOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(c.paidToDateOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(c.retentionHeldOMR, currency, false, true)} masked={masked} /></td>
                  <td className="py-2.5 px-3 text-right"><MaskedValue formatted={formatMoney(c.performanceBondOMR, currency, false, true)} masked={masked} /></td>
                  <td className={`py-2.5 px-3 font-medium ${c.status === 'Disputed' ? 'text-rose-600 dark:text-rose-400' : ''}`}>{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
