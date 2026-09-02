# ADR 0006: Separate Service, Client Service and Task

- Status: Accepted
- Date: 2026-08-19

## Decision

Model a reusable Service master, an effective-dated Client Service Agreement, and actual dated Tasks as separate entities.

## Alternatives

One combined service/task table; spreadsheet-style service columns on clients.

## Rationale and consequences

Defaults, client/GSTIN-specific configuration and historical work have different lifecycles. The separation prevents adding a new service from requiring a schema change and makes recurrence/billing ownership explicit. UI terminology must clearly teach the distinction.

