# GST Notice Analyser — CA Desktop Workstation

**ICAI AI (AICA) Level 2 — Capstone Project**

A workstation for Chartered Accountants that turns a GST notice into a working file.
The CA uploads the notice (PDF, scan, or pasted text); the app extracts every detail
with AI, then automatically builds the follow-on work across the practice: the list
of documents to obtain from the client, the questions to raise with them, and a
ready-to-file legal reply and covering emails.

**Multi-user and cloud-backed.** Each person signs in with their own account; everyone
in the same *firm* shares that firm's clients and notices. Data lives in a Supabase
PostgreSQL database with per-firm Row-Level Security, so one firm can never see
another firm's data.

---

## The problem it solves

When a GST notice arrives, a CA repeats the same manual sequence for every case:
read the notice, list the issues, draft a document-request list for the client, note
the questions to ask, track what comes back, and write the reply before the statutory
deadline — for every notice, every time.

This tool does the reading, the document list, the client questions and the first
draft of the reply **automatically from a single notice upload**, and keeps the whole
case file in one place.

---

## Modules

| Module | What it does |
|---|---|
| **Add Notice** | Upload the notice PDF / scan / image, or paste its text. Extract the structured details either by **pasting the result from a Claude.ai chat** (uses the CA's existing subscription, no API cost) or **automatically** if the firm has configured server-side extraction. On save, the notice is attached to the matching client by GSTIN — a client is created on the spot if it is new. |
| **Cases Overview** | Every client and notice, with the demand break-up (tax / interest / penalty), the reply deadline, and the issues raised. |
| **Side-by-Side Analysis** | The extracted notice metadata and the issue-by-issue breakdown shown next to the original document. Every figure is editable so the CA can correct and mark the extraction as verified. |
| **Document Tracker** | A checklist — generated automatically from the notice's issues — of the records to obtain from the client, with status tracking, per-issue tagging, and Excel / CSV import & export (auto-maps a firm's own tracker columns). |
| **Client Discussion** | A discussion log per notice, pre-seeded with a briefing entry and the specific questions to ask the client for each issue; entries can be marked resolved and carry follow-up dates. |
| **Reply & Email Studio** | A ready-to-file legal reply in **Microsoft Word (.docx)** on the firm letterhead, plus structured client **document-request** and **follow-up** emails that open in the mail app. |
| **Statutory Deadlines** | A reply-window and personal-hearing radar across all clients. |
| **GST Law & Notice Guide** | Built-in reference — CBIC Circular 183/2022 & 193/2023 on ITC-mismatch defence, the extraction workflow, and the data-privacy model. |

---

## Set up the backend

**You must do this before the app will run** — it needs a Supabase project (free tier).

Follow **[`SUPABASE-SETUP.md`](./SUPABASE-SETUP.md)** step by step:

1. Create a free Supabase project.
2. Run `supabase/schema.sql` in the Supabase SQL editor.
3. Put `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `.env.local`.
4. (optional) Deploy the `extract-notice` Edge Function for one-click AI extraction.

## Running it

**Requirements:** [Node.js 18 or newer](https://nodejs.org/).

```bash
npm install
cp .env.example .env.local     # then fill in your Supabase URL + anon key
npm run dev
```

Open the URL it prints (**http://localhost:5180**) in Chrome or Edge.

On Windows you can instead double-click **`Start-App.bat`** (run `npm install` once first).

### Production build

```bash
npm run build      # output: dist/
npm run preview    # serve the built app
```

### First use

1. **Create an account**, then **create a firm** (you become its owner).
2. **Add client** — legal name + 15-digit GSTIN.
3. **Add Notice** → *Use Claude.ai* → upload the PDF or paste the notice text →
   *Copy prompt for Claude.ai* → run it in claude.ai → paste the reply back →
   *Load pasted result* → *Save to client record*.
4. Review under **Side-by-Side Analysis**; work the **Document Tracker** and
   **Client Discussion**; generate the reply under **Reply & Email Studio**.

Any GST notice PDF works for a trial run, or paste a short notice extract as text.

---

## Data privacy

- Client data — GSTINs, notices, document trackers, discussion logs — is stored in a
  Supabase Postgres database, scoped per firm by Row-Level Security. A firm can only
  ever read or write its own rows.
- Notice content leaves the machine **only when the CA explicitly chooses** to send it
  to Claude for extraction — either by pasting it into claude.ai themselves, or via
  server-side extraction if the firm has configured it.

---

## Tech stack

| | |
|---|---|
| Language | TypeScript |
| UI | React 19 + Vite 6 |
| Styling | Tailwind CSS 4 |
| Backend | Supabase (Postgres + Auth, Row-Level Security) |
| Document output | `docx` (Word), `xlsx` (Excel), `file-saver` |
| Icons | `lucide-react` |
| AI extraction | Anthropic Claude — server-side Edge Function, or manual copy-paste from claude.ai |

---

## Project structure

```
GST-Notice-Analyser-Capstone/
├── index.html                     app entry
├── package.json                   scripts & dependencies
├── vite.config.ts                 Vite + React + Tailwind config
├── tsconfig.json                  TypeScript config
├── Start-App.bat                  Windows launcher
├── SUPABASE-SETUP.md              backend setup runbook
├── supabase/
│   ├── schema.sql                 tables, firms/members, RLS policies
│   └── functions/extract-notice/  Edge Function (server-side Claude call)
└── src/
    ├── App.tsx                     session/firm gate, tab routing
    ├── config.ts                   module configuration
    ├── lib/supabase.ts             Supabase client
    ├── main.tsx  ·  index.css
    ├── components/                 AuthScreen, Header, Sidebar, modals, PDF viewer
    ├── pages/                      one file per module screen
    ├── services/
    │   ├── aiService.ts            notice extraction (Edge Function + manual paste)
    │   ├── db.ts                   all reads/writes (Supabase) + auth + firms
    │   ├── documentGenerator.ts    Word (.docx) reply + email drafting
    │   ├── noticeArtifacts.ts      fan-out of a saved notice into the other tabs
    │   ├── discussions.ts          client-discussion log
    │   └── excelMapperEngine.ts    Excel / CSV import for the document tracker
    └── types/index.ts              shared TypeScript models
```

---

*Submitted to https://github.com/aiinicai/AICA-Level-2-Projects*
