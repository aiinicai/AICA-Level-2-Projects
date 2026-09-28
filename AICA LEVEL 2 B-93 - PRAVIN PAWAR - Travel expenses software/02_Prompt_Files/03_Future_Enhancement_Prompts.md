# Prompts for Adding More Features

Each prompt below can be given to an AI coding assistant together with the source folder
`ABC_Travel_Expense_App`. The code is organised so new features plug in easily:
routes are registered with `route(method, path, handler)` in `server.js`, pages with `ROUTES` in
`public/app.js`, rules in `computeExceptions()`, and switches in `settings.features`.

1. **Email / WhatsApp alerts** – "Add SMTP email notifications (configurable in Settings) that send the same messages as `notify()` to the recipient's email id, with a link to the request."
2. **Delegation of authority** – "Allow an approver to delegate approvals to another user for a date range (leave cover). Show 'approved by X on behalf of Y' in the audit trail."
3. **Escalation / SLA reminders** – "If a request waits more than N hours at a stage, remind the approver and escalate to the next level. Show ageing in the queues."
4. **OCR of bills** – "When a bill image is uploaded, extract date, vendor and amount and prefill the expense line."
5. **Corporate card reconciliation** – "Import a corporate card statement CSV and auto-match transactions to expense lines; flag unmatched lines."
6. **Travel agency / airline API** – "Let the Travel Assistant search fares from a travel-agent API and attach the chosen itinerary automatically."
7. **Mileage claims** – "Add an 'Own vehicle' category with km driven × rate per km from Settings."
8. **Per-diem for international travel** – "Add country-wise per-diem rates in foreign currency to the Matrix of Authority."
9. **Accounting export** – "Export paid claims as Tally Prime vouchers (XML) or journal CSV with GL codes and cost centers."
10. **Budget control** – "Department-wise annual travel budgets with utilisation shown on the dashboard and a warning when a request exceeds the remaining budget."
11. **Single sign-on** – "Add Microsoft Entra ID / Google Workspace login in addition to email + password."
12. **Push notifications** – "Use the service worker and Web Push so installed apps receive approval alerts on phones."
13. **Multi-entity** – "Support several group companies / countries with their own approvers, currencies and policies."
14. **Carbon footprint** – "Estimate CO₂ per flight and show it on the dashboard."
