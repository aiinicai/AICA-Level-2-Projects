# Phase 5 — Task lifecycle and assignments

## Outcome

Phase 5 adds actual, dated work items without confusing them with reusable services or future recurrence rules. Managers can create manual tasks from active client-service agreements, assign accountable employees, and monitor permitted work. Employees can update tasks within their OWN/TEAM/ALL permission scope. Every status change and reassignment preserves history.

The production target remains native Windows Server 2019 with IIS, .NET 10 and PostgreSQL. Windows and macOS staff use the same browser application across the office LAN.

## Database

Forward-only migration `20260820154226_AddTaskLifecycleAndAssignments` adds the `tasks` schema and:

- five protected statuses: Not Started, In Process, On Hold, Completed and Cancelled;
- eleven explicit allowed transitions with permission, reason and completion-note rules;
- manual work items linked to the client, service, optional client-service agreement and optional GSTIN;
- append-preserving primary, secondary and reviewer assignments;
- append-only task status history and non-destructive comments;
- row-version optimistic concurrency and task-number generation;
- two task permissions and seven configurable task field policies;
- least-privilege runtime grants for `practice_app`.

Constraints protect client/service agreement consistency, cross-client GSTIN references, dates, priority values, terminal metadata and one current primary assignment. Transaction rows are never physically deleted.

## Workflow

Normal progress supports Not Started → In Process/On Hold/Completed, In Process → On Hold/Completed, and On Hold → In Process. Any open state may be cancelled with a mandatory reason.

BIZ-007 uses the documented recommended default: reopening Completed → In Process or restoring Cancelled → Not Started requires the explicit `tasks.reopen` permission and a mandatory reason. The current status and an append-only history row are saved atomically.

Completion requires a completion note and records the completing user/time. Cancellation records the cancelling user/time and reason. Reopen clears the current terminal marker while retaining the original timeline and increments the reopen count.

## API and access control

Phase 5 activates `tasks.view`, `tasks.create`, `tasks.assign`, and `tasks.change_status`, and adds `tasks.reopen` and `tasks.comment`.

- OWN includes tasks currently assigned to the employee.
- TEAM includes current work assigned to accessible team members and direct reports.
- ALL includes firm-wide tasks.
- Direct task IDs, assignment targets, status commands and comments repeat the server-side scope check.
- Unassigned tasks are visible only at ALL scope until assigned.
- Mutations require the last observed row version; a stale request returns `409 Conflict` rather than overwriting another employee's change.

Endpoints provide filtered task lists, masters, task detail/timeline, task creation, assignment/reassignment, unassignment, status transitions and comments.

## User interface

The Tasks workspace provides:

- My Tasks, Team Tasks and All Tasks according to the user's maximum scope;
- status and text filters with stable pagination;
- task creation from an active client-service agreement;
- due date, period, priority, GSTIN scope, billable snapshot and assignees;
- primary reassignment without overwriting the earlier assignment row;
- only currently allowed and permissioned status actions;
- assignment, status and comment timelines in task detail.

Administrators can decide whether optional task fields, including primary assignee and client-service agreement, are mandatory. System-required client, service, title and due-date invariants cannot be disabled.

## Verification

- clean Release build and production React bundle;
- database model, architecture, identity and workbook checks;
- forward migration and safe second application;
- exact status/transition seeds and runtime grants;
- one-current-primary constraint and append-only history guard;
- manager create/assign flow and employee-scoped transition flow;
- cancellation, completion and reopen reason/data rules;
- stale row-version rejection and retained assignment/status timeline;
- rollback-only database acceptance transaction so no test work remains.

## Deferred

Phase 5 does not create recurrence rules, automatic work generation, holiday adjustment, calendar grids, task monetary amounts, billing entities, billing schedules or invoices. Recurrence and calendar begin in Phase 6; billing remains in Phases 7–8.
