# OfficeFlow — Enterprise Practice & Compliance Management Platform

<div align="center">

![OfficeFlow Banner](https://img.shields.io/badge/Platform-Android%20%7C%20Windows%20%7C%20Web%20PWA-1E40AF?style=for-the-badge)
![Security RBAC](https://img.shields.io/badge/Security-Firebase%20Auth%20%2B%20Firestore%20RBAC-059669?style=for-the-badge)
![Tech Stack](https://img.shields.io/badge/Stack-Kotlin%20Compose%20%7C%20C%23%20.NET%20%7C%20Cloud%20Firestore-D97706?style=for-the-badge)
![Build Status](https://img.shields.io/badge/Verification-100%25%20Rules%20%26%20Unit%20Tests%20Passed-7C3AED?style=for-the-badge)

</div>

---

## 📌 Executive Summary

**OfficeFlow** is an enterprise-grade practice workflow and statutory compliance management platform engineered specifically for Chartered Accountants (CAs), tax advisory firms, corporate legal teams, and enterprise financial departments.

It unifies daily office task assignment, real-time client project milestone tracking, team workload balancing, and multi-authority Indian statutory compliance tracking (GST, Income Tax, ROC/MCA, PF, ESI, Professional Tax, RBI/FEMA) across a **Native Android App**, a **Windows Desktop Application**, and a **Cloud Progressive Web App (PWA)** sharing a synchronized real-time database.

---

## 🚀 Key Value Propositions & Modules

```
                                  ┌────────────────────────────────┐
                                  │   OfficeFlow Unified Engine    │
                                  └───────────────┬────────────────┘
                  ┌───────────────────────────────┼───────────────────────────────┐
                  ▼                               ▼                               ▼
       ┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
       │   Native Android    │         │   Windows Desktop   │         │   Cross-Platform    │
       │   (Jetpack Compose) │         │   (C# .NET Host)    │         │     Web / PWA       │
       └──────────┬──────────┘         └──────────┬──────────┘         └──────────┬──────────┘
                  │                               │                               │
                  └───────────────────────────────┼───────────────────────────────┘
                                                  ▼
                                 ┌─────────────────────────────────┐
                                 │   Google Firebase Cloud Stack   │
                                 │   • Firebase Authentication     │
                                 │   • Cloud Firestore Live Sync   │
                                 │   • Role-Based Security Rules   │
                                 └─────────────────────────────────┘
```

### 1. 📊 Executive Dashboard & Practice Pulse
- **Real-Time KPIs:** Dynamic counters for open operational tasks, urgent statutory deadlines, active client projects, and active team workload capacity.
- **Quick Action Bar:** One-click shortcuts to assign tasks, launch projects, broadcast tax notices, and verify portal syncs.
- **Notification Center:** Live activity stream logging task updates, progress submissions, circular alerts, and system changes.

### 2. 📋 Granular Task Allocation & Execution Engine
- **Multi-Dimensional Assignment:** Allocate tasks with custom priorities (`LOW`, `MEDIUM`, `HIGH`, `URGENT`), due dates, categories, tags, and assigned project associations.
- **Interactive Checklists & Progress Slider:** Sub-task checklist tracking with percentage calculation (0–100%) and audit remark history.
- **Lifecycle Status Pipeline:** Move tasks seamlessly across `TODO` ➔ `IN_PROGRESS` ➔ `IN_REVIEW` ➔ `COMPLETED`.
- **Advanced Filtering & Search:** Filter work by status, priority, category, tag taxonomy, assigned team member, or keyword search.

### 3. 🎯 Client Projects & Milestone Tracking
- **Engagement Management:** Organize tasks into dedicated client project umbrellas with unique project codes (e.g., `PRJ-GST-01`, `PRJ-AUDIT-24`).
- **Progress Aggregation:** Live progress indicators reflecting milestone health, target completion dates, and project lead ownership.

### 4. 📅 Statutory Compliance Engine & Team Calendar
- **Built-in Indian Statutory Calendar:** Pre-configured legal obligation deadlines for:
  - **GST (CBIC):** GSTR-1 (11th/13th), GSTR-3B (20th), GSTR-6 (13th), GSTR-7/8 (10th), CMP-08, Annual Returns (GSTR-9/9C).
  - **Income Tax (CBDT):** Advance Tax Q1–Q4, Monthly TDS Payments (7th), Quarterly TDS Returns (Form 24Q, 26Q, 27Q), Tax Audit Reports (Forms 3CA/3CB-3CD), Annual ITR filings.
  - **Corporate Law (MCA21 / ROC):** AOC-4 (Financials), MGT-7 (Annual Return), DIR-3 KYC, DPT-3.
  - **Payroll & Labor:** EPF Electronic Challan-cum-Return (15th), ESIC Contributions (15th), Professional Tax (PT - 20th).
- **Interactive Calendar View:** Schedule and review work by date with visual badges distinguishing general tasks from legal tax alerts.

### 5. 📑 Client Master & Monthly Compliance Tracker
- **Spreadsheet-style Compliance Matrix:** Track recurring monthly client deliverables across 7 key obligations: **TDS (7th)**, **GSTR-1 (13th)**, **GSTR-3B (20th)**, **Accounting Closure**, **PT (20th)**, **PF (15th)**, and **ESI (15th)**.
- **One-Click State Cycling:** Interactive toggle (`Pending` ➔ `Done` ➔ `Not Applicable`) with instant real-time synchronization.
- **Bulk Data Import/Export:** Built-in spreadsheet parser supporting Excel (`.xlsx`, `.xls`) and `.csv` importing with automated GSTN matching and CSV export.

### 6. 📢 Statutory Tax Desk & Notice-to-Task Conversion
- **Official Circular Central:** Publish and manage statutory circulars, departmental notifications, and critical advisories.
- **Severity Classification:** Tag circulars with `NORMAL`, `IMPORTANT`, or `CRITICAL_ACTION_REQUIRED`.
- **1-Click Notice Conversion:** Instantly convert statutory notifications into actionable team tasks with pre-populated details, deadline syncing, and team assignment.

### 7. 🔗 Government Portal Integrations Sync
- **Central Gateway:** Monitor and test connectivity to GST Portal, Income Tax e-Filing, MCA21, e-Way Bill System, EPFO/ESIC, and Custom Webhooks.
- **Heartbeat & Endpoint Auditing:** Live status tracking and webhook payload inspection.

---

## 🔒 Security Architecture & Role-Based Access Control (RBAC)

OfficeFlow enforces enterprise security via **Firebase Authentication** and declarative **Cloud Firestore Security Rules (v2)**. User identities are verified at the token level, with permissions resolved against the user's role in the database.

```
┌──────────────┬───────────────────────────────────────────────────────────────────────────────────────┐
│ Role         │ Permissions & Capabilities                                                            │
├──────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ ADMIN        │ • Full administrative control over all collections (Tasks, Projects, Roster, Portals) │
│              │ • Onboard new team members and assign access credentials                              │
│              │ • Delete tasks, projects, clients, and portal integrations                            │
│              │ • Database maintenance and system reset authority                                     │
├──────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ PARTNER      │ • Strategic firm oversight: view all client projects, workload analytics, and audits   │
│              │ • Create projects, assign tasks to any department, approve filings                    │
│              │ • Configure government portal integrations and broadcast tax advisories               │
├──────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ MANAGER      │ • Operational lead: create client projects and assign tasks within teams              │
│              │ • Access firm-wide team workload capacity matrix                                      │
│              │ • Convert statutory notices into assigned tasks and push milestone updates            │
│              │ • (Cannot delete other members' profiles or alter portal security configurations)     │
├──────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
│ TEAM_MEMBER  │ • Focused individual workspace: view only assigned tasks and checklists               │
│              │ • Push progress updates (0–100%), add completion remarks, and check off items          │
│              │ • View firm-wide statutory tax circulars and personal deadlines calendar              │
│              │ • Strict data privacy: database rules prevent reading other members' tasks            │
└──────────────┴───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Test Credentials & Demo Accounts Matrix

The system includes pre-configured demo user accounts mapped to each operational role for evaluation:

| User ID | Full Name | Email Address (Login) | Password | Security Role | Department | Primary Evaluation Scenario |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **USR-001** | Mahesh C. | `maheshconsultantpro@gmail.com` | `admin123` | **ADMIN** | Executive Leadership | Full admin privileges: team onboarding, portal configuration, task deletion |
| **USR-002** | Arun Singhal | `arun.s@officeflow.internal` | `partner123` | **PARTNER** | Corporate Advisory | Executive oversight: monitor corporate filing projects & review audits |
| **USR-003** | Priya Sharma | `priya.s@officeflow.internal` | `manager123` | **MANAGER** | Indirect Tax (GST) | GST Manager: convert GSTR-3B circular into team task & monitor workload |
| **USR-004** | Rohit Verma | `rohit.v@officeflow.internal` | `manager123` | **MANAGER** | Direct Tax (Income Tax) | Tax Manager: push advance tax computation progress to 75% |
| **USR-005** | Ananya Rao | `ananya.r@officeflow.internal` | `member123` | **TEAM_MEMBER** | Audit & Assurance | Staff: push progress on Statutory Audit task and add work notes |
| **USR-006** | Vikram Patel | `vikram.p@officeflow.internal` | `member123` | **TEAM_MEMBER** | Corporate Advisory | Staff: complete MCA AOC-4 & MGT-7 annual return checklist |
| **USR-007** | Sneha Kulkarni | `sneha.k@officeflow.internal` | `member123` | **TEAM_MEMBER** | Compliance & Payroll | Staff: file TDS Form 26Q quarterly return |
| **USR-008** | Client Rep | `client@apexholdings.com` | `client123` | **CLIENT** | Client Representative | Client Portal: read-only visibility into ongoing engagement milestones |

*(Note: In live cloud mode, sign-in accounts authenticate against Firebase Auth; for alternative enterprise setups, primary administrator bootstrap is keyed to `mahesh@primeaccounting.in`).*

---

## 🛠️ Technology Stack & Engineering Design

| Layer | Technologies & Frameworks | Description / Design Choice |
| :--- | :--- | :--- |
| **Android Native** | Kotlin 2.0+, Jetpack Compose, Material 3, AndroidX Lifecycle | Declarative UI, reactive state flows, edge-to-edge layout, dynamic theming. |
| **Local Persistence** | Room Database (KSP), SQLite, Moshi JSON | Local caching of notifications, portal configs, and offline fallback. |
| **Desktop Client** | C# .NET Minimal Host, WebView2 / HTTP Loopback | Lightweight standalone executable (`.exe`) binding `127.0.0.1` origin. |
| **Web & PWA** | Vanilla ES Modules, HTML5, Modern CSS Grid/Flexbox | Fast load times, zero external framework overhead, IndexedDB persistence. |
| **Cloud Database** | Google Cloud Firestore | Real-time multi-client document sync with client-side indexing. |
| **Authentication** | Google Firebase Authentication | Secure JWT token handling, credential hashing, session persistence. |
| **Security Rules** | Firestore Security Rules 2.0 | Fine-grained document-level RBAC enforced server-side by Google Cloud. |
| **Verification & QA** | `@firebase/rules-unit-testing`, Mocha, PowerShell REST | Complete emulator permission-matrix test suite and live endpoint verifier. |

---

## 📁 Repository & Project Structure

```
officeflow/
├── app/                                  # Android Native Application
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/example/
│   │   │   │   ├── data/
│   │   │   │   │   ├── local/            # Room Database & DAO interfaces
│   │   │   │   │   ├── model/            # Domain models (TaskItem, Project, TeamMember, etc.)
│   │   │   │   │   └── repository/       # OfficeRepository (Firestore & Room data layer)
│   │   │   │   ├── notification/         # Android Notification Channels & System Alerts
│   │   │   │   ├── ui/
│   │   │   │   │   ├── components/       # Reusable Compose Dialogs, Cards & BottomSheets
│   │   │   │   │   ├── screens/          # Dashboard, Tasks, Projects, Calendar, Tax, Portals
│   │   │   │   │   ├── theme/            # Material 3 Color Schemes, Typography & Styles
│   │   │   │   │   └── OfficeApp.kt      # Main Navigation & App Scaffold
│   │   │   │   └── MainActivity.kt       # Activity Entry Point & Runtime Permissions
│   │   │   ├── res/                      # Android XML Resources, Drawables, Mipmaps
│   │   │   └── AndroidManifest.xml       # App Manifest & Capabilities
│   │   └── test/                         # Android Unit Tests (Robolectric, Roborazzi)
│   ├── google-services.json              # Firebase Android Configuration
│   └── build.gradle.kts                  # Android Gradle Build Configuration
├── desktop/                              # Windows Desktop Client
│   ├── OfficeFlow.exe                    # Pre-compiled Standalone Desktop Binary
│   ├── OfficeFlowDesktop.cs              # C# .NET Launcher Source
│   ├── officeflow.html                   # Embedded Web Application Source
│   ├── build.ps1                         # PowerShell Compilation Script
│   └── clients-import.csv                # Sample Client Master Data for Spreadsheet Import
├── public/                               # Web & PWA Assets
│   └── index.html                        # Production Progressive Web App Single-Page App
├── scripts/                              # DevOps & Verification Scripts
│   ├── verify-firestore-rules.ps1        # Live REST API Security Rules Validation
│   └── capture-crash.ps1                 # Diagnostic Log Extraction Utility
├── tests/                                # Security Rules Unit Test Suite
│   ├── rules.test.mjs                    # Complete RBAC Permission Matrix Test Suite
│   ├── firebase.json                     # Firebase Emulator Configuration
│   └── package.json                      # Test Dependencies (@firebase/rules-unit-testing)
├── firestore.rules                       # Production Firestore Security Rules (RBAC)
├── firestore.interim.rules               # Transitional Rule Definition
├── OfficeFlow-fixed.apk                  # Signed, Ready-to-Install Android Package (APK)
├── OfficeFlow-desktop.exe                # Standalone Windows Desktop Executable
├── OfficeFlow.html                       # Standalone Offline-Ready Web Application
├── OfficeFlow_Test_Credentials.csv       # Test Credentials Matrix
├── Logins - New.xlsx                     # Comprehensive Master Logins Spreadsheet
├── metadata.json                         # Project Metadata
└── README.md                             # Project Documentation
```

---

## 🚦 Getting Started & Execution Guide

### Option 1: Run the Standalone Windows Desktop App
1. Navigate to the project directory.
2. Double-click `OfficeFlow-desktop.exe` (or `desktop/OfficeFlow.exe`).
3. The application will launch an isolated, local browser window connected to the shared Cloud Firestore database.
4. Sign in with any of the credentials from the [Test Credentials](#-test-credentials--demo-accounts-matrix) table.

### Option 2: Install and Run on Android Device / Emulator
1. **Direct Install (APK):**
   - Transfer `OfficeFlow-fixed.apk` to your Android device.
   - Tap to install (enable "Install unknown apps" if prompted).
   - Open **OfficeFlow** and log in.
2. **From Android Studio:**
   - Launch **Android Studio** and select **Open** ➔ choose the project root folder.
   - Allow Gradle to sync dependencies.
   - Connect an Android device (or launch an Android Virtual Device / Emulator with API 24+).
   - Click **Run (`Shift + F10`)**.

### Option 3: Run the Web Application / PWA
- Open `OfficeFlow.html` (or `public/index.html`) in any modern web browser (Google Chrome, Microsoft Edge, Mozilla Firefox, Apple Safari).
- All live data syncing, offline caching, and responsive UI components operate natively.

---

## 🧪 Testing & Security Verification

### 1. Running the Automated Firestore Rules Unit Test Suite
The security rules test suite executes 30+ assertions against the local Firebase Firestore Emulator without touching production data:
```powershell
# Navigate to the test directory
cd tests

# Install test dependencies (if not already cached)
npm install

# Run the permission matrix unit tests
npm test
```
**Test Coverage Includes:**
- ✅ Unauthenticated read/write prevention across all collections
- ✅ Non-roster authenticated user isolation
- ✅ Primary administrator self-bootstrap authorization
- ✅ Team member restriction to own tasks (`read`/`update` only on matching `assignedMemberId`)
- ✅ Manager authorization to create tasks, assign work, and broadcast circulars
- ✅ Manager restriction against deleting tasks or modifying team member access roles
- ✅ Partner and Admin full governance access
- ✅ Unauthorized collection creation refusal

### 2. Live REST Security Rule Verification
To test live rule enforcement against the deployed Firebase project:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-firestore-rules.ps1
```

---

## 📊 Summary of Project Deliverables

| Deliverable Item | File Location | Description |
| :--- | :--- | :--- |
| **Android APK (Release)** | `OfficeFlow-fixed.apk` | Ready-to-install Android mobile application package |
| **Windows Desktop Binary** | `OfficeFlow-desktop.exe` | Standalone executable for Windows workstations |
| **Web / PWA Application** | `OfficeFlow.html` / `public/index.html` | Cross-platform web application |
| **Android Source Code** | `app/src/main/java/com/example/` | Complete Kotlin & Jetpack Compose source codebase |
| **Desktop Launcher Source** | `desktop/OfficeFlowDesktop.cs` | C# .NET desktop launcher source code |
| **Cloud Security Rules** | `firestore.rules` | Production-ready Firestore RBAC security rules |
| **Automated Test Matrix** | `tests/rules.test.mjs` | Unit test suite for security validation |
| **Client Dataset** | `desktop/clients-import.csv` | Sample client database with GSTN and assignee mapping |
| **Test Credentials Sheet** | `OfficeFlow_Test_Credentials.csv` | Full credentials matrix for role verification |

---

## 👥 Contributors & Submission Details

- **Project:** OfficeFlow — Enterprise Practice & Compliance Management Platform
- **Application Version:** 1.0.0
- **Submission Category:** AICA Level II Project Submission
- **Target Audience:** Chartered Accountants, Tax Practitioners, Corporate Compliance Officers, Financial Advisors
