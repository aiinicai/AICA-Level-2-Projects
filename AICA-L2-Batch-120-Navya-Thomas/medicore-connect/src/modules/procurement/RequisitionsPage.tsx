import React, { useState } from 'react';
import {
  FileText,
  Plus,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Filter,
  ShoppingCart,
  Send,
  Eye,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { Requisition } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';
import { TableFilterBar } from '../../components/TableFilterBar';
import { DocLink } from '../../components/DocLink';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { getActiveUser, checkMakerPermission, checkCanApprove } from '../../core/auth';
import { formatAED } from '../../core/currency';
import { useTableFilters } from '../../core/useTableFilters';

interface RequisitionsPageProps {
  onNavigate: (route: string) => void;
}

export const RequisitionsPage: React.FC<RequisitionsPageProps> = ({ onNavigate }) => {
  const db = getDb();
  const currentUser = getActiveUser();
  const requisitions = db.requisitions || [];

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
    activeFilterChips,
    clearAllFilters,
    uniqueBUs,
    uniqueStatuses,
  } = useTableFilters(requisitions, {
    searchFields: ['number', 'description', 'justification', 'department', 'requesterName', 'createdBy'],
    dateField: 'requisitionDate',
    amountField: 'totalAmount',
    statusField: 'status',
    buField: 'businessUnit',
  });

  const [rejectTarget, setRejectTarget] = useState<Requisition | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Summary Tiles Counts
  const pendingCount = requisitions.filter((r) => r.status === 'Pending Approval').length;
  const approvedCount = requisitions.filter((r) => r.status === 'Approved').length;
  const convertedCount = requisitions.filter(
    (r) => r.status === 'Converted to PO' || r.status === 'Partially Converted'
  ).length;
  const draftCount = requisitions.filter((r) => r.status === 'Draft').length;

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All Requisitions', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Approval', count: pendingCount, color: 'amber' },
    { id: 'Approved', label: 'Approved (Ready for PO)', count: approvedCount, color: 'emerald' },
    { id: 'Converted to PO', label: 'Converted to PO', count: convertedCount, color: 'plum' },
    { id: 'Draft', label: 'Drafts', count: draftCount, color: 'slate' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (!id || id === 'all') {
      setSelectedStatus('');
    } else {
      setSelectedStatus(id);
    }
  };

  // Approve Requisition Handler (Approver: Daniel Reed)
  const handleApprove = (req: Requisition) => {
    updateDb((state) => {
      const item = state.requisitions.find((r) => r.id === req.id);
      if (item) {
        item.status = 'Approved';
        item.approvedBy = currentUser.userId;
        item.approvedAt = new Date().toISOString();
      }
    });

    addAuditLog({
      entityType: 'Requisition',
      entityId: req.id,
      action: 'APPROVE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Approved Purchase Requisition ${req.number} (AED ${formatAED(req.totalAmount)})`,
    });

    setActionMessage(`Approved Requisition ${req.number}. It is now eligible for Purchase Order conversion.`);
  };

  const handleRejectConfirm = (reason?: string) => {
    if (!rejectTarget) return;

    updateDb((state) => {
      const item = state.requisitions.find((r) => r.id === rejectTarget.id);
      if (item) {
        item.status = 'Rejected';
        item.rejectionReason = reason;
      }
    });

    addAuditLog({
      entityType: 'Requisition',
      entityId: rejectTarget.id,
      action: 'REJECT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Rejected Requisition ${rejectTarget.number}. Reason: ${reason || 'Unspecified'}`,
    });

    setActionMessage(`Rejected Requisition ${rejectTarget.number} and returned to Maker.`);
    setRejectTarget(null);
  };

  const columns: ColumnDef<Requisition>[] = [
    {
      key: 'number',
      header: 'Requisition #',
      width: '140px',
      render: (r) => <DocLink number={r.number} showIcon />,
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (r) => <span className="font-semibold text-gray-800">{r.businessUnit}</span>,
    },
    {
      key: 'department',
      header: 'Department',
      width: '120px',
      render: (r) => <span className="text-gray-700 font-medium">{r.department}</span>,
    },
    {
      key: 'requisitionType',
      header: 'Type',
      width: '110px',
      render: (r) => (
        <span
          className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
            r.requisitionType === 'Capital Asset'
              ? 'bg-purple-100 text-purple-800'
              : r.requisitionType === 'Services'
              ? 'bg-amber-100 text-amber-800'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          {r.requisitionType || 'Goods'}
        </span>
      ),
    },
    {
      key: 'description',
      header: 'Justification / Purpose',
      render: (r) => (
        <span className="text-gray-900 block truncate max-w-xs" title={r.justification || r.description}>
          {r.justification || r.description || '—'}
        </span>
      ),
    },
    {
      key: 'date',
      header: 'Date',
      width: '95px',
      render: (r) => <span className="font-mono text-gray-600">{r.requisitionDate || r.date || '—'}</span>,
    },
    {
      key: 'totalAmount',
      header: 'Total Est. (AED)',
      align: 'right',
      width: '130px',
      render: (r) => (
        <span className="font-mono font-bold text-gray-900">{formatAED(r.totalAmount)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '130px',
      align: 'center',
      render: (r) => {
        const isApproved = r.status === 'Approved' || r.status === 'Converted to PO';
        const isPending = r.status === 'Pending Approval';
        const isRejected = r.status === 'Rejected';
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
            {r.status}
          </span>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '150px',
      align: 'right',
      render: (r) => {
        const canApproveResult = checkCanApprove(currentUser, r, 'Procurement');
        const isApproved = r.status === 'Approved';

        return (
          <div className="flex items-center justify-end space-x-1.5">
            {/* If approved and user is Maker -> Create PO button */}
            {isApproved && makerCheck.allowed && (
              <button
                onClick={() => onNavigate(`#/procurement/orders/create?reqNumber=${r.number}`)}
                className="px-2 py-1 bg-[#5B2C83] text-white hover:bg-[#3F1D5C] rounded text-[11px] font-semibold flex items-center space-x-1 cursor-pointer"
                title="Create PO from Requisition"
              >
                <ShoppingCart className="w-3 h-3" />
                <span>Create PO</span>
              </button>
            )}

            {/* If pending and user is Approver */}
            {canApproveResult.allowed && (
              <>
                <button
                  onClick={() => handleApprove(r)}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold cursor-pointer"
                  title="Approve Requisition"
                >
                  Approve
                </button>
                <button
                  onClick={() => setRejectTarget(r)}
                  className="px-2 py-1 border border-rose-200 text-rose-600 hover:bg-rose-50 rounded text-[11px] font-semibold cursor-pointer"
                  title="Reject Requisition"
                >
                  Reject
                </button>
              </>
            )}

            {/* If Draft and user is Maker -> Edit */}
            {r.status === 'Draft' && makerCheck.allowed && (
              <button
                onClick={() => onNavigate(`#/procurement/requisitions/create?edit=${r.id}`)}
                className="px-2 py-1 text-[#5B2C83] hover:underline text-[11px] font-semibold cursor-pointer"
              >
                Edit
              </button>
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
            <FileText className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              Purchase Requisitions Work Area
            </h1>
            <p className="text-xs text-gray-500">
              Procurement &bull; Maker: Liam Carter &bull; Approver: Daniel Reed (CFO) &bull; Section 2.2 Specification
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {makerCheck.allowed ? (
            <button
              onClick={() => onNavigate('#/procurement/requisitions/create')}
              className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Requisition</span>
            </button>
          ) : (
            <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-lg text-xs text-gray-500">
              <span>Only Liam Carter (Maker) can create requisitions</span>
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

      {/* Summary Status Tiles */}
      <SummaryTiles
        tiles={summaryTiles}
        activeTileId={selectedStatus || 'all'}
        onSelectTile={handleTileSelect}
      />

      {/* Filter Bar */}
      <TableFilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedBU={selectedBU}
        onBUChange={setSelectedBU}
        buOptions={uniqueBUs}
        selectedStatus={selectedStatus}
        onStatusChange={setSelectedStatus}
        statusOptions={uniqueStatuses}
        dateFrom={dateFrom}
        onDateFromChange={setDateFrom}
        dateTo={dateTo}
        onDateToChange={setDateTo}
        activeFilterChips={activeFilterChips}
        onClearAll={clearAllFilters}
        totalRecords={totalCount}
        filteredRecords={filteredCount}
      />

      {/* Data Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <DataTable
          data={filteredData}
          columns={columns}
          title="Enterprise Purchase Requisitions"
          searchPlaceholder="Search requisitions..."
          emptyMessage="No requisitions found matching current criteria."
        />
      </div>

      {rejectTarget && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setRejectTarget(null)}
          onConfirm={(reason) => handleRejectConfirm(reason)}
          title={`Reject Requisition ${rejectTarget.number}`}
          message="Provide mandatory reason for returning this requisition to maker (Liam Carter):"
          confirmLabel="Confirm Rejection"
          cancelLabel="Cancel"
          actionType="reject"
          requireComment={true}
        />
      )}
    </div>
  );
};
