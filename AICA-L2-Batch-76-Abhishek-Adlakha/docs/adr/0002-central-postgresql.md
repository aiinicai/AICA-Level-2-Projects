# ADR 0002: Central PostgreSQL Database

- Status: Accepted
- Date: 2026-08-19

## Decision

Use one PostgreSQL database with logical schemas and module-owned tables. Preserve foreign keys and transactions across module boundaries while prohibiting cross-module writes in application code.

## Alternatives

Database per client; database per module; document database.

## Rationale and consequences

Central storage best supports reporting, task assignment, integrity, migration and backup for a single CA organization. It is a shared operational dependency and needs careful migration/recovery controls. Per-client tenancy is reconsidered only if the product serves unrelated firms.

