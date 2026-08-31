# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read `HANDOFF.md` first for current phase status, completed/incomplete features, known bugs, and the active development priority — this file does not repeat that. This file is the stable layer: commands, architecture, conventions, and rules that stay true across phases.

## Project

Centralized practice-management web app for a single Chartered Accountant firm (`README.md`). Modular monolith: one React SPA, one ASP.NET Core API, one background worker (same codebase, separate host), one PostgreSQL database with 11 logical schemas, one migrator executable, one admin CLI. Business chain: `Client → GST registrations/contacts/groups → Service catalogue → Client-Service Agreement → Recurrence rule + Billing term → Tasks → Assignments`.

## Development commands

Full local stack (Docker Compose) — macOS/Linux:

```bash
./deploy/scripts/practice.sh bootstrap   # first-time setup
./deploy/scripts/practice.sh verify      # full build + all test suites + frontend checks
./deploy/scripts/practice.sh start       # start stack
./deploy/scripts/practice.sh stop        # stop without deleting the DB volume
```

Windows equivalents are `deploy\scripts\practice.ps1` with the same subcommands. `make bootstrap|verify|dev|down` are macOS/Linux shortcuts over the same script.

Backend, run individually:

```bash
dotnet build PracticeManagement.slnx -c Release
dotnet run --project tests/<TestProject>/<TestProject>.csproj --configuration Release --no-build
```

Each of the eight test projects (`Practice.Architecture.Tests`, `Practice.Database.Tests`, `Practice.Identity.Tests`, `Practice.Scheduling.Tests`, `Practice.Billing.Tests`, `Practice.Reporting.Tests`, `Practice.WorkbookProfiler.Tests`, `Practice.Api.IntegrationTests`) is a single-file console `Program.cs` that runs top-to-bottom `Require(...)` assertions and returns a non-zero exit code on failure — not xUnit/NUnit. There is no test filtering/single-test-selection mechanism; running the project runs everything in it. Add new checks by appending `Require(...)` calls in the relevant project's `Program.cs`, matching existing style.

Frontend, from `web/`:

```bash
pnpm install --frozen-lockfile
pnpm dev      # Vite dev server, port 5173, proxies /api and /health to 127.0.0.1:5080
pnpm lint     # tsc -b --pretty false (typecheck only, no ESLint configured)
pnpm test     # node scripts/check-foundation.mjs — static grep-based smoke check, not a behavioral test runner
pnpm build    # tsc -b && vite build
```

Database:

```bash
./deploy/scripts/database.sh migrate
./deploy/scripts/database.sh backup
./deploy/scripts/database.sh verify-backup backups/<file>.dump
```

EF migrations are authored/applied through `Practice.Migrator`, never by API/worker startup — see Database rules below.

The API integration suite alone needs a disposable PostgreSQL database; `verify` provisions one automatically. To run it directly:

```bash
PRACTICE_TEST_DATABASE="Host=127.0.0.1;Port=5432;Database=throwaway;Username=u;Password=p" dotnet run --project tests/Practice.Api.IntegrationTests/Practice.Api.IntegrationTests.csproj -c Release --no-build
```

It migrates the target itself and refuses to run against a database that already has users, so never point it at the development volume.

## Architecture

- Endpoint modules live under `src/Practice.Api/{Identity,Audit,Clients,Services,Tasks,Scheduling,Billing,Reporting}/*Endpoints.cs`, mapped from the single composition root `src/Practice.Api/Program.cs`, which also owns cookie auth, all authorization policies, antiforgery, rate limiting, and health/diagnostics endpoints.
- `src/Practice.Database` holds the one `AppDbContext`, all 47 entities (`Entities/*.cs`, grouped by domain not 1:1 with schemas), seed data, and `Migrations/`.
- `src/Practice.Identity` is the only place session/credential/RBAC logic should live: `IdentityService` (login, session validate/revoke, password change, claims-principal construction), `CredentialRules`, `SessionCookieEvents` (reloads roles/permissions from Postgres on every request), `SessionToken`, `BootstrapAdministratorService`, `LocalAccountRecoveryService`.
- `src/Practice.Scheduling` and `src/Practice.Billing` are pure calculation libraries (recurrence dates, projection math) consumed by both the API and the worker — keep them free of EF/HTTP concerns so they stay independently testable.
- `src/Practice.Worker` is a separate host built from the same solution; it takes a PostgreSQL advisory lock before generating tasks so it can run alongside the API without duplicate generation.
- `web/src/app/App.tsx` (~450 lines) is intentionally the whole SPA today: types, fetch helpers, navigation, and every workspace/form. There is no router, query library, form library, or schema-validation library installed — don't assume React Router/TanStack Query/RHF/Zod exist just because `docs/architecture-blueprint.md` discusses them; check `web/package.json`.
- Scope enforcement (OWN/TEAM/ALL) is computed independently inside each endpoint module rather than through a shared middleware/interceptor. This is a known duplication (see `HANDOFF.md` §16) — do not "fix" it by unifying the logic without adding parity tests across every module first; a subtle behavior change here is a security regression, not a refactor.

## Coding conventions

- `Directory.Build.props`: `net10.0`, nullable reference types enabled, implicit usings enabled, **warnings treated as errors**, `AnalysisLevel=latest-recommended`. A change that introduces a new analyzer warning fails the build, not just CI.
- `.editorconfig`: 4-space indent for C#, 2-space for everything else, file-scoped namespaces required (`csharp_style_namespace_declarations = file_scoped:warning`), LF line endings, trailing newline required.
- Package versions are centrally managed in `Directory.Packages.props` (`ManagePackageVersionsCentrally=true`) — add new package versions there, not in individual `.csproj` files.
- Strict TypeScript (`web/tsconfig*.json`); `pnpm lint` is a typecheck, not a linter — there is no ESLint/Prettier config in this repo, so don't assume lint will catch style issues.
- Minimal API endpoint modules follow the existing pattern of static `Map*Endpoints(this WebApplication app)` extension methods per domain; new endpoints should follow the same file/naming convention as their sibling domain.

## Database rules

- PostgreSQL 18, EF Core 10, one `AppDbContext`, schema-qualified tables (`reference`, `system`, `audit`, `import`, `identity`, `employees`, `clients`, `services`, `tasks`, `scheduling`, `billing`).
- **Never edit an already-applied migration.** Add a new corrective migration and regenerate `AppDbContextModelSnapshot.cs` through EF tooling.
- **API and worker startup must never call `Database.Migrate()`.** Migrations are an explicit, privileged step run only through `Practice.Migrator`. Separate DB roles enforce this: the runtime role cannot alter schema.
- Audit events (`audit.audit_events`) and task status history (`tasks.task_status_history`) are append-only — enforced in `AppDbContext` (`SaveChanges` throws on `Modified`/`Deleted` state for these) and, for audit events only, also at the DB-role level. Task status history immutability currently relies on the application guard alone (DB role has broader DML on the `tasks` schema) — don't remove the `AppDbContext` check assuming the DB enforces it.
- Effective-dated/versioned entities (recurrence rules, billing terms) must never be mutated in place to change historical meaning — create a new version.
- Use deactivation (`IsActive`/status flags), not deletion, for clients, masters, and other business records with history.
- `timestamptz`/`DateTimeOffset` for instants; `date`/`DateOnly` for business dates. Money is `numeric(19,2)`; never use floating point for money. Currency totals must never aggregate across different currency codes.
- Business-date semantics are Asia/Kolkata with an Indian financial year starting 1 April; instants stay UTC. Preserve this distinction — don't collapse it to a single "server time."

## Authentication / authorization rules

- Same-origin encrypted cookie auth (`Practice.Session`, `__Host-` prefixed in production), HttpOnly, `SameSite=Strict`, 12h fixed expiry, no sliding renewal. Login identity is a normalized 10-digit Indian mobile number.
- Session tokens are random; only their SHA-256 hash is stored server-side (`identity.user_sessions.TokenHash`). Never store or log a raw session token.
- **Roles and permissions are reloaded from PostgreSQL on every authenticated request** (`SessionCookieEvents`) — the encrypted cookie intentionally carries only user id and session token, not roles/permissions, so a permission change or session revocation takes effect immediately rather than only after the cookie is reissued. Do not "optimize" this by trusting cached claims in the cookie across requests.
- Every business permission is its own ASP.NET authorization policy (`options.AddPolicy(permission, ...)` in `Program.cs`), keyed off a permission claim. **A new endpoint that needs authorization must both (a) be included in the permission-claim policy registration loop in `Program.cs` if it's a new permission code, and (b) actually call `.RequireAuthorization(...)` on its route mapping** — the policy existing is not sufficient by itself; `Program.cs` currently has at least one endpoint where the policy is registered but never applied (see `HANDOFF.md` known bugs).
- Scope ceilings are `OWN` / `TEAM` / `ALL`, merged across a user's roles to the widest grant (`ALL > TEAM > OWN`). Treat any scope-query change as security-sensitive: verify list, detail/direct-ID, mutation, and export paths together, not just the list view.
- Frontend permission checks (`web/src/app/App.tsx` navigation gating) are convenience only. The API is the sole authorization boundary — never rely on hiding a UI element as the actual control.
- CSRF: HttpOnly antiforgery cookie + `X-CSRF-TOKEN` header, required on all mutating endpoints. New mutating endpoints must opt in the same way existing ones do.
- Password changes, account state changes, and role/permission changes must revoke affected sessions (existing pattern in `IdentityService`) — preserve this when touching identity code.

## Important design decisions (see `docs/adr/` for full rationale — do not casually reverse)

- Modular monolith, not microservices; one centralized PostgreSQL database, not per-module databases.
- Browser-only clients (Windows/macOS) against one server deployment; no offline/local database story.
- Native Windows Server 2019 + IIS is the production target; Docker Compose is development/pilot only, not a production deployment model.
- Service definition, client-service agreement, and task are distinct entities with distinct lifecycles — do not merge them.
- Task recurrence and billing schedules are intentionally independent; a service can recur monthly but bill quarterly. Never make one derive from the other.
- Recurrence rules and billing terms are effective-dated/versioned. Billing projection is expected fee only — never treat it as an invoice, revenue, receivable, or payment record.
- Employee (employment identity) and login user (credential identity) are separate entities so employment survives login disablement.
- Source workbook `Clients List.xlsm` is read-only migration input: profiling/dry-run code must never modify it or execute its macros.

## Testing requirements

- Run `./deploy/scripts/practice.sh verify` (or the PowerShell equivalent) before considering backend or frontend work done — it builds Release, runs the seven console suites, provisions a throwaway PostgreSQL container and runs the API integration suite, then runs the frontend typecheck/smoke-check/build.
- The console suites are deterministic unit/rule-level checks (dates, money matrices, recurrence math, model shape). They do **not** host the API, authenticate cookies, exercise CSRF, or run EF queries against PostgreSQL. Translation failures and authorization gaps are invisible to them — that is how two report endpoints, seven list endpoints and the CSRF control all shipped broken.
- `tests/Practice.Api.IntegrationTests` is the suite that catches those. It boots the real API with `WebApplicationFactory` against a disposable PostgreSQL database (`PRACTICE_TEST_DATABASE`, which it migrates itself and which must contain no existing users). **Any change to an EF query, an endpoint signature, or an authorization rule should be verified there**, not only in the console suites.
- A required non-nullable query parameter on a Minimal API handler makes binding throw, which surfaces as HTTP 500 rather than 400. Prefer nullable query parameters with explicit defaults on list endpoints.
- `UseAntiforgery()` only records a validation failure in `IAntiforgeryValidationFeature`; it does not reject JSON requests on its own. `Program.cs` acts on that feature — do not remove it, or CSRF enforcement silently disappears for every JSON mutation.
- **OWN/TEAM/ALL means one thing everywhere.** TEAM reaches the teams an employee belongs to or personally manages, and stops there — it does not follow direct reports into unrelated teams. Six modules implement this separately (clients, services, billing, scheduling, reporting, and the calendar's assignment variant). If you change one, change them all and run the scope checks, which assert the modules agree.
- Audit history is append-only and the runtime DB role has only `SELECT, INSERT` on the `audit` schema. The retention job deliberately does **not** run on that role — it uses a separate `PracticeAuditMaintenance` connection given only to the worker. Do not grant the app role `DELETE` on audit to make something easier; that removes the guarantee that a compromised API cannot erase evidence. Retention archives expired rows to a file and deletes only after that file is written.
- Security headers (CSP and friends) are set in **two** places — `web/nginx.conf` for Compose and a middleware in `Program.cs` for the Windows/IIS path that serves the SPA from `wwwroot`. Update both, and re-check the app in a browser: `style-src` must keep `'unsafe-inline'` because status chips colour themselves through a `style` attribute.
- Any production bug fix should get a regression check added to the relevant console suite, following that suite's existing `Require(...)` style.
- Do not weaken authorization/scope logic or an append-only guard to make a test pass.

## Warnings for future development

1. The code is the authority for what exists. `docs/architecture-blueprint.md` describes some uninstalled libraries and unbuilt infrastructure (OpenAPI, React Router, TanStack Query, React Hook Form, Zod, xUnit, Testcontainers, Playwright, a `src/Modules` layout) — verify against `web/package.json` / `Directory.Packages.props` / actual folder structure before assuming any of it is present.
2. Never let API or worker startup call `Database.Migrate()`. Always add and review a migration through `Practice.Migrator` for schema changes.
3. Never edit an already-applied migration.
4. Do not expose or reproduce `.env` values, connection strings, password hashes, session tokens, client records, workbook contents, backups, or export files in logs, commits, or chat output.
5. Do not delete/recreate the Docker database volume to resolve connectivity issues without explicit owner authorization and a verified backup.
6. Treat any change to a permission/scope query as security-critical: test list, detail/direct-ID, mutation, and export paths together.
7. Keep UI-side permission checks as usability hints only; the enforcement boundary is the API.
8. Preserve effective-dated/versioned history for recurrence rules and billing terms — never mutate a prior version in place.
9. Never conflate task recurrence with billing schedules, or billing projection with an invoice/ledger/payment.
10. Do not seed a legal billing entity or map the workbook value `Cash` without explicit owner confirmation (see `docs/phase-0-decision-register.md`).
11. Do not auto-map ambiguous workbook people/categories during migration work; dry-run, reconcile, and get sign-off first.
12. Keep `.env`, `backups/`, `artifacts/`, `bin/`, `obj/`, `node_modules/`, and `web/dist/` out of commits.
13. `Clients List.xlsm` is confidential and is already tracked in git history — do not add further confidential data to source control, and flag rather than silently work around this existing exposure.
14. Windows Server production is native IIS/.NET/PostgreSQL — do not introduce Docker Desktop or Hyper-V dependencies for that host.
15. Read `docs/adr/` before proposing an architectural change; supersede a decision with a new ADR rather than silently diverging from an accepted one.
