# TimeRecordingSystem

> **Reviewers:** see [DEMO_GUIDE.md](DEMO_GUIDE.md) for a 5-minute walkthrough of the live demo (no login needed) and `docs/` for the overview slides.

A web app for **timesheets, leave and attendance** for a professional-services firm. Staff record daily project hours, managers approve them, HR runs a payroll attendance report, and leave is managed in the same place.

Built with React 19, TypeScript, Vite, Tailwind CSS, Firebase Authentication and Cloud Firestore. Deployed on Vercel.

## Try it without logging in

Open the live app and use the **"Try the demo"** buttons on the sign-in page:

**https://leaveledger-rust.vercel.app**

| Button | What you can do |
|---|---|
| Demo as Employee | Enter hours per project by day, save drafts, submit days for approval, apply for leave |
| Demo as Manager | Approve or reject your team's timesheet days and leave requests |
| Demo as HR Admin | Payroll report (Excel download), project list, reopen locked days, leave policy, roster |

You can also switch role from the yellow banner at the top while in the demo.

The demo uses **made-up sample data held in your browser only**. It never connects to the real database, nothing is saved, and a page refresh resets it. Google Sheets sync is switched off in demo mode.

## Features

- **Timesheets:** weekly grid, Monday to Friday, 8 hours per day. Each submitted day must total exactly 8 h, split across projects as the staff member chooses. Holidays come from a holiday list. Approved leave fills in and locks the day.
- **Approval:** single level, routed to the employee's reporting manager. The top partner is approved by the HR admin.
- **Open window:** the last 14 days can be edited; older days are frozen and only an HR admin can reopen them.
- **Payroll report:** Excel download for any date range or month end, with staff-wise and project-wise views (hours, chargeable and non-chargeable, days present, leave by type).
- **Leave:** balances (opening, accrued, availed, closing), date-range and half-day requests, manager approvals, accrual runs and policy settings.
- **Google Sheets sync:** the employee roster and the project list are read from a Google Sheet.

## How it is built

```
src/
  App.tsx                 app shell, navigation, live Firestore listeners
  components/             screens (timesheet grid, approvals, payroll report, roster sync, leave ...)
  lib/
    firebase.ts           Firebase setup, Google sign-in, Sheets permission
    leaveService.ts       leave and roster data operations
    timesheetService.ts   timesheet and project data operations
    timesheetUtils.ts     day classification, 8-hour rule, payroll calculations
    sheetsAndExcel.ts     Google Sheets reading and Excel export
    fsAdapter.ts          routes Firestore calls to the real database, or to the demo store
    demoStore.ts          in-memory stand-in for Firestore (demo mode only)
    demoData.ts           fictional sample organisation for demo mode
firestore.rules           database security rules
firebase-blueprint.json   data model
security_spec.md          security notes
```

Access control is enforced twice: by the screens, and by Firestore security rules (`firestore.rules`) on the server. Employees can read and write only their own records, managers can act on their direct reports, and HR admins have wider access.

## Run it on your computer

Requires Node.js 20 or newer.

```bash
npm install --legacy-peer-deps
npm run dev
```

Open http://localhost:3000 and use the demo buttons. No accounts are needed for the demo.

Real Google sign-in works only for emails on the employee roster, and `localhost` must be listed under Firebase Authentication, Settings, Authorized domains. Sheets sync additionally needs `http://localhost:3000` as an authorized JavaScript origin for the OAuth client in Google Cloud.

## Configuration

`firebase-applet-config.json` holds the Firebase web configuration. A Firebase web API key identifies the project to the browser and is not a secret; access is controlled by the security rules and by the authorized-domains list. No server secrets are stored in this repository.

## Notes for reviewers

- The Firestore database is a named database; the id is set in `src/lib/firebase.ts`.
- The HR admin is identified by a fixed email set in `src/lib/firebase.ts`, plus an admin flag on employee records.
- The Excel payroll report counts **approved** hours only.
