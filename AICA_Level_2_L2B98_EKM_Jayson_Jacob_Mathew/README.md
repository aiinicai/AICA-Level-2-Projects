# DPDP Compliance Manager

A multi-institution web application that helps a school or college adopt the Digital Personal Data Protection Act, 2023 for the first time. It is run by a Chartered Accountant's firm for its institution clients.

Author: CA Jayson Jacob Mathew (Saju and Co.) | ICAI AICA Level 2 | Batch L2B98 EKM
Status: working prototype with synthetic data only. Not a certified compliance product.

## Problem
Institutions hold large volumes of student, parent and staff data, often in scattered systems, and have no structured way to find what they hold, judge which duties apply, assess controls, keep evidence and show who approved what.

## What it does
- Institution profile, departments, systems, vendors.
- Personal-data inventory (processing activities) with sensitive-data flags that prompt human review.
- Applicability questions with a written rationale and a "Needs legal review" outcome.
- Control library and item-by-item assessment (Implemented and verified, Implemented, Partial, Gap, Not applicable, Not assessed).
- Evidence kept in private storage; the uploader cannot verify their own evidence.
- Maker-checker approval: the preparer cannot approve their own assessment; approved assessments are frozen and reopening needs a reason.
- Corrective actions with owner, due date, overdue flag, closure evidence and risk acceptance.
- Dashboard and reports with numerator and denominator for every percentage. "Not assessed" is never counted as implemented.
- Audit trail that is append-only.

## Design decisions
- Tenant isolation is enforced in the database (row-level security), not only in the interface.
- State changes go through database functions, not direct updates.
- No Aadhaar storage. Money and legal dates are settings, not hard-coded. Legal content is marked "Requires verification" until a qualified person signs off.
- The words "compliant", "certified" and "guaranteed" are not used.

## Repository layout
| Folder | Contents |
|---|---|
| `database/` | `database_schema.sql`, `row_level_security.sql`, `seed_demo_data.sql` (run in this order) |
| `docs/` | screen map, data dictionary, test plan, build log |
| `tests/`, `tools/` | database test harness (225 tests) |
| `test_output/` | `rls_results.json` (225 passed, 0 failed) |
| `samples/` | synthetic CSV for inventory import testing and its checklist |
| `app/` | Lovable (TanStack Start, React, Supabase) front-end source |
| `user_manual/` | draft user manual |

## How it was built
Requirements and professional logic by the author (a practising CA). Database design, tests and prompts drafted with Claude (Anthropic); the interface was generated and revised with Lovable. All design decisions, legal logic and acceptance checks were reviewed by the author.

## Running the database
1. Create a Supabase (or Lovable Cloud) test project. Never use real data.
2. Run `database/database_schema.sql`, then `database/row_level_security.sql`, then `database/seed_demo_data.sql`.
3. Create a user in Authentication and add a row in `tenant_memberships` linking it to a demo institution.

## Running the database tests
```
cd tools && npm install
node tools/apply.mjs tests/supabase_stubs.sql database/database_schema.sql database/row_level_security.sql database/seed_demo_data.sql
node tools/run_rls_tests.mjs
```
Result recorded: 225 passed, 0 failed (see `test_output/rls_results.json`). One isolation condition was removed on purpose to prove the tests can fail; 28 tests then failed.

## What the tests do not prove
They run on an in-process PostgreSQL stand-in, not on Supabase. They do not prove JWT handling, storage behaviour, signed links or the invitation flow. Manual tests M1 to M13 in `docs/TEST_PLAN.md` are still to be run on the real project.

## Limitations and next steps
- Sign-in and database-backed screens are being connected (Phase 1); remaining workflow phases follow.
- Legal controls and statutory dates are demonstration content and must be verified against the Act, the Rules and Gazette notifications by a qualified person.
- Independent security review, backup and restore test, and accessibility audit are pending.
- The app records an assessment. It does not certify compliance or give legal advice.

## Security
No keys, passwords or `.env` files are stored in this repository. The browser uses only the public anon key. The service-role key must never be committed.
