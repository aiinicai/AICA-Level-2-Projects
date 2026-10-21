import React, { useState } from 'react';
import Decimal from 'decimal.js';
import { Search, Eye, Filter, Download, BookOpen } from 'lucide-react';
import { getDb } from '../../core/storage';
import { CHART_OF_ACCOUNTS } from '../../data/chartOfAccounts';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { formatAED, round2 } from '../../core/currency';
import { ViewAccountingModal } from '../../components/ViewAccountingModal';

interface AccountInquiryPageProps {
  onNavigate: (route: string) => void;
}

export const AccountInquiryPage: React.FC<AccountInquiryPageProps> = ({ onNavigate }) => {
  const db = getDb();
  const [selectedBU, setSelectedBU] = useState<string>('All');
  const [selectedType, setSelectedType] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [drillJournalNo, setDrillJournalNo] = useState<string | null>(null);

  // Compute account balances from posted GL journals
  const accountBalances = React.useMemo(() => {
    const map: Record<string, { debits: Decimal; credits: Decimal; lineCount: number }> = {};

    CHART_OF_ACCOUNTS.forEach((a) => {
      map[a.code] = { debits: new Decimal(0), credits: new Decimal(0), lineCount: 0 };
    });

    db.glJournals.forEach((j) => {
      if (j.status !== 'Posted') return;
      j.lines.forEach((l) => {
        if (selectedBU !== 'All' && l.businessUnit !== selectedBU) return;

        if (map[l.account]) {
          map[l.account].debits = map[l.account].debits.plus(l.debit || 0);
          map[l.account].credits = map[l.account].credits.plus(l.credit || 0);
          map[l.account].lineCount += 1;
        }
      });
    });

    return CHART_OF_ACCOUNTS.map((acct) => {
      const stats = map[acct.code] || { debits: new Decimal(0), credits: new Decimal(0), lineCount: 0 };
      const isNormalDebit = acct.normalBalance === 'Debit';
      const net = isNormalDebit
        ? stats.debits.minus(stats.credits)
        : stats.credits.minus(stats.debits);

      return {
        ...acct,
        totalDebits: stats.debits.toNumber(),
        totalCredits: stats.credits.toNumber(),
        lineCount: stats.lineCount,
        endingBalance: net.toNumber(),
      };
    });
  }, [db.glJournals, selectedBU]);

  // Filter accounts
  const filtered = accountBalances.filter((a) => {
    if (selectedType !== 'All' && a.type !== selectedType) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return a.code.toLowerCase().includes(q) || a.name.toLowerCase().includes(q) || a.ifrsLine.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto bg-gray-50">
      {/* Title */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-[#5B2C83] text-white flex items-center justify-center">
            <Search className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">Account Inquiry & Balances</h1>
            <p className="text-xs text-gray-500">
              Interactive general ledger inquiry across Chart of Accounts with double-entry audit trails.
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-gray-600">Business Unit:</label>
          <select
            value={selectedBU}
            onChange={(e) => setSelectedBU(e.target.value)}
            className="bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-xs text-gray-800 font-medium focus:ring-2 focus:ring-[#5B2C83] focus:outline-none"
          >
            <option value="All">All Business Units (Consolidated)</option>
            {BUSINESS_UNITS.map((bu) => (
              <option key={bu.code} value={bu.code}>
                {bu.code} &bull; {bu.name}
              </option>
            ))}
          </select>

          <label className="text-xs font-semibold text-gray-600">Account Type:</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-white border border-gray-300 rounded-lg px-3 py-1.5 text-xs text-gray-800 font-medium focus:ring-2 focus:ring-[#5B2C83] focus:outline-none"
          >
            <option value="All">All Account Types</option>
            <option value="Asset">Assets</option>
            <option value="Contra">Contra Assets</option>
            <option value="Liability">Liabilities</option>
            <option value="Equity">Equity</option>
            <option value="Revenue">Revenue</option>
            <option value="Expense">Expenses</option>
          </select>
        </div>
      </div>

      {/* Search Input */}
      <div className="mb-4">
        <div className="relative max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by code (e.g. 1020, 2000) or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-[#5B2C83] focus:outline-none"
          />
        </div>
      </div>

      {/* Account Inquiry Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xs">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
            <tr>
              <th className="py-2.5 px-3 w-20">Code</th>
              <th className="py-2.5 px-3">Account Name</th>
              <th className="py-2.5 px-3 w-28">Type</th>
              <th className="py-2.5 px-3 w-48">IFRS Statement Line</th>
              <th className="py-2.5 px-3 text-right w-32">Total Debits (AED)</th>
              <th className="py-2.5 px-3 text-right w-32">Total Credits (AED)</th>
              <th className="py-2.5 px-3 text-right w-36">Net Ending Balance (AED)</th>
              <th className="py-2.5 px-3 text-center w-24">Journals</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map((acct, idx) => {
              const isNonZero = Math.abs(acct.endingBalance) > 0.005 || acct.totalDebits > 0 || acct.totalCredits > 0;
              return (
                <tr
                  key={acct.code}
                  className={`hover:bg-plum-50/50 transition-colors ${
                    idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'
                  }`}
                >
                  <td className="py-2 px-3 font-mono font-bold text-[#5B2C83]">{acct.code}</td>
                  <td className="py-2 px-3">
                    <div className="font-semibold text-gray-900">{acct.name}</div>
                    {acct.isControlAccount && (
                      <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.2 rounded font-medium inline-block mt-0.5">
                        Subledger Control Account
                      </span>
                    )}
                  </td>
                  <td className="py-2 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-100 text-gray-700">
                      {acct.type}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-gray-600 truncate max-w-xs">{acct.ifrsLine}</td>
                  <td className="py-2 px-3 text-right font-mono text-gray-900">
                    {formatAED(acct.totalDebits, { zeroAsDash: true })}
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-gray-900">
                    {formatAED(acct.totalCredits, { zeroAsDash: true })}
                  </td>
                  <td className="py-2 px-3 text-right font-mono font-bold">
                    <span className={acct.endingBalance < 0 ? 'text-rose-600' : 'text-gray-900'}>
                      {formatAED(acct.endingBalance, { useBracketsForNegative: true, zeroAsDash: true })}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center">
                    <button
                      onClick={() => onNavigate(`#/general-accounting/journals`)}
                      className="px-2 py-0.5 rounded bg-plum-50 text-[#5B2C83] hover:bg-[#5B2C83] hover:text-white font-medium text-[11px] transition-colors"
                    >
                      {acct.lineCount} Lines
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
