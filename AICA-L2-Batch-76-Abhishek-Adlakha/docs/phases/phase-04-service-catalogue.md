# Phase 4 — Service catalogue and client service agreements

## Outcome

Phase 4 separates reusable service definitions from each client’s effective-dated engagement. A catalogue service is never a task, recurrence rule or fee. An agreement connects one client to one service, optionally for one of that client’s GST registrations, with dates, priority and a responsible team.

The production architecture remains native Windows Server 2019 with IIS, .NET 10 and PostgreSQL. Windows and macOS staff continue to use the same browser application across the office LAN.

## Database

Forward-only migration `20260820145554_AddServiceCatalogueAndClientAgreements` adds the `services` schema and:

- five service categories and 21 service definitions derived from the workbook’s real service columns;
- effective-dated `client_services` with optional GSTIN scope and responsible-team routing;
- service import proposal staging in the existing `import` schema;
- four service permissions and five configurable client-service field policies;
- least-privilege runtime grants for `practice_app`.

Database constraints enforce valid date ranges/priorities, reasoned deactivation, one active client-wide agreement per client/service, one active GSTIN-scoped agreement per client/service/GSTIN, and a composite foreign key proving that the selected GSTIN belongs to the same client.

Seed categories are Accounting, Income Tax, GST, Assurance and Advisory, and Corporate and Regulatory. Seed services preserve separate workbook concepts such as Audit versus Tax Audit and GST versus GSTR-9. Seeds are catalogue starting points and remain administratively configurable.

## API and access control

The API supplies catalogue/category creation, catalogue updates, impact-safe service deactivation, agreement list/detail/create/update, and reasoned agreement close/reactivation.

Permissions are `services.view`, `services.catalogue.manage`, `services.enrollments.view`, and `services.enrollments.manage`. `OWN` and `TEAM` agreement scopes are evaluated through the responsible team: OWN covers current team memberships; TEAM also covers teams managed by the employee and current direct-report memberships. `ALL` covers the firm. Scoped users cannot create or move an agreement outside an accessible responsible team.

Service default changes do not mutate existing agreements. A service with active agreements cannot be deactivated until those agreements are closed, and the API returns the impact count.

## User interface

Authorized users have a Services workspace containing:

- searchable/filterable accessible client agreements;
- service catalogue capabilities and active-agreement impact counts;
- service creation;
- client enrollment with client-wide or GSTIN-specific scope;
- effective dates, priority, responsible team and engagement metadata;
- safe service and agreement deactivation/reactivation.

No recurrence editor, work generation, task, fee or billing field appears in this workspace.

## Workbook service dry-run

Run:

```bash
dotnet run --project tools/Practice.WorkbookProfiler --configuration Release -- \
  "Clients List.xlsm" --service-dry-run --output artifacts/phase-04-service-dry-run.json
```

The source is opened read-only and its SHA-256 is checked before and after. Yes/No values become staged proposals. `A/c` values Monthly and Yearly also propose Accounts agreements, while retaining the cadence only as source metadata for Phase 6; Phase 4 does not create recurrence rules.

GST, GST Refund, GSTR-9 and LUT proposals require a valid GSTIN scope. `Accountant`, `Leader` and `ITR Data` values are reported as unresolved ownership references under BIZ-005 and are never guessed or matched automatically.

Current controlled dry-run totals for `Clients List.xlsm`:

- 511 source rows;
- 1,167 proposed agreements;
- 1,156 ready proposals;
- 11 GSTIN-scope exceptions;
- 40 distinct unresolved ownership references;
- zero unknown service flags;
- unchanged source SHA-256 `37e80309f683678c3466a7480fa6c01639699259a43fc9e81a443424eca0f0ac`.

No proposals are imported until the Phase 3 client exceptions and BIZ-005 employee mappings are reviewed and an explicit approved batch is authorized.

## Verification

- clean Release build of the solution and production web bundle;
- Architecture, Database, Identity and WorkbookProfiler executable checks;
- forward migration and safe second application;
- service/category seed counts and application-role grants;
- active agreement uniqueness for null and GSTIN scopes;
- database rejection of cross-client GSTIN references;
- service deactivation impact block;
- create GST Returns for two GSTINs and one client-wide Audit agreement in a controlled sample;
- confirm changing a service default does not alter those agreements;
- confirm workbook SHA remains unchanged.

## Deferred

Phase 4 does not create recurrence or due rules, work items, task assignments, amounts, billing entities, billing schedules or invoices. These remain in Phases 5–8. Workbook ownership names remain staged until BIZ-005 is confirmed.
