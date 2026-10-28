import React, { useState } from 'react';
import { Copy, Check, GitCommit, ArrowDown, ArrowRight } from 'lucide-react';

export const MermaidDiagram: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const mermaidSource = `erDiagram
    ITEMS ||--o{ ITEMS : "parent_id / project_id (hierarchy)"
    ITEMS ||--o{ ITEM_TAGS : "tagged with"
    TAGS ||--o{ ITEM_TAGS : "applies to"
    TAGS ||--o{ TAGS : "parent_id (hierarchy)"
    ITEMS ||--o| REPEAT_RULES : "repeats via"
    ITEMS ||--o{ ITEM_ATTACHMENTS : "references"
    ITEMS ||--o{ REVIEW_RECORDS : "reviewed in"
    HORIZON_NOTES ||--o{ ITEMS : "anchors projects"

    ITEMS {
        text id PK
        text type "folder | project | action"
        text title
        text parent_id FK
        text project_id FK
        int rank
        text status "inbox | active | on_hold | completed | dropped"
        bool flagged
        text project_type "sequential | parallel | single_action"
        timestamp defer_date
        timestamp due_date
        int estimated_minutes
        text energy_level
        timestamp completed_at
    }

    TAGS {
        text id PK
        text name
        text parent_id FK
        int rank
        bool is_context
    }

    ITEM_TAGS {
        text item_id PK,FK
        text tag_id PK,FK
    }

    REPEAT_RULES {
        text id PK
        text item_id FK
        text frequency "daily|weekly|monthly|yearly"
        int interval
        text repeat_from "scheduled_date|completion_date"
    }

    PERSPECTIVES {
        text id PK
        text name
        json filter_rules
        text group_by
        text sort_by
    }

    REVIEW_RECORDS {
        text id PK
        text project_id FK
        text review_type
        timestamp completed_at
        int items_processed
    }

    HORIZON_NOTES {
        text id PK
        int horizon_level "2 to 5"
        text title
        text area_folder_id FK
    }
`;

  const copyMermaid = () => {
    navigator.clipboard.writeText(mermaidSource);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            Entity-Relationship Architecture Diagram
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Visual model of items, tags, recurrence, review records, and horizons.
          </p>
        </div>
        <button
          onClick={copyMermaid}
          className="flex items-center gap-2 text-xs font-medium text-slate-700 hover:text-slate-900 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer shrink-0"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span>Copied Mermaid Code</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy Mermaid Code</span>
            </>
          )}
        </button>
      </div>

      {/* Visual Architectural Map */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Core Entity Box */}
        <div className="border-2 border-slate-900 bg-slate-50 rounded-xl p-5 lg:col-span-1 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <span className="font-bold text-sm text-slate-900 uppercase tracking-wide">
              ITEMS (Core Table)
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-200 rounded text-slate-700">
              Unified Hierarchy
            </span>
          </div>
          <div className="text-xs text-slate-600 space-y-1 font-mono">
            <div>• Folders (Area of Focus)</div>
            <div>• Projects (Sequential / Parallel / SAL)</div>
            <div>• Actions (Next Actions / Delegated)</div>
            <div>• Sub-actions (Checklists)</div>
          </div>
          <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500 font-sans">
            Self-referencing via <code>parent_id</code> & <code>project_id</code>. Holds status, dates, and order.
          </div>
        </div>

        {/* Associated Metadata Entities */}
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="border border-slate-200 rounded-lg p-3 bg-white space-y-1.5">
            <div className="font-semibold text-xs text-slate-900 flex items-center justify-between">
              <span>TAGS & ITEM_TAGS</span>
              <span className="text-[10px] text-slate-400 font-mono">M:N Relation</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Multiple tags per item. Tags can be nested (hierarchical contexts: Place, Tool, Person, Energy, Time).
            </p>
          </div>

          <div className="border border-slate-200 rounded-lg p-3 bg-white space-y-1.5">
            <div className="font-semibold text-xs text-slate-900 flex items-center justify-between">
              <span>REPEAT_RULES</span>
              <span className="text-[10px] text-slate-400 font-mono">1:1 with Items</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Fixed schedule vs repeat-from-completion semantics. Regenerates next action upon marking complete.
            </p>
          </div>

          <div className="border border-slate-200 rounded-lg p-3 bg-white space-y-1.5">
            <div className="font-semibold text-xs text-slate-900 flex items-center justify-between">
              <span>REVIEW_RECORDS</span>
              <span className="text-[10px] text-slate-400 font-mono">Audit Log</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Tracks Weekly Review sessions and per-project review timestamps to surface stalled projects.
            </p>
          </div>

          <div className="border border-slate-200 rounded-lg p-3 bg-white space-y-1.5">
            <div className="font-semibold text-xs text-slate-900 flex items-center justify-between">
              <span>HORIZON_NOTES</span>
              <span className="text-[10px] text-slate-400 font-mono">Horizons 2 - 5</span>
            </div>
            <p className="text-[11px] text-slate-500">
              Anchors high-level vision (Goals, Vision, Purpose) directly to operational projects.
            </p>
          </div>
        </div>
      </div>

      {/* Mermaid Source Code viewer */}
      <div className="pt-2">
        <label className="block text-xs font-semibold text-slate-700 mb-2">
          Mermaid Specification (Copyable for markdown or documentation rendering):
        </label>
        <pre className="p-4 bg-slate-900 text-slate-200 rounded-lg text-xs font-mono overflow-x-auto">
          {mermaidSource}
        </pre>
      </div>
    </div>
  );
};
