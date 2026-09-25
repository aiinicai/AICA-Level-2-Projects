"""Process-level outbound network guard for the offline application runtime.

Only loopback TCP/UDP destinations are permitted. Local Unix-domain sockets are left alone.
The dependency bootstrap intentionally runs before this guard so first-run package installation
can occur when needed. No current application feature receives an internet bypass.
"""
from __future__ import annotations

import ipaddress
import socket
import threading
from contextlib import contextmanager


class OutboundNetworkBlocked(OSError):
    """Raised before a non-loopback network connection or DNS lookup can occur."""


_LOCK = threading.RLock()
_INSTALLED = False
_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CONNECT_EX = socket.socket.connect_ex
_ORIGINAL_GETADDRINFO = socket.getaddrinfo


def _host_is_loopback(host: object) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        try:
            host = host.decode("ascii")
        except UnicodeDecodeError:
            return False
    text = str(host).strip().strip("[]").lower()
    if text in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


def _socket_address_is_local(sock: socket.socket, address: object) -> bool:
    if sock.family in {getattr(socket, "AF_UNIX", -999)}:
        return True
    if sock.family in {socket.AF_INET, socket.AF_INET6}:
        if not isinstance(address, tuple) or not address:
            return False
        return _host_is_loopback(address[0])
    # Non-IP local families (where available) are not internet egress.
    return sock.family not in {socket.AF_INET, socket.AF_INET6}


def _guarded_connect(self: socket.socket, address):
    if not _socket_address_is_local(self, address):
        raise OutboundNetworkBlocked("IBC Expert offline mode blocked a non-loopback network connection.")
    return _ORIGINAL_CONNECT(self, address)


def _guarded_connect_ex(self: socket.socket, address):
    if not _socket_address_is_local(self, address):
        raise OutboundNetworkBlocked("IBC Expert offline mode blocked a non-loopback network connection.")
    return _ORIGINAL_CONNECT_EX(self, address)


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    if not _host_is_loopback(host):
        raise OutboundNetworkBlocked("IBC Expert offline mode blocked external DNS/name resolution.")
    return _ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)


def install_outbound_network_guard() -> None:
    global _INSTALLED
    with _LOCK:
        if _INSTALLED:
            return
        socket.socket.connect = _guarded_connect
        socket.socket.connect_ex = _guarded_connect_ex
        socket.getaddrinfo = _guarded_getaddrinfo
        _INSTALLED = True


def network_guard_installed() -> bool:
    return _INSTALLED


@contextmanager
def future_permission_boundary(*_args, **_kwargs):
    """Reserved integration boundary; internet access is intentionally unavailable now."""
    raise OutboundNetworkBlocked(
        "Internet integrations are disabled in this version. A future secure updater may implement an explicit allowlist here."
    )
    yield  # pragma: no cover
