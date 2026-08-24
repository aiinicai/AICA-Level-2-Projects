# ADR 0011: Controlled Database Migrations

- Status: Accepted
- Date: 2026-08-19

## Decision

Use version-controlled EF Core migrations, reviewed SQL scripts or migration bundles for releases, and expand/contract changes where compatibility matters. Production application credentials cannot alter schema.

## Alternatives

Manual production DDL; unconditional migration during application startup.

## Rationale and consequences

Reviewed repeatable changes protect data and make releases traceable. Deployment needs a privileged migration step, backup/preflight and prior-version migration test. Released migrations are never edited; corrective migrations are added.

