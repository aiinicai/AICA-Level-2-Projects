# IBC Expert — User Manual

## 1. What the application is
IBC Expert is a single-user, offline-first Windows application for insolvency-practice work. Its database, encrypted document vault, legal knowledge base, backups and configuration are stored locally on the computer. This release does **not** automatically download, scrape, synchronize or update legal/database material from the internet.

## 2. First start
Run `IBCExpert.exe` after installation. A source installation may first show the dependency-setup window. It reports each missing pinned package and installs from a verified local `wheelhouse` when present; otherwise it may use the package index during initial setup only. Normal application use is offline.

On the first successful application initialization, create the local master user and a strong master password. Keep this password safely. The application does not store the plaintext password and cannot recover it for you.

## 3. Trial and activation
The first successful initialization starts the 30-day local trial. The application displays the remaining days and expiry date. When the trial expires, ordinary use is restricted but client data is not deleted. The activation page displays the device request code. Send that code to the software owner, receive the owner-generated activation credentials, and enter them on the activation screen. Activation is verified locally using the owner's public verification key.

## 4. Client Master
Use **Clients** to add, search, open, edit, archive, restore or soft-delete clients. Permanent deletion requires deliberate confirmation. Changes are persisted locally and field-change history is retained. Sensitive PAN data is encrypted at rest.

## 5. Document Vault
Use **Documents** to select files from the local computer. Supported documents are validated, content-hashed, encrypted in the local vault and associated with a client/matter where selected. Duplicate content is detected. Search uses stored metadata and extracted text. OCR is local-only and requires the configured local Tesseract component. ZIP imports are checked for traversal, symlink and suspicious compression/size risks.

## 6. Legal Database
Use **Legal Database** to add statutes, provisions and judgments or to import user-selected local legal packages/files. Imported or AI-assisted legal material is not silently treated as verified; the default state is `REVIEW_REQUIRED`. Verification status can be changed only by an explicit user action. Point-in-time provision history is retained when amendment versions are entered.

## 7. Local imports and review queue
Use **Imports** to select local CSV, XLSX, DOCX, JSON and supported document files. Structured records are staged in the **Review Queue**. Review, edit, approve or reject them. The current release contains no automatic internet data downloader or updater.

## 8. Workflow and recommendations
Workflow definitions are data-driven. Start a workflow for a matter, update stage status, recalculate deadlines when trigger dates change, and retain completion/history. Legal deadline rules require a citation. Recommendations are deterministic and cannot be stored as legal recommendations without an associated citation.

## 9. Forms and communications
Create templates, merge them with stored client/matter information, preserve versions and export supported outputs. Communication drafts remain offline; the application does not send email in this release.

## 10. Backups
Use **Backups** to create encrypted manual backups, configure scheduled local backups, verify integrity and apply scheduled-backup retention. Manual backups are not deleted by scheduled retention. Restore validates a backup before replacement and creates a safety backup of the current state.

## 11. Security
Optional offline TOTP can be enabled under **Security**. Sessions expire after inactivity. The local application server binds only to `127.0.0.1`. Runtime outbound network connections are blocked in this release. Do not move or edit internal database/vault files while the program is running.

## 12. Plugins and future internet updates
Plugins are disabled by default and permission-gated. A permission name is reserved for a possible future secure updater, but network-update permission is deliberately unavailable in this version. Future internet download/update capability must be added as a separate security-reviewed feature.
