# n8n workflows

Export the live workflows into `n8n/workflows/` with an n8n API key
(n8n > Settings > n8n API > Create an API key):

```
powershell -ExecutionPolicy Bypass -File tools/export-n8n.ps1
```

Exports contain nodes, connections and settings. Credentials appear by name only; no
secrets are exported.

## Importing into another n8n

1. Import every JSON (Workflows > Import from file).
2. Create the credentials and select them on the nodes that show a warning:
   - Google Drive, Google Sheets, Gmail (OAuth, the account that owns the tracker Drive folder)
   - Anthropic API (Sample Advisory): HTTP Request nodes in Claude skill runner, File client document, W4
   - Sample Advisory tracker webhook secret (Header Auth, name `X-Sample Advisory-Secret`): webhooks in W1, W1b, W6, Tracker users
   - WhatsApp Business (W2, W3b), optional
3. Sub-workflow links: the Execute Workflow nodes point at workflow IDs from the original
   instance. Open each one and pick the workflow by name again.
4. Settings > Error workflow: select DF · Error alert on every workflow.
5. Create the data tables below, then publish in this order: Tracker journal writer, Claude
   skill runner, File client document, W5, W4, W2, then W1, W1b, W6, Tracker users, the rest.

## Data tables

**Sample Advisory Config** (one row): trackerFolderId, clientsParentFolderId, checklistTemplateId,
skillMandate, skillIM, skillDeck, skillMOU, claudeModel, pcEmail, digestEmails, intakeEmail,
waPhoneNumberId

**Sample Advisory Clients**: leadId, codeName, clientName, clientEmail, clientDomain, clientPhone,
ownerEmail, associate, stage, rootFolderId, rootFolderUrl, f01Mandate, f01Signed, f02Data,
f02Financials, f02Statutory, f02Business, f02KYC, f02Unsorted, f03Anon, f03Named, f04Anon,
f04Named, f05MB, f05Signed, f06Corr, checklistSheetId, imFileIds, mbName, mbEmail

**Sample Advisory Tracker Users**: key, payload, savedBy (managed by the tracker's Users and access page)

## Webhooks used by the tracker

| Path | Workflow | Auth |
|---|---|---|
| POST /webhook/df-stage | W1 | Header secret |
| POST /webhook/df-mandate-request | W1b | Header secret |
| POST /webhook/df-mou-request | W6 | Header secret |
| GET /webhook/df-users | Tracker users | none (returns encrypted records only) |
| POST /webhook/df-users-save | Tracker users | Header secret |
