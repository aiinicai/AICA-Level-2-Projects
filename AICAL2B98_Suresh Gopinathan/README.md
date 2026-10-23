# TickTrail

TickTrail is an audit compliance register for a Chartered Accountant's practice in India. It takes an audit assignment from acceptance to the final file in six stages, so that a member of staff, or an articled student, can carry out the work step by step and every conclusion is backed by notes, working-paper references and scanned evidence.

The app works out which laws and reports apply to each client from its figures, entity type, activity and sector. Nobody chooses them by hand.

This folder is the **self-hosted edition**: TickTrail running on the firm's own Windows server, with all client data kept on that server.

---

## Contents

- [What TickTrail does](#what-ticktrail-does)
- [The six stages](#the-six-stages)
- [Checklist library](#checklist-library)
- [People and access](#people-and-access)
- [Documents](#documents)
- [Testing mode](#testing-mode)
- [Self-hosted edition](#self-hosted-edition)
- [Installing on Windows](#installing-on-windows)
- [Command-line tools](#command-line-tools)
- [Settings](#settings)
- [Security](#security)
- [Data model](#data-model)
- [For developers](#for-developers)
- [Open items](#open-items)

---

## What TickTrail does

| Area | What it covers |
|---|---|
| **Applicability** | CARO 2020, tax audit, IFC, MSMED, GST, labour laws, transfer pricing, FEMA, CSR and others are decided from the client's figures, entity type, activity and sector. Tax audit is decided once on the first page. |
| **Clients** | PAN checked for format and match with entity type. Names always in capitals. Figures entered as absolute rupee amounts, with a figure-in-words helper and a note on what each field should include; every field is mandatory. Master data carries forward from the previous year, with a financial-year selector beside the client name. |
| **Report format** | Picked automatically from the entity type. |
| **Working the checklist** | Every checkpoint has steps to follow. Marking a point Done needs a note of at least 10 characters, a working-paper reference and an attached PDF. |
| **Time** | A timer per audit file, manual entries, who did the work, and billable time per person and in total. |
| **Automatic updates** | When legal thresholds or a client's figures change, every open audit file recalculates its applicability. Marks are kept, a notice is shown, and signed-off or assembled files are never changed. |
| **Retention** | Signed-off files are kept for 7 years and cannot be deleted in that period (except in testing mode). |

## The six stages

Every audit file moves through six stages, with a **Save & next** bar at the bottom of each.

1. **Acceptance:** engagement team (partner, reviewer and staff chosen from a list), an independence declaration from each of them, eligibility, the letter to the previous auditor, and the SA 210 engagement letter. The dashboard shows anyone whose declaration is still pending.
2. **Planning:** understanding the entity, materiality (SA 320), the risk register (SA 315), time budget, work allocation, the list of documents to request from the client, and the SA 300 audit plan: an overall strategy plus an area-wise plan of nature, timing, extent, person assigned and procedures.
3. **Audit programme:** the checklist itself, module by module, with steps, notes, references and attachments.
4. **Evidence:** every supporting PDF in one place, by stage and checkpoint.
5. **Reporting:** misstatements (SA 450), subsequent events, going concern, the management representation letter (SA 580), the opinion, UDIN, and **CARO 2020 clause by clause**:
   - all 41 sub-clauses, with standard favourable and not-applicable wording;
   - adverse answers need details, with tables where the Order expects them;
   - answers filled in automatically from the client's profile where possible;
   - Annexure A downloadable on its own and used inside the audit report.
6. **Records:** file assembly within 60 days of the report date (SA 230), the file index, the change log and later amendments.

"Start an audit" always leads somewhere: to an existing file, to a new file at Acceptance, or to entering the year's figures first.

## Checklist library

| Part | Modules | Checkpoints |
|---|---|---|
| Core | 16: ENG, SA, FS, CA, CARO, IFC, IT, GST, MSME, LAB, TP, FEMA, CSR, LLP, TRUST, LIST | 195 |
| Sectors | 17: agriculture, chemicals, construction, education, food, general, healthcare, hospitality, IT, media, manufacturing, mining, NBFC, pharma, power, retail, transport | 79 |

The library covers audits of FY 2025-26 under the Income-tax Act 1961 and flags the Income-tax Act 2025 for tax year 2026-27 onwards. Admins can edit it under **Settings > Checklist library**. Review it after each Budget and each MCA or CBDT notification.

## People and access

| Role | Can |
|---|---|
| **Staff** | Add clients and figures, start audit files, work on checkpoints, record time, see their own hours. |
| **Reviewer** | All of the above, plus review other people's points and sign off a file once every point is complete and reviewed. |
| **Admin** | All of the above, plus approve, disable or delete users, reset passwords, set roles and hourly rates, see billable amounts, edit the library and thresholds, and delete clients and files. |
| **Owner** | The admin created at first start. Cannot be removed. |

- A new person creates a login and sends an access request. They see nothing until an admin approves them.
- Settings (Team & access, Legal thresholds, Checklist library) are visible to admins only.
- The profile menu ends with **Log out**. There are no keyboard shortcuts.

## Documents

Every document offers **preview, print, PDF and Word**. The documents are:
- engagement letter (SA 210);
- letter to the previous auditor;
- document request letter;
- audit plan (SA 300);
- planning memorandum;
- management representation letter;
- management letter;
- Form 3CD clause drafts;
- audit report (draft);
- CARO 2020 report (Annexure A);
- audit file index;
- change log.

PDFs are built in the browser (Times fonts, justified text, tables with repeated headers, page numbers). "₹" prints as "Rs." in PDFs only.

Firm details (name, FRN, address, city, email, phone) are entered once under **Settings > Team & access** and appear on every letter.

## Testing mode

Testing mode relaxes the workflow locks so the whole flow can be tried end to end. With it on:
- the audit programme opens without approvals;
- points can be marked Done without notes or PDFs;
- sign-off goes through with gaps;
- test files can be deleted.

It is **on** in this package. An admin turns it off with **Lock all controls** on the yellow banner before real audits begin.

---

## Self-hosted edition

TickTrail was first built as a page hosted on claude.ai. This edition runs the same page on your own server. Everything the page does stays the same; only the services underneath it change.

```
Browser (staff)
   │  HTTPS
   ▼
Caddy  ── certificates from Let's Encrypt, ports 80/443
   │  http://127.0.0.1:8080
   ▼
server.js (Node.js) ── logins, permissions, live updates, PDFs
   │
   ├── data/ticktrail.db   SQLite database (all records)
   └── data/blobs/         attached PDFs
```

| Service the page needs | Hosted on claude.ai | Self-hosted |
|---|---|---|
| Database with live updates | claude.ai database | SQLite, with live updates sent to browsers through server-sent events |
| Who is signed in | Claude account plus a TickTrail password | TickTrail user name and password, checked by the server |
| PDF storage | claude.ai file store | `data/blobs` folder |
| Downloads | claude.ai download prompt | the browser's own download |

The page talks to these services through `claude.use(...)`. `public/shim.js` provides the same interface backed by the server, so the audit logic did not need changing.

### Folder layout

```
TickTrail/
├── server.js                    the server (no packages to install)
├── config.json                  settings
├── public/
│   ├── app.html                 the TickTrail page, self-hosted edition
│   └── shim.js                  database, login, upload and download services for the page
├── seed/                        starting data loaded on first start
│   ├── library/                 checklist library and settings (35 documents)
│   └── members/                 the owner's admin record
├── caddy/Caddyfile              HTTPS settings (put caddy.exe here)
├── windows/                     PowerShell scripts used by the .cmd files
├── tools/build_app.py           rebuilds public/app.html from the hosted page
├── 1 - Try TickTrail now.cmd
├── 2 - Install to run automatically (as administrator).cmd
├── 3 - Set up HTTPS for internet access (as administrator).cmd
├── Create desktop shortcut.cmd
├── Backup now.cmd
├── Reset a password.cmd
├── Uninstall (as administrator).cmd
├── SETUP-GUIDE.txt              step-by-step installation guide
└── README.md                    this file

Created when running:
├── data/                        database, PDFs and server.log
└── backups/                     nightly backups (newest 30 kept)
```

## Installing on Windows

Full steps are in **SETUP-GUIDE.txt**. In short:

1. Install **Node.js 22.13 or later** (the LTS version from nodejs.org).
2. Unzip to `C:\TickTrail`.
3. Run **1 - Try TickTrail now.cmd** and create the owner login.
4. Run **2 - Install to run automatically**. TickTrail then starts with the computer, restarts if it stops, and backs up every evening at 8:30 pm.
5. Run **Create desktop shortcut.cmd** for an icon on the server's desktop.
6. For access from outside the office, run **3 - Set up HTTPS**. This needs:
   - a web address pointing to the office's fixed IP address;
   - ports 80 and 443 forwarded on the router;
   - `caddy.exe` in the `caddy` folder.

   Cloudflare Tunnel is an alternative when there is no fixed IP address.

The zip contains scripts, so Gmail blocks it as an attachment. Download it on the server directly, or move it by Google Drive, OneDrive or a USB drive.

## Command-line tools

Run these from the TickTrail folder (as administrator once step 4 is done):

| Command | Does |
|---|---|
| `node server.js` | Start the server |
| `node server.js --backup [folder]` | Copy the database and PDFs. Without a folder, saves to `backups\<date-time>` and keeps the newest 30. Safe while the server is running. |
| `node server.js --import <folder>` | Load exported documents laid out as `<folder>/<collection>/<id>.json` |
| `node server.js --reset-password <user>` | Set a temporary password; the person chooses a new one at their next login |
| `node server.js --list-users` | Show user names, names and roles |

## Settings

`config.json`:

| Key | Default | Meaning |
|---|---|---|
| `host` | `127.0.0.1` | Answer only on this computer (Caddy forwards to it). Use `0.0.0.0` for office-network-only use without Caddy, together with `trustProxy: false`. |
| `port` | `8080` | Port on this computer. Change `caddy/Caddyfile` to match. |
| `dataDir` | `data` | Where the database and PDFs are kept. |
| `trustProxy` | `true` | Read the visitor's address and HTTPS status from Caddy's headers. |
| `allowSignup` | `true` | Let new people create a login and request access. |
| `idleMinutes` | `30` | Log out after this long without activity. |
| `maxSessionHours` | `12` | Log out after this long in any case. |

## Security

**Logins**
- Passwords are stored as scrypt hashes with a separate salt for each person, and must be at least 8 characters with letters and numbers.
- Five wrong passwords lock a login for 15 minutes. Sign-in and sign-up attempts are also limited per address.
- Sessions use an HttpOnly, SameSite cookie, which is marked Secure over HTTPS. They end after 30 idle minutes or 12 hours.
- A password reset ends that person's sessions everywhere.

**Permissions**
- Permissions are checked on the server for every read and write, not in the browser. The browser cannot grant itself more access.
- A login that is not yet approved, or is disabled, can read nothing except its own access request.
- Hourly rates are visible to admins only. The library, thresholds and team list can be changed only by admins.

**Requests and files**
- Every data request must carry a header that other websites cannot add, which blocks cross-site requests.
- Only real PDF files can be uploaded, up to 20 MB, and they are served only to approved people.
- Pages are sent with a content security policy and standard protective headers.

**On the server**
- The install script restricts the `data` and `backups` folders to administrators and the SYSTEM account.

## Data model

Records are JSON documents in collections, stored in SQLite.

| Collection | Holds |
|---|---|
| `library` | Checklist modules `{id, name, need, order, items[{id, sec, text, ref, risk, steps[]}]}`; `_meta` (library version note), `_thresholds` (legal limits), `_firm` (firm details), `_settings` (`testMode`) |
| `clients` | Profile fields and `figures[fy]` in absolute rupees |
| `audits` | Scope, applicability, figures, `results` per checkpoint, and `acc`, `plan`, `rep`, `rec` for the stages; subcollections `time` (timer entries) and `log` (change log) |
| `members` | `{status, role, designation, mno}` per person |
| `requests` | Pending access requests |
| `rates` | Hourly rates |

Server tables:
- `users`: logins;
- `sessions`;
- `blobs`: PDF details, with the files themselves in `data/blobs`;
- `names`: names kept for people whose logins were deleted, so their work stays credited.

## For developers

**Where the page comes from**
- `public/app.html` is built from the hosted page by `tools/build_app.py`, which applies a fixed list of exact replacements: the login, logout, password, team-management wording and actions.
- Each replacement must match exactly once, so a changed source fails loudly rather than producing a half-patched page.
- To update after changing the hosted page:
  ```
  python3 tools/build_app.py <TickTrail.html from the hosted artifact> public/app.html
  ```

**Server and browser**
- `server.js` uses only Node's built-in modules (`http`, `crypto`, `node:sqlite`). Document writes follow the hosted database's rules:
  - `set` replaces a document;
  - `update` merges nested objects and replaces arrays, and fails if the document does not exist;
  - `delete` is idempotent.
- `public/shim.js` gives the page `claude.use("db" | "user" | "assets" | "downloads")`. It keeps live subscriptions up to date from the `/api/events` stream and catches up after a dropped connection or a sleeping tab.

**Testing**
- The edition was tested with Playwright in Chromium:
  - owner setup;
  - sign-up, approval, and live updates between two people;
  - permission refusals;
  - PDF attachments;
  - engagement letter preview, PDF and Word;
  - password reset and forced change;
  - disabling a user;
  - login lockout;
  - backups.
- The Windows scripts were not run on Windows during development.

## Open items

- Firm details still need to be entered; letters show placeholders until then.
- Testing mode is on until an admin clicks **Lock all controls**.
- The online copy on claude.ai is separate and is not synced. If clients or files are added there before moving, export them and load them with `--import`.
- Possible additions:
  - consolidated financial statements (CARO 3(xxi) is currently answered N.A. for standalone);
  - IFC working papers (risk and control matrix);
  - a client portal for uploading documents;
  - a staff workload report;
  - bulk import of client figures from Excel.
