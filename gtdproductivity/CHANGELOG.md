# Changelog

All notable changes to the **GTDProductivity** system will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning.

---

## [0.2.0] - Phase 1: Core Storage, Capture, Inbox & Guided Clarify Flow (Current)

### Added
- **Local-First Database Storage Engine (`src/services/storage.ts`)**:
  - Implemented persistent storage for `items` and `tags` using local storage with JSON backup and reset capabilities.
  - Seeded initial inbox items, sequential projects, parallel projects, and delegated items.
- **Reactive GTD State Store (`src/hooks/useGTDStore.ts`)**:
  - Full CRUD operations with automatic local persistence.
  - Real-time availability calculation for sequential and parallel projects.
- **Sub-3-Second Quick Capture Modal (`src/components/CaptureModal.tsx`)**:
  - Accessible via global shortcut (`c` or `n`) or top-bar button.
  - "Capture another immediately" option for rapid mind-sweeping.
- **David Allen Guided Clarify Flow (`src/components/ClarifyModal.tsx`)**:
  - One-item-at-a-time decision tree modal.
  - Non-actionable branch: Trash, Someday/Maybe, and Reference.
  - Actionable branch: 2-Minute Rule with interactive countdown timer and instant completion.
  - Delegation branch: "Waiting For" with person assignment and timestamp.
  - Multi-step outcome branch: Project creator with Sequential/Parallel/Single-Action list options and mandatory first next physical action definition.
  - Next Action branch: Assign to project, defer date ("available from"), energy level, and time estimates with verb-first action nudges.
- **Inbox Dashboard (`src/components/InboxView.tsx`)**:
  - Real-time inbox count, item triage, and "Process Inbox" trigger.
  - Celebrating Inbox Zero state.
- **Color Palette & Visual Identity (Red, Blue, Teal)**:
  - Transformed the interface with vibrant semantic colors:
    - **Teal**: Next Actions, availability status, active filters, quick capture CTAs, and brand energy.
    - **Cobalt Blue**: Projects structure, sequential workflow tags, active navigation, and delegation.
    - **Coral / Red**: Inbox attention loops, overdue review/stalled project warnings, and priority flags.
  - Enhanced KPI summary cards in ProjectsView with distinct blue, red, and teal gradients and icons.
  - Updated Clarify modal decision tree with high-contrast color routing (Teal for Actionable & 2-Minute Rule, Blue for Delegation, Red for Trash).
- **Next Actions View & Deadline Engine (`src/components/NextActionsView.tsx`)**:
  - Implemented dynamic deadline evaluation for hard landscape due dates:
    - **Within 24 Hours**: Small glowing/pulsing visual indicator (`Due in Xh` with animate-ping dot) in coral red.
    - **Upcoming Deadlines (>24h)**: Clean calendar date badge in blue/slate (`Due [Day, Mon DD]`).
    - **Overdue Deadlines**: High-contrast warning alert badge.
  - Added deadline quick-filter tabs: `All`, `Due ≤ 24h (Count)`, and `Upcoming (Count)`.
  - Added inline due date editor (`+ Due Date` / `Edit Due`) on every action row with native calendar picker and clear affordance.
  - Updated Quick Capture modal and store with optional `dueDate` support.
- **Projects Management View (`src/components/ProjectsView.tsx`)**:
  - Added summary KPI row displaying total active projects, stalled projects (projects lacking an incomplete next action), and total actions (remaining vs completed).
  - Added visual "Stalled (No next action)" indicator on stalled project headers to enforce GTD next-action discipline.
  - Sequential vs Parallel project indicators.
  - Inline next action creation.
- **Next Actions View & Context Engine (`src/components/NextActionsView.tsx`)**:
  - Extended the task model (`Item`) with a first-class `context` field (e.g. `@home`, `@office`, `@phone`, `@computer`, `@errands`, `@anywhere`).
  - Added multi-mode grouping switcher:
    - **By Context**: Groups available next actions into distinct context cards with dedicated icons, badge counts, and themed color schemes (Teal for `@home`, Blue for `@office`, Coral for `@phone`, Cyan for `@computer`, Purple for `@errands`).
    - **By Project**: Groups actions by enclosing project hierarchy with progress counts.
    - **Flat List**: Clean, dense list view with flagged prioritization.
  - Implemented interactive Context Filter bar with real-time per-context task counts.
  - Added inline Context assignment popover directly on each task row to switch, assign, create custom contexts, or remove contexts with zero navigation friction.
  - Added context selector in the guided Clarify modal and auto-detection of `@context` tags in Quick Capture.
- **Universal Search Bar (`src/components/SearchBar.tsx`)**:
  - Filter tasks, projects, notes, and contexts across all views with live cross-view match count badges and direct jump buttons.

## [0.1.0] - Phase 0: System Architecture & Data Model Baseline

### Added
- **System Architecture & Stack Blueprint**: Evaluated Python/PyQt6 Desktop vs. Local-First TypeScript/React Web architectures; published ADR-001 through ADR-006 in `DECISIONS.md`.
- **Unified Data Model**: Designed full Entity-Relationship model and SQL DDL schemas for:
  - `items`: Unified table supporting Folders, Projects (Sequential, Parallel, Single-Action List), Actions, and Sub-actions with rank ordering and hierarchical lineage.
  - `tags`: Hierarchical tagging system representing places, tools, people, energy levels, and time slots.
  - `item_tags`: Normalized many-to-many relationship mapping items to multiple contexts.
  - `repeat_rules`: Comprehensive recurrence rules (fixed schedule vs. repeat-from-completion).
  - `perspectives`: Serializable query and grouping specifications for custom power-user views.
  - `review_records`: Audit log for weekly reviews and project-level review checkpoints.
  - `item_attachments`: Support for rich markdown attachments, reference links, and external URI citations.
  - `horizon_notes`: First-class GTD Horizons of Focus (Runway, Projects, Areas of Focus, 1-2y Goals, 3-5y Vision, Purpose & Principles).
- **TypeScript Type System Baseline**: Created strict TypeScript definitions in `src/types/gtd.ts` encapsulating all GTD workflows, statuses, availability criteria, and filter configurations.
- **Phase 0 Interactive Architecture & Schema Explorer**: Built an interactive UI in `src/App.tsx` displaying the complete database specification, ER diagrams, SQL DDL, stack comparison, GTD workflow matrix, and initial review questions.
