"""Key/value application settings (e.g. last selected company)."""
from __future__ import annotations

from ipt.db.base import Database
from ipt.db.models import AppSetting


class SettingsService:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str, default: str = "") -> str:
        with self.db.session() as s:
            row = s.get(AppSetting, key)
            return row.value if row else default

    def set(self, key: str, value: str) -> None:
        with self.db.session() as s:
            row = s.get(AppSetting, key)
            if row is None:
                s.add(AppSetting(key=key, value=value))
            else:
                row.value = value
