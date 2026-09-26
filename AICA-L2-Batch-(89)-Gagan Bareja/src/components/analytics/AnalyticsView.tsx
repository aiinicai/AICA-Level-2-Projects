import React, { useState } from 'react';
import {
  TrendingUp,
  PackageCheck,
  Users,
  Layers,
  Filter,
  AlertTriangle,
  ArrowUpRight,
  ShieldAlert,
  Calendar,
  Download,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import { Customer, SalesInvoice, StockItem, SystemSettings } from '../../types';
import { computeInventoryProvision, formatINR, formatLakhs } from '../../services/accountingEngine';

interface AnalyticsViewProps {
  salesInvoices: SalesInvoice[];
  stockItems: StockItem[];
  customers: Customer[];
  settings: SystemSettings;
}

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({
  salesInvoices,
  stockItems,
  customers,
  settings,
}) => {
  const [activeTab, setActiveTab] = useState<'sales' | 'inventory' | 'customer' | 'report_builder'>('sales');
  const [dateRange, setDateRange] = useState<'FY_25_26' | 'Q4' | 'MONTH'>('FY_25_26');

  // Inventory provisioning computation per AS 2
  const inventoryData = computeInventoryProvision(stockItems, settings.inventoryProvisionPolicy);

  // Sales Analytics computations
  const categoryRevenue = [
    { name: 'Automation Hardware', value: 24500000, color: '#6366f1' },
    { name: 'Motion Dynamics', value: 14000000, color: '#3b82f6' },
    { name: 'Raw Materials & Resins', value: 4200000, color: '#10b981' },
    { name: 'Engineering Services', value: 2000000, color: '#f59e0b' },
  ];

  const branchRevenue = [
    { branch: 'Maharashtra (Pune Plant)', state: 'MH (27)', revenue: 32500000, share: '72.7%' },
    { branch: 'Karnataka (Bengaluru Hub)', state: 'KA (29)', revenue: 8400000, share: '18.8%' },
    { branch: 'Delhi NCR Hub', state: 'DL (07)', revenue: 3800000, share: '8.5%' },
  ];

  // Top Customers Ranking & Concentration Risk
  const totalSalesVolume = 44700000;
  const customerRankings = [
    { name: 'Godrej Precision Heavy Systems Ltd', revenue: 16500000, margin: '28.4%', share: 36.9 },
    { name: 'Larsen & Toubro Integrated Infra Ltd', revenue: 14200000, margin: '31.2%', share: 31.7 },
    { name: 'Tata AutoComp Component Solutions', revenue: 7800000, margin: '24.5%', share: 17.4 },
    { name: 'Bengaluru Aerospace Dynamics Pvt Ltd', revenue: 4100000, margin: '34.0%', share: 9.1 },
    { name: 'Premier Machine Tools & Robotics', revenue: 2100000, margin: '18.0%', share: 4.7 },
  ];
  const top2Concentration = (customerRankings[0].share + customerRankings[1].share).toFixed(1);

  // DSO Historical Trend
  const dsoData = [
    { month: 'Oct 25', dso: 52 },
    { month: 'Nov 25', dso: 48 },
    { month: 'Dec 25', dso: 45 },
    { month: 'Jan 26', dso: 43 },
    { month: 'Feb 26', dso: 41 },
    { month: 'Mar 26', dso: 42 },
  ];

  return (
    <div id="analytics-module-container" className="space-y-6">
      {/* Tab Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight">Financial & Operational Analytics</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Interactive drill-down on revenue trends, customer concentration risk, DSO ageing, and AS 2 inventory write-down policies.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Sub Tabs */}
          <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setActiveTab('sales')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
                activeTab === 'sales' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sales Analytics
            </button>
            <button
              onClick={() => setActiveTab('inventory')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
                activeTab === 'inventory' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Inventory & AS 2
            </button>
            <button
              onClick={() => setActiveTab('customer')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
                activeTab === 'customer' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Customer & DSO
            </button>
            <button
              onClick={() => setActiveTab('report_builder')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
                activeTab === 'report_builder' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              GL Pivot Builder
            </button>
          </div>
        </div>
      </div>

      {/* TAB 1: SALES ANALYTICS */}
      {activeTab === 'sales' && (
        <div className="space-y-6">
          {/* Metrics summary banner */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Total Net Invoiced Revenue</div>
              <div className="text-lg font-bold text-slate-100 font-mono mt-1">{formatLakhs(totalSalesVolume)}</div>
              <div className="text-[11px] text-emerald-400 mt-0.5">+18.4% YoY Expansion</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Top 2 Concentration Risk</div>
              <div className="text-lg font-bold text-amber-300 font-mono mt-1">{top2Concentration}%</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Godrej + L&T account for {top2Concentration}% of sales</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Blended Gross Margin</div>
              <div className="text-lg font-bold text-indigo-300 font-mono mt-1">29.8%</div>
              <div className="text-[11px] text-emerald-400 mt-0.5">+1.6% margin improvement</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Active Multi-Branch Outlets</div>
              <div className="text-lg font-bold text-slate-100 font-mono mt-1">3 GSTIN Hubs</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Maharashtra, Karnataka, Delhi</div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Category Mix Pie Chart */}
            <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-xl">
              <h3 className="font-semibold text-slate-100 text-sm">Product Category Contribution</h3>
              <p className="text-[11px] text-slate-400 mb-3">Revenue share across core manufacturing divisions</p>
              <div className="h-64 w-full flex items-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryRevenue}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={85}
                      paddingAngle={4}
                    >
                      {categoryRevenue.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                      formatter={(val: any) => [formatINR(val), 'Revenue']}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Location / Branch Breakdown */}
            <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-xl flex flex-col justify-between">
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">Branch & State-Wise Revenue (GST Split)</h3>
                <p className="text-[11px] text-slate-400 mb-4">Crucial for state-wise GST returns and turnover reconciliation</p>

                <div className="space-y-3">
                  {branchRevenue.map((br) => (
                    <div key={br.branch} className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-200">{br.branch}</span>
                        <span className="font-mono text-indigo-400 font-bold">{formatLakhs(br.revenue)}</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                        <span>GSTIN State Code: <strong className="text-slate-300">{br.state}</strong></span>
                        <span className="text-slate-300 font-medium">Contribution: {br.share}</span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-indigo-500 h-full rounded-full"
                          style={{ width: br.share }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
                <span>Inter-state vs Intra-state split:</span>
                <span className="text-slate-200 font-mono font-medium">Intra: 73% • Inter: 27%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: INVENTORY & AS 2 VALUATION */}
      {activeTab === 'inventory' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Gross Inventory Carrying Value</div>
              <div className="text-lg font-bold text-slate-100 font-mono mt-1">
                {formatLakhs(inventoryData.totalCarryingValue)}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">Weighted Average Cost Method</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Slow-Moving Stock (&gt;90 Days)</div>
              <div className="text-lg font-bold text-amber-300 font-mono mt-1">
                {formatLakhs(inventoryData.slowMovingValue)}
              </div>
              <div className="text-[11px] text-amber-400 mt-0.5">Configured policy: 25% write-down</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Dead Stock (&gt;180 Days)</div>
              <div className="text-lg font-bold text-rose-400 font-mono mt-1">
                {formatLakhs(inventoryData.deadStockValue)}
              </div>
              <div className="text-[11px] text-rose-400 mt-0.5">Configured policy: 60% write-down</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">AS 2 Required Provision Write-down</div>
              <div className="text-lg font-bold text-rose-300 font-mono mt-1">
                -{formatINR(inventoryData.computedProvision)}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">Charged to P&L Expenses</div>
            </div>
          </div>

          {/* AS 2 Lower of Cost or NRV Register */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">
                  AS 2 / Ind AS 2 Inventory Valuation & Provision Schedule
                </h3>
                <p className="text-[11px] text-slate-400">
                  Valued at Lower of Cost or Net Realisable Value (NRV), with automated aging bucket write-downs.
                </p>
              </div>
              <span className="text-[11px] font-mono bg-indigo-500/10 text-indigo-300 px-2.5 py-1 rounded-md border border-indigo-500/20">
                Net Balance Sheet Value: {formatLakhs(inventoryData.netInventoryValue)}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">SKU / Item Name</th>
                    <th className="py-3 px-4">Stock Qty</th>
                    <th className="py-3 px-4">Cost (W.Avg)</th>
                    <th className="py-3 px-4">NRV / Unit</th>
                    <th className="py-3 px-4">Carrying Cost</th>
                    <th className="py-3 px-4">Days Idle</th>
                    <th className="py-3 px-4">Classification</th>
                    <th className="py-3 px-4 text-right">Provision Required</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                  {inventoryData.evaluatedItems.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/40">
                      <td className="py-3 px-4">
                        <div className="font-sans font-medium text-slate-100">{item.name}</div>
                        <div className="text-[10px] text-slate-400">{item.sku} • {item.category}</div>
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-200">
                        {item.currentStock} {item.uom}
                      </td>
                      <td className="py-3 px-4 text-slate-300">{formatINR(item.weightedAvgCost)}</td>
                      <td className="py-3 px-4">
                        <span className={item.nrvUnit < item.weightedAvgCost ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                          {formatINR(item.nrvUnit)}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-100">{formatINR(item.costValue)}</td>
                      <td className="py-3 px-4">
                        <span className={item.daysSinceLastSale > 180 ? 'text-rose-400 font-bold' : item.daysSinceLastSale > 90 ? 'text-amber-400' : 'text-slate-300'}>
                          {item.daysSinceLastSale} d
                        </span>
                      </td>
                      <td className="py-3 px-4 font-sans">
                        {item.evaluatedCategory === 'DEAD_STOCK' ? (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                            Dead Stock
                          </span>
                        ) : item.evaluatedCategory === 'SLOW_MOVING' ? (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            Slow Moving
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Active Normal
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-rose-400">
                        {item.provisionAmount > 0 ? `-${formatINR(item.provisionAmount)}` : '₹0'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CUSTOMER & DSO ANALYTICS */}
      {activeTab === 'customer' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* DSO 6-Month Trend */}
            <div className="bg-slate-900/90 border border-slate-800 p-5 rounded-xl">
              <h3 className="font-semibold text-slate-100 text-sm">Days Sales Outstanding (DSO) Trend</h3>
              <p className="text-[11px] text-slate-400 mb-3">Target &lt; 45 days collection cycle</p>
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dsoData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="month" stroke="#64748b" tick={{ fontSize: 11 }} />
                    <YAxis stroke="#64748b" domain={[30, 60]} tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                      formatter={(v: any) => [`${v} Days`, 'DSO']}
                    />
                    <Line type="monotone" dataKey="dso" stroke="#6366f1" strokeWidth={3} dot={{ r: 4, fill: '#6366f1' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Credit Limit vs Exposure Alert */}
            <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 p-5 rounded-xl">
              <h3 className="font-semibold text-slate-100 text-sm">Credit Limit vs Current Exposure</h3>
              <p className="text-[11px] text-slate-400 mb-3">Monitoring credit breach risks & overdue collections</p>

              <div className="space-y-3">
                {customers.map((cust) => {
                  const utilizationPct = Math.min(100, Math.round((cust.currentOutstanding / cust.creditLimit) * 100));
                  const isHighRisk = cust.disputedAmount > 0 || utilizationPct > 85;

                  return (
                    <div key={cust.id} className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                      <div className="flex items-center justify-between text-xs">
                        <div className="font-semibold text-slate-200 flex items-center gap-2">
                          <span>{cust.name}</span>
                          {cust.disputedAmount > 0 && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-medium">
                              Disputed (₹{cust.disputedAmount / 1000}k)
                            </span>
                          )}
                        </div>
                        <div className="font-mono text-slate-200">
                          {formatINR(cust.currentOutstanding)} / {formatINR(cust.creditLimit)}
                        </div>
                      </div>

                      <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            utilizationPct > 85 ? 'bg-rose-500' : utilizationPct > 60 ? 'bg-amber-500' : 'bg-indigo-500'
                          }`}
                          style={{ width: `${utilizationPct}%` }}
                        ></div>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1 font-mono">
                        <span>GSTIN: {cust.gstin} ({cust.stateName})</span>
                        <span>Credit Term: {cust.creditPeriodDays} Days • Utilization: {utilizationPct}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: GL PIVOT BUILDER */}
      {activeTab === 'report_builder' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">Ad-Hoc General Ledger Pivot Report</h3>
              <p className="text-xs text-slate-400">
                Multi-dimensional pivot on posted GL entries sliced by Cost Center, Account Group, and Party.
              </p>
            </div>
            <button className="flex items-center gap-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg cursor-pointer">
              <Download className="w-3.5 h-3.5" />
              <span>Export Pivot to Excel (XLSX)</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <label className="text-[11px] text-slate-400 font-semibold block mb-1">Row Dimension</label>
              <select className="w-full bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded p-1.5 focus:outline-none">
                <option>Schedule III Sub-Group</option>
                <option>Customer / Vendor Party</option>
                <option>Account Code</option>
              </select>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <label className="text-[11px] text-slate-400 font-semibold block mb-1">Column Dimension</label>
              <select className="w-full bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded p-1.5 focus:outline-none">
                <option>Financial Quarter (Q1 to Q4)</option>
                <option>Branch / GSTIN State</option>
                <option>Document Type</option>
              </select>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <label className="text-[11px] text-slate-400 font-semibold block mb-1">Metric Measure</label>
              <select className="w-full bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded p-1.5 focus:outline-none">
                <option>Net Movement (Debit - Credit)</option>
                <option>Gross Debit Volume</option>
                <option>Gross Credit Volume</option>
              </select>
            </div>
          </div>

          <div className="border border-slate-800 rounded-lg overflow-hidden font-mono text-xs">
            <table className="w-full text-left">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">Account Group</th>
                  <th className="py-2.5 px-4 text-right">Q1 (₹)</th>
                  <th className="py-2.5 px-4 text-right">Q2 (₹)</th>
                  <th className="py-2.5 px-4 text-right">Q3 (₹)</th>
                  <th className="py-2.5 px-4 text-right">Q4 (₹)</th>
                  <th className="py-2.5 px-4 text-right">Total FY 25-26</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-200">
                <tr>
                  <td className="py-2.5 px-4 font-sans font-medium">Revenue from Operations</td>
                  <td className="py-2.5 px-4 text-right">1,03,00,000</td>
                  <td className="py-2.5 px-4 text-right">1,19,00,000</td>
                  <td className="py-2.5 px-4 text-right">1,34,00,000</td>
                  <td className="py-2.5 px-4 text-right">91,00,000</td>
                  <td className="py-2.5 px-4 text-right font-bold text-indigo-400">4,47,00,000</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans font-medium">Cost of Materials Consumed</td>
                  <td className="py-2.5 px-4 text-right">49,44,000</td>
                  <td className="py-2.5 px-4 text-right">57,12,000</td>
                  <td className="py-2.5 px-4 text-right">64,32,000</td>
                  <td className="py-2.5 px-4 text-right">43,62,000</td>
                  <td className="py-2.5 px-4 text-right font-bold text-slate-100">2,14,50,000</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans font-medium">Employee Benefit Expenses</td>
                  <td className="py-2.5 px-4 text-right">18,55,000</td>
                  <td className="py-2.5 px-4 text-right">18,55,000</td>
                  <td className="py-2.5 px-4 text-right">18,55,000</td>
                  <td className="py-2.5 px-4 text-right">18,55,000</td>
                  <td className="py-2.5 px-4 text-right font-bold text-slate-100">74,20,000</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-sans font-medium">Operating Other Expenses</td>
                  <td className="py-2.5 px-4 text-right">16,25,000</td>
                  <td className="py-2.5 px-4 text-right">17,40,000</td>
                  <td className="py-2.5 px-4 text-right">19,10,000</td>
                  <td className="py-2.5 px-4 text-right">13,90,000</td>
                  <td className="py-2.5 px-4 text-right font-bold text-slate-100">66,65,000</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
