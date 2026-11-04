# Agentic-browser tasks for ChatVault

These are task prompts for an agentic AI browser (Claude in Chrome, Perplexity Comet or similar).
Each one turns a manual chore around ChatVault into a supervised agent run. Record a short screen
capture of one run for the course demo.

Safety rules that apply to every task (include them in the prompt):
- Do not change sharing to "Anyone with the link" or make anything public.
- Do not delete files. Do not sign in, enter passwords, or accept new permissions; stop and ask me.
- Before any upload or submission, show me the file name and destination and wait for my "yes".

---

## Task 1 — File the latest archive in Google Drive

> In my Google Drive, open the folder **ChatVault Archive**. If it does not exist, create it.
> Inside it, open (or create) a folder named after the client tag in the archive I tell you, for
> example **Client: Shah**.
> Upload the most recent file in my Downloads whose name ends with **_archive.zip**.
> Before uploading, tell me the file name, its size and the destination folder, and wait for me
> to confirm.
> After uploading, copy the file's Drive link (keep sharing as "Restricted") and give it to me in
> one line in this format: `<file name> | <Drive folder path> | <link>`.

What to show the evaluator: the confirmation step, the upload, and the restricted-sharing link
that you then paste into the chat's **Note** field in ChatVault (Chat info → Tags and note).

## Task 2 — Verify GSTINs mentioned in a chat

> Here is a list of GSTINs taken from a ChatVault chat: `<paste>`.
> For each one, open https://services.gst.gov.in/services/searchtp and search the GSTIN.
> If a CAPTCHA appears, stop and ask me to solve it.
> Record the legal name, status (Active/Cancelled), registration date and last return filed.
> Give me the results as a table with one row per GSTIN and a column for the date you checked.

What to show: the agent pausing for the CAPTCHA, then the results table, which you can save
into the chat's note or alongside the exported archive.

## Task 3 — Weekly archive check

> Open ChatVault (the file **ChatVault.html** on my computer), sign in when I tell you I have
> entered my password, open **⋮ → Saved chats and backup**, click **Verify all**, and report how
> many chats were verified and whether any failed. Then open the **Backup** tab and stop; I will
> enter the backup passphrase myself.

What to show: an agent operating the app itself, with the human handling every secret.

---

## The local filing agent (`filing_agent.py`)

Runs on your computer without a browser. It watches Downloads, verifies every SHA-256 value
inside each ChatVault archive (both the media list and the output-hash list), and files the
archive under its first tag. Failed archives go to `_Quarantine`. Every action is written to
`register.csv`.

```
python agent/filing_agent.py --watch "C:/Users/<you>/Downloads" --archive "D:/Client Records/WhatsApp" --sync "G:/My Drive/ChatVault"
```

Pair it with Task 1: the filing agent organises and verifies locally; the browser agent publishes
to Drive with a human confirmation step.
