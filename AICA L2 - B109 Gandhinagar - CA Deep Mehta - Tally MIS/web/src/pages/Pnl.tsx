import { useState } from 'react';
import { fmtDate, fmtMoney, fmtNum } from '@shared/format';
import { useCompanyQuery } from '../api';
import { StatementTable } from '../components/Statement';
import { BarsChart, TrendChart } from '../components/charts';
import { Change, DataTable, ExportButtons, FLink, Money, Notes, Pct, Q, Share, StatusBadge, Tabs, useTab } from '../components/ui';

export function PnlPage() {
  const tab = useTab('statement');
  return (
    <div>
      <div className="row"><h1>Profit &amp; loss</h1><span className="spacer" />{tab === 'statement' && <ExportButtons report="pnl" />}{tab === 'products' && <ExportButtons report="products" />}</div>
      <Tabs tabs={[{ key: 'statement', label: 'Statement' }, { key: 'revenue', label: 'Revenue' }, { key: 'costs', label: 'Costs & expenses' }, { key: 'products', label: 'Product profitability' }, { key: 'top', label: 'Top products' }]} />
      {tab === 'statement' && <Statement />}
      {tab === 'revenue' && <Revenue />}
      {tab === 'costs' && <Costs />}
      {tab === 'products' && <Products />}
      {tab === 'top' && <TopProducts />}
    </div>
  );
}

function FigureRow({ f, label }: { f: any; label: string }) {
  return <tr><td>{label}</td><td className="num"><Money v={f.value} exact /></td><td><StatusBadge status={f.status} /></td><td className="small muted">{f.notes.join(' ')}</td></tr>;
}

function Statement() {
  const [view, setView] = useState('compare');
  const q = useCompanyQuery<any>('/pnl', { view });
  return (
    <Q q={q}>
      {(d) => {
        const cur = d.current;
        const columns = view === 'compare'
          ? [{ label: `${fmtDate(cur.range.from)} – ${fmtDate(cur.range.to)}`, sections: cur.sections, subtotals: cur.subtotals }, ...(d.previous ? [{ label: `${fmtDate(d.prevRange.from)} – ${fmtDate(d.prevRange.to)}`, sections: d.previous.sections, subtotals: d.previous.subtotals }] : [])]
          : [...d.columns.map((c: any) => ({ label: c.label, sections: c.pnl.sections, subtotals: c.pnl.subtotals })), { label: 'Total', sections: cur.sections, subtotals: cur.subtotals }];
        const f = cur.figures;
        return (
          <div>
            <div className="row mb">
              <select aria-label="Statement view" value={view} onChange={(e) => setView(e.target.value)}>
                <option value="compare">Current vs comparison (horizontal &amp; vertical analysis)</option>
                <option value="monthly">Monthly columns</option>
                <option value="quarterly">Quarterly columns</option>
              </select>
              <span className="small muted">{d.signConvention}</span>
            </div>
            {d.costCentreNote && <div className="banner info small">{d.costCentreNote}</div>}
            {cur.unclassified.length > 0 && <div className="banner warn small">⚠ {cur.unclassified.length} ledger(s) with activity are unclassified and excluded from P&L lines. <FLink to="/settings/mapping">Map them →</FLink></div>}
            <div className="card">
              <StatementTable columns={columns} base={f.revenue.value} budget={view === 'compare' ? d.budget : null} />
            </div>
            <div className="card mt">
              <h2>Key figures and how they are derived</h2>
              <table className="data"><tbody>
                <FigureRow f={f.grossSales} label="Gross sales" /><FigureRow f={f.salesReturns} label="Less: returns & reductions" /><FigureRow f={f.revenue} label="Revenue from operations (net)" />
                <FigureRow f={f.openingStock} label="Opening stock" /><FigureRow f={f.purchases} label="Purchases" /><FigureRow f={f.directExpenses} label="Direct expenses" /><FigureRow f={f.closingStock} label="Closing stock" />
                <FigureRow f={f.cogs} label="Cost of goods sold" /><FigureRow f={f.grossProfit} label="Gross profit" /><FigureRow f={f.opex} label="Operating expenses" />
                <FigureRow f={f.ebitda} label="EBITDA" /><FigureRow f={f.depreciation} label="Depreciation & amortisation" /><FigureRow f={f.ebit} label="EBIT" />
                <FigureRow f={f.otherIncome} label="Other income" /><FigureRow f={f.financeCost} label="Finance costs" /><FigureRow f={f.exceptional} label="Exceptional items" />
                <FigureRow f={f.pbt} label="Profit before tax" /><FigureRow f={f.tax} label="Tax" /><FigureRow f={f.netProfit} label="Net profit" />
              </tbody></table>
              <p className="small muted mt">Classification reliability: {cur.reliability.unverifiedSharePct.toFixed(0)}% of P&amp;L activity uses unverified (automatic) mappings; {cur.reliability.lowConfidenceSharePct.toFixed(0)}% low-confidence.</p>
            </div>
          </div>
        );
      }}
    </Q>
  );
}

function Concentration({ c, label }: { c: any; label: string }) {
  if (!c) return null;
  return (
    <div className="card">
      <h3>{label} concentration</h3>
      <table className="data"><tbody>
        <tr><td>Top 5 share</td><td className="num"><Pct v={c.top5} /></td></tr>
        <tr><td>Top 10 share</td><td className="num"><Pct v={c.top10} /></td></tr>
        <tr><td>Top 20 share</td><td className="num"><Pct v={c.top20} /></td></tr>
        <tr><td title="Herfindahl-Hirschman index: < 1,500 unconcentrated, > 2,500 highly concentrated">HHI</td><td className="num">{c.hhi === null ? '—' : fmtNum(c.hhi, 0)}</td></tr>
        <tr><td>Contributors</td><td className="num">{c.count}</td></tr>
      </tbody></table>
    </div>
  );
}

function Revenue() {
  const q = useCompanyQuery<any>('/pnl/revenue');
  return (
    <Q q={q}>
      {(d) => (
        <div>
          <div className="kpis mb">
            {[['Gross sales', d.totals.grossSales], ['Returns & reductions', d.totals.salesReturns], ['Net revenue', d.totals.revenue], ['Other income (non-operating)', d.totals.otherIncome]].map(([l, v]) => (
              <div className="card" key={l as string}><div className="small secondary">{l}</div><div style={{ fontSize: 20, fontWeight: 650 }}><Money v={v as number} /></div></div>
            ))}
          </div>
          <div className="grid g2">
            <div className="card"><TrendChart title="Monthly revenue" subtitle="Seasonality and trend" data={d.monthly} xKey="month" series={[{ key: 'revenue', label: 'Revenue' }]} /></div>
            <div className="card"><BarsChart title="Top income ledgers" horizontal data={d.ledgers.slice(0, 10).map((l: any) => ({ label: l.ledger, value: l.amount }))} series={[{ key: 'value', label: 'Revenue' }]} colorBySign /></div>
            <Concentration c={d.customerConcentration} label="Customer" />
            <Concentration c={d.productConcentration} label="Product" />
            {d.byCostCentre.length > 0 && <div className="card"><BarsChart title="Revenue by cost centre" horizontal data={d.byCostCentre.map((c: any) => ({ label: c.costCentre, value: c.amount }))} series={[{ key: 'value', label: 'Revenue' }]} /></div>}
            {d.byProductGroup.length > 0 && <div className="card"><BarsChart title="Revenue by product group" horizontal data={d.byProductGroup.map((g: any) => ({ label: g.group, value: g.netSales }))} series={[{ key: 'value', label: 'Net sales' }]} /></div>}
          </div>
          <div className="card mt">
            <h2>Top income ledgers</h2>
            <DataTable rows={d.ledgers} search={false} columns={[
              { key: 'ledger', label: 'Ledger', render: (r: any) => <FLink to={`/ledgers/${r.ledgerId}`}>{r.ledger}</FLink> },
              { key: 'classLabel', label: 'Class' },
              { key: 'amount', label: 'Amount', num: true, render: (r: any) => <Money v={r.amount} /> },
              { key: 'previous', label: 'Comparison', num: true, render: (r: any) => <Money v={r.previous} /> },
              { key: 'changePct', label: 'Change', num: true, render: (r: any) => <Change v={r.changePct} /> },
              { key: 'sharePct', label: 'Share', render: (r: any) => <Share v={r.sharePct} /> },
            ]} />
          </div>
          <div className="card mt">
            <h2>Revenue by customer</h2>
            <DataTable rows={d.customers} columns={[
              { key: 'customer', label: 'Customer', render: (r: any) => (r.ledgerId && r.isDebtor ? <FLink to={`/ledgers/${r.ledgerId}`}>{r.customer}</FLink> : r.customer) },
              { key: 'invoices', label: 'Vouchers', num: true },
              { key: 'amount', label: 'Revenue', num: true, render: (r: any) => <Money v={r.amount} /> },
              { key: 'previous', label: 'Comparison', num: true, render: (r: any) => <Money v={r.previous} /> },
              { key: 'changePct', label: 'Growth', num: true, render: (r: any) => <Change v={r.changePct} /> },
              { key: 'sharePct', label: 'Share', render: (r: any) => <Share v={r.sharePct} /> },
            ]} />
            <Notes notes={d.notes} />
          </div>
        </div>
      )}
    </Q>
  );
}

function Costs() {
  const q = useCompanyQuery<any>('/pnl/costs');
  return (
    <Q q={q}>
      {(d) => (
        <div>
          {d.totals.cogsStatus !== 'actual' && <div className="banner info small">COGS status: <StatusBadge status={d.totals.cogsStatus} /> {d.totals.cogsNotes.join(' ')}</div>}
          <div className="grid g2">
            <div className="card"><TrendChart title="Cost trend" data={d.monthly} xKey="month" series={[{ key: 'cogs', label: 'COGS' }, { key: 'opex', label: 'Operating expenses' }, { key: 'financeCost', label: 'Finance costs' }]} /></div>
            <div className="card"><BarsChart title="Expenses by class" horizontal data={d.classes.map((c: any) => ({ label: c.label, value: c.amount, previous: c.previous }))}
              series={[{ key: 'value', label: 'This period' }, ...(d.classes.some((c: any) => c.previous !== null) ? [{ key: 'previous', label: 'Comparison' }] : [])]} /></div>
          </div>
          <div className="card mt">
            <h2>Top 20 expense ledgers</h2>
            <DataTable rows={d.ledgers} search={false} pageSize={20} columns={[
              { key: 'ledger', label: 'Ledger', render: (r: any) => <FLink to={`/ledgers/${r.ledgerId}`}>{r.ledger}</FLink> },
              { key: 'classLabel', label: 'Class', render: (r: any) => <>{r.classLabel}{r.unverified && <span className="muted small"> ·unverified</span>}</> },
              { key: 'amount', label: 'Amount', num: true, render: (r: any) => <Money v={r.amount} /> },
              { key: 'previous', label: 'Comparison', num: true, render: (r: any) => <Money v={r.previous} /> },
              { key: 'changePct', label: 'Growth', num: true, render: (r: any) => <Change v={r.changePct} better="lower" /> },
              { key: 'sharePct', label: 'Share of expenses', render: (r: any) => <Share v={r.sharePct} /> },
              { key: 'costBehavior', label: 'Fixed/variable', render: (r: any) => r.costBehavior ?? <span className="muted">—</span> },
            ]} />
          </div>
          <div className="grid g2 mt">
            <div className="card">
              <h2>Fixed vs variable &amp; break-even</h2>
              <table className="data"><tbody>
                <tr><td>Fixed (tagged)</td><td className="num"><Money v={d.fixedVariable.fixed} /></td></tr>
                <tr><td>Variable (tagged)</td><td className="num"><Money v={d.fixedVariable.variable} /></td></tr>
                <tr><td>Not tagged</td><td className="num"><Money v={d.fixedVariable.unassigned} /></td></tr>
                <tr><td>Coverage</td><td className="num"><Pct v={d.fixedVariable.coveragePct} /></td></tr>
                <tr><td>Break-even revenue</td><td className="num">{d.fixedVariable.breakEvenRevenue === null ? <span className="muted">Unavailable</span> : <Money v={d.fixedVariable.breakEvenRevenue} />}</td></tr>
              </tbody></table>
              <p className="small muted">{d.fixedVariable.note}</p>
            </div>
            <div className="card">
              <h2>Unusual expense movements</h2>
              <p className="small muted">Ledger-months more than 3 standard deviations from that ledger's trailing 12-month pattern (≥ 6 months of history). Flags for review, not findings.</p>
              <DataTable rows={d.anomalies} search={false} pageSize={10} empty="No unusual movements detected" columns={[
                { key: 'ledger', label: 'Ledger', render: (r: any) => <FLink to={`/ledgers/${r.ledgerId}`}>{r.ledger}</FLink> },
                { key: 'month', label: 'Month' },
                { key: 'amount', label: 'Amount', num: true, render: (r: any) => <Money v={r.amount} /> },
                { key: 'mean', label: 'Typical', num: true, render: (r: any) => <Money v={r.mean} /> },
                { key: 'z', label: 'σ', num: true, render: (r: any) => r.z.toFixed(1) },
              ]} />
            </div>
          </div>
        </div>
      )}
    </Q>
  );
}

const FLAG_LABEL: Record<string, string> = { declining_margin: 'Margin declining', sales_up_profit_down: 'Sales ↑ profit ↓', strong_sales_weak_margin: 'High sales, thin margin', loss_making: 'Loss-making' };

function Products() {
  const q = useCompanyQuery<any>('/products');
  return (
    <Q q={q}>
      {(d) => !d.available ? <div className="banner info">{d.reason}</div> : (
        <div>
          <div className="banner info small">≈ {d.basis}</div>
          <div className="grid g2 mb">
            <div className="card"><BarsChart title="Top gross-profit contributors" horizontal data={[...d.rows].sort((a: any, b: any) => b.grossProfit - a.grossProfit).slice(0, 10).map((r: any) => ({ label: r.item, value: r.grossProfit }))} series={[{ key: 'value', label: 'Gross profit (est.)' }]} colorBySign /></div>
            <div className="card"><BarsChart title="Lowest margins (material items)" subtitle="Items with ≥ 1% of net sales" horizontal unit="percent"
              data={d.rows.filter((r: any) => (r.salesSharePct ?? 0) >= 1 && r.marginPct !== null).sort((a: any, b: any) => a.marginPct - b.marginPct).slice(0, 10).map((r: any) => ({ label: r.item, value: r.marginPct }))}
              series={[{ key: 'value', label: 'Margin %' }]} colorBySign /></div>
          </div>
          <div className="card">
            <DataTable rows={d.rows} initialSort={{ key: 'netSales', dir: -1 }} columns={[
              { key: 'item', label: 'Item' }, { key: 'group', label: 'Group' },
              { key: 'netQty', label: 'Net qty', num: true, render: (r: any) => `${fmtNum(r.netQty)} ${r.unit ?? ''}` },
              { key: 'netSales', label: 'Net sales', num: true, render: (r: any) => <Money v={r.netSales} /> },
              { key: 'salesReturns', label: 'Returns', num: true, render: (r: any) => <Money v={r.salesReturns} /> },
              { key: 'estCost', label: 'Est. COGS', num: true, render: (r: any) => <Money v={r.estCost} /> },
              { key: 'grossProfit', label: 'Gross profit', num: true, render: (r: any) => <Money v={r.grossProfit} /> },
              { key: 'marginPct', label: 'Margin', num: true, render: (r: any) => <Pct v={r.marginPct} /> },
              { key: 'prevMarginPct', label: 'Prior margin', num: true, render: (r: any) => <Pct v={r.prevMarginPct} /> },
              { key: 'avgSellingPrice', label: 'Avg price', num: true, render: (r: any) => fmtMoney(r.avgSellingPrice, { exact: true }) },
              { key: 'salesGrowthPct', label: 'Sales growth', num: true, render: (r: any) => <Change v={r.salesGrowthPct} /> },
              { key: 'gpSharePct', label: 'GP share', render: (r: any) => <Share v={r.gpSharePct} /> },
              { key: 'flags', label: 'Flags', value: (r: any) => r.flags.join(','), render: (r: any) => r.flags.map((f: string) => <span key={f} className="badge medium" style={{ marginRight: 4 }}>{FLAG_LABEL[f]}</span>) },
            ]} />
          </div>
        </div>
      )}
    </Q>
  );
}

function TopProducts() {
  const q = useCompanyQuery<any>('/products');
  const [metric, setMetric] = useState('sold_amount');
  const [n, setN] = useState(20);
  const [unit, setUnit] = useState('');
  const [group, setGroup] = useState('');
  return (
    <Q q={q}>
      {(d) => {
        if (!d.available) return <div className="banner info">{d.reason}</div>;
        const qtyMetric = metric.endsWith('qty');
        const u = unit || d.units[0] || '';
        const groups = [...new Set(d.rows.map((r: any) => r.group).filter(Boolean))] as string[];
        const key = { sold_amount: 'netSales', sold_qty: 'netQty', purchased_amount: 'purchaseValue', purchased_qty: 'purchaseQty' }[metric]!;
        const rows = d.rows.filter((r: any) => (!qtyMetric || r.unit === u) && (!group || r.group === group) && r[key] > 0).sort((a: any, b: any) => b[key] - a[key]).slice(0, n);
        const total = d.rows.filter((r: any) => (!qtyMetric || r.unit === u) && (!group || r.group === group)).reduce((a: number, r: any) => a + Math.max(0, r[key]), 0);
        const sold = metric.startsWith('sold');
        return (
          <div className="card">
            <div className="row mb">
              <select aria-label="Ranking metric" value={metric} onChange={(e) => setMetric(e.target.value)}>
                <option value="sold_amount">Products sold — by amount</option><option value="sold_qty">Products sold — by quantity</option>
                <option value="purchased_amount">Products purchased — by amount</option><option value="purchased_qty">Products purchased — by quantity</option>
              </select>
              {qtyMetric && <select aria-label="Unit" value={u} onChange={(e) => setUnit(e.target.value)}>{d.units.map((x: string) => <option key={x}>{x}</option>)}</select>}
              <select aria-label="Product group" value={group} onChange={(e) => setGroup(e.target.value)}><option value="">All groups</option>{groups.map((g) => <option key={g}>{g}</option>)}</select>
              <select aria-label="Number of rows" value={n} onChange={(e) => setN(Number(e.target.value))}>{[10, 20, 50].map((x) => <option key={x} value={x}>Top {x}</option>)}</select>
            </div>
            {qtyMetric && <p className="small muted">Quantity rankings include only items measured in “{u}” — quantities in different units are never added together.</p>}
            <table className="data">
              <thead><tr><th>#</th><th>Product</th><th>Group</th><th className="num">Quantity</th><th className="num">Amount</th><th className="num">Avg rate</th><th className="num">Period change</th><th>Share</th></tr></thead>
              <tbody>{rows.map((r: any, i: number) => (
                <tr key={r.itemId}>
                  <td>{i + 1}</td><td>{r.item}</td><td>{r.group}</td>
                  <td className="num">{fmtNum(sold ? r.netQty : r.purchaseQty)} {r.unit}</td>
                  <td className="num"><Money v={sold ? r.netSales : r.purchaseValue} /></td>
                  <td className="num">{fmtMoney(sold ? r.avgSellingPrice : r.avgPurchaseRate, { exact: true })}</td>
                  <td className="num">{sold ? <Change v={r.salesGrowthPct} /> : <span className="muted">—</span>}</td>
                  <td><Share v={total ? (Math.max(0, r[key]) / total) * 100 : null} /></td>
                </tr>))}</tbody>
            </table>
          </div>
        );
      }}
    </Q>
  );
}
