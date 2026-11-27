import React, { useState } from 'react';
import {
  Calendar,
  Clock,
  Plus,
  Tv,
  CheckCircle,
  AlertCircle,
  X,
  CreditCard
} from 'lucide-react';
import { ExpenseCategory, Subscription } from '../types/finance';

interface SubscriptionsTrackerProps {
  subscriptions: Subscription[];
  onUpdateSubscriptions: (subs: Subscription[]) => void;
}

export const POPULAR_UAE_SERVICES = [
  { name: 'Du', category: 'Telecom' as ExpenseCategory, color: '#00a3e0', defaultDay: 1 },
  { name: 'Etisalat', category: 'Telecom' as ExpenseCategory, color: '#719e19', defaultDay: 1 },
  { name: 'Netflix', category: 'Entertainment' as ExpenseCategory, color: '#e50914', defaultDay: 5 },
  { name: 'Amazon Prime', category: 'Entertainment' as ExpenseCategory, color: '#ff9900', defaultDay: 10 },
  { name: 'Noon', category: 'Shopping' as ExpenseCategory, color: '#eab308', defaultDay: 15 },
  { name: 'Talabat', category: 'Food' as ExpenseCategory, color: '#f97316', defaultDay: 20 },
];

export const SubscriptionsTracker: React.FC<SubscriptionsTrackerProps> = ({
  subscriptions,
  onUpdateSubscriptions
}) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState<ExpenseCategory>('Entertainment');
  const [billingDay, setBillingDay] = useState('1');

  const today = new Date();
  const currentDay = today.getDate();

  const totalMonthlyCommitment = subscriptions
    .filter(s => s.active)
    .reduce((sum, s) => sum + s.amount, 0);

  const handleToggle = (id: string) => {
    onUpdateSubscriptions(
      subscriptions.map(s => (s.id === id ? { ...s, active: !s.active } : s))
    );
  };

  const handleAddSubscription = (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(amount);
    const day = parseInt(billingDay, 10);
    if (!name || isNaN(amt) || isNaN(day)) return;

    const matchedService = POPULAR_UAE_SERVICES.find(
      s => s.name.toLowerCase() === name.trim().toLowerCase()
    );

    const newSub: Subscription = {
      id: `sub-${Date.now()}`,
      name: name.trim(),
      amount: amt,
      category,
      billingCycle: 'monthly',
      billingDay: day,
      accountId: 'acc-cash',
      active: true,
      logoText: name.slice(0, 3).toUpperCase(),
      color: matchedService?.color || '#0d9488'
    };

    onUpdateSubscriptions([...subscriptions, newSub]);
    setName('');
    setAmount('');
    setModalOpen(false);
  };

  const handleSelectPreset = (preset: typeof POPULAR_UAE_SERVICES[0]) => {
    setName(preset.name);
    setAmount('');
    setCategory(preset.category);
    setBillingDay(preset.defaultDay.toString());
    setModalOpen(true);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Recurring Bills & Subscriptions
          </h3>
          <p className="text-xs text-slate-400">
            Track fixed UAE monthly obligations (Du, Etisalat, Netflix, Amazon Prime, Noon, Talabat)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] text-slate-400">Total Recurring:</span>
            <p className="text-xs font-bold text-teal-400 tabular-nums">
              AED {totalMonthlyCommitment.toFixed(2)}/mo
            </p>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-lg transition cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Bill</span>
          </button>
        </div>
      </div>

      {/* Quick Add Presets Bar */}
      <div className="mb-5 pb-3 border-b border-slate-800/80">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold text-slate-400">Popular UAE Subscriptions:</span>
          <span className="text-[10px] text-teal-400">Click to add</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {POPULAR_UAE_SERVICES.map(srv => (
            <button
              key={srv.name}
              type="button"
              onClick={() => handleSelectPreset(srv)}
              className="px-3 py-1.5 rounded-lg bg-slate-950/80 hover:bg-slate-800 border border-slate-800 hover:border-teal-500/40 text-slate-300 hover:text-white text-xs font-medium transition cursor-pointer flex items-center gap-2 shadow-sm"
            >
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: srv.color }}></span>
              <span>{srv.name}</span>
            </button>
          ))}
        </div>
      </div>

      {subscriptions.length === 0 ? (
        <div className="text-center py-10 px-4 bg-slate-950/40 rounded-xl border border-dashed border-slate-800">
          <Tv className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-semibold text-slate-300">No active bills or subscriptions added yet</p>
          <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
            Track fixed UAE monthly obligations: Du, Etisalat, Netflix, Amazon Prime, Noon, and Talabat.
          </p>
          <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
            {POPULAR_UAE_SERVICES.map(srv => (
              <button
                key={srv.name}
                type="button"
                onClick={() => handleSelectPreset(srv)}
                className="px-3.5 py-2 rounded-lg bg-slate-850 hover:bg-slate-800 text-slate-200 text-xs font-semibold border border-slate-700/60 transition cursor-pointer flex items-center gap-2 shadow"
              >
                <Plus className="w-3.5 h-3.5 text-teal-400" />
                <span>Add {srv.name}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {subscriptions.map(sub => {
            let daysUntil = sub.billingDay - currentDay;
            if (daysUntil < 0) daysUntil += 30; // next month

            const isDueSoon = daysUntil <= 3 && sub.active;

            return (
              <div
                key={sub.id}
                className={`p-3.5 rounded-xl border flex items-center justify-between transition ${
                  !sub.active
                    ? 'bg-slate-950/40 border-slate-850 opacity-60'
                    : isDueSoon
                    ? 'bg-amber-950/20 border-amber-500/40'
                    : 'bg-slate-950/80 border-slate-800'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs text-white"
                    style={{ backgroundColor: sub.color }}
                  >
                    {sub.logoText}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">{sub.name}</h4>
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>Day {sub.billingDay}</span>
                      <span>·</span>
                      <span className={isDueSoon ? 'text-amber-400 font-bold' : ''}>
                        {daysUntil === 0 ? 'Due Today' : `In ${daysUntil} days`}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs font-bold text-white tabular-nums">
                    AED {sub.amount.toFixed(2)}
                  </span>
                  <div>
                    <button
                      onClick={() => handleToggle(sub.id)}
                      className={`text-[10px] font-semibold mt-1 px-1.5 py-0.5 rounded transition ${
                        sub.active
                          ? 'text-teal-400 hover:text-teal-300'
                          : 'text-slate-500 hover:text-slate-400'
                      }`}
                    >
                      {sub.active ? 'Active' : 'Paused'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <form
            onSubmit={handleAddSubscription}
            className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl"
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-white">Add Recurring Subscription</h4>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Preset Selector Buttons */}
            <div className="mb-3">
              <span className="text-[10px] text-slate-400 block mb-1">Quick Select:</span>
              <div className="flex flex-wrap gap-1.5">
                {POPULAR_UAE_SERVICES.map(srv => (
                  <button
                    key={srv.name}
                    type="button"
                    onClick={() => {
                      setName(srv.name);
                      setCategory(srv.category);
                      setBillingDay(srv.defaultDay.toString());
                    }}
                    className={`px-2 py-1 rounded-md text-[11px] font-medium border transition cursor-pointer ${
                      name.toLowerCase() === srv.name.toLowerCase()
                        ? 'bg-teal-500/20 border-teal-500 text-teal-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {srv.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3 mb-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Service / Bill Name:</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Du, Etisalat, Netflix, Amazon Prime, Noon, Talabat"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Monthly Amount (AED):</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  placeholder="Enter amount (AED)"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-bold"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Billing Day of Month (1-31):</label>
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={billingDay}
                  onChange={e => setBillingDay(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white"
                  required
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold transition"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
