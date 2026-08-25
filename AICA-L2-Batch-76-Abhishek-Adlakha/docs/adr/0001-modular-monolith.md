# ADR 0001: Modular Monolith

- Status: Accepted
- Date: 2026-08-19

## Decision

Use one deployable application codebase with explicit domain modules and a separately runnable worker from the same repository. Enforce module ownership and dependencies through tests and review.

## Alternatives

Microservices; an unstructured layered monolith.

## Rationale and consequences

The system needs strong transactions, cross-domain reporting and simple LAN operations. Microservices add failure modes and deployment overhead with no present team/scaling benefit. The monolith requires disciplined boundaries; a module may be extracted later only for measured independent scaling, ownership or release needs.

