import React, { useState } from 'react';
import {
  Package,
  ArrowRightLeft,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  TrendingDown,
  Layers,
  Plus,
  RefreshCw,
} from 'lucide-react';
import { StockItem, StockTransaction, SystemSettings } from '../../types';
import { computeInventoryProvision, formatINR, formatLakhs } from '../../services/accountingEngine';

interface StockViewProps {
  stockItems: StockItem[];
  stockTransactions: StockTransaction[];
  settings: SystemSettings;
  onAddStockAdjustment: (tx: StockTransaction) => void;
}

export const StockView: React.FC<StockViewProps> = ({
  stockItems,
  stockTransactions,
  settings,
  onAddStockAdjustment,
}) => {
  const [activeTab, setActiveTab] = useState<'register' | 'adjustments' | 'valuation' | 'dead_stock' | 'physical_count'>('register');
  const [showAdjustmentModal, setShowAdjustmentModal] = useState(false);

  // Adjustment form state
  const [selectedSkuId, setSelectedSkuId] = useState(stockItems[0]?.id || '');
  const [adjustType, setAdjustType] = useState<'ADJUSTMENT' | 'TRANSFER'>('ADJUSTMENT');
  const [adjustQty, setAdjustQty] = useState(5);
  const [targetLocation, setTargetLocation] = useState('Bengaluru Depot');
  const [adjustReason, setAdjustReason] = useState('Physical audit variance reconciliation');

  const inventoryEval = computeInventoryProvision(stockItems, settings.inventoryProvisionPolicy);

  const handleCreateAdjustment = (e: React.FormEvent) => {
    e.preventDefault();
    const sku = stockItems.find((s) => s.id === selectedSkuId) || stockItems[0];
    const newTx: StockTransaction = {
      id: `ST-${Date.now()}`,
      date: new Date().toISOString().split('T')[0],
      skuId: sku.id,
      skuCode: sku.sku,
      skuName: sku.name,
      type: adjustType,
      quantity: adjustQty,
      unitCost: sku.weightedAvgCost,
      totalValue: adjustQty * sku.weightedAvgCost,
      referenceDoc: `ADJ-2026-${Math.floor(100 + Math.random() * 900)}`,
      location: adjustType === 'TRANSFER' ? `Pune -> ${targetLocation}` : 'Pune Central Plant',
      narration: adjustReason,
    };

    onAddStockAdjustment(newTx);
    setShowAdjustmentModal(false);
  };

  return (
    <div id="stock-module-container" className="space-y-6">
      {/* Header & Sub Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Perpetual Stock Register & Valuation</h2>
            <span className="text-[11px] bg-indigo-500/10 text-indigo-300 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
              AS 2 / Ind AS 2 Compliant
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time perpetual inventory by SKU × Location with automated Weighted-Average costing and NRV write-down testing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAdjustmentModal(true)}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Stock Adjustment / Transfer</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs w-fit">
        <button
          onClick={() => setActiveTab('register')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'register' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Perpetual Stock Ledger
        </button>
        <button
          onClick={() => setActiveTab('adjustments')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'adjustments' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Transfers & Movements ({stockTransactions.length})
        </button>
        <button
          onClick={() => setActiveTab('valuation')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'valuation' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Stock Valuation (Cost vs NRV)
        </button>
        <button
          onClick={() => setActiveTab('dead_stock')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'dead_stock' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Slow & Dead Stock Report
        </button>
        <button
          onClick={() => setActiveTab('physical_count')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'physical_count' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Physical Count Recon
        </button>
      </div>

      {/* TAB 1: PERPETUAL STOCK LEDGER */}
      {activeTab === 'register' && (
        <div className="space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">Real-Time Perpetual Inventory Register</h3>
                <p className="text-[11px] text-slate-400">Current on-hand balances across Multi-Location plants</p>
              </div>
              <div className="text-xs font-mono text-slate-300">
                Total SKUs: <strong className="text-slate-100">{stockItems.length}</strong> • Total Valuation: <strong className="text-indigo-400">{formatLakhs(inventoryEval.netInventoryValue)}</strong>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800 uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">SKU / Description</th>
                    <th className="py-3 px-4">HSN / Tax</th>
                    <th className="py-3 px-4">Costing Method</th>
                    <th className="py-3 px-4 text-right">Unit Cost (₹)</th>
                    <th className="py-3 px-4 text-right">On-Hand Qty</th>
                    <th className="py-3 px-4">Warehouse Locations</th>
                    <th className="py-3 px-4 text-right">Total Carrying Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                  {stockItems.map((item) => {
                    const totalVal = item.currentStock * item.weightedAvgCost;
                    return (
                      <tr key={item.id} className="hover:bg-slate-800/40">
                        <td className="py-3 px-4">
                          <div className="font-sans font-medium text-slate-100">{item.name}</div>
                          <div className="text-[10px] text-slate-400">{item.sku} • {item.category}</div>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          <div>HSN: {item.hsnSac}</div>
                          <div className="text-[10px] text-slate-400">GST: {item.gstRate}%</div>
                        </td>
                        <td className="py-3 px-4 font-sans text-slate-300">
                          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                            {item.costingMethod === 'WEIGHTED_AVG' ? 'Weighted Average' : 'FIFO'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-slate-200">
                          {formatINR(item.weightedAvgCost)}
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-slate-100">
                          {item.currentStock} {item.uom}
                        </td>
                        <td className="py-3 px-4 font-sans text-[11px]">
                          {Object.entries(item.locationStocks).map(([loc, qty]) => (
                            <span key={loc} className="inline-block mr-2 px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300 text-[10px]">
                              {loc}: <strong>{qty}</strong>
                            </span>
                          ))}
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-indigo-300">
                          {formatINR(totalVal)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: MOVEMENTS & TRANSFERS */}
      {activeTab === 'adjustments' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-semibold text-slate-100 text-sm">Stock In / Stock Out Perpetual Movement Journal</h3>
            <span className="text-xs text-slate-400 font-mono">Immutable Movement Audit Trail</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3 px-4">Date / Ref</th>
                  <th className="py-3 px-4">Item Code & Name</th>
                  <th className="py-3 px-4">Transaction Type</th>
                  <th className="py-3 px-4 text-right">Quantity</th>
                  <th className="py-3 px-4 text-right">Unit Cost</th>
                  <th className="py-3 px-4 text-right">Total Movement</th>
                  <th className="py-3 px-4">Location & Narration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300">
                {stockTransactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-200">{tx.referenceDoc}</div>
                      <div className="text-[10px] text-slate-400">{tx.date}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-sans font-medium text-slate-100">{tx.skuName}</div>
                      <div className="text-[10px] text-slate-400">{tx.skuCode}</div>
                    </td>
                    <td className="py-3 px-4 font-sans">
                      {tx.type === 'OUT_SALE' ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold">
                          Dispatched (Sale)
                        </span>
                      ) : tx.type === 'IN_PURCHASE' ? (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                          Goods Receipt (GRN)
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-semibold">
                          {tx.type}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-200">{tx.quantity}</td>
                    <td className="py-3 px-4 text-right text-slate-300">{formatINR(tx.unitCost)}</td>
                    <td className="py-3 px-4 text-right font-bold text-indigo-300">{formatINR(tx.totalValue)}</td>
                    <td className="py-3 px-4 font-sans text-slate-300 text-[11px]">
                      <div className="font-medium text-slate-200">{tx.location}</div>
                      <div className="text-slate-400 text-[10px]">{tx.narration}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: VALUATION (AS 2 / IND AS 2 LOWER OF COST OR NRV) */}
      {activeTab === 'valuation' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30 flex items-start gap-3">
            <Layers className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <h4 className="font-semibold text-indigo-200 text-sm">AS 2 Valuation Rule: Lower of Cost or Net Realisable Value (NRV)</h4>
              <p className="text-slate-300 mt-1 leading-relaxed">
                Inventories are valued on an item-by-item basis. When estimated NRV falls below historical cost (due to obsolescence or slow movement),
                a direct provision is mandated under Indian GAAP & Ind AS 2, charging an impairment to the Profit & Loss statement and reducing Balance Sheet carrying values.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Total Carrying Cost (Before AS 2)</div>
              <div className="text-lg font-bold text-slate-100 font-mono mt-1">
                {formatINR(inventoryEval.totalCarryingValue)}
              </div>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Total Net Realisable Value (NRV)</div>
              <div className="text-lg font-bold text-slate-100 font-mono mt-1">
                {formatINR(inventoryEval.totalNrvValue)}
              </div>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Net Balance Sheet Asset Presentation</div>
              <div className="text-lg font-bold text-emerald-400 font-mono mt-1">
                {formatINR(inventoryEval.netInventoryValue)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: DEAD STOCK & SLOW MOVING */}
      {activeTab === 'dead_stock' && (
        <div className="space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5">
            <h3 className="font-semibold text-slate-100 text-sm mb-1">Aging Breakdown of Inventory Holdings</h3>
            <p className="text-xs text-slate-400 mb-4">
              Configured write-down slabs: &gt;90 days (25% provision) • &gt;180 days (60% provision)
            </p>

            <div className="space-y-3">
              {inventoryEval.evaluatedItems
                .filter((i) => i.evaluatedCategory !== 'ACTIVE')
                .map((item) => (
                  <div key={item.id} className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-100 font-sans">{item.name}</span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                          item.evaluatedCategory === 'DEAD_STOCK' ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {item.evaluatedCategory === 'DEAD_STOCK' ? 'Dead Stock (>180d)' : 'Slow Moving (>90d)'}
                        </span>
                      </div>
                      <div className="text-slate-400 text-[11px] font-mono mt-1">
                        Days Idle: <strong className="text-rose-400">{item.daysSinceLastSale} days</strong> • Stock: {item.currentStock} {item.uom}
                      </div>
                    </div>

                    <div className="text-right font-mono">
                      <div className="text-slate-400 text-[11px]">Carrying Cost: {formatINR(item.costValue)}</div>
                      <div className="text-rose-400 font-bold">Impairment Provision: -{formatINR(item.provisionAmount)}</div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: PHYSICAL COUNT RECONCILIATION */}
      {activeTab === 'physical_count' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4 text-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">Physical Stock Count Reconciliation (Audit Mandate)</h3>
              <p className="text-slate-400 text-[11px]">Quarterly physical stock verification comparison against Perpetual Book Ledger</p>
            </div>
            <button className="bg-slate-800 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-700 cursor-pointer">
              Upload Barcode Count File
            </button>
          </div>

          <div className="border border-slate-800 rounded-lg overflow-hidden font-mono text-[11px]">
            <table className="w-full text-left">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 text-[10px] uppercase">
                <tr>
                  <th className="p-3">SKU</th>
                  <th className="p-3">System Book Stock</th>
                  <th className="p-3">Audited Physical Count</th>
                  <th className="p-3">Variance</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-200">
                <tr>
                  <td className="p-3 font-sans">Industrial Controller Unit A400</td>
                  <td className="p-3 font-bold">140 NOS</td>
                  <td className="p-3 font-bold text-emerald-400">140 NOS</td>
                  <td className="p-3 text-emerald-400">0 (Nil)</td>
                  <td className="p-3 font-sans"><span className="text-emerald-400">Reconciled</span></td>
                </tr>
                <tr>
                  <td className="p-3 font-sans">High-Torque Servo Actuator 90Nm</td>
                  <td className="p-3 font-bold">85 NOS</td>
                  <td className="p-3 font-bold text-emerald-400">85 NOS</td>
                  <td className="p-3 text-emerald-400">0 (Nil)</td>
                  <td className="p-3 font-sans"><span className="text-emerald-400">Reconciled</span></td>
                </tr>
                <tr>
                  <td className="p-3 font-sans">Thermoplastic Synthetic Resin Grade 5</td>
                  <td className="p-3 font-bold">2,400 KGS</td>
                  <td className="p-3 font-bold text-amber-400">2,392 KGS</td>
                  <td className="p-3 text-amber-400">-8 KGS (Evaporation/Handling)</td>
                  <td className="p-3 font-sans"><span className="text-amber-400">Normal Variance &lt; 0.5%</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* MODAL: STOCK ADJUSTMENT */}
      {showAdjustmentModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm">Post Stock Adjustment / Transfer</h3>
              <button onClick={() => setShowAdjustmentModal(false)} className="text-slate-400 cursor-pointer">✕</button>
            </div>

            <form onSubmit={handleCreateAdjustment} className="space-y-3">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Select SKU</label>
                <select
                  value={selectedSkuId}
                  onChange={(e) => setSelectedSkuId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  {stockItems.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.sku} - Stock: {s.currentStock} {s.uom})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Type</label>
                  <select
                    value={adjustType}
                    onChange={(e) => setAdjustType(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="ADJUSTMENT">Stock Adjustment</option>
                    <option value="TRANSFER">Inter-Location Transfer</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Quantity</label>
                  <input
                    type="number"
                    value={adjustQty}
                    onChange={(e) => setAdjustQty(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Narration / Approval Justification</label>
                <input
                  type="text"
                  value={adjustReason}
                  onChange={(e) => setAdjustReason(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAdjustmentModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold cursor-pointer"
                >
                  Commit Movement
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
