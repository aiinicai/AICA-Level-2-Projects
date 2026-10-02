"""Client for the BRMCo Server Host.

The Local Host talks ONLY to the BRMCo Server Host — never directly to AI
providers or databases — and holds no provider credentials. In Phase 5 a
server-issued device token will be added here as an Authorization header.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config.settings import APP_VERSION

logger = logging.getLogger("brmco.server_client")


class ServerUnavailable(Exception):
    pass


@dataclass
class ServerStatus:
    reachable: bool
    base_url: str
    message: str
    health: dict[str, Any] | None = None
    version: dict[str, Any] | None = None
    compatible: bool | None = None
    secure: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _version_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in v.split(".")[:3])
    except ValueError:
        return (0,)


class ServerClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        if not self.base_url:
            raise ServerUnavailable("Server URL is not configured.")
        url = f"{self.base_url}{path}"
        try:
            resp = httpx.get(url, timeout=self.timeout,
                             headers={"User-Agent": f"BRMCo-Local/{APP_VERSION}", "Accept": "application/json"})
        except httpx.ConnectError as exc:
            raise ServerUnavailable(f"Cannot reach the BRMCo server at {self.base_url}.") from exc
        except httpx.TimeoutException as exc:
            raise ServerUnavailable(f"The BRMCo server did not respond within {self.timeout:.0f} seconds.") from exc
        except httpx.HTTPError as exc:
            raise ServerUnavailable(f"Server communication failed: {exc}") from exc
        if resp.status_code != 200:
            raise ServerUnavailable(f"Server returned HTTP {resp.status_code} for {path}.")
        try:
            return resp.json()
        except ValueError as exc:
            raise ServerUnavailable(f"Server returned a non-JSON response for {path}.") from exc

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def version(self) -> dict[str, Any]:
        return self._get("/version")

    def status(self) -> ServerStatus:
        parsed = urlparse(self.base_url)
        secure = parsed.scheme == "https"
        warnings: list[str] = []
        if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            warnings.append("The server URL is not HTTPS. Use HTTPS for any non-local server.")
        try:
            health = self.health()
            version = self.version()
        except ServerUnavailable as exc:
            logger.warning("Server check failed: %s", exc)
            return ServerStatus(False, self.base_url, str(exc), secure=secure, warnings=warnings)
        min_local = str(version.get("min_local_version", "0"))
        compatible = _version_tuple(APP_VERSION) >= _version_tuple(min_local)
        if not compatible:
            warnings.append(f"This Local Host ({APP_VERSION}) is older than the server requires ({min_local}).")
        logger.info("Server %s reachable, version %s", self.base_url, version.get("version"))
        return ServerStatus(True, self.base_url, f"Connected to {version.get('application', 'server')} "
                                                 f"{version.get('version', '')}".strip(),
                            health=health, version=version, compatible=compatible, secure=secure,
                            warnings=warnings)
