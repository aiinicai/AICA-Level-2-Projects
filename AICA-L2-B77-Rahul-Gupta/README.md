# CompanyVal AI — AI-Assisted Business Valuation

**Upload. Understand. Question. Simulate. Value.**

An ICAI AICA Level 2 capstone prototype: a full-stack, working valuation platform that
extracts financial statements with Python, independently verifies them with Gemini vision,
runs an adaptive rule-driven AI interview, values the business with a deterministic Python
engine (DCF + Market Multiple + Adjusted NAV), simulates scenarios live, and generates a
professional AI-assisted valuation report.

> **Core principle:** every authoritative number is computed by the deterministic Python
> engine. Gemini verifies, asks, interprets and explains — it never calculates or invents
> a financial value. AI failures never break the core app.

---

## Architecture

```
React (Vite + TS + Tailwind + Recharts)          ←  visual layer (mockup-faithful)
        │  REST (/api/*)
FastAPI + SQLAlchemy (SQLite dev / PostgreSQL)   ←  workflow, audit, persistence
        │
├── Document engine   PyMuPDF extraction → page rendering (200 DPI PNG)
│                     → Gemini vision verification → reconciliation → human review → lock
├── Financial engine  canonical schema, Indian number parsing (₹/lakh/crore/1,25,00,000),
│                     ratios, accounting validation, deterministic rules engine
├── Interview engine  rule triggers × materiality × uncertainty → 8–15 adaptive questions
├── Valuation engine  5-yr FCFF DCF, EV/EBITDA multiple, adjusted NAV, weighted central
│                     estimate, scenarios, sensitivity heatmap + tornado
└── Reporting         Jinja2 HTML → PDF (xhtml2pdf; WeasyPrint auto-used if installed)
```

The browser **never** calls Gemini. The API key is entered in Settings, validated
server-side, encrypted (Fernet + `COMPANYVAL_MASTER_KEY`) and never returned again.

## Quick reference

Day-to-day commands once the backend venv and frontend `node_modules` already exist (see
**Backend setup** / **Frontend setup** below for the first-time walkthrough). Run from the
repo root.

**Run the app.** Each server runs in the foreground, so these need **two separate
terminals** — chaining them in one shell leaves the frontend never starting.

Terminal 1 — API on :8000:

```bash
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 --reload
```

Terminal 2 — the web app on :5173:

```bash
cd frontend && npm run dev
```

Then open **http://localhost:5173** — that is the app. Port 8000 serves only the
API; opening it in a browser just points you back here, and `/docs` has the
interactive API reference.

**Reset all data to the fresh seeded state** — safe to run with the server up:

```bash
cd backend && .venv/bin/python -m app.seed --reset
```

> Do **not** reset by deleting `storage/companyval.db` while the backend is running.
> Unlinking the file leaves the live server writing to an orphaned inode: uploads look
> like they succeed, then disappear the moment the server restarts and opens the newly
> created file. `--reset` drops and recreates the tables in place, so there is only ever
> one database file.

**Set up on a new machine:**

```bash
git clone https://github.com/rahulguptaca/AICA-L2-B77-Ghaziabad-Capstone_Project.git
cd AICA-L2-B77-Ghaziabad-Capstone_Project
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt \
  && .venv/bin/python -m app.seed
cd ../frontend && npm install
```

**Free a stuck port** (swap in whichever port is stuck — 8000 backend, 5173 frontend):

```bash
lsof -ti :8000 -ti :5173 | xargs kill
```

## Prerequisites

- Python 3.12+ (tested on 3.14)
- Node.js 20+
- (optional) PostgreSQL 15+ — SQLite is the zero-config default
- (optional) A Google Gemini API key for visual verification, adaptive question drafting,
  AI insights and AI report narrative. Everything else works without it.

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment

```bash
cp ../.env.example ../.env      # optional — sane defaults work out of the box
```

Key variables (see `.env.example`): `DATABASE_URL`, `SECRET_KEY`,
`COMPANYVAL_MASTER_KEY` (Fernet key for encrypting the stored Gemini key — generate with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`;
in local dev a key is auto-generated at `storage/.master_key`), `UPLOAD_DIR`, `REPORT_DIR`,
`FRONTEND_URL`.

### Database & demo seed

```bash
python -m app.seed        # creates tables + seeds the ABC Food Pvt. Ltd. demo journey
```

To wipe everything and reseed fresh, delete `storage/companyval.db` and re-run the command
above (see **Quick reference** for the one-liner).

Tables are auto-created on startup for development. For managed migrations, Alembic is
wired to the app metadata:

```bash
alembic -c alembic.ini revision --autogenerate -m "initial"
alembic -c alembic.ini upgrade head
```

### Run the backend

```bash
python -m uvicorn app.main:app --port 8000 --reload
```

OpenAPI docs: http://localhost:8000/docs

## Frontend setup

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173 (proxies /api → localhost:8000)
```

Production build: `npm run build` (output in `frontend/dist/`).

## Gemini configuration

1. Open **Settings → AI Configuration** in the app.
2. Paste your Gemini API key → **Save**. The backend validates it, tests the connection,
   encrypts it and stores only the ciphertext. The UI thereafter shows `••••` + Connected.
3. Toggles: Structured Output (JSON), Visual Verification, AI Final Report.
   Default model: **Gemini 3.6 Flash** (provider adapter — swappable without touching the
   financial engine, see `app/services/ai/`).

Without a key: extraction, review, locking, interview (deterministic phrasing), valuation,
simulation, insights (engine-grounded) and reports (deterministic narrative) all still work.

## The demo case

`ABC Food Pvt. Ltd.` ships fully seeded (illustrative figures): three verified financial
years (FY2022-23 → FY2024-25, 44% latest revenue growth deliberately triggering the
`REV_GROWTH_HIGH` rule), an in-flight adaptive interview, accepted assumptions with an AI
recommendation trail, NAV revaluation schedule, run history and engine-grounded insights.
Four peer companies populate the dashboard.

Full journey on your own data: **New Valuation → Financials (upload 3 years of PDF/XLSX)
→ review discrepancies → Lock → AI Interview → Valuations (Calculate) → Simulation Lab →
AI Insights → Reports (Export PDF)**.

## PDF dependencies

- **Extraction/rendering:** PyMuPDF (bundled wheel, no system deps).
- **Report PDF:** xhtml2pdf (pure Python, bundled). If WeasyPrint is installed
  (`brew install pango` + `pip install weasyprint`), it is preferred automatically for
  higher CSS fidelity. HTML export always works.
- OCR is intentionally not attempted on digital PDFs; scanned PDFs are rejected with a
  clear message rather than guessed at.

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

38 tests cover: Indian number parsing (commas, lakh/crore, parentheses), FCFF mechanics,
Gordon terminal value, EV→equity bridge, weighted central estimate & range, scenarios,
sensitivity monotonicity, CAGR/ratios, accounting validation, rules triggering (44%
growth), and API round-trips (upload→lock→interview→calculate→report) on a seeded
in-memory database.

## Live demo & GitHub Pages deployment

**Live static preview:** https://rahulguptaca.github.io/AICA-L2-B77-Ghaziabad-Capstone_Project/

Every push to `main` triggers `.github/workflows/deploy-pages.yml`, which builds the
frontend and deploys it to GitHub Pages (repo **Settings → Pages → Source: GitHub
Actions** — the workflow enables this automatically on first run).

Because GitHub Pages only serves static files (it cannot run the Python backend), the
Pages build ships in **static demo mode**:

- All screens render from `frontend/src/demo/data.json` — a snapshot of the real
  backend's responses for the seeded demo, regenerated with
  `backend/scripts/snapshot_demo.py` against a running, freshly-seeded backend.
- The **Simulation Lab stays fully interactive** through a display-only TypeScript
  mirror of the valuation engine (`frontend/src/demo/simulate.ts`), verified to
  reproduce the Python engine's outputs exactly. The authoritative engine remains
  the Python one.
- "Export as PDF" serves the bundled, engine-generated sample report.
- Uploads, AI verification, the adaptive interview and live report generation
  need the backend — the banner on the site links back to this README.

To turn the Pages site into a fully live deployment later: host the backend
(Render/Railway/Fly.io), set the repository **Actions variable** `VITE_API_URL` to its
URL, add the Pages origin to the backend CORS list, and re-run the workflow — the
build then skips static mode and talks to the real API.

## Docker (optional)

```bash
docker compose up        # PostgreSQL + backend :8000 + frontend :5173
```

## Project structure

```
backend/app/
  api/            REST routers (cases, documents, interview, engine, settings)
  models/         SQLAlchemy models (24 tables incl. full audit trail)
  rules/          central deterministic rules engine
  prompts/        one focused prompt per AI task
  services/
    document/     extraction, rendering, pipeline, reconciliation
    financial/    numbers, canonical schema, analytics, validation, store
    valuation/    engine (DCF/MM/NAV/scenarios/sensitivity), scoring, orchestrator
    interview/    question bank + adaptive planner
    ai/           provider adapter + Gemini + encrypted key service
    reporting/    Jinja2 report generator + pluggable PDF renderer
  templates/      report.html
frontend/src/
  layouts/ pages/ components/ hooks/ services/ types/ styles/
storage/          uploads, rendered_pages, reports (gitignored)
```

## Disclaimer

CompanyVal AI produces an **AI-assisted indicative valuation simulation** based on the
financial information supplied and the assumptions explicitly accepted by the user. It is
not a statutory valuation, a registered valuer's certificate, a fairness opinion or an
audit opinion. Professional judgement and applicable regulatory requirements may be
necessary for formal purposes.
