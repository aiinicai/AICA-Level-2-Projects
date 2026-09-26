import React, { useState } from 'react';
import {
  CreditCard,
  Users,
  Building,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  FileCheck,
  RefreshCw,
  Plus,
} from 'lucide-react';
import { BankTransaction, PayrollRun } from '../../types';
import { formatINR, formatLakhs } from '../../services/accountingEngine';

interface BankingPayrollViewProps {
  bankTransactions: BankTransaction[];
  payrollRuns: PayrollRun[];
  onReconcileTransaction: (txId: string) => void;
  onPostPayroll: (run: PayrollRun) => void;
}

export const BankingPayrollView: React.FC<BankingPayrollViewProps> = ({
  bankTransactions,
  payrollRuns,
  onReconcileTransaction,
  onPostPayroll,
}) => {
  const [activeTab, setActiveTab] = useState<'bank_reconciliation' | 'payroll_runs'>('bank_reconciliation');

  const hdfcBalance = 6420000;
  const iciciBalance = 2150000;
  const totalBankBalance = hdfcBalance + iciciBalance;

  return (
    <div id="banking-payroll-container" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Treasury, Banking & Payroll Automation</h2>
            <span className="text-[11px] bg-indigo-500/10 text-indigo-300 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
              Auto-Reconciliation
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Automated bank statement reconciliation and statutory monthly payroll journal entry generation (PF, ESI, TDS, Net Salary).
          </p>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs w-fit">
        <button
          onClick={() => setActiveTab('bank_reconciliation')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'bank_reconciliation' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Bank Feed & Reconciliation ({bankTransactions.length})
        </button>
        <button
          onClick={() => setActiveTab('payroll_runs')}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
            activeTab === 'payroll_runs' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Statutory Payroll Engine ({payrollRuns.length})
        </button>
      </div>

      {/* TAB 1: BANK RECONCILIATION */}
      {activeTab === 'bank_reconciliation' && (
        <div className="space-y-5">
          {/* Bank Account Balances */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">Total Liquid Bank Balance</div>
              <div className="text-lg font-bold text-emerald-400 font-mono mt-1">{formatLakhs(totalBankBalance)}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">100% Reconciled with General Ledger</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">HDFC Bank Current A/c (502000...)</div>
              <div className="text-lg font-bold text-slate-100 font-mono mt-1">{formatINR(hdfcBalance)}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Pune Central Branch</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl">
              <div className="text-xs text-slate-400">ICICI Bank Escrow / Tax A/c</div>
              <div className="text-lg font-bold text-slate-100 font-mono mt-1">{formatINR(iciciBalance)}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">Designated for GST / TDS remittances</div>
            </div>
          </div>

          {/* Transactions Table */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm text-xs font-mono">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between font-sans">
              <h3 className="font-semibold text-slate-100 text-sm">Automated Bank Statement Feed</h3>
              <span className="text-xs text-slate-400 font-mono">Real-time Open Banking API Sync</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                  <tr>
                    <th className="p-3">Date / Bank Ref</th>
                    <th className="p-3 font-sans">Description / Counterparty</th>
                    <th className="p-3 text-right">Debit (Withdrawal)</th>
                    <th className="p-3 text-right">Credit (Deposit)</th>
                    <th className="p-3 font-sans">Auto-Matched Ledger Entity</th>
                    <th className="p-3 font-sans text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 text-slate-300">
                  {bankTransactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-slate-800/40">
                      <td className="p-3">
                        <div className="font-bold text-slate-100">{tx.referenceNumber}</div>
                        <div className="text-[10px] text-slate-400">{tx.date}</div>
                      </td>
                      <td className="p-3 font-sans text-slate-200">{tx.description}</td>
                      <td className="p-3 text-right font-bold text-rose-400">
                        {tx.type === 'DEBIT' ? `-${formatINR(tx.amount)}` : '-'}
                      </td>
                      <td className="p-3 text-right font-bold text-emerald-400">
                        {tx.type === 'CREDIT' ? `+${formatINR(tx.amount)}` : '-'}
                      </td>
                      <td className="p-3 font-sans">
                        <span className="text-[11px] text-indigo-300">{tx.matchedDocumentId}</span>
                      </td>
                      <td className="p-3 font-sans text-center">
                        {tx.status === 'RECONCILED' ? (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Reconciled
                          </span>
                        ) : (
                          <button
                            onClick={() => onReconcileTransaction(tx.id)}
                            className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 hover:bg-amber-500/20 cursor-pointer"
                          >
                            Match & Post
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: STATUTORY PAYROLL RUNS */}
      {activeTab === 'payroll_runs' && (
        <div className="space-y-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30 flex items-start gap-3">
            <Users className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
            <div className="font-sans">
              <h4 className="font-semibold text-indigo-200 text-sm">Automated Statutory Payroll Journal Entries</h4>
              <p className="text-slate-300 text-xs mt-1">
                When payroll is approved, the system automatically posts the compound journal voucher:
                Dr Employee Benefit Expense (Gross Pay), Cr PF Payable (12%), Cr ESI Payable (0.75%), Cr TDS under Sec 192, Cr Net Salaries Payable.
              </p>
            </div>
          </div>

          <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between font-sans">
              <h3 className="font-semibold text-slate-100 text-sm">Monthly Payroll Registers</h3>
              <span className="text-xs text-slate-400">{payrollRuns.length} Processed Runs</span>
            </div>

            <div className="divide-y divide-slate-800/80">
              {payrollRuns.map((run) => (
                <div key={run.id} className="p-4 space-y-3">
                  <div className="flex items-center justify-between font-sans">
                    <div>
                      <div className="font-bold text-slate-100 text-sm">{run.monthYear} Payroll Run</div>
                      <div className="text-[11px] text-slate-400">Headcount: {run.headcount} Regular Employees • Linked JV: {run.journalEntryId}</div>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Disbursed & Journal Posted
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px]">
                    <div>
                      <div className="text-slate-400 font-sans">Gross Salaries:</div>
                      <div className="text-slate-100 font-bold mt-0.5">{formatINR(run.grossSalary)}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 font-sans">EPF Deduction (12%):</div>
                      <div className="text-rose-300 font-bold mt-0.5">-{formatINR(run.pfDeduction)}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 font-sans">ESI Deduction:</div>
                      <div className="text-rose-300 font-bold mt-0.5">-{formatINR(run.esiDeduction)}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 font-sans">Sec 192 TDS:</div>
                      <div className="text-rose-300 font-bold mt-0.5">-{formatINR(run.tdsDeduction)}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 font-sans">Net Bank Disbursal:</div>
                      <div className="text-emerald-400 font-bold mt-0.5">{formatINR(run.netPayable)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
