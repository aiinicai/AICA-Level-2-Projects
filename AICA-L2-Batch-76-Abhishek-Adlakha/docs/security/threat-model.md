# Phase 0 Threat Model

## Scope and trust boundaries

Browser → LAN/TLS reverse proxy → API → PostgreSQL is the primary trust path. The worker is another privileged application process. Backups, deployment artifacts and future exports cross storage boundaries. The LAN is not trusted merely because it is internal.

## Assets

Client identity/tax data, task and billing records, credentials/sessions, role assignments, audit history, backups, source/release artifacts and availability during working hours.

## Priority threats and controls

| Threat | Initial control |
|---|---|
| Stolen/replayed browser session | Secure HttpOnly same-origin cookie, finite session, server revocation, security stamp, TLS |
| Horizontal/vertical privilege escalation | Permission policy plus own/team/all query scope in server application layer; direct-ID denial tests |
| CSRF/XSS | Antiforgery on state changes, output encoding, CSP/security headers, no token in local storage |
| SQL injection/mass assignment | Parameterized EF/allow-listed SQL, explicit request DTOs, bounded filters/sorts |
| Password guessing/account enumeration | Adaptive password hashing, rate limit/lockout, generic login response, safe audit |
| Malicious/accidental bulk action | Permission, limits, preview, reason, optimistic concurrency and audit |
| Recurrence duplicate/corruption | Persisted job, advisory lock, immutable occurrence key, unique constraint, idempotency tests |
| Backup theft/ransomware | Encryption, off-machine/immutable copy, separate credentials and restore tests |
| Insider reading exported data | Scoped report query, separate export permission, export audit, retention/secure download |
| Dependency/supply-chain compromise | Pinned lockfiles, trusted registries, CI scan, reviewed upgrades, immutable release artifacts |
| Server or disk failure | Health/restart policy, UPS, backup/recovery runbook and later PITR if RPO demands |
| Sensitive data in logs/errors | Structured allow-list logging, Problem Details, trace ID, no stack/SQL/secrets to client |

## Deferred threat-model extensions

Client portal, remote access/VPN, messaging, documents, external integrations, mobile apps and AI each require a dedicated review before implementation. Their absence in Phase 0 is a security boundary, not missing functionality.

