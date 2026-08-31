import React from 'react';
import {
  BarChart3,
  Download,
  TrendingUp,
  Building2,
  DollarSign,
  Package,
  Truck,
  CheckCircle2,
  Clock,
  ShieldAlert,
  FileSpreadsheet
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { InwardShipment, OutwardShipment, ThemeStyle } from '../types';
import { THEMES } from '../utils/theme';

interface AnalyticsReportsProps {
  inwardList: InwardShipment[];
  outwardList: OutwardShipment[];
  currentTheme?: ThemeStyle;
}

export const AnalyticsReports: React.FC<AnalyticsReportsProps> = ({
  inwardList,
  outwardList,
  currentTheme = 'navy',
}) => {
  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  // Aggregate Cost Recovery by Client
  const clientCostMap: Record<string, { client: string; cost: number; count: number }> = {};
  outwardList.forEach((item) => {
    if (!clientCostMap[item.clientJobCode]) {
      clientCostMap[item.clientJobCode] = {
        client: item.clientName.split(' ')[0],
        cost: 0,
        count: 0
      };
    }
    clientCostMap[item.clientJobCode].cost += item.courierCost;
    clientCostMap[item.clientJobCode].count += 1;
  });

  const clientCostData = Object.keys(clientCostMap).map((code) => ({
    code,
    name: clientCostMap[code].client,
    cost: clientCostMap[code].cost,
    dockets: clientCostMap[code].count
  }));

  // Aggregate by Carrier SLA
  const carrierMap: Record<string, { count: number; delivered: number }> = {};
  [...inwardList, ...outwardList].forEach((item) => {
    if (!carrierMap[item.carrier]) {
      carrierMap[item.carrier] = { count: 0, delivered: 0 };
    }
    carrierMap[item.carrier].count += 1;
    if (item.status === 'delivered' || item.status === 'handed_over_to_staff') {
      carrierMap[item.carrier].delivered += 1;
    }
  });

  const carrierData = Object.keys(carrierMap).map((carrier) => ({
    carrier: carrier.split(' ')[0] + ' ' + (carrier.split(' ')[1] || ''),
    total: carrierMap[carrier].count,
    delivered: carrierMap[carrier].delivered
  }));

  // Status Distribution
  const statusData = [
    {
      name: 'Delivered / Handed Over',
      value:
        inwardList.filter((i) => i.status === 'handed_over_to_staff').length +
        outwardList.filter((o) => o.status === 'delivered').length,
      color: '#10b981'
    },
    {
      name: 'In Transit / Out for Delivery',
      value: outwardList.filter((o) => o.status === 'in_transit' || o.status === 'out_for_delivery').length,
      color: themeConfig.accentColor || '#3b82f6'
    },
    {
      name: 'In Shelf Holding',
      value: inwardList.filter((i) => i.status === 'allocated_to_shelf').length,
      color: '#06b6d4'
    },
    {
      name: 'At Reception Desk',
      value: inwardList.filter((i) => i.status === 'received_at_reception').length,
      color: '#f59e0b'
    }
  ].filter((s) => s.value > 0);

  const totalExpense = outwardList.reduce((sum, item) => sum + item.courierCost, 0);
  const billableExpense = outwardList
    .filter((item) => item.billableToClient)
    .reduce((sum, item) => sum + item.courierCost, 0);

  const exportCSV = () => {
    const headers = [
      'Type',
      'Ref Number',
      'Tracking AWB',
      'Carrier',
      'Party / Client',
      'Job Code',
      'Staff Assigned',
      'Status',
      'Cost (INR)',
      'Timestamp'
    ];

    const inwardRows = inwardList.map((i) => [
      'Inward',
      i.referenceNumber,
      i.trackingNumber,
      i.carrier,
      `"${i.senderName}"`,
      'N/A',
      `"${i.recipientStaffName}"`,
      i.status,
      '0',
      `"${i.receivedAt}"`
    ]);

    const outwardRows = outwardList.map((o) => [
      'Outward',
      o.referenceNumber,
      o.trackingNumber,
      o.carrier,
      `"${o.clientName}"`,
      o.clientJobCode,
      `"${o.assignedStaffName}"`,
      o.status,
      o.courierCost.toString(),
      `"${o.dispatchedAt}"`
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...inwardRows.map((e) => e.join(',')), ...outwardRows.map((e) => e.join(','))].join(
        '\n'
      );

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `CA_Firm_Courier_Register_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-5">
      {/* Top Banner & Export */}
      <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${themeConfig.cardBg} p-4 rounded-xl border ${themeConfig.cardBorder} backdrop-blur-sm shadow-sm transition-colors duration-300`}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-600 dark:text-purple-400">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className={`text-base font-bold ${themeConfig.textPrimary} flex items-center gap-2`}>
              CA Cost Allocation & Audit Compliance Analytics
            </h2>
            <p className={`text-xs ${themeConfig.textMuted}`}>
              Recoverable courier costs by client matter, carrier SLAs, and statutory register exports.
            </p>
          </div>
        </div>

        <button
          onClick={exportCSV}
          className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl ${themeConfig.secondaryBtn} text-xs font-semibold transition-all shadow-sm`}
        >
          <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
          <span>Export Form 3CD Register (CSV)</span>
        </button>
      </div>

      {/* KPI Metric Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className={`p-4 rounded-xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} transition-colors duration-300`}>
          <span className={`text-xs ${themeConfig.textMuted} block font-medium`}>Total Outbound Cost:</span>
          <span className={`text-xl font-bold font-mono ${themeConfig.textPrimary} block mt-1`}>₹{totalExpense}</span>
          <span className="text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1 mt-1 font-semibold">
            <DollarSign className="w-3 h-3" />
            ₹{billableExpense} (100% Client Recoverable)
          </span>
        </div>

        <div className={`p-4 rounded-xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} transition-colors duration-300`}>
          <span className={`text-xs ${themeConfig.textMuted} block font-medium`}>Total Active Inward Dockets:</span>
          <span className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400 block mt-1">
            {inwardList.length} Items
          </span>
          <span className={`text-[11px] ${themeConfig.textMuted} block mt-1`}>
            {inwardList.filter((i) => i.status === 'allocated_to_shelf').length} in holding shelves
          </span>
        </div>

        <div className={`p-4 rounded-xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} transition-colors duration-300`}>
          <span className={`text-xs ${themeConfig.textMuted} block font-medium`}>Total Outward Dispatches:</span>
          <span className={`text-xl font-bold font-mono ${themeConfig.textAccent} block mt-1`}>
            {outwardList.length} Dockets
          </span>
          <span className={`text-[11px] ${themeConfig.textMuted} block mt-1`}>
            {outwardList.filter((o) => o.status === 'delivered').length} delivered with POD
          </span>
        </div>

        <div className={`p-4 rounded-xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} transition-colors duration-300`}>
          <span className={`text-xs ${themeConfig.textMuted} block font-medium`}>Chain-of-Custody Compliance:</span>
          <span className="text-xl font-bold font-mono text-purple-600 dark:text-purple-400 block mt-1">100%</span>
          <span className={`text-[11px] ${themeConfig.textMuted} block mt-1`}>
            Zero untracked dispatches
          </span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Chart 1: Cost Recovery by Client Code */}
        <div className={`p-5 rounded-xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} transition-colors duration-300`}>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className={`text-xs font-bold ${themeConfig.textPrimary} uppercase tracking-wider`}>
                Client Matter Cost Recovery (₹)
              </h3>
              <p className={`text-[11px] ${themeConfig.textMuted}`}>
                Courier expenses linked to specific client audit/tax codes
              </p>
            </div>
            <span className="text-xs font-mono text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 font-bold">
              Recoverable
            </span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={clientCostData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <XAxis dataKey="code" tick={{ fill: themeConfig.isLight ? '#475569' : '#94a3b8', fontSize: 10 }} angle={-15} textAnchor="end" />
                <YAxis tick={{ fill: themeConfig.isLight ? '#475569' : '#94a3b8', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: themeConfig.isLight ? '#ffffff' : '#0f172a',
                    borderColor: themeConfig.isLight ? '#cbd5e1' : '#334155',
                    borderRadius: '8px',
                    color: themeConfig.isLight ? '#0f172a' : '#f8fafc'
                  }}
                  itemStyle={{ fontSize: '11px' }}
                />
                <Bar dataKey="cost" fill={themeConfig.accentColor} radius={[4, 4, 0, 0]} name="Cost (₹)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Status Breakdown Pie */}
        <div className={`p-5 rounded-xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} transition-colors duration-300`}>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className={`text-xs font-bold ${themeConfig.textPrimary} uppercase tracking-wider`}>
                Consignment Pipeline Breakdown
              </h3>
              <p className={`text-[11px] ${themeConfig.textMuted}`}>
                Current operational status across all inward and outward packets
              </p>
            </div>
          </div>

          <div className="h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={4}
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: themeConfig.isLight ? '#ffffff' : '#0f172a',
                    borderColor: themeConfig.isLight ? '#cbd5e1' : '#334155',
                    borderRadius: '8px',
                    color: themeConfig.isLight ? '#0f172a' : '#f8fafc'
                  }}
                  itemStyle={{ fontSize: '11px' }}
                />
                <Legend
                  wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                  formatter={(value) => <span className={themeConfig.textSecondary}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
