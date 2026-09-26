# AuditVault Self-Test Report

Test date: 26-09-2026

## Result

AuditVault passed the final automated and live smoke tests. No blocking defect remains in the tested workflows.

## Defects found and fixed

1. **Styled Excel RCM template could not be imported**  
   Cause: the template contains a title and guidance rows above the actual column headers.  
   Fix: the importer now detects the real RCM header row within the opening rows of an Excel or CSV file.

2. **Valid RCM import could fail while saving**  
   Cause: the application captured a Sub Process value, but the database model did not include that column.  
   Fix: the field was added to the model with a safe automatic SQLite schema upgrade for existing installations.

3. **Malformed or unrelated files could create unusable RCM rows**  
   Fix: imports now require Risk Description and Control Description columns and return a clear list of missing and detected columns.

4. **Legacy comma-heavy CSV rows failed with a tokenizing error**  
   Fix: the supplied CSV is correctly quoted and the importer also repairs the older seven-column sample format when possible.

5. **Several Streamlit controls used a deprecated full-width setting**  
   Fix: controls now use the current stretch-width setting to avoid future compatibility failures.

6. **Upload formats were not easy to discover**  
   Fix: every engagement now includes a Download Upload Templates panel containing Excel and CSV RCM templates, an evidence index, an observation register, and an engagement-letter example.

7. **Visual hierarchy was inconsistent**  
   Fix: the application now uses the supplied prototype's navy navigation, blue active state, restrained gold accents, consistent cards, inputs, metrics, borders, and spacing.

8. **Access-governance events lacked structured accountability data**  
   Fix: audit records now include actor/target roles, target name, category, applied RBAC rule, state transitions, metadata, network origin, and downloadable forensic JSON.

9. **Legacy audit records had no integrity chain**  
   Fix: a backward-compatible migration adds SHA-256 evidence hashes and chains every record to its predecessor. Existing records are safely backfilled at startup.

10. **Audit-team deletion could leave unclear allocation state**  
    Fix: the confirmed delete workflow removes team membership links and detaches the team from allocations while preserving engagement and individual auditor records, then logs the full prior and resulting state.

11. **Laptop screens could show an oversized layout and the first row beneath the Streamlit toolbar**  
    Fix: added responsive laptop breakpoints, a narrower compact sidebar, toolbar-safe top spacing, denser cards and controls, horizontally scrollable tabs, reduced chart heights, and low-height sidebar behavior.

12. **No controlled deletion workflow existed for users, clients, or engagements**  
    Fix: Managers can delete Team Member accounts, engagements, clients, and teams; Admins can delete Manager accounts. Exact User ID, engagement code, or client name confirmation is required.

13. **Database deletion and evidence-file deletion were previously inseparable**  
    Fix: engagement and client confirmation dialogs now ask separately whether local evidence, engagement letters, RCM storage, consolidated folders, and export ZIP files should be permanently removed. All filesystem targets are restricted to `AuditVault_Data`.

## Tests performed

- Python syntax compilation for the application, authentication, database, models, utilities, and RCM importer.
- RCM CSV parse: passed with 5 sample rows.
- Styled RCM Excel parse: passed with 3 sample rows.
- Invalid RCM missing-column rejection: passed with a clear validation message.
- Database write/flush test for an imported RCM row: passed; the test transaction was rolled back and left no sample record.
- Streamlit automated UI smoke tests: Manager Engagements, Team Member Engagements, Admin Team Management, and Admin Audit Trail all rendered without application exceptions; Manager registration exposes only the Team Member role.
- Access-control ledger check: executive metrics, governance rules, filters, forensic event inspector, and compliance CSV export rendered successfully.
- SHA-256 audit-chain verification: all seeded and existing audit records passed predecessor-link and payload-hash verification.
- Permission/UI check: no Export IDR control is present; five template downloads are available in the engagement workspace.
- Live server health check: HTTP 200 and `ok` response.
- Live visual check: login, Manager dashboard, engagement selector, RCM workspace, and template download panel displayed correctly.
- Responsive visual check: the Manager dashboard rendered cleanly at a 1280 × 529 browser viewport with the sidebar, four KPI cards, and both chart panels fitting horizontally; no browser console errors were reported.
- Role-based deletion UI checks: Manager engagement/client deletion controls, Manager Team Member deletion list, and Admin Manager deletion list rendered with the correct restrictions.
- Isolated clean-release deletion test: engagement database deletion passed; client deletion and linked-engagement cascade passed; deleted-account authentication blocking passed. This test used an extracted temporary ZIP and did not alter the working database.

## Test note

The Streamlit test runner emitted Windows temporary-directory cleanup and bare-mode context warnings after the tests completed. These are test-environment messages; all nine application test cases passed.
