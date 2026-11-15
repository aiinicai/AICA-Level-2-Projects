import React, { useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { Task, TaskAttachment } from '../types';
import confetti from 'canvas-confetti';
import {
  CheckSquare,
  Square,
  Trash2,
  Paperclip,
  Clock,
  Plus,
  FileText,
  CheckCircle2,
  ChevronRight,
  ChevronDown,
  Download,
  X,
  Flame,
  Search,
  RotateCcw,
  RefreshCw,
  Pencil,
  Users,
  UserPlus,
  Save,
  AlertCircle
} from 'lucide-react';

export const TaskManagement: React.FC = () => {
  const {
    auth,
    tasks,
    addTask,
    editTask,
    toggleTaskComplete,
    deleteTask,
    addAttachmentToTask,
    staffMembers,
    addStaffMember,
    editStaffMember,
    deleteStaffMember,
    isFirebaseConnected,
    syncTasksNow
  } = useApp();

  const [isManualSyncing, setIsManualSyncing] = useState(false);

  const handleManualSync = async () => {
    setIsManualSyncing(true);
    await syncTasksNow();
    setTimeout(() => setIsManualSyncing(false), 500);
  };

  // Filter state
  const [filterMode, setFilterMode] = useState<'all' | 'pending' | 'completed' | 'urgent'>('all');
  const [selectedStaffFilter, setSelectedStaffFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Expanded task ID for viewing full details
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);

  // Task Modal state (Shared for Create & Edit — accessible to BOTH Admin and Staff)
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [taskDeadline, setTaskDeadline] = useState('');
  const [taskIsUrgent, setTaskIsUrgent] = useState(false);
  const [taskAssignedTo, setTaskAssignedTo] = useState('All Staff');
  const [taskAttachments, setTaskAttachments] = useState<TaskAttachment[]>([]);

  // Inline delete confirmation for tasks (Admin Only)
  const [confirmDeleteTaskId, setConfirmDeleteTaskId] = useState<string | null>(null);

  // Admin-Only Staff Management Modal state
  const [isStaffModalOpen, setIsStaffModalOpen] = useState(false);
  const [newStaffName, setNewStaffName] = useState('');
  const [editingStaffTarget, setEditingStaffTarget] = useState<string | null>(null);
  const [editingStaffValue, setEditingStaffValue] = useState('');
  const [confirmDeleteStaffName, setConfirmDeleteStaffName] = useState<string | null>(null);
  const [staffStatus, setStaffStatus] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Inline attachment upload for existing task
  const [activeTaskForAttachment, setActiveTaskForAttachment] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const taskAttachmentInputRef = useRef<HTMLInputElement | null>(null);

  const allAssigneeOptions = ['All Staff', ...staffMembers];

  // Filtered tasks
  const filteredTasks = tasks.filter(task => {
    if (filterMode === 'pending' && task.completed) return false;
    if (filterMode === 'completed' && !task.completed) return false;
    if (filterMode === 'urgent' && !task.isUrgent) return false;
    if (selectedStaffFilter !== 'all' && task.assignedTo !== selectedStaffFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = task.title.toLowerCase().includes(q);
      const matchDesc = task.description?.toLowerCase().includes(q);
      const matchStaff = task.assignedTo?.toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchStaff) return false;
    }
    return true;
  });

  const pendingCount = tasks.filter(t => !t.completed).length;
  const completedCount = tasks.filter(t => t.completed).length;
  const urgentCount = tasks.filter(t => t.isUrgent && !t.completed).length;

  const handleToggle = (task: Task) => {
    toggleTaskComplete(task.id);
    if (!task.completed) {
      try {
        confetti({
          particleCount: 40,
          spread: 50,
          origin: { y: 0.8 },
          colors: ['#b45309', '#f59e0b', '#fbbf24', '#10b981']
        });
      } catch (e) {}
    }
  };

  const openCreateTaskModal = () => {
    setEditingTaskId(null);
    setTaskTitle('');
    setTaskDesc('');
    setTaskDeadline('');
    setTaskIsUrgent(false);
    setTaskAssignedTo('All Staff');
    setTaskAttachments([]);
    setIsTaskModalOpen(true);
  };

  const openEditTaskModal = (task: Task, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingTaskId(task.id);
    setTaskTitle(task.title);
    setTaskDesc(task.description || '');
    setTaskDeadline(task.deadline || '');
    setTaskIsUrgent(!!task.isUrgent);
    setTaskAssignedTo(task.assignedTo || 'All Staff');
    setTaskAttachments(task.attachments || []);
    setIsTaskModalOpen(true);
  };

  const handleFileSelectForTaskModal = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    Array.from(files).forEach(file => {
      const isPdf = file.type === 'application/pdf' || file.name.endsWith('.pdf');
      const isImg = file.type.startsWith('image/');
      const sizeStr = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;

      const reader = new FileReader();
      reader.onload = () => {
        setTaskAttachments(prev => [
          ...prev,
          {
            name: file.name,
            url: reader.result as string,
            type: isPdf ? 'pdf' : isImg ? 'image' : 'file',
            size: sizeStr
          }
        ]);
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  };

  const handleFileSelectForExistingTask = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !activeTaskForAttachment) return;

    Array.from(files).forEach(file => {
      const isPdf = file.type === 'application/pdf' || file.name.endsWith('.pdf');
      const isImg = file.type.startsWith('image/');
      const sizeStr = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;

      const reader = new FileReader();
      reader.onload = () => {
        addAttachmentToTask(activeTaskForAttachment, {
          name: file.name,
          url: reader.result as string,
          type: isPdf ? 'pdf' : isImg ? 'image' : 'file',
          size: sizeStr
        });
      };
      reader.readAsDataURL(file);
    });

    setActiveTaskForAttachment(null);
    e.target.value = '';
  };

  const handleSaveTaskModal = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskTitle.trim()) return;

    const payload = {
      title: taskTitle.trim(),
      description: taskDesc.trim() || undefined,
      deadline: taskDeadline || undefined,
      isUrgent: taskIsUrgent,
      assignedTo: taskAssignedTo,
      attachments: taskAttachments
    };

    if (editingTaskId) {
      editTask(editingTaskId, payload);
    } else {
      addTask(payload);
    }

    setEditingTaskId(null);
    setTaskTitle('');
    setTaskDesc('');
    setTaskDeadline('');
    setTaskIsUrgent(false);
    setTaskAssignedTo('All Staff');
    setTaskAttachments([]);
    setIsTaskModalOpen(false);
  };

  // Staff CRUD Handlers (Admin Only)
  const handleAddStaff = (e: React.FormEvent) => {
    e.preventDefault();
    setStaffStatus(null);
    const res = addStaffMember(newStaffName);
    if (res.success) {
      setNewStaffName('');
      setStaffStatus({ type: 'success', text: res.message });
    } else {
      setStaffStatus({ type: 'error', text: res.message });
    }
  };

  const handleSaveStaffEdit = (oldName: string) => {
    setStaffStatus(null);
    const res = editStaffMember(oldName, editingStaffValue);
    if (res.success) {
      if (selectedStaffFilter === oldName) {
        setSelectedStaffFilter(editingStaffValue.trim());
      }
      setEditingStaffTarget(null);
      setEditingStaffValue('');
      setStaffStatus({ type: 'success', text: res.message });
    } else {
      setStaffStatus({ type: 'error', text: res.message });
    }
  };

  const handleConfirmDeleteStaff = (name: string) => {
    setStaffStatus(null);
    const res = deleteStaffMember(name);
    if (res.success) {
      if (selectedStaffFilter === name) {
        setSelectedStaffFilter('all');
      }
      setConfirmDeleteStaffName(null);
      setStaffStatus({ type: 'success', text: res.message });
    } else {
      setStaffStatus({ type: 'error', text: res.message });
    }
  };

  return (
    <div className="space-y-3">
      {/* TO-DO TASK WORKSPACE (Warm Dark Yellow with Light Yellowish accents) */}
      <div className="bg-amber-50/80 rounded-2xl p-2.5 sm:p-3.5 border border-amber-300 shadow-xs space-y-2">
        {/* Compact Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pb-2 border-b border-amber-200/90">
          <div className="flex items-center space-x-2">
            <span className="w-6 h-6 rounded-lg bg-gradient-to-tr from-amber-700 to-yellow-700 text-amber-50 flex items-center justify-center font-bold text-xs shadow-2xs">
              <CheckSquare className="w-3.5 h-3.5" />
            </span>
            <div>
              <h3 className="font-black text-amber-950 text-xs sm:text-sm leading-tight flex items-center space-x-1.5 flex-wrap gap-y-1">
                <span>Office To-Do Compliance Tasks</span>
                <span className="text-[9px] font-bold bg-amber-200/80 text-amber-950 px-1.5 py-0.1 rounded border border-amber-300">
                  {filteredTasks.length} active
                </span>
                <button
                  type="button"
                  onClick={handleManualSync}
                  className="text-[9px] font-bold bg-amber-100 hover:bg-amber-200 text-amber-950 px-1.5 py-0.2 rounded-md border border-amber-300 inline-flex items-center space-x-1 shadow-2xs transition-all active:scale-95 cursor-pointer"
                  title="Real-time Cloud Sync active across Mobile & Desktop. Click to refresh instantly."
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${isFirebaseConnected ? 'bg-emerald-500' : 'bg-amber-400 animate-pulse'}`}></span>
                  <span>{isFirebaseConnected ? 'Live Synced' : 'Connecting...'}</span>
                  <RefreshCw className={`w-2.5 h-2.5 text-amber-800 ${isManualSyncing ? 'animate-spin' : ''}`} />
                </button>
              </h3>
              <p className="text-[10px] text-amber-800/80 font-medium">
                Admin &amp; Staff add, edit, truncate &amp; attach • Admin-only task deletion &amp; staff directory
              </p>
            </div>
          </div>

          <div className="flex items-center flex-wrap gap-1.5">
            {/* Quick Summary Pill in Warm Amber */}
            <div className="flex items-center space-x-1.5 bg-amber-100/80 px-2 py-0.5 rounded-lg text-[10px] font-semibold text-amber-950 border border-amber-300/80 shadow-2xs">
              <span className="text-amber-950">{pendingCount} Pending</span>
              <span>•</span>
              <span className="text-red-700 font-bold">{urgentCount} Urgent</span>
              <span>•</span>
              <span className="text-amber-800">{completedCount} Done</span>
            </div>

            {/* Manage Staff Names Button — Strictly Admin Login Only */}
            {auth.role === 'admin' && (
              <button
                type="button"
                onClick={() => {
                  setStaffStatus(null);
                  setEditingStaffTarget(null);
                  setConfirmDeleteStaffName(null);
                  setIsStaffModalOpen(true);
                }}
                className="px-2.5 py-1 bg-white hover:bg-amber-100 text-amber-950 font-bold rounded-lg shadow-2xs transition-all text-[11px] flex items-center space-x-1 active:scale-95 border border-amber-300 cursor-pointer"
                title="Add, edit, or delete staff member names (Admin Only)"
              >
                <Users className="w-3 h-3 text-amber-700" />
                <span>Manage Staff</span>
              </button>
            )}

            <button
              type="button"
              onClick={openCreateTaskModal}
              className="px-2.5 py-1 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-amber-50 font-bold rounded-lg shadow-xs transition-all text-[11px] flex items-center space-x-1 active:scale-95 border border-amber-600/40 cursor-pointer"
            >
              <Plus className="w-3 h-3" />
              <span>New Task</span>
            </button>
          </div>
        </div>

        {/* REAL-TIME SEARCH BAR (Filters tasks by title or assignee in real-time) */}
        <div className="relative flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-amber-700/70 pointer-events-none" />
            <input
              type="text"
              placeholder="Search tasks in real-time by title or assignee (e.g. GSTR, Aman, Punjab, Rohit, TDS)..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-8.5 pr-8 py-1.5 text-xs bg-white border border-amber-300 rounded-xl text-amber-950 font-medium placeholder:text-amber-800/50 focus:outline-none focus:ring-1.5 focus:ring-amber-500/50 focus:border-amber-600 shadow-2xs transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2 p-0.5 rounded-full text-amber-700 hover:text-amber-950 hover:bg-amber-100 transition-colors"
                title="Clear search"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
          {searchQuery && (
            <div className="shrink-0 text-[10px] font-bold text-amber-950 bg-amber-100/90 px-2.5 py-1 rounded-xl border border-amber-300 flex items-center space-x-1">
              <span>{filteredTasks.length} {filteredTasks.length === 1 ? 'task found' : 'tasks found'}</span>
            </div>
          )}
        </div>

        {/* Filter bar & Quick Status Pills */}
        <div className="flex flex-wrap items-center justify-between gap-1.5 text-xs pt-0.5">
          <div className="flex items-center space-x-1 flex-wrap gap-y-1">
            <button
              onClick={() => setFilterMode('all')}
              className={`px-2 py-0.5 rounded-md font-bold transition-all text-[10px] sm:text-[11px] ${
                filterMode === 'all'
                  ? 'bg-amber-700 text-amber-50 shadow-xs'
                  : 'text-amber-950 bg-white hover:bg-amber-100/70 border border-amber-300/80'
              }`}
            >
              All ({tasks.length})
            </button>

            <button
              onClick={() => setFilterMode('pending')}
              className={`px-2 py-0.5 rounded-md font-bold transition-all text-[10px] sm:text-[11px] ${
                filterMode === 'pending'
                  ? 'bg-amber-700 text-amber-50 shadow-xs'
                  : 'text-amber-950 bg-white hover:bg-amber-100/70 border border-amber-300/80'
              }`}
            >
              Pending ({pendingCount})
            </button>

            <button
              onClick={() => setFilterMode('urgent')}
              className={`px-2 py-0.5 rounded-md font-bold transition-all text-[10px] sm:text-[11px] ${
                filterMode === 'urgent'
                  ? 'bg-red-700 text-white shadow-xs'
                  : 'text-amber-950 bg-white hover:bg-amber-100/70 border border-amber-300/80'
              }`}
            >
              Urgent ({urgentCount})
            </button>

            <button
              onClick={() => setFilterMode('completed')}
              className={`px-2 py-0.5 rounded-md font-bold transition-all text-[10px] sm:text-[11px] ${
                filterMode === 'completed'
                  ? 'bg-amber-700 text-amber-50 shadow-xs'
                  : 'text-amber-950 bg-white hover:bg-amber-100/70 border border-amber-300/80'
              }`}
            >
              Done ({completedCount})
            </button>
          </div>

          <div className="flex items-center space-x-1.5">
            <span className="text-[10px] text-amber-900/80 font-semibold hidden sm:inline">Assignee:</span>
            {/* Staff Filter dropdown (uses dynamic staffMembers) */}
            <select
              value={selectedStaffFilter}
              onChange={e => setSelectedStaffFilter(e.target.value)}
              className="text-[11px] bg-white border border-amber-300 rounded-md px-2 py-0.5 font-semibold text-amber-950 focus:outline-none focus:border-amber-500 shadow-2xs"
            >
              <option value="all">Staff: All</option>
              {allAssigneeOptions.map(member => (
                <option key={member} value={member}>
                  {member}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* COMPACT ONE-LINER ROWS */}
        <div className="space-y-1">
          {filteredTasks.length === 0 ? (
            <div className="bg-white/80 rounded-xl p-5 text-center border border-dashed border-amber-300 text-xs text-amber-950">
              <CheckCircle2 className="w-5 h-5 text-amber-600 mx-auto mb-1" />
              <div className="font-bold text-xs text-amber-950">
                {searchQuery.trim() ? `No tasks found matching "${searchQuery}"` : 'No tasks matching current filter'}
              </div>
              <div className="text-[10px] text-amber-800/70 mt-1">
                {searchQuery.trim() ? (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="text-amber-800 underline font-semibold hover:text-amber-950"
                  >
                    Clear search query to see all tasks
                  </button>
                ) : (
                  'All office compliance items cleared!'
                )}
              </div>
            </div>
          ) : (
            filteredTasks.map(task => {
              const isExpanded = expandedTaskId === task.id;
              const matchesSearchTitle = !!(searchQuery.trim() && task.title.toLowerCase().includes(searchQuery.toLowerCase().trim()));
              const matchesSearchAssignee = !!(searchQuery.trim() && task.assignedTo && task.assignedTo.toLowerCase().includes(searchQuery.toLowerCase().trim()));

              return (
                <div
                  key={task.id}
                  className={`rounded-lg border transition-all ${
                    task.completed
                      ? 'bg-amber-100/30 border-amber-200/60 text-amber-900/40'
                      : task.isUrgent
                      ? 'bg-red-50/50 border-red-300 hover:border-red-400 shadow-2xs'
                      : 'bg-white border-amber-200/90 hover:border-amber-400 hover:shadow-2xs'
                  }`}
                >
                  {/* ULTRA COMPACT ONE-LINER ROW */}
                  <div className="flex items-center justify-between px-2.5 py-1 gap-2 text-xs">
                    {/* Left: Checkbox & Small Title */}
                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation();
                          handleToggle(task);
                        }}
                        className={`shrink-0 transition-transform active:scale-90 ${
                          task.completed ? 'text-emerald-600' : 'text-amber-500 hover:text-amber-700'
                        }`}
                        title={task.completed ? 'Completed - Click to uncheck' : 'Tick to truncate'}
                      >
                        {task.completed ? (
                          <CheckSquare className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <Square className="w-3.5 h-3.5 text-amber-400" />
                        )}
                      </button>

                      {task.isUrgent && (
                        <span className="shrink-0 flex items-center space-x-0.5 text-[8px] font-black bg-red-100 text-red-800 border border-red-200 px-1 py-0.1 rounded uppercase">
                          <Flame className="w-2.5 h-2.5 text-red-600" />
                          <span>Urg</span>
                        </span>
                      )}

                      <span
                        onClick={() => setExpandedTaskId(isExpanded ? null : task.id)}
                        className={`font-semibold text-[11px] sm:text-xs truncate cursor-pointer hover:underline leading-tight ${
                          task.completed
                            ? 'line-through text-amber-900/40 font-normal'
                            : matchesSearchTitle
                            ? 'text-amber-950 font-black underline decoration-amber-500'
                            : 'text-amber-950 font-bold'
                        }`}
                        title={`${task.title} (Click to expand details)`}
                      >
                        {task.title}
                      </span>
                    </div>

                    {/* Middle: Badges */}
                    <div className="flex items-center space-x-1 shrink-0 text-[9px] font-medium">
                      {task.assignedTo && (
                        <span
                          className={`hidden sm:inline-block px-1.5 py-0.2 rounded border transition-colors ${
                            matchesSearchAssignee
                              ? 'bg-amber-200 text-amber-950 border-amber-400 font-bold ring-1 ring-amber-400'
                              : 'bg-amber-100/70 text-amber-900 border-amber-200/80'
                          }`}
                        >
                          {task.assignedTo.split(' ')[0]}
                        </span>
                      )}

                      {task.deadline && (
                        <span
                          className={`px-1.5 py-0.2 rounded border flex items-center space-x-1 ${
                            new Date(task.deadline) < new Date() && !task.completed
                              ? 'bg-red-100 text-red-800 border-red-200 font-bold'
                              : 'bg-amber-100/70 text-amber-900 border border-amber-200/80'
                          }`}
                        >
                          <Clock className="w-2.5 h-2.5 text-amber-700" />
                          <span>{task.deadline.slice(5)}</span>
                        </span>
                      )}

                      {task.attachments && task.attachments.length > 0 && (
                        <span className="px-1.5 py-0.2 bg-amber-100/70 text-amber-900 border border-amber-200/80 rounded flex items-center space-x-0.5">
                          <Paperclip className="w-2.5 h-2.5 text-amber-700" />
                          <span>{task.attachments.length}</span>
                        </span>
                      )}
                    </div>

                    {/* Right: Actions */}
                    <div className="flex items-center space-x-1 shrink-0">
                      {/* Truncate / Remove Truncated Option for BOTH Admin & Staff */}
                      {!task.completed ? (
                        <button
                          type="button"
                          onClick={e => {
                            e.stopPropagation();
                            handleToggle(task);
                          }}
                          className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 hover:bg-amber-300 text-amber-950 border border-amber-300 transition-all flex items-center space-x-1 shadow-2xs active:scale-95"
                          title="Click to truncate task"
                        >
                          <CheckSquare className="w-2.5 h-2.5 text-amber-800" />
                          <span>Truncate</span>
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={e => {
                            e.stopPropagation();
                            handleToggle(task);
                          }}
                          className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 hover:bg-emerald-200 text-emerald-900 border border-emerald-300 transition-all flex items-center space-x-1 shadow-2xs active:scale-95"
                          title="Task not complete? Click to remove truncated status and reopen"
                        >
                          <RotateCcw className="w-2.5 h-2.5 text-emerald-700" />
                          <span>Remove Truncated</span>
                        </button>
                      )}

                      {/* Edit Task Option — Enabled for BOTH Admin & Staff */}
                      <button
                        type="button"
                        onClick={e => openEditTaskModal(task, e)}
                        title="Edit Task (Admin & Staff)"
                        className="p-1 rounded text-amber-800 hover:text-amber-950 hover:bg-amber-100 transition-colors"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>

                      {/* Attach File — Enabled for BOTH Admin & Staff */}
                      <button
                        type="button"
                        onClick={() => {
                          setActiveTaskForAttachment(task.id);
                          taskAttachmentInputRef.current?.click();
                        }}
                        title="Attach PDF or Image file"
                        className="p-1 rounded text-amber-700 hover:text-amber-950 hover:bg-amber-100"
                      >
                        <Paperclip className="w-3 h-3" />
                      </button>

                      {/* Delete Task — Strictly ADMIN ONLY */}
                      {auth.role === 'admin' && (
                        confirmDeleteTaskId === task.id ? (
                          <div className="flex items-center space-x-1 bg-red-50 border border-red-200 rounded px-1 py-0.5">
                            <button
                              type="button"
                              onClick={e => {
                                e.stopPropagation();
                                deleteTask(task.id);
                                setConfirmDeleteTaskId(null);
                              }}
                              className="text-[9px] font-black text-red-700 hover:underline px-1"
                            >
                              Delete
                            </button>
                            <button
                              type="button"
                              onClick={e => {
                                e.stopPropagation();
                                setConfirmDeleteTaskId(null);
                              }}
                              className="text-[9px] font-bold text-slate-500 hover:text-slate-800"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={e => {
                              e.stopPropagation();
                              setConfirmDeleteTaskId(task.id);
                            }}
                            title="Remove Task Permanently (Admin Only)"
                            className="p-1 rounded text-red-600 hover:text-red-800 hover:bg-red-50 transition-colors"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        )
                      )}

                      <button
                        type="button"
                        onClick={() => setExpandedTaskId(isExpanded ? null : task.id)}
                        className="p-1 text-amber-700 hover:text-amber-950"
                      >
                        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded drawer for additional notes */}
                  {isExpanded && (
                    <div className="px-2.5 pb-2 pt-1 text-[11px] border-t border-amber-200/70 bg-amber-50/50 space-y-1">
                      {task.description && (
                        <p className={`text-[11px] ${task.completed ? 'line-through text-amber-900/40' : 'text-amber-950 font-medium'}`}>
                          {task.description}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center gap-2 text-[10px] text-amber-900/80">
                        <span>
                          Assigned to: <strong className="text-amber-950">{task.assignedTo || 'All Staff'}</strong>
                        </span>
                        {task.deadline && (
                          <span>
                            • Deadline: <strong className="text-amber-950">{task.deadline}</strong>
                          </span>
                        )}
                        {task.completed && (
                          <span className="text-emerald-700 font-bold">• Completed at {task.completedAt}</span>
                        )}
                      </div>

                      {task.attachments && task.attachments.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {task.attachments.map((att, idx) => (
                            <a
                              key={idx}
                              href={att.url}
                              download={att.name}
                              className="inline-flex items-center space-x-1 px-2 py-0.5 bg-white hover:bg-amber-100 text-amber-950 rounded text-[10px] font-semibold border border-amber-200 shadow-2xs"
                            >
                              <FileText className="w-2.5 h-2.5 text-red-600" />
                              <span className="truncate max-w-[140px]">{att.name}</span>
                              <Download className="w-2.5 h-2.5 text-amber-700" />
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Hidden file input for task attachments */}
      <input
        type="file"
        ref={taskAttachmentInputRef}
        onChange={handleFileSelectForExistingTask}
        accept=".pdf,image/*"
        className="hidden"
      />

      {/* Create / Edit Task Modal (Available to BOTH Admin & Staff) */}
      {isTaskModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-amber-200 overflow-hidden max-h-[90vh] flex flex-col">
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-5 py-3 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {editingTaskId ? (
                  <Pencil className="w-4 h-4 text-amber-200" />
                ) : (
                  <CheckSquare className="w-4 h-4 text-amber-200" />
                )}
                <div>
                  <h3 className="font-extrabold text-sm leading-tight text-white">
                    {editingTaskId ? 'Edit Office Task' : 'Assign New Task'}
                  </h3>
                  <p className="text-[11px] text-amber-200 font-medium">CA Office Compliance &amp; Client Workflow</p>
                </div>
              </div>
              <button
                onClick={() => setIsTaskModalOpen(false)}
                className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveTaskModal} className="p-4 space-y-3 overflow-y-auto flex-1 text-xs text-amber-950">
              <div>
                <label className="block font-bold text-amber-950 mb-1 text-[11px]">
                  Task Title <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  value={taskTitle}
                  onChange={e => setTaskTitle(e.target.value)}
                  placeholder="e.g. File GSTR-3B for M/s Punjab Agro Mills"
                  className="w-full px-3 py-1.5 bg-amber-50/40 border border-amber-300 rounded-xl text-xs font-semibold text-amber-950 focus:outline-none focus:border-amber-600"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-amber-950 mb-1 text-[11px]">
                  Description / Workpaper Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  value={taskDesc}
                  onChange={e => setTaskDesc(e.target.value)}
                  placeholder="e.g. Check GSTR-2B purchase reconciliation, verify RCM liability."
                  className="w-full px-3 py-1.5 bg-amber-50/40 border border-amber-300 rounded-xl text-xs font-medium text-amber-950 focus:outline-none focus:border-amber-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-bold text-amber-950 mb-1 text-[11px]">
                    Deadline (Optional)
                  </label>
                  <input
                    type="date"
                    value={taskDeadline}
                    onChange={e => setTaskDeadline(e.target.value)}
                    className="w-full px-2.5 py-1 bg-amber-50/40 border border-amber-300 rounded-xl text-xs font-semibold text-amber-950 focus:outline-none focus:border-amber-600"
                  />
                </div>

                <div>
                  <label className="block font-bold text-amber-950 mb-1 text-[11px]">
                    Assign To (Optional)
                  </label>
                  <select
                    value={taskAssignedTo}
                    onChange={e => setTaskAssignedTo(e.target.value)}
                    className="w-full px-2.5 py-1 bg-amber-50/40 border border-amber-300 rounded-xl text-xs font-semibold text-amber-950 focus:outline-none focus:border-amber-600"
                  >
                    {allAssigneeOptions.map(member => (
                      <option key={member} value={member}>
                        {member}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between p-2 bg-amber-100/60 rounded-xl border border-amber-200">
                <div className="flex items-center space-x-1.5">
                  <Flame className="w-3.5 h-3.5 text-red-600" />
                  <span className="font-bold text-amber-950 text-[11px]">Urgent Highlight (Optional)</span>
                </div>
                <input
                  type="checkbox"
                  checked={taskIsUrgent}
                  onChange={e => setTaskIsUrgent(e.target.checked)}
                  className="w-3.5 h-3.5 rounded text-amber-700 focus:ring-amber-500 border-amber-300"
                />
              </div>

              <div>
                <label className="block font-bold text-amber-950 mb-1 text-[11px]">
                  Attachments (PDF &amp; Images)
                </label>
                <div className="border border-dashed border-amber-300 rounded-xl p-2.5 text-center bg-amber-50/50">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileSelectForTaskModal}
                    multiple
                    accept=".pdf,image/*"
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-xs font-bold text-amber-800 hover:underline inline-flex items-center space-x-1"
                  >
                    <Paperclip className="w-3 h-3 text-amber-700" />
                    <span>Select PDF or Image</span>
                  </button>
                </div>

                {taskAttachments.length > 0 && (
                  <div className="mt-1 space-y-1">
                    {taskAttachments.map((att, idx) => (
                      <div key={idx} className="flex items-center justify-between p-1 bg-amber-50 rounded-lg text-[10px] font-semibold text-amber-950 border border-amber-200">
                        <span className="truncate">{att.name}</span>
                        <button
                          type="button"
                          onClick={() => setTaskAttachments(prev => prev.filter((_, i) => i !== idx))}
                          className="text-red-600 ml-2"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsTaskModalOpen(false)}
                  className="px-3 py-1 border border-amber-300 text-amber-900 rounded-xl font-bold hover:bg-amber-100 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-amber-50 font-bold rounded-xl shadow-xs flex items-center space-x-1 text-xs"
                >
                  {editingTaskId ? <Save className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                  <span>{editingTaskId ? 'Save Changes' : 'Create Task'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manage Staff Members Modal (Strictly Admin Login Only) */}
      {isStaffModalOpen && auth.role === 'admin' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-amber-200 overflow-hidden max-h-[88vh] flex flex-col">
            <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-5 py-3 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Users className="w-4 h-4 text-amber-200" />
                <div>
                  <h3 className="font-extrabold text-sm leading-tight text-white">Manage Staff Members</h3>
                  <p className="text-[11px] text-amber-200 font-medium">Admin Only • Add, Edit, or Delete Staff Names</p>
                </div>
              </div>
              <button
                onClick={() => setIsStaffModalOpen(false)}
                className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 space-y-3 overflow-y-auto flex-1 text-xs text-amber-950">
              {/* Enter new staff member form */}
              <form onSubmit={handleAddStaff} className="flex items-center gap-2">
                <input
                  type="text"
                  value={newStaffName}
                  onChange={e => setNewStaffName(e.target.value)}
                  placeholder="Enter new staff name..."
                  className="flex-1 px-3 py-1.5 bg-amber-50/50 border border-amber-300 rounded-xl text-xs font-semibold text-amber-950 focus:outline-none focus:border-amber-600"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-white font-bold rounded-xl text-xs flex items-center space-x-1 shrink-0 cursor-pointer"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>Add</span>
                </button>
              </form>

              {staffStatus && (
                <div
                  className={`p-2 rounded-xl text-[11px] flex items-center space-x-2 border ${
                    staffStatus.type === 'success'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                      : 'bg-red-50 text-red-700 border-red-200'
                  }`}
                >
                  {staffStatus.type === 'success' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-600" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-red-600" />
                  )}
                  <span>{staffStatus.text}</span>
                </div>
              )}

              {/* Existing Staff List */}
              <div className="space-y-1.5">
                <div className="text-[10px] font-black uppercase tracking-wider text-amber-800/80">
                  Office Staff List ({staffMembers.length})
                </div>

                {staffMembers.length === 0 ? (
                  <div className="p-4 text-center bg-amber-50/40 rounded-xl border border-dashed border-amber-300 text-amber-800/70">
                    No staff names added yet. Enter a name above to add.
                  </div>
                ) : (
                  staffMembers.map(member => (
                    <div
                      key={member}
                      className="flex items-center justify-between gap-2 p-2 rounded-xl bg-amber-50/50 border border-amber-200"
                    >
                      {editingStaffTarget === member ? (
                        <div className="flex items-center gap-1.5 flex-1">
                          <input
                            type="text"
                            value={editingStaffValue}
                            onChange={e => setEditingStaffValue(e.target.value)}
                            className="flex-1 px-2 py-1 bg-white border border-amber-400 rounded-lg text-xs font-semibold text-amber-950 focus:outline-none"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={() => handleSaveStaffEdit(member)}
                            className="px-2 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-[10px] font-bold"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingStaffTarget(null);
                              setEditingStaffValue('');
                            }}
                            className="px-2 py-1 bg-white border border-amber-300 text-amber-900 rounded-lg text-[10px] font-bold"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="font-bold text-xs text-amber-950 truncate">{member}</span>
                          <div className="flex items-center space-x-1 shrink-0">
                            {confirmDeleteStaffName === member ? (
                              <div className="flex items-center space-x-1 bg-red-50 border border-red-200 rounded-lg px-1.5 py-0.5">
                                <button
                                  type="button"
                                  onClick={() => handleConfirmDeleteStaff(member)}
                                  className="text-[10px] font-black text-red-700 hover:underline"
                                >
                                  Confirm
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setConfirmDeleteStaffName(null)}
                                  className="text-[10px] font-semibold text-slate-600"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingStaffTarget(member);
                                    setEditingStaffValue(member);
                                    setConfirmDeleteStaffName(null);
                                  }}
                                  title="Edit staff name"
                                  className="p-1 rounded-lg text-amber-800 hover:bg-amber-200/70 transition-colors"
                                >
                                  <Pencil className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setConfirmDeleteStaffName(member)}
                                  title="Delete staff member"
                                  className="p-1 rounded-lg text-red-600 hover:bg-red-100 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="px-4 py-2.5 bg-amber-50 border-t border-amber-200 flex justify-end">
              <button
                type="button"
                onClick={() => setIsStaffModalOpen(false)}
                className="px-3.5 py-1 bg-amber-700 hover:bg-amber-800 text-white rounded-xl text-xs font-bold"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
