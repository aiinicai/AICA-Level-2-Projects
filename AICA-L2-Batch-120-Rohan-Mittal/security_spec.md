# Fairlyshare Security Specification

## 1. Data Invariants

1. **User Identity Invariant**: A user document at `/users/{userId}` can only be read by authenticated users, and only written by the user whose UID matches `{userId}`. Users cannot alter `is_deleted` or claim administrative flags.
2. **Group Access Invariant**: A group document at `/groups/{groupId}` can only be read by its registered members (`request.auth.uid in resource.data.member_ids`). Group metadata updates and deletion require administrator role in the group.
3. **Expense Invariant**: An expense document at `/expenses/{expenseId}` can only be created by an authenticated member whose UID is in `participant_uids`. For group expenses, the user must be a member of `group_id`. Exact, equal, and percentage splits must equal the total expense amount. Edits and deletes are restricted to the expense creator or a group administrator.
4. **Settlement Invariant**: A settlement at `/settlements/{settlementId}` can only be recorded by an authenticated user where `from_uid == request.auth.uid` or `created_by == request.auth.uid`. A user cannot record a settlement between two identical users (`from_uid != to_uid`).
5. **Friendship Invariant**: A friendship document at `/friendships/{friendshipId}` can only be accessed or modified by users listed in its `users` array.
6. **Notification Invariant**: Notifications at `/notifications/{notificationId}` can only be read and updated (`is_read`) by `recipient_uid`. Senders can only create notifications if `sender_uid == request.auth.uid`.
7. **Invitation Invariant**: Group invitations and claim tokens are verified with unguessable tokens, expiring after 7 days, and cannot be reused.

## 2. The "Dirty Dozen" Payloads (Designed to Break Identity, Integrity, and State)

1. **Payload 1 (Ghost Admin Escalate)**: An unprivileged user attempts to write `{ role: "admin", isAdmin: true }` to `/users/{attackerUid}`.
2. **Payload 2 (User ID Impersonation on Profile)**: User B attempts to write to `/users/{userA_Uid}` with forged profile data.
3. **Payload 3 (Orphan Expense Creation)**: Attacker attempts to create an expense for a group `{ groupId: "foreign-group-1" }` without being in its `member_ids`.
4. **Payload 4 (Payer Self-Settlement Loop)**: Attacker attempts to create a settlement with `{ from_uid: "uid1", to_uid: "uid1", amount_units: 5000 }`.
5. **Payload 5 (Negative/Zero Settlement Injection)**: Attacker attempts to record a settlement with `{ amount_units: -100 }` or `{ amount_units: 0 }`.
6. **Payload 6 (Shadow Key / Property Pollution)**: Attacker attempts to create an expense containing an unexpected field `{ __proto__: "malicious", bypass_rules: true }`.
7. **Payload 7 (Denial of Wallet Huge Payload)**: Attacker attempts to inject a 500KB string into `description` of an expense.
8. **Payload 8 (Foreign Group Member Removal)**: Regular member tries to delete another member from `/groups/{groupId}/members/{otherMemberId}`.
9. **Payload 9 (Notification Cross-Reading)**: User A attempts to list/get notifications where `recipient_uid == "userB"`.
10. **Payload 10 (Archived Group Modification)**: User attempts to add an expense to an archived group.
11. **Payload 11 (Friendship Hijack)**: User C attempts to read or mutate `/friendships/{friendshipAB}` where `users: ["userA", "userB"]`.
12. **Payload 12 (Unauthorized Expense Delete)**: Regular member tries to delete an expense created by another member in the group.

## 3. Test Runner Specification

See `src/test/firestore.rules.test.ts` for automated security verification.
