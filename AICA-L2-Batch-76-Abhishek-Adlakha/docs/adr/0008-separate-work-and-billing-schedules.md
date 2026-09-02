# ADR 0008: Separate Work and Billing Schedules

- Status: Accepted
- Date: 2026-08-19

## Decision

Task recurrence and billing schedules are independent configurations linked through the client service agreement.

## Alternatives

Infer projected billing directly from generated tasks or use one frequency for both.

## Rationale and consequences

Monthly work may be billed quarterly and annual work may be billed in a selected month. Two schedules add UI responsibility, so configuration screens must summarize both and prevent users from assuming one controls the other.

