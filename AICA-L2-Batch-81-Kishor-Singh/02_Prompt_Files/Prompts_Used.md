# Prompt Files — AICA Level 2 Capstone Project

**Project:** CA DocuFlow AI (originally built as "PDF Office Utility – Sign,
Convert, Merge & Split", then expanded across three further phases into a
full document-intelligence and office-automation platform — see Prompts 3-5)
**AI Tool Used:** Claude Code (Anthropic), powered by the Claude Sonnet 5 model — an
agentic AI coding assistant that plans, writes, tests, and packages software
autonomously from a natural-language specification.

This document records the actual prompts given to the AI agent to design,
build, test, and package the entire application, in the order they were
issued. It is included to demonstrate the **agentic AI-assisted software
development workflow** taught in AICA Level 2 (Module 1: AI Agents – Concepts
& Architecture, and Module 10: Agentic AI).

---

## Prompt 1 — Master Specification (initial request)

> You are a senior Python software architect and desktop-application developer.
> I want you to design and develop a complete, production-quality Python desktop
> application for Windows for office/document-management use.
> The application should primarily solve the problem of signing multiple PDF
> documents quickly, but should also include Word-to-PDF conversion and PDF
> merge/split utilities.
>
> [Full specification covered: application naming/branding, the bulk PDF
> signing module — multi-file selection, drag-and-drop, visible image
> signatures with crop/resize/opacity/rotation, interactive drag-to-place
> preview, predefined and custom positions, every page-selection rule
> (single/multiple/range/first/last/odd/even/every-Nth/last-N/custom
> expressions), per-file rule overrides, multiple signature layers
> (Signature/Initial/Stamp/Seal), reusable templates, page-size-aware
> percentage-based placement, output naming and collision handling with a
> "never overwrite the original" default, an optional certificate-based
> cryptographic digital signature module (clearly distinguished from a
> cosmetic image stamp) — Word→PDF conversion via Microsoft Word COM
> automation with a LibreOffice fallback plus a "Convert & Sign" one-click
> pipeline — PDF merge with per-file page ranges — PDF split in six modes —
> a visual page organizer — a configurable multi-step Batch Workflow —
> watermarking and page numbering — password-protected PDF handling —
> background-threaded batch processing with progress/cancel/retry and a
> post-batch report — a local activity/audit register — a full PySide6 GUI
> with a sidebar, dashboard, keyboard shortcuts, and light/dark theming —
> a modular project architecture (`core/`, `ui/`, `workers/`, `models/`,
> `utils/`, `tests/`) — a pytest test suite — a README, a USER_MANUAL, a
> PyInstaller build spec, and instructions for producing a Windows .exe.]
>
> Start by creating the project architecture. Then implement the core PDF
> engine. Then implement the GUI. Then integrate each module. Then test the
> workflows. Do not leave major features as pseudocode... The final result
> should be a usable Windows desktop application rather than a programming
> demonstration.

**AI agent's response (summarised):** Asked one clarifying question (where to
create the project on disk), then autonomously created 60+ source files
across `core/`, `ui/`, `ui/widgets/`, `models/`, `utils/`, `workers/`, and
`tests/`; installed and validated dependencies in a virtual environment;
wrote and ran 119 automated tests (creating synthetic PDFs on the fly to
validate encryption handling, page-size proportional placement, merge/split
correctness, and more); launched the live GUI application to confirm it
runs; built and launched a standalone Windows `.exe` via PyInstaller;
generated a simple app icon; and produced `README.md` and `USER_MANUAL.md`.

---

## Prompt 2 — Capstone submission packaging

> make document as per this [AICA_Level2_Ver1.pdf capstone submission
> instructions] for submitting the capstone project and need to link to
> github and upload there everything as per the instructions given in the
> document

**AI agent's response (summarised):** Extracted and read the official AICA
Level 2 course document to identify the exact capstone submission
requirements (a single ZIP containing a Project Summary Document, Prompt
File(s), Example File(s), Executable File(s), and Supporting Documents);
clarified GitHub setup preferences with the user (install & authenticate
`gh` CLI, repository visibility, repository name); generated real example
input/output files using the application's own engines (a sample client
agreement, a raw vs. auto-cropped signature image, a signed PDF, a merged
PDF, and split output files) to demonstrate actual functioning; authored
this Project Summary Document and prompt log; and created/pushed a private
GitHub repository containing the full source code, tests, documentation,
and this capstone submission package.

---

## Prompt 3 — Rebrand + Document Intelligence Pack (Phase 1)

> [A detailed "CA DocuFlow AI — Master Development Prompt" was provided,
> proposing a much larger AI-powered "super app" for the firm: OCR,
> AI-assisted document classification/summarization/extraction/Q&A across
> multiple providers (Anthropic/OpenAI/Gemini/Ollama), redaction, document
> comparison, PDF compression, submission-pack building, QR integrity
> stamping, a multi-user maker-checker web platform, hardware DSC token
> signing, and email/cloud integrations — along with the question: "Let me
> know if the below is possible through claude code or I should use
> antigravity for the same".]

**AI agent's response (summarised):** Explained this was not a tool-choice
question — Claude Code and Antigravity are comparable agentic coding tools
— but a scope question, and flagged a real licensing risk found via web
search (the existing PDF engine, PyMuPDF, is AGPL/commercial dual-licensed,
which matters if the app is ever distributed beyond personal/capstone use).
After the user separately asked for a second opinion on a third-party
feasibility review of the same master prompt, the AI agent validated that
review's findings and proposed splitting the work into phases. The user
then chose, via explicit questions: rename the app to "CA DocuFlow AI";
build Phase 1 = the Document Intelligence Pack (OCR, AI Assistant,
redaction, document comparison); and keep PyMuPDF despite the AGPL risk (a
deliberate, informed trade-off for a personal/capstone build). The agent
then rebranded the app (`config/app_config.py` and all UI references),
built six new processing engines (`ocr_engine.py`, `ai_provider.py`,
`document_intelligence.py`, `extraction_engine.py`, `redaction_engine.py`,
`comparison_engine.py`) and their corresponding GUI tabs, and found and
fixed two real bugs during test-writing: invoice-total verification that
silently skipped almost every real invoice (it required tax fields that
are legitimately null for intra-state invoices), and redaction that only
removed the *first* occurrence of a matched value per page (significant
because an Indian GSTIN literally embeds the entity's PAN as characters
3–12, so both must be redacted).

---

## Prompt 4 — PDF Power-Tools, Submission Pack & Integrity/QR (Phase 2)

> Let's scope Phase 2

**AI agent's response (summarised):** Proposed three options — (A) PDF
Power-Tools (compression, scan enhancement, forms, Bates numbering,
repair), (B) a Submission Pack Builder, and (C) QR integrity stamping with
local verification — explicitly declining to build a fake maker-checker
sign-off log as a weaker alternative when asked. The user chose all three.
The agent built five new engines and their GUI tabs, and in the process
found and fixed a real image-corruption bug: PyMuPDF's
`Document.update_stream()` defaults to re-compressing image bytes even
when they are already JPEG-encoded, silently corrupting two of the four
compression presets — caught by a test that verified the *actual rendered
pixels* of the output, not just that a smaller file was produced.

---

## Prompt 5 — Multi-User Platform, Hardware Signing & Integrations (Phase 3)

> Let's scope Phase 3 and make the super app complete with all
> functionalities tested

**AI agent's response (summarised):** Gave an honest breakdown of what
could genuinely be built *and tested* without external infrastructure the
agent cannot obtain on its own (a live server, OAuth app registrations,
physical hardware tokens), versus what would need the user's own follow-up
action. The user chose, via explicit questions, to build and test all
three: (1) a real multi-user web/API platform with FastAPI, real accounts,
JWT auth, and a genuine role-based maker-checker workflow, tested locally;
(2) a PKCS#11 hardware DSC token signing adapter, tested against a mocked
PKCS#11 module; (3) Outlook/Gmail/OneDrive/Google Drive integration
adapters, tested with mocked HTTP. The agent built the `webapi/` FastAPI
service (SQLAlchemy models, JWT auth, an explicit workflow state machine
with separation-of-duties enforcement, a built-in HTML/JS frontend),
`core/pkcs11_engine.py`, the OAuth + Microsoft Graph + Gmail/Drive
adapters, and a consent-gated folder-watcher engine — while explicitly
refusing one specific request implied by thorough PKCS#11 testing:
downloading and running a third-party PKCS#11 binary (SoftHSM2) to get a
live software-token test, on the grounds that autonomously downloading and
executing third-party binaries is outside what the agent should do
regardless of the tool's reputation — instead documenting the exact
self-service steps for the user to do this themselves if desired. The
platform was verified through three independent layers: the automated
pytest suite against a real temporary database, a genuinely running
`uvicorn` server hit with real HTTP requests, and the actual browser
frontend clicking through a live workflow transition.

---

## How These Prompts Were Used

Every file in this repository — the original ten processing engines and
11-tab PySide6 GUI, the Phase 1 Document Intelligence Pack, the Phase 2
PDF Power-Tools/Submission Pack/Integrity-QR modules, the Phase 3
multi-user web platform/hardware signing/email-cloud integrations, the
315-test automated suite, the README and user manual, and the PyInstaller
packaging — was generated, tested, and iterated on by the AI agent
directly from the prompts above, with the human author directing scope,
reviewing behaviour, and making the explicit trade-off decisions (licensing
risk, phasing, what to build vs. what needs external infrastructure) —
never hand-writing the implementation. This is the practical, real-world
application of agentic AI-assisted development that AICA Level 2
introduces: describing a business problem in natural language and having
an AI agent plan, code, self-test, and deliver a working solution
end-to-end, while being explicit and honest about what remains genuinely
untested without infrastructure only the user can provide.
