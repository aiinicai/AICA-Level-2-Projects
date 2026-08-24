# ADR 0003: Technology Stack

- Status: Accepted
- Date: 2026-08-19

## Decision

Use .NET 10/ASP.NET Core, React 19 with strict TypeScript, PostgreSQL 18 and EF Core/Npgsql when persistence starts. Use REST/JSON and OpenAPI. Deploy versioned containers behind a reverse proxy.

## Alternatives

Django/PostgreSQL; NestJS/PostgreSQL.

## Rationale and consequences

The selected stack provides strong typing, mature security/data tooling and cross-platform LAN/cloud deployment. The team must maintain C# and TypeScript skills and pin/test dependencies. Phase 0 does not add EF/Npgsql because persistence begins in Phase 1.

