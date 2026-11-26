# Demo guide for reviewers (no login or password needed)

**Live app:** https://leaveledger-rust.vercel.app

On the sign-in screen, scroll to **"Just exploring? Try the demo"** and click one of the three buttons. Everything runs on sample data in your browser. Nothing is saved, and a page refresh resets it. You can switch role at any time using the amber "Demo mode" banner at the top.

## 5-minute walkthrough

1. **Demo as Employee (Kavya Iyer)**
   - Open **Timesheet**. The week grid shows Mon-Fri at 8 hours a day. Weekends, holidays and approved leave are locked.
   - Open a draft day and split 8 hours across projects (for example 5 + 3). A day cannot be submitted unless it totals exactly 8 hours.
   - Submit one or more days. They go to the reporting manager.
   - Days older than 14 days are frozen and read-only.
2. **Switch to Manager (Arjun Nair)**
   - Open **Timesheet Approvals**. Approve or reject a submission (a comment is required to reject).
   - Open the leave approvals and approve a pending leave request.
3. **Switch to HR Admin (Priya Sharma)**
   - **Payroll Report:** pick a month and export Excel. Only approved hours are counted.
   - **Projects:** the project master used by the timesheet picker.
   - **Reopen:** only the HR admin can reopen a frozen or approved day.
4. Switch back to Employee to see the effect of your approvals.

## Notes
- Real sign-in (Google, Firebase) is used in production. Demo mode is separate and never touches real data.
- Google Sheets sync is turned off in demo mode.
- A 3-slide overview is in `docs/TimeRecordingSystem_Overview.pptx`.
- To run locally: `npm install --legacy-peer-deps`, then `npm run dev` (http://localhost:3000). The demo works locally with no setup. Real sign-in on localhost needs `localhost` added to Firebase authorized domains.
