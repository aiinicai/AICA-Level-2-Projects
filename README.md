# GST Inward HSN/SAC Fetcher — V1

Desktop app that reads a downloaded NIC e-invoice "Received" JSON export and
produces an HSN-wise Excel report. Runs fully offline — no data leaves the
machine.

## What's built in this version (V1)

- **Home** — Manual upload of a downloaded e-invoice JSON. Decodes every
  record's embedded signed invoice, extracts HSN-level line items, stores
  them locally (SQLite), and is ready to export.
  "Fetch from portal" tile is present but disabled — that's the V2
  auto-download feature, not built yet.
- **Reports** — Pick a From/To month range (and optionally a GSTIN) and
  generate a consolidated 3-sheet Excel (Invoice Summary / HSN Item Detail /
  HSN Summary). Keeps a running list of past exports.
- **Settings** — Register the GSTINs you work with, and choose the folder
  where generated Excel reports are saved.

Data accumulates month-on-month in a local database
(`%APPDATA%\GSTInwardHSNFetcher\data.db`), so re-running the app next month
adds to what's already there rather than starting over. Re-uploading the same
JSON is safe — invoices are keyed by IRN, so nothing gets duplicated.

## Before you build — one-time setup on your Windows machine

You need Python 3.10+ installed. If DGFT AutoComply's build environment is
still on this machine, you likely already have everything needed.

```
cd GSTInwardFetcher
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Test it first (without building the exe)

```
python main.py
```

A window should open with the app. Try uploading a real e-invoice JSON and
confirm a report generates into your chosen folder before you build the exe —
much faster to catch issues here than after packaging.

## Build the .exe

```
pyinstaller build.spec
```

The finished file appears at:

```
dist\GST Inward HSN-SAC Fetcher.exe
```

This is a single portable file — the whole app, nothing else to carry
alongside it.

## Getting the .exe onto your office laptop via GitHub

1. Create a repository on GitHub (private, since this is your own tool) —
   e.g. `gst-inward-hsn-fetcher`.
2. Push the source code (main.py, backend.py, ui.html, etc.) — do **not**
   commit the built .exe into the repo itself (GitHub's normal file-size
   limits are much stricter than Release assets).
3. On GitHub, go to the repo → **Releases** → **Draft a new release** →
   attach `GST Inward HSN-SAC Fetcher.exe` as a release asset → publish.
4. On your office laptop, open the Release page in the browser and click
   the .exe link to download — this is a plain HTTPS download from
   github.com, which should go through even if other file-transfer routes
   are blocked.

## Known limitation to mention in the demo

The uploaded JSON file needs to be the **"Received" download** from
`einvoice.gst.gov.in` (Services → e-Invoice → Download e-Invoice →
Received tab). It reads the array of records with the `SignedInvoice`
field per record — the format we tested this against.
