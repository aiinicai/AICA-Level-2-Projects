# Phase 8 — Deterministic billing projection

## Outcome

Phase 8 calculates expected fixed fees on demand from Phase 7 billing terms and schedules. A projection is explicitly not an invoice, receivable, payment, revenue entry or tax calculation. No calculated rows are persisted, so billing configuration remains the only source of projection truth.

## Calculation contract

The request supplies a date range, report as-of date and optional client, primary-group, service, billing-entity, responsible-team or responsible-manager filters. The server first applies the caller's `billing.project` OWN/TEAM/ALL scope to client-service agreements, then expands every eligible fixed-fee schedule.

Each billing event emits the full configured amount. Monthly fees are therefore emitted monthly; quarterly fees once per configured quarter; half-yearly and annual fees at their configured anchor; specific/custom months only in selected months; and one-time fees once. Day 29–31 clips to the final day of shorter months. Previous/next adjustment uses Sunday plus the India firm holiday calendar.

Fee terms, client-service agreements and billing entities must all be effective on the adjusted projection date. Mid-period changes use the effective term version rather than prorating or dividing annual amounts. Each detail row explains the term version, frequency, nominal date, adjusted date, service period, amount and currency.

## Dimensional attribution

- Client and service come from the client-service agreement.
- Billing entity and currency come from the effective fee term.
- Client group means the single `PRIMARY` membership effective on the projection date. Secondary memberships never duplicate financial totals.
- Team means the agreement's responsible team.
- Employee means that team's manager and is labelled as operational attribution, not revenue ownership.
- Amounts are grouped only within the same currency. Cross-currency totals are never produced.
- Calendar quarter and Indian financial year (April–March) are separate views.

## Security and exports

`billing.project` is a new scoped permission. Administrators receive ALL scope through migration; other roles can be granted OWN, TEAM or ALL by an administrator. The same scope builder controls calculation, filter masters and export. CSV/XLSX download additionally requires scoped `reports.export`, and uses the narrower intersection of projection and export scope.

CSV protects spreadsheet formula-leading values. XLSX is generated as an Open XML workbook without storing a server-side copy. Both formats contain the complete scoped detail; the browser limits very large on-screen detail to the first 300 rows.

## API

- `GET /api/v1/billing-projections/masters`
- `POST /api/v1/billing-projections:calculate`
- `POST /api/v1/billing-projections:export`

Projection windows are capped at five years to bound schedule expansion. Normal financial-year and annual projections are calculated on demand; measured evidence is required before adding snapshot/cache tables or asynchronous export jobs.

## Acceptance evidence

- ₹2,000 monthly + ₹1,000 quarterly + ₹25,000 annual reconciles to ₹53,000 for the configured calendar-year example.
- Tests cover fiscal boundaries, mid-year fee changes, custom months, one-time billing, leap years, month-end clipping and Sunday adjustment.
- Primary-group selection is effective on every occurrence and does not sum secondary memberships.
- Detail and export use the same calculation result and permission scope.
- Currency-separated totals and the non-invoice definition are always returned with a report.

## Explicit exclusions

Phase 8 does not create invoices, invoice numbers, GST calculations, receivables, payments, revenue journals, write-offs or projection snapshots. Workbook Billing MIS remains staged until Abhishek confirms legal billing-entity mappings, including the unresolved value `Cash`.
