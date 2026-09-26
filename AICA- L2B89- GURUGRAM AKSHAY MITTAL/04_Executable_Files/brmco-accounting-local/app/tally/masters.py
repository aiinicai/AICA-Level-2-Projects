"""Tally master synchronisation and the in-memory lookup used during validation.

Phase 1 syncs names/parents for ledgers, groups, stock items, units and voucher
types. The engine never creates masters in Tally — unknown names are reported as
validation errors. Phase 2 can add GST details, opening balances, incremental
sync etc. by extending ``MASTER_COLLECTIONS`` and ``MasterRecord.extra``.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.database.repositories import MasterRecord, MasterRepository
from app.tally.client import MASTER_COLLECTIONS, TallyConnectionError

logger = logging.getLogger("brmco.tally.masters")

MASTER_TYPES = tuple(MASTER_COLLECTIONS)


class CachedMasters:
    """Case-insensitive lookup over the cached masters of one company."""

    def __init__(self, repo: MasterRepository | None, company: str = "") -> None:
        self._data: dict[str, dict[str, dict[str, Any]]] = {t: {} for t in MASTER_TYPES}
        if repo is None:
            return
        for t in MASTER_TYPES:
            rows = repo.all(company, t)
            self._data[t] = {
                r["name"].lower(): {"name": r["name"], "parent": r["parent"],
                                    **(json.loads(r["extra_json"]) if r.get("extra_json") else {})}
                for r in rows
            }

    @classmethod
    def from_records(cls, records: dict[str, list[dict[str, Any]]]) -> "CachedMasters":
        """In-memory masters (tests, sample generation, demo)."""
        inst = cls(None)
        for t, items in records.items():
            inst._data[t] = {i["name"].lower(): dict(i) for i in items}
        return inst

    def has(self, master_type: str) -> bool:
        return bool(self._data.get(master_type))

    def resolve(self, master_type: str, name: str) -> str | None:
        rec = self._data.get(master_type, {}).get(name.strip().lower())
        return rec["name"] if rec else None

    def get(self, master_type: str, name: str) -> dict[str, Any] | None:
        return self._data.get(master_type, {}).get(name.strip().lower())

    def names(self, master_type: str) -> list[str]:
        return [r["name"] for r in self._data.get(master_type, {}).values()]

    def is_under_group(self, ledger: str, groups: set[str]) -> bool | None:
        """True/False if determinable from cached groups, None if groups are not synced."""
        if not self.has("group"):
            return None
        rec = self.get("ledger", ledger)
        if rec is None:
            return None
        wanted = {g.lower() for g in groups}
        seen: set[str] = set()
        parent = (rec.get("parent") or "").lower()
        while parent and parent not in seen:
            if parent in wanted:
                return True
            seen.add(parent)
            group = self._data["group"].get(parent)
            parent = (group.get("parent") or "").lower() if group else ""
        return False

    def ledgers_under(self, groups: set[str]) -> list[str]:
        return [n for n in self.names("ledger") if self.is_under_group(n, groups)]


class MasterSyncService:
    def __init__(self, repo: MasterRepository) -> None:
        self.repo = repo

    def sync(self, client, company_key: str, tally_company: str, types: list[str] | None = None) -> dict[str, Any]:
        """Fetch masters from Tally and replace the local cache, type by type.

        A failure for one type leaves that type's previous cache intact.
        """
        results: dict[str, Any] = {}
        for t in types or list(MASTER_TYPES):
            if t not in MASTER_COLLECTIONS:
                results[t] = {"status": "error", "message": f"Unknown master type '{t}'"}
                continue
            try:
                records = client.fetch_masters(t, tally_company)
                count = self.repo.replace(company_key, t, (
                    MasterRecord(r["name"], r.get("parent"), {"unit": r["unit"]} if r.get("unit") else None)
                    for r in records))
                self.repo.log_sync(company_key, t, count, "ok")
                results[t] = {"status": "ok", "count": count}
                logger.info("Synced %d %s masters for %s", count, t, company_key)
            except TallyConnectionError as exc:
                self.repo.log_sync(company_key, t, 0, "error", str(exc))
                results[t] = {"status": "error", "message": str(exc)}
                # Tally is down: no point trying the remaining types.
                for rest in (types or list(MASTER_TYPES)):
                    results.setdefault(rest, {"status": "skipped", "message": "Tally not reachable"})
                break
            except Exception as exc:  # malformed response etc.
                logger.exception("Master sync failed for %s", t)
                self.repo.log_sync(company_key, t, 0, "error", str(exc))
                results[t] = {"status": "error", "message": f"Could not read {t} list from Tally: {exc}"}
        return results
