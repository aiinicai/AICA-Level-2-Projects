# WhatsApp Cleaner — H.D.Nakarani & Associates

A Windows desktop tool that clears **message history** from WhatsApp chats in
bulk, exports chat history, and never deletes a group.

Built with Python + Playwright (UI automation against WhatsApp Web in Microsoft
Edge) and a pywebview HTML frontend.

---

## Features

- **Bulk history clearing** across many chats in one run
- **Five cleanup modes**
  - All history
  - Newest N messages
  - Oldest N (of what is currently loaded — fast)
  - Oldest N (scrolls to the true top of history first — slower, exact)
  - Older than a chosen date
- **Clear + delete thread** for individual chats only (groups are always skipped)
- **Export chat** with or without media, to a folder you choose
- **Group / Individual filtering**, with an accurate "Verify types" pass that
  checks each chat's own menu
- **Search, sort, select-all**, live counts
- Modern dashboard UI (glassmorphism, metric tiles, activity log)

---

## Safety design

This tool is deliberately built so it **cannot** delete a group.

1. **`FORBIDDEN` list + `safe_click()`** — every click reads the element's text
   first and refuses if it matches `exit group`, `delete group`, `leave group`,
   or `delete for everyone`.
2. **Groups-only verification** — before clearing, the chat's own menu is opened
   and must show group markers (`Exit group` / `Group info` / `Add member`).
   Personal chats are skipped.
3. **JSON backup** written to `exports/` before every clear.
4. **Audit log** appended to `audit.log`.
5. **Explicit confirmation dialog** before any destructive run.
6. **Cancel button** stops cleanly after the current chat.
7. **Deliberate pacing** — 1.2 s between UI actions, 4 s between chats, to stay
   at human speed.

The "Clear + delete thread" mode is the single exception that removes a chat
thread, and it hard-checks that the chat is an individual before proceeding.

---

## Requirements

- Windows 10/11
- Microsoft Edge (used via `channel="msedge"` — no browser is bundled)
- Microsoft Edge WebView2 Runtime (usually preinstalled on Windows 11)
- Python 3.11+ (only if running from source)

---

## Install (from source)

```bash
pip install playwright pywebview
python wa_cleaner.py
```

No `playwright install` step is needed — the tool drives the system Edge.

On first run, scan the QR code shown in the Edge window. The session is cached
in `wa-profile/` so later runs skip the QR.

---

## Build a standalone EXE

```bash
build_exe.bat
```

Output lands at `dist\wa_cleaner\wa_cleaner.exe`. The script backs up
`wa-profile/`, `exports/`, `audit.log`, and `presets.json` before the build and
restores them afterwards, because PyInstaller wipes `dist\wa_cleaner\` during
its COLLECT step.

The whole `dist\wa_cleaner\` folder is portable — copy it to any Windows machine
that has Edge.

---

## Files

| File | Purpose |
|---|---|
| `wa_cleaner.py` | The tool — Playwright worker + pywebview HTML UI |
| `wa.py` | CLI diagnostics — `inspect`, `probe-menu` |
| `probe_list.py` | Diagnostic for chat-list sidebar selectors |
| `build_exe.bat` | PyInstaller build with session backup/restore |

### Not in this repository (intentionally)

- `wa-profile/` — **live WhatsApp session, treated as a credential**
- `exports/` — JSON snapshots of real messages
- `audit.log`, `presets.json` — contain real chat names
- `dist/`, `build/` — regenerable build output

---

## Known limitations

- **Clearing is local only.** It clears for you and your linked devices. Other
  participants keep their own copies. This is WhatsApp's behaviour, not a bug.
- **Selectors drift.** When WhatsApp redesigns its web client, the selectors in
  `MESSAGE_SELECTORS` and `LABELS` at the top of `wa_cleaner.py` may need
  updating. The diagnostic scripts help find replacements.
- **"Oldest N (of loaded)" is approximate** — it works on what is currently
  rendered. Use "Oldest N (from top)" for an exact result.
- **Group/individual detection** falls back to a heuristic when WhatsApp's DOM
  markers are absent. Run "Verify types" for accurate classification.

---

## Terms of service

Automating the personal WhatsApp client is against WhatsApp's Terms of Service.
Ban risk is low when reading and clearing at human pace, but it is not zero.
Use your own number only.

This is a personal utility, provided as-is, with no warranty.
