# Test plan

Covers functional and cross-tenant security testing for the DPDP Compliance Manager database layer, and the manual tests that automation cannot prove.

## 1. What has been tested and how

The SQL files were loaded into PostgreSQL 16.4 (PGlite, an in-process build) with stand-ins for Supabase's `auth` and `storage` schemas (`tests/supabase_stubs.sql`). Then `tools/run_rls_tests.mjs` ran **225 automated tests** as 18 different personas plus anonymous and the service role. Result at the time of writing: **225 passed, 0 failed** (`tests/rls_results.json`).

Two defects were found and fixed by this process: functions created after the initial revoke were executable by the anonymous role (fixed in section 9 of `row_level_security.sql`), and one test expectation was wrong about who may verify evidence (design confirmed: only firm reviewers verify, and never the uploader).

To show the suite can fail, one isolation condition was removed from `tenant_can()` on purpose. Twenty-eight tests failed. The condition was restored.

**What this does not prove.** PGlite is not Supabase. The tests prove that the policy logic, grants, triggers and constraints behave as designed. They do not prove Supabase's JWT handling, PostgREST behaviour, Storage service, signed URLs, Auth invitation flow or Edge Functions. Re-run the same suite on a real Supabase test project (section 5) before any real data enters, and obtain an independent security review (section 6).

Run it yourself:

```
cd tools && npm install
node tools/apply.mjs tests/supabase_stubs.sql sql/database_schema.sql sql/row_level_security.sql sql/seed_demo_data.sql
node tools/run_rls_tests.mjs
```

## 2. Test personas (all synthetic)

| Key | Who | Where |
|---|---|---|
| `pa` | Platform administrator | Platform only. No automatic access to client content. |
| `fa1` | Firm 1 administrator | Firm 1. No engagement assignment. |
| `tm1` | Firm 1 consultant | Assigned to the school. |
| `rv1` | Firm 1 reviewer | Assigned to the school and the college. |
| `tm_un` | Firm 1 consultant | Not assigned anywhere. |
| `fa2`, `tm2` | Firm 2 administrator and consultant | Firm 2 and the institute. |
| `a_admin`, `a_lead`, `a_coord`, `a_evid`, `a_view`, `a_rev` | School: client admin, privacy lead, department coordinator, evidence contributor, management viewer, client reviewer | School (tenant A). |
| `a_old` | Former school privacy lead | Disabled membership. |
| `b_admin`, `b_lead` | College client admin, privacy lead | College (tenant B). |
| `c_admin` | Institute client admin | Institute (tenant C, Firm 2). |
| `outsider` | Signed in, no membership | Nowhere. |

Tenants: A school and B college (Firm 1), C institute (Firm 2).

## 3. Automated tests by area

| Area | IDs | What they prove |
|---|---|---|
| Visibility | `VIS-001` onward | Row counts per persona and table. Client users see only their tenant. Disabled member sees nothing. Firm admin without assignment sees engagement metadata but zero client content. Consultant sees only assigned clients. Firm-only notes, draft assessments, unshared reports, unapproved control versions and other firms' libraries are hidden from the people who should not see them. Audit log is visible only to roles with `view_audit`. Platform admin has no content access. |
| Anonymous | `ANON-*` | Anonymous cannot read any tested table and cannot call any RPC or `app_private` function. |
| Writes refused | `DENY-001` onward | Cross-tenant insert, update, move and delete fail. Role limits (viewer, reviewer, contributor, coordinator) hold. Self-escalation to administrator fails. Audit, review decisions and snapshots cannot be edited or deleted, even by the service role. Direct writes to status fields fail. Approved library items and approved assessments are immutable. `tenant_id` cannot change. Composite foreign keys block cross-tenant links. CHECK rules reject invalid combinations. |
| Writes allowed | `ALLOW-*`, `TEN-edit` | The permitted writes still work, so refusals are not caused by a broken setup. |
| RPCs and state machine | `RPC-*`, `ACT-*`, `LIB-*` | Submit and approve assessments, maker-checker (preparer cannot approve own work), reopen raises version, closed assessment is frozen, action transitions and closure evidence, risk acceptance needs rationale, library approval needs a different person and a verified source. |
| Evidence | `EVD-*` | Upload confirmation needs the file to exist, records the uploader from the session, rejects bad file types, cannot be re-run, and the uploader cannot verify their own evidence. Client roles cannot verify. |
| Dashboard | `DSH-*` | `dashboard_metrics` and `my_tenants` refuse other tenants. |
| Structure | `STR-*` | RLS is on for every public table and every one has a policy. Every table without `tenant_id` is a known global or identity table. Anonymous holds no table or function privilege. DELETE is granted only on working tables. Every SECURITY DEFINER function pins `search_path`. The evidence bucket is private and size-limited. Seed tenants are all demo, and seed users have no passwords. |
| Storage policies | `STO-*` | Object read follows the evidence row's own access. Upload only to a waiting row's exact path by a person allowed to upload. No rename or delete. |
| Escalation | `ESC-*` | A client administrator can change roles in their tenant. A viewer cannot promote self. Users edit only their own profile. |

The full list with pass or fail is in `tests/rls_results.json`.

## 4. Functional acceptance mapping (Spec section 14)

| # | Acceptance criterion | Evidence | Status |
|---|---|---|---|
| 1 | Sign in, access only permitted workspaces | `VIS-*`, `ANON-*`; sign-in itself needs the real app | Partly automated. Manual M1. |
| 2 | Firm admin creates tenant and assigns users | `ALLOW` firm admin creates tenant; invitations need an Edge Function | Partly. Manual M2. |
| 3 | Client A cannot read or modify Client B through UI or direct API | `VIS-*`, `DENY-*` at database level | Database proven. Manual M3 (direct API calls with a real JWT). |
| 4 | No membership means no tenant access | outsider and `a_old` visibility tests | Automated. |
| 5 | Inventory create, edit, search, retrieve | `ALLOW` inventory writes; UI not built | Database ready. UI test pending. |
| 6 | Assessment keeps control version and period | schema: items point at a version id, assessment has period; `RPC-10` | Automated for storage. UI pending. |
| 7 | Not Assessed not counted as compliant | `DSH-*` data shape; check metric definition in manual M8 | Manual M8 required to confirm the query text. |
| 8 | Actions track owner, due date, closure evidence | `ACT-*` | Automated. |
| 9 | Reviewer decisions record who, when, why | `RPC-05`, `review_decisions` immutability | Automated. |
| 10 | Evidence stored privately, unauthorized downloads fail | `STO-*` logic | Policy proven. Manual M4, M5 on real Supabase. |
| 11 | CSV/report exports tenant-scoped | RLS limits rows; `log_export` exists | Manual M7 once the export is built. |
| 12 | Important changes auditable | audit triggers on 19 tables; audit immutability tests | Automated for database changes. |
| 13 | Backup and restore tested | not testable here | Manual M9. |
| 14 | No critical tenant-isolation defect | 225 tests pass | Not closed until M3 and independent review. |
| 15 | Legal metadata verified by authorized reviewer | gate in database; demo records bypass it deliberately | Manual M10. |
| 16 | Manual explains limits | not written | Open. |

## 5. Manual tests on a real Supabase test project

Use a project that never holds real data.

| ID | Test | Pass condition |
|---|---|---|
| M1 | Sign in as each persona through the real Auth flow. | The workspace list matches section 2. A user with no membership sees "No access". |
| M2 | Firm admin invites a client admin through the Edge Function. | Invitation email arrives, link works once, profile and membership are created. The service-role key appears nowhere in the browser bundle (search the built files and network tab). |
| M3 | With a real access token for a School user, call the REST API directly (`/rest/v1/processing_activities?tenant_id=eq.{college}`; PATCH and DELETE on college ids; RPCs with college ids). | Empty results or errors every time. Repeat as Firm 2 user against school ids. Repeat with the anon key and no token. |
| M4 | Upload evidence via the real Storage API, then try to read the object with a College user's token and with a signed URL after expiry. | College user fails. Expired URL fails. Signed URL lifetime is short (five minutes or less). |
| M5 | Try uploading a file of a disallowed type, over 25 MB, and with a path whose tenant folder is another tenant. | All refused by Storage. |
| M6 | Disable a member, then use their still-valid token. | Access stops at once (policies check membership status on every request). |
| M7 | Export CSVs as users of different tenants. | Each file contains only that tenant's rows; row count equals the audit entry. |
| M8 | Read the `dashboard_metrics` SQL. | `not_assessed` is reported separately and excluded from "implemented"; percentages show numerator and denominator. |
| M9 | Backup and restore into a new project; run the full automated suite against the restored database. | All tests pass. Time to restore and data loss window are recorded. |
| M10 | Replace demo legal records with real controls. A reviewer verifies each against the Gazette or official text and records commencement status. | No non-demo approved record has "Requires Verification" unless the firm has chosen to show it with that label. |
| M11 | Upload a test file containing the EICAR test string. | Storage has no malware scanning by default. Record the result and decide on a scanning step before real evidence. |
| M12 | Try SQL injection strings and script tags in free-text fields. | Stored as text; displayed escaped; no script runs. |
| M13 | Keyboard-only and screen-reader pass of each screen; 200 percent zoom; phone width. | All actions reachable; badges readable without colour; no horizontal scroll. |

## 6. Independent review before real data

A person other than the author reviews: the policies in `row_level_security.sql`, every SECURITY DEFINER function, the storage policies, the Edge Function for invitations, the front-end bundle (for secrets), Supabase project settings (email confirmation, password rules, leaked-password protection, multi-factor authentication for firm users, disabled public sign-up, network restrictions, log retention), and the data processing and hosting arrangements. Record findings in `BUILD_LOG.md`. No unresolved critical finding may remain.

## 7. Regression rule

Every change to a table, policy, function or grant re-runs `tools/run_rls_tests.mjs`. A change that adds a table adds at least: an anonymous refusal test, an other-tenant refusal test and a role-limit test.

## 8. Known gaps and limits

- Session-length, rate-limit and brute-force behaviour belong to Supabase Auth and are untested here.
- The data-protection obligations of the platform itself as a processor of client data are outside this test plan.
- Statutory dates and section references in the demo library are placeholders and unverified.
- Notifications are rows only; delivery is untested.
- Performance with large tenants is untested. Policies call helper functions per row; indexes exist on `tenant_id`, but run `EXPLAIN` on the real database with realistic volumes (several thousand activities, tens of thousands of audit rows) before the pilot.
