# LexSecure India Pro ⚖️
### Enterprise Legal & Regulatory Intelligence Web Application for Indian Business Entities
**A Capstone Project in Applied Legal-Tech, Regulatory Intelligence & Full-Stack Engineering**

---

## 📌 Executive Summary

**LexSecure India Pro** is an enterprise-grade Legal & Regulatory Intelligence Web Application engineered for ANY Indian operating business entity (startups, MSMEs, manufacturing plants, tech corporations, and large conglomerates). 

It bridges the critical compliance gap between rapidly shifting statutory frameworks (FEMA 1999, the 4 Labour Codes, DPDP Act 2023, MSMED Act 2006, Section 43B(h), and CERT-In) and corporate execution.

---

## 🚀 Quick Launch (Web Application)

Double-click `launch_web.bat` or run from terminal:

```powershell
cd C:\Users\Sameeha\.gemini\antigravity\scratch\LexSecure_India_Pro
.\launch_web.bat
```

Or run directly with Python:
```powershell
python run_web.py
```
*(Or `python manage.py runserver 127.0.0.1:8055`)*

Then navigate to: **`http://127.0.0.1:8055/`** *(Dedicated collision-free port)*

---

## 🏛️ Built-In Indian Statutory & Regulatory Coverage

1. **Foreign Exchange Management Act (FEMA 1999 & RBI Regulations):**
   - FDI inflows/reporting (FC-GPR), overseas transfer of shares (FC-TRS), External Commercial Borrowings (ECB) limits (SOFR + 550 bps), cross-border vendor payments (Form 15CA/15CB), compounding risks under Section 15.
2. **Comprehensive Labour & Employment Laws:**
   - **The 4 Labour Codes:** Code on Wages 2019 (50% basic wage allowance ceiling harmonization, overtime, bonus), Industrial Relations Code 2020, Code on Social Security 2020, and OSH Code 2020.
   - **Ongoing Acts:** EPF & MP Act 1952 (12% contribution rules), ESI Act, Payment of Gratuity Act 1972 (5-year continuous rule), Contract Labour (Regulation & Abolition) Act, and PoSH Act 2013 (Internal Complaints Committee & Jan 31 Annual Report filing).
   - **Indian Contract Act 1872 (Section 27):** Statutory voidness of post-employment non-compete clauses in India (*Percept D'Mark v. Zaheer Khan*).
3. **Corporate, Tax & MSME Governance:**
   - **Companies Act 2013:** Annual filings (AOC-4, MGT-7), DIR-3 KYC, Board resolutions, Demat mandate, CSR mandates under Section 135.
   - **MSMED Act 2006 & Section 43B(h) Income Tax:** Mandatory payment to micro/small vendors within 15/45 days to prevent tax deduction disallowance and penal compound interest at 3x RBI bank rate.
4. **Digital Privacy & Cybersecurity:**
   - **DPDP Act 2023:** Data fiduciary vs data processor agreements, explicit consent mechanisms in 22 Schedule VIII languages, child data safeguards, penalty exposure up to ₹250 Crores.
   - **CERT-In Cybersecurity Directives:** Mandatory 6-hour incident reporting window, system log retention for 180 days within Indian jurisdiction.

---

## 🌟 Core Modules & Web Workspaces

### 1. 📊 Executive Command Center (`/dashboard/`)
- Top Operating Entity Switcher (toggle between subsidiaries like Tech Pvt Ltd, Manufacturing Ltd).
- 4 Executive KPI Metric Cards:
  - Enterprise Legal Health Score (0–100%)
  - Dealbreakers & Uncapped Liability Flags (🔴 High Risk)
  - Overdue & Approaching Statutory Deadlines
  - Labour Codes & FEMA Compliance Index
- Department Accountability Heatmap (visual completion rates for Legal, HR/Labour, Finance/Tax, InfoSec/Tech, Operations).
- Live Indian Regulatory Watchlist with severity indicators (Critical / High / Advisory).
- Upcoming Statutory Deadlines countdown table with statutory penalties.

### 2. 📑 Pillar 1: Contract / Document Review & Storage Workspace (`/contracts/`)
- **Drag-and-Drop / Ingestion:** Upload commercial agreements in PDF, DOCX, or TXT format.
- **Entity Assignment:** Map contracts to specific operating entities for strict RBAC segregation.
- **Split-Screen Interactive Review:**
  - **Left Pane:** Full contract text rendered with color-coded risk callouts (🔴 High Risk dealbreakers, 🟡 Caution deviations, 🟢 Compliant redlines).
  - **Right Pane:** Clause breakdown with citations (*Section 27 Contract Act, Section 15 MSMED Act, FEMA ECB caps, DPDP Act 2023*) and a **1-Click "Accept Redline" HTMX button** that updates the score and applies compliance immediately.
- **📂 Document Storage Repository:** Filter documents entity-wise, inspect scores, re-assign documents between entities, and reload any contract back into review.
- **📥 1-Click Download Reviewed Report:** Export a publication-grade HTML audit report with colored highlights and statutory compliance schedule.

### 3. 📡 Pillar 2: Indian Statutory Gazette & Regulatory Tracker (`/regulatory/`)
- Ingests circulars from MCA, RBI (FEMA), Labour Ministry, SEBI, DPDPB, CERT-In, and GSTN.
- **⚡ Generate AI Impact Assessment:** Modal running Gemini / Statutory Heuristic engine to extract executive summaries, affected departments, and statutory deadlines.
- **Approve & Dispatch:** Automatically dispatches compliance tasks to department queues with a full cryptographic audit trail.

### 4. 📋 Pillar 3: Department Tasks & Evidence Hub (`/tasks/`)
- Tasks organized by department and status.
- **Interactive 1-Click Status Cycle:** `Pending` ➔ `In Progress` ➔ `Completed` via HTMX.
- **Upload Evidence Modal:** Attach proof dockets (PDF, DOCX, ZIP, screenshots) and verification notes.

### 5. 📅 Pillar 4: Statutory Compliance Calendar (`/calendar/`)
- Real-time countdowns for MCA Form AOC-4, PoSH Annual Report (Jan 31), FEMA FLA Return, PF/ESI Monthly ECR, GSTR-3B, CERT-In Log Review.
- Statutory Penalty Calculator detailing fines, compounding exposures, and director disqualification risks.

### 6. 🛡️ Pillar 5: Cryptographic Tamper-Evident Audit Ledger (`/audit/`)
- Chained SHA-256 ledger linking `prev_hash` to `current_hash` on every event.
- Live mathematical verification showing "✅ SHA-256 Audit Chain Verified: 100% Mathematically Intact".
- **📥 Generate Court-Admissible Defense Dossier:** 1-Click export to formal PDF / report certified under Section 65B of the Indian Evidence Act.

### 7. ⚙️ Operating Entity & User Corporate Governance (`/governance/`)
- **Operating Entities Management:** Add, edit, and delete operating entities. Automatically provisions the 5 compliance departments (`LEGAL`, `HR_LABOUR`, `FINANCE_TAX`, `INFOSEC_TECH`, `OPERATIONS`).
- **Corporate Users & RBAC:** Add, edit, and delete user profiles, assign roles (`GENERAL_COUNSEL`, `COMPLIANCE_OFFICER`, `DEPT_LEAD`, `AUDITOR`), and set security PINs (default `1234`).
- **Granular RBAC Matrix:** Full matrix table detailing permissions (Create, Read, Update, Delete, Legal Sign-off) across all 5 protected resources.

### 8. ☀️ / 🌙 Professional Dark & Light Mode Toggle
- Instant theme toggle in the top navigation bar supporting the Deep Slate/Navy palette and the high-contrast Enterprise Light theme, persisted in local storage.

---

## 📂 Project Architecture

```text
LexSecure_India_Pro/
├── compliance/                   # Django Compliance App
│   ├── management/commands/      # Database seeding scripts
│   ├── migrations/               # Database migration files
│   ├── models.py                 # 15 Core Enterprise Legal & Regulatory Models
│   ├── urls.py                   # Compliance routing
│   └── views.py                  # Web views & HTMX endpoints
├── connectors/                   # Statutory Connector Framework (MCA, RBI, Gazette)
├── data/                         # Sample commercial contracts & dockets
├── database/                     # DB engine & SQLite schema utilities
├── lexsecure_core/               # Django root project configuration (settings, urls, wsgi)
├── models/                       # Entity definitions
├── services/                     # Business logic services
│   ├── audit_service.py          # SHA-256 verification & PDF Defense Dossier generator
│   ├── document_parser.py        # Multi-engine PDF/DOCX/TXT extraction
│   └── legal_ai_service.py       # Dual engine: Gemini Flash + Statutory Fallback
├── templates/                    # Web frontend templates
│   ├── base.html                 # Master layout (Tailwind, Alpine.js, HTMX, Theme Toggle)
│   └── compliance/               # Workspaces (Dashboard, Contracts, Regulatory, Tasks, etc.)
├── ui/                           # Optional Desktop PyQt6 client views & styles
├── launch_web.bat                # 1-Click Windows Web Launcher (Port 8055)
├── run_web.py                    # Python Web Server & Auto-browser opener
├── manage.py                     # Django CLI
├── requirements.txt              # Production Python dependencies
└── README.md                     # Comprehensive documentation
```

---

## 🛠️ Technology Stack
- **Backend:** Python 3.11+, Django 5.x / 6.x
- **Database:** SQLite (production-ready migrations for PostgreSQL)
- **Frontend:** Tailwind CSS (via CDN), Alpine.js 3.x, HTMX 1.9+
- **Document Processing:** PyMuPDF, pypdf, python-docx
- **AI Engine:** Google Gemini Flash with extensive Indian Statutory Heuristic Fallback Engine
- **Cryptography:** Python standard `hashlib` SHA-256 chained event ledger
