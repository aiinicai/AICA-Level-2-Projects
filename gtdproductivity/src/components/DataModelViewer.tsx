import React, { useState } from 'react';
import { Database, GitFork, Key, CheckCircle, Table, ArrowRight, Layers } from 'lucide-react';

export const DataModelViewer: React.FC = () => {
  const [selectedEntity, setSelectedEntity] = useState<string>('items');

  const entities = [
    { id: 'items', name: 'items', label: 'Unified Items (Folders, Projects, Actions)', count: 'Core' },
    { id: 'tags', name: 'tags', label: 'Tags & Hierarchical Contexts', count: 'Metadata' },
    { id: 'item_tags', name: 'item_tags', label: 'Item-Tag Associations (M:N)', count: 'Junction' },
    { id: 'repeat_rules', name: 'repeat_rules', label: 'Repeat Rules (Fixed vs Completion)', count: 'Recurrence' },
    { id: 'perspectives', name: 'perspectives', label: 'Perspectives (Saved Query Rules)', count: 'Views' },
    { id: 'review_records', name: 'review_records', label: 'Review Records (Weekly & Project)', count: 'Audit' },
    { id: 'item_attachments', name: 'item_attachments', label: 'Attachments & External Links', count: 'Content' },
    { id: 'horizon_notes', name: 'horizon_notes', label: 'Horizon Notes (Horizons 2 to 5)', count: 'Vision' },
  ];

  return (
    <div className="space-y-6">
      {/* Unified Table Justification Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-slate-100 rounded-lg text-slate-900 shrink-0">
            <GitFork className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Architectural Decision: Why a Unified `items` Table?
            </h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              In David Allen's GTD methodology and OmniFocus's relational model, task boundaries are fluid by design. A single inbox thought (e.g. <em>"Organize summer conference"</em>) frequently reveals itself during the Clarify step to be a multi-action Project requiring sub-actions.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-4 border-t border-slate-100">
              <div className="p-4 bg-rose-50/50 border border-rose-100 rounded-lg">
                <div className="text-xs font-semibold text-rose-800 uppercase tracking-wide">
                  Separate Tables Flaw
                </div>
                <p className="text-xs text-rose-700 mt-1 leading-relaxed">
                  Requires deleting rows from an <code>actions</code> table, inserting into a <code>projects</code> table, repointing foreign keys in tags, repeat rules, and notes, and writing complex UNION queries for search and global forecast calendars.
                </p>
              </div>
              <div className="p-4 bg-emerald-50/50 border border-emerald-100 rounded-lg">
                <div className="text-xs font-semibold text-emerald-800 uppercase tracking-wide">
                  Unified Hierarchy Advantage (Adopted)
                </div>
                <p className="text-xs text-emerald-700 mt-1 leading-relaxed">
                  Promoting an action to a project is an instantaneous O(1) update (<code>type = 'project'</code>). Sub-actions, checklists, and projects share the same notes, flags, dates, and lineage trees seamlessly.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Entity Schema Explorer */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Table className="w-4 h-4 text-slate-900" />
          Relational Schema Entities
        </h3>
        
        {/* Selector pills replaced with clean interactive tab buttons */}
        <div className="flex flex-wrap gap-2 pb-4 border-b border-slate-100">
          {entities.map((ent) => (
            <button
              key={ent.id}
              onClick={() => setSelectedEntity(ent.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer ${
                selectedEntity === ent.id
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:text-slate-900'
              }`}
            >
              {ent.name}
            </button>
          ))}
        </div>

        {/* Selected Schema Detail */}
        <div className="mt-4">
          {selectedEntity === 'items' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                Primary table representing folders, projects, actions, and sub-actions.
              </div>
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs divide-y divide-slate-200">
                  <thead className="bg-slate-50 text-slate-600 font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Column</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Nullable</th>
                      <th className="py-2.5 px-3">GTD / OmniFocus Rationale</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">id</td>
                      <td className="py-2 px-3 text-slate-600">TEXT (UUID)</td>
                      <td className="py-2 px-3 text-rose-600">NO (PK)</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Unique identifier</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">type</td>
                      <td className="py-2 px-3 text-slate-600">TEXT</td>
                      <td className="py-2 px-3 text-rose-600">NO</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Discriminator: 'folder' | 'project' | 'action'</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">title</td>
                      <td className="py-2 px-3 text-slate-600">TEXT</td>
                      <td className="py-2 px-3 text-rose-600">NO</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Physical, visible next action or project outcome</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">notes</td>
                      <td className="py-2 px-3 text-slate-600">TEXT</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Rich details, Natural Planning Model, checklists</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">parent_id</td>
                      <td className="py-2 px-3 text-slate-600">TEXT (FK)</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Self-referencing parent (folder, project, or parent action)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">project_id</td>
                      <td className="py-2 px-3 text-slate-600">TEXT (FK)</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Denormalized enclosing project for O(1) project filtering</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">rank</td>
                      <td className="py-2 px-3 text-slate-600">INTEGER</td>
                      <td className="py-2 px-3 text-rose-600">NO</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Order index inside sibling collection (controls sequential execution)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">status</td>
                      <td className="py-2 px-3 text-slate-600">TEXT</td>
                      <td className="py-2 px-3 text-rose-600">NO</td>
                      <td className="py-2 px-3 font-sans text-slate-500">'inbox' | 'active' | 'on_hold' | 'completed' | 'dropped'</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">project_type</td>
                      <td className="py-2 px-3 text-slate-600">TEXT</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">'sequential' | 'parallel' | 'single_action' (for projects only)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">defer_date</td>
                      <td className="py-2 px-3 text-slate-600">TIMESTAMP</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">"Available from" (Tickler date). Not actionable until this date</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">due_date</td>
                      <td className="py-2 px-3 text-slate-600">TIMESTAMP</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Hard landscape deadline only. Never for aspirational intent</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">waiting_for_person</td>
                      <td className="py-2 px-3 text-slate-600">TEXT</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Contact / Person delegated to</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">waiting_since</td>
                      <td className="py-2 px-3 text-slate-600">TIMESTAMP</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Date hand-off was initiated</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">review_interval_days</td>
                      <td className="py-2 px-3 text-slate-600">INTEGER</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Cadence for Weekly Review inspection (default 7 days)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">last_reviewed_at</td>
                      <td className="py-2 px-3 text-slate-600">TIMESTAMP</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">Timestamp of last project review audit</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">estimated_minutes</td>
                      <td className="py-2 px-3 text-slate-600">INTEGER</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">GTD time-available filter criterion</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold text-slate-900">energy_level</td>
                      <td className="py-2 px-3 text-slate-600">TEXT</td>
                      <td className="py-2 px-3 text-slate-400">YES</td>
                      <td className="py-2 px-3 font-sans text-slate-500">'low' | 'medium' | 'high'</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {selectedEntity === 'tags' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                Represents flexible GTD contexts (Location, Tools, People, Energy, Time).
              </div>
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs divide-y divide-slate-200">
                  <thead className="bg-slate-50 text-slate-600 font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Column</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Purpose</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    <tr>
                      <td className="py-2 px-3 font-semibold">id</td>
                      <td className="py-2 px-3">TEXT (PK)</td>
                      <td className="py-2 px-3 font-sans">Unique UUID</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold">name</td>
                      <td className="py-2 px-3">TEXT</td>
                      <td className="py-2 px-3 font-sans">Tag label (e.g. "@calls", "Deep Focus", "Errands", "Sarah")</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold">parent_id</td>
                      <td className="py-2 px-3">TEXT (FK)</td>
                      <td className="py-2 px-3 font-sans">Hierarchical tag grouping (e.g. Places &gt; Hardware Store)</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold">is_context</td>
                      <td className="py-2 px-3">BOOLEAN</td>
                      <td className="py-2 px-3 font-sans">Marks whether this tag filters physical execution context</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-3 font-semibold">rank</td>
                      <td className="py-2 px-3">INTEGER</td>
                      <td className="py-2 px-3 font-sans">Sorting order in Tag Perspective</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {selectedEntity === 'repeat_rules' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                Supports OmniFocus's dual recurrence semantics: Fixed schedule vs. Repeat-from-completion.
              </div>
              <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-700 leading-relaxed">
                <strong>Repeat from completion:</strong> "Water plants every 5 days after I actually water them" (prevents task pileup).<br />
                <strong>Fixed schedule:</strong> "File quarterly tax on the 15th regardless of completion date" (hard legal schedule).
              </div>
            </div>
          )}

          {selectedEntity === 'perspectives' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                Custom views saved as JSON rules for filtering, grouping, and ordering.
              </div>
              <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono overflow-x-auto">
{`{
  "id": "persp-next-actions",
  "name": "Next Actions",
  "icon": "play-circle",
  "filter": {
    "itemTypes": ["action"],
    "canonicalStatuses": ["active"],
    "availability": ["available", "due_soon", "overdue"],
    "waitingForOnly": false
  },
  "groupBy": "context",
  "sortBy": "due_date",
  "sortOrder": "asc"
}`}
              </pre>
            </div>
          )}

          {selectedEntity === 'horizon_notes' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                David Allen's Horizons of Focus (Horizons 2 to 5) anchoring purposeful action.
              </div>
              <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-5">
                <li><strong>Horizon 2:</strong> Areas of Focus & Accountability (Health, Finances, Team, Family).</li>
                <li><strong>Horizon 3:</strong> 1-2 Year Goals & Objectives.</li>
                <li><strong>Horizon 4:</strong> 3-5 Year Vision.</li>
                <li><strong>Horizon 5:</strong> Purpose and Principles (The "Why").</li>
              </ul>
            </div>
          )}

          {selectedEntity === 'review_records' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                Audit trail for Weekly Reviews and Project inspection dates to highlight stalled projects.
              </div>
            </div>
          )}

          {selectedEntity === 'item_tags' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                Normalized composite PK <code>(item_id, tag_id)</code> with cascade deletes and bidirectional indexes.
              </div>
            </div>
          )}

          {selectedEntity === 'item_attachments' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-500">
                Rich reference links, file URIs, and Natural Planning Model notes.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
