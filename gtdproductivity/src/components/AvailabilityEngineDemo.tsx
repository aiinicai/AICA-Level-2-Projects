import React, { useState, useMemo } from 'react';
import { ProjectType, DynamicAvailability } from '../types/gtd';
import { CheckCircle2, Clock, Ban, AlertCircle, PlayCircle, Shield, RefreshCw } from 'lucide-react';

interface DemoTask {
  id: string;
  title: string;
  order: number;
  completed: boolean;
  deferDaysFromNow: number; // 0 = available now, >0 = deferred
  dueDaysFromNow: number | null; // null = no due date
}

export const AvailabilityEngineDemo: React.FC = () => {
  const [projectType, setProjectType] = useState<ProjectType>('sequential');
  const [projectOnHold, setProjectOnHold] = useState(false);
  const [tasks, setTasks] = useState<DemoTask[]>([
    { id: 't1', title: 'Draft proposal outline', order: 1, completed: false, deferDaysFromNow: 0, dueDaysFromNow: 1 },
    { id: 't2', title: 'Schedule stakeholder interview', order: 2, completed: false, deferDaysFromNow: 0, dueDaysFromNow: null },
    { id: 't3', title: 'Review feedback with legal counsel', order: 3, completed: false, deferDaysFromNow: 3, dueDaysFromNow: 7 },
    { id: 't4', title: 'Send finalized agreement for signature', order: 4, completed: false, deferDaysFromNow: 0, dueDaysFromNow: 14 },
  ]);

  // OmniFocus GTD Availability Algorithm Evaluation
  const evaluatedTasks = useMemo(() => {
    let foundFirstActiveSequential = false;

    return tasks.map((task) => {
      if (task.completed) {
        return { ...task, availability: 'completed' as DynamicAvailability, reason: 'Action marked completed' };
      }

      if (projectOnHold) {
        return { ...task, availability: 'blocked' as DynamicAvailability, reason: 'Parent project is On Hold' };
      }

      // Check Defer Date
      if (task.deferDaysFromNow > 0) {
        return {
          ...task,
          availability: 'deferred' as DynamicAvailability,
          reason: `Deferred for ${task.deferDaysFromNow} days (not yet available in landscape)`,
        };
      }

      // Sequential Project Logic
      if (projectType === 'sequential') {
        if (!foundFirstActiveSequential) {
          foundFirstActiveSequential = true;
          // Check due status
          if (task.dueDaysFromNow !== null && task.dueDaysFromNow <= 0) {
            return { ...task, availability: 'overdue' as DynamicAvailability, reason: 'Next Action (Overdue!)' };
          }
          if (task.dueDaysFromNow !== null && task.dueDaysFromNow <= 1) {
            return { ...task, availability: 'due_soon' as DynamicAvailability, reason: 'Next Action (Due Soon)' };
          }
          return { ...task, availability: 'available' as DynamicAvailability, reason: 'First Next Action in sequence' };
        } else {
          return {
            ...task,
            availability: 'blocked' as DynamicAvailability,
            reason: 'Blocked by preceding incomplete action in sequential project',
          };
        }
      }

      // Parallel Project Logic
      if (projectType === 'parallel') {
        if (task.dueDaysFromNow !== null && task.dueDaysFromNow <= 0) {
          return { ...task, availability: 'overdue' as DynamicAvailability, reason: 'Available (Overdue)' };
        }
        if (task.dueDaysFromNow !== null && task.dueDaysFromNow <= 1) {
          return { ...task, availability: 'due_soon' as DynamicAvailability, reason: 'Available (Due Soon)' };
        }
        return { ...task, availability: 'available' as DynamicAvailability, reason: 'Available concurrently with siblings' };
      }

      // Single-Action List Logic (all actions independent)
      return { ...task, availability: 'available' as DynamicAvailability, reason: 'Independent next action' };
    });
  }, [tasks, projectType, projectOnHold]);

  const toggleComplete = (id: string) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
  };

  const updateDefer = (id: string, delta: number) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, deferDaysFromNow: Math.max(0, t.deferDaysFromNow + delta) } : t));
  };

  const resetDemo = () => {
    setTasks([
      { id: 't1', title: 'Draft proposal outline', order: 1, completed: false, deferDaysFromNow: 0, dueDaysFromNow: 1 },
      { id: 't2', title: 'Schedule stakeholder interview', order: 2, completed: false, deferDaysFromNow: 0, dueDaysFromNow: null },
      { id: 't3', title: 'Review feedback with legal counsel', order: 3, completed: false, deferDaysFromNow: 3, dueDaysFromNow: 7 },
      { id: 't4', title: 'Send finalized agreement for signature', order: 4, completed: false, deferDaysFromNow: 0, dueDaysFromNow: 14 },
    ]);
    setProjectType('sequential');
    setProjectOnHold(false);
  };

  const renderBadge = (status: DynamicAvailability) => {
    switch (status) {
      case 'available':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
            <PlayCircle className="w-3.5 h-3.5" /> Available (Next Action)
          </span>
        );
      case 'blocked':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
            <Ban className="w-3.5 h-3.5" /> Blocked
          </span>
        );
      case 'deferred':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
            <Clock className="w-3.5 h-3.5" /> Deferred
          </span>
        );
      case 'due_soon':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-orange-700 bg-orange-50 px-2 py-0.5 rounded">
            <AlertCircle className="w-3.5 h-3.5" /> Due Soon
          </span>
        );
      case 'overdue':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded">
            <AlertCircle className="w-3.5 h-3.5" /> Overdue
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 bg-slate-50 px-2 py-0.5 rounded line-through">
            <CheckCircle2 className="w-3.5 h-3.5" /> Completed
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              OmniFocus-Style Availability Engine Verification
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Demonstrates GTD Next Action calculation based on project order, defer dates, and completion state.
            </p>
          </div>
          <button
            onClick={resetDemo}
            className="flex items-center gap-2 text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Reset Demo
          </button>
        </div>

        {/* Project Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">
              Project Structure Type
            </label>
            <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-lg">
              <button
                onClick={() => setProjectType('sequential')}
                className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  projectType === 'sequential'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Sequential (1 Next Action)
              </button>
              <button
                onClick={() => setProjectType('parallel')}
                className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  projectType === 'parallel'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Parallel (All Available)
              </button>
              <button
                onClick={() => setProjectType('single_action')}
                className={`flex-1 py-1.5 px-3 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  projectType === 'single_action'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Single-Action List
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">
              Project Status
            </label>
            <div className="flex items-center gap-3 pt-1.5">
              <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={projectOnHold}
                  onChange={(e) => setProjectOnHold(e.target.checked)}
                  className="rounded text-slate-900 focus:ring-slate-900 w-4 h-4 cursor-pointer"
                />
                Hold Project (Temporarily block all enclosed actions)
              </label>
            </div>
          </div>
        </div>

        {/* Task List Table */}
        <div className="overflow-x-auto border border-slate-200 rounded-lg mt-4">
          <table className="w-full text-left text-sm divide-y divide-slate-200">
            <thead className="bg-slate-50 text-slate-500 text-xs font-semibold">
              <tr>
                <th className="py-3 px-4 w-12">Done</th>
                <th className="py-3 px-4">Action Item</th>
                <th className="py-3 px-4">Calculated Availability</th>
                <th className="py-3 px-4">Defer Date ("Available From")</th>
                <th className="py-3 px-4">OmniFocus GTD Logic Explanation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {evaluatedTasks.map((task) => (
                <tr key={task.id} className={task.completed ? 'bg-slate-50/60' : 'hover:bg-slate-50/50'}>
                  <td className="py-3 px-4">
                    <input
                      type="checkbox"
                      checked={task.completed}
                      onChange={() => toggleComplete(task.id)}
                      className="w-4 h-4 rounded text-slate-900 focus:ring-slate-900 cursor-pointer"
                    />
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-900">
                    <span className={task.completed ? 'line-through text-slate-400' : ''}>
                      {task.order}. {task.title}
                    </span>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    {renderBadge(task.availability)}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap text-xs text-slate-600">
                    <div className="flex items-center gap-2">
                      <span className="font-mono tabular-nums">
                        {task.deferDaysFromNow === 0 ? 'Today (Now)' : `+${task.deferDaysFromNow} days`}
                      </span>
                      <div className="inline-flex gap-1">
                        <button
                          onClick={() => updateDefer(task.id, -1)}
                          disabled={task.deferDaysFromNow <= 0}
                          className="px-1.5 py-0.5 text-xs bg-slate-100 hover:bg-slate-200 rounded disabled:opacity-30 cursor-pointer"
                        >
                          -1d
                        </button>
                        <button
                          onClick={() => updateDefer(task.id, 1)}
                          className="px-1.5 py-0.5 text-xs bg-slate-100 hover:bg-slate-200 rounded cursor-pointer"
                        >
                          +1d
                        </button>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-500">
                    {task.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Algorithm Summary Callout */}
        <div className="mt-6 p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 space-y-2">
          <div className="font-semibold text-slate-800 flex items-center gap-2">
            <Shield className="w-4 h-4 text-slate-900" />
            GTD Core Rule: Trustworthy Availability Guarantee
          </div>
          <p>
            In a <strong>Sequential</strong> project, completing item #1 instantly unlocks item #2 into the <em>Next Actions</em> perspective. Items with future defer dates remain dormant in the Tickler, preventing cognitive overload. No action appears on your Next Action list until it is physically possible to execute right now.
          </p>
        </div>
      </div>
    </div>
  );
};
