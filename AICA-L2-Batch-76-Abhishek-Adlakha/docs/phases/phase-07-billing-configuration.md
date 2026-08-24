# Phase 7 — Billing entities and effective-dated billing configuration

## Outcome

Phase 7 adds the legal billing-entity master and commercial terms for each client-service agreement. A fee is fixed per billing event, not per task. Billing schedules remain independent from task recurrence: monthly work may be billed quarterly, while an annual service may be billed in a selected month.

No legal firm is seeded. Abhishek must enter only confirmed legal billing entities. The workbook value `Cash` remains an import exception because it may represent a payment mode or unresolved migration value rather than an invoicing entity.

## Database and history

Forward-only migration `20260820173917_AddBillingEntitiesAndEffectiveDatedTerms` adds:

- `billing.billing_entities`, with unique code and optional unique GSTIN, effective dates, active status and optimistic concurrency;
- `billing.billing_terms`, with immutable client-service versions, fixed `numeric(19,2)` fees, billing entity, currency, tax-inclusive flag and effective dates;
- one-to-one `billing.billing_schedules` and selected `billing.billing_schedule_months`;
- `import.billing_import_proposals` for later reviewed Billing MIS staging.

A PostgreSQL exclusion constraint prevents effective-date overlap for the same client-service agreement, including concurrent writes. A replacement closes the prior term on the day before the new version starts and retains both records. Non-billable terms have no amount, billing entity or schedule.

## Frequencies and validation

Supported schedules are Monthly, Quarterly, Half-yearly, Annually, Specific Month, One-time and Custom Months. Recurring schedules require an anchor date and billing day; one-time schedules require only one billing date. Business-day adjustment is None, Previous or Next. Projection timing is fixed to one fee per billing event for the Phase 8 calculation engine.

The billing entity must be active and effective for the complete term. Its currency must match the term currency. Term dates must remain within the client-service agreement. Billing entities cannot be deactivated while current or future terms still reference them.

## API, permissions and user interface

Phase 7 activates scoped `billing.view` and scoped `billing.configure`. OWN/TEAM/ALL access is evaluated from the responsible team on the client-service agreement. Only ALL-scope billing administrators may maintain the legal billing-entity master; scoped administrators may configure permitted agreement terms.

The Billing workspace provides:

- confirmed legal billing entities with effective dates and status;
- agreement filtering and an effective-dated fee timeline;
- billable and explicit non-billable terms;
- all seven billing frequencies and business-day choices;
- guarded fee replacement that retains earlier versions;
- configurable optional billing-entity and fee-note requirements in Administration.

All changes are audited. Amounts use decimal database values and are never stored as floating point.

## Verification

- strict Release compilation for all .NET projects;
- billing-rule tests covering every frequency and invalid month combinations;
- database-model checks for schema ownership, decimals, concurrency and schedule shape;
- migration application on the existing Phase 6 database and idempotent second application;
- live API readiness and browser production build;
- database acceptance checks for overlap rejection and least-privilege runtime access.

## Deferred

Phase 7 does not calculate projected totals, generate invoices, apply tax calculations, record receivables or accept payments. Phase 8 will compute deterministic projections from these terms and schedules. No Billing MIS row is imported until legal-entity mappings, including `Cash`, are reviewed and explicitly approved.
