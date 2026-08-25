# Consolidated Lovable Prompt — AuditFlow

Build a complete responsive web application named **“AuditFlow – Internal Audit Lifecycle Management System.”**

The application is a capstone prototype for Chartered Accountants and internal audit teams. It must manage an internal audit assignment from client creation and engagement planning through scope definition, testing, evidence review, clarifications, audit observations, management responses, corrective actions, final reporting and closure tracking.

## 1. Build approach

Create the complete application in one project using:

- React
- TypeScript
- TanStack Start / TanStack Router
- Tailwind CSS
- React Query or equivalent query/cache pattern
- Reusable components
- A local in-memory/mock service layer

The application must be fully demonstrable using synthetic data.

### Mandatory restrictions

- Do not use Supabase.
- Do not use Firebase.
- Do not connect any production database.
- Do not add real authentication.
- Do not add a generative AI API.
- Do not add n8n.
- Do not configure a PWA or service worker.
- Do not add Google Drive, Google Sheets or Google Apps Script integration in this version.
- Do not permanently delete audit records.
- Do not place mock data directly inside page components.
- Keep UI, services, mock data and types separated so the mock services can later be replaced with Google Apps Script REST endpoints.

Create `src/config/api.ts` with:

```ts
export const GOOGLE_APPS_SCRIPT_URL = "";
```

Keep it blank and unused.

## 2. Professional design

Use a restrained corporate interface suitable for:

- A Chartered Accountancy firm
- A corporate internal audit department
- Audit managers and process owners

Use:

- Grouped left navigation
- Fixed top header
- Breadcrumbs
- Structured tables
- Search and filters
- Status badges
- Risk badges
- Dialogs/drawers for forms
- Confirmation and reason dialogs
- Responsive desktop and tablet layout
- Clear typography and spacing
- Empty, loading and error states

Do not create a colourful consumer/startup dashboard or marketing website.

## 3. User roles

Provide a temporary role selector in the header, persisted locally:

1. Auditor
2. Audit Manager
3. Auditee / Process Owner

This is front-end demonstration role control only.

### Role principles

**Auditor**
- Creates and edits audit records.
- Performs evidence review.
- Raises and resolves clarifications.
- Drafts observations.
- Assesses management responses and actions.
- Prepares reports.

**Audit Manager**
- Has all Auditor permissions.
- Performs exceptional backward transitions.
- Finalises observations and reports.
- Approves risk overrides and revised action dates.
- Closes/reopens actions and accepts risk.

**Auditee / Process Owner**
- Views assigned audit items.
- Submits evidence metadata.
- Records clarification and management responses.
- Proposes actions and closure updates.
- Cannot alter audit conclusions, risk ratings or final approvals.

Enforce important business rules in both UI and mock service methods.

## 4. Routes and navigation

Create these routes/pages:

- `/` — Dashboard
- `/clients`
- `/clients/:clientId`
- `/engagements`
- `/engagements/:engagementId`
- `/scope-programme`
- `/scope-programme/:scopeId`
- `/data-requirements`
- `/evidence-review`
- `/clarifications`
- `/observations`
- `/management-responses`
- `/management-actions`
- `/final-reporting`
- `/closure-tracking`
- `/activity-log`
- `/settings`

Group navigation logically under Dashboard, Planning, Execution, Resolution and Administration.

## 5. Shared architecture

Create folders broadly as follows:

- `src/components/common`
- `src/components/layout`
- `src/components/clients`
- `src/components/engagements`
- `src/components/fieldwork`
- `src/components/reporting`
- `src/config`
- `src/context`
- `src/data`
- `src/hooks`
- `src/lib`
- `src/pages`
- `src/routes`
- `src/services`
- `src/types`

Create reusable components including:

- PageHeader
- Breadcrumbs
- DataTableShell
- StatusBadge
- RiskBadge
- EmptyState
- LoadingState
- ErrorState
- SearchBox
- FilterPanel
- ConfirmDialog
- ReasonDialog / PromptDialog
- FormSection
- DetailCard
- ActivityTimeline / ActivityTable
- LifecycleIndicator
- MetricCard
- RowActions

Use thin route files and keep page logic in `src/pages`.

## 6. Entity IDs and metadata

Use flat sequential IDs:

- Client: `CLT-####`
- Engagement: `ENG-####`
- Scope: `SCP-####`
- Procedure: `PRC-####`
- Requirement: `REQ-####`
- Evidence: `EVD-####`
- Clarification: `CLR-####`
- Observation: `OBS-####`
- Management Response: `MGR-####`
- Management Action: `ACT-####`
- Closure Update: `CLU-####`
- Report: `RPT-####`

Every entity should contain:

- id/reference
- createdAt
- createdBy
- updatedAt
- updatedBy
- isActive

No permanent delete actions. Use inactive, archived, cancelled, not applicable or dropped states.

## 7. Data relationships

Implement this data model:

```text
Client 1 ── * Engagement
Engagement 1 ── * Scope
Scope 1 ── * Procedure
Procedure 1 ── * Requirement
Requirement 1 ── * Evidence
Clarification links to Engagement and optionally Scope/Procedure/Requirement/Evidence
Clarification 0..1 ── 1 Observation
Observation 1 ── 0..1 Management Response
Observation 1 ── * Management Action
Management Action 1 ── * Closure Update
Engagement 1 ── 0..1 Report
All material actions ── * Activity Log
```

## 8. Client Master

### Client fields

- Client code
- Legal name
- Trade name
- Industry
- Entity type
- Registered office
- Corporate office
- City
- State
- Country
- PIN code
- Primary audit coordinator
- Coordinator designation
- Email
- Mobile number
- Financial year ending
- PAN, optional with validation
- GSTIN, optional with validation
- Remarks
- Status

Client status:

- Active
- Inactive
- Archived

### Client rules

- Auto-generate `CLT-####`.
- New clients are always Active.
- Client code and status are read-only during normal edit.
- Status changes only through Deactivate, Reactivate and Archive actions.
- Deactivate only from Active.
- Reactivate only from Inactive.
- Archived clients remain archived in this MVP.
- Archive is blocked when live engagements exist.
- Every valid action is logged.

### Client pages

Client list columns:

- Code
- Legal name
- Trade name
- Industry
- Entity type
- Registered office
- Coordinator
- Email
- Mobile
- Active engagement count
- Status
- Last updated
- Actions

Client detail tabs:

- Overview
- Contacts
- Locations
- Engagements
- Documents
- Activity

Documents can show a future-stage empty state. Secondary contacts and locations may be stored as nested arrays.

## 9. Audit Engagements

### Engagement fields

- Engagement reference
- Client ID
- Title
- Audit type
- Audit area
- Audit period from/to
- Location
- Audit objective
- Engagement manager
- Audit team
- Process owner
- Audit coordinator
- Planned start date
- Planned completion date
- Reporting due date
- Status
- Lifecycle stage
- Prior status/stage for hold/resume
- Remarks

Statuses:

- Draft
- Planned
- In Progress
- Fieldwork Completed
- Reporting
- Action Tracking
- Closed
- On Hold
- Cancelled

Lifecycle stages:

- Planning
- Fieldwork
- Clarifications
- Reporting
- Action Tracking
- Closure

Map statuses to lifecycle stages and show a reusable lifecycle indicator.

### Controlled engagement transitions

Normal flow:

```text
Draft → Planned → In Progress → Fieldwork Completed → Reporting → Action Tracking → Closed
```

Rules:

- On Hold permitted only from Planned through Action Tracking.
- Resume restores valid stored prior status and stage.
- Cancel allowed from Draft through Action Tracking and On Hold, but not Closed or Cancelled.
- Close allowed only from Action Tracking with closure remarks.
- Reopen allowed only from Closed and returns to Action Tracking.
- Correct Status is Audit Manager only, reason required, and targets only Draft, Planned, In Progress, Fieldwork Completed, Reporting or Action Tracking.
- Do not permit arbitrary status selection in the edit form.
- All transition rules must be validated in the service layer.

### Engagement pages

List and filters for client, type, area, manager, status, stage and date range.

Engagement detail tabs:

1. Overview
2. Scope & Procedures
3. Requirements & Evidence
4. Clarifications
5. Observations
6. Reporting
7. Actions & Closure
8. Activity

Overview must show live linked counts and two progress measures:

- Audit execution completion
- Management action closure completion

## 10. Scope and Audit Programme

### Scope fields

- `SCP-####`
- Engagement ID
- Process
- Sub-process
- Audit objective
- Scope inclusion
- Scope exclusion
- Key risk
- Expected control
- Applicable policy/regulation
- Assigned auditor
- Status
- Remarks

Statuses:

- Draft
- Active
- Completed
- Not Applicable

Scope list and detail page must show nested procedures.

## 11. Testing Procedures

### Procedure fields

- `PRC-####`
- Scope ID
- Risk addressed
- Control objective
- Procedure description
- Population
- Sample size
- Sample-selection method
- Assigned auditor
- Target date
- Test status
- Test conclusion
- Remarks

Statuses:

- Not Started
- In Progress
- Evidence Awaited
- Completed
- Exception Noted
- Not Applicable

Controlled transitions:

- Not Started → In Progress → Evidence Awaited → Completed
- In Progress may move directly to Completed or Exception Noted.
- Evidence Awaited may return to In Progress or move to Completed/Exception Noted.
- Any non-final status may become Not Applicable with reason.
- Completed/Exception Noted may be reopened to In Progress by Audit Manager with reason.
- Test conclusion is editable only in final/exception/not-applicable states.

## 12. Data Requirements

### Requirement fields

- `REQ-####`
- Procedure ID
- Engagement/Scope derived through parent relationships
- Department
- Requirement description
- Format required
- Period covered
- Responsible person
- Date issued
- Due date
- Priority
- Submission status
- Review status
- Auditor remarks
- Auditee remarks
- Not Applicable reason
- Computed completion percentage

Priority:

- Low
- Medium
- High
- Critical

Submission status:

- Draft
- Issued
- Partially Received
- Received
- Not Applicable

Review status:

- Not Reviewed
- Under Review
- Additional Data Required
- Reviewed
- Closed

Use cascading selection Engagement → Scope → Procedure, but store Procedure ID as the primary parent.

### Requirement actions

- Add/View/Edit
- Issue
- Mark Partially Received
- Mark Received
- Start Review
- Request Additional Data
- Mark Reviewed
- Close
- Reopen by Audit Manager
- Mark Not Applicable with reason
- Send Reminder as simulated toast

Completion percentage must be derived, not entered.

## 13. Evidence Review

No actual file storage. Use metadata-only simulated uploads.

### Evidence fields

- `EVD-####`
- Requirement ID
- File name
- Document category
- File type
- File size
- Version number
- Submitted by
- Submission date
- Auditee remarks
- Assigned reviewer
- Review status
- Audit result
- Auditor review remarks
- Reviewed date
- Pending revision flag/version, where relevant

Review status:

- Awaiting Review
- Incomplete
- Incorrect Format
- Additional Data Required
- Satisfactory
- Accepted

Audit result:

- Not Assessed
- No Exception
- Exception Identified
- Further Testing Required

Keep review quality and audit result separate. Accepted evidence may still show an exception.

### Revision workflow

- Request Revision marks the existing evidence as requiring revision and reserves the next version.
- A pending revision has no submission date and does not count as received evidence.
- Auditee uses a separate Submit Revised Evidence action.
- Submission creates a new version record with submission metadata and preserves prior history.
- Show version history clearly.

### Evidence actions

- Add Evidence
- View
- Preview/Download simulated
- Review
- Request Revision
- Submit Revised Evidence
- Mark Satisfactory
- Accept
- Raise Clarification

Update parent Requirement statuses according to evidence activity.

## 14. Audit Clarifications

### Clarification fields

- `CLR-####`
- Engagement ID
- Optional Scope/Procedure/Requirement/Evidence IDs
- Subject
- Clarification raised
- Raised by
- Date raised
- Response due date
- Respondent
- Auditee response
- Response date
- Auditor conclusion
- Status
- Linked Observation reference

Statuses:

- Draft
- Open
- Response Received
- Further Clarification Required
- Resolved
- Converted to Observation
- Closed Without Observation

Workflow:

```text
Draft → Open → Response Received → Resolved
Response Received → Further Clarification Required → Response Received
Resolved → Converted to Observation
Resolved → Closed Without Observation
```

Rules:

- Open requires respondent and due date.
- Record response requires response text/date.
- Resolve requires auditor conclusion.
- Converted clarification becomes read-only.

### Convert to Observation

Create or complete a reserved `OBS-####` draft and carry forward:

- Engagement, Scope, Procedure, Requirement, Evidence and Clarification links
- Subject as title
- Clarification text and response as draft condition
- Auditor conclusion as preliminary note

Do not create duplicates if a reserved observation already exists.

## 15. Audit Observations

Keep three independent axes:

1. Observation workflow status
2. Reporting decision
3. Derived implementation roll-up

### Observation fields

- `OBS-####`
- Engagement ID
- Process
- Title
- Optional Scope/Procedure/Requirement/Evidence/Clarification IDs
- Condition
- Criteria
- Root cause
- Risk or implication
- Financial impact
- Recommendation
- Supporting evidence
- Impact rating
- Likelihood rating
- Calculated risk rating
- Final risk rating
- Risk override reason
- Workflow status
- Reporting decision
- Derived implementation roll-up
- Prepared by
- Reviewed by
- Review remarks
- Finalisation remarks
- Drop reason

Workflow statuses:

- Draft
- Under Auditor Review
- Issued for Management Response
- Awaiting Finalisation
- Finalised
- Included in Report
- Reported
- Dropped

Reporting decisions:

- Include in Final Report
- Merge with Another Observation
- Advisory Point
- Verbal Discussion
- Working Papers Only
- Drop after Explanation

### Risk matrix

Impact and likelihood use Low/Medium/High.

Matrix:

- Low + Low = Low
- Low + Medium = Low
- Low + High = Medium
- Medium + Low = Low
- Medium + Medium = Medium
- Medium + High = High
- High + Low = Medium
- High + Medium = High
- High + High = High

Final risk defaults to calculated risk. Override requires mandatory reason.

### Observation workflow

- Draft → Under Auditor Review
- Under Auditor Review → Draft with comments, or Issued for Management Response
- Issued for Management Response → Awaiting Finalisation when linked response is accepted and required actions are agreed
- Awaiting Finalisation → Finalised with confirmation
- Finalised → Included in Report or Dropped
- Included in Report → Reported when report finalises
- Audit Manager may drop pre-final observations with reason
- Finalised wording is locked unless Audit Manager reopens with reason

Derived implementation roll-up values:

- No Action Created
- Awaiting Management Response
- Open
- Partly Implemented
- Implemented
- Risk Accepted
- Closed

Never allow manual editing of the roll-up.

## 16. Management Responses

### Fields

- `MGR-####`
- Observation ID
- Management acceptance
- Management response
- Cause acknowledged
- Proposed corrective approach
- Management remarks
- Respondent
- Respondent designation
- Response date
- Auditor assessment
- Status
- Version
- Append-only response history

Management acceptance:

- Accepted
- Partially Accepted
- Not Accepted
- Under Discussion

Status:

- Awaiting Response
- Response Received
- Revision Requested
- Accepted by Auditor

Workflow:

```text
Awaiting Response → Response Received → Accepted by Auditor
Response Received → Revision Requested → Response Received
```

Preserve prior response versions.

## 17. Management Actions

One observation may have multiple actions.

### Fields

- `ACT-####`
- Observation ID
- Action title
- Description
- Action type
- Action owner
- Owner designation
- Department
- Original target date
- Revised target date
- Reason for revised date
- Priority
- Auditor assessment
- Agreement status
- Derived implementation status
- Escalated flag/date/remarks

Action types:

- Corrective
- Preventive
- Compensating Control
- Process Improvement

Agreement status:

- Draft
- Proposed by Management
- Revision Requested
- Agreed by Auditor
- Rejected

Workflow:

```text
Draft → Proposed by Management → Agreed by Auditor
Proposed by Management → Revision Requested → Proposed by Management
```

Implementation status is derived from latest Closure Update:

- Pending
- Update Received
- Partly Implemented
- Implemented
- Risk Accepted
- Closed

### Due status

Compute from revised target date, otherwise original target date:

- Not Due
- Due Soon — within 7 days
- Overdue

Never store Due Status as editable data.

## 18. Closure Tracking

Closure Updates are append-only.

### Closure Update fields

- `CLU-####`
- Action ID
- Update date
- Updated by
- Management update
- Closure evidence metadata
- Auditor verification
- Auditor verification date
- Implementation status
- Closure conclusion
- Reopen reason
- Risk acceptance note
- Escalation note

Workflow:

```text
Pending → Update Received → Partly Implemented → Implemented → Closed
Any active status → Risk Accepted → Closed
Implemented or Closed → Update Received through Reopen
```

Rules:

- Management update requires text/date.
- Closure evidence is metadata only.
- Partly Implemented requires auditor verification.
- Implemented requires verification and evidence metadata.
- Close allowed only from Implemented or Risk Accepted, Audit Manager only.
- Risk Accepted requires sign-off note and responsible person.
- Reopen requires reason and creates a new update.
- Escalate is available when Overdue and requires remarks.

## 19. Final Reporting

### Report fields

- `RPT-####`
- Engagement ID
- Title
- Report period
- Addressee
- Issue date
- Executive summary
- Overall conclusion
- Status
- Included Observation IDs in presentation order
- Prepared by
- Reviewed by
- Approved by
- Reason for reporting without accepted response

Report status:

- Draft
- Under Review
- Finalised

Eligible observations:

- Finalised or Included in Report
- Reporting decision is Include in Final Report or Advisory Point

Allow:

- Create report
- Select/exclude line items
- Reorder with simple up/down controls
- Add executive summary and conclusion
- Mark Under Review
- Finalise
- Print-style preview

Preview each observation with:

- Reference/title/risk
- Condition
- Criteria
- Root cause
- Risk/implication
- Recommendation
- Management response
- Management actions
- Owners and target dates

Report finalisation requires at least one observation, completed report header fields, review/approval names and accepted management response unless manager records a reason. On finalisation, included observations become Reported.

## 20. Activity Log

Create an append-only activity log with:

- Timestamp
- User
- Role
- Client
- Engagement
- Module
- Record reference
- Action
- Previous status
- New status
- Remarks

Log all material create/update/status actions across Clients, Engagements, Scope, Procedures, Requirements, Evidence, Clarifications, Observations, Responses, Actions, Closure and Reports.

Provide filters by date, user, engagement, module and action.

## 21. Dashboard

Use computed mock-service data, not hardcoded numbers.

Cards:

- Active engagements
- Data requirements pending
- Evidence awaiting review
- Open clarifications
- Draft observations
- High-risk observations
- Management responses pending
- Overdue management actions
- Actions closed

Also show:

- Engagement-stage summary
- Pending items by department
- Risk-rating distribution
- Upcoming due dates
- Recent activity
- Audit execution completion
- Management action closure completion

Do not add a new chart library. Reuse existing components, cards, progress bars and simple tables.

### Audit execution completion

Calculate from:

- Completed/Not Applicable Procedures
- Closed/Not Applicable Requirements
- Resolved/Converted/Closed Clarifications
- Finalised/Included/Reported/Dropped Observations

### Management action closure completion

Agreed actions with latest status Closed or Risk Accepted divided by total agreed actions.

## 22. Settings and project information

Provide master-data screens or sections for:

- Industries
- Entity types
- Audit areas
- Departments
- Document categories
- Risk ratings
- Priorities
- Locations
- Users and roles

Also include an About/Project Information section:

**Project:** AuditFlow – Internal Audit Lifecycle Management System

**Purpose:** Manage internal audits from planning through fieldwork, reporting and closure.

**Technology:** React, TypeScript, TanStack Start, Tailwind CSS, local mock services, future Google Workspace integration.

**Safeguards:** Auditor judgement remains mandatory; all demo data is synthetic; production deployment requires authentication, secure storage, access controls, backup, retention and confidentiality controls.

**Current limitations:** No production backend, real file storage, authentication, email automation, Google Workspace integration or PDF/Word export.

## 23. Synthetic demonstration data

Create realistic, internally consistent seed data.

### Clients

1. `CLT-0001` — ABC Manufacturing Private Limited, Auto Components, Chennai, Active
2. `CLT-0002` — Delta Engineering Limited, Industrial Engineering, Coimbatore, Active
3. One Inactive client

### Engagements

Primary engagement:

- `ENG-0001`
- ABC Manufacturing Private Limited
- Inventory and Job-Work Internal Audit – Q1 FY 2026-27
- Audit period: 1 April 2026 to 30 June 2026
- Chennai Plant
- Objective: Evaluate inventory controls, job-worker stock accountability, material movement documentation, physical verification and reconciliation procedures
- Manager: E. Radhakrishnan
- Status: In Progress

Also create:

- One Planned engagement
- One Reporting engagement
- One Closed historical engagement

### Scope and procedures for ENG-0001

Scope items:

1. Job-worker stock movement and reconciliation
2. Purchase-to-pay controls
3. Goods receipt and inventory recording
4. Physical verification and inventory differences

Create at least two procedures under each scope.

### Requirements

Create at least eight realistic requirements with varied statuses, including:

- Job-worker-wise stock reconciliation
- Open job-work challan register
- Purchase order and invoice dump
- Delegation of authority matrix
- GRN ageing report
- Gate inward register
- Physical stock-verification report
- Inventory adjustment approval records

### Evidence and clarifications

Create varied evidence versions/statuses/results and at least three clarifications:

1. Job-worker stock reconciliation not furnished
2. Purchase orders created after invoice dates
3. GRN delays exceeding prescribed timeline

### Observations

Create:

1. Job-worker stock reconciliation not completed periodically — High
2. Purchase orders created after supplier invoice date — High
3. Delays in recording goods receipt notes — Medium
4. Physical verification differences not investigated — Medium
5. Minor gaps in document indexing — Low / Advisory Point

Use varied workflow states: Draft, Under Review, Issued, Finalised, Included in Report.

### Responses, actions and closure

Seed:

- Awaiting Response
- Response Received
- Revision Requested
- Accepted responses
- One observation with multiple actions
- One Closed action
- One Implemented action
- One Partly Implemented action
- One Overdue action
- One Due Soon action
- One Risk Accepted action
- Append-only closure history
- One Draft Report with at least two observations

Ensure all dashboard counts are meaningful and relationships are consistent.

## 24. Mock services

Create separate service modules for:

- Clients
- Engagements
- Scope
- Procedures
- Requirements
- Evidence
- Clarifications
- Observations
- Management Responses
- Management Actions
- Closure Updates
- Reports
- Activity Log
- Dashboard aggregation

Services should support appropriate list/get/create/update/status-action/relationship-query methods, simulate a short API delay, enforce business rules and trigger React Query cache invalidation or equivalent refresh.

Do not store data directly in page components.

## 25. Final quality requirements

- All routes work.
- TypeScript typecheck is clean.
- Existing records are linked consistently.
- Role-gated buttons and service validations match.
- Status transitions use controlled actions.
- No permanent deletion.
- No Supabase, Firebase, database, AI API, PWA, n8n or Google integration.
- Dashboard figures are live from mock data.
- The app is ready for a capstone demonstration.

At completion, provide a summary of:

1. Pages and routes created
2. Reusable components
3. Entity types and relationships
4. Service files
5. Status workflows
6. Seed data
7. Simulated features and limitations
8. Confirmation that the typecheck passes
9. Confirmation that prohibited integrations were not added
