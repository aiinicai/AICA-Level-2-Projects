"""
auth.py
-------
Simple local authentication for authorised users.

Scope (per firm's decision):
  * Anyone can create and save a brand-new invoice.
  * Only authorised (logged-in) users can:
      - Search / view invoice history
      - Edit and re-save an already-saved invoice
      - Delete a saved invoice
      - Manage user accounts

Design:
  * Individual named accounts (username + password), not a single shared
    password.
  * Once a user logs in successfully, the session stays unlocked until the
    app is closed (or the user explicitly logs out).
  * Passwords are never stored in plain text -- only a salted PBKDF2-SHA256
    hash is written to database/users.json.
"""

import hashlib
import os
import secrets
from datetime import datetime

from app import config, database

PBKDF2_ITERATIONS = 200_000


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return dk.hex()


def _empty_store():
    return {"users": {}}


def load_users() -> dict:
    database.ensure_folders()
    if not os.path.exists(config.USERS_FILE):
        store = _empty_store()
        save_users(store)
        return store
    try:
        import json
        with open(config.USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "users" not in data:
            raise ValueError("bad users file")
        return data
    except Exception:
        store = _empty_store()
        save_users(store)
        return store


def save_users(store: dict):
    database.ensure_folders()
    import json
    tmp_path = config.USERS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, config.USERS_FILE)


def users_exist() -> bool:
    return len(load_users()["users"]) > 0


def list_usernames() -> list:
    return sorted(load_users()["users"].keys())


def create_user(username: str, password: str):
    username = (username or "").strip()
    if not username:
        raise ValueError("Username is required.")
    if not password or len(password) < 4:
        raise ValueError("Password must be at least 4 characters long.")

    store = load_users()
    if username.lower() in {u.lower() for u in store["users"]}:
        raise ValueError(f"A user named '{username}' already exists.")

    salt_hex = secrets.token_hex(16)
    store["users"][username] = {
        "salt": salt_hex,
        "hash": _hash_password(password, salt_hex),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_users(store)


def verify_user(username: str, password: str) -> bool:
    store = load_users()
    user = store["users"].get((username or "").strip())
    if not user:
        return False
    return _hash_password(password or "", user["salt"]) == user["hash"]


def change_password(username: str, new_password: str):
    if not new_password or len(new_password) < 4:
        raise ValueError("Password must be at least 4 characters long.")
    store = load_users()
    if username not in store["users"]:
        raise ValueError(f"User '{username}' not found.")
    salt_hex = secrets.token_hex(16)
    store["users"][username]["salt"] = salt_hex
    store["users"][username]["hash"] = _hash_password(new_password, salt_hex)
    save_users(store)


def delete_user(username: str):
    store = load_users()
    if username not in store["users"]:
        raise ValueError(f"User '{username}' not found.")
    if len(store["users"]) <= 1:
        raise ValueError("Cannot delete the last remaining authorised user account.")
    del store["users"][username]
    save_users(store)
