# AuditFlow – Internal Audit Lifecycle Management System

## 1. Project Overview
AuditFlow is a web-based internal audit lifecycle management prototype designed for Chartered Accountants and internal audit teams.

It manages an internal audit assignment from client creation and engagement planning through fieldwork, reporting, management action tracking and closure.

## 2. Business Problem
Internal audit information is often maintained across spreadsheets, emails, shared folders and follow-up messages. This results in:

- Missing or delayed audit evidence
- Difficulty tracking data requirements
- Disconnected audit clarifications
- Inconsistent observation drafting
- Poor management action tracking
- Lack of visibility over overdue items and closure status

AuditFlow brings these activities into one structured workflow.

## 3. Target Users

- Internal Auditor
- Audit Manager
- Auditee / Process Owner

## 4. Modules Implemented

- Client Master
- Audit Engagements
- Scope and Audit Programme
- Testing Procedures
- Data Requirements
- Evidence Review
- Audit Clarifications
- Audit Observations
- Management Responses
- Management Actions
- Final Reporting
- Closure Tracking
- Activity Log
- Dashboard

## 5. Internal Audit Lifecycle

Client
→ Engagement
→ Scope
→ Testing Procedure
→ Data Requirement
→ Evidence
→ Clarification
→ Observation
→ Management Response
→ Management Action
→ Final Reporting
→ Closure

## 6. Key Features

- Structured client and engagement management
- Controlled audit lifecycle status transitions
- Scope and testing-procedure documentation
- Data requirement and evidence tracking
- Clarification-response workflow
- Clarification-to-observation conversion
- Impact and likelihood-based risk classification
- Management response and action tracking
- Due-date and overdue monitoring
- Append-only closure updates
- Final report line-item selection and preview
- Role-based interface controls
- Activity trail
- Live dashboard metrics

## 7. Technology Used

- React
- TypeScript
- Lovable
- Local mock service layer
- React Query
- Reusable component architecture

## 8. Application Architecture

The present capstone uses a local mock service layer.

Future deployment architecture:

AuditFlow User Interface
→ Google Apps Script API
→ Google Sheets for structured records
→ Google Drive for audit evidence
→ Google Docs for report generation
→ Gmail for reminders

## 9. Demonstration Scenario

Client:
ABC Manufacturing Private Limited

Engagement:
Inventory and Job-Work Internal Audit – Q1 FY 2026-27

The demonstration includes:

- Scope items
- Audit procedures
- Data requirements
- Evidence records
- Audit clarifications
- Audit observations
- Management responses
- Management actions
- Final reporting
- Closure updates

All data used in the application is synthetic.

## 10. Role Summary

### Auditor
Creates scope, procedures, requirements, clarifications and observations and performs evidence review.

### Audit Manager
Reviews and finalises observations, approves risk overrides, finalises reports and closes actions.

### Auditee / Process Owner
Submits evidence, clarification responses, management responses and closure updates.

## 11. How to Run the Project

1. Install Node.js.
2. Clone or download the repository.
3. Open the project folder.
4. Install dependencies:

   npm install

5. Start the development server:

   npm run dev

6. Open the local URL shown in the terminal.

## 12. Professional Safeguards

- Risk ratings remain subject to auditor judgement.
- Reporting decisions remain with the auditor.
- Management responses do not automatically override audit conclusions.
- Closure requires auditor verification.
- All demonstration data is synthetic.
- The application does not upload client data to an AI service.

## 13. Current Limitations

- Local mock data only
- No production database
- No real authentication
- No Google Drive integration
- No actual document storage
- No email reminders
- No Google Sheets integration
- No PDF or Word report export
- Role controls are front-end demonstration controls only

## 14. Future Enhancements

- Google Sheets backend
- Google Drive evidence storage
- Google Apps Script workflow automation
- Email reminders
- User authentication
- Access control by client and engagement
- Report export to Google Docs, Word or PDF
- File-version management
- Secure production audit trail

## 15. Disclaimer

This project is a capstone prototype developed for educational purposes. It is not a production-ready audit-management system.