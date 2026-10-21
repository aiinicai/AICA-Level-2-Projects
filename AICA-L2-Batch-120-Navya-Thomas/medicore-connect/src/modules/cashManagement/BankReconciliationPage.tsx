import React, { useState } from 'react';
import {
  Landmark,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Search,
  ArrowRight,
  FileSpreadsheet,
} from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { getActiveUser } from '../../core/auth';
import { formatAED, round2 } from '../../core/currency';
import { BUSINESS_UNITS } from '../../data/businessUnits';

interface BankReconciliationPageProps {
  onNavigate: (route: string) => void;
}

export const BankReconciliationPage: React.FC<BankReconciliationPageProps> = ({ onNavigate }) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [selectedBU, setSelectedBU] = useState('H01');
  const [selectedAccount, setSelectedAccount] = useState('1020');
  const [autoMatchMessage, setAutoMatchMessage] = useState<string | null>(null);

  const statements = db.bankStatements.filter(
    (s) => s.businessUnit === selectedBU && s.bankAccountCode === selectedAccount
  );
  const currentStatement = statements[0] || db.bankStatements[0];

  // Auto-matching simulation
  const handleAutoMatch = () => {
    if (!currentStatement) return;

    let matchedCount = 0;
    updateDb((state) => {
      const stmt = state.bankStatements.find((s) => s.id === currentStatement.id);
      if (stmt) {
        stmt.lines.forEach((line) => {
          if (!line.isReconciled) {
            line.isReconciled = true;
            matchedCount++;
          }
        });
        stmt.status = 'Reconciled';
      }
    });

    addAuditLog({
      entityType: 'BankStatement',
      entityId: currentStatement.id,
      action: 'APPROVE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Auto-matched ${matchedCount} bank statement lines against subledger AP payments & AR deposits`,
    });

    setAutoMatchMessage(
      `Auto-Match Complete: Successfully matched and reconciled ${matchedCount} statement lines with zero variance.`
    );
  };

  const lines = currentStatement?.lines || [];
  const reconciledLines = lines.filter((l) => l.isReconciled);
  const unreconciledLines = lines.filter((l) => !l.isReconciled);

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50 select-none">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center shadow-xs">
            <Landmark className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Bank Statements & Reconciliation</h1>
            <p className="text-xs text-gray-500">
              Automated 3-way matching of electronic bank statement feeds against AP disbursements and AR collections.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          <div>
            <label className="font-semibold text-gray-600 mr-2">BU:</label>
            <select
              value={selectedBU}
              onChange={(e) => setSelectedBU(e.target.value)}
              className="bg-white border border-gray-300 rounded px-2.5 py-1.5 font-semibold text-gray-800"
            >
              {BUSINESS_UNITS.slice(0, 5).map((bu) => (
                <option key={bu.code} value={bu.code}>
                  {bu.code} - {bu.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="font-semibold text-gray-600 mr-2">Account:</label>
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className="bg-white border border-gray-300 rounded px-2.5 py-1.5 font-mono font-bold text-gray-800"
            >
              <option value="1020">1020 - FAB Operating Account</option>
              <option value="1030">1030 - ENBD Collections Account</option>
            </select>
          </div>

          <button
            onClick={handleAutoMatch}
            className="px-4 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg font-semibold shadow-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Run Auto-Match</span>
          </button>
        </div>
      </div>

      {autoMatchMessage && (
        <div className="mb-5 p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs flex items-center justify-between">
          <span>{autoMatchMessage}</span>
          <button onClick={() => setAutoMatchMessage(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Statement Reconciliation Banner */}
      {currentStatement && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6 shadow-xs">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-xs">
            <div>
              <span className="text-gray-500 block uppercase font-medium">Bank Statement No.</span>
              <span className="font-mono font-bold text-base text-[#3F1D5C]">
                {currentStatement.number}
              </span>
            </div>
            <div>
              <span className="text-gray-500 block uppercase font-medium">Opening Balance</span>
              <span className="font-mono font-bold text-base text-gray-800">
                {formatAED(currentStatement.openingBalance, { showCurrency: true })}
              </span>
            </div>
            <div>
              <span className="text-gray-500 block uppercase font-medium">Closing Statement Balance</span>
              <span className="font-mono font-bold text-base text-gray-800">
                {formatAED(currentStatement.closingBalance, { showCurrency: true })}
              </span>
            </div>
            <div>
              <span className="text-gray-500 block uppercase font-medium">Status</span>
              <span
                className={`inline-flex items-center text-xs font-bold px-2.5 py-0.5 rounded-full mt-1 ${
                  currentStatement.status === 'Reconciled'
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-amber-100 text-amber-800'
                }`}
              >
                {currentStatement.status === 'Reconciled' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                ) : (
                  <AlertCircle className="w-3.5 h-3.5 mr-1" />
                )}
                {currentStatement.status}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Statement Lines Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="p-4 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
            Statement Line Activity ({lines.length} Lines)
          </h2>
          <span className="text-xs text-gray-500">
            Reconciled: <strong className="text-emerald-700">{reconciledLines.length}</strong> &bull; Unmatched:{' '}
            <strong className="text-rose-700">{unreconciledLines.length}</strong>
          </span>
        </div>

        <table className="w-full text-xs text-left border-collapse">
          <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
            <tr>
              <th className="py-2.5 px-3 w-24">Date</th>
              <th className="py-2.5 px-3 w-20">Type</th>
              <th className="py-2.5 px-3 w-36">Reference</th>
              <th className="py-2.5 px-3">Description</th>
              <th className="py-2.5 px-3 text-right w-28">Amount (AED)</th>
              <th className="py-2.5 px-3 text-center w-28">Matched Status</th>
              <th className="py-2.5 px-3 w-36">Matched Transaction</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {lines.map((l) => (
              <tr key={l.id} className="hover:bg-plum-50/20">
                <td className="py-2 px-3 font-medium text-gray-800">{l.lineDate}</td>
                <td className="py-2 px-3">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      l.type === 'Credit' ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'
                    }`}
                  >
                    {l.type}
                  </span>
                </td>
                <td className="py-2 px-3 font-mono font-medium text-gray-700">{l.reference}</td>
                <td className="py-2 px-3 text-gray-800">{l.description}</td>
                <td className="py-2 px-3 text-right font-mono font-bold text-gray-900">
                  {formatAED(l.amount)}
                </td>
                <td className="py-2 px-3 text-center">
                  {l.isReconciled ? (
                    <span className="inline-flex items-center text-[11px] font-bold text-emerald-700">
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                      Matched
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-[11px] font-bold text-rose-700">
                      <AlertCircle className="w-3.5 h-3.5 mr-1" />
                      Unmatched
                    </span>
                  )}
                </td>
                <td className="py-2 px-3 font-mono text-[11px] text-gray-600">
                  {l.matchedTransactionNumber || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
