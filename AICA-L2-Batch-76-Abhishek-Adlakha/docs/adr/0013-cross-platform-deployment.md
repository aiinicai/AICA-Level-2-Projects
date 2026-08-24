# ADR 0013: Cross-Platform Deployment

- Status: Superseded by ADR 0014
- Date: 2026-08-20

## Decision

Ship one multi-architecture container deployment for PostgreSQL, API and web. Staff use the application through a supported browser on Windows or macOS. Operators receive equivalent PowerShell and POSIX lifecycle commands that invoke the same Compose file, environment contract and images.

Development and pilot hosting support Docker Desktop on Windows 11 and macOS, including Apple silicon. The recommended always-on production runtime is Docker Engine on a supported Linux host or Linux VM. That VM may be hosted by a Windows or Mac office server, preserving a single release artifact and operating model.

## Alternatives

Separate Windows and macOS application builds; native PostgreSQL/.NET/Nginx installation on every supported host; desktop applications installed on each staff computer.

## Rationale and consequences

A browser client and multi-architecture Linux containers remove OS-specific business code and installer drift. Windows and Mac remain first-class access and administration platforms, while production services use a predictable server runtime.

Docker Desktop licensing, automatic-start and uptime suitability must be checked before using a Windows or Mac workstation as an always-on server. Native Windows Service and macOS `launchd` packages are not maintained in MVP; adding them would create separate operational/test matrices and requires a new decision.

ADR 0014 records the owner-approved change to native Windows Server 2019 production hosting. This ADR remains the historical basis for cross-platform browser access and Docker-based development.
