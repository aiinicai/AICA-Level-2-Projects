# Demo Script: Presenting and Recording

Total time about 7 minutes. Each scene gives what to **do** on screen and what to **say**. Read the "say" lines in your own words.

## Setup before you record

1. Open a terminal in the project folder and run:
   ```
   python prepare_demo.py --launch
   ```
   This builds a clean `demo_workspace` folder with the fictional data and opens the tool. You can repeat this command to reset everything for another take.
2. Keep the demo folder open in File Explorer in a second window (to pick files and show the checked output).
3. Passkey for the demo: `Demo@1234`.
4. Recording: on Windows press **Win + G** (Xbox Game Bar) or use OBS Studio. Record at 1080p with the microphone on, close notifications and other windows, and zoom the screen to 125 percent if text looks small.
5. Optional second window: a terminal ready to run `python tests/test_vendor_name_matching.py` for the closing scene.

---

## Scene 1: The problem (0:00 to 0:45)

**Do:** Show the tool window, still empty.

**Say:** "Before a bulk payment goes out, someone has to confirm that every account number really belongs to the vendor on the payment. Done by eye, this is slow, and the dangerous error is easy to miss: a valid account that belongs to the wrong party. This tool, Vendor Name Matching, does that check in seconds and leaves a record."

## Scene 2: Tour of the window (0:45 to 1:15)

**Do:** Point to the four buttons and the three cards.

**Say:** "There are four actions: check a payment file, reset, edit the vendor master, and open the output folder. The cards show total, matched and not matched. Everything runs on a master vendor list kept in one folder."

## Scene 3: A mixed payment file (1:15 to 3:00)

**Do:** Click **Select Payment File and Check**, choose `Payment_Demo_Mixed.xlsx` from the demo folder. Wait for the popup, then click OK.

**Say:** "Twelve payments. Five matched, seven not matched." Then walk down the rows:

- **Rows 1 to 5 (green):** "These matched even though the data is written differently: 'Private Limited' instead of 'Pvt Ltd', capital letters, 'and' instead of an ampersand, a lower case IFSC, spaces and hyphens inside the account number, and an account number starting with zeros. The tool cleans all of this before comparing."
- **Rows 6 and 7:** "A wrong last digit in the account number, and a wrong IFSC. Neither is in the master."
- **Rows 8 and 9, the important ones:** "Here the bank details are valid but they belong to a different vendor. Row 9 uses Nova Safety's account under Kaveri Aggregates' name. The remark shows the registered name, so the reviewer sees the problem immediately. A name only check would have passed this."
- **Rows 10 to 12:** "Missing IFSC, missing name, missing account number."

**Do:** Click **Open Output Folder**, open the new `Payment_Demo_Mixed_Checked_...xlsx` in Excel.

**Say:** "The result is saved as a new file with Status and Remarks added. The original is never changed, and every run is a separate record."

## Scene 4: A clean file (3:00 to 3:30)

**Do:** Click **Reset**. Check `Payment_Demo_AllMatched.xlsx`.

**Say:** "Reset clears the screen for the next file. This file is clean: five out of five matched."

**Print check (optional, 30 seconds):** Click **Print Verified PDF**. Say: "Every line is matched, so the PDF is created with all the columns from the original file." Click **No** when asked to open it, or **Yes** to show it. To show the control, Reset, check `Payment_Demo_Mixed.xlsx` and click **Print Verified PDF**: "Seven lines are not matched, so printing is refused and no PDF is created."

## Scene 5: A vendor that is not yet in the master (3:30 to 4:00)

**Do:** Click **Reset**. Check `Payment_Demo_NewVendors.xlsx`.

**Say:** "Three new vendors, none of them in the master yet, so all three are flagged. Now I will add them the proper way." Click **Reset**.

## Scene 6: Admin access to the master (4:00 to 4:30)

**Do:** Click **Edit Vendor Master**. Set the passkey `Demo@1234` twice.

**Say:** "The master is the control point of the whole process, so editing it needs an admin passkey. It is set on first use, stored only as a salted hash, and three wrong attempts lock the editor for a minute."

## Scene 7: Duplicates are not allowed (4:30 to 5:10)

**Do:** Click **Add Row**. Type the name `Sunrise Cement Pvt Ltd`, the IFSC `HDFC0001234` and the account number `50100123456789`. A warning appears. Click OK. Then click **Save Master**.

**Say:** "I am entering a vendor that already exists. The tool warns me at once, highlights both rows in red, and refuses to save. The same account and IFSC can never be in the master twice, even if the spacing or the vendor name is different. Otherwise a payment could match against either name." Select the new row and click **Delete Selected Row(s)**.

## Scene 8: Bulk upload (5:10 to 6:00)

**Do:** Click **Bulk Upload**, choose `Bulk_Upload_Demo.xlsx`, click **Add to Existing**. Read the summary.

**Say:** "This file has its columns in a different order and an extra column, and the tool still reads it, because it matches columns by name. Three vendors added. Two duplicates skipped. One row skipped because the account already belongs to another vendor under a different name. One incomplete row skipped. Nothing is saved yet, so I can review."

**Do:** Click **Save Master**, then OK. Point to the backup path in the message.

**Say:** "Saving makes an automatic backup of the previous master first."

**Do (optional, 15 seconds):** Click **Download Master** and show the Excel export. Click **Close**.

## Scene 9: Proof that the master drives the result (6:00 to 6:30)

**Do:** Check `Payment_Demo_NewVendors.xlsx` again.

**Say:** "The same file that failed earlier now shows three out of three matched, because the master was updated. That is the point: the check is only as good as the master, and the master is protected."

## Scene 10: Quality and close (6:30 to 7:00)

**Do:** Switch to the terminal and run `python tests/test_vendor_name_matching.py`. Let it finish with `OK`.

**Say:** "The tool is backed by 43 automated tests covering matching, duplicates, the passkey, bulk upload and the editor window, plus demo data with the correct answer for every row. It is limited to Excel files and uses strict name matching on purpose. Next steps would be CSV support and review suggestions for near matches. Thank you."

---

## Checklist for the reviewer demo

- [ ] Mixed file: 12 rows, 5 Matched, 7 Not Matched
- [ ] Rows 8 and 9 show the registered vendor name in Remarks
- [ ] Duplicate entry is blocked and Save is refused
- [ ] Bulk upload summary: 3 added, 2 duplicates, 1 name conflict, 1 incomplete
- [ ] New vendors file: 0 Matched before, 3 Matched after
- [ ] Print Verified PDF is refused for the mixed file and creates a PDF for the all matched file
- [ ] All 43 tests pass
