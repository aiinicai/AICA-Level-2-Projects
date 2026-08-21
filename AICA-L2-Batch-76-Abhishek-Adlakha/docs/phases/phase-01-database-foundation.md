# Phase 1 Completion Record

Date: 2026-08-20  
Status: Implemented and locally verified on Docker Desktop for macOS (Apple Silicon).

## Scope delivered

- `Practice.Database` EF Core 10 persistence project with PostgreSQL provider and explicit snake-case relational mapping.
- Logical `reference`, `system`, `audit`, and `import` schemas plus EF migration history in `system`.
- Eight foundation entities: India state/UT reference, application setting, holiday calendar/holiday, append-only audit event, outbox message, import run, and import issue.
- Initial settings for `Asia/Kolkata` and the 1 April financial-year start, plus an empty configurable India holiday-calendar framework. No unverified statutory holiday dates were seeded.
- Thirty-six active GST state/UT reference rows, including code 38 Ladakh and the merged code 26 union territory.
- Reviewed `InitialFoundation` migration, a one-shot migrator container, and no application-host startup migration.
- Fixed `practice_migrator` schema-owner identity and lower-privilege `practice_app` runtime identity. Only passwords are configurable.
- Application-role grants scoped by schema; it cannot create schema objects, rewrite audit events, or alter EF migration history.
- Database-aware readiness and `/api/v1/system/diagnostics` with safe provider/migration/reference counts.
- Structured JSON console logging for API and migrator.
- `IAuditWriter` abstraction with an EF implementation and an application guard against audit update/delete.
- Cross-platform database migration, backup, and isolated restore-verification wrappers for POSIX and PowerShell.
- Standalone .NET Open XML workbook profiler for `.xlsx`/`.xlsm`, with source hash, sheet/row/column counts, normalized duplicates, blank headers, and optional unmatched assignment-reference reporting.
- Phase 1 diagnostics UI; no admin mutations or business pages.

## Initial physical tables

| Schema | Tables |
|---|---|
| `reference` | `india_states` |
| `system` | `app_settings`, `holiday_calendars`, `holidays`, `outbox_messages`, `ef_migrations_history` |
| `audit` | `audit_events` |
| `import` | `import_runs`, `import_issues` |

All entity tables have named primary keys. Relationships, uniqueness constraints, check constraints, and operational indexes are declared in the EF model and migration. Audit records are append-only at both application and database-permission layers.

## Verification evidence

| Check | Result |
|---|---|
| Full .NET Release build | Passed; 9 projects, 0 warnings, 0 errors |
| Architecture checks | Passed; application hosts cannot invoke migrations at startup |
| Database model checks | Passed; 8 entities, 4 owned schemas, 36 state/UT seeds, 1 migration, append-only audit guard |
| Workbook profiler sanitized fixture | Passed; source hash unchanged, duplicate and unmatched-reference observations detected |
| Frontend typecheck/test/production build | Passed |
| Fresh PostgreSQL 18 initialization | Passed from an empty Docker volume |
| Initial EF migration | Passed; migrator exited 0 and created 9 tables including migration history |
| Second migration application | Passed; reported 0 pending and no migrations applied |
| Runtime database permissions | Passed; schema create=false, audit update=false, audit insert=true, migration-history delete=false |
| API system information | Passed; reports Phase 1 |
| Database diagnostics | Passed; Healthy, Npgsql provider, 1 migration, 36 state/UT rows |
| `/health/ready` | Passed with live database check |
| Browser-rendered diagnostics | Passed; correct four diagnostics and no console warnings/errors |
| Backup | Passed; custom-format dump created in Git-ignored `backups/` |
| Restore rehearsal | Passed; restored 9 tables to `practice_restore_verification`, validated, then removed only that temporary database |

## Workbook profile evidence

The source `Clients List.xlsm` was opened read-only and profiled without macro execution:

- File size: 182,680 bytes.
- SHA-256: `37e80309f683678c3466a7480fa6c01639699259a43fc9e81a443424eca0f0ac`.
- Sheets: `Master Data` (511 worksheet data rows, 39 columns) and `Billing MIS` (972 worksheet data rows, 20 columns).
- Total: 1,483 worksheet data rows and 437 normalized duplicate-value observations.
- No reference list was supplied for real employee matching, so the tool did not label real names as matched/unmatched. That decision remains BIZ-005 and must be resolved before employee import work.

Counts describe non-empty Open XML row elements below each detected header and are profiling evidence, not approved import totals. The JSON report is stored locally at `artifacts/clients-list-profile.json`, which is excluded from Git.

## Deliberately not implemented

- No authentication, users, employees, roles, permissions, teams, or sessions.
- No client, group, GSTIN, service, task, recurrence, billing, projection, report, or dashboard business tables.
- No workbook staging writes, transformation, final import, macro execution, or source modification.
- No authoritative statutory holiday dates.
- No API that mutates settings, holidays, imports, audit, or outbox data.
- No production restore automation that can overwrite the primary database.

## Exit gates before Phase 2

1. Replace both example local passwords before any shared/LAN or non-local deployment.
2. Confirm the bootstrap-administrator ownership and credential-delivery procedure during Phase 2 implementation.
3. Resolve BIZ-005 with a named business owner before any employee-name workbook mapping is authorized.

Phase 2 may implement identity, employee/user separation, roles, permissions, teams, and secure sessions only. It must not pull client or billing CRUD forward.
