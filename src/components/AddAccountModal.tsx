import React, { useState } from 'react';
import {
  X,
  CreditCard,
  Building,
  Wallet,
  TrendingUp,
  Plus,
  Check
} from 'lucide-react';
import { Account, AccountType, UAE_BANKS_LIST, UAE_INVESTMENT_PLATFORMS } from '../types/finance';

interface AddAccountModalProps {
  onClose: () => void;
  onAddAccount: (account: Account) => void;
}

const UAE_BANKS = [...UAE_BANKS_LIST];
const UAE_BROKERS = [...UAE_INVESTMENT_PLATFORMS];

const PRESET_COLORS = [
  '#0d9488', // Teal
  '#0284c7', // Sky Blue
  '#e11d48', // Rose / Red
  '#8b5cf6', // Purple
  '#f59e0b', // Amber
  '#10b981', // Emerald
  '#6366f1', // Indigo
  '#0f172a'  // Dark Slate
];

export const AddAccountModal: React.FC<AddAccountModalProps> = ({
  onClose,
  onAddAccount
}) => {
  const [type, setType] = useState<AccountType>('bank');
  const [selectedBank, setSelectedBank] = useState<string>(UAE_BANKS[0]);
  const [customBankName, setCustomBankName] = useState('');
  const [selectedBroker, setSelectedBroker] = useState<string>(UAE_BROKERS[0]);
  const [customBrokerName, setCustomBrokerName] = useState('');
  const [assetClass, setAssetClass] = useState<string>('Stocks & ETFs');
  const [name, setName] = useState('');
  const [last4Digits, setLast4Digits] = useState('');
  const [balanceStr, setBalanceStr] = useState('0.00');
  const [valuationStr, setValuationStr] = useState('0.00');
  const [creditLimitStr, setCreditLimitStr] = useState('20000');
  const [dueDate, setDueDate] = useState('25th of every month');
  const [color, setColor] = useState(PRESET_COLORS[0]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const finalBank = selectedBank === 'Other Bank' ? (customBankName || 'My Bank') : selectedBank;
    const finalBroker = selectedBroker === 'Other Broker / Investment' ? (customBrokerName || 'Investment') : selectedBroker;

    const accountTitle = name.trim() || (
      type === 'investment'
        ? `${finalBroker} (${assetClass})`
        : `${finalBank} ${type === 'credit_card' ? 'Credit Card' : 'Account'}`
    );

    const initialInvested = parseFloat(balanceStr) || 0;
    const currentVal = type === 'investment'
      ? (parseFloat(valuationStr) || initialInvested)
      : (parseFloat(balanceStr) || 0);

    const balance = currentVal;
    const creditLimit = type === 'credit_card' ? (parseFloat(creditLimitStr) || 20000) : undefined;
    const masked = last4Digits.trim()
      ? `•••• ${last4Digits.trim().slice(-4)}`
      : (type === 'cash' ? 'Cash' : type === 'investment' ? 'Invest' : '•••• 0000');

    const newAccount: Account = {
      id: `acc-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      name: accountTitle,
      type,
      bankName: type === 'cash' ? undefined : (type === 'investment' ? finalBroker : finalBank),
      brokerName: type === 'investment' ? finalBroker : undefined,
      accountNumberMasked: masked,
      balance,
      initialBalance: initialInvested,
      totalInvested: type === 'investment' ? initialInvested : undefined,
      currentValuation: type === 'investment' ? currentVal : undefined,
      unrealizedGainLoss: type === 'investment' ? (currentVal - initialInvested) : undefined,
      gainLossPercentage: type === 'investment' && initialInvested > 0 ? ((currentVal - initialInvested) / initialInvested) * 100 : undefined,
      assetClass: type === 'investment' ? (assetClass as any) : undefined,
      creditLimit,
      dueDate: type === 'credit_card' ? dueDate : undefined,
      color: type === 'investment' ? '#10b981' : color
    };

    onAddAccount(newAccount);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/80 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-2xl shadow-2xl flex flex-col max-h-[92vh] sm:max-h-[90vh] overflow-hidden">
        {/* Header - Fixed & sticky */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-950/70 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center">
              <Plus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Add Bank or Credit Card</h3>
              <p className="text-xs text-slate-400">Configure your UAE bank account, card, or wallet</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Modal Body */}
        <div className="overflow-y-auto px-5 py-4 flex-1 min-h-0 space-y-4">
          {/* Account Type Selector */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-4 p-1.5 bg-slate-950 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => {
              setType('bank');
              setColor('#0d9488');
            }}
            className={`py-2 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer ${
              type === 'bank'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Building className="w-3.5 h-3.5" />
            <span>Bank</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setType('credit_card');
              setColor('#e11d48');
            }}
            className={`py-2 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer ${
              type === 'credit_card'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>Card</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setType('cash');
              setColor('#10b981');
            }}
            className={`py-2 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer ${
              type === 'cash'
                ? 'bg-teal-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Wallet className="w-3.5 h-3.5" />
            <span>Cash</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setType('investment');
              setColor('#10b981');
            }}
            className={`py-2 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer ${
              type === 'investment'
                ? 'bg-emerald-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Investment</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          {/* Investment Specific Inputs */}
          {type === 'investment' ? (
            <>
              <div>
                <label className="block text-slate-400 mb-1">Select Investment Platform / Broker:</label>
                <select
                  value={selectedBroker}
                  onChange={e => setSelectedBroker(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-teal-500 cursor-pointer"
                >
                  {UAE_BROKERS.map(b => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>

                {selectedBroker === 'Other Broker / Investment' && (
                  <input
                    type="text"
                    placeholder="Enter Broker / Platform Name (e.g. Interactive Brokers)"
                    value={customBrokerName}
                    onChange={e => setCustomBrokerName(e.target.value)}
                    className="mt-2 w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs"
                    required
                  />
                )}
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Asset Class / Portfolio Type:</label>
                <select
                  value={assetClass}
                  onChange={e => setAssetClass(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-teal-500 cursor-pointer"
                >
                  <option value="Stocks & ETFs">Stocks &amp; Global ETFs (US / UAE)</option>
                  <option value="Crypto">Crypto (Bitcoin, Ethereum, Portfolio)</option>
                  <option value="Gold & Bullion">Physical Gold &amp; Bullion</option>
                  <option value="Real Estate">Real Estate Crowdfunding (Stake / SmartCrowd)</option>
                  <option value="Sukuk & Fixed Income">Sukuk / National Bonds / Fixed Deposit</option>
                  <option value="Mutual Funds">Mutual Funds</option>
                  <option value="General Portfolio">General Diversified Portfolio</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Account / Portfolio Name:</label>
                <input
                  type="text"
                  placeholder="e.g. Sarwa Growth Portfolio, IBKR US Stocks"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-teal-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Total Principal Invested (AED):</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={balanceStr}
                    onChange={e => {
                      setBalanceStr(e.target.value);
                      if (!valuationStr || valuationStr === '0.00' || valuationStr === balanceStr) {
                        setValuationStr(e.target.value);
                      }
                    }}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-bold"
                    required
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Original cash parked</span>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Current Market Valuation (AED):</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={valuationStr}
                    onChange={e => setValuationStr(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-bold text-emerald-400"
                    required
                  />
                  <span className="text-[10px] text-slate-500 mt-0.5 block">Current portfolio value</span>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Bank Dropdown if not Cash */}
              {type !== 'cash' && (
                <div>
                  <label className="block text-slate-400 mb-1">Select Bank / Institution:</label>
                  <select
                    value={selectedBank}
                    onChange={e => setSelectedBank(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-teal-500"
                  >
                    {UAE_BANKS.map(b => (
                      <option key={b} value={b}>
                        {b}
                      </option>
                    ))}
                  </select>

                  {selectedBank === 'Other Bank' && (
                    <input
                      type="text"
                      placeholder="Enter Bank Name"
                      value={customBankName}
                      onChange={e => setCustomBankName(e.target.value)}
                      className="mt-2 w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs"
                      required
                    />
                  )}
                </div>
              )}

              {/* Account Label / Name */}
              <div>
                <label className="block text-slate-400 mb-1">
                  Account Display Name (Optional):
                </label>
                <input
                  type="text"
                  placeholder={
                    type === 'credit_card'
                      ? 'e.g. Cashback Titanium Card, Miles Card'
                      : type === 'bank'
                      ? 'e.g. Salary Current Account, Savings'
                      : 'e.g. Petty Cash, Daily Spending'
                  }
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs focus:outline-none focus:border-teal-500"
                />
              </div>

              {/* Last 4 Digits & Initial Balance */}
              <div className="grid grid-cols-2 gap-3">
                {type !== 'cash' && (
                  <div>
                    <label className="block text-slate-400 mb-1">Card / Account Last 4 Digits:</label>
                    <input
                      type="text"
                      maxLength={4}
                      placeholder="e.g. 4289"
                      value={last4Digits}
                      onChange={e => setLast4Digits(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-mono"
                    />
                  </div>
                )}

                <div className={type === 'cash' ? 'col-span-2' : ''}>
                  <label className="block text-slate-400 mb-1">
                    {type === 'credit_card' ? 'Current Outstanding (AED):' : 'Current Balance (AED):'}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={balanceStr}
                    onChange={e => setBalanceStr(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-bold"
                  />
                </div>
              </div>
            </>
          )}

          {/* Credit Card Specific Fields */}
          {type === 'credit_card' && (
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-950 rounded-xl border border-slate-800">
              <div>
                <label className="block text-slate-400 mb-1">Credit Limit (AED):</label>
                <input
                  type="number"
                  step="100"
                  placeholder="25000"
                  value={creditLimitStr}
                  onChange={e => setCreditLimitStr(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs font-bold"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Monthly Due Date:</label>
                <input
                  type="text"
                  placeholder="e.g. 25th of month"
                  value={dueDate}
                  onChange={e => setDueDate(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white text-xs"
                />
              </div>
            </div>
          )}

          {/* Card Theme Color */}
          <div>
            <label className="block text-slate-400 mb-1.5">Card Theme Color:</label>
            <div className="flex items-center gap-2">
              {PRESET_COLORS.map(c => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className="w-6 h-6 rounded-full flex items-center justify-center transition cursor-pointer"
                  style={{ backgroundColor: c }}
                >
                  {color === c && <Check className="w-3.5 h-3.5 text-white stroke-[3]" />}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons: Cancel and Add Account */}
          <div className="pt-3 pb-3 flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 px-4 bg-slate-800 hover:bg-slate-700 active:bg-slate-700 text-slate-300 hover:text-white font-bold text-xs rounded-xl border border-slate-700 transition cursor-pointer text-center"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 py-3 px-4 bg-teal-500 hover:bg-teal-400 active:bg-teal-300 text-slate-950 font-extrabold text-xs rounded-xl shadow-lg transition cursor-pointer text-center"
            >
              Add {type === 'credit_card' ? 'Credit Card' : type === 'bank' ? 'Bank Account' : type === 'investment' ? 'Investment' : 'Wallet'}
            </button>
          </div>
        </form>
        </div>
      </div>
    </div>
  );
};
