# User Guide

## 1. Before you start

- Python 3.8 or newer is installed (IDLE is enough).
- Internet is available for the first run, so the tool can install PyQt5 and openpyxl.
- The vendor master `Unique_Vendor_Master.xlsx` is in the working folder (`C:\Day 5` by default). If it is missing, create it with **Edit Vendor Master**.

To try the tool on the fictional demo data without touching any real folder:

```
python prepare_demo.py --launch
```

## 2. Starting the tool

Open `Vendor_Name_Matching.py` in IDLE and press **F5**. The first run may take a minute while libraries install. Close the tool window before pressing F5 again.

## 3. Checking a payment file

1. Click **Select Payment File and Check**.
2. Choose the payment `.xlsx` file.
3. Read the result:
   - The three cards show Total Rows, Matched and Not Matched.
   - Each row is green (Matched) or red (Not Matched), with the reason in **Remarks**.
4. The checked file is saved as `<OriginalName>_Checked_<date_time>.xlsx` in the working folder. The original is unchanged.
5. Click **Open Output Folder** to see it, or **Reset** to clear the screen for the next file.

### Printing the verified payment file (PDF)

Click **Print Verified PDF** after checking a file.

- **Every line Matched:** a PDF is created as `<OriginalName>_Verified_<date_time>.pdf` in the working folder. It holds every column and every row of the payment file as you uploaded it, exactly as uploaded, as a plain table with no heading, extra column or footer, on A4 landscape pages with the column headings repeated on each page. A **Total** row at the end sums the Amount column. If an amount is not a number, printing is refused rather than showing a wrong total. You are then asked whether to open it.
- **Any line Not Matched:** nothing is created. A message states how many lines failed and why. Correct the payment file or the vendor master, then check again.
- The vendor master is read again at the moment you click, so the PDF always reflects the current master. The original payment file is never changed.
- Before a file has been checked, or after **Reset**, the button explains that a file must be checked first.

**Payment file layout.** Headers in row 1. The tool needs Beneficiary Account Name, IFSC Code and Beneficiary Account Number (written "Number" or "No."). Sr. No. and Amount are shown if present. Close the file in Excel first.

## 4. Managing the vendor master

Click **Edit Vendor Master**.

**First time only:** the tool asks you to set an admin passkey (at least 6 characters, entered twice). Keep it with the administrator. After that, the passkey is asked every time.

| Task | How |
|---|---|
| Add a vendor | **Add Row**, then type. Or click a cell and press Ctrl+V to paste rows copied from Excel |
| Edit a vendor | Double-click a cell |
| Delete vendors | Select one or more rows, click **Delete Selected Row(s)**, confirm |
| Find a vendor | Type in the search box (name, account number or IFSC) |
| Bulk upload | **Bulk Upload**, choose the file, then **Add to Existing** or **Replace Entire Master**. Review the summary |
| Download | **Download Master**, choose a file name |
| Change the passkey | **Change Passkey**, enter the current one, then the new one twice |
| Apply your changes | **Save Master**. Nothing changes in the real master until you click it |

### Duplicate entries

The same **Account Number + IFSC** cannot be in the master twice, even with different spacing, upper or lower case, or a different vendor name.

- A warning appears as soon as a duplicate is typed or pasted.
- The clashing rows turn red and a message appears at the bottom.
- **Save Master** is refused until the duplicates are deleted or corrected.

### Bulk upload rules

- Columns are found by header name, so order does not matter and extra columns are ignored.
- Format the account number column as **Text** in Excel before uploading, so leading zeros are kept.
- The summary shows how many vendors were added and how many rows were skipped as duplicates, name conflicts or incomplete.

### Backups

Before every save, the previous master is copied to `Master_Backups` in the working folder. The latest 20 backups are kept. To restore one, copy it over `Unique_Vendor_Master.xlsx`.

## 5. Messages you may see

| Message | What to do |
|---|---|
| Master file not found | Click **Edit Vendor Master** to create it, or place the file in the working folder |
| Master file is open in Excel | Close it in Excel and try again |
| These columns were not found in row 1 | Compare the headers listed in the message with your file |
| Too many incorrect attempts | Wait 60 seconds, then try again |
| Duplicate entry is not allowed | Delete or correct the red rows |
| Printing is not allowed. N of M lines are Not Matched | Fix the listed rows or add the vendor to the master, then check the file again |

## 6. Manual installation of libraries

If the automatic installation fails, open Command Prompt and run:

```
pip install PyQt5 openpyxl reportlab
```

## 7. Tips for administrators

- Keep the passkey with the administrator only.
- Also restrict write access to `Unique_Vendor_Master.xlsx` and `Vendor_Master_Admin.json` in Windows (Properties, Security), so that only the administrator can change them. The passkey protects the editor inside the tool, not the Excel file itself.
- A downloaded master is an unprotected copy of bank details. Store it securely.
