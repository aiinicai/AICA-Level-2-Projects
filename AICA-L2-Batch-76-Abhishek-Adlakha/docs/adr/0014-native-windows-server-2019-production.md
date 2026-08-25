# ADR 0014: Native Windows Server 2019 Production

- Status: Accepted
- Date: 2026-08-20
- Supersedes: ADR 0013 for production hosting only

## Decision

Use a fully patched Windows Server 2019 machine as the production host without Hyper-V. IIS with the .NET 10 Hosting Bundle serves the combined React and ASP.NET Core application over HTTPS. PostgreSQL runs natively as an automatically started Windows service. Reviewed EF migrations run as a separate deployment step using a migration-owner login; the application uses a restricted DML login.

Docker Compose remains supported for development on macOS and Windows workstations. Staff on Windows and macOS use a browser and the same internal HTTPS URL; no staff-side application or database is installed.

## Rationale

The available production server is Windows Server 2019 and Hyper-V is not available. Docker Desktop is not a supported Windows Server production runtime. Native IIS and PostgreSQL avoid a virtualization dependency while retaining the same .NET application, React build and relational schema.

## Consequences

Release testing has two runtime lanes: Compose for development/integration and a `win-x64` IIS package for production. Phase 11 must prove HTTPS, service restart, PostgreSQL backup/restore, least-privilege ACLs, update and rollback on a representative Windows Server 2019 host. Windows Server, IIS, .NET Hosting Bundle and PostgreSQL patching become explicit operating responsibilities.
