# ADR 0007: Versioned Rolling Recurrence Generation

- Status: Accepted
- Date: 2026-08-19

## Decision

Store effective-dated recurrence rules and generate only a bounded future task horizon using a persisted, locked, idempotent worker. Use immutable occurrence keys and explicit exceptions.

## Alternatives

Generate years of tasks in advance; calculate tasks only when a calendar is opened; mutate a single rule in place.

## Rationale and consequences

Rolling generation creates actionable/auditable tasks without database explosion. It requires a worker, deterministic due-date tests, job visibility and impact preview when rule versions change.

