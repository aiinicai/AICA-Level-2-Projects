# Setup guide (everything free)

This guide has five parts. Do them in order; parts 1 and 2 are enough for a demo on your own laptop.

1. Run it on your laptop
2. Put the code on GitHub
3. Create the free cloud database (Supabase)
4. Put the app online for your team (Streamlit Community Cloud)
5. Get the Windows desktop app and installer

Then: switching on the AI Assistant, how to give the app your data, how to keep due dates updated, and fixes for common problems.

---

## 1. Run it on your laptop (5 minutes)

1. Install **Python 3.12** from python.org. On the first installer screen, tick **"Add python.exe to PATH"**.
2. Unzip the project folder.
3. Double-click **`Start_App.bat`**. The first run installs packages, which takes a few minutes. Your browser then opens the app.
4. Sign in with **admin / admin@123** and set your own password.
5. For a demo, go to **Settings → Data & connection → Load demo data**.

This uses a local database file (`practice.db`) on your laptop only. Parts 3–4 make it shared and live for the whole team.

## 2. Put the code on GitHub

1. Create a free account at github.com.
2. Install **GitHub Desktop** (desktop.github.com) and sign in.
3. In GitHub Desktop, choose **File → Add local repository** and pick the project folder. When it says the folder isn't a repository, click **create a repository** and keep the default settings.
4. Click **Publish repository**. Untick "Keep this code private" if your evaluators need to see it.

`.gitignore` already keeps your database, passwords and build files out of GitHub.

## 3. Create the free cloud database (Supabase)

1. Sign up at **supabase.com** with GitHub.
2. Click **New project**. Choose a name, a strong **database password** (save it), and the **Mumbai (ap-south-1)** region.
3. When the project is ready, click **Connect** at the top, then choose **Session pooler**. Copy the URI. It looks like:
   `postgresql://postgres.abcdxyz:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`
4. Replace `[YOUR-PASSWORD]` with your database password.

Use the **Session pooler** string, not "Direct connection". The direct one only works on IPv6 networks, which Streamlit Cloud and many home connections don't support.

You don't need to create tables; the app creates them the first time it connects.

**Free-tier notes:** 500 MB of database space per project, and the project **pauses after 7 days without use**. If it pauses, open supabase.com and click **Restore**. Opening the app at least once a week avoids this.

## 4. Put the app online for your team (Streamlit Community Cloud)

1. Go to **share.streamlit.io** and sign in with GitHub.
2. Click **Create app → Deploy a public app from GitHub**. Choose your repository, branch `main`, and main file `app.py`.
3. Open **Advanced settings**:
   * **Python version: 3.12.** Don't leave the default, because some packages don't support the newest Python yet.
   * **Secrets:** paste the line below with your Session pooler string:
     ```toml
     DATABASE_URL = "postgresql://postgres.abcdxyz:YOUR-PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
     ```
4. Click **Deploy**. After a few minutes you get a link like `https://your-app.streamlit.app`.
5. Sign in as **admin / admin@123**, set your password, then add your team under **Settings → Team & logins**. Each person gets a temporary password and sets their own on first sign-in.

Share the link with your staff. Everyone works on the same live data, and screens refresh every 30 seconds.

**Free-tier note:** if nobody opens the app for 12 hours it goes to sleep. The next visitor clicks "Yes, get this app back up" and waits about a minute.

## 5. Get the Windows desktop app (installer to share with colleagues)

The desktop app opens in **its own window** (like any Windows program, no browser tab and no black console window), has a Start-menu and desktop shortcut, and appears in *Settings → Apps* so it can be uninstalled normally. It installs without administrator rights.

**Option A: GitHub builds it for you (recommended, nothing to install on your PC)**
1. On github.com, open your repository → **Actions** tab. If asked, enable workflows.
2. Click **Build Windows app → Run workflow**. It takes about 10–15 minutes.
3. Open the finished run. Under **Artifacts**, download:
   * **CAPracticeManager-Setup**: unzip it to get **`CAPracticeManager-Setup.exe`**. This is the one file to share with colleagues.
   * *CAPracticeManager-portable* (optional): a zip that runs without installing.
4. For a permanent download link, push a tag (GitHub Desktop → Repository → Create tag, e.g. `v2.0.0`, then Push). The workflow attaches both files to a **Release**.

**Option B: build it on your PC.** Double-click **`build_exe.bat`**. To also get the Setup.exe, first install the free **Inno Setup 6** (jrsoftware.org). Results go in the `dist` folder.

### Installing on each computer
1. Double-click `CAPracticeManager-Setup.exe` → Next → Install. Windows SmartScreen may say "Windows protected your PC" because the app isn't code-signed (a signing certificate costs money). Click **More info → Run anyway**.
2. On first launch the app asks how to connect:
   * **Join my firm**: paste the connection details (below). Everyone then shares the same live data.
   * **Use on this computer only**: separate data on that PC, for trying it out or working alone.
3. Each person signs in with the username and password the partner created in **Settings → Team & logins**.

### Giving colleagues the connection details
A Partner opens **Settings → Data & connection → Share with colleagues** and copies the text shown. Send it privately, for example on WhatsApp to the person directly. It contains the database password, so if someone leaves the firm, change the database password in Supabase (Project settings → Database) and share the new details.

### Good to know
* The app keeps its settings, its local database (in "this computer only" mode) and a log file in `%LOCALAPPDATA%\CAPracticeManager`. Type that into the File Explorer address bar to open it. If something goes wrong, send `app.log` from there.
* The app window uses Microsoft Edge WebView2, which is built into Windows 10 and 11. If it's missing, the app opens in the normal web browser instead and shows a small "CA Practice Manager is running" window. Close that window to stop the app.
* Installing a newer Setup.exe over the old one keeps your settings.

---

## Switching on the AI Assistant (free, 5 minutes)

1. Go to **aistudio.google.com** and sign in with any Google account.
2. Click **Get API key → Create API key**. Copy the key. No payment details are needed for the free tier.
3. In the app: **Settings → AI assistant**, paste the key, click **Save**, then **Test the AI connection**. It should say "Working".
4. Everyone in the firm can now use **AI Assistant** in the sidebar. The key is shared; only Partners can see or change it.

Privacy: on Google's free tier, what is sent may be used to improve Google's products and may be read by reviewers. The app masks client names, staff names, PAN, GSTIN, Aadhaar, phone numbers, e-mails and address lines before every request, and shows you exactly what was sent. For a notice, review the masked text and remove anything else confidential before ticking the consent box. If the free model stops working (Google renames models from time to time), pick another model in the same Settings tab.

---

## How you give the app your data

| What | Where in the app |
|---|---|
| Your firm's name, GSTIN, PAN, state and bank details (printed on invoices) | **Settings → Firm profile** |
| Team members and logins | **Settings → Team & logins** |
| **Existing client list** | **Clients → Excel template**: fill one client per row (drop-downs included), then **Import from Excel**. The app checks PAN/GSTIN formats and duplicates and shows a preview before importing. |
| One new client | **Clients → Add client** |
| Statutory tasks | Created automatically from the services ticked for each client |
| Other work (notices, assessments, certificates) | **Task Board → New task** |
| Work status | Staff move cards with ▶ or open ⋯ for notes. Partners and managers mark reviewed work **Done**. |
| Invoices | **Billing → New invoice**, or **Raise [month] retainer invoices** for all clients at once |
| Documents | **Documents → Upload** (up to 10 MB per file) |
| Backup | **Settings → Data & connection → Prepare Excel export** |

## Keeping due dates updated

There's no official government feed of due dates, so the firm keeps its own master list. Two ways to record a change:

**A. In the app (fastest for one extension):** **Compliance Calendar → Extend a due date**. Pick the return, the period(s) and the new date, and add the notification reference. Every pending task for that return moves; completed work is untouched.

**B. From GitHub (updates every copy, including every .exe):**
1. One time only: **Compliance Calendar → Updates from GitHub**, paste the link to `due_dates.json` in your repository (for example `https://github.com/<you>/<repo>/blob/main/due_dates.json`), and click **Save link**.
2. When CBIC/CBDT change a date, open `due_dates.json` on github.com and click ✏️ **Edit**. Add an entry under `"overrides"`, for example:
   ```json
   "overrides": [
     {"code": "GSTR3B_M", "period": "Oct-2026", "due_date": "2026-11-25", "note": "Extended vide Notification xx/2026-CT"}
   ]
   ```
   Then change `"version"` to today's date, e.g. `"2026.11.20"`, and click **Commit changes**.
3. The app checks automatically every 6 hours when a partner or manager signs in. You can also click **Check for updates**.

Period names follow the task cards: monthly returns use `Oct-2026`; quarterly and annual ones use `Q2 FY 2026-27`, `ITR FY 2026-27`, and so on. **Compliance Calendar → Download current due_dates.json** gives you a correctly formatted file to start from.

## Common problems

| Problem | Fix |
|---|---|
| `requirements.txt` not found | Open the terminal **inside** the project folder, or just double-click `Start_App.bat`. |
| "Can't reach the database" | Check your internet connection. Check that the Supabase project isn't paused (supabase.com → Restore). Check that you used the **Session pooler** string with the right password. |
| Streamlit Cloud app stuck "in the oven" | App settings → set Python to **3.12** → Reboot. |
| Forgot the admin password | Another Partner can reset it in **Settings → Team & logins**. On a local copy, delete `practice.db` to start fresh. |
| A browser refresh signed me out | That's expected: sessions are kept in memory. Sign in again. |
