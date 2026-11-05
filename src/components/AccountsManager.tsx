import React, { useState } from 'react';
import {
  CreditCard,
  Building,
  Wallet,
  ArrowRightLeft,
  CheckCircle,
  Plus,
  ShieldCheck,
  Calendar,
  X,
  Trash2,
  Edit2,
  RefreshCw,
  FileSpreadsheet,
  Sparkles,
  TrendingUp,
  ArrowUpRight,
  ArrowDownLeft,
  LineChart
} from 'lucide-react';
import { Account, Transaction } from '../types/finance';
import { StorageService } from '../services/storage';
import { BankStatementImportModal } from './BankStatementImportModal';

interface AccountsManagerProps {
  accounts: Account[];
  transactions?: Transaction[];
  onRecordTransaction: (tx: Partial<Transaction>) => void;
  onUpdateAccounts: (updated: Account[]) => void;
  onUpdateTransactions?: (updated: Transaction[]) => void;
  onOpenAddAccountModal: () => void;
}

export const AccountsManager: React.FC<AccountsManagerProps> = ({
  accounts,
  transactions = [],
  onRecordTransaction,
  onUpdateAccounts,
  onUpdateTransactions,
  onOpenAddAccountModal
}) => {
  // Bank Statement Import Modal
  const [statementImportModalOpen, setStatementImportModalOpen] = useState(false);

  // Pay Credit Card Modal
  const [payCardModalOpen, setPayCardModalOpen] = useState(false);
  const [selectedCardId, setSelectedCardId] = useState<string>('');
  const [fromBankId, setFromBankId] = useState<string>('');
  const [payAmount, setPayAmount] = useState<string>('');

  // Transfer Between Accounts Modal (Supports Bank, Cash, and Investment)
  const [transferModalOpen, setTransferModalOpen] = useState(false);
  const [transferFromId, setTransferFromId] = useState<string>('');
  const [transferToId, setTransferToId] = useState<string>('');
  const [transferAmount, setTransferAmount] = useState<string>('');

  // Update Valuation Modal State for Investment Accounts
  const [valuationModalOpen, setValuationModalOpen] = useState(false);
  const [selectedValuationAccount, setSelectedValuationAccount] = useState<Account | null>(null);
  const [newValuationInput, setNewValuationInput] = useState<string>('');

  // Edit Account Modal State
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [editName, setEditName] = useState('');
  const [editBankName, setEditBankName] = useState('');
  const [editMasked, setEditMasked] = useState('');
  const [editInitialBalanceStr, setEditInitialBalanceStr] = useState('0.00');
  const [editValuationStr, setEditValuationStr] = useState('0.00');
  const [editAssetClass, setEditAssetClass] = useState<string>('Stocks & ETFs');
  const [editCreditLimitStr, setEditCreditLimitStr] = useState('20000');
  const [editDueDate, setEditDueDate] = useState('');
  const [syncStatus, setSyncStatus] = useState<string | null>(null);

  const bankAccounts = accounts.filter(a => a.type === 'bank' || a.type === 'cash');
  const creditCards = accounts.filter(a => a.type === 'credit_card');
  const investmentAccounts = accounts.filter(a => a.type === 'investment');

  const totalBankAndCash = bankAccounts.reduce((sum, a) => sum + a.balance, 0);
  const totalCreditCardDebt = creditCards.reduce((sum, a) => sum + a.balance, 0);
  const totalInvestments = investmentAccounts.reduce((sum, a) => sum + (a.currentValuation ?? a.balance), 0);
  const totalInvestedPrincipal = investmentAccounts.reduce((sum, a) => sum + (a.totalInvested ?? a.initialBalance ?? a.balance), 0);
  const totalUnrealizedGainLoss = totalInvestments - totalInvestedPrincipal;
  const totalGainLossPct = totalInvestedPrincipal > 0 ? (totalUnrealizedGainLoss / totalInvestedPrincipal) * 100 : 0;
  const totalCreditLimit = creditCards.reduce((sum, a) => sum + (a.creditLimit || 0), 0);
  const netWorth = totalBankAndCash + totalInvestments - totalCreditCardDebt;

  const handleDeleteAccount = (id: string, name: string) => {
    if (accounts.length <= 1) {
      alert('You must keep at least one account or wallet.');
      return;
    }
    if (confirm(`Remove account "${name}"?`)) {
      onUpdateAccounts(accounts.filter(a => a.id !== id));
    }
  };

  const openEditAccount = (acc: Account) => {
    setEditingAccount(acc);
    setEditName(acc.name);
    setEditBankName(acc.brokerName || acc.bankName || '');
    setEditMasked(acc.accountNumberMasked.replace('•••• ', ''));
    setEditInitialBalanceStr(acc.initialBalance !== undefined ? acc.initialBalance.toString() : '0.00');
    setEditValuationStr(acc.currentValuation !== undefined ? acc.currentValuation.toString() : (acc.balance !== undefined ? acc.balance.toString() : '0.00'));
    setEditAssetClass(acc.assetClass || 'Stocks & ETFs');
    setEditCreditLimitStr(acc.creditLimit ? acc.creditLimit.toString() : '20000');
    setEditDueDate(acc.dueDate || '25th of every month');
  };

  const handleEditAccountSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAccount) return;

    const parsedInitial = parseFloat(editInitialBalanceStr);
    const validInitial = isNaN(parsedInitial) ? 0 : parsedInitial;
    const parsedLimit = parseFloat(editCreditLimitStr);
    const parsedValuation = parseFloat(editValuationStr);
    const validValuation = isNaN(parsedValuation) ? undefined : parsedValuation;

    const updatedAccount: Account = {
      ...editingAccount,
      name: editName.trim() || editingAccount.name,
      bankName: editingAccount.type === 'cash' ? undefined : (editBankName.trim() || editingAccount.bankName),
      brokerName: editingAccount.type === 'investment' ? (editBankName.trim() || editingAccount.brokerName) : undefined,
      accountNumberMasked: editMasked.trim() ? (editMasked.startsWith('••••') ? editMasked : `•••• ${editMasked.slice(-4)}`) : editingAccount.accountNumberMasked,
      initialBalance: validInitial,
      currentValuation: editingAccount.type === 'investment' ? (validValuation !== undefined ? validValuation : editingAccount.currentValuation) : undefined,
      assetClass: editingAccount.type === 'investment' ? (editAssetClass as any) : undefined,
      creditLimit: editingAccount.type === 'credit_card' ? (isNaN(parsedLimit) ? 20000 : parsedLimit) : undefined,
      dueDate: editingAccount.type === 'credit_card' ? editDueDate : undefined
    };

    const nextAccounts = accounts.map(a => a.id === updatedAccount.id ? updatedAccount : a);
    const txList = transactions.length > 0 ? transactions : StorageService.getTransactions();
    const recalculated = StorageService.recalculateAccountBalances(nextAccounts, txList);
    onUpdateAccounts(recalculated);
    StorageService.saveAccounts(recalculated);
    setEditingAccount(null);
  };

  const handleVerifyBalances = () => {
    const txList = transactions.length > 0 ? transactions : StorageService.getTransactions();
    const recalculated = StorageService.recalculateAccountBalances(accounts, txList);
    onUpdateAccounts(recalculated);
    StorageService.saveAccounts(recalculated);
    setSyncStatus('✓ Balances Re-verified Against All Transactions');
    setTimeout(() => setSyncStatus(null), 3500);
  };

  // Quick Action: Park / Invest Money into an Investment Account
  const openParkMoneyModal = (targetInvestmentAcc: Account) => {
    setTransferToId(targetInvestmentAcc.id);
    const firstBank = bankAccounts[0]?.id || accounts[0]?.id || '';
    setTransferFromId(firstBank);
    setTransferAmount('');
    setTransferModalOpen(true);
  };

  // Quick Action: Withdraw from an Investment Account to Bank/Cash
  const openWithdrawModal = (sourceInvestmentAcc: Account) => {
    setTransferFromId(sourceInvestmentAcc.id);
    const firstBank = bankAccounts[0]?.id || accounts[0]?.id || '';
    setTransferToId(firstBank);
    setTransferAmount('');
    setTransferModalOpen(true);
  };

  // Open Update Valuation Modal
  const openUpdateValuation = (acc: Account) => {
    setSelectedValuationAccount(acc);
    setNewValuationInput(acc.balance.toString());
    setValuationModalOpen(true);
  };

  const handleUpdateValuationSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedValuationAccount) return;
    const parsed = parseFloat(newValuationInput);
    if (isNaN(parsed) || parsed < 0) return;

    const invested = selectedValuationAccount.totalInvested ?? selectedValuationAccount.initialBalance ?? parsed;
    const gainLoss = Math.round((parsed - invested) * 100) / 100;
    const gainPct = invested > 0 ? Math.round(((parsed - invested) / invested) * 1000) / 10 : 0;

    const updatedAccount: Account = {
      ...selectedValuationAccount,
      currentValuation: parsed,
      balance: parsed,
      unrealizedGainLoss: gainLoss,
      gainLossPercentage: gainPct
    };

    const nextAccounts = accounts.map(a => a.id === updatedAccount.id ? updatedAccount : a);
    const txList = transactions.length > 0 ? transactions : StorageService.getTransactions();
    const recalculated = StorageService.recalculateAccountBalances(nextAccounts, txList);
    onUpdateAccounts(recalculated);
    StorageService.saveAccounts(recalculated);
    setValuationModalOpen(false);
    setSelectedValuationAccount(null);
    setSyncStatus(`✓ Updated valuation for ${selectedValuationAccount.name}`);
    setTimeout(() => setSyncStatus(null), 3500);
  };

  // Handle Pay Credit Card Bill (Anti-double-counting logic)
  const handlePayCardSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(payAmount);
    if (!selectedCardId || !fromBankId || isNaN(amt) || amt <= 0) return;

    const card = accounts.find(a => a.id === selectedCardId);
    const bank = accounts.find(a => a.id === fromBankId);
    if (!card || !bank) return;

    // Record as 'card_payment' type (anti-double-counting)
    onRecordTransaction({
      amount: amt,
      currency: 'AED',
      merchant: `Credit Card Payment (${card.name})`,
      category: 'Other',
      date: new Date().toISOString().split('T')[0],
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      accountId: fromBankId,
      toAccountId: selectedCardId,
      type: 'card_payment',
      source: 'manual',
      bankName: bank.bankName || 'Bank',
      isRedFlag: false,
      isVerifiedByUser: true,
      notes: `Settlement of ${card.name} from ${bank.name}. Not counted as double expense.`
    });

    setPayCardModalOpen(false);
    setPayAmount('');
  };

  // Handle Transfer Between Accounts (Bank <-> Investment <-> Cash)
  const handleTransferSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(transferAmount);
    if (!transferFromId || !transferToId || transferFromId === transferToId || isNaN(amt) || amt <= 0) return;

    const fromAcc = accounts.find(a => a.id === transferFromId);
    const toAcc = accounts.find(a => a.id === transferToId);
    if (!fromAcc || !toAcc) return;

    const isToInvestment = toAcc.type === 'investment';
    const isFromInvestment = fromAcc.type === 'investment';
    const txType = isToInvestment
      ? 'investment_deposit'
      : isFromInvestment
      ? 'investment_withdrawal'
      : 'transfer';

    const merchantTitle = isToInvestment
      ? `Investment Deposit: ${fromAcc.name} → ${toAcc.name}`
      : isFromInvestment
      ? `Investment Withdrawal: ${fromAcc.name} → ${toAcc.name}`
      : `Transfer: ${fromAcc.name} → ${toAcc.name}`;

    const txNotes = isToInvestment
      ? `Parked/Transferred AED ${amt.toFixed(2)} from ${fromAcc.name} into ${toAcc.name}. Not counted as expense.`
      : isFromInvestment
      ? `Withdrawn AED ${amt.toFixed(2)} from ${fromAcc.name} to ${toAcc.name}. Not counted as income or expense.`
      : 'Internal fund transfer. Excluded from monthly expense statistics.';

    onRecordTransaction({
      amount: amt,
      currency: 'AED',
      merchant: merchantTitle,
      category: 'Other',
      date: new Date().toISOString().split('T')[0],
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      accountId: transferFromId,
      toAccountId: transferToId,
      type: txType,
      source: 'manual',
      bankName: fromAcc.bankName || fromAcc.name,
      isRedFlag: false,
      isVerifiedByUser: true,
      notes: txNotes
    });

    setTransferModalOpen(false);
    setTransferAmount('');
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-3.5 sm:p-5 shadow-lg">
      {/* Header with Quick Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Accounts & Credit Cards
          </h3>
          <p className="text-xs text-slate-400">
            Manage your personal bank accounts, cards, and cash wallets
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* AI Bank Statement Import Action Button */}
          <button
            onClick={() => setStatementImportModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-teal-500/20 to-emerald-500/20 hover:from-teal-500/30 hover:to-emerald-500/30 border border-teal-500/40 text-teal-300 text-xs font-bold rounded-xl transition cursor-pointer shadow-sm"
            title="Import bank & credit card statements in PDF, Excel, or CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-teal-400" />
            <span>Import Statement</span>
          </button>

          {/* Add Bank or Credit Card Primary Action */}
          <button
            onClick={onOpenAddAccountModal}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold rounded-xl transition cursor-pointer shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>Add Bank / Card</span>
          </button>

          {/* Recalculate and Verify Balances Action */}
          <button
            onClick={handleVerifyBalances}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-750 border border-slate-700 text-teal-300 text-xs font-semibold rounded-xl transition cursor-pointer"
            title="Recalculate and audit all balances against actual transaction history"
          >
            <RefreshCw className="w-3.5 h-3.5 text-teal-400" />
            <span>Recalculate Balances</span>
          </button>

          {creditCards.length > 0 && (
            <button
              onClick={() => {
                if (creditCards.length > 0) setSelectedCardId(creditCards[0].id);
                if (bankAccounts.length > 0) setFromBankId(bankAccounts[0].id);
                setPayCardModalOpen(true);
              }}
              className="flex items-center gap-1.5 px-3 py-2 bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 text-xs font-semibold rounded-xl transition cursor-pointer"
            >
              <CreditCard className="w-3.5 h-3.5" />
              <span>Pay Card Bill</span>
            </button>
          )}

          {bankAccounts.length > 1 && (
            <button
              onClick={() => {
                if (bankAccounts.length > 0) setTransferFromId(bankAccounts[0].id);
                if (bankAccounts.length > 1) setTransferToId(bankAccounts[1].id);
                setTransferModalOpen(true);
              }}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-750 border border-slate-700 text-teal-300 text-xs font-semibold rounded-xl transition cursor-pointer"
            >
              <ArrowRightLeft className="w-3.5 h-3.5" />
              <span>Transfer</span>
            </button>
          )}
        </div>
      </div>

      {/* Sync Status Banner if triggered */}
      {syncStatus && (
        <div className="mb-4 p-3 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-emerald-300 text-xs flex items-center gap-2 animate-fade-in font-medium">
          <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{syncStatus}</span>
        </div>
      )}

      {/* AI Bank Statement Import Banner */}
      <div className="mb-4 p-3.5 sm:p-4 rounded-2xl bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-teal-500/30 shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0 mt-0.5">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="text-sm font-bold text-white">AI-Powered Bank Statement Import</h4>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30">
                PDF • Excel • CSV
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Upload official statements from Emirates NBD, ADCB, FAB, Mashreq &amp; RAKBANK. Automatic duplicate shielding, opening/closing reconciliation &amp; 1-click ledger posting.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setStatementImportModalOpen(true)}
          className="px-4 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl transition cursor-pointer shrink-0 shadow-lg flex items-center justify-center gap-2"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Upload Statement</span>
        </button>
      </div>

      {/* Aggregate Balance Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
          <span className="text-[11px] text-slate-400">Bank & Cash Liquidity</span>
          <p className="text-lg font-bold text-teal-400 tabular-nums mt-0.5">
            AED {totalBankAndCash.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
          </p>
          <span className="text-[10px] text-slate-500">{bankAccounts.length} Account(s)</span>
        </div>

        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-400">Invested Portfolios</span>
            {totalInvestments > 0 && (
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${totalUnrealizedGainLoss >= 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>
                {totalUnrealizedGainLoss >= 0 ? `+${totalGainLossPct.toFixed(1)}%` : `${totalGainLossPct.toFixed(1)}%`}
              </span>
            )}
          </div>
          <p className="text-lg font-bold text-emerald-400 tabular-nums mt-0.5">
            AED {totalInvestments.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
          </p>
          <span className="text-[10px] text-slate-500">{investmentAccounts.length} Portfolio(s)</span>
        </div>

        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800">
          <span className="text-[11px] text-slate-400">Credit Card Debt</span>
          <p className="text-lg font-bold text-rose-400 tabular-nums mt-0.5">
            AED {totalCreditCardDebt.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
          </p>
          <span className="text-[10px] text-slate-500">{creditCards.length} Card(s)</span>
        </div>

        <div className="bg-slate-950 p-3.5 rounded-xl border border-teal-500/30 bg-gradient-to-br from-slate-950 via-slate-950 to-teal-950/40">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-400 font-bold">Total Net Worth</span>
            <span className="text-[9px] font-bold text-teal-300 bg-teal-500/20 px-1.5 py-0.2 rounded border border-teal-500/30">
              Live
            </span>
          </div>
          <p className="text-lg font-black text-white tabular-nums mt-0.5">
            AED {netWorth.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
          </p>
          <span className="text-[10px] text-teal-400 font-medium">Bank + Invest - Debt</span>
        </div>
      </div>

      {/* Accounts List Grid */}
      <div className="space-y-5">
        {/* Bank & Cash Accounts */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Bank Accounts & Wallets ({bankAccounts.length})
            </h4>
            <button
              onClick={onOpenAddAccountModal}
              className="text-teal-400 hover:underline text-xs flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Account</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {bankAccounts.map(acc => (
              <div
                key={acc.id}
                className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-white"
                    style={{ backgroundColor: acc.color + '25', color: acc.color }}
                  >
                    {acc.type === 'cash' ? <Wallet className="w-5 h-5" /> : <Building className="w-5 h-5" />}
                  </div>
                  <div>
                    <h5 className="text-xs font-bold text-white">{acc.name}</h5>
                    <p className="text-[11px] text-slate-400">
                      {acc.bankName || 'Physical Cash'} · {acc.accountNumberMasked}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-right">
                  <div>
                    <span className="text-xs font-bold text-white tabular-nums">
                      AED {acc.balance.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                    </span>
                    <p className="text-[10px] text-teal-400 font-medium">Available</p>
                  </div>

                  <button
                    onClick={() => openEditAccount(acc)}
                    className="p-1.5 text-slate-400 hover:text-teal-300 transition cursor-pointer opacity-70 group-hover:opacity-100"
                    title="Edit account details or initial balance"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>

                  {accounts.length > 1 && (
                    <button
                      onClick={() => handleDeleteAccount(acc.id, acc.name)}
                      className="p-1.5 text-slate-600 hover:text-rose-400 transition cursor-pointer opacity-70 group-hover:opacity-100"
                      title="Remove account"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Credit Cards */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Credit Cards ({creditCards.length})
            </h4>
            <button
              onClick={onOpenAddAccountModal}
              className="text-teal-400 hover:underline text-xs flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Credit Card</span>
            </button>
          </div>

          {creditCards.length === 0 ? (
            <div className="p-6 bg-slate-950/40 border border-dashed border-slate-800 rounded-xl text-center">
              <CreditCard className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 font-medium">No credit cards added yet</p>
              <button
                onClick={onOpenAddAccountModal}
                className="mt-2.5 px-3 py-1.5 bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/30 text-teal-300 text-xs font-semibold rounded-lg transition"
              >
                + Add Your Credit Card
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {creditCards.map(card => {
                const limit = card.creditLimit || 25000;
                const available = Math.max(0, limit - card.balance);
                const utilization = Math.round((card.balance / limit) * 100);

                return (
                  <div
                    key={card.id}
                    className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 group"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center text-white"
                          style={{ backgroundColor: card.color + '25', color: card.color }}
                        >
                          <CreditCard className="w-4 h-4" />
                        </div>
                        <div>
                          <h5 className="text-xs font-bold text-white">{card.name}</h5>
                          <p className="text-[10px] text-slate-400">
                            {card.bankName} · {card.accountNumberMasked}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-right">
                        <div>
                          <span className="text-xs font-bold text-rose-400 tabular-nums">
                            AED {card.balance.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                          </span>
                          <p className="text-[10px] text-slate-400">Outstanding Debt</p>
                        </div>
                        <button
                          onClick={() => openEditAccount(card)}
                          className="p-1 text-slate-400 hover:text-teal-300 transition cursor-pointer opacity-70 group-hover:opacity-100"
                          title="Edit card details or limit"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteAccount(card.id, card.name)}
                          className="p-1 text-slate-600 hover:text-rose-400 transition cursor-pointer opacity-70 group-hover:opacity-100"
                          title="Remove card"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Utilization Bar */}
                    <div className="mt-3">
                      <div className="flex justify-between text-[10px] text-slate-400 mb-1 tabular-nums">
                        <span>Available: AED {available.toLocaleString()}</span>
                        <span>Limit: AED {limit.toLocaleString()} ({utilization}% used)</span>
                      </div>
                      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${
                            utilization > 70 ? 'bg-rose-500' : 'bg-teal-400'
                          }`}
                          style={{ width: `${Math.min(100, utilization)}%` }}
                        />
                      </div>
                    </div>

                    {card.dueDate && (
                      <div className="mt-2.5 pt-2 border-t border-slate-850 flex items-center justify-between text-[10px]">
                        <span className="text-slate-400 flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-500" />
                          Due: {card.dueDate}
                        </span>
                        <button
                          onClick={() => {
                            setSelectedCardId(card.id);
                            if (bankAccounts.length > 0) setFromBankId(bankAccounts[0].id);
                            setPayAmount(card.balance.toString());
                            setPayCardModalOpen(true);
                          }}
                          className="text-teal-300 hover:text-teal-200 font-semibold cursor-pointer underline"
                        >
                          Pay Balance
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Investment Accounts & Portfolios */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Investment Portfolios &amp; Assets ({investmentAccounts.length})
              </h4>
            </div>
            <button
              onClick={onOpenAddAccountModal}
              className="text-emerald-400 hover:underline text-xs flex items-center gap-1 font-semibold"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>+ Add Investment</span>
            </button>
          </div>

          {investmentAccounts.length === 0 ? (
            <div className="p-6 bg-slate-950/40 border border-dashed border-slate-800 rounded-xl text-center">
              <TrendingUp className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-300 font-bold">No Investment Accounts Connected Yet</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto mt-1">
                Connect your investment accounts (Sarwa, Wio Invest, IBKR, Baraka, Gold, Crypto) to park funds and track portfolio net worth without counting transfers as expenses.
              </p>
              <button
                onClick={onOpenAddAccountModal}
                className="mt-3 px-3.5 py-1.5 bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-bold rounded-lg transition cursor-pointer"
              >
                + Connect Investment Account
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {investmentAccounts.map(inv => {
                const investedPrincipal = inv.totalInvested ?? inv.initialBalance ?? 0;
                const valuation = inv.currentValuation ?? inv.balance;
                const gainLoss = inv.unrealizedGainLoss ?? (valuation - investedPrincipal);
                const gainPct = inv.gainLossPercentage ?? (investedPrincipal > 0 ? (gainLoss / investedPrincipal) * 100 : 0);
                const isPositive = gainLoss >= 0;

                return (
                  <div
                    key={inv.id}
                    className="bg-slate-950/80 border border-slate-800 hover:border-emerald-500/40 rounded-xl p-3.5 transition group flex flex-col justify-between"
                  >
                    <div>
                      {/* Top Row: Icon, Name, Broker & Actions */}
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div
                            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                            style={{ backgroundColor: (inv.color || '#10b981') + '25', color: inv.color || '#10b981' }}
                          >
                            <TrendingUp className="w-5 h-5" />
                          </div>
                          <div className="min-w-0">
                            <h5 className="text-xs font-bold text-white truncate">{inv.name}</h5>
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="text-[10px] text-slate-400">
                                {inv.brokerName || inv.bankName || 'Investment'}
                              </span>
                              {inv.assetClass && (
                                <span className="text-[9px] font-semibold text-emerald-300 bg-emerald-500/15 px-1.5 py-0.2 rounded border border-emerald-500/30">
                                  {inv.assetClass}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            onClick={() => openEditAccount(inv)}
                            className="p-1 text-slate-400 hover:text-teal-300 transition cursor-pointer opacity-70 group-hover:opacity-100"
                            title="Edit account details"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          {accounts.length > 1 && (
                            <button
                              onClick={() => handleDeleteAccount(inv.id, inv.name)}
                              className="p-1 text-slate-600 hover:text-rose-400 transition cursor-pointer opacity-70 group-hover:opacity-100"
                              title="Remove investment account"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Valuation & Capital metrics */}
                      <div className="grid grid-cols-2 gap-2 my-2.5 p-2 rounded-lg bg-slate-900 border border-slate-800/80">
                        <div>
                          <span className="text-[10px] text-slate-400">Current Valuation</span>
                          <p className="text-sm sm:text-base font-black text-emerald-400 tabular-nums">
                            AED {valuation.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400">Invested Capital</span>
                          <p className="text-xs font-bold text-slate-200 tabular-nums">
                            AED {investedPrincipal.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                          </p>
                          <div className={`text-[10px] font-bold tabular-nums mt-0.5 ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isPositive ? '+' : ''}AED {gainLoss.toLocaleString('en-AE', { minimumFractionDigits: 2 })} ({isPositive ? '+' : ''}{gainPct.toFixed(1)}%)
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Action Buttons: Park Money, Withdraw, Update Valuation */}
                    <div className="pt-2 border-t border-slate-850 flex items-center justify-between gap-1 text-[11px]">
                      <button
                        onClick={() => openParkMoneyModal(inv)}
                        className="flex-1 py-1.5 px-2 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 font-bold transition flex items-center justify-center gap-1 cursor-pointer"
                        title="Park/transfer money from Bank or Cash into this investment"
                      >
                        <ArrowUpRight className="w-3.5 h-3.5" />
                        <span>Park Money</span>
                      </button>

                      <button
                        onClick={() => openWithdrawModal(inv)}
                        className="flex-1 py-1.5 px-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition flex items-center justify-center gap-1 cursor-pointer"
                        title="Withdraw funds from investment to bank"
                      >
                        <ArrowDownLeft className="w-3.5 h-3.5" />
                        <span>Withdraw</span>
                      </button>

                      <button
                        onClick={() => openUpdateValuation(inv)}
                        className="py-1.5 px-2 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 font-semibold transition flex items-center justify-center gap-1 cursor-pointer"
                        title="Update current market valuation"
                      >
                        <TrendingUp className="w-3.5 h-3.5" />
                        <span>Valuation</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Pay Credit Card Modal */}
      {payCardModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <form
            onSubmit={handlePayCardSubmit}
            className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl"
          >
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-rose-400" />
                Pay Credit Card Bill
              </h4>
              <button
                type="button"
                onClick={() => setPayCardModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 mb-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Select Credit Card:</label>
                <select
                  value={selectedCardId}
                  onChange={e => setSelectedCardId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                >
                  {creditCards.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} (Due: AED {c.balance.toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Pay From Bank Account:</label>
                <select
                  value={fromBankId}
                  onChange={e => setFromBankId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                >
                  {bankAccounts.map(b => (
                    <option key={b.id} value={b.id}>
                      {b.name} (Balance: AED {b.balance.toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Payment Amount (AED):</label>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  value={payAmount}
                  onChange={e => setPayAmount(e.target.value)}
                  placeholder="e.g. 1500.00"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-bold"
                  required
                />
              </div>

              <div className="p-2.5 rounded-lg bg-teal-950/30 border border-teal-500/20 text-[11px] text-teal-300">
                <span className="font-bold">Anti-Double-Counting Guard:</span> Deducts bank balance and credit card debt without duplicating expenses.
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPayCardModalOpen(false)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-white text-xs font-bold transition"
              >
                Confirm Payment
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Transfer Between Accounts Modal */}
      {transferModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <form
            onSubmit={handleTransferSubmit}
            className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl"
          >
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-teal-400" />
                Transfer Between Accounts
              </h4>
              <button
                type="button"
                onClick={() => setTransferModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 mb-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">From Account:</label>
                <select
                  value={transferFromId}
                  onChange={e => setTransferFromId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                >
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.name} (AED {a.balance.toFixed(2)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">To Account:</label>
                <select
                  value={transferToId}
                  onChange={e => setTransferToId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                >
                  {accounts.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.type === 'investment' ? 'Investment Portfolio' : `AED ${a.balance.toFixed(2)}`})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Amount (AED):</label>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  value={transferAmount}
                  onChange={e => setTransferAmount(e.target.value)}
                  placeholder="e.g. 2000.00"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-bold"
                  required
                />
              </div>

              {/* Smart Contextual Guidance */}
              {accounts.find(a => a.id === transferToId)?.type === 'investment' && (
                <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-[11px] text-emerald-300">
                  <span className="font-bold">✓ Investment Deposit:</span> Parks money into your investment portfolio. Reduces bank balance and increases invested balance without counting as an expense.
                </div>
              )}

              {accounts.find(a => a.id === transferFromId)?.type === 'investment' && (
                <div className="p-2.5 rounded-lg bg-teal-950/40 border border-teal-500/30 text-[11px] text-teal-300">
                  <span className="font-bold">✓ Investment Withdrawal:</span> Withdraws funds back to your liquid bank or cash account. Does not count as income or expense.
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setTransferModalOpen(false)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold transition"
              >
                Execute Transfer
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Update Investment Valuation Modal */}
      {valuationModalOpen && selectedValuationAccount && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <form
            onSubmit={handleUpdateValuationSubmit}
            className="w-full max-w-sm bg-slate-900 border border-emerald-500/40 rounded-2xl p-5 shadow-2xl animate-fade-in"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Update Market Valuation</h4>
                  <p className="text-[10px] text-slate-400">{selectedValuationAccount.name}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setValuationModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3.5 mb-4 text-xs">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex justify-between items-center">
                <span className="text-slate-400 text-[11px]">Total Cash Invested (Principal):</span>
                <span className="font-bold text-slate-200 tabular-nums">
                  AED {(selectedValuationAccount.totalInvested ?? selectedValuationAccount.initialBalance ?? 0).toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                </span>
              </div>

              <div>
                <label className="block text-slate-400 mb-1 font-semibold">
                  Current Portfolio Market Valuation (AED):
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={newValuationInput}
                  onChange={e => setNewValuationInput(e.target.value)}
                  placeholder="e.g. 27500.00"
                  className="w-full bg-slate-950 border border-emerald-500/40 rounded-xl px-3 py-2 text-white font-bold text-sm focus:outline-none focus:border-emerald-400 tabular-nums"
                  required
                  autoFocus
                />
              </div>

              {/* Live Preview of Gain/Loss */}
              {(() => {
                const parsedVal = parseFloat(newValuationInput);
                if (isNaN(parsedVal)) return null;
                const principal = selectedValuationAccount.totalInvested ?? selectedValuationAccount.initialBalance ?? parsedVal;
                const gain = parsedVal - principal;
                const pct = principal > 0 ? (gain / principal) * 100 : 0;
                const isPos = gain >= 0;

                return (
                  <div className={`p-3 rounded-xl border flex items-center justify-between text-xs ${isPos ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300' : 'bg-rose-950/30 border-rose-500/30 text-rose-300'}`}>
                    <span className="font-semibold">Unrealized Gain / Loss:</span>
                    <span className="font-bold tabular-nums">
                      {isPos ? '+' : ''}AED {gain.toLocaleString('en-AE', { minimumFractionDigits: 2 })} ({isPos ? '+' : ''}{pct.toFixed(2)}%)
                    </span>
                  </div>
                );
              })()}

              <p className="text-[10px] text-slate-500">
                Updating valuation recalibrates your total Net Worth and portfolio return automatically without creating expense transactions.
              </p>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setValuationModalOpen(false)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition shadow-lg"
              >
                Save Valuation
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Edit Account Modal */}
      {editingAccount && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
          <form
            onSubmit={handleEditAccountSubmit}
            className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl my-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center">
                  <Edit2 className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-base font-bold text-white">Edit Account &amp; Starting Balance</h4>
                  <p className="text-xs text-slate-400">Update account details and ledger calibration</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEditingAccount(null)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3.5 text-xs mb-5">
              <div>
                <label className="block text-slate-400 mb-1">Account Display Name:</label>
                <input
                  type="text"
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-medium focus:outline-none focus:border-teal-500"
                  required
                />
              </div>

              {editingAccount.type === 'investment' ? (
                <>
                  <div>
                    <label className="block text-slate-400 mb-1">Platform / Broker Name:</label>
                    <input
                      type="text"
                      value={editBankName}
                      onChange={e => setEditBankName(e.target.value)}
                      placeholder="e.g. Sarwa, Wio Invest, IBKR, Baraka, Binance"
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1">Asset Class:</label>
                    <select
                      value={editAssetClass}
                      onChange={e => setEditAssetClass(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-emerald-500"
                    >
                      <option value="Stocks & ETFs">Stocks &amp; ETFs</option>
                      <option value="Crypto">Crypto</option>
                      <option value="Gold & Bullion">Gold &amp; Bullion</option>
                      <option value="Real Estate">Real Estate</option>
                      <option value="Sukuk & Fixed Income">Sukuk &amp; Fixed Income</option>
                      <option value="Mutual Funds">Mutual Funds</option>
                      <option value="General Portfolio">General Portfolio</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-slate-400 mb-1">Initial Invested (AED):</label>
                      <input
                        type="number"
                        step="0.01"
                        value={editInitialBalanceStr}
                        onChange={e => setEditInitialBalanceStr(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-bold font-mono"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 mb-1">Current Valuation (AED):</label>
                      <input
                        type="number"
                        step="0.01"
                        value={editValuationStr}
                        onChange={e => setEditValuationStr(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-emerald-400 text-xs font-bold font-mono"
                        required
                      />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  {editingAccount.type !== 'cash' && (
                    <div>
                      <label className="block text-slate-400 mb-1">Bank Name:</label>
                      <input
                        type="text"
                        value={editBankName}
                        onChange={e => setEditBankName(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-teal-500"
                      />
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    {editingAccount.type !== 'cash' && (
                      <div>
                        <label className="block text-slate-400 mb-1">Last 4 Digits:</label>
                        <input
                          type="text"
                          maxLength={4}
                          value={editMasked}
                          onChange={e => setEditMasked(e.target.value)}
                          placeholder="e.g. 4289"
                          className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-mono"
                        />
                      </div>
                    )}

                    <div className={editingAccount.type === 'cash' ? 'col-span-2' : ''}>
                      <label className="block text-slate-400 mb-1">
                        {editingAccount.type === 'credit_card' ? 'Initial Opening Debt (AED):' : 'Initial Opening Balance (AED):'}
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        value={editInitialBalanceStr}
                        onChange={e => setEditInitialBalanceStr(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-bold font-mono"
                        required
                      />
                    </div>
                  </div>

                  {editingAccount.type === 'credit_card' && (
                    <div className="grid grid-cols-2 gap-3 p-3 bg-slate-950 rounded-xl border border-slate-800">
                      <div>
                        <label className="block text-slate-400 mb-1">Credit Limit (AED):</label>
                        <input
                          type="number"
                          step="100"
                          value={editCreditLimitStr}
                          onChange={e => setEditCreditLimitStr(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs font-bold"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-400 mb-1">Due Date:</label>
                        <input
                          type="text"
                          value={editDueDate}
                          onChange={e => setEditDueDate(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs"
                        />
                      </div>
                    </div>
                  )}
                </>
              )}

              <div className="p-3 bg-teal-950/30 border border-teal-500/20 rounded-xl text-[11px] text-teal-300">
                <span className="font-bold">⚡ Automatic Recalculation:</span> Saving will automatically compute the available balance / portfolio valuation as: <span className="font-mono text-teal-200">Opening Balance + Actual Transactions</span>.
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setEditingAccount(null)}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold shadow cursor-pointer transition"
              >
                Save &amp; Recalculate
              </button>
            </div>
          </form>
        </div>
      )}

      {/* AI Bank Statement Import & Reconciliation Modal */}
      <BankStatementImportModal
        isOpen={statementImportModalOpen}
        onClose={() => setStatementImportModalOpen(false)}
        accounts={accounts}
        transactions={transactions}
        onTransactionsImported={(updatedAccounts, newTransactions) => {
          onUpdateAccounts(updatedAccounts);
          if (onUpdateTransactions) {
            onUpdateTransactions(newTransactions);
          }
          setSyncStatus('Bank statement transactions imported & accounts reconciled successfully');
          setTimeout(() => setSyncStatus(null), 5000);
        }}
      />
    </div>
  );
};
