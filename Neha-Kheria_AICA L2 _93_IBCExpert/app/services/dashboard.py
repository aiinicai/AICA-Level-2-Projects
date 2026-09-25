"""Dashboard metrics calculated exclusively from persistent local data."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class DashboardService:
    connection: sqlite3.Connection

    def metrics(self, today: date | None = None) -> dict[str, int]:
        today = today or date.today()
        week_end = today + timedelta(days=7)
        scalar = lambda sql, params=(): int(self.connection.execute(sql, params).fetchone()[0])
        return {
            "active_clients": scalar("SELECT COUNT(*) FROM clients WHERE status='ACTIVE'"),
            "active_assignments": scalar("SELECT COUNT(*) FROM matters WHERE status='OPEN'"),
            "deadlines_today": scalar("SELECT COUNT(*) FROM deadlines WHERE due_date=? AND status NOT IN ('COMPLETED','WAIVED')", (today.isoformat(),)),
            "deadlines_this_week": scalar("SELECT COUNT(*) FROM deadlines WHERE due_date>=? AND due_date<=? AND status NOT IN ('COMPLETED','WAIVED')", (today.isoformat(), week_end.isoformat())),
            "overdue_tasks": scalar("SELECT COUNT(*) FROM tasks WHERE (status='OVERDUE' OR (due_at<? AND status NOT IN ('DONE','CANCELLED')))", (today.isoformat(),)),
            "pending_claims": scalar("SELECT COUNT(*) FROM claims WHERE status IN ('PENDING','UNDER_REVIEW')"),
            "legal_review_required": scalar("SELECT (SELECT COUNT(*) FROM statutes WHERE verification_status IN ('UNVERIFIED','REVIEW_REQUIRED')) + (SELECT COUNT(*) FROM legal_provisions WHERE verification_status IN ('UNVERIFIED','REVIEW_REQUIRED')) + (SELECT COUNT(*) FROM judgments WHERE verification_status IN ('UNVERIFIED','REVIEW_REQUIRED'))"),
            "recommendations": scalar("SELECT COUNT(*) FROM recommendations WHERE dismissed=0"),
            "documents": scalar("SELECT COUNT(*) FROM documents"),
        }

    def process_progress(self) -> list[dict[str, int | str]]:
        rows = self.connection.execute(
            """SELECT pi.id,pd.name,
                      COUNT(ps.id) AS total,
                      SUM(CASE WHEN ps.status='DONE' THEN 1 ELSE 0 END) AS completed
               FROM process_instances pi JOIN process_definitions pd ON pd.id=pi.process_definition_id
               LEFT JOIN process_stages ps ON ps.process_instance_id=pi.id
               WHERE pi.status='ACTIVE' GROUP BY pi.id,pd.name ORDER BY pi.updated_at DESC"""
        ).fetchall()
        return [{"instance_id": row["id"], "name": row["name"], "total": row["total"], "completed": row["completed"] or 0, "percent": round(100 * (row["completed"] or 0) / row["total"]) if row["total"] else 0} for row in rows]
