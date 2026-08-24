# Architecture Decision Records

ADRs document decisions that should not be rediscovered during feature work.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith | Accepted |
| [0002](0002-central-postgresql.md) | Central PostgreSQL database with logical schemas | Accepted |
| [0003](0003-technology-stack.md) | .NET 10, React/TypeScript, PostgreSQL | Accepted |
| [0004](0004-browser-authentication.md) | Same-origin secure cookie authentication | Accepted |
| [0005](0005-authorization-model.md) | RBAC plus own/team/all scopes | Accepted |
| [0006](0006-service-client-service-task.md) | Separate service, client service and task | Accepted |
| [0007](0007-recurring-task-generation.md) | Versioned rolling recurrence generation | Accepted |
| [0008](0008-separate-work-and-billing-schedules.md) | Separate work recurrence and billing schedules | Accepted |
| [0009](0009-effective-dated-billing.md) | Effective-dated client-service billing terms | Accepted |
| [0010](0010-deactivation-not-deletion.md) | Deactivation and retained history | Accepted |
| [0011](0011-database-migrations.md) | Reviewed EF migrations and deployment artifacts | Accepted |
| [0012](0012-projection-is-not-invoice.md) | Projection is not an invoice ledger | Accepted |
| [0013](0013-cross-platform-deployment.md) | One container deployment for Windows and macOS access/hosting | Superseded for production by 0014 |
| [0014](0014-native-windows-server-2019-production.md) | Native Windows Server 2019 production without Hyper-V | Accepted |
| [0015](0015-mobile-identity-and-field-policies.md) | Mobile login, extensible roles and configurable field policies | Accepted |

Status changes or superseding decisions require a new ADR; do not rewrite accepted history to hide a change.
