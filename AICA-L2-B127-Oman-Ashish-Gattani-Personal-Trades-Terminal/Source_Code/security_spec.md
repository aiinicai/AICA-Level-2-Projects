# ArthaTerminal Security Specification (Phase 0 TDD)

## 1. Data Invariants
1. **Strict Owner Isolation (PII Protection)**: `/users/{userId}` contains `email` and personal trading preferences. Only the verified authenticated owner (`request.auth.uid == userId`) can read or write their profile. Listing `/users` is globally denied (`allow list: if false`).
2. **Master Gate Parent Existence**: Every subcollection write (`holdings`, `savedScans`, `customIndicators`, `alerts`) under `/users/{userId}` requires the parent `/users/{userId}` document to exist with `uid == request.auth.uid`.
3. **Immutable Ownership & Temporal Integrity**: `uid` / `userId` and `createdAt` can never be mutated after creation. `createdAt == request.time` on create; `updatedAt == request.time` on create and update.
4. **Verified Identity for Writes**: All write operations mandate `request.auth.token.email_verified == true`.
5. **Bounded Arrays & Strict String Lengths**: `watchlist` is strictly bounded to `<= 60` items; every string enforces explicit `.size()` bounds and regex pattern validation on IDs and tickers.
6. **Zero Shadow Fields**: All creates enforce `keys().hasAll(...) && keys().hasOnly(...)`; all updates use action-based `affectedKeys().hasOnly(...)` wrapped by `isValid[Entity](incoming())`.

## 2. The "Dirty Dozen" Attack Payloads (All Must Return PERMISSION_DENIED)
1. **Unauthenticated Profile Read**: `GET /users/userA` with `auth = null`.
2. **Cross-User PII Leak**: `GET /users/userA` authenticated as `userB`.
3. **Directory Enumeration (List Users)**: `LIST /users` authenticated as `userA`.
4. **Shadow Field Injection on Profile**: `CREATE /users/userA` with valid fields + `isAdmin: true`.
5. **Email Unverified Write Spoof**: `CREATE /users/userA` where `auth.uid == 'userA'` but `auth.token.email_verified == false`.
6. **Backdated Timestamp Spoof**: `CREATE /users/userA/holdings/h1` with client-forged `createdAt` != `request.time`.
7. **Immutable Owner Tampering**: `UPDATE /users/userA/holdings/h1` changing `userId` from `userA` to `userB`.
8. **ID Poisoning (Denial of Wallet)**: `CREATE /users/userA/holdings/<200-char-invalid-id!@#>` with malformed document ID.
9. **Watchlist Array Flood**: `UPDATE /users/userA` setting `watchlist` array with 61 items or non-string first element `[123]`.
10. **Value Poisoning on Allowed Key**: `UPDATE /users/userA/holdings/h1` changing `shares` to `-50` or `"invalid_string"`.
11. **Orphaned Subcollection Record**: `CREATE /users/userGhost/alerts/a1` when parent `/users/userGhost` does not exist.
12. **Cross-User Subcollection List Scrape**: `LIST /users/userA/holdings` authenticated as `userB`.
