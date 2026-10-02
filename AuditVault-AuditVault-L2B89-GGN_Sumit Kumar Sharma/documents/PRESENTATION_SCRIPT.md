# AuditVault Presentation and Live Demonstration Script

## Recommended presentation length: 10–12 minutes

### 1. Opening (about 45 seconds)

“Good morning/afternoon. Today I am presenting AuditVault, an internal audit engagement and working-paper management application. Audit teams often depend on folders, spreadsheets, emails, and manually named file versions. That creates risks such as missing evidence, unclear ownership, duplicate versions, weak review tracking, and limited management visibility. AuditVault brings this lifecycle into one secure, role-based workspace.”

“The application is built with Python, Streamlit, SQLite, SQLAlchemy, and local version-controlled file storage. It supports Indian date and currency formats and can later migrate to a larger database such as PostgreSQL.”

### 2. Main value proposition (about 45 seconds)

“AuditVault manages an audit from engagement creation through final archival. It connects clients, engagement letters, teams, RCMs, evidence, observations, review comments, completion controls, and an audit trail. Its key principle is: every engagement, every version, securely vaulted.”

### 3. Explain the user roles (about 2 minutes)

“There are three user roles.”

“First, the Admin controls user administration. The Admin can create Managers and Team Members, reset passwords, delete Manager accounts, view the audit trail, and switch into another account for support. Every switch-user action is logged. The Admin is intentionally separated from audit execution and does not directly create or complete engagements.”

“Second, the Manager owns audit delivery. A Manager creates clients and engagements, defines the audit period, scope, deadline, and budget, uploads the engagement letter, creates and edits audit squads, assigns auditors, manages RCM information, reviews fieldwork, completes the audit, and can reopen it when justified. Managers may register or delete Team Members, but only an Admin can create or delete a Manager. Controlled client and engagement deletion requires exact confirmation and separately asks whether locally stored evidence should also be removed.”

“Third, the Team Member or Auditor sees only assigned engagements. The auditor works on permitted RCM content, uploads evidence to individual line items, records observations, responds to review comments, and views file-version history. Once a Manager completes and locks an engagement, the auditor loses editing rights.”

### 4. Live demonstration flow (about 6 minutes)

#### Admin demonstration

1. Sign in with the Admin account.
2. Open Team Management and show that Admin can register either a Manager or Team Member.
3. Show Reset Password.
4. Open Audit Trail and explain that important actions are timestamped.
5. Open Access Control Audit and show role filters, state changes, SHA-256 integrity, and the compliance CSV export.
6. Show Switch User and explain that impersonation is logged.
7. Open Delete Account and explain that Admin can delete Manager accounts but cannot use this control to delete another Admin.

Say: “This demonstrates segregation of duties and administrative accountability.”

#### Manager demonstration

1. Sign out and sign in as `rohit.sharma`.
2. Show Dashboard summary cards, charts, engagement status, deadlines, and Indian currency formatting.
3. Open Clients and explain the centralized client master.
4. Open Team Management, select an existing squad, add or remove a member, and save.
5. Open Engagements and select Sundaram Textiles Ltd.
6. Point out the engagement code, process, audit period, estimated fee, and status.
7. Download the RCM Excel template and explain that the same controlled format is used for every bulk upload.
8. Move through the RCM line-item tabs and explain that each risk/control receives a dedicated workspace.
9. Show evidence, observations, comments, and version history.
10. Explain that Complete Audit consolidates the newest evidence versions into a ZIP and locks the engagement.
11. Show the controlled deletion panels for Team Members, clients, engagements, and audit squads. Explain the exact-name/code confirmation and the separate local-evidence choice.

Say: “A Manager can reopen a completed audit, but the action and justification remain visible in the audit trail.”

Say: “When an account is deleted, access is revoked while historical comments, upload attribution, and audit evidence remain available for accountability.”

#### Auditor demonstration

1. Sign out and sign in as `anita.kulkarni`.
2. Show that only assigned engagements are visible.
3. Open a line item, upload sample evidence, enter an observation, and respond to a query.
4. Explain the folder pattern: engagement, client, line item, and date.
5. Explain that a new dated folder preserves earlier evidence versions instead of overwriting them.

Say: “This gives the engagement team a clear working-paper trail while preserving Manager control.”

#### Profile demonstration

1. Open My Profile.
2. Upload a PNG or JPEG photo.
3. Update the profile and show the avatar in the top bar.
4. Briefly show the light/dark theme option.

### 5. Sample business scenario

“For the demonstration, our client is Sundaram Textiles Ltd. The engagement code is ENG-2026-014, the process is Procure-to-Pay, and the estimated fee is ₹14,50,000. A representative RCM item is P2P-01. We import the approved RCM, test whether purchase orders, goods-received notes, and invoices agree, upload a sample purchase-order workbook as evidence, record any exception, and submit it for Manager review.”

Suggested observation:

“During sample testing, 3 of 25 invoices did not contain evidence of independent three-way-match review before payment. This may increase the risk of duplicate or unsupported payments. We recommend configuring a mandatory approval control and monitoring exceptions monthly.”

Suggested review query:

“Please confirm whether the three exceptions were approved retrospectively and attach the supporting approval evidence.”

Suggested auditor reply:

“Management provided approvals for two exceptions. One item remains unsupported and has been retained in the final observation.”

### 6. Security and technical explanation (about 1 minute)

“Passwords are stored as salted hashes rather than plain text. Access is filtered by role and assignment. User actions are logged in an append-only SHA-256 hash chain. Audit evidence is stored in a structured folder hierarchy, and completion creates a consolidated archive. The demonstration account can activate on only one computer through a local device-binding record. File deletion is restricted to the AuditVault data directory and requires explicit confirmation.”

“For production use, I would place the app behind HTTPS, use PostgreSQL, centralized identity management, encrypted object storage, server-side session controls, regular backups, and independent security testing.”

### 7. Closing (about 30 seconds)

“AuditVault reduces administrative effort, improves traceability, and gives Managers real-time visibility without removing professional audit judgment. It demonstrates how a fragmented audit process can become a controlled, searchable, and reviewable digital workflow. Thank you; I am happy to demonstrate any role or workflow in more detail.”

## Demonstration credentials

| Role | User ID | Password | Intended demonstration |
|---|---|---|---|
| Admin | `admin` | `admin123` | User management, reset password, audit trail, switch user |
| Manager | `rohit.sharma` | `manager123` | Dashboard, clients, teams, engagements, finalization |
| Manager | `manager.rajesh` | `manager123` | Second Manager account and role separation |
| Team Member | `anita.kulkarni` | `auditor123` | Assigned audit fieldwork and observations |
| Team Member | `vikram.n` | `auditor123` | Team membership and assigned work |
| Team Member | `neha.patil` | `auditor123` | IT audit persona and assigned work |
| Device-bound demo | `demo.viewer` | `AuditVault@Demo2026` | Viewer demonstration; first computer activation only |

Change every default password before using the application with real information.
