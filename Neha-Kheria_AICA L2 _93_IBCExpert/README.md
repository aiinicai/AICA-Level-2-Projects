# IBC Expert

**Submitted by:** Neha Kheria
**Batch:** 93
**Course:** AICA Level 2 Certificate Course — Capstone Project

## About the project

IBC Expert is an offline-first Windows desktop application for insolvency
practitioners, built to help manage clients, documents, workflow timelines,
and recommendations connected to matters under the Insolvency and
Bankruptcy Code. The application runs entirely on the user's own computer:
a local FastAPI service talks only to `127.0.0.1`, the UI is rendered
through a native desktop window (pywebview), and all data is stored in a
local, encrypted SQLite database. No client data is ever sent to the
internet.

### Key features
- Client and matter management
- Encrypted document vault with OCR-assisted text extraction
- A searchable legal database (point-in-time versioned, full-text search)
- Workflow engine for stage tracking, statutory-style date rules, and
  recommendations, with every rule requiring an explicit cited source
- Form generation
- A tamper-evident, HMAC-chained audit log of user actions
- A 30-day evaluation trial with an offline, cryptographically signed
  licence-activation system for full/owner use

### Security design highlights
- A master password derives the key used to protect the local database
  and document vault (per-object keys via HKDF; authenticated encryption
  for vault/backup payloads)
- Licences are signed offline with Ed25519; the customer/trial build only
  ever ships the public verification key, never a private key
- A process-level network guard restricts the app to loopback-only
  connections — no background telemetry, scraping, or remote sync
- No statutory deadline, form, or legal holding is hardcoded — workflow
  rules require a cited source and an explicit human verification step
  before they can be used

## Tech stack
Python 3.14, FastAPI, SQLite, pywebview (desktop shell), PyInstaller
(Windows packaging).

## Running the application

This submission contains full source code. To run it locally:

1. Install Python 3.14 (64-bit) from python.org, ensuring "Add python.exe
   to PATH" is checked during installation.
2. Open a terminal in this project folder.
3. Run:
   ```
   python launch_desktop.py
   ```
   On first run this installs the required dependencies automatically
   (internet access needed for this one-time step only) and then opens
   the application window.
4. On first use, you will be asked to create a local master password.

The application starts in a 30-day evaluation trial by default. See
`docs/OWNER_LICENSING_MANUAL.md` for how offline licence activation works.

## Project documentation

Further documentation is included under `docs/` and in the top-level
`ARCHITECTURE.md`, `PROJECT_STATE.md`, and `RELEASE_CHECKLIST.md` files,
covering the installation process, user manual, API reference, developer
integration notes, and the security/licensing design in more detail.

## Declaration

This project is submitted as original work for the AICA Level 2
Certificate Course capstone project requirement.
