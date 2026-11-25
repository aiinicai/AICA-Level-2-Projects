# Multi-Country Workforce Analytics – CFO Dashboard
**ICAI AICA Level 2 Capstone Project** · *[Your name] · [Batch number] · [Membership number]*

**Live dashboard:** `https://<your-github-username>.github.io/<repo-name>/` *(add your link after step 2 below)*
**Demo video:** *[YouTube / Google Drive link]*

---

## 1. Business problem
A group with operations in **India, UK, US, France and China** collects workforce data every month from five country SPOCs by email. FP&A then spends days merging the spreadsheets by hand, converting currencies, building the headcount walk and explaining variances to the CFO. The result is slow and error-prone, and the cost-per-head trend is hard to see.

## 2. Solution
An automated pipeline from inbox to CFO dashboard:

```
Country SPOCs ──email──▶ Gmail ──▶ n8n workflow ──▶ Google Drive (WF_Inbox)
                                     │ every hour on the 25th: checks subject / country / month / attachment
                                     │ logs every submission, replies to the SPOC
                                     │ 25th of the month, 6 PM: status email to FP&A (received / pending)
                                                          │
                                                          ▼
                                     consolidate.py (Python)
                                     │ 12 content checks per file (duplicates, roll-forward, grades …)
                                     │ workforce walk, cost in INR, grade / location / function mix
                                     │ budget variance split into volume and rate / mix effects
                                                          ▼
                     Consolidated_Workforce_<month>.xlsx  +  dashboard_data.json
                                                          ▼
                     CFO Dashboard (web app, installable on phone and desktop, works offline)
```

| Layer | Tool | Folder |
|---|---|---|
| Data intake and control | n8n (Gmail, Google Drive, Data Table) | `n8n/` |
| Consolidation and variance engine | Python (pandas, openpyxl) | `consolidation/` |
| CFO dashboard | HTML, JavaScript and D3, as a Progressive Web App (PWA) | `docs/` |
| Sample data | 5 country files, budget, FX, control totals | `sample_data/`, `consolidation/` |

## 3. What the CFO sees (sample data, Jul–Nov 2026; November shown)
| Metric | Actual | Budget | Variance |
|---|---|---|---|
| Headcount (internal + external) | 2,773 | 2,667 | +106 (+4.0%) |
| Monthly workforce cost | ₹178.9 Cr | ₹179.8 Cr | −₹0.8 Cr (−0.5%) |
| Cost per head per month | ₹6.45 L | ₹6.74 L | −4.3% |

**Insight:** headcount is 4% over budget, yet cost is under budget. The extra heads add **₹7.4 Cr** (volume effect), but a lower cost per head saves **₹8.2 Cr** (rate / mix effect), driven by junior and project hiring. If cost per head returns to budget, the same headcount would cost ₹7.4 Cr a month over budget, which is the key risk for the forecast.

Five months of sample data (Jul–Nov 2026) are included. **Group / country buttons** (Group, India, UK, US, France, China) and **year**, **month** and walk-population filters apply to every section: choosing a country shows only that country's figures, charts, table and commentary. A separate **Projects** page (tab at the top) shows project headcount and cost, cost per head, joiners in the month, a cost trend by project, a project register and a project × country matrix, and follows the same buttons and filters. In the Group view, a **country share chart** compares each country's share of group headcount with its share of group cost (e.g. India: 36% of heads, 9% of cost). A **monthly trend** of actual against budget shows headcount and cost across all months, and links can be shared, e.g. `…/#p=Aug-2026&c=India`.

The dashboard shows:
- headline cards against budget
- the workforce walk (opening + hires − leavers − terminations + project hires = closing) as a waterfall chart
- a cost bridge from budget to actual
- variance commentary in four parts: what happened, why, business impact and action required
- a variance table by country, with a country filter
- the internal grade mix and the location mix

![Dashboard](docs/screenshot-desktop.png)

![Projects page](docs/screenshot-projects.png)

## 4. Publishing the dashboard (GitHub Pages, free)
1. Create a **public** GitHub repository and upload this whole folder, keeping the folder structure.
2. In the repository, go to **Settings → Pages → Build and deployment**. Set *Source* to **Deploy from a branch**, *Branch* to **main**, and *Folder* to **/docs**, then **Save**.
3. Wait about a minute. The site goes live at `https://<username>.github.io/<repo-name>/`. Paste that link at the top of this README.
4. **Install as an app:**
   - Android / Chrome: open the link, then use the **Install app** button or ⋮ → *Install app*.
   - iPhone (Safari): Share → *Add to Home Screen*.
   - Desktop Chrome / Edge: use the install icon in the address bar.

   It opens full-screen with its own icon and works offline.

**Monthly update:** run `consolidation/run_consolidation.bat` for the new month. From `consolidation/output/`, copy **`dashboard_data_<Mon-YYYY>.json`** and **`index.json`** into `docs/data/`, then commit. The new month appears in the Month filter and the trend; earlier months stay available.
**View any month without publishing:** use **Load month files** in the dashboard (select several JSON files at once). The file stays on that device.

## 5. Running the consolidation
```
cd consolidation
pip install -r requirements.txt
python consolidate.py --period Nov-2026 --input ./inbox --output ./output
# repeat for Jul-2026 … Oct-2026 to rebuild every month
```
Or double-click `run_consolidation.bat`. Details are in [`consolidation/README.md`](consolidation/README.md).

## 6. Setting up the n8n workflow
1. In n8n, create a **Data Table** called `WF_Submission_Log` with these string columns: messageId, country, period, sender, subject, fileName, status, issues, driveFileId, driveLink, and a date column: receivedAt.
2. **Import** `n8n/workforce_data_intake.json`. Connect your Gmail and Google Drive credentials, select the table in the four Data Table steps, pick your **WF_Inbox** Drive folder, and set your email in *Email Status to FP&A*.
3. SPOCs email their file with the subject **`WF-DATA | <Country> | <Mon-YYYY>`**, for example `WF-DATA | India | Nov-2026`.
4. Gmail is checked **every hour on the 25th** (India time); the **Run Now** trigger processes waiting emails on any other day. Emails that were already processed are skipped by message ID, so it is safe to re-run.

## 7. Testing and controls
- **Intake:** tested live on five real submissions. Nine subject and attachment cases were unit-tested, including a wrong country, a wrong month, no attachment, two attachments and a mismatched file name.
- **Consolidation:** reproduces the independent control totals exactly for the walk, and within ₹10 per line for cost (per-person rounding).
- **Negative test:** a planted duplicate code, an invalid grade, a missing exit type, a dropped employee and a missing country file all raised the expected errors.
- **Months chain:** each month's closing headcount equals the next month's opening for every country and population (Jul→Nov). All 50 budget lines are within the set ranges (headcount +2% to +5%, cost −2% to +1%).
- **Dashboard:** checked at desktop and phone width, with month, year and country filters, shared links and offline mode. It loads with no browser errors.
- **Definitions:** headcount is the population active at month-end. Monthly cost is internal CTC ÷ 12 plus external bill rate × billable units, at the month's FX rate. Budget is at the same FX rate, so variances carry no currency effect.

## 8. AI tools used
Claude (Anthropic) was used for solution design, code generation, sample data generation, testing and documentation. The n8n workflow was built and tested through n8n's MCP integration.

## 9. Data note
All names, codes and amounts are **fictitious sample data** created for this capstone. No client or personal data is included, in line with ICAI's guidance on AI tools and confidential information.

## Repository layout
```
docs/                 CFO dashboard web app (GitHub Pages serves this folder)
  index.html, app.js, styles.css, manifest.webmanifest, sw.js, lib/d3.min.js, icons/
  data/index.json + dashboard_data_<Mon-YYYY>.json   ← add one file per month
consolidation/        consolidate.py, run_consolidation.bat, budget, assumptions (FX), sample inbox, sample output
n8n/                  workforce_data_intake.json (import into n8n)
sample_data/          the country workforce files as SPOCs send them, Jul–Nov 2026 (5 countries × 5 months)
```
