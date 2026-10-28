# Live Bank Balance Reports & Automation Dashboard

An automated bank balance and transaction extraction suite with a local web dashboard, real-time drill-down analytics, centralized account management, and multi-entity tracking across **HDFC Bank** and **RBL Bank**.

---

## 📌 Architecture & Components

```
Live Bank Balance Reports/
├── Start_Bank_Dashboard_Mac.py  # macOS launcher (auto-frees port 10001 & opens dashboard)
├── Start_Bank_Dashboard.bat     # Windows launcher
├── config.py                    # Cross-platform paths, Chrome detection & secure prompts
├── bank_dashboard.py            # Local Flask web dashboard server (Port 10001)
├── generate_bank_summary.py     # Excel parser & HTML summary widget engine
├── bank_accounts.json           # Centralized bank accounts config (Codes, IDs, Entity Names)
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
├── bank_summary_latest.html     # Standalone visual HTML dashboard report
├── bank_summary_snippet.html    # Embeddable summary widget snippet
│
├── HDFC/                        # HDFC Automation & Assets
│   ├── HDFC balances.py         # Playwright automation for HDFC account balances
│   ├── HDFC Transactions.py     # Playwright automation for HDFC transaction statements
│   ├── HDFC balances.xlsx       # Output Excel report: HDFC balances
│   ├── HDFC transactions.xlsx   # Output Excel report: HDFC transactions
│   └── hdfc_logo.png            # Custom HDFC Bank logo image
│
└── RBL/                         # RBL Automation & Assets
    ├── RBL balances.py          # Playwright automation for RBL account balances
    ├── RBL Transactions.py      # Playwright automation for RBL transaction statements
    ├── RBL Balances.xlsx        # Output Excel report: RBL balances
    ├── RBL Transactions.xlsx    # Output Excel report: RBL transactions
    └── rbl_logo.png             # Custom RBL Bank logo image
```

---

## 🚀 Quick Setup & Portability

To run this project on any new machine (macOS or Windows):

### 1. Prerequisites
- **Python 3.10+**
- **Google Chrome** (or Chromium)

### 2. Environment Setup
Create and activate an isolated virtual environment:

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

---

## 🖥️ Running the Dashboard

### On macOS:
```bash
python3 Start_Bank_Dashboard_Mac.py
```
- Automatically kills any stale processes lingering on port `10001`.
- Launches the Flask web application in the background.
- Opens Chrome in native app mode (`--app=http://localhost:10001`) with an isolated profile (`.dashboard_profile`).
- When clicking **"🛑 Exit Dashboard"**, it shuts down the server, frees port `10001`, and automatically closes Chrome.

### On Windows:
Double-click:
```cmd
Start_Bank_Dashboard.bat
```

---

## ⚙️ Centralized Bank Accounts Manager

You can manage all bank accounts from a **single window** directly in the dashboard UI:
1. Click **"⚙️ Manage Accounts"** in the top navigation bar.
2. Switch between **HDFC Accounts** and **RBL Accounts** tabs.
3. Edit **Nickname**, **Entity / Company Name**, **Customer ID / User ID**, or toggle **Active** status.
4. Click **"+ Add Account"** to add a new account or click **"&times;"** to delete.
5. Click **"💾 Save Changes"** — the dashboard immediately updates your selection chips and syncs

---

## 🎨 Custom Bank Logos

The dashboard and summary reports automatically detect custom bank logos:
- **HDFC**: Place `hdfc_logo.png`, `hdfc_logo.svg`, or `hdfc_logo.jpg` inside `HDFC/` (or the base folder).
- **RBL**: Place `rbl_logo.png`, `rbl_logo.svg`, or `rbl_logo.jpg` inside `RBL/` (or the base folder).

**Fallback:** If no custom image file is provided, authentic lightweight vector SVGs are rendered automatically.

---

## 📊 Features

1. **One-Click Automation**: Run balance fetching or transaction downloads for selected accounts or all accounts at once.
2. **Real-time Terminal Output**: Live streaming of automation progress and logs directly within the web dashboard.
3. **Interactive Financial Summary**:
   - Total balances per bank and aggregated totals.
   - Drill down by bank, entity, or search query.
   - Account freshness indicator (alerts when data is older than 24h).
   - Direct download and opening of generated `.xlsx` reports from `HDFC/` and `RBL/`.
4. **Clean Session Management**:
   - Automatic port `10001` cleanup at startup and exit.
   - Heartbeat monitoring to cleanly shut down server after browser is closed.
