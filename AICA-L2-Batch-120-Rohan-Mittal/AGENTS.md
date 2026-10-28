## Architecture rules

- Balance math lives in pure integer-cent functions in src/lib/balanceEngine.ts — keeps splits penny-exact and testable.
- All writes to groups, members, expenses and settlements go through validated Firestore service functions in src/lib/fairlyshareDb.ts, protected and enforced by Firebase Firestore security rules (`firestore.rules`).
- Placeholder identities are claimed only with admin-issued, single-use, expiring personal links; the group invite link only adds new members — prevents impersonation.
- Signed-in pages live under src/routes/_authenticated (client-only gate, redirects to /auth?redirect=...) — preserves invite links through login.
- Service worker registers only via src/lib/pwa.ts guards (production, not preview/iframe) — avoids stale preview caches.
