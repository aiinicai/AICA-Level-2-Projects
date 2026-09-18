"""Google adapter: Gmail + Google Drive, via plain REST calls.

Same design as :mod:`core.ms_graph_integration`: the shared OAuth2 helper
in :mod:`core.oauth_integration` handles the Authorization Code + PKCE
handshake, then this module talks to the Gmail/Drive REST APIs directly
over HTTPS with the resulting bearer token -- deliberately not using the
heavier ``google-api-python-client`` (its dynamically-generated API proxy
objects are difficult to unit test cleanly); plain REST keeps this
consistent and mockable like every other provider adapter in this codebase.

**Setup required for live use:** create an OAuth 2.0 Client ID in Google
Cloud Console (console.cloud.google.com -> APIs & Services -> Credentials),
type "Desktop app", enable the Gmail API and Drive API for the project, and
add the requested scopes to the OAuth consent screen. Put the resulting
Client ID (and secret, for a Desktop app type) into Settings.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

import requests

from core.oauth_integration import OAuthConfig, OAuthProviderEndpoints
from utils.validation import ValidationError

_GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
_DRIVE_BASE = "https://www.googleapis.com/drive/v3"
_DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
_REQUEST_TIMEOUT_SECONDS = 30

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/drive.file",
]


def build_oauth_config(client_id: str, client_secret: str, redirect_uri: str, scopes: list[str] | None = None) -> OAuthConfig:
    return OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes or DEFAULT_SCOPES,
        endpoints=OAuthProviderEndpoints(
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
        ),
    )


@dataclass
class GmailMessageSummary:
    id: str
    subject: str
    sender: str
    snippet: str
    has_attachments: bool


@dataclass
class DriveFileInfo:
    id: str
    name: str
    mime_type: str
    size: int
    web_view_link: str


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def _raise_for_error(resp: requests.Response, provider_label: str) -> None:
    if resp.ok:
        return
    try:
        detail = resp.json().get("error", {}).get("message", resp.text[:300])
    except ValueError:
        detail = resp.text[:300]
    raise ValidationError(f"{provider_label} request failed (HTTP {resp.status_code}): {detail}")


def list_recent_messages(access_token: str, max_results: int = 10, query: str = "") -> list[GmailMessageSummary]:
    """List recent Gmail messages. ``query`` uses Gmail's search syntax (e.g. 'is:unread has:attachment')."""
    params = {"maxResults": max_results}
    if query:
        params["q"] = query
    resp = requests.get(f"{_GMAIL_BASE}/messages", headers=_headers(access_token), params=params, timeout=_REQUEST_TIMEOUT_SECONDS)
    _raise_for_error(resp, "Gmail")

    summaries = []
    for item in resp.json().get("messages", []):
        detail_resp = requests.get(
            f"{_GMAIL_BASE}/messages/{item['id']}", headers=_headers(access_token),
            params={"format": "metadata", "metadataHeaders": ["Subject", "From"]}, timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        _raise_for_error(detail_resp, "Gmail")
        detail = detail_resp.json()
        headers_map = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        has_attachments = any(part.get("filename") for part in detail.get("payload", {}).get("parts", []) or [])
        summaries.append(GmailMessageSummary(
            id=item["id"], subject=headers_map.get("Subject", ""), sender=headers_map.get("From", ""),
            snippet=detail.get("snippet", ""), has_attachments=has_attachments,
        ))
    return summaries


def download_attachment_bytes(access_token: str, message_id: str, attachment_id: str) -> bytes:
    resp = requests.get(
        f"{_GMAIL_BASE}/messages/{message_id}/attachments/{attachment_id}",
        headers=_headers(access_token), timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_error(resp, "Gmail")
    data_b64url = resp.json().get("data")
    if not data_b64url:
        raise ValidationError("This attachment has no downloadable content.")
    return base64.urlsafe_b64decode(data_b64url + "=" * (-len(data_b64url) % 4))


def create_draft_reply(access_token: str, thread_id: str, to_address: str, subject: str, body_text: str) -> str:
    """Create a Gmail DRAFT (never sends). Returns the new draft's ID."""
    import email.mime.text

    message = email.mime.text.MIMEText(body_text)
    message["to"] = to_address
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    resp = requests.post(
        f"{_GMAIL_BASE}/drafts", headers={**_headers(access_token), "Content-Type": "application/json"},
        json={"message": {"raw": raw, "threadId": thread_id}}, timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_error(resp, "Gmail")
    return resp.json()["id"]


def send_draft(access_token: str, draft_id: str) -> None:
    """Sends a previously created draft. Callers must obtain explicit user
    confirmation before calling this."""
    resp = requests.post(
        f"{_GMAIL_BASE}/drafts/send", headers={**_headers(access_token), "Content-Type": "application/json"},
        json={"id": draft_id}, timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_error(resp, "Gmail")


def list_drive_files(access_token: str, folder_id: str | None = None, query: str = "") -> list[DriveFileInfo]:
    q_parts = []
    if folder_id:
        q_parts.append(f"'{folder_id}' in parents")
    if query:
        q_parts.append(query)
    params = {"fields": "files(id,name,mimeType,size,webViewLink)"}
    if q_parts:
        params["q"] = " and ".join(q_parts)
    resp = requests.get(f"{_DRIVE_BASE}/files", headers=_headers(access_token), params=params, timeout=_REQUEST_TIMEOUT_SECONDS)
    _raise_for_error(resp, "Google Drive")
    return [
        DriveFileInfo(
            id=f["id"], name=f.get("name", ""), mime_type=f.get("mimeType", ""),
            size=int(f.get("size", 0) or 0), web_view_link=f.get("webViewLink", ""),
        )
        for f in resp.json().get("files", [])
    ]


def upload_to_drive(access_token: str, filename: str, content: bytes, folder_id: str | None = None, mime_type: str = "application/pdf") -> DriveFileInfo:
    """Simple (non-resumable) upload -- suitable for typical signed-document sizes."""
    import json as _json

    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    boundary = "cadocuflow-upload-boundary"
    body = (
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{_json.dumps(metadata)}\r\n"
        f"--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--".encode("utf-8")

    resp = requests.post(
        f"{_DRIVE_UPLOAD_BASE}/files",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": f"multipart/related; boundary={boundary}"},
        params={"uploadType": "multipart", "fields": "id,name,mimeType,size,webViewLink"},
        data=body, timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_error(resp, "Google Drive")
    data = resp.json()
    return DriveFileInfo(
        id=data["id"], name=data.get("name", filename), mime_type=data.get("mimeType", mime_type),
        size=int(data.get("size", len(content)) or len(content)), web_view_link=data.get("webViewLink", ""),
    )
