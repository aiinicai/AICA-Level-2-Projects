# PROMPT FOR GOOGLE AI STUDIO — "MediCore Connect" Healthcare ERP (Financials + Supply Chain)

## 0. ROLE AND OBJECTIVE

You are a principal software architect and a chartered accountant (20+ years in ERP consulting, Oracle Fusion Cloud Financials style implementations, IFRS reporting). Build a **fully working, browser-based ERP application** called **MediCore Connect** for **Meridian Healthcare Group**, a healthcare group with **5 hospitals, 5 clinics and 5 pharmacies**.

It must look and behave like an Oracle Fusion Cloud-style home page with module tabs, quick actions and app tiles, but with its own original branding and colour scheme (section 2). Every module must be functional end to end: transactions are created, submitted by a Maker, approved by a Checker, accounted, and posted to the General Ledger. The Trial Balance and IFRS financial statements must always agree to the penny.

**Non-negotiable quality rules**
1. No placeholder screens, "coming soon" buttons, lorem ipsum or dead links. Every tile, quick action, button and menu item must open a working screen.
2. Accounting must be correct: every journal balances, subledgers reconcile to GL control accounts, the Trial Balance balances, and the Balance Sheet balances.
3. The app must ship with rich, realistic, internally consistent seeded data (section 12), created by running transactions through the same posting engine the UI uses.
4. Build for real use: validation, error messages, empty states, loading states, confirmation dialogs, audit trail.
5. If the full app cannot fit in one response, build in the phases of section 15. Finish each phase completely before starting the next and end with "Ready for Phase N". Never stub a feature to save space.

---

## 1. TECHNOLOGY

- React 18 + TypeScript + Vite, Tailwind CSS, React Router (hash router), Zustand for state, Recharts for charts, lucide-react for icons.
- No backend. Persist everything in IndexedDB (via `idb-keyval` or `localforage`) with a repository layer, so a real API can replace it later. Provide a **Reset Demo Data** button (Tools → Administration) that re-seeds.
- Use `decimal.js` (or integer fils) for all money maths. Never use floating-point sums for accounting. Round to 2 decimals. Currency AED; show amounts as `1,234,567.89`; negatives in brackets in reports.
- Excel export with `xlsx` (SheetJS), PDF export with `jspdf` + `jspdf-autotable`, CSV export natively. Every report page offers **Download Excel / PDF / CSV** and **Print**.
- Date format `DD/MMM/YYYY` (e.g. 19/Oct/2026). Fiscal year = calendar year. "Today" for the demo is **19/Oct/2026**, current open period **Oct-26**.
- Code structure: `/src/core` (posting engine, sequences, approvals, auth, periods), `/src/data` (COA, seed, repositories), `/src/modules/<module>`, `/src/reports`, `/src/components` (shared table, dialogs, forms), `/src/pages`. Keep files small and cohesive.

---

## 2. LOOK AND FEEL (replicate the layout of the reference screenshots, but not their colours, name or logo)

**Do NOT use blue or teal anywhere** (including links, focus rings, charts). Use this palette:

- Primary: deep plum `#5B2C83`; primary dark `#3F1D5C`; primary light `#EDE4F5`
- Accent: warm amber `#E8A317`
- Neutral: slate/warm greys `#1F2937, #4B5563, #9CA3AF, #E5E7EB, #F9FAFB`
- Status: success emerald `#059669`, warning amber `#D97706`, error rose `#DC2626`, info violet `#7C3AED`
- Chart palette: plum, amber, emerald, rose, orange, slate, violet, olive (no blue)

**Branding:** logo text "MediCore Connect" with a small original SVG mark (a plus sign inside a hexagon). Do not copy any real company's logo or name.

**Global header (dark plum bar):** hamburger menu (opens a slide-out navigator listing all modules and apps), logo, then on the right: Home icon, Favourites (star, saves tiles/pages), Tasks/Worklist (flag), Notifications (bell with count of pending approvals), user avatar menu (profile, Switch User for demo, Sign Out).

**Home page:** a plum gradient hero with subtle pattern. Greeting "Good morning / afternoon / evening, Charlotte Davis" based on local time. Below it a horizontally scrollable **tab strip with left/right arrows** with these tabs:

`Procurement | Supply Chain Execution | Payables | Receivables | General Accounting | Intercompany Accounting | Cash Management | Fixed Assets | Reports | Tools`

Each tab shows two panels exactly like the reference:
- **QUICK ACTIONS** (left): icon + label list with "Show More".
- **APPS** (right): frosted square tiles with icon and label, plus a "+" tile to add a favourite app.
- Below: **Things to Finish** cards (live counts: pending approvals, incomplete items, unreconciled items) that deep-link into the relevant work area.

**Work area pages** (e.g. Payables → Invoices, Fixed Assets → Assets):
- Page title with help icon and a business unit selector ("All Business Units" default).
- A row of **summary tiles** (counts/amounts by status, clickable to filter the table below), each with a dark footer chevron to expand.
- A **data table** with toolbar: Actions menu, View menu (column chooser), Freeze, Wrap, **Detach**, and action buttons. Sortable columns, column filters, pagination, row warning icons for exceptions, row selection, and drill-down links.
- A **right-side icon rail**: Tasks panel (links to related quick tasks), Search panel (advanced search form), Reports/Analytics panel (charts).
- Responsive and keyboard friendly.

**Maker–Checker visibility:** every transaction page shows status chips (Draft, Pending Approval, Approved, Posted, Rejected, Cancelled, Reversed), Created By / Approved By, and an **Audit Trail** tab (who did what, when, comments).

---

## 3. AUTHENTICATION, USERS AND ROLES

**Sign-in page** (plum split screen with the logo): User ID, Password, Show/Hide password, "Sign In" button, and a **"Demo credentials"** helper box that lists the accounts below (click to autofill). Invalid login shows an error. Session persists until sign-out.

| User | Role | User ID | Password | Approval limit (AED) |
|---|---|---|---|---|
| **Charlotte Davis** (primary demo user) | Finance Controller: Maker for all modules, Checker for items created by others, GL accountant, report access | `charlotte.davis` | `Charlotte@2026` | 250,000 |
| Daniel Reed | CFO: Checker, unlimited limit, period close | `daniel.reed` | `Daniel@2026` | Unlimited |
| Omar Haddad | AP Maker | `omar.haddad` | `Omar@2026` | n/a |
| Sofia Marin | AR Maker | `sofia.marin` | `Sofia@2026` | n/a |
| Liam Carter | Procurement Maker / Buyer | `liam.carter` | `Liam@2026` | n/a |
| Aisha Khan | Treasury Maker (cash, bank rec) | `aisha.khan` | `Aisha@2026` | n/a |
| Henry Brooks | Fixed Asset Accountant | `henry.brooks` | `Henry@2026` | n/a |

**Segregation of duties (enforced in code, not only in the UI):**
- A user can never approve a transaction they created, and the Approve button is disabled with an explanatory tooltip.
- If the transaction amount exceeds the approver's limit, show "Exceeds your approval limit; escalate to CFO", and the status becomes "Pending Higher Approval".
- Makers can edit Draft and Rejected items only. Pending, Approved and Posted items are read-only.
- Posted records are never edited or deleted; use **Reverse** (creates an opposite entry with a reason) or **Credit Memo**.
- Add a **Switch User** option in the avatar menu (demo convenience) so a reviewer can switch to Daniel Reed to approve Charlotte's items without logging out.

---

## 4. ORGANISATION: 15 BUSINESS UNITS

Each unit is a balancing segment in the GL. Currency AED. Maintain a Business Unit master (code, name, type, emirate, VAT TRN, status).

| Code | Name | Type |
|---|---|---|
| H01–H05 | Meridian Hospital Abu Dhabi, Dubai, Sharjah, Al Ain, Ras Al Khaimah | Hospital |
| C01–C05 | Meridian Clinic Khalifa City, Jumeirah, Al Nahda, Al Jimi, Al Nakheel | Clinic |
| P01–P05 | Meridian Pharmacy Corniche, Marina, Muweilah, Al Ain Mall, Julphar Road | Pharmacy |

Every transaction carries a Business Unit. Users see "All Business Units" or a single unit everywhere. Report parameters also offer group selections: All Hospitals, All Clinics, All Pharmacies, All Units.

---

## 5. CHART OF ACCOUNTS (IFRS-mapped) AND GL STRUCTURE

GL accounting flexfield: **Business Unit – Natural Account – Department (optional)**. Seed departments: Clinical, Pharmacy, Laboratory, Radiology, Administration, Facilities, IT, Procurement. Each account has: code, name, type (Asset/Liability/Equity/Revenue/Expense), normal balance, **IFRS statement line**, current/non-current flag, control-account flag (subledger-only), active flag.

**Control accounts (blocked for manual journals except by the system or Intercompany): 1100, 1110, 1120, 1200–1230, 1500, 1610, 2000, 2010, 2500, and the accumulated depreciation accounts.**

| Acct | Name | Type | IFRS line |
|---|---|---|---|
| 1000 | Main Cash on Hand | Asset | Cash and cash equivalents |
| 1010 | Petty Cash | Asset | Cash and cash equivalents |
| 1020 | Bank – Operating Account | Asset | Cash and cash equivalents |
| 1030 | Bank – Collections Account | Asset | Cash and cash equivalents |
| 1040 | Cash in Transit | Asset | Cash and cash equivalents |
| 1100 | Trade Receivables – Patients (AR control) | Asset | Trade receivables |
| 1110 | Trade Receivables – Insurance (AR control) | Asset | Trade receivables |
| 1120 | Trade Receivables – Corporate & Other (AR control) | Asset | Trade receivables |
| 1190 | Allowance for Expected Credit Losses (contra) | Asset | Trade receivables |
| 1200 | Inventory – Pharmaceuticals | Asset | Inventories |
| 1210 | Inventory – Medical Consumables | Asset | Inventories |
| 1220 | Inventory – Implants & Surgical | Asset | Inventories |
| 1230 | Inventory – General Stores | Asset | Inventories |
| 1300 | Prepayments | Asset | Prepayments and other receivables |
| 1310 | Advances to Suppliers | Asset | Prepayments and other receivables |
| 1320 | Deposits and Other Receivables | Asset | Prepayments and other receivables |
| 1400 | VAT Input Recoverable | Asset | Prepayments and other receivables |
| 1500 | Intercompany Receivable (Due from units) | Asset | Due from related units (eliminated on consolidation) |
| 1600 | Capital Work in Progress | Asset | Property, plant and equipment (CWIP) |
| 1610 | Asset Clearing – Pending Capitalisation | Asset | Property, plant and equipment (CWIP) |
| 1700 | PPE – Land | Asset (NC) | Property, plant and equipment |
| 1710 | PPE – Buildings | Asset (NC) | Property, plant and equipment |
| 1720 | PPE – Leasehold Improvements | Asset (NC) | Property, plant and equipment |
| 1730 | PPE – Medical Equipment | Asset (NC) | Property, plant and equipment |
| 1740 | PPE – Furniture and Fixtures | Asset (NC) | Property, plant and equipment |
| 1750 | PPE – IT Equipment | Asset (NC) | Property, plant and equipment |
| 1760 | PPE – Vehicles | Asset (NC) | Property, plant and equipment |
| 1770 | PPE – Plant, HVAC and Electrical | Asset (NC) | Property, plant and equipment |
| 1810–1870 | Accumulated Depreciation for 1710, 1720, 1730, 1740, 1750, 1760, 1770 (1810 = Buildings … 1870 = Plant/HVAC) | Contra (NC) | Property, plant and equipment |
| 2000 | Trade Payables (AP control) | Liability | Trade and other payables |
| 2010 | Goods Received Not Invoiced (GRNI) | Liability | Trade and other payables |
| 2020 | Accrued Expenses | Liability | Trade and other payables |
| 2100 | VAT Output Payable | Liability | Trade and other payables |
| 2200 | Accrued Salaries and Staff Payables | Liability | Trade and other payables |
| 2210 | End of Service Benefits Provision | Liability (NC) | Employee benefits provision |
| 2300 | Patient Deposits and Deferred Revenue | Liability | Contract liabilities |
| 2400 | Corporate Tax Payable | Liability | Current tax liability |
| 2500 | Intercompany Payable (Due to units) | Liability | Due to related units (eliminated on consolidation) |
| 2600 | Lease Liabilities | Liability | Lease liabilities |
| 2700 | Bank Loan – Current Portion | Liability | Borrowings (current) |
| 2710 | Bank Loan – Non-current | Liability (NC) | Borrowings (non-current) |
| 3000 | Share Capital | Equity | Share capital |
| 3100 | Retained Earnings | Equity | Retained earnings |
| 3200 | Statutory Reserve | Equity | Reserves |
| 4000 | Inpatient Revenue | Revenue | Revenue from contracts with customers |
| 4010 | Outpatient Revenue | Revenue | Revenue from contracts with customers |
| 4020 | Surgery and Procedures Revenue | Revenue | Revenue from contracts with customers |
| 4030 | Laboratory and Radiology Revenue | Revenue | Revenue from contracts with customers |
| 4040 | Pharmacy Sales – Retail | Revenue | Revenue from contracts with customers |
| 4050 | Pharmacy Sales – Insurance | Revenue | Revenue from contracts with customers |
| 4060 | Clinic Consultation Revenue | Revenue | Revenue from contracts with customers |
| 4090 | Discounts and Contractual Adjustments (contra) | Revenue | Revenue from contracts with customers |
| 4900 | Intercompany Service Revenue | Revenue | Eliminated on consolidation |
| 4950 | Other Income | Revenue | Other income |
| 5000 | Cost of Medicines Sold | Expense | Cost of sales |
| 5010 | Medical Consumables Consumed | Expense | Cost of sales |
| 5020 | Implants and Surgical Items Consumed | Expense | Cost of sales |
| 5030 | Inventory Adjustments, Expiry and Shrinkage | Expense | Cost of sales |
| 5040 | Purchase Price Variance | Expense | Cost of sales |
| 5100 | Clinical Staff Costs | Expense | Cost of sales |
| 5110 | Doctors' Professional Fees | Expense | Cost of sales |
| 6000 | Administrative Salaries | Expense | Administrative expenses |
| 6100 | Rent Expense | Expense | Administrative expenses |
| 6110 | Utilities | Expense | Administrative expenses |
| 6120 | Repairs and Maintenance | Expense | Administrative expenses |
| 6130 | Cleaning and Housekeeping | Expense | Administrative expenses |
| 6140 | Security Services | Expense | Administrative expenses |
| 6150 | Insurance Expense (Malpractice and Property) | Expense | Administrative expenses |
| 6200 | Office Supplies and Stationery | Expense | Administrative expenses |
| 6220 | Communication and Internet | Expense | Administrative expenses |
| 6230 | Travel and Transport | Expense | Administrative expenses |
| 6240 | Hospitality and Staff Welfare | Expense | Administrative expenses |
| 6250 | Professional and Consulting Fees | Expense | Administrative expenses |
| 6260 | Marketing and Advertising | Expense | Selling and distribution expenses |
| 6270 | Bank Charges | Expense | Administrative expenses |
| 6280 | Licences and Regulatory Fees | Expense | Administrative expenses |
| 6290 | Miscellaneous Expenses | Expense | Administrative expenses |
| 6300 | Depreciation Expense | Expense | Administrative expenses (disclose in notes) |
| 6310 | Expected Credit Loss Expense | Expense | Impairment losses on financial assets |
| 6320 | Medical Waste Disposal | Expense | Administrative expenses |
| 6400 | Intercompany Service Charge Expense | Expense | Eliminated on consolidation |
| 7000 | Finance Costs | Expense | Finance costs |
| 7100 | Gain/Loss on Disposal of Assets | Expense/Income | Other income / other expenses |
| 7200 | Foreign Exchange Gain/Loss | Expense/Income | Other income / other expenses |
| 7300 | Corporate Tax Expense | Expense | Income tax expense |

**Tax codes:** VAT 5% Standard; VAT 0% Zero-rated (many healthcare services and qualifying medicines); VAT Exempt; Out of Scope. Each AR/AP line has a tax code. VAT Input posts to 1400, VAT Output to 2100.

---

## 6. CORE ENGINE (build this first and use it everywhere)

### 6.1 Transaction lifecycle (all modules)
`Draft → Pending Approval → Approved → Posted (accounted and transferred to GL)`; side states: `Rejected` (returns to the maker with a mandatory reason, editable and resubmittable), `Cancelled` (drafts only; the number is retained as CANCELLED so there are no gaps), `Reversed`.

**On Approval, the engine automatically runs Create Accounting and posts to the GL in one atomic unit** (all-or-nothing). If accounting fails (closed period, missing account, imbalance), the status becomes **Approved – Accounting Error** with the reason visible, the item appears under Things to Finish, and a **Create Accounting** quick action retries it. Every subledger transaction has a **View Accounting** button showing the subledger journal lines and a link to the GL journal.

### 6.2 Posting engine API (single source of truth)
```ts
createAccounting(txn): SubledgerEntry   // builds balanced lines from the posting templates in section 7
postToGL(entry): GLJournal              // validates, assigns journal number, updates balances
reverseJournal(journalId, reason, date)
```
Validations in `postToGL`: debits equal credits to the fil; each line has valid BU and account; account active and not blocked; the period is **Open**; no manual use of control accounts; the journal date is within the period; amounts non-zero; the source document is not already posted (idempotent). Every posted line stores: journal number, period, BU, account, department, debit, credit, description, source module, source document number and id, created by, approved by, posted date.

### 6.3 Gapless sequential numbering
A sequence service issues numbers atomically per document type and fiscal year, shown as `PREFIX-YYYY-NNNNNN`: REQ, PO, RCV, PINV (AP invoice), PCM (AP credit memo), PAY (AP payment), RINV (AR invoice), RCM (AR credit memo), RCT (AR receipt), PCV (petty cash voucher), MCV (main cash voucher), CTR (cash transfer), BST (bank statement), FAB (asset addition batch), ICI (IC invoice), ICC (IC credit note), ICJ (IC journal), JV (manual journal), STO (stock transfer), ADJ (inventory adjustment). Number is assigned on save of a new transaction (the user sees it immediately, not editable). Fixed assets get tag numbers `FA-000001`. The supplier's own invoice number is a separate field with duplicate detection (same supplier + same invoice number → block).

### 6.4 Periods
Period master Jan-26…Dec-26. Seed: Jan–Sep **Closed**, Oct-26 **Open**, Nov–Dec **Future**. Period Close page (General Accounting → Period Close) shows a close checklist per module (unapproved transactions, unposted items, unreconciled bank statements, depreciation run, IC reconciliation) and lets the CFO close/re-open. Posting to a Closed or Future period is blocked.

### 6.5 Cross-cutting
Attachments (simulated file names), comments, full **audit log** table (entity, action, user, timestamp, before/after) viewable in Tools → Audit Trail, notification centre for approvals and rejections, global search box (find any transaction by number across all modules and open it).

---

## 7. POSTING TEMPLATES (the accounting rules, implement exactly)

Dr = debit, Cr = credit. VAT 5% unless the tax code says otherwise. The BU on the transaction is the balancing segment on every line.

**Procurement and Supply Chain**
- Goods receipt of stock items (PO matched): Dr Inventory (1200/1210/1220/1230 by item class) / Cr **GRNI 2010**.
- Receipt of services or non-stock goods: Dr Expense or CWIP / Cr GRNI (only if receipt-matching is on for the PO line; otherwise expense on invoice).
- Issue to consumption (hospital departments): Dr 5010/5020 / Cr Inventory.
- Pharmacy dispense or sale (cost side, triggered by AR retail/insurance sale lines): Dr 5000 / Cr 1200 at weighted average cost.
- Inventory adjustment or expiry write-off: Dr 5030 / Cr Inventory (gain is the reverse).
- Inter-unit stock transfer: creates an Intercompany transaction (see Intercompany) and moves on-hand quantity between BUs at weighted average cost.

**Payables**
- **AP Invoice, PO matched (goods):** Dr GRNI 2010 (receipt value) / Dr 5040 PPV (price difference, if any) / Dr VAT Input 1400 / Cr **Trade Payables 2000**.
- **AP Invoice, PO matched (services, expense):** Dr expense account from the PO distribution / Dr 1400 / Cr 2000.
- **AP Invoice, capital item:** Dr **Asset Clearing 1610** (or CWIP 1600 if flagged construction) / Dr 1400 / Cr 2000, **and the line is sent to the Fixed Assets Additions queue** (section 8.4).
- **AP Invoice, non-PO:** allowed only for supplier or expense categories flagged "PO not required" (utilities, rent, regulatory fees, bank charges). All other invoices must reference an approved PO (goods also need a receipt, i.e. three-way match with tolerance of 2% price and 0% quantity).
- **AP Credit Memo:** reverse of the invoice (Dr 2000 / Cr expense or inventory/GRNI / Cr 1400).
- **AP Payment:** Dr 2000 / Cr Bank 1020. Payments are for approved invoices only, with partial payments supported. Payment appears in Cash Management for reconciliation. Status: Draft → Pending Approval → Approved/Paid.
- **Prepayment or supplier advance:** Dr 1310 / Cr Bank, applied against later invoices (Dr 2000 / Cr 1310).

**Receivables**
- **AR Invoice (patient self-pay, insurance claim, corporate, pharmacy):** Dr AR control (1100 patient / 1110 insurance / 1120 corporate) / Cr Revenue (4000–4060 by service line) / Cr VAT Output 2100 (if taxable). Gross billing less insurance discounts: Dr 4090 for contractual adjustments at invoice level.
- **AR Credit Memo:** Dr Revenue (or 4090) / Dr 2100 / Cr AR control.
- **AR Receipt:** Dr Bank 1030 (or Main Cash 1000 for cash) / Cr AR control; supports partial receipt and application to specific invoices; unapplied receipts go to 2300 until applied.
- **Insurance rejection write-off:** Dr 4090 (or 6310) / Cr 1110.
- **Pharmacy daily retail sales batch (cash/card):** Dr 1000 or 1040 / Cr 4040 / Cr 2100, together with the cost-of-sales entry above.
- Month-end **ECL provision** run (simple ageing matrix: 0–30 1%, 31–90 3%, 91–180 10%, 181–365 25%, >365 50%): Dr 6310 / Cr 1190 (movement only).

**Cash Management**
- **Petty cash fund (imprest) setup or replenishment:** Dr 1010 / Cr Bank 1020 (replenishment tops up to the imprest limit).
- **Petty cash expense voucher:** Dr expense (6200/6230/6240/6290 etc.) / Dr 1400 (if VAT invoice) / Cr 1010. Checks: voucher amount ≤ per-voucher cap (AED 1,000) and ≤ fund balance.
- **Main cash expense (paid from main cash safe):** Dr expense / Dr 1400 / Cr Main Cash 1000. Cap AED 5,000; cash balance check.
- **Cash deposit to bank:** Dr 1020 / Cr 1000. **Cash withdrawal:** reverse. **Bank transfer between own accounts:** Dr destination / Cr source.
- **Bank charges or interest from the statement:** Dr 6270 or 7000 / Cr 1020, created from the reconciliation screen.

**Fixed Assets**
- **Capitalisation (after validation and approval):** Dr Asset cost account by category (1710–1770) / Cr **Asset Clearing 1610**.
- **Monthly depreciation run:** Dr 6300 / Cr Accumulated Depreciation (by category) per asset per BU.
- **Cost adjustment:** Dr or Cr Asset cost / Cr or Dr 1610 or Bank as selected.
- **Transfer between BUs:** creates an intercompany transaction at net book value (Dr 1500 at the sender, Cr asset cost and Dr accumulated depreciation; the receiver does the opposite with 2500). Section 9.
- **Retirement or disposal:** Dr Bank/Receivable (proceeds) / Dr Accumulated Depreciation / Dr or Cr 7100 loss or gain / Cr Asset cost.

**Intercompany** (section 9) and **Manual GL journals** (section 10) as defined there.

---

## 8. MODULE SPECIFICATIONS

### 8.1 PAYABLES (Tab: Payables)
Quick actions: Create Invoice, Manage Invoices, Create Payment, Manage Payments, Import Invoices (CSV upload with validation report), Payables Invoice Aging Report, Payables Trial Balance Report, Prepare Payables to General Ledger Reconciliation. Apps: Payables Dashboard, Invoices, Payments, Suppliers.

- **Invoices work area:** summary tiles (Holds by type, Approval: Pending/Others/Rejected, as in the reference); table with Invoice Number, Supplier, Supplier Invoice No., Date, Due Date, Amount, Tax, Status, Maker, Checker. Right-side **Search panel**: Invoice Number, Supplier or Party (lookup), Supplier Site, Status, Date range, BU, Amount range. "At least one criterion required" rule. Search by **internal sequential invoice number** must work, including partial match.
- **Create Invoice form:** header (BU, Supplier and site, Invoice type: Standard/Credit Memo/Prepayment, Supplier invoice no., invoice date, GL date, due date from payment terms, currency, description), lines (PO number lookup → pulls PO lines and receipts, quantity, unit price, line amount, tax code, distribution account, department, "Capital item" flag with asset category), tax summary, totals. Buttons: Save as Draft, Validate, Submit for Approval, Cancel. Validation: totals tie, PO-match tolerance, duplicate invoice, supplier active, period open. Holds: system holds such as "Total of invoice lines does not equal invoice amount", "Price exceeds PO", "Receipt missing" (reproduce the style of the reference hold list); holds must be released or corrected before submission.
- **Approval:** Checker opens "Pending Approval" queue, reviews lines and View Accounting preview, then Approve or Reject (with reason).
- **Supplier master:** code, name, TRN, payment terms, bank details, site(s), category, "PO not required" flag.

### 8.2 RECEIVABLES (Tab: Receivables)
Quick actions: Create Transaction, Manage Transactions, Manage Receipts, Create Receipt, Create Credit Memo, Aging Report, Statement of Account. Apps: Billing, Accounts Receivable, Customers.

- **Billing work area** (as in the reference): summary tiles (Incomplete 0–10 days and 10+ days, Adjustment Approval, Adjustment Research), table of transactions (Number, Source, Class, Customer, Amount, Status), right-hand task list (Manage Transactions, Manage AutoInvoice Lines, Review Customer Account Details, Create Adjustment Journal, Review Journal Entries).
- **Create Invoice:** BU, customer (patient, insurer, corporate), service line (revenue account), patient/claim reference, visit date, lines with tax codes, discounts, insurance co-pay split (patient share vs insurer share creates two receivable lines), payment terms.
- **Receipts:** apply to invoices (auto and manual), partial/unapplied handling, bank/cash selection, approval, accounting.
- **Customer master**, credit limit check (warn if exceeded), **statement of account**, **aging** (0–30, 31–60, 61–90, 91–180, 181+).
- Same lifecycle, numbering, approval and GL posting rules as Payables.

### 8.3 SUPPLY CHAIN: PROCUREMENT and SUPPLY CHAIN EXECUTION
**All purchasing flows through here.**
Procurement tab apps: Purchase Requisitions, Purchase Orders, Suppliers (read link), Procurement Dashboard. Quick actions: Create Requisition, Manage Requisitions, Create Order, Manage Orders, Approve Orders.
Supply Chain Execution tab apps: Inventory, Receiving, Stock Transfers, Consumption and Adjustments, Item Master. Quick actions: Create Receipt, Manage Receipts, Create Stock Transfer, Record Consumption, Create Inventory Adjustment, Stock On-hand.

Flow: **Requisition → (approval) → Purchase Order → (approval) → Receipt (goods/services) → AP Invoice (3-way match) → Payment.** Item master with item code, description, class (Pharmaceutical, Consumable, Implant/Surgical, General, Service, Capital Asset), UoM, expiry-tracked flag, reorder level. Inventory by BU and sub-inventory (Main Store, Pharmacy, OT), weighted-average costing, on-hand report, expiry report. PO has lines with account distribution and "capital" flag. Receipts post per 7. Show a **Procurement Dashboard** (open POs, GRNI balance, spend by category, top suppliers).

### 8.4 FIXED ASSETS (Tab: Fixed Assets) — follow the reference "Assets" work area
Quick actions: Prepare Source Lines, Adjust Assets, Add Asset, Transfer Assets, Retire Assets, Run Depreciation, Asset Register Report. Apps: Assets, Asset Inquiry.

Book: "MERIDIAN CORPORATE ASSETS – AED". **Assets work area** summary tiles: **Additions** (Incomplete / Exceptions / Ready to Post), **Adjustments**, **Transfers**, **Retirements** (Incomplete counts), **Depreciation** (current period, e.g., Oct-26). Table of source lines with columns: Description, Invoice Number, Cost, In-Service Date, Category, PO Number, Units, Comments; warning icon for exceptions.

Workflow:
1. When an **AP invoice with a capital line is approved**, a line lands in **Additions → Incomplete** (accounted to 1610 as per section 7).
2. The FA accountant (Maker) opens **Prepare Source Lines**: selects category (default life, method, depreciation account from category), in-service date, units, location (BU/department), tag number, optional merge/split/add-to-existing-asset. **Exceptions** are lines that cannot be prepared (missing category, cancelled invoice, zero cost, in-service date before invoice date) and must be corrected.
3. Prepared lines move to **Ready to Post**. Checker approves → **Create Assets** → assets are recorded in the register and the **capitalisation entry posts to GL** (Dr asset cost / Cr 1610).
4. **Depreciation**: straight-line, monthly, prorated from the in-service month. Categories and default lives: Buildings 25y, Leasehold Improvements 10y, Medical Equipment 8y, Furniture 5y, IT Equipment 4y, Vehicles 5y, Plant/HVAC/Electrical 10y; Land not depreciated; residual value 0 by default. **Run Depreciation** for an open period is previewed, approved, then posted (Dr 6300 / Cr accumulated depreciation) with the register updated; cannot run twice for the same period; blocks if prior periods are unrun.
5. Adjustments, Transfers (BU to BU with IC entries) and Retirements follow the same Maker–Checker flow.
6. Reports: Asset Register, Depreciation Schedule, Additions/Retirements Listing, FA-to-GL reconciliation (asset cost and accumulated depreciation by category vs GL).

### 8.5 CASH MANAGEMENT (Tab: Cash Management)
Quick actions: Create Petty Cash Voucher, Create Main Cash Expense, Replenish Petty Cash, Create Bank Statement, Manage Bank Statements, Reconcile, Cash Position. Apps: Bank Statements and Reconciliation, Petty Cash, Main Cash.

- **Bank accounts master** per BU (Operating, Collections). **Petty cash funds** per BU (imprest amount, custodian).
- **Petty Cash:** voucher form (BU, fund, date, payee, expense category/account, description, amount, tax code, receipt attached flag). Maker submits → Checker approves → posts Dr expense / Cr 1010. Fund balance and caps enforced. **Replenishment** request posts Dr 1010 / Cr bank when approved.
- **Main Cash:** cash-in-hand register per BU with expense vouchers, deposits to bank, and opening/closing cash count. Each is Maker–Checker. Cash book view shows running balance that must tie to GL 1000/1010.
- **Bank Statements and Reconciliation:** create (manual lines or CSV import) and manage statements; reconcile screen with auto-match (amount + date ±3 days + reference) against AP payments, AR receipts and cash deposits, manual match, create-entry-for-unmatched (bank charges, interest), reconciliation status and difference. Report: Bank Reconciliation Statement, Cash Position by BU.

### 8.6 INTERCOMPANY ACCOUNTING (Tab: Intercompany Accounting) — as in the reference
Quick actions: Manage Intercompany Outbound Transactions, Manage Intercompany Inbound Transactions, Create Intercompany Transaction, Manage Approvals for Intercompany Transactions. Apps: Multitier Intercompany Operations, Transactions, Reconciliation.

Create Intercompany Transaction has three types:
- **Intercompany Invoice** (provider BU charges receiver BU for services, supplies or recharges): Provider: Dr 1500 (due from receiver) / Cr 4900 (or Cr Inventory for stock transfers, or Cr Asset for asset transfers). Receiver: Dr expense/inventory/asset / Cr 2500 (due to provider). Receiver BU users must **Accept** (or Reject with reason) before posting; both sides post in the same transaction.
- **Intercompany Credit Note:** reverses a prior intercompany invoice fully or partially (links to the original).
- **Intercompany Journal:** a multi-BU journal; where lines for different BUs do not balance within each BU, the system **automatically adds 1500/2500 balancing lines** per BU pair so every BU balances on its own (standard Oracle behaviour).
Maker–Checker, numbering ICI/ICC/ICJ, approval then auto-post both sides to GL. **Reconciliation** screen: matrix of BU pairs showing due-from vs due-to; differences highlighted; the net across the group must be zero. A "Eliminations" report lists IC balances and IC revenue/expense eliminated on consolidation.

### 8.7 GENERAL ACCOUNTING (Tab: General Accounting) — as in the reference
Quick actions: Manage Journals, Create Journal, Manage Approvals for Journals, Import Journals, Create Accounting. Apps: General Accounting Dashboard, Journals, Period Close, Account Inquiry.

- **Journals:** list and search every GL journal from every module (filters: journal no., source module, BU, account, period, date, status, amount, created by), drill down to lines and to the **source subledger transaction**. Show Source = Payables, Receivables, Fixed Assets, Cash Management, Procurement/Inventory, Intercompany, Manual, Depreciation.
- **Create Journal (manual):** header (BU(s), period, date, category, currency, description), lines (BU, account, department, debit, credit, line description), live balance check, templates, upload lines via CSV, recurring/reversing option (auto-reversal date). Maker → Checker → posted. Blocks control accounts and closed periods.
- **Reverse Journal**, **Import Journals** with validation errors list, **Create Accounting** (retry for accounting errors), **Account Inquiry/Balances** (BU × account × period with drill-down), **Period Close**, **General Accounting Dashboard** (key KPIs: revenue, expense, net profit, cash, AR and AP totals, unposted items; charts of revenue vs expense by month and by BU type).

### 8.8 REPORTS (Tab: Reports) and module reports
**A. General Ledger Report:** parameters: Fiscal Year, Period From/To **or** Date From/To, Account From/To (and "All accounts"), Business Unit (single, group, or **All Units**), Source, Include opening balance (Y/N). Output: per account, opening balance, every line (date, journal no., source, document no., description, BU, debit, credit, running balance), closing balance, grand totals. Download Excel/PDF/CSV.

**B. Trial Balance:** parameters: As-of Date or Period, BU (single, group, **All Units**), level (account / BU × account), include zero balances Y/N. Columns: Opening Dr/Cr, Period Movement Dr/Cr, Closing Dr/Cr; total row must show Dr = Cr; a red banner if not (it should never happen).

**C. IFRS Financial Statements** for the selected entity (any single BU, BU group, or **Consolidated with intercompany eliminated**), prepared strictly from the Trial Balance for the selected period using the IFRS line mapping in section 5:
1. **Statement of Financial Position** (IAS 1: current/non-current split, comparative at the opening balance date).
2. **Statement of Profit or Loss and Other Comprehensive Income** (IAS 1, by function: revenue (IFRS 15), cost of sales, gross profit, other income, administrative and selling expenses, impairment losses (IFRS 9), operating profit, finance costs, profit before tax, income tax, profit for the period, OCI nil).
3. **Statement of Changes in Equity** (IAS 1).
4. **Statement of Cash Flows** (IAS 7, indirect method derived from TB movements: operating, investing, financing, ties to the movement in cash and cash equivalents with a check line).
5. **Notes:** basis of preparation and significant accounting policies (IFRS 15, IFRS 9 ECL, IAS 2 weighted average cost, IAS 16 straight-line, IFRS 16 note placeholder with lease balances from accounts 2600, IAS 12), PPE movement schedule by category (cost, accumulated depreciation, additions, disposals, NBV), inventories, trade receivables with ageing and ECL, trade and other payables, revenue disaggregation by service line, related-party (intercompany) balances.
Parameters: Entity, Period From/To (or year-to-date), Comparative (opening balance / prior period), Presentation (AED, AED '000). Checks displayed: Assets = Equity + Liabilities; profit agrees to TB; cash flow agrees to cash. Current-year profit is rolled into equity by the system.

**D. Module Reports (each module has a "Reports" app with filters: date range, BU, status, counterparty, and downloads in Excel/PDF/CSV):**
Payables: Invoice Register (all transactions), Payments Register, Supplier Ledger, Aging, Payables Trial Balance, AP-to-GL Reconciliation, Held Invoices.
Receivables: Transaction Register, Receipts Register, Customer Statement, Aging, Insurance Claims Status, AR-to-GL Reconciliation.
Procurement/SCE: PO Register, Open POs, GRNI Report, Receipt Register, Inventory On-hand and Valuation, Expiry Report, Stock Movement.
Fixed Assets: Asset Register, Depreciation Schedule, Additions/Retirements, FA-to-GL Reconciliation, Source Lines Awaiting Validation.
Cash Management: Petty Cash Register, Main Cash Book, Bank Reconciliation, Bank Statement Listing, Cash Position.
Intercompany: IC Transactions Register, IC Reconciliation Matrix, Eliminations.
General Accounting: Journal Register, Unposted Journals, Account Balances, Audit Trail.
Every report shows the parameters used, generated by/at, and report totals.

### 8.9 TOOLS (Tab: Tools)
Administration (Business Units, Chart of Accounts viewer, Suppliers/Customers/Items masters, Users and Roles, Approval limits, Sequences viewer, Tax codes), **Audit Trail**, **Reset Demo Data**, **System Integrity Check** (section 13), Notifications, Favourites.

---

## 9. END-TO-END FLOWS THE APP MUST DEMONSTRATE
1. Requisition → PO → Receipt → AP invoice (3-way match) → approval → GL → payment → bank reconciliation.
2. Capital purchase (e.g., an MRI unit): PO → receipt → AP invoice with capital line → approval → GL (Dr 1610, VAT, Cr 2000) → appears in FA Additions → prepare and validate → approve → asset created → GL (Dr 1730 / Cr 1610) → monthly depreciation → disposal.
3. Insurance claim invoice → approval → GL → receipt → partial rejection write-off.
4. Pharmacy daily sales batch with automatic cost of sales and inventory relief.
5. Petty cash voucher and main cash expense → approval → GL; replenishment; bank deposit.
6. Intercompany invoice from a hospital to a clinic (and a stock transfer between pharmacies) → acceptance → both sides in GL → reconciliation nets to zero; credit note reversing part.
7. Manual GL journal (accrual) with auto-reversal; period close checklist.
8. Reports: GL, TB (all units and single unit), IFRS statements (consolidated and single BU), module registers, all downloadable.

---

## 10. DATA MODEL (minimum)
Entities: User, Role, BusinessUnit, Department, Account, Period, TaxCode, Sequence, Supplier(+Site), Customer, Item, Requisition(+Lines), PurchaseOrder(+Lines), Receipt(+Lines), InventoryBalance, StockMovement, APInvoice(+Lines, Holds), APPayment(+Applications), ARTransaction(+Lines), ARReceipt(+Applications), PettyCashFund, CashVoucher, BankAccount, BankStatement(+Lines), Reconciliation, AssetCategory, Asset, AssetSourceLine, AssetBook, DepreciationRun(+Lines), AssetTransaction (adjust/transfer/retire), ICTransaction(+Lines, both sides), ApprovalRecord, SubledgerEntry(+Lines), GLJournal(+Lines), AuditLog, Notification, Attachment, Favourite. Every transaction has: id, number, BU, status, createdBy/At, submittedBy/At, approvedBy/At, rejectionReason, postedAt, glJournalId.

---

## 11. UX DETAILS
- Dashboards with Recharts on Payables, Receivables, Procurement, Cash, GL.
- Toasts for every action; confirmation dialogs for submit/approve/reject/reverse; inline validation with field-level errors.
- Right-aligned numeric columns; sticky table headers; CSV/Excel export from any table (Actions → Export).
- Accessible: labels, keyboard focus, contrast compliant with the plum palette.

---

## 12. SEED DATA (generated programmatically through the real posting engine using a deterministic PRNG, seed 2026; all figures plausible for a healthcare group)
- **Opening balances at 01/Jan/2026** (a balanced opening journal per BU: cash, bank, receivables, inventory, PPE at cost and accumulated depreciation, payables, loans, share capital, retained earnings). The Balance Sheet comparative uses these.
- Masters: 40 suppliers (pharma distributors, medical equipment vendors, consumables, facility management, utilities, IT, lessors), 40 customers (insurers, corporates, government programmes, and patient accounts; use fictional names), 120 items, 7 users, 15 BUs, 8 departments.
- Transactions between **Jan and 19 Oct 2026**, at least:
  - 220 requisitions/POs, 260 receipts, **300 AP invoices** (incl. 25 pending approval, 10 drafts, 8 rejected, 6 on hold, 12 credit memos, some cancelled), 180 AP payments.
  - **320 AR invoices** across hospitals/clinics/pharmacies (incl. 30 pending approval, 15 drafts), 250 receipts, 12 credit memos, insurance rejections.
  - 60 pharmacy daily sales batches with COGS.
  - **80 fixed assets** in the register (buildings, medical equipment such as CT, MRI, ultrasound, HVAC, IT, furniture, vehicles), monthly depreciation Jan–Sep posted and Oct-26 run available; in the Additions queue: about 30 Incomplete, 3 Exceptions (missing category, cancelled invoice reference), 20 Ready to Post; 2 retirements pending.
  - 150 petty cash vouchers and 60 main cash expenses (some pending), 12 replenishments, 30 deposits, 15 bank statements with a mix of reconciled and unreconciled lines.
  - 45 intercompany invoices, 8 credit notes, 12 intercompany journals (some pending acceptance/approval); reconciliation nets to zero.
  - 40 manual journals (accruals, reclasses, provisions, ECL, with auto-reversals).
- Result: more than 3,000 GL lines; **TB balanced**, Balance Sheet balanced, subledger-to-GL reconciliations all zero.
- **Approval demo coverage:** include pending items created by other makers (so Charlotte can approve them) **and** a handful of Charlotte's own drafts/pending items (so Switch User → Daniel Reed demonstrates segregation of duties). Home "Things to Finish" and the bell must show non-zero live counts.

---

## 13. SYSTEM INTEGRITY CHECK (Tools) — automated self-test page with pass/fail rows
1. Every GL journal: debits = credits. 2. Total TB debits = total credits (all units and each BU). 3. AP subledger open balance = GL 2000; AR = 1100+1110+1120 (net of 1190 shown separately); Inventory subledger = 1200–1230; GRNI = uninvoiced receipts; Petty cash register = 1010; Main cash book = 1000; FA register cost = 1700–1770 and accumulated depreciation = 1810–1870; Asset clearing 1610 = capital lines awaiting capitalisation. 4. Intercompany 1500 total = 2500 total across the group. 5. Sequences gapless per type. 6. No posted journal in a closed period outside its date. 7. Balance Sheet check = 0 for each BU and consolidated. 8. No user approved their own transaction.
Display green ticks; if any fail, show the offending records.

---

## 14. ACCEPTANCE TESTS (the app must pass these before you say you are done)
1. Log in as `charlotte.davis / Charlotte@2026`; see "Good evening, Charlotte Davis" and the module tabs.
2. Create an AP invoice for PO-matched goods → number is the next sequential PINV; search by that number finds it; submit; Charlotte cannot approve it; Switch User to Daniel Reed and approve; a GL journal appears in General Accounting → Journals with Source = Payables and the exact lines from section 7.
3. Create an AP invoice with a capital line → after approval it appears in Fixed Assets → Additions (Incomplete). Prepare, approve, the asset appears in the register, and GL shows Dr 1730 / Cr 1610 with 1610 returning to zero for that item.
4. Create an AR insurance invoice, approve it and receive payment; the aging and GL reflect it.
5. Petty cash voucher above the cap is blocked; a valid one posts Dr expense / Dr VAT / Cr 1010 after approval.
6. Intercompany invoice H01 → C01: after acceptance and approval, both BUs' GL show the mirror entries; the reconciliation difference is 0.
7. Run Oct-26 depreciation; GL shows 6300 / accumulated depreciation lines; second run is blocked.
8. Try posting a manual journal into a closed period → blocked with a clear error.
9. Generate: GL report (Year 2026, account 2000–2000, BU All Units), TB at 30/Sep/2026 (All Units), IFRS statements for H01 and Consolidated; download Excel, PDF and CSV; Balance Sheet balances and agrees to the TB.
10. Integrity Check page shows all green.

---

## 15. BUILD PHASES (finish each fully; no stubs)
- **Phase 1:** Project scaffold, design system and palette, sign-in, shell (header, navigator, home tabs, tiles, quick actions, Things to Finish), IndexedDB layer, users/roles, BU/COA/periods/sequences/audit, **posting engine and approval engine**.
- **Phase 2:** General Accounting (journals, create/import/reverse, period close, account inquiry, dashboard) and Reports tab core (GL report, Trial Balance).
- **Phase 3:** Supply chain (procurement, receiving, inventory), Payables, Receivables with all flows and templates.
- **Phase 4:** Fixed Assets, Cash Management (petty cash, main cash, bank reconciliation), Intercompany.
- **Phase 5:** IFRS financial statements, module reports, seed data generation, System Integrity Check, polishing, run all acceptance tests and fix issues.

**Start now with Phase 1. At the end of the final phase, give a short guide: login credentials, a 10-minute demo script, and the list of acceptance tests passed.**
