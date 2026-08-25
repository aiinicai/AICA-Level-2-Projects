> **AICA Level 2 Capstone Project — Batch 76 — Abhishek Adlakha**
> Built with Claude Code (Anthropic) as the primary AI development tool, end to end: architecture,
> backend, frontend, database schema, security hardening and testing. See `CLAUDE.md` for the
> project's working conventions and `HANDOFF.md` for phase-by-phase development history.

# CA Firm Practice Management

Modular practice-management software for a Chartered Accountant firm. The repository is currently at **Phase 9: dashboards and MVP reports**. Audit, security and operational hardening remain in the next phase.

## Current deliverables

- ASP.NET Core API with secure mobile-number login, revocable server sessions, lockout and CSRF protection.
- React/TypeScript login and administration screens for employees, roles and mandatory-field policies.
- Client registry, GSTIN, service-agreement and scoped task workspaces.
- Manual tasks with primary/secondary assignments, controlled status transitions, comments and retained timelines.
- Recurrence worker, holiday-aware calendar and idempotent rolling task generation.
- Legal billing-entity master and versioned fixed-fee schedules independent from task recurrence.
- Deterministic expected-fee projections plus scoped operational dashboards and client/task reports with CSV/XLSX export.
- PostgreSQL 18 schemas for reference/system/audit/import, identity/employees, clients/services and tasks, with reviewed EF Core migrations.
- Six required default roles, administrator-created roles, action permissions and own/team/all scope ceilings.
- One-time secure bootstrap command for the first administrator, defaulting to Abhishek Adlakha.
- Separate fixed migration and runtime database roles; the API cannot alter schema or rewrite audit events.
- One-shot migration container plus cross-platform backup and isolated restore-verification scripts.
- Read-only `.xlsx`/`.xlsm` workbook profiler with duplicate and reference-matching reports.
- Architecture, database-model, profiler, frontend, CI, and strict compiler checks.
- Accepted technical ADRs and a business-decision register requiring owner confirmation.

The source workbook `Clients List.xlsm` remains read-only migration input. Client and service dry-runs stage proposals and exceptions but do not modify or automatically import the source.

## Supported platforms

Staff use the application through a current managed browser on **Windows or macOS**; nothing is installed on each staff computer. Docker Compose remains the development runtime on macOS and Windows workstations.

The adopted production target is **native Windows Server 2019 without Hyper-V**: IIS hosts the combined ASP.NET Core/React application, PostgreSQL runs as a native Windows service, and users connect through one internal HTTPS address. See [native Windows Server deployment](deploy/windows-server/README.md).

## Prerequisites

- .NET 10 SDK (the repository uses `global.json`).
- Node.js 24 and pnpm 11.
- Docker Engine with Compose v2 for the full local stack.

## Windows setup and operation

From PowerShell:

```powershell
.\deploy\scripts\practice.ps1 bootstrap
.\deploy\scripts\practice.ps1 verify
.\deploy\scripts\practice.ps1 start
```

## macOS setup and operation

```bash
./deploy/scripts/practice.sh bootstrap
./deploy/scripts/practice.sh verify
./deploy/scripts/practice.sh start
```

`make bootstrap`, `make verify`, `make dev`, and `make down` remain macOS/Linux shortcuts over the same script.

After startup, open `http://localhost:8088` on the host or `http://SERVER-LAN-IP:8088` from an authorized Windows or Mac computer. The API endpoints are `/api/v1/system/info`, `/health/live`, and `/health/ready` through the web proxy.

Stop the stack without deleting its database volume:

```powershell
.\deploy\scripts\practice.ps1 stop
```

or `./deploy/scripts/practice.sh stop` on macOS/Linux.

Do not reuse the example database password outside local development. See [cross-platform deployment](docs/operations/cross-platform-deployment.md), [development instructions](docs/development.md), [architecture blueprint](docs/architecture-blueprint.md), and [decision register](docs/phase-0-decision-register.md).

Database migration, backup/restore verification, and workbook profiling commands are documented in [database operations](docs/operations/database-operations.md).

## Phase boundary

Phase 9 provides scoped operational cards with matching drill-down records, client/task registers and deterministic billing projection reports. OWN/TEAM/ALL scope is enforced on the server and export scope can never exceed on-screen report visibility. Phase 10 is the next increment: audit UI, security and operational hardening. Invoices, receivables, payments and revenue recognition remain outside the MVP phase boundary.
