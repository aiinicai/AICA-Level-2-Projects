# Phase 2 Completion Record

Date: 2026-08-20  
Status: Implemented and locally verified; real administrator activation requires Abhishek Adlakha to enter his mobile number and password locally.

## Delivered

- Login users separated from employee records; normalized 10-digit Indian mobile username.
- ASP.NET Core password hashing, generic login failure, five-attempt/15-minute lockout, 12-hour non-sliding sessions, hashed server-side session tokens and security-stamp revocation.
- Same-origin `HttpOnly`/`SameSite=Strict` cookie, antiforgery tokens on mutations and login rate limiting.
- One-time administrator bootstrap CLI with no default credentials; default name `Abhishek Adlakha`.
- Local audited password-recovery CLI with double-entry confirmation and session revocation.
- Exact default roles: Administrators, Manager, Articles, Paid Assistants, Accountants and Client Accountants.
- Twenty-two action permissions, own/team/all scope ceilings, protected full-access Administrators role, administrator-created roles and editable access assignments.
- Employee/login creation with temporary password and mandatory change on first login; account enable/disable protections and session revocation.
- Teams/team-membership persistence and administration API foundation.
- Administrator-controlled mandatory-field policies with database enforcement that system-required fields cannot become optional. Employee fields are registered now; Client and Task fields are registered by their owning future phases.
- Append-only audit events for bootstrap, login, password, employee, role, user-status, team and field-policy changes.
- Responsive login and administration UI for employees, roles/permissions and field policies.
- Forward-only EF migration `20260820113450_AddIdentityAccessAndFieldPolicies` with least-privilege `practice_app` grants.

## Native Windows Server 2019 production decision

ADR 0014 supersedes the production-host portion of ADR 0013. Development continues through Docker Compose on macOS/Windows. Production is a `win-x64` release under IIS and the .NET 10 Hosting Bundle, with native PostgreSQL as a Windows service, HTTPS, persisted data-protection keys and no Hyper-V or Docker Desktop dependency.

Phase 2 adds the release builder and installation baseline under `deploy/windows-server`. Phase 11 still owns production commissioning: approved certificates/DNS, service recovery, signed packages/checksums, scheduled backup/restore drill, rollback and UAT on the actual server.

## Verification evidence

| Check | Result |
|---|---|
| Release build with warnings as errors | Passed, 12 projects, 0 warnings/errors |
| Architecture checks | Passed |
| Database model/seed/invariant checks | Passed: 18 entities, 6 schemas, 6 roles, 22 permissions, 7 field policies |
| Credential/session-token checks | Passed |
| Workbook source/profiler regression | Passed; source workbook remains read-only |
| React/TypeScript lint, test and production build | Passed |
| Forward migration over existing Phase 1 database | Passed; both migrations applied |
| Second migration application | Passed; zero pending migrations |
| Runtime database privileges | Passed: DML/USAGE allowed; schema CREATE denied to `practice_app` |
| Live API diagnostics | Passed: Phase 2, healthy database, 36 India state/UT rows |
| Isolated bootstrap and mobile login | Passed in disposable `practice_phase2_verification` database |
| Custom role and field-policy mutations | Passed with antiforgery protection |
| Logout/session revocation | Passed; reused cookie returned 401 |
| Disposable verification data | Removed after testing |
| Native Windows package script execution | Deferred to Windows CI/Windows host; PowerShell is unavailable on the development Mac |

## Activate the real development administrator

The real database intentionally has zero users. From the project root in a terminal (not chat), run:

```bash
docker compose --env-file .env -f deploy/compose/compose.yml --profile admin run --rm admin \
  bootstrap-admin --mobile YOUR_10_DIGIT_MOBILE --name "Abhishek Adlakha"
```

Enter the password at the hidden prompt. Use at least 12 characters and do not include the mobile number. Then open `http://localhost:8088` and sign in. Production bootstrap is documented separately in `deploy/windows-server/README.md`.

## Phase boundary

No Client, GSTIN, Service, Task or Billing business table/CRUD was added. Phase 3 may now implement the client registry, groups, GSTINs and controlled workbook import. Service agreements remain Phase 4; tasks remain Phase 5.
