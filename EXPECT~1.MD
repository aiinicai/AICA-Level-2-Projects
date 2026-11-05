# Demo Data and Expected Results

All names, bank account numbers and IFSC codes in this folder are **fictional**. They exist only to demonstrate the tool. No real vendor or bank information is included.

| File | Purpose |
|---|---|
| `Unique_Vendor_Master.xlsx` | Demo vendor master with 12 fictional vendors |
| `Payment_Demo_Mixed.xlsx` | 12 payment rows covering every matching scenario |
| `Payment_Demo_AllMatched.xlsx` | 5 payment rows that should all match (a clean run) |
| `Payment_Demo_NewVendors.xlsx` | 3 payment rows for vendors that exist only in the bulk upload file (a before and after test) |
| `Bulk_Upload_Demo.xlsx` | A vendor list for testing Bulk Upload, with deliberate duplicates and problems |

## 1. Payment_Demo_Mixed.xlsx

Expected totals: **12 rows, 5 Matched, 7 Not Matched**.

| Sr. No. | Scenario | Expected Status | Expected Remarks |
|---|---|---|---|
| 1 | Exact match | Matched | Account, IFSC and name agree with master |
| 2 | "Private Limited" written for "Pvt Ltd" | Matched | Account, IFSC and name agree with master |
| 3 | Upper case, "AND" written for "&", full stop at the end | Matched | Account, IFSC and name agree with master |
| 4 | Lower case IFSC, spaces and a hyphen inside the account number | Matched | Account, IFSC and name agree with master |
| 5 | Account number starting with zeros (kept as text) | Matched | Account, IFSC and name agree with master |
| 6 | Wrong account number (last digit changed) | Not Matched | Account number and IFSC not found in master |
| 7 | Correct account number, wrong IFSC | Not Matched | Account number and IFSC not found in master |
| 8 | Right account and IFSC, different vendor name | Not Matched | Name differs from master. Master name: Orion Transformers Ltd |
| 9 | Another vendor's account used under a known vendor's name (account substitution) | Not Matched | Name differs from master. Master name: Nova Safety Systems Pvt Ltd |
| 10 | Blank IFSC | Not Matched | IFSC code is blank |
| 11 | Blank vendor name | Not Matched | Beneficiary account name is blank |
| 12 | Blank account number | Not Matched | Beneficiary account number is blank |

Rows 8 and 9 are the most important for payment control. The bank details look valid, but they do not belong to the vendor named on the payment. A name based check alone would miss them.

## 2. Payment_Demo_AllMatched.xlsx

Expected totals: **5 rows, 5 Matched, 0 Not Matched**.

## 3. Bulk_Upload_Demo.xlsx

The file has its columns in a different order from the master, uses the header "Beneficiary Account No." and contains an extra "Remarks" column. The tool still reads it correctly.

Load it with **Edit Vendor Master, Bulk Upload, Add to Existing** on the demo master. Expected result:

| Outcome | Count | Rows |
|---|---|---|
| Vendors added | 3 | Riverbank Concrete Works, Summit Crane Hire Services, Lotus Electricals |
| Duplicates skipped | 2 | Sunrise Cement (already in master), second Riverbank row (repeated inside the file) |
| Skipped, same account under a different name | 1 | Greenfield Power Solutions (account already belongs to Greenfield Solar Energy Pvt Ltd) |
| Skipped, incomplete row | 1 | Incomplete Row Enterprises (blank IFSC) |
| Total rows in master after upload | 15 | 12 original plus 3 added |

## 4. Before and after test with Payment_Demo_NewVendors.xlsx

| Moment | Expected totals |
|---|---|
| Before the bulk upload is saved | 3 rows, 0 Matched, 3 Not Matched (vendors not in master) |
| After Bulk Upload, Add to Existing, then Save Master | 3 rows, **3 Matched**, 0 Not Matched |

This shows that updating the vendor master immediately changes the payment check results.

## 5. Duplicate prevention (manual test)

In **Edit Vendor Master**, click **Add Row** and type the account number `50100123456789` and IFSC `HDFC0001234`. A warning appears, both rows turn red, and **Save Master** is refused until the duplicate is corrected or deleted.

## 6. Print Verified PDF

| Action | Expected result |
|---|---|
| Check `Payment_Demo_Mixed.xlsx`, click **Print Verified PDF** | Refused: "7 of 12 lines are Not Matched". No PDF is created |
| Check `Payment_Demo_AllMatched.xlsx`, click **Print Verified PDF** | PDF created with all 5 lines and every original column. `Sample_Verified_Output.pdf` shows the result |
| Click **Print Verified PDF** before checking, or after Reset | Message asking to check a file first. No PDF |
