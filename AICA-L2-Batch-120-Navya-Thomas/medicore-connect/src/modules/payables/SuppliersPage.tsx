import React from 'react';
import { Users, Building2, Plus, Download } from 'lucide-react';
import { getDb } from '../../core/storage';
import { Supplier } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';

interface SuppliersPageProps {
  onNavigate: (route: string) => void;
}

export const SuppliersPage: React.FC<SuppliersPageProps> = () => {
  const db = getDb();

  const columns: ColumnDef<Supplier>[] = [
    {
      key: 'code',
      header: 'Supplier Code',
      width: '130px',
      render: (s) => <span className="font-mono font-bold text-[#5B2C83]">{s.code}</span>,
    },
    {
      key: 'name',
      header: 'Supplier Name',
      render: (s) => (
        <div>
          <span className="font-semibold text-gray-900 block">{s.name}</span>
          <span className="text-[10px] text-gray-500 font-mono">IBAN: {s.bankIban}</span>
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      width: '160px',
      render: (s) => (
        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-100 text-gray-800">
          {s.category}
        </span>
      ),
    },
    {
      key: 'trn',
      header: 'Tax TRN',
      width: '150px',
      render: (s) => <span className="font-mono text-gray-700">{s.trn}</span>,
    },
    {
      key: 'paymentTerms',
      header: 'Payment Terms',
      width: '120px',
    },
    {
      key: 'poNotRequired',
      header: 'PO Policy',
      width: '130px',
      render: (s) => (
        <span className="text-[11px] text-gray-600">
          {s.poNotRequired ? 'Non-PO Allowed (Utility)' : 'PO Required'}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '90px',
      align: 'center',
      render: (s) => (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
          {s.status}
        </span>
      ),
    },
  ];

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
          <Users className="w-5 h-5 text-amber-300" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Suppliers & Creditor Master Directory</h1>
          <p className="text-xs text-gray-500">
            Registered medical equipment distributors, pharmaceuticals, utilities, and facility vendors across the UAE.
          </p>
        </div>
      </div>

      <DataTable
        title="Supplier Master Directory"
        data={db.suppliers}
        columns={columns}
        keyField="id"
        filterPlaceholder="Search supplier name, code, TRN, category..."
      />
    </div>
  );
};
