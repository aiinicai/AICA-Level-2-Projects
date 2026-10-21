import React, { useState } from 'react';
import {
  Receipt,
  Plus,
  Eye,
  CheckCircle,
  XCircle,
  Clock,
  Send,
  AlertCircle,
  CreditCard,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { ARTransaction, TransactionStatus } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { RightRail } from '../../components/RightRail';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED } from '../../core/currency';
import { getActiveUser, checkCanApprove } from '../../core/auth';
import { buildARInvoiceAccounting, postToGL } from '../../core/postingEngine';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { CreateBillingModal } from './CreateBillingModal';
import { CreateReceiptModal } from './CreateReceiptModal';

interface BillingPageProps {
  onNavigate: (route: string) => void;
  initialAction?: string;
}

export const BillingPage: React.FC<BillingPageProps> = ({ onNavigate, initialAction }) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [viewAccountingNumber, setViewAccountingNumber] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(initialAction === 'create');
  const [receiptTarget, setReceiptTarget] = useState<ARTransaction | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [approveTarget, setApproveTarget] = useState<ARTransaction | null>(null);
  const [rejectTarget, setRejectTarget] = useState<ARTransaction | null>(null);

  // Filter AR transactions
  const transactions = db.arTransactions.filter((ar) => {
    if (selectedBU !== 'All' && ar.businessUnit !== selectedBU) return false;
    if (statusFilter && ar.status !== statusFilter) return false;
    return true;
  });

  // Summary counts
  const totalCount = db.arTransactions.length;
  const pendingCount = db.arTransactions.filter((i) => i.status === 'Pending Approval').length;
  const postedCount = db.arTransactions.filter((i) => i.status === 'Posted' || i.status === 'Approved').length;
  const draftCount = db.arTransactions.filter((i) => i.status === 'Draft').length;
  const receiptsCount = db.arReceipts.length;

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All Billings', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Approval', count: pendingCount, statusKey: 'Pending Approval', color: 'amber' },
    { id: 'Posted', label: 'Approved & Posted', count: postedCount, statusKey: 'Posted', color: 'emerald' },
    { id: 'Draft', label: 'Drafts', count: draftCount, statusKey: 'Draft', color: 'slate' },
    { id: 'receipts', label: 'Receipts Applied', count: receiptsCount, color: 'plum' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (!id || id === 'all') {
      setStatusFilter(null);
    } else if (id === 'receipts') {
      onNavigate('#/receivables/receipts');
    } else {
      setStatusFilter(id);
    }
  };

  // Approve AR transaction
  const handleApproveConfirm = () => {
    if (!approveTarget) return;

    const check = checkCanApprove(currentUser, approveTarget);
    if (!check.allowed) {
      setActionMessage(`Approval Denied: ${check.reason}`);
      setApproveTarget(null);
      return;
    }

    const subEntry = buildARInvoiceAccounting(approveTarget);
    const postRes = postToGL(subEntry, {
      createdBy: approveTarget.createdBy,
      approvedBy: currentUser.userId,
      category: 'Sales Invoices',
    });

    if (postRes.success && postRes.journal) {
      updateDb((state) => {
        const ar = state.arTransactions.find((i) => i.id === approveTarget.id);
        if (ar) {
          ar.status = 'Posted';
          ar.approvedBy = currentUser.userId;
          ar.approvedAt = new Date().toISOString();
          ar.postedAt = new Date().toISOString();
          ar.glJournalId = postRes.journal!.id;
        }
      });

      addAuditLog({
        entityType: 'ARTransaction',
        entityId: approveTarget.id,
        action: 'APPROVE',
        userId: currentUser.userId,
        userName: currentUser.name,
        comments: `Approved AR invoice ${approveTarget.number} and posted GL journal ${postRes.journal.number}`,
      });

      setActionMessage(
        `Successfully approved AR claim ${approveTarget.number}. Generated GL Journal ${postRes.journal.number} (Dr AR Control, Cr Revenue & VAT).`
      );
    } else {
      setActionMessage(`Accounting Error: ${postRes.errors?.join('; ')}`);
    }

    setApproveTarget(null);
  };

  const columns: ColumnDef<ARTransaction>[] = [
    {
      key: 'number',
      header: 'Transaction No.',
      width: '150px',
      render: (i) => <span className="font-mono font-bold text-[#5B2C83]">{i.number}</span>,
    },
    {
      key: 'customerName',
      header: 'Customer / Insurer',
      render: (i) => (
        <div>
          <span className="font-semibold text-gray-900 block truncate">{i.customerName}</span>
          <span className="text-[10px] text-gray-400">
            {i.customerType} &bull; {i.claimReference || i.patientName || 'Self-pay'}
          </span>
        </div>
      ),
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (i) => <span className="font-semibold text-gray-800">{i.businessUnit}</span>,
    },
    {
      key: 'transactionDate',
      header: 'Date',
      width: '100px',
    },
    {
      key: 'totalAmount',
      header: 'Net Billed (AED)',
      align: 'right',
      width: '130px',
      render: (i) => (
        <span className="font-mono font-bold text-gray-900">
          {formatAED(i.totalAmount)}
        </span>
      ),
      exportValue: (i) => i.totalAmount,
    },
    {
      key: 'paidAmount',
      header: 'Collected (AED)',
      align: 'right',
      width: '130px',
      render: (i) => (
        <span className="font-mono text-emerald-700 font-semibold">
          {formatAED(i.paidAmount)}
        </span>
      ),
      exportValue: (i) => i.paidAmount,
    },
    {
      key: 'status',
      header: 'Status',
      width: '120px',
      align: 'center',
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '160px',
      align: 'center',
      sortable: false,
      render: (i) => (
        <div className="flex items-center justify-center space-x-1" onClick={(e) => e.stopPropagation()}>
          {i.status === 'Pending Approval' ? (
            <button
              onClick={() => setApproveTarget(i)}
              className="px-2 py-0.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px]"
            >
              Approve
            </button>
          ) : (i.status === 'Posted' || i.status === 'Approved') && (i.totalAmount - (i.paidAmount || 0)) > 0 ? (
            <button
              onClick={() => setReceiptTarget(i)}
              className="px-2 py-0.5 rounded bg-[#5B2C83] hover:bg-[#3F1D5C] text-white font-semibold text-[11px] flex items-center space-x-1"
            >
              <CreditCard className="w-3 h-3" />
              <span>Receive</span>
            </button>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main Work Area */}
      <div className="flex-1 flex flex-col p-6 overflow-y-auto">
        {/* Title Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
              <Receipt className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">Receivables: Billing Work Area</h1>
              <p className="text-xs text-gray-500">
                Patient self-pay billing, insurer electronic claims, and cash collections registers.
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
              <option value="All">All Business Units (Consolidated)</option>
              {BUSINESS_UNITS.map((bu) => (
                <option key={bu.code} value={bu.code}>
                  {bu.code} &bull; {bu.name}
                </option>
              ))}
            </select>

            <button
              onClick={() => setIsCreateOpen(true)}
              className="bg-[#5B2C83] hover:bg-[#3F1D5C] text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Create Transaction</span>
            </button>
          </div>
        </div>

        {actionMessage && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)} className="text-emerald-700 font-bold ml-2">
              &times;
            </button>
          </div>
        )}

        {/* Summary Tiles */}
        <SummaryTiles
          tiles={summaryTiles}
          selectedId={statusFilter}
          onSelect={handleTileSelect}
        />

        {/* Data Table */}
        <DataTable
          title="Receivables Transactions"
          data={transactions}
          columns={columns}
          keyField="id"
          onNewClick={() => setIsCreateOpen(true)}
          newButtonLabel="Create AR Transaction"
          onViewAccounting={(i) => setViewAccountingNumber(i.number)}
          onRowClick={(i) => setViewAccountingNumber(i.number)}
          filterPlaceholder="Search transaction number, patient, customer, claim reference..."
        />
      </div>

      {/* Right Rail */}
      <RightRail
        tasks={[
          { label: 'Create Billing Claim', onClick: () => setIsCreateOpen(true) },
          { label: 'Manage Receipts', onClick: () => onNavigate('#/receivables/receipts') },
          { label: 'Manage Customers', onClick: () => onNavigate('#/receivables/customers') },
          { label: 'Customer Aging Schedule', onClick: () => onNavigate('#/reports/receivables-aging') },
          { label: 'AR to GL Reconciliation', onClick: () => onNavigate('#/reports/reconciliations') },
        ]}
      />

      {/* Create Modal */}
      {isCreateOpen && (
        <CreateBillingModal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onCreated={(ar) => {
            setIsCreateOpen(false);
            setActionMessage(`Billing claim ${ar.number} created in status '${ar.status}'.`);
          }}
        />
      )}

      {/* Create Receipt Modal */}
      {receiptTarget && (
        <CreateReceiptModal
          isOpen={Boolean(receiptTarget)}
          onClose={() => setReceiptTarget(null)}
          transaction={receiptTarget}
          onCreated={(rct) => {
            setReceiptTarget(null);
            setActionMessage(`Payment receipt ${rct.number} posted against claim ${receiptTarget.number}.`);
          }}
        />
      )}

      {/* View Accounting */}
      {viewAccountingNumber && (
        <ViewAccountingModal
          isOpen={Boolean(viewAccountingNumber)}
          onClose={() => setViewAccountingNumber(null)}
          documentNumber={viewAccountingNumber}
          sourceModule="Receivables"
          onNavigateToJournal={() => onNavigate('#/general-accounting/journals')}
        />
      )}

      {/* Approve Confirm */}
      {approveTarget && (
        <ConfirmDialog
          isOpen={Boolean(approveTarget)}
          onClose={() => setApproveTarget(null)}
          onConfirm={handleApproveConfirm}
          title={`Approve AR Invoice ${approveTarget.number}?`}
          message={`Are you sure you want to approve this clinical billing for ${approveTarget.customerName} for AED ${formatAED(
            approveTarget.totalAmount
          )}? This will post subledger journal entries to the General Ledger.`}
          type="approve"
          confirmLabel="Approve & Post to GL"
        />
      )}
    </div>
  );
};
