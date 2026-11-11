# Family Vault — Consolidated Requirements Checklist

**Version:** 1.0 · **Date:** 9 November 2026 · **Owner:** CA Gurpreet Singh Samby

This checklist consolidates the two authoritative source documents into one traceable
list. It is the single reference used to judge whether a phase is complete.

**Source documents**

| Ref | Document | Authority over |
|---|---|---|
| BR | Family Vault – Build Route and Plan | Deployment and build strategy |
| FI | Family Vault – Feature Inventory | Scope definition and three-phase roadmap |
| MP | Master Development Prompt (this engagement) | Detailed functional and security requirements |

**Status values:** NOT STARTED · IN PROGRESS · COMPLETED · TESTING · BLOCKED

A requirement is only marked COMPLETED when the code exists **and** a test covering it
passes in CI. A screen that renders is not a completed feature.

---

## A. Non-negotiable constraints

These override convenience at every decision point.

| ID | Requirement | Source | Status |
|---|---|---|---|
| A1 | All encryption and decryption happens locally on the device | MP 5.1, FI 1 | COMPLETED (no network path exists; libsodium runs in-process) |
| A2 | No central server; no server able to decrypt a vault | MP 5.1, MP 11 | COMPLETED (none exists) |
| A3 | Cloud drive receives encrypted vault files only | MP 5.1, FI 1 | NOT STARTED |
| A4 | Titles, URLs, usernames, notes and folder names are all inside the encrypted payload | MP 5.1, FI 1 | COMPLETED (titles, URLs, usernames, notes and folder names are all inside the encrypted payload; asserted by test) |
| A5 | No vault contents, master password, keys or TOTP secrets sent to analytics, logs or any external service | MP 5.1 | COMPLETED for Stage 1 (no network code exists; `avoid_print` enforced) |
| A6 | Cryptographic primitives are never hand-implemented; vetted libraries only | MP 4, FI 1 | COMPLETED (libsodium via `package:sodium`; no primitive written here) |
| A7 | Public repository contains no real credentials, vault files, keys or family data | BR, MP 13 | COMPLETED for Stage 1 (`.gitignore` guard; verified no secret material present) |
| A8 | Two-factor protection for opening a vault is optional and off by default | MP 6, FI 4 | NOT STARTED |
| A9 | No TOTP code check offered as a substitute for encryption-key protection | MP 6, FI 4 | NOT STARTED |
| A10 | No paid services, subscriptions or hosted infrastructure introduced | MP 11 | COMPLETED (none used) |
| A11 | Implemented features are distinguished from planned and demo-only features in all documentation | MP 2, MP 21 | COMPLETED |

---

## B. Phase 1 — Minimum viable product

### B1. Cryptographic core

| ID | Requirement | Source | Status |
|---|---|---|---|
| B1.1 | Argon2id key derivation from master password | MP 5.3, FI 1 | COMPLETED (`argon2id13` named explicitly, not left to a default) |
| B1.2 | Cryptographically secure random salt, unique per vault | MP 5.3 | COMPLETED (tested: two vaults with the same password get different salts) |
| B1.3 | KDF algorithm, parameters and version stored in vault header | MP 5.3, MP 5.5 | COMPLETED |
| B1.4 | KDF cost parameters raisable later without breaking existing vaults | MP 5.3 | COMPLETED (costs live in the header; ceiling 1 GiB) |
| B1.5 | Malformed or hostile KDF parameters rejected before allocation (resource-exhaustion guard) | MP 5.3 | COMPLETED (bounds-checked in the header parser and again in the service) |
| B1.6 | Authenticated encryption: AES-256-GCM or XChaCha20-Poly1305 | MP 5.4, FI 1 | COMPLETED (XChaCha20-Poly1305-IETF; decision D-003) |
| B1.7 | Unique, cryptographically secure nonce per encryption; nonce reuse prevented | MP 5.4 | COMPLETED (fresh 192-bit nonce every write; tested) |
| B1.8 | Tampered, truncated or corrupted vault rejected; authentication failure never silently accepted | MP 5.4 | COMPLETED (a bit flipped at every byte position is refused; so is truncation, extension and splicing) |
| B1.9 | Documented, versioned vault file format with migration path | MP 5.5 | IN PROGRESS (format implemented and versioned; the standalone specification F9 is still to write) |
| B1.10 | Header carries only what decryption and versioning require; no account data in plaintext | MP 5.5 | COMPLETED (asserted by test) |
| B1.11 | Master password never stored; verification is by successful decryption | MP 5.2 | COMPLETED |
| B1.12 | Argon2id parameters benchmarked on target devices | MP 5.3 | IN PROGRESS (60 ms on CI hardware at 64 MiB / 2 passes; not yet measured on a phone) |

### B2. Vault management

| ID | Requirement | Source | Status |
|---|---|---|---|
| B2.1 | Create a new vault with master-password confirmation and strength guidance | MP 5.2, MP 7.1 | COMPLETED (confirmation, strength meter and an acknowledged warning) |
| B2.2 | Open an existing vault | MP 7.1 | COMPLETED |
| B2.3 | Lock and unlock | MP 7.1 | COMPLETED |
| B2.4 | Change vault settings | MP 7.1 | COMPLETED |
| B2.5 | Encrypted vault export | MP 7.1, MP 7.9 | COMPLETED (Backup & Transfer screen; own password optional) |
| B2.6 | Vault import | MP 7.1 | COMPLETED (reads, describes, then merges per entry; restore on the setup screen for a device with no vault) |
| B2.7 | Delete a vault behind an explicit confirmation | MP 7.1 | COMPLETED (two confirmations and the word DELETE typed out) |
| B2.8 | Full offline operation on the local encrypted file | MP 3, MP 7.1 | COMPLETED |
| B2.9 | Clear warnings that a lost master password means a lost vault | MP 5.2 | COMPLETED |

### B3. Item types

| ID | Requirement | Source | Status |
|---|---|---|---|
| B3.1 | Login: name, URL, username, email, password, notes, TOTP secret, created, modified | MP 7.2A | COMPLETED |
| B3.2 | Secure Note: title, folder, text content, created, modified | MP 7.2B, FI 2 | COMPLETED |
| B3.3 | Payment Card: cardholder, number, expiry, CVV, nickname, notes — all encrypted, never needlessly displayed | MP 7.2C | COMPLETED |
| B3.4 | Identity: full name, address, email, phone, date of birth, other fields, notes | MP 7.2D | COMPLETED |
| B3.5 | Data model extensible to future item types | MP 7.2 | COMPLETED (each type carries its own field list; one form renders all four) |

### B4. Organisation and retrieval

| ID | Requirement | Source | Status |
|---|---|---|---|
| B4.1 | Create, rename, delete and organise folders | MP 7.3, FI 2 | COMPLETED |
| B4.2 | Folder names and relationships encrypted | MP 7.3 | COMPLETED |
| B4.3 | Search by item name, username, website and folder | MP 7.4 | COMPLETED |
| B4.4 | Favourites | MP 7.4, FI 2 | COMPLETED |
| B4.5 | Sorting and filtering | MP 7.4 | IN PROGRESS (sorted by name; no user-chosen sort yet) |
| B4.6 | Search runs on in-memory decrypted data; terms never leave the device | MP 7.4 | COMPLETED (runs in memory; passwords deliberately not searched) |
| B4.7 | Trash: view, restore, permanently delete with confirmation; deleted data stays encrypted | MP 7.8, FI 2 | COMPLETED |

### B5. Generator and health

| ID | Requirement | Source | Status |
|---|---|---|---|
| B5.1 | Password generator: length, upper, lower, digits, symbols, ambiguous-character exclusion | MP 7.5, FI 2 | COMPLETED |
| B5.2 | Passphrase generation with configurable word count | MP 7.5 | COMPLETED |
| B5.3 | Username generation | MP 7.5 | COMPLETED |
| B5.4 | Password-strength evaluation | MP 7.5 | COMPLETED (master-password meter and the health report) |
| B5.5 | Cryptographically secure RNG for all generation | MP 7.5 | COMPLETED (Random.secure throughout) |
| B5.6 | Generated password copyable and savable straight into an entry | MP 7.5 | COMPLETED |
| B5.7 | Password-health report: weak, reused, old, needs-updating, with risk summary and recommendations | MP 7.6, FI 5 | COMPLETED |
| B5.8 | Health report runs entirely on-device; no password sent to any service | MP 7.6 | COMPLETED |

### B6. Built-in TOTP authenticator (for the user's other accounts)

| ID | Requirement | Source | Status |
|---|---|---|---|
| B6.1 | RFC 6238-compliant TOTP generation | MP 7.7, FI 4 | COMPLETED (RFC 6238 vectors asserted for SHA-1, SHA-256 and SHA-512) |
| B6.2 | Attach an authenticator secret to a login item | MP 7.7 | COMPLETED |
| B6.3 | Six-digit codes by default, with countdown to renewal | MP 7.7 | COMPLETED |
| B6.4 | Copy code | MP 7.7 | COMPLETED |
| B6.5 | Validate supported TOTP parameters; handle clock-skew problems | MP 7.7 | IN PROGRESS (parameters validated; no clock-skew warning yet) |
| B6.6 | TOTP secrets stay encrypted inside the vault | MP 7.7 | COMPLETED |
| B6.7 | Accept standard `otpauth://` provisioning URIs | MP 7.7 | COMPLETED (otpauth links accepted and normalised) |

### B7. Import and export

| ID | Requirement | Source | Status |
|---|---|---|---|
| B7.1 | CSV import from Bitwarden | MP 7.9, FI 2 | NOT STARTED |
| B7.2 | CSV import from Google Chrome | MP 7.9, FI 2 | NOT STARTED |
| B7.3 | CSV import from KeePass | MP 7.9, FI 2 | NOT STARTED |
| B7.4 | Column mapping and validation to reduce import errors | MP 7.9 | NOT STARTED |
| B7.5 | Encrypted export | MP 7.9, FI 2 | COMPLETED |
| B7.6 | Explicit confirmation and warning that CSV export is unencrypted; temporary files handled securely | MP 7.9 | NOT STARTED |

### B8. Security controls

| ID | Requirement | Source | Status |
|---|---|---|---|
| B8.1 | Auto-lock after configurable inactivity | MP 5.6, FI 1 | COMPLETED |
| B8.2 | Immediate manual lock | MP 5.6 | COMPLETED |
| B8.3 | Clipboard auto-clear after a configurable period | MP 5.6, FI 1 | COMPLETED (only clears if the clipboard still holds that value) |
| B8.4 | Screenshot protection on Android where supported | MP 5.6, FI 1 | NOT STARTED |
| B8.5 | Sensitive data handled carefully in memory and cleared when locking | MP 5.6 | COMPLETED (key wiped on lock; contents dropped) |
| B8.6 | Biometric unlock as optional convenience only | MP 5.6, MP 6, FI 1 | NOT STARTED |
| B8.7 | Hardware-backed device key storage where supported (Android Keystore, Windows) | MP 5.6, FI 1 | NOT STARTED |
| B8.8 | Master password required again after application restart | MP 5.6, FI 1 | COMPLETED |
| B8.9 | Injection, path-traversal and file-manipulation defences | MP 5.6 | IN PROGRESS (no path built from user input; file name is fixed) |
| B8.10 | Error handling that never discloses secrets | MP 5.6 | COMPLETED (asserted by test) |

### B9. Android application

| ID | Requirement | Source | Status |
|---|---|---|---|
| B9.1 | Installable Android APK | BR, MP 8.1, FI 3 | COMPLETED (built in CI; installed and running on the owner's phone, 9 Nov 2026) |
| B9.2 | Responsive smartphone interface | MP 8.1 | COMPLETED (drawer layout below 900 logical pixels) |
| B9.3 | Android Keystore integration | MP 4, MP 8.1 | NOT STARTED |
| B9.4 | Android Autofill Framework integration, selectable as system provider | MP 4, MP 8.1, FI 3 | NOT STARTED |
| B9.5 | Credential matching and secure handling of autofill requests | MP 8.1 | NOT STARTED |
| B9.6 | Minimum necessary Android permissions | MP 8.1 | NOT STARTED |
| B9.7 | No claim of passkey autofill support in Phase 1 | MP 8.1 | COMPLETED (not claimed) |

### B10. Windows desktop application

| ID | Requirement | Source | Status |
|---|---|---|---|
| B10.1 | Native Flutter Windows build | BR, MP 8.2, FI 3 | COMPLETED (built in CI; running on the owner's laptop, 9 Nov 2026) |
| B10.2 | Feature parity with Android for vault, items, generator, TOTP, health, search, import/export | MP 8.2 | COMPLETED (one codebase; no platform-specific screens) |
| B10.3 | Secure local storage on Windows | MP 8.2 | NOT STARTED |
| B10.4 | Optional Windows Hello where supported | MP 4, MP 8.2 | NOT STARTED |
| B10.5 | Distributable package or installer | MP 8.2 | IN PROGRESS (zip; no installer) |
| B10.6 | Architecture left extensible to macOS and Linux without delaying Windows | MP 8.2 | COMPLETED for Stage 1 (no Windows-only code in shared layers) |

### B11. Interface

| ID | Requirement | Source | Status |
|---|---|---|---|
| B11.1 | Twelve-destination navigation: Dashboard, All Items, Logins, Secure Notes, Cards, Identities, Folders, Favourites, Authenticator, Password Health, Trash, Settings | MP 12 | COMPLETED |
| B11.2 | Dashboard counters: items, folders, weak, reused, needs attention, favourites | MP 12 | COMPLETED |
| B11.3 | Light and dark themes | MP 12 | COMPLETED |
| B11.4 | Responsive layouts consistent across Android and Windows | MP 12 | COMPLETED |
| B11.5 | Confirmation dialogs on every destructive action | MP 12 | COMPLETED |
| B11.6 | Plain-language security messages, not unexplained jargon | MP 12 | COMPLETED |
| B11.7 | No sensitive data shown on the dashboard unnecessarily | MP 12 | COMPLETED (counts only, never entry names) |

### B12. Build, test and release pipeline

| ID | Requirement | Source | Status |
|---|---|---|---|
| B12.1 | GitHub repository as central source control | BR, MP 13 | COMPLETED |
| B12.2 | GitHub Actions automated builds | BR, MP 13 | COMPLETED |
| B12.3 | Automated Android APK build on every relevant push | BR, MP 13 | COMPLETED |
| B12.4 | Automated Windows build | BR, MP 13 | COMPLETED |
| B12.5 | Build artifacts published | BR, MP 13 | COMPLETED |
| B12.6 | GitHub Releases for installable versions | BR, MP 13 | COMPLETED (v0.1.0 published with both installers) |
| B12.7 | Analyzer and automated tests run in CI, blocking on failure | MP 16 | COMPLETED (format, analyse and test all blocking) |
| B12.8 | Build failures diagnosed from logs and fixed, never hidden or misreported | MP 17 | COMPLETED (three failures diagnosed and fixed; see progress log) |
| B12.9 | Public web demonstration on a shareable URL, dummy data only, labelled as a demo | BR, MP 14, FI 3 | BLOCKED (builds and is downloadable; live URL needs Pages enabled by owner) |

---

## C. Phase 2

| ID | Requirement | Source | Status |
|---|---|---|---|
| C1 | Encrypted vault file synchronised through a cloud drive | MP 9.1, FI 1 | COMPLETED (shared-folder sync; the user presses Sync now — nothing runs in the background) |
| C2 | Provider-independent sync architecture isolated from the crypto core | MP 9.1 | COMPLETED (VaultMerge is pure Dart with no file, network or platform dependency; transfer is a FileTransfer interface) |
| C3 | Upload, download, manual and automatic sync | MP 9.1 | IN PROGRESS (a single Sync now reads every other device and writes this one's file back; a background or scheduled sync is not built) |
| C4 | Version tracking, conflict detection and resolution | MP 9.1 | NOT STARTED |
| C5 | Never overwrite a newer vault with an older one | MP 9.1 | NOT STARTED |
| C6 | Recovery from interrupted transfers; integrity verification | MP 9.1 | NOT STARTED |
| C7 | Safe handling of simultaneous edits across devices | MP 9.1 | NOT STARTED |
| C8 | Optional key-file protection | MP 6, FI 4 | NOT STARTED |
| C9 | Optional FIDO2 hardware security key where supported | MP 6, FI 4 | NOT STARTED |
| C10 | Printable recovery sheet describing only real recovery mechanisms | MP 9.2, FI 6 | NOT STARTED |
| C11 | Item history | MP 9.3, FI 2 | NOT STARTED |
| C12 | Custom fields | MP 9.3, FI 2 | NOT STARTED |
| C13 | Secure file attachments | MP 9.3, FI 2 | NOT STARTED |
| C14 | Optional breach check via Have I Been Pwned k-anonymity, off by default, consent required, no plaintext password transmitted | MP 9.3, FI 5 | NOT STARTED |
| C15 | Optional "2FA available" reminders | MP 9.3, FI 5 | NOT STARTED |

---

## D. Phase 3

| ID | Requirement | Source | Status |
|---|---|---|---|
| D1 | Passkey storage via FIDO2/WebAuthn | MP 10, FI 4 | NOT STARTED |
| D2 | Secure sharing between family members | MP 10, FI 6 | NOT STARTED |
| D3 | Emergency access through a trusted contact | MP 10, FI 6 | NOT STARTED |
| D4 | Browser extension | MP 10, FI 3 | NOT STARTED |
| D5 | Additional desktop operating systems | MP 10 | NOT STARTED |

---

## E. Explicitly out of scope

Confirmed excluded, per MP 11 and FI 7. Any future request for these is a scope change.

Enterprise administration · corporate single sign-on · role-based enterprise access
control · self-hosted infrastructure · command-line tools · a central password database ·
any server capable of decrypting a user vault · mandatory subscriptions or paid cloud
infrastructure.

---

## F. Documentation deliverables

| ID | Deliverable | Status |
|---|---|---|
| F1 | Project README | COMPLETED |
| F2 | Consolidated requirements checklist (this document) | COMPLETED |
| F3 | System architecture document | COMPLETED |
| F4 | Architecture diagrams | COMPLETED |
| F5 | Design decisions and risk register | COMPLETED |
| F6 | Development progress log | COMPLETED |
| F7 | Security architecture and threat model | NOT STARTED (Stage 2) |
| F8 | Cryptographic design specification | NOT STARTED (Stage 2) |
| F9 | Vault file-format specification | NOT STARTED (Stage 2) |
| F10 | Data-model documentation | IN PROGRESS (the model is documented in the source; no standalone document yet) |
| F11 | Android installation guide | COMPLETED (`docs/installing.md`) |
| F12 | Windows installation guide | COMPLETED (`docs/installing.md`) |
| F13 | User manual for non-technical family members | COMPLETED (`docs/user-guide.md`) |
| F14 | Testing and QA report | NOT STARTED (Stage 2) |
| F15 | Known limitations | COMPLETED (initial version) |
| F16 | Capstone technical report | NOT STARTED (final stage) |

No independent security audit has been carried out, and none is claimed anywhere in this
project's documentation.
