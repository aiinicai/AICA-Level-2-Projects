import React, { useState } from 'react';
import { Boxes, Package, Download } from 'lucide-react';
import { getDb } from '../../core/storage';
import { InventoryBalance } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { formatAED, round2 } from '../../core/currency';
import { BUSINESS_UNITS } from '../../data/businessUnits';

interface InventoryPageProps {
  onNavigate: (route: string) => void;
}

export const InventoryPage: React.FC<InventoryPageProps> = () => {
  const db = getDb();
  const [selectedBU, setSelectedBU] = useState('All');

  const balances = db.inventoryBalances.filter((b) => {
    if (selectedBU !== 'All' && b.businessUnit !== selectedBU) return false;
    return true;
  });

  const totalValuation = balances.reduce(
    (acc, b) => acc + (b.quantityOnHand * b.weightedAvgCost),
    0
  );

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'Total Stock Batches', count: balances.length },
    { id: 'val', label: 'Total Valuation (AED)', count: balances.length, amount: totalValuation, color: 'plum' },
  ];

  const columns: ColumnDef<InventoryBalance>[] = [
    {
      key: 'itemCode',
      header: 'Item Code',
      width: '130px',
      render: (b) => <span className="font-mono font-bold text-[#5B2C83]">{b.itemCode}</span>,
    },
    {
      key: 'description',
      header: 'Item Description',
      render: (b) => {
        const itm = db.items.find((i) => i.code === b.itemCode);
        return (
          <div>
            <span className="font-semibold text-gray-900 block">{itm?.description || b.itemCode}</span>
            <span className="text-[10px] text-gray-400">Class: {itm?.itemClass} &bull; UoM: {itm?.uom}</span>
          </div>
        );
      },
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (b) => <span className="font-semibold text-gray-800">{b.businessUnit}</span>,
    },
    {
      key: 'subInventory',
      header: 'Sub-Inventory',
      width: '120px',
      render: (b) => (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800">
          {b.subInventory}
        </span>
      ),
    },
    {
      key: 'quantityOnHand',
      header: 'On-Hand Qty',
      align: 'right',
      width: '110px',
      render: (b) => <span className="font-mono font-bold text-gray-900">{b.quantityOnHand}</span>,
      exportValue: (b) => b.quantityOnHand,
    },
    {
      key: 'weightedAvgCost',
      header: 'Unit WAC (AED)',
      align: 'right',
      width: '130px',
      render: (b) => <span className="font-mono text-gray-700">{formatAED(b.weightedAvgCost)}</span>,
      exportValue: (b) => b.weightedAvgCost,
    },
    {
      key: 'valuation',
      header: 'Total Value (AED)',
      align: 'right',
      width: '140px',
      render: (b) => (
        <span className="font-mono font-bold text-[#3F1D5C]">
          {formatAED(round2(b.quantityOnHand * b.weightedAvgCost))}
        </span>
      ),
      exportValue: (b) => round2(b.quantityOnHand * b.weightedAvgCost),
    },
    {
      key: 'expiryDate',
      header: 'Expiry Date',
      width: '100px',
    },
  ];

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <Boxes className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Inventory & Stock On-Hand</h1>
            <p className="text-xs text-gray-500">
              Sub-inventory balances, weighted average costing (IAS 2), batch tracking, and pharmaceutical expiry dates.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-gray-600">Business Unit:</label>
          <select
            value={selectedBU}
            onChange={(e) => setSelectedBU(e.target.value)}
            className="bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-xs text-gray-800 font-medium focus:ring-2 focus:ring-[#5B2C83] focus:outline-none shadow-xs"
          >
            <option value="All">All Business Units</option>
            {BUSINESS_UNITS.map((bu) => (
              <option key={bu.code} value={bu.code}>
                {bu.code} &bull; {bu.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <SummaryTiles tiles={summaryTiles} selectedId={null} onSelect={() => {}} />

      <DataTable
        title="Stock On-Hand & Valuation"
        data={balances}
        columns={columns}
        keyField="itemCode"
        filterPlaceholder="Search item code, description, sub-inventory..."
      />
    </div>
  );
};
