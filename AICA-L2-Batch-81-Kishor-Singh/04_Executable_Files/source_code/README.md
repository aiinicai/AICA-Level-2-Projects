# CA DocuFlow AI

*(formerly PDF Office Utility — Sign, Convert, Merge & Split)*

A production-quality, primarily-offline Windows desktop application for
Chartered Accountant office document management: bulk PDF signing (the
original flagship feature), Word→PDF conversion, PDF merge/split, a visual
page organizer, watermarking, page numbering, a configurable multi-step
batch workflow, local OCR, permanent redaction, document comparison, and an
opt-in AI Assistant (classification, summarization, structured data
extraction, and Ask Document) that supports Anthropic, OpenAI, Google
Gemini, or a fully local/offline Ollama model.

Beyond the desktop app, an optional **Team Deployment** layer
(`webapi/`) adds a real multi-user, role-based maker-checker approval
workflow over HTTP; hardware DSC (USB) token signing via PKCS#11; and
Outlook/Gmail/OneDrive/Google Drive integration adapters — see
[Team Deployment](#team-deployment-multi-user-web--api-platform),
[Hardware DSC Token Signing](#hardware-dsc-token-signing-pkcs11), and
[Email & Cloud Integrations](#email--cloud-integrations) below.

> **Rebranding:** the application name, organisation name and logo are all
> defined in one place — [`config/app_config.py`](config/app_config.py).
> Change `APP_NAME`, `ORGANIZATION_NAME` and drop in `assets/icons/app_icon.png`
> / `app_icon.ico` to re-brand for your firm.

> **PDF engine licensing note:** this build uses PyMuPDF (`fitz`), which is
> dual-licensed AGPL-3.0 / commercial (Artifex Software). For a private,
> non-commercial capstone/personal-use build this is low-risk, but before
> distributing this application beyond your own use (to other CAs, clients,
> or as a sold product), either purchase a commercial PyMuPDF license from
> Artifex or migrate the PDF engines to permissively-licensed alternatives
> (`pikepdf` + `pypdf` + `reportlab`). This was a deliberate, informed
> trade-off, not an oversight -- see the note in `core/pdf_engine.py`.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation (Development Setup)](#installation-development-setup)
4. [Running the Application](#running-the-application)
5. [How Signing Works](#how-signing-works)
6. [Word-to-PDF Requirements](#word-to-pdf-requirements)
7. [Digital Signature (Certificate-Based) — Capabilities & Limitations](#digital-signature-certificate-based--capabilities--limitations)
8. [OCR Setup (optional)](#ocr-setup-optional)
9. [AI Assistant Setup (optional)](#ai-assistant-setup-optional)
10. [Submission Pack Builder](#submission-pack-builder)
11. [Integrity / QR — Capabilities & Limitations](#integrity--qr--capabilities--limitations)
12. [Team Deployment (Multi-User Web / API Platform)](#team-deployment-multi-user-web--api-platform)
13. [Hardware DSC Token Signing (PKCS#11)](#hardware-dsc-token-signing-pkcs11)
14. [Email & Cloud Integrations](#email--cloud-integrations)
15. [Folder Watcher (Auto-Processing)](#folder-watcher-auto-processing)
16. [Creating the Windows EXE](#creating-the-windows-exe)
17. [Configuration & Data Storage](#configuration--data-storage)
18. [Security & Privacy](#security--privacy)
19. [Testing](#testing)
20. [Troubleshooting](#troubleshooting)
21. [Future Extension Points](#future-extension-points)

---

## Features

| Module | Capability |
|---|---|
| **Sign PDF** | Bulk-sign 1–500+ PDFs in one click; multiple signature layers (Signature/Initial/Stamp/Seal); interactive drag-and-drop placement; predefined + custom positions; page-selection rules (single/multiple/range/first/last/odd/even/every-Nth/last-N/custom expressions); per-file overrides; reusable templates; never overwrites originals by default |
| **Word → PDF** | Bulk DOC/DOCX → PDF via Microsoft Word COM automation (high fidelity) with LibreOffice headless fallback; "Convert & Sign" one-click pipeline |
| **Merge PDF** | Combine PDFs with reordering and per-file page ranges |
| **Split PDF** | Every page / by range / extract pages / every N pages / equal parts / remove pages |
| **Organize Pages** | Thumbnail grid: drag to reorder, delete, rotate, duplicate, insert blank/other-PDF pages, extract, save as new file |
| **Batch Workflow** | Chain Convert → Merge → Sign → Watermark/Seal → Save into one repeatable pipeline run over many source documents |
| **Templates** | Save/edit/delete/apply named signature/stamp configurations (percentage-based, so they work correctly on A4/Letter/Legal, portrait/landscape) |
| **Watermarking & Page Numbers** | Text/image watermarks and page numbering, engine-level (`core/watermark_engine.py`), wired into the Batch Workflow tab |
| **OCR / Scan** | Makes scanned PDFs searchable entirely offline via Tesseract OCR (English/Hindi/Kannada); skips pages that already have a text layer |
| **Edit / Redact** | Finds PAN/GSTIN/Aadhaar-like/email/phone/account-number candidates, requires explicit per-value approval, then genuinely removes the underlying content (not a cosmetic overlay) with automatic verification |
| **Compare** | Page-by-page text diff plus a rendered pixel-difference view between two document versions |
| **AI Assistant** *(opt-in, needs a provider)* | Document classification, plain-language summarization, structured data extraction (Invoices/Bank Statements/GST/Income-Tax notices) with Decimal-exact total verification, and a citation-backed Ask Document Q&A across loaded files. Supports Anthropic, OpenAI, Google Gemini, or a fully local/offline Ollama model |
| **Logs & Audit** | Rotating application log + an optional local "activity register" (audit trail) with CSV export |
| **Digital Signature (optional)** | Certificate-based PAdES/PKCS#7 signing via pyHanko, clearly distinguished from a cosmetic image stamp |
| **PDF Tools: Compress** | Four presets (Maximum Quality/Standard/Email/Maximum Compression); recompresses embedded images only, never rasterizes text; never produces an output larger than the source |
| **PDF Tools: Scan Enhance** | Deskew, orientation fix (via Tesseract OSD), denoise, and border trimming for scanned pages -- dependency-light (no OpenCV), also improves OCR accuracy |
| **PDF Tools: Forms** | List/fill/export/flatten AcroForm fields; clearly rejects unsupported legacy XFA forms rather than silently failing |
| **PDF Tools: Bates Numbering** | Continuous legal-style numbering (e.g. `KSC-000001`) across a whole batch of files, carrying the sequence from one file to the next |
| **PDF Tools: Repair** | Standalone pikepdf/qpdf-based structural repair, invokable directly on any file |
| **Submission Pack Builder** | Assembles a client's documents into one indexed, Bates-numbered PDF with an auto-generated table of contents, annexure labels, a cover letter, a SHA-256 manifest of every source file, missing-document checklist flags, and a ready-to-send ZIP |
| **Integrity / QR** | Stamps a document ID + QR before final processing, registers the truly-final file's SHA-256 in a local registry, and verifies a document against that registry later -- explicitly a local-machine check, not a public verification service (see limitations below) |
| **Team Deployment (`webapi/`)** *(optional, separate service)* | Real multi-user accounts, JWT auth, and a role-based maker-checker approval workflow (Draft → Prepared → In Review → Approved/Changes Requested/Rejected → Signing → Signed → Verified → Released → Archived) with separation-of-duties enforcement (you cannot approve your own submission) |
| **Hardware DSC Token Signing (PKCS#11)** *(optional, engine-level API — no GUI screen yet)* | Signs with a physical/software USB DSC token via PKCS#11 + pyHanko, alongside the existing PKCS#12 (.pfx) certificate-file signing |
| **Email & Cloud Integrations** *(optional, engine-level API — no GUI screen yet; needs OAuth setup)* | List/download attachments and create (never auto-send) reply drafts in Outlook or Gmail; upload/list files in OneDrive or Google Drive |
| **Folder Watcher** *(optional, engine-level API — no GUI screen yet; disabled by default)* | Polling-based "Incoming" folder auto-processor with explicit recorded consent, file-stability detection, and restart-safe de-duplication -- never runs without deliberate opt-in |

---

## Architecture

```
PDFOfficeUtility/                (repo folder name; app itself is "CA DocuFlow AI")
├── app.py                     # Entry point
├── requirements.txt
├── pdf_office_utility.spec    # PyInstaller build spec
├── config/
│   ├── app_config.py          # Branding constants (APP_NAME, icon paths, ...)
│   └── ...
├── assets/icons/               # App icon/logo (drop your own here)
├── core/                       # Pure processing engines — NO Qt/GUI code
│   ├── page_selection.py       # "1,3,5-8,last" style expression parser (used everywhere)
│   ├── pdf_engine.py           # Open/inspect PDFs, encryption handling, rendering
│   ├── signature_engine.py     # Image prep (crop/resize/opacity/rotate) + placement math + stamping
│   ├── digital_signature_engine.py  # PKCS#12 cryptographic signing (pyHanko)
│   ├── word_converter.py       # MS Word COM automation + LibreOffice fallback
│   ├── merge_engine.py         # Merge with per-file page ranges
│   ├── split_engine.py         # All 6 split strategies
│   ├── page_organizer.py       # Reorder/delete/rotate/duplicate/insert/extract
│   ├── watermark_engine.py     # Text/image watermark + page numbering
│   ├── workflow_engine.py      # Chains the above into repeatable multi-step pipelines
│   ├── ocr_engine.py           # Local Tesseract OCR -> searchable PDF
│   ├── redaction_engine.py     # Candidate detection + genuine content-stream redaction
│   ├── comparison_engine.py    # Text diff + rendered pixel-difference between versions
│   ├── ai_provider.py          # Provider-agnostic adapter: Anthropic/OpenAI/Gemini/Ollama
│   ├── document_intelligence.py # Classification, summarization, Ask-Document (with citations)
│   ├── extraction_engine.py    # Pydantic-validated structured extraction (Invoice/Bank/GST/IT)
│   ├── compression_engine.py   # 4-preset image recompression, never rasterizes text
│   ├── scan_enhancement_engine.py # Deskew/orientation/denoise/border-trim for scans
│   ├── form_engine.py          # AcroForm list/fill/export/flatten (XFA explicitly rejected)
│   ├── submission_pack_engine.py # Client submission pack: TOC, annexures, Bates, manifest, ZIP
│   ├── integrity_engine.py     # QR/Doc-ID stamping + local SHA-256 registry verification
│   ├── pkcs11_engine.py        # Hardware DSC token discovery + signing via PKCS#11 + pyHanko
│   ├── oauth_integration.py    # Shared OAuth 2.0 Authorization Code + PKCE helper
│   ├── ms_graph_integration.py # Outlook Mail + OneDrive via Microsoft Graph REST
│   ├── google_integration.py   # Gmail + Google Drive via REST
│   └── folder_watcher_engine.py # Consent-gated "Incoming" folder auto-processor
├── webapi/                     # Optional "Team Deployment" service -- separate from the
│   │                           # desktop app; NOT bundled into the .exe; run via `uvicorn webapi.app:app`
│   ├── app.py                  # FastAPI app factory, CORS, admin bootstrap, static frontend mount
│   ├── database.py             # SQLAlchemy engine/session (SQLite dev, PostgreSQL via DATABASE_URL)
│   ├── models.py                # User / Document / DocumentVersion / ApprovalAction / AuditEvent
│   ├── security.py             # bcrypt password hashing + JWT issue/verify
│   ├── workflow.py             # Maker-checker state machine (roles, transitions, separation of duties)
│   ├── schemas.py               # Pydantic request/response models
│   ├── deps.py                  # Auth dependency (re-checks is_active on every request) + role guard
│   ├── storage.py                # Content-addressed (SHA-256) document blob storage
│   ├── routers/                 # auth.py, users.py, documents.py, approvals.py
│   └── static/index.html        # Minimal built-in frontend (see "Team Deployment" below)
├── utils/
│   ├── file_utils.py           # Output naming, collision handling, temp workspace
│   ├── logging_utils.py        # Rotating log setup, structured operation logging
│   ├── validation.py           # Non-technical error messages
│   ├── config_manager.py       # settings.json persistence (AppSettings dataclass)
│   └── database.py             # SQLite: templates, recent jobs, audit trail, integrity registry
├── workers/
│   └── batch_worker.py         # QThread-based generic batch runner (progress/cancel/retry)
├── models/
│   ├── enums.py                # All controlled vocabularies (no magic strings)
│   ├── job.py                  # SigningJob / BatchResult
│   └── signature_template.py   # SignatureTemplate dataclass (percentage-based placement)
├── ui/                         # PySide6 GUI — delegates all real work to core/ and workers/
│   ├── main_window.py          # Sidebar navigation + menu/shortcuts
│   ├── sign_tab.py             # Flagship bulk-signing tab
│   ├── convert_tab.py, merge_tab.py, split_tab.py, organizer_tab.py,
│   │   ocr_tab.py, redact_tab.py, compare_tab.py, ai_assistant_tab.py,
│   │   pdf_tools_tab.py, submission_pack_tab.py, integrity_tab.py,
│   │   workflow_tab.py, templates_tab.py, settings_tab.py, logs_tab.py,
│   │   dashboard.py, about_tab.py
│   ├── ai_helper.py             # Builds an AIProvider from persisted Settings
│   └── widgets/                 # Reusable widgets (PDF preview, file table, AI settings, dialogs, ...)
└── tests/                      # pytest unit + integration tests (308 tests)
```

**Design principles enforced throughout:**

- **Separation of concerns.** `core/` has zero Qt imports and can be unit
  tested (and reused from a future CLI/service) without a GUI. `ui/` never
  contains PDF/Word processing logic — it only calls into `core/` and
  `workers/`.
- **Percentage-based placement.** Signature/watermark/stamp positions are
  stored as *percentages of page width/height*, not absolute pixels, so a
  template built on an A4 page renders correctly on Letter, Legal, and
  landscape pages too (see `core/signature_engine.resolve_placement`).
- **Never touch the original.** Every engine writes to a brand-new file
  (or a temp file that is atomically swapped into place — see
  `utils.file_utils.atomic_replace`). "Overwrite Original" is an explicit,
  opt-in output mode, never the default.
- **Off the GUI thread.** All batch operations run in a `QThread`
  (`workers/batch_worker.py`) with progress/cancel/retry signals, so the UI
  never freezes even on 500+ file batches.

---

## Installation (Development Setup)

**Requirements:** Windows 10/11, Python 3.12+ (developed against 3.12–3.14).

```bash
cd PDFOfficeUtility
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> `pywin32` (for Word COM automation) and the `pkcs11` extra of `pyHanko`
> are Windows-specific/optional — see `requirements.txt` comments. If you
> don't need certificate-based signing, you can `pip install` everything
> except `pyHanko`/`cryptography` and the app degrades gracefully (that
> module raises a clear, actionable error only when actually used).

## Running the Application

```bash
python app.py
```

On first run, the app creates its per-user data folder at
`%APPDATA%\PDFOfficeUtility\` (settings, SQLite database, logs) — no
installation step or admin rights required.

---

## How Signing Works

1. **Add PDFs** — drag & drop files/folders onto the Sign PDF tab, or use
   *Add Files* / *Add Folder* (`Ctrl+O` / `Ctrl+Shift+O`).
2. **Configure one or more signature layers** (Signature / Initial / Stamp /
   Company Seal), each with its own image, size, position and page rule.
   Load a saved **Template** or build one from scratch, then optionally
   *Save As Template* for reuse.
3. **Place it visually** — load a file into the interactive preview, drag
   the signature onto the page, resize it with the corner handle, then
   click *Use This Position For Selected Layer* to lock those coordinates
   into the layer (stored as page-relative percentages).
4. **Page rule** — choose from Single Page, Multiple Pages, Page Range,
   First/Last/First & Last/All/Odd/Even, Every Nth Page, Last N Pages, or a
   raw custom expression like `1,3,5-8,last`. "Last Page" is resolved
   **independently per file**, so a 5-page and a 50-page PDF in the same
   batch each get signed on their own actual last page.
5. **Per-file overrides** — double-click any row in the file table to give
   that one file a different page rule / position than the global setting.
6. **Output options** — output folder, naming (Keep Original / Add Suffix
   / Add Prefix / Overwrite Original — **default is Add Suffix, i.e. never
   overwrite**), and what to do on a filename collision (Skip / Replace /
   Rename Automatically — default Rename Automatically).
7. Click **SIGN ALL SELECTED PDFs** → review the confirmation screen
   (document count, total pages, signature, rule, position, output folder)
   → **Preview** or **Sign All N Documents**.
8. A progress dialog shows live per-file status; **Cancel** stops the
   remaining queue. When done, a **report** lists successes/failures (with
   reasons), exportable to CSV, with a **Retry Failed** button.

Visible signatures are images: they are a good "this document has been
approved/signed" marker but are **not** a cryptographic signature. See the
[Digital Signature](#digital-signature-certificate-based--capabilities--limitations)
section for that.

---

## Word-to-PDF Requirements

- **Preferred engine:** Microsoft Word installed on the machine. The app
  drives it via COM automation (`pywin32`), which gives the highest
  fidelity — fonts, margins, tables, headers/footers, page numbering,
  orientation, images and section breaks are preserved exactly as Word
  itself would print them.
- **Fallback engine:** [LibreOffice](https://www.libreoffice.org/) headless
  (`soffice --headless --convert-to pdf`), used automatically when Word is
  not available (or configurable explicitly in Settings). Layout fidelity
  is generally good but not guaranteed pixel-identical to Word's own
  renderer — this is why it's presented as an *optional fallback*, not the
  default.
- **"Convert & Sign"** in the Word → PDF tab chains conversion straight
  into the signing engine so, e.g., 25 Word documents can become 25 signed
  PDFs in a single click.

---

## Digital Signature (Certificate-Based) — Capabilities & Limitations

`core/digital_signature_engine.py` implements real cryptographic PDF
signing (PAdES/PKCS#7) using **pyHanko**, entirely separate from the
visible-image signature path. It supports:

- Loading a **PFX/P12 (PKCS#12)** certificate file + password
- Reason, Location, Contact Information metadata
- A visible signature box on the page (distinct from — and can be combined
  with — the cosmetic image stamp)
- **Hardware USB DSC tokens** (ePass2003, ProxKey, etc., common in India for
  GST/MCA/Income-Tax filings), via a separate PKCS#11 backend — see
  [Hardware DSC Token Signing (PKCS#11)](#hardware-dsc-token-signing-pkcs11)
  for setup and exactly what is and isn't verified about it

Both backends (PKCS#12 file and PKCS#11 hardware token) share the same
underlying `sign_with_pyhanko_signer()` signing call — see
`core/digital_signature_engine.py` and `core/pkcs11_engine.py`.

**The app never represents a visible image stamp as a verified digital
signature** — the UI, About tab, and code comments consistently distinguish
`SignatureType.VISIBLE_IMAGE` from `SignatureType.DIGITAL_CERTIFICATE`.

---

## OCR Setup (optional)

The **OCR / Scan** tab and the AI Assistant's document-reading fallback both
need [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (the
Windows build) installed separately — it is not bundled. Install it, then
either let the app auto-detect it (checks `PATH` and the standard `C:\Program
Files\Tesseract-OCR\` location) or set an explicit path in **Settings ->
OCR**. Everything runs on your machine; no page is ever uploaded anywhere
for OCR. English, Hindi and Kannada language packs are exposed in the UI
(`core/ocr_engine.SUPPORTED_LANGUAGES`) — more can be added if you install
additional Tesseract language data.

## AI Assistant Setup (optional)

The **AI Assistant** tab (classification, summarization, structured
extraction, Ask Document) is entirely opt-in — no AI call happens unless you
click an action button there. Configure a provider in **Settings -> AI
Assistant**:

| Provider | Setup | Data leaves your machine? |
|---|---|---|
| **Ollama** | Install [Ollama](https://ollama.com/), pull a model (`ollama pull llama3`), leave the default local URL | **No** — fully offline |
| **Anthropic (Claude)** | Add an API key from [console.anthropic.com](https://console.anthropic.com/) | Yes — to Anthropic's API |
| **OpenAI (GPT)** | Add an API key from [platform.openai.com](https://platform.openai.com/) | Yes — to OpenAI's API |
| **Google Gemini** | Add an API key from [aistudio.google.com](https://aistudio.google.com/) | Yes — to Google's API |

API keys are stored via the Windows Credential Manager (`keyring` package),
**never** in `settings.json` or in any log file. Use **Test Connection** in
Settings to confirm a provider is reachable before relying on it.

**Confidentiality note for a CA practice:** sending a client document's text
to a cloud AI provider means that provider's servers process it. For
sensitive filings, prefer Ollama (fully local) or confirm your cloud
provider's data-retention/zero-retention terms before use — this is a
professional judgment call the software cannot make for you (see the ICAI
Code of Ethics confidentiality obligations).

Every structured extraction (Invoice/Bank Statement/GST Notice/Income Tax
Notice) uses `Decimal` arithmetic throughout (never `float`) and leaves any
field the AI could not find in the document as `null`/missing rather than
guessing — the UI highlights missing fields in red and, for invoices, flags
a mismatch between the extracted total and the sum of taxable value + taxes.
**Every AI output is a draft for your review, never an auto-filed fact.**

---

## Submission Pack Builder

Assembles a client's documents (invoices, bank statements, replies,
evidence, etc.) into one indexed PDF: a cover letter page (optional), an
auto-generated table of contents with correct page-number cross-references,
annexure labels (A, B, C, ...), continuous Bates numbering across the whole
pack (optional), and a JSON manifest recording each source file's name,
category, SHA-256 hash, and exact page range within the combined document.
A checklist of expected document categories flags anything missing before
you send the pack out. The combined PDF + manifest are also bundled into
one ZIP. Source files are never modified — only their hashes are recorded,
proving what went into the pack without altering the originals.

## Integrity / QR — Capabilities & Limitations

The **Integrity / QR** tab stamps a document ID and QR code onto a page
*before* any further processing, then registers the SHA-256 hash of the
*truly final* file (after OCR/watermarking/signing) in this computer's
local SQLite database. Later, **Verify Document** re-reads that ID from
the file's text, looks it up locally, and reports whether the current
bytes still match what was registered.

**This is explicitly a local-machine registry, not a public verification
service.** Scanning the QR code, by itself, proves nothing to anyone else —
verification only works by opening this same app against this same
database (or a copy of it). A genuinely public "scan this QR to verify"
experience needs a real server with its own database, which is Phase 3
(web/API) scope, not something this desktop build fakes. The QR payload
encodes a stable ID specifically so a future server-backed version can
resolve the same identifier without changing anything already stamped.

> **Status:** the Phase 3 web/API platform (below) now exists, but the
> Integrity/QR registry has *not* been rewired to use it — it is still the
> desktop app's own local SQLite database. Pointing QR verification at the
> `webapi/` service's own document registry (so a scan can be checked from
> any device, not just this machine) is a natural follow-on, not yet built.

---

## Team Deployment (Multi-User Web / API Platform)

`webapi/` is a separate FastAPI service providing real multi-user accounts,
JWT authentication, and a role-based maker-checker approval workflow over
HTTP. It is **not** part of the desktop app or the desktop `.exe` — it is
its own thing you run separately, for a firm that wants documents to move
through Preparer → Reviewer → Signatory → Auditor → Partner sign-off with a
server as the source of truth, instead of everyone working on local files.

**Roles:** Admin, Maker, Checker, Approver, Signatory, Auditor, Client.

**Workflow (`webapi/workflow.py`):**

```
Draft --submit_for_review--> Prepared --send_to_checker--> In Review
In Review --approve--> Approved            (Checker/Approver/Admin)
In Review --request_changes--> Changes Requested
In Review --reject--> Rejected
Changes Requested --resubmit--> Prepared
Approved --start_signing--> Signing --confirm_signed--> Signed
Signed --verify--> Verified --release--> Released --archive--> Archived
```

(Admin can also `cancel` a document from any non-terminal state, moving it
to a separate `Cancelled` end state — not shown above for clarity.)

Every transition checks the actor's role, and the four `In Review`
transitions additionally enforce **separation of duties**: the same person
who last acted on a document as its Maker cannot also Approve/Reject/
Request-Changes on it — the API returns HTTP 409 if they try. Uploading a
new version of a document that had already moved past Draft resets it back
to Draft (a reviewed document doesn't stay "approved" once its content
changes).

**Running it locally:**

```bash
pip install -r requirements.txt
set DOCUFLOW_ADMIN_PASSWORD=choose-a-strong-password
uvicorn webapi.app:app --reload
```

Open `http://127.0.0.1:8000/` for the built-in frontend, or `/docs` for the
interactive OpenAPI/Swagger UI. On first run (empty database) an Admin
account is created automatically — username `admin` (or
`DOCUFLOW_ADMIN_USERNAME`), password from `DOCUFLOW_ADMIN_PASSWORD` if set,
otherwise a random one is generated and printed once to the console (copy
it immediately — it is not shown again and is not recoverable). Log in as
Admin to create Maker/Checker/Approver/etc. accounts for your team (there is
deliberately no public self-registration endpoint — this is an internal
firm tool, not a public SaaS signup).

**Configuration (environment variables):**

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | local SQLite file next to `webapi/` |
| `DOCUFLOW_ADMIN_USERNAME` / `DOCUFLOW_ADMIN_PASSWORD` | First-run bootstrap admin | `admin` / randomly generated |
| `DOCUFLOW_STORAGE_DIR` | Where uploaded document bytes are stored on disk | local `storage/` folder |
| `DOCUFLOW_JWT_SECRET` | JWT signing secret — **set this explicitly in production**, otherwise a random one is generated at process start (which invalidates every session on restart) | random |
| `CORS_ALLOW_ORIGINS` | Comma-separated allowed origins | `*` (tighten this before exposing beyond localhost) |

For a real Postgres-backed deployment: `pip install psycopg2-binary` and set
`DATABASE_URL=postgresql://user:pass@host/dbname`.

**Frontend:** `webapi/static/index.html` is a single-file, dependency-free
HTML+vanilla-JS page (login, upload, document table, all 12 workflow
actions including cancel, status pills) — a deliberate, documented substitute for a full
React/TypeScript SPA (no Node.js toolchain in the environment this was
built in). It talks to the same REST API any other client would use;
swapping in a proper React build later means only replacing this one file,
not touching `webapi/routers/` or `webapi/workflow.py`.

**What is and isn't verified:** the workflow state machine has 15 pure-logic
tests with no database at all (`tests/test_webapi_workflow.py`), and the
full HTTP API — including a complete Draft→Released walkthrough across five
different role accounts, the self-approval 409 rejection, immediate token
invalidation on account deactivation, and the version-upload reset-to-Draft
behaviour — is tested end-to-end via FastAPI's `TestClient` against a real
temporary SQLite database (`tests/test_webapi_api.py`). It has also been
manually driven through a real running `uvicorn` process and the actual
browser frontend, clicking through a live workflow transition. **What is
genuinely not tested here:** running it under a real production
ASGI/reverse-proxy setup (nginx/IIS + gunicorn/hypercorn), a real PostgreSQL
database at scale, or actual internet-facing deployment/HTTPS/hosting —
those depend on infrastructure (a server, a domain, TLS certificates) that
only you can provide, and are configuration/ops work rather than something
this codebase can self-verify.

---

## Hardware DSC Token Signing (PKCS#11)

`core/pkcs11_engine.py` adds signing with a physical (or software) USB
Digital Signature Certificate token via the PKCS#11 standard, alongside the
existing `.pfx`/PKCS#12 file-based signing in
`core/digital_signature_engine.py`. This is what most Indian CA-office DSC
tokens (Class 3, from providers like eMudhra, Capricorn, or Sify) actually
are: a USB device exposing a PKCS#11 interface via a vendor driver `.dll`,
rather than a portable certificate file.

**Current state: engine-only, not yet wired into the desktop UI.** The
Sign tab's dialog only exposes PKCS#12 (`.pfx` file) signing today; there is
no PKCS#11 module-path/slot/PIN screen in the GUI yet. `core/pkcs11_engine.py`
is a complete, tested Python API you (or a future UI screen) can call
directly:

```python
from core.pkcs11_engine import list_available_tokens, list_certificates_on_token, Pkcs11SigningBackend

tokens = list_available_tokens("C:/Windows/System32/eToken.dll")
certs = list_certificates_on_token("C:/Windows/System32/eToken.dll", slot_id=tokens[0].slot_id, pin="1234")
backend = Pkcs11SigningBackend(module_path="C:/Windows/System32/eToken.dll", slot_id=tokens[0].slot_id, pin="1234")
# backend.sign(request) -- same SigningBackend protocol as the PKCS#12 backend
```

**To use it with a real token, once you have (or add) a way to call the
above:**

1. Install the token vendor's PKCS#11 driver (it ships with the token, or
   is downloadable from the vendor's site) — this gives you a `.dll` path
   such as `C:\Windows\System32\eToken.dll` or similar.
2. `pip install python-pkcs11` (already in `requirements.txt`).
3. List slots/certificates as above, then sign using the matching slot ID
   and the token's PIN.

**Common pitfall:** many Indian DSC token drivers still ship as 32-bit-only
DLLs. Loading a 32-bit `.dll` from a 64-bit Python process fails with an
`OSError` — `core/pkcs11_engine.py` detects this specific case and raises a
message pointing you at installing 32-bit Python (or asking the vendor for
a 64-bit driver) rather than a bare, confusing `OSError`.

**What is and isn't verified:** `core/pkcs11_engine.py` has 11 unit tests
(`tests/test_pkcs11_engine.py`) covering token/certificate listing, PIN
error handling (incorrect/locked PIN), and the signing call's argument
wiring — but every one of them runs against a **hand-installed fake
`pkcs11` Python module**, not a physical token or even a software token
(SoftHSM2). No PKCS#11 binary, driver, or software token was downloaded or
executed as part of building this: that was a deliberate boundary, not an
oversight, since installing and running third-party native binaries
autonomously is outside what an agent should do without you directly
driving it.

**Separately, the underlying cryptographic signing path** (`pyHanko`
PAdES/PKCS#7 signing + trust-chain/tamper-detection validation) *is*
genuinely end-to-end tested with a real self-signed certificate — see
`tests/test_digital_signature_engine_e2e.py` — so what remains unverified
is specifically the PKCS#11 hardware-token *adapter layer*, not the
signing logic underneath it.

**If you want to verify the PKCS#11 layer yourself against a real (if
software) token**, SoftHSM2 is the standard tool for this and is safe to
install — but you should install and run it yourself:

1. Download SoftHSM2 for Windows from
   [github.com/disig/SoftHSM2-for-Windows](https://github.com/disig/SoftHSM2-for-Windows)
   (releases page) and install it.
2. Initialize a token: `softhsm2-util --init-token --slot 0 --label "test"`
   (set a SO PIN and a user PIN when prompted).
3. Generate a test key/certificate into that token (SoftHSM2's docs and
   `pkcs11-tool` from OpenSC cover this) or import an existing test `.pfx`.
4. Point the app's PKCS#11 module path at SoftHSM2's `.dll`
   (typically `C:\SoftHSM2\lib\softhsm2-x64.dll`), select the slot, and sign
   a test document with the user PIN you set.

---

## Email & Cloud Integrations

Two REST-based adapters — `core/ms_graph_integration.py` (Outlook Mail +
OneDrive, via Microsoft Graph) and `core/google_integration.py` (Gmail +
Google Drive) — let the app list recent messages, download attachments,
create reply **drafts** (never auto-send — sending is always a separate,
explicit call), and upload/list files in cloud storage. Both share the
generic OAuth 2.0 Authorization Code + PKCE flow in
`core/oauth_integration.py`, and both talk to the provider's plain REST API
directly (not the `msal`/`google-api-python-client` SDKs) for consistency
and mockability with every other adapter in this codebase.

**These need an OAuth app registration you create yourself** — this app
has no shared/pre-registered client ID, since that would mean every
installation shares one app identity and quota, which is not appropriate
for a real deployment.

**Microsoft (Outlook/OneDrive) setup:**

1. Go to [portal.azure.com](https://portal.azure.com) → Azure Active
   Directory → App registrations → New registration.
2. Name it (e.g. "CA DocuFlow AI"), choose "Accounts in this organizational
   directory only" (or as appropriate for your tenant), and add a
   **public client / native** redirect URI, e.g. `http://localhost:8400/callback`.
3. Under Authentication, enable "Allow public client flows" (this app uses
   PKCE, not a client secret).
4. Under API permissions, add Microsoft Graph **delegated** permissions:
   `Mail.Read`, `Mail.ReadWrite` (for drafts), `Mail.Send` (only if you want
   the send step), `Files.ReadWrite` (OneDrive).
5. Copy the Application (client) ID and your tenant ID into the app's
   Settings.

**Google (Gmail/Drive) setup:**

1. Go to [console.cloud.google.com](https://console.cloud.google.com) →
   create/select a project → APIs & Services → Enabled APIs → enable
   **Gmail API** and **Google Drive API**.
2. APIs & Services → OAuth consent screen: configure it (Internal if you
   have Google Workspace, External + test users otherwise), and add scopes
   `gmail.readonly`, `gmail.compose`, `drive.file`.
3. APIs & Services → Credentials → Create Credentials → OAuth client ID →
   type **Desktop app**.
4. Copy the Client ID (and secret) into the app's Settings.

**What is and isn't verified:** both adapters have thorough tests
(`tests/test_ms_graph_integration.py`, 13 tests;
`tests/test_google_integration.py`, 10 tests;
`tests/test_oauth_integration.py`, 9 tests for the shared PKCE flow) —
every one of them runs against **mocked HTTP responses**, not a live
Microsoft/Google account. No real OAuth app registration, consent screen,
or account was used in building or testing this, because that requires
credentials only you can create. Field mapping (subject/sender/attachment
detection), base64/base64url attachment decoding, the never-auto-send
draft/send split, and error surfacing (expired token, insufficient
permissions, quota exceeded) are all verified against realistic mocked
payloads shaped like the real Graph/Gmail API responses; the actual network
calls to `graph.microsoft.com` / `gmail.googleapis.com` themselves are not.

---

## Folder Watcher (Auto-Processing)

`core/folder_watcher_engine.py` implements the "watch an Incoming folder
and automatically apply a saved template" feature — **disabled in every
sense until explicitly configured**. There is no code path that starts
watching without a populated `WatcherConsent` with `enabled=True`, a
non-empty `acknowledgement_text` (the exact text you were shown and agreed
to) and `acknowledged_by`, and all four folders (Incoming/Processing/Done/
Failed) configured. An expired `valid_until` also blocks it.

It is deliberately **polling-based** (checked on a timer) rather than
OS-event-based: a file only gets processed once its size is unchanged
across two consecutive scans (so an in-progress copy is never touched), and
every processed file's SHA-256 is recorded in a small local JSON registry
so a restart never reprocesses the same file twice. One bad file (an
exception from your processing function) is routed to a Failed folder with
the error message and does not block the rest of the batch.

**What is and isn't verified:** 17 tests (`tests/test_folder_watcher_engine.py`)
cover every consent-gating rule, stability detection across scans (including
a file still being copied), success/failure routing, the one-bad-file-
doesn't-block-others case, de-duplication surviving a simulated restart
(a fresh service instance loading the same registry file), pause/resume,
dry-run, extension filtering, and the max-files-per-run cap — all against
a real temp filesystem, no mocking needed since this module has no external
service dependency. There is currently no UI wired up to configure/start
it from the desktop app (it exists as a tested, ready-to-wire engine); doing
so is a natural next step, not yet built.

---

## Creating the Windows EXE

Everything below assumes your virtual environment is active and
`requirements.txt` (which includes `pyinstaller`) is installed.

### Portable folder build (recommended)

```bash
pyinstaller pdf_office_utility.spec
```

Output: `dist/PDFOfficeUtility/PDFOfficeUtility.exe` plus its supporting
files in the same folder. Zip the whole `dist/PDFOfficeUtility/` folder to
distribute — end users need **no** Python installation. This form starts
faster and is less likely to be flagged by antivirus heuristics than a
single-file build.

### Single-file EXE

Open `pdf_office_utility.spec` and follow the comment near the bottom:
comment out the `EXE(...)`/`COLLECT(...)` pair and uncomment the
single-file `EXE(...)` block, then rebuild. This produces one
`PDFOfficeUtility.exe` that self-extracts to a temp folder on each launch
(slightly slower startup).

### Optional: a real Windows installer

Wrap the portable folder build with either:

- **[Inno Setup](https://jrsoftware.org/isinfo.php)** (free) — point its
  script at `dist/PDFOfficeUtility/`, set the app name from
  `config/app_config.py`, and it produces a signed-or-unsigned
  `Setup.exe` with Start Menu shortcuts and an uninstaller.
- **[NSIS](https://nsis.sourceforge.io/)** — similar, script-based
  alternative.

Neither is bundled in this repo (they're external, standalone tools), but
both work directly against the PyInstaller output folder with no code
changes required.

### Icon

Drop a `.ico` file at `assets/icons/app_icon.ico` (and a `.png` at
`assets/icons/app_icon.png` for in-app display) before building — the spec
file picks it up automatically if present.

---

## Configuration & Data Storage

All user/firm data lives under `%APPDATA%\PDFOfficeUtility\`:

- `settings.json` — non-sensitive preferences (`utils/config_manager.py`)
- `app_data.db` — SQLite: signature templates, recent-jobs list, and the
  optional activity register/audit trail (`utils/database.py`) — **never**
  PDF/Word file contents, **never** passwords
- `logs/pdf_office_utility.log` — rotating application log (5 MB × 5 files)

Nothing is written under the installation folder, so a read-only/portable
install still works, and re-installing the app doesn't wipe preferences.

---

## Security & Privacy

- **Offline by default.** Every PDF operation (signing, merge, split,
  organizing, watermarking, OCR, redaction, comparison) runs entirely on
  this computer with no network call. The one deliberate exception is the
  opt-in **AI Assistant**: if you configure a cloud provider (Anthropic/
  OpenAI/Gemini), the document text you explicitly submit to that feature
  is sent to that provider's API — nothing else in the app does this, no
  AI call happens automatically, and choosing Ollama keeps AI features
  fully local too.
- **Passwords and API keys are never persisted in plain text.** A PDF's
  open-password and a certificate's PFX password are held only in memory
  for the duration of the current batch run; AI provider API keys are
  stored via the OS credential store (Windows Credential Manager), never
  in `settings.json` or any log file.
- **Owner-permission restrictions are respected.** If a PDF's owner
  password disallows modification, the app refuses to process it rather
  than bypassing that restriction (see `core/pdf_engine.open_pdf`).
- **Temp files are cleaned up.** Every batch uses a
  `utils.file_utils.TempWorkspace` that is deleted once the batch finishes,
  is cancelled, or errors.
- **Originals are never modified** unless the user explicitly selects
  "Overwrite Original" as the naming mode — and even then, the write goes
  through a temp file + atomic replace so a crash mid-write cannot corrupt
  the source.

---

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

308 tests cover: page-selection expression parsing (all shorthand forms and
combinations), PDF opening/encryption/permission handling across portrait
A4, landscape A4, Legal, mixed-size and single/100-page documents, the
signature placement math (proportional scaling across page sizes — the
core correctness requirement), end-to-end signing (last page / all pages /
multiple layers / per-file overrides / original-never-modified), merge
(ordering, per-file ranges, sparse selections), all six split strategies,
real end-to-end OCR (a synthetic scanned page recovers correct, searchable
text), genuine content-stream redaction (values are verified absent from
the output, including the India-specific case of a PAN embedded inside a
GSTIN), document comparison (text diff + rendered pixel diff), the AI
provider adapter for all four backends (mocked HTTP, no live keys used),
classification/summarization/Ask-Document/extraction logic (stub providers,
Decimal-exact invoice-total verification), image compression (a regression
test catches the exact real bug found during development where PyMuPDF's
`update_stream()` default compression silently corrupted re-encoded JPEG
streams), scan enhancement (deskew/border-trim/denoise verified against a
deliberately skewed/bordered/noisy synthetic scan), AcroForm list/fill/
export/flatten, Bates numbering continuity across multiple files, standalone
PDF repair, the submission pack builder (page-accurate table of contents,
manifest hashes, missing-checklist detection), the integrity engine (a
genuine end-to-end stamp → process → register → verify → tamper-detect
cycle), the page organizer
(reorder/delete/rotate/duplicate/insert/extract),
output-naming and collision-handling policies, watermarking/page-numbering,
workflow chaining, corrupt-PDF repair via pikepdf, `.docx` structural
inspection, the certificate-signing engine's error handling, and the Sign
tab's actual batch-processing closure end-to-end (not just mocked).

**Phase 3 additions:** genuine end-to-end PKCS#12 certificate signing with
real trust-chain validation and tamper detection (a flipped byte is
confirmed to break signature integrity); the maker-checker workflow state
machine in pure logic (no database) plus the full HTTP API against a real
temporary SQLite database, including a complete Draft→Released walkthrough
across five different role accounts and the self-approval 409 rejection;
the PKCS#11 hardware-token adapter and the Outlook/Gmail/OneDrive/Drive
integrations against, respectively, a hand-installed fake `pkcs11` module
and mocked HTTP (see [Hardware DSC Token Signing](#hardware-dsc-token-signing-pkcs11)
and [Email & Cloud Integrations](#email--cloud-integrations) above for
exactly what that does and doesn't verify); and the folder watcher's
consent gating, file-stability detection, and restart-safe de-duplication
against a real temp filesystem.

---

## Troubleshooting

| Problem | Cause / Fix |
|---|---|
| "Microsoft Word is not installed or could not be automated" | Install Word, or switch the engine to LibreOffice in Settings |
| "Neither Microsoft Word nor LibreOffice was found" | Install LibreOffice and/or set its `soffice.exe` path in Settings |
| "`<file>` is password protected" | Enter the PDF's open password when prompted; if it has no open password but you still see this, the file uses owner-only encryption — an app default in some scanners |
| "...protected against modification by its owner password" | The PDF's owner explicitly disallowed edits; the app will not bypass this — obtain a copy without that restriction |
| "Output file already exists" and nothing happens | Check the collision policy in Output Options — default is Rename Automatically, but Skip silently skips |
| Certificate signing raises an import error | `pip install pyHanko` — it's an optional dependency, only required for certificate-based signing |
| A USB DSC token isn't recognized | Enter your token vendor's PKCS#11 `.dll` path in the signing dialog — see [Hardware DSC Token Signing](#hardware-dsc-token-signing-pkcs11) |
| PKCS#11 signing raises an `OSError` on module load | Usually a 32-bit-only vendor driver loaded from 64-bit Python — install 32-bit Python or ask the vendor for a 64-bit driver, see [Hardware DSC Token Signing](#hardware-dsc-token-signing-pkcs11) |
| `webapi` won't start / `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` — the web/API platform has its own dependencies (FastAPI, SQLAlchemy, etc.) beyond the desktop app's |
| Maker-checker action returns HTTP 409 | Separation of duties: you cannot approve/reject/request-changes on a document you yourself last acted on as Maker — have a different role/account do it |
| App looks "wrong" in dark mode | Settings → Theme → System/Light/Dark |
| "Tesseract OCR is not installed" | Install from github.com/UB-Mannheim/tesseract/wiki, or set its path in Settings → OCR |
| AI Assistant says "not configured" | Add an API key (or select Ollama) in Settings → AI Assistant, then use Test Connection |
| AI provider returns an HTTP 401/403 error | Your API key is invalid, expired, or lacks quota — check it on the provider's own dashboard |
| Ollama "not reachable" | Make sure `ollama serve` is running and a model is pulled (`ollama pull llama3`) |
| Extraction result has many fields marked "missing" | Expected when the document doesn't clearly state that value, or the OCR/text quality is poor — always review before use, never treat a null as zero |
| Redaction still shows a value elsewhere in the document | A value can appear in more than one form/place (e.g. a PAN embedded inside a GSTIN) — the app redacts every literal occurrence it finds, but always visually re-check the output before sharing it |

---

## Future Extension Points

As of Phase 3, PDF compression, OCR, email-attachment processing,
Google Drive/OneDrive/Outlook integration, a maker-checker approval
workflow, PKCS#11 hardware-token signing, multi-user/role-based
permissions, and a consent-gated folder-watcher service are all built and
tested (to the extent described in their own sections above). What
genuinely remains open:

- **PDF→Word/Excel/PowerPoint conversion** — not built in any phase.
- **Public/server-backed QR verification** — the Integrity/QR registry is
  still local-machine-only; wiring it to the `webapi/` service's own
  database (so a scan can be checked from any device) is a natural
  follow-on.
- **A production deployment of `webapi/`** — real hosting, a domain, TLS,
  a production ASGI/reverse-proxy setup, and a PostgreSQL database at
  scale are all configuration/infrastructure work only you can do; nothing
  here has been tested against that (see [Team Deployment](#team-deployment-multi-user-web--api-platform)).
- **Live PKCS#11 hardware verification** — the adapter is thoroughly
  tested against a mocked module; verifying it against a real or software
  (SoftHSM2) token is a self-service step described in
  [Hardware DSC Token Signing](#hardware-dsc-token-signing-pkcs11).
- **Live Outlook/Gmail/OneDrive/Drive verification** — the adapters are
  thoroughly tested against mocked HTTP; exercising them against a real
  account needs an OAuth app registration only you can create, described
  in [Email & Cloud Integrations](#email--cloud-integrations).
- **A UI for the folder watcher** — the engine is built and tested but not
  yet wired into the desktop app's settings/tabs.
- **A full React/TypeScript frontend** for `webapi/`, replacing the current
  single-file HTML+vanilla-JS substitute (see [Team Deployment](#team-deployment-multi-user-web--api-platform)).
