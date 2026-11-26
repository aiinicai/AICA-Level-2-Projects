# LeaveLedger Security Specification (Phase 0)

## 1. Data Invariants
1. **Verified Identity Only**: Every Firestore read and write requires `request.auth != null` and `request.auth.token.email_verified == true`.
2. **PII Isolation (No Blanket Directory Reads)**: An employee record (`/employees/{empId}`) contains email PII and reporting lines. Only the employee (`email == authEmail()`), their direct reporting manager (`managerEmail == authEmail()`), or an HR Admin (`isAdmin()` on `get`; `isBootstrappedAdmin()` on `list`) may read it.
3. **Immutable Ownership & Accounting Math**:
   - An employee cannot submit a `LeaveRequest` on behalf of another employee (`incoming().employeeEmail == authEmail()`), nor set `status` to anything other than `'pending'` on creation, nor forge `managerEmail` (must match their active `/employees/{empId}` record or admin override).
   - Once a `LeaveRequest` reaches a terminal state (`approved`, `rejected`, `cancelled`), non-admins cannot re-open or mutate it.
   - `LeaveBalance` must satisfy `closing == opening + accrued - availed` on every write. Only HR Admins may alter `opening` or `accrued` after creation; Reporting Managers may only increment `availed` (and decrement `closing` accordingly) for their direct reports.
4. **Temporal & ID Integrity**: All `createdAt`/`updatedAt` timestamps must equal `request.time`. All path IDs must match `^[a-zA-Z0-9_-]+$` and stay within 128 characters.

## 2. The "Dirty Dozen" Attack Payloads
1. **Unverified Email Spoof**: User with `email_verified: false` tries to read `/employees/{empId}`. -> `PERMISSION_DENIED`.
2. **Shadow Field Injection on Leave Request**: Employee creates `/leaveRequests/{reqId}` with extra ghost field `isAutoApproved: true`. -> `PERMISSION_DENIED` (`hasOnly` check).
3. **Self-Approval on Creation**: Employee creates `/leaveRequests/{reqId}` with `status: 'approved'`. -> `PERMISSION_DENIED`.
4. **Impersonated Leave Request**: Employee A creates `/leaveRequests/{reqId}` with `employeeEmail: 'colleague@company.com'`. -> `PERMISSION_DENIED`.
5. **Manager Routing Forgery**: Employee creates `/leaveRequests/{reqId}` setting `managerEmail` to a colluding friend instead of their `/employees/{empId}` `managerEmail`. -> `PERMISSION_DENIED`.
6. **Unauthorized Manager Approval**: Non-manager colleague tries to update `/leaveRequests/{reqId}` `status` to `'approved'`. -> `PERMISSION_DENIED`.
7. **Terminal State Mutation**: Manager tries to change an already `'rejected'` `/leaveRequests/{reqId}` back to `'approved'`. -> `PERMISSION_DENIED`.
8. **Balance Tampering by Employee**: Employee updates their own `/leaveBalances/{balId}` to set `opening: 999`. -> `PERMISSION_DENIED`.
9. **Balance Tampering by Manager**: Manager updates direct report's `/leaveBalances/{balId}` to change `accrued` or break `closing == opening + accrued - availed`. -> `PERMISSION_DENIED`.
10. **PII Scraping via List Query**: Non-admin employee runs `list` on `/employees` without restricting to their own email or direct reports. -> `PERMISSION_DENIED`.
11. **Privilege Escalation on Employee Profile**: Employee tries to update their own `/employees/{empId}` `isAdmin: true` or `managerEmail`. -> `PERMISSION_DENIED`.
12. **Client Timestamp Forgery / ID Poisoning**: User creates `/leaveRequests/../../poison` or passes a backdated `createdAt`. -> `PERMISSION_DENIED`.
