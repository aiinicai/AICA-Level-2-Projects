"""Database repository for CRUD operations and analysis persistence."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Dict, List, Optional, Tuple, Any

from src.database.schema import init_database
from src.core.components import MappingDecision
from src.core.assumptions import AssumptionItem
from src.core.calculator import SingleRatioResult, CalculationResultSet
from src.core.integrity import IntegrityCheckResult
from src.core.audit import AuditLogger


class Repository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = init_database(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_connection(self) -> sqlite3.Connection:
        return self.conn

    def list_clients(self, search_query: str = "") -> List[Dict[str, Any]]:
        query = """
            SELECT c.id, c.name, c.cin, c.fy_end, c.units, c.schedule_division,
                   c.created_at, c.updated_at,
                   (SELECT a.fy_label FROM analyses a WHERE a.client_id = c.id ORDER BY a.id DESC LIMIT 1) as last_fy,
                   (SELECT a.created_at FROM analyses a WHERE a.client_id = c.id ORDER BY a.id DESC LIMIT 1) as last_analysis_date
            FROM clients c
        """
        params = []
        if search_query:
            query += " WHERE c.name LIKE ?"
            params.append(f"%{search_query}%")
        query += " ORDER BY c.updated_at DESC"
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def get_client(self, client_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_client_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE name = ? COLLATE NOCASE", (name.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_client(self, name: str, cin: str = "", units: str = "Lacs", schedule_division: str = "Division I") -> int:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Client name cannot be blank.")
        if len(clean_name) < 2:
            raise ValueError("Client name must be at least 2 characters.")
        if len(clean_name) > 150:
            raise ValueError("Client name cannot exceed 150 characters.")
            
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO clients (name, cin, units, schedule_division, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (clean_name, cin.strip(), units, schedule_division, now, now)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_client_name(self, client_id: int, new_name: str) -> None:
        clean_name = new_name.strip()
        if not clean_name:
            raise ValueError("Client name cannot be blank.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "UPDATE clients SET name = ?, updated_at = ? WHERE id = ?",
            (clean_name, now, client_id)
        )
        self.conn.commit()

    def update_client_metadata(self, client_id: int, fy_end: str, units: str, schedule_division: str = "Division I") -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "UPDATE clients SET fy_end = ?, units = ?, schedule_division = ?, updated_at = ? WHERE id = ?",
            (fy_end, units, schedule_division, now, client_id)
        )
        self.conn.commit()

    def duplicate_client(self, client_id: int, new_name: str) -> int:
        original = self.get_client(client_id)
        if not original:
            raise ValueError(f"Client {client_id} not found")
            
        new_id = self.create_client(
            name=new_name,
            cin=original.get("cin", ""),
            units=original.get("units", "Lacs"),
            schedule_division=original.get("schedule_division", "Division I")
        )
        return new_id

    def delete_client(self, client_id: int) -> None:
        self.conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        self.conn.commit()

    def save_analysis(
        self,
        client_id: int,
        fy_label: str,
        threshold_pct: float,
        ratios: List[SingleRatioResult],
        integrity_results: List[IntegrityCheckResult],
        audit_logger: AuditLogger
    ) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        
        cursor.execute(
            "INSERT INTO analyses (client_id, fy_label, threshold_pct, created_at) VALUES (?, ?, ?, ?)",
            (client_id, fy_label, threshold_pct, now)
        )
        analysis_id = cursor.lastrowid
        
        for r in ratios:
            cursor.execute(
                """
                INSERT INTO ratio_results (
                    analysis_id, ratio_key, numerator_cy, denominator_cy, value_cy,
                    numerator_py, denominator_py, value_py, variance_pct, is_flagged,
                    status, reason_generated, reason_final, is_reason_edited
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id, r.key, r.numerator_cy, r.denominator_cy, r.value_cy,
                    r.numerator_py, r.denominator_py, r.value_py, r.variance_pct,
                    1 if r.is_flagged else 0, r.status, r.reason_generated,
                    r.reason_final, 1 if r.is_reason_edited else 0
                )
            )
            
        for ic in integrity_results:
            cursor.execute(
                """
                INSERT INTO integrity_results (
                    analysis_id, check_id, expected, actual, status, comment
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (analysis_id, ic.check_id, ic.expected, ic.actual, ic.status, ic.comment)
            )
            
        for e in audit_logger.entries:
            cursor.execute(
                "INSERT INTO audit_log (analysis_id, timestamp, event_type, detail) VALUES (?, ?, ?, ?)",
                (analysis_id, e.timestamp, e.event_type, e.detail)
            )
            
        self.conn.commit()
        return analysis_id

    def backup_to_file(self, target_path: str) -> None:
        self.conn.commit()
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(self.db_path), str(target))

    def restore_from_file(self, source_path: str) -> None:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Backup file not found: {source_path}")
        self.conn.close()
        shutil.copy2(str(source), str(self.db_path))
        self.conn = init_database(self.db_path)
        self.conn.row_factory = sqlite3.Row
