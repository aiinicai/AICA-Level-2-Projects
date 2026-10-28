import React, { useState, useEffect } from 'react';
import { Item, ProjectType } from '../types/gtd';
import { 
  X, 
  Trash2, 
  Archive, 
  BookOpen, 
  Zap, 
  UserCheck, 
  FolderPlus, 
  ArrowRight, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  Play,
  Pause,
  RotateCcw
} from 'lucide-react';

interface ClarifyModalProps {
  isOpen: boolean;
  onClose: () => void;
  inboxItems: Item[];
  projects: Item[];
  onTrash: (id: string) => void;
  onSomedayMaybe: (id: string, notes?: string) => void;
  onReference: (id: string, title?: string, notes?: string) => void;
  onDoNow: (id: string) => void;
  onWaitingFor: (id: string, person: string, notes?: string) => void;
  onConvertToProject: (id: string, title: string, type: ProjectType, firstAction: string, notes?: string) => void;
  onToNextAction: (
    id: string,
    title: string,
    projectId: string | null,
    notes?: string,
    deferDate?: string | null,
    dueDate?: string | null,
    estimatedMinutes?: number | null,
    energyLevel?: 'low' | 'medium' | 'high' | null,
    context?: string | null
  ) => void;
}

export const ClarifyModal: React.FC<ClarifyModalProps> = ({
  isOpen,
  onClose,
  inboxItems,
  projects,
  onTrash,
  onSomedayMaybe,
  onReference,
  onDoNow,
  onWaitingFor,
  onConvertToProject,
  onToNextAction,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [stage, setStage] = useState<'actionable_choice' | 'not_actionable' | 'actionable_branch' | 'two_minute_timer' | 'delegate' | 'create_project' | 'single_next_action'>('actionable_choice');

  // Form states for various branches
  const [delegatedPerson, setDelegatedPerson] = useState('');
  const [projectTitle, setProjectTitle] = useState('');
  const [projectType, setProjectType] = useState<ProjectType>('sequential');
  const [firstActionTitle, setFirstActionTitle] = useState('');
  const [actionTitle, setActionTitle] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [deferDate, setDeferDate] = useState<string>('');
  const [dueDate, setDueDate] = useState<string>('');
  const [estimatedMinutes, setEstimatedMinutes] = useState<number | ''>('');
  const [energyLevel, setEnergyLevel] = useState<'low' | 'medium' | 'high' | ''>('');
  const [actionContext, setActionContext] = useState<string>('@computer');
  const [itemNotes, setItemNotes] = useState('');

  // 2-Minute Rule Timer State
  const [timerSeconds, setTimerSeconds] = useState(120);
  const [timerRunning, setTimerRunning] = useState(false);

  const currentItem = inboxItems[currentIndex];

  useEffect(() => {
    if (currentItem) {
      setActionTitle(currentItem.title);
      setProjectTitle(currentItem.title);
      setItemNotes(currentItem.notes || '');
      setStage('actionable_choice');
      setTimerSeconds(120);
      setTimerRunning(false);
      setDelegatedPerson('');
      setSelectedProjectId('');
      setDeferDate('');
      setDueDate('');
      setFirstActionTitle('');
      setActionContext(currentItem.context || '@computer');
    }
  }, [currentIndex, currentItem]);

  // 2-minute countdown timer effect
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (timerRunning && timerSeconds > 0) {
      interval = setInterval(() => {
        setTimerSeconds(prev => prev - 1);
      }, 1000);
    } else if (timerSeconds === 0) {
      setTimerRunning(false);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [timerRunning, timerSeconds]);

  if (!isOpen) return null;

  // Inbox Zero achieved in this session
  if (!currentItem || inboxItems.length === 0) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
        <div className="w-full max-w-md bg-white rounded-xl shadow-xl border border-slate-200 p-8 text-center space-y-4">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-800 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Inbox Zero Reached!</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            All thoughts in your inbox have been clarified into actions, projects, or reference material. Your mind is clear.
          </p>
          <button
            onClick={onClose}
            className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Verb-first detector for GTD physical action quality
  const isVerbFirst = (text: string) => {
    const commonVerbs = ['call', 'phone', 'email', 'send', 'draft', 'write', 'buy', 'purchase', 'review', 'read', 'clean', 'schedule', 'book', 'ask', 'talk', 'order', 'inspect', 'pay', 'file', 'measure', 'find', 'research', 'organize', 'listen', 'print'];
    const firstWord = text.trim().split(/\s+/)[0]?.toLowerCase();
    return commonVerbs.includes(firstWord);
  };

  const handleNextItem = () => {
    if (currentIndex >= inboxItems.length - 1) {
      setCurrentIndex(0);
    }
  };

  // 1. Non-Actionable Handlers
  const handleTrash = () => {
    onTrash(currentItem.id);
    handleNextItem();
  };

  const handleSomedayMaybe = () => {
    onSomedayMaybe(currentItem.id, itemNotes);
    handleNextItem();
  };

  const handleReference = () => {
    onReference(currentItem.id, currentItem.title, itemNotes);
    handleNextItem();
  };

  // 2. Actionable Handlers
  const handleDoNowCompleted = () => {
    onDoNow(currentItem.id);
    handleNextItem();
  };

  const handleSaveWaitingFor = () => {
    if (!delegatedPerson.trim()) return;
    onWaitingFor(currentItem.id, delegatedPerson, itemNotes);
    handleNextItem();
  };

  const handleSaveProject = () => {
    if (!projectTitle.trim()) return;
    onConvertToProject(currentItem.id, projectTitle, projectType, firstActionTitle || 'Define initial next step', itemNotes);
    handleNextItem();
  };

  const handleSaveNextAction = () => {
    if (!actionTitle.trim()) return;
    onToNextAction(
      currentItem.id,
      actionTitle,
      selectedProjectId || null,
      itemNotes,
      deferDate || null,
      dueDate || null,
      estimatedMinutes ? Number(estimatedMinutes) : null,
      energyLevel || null,
      actionContext || null
    );
    handleNextItem();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/70 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              Clarify Inbox
            </span>
            <span className="text-xs text-slate-500 font-mono">
              Item {currentIndex + 1} of {inboxItems.length}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1 rounded-md hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current Inbox Item Display */}
        <div className="p-6 bg-slate-50/40 border-b border-slate-100 shrink-0">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
            Unprocessed Inbox Item
          </div>
          <h2 className="text-lg font-bold text-slate-900 leading-snug">
            {currentItem.title}
          </h2>
          {currentItem.notes && (
            <p className="text-xs text-slate-600 mt-2 bg-white p-2.5 rounded-lg border border-slate-200/80">
              {currentItem.notes}
            </p>
          )}
        </div>

        {/* Dynamic Clarify Stage Area */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* Step 1: Is it Actionable? */}
          {stage === 'actionable_choice' && (
            <div className="space-y-4">
              <div className="text-sm font-semibold text-slate-900">
                David Allen's Decision Step 1: Is this item actionable?
              </div>
              <p className="text-xs text-slate-500">
                Can anything physical and visible be done right now or in the future regarding this item?
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <button
                  onClick={() => setStage('actionable_branch')}
                  className="p-5 border border-teal-600 bg-gradient-to-br from-teal-600 to-teal-700 text-white rounded-xl hover:from-teal-700 hover:to-teal-800 transition-all text-left space-y-1.5 cursor-pointer shadow-sm shadow-teal-600/30 active:scale-98"
                >
                  <div className="font-bold text-sm flex items-center justify-between">
                    <span>YES, Actionable</span>
                    <ArrowRight className="w-4 h-4" />
                  </div>
                  <p className="text-xs text-teal-100">
                    Next action, 2-minute task, delegation, or multi-step project.
                  </p>
                </button>

                <button
                  onClick={() => setStage('not_actionable')}
                  className="p-5 border border-rose-200 bg-gradient-to-br from-rose-50/70 to-white hover:bg-rose-100/60 rounded-xl transition-all text-left space-y-1.5 cursor-pointer shadow-2xs"
                >
                  <div className="font-bold text-sm text-rose-950 flex items-center justify-between">
                    <span>NO, Not Actionable</span>
                    <ArrowRight className="w-4 h-4 text-rose-500" />
                  </div>
                  <p className="text-xs text-rose-700/90">
                    Trash it, file for Someday/Maybe, or keep as Reference.
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* Step 1b: Not Actionable Choices */}
          {stage === 'not_actionable' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-slate-900">
                  Non-Actionable Buckets
                </h4>
                <button
                  onClick={() => setStage('actionable_choice')}
                  className="text-xs text-blue-600 hover:text-blue-800 underline cursor-pointer"
                >
                  Back
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  onClick={handleTrash}
                  className="p-4 border border-rose-300 bg-rose-50/80 hover:bg-rose-100 rounded-xl text-left space-y-2 transition-colors cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center gap-2 text-rose-900 font-bold text-xs uppercase">
                    <Trash2 className="w-4 h-4 text-rose-600" />
                    Trash
                  </div>
                  <p className="text-xs text-rose-800">
                    No value or obligation. Eliminate immediately.
                  </p>
                </button>

                <button
                  onClick={handleSomedayMaybe}
                  className="p-4 border border-blue-200 bg-blue-50/70 hover:bg-blue-100/70 rounded-xl text-left space-y-2 transition-colors cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center gap-2 text-blue-900 font-bold text-xs uppercase">
                    <Archive className="w-4 h-4 text-blue-600" />
                    Someday/Maybe
                  </div>
                  <p className="text-xs text-blue-800">
                    Hold for weekly reflection. Not actionable now.
                  </p>
                </button>

                <button
                  onClick={handleReference}
                  className="p-4 border border-teal-200 bg-teal-50/70 hover:bg-teal-100/70 rounded-xl text-left space-y-2 transition-colors cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center gap-2 text-teal-900 font-bold text-xs uppercase">
                    <BookOpen className="w-4 h-4 text-teal-600" />
                    Reference
                  </div>
                  <p className="text-xs text-teal-800">
                    Useful data or ideas with no next action required.
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Actionable Routes */}
          {stage === 'actionable_branch' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-slate-900">
                  Actionable Clarification: What is the next step?
                </h4>
                <button
                  onClick={() => setStage('actionable_choice')}
                  className="text-xs text-blue-600 hover:text-blue-800 underline cursor-pointer"
                >
                  Back
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* 2-Minute Rule (Teal) */}
                <button
                  onClick={() => setStage('two_minute_timer')}
                  className="p-4 border border-teal-300 bg-teal-50/80 hover:bg-teal-100/80 rounded-xl text-left space-y-1.5 transition-colors cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center gap-2 text-teal-950 font-bold text-xs uppercase">
                    <Zap className="w-4 h-4 text-teal-600" />
                    Takes &lt; 2 Minutes? (Do It Now)
                  </div>
                  <p className="text-xs text-teal-800">
                    If it takes under 2 minutes, the overhead to track it exceeds execution. Do it right now!
                  </p>
                </button>

                {/* Delegate / Waiting For (Blue) */}
                <button
                  onClick={() => setStage('delegate')}
                  className="p-4 border border-blue-300 bg-blue-50/80 hover:bg-blue-100/80 rounded-xl text-left space-y-1.5 transition-colors cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center gap-2 text-blue-950 font-bold text-xs uppercase">
                    <UserCheck className="w-4 h-4 text-blue-600" />
                    Someone else's job? (Delegate)
                  </div>
                  <p className="text-xs text-blue-800">
                    Track in "Waiting For" with the person's name and hand-off date.
                  </p>
                </button>

                {/* Multi-Step Outcome -> Project (Deep Blue / Indigo) */}
                <button
                  onClick={() => setStage('create_project')}
                  className="p-4 border border-indigo-200 bg-indigo-50/70 hover:bg-indigo-100/70 rounded-xl text-left space-y-1.5 transition-colors cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center gap-2 text-indigo-950 font-bold text-xs uppercase">
                    <FolderPlus className="w-4 h-4 text-indigo-600" />
                    Multi-Step Outcome? (Project)
                  </div>
                  <p className="text-xs text-indigo-800">
                    Needs more than one action step to complete. Create project and define first action.
                  </p>
                </button>

                {/* Single Next Action (Teal / Clean) */}
                <button
                  onClick={() => setStage('single_next_action')}
                  className="p-4 border border-teal-200 bg-white hover:bg-teal-50/40 rounded-xl text-left space-y-1.5 transition-colors cursor-pointer shadow-2xs"
                >
                  <div className="flex items-center gap-2 text-teal-900 font-bold text-xs uppercase">
                    <CheckCircle2 className="w-4 h-4 text-teal-600" />
                    Single Next Action
                  </div>
                  <p className="text-xs text-slate-600">
                    Concrete physical action. Assign to an existing project or standalone next actions list.
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* 2-Minute Rule Interactive Stepper */}
          {stage === 'two_minute_timer' && (
            <div className="space-y-5 p-5 bg-emerald-50/50 border border-emerald-200 rounded-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-900 uppercase tracking-wide flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-emerald-700" />
                  The 2-Minute Rule in Action
                </span>
                <button
                  onClick={() => setStage('actionable_branch')}
                  className="text-xs text-slate-500 hover:text-slate-900 underline cursor-pointer"
                >
                  Back
                </button>
              </div>

              <div className="text-center py-4 space-y-3">
                <div className="text-4xl font-mono font-bold text-slate-900 tabular-nums">
                  {Math.floor(timerSeconds / 60)}:{(timerSeconds % 60).toString().padStart(2, '0')}
                </div>
                <p className="text-xs text-slate-600 max-w-sm mx-auto">
                  Execute the task immediately: send the email, make the phone call, or file the form.
                </p>

                <div className="flex items-center justify-center gap-2 pt-2">
                  <button
                    onClick={() => setTimerRunning(!timerRunning)}
                    className="px-3 py-1.5 bg-white border border-slate-200 hover:bg-slate-100 rounded-lg text-xs font-semibold text-slate-800 flex items-center gap-1.5 cursor-pointer"
                  >
                    {timerRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    <span>{timerRunning ? 'Pause Timer' : 'Start Timer'}</span>
                  </button>
                  <button
                    onClick={() => { setTimerSeconds(120); setTimerRunning(false); }}
                    className="p-1.5 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-lg cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="pt-2 border-t border-emerald-200 flex justify-end">
                <button
                  onClick={handleDoNowCompleted}
                  className="px-4 py-2 bg-emerald-800 hover:bg-emerald-900 text-white rounded-lg text-xs font-semibold flex items-center gap-2 cursor-pointer shadow-xs"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Done! Mark Completed</span>
                </button>
              </div>
            </div>
          )}

          {/* Delegate / Waiting For Form */}
          {stage === 'delegate' && (
            <div className="space-y-4 p-5 bg-blue-50/40 border border-blue-200 rounded-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-900 uppercase tracking-wide flex items-center gap-1.5">
                  <UserCheck className="w-4 h-4 text-blue-700" />
                  Track in "Waiting For"
                </span>
                <button
                  onClick={() => setStage('actionable_branch')}
                  className="text-xs text-slate-500 hover:text-slate-900 underline cursor-pointer"
                >
                  Back
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Who are you delegating this to? *
                  </label>
                  <input
                    type="text"
                    value={delegatedPerson}
                    onChange={(e) => setDelegatedPerson(e.target.value)}
                    placeholder="e.g. Sarah Jenkins, Legal Team, Vendor Support"
                    className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-blue-600"
                    autoFocus
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Follow-up Notes / Deliverable Expected
                  </label>
                  <textarea
                    value={itemNotes}
                    onChange={(e) => setItemNotes(e.target.value)}
                    rows={2}
                    placeholder="Details about what was requested..."
                    className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-blue-600"
                  />
                </div>
              </div>

              <div className="pt-2 border-t border-blue-200 flex justify-end">
                <button
                  onClick={handleSaveWaitingFor}
                  disabled={!delegatedPerson.trim()}
                  className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-lg text-xs font-semibold disabled:opacity-40 flex items-center gap-2 cursor-pointer"
                >
                  <span>File to "Waiting For"</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Multi-Step Outcome -> Project Creator */}
          {stage === 'create_project' && (
            <div className="space-y-4 p-5 bg-purple-50/40 border border-purple-200 rounded-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-purple-900 uppercase tracking-wide flex items-center gap-1.5">
                  <FolderPlus className="w-4 h-4 text-purple-700" />
                  Define Multi-Step Project Outcome
                </span>
                <button
                  onClick={() => setStage('actionable_branch')}
                  className="text-xs text-slate-500 hover:text-slate-900 underline cursor-pointer"
                >
                  Back
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Desired Outcome / Project Name *
                  </label>
                  <input
                    type="text"
                    value={projectTitle}
                    onChange={(e) => setProjectTitle(e.target.value)}
                    placeholder="e.g. Kitchen remodel finalized and approved"
                    className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-purple-600"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Project Type (OmniFocus Availability Rule)
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setProjectType('sequential')}
                      className={`p-2 text-xs font-medium rounded-lg border text-center cursor-pointer transition-colors ${
                        projectType === 'sequential'
                          ? 'border-purple-600 bg-purple-100 text-purple-950 font-semibold'
                          : 'border-slate-200 bg-white text-slate-700'
                      }`}
                    >
                      Sequential
                    </button>
                    <button
                      type="button"
                      onClick={() => setProjectType('parallel')}
                      className={`p-2 text-xs font-medium rounded-lg border text-center cursor-pointer transition-colors ${
                        projectType === 'parallel'
                          ? 'border-purple-600 bg-purple-100 text-purple-950 font-semibold'
                          : 'border-slate-200 bg-white text-slate-700'
                      }`}
                    >
                      Parallel
                    </button>
                    <button
                      type="button"
                      onClick={() => setProjectType('single_action')}
                      className={`p-2 text-xs font-medium rounded-lg border text-center cursor-pointer transition-colors ${
                        projectType === 'single_action'
                          ? 'border-purple-600 bg-purple-100 text-purple-950 font-semibold'
                          : 'border-slate-200 bg-white text-slate-700'
                      }`}
                    >
                      Single-Action List
                    </button>
                  </div>
                </div>

                {/* First Next Physical Action (GTD Mandatory rule: No stalled projects!) */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-700">
                      What is the first physical, visible next action? *
                    </label>
                    {!isVerbFirst(firstActionTitle) && firstActionTitle.length > 2 && (
                      <span className="text-[11px] text-amber-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" /> Nudge: Start with a verb (Call, Draft, Buy...)
                      </span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={firstActionTitle}
                    onChange={(e) => setFirstActionTitle(e.target.value)}
                    placeholder="e.g. Call architect to schedule site measurement"
                    className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-purple-600"
                  />
                </div>
              </div>

              <div className="pt-2 border-t border-purple-200 flex justify-end">
                <button
                  onClick={handleSaveProject}
                  disabled={!projectTitle.trim() || !firstActionTitle.trim()}
                  className="px-4 py-2 bg-purple-800 hover:bg-purple-900 text-white rounded-lg text-xs font-semibold disabled:opacity-40 flex items-center gap-2 cursor-pointer shadow-xs"
                >
                  <span>Create Project & First Action</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Single Action Form */}
          {stage === 'single_next_action' && (
            <div className="space-y-4 p-5 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wide flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-slate-700" />
                  Define Next Physical Action
                </span>
                <button
                  onClick={() => setStage('actionable_branch')}
                  className="text-xs text-slate-500 hover:text-slate-900 underline cursor-pointer"
                >
                  Back
                </button>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-700">
                      Physical Next Action *
                    </label>
                    {!isVerbFirst(actionTitle) && (
                      <span className="text-[11px] text-amber-600 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" /> Nudge: Begin with physical verb
                      </span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={actionTitle}
                    onChange={(e) => setActionTitle(e.target.value)}
                    placeholder="e.g. Draft feedback for team design review"
                    className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-slate-900"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Context (e.g. @home, @office)
                    </label>
                    <select
                      value={actionContext}
                      onChange={(e) => setActionContext(e.target.value)}
                      className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-slate-900 font-mono"
                    >
                      <option value="@home">@home</option>
                      <option value="@office">@office</option>
                      <option value="@phone">@phone</option>
                      <option value="@computer">@computer</option>
                      <option value="@errands">@errands</option>
                      <option value="@anywhere">@anywhere</option>
                      <option value="">No Context</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Assign to Project (Optional)
                    </label>
                    <select
                      value={selectedProjectId}
                      onChange={(e) => setSelectedProjectId(e.target.value)}
                      className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-slate-900"
                    >
                      <option value="">No Project (Standalone Action)</option>
                      {projects.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.title} ({p.projectType})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Defer Date ("Available From")
                    </label>
                    <input
                      type="date"
                      value={deferDate}
                      onChange={(e) => setDeferDate(e.target.value)}
                      className="w-full text-xs p-2 bg-white border border-slate-300 rounded-lg outline-none focus:border-slate-900"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Estimated Time (Minutes)
                    </label>
                    <input
                      type="number"
                      value={estimatedMinutes}
                      onChange={(e) => setEstimatedMinutes(e.target.value === '' ? '' : Number(e.target.value))}
                      placeholder="e.g. 15, 30, 60"
                      className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-slate-900"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Energy Available Requirement
                    </label>
                    <select
                      value={energyLevel}
                      onChange={(e) => setEnergyLevel(e.target.value as any)}
                      className="w-full text-xs p-2.5 bg-white border border-slate-300 rounded-lg outline-none focus:border-slate-900"
                    >
                      <option value="">Any Energy</option>
                      <option value="low">Low Energy (Routine / Administrative)</option>
                      <option value="medium">Medium Energy</option>
                      <option value="high">High Energy (Creative / Deep Focus)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-200 flex justify-end">
                <button
                  onClick={handleSaveNextAction}
                  disabled={!actionTitle.trim()}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold disabled:opacity-40 flex items-center gap-2 cursor-pointer shadow-xs"
                >
                  <span>Save to Next Actions</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
