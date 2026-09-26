# AuditVault 🛡️
> **"Every Engagement. Every Version. Securely Vaulted."**

AuditVault is an enterprise-grade, Python & Streamlit-powered Internal Audit Engagement and Working Paper Management System architected for Internal Audit Departments of corporates and Indian Chartered Accountant (CA) firms.

---

## 🌟 Key Capabilities & Highlights

1. **Role-Based Access Control (RBAC)**:
   - 👑 **Admin**: Manages accounts, resets credentials, inspects the immutable audit trail, and features **Support Impersonation ("Switch User")** with mandatory permanent audit logging. Admins cannot create engagements or edit audit data directly.
   - 👔 **Manager**: Creates engagements, clients, teams, and Team Member accounts. Uploads Engagement Letters and RCM matrices. Enforces **Field-Level Lock & Override Hierarchy** (Manager locks cannot be overwritten by auditors). Conducts reviews, signs off line items, executes **Consolidated Archival**, and controls engagement lock/reopen states. Only an Admin can create another Manager.
   - 🔍 **Engagement Team Member (Auditor)**: Views only assigned engagements. Uploads evidence to auto-generated daily versioned vaults, records observations with risk ratings, and participates in in-app review comment/query threads.

2. **Access Governance & Accountability**:
   - Dedicated access-control ledger inside Team Management and the main Audit Trail.
   - Search and filter by category, actor role, event, target, and applied RBAC rule.
   - Side-by-side previous/new state inspection plus downloadable event JSON.
   - SHA-256 chained integrity verification for every audit record.
   - Compliance-ready CSV export for ISO 27001, SOC 2, and ICAI access-governance review.
   - Safe audit-team deletion removes member links and detaches the team label from existing allocations without deleting engagements or users.
   - Controlled deletion workflows: Managers can delete Team Member accounts, clients, engagements, and audit teams; Admins can delete Manager accounts. Client and engagement deletion asks separately whether local evidence/base files should also be removed.
   - Deleted user accounts are access-revoked and removed from active assignments while historical comments, upload attribution, and immutable audit evidence remain available.

3. **Core 7-Step Lifecycle**:
   - **Step 1: Engagement Creation**: Manager specifies client, scope, audit period (`DD-MM-YYYY`), budget in Indian Rupees (`₹ 14,50,000`), deadline, and uploads signed Engagement Letter.
   - **Step 2: Team Assignment**: Manager assigns specialized squads (Team 1, Team 2) or individual auditors with specific roles.
   - **Step 3: Risk Control Matrix (RCM)**: Import the included Excel/CSV templates or add line items manually. Manager lock controls visually safeguard critical testing steps.
   - **Step 4: Fieldwork & Dedicated Line Item Workspace**: Dedicated tab per RCM line item. Automatically creates daily date-versioned storage:  
     `/AuditVault_Data/engagements/{EngagementID}/{ClientName}/{LineItemID}/{DD-MM-YYYY}/`  
     Includes file version explorer, native desktop app launch, and observation rich editor.
   - **Step 5: Review & In-App Queries**: Threaded discussions directly within the line item workspace, tagging review queries and resolution states. Manager marks line items as "Reviewed".
   - **Step 6: Finalization, Consolidation & Archival**: Manager executes "Complete Audit", consolidating the latest version of every evidence file into:  
     `/AuditVault_Data/consolidated/{EngagementID}_{ClientName}/{LineItemID}/`  
     Prompts for ZIP archive download and provides the choice to retain originals as backup or clean up. Engagement is locked; Manager can reopen with a mandatory logged justification.
   - **Step 7: Immutable Audit Trail**: Append-only log recording every login, upload, edit, status transition, reopening, and admin impersonation. Cannot be altered or purged by any user.

4. **Indian Locale Formatting Throughout**:
   - **Dates**: Enforced `DD-MM-YYYY` display. Interactive date-picker widget PLUS flexible manual 8-digit auto-parser (e.g. typing `04062026` auto-formats to `04-06-2026`).
   - **Numbering & Currency**: Formatted with the Indian numbering system (Lakhs and Crores e.g. `₹ 14,50,000` instead of `1,450,000`).

5. **UI/UX Design**:
   - Deep Blue (`#0A2540`), Slate White (`#F8FAFC`), Gold/Amber (`#F59E0B`), and Teal accents.
   - Light mode and Dark mode toggles.
   - Guided role-specific product tour on first login or on demand.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure Python 3.9+ is installed on your machine.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run AuditVault
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🔑 Pre-Seeded Presentation Accounts

AuditVault initializes with realistic enterprise audit data:

| Role | Username | Password | Full Name & Designation |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | Sunil Mehra (Chief Audit Executive / IT Admin) |
| **Manager** | `rohit.sharma` | `manager123` | Rohit Sharma (Internal Audit Manager) |
| **Manager** | `manager.rajesh` | `manager123` | CA Rajesh Sharma (Senior Audit Manager & Partner) |
| **Auditor** | `anita.kulkarni` | `auditor123` | Anita Kulkarni (Lead Internal Auditor) |
| **Auditor** | `vikram.n` | `auditor123` | Vikram N. (Audit Associate) |
| **Auditor** | `neha.patil` | `auditor123` | Neha Patil (IT Systems Auditor) |
| **Device-bound Demo** | `demo.viewer` | `AuditVault@Demo2026` | Demo Viewer (first computer activation only) |

The login screen requires the User ID and password. The shared demo account is bound to the first computer that activates it. This is a prototype deterrent, not a replacement for server-side licensing. Delete or reset the local binding only as the project owner.

> **Important:** Change all seeded passwords before entering real client or audit information.

---

## GitHub-safe publication

The included `.gitignore` prevents the local database, evidence vault, environment file, profile photos, and generated archives from being committed. Before publishing, confirm with `git status` that none of those files are staged.

```bash
git init
git add .
git status
git commit -m "Initial AuditVault release"
git branch -M main
git remote add origin https://github.com/YOUR-USER/YOUR-REPOSITORY.git
git push -u origin main
```

Anyone cloning the repository can then run:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Source protection limitation

A public GitHub repository necessarily allows visitors to read and download its source. The included `LICENSE` reserves legal rights, but it cannot technically stop copying. If source secrecy is required, keep the repository private and distribute a compiled Windows build (for example, with Nuitka) or host AuditVault on a controlled server so users access only the web interface.

---

## 📁 Repository Structure

```
├── app.py                      # Main Streamlit application entrypoint & routing
├── database.py                 # SQLAlchemy DB engine & automatic database seeder
├── models.py                   # ORM models (Users, Engagements, RCM, Evidence, Audit Trail, etc.)
├── auth.py                     # Authentication, PBKDF2/bcrypt hashing, Admin Impersonation
├── rcm_import.py               # Validated CSV/XLSX RCM parser with header detection
├── utils.py                    # Indian dates (DD-MM-YYYY), currency (₹), Vault storage & ZIP engine
├── styles.py                   # Custom CSS styling (Light/Dark themes, badges, KPI metric cards)
├── requirements.txt            # Python dependencies
├── tests/                      # Automated role and import smoke tests
└── sample_data/
    ├── sample_rcm_template.xlsx      # Styled Risk Control Matrix import template
    ├── sample_rcm.csv                # CSV Risk Control Matrix import template
    ├── sample_evidence_register.csv  # Suggested evidence index format
    ├── sample_observation_register.csv # Suggested observations register format
    └── sample_engagement_letter.txt  # Sample signed engagement letter
```

See `SELF_TEST_REPORT.md` for the final defect list and verification results.
See `DEMO_CREDENTIALS.md` for the complete clean-install demonstration account list.

---

## 🏛️ Vault Storage Directory Structure

When running, AuditVault automatically maintains an organized repository inside `AuditVault_Data/`:

```
AuditVault_Data/
├── engagements/
│   └── {EngagementID}/
│       └── {ClientName}/
│           └── {LineItemID}/
│               └── {DD-MM-YYYY}/          <-- New folder created per calendar day of modification
│                   └── [Evidence Files]
├── consolidated/
│   └── {EngagementID}_{ClientName}/
│       └── {LineItemID}/
│           └── [Final Latest Files]
├── exports/                               <-- Downloadable consolidated ZIP archives
├── engagement_letters/
└── rcm/
```
