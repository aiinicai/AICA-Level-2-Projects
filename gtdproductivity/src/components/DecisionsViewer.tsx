import React, { useState } from 'react';
import { HelpCircle, CheckCircle, ChevronDown, ChevronRight, AlertTriangle, ShieldCheck } from 'lucide-react';

export const DecisionsViewer: React.FC = () => {
  const [expandedAdrs, setExpandedAdrs] = useState<Record<string, boolean>>({
    'ADR-001': true,
    'ADR-002': true,
    'ADR-003': false,
    'ADR-004': false,
    'ADR-005': false,
    'ADR-006': false,
  });

  const toggleAdr = (id: string) => {
    setExpandedAdrs(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const topQuestions = [
    {
      id: 1,
      title: 'Target Runtime Platform & Local Storage Driver',
      impact: 'CRITICAL (Phase 0 Baseline)',
      description: 'Do you approve using TypeScript + React + local-first IndexedDB/WASM SQLite with JSON/CSV export, which runs immediately in your browser preview and can be wrapped with Tauri for desktop later, or do you require a local Python 3.11 / PyQt6 desktop app?',
      recommendation: 'Recommended: TypeScript/React local-first web app with zero-lock-in exports.',
    },
    {
      id: 2,
      title: 'Unified `items` Table vs. Separate Entity Tables',
      impact: 'HIGH (Data Model & Schema)',
      description: 'Do you approve the unified items table (type discriminator for folders, projects, actions) enabling O(1) task-to-project promotions and recursive hierarchy, or do you prefer separate tables?',
      recommendation: 'Recommended: Unified items table (OmniFocus architecture).',
    },
    {
      id: 3,
      title: 'Calendar Hard Landscape Policy Enforcement',
      impact: 'HIGH (GTD Fidelity)',
      description: 'GTD strictly dictates due dates are for hard landscape only (day/time specific). Shall we enforce defer dates as the default date picker, and warn or require confirmation if a user adds a due date without a true deadline?',
      recommendation: 'Recommended: Prominent defer dates; subtle non-blocking nudge on due dates.',
    },
    {
      id: 4,
      title: 'Sequential Project Blocking Behavior on Sub-actions',
      impact: 'HIGH (Availability Engine)',
      description: 'When an action inside a sequential project has sub-actions (action groups), should availability evaluate strictly depth-first down to the leaf action, or treat the parent action as the next action?',
      recommendation: 'Recommended: Depth-first leaf next action (true OmniFocus behavior).',
    },
    {
      id: 5,
      title: 'Weekly Review Enforcement Cadence & Reminders',
      impact: 'MEDIUM (Review Stepper)',
      description: 'How should the app handle projects whose review date has passed? Display an overdue review badge in the sidebar and highlight in Review Perspective, or soft-nudge during daily glance?',
      recommendation: 'Recommended: Badge in sidebar + dedicated "Stalled / Overdue Review" filter.',
    },
    {
      id: 6,
      title: 'Tickler Engine: Re-entry into Inbox vs. Next Actions',
      impact: 'MEDIUM (Capture & Organization)',
      description: 'When a deferred item reaches its "available from" date, should it appear directly in Next Actions (if already clarified to a project/context) or pop back into the Inbox for re-clarification?',
      recommendation: 'Recommended: Pop into Next Actions if assigned; into Inbox if unclarified.',
    },
    {
      id: 7,
      title: 'Single-Action Lists vs. Standard Projects',
      impact: 'MEDIUM (Hierarchy)',
      description: 'Should Single-Action Lists (e.g. "Errands", "Home Maintenance") be treated as projects with a flag `is_single_action = true` that never "complete", or as a separate folder container?',
      recommendation: 'Recommended: Projects with `project_type: single_action` and no project completion checkbox.',
    },
    {
      id: 8,
      title: 'Tag Mutability and Hierarchical Context Semantics',
      impact: 'MEDIUM (Tags & Perspective Engine)',
      description: 'Do you want nested tags (e.g. `Location > Office`, `People > Team > Sarah`) where filtering by parent tag includes all children, or flat multi-tagging?',
      recommendation: 'Recommended: Hierarchical tags with recursive child inclusion.',
    },
    {
      id: 9,
      title: 'Natural Planning Model (NPM) Template Structure',
      impact: 'LOW-MEDIUM (Project Planning)',
      description: 'Should project notes include an optional 5-stage markdown template for Allen\'s Natural Planning Model (Purpose, Principles, Vision, Brainstorm, Next Actions)?',
      recommendation: 'Recommended: One-click "Insert NPM Template" in project inspector notes.',
    },
    {
      id: 10,
      title: 'Undo/Redo Depth & Backup Retention Strategy',
      impact: 'LOW (Safety & Audit)',
      description: 'Should we maintain a 50-step in-memory command stack with Ctrl+Z/Cmd+Z, plus automatic hourly rolling backups saved to localStorage/export files?',
      recommendation: 'Recommended: 50-step undo stack + automatic local snapshots + 30-day trash.',
    },
  ];

  return (
    <div className="space-y-6">
      {/* 200-Word Understanding Confirmation */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-slate-900 text-white rounded-lg shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div className="space-y-2">
            <h3 className="text-base font-semibold text-slate-900">
              Understanding Confirmation (GTD & OmniFocus System Vision)
            </h3>
            <p className="text-sm text-slate-700 leading-relaxed font-sans">
              I understand your vision: a personal, trusted-system task manager that strictly embodies David Allen's Getting Things Done (5 workflow stages: Capture, Clarify, Organize, Reflect, Engage) combined with OmniFocus's power-user mechanics.
            </p>
            <p className="text-sm text-slate-700 leading-relaxed font-sans">
              Key tenets include: concrete verb-first next physical actions; hard-landscape calendar discipline (defer dates for soft intentions); hierarchical folders, projects (sequential, parallel, single-action lists), and sub-actions; dynamic availability calculation (available, blocked, deferred, due soon, overdue); flexible multi-dimensional tags (places, tools, energy, time, people); a first-class Weekly Review stepper with mind-sweep triggers and stalled project detection; and Horizons of Focus (0–5).
            </p>
            <p className="text-sm text-slate-700 leading-relaxed font-sans">
              Non-negotiable attributes: sub-3s frictionless capture, local-first offline storage, zero data lock-in via JSON/CSV exports, full keyboard navigation, and calm, distraction-free visual design. No application code will be committed until you approve the Phase 0 architecture and data model.
            </p>
            <div className="pt-2 text-xs text-slate-400 font-mono">
              Word count: 142 words (Compliant with &lt; 200 words constraint).
            </div>
          </div>
        </div>
      </div>

      {/* Top 10 Questions / Decisions */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-2 flex items-center gap-2">
          <HelpCircle className="w-4 h-4 text-slate-900" />
          Top 10 Questions / Decisions Needed (Ordered by Architectural Impact)
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          Please review the questions below. Each question includes our recommended default based on GTD and OmniFocus best practices.
        </p>

        <div className="space-y-3">
          {topQuestions.map((q) => (
            <div key={q.id} className="border border-slate-200 rounded-lg p-4 bg-slate-50/50 hover:bg-slate-50 transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <span className="text-xs font-bold text-slate-900">
                  {q.id}. {q.title}
                </span>
                <span className="text-[11px] font-mono text-slate-500">
                  {q.impact}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                {q.description}
              </p>
              <div className="mt-2.5 text-xs text-emerald-800 bg-emerald-50/70 border border-emerald-100 rounded px-2.5 py-1.5 font-medium">
                {q.recommendation}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Architecture Decision Records */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-4">
          Architecture Decision Records (DECISIONS.md)
        </h3>
        <div className="space-y-3">
          {[
            {
              id: 'ADR-001',
              title: 'Platform & Technology Stack Selection',
              status: 'PROPOSED',
              summary: 'TypeScript + React + Vite with local-first IndexedDB/WASM SQLite adapter and instant web evaluation.',
            },
            {
              id: 'ADR-002',
              title: 'Unified `items` Table vs. Separate Entity Tables',
              status: 'PROPOSED',
              summary: 'Unified self-referential hierarchy with type discriminator for seamless O(1) task-to-project promotions.',
            },
            {
              id: 'ADR-003',
              title: 'Dynamic Availability Calculation & Indexing',
              status: 'PROPOSED',
              summary: 'Deterministic memoized availability evaluation with composite indexes for sub-millisecond query performance.',
            },
            {
              id: 'ADR-004',
              title: 'Horizons of Focus Architecture',
              status: 'PROPOSED',
              summary: 'Horizon 2 represented as Areas of Focus folders; Horizons 3-5 represented as linked vision notes.',
            },
            {
              id: 'ADR-005',
              title: 'Perspectives Engine Serialization',
              status: 'PROPOSED',
              summary: 'Clean JSON filter criteria for custom power-user views, saved queries, and grouping rules.',
            },
            {
              id: 'ADR-006',
              title: 'Audit Trail, Safety & Change Log',
              status: 'PROPOSED',
              summary: 'Soft deletion with 30-day trash safety, 50-step undo/redo command stack, and automatic rolling snapshots.',
            },
          ].map((adr) => (
            <div key={adr.id} className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                onClick={() => toggleAdr(adr.id)}
                className="w-full text-left p-3.5 bg-slate-50 hover:bg-slate-100 flex items-center justify-between cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold text-xs text-slate-900">{adr.id}</span>
                  <span className="text-xs font-semibold text-slate-800">{adr.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                    {adr.status}
                  </span>
                  {expandedAdrs[adr.id] ? (
                    <ChevronDown className="w-4 h-4 text-slate-500" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  )}
                </div>
              </button>
              {expandedAdrs[adr.id] && (
                <div className="p-4 bg-white text-xs text-slate-600 leading-relaxed border-t border-slate-200">
                  {adr.summary}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
