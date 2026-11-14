---
title: "Miles2Collect: Master Build Prompt"
subtitle: "ICAI AICA Level 2 Capstone | CA Dipti Kothari | Revised 43"
---

# How to use this prompt

This is the prompt sequence used to build Miles2Collect with an AI coding assistant (Claude). Paste **Prompt 0** once at the start, then paste **Prompts 1 to 9** one at a time. Test each stage before moving to the next. Each prompt states what the result must do, so it can also be used as the specification of the tool.

Tools used: Claude (build), Google Gemini through n8n (runtime AI for two narrow jobs), n8n Cloud, Gmail (test inboxes only).

# Prompt 0: Role, context and rules (paste once)

You are a senior full-stack engineer and a Chartered Accountant-level domain expert in Indian real estate finance (RERA, GST, Companies Act, MIS). Build **Miles2Collect**, an offline-first, single-file HTML application (HTML + CSS + JS in one file, no server) for a Maharashtra real estate developer. It controls construction-milestone billing and collection.

**Problem.** Developers may demand money only after a construction milestone is certified complete. Today the chain (architect certificate, schedule check, instalment and GST, demand letter, bank matching, overdue chase, interest, RERA 70% account) runs on scattered Excel, PDFs and emails with weak controls.

**Design principle (do not break).** AI reads and suggests, fixed rules verify every statutory number, and a human approves. AI never calculates GST, interest or the RERA figure, and never sends anything on its own.

**Technical rules**

- One HTML file; inline pdf.js, jsPDF and SheetJS; no CDN dependency at run time. Works offline except the n8n calls.
- One state object, a `recompute()` function for derived totals, a `render()` function for the screen.
- Persist to localStorage; keep large files (master Excel, certificate PDF) under a separate key so a full store never blocks the small approval record. Confirm the save to the user and warn clearly on failure.
- Accessible, responsive, professional UI; Indian number format (lakh and crore).
- Never invent figures. If data is missing, show "not recorded".
- Show partial progress honestly: if a demand is raised on 2 of 30 customers, every status must say "Partly · 2 of 30", never "Done".

**Domain rules, kept as configurable settings**

- Maharashtra RERA only. 70% of collections are held in the RERA account; withdrawal eligibility = (deposits + transfer) x cost-completed %.
- GST on residential construction demand: 5% without ITC, shown as CGST 2.5% + SGST 2.5% (IGST 5% if the customer's State is outside Maharashtra), on the full instalment, no separate land deduction. SAC 995411. Invoice date = milestone completion date.
- Delayed-payment interest: simple interest on unpaid overdue principal from demand date plus 15 days, default 12% p.a., read from Project Info key `Interest Rate % p.a.` (a demo input).

**Roles and access (demo-level, in the browser)**

- Accountant: Upload Master Data, Demand Workflow, Overdue Reminders, Upload Bank Statement, Reports.
- Manager: Sales & Inventory, Demand Schedule (approval inbox), Bank & Collections.
- Director: Dashboard and Profit & Loss only, view-only.
- Enforce by role guards on every action with a clear "not permitted" message. Passwords are set in one place.

Confirm you understand, then wait for Prompt 1.

# Prompt 1: Data model and master Excel upload

Parse a master Excel with sheets: Sales and Collections, Unit Master, Customer Master (including optional State and Virtual Account No), Company Payment Schedule (milestone no., name, % of agreement value), Project Info (key/value, including interest rate and RERA deposits and withdrawals), Project Cost (head, estimate, incurred). Validate and report missing or malformed columns in plain language. Build totals: agreement value, principal collected, outstanding, and per-flat schedule rows (achieved, raised, due, overdue days). Provide backup and restore of the whole project as a JSON file, and a "Download updated master Excel".

# Prompt 2: Architect certificate reading and validation

Upload a PDF (3 MB limit, with a clear message showing the actual size). Extract text with pdf.js and read fields by rules: is-certificate, project, milestone no., stage %, cumulative %, completion date, certificate reference, architect. Validate against the schedule: next pending milestone only, no skipped sequence, future dates rejected, percentages consistent. Show a "vs Schedule" comparison table. A wrong certificate shows red "rejected", blocks the stepper, and allows **Remove and re-upload** (Accountant only). Never show "AI cross-check done" for a rejected certificate.

# Prompt 3: AI cross-check through n8n (Gemini)

Build an n8n workflow: Webhook (POST) -> token check -> Gemini (temperature 0) via an LLM chain with a structured JSON output parser -> Respond to Webhook. Output: `is_certificate, project, milestone, milestone_name, stage_pct, cumulative_pct, completion_date, certificate_ref, architect, signed, confidence, notes`. In the app add an **AI cross-check** button, a "readers agree?" column (rules versus AI) and a rules-only fallback ("proceed on rule-based reading", logged against the reviewer) if n8n is unreachable. State clearly that confidence measures reading accuracy, not correctness; the rules decide.

# Prompt 4: Maker-checker approval

The Accountant enters the preparer name and submits only if the certificate is accepted and the AI step is done. The Manager sees an approval inbox on the Demand Schedule tab (pending count, last-saved time, a "Check for new submissions" button; also a banner on every Manager tab), reviews the rules and AI readings side by side, and Approves or Returns (a remark is required to return). Show an eight-step stepper: Master Excel, Certificate read, AI cross-check, Manager approval, Demands prepared, Demands raised, Demand emails sent, Receipts matched. Demands cannot be prepared, raised or emailed without approval. The Accountant cannot approve his or her own submission.

# Prompt 5: Demand generation and the GST invoice-cum-demand letter

For each sold flat with an agreement value compute principal = agreement value x milestone %, GST per the settings, the total, and the cumulative position. The Accountant selects customers (with a "Select all customers" box) and raises the demand. Create a boxed **Tax Invoice-cum-Demand** (HTML preview and A4 PDF with jsPDF): invoice number and date, supplier and recipient details, an amounts table with CGST/SGST or IGST, amount in words, bank and virtual account details, payment terms, interest clause and signature block. Give each demand a reference such as `M2C-<flat>-M<n>`. Email through a second n8n workflow (Gmail, HTML plus PDF, test-inbox guard), with a dry-run option. Status wording: "Email sent"; the Accountant can click "Mark as received" when the inbox confirms, and the name and time are recorded. Mark the invoice as a demo format, not a valid tax invoice. Handle new sales: upload an Agreement for Sale (PDF), block a second sale of a sold flat, and compute the catch-up demand (stages achieved to date x agreement value, less advance received, plus GST).

# Prompt 6: Bank statements, matching and AI narration help

Accept PDF, CSV or Excel statements (several files); skip duplicate entries. Show a list of uploaded statements with entries, receipts and payments per file, and let the Accountant remove one file or all. Match receipts by demand reference, flat number, virtual account, full customer name, then exact amount for an open demand. Unmatched receipts get an **AI suggest** button (and a bulk button). A third n8n workflow sends the narration, amount and the sold-flat list to Gemini and returns `matched, flat, confidence, reason`. Guards: the answer must be a flat from the list (otherwise discard), never match on amount alone, ambiguous surnames or vendor refunds return no match, below 70% confidence there is no Accept button, nothing applies until the Accountant clicks Accept, and the acceptance is logged.

# Prompt 7: Overdue reminders, interest and RERA

Ageing buckets (due not yet overdue, 1-30, 31-60, 61-90, over 90 days) on principal. Reminder emails with the interest worked out at the configured rate and a letter the Accountant can view first. Show the customers reminded with their overdue position before and after the next statement. Show collection efficiency = sum of min(received, demanded) / sum of demanded. RERA block: deposits, withdrawals, cost %, eligible amount, Form 3 style working.

# Prompt 8: Dashboards, flags and Profit & Loss

Director Dashboard cards (sales, demand, collection, outstanding with a four-line split, overdue, interest, RERA) and a separate Profit & Loss tab (the profit on the card and the statement must match). The Manager sees the inventory map and the red-flag list (overdue, bounced cheque, TDS not recorded, collection above 10% without a registered agreement, GST or stamp duty pending), each with who resolves it.

# Prompt 9: Reports, registers and packaging

Reports tab with three registers, each downloadable as Excel, PDF or CSV: Demand Register, Receipt Register (date, narration, amount, type, flat, how matched, demand reference, status, statement file) and Overdue Reminder Register. Add a Reset Project button for demo rehearsal only (state in the notes that production has no reset). Provide a complete delivery folder: the HTML, a launcher, START_HERE, a change log, demo files (master Excel, correct and wrong certificates, bank statements including a narration-matching file, three agreements) and a zip.

# Prompt 10: Self-review (run at the end)

Act as a sceptical CA judge. List every place where a status, total or label could mislead (partial progress shown as complete, stale wording, numbers that do not tie, controls that can be bypassed). Fix each and re-test the full demo sequence against the expected figures in START_HERE.
