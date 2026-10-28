import React, { useState } from 'react';
import { X, Plus, Trash2, AlertCircle, CheckCircle2, BookOpen } from 'lucide-react';
import { CHART_OF_ACCOUNTS } from '../../data/chartOfAccounts';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { DEPARTMENTS } from '../../data/chartOfAccounts';
import { getActiveUser } from '../../core/auth';
import { postToGL } from '../../core/postingEngine';
import { GLJournal, SubledgerEntry } from '../../core/types';
import { round2, addMoney, formatAED } from '../../core/currency';
import { getPeriodFromDate, DEMO_TODAY } from '../../core/dates';
import { checkDatePeriodStatus } from '../../core/periods';

interface CreateJournalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (journal: GLJournal) => void;
}

interface FormLine {
  id: string;
  businessUnit: string;
  account: string;
  department: string;
  debit: string;
  credit: string;
  description: string;
}

export const CreateJournalModal: React.FC<CreateJournalModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const currentUser = getActiveUser();

  const [date, setDate] = useState(DEMO_TODAY);
  const [category, setCategory] = useState('Manual Accrual');
  const [description, setDescription] = useState('');
  const [isReversing, setIsReversing] = useState(false);
  const [reversalDate, setReversalDate] = useState('2026-11-01');
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const [lines, setLines] = useState<FormLine[]>([
    {
      id: '1',
      businessUnit: 'H01',
      account: '6250', // Professional and Consulting Fees
      department: 'Administration',
      debit: '15000',
      credit: '',
      description: 'Monthly clinical advisory consulting fee accrual',
    },
    {
      id: '2',
      businessUnit: 'H01',
      account: '2020', // Accrued Expenses
      department: 'Administration',
      debit: '',
      credit: '15000',
      description: 'Accrued expenses month-end provision',
    },
  ]);

  if (!isOpen) return null;

  const handleAddLine = () => {
    setLines([
      ...lines,
      {
        id: String(Date.now()),
        businessUnit: lines[lines.length - 1]?.businessUnit || 'H01',
        account: '',
        department: 'Administration',
        debit: '',
        credit: '',
        description: description || 'Journal line',
      },
    ]);
  };

  const handleRemoveLine = (idx: number) => {
    if (lines.length <= 2) {
      setErrorBanner('Journals must contain at least 2 lines.');
      return;
    }
    const updated = [...lines];
    updated.splice(idx, 1);
    setLines(updated);
  };

  const updateLine = (idx: number, field: keyof FormLine, value: string) => {
    const updated = [...lines];
    updated[idx] = { ...updated[idx], [field]: value };
    // Clear debit if entering credit and vice versa
    if (field === 'debit' && value) updated[idx].credit = '';
    if (field === 'credit' && value) updated[idx].debit = '';
    setLines(updated);
    if (errorBanner) setErrorBanner(null);
  };

  // Balance calculation
  let totalDebit = 0;
  let totalCredit = 0;
  lines.forEach((l) => {
    totalDebit = addMoney(totalDebit, parseFloat(l.debit) || 0);
    totalCredit = addMoney(totalCredit, parseFloat(l.credit) || 0);
  });
  const difference = round2(Math.abs(totalDebit - totalCredit));
  const isBalanced = difference === 0 && totalDebit > 0;

  const handleSave = (asDraft: boolean) => {
    setErrorBanner(null);

    // Maker check
    const isMaker = currentUser.userId.toLowerCase() === 'charlotte.davis' || currentUser.role === 'Finance Controller';
    if (!isMaker) {
      setErrorBanner('Only the General Accounting Maker (Charlotte Davis) is authorized to create and submit manual journals.');
      return;
    }

    // 1. Period check
    const periodCheck = checkDatePeriodStatus(date);
    if (!periodCheck.isOpen) {
      setErrorBanner(periodCheck.error || `Period for date ${date} is not open for manual posting.`);
      return;
    }

    if (!isBalanced) {
      setErrorBanner(`Journal is out of balance by AED ${difference.toFixed(2)}. Debits must equal Credits.`);
      return;
    }

    // 2. Control account validation
    for (let i = 0; i < lines.length; i++) {
      const l = lines[i];
      if (!l.account) {
        setErrorBanner(`Line ${i + 1}: Account must be selected.`);
        return;
      }
      const acct = CHART_OF_ACCOUNTS.find((a) => a.code === l.account);
      if (acct?.isControlAccount) {
        setErrorBanner(
          `Line ${i + 1}: Account '${l.account} - ${acct.name}' is a Subledger Control Account and is strictly blocked from manual journals.`
        );
        return;
      }
    }

    const uniqueBUs = Array.from(new Set(lines.map((l) => l.businessUnit)));
    const buDisplay = uniqueBUs.length === 1 ? uniqueBUs[0] : 'Multi-BU';
    const jvNumber = getNextSequenceNumber('JV', 2026);
    const period = getPeriodFromDate(date);
    const nowIso = new Date().toISOString();

    const glLines = lines.map((l, idx) => ({
      lineNumber: idx + 1,
      businessUnit: l.businessUnit,
      account: l.account,
      department: l.department,
      debit: parseFloat(l.debit) || 0,
      credit: parseFloat(l.credit) || 0,
      description: l.description || description,
      sourceModule: 'Manual',
      sourceDocumentNumber: jvNumber,
      sourceDocumentId: `MAN-${Date.now()}`,
    }));

    const newJournal: GLJournal = {
      id: `GLJ-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      number: jvNumber,
      period,
      journalDate: date,
      businessUnit: buDisplay,
      sourceModule: 'Manual',
      category,
      description: description || 'Manual General Journal Entry',
      status: asDraft ? 'Draft' : 'Pending Approval',
      totalDebit,
      totalCredit,
      lines: glLines,
      createdBy: currentUser.userId,
      createdAt: nowIso,
      submittedAt: !asDraft ? nowIso : undefined,
    };

    updateDb((state) => {
      if (!state.glJournals) state.glJournals = [];
      state.glJournals.unshift(newJournal);
    });

    addAuditLog({
      entityType: 'GLJournal',
      entityId: newJournal.id,
      action: asDraft ? 'CREATE' : 'SUBMIT',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `${asDraft ? 'Created Draft' : 'Submitted for Approval'} Manual General Journal ${newJournal.number} (AED ${formatAED(totalDebit)})`,
      details: { totalAmount: totalDebit, period, status: newJournal.status },
    });

    onCreated(newJournal);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSave(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={onClose} />

      <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-5xl max-h-[92vh] flex flex-col z-10 animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-[#3F1D5C] text-white px-6 py-4 rounded-t-xl flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-amber-300" />
            <div>
              <h2 className="font-bold text-base">Create Manual Journal Entry</h2>
              <p className="text-xs text-plum-200">
                Period: <strong className="text-white">{getPeriodFromDate(date)}</strong> | Currency: AED
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-[#5B2C83] text-gray-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 flex flex-col justify-between">
          <div>
            {errorBanner && (
              <div className="mb-4 p-3 bg-rose-50 border border-rose-300 text-rose-800 rounded-lg text-xs flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{errorBanner}</span>
              </div>
            )}

            {/* Header fields */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-5 p-4 bg-gray-50 rounded-lg border border-gray-200 text-xs">
              <div>
                <label className="block font-semibold text-gray-700 mb-1">
                  Accounting Date <span className="text-rose-500">*</span>
                </label>
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Journal Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
                >
                  <option value="Manual Accrual">Manual Accrual</option>
                  <option value="Adjustment">Adjustment / Reclassification</option>
                  <option value="Provision">Provision & ECL</option>
                  <option value="Tax Allocation">Tax Allocation</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block font-semibold text-gray-700 mb-1">
                  Header Description <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Monthly medical consulting fee accrual for hospital"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
                  required
                />
              </div>
            </div>

            {/* Lines Table */}
            <div className="border border-gray-200 rounded-lg overflow-hidden mb-4">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
                  <tr>
                    <th className="py-2.5 px-3 w-10 text-center">#</th>
                    <th className="py-2.5 px-3 w-36">Business Unit</th>
                    <th className="py-2.5 px-3 w-64">Account (Non-Control)</th>
                    <th className="py-2.5 px-3 w-32">Department</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3 text-right w-28">Debit (AED)</th>
                    <th className="py-2.5 px-3 text-right w-28">Credit (AED)</th>
                    <th className="py-2.5 px-2 w-10 text-center"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {lines.map((line, idx) => (
                    <tr key={line.id} className="hover:bg-plum-50/30">
                      <td className="py-2 px-3 text-center text-gray-400 font-semibold">{idx + 1}</td>
                      <td className="py-2 px-2">
                        <select
                          value={line.businessUnit}
                          onChange={(e) => updateLine(idx, 'businessUnit', e.target.value)}
                          className="w-full p-1.5 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83]"
                        >
                          {BUSINESS_UNITS.map((b) => (
                            <option key={b.code} value={b.code}>
                              {b.code} - {b.name.replace('Meridian ', '')}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-2">
                        <select
                          value={line.account}
                          onChange={(e) => updateLine(idx, 'account', e.target.value)}
                          className="w-full p-1.5 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83]"
                          required
                        >
                          <option value="">Select Account...</option>
                          {CHART_OF_ACCOUNTS.map((a) => (
                            <option
                              key={a.code}
                              value={a.code}
                              disabled={a.isControlAccount}
                              className={a.isControlAccount ? 'text-gray-400 italic' : ''}
                            >
                              {a.code} - {a.name} {a.isControlAccount ? '(Control - Blocked)' : ''}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-2">
                        <select
                          value={line.department}
                          onChange={(e) => updateLine(idx, 'department', e.target.value)}
                          className="w-full p-1.5 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-[#5B2C83]"
                        >
                          {DEPARTMENTS.map((d) => (
                            <option key={d} value={d}>
                              {d}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={line.description}
                          onChange={(e) => updateLine(idx, 'description', e.target.value)}
                          placeholder="Line description"
                          className="w-full p-1.5 border border-gray-300 rounded text-xs"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={line.debit}
                          onChange={(e) => updateLine(idx, 'debit', e.target.value)}
                          placeholder="0.00"
                          className="w-full p-1.5 border border-gray-300 rounded text-xs text-right font-mono"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={line.credit}
                          onChange={(e) => updateLine(idx, 'credit', e.target.value)}
                          placeholder="0.00"
                          className="w-full p-1.5 border border-gray-300 rounded text-xs text-right font-mono"
                        />
                      </td>
                      <td className="py-2 px-2 text-center">
                        <button
                          type="button"
                          onClick={() => handleRemoveLine(idx)}
                          title="Remove line"
                          className="p-1 text-gray-400 hover:text-rose-600 rounded"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-100 font-bold border-t border-gray-300">
                  <tr>
                    <td colSpan={5} className="py-2 px-3 text-right text-gray-700">
                      Total Debits / Credits:
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-emerald-800 text-sm">
                      {formatAED(totalDebit)}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-emerald-800 text-sm">
                      {formatAED(totalCredit)}
                    </td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="flex items-center justify-between mb-4">
              <button
                type="button"
                onClick={handleAddLine}
                className="px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold flex items-center space-x-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Distribution Line</span>
              </button>

              <div className="text-xs">
                {isBalanced ? (
                  <span className="flex items-center text-emerald-700 font-bold">
                    <CheckCircle2 className="w-4 h-4 mr-1 text-emerald-600" />
                    Balanced: Debits equal Credits (Diff: 0.00 AED)
                  </span>
                ) : (
                  <span className="flex items-center text-rose-600 font-bold">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    Out of balance by AED {difference.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-gray-200 flex items-center justify-between">
            <span className="text-[11px] text-gray-500">
              Maker: <strong>{currentUser.name}</strong> ({currentUser.role})
            </span>
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-100 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!isBalanced}
                onClick={() => handleSave(true)}
                className="px-4 py-2 border border-[#5B2C83] text-[#5B2C83] hover:bg-plum-50 disabled:opacity-50 rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1 cursor-pointer"
              >
                <span>Save as Draft</span>
              </button>
              <button
                type="button"
                disabled={!isBalanced}
                onClick={() => handleSave(false)}
                className="px-5 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center space-x-1.5 cursor-pointer"
              >
                <Send className="w-3.5 h-3.5 text-amber-300" />
                <span>Submit for Approval</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
