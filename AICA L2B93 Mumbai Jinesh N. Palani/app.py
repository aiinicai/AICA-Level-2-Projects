"""
AutoContract2Tally - offline desktop app.

A local web dashboard (served on http://127.0.0.1:8765) that ties
together the capstone pipeline:

  Stage A (needs internet): Gmail -> watch folder      (gmail_fetch)
  Stage B (fully offline) : watch folder -> parse -> Tally  (automation)

Run directly with `python app.py`, or as the packaged AutoContract2Tally.exe
(see build_exe.bat). On launch it opens the dashboard in the default
browser automatically.
"""
import json
import os
import re
import shutil
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "parsers"))
sys.path.insert(0, str(BASE_DIR / "accounting_engine"))
sys.path.insert(0, str(BASE_DIR / "automation"))
sys.path.insert(0, str(BASE_DIR / "gmail_fetch"))

import watch_and_post  # noqa: E402

app = Flask(__name__)

# Per-user writable config/settings location (works both as a script and
# when frozen into a onefile .exe, where BASE_DIR is a temp extraction dir).
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AutoContract2Tally"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = CONFIG_DIR / "settings.json"
LAST_RUN_PATH = CONFIG_DIR / "last_run.json"
os.environ.setdefault("AUTOCONTRACT2TALLY_CONFIG", str(CONFIG_DIR))

DEFAULT_SETTINGS = {"watch_folder": str(Path.home() / "AutoContract2Tally" / "ContractNotes"),
                     "tally_gateway_url": "http://localhost:9000",
                     "tally_company": "",
                     "gmail_filter_strategy": "broker_only",
                     "gmail_client_emails": "",
                     "gmail_label": "",
                     "gmail_search_days": 0,
                     "pdf_passwords": ""}


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_PATH.read_text())}
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


_ILLEGAL_FOLDER_CHARS = re.compile(r'[<>:"/\\|?*]')


def _sanitize_folder_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "Default Client"
    return _ILLEGAL_FOLDER_CHARS.sub("_", name)


def _migrate_legacy_root_into_client_folder(root: Path, client_folder: Path) -> None:
    """One-time, safe migration: earlier versions of this app saved every
    client's notes directly in the configured watch folder, with no
    per-client subfolders -- once multiple clients share one practice,
    that mixes everyone's files together. If this client's folder hasn't
    been used yet, move any loose pending files plus the existing
    processed/errors history and logs from the old root into it, so nothing
    already downloaded or already processed gets stranded when switching to
    per-client folders. Only ever runs once per client folder (it does
    nothing once that folder has anything in it), so it's safe to call on
    every request."""
    if client_folder.exists() and any(client_folder.iterdir()):
        return
    if not root.exists():
        return
    client_folder.mkdir(parents=True, exist_ok=True)
    for name in (".processed_log.json", ".gmail_fetch_log.json"):
        src = root / name
        if src.exists():
            shutil.move(str(src), str(client_folder / name))
    for sub in ("processed", "errors"):
        src = root / sub
        if src.exists() and src.is_dir():
            shutil.move(str(src), str(client_folder / sub))
    for p in list(root.iterdir()):
        if p.is_file() and p.suffix.lower() in (".pdf", ".txt"):
            shutil.move(str(p), str(client_folder / p.name))


def client_folder(settings: dict) -> Path:
    """Every client's notes live in their own subfolder, named after the
    Tally company configured in Settings, inside the shared parent 'Watch
    folder' -- so switching clients (changing the company name) never mixes
    one client's contract notes, logs, or processed/errors history with
    another's.

    Supports both ways of using the Watch folder setting: pointing it at
    one shared parent folder (e.g. "...\\Contract Notes") that every
    client's subfolder lives inside, OR pointing it directly at a
    folder already dedicated to one client (e.g.
    "...\\Contract Notes\\PALBRO TRADE") chosen by hand each time. If the
    Watch folder's own name already matches the configured company, it's
    used as-is rather than nesting another same-named subfolder inside
    itself -- without this, a Watch folder already named after the company
    would silently end up as ".../PALBRO TRADE/PALBRO TRADE", and any file
    someone can actually see sitting in the single-level folder would never
    be found by Gmail fetch or Run pipeline (both of which only ever look
    inside the doubly-nested one)."""
    root = Path(settings["watch_folder"])
    company_name = _sanitize_folder_name(settings.get("tally_company"))
    if root.name == company_name:
        return root
    folder = root / company_name
    _migrate_legacy_root_into_client_folder(root, folder)
    return folder


@app.route("/")
def index():
    return render_template("index.html", settings=load_settings())


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        settings = load_settings()
        settings.update(request.json or {})
        save_settings(settings)
        client_folder(settings).mkdir(parents=True, exist_ok=True)
        return jsonify(settings)
    return jsonify(load_settings())


@app.route("/api/fetch-gmail", methods=["POST"])
def api_fetch_gmail():
    """Stage A: needs internet. Fails cleanly (with a clear message) if
    credentials.json hasn't been set up yet, or if there's no network."""
    settings = load_settings()
    try:
        import gmail_fetcher
        query = gmail_fetcher.build_query(settings)
        result = gmail_fetcher.fetch_contract_notes(str(client_folder(settings)), query=query)
        result["query_used"] = query
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/gmail-query-preview")
def api_gmail_query_preview():
    """Builds the Gmail search query from current settings without needing
    an authorized session -- lets the dashboard show a live preview of the
    query even before credentials.json / sign-in is done."""
    import gmail_fetcher
    settings = load_settings()
    return jsonify({"query": gmail_fetcher.build_query(settings)})


@app.route("/api/gmail-labels")
def api_gmail_labels():
    """Real Gmail API call -- requires credentials.json and a completed
    sign-in (a token.json). Returns the user's own labels so they can pick
    one instead of typing an exact label name from memory."""
    import gmail_fetcher
    try:
        return jsonify({"ok": True, "labels": gmail_fetcher.list_labels()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/run-pipeline", methods=["POST"])
def api_run_pipeline():
    """Stage B: fully offline. dry_run=true parses and builds vouchers
    without posting to Tally or moving files -- safe to try first."""
    settings = load_settings()
    dry_run = bool((request.json or {}).get("dry_run", False))
    watch_and_post.TALLY_GATEWAY_URL = settings.get("tally_gateway_url", "http://localhost:9000")
    watch_and_post.TALLY_COMPANY = settings.get("tally_company", "")
    watch_and_post.PDF_PASSWORDS = [p.strip() for p in (settings.get("pdf_passwords") or "").split(",") if p.strip()]
    try:
        folder = client_folder(settings)
        folder.mkdir(parents=True, exist_ok=True)
        result = watch_and_post.run(str(folder), dry_run=dry_run)
        if result.get("details"):
            existing = json.loads(LAST_RUN_PATH.read_text()) if LAST_RUN_PATH.exists() else []
            # keep the 10 most recent parsed notes (newest first) for the dashboard's
            # Broker Parser / Tally Accounting step views
            combined = result["details"] + existing
            LAST_RUN_PATH.write_text(json.dumps(combined[:10], indent=2))
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/last-run")
def api_last_run():
    details = json.loads(LAST_RUN_PATH.read_text()) if LAST_RUN_PATH.exists() else []
    return jsonify({"details": details})


@app.route("/api/gmail-status")
def api_gmail_status():
    creds_path = CONFIG_DIR / "credentials.json"
    token_path = CONFIG_DIR / "token.json"
    return jsonify({
        "credentials_configured": creds_path.exists(),
        "signed_in": token_path.exists(),
        "credentials_path": str(creds_path),
    })


@app.route("/api/gmail-whoami")
def api_gmail_whoami():
    """Real (lightweight) Gmail API call -- only made on demand, e.g. right
    after the dashboard sees signed_in=true, never on a polling loop."""
    import gmail_fetcher
    try:
        return jsonify({"ok": True, "email": gmail_fetcher.whoami()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/gmail-signout", methods=["POST"])
def api_gmail_signout():
    """Removes the cached account sign-in (token.json) only -- the OAuth
    client itself (credentials.json, the one-time Google Cloud setup) is
    left in place. The next fetch / label lookup will run through Google's
    sign-in flow again with the account chooser, so a different Google
    account can be picked."""
    import gmail_fetcher
    removed = gmail_fetcher.sign_out()
    return jsonify({"ok": True, "removed": removed})


@app.route("/api/retry-errors", methods=["POST"])
def api_retry_errors():
    """Moves every file out of watch_folder/errors back into the watch
    folder root so it gets picked up on the next Dry run / Post to Tally.
    A file only lands in errors/ because something about it failed (wrong
    or missing PDF password, unrecognized broker letterhead, etc) -- once
    that's fixed (e.g. the password is added in Settings), the file itself
    doesn't move on its own, so this is the "try it again" button."""
    settings = load_settings()
    watch_dir = client_folder(settings)
    error_dir = watch_dir / "errors"
    moved = []
    if error_dir.exists():
        for p in sorted(error_dir.iterdir()):
            if not p.is_file():
                continue
            dest = watch_dir / p.name
            if dest.exists():
                stem, dot, ext = p.name.rpartition(".")
                dest = watch_dir / (f"{stem}_retry.{ext}" if dot else f"{p.name}_retry")
            shutil.move(str(p), str(dest))
            moved.append(dest.name)
    return jsonify({"ok": True, "moved": moved})


@app.route("/api/status")
def api_status():
    settings = load_settings()
    watch_dir = client_folder(settings)
    pending = sorted(p.name for p in watch_dir.glob("*") if p.is_file() and p.suffix.lower() in (".pdf", ".txt")) \
        if watch_dir.exists() else []
    processed = sorted(p.name for p in (watch_dir / "processed").glob("*")) if (watch_dir / "processed").exists() else []
    errors = sorted(p.name for p in (watch_dir / "errors").glob("*")) if (watch_dir / "errors").exists() else []
    log_path = watch_dir / ".processed_log.json"
    recent = list(json.loads(log_path.read_text()).values())[-10:] if log_path.exists() else []
    return jsonify({"pending": pending, "processed": processed, "errors": errors, "recent": recent,
                     "watch_folder": str(watch_dir)})


def _open_browser():
    webbrowser.open("http://127.0.0.1:8765")


if __name__ == "__main__":
    threading.Timer(1.0, _open_browser).start()
    app.run(host="127.0.0.1", port=8765, debug=False)
