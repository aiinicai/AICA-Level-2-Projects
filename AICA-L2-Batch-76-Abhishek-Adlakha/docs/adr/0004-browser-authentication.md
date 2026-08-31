# ADR 0004: Browser Authentication

- Status: Accepted
- Date: 2026-08-19

## Decision

Use same-origin encrypted, Secure, HttpOnly cookie sessions with server-side revocation and antiforgery protection. Keep browser session secrets out of local storage.

## Alternatives

JWT bearer tokens in browser storage; implicit trust based on LAN/Windows login.

## Rationale and consequences

Cookies provide mature browser protection and revocation for the initial web client. State-changing requests need CSRF protection. Future mobile/client-portal clients may add standards-based OAuth/OIDC without changing the internal employee browser decision.

