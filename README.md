# CA Practice Management – Consolidated V2.4

This release builds on the consolidated V2.1 application and retains the existing local-first FastAPI/SQLite architecture, V1.7 dashboard theme, Google Calendar/Meet integration, clients, assignments, tasks, meetings, documents, calls, commitments, compliance, approvals and client 360° features.

## Changes in V2.4
- Backup & Recovery and Staff Management are visible in the Administrator navigation.
- Staff Management restored: add employee logins, deactivate and reactivate logins. No fixed two-staff limit. Deactivation preserves historical records and assignments.
- Removed the Manager login role. Existing Manager users are migrated to Staff without deleting their accounts or historical records. Approval is now a single Administrator approval/return workflow.
- Administrator display name can be changed in Settings. This changes the displayed label only; it does not change the login username.
- Billing register: invoice records with taxable amount and GST rate, receipts, outstanding balance.
- Professional time entries and unbilled WIP.
- Practice MIS: billing, receipts, outstanding, WIP, receivables ageing and assignment mix by service line.
- CSV exports for clients, invoices and compliance.
- Backup archive includes SQLite database snapshot, client documents and local configuration/integration files; optional encrypted external-drive copy.

## Upgrade instructions
1. Stop the existing server.
2. Make a full copy of the existing application folder before upgrading.
3. Extract this ZIP and copy the contents of `ca_practice_prototype` into the existing application folder.
4. Replace application files when prompted.
5. **Do not replace or delete the existing `data` folder.** Existing `practice.db`, documents, Google OAuth client JSON, encrypted Google token, keys and session secret must be preserved.
6. Start with `start_windows.bat`. SQLite schema migrations run at startup.

## Important operating notes
- Existing Manager accounts are retained but converted to Staff. Reallocate assignments if required.
- Administrator approvals replace the former Manager-then-Partner sequence. The Administrator login is the approval authority in this prototype.
- Billing records are management records. Validate invoice numbering, GST treatment, tax invoice particulars and accounting entries before using them as statutory invoices or books of account.
- CSV exports contain client-confidential data; store and transmit them securely.
- Local backup ZIPs contain confidential data and are not encrypted. Protect the laptop and local backup folder. The external copy is encrypted. Keep a separate secure copy of the recovery key; losing it prevents decryption.
- This release creates backups on demand. Scheduled unattended backups, guided restoration and verified restore testing remain future work. Test restoration on a separate copy before relying on backups.
- This is a practice-management prototype, not independently security-audited or penetration-tested. Continue using dummy data until security, backup restoration and operational testing are completed.


## V2.4.6 Sidebar repair (navigation-only)
- Replaced the accumulated V2.4.2–V2.4.5 sidebar CSS patches with one authoritative layout block.
- Sidebar is fixed to the viewport; the brand area stays fixed; only the navigation list scrolls.
- The navigation uses a zero-basis, shrinkable flex region with an explicit constrained height and `overflow-y: scroll`, preventing long menus from expanding beyond the viewport.
- The menu remains a single vertical list at narrow widths; it does not switch into a two-column menu below 620px.
- All 16 Administrator navigation links remain in `base.html`. Staff Management, Backup & Recovery and Billing & WIP remain Admin-only in navigation.
- No database, application routes, business logic, or existing practice data were changed.

Validation performed for this navigation-only package:
- Confirmed 16 navigation anchors are present in the shared template.
- Confirmed Admin-only conditions remain around Staff Management, Backup & Recovery and Billing & WIP.
- Confirmed Billing route continues to call the existing Administrator guard.
- Confirmed Practice MIS remains visible to Staff while its template hides financial billing, collections, outstanding and WIP figures unless `admin` is true.
- Python application source compiles successfully.
- No live browser acceptance test on the user's laptop has been performed. Please test this package against a copy of the application before replacing the working folder.


## Consolidated V2.7 development update (based on V2.4.6)

This package retains the existing V2.4.6 application and adds:
- Administrator display-name dashboard greeting.
- Activity Logs page (Administrator sees practice-wide activity; staff see their own activity).
- Document version indexing with SHA-256 hashes, revision uploads and historical downloads.
- Notice and Litigation register with reply, hearing and appeal dates.
- Automation Rules configuration with enabled/disabled controls and task-submission event logging.
- Local Practice Assistant for structured searches of authorised assignments, tasks, compliance, documents, notices and calls.

Important scope notes:
- The Practice Assistant is a local structured-query assistant, not a generative AI model and not a tax/legal opinion engine.
- Automation rules are configuration records; only the task-submission event is wired in this release. Other displayed rules are not represented as fully executing automations.
- Gmail inbox/attachment ingestion, automatic personal WhatsApp extraction, external AI/OCR and unattended daily scheduler require credentials, API approvals or additional deployment decisions and are not silently enabled.
- Continue to preserve the existing `data` folder and make a full backup before upgrading.


## V2.8 – Conversational AI & Regulatory Intelligence

### Practice Assistant
- Multi-turn conversations with saved chat history per login.
- Natural-language intent classification and access-controlled local database queries.
- Regulatory questions search the locally collected official-source bulletin and, when enabled, use live web research through the OpenAI Responses API web_search tool. Live web search requires an OpenAI API key and OpenAI endpoint; compatible chat endpoints alone do not provide this capability.
- AI responses require an Administrator-configured OpenAI-compatible Chat Completions API key/model in Settings.
- Client-specific records are NOT sent to the AI provider unless the Administrator explicitly enables that setting. It is disabled by default.
- When client-data sharing is disabled or no API key is configured, supported database queries still run locally and show matching records.

### Regulatory Bulletin
- Official-source RSS collection for Income Tax Department circulars, notifications and press releases, SEBI and PIB. Secondary commentary page monitors include Taxmann, EY India, Deloitte India, KPMG India and Grant Thornton Bharat, clearly separated from primary government/ICAI sources.
- Conservative daily page monitoring for official CBIC/GST Council, MCA and ICAI update pages.
- Important items are held in Pending Review; Administrator approval is required before publication. Routine items are published automatically.
- AI summaries use only the collected public headline/description and include a reminder to verify the original source. The Administrator can generate missing summaries for previously collected updates from the Bulletin page.
- Each bulletin item links to the original source. The source directory marks RSS versus official-page monitoring.
- Daily fetch can be run manually from the Bulletin page by the Administrator.

### Daily Windows schedule
1. Run `start_windows.bat` once so `.venv` and dependencies are installed.
2. Run `install_daily_regulatory_task.bat` once from the application folder.
3. The task runs daily at 7:00 AM while the Windows user is logged in. It can also be run manually from the Bulletin page.
4. If the laptop is off or asleep at 7:00 AM, Windows Task Scheduler is configured to start the missed task when available.

### AI setup and privacy
1. The Administrator opens Settings > AI Assistant & Regulatory Intelligence.
2. Enter an API key, model name and HTTPS-compatible Chat Completions endpoint.
3. Save the key. It is encrypted locally using a Fernet key stored in the application data folder.
4. Client-data processing remains disabled by default. Enable only after firm approval and review of the provider's privacy and retention terms.
5. Public regulatory source text may be sent to the configured AI provider to generate summaries.

### Source coverage limitations
- Official Income Tax RSS feeds, SEBI RSS and PIB RSS are collected automatically.
- CBIC, GST Council, MCA and ICAI pages are monitored by conservative link extraction where accessible. Government pages may change structure, rate-limit automated requests or return no extractable updates; each source's last-check/error status is recorded.
- A daily collector does not guarantee that every regulator publishes an RSS feed or that every update is captured. The official source directory remains available for direct verification.
- Regulatory summaries are informational and must not replace reading the original notification/circular or professional review.


### V2.8.1 – Practice Assistant answer quality
- General questions, explanations, drafting and multi-part prompts now reach the AI instead of being stopped by a fixed category clarification.
- Question classification is performed on the question only and does not require enabling client-data processing.
- The assistant is instructed to answer every part, explain reasoning and practical implications, and vary structure/depth to suit the question.
- Increased the practice-answer response budget to support more complete answers.
- Existing client-data privacy gates and authorised-record restrictions are retained.


## V2.9 – Reliability, deletion controls and workflow hardening
- Added administrator-only deletion controls for clients, assignments, tasks, staff logins, calls, commitments, documents (including stored versions), meetings/action items, notices, compliance items and invoices.
- Client and assignment deletion performs explicit dependency cleanup; invoices with receipt history cannot be deleted; staff logins with linked work must be reassigned or deactivated first.
- Added audit-log entries for deletion actions.
- Added login throttling (8 failed attempts per username/IP per 15-minute window; in-process limiter).
- Session lifetime limited to 8 hours; enable HTTPS-only cookies in HTTPS deployments with `CA_FORCE_HTTPS=1`.
- Added upload extension allowlist and 20 MB limit for document uploads and revisions.
- Added decimal-safe invoice total rounding, over-receipt prevention and CSV formula-injection mitigation.
- Destructive actions require Administrator role and browser confirmation.

IMPORTANT DEPLOYMENT NOTES:
- Back up `data/practice.db`, `data/client_docs/`, `data/.session_secret`, AI key files and Google credential files before upgrading.
- Test on a copy of the existing database first. Deletion is permanent; client deletion removes linked operational records and document files.
- HTTPS-only cookies must be enabled only when the app is actually served through HTTPS.
- The built-in login limiter is per-process. Multi-worker or internet-facing deployments require a shared rate limiter, CSRF protection, reverse-proxy HTTPS, secure secret management, and professional security review.
- Gmail sending, WhatsApp Business API delivery, and external workflow automation require verified provider credentials and organisation consent. The app's existing manual WhatsApp handoff and Google Calendar connection are not equivalent to fully automated messaging.


# V2.9 – Full application hardening and workflow improvements

## Included in this release
### Phase 1 – Essential controls
- Added double-submit CSRF protection to application POST forms, including multipart document uploads.
- Added per-process login throttling after repeated failed attempts.
- Session lifetime is limited to 8 hours. Set `CA_FORCE_HTTPS=1` only when serving behind correctly configured HTTPS.
- Added file extension allowlisting and a 20 MB limit for document uploads and revisions.
- Added invoice total rounding using decimal arithmetic and blocked receipts above the invoice balance.
- Added CSV formula-injection protection.
- Restricted staff approval visibility to requests they raised or assignments they are allocated to.
- Deletion actions are administrator-only and create activity-log entries.

### Deletion and record lifecycle
Administrator deletion controls are available for clients, assignments, tasks, staff logins, calls, commitments, documents and document versions, meetings and meeting action items, notices, compliance items, approval requests, invoices, receipts, time entries, regulatory bulletin items, regulatory sources and automation rules.
- Client deletion removes linked client operations, assignments, billing records, documents and stored document versions.
- Assignment deletion removes its tasks and allocation rows, and safely unlinks related records where possible.
- An invoice with receipt history cannot be deleted until receipt entries are reversed/deleted.
- A staff login with linked work cannot be hard-deleted; reassign the work first or deactivate the login to preserve historical accountability.
- Every destructive action asks for browser confirmation. Deletion is permanent.

### Phase 2 – AI and practice intelligence
- Retained the conversational AI response improvements and expanded answer budget.
- OpenAI insufficient-quota, rate-limit and invalid-key errors now receive clearer user-facing messages.
- Regulatory research continues to prioritise primary sources and distinguishes official instruments from commentary.
- MIS effective fee-per-hour denominator now uses billable hours rather than all recorded hours.

### Phase 3 – Workflow automation
- Added executable daily internal checks for overdue compliance items, client commitments and unpaid invoices.
- Daily checks are idempotent per record per day and create internal event alerts without sending external messages.
- Added a Run Automations Now control for administrators.
- Updated the Windows Scheduled Task to run internal reminder checks and regulatory collection every day at 7:00 AM.
- Existing Google Calendar/Meet integration and manual WhatsApp handoff are retained.

## External integrations requiring setup
Gmail inbox/attachment ingestion and WhatsApp Business API message delivery are not enabled merely by installing this ZIP. They require Google OAuth consent with the appropriate Gmail scope, a configured WhatsApp Business Cloud API account/phone number/token, security review, and user-approved message workflows. The current WhatsApp workflow is a user-reviewed handoff, not unattended sending. No external email or WhatsApp messages are sent by the new daily automation checks.

## Upgrade safely
1. Stop the existing application.
2. Make a complete backup of the entire application folder, especially `data/practice.db`, `data/client_docs/`, `.session_secret`, encrypted AI key files, Google OAuth client JSON and Google token/key files.
3. Extract this ZIP into a new folder first and test it against a COPY of your existing `data` folder.
4. After successful testing, replace application code/templates/static files while preserving your original `data` folder.
5. Run `start_windows.bat`; database migrations run at startup.
6. If deployed behind HTTPS, configure `CA_FORCE_HTTPS=1` in the environment. Do not set it for plain localhost HTTP or browser sessions will not retain secure cookies.
7. Run `install_daily_regulatory_task.bat` from the Windows account that should own the daily scheduled task.

## Limitations and production readiness
- Automated testing was performed on a fresh test database and local TestClient; it is not a live acceptance test against your firm's production database or Windows environment.
- The login limiter is in-process and should be replaced by a shared rate limiter for multi-worker deployments.
- This application has not undergone an independent penetration test or external security certification.
- Regulatory feeds and page monitors depend on source-site availability and layout; a successful fetch does not prove that every legal update has been captured.
- Review database backups and test restoration before production use. Keep dummy-data testing until your own live data and integrations have been verified.
