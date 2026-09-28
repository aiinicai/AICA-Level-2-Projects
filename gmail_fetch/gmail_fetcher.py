"""
Stage A of the pipeline: Gmail -> local watch folder.

Downloads PDF attachments from known broker sender addresses (Zerodha,
Angel One, Upstox contract-note emails) into the local watch folder that
automation/watch_and_post.py scans. This is the only part of the app that
needs the internet; everything downstream (parsing, voucher building,
posting to Tally) runs fully offline against localhost.

One-time setup (the user must do this themselves -- it needs their own
Google account and cannot be done on their behalf):
  1. Go to https://console.cloud.google.com/ , create a project (or reuse
     one), enable the "Gmail API".
  2. Under "APIs & Services -> Credentials", create an OAuth Client ID of
     type "Desktop app". Download the JSON and save it next to this
     script (or wherever this app's config points) as `credentials.json`.
  3. Run this script (or click "Fetch from Gmail" in the app) once -- a
     browser tab opens for Google sign-in and consent. A `token.json` is
     then cached alongside `credentials.json` so future runs are silent.

Only read-only Gmail access (gmail.readonly scope) is requested; nothing
is sent, deleted, or modified in the mailbox.
"""
from __future__ import annotations
import base64
import json
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

BROKER_SENDERS = ["contractnotes@zerodha.com", "*@angelone.in", "*@upstox.com"]

BROKER_SENDER_QUERY = (
    '(from:contractnotes@zerodha.com OR from:*@angelone.in OR from:*@upstox.com) '
    'has:attachment filename:pdf'
)


def build_query(settings: dict) -> str:
    """Build the Gmail search query from the dashboard's Gmail Filter &
    Watcher Settings. Broker attribution itself still happens downstream
    in Stage B (broker_parsers.detect_broker_from_text, from the note's own
    letterhead) -- this query's only job is deciding which *emails* Stage A
    should even look at, which matters when a client forwards their own
    contract note from a personal address rather than the broker emailing
    the practice directly.

    strategy:
      "broker_only"      -- only the known broker sender addresses (default)
      "client_forwards"  -- only the configured client/forwarder addresses
      "all"              -- broker addresses OR client/forwarder addresses
      "by_label"         -- a Gmail label the user already files these under,
                            ignoring sender entirely

    gmail_search_days: 0 (or missing) searches the full inbox with no date
    limit; a positive integer N restricts to messages newer than N days
    (Gmail's own `newer_than:Nd` operator), which is both faster and less
    likely to re-surface long-settled correspondence on a big mailbox.
    """
    strategy = (settings.get("gmail_filter_strategy") or "broker_only").strip()
    client_emails = [e.strip() for e in (settings.get("gmail_client_emails") or "").split(",") if e.strip()]
    label = (settings.get("gmail_label") or "").strip()

    broker_clause = "(" + " OR ".join(f"from:{s}" for s in BROKER_SENDERS) + ")"
    client_clause = "(" + " OR ".join(f"from:{e}" for e in client_emails) + ")" if client_emails else None

    if strategy == "by_label" and label:
        base = f'label:{label} has:attachment filename:pdf'
    elif strategy == "client_forwards" and client_clause:
        base = f'{client_clause} has:attachment filename:pdf'
    elif strategy == "all":
        clauses = [broker_clause] + ([client_clause] if client_clause else [])
        base = "(" + " OR ".join(c.strip("()") for c in clauses) + ") has:attachment filename:pdf"
    else:
        # fall back to broker-only (also covers "broker_only" and any unrecognized/empty strategy)
        base = BROKER_SENDER_QUERY

    try:
        days = int(settings.get("gmail_search_days") or 0)
    except (TypeError, ValueError):
        days = 0
    if days > 0:
        base = f"{base} newer_than:{days}d"
    return base


def list_labels() -> list[dict]:
    """Real Gmail API call (needs an already-authorized session) so the
    dashboard's "Fetch My Gmail Labels" button shows the user's own labels
    instead of them having to guess/type the exact name."""
    service = get_gmail_service()
    resp = service.users().labels().list(userId="me").execute()
    labels = resp.get("labels", [])
    # user-created labels only (skip Gmail's built-in system labels like INBOX/SENT/SPAM)
    return sorted(
        [{"id": l["id"], "name": l["name"]} for l in labels if l.get("type") == "user"],
        key=lambda l: l["name"].lower(),
    )


def _config_dir() -> Path:
    """Where credentials.json / token.json live -- next to this script by
    default, overridable via AUTOCONTRACT2TALLY_CONFIG env var (set by the
    packaged .exe to a writable per-user folder)."""
    import os
    override = os.environ.get("AUTOCONTRACT2TALLY_CONFIG")
    return Path(override) if override else Path(__file__).parent


def sign_out() -> bool:
    """Deletes the cached token.json (the *account* sign-in), leaving
    credentials.json (the OAuth *client*, one-time Google Cloud setup)
    untouched. The next fetch or "Fetch my Gmail labels" call then runs
    through Google's sign-in flow again with prompt=select_account, so a
    different Google account can be chosen. Returns True if a token
    actually existed and was removed."""
    token_path = _config_dir() / "token.json"
    if token_path.exists():
        token_path.unlink()
        return True
    return False


def whoami() -> str:
    """The email address of whichever Google account the cached token
    belongs to, so the dashboard can show it. Returns '' if not signed in."""
    from google.oauth2.credentials import Credentials
    token_path = _config_dir() / "token.json"
    if not token_path.exists():
        return ""
    try:
        data = json.loads(token_path.read_text())
        # google-auth-oauthlib doesn't always persist the email in token.json;
        # fall back to an actual (cheap) API call when it isn't present.
        if data.get("account"):
            return data["account"]
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        return ""


def get_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    config_dir = _config_dir()
    creds_path = config_dir / "credentials.json"
    token_path = config_dir / "token.json"

    if not creds_path.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {creds_path}. Follow the one-time "
            "Gmail API setup steps in this file's docstring / the app README."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            # prompt=select_account: after sign_out() removes token.json, this
            # makes Google show the account chooser instead of silently
            # reusing whatever Google account is already active in the
            # browser, so switching accounts actually works.
            creds = flow.run_local_server(port=0, prompt="select_account")
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _header(msg: dict, name: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def fetch_contract_notes(watch_folder: str, query: str = BROKER_SENDER_QUERY, max_results: int = 25) -> dict:
    """Search Gmail for broker contract-note emails with PDF attachments
    not yet downloaded, and save each new attachment into watch_folder.
    Downloaded message IDs are recorded in .gmail_fetch_log.json inside
    watch_folder so re-running never re-downloads the same attachment.

    Also returns diagnostics (messages_found, and -- for any matched
    message that had no PDF actually extracted -- its subject/sender and
    every attachment filename it did carry) so a "downloaded 0" run is
    debuggable from the dashboard instead of a dead end: it tells you
    whether the search matched nothing at all (wrong address/label) or
    matched a message whose attachment wasn't recognised as a PDF."""
    watch_dir = Path(watch_folder)
    watch_dir.mkdir(parents=True, exist_ok=True)
    log_path = watch_dir / ".gmail_fetch_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}

    service = get_gmail_service()
    results = {"downloaded": [], "skipped_messages": 0, "errors": [],
               "messages_found": 0, "no_pdf_found": []}

    resp = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = resp.get("messages", [])
    results["messages_found"] = len(messages)

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        if msg_id in log:
            results["skipped_messages"] += 1
            continue
        try:
            msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            saved_any = False
            all_attachment_names = []
            for part in _walk_parts(msg.get("payload", {})):
                filename = part.get("filename", "")
                body = part.get("body", {})
                if filename:
                    all_attachment_names.append(filename)
                if not filename.lower().endswith(".pdf") or "attachmentId" not in body:
                    continue
                att_id = body["attachmentId"]
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=att_id
                ).execute()
                data = base64.urlsafe_b64decode(att["data"])
                out_path = watch_dir / _unique_name(watch_dir, filename)
                out_path.write_bytes(data)
                results["downloaded"].append(out_path.name)
                saved_any = True
            if not saved_any:
                results["no_pdf_found"].append({
                    "message_id": msg_id,
                    "subject": _header(msg, "Subject"),
                    "from": _header(msg, "From"),
                    "attachments_seen": all_attachment_names,
                })
            log[msg_id] = {"saved": saved_any}
        except Exception as e:
            results["errors"].append({"message_id": msg_id, "error": str(e)})

    log_path.write_text(json.dumps(log, indent=2))
    return results


def _walk_parts(payload: dict):
    parts = payload.get("parts")
    if parts:
        for p in parts:
            yield from _walk_parts(p)
    else:
        yield payload


def _unique_name(folder: Path, filename: str) -> str:
    candidate = filename
    i = 1
    while (folder / candidate).exists():
        stem, dot, ext = filename.rpartition(".")
        candidate = f"{stem}_{i}.{ext}" if dot else f"{filename}_{i}"
        i += 1
    return candidate


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Fetch broker contract-note PDF attachments from Gmail")
    ap.add_argument("watch_folder", help="Folder to save downloaded attachments into")
    args = ap.parse_args()
    print(json.dumps(fetch_contract_notes(args.watch_folder), indent=2))
