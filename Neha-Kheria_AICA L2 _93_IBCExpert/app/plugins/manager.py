"""Disabled-by-default local plugin registry and in-process event bus.

No network transport is implemented here. Plugins are registered explicitly in code or by a
future trusted installer, remain disabled by default, and only receive declared permissions.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.errors import ValidationError
from app.core.time import SystemClock, to_utc_iso
from app.db.connection import transaction

KNOWN_PERMISSIONS = {
    "events.read",
    "documents.read_metadata",
    "clients.read_summary",
    "local_import.request",
    "future.network_update",
}

@dataclass(frozen=True)
class PluginManifest:
    key: str
    display_name: str
    version: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""

    def validate(self) -> None:
        if not self.key or len(self.key) > 80 or not self.key.replace("-", "").replace("_", "").isalnum():
            raise ValidationError("Plugin key is invalid.")
        unknown = set(self.permissions) - KNOWN_PERMISSIONS
        if unknown:
            raise ValidationError(f"Plugin requests unsupported permission(s): {', '.join(sorted(unknown))}")
        if "future.network_update" in self.permissions:
            raise ValidationError("Internet update permission is reserved and unavailable in this version.")


class EventBus:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        import uuid
        now = to_utc_iso(SystemClock().now())
        with transaction(self.connection):
            self.connection.execute(
                "INSERT INTO event_outbox(event_uuid,event_type,payload_json,created_at) VALUES(?,?,?,?)",
                (str(uuid.uuid4()), event_type, json.dumps(payload, sort_keys=True, ensure_ascii=False), now),
            )
        for handler in tuple(self._subscribers.get(event_type, ())):
            handler(dict(payload))


class PluginManager:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self._manifests: dict[str, PluginManifest] = {}

    def register(self, manifest: PluginManifest) -> None:
        manifest.validate()
        self._manifests[manifest.key] = manifest
        now = to_utc_iso(SystemClock().now())
        self.connection.execute(
            """INSERT INTO plugin_configuration(plugin_key,display_name,version,enabled,permissions_json,updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(plugin_key) DO UPDATE SET display_name=excluded.display_name,
                 version=excluded.version, permissions_json=excluded.permissions_json, updated_at=excluded.updated_at""",
            (manifest.key, manifest.display_name, manifest.version, 0, json.dumps(list(manifest.permissions)), now),
        )
        self.connection.commit()

    def list_plugins(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT plugin_key,display_name,version,enabled,permissions_json,updated_at FROM plugin_configuration ORDER BY display_name"
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["permissions"] = json.loads(item.pop("permissions_json") or "[]")
            item["description"] = self._manifests.get(item["plugin_key"], PluginManifest(item["plugin_key"], item["display_name"], item["version"])).description
            result.append(item)
        return result

    def set_enabled(self, plugin_key: str, enabled: bool) -> None:
        if plugin_key not in self._manifests:
            raise ValidationError("Plugin is not registered in this application build.")
        self.connection.execute(
            "UPDATE plugin_configuration SET enabled=?,updated_at=? WHERE plugin_key=?",
            (1 if enabled else 0, to_utc_iso(SystemClock().now()), plugin_key),
        )
        self.connection.commit()

    def require_permission(self, plugin_key: str, permission: str) -> None:
        row = self.connection.execute(
            "SELECT enabled,permissions_json FROM plugin_configuration WHERE plugin_key=?", (plugin_key,)
        ).fetchone()
        if row is None or not int(row["enabled"]):
            raise ValidationError("Plugin is disabled.")
        permissions = set(json.loads(row["permissions_json"] or "[]"))
        if permission not in permissions:
            raise ValidationError("Plugin does not have permission for this operation.")
        if permission == "future.network_update":
            raise ValidationError("Internet update functionality is not available in this version.")
