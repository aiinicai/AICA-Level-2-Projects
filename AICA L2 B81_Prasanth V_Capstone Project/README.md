# Asset Tagging & Label Management System (Enterprise v1.0)

A production-ready, multi-company **Asset Tagging & Label Generation Management System** built for fixed asset and inventory tagging consulting assignments.

---

## 🌟 Key Capabilities

1. **Faithful Reference Asset Tag Generation**:
   - Accurately replicates the corporate reference layout (Company Name & Logo header, Key-Value grid for SAP No / Description / Location).
   - **Barcode Mode**: Code 128 barcode pinned to bottom quadrant with human-readable Asset ID.
   - **QR Code Mode**: High-density QR code on right quadrant with automatic key-value reflow.
   - **Strict Scanner Compliance**: Only the unique Asset ID is encoded in the barcode/QR symbol.

2. **Multi-Company Management**:
   - Company Profiles with custom logos (PNG/JPG/SVG).
   - Configurable Asset ID prefixes (e.g. `FA`, `BIO`, `INV`) and numbering patterns (`{PREFIX}-{NUM:6}`, `{PREFIX}/{YEAR}/{NUM:6}`).
   - Concurrency-safe atomic sequence generation engine.

3. **Strict Duplicate Prevention & Audit Overrides**:
   - Real-time duplicate check across existing assets and within upload batches.
   - Blocks duplicate creation unless a mandatory justification comment is provided.
   - Full audit trail logging user, timestamp, IP address, and override reasoning.

4. **Bulk Excel Processing**:
   - One-click downloadable Excel template (`.xlsx`) with sample rows and guidelines.
   - Pre-generation validation table (Valid, Duplicate in DB, Duplicate in Batch, Missing required fields).
   - Inline row-by-row duplicate override and batch tag generator with live progress indicator.
   - Bulk ZIP export containing high-resolution PNGs named strictly by Asset ID (e.g. `FA-000001.png`).

5. **A4/A3 Sheet Printing & Thermal Label Printers**:
   - **Intelligent Sheet Optimizer**: Computes matrix (columns × rows) for A4, A3, Letter paper with custom margins and gaps.
   - **Hardware Spooler Bridge**: Integrates directly with Windows print spooler and thermal label printers (Zebra, Brother, DYMO, TSC).

6. **Enterprise Security & Disaster Recovery**:
   - Role-Based Access Control (**Administrator** vs **Standard User**).
   - Passwords hashed securely using Bcrypt.
   - One-click SQLite WAL database snapshot download and restore.

---

## 🚀 Quick Start (Single-Click Windows Launcher)

### Option 1: Double-Click Batch Launcher
Simply double click `run_app.bat` or run:
```cmd
run_app.bat
```
> **What it does**: Starts the backend server on `http://127.0.0.1:8000`, initializes SQLite WAL database with reference demo data, serves the built React UI, and opens your default browser (Chrome/Edge) automatically!

### Option 2: PowerShell Runner
```powershell
.\start_app.ps1
```

---

## 🔐 Demo Credentials

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `prasanth@gmail.com` | `123456789` | Full administrative, company, user & backup access |
| **Standard User** | `mahesh@gmail.com` | `987654321` | Tag generation, bulk upload & printing access |

*(Quick-fill demo buttons are provided on the login screen for instant access).*

---

## 🛠 Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, `bwip-js`, `jspdf`, `xlsx`.
- **Backend**: Python FastAPI, SQLAlchemy, SQLite (WAL mode with foreign keys enabled), Pydantic v2.
- **Engines**: ReportLab (High-Precision PDF Vector Rendering), Pillow & python-barcode (High-DPI Rasterizer), openpyxl (Bulk Excel Processor), `win32print` (Windows Hardware Print Bridge).

---

## 🧪 Acceptance Test Suite

To verify all 10 end-to-end acceptance scenarios programmatically:
```cmd
python tests\test_system.py
```
All test scenarios execute with `100% PASS` rate.
