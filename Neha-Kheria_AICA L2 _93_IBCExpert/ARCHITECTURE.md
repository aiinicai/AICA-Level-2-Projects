# IBC Expert Architecture v1.0

## Security and trust boundaries
1. The desktop shell and local browser talk only to `127.0.0.1` using a random loopback port.
2. Confidential business data never requires outbound networking.
3. A master password derives a key-encryption key. It decrypts a random application master key; changing the password re-wraps rather than re-encrypting every file.
4. Per-object keys are HKDF-derived from the application master key and object identity. Vault and backup payloads use authenticated encryption with unique nonces.
5. Owner licences are canonical JSON signed with Ed25519. Customer builds contain only the public verification key.
6. Audit records form an HMAC-protected chain. Mutating, deleting, or reordering entries is detectable.
7. Imported legal records are data, not Python logic. Verification is an explicit professional action recorded in audit history.

## Layers
- `app/core`: paths, configuration, bootstrap, logging, time abstraction, errors.
- `app/security`: KDF/AEAD, authentication, DPAPI, audit integrity, safe files/archives, network policy.
- `app/db`: SQLite lifecycle and ordered transactional migrations.
- `app/repositories`: SQL persistence only.
- `app/services`: application use-cases and transaction boundaries.
- `app/documents`: validation, extraction, OCR and encrypted vault.
- `app/legal`: import, point-in-time versioning and FTS search.
- `app/workflow`: data-driven date rules, stages and recommendations.
- `app/licensing`: trial, request code, signed entitlement and feature service.
- `app/api`: versioned localhost API and UI routes.
- `app/ui`: local templates and assets.
- `app/plugins`: disabled-by-default permission-scoped integrations.
- `owner_tools`: owner-only signing utility, excluded from customer builds.

## Database
SQLite runs with foreign keys, WAL, busy timeout, secure delete and transactional migration checksums. FTS5 indexes only decryptable/extracted text explicitly accepted for local indexing. Sensitive structured fields are encrypted before persistence where marked.

## No invented law
No statutory deadline, form, citation, or holding is pre-verified by code. Workflow definitions require source citation and verification status. An uncited legal recommendation cannot be persisted.

## Local data and future internet-update boundary
The production database is local SQLite under the user's local application-data directory. The current application performs no automatic web import, scraping, download, telemetry, remote database synchronization, or background legal update. Data is imported only when the user explicitly selects a local file or performs manual entry. The architecture reserves a future permission-controlled updater/plugin boundary, disabled by default, for a later secure internet-download/update feature with source validation, integrity verification, staging, manual review and audit logging before local database promotion.


## Build 10: local backup scheduling and offline network boundary
- Scheduled backups are encrypted with the existing master-key-derived backup cryptography and written only to the local application backup directory.
- Scheduling state is stored locally in the database settings table. Automatic due checks occur only during authenticated application use; no cloud scheduler or remote service is involved.
- Retention applies only to application-created scheduled backups and never automatically deletes manual backups.
- The application runtime installs a process-level Python socket/DNS guard that permits loopback only. This preserves the `127.0.0.1` FastAPI/PyWebView architecture while preventing current Python features from opening external network connections.
- Future internet download/update capability remains an intentionally nonfunctional extension boundary and must later be implemented with explicit permission, allowlisting, verification and security review.
