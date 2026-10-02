# Deal Flow Automation for an Advisory Firm

**AICA Level 2 project, Batch B93, Pratik Chheda**

A working system that takes an advisory firm's client from the first lead to a signed
merchant banker MOU with as little manual drafting as possible. Three parts work together:

1. **A lead and meeting tracker** (Windows desktop app plus a sign-in protected web app).
2. **n8n workflows** that move each client from stage to stage, create Drive folders,
   chase documents and send approvals.
3. **Claude custom skills** that draft the mandate letter and the merchant banker MOU in the
   firm's exact approved wording. A partner approves each document before it leaves the firm.

> This is a white-labelled copy made for the course. The firm name, registration numbers,
> addresses, signatories, letterhead, logo and every client record have been removed or
> replaced with placeholders ("Sample Advisory", `example.com`, "YOUR LOGO").
> The tracker ships with an empty dataset.

## The problem

An advisory firm running IPO and fund-raising mandates repeats the same steps for every
client: log the lead, follow up, send a mandate letter, collect a long data checklist, write
an information memorandum and an investor deck, then sign an MOU with a merchant banker.
Each step was manual (email, Word, spreadsheets), so status was hard to see and
documents took days.

## How it fits together

```
Tracker (desktop / web) --stage change--> n8n webhooks --> Claude API + custom skills
        ^                                      |                     |
        |  journal file on Google Drive        v                     v
        +------------------------------ client folders, checklists, .docx / .pdf / .pptx
                                         Gmail approvals (Approve / Request changes)
```

| Stage | Trigger | n8n workflow | Output |
|---|---|---|---|
| 1 Lead | Daily 9:00 | W0 Daily follow up digest | Email digest |
| 2 Prospect | Tracker: stage Prospect | W1 Tracker stage router | Code name, Drive folder tree, client record |
| 3 Mandate | Tracker: Generate mandate | W1b Mandate letter | Mandate .docx/.pdf, partner approval, email to client |
| 3b Signed | Every 30 min | W1c Signed copy watcher | Stage moves to Mandate signed |
| 4 Data | Mandate signed | W2 Data request, W3a email intake, W3b WhatsApp intake, W3c reminders | Checklist, filed documents, progress |
| 5 IM | Tracker: Data complete | W4 Information memorandum | Anonymous and named IM |
| 6 Deck | IM approved | W5 Investor deck | Anonymous and named deck |
| 7 MOU | Tracker: Generate MOU | W6 Merchant banker MOU | MOU .docx/.pdf |

Shared sub-workflows: Claude skill runner, File client document, Tracker journal writer,
Tracker users (web logins), Error alert.

## What is inside

| Folder | Contents |
|---|---|
| `tracker/` | Electron desktop app (SQLite, Google Calendar and Drive sync, automation bridge) and the web app in `tracker/app` (PWA, encrypted sign-in, deal pipeline, mandate and MOU forms) |
| `skills/` | Claude custom skills: advisory mandate letter and merchant banker MOU (blank template, fill script, sample input), plus an upload script |
| `n8n/` | Notes for importing the workflows and the data table layouts |
| `tools/` | Data inject/extract, protected website build, demo builder with invented data, local preview server, n8n export |
| `docs/` | Full setup guide: Google, n8n, Anthropic, skills and hosting |

## Key techniques

- **Claude Messages API with the code execution tool and custom skills**: documents are
  built inside Claude's container from a fixed template, so approved legal wording is never
  rewritten; only the blanks are filled.
- **Human in the loop**: every generated document goes to a partner through a Gmail
  "send and wait" approval before it reaches the client.
- **Two-way sync without a server**: the tracker and n8n exchange small journal files on
  Google Drive, so the desktop app, the web app and the automation stay in step.
- **Security**: the hosted web app is encrypted (AES-256-GCM) and opens only after sign-in;
  each user's key is wrapped with PBKDF2 (600,000 rounds). Webhooks need a shared header
  secret. API keys stay in n8n credentials and are never stored in the app.
- **Safe demos**: a demo builder swaps every real record for invented ones and blocks all
  automation calls, so the app can be shown to prospects.

## Try it

```
cd tracker
npm install
npm start      # desktop app with an empty tracker
npm test       # smoke test
```

Or open `tracker/app/index.html` in a browser (`node tools/serve.js tracker/app 5184`).
See [docs/SETUP.md](docs/SETUP.md) to connect Google, n8n and the Anthropic API.

## Built with

n8n, Claude API (Anthropic), Electron, sql.js, Google Drive, Calendar, Sheets and Gmail APIs,
python-docx, docx-js.
