# Example Files: Input → Validation → Output

This folder shows what goes **into** the application and what comes **out**.

| Folder | Contents |
|---|---|
| `A_Blank_Excel_Templates` | Blank templates for Sales, Purchase, Journal, Bank Receipt and Bank Payment. Hidden sheets identify the template and version. |
| `B_Sample_Input_Excel` | The same templates filled with example transactions for a demo company. |
| `C_Sample_Output_Tally_XML` | The Tally import XML the application generated from each sample file. |

The templates downloaded from inside the app also include drop-down lists of the ledgers, stock items and units from your own Tally company.

---

## Worked example 1: Sales invoice (intra-state)

**Input** (`sample_sales.xlsx`, row 2):

| Voucher Date | Invoice No. | Customer | Place of Supply | Sales Ledger | Taxable | CGST 9% | SGST 9% | Invoice Total |
|---|---|---|---|---|---|---|---|---|
| 25-09-2026 | INV-1025 | ABC Traders | Maharashtra | Sales - Services | 1,00,000 | 9,000 | 9,000 | 1,18,000 |

**Checks the application performs:**
- The date is within FY 2026-27.
- The GSTIN format and checksum are valid, and the state code matches Maharashtra.
- The company and the place of supply are both in Maharashtra, so the supply is intra-state and CGST + SGST is correct (IGST would be an error).
- 9% of 1,00,000 = 9,000 ✔
- 1,00,000 + 9,000 + 9,000 + 0 round off = 1,18,000 ✔
- Every ledger exists in the synced Tally masters.
- INV-1025 has not been posted before.

**Accounting entry shown in the preview:**

| Ledger | Debit (₹) | Credit (₹) |
|---|---|---|
| ABC Traders | 1,18,000.00 | |
| Sales - Services | | 1,00,000.00 |
| Output CGST | | 9,000.00 |
| Output SGST | | 9,000.00 |
| **Total** | **1,18,000.00** | **1,18,000.00** |

**Output:** see `C_Sample_Output_Tally_XML/sample_sales.xml`. In Tally's convention a debit is written as a negative amount with `ISDEEMEDPOSITIVE = Yes`, and a credit as a positive amount with `No`.

---

## Worked example 2: Sales with stock items (inter-state, 2 lines)

INV-1026 has two rows (Steel Rod 12mm, 100 Kg @ ₹55, and Office Chair, 2 Nos @ ₹4,500) to a Gujarat customer.
- The rows are grouped into **one invoice** because they share the invoice number.
- The supply is inter-state, so **IGST 18%** applies: ₹2,610.
- The items match Tally stock items, so the XML is created in **Item Invoice** mode with quantity, unit and rate.

## Worked example 3: Purchase with ineligible ITC

MOS-4471 is a pantry-items bill from Metro Office Supplies with ITC marked **Ineligible**.
- The GST of ₹360.10 is **added to the Office Expenses ledger** instead of Input CGST/SGST, which is the correct treatment for blocked credit.
- Round off of −0.60 brings the total to ₹2,360.

## Worked example 4: Journal

JV-001 is Salary Dr ₹50,000 (cost centre: Head Office) / Salary Payable Cr ₹50,000. If the debits and credits did not match, the application would block the entry.

## Worked examples 5 and 6: Bank Receipt and Bank Payment

- **Receipt:** HDFC Bank Dr ₹1,18,000 / ABC Traders Cr, with UTR, settled **against bill INV-1025**.
- **Payment:** Sharma Suppliers Dr ₹59,000 / ICICI Bank Cr (against SS/2026/881). Also Bank Charges ₹236.

---

## Example of the application catching errors

A deliberately wrong journal produced these messages (screen output):

| Row | Column | Message |
|---|---|---|
| 2 | Debit | Voucher is not balanced: Total Debit 50000.00 vs Total Credit 45000.00 (difference 5000.00). It will not be posted. |
| 3 | Ledger | Ledger "Salaries Payable" does not exist in Tally master data. |
| 4 | Voucher Date | "31-13-2026" is not a valid date. Use DD-MM-YYYY. |

The **Confirm & Post** and **Download XML** buttons stay disabled until the Excel file is corrected.

## How to try these examples

Start the application, which is in **Demo Mode** by default. Open any voucher page, click **Download filled sample**, then upload it. You can also upload the files from `B_Sample_Input_Excel` directly.
