import React, { useState } from 'react';
import {
  ShoppingCart,
  Plus,
  Eye,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
  Boxes,
  FileText,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { PurchaseOrder } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';
import { TableFilterBar } from '../../components/TableFilterBar';
import { DocLink } from '../../components/DocLink';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED } from '../../core/currency';
import { getActiveUser, checkMakerPermission, checkCanApprove } from '../../core/auth';
import { useTableFilters } from '../../core/useTableFilters';

interface PurchaseOrdersPageProps {
  onNavigate: (route: string) => void;
}

export const PurchaseOrdersPage: React.FC<PurchaseOrdersPageProps> = ({ onNavigate }) => {
  const db = getDb();
  const currentUser = getActiveUser();
  const orders = db.purchaseOrders || [];

  const makerCheck = checkMakerPermission(currentUser, 'Procurement');

  const {
    filteredData,
    totalCount,
    filteredCount,
    searchQuery,
    setSearchQuery,
    selectedStatus,
    setSelectedStatus,
    selectedBU,
    setSelectedBU,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    selectedCounterparty,
    setSelectedCounterparty,
    activeFilterChips,
    clearAllFilters,
    uniqueBUs,
    uniqueStatuses,
    uniqueCounterparties,
  } = useTableFilters(orders, {
    searchFields: ['number', 'supplierName', 'notes', 'buyerName', 'createdBy'],
    dateField: 'poDate',
    amountField: 'totalAmount',
    statusField: 'status',
    buField: 'businessUnit',
    counterpartyField: 'supplierName',
  });

  const [rejectTarget, setRejectTarget] = useState<PurchaseOrder | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Status Tile Counts
  const pendingCount = orders.filter((p) => p.status === 'Pending Approval').length;
  const approvedCount = orders.filter((p) => p.status === 'Approved').length;
  const receivedCount = orders.filter((p) => p.status === 'Received' || p.status === 'Partially Received').length;
  const draftCount = orders.filter((p) => p.status === 'Draft').length;

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All Purchase Orders', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Approval', count: pendingCount, color: 'amber' },
    { id: 'Approved', label: 'Approved (Open Orders)', count: approvedCount, color: 'emerald' },
    { id: 'Received', label: 'Received / Partially Received', count: receivedCount, color: 'plum' },
    { id: 'Draft', label: 'Drafts', count: draftCount, color: 'slate' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (!id || id === 'all') {
      setSelectedStatus('');
    } else {
      setSelectedStatus(id);
    }
  };

  const handleApprove = (po: PurchaseOrder) => {
    updateDb((state) => {
      const item = state.purchaseOrders.find((p) => p.id === po.id);
      if (item) {
        item.status = 'Approved';
        item.approvedBy = currentUser.userId;
        item.approvedAt = new Date().toISOString();
      }
    });

    addAuditLog({
      entityType: 'PurchaseOrder',
      entityId: po.id,
      action: 'APPROVE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Approved Purchase Order ${po.number} for ${po.supplierName} (AED ${formatAED(po.totalAmount)})`,
    });

    setActionMessage(`Approved Purchase Order ${po.number}. It is now authorized for Receiving and Invoice 3-Way Match.`);
  };

  const handleRejectConfirm = (reason?: string) => {
    if (!rejectTarget) return;

    updateDb((state) => {
      const item = state.purchaseOrders.find((p) => p.id === rejectTarget.id);
      if (item) {
        item.status = 'Rejected';
        item.rejectionReason = reason;
      }
    });

    addAuditLog({
      entityType: 'PurchaseOrder',
      entityId: rejectTarget.id,
      action: 'REJECT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Rejected Purchase Order ${rejectTarget.number}. Reason: ${reason || 'Unspecified'}`,
    });

    setActionMessage(`Rejected Purchase Order ${rejectTarget.number} and returned to Maker.`);
    setRejectTarget(null);
  };

  const columns: ColumnDef<PurchaseOrder>[] = [
    {
      key: 'number',
      header: 'PO Number',
      width: '140px',
      render: (p) => <DocLink number={p.number} showIcon />,
    },
    {
      key: 'supplierName',
      header: 'Supplier / Vendor',
      render: (p) => (
        <div>
          <span className="font-semibold text-gray-900 block truncate">{p.supplierName}</span>
          {p.orderType && (
            <span className="text-[10px] text-gray-400">
              Type: {p.orderType} &bull; Terms: {p.paymentTerms}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (p) => <span className="font-semibold text-gray-800">{p.businessUnit}</span>,
    },
    {
      key: 'date',
      header: 'PO Date',
      width: '100px',
      render: (p) => <span className="font-mono text-gray-600">{p.poDate || p.date}</span>,
    },
    {
      key: 'totalAmount',
      header: 'Committed Total (AED)',
      align: 'right',
      width: '150px',
      render: (p) => <span className="font-mono font-bold text-gray-900">{formatAED(p.totalAmount)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: '140px',
      align: 'center',
      render: (p) => {
        const isApproved = p.status === 'Approved' || p.status === 'Received';
        const isPending = p.status === 'Pending Approval';
        const isRejected = p.status === 'Rejected';
        return (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
              isApproved
                ? 'bg-emerald-100 text-emerald-800'
                : isPending
                ? 'bg-amber-100 text-amber-800'
                : isRejected
                ? 'bg-rose-100 text-rose-800'
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            {p.status}
          </span>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '170px',
      align: 'right',
      render: (p) => {
        const canApproveResult = checkCanApprove(currentUser, p, 'Procurement');
        const isApproved = p.status === 'Approved' || p.status === 'Partially Received';

        return (
          <div className="flex items-center justify-end space-x-1.5">
            {/* If approved and user is Supply Chain Maker (Noah Bennett) -> Create Receipt */}
            {isApproved && (currentUser.userId === 'noah.bennett' || currentUser.role === 'Store Controller' || currentUser.role === 'CFO') && (
              <button
                onClick={() => onNavigate(`#/supply-chain/receiving?action=create&poNumber=${p.number}`)}
                className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold flex items-center space-x-1 cursor-pointer"
                title="Create Goods Receipt Note (GRN)"
              >
                <Boxes className="w-3 h-3" />
                <span>Receive</span>
              </button>
            )}

            {/* If approved and user is Payables Maker (Omar Haddad) -> Create Invoice */}
            {isApproved && (currentUser.userId === 'omar.haddad' || currentUser.role === 'AP Maker' || currentUser.role === 'CFO') && (
              <button
                onClick={() => onNavigate(`#/payables/invoices?action=create&poNumber=${p.number}`)}
                className="px-2 py-1 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded text-[11px] font-semibold flex items-center space-x-1 cursor-pointer"
                title="Create AP Invoice against PO"
              >
                <FileText className="w-3 h-3" />
                <span>Match Invoice</span>
              </button>
            )}

            {/* If pending and user is Approver (Daniel Reed) */}
            {canApproveResult.allowed && (
              <>
                <button
                  onClick={() => handleApprove(p)}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold cursor-pointer"
                  title="Approve Order"
                >
                  Approve
                </button>
                <button
                  onClick={() => setRejectTarget(p)}
                  className="px-2 py-1 border border-rose-200 text-rose-600 hover:bg-rose-50 rounded text-[11px] font-semibold cursor-pointer"
                  title="Reject Order"
                >
                  Reject
                </button>
              </>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Module Access Banner */}
      <ModuleAccessBanner module="Procurement" onNavigate={onNavigate} />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <ShoppingCart className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Purchase Orders Work Area</h1>
            <p className="text-xs text-gray-500">
              Procurement &bull; Maker: Liam Carter &bull; Approver: Daniel Reed (CFO) &bull; Section 2 Specification
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {makerCheck.allowed ? (
            <button
              onClick={() => onNavigate('#/procurement/orders/create')}
              className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Purchase Order</span>
            </button>
          ) : (
            <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-lg text-xs text-gray-500">
              <span>Only Liam Carter (Maker) can create orders</span>
            </div>
          )}
        </div>
      </div>

      {actionMessage && (
        <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between shadow-2xs">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-gray-400 hover:text-gray-600 font-bold ml-2 cursor-pointer"
          >
            &times;
          </button>
        </div>
      )}

      {/* Summary Tiles */}
      <SummaryTiles
        tiles={summaryTiles}
        activeTileId={selectedStatus || 'all'}
        onSelectTile={handleTileSelect}
      />

      {/* Reusable Filter Bar */}
      <TableFilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedBU={selectedBU}
        onBUChange={setSelectedBU}
        buOptions={uniqueBUs}
        selectedStatus={selectedStatus}
        onStatusChange={setSelectedStatus}
        statusOptions={uniqueStatuses}
        selectedCounterparty={selectedCounterparty}
        onCounterpartyChange={setSelectedCounterparty}
        counterpartyOptions={uniqueCounterparties}
        counterpartyLabel="Supplier"
        dateFrom={dateFrom}
        onDateFromChange={setDateFrom}
        dateTo={dateTo}
        onDateToChange={setDateTo}
        activeFilterChips={activeFilterChips}
        onClearAll={clearAllFilters}
        totalRecords={totalCount}
        filteredRecords={filteredCount}
      />

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <DataTable
          data={filteredData}
          columns={columns}
          title="Enterprise Purchase Orders"
          searchPlaceholder="Search orders..."
          emptyMessage="No purchase orders found matching current criteria."
        />
      </div>

      {rejectTarget && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setRejectTarget(null)}
          onConfirm={(reason) => handleRejectConfirm(reason)}
          title={`Reject Purchase Order ${rejectTarget.number}`}
          message="Provide mandatory reason for returning this purchase order to maker (Liam Carter):"
          confirmLabel="Confirm Rejection"
          cancelLabel="Cancel"
          actionType="reject"
          requireComment={true}
        />
      )}
    </div>
  );
};
