# ADR 0012: Projection Is Not an Invoice

- Status: Accepted
- Date: 2026-08-19

## Decision

Treat projected billing as a calculation from billing terms/schedules. It is not an invoice, receivable, payment record or revenue-recognition ledger.

## Alternatives

Reuse projection rows as invoices or treat spreadsheet monthly values as issued billing.

## Rationale and consequences

The separation avoids accounting ambiguity and allows later invoice/payment modules to own immutable ledgers. Projection UI/reports must label definition, as-of date and assumptions; future invoices may reference originating terms/projection context without mutating them.
