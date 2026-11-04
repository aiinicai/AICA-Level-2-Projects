# ChatVault — WhatsApp Chat Archiver

A use-case project for the AI ICI course. ChatVault turns a WhatsApp chat export into a
searchable, analysable, tamper-evident archive. It reproduces the familiar WhatsApp chat
layout, adds role-based access control, and fingerprints every file with SHA-256.

## Problem
WhatsApp is now a primary business channel. Its own export gives a plain text file and a pile
of loosely named media files: hard to read, impossible to search properly, and unsuitable as a
record or as evidence.

## What is in this folder

| Path | What it is | Tools |
|---|---|---|
| `app/dist/ChatVault.html` | The web app. Double-click to open in Chrome or Edge. Works offline. | HTML, CSS, JavaScript |
| `app/src/` | App source: `style.css`, `app.js` | HTML, CSS, JavaScript |
| `app/build.py` | Assembles the source into one HTML file | Python |
| `python/chatvault.py` | Command-line archiver (PDF transcript, Excel index, hashes) | Python |
| `agent/filing_agent.py` | Filing agent: verifies and files exported archives by client tag | Python |
| `agent/BROWSER_AGENT_TASKS.md` | Task prompts for an agentic AI browser (Drive filing, GSTIN checks) | Agentic browser |
| `samples/` | Fictional exports (Android group with a later re-export, iPhone 1:1) and the generator | Python |

## Running it

**Web app:** open `app/dist/ChatVault.html` in a browser. The first screen creates the admin
account (and, optionally, demo `reviewer` and `viewer` accounts). Two sample chats load
automatically. Import your own export with **+** or by dragging the ZIP onto the window.

**Python CLI:**
```
pip install openpyxl reportlab
python python/chatvault.py "WhatsApp Chat with X.zip" -o output --me "Your Name" [--mask]
cd output/X_archive && sha256sum -c SHA256SUMS.txt      # verify integrity later
```

**Rebuild the app after editing source:** `python app/build.py`

## Features

**Reading (WhatsApp-style view)**
- Parses both Android and iPhone export formats, 12/24-hour time, DD/MM and MM/DD dates,
  multi-line messages, captions, edited, deleted and omitted media, system messages
- Bubbles with tails, per-sender name colours in groups, date chips, "you" on the right
- Inline photos, video, voice-note player with waveform progress, document cards
- Full-screen viewer with zoom, filmstrip and keyboard navigation; built-in PDF reader
- WhatsApp text formatting (*bold*, _italic_, ~strike~, ```mono```), clickable links
- Light and dark themes; phone, tablet and desktop layouts

**Finding**
- Search by text, sender, date range and type (photos, videos, voice, docs, links, deleted)
- Jump to any date from the date chip; media, docs and links gallery

**Insights and AI**
- Message counts, activity by hour, participation chart
- Rule-based detection of requests/commitments and rupee amounts (works offline)
- AI summary with Claude (when opened inside Claude): summary, action items, timeline,
  amounts and open questions, each linked back to the source message

**Saving and retrieving (v1.1)**
- Imported chats are saved in the browser (IndexedDB), encrypted with AES-256-GCM, and come back
  after a reload. One vault key encrypts all chats; it is wrapped separately with each user's
  password (PBKDF2, 150,000 iterations), so every authorised user unlocks the same archive.
- Every saved chat is re-hashed when opened and compared with its import fingerprint
- Tags and private notes per chat; filter the list by tag; sort by latest message, name or import date
- Search across all chats at once from the sidebar (names, tags, notes and message text)
- Saved-chat manager: storage use, verify one or all, permanent delete (Admin only)
- Encrypted backup to one file with its own passphrase, and restore on any computer

**Merging and comparing exports (v1.1)**
- Import a newer export of the same chat and ChatVault offers to merge it
- Messages deleted after the earlier export are recovered and shown with their original text
- Edits are flagged with the earlier version; messages that vanished ("delete for me") are marked
- A "Changes between exports" panel lists every difference with a link to the message

**Access control**
- Accounts with salted PBKDF2-SHA-256 password hashes (150,000 iterations)
- Three roles: Admin, Reviewer, Viewer, with a published permission matrix
- Viewer role sees phone numbers and emails masked, optionally names replaced, and cannot export
- Five failed attempts lock an account for two minutes; auto-lock after inactivity
- Audit log of sign-ins, imports, merges, exports, backups, deletions and user changes; CSV export

**Integrity, redaction and export**
- SHA-256 of every source export and every file inside it, computed at import
- Complete archive ZIP: chat viewer HTML, media sorted into folders and renamed
  `date_time_sender_file`, Excel index with change status, original transcripts,
  `SHA256SUMS.txt`, `OUTPUT HASHES.txt` (hashes of the generated files) and an integrity statement
- Redaction on export: mask phone numbers and emails, and/or replace names with Participant A, B, C
- Integrity statement references Section 63 of the Bharatiya Sakshya Adhiniyam, 2023

**PDF export and date ranges (v1.1)**
- PDF · Evidence transcript: cover page with export fingerprints, numbered message table with
  RECOVERED / EDITED / MISSING LATER flags and photo thumbnails, full integrity statement,
  attachment fingerprint table and signature lines; "Page x of y" footer with the source hash
- PDF · Chat view: pages that look like the phone conversation, photos inline, message numbers
- Every export can be limited to a period (From / To, or Whole chat, Last 30 days, financial year,
  latest month); message numbers stay those of the full chat so citations remain valid
- After each export the SHA-256 of the produced file is shown and written to the audit log
- Known limit: the PDF font has no emoji or Indic scripts; emoji are dropped in PDFs only

**Storage folder (v1.3)**
- On first sign-in ChatVault asks once where to keep the archive: a folder on this computer, a
  folder inside Google Drive / OneDrive / Dropbox (the drive app syncs it), or the browser only
- Change, sync, reconnect or disconnect later in ⋮ → Saved chats and backup → Storage folder
  (also linked from Users and roles → Settings)
- Folder layout: `vault.json` (archive id and accounts), `chats/<id>/meta.cvault` and
  `<sha256>.cvault` per export, all AES-256-GCM encrypted; `README.txt` explains it
- Two-way sync: new chats and changes (tags, stars, notes, client details) go both ways;
  deletions propagate; every file restored from the folder is re-checked against its SHA-256
- Another computer: on the first screen choose "Open an existing archive folder", pick the same
  folder and sign in with your usual account
- Needs Chrome or Edge with ChatVault.html opened from the computer; the copy published inside
  Claude cannot reach folders and keeps using browser storage and backup files

**Practice features (v1.2)**
- Client and matter fields per chat (client, PAN, GSTIN with format checks, matter, FY, reference);
  sort and group the chat list by client; printed on PDF covers and in the integrity statement
- Star messages, add private notes to any message, copy a ready-made citation
  (quote, sender, chat, message number, date and time, client, source hash)
- PDF · Evidence bundle: only starred messages, each as Annexure A-1, A-2… with photo, fingerprint,
  note and citation, plus an index, integrity statement and signature lines
- Section 63 certificate draft (.docx) in the form of the Schedule to the Bharatiya Sakshya
  Adhiniyam, 2023: Part A pre-filled with hash values and device details, blank Part B for the
  expert, and Annexure H-1 hash report with the chain of custody. Draft only; review and sign.
- Chain of custody per chat: imports, merges, verifications on open, exports and certificates,
  each with user, time and SHA-256
- Gujarati and Hindi text in PDFs (Noto Sans fonts, SIL Open Font License, embedded)

**Navigation and comfort (v1.2)**
- Calendar with message-density shading to jump to any day
- Bulk import of many exports at once, with automatic merging of repeat exports
- Clear notices when a chat was exported without media, or when some media is missing
- Appearance: Light, Dark or System; six colour themes; patterned, plain or tinted chat background
- Privacy screen button (Ctrl + .), and optional automatic privacy screen when switching windows
- Keyboard shortcuts (press ? in the app)

**Insights**
- Response times per participant (median and average) and the longest silences

**Guided tour**
- A nine-step spotlight tour runs on first sign-in and from the **?** button

**Filing agent and agentic browser**
- `filing_agent.py` watches Downloads, verifies every hash in each archive, files it under
  `<tag>/<chat>/`, quarantines anything that fails and keeps `register.csv`
- `BROWSER_AGENT_TASKS.md` gives supervised agentic-browser tasks: upload to Google Drive with
  restricted sharing, and GSTIN verification on the GST portal

## Architecture
```
 WhatsApp export (.zip/.txt)
        │
        ▼
 [Browser] JSZip unpack ──► SHA-256 (Web Crypto) ──► Parser ──► Attachment linker
        │                                                         │
        ▼                                                         ▼
 Access control (PBKDF2, roles, audit) ──► WhatsApp-style viewer, search, insights
                                                 │                 │
                                                 ▼                 ▼
                                     Exports (ZIP/HTML/XLSX)   Claude AI summary
 [Python CLI] same parser ──► PDF transcript, Excel index, SHA256SUMS, statement
```
Privacy: all processing runs on the user's device. Nothing is uploaded. The AI summary sends
only message text, never attachments, and only when the user clicks the button.

## Limitations and future scope
- Accounts, saved chats and the audit log live in the browser on one device. Clearing site data
  deletes them, so keep encrypted backups. A multi-user deployment would add a server with a
  proper identity provider.
- WhatsApp may drop media from very large exports; ChatVault flags each missing attachment.
- Next steps: voice-note transcription, Gujarati/Hindi translation, merging multiple exports
  of the same chat, and an agentic step that files archives into a document-management system.

All names and data in the samples are fictional.
