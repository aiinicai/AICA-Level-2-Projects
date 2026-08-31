"""Hermetic test boundary: offline providers plus a proven socket kill switch."""

from __future__ import annotations

import ipaddress
import os
import socket
from collections.abc import Generator
from typing import Any

import pytest

import amg.config as config_module
from amg.config import get_settings
from amg.providers import reset_provider_state


def _is_loopback(address: object) -> bool:
    if isinstance(address, str):
        host = address
    elif isinstance(address, tuple) and address:
        host = str(address[0])
    else:
        return False
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def hermetic_provider_environment(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Generator[None, None, None]:
    """Block network and force deterministic providers except for explicit live runs."""

    is_live = request.node.get_closest_marker("live") is not None
    live_opt_in = (
        is_live
        and os.getenv("AMG_RUN_LIVE_TESTS") == "1"
        and os.getenv("AMG_OFFLINE") == "0"
    )
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)
    if live_opt_in:
        yield
        get_settings.cache_clear()
        reset_provider_state(clear_working_model=True)
        return

    original_socket_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    def guarded_socket_connect(
        sock: socket.socket, address: Any
    ) -> Any:
        if not _is_loopback(address):
            raise AssertionError(f"Test attempted network access to {address}")
        return original_socket_connect(sock, address)

    def guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
        if not _is_loopback(address):
            raise AssertionError(f"Test attempted network access to {address}")
        return original_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_socket_connect)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setenv("AMG_OFFLINE", "1")
    monkeypatch.setenv("AMG_LLM_PROVIDER", "stub")
    monkeypatch.setenv("AMG_EMBED_PROVIDER", "local")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    # The repository .env intentionally contains live keys. Tests exercise its
    # path logic with a fake loader, while the default suite keeps those keys
    # absent from the process as an additional layer beneath the socket guard.
    monkeypatch.setattr(config_module, "load_dotenv", lambda **_: False)
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)
    yield
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)
