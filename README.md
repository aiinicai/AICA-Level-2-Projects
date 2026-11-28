# Auto Bank Statement Entry — Office Desktop Edition (C# / .NET 8 WPF)

A native, 100% offline Windows x64 desktop application built for daily CA and office Tally accounting.

## Key Advantages for Daily Office Use
- **Lean Single Portable `.exe` (~65–80 MB) with Custom App Icon**: No Python, no .NET runtime, and no launcher script needed — double-click `AutoBankStatementEntry.exe` directly from your PC or office server share.
- **Handles Large Digital PDF, Excel & CSV Statements**: Virtualized native WPF `DataGrid` (100,000+ rows smoothly), streaming `ExcelDataReader` (`.xlsx`/`.xlsm`/`.xls`/`.csv`), and `PdfPig` word-coordinate extraction for borderless digital Indian bank PDFs (AU Bank, HDFC, SBI, ICICI, Axis, etc., including password-protected PDFs).
- **Live Against-Invoice & Multi-Invoice Split (`Agst Ref`)**: Fetches open bills live from Tally for Sundry Debtors/Creditors, lets you pick a single bill, split across multiple invoices (with FIFO auto-allocate and `On Account` balance), or leave blank.
- **Local ML + Short-Form Tally Ledger Matching**: Prefilled with Indian banking seeds, learns live from every edit (cascading updates to unedited rows below, saved in the background for zero LAN lag), and maps automatically to short-form Tally ledgers (`Int Rec`, `Int from SB`, `Elec Exp`, `Ptg & Stat`, `Rep & Maint`, etc.).
- **Complete Tally Workflow**: Multi-Tally port discovery + active company detection (`$$CurrentCompany`), automatic Bank A/c last-4 digits & IFSC sync from Tally, Contra & zero-overlap detection, Opening & Closing Balance reconciliation, pre-posting Tally Backup, Missing Ledger creation prompt, zero XML created on direct push, and per-entry **Done + Failed Entries** verification popup.
- **Excel-Style Speed**: `Down`/`Up` browse ledgers without overwriting, `Tab` or click autocompletes and closes the dropdown, `Enter` keeps your typed name and jumps to the next row, `Ctrl + D` copies from above, and **AMOLED Dark / Light mode** toggles with one click.

## Build Once on Windows x64
1. Unzip `AutoBankStatementEntry_WPF.zip`.
2. Double-click **`build_office_exe.bat`** (auto-installs `.NET 8 SDK` via `winget` if not already installed).
3. Copy **`publish\AutoBankStatementEntry.exe`** to your office server or any Windows 10/11 x64 PC and double-click to run 100% offline!

## Everyday review: what the colours and ticks mean

* **Four steps** in the blue title bar: 1 Choose file → 2 Analyze → 3 Check ⚠ → 4 Post. The step you are on is
  highlighted. You can also **drag statement files** (PDF / Excel / CSV) onto the window instead of using 📂 Select File(s).
* **More rows on screen:** click **▲ Hide setup** (title bar) to fold away the Tally and Statement panels while you
  review; **▼ Show setup** brings them back (they also come back by themselves when you choose or drop a new file).
  The keyboard shortcuts are under **⌨ Keys** (point at it).
* **Tally on any port.** Detect Tally finds Tally whatever port it is set to (it reads which ports the Tally program
  itself has open, then tries the usual ones). If Tally is open but not sharing data, it says so and shows the one-time
  setting to switch on.
* **Colour strip** at the left of every row (the key is in the bottom bar): green = ready to post, amber = check it,
  grey = skipped / already in Tally / posted, red = problem (failed or balance break).
* **Bills are picked for you** when there is no doubt: if a party has exactly one open bill of exactly the entry's
  amount, on the right side (a Payment settles a bill you owe, a Receipt a bill owed to you), that bill is chosen. If two
  bills or two entries could match, nothing is picked and you choose as before.
* **Splits are remembered.** After you split an entry (e.g. Rent + GST), the next entry from the same party in the same
  direction is split the same way at Analyze. Same total → same amounts, row stays ticked. Different total → amounts in
  the same ratio, row unticked and marked "⚠ Check split amounts". "Remove Split" forgets it.
* **Short narration** (tick box beside Search). ON: a blue "Party • Mode • Ref" line is shown above the bank's text, and
  Tally gets that line first with the bank's original text on the next line. OFF: only the bank's original text is shown
  and posted. Cash, interest and bank-charge rows always keep the bank's text only. The choice is saved for everyone.
* **Bank date (BRS).** Posted entries get the statement date as their bank date, so they show as reconciled in Tally's
  Bank Reconciliation. Switch it off under **More ▾** if you reconcile by hand.
* **More ▾** holds the tools needed only now and then: 🧩 Teach Columns, Export XML, 📋 Debug report and the bank-date
  switch. 🏦 Bank Details and the backup controls stay where they were.

* **Exact party from Tally.** If a party ledger in Tally has its bank details filled in (account number / IFSC), or the
  party's name appears in the narration, that party is chosen automatically. This is not a guess.
* **"⚠ Check ledger" rows start unticked.** The app is less than 60% sure of these, or they point to Suspense / no
  ledger. Choose the right ledger (type it, pick it from the list, use Bulk Set Ledger, or press Ctrl+D for "same as the
  row above") and the row ticks itself.
* **✂ Split Entry.** Click a bank entry, then ✂ Split Entry, to post one bank amount to several ledgers (e.g. Rent
  ₹10,000 + CGST ₹900 + SGST ₹900). The first line fills itself with whatever is left; Save is enabled only when the
  lines add up exactly. Party lines of a split are posted "On Account".
* **Group similar** (tick box beside Search): rows with the same party, direction AND ledger fold into one line showing
  the count and total. "Set ledger for all" on that line sets every row in it (they tick themselves). If a row does not
  belong, give it its own ledger and it leaves the group by itself, or right-click → "Take out of group" ("Put back into
  its group" undoes it). Groups with a row to check open by themselves. Each row is still posted as its own voucher.
* **Keyboard:** Enter = save the ledger and go to the next row • Ctrl+D = same ledger as the row above • Space = tick /
  untick the highlighted rows • F8 = jump to the next row that needs a ledger check • Ctrl+F = search.
* **Sending a problem statement for a fix:** click More ▾ → 📋 Debug report and answer Yes to "anonymised copy". It saves the debug report
  and a copy of the PDF with every name, narration word and account / reference number replaced (dates, amounts, column
  headings and layout unchanged). Open the copy once to check it, then send both files.
* **Dates Tally cannot accept** (future dates, or before the company's "Books beginning from") are never posted; the
  app lists them and posts the rest.

## When a statement is not read correctly — 🧩 Teach Columns

Every statement must be **proven complete** before it can be posted. Posting is **blocked** (there is no "post anyway")
when any of these fail:
* the running balance does not reconcile (Opening + receipts − payments ≠ Closing)
* the totals printed in the statement (Total Debits / Credits, HDFC Dr/Cr count) differ from what was read
* the "Page x of N" numbers show a missing or repeated page

Analyze also warns when a statement does not continue from the previous statement posted for the same bank ledger
(its opening ≠ the last closing).

When a format is not read correctly, Analyze offers **Teach Columns**. You can also open it from **More ▾ → 🧩 Teach Columns**. In the
Teach Columns window:
1. Go to **any page that shows the transactions**. It does not have to be page 1: cover and summary pages without a
   table are skipped, and headings are optional.
2. Drag the red dividers so each column sits between two of them (click to add a divider, right-click to remove one).
3. Name each column (Date, Description, Debit, Credit, Balance …; "ignore" for the rest).
4. Click **Test**. The layout can be saved only when every row is proven by the running balance.

Saved layouts are stored in the shared database, so every PC uses them. They are applied to all pages, including pages
without headings. A saved layout is only used when its result reconciles; it can never replace a proven automatic read
with an unproven one. Delete a layout from the list in the same window.

## Tests & Audit
- `build_office_exe.bat` runs the full xUnit suite before publishing: the original tests, plus `Tests/AuditRegressionTests.cs` with 29 bank-statement fixtures (CSV / XLSX / HTML-xls / PDF) covering the top Indian banks. Every fixture must parse every debit and credit exactly and reconcile Opening − Dr + Cr = Closing.
- See `AUDIT_REPORT.md` for every bug fixed, how it was verified, and the deployment notes for multi-user offices.

## Updating to a new version (your ML learning is kept)
- All learning, bank details and posting history live in `abse.db` in the data folder: the folder named in `data_path.txt` beside the .exe, or else the `data` folder next to the .exe. The .exe itself holds no data.
- To update: close the app on every PC, copy `abse.db` somewhere safe (just in case), then replace only `AutoBankStatementEntry.exe`. The new version opens the same database. Schema changes only ever add things, so nothing is lost.
- Recommended for offices: put a `data_path.txt` beside the .exe pointing to a shared folder (e.g. `\\SERVER\Share\TallyMLData`), so the data is never inside the program folder.
- `build_office_exe.bat` replaces only the program files in `publish` and never deletes `publish\data`.
