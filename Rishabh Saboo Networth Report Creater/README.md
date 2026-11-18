# Net Worth Office

Net Worth Office is a Python web app. Install it on one computer or cloud server. The report editor opens directly in the browser.

## Run locally on Windows

If you already installed the libraries, double-click **Start Net Worth Office.vbs**. It starts Python in the background and opens your default browser. Double-click it again to reopen the app. **Start Net Worth Office.cmd** remains available for troubleshooting startup.

For a new installation, install Python 3.11 or newer. Open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Double-click the launcher, or run `.\.venv\Scripts\python.exe networth.py local` from PowerShell. If your browser stays closed, open [Net Worth Office](http://127.0.0.1:8080) manually. Fill in **Firm master** before saving your first report.

## Create and resume reports

In **Settings → Firm masters**, select **Add a new firm** for each profile. In **Report details**, select the firm for that certificate and choose a manual or automatic reference. **Save draft** keeps partially entered details. Use **New report** to start another, and **Report library** to find drafts and completed reports by reference, firm, applicant, or status. Generating Word or PDF validates and completes the draft.

## Fill the ICAI UDIN form

On the Windows computer running Net Worth Office, select **Prepare UDIN → Open ICAI and generate UDIN**. The app opens a separate Edge or Chrome window and fills the firm’s saved credentials. Enter CAPTCHA and sign in there, then enter the OTP in the ICAI window. Follow any manual steps displayed in **Prepare UDIN** if ICAI presents a different form. The app watches for the issued number and saves it against the report revision used to generate it.

Install the updated `requirements.txt` if automatic UDIN reports that Playwright is missing. The browser window runs on the computer hosting the app.

### Manual fallback

From a completed certificate with a foreign currency, choose **Prepare UDIN**. Download the bookmark file and import it in Edge or Chrome using **Import bookmarks from HTML**. This is a one-time setup.

Choose **Copy autofill data**, open the official ICAI portal, and sign in to **Generate UDIN**. Click the **Fill ICAI UDIN** bookmark and paste the copied data when prompted. Check the fields listed by the helper and review the two amounts. Complete the portal's verification and submission, then return to Net Worth Office and use **Save issued UDIN**.

The bookmark runs on the official Generate UDIN page. Browser scripts cannot access that page directly from the Net Worth Office tab.

## Enable Google Gemini valuation extraction

Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey). Set `GEMINI_API_KEY` in the server process environment and restart the app. For a local PowerShell session, enter the key at a masked prompt before starting the app:

```powershell
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Gemini API key' -AsSecureString)).Password
.\.venv\Scripts\python.exe networth.py local
```

The default model is `gemini-3.5-flash-lite`. Set `GEMINI_MODEL` in the same environment if your project uses a different Gemini model with image input and structured output. Use **Settings → Google Gemini → Test connection** to check the key and model. Settings changes apply for the current server session. The app can also load a Windows-protected `gemini-key.windows` file for the Windows account that encrypted it. For cloud deployment, configure the key through the server environment.

In **Properties** or **Investments**, choose **Import valuation**, select a PDF, PNG, or JPEG, and click **Extract with AI**. That action sends the valuation pages to Google Gemini. Check the proposed figures and particulars against the source before applying them.

## Deploy on a cloud server

1. Install the dependencies from `requirements.txt` in a virtual environment.
2. Set `NW_DB` to an absolute SQLite path in a private directory on persistent local storage. Use the same setting for the server and account commands. Restrict access to the directory and use encrypted storage for client data.
3. Set `NW_SECURE=1`. Run `python networth.py` as a service behind an HTTPS reverse proxy. The app defaults to `127.0.0.1:8080`. Set `NW_PORT` if the proxy uses a different upstream port.
4. Restrict the HTTPS address to your office VPN, private network, or access-controlled reverse proxy. Anyone who can reach the app can view and edit reports.

Create a consistent database backup with `python networth.py backup /path/to/new-backup.sqlite3`. Store backups privately and use a new destination filename for each backup.
