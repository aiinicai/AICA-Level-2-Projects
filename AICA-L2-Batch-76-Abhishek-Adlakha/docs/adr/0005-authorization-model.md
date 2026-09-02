# ADR 0005: Authorization Model

- Status: Accepted
- Date: 2026-08-19

## Decision

Represent roles as configurable permission collections. Permissions name stable actions and use `OWN`, `TEAM` or `ALL` record scopes where relevant. Enforce policy and record scope on the server.

## Alternatives

Hard-coded roles; client-side visibility; unrestricted per-record ACLs.

## Rationale and consequences

Action permissions are flexible without the administration complexity of arbitrary ACLs. UI checks are usability only. Confidential client-specific grants may be added later if a demonstrated requirement cannot use team responsibility.

