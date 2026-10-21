import React, { useState, useMemo } from 'react';
import { Item } from '../types/gtd';
import { 
  PlayCircle, 
  Circle, 
  Flag, 
  Clock, 
  Zap, 
  Calendar, 
  AlertTriangle, 
  CalendarClock,
  XCircle,
  Tag,
  Home,
  Building2,
  Phone,
  Laptop,
  ShoppingBag,
  Layers,
  List,
  Check,
  ChevronDown,
  X,
  Plus
} from 'lucide-react';

interface NextActionsViewProps {
  nextActions: Item[];
  projects: Item[];
  searchQuery?: string;
  onClearSearch?: () => void;
  onToggleComplete: (id: string) => void;
  onToggleFlag: (id: string) => void;
  onUpdateDueDate?: (id: string, dueDate: string | null) => void;
  onUpdateContext?: (id: string, context: string | null) => void;
}

const PRESET_CONTEXTS = ['@home', '@office', '@phone', '@computer', '@errands'];

export const NextActionsView: React.FC<NextActionsViewProps> = ({
  nextActions,
  projects,
  searchQuery = '',
  onClearSearch,
  onToggleComplete,
  onToggleFlag,
  onUpdateDueDate,
  onUpdateContext,
}) => {
  const [filterContext, setFilterContext] = useState<string>('all');
  const [groupBy, setGroupBy] = useState<'none' | 'context' | 'project'>('context');
  const [filterEnergy, setFilterEnergy] = useState<string>('all');
  const [filterTime, setFilterTime] = useState<string>('all');
  const [filterDeadline, setFilterDeadline] = useState<'all' | 'due_soon' | 'upcoming'>('all');
  const [editingDueDateId, setEditingDueDateId] = useState<string | null>(null);
  const [editingContextId, setEditingContextId] = useState<string | null>(null);
  const [customContextInput, setCustomContextInput] = useState('');

  // Helper to calculate deadline status for any task
  const getDeadlineMeta = (dueDateStr: string | null | undefined) => {
    if (!dueDateStr) return null;
    const due = new Date(dueDateStr);
    if (isNaN(due.getTime())) return null;

    const now = new Date();
    const diffMs = due.getTime() - now.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);

    const isOverdue = diffMs < 0;
    const isDueWithin24h = !isOverdue && diffHours <= 24;
    const isUpcoming = !isOverdue && !isDueWithin24h;

    return {
      due,
      diffHours,
      isOverdue,
      isDueWithin24h,
      isUpcoming,
    };
  };

  const getProjectName = (projectId: string | null) => {
    if (!projectId) return 'Standalone Next Action';
    const proj = projects.find(p => p.id === projectId);
    return proj ? proj.title : 'Project';
  };

  // Helper to style contexts gracefully
  const getContextMeta = (context?: string | null) => {
    if (!context) {
      return {
        label: 'No context',
        colorClass: 'bg-slate-100 text-slate-600 border-slate-200',
        activeFilterClass: 'bg-slate-800 text-white border-slate-800',
        cardHeaderClass: 'bg-slate-50 border-slate-200 text-slate-700',
        icon: Tag,
      };
    }

    const c = context.toLowerCase();
    if (c.includes('home')) {
      return {
        label: context,
        colorClass: 'bg-teal-50 text-teal-800 border-teal-200/90',
        activeFilterClass: 'bg-teal-700 text-white border-teal-700',
        cardHeaderClass: 'bg-teal-50/70 border-teal-200 text-teal-900',
        icon: Home,
      };
    }
    if (c.includes('office') || c.includes('work')) {
      return {
        label: context,
        colorClass: 'bg-blue-50 text-blue-800 border-blue-200/90',
        activeFilterClass: 'bg-blue-700 text-white border-blue-700',
        cardHeaderClass: 'bg-blue-50/70 border-blue-200 text-blue-900',
        icon: Building2,
      };
    }
    if (c.includes('phone') || c.includes('call')) {
      return {
        label: context,
        colorClass: 'bg-rose-50 text-rose-800 border-rose-200/90',
        activeFilterClass: 'bg-rose-700 text-white border-rose-700',
        cardHeaderClass: 'bg-rose-50/70 border-rose-200 text-rose-900',
        icon: Phone,
      };
    }
    if (c.includes('computer') || c.includes('online') || c.includes('desk')) {
      return {
        label: context,
        colorClass: 'bg-cyan-50 text-cyan-800 border-cyan-200/90',
        activeFilterClass: 'bg-cyan-700 text-white border-cyan-700',
        cardHeaderClass: 'bg-cyan-50/70 border-cyan-200 text-cyan-900',
        icon: Laptop,
      };
    }
    if (c.includes('errand')) {
      return {
        label: context,
        colorClass: 'bg-purple-50 text-purple-800 border-purple-200/90',
        activeFilterClass: 'bg-purple-700 text-white border-purple-700',
        cardHeaderClass: 'bg-purple-50/70 border-purple-200 text-purple-900',
        icon: ShoppingBag,
      };
    }

    return {
      label: context,
      colorClass: 'bg-teal-50 text-teal-800 border-teal-200/90',
      activeFilterClass: 'bg-teal-700 text-white border-teal-700',
      cardHeaderClass: 'bg-teal-50/70 border-teal-200 text-teal-900',
      icon: Tag,
    };
  };

  // Collect all unique contexts from available next actions
  const uniqueContexts = useMemo(() => {
    const set = new Set<string>(PRESET_CONTEXTS);
    nextActions.forEach(action => {
      if (action.context) set.add(action.context);
    });
    return Array.from(set);
  }, [nextActions]);

  // Context counts
  const contextCounts = useMemo(() => {
    const counts: Record<string, number> = { all: nextActions.length, none: 0 };
    uniqueContexts.forEach(c => { counts[c] = 0; });
    nextActions.forEach(action => {
      if (action.context) {
        counts[action.context] = (counts[action.context] || 0) + 1;
      } else {
        counts.none = (counts.none || 0) + 1;
      }
    });
    return counts;
  }, [nextActions, uniqueContexts]);

  // Pre-calculate deadline counts for the summary banner
  const deadlineStats = useMemo(() => {
    let dueWithin24hCount = 0;
    let upcomingCount = 0;
    let overdueCount = 0;

    nextActions.forEach(action => {
      const meta = getDeadlineMeta(action.dueDate);
      if (meta) {
        if (meta.isOverdue) overdueCount++;
        else if (meta.isDueWithin24h) dueWithin24hCount++;
        else upcomingCount++;
      }
    });

    return { dueWithin24hCount, upcomingCount, overdueCount };
  }, [nextActions]);

  // Filter based on Search Query, Context, Energy, Time, and Deadline criteria
  const filteredActions = useMemo(() => {
    return nextActions.filter(action => {
      // Keyword search across title, notes, parent project title, and context
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const projName = getProjectName(action.projectId).toLowerCase();
        const ctx = (action.context || '').toLowerCase();
        const titleMatch = action.title.toLowerCase().includes(q);
        const notesMatch = action.notes ? action.notes.toLowerCase().includes(q) : false;
        const projMatch = projName.includes(q);
        const ctxMatch = ctx.includes(q);
        if (!titleMatch && !notesMatch && !projMatch && !ctxMatch) {
          return false;
        }
      }

      // Context filter
      if (filterContext !== 'all') {
        if (filterContext === 'none') {
          if (action.context) return false;
        } else {
          if (action.context !== filterContext) return false;
        }
      }

      // Energy filter
      if (filterEnergy !== 'all' && action.energyLevel !== filterEnergy) {
        return false;
      }
      // Time filter
      if (filterTime === '15' && (!action.estimatedMinutes || action.estimatedMinutes > 15)) {
        return false;
      }
      if (filterTime === '30' && (!action.estimatedMinutes || action.estimatedMinutes > 30)) {
        return false;
      }
      // Deadline filter
      const meta = getDeadlineMeta(action.dueDate);
      if (filterDeadline === 'due_soon') {
        if (!meta || (!meta.isDueWithin24h && !meta.isOverdue)) return false;
      } else if (filterDeadline === 'upcoming') {
        if (!meta || !meta.isUpcoming) return false;
      }

      return true;
    });
  }, [nextActions, projects, searchQuery, filterContext, filterEnergy, filterTime, filterDeadline]);

  // Grouped by Context
  const groupedByContext = useMemo(() => {
    const map = new Map<string, Item[]>();
    const noContextItems: Item[] = [];

    filteredActions.forEach(action => {
      if (action.context) {
        if (!map.has(action.context)) {
          map.set(action.context, []);
        }
        map.get(action.context)!.push(action);
      } else {
        noContextItems.push(action);
      }
    });

    const groups: { key: string; label: string; context: string | null; actions: Item[] }[] = [];
    map.forEach((actions, ctx) => {
      groups.push({ key: ctx, label: ctx, context: ctx, actions });
    });

    if (noContextItems.length > 0) {
      groups.push({ key: 'none', label: 'No Context Assigned', context: null, actions: noContextItems });
    }

    return groups;
  }, [filteredActions]);

  // Grouped by Project
  const groupedByProject = useMemo(() => {
    const map = new Map<string, Item[]>();
    const standalone: Item[] = [];

    filteredActions.forEach(action => {
      if (action.projectId) {
        if (!map.has(action.projectId)) {
          map.set(action.projectId, []);
        }
        map.get(action.projectId)!.push(action);
      } else {
        standalone.push(action);
      }
    });

    const groups: { key: string; label: string; actions: Item[] }[] = [];
    map.forEach((actions, pId) => {
      groups.push({
        key: pId,
        label: getProjectName(pId),
        actions,
      });
    });

    if (standalone.length > 0) {
      groups.push({
        key: 'standalone',
        label: 'Standalone Next Actions (No Project)',
        actions: standalone,
      });
    }

    return groups;
  }, [filteredActions, projects]);

  const handleDateChange = (id: string, dateString: string) => {
    if (onUpdateDueDate) {
      if (!dateString) {
        onUpdateDueDate(id, null);
      } else {
        const selected = new Date(dateString);
        selected.setHours(23, 59, 59, 999);
        onUpdateDueDate(id, selected.toISOString());
      }
    }
    setEditingDueDateId(null);
  };

  const handleContextChange = (id: string, newContext: string | null) => {
    if (onUpdateContext) {
      onUpdateContext(id, newContext);
    }
    setEditingContextId(null);
    setCustomContextInput('');
  };

  const handleAddCustomContext = (id: string) => {
    if (!customContextInput.trim()) return;
    let formatted = customContextInput.trim();
    if (!formatted.startsWith('@')) {
      formatted = `@${formatted}`;
    }
    handleContextChange(id, formatted);
  };

  // Reusable Task Row Renderer
  const renderActionRow = (action: Item) => {
    const deadlineMeta = getDeadlineMeta(action.dueDate);
    const isEditingDate = editingDueDateId === action.id;
    const isEditingContext = editingContextId === action.id;
    const contextMeta = getContextMeta(action.context);
    const ContextIcon = contextMeta.icon;

    return (
      <div
        key={action.id}
        className="p-4 hover:bg-teal-50/20 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 group relative"
      >
        <div className="flex items-start sm:items-center gap-3.5 flex-1 min-w-0">
          <button
            onClick={() => onToggleComplete(action.id)}
            title="Mark Completed"
            className="text-slate-400 hover:text-teal-600 cursor-pointer shrink-0 transition-colors pt-0.5 sm:pt-0"
          >
            <Circle className="w-4 h-4" />
          </button>

          <div className="space-y-1.5 min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-slate-900 truncate">
                {action.title}
              </span>

              {/* Context Tag Badge with Click-to-Edit */}
              <div className="relative inline-block">
                <button
                  onClick={() => {
                    setEditingContextId(isEditingContext ? null : action.id);
                    setCustomContextInput('');
                  }}
                  title="Click to assign or change context"
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-medium border transition-all cursor-pointer ${
                    action.context
                      ? contextMeta.colorClass
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-500 border-dashed border-slate-300'
                  }`}
                >
                  <ContextIcon className="w-3 h-3 shrink-0" />
                  <span>{action.context || '+ Context'}</span>
                  <ChevronDown className="w-2.5 h-2.5 opacity-60" />
                </button>

                {/* Context Selector Popover */}
                {isEditingContext && (
                  <div className="absolute left-0 top-7 z-30 w-56 bg-white rounded-xl shadow-xl border border-slate-200 p-2.5 space-y-2 animate-in fade-in zoom-in-95 duration-100">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 px-1">
                      <span className="text-[11px] font-bold text-slate-700">Assign Context</span>
                      <button
                        onClick={() => setEditingContextId(null)}
                        className="text-slate-400 hover:text-slate-600 p-0.5"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-1">
                      {PRESET_CONTEXTS.map(c => {
                        const meta = getContextMeta(c);
                        const Icon = meta.icon;
                        const isCurrent = action.context === c;
                        return (
                          <button
                            key={c}
                            onClick={() => handleContextChange(action.id, c)}
                            className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs text-left transition-colors cursor-pointer ${
                              isCurrent
                                ? 'bg-teal-100 text-teal-800 font-bold border border-teal-300'
                                : 'hover:bg-slate-100 text-slate-700'
                            }`}
                          >
                            <Icon className="w-3 h-3 text-slate-500 shrink-0" />
                            <span className="truncate">{c}</span>
                            {isCurrent && <Check className="w-3 h-3 ml-auto text-teal-700" />}
                          </button>
                        );
                      })}
                    </div>

                    {/* Custom Context input */}
                    <div className="pt-1 border-t border-slate-100 flex items-center gap-1">
                      <input
                        type="text"
                        value={customContextInput}
                        onChange={(e) => setCustomContextInput(e.target.value)}
                        placeholder="@custom..."
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAddCustomContext(action.id);
                          }
                        }}
                        className="w-full text-xs px-2 py-1 bg-slate-50 border border-slate-200 rounded outline-none font-mono focus:border-teal-500"
                      />
                      <button
                        onClick={() => handleAddCustomContext(action.id)}
                        disabled={!customContextInput.trim()}
                        className="px-2 py-1 bg-teal-600 text-white rounded text-xs font-semibold disabled:opacity-40 hover:bg-teal-700 cursor-pointer"
                      >
                        Add
                      </button>
                    </div>

                    {action.context && (
                      <button
                        onClick={() => handleContextChange(action.id, null)}
                        className="w-full text-center text-[10px] text-rose-600 hover:text-rose-700 hover:bg-rose-50 py-1 rounded font-medium cursor-pointer transition-colors"
                      >
                        Remove context
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Visual indicator for tasks due within 24 hours */}
              {deadlineMeta?.isDueWithin24h && (
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold font-mono text-rose-700 bg-rose-50 border border-rose-300 shadow-2xs">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-600"></span>
                  </span>
                  <span>
                    Due in {deadlineMeta.diffHours < 1 ? '<1h' : `${Math.round(deadlineMeta.diffHours)}h`}
                  </span>
                </span>
              )}

              {/* Overdue alert indicator */}
              {deadlineMeta?.isOverdue && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold font-mono text-rose-800 bg-rose-100 border border-rose-300 shadow-2xs">
                  <AlertTriangle className="w-3 h-3 text-rose-600" />
                  <span>Overdue</span>
                </span>
              )}

              {/* Upcoming deadline indicator (> 24 hours) */}
              {deadlineMeta?.isUpcoming && (
                <span className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-600 bg-slate-50 border border-slate-200/90 px-2 py-0.5 rounded">
                  <Calendar className="w-3 h-3 text-blue-600" />
                  <span>
                    Due {deadlineMeta.due.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
                  </span>
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="font-medium text-blue-700">
                {getProjectName(action.projectId)}
              </span>
              {action.estimatedMinutes && (
                <>
                  <span aria-hidden="true" className="text-slate-300">·</span>
                  <span className="font-mono tabular-nums flex items-center gap-1 text-teal-700">
                    <Clock className="w-3 h-3 text-teal-600" />
                    {action.estimatedMinutes}m
                  </span>
                </>
              )}
              {action.energyLevel && (
                <>
                  <span aria-hidden="true" className="text-slate-300">·</span>
                  <span className="capitalize flex items-center gap-1 text-slate-600">
                    <Zap className="w-3 h-3 text-amber-500" />
                    {action.energyLevel} energy
                  </span>
                </>
              )}
              {action.notes && (
                <>
                  <span aria-hidden="true" className="text-slate-300">·</span>
                  <span className="text-slate-400 italic truncate max-w-xs">{action.notes}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right controls: Due Date Editor & Flag */}
        <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
          {/* Inline Due Date Picker / Modifier */}
          {isEditingDate ? (
            <div className="flex items-center gap-1 bg-white border border-slate-300 p-1 rounded-lg shadow-sm">
              <input
                type="date"
                defaultValue={action.dueDate ? action.dueDate.split('T')[0] : ''}
                onChange={(e) => handleDateChange(action.id, e.target.value)}
                className="text-xs p-1 outline-none font-mono"
                autoFocus
              />
              <button
                onClick={() => handleDateChange(action.id, '')}
                title="Clear deadline"
                className="p-1 text-slate-400 hover:text-rose-600 cursor-pointer"
              >
                <XCircle className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditingDueDateId(action.id)}
              title={action.dueDate ? 'Change due date' : 'Add hard landscape deadline'}
              className="px-2 py-1 text-[11px] text-slate-500 hover:text-blue-700 hover:bg-blue-50/70 border border-slate-200 rounded-md transition-colors cursor-pointer flex items-center gap-1 font-mono"
            >
              <CalendarClock className="w-3.5 h-3.5 text-blue-600" />
              <span className="hidden sm:inline">
                {action.dueDate ? 'Edit Due' : '+ Due Date'}
              </span>
            </button>
          )}

          <button
            onClick={() => onToggleFlag(action.id)}
            title="Toggle Flag"
            className={`p-1.5 rounded-md cursor-pointer transition-colors ${
              action.flagged ? 'text-rose-600 fill-rose-500' : 'text-slate-300 hover:text-rose-500'
            }`}
          >
            <Flag className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <PlayCircle className="w-5 h-5 text-teal-600 fill-teal-50" />
              Next Actions
            </h2>
            <span className="text-xs font-mono font-semibold px-2.5 py-0.5 bg-teal-50 text-teal-800 border border-teal-200/80 rounded-full">
              {filteredActions.length} Available
            </span>
            {deadlineStats.dueWithin24hCount > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold px-2.5 py-0.5 bg-rose-50 text-rose-700 border border-rose-300 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-600 animate-pulse" />
                {deadlineStats.dueWithin24hCount} Due &le; 24h
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Physical, visible actions ready to execute right now. Group and filter by context, energy, time, or deadline.
          </p>
        </div>

        {/* View Grouping Switcher */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg shrink-0">
          <span className="text-[11px] font-semibold text-slate-400 px-2 select-none hidden md:inline">Group:</span>
          <button
            onClick={() => setGroupBy('context')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer flex items-center gap-1.5 ${
              groupBy === 'context'
                ? 'bg-white text-teal-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Tag className="w-3.5 h-3.5 text-teal-600" />
            <span>By Context</span>
          </button>
          <button
            onClick={() => setGroupBy('project')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer flex items-center gap-1.5 ${
              groupBy === 'project'
                ? 'bg-white text-blue-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-blue-600" />
            <span>By Project</span>
          </button>
          <button
            onClick={() => setGroupBy('none')}
            className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer flex items-center gap-1.5 ${
              groupBy === 'none'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <List className="w-3.5 h-3.5 text-slate-600" />
            <span>Flat</span>
          </button>
        </div>
      </div>

      {/* Context Filter Bar */}
      <div className="bg-white border border-slate-200/90 rounded-xl p-3 shadow-2xs space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-teal-600" />
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">Filter by Context:</span>
          </div>
          {filterContext !== 'all' && (
            <button
              onClick={() => setFilterContext('all')}
              className="text-xs text-teal-700 hover:text-teal-900 font-medium underline cursor-pointer"
            >
              Reset context filter
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <button
            onClick={() => setFilterContext('all')}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              filterContext === 'all'
                ? 'bg-slate-800 text-white shadow-2xs'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            All Contexts ({contextCounts.all})
          </button>

          {uniqueContexts.map(contextName => {
            const meta = getContextMeta(contextName);
            const Icon = meta.icon;
            const count = contextCounts[contextName] || 0;
            const isSelected = filterContext === contextName;

            return (
              <button
                key={contextName}
                onClick={() => setFilterContext(isSelected ? 'all' : contextName)}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer border ${
                  isSelected
                    ? meta.activeFilterClass
                    : `${meta.colorClass} hover:brightness-95`
                }`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                <span>{contextName}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-black/10 tabular-nums">
                  {count}
                </span>
              </button>
            );
          })}

          {contextCounts.none > 0 && (
            <button
              onClick={() => setFilterContext(filterContext === 'none' ? 'all' : 'none')}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer border ${
                filterContext === 'none'
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
              }`}
            >
              <span>No Context</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-black/10 tabular-nums">
                {contextCounts.none}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Secondary Criteria Filter Bar (Deadlines, Energy, Time) */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white/70 border border-slate-200/80 rounded-xl p-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Deadline filter tabs */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setFilterDeadline('all')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filterDeadline === 'all' ? 'bg-white text-teal-900 font-semibold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Deadlines
            </button>
            <button
              onClick={() => setFilterDeadline('due_soon')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer flex items-center gap-1 ${
                filterDeadline === 'due_soon' ? 'bg-rose-600 text-white font-semibold shadow-xs' : 'text-rose-700 hover:text-rose-900'
              }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              Due &le; 24h ({deadlineStats.dueWithin24hCount})
            </button>
            <button
              onClick={() => setFilterDeadline('upcoming')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filterDeadline === 'upcoming' ? 'bg-white text-blue-900 font-semibold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Upcoming ({deadlineStats.upcomingCount})
            </button>
          </div>

          {/* Energy filter */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setFilterEnergy('all')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filterEnergy === 'all' ? 'bg-white text-teal-900 font-semibold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Energy
            </button>
            <button
              onClick={() => setFilterEnergy('low')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filterEnergy === 'low' ? 'bg-white text-blue-900 font-semibold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Low
            </button>
            <button
              onClick={() => setFilterEnergy('high')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filterEnergy === 'high' ? 'bg-white text-teal-900 font-semibold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              High
            </button>
          </div>

          {/* Time filter */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setFilterTime('all')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filterTime === 'all' ? 'bg-white text-teal-900 font-semibold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Time
            </button>
            <button
              onClick={() => setFilterTime('15')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                filterTime === '15' ? 'bg-white text-teal-900 font-semibold shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              &le; 15m
            </button>
          </div>
        </div>

        <div className="text-xs text-slate-400 font-mono">
          Showing {filteredActions.length} of {nextActions.length} actions
        </div>
      </div>

      {/* Main Actions Display */}
      {filteredActions.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-2xs">
          <p className="text-sm font-semibold text-slate-800">
            {searchQuery 
              ? `No next actions match "${searchQuery}"`
              : filterContext !== 'all'
              ? `No next actions match context "${filterContext}"`
              : 'No actions match current filters'}
          </p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {searchQuery
              ? 'Check your spelling or switch views to see matches.'
              : 'Try selecting "All Contexts" or resetting your energy and time filters.'}
          </p>
          <div className="flex items-center justify-center gap-2 pt-2">
            {searchQuery && onClearSearch && (
              <button
                onClick={onClearSearch}
                className="px-3.5 py-1.5 text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg cursor-pointer transition-colors"
              >
                Clear search filter
              </button>
            )}
            {filterContext !== 'all' && (
              <button
                onClick={() => setFilterContext('all')}
                className="px-3.5 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg cursor-pointer transition-colors"
              >
                Show all contexts
              </button>
            )}
          </div>
        </div>
      ) : groupBy === 'context' ? (
        /* Render Grouped by Context */
        <div className="space-y-5">
          {groupedByContext.map(group => {
            const meta = getContextMeta(group.context);
            const Icon = meta.icon;

            return (
              <div
                key={group.key}
                className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs"
              >
                {/* Context Section Header */}
                <div className={`px-4 py-3 border-b flex items-center justify-between ${meta.cardHeaderClass}`}>
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-white shadow-2xs">
                      <Icon className="w-4 h-4 text-slate-700" />
                    </div>
                    <div>
                      <div className="text-xs font-bold font-mono tracking-tight text-slate-900">
                        {group.label}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {group.actions.length} {group.actions.length === 1 ? 'action available' : 'actions available'} in this context
                      </div>
                    </div>
                  </div>

                  <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-white/80 rounded-full border border-slate-200/80">
                    {group.actions.length}
                  </span>
                </div>

                {/* Actions in this Context */}
                <div className="divide-y divide-slate-100">
                  {group.actions.map(action => renderActionRow(action))}
                </div>
              </div>
            );
          })}
        </div>
      ) : groupBy === 'project' ? (
        /* Render Grouped by Project */
        <div className="space-y-5">
          {groupedByProject.map(group => (
            <div
              key={group.key}
              className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs"
            >
              {/* Project Section Header */}
              <div className="px-4 py-3 bg-blue-50/60 border-b border-blue-100 flex items-center justify-between text-blue-950">
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg bg-white shadow-2xs text-blue-700">
                    <Layers className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold tracking-tight">
                      {group.label}
                    </div>
                    <div className="text-[11px] text-blue-600/80">
                      {group.actions.length} next action{group.actions.length === 1 ? '' : 's'}
                    </div>
                  </div>
                </div>

                <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-white/80 text-blue-800 rounded-full border border-blue-200/80">
                  {group.actions.length}
                </span>
              </div>

              {/* Actions in this Project */}
              <div className="divide-y divide-slate-100">
                {group.actions.map(action => renderActionRow(action))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Flat List */
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs divide-y divide-slate-100">
          {filteredActions.map(action => renderActionRow(action))}
        </div>
      )}
    </div>
  );
};
