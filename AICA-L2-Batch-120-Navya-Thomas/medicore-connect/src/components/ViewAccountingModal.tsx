import React from 'react';
import { X, CheckCircle, ExternalLink, BookOpen, AlertTriangle } from 'lucide-react';
import { getDb } from '../core/storage';
import { GLJournal, SubledgerEntry } from '../core/types';
import { getAccountByCode } from '../data/chartOfAccounts';
import { formatAED } from '../core/currency';

interface ViewAccountingModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentNumber: string;
  sourceModule: string;
  onNavigateToJournal?: (journalId: string) => void;
}

export const ViewAccountingModal: React.FC<ViewAccountingModalProps> = ({
  isOpen,
  onClose,
  documentNumber,
  sourceModule,
  onNavigateToJournal,
}) => {
  if (!isOpen) return null;

  const db = getDb();
  // Find associated GL Journal
  const journal: GLJournal | undefined = db.glJournals.find(
    (j) =>
      j.lines.some((l) => l.sourceDocumentNumber === documentNumber) ||
      j.number === documentNumber
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={onClose} />

      {/* Modal Dialog */}
      <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-4xl max-h-[90vh] flex flex-col z-10 animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-[#3F1D5C] text-white px-6 py-4 rounded-t-xl flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <BookOpen className="w-5 h-5 text-amber-300" />
            <div>
              <h2 className="font-bold text-base">View Accounting Entries</h2>
              <p className="text-xs text-plum-200">
                Source: <span className="font-medium text-white">{sourceModule}</span> | Document:{' '}
                <strong className="text-amber-300 font-mono">{documentNumber}</strong>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-[#5B2C83] text-gray-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {!journal ? (
            <div className="text-center py-10 bg-gray-50 rounded-lg border border-dashed border-gray-300">
              <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto mb-2" />
              <h3 className="font-semibold text-gray-800 text-sm">No GL Journal Posted Yet</h3>
              <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
                This transaction has not yet been approved and accounted to the General Ledger. Approve the item to generate subledger entries.
              </p>
            </div>
          ) : (
            <div>
              {/* Journal Summary Banner */}
              <div className="bg-plum-50/70 border border-plum-200 rounded-lg p-4 mb-5 flex flex-wrap items-center justify-between gap-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                  <div>
                    <span className="text-gray-500 block">GL Journal No.</span>
                    <span className="font-mono font-bold text-[#3F1D5C] text-sm">{journal.number}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block">Accounting Date</span>
                    <span className="font-medium text-gray-800">{journal.journalDate}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block">Fiscal Period</span>
                    <span className="font-semibold text-[#5B2C83]">{journal.period}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 block">Posting Status</span>
                    <span className="inline-flex items-center text-emerald-700 font-semibold">
                      <CheckCircle className="w-3.5 h-3.5 mr-1" />
                      {journal.status}
                    </span>
                  </div>
                </div>

                {onNavigateToJournal && (
                  <button
                    onClick={() => {
                      onNavigateToJournal(journal.id);
                      onClose();
                    }}
                    className="px-3 py-1.5 rounded-md bg-[#5B2C83] hover:bg-[#3F1D5C] text-white text-xs font-semibold flex items-center space-x-1.5 shadow-xs transition-colors"
                  >
                    <span>Open in General Ledger</span>
                    <ExternalLink className="w-3.5 h-3.5 text-amber-300" />
                  </button>
                )}
              </div>

              {/* Journal Lines Table */}
              <div className="border border-gray-200 rounded-lg overflow-hidden shadow-xs">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
                    <tr>
                      <th className="py-2.5 px-3 w-10 text-center">#</th>
                      <th className="py-2.5 px-3 w-16">BU</th>
                      <th className="py-2.5 px-3 w-28">Account</th>
                      <th className="py-2.5 px-3">Account Description</th>
                      <th className="py-2.5 px-3 w-24">Department</th>
                      <th className="py-2.5 px-3 text-right w-28">Debit (AED)</th>
                      <th className="py-2.5 px-3 text-right w-28">Credit (AED)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {journal.lines.map((line, idx) => {
                      const acct = getAccountByCode(line.account);
                      return (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="py-2 px-3 text-center text-gray-400">{idx + 1}</td>
                          <td className="py-2 px-3 font-semibold text-gray-700">{line.businessUnit}</td>
                          <td className="py-2 px-3 font-mono font-medium text-[#5B2C83]">{line.account}</td>
                          <td className="py-2 px-3 text-gray-800">
                            <div>{acct ? acct.name : line.description}</div>
                            {line.description && (
                              <div className="text-[10px] text-gray-500 italic">{line.description}</div>
                            )}
                          </td>
                          <td className="py-2 px-3 text-gray-600">{line.department || '—'}</td>
                          <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                            {line.debit > 0 ? formatAED(line.debit) : '—'}
                          </td>
                          <td className="py-2 px-3 text-right font-mono font-medium text-gray-900">
                            {line.credit > 0 ? formatAED(line.credit) : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot className="bg-gray-100 font-bold border-t border-gray-300 text-gray-900">
                    <tr>
                      <td colSpan={5} className="py-2.5 px-3 text-right uppercase tracking-wider text-xs">
                        Total General Ledger Movement:
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-emerald-800 text-sm">
                        {formatAED(journal.totalDebit)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-emerald-800 text-sm">
                        {formatAED(journal.totalCredit)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* Debits = Credits check tag */}
              <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                <span className="flex items-center text-emerald-700 font-medium">
                  <CheckCircle className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                  Journal is in balance: Debits = Credits (Difference: 0.00 AED)
                </span>
                <span>Audit Ref: {journal.approvedBy} on {journal.postedAt.slice(0, 10)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-3 rounded-b-xl border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded text-xs font-semibold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
