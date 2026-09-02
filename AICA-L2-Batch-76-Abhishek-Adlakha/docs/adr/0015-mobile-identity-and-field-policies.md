# ADR 0015: Mobile Identity, Extensible Roles and Field Policies

- Status: Accepted
- Date: 2026-08-20

## Decision

Employees authenticate with a normalized 10-digit Indian mobile number as username and a hashed password. Employees and login users remain separate entities. Server-side sessions are revocable, expire after 12 hours, and are invalidated by password, account or role-permission changes.

Seed the exact roles Administrators, Manager, Articles, Paid Assistants, Accountants and Client Accountants. Administrators may add roles and configure permission scope. Administrators may also mark registered fields mandatory or optional. A system-required field cannot be made optional because database identity, referential or business invariants take precedence.

The first administrator is Abhishek Adlakha and is created by a one-time local bootstrap command. No default password or mobile number is stored in source code.

## Consequences

Role and field-policy changes are audited. Temporary employee passwords require change at first login. Client/task field definitions are added by their owning future phases before administrators can configure them.
