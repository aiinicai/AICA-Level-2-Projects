import React, { useState } from 'react';
import {
  Landmark,
  Plus,
  Eye,
  CheckCircle,
  AlertTriangle,
  AlertCircle,
  XCircle,
  Clock,
  ShieldCheck,
  Receipt,
  CheckCircle2,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { CashVoucher, TransactionStatus } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { RightRail } from '../../components/RightRail';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED, round2, subMoney, addMoney } from '../../core/currency';
import { getActiveUser, checkCanApprove } from '../../core/auth';
import { getNextSequenceNumber } from '../../core/sequences';
import { buildCashVoucherAccounting, postToGL } from '../../core/postingEngine';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEMO_TODAY } from '../../core/dates';

interface PettyCashPageProps {
  onNavigate: (route: string) => void;
  initialAction?: string;
}

export const PettyCashPage: React.FC<PettyCashPageProps> = ({ onNavigate, initialAction }) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [viewAccountingNumber, setViewAccountingNumber] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(initialAction === 'create');
  const [approveTarget, setApproveTarget] = useState<CashVoucher | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form states for new voucher
  const [voucherBU, setVoucherBU] = useState('H01');
  const [payee, setPayee] = useState('City Express Pathology Couriers');
  const [expenseAccount, setExpenseAccount] = useState('6200'); // Office Supplies
  const [department, setDepartment] = useState('Administration');
  const [amountStr, setAmountStr] = useState('450');
  const [taxCode, setTaxCode] = useState<'STANDARD_5' | 'ZERO_0'>('STANDARD_5');
  const [description, setDescription] = useState('Urgent lab specimen courier transfer across hospitals');

  // Filter vouchers
  const vouchers = db.cashVouchers.filter((v) => {
    if (selectedBU !== 'All' && v.businessUnit !== selectedBU) return false;
    if (statusFilter && v.status !== statusFilter) return false;
    return true;
  });

  const totalCount = db.cashVouchers.length;
  const pendingCount = db.cashVouchers.filter((v) => v.status === 'Pending Approval').length;
  const postedCount = db.cashVouchers.filter((v) => v.status === 'Posted').length;
  const pettyCount = db.cashVouchers.filter((v) => v.type === 'PettyCash').length;
  const mainCount = db.cashVouchers.filter((v) => v.type === 'MainCash').length;

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All Cash Vouchers', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Approval', count: pendingCount, color: 'amber' },
    { id: 'Posted', label: 'Approved & Posted', count: postedCount, color: 'emerald' },
    { id: 'petty', label: 'Petty Cash (1010)', count: pettyCount, color: 'plum' },
    { id: 'main', label: 'Main Cash Safe (1000)', count: mainCount, color: 'slate' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (!id || id === 'all') setStatusFilter(null);
    else if (id === 'petty') {
      // filter petty
      setStatusFilter(null);
    } else {
      setStatusFilter(id);
    }
  };

  // Create Voucher with AED 1,000 cap check (Acceptance Test 5!)
  const handleCreateVoucherSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const amt = parseFloat(amountStr) || 0;

    // Strict Acceptance Test 5: Petty cash voucher above the cap (AED 1,000) is blocked!
    if (amt > 1000) {
      setErrorMessage(
        `Cap Violation Blocked: Petty Cash expense voucher amount (AED ${formatAED(amt)}) exceeds the statutory imprest limit of AED 1,000.00 per voucher. Route through AP Invoice or Main Cash safe.`
      );
      return;
    }

    if (amt <= 0) {
      setErrorMessage('Amount must be greater than zero.');
      return;
    }

    const taxAmt = taxCode === 'STANDARD_5' ? round2(amt * 0.05) : 0;
    const assignedSeq = getNextSequenceNumber('PCV', 2026);

    const newVoucher: CashVoucher = {
      id: `VOUCH-${Date.now()}`,
      number: assignedSeq,
      type: 'PettyCash',
      businessUnit: voucherBU,
      date: DEMO_TODAY,
      payee,
      expenseCategory: 'Operating Expense',
      expenseAccount,
      department,
      description,
      amount: amt,
      taxCode,
      taxAmount: taxAmt,
      receiptAttached: true,
      status: 'Pending Approval',
      createdBy: currentUser.userId,
      createdAt: new Date().toISOString(),
    };

    updateDb((state) => {
      state.cashVouchers.unshift(newVoucher);
    });

    addAuditLog({
      entityType: 'CashVoucher',
      entityId: newVoucher.id,
      action: 'SUBMIT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Created and submitted petty cash voucher ${newVoucher.number} for AED ${formatAED(amt)}`,
    });

    setIsCreateOpen(false);
    setActionMessage(
      `Petty Cash Voucher ${newVoucher.number} created for AED ${formatAED(amt)}. Submitted for Checker approval.`
    );
  };

  // Approve Voucher Flow -> Posts to GL (Dr Expense, Dr 1400 VAT, Cr 1010 Petty Cash)
  const handleApproveConfirm = () => {
    if (!approveTarget) return;

    const check = checkCanApprove(currentUser, approveTarget);
    if (!check.allowed) {
      setErrorMessage(`Approval Denied: ${check.reason}`);
      setApproveTarget(null);
      return;
    }

    const subEntry = buildCashVoucherAccounting(approveTarget);
    const postRes = postToGL(subEntry, {
      createdBy: approveTarget.createdBy,
      approvedBy: currentUser.userId,
      category: 'Cash Expense',
    });

    if (postRes.success && postRes.journal) {
      updateDb((state) => {
        const v = state.cashVouchers.find((i) => i.id === approveTarget.id);
        if (v) {
          v.status = 'Posted';
          v.approvedBy = currentUser.userId;
          v.approvedAt = new Date().toISOString();
          v.glJournalId = postRes.journal!.id;
        }
      });

      addAuditLog({
        entityType: 'CashVoucher',
        entityId: approveTarget.id,
        action: 'APPROVE',
        userId: currentUser.userId,
        userName: currentUser.name,
        comments: `Approved cash voucher ${approveTarget.number} and posted GL journal ${postRes.journal.number}`,
      });

      setActionMessage(
        `Successfully approved Petty Cash Voucher ${approveTarget.number}. Generated GL Journal ${postRes.journal.number} (Dr ${approveTarget.expenseAccount} / Dr 1400 VAT / Cr 1010 Petty Cash).`
      );
    } else {
      setErrorMessage(`Posting Failed: ${postRes.errors?.join('; ')}`);
    }

    setApproveTarget(null);
  };

  const columns: ColumnDef<CashVoucher>[] = [
    {
      key: 'number',
      header: 'Voucher No.',
      width: '140px',
      render: (v) => <span className="font-mono font-bold text-[#5B2C83]">{v.number}</span>,
    },
    {
      key: 'type',
      header: 'Fund Type',
      width: '110px',
      render: (v) => (
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
            v.type === 'PettyCash'
              ? 'bg-plum-50 text-[#5B2C83] border border-plum-200'
              : 'bg-amber-50 text-amber-800 border border-amber-200'
          }`}
        >
          {v.type === 'PettyCash' ? 'Petty (1010)' : 'Main (1000)'}
        </span>
      ),
    },
    {
      key: 'payee',
      header: 'Payee / Recipient',
      render: (v) => (
        <div>
          <span className="font-semibold text-gray-900 block">{v.payee}</span>
          <span className="text-[10px] text-gray-500 truncate max-w-sm block">{v.description}</span>
        </div>
      ),
    },
    {
      key: 'businessUnit',
      header: 'BU',
      width: '60px',
      render: (v) => <span className="font-semibold text-gray-800">{v.businessUnit}</span>,
    },
    {
      key: 'date',
      header: 'Date',
      width: '100px',
    },
    {
      key: 'expenseAccount',
      header: 'Account',
      width: '80px',
      render: (v) => <span className="font-mono text-gray-700">{v.expenseAccount}</span>,
    },
    {
      key: 'amount',
      header: 'Amount (AED)',
      align: 'right',
      width: '120px',
      render: (v) => <span className="font-mono font-bold text-gray-900">{formatAED(v.amount)}</span>,
      exportValue: (v) => v.amount,
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
      width: '120px',
      align: 'center',
      sortable: false,
      render: (v) => {
        if (v.status === 'Pending Approval') {
          return (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setApproveTarget(v);
              }}
              className="px-2.5 py-0.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px]"
            >
              Approve
            </button>
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
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
              <Landmark className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">Cash Management: Petty Cash Registers</h1>
              <p className="text-xs text-gray-500">
                Imprest funds, AED 1,000 disbursement caps, receipt vouchers, and replenishment accounting.
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
              <span>Create Petty Cash Voucher</span>
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

        {errorMessage && (
          <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-300 text-rose-800 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-700 font-bold ml-2">
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
          title="Petty Cash Expense Vouchers"
          data={vouchers}
          columns={columns}
          keyField="id"
          onNewClick={() => setIsCreateOpen(true)}
          newButtonLabel="Create Voucher"
          onViewAccounting={(v) => setViewAccountingNumber(v.number)}
          onRowClick={(v) => setViewAccountingNumber(v.number)}
          filterPlaceholder="Search voucher number, payee, description..."
        />
      </div>

      {/* Right Rail */}
      <RightRail
        tasks={[
          { label: 'Create Petty Cash Voucher', onClick: () => setIsCreateOpen(true) },
          { label: 'Bank Reconciliation', onClick: () => onNavigate('#/cash/bank-reconciliation') },
          { label: 'Petty Cash Register Report', onClick: () => onNavigate('#/reports/petty-cash-register') },
        ]}
      />

      {/* Create Voucher Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={() => setIsCreateOpen(false)} />

          <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 max-w-lg w-full p-6 z-10 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <div>
                <h3 className="font-bold text-base text-gray-900">Create Petty Cash Voucher</h3>
                <p className="text-xs text-gray-500">Statutory Per-Voucher Imprest Cap: <strong>AED 1,000.00</strong></p>
              </div>
              <button onClick={() => setIsCreateOpen(false)} className="text-gray-400 hover:text-gray-600">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateVoucherSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Business Unit</label>
                  <select
                    value={voucherBU}
                    onChange={(e) => setVoucherBU(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded font-medium"
                  >
                    {BUSINESS_UNITS.map((b) => (
                      <option key={b.code} value={b.code}>
                        {b.code} - {b.name.replace('Meridian ', '')}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">
                    Disbursement Amount (AED) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={amountStr}
                    onChange={(e) => setAmountStr(e.target.value)}
                    placeholder="Max 1000.00"
                    className="w-full p-2 border border-gray-300 rounded font-mono font-bold"
                    required
                  />
                  <span className="text-[10px] text-gray-400 mt-0.5 block">Voucher cap: AED 1,000</span>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Payee / Recipient</label>
                <input
                  type="text"
                  value={payee}
                  onChange={(e) => setPayee(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded font-medium"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Expense Account</label>
                  <select
                    value={expenseAccount}
                    onChange={(e) => setExpenseAccount(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded font-mono"
                  >
                    <option value="6200">6200 - Office Supplies & Stationery</option>
                    <option value="6230">6230 - Travel and Transport</option>
                    <option value="6240">6240 - Hospitality and Staff Welfare</option>
                    <option value="6120">6120 - Repairs & Emergency Maintenance</option>
                    <option value="6290">6290 - Miscellaneous Expenses</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Tax Code</label>
                  <select
                    value={taxCode}
                    onChange={(e) => setTaxCode(e.target.value as any)}
                    className="w-full p-2 border border-gray-300 rounded"
                  >
                    <option value="STANDARD_5">VAT 5% Standard (Input)</option>
                    <option value="ZERO_0">VAT 0% Zero-rated</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Business Justification / Description</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded"
                  required
                />
              </div>

              <div className="pt-3 border-t border-gray-100 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg font-semibold"
                >
                  Submit Voucher &rarr;
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Approve Confirmation */}
      {approveTarget && (
        <ConfirmDialog
          isOpen={Boolean(approveTarget)}
          onClose={() => setApproveTarget(null)}
          onConfirm={handleApproveConfirm}
          title={`Approve Cash Voucher ${approveTarget.number}?`}
          message={`Disbursement of AED ${formatAED(
            approveTarget.amount
          )} to ${approveTarget.payee}. Will post Dr ${approveTarget.expenseAccount} / Dr 1400 / Cr 1010 Petty Cash.`}
          type="approve"
          confirmLabel="Approve & Post to GL"
        />
      )}

      {/* View Accounting */}
      {viewAccountingNumber && (
        <ViewAccountingModal
          isOpen={Boolean(viewAccountingNumber)}
          onClose={() => setViewAccountingNumber(null)}
          documentNumber={viewAccountingNumber}
          sourceModule="Cash Management"
          onNavigateToJournal={() => onNavigate('#/general-accounting/journals')}
        />
      )}
    </div>
  );
};
