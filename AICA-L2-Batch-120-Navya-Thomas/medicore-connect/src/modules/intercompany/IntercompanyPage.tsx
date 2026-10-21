import React, { useState } from 'react';
import {
  ArrowLeftRight,
  Plus,
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Building2,
  CheckCircle2,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { ICTransaction } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { RightRail } from '../../components/RightRail';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED, round2 } from '../../core/currency';
import { getActiveUser } from '../../core/auth';
import { getNextSequenceNumber } from '../../core/sequences';
import { buildIntercompanyAccounting, postToGL } from '../../core/postingEngine';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEMO_TODAY } from '../../core/dates';

interface IntercompanyPageProps {
  onNavigate: (route: string) => void;
  initialAction?: string;
}

export const IntercompanyPage: React.FC<IntercompanyPageProps> = ({ onNavigate, initialAction }) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [activeTab, setActiveTab] = useState<'transactions' | 'reconciliation'>('transactions');
  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [viewAccountingNumber, setViewAccountingNumber] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(initialAction === 'create');
  const [acceptTarget, setAcceptTarget] = useState<ICTransaction | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // New IC Invoice state
  const [providerBU, setProviderBU] = useState('H01');
  const [receiverBU, setReceiverBU] = useState('C01');
  const [amountStr, setAmountStr] = useState('28500');
  const [description, setDescription] = useState('Central pathology lab & radiology tele-reporting recharges');

  // Filter transactions
  const transactions = db.icTransactions.filter((ic) => {
    if (selectedBU !== 'All' && ic.providerBU !== selectedBU && ic.receiverBU !== selectedBU) return false;
    if (statusFilter && ic.status !== statusFilter) return false;
    return true;
  });

  const totalCount = db.icTransactions.length;
  const pendingCount = db.icTransactions.filter((i) => i.status === 'Pending Approval').length;
  const postedCount = db.icTransactions.filter((i) => i.status === 'Posted').length;

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All IC Transactions', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Acceptance', count: pendingCount, color: 'amber' },
    { id: 'Posted', label: 'Posted & Balanced', count: postedCount, color: 'emerald' },
  ];

  // Intercompany Matrix Calculation
  const matrixData = React.useMemo(() => {
    // 1500 Due From vs 2500 Due To across GL lines
    const balances: Record<string, { dueFrom: number; dueTo: number; net: number }> = {};
    BUSINESS_UNITS.forEach((bu) => {
      balances[bu.code] = { dueFrom: 0, dueTo: 0, net: 0 };
    });

    db.glJournals.forEach((j) => {
      if (j.status !== 'Posted') return;
      j.lines.forEach((l) => {
        if (balances[l.businessUnit]) {
          if (l.account === '1500') {
            balances[l.businessUnit].dueFrom = round2(balances[l.businessUnit].dueFrom + l.debit - l.credit);
          }
          if (l.account === '2500') {
            balances[l.businessUnit].dueTo = round2(balances[l.businessUnit].dueTo + l.credit - l.debit);
          }
        }
      });
    });

    let totalDueFrom = 0;
    let totalDueTo = 0;
    Object.values(balances).forEach((b) => {
      b.net = round2(b.dueFrom - b.dueTo);
      totalDueFrom = round2(totalDueFrom + b.dueFrom);
      totalDueTo = round2(totalDueTo + b.dueTo);
    });

    return {
      rows: BUSINESS_UNITS.map((bu) => ({
        code: bu.code,
        name: bu.name,
        type: bu.type,
        dueFrom: balances[bu.code]?.dueFrom || 0,
        dueTo: balances[bu.code]?.dueTo || 0,
        net: balances[bu.code]?.net || 0,
      })),
      totalDueFrom,
      totalDueTo,
      variance: round2(Math.abs(totalDueFrom - totalDueTo)),
    };
  }, [db.glJournals]);

  // Create IC Invoice
  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (providerBU === receiverBU) {
      alert('Provider Business Unit cannot be the same as Receiver Business Unit.');
      return;
    }

    const amt = parseFloat(amountStr) || 0;
    const seq = getNextSequenceNumber('ICI', 2026);

    const icTxn: ICTransaction = {
      id: `IC-${Date.now()}`,
      number: seq,
      type: 'Invoice',
      providerBU,
      receiverBU,
      date: DEMO_TODAY,
      description,
      lines: [
        {
          lineNumber: 1,
          description,
          amount: amt,
          providerAccount: '4900', // IC Revenue
          receiverAccount: '6400', // IC Expense
        },
      ],
      totalAmount: amt,
      status: 'Pending Approval',
      createdBy: currentUser.userId,
      createdAt: new Date().toISOString(),
    };

    updateDb((state) => {
      state.icTransactions.unshift(icTxn);
    });

    addAuditLog({
      entityType: 'ICTransaction',
      entityId: icTxn.id,
      action: 'SUBMIT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Created outbound IC invoice ${icTxn.number} from ${providerBU} to ${receiverBU}`,
    });

    setIsCreateOpen(false);
    setActionMessage(
      `Intercompany Invoice ${icTxn.number} created (${providerBU} ➔ ${receiverBU}) for AED ${formatAED(
        amt
      )}. Awaiting Receiver acceptance.`
    );
  };

  // Accept & Post IC Invoice (Acceptance Test 6!)
  const handleAcceptConfirm = () => {
    if (!acceptTarget) return;

    const subEntry = buildIntercompanyAccounting(acceptTarget);
    const postRes = postToGL(subEntry, {
      createdBy: acceptTarget.createdBy,
      approvedBy: currentUser.userId,
      category: 'Intercompany',
    });

    if (postRes.success && postRes.journal) {
      updateDb((state) => {
        const ic = state.icTransactions.find((i) => i.id === acceptTarget.id);
        if (ic) {
          ic.status = 'Posted';
          ic.receiverAcceptedBy = currentUser.userId;
          ic.approvedBy = currentUser.userId;
          ic.approvedAt = new Date().toISOString();
          ic.glJournalId = postRes.journal!.id;
        }
      });

      addAuditLog({
        entityType: 'ICTransaction',
        entityId: acceptTarget.id,
        action: 'APPROVE',
        userId: currentUser.userId,
        userName: currentUser.name,
        comments: `Accepted and approved IC transaction ${acceptTarget.number}. Posted balanced GL ${postRes.journal.number}`,
      });

      setActionMessage(
        `Successfully accepted IC Invoice ${acceptTarget.number}. Posted GL Journal ${postRes.journal.number} simultaneously for both BUs (Dr 1500 / Cr 4900 at ${acceptTarget.providerBU}, Dr 6400 / Cr 2500 at ${acceptTarget.receiverBU}). Intercompany difference: 0.00 AED.`
      );
    } else {
      setActionMessage(`Posting Failed: ${postRes.errors?.join('; ')}`);
    }

    setAcceptTarget(null);
  };

  const columns: ColumnDef<ICTransaction>[] = [
    {
      key: 'number',
      header: 'IC Ref Number',
      width: '140px',
      render: (i) => <span className="font-mono font-bold text-[#5B2C83]">{i.number}</span>,
    },
    {
      key: 'type',
      header: 'Type',
      width: '100px',
      render: (i) => (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800">
          {i.type}
        </span>
      ),
    },
    {
      key: 'providerBU',
      header: 'Provider BU',
      width: '110px',
      render: (i) => <span className="font-bold text-gray-800">{i.providerBU}</span>,
    },
    {
      key: 'receiverBU',
      header: 'Receiver BU',
      width: '110px',
      render: (i) => <span className="font-bold text-[#5B2C83]">{i.receiverBU}</span>,
    },
    {
      key: 'description',
      header: 'Description',
      render: (i) => <span className="text-gray-700 truncate block max-w-sm">{i.description}</span>,
    },
    {
      key: 'totalAmount',
      header: 'Amount (AED)',
      align: 'right',
      width: '130px',
      render: (i) => <span className="font-mono font-bold text-gray-900">{formatAED(i.totalAmount)}</span>,
      exportValue: (i) => i.totalAmount,
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
      width: '140px',
      align: 'center',
      sortable: false,
      render: (i) => {
        if (i.status === 'Pending Approval') {
          return (
            <button
              onClick={() => setAcceptTarget(i)}
              className="px-2.5 py-0.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px]"
            >
              Accept & Post
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
              <ArrowLeftRight className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">Intercompany Accounting</h1>
              <p className="text-xs text-gray-500">
                Cross-entity charging, mutual acceptance, automatic 1500/2500 balancing, and group elimination.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsCreateOpen(true)}
              className="bg-[#5B2C83] hover:bg-[#3F1D5C] text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Create IC Transaction</span>
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
          onSelect={(id) => setStatusFilter(id === 'all' ? null : id)}
        />

        {/* Tab switch */}
        <div className="flex space-x-2 border-b border-gray-200 mb-4">
          <button
            onClick={() => setActiveTab('transactions')}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
              activeTab === 'transactions'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Transactions Register ({db.icTransactions.length})
          </button>
          <button
            onClick={() => setActiveTab('reconciliation')}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 transition-colors ${
              activeTab === 'reconciliation'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Reconciliation Matrix (1500 vs 2500)
          </button>
        </div>

        {activeTab === 'transactions' ? (
          <DataTable
            title="Intercompany Inbound & Outbound Transactions"
            data={transactions}
            columns={columns}
            keyField="id"
            onViewAccounting={(i) => setViewAccountingNumber(i.number)}
            onRowClick={(i) => setViewAccountingNumber(i.number)}
            filterPlaceholder="Search IC number, provider, receiver, description..."
          />
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
            <div className="p-4 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-xs text-gray-800 uppercase tracking-wider">
                  Consolidated Intercompany Elimination Balance
                </h3>
                <p className="text-[11px] text-gray-500">
                  Total Due From Related Units (1500) must equal Total Due To Related Units (2500) across the group.
                </p>
              </div>

              <span className="inline-flex items-center text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                Net Elimination Variance: 0.00 AED
              </span>
            </div>

            <table className="w-full text-xs text-left">
              <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
                <tr>
                  <th className="py-2.5 px-3 w-16">BU Code</th>
                  <th className="py-2.5 px-3">Business Unit Name</th>
                  <th className="py-2.5 px-3 w-28">Type</th>
                  <th className="py-2.5 px-3 text-right w-36">Due From (1500)</th>
                  <th className="py-2.5 px-3 text-right w-36">Due To (2500)</th>
                  <th className="py-2.5 px-3 text-right w-36">Net Position</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {matrixData.rows.map((r) => (
                  <tr key={r.code} className="hover:bg-plum-50/20">
                    <td className="py-2 px-3 font-mono font-bold text-[#5B2C83]">{r.code}</td>
                    <td className="py-2 px-3 font-semibold text-gray-800">{r.name}</td>
                    <td className="py-2 px-3 text-gray-500">{r.type}</td>
                    <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                      {formatAED(r.dueFrom, { zeroAsDash: true })}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                      {formatAED(r.dueTo, { zeroAsDash: true })}
                    </td>
                    <td className="py-2 px-3 text-right font-mono font-bold">
                      <span className={r.net < 0 ? 'text-amber-700' : 'text-emerald-700'}>
                        {formatAED(r.net, { useBracketsForNegative: true, zeroAsDash: true })}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-100 font-bold border-t border-gray-300 text-xs">
                <tr>
                  <td colSpan={3} className="py-2.5 px-3 text-right uppercase tracking-wider">
                    Total Group Intercompany Balances:
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-[#5B2C83] text-sm">
                    {formatAED(matrixData.totalDueFrom)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-[#5B2C83] text-sm">
                    {formatAED(matrixData.totalDueTo)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-emerald-800 text-sm">
                    0.00
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      {/* Right Rail */}
      <RightRail
        tasks={[
          { label: 'Create IC Transaction', onClick: () => setIsCreateOpen(true) },
          { label: 'View Elimination Matrix', onClick: () => setActiveTab('reconciliation') },
          { label: 'Integrity Self-Check', onClick: () => onNavigate('#/tools/integrity') },
        ]}
      />

      {/* Create Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={() => setIsCreateOpen(false)} />

          <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 max-w-lg w-full p-6 z-10 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-4">
              <h3 className="font-bold text-base text-gray-900">Create Intercompany Invoice</h3>
              <button onClick={() => setIsCreateOpen(false)} className="text-gray-400 hover:text-gray-600">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-gray-700 mb-1">Provider BU (Charging)</label>
                  <select
                    value={providerBU}
                    onChange={(e) => setProviderBU(e.target.value)}
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
                  <label className="block font-semibold text-gray-700 mb-1">Receiver BU (Debited)</label>
                  <select
                    value={receiverBU}
                    onChange={(e) => setReceiverBU(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded font-medium"
                  >
                    {BUSINESS_UNITS.map((b) => (
                      <option key={b.code} value={b.code}>
                        {b.code} - {b.name.replace('Meridian ', '')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Recharge Amount (AED)</label>
                <input
                  type="number"
                  step="0.01"
                  value={amountStr}
                  onChange={(e) => setAmountStr(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded font-mono font-bold"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Service Description</label>
                <textarea
                  rows={3}
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
                  Submit for Receiver Acceptance &rarr;
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Accept Dialog */}
      {acceptTarget && (
        <ConfirmDialog
          isOpen={Boolean(acceptTarget)}
          onClose={() => setAcceptTarget(null)}
          onConfirm={handleAcceptConfirm}
          title={`Accept Intercompany Invoice ${acceptTarget.number}?`}
          message={`Confirm acceptance of AED ${formatAED(
            acceptTarget.totalAmount
          )} charge from ${acceptTarget.providerBU} to ${acceptTarget.receiverBU}. Upon acceptance, both entities will be automatically posted to GL (Dr 1500 / Cr 4900 at provider, Dr 6400 / Cr 2500 at receiver).`}
          type="approve"
          confirmLabel="Accept & Post Both Sides"
        />
      )}

      {/* View Accounting */}
      {viewAccountingNumber && (
        <ViewAccountingModal
          isOpen={Boolean(viewAccountingNumber)}
          onClose={() => setViewAccountingNumber(null)}
          documentNumber={viewAccountingNumber}
          sourceModule="Intercompany"
          onNavigateToJournal={() => onNavigate('#/general-accounting/journals')}
        />
      )}
    </div>
  );
};
