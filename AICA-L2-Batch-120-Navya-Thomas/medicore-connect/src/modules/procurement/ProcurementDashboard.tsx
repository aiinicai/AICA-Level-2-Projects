import React, { useState } from 'react';
import {
  ShoppingCart,
  Boxes,
  FileSpreadsheet,
  Clock,
  TrendingUp,
  Building2,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  Plus,
} from 'lucide-react';
import { getDb } from '../../core/storage';
import { formatAED } from '../../core/currency';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';
import { DocLink } from '../../components/DocLink';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

interface ProcurementDashboardProps {
  onNavigate: (route: string) => void;
}

const PLUM_CHART_COLORS = ['#5B2C83', '#E8A317', '#059669', '#DC2626', '#844db3', '#D97706'];

export const ProcurementDashboard: React.FC<ProcurementDashboardProps> = ({ onNavigate }) => {
  const db = getDb();
  const [selectedBU, setSelectedBU] = useState<string>('All');

  const orders = db.purchaseOrders?.filter(
    (p) => selectedBU === 'All' || p.businessUnit === selectedBU
  ) || [];
  const requisitions = db.requisitions?.filter(
    (r) => selectedBU === 'All' || r.businessUnit === selectedBU
  ) || [];

  // Key KPI calculations
  const openPOs = orders.filter(
    (p) => p.status === 'Approved' || p.status === 'Partially Received'
  );
  const totalCommittedAED = orders.reduce((sum, p) => sum + (p.totalAmount || 0), 0);
  const pendingReqsCount = requisitions.filter((r) => r.status === 'Pending Approval').length;

  // GRNI Balance from Receipts
  const receipts = db.receipts || [];
  const uninvoicedReceiptLines = receipts.reduce((sum, r) => {
    return sum + (r.lines || []).reduce((lSum, l) => lSum + (l.lineAmount || 0), 0);
  }, 0);

  // Spend by Category
  const categorySpendMap: Record<string, number> = {};
  orders.forEach((po) => {
    (po.lines || []).forEach((line) => {
      const cat = line.itemClass || (line.isCapital ? 'Capital Asset' : 'Pharmaceutical');
      categorySpendMap[cat] = (categorySpendMap[cat] || 0) + (line.lineAmount || 0);
    });
  });

  const categorySpendData = Object.entries(categorySpendMap).map(([name, value]) => ({
    name,
    value,
  }));

  // Top 5 Suppliers by Spend
  const supplierSpendMap: Record<string, number> = {};
  orders.forEach((po) => {
    supplierSpendMap[po.supplierName] = (supplierSpendMap[po.supplierName] || 0) + (po.totalAmount || 0);
  });

  const topSuppliersData = Object.entries(supplierSpendMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([supplier, amount]) => ({
      supplier: supplier.length > 20 ? supplier.slice(0, 18) + '...' : supplier,
      amount,
    }));

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Module Access Banner */}
      <ModuleAccessBanner module="Procurement" onNavigate={onNavigate} />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <ShoppingCart className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              Procurement & Sourcing Dashboard
            </h1>
            <p className="text-xs text-gray-500">
              Open PO commitments, GRNI accruals, supplier spend analytics &bull; Section 2 Specification
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => onNavigate('#/procurement/requisitions/create')}
            className="px-3 py-1.5 border border-plum-300 bg-white text-[#5B2C83] hover:bg-plum-50 rounded-lg text-xs font-semibold shadow-2xs flex items-center space-x-1 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Requisition</span>
          </button>
          <button
            onClick={() => onNavigate('#/procurement/orders/create')}
            className="px-3.5 py-1.5 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Purchase Order</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-white rounded-xl border border-gray-200 shadow-2xs">
          <span className="text-[10px] text-gray-400 uppercase font-bold tracking-wider block">
            Open PO Commitments
          </span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-[#5B2C83]">{openPOs.length}</span>
            <span className="text-xs text-gray-500 font-mono">
              {formatAED(openPOs.reduce((s, p) => s + p.totalAmount, 0))}
            </span>
          </div>
          <span className="text-[11px] text-gray-400 mt-1 block">Active approved orders awaiting delivery</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-gray-200 shadow-2xs">
          <span className="text-[10px] text-gray-400 uppercase font-bold tracking-wider block">
            Requisitions Awaiting Approval
          </span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-amber-600">{pendingReqsCount}</span>
            <button
              onClick={() => onNavigate('#/procurement/requisitions?status=Pending+Approval')}
              className="text-xs text-[#5B2C83] font-semibold hover:underline"
            >
              Review Queue &rarr;
            </button>
          </div>
          <span className="text-[11px] text-gray-400 mt-1 block">Maker submissions pending CFO action</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-gray-200 shadow-2xs">
          <span className="text-[10px] text-gray-400 uppercase font-bold tracking-wider block">
            GRNI Accrual Balance (2010)
          </span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-gray-900 font-mono">
              {formatAED(uninvoicedReceiptLines)}
            </span>
          </div>
          <span className="text-[11px] text-gray-400 mt-1 block">Received goods awaiting supplier invoice</span>
        </div>

        <div className="p-4 bg-white rounded-xl border border-gray-200 shadow-2xs">
          <span className="text-[10px] text-gray-400 uppercase font-bold tracking-wider block">
            Total 2026 Procurement
          </span>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-[#5B2C83] font-mono">
              {formatAED(totalCommittedAED)}
            </span>
            <span className="text-xs text-emerald-600 font-bold">{orders.length} POs</span>
          </div>
          <span className="text-[11px] text-gray-400 mt-1 block">Group-wide contracted procurement</span>
        </div>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Spend by Category Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#5B2C83] mb-4">
            Spend Distribution by Item Class
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categorySpendData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }: any) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  labelLine={false}
                >
                  {categorySpendData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PLUM_CHART_COLORS[index % PLUM_CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: any) => formatAED(Number(value))} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Suppliers Bar Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-2xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-[#5B2C83] mb-4">
            Top 5 Suppliers by Contract Volume (AED)
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topSuppliersData} layout="vertical" margin={{ left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <YAxis dataKey="supplier" type="category" width={110} tick={{ fontSize: 10 }} />
                <Tooltip formatter={(value: any) => formatAED(Number(value))} />
                <Bar dataKey="amount" fill="#5B2C83" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Open Orders Table Preview */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-2xs overflow-hidden">
        <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-bold text-xs text-gray-900">Recent Purchase Orders Awaiting Fulfillment</h3>
          <button
            onClick={() => onNavigate('#/procurement/orders')}
            className="text-xs text-[#5B2C83] font-semibold hover:underline flex items-center space-x-1"
          >
            <span>View All Orders</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#FAF7FC] text-gray-600 uppercase font-semibold text-[10px] border-b border-gray-200">
              <tr>
                <th className="py-2.5 px-4">PO Number</th>
                <th className="py-2.5 px-4">Supplier</th>
                <th className="py-2.5 px-4">BU</th>
                <th className="py-2.5 px-4">Date</th>
                <th className="py-2.5 px-4 text-right">Amount (AED)</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orders.slice(0, 6).map((po) => (
                <tr key={po.id} className="hover:bg-gray-50/60">
                  <td className="py-2.5 px-4">
                    <DocLink number={po.number} showIcon />
                  </td>
                  <td className="py-2.5 px-4 font-semibold text-gray-900">{po.supplierName}</td>
                  <td className="py-2.5 px-4 font-semibold text-gray-700">{po.businessUnit}</td>
                  <td className="py-2.5 px-4 font-mono text-gray-600">{po.poDate || po.date}</td>
                  <td className="py-2.5 px-4 text-right font-mono font-bold text-[#5B2C83]">
                    {formatAED(po.totalAmount)}
                  </td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      {po.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
