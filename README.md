# AutoContract2Tally — offline desktop app

This packages the AICA capstone pipeline (broker contract note → Tally
voucher) — the same functionality described on the AI Studio demo page
(`autocontract2tally-broker-contract-note-to-tally.ai.studio`) — into a
single Windows `.exe` that runs entirely on your own machine.

**What runs where:**
- Stage A — "Fetch from Gmail" — is the only part that touches the
  internet. It downloads broker contract-note PDF attachments (Zerodha,
  Angel One, Upstox) into a local watch folder.
- Stage B — parsing the PDF, building the Tally journal voucher, and
  posting it — is fully offline. It only talks to `localhost:9000`,
  TallyPrime's own XML/HTTP gateway running on the same PC.

## Folder contents

```
AutoContract2Tally/
  app.py                     Flask app + local dashboard (http://127.0.0.1:8765)
  templates/index.html       The dashboard UI
  parsers/broker_parsers.py  Contract-note text/PDF -> normalized trade dict
  accounting_engine/         Normalized trades -> Tally journal voucher (Dr=Cr)
  automation/watch_and_post.py   Folder scan -> parse -> post (idempotent)
  gmail_fetch/gmail_fetcher.py   Gmail -> watch folder (Stage A)
  requirements.txt
  build_exe.bat              One-click builder (run this on Windows)
```

## Important — please verify before relying on this for real filings

`parsers/broker_parsers.py` and `accounting_engine/accounting_engine.py`
in this package are a **consolidated rebuild** based on the project's own
progress notes, because only `watch_and_post.py` was found in the
connected `Capstone Project` folder — the parser and accounting-engine
modules referenced by it weren't present there. The Zerodha PDF parsing
logic and voucher-splitting rules (Speculation / Equity / Futures /
Options, GST pure-agent treatment of STT & stamp duty) follow what's
documented in the project log, but **you should re-run this against the
same test PDF you validated earlier** (`zerodha_realistic_test_note.pdf`)
and compare the output voucher to the one you'd previously confirmed
balances at ₹12,66,508.10, before posting anything real. If you still
have the original `parsers/` and `accounting_engine/` files from earlier
chat rounds, drop them into this folder in place of these to be safe.

Angel One and Upstox parsers still use an invented plain-text format —
this was already flagged as unverified in the project log and remains
so; don't rely on them until you have real sample notes from those
brokers.

## Building the .exe (one time, on Windows)

1. Make sure Python 3.10+ is installed (python.org) and on PATH.
2. Double-click `build_exe.bat` in this folder. It creates a virtual
   environment, installs dependencies, and runs PyInstaller.
3. The finished app appears at `dist\AutoContract2Tally.exe` — a single
   file. Copy it anywhere (Desktop, a USB stick, another PC) and
   double-click it to run; no install needed. It opens your browser to
   `http://127.0.0.1:8765` automatically.

Rebuilding after any code change: just re-run `build_exe.bat`.

## One-time Gmail API setup (for Stage A)

This step needs your own Google account and can't be done on your
behalf — Google requires you to create the OAuth client yourself:

1. Go to https://console.cloud.google.com/ → create/select a project →
   enable the **Gmail API** (APIs & Services → Library).
2. APIs & Services → Credentials → **Create Credentials → OAuth client
   ID** → Application type **Desktop app**.
3. Download the JSON. Rename it `credentials.json`.
4. Place it in `%LOCALAPPDATA%\AutoContract2Tally\credentials.json`
   (the app creates this folder the first time you run it — run the app
   once, then copy the file in).
5. Click **"Fetch new contract notes"** in the app. A browser tab opens
   for Google sign-in and consent (read-only Gmail access only — nothing
   is sent, deleted, or modified). After the first successful sign-in, a
   `token.json` is cached in the same folder so future fetches are
   silent.

## TallyPrime gateway

In TallyPrime: **F1 (Help) → Settings → Connectivity** → enable the
**ODBC/XML port**, default `9000`. The app posts to
`http://localhost:9000` by default — change it in the dashboard's
Settings card if your Tally uses a different port. Per the project's
outstanding items, this hasn't yet been tested against a live Tally
instance (Tally wasn't reachable at localhost:9000 in any prior test
session) — please do a **Dry run** first, and a small real test voucher
before trusting it with a full day's contract notes.

## Running without building an .exe

`pip install -r requirements.txt` then `python app.py` — works
identically to the packaged .exe, useful while you're still checking the
parser/accounting output against known-good figures.
