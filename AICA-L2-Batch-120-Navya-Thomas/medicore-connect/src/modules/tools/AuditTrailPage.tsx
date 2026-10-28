import React, { useState } from 'react';
import { History, Search, Download, Clock } from 'lucide-react';
import { getDb } from '../../core/storage';
import { AuditLog } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';

interface AuditTrailPageProps {
  onNavigate: (route: string) => void;
}

export const AuditTrailPage: React.FC<AuditTrailPageProps> = () => {
  const db = getDb();
  const [selectedEntity, setSelectedEntity] = useState<string>('All');

  const logs = db.auditLogs.filter((l) => {
    if (selectedEntity !== 'All' && l.entityType !== selectedEntity) return false;
    return true;
  });

  const columns: ColumnDef<AuditLog>[] = [
    {
      key: 'timestamp',
      header: 'Timestamp',
      width: '180px',
      render: (l) => <span className="font-mono text-gray-700">{l.timestamp.replace('T', ' ').slice(0, 19)}</span>,
    },
    {
      key: 'action',
      header: 'Action',
      width: '110px',
      render: (l) => {
        let bg = 'bg-gray-100 text-gray-800';
        if (l.action === 'APPROVE' || l.action === 'POST') bg = 'bg-emerald-100 text-emerald-800';
        else if (l.action === 'SUBMIT') bg = 'bg-plum-100 text-[#5B2C83]';
        else if (l.action === 'REJECT' || l.action === 'CANCEL') bg = 'bg-rose-100 text-rose-800';
        else if (l.action === 'REVERSE') bg = 'bg-amber-100 text-amber-800';

        return <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${bg}`}>{l.action}</span>;
      },
    },
    {
      key: 'entityType',
      header: 'Entity',
      width: '140px',
      render: (l) => <span className="font-semibold text-gray-800">{l.entityType}</span>,
    },
    {
      key: 'userName',
      header: 'User / Actor',
      width: '160px',
      render: (l) => (
        <div>
          <span className="font-medium text-gray-900 block">{l.userName}</span>
          <span className="text-[10px] text-gray-400 font-mono">{l.userId}</span>
        </div>
      ),
    },
    {
      key: 'comments',
      header: 'Event Description & Details',
      render: (l) => (
        <div>
          <span className="text-gray-800 font-medium block">{l.comments}</span>
          {l.details && (
            <span className="text-[10px] text-gray-500 font-mono">{JSON.stringify(l.details)}</span>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <History className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Enterprise Audit Trail</h1>
            <p className="text-xs text-gray-500">
              Complete chronological audit logging of all transactional events, maker-checker submissions, approvals, and reversals.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-gray-600">Filter Entity:</label>
          <select
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-xs text-gray-800 font-medium focus:ring-2 focus:ring-[#5B2C83] focus:outline-none"
          >
            <option value="All">All Entities</option>
            <option value="APInvoice">Payables Invoices</option>
            <option value="ARTransaction">Receivables Billings</option>
            <option value="FixedAsset">Fixed Assets</option>
            <option value="GLJournal">General Ledger Journals</option>
            <option value="CashVoucher">Cash Vouchers</option>
            <option value="ICTransaction">Intercompany</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <DataTable
        title="Audit Logs"
        data={logs}
        columns={columns}
        keyField="id"
        filterPlaceholder="Search audit events, comments, user actor..."
      />
    </div>
  );
};
