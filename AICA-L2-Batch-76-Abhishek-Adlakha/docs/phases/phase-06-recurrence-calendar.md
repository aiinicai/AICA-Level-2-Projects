# Phase 6 — Recurrence engine and calendar

## Outcome

Phase 6 converts confirmed client-service agreements into dated tasks through versioned recurrence rules. The generator is idempotent: each rule version and period has a stable occurrence key, the database enforces uniqueness, and a PostgreSQL advisory lock prevents parallel workers from racing. Manual tasks remain unchanged.

The calendar is a permission-scoped task read model rather than a second source of truth. Windows and macOS employees use the same browser application over the office LAN. Local Mac development runs the worker in Docker; native Windows Server 2019 production runs the published worker from Windows Task Scheduler without Docker or Hyper-V.

## Scheduling policy

- Firm-local dates use `Asia/Kolkata`.
- Sunday is non-working.
- Saturday remains working until the firm confirms a different policy (BIZ-006).
- Administrators enter holidays and explicit working-day overrides in the firm calendar.
- A due date can remain unchanged, move to the previous business day, or move to the next business day.
- No unverified statutory calendar or guessed GST/compliance due-date library is seeded.

The confirmed test rule is monthly GST: July 2026 period, nominal due date 20 August 2026, next-business-day adjustment, and a 21-day generation lead. If 20 August is configured as a holiday, it moves to 21 August.

## Database and safety

Forward-only migration `20260820163325_AddRecurringSchedulingAndCalendar` adds the `scheduling` schema with recurrence rules, selected custom months, period exceptions, generator runs and generator run items. It also adds nullable recurrence links and a filtered unique occurrence key to tasks.

Rule edits create a replacement version with a later effective date; historical tasks continue to reference the version that produced them. System-generated tasks allow a null human actor while user-driven changes still record the authenticated user. Inactive clients, services, agreements and rules are excluded by the generator.

## API and permissions

Phase 6 adds scoped `scheduling.view`, scoped `scheduling.manage`, `scheduling.generate`, scoped `calendar.view`, and `scheduling.holidays.manage` permissions. Administrators receive all five; other roles remain administrator-configured.

Endpoints provide schedule masters/list/create/version/deactivate, a no-write preview, manual generation, generator health, holiday maintenance and a 93-day bounded calendar query. Calendar and scheduling agreement queries apply OWN/TEAM/ALL server-side scope rules.

## Worker and deployment

The rolling worker looks back 30 days for catch-up and forward 45 days. It executes on startup and every six hours. Run records retain created, already-existing, skipped and error counts. Docker Compose includes the worker for Mac development. The Windows installer publishes the same executable and registers a non-overlapping SYSTEM scheduled task.

## User interface

The Calendar workspace includes a responsive month grid, active rule list, generator health, manual generation, holiday entry and recurrence creation with a full-year preview. The preview makes period, nominal due date, adjusted due date and generation lead visible before activation.

## Verification

- Release build with warnings treated as errors;
- model checks for the scheduling schema, version concurrency, active-version uniqueness and occurrence uniqueness;
- monthly GST, holiday roll-forward, Sunday, Saturday and leap-month due-date tests;
- repeat generation and advisory-lock safety through database constraints/run records;
- inactive client/service/agreement filtering;
- React lint, tests and production build;
- forward migration, second idempotent migration, and live API/worker health checks.

## Deferred

Phase 6 does not add notifications, email/WhatsApp, external calendars, invoice generation or a general statutory rule language. Only rules confirmed by the firm should be entered. Billing entity and fixed-fee configuration begin in Phase 7.
