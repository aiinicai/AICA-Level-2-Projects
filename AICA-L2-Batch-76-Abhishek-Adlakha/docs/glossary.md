# Domain Glossary

These terms are normative. API names, database names, UI labels and tests should use them consistently.

| Term | Meaning | Not the same as |
|---|---|---|
| Client | A person or legal entity for whom the CA firm performs work | Client group, GST registration, billing entity |
| Client category | Configurable legal constitution such as Individual, HUF or LLP | Service category |
| Client group | A reporting/relationship grouping containing one or more clients | One legal client; a billing entity |
| GST registration / GSTIN | One tax registration belonging to a client; a client may have zero-to-many | Client identifier or client itself |
| Service | Reusable catalogue definition such as GST Return or Audit | A dated work item |
| Client service agreement | Effective-dated configuration saying the firm performs one service for one client, optionally for one GSTIN | Service default, generated task or billing term |
| Task / work item | Actual unit of work, e.g. GST Return for ABC for July 2026 | Service definition or recurrence rule |
| Recurrence rule | Versioned rule that determines service periods and when tasks are generated | Billing schedule |
| Due-date policy | Deterministic rule calculating a task due date from a service period and holiday calendar | Task recurrence frequency |
| Task assignment | Effective/historical link between a task and an accountable employee | Team membership |
| Billing entity | Legal firm/entity through which a client service will be billed | Client, branch, person responsible, or payment mode such as Cash |
| Billing term | Effective-dated commercial terms for a client service and billing entity | Invoice or task recurrence |
| Billing schedule | Rule determining projected billing occurrences | Task generation schedule |
| Projection | Expected billing calculated from active terms/schedules for a horizon | Invoice, receivable, payment, revenue recognition |
| Employee | Staff/person record that can receive work | Login account |
| User | Login identity with sessions and roles; may link to an employee | Employee HR record |
| Role | Configurable collection of permissions | A hard-coded job designation |
| Permission | Stable action capability, optionally constrained to own/team/all scope | UI visibility alone |
| Deactivation | Reversible or controlled end of future operational eligibility with history retained | Physical deletion |
| Audit event | Append-only record of a business-significant change | Technical application log |
| Financial year | Indian financial year, provisionally 1 April–31 March | Calendar year |

