# AuditSignOff Suite UAE - User guide

Detailed reference. Start with the main `README.md`.

## Input rules
* The **engagement fact sheet** (`templates/Engagement_Fact_Sheet.xlsx`; YAML still accepted) is typed from the trade licence, MOA, passports and Board Resolution. It is what the FS is checked against.
* **Accepted inputs**

  | Input | Formats | Notes |
  |---|---|---|
  | Engagement fact sheet | Excel, Word, PDF, JPG/PNG (templates: `Engagement_Fact_Sheet.xlsx` / `.docx`), YAML | Word/PDF/image must follow the Field/Value layout or `Field: value` lines; image/scan is OCR (flagged in the review paper). Free-form trade licence/MOA/passport scans are NOT auto-read.  Lists separated by `;`, Yes/No for flags, dates dd/mm/yyyy |
  | Liquidation tracker | Excel (`Liquidation_Tracker.xlsx`: Liquidation, NOCs, Banks sheets), YAML | Blank date = pending, `NA` = not applicable |
  | FS pack | Word, PDF (text or scanned), Excel, JPG/JPEG/PNG/TIFF | Excel, scanned PDF and images: content and tie-out checks only |
  | Trial balance | Excel, CSV | Columns: Account, Class, Debit, Credit |
* **Old formats (.doc, .xls, .rtf)** are converted to .docx/.xlsx automatically and offline, using LibreOffice if installed, otherwise Microsoft Word/Excel on the PC. If neither exists you get a message to Save As .docx/.xlsx.
* **Folder input**: in the FS tab choose *Engagement folder on this PC*, paste the folder path, press *Scan folder*. Files are sorted by name (FS pack, fact sheet, trial balance, licence, MOA/AOA, other source) and every role can be corrected before running. (Browsers cannot upload a folder, but this app runs on your PC so it reads the folder directly.)
* **Pre-fill tab**: reads trade licence, MOA/AOA, certificate, etc. (any format) and proposes company name, legal status, authority, emirate, shareholders, signatories, year end and incorporation year. Class B: each value shows its source file, matched text and confidence; OCR values are always Low; the reviewer must tick that values were checked before the fact sheet is created. FS signatories and the Board Resolution flag are not on those documents and stay for the team to enter.
* **OCR (images / scanned PDFs)**: install the Tesseract program (Windows: UB-Mannheim build), add it to PATH, then `python -m pip install -r requirements.txt`. OCR results are Class B: the reviewer confirms each OCR-based exception against the original.
* DOCX gives the full set of formatting checks. PDF supports content, tie-out, font, size and left-margin checks; alignment and top margin are not measurable from a PDF. Excel, scanned and image inputs report formatting checks as Not run.
* TB format: XLSX with columns `Account, Class (Asset/Liability/Equity/Income/Expense), Debit, Credit`.
* A check whose input is missing is reported **Not run**, never Pass.

## Limits you must know
* Tested on synthetic packs only (see `tests/`). Run Phase-0 shadow testing on 10 closed engagement files before relying on it.
* Statement tables are recognised by row labels (`Total assets`, `Total equity and liabilities`, ...). Packs with unusual labels need a label map in `params.yaml`.
* The UAE public-holiday list is intentionally empty; load the official calendar into `params.yaml: holidays` or the 20-business-day clock will be early by the number of holidays in the window.
* `standards_not_yet_effective_mentions` holds sample entries; the technical partner must sign off the list for each year-end.
* Packaging as a Windows EXE (PyInstaller / PySide6) is Phase 3 and has not been built in this prototype.


## CT + TP step by step
See `docs/CT_TP_step_by_step.md`. Module C implements a 79-check managerial-remuneration transfer-pricing checklist (`rules/catalogue.yaml`), every one automated or evidence-driven, in checklist order (sections 1.1-1.13; 1.14 keeps the firm-added sample-report checks). Section 1.8 is applied to Full Benchmarking Reports only and 1.12 to Financial Updates only (the other shows N/A); the type is read from the report cover. The old Excel checklist and its IDs were removed.

## What the Final Review Paper now shows
* Section 2 – exceptions only, each with a **page / location reference** (PDF page and printed page number; Word heading or table/row).
* Section 4 – only **exceptions and items not fully checked** (passed checks are not repeated):
  `EXC` exception · `ASSIST` the software extracted the evidence, the reviewer confirms · `r` not run, with the exact input to supply.
* TP, FS, Liquidation and Forensic modules are now covered; TP formatting checks also run on PDF reports.
* Liquidation tracker: new optional answers (partners, VAT/CT status, authority conditions, report build, FTA letter, legal) drive LQ-09/12/15/16/17/18. Optional FS fact-sheet fields `tp_related_party_total`, `ct_payable_working`, `ct_return_payable`, `vat_turnover` drive SA-40/43/45.

## Liquidation tab - documents (LQ-21 to LQ-26)
Upload the tracker plus: Board Resolution, Statement of Affairs, Liquidator's report/audit report, optional trial balance, CT/VAT registration certificates or FTA letters, optional licence/MOA (Word, PDF, Excel or image; scans use OCR). Or point to a folder and confirm the roles.
| Check | What it tests |
|---|---|
| LQ-21 | BR: company, resolution wording, liquidator, date vs tracker, shareholders named, signature block |
| LQ-22 | SOA: as-at date, assets less liabilities recomputed, deficiency (insolvency) flag, tax creditors |
| LQ-23 | Report: required sections, dates and advertisement dates vs tracker, figures vs SOA |
| LQ-24 | TB (optional): debits = credits, agrees to SOA/report within 5% |
| LQ-25 | CT and VAT registration evidenced; deregistration initiated; final CT return addressed |
| LQ-26 | Company and liquidator names consistent across documents |
Optional tracker fields `liquidator.name` and `shareholders` sharpen LQ-21/22. A missing document shows as "not checked - upload X". Grey area: a SOA deficiency under a solvent-liquidation route and the late CT registration penalty amount need Partner confirmation.

## Self-check (run before every important review)
`python doctor.py` (Windows: double-click `run_doctor.bat`). It checks Python, packages, Tesseract (found even if not on PATH), LibreOffice/Word, runs an OCR round trip and builds a review file in every tab from sample data, re-opening each output. Any FAIL line tells you the fix.
Every review file is re-opened after it is written (Word, Excel, JSON); a broken file raises an error instead of being handed over. Scanned documents add an "OCR quality warning" to the review paper.

## Review workflow (First review -> Manager -> Partner)
Tab **Review workflow**. Levels, names, roles and who may waive a point are in `rules/workflow.yaml`.
1. Create the engagement (reference, module, client, period).
2. **L1 round:** the first reviewer loads the review run (the **Review run (JSON)** download on each module result, or the .json in `out/` from the command line). Every exception becomes a numbered review point; add manual points for judgement items. Clear, reopen (reason) each point and **Close the round**.
3. Open points send the file **back to the preparer**, who answers each (Corrected / Disputed / Not applicable / Will correct next version, comment required for disputes) and submits.
4. The reviewer loads the **re-run**: points no longer found are auto-cleared; points claimed corrected but still found are **reopened**; new findings are added.
5. When no point is open the file passes to **Manager review**, then **Partner review**. Partner closing with nothing open = **sign-off** (locked). Manager/Partner may waive a point with a reason.
6. Download the **Review trail** (points, rounds with run-file SHA-256, audit log) at any time.

## Navigation
Left sidebar: **All categories** (home cards) and grouped pages - Review modules (FS, Liquidation, TP, CT, Forensic), Preparation (Pre-fill), Review control (Review workflow). Use the search box to filter. Note: uploaded files are cleared when you switch page, so finish one review before moving on (outputs and the workflow database are kept).

## Sharing with the team (Microsoft Teams)
Recommended: **one office PC runs the app** (`run_app_team.bat`); colleagues open `http://<PC-name>:8501` in their browser on the office network or VPN. Everyone then uses one workflow database and one `review_workflow\files` folder, so there are no sync conflicts. Allow port 8501 on that PC's Windows Firewall (private network only). Streamlit has no login: restrict to the office network.
- **Do not** put `workflow.db` in a OneDrive/SharePoint/Teams-synced folder that several people edit: SQLite file sync can corrupt it. Back up the `review_workflow` folder daily instead.
- **Hand-off messages:** the workflow page shows a ready-to-paste Teams message. For automatic channel posts, create a Teams channel *Workflows / Incoming webhook* and paste its URL into `rules/workflow.yaml` (`teams_webhook`). Only reference, stage, owner and counts are sent - never client figures. Leave blank to stay fully offline.
- **Assign people** per file (Preparer, First reviewer, Manager, Partner); each person sees **Waiting for you** at the top. Updated files uploaded at submit/close are stored, hashed and listed in the trail.

## Staff list (no YAML editing needed)
Review workflow page -> **Team** panel: type a name, pick Preparer / First reviewer / Manager / Partner and click Add, or upload an Excel/CSV list (columns Name, Role, optional Email; template downloadable). The "You are" box and the per-file assignment drop-downs use this list (a Manager or Partner can also be assigned lower-level roles). Until you add names, the sample names in rules/workflow.yaml are used.

## Name matching and reviewer names
- Company, shareholder and liquidator names are matched ignoring case, dash type (- / – / —), spacing and punctuation, in every module (FS, TP, Liquidation). Only genuine spelling differences are flagged.
- Pick **Prepared by / First reviewer / Manager / Partner** in the sidebar **Review team** box (from the staff list). Those names are filled on the Final Review Paper sign-off table and in the review header automatically; date and signature stay blank to sign.

## Stage sign-off and flow control
- The workflow page shows a **flow table**: Preparer -> First review -> Manager review -> Partner review, with owner, status (Signed off / In review / Pending), who signed and when, and a banner such as *PENDING - Manager review awaiting start (Meera)* plus "Next after this".
- A reviewer **cannot pass the file forward without ticking the sign-off confirmation** (name and time recorded). The preparer signs on creation and on every resubmission.
- If the preparer uploads a corrected file after a stage was signed, that stage shows **"file changed after sign-off"** so the reviewer can decide whether to re-review.
- **Stamp** the live status and sign-offs onto a Final Review Paper (.docx): banner at the top, stage table, and the paper's own sign-off table (Name/Date) filled. The review trail Excel opens on a **Flow** sheet.

## Date/time of every sign-off and the movement trail
- Every sign-off is stored with date **and time**. The stamped Final Review Paper shows them in its own sign-off table (Name / Date-time / Sign) and in a **Review movement trail** table, e.g. *18:32 Ravi - Completed First review and signed off - Passed to Manager review - Meera*.
- Link the sidebar **Review team** box to a workflow engagement: from then on every review paper generated is **stamped automatically** (status banner, stage table, trail, sign-off dates). Stamping again replaces the old block, so the Partner's copy shows all earlier members' times.
- A paper generated by a preparer records "Prepared by <name>" with the generation date/time.

## Why a paper may show names only (and the fix)
The sign-off/trail block appears only when the review is recorded in the workflow. In the sidebar **Review team** box: pick **Prepared by** (and the reviewers) and keep **"Record every review I run in the workflow"** ticked (default). The first run creates the engagement (client + module + year), assigns the people, and stamps the paper. Later stages: the reviewer opens **Review workflow**, loads the review .json, signs off; re-running or re-stamping the paper then shows each person's date/time and the movement trail. If neither a link nor auto-record is on, the sidebar warns that the paper will show names only.


## TP checklist: how each row is tested (rules_tp3.py)
* **Deterministic** (PASS / Exception): TOC text, annexure titles/pages, TOC formatting, subheading formatting, profile vs notes to accounts, remuneration split vs BIRF, rejected-comparable reasons, naming consistency.
* **Hybrid** (Exception when a real gap is found, otherwise "Review" with the evidence on the paper): functional analysis, PLI rationale, data periods, method rejection, secondary vs primary conclusion, chart scale/data/message, all of section 1.12 (Financial Update), report components, connected persons, legal references.
* **BIRF template** (`templates/BIRF_Template.xlsx`, also a download button on the TP tab): one row per recipient, columns Salary / Bonus / Allowances / End-of-service / Share-based pay / Benefits in kind. Fill it in Excel, save, upload. Any Word/PDF form with the same wording is also read.
* Optional **BIRF** upload (TP tab, or `--birf`): enables the remuneration-split and connected-person checks. Without it those rows show "Not run - upload the BIRF".
* The prior-year report must be attached after the update inside the same Word/PDF file; section 1.12 reads it from there.
* `rules/law_refs.yaml` holds the legal references and TP thresholds the report is tested against (as at 16-Oct-2026). Edit it when the law changes; unknown citations are flagged "verify".
* `rules/params.yaml`: `tp.refresh_cycle_years` (3) and `tp.range_move_pct` (25).


## Forensic tab - fraud-scenario inputs (FA-11 to FA-14)
All are optional; a check whose input is missing shows **Not run**, never Pass. Column names are matched by wording, so exact spelling is not required.
| Input | Columns | Used for |
|---|---|---|
| Bank statement (Excel/CSV) | Date, Narration, Beneficiary Name, Beneficiary IBAN, Debit, Credit, Balance | FA-12: payments outside the vendor master or into another account, employee/related accounts, swept balance, pass-through, payments missing from the GL |
| Authorised-signatory mandate | Name, Designation, Single signing limit, Joint signing above, Specimen (image file), Valid from, Valid to | FA-11 |
| Signatures (upload box, or a folder with **Browse…**) | `signature_register.xlsx` (Document, Date, Amount, Claimed Signatory, Second Signatory, Image) plus the image files: PNG, JPG, TIF, BMP, WebP or PDF scans, specimens included, all selected together | FA-11: authority, limits, copy-pasted images, resemblance to the specimen |
| FS data | Item, CY, PY with lines such as Revenue, Cost of sales, Receivables, Inventories, Payables, Net profit, Operating cash flow, Total assets | FA-13: ratios, Beneish M-score, FS vs GL, year-end cut-off |
| Stock register | Item, Location, Opening Qty, GRN Qty, Issued Qty, Adjustment Qty, Closing Book Qty, Physical Count Qty, Unit Cost, Invoiced Sales Qty, Invoiced Purchases Qty | FA-14 |
| Public holidays | dates `YYYY-MM-DD` (`--holidays`, or the box on the Forensic page) | FA-05; check them against the official UAE calendar |
Thresholds (limits, percentages, Beneish cut-off, signature similarity) are in `rules/params.yaml` under `forensic:`.
Signature screening compares the signature image with the specimen after cropping and blurring; it is a triage tool, and a forensic document examiner must confirm any suspected forgery.
