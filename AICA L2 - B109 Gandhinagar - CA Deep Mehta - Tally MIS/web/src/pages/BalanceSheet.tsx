import { fmtDate, fmtMoney } from '@shared/format';
import type { KpiResult } from '@shared/types';
import { useCompanyQuery } from '../api';
import { StatementTable } from '../components/Statement';
import { BarsChart, TrendChart } from '../components/charts';
import { KpiCard } from '../components/KpiCard';
import { DataTable, ExportButtons, FLink, Money, Notes, Q, SeverityBadge, Tabs, useTab } from '../components/ui';

export function BalanceSheetPage() {
  const tab = useTab('statement');
  return (
    <div>
      <div className="row"><h1>Balance sheet</h1><span className="spacer" />{tab === 'statement' && <ExportButtons report="bs" />}</div>
      <Tabs tabs={[{ key: 'statement', label: 'Statement' }, { key: 'liquidity', label: 'Liquidity' }, { key: 'solvency', label: 'Solvency & capital' }, { key: 'quality', label: 'Asset quality & returns' }, { key: 'risk', label: 'Risk & integrity checks' }, { key: 'cashflow', label: 'Cash flow' }]} />
      {tab === 'statement' && <Statement />}
      {tab === 'liquidity' && <RatioTab codes={['current_ratio', 'quick_ratio', 'cash_ratio', 'working_capital', 'cash_bank', 'operating_cash_flow', 'cash_runway_months', 'overdue_receivables_pct']} series={[['currentRatio', 'Current ratio'], ['quickRatio', 'Quick ratio']]} money={[['cash', 'Cash & bank'], ['workingCapital', 'Working capital']]} />}
      {tab === 'solvency' && <RatioTab codes={['debt_to_equity', 'liabilities_to_assets_pct', 'equity_ratio_pct', 'net_debt', 'interest_coverage', 'finance_cost_ratio_pct']} series={[['debtToEquity', 'Debt to equity']]} money={[['debt', 'Interest-bearing debt'], ['equity', 'Equity']]}
        note="Debt = liabilities flagged interest-bearing (all borrowings by default; change per ledger in Ledger mapping). Equity = capital + reserves + accumulated profit." />}
      {tab === 'quality' && <RatioTab codes={['roa_pct', 'roe_pct', 'roce_pct', 'fixed_asset_turnover', 'receivable_days', 'inventory_days', 'payable_days', 'cash_conversion_cycle']} series={[]} money={[['totalAssets', 'Total assets']]}
        note="Returns use annualised profit and average of opening and closing balances. Capital employed = equity + interest-bearing debt." />}
      {tab === 'risk' && <Risk />}
      {tab === 'cashflow' && <CashFlow />}
    </div>
  );
}

function Statement() {
  const q = useCompanyQuery<any>('/bs');
  return (
    <Q q={q}>
      {(d) => {
        const cols = (b: any, side: string) => b.sections.filter((s: any) => s.side === side);
        const t = d.current.totals;
        return (
          <div>
            {Math.abs(t.difference) > 0.5 && <div className="banner error">⚠ Assets differ from liabilities + equity by {fmtMoney(t.difference, { exact: true })}. <FLink to="/data-quality">See data quality</FLink></div>}
            <Notes notes={d.current.notes} />
            <div className="grid">
              {(['assets', 'liabilities'] as const).map((side) => (
                <div className="card" key={side}>
                  <h2>{side === 'assets' ? 'Assets' : 'Equity & liabilities'}</h2>
                  <StatementTable verticalLabel="% of total" base={t.totalAssets} columns={[
                    { label: `At ${fmtDate(d.current.asOf)}`, sections: cols(d.current, side) },
                    { label: `${d.comparisonLabel} ${fmtDate(d.comparison.asOf)}`, sections: cols(d.comparison, side) },
                  ]} />
                </div>
              ))}
            </div>
            <div className="card mt small">
              <table className="data"><tbody>
                <tr><td>Total assets</td><td className="num"><Money v={t.totalAssets} exact /></td></tr>
                <tr><td>Total liabilities</td><td className="num"><Money v={t.totalLiabilities} exact /></td></tr>
                <tr><td>Equity</td><td className="num"><Money v={t.equity} exact /></td></tr>
                <tr><td>Suspense, unclassified &amp; opening differences</td><td className="num"><Money v={t.suspenseAndOther} exact /></td></tr>
                <tr className="total"><td>Check: assets − (liabilities + equity + other)</td><td className="num"><Money v={t.difference} exact /></td></tr>
              </tbody></table>
              <p className="muted">Ledger balances are rebuilt from opening balances plus posted vouchers. Groups follow your ledger mapping, not Tally's statutory layout; ambiguous classifications are marked “unverified”.</p>
            </div>
          </div>
        );
      }}
    </Q>
  );
}

function RatioTab({ codes, series, money, note }: { codes: string[]; series: [string, string][]; money: [string, string][]; note?: string }) {
  const k = useCompanyQuery<KpiResult[]>('/kpis', { codes: codes.join(','), trend: '1' });
  const a = useCompanyQuery<any>('/bs/analysis');
  return (
    <div>
      {note && <p className="small muted">{note}</p>}
      <Q q={k}>{(ks) => <div className="kpis">{codes.map((c) => ks.find((x) => x.code === c)).filter(Boolean).map((x) => <KpiCard key={x!.code} k={x!} />)}</div>}</Q>
      <Q q={a}>
        {(d) => (
          <div className="grid g2 mt">
            {series.length > 0 && <div className="card"><TrendChart title="Ratio trend (month-end)" unit="ratio" data={d.trend} xKey="month" series={series.map(([key, label]) => ({ key, label }))} /></div>}
            {money.length > 0 && <div className="card"><TrendChart title="Balances (month-end)" data={d.trend} xKey="month" zeroLine series={money.map(([key, label]) => ({ key, label }))} /></div>}
          </div>
        )}
      </Q>
    </div>
  );
}

function Risk() {
  const q = useCompanyQuery<any>('/bs/analysis');
  return (
    <Q q={q}>
      {(d) => (
        <div className="card">
          <p className="small muted">Analytical flags requiring review. An anomaly is not an error until verified.</p>
          <DataTable rows={d.flags} search={false} empty="No balance-sheet flags for this period" columns={[
            { key: 'severity', label: 'Severity', render: (r: any) => <SeverityBadge severity={r.severity} /> },
            { key: 'title', label: 'Flag', render: (r: any) => <>{r.link ? <FLink to={r.link}>{r.title}</FLink> : r.title}<div className="small muted">{r.detail}</div></> },
            { key: 'amount', label: 'Amount', num: true, render: (r: any) => <Money v={r.amount} /> },
            { key: 'rule', label: 'Rule', render: (r: any) => <span className="small">{r.rule}</span> },
            { key: 'action', label: 'Follow-up', render: (r: any) => <span className="small">{r.action}</span> },
          ]} />
        </div>
      )}
    </Q>
  );
}

function CashFlow() {
  const q = useCompanyQuery<any>('/cashflow');
  return (
    <Q q={q}>
      {(d) => (
        <div>
          <div className="kpis mb">
            {[['Opening cash & bank', d.opening], ['Operating', d.byCategory.operating], ['Investing', d.byCategory.investing], ['Financing', d.byCategory.financing], ['Unclassified', d.byCategory.unclassified], ['Closing cash & bank', d.closing]].map(([l, v]) => (
              <div className="card" key={l}><div className="small secondary">{l}</div><div style={{ fontSize: 20, fontWeight: 650 }}><Money v={v} /></div></div>
            ))}
          </div>
          {Math.abs(d.check) > 1 && <div className="banner warn">Cash flow differs from the change in cash balances by {fmtMoney(d.check, { exact: true })}.</div>}
          <div className="grid g2">
            <div className="card"><BarsChart title="Monthly cash flow by activity" data={d.monthly} xKey="month" stacked
              series={[{ key: 'operating', label: 'Operating' }, { key: 'investing', label: 'Investing' }, { key: 'financing', label: 'Financing' }, { key: 'unclassified', label: 'Unclassified' }]} /></div>
            <div className="card">
              <h2>Flows by contra-ledger class</h2>
              <DataTable rows={d.byClass} search={false} pageSize={12} columns={[
                { key: 'label', label: 'Class' }, { key: 'category', label: 'Activity' },
                { key: 'inflow', label: 'Inflow', num: true, render: (r: any) => <Money v={r.inflow} /> },
                { key: 'outflow', label: 'Outflow', num: true, render: (r: any) => <Money v={r.outflow} /> },
              ]} />
            </div>
          </div>
          <Notes notes={[...d.notes, 'Direct method: each cash/bank voucher is attributed to the classes of its other ledgers, so mixed vouchers (e.g. receipts net of discount) split exactly.']} />
        </div>
      )}
    </Q>
  );
}
