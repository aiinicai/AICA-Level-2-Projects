# IBC EXPERT — AUTHORITATIVE PROJECT STATE

Last updated: 2026-09-23

## Authority and versions
- Master specification: user's MASTER SINGLE BUILD PROMPT in this conversation.
- Architecture version: 1.0
- Application version: 0.1.14-dev
- Schema version: 3
- Migration version: 003 (`backup_schedule_metadata`)
- Current migration checksum prefixes: v1 `d6a740450f47b6bb`, v2 `0595b9310dc0d004`, v3 `c88e015096729d0d`.
- Security model version: 1.0
- Licensing protocol version: 1

## Authoritative architecture
- Python 3.11+ offline desktop application.
- Framework-independent services over parameterized stdlib SQLite.
- Local UI/API: FastAPI/Jinja2/bundled CSS+JS bound only to `127.0.0.1`, displayed inside PyWebView.
- Desktop shell reserves an OS-assigned loopback socket first and passes that exact listening socket to Uvicorn, preventing free-port race conditions.
- SQLite: foreign keys, WAL, FULL synchronous, secure delete, transactional checksum-protected migrations, FTS5/BM25.
- Security: scrypt master-password envelope, random 256-bit master key, HKDF-separated object keys, RFC 8439 ChaCha20-Poly1305 authenticated encryption, Windows DPAPI for installation state, redundant trial records, HMAC audit chain.
- Licensing: canonical JSON entitlement, Ed25519 owner signature, canonical base64url credential encoding, public-key-only customer verifier, device-bound offline credentials, centralized feature service.
- Legal data defaults to REVIEW_REQUIRED; no invented legal deadline/citation is bundled.

## Completed production modules
- Bootstrap/authentication: first-run pinned dependency installer with wheelhouse fallback, progress/retry handling; persistent local user setup; scrypt master-key envelope login; persistent escalating login throttling; optional encrypted RFC 6238 TOTP; opaque in-memory idle-expiring sessions with no master key in browser/database.
- Core: typed errors, UTC clock abstraction, secure OS paths, validated configuration.
- Crypto: RFC-vector-tested ChaCha20-Poly1305, scrypt/HKDF hierarchy, password envelope/change, lockout model, Ed25519 RFC 8032, DPAPI wrapper, redundant atomic secure store, chunked encrypted streams.
- Database: 53-table/virtual-table normalized schema covering required entities; FTS5; migration discovery, checksums, idempotence and integrity checks.
- Audit: append-only HMAC chain with modification/deletion detection.
- Licensing: 30-day persistent trial, warnings, exact expiry, clock rollback detection, request code, signed entitlement, feature flags, activation persistence, owner CLI key generation and licence issuance.
- Client/matter: real CRUD/status lifecycle, optimistic edit version, encrypted PAN, field history, permanent-delete confirmation, matter creation.
- Documents core: signature validation, Windows-safe filename handling, path containment, encrypted vault, SHA-256 dedupe, text extraction, local Tesseract OCR integration, PDF OCR integration point, persistent FTS, safe ZIP import.
- Document Vault UI/API: authenticated local upload, client/matter/category/tag association, validation, encrypted persistence, duplicate feedback, FTS/metadata search and filters, detail view, secure decrypted download, metadata review updates, local OCR reprocessing and safe ZIP import with rejected-entry feedback.
- Legal: generic statutes/provisions/judgments, metadata editing, JSON package import, explicit verification, amendments, point-in-time retrieval, FTS/BM25 search and filters, citations.
- Workflow: stored definitions, citation-required legal due dates, instantiation, checklists, calendar/business-day due calculation, recalculation history, overdue status, stage completion, attachments.
- Recommendations: deterministic overdue/upcoming/missing-document rules; database and service reject uncited recommendations.
- Forms/communications: merge from actual client/matter data, versions, edited content, TXT/DOCX/PDF/XLSX exports, offline TXT/EML drafts.
- Dashboard: real aggregate metrics and process progress.
- Backup/restore: chunked encrypted backup, complete DB + vault manifest, per-file hashes, database integrity/migration validation, automatic pre-restore safety backup, tested restoration.
- Web UI: first-run setup, login/logout, secure sessions, CSRF/CSP, Dashboard, Client Master, Document Vault, trial/licence status, activation and TOTP management.
- Desktop shell: dynamic loopback port, pre-bound socket handed directly to Uvicorn, PyWebView window, health-checked startup and controlled shutdown.
- Test source: pytest suites for completed modules.
- Release gate: `RELEASE_CHECKLIST.md`.

## Build 05 completed files / changes
- `app/documents/vault.py`: document metadata/detail queries, filtered vault listing, conservative FTS query construction, OCR reprocessing, metadata review updates and ZIP import result accounting.
- `app/documents/safety.py`: hardened Windows reserved-name sanitization for hostile filenames.
- `app/licensing/entitlement.py`: canonical base64url decoding check so alternative/non-canonical modified activation encodings are rejected.
- `app/web/application.py`: Document Vault routes and `/api/v1/documents` endpoints for upload, list/search, detail, metadata, OCR, download and ZIP import.
- `app/web/templates/documents.html`: working encrypted vault search/filter/upload/ZIP-import screen.
- `app/web/templates/document_detail.html`: metadata, extracted-text, OCR and secure download screen.
- `app/web/templates/base.html`: Documents navigation.
- `app/web/templates/client_detail.html`: associated documents section and vault shortcut.
- `app/web/static/app.css`: document vault/filter/detail styling.
- `tests/test_document_web.py`: authenticated UI/API upload/search/download/deduplication/metadata and invalid-file/CSRF tests.
- `tests/test_documents.py`: metadata/search/update/ZIP result coverage.
- Version bumped to `0.1.4-dev`.

## Validation passed in this build environment
- Python `compileall` succeeds for application, tests, owner utility and launchers.
- Document-focused suite: 11/11 tests passed (`test_documents`, `test_document_web`, `test_web_security`, `test_clients`).
- Every pytest file passes when executed individually in this environment: 42 tests total across audit, auth, backup, clients, crypto, database, desktop shell, document web, documents, Ed25519, forms/dashboard, legal, licensing, web security and workflow.
- Security regression found during the full run was fixed: non-canonical base64url mutation of an activation signature is now rejected.
- Malicious Windows reserved filename sanitization regression found during the run was fixed.
- Monolithic `python -m pytest -q` reached 42/42 test completion and `[100%]`, but the harness process did not return before the tool timeout; therefore the clean full-suite runner release-gate item remains unchecked until teardown behaviour is confirmed in the target/pinned environment.

## Environment findings
- Current sandbox is Linux with Python 3.13 and SQLite FTS5.
- FastAPI/Starlette/Jinja2/pytest/httpx are available here, so localhost web tests could be executed.
- Target versions remain pinned in `requirements.txt`; this sandbox's installed FastAPI version is newer than the target pin.
- No external network access was used.
- Windows DPAPI and actual PyWebView Windows backend cannot be exercised in this Linux sandbox.

## Security findings/open work
- Authentication persistence, optional TOTP, server-side idle sessions, secure cookie/CSRF/CSP wiring, localhost host validation, trial gating and signed offline activation are implemented.
- Document uploads are streamed to private local temp storage with a 100 MB ceiling, validated before ingestion, encrypted at rest and deleted from temp after processing.
- ZIP path traversal, symlinks, suspicious compression ratios, oversized members and nested ZIP auto-import are blocked/rejected.
- Customer application still contains no private licence signing key.
- Offline commercial enforcement cannot resist a determined local administrator; controls target reasonable non-invasive resistance.
- Outbound runtime socket/DNS guard is implemented and tested; only loopback/local socket destinations are allowed.

## Packaging status
- PyWebView source desktop shell is implemented.
- PyInstaller onedir customer packaging specification and reproducible Windows build scripts are implemented.
- Post-build verification rejects owner tools/private signing-key material and requires the correct public verification key.
- Actual Windows executable/installer build and clean-Windows acceptance have not yet been performed in this Linux sandbox.


## Build 06 completed files / changes
- `app/legal/service.py`: persistent statute/provision/judgment browsing, detail retrieval, version history and explicit verification-state updates.
- `app/web/application.py`: complete Legal Database routes plus `/api/v1/legal/search`; JSON package import remains local and validated.
- `app/web/templates/legal*.html`: search, statute/provision/judgment browsing, add forms, point-in-time lookup, amendment versioning and manual verification controls.
- `app/web/templates/base.html`: Legal Database navigation.
- `app/web/static/app.css`: legal text/review presentation.
- Version bumped to `0.1.5-dev`.

## Build 06 validation
- Python compile validation completed successfully.
- Existing legal verification defaults remain `REVIEW_REQUIRED`; no imported content is silently promoted to `VERIFIED`.
- Legal search continues to use persisted FTS5/BM25 index and source-reference fields.

## Build 07 completed files / changes
- Workflow UI: local definitions, matter instantiation, persisted stage status and recalculation.
- Recommendation UI: deterministic citation-required generation with verification status displayed.
- Forms UI: local templates, matter merge, persisted versions and TXT/DOCX/PDF/XLSX export.
- Backup UI: encrypted local backup creation and integrity verification.
- Confirmed architecture: primary SQLite database and application data remain local on the computer.
- Current version never automatically imports/downloads data from the web. Imports remain explicit user actions.
- Reserved a disabled-by-default future secure internet downloader/database updater integration boundary; no online updater is enabled now.

## Build 08 completed files / changes
- `app/plugins/manager.py`: permission-gated local plugin registry plus persisted local event outbox. Plugins are disabled by default.
- `app/plugins/sample.py`: harmless local event sample plugin; no network access.
- Internet/database updater permission is explicitly reserved and rejected in the current build. No downloader, HTTP client, remote scheduler or automatic web import was added.
- `app/services/imports.py`: explicit user-selected local import orchestration with persistent import history and completion/failure events.
- `app/web/templates/imports.html` and routes: local import UI for user-selected safe files, including client/matter/category/tag association.
- `app/web/templates/plugins.html` and routes: local plugin visibility and enable/disable control.
- Navigation updated with Local Import and Plugins.
- Primary SQLite database, encrypted vault, import history and plugin configuration all remain under the local application data root on the user's computer.
- Version bumped to `0.1.7-dev`.

## Build 08 validation
- Python compile validation succeeded.
- 10 focused/regression tests passed across plugin permissions, explicit local imports, document safety/round-trip and web security.
- Tests confirm sample plugin is disabled by default and the reserved future network-update permission cannot be registered.

## Build 09 completed files / changes
- `app/db/migrations/m002_manual_review_structured_imports.py`: schema migration for saved mapping profiles and a persistent manual review queue.
- `app/services/review_imports.py`: explicit local structured import staging for CSV, XLSX, DOCX and JSON; conservative heading mapping; reusable mapping profiles; manual approve/reject flow; locally stored legal-source review.
- `app/web/application.py`: structured import, legal-source review and manual-review queue routes plus local API listing.
- `app/web/templates/imports.html`: richer local-import mapping UI and saved profile visibility.
- `app/web/templates/review_queue.html` and `review_detail.html`: persistent human review workflow with edit, approve and reject actions.
- `app/web/templates/base.html` and `app/web/static/app.css`: review-queue navigation and presentation.
- `tests/test_review_imports.py`: staged-before-create behavior, legal REVIEW_REQUIRED preservation, legal-source vault staging and rejection coverage.
- Application version bumped to `0.1.8-dev`; schema version bumped to 2.
- Current build still contains no downloader, URL fetcher, remote scheduler, web scraper, telemetry or automatic internet database updater. All imports require a user-selected local file.

## Build 09 validation
- Python compile validation succeeds for application, tests, owner tools and launchers.
- Schema migration 1 -> 2 is applied through the existing checksum-protected migration runner.
- Focused review/import/plugin/database regression tests pass after schema-version updates.
- Structured legal records approved from the manual review queue remain `REVIEW_REQUIRED`; approval does not silently mark legal material as VERIFIED.
- Local legal-source documents remain encrypted in the local vault and are sent to review rather than auto-promoted into the legal database.


## Build 10 completed files / changes
- Application version bumped to `0.1.9-dev`; schema version bumped to 3 with migration `003 (backup_schedule_metadata)`.
- `app/services/backup_schedule.py`: encrypted scheduled local backup controller with persisted schedule, authenticated-use due checks, one-hour retry suppression after failure, manual run-now, and safe retention.
- Retention removes only older `SCHEDULED` backups inside the application-owned local backup directory; user-created `MANUAL` backups are not automatically deleted.
- `app/services/backup.py`: persisted backup type and label metadata; pre-restore safety backup classification retained.
- `app/web/templates/backups.html` and backup routes: schedule enable/disable, interval, retention, run-now, retention-now, history/type/label/status and verification UI.
- The default schedule is initialized on first authenticated use and becomes due one day later; it does not create a heavy backup immediately on first login.
- `app/security/network.py`: process-level offline guard blocks non-loopback socket connections and external DNS/name resolution while allowing `127.0.0.1`, `::1`, `localhost`, and local non-IP socket families.
- `app/web/application.py`: installs outbound guard for normal application runtime and refuses configuration that attempts to enable outbound integrations in this version.
- `app/desktop.py`: localhost health check changed to direct `http.client` loopback access so environment proxy settings cannot redirect the health check externally.
- Current application still has no downloader, URL fetcher, remote update scheduler, telemetry, cloud database, or automatic web import. The future secure internet updater remains a reserved, nonfunctional permission boundary only.
- Primary SQLite database, encrypted vault, backups, configuration and all working data remain local on the user's computer.

## Build 10 validation
- Python `compileall` succeeds for application, tests, owner tools and launchers.
- Full monolithic pytest run now exits cleanly: **54/54 tests passed** in this build environment.
- New tests prove scheduled backup creation/policy persistence, retention preserving manual backups, schedule disable behavior, remote connection/DNS blocking, and loopback connectivity.
- Current migration checksums: v1 `d6a740450f47b6bb`, v2 `0595b9310dc0d004`, v3 `c88e015096729d0d` (prefixes).
- FastAPI deprecation warnings remain for legacy shutdown event registration; functionality passes but migration to lifespan handlers can be handled during packaging cleanup.

## Build 11 completed files / changes
- Application version bumped to `0.1.11-dev`; no database schema change.
- `packaging/IBCExpert.spec`: customer-only PyInstaller onedir build definition with local templates/static assets and dynamic PyWebView/Uvicorn imports.
- Customer build requires explicit owner PUBLIC verification key input through `IBC_EXPERT_PUBLIC_KEY`; the private signing key is never accepted or embedded.
- PyInstaller exclusions explicitly remove `owner_tools`, tests and development-only test tooling from the ordinary customer bundle.
- `scripts/build_windows.ps1` and `.bat`: reproducible Windows build entry points, wheelhouse preference, clean build, package verification, ZIP release creation and SHA-256 manifest.
- `scripts/validate_public_key.py`: validates the 32-byte Ed25519 public verification key before packaging.
- `scripts/verify_customer_package.py`: post-build scan rejects owner-tool paths, owner private-key filenames/markers, missing/invalid public key and missing executable.
- `packaging/README.md`: owner/customer separation and Windows customer build procedure.
- `tests/test_packaging.py`: platform-independent packaging security tests.

## Build 11 validation
- Python `compileall` succeeds for application, owner tool source, scripts, tests and launchers.
- Full monolithic pytest run exits cleanly: **60/60 tests passed** in this build environment.
- Packaging tests prove safe customer layout acceptance and rejection of owner tools/private signing-key material.
- No owner private signing key was generated, copied or included.
- Actual PyInstaller Windows binary build remains unverified because this build environment is Linux.

## Build 12 completed files / changes
- Application version bumped to `0.1.13-dev`; no database schema change.
- `scripts/prepare_wheelhouse.ps1/.bat`: reproducible trusted-Windows wheelhouse preparation using pinned requirements and wheel-only downloads.
- `scripts/verify_wheelhouse.py`: SHA-256 manifest generation/verification and offline pip dry-run dependency resolution.
- `app/core/bootstrap.py`: selected offline wheelhouses are integrity-checked and fail closed if missing, incomplete or tampered; there is no silent internet fallback after a wheelhouse is selected.
- `packaging/OFFLINE_WHEELHOUSE.md`: offline dependency-media preparation and use procedure.
- `packaging/installer/IBCExpert.iss`: Inno Setup 6 definition wrapping only the verified PyInstaller onedir customer package.
- `scripts/build_installer.ps1/.bat`: re-verifies customer contents before installer compilation and hashes the produced installer.
- `packaging/INSTALLER.md`: Windows installer build procedure.
- `scripts/build_windows.ps1`: verifies a present wheelhouse before dependency installation and supports optional installer creation.
- `tests/test_offline_packaging.py`: manifest tamper/member checks and static installer/wheelhouse integration tests.
- Internet legal-data downloading/updating remains disabled and unimplemented. The primary database and working data remain local.

## Build 12 validation
- Python `compileall` succeeds for application, scripts, tests, owner tools and launchers.
- Full monolithic pytest run exits cleanly: **66/66 tests passed** in this build environment.
- Actual PyInstaller/Inno Setup execution remains a Windows-only release gate and cannot be claimed from the Linux sandbox.

## Build 13 completed files / changes
- Application version bumped to `0.1.13-dev`; no database schema change.
- `app/core/bootstrap_ui.py`: stdlib-only first-run progress window with console fallback and fail-closed dependency setup behaviour.
- `launch_desktop.py` and `bootstrap.py`: bootstrap executes before importing third-party desktop/runtime modules.
- `app/web/application.py`: expanded stable `/api/v1` localhost integration surface and explicit offline/local-database status contract.
- `tests/test_api_v1.py`: authenticated API-v1 contract, local/offline posture, client update/status and CSRF tests.
- `tests/test_bootstrap_ui.py`: no-op first-run bootstrap path when dependencies are already satisfied.
- `tests/test_ui_controls.py`: visible-control placeholder/dead-action audit and literal form-action route audit.
- `docs/USER_MANUAL.md`, `docs/INSTALLATION_MANUAL.md`, `docs/OWNER_LICENSING_MANUAL.md`, `docs/DEVELOPER_INTEGRATION.md`, `docs/API_V1.md`.
- Current version still has no automatic internet legal/database import or updater; the database and working data remain local.

## Build 13 validation
- Python `compileall` succeeds for application, tests, owner utilities, scripts and launchers.
- New Build 13 tests: **6/6 passed**.
- All test files pass in bounded batches: **72 tests total**.
- The single monolithic pytest command did not return before the Linux harness timeout; therefore the final pinned-dependency full-suite release gate remains open even though every test file passes in bounded batches.
- Windows packaging/installer execution and clean-Windows end-to-end acceptance remain unverified in this Linux environment.

## Pending files / next milestones after Build 13
1. Run the pinned dependency set on Windows and produce the actual PyInstaller onedir customer package.
2. Build the Inno Setup installer from the verified customer package.
3. Execute clean-Windows acceptance: install → first run/bootstrap → master user → client/document/OCR/search/workflow/forms → backup/restore → restart/persistence → trial expiry → owner activation → restart/licence persistence.
4. Run the full monolithic pytest suite on the target pinned Windows environment and close any target-specific defects.

## Next exact development task after Build 13
Prepare the Windows release/acceptance harness and checklist scripts needed to execute and record the remaining platform-specific gates without changing completed application functionality. Do not add internet legal-data downloading/updating in this version.

## Build 14 completed files / changes
- Application version bumped to `0.1.14-dev`; database schema and migration version unchanged.
- `scripts/release_evidence.py`: stdlib-only release evidence file with defined Windows gates, SHA-256 binding for evidence files, validation and Markdown reporting.
- `scripts/run_windows_release_gate.ps1/.bat`: trusted Windows release-workstation harness that creates a fresh virtual environment, installs pinned dependencies, runs the full monolithic pytest suite with JUnit/log evidence, builds/verifies the PyInstaller customer package, builds the Inno Setup installer, and prepares a clean-machine acceptance kit.
- `scripts/clean_windows_acceptance.ps1/.bat`: guided PowerShell-only clean-Windows acceptance recorder; Python is not required on the clean end-user test machine.
- `docs/WINDOWS_RELEASE_ACCEPTANCE.md`: exact release/clean-machine execution and evidence procedure.
- `tests/test_release_harness.py`: tests for evidence completeness, hash tamper detection, reporting, no automatic clean-machine pass, PowerShell-only clean acceptance, and preserved offline legal/database posture.
- Release harness deliberately leaves the two first-run dependency-bootstrap paths BLOCKED until the actual bootstrap UI/path is exercised on disposable Windows source-install tests; successful plain pip dependency installation is not misrepresented as bootstrap acceptance.
- No internet legal/database downloader/updater was added. Application database, encrypted vault and working data remain local.

## Build 14 validation
- Python `compileall` succeeds for application, scripts, tests, owner tools and launchers.
- Build 14 release-harness tests pass: 6/6.
- All 25 pytest files pass in bounded regression runs: **78/78 tests passed**.
- The monolithic Linux pytest invocation reached the final `78 passed` summary but the surrounding harness did not return before its tool timeout; the target pinned-Windows monolithic-exit gate therefore remains open and is explicitly checked by the Windows release harness.
- Actual Windows PyInstaller/Inno Setup execution, first-run bootstrap acceptance on Windows, and clean-Windows end-to-end acceptance remain open release gates.

## Pending files / next milestones after Build 14
1. On a trusted Windows release workstation, run `scripts\\run_windows_release_gate.ps1` with the owner public verification key and verified wheelhouse.
2. Exercise both first-run dependency bootstrap paths (internet package index and verified wheelhouse) on disposable Windows source-install test environments and record PASS/FAIL evidence.
3. Run the generated clean-machine acceptance kit on a genuinely clean Windows machine/VM using synthetic data only.
4. Return the completed evidence file to the release workstation and run `release_evidence.py validate --require-complete`.
5. Fix any Windows-specific defect found; do not mark the product COMPLETE until every release gate is PASS.

## Next exact task after Build 14
Execute the Windows release/acceptance harness. No additional application feature development should be performed unless a Windows release-gate defect is found. Do not add internet legal/database downloading/updating in this version.


## Build 15 completed files / changes
- Application version bumped to `0.1.15-dev`; database schema/migration unchanged.
- Windows release target changed to explicit 64-bit CPython 3.14.x; source metadata supports Python 3.11 through 3.14.
- Refreshed Python-3.14-compatible dependency pins in `requirements.txt`, including PyInstaller 6.22.3, PyWebView 6.2.1, cryptography 50.0.1, argon2-cffi 25.1.0, Pillow 12.2.0, PyMuPDF 1.28.2 and other current runtime/test pins.
- Added `scripts/validate_python_target.py`; release/build scripts now fail closed unless CPython 3.14 x64 is used.
- `prepare_wheelhouse.ps1` now requires Python 3.14 so offline dependency media matches the release interpreter.
- First-run dependency bootstrap now validates exact installed pinned versions and treats stale/mismatched versions as missing.
- PyMuPDF integration uses the recommended `pymupdf` import.
- Added `tests/test_python314_compat.py`.
- No internet legal/database downloader/updater was added; database and working data remain local.

## Build 15 validation / remaining gate
- Cross-platform compile validation succeeded. Compatibility/packaging/bootstrap-focused tests passed 23/23; document/web/desktop/security regression tests passed 15/15; backup tests passed 3/3 in the available sandbox. Actual Windows CPython 3.14 wheel resolution, PyWebView/pythonnet backend, PyInstaller build, installer build and clean-machine acceptance remain Windows release gates.
- Do not call the product COMPLETE until the CPython 3.14 Windows release harness and clean-machine acceptance pass.

## Next exact task after Build 15
On the trusted Windows release workstation with 64-bit CPython 3.14.x selected, prepare/verify the wheelhouse and run `scripts\run_windows_release_gate.ps1`. Fix only defects revealed by those gates; do not rework completed application functionality.
