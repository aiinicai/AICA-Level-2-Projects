"""
services/knowledge_vault.py — R K Muley & Co | Tax Notice Litigation Assistant v8.1

CA Knowledge Vault — firm institutional memory.
Uses the `ca_vault` table managed exclusively by DatabaseMigrationEngine.
The v8 schema migration handles data continuity from prior installations.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from database import execute_query, query_dicts

logger = logging.getLogger("RKMuley.Vault.v9")


class VaultError(Exception):
    """CA Knowledge Vault I/O error."""


class CAKnowledgeVault:
    """
    Persistent vault storing past notice outcomes.
    Powers NoticeProbabilityPredictor (F1) and ReplySuccessScorer (F2).
    All data stays local — never leaves the machine.
    Uses `ca_vault` table (managed by DatabaseMigrationEngine).
    """

    def add_entry(self, entry: dict) -> int:
        """Add a new vault record. Returns new row id."""
        try:
            return int(execute_query(
                "INSERT INTO ca_vault "
                "(ts_added, assessee, ay, notice_type, sections, issue_type, "
                "quantum_lakh, outcome, strategy, lessons, forum, tags, "
                "ao_ward, assessee_type, created_by) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    entry.get("assessee", "Anonymous"),
                    entry.get("ay", ""),
                    entry.get("notice_type", ""),
                    entry.get("sections", ""),
                    entry.get("issue_type", ""),
                    float(entry.get("quantum_lakh", 0.0)),
                    entry.get("outcome", "Pending"),
                    entry.get("strategy", ""),
                    entry.get("lessons", ""),
                    entry.get("forum", "AO Level"),
                    entry.get("tags", ""),
                    entry.get("ao_ward", ""),
                    entry.get("assessee_type", ""),
                    entry.get("created_by", ""),
                ),
            ) or -1)
        except Exception as exc:
            raise VaultError(f"add_entry failed: {exc}") from exc

    def update_outcome(self, row_id: int, outcome: str, lessons: str = "") -> None:
        """Update the outcome of an existing vault entry."""
        try:
            execute_query(
                "UPDATE ca_vault SET outcome=?, lessons=?, updated_at=? WHERE id=?",
                (outcome, lessons, datetime.now().isoformat(), row_id),
            )
        except Exception as exc:
            raise VaultError(f"update_outcome failed: {exc}") from exc

    def get_similar(self, keywords: list[str], limit: int = 5) -> list[dict]:
        """Fetch vault entries matching any of the given keywords."""
        if not keywords:
            return []
        try:
            clauses = " OR ".join(
                "(issue_type LIKE ? OR tags LIKE ? OR sections LIKE ?)"
                for _ in keywords
            )
            params: list = []
            for kw in keywords:
                params += [f"%{kw}%", f"%{kw}%", f"%{kw}%"]
            return query_dicts(
                f"SELECT * FROM ca_vault WHERE {clauses} ORDER BY ts_added DESC LIMIT {int(limit)}",
                tuple(params),
            )
        except Exception as exc:
            logger.warning("Vault get_similar error: %s", exc)
            return []

    def win_rate(self, issue_kw: str) -> Optional[float]:
        """Win rate for a given issue keyword. Returns None if no data."""
        try:
            row = execute_query(
                "SELECT COUNT(*) as t, SUM(CASE WHEN outcome='Win' THEN 1 ELSE 0 END) as w "
                "FROM ca_vault WHERE issue_type LIKE ? AND outcome != 'Pending'",
                (f"%{issue_kw}%",),
                fetch="one",
            )
            if row and row[0] > 0:
                return round(row[1] / row[0], 2)
            return None
        except Exception:
            return None

    def all_entries(self, limit: int = 500) -> list[dict]:
        """Fetch all vault entries ordered by most recent."""
        try:
            return query_dicts(f"SELECT * FROM ca_vault ORDER BY ts_added DESC LIMIT {int(limit)}")
        except Exception:
            return []

    def delete(self, row_id: int) -> None:
        """Hard delete a vault entry (admin only)."""
        try:
            execute_query("DELETE FROM ca_vault WHERE id=?", (row_id,))
        except Exception as exc:
            raise VaultError(f"delete failed: {exc}") from exc

    def stats(self) -> dict:
        """Summary statistics for the analytics tab."""
        try:
            row = execute_query(
                "SELECT "
                "COUNT(*) as total, "
                "SUM(CASE WHEN outcome='Win'     THEN 1 ELSE 0 END) as wins, "
                "SUM(CASE WHEN outcome='Loss'    THEN 1 ELSE 0 END) as losses, "
                "SUM(CASE WHEN outcome='Settle'  THEN 1 ELSE 0 END) as settlements, "
                "SUM(CASE WHEN outcome='Pending' THEN 1 ELSE 0 END) as pending "
                "FROM ca_vault",
                fetch="one",
            )
            section_stats = query_dicts(
                "SELECT sections, outcome, COUNT(*) as cnt "
                "FROM ca_vault WHERE outcome != 'Pending' "
                "GROUP BY sections, outcome ORDER BY cnt DESC LIMIT 20"
            )
            total = row[0] or 0
            wins  = row[1] or 0
            return {
                "total":        total,
                "wins":         wins,
                "losses":       row[2] or 0,
                "settlements":  row[3] or 0,
                "pending":      row[4] or 0,
                "win_rate_pct": round(100 * wins / total, 1) if total > 0 else 0,
                "section_breakdown": section_stats,
            }
        except Exception:
            return {"total": 0, "wins": 0, "losses": 0, "settlements": 0,
                    "pending": 0, "win_rate_pct": 0, "section_breakdown": []}

    def export_csv(self) -> str:
        """Export all entries as a CSV string."""
        import csv, io
        entries = self.all_entries()
        if not entries:
            return "No records in vault."
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=entries[0].keys())
        w.writeheader()
        w.writerows(entries)
        return buf.getvalue()
