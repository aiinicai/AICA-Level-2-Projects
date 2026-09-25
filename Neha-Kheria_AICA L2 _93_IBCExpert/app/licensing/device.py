"""Privacy-preserving device request code generation."""
from __future__ import annotations

import base64
import hashlib
import json
import platform
import subprocess
import uuid
from pathlib import Path

REQUEST_PREFIX = "IBC-REQ1-"


def _windows_machine_guid() -> str:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            return str(winreg.QueryValueEx(key, "MachineGuid")[0])
    except (OSError, ImportError):
        return "unavailable"


def _machine_token() -> str:
    system = platform.system()
    if system == "Windows":
        stable = _windows_machine_guid()
    else:
        stable = "unavailable"
        for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
            try:
                value = path.read_text(encoding="ascii").strip()
                if value:
                    stable = value
                    break
            except OSError:
                continue
    # Hash immediately: raw machine identifiers are never displayed or persisted
    # in the licence payload.
    raw = f"{system}|{platform.machine()}|{stable}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def device_request_code(installation_id: str) -> str:
    try:
        uuid.UUID(installation_id)
    except ValueError as exc:
        raise ValueError("installation_id must be a UUID") from exc
    canonical = json.dumps(
        {"installation_id": installation_id, "machine_token": _machine_token(), "v": 1},
        separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).digest()[:20]
    encoded = base64.b32encode(digest).decode("ascii").rstrip("=")
    return REQUEST_PREFIX + "-".join(encoded[i:i+4] for i in range(0, len(encoded), 4))


def normalize_request_code(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "")
    if not normalized.startswith(REQUEST_PREFIX):
        raise ValueError("Device request code has an invalid prefix")
    compact = normalized[len(REQUEST_PREFIX):].replace("-", "")
    if len(compact) != 32 or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for ch in compact):
        raise ValueError("Device request code has an invalid format")
    return REQUEST_PREFIX + "-".join(compact[i:i+4] for i in range(0, 32, 4))
