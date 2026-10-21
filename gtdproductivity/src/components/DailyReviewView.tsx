import React, { useState, useMemo } from 'react';
import { Item, ProjectType } from '../types/gtd';
import { storage } from '../services/storage';
import { 
  CheckCircle2, 
  Circle, 
  Clock, 
  Users, 
  Sparkles, 
  ArrowRight, 
  Plus, 
  CheckCheck, 
  AlertCircle, 
  Calendar, 
  MessageSquare, 
  Send, 
  Trash2, 
  Search,
  Inbox,
  PlayCircle,
  X,
  BookmarkCheck
} from 'lucide-react';

interface DailyReviewViewProps {
  inboxItems: Item[];
  waitingForItems: Item[];
  somedayMaybeItems: Item[];
  nextActions: Item[];
  projects: Item[];
  lastDailyReview: string | null;
  onCompleteDailyReview: () => void;
  onStartClarify: () => void;
  onOpenCapture: () => void;
  onToggleComplete: (id: string) => void;
  onActivateSomedayMaybe: (id: string, context?: string | null) => void;
  onResolveWaitingFor: (id: string, resolution: 'complete' | 'next_action') => void;
  onLogWaitingForFollowUp: (id: string, note?: string) => void;
  onAddWaitingForItem: (title: string, person: string, notes?: string, context?: string | null) => void;
  onAddSomedayMaybeItem: (title: string, notes?: string, context?: string | null) => void;
  onClarifyDoNow: (id: string) => void;
  onClarifyTrash: (id: string) => void;
  onClarifySomedayMaybe: (id: string) => void;
  onClarifyConvertToProject: (id: string, projectTitle: string, projectType: ProjectType, firstActionTitle: string) => void;
}

interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  iconName: string;
}

const DEFAULT_CHECKLIST: ChecklistItem[] = [
  {
    id: 'chk-physical',
    title: 'Gather physical & loose inputs',
    description: 'Empty desktop receipts, loose notebook pages, sticky notes, and paper trays into inbox.',
    iconName: 'inbox',
  },
  {
    id: 'chk-digital',
    title: 'Scan communication channels to zero',
    description: 'Triage email inboxes, Slack/Teams DMs, voicemails, and browser reading tabs.',
    iconName: 'mail',
  },
  {
    id: 'chk-two-min',
    title: 'Execute the 2-Minute Rule immediately',
    description: 'If an actionable inbox item takes less than 2 minutes, do it right now without deferring.',
    iconName: 'clock',
  },
  {
    id: 'chk-delegate-defer',
    title: 'Delegate or Defer all multi-minute actions',
    description: 'Assign delegated work to "Waiting For" with an owner, or assign concrete next actions.',
    iconName: 'users',
  },
  {
    id: 'chk-inbox-zero',
    title: 'Achieve Inbox Zero in GTD Trusted System',
    description: 'Confirm all captured inbox items are clarified into their rightful home list.',
    iconName: 'check',
  },
];

export const DailyReviewView: React.FC<DailyReviewViewProps> = ({
  inboxItems,
  waitingForItems,
  somedayMaybeItems,
  nextActions,
  projects,
  lastDailyReview,
  onCompleteDailyReview,
  onStartClarify,
  onOpenCapture,
  onToggleComplete,
  onActivateSomedayMaybe,
  onResolveWaitingFor,
  onLogWaitingForFollowUp,
  onAddWaitingForItem,
  onAddSomedayMaybeItem,
  onClarifyDoNow,
  onClarifyTrash,
  onClarifySomedayMaybe,
  onClarifyConvertToProject,
}) => {
  // Navigation tabs within the Daily Review
  const [activeTab, setActiveTab] = useState<'all' | 'inbox_checklist' | 'waiting_for' | 'someday_maybe' | 'daily_alignment'>('all');

  // Interactive inbox clearing checklist state
  const [checklist, setChecklist] = useState<Record<string, boolean>>(() => storage.getDailyChecklist());

  // Follow-up modal / form state for Waiting For
  const [followUpItemId, setFollowUpItemId] = useState<string | null>(null);
  const [followUpNote, setFollowUpNote] = useState('');

  // Add Waiting For form state
  const [isAddingWaitingFor, setIsAddingWaitingFor] = useState(false);
  const [newWfTitle, setNewWfTitle] = useState('');
  const [newWfPerson, setNewWfPerson] = useState('');
  const [newWfNotes, setNewWfNotes] = useState('');
  const [newWfContext, setNewWfContext] = useState('@office');

  // Add Someday/Maybe form state
  const [isAddingSomeday, setIsAddingSomeday] = useState(false);
  const [newSmTitle, setNewSmTitle] = useState('');
  const [newSmNotes, setNewSmNotes] = useState('');
  const [newSmContext, setNewSmContext] = useState('@home');

  // Daily reflection notes
  const [dailyNotes, setDailyNotes] = useState(() => {
    try {
      return localStorage.getItem('gtd_daily_review_notes') || '';
    } catch {
      return '';
    }
  });
  const [justCompletedReview, setJustCompletedReview] = useState(false);

  // Search/filter states for Waiting For and Someday/Maybe
  const [wfSearch, setWfSearch] = useState('');
  const [smSearch, setSmSearch] = useState('');

  const toggleChecklistItem = (id: string) => {
    setChecklist(prev => {
      const next = { ...prev, [id]: !prev[id] };
      storage.saveDailyChecklist(next);
      return next;
    });
  };

  const handleSaveDailyNotes = (text: string) => {
    setDailyNotes(text);
    try {
      localStorage.setItem('gtd_daily_review_notes', text);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFinishReview = () => {
    onCompleteDailyReview();
    setJustCompletedReview(true);
    setTimeout(() => setJustCompletedReview(false), 5000);
  };

  // Check if review was done today
  const isReviewedToday = useMemo(() => {
    if (!lastDailyReview) return false;
    const reviewDate = new Date(lastDailyReview);
    const today = new Date();
    return (
      reviewDate.getFullYear() === today.getFullYear() &&
      reviewDate.getMonth() === today.getMonth() &&
      reviewDate.getDate() === today.getDate()
    );
  }, [lastDailyReview]);

  // Compute checklist progress
  const checklistCheckedCount = DEFAULT_CHECKLIST.filter(c => checklist[c.id]).length;
  const isInboxZero = inboxItems.length === 0;

  // Filtered waiting for items
  const filteredWaitingFor = useMemo(() => {
    if (!wfSearch.trim()) return waitingForItems;
    const q = wfSearch.toLowerCase().trim();
    return waitingForItems.filter(item => 
      item.title.toLowerCase().includes(q) ||
      (item.waitingForPerson && item.waitingForPerson.toLowerCase().includes(q)) ||
      (item.notes && item.notes.toLowerCase().includes(q))
    );
  }, [waitingForItems, wfSearch]);

  // Filtered someday items
  const filteredSomeday = useMemo(() => {
    if (!smSearch.trim()) return somedayMaybeItems;
    const q = smSearch.toLowerCase().trim();
    return somedayMaybeItems.filter(item => 
      item.title.toLowerCase().includes(q) ||
      (item.notes && item.notes.toLowerCase().includes(q)) ||
      (item.context && item.context.toLowerCase().includes(q))
    );
  }, [somedayMaybeItems, smSearch]);

  // Calculate days waiting helper
  const getDaysWaiting = (waitingSince?: string | null, createdAt?: string) => {
    const dateStr = waitingSince || createdAt;
    if (!dateStr) return 0;
    const start = new Date(dateStr).getTime();
    const now = Date.now();
    const diffDays = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    return Math.max(0, diffDays);
  };

  // Tasks due within 24 hours
  const dueSoonTasks = useMemo(() => {
    const now = new Date();
    return nextActions.filter(item => {
      if (!item.dueDate) return false;
      const due = new Date(item.dueDate);
      const diffHours = (due.getTime() - now.getTime()) / (1000 * 60 * 60);
      return diffHours >= 0 && diffHours <= 24;
    });
  }, [nextActions]);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner: Daily Calibration & Review Status */}
      <div className="bg-gradient-to-r from-slate-900 via-teal-950 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-md relative overflow-hidden">
        {/* Subtle decorative background glow */}
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute right-40 -bottom-20 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold tracking-wide border border-teal-400/30">
              <Sparkles className="w-3.5 h-3.5" />
              <span>David Allen GTD Protocol</span>
              <span className="text-teal-400/50">·</span>
              <span>Daily Perspective & Calibration</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Daily Review & Inbox Clearing
            </h1>
            <p className="text-slate-300 text-xs sm:text-sm leading-relaxed">
              Clear your mind, calibrate open loops, follow up on delegated dependencies in{' '}
              <strong className="text-teal-300 font-semibold">Waiting For</strong>, and incubate possibilities in{' '}
              <strong className="text-purple-300 font-semibold">Someday/Maybe</strong>.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            {isReviewedToday ? (
              <div className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500/20 border border-emerald-400/40 rounded-xl text-emerald-300 text-xs font-semibold">
                <BookmarkCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="font-bold text-emerald-200">Reviewed Today</div>
                  <div className="text-[10px] text-emerald-300/80 font-mono">
                    {new Date(lastDailyReview!).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3.5 py-2.5 bg-amber-500/15 border border-amber-400/30 rounded-xl text-amber-200 text-xs font-medium">
                <AlertCircle className="w-4 h-4 text-amber-300 shrink-0" />
                <span>Daily review recommended</span>
              </div>
            )}

            <button
              onClick={handleFinishReview}
              className={`px-4 py-2.5 text-xs font-bold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-2 shadow-sm ${
                justCompletedReview
                  ? 'bg-emerald-600 text-white'
                  : 'bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold hover:shadow-teal-500/25'
              }`}
            >
              <CheckCheck className="w-4 h-4" />
              <span>{isReviewedToday ? 'Update Review Timestamp' : 'Mark Review Complete'}</span>
            </button>
          </div>
        </div>

        {justCompletedReview && (
          <div className="mt-4 p-3 bg-emerald-500/30 border border-emerald-400/50 rounded-xl text-xs text-emerald-200 font-medium flex items-center gap-2 animate-bounce">
            <CheckCircle2 className="w-4 h-4 text-emerald-300 shrink-0" />
            <span>Well done! Daily Review logged. Your trusted system is calibrated for the day.</span>
          </div>
        )}

        {/* Review Stage Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-slate-800/80">
          <button
            onClick={() => setActiveTab('inbox_checklist')}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeTab === 'inbox_checklist' 
                ? 'bg-white/10 border-teal-400/50 shadow-xs' 
                : 'bg-white/5 border-white/5 hover:bg-white/8'
            }`}
          >
            <div className="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Inbox Clearing</span>
              <Inbox className="w-3.5 h-3.5 text-rose-400" />
            </div>
            <div className="text-lg font-bold mt-1 text-white flex items-center gap-1.5">
              <span>{inboxItems.length} items</span>
              {isInboxZero ? (
                <span className="text-[10px] text-emerald-400 bg-emerald-500/20 px-1.5 py-0.2 rounded font-mono">Zero</span>
              ) : (
                <span className="text-[10px] text-rose-400 bg-rose-500/20 px-1.5 py-0.2 rounded font-mono">Pending</span>
              )}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {checklistCheckedCount} of {DEFAULT_CHECKLIST.length} checklist steps
            </div>
          </button>

          <button
            onClick={() => setActiveTab('waiting_for')}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeTab === 'waiting_for' 
                ? 'bg-white/10 border-teal-400/50 shadow-xs' 
                : 'bg-white/5 border-white/5 hover:bg-white/8'
            }`}
          >
            <div className="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Waiting For</span>
              <Users className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <div className="text-lg font-bold mt-1 text-white">
              {waitingForItems.length} delegated
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Check external responses
            </div>
          </button>

          <button
            onClick={() => setActiveTab('someday_maybe')}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeTab === 'someday_maybe' 
                ? 'bg-white/10 border-teal-400/50 shadow-xs' 
                : 'bg-white/5 border-white/5 hover:bg-white/8'
            }`}
          >
            <div className="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Someday/Maybe</span>
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="text-lg font-bold mt-1 text-white">
              {somedayMaybeItems.length} parked
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Incubated ideas to activate
            </div>
          </button>

          <button
            onClick={() => setActiveTab('daily_alignment')}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeTab === 'daily_alignment' 
                ? 'bg-white/10 border-teal-400/50 shadow-xs' 
                : 'bg-white/5 border-white/5 hover:bg-white/8'
            }`}
          >
            <div className="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Today's Horizon</span>
              <Calendar className="w-3.5 h-3.5 text-teal-400" />
            </div>
            <div className="text-lg font-bold mt-1 text-white">
              {dueSoonTasks.length} due soon
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Hard landscape & deadlines
            </div>
          </button>
        </div>
      </div>

      {/* Review Section Navigation Filter Tabs */}
      <div className="flex items-center gap-1.5 p-1.5 bg-slate-200/70 rounded-xl overflow-x-auto text-xs font-semibold">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'all'
              ? 'bg-white text-slate-900 shadow-2xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Complete Review (All Steps)
        </button>
        <button
          onClick={() => setActiveTab('inbox_checklist')}
          className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'inbox_checklist'
              ? 'bg-white text-rose-700 shadow-2xs'
              : 'text-slate-600 hover:text-rose-700'
          }`}
        >
          <Inbox className="w-3.5 h-3.5" />
          <span>1. Inbox Clearing ({inboxItems.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('waiting_for')}
          className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'waiting_for'
              ? 'bg-white text-blue-700 shadow-2xs'
              : 'text-slate-600 hover:text-blue-700'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>2. Waiting For List ({waitingForItems.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('someday_maybe')}
          className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'someday_maybe'
              ? 'bg-white text-purple-700 shadow-2xs'
              : 'text-slate-600 hover:text-purple-700'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>3. Someday / Maybe List ({somedayMaybeItems.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('daily_alignment')}
          className={`px-3.5 py-1.5 rounded-lg transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === 'daily_alignment'
              ? 'bg-white text-teal-700 shadow-2xs'
              : 'text-slate-600 hover:text-teal-700'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          <span>4. Today's Horizon</span>
        </button>
      </div>

      {/* ======================================================== */}
      {/* SECTION 1: INBOX CLEARING CHECKLIST & TRIAGE             */}
      {/* ======================================================== */}
      {(activeTab === 'all' || activeTab === 'inbox_checklist') && (
        <section className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-2xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-rose-100 text-rose-700 flex items-center justify-center font-bold text-xs">
                  1
                </span>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Inbox Clearing & Triage Checklist
                </h2>
              </div>
              <p className="text-xs text-slate-500 leading-normal pl-8">
                Collect all inputs into zero and process every inbox item using the David Allen workflow decision tree.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0 pl-8 sm:pl-0">
              {isInboxZero ? (
                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Inbox Zero reached</span>
                </div>
              ) : (
                <button
                  onClick={onStartClarify}
                  className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
                >
                  <ArrowRight className="w-3.5 h-3.5" />
                  <span>Clarify Inbox ({inboxItems.length})</span>
                </button>
              )}
            </div>
          </div>

          {/* Interactive Checklist Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {DEFAULT_CHECKLIST.map((step) => {
              const isChecked = Boolean(checklist[step.id]);
              return (
                <div
                  key={step.id}
                  onClick={() => toggleChecklistItem(step.id)}
                  className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer flex items-start gap-3 select-none ${
                    isChecked
                      ? 'bg-teal-50/50 border-teal-200 text-slate-900'
                      : 'bg-slate-50/70 hover:bg-slate-50 border-slate-200 text-slate-700'
                  }`}
                >
                  <button
                    type="button"
                    aria-label={`Mark ${step.title} complete`}
                    className="mt-0.5 text-teal-600 shrink-0 cursor-pointer"
                  >
                    {isChecked ? (
                      <CheckCircle2 className="w-5 h-5 fill-teal-600 text-white" />
                    ) : (
                      <Circle className="w-5 h-5 text-slate-400 hover:text-teal-600" />
                    )}
                  </button>
                  <div className="space-y-0.5 min-w-0">
                    <p className={`text-xs font-bold ${isChecked ? 'line-through text-slate-500' : 'text-slate-800'}`}>
                      {step.title}
                    </p>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Live Inbox Preview and Quick Triage if items exist */}
          {inboxItems.length > 0 ? (
            <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-600 font-semibold">
                <span>Items currently in Inbox ({inboxItems.length})</span>
                <span className="text-[11px] text-slate-400">Apply the 2-Minute Rule or triage:</span>
              </div>

              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {inboxItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 bg-white rounded-xl border border-slate-200 hover:border-slate-300 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs transition-all"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                        <h4 className="text-xs font-semibold text-slate-800 truncate">
                          {item.title}
                        </h4>
                        {item.context && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded font-mono bg-slate-100 text-slate-600 border border-slate-200">
                            {item.context}
                          </span>
                        )}
                      </div>
                      {item.notes && (
                        <p className="text-[11px] text-slate-500 truncate pl-4">
                          {item.notes}
                        </p>
                      )}
                    </div>

                    {/* Quick Triage Buttons */}
                    <div className="flex items-center gap-1.5 shrink-0 pl-4 sm:pl-0">
                      <button
                        onClick={() => onClarifyDoNow(item.id)}
                        title="2-Minute Rule: Done right now"
                        className="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded text-[11px] font-semibold transition-colors cursor-pointer flex items-center gap-1"
                      >
                        <CheckCheck className="w-3 h-3 text-emerald-600" />
                        <span>Do Now</span>
                      </button>
                      <button
                        onClick={() => onClarifySomedayMaybe(item.id)}
                        title="Park into Someday / Maybe"
                        className="px-2 py-1 bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 rounded text-[11px] font-semibold transition-colors cursor-pointer flex items-center gap-1"
                      >
                        <Sparkles className="w-3 h-3 text-purple-600" />
                        <span>Someday</span>
                      </button>
                      <button
                        onClick={() => onClarifyTrash(item.id)}
                        title="Delete / Not Actionable"
                        className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-xl flex items-center gap-3 text-xs text-emerald-800">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <div>
                <strong className="font-bold">Zero items in GTD Inbox!</strong> You have no unprocessed attention loops. Every incoming item has been filed into its active or reference home.
              </div>
            </div>
          )}
        </section>
      )}

      {/* ======================================================== */}
      {/* SECTION 2: CHECK 'WAITING FOR' LIST (DELEGATIONS)        */}
      {/* ======================================================== */}
      {(activeTab === 'all' || activeTab === 'waiting_for') && (
        <section className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-2xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
                  2
                </span>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Check 'Waiting For' List (Delegated Work)
                </h2>
                <span className="text-xs font-mono font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-200">
                  {waitingForItems.length}
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-normal pl-8">
                David Allen: "Review who owes you what and trigger any necessary follow-ups before projects stall."
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0 pl-8 sm:pl-0">
              <button
                onClick={() => setIsAddingWaitingFor(prev => !prev)}
                className="px-3.5 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-800 border border-blue-200 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Delegated Item</span>
              </button>
            </div>
          </div>

          {/* Quick Add Waiting For Form */}
          {isAddingWaitingFor && (
            <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-xl space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-blue-900">Add Delegated Item to 'Waiting For'</h4>
                <button
                  onClick={() => setIsAddingWaitingFor(false)}
                  className="text-slate-400 hover:text-slate-700 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="What are you waiting for? (e.g. Countersigned contract, Code review)"
                  value={newWfTitle}
                  onChange={(e) => setNewWfTitle(e.target.value)}
                  className="px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-blue-500"
                />
                <input
                  type="text"
                  placeholder="Delegated to person / entity (e.g. Marcus, IT Helpdesk)"
                  value={newWfPerson}
                  onChange={(e) => setNewWfPerson(e.target.value)}
                  className="px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Additional context or email subject notes..."
                  value={newWfNotes}
                  onChange={(e) => setNewWfNotes(e.target.value)}
                  className="sm:col-span-2 px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-blue-500"
                />
                <select
                  value={newWfContext}
                  onChange={(e) => setNewWfContext(e.target.value)}
                  className="px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-blue-500"
                >
                  <option value="@office">@office</option>
                  <option value="@phone">@phone</option>
                  <option value="@computer">@computer</option>
                  <option value="@home">@home</option>
                  <option value="@errands">@errands</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <button
                  onClick={() => setIsAddingWaitingFor(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  disabled={!newWfTitle.trim() || !newWfPerson.trim()}
                  onClick={() => {
                    onAddWaitingForItem(newWfTitle, newWfPerson, newWfNotes, newWfContext);
                    setNewWfTitle('');
                    setNewWfPerson('');
                    setNewWfNotes('');
                    setIsAddingWaitingFor(false);
                  }}
                  className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                >
                  Save to Waiting For
                </button>
              </div>
            </div>
          )}

          {/* Search bar inside Waiting For */}
          {waitingForItems.length > 2 && (
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Filter delegated items by person, title, or notes..."
                value={wfSearch}
                onChange={(e) => setWfSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg outline-none focus:bg-white focus:border-blue-500"
              />
            </div>
          )}

          {/* List of Waiting For Items */}
          {filteredWaitingFor.length === 0 ? (
            <div className="p-8 text-center bg-slate-50 border border-dashed border-slate-200 rounded-xl space-y-2">
              <Users className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs font-semibold text-slate-700">No delegated items in Waiting For</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                When you delegate a deliverable or request information from colleagues or vendors, record it here so nothing slips through the cracks.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredWaitingFor.map((item) => {
                const daysWaiting = getDaysWaiting(item.waitingSince, item.createdAt);
                const isStale = daysWaiting >= 4;

                return (
                  <div
                    key={item.id}
                    className="p-4 bg-white rounded-xl border border-slate-200 hover:border-slate-300 shadow-2xs space-y-3 transition-all"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1.5 min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 text-[11px] font-semibold border border-blue-200">
                            <Users className="w-3 h-3 text-blue-600" />
                            <span>Waiting on {item.waitingForPerson || 'external party'}</span>
                          </span>

                          {item.context && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-100 text-slate-600 border border-slate-200">
                              {item.context}
                            </span>
                          )}

                          {isStale ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full">
                              <AlertCircle className="w-3 h-3 text-rose-600" />
                              <span>{daysWaiting} days ago (Follow-up recommended)</span>
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-400" />
                              <span>{daysWaiting === 0 ? 'Today' : `${daysWaiting}d ago`}</span>
                            </span>
                          )}
                        </div>

                        <h3 className="text-sm font-semibold text-slate-900">
                          {item.title}
                        </h3>

                        {item.notes && (
                          <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100 whitespace-pre-wrap leading-relaxed">
                            {item.notes}
                          </p>
                        )}
                      </div>

                      {/* Action buttons on Waiting For card */}
                      <div className="flex flex-wrap items-center gap-1.5 shrink-0">
                        {/* 1. Log follow-up */}
                        <button
                          onClick={() => {
                            setFollowUpItemId(followUpItemId === item.id ? null : item.id);
                            setFollowUpNote('');
                          }}
                          className="px-2.5 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors cursor-pointer flex items-center gap-1"
                        >
                          <Send className="w-3 h-3" />
                          <span>Follow Up</span>
                        </button>

                        {/* 2. Received / Completed */}
                        <button
                          onClick={() => onResolveWaitingFor(item.id, 'complete')}
                          className="px-2.5 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg transition-colors cursor-pointer flex items-center gap-1"
                          title="Mark received & resolved"
                        >
                          <CheckCheck className="w-3 h-3 text-emerald-600" />
                          <span>Received</span>
                        </button>

                        {/* 3. Convert to Next Action */}
                        <button
                          onClick={() => onResolveWaitingFor(item.id, 'next_action')}
                          className="px-2.5 py-1.5 text-xs font-semibold text-teal-800 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg transition-colors cursor-pointer flex items-center gap-1"
                          title="They replied! Move this task to your active Next Actions"
                        >
                          <PlayCircle className="w-3 h-3 text-teal-600" />
                          <span>Now My Action</span>
                        </button>

                        {/* Trash */}
                        <button
                          onClick={() => onClarifyTrash(item.id)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors cursor-pointer"
                          title="Drop / Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Inline Follow-up logger */}
                    {followUpItemId === item.id && (
                      <div className="mt-2 pt-2 border-t border-slate-100 flex items-center gap-2">
                        <input
                          type="text"
                          placeholder="Log follow-up note (e.g. Sent Slack reminder, phoned office)..."
                          value={followUpNote}
                          onChange={(e) => setFollowUpNote(e.target.value)}
                          className="flex-1 text-xs px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:bg-white focus:border-blue-500"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              onLogWaitingForFollowUp(item.id, followUpNote);
                              setFollowUpItemId(null);
                            }
                          }}
                        />
                        <button
                          onClick={() => {
                            onLogWaitingForFollowUp(item.id, followUpNote);
                            setFollowUpItemId(null);
                          }}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg cursor-pointer"
                        >
                          Log Nudge
                        </button>
                        <button
                          onClick={() => setFollowUpItemId(null)}
                          className="text-xs text-slate-400 hover:text-slate-700 cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {/* ======================================================== */}
      {/* SECTION 3: CHECK 'SOMEDAY / MAYBE' LIST (INCUBATION)     */}
      {/* ======================================================== */}
      {(activeTab === 'all' || activeTab === 'someday_maybe') && (
        <section className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-2xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-xs">
                  3
                </span>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Check 'Someday/Maybe' List (Parked Ideas)
                </h2>
                <span className="text-xs font-mono font-bold bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full border border-purple-200">
                  {somedayMaybeItems.length}
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-normal pl-8">
                David Allen: "Scan ideas and aspirations on hold. Decide if anything is ready to activate this season, promote to a project, or delete."
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0 pl-8 sm:pl-0">
              <button
                onClick={() => setIsAddingSomeday(prev => !prev)}
                className="px-3.5 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Someday Idea</span>
              </button>
            </div>
          </div>

          {/* Quick Add Someday Form */}
          {isAddingSomeday && (
            <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-xl space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-purple-900">Park New Idea into 'Someday / Maybe'</h4>
                <button
                  onClick={() => setIsAddingSomeday(false)}
                  className="text-slate-400 hover:text-slate-700 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Future idea or aspirational project... (e.g. Learn pottery, Rebuild blog)"
                  value={newSmTitle}
                  onChange={(e) => setNewSmTitle(e.target.value)}
                  className="sm:col-span-2 px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-purple-500"
                />
                <select
                  value={newSmContext}
                  onChange={(e) => setNewSmContext(e.target.value)}
                  className="px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-purple-500"
                >
                  <option value="@home">@home</option>
                  <option value="@computer">@computer</option>
                  <option value="@office">@office</option>
                  <option value="@errands">@errands</option>
                  <option value="@phone">@phone</option>
                </select>
              </div>

              <input
                type="text"
                placeholder="Optional notes, links, inspiration or research leads..."
                value={newSmNotes}
                onChange={(e) => setNewSmNotes(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg outline-none focus:border-purple-500"
              />

              <div className="flex justify-end gap-2 pt-1">
                <button
                  onClick={() => setIsAddingSomeday(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  disabled={!newSmTitle.trim()}
                  onClick={() => {
                    onAddSomedayMaybeItem(newSmTitle, newSmNotes, newSmContext);
                    setNewSmTitle('');
                    setNewSmNotes('');
                    setIsAddingSomeday(false);
                  }}
                  className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                >
                  Park into Someday/Maybe
                </button>
              </div>
            </div>
          )}

          {/* Search bar inside Someday/Maybe */}
          {somedayMaybeItems.length > 2 && (
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Filter incubated ideas by keyword or context..."
                value={smSearch}
                onChange={(e) => setSmSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg outline-none focus:bg-white focus:border-purple-500"
              />
            </div>
          )}

          {/* List of Someday / Maybe Items */}
          {filteredSomeday.length === 0 ? (
            <div className="p-8 text-center bg-slate-50 border border-dashed border-slate-200 rounded-xl space-y-2">
              <Sparkles className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs font-semibold text-slate-700">No incubated items in Someday/Maybe</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                Park trips, hobbies, creative ideas, and book recommendations here without cluttering your active next actions.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredSomeday.map((item) => (
                <div
                  key={item.id}
                  className="p-4 bg-white rounded-xl border border-slate-200 hover:border-purple-200/80 hover:shadow-sm shadow-2xs space-y-3 transition-all flex flex-col justify-between"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 text-[10px] font-semibold border border-purple-200">
                        <Sparkles className="w-3.5 h-3.5 text-purple-500" />
                        <span>Parked Idea</span>
                      </span>

                      {item.context && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-100 text-slate-600 border border-slate-200">
                          {item.context}
                        </span>
                      )}
                    </div>

                    <h3 className="text-sm font-semibold text-slate-900 leading-snug">
                      {item.title}
                    </h3>

                    {item.notes && (
                      <p className="text-xs text-slate-600 line-clamp-3 bg-slate-50 p-2 rounded-lg border border-slate-100 leading-relaxed">
                        {item.notes}
                      </p>
                    )}
                  </div>

                  {/* Actions on Someday / Maybe Item */}
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      {/* Activate as Next Action */}
                      <button
                        onClick={() => onActivateSomedayMaybe(item.id, item.context)}
                        className="px-2.5 py-1 bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                        title="Activate now as a physical Next Action"
                      >
                        <PlayCircle className="w-3.5 h-3.5 text-teal-600" />
                        <span>Activate Now</span>
                      </button>

                      {/* Convert to Multi-Step Project */}
                      <button
                        onClick={() => {
                          const actionTitle = window.prompt(
                            `Define the first physical Next Action for project "${item.title}":`,
                            `Research options and create initial plan`
                          );
                          if (actionTitle) {
                            onClarifyConvertToProject(item.id, item.title, 'sequential', actionTitle);
                          }
                        }}
                        className="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-800 border border-blue-200 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                        title="Promote to an active multi-step Project"
                      >
                        <ArrowRight className="w-3.5 h-3.5 text-blue-600" />
                        <span>To Project</span>
                      </button>
                    </div>

                    <button
                      onClick={() => onClarifyTrash(item.id)}
                      className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors cursor-pointer"
                      title="Discard / Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ======================================================== */}
      {/* SECTION 4: TODAY'S HORIZON & DAILY FOCUS REFLECTION       */}
      {/* ======================================================== */}
      {(activeTab === 'all' || activeTab === 'daily_alignment') && (
        <section className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-2xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-xs">
                  4
                </span>
                <h2 className="text-lg font-bold text-slate-900 tracking-tight">
                  Today's Horizon & Focus Alignment
                </h2>
              </div>
              <p className="text-xs text-slate-500 leading-normal pl-8">
                Confirm your hard deadlines and set one core priority intention for today.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Hard Deadlines / Due Soon */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-rose-600" />
                <span>Hard Deadlines Due Within 24h ({dueSoonTasks.length})</span>
              </h3>

              {dueSoonTasks.length === 0 ? (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-500">
                  No impending hard deadlines in the next 24 hours. Your schedule has healthy breathing room today.
                </div>
              ) : (
                <div className="space-y-2">
                  {dueSoonTasks.map((task) => (
                    <div
                      key={task.id}
                      className="p-3 bg-rose-50/50 border border-rose-200 rounded-xl flex items-center justify-between gap-3"
                    >
                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-rose-600" />
                          <h4 className="text-xs font-bold text-slate-900 truncate">
                            {task.title}
                          </h4>
                        </div>
                        <p className="text-[10px] text-rose-700 font-medium pl-4">
                          Due:{' '}
                          {new Date(task.dueDate!).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>

                      <button
                        onClick={() => onToggleComplete(task.id)}
                        className="px-2.5 py-1 bg-white hover:bg-emerald-50 text-slate-700 hover:text-emerald-800 border border-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer shrink-0"
                      >
                        Mark Done
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Daily Intention & Reflection Notes */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-teal-600" />
                <span>Today's Core Focus & Reflection</span>
              </h3>

              <textarea
                rows={4}
                placeholder="What is the single most important outcome you want to accomplish today? Write your daily calibration note..."
                value={dailyNotes}
                onChange={(e) => handleSaveDailyNotes(e.target.value)}
                className="w-full text-xs p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-teal-500 leading-relaxed text-slate-800"
              />

              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Automatically saved to local storage</span>
                <button
                  onClick={handleFinishReview}
                  className="px-4 py-2 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white rounded-xl font-bold cursor-pointer transition-all shadow-sm"
                >
                  Finish Daily Review
                </button>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
