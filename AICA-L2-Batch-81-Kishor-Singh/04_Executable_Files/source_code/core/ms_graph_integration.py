"""Microsoft Graph adapter: Outlook email + OneDrive, via plain REST calls.

Uses the shared OAuth2 helper in :mod:`core.oauth_integration` for the
Authorization Code + PKCE handshake (Microsoft's public-client flow needs
no client secret), then talks to the Graph REST API directly over HTTPS
with the resulting bearer token -- no ``msal``/SDK indirection, so the same
mocked-HTTP testing approach as :mod:`core.ai_provider` applies cleanly.

**Setup required for live use (cannot be done by this code alone):**
register an app in Azure AD (portal.azure.com -> App registrations -> New
registration), add a "Mobile and desktop applications" redirect URI
matching ``OAuthConfig.redirect_uri``, and request the delegated
permissions ``Mail.Read``, ``Mail.Send``, ``Files.ReadWrite`` (admin
consent may be required depending on your tenant's policy). Put the
resulting Application (client) ID into Settings. No client secret is
needed for this flow.

Every document/email import goes through the same "treat content as
data, never instructions" discipline as the AI Assistant
(:mod:`core.document_intelligence`) if that content is later fed to an AI
feature -- this module itself does not interpret email content.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import requests

from core.oauth_integration import OAuthConfig, OAuthProviderEndpoints
from utils.validation import ValidationError

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_REQUEST_TIMEOUT_SECONDS = 30

DEFAULT_SCOPES = ["Mail.Read", "Mail.Send", "Files.ReadWrite", "offline_access"]


def build_oauth_config(client_id: str, redirect_uri: str, tenant: str = "common", scopes: list[str] | None = None) -> OAuthConfig:
    return OAuthConfig(
        client_id=client_id,
        client_secret="",  # public client + PKCE, no secret needed
        redirect_uri=redirect_uri,
        scopes=scopes or DEFAULT_SCOPES,
        endpoints=OAuthProviderEndpoints(
            authorize_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        ),
    )


@dataclass
class EmailAttachmentInfo:
    id: str
    name: str
    content_type: str
    size: int


@dataclass
class EmailMessage:
    id: str
    subject: str
    sender: str
    received_at: str
    has_attachments: bool
    attachments: list[EmailAttachmentInfo] = field(default_factory=list)


@dataclass
class DriveItemInfo:
    id: str
    name: str
    is_folder: bool
    size: int
    web_url: str


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


def _raise_for_graph_error(resp: requests.Response) -> None:
    if resp.ok:
        return
    try:
        detail = resp.json().get("error", {}).get("message", resp.text[:300])
    except ValueError:
        detail = resp.text[:300]
    raise ValidationError(f"Microsoft Graph request failed (HTTP {resp.status_code}): {detail}")


def list_recent_messages(access_token: str, top: int = 10, unread_only: bool = False) -> list[EmailMessage]:
    """List recent Outlook messages in the signed-in user's mailbox."""
    params = {"$top": top, "$orderby": "receivedDateTime desc", "$select": "id,subject,from,receivedDateTime,hasAttachments"}
    if unread_only:
        params["$filter"] = "isRead eq false"
    resp = requests.get(f"{_GRAPH_BASE}/me/messages", headers=_headers(access_token), params=params, timeout=_REQUEST_TIMEOUT_SECONDS)
    _raise_for_graph_error(resp)
    messages = []
    for item in resp.json().get("value", []):
        sender = item.get("from", {}).get("emailAddress", {}).get("address", "")
        messages.append(EmailMessage(
            id=item["id"], subject=item.get("subject", ""), sender=sender,
            received_at=item.get("receivedDateTime", ""), has_attachments=item.get("hasAttachments", False),
        ))
    return messages


def list_message_attachments(access_token: str, message_id: str) -> list[EmailAttachmentInfo]:
    resp = requests.get(
        f"{_GRAPH_BASE}/me/messages/{message_id}/attachments", headers=_headers(access_token), timeout=_REQUEST_TIMEOUT_SECONDS
    )
    _raise_for_graph_error(resp)
    return [
        EmailAttachmentInfo(id=a["id"], name=a.get("name", ""), content_type=a.get("contentType", ""), size=a.get("size", 0))
        for a in resp.json().get("value", [])
    ]


def download_attachment_bytes(access_token: str, message_id: str, attachment_id: str) -> bytes:
    """Download one attachment's raw bytes (decoded from Graph's base64 contentBytes)."""
    import base64

    resp = requests.get(
        f"{_GRAPH_BASE}/me/messages/{message_id}/attachments/{attachment_id}",
        headers=_headers(access_token), timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_graph_error(resp)
    content_b64 = resp.json().get("contentBytes")
    if not content_b64:
        raise ValidationError("This attachment has no downloadable content (it may be a reference attachment, not a file).")
    return base64.b64decode(content_b64)


def create_reply_draft(access_token: str, message_id: str, comment: str) -> str:
    """Create a DRAFT reply -- never sends automatically. Returns the new draft's message ID."""
    resp = requests.post(
        f"{_GRAPH_BASE}/me/messages/{message_id}/createReply",
        headers=_headers(access_token), json={"comment": comment}, timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_graph_error(resp)
    return resp.json()["id"]


def send_draft(access_token: str, draft_message_id: str) -> None:
    """Sends a previously created draft. Callers (the UI) must obtain explicit
    user confirmation before calling this -- sending is a one-way, visible action."""
    resp = requests.post(
        f"{_GRAPH_BASE}/me/messages/{draft_message_id}/send", headers=_headers(access_token), timeout=_REQUEST_TIMEOUT_SECONDS
    )
    if resp.status_code not in (200, 202):
        _raise_for_graph_error(resp)


def list_onedrive_folder(access_token: str, folder_path: str = "/") -> list[DriveItemInfo]:
    path_segment = "root" if folder_path in ("/", "") else f"root:/{folder_path.strip('/')}:"
    resp = requests.get(
        f"{_GRAPH_BASE}/me/drive/{path_segment}/children", headers=_headers(access_token), timeout=_REQUEST_TIMEOUT_SECONDS
    )
    _raise_for_graph_error(resp)
    items = []
    for item in resp.json().get("value", []):
        items.append(DriveItemInfo(
            id=item["id"], name=item.get("name", ""), is_folder="folder" in item,
            size=item.get("size", 0), web_url=item.get("webUrl", ""),
        ))
    return items


def upload_to_onedrive(access_token: str, folder_path: str, filename: str, content: bytes) -> DriveItemInfo:
    """Upload a small file (<4MB) directly. Larger files need Graph's resumable
    upload session API, not implemented here -- most signed documents are well
    under this limit."""
    if len(content) > 4 * 1024 * 1024:
        raise ValidationError("This file is larger than 4 MB; use OneDrive's resumable upload session for large files (not yet implemented here).")
    clean_path = folder_path.strip("/")
    target = f"root:/{clean_path}/{filename}:" if clean_path else f"root:/{filename}:"
    resp = requests.put(
        f"{_GRAPH_BASE}/me/drive/{target}/content",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"},
        data=content, timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_graph_error(resp)
    item = resp.json()
    return DriveItemInfo(id=item["id"], name=item.get("name", filename), is_folder=False, size=item.get("size", len(content)), web_url=item.get("webUrl", ""))
