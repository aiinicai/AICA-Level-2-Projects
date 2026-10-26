# Screen map

DPDP Compliance Manager. Page-by-page layout, navigation and what each screen reads and writes.
Companion to `DATA_DICTIONARY.md` (tables), `row_level_security.sql` (who may do what) and `LOVABLE_BUILD_PROMPTS.md` (build order).

## 1. Principles that apply to every screen

- The browser never decides who may do something. It hides buttons the user cannot use, but the database refuses the action regardless. Every screen below lists the rule that enforces it.
- Every screen shows four states: loading, empty (says what to do next), error (says what failed and what to try) and content.
- A **Demo data** banner shows whenever the tenant has `is_demo = true`. The banner cannot be dismissed.
- Status is always text plus a badge, never colour alone.
- "Not Assessed" is shown as its own state. It is never grouped with "Implemented" and every percentage shows its denominator, for example "3 of 8 implemented and verified, 2 not assessed".
- Destructive actions (archive, revoke, reject, reopen) ask for confirmation and, where the database requires one, a reason.
- Nothing says "compliant", "certified" or "guaranteed". Use "assessed as", "gap identified", "evidence verified".
- Legal commencement is shown exactly as stored. Anything other than a "Verified" status carries the label **Requires Verification** next to it.
- No fake buttons. An action that is not built yet is shown disabled with the words "In development".

## 2. Sign-in and workspace choice

| Screen | Route | Who | Purpose |
|---|---|---|---|
| Sign in | `/login` | anyone | Email and password. Link for password reset. No self-service sign-up for client users: they arrive by invitation. |
| Accept invitation | `/invite` | invited user | Set a password, confirm name. The invitation itself is created by an Edge Function (see build prompts) because only the server may use the service-role key. |
| Choose workspace | `/workspaces` | any signed-in user with more than one workspace | Calls `my_tenants()`. Lists each client the user can open, with the user's role there. A firm user also sees "Firm workspace". One workspace only: skip this screen. |
| No access | `/no-access` | signed-in user with no active membership | Plain message: "Your account is not linked to a workspace. Ask your administrator." No data. |

Disabled memberships behave like no membership (`is_active_user`, `status = 'active'`).

## 3. Navigation

Left sidebar with the workspace name and a workspace switcher on top. Items the role cannot use are not shown. Mobile: sidebar becomes a drawer.

**Firm workspace** (firm members): Firm Dashboard, Clients and Engagements, Team and Assignments, Legal Sources, Approved Control Library, Reports, Firm Settings and Audit Events.

**Client workspace** (client members and assigned firm members): Dashboard, Institution Profile, Departments and Systems, Personal-Data Inventory, Applicability, Control Register, Gap Assessment, Corrective Actions, Evidence Register, Review and Approval, Reports, Users and Settings.

Breadcrumb: `Workspace › Section › Record`. Every list has search, filters and pagination (25 rows per page).

## 4. Firm workspace screens

### F1. Firm Dashboard `/firm`
- Shows: engagements by status, assessments awaiting my review, overdue actions across engagements I am assigned to, evidence waiting for verification.
- Reads: `engagements`, `assessments`, `corrective_actions`, `evidence_records` (RLS limits these to assigned engagements). Counts are computed by queries, not stored.
- A firm administrator who holds no assignment sees engagement and client metadata, but zero content counts. Show "Not assigned" instead of 0 so nobody reads it as "no gaps".

### F2. Clients and Engagements `/firm/clients`
- List of tenants of the firm: name, type, status, demo flag, engagement count.
- Actions (firm administrator): New client (`tenants` insert), edit client details (`tenants` update), set status, New engagement (`engagements` insert with scope, period, dates).
- Detail page `/firm/clients/:tenantId`: tabs Overview, Engagements, Client users, Internal notes.
  - Client users tab: list `tenant_memberships`; Invite user opens the invitation form (Edge Function), change role, disable.
  - Internal notes: `engagement_notes` with visibility `firm_only` or `client_visible`. Firm-only notes are never returned to client users.

### F3. Team and Assignments `/firm/team`
- Firm members and their roles; engagement assignments (who works on which engagement, as team member or reviewer).
- Actions (firm administrator): add or remove firm member, assign or revoke engagement assignment.
- Rule shown on screen: "Firm administrators manage who works on a client. They see client records only when assigned."

### F4. Legal Sources `/firm/sources`
- List of sources (global and own-firm), each with its versions. Version detail shows retrieval date, commencement status, verification status, approval state, verifier.
- Actions: add source and version (editor), submit for review, reviewer verifies (checks official text, records verifier) and approves. Approved versions are read-only; a change creates a new version.
- Banner on any version where `is_demo` or verification is outstanding: "Not verified against the official text".

### F5. Approved Control Library `/firm/controls`
- Controls with versions: legal reference, statement, applicability logic, assessment question, required evidence, test procedure, expected result, risk guidance, linked source version.
- Version lifecycle: draft, in review, approved, retired. A control version can only be approved against an approved, verified source version (the database refuses otherwise, unless demo).
- The author cannot approve their own version.

### F6. Reports `/firm/reports`
- All report runs for assigned engagements. Create report from an approved assessment (executive summary, gaps and remediation, evidence register, inventory). See C12 for contents.

### F7. Firm Settings and Audit Events `/firm/settings`
- Firm name. Audit log viewer (read-only, filter by date, actor, entity, tenant). Audit rows cannot be edited or deleted by anyone.

## 5. Client workspace screens

Route prefix `/t/:tenantId`.

### C1. Dashboard `/t/:id`
- Calls `dashboard_metrics(tenant)`. Tiles, each with its denominator:
  - Inventory: activities by status; activities with review overdue; activities flagged children's data or special case.
  - Assessment: items by result (Implemented and verified, Implemented, Partial, Gap, Not applicable, **Not assessed**, Needs legal review). Not assessed is never counted as compliant.
  - Actions: open, blocked, overdue, awaiting review, closed; by risk level.
  - Evidence: verified, submitted, missing, expired.
- Beneath the tiles: "Based on assessment: {title}, period {dates}, version {n}, {approved/draft}". If the assessment used an older control version than the latest approved, show "Control library has newer version".
- Client roles see approved and shared assessments only; draft work is not visible to them.

### C2. Institution Profile `/t/:id/profile`
- Name, type, sector, description, headcount band, primary contact. Edit needs `edit_profile` (client admin, privacy lead; firm team members by assignment).

### C3. Departments and Systems `/t/:id/departments`
- Tabs: Departments (with coordinator), Systems (type, hosting location, owner department, vendor), Vendors (relationship, country, contract status).
- A department coordinator can edit only inventory for their own department. Archive instead of delete.

### C4. Personal-Data Inventory `/t/:id/inventory`
- Table: activity, department, owner, lawful ground, children's data, special-case flags, review date, status. Search, filter by department, status, lawful ground.
- Detail and edit form (sections): Basics, Whose data, Why (purposes), What happens to it (operations, recipients), Lawful ground and rationale, Retention and deletion, Cross-border, Children and special cases, Linked systems, vendors and data categories.
- Lawful ground default "Not yet assessed". The tool never chooses a ground. "Needs legal review" is a valid value.
- Archive needs a reason. Archived records stay visible under the Archived filter.

### C5. Applicability `/t/:id/applicability`
- Guided questions for an assessment (Is the institution a Data Fiduciary? Does it process children's data? Could it be notified as a Significant Data Fiduciary?). Each answer: Applicable, Not applicable, Needs legal review, with rationale. Result is advice for the professional, not a legal conclusion.

### C6. Control Register `/t/:id/controls`
- Read-only view of approved controls (global and the firm's) with version, legal reference, commencement status and verification label. Client roles see approved versions only.

### C7. Gap Assessment `/t/:id/assessments` and `/t/:id/assessments/:aid`
- List: title, period, status (draft, in review, approved), version, reviewer.
- Detail: one row per control version: applicability, result, evidence quality, risk level, notes, recommendation, owner, target date. Items are editable only while the assessment is a draft and only by the firm side (`edit_assessment`).
- Result values: Implemented and verified, Implemented, Partial, Gap, Not applicable, Not assessed. "Implemented and verified" is selectable only when verified evidence is linked (the database enforces it). "Not applicable" requires a rationale.
- Buttons: Submit for review (preparer; a reviewer must be set), Approve or Return (reviewer who is not the preparer), Reopen with reason (reviewer; raises version number).
- Approved assessments are frozen; a snapshot is stored.

### C8. Corrective Actions `/t/:id/actions`
- Table: title, linked item, owner, due date, risk level, status, closure evidence. Filter: overdue, mine, blocked.
- Status flow: open, in progress, blocked, submitted for review, closed, risk accepted. Buttons call `set_action_status`, `close_corrective_action` (firm reviewer, needs verified closure evidence) and `accept_risk` (a client user holding the approve-client right, with a written rationale).
- A "closed" action shows who closed it, when and which evidence.

### C9. Evidence Register `/t/:id/evidence`
- Table: title, category, linked activity/item/action, status (missing, submitted, under review, verified, rejected, expired), valid until, uploader.
- Request evidence (creates a "missing" placeholder with a storage path). Upload: browser uploads to the private bucket at `{tenant_id}/{random uuid}/{file}`, then calls `confirm_evidence_upload`. Download: short-lived signed URL; the screen also calls `log_evidence_access`.
- Verify or reject: firm reviewer only, and never the uploader (`decide_evidence`).
- File rules shown on the upload dialog: PDF, PNG, JPEG, text, CSV, DOCX, XLSX; 25 MB maximum. Virus scanning is not built in (see TEST_PLAN, manual tests).

### C10. Review and Approval `/t/:id/reviews`
- Chronological list of `review_decisions`: subject, version, decision, reviewer, capacity (firm reviewer or client reviewer), comments, time. Read-only. Decisions are recorded by the Approve/Return buttons, not typed here.

### C11. Users and Settings `/t/:id/users`
- Members list with role and status. Invite, change role, disable (client administrator, or firm administrator for that client). Role descriptions beside the dropdown.
- A client administrator cannot give a role the matrix does not allow; the database refuses.

### C12. Reports `/t/:id/reports`
- Report types: Executive summary, Gaps and remediation, Evidence register, Inventory (CSV), Action tracker (CSV).
- Each report header states: client, assessment, period, version, generated by, generated at, status (draft or final), limitations paragraph, denominators. Drafts are visible to the firm only until "Finalize and share" (`finalize_report`).
- Every export calls `log_export` with the row count. CSV contains only the current tenant's rows.
- Fixed footer: "This report records an assessment of the evidence reviewed on the date stated. It is not a certificate of compliance and does not give a legal opinion."

## 6. Screen-to-role summary

Derived from the `role_capabilities` table in `row_level_security.sql`. `✓` = can change, `r` = can read, `own` = own department or assigned items only, `—` = no access. Firm columns apply only to a person assigned to that client's engagement.

| Screen | Client admin | Privacy lead | Dept coordinator | Evidence contributor | Mgmt viewer | Client reviewer | Firm team member | Firm reviewer |
|---|---|---|---|---|---|---|---|---|
| Dashboard and approved reports | r | r | r | — | r | r | r | r |
| Institution profile | ✓ | ✓ | r | — | — | r | ✓ | r |
| Departments, systems, vendors | ✓ | ✓ | r | — | — | r | ✓ | r |
| Inventory | r | ✓ | own | — | — | r | ✓ | r |
| Control register | r | r | r | — | — | r | r | r |
| Gap assessment | r (approved and shared) | r | r | — | r (summary) | r | ✓ prepare | ✓ approve, reopen |
| Corrective actions | r | ✓ | r | own | — | r | ✓ | ✓ close |
| Accept risk | ✓ | — | — | — | — | ✓ | — | — |
| Evidence: view | r | r | r | own | — | r | r | r |
| Evidence: upload | — | ✓ | — | own | — | — | ✓ | — |
| Evidence: verify | — | — | — | — | — | — | — | ✓ |
| Review trail | r | r | r | — | — | r | r | r |
| Users and roles | ✓ | — | — | — | — | — | — | — |
| Audit log | ✓ | — | — | — | — | — | ✓ | ✓ |
| Internal firm notes | — | — | — | — | — | — | ✓ | ✓ |
| Export CSV | ✓ | ✓ | — | — | — | — | ✓ | ✓ |

Two other actors: a **firm administrator** manages clients, engagements, assignments and client users, and sees engagement metadata, but sees no client content unless also assigned. A **platform administrator** manages platform setup and has no automatic access to client content.

Where this table and the database disagree, the database is right and this document must be corrected. Two consequences worth confirming with the practice (see `BUILD_LOG.md`, open decisions): the client administrator can manage people but cannot edit inventory, and evidence is verified only by the firm reviewer.

## 7. Key workflows

1. **Onboard a client.** Firm admin creates tenant and engagement, assigns team member and reviewer, invites the client admin. Client admin invites privacy lead and coordinators.
2. **Build the inventory.** Coordinators and the privacy lead enter activities; status moves draft, active, needs review. Review dates drive "overdue" tiles.
3. **Assess.** Team member creates an assessment for the period, adds applicability answers, adds one item per approved control version, records results and links evidence.
4. **Evidence.** Request, upload, confirm, verify (different person), link to item.
5. **Review.** Preparer submits; reviewer approves or returns with comments; approval freezes the assessment and stores a snapshot; firm decides when to share with the client.
6. **Remediate.** Actions with owners and dates; closure needs verified evidence and a different person to close; accepted risk needs management's written rationale.
7. **Report.** Generate draft, review, finalize and share; export logged.
8. **Reopen.** A reviewer reopens an approved assessment with a reason; version number rises; earlier snapshot is kept.

## 8. Not in this release

AI assistance, automatic legal change monitoring, ERP/HR/LMS integrations, automatic breach reporting, automatic deletion, billing, public portals, mobile app, any automatic legal conclusion or certificate. Email notifications are stored as rows only; sending needs an Edge Function and a provider chosen later.
