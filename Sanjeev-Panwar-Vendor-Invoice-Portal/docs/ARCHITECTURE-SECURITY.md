# Architecture and security

Browser -> Waitress (loopback) -> Django WSGI/URL routing -> billing views/forms/models -> demo SQLite database and authorized private document storage. Django templates render the UI; WhiteNoise serves collected static assets. All data paths stay in this copy's local_demo directory.

## Workflow and entities
User -> VendorProfile (Finance approval) -> Invoice (Company, financial fields and status) -> Documents. Finance review records approved/rejected state; approved invoices are grouped in ExportBatch and marked exported after CSV generation. AuditEvent records selected registration, approval, submission, review and export actions.

Extraction is local: digital PDF text through PyMuPDF; raster OCR through optional Tesseract; regex/context heuristics identify recipient PIN, invoice/PO number, date, currency and amounts. No external generative model, cloud storage, SMTP service or tunnel is configured in the clean copy.

## Verified by regression checks
Registration/login; approval gating; staff-only vendor approval with POST; digital-PDF submission; extraction; recipient mismatch and duplicate rejection; Finance review/approval; export and subsequent review lock; vendor document/detail isolation; malformed PDF rejection; CSRF enforcement on a modifying Finance request. These checks are evidence for specific paths, not a complete security audit.

## Source controls and limits
- Upload extensions/signatures and document structure are checked; combined size limited to 20,000,000 bytes. Basic upload validation permits PDFs up to 50 pages, but invoice/PO extraction rejects PDFs above 30 pages. Image validation permits up to 25 megapixels (an additional extraction check is 30 megapixels).
- Generated storage names avoid trusting original filenames. Download views enforce owner-or-staff authorization. Staff users and Django superusers remain highly privileged.
- CSV strings beginning with formula-related characters are prefixed for safer spreadsheet use; downstream ERP import must validate the format independently.
- Heuristic extraction needs mandatory human verification. No accuracy metric was measured; OCR can fail closed on unreadable/ambiguous recipient details.
- File writes occur after the invoice database transaction: storage failures can leave inconsistent metadata. There is no distributed transaction or repair mechanism.
- Duplicate detection and export selection are not protected against all concurrent submissions; there is no unique business-key constraint or deployment load/concurrency validation.
- The "previous" values recorded during Finance edits may not reliably preserve pre-edit values because ModelForm validation can mutate the bound instance. Audit data is not tamper-evident and privileged admin edits can bypass the UI's export lock.
- There is no antivirus/sandboxed parsing, tested brute-force registration protection, email verification, comprehensive permission test matrix, retention policy or production backup workflow.
- Password-reset mail files contain sensitive links after local execution; all runtime artifacts remain excluded even for synthetic data.

Use fictional inputs and loopback only. Production use needs a separately reviewed HTTPS deployment, roles/permissions, safe file processing, transactional consistency, backups/retention, operational monitoring and dependency review. No claim of production readiness or compliance is made.
