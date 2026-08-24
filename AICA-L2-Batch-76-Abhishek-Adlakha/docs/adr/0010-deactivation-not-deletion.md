# ADR 0010: Deactivation, Not Business Deletion

- Status: Accepted
- Date: 2026-08-19

## Decision

Deactivate clients and configurable masters with effective dates/reasons. Never physically delete historical tasks, assignments, billing terms or audit records in ordinary workflows.

## Alternatives

Hard delete; universal undifferentiated `deleted_at`.

## Rationale and consequences

Professional-services history must remain reportable. Operational queries default to active records; historical screens can include inactive. Legal erasure/retention actions, if needed, require a separate governed process rather than ordinary CRUD.

