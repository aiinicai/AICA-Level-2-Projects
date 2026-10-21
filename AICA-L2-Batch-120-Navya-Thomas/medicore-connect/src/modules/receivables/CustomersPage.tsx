import React from 'react';
import { Users, Building2, Download } from 'lucide-react';
import { getDb } from '../../core/storage';
import { Customer } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { formatAED } from '../../core/currency';

interface CustomersPageProps {
  onNavigate: (route: string) => void;
}

export const CustomersPage: React.FC<CustomersPageProps> = () => {
  const db = getDb();

  const columns: ColumnDef<Customer>[] = [
    {
      key: 'code',
      header: 'Customer Code',
      width: '130px',
      render: (c) => <span className="font-mono font-bold text-[#5B2C83]">{c.code}</span>,
    },
    {
      key: 'name',
      header: 'Customer / Insurer Name',
      render: (c) => (
        <div>
          <span className="font-semibold text-gray-900 block">{c.name}</span>
          {c.trn && <span className="text-[10px] text-gray-400 font-mono">TRN: {c.trn}</span>}
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Customer Type',
      width: '130px',
      render: (c) => (
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
            c.type === 'Insurance'
              ? 'bg-plum-50 text-[#5B2C83] border border-plum-200'
              : c.type === 'Corporate'
              ? 'bg-amber-50 text-amber-900 border border-amber-200'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {c.type}
        </span>
      ),
    },
    {
      key: 'creditLimitAED',
      header: 'Credit Limit (AED)',
      align: 'right',
      width: '150px',
      render: (c) => <span className="font-mono font-semibold">{formatAED(c.creditLimitAED)}</span>,
      exportValue: (c) => c.creditLimitAED,
    },
    {
      key: 'currentBalanceAED',
      header: 'Current Open (AED)',
      align: 'right',
      width: '150px',
      render: (c) => <span className="font-mono font-bold text-gray-900">{formatAED(c.currentBalanceAED)}</span>,
      exportValue: (c) => c.currentBalanceAED,
    },
    {
      key: 'paymentTerms',
      header: 'Payment Terms',
      width: '120px',
    },
    {
      key: 'status',
      header: 'Status',
      width: '90px',
      align: 'center',
      render: (c) => (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
          {c.status}
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
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Customer Master Directory</h1>
          <p className="text-xs text-gray-500">
            Registered health insurance networks, corporate healthcare wellness schemes, and patient master accounts.
          </p>
        </div>
      </div>

      <DataTable
        title="Customer Master Directory"
        data={db.customers}
        columns={columns}
        keyField="id"
        filterPlaceholder="Search customer, insurer, corporate name, type..."
      />
    </div>
  );
};
