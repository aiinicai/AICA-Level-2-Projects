# Advanced GST Invoicing System & Sales Register

A lightweight, standalone web-based tool designed for generating **Proforma Invoices**, **Tax Invoices**, and **Quotations** compliant with Indian GST standards. Built as a single file using HTML5, CSS3, and JavaScript, it leverages **SheetJS (xlsx)** for seamless Excel data exports and uses `localStorage` for dynamic profile management and sales logging.

---

## Key Features

* **Multi-Document Generation:** Toggle between Proforma Invoice, Statutory Tax Invoice, and Quotation modes with dynamic disclaimer updates.
* **Automated GST & State Logic:**
  * Auto-detects seller and buyer states directly from GSTIN prefix codes.
  * Automatically calculates split tax types (CGST + SGST vs. IGST) based on intra-state vs. inter-state supply rules.
  * Auto-extracts 10-digit PAN numbers from provided GSTINs.
* **Dynamic Calculations:** Real-time line item subtotals, item-level discounts, tax breakdowns, advance deduction, balance due calculations, and Indian numbering word conversion.
* **Master Profile Management:** Save and load frequent Supplier and Buyer details to `localStorage` or pick from default regional profiles (e.g., GSPL India Gasnet Limited regional branches).
* **State-Based Sequential Numbering:** Generates auto-incrementing document numbers mapped to specific state codes (e.g., `GIGL/GUJ/26-27/001`).
* **Data Export Options:**
  * **Print / PDF:** Uses dedicated `@media print` CSS rules to generate clean printed invoices without UI control buttons.
  * **Excel Invoice Export:** Downloads individual invoice structures to `.xlsx` files via SheetJS.
  * **Sales Register:** Logs all generated documents locally and exports an aggregated master sales register spreadsheet.

---

## File Structure & Dependencies

The entire application runs entirely in the browser and requires no backend server setup.

* **Single Source File:** `index.html` (contains layout, CSS styling, and logic).
* **External CDN Dependency:**
  * `xlsx.full.min.js` (SheetJS v0.18.5) — Loaded via CDN for client-side Excel parsing and file generation.

---

## Technical Overview

### 1. Document & Header Configuration
* Selecting a document type from the top controls updates `#headerTitle` and changes the header sub-caption depending on whether ITC (Input Tax Credit) is claimable.

### 2. State & GST Resolution
* The `gstStateCodes` map translates 2-digit state prefixes (e.g., `24` for Gujarat, `27` for Maharashtra) into human-readable state names.
* The system evaluates `suppCode === buyCode` to toggle visible rows between `(CGST + SGST)` and `IGST`.

### 3. Data Storage Keys (`localStorage`)
* `seller_masters`: Array of saved supplier profiles.
* `customer_masters`: Array of saved buyer profiles.
* `invoice_counters`: Key-value map storing current state-specific sequence numbers.
* `sales_register`: Master log array of past finalized transactions.

---

## How to Use

1. **Launch:** Open `index.html` in any modern web browser.
2. **Select Document Type:** Pick *Proforma Invoice*, *Tax Invoice*, or *Quotation* from the top bar.
3. **Set Profiles:** Select an existing profile from the **Seller** or **Customer** dropdowns, or enter details manually and click **+ Save to Master**.
4. **Manage Line Items:**
   * Edit item descriptions, HSN/SAC codes, quantity, rate, and discount.
   * Click **+ Add Line Item** to add additional items or click **X** to remove a row.
5. **Adjust Tax & Advances:** Modify the overall GST Rate (%) or enter an Advance Received amount to compute the final Balance Payable.
6. **Save & Export:**
   * **Print / Export PDF:** Triggers browser print dialog tailored for standard A4 document layout.
   * **Export Invoice Excel:** Exports the currently displayed invoice to an `.xlsx` file.
   * **Save & Export Sales Register:** Appends the record to the master sales log, exports `Sales_Register_Master.xlsx`, and increments the invoice number.