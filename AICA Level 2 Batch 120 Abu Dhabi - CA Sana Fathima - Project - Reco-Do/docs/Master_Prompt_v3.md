# MASTER PROMPT v3 — Reco-Do (paste everything below this line into Claude Code / Antigravity)

---

You are a senior full-stack engineer and a chartered-accountant-level domain expert in reconciliations. Build **Reco-Do**, a **Windows desktop application (.exe)** for accounting professionals. It simplifies daily reconciliations, adds AI help only when the user asks for it, and includes a set of document and data tools. Build it end to end. I am a finance professional but NOT a programmer: you must create every file, install every dependency, run the app yourself, test it, package the .exe, and at the end give me plain-English steps to install and run it.

This is my **capstone project and will be published on GitHub**, so the repository must be clean, documented and reproducible (see §10).

Work in phases. After each phase, run the app, run the tests, fix errors, and tell me what to check in the app before moving on.

**What changed from v2:** the product is named **Reco-Do**; it is a **Windows .exe built with Electron** (not a browser web app); sample files for every live module and tool are bundled with a one-click **"Try with sample files"** button; the repository is structured for GitHub.

**What changed from v1:**
- **General Reconciliation is now Live** and is part of this build: any two files, any columns matched, amount optional.
- **GL Reconciliation and Credit Card Recon remain Phase 2.** Show them as "Coming soon". Do not build them in this round, but keep the design ready so they can be added later as configuration only.
- **New "Tools" section** on the dashboard and sidebar with six stand-alone tools: PDF → Excel, Excel → PDF, Merge PDFs, Split PDF, Merge Files, Data Cleaner. These are general-purpose tools that work on any file. They are **not** linked to any reconciliation module.

## 1. Tech stack (do not change without asking me)

- **Desktop shell:** Electron, built with `electron-vite` (main, preload and renderer in TypeScript) and packaged with `electron-builder` into:
  - `Reco-Do-Setup-<version>.exe`: a normal Windows installer (Start menu + desktop shortcut, uninstaller).
  - `Reco-Do-<version>-portable.exe`: a single file that runs without installing.
  - App icon, window title "Reco-Do", minimum window size 1280 × 800, no default Electron menu bar.
- **Security:** `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`. The renderer talks to the main process only through a small typed `preload` API (open file dialog, save file dialog, AI call, secure key storage). A Content-Security-Policy blocks all network access from the renderer.
- **Fully offline:** every library, font, OCR worker and language file is bundled inside the app. No CDN. The app must work with the network cable unplugged, except the optional Smart Recon AI call.
- **Frontend (renderer):** React + Vite + TypeScript, Tailwind CSS, shadcn/ui components, lucide-react icons. Use a hash router.
- **File reading:** SheetJS (`xlsx`, official build from cdn.sheetjs.com) for reading .xlsx/.xls/.csv, parsed **inside the app** (renderer).
- **Formatted Excel writing:** ExcelJS. Use it for every Excel file the app produces (recon export and all tools), because SheetJS community edition cannot write bold headers, fills, frozen panes or column widths.
- **PDF reading:** `pdfjs-dist` (text with x/y positions, page rendering to canvas).
- **OCR for scanned PDFs:** `tesseract.js`. It runs **inside the app**, and its worker, core and English language data must be bundled with the app so OCR works offline with no download at run time.
- **PDF writing / editing:** `pdf-lib` (merge, split, reorder, rotate, delete pages); `jspdf` + `jspdf-autotable` (Excel → PDF).
- **Zip downloads:** `jszip` (when a tool produces several files).
- **Matching engine:** pure TypeScript module (`/src/engine`), no UI code inside it, fully unit-tested with Vitest.
- **Tool engines:** pure TypeScript modules in `/src/tools/<tool-name>` (no UI code), fully unit-tested with Vitest. The shared header detection, junk-row detection and number/date parsing live in one shared module (`/src/shared/parsing`) used by both the recon wizard and the tools. Do not write them twice.
- **Storage:** IndexedDB (via `idb`) for saved column mappings, General Recon templates, tool recipes, recon history and settings. No server database.
- **AI (Smart Recon only):** your choice of AI provider (Claude, ChatGPT, Gemini, DeepSeek, or any OpenAI-compatible service, including local models), called from the **Electron main process** (not the renderer) with the user's own API key: Anthropic Messages API, OpenAI Responses API, Gemini generateContent, DeepSeek or any OpenAI-compatible Chat Completions endpoint. Provider and model are fields in Settings (default: Anthropic with a current Claude Sonnet model). Each provider's key is encrypted with Electron `safeStorage` (Windows DPAPI) and stored only in the app's user-data folder on this machine; masked in the UI, with a "Forget key" button. The AI connection may reach only the chosen provider's official API host, or the exact base URL the user saved for an OpenAI-compatible service (https, or http only for localhost). The key never appears in the renderer after it is saved. **No tool uses AI.** The app is fully usable without an API key.
- **Saving files:** every export or tool output opens the native Windows "Save as" dialog (via the preload API) with a sensible default name.
- **Export:** Excel export (one workbook, multiple sheets) and a PDF summary (generate a real PDF file, e.g. Electron `printToPDF` of a print-styled page).
- **Privacy rule:** No file data ever leaves the computer except the specific unmatched rows sent to Smart Recon, and only after the user clicks "Run Smart Recon" and sees a preview of exactly what will be sent. **All six tools run 100% on this computer with no network calls**. Show "Runs on this computer. Nothing is uploaded." on every tool screen.

## 2. Layout and look

Match the mockup images in `docs/mockups/` (mockups 2 and 3 still show the old working name "ReconPro" in the logo; use "Reco-Do"):
1. `RecoDo_1_Home_Dashboard.png`: Home
2. `RecoDo_2_Bank_Recon_Setup_Mapping.png`: wizard Setup (Map & Rules)
3. `RecoDo_3_Recon_Results_SmartRecon.png`: wizard Results + Smart Recon
4. `RecoDo_4_General_Recon_Setup.png`: General Reconciliation Setup
5. `RecoDo_5_Tool_PDF_to_Excel.png`: PDF → Excel tool (use the same two-panel layout, options on the left and preview on the right, for every tool)

- Left navy sidebar (#0F2A44) with logo "Reco-**Do**" ("Do" in teal #3FC3A0), sections:
  - Dashboard
  - **MODULES:** Bank, AR, AP, General, GL (small "P2" tag), Credit Card (small "P2" tag)
  - **TOOLS:** PDF → Excel, Excel → PDF, Merge PDFs, Split PDF, Merge Files, Data Cleaner
  - **WORKSPACE:** Mappings & Templates, Recon History, Settings & API Key
- Light grey canvas (#F4F6F9), white rounded cards, primary blue #1D6FD8.
- Status colours used everywhere consistently: Matched green #11865F, Doubtful amber #A86B00, Likely orange #C25500, Unmatched red #C0292B, AI suggestion purple #5A43D6.
- Numbers right-aligned, thousand separators, 2 decimals, currency label (default AED, configurable). Dates shown as DD-MMM-YYYY.

## 3. Home dashboard (Screen 1)

- **KPI row** from recon history: recons this month, average auto-match rate, open items to review (count + amount), oldest open item (days + account).
- **Reconciliation modules**, six cards in a 3 × 2 grid:
  - Row 1: Bank Reconciliation, AR Reconciliation, AP Reconciliation, all **Live**.
  - Row 2: **General Reconciliation (Live)**, GL Reconciliation (**Phase 2**), Credit Card Recon (**Phase 2**). Phase 2 cards are visually dimmed, clickable, and show a "Coming soon" page.
  - The General card footer shows the number of saved templates and the most recent one.
- **Document & data tools**: a row of six compact tool cards (icon, name, one-line description, "Open →"), with the "All tools run on this computer. Files are never uploaded." note on the right of the section header.
- All modules share ONE engine and ONE wizard; modules differ only in defaults (labels, default sign convention, default tolerances, key types, output report layout). Build it so adding GL / Credit Card later is configuration, not new code.

## 4. The reconciliation wizard (shared by all modules)

Stepper across the top: **1 Upload → 2 Map & Rules → 3 Reconcile → 4 Smart Recon → 5 Review & Export.**

### Step 1 — Upload
- Two drop zones that accept .xlsx / .xls / .csv. If a PDF is dropped, explain in plain words that the wizard reads Excel/CSV and that the PDF → Excel tool (Tools section) can convert it first. Do not convert inside the wizard.
- Labels by module:
  - Bank: "Bank statement" vs "General ledger extract"
  - AR: "Our AR ledger (customer account)" vs "Customer's statement of account"
  - AP: "Our AP ledger (supplier account)" vs "Supplier's statement of account"
  - **General: editable name fields for each side** (default "File A" / "File B"; e.g. "HR employee master" vs "WPS payroll register"). These names replace "File A / File B" everywhere afterwards: column headers, tabs, KPI cards, export sheet names and the statement.
- Header detection: files often have logos/address lines on top. Scan the first 30 rows and pick the row that looks most like a header (most non-empty text cells, followed by rows containing dates/numbers). Show "Header found on row N" with an option to change N.
- If a workbook has several sheets, let me pick the sheet.
- Ignore blank rows, subtotal rows, "Opening balance"/"Closing balance"/"Total" rows (flag them, don't delete silently; show "5 rows excluded" with a list).
- Capture opening and closing balances if present (needed for the reconciliation statement).
- Show **all detected columns as chips** for each file ("7 columns identified"), plus row count and a 10-row preview.

### Step 2 — Map & Rules
- **Match-key table.** Rows = match keys; columns = Use (checkbox), Key name, Column in File A (dropdown), Column in File B (dropdown), Type, Rule/Tolerance.
  - Bank / AR / AP default keys: **Reference**, **Date**, **Amount**. "+ Add key" lets me add any other pair (e.g. Cheque No ↔ Cheque No, Invoice No ↔ Doc No, Party ↔ Customer name).
  - **General:** no fixed default keys. I pick **any column in File A to match any column in File B**, as many pairs as I want. **Amount is optional.** A General recon can run on IDs/text alone (e.g. Emp ID ↔ Employee No, IBAN ↔ IBAN).
- **Key types** (every key has one):
  | Type | Rules available | Can identify a record on its own? |
  |---|---|---|
  | **ID / code** | Exact / Contains / Normalised | Yes |
  | **Text** | Exact / Contains / Normalised | Only if I tick "ID key" on that row |
  | **Amount** | Exact / ± fixed / ± % | Yes |
  | **Number / Quantity** | Exact / ± fixed / ± % | Yes |
  | **Date** | Exact / ± N days | **Never** (date-only is never a match) |
  - In Bank/AR/AP, Reference is Text with "ID key" ticked by default.
  - The wizard refuses to run unless at least one used key can identify a record. Message: "Add at least one ID, Amount, Number or ID-key Text column."
- **Auto-suggest pairs** using header-name similarity **and** a sample of value overlap (e.g. "Emp ID ↔ Employee No · 92% values overlap"). Examples: "Value Date"/"Posting Date" → Date; "Reference"/"Remarks"/"Narration"/"Description" → Reference; "Debit","Credit","Amount","Dr","Cr" → Amount. Suggest a type for each column from its values. **I must confirm every suggestion.**
- **Amount handling** (when an Amount key is used): support (a) one signed amount column, (b) separate Debit and Credit columns, (c) amount + Dr/Cr indicator column. Convert everything internally to one signed number.
- **Sign convention toggle** (shown only when an Amount key is used): "Same sign" / "Inverse sign" with a plain-English explanation underneath, e.g. "Bank Credit = GL Debit". Defaults: Bank = Inverse, AR = Inverse, AP = Inverse, Credit Card = Inverse, GL/General = Same. Show a live preview of the first likely pair so I can see if the sign is right; if >80% of amounts only match with the opposite setting, warn me.
- **Tolerances:**
  - Date: exact / ± N days (default ±3 for Bank **and General**, ±7 for AR/AP).
  - Amount: exact / ± fixed amount / ± % (default exact).
  - Reference / ID / Text: Exact text / Contains (A's value appears inside B's text or vice versa) / Normalised (ignore case, spaces, dashes, leading zeros, prefixes like "CHQ", "FT", "INV", "REF").
- **Save mapping** with a name (e.g. "ENBD Current A/c ↔ GL 101200"). When I upload files with the same column headers again, auto-load the saved mapping.
- **General templates (nice to have, build after the core General flow works):** "Save as template" stores the side names, key pairs, types, rules, tolerances and sign setting under a name (e.g. "Payroll vs HR master"). Templates appear in "Load template ▾", on the General dashboard card, and in Workspace → Mappings & Templates (rename, duplicate, delete). If this cannot be completed cleanly, tell me and leave it out rather than shipping it half-done.

### Step 3 — Reconcile (deterministic, no AI)

For every candidate pair, test each selected key (pass/fail). Then classify:

| Tier | Rule | Meaning |
|---|---|---|
| **Matched** | All selected keys pass | Closed, no review needed |
| **Doubtful** | Exactly one key fails (e.g. 2 of 3 pass) | Must be reviewed |
| **Likely** | Only one key passes, AND that key can identify a record (Amount, Reference, ID, Number, or ID-key Text) | Low-confidence possibility |
| **Unmatched** | Nothing above | Reconciling item |

**Tiers with fewer than 3 keys** (applies to every module, mostly General):
- **1 key used:** pass = Matched, fail = Unmatched. No Doubtful or Likely.
- **2 keys used:** both pass = Matched; only one passes **and it can identify a record** = Likely; otherwise Unmatched. (No Doubtful, because "one fails" and "one passes" are the same thing with 2 keys.)
- **3+ keys:** table above as written.

Critical rules — implement exactly:
1. **One-to-one only in this step.** Each line can be used once. Assign in order: Matched first, then Doubtful, then Likely. Within a tier, prefer the pair with the closest date, then smallest amount difference (when those keys exist), then the most keys passed.
2. **Date-only is never a match.** A pair where only the date agrees is Unmatched (too many false positives).
3. **Duplicates:** if one line has 2+ equally good candidates (e.g. three payments of 1,000.00 on the same day, or the same Employee ID twice), do not guess. Mark them Doubtful with reason "Multiple identical candidates" and show all candidates.
4. Every pair stores a **reason string** in plain English, e.g. "Reference and amount agree; date differs by 5 days", "Employee ID and IBAN agree; name differs ('Mohd Rafi' vs 'Mohammed Rafi')", or "Reference and date agree; amount differs by 90.00 (possible transposition 8,450 vs 8,540)". Detect and label transposition errors (difference divisible by 9) and bank-charge style differences (small difference, amount within 1%).
5. Engine must handle 50,000 rows per side in under 10 seconds. Use hash maps on every identifying key's normalised value (amount buckets for amount tolerance) to find candidates; never compare every row with every row.

### Step 4 — Smart Recon (AI, optional)

Runs ONLY on lines still Unmatched (and optionally Doubtful). Panel with: API key field (masked), checkboxes, "Preview data to be sent", "Run Smart Recon".

Split the work between code and AI — this is important:
- **Done by code (not AI):**
  - **One-to-many / many-to-one sum matching** (only when an Amount key is used): find groups of up to 5 lines on one side whose total equals one line on the other side (within amount tolerance), restricted to the date window and, where a party/name column exists, the same party. Use a bounded subset-sum search; stop after N candidates and report if search was capped.
  - **Partial reference:** extract tokens (digits ≥4 long, alphanumeric codes) from references/IDs and look for them inside the other side's text columns.
- **Done by AI (the provider chosen in Settings):** fuzzy text understanding, e.g. "Al Noor Trdg" = "AL NOOR TRADING LLC", narration "salary Sep" vs GL "Payroll September", "Mohd Rafi" = "Mohammed Rafi", reference written differently, and ranking/explaining the code-generated group candidates.
- Send the AI only: row id, the mapped key columns (date, signed amount, reference/remarks text, party, or the General key columns). Option "Mask party names" replaces names with stable tokens. Batch rows (max ~200 per call), ask for **strict JSON** back: `[{a_ids:[], b_ids:[], confidence:0-100, reason:""}]`. Validate the JSON. Code discards, never shows: any suggestion whose amounts do not actually reconcile (when Amount is used), any suggestion referring to unknown ids, and any suggestion that reuses an already-matched line.
- Show token/cost estimate before running and handle API errors (bad key, rate limit) with clear messages.
- **AI never auto-matches.** Every AI suggestion appears in the "AI Suggested" tab with Approve / Reject. Approved ones move to Matched with label "Matched — AI assisted (approved by <user>)".

### Step 5 — Review & Export (Screen 3)

- KPI cards: Matched, Doubtful, Likely, Unmatched (A / B counts), AI Suggested pending, each with count and amount (count only when no Amount key is used).
- Tabs: Matched | Doubtful | Likely | Unmatched – File A | Unmatched – File B | AI Suggested (use the module's side names).
- Each row shows both sides side by side, a ✓ / ✗ per key, the difference, and the reason string. Actions: Accept (moves to Matched), Reject (splits back to Unmatched), Add note. Bulk accept/reject with checkboxes. Manual match: tick lines on both sides and click "Match selected" (allow 1:many manually; totals must agree or I must enter a reason).
- **Audit trail:** every decision logged (user, timestamp, before/after, note). Matched items are locked once the recon is finalised.
- **Finalise & sign off** button: requires Doubtful and AI Suggested tabs to be empty (accepted or rejected); records preparer name and date.

**Excel export (formatted with ExcelJS: bold frozen header row, autofilter, sensible column widths, number format `#,##0.00`, dates DD-MMM-YYYY, status colours on the tier column) — sheets:**
1. *Summary*: module, account/side names, period, files used, mapping/template used, counts and amounts per tier, preparer, date.
2. *Reconciliation Statement*
   - Bank: Balance as per bank statement → less unpresented payments (in GL, not in bank) → add uncredited deposits (in GL, not in bank) → ± bank items not in GL (charges, interest, direct credits) → Adjusted balance; compare to balance as per GL; show unexplained difference (should be 0.00).
   - AR/AP: Balance as per our books → items in our books not in theirs → items in theirs not in ours → balance as per their statement; unexplained difference.
   - **General with an Amount key:** Balance per [File A name] → less items in A not in B → add items in B not in A → = Balance per [File B name]; unexplained difference (should be 0.00).
   - **General without an Amount key: Record-count statement:** Records in A = Matched + Doubtful/Likely pending + Only in A; Records in B = Matched + Doubtful/Likely pending + Only in B; check line shows any count difference (should be 0).
3. *Matched (100%)*: no action needed.
4. *To Reconcile — ours* and *To Reconcile — theirs* (or bank, or the General side names): unmatched items with ageing (0-30, 31-60, 61-90, 90+ days) when a Date key exists.
5. *Doubtful & Likely*: each pair with tier, which keys passed/failed, difference, reason, my decision/note.
6. *AI Assisted*: approved AI matches with confidence and reason.
7. *Audit Log*.

## 5. Module specifics

- **Bank:** File A = bank statement, File B = GL cash account. Default inverse sign. Common narration patterns (FT, TT, CHQ, POS, SALARY, CHARGES, INTEREST) used for reference normalisation and for auto-labelling unmatched bank-only items ("Probable bank charge – post JV").
- **AR:** File A = our customer ledger, File B = customer's SOA (their AP view of us). Default inverse sign. Prefer Invoice No as the reference key; detect credit notes and payments on account.
- **AP:** File A = our supplier ledger, File B = supplier's SOA. Default inverse sign. Flag invoices in supplier SOA missing from our books as "Possible unrecorded liability".
- **General (Live):** any two files with user-named sides. No fixed keys; any column ↔ any column; Amount optional. Defaults: same sign, date ±3 days, amount exact, text Normalised. Typical uses to test against: payroll register vs HR master (no amount), intercompany A vs B (with amount), asset register vs physical count (tag no + quantity), vendor master vs bank beneficiary list.
- **GL / Credit Card (Phase 2):** NOT built in this round. Show "Coming soon". The module configuration system must allow adding them later with configuration only.

## 6. Tools (stand-alone, Tools section)

General rules for every tool:
- Opens from the dashboard tool card or the sidebar. Not connected to any reconciliation module and does not hand files to the wizard. Output is **download only**.
- Two-panel layout like mockup 5: options on the left, live preview on the right, primary button "Download …".
- 100% on this computer, no network calls. Show progress for anything over 1 second, with a Cancel button.
- Every Excel output is formatted (bold frozen header, autofilter, column widths, real numbers with `#,##0.00`, real dates DD-MMM-YYYY).
- Output file name defaults to the source name with the new extension; editable.
- Clear plain-English errors (corrupt file, unsupported type, empty result).
- **Password-protected PDFs are not supported.** Detect them and say: "This PDF is password-protected. Remove the password first, then try again."
- **Recipes (automation of manual work):** PDF → Excel, Merge Files and Data Cleaner let me "Save settings as recipe" (name + all chosen options and column renames). Next month I pick the recipe, drop the new file, and download. Recipes are stored in IndexedDB and listed under Workspace → Mappings & Templates.

### 6.1 PDF → Excel
Purpose: convert **any** table-style PDF (bank statements, SOAs, reports, price lists, registers) into a properly formatted Excel file.
- **Digital PDFs:** extract text with positions using pdf.js; rebuild rows by grouping words on the same line (y-position) and columns by clustering x-positions across the page; handle multi-line cells (a description wrapping onto a second line belongs to the row above when that line has no date/amount).
- **Scanned PDFs:** detect per page (no or almost no text layer). Render that page to a canvas at good resolution and run on-device OCR with tesseract.js (word boxes + confidence), then rebuild the table the same way. A file may mix digital and scanned pages; show which pages used OCR. Cells with OCR confidence below 85% are shaded amber in the preview **and** in the Excel output, with a note in a "Read me" sheet. No AI, no upload.
- **Output layout toggle:**
  - **Raw tables (default):** keep the PDF's own column headers and order.
  - **Bank statement layout:** map to Date · Value Date · Description · Reference · Debit · Credit · Balance. Suggest the mapping from headers; I confirm or change it. Columns not present stay empty.
- **Options:** page range (All / e.g. "1-3, 5"); join tables that continue across pages; remove repeated page headers and footers (page numbers, bank address, "continued"); convert text numbers and dates to real values (handle `1,234.50`, `(1,234.50)`, `1,234.50-`, `1,234.50 CR/DR`, DD/MM/YYYY vs MM/DD/YYYY: ask when ambiguous); one sheet per table vs all in one sheet; add a "Page" column for traceability.
- **Preview:** page thumbnails, extracted table, "Excluded rows (N)" tab listing rows dropped as headers/footers/blank (never drop silently). I can click a column header to rename it or change its type (text / number / amount / date) before download.
- **No balance/quality check** is required in this tool.
- Performance target: a 50-page digital PDF in under 10 seconds; OCR shows per-page progress.

### 6.2 Excel → PDF
- Pick a file (.xlsx/.xls/.csv), the sheet(s) and optionally a range; header row auto-detected (shared module).
- Options: portrait / landscape / auto; fit all columns to page width; repeat header row on every page; page numbers "Page x of y"; title line and optional subtitle (e.g. company name, period); optional totals row for chosen amount columns; keep number and date formatting; gridlines on/off.
- Preview of the first page before download. Output is a real PDF file (jsPDF + autotable), not the print dialog.

### 6.3 Merge PDFs
- Drop several PDFs; drag to reorder files. Expand any file to page thumbnails to reorder, rotate or remove individual pages.
- Show total page count; "Download merged PDF" (pdf-lib).

### 6.4 Split PDF
- Modes: (a) every N pages; (b) custom ranges, one file per range (e.g. "1-3, 4-6, 7"); (c) extract selected pages (click thumbnails) into one new file; (d) one file per page.
- Output: a single PDF, or a .zip when several files are produced. File names include the page range (e.g. `Statement_p1-3.pdf`).

### 6.5 Merge Files
- Combine many Excel / CSV files **and PDFs (converted via the PDF → Excel engine)** into **one** formatted Excel sheet, e.g. three monthly statements into one.
- Header detection per file (shared module). Align columns by header name; when headers differ, show a column-matching grid so I can map "Txn Date" in file 1 to "Date" in file 2, or keep both.
- Adds "Source file" and "Sheet / Page" columns. Option to sort by a chosen date column. Repeated header rows and total rows inside files are excluded and listed.
- Summary line per file (rows taken, rows excluded).

### 6.6 Data Cleaner
- Load one Excel/CSV file and sheet; header detection as in the wizard.
- Cleaning actions (each a checkbox; each shows how many cells/rows it will change before I apply):
  - Remove blank rows, repeated header rows, subtotal/total/opening/closing rows (listed, not silent).
  - Trim extra spaces and non-printing characters.
  - Convert text numbers to numbers (same formats as 6.1, including `CR/DR` and brackets).
  - Convert text dates to real dates (ask DD/MM vs MM/DD when ambiguous).
  - Split one signed amount into Debit / Credit columns, or combine Debit / Credit into one signed Amount.
  - Fill down blank cells from merged-cell layouts (choose columns).
  - Flag or remove exact duplicate rows (flagged by default).
  - Change text case for chosen columns (UPPER / Proper / lower).
- Before/after preview with changed cells highlighted; "Download cleaned file" keeps the original sheet as a second sheet "Original" for audit.

## 7. Testing (mandatory)

- Create `/sample-data` with realistic dummy files (fictional companies and people only), one folder per live module and one for tools, generated by `npm run samples` (scripts in `/scripts/generate-samples`, fixed random seed so the output is identical every time):
  - **`bank/`** (bank ~300 rows, GL ~290 rows) deliberately containing: exact matches, date shifts, amount typos (transposition), missing references, duplicates of the same amount/day, a 1-bank-to-3-GL split, a 2-bank-to-1-GL combination, bank charges, a statement with 6 junk rows above the header, and separate Dr/Cr columns. Opening and closing balances must make the bank reconciliation statement tie to 0.00.
  - **`ar/`**: our customer ledger vs customer SOA (~60 rows each): matching invoices, a credit note, a payment on account, a payment in transit (in ours, not theirs), an invoice they have not booked, an invoice amount disputed by 90.00 (transposition), invoice numbers written differently ("INV-00123" vs "123").
  - **`ap/`**: our supplier ledger vs supplier SOA (~60 rows each): matching invoices, a supplier invoice missing from our books ("Possible unrecorded liability"), a debit note, a payment in transit, a duplicate invoice in the SOA, one small rounding difference.
  - **`general/`**:
    - **No amount:** HR employee master (~180 rows) vs payroll register (~175 rows) with: IDs with/without leading zeros, name spelling variants, an employee only in HR, an employee only in payroll, a duplicated Employee ID, and an IBAN mismatch.
    - **With amount:** intercompany Entity A vs Entity B (~100 rows each, same-sign).
  - **`tools/`**: a 6-page digital bank statement PDF with repeated page headers and wrapped descriptions; a non-bank table PDF (e.g. price list); a PDF with one scanned (image-only) page; a password-protected PDF (to test the error message); two PDFs to merge and a 12-page PDF to split; three monthly Excel statements with slightly different headers for Merge Files; a sheet to print for Excel → PDF; a messy Excel file for Data Cleaner (text numbers, `CR/DR`, text dates, merged cells, blank and total rows, duplicates).
  - `sample-data/README.md` lists every planted scenario per file and the **expected result** (e.g. "Bank: 1 transposition 8,450 vs 8,540 → Doubtful"), so a demo viewer can check the app found them.
- **Demo mode:** sample files are bundled inside the .exe. Step 1 of every live module and every tool screen has a **"Try with sample files"** button that loads the matching samples in one click, so the app can be demonstrated without hunting for files.
- Vitest unit tests for: header detection, amount sign handling (both conventions, all three amount formats), each tier rule **including the 1-key and 2-key rules**, duplicate handling, date-only exclusion, refusing to run without an identifying key, General recon with no amount, subset-sum grouping, reconciliation statement arithmetic (unexplained difference must be 0.00 on the sample), record-count statement arithmetic (difference must be 0), PDF table reconstruction (row/column rebuild, wrapped lines, page joining, repeated header removal), number/date parsing variants, merge/split page counts and order, Excel → PDF page count with repeated headers, Merge Files column alignment, each Data Cleaner action, and recipe save/re-apply.
- Run tests and show me the results in plain words.

## 8. Build order

1. Project setup (Electron + electron-vite + React), GitHub repo skeleton, sample data generators, layout, sidebar (with TOOLS section), Home dashboard (static KPIs first). **Package a first .exe at the end of this phase** to prove the packaging works, and re-package at the end of every later phase.
2. Upload + header detection + preview (shared parsing module).
3. Map & Rules + key types + saved mappings.
4. Deterministic engine + tests (including 1-key / 2-key rules and no-amount recons).
5. Results screen + manual review + audit trail.
6. Excel/PDF export with reconciliation statement.
7. Smart Recon (code grouping first, then AI layer).
8. **AR, AP and General module defaults and report layouts** (General: side names, any-column mapping, record-count statement; then templates if feasible).
9. **Tools**, in this order: PDF → Excel (digital first, then OCR), Excel → PDF, Merge PDFs, Split PDF, Merge Files, Data Cleaner, then recipes.
10. Polish. (GL and Credit Card stay "Coming soon"; not built in this round.)

## 9. Hand-over

At the end, give me:
- The installer and portable .exe in `release/`, and plain-English steps to install and open Reco-Do (including what to click on the Windows SmartScreen "unknown publisher" warning, since the .exe is not code-signed).
- For developers: `npm install`, `npm run dev` (run from source), `npm test`, `npm run samples`, `npm run dist` (build the .exe).
- A one-page "How to use Reco-Do" guide in plain English for a finance user (`docs/User_Guide.md`), including a short section for each module and tool.
- A list of known limitations (e.g. OCR accuracy on poor scans, very complex PDF layouts, password-protected PDFs not supported, unsigned .exe).

## 10. GitHub repository (capstone)

- Repository root = the app. Layout:
  ```
  reco-do/
  ├─ src/main/            Electron main process (window, file dialogs, AI call, key storage)
  ├─ src/preload/         typed bridge exposed to the renderer
  ├─ src/renderer/        React UI
  ├─ src/engine/          matching engine (pure TS, tested)
  ├─ src/tools/           tool engines (pure TS, tested)
  ├─ src/shared/          parsing, number/date formats, types
  ├─ tests/               Vitest tests
  ├─ sample-data/         generated sample files + README of planted scenarios
  ├─ scripts/             sample-data generators
  ├─ docs/                Problem statement (.docx), master prompt, mockups, user guide, screenshots
  ├─ build/               app icon
  ├─ .github/workflows/   CI
  ├─ README.md  LICENSE  .gitignore  package.json
  ```
- `README.md`: project title and one-line pitch, problem statement summary (link to the Word file), feature list, screenshots of the real app (taken from the running app, saved in `docs/screenshots/`), install steps, run-from-source steps, tech stack, architecture diagram (main ↔ preload ↔ renderer, engine, tools), privacy statement, testing summary, known limitations, roadmap (GL and Credit Card in Phase 2).
- `.gitignore` excludes `node_modules/`, `out/`, `release/`, `dist/`, logs and any `.env`. **Never commit the .exe, an API key, or real client data.**
- `.github/workflows/ci.yml`: on every push, run install, typecheck and tests on `windows-latest`. `.github/workflows/release.yml`: when a tag `v*` is pushed, build the installer and portable .exe and attach them to a **GitHub Release**. This is how the .exe is shared, not by committing it.
- Small, meaningful commits per phase.

Do not skip steps, do not leave TODOs or placeholder functions, and ask me before making any assumption that changes accounting logic.
