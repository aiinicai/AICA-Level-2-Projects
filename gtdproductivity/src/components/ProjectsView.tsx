import React, { useState, useMemo } from 'react';
import { Item, ProjectType } from '../types/gtd';
import { 
  FolderPlus, 
  ChevronDown, 
  ChevronRight, 
  Plus, 
  CheckCircle2, 
  Circle, 
  Flag, 
  Layers, 
  Clock, 
  Ban, 
  PlayCircle,
  AlertCircle,
  ListTodo
} from 'lucide-react';

interface ProjectsViewProps {
  projects: Item[];
  allItems: Item[];
  searchQuery?: string;
  onClearSearch?: () => void;
  onCreateProject: (title: string, type: ProjectType, notes: string) => void;
  onAddAction: (projectId: string, title: string) => void;
  onToggleComplete: (id: string) => void;
  onToggleFlag: (id: string) => void;
}

export const ProjectsView: React.FC<ProjectsViewProps> = ({
  projects,
  allItems,
  searchQuery = '',
  onClearSearch,
  onCreateProject,
  onAddAction,
  onToggleComplete,
  onToggleFlag,
}) => {
  const [expandedProjects, setExpandedProjects] = useState<Record<string, boolean>>(() => {
    const map: Record<string, boolean> = {};
    projects.forEach(p => { map[p.id] = true; });
    return map;
  });

  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects;
    const q = searchQuery.toLowerCase().trim();
    return projects.filter(project => {
      const titleMatch = project.title.toLowerCase().includes(q);
      const notesMatch = project.notes ? project.notes.toLowerCase().includes(q) : false;
      if (titleMatch || notesMatch) return true;
      return allItems.some(i =>
        i.projectId === project.id && !i.deletedAt && (
          i.title.toLowerCase().includes(q) ||
          (i.notes && i.notes.toLowerCase().includes(q))
        )
      );
    });
  }, [projects, allItems, searchQuery]);

  const [newActionTitles, setNewActionTitles] = useState<Record<string, string>>({});
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjTitle, setNewProjTitle] = useState('');
  const [newProjType, setNewProjType] = useState<ProjectType>('sequential');
  const [newProjNotes, setNewProjNotes] = useState('');

  const toggleExpand = (id: string) => {
    setExpandedProjects(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCreateProjectSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjTitle.trim()) return;
    onCreateProject(newProjTitle, newProjType, newProjNotes);
    setNewProjTitle('');
    setNewProjNotes('');
    setShowNewProjectModal(false);
  };

  const handleAddActionSubmit = (projectId: string, e: React.FormEvent) => {
    e.preventDefault();
    const title = newActionTitles[projectId];
    if (!title || !title.trim()) return;
    onAddAction(projectId, title.trim());
    setNewActionTitles(prev => ({ ...prev, [projectId]: '' }));
  };

  const stats = useMemo(() => {
    const activeProjects = projects.filter(p => p.status === 'active');
    let stalledCount = 0;
    let totalActions = 0;
    let remainingActions = 0;

    activeProjects.forEach(project => {
      const children = allItems.filter(i => i.projectId === project.id && !i.deletedAt);
      totalActions += children.length;
      const incomplete = children.filter(c => !c.completedAt);
      remainingActions += incomplete.length;
      if (incomplete.length === 0) {
        stalledCount += 1;
      }
    });

    return {
      activeProjectsCount: activeProjects.length,
      stalledProjectsCount: stalledCount,
      totalActionsCount: totalActions,
      remainingActionsCount: remainingActions,
      completedActionsCount: totalActions - remainingActions,
    };
  }, [projects, allItems]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-600" />
              Projects
            </h2>
            <span className="text-xs font-mono font-semibold px-2 py-0.5 bg-blue-50 text-blue-800 border border-blue-200/60 rounded">
              {projects.length} Active
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Outcomes requiring more than one action step. Supports Sequential, Parallel, and Single-Action structures.
          </p>
        </div>

        <button
          onClick={() => setShowNewProjectModal(true)}
          className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors cursor-pointer flex items-center gap-2 shadow-sm shadow-blue-500/20 shrink-0"
        >
          <FolderPlus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Projects Summary Row - Blue, Red & Teal Theme */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Active Projects - Blue Card */}
        <div className="bg-gradient-to-br from-blue-50/70 to-white border border-blue-200/90 rounded-xl p-4 flex items-center justify-between shadow-2xs">
          <div>
            <div className="text-xs font-semibold text-blue-800">Active Projects</div>
            <div className="text-2xl font-bold tracking-tight text-blue-950 font-mono tabular-nums mt-0.5">
              {stats.activeProjectsCount}
            </div>
            <div className="text-[11px] text-blue-600/80 mt-0.5">
              Current multi-step outcomes
            </div>
          </div>
          <div className="p-2.5 bg-blue-100/90 text-blue-700 rounded-lg shrink-0">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        {/* Stalled Projects - Red / Coral Card */}
        <div className={`border rounded-xl p-4 flex items-center justify-between shadow-2xs ${
          stats.stalledProjectsCount > 0 
            ? 'bg-gradient-to-br from-rose-50/80 to-white border-rose-300' 
            : 'bg-gradient-to-br from-slate-50 to-white border-slate-200'
        }`}>
          <div>
            <div className={`text-xs font-semibold ${stats.stalledProjectsCount > 0 ? 'text-rose-800' : 'text-slate-600'}`}>
              Stalled Projects
            </div>
            <div className={`text-2xl font-bold tracking-tight font-mono tabular-nums mt-0.5 ${stats.stalledProjectsCount > 0 ? 'text-rose-600' : 'text-slate-800'}`}>
              {stats.stalledProjectsCount}
            </div>
            <div className={`text-[11px] mt-0.5 ${stats.stalledProjectsCount > 0 ? 'text-rose-700/80 font-medium' : 'text-slate-400'}`}>
              {stats.stalledProjectsCount === 0 ? 'All projects have next action' : 'Require defined next action'}
            </div>
          </div>
          <div className={`p-2.5 rounded-lg shrink-0 ${stats.stalledProjectsCount > 0 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-500'}`}>
            <AlertCircle className="w-5 h-5" />
          </div>
        </div>

        {/* Total Actions - Teal Card */}
        <div className="bg-gradient-to-br from-teal-50/70 to-white border border-teal-200/90 rounded-xl p-4 flex items-center justify-between shadow-2xs">
          <div>
            <div className="text-xs font-semibold text-teal-800">Total Actions</div>
            <div className="text-2xl font-bold tracking-tight text-teal-950 font-mono tabular-nums mt-0.5">
              {stats.totalActionsCount}
            </div>
            <div className="text-[11px] text-teal-700/80 mt-0.5 font-mono tabular-nums">
              {stats.remainingActionsCount} remaining · {stats.completedActionsCount} completed
            </div>
          </div>
          <div className="p-2.5 bg-teal-100/90 text-teal-700 rounded-lg shrink-0">
            <ListTodo className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Projects List */}
      <div className="space-y-4">
        {filteredProjects.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-2xs">
            <h3 className="text-sm font-bold text-slate-900">
              {searchQuery ? `No matching projects or actions` : 'No Active Projects'}
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchQuery
                ? `No projects or actions match "${searchQuery}".`
                : 'Clarify multi-step outcomes from your Inbox, or click New Project to begin.'}
            </p>
            {searchQuery && onClearSearch && (
              <div className="pt-2">
                <button
                  onClick={onClearSearch}
                  className="px-3.5 py-1.5 text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg cursor-pointer transition-colors"
                >
                  Clear search filter
                </button>
              </div>
            )}
          </div>
        ) : (
          filteredProjects.map((project) => {
            const projectChildren = allItems
              .filter(i => i.projectId === project.id && !i.deletedAt)
              .sort((a, b) => a.rank - b.rank);
            const isExpanded = searchQuery.trim() ? true : expandedProjects[project.id];
            const incompleteChildren = projectChildren.filter(c => !c.completedAt);
            const completedCount = projectChildren.length - incompleteChildren.length;
            const isStalled = project.status === 'active' && incompleteChildren.length === 0;

            return (
              <div key={project.id} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
                {/* Project Header */}
                <div
                  onClick={() => toggleExpand(project.id)}
                  className="p-4 bg-slate-50/70 hover:bg-slate-100/70 transition-colors flex items-center justify-between cursor-pointer border-b border-slate-100"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-slate-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-500" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-900">
                          {project.title}
                        </span>
                        {project.projectType === 'sequential' && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200/80 font-medium">
                            Sequential
                          </span>
                        )}
                        {project.projectType === 'parallel' && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200/80 font-medium">
                            Parallel
                          </span>
                        )}
                        {project.projectType === 'single_action' && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                            Single-Action
                          </span>
                        )}
                        {isStalled && (
                          <span className="text-[10px] font-semibold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded flex items-center gap-1 shadow-2xs">
                            <AlertCircle className="w-3 h-3 text-rose-600" /> Stalled (No next action)
                          </span>
                        )}
                      </div>
                      {project.notes && (
                        <p className="text-xs text-slate-500 mt-0.5">
                          {project.notes}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-slate-500 font-mono">
                    <span className="text-teal-700 font-medium">
                      {completedCount}/{projectChildren.length} done
                    </span>
                  </div>
                </div>

                {/* Project Children & Action Inserter */}
                {isExpanded && (
                  <div className="p-4 space-y-3">
                    {projectChildren.length === 0 ? (
                      <div className="text-xs text-rose-600/90 py-2 italic pl-6 bg-rose-50/40 rounded-lg border border-rose-100">
                        No actions yet. An active project must have at least one defined next action!
                      </div>
                    ) : (
                      <div className="divide-y divide-slate-100">
                        {projectChildren.map((action, idx) => {
                          const isDone = Boolean(action.completedAt);
                          const isFirstSequential = project.projectType === 'sequential' && idx === projectChildren.findIndex(a => !a.completedAt);

                          const q = searchQuery.toLowerCase().trim();
                          const isActionMatch = Boolean(
                            q && (
                              action.title.toLowerCase().includes(q) ||
                              (action.notes && action.notes.toLowerCase().includes(q))
                            )
                          );

                          return (
                            <div
                              key={action.id}
                              className={`py-2.5 flex items-center justify-between gap-3 group px-2 rounded-lg transition-colors ${
                                isActionMatch 
                                  ? 'bg-teal-50/80 border border-teal-300/80 shadow-2xs' 
                                  : 'hover:bg-slate-50/50'
                              }`}
                            >
                              <div className="flex items-center gap-3 flex-1 min-w-0">
                                <button
                                  onClick={() => onToggleComplete(action.id)}
                                  className="text-slate-400 hover:text-teal-600 cursor-pointer shrink-0 transition-colors"
                                >
                                  {isDone ? (
                                    <CheckCircle2 className="w-4 h-4 text-teal-600" />
                                  ) : (
                                    <Circle className="w-4 h-4" />
                                  )}
                                </button>
                                <span className={`text-xs font-medium flex-1 truncate ${isDone ? 'line-through text-slate-400' : 'text-slate-800'}`}>
                                  {action.title}
                                </span>
                                {isActionMatch && (
                                  <span className="text-[10px] font-mono font-medium text-teal-700 bg-teal-100/70 border border-teal-300 px-1.5 py-0.2 rounded shrink-0">
                                    Matches query
                                  </span>
                                )}
                                {isFirstSequential && !isDone && (
                                  <span className="text-[10px] font-semibold text-teal-800 bg-teal-50 border border-teal-200/80 px-2 py-0.5 rounded shrink-0">
                                    Next Action
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center gap-2 shrink-0">
                                {action.estimatedMinutes && (
                                  <span className="text-[11px] font-mono text-slate-400">
                                    {action.estimatedMinutes}m
                                  </span>
                                )}
                                <button
                                  onClick={() => onToggleFlag(action.id)}
                                  className={`p-1 rounded cursor-pointer transition-colors ${
                                    action.flagged ? 'text-rose-500' : 'text-slate-300 opacity-0 group-hover:opacity-100 hover:text-rose-400'
                                  }`}
                                >
                                  <Flag className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Quick Add Action row */}
                    <form
                      onSubmit={(e) => handleAddActionSubmit(project.id, e)}
                      className="pt-2 flex items-center gap-2"
                    >
                      <input
                        type="text"
                        value={newActionTitles[project.id] || ''}
                        onChange={(e) => setNewActionTitles({ ...newActionTitles, [project.id]: e.target.value })}
                        placeholder="+ Add physical next action..."
                        className="text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg flex-1 outline-none focus:border-blue-400 focus:bg-white transition-colors"
                      />
                      <button
                        type="submit"
                        disabled={!newActionTitles[project.id]?.trim()}
                        className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold disabled:opacity-30 cursor-pointer transition-colors"
                      >
                        Add
                      </button>
                    </form>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* New Project Modal */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="w-full max-w-md bg-white rounded-xl shadow-xl border border-slate-200 p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">Create New Project</h3>
            <form onSubmit={handleCreateProjectSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Project Title (Outcome) *
                </label>
                <input
                  type="text"
                  value={newProjTitle}
                  onChange={(e) => setNewProjTitle(e.target.value)}
                  placeholder="e.g. Publish annual report"
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg outline-none focus:border-slate-900"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Structure Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setNewProjType('sequential')}
                    className={`p-2 text-xs font-medium rounded-lg border text-center cursor-pointer ${
                      newProjType === 'sequential'
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-slate-200 bg-white text-slate-700'
                    }`}
                  >
                    Sequential
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewProjType('parallel')}
                    className={`p-2 text-xs font-medium rounded-lg border text-center cursor-pointer ${
                      newProjType === 'parallel'
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-slate-200 bg-white text-slate-700'
                    }`}
                  >
                    Parallel
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewProjType('single_action')}
                    className={`p-2 text-xs font-medium rounded-lg border text-center cursor-pointer ${
                      newProjType === 'single_action'
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-slate-200 bg-white text-slate-700'
                    }`}
                  >
                    Single-Action
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Notes / Outcome Vision
                </label>
                <textarea
                  value={newProjNotes}
                  onChange={(e) => setNewProjNotes(e.target.value)}
                  rows={2}
                  placeholder="Notes, scope, or principles..."
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg outline-none focus:border-slate-900"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewProjectModal(false)}
                  className="px-3 py-2 text-xs text-slate-600 hover:text-slate-900 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newProjTitle.trim()}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
                >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
