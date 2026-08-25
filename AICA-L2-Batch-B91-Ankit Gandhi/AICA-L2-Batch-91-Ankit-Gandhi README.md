# LedgerPulse

**Enterprise Accounts Receivable (AR) \& Accounts Payable (AP) Cash Flow Acceleration Platform**

LedgerPulse is a full-stack financial operations platform built for CFOs, Financial Controllers, Auditors, and Credit Control teams. It unifies AR/AP ledger management, aging analytics, automated dunning (collections reminders), and dual-currency (USD ⇄ TZS) reporting into a single desktop-ready application.

> Author: \*\*Ankit Gandhi\*\* (AICA L2, Batch 91)

\---

## Table of Contents

* [Overview](#overview)
* [Core Modules](#core-modules)
* [Tech Stack](#tech-stack)
* [Repository Contents](#repository-contents)
* [Running the App](#running-the-app)
* [Sample Dataset](#sample-dataset)
* [Roles \& Access (RBAC)](#roles--access-rbac)
* [Automated Dunning Cadence](#automated-dunning-cadence)

\---

## Overview

LedgerPulse bridges international trade and local commerce by natively supporting:

* **Dual-currency financial operations** (USD ⇄ TZS, default rate 1 USD = 2,650 TZS)
* **Automated 4-tier dunning reminders** with customizable sender identities and CC routing
* **Real-time aging schedule visualizers** (0–30, 31–60, 61–90, 90+ days overdue)
* **Trailing 12-month DSO (Days Sales Outstanding) analytics**
* **Excel / CSV data ingestion** with smart header auto-mapping
* **Granular Role-Based Access Control (RBAC)**
* **Offline-capable Progressive Web App (PWA)** with desktop packaging

## Core Modules

|Module|Description|
|-|-|
|**Full-Stack Architecture**|React 19 + TypeScript frontend, Node.js/Express backend bundled via esbuild into a standalone binary, in-memory relational data store seeded with enterprise sample data (26 invoices, 10 debtors/vendors, reminder rules, DSO history, audit logs)|
|**Dual-Currency Engine**|Global USD/TZS switcher with live exchange rate management and an interactive bidirectional currency calculator; all tables, KPIs, charts, and exports update dynamically|
|**Aging Schedules \& DSO Analytics**|5-bracket aging classification (Current, 0–30, 31–60, 61–90, 90+ days), Recharts drilldown visualizations, trailing 12-month DSO trend engine (`DSO = (Ending Receivables / Credit Sales) × Period Days`), Collection Effectiveness Index (CEI) tracking, configurable benchmark DSO|
|**Automated Dunning \& Escalation**|4-tier reminder cadence with token templating (`{{client\_name}}`, `{{invoice\_number}}`, `{{amount\_due}}`, etc.), customizable sender identity, multi-recipient CC/BCC routing|
|**Invoice \& Ledger Register**|Unified searchable AR/AP ledger, payment allocation (partial/full settlement), automatic due-date computation by credit terms, batch status updates, CSV export|
|**Data Ingestion**|Excel (.xlsx/.xls) and CSV upload with smart auto-mapping and pre-ingestion validation|
|**RBAC \& Governance**|6 role profiles (CFO, Finance Controller, Data Analyst, Auditor, Collection Specialist, Data Operator), user invitations, active/deactivated toggles, session audit logs|
|**Offline PWA \& Desktop**|Service worker caching for offline access, installable PWA, standalone desktop window, dark/light theme persistence|

## Tech Stack

* **Frontend:** React 19, TypeScript, Tailwind CSS v4, Motion, Recharts, Lucide-React
* **Backend:** Node.js + Express, bundled with esbuild into a standalone CommonJS binary
* **Persistence:** In-memory relational store seeded with enterprise sample data
* **Exports:** jsPDF \& jsPDF-AutoTable (PDF), SheetJS/XLSX (multi-sheet Excel), PapaParse (CSV)
* **AI Layer:** Google GenAI SDK (`@google/genai`) — server-side cash flow forecasting, overdue risk analysis, debtor follow-up strategy generation
* **Desktop Packaging:** Electron-style `.exe` build (see `LedgerPulse-win32-x64/`)

## Repository Contents

|File|Description|
|-|-|
|`LedgerPulse\_Final.bat`|Windows launcher script — starts the backend server, waits for it to warm up, then launches the desktop app|
|`LedgerPulse\_Desktop\_Presentation\_Model.html`|Self-contained, browser-viewable executive presentation deck / demo of the app UI (KPI dashboard, currency switcher, slide navigation)|
|`LedgerPulse\_Enterprise\_Financial\_Dataset.xlsx`|Seed dataset — invoices/bills register, debtors \& vendors, aging summary, DSO trend, dunning rules, RBAC matrix|
|`Prompt\_of\_Ledgerpulse.docx`|Original product/engineering specification used to build the platform|
|`Ankit\_Gandhi\_AICA\_L2\_91.mp4`|Project walkthrough / demo recording|

## Running the App

The included launcher (`LedgerPulse\_Final.bat`) is a Windows batch script that:

1. Kills any stuck `node.exe` processes.
2. Navigates to the project folder:
`C:\\Users\\ankit\\Desktop\\AICA-L2-Batch-91-Ankit-Gandhi\\LP`
3. Starts the backend server in the background:
`npx tsx server.ts`
4. Waits 5 seconds for the server to initialize.
5. Launches the packaged desktop client:
`LedgerPulse-win32-x64\\LedgerPulse.exe`

**To run locally:**

```bat
:: From the project root
LedgerPulse\_Final.bat
```

**Prerequisites:**

* Node.js installed (for `npx tsx`)
* Project folder present at the path referenced in the script (update the path in the `.bat` file if your project lives elsewhere)
* The desktop build (`LedgerPulse-win32-x64/LedgerPulse.exe`) already generated in the project folder

> ⚠️ The batch file has the project path hardcoded to `ankit`'s desktop. Update the `cd /d` path if running from a different machine or user account.

For a quick, no-install look at the UI and KPIs, open `LedgerPulse\_Desktop\_Presentation\_Model.html` directly in any browser.

## Sample Dataset

`LedgerPulse\_Enterprise\_Financial\_Dataset.xlsx` contains 6 sheets used to seed the app:

* **Invoices\_Master\_Register** — 26 invoices/bills (receivables \& payables) with amounts in USD and TZS, status, overdue days, and aging bracket
* **Debtors\_and\_Vendors** — 10 customer/vendor accounts with credit terms, outstanding balances, and risk status
* **Aging\_Schedules\_Summary** — rolled-up totals per aging bracket with risk weighting
* **DSO\_12\_Month\_Trend** — trailing 12-month DSO vs. benchmark (90-day target in this dataset), with variance and health status
* **Automated\_Dunning\_Rules** — the 5-stage reminder templates, trigger timing, and CC routing
* **Team\_and\_RBAC\_Matrix** — user accounts, roles, and access levels

## Roles \& Access (RBAC)

|Role|Purpose|
|-|-|
|CFO|Full executive visibility and control|
|Finance Controller|Oversight of AR/AP operations and approvals|
|Data Analyst|Reporting and analytics access|
|Auditor|Read-only audit trail and compliance access|
|Collection Specialist|Manages debtor follow-ups and task allocation|
|Data Operator|Data entry and ingestion|

## Automated Dunning Cadence

|Stage|Trigger|Recipient CC|
|-|-|-|
|Courtesy Reminder|3 days before due date|—|
|Due Date Notification|Due date (Day 0)|—|
|First Overdue Escalation|+7 days overdue|Controller|
|Second Overdue Notice|+15 days overdue|—|
|Final Demand \& Legal Notice|+30 days overdue|CFO \& Legal|

Each reminder uses dynamic tokens (`{{client\_name}}`, `{{invoice\_number}}`, `{{amount\_due}}`, `{{due\_date}}`, `{{overdue\_days}}`, `{{company\_name}}`, `{{payment\_link}}`) and supports customizable sender identity (From Name, From Email, Reply-To, Phone, Address).

\---

