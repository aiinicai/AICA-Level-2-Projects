import React, { useState } from 'react';
import {
  X,
  Flag,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileText,
  Clock,
  ArrowRight,
  ShieldCheck,
  CheckSquare,
} from 'lucide-react';
import { getActiveUser, checkCanApprove } from '../core/auth';
import { getDb, updateDb, addAuditLog } from '../core/storage';
import { formatAED } from '../core/currency';
import { DocLink } from './DocLink';
import { ConfirmDialog } from './ConfirmDialog';
import { postToGL, buildReceiptAccounting, buildAPInvoiceAccounting, buildARTransactionAccounting, buildCashVoucherAccounting } from '../core/postingEngine';

interface WorklistModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (route: string) => void;
}

interface PendingItem {
  id: string;
  number: string;
  module: string;
  type: string;
  businessUnit: string;
  date: string;
  amount: number;
  counterparty: string;
  createdBy: string;
  rawType: 'APInvoice' | 'ARTransaction' | 'Requisition' | 'PurchaseOrder' | 'Receipt' | 'CashVoucher' | 'ICTransaction' | 'GLJournal';
  rawRecord: any;
}

export const WorklistModal: React.FC<WorklistModalProps> = ({ isOpen, onClose, onNavigate }) => {
  if (!isOpen) return null;

  const db = getDb();
  const currentUser = getActiveUser();

  const [selectedModule, setSelectedModule] = useState<string>('All');
  const [rejectTarget, setRejectTarget] = useState<PendingItem | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Collect all items pending approval where current user has approval rights
  const pendingItems: PendingItem[] = [];

  // 1. AP Invoices
  (db.apInvoices || []).forEach((inv) => {
    if (inv.status === 'Pending Approval' || inv.status === 'Pending Higher Approval') {
      const check = checkCanApprove(currentUser, inv, 'Payables');
      if (check.allowed) {
        pendingItems.push({
          id: inv.id,
          number: inv.number,
          module: 'Payables',
          type: inv.invoiceType === 'Credit Memo' ? 'AP Credit Memo' : 'Supplier Invoice',
          businessUnit: inv.businessUnit,
          date: inv.invoiceDate,
          amount: inv.totalAmount,
          counterparty: inv.supplierName,
          createdBy: inv.createdBy,
          rawType: 'APInvoice',
          rawRecord: inv,
        });
      }
    }
  });

  // 2. AR Transactions
  (db.arTransactions || []).forEach((ar) => {
    if (ar.status === 'Pending Approval' || ar.status === 'Pending Higher Approval') {
      const check = checkCanApprove(currentUser, ar, 'Receivables');
      if (check.allowed) {
        pendingItems.push({
          id: ar.id,
          number: ar.number,
          module: 'Receivables',
          type: ar.transactionClass === 'Credit Memo' ? 'AR Credit Memo' : 'Customer Invoice',
          businessUnit: ar.businessUnit,
          date: ar.transactionDate,
          amount: ar.totalAmount,
          counterparty: ar.customerName,
          createdBy: ar.createdBy,
          rawType: 'ARTransaction',
          rawRecord: ar,
        });
      }
    }
  });

  // 3. Purchase Requisitions
  (db.requisitions || []).forEach((req) => {
    if (req.status === 'Pending Approval') {
      const check = checkCanApprove(currentUser, req, 'Procurement');
      if (check.allowed) {
        pendingItems.push({
          id: req.id,
          number: req.number,
          module: 'Procurement',
          type: 'Purchase Requisition',
          businessUnit: req.businessUnit,
          date: req.requisitionDate || req.date || req.createdAt,
          amount: req.totalAmount,
          counterparty: req.department,
          createdBy: req.createdBy,
          rawType: 'Requisition',
          rawRecord: req,
        });
      }
    }
  });

  // 4. Purchase Orders
  (db.purchaseOrders || []).forEach((po) => {
    if (po.status === 'Pending Approval') {
      const check = checkCanApprove(currentUser, po, 'Procurement');
      if (check.allowed) {
        pendingItems.push({
          id: po.id,
          number: po.number,
          module: 'Procurement',
          type: 'Purchase Order',
          businessUnit: po.businessUnit,
          date: po.poDate || po.date || po.createdAt,
          amount: po.totalAmount,
          counterparty: po.supplierName,
          createdBy: po.createdBy,
          rawType: 'PurchaseOrder',
          rawRecord: po,
        });
      }
    }
  });

  // 5. Receipts (GRN)
  (db.receipts || []).forEach((rcv) => {
    if (rcv.status === 'Pending Approval') {
      const check = checkCanApprove(currentUser, rcv, 'Supply Chain Execution');
      if (check.allowed) {
        pendingItems.push({
          id: rcv.id,
          number: rcv.number,
          module: 'Supply Chain Execution',
          type: 'Goods Receipt Note (GRN)',
          businessUnit: rcv.businessUnit,
          date: rcv.receiptDate,
          amount: rcv.totalAmount,
          counterparty: rcv.supplierName,
          createdBy: rcv.createdBy,
          rawType: 'Receipt',
          rawRecord: rcv,
        });
      }
    }
  });

  // 6. Cash Vouchers
  (db.cashVouchers || []).forEach((v) => {
    if (v.status === 'Pending Approval') {
      const check = checkCanApprove(currentUser, v, 'Cash Management');
      if (check.allowed) {
        pendingItems.push({
          id: v.id,
          number: v.number,
          module: 'Cash Management',
          type: v.voucherType === 'Main Cash' ? 'Main Cash Voucher' : 'Petty Cash Voucher',
          businessUnit: v.businessUnit,
          date: v.date,
          amount: v.totalAmount,
          counterparty: v.payee,
          createdBy: v.createdBy,
          rawType: 'CashVoucher',
          rawRecord: v,
        });
      }
    }
  });

  // 7. GL Journals
  (db.glJournals || []).forEach((j) => {
    if (j.status === 'Pending Approval') {
      const check = checkCanApprove(currentUser, { createdBy: j.createdBy, totalAmount: j.totalDebit, status: j.status }, 'General Accounting');
      if (check.allowed) {
        pendingItems.push({
          id: j.id,
          number: j.number,
          module: 'General Accounting',
          type: 'Manual GL Journal',
          businessUnit: j.businessUnit,
          date: j.journalDate,
          amount: j.totalDebit,
          counterparty: j.category,
          createdBy: j.createdBy,
          rawType: 'GLJournal',
          rawRecord: j,
        });
      }
    }
  });

  const filteredItems = pendingItems.filter(
    (item) => selectedModule === 'All' || item.module === selectedModule
  );

  const modules = Array.from(new Set(pendingItems.map((p) => p.module)));

  // Approve single item handler
  const handleApprove = (item: PendingItem) => {
    if (item.rawType === 'APInvoice') {
      const subEntry = buildAPInvoiceAccounting(item.rawRecord);
      const postRes = postToGL(subEntry, { createdBy: currentUser.userId, approvedBy: currentUser.userId, category: 'Purchase Invoice' });
      updateDb((state) => {
        const inv = state.apInvoices.find((i) => i.id === item.id);
        if (inv) {
          inv.status = 'Approved';
          inv.approvedBy = currentUser.userId;
          inv.approvedAt = new Date().toISOString();
          inv.glJournalId = postRes.journal?.id;
        }
      });
    } else if (item.rawType === 'ARTransaction') {
      const subEntry = buildARTransactionAccounting(item.rawRecord);
      const postRes = postToGL(subEntry, { createdBy: currentUser.userId, approvedBy: currentUser.userId, category: 'Sales Invoice' });
      updateDb((state) => {
        const ar = state.arTransactions.find((i) => i.id === item.id);
        if (ar) {
          ar.status = 'Approved';
          ar.approvedBy = currentUser.userId;
          ar.approvedAt = new Date().toISOString();
          ar.glJournalId = postRes.journal?.id;
        }
      });
    } else if (item.rawType === 'Requisition') {
      updateDb((state) => {
        const req = state.requisitions.find((r) => r.id === item.id);
        if (req) {
          req.status = 'Approved';
          req.approvedBy = currentUser.userId;
          req.approvedAt = new Date().toISOString();
        }
      });
    } else if (item.rawType === 'PurchaseOrder') {
      updateDb((state) => {
        const po = state.purchaseOrders.find((p) => p.id === item.id);
        if (po) {
          po.status = 'Approved';
          po.approvedBy = currentUser.userId;
          po.approvedAt = new Date().toISOString();
        }
      });
    } else if (item.rawType === 'Receipt') {
      const subEntry = buildReceiptAccounting(item.rawRecord);
      const postRes = postToGL(subEntry, { createdBy: currentUser.userId, approvedBy: currentUser.userId, category: 'Goods Receipt' });
      updateDb((state) => {
        const rcv = state.receipts.find((r) => r.id === item.id);
        if (rcv) {
          rcv.status = 'Approved';
          rcv.approvedBy = currentUser.userId;
          rcv.approvedAt = new Date().toISOString();
          rcv.glJournalId = postRes.journal?.id;
          rcv.glJournalNumber = postRes.journal?.number;
        }
      });
    } else if (item.rawType === 'CashVoucher') {
      const subEntry = buildCashVoucherAccounting(item.rawRecord);
      const postRes = postToGL(subEntry, { createdBy: currentUser.userId, approvedBy: currentUser.userId, category: 'Cash Expense' });
      updateDb((state) => {
        const v = state.cashVouchers.find((c) => c.id === item.id);
        if (v) {
          v.status = 'Approved';
          v.approvedBy = currentUser.userId;
          v.approvedAt = new Date().toISOString();
          v.glJournalId = postRes.journal?.id;
        }
      });
    } else if (item.rawType === 'GLJournal') {
      updateDb((state) => {
        const j = state.glJournals.find((x) => x.id === item.id);
        if (j) {
          j.status = 'Posted';
          j.approvedBy = currentUser.userId;
          j.approvedAt = new Date().toISOString();
          j.postedAt = new Date().toISOString();
        }
      });
    }

    addAuditLog({
      entityType: item.rawType,
      entityId: item.id,
      action: 'APPROVE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Approved via Worklist / My Approvals queue (${item.number})`,
    });

    setActionMessage(`Successfully approved ${item.type} ${item.number}.`);
  };

  const handleBulkApprove = () => {
    filteredItems.forEach((item) => handleApprove(item));
    setActionMessage(`Successfully bulk approved ${filteredItems.length} transactions.`);
  };

  const handleRejectConfirm = (reason?: string) => {
    if (!rejectTarget) return;

    updateDb((state) => {
      if (rejectTarget.rawType === 'APInvoice') {
        const i = state.apInvoices.find((x) => x.id === rejectTarget.id);
        if (i) { i.status = 'Rejected'; i.rejectionReason = reason; }
      } else if (rejectTarget.rawType === 'ARTransaction') {
        const i = state.arTransactions.find((x) => x.id === rejectTarget.id);
        if (i) { i.status = 'Rejected'; i.rejectionReason = reason; }
      } else if (rejectTarget.rawType === 'Requisition') {
        const i = state.requisitions.find((x) => x.id === rejectTarget.id);
        if (i) { i.status = 'Rejected'; i.rejectionReason = reason; }
      } else if (rejectTarget.rawType === 'PurchaseOrder') {
        const i = state.purchaseOrders.find((x) => x.id === rejectTarget.id);
        if (i) { i.status = 'Rejected'; i.rejectionReason = reason; }
      } else if (rejectTarget.rawType === 'Receipt') {
        const i = state.receipts.find((x) => x.id === rejectTarget.id);
        if (i) { i.status = 'Rejected'; i.rejectionReason = reason; }
      } else if (rejectTarget.rawType === 'CashVoucher') {
        const i = state.cashVouchers.find((x) => x.id === rejectTarget.id);
        if (i) { i.status = 'Rejected'; i.rejectionReason = reason; }
      } else if (rejectTarget.rawType === 'GLJournal') {
        const i = state.glJournals.find((x) => x.id === rejectTarget.id);
        if (i) { i.status = 'Rejected'; i.rejectionReason = reason; }
      }
    });

    addAuditLog({
      entityType: rejectTarget.rawType,
      entityId: rejectTarget.id,
      action: 'REJECT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Rejected from Worklist. Reason: ${reason || 'Not specified'}`,
    });

    setActionMessage(`Rejected ${rejectTarget.number} with comments.`);
    setRejectTarget(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-gray-200">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#3F1D5C] to-[#5B2C83] text-white px-6 py-4 flex items-center justify-between shadow-xs shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-amber-400 text-[#3F1D5C] flex items-center justify-center font-bold">
              <Flag className="w-5 h-5 fill-current" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-300">
                  Enterprise Worklist &bull; Approval Center
                </span>
              </div>
              <h2 className="text-lg font-bold tracking-tight text-white flex items-center space-x-2">
                <span>My Approvals</span>
                <span className="px-2 py-0.2 rounded-full bg-white/20 text-white font-mono text-xs">
                  {pendingItems.length} Awaiting Action
                </span>
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-white/10 hover:bg-rose-500/30 text-plum-200 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message Banner */}
        {actionMessage && (
          <div className="bg-emerald-50 border-b border-emerald-200 px-6 py-2.5 text-xs text-emerald-900 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{actionMessage}</span>
            </div>
            <button
              onClick={() => setActionMessage(null)}
              className="text-gray-400 hover:text-gray-700 cursor-pointer font-bold"
            >
              &times;
            </button>
          </div>
        )}

        {/* Filter bar */}
        <div className="px-6 py-3 bg-[#FAF7FC] border-b border-plum-100 flex flex-wrap items-center justify-between gap-3 text-xs shrink-0">
          <div className="flex items-center space-x-2">
            <span className="text-gray-500 font-semibold text-[11px]">Filter Module:</span>
            <button
              onClick={() => setSelectedModule('All')}
              className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors cursor-pointer ${
                selectedModule === 'All'
                  ? 'bg-[#5B2C83] text-white'
                  : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              All ({pendingItems.length})
            </button>
            {modules.map((m) => (
              <button
                key={m}
                onClick={() => setSelectedModule(m)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors cursor-pointer ${
                  selectedModule === m
                    ? 'bg-[#5B2C83] text-white'
                    : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
                }`}
              >
                {m} ({pendingItems.filter((i) => i.module === m).length})
              </button>
            ))}
          </div>

          {filteredItems.length > 0 && (
            <button
              onClick={handleBulkApprove}
              className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-2xs flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <CheckSquare className="w-3.5 h-3.5" />
              <span>Approve All ({filteredItems.length})</span>
            </button>
          )}
        </div>

        {/* Content Table */}
        <div className="flex-1 p-6 overflow-y-auto">
          {filteredItems.length === 0 ? (
            <div className="py-16 text-center text-gray-400 text-xs">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2 opacity-60" />
              <p className="font-semibold text-base text-gray-700">All caught up!</p>
              <p className="text-gray-400 mt-1 max-w-sm mx-auto">
                No items are currently awaiting your authorization in this queue. Items created by you are segregated and pending review by designated checkers.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredItems.map((item) => (
                <div
                  key={`${item.rawType}-${item.id}`}
                  className="p-4 rounded-xl border border-gray-200 bg-white hover:border-plum-300 transition-all shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <DocLink number={item.number} prefixBadge showIcon />
                      <span className="text-gray-300">&bull;</span>
                      <span className="text-[11px] font-semibold text-gray-700">{item.type}</span>
                      <span className="text-gray-300">&bull;</span>
                      <span className="text-[11px] text-gray-500">{item.businessUnit}</span>
                    </div>

                    <div className="flex items-center space-x-3 text-xs text-gray-600">
                      <span>
                        Party: <strong className="text-gray-800">{item.counterparty}</strong>
                      </span>
                      <span>&bull;</span>
                      <span>
                        Date: <span className="font-mono">{item.date}</span>
                      </span>
                      <span>&bull;</span>
                      <span>
                        Maker: <span className="text-emerald-700 font-medium">{item.createdBy}</span>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 self-end sm:self-auto shrink-0">
                    <div className="text-right">
                      <span className="text-[10px] text-gray-400 block uppercase font-semibold">Amount</span>
                      <span className="font-mono font-bold text-sm text-[#5B2C83]">
                        {formatAED(item.amount)}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1.5 ml-2">
                      <button
                        onClick={() => handleApprove(item)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-2xs flex items-center space-x-1 transition-colors cursor-pointer"
                        title="Approve and post to General Ledger"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approve</span>
                      </button>

                      <button
                        onClick={() => setRejectTarget(item)}
                        className="px-2.5 py-1.5 border border-rose-200 text-rose-600 hover:bg-rose-50 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                        title="Reject with mandatory comments"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 border-t border-gray-200 px-6 py-3 flex items-center justify-between text-xs text-gray-500 shrink-0">
          <span>
            Logged in as <strong className="text-gray-800">{currentUser.name}</strong> ({currentUser.role})
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-800 hover:bg-gray-900 text-white rounded-lg font-semibold cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>

      {rejectTarget && (
        <ConfirmDialog
          isOpen={true}
          onClose={() => setRejectTarget(null)}
          onConfirm={(reason) => handleRejectConfirm(reason)}
          title={`Reject ${rejectTarget.type} ${rejectTarget.number}`}
          message={`Please provide mandatory comments explaining the reason for returning this transaction to maker (${rejectTarget.createdBy}):`}
          confirmLabel="Confirm Rejection"
          cancelLabel="Keep in Queue"
          actionType="reject"
          requireComment={true}
        />
      )}
    </div>
  );
};
