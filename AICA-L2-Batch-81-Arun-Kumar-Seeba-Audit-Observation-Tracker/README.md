# 📋 Audit Observation & Query Tracker (CA Firm Portal)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0%2B-green.svg)](https://www.djangoproject.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple.svg)](https://getbootstrap.com/)
[![Auditing Standards](https://img.shields.io/badge/Standards-ICAI%20SA%20230%20%2F%20260-orange.svg)](https://www.icai.org/)

A professional web-based **Audit Observation & Query Lifecycle Tracker** purpose-built for Chartered Accountancy and Audit firms. It standardizes and manages the full end-to-end lifecycle of audit observations and Provided By Client (PBC) information requests across client engagements—from initial drafting and maker-checker internal review, through client response capture and partner exceptions, culminating in a system-generated **Audit Summary Memo in Microsoft Word (.docx) format** and formatted **Excel Observation Register (.xlsx)**.

---

## 🚀 1-Click Quick Start (Windows)

1. Clone or Download this repository as a ZIP and extract it.
2. Ensure **Python 3.10+** is installed on your machine.
3. **Double-click `setup_and_run.bat`** (or `start_server.bat` for subsequent launches).
4. The batch script automatically:
   - Detects and switches away from occupied ports (port conflict resolution).
   - Installs required dependencies.
   - Applies database migrations.
   - Populates realistic demo seed data.
   - Launches the local development server and opens the portal directly in your default browser!

---

## 💻 Manual Setup & Run (Linux / macOS / Windows CLI)

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/audit-observation-tracker.git
cd audit-observation-tracker

# 2. Create virtual environment (optional but recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations
python manage.py migrate

# 5. Populate pre-seeded demo data (Clients, Staff, Engagements, Queries)
python manage.py seed_demo_data

# 6. Start the server
python manage.py runserver 0.0.0.0:8000
```
Open **`http://127.0.0.1:8000/`** in your browser.

---

## 👥 Demo User Accounts & Roles

The system is pre-configured with role-based access control (RBAC). Use any of the following accounts:

| Role / Designation | Demo User Email | Password | Primary Capabilities |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@firm.com` | `Admin@123` | User & Staff management, Client master, System Audit Logs |
| **Audit Partner** | `partner1@firm.com` | `Partner@123` | Partner Dashboard, Step-Up Auth Exception Approvals (EX-01 to EX-07), Summary Word Memo (.docx) generation & sign-off |
| **Audit Manager** | `manager1@firm.com` | `Manager@123` | Engagement oversight, Maker-Checker draft review & query issuance, closure review, exception requesting |
| **Senior Auditor** | `senior1@firm.com` | `Senior@123` | Structured 5-element observation drafting, fieldwork tracking, follow-ups |
| **Article Assistant** | `article1@firm.com` | `Article@123` | Draft observation entry (restricted from direct client issuance) |
| **Client Coordinator** | `cfo@apexindustries.com` | `Client@123` | Client Portal: view issued queries, assign to team, submit official client responses & evidence |

---

## 🔑 Key Features & Compliance Controls

- **Maker-Checker Enforcement (BR-02):** Article Assistants cannot issue queries directly to clients; draft creators cannot self-approve issuance.
- **5-Element Structured Findings:** Rigorous observation capture adhering to ICAI SA 230 / CARO 2020:
  1. *Condition* (What was found)
  2. *Criteria* (What standard/law applies)
  3. *Cause* (Why it occurred)
  4. *Effect / Risk* (Financial & compliance impact)
  5. *Recommendation* (Actionable corrective measure)
- **Strict Terminal Gate for Memo Generation (FR-11):** Summary Word Memo (.docx) generation is strictly blocked if unresolved or non-terminal queries exist, unless overridden by an approved Partner Exception (EX-03).
- **Partner Step-Up Authentication (FR-07, FR-12):** Mandatory re-authentication password prompts for granting partner exceptions and signing off final summary memos.
- **Automated Word Memo Generator (.docx):** Dynamic memo generation featuring Firm letterhead, engagement scope, query statistics table, Annexures A–D, and formal partner signature block.
- **Formatted Excel Export (.xlsx):** One-click styled audit query register export via `openpyxl` with color-coded risk ratings and lifecycle status tags.
- **Append-Only Audit Trail (FR-14):** Comprehensive logging of all lifecycle transitions, authentication events, exception overrides, and memo exports.

---

## 📊 Presentations & Project Documentation

- **`Audit_Observation_Tracker_Walkthrough_Read me.pptx`**: Comprehensive 15-slide viva presentation deck complete with UI walkthrough screenshots, system workflow diagrams, maker-checker governance charts, and technical architecture.

---

## 🧪 Running Automated Tests

Run the full Django test suite covering state transitions, maker-checker constraints, memo gates, and audit trails:

```bash
python manage.py test
```

---

## 📄 License & Academic Deliverable
Developed as an academic and professional project deliverable for Chartered Accountancy Audit Practice automation.