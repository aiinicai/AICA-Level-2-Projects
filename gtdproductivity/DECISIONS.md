# Architecture Decision Records (ADRs) - GTDProductivity

## Status Legend
- **PROPOSED**: Awaiting user review and approval in Phase 0.
- **ACCEPTED**: Approved for implementation.
- **SUPERSEDED**: Replaced by subsequent decision.

---

### ADR-001: Platform & Technology Stack
- **Status**: PROPOSED
- **Context**: The user requires a personal, trusted-system task manager adhering to David Allen's Getting Things Done (GTD) and inspired by OmniFocus's depth. Key non-functional requirements include capture in under 3 seconds, local-first offline storage, high performance (10k+ items, 500+ projects), keyboard accessibility, and zero data lock-in (JSON/CSV exports).
- **Options Evaluated**:
  1. *Python 3.11+ / PyQt6 + SQLite (desktop native)*: Solid offline local SQLite architecture, but requires OS-specific desktop packaging/installers (PyInstaller/pipx/dmg/exe), lacks zero-friction instant web execution in cloud preview environments, and makes cross-device sync (e.g. mobile/tablet companion) significantly harder.
  2. *TypeScript + React + Vite + Local-First Engine (Web / PWA / Desktop via Tauri/Electron)*: Instant interactive feedback in modern browsers, zero install requirement, works offline via IndexedDB / Web SQL / WASM SQLite / OPFS, full keyboard shortcut engine, and seamless portability to desktop (Tauri) or mobile (PWA/Capacitor) without rewriting core logic.
- **Decision / Recommendation**: Adopt **TypeScript + React + Vite** with a modular local-first database adapter (IndexedDB with Dexie / in-memory SQLite WASM + structured JSON/CSV export & backup engine). Standard, readable functional components with strong TypeScript models, zero-slop typography, and robust local persistence.
- **Consequences**:
  - Positive: Instant reactivity, cross-platform reach, zero-dependency launch, rich keyboard binding support (`Hotkeys`), visual clarity.
  - Mitigations: Global OS hotkeys when outside the browser require PWA/desktop wrapper (Tauri/Electron in Phase 6); browser tabs handle shortcuts reliably when focused.

---

### ADR-002: Data Model - Unified Item Table vs. Separate Tables
- **Status**: PROPOSED
- **Context**: In GTD and OmniFocus, an item can evolve: a simple Inbox action might turn into a multi-action Project; a Project can be nested under a Folder; Actions can have Sub-actions (checklists/action groups); and Single-Action Lists hold independent actions.
- **Options Evaluated**:
  1. *Separate tables (`folders`, `projects`, `actions`, `subactions`)*: Enforces strict schemas per type at the SQL level, but causes schema duplication (title, notes, dates, status, flags apply to projects and actions alike), makes converting an action into a project require cross-table deletes/inserts and foreign-key repointing, and complicates recursive queries.
  2. *Unified `items` table with self-referencing hierarchy (`parent_id`, `project_id`, `type: 'folder' | 'project' | 'action'`)*: OmniFocus's proven architectural model. An item has a `type` discriminator. An action can be promoted to a project simply by changing `type = 'project'` and adding children. Actions point to their enclosing `project_id` (for fast indexing) and optional `parent_id` (for sub-action trees).
- **Decision / Recommendation**: Adopt the **Unified `items` table architecture** with specialized nullable attributes for project-specific settings (e.g., `project_type: 'sequential' | 'parallel' | 'single_action'`, `review_interval_days`, `last_reviewed_at`, `next_review_at`).
- **Consequences**:
  - High performance: One single recursive query or flattened indexed scan resolves the entire action tree.
  - Seamless evolution: Promoting an inbox task into a project is an $O(1)$ attribute update.
  - Clear constraints: Check constraints ensure folders cannot have due dates, and sequential projects respect rank order among children.

---

### ADR-003: Availability Calculation Engine & Indexing
- **Status**: PROPOSED
- **Context**: In OmniFocus/GTD, an action is not simply "pending" or "done". It has an availability state determined dynamically:
  - **Available**: Project is active, action is not deferred (`defer_date <= now()` or null), action is not blocked by a prior incomplete action in a sequential project, and action is not on hold / dropped.
  - **Blocked**: Action is preceded by an incomplete item in a sequential project or parent group.
  - **Deferred**: Action or its parent/project has `defer_date > now()`.
  - **Due Soon**: Action has `due_date` within user's due-soon window (default 24h or 48h).
  - **Overdue**: Action has `due_date < now()`.
  - **Completed** / **Dropped**: Terminal states.
- **Decision / Recommendation**:
  - The database stores canonical state (`status: 'inbox' | 'active' | 'on_hold' | 'completed' | 'dropped'`), dates (`defer_date`, `due_date`, `completed_at`), and sequencing (`rank`, `parent_id`, `project_type`).
  - An in-memory, deterministic **Availability Engine** calculates dynamic availability (`isAvailable`, `isBlocked`, `isDeferred`, `isDueSoon`, `isOverdue`, `isStalled`) with sub-millisecond memoized evaluation.
  - Composite indexes on `(status, defer_date, due_date)` and `(project_id, rank)` keep queries under 2ms even with 10,000+ items.

---

### ADR-004: Horizon Notes & Area of Focus Architecture
- **Status**: PROPOSED
- **Context**: GTD defines Horizons of Focus (Runway through Horizon 5). Areas of Focus (Horizon 2) represent ongoing areas of responsibility without end dates (e.g. Health, Finance, Product Leadership).
- **Decision**: Represent Horizon 2 (Areas of Focus) as top-level Folders / Groups that enclose Projects and Single-Action Lists. Provide dedicated `horizon_notes` records for Horizons 3, 4, 5 (1-2 Year Goals, 3-5 Year Vision, Life Purpose & Principles) that can be linked to Projects as their driving motivation ("Outcome Vision").

---

### ADR-005: Perspectives Engine Serialization
- **Status**: PROPOSED
- **Context**: Users need built-in views (Inbox, Projects, Tags, Forecast, Flagged, Review, Waiting For, Someday/Maybe, Stalled) plus the ability to create and save custom perspectives.
- **Decision**: Perspectives are stored in a dedicated `perspectives` table with a clean JSON filter schema:
  ```json
  {
    "filter": {
      "item_types": ["action"],
      "availability": ["available"],
      "flagged": true,
      "tag_ids": ["tag-1"],
      "project_ids": []
    },
    "group_by": "tag",
    "sort_by": "due_date",
    "sort_order": "asc"
  }
  ```

---

### ADR-006: Audit Trail, Safety & Change Log
- **Status**: ACCEPTED
- **Context**: A trusted system must never lose tasks, accidentally wipe data, or cause anxiety.
- **Decision**: Implement soft deletion (`deleted_at IS NOT NULL`) with a 30-day Trash bucket before permanent purge, an in-memory undo/redo command stack, and automatic rolling snapshots to local backup storage on every major session transition.

---

### ADR-007: Guided Clarify Flow State Machine & Two-Minute Rule Execution
- **Status**: ACCEPTED (Phase 1)
- **Context**: David Allen emphasizes that processing the inbox must happen one item at a time to prevent cherry-picking easy tasks while avoiding difficult ones.
- **Decision**: 
  - The Clarify modal enforces sequential, single-item focus.
  - Non-actionable items branch directly to Trash, Someday/Maybe, or Reference.
  - Actionable items enforce a verb-first physical action nudge ("Call...", "Draft...", "Buy...").
  - An interactive 2-minute countdown timer directly enables executing tasks on the spot, marking them complete with one click upon completion.
  - Multi-step outcomes mandate creating both the Project record AND its first physical next action simultaneously, eliminating stalled "empty" projects by design.

