import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Task, StatutoryEvent } from '../types';
import { 
  Calendar as CalendarIcon, 
  Clock, 
  CheckSquare, 
  Square, 
  Flame, 
  Sparkles, 
  X, 
  ChevronRight, 
  AlertCircle,
  FileText,
  CalendarDays,
  UserCheck
} from 'lucide-react';

interface SidebarUpcomingCalendarProps {
  onOpenFullCalendar?: () => void;
}

export const SidebarUpcomingCalendar: React.FC<SidebarUpcomingCalendarProps> = ({ onOpenFullCalendar }) => {
  const { auth, tasks, calendarEvents, toggleTaskComplete } = useApp();

  // Selected date for viewing details in popup drawer/modal
  const [selectedDayDetails, setSelectedDayDetails] = useState<{
    dateStr: string;
    formattedDate: string;
    dayName: string;
    isToday: boolean;
  } | null>(null);

  // Generate 7 upcoming days starting from Today (0 to 6) in local timezone
  const today = new Date();
  const upcoming7Days = Array.from({ length: 7 }).map((_, index) => {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + index);
    const dateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const isToday = index === 0;

    const dayTasks = tasks.filter(t => t.deadline === dateStr);
    const dayStatutory = calendarEvents.filter(e => e.date === dateStr);
    const pendingTasks = dayTasks.filter(t => !t.completed);
    const hasUrgent = dayTasks.some(t => t.isUrgent && !t.completed);

    return {
      date: d,
      dateStr,
      dayName: d.toLocaleDateString('en-IN', { weekday: 'short' }),
      dayNumber: d.getDate(),
      monthShort: d.toLocaleDateString('en-IN', { month: 'short' }),
      formattedDate: d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }),
      isToday,
      dayTasks,
      pendingTasksCount: pendingTasks.length,
      completedTasksCount: dayTasks.length - pendingTasks.length,
      hasUrgent,
      statutoryEvents: dayStatutory
    };
  });

  const handleDayClick = (day: typeof upcoming7Days[0]) => {
    setSelectedDayDetails({
      dateStr: day.dateStr,
      formattedDate: day.formattedDate,
      dayName: day.dayName,
      isToday: day.isToday
    });
  };

  const selectedDayData = selectedDayDetails 
    ? upcoming7Days.find(d => d.dateStr === selectedDayDetails.dateStr)
    : null;

  return (
    <div className="mt-3 pt-2.5 border-t border-amber-200/90">
      {/* Mini Calendar Header behind Quick Launch */}
      <div className="flex items-center justify-between mb-1.5 px-0.5">
        <div className="flex items-center space-x-1.5">
          <CalendarDays className="w-3.5 h-3.5 text-amber-700" />
          <span className="text-[10px] font-black uppercase tracking-wider text-amber-950 hidden sm:inline">
            7-Day Upcoming
          </span>
        </div>
        <span className="text-[9px] font-bold text-amber-800/80 hidden sm:inline">
          {auth.role === 'admin' ? 'Admin View' : 'Staff View'}
        </span>
      </div>

      {/* 7 Upcoming Days List - Compact vertical list on sidebar */}
      <div className="space-y-1">
        {upcoming7Days.map(day => {
          return (
            <button
              key={day.dateStr}
              type="button"
              onClick={() => handleDayClick(day)}
              title={`${day.dayName}, ${day.dayNumber} ${day.monthShort} - ${day.pendingTasksCount} tasks, ${day.statutoryEvents.length} compliance events (Click for details)`}
              className={`w-full text-left p-1 sm:p-1.5 rounded-lg border transition-all flex items-center justify-between text-xs group active:scale-98 ${
                day.isToday
                  ? 'bg-gradient-to-r from-amber-700 to-yellow-700 text-amber-50 border-amber-800 shadow-xs ring-1 ring-amber-400'
                  : 'bg-white hover:bg-amber-100/70 border-amber-200/90 text-amber-950'
              }`}
            >
              {/* Left: Date number & day */}
              <div className="flex items-center space-x-1.5 min-w-0">
                <div className={`w-5 h-5 rounded flex flex-col items-center justify-center text-[10px] font-bold shrink-0 ${
                  day.isToday
                    ? 'bg-amber-800/80 text-amber-100'
                    : 'bg-amber-100 text-amber-900 group-hover:bg-amber-200'
                }`}>
                  <span>{day.dayNumber}</span>
                </div>

                <div className="min-w-0 hidden sm:block">
                  <div className="flex items-center space-x-1">
                    <span className={`text-[10px] font-black leading-tight ${day.isToday ? 'text-amber-50' : 'text-amber-950'}`}>
                      {day.dayName}
                    </span>
                    {day.isToday && (
                      <span className="text-[8px] font-black bg-amber-800/90 text-amber-200 px-1 py-0.1 rounded leading-none">
                        TODAY
                      </span>
                    )}
                  </div>
                  <div className={`text-[9px] truncate leading-tight ${day.isToday ? 'text-amber-200' : 'text-amber-800/70'}`}>
                    {day.monthShort}
                  </div>
                </div>
              </div>

              {/* Right: Indicators (Tasks count & compliance tags) */}
              <div className="flex items-center space-x-1 shrink-0">
                {day.hasUrgent && (
                  <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" title="Urgent Task Due" />
                )}

                {day.pendingTasksCount > 0 && (
                  <span className={`text-[9px] font-bold px-1 rounded leading-tight ${
                    day.isToday 
                      ? 'bg-amber-800 text-amber-100' 
                      : 'bg-amber-100 text-amber-900 border border-amber-300'
                  }`}>
                    {day.pendingTasksCount}t
                  </span>
                )}

                {day.statutoryEvents.length > 0 && (
                  <span className={`text-[8px] font-bold px-1 rounded leading-tight hidden md:inline-block ${
                    day.isToday
                      ? 'bg-amber-800 text-amber-100'
                      : day.statutoryEvents.some(s => s.category === 'GAZETTED_HOLIDAY' || s.category === 'HOLIDAY')
                      ? 'bg-rose-100 text-rose-900 border border-rose-300 font-extrabold'
                      : day.statutoryEvents.some(s => s.category === 'PUNJAB_FESTIVAL')
                      ? 'bg-amber-100 text-amber-900 border border-amber-300'
                      : 'bg-amber-700 text-amber-50'
                  }`}>
                    {day.statutoryEvents.some(s => s.category === 'GAZETTED_HOLIDAY' || s.category === 'HOLIDAY')
                      ? 'Hol'
                      : day.statutoryEvents.some(s => s.category === 'PUNJAB_FESTIVAL')
                      ? 'Fest'
                      : 'Due'}
                  </span>
                )}

                <ChevronRight className={`w-3.5 h-3.5 ${day.isToday ? 'text-amber-200' : 'text-amber-400'} opacity-60 group-hover:opacity-100 transition-opacity hidden sm:block`} />
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-2 text-center hidden sm:block">
        <button
          type="button"
          onClick={onOpenFullCalendar}
          className="text-[10px] font-bold text-amber-800 hover:text-amber-950 hover:underline flex items-center justify-center space-x-1 mx-auto"
        >
          <span>View 15-Day / Full Calendar</span>
          <ChevronRight className="w-3 h-3 text-amber-700" />
        </button>
      </div>

      {/* POPUP MODAL: DAY DETAILS WHILE CLICKING THE CALENDAR */}
      {selectedDayDetails && selectedDayData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-amber-200 overflow-hidden flex flex-col max-h-[85vh]">
            {/* Header in Dark Yellow Gradient */}
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-4 py-3 text-amber-50 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CalendarIcon className="w-4 h-4 text-amber-200" />
                <div>
                  <div className="flex items-center space-x-1.5">
                    <h3 className="font-extrabold text-sm leading-tight text-white">
                      {selectedDayDetails.dayName}, {selectedDayDetails.formattedDate}
                    </h3>
                    {selectedDayDetails.isToday && (
                      <span className="text-[9px] font-black bg-amber-600 text-white px-1 rounded">
                        TODAY
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-amber-200/90 font-medium">
                    Upcoming Tasks &amp; Statutory Compliance Details
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setSelectedDayDetails(null)}
                className="p-1 rounded-lg text-amber-100 hover:text-white hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content Body */}
            <div className="p-4 overflow-y-auto space-y-3.5 text-xs text-amber-950 bg-amber-50/30">
              {/* Statutory compliance & holidays due on this date */}
              <div>
                <span className="text-[10px] font-black uppercase tracking-wider text-amber-900/80 block mb-1">
                  Statutory Due Dates &amp; Punjab Events
                </span>
                {selectedDayData.statutoryEvents.length === 0 ? (
                  <div className="p-2.5 rounded-xl bg-white border border-amber-200/80 text-[11px] text-amber-800/80">
                    No statutory filings or gazetted holidays scheduled on this day.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {selectedDayData.statutoryEvents.map(evt => (
                      <div
                        key={evt.id}
                        className={`p-2.5 rounded-xl border flex items-start space-x-2 ${
                          evt.category === 'GAZETTED_HOLIDAY' || evt.category === 'HOLIDAY'
                            ? 'bg-rose-50 border-rose-200 text-amber-950'
                            : evt.category === 'PUNJAB_FESTIVAL'
                            ? 'bg-amber-100/70 border-amber-300 text-amber-950'
                            : 'bg-white border-amber-200 text-amber-950'
                        }`}
                      >
                        <div className="mt-0.5">
                          {evt.category === 'GAZETTED_HOLIDAY' || evt.category === 'HOLIDAY' ? (
                            <span className="text-[9px] font-black bg-rose-700 text-white px-1.5 py-0.2 rounded">
                              HOLIDAY
                            </span>
                          ) : evt.category === 'PUNJAB_FESTIVAL' ? (
                            <span className="text-[9px] font-black bg-amber-700 text-amber-50 px-1.5 py-0.2 rounded">
                              PUNJAB
                            </span>
                          ) : (
                            <span className="text-[9px] font-black bg-amber-800 text-amber-50 px-1.5 py-0.2 rounded">
                              {evt.category}
                            </span>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-bold text-xs text-amber-950">{evt.title}</div>
                          <div className="text-[10px] text-amber-800/80 font-medium">{evt.description}</div>
                          {(evt.category === 'PUNJAB_FESTIVAL' || evt.category === 'HOLIDAY' || evt.category === 'GAZETTED_HOLIDAY') && (
                            <div className="text-[9px] font-bold text-rose-700 mt-0.5">
                              ★ {evt.category === 'PUNJAB_FESTIVAL' ? 'Punjab Holiday / Festival' : 'Indian National / Gazetted Holiday'}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Tasks due on this day */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-black uppercase tracking-wider text-amber-900/80">
                    Office To-Do Tasks Due ({selectedDayData.dayTasks.length})
                  </span>
                  <span className="text-[10px] text-amber-800 font-bold">
                    {selectedDayData.pendingTasksCount} Pending
                  </span>
                </div>

                {selectedDayData.dayTasks.length === 0 ? (
                  <div className="p-3 rounded-xl bg-white border border-amber-200/80 text-center text-[11px] text-amber-800/80">
                    No client tasks with deadline on this day.
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    {selectedDayData.dayTasks.map(task => (
                      <div
                        key={task.id}
                        className={`p-2 rounded-xl border text-xs flex items-center justify-between gap-2 transition-all ${
                          task.completed
                            ? 'bg-amber-100/40 border-amber-200/60 text-amber-900/40 line-through'
                            : task.isUrgent
                            ? 'bg-red-50/90 border-red-300 text-amber-950'
                            : 'bg-white border-amber-200 text-amber-950'
                        }`}
                      >
                        <div className="flex items-center space-x-2 flex-1 min-w-0">
                          <button
                            type="button"
                            onClick={() => toggleTaskComplete(task.id)}
                            className="shrink-0 text-amber-700"
                            title={task.completed ? 'Mark pending' : 'Tick to complete'}
                          >
                            {task.completed ? (
                              <CheckSquare className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <Square className="w-4 h-4 text-amber-400" />
                            )}
                          </button>

                          <div className="min-w-0 flex-1">
                            <div className="font-bold text-[11px] truncate flex items-center space-x-1">
                              {task.isUrgent && (
                                <span className="text-[8px] font-black bg-red-600 text-white px-1 rounded uppercase">
                                  Urgent
                                </span>
                              )}
                              <span>{task.title}</span>
                            </div>
                            <div className="text-[9px] text-amber-800/80 font-medium flex items-center space-x-1.5">
                              <span>Assignee: {task.assignedTo || 'All Staff'}</span>
                              {task.completed && <span>• Done</span>}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="bg-amber-50 px-4 py-2 border-t border-amber-200 flex items-center justify-end">
              <button
                type="button"
                onClick={() => setSelectedDayDetails(null)}
                className="px-3.5 py-1 bg-amber-700 hover:bg-amber-800 text-amber-50 rounded-lg text-xs font-bold shadow-2xs"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
