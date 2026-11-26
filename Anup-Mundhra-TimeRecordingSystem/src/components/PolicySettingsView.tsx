import React, { useState } from 'react';
import { CalendarOff, Plus, Trash2 } from 'lucide-react';
import { VALIDATION_LIMITS, type Holiday, type LeaveCategory } from '../types/leave';

interface PolicySettingsViewProps {
  categories: LeaveCategory[];
  holidays: Holiday[];
  onSaveCategory: (category: Omit<LeaveCategory, 'updatedAt'>) => Promise<void>;
  onSaveHoliday: (date: string, name: string) => Promise<void>;
  onDeleteHoliday: (holidayId: string) => Promise<void>;
}

export const PolicySettingsView: React.FC<PolicySettingsViewProps> = ({
  categories,
  holidays,
  onSaveCategory,
  onSaveHoliday,
  onDeleteHoliday,
}) => {
  const [catName, setCatName] = useState('');
  const [catCode, setCatCode] = useState('');
  const [catOpening, setCatOpening] = useState('12');
  const [catAccrual, setCatAccrual] = useState('1');
  const [catAllowNeg, setCatAllowNeg] = useState(false);
  const [savingCat, setSavingCat] = useState(false);

  const [holidayDate, setHolidayDate] = useState('');
  const [holidayName, setHolidayName] = useState('');
  const [savingHoliday, setSavingHoliday] = useState(false);

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catName.trim() || !catCode.trim()) return;
    setSavingCat(true);
    try {
      const slug = catName
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_|_$/g, '')
        .slice(0, 48);
      await onSaveCategory({
        id: slug || `cat_${Date.now()}`,
        name: catName.trim(),
        code: catCode.trim().toUpperCase(),
        defaultOpening: Number(catOpening) || 0,
        monthlyAccrual: Number(catAccrual) || 0,
        allowNegative: catAllowNeg,
        requiresReason: true,
        active: true,
      });
      setCatName('');
      setCatCode('');
      setCatOpening('12');
      setCatAccrual('1');
      setCatAllowNeg(false);
    } finally {
      setSavingCat(false);
    }
  };

  const handleToggleActive = async (cat: LeaveCategory) => {
    await onSaveCategory({
      ...cat,
      active: !cat.active,
    });
  };

  const handleAddHoliday = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!holidayDate || !holidayName.trim()) return;
    setSavingHoliday(true);
    try {
      await onSaveHoliday(holidayDate, holidayName.trim());
      setHolidayDate('');
      setHolidayName('');
    } finally {
      setSavingHoliday(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Leave Policy &amp; Company Holidays</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure leave categories available in the employee drop-down, accrual rules, and excluded holiday dates
        </p>
      </div>

      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-base font-semibold text-slate-900">Leave Categories</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-600">
                <th className="py-3 px-6">Category</th>
                <th className="py-3 px-4">Code</th>
                <th className="py-3 px-4 text-right">Default Opening</th>
                <th className="py-3 px-4 text-right">Monthly Accrual</th>
                <th className="py-3 px-4">Negative Allowed</th>
                <th className="py-3 px-6 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {categories.map((cat) => (
                <tr key={cat.id} className="hover:bg-slate-50/70">
                  <td className="py-3 px-6 font-medium text-slate-900">{cat.name}</td>
                  <td className="py-3 px-4 font-mono text-xs text-slate-600">{cat.code}</td>
                  <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                    {cat.defaultOpening}
                  </td>
                  <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-700">
                    +{cat.monthlyAccrual}/mo
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-600">
                    {cat.allowNegative ? 'Yes (Unpaid)' : 'No'}
                  </td>
                  <td className="py-3 px-6 text-right">
                    <button
                      type="button"
                      onClick={() => handleToggleActive(cat)}
                      className={`text-xs font-medium underline underline-offset-2 cursor-pointer ${
                        cat.active ? 'text-emerald-700' : 'text-slate-400'
                      }`}
                    >
                      {cat.active ? 'Active' : 'Disabled'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form
          onSubmit={handleAddCategory}
          className="p-6 bg-slate-50 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-6 gap-3 items-end"
        >
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-slate-700 mb-1">
              New Category Name
            </label>
            <input
              type="text"
              required
              maxLength={VALIDATION_LIMITS.maxCategoryNameLength}
              value={catName}
              onChange={(e) => setCatName(e.target.value)}
              placeholder="e.g., Parental Leave"
              className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Code</label>
            <input
              type="text"
              required
              maxLength={VALIDATION_LIMITS.maxCategoryCodeLength}
              value={catCode}
              onChange={(e) => setCatCode(e.target.value.toUpperCase())}
              placeholder="PL"
              className="w-full px-3 py-2 text-xs font-mono bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Opening (d)</label>
            <input
              type="number"
              step="0.5"
              min="0"
              value={catOpening}
              onChange={(e) => setCatOpening(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono tabular-nums bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Accrual/Mo</label>
            <input
              type="number"
              step="0.25"
              min="0"
              value={catAccrual}
              onChange={(e) => setCatAccrual(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono tabular-nums bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <label className="inline-flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={catAllowNeg}
                onChange={(e) => setCatAllowNeg(e.target.checked)}
                className="rounded border-slate-300"
              />
              Unpaid
            </label>
            <button
              type="submit"
              disabled={savingCat}
              className="inline-flex items-center gap-1 px-3 py-2 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-60"
            >
              <Plus className="w-3.5 h-3.5" />
              Add
            </button>
          </div>
        </form>
      </section>

      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-2">
          <CalendarOff className="w-4 h-4 text-slate-500" />
          <h2 className="text-base font-semibold text-slate-900">
            Company Holidays ({holidays.length})
          </h2>
        </div>

        <div className="divide-y divide-slate-200">
          {holidays.length === 0 ? (
            <div className="p-6 text-sm text-slate-500 text-center">
              No company holidays configured yet.
            </div>
          ) : (
            holidays.map((h) => (
              <div
                key={h.id}
                className="px-6 py-3 flex items-center justify-between gap-4 text-sm hover:bg-slate-50/70"
              >
                <div className="flex items-center gap-4">
                  <span className="font-mono tabular-nums text-xs text-slate-600">{h.date}</span>
                  <span className="font-medium text-slate-900">{h.name}</span>
                </div>
                <button
                  type="button"
                  onClick={() => onDeleteHoliday(h.id)}
                  className="text-slate-400 hover:text-red-700 p-1 cursor-pointer"
                  aria-label={`Remove ${h.name}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>

        <form
          onSubmit={handleAddHoliday}
          className="p-6 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-stretch sm:items-end gap-3"
        >
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Holiday Date</label>
            <input
              type="date"
              required
              value={holidayDate}
              onChange={(e) => setHolidayDate(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono tabular-nums bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-700 mb-1">Holiday Name</label>
            <input
              type="text"
              required
              maxLength={VALIDATION_LIMITS.maxHolidayNameLength}
              value={holidayName}
              onChange={(e) => setHolidayName(e.target.value)}
              placeholder="e.g., Independence Day"
              className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
          <button
            type="submit"
            disabled={savingHoliday}
            className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-60"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Holiday
          </button>
        </form>
      </section>
    </div>
  );
};
