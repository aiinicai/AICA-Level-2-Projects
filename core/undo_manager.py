"""
Undo and Audit Management Engine for TDS & TCS Certificate PDF Auto-Renamer.
Maintains persistent session logs to enable 1-click rollback of any batch rename operation.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from core.models import CertificateData, ProcessingStatus


class UndoManager:
    """Manages audit trails and rollback of file operations."""

    def __init__(self, audit_dir: Optional[Path] = None):
        if audit_dir:
            self.history_file = Path(audit_dir) / ".rename_audit_history.json"
        else:
            base_dir = Path.home() / ".tds_renamer"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = base_dir / "audit_history.json"

    def record_session(
        self,
        folder_path: str,
        certificates: List[CertificateData],
        mode: str,
    ) -> str:
        """
        Record completed rename operations for rollback.
        Returns the session ID.
        """
        session_id = f"session_{int(time.time())}"
        ops = []

        for cert in certificates:
            if cert.final_filepath and cert.status in (
                ProcessingStatus.RENAMED,
                ProcessingStatus.COPIED,
                ProcessingStatus.MOVED,
            ):
                ops.append({
                    "original_path": str(cert.file_path.resolve()),
                    "renamed_path": str(cert.final_filepath.resolve()),
                    "original_filename": cert.original_filename,
                    "renamed_filename": cert.proposed_filename,
                    "mode": mode,
                    "status": cert.status.value,
                })

        if not ops:
            return ""

        session_entry = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "folder_path": str(folder_path),
            "operation_mode": mode,
            "operations_count": len(ops),
            "operations": ops,
        }

        history = self._load_history()
        history.append(session_entry)
        self._save_history(history)
        return session_id

    def get_last_session(self) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent rename session."""
        history = self._load_history()
        return history[-1] if history else None

    def rollback_session(self, session_id: Optional[str] = None) -> Tuple[int, int, List[str]]:
        """
        Rollback a rename session.
        Returns: (success_count, error_count, log_messages)
        """
        history = self._load_history()
        if not history:
            return 0, 0, ["No rename sessions found to undo."]

        target_session = None
        if session_id:
            for s in history:
                if s["session_id"] == session_id:
                    target_session = s
                    break
        else:
            target_session = history[-1]

        if not target_session:
            return 0, 0, [f"Session {session_id} not found."]

        success_count = 0
        error_count = 0
        logs = []

        for op in reversed(target_session["operations"]):
            orig_path = Path(op["original_path"])
            renamed_path = Path(op["renamed_path"])
            mode = op.get("mode")

            if mode in ("rename_in_place", "move_to_folder"):
                if not renamed_path.exists():
                    error_count += 1
                    logs.append(f"Cannot undo: Renamed file not found: {renamed_path.name}")
                    continue
                if orig_path.exists():
                    error_count += 1
                    logs.append(f"Cannot undo: Original file path already exists: {orig_path.name}")
                    continue
                try:
                    renamed_path.rename(orig_path)
                    success_count += 1
                    logs.append(f"Restored: {renamed_path.name} -> {orig_path.name}")
                except Exception as e:
                    error_count += 1
                    logs.append(f"Error restoring {renamed_path.name}: {str(e)}")

            elif mode == "copy_to_folder":
                # For copy mode, rollback deletes the copied file
                if renamed_path.exists():
                    try:
                        renamed_path.unlink()
                        success_count += 1
                        logs.append(f"Deleted copied file: {renamed_path.name}")
                    except Exception as e:
                        error_count += 1
                        logs.append(f"Error removing {renamed_path.name}: {str(e)}")
                else:
                    logs.append(f"File already absent: {renamed_path.name}")

        # Remove the reverted session from history
        history = [s for s in history if s["session_id"] != target_session["session_id"]]
        self._save_history(history)

        return success_count, error_count, logs

    def _load_history(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, history: List[Dict[str, Any]]):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Failed to save undo history: {e}")
