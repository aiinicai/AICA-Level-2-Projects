# CA PracticeOS Compliance

## AICA Level 2 Capstone Project

**Participant:**
CA Shubham Mishra

---

### 1. Project Overview

CA PracticeOS Compliance is an AI-powered compliance and practice-management platform designed for Chartered Accountant firms. It brings together document intelligence, compliance checking, client onboarding, document drafting, and accounting-system connectivity into one practical, browser-based application, backed by a real Python/FastAPI service and a permanent cloud database.

The application is a working, deployed system, not a slide-deck concept: it is publicly accessible, supports real multi-firm sign-up with admin approval, and every capability described in this document has been tested against the live deployment before being documented here.

### 2. Problem Statement

A Chartered Accountant firm's day-to-day practice work carries several recurring, largely manual burdens:

- **Manual compliance checking** — verifying that a drafted document (engagement letter, certificate, etc.) actually contains every clause a professional standard requires is easy to skip under time pressure.
- **Repetitive documentation** — engagement letters, certificates, and fee notes are drafted from scratch for every assignment, even when the structure barely changes.
- **Client onboarding effort** — client details are manually retyped from PAN cards and GST certificates into the firm's records.
- **Fragmented workflows** — client data, document drafting, and accounting-system data (e.g., Tally) typically live in separate, disconnected tools.
- **Data handling and governance** — client PAN, GSTIN, and other personal/financial details need controlled, auditable handling, not ad-hoc storage.
- **Need for accounting-system connectivity** — firms need a practical way to pull live company/ledger data from the accounting software they already use.
- **Need for standardisation and auditability** — without a shared system, document versions, approvals, and access are hard to track consistently across a firm's staff.

### 3. Project Objective

This project aims to:

- Reduce manual effort in client onboarding and document drafting.
- Improve process consistency through a shared document engine and templates.
- Automate repetitive activities using AI agents rather than blank-page drafting.
- Support compliance workflows with an explicit, evidence-based clause-checking step.
- Improve document management through a central Document Register and version history.
- Improve operational efficiency by connecting directly to a firm's existing accounting data (Tally).
- Support responsible handling of client information through role-based access control, per-firm data isolation, and the ability to revoke access at any time.

### 4. Key AI Capabilities

The following AI capabilities are actually implemented in the application (see `2_Prompt_Files/` for the exact prompts used):

- **AI Compliance Checking Agent** — checks a drafted document's text against a mandatory-clause checklist for its document type and reports a pass/fail verdict with exactly what is missing, evidenced by quotes from the text.
- **AI Client Onboarding Agent** — reads a photo/PDF of a PAN card or GST certificate and extracts a structured, validated client record (name, entity type, PAN, GSTIN, address), cross-checking that the GSTIN embeds the same PAN.
- **AI Drafting Agent** — turns one plain-English instruction (e.g. *"Prepare an engagement letter for ABC Pvt Ltd for tax audit AY 2025-26, fees Rs 50,000"*) into a filled document draft, which can then be run through the Compliance Agent.
- **Document Intelligence** — PDF text extraction and image-based (vision) reading of PAN/GST documents feed the Onboarding Agent above.
- **AI-assisted workflow automation** — the Drafting Agent's output is chained directly into the Compliance Agent, demonstrating a multi-step agent pipeline rather than a single one-shot call.
- **Tally integration/connectivity** — a working connector that pulls live company and ledger data directly from a locally running Tally Prime instance (see Section 8).

No capability beyond what is listed above is claimed for this build.

### 5. Solution Architecture

| Component | Description |
|---|---|
| **Frontend** | `CA_PracticeOS_Compliance.html` — a single-file browser application, installable as a Progressive Web App (`manifest.json`, `sw.js`, `icons/`), hosted on GitHub Pages. |
| **Backend** | Python 3.11 / FastAPI service (`backend_src/main.py`) exposing endpoints for authentication, team management, and all three AI agents. |
| **AI agents** | `backend_src/agents/compliance.py`, `onboarding.py`, `drafting.py` — each calls the Claude API for its reasoning step. |
| **Prompt layer** | `2_Prompt_Files/compliance_agent.md`, `onboarding_agent.md`, `drafting_agent.md` — the actual prompts driving each agent. |
| **Document processing** | PDF parsing and image-based extraction inside the Onboarding Agent; document template filling inside the Drafting Agent. |
| **Connectors** | `backend_src/../connectors/base_connector.py` (interface), `tally_connector.py`, and `tally_browser_relay.py` (a small local CORS relay so the browser can talk to Tally Prime's gateway — see Section 8). |
| **Data layer** | SQLAlchemy models (`backend_src/models.py`) for Tenants, Users, and Clients, on a Postgres database in production (SQLite fallback for local development). |
| **Deployment** | Frontend on GitHub Pages; backend on Render; database on Supabase Postgres. See `4_Executable_Files/deployment_link.txt` and Section 12 below. |

### 6. How the Solution Works

A typical flow through the system:

```
User input (photo/PDF, or one plain-English line, or a login)
        │
        ▼
Frontend (CA_PracticeOS_Compliance.html)
        │  HTTPS calls
        ▼
FastAPI Backend  ──────────────►  Claude API (AI reasoning step)
        │
        ▼
AI Agent (Onboarding / Drafting / Compliance)
        │
        ▼
Validation / structured output (client record, filled draft, or pass/fail verdict)
        │
        ▼
Written back into the app (Client Master, Document Register, or shown inline)
        │
        ▼
Human / professional review before the document is issued
```

For sign-up and login specifically, the flow is: a firm signs up → the platform owner is emailed an approval link → once approved, that firm's users log in with a JWT-backed session → all subsequent data (clients, documents) is scoped strictly to that firm's own tenant record in the database.

### 7. AI Agents

| Agent | Purpose | Input | Output |
|---|---|---|---|
| **Compliance Agent** | Checks a drafted document against the mandatory-clause checklist for its document type. This is the project's headline capability. | Drafted document text; document type (or auto-detected) | Pass/fail verdict, list of missing clauses, quoted evidence for clauses found |
| **Onboarding Agent** | Turns an identity/registration document into a usable client record. | Photo or PDF of a PAN card or GST certificate | Structured JSON: name, entity type, PAN, GSTIN, address, with cross-field validation |
| **Drafting Agent** | Turns a plain-English instruction into a filled document draft. | One-line natural-language instruction | Filled draft text, ready to be checked by the Compliance Agent |

Full prompt text for each agent is provided in `2_Prompt_Files/`.

### 8. Tally Integration

The application includes a working **Tally Connector**, documented in full in `5_Supporting_Documents/tally_connector_setup.docx`. In summary:

- The browser connects directly to Tally Prime's own built-in XML/HTTP gateway (default port 9000) running on the same machine or local network.
- Tally Prime's gateway does not send CORS headers, so a small local relay script (`connectors/tally_browser_relay.py`) is required in between; it forwards requests to Tally and adds the necessary headers so the browser will accept the response.
- Once connected, the app can fetch company lists and ledger accounts **live**, directly from the running Tally instance — this is a real connection, not a static mock.
- **Known constraint, stated honestly:** because Tally Prime only runs locally, this connector only works while Tally and the relay are running on the same machine as the browser being used. It cannot reach a Tally instance over the public internet. A production version of this platform would use a local sync agent that pushes data from Tally to the cloud backend on its own schedule, so the web app itself never has to connect to Tally directly — that pattern is future scope (Section 16), not built in this version.

### 9. DPDP / Data Governance Relevance

This project is directly relevant to the practical concerns raised by India's evolving Digital Personal Data Protection (DPDP) framework, because a CA firm's client records inherently include personal and financial information (names, PAN, GSTIN, addresses, contact details). The application's design reflects that in several concrete ways:

- **Controlled handling of client information** — client records are stored per-firm (per tenant) in a managed Postgres database, not scattered across local files.
- **Data governance** — every client record belongs to exactly one firm's tenant; there is no shared or global client pool.
- **Access control** — login is required to use the system; a firm's own Admin controls who on their staff (Preparer/Reviewer/Approver/Admin) can access the data, and can add, revoke, or restore any staff member's access at any time.
- **Responsible data processing** — AI extraction (Onboarding Agent) produces structured data for human review before it is saved as a client record; it does not silently overwrite existing data without a save action.
- **Security considerations** — passwords are hashed (never stored in plain text), sessions use signed JWTs, and platform-level firm access can be revoked independently of any single firm's own admin.
- **Minimisation of unnecessary exposure of personal information** — the application does not transmit client personal data to any third party beyond the AI provider call required to process a specific document, and all example/sample data shipped with this project is dummy or clearly marked as a sample.
- **Human review** — every AI output (extracted client data, a drafted document, a compliance verdict) is designed to be reviewed by the professional before being relied upon, not acted on automatically.

**This project is designed to SUPPORT compliance and data-governance practices. It is NOT itself a legal certification of DPDP compliance, and no such claim is made.** Any firm using this platform in practice remains responsible for its own independent assessment of DPDP and other applicable regulatory obligations.

### 10. Responsible AI

- **Human review** — every AI-generated output (client extraction, document draft, compliance verdict) is presented for review, not auto-committed as final.
- **Validation of AI-generated outputs** — the Compliance Agent itself is built as a two-step check (an initial verdict, then an independent self-check pass) precisely so a single model call is not blindly trusted.
- **Transparency about limitations** — this document and the in-app UI text (e.g. the "Professional Control Reminder" shown on the app's own dashboard) explicitly state that the application assists with drafting and checking, and that the signing Chartered Accountant remains responsible for verifying applicable law, professional standards, facts, and the final document.
- **No reliance on AI output without professional judgement** — the application is positioned throughout as a workflow and drafting aid, never as a replacement for the CA's own sign-off.
- **Protection of confidential information** — no real client data is included anywhere in this submission; all sample data is dummy or synthetic (see Section 6 of the security review in this package's preparation notes).
- **Avoidance of fabricated results** — the Compliance Agent is required to quote evidence from the actual document text for any clause it marks present, rather than asserting compliance without a textual basis.

### 11. Project Structure

```
Shubham-Mishra-CA-PracticeOS-Compliance/
├── README.md                          — this file
├── 1_Project_Summary_Document/        — the formal project summary (PDF)
├── 2_Prompt_Files/                    — the actual AI prompts used to build/run the agents
├── 3_Example_Files/                   — sample input documents and sample agent outputs
├── 4_Executable_Files/                — the runnable application: frontend, backend, connectors
└── 5_Supporting_Documents/            — SOP, walkthrough script, screenshots, Tally setup guide
```

- **1_Project_Summary_Document/** — `project_summary.pdf`: project title, participant/membership details, problem statement, objective, AI technology used, architecture, key features, results/benefits, and future scope.
- **2_Prompt_Files/** — the compliance, onboarding, and drafting agent prompts, plus `CLAUDE.docx`, the working build-plan document used while developing this project.
- **3_Example_Files/** — `inputs/` (sample PAN/GST images, sample drafted documents, sample prompts) and `outputs/` (the corresponding agent results, including a sample Tally data pull).
- **4_Executable_Files/** — the actual application: the frontend HTML file, the FastAPI backend source, the connectors, PWA assets, deployment configuration, and `deployment_link.txt` / `.env.example`.
- **5_Supporting_Documents/** — the Standard Operating Procedure (screenshots and section-by-section explanation of every screen), the full app walkthrough script, application screenshots, and the Tally connector setup guide.

### 12. Deployment

The application is already deployed and publicly accessible. From `4_Executable_Files/deployment_link.txt`:

- **Live application:** `https://cashubhammishra-ctrl.github.io/CA_PracticeOS_Compliance/CA_PracticeOS_Compliance.html`
- **Live backend API:** `https://ca-practiceos-backend.onrender.com`

An evaluator can open the live application link directly in any browser. It is installable as a Progressive Web App (the browser will offer "Install app" on desktop or "Add to Home Screen" on mobile). Signing up creates a pending account; access is granted once approved by the platform owner via the email-based approval flow described in Section 2 of this README.

No API keys, passwords, or other secrets are present anywhere in this submission package.

### 13. Installation / Setup

The application can also be run locally for development or evaluation:

1. **Frontend** — `4_Executable_Files/CA_PracticeOS_Compliance.html` can be opened directly in a browser, or served with any static file server (e.g. `python -m http.server`) from inside `4_Executable_Files/`.
2. **Backend** —
   ```
   cd 4_Executable_Files/backend_src
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
3. **Environment variables** — copy `4_Executable_Files/.env.example` to `.env` and fill in real values for your own deployment. **Never commit a real `.env` file.** At minimum, `ANTHROPIC_API_KEY` is required for the AI agents to function; the other variables in `.env.example` are documented inline and are optional for local/demo use (the app falls back to a local SQLite database and a randomly generated session secret if `DATABASE_URL` and `JWT_SECRET` are not set).
4. **Tally Connector (optional)** — see `5_Supporting_Documents/tally_connector_setup.docx` for the local setup steps (Tally Prime configuration and running `connectors/tally_browser_relay.py`).

### 14. Demonstration

The Capstone demonstration video for this project is submitted separately through the ICAI Google Form, using the permitted Google Drive/YouTube link mechanism. It is not embedded in this README or this package.

### 15. Limitations

The following limitations are known and are stated here honestly rather than hidden:

- The Tally Connector only works when Tally Prime and the accompanying relay script are running on the same machine/local network as the browser; it cannot reach a Tally instance over the public internet (see Section 8).
- There is currently no self-service password-reset flow for user accounts.
- Audit logging for day-to-day document actions is currently client-side/local for the offline-first document features; SaaS-level actions (login, team changes, access revocation) are logged server-side, but a unified audit trail across both is not yet built.
- Zoho Books and SAP connectors are not implemented; only the Tally connector exists in this build (see Future Scope).
- The application supports and assists compliance and documentation workflows; it does not itself constitute legal or regulatory certification of any kind (see Section 9).

### 16. Future Scope

Realistic next steps for this project, building on what already exists:

- **Zoho Books and SAP connectors**, added via the same `BaseConnector` interface already used for Tally.
- **A local sync agent for Tally** that proactively pushes data to the cloud backend, removing the need for the browser to connect to Tally directly at all.
- **Self-service password reset** for user accounts.
- **Unified, server-side audit logging** across both the document workflow and the SaaS access-control layer.

### 17. Disclaimer

This is an AICA Level 2 Capstone project submitted for academic and professional-development evaluation purposes. All AI-generated outputs produced by this application require appropriate professional review before use. The application is a demonstration of AI and automation capabilities applied to a Chartered Accountant firm's practice-management workflow, and should not be treated as a substitute for professional judgement. Any compliance, legal, or regulatory conclusions suggested by the application's output should be independently validated by a qualified professional before being relied upon.
