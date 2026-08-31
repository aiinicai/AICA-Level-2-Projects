# Ind AS 116 — Lease Accounting Suite

A modular, GUI-based lease accounting model for Chartered Accountancy
practices, covering **Day-0 measurement** of the Right-of-Use (ROU)
asset and Lease Liability under **Ind AS 116**, plus month-wise
liability amortisation and ROU depreciation schedules.

## Requirements
- Python 3.9 or later
- Tkinter (ships with standard Python installers on Windows/macOS; on
  some Linux distributions install via `sudo apt install python3-tk`)

All other third-party packages (`pandas`, `openpyxl`,
`python-dateutil`) are detected and installed **automatically the
first time you run the app** — you will see a live installation log
window while this happens. This only happens once per machine.

## Running the application
```
python main.py
```

## What it does
1. **Lease Inputs tab** — enter monthly rental, lease term, escalation,
   payment timing (advance/arrears), the Interest Rate Implicit in the
   Lease (or Incremental Borrowing Rate if not determinable), initial
   direct costs, incentives, restoration costs, etc.
2. **Run Model** computes:
   - Lease Liability at Day 0 = PV of unpaid lease payments
   - ROU Asset at Day 0 = Lease Liability + prepaid rentals + initial
     direct costs − incentives + PV of restoration costs
   - Month-wise lease liability amortisation (effective interest method)
   - Month-wise ROU depreciation (straight-line over the lease term)
3. **Export to Excel** — saves all schedules to a multi-sheet workbook
   suitable for client working papers.
4. **Save/Load Template** — save a lease's input set as a `.json` file
   so recurring engagements (e.g. annual re-runs, similar leases across
   branches) can be reloaded instantly instead of re-keyed.

## Project structure (for maintenance)
```
ind_as_116_suite/
├── main.py                  Entry point (run this)
├── README.md
└── ind_as_116/
    ├── __init__.py           Package metadata
    ├── bootstrap.py          First-run dependency detection & install
    ├── models.py             LeaseInputs / LeaseResult data structures
    ├── engine.py             All Ind AS 116 calculations (no I/O)
    ├── excel_export.py       Excel workbook export
    └── gui.py                Tkinter GUI (install log + main window)
```

The calculation engine (`engine.py`) is fully decoupled from the GUI —
it can be imported and run headlessly (e.g. from a script that batch-
processes many client leases from a CSV, or from a future web/CLI
front-end) without any Tkinter dependency:

```python
from datetime import date
from ind_as_116.models import LeaseInputs
from ind_as_116.engine import LeaseEngine
from ind_as_116.excel_export import export_to_excel

inputs = LeaseInputs(
    lease_commencement_date=date(2025, 4, 1),
    lease_term_months=60,
    monthly_rental=100000,
    incremental_borrowing_rate_annual=0.10,
)
result = LeaseEngine(inputs).run()
print(result.summary)
export_to_excel(result, "lease_model.xlsx")
```

## Key accounting reference
Ind AS 116 (Leases) — lessee recognition and initial measurement:
the Right-of-Use asset is measured at cost, and the lease liability
at the present value of lease payments not paid at the commencement
date, discounted using the interest rate implicit in the lease if
readily determinable, or otherwise the lessee's incremental
borrowing rate.

## Notes on assumptions built into this model
- Depreciation is charged straight-line over the full lease term. If
  the underlying asset's useful life is shorter and ownership does not
  transfer, adjust `build_depreciation_schedule()` accordingly.
- Variable lease payments (not based on an index/rate), sublease
  accounting, and lease modification/reassessment are **not** yet
  modelled — flagged here so future maintainers know the current scope
  boundary.
- All amounts are assumed to be in a single currency (no FX translation
  built in).

## Extending this suite
Because the engine, GUI, and export layers are separate modules,
common extensions are isolated to one file each:
- New calculation logic (e.g. lease modifications) → `engine.py`
- New input fields → add to `LeaseInputs` in `models.py` and to the
  `FIELDS` list in `gui.py`
- New export formats (e.g. PDF working paper) → new module alongside
  `excel_export.py`
# INNFLOW — Enterprise Hotel Operations & Management Ecosystem
**AICA Level-2 Capstone Project**  
**Author:** CA Ankit Tandon  
**Target Industry:** Hospitality, Hotel Property Management & Internal Financial Controls

---

## 📌 Project Overview

**INNFLOW** is a full-stack, enterprise-grade Hotel Operations and Property Management platform designed to solve operational bottlenecks, prevent financial leakages, enforce multi-tier approval hierarchies, and provide real-time statutory audit transparency across luxury hotel properties.

The system features a **Dual-Access Ecosystem**:
1. **📱 Mobile Application (React Native / Expo / Android APK & AAB)**: Used by floor staff (Housekeeping, Engineering technicians, Duty managers, Security) for real-time room readiness inspections, work order execution, lost & found safekeeping, and instant voice/chat task dispatch.
2. **💻 Web-Based Administration Portal (React / TypeScript / Tailwind)**: Used by General Managers, Financial Controllers, and Department Heads on desktop browsers for capital expenditure approvals, CMMS plant maintenance scheduling, compliance tracking, and revenue reconciliation.
3. **🗄️ Centralized Server & Relational Database (Express / tRPC / Drizzle ORM / MySQL)**: Single source of truth with immutable append-only audit event logging.
4. **☁️ Secure Cloudflare Tunnel Integration (`cloudflared`)**: Encrypted zero-trust connection bridging on-premise PMS/POS feeds and mobile clients with zero open public ports.

---

## 🚀 Key Functional Modules

### 1. Housekeeping & Room Matrix
- Real-time room status board across floors (*Inspected, Clean, Dirty, Out of Order, Do Not Disturb*).
- **Mandatory 5-Star Digital Inspection Checklist Gate**: Programmatic block preventing room release to the PMS until all safety, hygiene, and amenity verification points are checked.

### 2. Purchase Requisitions & Financial Approvals Hierarchy
- Threshold-based authorization workflow for CAPEX and OPEX expenses (e.g. Linen restocking, Spa vouchers, F&B replenishment).
- Complete variance tracking between Point-of-Sale (POS) night audit settlements and PMS front-desk folios.

### 3. Engineering CMMS & Preventative Maintenance (PPM)
- Registry of heavy hotel plant equipment (HVAC Chillers, Steam Boilers, Elevator Banks, Cold Storage).
- Automated preventative maintenance service scheduling with SLA response target tracking.

### 4. Lost & Found Safekeeping Registry
- Digital chain-of-custody tracking with designated locker/vault IDs, item categorization, and verified guest claim handover workflow.

### 5. Hotel ERP Operations & 3-Way Procurement Cockpit
- Integrated inventory management distinguishing usable stock from physical, reserved, and damaged stock.
- 3-Way matching control (*Purchase Order ➔ Goods Receipt ➔ Invoice*) with automated payment holds on discrepancies.
- Perishable goods tracking with First-Expired, First-Out (FEFO) watchlists and booking-driven demand shortage signals.

### 6. Statutory Compliance & License Register
- Tracking statutory operating permits (Fire Safety Certificates, FSSAI/Food Handling Licenses, Lift Inspection Registers, Public Liability Insurance) with automated renewal lead-time alerts.

### 7. Team Shift Roster & Instant Dispatcher
- Real-time staff accountability map tracking active duty statuses (*On Floor, On Task, On Break, Off Duty*) with direct task dispatching.

### 8. Immutable Audit Trail
- Non-repudiable audit logging recording every document creation, approval, status transition, and guest compensation event.

---

## 📂 Codebase Organization

The software is structured into clean architectural layers:
- **🌐 Frontend (`app/`, `components/`, `lib/`, `constants/`)**: Expo Router mobile screens, widescreen desktop web management portal, and offline-first state stores.
- **🖥️ Backend (`server/`)**: Express API server, type-safe tRPC procedure routers, authentication, and CORS security.
- **🗄️ Database (`drizzle/`, `server/db.ts`)**: Normalized relational schema, foreign key relations, and dual MySQL/in-memory store.
- **🧪 Tests (`tests/`)**: 20 automated Vitest unit and integration test suites.
- **⚙️ DevOps & Scripts (`scripts/`, `eas.json`, `app.config.ts`)**: Cloudflare Tunnel runner, EAS production Android builds (`.aab` and `.apk`).
- **📚 Documentation (`docs/`)**: Detailed architecture, tunnel guides, and Google Play Store deployment guides.

*For full details, see [`docs/PROJECT_STRUCTURE.md`](./docs/PROJECT_STRUCTURE.md).*

---

## 🛠️ Technology Stack & Architecture

| Layer | Technologies Used |
| :--- | :--- |
| **Mobile Frontend** | React Native (v0.76+), Expo (v54), Expo Router, TypeScript, NativeWind |
| **Desktop Web Portal** | React 19, HTML5, CSS Grid, tRPC React Query Client |
| **Backend & API** | Node.js, Express, tRPC (Type-safe RPC v11), SuperJSON, Zod Validation |
| **Database & ORM** | MySQL, Drizzle ORM (Relational schema with foreign keys and migrations) |
| **Tunneling & Security**| Cloudflare Tunnel (`cloudflared`), CORS Origin Sanitization, Strict CSP |
| **Testing & CI** | Vitest (Unit & Integration tests), TypeScript Compiler (`tsc --noEmit`) |
| **Build & Distribution**| EAS Build (Android `.aab` for Google Play Store & standalone `.apk`) |

---

## 💻 Local Quickstart & Running Instructions

### 1. Start the Backend API & Database Server (Port 11000)
```bash
pnpm dev:server
```

### 2. Start the Web Portal & Mobile Bundler (Port 8081)
```bash
pnpm dev:metro
```
*(Or launch both simultaneously with `pnpm dev` or double-click `start-pc-server-and-web.bat`)*

### 3. Access URLs
- **Web Management Portal**: `http://localhost:8081/admin`
- **Mobile Web View**: `http://localhost:8081`
- **Backend API Health**: `http://localhost:11000/api/health`

### 4. Start Cloudflare Tunnel
```bash
pnpm tunnel
```

---

## 🧪 Verification & Automated Tests
# TAX COMMAND CENTRE
## AI-Powered Corporate Direct Tax Compliance, Assessment & Litigation Management
<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/31b21528-31d6-4768-be02-f0ef92331fd9

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`
# 📊 Stock Statement + ICAI UDIN Automation Tool

**A Professional Automation Solution for Chartered Accountants**

## 🎯 Project Overview

This is an advanced **automation tool** designed specifically for **Chartered Accountants (CAs)** to streamline the process of:

- ✅ Generating **Stock Statements** 
- ✅ Creating **Drawing Power Certificates**
- ✅ Automating **ICAI UDIN** (Unique Document Identification Number) certificate registration
- ✅ Managing multiple **bank clients** and financial data
- ✅ Auto-filling **ICAI forms** with UDIN integration

### 🌟 Key Features

| Feature | Description |
|---------|-------------|
| **Browser Automation** | Uses Selenium + Microsoft Edge for ICAI website automation |
| **Data Management** | JSON-based storage for clients, debtors, creditors, and stock information |
| **UDIN Integration** | Automated UDIN certificate generation and submission to ICAI portal |
| **Multi-Client Support** | Manage multiple clients with different banks and credit limits |
| **CA Profile Storage** | Secure storage of CA credentials (ICAI username, FRN, membership details) |
| **Form Recording** | Records user steps for debugging and process optimization |
| **HTML Interface** | User-friendly web-based interface for data entry |
| **Batch Processing** | Process multiple certificates in one session |

---

## 🛠️ Tech Stack

- **Backend**: Python 3 with Selenium WebDriver
- **Frontend**: HTML5 + Angular (ng-select for dropdowns)
- **Data Storage**: JSON files (structured data format)
- **Browser Automation**: Microsoft Edge WebDriver
- **Platform**: Windows (.bat files for execution)

---

## 📋 Prerequisites

### System Requirements
- Windows 10 or higher
- Python 3.7+
- Microsoft Edge browser
- Internet connection (for ICAI portal access)

### Software Dependencies
- **Python Libraries**: 
  - `selenium` (for browser automation)
  - Additional dependencies auto-installed on first run

### ICAI Credentials Required
- ICAI Member Username (Email format: `MEMBERSHIP_NO@icai.org`)
- ICAI Portal Password
- Firm Registration Number (FRN)
- CA Membership Number

---

## 📦 Project Structure

```
Stock Statement UDIN Automation/
│
├── RUN_STOCK_STATEMENT_UDIN_V21_FIXED.py      # Main automation script
├── Stock_Statement_Drawing_Power_UDIN_Integrated_v20.html  # UI Interface
├── RUN_STOCK_STATEMENT_UDIN_V21.bat            # Batch file to run tool
├── RECORD_ICAI_STEPS.bat                       # Batch file to record steps
│
├── StockStatementData/                         # Data folder (created automatically)
│   ├── clients.json                            # Client master data
│   ├── debtors.json                            # Sundry Debtors list
│   ├── creditors.json                          # Sundry Creditors list
│   ├── stock.json                              # Stock information
│   ├── profiles.json                           # CA profile & credentials
│   ├── stock-statement_*.json                  # Form state backups
│   └── recordings/                             # Step recordings
│
├── README.md                                   # This file
├── DOCUMENTATION.md                            # Detailed process guide
└── DATA_STRUCTURE.md                           # Data format reference

```

---

## 🚀 Installation & Setup

### Step 1: Download Python
1. Visit https://www.python.org/
2. Download **Python 3.9 or higher**
3. During installation, **TICK the checkbox** "Add Python to PATH"
4. Click Install

### Step 2: Extract Project Files
- Extract all project files to a folder (e.g., `C:\StockStatementTool\`)
- Keep all files together in the same folder

### Step 3: Prepare Your Data
- Edit `StockStatementData/profiles.json` with your CA credentials
- Add your clients in `StockStatementData/clients.json`
- Update debtors and creditors data as needed

### Step 4: First Run
- Double-click `RUN_STOCK_STATEMENT_UDIN_V21.bat`
- The tool will:
  1. Check for Python installation
  2. Install Selenium (if not present)
  3. Open the HTML interface
  4. Launch Microsoft Edge for ICAI automation

---

## 💻 Usage Guide

### Running the Tool

```bash
# Run the main application
RUN_STOCK_STATEMENT_UDIN_V21.bat

# Record ICAI steps for debugging
RECORD_ICAI_STEPS.bat
```

### Workflow

1. **Launch Tool**: Double-click `.bat` file
2. **Select CA Profile**: Choose from saved profiles (picks your CA credentials)
3. **Enter Client Details**: 
   - Select client name
   - Enter statement date
   - Choose certificate type (Stock Statement, Drawing Power, etc.)
4. **Add Figures**:
   - Sundry Debtors amount
   - Stock value
   - Sundry Creditors amount
5. **Auto-Fill ICAI Form**: Tool automatically fills the ICAI portal
6. **Enter CAPTCHA**: Manually enter CAPTCHA (shown in HTML interface, not Edge window)
7. **Generate UDIN**: Submit and receive UDIN from ICAI
8. **Save Certificate**: Download and store UDIN certificate

---

## 📊 Data Files Explained

### `clients.json`
Stores master client data with bank and credit details.

**Fields**:
- `name`: Company/Borrower name
- `pan`: PAN number (10 characters)
- `address`: Complete address
- `gst`: GSTIN (15 characters)
- `bank`: Bank name (e.g., "State Bank of India")
- `branch`: Branch name
- `loanAccountNo`: Loan/CC Account number
- `sanctionLimit`: Credit limit in rupees

### `debtors.json` / `creditors.json` / `stock.json`
PDF backup of financial statements (base64 encoded).

### `profiles.json`
CA credentials and firm information.

**Fields**:
- `id`: Unique profile ID
- `label`: Display name
- `icaiUsername`: ICAI login (format: `MEMBERSHIP_NO@icai.org`)
- `icaiPassword`: ICAI portal password
- `firmName`: Registered firm name
- `caName`: CA's full name
- `membershipNo`: ICAI membership number
- `frn`: Firm Registration Number
- `certificatePlace`: Signing location (usually city name)

---

## 🔧 Troubleshooting

### Issue: Python not found
**Solution**: Reinstall Python and tick "Add Python to PATH"

### Issue: Selenium not installing
**Solution**: Open Command Prompt as Administrator and run:
```bash
python -m pip install --upgrade selenium
```

### Issue: CAPTCHA auto-fill fails
**Check**: Look at `udin_autofill_debug.png` in the project folder for debugging screenshot

### Issue: ICAI login fails
**Check**: 
- Verify username format: `MEMBERSHIP_NO@icai.org`
- Confirm password is correct
- Check ICAI website is accessible: https://udin.icai.org/ICAI/login

### Issue: Form doesn't auto-fill
**Solution**: Run `RECORD_ICAI_STEPS.bat` to record new steps for your workflow

---

## 📁 File Locations & Portability

**Important**: Your data is saved in the `StockStatementData` folder next to this tool.

To move the tool to another computer:
1. Copy the entire project folder
2. The `StockStatementData` folder moves with it
3. All your client data, profiles, and settings come along

---

## 🔐 Security Notes

⚠️ **Be Careful**:
- `profiles.json` contains your ICAI credentials in **plain text**
- Keep this file **SECURE** and **BACKED UP**
- Never share this file with unauthorized persons
- Consider encrypting sensitive data in production use

---

## 📌 ICAI Compliance

✅ This tool is designed to assist CAs in compliance with:
- ICAI guidelines for UDIN (Unique Document Identification Number)
- Stock Statement audit requirements
- Drawing Power Certificate generation
- Banking regulations for credit audits

⚠️ **Disclaimer**: This tool is a **helper application**. Final certificate submission and UDIN generation happens through the **official ICAI portal**. CAs remain responsible for all submitted documents.

---

## 🎓 For Beginners (Step-by-Step)

If you're new to this tool, follow these steps:

1. Read `DOCUMENTATION.md` (detailed process guide)
2. Check `DATA_STRUCTURE.md` (understand your data format)
3. Run the tool with test client first
4. Refer to troubleshooting section if any issue

---

## 🤝 Support & Maintenance

For technical issues:
- Check the `udin_autofill_debug.png` screenshot
- Review step recordings in `StockStatementData/recordings/`
- Run `RECORD_ICAI_STEPS.bat` to capture your specific workflow

To execute the automated test suites verifying room gates, search indexing, access control, and database operations:
```bash
pnpm test
```
```bash
pnpm check
```

---

## 👤 Author & Developer Attribution
- **Developer:** CA Ankit Tandon
- **Course:** ICAI AICA Level-2 Certification
- **Rights:** Developed and Built by CA Ankit Tandon · All Rights Reserved
# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt --break-system-packages  # or without the flag in a venv
python run.py

# Frontend (separate terminal, for development only)
cd frontend
npm install
npm run dev
```
---

## 📝 Version Info

- **Tool Version**: V21 (Fixed)
- **Last Updated**: August 2026
- **Python Requirement**: 3.7+
- **Selenium Version**: Latest (auto-updated)

---

## ✨ Features Roadmap

Future enhancements:
- [ ] Batch UDIN generation for multiple clients
- [ ] Excel import/export for client data
- [ ] PDF certificate download automation
- [ ] Email notification system
- [ ] Data encryption for credentials
- [ ] Web-based interface (non-browser dependent)

---

## 📞 Contact & Credits

**Developer**: Atul Talaviya (CA, ICAI Member #159692)  
**Firm**: Shapy & Associates  
**ICAI FRN**: 124286W  
**Tool Purpose**: AICA Level 2 Capstone Project  

---

**Last Modified**: August 26, 2026  
**Status**: ✅ Production Ready
