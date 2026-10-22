# MarketMatch – Amazon Sales, Payout & GST Reconciliation

**MarketMatch** is a local Python application engineered to reconcile three Amazon seller reports for small Indian sellers:
1. **Merchant Tax Report (MTR)**: Invoice-level sales and returns.
2. **GST Ready-to-File Report (GSTR-1 format)**: Summarized and invoice-level GST reported sales.
3. **Payments Report (Date Range / Unified Transaction)**: Payout settlements, fees, TCS, TDS, and deferred transactions.

MarketMatch bridges the gaps between sales, tax filings, and bank disbursements, identifies short disbursements, catches missing tax declarations, and drafts claim emails for Amazon Seller Support.

---

## 🔒 Privacy & Local Execution Notice
MarketMatch runs **100% locally** on your machine.
- No financial figures, order details, GSTINs, or customer records are sent to any external server or cloud service.
- All database operations are stored in a local SQLite file (`marketmatch.db`).
- All file processing and reconciliation algorithms execute in pure Python on your local processor.

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.10 or higher
- Git (optional)

### 1. Clone or Open the Repository
```bash
cd "Antigravity- Output"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
streamlit run app.py
```
The application will launch in your browser at `http://localhost:8501`.

---

## 📥 How to Download Amazon Seller Reports

### 1. Amazon Merchant Tax Report (MTR) – Sales
1. Log in to [Amazon Seller Central India](https://sellercentral.amazon.in).
2. Navigate to **Reports** → **Tax Document Library**.
3. Select the **Merchant Tax Report** tab.
4. Select report type: **B2C Invoices** (or B2B if registered).
5. Choose your target month and click **Request Report**.
6. Download the resulting `.csv` or `.xlsx` file.

### 2. Amazon GST Ready-to-File Report (GSTR-1 format) – Tax Reported
1. Go to **Reports** → **Tax Document Library**.
2. Select **GST Monthly Reports** (or GSTR-1 Ready to file).
3. Select your filing month and download the multi-sheet workbook (`.xlsx`).
4. *Note:* The workbook contains tabs such as `B2CS`, `B2CL`, `CDNUR`, and `HSN Summary`. Rows 1–3 contain cached titles and summary formulas; MarketMatch automatically skips these rows and recalculates true control totals from row 5 detail rows.

### 3. Amazon Payments Transaction Report – Payouts Received
1. Navigate to **Payments** → **Date Range Reports**.
2. Click **Generate Report**.
3. Select report type: **Transaction** (Reports with start date from 1 Jan 2025 or later include released and deferred transactions with `Transaction Status` and `Transaction Release Date`).
4. Select the custom date range covering your filing month and click **Generate**.
5. Download the `.csv` file.

---

## ⚙️ Profile-Driven Parsing Architecture (`config/column_aliases.json`)

MarketMatch does not hardcode column names. All report parsing is dynamically driven by `config/column_aliases.json` (Version 2).

### Supporting New Marketplaces
To add support for other marketplaces (e.g. Flipkart, Meesho, Myntra), add a new profile under the `reports` dictionary in `config/column_aliases.json` without modifying any Python code:
```json
{
  "reports": {
    "flipkart_sales": {
      "display_name": "Flipkart Sales Report",
      "role": "sales",
      "verified": false,
      "value_formats_verified": false,
      "required": ["order_id", "invoice_no", "taxable_value", "invoice_value"],
      "columns": {
        "order_id": ["Order ID", "order_id"],
        "invoice_value": ["Final Invoice Amount", "Invoice Amount"]
      }
    }
  }
}
```

### Profile Verification Flags
Each profile maintains two essential flags:
1. `"verified"`: True when headers were copied directly from a production marketplace export.
2. `"value_formats_verified"`: True when real data rows have been verified. When `value_formats_verified` is `false`, MarketMatch surfaces an interactive **Value Mapping Screen** on the Upload page showing distinct column values with counts, prompting the user to confirm mappings.

---

## 🧠 How Reconciliation Layers Work

### Layer A – Sales ↔ Payments (Order-Level Bridge)
- **Matching Key**: `order_id`.
- **Financial Bridge per Order**:
  $$\text{Expected Net Payout} = \text{Invoice Value} - \text{Refunds} - \text{Selling Fees} - \text{FBA Fees} - \text{Other Fees} - \text{GST on Fees} - \text{TCS} - \text{TDS} \pm \text{Rebates}$$
- **Handling Deferred Payouts**: Rows with `Transaction Status == "Deferred"` are classified strictly as **"Awaiting release (Timing)"**, never as "Not paid".
- **Unpaid Aging Rule**: An order is classified as **"Not paid"** only when it has passed the configured `unpaid_threshold_days` (default 10 days) with neither a Released nor a Deferred payout record.
- **Statuses**: `Matched`, `Short paid`, `Excess paid`, `Payout without order`, `Duplicate payout`, `Refund without credit note`, `Timing difference`, `Awaiting release (Timing)`, `Not paid`, `Rounding`, `Unexplained`.

### Layer B – Sales ↔ GST Reported (Section Tie-Out)
- **B2C Routing**:
  - Inter-state B2C orders with invoice value $> ₹ 1,00,000$ route to **B2C Large (B2CL)**.
  - Credit notes against B2CL route to **CDNUR**.
  - All other sales and refunds route to **B2C Small (B2CS)** grouped by $(Place\ of\ Supply,\ Rate)$.
- **HSN Tie-Out**: Aggregates net sales by $(HSN,\ Rate)$. Matches GST report HSNs on **exact code first**, then falls back to **4-digit prefix** matching.
- **HSN Tax Gap Notice**: Amazon's GSTR-1 report often exhibits tax column sums that are lower than $Taxable \times Rate$ (observed in the test sample as a ₹ 291.94 variance). MarketMatch flags this explicitly as an internal Amazon export defect and reconciles it against the MTR sales tax columns.

### Layer C – TCS & TDS Statutory Compliance
- Validates that TCS deducted across MTR and Payments aligns with the statutory rate ($0.5\%$ default).
- Verifies Section 194-O Income Tax TDS ($0.1\%$ default).
- Allows sellers to enter monthly filed figures from **GSTR-8 (Table 4)** and **Form 26AS** to confirm government deposits.

---

## 📋 Reasonable Assumptions Made

1. **Zero-Float Accounting**: All monetary arithmetic uses Python `Decimal` rounded to 2 decimal places (integer paise). Source files containing floating-point noise (such as `11833.809999999996`) are sanitized on load.
2. **Text Representation for IDs**: Order IDs, invoice numbers, credit note numbers, and HSN codes are ingested strictly as strings to prevent Excel scientific notation (`4.07E+12`) or leading digit loss.
3. **Preamble Lines in Payments**: Amazon Payments CSV files begin with 13 explanatory definition lines. MarketMatch dynamically identifies the header row using keyword matching (`settlement id`, `order id`, `Transaction Status`) rather than hardcoded row numbers.
4. **GST State Matching**: GST portal place-of-supply formats (`33-Tamil Nadu`, `33`, or `Tamil Nadu`) are normalized to standard 2-digit GST state codes (`33`) based on CBIC state code definitions.
5. **Tolerance Window**: A default rounding tolerance of ₹ 1.00 is applied across calculations to absorb sub-paise fractional variances across high transaction volumes.
6. **Pure Core Logic**: All functions in `core/` are pure and free of Streamlit dependencies, taking an explicit `as_of` parameter to support historic reproducibility.

---

## ⚠️ Known Limitations
- Version 1 supports Amazon India report formats out-of-the-box. Other marketplaces require adding their profile schema into `config/column_aliases.json`.
- Amazon's GSTR-1 export does not contain order IDs in the B2CS tab; tie-out is performed on grouped state-rate aggregates.
- Statutory withholding tax rates (TCS 0.5%, TDS 0.1%, GST on fees 18%) are subject to government policy updates; verify current rates in the Settings page.

---

## 🧪 Running Automated Tests
Run the comprehensive pytest suite covering all reconciliation layers, real sample workbook fixture, normalization, and synthetic demo counts:
```bash
python -m pytest tests/ -v
```

---

<div align="center">
  <sub>Demo project. Not tax advice.</sub>
</div>
