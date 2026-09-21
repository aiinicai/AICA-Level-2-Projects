# Client Connect Hub

KGMC CSSP — Client Self Service Portal

AICA Level 2 — Phase 1 MVP Full-Stack Web Application

You are acting as a senior product architect, UI/UX designer, and full-stack software engineer.

I want you to build a complete, functional, production-quality full-stack web application called:

KGMC CSSP

Client Self Service Portal

This is an AICA Level 2 project developed for a Chartered Accountancy / Financial Advisory firm.

I will provide a UI reference image along with this prompt. Use that image as the primary visual reference for the overall look, layout, spacing, dashboard structure, navigation style, cards, tables, typography hierarchy, and professional SaaS aesthetic.

Do not merely create a static UI prototype. Build a functioning end-to-end application with frontend, backend, database, authentication, authorization, business logic, file handling, notifications, audit trail, dashboards, search, filters, and reports.

1. PRODUCT OBJECTIVE

KGMC CSSP solves a common problem in Chartered Accountancy firms.

CA firms have multiple clients and multiple team members. Clients regularly communicate with the CA firm for requests such as:

Provide my ITR copy

Provide GST return copy

Confirm whether GST return has been filed

Provide PAN card

Provide previous years' audit reports

Provide financial statements

Clarify tax matters

Ask accounting questions

Ask compliance-related questions

Request certificates

Request previously submitted documents

At the same time, the CA firm regularly needs information and documents from clients:

Bank statements

Sales data

Purchase data

GST data

TDS data

Payroll information

Invoices

Agreements

Financial information

Audit schedules

Supporting documents

Currently this communication is often handled through WhatsApp, email, phone calls, Excel sheets and informal follow-ups.

This creates:

Missed queries

Unclear ownership

Delayed responses

No central communication history

Difficult follow-up

Poor visibility for Partners

Poor workload visibility for Managers

Repeated document requests

No structured SLA monitoring

Difficulty identifying overdue matters

Lack of audit trail

KGMC CSSP should centralize this entire communication workflow.

2. CORE VALUE PROPOSITION

The application should provide:

Visibility

Partners and Managers can see what is happening across clients and team members.

Accountability

Every query/request has an owner, priority, status and due date.

Traceability

Every communication, status change, assignment and document upload is recorded.

The core product philosophy is:

ONE PLATFORM
ONE OWNER
ONE STATUS
ONE SLA
ONE AUDIT TRAIL

3. IMPORTANT MVP SCOPE

This is the Phase 1 AICA Level 2 MVP.

Build ONLY the following 19 core features:

Authentication / Login

Role-Based Access Control

Client Management

User Management

Query Creation

Query Assignment

Query Priority

SLA / Due Date

Two-Way Communication

File Upload / Attachments

@Mention

Query Status Workflow

Partner Dashboard

Manager Dashboard

Client Dashboard

In-App Notifications

Search and Filters

Audit Trail

Reports

Do NOT implement the following in Phase 1:

WhatsApp integration

Email integration

OCR

AI

Tally integration

Zoho integration

GST API integration

Income Tax API integration

Calendar integration

SMS

External notification services

Payment gateway

Complex document OCR

AI chatbot

AI-generated responses

These will be considered Phase 2 / Capstone / Future Scope.

However, design the architecture cleanly so these capabilities can be added later without rebuilding the application.

4. USER ROLES

Create the following six roles.

INTERNAL USERS

1. Super Admin

Can:

Create/edit/deactivate users

Create/edit/deactivate clients

Manage roles

Assign Partner to client

Assign Manager to client

Manage departments

Manage query categories

Configure SLA rules

View all queries

View all requests

View reports

View audit logs

2. Partner

Can:

View all assigned clients

View all queries for assigned clients

View all requests

View team performance

View dashboards

View overdue queries

View high-priority queries

View matters requiring Partner attention

Respond to queries

Add internal notes

Mention team members

Resolve/escalate queries

3. Manager

Can:

View assigned clients

View team queries

Assign/reassign queries

Monitor SLA

Monitor overdue queries

Respond to queries

Add internal notes

Mention Partner/team members

Escalate matters

View team performance

4. Team Member

Can:

View assigned queries

View assigned requests

Respond to clients

Upload documents

Add internal notes

Mention Manager/Partner

Change permitted statuses

Resolve queries

View relevant client information

EXTERNAL USERS

5. Client Admin

Can:

View their organization

View organization queries

Raise queries

Respond to queries

Upload documents

View requests from KGMC

Manage permitted client users

View notifications

Close/confirm resolved queries

6. Client User

Can:

Raise queries

View their permitted queries

Respond

Upload documents

Respond to information requests

View notifications

Client users must NEVER be able to see:

Other clients

Internal notes

Internal staff discussions

Other clients' data

Internal performance data

Partner dashboards

Manager dashboards

5. MULTI-TENANT / DATA ISOLATION

The application must maintain strict data isolation.

A client user must only be able to access data belonging to their client organization.

Internal KGMC users can access data according to their role and assigned clients.

Never expose another client's:

Queries

Requests

Documents

Users

Messages

Reports

Implement authorization on the backend/database level, not merely by hiding UI elements.

6. MAIN APPLICATION NAVIGATION

Use a professional left sidebar similar to the provided UI reference.

Main navigation:

Dashboard

Queries

Requests

Clients

Documents

Reports

Notifications

Users

Settings

Not every role should see every menu item.

For example:

Client users should see:

Dashboard

My Queries

My Requests

My Documents

Notifications

Profile

Partner should see:

Dashboard

Queries

Requests

Clients

Documents

Reports

Notifications

Super Admin should see everything.

7. BRANDING

Application name:

KGMC CSSP

Full name:

Client Self Service Portal

Use a premium, modern professional consulting/SaaS visual language.

The UI reference image provided with this prompt should guide the design.

Design characteristics:

Professional

Minimal

Clean

Premium

Corporate

Easy to navigate

High information density without looking cluttered

Strong visual hierarchy

Rounded cards

Clean tables

Status badges

Priority indicators

Professional dashboard charts

Use the KGMC CSSP brand identity consistently throughout the application.

Do not make the interface look like a generic student CRUD project.

It should look like a genuine B2B SaaS product that a professional CA firm could use.

8. AUTHENTICATION

Create a proper authentication system.

Required:

Login

Logout

Session management

Password hashing

Protected routes

Role-based authorization

Password reset capability if supported by the chosen authentication framework

The application must redirect users to the correct dashboard based on their role.

9. CLIENT MASTER

Create a Client Management module.

Client fields:

Client ID

Legal Name

Display Name

Entity Type

PAN

GSTIN

CIN

Industry

Registered Address

Contact Email

Contact Number

Partner

Manager

Status

Onboarding Date

Created Date

Client statuses:

Active

Inactive

Provide:

Add Client

Edit Client

View Client

Search Client

Filter Client

Deactivate Client

10. CLIENT USERS

Each client can have multiple users.

Example:

ABC Pvt Ltd

CFO — Client Admin

Finance Manager — Client User

Accounts Executive — Client User

Client Admin can manage permitted client users.

Each user must be linked to exactly one client organization unless they are internal KGMC users.

11. QUERY MANAGEMENT

This is the primary module.

A Client should be able to click:

+ New Query

Create a query with:

Query ID — automatically generated

Client — automatically populated

Category

Subject

Description

Priority

Assigned To

Attachment

Created Date

Due Date

Status

Example:

Query ID:

CSSP-Q-000125

Client:

ABC Pvt Ltd

Category:

Income Tax

Subject:

ITR Copy Required

Description:

"Please provide ITR acknowledgement and computation for FY 2025-26."

Priority:

High

12. QUERY CATEGORIES

Create these default categories:

GST

Income Tax

TDS

Accounting

Audit

ROC / Companies Act

Payroll

Finance

FEMA / RBI

Other

Allow Super Admin to manage categories later.

13. PRIORITY

Three priority levels:

HIGH

Red indicator

MEDIUM

Amber/orange indicator

LOW

Green indicator

Priority must influence SLA calculation.

14. QUERY STATUS WORKFLOW

Implement the following controlled workflow:

NEW
↓
ASSIGNED
↓
IN PROGRESS
↓
AWAITING CLIENT
↓
IN PROGRESS
↓
RESOLVED
↓
CLOSED

Do not allow arbitrary status transitions.

A query marked RESOLVED should not automatically become CLOSED.

The client should be able to confirm that the issue is resolved.

If the client rejects the resolution, allow the query to return to IN PROGRESS.

15. QUERY CONVERSATION

Every query should have a conversation thread.

Example:

CLIENT:

"Please provide ITR copy for FY 2025-26."

TEAM MEMBER:

"Sure. We are arranging the same."

TEAM MEMBER:

"Please find attached the ITR acknowledgement."

CLIENT:

"Thank you. Received."

The conversation should show:

User name

Role

Timestamp

Message

Attachments

Make it visually similar to a professional business communication thread.

16. INTERNAL NOTES

Internal notes are extremely important.

A KGMC internal user should be able to add:

Internal Note

Example:

"@Mohit – Please confirm whether this expenditure is allowable."

Internal notes must NEVER be visible to Client users.

Clearly visually differentiate:

Client-visible messages

Internal notes

17. @MENTION

Allow internal users to mention other internal users.

Example:

@Partner

@Manager

@Team Member

When a user is mentioned:

Create a notification

Highlight the mention

Show "Attention Required" where appropriate

Example:

"@Mohit – Please review this query."

Partner dashboard should show:

Partner Attention Required: 7

18. CA FIRM → CLIENT REQUESTS

This is a separate but equally important module.

KGMC users should be able to create:

Information / Document Request

Example:

Request ID:

CSSP-R-000452

Client:

ABC Pvt Ltd

Request:

"Please upload bank statement for April–September 2026."

Priority:

Medium

Due Date:

20 September 2026

The client should receive an in-app notification.

19. REQUEST WORKFLOW

Use:

REQUESTED
↓
CLIENT UPLOADED
↓
UNDER REVIEW
↓
ACCEPTED

If the document is incorrect:

UNDER REVIEW
↓
REVISION REQUIRED
↓
CLIENT UPLOADED

Allow KGMC staff to add comments explaining what revision is required.

20. FILE UPLOADS

Allow attachments for:

PDF

XLS

XLSX

DOC

DOCX

JPG

JPEG

PNG

Store:

File name

File size

Uploaded by

Upload date

Related query/request

Version

File URL/path

Provide:

Upload

Download

Preview where technically feasible

Delete according to permission

Implement secure access control for files.

A client must never be able to access a file belonging to another client.

21. SLA ENGINE

Implement basic SLA logic.

Default SLA:

HIGH:
4 working hours

MEDIUM:
1 working day

LOW:
3 working days

When a query is created, automatically calculate the due date/time.

Example:

Created:

15 September 2026 — 10:00 AM

Priority:

HIGH

SLA:

4 working hours

Due:

15 September 2026 — 2:00 PM

Display SLA status:

On Track

Due Soon

Overdue

Use appropriate visual indicators.

Do not count weekends if the business-calendar implementation can reasonably support this.

Keep the initial implementation simple and configurable.

22. OVERDUE LOGIC

When current time exceeds the due time and the query is not closed/resolved according to the SLA rules:

Mark:

OVERDUE

Show:

"Overdue by 2h 14m"

Overdue queries should appear prominently in:

Partner dashboard

Manager dashboard

Team Member dashboard

according to permissions.

23. IN-APP NOTIFICATIONS

Build an in-app notification centre.

Notifications should be generated for events such as:

New query assigned

Query reassigned

User mentioned

New client request

Client uploaded document

Query resolved

Query reopened

Query overdue

Request approaching due date

Notification fields:

Notification ID

Recipient

Notification type

Message

Related entity

Read/unread

Created date

Provide:

Mark as read

and

Mark all as read

24. PARTNER DASHBOARD

The Partner dashboard is the most important management screen.

Use the provided UI image as the primary design reference.

Show KPI cards:

Open Queries

87

Overdue

9

Awaiting Client

23

Total Clients

125

These numbers should be dynamically calculated from the database in the actual application.

Do not hardcode these values in the final application.

25. PARTNER DASHBOARD ANALYTICS

Include:

Queries by Status

New

In Progress

Awaiting Client

Resolved

Closed

Use a donut/pie chart.

Queries by Category

GST

Income Tax

Audit

Accounting

ROC

TDS

Others

Use a bar chart.

Recent Queries

Show:

Query ID

Client

Subject

Priority

Status

Assigned To

Updated On

My To-Dos

Examples:

Queries requiring attention

Overdue queries

Clients awaiting response

Team members needing guidance

Recent Notifications

Show the latest notifications.

Client Engagement

Show:

Active clients

Query count

Top clients by query volume

26. MANAGER DASHBOARD

Manager dashboard should focus on team execution.

KPI cards:

Open Queries

Overdue

Due Today

Awaiting Client

Partner Attention

Team workload table:

Team Member | Open | Overdue | High Priority

Allow Manager to:

Reassign

Escalate

Review

Filter

27. TEAM MEMBER DASHBOARD

Show:

My Open Queries

Due Today

Overdue

Awaiting Client

Partner Attention

Primary focus should be the team member's personal work queue.

28. CLIENT DASHBOARD

Client dashboard must be much simpler.

Show:

My Queries

Open

In Progress

Awaiting Me

Resolved

Closed

My Requests

Pending

Uploaded

Under Review

Accepted

Revision Required

Recent Notifications

Quick Actions

+ New Query

+ Upload Requested Document

The client should immediately understand what requires their attention.

29. SEARCH

Implement application-level search.

Search should be able to find relevant records according to permissions.

Search examples:

"ITR"

"ABC"

"GST Return"

"CSSP-Q-00125"

"Audit Report"

Never return records that the logged-in user is not authorized to access.

30. FILTERS

Queries should support:

Client

Category

Priority

Status

Assigned To

Date range

SLA status

Requests should support:

Client

Status

Priority

Assigned To

Due date

31. AUDIT TRAIL

Create a proper audit log.

Record important actions such as:

Login

Query created

Query assigned

Query reassigned

Priority changed

Status changed

Message added

Internal note added

User mentioned

Attachment uploaded

Query resolved

Query reopened

Query closed

Request created

Document uploaded

Request accepted

Each audit event should contain:

User

Action

Entity

Entity ID

Timestamp

Relevant details

This information should be accessible only to authorized internal users.

32. REPORTS

Create a Reports section.

Minimum reports:

1. Query Summary Report

2. Client-wise Query Report

3. Team Performance Report

4. SLA Performance Report

Allow filtering by:

Date

Client

Team member

Category

Priority

Status

Provide CSV/Excel export if supported.

33. DASHBOARD DATA MUST BE REAL

This is critical.

Do not create fake static dashboard numbers.

All:

KPI cards

charts

tables

query counts

overdue counts

client counts

team performance

must be calculated from actual database records.

For development/demo purposes, create realistic seed/demo data.

Clearly separate demo seed data from the application logic.

34. DATABASE DESIGN

Use a relational database.

Recommended:

PostgreSQL

Core entities should include at minimum:

users

roles

clients

client_users

departments

query_categories

queries

query_assignments

query_messages

query_mentions

requests

request_messages

attachments

notifications

sla_rules

audit_logs

Create proper:

Primary keys

Foreign keys

Indexes

Timestamps

Status fields

Created_by / updated_by fields where appropriate

Use UUIDs or another secure identifier strategy rather than exposing sequential database IDs unnecessarily.

35. SECURITY REQUIREMENTS

Implement proper security practices.

At minimum:

Authentication

Authorization

Role-based access control

Client-level data isolation

Secure password handling

Protected API endpoints

Input validation

File type validation

File size validation

Secure file access

Server-side permission checks

Audit logging

Do not rely only on frontend restrictions for security.

36. RESPONSIVE DESIGN

The primary application is a desktop web application because CA firms will primarily use it on computers.

However, make the UI responsive enough for:

Laptop

Desktop

Tablet

Mobile browser

The Partner/Manager dashboard should remain usable on smaller screens.

37. UI / UX REQUIREMENTS

Use the supplied UI reference image.

The visual direction should be:

Premium SaaS

Professional CA/consulting environment

Clean

Modern

Minimal

Data-driven

Easy to scan

Use:

Sidebar navigation

Top search

Profile menu

Notification bell

KPI cards

Charts

Data tables

Status badges

Priority badges

Modal/drawer forms

Confirmation dialogs

Empty states

Loading states

Error states

Success notifications/toasts

Maintain consistent spacing, typography, iconography and component design.

38. IMPORTANT UI PRINCIPLE

The application must distinguish clearly between:

ACTION REQUIRED

and

INFORMATION

For example:

RED:

Overdue

AMBER:

Due Soon

BLUE:

Awaiting Client

GREEN:

Resolved

This should allow a Partner or Manager to understand the situation within seconds.

39. QUERY DETAIL PAGE

Create a rich query detail page.

Suggested layout:

LEFT / MAIN:

Query subject

Query information

Conversation

Attachments

RIGHT:

Client

Assigned To

Priority

Status

SLA

Due Date

Created Date

Escalation

Partner Attention

Bottom / activity:

Audit timeline

Include actions such as:

Reply

Add Internal Note

Upload Attachment

Mention User

Change Status

Reassign

Resolve

The UI should be intuitive.

40. CLIENT DETAIL PAGE

For internal users, client detail page should show:

Client profile

Partner

Manager

Client users

Open queries

Requests

Recent activity

Documents

Query statistics

Do not overwhelm the page.

Use tabs where appropriate.

41. EMPTY STATES

Create useful empty states.

Example:

"No open queries"

"All client requests are up to date."

"Great! There are no overdue queries."

Do not leave blank screens.

42. DEMO DATA

Create realistic demo data for the AICA presentation.

Example clients:

ABC Pvt Ltd

XYZ Ltd

LMN Industries

PQR Ltd

DEF Pvt Ltd

Example queries:

ITR Copy Required

GST Return Status

Audit Report FY 2023-24

PAN Card Copy

TDS Certificate

Example team members:

Rahul Sharma

Priya Sharma

Amit Kumar

Neha Verma

Rohit Jain

Create enough records to make dashboards and reports visually meaningful.

43. DEVELOPMENT APPROACH

Do not attempt to build everything in one uncontrolled step.

First establish:

Application architecture

Database schema

Authentication

RBAC

Client management

Query management

Communication

Request management

File uploads

SLA

Notifications

Dashboards

Reports

Audit logs

Testing

After each major module, ensure it is functional before moving to the next.

44. CODE QUALITY

Write maintainable code.

Use:

Reusable components

Reusable UI components

Clear naming conventions

Separation of concerns

Service/business logic separation

Proper error handling

Form validation

Loading states

Empty states

Comments only where useful

Do not duplicate large amounts of code.

45. DO NOT OVERENGINEER

This is an AICA Level 2 MVP.

Do not introduce unnecessary microservices, complex infrastructure or enterprise architecture that is not required.

Keep the application:

Reliable

Maintainable

Understandable

Demonstrable

Scalable enough for future phases

46. FUTURE CAPSTONE — DO NOT BUILD NOW

The following are future enhancements only.

Mention them in the architecture/documentation where appropriate but do not implement them in Phase 1:

Communication integrations

WhatsApp

Email

SMS

Automation

Automated reminders

Escalation engine

Recurring requests

Document intelligence

OCR

Document classification

Document expiry tracking

AI

AI query classification

AI-generated response suggestions

AI document identification

AI priority recommendation

AI summary of long conversations

Accounting/Tax integrations

Tally

Zoho Books

GST

Income Tax

Other APIs

47. CAPSTONE ARCHITECTURE PRINCIPLE

Although the above features are not required now, make sure the application architecture does not prevent future integration.

For example:

Query should be designed so that future fields could include:

Source

AI classification

External reference

Integration ID

Automation status

But do not expose unnecessary future functionality in the MVP UI.

48. FINAL USER EXPERIENCE

The final experience should feel like:

Client

"I know exactly where to ask KGMC for something and I can see what is happening."

Team Member

"I know exactly what work is assigned to me and what is overdue."

Manager

"I know how my team is performing and where intervention is required."

Partner

"I can see the exceptions, bottlenecks and matters requiring my attention without going through hundreds of WhatsApp messages."

This is the fundamental purpose of KGMC CSSP.

49. SUCCESS CRITERIA

The Phase 1 MVP will be considered successful if the following end-to-end workflow works:

Workflow A — Client Query

Client logs in
→ Raises Query
→ Selects Category
→ Selects Priority
→ Query assigned to KGMC team member
→ Team member receives notification
→ Team member responds
→ Team member uploads document if required
→ Team member can mention Manager/Partner
→ Partner can review
→ Query marked Resolved
→ Client confirms
→ Query Closed
→ Entire activity appears in Audit Trail

Workflow B — KGMC Request

KGMC user logs in
→ Selects Client
→ Creates Document/Information Request
→ Assigns request
→ Client receives notification
→ Client uploads document
→ KGMC reviews
→ Document accepted OR revision requested
→ Request completed
→ Full history retained

Workflow C — SLA

Query created
→ SLA calculated
→ Due date displayed
→ Due Soon status
→ If unresolved after deadline → Overdue
→ Dashboard updates
→ Relevant user receives notification
→ Manager/Partner can identify overdue item

50. FINAL DESIGN DIRECTION

Use the attached UI image as the visual benchmark.

Do not reproduce the image as a static page.

Instead, use it to create a complete functioning application with:

Real navigation

Real forms

Real database records

Real authentication

Real permissions

Real workflows

Real dashboards

Real notifications

Real file attachments

Real search

Real reports

Real audit history

Every major button shown in the UI should perform a meaningful action.

Avoid placeholder buttons that do nothing.

51. FIRST IMPLEMENTATION STEP

Before generating the complete application, first analyze this specification and establish the application architecture.

Then implement the application module-by-module.

Start with:

Project structure

Database schema

Authentication

Role-based access

Basic application shell

Sidebar

Top navigation

Dashboard framework

Then progressively implement the remaining modules.

At every stage, preserve the functionality already implemented.

The final result must be a cohesive full-stack application rather than disconnected screens.

52. IMPORTANT FINAL INSTRUCTION

This is a real product concept, not merely an academic CRUD exercise.

Make reasonable product and UX decisions where the specification does not explicitly define a detail, but always prioritize:

Security → Data isolation → Usability → Workflow clarity → Maintainability → Visual quality

The final application should look and behave like a professional B2B SaaS platform designed specifically for Chartered Accountancy and financial advisory firms.

Application name throughout the UI:

KGMC CSSP

Subtitle:

Client Self Service Portal

Tagline:

Simpler Communication. Stronger Relationships.

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://cacssp.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/49aaccce-e832-4d9a-9c52-e94af764172b).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
