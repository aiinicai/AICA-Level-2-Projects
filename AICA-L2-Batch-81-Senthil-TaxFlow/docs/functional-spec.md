# TaxFlow — Functional Specification (As-Built)

| | |
|---|---|
| Product | TaxFlow — Indirect Tax Compliance Platform |
| Version | 0.1.0 |
| Document type | As-built functional specification |
| Scope | Full product: authentication, organizations, roles, master data, recurring templates, ad-hoc compliance, compliance tracking & lifecycle, approvals, notifications, dashboards, reports, calendar, search, settings |
| Source of truth | Implemented behavior in the codebase (`src/`, `prisma/schema.prisma`, database schema), captured as of this document's writing |

> **How to read this document.** This is a *product* specification written from the implemented system. It describes what the product does today, the business rules it enforces, and the behaviors a user can rely on. Where the implemented behavior is surprising, differs from the master-data or template configuration a user might expect, or is unfinished, it is called out in an **As-built note**. Every chapter ends with acceptance criteria stated as observable behavior.

---

## Table of contents

1. [Product Overview](#1-product-overview)
2. [Users, Organizations, Roles & Permissions](#2-users-organizations-roles--permissions)
3. [Domain Glossary](#3-domain-glossary)
4. [Master Data](#4-master-data)
5. [Recurring Compliance Templates](#5-recurring-compliance-templates)
6. [Ad-hoc Compliance](#6-ad-hoc-compliance)
7. [Obligations Tracker](#7-obligations-tracker)
8. [Compliance Lifecycle, Approvals & Payments (Authoritative Chapter)](#8-compliance-lifecycle-approvals--payments-authoritative-chapter)
9. [Notifications, Activity & Audit](#9-notifications-activity--audit)
10. [Dashboard, Reports, Calendar & Search](#10-dashboard-reports-calendar--search)
11. [Settings, Application Shell & Cross-Cutting Behavior](#11-settings-application-shell--cross-cutting-behavior)
12. [Appendix A — Navigation Map](#appendix-a--navigation-map)
13. [Appendix B — Role / Permission Matrix](#appendix-b--role--permission-matrix)
14. [Appendix C — Compliance Status Flow](#appendix-c--compliance-status-flow)
15. [Appendix D — Notification Events](#appendix-d--notification-events)
16. [Appendix E — Report Catalog](#appendix-e--report-catalog)
17. [Appendix F — As-Built Notes & Gaps](#appendix-f--as-built-notes--gaps)

---

# 1. Product Overview

## 1.1 What TaxFlow is

TaxFlow is an **enterprise indirect-tax compliance management platform**. It helps organizations plan, assign, prepare, review, approve, file, and pay their recurring and one-off tax compliance obligations (VAT/GST, sales tax, withholding tax, corporate/income tax, statutory returns) across multiple legal entities and countries.

The product is delivered as a **web application** (Next.js on the App Router, styled with Tailwind and shadcn/Radix UI primitives, with data stored in PostgreSQL via Supabase). It is part of the wider **LucidBooks/Lucid** product family and uses **LucidShare** as its single sign-on identity provider.

## 1.2 Problem it solves

- Tax teams juggle many obligations: **recurring** filings (monthly/quarterly/annual per entity per form) and **one-off** filings (ad-hoc).
- Without a system, ownership, due dates, review/approval gates, filing evidence, and payment confirmation are tracked in spreadsheets and email.
- TaxFlow codifies the runbook: **who prepares, who reviews, who approves, what amount is being filed/paid, when it must be filed, and proof that it was filed and paid.**

## 1.3 Core concepts at a glance

- **Organizations** are the tenant boundary. Users belong to one or more organizations and act inside one "active organization" at a time.
- **Recurring Templates** define a standing obligation (form + entities + frequency + period anchoring + due dates + an approval flow + assigned people) that can be generated into individual compliance records for a given filing month.
- **Compliance records** ("compliance items", "schedules") are the tracked unit. They carry a tax period, filing due date, payment due date, status, preparer, reviewer/approver chain, filing details, and payment details. They come from recurring templates, from manual creation, from CSV import, or by rolling recurring records forward.
- **Approval flows** decide how many sign-offs a prepared submission needs: none, one-level (reviewer), or two-level (reviewer then approver).
- **The lifecycle** moves a compliance from creation → (admin/reviewer gate for non-template items) → preparation → submission → approval → **filed** → **paid** → **closed**.

## 1.4 Users

- Compliance **Preparers** — prepare filings and payments.
- **Reviewers / Approvers** — check and sign off.
- **Administrators** — configure templates and master data, generate filings, manage the organization.
- **Managers** — organization-wide oversight (recognized for closing and payment recording).
- The same person may hold different roles in different organizations.

## 1.5 Product-wide conventions

- Lists and dialogs are consistent across modules: searchable, filterable tables; create/edit dialogs; AlertDialog confirmation for destructive actions; toast notifications on success/error; empty states that offer a next action.
- Destructive deletes are **hard deletes** after an explicit confirmation ("This action cannot be undone.").
- Status is always visible as a colored badge; due dates are color-coded for urgency (red overdue, orange ≤3 days).
- There is no dark mode. The theme is a light "Lucid" palette (cream background, orange brand accent, warm card borders).
- The application is fully English (UI strings), with some US-centric formatting.

---

# 2. Users, Organizations, Roles & Permissions

## 2.1 Sign-in (authentication)

- Sign-in is delegated to **LucidShare**, the shared Lucid identity provider (Supabase Auth). The application does not verify passwords itself.
- The login page (route `/login`) presents **Email** and **Password** fields and a **"Sign in with your LucidShare credentials"** note. Successful sign-in redirects to the **Dashboard**.
- Signing out (header/sidebar **Sign Out**) returns the user to `/login`.
- Unauthenticated users visiting any application page are redirected to `/login`; signed-in users visiting `/login` are redirected to `/dashboard`.

### User profile auto-provisioning

- On the first sign-in of an email the app has not seen, TaxFlow automatically creates a local user profile:
  - username = email local-part; name from identity metadata if present, else the same local-part.
  - Default global role **PREPARER**.
  - The user is not yet a member of any organization.
- The user record is independent of their LucidShare credentials — credentials live in LucidShare; the profile, roles, and memberships live in TaxFlow.

## 2.2 Organizations & memberships

- An **organization** is the tenant. Users create organizations (from the dashboard when they have none, or via the sidebar org switcher's **Create Organization**).
- Creating an organization makes the creator its first member with the **ADMINISTRATOR** role.
- A user may belong to **multiple organizations**, with a different set of roles in each (stored per-membership, e.g. Admin in Org A, Preparer in Org B).
- **Employees** (Chapter 4) are the org members: an organization's user list is exactly its member list.

### Active context

- Most work happens inside one organization at a time — the **active organization** — plus one **active role** chosen from the roles the user holds in that org.
- Switching organizations/roles is done from the **Org Switcher** in the sidebar: it lists the user's organizations (check marks the active one) and shows role pills when the org grants more than one role. Pills are labeled **Admin** (for ADMINISTRATOR) or capitalized role names.
- The active context drives every page: data lists, filters, KPI dashboards, and the actions the server will allow.
- The active selection persists for 30 days (remembered in browser cookies).

> **As-built note.** The active organization is the primary data boundary. All compliance and org-scoped master data is scoped to the active organization. Role changes made via the header **Role:** submenu change the *user's global default role*, which is distinct from org-scoped roles and used as the active role's fallback.

## 2.3 Roles

The product recognizes the following roles (labels used in the UI in parentheses):

| Role | Label | Notes |
|---|---|---|
| `ADMINISTRATOR` | Admin | Full configuration & administrative control; org-wide visibility; template/approval gate actions; delete/generate rights |
| `MANAGER` | Manager | Orphaned-but-recognized; can close compliance and record payments; org-wide dashboard; can be granted by admins on the Employees page but **cannot be self-assigned** via Settings/header |
| `PREPARER` | Preparer | Default role; prepares, submits, files, records payment on items they are assigned |
| `REVIEWER` | Reviewer | Available as a role and used to filter reviewer pickers; step-1 approver in approval flows |
| `APPROVER` | Approver | Step-2 approver in two-level flows; approver-scoped dashboard |

- **Default global role for new users is PREPARER.** Default org role when adding a member is PREPARER.
- Users can change their own global role from **Settings → Account → Role** and from the header **Role** submenu (options: Administrator, Preparer, Reviewer, Approver).
- Membership roles are controlled by **Administrators** on the Employees page and apply per organization.

## 2.4 Permission model summary

Permissions are a mix of:
1. **Global/organization role** (active role), and
2. **Workflow identity** — being the assigned preparer, the assigned reviewer, or a recorded approver on a specific compliance, and
3. **Assignment records** created at compliance creation/editing.

Highlights (the full matrix is in Appendix B):

- **Admins** can do everything relevant to their org: create/edit templates, approve/send-for-review/reject templates, generate compliance, approve or send compliance to a reviewer, delete compliance, close compliance, and record payment.
- **Managers** (plus admins) can close compliance and record payment; admins/managers see the org-wide Executive Dashboard.
- **Preparers** see and act on their assigned work (dashboard, submit, resubmit, file, mark paid). Preparers (and admins) can add ad-hoc/recurring compliance and see edit controls on tracker rows.
- **Assigned reviewers** approve/reject compliance at the review stage and approve/reject templates sent to them.
- **Approvers** act at the current approval step, and see their own approval dashboard.

> **As-built note.** Several lifecycle actions (submit, resubmit, submit-to-admin, file) have no server-side role restriction — enforcement is by status gating and, on the UI, by what buttons a role sees. Edit of any compliance record is available to any authenticated viewer through the edit route/URL. See Appendix F.

---

# 3. Domain Glossary

| Term | Definition |
|---|---|
| **Organization** | Tenant boundary; owns master data, compliance records and templates. |
| **Entity (Legal Entity)** | A registrable company/unit within an organization that files returns (e.g., "ACME Pte Ltd"). Has its own country, functional currency, and approval-flow default. |
| **Group filing / Group return** | A single compliance record that covers several entities at once. One entity is the **filing entity** (the return is filed under it); the others are linked as group members. |
| **Form** | A regulatory form master used to label filings and carry defaults (tax type link, requires-payment flag, approval-flow default). |
| **Tax type** | Fixed classification (GST, VAT, SALES_TAX, WHT, CORPORATE_TAX, STATUTORY). |
| **Tax period** | The reporting window a filing covers, expressed as a start date, end date, and a display label (e.g., "2026-03-01 – 2026-03-31"). |
| **Filing month** | The calendar month in which the return must be filed (derived from the due date); used to schedule recurring generation. |
| **Filing due date (F Due)** | Deadline to file. |
| **Payment due date (P Due)** | Deadline to pay the tax due (may differ from filing due date → "dual due dates"). |
| **Recurring template** | Standing definition of a repeated obligation; admin-approved; can be generated into compliance records per filing month and rolled forward period after period. |
| **Ad-hoc compliance** | A one-off compliance item tracked independently of any template (created individually or imported via CSV). |
| **Approval flow** | `NONE` (no approval), `ONE_LEVEL` (reviewer only), `TWO_LEVEL` (reviewer then approver). |
| **Preparer** | The person assigned to prepare a compliance item. |
| **Reviewer** | Step-1 sign-off in a one- or two-level flow. |
| **Approver** | Step-2 sign-off in a two-level flow. |
| **Delay** | A derived figure — how many days past a due date a filing or payment occurred (or is overdue by). Not stored; computed when displayed/exported. |
| **Confirmation chain** | For payment filings, the sequence of amount confirmations (entered at submission, reconfirmed by each approver, confirmed at payment) that must be completed before approval/payment is recorded. |
| **NIL return** | A filing of zero amount; requires no payment. Non-payment forms auto-filing as NIL returns. |
| **Refund return** | A filing claiming a refund, with a refund type of **Claimed from tax authority** or **Carried forward for adjustment**. |

---

# 4. Master Data

Master Data is where the reference data used across TaxFlow is managed. Reached via the sidebar **Master Data** group and the "Master Data Management" landing page. Modules: Countries, Entities, Tax Types, Forms, Employees, Currencies, Exchange Rates. (Recurring Templates is admin/master-adjacent and documented separately in Chapter 5.)

Data scope varies by module — see each section. The general pattern is a table with search/filters, add/edit dialogs, delete confirmations, and CSV import where supported.

## 4.1 Countries

- **Fields:** Name (required), Code (required, max 3 chars, stored uppercase e.g. `US`), Region (optional).
- **Scope:** Global (shared by all organizations) — countries are not org-specific.
- **Behaviors:** search by name/code/region; add/edit/delete (hard delete). Duplicate name or code is rejected.
- **CSV import:** headers `Name, Code, Region`. Existing rows are updated (region) when name or code matches; new rows inserted.

### Acceptance criteria
1. A user can create a country with a unique name and unique 3-character code; duplicates are rejected with a message.
2. A country can be edited, searched, and deleted (with confirmation).
3. Importing `Name, Code, Region` rows adds new countries and updates the region of matching existing ones, and reports Inserted/Updated vs Skipped counts.

## 4.2 Entities (Legal Entities)

- **Fields:**
  - Entity Number (required, unique within org; free text, e.g. `ENT-001`)
  - Entity Name (required)
  - Country (required)
  - Status — **Active / Inactive / Suspended** (default Active)
  - Tax Registration Number (optional)
  - **Legal Entity Functional Currency** (default USD)
  - **Approval Flow** — None / One-Level / Two-Level, with helper text "Determines how submitted compliances are approved for this entity." (default One-Level)
- **Scope:** Org-scoped. Entity number must be unique within the active org.
- **Behaviors:** search by number/name/tax-reg; filter by country; add/edit/delete. Deletion is blocked by the database when the entity is referenced by a compliance record/template (the UI surfaces the delete as a failure toast).
- **Use in the product:** entities are selected when defining templates and compliance items; an entity can be a **filing entity** for a group return. Entity country auto-fills the compliance/template country; entity currency becomes the compliance's reporting currency; entity approval flow is the default flow when the form doesn't specify one.
- **CSV import:** headers `Entity Number*, Entity Name*, Country ID*` (UUID from Countries), `Status`, `Tax Reg Number`, `Currency`, `Approval Flow`. Upsert by `(org, entity number)`.

> **As-built note.** The entity dialog's currency dropdown is populated from currencies that appear as `fromCurrency` in Exchange Rates (with USD fallback), not from the Currencies master list.

### Acceptance criteria
1. Creating an entity requires number, name, country; duplicate number in the org is rejected.
2. Entity list shows number, name, country, approval flow, status, tax reg, and functional currency; entity records can be searched and country-filtered.
3. Selecting multiple entities for a compliance/template requires designating one **Filing Entity**.
4. A referenced entity cannot be deleted (delete fails with an error).

## 4.3 Tax Types

- A **fixed, read-only** catalog of six tax types: GST (Goods and Services Tax), VAT (Value Added Tax), Sales Tax, WHT (Withholding Tax), Corporate/Income Tax, Statutory Contributions.
- No create/edit/delete and no API — the list is a reference used in selectors throughout the product (compliance forms, templates, filters, reports, imports).

### Acceptance criteria
1. The Tax Types page lists all six tax types with code and description and offers no editing.
2. Every tax-type selector across the product offers the same six values.

## 4.4 Forms (Form Master)

- **Fields:**
  - Form Number (required, unique within org+country)
  - Form Name (required)
  - Tax Type (optional; from the six fixed types)
  - Description (optional)
  - **Requires Payment** (toggle, default **on**) — "Non-payment filings skip the payment section."
  - **Approval Flow** (default One-Level) — "Compared against the entity master on each compliance. The form's flow applies."
- **Scope:** Org-scoped.
- **Behaviors:** search/filter; add/edit/delete (hard delete; deleting a form nulls the form on existing schedules/templates rather than blocking). Duplicate form numbers within the same org and country are rejected.
- **Effect on other modules:** choosing a Form in a compliance/template seeds the approval flow (form flow overrides entity flow) and determines whether payment fields (payment due date, amount, confirmations, mark-paid) apply (`requiresPayment`).
- **CSV import:** headers `Form Number*, Form Name*, Tax Type, Description, Requires Payment` (yes/no), `Approval Flow`.

> **As-built note.** The Forms page does not expose Country or Compliance Type fields, although the data model/API support them and templates select forms by tax type only.

### Acceptance criteria
1. Creating a form requires form number and name; duplicates within the org+country are rejected.
2. A form with **Requires Payment off** causes generated/compliance forms to skip payment due dates and payment sections.
3. Selecting a form in a compliance auto-applies the form's approval flow unless the user overrides it.
4. Deleting a form does not block deletion of referencing compliance items.

## 4.5 Employees (Organization Members)

- There is **no separate employee table** — an "employee" is an organization membership joined to a user account.
- **Add Member:** an administrator searches registered users (by name/email/username) and assigns them one or more roles in the org. Default preselected role: **Preparer**. At least one role is required. Duplicate membership is rejected ("User is already a member of this organization").
- **List columns:** Name | Email | Roles (badges) | Status (derived from the user's Active flag — not editable here) | Actions.
- **Edit Roles:** change a member's role set (e.g., add Reviewer/Approver/Admin).
- **Remove Member:** removes the membership (not the user account).
- **Role options an admin can grant:** Administrator, Manager, Preparer, Reviewer, Approver.
- Related to roles **reviewer/approver/preparer pickers**: when a compliance/template needs to pick a Preparer, Reviewer, or Approver, the pickers are filtered to org members holding that role.

> **As-built note.** Assigning a reviewer/approver on an item whose person is not (yet) an org member auto-adds them as a member with the matching role, so the pickers and membership stay consistent.

### Acceptance criteria
1. An admin can add an existing registered user as a member with chosen roles and can edit/remove the membership.
2. A member's Status column reflects the linked user account's active state.
3. Role-filtered pickers (Preparer/Reviewer/Approver) only show org members with that role.

## 4.6 Currencies

- **Fields:** Code (required, uppercase, unique within org), Name (required), Symbol (optional), Decimals (default 2, 0–6), **Base** (boolean "Mark as base currency").
- **Scope:** Org-scoped.
- **Behaviors:** search; add/edit/delete; duplicate code within the org rejected. Base is informational (starred "Base" badge).
- **CSV import:** headers `Code*, Name*, Symbol, Decimals, Base` (true/false).

> **As-built note.** Nothing enforces a single base currency per org; and the Entity currency picker reads from Exchange Rates rather than this list (see 4.2 note).

### Acceptance criteria
1. A currency can be created/edited/deleted per org with code uniqueness enforced.
2. Marking a currency as base shows the Base badge in the list.

## 4.7 Exchange Rates

- **Semantics:** rates are **USD-relative**. Each row stores `fromCurrency` → USD; the helper text reads: "Rate is the amount of {fromCurrency} equal to 1 USD. Example: if 1 USD = 83.50 INR, enter fromCurrency: INR, rate: 83.50."
- **Fields:** From Currency (required), Rate (required, 6-decimal), Date (required). **To Currency is always USD** (not editable).
- **Scope:** Global (shared across organizations). One rate per (fromCurrency, date) — duplicate rejected.
- **Behaviors:** search by currency; add/edit/delete; list sorted newest-first.
- **Upload:** download a `fromCurrency, rate, date` template or upload your own CSV; results show Inserted/Updated, Skipped, Total.
- **Consumption:** when exporting reports, amounts are converted to USD using the rate for the relevant month (falling back to the latest prior rate) — see Chapter 10. Rates are also the source list for entity functional-currency pickers.

### Acceptance criteria
1. Adding an exchange rate requires from-currency, rate (>0), date; a duplicate (currency, date) is rejected.
2. Exports convert compliance amounts to USD using the rate effective for the item's month, falling back to the most recent prior rate.

---

# 5. Recurring Compliance Templates

Recurring Templates let an organization define a standing obligation once, get it approved, and then **generate** a compliance record for each filing period. Templates live under the sidebar path **Compliance Home → Recurring Templates** (`/master/compliance-templates`) and are administered from the "Recurring Templates" list page.

## 5.1 List page

- Title **"Recurring Templates"**, description "Manage recurring template schedules and generate by month."
- **Table columns:** Template Number, Version (shown as `v{n}` when >0), Status, Tax Type, Country, Form, Frequency, Entities (count), Recurring (Yes), Created By, Actions.
- **Filters:** text search (template number) plus Status, Country, Entity, Tax Type, Form, Frequency selects. Status options are Pending Admin Approval, Pending Review, Approved, Rejected (Draft is never offered because templates never sit in Draft).
- **Row actions (dropdown):**
  - Everyone: **View**, **Edit**.
  - Admins only: **Generate for Month**, **Activate/Deactivate** (only when status is Approved), **Delete** (only allowed when no compliance has been generated from the template — otherwise the server instructs you to deactivate instead).
- **Header actions (admins):** **+ Add Recurring Templates** and **Generate for Month** (bulk generation across templates for a chosen filing month).

## 5.2 Template anatomy — the create/edit form

| Field | Required | Notes |
|---|---|---|
| Tax Type | Yes | One of the six fixed tax types |
| Form | No | Filtered by tax type; auto-seeds approval flow + payment requirement |
| Entities | Yes | Multi-select; "A template must be linked to at least one entity." |
| Filing Entity | Yes* | Required only when >1 entity ("the entity the group return is filed under"); disabled otherwise |
| Country | Yes | Auto-detected from first selected entity; overridable |
| Frequency | Yes | Weekly / Monthly / Bi-Monthly / Quarterly / Half-Yearly / Annual |
| Days to File | No | "Days available to file after the tax period ends." (1–365; default math uses 15) |
| First Period End Date | No | "End date of the first tax period. Subsequent periods roll forward from here." |
| Payment Due Days | No | Shown only when the form requires payment; "Defaults to Days to File." |
| Priority | No | Normal / High / Critical (default Normal) |
| Approval Flow | No | None / One-Level (Reviewer only) / Two-Level (Reviewer then Approver); default One-Level; auto-suggested from form, else filing entity |
| Preparer | No | Defaults to the current user |
| Reviewer | Yes* | Required when the flow uses a reviewer; "Reviewers step-1 approvals on generated compliances." |
| Approver | Yes* | Required only for Two-Level |
| Recurring End Date | No | "Generation stops after this date (optional)." |
| Notes | No | Free text |
| Change Reason | (edit only) | Shown to admins editing an **approved** template: "Saving this approved template creates a new version with the reason recorded." |

- The form **always** creates a recurring template (`isRecurring = true`); there is no recurring/one-off toggle on templates.
- Approval flow is auto-suggested at creation from the selected form's flow, else the filing entity's flow. On edit, the stored value is used instead.
- Templates are **submitted directly for approval on creation** ("Define a recurring template for repeated compliance schedules. Submits directly for approval.") — the submit happens as part of Create.

## 5.3 Template lifecycle & approval

Templates have their own approval lifecycle (distinct from individual compliance items):

```
Created (PENDING_ADMIN_APPROVAL, submitted by creator)
   │
   ├─ Admin approves ────────────► APPROVED  (version 1, template number issued,
   │                                   first compliance auto-generated for current month)
   ├─ Admin sends to reviewer ──► PENDING_REVIEW
   │                                  │
   │                                  └─ Reviewer approves ─► APPROVED
   │                                      (version 1, number issued, first compliance generated)
   └─ Reject (admin, or assigned reviewer at review stage) ─► REJECTED
```

| Step | Who | Result |
|---|---|---|
| Create | Any user (button is admin-oriented in UI) | Status `PENDING_ADMIN_APPROVAL`, version 0, submitted-by recorded, awaiting admin approval |
| Approve (admin) | Admin | `APPROVED`, template number issued (`TPL-{taxType}-{countryCode}-{NNN}`), version 1 with snapshot ("Initial approval"), **and the first compliance is generated for the current month** |
| Send to Reviewer | Admin | `PENDING_REVIEW`; reviewer is notified |
| Reviewer approve | The **assigned reviewer** (by identity) | `APPROVED`, number issued, version 1 ("Reviewer approval"), first compliance generated for the current month |
| Reject | Admin (at admin stage) or assigned reviewer/admin (at review stage) | `REJECTED`; reason recorded in audit and notification to the creator |
| Deactivate / Activate | Admin (Approved only in UI) | Flips the Active flag; generation is blocked for inactive templates |
| Edit | Anyone for non-approved; **admin-only for approved** | Approved-template edits create a **new version** (snapshot + field diffs + change reason); non-approved edits update in place |

Notes:
- A template number is only issued at first approval.
- Only **active** templates participate in generation.
- Deleting a template is refused if any compliance records were generated from it ("Cannot delete template with generated compliances. Deactivate it instead.").

## 5.4 Versioning

- Version 0 = created. Version 1 = first approval. Each subsequent admin edit of an **approved** template increments the version and stores: a full snapshot, the field-level diffs (old → new), and the change reason.
- The **Versions** tab on the template detail page lists every version with who/when/reason and an expandable field-diff table.

## 5.5 Approval-flow decoupling ("flow override")

- The template carries its own **active approval flow** that governs the compliance items it generates — independent of the entity master and form master "placeholder" flows.
- The template detail page shows an **Approval Flow Mechanism** card with three panels:
  1. Entity Master Flow (placeholder)
  2. Form Master Flow (placeholder)
  3. **Active Template Flow (Driving Flow)**
- When the template flow differs from the entity/form defaults, an amber **"Flow Override Active"** notice explains that the active template flow overrides the master placeholder settings.
- Generated compliance items receive approval records from this template flow (reviewer step 1, approver step 2 when configured).

## 5.6 Generation of compliance items

Two admin-driven mechanisms produce compliance records from templates:

**(a) One-off / bulk "Generate for Month"**
- Pick a filing month (required); optionally filter bulk generation by country/tax type/entity.
- For each matching active, approved template, the system computes the tax period and due dates (see period logic below), then either **generates** a new compliance item or skips it and reports the reason bucket:
  - `existing` — a compliance for that filing month already exists
  - `future` — the computed filing due date falls outside the requested month
  - `overlap` — the candidate tax period overlaps an already-generated period
  - `generate` — created
- Results summarize Created / future-skipped / overlap-skipped / existing-skipped / failed.
- Single-template generation from the detail page (admin) refuses months beyond the recurring end date.

**(b) First-compliance generation at template approval**
- When a template is first approved, the system automatically generates its first compliance item for the current month (respecting no recurring-end check).

### Period & due-date computation

- If prior periods exist → the next period starts the day after the last period ends and extends per frequency (e.g., monthly = to end of the following month; weekly = next 7 days).
- Otherwise, if a **First Period End Date** was set → the first period ends on that anchor date and starts frequency-length earlier (back-dated to month boundaries).
- Otherwise → a calendar-aligned period for the filing month (month = whole month, quarter = the quarter, etc.).
- **Filing due date** = period end + Days to File (default 15). **Payment due date** = period end + Payment Due Days (defaults to Days to File). Payment due date is only stored when the form requires payment.
- One template → **one** compliance per period, listing all its entities as group members under the filing entity (group-return design). Deduplication is per template.

### What a generated compliance contains

- Compliance ID `TAX-#####` (5 random digits)
- Status `PENDING_PREPARATION` (straight to preparation — template-generated items **bypass** the admin/reviewer draft gate)
- Country, tax type, form, tax period (start/end + label), filing month, frequency, both due dates, priority
- The template's entity set as group members; filing entity recorded
- Assignment to the template's preparer (when set)
- Approval records built from the template's flow (reviewer/approver)
- `source = TEMPLATE`, recurring flags and recurring-end date copied from the template, `templateVersion` recorded
- Activity entry "Generated from template {number} v{version} for {month}"

## 5.7 Acceptance criteria

1. Creating a template requires ≥1 entity, tax type, country, frequency; a group template (>1 entity) requires a filing entity; a one/two-level flow requires a reviewer; a two-level flow additionally requires an approver.
2. A newly created template enters Pending Admin Approval (submitted by its creator) and cannot be activated for generation until approved.
3. An admin can approve, send to a reviewer, or reject a pending template; the assigned reviewer can approve/reject a template in Pending Review.
4. First approval issues a template number, sets version 1, and auto-generates the first compliance for the current month.
5. Admin edits to an approved template require a change reason and produce a new version with field diffs; edits to non-approved templates save in place without a new version.
6. "Generate for Month" (single or bulk) creates compliance items for the requested filing month, skipping duplicates/overlaps/out-of-month due dates with a clear summary.
7. Template-generated compliance items start in Pending Preparation with the template's entities, preparer, and approval records.
8. Deactivating a template stops it from generating; deleting is blocked once compliances were generated from it.

---

# 6. Ad-hoc Compliance

Ad-hoc compliance items are **one-off obligations tracked without a recurring template**. They live under **Compliance Home → Ad-hoc Templates** (`/compliance/ad-hoc`), described as "One-off compliance items uploaded for tracking."

## 6.1 Ad-hoc list page

- **Table columns** (admin view adds a select-all checkbox column first): Compliance ID | Entity | Country | Tax Type | Tax Period | F Due | P Due | Priority | Status | Source | Preparer | Actions.
- **Filters:** search (compliance ID) + Status, Priority, Country, Entity.
- The page shows **only ad-hoc items** (`isRecurring = false`); recurring/generated items are excluded.
- **Actions:**
  - **+ Add Individual** (admin/preparer) → the ad-hoc create form.
  - **+ Upload CSV** (admin/preparer) → CSV import dialog.
  - **Approve Selected** (admin) — select rows via checkboxes, then bulk-approve in one step (see 8.7).
  - Row menu: **View / Edit / Delete** (View all; Edit admin/preparer; Delete admin).
- Due-date cells color-code urgency exactly as the tracker (red overdue, orange ≤3 days, "(Overdue)" / "(Nd left)" hints).
- Empty state: "No ad-hoc templates found — Upload a CSV to import one-off compliance items for tracking."

## 6.2 Creating an ad-hoc item ("Add Individual")

Form sections and fields:

- **Compliance Details:** Tax Type (required) | Form (optional; drives payment requirement; loaded per tax type) | Entities (required multi-select; country auto-fills from the first selected) | Filing Entity (required when >1 entity) | Country (auto, overridable) | Tax Period Start (required) | Tax Period End (required, min = start; live "Period: …" preview) | Due Date (required).
- **Payment & Priority:** Payment Due Date (only when the selected form requires payment), Priority.
- **Assignment & Approval:** Approval Flow (auto-defaulted from the form's flow, else entity's), Preparer (defaults to you), Reviewer (required when the flow needs a reviewer), Approver (required for two-level).
- **Notes.**
- Submit button: **Create Compliance**. On success you return to the ad-hoc list.

A single ad-hoc item is stored with `frequency = AD_HOC`, `isRecurring = false`, `source = MANUAL`, status **Draft**, and the chosen entities/approval records/preparer. Ad-hoc items start in **Draft** and therefore go through the admin (or reviewer) approval gate before preparation (see Chapter 8) — unlike template-generated items.

## 6.3 CSV import (bulk ad-hoc upload)

Required/downloadable template columns:

- **Entity Number** (must exist in the org)
- **Tax Type** (VAT/GST/SALES_TAX/WHT/CORPORATE_TAX/STATUTORY)
- **Tax Period** (e.g. `2026-03` or `Q1 2026`)
- **Due Date** (YYYY-MM-DD)
- Optional: Country (defaults to entity's country), Frequency (defaults AD_HOC), Priority, Reviewer Email, Approver Email, Notes

Import behaviors:
- Country defaults to the entity's country; reviewers/approvers are resolved by email.
- Approval records are built from the **entity's approval flow**; a two-level flow requires reviewer+approver emails, a one-level flow requires a reviewer.
- Duplicate rows (same entity+period+due date) are skipped.
- Imported items: status **Draft**, `source = IMPORT`, no preparer assignment, ad-hoc.
- The dialog reports Inserted/Updated, Skipped, and Total.

## 6.4 Acceptance criteria

1. The ad-hoc page lists only one-off compliance items, with the same filtering and due-date coloring as the tracker.
2. "Add Individual" creates a single ad-hoc item in Draft with a tax period range and both due dates, group support via Filing Entity, and approval records matching the chosen flow.
3. CSV import creates Draft ad-hoc items keyed to existing entities; invalid/missing values and duplicates are skipped and summarized; review/approval records are attached from the entity's flow by email.
4. An admin can select multiple ad-hoc items and **Approve Selected** to bulk-approve them (see 8.7).

---

# 7. Obligations Tracker

The Obligations Tracker (`/compliance`) is the main working list of every compliance item (recurring-generated, manual, and imported). It is the "Obligations Tracker" section of the sidebar's Compliance Home group.

## 7.1 List behavior

- **Columns:** Compliance ID | Entity | Country | Tax Type | Tax Period | F Due | P Due | Priority | Status | Source | Payment Amount | Filing Type | Currency | Preparer | Actions.
- **Filters:** text search (matches compliance ID) + Status ("All Statuses" default), Priority, Country, and Entity selects.
- **Sorting:** items are returned earliest filing-due first.
- The tracker shows **both** recurring and ad-hoc items. The only on-row indicator of origin is the **Source** badge (TEMPLATE / IMPORT / MANUAL).
- **Entity cell** for group returns lists the group's entity names (filing entity implicit).
- **Due-date coloring:** F Due and P Due show red text + "(Overdue)" when past due, orange + "({N}d left)" when within 3 days, suppressed once filed/paid. A "Nd left" formatting is used when not yet filed/paid.
- **Status & priority badges:** color-coded; status text renders with underscores replaced by spaces (e.g. `PENDING ADMIN APPROVAL`). Statuses: Draft, Pending Admin Approval, Pending Review, Pending Preparation, Prepared, Pending Approval, Approved, Rejected, Filed, Paid, Closed.

## 7.2 Actions

- **Header:** **+ Add Ad-hoc Templates** → the ad-hoc page; **+ Add Recurring Templates** → the recurring-template create page. Both shown to admins and preparers.
- **Row menu:** **View** (all roles); **Edit** (admin/preparer); **Delete** (admin only, confirmed; hard delete that also removes assignments/approvals/comments/attachments).
- **Empty state:** "No compliance items found" with **+ Add Recurring Templates** and **+ Add Ad-hoc Templates** buttons.

## 7.3 Acceptance criteria

1. The tracker lists all org compliance items, newest activity reflected in due-date ordering, filterable by status/priority/country/entity and searchable by ID.
2. Filing/payment due cells communicate urgency (overdue red, ≤3 days orange) and hide hints once filed/paid.
3. Row actions are role-appropriate: view for all, edit for admins/preparers, delete for admins only.
4. The tracker surface always offers paths to add both recurring (via templates) and ad-hoc items, including from the empty state.

---

# 8. Compliance Lifecycle, Approvals & Payments (Authoritative Chapter)

This chapter is the single source of truth for compliance states and transitions. Other chapters reference it. A compliance item is tracked by its **status**, its **preparer assignment**, its **approval records**, its **payment confirmations**, and its **filed/paid timestamps**.

## 8.1 States

| Status | Meaning |
|---|---|
| `DRAFT` | Created (manual or imported); not yet routed. Only for non-template items. |
| `PENDING_ADMIN_APPROVAL` | Submitted to admins for the pre-preparation gate. |
| `PENDING_REVIEW` | Sent by an admin to a named reviewer for the pre-preparation gate. |
| `PENDING_PREPARATION` | Approved for preparation; assigned preparer works on the filing. |
| `PREPARED` | (Legacy/seed state) preparer indicates work done. Rarely written today. |
| `PENDING_APPROVAL` | Submitted by the preparer; awaiting step-1 (and then step-2) approval. |
| `APPROVED` | All approval steps complete; ready to file/pay. |
| `REJECTED` | An approver rejected the submission. |
| `FILED` | Filing recorded (with filing date). |
| `PAID` | Payment recorded (with payment date/amount/reference). |
| `CLOSED` | Filed and (if payment required) paid; administratively closed. |

## 8.2 Two gates — important mental model

TaxFlow has **two distinct approval mechanisms** that act at different phases:

1. **The pre-preparation gate** (only for non-template items: `source` MANUAL or IMPORT). Items created/imported in **Draft** must be cleared before preparation:
   - Preparer/creator: **Submit to Admin** → `PENDING_ADMIN_APPROVAL`.
   - Admin: **Approve** → `PENDING_PREPARATION` (preparer notified "ready for preparation"), **Send to Reviewer** → `PENDING_REVIEW`, or **Reject**.
   - Assigned reviewer: **Approve** → `PENDING_PREPARATION`, or **Reject**.
   - **Template-generated items skip this gate entirely** (created directly in `PENDING_PREPARATION`); these admin/reviewer actions are refused for them ("Template-sourced compliances are approved through the template").

2. **The submission & approval flow** (`approvalFlow`: NONE / ONE_LEVEL / TWO_LEVEL) governs sign-off of the *prepared submission*:
   - Preparer: **Submit for Approval** (with payment details) → `PENDING_APPROVAL` when approval records exist, or straight to `APPROVED` when the flow is NONE (no records).
   - Step approvals happen in order (step 1 reviewer, then step 2 approver for two-level).
   - This is where the **amount confirmation chain** is enforced for payment filings (see 8.6).

Flow resolution (which flow applies) is decided at creation/edit in this precedence: **user's explicit choice on the item > the Form master's flow > the Filing Entity's flow > default ONE_LEVEL.**

## 8.3 The state machine

Allowed transitions and the actor/who rules. "Assigned preparer" = the person on the item's assignment record; "assigned reviewer" = `reviewerId` on the item; approvers = the people recorded in `compliance_approvals` (the "approval records").

| From | Action (button) | To | Who may (server-enforced) |
|---|---|---|---|
| DRAFT | **Submit to Admin** | PENDING_ADMIN_APPROVAL | Any user (UI: preparer/creator). Notifies org admins. |
| DRAFT / PENDING_ADMIN_APPROVAL | **Approve** (admin approve) | PENDING_PREPARATION | Admin. Notifies preparer. Non-template only. |
| DRAFT / PENDING_ADMIN_APPROVAL | **Send to Reviewer** | PENDING_REVIEW | Admin. Chooses reviewer; reviewer notified. Non-template only. |
| PENDING_REVIEW | **Approve** (reviewer approve) | PENDING_PREPARATION | The assigned reviewer (identity check). Notifies preparer. Non-template only. |
| PENDING_PREPARATION / PREPARED | **Submit for Approval** | PENDING_APPROVAL (or APPROVED if no approval records) | Any user (UI: preparer). Captures filing/payment details; records the preparer amount confirmation. Notifies step-1 approvers. |
| PENDING_APPROVAL | **Approve** (step approve) | stays PENDING_APPROVAL until all records approved, then APPROVED | The current step's approver (recorded approverId; UI also checks ordering). Records amount reconfirmation for that step. Notifies preparer and next-step approvers. |
| PENDING_APPROVAL | **Reject** | REJECTED | A recorded approver (comments required). Notifies preparers with reason. |
| REJECTED | **Resubmit** | PENDING_APPROVAL | Any user (UI: preparer). Resets all approval records to pending; refreshes submitted-at; notifies approvers. |
| APPROVED | **File** | FILED | Any user (UI: admin/manager). Records optional filing date (default today). |
| APPROVED / FILED | **Mark Paid** | PAID | Assigned preparer, admin, or manager. Records payment date/reference/method/notes; requires payment confirmation. Non-payment items excluded. |
| FILED / PAID | **Close** | CLOSED | Admin or manager. Requires filed + (if payment required) paid. |
| APPROVED / PAID | (File after paid) | FILED | as File above — filing and payment may happen in **either order**. |
| DRAFT / PENDING_ADMIN_APPROVAL | **Bulk approve** (ad-hoc page) | PENDING_PREPARATION (or PENDING_REVIEW if a reviewer is supplied) | Admin. Skips template-sourced items. |
| any | **Edit (PUT)** | (arbitrary, incl. status) | Any authenticated user (see 8.9). |
| any | **Delete** | — | Admin. |

Notes:
- **Reject during the admin/reviewer gate** (PENDING_ADMIN_APPROVAL or PENDING_REVIEW) is offered in the UI, but today only the PENDING_APPROVAL rejection endpoint exists server-side; gate-stage rejections currently fail. (Appendix F.)
- `PREPARED` is accepted as a from-state for submit but is effectively never set by the running product.
- Filing and payment may be recorded in **either order** (File-then-Paid or Paid-then-File); **Close** only appears once both applicable steps are done.

## 8.4 The approval records model

- Approval records live per compliance (one row per person) with a **step** number and status:
  - Flow NONE → no records.
  - Flow ONE_LEVEL → one record: step 1 = the Reviewer.
  - Flow TWO_LEVEL → two records: step 1 = Reviewer, step 2 = Approver.
- Records are created when the item is created (or imported/generated/edited) based on the effective flow and chosen people.
- Step **1 must be approved before step 2** can act ("Previous approval step must be completed first").
- An approver who is not yet an org member is auto-added as a member with a matching role so the approval can proceed.
- On the detail page the Approvers card lists each step as "Step {n} (Reviewer/Approver): {name}" with its status.

## 8.5 Submission & payment details

At **Submit for Approval** (and Resubmit), the preparer supplies the filing's financial details:

- **Filing Type:** Payment / NIL Return / Refund Return.
  - Payment: a non-negative amount in a currency.
  - NIL Return: amount must be 0; no payment required.
  - Refund Return: amount plus a **Refund Type** — "Claimed from tax authority" or "Carried forward for adjustment".
- For items whose form has **Requires Payment = off**, submitting auto-records the filing as a **NIL Return** (amount 0) and no payment is needed.

## 8.6 Mandatory amount-confirmation chain

For payment filings, the amount is confirmed at **every** sign-off, and the chain must be complete before the respective milestone:

1. **Preparer submit** — amount entered (recorded automatically on submission).
2. **Reviewer** (step 1) — "reconfirm amount" checkbox mandatory before approving.
3. **Approver** (step 2) — "reconfirm amount" checkbox mandatory before approving.
4. **Preparer payment** — "I confirm the same amount has been paid" checkbox mandatory before Mark Paid.

If the required confirmation is missing, the server refuses the action ("Amount must be reconfirmed before approval" / "Payment must be confirmed before marking paid"). The detail page shows the **Amount Confirmations** list (each stage, who confirmed it, when).

> **As-built note.** Approving without a payment amount present is refused; the UI disables Approve until the submitted amount exists.

## 8.7 Bulk approval (ad-hoc)

- On the Ad-hoc page an admin may check multiple Draft/Pending-Admin-Approval items and **Approve Selected**:
  - With a reviewer → items move to `PENDING_REVIEW` (reviewer notified).
  - Without a reviewer → items move to `PENDING_PREPARATION` (preparers notified).
- Template-sourced items are skipped.

## 8.8 Rejection & resubmission

- **Reject** (at PENDING_APPROVAL): the acting approver must provide a reason (required). The item → `REJECTED`; preparers are notified with the reason.
- **Resubmit** (from REJECTED, by the preparer): all approval records are reset to pending (their previous action/comments cleared), `submittedAt` refreshed, the payment details re-validated/re-entered, and all approvers notified.

## 8.9 Editing a compliance item

The detail page's **Edit** opens the edit form. Editing can change details including entities, form, tax period, due dates, priority, preparer, reviewer/approver, and the approval flow:

- Changing the preparer re-assigns the assignment record.
- Changing the reviewer/approver or the approval flow **rebuilds the approval records** (existing records deleted and recreated from the new flow).
- When Requires Payment is turned off, the payment due date is cleared.
- If the status is changed through editing, the status change is recorded in the activity feed and audit log.

> **As-built note.** The edit screen itself does not restrict who may edit by role; the row **Edit** action is admin/preparer-oriented on the list, but the edit route is open to any authenticated viewer. See Appendix F.

## 8.10 Detail page (single compliance)

- **Header:** compliance ID, status badge, priority badge, created date, and an **Edit** action. Action buttons appear per role and status (the sets in 8.3).
- **Stat cards:** Entities (with filing-entity marker), Compliance Info (tax type, form, period+frequency, F Due and P Due with days-overdue/left hints, payment due shown only when payment applies), Preparer (assignment with start/completion), Approvers (each step + status).
- **Tabs:**
  - **Details** — Approval Flow Mechanism card (entity/form placeholders + active driving flow with "Flow Override Active" warning when they differ); the details grid (ID, country, period, frequency, due date, filing month, recurring flag/end date, status, source, priority, created/updated, reviewer, admin-approved, submitted, filed); **Payment Details** card (filing type, refund type, amount+currency, marked paid date, payment date/reference/method, amount confirmations) when the item requires payment and has data; notes.
  - **Timeline** — vertical activity timeline.
  - **Documents** — attachments list (with download) + upload.
  - **Comments** — threaded comments feed + composer.
  - **Audit Trail** — table of the recorded activity (from → to status) on the item.

## 8.11 Actions dialogs

Each action is presented through a modal that collects the action-specific inputs:
- **Approve/Send to Reviewer (admin gate):** pick a reviewer (pre-filled when one is assigned); locked if both reviewer & approver already chosen.
- **Submit/Resubmit:** payment section with filing type/amount/currency/refund type when payment applies.
- **Step Approve:** shows the submitted amount and requires the reconfirmation checkbox.
- **Reject:** reason field (mandatory).
- **File:** optional filing date ("Leave blank to use today's date").
- **Mark Paid:** payment date/reference/method/notes + confirmation checkbox.
- **Close:** confirmation only.

## 8.12 Acceptance criteria

1. Every transition in the state machine table above is reachable from the detail page for the right role/status, and refused (with an error) otherwise.
2. Template-generated items cannot be sent through the admin/reviewer gate; ad-hoc/imported Draft items must clear the gate before preparation.
3. One- and two-level flows create exactly the right approval records; step 2 cannot act before step 1; the final approval moves the item to Approved.
4. A nil-return (non-payment) filing requires no payment and can be filed; a payment/refund filing captures amount, currency, and (for refunds) refund type.
5. The amount-confirmation chain blocks approval and payment recording until each required confirmation is given.
6. Rejection requires a reason; resubmission resets approvals and notifies approvers; filing and payment can be recorded in either order; close requires both (when payment applies) and is admin/manager-only.
7. The detail page reflects all of the above in its cards, tabs, and action buttons.

---

# 9. Notifications, Activity & Audit

## 9.1 Notifications

Notifications inform users when their action is needed or an outcome they care about occurred. Recipients and patterns are defined in Appendix D. The Notification center is reached via `/notifications` and the header bell.

- **Notification center:** newest-first list with type icon (colored per type), title, message, and relative time. An **"{n} unread"** pill and **Mark all as read** appear when there are unread items.
- Clicking an unread item marks that item read (blue dot and bold weight removed). Clicking does not navigate to the referenced compliance (see as-built note).
- The header bell shows a static orange indicator (not a live count) linking to the center.

Event triggers (all link back to the compliance): compliance pending admin approval (admins), sent for review (reviewer), ready for preparation (preparers), submitted pending review (step-1 approvers), ready for your approval (next-step approver), approved/partially approved (preparers), rejected (preparers, with reason), resubmitted (approvers), and the template review-request/rejection notifications to creators. Template approval events notify the preparer/reviewer chain in the same way.

## 9.2 Activity & audit

- **Activity feed:** every lifecycle transition records an activity entry — actor, action, from-status → to-status, optional comment, timestamp. These render as the **Timeline** tab and the **Audit Trail** tab on the compliance detail page (both read the same per-item activity log; the Audit Trail tab shows it as a table).
- Recorded actions include: created, status changed, submitted to admin, admin approved, sent to reviewer, reviewer approved, submitted, approved (partial/full), rejected, resubmitted, filed, marked paid, closed, commented, recurring-generated.
- **Comment** activity: posting a comment also records a "commented" activity (first 100 chars).
- **A separate internal audit log** (`audit_trails`) is written by every route action for change/error analysis; it is not surfaced in the UI.

## 9.3 Acceptance criteria

1. Every action in Chapter 8 generates the corresponding notification to the people listed in Appendix D and records activity with from/to status.
2. The notification center shows unread counts, supports marking single items and all items as read, and timestamps items in relative form.
3. The detail page Timeline and Audit Trail tabs reflect the item's full activity history.
4. Marking a notification read does not alter any compliance data.

---

# 10. Dashboard, Reports, Calendar & Search

## 10.1 Dashboard (`/dashboard`)

The dashboard is the landing page after sign-in and is **role-aware** — the API returns a different metric payload per role (active role; fallback to the user's global role):

**Preparer dashboard**
- Stat cards: Assigned Tasks, Completed, Pending, Overdue, Due Today, Due This Week, Avg Turnaround.
- Charts/lists: **Monthly Progress** (completed vs pending, last 6 months, bar chart); **Pending vs Completed** (donut); **Upcoming Due Dates** (next 5, with due-date badges: "Nd overdue" / "Due today" / "Nd left"); **Recent Activity** (last 10 on assigned items).
- Scope: the preparer's own assignments.

**Approver dashboard**
- Stat cards: Pending Approval, Rejected, Approved Today, Avg Approval Time (hours).
- Charts/lists: **Approval Trend (Last 30 Days)** (line chart); **Pending by Country** and **Pending by Entity** (bar charts); **Recent Activities**.
- Scope: approvals the user is recorded on.

**Admin / Manager dashboard ("Executive Dashboard")**
- Stat cards: Total Compliances, Completed, Pending, Overdue, Filed Late, Paid Late, Rejected, Awaiting Approval, Avg Processing.
- Charts (org-wide): **Compliance Status** (pie); **Country Wise Compliance** (bar); **Compliance Source** (pie: TEMPLATE/MANUAL/IMPORT); **Entity Wise Compliance** (bar); **Tax Type Distribution** (pie); **Monthly Compliance Trend** (12-month area chart); **Employee Workload** (grouped bar); **Overdue Heat Map**; **Approval Bottlenecks**; **Top Delayed Countries/Entities**.
- A filter bar (All Countries/Entities/Tax Types/Types/Employees + period This Year/Quarter/Month/All Time) is present but does not currently re-query the API.
- **Definitions:** Completed = Filed or Approved (per-role defs vary slightly); Overdue = due date passed and not filed; Filed Late = filed after due date; Paid Late = paid after payment due date (payment items).

**Entry states:** a user with no org sees the **Create Organization** welcome; a user with orgs but no active selection is prompted to choose one.

## 10.2 Reports (`/reports`)

- **Report catalog** (14 card types — Appendix E): Compliance Register, Pending Compliance, Overdue Report, Employee Productivity, Approval TAT, Preparation TAT, Country Compliance, Entity Compliance, Audit Trail, Rejected Compliance, Compliance Source Breakdown, Monthly/Quarterly/Yearly Summary.
- **Export formats:** Excel (.xlsx), CSV (.csv), PDF (.pdf). Default Excel.
- **Filters:** Date From / Date To / Status / Priority (via a collapsible filter card). The report download includes whichever items match; the server also honors country/entity/compliance-type if supplied.
- **Export content:** a compliance register row set with columns including Compliance ID, Entity, Country, Currency, Compliance Type, Tax Type, Form, Tax Period, Frequency, Due Date, Payment Due Date, Requires Payment, Filing Date, **Filing Delay (days)**, Payment Date, **Payment Delay (days)**, Status, Priority, Source, Filing Type, Refund Type, Payment (local), **Payment (USD)**, Preparer, Approver.
- **USD conversion:** payment amounts are converted to USD using the exchange rate effective for the item's month (latest prior rate fallback) — Chapter 4.7.
- **Delay semantics:** Filing Delay = days from due date to filing date (blank when on time); Payment Delay = days from payment due date to payment date (blank when on time, "N/A" when no payment required).

> **As-built note.** The 14 report *types* mostly share one underlying register; only Compliance Source Breakdown returns a genuinely different dataset. See Appendix F.

## 10.3 Calendar (`/calendar`)

- **Views:** Month, Week, Agenda (default Month).
- Items are pinned to their **filing due date** (due-date only; payment due dates are not shown on the calendar).
- **Month view:** max 3 chips per day then "+N more"; other-month days dimmed; today ringed.
- **Agenda view:** upcoming items (due date ≥ today), oldest first, up to 50, each with an Overdue/Today badge where applicable.
- **Dot semantics (Month/Week):** green = Completed (Approved/Filed/Paid/Closed), red = Overdue or Rejected, orange = Due Today, blue = Pending. Legend shown.
- Data covers all org items.

> **As-built note.** Calendar chips appear clickable but do not navigate; and the data fetch requests "limit=100" which the API ignores (returns all org items).

## 10.4 Search (`/search`)

- A global search box in the header (placeholder "Search compliances, entities...") submits to the Search page; results are grouped by type with colored badges.
- Requires at least 2 characters. Search returns up to 10 per category: **Compliance Schedules** (by compliance ID, tax period, status, tax type/notes/entity matches — title shows ID, subtitle "Entity | Compliance Type (Tax Type)"), **Entities**, **Countries**, **Forms**, **Employees** (name/email/username).
- Each result links to its detail page.

> **As-built note.** Global search is currently not scoped to the active organization (searches all orgs' data). See Appendix F.

## 10.5 Acceptance criteria

1. The dashboard reflects the viewer's role (preparer/approver/manager) with the metrics and charts listed above, and correctly handles the no-org and no-active-org states.
2. Every report type in the catalog can be generated in each of the three formats and downloads a correctly named file; exports include delay and USD columns.
3. Calendar month/week/agenda views pin items to filing due dates with the correct dot colors.
4. Search finds compliance/entities/countries/forms/employees by the fields listed and links to their pages.

---

# 11. Settings, Application Shell & Cross-Cutting Behavior

## 11.1 Settings (`/settings`)

- **Profile card** — Full Name, Email, Username. Read-only (identity comes from LucidShare).
- **Account card** — Role dropdown (Administrator / Preparer / Reviewer / Approver) with live save ("Role updated successfully"); Department and Employee ID displayed read-only.

## 11.2 Application shell

- **Sidebar** groups and navigation are defined in Appendix A (Dashboard; Compliance Home → Obligations Tracker / Ad-hoc Templates / Recurring Templates; Master Data → Countries/Entities/Tax Types/Forms/Employees/Currencies/Exchange Rates; Reports; Calendar View; Notifications; Search; Settings).
- **Org Switcher** at the top switches the active organization and shows per-org role pills when the user holds multiple roles in the org.
- **Footer user block** shows avatar/name/email/role and **Sign Out**.
- **Header** shows the current page title, mobile menu, a global search box, the notifications bell, and a user menu (Profile/Settings, Role submenu, Sign Out).
- The sidebar can collapse to an icon rail (persisted preference).
- **Branding:** "TaxFlow — Compliance Platform"; light cream/orange "Lucid" theme; no dark mode.
- The Master Data area shows an in-page tab bar (Countries / Entities / Forms / Employees / Exchange Rates) beneath its heading.

## 11.3 Cross-cutting behaviors

- Active-org data scoping for all org-scoped modules (compliance, entities, currencies, forms, templates, employees, KPI).
- Role-driven action availability throughout the UI (buttons appear/hide by role and status).
- Consistent confirm-on-delete, toast feedback, skeletons while loading, empty states with next actions, and a max-content-width layout.

## 11.4 Acceptance criteria

1. Settings shows profile (read-only) and account role change; saving a role updates the user's global role and shows confirmation.
2. The shell's navigation matches Appendix A; org/role switching updates the active context and re-renders data accordingly.
3. All destructive actions require confirmation and report success/failure via toast.

---

# Appendix A — Navigation Map

| Group | Item | Route |
|---|---|---|
| — | Dashboard | `/dashboard` |
| Compliance Home | Obligations Tracker | `/compliance` |
| Compliance Home | ├ Ad-hoc Templates | `/compliance/ad-hoc` |
| Compliance Home | └ Recurring Templates | `/master/compliance-templates` |
| Master Data | Countries | `/master/countries` |
| Master Data | Entities | `/master/entities` |
| Master Data | Tax Types | `/master/tax-types` |
| Master Data | Forms | `/master/forms` |
| Master Data | Employees | `/master/employees` |
| Master Data | Currencies | `/master/currencies` |
| Master Data | Exchange Rates | `/master/exchange-rates` |
| — | Reports | `/reports` |
| — | Calendar View | `/calendar` |
| — | Notifications | `/notifications` |
| — | Search | `/search` |
| — | Settings | `/settings` |

(Other routes: `/login`; compliance detail `/compliance/{id}`, edit `/compliance/{id}/edit`; template detail `/master/compliance-templates/{id}`, create, edit.)

# Appendix B — Role / Permission Matrix

Legend: ✅ full, ◐ partial/conditional, ❌ none. "Workflow" rows depend on assignment identity, not role alone.

| Capability | Admin | Manager | Preparer | Reviewer | Approver |
|---|---|---|---|---|---|
| Create organization | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage org members & roles | ✅ | ❌ | ❌ | ❌ | ❌ |
| Maintain master data (countries/entities/currencies/rates/forms) | ✅ | ◐ view | ◐ view | ◐ view | ◐ view |
| Add ad-hoc / recurring compliance entries | ✅ | ❌ | ✅ | ❌ | ❌ |
| Create/edit/approve/activate/delete **templates** | ✅ | ❌ | ◐ (create only) | ◐ (assigned review/approve) | ❌ |
| Generate compliance from templates | ✅ | ❌ | ❌ | ❌ | ❌ |
| Submit to admin (gate) — own/manual item | ✅ | ◐ | ✅ | ◐ | ◐ |
| Approve/send-to-reviewer (gate) | ✅ | ❌ | ❌ | ◐ assigned reviewer | ❌ |
| Prepare & submit for approval | ◐ | ❌ | ✅ (assigned) | ❌ | ❌ |
| Approve step 1/2 | ❌ | ❌ | ❌ | ◐ assigned step-1 | ◐ assigned step-2 |
| Reject submission | ❌ | ❌ | ❌ | ◐ assigned step | ◐ assigned step |
| Resubmit rejected item | ❌ | ❌ | ✅ (preparer) | ❌ | ❌ |
| Record **file** | ✅ | ✅ | ✅ (assigned preparer) | ❌ | ❌ |
| Record **payment** | ✅ | ✅ | ✅ (assigned preparer) | ❌ | ❌ |
| **Close** item | ✅ | ✅ | ❌ | ❌ | ❌ |
| Bulk approve ad-hoc | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete compliance | ✅ | ❌ | ❌ | ❌ | ❌ |
| Edit compliance item | ✅ | ◐ (via URL) | ✅ | ◐ (via URL) | ◐ (via URL) |
| Org-wide Executive Dashboard | ✅ | ✅ | ❌ (own work) | ❌ (org-wide fallback) | ❌ (own approvals) |
| Reports/Calendar/Search | ✅ | ✅ | ✅ | ✅ | ✅ |
| Change own global role | ✅ | ❌ (not offered) | ✅ | ✅ | ✅ |

> Notes: "Reviewer" and "Approver" columns describe users holding those roles; workflow steps also depend on being the *assigned* person. Users not assigned to an item and not holding an action role see the item read-only on the detail page.

# Appendix C — Compliance Status Flow

```
                            ┌───────────── ad-hoc/manual/import only ─────────────┐
   CREATE ──► DRAFT ──► PENDING_ADMIN_APPROVAL ──► PENDING_REVIEW ──► ─┐          │
   (manual/import)        │  (admin)                    (reviewer)    ▼          │
                          └──────► PENDING_PREPARATION ◄─────────── admin approve/send-reviewer approve
                                          │
        TEMPLATE-generated ────────────────┘        PREPARED (legacy)
                                          │              │
                                          ▼              ▼
                                   (preparer) SUBMIT for approval
                                          │
                   NONE flow (no records)  │  ONE/TWO-LEVEL (records exist)
                                          ▼              ▼
                                        APPROVED ◄── PENDING_APPROVAL ──► REJECTED
                                                      (step1→step2)           │
                                          │                                   │ resubmit
                                          │  ◄────────────────────────────────┘
                          ┌───────────────┴────────────────┐
                          ▼                               ▼
                     (mark paid) PAID ◄──► FILED (file)   (either order)
                          │              │
                          └──────► CLOSED (admin/manager; filed + paid when payment applies)
```

# Appendix D — Notification Events

| Event | Recipients | Title | Link |
|---|---|---|---|
| Submitted to admin (gate) | Org admins (excluding actor) | Compliance Awaiting Admin Approval | `/compliance/{id}` |
| Sent to reviewer (gate) | Chosen reviewer | Compliance Sent for Your Review | `/compliance/{id}` |
| Admin/reviewer approved (gate) | Assigned preparer(s) | Compliance Ready for Preparation | `/compliance/{id}` |
| Submitted for approval | Step-1 approvers | Compliance Pending Review | `/compliance/{id}` |
| Step approved (not final) | Next-step approver(s) | Compliance Ready for Approval | `/compliance/{id}` |
| Step approved (final) | Assigned preparer(s) | Compliance Approved / Partially Approved | `/compliance/{id}` |
| Rejected | Assigned preparer(s) | Compliance Rejected (reason embedded) | `/compliance/{id}` |
| Resubmitted | All recorded approvers | Compliance Resubmitted | `/compliance/{id}` |
| Template sent for review | Assigned template reviewer | Template Review Requested | — |
| Template rejected | Template creator | Template Rejected | — |

(Filing, marking paid, and closing do not send notifications.)

# Appendix E — Report Catalog

| Card | Purpose label | Content |
|---|---|---|
| Compliance Register | All tracked compliance | Register rows (Chapter 10.2) |
| Pending Compliance | Items not completed | Register rows (pending states as filtered) |
| Overdue Report | Overdue items | Register rows (overdue as filtered) |
| Employee Productivity | Work by person | Register rows grouped by preparer |
| Approval TAT | Approval turnaround | Register rows incl. approval data |
| Preparation TAT | Preparation turnaround | Register rows |
| Country Compliance | By country | Register rows |
| Entity Compliance | By entity | Register rows |
| Audit Trail | Recorded activity | Register rows |
| Rejected Compliance | Rejected items | Register rows |
| Compliance Source Breakdown | Source distribution | Source/Status/Count table |
| Monthly / Quarterly / Yearly Summary | Period summaries | Register rows |

> All formats export via the selected type's default file name `{type}-{timestamp}.{ext}`.

# Appendix F — As-Built Notes & Gaps

Behavioral observations worth confirming with the product owner before relying on them:

1. **Reject during the admin/reviewer gate is offered but fails.** The UI shows Reject at Pending Admin Approval / Pending Review, but the reject endpoint only accepts items in Pending Approval, so those rejections error out.
2. **Gate-stage approvals don't record an "admin approved" timestamp/comment** on the compliance (the field exists and is displayed but is never written by any action).
3. **Edit is not role-restricted server-side**; any authenticated user who knows the URL can edit any compliance item (including changing status), though the UI only shows Edit for admins/preparers.
4. **Submit/resubmit/submit-to-admin/file have no server-side role checks** — a caller could trigger them for states that allow them regardless of identity (status gating still applies).
5. **Global role self-service:** any signed-in user can set their own global role (e.g., Administrator) via Settings/header; org-scoped membership roles are the actual access key for admin actions, so an org-admin must grant membership roles.
6. **Reports** largely share one register dataset regardless of chosen report type (only Compliance Source Breakdown differs); no role or org scoping on the reports endpoint; UI hides country/entity/compliance-type filter controls the API supports.
7. **Manager/Admin dashboard filters and period selector are cosmetic** (charts are org-wide regardless of selection); Avg Turnaround and Avg Processing always display 0.
8. **Calendar chips are not clickable**, and the calendar fetch is not limited to 100 despite the request.
9. **Search is not org-scoped** and calendar/report data is likewise not org-filtered at the source.
10. **Notifications don't navigate** on click (they only mark read), though each carries a link to its compliance.
11. **Attachment version/stage** are supported by the data model and shown in the UI as `v1`, but no flow ever increments the version or sets a stage.
12. **Marking paid** records payment date/reference/method/notes but never refund amount/reference (fields exist but are unused).
13. **No "Prepared" producer:** the Prepared status appears in filters and is accepted as a submit from-state but is never set by the product at runtime.
14. **Membership role inconsistencies:** assigning a reviewer via some paths auto-grants them an "APPROVER" org role rather than "REVIEWER", and the DB role enum lacks a REVIEWER value (REVIEWER exists only as app-level text).

---

*End of specification.*
