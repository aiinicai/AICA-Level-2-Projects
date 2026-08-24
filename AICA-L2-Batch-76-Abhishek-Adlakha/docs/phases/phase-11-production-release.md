# Phase 11 — Production release, data import and commissioning

Phase 11 is mostly operational rather than software. It has three independent tracks, and only one
of them can progress without the product owner or the production hardware.

| Track | Status | Blocked by |
|---|---|---|
| Backup, restore and rollback rehearsal | **Drill passed locally** | Nothing for the local drill; production drill needs the server |
| Workbook cleansing and production import | **Clients imported**; services and billing outstanding | BIZ-009 for billing; BIZ-005 deferred to in-app mapping |
| Windows Server 2019 commissioning, UAT, training | Not started | Access to the production host |

## 1. Backup and restore drill

Performed 2026-08-21 against the local Compose stack.

Method: `deploy/scripts/database.sh backup`, then a restore into a throwaway database on the same
server, comparing business row counts before and after rather than only checking that tables exist.

| Table | Live | Restored |
|---|---|---|
| `clients.clients` | 1 | 1 |
| `services.client_services` | 1 | 1 |
| `tasks.tasks` | 0 | 0 |
| `identity.users` | 2 | 2 |
| `audit.audit_events` | 22 | 22 |
| `scheduling.recurrence_rules` | 0 | 0 |

Password hashes survived the round trip, so users can still authenticate against a restored copy.

Limits of this evidence, which must not be overstated:

- It was taken against a nearly empty development database. It proves the mechanism, not the
  duration or reliability of a restore at production volume.
- `verify-backup` only counts tables in four schemas. The fuller comparison above was run by hand.
- No off-server copy, no encryption at rest for the dump, and no rollback-after-failed-upgrade
  rehearsal yet. All three are required before go-live.
- Audit archive files produced by retention are **not** covered by this backup. They live in the
  `practice-audit-archive` volume and hold history that has been removed from the database.

## 2. Client import — completed 2026-08-21

The client import ran against the live development database after the owner confirmed the single
pre-existing client was test data. That client and its one agreement, contact and address were
removed first; a backup was taken and restore-verified beforehand
(`practice-management-20260821T103616Z.dump`), and again afterwards
(`practice-management-20260821T103720Z.dump`).

Result: 511 workbook rows became **493 clients** with **107 GST registrations**, recorded under
import run `a669524f-6357-4945-ae7c-a9c4afc5588a` with 493 per-client results and zero issues.

| Check | Result |
|---|---|
| Clients without a category | 0 |
| Duplicate client codes | 0 |
| Clients with two primary GSTINs | 0 |
| Clients holding several state registrations | 8 |
| Clients merged from multiple rows | 12 |
| Clients retaining a previous name in notes | 7 |

Category split: Individual 373, Private Limited 38, LLP 34, Partnership 25, HUF 17, Trust 5,
One Person Company 1.

Re-running the importer against the same workbook is refused, because the source SHA-256 is already
recorded against a completed run.

## 3. Remaining import work

Source: `Clients List.xlsm`, sheet `Master Data`, SHA-256
`37e80309f683678c3466a7480fa6c01639699259a43fc9e81a443424eca0f0ac`, 511 rows.

Read-only dry runs were executed; the workbook was not modified. Full detail is written to
`artifacts/client-dry-run.json` and `artifacts/service-dry-run.json`, which are git-ignored because
they contain client data.

### Clients

| Outcome | Rows |
|---|---|
| Ready to import | 449 |
| Held as exceptions | 62 |

| Exception | Rows | Decision |
|---|---|---|
| `AMBIGUOUS_FIRM` | 31 | BIZ-004 |
| `DUPLICATE_TAX_ID` | 30 | BIZ-003 |
| `DUPLICATE_LEGACY_CODE` | 12 | BIZ-003 |
| `UNMAPPED_CATEGORY` | 1 | BIZ-004 |

Source categories present: INDIVIDUAL 370, PVT LTD 50, FIRM 31, LLP 30, HUF 17, TRUST 5, OPC 1,
blank 7.

### Services and agreements

1,167 agreements proposed across 21 distinct services; 1,156 ready, 11 held as
`GSTIN_SCOPE_REQUIRED`. 40 ownership references across `Accountant` (20), `ITR Data` (16) and
`Leader` (4) do not resolve to an employee, covering **24 distinct people** who must be mapped to
employee records before import (BIZ-005).

### What is still missing

There is no production importer. The dry-run services stage proposals and exceptions but nothing
writes them into the live schema. Building it is straightforward once the decisions below are made,
and it must not be built before them: the mappings are inputs to the importer, not afterthoughts.

## 4. Decisions still blocking the remaining import

| ID | Question | Rows affected |
|---|---|---|
| BIZ-004 | What does the category `Firm` mean — Partnership, Proprietorship or something else? | 31 (+1 unmapped) |
| BIZ-003 | Are the duplicate PAN/GSTIN and legacy-code rows genuine separate clients, or the same client entered twice? | 42 |
| BIZ-005 | Which employee does each of the 24 unresolved names refer to? | 40 references |
| BIZ-009 | Confirm `Cash` is a payment mode, not a legal billing entity, and name the real billing entities | Billing setup |

BIZ-011 (RPO 24 hours, RTO 4 hours) and BIZ-006 (Saturday working policy) remain at their
recommended defaults and should be confirmed rather than assumed before go-live.

## 5. Not yet started

Windows Server 2019 commissioning, certificate and DNS validation, service recovery behaviour,
signed package approval, update and rollback rehearsal, performance testing at the documented
2,000-client scale, UAT and administrator training. All need the production host or the firm's
staff, and none can be completed from a development machine.
