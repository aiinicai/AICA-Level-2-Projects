# Setup guide

## 1. Accounts

| Account | Used for |
|---|---|
| Google Workspace or Gmail that owns the tracker Drive folder | Drive sync, client folders, checklists, n8n Drive/Sheets/Gmail credentials |
| n8n cloud | All workflows |
| Anthropic Console (API key with credit) | Claude skill runs from n8n |
| WhatsApp Business Cloud API (optional) | Document intake by WhatsApp |
| Website hosting (optional) | Protected web tracker |

Emails go out from the Gmail account connected in n8n; set its default "Send mail as"
alias (for example the firm's info@ address) in Gmail settings, Accounts and Import.

## 2. Google Cloud

1. Create a project; enable Google Drive API and Google Calendar API.
2. OAuth consent screen: Internal (Workspace) or External with test users.
3. OAuth client **Desktop app** for the exe (client ID plus secret go into the tracker's Google card).
4. OAuth client **Web application** for the web tracker; add the site origin under Authorized
   JavaScript origins; put its client ID in `tracker/app/config.json` (copy `config.example.json`).

## 3. n8n

Follow [n8n/README.md](../n8n/README.md): import workflows, credentials, data tables, publish.
Fill the Sample Advisory Config row:

- `trackerFolderId`: the shared Drive folder the tracker syncs to
- `clientsParentFolderId`: link of the "Sample Advisory Clients" Drive folder
- `checklistTemplateId`: Google Sheet made from the data checklist (tab named `Checklist`)
- `skillMandate`, `skillMOU` (and later `skillIM`, `skillDeck`): skill IDs from step 4
- `claudeModel`: e.g. `claude-opus-5`
- `pcEmail`, `digestEmails`, `intakeEmail`

## 4. Claude skills

Double-click `skills/upload-mandate-skill.bat` and `skills/upload-mou-skill.bat` (or run
`skills/upload-skill.ps1 <folder>`), paste the Anthropic API key, and copy the printed
`skill_...` IDs into Sample Advisory Config. The skill runner also loads Anthropic's docx, pdf,
pptx and xlsx skills, which provide the Word library and LibreOffice conversion.

## 5. Tracker

- Desktop: install the built app; Reports and export: Google account (Connect), Google Drive
  sync (folder link), Automation (n8n address, header name `X-Sample Advisory-Secret`, secret, partner emails).
- Pipeline stages: Prospect and Data complete notify n8n; Generate mandate and Generate MOU
  send the dashboard's data to n8n; later stages come back from n8n through Drive sync.

## 6. Protected website

1. `tools/protect-website.ps1` asks for the first admin and writes `dist-website/` with the
   tracker's code plus data encrypted (AES-256-GCM; each user's password unwraps the key).
2. Upload everything in `dist-website/` to the tracker folder on the site.
3. Sign in as admin; Reports and export, Automation: save the secret (this also stores the
   user list in n8n); Users and access: add users with temporary passwords.
4. To revoke someone completely: remove them, rebuild the protected copy, re-upload, and
   remove their access to the shared Drive folder.

## 7. Client demo

`node tools/make-demo.js tracker/app/index.html demo.html` (with real data loaded locally)
builds a copy with invented companies, people, contacts, notes and amounts; it refuses to
save if any real name, phone number or email remains, never contacts Drive or n8n, and
plays back the automation steps.
