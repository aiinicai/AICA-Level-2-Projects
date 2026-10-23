# Prompts for maintaining the GST Downloader (v2)

Attach the files each prompt names. The ground rules always stay the same: **you type the captcha and OTP, the browser stays visible, and the password is never saved.**

## 1. Something stopped working

> My GST Downloader (Python, Playwright + pandas) fails at: **[paste the activity log lines]**.
> Attached: `portal_config.py`, `portal.py`.
> Open the GST portal in the browser, log in (I will type the captcha), and repeat this step yourself. Check the network calls the portal page makes. Then update ONLY `portal_config.py` (or the one function in `portal.py` that needs to change). Keep the captcha typed by a person.

## 2. Login or captcha changed

> On the GST login page the app no longer shows the captcha (or the login is not detected). Inspect the live login page: the ids of the username, password, captcha image, captcha input and refresh button, and when the captcha appears. Update the `LOGIN` section of `portal_config.py` and `cmd_open_login` / `cmd_login` in `portal.py` if needed.

## 3. Add a new download

> Add **[Electronic Cash Ledger / Credit Ledger / Liability Register]** for the selected FY to my GST Downloader. First find, on the live portal, which JSON call the ledger page makes. Add it to `API` in `portal_config.py`, fetch it in `cmd_run_jobs` the same way GSTR-3B is fetched, turn it into a pandas table in `reports.py`, and add a tick box in `main.py`.

> Add **invoice-level GSTR-1 (B2B, B2CL, CDNR, HSN)** to Excel by reading the extracted GSTR-1 JSON files that the app saves in `<FY>\GSTR1\..._extracted`.

## 4. Better reconciliation

> Extend `reports.reconciliation`:
> * Show 2B vs 3B ITC by head (IGST, CGST, SGST and Cess separately).
> * Add a supplier-wise list of 2B invoices where the supplier filed GSTR-1 after the 3B due date.
> * Add a cumulative ITC difference across the FY.

## 5. Multi-client (later)

> Convert the app to multi-client: a client list (name, GSTIN, username) in SQLite, with passwords stored using Windows Credential Manager (`keyring`). Add a batch run that logs in to each client one by one; I still type each captcha. Add a combined dashboard across clients.

## 6. Make an .exe

> Package my GST Downloader as a Windows app with PyInstaller (`--noconsole --onedir`). Use the installed Chrome or Edge through Playwright `channel="chrome"`/`"msedge"` so no separate browser download is needed. Give me a `build.bat`.
