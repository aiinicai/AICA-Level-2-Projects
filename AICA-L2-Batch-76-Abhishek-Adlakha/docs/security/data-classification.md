# Data Classification

| Class | Examples | Handling baseline |
|---|---|---|
| Restricted | Password/session secrets, encryption keys, database credentials, backup keys | Never log/audit; secret store or protected server file; minimal administrators; rotate and revoke |
| Confidential | PAN, TAN, GSTIN, DOB, phone, email, address, client notes, billing amounts, task comments, exports, backups | Role/scope authorization, TLS, encrypted backup, no production copy to development without masking |
| Internal | Employee/team structure, service masters, task status metadata, operational metrics | Authenticated staff only; least privilege; safe structured logs by stable IDs |
| Public | Product name, generic health status, non-sensitive documentation approved for release | May be exposed intentionally; health output still excludes topology/version secrets |

Classification follows the most sensitive field in a record/export. Audit events may reference confidential records but must allow-list changed fields and exclude restricted values. New modules must add their data types and retention owner before implementation.

