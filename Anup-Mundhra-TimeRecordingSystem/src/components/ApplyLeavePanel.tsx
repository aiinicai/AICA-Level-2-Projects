import React, { useMemo, useState } from 'react';
import { AlertCircle, Calendar, Send } from 'lucide-react';
import {
  calculateWorkingDays,
  datesOverlap,
  getCurrentYear,
  getTodayIsoDate,
  roundDays,
} from '../lib/dateUtils';
import {
  VALIDATION_LIMITS,
  type Employee,
  type HalfDayOption,
  type Holiday,
  type LeaveBalance,
  type LeaveCategory,
  type LeaveRequest,
} from '../types/leave';

interface ApplyLeavePanelProps {
  employee: Employee;
  categories: LeaveCategory[];
  balances: LeaveBalance[];
  myRequests: LeaveRequest[];
  holidays: Holiday[];
  onSubmit: (payload: {
    category: LeaveCategory;
    startDate: string;
    endDate: string;
    halfDay: HalfDayOption;
    workingDays: number;
    reason: string;
  }) => Promise<void>;
}

export const ApplyLeavePanel: React.FC<ApplyLeavePanelProps> = ({
  employee,
  categories,
  balances,
  myRequests,
  holidays,
  onSubmit,
}) => {
  const activeCategories = useMemo(
    () => categories.filter((c) => c.active),
    [categories]
  );

  const today = getTodayIsoDate();
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>(
    () => activeCategories[0]?.id || ''
  );
  const [startDate, setStartDate] = useState<string>(today);
  const [endDate, setEndDate] = useState<string>(today);
  const [halfDay, setHalfDay] = useState<HalfDayOption>('none');
  const [reason, setReason] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const effectiveCategoryId =
    activeCategories.some((c) => c.id === selectedCategoryId)
      ? selectedCategoryId
      : activeCategories[0]?.id || '';

  const selectedCategory = activeCategories.find((c) => c.id === effectiveCategoryId);

  const holidayDateSet = useMemo(
    () => new Set(holidays.map((h) => h.date)),
    [holidays]
  );

  const breakdown = useMemo(
    () =>
      calculateWorkingDays(
        startDate,
        endDate,
        startDate === endDate ? halfDay : 'none',
        holidayDateSet
      ),
    [startDate, endDate, halfDay, holidayDateSet]
  );

  const year = Number(startDate.slice(0, 4)) || getCurrentYear();
  const currentBalance = balances.find(
    (b) => b.employeeId === employee.id && b.year === year && b.categoryId === effectiveCategoryId
  );

  const pendingHoldForCategory = useMemo(
    () =>
      myRequests
        .filter(
          (r) =>
            r.status === 'pending' &&
            r.categoryId === effectiveCategoryId &&
            Number(r.startDate.slice(0, 4)) === year
        )
        .reduce((sum, r) => sum + r.workingDays, 0),
    [myRequests, effectiveCategoryId, year]
  );

  const closingDays = currentBalance
    ? currentBalance.closing
    : (selectedCategory?.defaultOpening ?? 0);
  const availableAfterPending = roundDays(closingDays - pendingHoldForCategory);
  const projectedAfterRequest = roundDays(availableAfterPending - breakdown.workingDays);

  const overlappingExisting = useMemo(() => {
    if (!breakdown.isValidRange) return null;
    return myRequests.find(
      (r) =>
        (r.status === 'pending' || r.status === 'approved') &&
        datesOverlap(startDate, endDate, r.startDate, r.endDate)
    );
  }, [myRequests, startDate, endDate, breakdown.isValidRange]);

  const insufficientBalance =
    selectedCategory &&
    !selectedCategory.allowNegative &&
    breakdown.workingDays > availableAfterPending;

  const missingManager = !employee.managerEmail;
  const isResigned = employee.status !== 'active';

  const canSubmit =
    !submitting &&
    !missingManager &&
    !isResigned &&
    Boolean(selectedCategory) &&
    breakdown.isValidRange &&
    breakdown.workingDays > 0 &&
    !insufficientBalance &&
    !overlappingExisting &&
    reason.trim().length > 0;

  const handleStartChange = (val: string) => {
    setStartDate(val);
    if (endDate < val) {
      setEndDate(val);
    }
    if (val !== endDate) {
      setHalfDay('none');
    }
    setFormError(null);
  };

  const handleEndChange = (val: string) => {
    setEndDate(val);
    if (val !== startDate) {
      setHalfDay('none');
    }
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCategory || !canSubmit) return;

    setFormError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        category: selectedCategory,
        startDate,
        endDate,
        halfDay: startDate === endDate ? halfDay : 'none',
        workingDays: breakdown.workingDays,
        reason: reason.trim(),
      });
      setReason('');
      setHalfDay('none');
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Unable to submit leave request.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Apply for Leave</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {employee.managerEmail
              ? `Routes to reporting manager: ${employee.managerName || employee.managerEmail} (${employee.managerEmail})`
              : 'No reporting manager assigned in the directory'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span>Weekends &amp; company holidays excluded</span>
        </div>
      </div>

      {(missingManager || isResigned) && (
        <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-2.5 text-xs text-amber-800">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            {isResigned
              ? 'Your employee status is marked Resigned. New leave applications are disabled.'
              : 'You cannot submit leave yet because no Reporting Manager Email is mapped for your account in the employee sheet.'}
          </span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 space-y-4">
          <div>
            <label
              htmlFor="leave-category-select"
              className="block text-xs font-medium text-slate-700 mb-1.5"
            >
              Leave Category
            </label>
            <select
              id="leave-category-select"
              value={effectiveCategoryId}
              onChange={(e) => {
                setSelectedCategoryId(e.target.value);
                setFormError(null);
              }}
              className="w-full px-3 py-2.5 text-sm bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
            >
              {activeCategories.map((cat) => {
                const bal = balances.find(
                  (b) => b.employeeId === employee.id && b.year === year && b.categoryId === cat.id
                );
                const avail = bal ? bal.closing : cat.defaultOpening;
                return (
                  <option key={cat.id} value={cat.id}>
                    {cat.name} ({cat.code}) — {cat.allowNegative ? 'Unpaid / Flexible' : `${avail} days closing`}
                  </option>
                );
              })}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="leave-start-date"
                className="block text-xs font-medium text-slate-700 mb-1.5"
              >
                From Date
              </label>
              <input
                id="leave-start-date"
                type="date"
                value={startDate}
                onChange={(e) => handleStartChange(e.target.value)}
                required
                className="w-full px-3 py-2 text-sm font-mono tabular-nums bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>

            <div>
              <label
                htmlFor="leave-end-date"
                className="block text-xs font-medium text-slate-700 mb-1.5"
              >
                To Date
              </label>
              <input
                id="leave-end-date"
                type="date"
                value={endDate}
                min={startDate}
                onChange={(e) => handleEndChange(e.target.value)}
                required
                className="w-full px-3 py-2 text-sm font-mono tabular-nums bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
          </div>

          {startDate === endDate && (
            <div>
              <label
                htmlFor="leave-half-day"
                className="block text-xs font-medium text-slate-700 mb-1.5"
              >
                Duration Option (Single Day)
              </label>
              <select
                id="leave-half-day"
                value={halfDay}
                onChange={(e) => setHalfDay(e.target.value as HalfDayOption)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="none">Full Day (1.0 day)</option>
                <option value="first_half">First Half (0.5 day)</option>
                <option value="second_half">Second Half (0.5 day)</option>
              </select>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="leave-reason"
                className="block text-xs font-medium text-slate-700"
              >
                Reason / Handover Note
              </label>
              <span className="text-xs font-mono tabular-nums text-slate-400">
                {reason.length}/{VALIDATION_LIMITS.maxReasonLength}
              </span>
            </div>
            <textarea
              id="leave-reason"
              rows={3}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                setFormError(null);
              }}
              maxLength={VALIDATION_LIMITS.maxReasonLength}
              placeholder="Briefly state the purpose of leave and any backup coverage..."
              required
              className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900 resize-none"
            />
          </div>
        </div>

        <div className="lg:col-span-5 bg-slate-50 border border-slate-200 rounded-xl p-5 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-900">Leave Impact Summary</h3>

            <dl className="space-y-2.5 text-sm">
              <div className="flex items-center justify-between">
                <dt className="text-slate-600">Net Working Days</dt>
                <dd className="font-mono tabular-nums font-semibold text-slate-900">
                  {breakdown.workingDays} {breakdown.workingDays === 1 ? 'day' : 'days'}
                </dd>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <dt>Calendar / Weekends / Holidays</dt>
                <dd className="font-mono tabular-nums">
                  {breakdown.calendarDays}d / {breakdown.weekendDays}w / {breakdown.holidayDays}h
                </dd>
              </div>

              <div className="border-t border-slate-200 pt-2.5 flex items-center justify-between">
                <dt className="text-slate-600">Current Closing Balance</dt>
                <dd className="font-mono tabular-nums font-medium text-slate-900">
                  {closingDays} days
                </dd>
              </div>
              {pendingHoldForCategory > 0 && (
                <div className="flex items-center justify-between text-xs text-amber-700">
                  <dt>Already Pending Approval</dt>
                  <dd className="font-mono tabular-nums">−{pendingHoldForCategory} days</dd>
                </div>
              )}
              <div className="flex items-center justify-between pt-1">
                <dt className="font-medium text-slate-900">Projected Closing</dt>
                <dd
                  className={`font-mono tabular-nums font-semibold ${
                    insufficientBalance ? 'text-red-700' : 'text-emerald-700'
                  }`}
                >
                  {projectedAfterRequest} days
                </dd>
              </div>
            </dl>

            {breakdown.isValidRange && breakdown.workingDays === 0 && (
              <p className="text-xs text-amber-700 leading-relaxed">
                The selected date range falls entirely on weekends or company holidays (0 working days).
              </p>
            )}
            {insufficientBalance && (
              <p className="text-xs text-red-700 leading-relaxed">
                Insufficient available balance for {selectedCategory?.name}. Choose Loss of Pay (Unpaid) or shorten the date range.
              </p>
            )}
            {overlappingExisting && (
              <p className="text-xs text-red-700 leading-relaxed">
                Overlaps with an existing {overlappingExisting.status} leave ({overlappingExisting.startDate} to {overlappingExisting.endDate}).
              </p>
            )}
            {formError && (
              <p className="text-xs text-red-700 leading-relaxed">{formError}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
            {submitting ? 'Submitting...' : 'Submit Leave Request'}
          </button>
        </div>
      </form>
    </section>
  );
};
