import type { KpiResult, Insight } from '@shared/types';
import { fmtDate, fmtMoney } from '@shared/format';
import { useCompanyQuery } from '../api';
import { KpiCard } from '../components/KpiCard';
import { BarsChart, TrendChart } from '../components/charts';
import { FLink, Q, SeverityBadge, ExportButtons } from '../components/ui';

export function InsightList({ items }: { items: Insight[] }) {
  if (!items.length) return <p className="muted">No rule fired for this period.</p>;
  return (
    <div>
      {items.map((i) => (
        <div key={i.id} className={`insight ${i.severity}`}>
          <div className="row"><strong>{i.headline}</strong><span className="spacer" /><SeverityBadge severity={i.severity} /><span className="badge" title="Confidence in the underlying data">conf. {i.confidence}</span></div>
          <div className="small secondary">{i.metric}: {i.current} <span className="muted">(baseline {i.baseline})</span></div>
          <div className="small">{i.explanation}</div>
          {i.possibleCauses && <div className="small muted">Possible causes (hypotheses, not findings): {i.possibleCauses.join('; ')}</div>}
          <div className="small"><strong>Suggested action:</strong> {i.action}</div>
          <div className="small muted">Rule: {i.rule}{i.drill && <> · <FLink to={i.drill.path}>{i.drill.label} →</FLink></>}</div>
        </div>
      ))}
    </div>
  );
}

export function Dashboard() {
  const q = useCompanyQuery<any>('/dashboard');
  return (
    <Q q={q}>
      {(d) => (
        <div>
          <div className="row mb">
            <div>
              <h1>Executive overview</h1>
              <p className="small muted">{fmtDate(d.range.from)} – {fmtDate(d.range.to)}{d.prev ? ` · compared with ${fmtDate(d.prev.from)} – ${fmtDate(d.prev.to)}` : ''} · Profile: {d.profile.label}</p>
            </div>
            <span className="spacer" />
            <ExportButtons report="kpis" />
          </div>
          {(d.dq.high > 0 || d.reliability.lowConfidenceSharePct > 10) && (
            <div className="banner warn" role="note">
              ⚠ Data-quality warnings: {d.dq.high} high-severity issue{d.dq.high === 1 ? '' : 's'}
              {d.reliability.lowConfidenceSharePct > 10 ? `; ${d.reliability.lowConfidenceSharePct.toFixed(0)}% of P&L activity uses low-confidence classifications` : ''}.
              <FLink to="/data-quality">Review →</FLink>
            </div>
          )}
          {d.stockSource.closing === 'estimated_replay' && <div className="banner info small">≈ Closing stock for this period is estimated (no Tally valuation snapshot at {fmtDate(d.range.to)}). COGS-based figures are marked “Estimated”.</div>}

          <div className="kpis">{d.kpis.map((k: KpiResult) => <KpiCard key={k.code} k={k} />)}</div>

          <div className="grid g2 mt">
            <div className="card"><TrendChart title="Revenue and net profit" subtitle="Monthly; net profit can be negative" data={d.series} zeroLine
              series={[{ key: 'revenue', label: 'Revenue' }, { key: 'netProfit', label: 'Net profit' }]} /></div>
            <div className="card"><TrendChart title="Revenue vs total expenses" subtitle="Expenses = revenue − net profit (all costs incl. COGS, tax)" data={d.series}
              series={[{ key: 'revenue', label: 'Revenue' }, { key: 'expenses', label: 'Total expenses' }]} /></div>
            <div className="card"><TrendChart title="Gross and net margin" data={d.series} unit="percent" zeroLine
              series={[{ key: 'grossMarginPct', label: 'Gross margin %' }, { key: 'netMarginPct', label: 'Net margin %' }]} /></div>
            <div className="card"><TrendChart title="Cash and working capital" subtitle="Month-end balances" data={d.series} zeroLine
              series={[{ key: 'cash', label: 'Cash & bank' }, { key: 'workingCapital', label: 'Working capital' }]} /></div>
            {d.prevSeries.length > 0 && (
              <div className="card"><TrendChart title="Revenue: this period vs comparison" subtitle="Month by month, aligned by position in the period"
                data={d.series.map((s: any, i: number) => ({ label: s.label, current: s.revenue, previous: d.prevSeries[i]?.revenue ?? null }))}
                series={[{ key: 'current', label: 'This period' }, { key: 'previous', label: 'Comparison', dashed: true }]} /></div>
            )}
            <div className="card"><BarsChart title="Where the money goes" subtitle="Cost composition for the period" horizontal data={d.composition.expenses} series={[{ key: 'value', label: 'Amount' }]} /></div>
            <div className="card"><BarsChart title="Top revenue ledgers" horizontal data={d.topRevenue} series={[{ key: 'value', label: 'Revenue' }]} /></div>
            <div className="card"><BarsChart title="Top expense ledgers" subtitle="Operating, D&A, finance and exceptional" horizontal data={d.topExpenses} series={[{ key: 'value', label: 'Expense' }]} /></div>
            {d.exposure && (
              <div className="card">
                <h2>Receivables and payables exposure</h2>
                <p className="small muted">Bill-wise ageing at {fmtDate(d.range.to)} (by due date). Receivables {fmtMoney(d.exposure.receivables.total)} ({fmtMoney(d.exposure.receivables.overdue)} overdue); payables {fmtMoney(d.exposure.payables.total)}.</p>
                <BarsChart data={d.exposure.bucketOrder.map((b: string) => ({ label: b, receivables: d.exposure.receivables.buckets.find((x: any) => x.bucket === b)?.value ?? 0, payables: d.exposure.payables.buckets.find((x: any) => x.bucket === b)?.value ?? 0 })).filter((r: any) => r.receivables || r.payables)}
                  series={[{ key: 'receivables', label: 'Receivables' }, { key: 'payables', label: 'Payables' }]} />
                <FLink to="/receivables-payables">Ageing detail →</FLink>
              </div>
            )}
            {d.inventoryMode !== 'none' && (
              <div className="card"><TrendChart title="Inventory, receivables and payables" subtitle="Month-end balances" data={d.series}
                series={[{ key: 'inventory', label: 'Inventory' }, { key: 'receivables', label: 'Receivables' }, { key: 'payables', label: 'Payables' }]} /></div>
            )}
          </div>

          {d.insightCount > 0 && (
            <div className="card mt">
              <div className="row"><h2>Insights &amp; alerts</h2></div>
              <InsightList items={d.insights} />
            </div>
          )}
          {d.profile.notes.length > 0 && <p className="small muted mt">Industry profile notes: {d.profile.notes.join(' ')}</p>}
        </div>
      )}
    </Q>
  );
}
