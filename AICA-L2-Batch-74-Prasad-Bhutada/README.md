# CA Docs — Document Automation System

A LAN-deployed document automation system for a Chartered Accountant office: eliminates copy-paste template editing by generating client-specific Word/PDF documents from managed templates with `#Placeholder#` fields, formatting fully preserved.

## Project status

This is a **working foundation**, not a finished multi-week enterprise build compressed into one session — that scope (12 modules, full test coverage, polished UI for every screen, manuals) is realistically weeks of work. What's here has been **built and verified**, not just written:

**Built, tested, and confirmed working:**
- Full normalized SQLite schema (Prisma) covering every module in the spec
- Placeholder detection engine — verified against real .docx files to correctly find placeholders in body text, tables, headers, and footers, with correct dedup
- Formatting-preserving generation engine (docxtemplater) — verified via actual LibreOffice-rendered output that bold/italic/underline/color/highlight/table formatting all survive replacement unchanged
- Image placeholder support (Signature/Logo/Photograph) — found and fixed a real integration bug where the third-party image module required non-spec `%tag` syntax; fixed with a custom parser hook and re-verified visually
- PDF conversion via LibreOffice headless
- Master templates confirmed never mutated (checksum-verified before/after generation)
- Full REST API for all 12 modules (see `docs/API_REFERENCE.md`)
- React frontend: three-panel Template Manager, generation wizard, clients, history, settings
- 17 passing automated unit tests covering the detection/generation/validation engines (`npm test`)
- Both backend and frontend build cleanly with zero TypeScript errors

**Implemented but not yet run through live end-to-end testing:**
- Client bulk Excel import/export
- Backup/restore
- Placeholder-to-Client-Master mapping UI flow
- Category management UI

**Not yet done:**
- Polished visual design pass (current UI is functional/clean but plain — see `frontend-design` conventions for a follow-up pass)
- Configurable validation rules via the Settings UI (rules currently live in `validators.ts`; wiring them to the `Setting` table is a small, well-scoped follow-up)
- SmartArt placeholder detection (documented limitation — see `docs/ARCHITECTURE.md`)
- Load/concurrency testing under real multi-user LAN conditions

## Quick start (no command line needed)

1. Install **Node.js** — download the "LTS" version for Windows from https://nodejs.org and run the installer with default options. (This is the one unavoidable technical step — CA Docs runs on top of it. You only do this once.)
2. Double-click **`setup.bat`** in this folder. It installs everything and builds the app — this takes a few minutes and only needs to be run once (or again after an update).
3. Double-click **`start.bat`** to run CA Docs. Your browser will open automatically to `http://localhost:4000`.

That's it — one program, one address, nothing to configure. To make CA Docs start automatically with Windows, see "Run CA Docs automatically" in `docs/INSTALLATION.md`.

If anything goes wrong, `setup.bat` prints a clear message about what to fix — see the Troubleshooting section below, or `docs/INSTALLATION.md` for a step-by-step manual walkthrough of exactly what the scripts do, useful if someone technical needs to help you.


## Documentation

| Doc | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | Stack choices, rationale, data model, known limitations |
| `docs/INSTALLATION.md` | First-time setup on a Windows PC |
| `docs/DEPLOYMENT.md` | Running as an always-on Windows LAN service |
| `docs/API_REFERENCE.md` | REST endpoint reference |
| `docs/USER_MANUAL.md` | Daily staff usage (no login needed) |
| `docs/ADMIN_MANUAL.md` | Template management, settings, backup (password protected) |

## Troubleshooting

**Blank white page (browser tab shows "CA Docs" but nothing renders):** as of this version, the frontend and backend are served by the same program on the same address (`http://localhost:4000`), which removes the most common cause of this (a frontend that can't find its backend). If you still see this, hard-refresh with **Ctrl+Shift+R**, and check the "CA Docs - server" window for red error text.

**`setup.bat` says Node.js was not found, or the version is too old:** install Node.js 20 LTS from nodejs.org (see Quick Start above), restart your computer, then run `setup.bat` again.

**Nothing happens when I double-click `start.bat`:** right-click it → "Run as administrator" once, in case Windows is blocking script execution silently. If a security prompt (SmartScreen) appears, choose "More info" → "Run anyway" — this is expected for a locally-built application without a paid code-signing certificate.

## Testing

```bash
cd backend
npm test
```
17 unit tests cover placeholder detection, formatting-preserving generation (including image embedding and line-break stripping), and validation rules. An integration test (`integration.test.ts`) exercises the API/DB layer against a throwaway SQLite database — it requires a working internet connection during `npx prisma db push` to fetch Prisma's query engine binary the first time (standard for any Prisma project; not an issue on a normal office internet connection).

## Continuing this build

The highest-value next steps, in order:
1. Live-test client Excel import/export and backup/restore against real files.
2. Wire configurable validation patterns into Settings.
3. A visual design pass on the frontend (typography, spacing, empty states, loading states).
4. Multi-user concurrency testing (several browsers hitting the same backend simultaneously while generating documents).
5. Package an installer/setup script that automates `docs/INSTALLATION.md` end-to-end.

Happy to keep building any of these out.
