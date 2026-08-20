# FinAudit AI — Ind AS Statutory Financial Statement Auditor & Consistency Verifier
### 100% Offline, Privacy-First On-Device Edition

**FinAudit AI** is a specialized statutory financial statement audit, note-by-note proofreading, and mathematical consistency verification application designed for **Statutory Auditors, Quality Review Boards (QRB), and Chartered Accountants**.

---

## 🚀 Key Features

- **100% Offline Audit Engine**: Complete deterministic evaluation of financial statements against Ind AS (Ind AS 1 through 116) and Schedule III MCA 2021 statutory rules without requiring internet or API keys.
- **Privacy Guarantee**: All client financial statements, tables, and notes are processed directly on your machine. Zero cloud transmission.
- **Mathematical Casting & Consistency Check**: Automatic footing and casting checks (`Opening + Additions - Deductions = Closing`), `Total Assets == Total Equity & Liabilities`, and Primary statement vs Note sub-schedule reconciliation.
- **Note-by-Note Proofreading**: Scrutinizes phrasing, MSME disclosures (MSMED Act s.22), PPE rollforwards (Ind AS 16), Employee Benefits (Ind AS 19), Related Party transactions (Ind AS 24), Leases (Ind AS 116), and 11 Statutory Ratios (>25% variance checks).
- **Offline CA Technical Assistant**: Instant on-device generation of Audit Query Memos, Management Representation Letter (MRL) clauses (SA 580), Qualified Audit Opinions (SA 705), and CARO 2020 impact reports.
- **Interactive Note Reconciler**: Step-by-step arithmetic reconciliation tool with automatic CA adjusting journal entries.
- **Local Storage Vault**: Locally stores audit dossiers and history on your device with zero cloud databases.
- **Multi-Format Export**: One-click export to Print-ready HTML Dossiers, Markdown, and CSV workpapers.

---

## 💻 Quick Start & Running Offline

### Option 1: One-Click Windows Launcher (Recommended)
Double-click:
- **`Start-FinAudit-Offline.bat`** — Launches the offline application immediately in your web browser.
- **`Start-FinAudit-Desktop.bat`** — Launches the native Electron Windows desktop app.

### Option 2: Command Line
1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Run Offline Application:**
   ```bash
   npm run offline
   ```
   *(Opens http://localhost:3000 in your browser)*

3. **Run as Native Desktop App:**
   ```bash
   npm run desktop
   ```

4. **Build Production Bundle:**
   ```bash
   npm run build
   ```

---

## 🏛️ Regulatory Standards Supported
- **Ind AS (Indian Accounting Standards)**: Ind AS 1, 2, 7, 8, 12, 16, 19, 23, 24, 33, 36, 37, 38, 107, 108, 109, 115, 116.
- **Companies Act, 2013**: Schedule III (Division I, Division II, Division III) with MCA 2021 Amendments (GSR 207(E)).
- **Standards on Auditing**: SA 700, SA 705 (Modifications to Opinion), SA 706 (Emphasis of Matter), SA 580 (Written Representations).
- **CARO 2020**: Companies (Auditor's Report) Order, 2020 clauses (i) to (xxi).
