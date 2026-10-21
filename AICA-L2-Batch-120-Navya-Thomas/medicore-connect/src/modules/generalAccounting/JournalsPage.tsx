import React, { useState } from 'react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { GLJournal, SubledgerEntry } from '../../core/types';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { SummaryTiles, SummaryTileItem } from '../../components/SummaryTiles';
import { TableFilterBar } from '../../components/TableFilterBar';
import { ModuleAccessBanner } from '../../components/ModuleAccessBanner';
import { DocLink } from '../../components/DocLink';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { formatAED, round2, addMoney } from '../../core/currency';
import { getActiveUser, checkMakerPermission, checkCanApprove } from '../../core/auth';
import { reverseJournal, postToGL } from '../../core/postingEngine';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { useTableFilters } from '../../core/useTableFilters';
import {
  Undo2,
  Plus,
  Eye,
  BookOpen,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  CheckSquare,
  ShieldCheck,
  Send,
  Lock,
} from 'lucide-react';
import { CreateJournalModal } from './CreateJournalModal';

interface JournalsPageProps {
  onNavigate: (route: string) => void;
}

export const JournalsPage: React.FC<JournalsPageProps> = ({ onNavigate }) => {
  const db = getDb();
  const currentUser = getActiveUser();
  const allJournals = db.glJournals || [];

  const makerCheck = checkMakerPermission(currentUser, 'General Accounting');
  const approverCheck = checkCanApprove(currentUser, { createdBy: 'charlotte.davis' }, 'General Accounting');

  const [activeTab, setActiveTab] = useState<'all' | 'approvals'>('all');
  const [selectedJournal, setSelectedJournal] = useState<GLJournal | null>(null);
  const [viewAccountingNumber, setViewAccountingNumber] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [reverseTarget, setReverseTarget] = useState<GLJournal | null>(null);
  const [rejectTarget, setRejectTarget] = useState<GLJournal | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Selected journals for bulk actions in approvals queue
  const [selectedJvIds, setSelectedJvIds] = useState<string[]>([]);

  // Filter Engine
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
  } = useTableFilters(allJournals, {
    searchFields: ['number', 'description', 'sourceModule', 'category', 'createdBy', 'approvedBy'],
    dateField: 'journalDate',
    amountField: 'totalDebit',
    statusField: 'status',
    buField: 'businessUnit',
  });

  // Summary counts
  const draftCount = allJournals.filter((j) => j.status === 'Draft').length;
  const pendingCount = allJournals.filter((j) => j.status === 'Pending Approval').length;
  const approvedCount = allJournals.filter((j) => j.status === 'Approved').length;
  const postedCount = allJournals.filter((j) => j.status === 'Posted').length;
  const rejectedCount = allJournals.filter((j) => j.status === 'Rejected').length;
  const reversedCount = allJournals.filter((j) => j.status === 'Reversed').length;

  const summaryTiles: SummaryTileItem[] = [
    { id: 'all', label: 'All Journals', count: totalCount },
    { id: 'Pending Approval', label: 'Pending Approval', count: pendingCount, color: 'amber' },
    { id: 'Posted', label: 'Posted to GL', count: postedCount, color: 'emerald' },
    { id: 'Draft', label: 'Drafts', count: draftCount, color: 'slate' },
    { id: 'Rejected', label: 'Rejected', count: rejectedCount, color: 'rose' },
    { id: 'Reversed', label: 'Reversed', count: reversedCount, color: 'purple' },
  ];

  const handleTileSelect = (id: string | null) => {
    if (!id || id === 'all') setSelectedStatus('');
    else setSelectedStatus(id);
  };

  // Approve manual journal (Daniel Reed)
  const handleApproveJournal = (journal: GLJournal) => {
    if (!approverCheck.allowed) {
      setActionMessage(approverCheck.reason || 'Only the General Accounting Approver (Daniel Reed) can approve manual journals.');
      return;
    }

    // Segregation of duties: cannot approve own journal
    if (journal.createdBy && journal.createdBy.toLowerCase() === currentUser.userId.toLowerCase()) {
      setActionMessage('Segregation of duties violation: You cannot approve a journal entry that you created.');
      return;
    }

    updateDb((state) => {
      const target = state.glJournals.find((j) => j.id === journal.id);
      if (target) {
        target.status = 'Posted';
        target.approvedBy = currentUser.userId;
        target.approvedAt = new Date().toISOString();
        target.postedAt = new Date().toISOString();
      }
    });

    addAuditLog({
      entityType: 'GLJournal',
      entityId: journal.id,
      action: 'APPROVE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Approved manual general journal ${journal.number} for posting to General Ledger.`,
      details: { totalAmount: journal.totalDebit, period: journal.period },
    });

    setActionMessage(`Journal ${journal.number} has been approved and successfully posted to the General Ledger!`);
  };

  // Reject manual journal (Daniel Reed)
  const handleRejectConfirm = (reason?: string) => {
    if (!rejectTarget) return;

    if (!approverCheck.allowed) {
      setActionMessage('Only Daniel Reed can reject manual journals.');
      setRejectTarget(null);
      return;
    }

    const mandatoryReason = reason?.trim() || 'Returned to Maker for adjustment';

    updateDb((state) => {
      const target = state.glJournals.find((j) => j.id === rejectTarget.id);
      if (target) {
        target.status = 'Rejected';
        target.rejectionReason = mandatoryReason;
        target.approvedBy = currentUser.userId;
      }
    });

    addAuditLog({
      entityType: 'GLJournal',
      entityId: rejectTarget.id,
      action: 'REJECT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Rejected manual journal ${rejectTarget.number}. Reason: ${mandatoryReason}`,
    });

    setActionMessage(`Journal ${rejectTarget.number} was rejected and returned to Charlotte Davis with reason.`);
    setRejectTarget(null);
  };

  // Bulk Approve pending journals
  const handleBulkApprove = () => {
    if (!approverCheck.allowed) {
      setActionMessage('Only Daniel Reed can approve journals.');
      return;
    }

    if (selectedJvIds.length === 0) return;

    let approvedCount = 0;
    updateDb((state) => {
      selectedJvIds.forEach((id) => {
        const j = state.glJournals.find((x) => x.id === id);
        if (j && j.status === 'Pending Approval') {
          if (j.createdBy?.toLowerCase() !== currentUser.userId.toLowerCase()) {
            j.status = 'Posted';
            j.approvedBy = currentUser.userId;
            j.approvedAt = new Date().toISOString();
            j.postedAt = new Date().toISOString();
            approvedCount++;
          }
        }
      });
    });

    addAuditLog({
      entityType: 'GLJournal',
      entityId: 'BULK',
      action: 'APPROVE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Bulk approved ${approvedCount} general ledger journals.`,
    });

    setActionMessage(`Successfully bulk-approved and posted ${approvedCount} journals to the General Ledger.`);
    setSelectedJvIds([]);
  };

  // Reverse journal handler
  const handleReverseConfirm = (reason?: string) => {
    if (!reverseTarget) return;

    if (!makerCheck.allowed && !approverCheck.allowed) {
      setActionMessage('Only General Accounting authorized users can reverse journals.');
      setReverseTarget(null);
      return;
    }

    const res = reverseJournal(
      reverseTarget.id,
      reason || 'User requested reversal',
      '2026-10-19',
      currentUser.userId
    );

    if (res.success) {
      setActionMessage(`Successfully reversed journal ${reverseTarget.number} via reversal journal ${res.reversedJournal?.number}.`);
    } else {
      setActionMessage(`Reversal failed: ${res.error}`);
    }
    setReverseTarget(null);
  };

  const columns: ColumnDef<GLJournal>[] = [
    {
      key: 'number',
      header: 'Journal Number',
      width: '140px',
      render: (j) => <DocLink number={j.number} />,
    },
    {
      key: 'period',
      header: 'Period',
      width: '80px',
      render: (j) => <span className="font-semibold text-gray-800">{j.period}</span>,
    },
    {
      key: 'journalDate',
      header: 'Date',
      width: '100px',
    },
    {
      key: 'businessUnit',
      header: 'Business Unit',
      width: '100px',
      render: (j) => <span className="font-medium text-gray-700">{j.businessUnit}</span>,
    },
    {
      key: 'sourceModule',
      header: 'Source Module',
      width: '140px',
      render: (j) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-plum-50 text-[#5B2C83] border border-plum-200">
          {j.sourceModule}
        </span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: (j) => (
        <div>
          <span className="text-gray-900 truncate block max-w-xs">{j.description}</span>
          {j.lines[0]?.sourceDocumentNumber && (
            <span className="text-[10px] text-gray-500">
              Source:{' '}
              <DocLink number={j.lines[0].sourceDocumentNumber} />
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'totalDebit',
      header: 'Debit (AED)',
      align: 'right',
      width: '120px',
      render: (j) => <span className="font-mono font-semibold">{formatAED(j.totalDebit)}</span>,
    },
    {
      key: 'totalCredit',
      header: 'Credit (AED)',
      align: 'right',
      width: '120px',
      render: (j) => <span className="font-mono font-semibold">{formatAED(j.totalCredit)}</span>,
    },
    {
      key: 'status',
      header: 'Status & Approval',
      width: '150px',
      align: 'center',
      render: (j) => {
        const isSubledger = j.sourceModule !== 'Manual' && j.sourceModule !== 'Opening Balances';
        return (
          <div className="flex flex-col items-center">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                j.status === 'Posted'
                  ? 'bg-emerald-100 text-emerald-800'
                  : j.status === 'Pending Approval'
                  ? 'bg-amber-100 text-amber-800 animate-pulse'
                  : j.status === 'Draft'
                  ? 'bg-gray-100 text-gray-700'
                  : j.status === 'Rejected'
                  ? 'bg-rose-100 text-rose-800'
                  : 'bg-purple-100 text-purple-800'
              }`}
            >
              {j.status}
            </span>
            {isSubledger && j.lines[0]?.sourceDocumentNumber ? (
              <span className="text-[9px] text-gray-500 truncate max-w-[130px] mt-0.5">
                Approved at source: {j.lines[0].sourceDocumentNumber}
              </span>
            ) : j.approvedBy ? (
              <span className="text-[9px] text-gray-500 mt-0.5">
                By: {j.approvedBy}
              </span>
            ) : null}
          </div>
        );
      },
    },
    {
      key: 'actions' as any,
      header: 'Actions',
      width: '120px',
      align: 'center',
      render: (j) => {
        const canApproveThis =
          j.status === 'Pending Approval' &&
          approverCheck.allowed &&
          j.createdBy?.toLowerCase() !== currentUser.userId.toLowerCase();

        return (
          <div className="flex items-center justify-center space-x-1.5">
            <button
              onClick={() => setSelectedJournal(j)}
              title="View Journal Lines"
              className="p-1 rounded text-gray-600 hover:text-[#5B2C83] hover:bg-plum-50 cursor-pointer"
            >
              <Eye className="w-3.5 h-3.5" />
            </button>

            {canApproveThis && (
              <>
                <button
                  onClick={() => handleApproveJournal(j)}
                  title="Approve Journal to Post"
                  className="p-1 rounded text-emerald-600 hover:bg-emerald-50 cursor-pointer"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setRejectTarget(j)}
                  title="Reject Journal"
                  className="p-1 rounded text-rose-600 hover:bg-rose-50 cursor-pointer"
                >
                  <XCircle className="w-3.5 h-3.5" />
                </button>
              </>
            )}

            {j.status === 'Posted' && (
              <button
                onClick={() => setReverseTarget(j)}
                title="Reverse Journal"
                className="p-1 rounded text-gray-400 hover:text-purple-700 hover:bg-purple-50 cursor-pointer"
              >
                <Undo2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        );
      },
    },
  ];

  const pendingApprovalsList = allJournals.filter((j) => j.status === 'Pending Approval');

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <BookOpen className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">General Ledger Journals</h1>
            <p className="text-xs text-gray-500">
              Audit-compliant general ledger entries, multi-BU posting and Maker–Checker segregation
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {makerCheck.allowed ? (
            <button
              onClick={() => setIsCreateOpen(true)}
              className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4 text-amber-300" />
              <span>Create Journal</span>
            </button>
          ) : (
            <span
              title={makerCheck.reason}
              className="px-4 py-2 bg-gray-200 text-gray-500 rounded-lg text-xs font-semibold flex items-center space-x-1.5 cursor-not-allowed opacity-70"
            >
              <Lock className="w-4 h-4" />
              <span>Create Journal (Locked)</span>
            </span>
          )}
        </div>
      </div>

      {/* Access Banner */}
      <div className="mb-4">
        <ModuleAccessBanner module="General Accounting" />
      </div>

      {/* Action Toast */}
      {actionMessage && (
        <div className="mb-4 p-3 rounded-lg bg-plum-50 border border-plum-200 text-[#3F1D5C] text-xs flex items-center justify-between shadow-xs">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-gray-500 hover:text-gray-800 font-bold ml-2">
            ×
          </button>
        </div>
      )}

      {/* View Tabs: All Journals vs Manage Approvals */}
      <div className="flex items-center justify-between border-b border-gray-200 mb-4">
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveTab('all')}
            className={`pb-2.5 text-xs font-bold border-b-2 flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeTab === 'all'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>All Journals ({totalCount})</span>
          </button>
          <button
            onClick={() => setActiveTab('approvals')}
            className={`pb-2.5 text-xs font-bold border-b-2 flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeTab === 'approvals'
                ? 'border-[#5B2C83] text-[#5B2C83]'
                : 'border-transparent text-gray-500 hover:text-gray-800'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Manage Approvals ({pendingCount})</span>
            {pendingCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-amber-400 text-amber-950 font-bold text-[10px]">
                {pendingCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* TAB 1: ALL JOURNALS */}
      {activeTab === 'all' && (
        <>
          {/* Summary Tiles acting as filters */}
          <SummaryTiles
            items={summaryTiles}
            selectedId={selectedStatus || 'all'}
            onSelect={handleTileSelect}
          />

          {/* Table Filter Bar */}
          <TableFilterBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            searchPlaceholder="Search journal number, description, category, creator..."
            selectedStatus={selectedStatus}
            onStatusChange={setSelectedStatus}
            statusOptions={uniqueStatuses}
            selectedBU={selectedBU}
            onBUChange={setSelectedBU}
            buOptions={uniqueBUs}
            dateFrom={dateFrom}
            onDateFromChange={setDateFrom}
            dateTo={dateTo}
            onDateToChange={setDateTo}
            activeChips={activeFilterChips}
            onClearAll={clearAllFilters}
            totalCount={totalCount}
            filteredCount={filteredCount}
          />

          {/* DataTable */}
          <div className="bg-white rounded-xl shadow-xs border border-gray-200 overflow-hidden">
            <DataTable
              data={filteredData}
              columns={columns}
              rowKey="id"
              emptyMessage="No general ledger journals match your active filters."
            />
          </div>
        </>
      )}

      {/* TAB 2: MANAGE APPROVALS QUEUE */}
      {activeTab === 'approvals' && (
        <div className="space-y-4">
          <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-2 text-amber-900">
              <Clock className="w-5 h-5 text-amber-600 shrink-0" />
              <div>
                <strong className="block">Journals Awaiting Authorized Checker Approval</strong>
                <span className="text-amber-800">
                  Manual journals do not affect GL balances or financial reports until approved by the General Accounting Approver (Daniel Reed).
                </span>
              </div>
            </div>

            {approverCheck.allowed && selectedJvIds.length > 0 && (
              <button
                onClick={handleBulkApprove}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg shadow-xs flex items-center space-x-1.5 cursor-pointer"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Bulk Approve Selected ({selectedJvIds.length})</span>
              </button>
            )}
          </div>

          {pendingApprovalsList.length === 0 ? (
            <div className="bg-white p-12 text-center rounded-xl border border-dashed border-gray-300">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
              <h3 className="font-semibold text-gray-800 text-sm">Approvals Queue is Clear</h3>
              <p className="text-xs text-gray-500 mt-1">
                There are no manual journals currently awaiting checker authorization.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingApprovalsList.map((journal) => {
                const isCreator = journal.createdBy?.toLowerCase() === currentUser.userId.toLowerCase();
                const canApprove = approverCheck.allowed && !isCreator;

                return (
                  <div
                    key={journal.id}
                    className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden"
                  >
                    {/* Header */}
                    <div className="px-5 py-3.5 bg-gray-50/80 border-b border-gray-200 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          checked={selectedJvIds.includes(journal.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedJvIds([...selectedJvIds, journal.id]);
                            } else {
                              setSelectedJvIds(selectedJvIds.filter((id) => id !== journal.id));
                            }
                          }}
                          className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
                        />
                        <DocLink number={journal.number} className="font-bold text-sm" />
                        <span className="font-semibold text-xs text-gray-900">{journal.description}</span>
                        <span className="font-mono text-xs text-[#5B2C83] px-2 py-0.5 rounded bg-plum-100 font-semibold">
                          {journal.businessUnit}
                        </span>
                        <span className="text-xs text-gray-500">Period: {journal.period}</span>
                      </div>

                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <span className="text-[10px] text-gray-400 block uppercase font-semibold">Amount</span>
                          <span className="font-mono font-bold text-xs text-gray-900">
                            AED {formatAED(journal.totalDebit)}
                          </span>
                        </div>

                        <div className="flex items-center space-x-2">
                          {canApprove ? (
                            <>
                              <button
                                onClick={() => handleApproveJournal(journal)}
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg flex items-center space-x-1 cursor-pointer"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>Approve & Post</span>
                              </button>
                              <button
                                onClick={() => setRejectTarget(journal)}
                                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg flex items-center space-x-1 cursor-pointer"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                                <span>Reject</span>
                              </button>
                            </>
                          ) : isCreator ? (
                            <span className="text-[11px] text-gray-500 italic px-2 py-1 bg-gray-100 rounded">
                              Created by you (Segregation of Duties)
                            </span>
                          ) : (
                            <span className="text-[11px] text-gray-400 italic">
                              Awaiting Daniel Reed
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Lines Preview */}
                    <div className="p-4 overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold">
                          <tr>
                            <th className="py-2 px-3 w-12 text-center">#</th>
                            <th className="py-2 px-3 w-16">BU</th>
                            <th className="py-2 px-3 w-28">Account</th>
                            <th className="py-2 px-3">Description</th>
                            <th className="py-2 px-3 w-24">Department</th>
                            <th className="py-2 px-3 text-right w-28">Debit (AED)</th>
                            <th className="py-2 px-3 text-right w-28">Credit (AED)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {journal.lines.map((line, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="py-1.5 px-3 text-center text-gray-400">{idx + 1}</td>
                              <td className="py-1.5 px-3 font-semibold text-gray-700">{line.businessUnit}</td>
                              <td className="py-1.5 px-3 font-mono font-medium text-[#5B2C83]">{line.account}</td>
                              <td className="py-1.5 px-3 text-gray-800">{line.description}</td>
                              <td className="py-1.5 px-3 text-gray-600">{line.department || '—'}</td>
                              <td className="py-1.5 px-3 text-right font-mono font-medium text-gray-900">
                                {line.debit > 0 ? formatAED(line.debit) : '—'}
                              </td>
                              <td className="py-1.5 px-3 text-right font-mono font-medium text-gray-900">
                                {line.credit > 0 ? formatAED(line.credit) : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Create Journal Modal */}
      <CreateJournalModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={(j) => {
          setIsCreateOpen(false);
          setActionMessage(
            `Journal ${j.number} created with status '${j.status}'. ${
              j.status === 'Pending Approval' ? 'Submitted to Daniel Reed for approval.' : 'Saved as draft.'
            }`
          );
        }}
      />

      {/* Lines Preview Modal */}
      {selectedJournal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={() => setSelectedJournal(null)} />
          <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-4xl max-h-[90vh] flex flex-col z-10 animate-in zoom-in-95 duration-150">
            <div className="bg-[#3F1D5C] text-white px-6 py-4 rounded-t-xl flex items-center justify-between">
              <div>
                <h3 className="font-bold text-base">
                  Journal Lines: <span className="font-mono text-amber-300">{selectedJournal.number}</span>
                </h3>
                <p className="text-xs text-plum-200">
                  {selectedJournal.description} | Status: <strong className="text-white">{selectedJournal.status}</strong>
                </p>
              </div>
              <button onClick={() => setSelectedJournal(null)} className="text-gray-200 hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <table className="w-full text-xs text-left border border-gray-200 rounded-lg overflow-hidden">
                <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold">
                  <tr>
                    <th className="py-2.5 px-3 w-12 text-center">#</th>
                    <th className="py-2.5 px-3 w-16">BU</th>
                    <th className="py-2.5 px-3 w-28">Account</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3 w-24">Department</th>
                    <th className="py-2.5 px-3 text-right w-28">Debit (AED)</th>
                    <th className="py-2.5 px-3 text-right w-28">Credit (AED)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {selectedJournal.lines.map((l, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="py-2 px-3 text-center text-gray-400">{idx + 1}</td>
                      <td className="py-2 px-3 font-semibold text-gray-700">{l.businessUnit}</td>
                      <td className="py-2 px-3 font-mono font-medium text-[#5B2C83]">{l.account}</td>
                      <td className="py-2 px-3 text-gray-800">{l.description}</td>
                      <td className="py-2 px-3 text-gray-600">{l.department || '—'}</td>
                      <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                        {l.debit > 0 ? formatAED(l.debit) : '—'}
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                        {l.credit > 0 ? formatAED(l.credit) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-50 font-bold border-t border-gray-200">
                  <tr>
                    <td colSpan={5} className="py-2.5 px-3 text-right text-gray-700">
                      Total:
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-900">
                      AED {formatAED(selectedJournal.totalDebit)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-gray-900">
                      AED {formatAED(selectedJournal.totalCredit)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Reverse Confirm Dialog */}
      <ConfirmDialog
        isOpen={Boolean(reverseTarget)}
        title={`Reverse Journal ${reverseTarget?.number}`}
        message={`Are you sure you want to reverse journal ${reverseTarget?.number}? This will generate an offsetting reversal general journal.`}
        confirmLabel="Confirm Reversal"
        cancelLabel="Cancel"
        requireReason={true}
        onConfirm={handleReverseConfirm}
        onCancel={() => setReverseTarget(null)}
      />

      {/* Reject Confirm Dialog */}
      <ConfirmDialog
        isOpen={Boolean(rejectTarget)}
        title={`Reject Journal ${rejectTarget?.number}`}
        message={`Are you sure you want to reject journal ${rejectTarget?.number}? Please provide a mandatory reason for the rejection.`}
        confirmLabel="Reject Journal"
        confirmVariant="danger"
        cancelLabel="Cancel"
        requireReason={true}
        onConfirm={handleRejectConfirm}
        onCancel={() => setRejectTarget(null)}
      />
    </div>
  );
};
