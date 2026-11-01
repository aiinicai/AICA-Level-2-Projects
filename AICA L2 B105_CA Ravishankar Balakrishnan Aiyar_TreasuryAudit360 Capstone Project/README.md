# TreasuryAudit360 – Automated Audit of Bank Treasury (India)

Capstone project by **CA Ravishankar Balakrishnan Aiyar** · Membership No. 040524 · Batch AIL2B105

An end-to-end audit automation for the Treasury department of an Indian bank. It covers **RBI, SEBI, IFSCA (GIFT City) and FEMA**, documented to the **ICAI Standards on Auditing**. Built with **n8n** workflow automation, **Claude** AI and a web front end.

> **Demo data notice:** "Bharat Demo Bank Ltd" and every counterparty, dealer, ISIN and amount are fictitious. Regulatory thresholds are parameters and must be verified against current RBI / SEBI / IFSCA circulars before real use.

## Live links

| What | Link |
|---|---|
| Hosted app (Lovable) | https://treasuryaudit360.lovable.app |
| This repository's app on GitHub Pages | `https://<your-github-username>.github.io/TreasuryAudit360/` (after step 2 below) |
| n8n back end (published webhooks) | `https://nonchallant.app.n8n.cloud/webhook/treasury-audit/...` |

## What is in this repository

| Path | Contents |
|---|---|
| `index.html` | The complete web app: one file, no build step, no dependencies. Dashboard, Run Audit, Audit Report, Findings Register (with management response), Compliance Matrix, Data Explorer, About, Settings |
| `manifest.webmanifest`, `sw.js`, `icons/`, `screenshots/` | Make it an installable Android / desktop app (PWA): app name, theme, adaptive icons, store screenshots, offline app shell |
| `ANDROID.md` | Step-by-step: install on Android from Chrome, build an APK / Play Store AAB with PWABuilder, publish on Google Play |
| `android/TreasuryAudit360.apk` | Signed Android app (native Java WebView app, Android 7.0–16): download and install on a phone |
| `n8n-workflows/0-setup-demo-data.json` | n8n workflow that creates the Google Sheet and fills it with the demo data |
| `n8n-workflows/1-audit-engine.json` | n8n workflow that runs 23 audit tests (JavaScript), has Claude draft the report, saves findings and the SA 230 audit trail, emails the report and returns JSON |
| `n8n-workflows/2-findings-and-data-api.json` | n8n workflow that serves findings and data to the app and records management responses |
| `sample-data/*.csv` | The demo data, one CSV per Google Sheet tab |
| `docs/` | Project guide (PDF/Word), narration script, demo video deck and the capstone presentation (`TreasuryAudit360_Capstone_Presentation.pptx`) |

## 1. Run it immediately (no setup)

Download the repository and **double-click `index.html`**. It opens in your browser and connects to the published n8n back end. Everything works: run an audit, read the report, filter findings, submit management responses.

## 2. Publish on GitHub Pages (free hosting)

1. Create a new **public** repository on GitHub named `TreasuryAudit360`.
2. Click **Add file → Upload files** and drag in **all** files and folders from this folder (`index.html` must be at the top level). Include the hidden `.nojekyll` file: in Windows File Explorer use *View → Show → Hidden items*. Click **Commit changes**.
3. Go to **Settings → Pages**. Under **Build and deployment**, set **Source = Deploy from a branch**, **Branch = main**, **Folder = / (root)**, and click **Save**.
4. Wait 1–2 minutes and refresh. GitHub shows *"Your site is live at https://<username>.github.io/TreasuryAudit360/"*. Open it.

No build or install step is needed. The n8n webhooks allow cross-origin requests, so the GitHub Pages site calls them directly.

> **Building an Android app?** Name the repository **`<username>.github.io`** instead, so the app is served from the domain root. The Android app can then run full-screen without a browser bar. See **[ANDROID.md](ANDROID.md)**.

## Android app

**Ready-made Android app:** download [`android/TreasuryAudit360.apk`](android/TreasuryAudit360.apk) on your phone and tap it to install. Allow "Install unknown apps" when asked. It works on Android 7.0 to Android 16. It is a native Java app with the screens built in, the back button, Print / Save as PDF, and CSV/report downloads to `Downloads/TreasuryAudit360`.

The site is also a Progressive Web App:
- **Install from Chrome on Android:** tap **⬇ Install app** in the menu, or Chrome **⋮ → Install app**.
- **Build an APK / Play Store AAB:** use **PWABuilder** (free, by Microsoft). Full steps are in **[ANDROID.md](ANDROID.md)**.

## 3. Run your own copy of the back end (optional)

1. **n8n:** create an account at n8n.io (Cloud) or self-host with Docker.
2. **Credentials** (n8n → Credentials): Google Sheets OAuth2, Gmail OAuth2, and Anthropic (an API key, or n8n's built-in AI credits).
3. **Import** each file in `n8n-workflows/` (Workflows → ⋯ → *Import from File*). On each Google Sheets, Gmail and Anthropic node, select your credential.
4. Open **0-setup-demo-data** and click **Execute workflow** once. It creates a Google Sheet. Copy that sheet's ID from its URL.
5. In workflows **1** and **2**, replace `YOUR_GOOGLE_SHEET_ID` with your sheet ID: open each Google Sheets node, choose *By ID*, and paste the ID.
6. **Publish** workflows 1 and 2 (toggle at the top right).
7. In the app, open **Settings** and enter your webhook base URL, e.g. `https://<your-instance>.app.n8n.cloud/webhook`. Click **Save & test connection**. You can also change `DEFAULT_N8N_BASE` near the top of the `<script>` in `index.html` and commit.

## Architecture

```
Treasury extracts → Google Sheets (7 tabs + Parameters)
      → n8n Audit Engine (webhook / daily schedule)
          → 23 rule-based tests (JavaScript, 100% population)
          → Claude Sonnet 5.5 drafts the Audit Committee report (SIA 370 / SA 265)
          → Findings register + Audit_Runs trail in Google Sheets (SA 230)
          → HTML report emailed (Gmail) → JSON to the web app
      → Web app: findings → management response → n8n updates the register
```

## API endpoints

| Method | Path (prefix with the base URL) | Purpose |
|---|---|---|
| POST | `/treasury-audit/run` | Run a full audit. Body: `{auditor_name, auditor_email, engagement}`. Takes 60–120 s |
| GET | `/treasury-audit/findings` | Findings for the latest run (`?run_id=` or `?all=true`), plus run history |
| GET | `/treasury-audit/data` | Population tested and parameters |
| POST | `/treasury-audit/response` | Body: `{finding_id, status, management_response, action_owner, target_date}` |

## Audit tests (23)

| Test | Check | Regulator | ICAI SA |
|---|---|---|---|
| TR-01/02 | Unconfirmed / delayed deal confirmations | RBI | SA 505, SA 330 |
| TR-03 | Dealer confirming own deal (segregation of duties) | RBI | SA 315, SA 265, SA 240 |
| TR-04/05 | Off-market rates; after-hours / unrecorded deals | RBI / FEMA | SA 240, SA 520 |
| TR-06/07/08 | Counterparty, dealer and stop-loss limits | RBI | SA 250, SA 315 |
| TR-09/10/16 | NOOP, call money, capital market exposure | RBI / FEMA | SA 250, SA 330 |
| TR-11 | Settlement failure / SGL bounce | RBI | SA 330, SA 505 |
| TR-12–15 | HTM sales, fair-value loss, stale valuation, non-SLR below investment grade | RBI | SA 540, SA 450 |
| TR-17 | Trade in restricted-list (UPSI) scrip | SEBI | SA 250, SA 240 |
| TR-18 | User derivative without suitability / ISDA | RBI | SA 250, SA 315 |
| TR-19/20/21 | IBU in INR, ring-fencing, resident individual | IFSCA / FEMA | SA 250, SA 265 |
| TR-22 | KYC-pending counterparty | RBI | SA 250, SA 240 |
| TR-23 | Holdings vs NSDL / CDSL / SGL | SEBI / RBI | SA 505, SA 500 |

## AI tools and languages

- **Claude Sonnet 5.5** (Anthropic node in n8n): drafts the report at run time, from computed facts only.
- **Claude Opus 5.5** (Claude Code): designed and built the workflows, tests, data, documents and this app.
- **Lovable AI**: generated the hosted React version of the app.
- **Languages:**
  - TypeScript (n8n Workflow SDK)
  - JavaScript (n8n Code nodes and `index.html`)
  - n8n expressions
  - JSON
  - HTML/CSS
  - Python and PowerShell (documents and video)

Every finding is decided by deterministic rules. The AI never decides a finding; it only writes the narrative.

## Security note for production use

The demo webhooks are open (no authentication). For real use:
- Add Header Auth or JWT to the n8n webhooks.
- Restrict allowed origins to your app's domain.
- Self-host n8n in India.
- Never commit credentials. This repository contains none.
