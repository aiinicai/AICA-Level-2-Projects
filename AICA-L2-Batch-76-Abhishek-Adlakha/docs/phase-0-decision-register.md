# Phase 0 Business Decision Register

Technical ADRs are accepted as the starting baseline because Phase 0 was authorized. The following business decisions still require the product owner’s explicit confirmation before their dependent phase begins.

| ID | Decision needed | Recommended default | Required before |
|---|---|---|---|
| BIZ-001 | Reporting year | Indian financial year (1 April–31 March), plus optional calendar filters | Phase 3 reports |
| BIZ-002 | Group membership | Multiple groups allowed; one optional PRIMARY group used for non-duplicating financial totals | Phase 3 |
| BIZ-005 | Employee name ownership | Named business owner resolves Accountant/Leader/ITR Data variants to employee codes | Phase 4 import — **deferred by owner**: clients import first, the 24 names are mapped in the application afterwards |
| BIZ-006 | Saturday/holiday policy | Configurable holiday calendars; Sunday off; Saturday rule to be confirmed | Phase 6 |
| BIZ-007 | Reopen completed/cancelled task | Manager or explicit permission, mandatory reason, audit every transition | Phase 5 |
| BIZ-008 | Projection meaning | Expected fee in scheduled billing month, exclusive of GST; not invoice/revenue | Phase 7 |
| BIZ-009 | Billing entity `Cash` | Treat as unresolved/payment-mode placeholder, not a legal billing entity | Phase 7 import |
| BIZ-010 | Billing splits | One billing entity per active client-service term; split allocations deferred | Phase 7 |
| BIZ-011 | Recovery targets | RPO 24 hours, RTO 4 hours initially | Production release |
| BIZ-013 | Audit retention | Seven financial years plus current year, subject to CA/legal retention advice | Phase 10 |

> **BIZ-013 needs re-confirmation.** On 2026-08-21 the owner chose three months in the database
> (twelve for security actions), and that is what is implemented. The recommendation in this
> register was seven financial years plus the current year, subject to CA and legal retention
> advice, so the chosen value is materially shorter than the default this project recorded.
> History is not destroyed: expired rows are written to archive files before deletion, so the
> effective retention is as long as those archives are kept — but the archives are not yet rotated,
> encrypted or copied off the server. Confirm the three-month figure against the firm's actual
> retention obligations, and either record it as a signed decision or raise it.
| BIZ-014 | MVP statutory services | Start with only services whose period/due rules have named business test cases | Phase 6 |

Record confirmation by changing a row to an ADR or signed product decision; do not silently remove it from this register.

## Confirmed decisions

| ID | Confirmed decision | Date |
|---|---|---|
| BIZ-012 | Windows and macOS staff access one centrally hosted application in a browser. Docker Compose is the development runtime; production uses native IIS/.NET and PostgreSQL on Windows Server 2019 without Hyper-V. | 2026-08-20 |
| BIZ-015 | Employee login username is the normalized 10-digit Indian mobile number. | 2026-08-20 |
| BIZ-016 | Default roles are Administrators, Manager, Articles, Paid Assistants, Accountants and Client Accountants; administrators may add roles. | 2026-08-20 |
| BIZ-017 | Administrators configure registered fields as mandatory/optional, except system-required invariants. | 2026-08-20 |
| BIZ-018 | Abhishek Adlakha is the first system administrator; mobile and password are supplied only through local secure bootstrap. | 2026-08-20 |
| BIZ-004 | Workbook category `Firm` means Partnership Firm. A name containing `LLP` is a Limited Liability Partnership; a name containing `OPC` is a One Person Company. A row with no category becomes Individual. | 2026-08-21 |
| BIZ-003 | Rows sharing a PAN are the same client — either the name changed or the business is GST-registered in several states — and merge into one client holding every GSTIN, keeping the later name and recording the earlier one. Rows sharing only an old code but having different PANs are different clients and are both kept. | 2026-08-21 |
| BIZ-019 | The production host is Windows Server 2019 using native IIS/.NET/PostgreSQL and no Hyper-V. | 2026-08-20 |
