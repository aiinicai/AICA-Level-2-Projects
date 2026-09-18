# ClientLedger India — User Manual

This is a guide to *using* the app day-to-day. If you're the person building or installing it, see `INSTALLATION-GUIDE.md` (complete beginner walkthrough) or `README-BUILD.md` (technical reference) instead.

---

## 1. First-time setup

The very first time you open ClientLedger India, it will ask you to choose a **data folder** — this is where the app keeps everything: your client list, all downloaded GST returns, and Excel exports. Pick a location you'll remember and back up regularly (a local drive, an external drive, or a synced folder like OneDrive/Google Drive).

You only do this once. The app remembers your choice and won't ask again, even after reinstalling or updating.

**Inside your chosen folder**, the app creates:

| Folder | What's in it |
|---|---|
| `Database\` | Your client list (`clientledger.db`) |
| `GSTR1\`, `GSTR2A\`, `GSTR2B\`, `GSTR3B\`, `TDS_TCS\` | Downloaded returns and Excel exports, organized as `<GSTIN>\<Financial Year>\` |
| `System\logs\` | The activity log — check here first if anything goes wrong |

If you ever need to change the data folder, that's done from **Settings**.

---

## 2. The main window

The sidebar on the left has four sections:

- **Clients** — add and manage your client list
- **GST Compliance** — check filing status, download returns, log in to the GST portal
- **Reports & Data** — Excel exports, bulk import, the GSTIN Supplier Directory
- **Settings & Safety** — backup/restore, app settings

---

## 3. Managing clients

### Add Client
Click **Clients → Add Client**. Required fields: Client Type, Name, Address, State, PIN Code, Date of Birth, Email, Mobile, PAN (Aadhaar is required for individuals). Optional: GSTIN, TAN, Professional Tax number, DIN, and GST portal login (User ID + Password) — filling in the GST credentials here is what lets the app log in to the GST portal on that client's behalf for downloads, without you re-typing credentials every time.

### All Clients
Your full client list, searchable by name, email, PAN, GSTIN, or mobile number. Click any row to view or edit that client's details.

### Bulk Import
For adding many clients at once from a spreadsheet. The columns marked with `*` (Client Type, Name, Address, State, PIN Code, Date of Birth, Email, Mobile, PAN, and Aadhaar for individuals) are required; GSTIN, TAN, PT Number, DIN, and GST login are optional. The screen shows the exact column layout expected before you upload.

---

## 4. GST Compliance

This is where you check filing status and download returns. Every download flow follows the same basic pattern:

1. Pick the client (GSTIN) and Financial Year.
2. Enter the GST portal username and password (or they're pre-filled if saved on the client record).
3. Click **Start**. A browser window opens and logs in to the GST portal automatically.
4. **If a CAPTCHA appears**, type what you see into the box in the app and submit — the app can't solve CAPTCHAs itself, this is the one manual step in the whole process.
5. **If an OTP is requested**, enter it the same way when it arrives on the registered mobile/email.
6. After that, the download runs on its own — no further captchas or logins needed for that session.

### Filing Status
A quick check across your clients showing which returns are filed vs. pending, without downloading the full data.

### GSTR-1 / GSTR-2A / GSTR-2B / GSTR-3B / TDS-TCS Download
Each has its own tab under GST Compliance, letting you download that specific return type for one client and financial year (or a specific month). Files land in the matching folder (`GSTR1\`, `GSTR2A\`, etc.) automatically.

### Download All
Runs GSTR-1, 2A, 2B, 3B, and TDS/TCS for one client in a single browser session — you log in and solve the CAPTCHA **once**, and all five download in sequence instead of five separate logins. This is the fastest way to pull a complete picture for one client.

**If Download All (or any individual download) seems stuck:** check `System\logs\gst_rpa_activity.log` in your data folder. Any real failure — a bad password, a portal error, a browser problem — will show up there with a clear message. If nothing new is appearing in the log at all and no browser window ever opened, that's worth reporting.

**"Already running — reset first"**: this means a previous session for that same feature didn't fully finish. Look for a **Reset** button on that screen, or check the activity log for what happened to the last run.

---

## 5. Reports & Data

### Export to Excel / Filtered Export
Exports your client list to an Excel file — "Filtered Export" respects whatever search/filter is currently applied on the All Clients screen.

### GSTR-1/2A/2B/3B/TDS-TCS → Excel
Converts the raw downloaded data for a client + financial year into a formatted Excel workbook. **This requires that you've already downloaded that return type for that client/period** — if you see "No JSON files found," run the download first.

Every export saves a copy on disk automatically, in the matching `GSTR*\<GSTIN>\<FY>\` folder — check that module's activity log for the exact saved path if you can't find it in your browser's Downloads folder.

### GSTIN Supplier Directory
A repository of trade names and legal names for every supplier/buyer GSTIN found across your downloaded GSTR-2A, GSTR-2B, and GSTR-1 data.

- **Scan Files** — builds/refreshes the directory from whatever you've already downloaded.
- **Portal Enrichment** — logs in to the GST portal once, then looks up the legal name for every GSTIN missing one, without any further captchas. Choose the scope (only unnamed GSTINs, only those missing a legal name, or re-enrich everything) before starting.
- **Backup / Restore** — save or reload the whole directory as a JSON file.
- **Export CSV** — for use outside the app.

---

## 6. Settings & Safety

### Backup & Restore
Backs up your entire client list to a file, or restores from a previous backup. Two restore modes:
- **Merge** — adds backup records that don't already exist (matched by PAN/Aadhaar/email), leaves your current data alone otherwise.
- **Replace All** — wipes your current client list and replaces it entirely with the backup. If some records fail during Replace All (usually because two clients in the backup share the same PAN/Aadhaar/email), you'll get a clear warning listing which records and why — check the browser console (F12) for full detail if needed.

**Back up regularly.** This is the only copy of your client list outside of the `Database\clientledger.db` file itself.

### Settings
Change the data folder location, adjust app preferences.

---

## 7. Common issues

**A CAPTCHA image doesn't load, or nothing happens after entering it.** Try again — the GST portal's own CAPTCHA service is sometimes slow or briefly unavailable. This isn't something the app controls.

**The GST portal itself won't load at all ("requested URL was rejected").** This is usually a network-level block (VPN, institutional firewall, or the portal itself under load), not an app problem. Try a different network (e.g. a mobile hotspot) to confirm.

**Windows blocked the app from opening at all ("Smart App Control").** This is a Windows 11 security feature that blocks unsigned apps outright, with no override button. Ask whoever installed the app about disabling Smart App Control (Windows Security → App & browser control) — this is a one-time Windows setting, not something wrong with the app.

**Where do I find error details if something fails?** `<your data folder>\System\logs\gst_rpa_activity.log`. Every feature logs there, and any real crash shows up as a clear error message rather than the app just doing nothing.

**A save/action fails with a vague message like "Failed to fetch."** This means the app's request never reached its own local server at all — the activity log won't have anything useful for this specific case since the request never got that far. This requires the app's built-in DevTools diagnostics, which are off by default to keep normal use clean — ask whoever supports the app to close it, set the `CLIENTLEDGER_DEBUG` environment variable to `1`, and relaunch; right-click anywhere in the app window and choose **Inspect** to open the diagnostics panel, click the **Console** and **Network** tabs, and try the action again — details will appear there that the app's own error popup doesn't show. If you're reporting this kind of issue, a screenshot of that output is the most useful thing you can send.

**Can I run this on more than one computer?** Yes — the data folder can be a synced folder (OneDrive, Google Drive, a shared network drive) if everyone points the app at the same location. There's no built-in multi-user locking, though, so avoid two people running downloads for the same client at the exact same time.
