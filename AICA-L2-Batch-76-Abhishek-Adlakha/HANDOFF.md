# Project Handoff — CA Firm Practice Management

Last inspected: 2026-08-21 (Asia/Kolkata)  
Repository state inspected: branch `main`, Phase 10 in progress  
Implemented phase: **Phase 10 of 12 (complete)**  
Next planned phase: **Phase 11 — production release, workbook import and Windows commissioning**

Phase 10 delivered: the diagnostics endpoint is authorized; `audit.view` is a real permission with
a query API and workspace; failed logins, lockouts, session revocation, exports, generation runs
and holiday changes are audited; CSRF is genuinely enforced for JSON mutations; CSP and the
remaining security headers are set on both hosting paths; error responses carry a support
reference; the administration workspace no longer fails for non-administrators; and a
PostgreSQL-backed API integration suite covers anonymous denial, authorised reads, antiforgery and
OWN/TEAM/ALL record scope across every scoped module.

That suite exposed several defects that had shipped in Phase 9 and one inconsistency in the
security boundary; see section 7. Two items were deliberately deferred rather than rushed and are
listed in section 14.

This document describes the repository as it exists, not only the aspirational architecture in `docs/architecture-blueprint.md`. Where the blueprint and implementation differ, this document calls out the difference. No credentials or connection-string values are included.

## 1. PROJECT OVERVIEW

### Purpose

This is a centralized practice-management web application for a single Chartered Accountant firm. It replaces spreadsheet-shaped client/service/task/billing data with a relational system that supports controlled work allocation, recurring compliance work, expected-fee projection, and permission-scoped reporting.

The central business model is:

`Client -> GST registrations / contacts / addresses / groups -> Client service agreement -> recurrence rule and billing term -> generated/manual tasks -> employee assignments`

A reusable service definition is deliberately separate from a client's agreement for that service, and both are separate from the actual tasks. A billing term belongs to a client-service agreement and references a legal billing entity.

### Intended users

- The system administrator, initially Abhishek Adlakha.
- Managers.
- Articles.
- Paid Assistants.
- Accountants.
- Client Accountants.
- Future administrator-created roles with configurable permissions.

Staff use a browser. They do not install a desktop client or local database. macOS and Windows are both supported as browser clients across the office LAN.

### Main business functionality

- Employee login by normalized 10-digit Indian mobile number.
- Employee, role, permission, and mandatory-field administration.
- Client registry with legal/tax details, contacts, addresses, multiple GSTINs, and client groups.
- Reusable service catalogue and client-specific service agreements.
- Manual and recurring tasks, assignments, workflow transitions, comments, and history.
- Holiday-aware recurrence rules, preview, generation runs, and calendar views.
- Legal billing entities and effective-dated fixed-fee terms/schedules.
- Deterministic expected-fee projections and CSV/XLSX exports.
- Permission-scoped dashboard, client register, task register, and projection reports.
- Read-only profiling and dry-run analysis of the source workbook `Clients List.xlsm`.

Invoices, receivables, payments, tax calculation, revenue recognition, document management, client portals, notifications, external integrations, advanced analytics, and AI features are not implemented.

## 2. CURRENT ARCHITECTURE

### Architectural style

The application is a modular monolith in one repository:

- One React browser application.
- One ASP.NET Core API host.
- One separately runnable background worker built from the same codebase.
- One PostgreSQL database divided into logical schemas.
- One separate migrator executable and one local administrator CLI.

The implementation is organized into projects rather than a single `src/Modules` tree. Some older architecture prose refers to a future `src/Modules` layout; that directory structure was not adopted.

### Frontend

- React 19.2 and React DOM 19.2.
- Strict TypeScript 5.9.
- Vite 7.2.
- Node.js 24 or newer and pnpm 11.19.
- No React Router, query library, form library, schema-validation library, or component library is currently installed, despite those being discussed in the original blueprint.
- The UI is presently a single-page application whose types, fetch helpers, navigation, and workspaces are concentrated in `web/src/app/App.tsx`.
- `web/src/app/styles.css` contains the application styling.
- Navigation is permission-aware, but UI permission checks are convenience only; the API is intended to be authoritative.
- Vite proxies `/api` and `/health` to a directly run API on port 5080.
- In Compose, Nginx serves the built SPA and proxies API/health calls to the API container.
- In native Windows production, the compiled React assets are copied into the API's `wwwroot` and served by ASP.NET Core under IIS.

### Backend

- .NET 10 / ASP.NET Core 10 Minimal APIs.
- Nullable reference types enabled.
- Latest recommended analyzers enabled and warnings treated as errors.
- REST/JSON endpoints under `/api/v1`.
- Endpoint modules live under `src/Practice.Api/{Identity,Clients,Services,Tasks,Scheduling,Billing,Reporting}`.
- `src/Practice.Api/Program.cs` is the composition root for middleware, authentication, authorization policies, health checks, static assets, and endpoint registration.
- OpenAPI is mentioned in the blueprint but is **not configured in the current API**.
- Errors use ASP.NET Core Problem Details/exception handling, while the web client often reduces them to `Request failed (<status>)`.

### Database

- PostgreSQL 18.
- EF Core 10.0.10 with Npgsql EF provider 10.0.3.
- One `AppDbContext` and one database with 11 logical schemas.
- Eight version-controlled migrations are present and applied in the inspected local database.
- The API never migrates at startup. `Practice.Migrator` runs migrations as an explicit deployment step.
- Separate fixed database roles are used for migrations and application runtime. The runtime role cannot alter the schema and has only select/insert access to audit events.

### Authentication

- Same-origin ASP.NET Core encrypted cookie authentication.
- Passwords are hashed using ASP.NET Core's `PasswordHasher<LoginUser>`.
- The browser login identifier is a normalized 10-digit Indian mobile number beginning with 6, 7, 8, or 9.
- A random session token is placed inside the encrypted cookie; only its SHA-256 hash is stored in `identity.user_sessions`.
- Sessions expire after 12 hours and do not slide.
- Session validity, account state, security stamp, current roles, and current permissions are reloaded from PostgreSQL on every authenticated request.
- Password changes, account changes, and role-permission changes revoke affected sessions.
- Temporary employee passwords require a password change before business endpoints can be used.

### Authorization / RBAC

- Stable action permissions are assigned to roles.
- Permissions that support record scope use `OWN`, `TEAM`, or `ALL` ceilings.
- Multiple roles are merged to the widest granted scope (`ALL > TEAM > OWN`) for each permission.
- ASP.NET authorization policies enforce action permissions.
- EF query filters and record checks enforce client, agreement, task, billing, scheduling, projection, and report scope server-side.
- Frontend visibility is not relied upon as a security boundary.

### Major modules and projects

| Project/module | Responsibility |
|---|---|
| `Practice.Api` | HTTP host, middleware, endpoint DTOs, API authorization, static SPA hosting |
| `Practice.Database` | EF entities, model configuration, seeds, migrations, audit persistence |
| `Practice.Identity` | credential rules, login/session handling, bootstrap and local recovery |
| `Practice.Scheduling` | recurrence calculation and idempotent task generation |
| `Practice.Billing` | billing schedule validation and deterministic projection calculation |
| `Practice.Reporting` | metric/date rules and safe CSV/XLSX generation |
| `Practice.BuildingBlocks` | clock and auditing abstractions |
| `Practice.Worker` | recurring task-generation host |
| `Practice.Migrator` | one-shot EF migration executable |
| `Practice.AdminCli` | first-admin bootstrap and local password recovery |
| `Practice.WorkbookProfiler` | read-only XLSX/XLSM profiler plus client/service dry-run analysis |

### Component interaction

1. The browser requests the SPA and `/api/v1` endpoints from one origin.
2. Nginx (local Compose) or IIS/ASP.NET Core (Windows production) serves assets and routes API traffic.
3. Cookie authentication validates the server-side session and reloads RBAC claims.
4. Endpoint code validates input, applies permission and record scope, and uses `AppDbContext`.
5. Business changes and their audit records are saved in the same EF transaction where implemented.
6. The worker obtains a PostgreSQL advisory lock, calculates bounded recurrence occurrences, and creates tasks idempotently.
7. Reporting and projections read normalized transactional data on demand; projection rows are not persisted.

## 3. DATABASE

### Technology and conventions

- PostgreSQL 18, EF Core migrations, Npgsql provider.
- Schema history table: `system.ef_migrations_history`.
- Database names are `snake_case`; EF entity/property names are C# PascalCase.
- UUID primary keys are used for most entities; task numbers and import issue IDs use database-generated numeric values where configured.
- `timestamptz`/`DateTimeOffset` represents instants; `date`/`DateOnly` represents business dates.
- Money is `numeric(19,2)` and currency uses three-letter codes.
- Structured audit/import metadata uses `jsonb`.
- Foreign keys generally use restrictive delete behavior. Cascades are limited to true owned children/join data.
- Important normalized codes and identifiers have unique/partial indexes and database check constraints.
- Clients and masters are deactivated rather than deleted; historical task/billing/audit records are retained.
- Tasks, recurrence rules, and billing entities use optimistic concurrency row versions.
- Audit events and task status history are guarded as append-only by `AppDbContext`. Audit update/delete is also denied to the runtime DB role; task-history immutability currently depends on application code because the runtime role has broader DML on the `tasks` schema.

### Current physical schema: 47 EF entities

| Schema | Tables | Important purpose/fields |
|---|---|---|
| `reference` | `india_states` | GST state code, name, union-territory and active flags |
| `system` | `app_settings`, `holiday_calendars`, `holidays`, `outbox_messages`, `field_definitions` | Firm time zone/financial-year settings, working-day overrides, future outbox storage, configurable required fields |
| `audit` | `audit_events` | Occurrence time, actor, action, entity type/id, reason, correlation ID, allow-listed JSON data |
| `import` | `import_runs`, `import_issues`, `client_import_mappings`, `client_import_results`, `service_import_proposals`, `billing_import_proposals` | Source hash/run status, reconciliation issues, mappings, proposals, import outcomes |
| `identity` | `users`, `user_sessions`, `roles`, `permissions`, `user_roles`, `role_permissions` | Mobile login, hashed password, lockout/security stamp, session hash/revocation, RBAC and scope ceilings |
| `employees` | `employees`, `teams`, `team_memberships` | Employee identity, optional user link, manager relationship, team ownership, effective membership |
| `clients` | `client_categories`, `clients`, `client_contacts`, `client_addresses`, `gst_registrations`, `client_groups`, `client_group_memberships` | Legal/client identity, lifecycle status, tax identifiers, child details, multiple GSTINs and effective group membership |
| `services` | `service_categories`, `services`, `client_services` | Service catalogue and effective client/GSTIN-specific agreements, responsible team and defaults |
| `tasks` | `task_statuses`, `task_status_transitions`, `tasks`, `task_assignments`, `task_status_history`, `task_comments` | Work lifecycle, assignment roles/history, status timeline, comments, occurrence keys and concurrency |
| `scheduling` | `recurrence_rules`, `recurrence_rule_months`, `recurrence_exceptions`, `generation_runs`, `generation_run_items` | Versioned recurrence/due-date rules, custom months, skip/override exceptions and generator evidence |
| `billing` | `billing_entities`, `billing_terms`, `billing_schedules`, `billing_schedule_months` | Legal invoicing entity, effective fee versions, independent billing schedules and selected months |

### Important relationships and integrity rules

- A `LoginUser` may have one linked `Employee`; the employee may exist without a login.
- Employees have an optional self-referencing manager and effective-dated team memberships.
- A client has zero-to-many contacts, addresses, GST registrations, and group memberships.
- At most one active primary GSTIN exists per client. GSTIN is unique across clients and checksum/state-prefix validated by the API.
- Clients can belong to multiple groups, with at most one current `PRIMARY` membership for non-duplicating totals.
- `ClientService` joins a client and service and may target one of that client's GST registrations. Separate uniqueness rules prevent duplicate active client-wide or GSTIN-scoped agreements.
- A client service may have one active recurrence-rule version and multiple historical versions/exceptions.
- Generated tasks carry an immutable occurrence key; a unique partial index prevents duplicate generated work.
- Tasks retain current status plus append-only status history. Current assignments are effective records; at most one current primary assignee is allowed.
- Billing terms are effective-dated versions per client service. Fixed-fee billable terms require amount/entity/schedule; non-billable terms do not.
- Task recurrence and billing schedules are intentionally independent.
- Billing projection applies terms/schedules on demand. It does not create invoice or ledger records.

### Migrations

Migrations are in `src/Practice.Database/Migrations`:

1. `20260819193112_InitialFoundation`
2. `20260820113450_AddIdentityAccessAndFieldPolicies`
3. `20260820143034_AddClientRegistryAndImportStaging`
4. `20260820145554_AddServiceCatalogueAndClientAgreements`
5. `20260820154226_AddTaskLifecycleAndAssignments`
6. `20260820163325_AddRecurringSchedulingAndCalendar`
7. `20260820173917_AddBillingEntitiesAndEffectiveDatedTerms`
8. `20260820181042_AddBillingProjectionPermission`

Phase 9 reporting and Phase 10 audit needed no schema migration; `audit.view` was already seeded. Do not edit a released migration; add a corrective migration and update `AppDbContextModelSnapshot.cs` through EF tooling.

### Seed data

- 36 India states/union territories.
- Two app settings: Asia/Kolkata organization time zone and 1 April financial-year start.
- One default India holiday calendar; actual holidays are not pre-populated.
- Six default roles.
- 34 permission definitions.
- All 34 permissions at `ALL` scope for the protected Administrators role.
- The five non-administrator default roles are created without default grants; an administrator must configure them.
- 42 registered mandatory-field definitions covering employees, clients, client services, tasks, billing entities, and billing terms.
- 11 legal client categories. The ambiguous workbook category `Firm` is deliberately not seeded.
- Five service categories and 21 approved service definitions.
- Five task statuses and 11 allowed status transitions.
- No legal billing entity is seeded; it must be confirmed by the business owner.
- No default user/mobile/password is seeded. The first administrator is created locally by CLI.

### Current local database state

At inspection time, the Docker development database was healthy and had all eight migrations applied. Aggregate counts were: 2 users, 2 employees, 1 client, 1 client-service agreement, 0 tasks, 0 billing entities, 0 billing terms, and 21 audit events. These records are in the Docker named volume, not in Git, and can change independently of this document.

## 4. USER MANAGEMENT AND RBAC

### Authentication behavior

- Login endpoint: `POST /api/v1/auth/login`.
- Session endpoints include CSRF token, bootstrap status, current user, logout, and password change.
- Password length is 12–128 characters; common passwords and a password containing the login mobile number are rejected.
- Five failed logins cause a 15-minute lockout.
- Login is rate limited to 10 requests per minute per observed IP.
- Authentication failure is generic and a missing user still performs password-hashing work to reduce enumeration/timing differences.
- Session cookie names are development-specific locally and `__Host-` prefixed in production. Cookies are HttpOnly, SameSite Strict, Secure in production, non-persistent, and non-sliding.
- CSRF uses an HttpOnly antiforgery cookie plus `X-CSRF-TOKEN`; all implemented mutations opt into antiforgery validation.

### Roles

Seeded roles are exactly:

- Administrators (protected)
- Manager
- Articles
- Paid Assistants
- Accountants
- Client Accountants

Administrators can create additional roles and replace the permission set of non-protected roles. The protected Administrators role cannot have its permissions reduced through the API.

### Permissions

There are 34 seeded permissions across identity, employees, system, audit, clients, services, tasks, scheduling/calendar, billing, and reporting. Examples include `clients.view`, `tasks.assign`, `billing.project`, `reports.export`, and `settings.field_policies.manage`.

The exact codes are:

- Identity/system: `identity.users.view`, `identity.users.manage`, `identity.roles.view`, `identity.roles.manage`, `settings.field_policies.manage`, `system.diagnostics.view`, `audit.view`.
- Employees/teams: `employees.view`, `employees.manage`, `teams.manage`.
- Clients: `clients.view`, `clients.create`, `clients.edit`, `clients.deactivate`.
- Services: `services.view`, `services.catalogue.manage`, `services.enrollments.view`, `services.enrollments.manage`.
- Tasks: `tasks.view`, `tasks.create`, `tasks.assign`, `tasks.change_status`, `tasks.reopen`, `tasks.comment`.
- Scheduling/calendar: `scheduling.view`, `scheduling.manage`, `scheduling.generate`, `calendar.view`, `scheduling.holidays.manage`.
- Billing/reporting: `billing.view`, `billing.configure`, `billing.project`, `reports.view`, `reports.export`.

The permission seed marks employee/team, client record, service-enrollment, task record, scheduling/calendar, billing, and reporting permissions as scope-capable where applicable. Global catalogue/settings/identity operations do not derive row scope. `tasks.create` is unscoped in the permission seed, but the endpoint additionally constrains non-ALL creators through an accessible client-service/responsible-team check.

`audit.view` is seeded without scope support, so it is deliberately unscoped: a holder sees every recorded event. It now has a `PermissionCodes.AuditView` constant, a registered policy, read-only query endpoints and an administrator workspace.

### Scope enforcement

- Scope ceilings are stored in `identity.role_permissions`.
- Action policy checks occur via `RequireAuthorization(...)` on endpoint mappings.
- OWN task scope means current assignment to the signed-in employee.
- TEAM scope uses manager/direct-report and effective team-membership relationships.
- Client/agreement/billing scope is derived from the responsible team on client-service agreements.
- Report exports apply the intersection of `reports.view` and `reports.export`; they cannot widen on-screen visibility.
- Projection used inside reports additionally intersects `billing.project`.

Scope query logic is duplicated across several endpoint files and is security-sensitive. Do not casually consolidate or alter it without comparison tests for every module and direct-ID denial path.

### Administrator functionality actually exposed

Backend APIs support:

- Listing and creating employees/logins.
- Enabling/disabling users with last-administrator and self-disable protections.
- Listing/creating roles and configuring role permissions/scopes.
- Listing/updating field policies.
- Listing/creating teams.

Current UI supports:

- Listing and creating employee logins (one role selected at creation).
- Listing/creating roles and editing non-protected permission assignments.
- Toggling registered mandatory fields that are not system-required.

Current UI does **not** expose user enable/disable, employee editing, post-creation user-role assignment, team creation/membership administration, or multiple-role selection during employee creation.

### First administrator and recovery

- Abhishek Adlakha is the intended first administrator.
- `Practice.AdminCli bootstrap-admin` creates the first user only when no user exists and reads the password without echo.
- `Practice.AdminCli reset-password` is the local recovery path. It reads the new password without echo, clears lockout, rotates the security stamp, revokes sessions, and audits the reset.
- Never put a real password or mobile number in source, documentation, chat, `.env`, or ordinary command-line arguments.

## 5. COMPLETED FEATURES

The following are implemented in current code, not merely planned:

### Foundation and operations

- Modular .NET solution and React build with cross-platform wrapper scripts.
- Docker Compose development stack with PostgreSQL, migrator, API, worker, Nginx web, and optional admin CLI profile.
- Liveness/readiness endpoints and JSON console logging.
- Separate migrator/runtime database roles and explicit migration execution.
- Cross-platform database backup and isolated restore-verification scripts.
- Native Windows Server 2019 release packaging and installation baseline.

### Identity and administration

- Mobile-number login, hashed passwords, server-revocable sessions, lockout, password change, logout, and local password recovery.
- First-administrator one-time bootstrap.
- Six seeded roles, administrator-created roles, 34 permissions, and scoped permission editing.
- Session invalidation after account/password/role-permission changes.
- Employee creation and account status backend operations.
- Configurable mandatory-field policies with locked system invariants.
- Audit events for successful login, password/admin changes, and most business mutations.

### Client registry

- Searchable, paginated client list with active/inactive filtering and permission scope.
- Client detail, creation, update, deactivate/reactivate.
- PAN/TAN format checks and GSTIN checksum/state/uniqueness checks.
- Contacts, addresses, multiple GST registrations, client groups, and effective memberships.
- Client-category and group master data.
- UI creation supports zero, one, or two GSTINs; API/domain model supports arbitrary collections.

### Services and client agreements

- Seeded service catalogue plus category/service create/update/status APIs.
- Effective-dated client-service agreements, optionally scoped to one GSTIN and one responsible team.
- Agreement list/detail/create/update/deactivate/reactivate with server-side scope.
- UI catalogue/agreement list, create service, create agreement, and status controls.

### Tasks

- Paginated My/Team/All task views subject to scope ceiling.
- Manual task creation from an active client-service agreement.
- Primary/secondary assignment at creation and primary reassignment in the UI.
- Backend assignment roles: PRIMARY, SECONDARY, REVIEWER; assignment and unassignment history.
- Controlled status-transition graph with mandatory completion notes/reopen/cancellation reasons where configured.
- Optimistic concurrency on mutations.
- Status history, assignment history, comments, and audit events.
- Task detail UI with workflow actions, primary assignment, comment form, and timelines.

### Scheduling and calendar

- Monthly, quarterly, half-yearly, yearly, and custom-month recurrence calculation.
- Fixed due-day/month offsets, lead days, last-day clipping, leap-year handling, and previous/next business-day adjustment.
- Sunday non-working and Saturday working until the firm confirms another policy.
- Versioned recurrence rules and skip/override exceptions.
- Holiday calendar and firm holiday/working-day override records.
- Preview endpoint and UI.
- Manual generation and six-hour worker generation.
- PostgreSQL advisory lock, persisted run/item evidence, deterministic occurrence keys, and unique-index idempotency.
- Calendar month UI and recent generation-run status.

### Billing and projection

- Legal billing entity CRUD/status backend and create/status UI.
- Effective-dated fixed-fee or non-billable terms per client-service agreement.
- Term replacement preserves prior versions.
- Monthly, quarterly, half-yearly, annual, selected-month, custom-month, and one-time billing schedules.
- Task recurrence and billing schedules remain independent.
- On-demand expected-fee projection by month, calendar quarter, Indian financial year, client, primary group, billing entity, service, responsible team, and manager.
- Currency-separated totals, explanation rows, scoped calculation, and CSV/XLSX export.
- No projection persistence, by design.

### Dashboard and reports (Phase 9)

- Operational dashboard cards for client state/GSTIN coverage and due/overdue/in-process/completed/cancelled task metrics.
- Current primary-assignee workload breakdown.
- Current-month projected fee totals when the user also has `billing.project`.
- Card drill-down to matching client/task records.
- Client report with status/category/group/GSTIN filters and summaries.
- Task report with bucket/status/date/employee/client/service/billable filters and summaries.
- Billing projection presented as the third core report family.
- Server pagination, bounded date windows, maximum 10,000-row exports, CSV formula-injection defense, and valid in-memory Open XML XLSX output.

### Audit, security and testing (Phase 10, in progress)

- Diagnostics endpoint requires `system.diagnostics.view`.
- `audit.view` policy, read-only audit search/filter API, and a permission-gated audit workspace.
- Failed logins, automatic lockouts and session revocation recorded in the audit trail, without
  ever recording the submitted password.
- Antiforgery genuinely enforced for JSON mutations.
- PostgreSQL-backed API integration suite wired into `verify`.

### Workbook tooling

- Read-only `.xlsx`/`.xlsm` profiling without macro execution.
- Source SHA-256, sheet/column observations, duplicates, and optional employee-reference matching.
- Client and service dry-run proposal/exception analysis.
- Tests verify that profiling/dry-run does not alter the source workbook.

## 6. PARTIALLY COMPLETED FEATURES

### Audit and operational administration

Audit storage, an unscoped search API and an administrator workspace exist. Recorded actions now
include login, failed login, lockout, session revocation, password and account changes, business
mutations, report exports, manual generation runs and holiday changes. Audit retention is implemented: routine history is kept three months and security history twelve,
with expired rows archived to a file before deletion. An administrator health screen shows
database, generation and retention status. Still outstanding: alerting when a generation run
fails, and off-server rotation of the archive files.

### Security hardening

CSRF is genuinely enforced for JSON mutations; CSP, Permissions-Policy and cross-origin isolation
headers are set at Nginx and in the API; exports are audited; error responses carry a trace
reference; and integration tests cover anonymous denial, antiforgery rejection and OWN/TEAM/ALL
scope. Outstanding: forwarded-header and host-filtering review for the real proxy, log secret
scanning, dependency and supply-chain scanning in CI, rate limiting beyond login, and a broader
OWASP-focused validation pass.

### Employee/team administration

Tables and basic team list/create APIs exist, but team membership management and most employee editing are absent. The UI exposes a narrower subset than the API. Roles cannot currently be reassigned to an existing employee through a dedicated endpoint/UI.

### Client/service/billing editing UX

- Client update exists, but the UI edits only display/legal names through browser prompts and resubmits the rest unchanged.
- Service and client-service update APIs exist, but the UI exposes create/status rather than full edit forms.
- Billing entity update exists in the API but has no UI edit form.
- Full arbitrary child-record maintenance for contacts, addresses, GSTINs, and group memberships is not a polished UI workflow.

### Task UX

The backend supports secondary/reviewer assignment and unassignment, but the UI mainly replaces the primary assignee. Comment fields model editing/redaction, but only comment creation is exposed. There is no general task-edit endpoint/UI after creation.

### Scheduling UX

Backend rule versioning, deactivation, exception list/add, and holiday maintenance exist. The UI exposes rule creation/preview, manual generation, simple holiday addition, calendar, and run summaries, but not full rule-version/deactivation/exception administration.

### Data migration

Workbook profiling, dry-run services, staging tables, and exception models exist. There is no approved production importer/cutover execution. Employee-name mappings, ambiguous `Firm`, legal billing entities, and the workbook value `Cash` still require owner decisions and reconciliation.

### Outbox

`system.outbox_messages` exists as a foundation table, but no producer/consumer processing pipeline is implemented.

### Windows production

Release and installation scripts are present, but the application has not completed Phase 11 commissioning on the real Windows Server 2019 host. Certificate/DNS validation, Windows service recovery behavior, signed package/checksum approval, update/rollback rehearsal, off-server backup/restore drill, performance checks, UAT, and administrator training remain outstanding.

### Testing infrastructure

Core rule checks exist, and `tests/Practice.Api.IntegrationTests` now boots the real API with
`WebApplicationFactory` against a disposable PostgreSQL database. The repository still does not use
xUnit, Testcontainers, browser component tests, or Playwright end-to-end tests. The integration
suite covers anonymous denial and authorised reads; per-scope OWN/TEAM/ALL assertions and
mutation-path coverage are not written yet.

## 7. KNOWN BUGS / LIMITATIONS

### Fixed in Phase 10: diagnostics endpoint was public

`GET /api/v1/system/diagnostics` was mapped without authentication even though `system.diagnostics.view` was seeded and its policy registered; the mapping simply never called `RequireAuthorization`. It now requires that permission. An architecture check and the API integration suite both assert anonymous access is denied. The generic system-info and health endpoints remain intentionally public.

### Fixed in Phase 10: administration workspace failed for non-administrators

`AdminWorkspace` loaded roles, permissions, employees and field policies on mount for every
session, so a user lacking one of those permissions saw `Request failed (403)` over empty panels,
and the Administration entry was offered to everyone. The entry is now hidden unless the session
can read something there, the fetch runs only when the view is opened, and each request is issued
only if its permission is present. Reproduced and confirmed fixed in a browser.

### Compose credential rotation trap can cause 502 responses

The PostgreSQL init script creates the runtime login only when a new database volume is initialized. Changing local `.env` database passwords later does not update roles inside an existing PostgreSQL volume. The API can then fail to connect, while Nginx reports `Request failed (502)`. Synchronize the database-role passwords with the controlled `.env` values, or restore the prior matching values. Never delete the database volume as a shortcut without a verified backup.

### Fixed in Phase 10: both Phase 9 reports were returning 500

The dashboard defect described in Phase 9 was fixed, but the same defect class survived in the
client and task reports, which had never worked against PostgreSQL:

- Ordering was applied to the projected report row, which carries correlated subqueries that
  cannot appear in `ORDER BY`. Ordering now happens on the entity, before projection.
- The grouped breakdowns ordered by a member of the constructed `ReportBreakdown` record, and the
  service breakdown converted a GUID to string inside the SQL projection. Both now materialise the
  aggregate first and map in memory.

The CSV/XLSX exports shared the ordering defect. All are fixed and covered by the API integration
suite, which executes every authorised read against a real PostgreSQL database.

### Fixed in Phase 10: list endpoints returned 500 without query parameters

Required non-nullable query parameters (`int page`, `bool includeInactive`, `DateOnly from`) made
Minimal API binding throw, so a plain `GET` of the client, task, service, agreement, billing-entity,
calendar or recurrence-rule list returned HTTP 500 rather than data. These now default. The
frontend always sent the parameters, which is why the defect stayed hidden.

### Fixed in Phase 10: CSRF was not enforced for JSON mutations

`UseAntiforgery()` records a failed validation in `IAntiforgeryValidationFeature`, but only form
binding reads it. Every JSON mutation therefore reached its handler with a missing or invalid
token despite carrying `RequireAntiforgeryToken` metadata; a `POST` without a token was accepted
and returned 201. `SameSite=Strict` cookies limited the practical exposure, but the documented
control was not functioning. The recorded failure is now acted on and returns 400.

### Default non-administrator roles have no grants

Manager, Articles, Paid Assistants, Accountants, and Client Accountants are seeded as role names only. Until an administrator configures their permissions, users with only those roles may have no usable business navigation.

### Resolved in Phase 10: the client register was wider than the client report

`ClientEndpoints` and `ReportingEndpoints` answered "which clients may this user see" differently
for the same permission and ceiling. The register's team set also followed the user's **direct
reports** into teams the user neither joined nor managed; the reporting helper did not. A
TEAM-scoped manager therefore saw a client in the client register that disappeared from the client
report.

Resolved by narrowing the register to the reporting rule: TEAM now reaches only the teams the
employee belongs to or personally manages. This also tightens `CanAccessClientAsync`, so client
edit and deactivate follow the same boundary. The scope checks assert both surfaces together, on
the list and by direct id, and were confirmed to fail when the narrowing is reverted.

One difference remains and is **not** yet resolved: the register requires `agreement.IsActive` for
team-based visibility and the reporting helper does not, so a client whose only agreement is
inactive can still appear in the report but not the register. Deactivation-not-deletion (ADR 0010)
argues for keeping history reportable, so this may be intended; it needs an owner decision and has
no test coverage yet.

### Frontend/API feature mismatch

Several safe backend operations have no complete UI, as listed in the partial-features section. Do not assume an API's existence means an administrator can perform it through the browser.

### Limited error detail and supportability

The frontend often shows only `Request failed (<status>)`. There is no trace/correlation identifier carried to a support-facing error view. Safe structured troubleshooting is Phase 10 work.

### Reporting performance is unproven at target scale

Reports query normalized tables directly; no materialized views or report-specific indexes were introduced in Phase 9. This is intentional until representative measurements exist, but the 2,000-client/5-million-task targets have not been load-tested.

### Production limitations

- No completed production import/UAT.
- No production backup/restore or rollback rehearsal.
- No high-availability claim; design is single-node and recovery-focused.
- The worker logs/records generation failure but there is no alerting pipeline.
- Nginx has basic headers but no CSP; forwarded-header handling needs production review.

### Repository/data limitations

- `Clients List.xlsm` is tracked in Git and may contain confidential firm/client data. Do not paste its contents into prompts, logs, tests, commits, or issue trackers. Reconsider source-control handling during security hardening.
- The live Docker volume and local `.env` are not part of the Git repository. Moving only source code does not move runtime data or secrets.
- The repository currently has one broad checkpoint commit, so Git history does not provide phase-by-phase intent or easy blame information.

## 8. RECENT DEVELOPMENT

The latest change fixes the effective-dated fee timeline in Billing Configuration. There was no way
to undo a mistaken fee revision, and the timeline offered "Revise fee" on agreements that had been
closed, where the API then refused it with "Choose an active client-service agreement" — advice the
form cannot act on, because the agreement is fixed when revising an existing fee.

- `src/Practice.Api/Billing/BillingEndpoints.cs`: added `POST /api/v1/billing/terms/{id}/remove`
  (a POST rather than a DELETE, because it carries a reason and Minimal APIs do not infer a body on
  DELETE). Only the current version can be removed, a reason is required, removal reopens the
  version it replaced, and `billing.term_removed` is audited. Superseded versions are kept: they
  record what was actually agreed. The replace refusal now names the real cause — closed agreement,
  inactive client, or deactivated service. The terms list returns `agreementIsActive`.
- `web/src/app/App.tsx`: "Remove" alongside "Revise fee" on the current term, and an "Agreement
  closed" indicator instead of actions that would be refused.
- `tests/Practice.Api.IntegrationTests/BillingTermChecks.cs`: new regression checks covering all of
  the above. Each assertion was proved to fail against a deliberately reintroduced defect.

The preceding implemented increment is Phase 10 (in progress): audit, security and testing
hardening. Key files added or changed:

- `src/Practice.Api/Audit/AuditEndpoints.cs` (new audit query API)
- `src/Practice.Api/Program.cs` (diagnostics authorization, `audit.view` policy, antiforgery enforcement)
- `src/Practice.Identity/IdentityService.cs` (failed login, lockout and session-revocation auditing)
- `src/Practice.Api/Reporting/ReportingEndpoints.cs` (report translation fixes)
- `tests/Practice.Api.IntegrationTests/` (new PostgreSQL-backed suite)
- `web/src/app/App.tsx` (audit workspace)
- `deploy/scripts/practice.sh` and `practice.ps1` (provision a throwaway database for the suite)

The preceding increment was Phase 9: dashboards and MVP reports.

Primary files involved:

- `src/Practice.Reporting/Practice.Reporting.csproj`
- `src/Practice.Reporting/ReportingRules.cs`
- `src/Practice.Reporting/TabularExport.cs`
- `src/Practice.Api/Reporting/ReportingEndpoints.cs`
- `src/Practice.Api/Billing/BillingProjectionEndpoints.cs` (projection reuse/intersection for reports)
- `src/Practice.Api/Program.cs` (report policies/endpoints and phase metadata)
- `src/Practice.Identity/IdentityConstants.cs` (report permission constants)
- `web/src/app/App.tsx` (dashboard/report/projection workspaces)
- `web/src/app/styles.css`
- `web/scripts/check-foundation.mjs`
- `tests/Practice.Reporting.Tests/Program.cs`
- `docs/phases/phase-09-dashboards-reports.md`
- `docs/architecture-blueprint.md`

The last bug fix was in `src/Practice.Api/Reporting/ReportingEndpoints.cs`: employee workload grouping now materializes the GUID and count from SQL before creating `DashboardBreakdown` strings. This fixed the observed dashboard HTTP 500 without a schema change.

The immediately preceding Phase 8 work added deterministic billing projection and migration `20260820181042_AddBillingProjectionPermission`. Phase 7 added billing entities/terms/schedules and the corresponding schema migration.

## 9. IMPORTANT DESIGN DECISIONS

The accepted ADRs in `docs/adr` should be read before changing architecture. Do not casually reverse these decisions:

1. **Modular monolith, not microservices.** Strong transactions, cross-domain reporting, and simple LAN operations are priorities.
2. **One centralized PostgreSQL database.** Logical schemas and code ownership provide separation while retaining foreign keys and reporting.
3. **Browser client on Windows and macOS.** There is one server deployment, not synchronized per-user desktop databases.
4. **Native Windows Server 2019 production without Hyper-V.** IIS hosts .NET/React; PostgreSQL is a native service. Docker Compose is development/pilot only.
5. **Same-origin secure cookie authentication.** Do not replace it with browser-local-storage JWTs without a new security ADR.
6. **Configurable permissions plus OWN/TEAM/ALL scopes.** Roles are collections of stable permissions; UI visibility is not authorization.
7. **Employee and login user are separate entities.** Employment identity must survive login disablement.
8. **Service, client-service agreement, and task are separate.** They have different lifecycles and meanings.
9. **Task recurrence and billing schedules are separate.** Monthly work may be billed quarterly, and vice versa.
10. **Recurrence rules and billing terms are effective-dated/versioned.** Do not overwrite historical business meaning.
11. **Deactivation instead of ordinary deletion.** Historical business records remain reportable.
12. **Migrations are explicit and privileged.** API/worker startup must not call `Migrate()`.
13. **Projection is expected fee, not invoice/revenue/receivable/payment.** Do not reuse projection results as an accounting ledger.
14. **Asia/Kolkata and Indian financial year.** Instants remain UTC; business dates preserve local meaning; financial year starts 1 April.
15. **Currency totals never aggregate across currency codes.** Fixed fees use decimal money, not floating point.
16. **Source workbook is read-only migration input.** Profiling/dry-run must not modify or execute workbook macros.

Some blueprint statements are aspirational rather than implemented. In particular, time-ordered UUIDs, OpenAPI, React Router/TanStack Query/React Hook Form/Zod, xUnit/Testcontainers, Playwright, complete outbox handling, and full structured observability are not current capabilities. Verify source and package manifests before relying on blueprint language.

## 10. CURRENT APPLICATION STATE

### Inspected runtime state

At handoff time, the local Docker Compose services `database`, `api`, `worker`, and `web` were running. PostgreSQL reported healthy, the proxied readiness endpoint returned `Healthy`, and all eight migrations were applied. The web entry point is the Compose development URL on port 8088.

### Prerequisites

- .NET SDK selected by `global.json` (10.0.100 baseline with latest feature roll-forward).
- Node.js 24+.
- pnpm 11.19.
- Docker Desktop/Engine with Compose v2 for the complete local stack.
- PowerShell on Windows or POSIX shell on macOS/Linux.

### Required local environment variables

Copy `.env.example` to the ignored `.env` and replace placeholders. Variable names are:

- `POSTGRES_DB`
- `POSTGRES_MIGRATOR_PASSWORD`
- `POSTGRES_APP_PASSWORD`
- `POSTGRES_PORT`
- `API_PORT`
- `WEB_PORT`

Do not copy actual values into documentation or commits. The Compose API is normally reached through the web proxy; its declared `API_PORT` is not currently published by `compose.yml`.

Application configuration names used outside Compose:

- `ConnectionStrings__PracticeDatabase`
- `Security__DataProtectionKeyPath`
- `ASPNETCORE_ENVIRONMENT`
- `ASPNETCORE_URLS`
- `PRACTICE_CONFIG_FILE`
- `PRACTICE_MIGRATION_CONNECTION` (design-time EF/migration tooling)
- `PRACTICE_BOOTSTRAP_PASSWORD` (optional controlled automation only; interactive hidden input is safer)

`src/Practice.Api/appsettings.json` contains a development placeholder connection configuration. Treat it as non-production and do not replace it with a real credential in source.

### Recommended local workflow — macOS/Linux

```bash
./deploy/scripts/practice.sh bootstrap
./deploy/scripts/practice.sh verify
./deploy/scripts/practice.sh start
```

Equivalent Make aliases are `make bootstrap`, `make verify`, `make dev`, and `make down`.

Stop without deleting the database volume:

```bash
./deploy/scripts/practice.sh stop
```

### Recommended local workflow — Windows workstation

```powershell
.\deploy\scripts\practice.ps1 bootstrap
.\deploy\scripts\practice.ps1 verify
.\deploy\scripts\practice.ps1 start
```

Stop with:

```powershell
.\deploy\scripts\practice.ps1 stop
```

### Database operations

Apply pending migrations explicitly:

```bash
./deploy/scripts/database.sh migrate
```

PowerShell equivalent:

```powershell
.\deploy\scripts\database.ps1 migrate
```

Backup and verify an isolated restore:

```bash
./deploy/scripts/database.sh backup
./deploy/scripts/database.sh verify-backup backups/<backup-file>.dump
```

Use the equivalent PowerShell script on Windows. Backup files contain confidential data and are Git-ignored; store production copies encrypted and off-server.

### First administrator and password recovery

Local Compose bootstrap (only when no user exists):

```bash
docker compose --env-file .env -f deploy/compose/compose.yml --profile admin run --rm admin \
  bootstrap-admin --mobile YOUR_10_DIGIT_MOBILE --name "Abhishek Adlakha"
```

Local recovery uses the same admin profile with `reset-password --mobile YOUR_10_DIGIT_MOBILE`. Password input is hidden.

### Running components separately for development

This is useful for API/frontend debugging, but the full Compose workflow is the supported integration path:

1. Start PostgreSQL and apply migrations through Compose/database scripts.
2. Provide `ConnectionStrings__PracticeDatabase` to the API without committing it.
3. Run the API on `http://127.0.0.1:5080` so Vite's existing proxy matches.
4. In `web`, run `pnpm install --frozen-lockfile` and `pnpm dev`; Vite listens on port 5173.
5. Run `Practice.Worker` separately only when recurrence generation is required; `--once` runs one generation cycle.

### Native Windows Server 2019 production path

Build on a controlled Windows build machine:

```powershell
.\deploy\windows-server\Publish-Release.ps1
```

The output is a `win-x64`, framework-dependent package containing the API+SPA, migrator, admin CLI, and worker. On the server, the elevated installer:

- Prompts privately for migration-owner and runtime database configuration.
- Migrates before swapping the application directory.
- Stores runtime configuration and Data Protection keys under restricted `ProgramData` storage.
- Creates an IIS HTTPS site/app pool.
- Opens only the selected HTTPS port.
- Installs the worker as a SYSTEM scheduled task at startup and every six hours.

Read `deploy/windows-server/README.md` and `Install-PracticeManagement.ps1` before use. This production path has not yet completed Phase 11 commissioning.

## 11. TESTING

### Existing tests

The eight .NET test projects are executable console checks, not xUnit/NUnit projects:

| Test project | Coverage |
|---|---|
| `Practice.Architecture.Tests` | Required files, module-dependency guard, API/worker must not migrate at startup |
| `Practice.Database.Tests` | EF model count/schemas/seeds/indexes/checks/concurrency and application append-only guards |
| `Practice.Identity.Tests` | Mobile/password validation, random/hash-only sessions, compact login ticket |
| `Practice.Scheduling.Tests` | Recurrence/date matrix, holiday/weekend behavior, leap-year clipping, occurrence-key stability |
| `Practice.Billing.Tests` | Schedule shapes, projection matrix, effective dates, weekends, leap year, CSV/XLSX |
| `Practice.Reporting.Tests` | Dashboard metric date boundaries, IST conversion, CSV formula defense, XLSX package |
| `Practice.WorkbookProfiler.Tests` | Read-only fixture profiling, duplicate/reference checks, client/service dry-run |
| `Practice.Api.IntegrationTests` | Real HTTP pipeline against PostgreSQL: anonymous denial, authorised reads, antiforgery rejection, identity audit coverage, and OWN/TEAM/ALL scope for tasks and clients including direct-ID denial, report narrowing and export narrowing |

`Practice.Api.IntegrationTests` is the only suite that executes EF queries and the HTTP pipeline.
It requires `PRACTICE_TEST_DATABASE` pointing at a **disposable** database with no existing users;
it applies migrations itself. `verify` provisions and always removes a throwaway PostgreSQL
container for it, and skips with a warning when Docker is unavailable.

Frontend `pnpm test` runs `web/scripts/check-foundation.mjs`, which checks required files and source-code strings/endpoints. It is a smoke/static-presence check, not a browser or component behavior suite.

### How to run

Run the complete suite from the repository root:

```bash
./deploy/scripts/practice.sh verify
```

or on Windows:

```powershell
.\deploy\scripts\practice.ps1 verify
```

This restores/builds the .NET solution, runs all seven console suites, provisions a throwaway PostgreSQL container and runs the API integration suite, then performs `pnpm install --frozen-lockfile`, TypeScript checks, frontend smoke check, and a production Vite build.

Individual .NET checks use:

```bash
dotnet run --project tests/<TestProject>/<TestProject>.csproj --configuration Release --no-build
```

Frontend checks use:

```bash
cd web
pnpm lint
pnpm test
pnpm build
```

### Current status

On 2026-08-21 during Phase 10, verification passed:

- .NET Release build: 0 warnings, 0 errors.
- All seven console suites passed.
- The API integration suite passed against PostgreSQL 18.
- TypeScript check, frontend smoke check and Vite production build passed.

The .NET SDK was not installed on the inspecting machine; the build and suites were run in a
`mcr.microsoft.com/dotnet/sdk:10.0` container against the mounted repository. `practice.sh verify`
requires a local `dotnet` and will fail its `require_command dotnet` check until the SDK is installed.

The GitHub workflow also defines Ubuntu, Windows, and macOS verification; Linux Compose/migration/backup/restore verification; and Windows release-package construction. This handoff did not query a remote CI run, so only the local result above is confirmed.

### Testing gaps/conventions

- Extend the integration suite to constraints, migrations, and per-scope OWN/TEAM/ALL queries.
- Add direct-ID denial and scope-intersection tests; the current suite covers anonymous denial and
  antiforgery rejection but not scope narrowing.
- Add browser-level critical paths (login, password change, admin grants, client/task workflows,
  dashboard/report exports). No UI behaviour is currently tested; the frontend check is static.
- Every production incident/fix should gain a regression test. Prefer the integration suite for
  anything touching an EF query, because the console suites cannot catch translation failures.
- Continue using deterministic clocks/date fixtures, explicit Asia/Kolkata boundaries, hand-reconciled money matrices, and source-workbook immutability checks.
- Do not weaken authorization/integrity to make tests easier.

## 12. FILE AND FOLDER STRUCTURE

| Path | Purpose |
|---|---|
| `PracticeManagement.slnx` | .NET solution containing product, tool, and test projects |
| `global.json` | Required .NET SDK baseline |
| `Directory.Build.props` | net10.0, nullable, analyzers, warnings-as-errors |
| `Directory.Packages.props` | Central EF Core/Npgsql package versions |
| `README.md` | Top-level status and quick-start |
| `src/Practice.Api` | API host and vertical endpoint modules |
| `src/Practice.Database` | EF context, physical model, seeds, and migrations |
| `src/Practice.Identity` | Authentication/session/credential/recovery services |
| `src/Practice.Scheduling` | Recurrence calculator and generator service |
| `src/Practice.Billing` | Billing rules and pure projection calculator |
| `src/Practice.Reporting` | Reporting/date rules and tabular export |
| `src/Practice.BuildingBlocks` | Shared clock/auditing abstractions only |
| `src/Practice.Worker` | Six-hour/one-shot generation process |
| `src/Practice.Migrator` | Explicit schema migrator |
| `src/Practice.AdminCli` | Bootstrap/recovery CLI |
| `web` | React/Vite application, Nginx config, Dockerfile, pnpm lockfile |
| `tests` | Seven executable .NET check projects |
| `tools/Practice.WorkbookProfiler` | Read-only workbook profiling/dry-run tool |
| `deploy/compose` | Local/pilot Docker Compose definition |
| `deploy/postgres/init` | Initial runtime-role creation for a new PostgreSQL volume |
| `deploy/scripts` | Cross-platform lifecycle, migration, backup, restore verification |
| `deploy/windows-server` | Native Windows Server 2019 release and installer baseline |
| `docs/adr` | Accepted architectural decisions; supersede with new ADRs rather than rewriting history |
| `docs/phases` | Phase-specific outcomes/contracts through Phase 9 |
| `docs/security` | Threat model and data classification |
| `docs/operations` | Cross-platform and database operations |
| `docs/phase-0-decision-register.md` | Confirmed/open business decisions |
| `Clients List.xlsm` | Confidential, read-only migration source; not a relational schema |

Empty local directories such as `src/Practice.Clients` or `tools/Practice.ClientImporter` are not solution projects and contain no tracked implementation. Do not infer features from them.

## 13. SECURITY

### Implemented controls

- Password hashing through ASP.NET Core Identity-compatible hasher.
- Password length/common/mobile checks.
- Generic login failures, lockout, and IP-based rate limiting.
- Encrypted HttpOnly same-origin cookies; Secure and `__Host-` cookies in production.
- Server-side session token hash, finite expiry, revocation, and security stamp.
- Permission policies plus server-side row scope.
- Antiforgery cookie/header validation for mutations.
- Restricted migrator/runtime PostgreSQL roles.
- Explicit migrations; no application-startup schema changes.
- Data Protection key persistence in Compose volume/Windows restricted storage.
- Audit records for many significant changes; append-only protection.
- CSV formula neutralization and bounded exports.
- Nginx `nosniff`, frame denial, and no-referrer headers.
- Windows installer applies restricted filesystem ACLs and IIS HTTPS.

### Secrets and environment handling

- `.env` is local and must remain uncommitted.
- Do not place real passwords in `appsettings*.json`, `.env.example`, scripts, docs, prompts, shell history, or ordinary CLI arguments.
- Production runtime configuration and data-protection keys belong in restricted server storage.
- Migration and runtime DB credentials must remain separate.
- Backups, exports, the source workbook, client tax identifiers, phones, emails, addresses, billing data, comments, and audit rows are confidential.
- Session secrets, password hashes, DB credentials, and key material are restricted and must never be logged or audited.
- If source/runtime data is copied to another machine or agent environment, use an encrypted, approved channel and transfer only what is required.

### Security work still required

- Protect the diagnostics endpoint.
- Implement `audit.view`, audit search/timeline, export audit, and complete action coverage.
- Add CSP and review all response headers, IIS/Nginx forwarding, host filtering, HTTPS assumptions, and error responses.
- Add safe trace/correlation IDs without returning SQL/stack/secrets.
- Add authorization integration tests for direct IDs and every OWN/TEAM/ALL query path.
- Review rate limiting beyond login where bulk/export/generation endpoints warrant it.
- Add dependency/supply-chain and secret scanning to CI.
- Decide retention and governed redaction/erasure behavior.
- Review the presence of the confidential workbook in Git history.
- Commission encrypted off-server backups and restore drills.

## 14. CURRENT DEVELOPMENT PRIORITY

**Phase 10 is complete.** Delivered: diagnostics authorization; `audit.view` policy, query API and
workspace; audit coverage for failed logins, lockouts, session revocation, exports, generation runs
and holiday changes; JSON antiforgery enforcement; CSP and the remaining security headers on both
hosting paths; support references on error responses; the administration workspace permission fix;
a consistent OWN/TEAM/ALL team rule across all six scoped modules; and a PostgreSQL-backed
integration suite covering anonymous denial, authorised reads, antiforgery and record scope.

Audit retention and the administrator health screen, previously deferred, are now implemented.
Retention keeps routine history three months and security history twelve, archiving expired rows
to a file before deleting them.

Operational note: the archive files accumulate in the `practice-audit-archive` volume (or the
configured `Audit:ArchivePath` on Windows). They contain confidential history and are **not** yet
rotated or copied off the server. Fold them into the Phase 11 backup routine.

Still open, and cheap to finish when someone touches these areas:

1. Alerting when a generation run fails. The health screen shows staleness, but nobody is told.
2. The second client-scope difference recorded in section 7: the register requires an active
   agreement for team visibility and the report does not.
3. Automated browser critical-path tests. UI behaviour has been verified manually and the frontend
   check is static only.
4. Consolidating audit writing: call sites still construct `AuditEvent` by hand rather than using
   `IAuditWriter`, so payload conventions drift.
5. Forwarded-header, host-filtering and TLS review against the real proxy, plus dependency and
   secret scanning in CI.

After Phase 10, Phase 11 is production release, workbook cleansing/import, Windows Server commissioning, migration/backup/rollback rehearsal, performance testing, UAT, and training. Phase 12 is time-boxed post-release stabilization.

Phase 13 (`docs/phases/phase-13-bulk-client-import.md`) holds bulk client import from an uploaded
spreadsheet: template download, upload, validation and a preview before anything is written. It was
requested on 2026-08-21 and deferred by the owner the same day. It is a feature in its own right,
not an extension of the one-time migration importer, because it runs against a file nobody has
studied beforehand. Four decisions are recorded there and are needed before it is built.

Do not start invoices, payments, portals, documents, messaging, or other post-MVP features before the Phase 10/11 safety and commissioning work.

Business decisions still needed before production import include legal billing entities, classification of workbook value `Cash`, employee-name mappings, ambiguous `Firm` classification, Saturday/holiday policy, audit retention, recovery targets, and approved statutory recurrence test cases. See `docs/phase-0-decision-register.md`.

## 15. WARNINGS FOR THE NEXT AI CODING AGENT

1. Read this file, `README.md`, relevant phase document, `docs/adr/README.md`, and `docs/phase-0-decision-register.md` before editing.
2. The code is the authority for what exists; the blueprint includes uninstalled libraries and future infrastructure.
3. Preserve the centralized PostgreSQL/modular-monolith boundaries. Do not introduce microservices or per-client databases.
4. Never let API or worker startup apply migrations. Add and review a new EF migration for every schema change.
5. Never edit an already-applied migration. Add a corrective migration.
6. Do not expose or reproduce `.env`, database configuration values, password hashes, session data, client records, workbook contents, backups, or exports.
7. Do not delete/recreate the Docker database volume to solve connectivity unless the owner explicitly authorizes data loss and a restore has been verified.
8. If `.env` database passwords change, remember existing PostgreSQL roles are not automatically rotated by the initialization script.
9. Treat every permission scope/query change as security-critical. Test list, detail/direct-ID, mutation, masters/filter metadata, dashboard, and export paths.
10. Keep UI checks as usability only. Every action and record scope must remain enforced server-side.
11. Preserve effective-dated/versioned recurrence and billing history. Do not mutate prior versions in place.
12. Do not merge task recurrence and billing schedules.
13. Never treat a billing projection as an invoice, revenue, receivable, or payment.
14. Do not seed a legal billing entity or map `Cash` without owner confirmation.
15. Do not auto-map ambiguous workbook people/categories. Dry-run, reconcile, and obtain sign-off.
16. Maintain Asia/Kolkata business-date semantics, UTC instants, Indian financial-year boundaries, decimal money, and currency-separated totals.
17. Run the full verify script before handoff. If a query changed, add a real PostgreSQL integration test; the existing console tests cannot catch all EF translation errors.
18. Keep `.env`, `backups`, `artifacts`, `bin`, `obj`, `node_modules`, and generated `web/dist` out of commits.
19. The current one-commit history is weak evidence. Keep future changes small, explain phase/decision intent, and report migrations/tests/operational impact.
20. Windows Server production is native IIS/.NET/PostgreSQL. Do not propose Docker Desktop or Hyper-V for that host.

## 16. CODE QUALITY / TECHNICAL DEBT

### Frontend concentration

`web/src/app/App.tsx` is approximately 446 dense lines containing most types, API helpers, navigation, and every workspace/form. `styles.css` is similarly compressed. This makes permission-aware loading, error states, testing, and feature maintenance fragile. A gradual split by feature plus shared API/session primitives is warranted, but only with behavior tests first; a broad visual rewrite before Phase 10 would be risky.

### Endpoint concentration and duplicated policy logic

Endpoint files are large static modules with validation, EF queries, auditing, and DTO mapping together. OWN/TEAM/ALL calculations and audit helper construction are duplicated across clients, services, tasks, scheduling, billing, projection, and reporting. Consolidation could reduce drift but is security-sensitive and must be preceded by cross-module parity tests.

### Testing depth

The console checks are fast and useful but do not host the API, authenticate real cookies/CSRF, or exercise EF queries against PostgreSQL. The dashboard 500 demonstrated this gap. Introduce an actual test framework and integration harness incrementally; do not discard the deterministic rule matrices.

### Documentation drift

The architecture blueprint mentions React Router, TanStack Query, React Hook Form, Zod, OpenAPI, xUnit, Testcontainers, Playwright, time-ordered UUIDs, and a `src/Modules` layout. These are not current implementation facts. Update documentation when decisions are actually implemented, and use ADRs when changing accepted architecture.

### Audit inconsistency

Many endpoints manually instantiate `AuditEvent` with local helper functions even though `IAuditWriter`/`EfAuditWriter` exists. Coverage and payload conventions can drift. Phase 10 should define a single action/payload policy and transactional approach before refactoring.

### Database privilege consistency

Audit event immutability has both application and DB-role protection. Task status history has an application guard but inherits general task-schema update/delete grants. Consider database-level tightening in a new migration, after verifying EF/runtime needs.

### Outbox and operational observability

The outbox schema is unused. Logs are JSON but there is no end-to-end correlation/trace support, alerting, metrics backend, or worker failure notification. Avoid adding a large observability stack without operational need, but implement safe trace IDs and administrator health visibility in Phase 10.

### Frontend UX debt

Several edits use `window.prompt`; validation errors are generic; modals lack robust focus management; admin data is eagerly loaded; and important backend operations lack forms. Preserve server invariants while replacing these incrementally with accessible forms and permission-aware loading.

### Performance debt

Reporting/projection read normalized tables directly and some scope helpers materialize ID arrays. This is acceptable for the current small data set but unproven at the documented target scale. Measure representative PostgreSQL query plans before adding indexes/read models or changing authorization logic.

### Configuration debt

Development placeholder database configuration is present in source appsettings, while production correctly uses external protected configuration. Phase 10 should tighten the development configuration story without committing secrets or breaking Compose/direct-run workflows.

### Git/data hygiene

The single checkpoint commit contains the entire implementation and the confidential source workbook. Future work needs smaller commits, explicit migration/release notes, and a deliberate decision about workbook/source-history access. Removing a file from the latest tree alone does not remove it from Git history.
