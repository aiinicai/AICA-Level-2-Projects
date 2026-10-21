import React, { useState } from 'react';
import { Copy, Check, Terminal, Shield } from 'lucide-react';

export const SqlSchemaViewer: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const sqlDDL = `-- ============================================================================
-- GTDProductivity Relational Database Schema (PostgreSQL / SQLite Compatible)
-- Embodying David Allen's Getting Things Done & OmniFocus Power-User Engine
-- ============================================================================

-- 1. Unified Items Table (Folders, Projects, Actions, Sub-actions)
CREATE TABLE items (
    id                   TEXT PRIMARY KEY,
    type                 TEXT NOT NULL CHECK (type IN ('folder', 'project', 'action')),
    title                TEXT NOT NULL,
    notes                TEXT DEFAULT '',
    
    -- Hierarchy & Lineage
    parent_id            TEXT REFERENCES items(id) ON DELETE CASCADE,
    project_id           TEXT REFERENCES items(id) ON DELETE CASCADE,
    rank                 INTEGER NOT NULL DEFAULT 0,
    
    -- Status & Flags
    status               TEXT NOT NULL DEFAULT 'inbox' 
                         CHECK (status IN ('inbox', 'active', 'on_hold', 'completed', 'dropped')),
    flagged              BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- GTD Waiting For Delegation
    waiting_for_person   TEXT,
    waiting_since        TIMESTAMP WITH TIME ZONE,
    
    -- OmniFocus Date Discipline
    defer_date           TIMESTAMP WITH TIME ZONE, -- Soft "Available From" (Tickler)
    due_date             TIMESTAMP WITH TIME ZONE, -- Hard Landscape Deadline ONLY
    estimated_minutes    INTEGER,                  -- Time Available Criterion
    energy_level         TEXT CHECK (energy_level IN ('low', 'medium', 'high')),
    completed_at         TIMESTAMP WITH TIME ZONE,
    dropped_at           TIMESTAMP WITH TIME ZONE,
    
    -- Project-Specific Attributes
    project_type         TEXT CHECK (project_type IN ('sequential', 'parallel', 'single_action')),
    review_interval_days INTEGER DEFAULT 7,
    last_reviewed_at     TIMESTAMP WITH TIME ZONE,
    next_review_at       TIMESTAMP WITH TIME ZONE,
    npm_plan_json        JSON,                     -- Natural Planning Model
    
    -- Audit & Soft-Delete Safety
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at           TIMESTAMP WITH TIME ZONE  -- Soft-delete for 30-day trash safety
);

-- 2. Tags Table (Hierarchical Contexts)
CREATE TABLE tags (
    id                   TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    parent_id            TEXT REFERENCES tags(id) ON DELETE SET NULL,
    color                TEXT,
    icon                 TEXT,
    rank                 INTEGER NOT NULL DEFAULT 0,
    is_context           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Item Tags Junction Table (M:N)
CREATE TABLE item_tags (
    item_id              TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    tag_id               TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id, tag_id)
);

-- 4. Repeat Rules Table
CREATE TABLE repeat_rules (
    id                   TEXT PRIMARY KEY,
    item_id              TEXT NOT NULL UNIQUE REFERENCES items(id) ON DELETE CASCADE,
    frequency            TEXT NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    interval             INTEGER NOT NULL DEFAULT 1,
    repeat_from          TEXT NOT NULL CHECK (repeat_from IN ('scheduled_date', 'completion_date')),
    days_of_week_json    JSON,
    end_type             TEXT NOT NULL DEFAULT 'never' CHECK (end_type IN ('never', 'after_occurrences', 'on_date')),
    end_occurrences      INTEGER,
    end_date             TIMESTAMP WITH TIME ZONE,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Saved Perspectives Table
CREATE TABLE perspectives (
    id                   TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    icon                 TEXT NOT NULL,
    is_builtin           BOOLEAN NOT NULL DEFAULT FALSE,
    filter_rules_json    JSON NOT NULL,
    group_by             TEXT NOT NULL DEFAULT 'none',
    sort_by              TEXT NOT NULL DEFAULT 'rank',
    sort_order           TEXT NOT NULL DEFAULT 'asc',
    rank                 INTEGER NOT NULL DEFAULT 0,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Review Records Audit Table
CREATE TABLE review_records (
    id                   TEXT PRIMARY KEY,
    project_id           TEXT REFERENCES items(id) ON DELETE SET NULL,
    review_type          TEXT NOT NULL CHECK (review_type IN ('weekly_review_full', 'single_project', 'daily_glance')),
    completed_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                TEXT,
    items_processed      INTEGER NOT NULL DEFAULT 0
);

-- 7. Item Attachments & External Links Table
CREATE TABLE item_attachments (
    id                   TEXT PRIMARY KEY,
    item_id              TEXT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    attachment_type      TEXT NOT NULL CHECK (attachment_type IN ('link', 'note', 'file_ref')),
    title                TEXT NOT NULL,
    uri_or_path          TEXT,
    text_content         TEXT,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. Horizon Notes (Areas of Focus, Goals, Vision, Purpose)
CREATE TABLE horizon_notes (
    id                   TEXT PRIMARY KEY,
    horizon_level        INTEGER NOT NULL CHECK (horizon_level BETWEEN 2 AND 5),
    title                TEXT NOT NULL,
    description          TEXT NOT NULL DEFAULT '',
    area_folder_id       TEXT REFERENCES items(id) ON DELETE SET NULL,
    linked_project_ids   JSON DEFAULT '[]',
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- HIGH-PERFORMANCE INDEXES FOR SUB-MILLISECOND AVAILABILITY QUERIES
-- ============================================================================

-- Fast availability scanner (Status + Defer + Due)
CREATE INDEX idx_items_availability ON items (status, defer_date, due_date)
    WHERE deleted_at IS NULL;

-- Sequential Action Ordering within Projects
CREATE INDEX idx_items_project_rank ON items (project_id, rank)
    WHERE deleted_at IS NULL;

-- Fast Hierarchy Lineage Traversal
CREATE INDEX idx_items_parent ON items (parent_id)
    WHERE deleted_at IS NULL;

-- Inbox Quick Filter
CREATE INDEX idx_items_inbox ON items (created_at DESC)
    WHERE status = 'inbox' AND deleted_at IS NULL;

-- Flagged Perspective Filter
CREATE INDEX idx_items_flagged ON items (due_date ASC)
    WHERE flagged = TRUE AND status = 'active' AND deleted_at IS NULL;

-- Stalled Projects Scanner (Active projects with no review or overdue review)
CREATE INDEX idx_projects_review ON items (next_review_at ASC)
    WHERE type = 'project' AND status = 'active' AND deleted_at IS NULL;

-- M:N Tag Lookups
CREATE INDEX idx_item_tags_tag_id ON item_tags (tag_id);
CREATE INDEX idx_item_tags_item_id ON item_tags (item_id);
`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(sqlDDL);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-slate-900" />
              Complete SQL DDL Schema & Availability Indexes
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              ANSI SQL compatible with PostgreSQL and SQLite. Optimized for 10,000+ items and instant availability queries.
            </p>
          </div>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-2 text-xs font-medium text-slate-700 hover:text-slate-900 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer shrink-0"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>Copied to Clipboard</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy SQL DDL</span>
              </>
            )}
          </button>
        </div>

        {/* SQL Code Block */}
        <div className="mt-4 rounded-lg bg-slate-950 p-4 overflow-x-auto text-slate-200 font-mono text-xs leading-relaxed max-h-[550px] overflow-y-auto">
          <pre>{sqlDDL}</pre>
        </div>

        {/* Migration Strategy Card */}
        <div className="mt-6 p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-900">
            <Shield className="w-4 h-4 text-slate-900" />
            Migration & Storage Portability Strategy
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            1. <strong>Strict Versioning:</strong> Applied via numbered sequential migration files (e.g. <code>001_baseline_schema.sql</code>, <code>002_add_location_meta.sql</code>).<br />
            2. <strong>Local Storage Abstraction:</strong> The data access layer exposes a uniform async interface (<code>DatabaseAdapter</code>), supporting in-browser IndexedDB / SQLite WASM for the client and SQLite/PostgreSQL for headless backends.<br />
            3. <strong>Zero-Lock-In Export:</strong> Built-in <code>exportSystemToJson()</code> and <code>exportSystemToCsv()</code> allow downloading an uncompressed, complete dump at any second, ensuring user trust and portability.
          </p>
        </div>
      </div>
    </div>
  );
};
