import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Plus,
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Send,
  Undo2,
  HelpCircle,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { APInvoice, TransactionStatus } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { RightRail } from '../../components/RightRail';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED } from '../../core/currency';
import { getActiveUser, checkCanApprove } from '../../core/auth';
import { buildAPInvoiceAccounting, postToGL } from '../../core/postingEngine';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { CreateInvoiceModal } from './CreateInvoiceModal';

interface InvoicesPageProps {
  onNavigate: (route: string) => void;
  initialAction?: string;
}

export const InvoicesPage: React.FC<InvoicesPageProps> = ({ onNavigate, initialAction }) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [viewAccountingNumber, setViewAccountingNumber] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(initialAction === 'create');
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [approveTarget, setApproveTarget] = useState<APInvoice | null>(null);
  const [rejectTarget, setRejectTarget] = useState<APInvoice | null>(null);

  // Filter invoices
  const invoices = db.apInvoices.filter((inv) => {
    if (selectedBU !== 'All' && inv.businessUnit !== selectedBU) return false;
    if (statusFilter && inv.status !== statusFilter) return false;
    return true;
  });

  // Summary counts
  const totalCount = db.apInvoices.length;
  const pendingCount = db.apInvoices.filter((i) => i.status === 'Pending Approval').length;
  const postedCount = db.apInvoices.filter((i) => i.status === 'Posted' || i.status === 'Approved').length;
  const draftCount = db.apInvoices.filter((i) => i.status === 'Draft').length;
  const rejectedCount = db.apInvoices.filter((i) => i.status === 'Rejected').length;
  const holdsCount = db.apInvoices.filter((i) => i.holds?.length > 0).length;

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All Invoices', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Approval', count: pendingCount, statusKey: 'Pending Approval', color: 'amber' },
    { id: 'Posted', label: 'Approved & Posted', count: postedCount, statusKey: 'Posted', color: 'emerald' },
    { id: 'Draft', label: 'Drafts', count: draftCount, statusKey: 'Draft', color: 'slate' },
    { id: 'Rejected', label: 'Rejected', count: rejectedCount, statusKey: 'Rejected', color: 'rose' },
    { id: 'holds', label: 'On System Hold', count: holdsCount, color: 'rose' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (!id || id === 'all') {
      setStatusFilter(null);
    } else if (id === 'holds') {
      // Filter by holds
      setStatusFilter(null);
    } else {
      setStatusFilter(id);
    }
  };

  // Approve invoice flow
  const handleApproveConfirm = () => {
    if (!approveTarget) return;

    const check = checkCanApprove(currentUser, approveTarget);
    if (!check.allowed) {
      setActionMessage(`Approval Denied: ${check.reason}`);
      setApproveTarget(null);
      return;
    }

    // Run Create Accounting & Post to GL
    const subEntry = buildAPInvoiceAccounting(approveTarget);
    const postRes = postToGL(subEntry, {
      createdBy: approveTarget.createdBy,
      approvedBy: currentUser.userId,
      category: 'Purchase Invoices',
    });

    if (postRes.success && postRes.journal) {
      updateDb((state) => {
        const inv = state.apInvoices.find((i) => i.id === approveTarget.id);
        if (inv) {
          inv.status = 'Posted';
          inv.approvedBy = currentUser.userId;
          inv.approvedAt = new Date().toISOString();
          inv.postedAt = new Date().toISOString();
          inv.glJournalId = postRes.journal!.id;
        }

        // If capital invoice, add line to Fixed Assets Additions Queue!
        const hasCapital = approveTarget.lines.some((l) => l.isCapital);
        if (hasCapital) {
          approveTarget.lines.forEach((line) => {
            if (line.isCapital) {
              state.assetSourceLines.push({
                id: `SRC-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
                apInvoiceId: approveTarget.id,
                apInvoiceNumber: approveTarget.number,
                lineNumber: line.lineNumber,
                poNumber: line.poNumber,
                businessUnit: approveTarget.businessUnit,
                description: line.description,
                cost: line.lineAmount,
                invoiceDate: approveTarget.invoiceDate,
                inServiceDate: approveTarget.invoiceDate,
                categoryName: line.assetCategory || 'Medical Equipment',
                units: line.quantity || 1,
                department: line.department || 'Clinical',
                status: 'Incomplete',
                comments: 'Transferred from approved AP Capital Invoice',
              });
            }
          });
        }
      });

      addAuditLog({
        entityType: 'APInvoice',
        entityId: approveTarget.id,
        action: 'APPROVE',
        userId: currentUser.userId,
        userName: currentUser.name,
        comments: `Approved AP invoice ${approveTarget.number} and posted GL journal ${postRes.journal.number}`,
      });

      setActionMessage(
        `Successfully approved invoice ${approveTarget.number}. Generated GL Journal ${postRes.journal.number} (Dr GRNI/Expense/Clearing, Cr 2000 Trade Payables).`
      );
    } else {
      updateDb((state) => {
        const inv = state.apInvoices.find((i) => i.id === approveTarget.id);
        if (inv) {
          inv.status = 'Approved - Accounting Error';
        }
      });
      setActionMessage(`Accounting Error: ${postRes.errors?.join('; ')}`);
    }

    setApproveTarget(null);
  };

  // Reject invoice flow
  const handleRejectConfirm = (reason?: string) => {
    if (!rejectTarget) return;

    updateDb((state) => {
      const inv = state.apInvoices.find((i) => i.id === rejectTarget.id);
      if (inv) {
        inv.status = 'Rejected';
        inv.rejectionReason = reason;
      }
    });

    addAuditLog({
      entityType: 'APInvoice',
      entityId: rejectTarget.id,
      action: 'REJECT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Rejected AP invoice ${rejectTarget.number}. Reason: ${reason}`,
    });

    setActionMessage(`Invoice ${rejectTarget.number} rejected and returned to maker with reason: "${reason}".`);
    setRejectTarget(null);
  };

  const columns: ColumnDef<APInvoice>[] = [
    {
      key: 'number',
      header: 'Invoice No.',
      width: '150px',
      render: (i) => <span className="font-mono font-bold text-[#5B2C83]">{i.number}</span>,
    },
    {
      key: 'supplierName',
      header: 'Supplier / Payee',
      render: (i) => (
        <div>
          <span className="font-semibold text-gray-900 block truncate">{i.supplierName}</span>
          <span className="text-[10px] text-gray-400 font-mono">Site: {i.supplierSite || 'HQ'}</span>
        </div>
      ),
    },
    {
      key: 'supplierInvoiceNumber',
      header: 'Supplier Ref',
      width: '130px',
      render: (i) => <span className="font-mono text-gray-600">{i.supplierInvoiceNumber}</span>,
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (i) => <span className="font-semibold text-gray-800">{i.businessUnit}</span>,
    },
    {
      key: 'invoiceDate',
      header: 'Invoice Date',
      width: '100px',
    },
    {
      key: 'dueDate',
      header: 'Due Date',
      width: '100px',
    },
    {
      key: 'totalAmount',
      header: 'Total Amount (AED)',
      align: 'right',
      width: '140px',
      render: (i) => (
        <span className="font-mono font-semibold text-gray-900">
          {formatAED(i.totalAmount)}
        </span>
      ),
      exportValue: (i) => i.totalAmount,
    },
    {
      key: 'status',
      header: 'Status',
      width: '130px',
      align: 'center',
    },
    {
      key: 'createdBy',
      header: 'Maker / Checker',
      width: '130px',
      render: (i) => (
        <div className="text-[10px]">
          <div>M: <span className="font-medium text-gray-700">{i.createdBy}</span></div>
          {i.approvedBy && <div>C: <span className="font-medium text-emerald-700">{i.approvedBy}</span></div>}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Approval Actions',
      width: '140px',
      align: 'center',
      sortable: false,
      render: (i) => {
        if (i.status === 'Pending Approval') {
          const check = checkCanApprove(currentUser, i);
          return (
            <div className="flex items-center justify-center space-x-1" onClick={(e) => e.stopPropagation()}>
              <button
                disabled={!check.allowed}
                onClick={() => setApproveTarget(i)}
                title={check.allowed ? 'Approve Invoice' : check.reason}
                className="px-2 py-0.5 rounded bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white font-semibold text-[11px] transition-colors"
              >
                Approve
              </button>
              <button
                onClick={() => setRejectTarget(i)}
                title="Reject Invoice"
                className="px-2 py-0.5 rounded bg-rose-600 hover:bg-rose-700 text-white font-semibold text-[11px] transition-colors"
              >
                Reject
              </button>
            </div>
          );
        }
        return <span className="text-gray-400 text-[10px]">—</span>;
      },
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
              <FileSpreadsheet className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">Payables: Invoices</h1>
              <p className="text-xs text-gray-500">
                Manage supplier invoices, 3-way PO matching, approval worklists, and GL accounting.
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
              <span>Create Invoice</span>
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
          title="Payables Invoices"
          data={invoices}
          columns={columns}
          keyField="id"
          onNewClick={() => setIsCreateOpen(true)}
          newButtonLabel="Create Invoice"
          onViewAccounting={(i) => setViewAccountingNumber(i.number)}
          onRowClick={(i) => setViewAccountingNumber(i.number)}
          filterPlaceholder="Search invoice number, supplier, reference..."
        />
      </div>

      {/* Right Rail */}
      <RightRail
        tasks={[
          { label: 'Create Standard Invoice', onClick: () => setIsCreateOpen(true) },
          { label: 'Create Payment Run', onClick: () => onNavigate('#/payables/payments?action=create') },
          { label: 'Manage Suppliers', onClick: () => onNavigate('#/payables/suppliers') },
          { label: 'Payables Aging Report', onClick: () => onNavigate('#/reports/payables-aging') },
          { label: 'AP to GL Reconciliation', onClick: () => onNavigate('#/reports/reconciliations') },
        ]}
      />

      {/* Create Invoice Modal */}
      {isCreateOpen && (
        <CreateInvoiceModal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onCreated={(inv) => {
            setIsCreateOpen(false);
            setActionMessage(`Invoice ${inv.number} created with status '${inv.status}'.`);
          }}
        />
      )}

      {/* View Accounting Lines Modal */}
      {viewAccountingNumber && (
        <ViewAccountingModal
          isOpen={Boolean(viewAccountingNumber)}
          onClose={() => setViewAccountingNumber(null)}
          documentNumber={viewAccountingNumber}
          sourceModule="Payables"
          onNavigateToJournal={() => onNavigate('#/general-accounting/journals')}
        />
      )}

      {/* Approve Confirmation Dialog */}
      {approveTarget && (
        <ConfirmDialog
          isOpen={Boolean(approveTarget)}
          onClose={() => setApproveTarget(null)}
          onConfirm={handleApproveConfirm}
          title={`Approve Invoice ${approveTarget.number}?`}
          message={`Are you sure you want to approve this invoice from ${approveTarget.supplierName} for AED ${formatAED(
            approveTarget.totalAmount
          )}? Approving will immediately generate subledger entries and post to the General Ledger.`}
          type="approve"
          confirmLabel="Approve & Post to GL"
        />
      )}

      {/* Reject Confirmation Dialog */}
      {rejectTarget && (
        <ConfirmDialog
          isOpen={Boolean(rejectTarget)}
          onClose={() => setRejectTarget(null)}
          onConfirm={handleRejectConfirm}
          title={`Reject Invoice ${rejectTarget.number}`}
          message="Enter a mandatory rejection justification to return this item to the Maker."
          type="reject"
          confirmLabel="Reject Invoice"
          requireComment={true}
          commentPlaceholder="Reason for rejection (e.g. TRN mismatch, incorrect price, missing delivery receipt)..."
        />
      )}
    </div>
  );
};
