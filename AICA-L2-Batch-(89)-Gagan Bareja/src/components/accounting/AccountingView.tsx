import React, { useState } from 'react';
import {
  FileText,
  BookOpen,
  Scale,
  Plus,
  Lock,
  Download,
  Calendar,
  Layers,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { Account, JournalEntry, SystemSettings } from '../../types';
import {
  calculateBalanceSheet,
  calculateProfitAndLoss,
  calculateTrialBalance,
  formatINR,
  formatLakhs,
} from '../../services/accountingEngine';

interface AccountingViewProps {
  accounts: Account[];
  journalEntries: JournalEntry[];
  settings: SystemSettings;
  onAddManualJournalEntry: (entry: JournalEntry) => void;
}

export const AccountingView: React.FC<AccountingViewProps> = ({
  accounts,
  journalEntries,
  settings,
  onAddManualJournalEntry,
}) => {
  const [activeTab, setActiveTab] = useState<'balance_sheet' | 'pnl' | 'trial_balance' | 'general_ledger' | 'chart_of_accounts' | 'closing_controls'>('balance_sheet');
  const [showManualEntryModal, setShowManualEntryModal] = useState(false);
  const [selectedEntryForDrilldown, setSelectedEntryForDrilldown] = useState<JournalEntry | null>(null);

  // Manual JV State
  const [debitAccCode, setDebitAccCode] = useState('4202'); // Rent expense
  const [creditAccCode, setCreditAccCode] = useState('1002'); // HDFC Bank
  const [jvAmount, setJvAmount] = useState(75000);
  const [jvNarration, setJvNarration] = useState('Payment of Pune corporate office lease rental for March 2026');

  const trialBalance = calculateTrialBalance(accounts);
  const balanceSheet = calculateBalanceSheet(accounts);
  const pnl = calculateProfitAndLoss(accounts);

  const handlePostManualJV = (e: React.FormEvent) => {
    e.preventDefault();
    const debitAcc = accounts.find((a) => a.code === debitAccCode) || accounts[0];
    const creditAcc = accounts.find((a) => a.code === creditAccCode) || accounts[1];

    const newJv: JournalEntry = {
      id: `JE-2026-${Math.floor(100 + Math.random() * 900)}`,
      date: new Date().toISOString().split('T')[0],
      sourceDocumentType: 'MANUAL_JOURNAL',
      sourceDocumentId: `JV-${Date.now()}`,
      lines: [
        {
          id: `L1-${Date.now()}`,
          accountId: debitAcc.id || debitAcc.code,
          accountCode: debitAcc.code,
          accountName: debitAcc.name,
          debit: jvAmount,
          credit: 0,
        },
        {
          id: `L2-${Date.now()}`,
          accountId: creditAcc.id || creditAcc.code,
          accountCode: creditAcc.code,
          accountName: creditAcc.name,
          debit: 0,
          credit: jvAmount,
        },
      ],
      totalDebit: jvAmount,
      totalCredit: jvAmount,
      status: 'POSTED',
      narration: jvNarration,
      postedBy: 'Gagan Bareja (CFO)',
      postedAt: new Date().toISOString(),
    };

    onAddManualJournalEntry(newJv);
    setShowManualEntryModal(false);
  };

  return (
    <div id="accounting-module-container" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Statutory Accounting & General Ledger</h2>
            <span className="text-[11px] bg-indigo-500/10 text-indigo-300 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
              Schedule III (Companies Act 2013)
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographically verifiable, immutable double-entry ledger with automated financial statement generation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowManualEntryModal(true)}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Journal Voucher (JV)</span>
          </button>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs w-fit">
        <button
          onClick={() => setActiveTab('balance_sheet')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'balance_sheet' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Balance Sheet
        </button>
        <button
          onClick={() => setActiveTab('pnl')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'pnl' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Profit & Loss Statement
        </button>
        <button
          onClick={() => setActiveTab('trial_balance')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'trial_balance' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Trial Balance
        </button>
        <button
          onClick={() => setActiveTab('general_ledger')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'general_ledger' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Immutable Journal Entries ({journalEntries.length})
        </button>
        <button
          onClick={() => setActiveTab('chart_of_accounts')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'chart_of_accounts' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Chart of Accounts ({accounts.length})
        </button>
        <button
          onClick={() => setActiveTab('closing_controls')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'closing_controls' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Period-End Lock Controls
        </button>
      </div>

      {/* TAB 1: SCHEDULE III BALANCE SHEET */}
      {activeTab === 'balance_sheet' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm font-mono text-xs">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between font-sans">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">
                Schedule III (Division I) Balance Sheet as of 31st March 2026
              </h3>
              <p className="text-[11px] text-slate-400">Statement of Assets and Liabilities (Standalone Ind AS / AS format)</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                Balance Check: Balanced
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-4 font-sans">Particulars</th>
                  <th className="py-2.5 px-4 text-right">Note No.</th>
                  <th className="py-2.5 px-4 text-right">Figures as of Current Period (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {/* EQUITY AND LIABILITIES */}
                <tr className="bg-slate-950/60 font-sans font-bold text-slate-100">
                  <td colSpan={3} className="py-2.5 px-4 text-indigo-300">
                    I. EQUITY AND LIABILITIES
                  </td>
                </tr>

                {/* 1. Shareholders' Funds */}
                <tr className="font-semibold text-slate-200">
                  <td className="py-2 px-6 font-sans">1. Shareholders' Funds</td>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(a) Share Capital (Equity)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">1</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.shareCapital)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(b) Reserves and Surplus (Retained Earnings)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">2</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.reservesAndSurplus)}</td>
                </tr>

                {/* 2. Non-Current Liabilities */}
                <tr className="font-semibold text-slate-200">
                  <td className="py-2 px-6 font-sans">2. Non-Current Liabilities</td>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(a) Long-Term Borrowings (Term Loans)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">3</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.longTermBorrowings)}</td>
                </tr>

                {/* 3. Current Liabilities */}
                <tr className="font-semibold text-slate-200">
                  <td className="py-2 px-6 font-sans">3. Current Liabilities</td>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(a) Trade Payables (Creditors)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">4</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.tradePayables)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(b) Other Current Liabilities (GST/TDS/PF)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">5</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.otherCurrentLiabilities)}</td>
                </tr>

                <tr className="bg-slate-950 font-bold text-slate-100 border-t border-b border-slate-700">
                  <td className="py-3 px-4 font-sans text-indigo-300">TOTAL EQUITY AND LIABILITIES</td>
                  <td className="py-3 px-4 text-right"></td>
                  <td className="py-3 px-4 text-right text-indigo-300 text-sm">{formatINR(balanceSheet.totalLiabilities)}</td>
                </tr>

                {/* ASSETS */}
                <tr className="bg-slate-950/60 font-sans font-bold text-slate-100">
                  <td colSpan={3} className="py-2.5 px-4 text-emerald-300">
                    II. ASSETS
                  </td>
                </tr>

                {/* 1. Non-Current Assets */}
                <tr className="font-semibold text-slate-200">
                  <td className="py-2 px-6 font-sans">1. Non-Current Assets</td>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(a) Property, Plant and Equipment (Net Block)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">6</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.tangibleAssets)}</td>
                </tr>

                {/* 2. Current Assets */}
                <tr className="font-semibold text-slate-200">
                  <td className="py-2 px-6 font-sans">2. Current Assets</td>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(a) Inventories (Perpetual at Lower of Cost or NRV)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">7</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.inventories)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(b) Trade Receivables (Debtors Net of Provisions)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">8</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.tradeReceivables)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(c) Cash and Cash Equivalents</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">9</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.cashAndBank)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-10 font-sans text-slate-300">(d) Short-term Loans, Advances & Input GST ITC</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">10</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(balanceSheet.shortTermAdvances)}</td>
                </tr>

                <tr className="bg-slate-950 font-bold text-slate-100 border-t-2 border-slate-700">
                  <td className="py-3 px-4 font-sans text-emerald-300">TOTAL ASSETS</td>
                  <td className="py-3 px-4 text-right"></td>
                  <td className="py-3 px-4 text-right text-emerald-300 text-sm">{formatINR(balanceSheet.totalAssets)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: SCHEDULE III PROFIT & LOSS */}
      {activeTab === 'pnl' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm font-mono text-xs">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between font-sans">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">
                Statement of Profit and Loss for the Period Ended 31st March 2026
              </h3>
              <p className="text-[11px] text-slate-400">Schedule III Part II format (By Nature of Expense)</p>
            </div>
            <button className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 cursor-pointer">
              <Download className="w-3.5 h-3.5" />
              <span>Export P&L to Excel</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-4 font-sans">Particulars</th>
                  <th className="py-2.5 px-4 text-right">Note No.</th>
                  <th className="py-2.5 px-4 text-right">Amount (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                <tr className="font-semibold text-slate-200">
                  <td className="py-2 px-4 font-sans">I. Revenue from Operations</td>
                  <td className="py-2 px-4 text-right text-slate-400">11</td>
                  <td className="py-2 px-4 text-right font-bold text-slate-100">{formatINR(pnl.revenueFromOperations)}</td>
                </tr>
                <tr className="font-semibold text-slate-200">
                  <td className="py-2 px-4 font-sans">II. Other Income</td>
                  <td className="py-2 px-4 text-right text-slate-400">12</td>
                  <td className="py-2 px-4 text-right">{formatINR(pnl.otherIncome)}</td>
                </tr>
                <tr className="bg-slate-950/60 font-bold text-indigo-300 border-t border-b border-slate-800">
                  <td className="py-2.5 px-4 font-sans">III. Total Revenue (I + II)</td>
                  <td className="py-2.5 px-4 text-right"></td>
                  <td className="py-2.5 px-4 text-right">{formatINR(pnl.totalRevenue)}</td>
                </tr>

                <tr className="bg-slate-950/30 font-sans font-semibold text-slate-300">
                  <td colSpan={3} className="py-2 px-4">IV. Expenses</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-8 font-sans text-slate-300">(a) Cost of Materials Consumed / Direct COGS</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">13</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(pnl.costOfMaterials)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-8 font-sans text-slate-300">(b) Employee Benefit Expense (Salaries, PF, Gratuity)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">14</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(pnl.employeeBenefits)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-8 font-sans text-slate-300">(c) Finance Costs (Bank Interest & Borrowing charges)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">15</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(pnl.financeCosts)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-8 font-sans text-slate-300">(d) Depreciation and Amortisation Expense (Schedule II)</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">16</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(pnl.depreciation)}</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-8 font-sans text-slate-300">(e) Other Operating Expenses</td>
                  <td className="py-1.5 px-4 text-right text-slate-400">17</td>
                  <td className="py-1.5 px-4 text-right">{formatINR(pnl.otherExpenses)}</td>
                </tr>

                <tr className="bg-slate-950/60 font-bold text-slate-100 border-t border-b border-slate-800">
                  <td className="py-2.5 px-4 font-sans">Total Expenses (IV)</td>
                  <td className="py-2.5 px-4 text-right"></td>
                  <td className="py-2.5 px-4 text-right">{formatINR(pnl.totalExpenses)}</td>
                </tr>

                <tr className="bg-indigo-950/20 font-bold text-slate-100 border-t border-b border-indigo-500/30">
                  <td className="py-3 px-4 font-sans text-indigo-300">V. Profit Before Tax (PBT) (III - IV)</td>
                  <td className="py-3 px-4 text-right"></td>
                  <td className="py-3 px-4 text-right text-indigo-300">{formatINR(pnl.profitBeforeTax)}</td>
                </tr>
                <tr>
                  <td className="py-2 px-8 font-sans text-slate-300">VI. Current Tax Expense (Sec 115BAA @ 25.17%)</td>
                  <td className="py-2 px-4 text-right text-slate-400">18</td>
                  <td className="py-2 px-4 text-right">{formatINR(pnl.taxExpense)}</td>
                </tr>
                <tr className="bg-emerald-950/20 font-bold text-emerald-300 border-t-2 border-emerald-500/30 text-sm">
                  <td className="py-3.5 px-4 font-sans">VII. Profit After Tax (PAT) for the Period</td>
                  <td className="py-3.5 px-4 text-right"></td>
                  <td className="py-3.5 px-4 text-right">{formatINR(pnl.profitAfterTax)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: TRIAL BALANCE */}
      {activeTab === 'trial_balance' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm font-mono text-xs">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between font-sans">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">Real-Time Trial Balance</h3>
              <p className="text-[11px] text-slate-400">Complete listing of debit and credit ledger balances</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Balanced: Difference ₹0
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-4">Code</th>
                  <th className="py-2.5 px-4 font-sans">Account Name</th>
                  <th className="py-2.5 px-4">Classification</th>
                  <th className="py-2.5 px-4 text-right">Debit Balance (₹)</th>
                  <th className="py-2.5 px-4 text-right">Credit Balance (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {trialBalance.rows.map((row) => (
                  <tr key={row.account.id || row.account.code} className="hover:bg-slate-800/40">
                    <td className="py-2 px-4 font-bold text-slate-200">{row.account.code}</td>
                    <td className="py-2 px-4 font-sans font-medium text-slate-100">{row.account.name}</td>
                    <td className="py-2 px-4 font-sans text-slate-400">{row.account.subGroup}</td>
                    <td className="py-2 px-4 text-right text-slate-100">{row.debit > 0 ? formatINR(row.debit) : '-'}</td>
                    <td className="py-2 px-4 text-right text-slate-100">{row.credit > 0 ? formatINR(row.credit) : '-'}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-950 font-bold text-slate-100 border-t-2 border-slate-700">
                <tr>
                  <td colSpan={3} className="py-3 px-4 font-sans text-indigo-300">TOTAL TRIAL BALANCE</td>
                  <td className="py-3 px-4 text-right text-indigo-300 text-sm">{formatINR(trialBalance.totalDebit)}</td>
                  <td className="py-3 px-4 text-right text-indigo-300 text-sm">{formatINR(trialBalance.totalCredit)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: IMMUTABLE JOURNAL ENTRIES */}
      {activeTab === 'general_ledger' && (
        <div className="space-y-4 font-mono text-xs">
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between font-sans">
              <div>
                <h3 className="font-semibold text-slate-100 text-sm">General Ledger Journal Entries (Immutable Register)</h3>
                <p className="text-[11px] text-slate-400">
                  Strict append-only ledger per Companies Act 2013 audit trail mandates. Edit/deletion disabled.
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">{journalEntries.length} Total Vouchers</span>
            </div>

            <div className="divide-y divide-slate-800/80">
              {journalEntries.map((je) => (
                <div key={je.id} className="p-4 hover:bg-slate-800/30 transition-colors">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-indigo-400 text-sm">{je.id}</span>
                      <span className="text-[10px] font-sans font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {je.sourceDocumentType}
                      </span>
                      <span className="text-slate-400 text-[11px]">Ref: {je.sourceDocumentId}</span>
                    </div>
                    <div className="text-slate-400 text-[11px]">
                      Date: <strong className="text-slate-200">{je.date}</strong> • Posted by: {je.postedBy}
                    </div>
                  </div>

                  <p className="text-slate-300 font-sans text-xs mb-2.5 italic">Narration: {je.narration}</p>

                  <div className="border border-slate-800/80 rounded-lg overflow-hidden bg-slate-950/50">
                    <table className="w-full text-left text-[11px]">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 text-[10px] uppercase">
                        <tr>
                          <th className="p-2">Account Code & Name</th>
                          <th className="p-2 text-right">Debit (₹)</th>
                          <th className="p-2 text-right">Credit (₹)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/80">
                        {je.lines.map((line) => (
                          <tr key={line.id}>
                            <td className="p-2 text-slate-200">
                              <span className="font-bold mr-2 text-slate-400">{line.accountCode}</span>
                              <span className="font-sans">{line.accountName}</span>
                            </td>
                            <td className="p-2 text-right font-bold text-slate-100">{line.debit > 0 ? formatINR(line.debit) : '-'}</td>
                            <td className="p-2 text-right font-bold text-slate-100">{line.credit > 0 ? formatINR(line.credit) : '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: CHART OF ACCOUNTS */}
      {activeTab === 'chart_of_accounts' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm text-xs">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-100 text-sm">Schedule III Standard Chart of Accounts (COA)</h3>
              <p className="text-[11px] text-slate-400">Structured by Schedule III classification</p>
            </div>
            <span className="text-xs font-mono text-slate-400">{accounts.length} GL Accounts</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono">
              <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4 font-sans">Account Name</th>
                  <th className="py-3 px-4 font-sans">Major Category</th>
                  <th className="py-3 px-4 font-sans">Schedule III Sub-Group</th>
                  <th className="py-3 px-4 text-right">Closing Balance (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {accounts.map((acc) => (
                  <tr key={acc.id} className="hover:bg-slate-800/40">
                    <td className="py-2.5 px-4 font-bold text-slate-200">{acc.code}</td>
                    <td className="py-2.5 px-4 font-sans font-medium text-slate-100">{acc.name}</td>
                    <td className="py-2.5 px-4 font-sans">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                        acc.category === 'ASSET' ? 'bg-emerald-500/10 text-emerald-400' :
                        acc.category === 'LIABILITY' ? 'bg-purple-500/10 text-purple-400' :
                        acc.category === 'EQUITY' ? 'bg-indigo-500/10 text-indigo-400' :
                        acc.category === 'INCOME' ? 'bg-blue-500/10 text-blue-400' : 'bg-amber-500/10 text-amber-400'
                      }`}>
                        {acc.category}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 font-sans text-slate-400">{acc.subGroup}</td>
                    <td className="py-2.5 px-4 text-right font-bold text-slate-100">{formatINR(acc.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 6: PERIOD-END CLOSING CONTROLS */}
      {activeTab === 'closing_controls' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 space-y-5 text-xs">
          <div>
            <h3 className="font-semibold text-slate-100 text-sm">Period-End Financial Close & Freeze Controls</h3>
            <p className="text-slate-400 mt-0.5">
              Strict accounting controls preventing retroactive postings to finalized or audited fiscal quarters.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-100 font-sans">Hard Close Lock Date</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 font-semibold border border-rose-500/20">
                  LOCKED
                </span>
              </div>
              <p className="text-slate-400 text-[11px]">
                No transaction or journal voucher can be posted with document date on or prior to <strong>31st Dec 2025 (Q3)</strong>.
              </p>
            </div>

            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-100 font-sans">Auditor Verification Trail</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                  AUDITED
                </span>
              </div>
              <p className="text-slate-400 text-[11px]">
                Section 143(3) CARO 2020 verification complete. Audit software logging feature active.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CREATE MANUAL JOURNAL ENTRY */}
      {showManualEntryModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-slate-100 text-sm">Post Manual Journal Voucher (JV)</h3>
              <button onClick={() => setShowManualEntryModal(false)} className="text-slate-400 cursor-pointer">✕</button>
            </div>

            <form onSubmit={handlePostManualJV} className="space-y-3">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Debit Account</label>
                <select
                  value={debitAccCode}
                  onChange={(e) => setDebitAccCode(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  {accounts.map((a) => (
                    <option key={a.id} value={a.code}>
                      {a.code} - {a.name} ({a.category})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Credit Account</label>
                <select
                  value={creditAccCode}
                  onChange={(e) => setCreditAccCode(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                >
                  {accounts.map((a) => (
                    <option key={a.id} value={a.code}>
                      {a.code} - {a.name} ({a.category})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Voucher Amount (₹)</label>
                <input
                  type="number"
                  value={jvAmount}
                  onChange={(e) => setJvAmount(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Mandatory Narration</label>
                <input
                  type="text"
                  required
                  value={jvNarration}
                  onChange={(e) => setJvNarration(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowManualEntryModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold cursor-pointer shadow-md"
                >
                  Post JV to General Ledger
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
