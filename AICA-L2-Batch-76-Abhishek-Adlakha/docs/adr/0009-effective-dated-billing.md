# ADR 0009: Effective-Dated Billing Terms

- Status: Accepted
- Date: 2026-08-19

## Decision

Store fixed-fee commercial terms as non-overlapping, effective-dated versions per client service, each referencing its billing entity and schedule.

## Alternatives

Fee on client, service master or generated task; overwrite the current rate/entity.

## Rationale and consequences

Client-specific fees and entity changes must preserve projection history. Editing creates a future version rather than rewriting prior terms. MVP allows one entity per active term; split allocations need a later ADR.

