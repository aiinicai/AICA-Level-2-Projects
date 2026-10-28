import React, { useState } from 'react';
import {
  Boxes,
  Plus,
  Eye,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
  PackageCheck,
  BookOpen,
  AlertCircle,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { Receipt, ReceiptLine, PurchaseOrder, InventoryBalance } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';
import { TableFilterBar } from '../../components/TableFilterBar';
import { DocLink } from '../../components/DocLink';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED, round2, addMoney } from '../../core/currency';
import { getActiveUser, checkMakerPermission, checkCanApprove } from '../../core/auth';
import { getNextSequenceNumber } from '../../core/sequences';
import { buildReceiptAccounting, postToGL } from '../../core/postingEngine';
import { useTableFilters } from '../../core/useTableFilters';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEMO_TODAY } from '../../core/dates';

interface ReceivingPageProps {
  onNavigate: (route: string) => void;
  initialAction?: string;
  initialPoNumber?: string;
}

export const ReceivingPage: React.FC<ReceivingPageProps> = ({
  onNavigate,
  initialAction,
  initialPoNumber,
}) => {
  const db = getDb();
  const currentUser = getActiveUser();
  const receipts = db.receipts || [];

  const makerCheck = checkMakerPermission(currentUser, 'Supply Chain Execution');

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
  } = useTableFilters(receipts, {
    searchFields: ['number', 'poNumber', 'supplierName', 'notes', 'deliveryNoteNumber'],
    dateField: 'receiptDate',
    amountField: 'totalAmount',
    statusField: 'status',
    buField: 'businessUnit',
    counterpartyField: 'supplierName',
  });

  const [viewAccountingNumber, setViewAccountingNumber] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<Receipt | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Create Receipt Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(initialAction === 'create' || false);
  const [createBU, setCreateBU] = useState('H01');
  const [createPoNumber, setCreatePoNumber] = useState(initialPoNumber || '');
  const [deliveryNote, setDeliveryNote] = useState(`DN-${Date.now().toString().slice(-6)}`);
  const [receiptDate, setReceiptDate] = useState(DEMO_TODAY);
  const [receivingLines, setReceivingLines] = useState<Array<{
    poLineNumber: number;
    itemCode: string;
    description: string;
    orderedQty: number;
    receivedToDate: number;
    openQty: number;
    receivingQty: number;
    unitPrice: number;
    lotNumber: string;
    expiryDate: string;
    subInventory: 'Main Store' | 'Pharmacy' | 'OT / Ward';
  }>>([]);
  const [createError, setCreateError] = useState<string | null>(null);

  // Approved POs eligible for receiving
  const approvedPOs = (db.purchaseOrders || []).filter(
    (p) => (p.status === 'Approved' || p.status === 'Partially Received') && (p.businessUnit === createBU || createBU === 'All')
  );

  // When PO is chosen in modal
  const handleSelectPO = (poNum: string) => {
    setCreatePoNumber(poNum);
    const po = db.purchaseOrders?.find((p) => p.number === poNum);
    if (!po) return;

    setCreateBU(po.businessUnit);
    const rLines = (po.lines || []).map((l) => {
      const openQty = Math.max(0, l.quantity - (l.receivedQuantity || 0));
      return {
        poLineNumber: l.lineNumber,
        itemCode: l.itemCode || 'ITEM',
        description: l.description,
        orderedQty: l.quantity,
        receivedToDate: l.receivedQuantity || 0,
        openQty,
        receivingQty: openQty,
        unitPrice: l.unitPrice,
        lotNumber: `LOT-2026-${Math.floor(Math.random() * 9000 + 1000)}`,
        expiryDate: '2027-10-31',
        subInventory: (l.department === 'Pharmacy' ? 'Pharmacy' : 'Main Store') as any,
      };
    });
    setReceivingLines(rLines);
  };

  // Status counts
  const pendingCount = receipts.filter((r) => r.status === 'Pending Approval').length;
  const postedCount = receipts.filter((r) => r.status === 'Posted' || r.status === 'Approved').length;
  const draftCount = receipts.filter((r) => r.status === 'Draft').length;
  const totalValue = receipts.reduce((acc, r) => acc + (r.totalAmount || 0), 0);

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All Goods Receipts', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Approval', count: pendingCount, color: 'amber' },
    { id: 'Posted', label: 'Posted to GRNI (2010)', count: postedCount, color: 'emerald' },
    { id: 'Draft', label: 'Drafts', count: draftCount, color: 'slate' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (!id || id === 'all') setSelectedStatus('');
    else setSelectedStatus(id);
  };

  // Submit new receipt (Maker: Noah Bennett)
  const handleSaveReceipt = (asDraft: boolean) => {
    if (!makerCheck.allowed) {
      setCreateError(makerCheck.reason || 'Only Store Controller (Noah Bennett) can create Goods Receipts.');
      return;
    }
    const po = db.purchaseOrders?.find((p) => p.number === createPoNumber);
    if (!po) {
      setCreateError('Please select a valid Approved Purchase Order.');
      return;
    }

    const linesToReceive = receivingLines.filter((l) => l.receivingQty > 0);
    if (linesToReceive.length === 0) {
      setCreateError('At least one line item must have a receiving quantity greater than 0.');
      return;
    }

    // 0% tolerance check against open quantity
    for (const l of linesToReceive) {
      if (l.receivingQty > l.openQty) {
        setCreateError(
          `Receiving quantity (${l.receivingQty}) exceeds open PO quantity (${l.openQty}) for ${l.description}. Zero tolerance policy enforced.`
        );
        return;
      }
    }

    const rcvNumber = getNextSequenceNumber('RCV');
    const totalAmount = round2(linesToReceive.reduce((sum, l) => sum + l.receivingQty * l.unitPrice, 0));

    const newReceipt: Receipt = {
      id: `RCV-${Date.now()}`,
      number: rcvNumber,
      poNumber: po.number,
      poId: po.id,
      businessUnit: po.businessUnit,
      supplierId: po.supplierId,
      supplierName: po.supplierName,
      receiptDate,
      deliveryNoteNumber: deliveryNote,
      notes: `Goods receipt note against ${po.number}`,
      status: asDraft ? 'Draft' : 'Pending Approval',
      lines: linesToReceive.map((l, i) => ({
        lineNumber: i + 1,
        poNumber: po.number,
        poLineNumber: l.poLineNumber,
        itemCode: l.itemCode,
        description: l.description,
        orderedQuantity: l.orderedQty,
        receivedToDate: l.receivedToDate,
        quantityReceived: l.receivingQty,
        unitPrice: l.unitPrice,
        lineAmount: round2(l.receivingQty * l.unitPrice),
        account: l.itemCode.includes('PH') ? '1200' : l.itemCode.includes('CS') ? '1210' : '1230',
        lotNumber: l.lotNumber,
        expiryDate: l.expiryDate,
        subInventory: l.subInventory,
      })),
      totalAmount,
      createdBy: currentUser.userId,
      createdAt: new Date().toISOString(),
      submittedAt: !asDraft ? new Date().toISOString() : undefined,
    };

    updateDb((state) => {
      if (!state.receipts) state.receipts = [];
      state.receipts.unshift(newReceipt);
    });

    addAuditLog({
      entityType: 'Receipt',
      entityId: newReceipt.id,
      action: asDraft ? 'CREATE' : 'SUBMIT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `${asDraft ? 'Created Draft' : 'Submitted for Approval'} Goods Receipt ${newReceipt.number} for PO ${po.number} (AED ${formatAED(totalAmount)})`,
    });

    setActionMessage(
      `Receipt ${newReceipt.number} ${asDraft ? 'saved as Draft' : 'submitted for Approval to Charlotte Davis'}.`
    );
    setIsCreateOpen(false);
    setCreateError(null);
  };

  // Approve Receipt Handler (Approver: Charlotte Davis)
  // On approval, posting engine creates Dr Inventory / Cr GRNI 2010 atomically!
  const handleApprove = (rcv: Receipt) => {
    const subEntry = buildReceiptAccounting(rcv);
    const postRes = postToGL(subEntry, {
      createdBy: currentUser.userId,
      approvedBy: currentUser.userId,
      category: 'Goods Receipt',
    });

    if (!postRes.success || !postRes.journal) {
      setActionMessage(`Posting Error: ${postRes.errors?.join('; ')}`);
      return;
    }

    updateDb((state) => {
      // 1. Update Receipt Status
      const item = state.receipts.find((r) => r.id === rcv.id);
      if (item) {
        item.status = 'Posted';
        item.approvedBy = currentUser.userId;
        item.approvedAt = new Date().toISOString();
        item.glJournalId = postRes.journal.id;
        item.glJournalNumber = postRes.journal.number;
      }

      // 2. Update PO Received Quantities
      const po = state.purchaseOrders.find((p) => p.number === rcv.poNumber);
      if (po) {
        rcv.lines.forEach((rl) => {
          const poLine = po.lines.find((pl) => pl.lineNumber === rl.poLineNumber);
          if (poLine) {
            poLine.receivedQuantity = (poLine.receivedQuantity || 0) + rl.quantityReceived;
          }
        });
        const allReceived = po.lines.every((pl) => pl.receivedQuantity >= pl.quantity);
        po.status = allReceived ? 'Received' : 'Partially Received';
      }

      // 3. Update Inventory Balances on Hand
      rcv.lines.forEach((rl) => {
        const subInv = (rl.subInventory || 'Main Store') as 'Main Store' | 'Pharmacy' | 'OT / Ward';
        const existingBal = state.inventoryBalances?.find(
          (b) => b.businessUnit === rcv.businessUnit && b.itemCode === rl.itemCode && b.subInventory === subInv
        );
        if (existingBal) {
          existingBal.quantityOnHand += rl.quantityReceived;
        } else {
          if (!state.inventoryBalances) state.inventoryBalances = [];
          state.inventoryBalances.push({
            businessUnit: rcv.businessUnit,
            subInventory: subInv,
            itemCode: rl.itemCode,
            quantityOnHand: rl.quantityReceived,
            weightedAvgCost: rl.unitPrice,
          });
        }
      });
    });

    addAuditLog({
      entityType: 'Receipt',
      entityId: rcv.id,
      action: 'APPROVE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Approved Receipt ${rcv.number}. Generated GL Journal ${postRes.journal.number} (Dr Inventory, Cr GRNI 2010)`,
    });

    setActionMessage(
      `Approved Receipt ${rcv.number}! Accounted and posted to General Ledger (Journal: ${postRes.journal.number}). Inventory on-hand updated.`
    );
  };

  const handleRejectConfirm = (reason?: string) => {
    if (!rejectTarget) return;

    updateDb((state) => {
      const item = state.receipts.find((r) => r.id === rejectTarget.id);
      if (item) {
        item.status = 'Rejected';
        item.rejectionReason = reason;
      }
    });

    addAuditLog({
      entityType: 'Receipt',
      entityId: rejectTarget.id,
      action: 'REJECT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Rejected Receipt ${rejectTarget.number}. Reason: ${reason || 'Unspecified'}`,
    });

    setActionMessage(`Rejected Goods Receipt ${rejectTarget.number} and returned to Store Controller.`);
    setRejectTarget(null);
  };

  const columns: ColumnDef<Receipt>[] = [
    {
      key: 'number',
      header: 'Receipt #',
      width: '140px',
      render: (r) => <DocLink number={r.number} showIcon />,
    },
    {
      key: 'poNumber',
      header: 'PO Reference',
      width: '140px',
      render: (r) => <DocLink number={r.poNumber} />,
    },
    {
      key: 'supplierName',
      header: 'Supplier / Vendor',
      render: (r) => (
        <div>
          <span className="font-semibold text-gray-900 block truncate">{r.supplierName}</span>
          {r.deliveryNoteNumber && (
            <span className="text-[10px] text-gray-400">DN: {r.deliveryNoteNumber}</span>
          )}
        </div>
      ),
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (r) => <span className="font-semibold text-gray-800">{r.businessUnit}</span>,
    },
    {
      key: 'receiptDate',
      header: 'Receipt Date',
      width: '100px',
      render: (r) => <span className="font-mono text-gray-600">{r.receiptDate}</span>,
    },
    {
      key: 'totalAmount',
      header: 'Receipt Value (AED)',
      align: 'right',
      width: '145px',
      render: (r) => <span className="font-mono font-bold text-gray-900">{formatAED(r.totalAmount)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: '130px',
      align: 'center',
      render: (r) => {
        const isPosted = r.status === 'Posted' || r.status === 'Approved';
        const isPending = r.status === 'Pending Approval';
        const isRejected = r.status === 'Rejected';
        return (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
              isPosted
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
      width: '175px',
      align: 'right',
      render: (r) => {
        const canApproveResult = checkCanApprove(currentUser, r, 'Supply Chain Execution');

        return (
          <div className="flex items-center justify-end space-x-1.5">
            {/* View Accounting button */}
            <button
              onClick={() => setViewAccountingNumber(r.number)}
              className="px-2 py-1 text-[#5B2C83] hover:bg-plum-50 rounded text-[11px] font-semibold flex items-center space-x-1 cursor-pointer"
              title="View Subledger Accounting & GL Journal"
            >
              <BookOpen className="w-3 h-3" />
              <span>Accounting</span>
            </button>

            {/* Approver actions */}
            {canApproveResult.allowed && (
              <>
                <button
                  onClick={() => handleApprove(r)}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold cursor-pointer"
                  title="Approve and Post to General Ledger"
                >
                  Approve
                </button>
                <button
                  onClick={() => setRejectTarget(r)}
                  className="px-2 py-1 border border-rose-200 text-rose-600 hover:bg-rose-50 rounded text-[11px] font-semibold cursor-pointer"
                  title="Reject"
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
      <ModuleAccessBanner module="Supply Chain Execution" onNavigate={onNavigate} />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <PackageCheck className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              Goods Receiving Work Area (GRN & GRNI 2010 Accrual)
            </h1>
            <p className="text-xs text-gray-500">
              Supply Chain Execution &bull; Maker: Noah Bennett &bull; Approver: Charlotte Davis &bull; Section 3 Specification
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {makerCheck.allowed ? (
            <button
              onClick={() => setIsCreateOpen(true)}
              className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Goods Receipt (GRN)</span>
            </button>
          ) : (
            <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-lg text-xs text-gray-500">
              <span>Only Store Controller (Noah Bennett) can create receipts</span>
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
          title="Goods Receipt Notes"
          searchPlaceholder="Search receipts..."
          emptyMessage="No goods receipts found matching current criteria."
        />
      </div>

      {/* Create Receipt Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl border border-gray-200 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 shrink-0">
              <div className="flex items-center space-x-2">
                <PackageCheck className="w-5 h-5 text-[#5B2C83]" />
                <h3 className="font-bold text-sm text-gray-900">Create Goods Receipt Note (GRN)</h3>
              </div>
              <button onClick={() => setIsCreateOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {createError && (
              <div className="mt-3 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center space-x-2 shrink-0">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <div className="mt-4 space-y-4 overflow-y-auto flex-1 pr-1 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-gray-500 font-semibold mb-1">Select Approved PO *</label>
                  <select
                    value={createPoNumber}
                    onChange={(e) => handleSelectPO(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg font-mono text-[#5B2C83] font-semibold"
                  >
                    <option value="">-- Choose Approved PO --</option>
                    {approvedPOs.map((p) => (
                      <option key={p.id} value={p.number}>
                        {p.number} &bull; {p.supplierName} ({p.businessUnit})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-500 font-semibold mb-1">Receipt Date</label>
                  <input
                    type="date"
                    value={receiptDate}
                    onChange={(e) => setReceiptDate(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-gray-500 font-semibold mb-1">Delivery Note (DN) #</label>
                  <input
                    type="text"
                    value={deliveryNote}
                    onChange={(e) => setDeliveryNote(e.target.value)}
                    className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              {receivingLines.length > 0 && (
                <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#FAF7FC] text-gray-700 uppercase font-semibold text-[10px] border-b border-gray-200">
                      <tr>
                        <th className="py-2 px-3">Item / Description</th>
                        <th className="py-2 px-3 text-right">Ordered</th>
                        <th className="py-2 px-3 text-right">Open Qty</th>
                        <th className="py-2 px-3 text-right w-24">Receiving Qty</th>
                        <th className="py-2 px-3">Lot #</th>
                        <th className="py-2 px-3">Sub-Inventory</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {receivingLines.map((l, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="py-2 px-3">
                            <span className="font-semibold text-gray-800 block">{l.description}</span>
                            <span className="text-[10px] text-gray-400 font-mono">{l.itemCode}</span>
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-gray-600">{l.orderedQty}</td>
                          <td className="py-2 px-3 text-right font-mono font-bold text-amber-700">
                            {l.openQty}
                          </td>
                          <td className="py-2 px-3 text-right">
                            <input
                              type="number"
                              min="0"
                              max={l.openQty}
                              value={l.receivingQty}
                              onChange={(e) => {
                                const val = Number(e.target.value);
                                const updated = [...receivingLines];
                                updated[idx].receivingQty = val;
                                setReceivingLines(updated);
                              }}
                              className="w-20 px-2 py-1 text-right bg-white border border-gray-300 rounded font-mono font-bold text-[#5B2C83]"
                            />
                          </td>
                          <td className="py-2 px-3">
                            <input
                              type="text"
                              value={l.lotNumber}
                              onChange={(e) => {
                                const updated = [...receivingLines];
                                updated[idx].lotNumber = e.target.value;
                                setReceivingLines(updated);
                              }}
                              className="w-28 px-2 py-1 bg-white border border-gray-300 rounded font-mono text-[11px]"
                            />
                          </td>
                          <td className="py-2 px-3">
                            <select
                              value={l.subInventory}
                              onChange={(e) => {
                                const updated = [...receivingLines];
                                updated[idx].subInventory = e.target.value as any;
                                setReceivingLines(updated);
                              }}
                              className="px-2 py-1 bg-white border border-gray-300 rounded text-[11px]"
                            >
                              <option value="Main Store">Main Store</option>
                              <option value="Pharmacy">Pharmacy</option>
                              <option value="OT / Ward">OT / Ward</option>
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between shrink-0">
              <span className="text-xs text-gray-400">
                0% Quantity Tolerance enforced &bull; Posts to GRNI 2010 on approval
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="px-3 py-1.5 text-gray-600 hover:text-gray-800 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleSaveReceipt(true)}
                  className="px-3 py-1.5 border border-plum-300 text-[#5B2C83] hover:bg-plum-50 rounded-lg text-xs font-semibold"
                >
                  Save Draft
                </button>
                <button
                  onClick={() => handleSaveReceipt(false)}
                  className="px-4 py-1.5 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs"
                >
                  Submit for Approval
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* View Accounting Modal */}
      {viewAccountingNumber && (
        <ViewAccountingModal
          isOpen={Boolean(viewAccountingNumber)}
          onClose={() => setViewAccountingNumber(null)}
          documentNumber={viewAccountingNumber}
          sourceModule="Procurement/Inventory"
          onNavigateToJournal={() => onNavigate('#/general-accounting/journals')}
        />
      )}

      {/* Rejection Dialog */}
      {rejectTarget && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setRejectTarget(null)}
          onConfirm={(reason) => handleRejectConfirm(reason)}
          title={`Reject Goods Receipt ${rejectTarget.number}`}
          message="Provide mandatory reason for returning this receipt to Store Controller (Noah Bennett):"
          confirmLabel="Confirm Rejection"
          cancelLabel="Cancel"
          actionType="reject"
          requireComment={true}
        />
      )}
    </div>
  );
};
