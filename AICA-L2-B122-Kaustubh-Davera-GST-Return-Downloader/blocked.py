"""Clients blocked after a failed login.

A client stays blocked until its password in the Excel file changes (or a
user clicks Unblock). Only a hash of GSTIN+password is stored, never the
password itself.
"""
import hashlib
import json
import os
import threading
from datetime import datetime

from settings import app_dir

PATH = os.path.join(app_dir(), "blocked.json")
_lock = threading.Lock()


def _hash(gstin: str, password: str) -> str:
    return hashlib.sha256(f"{gstin}|{password}".encode("utf-8")).hexdigest()


def _load() -> dict:
    if not os.path.exists(PATH):
        return {}
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, PATH)


def check(client) -> dict | None:
    """Return the block entry if blocked. Auto-unblocks when the password changed."""
    with _lock:
        data = _load()
        entry = data.get(client.gstin)
        if not entry:
            return None
        if entry.get("hash") != _hash(client.gstin, client.password):
            data.pop(client.gstin, None)
            _save(data)
            return None
        return entry


def block(client, reason: str) -> None:
    with _lock:
        data = _load()
        data[client.gstin] = {
            "hash": _hash(client.gstin, client.password),
            "reason": reason,
            "time": datetime.now().strftime("%d-%b-%Y %H:%M"),
        }
        _save(data)


def unblock(gstin: str) -> None:
    with _lock:
        data = _load()
        if data.pop(gstin, None) is not None:
            _save(data)
