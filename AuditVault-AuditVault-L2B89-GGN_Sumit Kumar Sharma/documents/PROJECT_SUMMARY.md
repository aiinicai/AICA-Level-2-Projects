# AuditVault - AI-Powered Internal Audit Engagement Management

## Project overview

AuditVault is a Python and Streamlit application designed for internal audit departments and Chartered Accountant firms. It replaces fragmented folders, spreadsheets, email threads, and manual evidence tracking with a centralized, role-based audit workspace.

The application manages the full engagement lifecycle: client and engagement setup, team assignment, Risk Control Matrices (RCM), fieldwork evidence, observations, review queries, audit completion, consolidated archival, and audit-trail reporting.

## Business problem addressed

Traditional audit teams commonly face:

- Inconsistent working-paper folders and file names.
- Missing or overwritten evidence versions.
- Limited visibility over engagement progress.
- Review comments dispersed across email and chat.
- Weak traceability of user activity and status changes.
- Difficulty enforcing role-based responsibilities.

AuditVault organizes this work into a controlled and searchable workflow while preserving professional audit judgment.

## User roles

### Admin

- Creates Managers and Team Members.
- Resets user passwords.
- Reviews the audit trail.
- Uses logged support impersonation to view another user's workspace.
- Does not directly execute audit engagements.

### Manager

- Creates clients, engagements, and audit squads.
- Adds or removes team members from existing squads.
- Uploads engagement letters and manages RCM information.
- Assigns auditors and monitors progress.
- Reviews observations and evidence.
- Completes, locks, consolidates, and reopens engagements.
- Can create Team Members but cannot create another Manager.

### Team Member / Auditor

- Sees only assigned engagements.
- Works on permitted RCM content.
- Uploads evidence to date-versioned folders.
- Records observations and responds to review queries.
- Loses editing access after engagement completion and locking.

## Key functionality

- User ID and hashed-password authentication.
- Role-based and assignment-based access control.
- Client, engagement, team, RCM, and fieldwork management.
- Evidence storage by engagement, client, line item, and date.
- Observation and review-query workflows.
- Downloadable RCM, evidence-index, observation-register, and engagement-letter templates.
- Consolidated final ZIP generation.
- Append-only application audit trail.
- Indian date and currency formatting.
- Light/dark interface options and profile-photo support.
- Device-bound presentation account for first-computer activation.

## Technology used

- Python
- Streamlit
- SQLAlchemy ORM
- SQLite
- Pandas and OpenPyXL
- Plotly
- python-docx and pypdf
- Local structured file storage

## Example demonstration scenario

The included fictional scenario is a Procure-to-Pay audit of Sundaram Textiles Ltd. The engagement contains four RCM line items, an observation, review comments, and sample evidence metadata. It demonstrates the flow from planning and fieldwork through Manager review and final consolidation.

## AI contribution

Generative AI was used as a development assistant to translate business requirements into the application structure, refine the user interface, analyze access-control requirements, generate sample fictional audit data, troubleshoot the implementation, and prepare documentation and presentation materials. Human judgment was used to define the audit workflow, validate permissions, review generated code, test the application, and determine the final design.

## Installation and execution

1. Install Python 3.9 or later.
2. Create and activate a virtual environment.
3. Run `pip install -r requirements.txt`.
4. Run `streamlit run app.py` or use `run_auditvault.bat` on Windows.
5. Open `http://localhost:8501` if the browser does not open automatically.

The SQLite database and fictional sample records are initialized automatically on first run.

## Demonstration account

- User ID: `demo.viewer`
- Password: `AuditVault@Demo2026`

The demonstration account is locally bound to the first computer on which it is activated. The standard presentation credentials are listed in the included presentation document.

## Limitations and future development

This submission is a functional educational prototype, not a production-certified audit platform. Production deployment should include HTTPS, PostgreSQL, centralized identity management, server-side session and licensing controls, encrypted object storage, backup and recovery processes, formal database migrations, automated tests, and independent security testing.

## Data and privacy

All sample data included with the submission is fictional. The submission intentionally excludes the developer's local database, working-paper vault, environment variables, user-uploaded profile pictures, and machine-specific activation records.
