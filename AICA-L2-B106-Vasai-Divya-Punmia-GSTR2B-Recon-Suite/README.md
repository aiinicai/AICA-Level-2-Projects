# GSTR-2B Recon Suite

Reconciles the GSTR-2B with the purchase register, then helps with what follows: smart matching, Section 17(5) blocked credits, reverse charge, credit/debit notes, supplier follow-ups, filing reports, ITC health checks and the GSTR-3B Table 4 figures.

Everything is stored in a local SQLite database on the computer that runs the app. Nothing is sent to any outside service.

**Demo video:** [watch on Google Drive](https://drive.google.com/file/d/1d8IxJQBbDuPHpjrLnTBFqjT-qhAmWred/view?usp=drive_link) (also in `docs/demo.mp4`)

## Starting the app (Windows)

| File | Use it when |
|---|---|
| `1-Start-Localhost.bat` | Only this computer will use the app. Opens http://localhost:3100 |
| `2-Start-Server-Host.bat` | Other computers / phones / tablets on the same Wi-Fi or LAN will use it. Prints the links to share (http on port 3100, https on port 3443) and adds firewall rules (Administrator needed once). |

Double-click the file and keep the black window open while using the app. Close the window (or press Ctrl+C) to stop it.

**First run:** if Node.js with npm is not installed, a private copy (about 30 MB) is downloaded into `runtime\node`. Packages are then installed into `node_modules`. npm's download cache goes to `runtime\npm-cache` in this folder, not drive C:. Later starts are quick.

The app uses **port 3100**, so it can run alongside Audit Working Paper Pro (port 3000). To change it, copy `.env.example` to `.env` and set `PORT`.

## Using it

1. **Import & Settings**: create the client and period (top bar **+**), then load the **GSTR-2B** file and the **purchase register**. Each file opens a column-matching window. Check the detected columns and the preview, then click **Import**. GSTR-2B Excel files from the portal are read sheet by sheet (B2B, B2BA, CDNR). Sample files can be downloaded from each box.
2. Reconciliation runs automatically. The **Tolerance ₹** box (top bar) sets the difference that still counts as matched.
3. Work through the tabs:

| Tab | What it shows |
|---|---|
| GSTR-2B Invoices | Both registers as read (split lines added up, amendments applied) |
| Compliance Dashboard | Final status counts, ITC position, and suggested **GSTR-3B Table 4** figures |
| Reconciliation Ledger | Every invoice once, with filters. **Block** (Section 17(5)) and **Note** on each row. Excluded rows are listed too |
| Smart Match Runs | Pass 1 invoice core, Pass 2 amount + date, Pass 3 tax values, and the unresolved list |
| CDN Registry | Credit / debit notes reconciled separately |
| RCM Purchase Bills | Reverse-charge bills (separate file plus rows marked or detected as RCM) |
| Blocked Credits 17(5) | Blocked invoices. **Release** or **Block again** |
| Supplier Follow-ups | Suppliers whose invoices are missing from GSTR-2B: **PDF notice**, **Copy e-mail**, **Open in mail app** |
| Filing Reports | By GSTIN, by month, and non-filer risk |
| ITC Health Check | GSTIN check digit, MSME status, duplicate invoice nos., Section 16(4) time limit, non-filers |
| Audit Logs | Every import, block, note, supplier change and download |

Every tab has an **Excel** button for what it shows. **Full export** (top bar) downloads one workbook with all views.

## What changed from the AI Studio version

- **Each invoice is counted once.** An invoice found by a smart pass used to be counted as matched and also as missing. Now every invoice has one final status, and the dashboard, Table 4, reports and follow-ups all use it.
- **Dates are always read as dd/mm/yyyy.** Excel cells with the default short-date format came in as US-style text (4 October 2026 became "10/4/26", and was grouped under April). CSV dates are now read as text and always day-first, and Excel date cells are converted exactly.
- **Block tags the right invoice.** In AI Studio, blocking a row while the ledger was filtered could block a different invoice.
- **Smart Pass 1 works as described.** `TAX-2024-25/0091` now really matches `INV/91`.
- **Tally exports map correctly.** "Supplier Invoice No." is chosen over "Voucher No.".
- **Report exports** export the report shown. In AI Studio they exported the smart-match list.
- **Table 4** keeps reverse-charge ITC in 4(A)(3) instead of 4(A)(5), and reverses only blocked credit that was included in 4(A)(5).
- **MSME status is recorded by you.** AI Studio's "Verify MSME" made up a random answer, and there is no public registry service to connect to. Record each supplier's classification and Udyam number from their Udyam certificate (Health Check → MSME, or **E-mail & MSME** in Follow-ups).
- **Keyword detection is narrower.** Supplier-name detection for RCM and 17(5) no longer flags words like "car", "steel", "trust" or "hotel" on their own. Auto-blocked invoices are marked "Name keywords" so they can be checked.

## Data and backups

- Database: `data\gstr2b_recon.db` (a standard SQLite file). Set `GSR_DB_PATH` in `.env` to keep it elsewhere.
- **Import & Settings → Download database backup** saves a copy at any time.
- To move to another computer, copy this whole folder. `node_modules` and `runtime` can be left out; they are set up again on first start.

## Phones, tablets and computers

The app detects the device it is opened on and adjusts the layout, and it adjusts again when a tablet is rotated or a window is resized:

| Device | Layout |
|---|---|
| Computer / laptop (1024 px and wider, mouse) | Full sidebar, wide tables |
| iPad / tablet held sideways | Full sidebar, larger touch targets |
| iPad / tablet held upright, or a narrow window | Slim icon rail (tap ☰ for the full menu) |
| Phone | Menu button and bottom tab bar. Tables turn into cards, charts are stacked, dialogs slide up from the bottom |

On touch screens, buttons are at least 40 px tall and form fields use 16 px text, so iPhone and iPad do not zoom in. The installed app keeps clear of the notch and the home bar.

## Install as an app (PWA)

| Where | How |
|---|---|
| **This computer** (Chrome / Edge) | Open http://localhost:3100. Click **Install app** in the app's top bar, the install icon in the address bar, or menu → *Install GSTR-2B Recon Suite*. |
| **Phones, tablets, other PCs** | Start with **2-Start-Server-Host.bat**. It switches on **https** (port 3443), because browsers only install apps from secure addresses. On each device, once: open `http://<server-ip>:3100/install`, download the certificate and trust it (the page shows the steps for Android, iPhone / iPad and Windows). Then open `https://<server-ip>:3443` and choose **Install app** (Android Chrome) or **Share → Add to Home Screen** (iPhone / iPad Safari). |

The installed app has its own window and icon, opens straight to the app, and offers shortcuts from its icon (Dashboard, Ledger, Follow-ups, Import). It shows a **Reload** banner when a new version is available. Data always comes live from the server's database; nothing is stored on the phone.

The https certificate is created on the server computer by the app itself (in `certs\`; the private keys never leave that folder and are not shared). It is renewed automatically if the computer's network address changes. Delete the `certs` folder to start over; devices then need to trust the new certificate again.

## For developers

```
npm install
npm run dev      # hot reload on http://localhost:3100
npm test         # engine, importer and date tests
npm run build && npm start
```

- `server.mjs` serves the API (`/api/*`) and the built app.
- `shared/db.mjs` is the SQLite layer. It uses `node:sqlite` on Node 22.13+, otherwise `sql.js`.
- `src/lib/engine.ts` holds the matching, Table 4, reports and health checks.
- `src/lib/importer.ts` handles header detection, column mapping and row building.
- `src/lib/dates.ts` handles day-first date parsing.
