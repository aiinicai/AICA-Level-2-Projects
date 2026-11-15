import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { EventCategory, StatutoryEvent } from '../types';
import { 
  Calendar as CalendarIcon, 
  Sparkles, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  ExternalLink, 
  Filter, 
  Flame, 
  MapPin, 
  Clock, 
  ChevronRight,
  ShieldCheck,
  Building,
  CalendarRange
} from 'lucide-react';

export const StatutoryCalendar: React.FC = () => {
  const { auth, calendarEvents, refreshCalendarWithAI } = useApp();
  
  // View mode based on role requirements:
  // Admin default: 15-day lookahead; Staff default: 7-day lookahead
  const [viewScope, setViewScope] = useState<'lookahead' | 'allMonth'>(
    auth.role === 'admin' ? 'lookahead' : 'lookahead'
  );

  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshFeedback, setRefreshFeedback] = useState<string | null>(null);

  // Today reference (local date normalized to midnight)
  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const formatLocalDate = (d: Date) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };
  const todayStr = formatLocalDate(todayStart);

  const lookaheadDays = auth.role === 'admin' ? 15 : 7;
  const maxLookaheadDate = new Date(todayStart);
  maxLookaheadDate.setDate(todayStart.getDate() + lookaheadDays);
  maxLookaheadDate.setHours(23, 59, 59, 999);

  const parseEventDate = (dateStr: string) => {
    const parts = dateStr.split('-').map(Number);
    if (parts.length === 3 && !parts.some(isNaN)) {
      return new Date(parts[0], parts[1] - 1, parts[2]);
    }
    return new Date(dateStr);
  };

  // Filter events by lookahead and category
  const filteredEvents = calendarEvents.filter(ev => {
    const evDate = parseEventDate(ev.date);

    // Check lookahead
    if (viewScope === 'lookahead') {
      if (evDate < todayStart || evDate > maxLookaheadDate) {
        return false;
      }
    }

    // Check category
    if (selectedCategory !== 'ALL') {
      if (selectedCategory === 'GAZETTED_HOLIDAY') {
        if (ev.category !== 'GAZETTED_HOLIDAY' && ev.category !== 'HOLIDAY') return false;
      } else if (ev.category !== selectedCategory) {
        return false;
      }
    }

    return true;
  }).sort((a, b) => parseEventDate(a.date).getTime() - parseEventDate(b.date).getTime());

  const handleAiRefresh = async () => {
    setIsRefreshing(true);
    setRefreshFeedback(null);
    try {
      const curYear = today.getFullYear();
      const curMonth = today.getMonth() + 1;
      const res = await refreshCalendarWithAI(curYear, curMonth);
      setRefreshFeedback(res.message);
    } catch (e: any) {
      setRefreshFeedback('Sync failed. Please check internet connection.');
    } finally {
      setIsRefreshing(false);
    }
  };

  const getCategoryBadge = (cat: EventCategory) => {
    switch (cat) {
      case 'GST':
        return { label: 'GST Compliance', bg: 'bg-emerald-100 text-emerald-800 border-emerald-300' };
      case 'INCOME_TAX':
        return { label: 'Income Tax', bg: 'bg-blue-100 text-blue-800 border-blue-300' };
      case 'PUNJAB_FESTIVAL':
        return { label: 'Punjab Festival & Mela', bg: 'bg-amber-100 text-amber-900 border-amber-300' };
      case 'HOLIDAY':
      case 'GAZETTED_HOLIDAY':
        return { label: 'National & Gazetted Holiday', bg: 'bg-rose-100 text-rose-800 border-rose-300' };
      default:
        return { label: 'Statutory Obligation', bg: 'bg-purple-100 text-purple-800 border-purple-300' };
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-teal-700 via-emerald-700 to-amber-600 rounded-2xl p-5 sm:p-6 text-white shadow-lg relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-white/20 backdrop-blur-xs text-white uppercase tracking-wider">
                {auth.role === 'admin' ? 'Admin 15-Day Strategic Outlook' : 'Staff 1-Week Active Lookahead'}
              </span>
              <span className="text-xs text-amber-200 font-semibold">• Punjab &amp; Central Compliance</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Statutory Calendar &amp; National Holidays
            </h2>
            <p className="text-xs sm:text-sm text-emerald-50 mt-1 max-w-2xl">
              Real-time due dates for GST, Income Tax (TDS, Advance Tax, 44AB), Indian National &amp; Gazetted Holidays (Republic Day, Independence Day, Children&apos;s Day, Gandhi Jayanti, Gurpurab) &amp; Punjab Festivals.
            </p>
          </div>

          {/* AI Real-time Sync Button */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <button
              onClick={handleAiRefresh}
              disabled={isRefreshing}
              className="px-4 py-2.5 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-500 hover:to-amber-600 text-slate-950 font-bold rounded-xl shadow-md transition-all text-xs flex items-center justify-center space-x-2 shrink-0 active:scale-95"
            >
              <Sparkles className={`w-4 h-4 text-slate-900 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Gemini AI Syncing...' : 'AI Real-Time Sync (API)'}</span>
            </button>
          </div>
        </div>

        {refreshFeedback && (
          <div className="mt-4 p-2.5 rounded-xl bg-black/20 backdrop-blur-xs border border-white/20 text-xs flex items-center space-x-2 text-white">
            <CheckCircle2 className="w-4 h-4 text-amber-300 shrink-0" />
            <span>{refreshFeedback}</span>
          </div>
        )}
      </div>

      {/* Control Bar: Lookahead Toggle & Category Filter */}
      <div className="bg-white rounded-2xl p-4 shadow-xs border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Lookahead Scope Selector */}
        <div className="flex items-center space-x-1 p-1 bg-slate-100 rounded-xl">
          <button
            onClick={() => setViewScope('lookahead')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center space-x-1.5 ${
              viewScope === 'lookahead'
                ? 'bg-white text-emerald-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <CalendarRange className="w-3.5 h-3.5 text-emerald-600" />
            <span>
              {auth.role === 'admin' ? '15 Days Lookahead (Admin)' : '1 Week Ahead Look (Staff)'}
            </span>
          </button>

          <button
            onClick={() => setViewScope('allMonth')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              viewScope === 'allMonth'
                ? 'bg-white text-emerald-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Full Calendar (All Seasons)
          </button>
        </div>

        {/* Category Filters */}
        <div className="flex items-center space-x-1 overflow-x-auto pb-1 md:pb-0">
          {[
            { id: 'ALL', label: 'All Items' },
            { id: 'GST', label: 'GST Returns' },
            { id: 'INCOME_TAX', label: 'Income Tax' },
            { id: 'GAZETTED_HOLIDAY', label: 'National & Gazetted Holidays' },
            { id: 'PUNJAB_FESTIVAL', label: 'Punjab Festivals & Melas' }
          ].map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                selectedCategory === cat.id
                  ? 'bg-emerald-700 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Lookahead Explanation Badge */}
      <div className="flex items-center justify-between px-2 text-xs text-slate-500">
        <div className="flex items-center space-x-1.5">
          <Clock className="w-4 h-4 text-emerald-600" />
          <span>
            Showing events from <strong>Today ({todayStart.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })})</strong> to{' '}
            <strong>
              {viewScope === 'lookahead'
                ? maxLookaheadDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
                : 'All scheduled dates'}
            </strong>
          </span>
        </div>
        <span className="font-semibold text-slate-700">{filteredEvents.length} Events found</span>
      </div>

      {/* Events Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredEvents.length === 0 ? (
          <div className="col-span-full bg-white rounded-2xl p-12 text-center border border-slate-200">
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <h4 className="font-bold text-slate-800 text-base">No statutory events in this view window</h4>
            <p className="text-xs text-slate-500 mt-1">Switch to &apos;Full Calendar&apos; to view upcoming obligations in future months.</p>
          </div>
        ) : (
          filteredEvents.map(event => {
            const evDate = parseEventDate(event.date);
            const badge = getCategoryBadge(event.category);
            const isToday = event.date === todayStr;
            const daysDiff = Math.round((evDate.getTime() - todayStart.getTime()) / (1000 * 3600 * 24));

            return (
              <div
                key={event.id}
                className={`bg-white rounded-2xl p-5 border transition-all hover:shadow-md flex flex-col justify-between ${
                  isToday
                    ? 'border-amber-400 ring-2 ring-amber-400/30'
                    : event.urgency === 'HIGH'
                    ? 'border-red-200 hover:border-red-300'
                    : 'border-slate-200 hover:border-emerald-300'
                }`}
              >
                <div>
                  {/* Card Header: Category & Date Badge */}
                  <div className="flex items-center justify-between mb-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold border ${badge.bg}`}>
                      {badge.label}
                    </span>

                    <div className="text-right">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${
                        daysDiff < 0
                          ? 'bg-slate-100 text-slate-500'
                          : daysDiff === 0
                          ? 'bg-amber-400 text-slate-900 font-extrabold'
                          : daysDiff <= 3
                          ? 'bg-red-100 text-red-800 font-bold'
                          : 'bg-emerald-50 text-emerald-800'
                      }`}>
                        {daysDiff === 0
                          ? 'Due Today!'
                          : daysDiff < 0
                          ? 'Passed'
                          : `In ${daysDiff} days`}
                      </span>
                    </div>
                  </div>

                  {/* Date & Title */}
                  <div className="flex items-baseline space-x-2 text-xs font-extrabold text-emerald-700 mb-1">
                    <CalendarIcon className="w-3.5 h-3.5" />
                    <span>
                      {evDate.toLocaleDateString('en-IN', {
                        weekday: 'short',
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric'
                      })}
                    </span>
                  </div>

                  <h3 className="font-extrabold text-slate-900 text-base leading-snug tracking-tight">
                    {event.title}
                  </h3>

                  <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                    {event.description}
                  </p>
                </div>

                {/* Footer Portal Link */}
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400 font-medium">
                    Priority: <strong className={event.urgency === 'HIGH' ? 'text-red-600' : 'text-slate-600'}>{event.urgency}</strong>
                  </span>

                  {event.portalLink && (
                    <a
                      href={event.portalLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline"
                    >
                      <span>Open Portal</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
