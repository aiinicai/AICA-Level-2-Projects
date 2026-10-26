import React, { useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Check,
  CalendarPlus,
  ExternalLink,
  X,
} from 'lucide-react';
import { NormalizedAlert, AppRow } from '../types';
import { inr, inrS, longD, stateOf } from '../utils/calculations';
import { downloadCalendarEvent, getGoogleCalendarUrl } from '../utils/calendarExport';
import { ItemBadge } from './ItemBadge';

interface Props {
  alerts: NormalizedAlert[];
  onMarkPaid?: (id: string) => void;
  onEdit: (row: AppRow) => void;
  onDelete: (id: string) => void;
}

export const CalendarView: React.FC<Props> = ({
  alerts,
  onMarkPaid,
  onEdit,
  onDelete,
}) => {
  const today = new Date();
  const [currentYear, setCurrentYear] = useState<number>(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState<number>(today.getMonth()); // 0-11
  const [selectedDay, setSelectedDay] = useState<string | null>(null); // YYYY-MM-DD

  // Days in month
  const firstDayOfMonth = new Date(Date.UTC(currentYear, currentMonth, 1));
  const startDayOfWeek = firstDayOfMonth.getUTCDay(); // 0 = Sun
  const daysInMonth = new Date(Date.UTC(currentYear, currentMonth + 1, 0)).getUTCDate();

  const prevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
  };

  const nextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
  };

  const goToToday = () => {
    const now = new Date();
    setCurrentYear(now.getFullYear());
    setCurrentMonth(now.getMonth());
  };

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];

  // Map alerts by YYYY-MM-DD
  const alertsByDate: Record<string, NormalizedAlert[]> = {};
  alerts.forEach((a) => {
    if (a.due) {
      if (!alertsByDate[a.due]) alertsByDate[a.due] = [];
      alertsByDate[a.due].push(a);
    }
  });

  const selectedDayAlerts = selectedDay ? alertsByDate[selectedDay] || [] : [];
  const selectedDayTotal = selectedDayAlerts
    .filter((a) => a.vk === 'due' && !a.paid)
    .reduce((s, a) => s + (a.amount || 0), 0);

  // Month summary total
  const monthPrefix = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`;
  const monthTotalDues = alerts
    .filter((a) => a.due.startsWith(monthPrefix) && a.vk === 'due' && !a.paid)
    .reduce((s, a) => s + (a.amount || 0), 0);

  return (
    <div className="space-y-4">
      {/* Month Navigation Bar */}
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button
              onClick={prevMonth}
              className="p-1.5 rounded-lg border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Previous month"
            >
              <ChevronLeft className="w-4 h-4 text-[#0F1B2D] dark:text-[#E8EDF5]" />
            </button>
            <button
              onClick={nextMonth}
              className="p-1.5 rounded-lg border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Next month"
            >
              <ChevronRight className="w-4 h-4 text-[#0F1B2D] dark:text-[#E8EDF5]" />
            </button>
          </div>

          <h2 className="font-bold text-lg text-[#0F1B2D] dark:text-[#E8EDF5]">
            {monthNames[currentMonth]} {currentYear}
          </h2>

          <button
            onClick={goToToday}
            className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-[#0F1B2D] dark:text-[#E8EDF5] transition"
          >
            Today
          </button>
        </div>

        <div className="text-xs sm:text-sm text-[#46566C] dark:text-[#A9B6C9] flex items-center gap-1">
          <span>Pending in {monthNames[currentMonth].slice(0, 3)}:</span>
          <span className="font-bold text-sm text-[#0B3B66] dark:text-[#5B9BE0]">
            {inrS(monthTotalDues)}
          </span>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl overflow-hidden shadow-xs">
        {/* Days of week header */}
        <div className="grid grid-cols-7 border-b border-[#DCE2EA] dark:border-[#25324A] text-center text-[11px] font-bold uppercase tracking-wider text-[#6F7E92] dark:text-[#8594AA] py-2.5 bg-slate-50/60 dark:bg-slate-900/40">
          <span className="text-rose-600 dark:text-rose-400">Sun</span>
          <span>Mon</span>
          <span>Tue</span>
          <span>Wed</span>
          <span>Thu</span>
          <span>Fri</span>
          <span>Sat</span>
        </div>

        {/* Days grid */}
        <div className="grid grid-cols-7 divide-x divide-y divide-[#DCE2EA] dark:divide-[#25324A] text-xs">
          {/* Empty cells before start of month */}
          {Array.from({ length: startDayOfWeek }).map((_, idx) => (
            <div
              key={`empty-${idx}`}
              className="min-h-16 sm:min-h-24 bg-slate-50/40 dark:bg-slate-900/20 p-1"
            />
          ))}

          {/* Month days */}
          {Array.from({ length: daysInMonth }).map((_, idx) => {
            const dayNum = idx + 1;
            const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(
              dayNum
            ).padStart(2, '0')}`;
            const dayAlerts = alertsByDate[dateStr] || [];
            const daySum = dayAlerts
              .filter((a) => a.vk === 'due' && !a.paid)
              .reduce((s, a) => s + (a.amount || 0), 0);

            const isToday =
              new Date().toISOString().slice(0, 10) === dateStr;
            const isSelected = selectedDay === dateStr;

            return (
              <div
                key={dateStr}
                onClick={() => setSelectedDay(dateStr)}
                className={`min-h-16 sm:min-h-24 p-1 sm:p-2 cursor-pointer transition-all flex flex-col justify-between ${
                  isSelected
                    ? 'bg-[#0E7C86]/10 ring-2 ring-inset ring-[#0E7C86]'
                    : isToday
                    ? 'bg-amber-50/50 dark:bg-amber-950/20'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                }`}
              >
                {/* Day number & Total Rs */}
                <div className="flex items-center justify-between">
                  <span
                    className={`text-xs font-semibold rounded-full w-5 h-5 flex items-center justify-center ${
                      isToday
                        ? 'bg-[#0E7C86] text-white'
                        : 'text-[#0F1B2D] dark:text-[#E8EDF5]'
                    }`}
                  >
                    {dayNum}
                  </span>
                  {daySum > 0 && (
                    <span className="text-[10px] font-bold text-rose-600 dark:text-rose-400 truncate hidden sm:inline">
                      {inrS(daySum)}
                    </span>
                  )}
                </div>

                {/* Day events pills */}
                <div className="space-y-0.5 mt-1 overflow-hidden">
                  {dayAlerts.slice(0, 2).map((a, i) => {
                    const s = stateOf(a);
                    return (
                      <div
                        key={i}
                        className={`text-[9px] sm:text-[10px] font-medium px-1.5 py-0.5 rounded truncate ${
                          a.paid
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                            : s === 'overdue'
                            ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                            : s === 'today'
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                        }`}
                        title={`${a.name}: ${a.amount ? inr(a.amount) : a.label}`}
                      >
                        {a.name}
                      </div>
                    );
                  })}
                  {dayAlerts.length > 2 && (
                    <div className="text-[9px] text-[#6F7E92] dark:text-[#8594AA] font-semibold pl-1">
                      +{dayAlerts.length - 2} more
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Day Details Drawer/Card (Shown when a day is selected) */}
      {selectedDay && (
        <div className="bg-white dark:bg-[#131C2E] border border-[#0E7C86]/40 rounded-2xl p-5 shadow-md space-y-3 animate-fadeIn">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarIcon className="w-5 h-5 text-[#0E7C86]" />
              <h3 className="font-bold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
                {longD(selectedDay)}
              </h3>
              {selectedDayTotal > 0 && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300">
                  Total Due: {inr(selectedDayTotal)}
                </span>
              )}
            </div>

            <button
              onClick={() => setSelectedDay(null)}
              className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="divide-y divide-[#DCE2EA] dark:divide-[#25324A]">
            {selectedDayAlerts.length ? (
              selectedDayAlerts.map((alert) => (
                <div
                  key={alert.row.id + alert.vk}
                  className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <ItemBadge alert={alert} />
                    <div className="truncate">
                      <span className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                        {alert.name}
                      </span>
                      {alert.who && (
                        <span className="ml-1.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[#E7ECF2] dark:bg-[#1E2A40] text-[#0B3B66] dark:text-[#5B9BE0]">
                          {alert.who}
                        </span>
                      )}
                      <div className="text-[#6F7E92] dark:text-[#8594AA] text-[11px]">
                        {alert.label}
                        {alert.sub && ` · ${alert.sub}`}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-2 w-full sm:w-auto">
                    {alert.amount > 0 && (
                      <span className="font-bold text-sm text-[#0F1B2D] dark:text-[#E8EDF5] min-w-20 text-right">
                        {inr(alert.amount)}
                      </span>
                    )}

                    <div className="flex items-center gap-1">
                      {/* Mark Paid */}
                      {alert.row.kind === 'due' && !alert.paid && onMarkPaid && (
                        <button
                          onClick={() => onMarkPaid(alert.row.id)}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950 hover:bg-emerald-100 transition"
                          title="Mark paid"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Paid</span>
                        </button>
                      )}

                      {/* Add to Calendar */}
                      <button
                        onClick={() => downloadCalendarEvent(alert)}
                        className="p-1.5 rounded-lg border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 text-[#0B3B66] dark:text-[#5B9BE0] transition"
                        title="Download .ics event for Phone / Outlook Calendar"
                      >
                        <CalendarPlus className="w-3.5 h-3.5" />
                      </button>

                      <a
                        href={getGoogleCalendarUrl(alert)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 text-emerald-600 transition"
                        title="Add directly to Google Calendar"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-6 text-center text-[#6F7E92] dark:text-[#8594AA]">
                No bills, renewals or expiries on this date.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
