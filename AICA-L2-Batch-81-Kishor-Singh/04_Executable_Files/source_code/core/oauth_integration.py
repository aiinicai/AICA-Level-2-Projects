"""Generic OAuth 2.0 Authorization Code flow helper, shared by the Microsoft
Graph (Outlook/OneDrive) and Google (Gmail/Drive) adapters -- both are
standard OAuth2 providers, so the handshake logic is identical; only the
endpoint URLs, scopes, and API calls that follow differ.

**This is real, standards-based OAuth2 client code, but it has never
completed a live authorization with an actual Microsoft or Google account**
-- doing that requires an app registered under your own developer account
(Azure AD App Registration / Google Cloud Console OAuth client), which only
you can create. Every test in ``tests/test_oauth_integration.py`` and the
provider-specific test files mocks the HTTP layer, the same proven approach
used for ``core/ai_provider.py``. See the README "Email/Cloud Integration
Setup" section for exactly how to register an app and go live.

No token is ever persisted to disk by this module -- callers (the UI) are
responsible for deciding whether/how to cache a refresh token (e.g. via the
OS credential store, matching ``core.ai_provider``'s pattern), and this
module never logs a token value.
"""
from __future__ import annotations

import secrets
import urllib.parse
from dataclasses import dataclass, field

import requests

from utils.validation import ValidationError

_REQUEST_TIMEOUT_SECONDS = 30


class OAuthError(ValidationError):
    """Raised for any OAuth handshake or token-refresh failure."""


@dataclass
class OAuthProviderEndpoints:
    authorize_url: str
    token_url: str


@dataclass
class OAuthConfig:
    client_id: str
    client_secret: str  # empty string for a public/native client using PKCE only
    redirect_uri: str
    scopes: list[str] = field(default_factory=list)
    endpoints: OAuthProviderEndpoints = None  # type: ignore[assignment]  # set by provider-specific subclasses/factories


@dataclass
class OAuthToken:
    access_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str = "Bearer"
    scope: str = ""


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) for PKCE -- recommended for any
    OAuth client, required for public/native clients with no client secret."""
    import base64
    import hashlib

    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorization_url(config: OAuthConfig, state: str, code_challenge: str | None = None) -> str:
    params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
        "scope": " ".join(config.scopes),
        "state": state,
    }
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    return f"{config.endpoints.authorize_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(config: OAuthConfig, authorization_code: str, code_verifier: str | None = None) -> OAuthToken:
    data = {
        "client_id": config.client_id,
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": config.redirect_uri,
    }
    if config.client_secret:
        data["client_secret"] = config.client_secret
    if code_verifier:
        data["code_verifier"] = code_verifier

    resp = requests.post(config.endpoints.token_url, data=data, timeout=_REQUEST_TIMEOUT_SECONDS)
    return _parse_token_response(resp)


def refresh_access_token(config: OAuthConfig, refresh_token: str) -> OAuthToken:
    data = {
        "client_id": config.client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if config.client_secret:
        data["client_secret"] = config.client_secret

    resp = requests.post(config.endpoints.token_url, data=data, timeout=_REQUEST_TIMEOUT_SECONDS)
    return _parse_token_response(resp)


def _parse_token_response(resp: requests.Response) -> OAuthToken:
    if not resp.ok:
        try:
            detail = resp.json().get("error_description", resp.text[:300])
        except ValueError:
            detail = resp.text[:300]
        raise OAuthError(f"OAuth token request failed (HTTP {resp.status_code}): {detail}")
    data = resp.json()
    return OAuthToken(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=int(data.get("expires_in", 3600)),
        token_type=data.get("token_type", "Bearer"),
        scope=data.get("scope", ""),
    )
