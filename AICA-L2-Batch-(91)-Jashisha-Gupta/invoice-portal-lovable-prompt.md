# Prompt for Lovable: Invoice Submission & Approval Portal with Auto-Accounting

You are a senior software development officer tasked with designing and building an **Invoice Submission & Workflow Portal** for a multi-department organization. The current accounting system has no workflow/approval capability, no tracking, and every invoice (Expense or Capex) is posted directly to the GL with no integrated PO process. This portal must sit in front of the accounting system, enforce a proper approval workflow, and produce clean, ready-to-post accounting entries.

Build a full web application (React frontend + Supabase backend, with authentication, role-based access, database, file storage, and PDF generation) covering the following.

---

## 1. User Roles & Access Control

Access control must be **role-based and enforced at both the UI and database/API level** (not just hidden buttons) — a user should not be able to call an API action outside their role even if they know the endpoint.

| Role | Description | Key Permissions |
|---|---|---|
| **Requester (Department User)** | Any staff member raising an invoice on behalf of their department | Create/edit own Draft requests only, attach scanned invoice, submit (Send to HOD), view/track own requests only |
| **HOD (Head of Department)** | Approves invoices raised by their own department | View/approve/reject/return requests **only for their own department**, system-approve, upload signed physical HOD Approval Sheet |
| **Finance Checker** | First point of contact in Finance | View all HOD-approved requests (all departments), **link Vendor Code**, edit GL/Expense account & cost center, compute WHT, generate Physical Invoice Submission Sheet, forward to Finance Approver — **cannot approve final voucher, cannot see/edit after Finance Approval except via revision return** |
| **Finance Approver (Finance Review & Approve)** | Senior finance reviewer | View Finance-Checked queue, Approve / Reject / Return for Revision, triggers Voucher generation on approval — **cannot edit Vendor/GL fields directly; must return to Checker to correct** |
| **Finance Staff (Payment Processing)** | Handles post-voucher payment confirmation | View Payment Request queue, upload Statement of Account (SOA) from accounting system, confirm/reconcile voucher entries — **cannot create or edit vouchers** |
| **Admin** | System configuration | Manage users, roles, departments, vendor master, GL/expense account mapping, WHT rate master, approval matrix/thresholds, ODBC connection settings, full audit trail and all reports |

Additional access-control rules:
- **Field-level locking** by stage: Vendor Code and GL/Expense Account fields are editable **only** by Finance Checker, and only before Finance Approval; Voucher fields are **never** editable by any role once generated (system-only, read-only).
- **Department-scoped visibility**: HOD and Requester can only see requests belonging to their own department; Finance roles see across all departments.
- **Segregation of duties**: the same user cannot hold both Finance Checker and Finance Approver roles simultaneously on the same invoice (system should block self-approval where a user is assigned both roles).
- Admin manages all role assignments and can configure department-to-HOD mapping and approval thresholds.

Support multi-level HOD approval if amount exceeds a configurable threshold (e.g., escalate to next-level approver/Finance Director above a limit).

---

## 2. End-to-End Workflow (Status Flow)

```
Draft → Submitted → HOD Approved (System + Physical) → Finance Checked (Vendor Linked, WHT Applied) 
      → Finance Approved → Accounting Entry (Voucher) Generated → Payment Request 
      → Payment Confirmed (ODBC-matched) → Closed/Paid
      
(At any stage: "Returned for Correction" or "Rejected" is possible, 
with mandatory comment, routing back to the Requester or Finance Checker as applicable)
```

1. **Draft** – Requester fills the invoice request form, attaches scanned invoice copy, saves as draft. The request stays fully editable and is **not counted/tracked** anywhere yet.
2. **Submitted (Confirmed)** – Requester clicks **Send to HOD**; this is the confirmation point — the Draft is locked (no further edits by Requester without HOD/Finance sending it back), a unique Request ID is assigned, and the system auto-routes it to the correct HOD based on department.
3. **HOD Approval (Dual Confirmation — System + Physical):** HOD approval is only considered complete when **both** of the following are done:
   - **System Approval** – HOD logs in, reviews the request online, and clicks Approve / Reject / Return with comments.
   - **Physical Approval** – On system approval, the system auto-generates a printable **HOD Approval Sheet** (PDF) summarizing the request (department, vendor, amount, GL/expense category, reference type/LPO or Agreement number, requester). This sheet must be **physically signed by the HOD** and then scanned/uploaded back into the system by the Requester or HOD as proof of physical sign-off.
   - The request **cannot move forward to Finance Check** until both the system approval flag AND the signed physical copy upload are recorded — track this as two distinct checkboxes/timestamps (`hod_system_approved_at`, `hod_physical_signed_uploaded_at`) so partial completion is visible and chase-able.
   - Multi-level approval if above threshold follows the same dual-confirmation pattern at each level.
4. **Finance Check** – Finance Checker:
   - Validates invoice details, amount, attachments, tax
   - **Links the correct Vendor Code** from Vendor Master (mandatory field before proceeding)
   - Confirms/edits the Expense or Capex GL account and cost center
   - **Computes Withholding Tax (WHT)**, if applicable, based on the vendor's WHT category (see Section 3)
   - Checks for duplicate invoice numbers per vendor
   - Generates the **Physical Invoice Submission Sheet** (see Section 5) as a PDF with a unique tracking/barcode number
   - Forwards to Finance Approver
5. **Finance Review & Approve** – Finance Approver does final review and Approves / Rejects / **Sends Back for Revision**.
   - If the Finance Approver finds an error in the Finance Checker's work (e.g., wrong Vendor Code linked, incorrect GL/Expense account, wrong cost center, wrong reference type, wrong WHT computation), they select **"Return for Revision"** and must enter a **mandatory correction comment/suggestion**.
   - This routes the invoice back to the **same Finance Checker** (not to HOD or Requester) with the correction note visible at the top of the screen.
   - Finance Checker corrects the flagged field(s) and re-submits to Finance Approver. This can loop as many times as needed.
   - **No Voucher/Expense entry is generated at any point during this back-and-forth** — see the hard rule in Section 3.
6. **On Finance Approval only (system-triggered, automatic):**
   - System auto-generates the **Accounting/Journal Voucher** (see Section 3) with a unique **Voucher Number**
   - Status changes to "Accounting Entry Generated"
   - Voucher is queued for export/posting into the core accounting system
7. **Payment Request** – Once the voucher is generated and posted into the accounting system (outside this portal, via export or manual entry by Finance), the request is auto-routed to a **Payment Request queue** for Finance Staff. See Section 4 for the full reconciliation process.
8. **Payment Confirmed / Closed** – Once the voucher is matched and confirmed against the accounting system's Statement of Account (see Section 4), status updates to "Payment Confirmed" and the request is closed.

Every stage change must be logged in an **audit trail** (who, when, action, comments) and trigger email/in-app notifications to the next actor and the requester.

---

## 3. Accounting Entry Logic (Core Business Rule)

This is the most critical function of the system. When the Finance Approver approves an invoice, the system must **automatically generate a balanced Journal/Expense Voucher** — no manual journal entry by finance staff.

**Hard rule — Voucher timing:**
- The Expense/Capex Voucher must **only** be generated (and only become printable/exportable) the moment the **Finance Approver clicks Final Approve**.
- No voucher, draft voucher, or preview PDF may be created at Finance Checker stage, during Finance Checker ↔ Finance Approver revision loops, or at any earlier stage. Enforce this at the database/application level (voucher record should not exist until `status = Finance Approved`), not just hidden in the UI, so it cannot be bypassed or generated early by mistake.
- Once generated, the Voucher should be locked (read-only) — any further correction after this point requires a separate reversal/adjustment voucher, not an edit to the original.

**Standard entry to be auto-created (no WHT applicable):**

| Account | Dr / Cr | Source |
|---|---|---|
| Expense / Capex GL Account | **Debit** | Selected/confirmed by Finance Checker from a predefined GL/Expense Chart of Accounts mapped to department & expense category |
| Vendor (Accounts Payable – Vendor Subledger) | **Credit** | Vendor Code linked by Finance Checker from Vendor Master |

**Withholding Tax (WHT) — computed at Finance Check stage:**
- Each Vendor Master record carries a **WHT Category / Applicability flag** (e.g., WHT-applicable services, WHT-exempt, rate varies by service type) maintained by Admin, plus a **WHT Rate Master** table (rate % by category, effective date, so rates can change over time without code changes).
- When Finance Checker links the Vendor Code, if that vendor/category is WHT-applicable, the system should **auto-suggest the WHT rate and computed WHT amount** based on the invoice amount, which the Finance Checker can confirm or override (with a mandatory reason, logged for audit).
- If WHT applies, the voucher becomes a **three-line entry** instead of two:

| Account | Dr / Cr | Source |
|---|---|---|
| Expense / Capex GL Account | **Debit** (full invoice amount) | GL/expense category |
| Vendor (Accounts Payable – Vendor Subledger) | **Credit** (invoice amount **less** WHT) | Vendor Code, net of WHT |
| WHT Payable GL Account | **Credit** (WHT amount) | WHT rate × invoice amount, per WHT Rate Master |

- The system must validate **Total Debit = Total Credit** including the WHT split before the voucher can be generated.
- WHT rate, WHT amount, and WHT GL account used must be stored on the voucher record itself (not just referenced) so historical vouchers remain accurate even if rates change later.

Design rules:
- **Vendor Code linking is mandatory** and can only be performed at the **Finance Checker** stage (not by the Requester or HOD) — enforce this with role-based field locking.
- Each invoice request must capture: Department, Cost Center, Expense Category (mapped to a specific GL code), Expense vs Capex flag, Invoice Number, Invoice Date, Vendor Name (free text at request stage), Currency, Amount, Tax/VAT amount, Net Payable, Attachment(s).
- **Invoice Reference Type** (mandatory dropdown at request stage) — since LPOs are managed in a separate system with no integration, capture reference-only fields:
  - **Against LPO** – Requester selects this and enters the **LPO Number** (free text, no live validation against the LPO system for now) and LPO Date. Optionally allow an attachment of the LPO copy for cross-check.
  - **Against Agreement/Contract** – Requester selects this and enters **Agreement/Contract Reference Number**, Agreement Vendor Name, and Agreement Validity Period (optional attachment of the agreement/contract copy).
  - **Direct (No LPO/No Agreement)** – no reference required, but Finance Checker should see this flag clearly to apply extra scrutiny (since there's no PO or contract backing it).
  - This reference type and number must flow through to the Finance Checker screen and onto the **Physical Invoice Submission Sheet** and the final **Voucher** as a reference field (not a posting field) — it does not affect the Dr/Cr accounting entry, it's purely for traceability and audit, since LPO/Agreement values live in another system.
  - Admin dashboard/reports should allow filtering invoices by reference type (LPO / Agreement / Direct) so management can see what % of spend bypasses LPO/Agreement controls.
- The system should validate that **Total Debit = Total Credit** before allowing the voucher to be generated (should always balance automatically since it's a single Dr/Cr pair, but design the schema to support multi-line expense splits, e.g., one invoice split across two departments/cost centers/GL codes).
- Voucher should carry a unique **Voucher Number**, linked back to the original Invoice Request ID, Vendor Code, GL Code(s), Cost Center(s), and approval trail — this becomes your audit-ready source document.
- Since there is **no integrated PO**, add an optional "Budget/Cost Center reference" field at Finance Checker stage for informal budget validation (not a hard PO match, just a soft control).
- Provide an **export function** (CSV/Excel in a format matching the existing accounting system's journal import template) so Finance can upload the generated vouchers into the core accounting system until real-time integration is built.
- Maintain a **Vendor Master** and **GL/Expense Account Master** as admin-managed lookup tables, each with an active/inactive flag.

---

## 4. Payment Request & Accounting System Reconciliation (ODBC)

After the Voucher is generated and exported/posted into the core accounting system, the request enters the **Payment Request** stage — this is where the portal confirms the entry actually landed correctly in the accounting system, closing the loop.

**Process:**
1. Once a voucher is generated, the request automatically appears in the **Payment Request queue**, visible to **Finance Staff (Payment Processing)** role.
2. Finance Staff **uploads the Statement of Account (SOA) / GL extract** from the accounting system (as a file — CSV/Excel/PDF export) for the relevant period or vendor.
3. The system establishes a **read-only ODBC connection to the accounting system's database** and pulls the posted voucher/GL entries directly (in addition to, or instead of, the manual SOA upload, depending on what access is granted).
4. The system performs an automatic match using the following logic, since the accounting system may assign its **own posting reference** separate from this portal's Voucher Number:
   - **Primary match**: **Vendor Code + Amount + Date** (invoice/posting date, with a small configurable date-tolerance window, e.g., ±3 days, to allow for posting lag) against the accounting system's entries (via ODBC and/or the uploaded SOA).
   - **Secondary/confirming check**: if the accounting system entry also carries the portal's **Voucher Number** (e.g., in a narration/reference field), the system checks for it and marks the match as **"Strong Match"** when both the primary fields and the Voucher Number agree, versus **"Match (No Voucher Ref)"** when only Vendor+Amount+Date agree but the Voucher Number isn't found in the accounting system's reference field.
   - This distinction matters for audit: a Strong Match is fully traceable end-to-end; a Match (No Voucher Ref) still confirms the payment happened but flags that the accounting system posting didn't carry the portal's reference — useful feedback to Finance on posting discipline.
5. **Match outcomes:**
   - **Strong Match** or **Match (No Voucher Ref)** – status auto-updates to **"Payment Confirmed"**, timestamped, with the matched accounting-system reference and match type stored for audit.
   - **Multiple Candidates** – more than one accounting-system entry fits Vendor+Amount+Date within tolerance (e.g., two similar invoices from the same vendor on the same day) → flagged for **manual selection** by Finance Staff rather than auto-confirmed, to avoid a false match.
   - **Mismatch / Not Found** – no accounting-system entry fits Vendor+Amount+Date at all → flagged as **"Reconciliation Exception"**, routed to Finance Staff/Finance Manager for manual investigation, with the discrepancy details displayed side-by-side (portal value vs. accounting system value).
6. Finance Staff can manually mark exceptions as resolved (with comments) once investigated, or re-run the match after a corrected posting.

**Design notes for Lovable:**
- Build this as a **read-only ODBC/database connector configuration screen** (Admin-managed: connection string, table/view name, field mapping for Vendor Code/Amount/Posting Date/Voucher-or-Narration-field) — the portal should never write back to the accounting system, only read.
- Make the **date-tolerance window** for the Vendor+Amount+Date match admin-configurable (default a few days), since posting into the accounting system may lag the approval date.
- If a live ODBC connection isn't feasible in the initial build, structure this as a **pluggable reconciliation module**: start with manual SOA upload + matching logic (CSV/Excel parsing, exact match on Vendor+Amount+Date with tolerance, plus text search for Voucher Number in the narration field), and design the matching engine so a live ODBC feed can be swapped in later without changing the workflow or UI.
- Log every match attempt (Strong Match, Match No Voucher Ref, Multiple Candidates, Mismatch, manual override) for audit — this becomes the definitive proof that a booked expense was actually posted and paid, and how confidently it was matched.

---

## 5. Physical Invoice Submission Sheet

Since original paper invoices must still physically move to Finance:

- On completion of the **Finance Check** step (after vendor code is linked), the system auto-generates a **printable PDF "Invoice Submission Sheet"** containing:
  - Unique Tracking Number / Barcode or QR code
  - Department, Requester name, Invoice number, Vendor name & code, Amount, GL/Cost Center, Approval status history (HOD approved by/date)
  - A checklist/signature block for "Physical invoice attached", "Received by Finance", date & signature fields
- This sheet is printed and **physically stapled to the original paper invoice** when it's walked/couriered to Finance.
- Finance Checker/Approver can mark **"Physical Copy Received"** in the system (checkbox + timestamp + received-by user) to close the loop between the digital workflow and the physical document — this becomes a key tracking control that doesn't exist today.

---

## 6. Finance Checker Accuracy / Correction Log (KPI Tracking)

Every time a Finance Approver returns an invoice for revision, the system must log it as a **correction record**, separate from the general audit trail, purpose-built for KPI reporting on Finance Checker accuracy:

- `checker_corrections` table: invoice_id, finance_checker_id, finance_approver_id, field_corrected (e.g., Vendor Code / GL Account / Cost Center / Reference Type / Amount / Other), original_value, corrected_value (once checker resubmits), approver_comment, returned_at, resolved_at, revision_round_number (1st, 2nd, 3rd return on the same invoice).
- This must capture **every round** if an invoice bounces back and forth more than once — don't overwrite, append.
- **Admin/Management Dashboard** should include a **Finance Checker Accuracy report**:
  - Number of invoices processed per checker vs. number returned for revision (error rate %)
  - Breakdown by error type (Vendor mislink, wrong GL/Expense mapping, wrong cost center, etc.)
  - Trend over time (monthly/quarterly) per checker — for performance review / KPI purposes
  - Average number of revision rounds per invoice
- This log should be visible to Admin/Finance Manager but **not editable/deletable** by the Finance Checker or Approver — it's a performance record, so it needs to be tamper-proof once created.

---

## 7. Dashboards & Tracking

- **Requester Dashboard**: My submissions, status, pending action, aging (days pending at each stage).
- **HOD Dashboard**: Pending approvals for my department, approved/rejected history.
- **Finance Checker Dashboard**: Queue of HOD-approved invoices pending vendor linking/check/WHT computation, physical copy tracking status.
- **Finance Approver Dashboard**: Queue pending final approval, generated vouchers log.
- **Finance Staff (Payment Processing) Dashboard**: Payment Request queue, reconciliation exceptions pending investigation.
- **Admin/Management Dashboard**: 
  - Full pipeline view (Kanban or status funnel: Draft → Submitted → HOD → Finance Check → Finance Approved → Payment Request → Payment Confirmed)
  - Ageing report (invoices stuck > X days at any stage)
  - Expense vs Capex split, by department, by vendor, by GL account
  - WHT summary report (total WHT withheld by vendor/period, for tax filing support)
  - Reconciliation exception report (unmatched vouchers)
  - Audit log / full history export

---

## 8. Data Model (suggested core tables)

- `users` (id, name, email, role, department_id)
- `departments` (id, name, hod_user_id, approval_threshold)
- `vendors` (vendor_code, vendor_name, tax_id, bank_details, wht_category, wht_applicable_flag, status)
- `wht_rates` (id, wht_category, rate_percent, effective_from, effective_to)
- `gl_accounts` (gl_code, gl_name, type: Expense/Capex/WHT_Payable, department_id_optional)
- `cost_centers` (id, name, department_id)
- `invoice_requests` (id, requester_id, department_id, vendor_name_free_text, invoice_no, invoice_date, currency, amount, tax_amount, net_amount, expense_type, reference_type: LPO/Agreement/Direct, reference_number, reference_date, description, status, current_approver_id, hod_system_approved_at, hod_physical_signed_uploaded_at, wht_applicable, wht_rate, wht_amount, created_at)
- `invoice_lines` (invoice_id, gl_code, cost_center_id, amount) — supports split entries
- `approvals` (invoice_id, approver_id, role, action, comments, timestamp)
- `vendor_links` (invoice_id, vendor_code, linked_by, linked_at)
- `vouchers` (voucher_no, invoice_id, gl_code, dr_cr, amount, vendor_code, wht_amount, wht_gl_code, created_at, exported_flag) — **rows only ever created at `status = Finance Approved`**
- `checker_corrections` (id, invoice_id, finance_checker_id, finance_approver_id, field_corrected, original_value, corrected_value, approver_comment, revision_round_number, returned_at, resolved_at) — append-only, used for Finance Checker KPI reporting
- `payment_reconciliation` (id, voucher_no, invoice_id, match_status: StrongMatch/MatchNoVoucherRef/MultipleCandidates/Mismatch/NotFound/ManuallyResolved, accounting_system_reference, matched_vendor_code, matched_amount, matched_date, date_tolerance_used, matched_at, matched_by, notes)
- `attachments` (invoice_id, file_url, uploaded_by, uploaded_at, type: scanned_invoice/hod_approval_sheet/submission_sheet/soa_upload)
- `audit_log` (entity, entity_id, action, user_id, timestamp, details)

---

## 9. Non-Functional Requirements

- Role-based authentication and access control (Supabase Auth), enforced at API level, not just UI
- Field-level and record-level permission checks (see Section 1) — segregation of duties between Checker and Approver
- Email/in-app notifications on every status change, including reconciliation exceptions
- Full audit trail (immutable log of all actions)
- File upload/storage for scanned invoices, generated PDFs, and Statement of Account uploads
- PDF generation for the HOD Approval Sheet and Invoice Submission Sheet
- CSV/Excel export of vouchers for import into the existing accounting system
- Read-only ODBC/database connector for accounting-system reconciliation (Admin-configurable, never writes back)
- Search/filter on invoices by status, department, vendor, date range, amount, reference type, WHT applicability
- Responsive UI, clean dashboard-style layout, clear status badges/colors per stage
- Configurable approval thresholds and multi-level approval per department (admin-manageable)
- Configurable WHT rate master, independent of code changes, with effective-dating

---

## Objective

Build this as a production-ready web app that closes the current gaps: no workflow, no tracking, and direct-to-GL posting with no controls. The end result should give Finance a clean, vendor-linked, GL-mapped, fully auditable Expense Voucher (Debit Expense/Capex, Credit Vendor) the moment an invoice is approved — ready to post into the existing accounting system — while giving every department full visibility into where their invoice is stuck in the approval chain.
