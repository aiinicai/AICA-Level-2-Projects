# How to use Reco-Do

Reco-Do compares two sets of records, matches what agrees, and shows you only what needs a decision. Everything runs on your computer. Nothing is uploaded unless you choose to use Smart Recon.

## Install and open

`RecoDo-Setup.exe` installs Reco-Do (once, or to update). `RecoDo.exe` is the app itself and runs without installing. After installing, open Reco-Do from the Desktop/Start menu shortcut.

- The version is shown at the bottom of the sidebar and in **Settings → About**, which also shows the build date and the folder where your data is kept (**Open data folder**). Older builds are kept in `release/previous-versions` with their version in the name.
- You do not need `RecoDo-Setup.exe` again after installing. If you run it again anyway, it tells you Reco-Do is already installed: click **No** to open Reco-Do, or **Yes** to reinstall/repair it. Your reconciliations and settings are kept either way.
- The first time, Windows SmartScreen may say "Windows protected your PC" because the file is not code-signed. Click **More info → Run anyway**.
- Reco-Do fits screens from 1024 × 640 up and remembers the window size and position you leave it at.

## Before you start

1. Open **Settings & API Key**. Enter your name (it goes on sign-off and in the audit trail), your department and your default currency.
2. Optional: to use Smart Recon's AI step, pick your choice of AI provider (Claude, ChatGPT, Gemini, DeepSeek, or any OpenAI-compatible service, including local models) under **AI provider (Smart Recon)**, paste that provider's API key and click **Test connection**. For Gemini, use a Gemini API key from Google AI Studio (Google Antigravity is Google's coding tool, not an API key). For a local server such as LM Studio or Ollama, choose **Other (OpenAI-compatible)**, enter its base URL (for example http://localhost:1234/v1) and the model name; no key is needed. Every other feature works without any of this.
3. Want to practise first? Every module and tool has a **Try with sample files** button.

## A reconciliation in five steps

Every module uses the same wizard.

1. **Upload.** Choose or drop the two files (Excel or CSV). Reco-Do finds the header row, skips titles, blank rows, totals and repeated headers, and picks up opening and closing balances. Check the preview; if the header row is wrong, click **Change** and type the row number (0, or **No header row**, for a file without one: its columns are then named Column 1, Column 2, …). If Reco-Do had to repair something while reading a CSV (for example a quote that is never closed), it says so under the file. A PDF statement? Convert it first with **PDF → Excel**.
2. **Map & rules.** Reco-Do suggests which columns to match (for example Reference, Date and Amount) and how each file shows money (one signed column, Debit and Credit columns, or an amount with Dr/Cr). Adjust the keys, the date tolerance (± days), the amount tolerance and the sign setting. When the dates in a file could be read either way (every day is 12 or less) or the two files write dates differently, a **Date format** box shows how each file is read (DD/MM/YYYY or MM/DD/YYYY); change it if it is wrong. If a Credit column holds negative numbers, a note confirms they are still treated as credits. **Save mapping** so the same files map themselves next time.
3. **Reconcile.** Click **Run reconciliation**. Every line lands in one tier, with a plain-English reason:
   - **Matched:** all keys agree.
   - **Doubtful:** all keys but one agree. Check and accept or reject.
   - **Likely:** only one identifying key agrees. Check carefully.
   - **Unmatched:** nothing on the other side agrees.
4. **Smart Recon (optional).** Code looks for one-to-many and many-to-one combinations (for example one receipt paying three invoices). With an AI provider set up, the AI can also suggest fuzzy matches. The panel shows where rows will go (for example "Sends to: OpenAI · gpt-6.1-sol"), and the preview names the exact destination. You see exactly which rows and columns would be sent before anything leaves the computer, and party names can be masked: the party column and name columns such as Name or Employee are replaced by tokens (PARTY_01 …), and those names are also hidden wherever they appear in other text. If no party or name column is mapped, the option is greyed out because there is nothing to mask. **Cancel** stops the request that is in progress. Nothing is matched until you approve it.
5. **Review & export.** Accept, reject, unmatch or add notes, or tick lines on both Unmatched tabs and click **Match selected**. Every action is recorded in the **Audit trail**. When Doubtful and AI suggestions are cleared, **Finalise & sign off** locks the reconciliation. **Export Excel** gives a formatted workbook (summary, reconciliation statement, matched items, open items per side with ageing, review items, AI-assisted matches and the audit log). **Export PDF** gives a print-ready summary for sign-off.

Your reconciliations are saved automatically: as a draft from the moment both files are read, and after every decision once it has run. If you close the window while something is still being saved, Reco-Do finishes saving first. Open them again from **Recon History**.

## Working on several reconciliations

You can keep several reconciliations going at once, in every module, and come back to each one later. Finalising is never required.

- **New reconciliation** (next to the title of every step) starts a fresh one for the module. The one on screen is kept: if it has not been run yet it is saved as a draft ("Saved as draft — find it under In progress").
- **In progress** (next to it) lists the module's unfinished reconciliations: drafts that have not been run yet and results that are not finalised. Each one shows the account, period, where it stands (for example "Map & rules" or "Review: 16 doubtful open") and when it was last updated. Click **Open** to switch; everything on the screen you leave stays as it was. The bin icon deletes one (you are asked first).
- Drafts keep their files, sheet and header-row choices, account, period and Map & rules settings, so after closing the app a draft opens again at the step you left, files included.
- Results that are not finalised keep their files too, so you can go back to **Map & rules**, change a setting and run again. Finalised reconciliations stay locked. Reconciliations saved by an earlier version of Reco-Do did not keep their files, so for those only the results can be opened.
- The **Dashboard** shows "N in progress" on each module card (click it to open the list) and your five most recent unfinished reconciliations. **Recon History** lists everything with a status (**Draft**, **In review** or **Finalised**) and can show just one status.
- The files are stored on this computer with the reconciliation. If the disk is full, Reco-Do says so and keeps your work on screen; free up some space and carry on.

## The modules

- **Bank Reconciliation:** bank statement against the GL cash account. Bank debits normally match GL credits, so the sign is inverse by default. Bank charges and interest in the statement are labelled so you can post the journal.
- **AR Reconciliation:** your customer ledger against the customer's statement. Matches on invoice number, date and amount; the statement shows the balance difference and what explains it.
- **AP Reconciliation:** your supplier ledger against the supplier's statement. Supplier invoices missing from your books are flagged as possible unrecorded liabilities.
- **General Reconciliation:** any two files, any columns. Name the two sides, pick the column pairs to match, and leave the amount out if there is none (for example employee lists). Save the setup as a **template** to reuse it.
- **GL Reconciliation** and **Credit Card Recon** are coming in the next phase.

## The tools

All tools work on any file, run on your computer and can save their settings as a **recipe** for repeat jobs.

- **PDF → Excel:** turns digital or scanned PDFs into Excel. Choose **Raw tables** or **Bank statement** layout. Scanned pages are read with on-device OCR; cells it is unsure about are shaded amber for you to check.
- **Excel → PDF:** prints a sheet to a tidy PDF with repeated headers, page numbers and fit-to-width.
- **Merge PDFs:** combines PDFs. Reorder files and pages by dragging or with the arrow buttons; rotate or remove pages.
- **Split PDF:** splits by page ranges, every N pages, or extracts chosen pages.
- **Merge Files:** stacks several Excel, CSV or PDF statements into one sheet, lines up columns with different names, and adds a "Source file" column.
- **Data Cleaner:** removes junk and total rows, fills merged cells down, converts text numbers and dates, splits Debit/Credit, trims spaces and removes duplicates. It shows what changed before you save.

## Good to know

- The app never changes your original files; exports are always new files.
- Password-protected PDFs must be unlocked first.
- Very large reconciliations (tens of thousands of lines a side) work, but each review decision takes a moment to save.
