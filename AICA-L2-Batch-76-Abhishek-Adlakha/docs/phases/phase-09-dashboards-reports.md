# Phase 9 — Dashboards and MVP reports

## Outcome

Phase 9 adds a permission-scoped operational dashboard and three core report families: client register, task register and deterministic billing projection. Dashboard cards use the same server filters as their drill-down reports, so a card count and the report total reconcile by construction. No reporting rows, snapshots or materialized views are introduced; the current normalized transactional data remains the source of truth.

## Metric contract

The business date is the current `Asia/Kolkata` date. Active and inactive client counts use the current client lifecycle status. “Clients with GSTIN” means a visible client with at least one active GST registration. “Due today” and “overdue” include only non-terminal tasks. “In process” uses the current status code. Completed and cancelled totals use their respective event timestamps inside the selected inclusive local-date period; UTC boundaries are calculated from India Standard Time.

Current workload groups visible tasks by their current active primary assignment. Current-month projected fees reuse the Phase 8 deterministic calculation and keep currencies separate. They are displayed only when the caller has both `reports.view` and `billing.project`; they remain expected fees, not invoices, revenue, receivables or payments.

## Reports and filters

- Client register: lifecycle status, active-GSTIN coverage, category and currently effective primary group; rows show code, name, PAN, category, group and active GSTIN count.
- Task register: due/status bucket, explicit status, inclusive date period, current employee assignment, client, service and billable flag; rows show task, client, service, due date, status, priority and primary assignee.
- Billing projection: the Phase 8 month, quarter, financial-year, client, group, billing-entity, service, team and manager views.

Client/task reports include reconciled status and category/service summaries, server pagination and bounded CSV/XLSX detail. CSV values that could be interpreted as spreadsheet formulae are neutralized. XLSX files are generated as Open XML without server-side persistence. Exports are limited to 10,000 matching rows and report periods to five years; the dashboard period is limited to 367 days.

## Security contract

Every dashboard and report query requires `reports.view` and applies its OWN, TEAM or ALL scope on the server. Task OWN scope means current assignments to the signed-in employee; TEAM includes currently accessible team employees; ALL is firm-wide. Client OWN/TEAM scope is derived from responsible teams on client-service agreements. Filter masters use the same visible task/client sets and do not expose out-of-scope employees, clients, services, categories or groups.

CSV/XLSX additionally requires `reports.export`. Export queries intersect the caller's `reports.view` and `reports.export` scopes, so export can never widen screen visibility. Projection export also retains its Phase 8 `billing.project` intersection. Client-side filtering is never treated as an authorization control.

## API

- `GET /api/v1/dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD`
- `GET /api/v1/reports/catalog`
- `GET /api/v1/reports/masters`
- `GET /api/v1/reports/clients`
- `GET /api/v1/reports/tasks`
- `POST /api/v1/reports/clients:export`
- `POST /api/v1/reports/tasks:export`

The existing Phase 8 projection calculate/export endpoints remain the billing report implementation.

## Acceptance evidence

- Metric rules cover due-date buckets, terminal exclusions and completion/cancellation boundaries at India-local midnight.
- Every operational card opens the equivalent report filter and displays card total versus report total.
- Client/task reports, filter masters and exports share server-side permission scope.
- CSV formula protection and valid XLSX package generation are tested.
- The API release image, TypeScript checks, frontend production build and Phase 9 UI smoke checks pass.
- No schema migration was required because report permissions were introduced earlier and normalized Phase 3–8 entities already supply the required data.

## Explicit exclusions

Phase 9 does not add advanced analytics, employee-utilization targets, custom report builders, AI, projection snapshots, invoices, tax calculations, receivables, payments or revenue recognition. Covering indexes or report read models will be added only after production-like measurements justify them.
